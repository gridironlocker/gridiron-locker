"""Polite, bounded HTTP layer for the OSINT prospect engine.

Safety properties (all required by the engine spec):

* A descriptive User-Agent that identifies Gridiron Locker and links the
  repository's public storefront.
* robots.txt is checked (and cached per host) before any content fetch.
* Per-host rate limiting (minimum interval between requests, default 2.5s).
* Hard caps: timeout, response size, redirects handled by urllib.
* Only http/https URLs.
* No cookies, no credentials, no sessions, no login, no CAPTCHA solving.

A ``transport`` callable can be injected so the test suite can run the whole
pipeline against fixture responses without any network access.
"""
from __future__ import annotations

import hashlib
import html.parser
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = (
    "GridironLockerProspectResearch/1.0 "
    "(+https://gridironlocker.store; public business prospect research; "
    "contact via storefront contact page)"
)

DEFAULT_TIMEOUT = 15
DEFAULT_MIN_INTERVAL = 2.5      # seconds between requests to the same host
MAX_BYTES = 2_000_000           # 2 MiB response cap
MAX_CACHE = 512                 # robots caches / hosts remembered


class HtmlTextParser(html.parser.HTMLParser):
    """Collect visible text and mailto: links from HTML."""

    _SKIP = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.mailto_links: list[str] = []
        self.links: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value:
                    self.links.append(value)
                    if value.lower().startswith("mailto:"):
                        self.mailto_links.append(value[7:].split("?", 1)[0])

    def handle_endtag(self, tag) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data) -> None:
        if not self._skip_depth and data.strip():
            self.text_parts.append(data.strip())

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


