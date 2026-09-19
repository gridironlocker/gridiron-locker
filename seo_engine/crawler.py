"""Local static-site crawler. Reads ``site/`` off disk — no network.

Produces a page inventory the auditor and decider share. Mirrors the path
conventions used by ``qa_audit.py`` so findings line up with the existing gate.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from .config import (
    EXCLUDED_PREFIXES,
    NOT_PAGES,
    SITE,
    domain,
)


@dataclass
class Page:
    path: str                 # URL path, e.g. /shop/foo/ or /michigan-wolverines-shirts/
    file: str                 # absolute filesystem path
    title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical: Optional[str] = None
    robots: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    h1: List[str] = field(default_factory=list)
    h2: List[str] = field(default_factory=list)
    image_alts: List[dict] = field(default_factory=list)  # {src, alt, missing}
    internal_links: List[str] = field(default_factory=list)
    has_json_ld: bool = False
    json_ld_types: List[str] = field(default_factory=list)
    noindex: bool = False
    word_count: int = 0
    kind: str = "other"       # home|collection|product|guide|static|stub|other

    def to_dict(self) -> dict:
        return asdict(self)


_HEAD_END = re.compile(r"</head>", re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_CANON = re.compile(r'<link[^>]+rel=["\']canonical["\'][^>]*>', re.I)
_HREF = re.compile(r'href=["\']([^"\']*)["\']', re.I)
_META = re.compile(
    r"<meta\b([^>]*)>", re.I
)
_ATTR = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*["\']([^"\']*)["\']')
_H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)
_H2 = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
_IMG = re.compile(r"<img\b([^>]*)>", re.I)
_A = re.compile(r"<a\b([^>]*)>", re.I)
_LD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.S | re.I,
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _strip(html_frag: str) -> str:
    return _WS.sub(" ", _html.unescape(_TAG.sub(" ", html_frag or ""))).strip()


def _meta_map(head: str) -> dict:
    out = {}
    for m in _META.finditer(head):
        attrs = {k.lower(): v for k, v in _ATTR.findall(m.group(1))}
        key = attrs.get("name") or attrs.get("property") or attrs.get("http-equiv")
        if key and "content" in attrs:
            out[key.lower()] = attrs["content"]
    return out


def _classify(path: str, noindex: bool) -> str:
    if path in ("/", "/index.html"):
        return "home"
    if path.startswith("/shop/"):
        return "stub" if noindex else "product"
    if any(path.rstrip("/").endswith(s) or f"/{s}/" in path
           for s in (
               "cleveland-browns-shirts", "dallas-cowboys-shirts",
               "green-bay-packers-shirts", "michigan-wolverines-shirts",
           )):
        return "collection"
    if path.startswith("/guides/"):
        return "guide"
    if path.rstrip("/").split("/")[-1] in {
        "about", "contact", "faq", "privacy", "shipping", "size-guide",
        "search", "drops", "collections", "2026-season", "fan-trend-index",
    }:
        return "static"
    return "other"


def _is_excluded(rel: str) -> bool:
    if any(rel.startswith(p) for p in EXCLUDED_PREFIXES):
        return True
    base = os.path.basename(rel)
    return any(base.startswith(tok) for tok in NOT_PAGES)


def iter_page_files(site: Path = SITE) -> Iterable[tuple[str, Path]]:
    """Yield (url_path, absolute_file) for every public HTML page."""
    site = Path(site)
    for base, _dirs, files in os.walk(site):
        for f in files:
            if not f.endswith(".html"):
                continue
            full = Path(base) / f
            rel = "/" + full.relative_to(site).as_posix()
            if _is_excluded(rel):
                continue
            url = re.sub(r"/index\.html$", "/", rel)
            if url.endswith(".html") and not url.endswith("404.html"):
                # bare page.html → keep; 404 is special
                pass
            yield url, full


def parse_page(url_path: str, file_path: Path, site_domain: str | None = None) -> Page:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    head = text[: lower.find("</head>") + 7] if "</head>" in lower else text[:8000]
    metas = _meta_map(head)

    title_m = _TITLE.search(head)
    title = _strip(title_m.group(1)) if title_m else None

    canon = None
    cm = _CANON.search(head)
    if cm:
        hm = _HREF.search(cm.group(0))
        canon = hm.group(1) if hm else None

    robots = metas.get("robots")
    noindex = bool(robots and "noindex" in robots.lower())

    h1s = [_strip(h) for h in _H1.findall(text)]
    h2s = [_strip(h) for h in _H2.findall(text)]

    image_alts = []
    for im in _IMG.finditer(text):
        attrs = {k.lower(): v for k, v in _ATTR.findall(im.group(1))}
        src = attrs.get("src", "")
        if "alt" not in attrs:
            image_alts.append({"src": src, "alt": None, "missing": True})
        else:
            image_alts.append({
                "src": src,
                "alt": attrs.get("alt") or "",
                "missing": attrs.get("alt", None) is None,
            })

    internal = []
    host = (site_domain or domain()).replace("https://", "").replace("http://", "")
    for am in _A.finditer(text):
        attrs = {k.lower(): v for k, v in _ATTR.findall(am.group(1))}
        href = attrs.get("href") or ""
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if href.startswith("http"):
            if host not in href:
                continue
            parsed = urlparse(href)
            href = parsed.path or "/"
        if not href.startswith("/"):
            continue
        internal.append(href.split("?")[0].split("#")[0])

    ld_types = []
    has_ld = False
    for block in _LD.findall(text):
        has_ld = True
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if isinstance(it, dict):
                t = it.get("@type")
                if isinstance(t, list):
                    ld_types.extend(str(x) for x in t)
                elif t:
                    ld_types.append(str(t))

    body_text = _strip(text)
    words = re.findall(r"[A-Za-z0-9']+", body_text)

    return Page(
        path=url_path,
        file=str(file_path),
        title=title,
        meta_description=metas.get("description"),
        canonical=canon,
        robots=robots,
        og_title=metas.get("og:title"),
        og_description=metas.get("og:description"),
        og_image=metas.get("og:image"),
        h1=h1s,
        h2=h2s,
        image_alts=image_alts,
        internal_links=internal,
        has_json_ld=has_ld,
        json_ld_types=ld_types,
        noindex=noindex,
        word_count=len(words),
        kind=_classify(url_path, noindex),
    )


def crawl(site: Path = SITE) -> List[Page]:
    """Full public-page inventory."""
    site_domain = domain()
    pages = []
    for url, full in iter_page_files(site):
        try:
            pages.append(parse_page(url, full, site_domain))
        except Exception as exc:  # pragma: no cover - defensive
            pages.append(Page(
                path=url, file=str(full), title=f"[parse-error: {exc}]", kind="other",
            ))
    return sorted(pages, key=lambda p: p.path)
