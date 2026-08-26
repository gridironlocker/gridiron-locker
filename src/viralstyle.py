#!/usr/bin/env python3
"""Viralstyle connection layer.

Single place where every Viralstyle HTTP request goes through. The old scrapers
each created their own bare `requests.Session` with one User-Agent, no retries
and one URL shape - so a single blocked request silently produced an empty
catalogue and the daily refresh committed the damage.

This module gives the crawlers:

  * one pooled, keep-alive session with browser-like headers
  * automatic retry with exponential backoff on 429/5xx and transport errors
  * TLS-failure tolerance (some edges reset the handshake on the first hit)
  * multiple URL strategies per page, tried in order until one returns real HTML
  * a hard "did we actually get a product page?" validity check, so a captcha,
    a redirect to the storefront or an empty SPA shell is treated as a failure
    instead of as an empty collection
  * `health_check()` / `python src/viralstyle.py --check` for diagnosing the
    connection from any machine or from CI

Nothing here writes files or touches the built site.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import ssl
import sys
import time
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 v2 and v1 keep Retry in different places
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

BASE = "https://viralstyle.com"
STORE = "kebystore"

# Desktop UAs. Viralstyle serves a lighter SPA shell to unknown agents, so we
# look like a normal browser rather than like `python-requests/2.x`.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36",
]

DEFAULT_TIMEOUT = float(os.environ.get("VS_TIMEOUT", "45"))
MAX_ATTEMPTS = int(os.environ.get("VS_ATTEMPTS", "4"))
# Minimum bytes before we believe a response is a real rendered page.
MIN_HTML = int(os.environ.get("VS_MIN_HTML", "20000"))
MIN_STORE_HTML = int(os.environ.get("VS_MIN_STORE_HTML", "8000"))

# Substrings that mean "we were served an interstitial, not the page".
BLOCK_MARKERS = (
    "captcha",
    "cf-browser-verification",
    "access denied",
    "attention required",
    "request unsuccessful",
    "temporarily unavailable",
)


class VSError(RuntimeError):
    """Raised when Viralstyle cannot be reached or returns unusable content."""


class _TLSAdapter(HTTPAdapter):
    """Adapter that tolerates picky/older TLS edges.

    Some networks terminate the handshake when the client offers a very small
    or very modern cipher set. We relax the SECLEVEL and let OpenSSL negotiate
    anything from TLS 1.2 up, which fixes `SSL_ERROR_SYSCALL` style resets
    without disabling certificate verification.
    """

    def init_poolmanager(self, *a, **kw):
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        except ssl.SSLError:
            pass
        kw["ssl_context"] = ctx
        return super().init_poolmanager(*a, **kw)


def make_session(pool: int = 16) -> requests.Session:
    """A pooled session with browser headers, retries and TLS tolerance."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                  "image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
    })
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.5,
        status_forcelist=(408, 425, 429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    ad = _TLSAdapter(max_retries=retry, pool_connections=pool, pool_maxsize=pool)
    s.mount("https://", ad)
    s.mount("http://", ad)
    return s


SESSION = make_session()


def _looks_blocked(text: str) -> bool:
    head = text[:4000].lower()
    return any(m in head for m in BLOCK_MARKERS)


def fetch(url: str, *, session: requests.Session | None = None,
          min_len: int = MIN_HTML, attempts: int = MAX_ATTEMPTS,
          timeout: float = DEFAULT_TIMEOUT) -> str | None:
    """GET `url`, returning HTML only if it looks like a real rendered page.

    Returns None instead of raising so callers can fall through to the next
    URL strategy. Every failure reason is printed once, which is what makes a
    broken CI run diagnosable after the fact.
    """
    s = session or SESSION
    last = ""
    for i in range(attempts):
        try:
            r = s.get(url, timeout=timeout, allow_redirects=True)
        except requests.exceptions.SSLError as e:
            last = f"TLS {e.__class__.__name__}"
        except requests.exceptions.ConnectionError as e:
            last = f"conn {e.__class__.__name__}"
        except requests.exceptions.Timeout:
            last = "timeout"
        except Exception as e:  # noqa: BLE001 - crawler must never die here
            last = f"{e.__class__.__name__}: {e}"
        else:
            if r.status_code == 404:
                return None  # genuinely gone - do not burn retries
            if r.status_code != 200:
                last = f"HTTP {r.status_code}"
            elif _looks_blocked(r.text):
                last = "blocked/captcha interstitial"
            elif len(r.text) < min_len:
                last = f"short body ({len(r.text)}B < {min_len}B)"
            else:
                return r.text
        if i < attempts - 1:
            # jittered exponential backoff, and rotate identity on retry
            time.sleep(min(20.0, (2 ** i) + random.random() * 1.5))
            s.headers["User-Agent"] = random.choice(USER_AGENTS)
    print(f"  ! fetch failed {url} -> {last}")
    return None


def fetch_first(urls: Iterable[str], **kw) -> str | None:
    """Try several URL shapes for the same logical page; first good one wins."""
    for u in urls:
        html = fetch(u, **kw)
        if html:
            return html
    return None


# --------------------------------------------------------------- URL shapes
def product_urls(slug: str) -> list[str]:
    """Every known way to ask Viralstyle for a single campaign page."""
    return [
        f"{BASE}/{STORE}/{slug}?_escaped_fragment_=",
        f"{BASE}/{STORE}/{slug}",
        f"{BASE}/{STORE}/{slug}/",
    ]


def store_urls(path: str, page: int = 1) -> list[str]:
    """Every known way to ask for a collection listing page."""
    return [
        f"{BASE}/store/{STORE}/{path}/{page}?_escaped_fragment_=",
        f"{BASE}/store/{STORE}/{path}/{page}",
        f"{BASE}/store/{STORE}/{path}?page={page}",
    ]


def get_product(slug: str, *, session: requests.Session | None = None) -> str | None:
    return fetch_first(product_urls(slug), session=session, min_len=MIN_HTML)


def get_store_page(path: str, page: int = 1,
                   *, session: requests.Session | None = None) -> str | None:
    return fetch_first(store_urls(path, page), session=session, min_len=MIN_STORE_HTML)


# --------------------------------------------------------------- diagnostics
def health_check(sample_slug: str | None = None, sample_store: str = "Cleveland-Browns") -> dict:
    """Prove the connection end to end and report exactly where it breaks.

    Checked in order: DNS -> TCP -> TLS -> storefront HTML -> product HTML.
    """
    import socket

    out: dict = {"base": BASE, "steps": {}, "ok": False}

    # DNS
    try:
        ips = sorted({ai[4][0] for ai in socket.getaddrinfo("viralstyle.com", 443)})
        out["steps"]["dns"] = {"ok": True, "ips": ips}
    except Exception as e:
        out["steps"]["dns"] = {"ok": False, "error": str(e)}
        return out

    # TCP + TLS
    for ip in ips[:3]:
        try:
            with socket.create_connection((ip, 443), timeout=10) as sock:
                ctx = ssl.create_default_context()
                with ctx.wrap_socket(sock, server_hostname="viralstyle.com") as ts:
                    out["steps"]["tls"] = {"ok": True, "ip": ip,
                                           "version": ts.version(),
                                           "cipher": ts.cipher()[0]}
                    break
        except Exception as e:
            out["steps"]["tls"] = {"ok": False, "ip": ip,
                                   "error": f"{e.__class__.__name__}: {e}"}
    if not out["steps"].get("tls", {}).get("ok"):
        return out

    # Storefront HTML
    t0 = time.time()
    html = get_store_page(sample_store, 1)
    out["steps"]["store"] = {"ok": bool(html), "path": sample_store,
                             "bytes": len(html or ""), "secs": round(time.time() - t0, 1)}
    if not html:
        return out

    # Product HTML
    if sample_slug:
        t0 = time.time()
        phtml = get_product(sample_slug)
        out["steps"]["product"] = {"ok": bool(phtml), "slug": sample_slug,
                                   "bytes": len(phtml or ""),
                                   "secs": round(time.time() - t0, 1)}
        out["ok"] = bool(phtml)
    else:
        out["ok"] = True
    return out


def _default_sample_slug() -> str | None:
    """Pick a real slug out of the committed catalogue, if there is one."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        cols = json.load(open(os.path.join(root, "data/collections.json")))
        for c in cols.values():
            for p in c.get("products", []):
                if p.get("slug"):
                    return p["slug"]
    except Exception:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Viralstyle connection diagnostics")
    ap.add_argument("--check", action="store_true", help="run the health check")
    ap.add_argument("--slug", default=None, help="product slug to sample")
    ap.add_argument("--store", default="Cleveland-Browns", help="store path to sample")
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    a = ap.parse_args()

    if not a.check:
        ap.print_help()
        return 0

    res = health_check(a.slug or _default_sample_slug(), a.store)
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print(f"Viralstyle connection check -> {BASE}")
        for name, st in res["steps"].items():
            mark = "OK  " if st.get("ok") else "FAIL"
            extra = {k: v for k, v in st.items() if k != "ok"}
            print(f"  [{mark}] {name:<8} {extra}")
        print(f"\nresult: {'CONNECTED' if res['ok'] else 'NOT CONNECTED'}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