def parse_html(raw: bytes | str) -> HtmlTextParser:
    parser = HtmlTextParser()
    if isinstance(raw, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                raw = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
    parser.feed(raw or "")
    parser.close()
    return parser


@dataclass
class FetchResult:
    url: str
    status: int
    body: bytes
    content_type: str = ""
    fetched_at: str = ""
    robots_ok: bool = True

    def text(self) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                return self.body.decode(encoding)
            except UnicodeDecodeError:
                continue
        return self.body.decode("utf-8", errors="replace")

    def ok(self) -> bool:
        return 200 <= self.status < 300


class RobotsPolicy:
    """Tiny robots.txt evaluator (User-agent: * and our own UA, Disallow)."""

    def __init__(self) -> None:
        self._cache: dict[str, "_RulesList | None"] = {}
        self._fetched: set[str] = set()

    def remember(self, host: str, rules: "_RulesList | None") -> None:
        self._cache[host] = rules
        self._fetched.add(host)

    def fetched(self, host: str) -> bool:
        return host in self._fetched

    def rules(self, host: str) -> list[str] | None:
        return self._cache.get(host)

    @staticmethod
    def parse(body: str, ua_token: str = "gridironlockerprospectresearch") -> "_RulesList | None":
        """Return the rules applying to us (our UA group if present, else the
        ``*`` group). An unparseable robots file allows everything (None)."""
        groups: list[dict] = []
        current: dict | None = None
        for line in body.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip().lower()
            value = value.strip()
            if key == "user-agent":
                if current is not None and current["rules"]:
                    current = None  # a new group starts after rules were seen
                if current is None:
                    current = {"agents": [], "rules": []}
                    groups.append(current)
                current["agents"].append(value.lower())
            elif key in ("disallow", "allow") and current is not None:
                current["rules"].append((key, value))
        chosen: list = []
        for group in groups:
            agents = group.get("agents", [])
            if ua_token in agents:
                chosen = group["rules"]
                break  # a group naming our agent always wins
            if "*" in agents and not chosen:
                chosen = group["rules"]
        if not chosen:
            return None
        disallows = [v for k, v in chosen if k == "disallow"]
        allows = [v for k, v in chosen if k == "allow"]
        return _RulesList(disallows, allows)

    def permitted(self, host: str, path: str) -> bool:
        rules = self._cache.get(host)
        if rules is None:
            return True
        return rules.permitted(path)


class _RulesList:
    def __init__(self, disallows: list[str], allows: list[str]) -> None:
        self.disallows = [d for d in disallows if d]
        self.allows = [a for a in allows if a]

    def permitted(self, path: str) -> bool:
        for allow in self.allows:
            if path.startswith(allow):
                return True
        for disallow in self.disallows:
            if path.startswith(disallow):
                return False
        return True


class Fetcher:
    """Rate-limited, robots-respecting HTTP GET client."""

    def __init__(
        self,
        transport=None,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        timeout: int = DEFAULT_TIMEOUT,
        max_bytes: int = MAX_BYTES,
        user_agent: str = USER_AGENT,
    ) -> None:
        #: transport(url, headers, timeout) -> (status, content_type, body)
        self.transport = transport or self._urllib_transport
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.user_agent = user_agent
        self.robots = RobotsPolicy()
        self._last_hit: dict[str, float] = {}
        self.stats = {"requests": 0, "robots_denied": 0, "errors": 0, "bytes": 0}

    # -- transport -------------------------------------------------------
    @staticmethod
    def _urllib_transport(url: str, headers: dict, timeout: int):
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(8 * 1024 * 1024)
                return response.status, response.headers.get("Content-Type", ""), body
        except urllib.error.HTTPError as err:
            return err.code, err.headers.get("Content-Type", "") if err.headers else "", b""
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return 0, "", b""

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def host_of(url: str) -> str:
        return urllib.parse.urlsplit(url).netloc.lower()

    def _throttle(self, host: str) -> None:
        last = self._last_hit.get(host)
        if last is not None:
            wait = self.min_interval - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_hit[host] = time.monotonic()
        if len(self._last_hit) > MAX_CACHE:
            self._last_hit.clear()

    def _load_robots(self, scheme_host: str) -> None:
        host = scheme_host.split("://", 1)[-1]
        if self.robots.fetched(host):
            return
        url = f"{scheme_host}/robots.txt"
        try:
            status, ctype, body = self.transport(url, self._headers(), self.timeout)
        except Exception:  # noqa: BLE001 — robots failures allow fetching
            status, body = 0, b""
        rules: _RulesList | None = None
        if status == 200 and body:
            parsed = RobotsPolicy.parse(body.decode("utf-8", "replace"))
            rules = parsed if isinstance(parsed, _RulesList) else None
        # remember() stores None for "fetched, no applicable rules" — that is
        # what permits every path on this host.
        self.robots.remember(host, rules)
        self.stats["requests"] += 1

    def _headers(self) -> dict:
        return {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml,application/json;q=0.9,*/*;q=0.8"}

    # -- public API -------------------------------------------------------
    def fetch(self, url: str, robots: bool = True) -> FetchResult:
        """GET ``url``. ``robots=False`` is reserved for documented public
        JSON APIs (Apple iTunes Search, YouTube Data API) where robots.txt is
        not the applicable access contract."""
        split = urllib.parse.urlsplit(url)
        if split.scheme not in ("http", "https") or not split.netloc:
            return FetchResult(url=url, status=0, body=b"", robots_ok=False)
        host = split.netloc.lower()
        if robots:
            scheme_host = f"{split.scheme}://{host}"
            self._load_robots(scheme_host)
            path = split.path or "/"
            if split.query:
                path += "?" + split.query
            if not self.robots.permitted(host, path):
                self.stats["robots_denied"] += 1
                return FetchResult(url=url, status=0, body=b"", robots_ok=False)
        self._throttle(host)
        self.stats["requests"] += 1
        try:
            status, ctype, body = self.transport(url, self._headers(), self.timeout)
        except Exception:  # noqa: BLE001 — collection must never crash a run
            self.stats["errors"] += 1
            return FetchResult(url=url, status=0, body=b"")
        body = (body or b"")[: self.max_bytes]
        self.stats["bytes"] += len(body)
        return FetchResult(
            url=url,
            status=status or 0,
            body=body,
            content_type=ctype or "",
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


def cache_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()
