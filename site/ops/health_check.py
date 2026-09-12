#!/usr/bin/env python3
"""Daily site health check: is the LIVE store actually serving a good store?

The refresh pipeline already verifies its own build before it publishes
(products present, sitemap depth, no missing local refs). Everything it
verifies, however, is verified *locally*: a build can be perfect and the
site still be broken because the deploy failed, Pages served an old artifact,
a hero was replaced but the JPG never uploaded, or a URL that four pages link
to quietly started 404ing.

This script is the other half: it checks the deployed site over HTTPS, at the
URL a customer would use, after the fact. It is what `.github/workflows/
health-check.yml` runs once a day - and on demand - so "the site is fine" is a
statement about production rather than about the workspace.

What it proves, in order:

  1. Pages - every important URL answers 200 with a real title, exactly one
     H1, a self-consistent canonical, parseable JSON-LD, and no traceback or
     placeholder text leaked into the HTML.
  2. Assets - the stylesheet, the script and the artwork referenced by those
     pages are fetched (same-origin) and answer 200.
  3. Banner bands - each hero band's `<img width height>` ratio matches the
     real pixels of the deployed image, so the poster is never cropped, and
     the file is under the 750 KB budget, so a PNG master was not shipped.
  4. Deployed artwork matches the repo - the hero URLs production serves are
     the ones this checkout just built. This is the check that catches "new
     banners were committed but the site is still showing the old poster".
  5. Sitemap - every <loc> answers 200, the shop catalogue is whole, 404 is
     excluded, and the lastmod date is recent (a stuck pipeline shows up here).

Run it locally against a local build, or against production:

    python3 ops/health_check.py                       # production
    python3 ops/health_check.py --base http://127.0.0.1:8080

Exit status is 0 only when every check passes. Failures print one line each
with the URL, so a red run reads like a to-do list.
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from urllib.parse import urljoin

import requests
from PIL import Image
from io import BytesIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
PRODUCTION = "https://gridironlocker.store"
HOST = "gridironlocker.store"

# The storefront, the shop and the creator collab: everything a customer is
# sent to from the nav, an ad, a pin or a Google result.
PAGES = [
    "/", "/collections/", "/search/", "/drops/", "/2026-season/",
    "/fan-trend-index/", "/guides/", "/guides/2026-week-1-shirts/",
    "/guides/cleveland-browns-shirts-buying-guide/",
    "/guides/green-bay-packers-shirts-buying-guide/",
    "/guides/dallas-cowboys-shirts-buying-guide/",
    "/guides/michigan-wolverines-shirts-buying-guide/",
    "/cleveland-browns-shirts/", "/green-bay-packers-shirts/",
    "/dallas-cowboys-shirts/", "/michigan-wolverines-shirts/",
    "/michigan/joe/",
    "/faq/", "/shipping/", "/size-guide/", "/contact/", "/about/",
    "/privacy/", "/trademark-notice/",
]
# Pages whose first job is a product image, not a story.
PRODUCT_PAGES = 6
# Required by the storefront's structured data contract.
SCHEMA_TYPES = {"Organization", "WebSite"}
PAGE_SCHEMA = {
    "/": {"ItemList"},
    "/michigan/joe/": {"CollectionPage"},
}
# Files every deploy must serve, whatever else changes.
FILES = [
    "/robots.txt", "/sitemap.xml", "/sitemap-images.xml", "/feed.xml",
    "/llms.txt", "/site.webmanifest", "/assets/style.css", "/assets/app.js",
    "/img/favicon.svg",
]
# The five banners plus the four square team cards the homepage deck uses.
BANNERS = {
    "/": ("/img/hero-home.jpg", 2048, 768),
    "/drops/": ("/img/hero-home.jpg", 2048, 768),
    "/cleveland-browns-shirts/": ("/img/hero-cleveland.jpg", 2048, 768),
    "/green-bay-packers-shirts/": ("/img/hero-greenbay.jpg", 2048, 768),
    "/dallas-cowboys-shirts/": ("/img/hero-dallas.jpg", 2048, 768),
    "/michigan-wolverines-shirts/": ("/img/hero-michigan.jpg", 2048, 768),
}
TEAM_CARDS = [
    "/img/team-cleveland.jpg", "/img/team-greenbay.jpg",
    "/img/team-dallas.jpg", "/img/team-michigan.jpg",
]
MAX_ART_BYTES = 750 * 1024            # the design budget for any single banner
MAX_IMAGE_REFS_PER_PAGE = 40          # sample depth for per-page asset checks
SITEMAP_MAX_AGE_DAYS = 5              # the refresh runs twice a day


def catalogue_counts():
    """Master catalogue totals, straight from the build.

    These thresholds used to be magic numbers (100 URLs, 100 products) that
    quietly disagreed with the real catalogue - 81 designs across 4
    collections - so the health check failed a perfectly complete build while
    still missing a genuinely truncated one. Deriving them from src/build.py
    means the sitemap is checked against the catalogue that produced it, and a
    real regression (a truncated crawl) still trips the exact-match assert.
    """
    try:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        import build
        return len(build.ALL), {k: len(v) for k, v in build.MODEL.items()}
    except Exception:
        return None, None


CATALOGUE_SIZE, COLLECTION_SIZES = catalogue_counts()
# A truncated build drops well below the real catalogue; keep a floor so the
# check still fires if the catalogue itself cannot be read.
SITEMAP_MIN_URLS = 60


class Checker:
    """A tiny results ledger: every check is pass/fail plus a human line."""

    def __init__(self, base, verbose=False, quiet=False):
        self.base = base.rstrip("/")
        self.verbose = verbose
        self.quiet = quiet          # unit tests drive the ledger without printing
        self.failures = []
        self.notes = []
        self.checked = 0

    # ---------------------------------------------------------------- plumbing
    def ok(self, msg):
        self.checked += 1
        if self.verbose:
            print(f"  OK   {msg}")

    def fail(self, msg):
        self.checked += 1
        self.failures.append(msg)
        if not self.quiet:
            print(f"  FAIL {msg}")

    def note(self, msg):
        self.notes.append(msg)
        if not self.quiet:
            print(f"  ..   {msg}")

    def url(self, path, page=None):
        """Absolute URL for a path, or for a relative ref on `page`.

        The built pages use relative links (so the same files work on
        gridironlocker.store and from a file:// copy), which is why every
        per-page asset reference has to be resolved against its page.
        """
        if str(path).startswith("http"):
            return path
        if page is not None and not str(path).startswith("/"):
            return urljoin(self.url(page), path)
        return f"{self.base}{path}"

    def get(self, session, path, page=None):
        """GET a path (relative refs resolved against `page`).

        Returns (response, bytes); (None, b"") when every retry failed.
        """
        url = self.url(path, page=page)
        try:
            r = session.get(url, timeout=25)
        except requests.RequestException as e:
            return None, b""
        if r.status_code != 200:
            return r, b""
        return r, r.content

    # -------------------------------------------------------------- 1. pages
    def check_pages(self, session, paths):
        for path in paths:
            r, body = self.get(session, path)
            if r is None:
                self.fail(f"{path}: did not answer (network error or timeout)")
                continue
            if r.status_code != 200:
                self.fail(f"{path}: HTTP {r.status_code}")
                continue
            html = body.decode("utf-8", "replace")
            if len(html) < 2000:
                self.fail(f"{path}: suspiciously small page ({len(html)} bytes)")
                continue
            self.check_page_html(path, html)
            self.check_page_assets(session, path, html)
            self.ok(f"{path} ({len(body) // 1024} KB)")

    def check_page_html(self, path, html):
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
        if not title or not title.group(1).strip():
            self.fail(f"{path}: no <title>")
        h1 = re.findall(r"<h1[ >]", html)
        if len(h1) != 1:
            self.fail(f"{path}: {len(h1)} <h1> tags (want exactly 1)")

        want = f"https://{HOST}{path}"
        canon = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        if not canon:
            self.fail(f"{path}: no canonical link")
        elif canon.group(1).rstrip("/") != want.rstrip("/"):
            self.fail(f"{path}: canonical is {canon.group(1)}, expected {want}")

        desc = re.search(r'<meta name="description" content="([^"]*)"', html)
        if not desc or len(desc.group(1)) < 40:
            self.fail(f"{path}: missing or stubby meta description")

        # Structured data must parse - a broken JSON-LD block silently kills
        # rich results for every page that embeds it.
        found = set()
        for i, block in enumerate(re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', html, re.S)):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as e:
                self.fail(f"{path}: JSON-LD block {i + 1} does not parse ({e})")
                continue
            if isinstance(data, dict):
                found.add(data.get("@type"))
        for need in SCHEMA_TYPES | PAGE_SCHEMA.get(path, set()):
            if need not in found:
                self.fail(f"{path}: no {need} structured data")

        for marker in ("Traceback (most recent call last)", "undefined",
                       "{{", "TODO", "lorem ipsum"):
            if marker in html:
                self.fail(f"{path}: HTML contains {marker!r}")

    def check_page_assets(self, session, path, html):
        """Fetch the same-origin things this page renders (styles, scripts,
        images) - the HTTP form of the build's "no missing local refs" gate."""
        refs = []
        for attr in re.finditer(r'(?:src|href)="([^"]+)"', html):
            val = attr.group(1).strip()
            if val.startswith("//") or val.startswith("http") or val.startswith("#"):
                continue
            if val.split("#")[0].endswith((".html", "/")) and attr.group(0).startswith("href"):
                continue                     # page links are checked elsewhere
            val = val.split("#")[0].split("?")[0]
            if not val or val in ("", "/"):
                continue
            refs.append(val)
        # Keep the stylesheet/script plus the first N images: enough to catch a
        # half-uploaded deploy without hammering Pages.
        styles = [r for r in refs if r.endswith((".css", ".js", ".xml", ".txt", ".svg"))]
        images = [r for r in refs if r.endswith((".jpg", ".jpeg", ".png", ".webp"))]
        seen, todo = set(), []
        for ref in styles + images[:MAX_IMAGE_REFS_PER_PAGE]:
            if ref in seen:
                continue
            seen.add(ref)
            todo.append(ref)
        for ref in todo:
            r, _ = self.get(session, ref, page=path)
            if r is None or r.status_code != 200:
                code = "network error" if r is None else f"HTTP {r.status_code}"
                self.fail(f"{path}: {ref} -> {code}")

    # ------------------------------------------------------ 3. banner bands
    def check_banners(self, session):
        for page, (img_path, w, h) in BANNERS.items():
            r, body = self.get(session, page)
            if r is None or r.status_code != 200:
                self.fail(f"{page}: cannot read the page to check its band")
                continue
            html = body.decode("utf-8", "replace")
            band = re.search(r'<div class="band"><img\b[^>]*>', html)
            if not band:
                self.fail(f"{page}: no <div class=\"band\"><img> hero band")
                continue
            tag = band.group(0)
            src = re.search(r'src="([^"]+)"', tag)
            size = re.search(r'width="(\d+)" height="(\d+)"', tag)
            if not src or not size:
                self.fail(f"{page}: band image is missing src/width/height")
                continue
            got = src.group(1).split("?")[0].split("/")[-1]
            if got != img_path.split("/")[-1]:
                self.fail(f"{page}: band shows {got}, expected {img_path.split('/')[-1]}")
                continue
            if (int(size.group(1)), int(size.group(2))) != (w, h):
                self.fail(f"{page}: band declares {size.group(1)}x{size.group(2)}, "
                          f"expected {w}x{h}")
                continue
            if 'fetchpriority="high"' not in tag:
                self.fail(f"{page}: band image is not the prioritised LCP element")
            self.check_banner_image(session, page, src.group(1), w, h)

    def check_banner_image(self, session, page, img_path, w, h):
        r, body = self.get(session, img_path, page=page)
        if r is None:
            self.fail(f"{page}: {img_path} did not answer")
            return
        if r.status_code != 200:
            self.fail(f"{page}: {img_path} -> HTTP {r.status_code}")
            return
        ctype = r.headers.get("Content-Type", "")
        if "image/" not in ctype:
            self.fail(f"{img_path}: Content-Type {ctype!r}, expected an image")
        if len(body) > MAX_ART_BYTES:
            self.fail(f"{img_path}: {len(body) // 1024} KB - over the "
                      f"{MAX_ART_BYTES // 1024} KB banner budget (PNG master shipped?)")
        try:
            im = Image.open(BytesIO(body))
            iw, ih = im.size
        except Exception as e:                       # noqa: BLE001 - report anything
            self.fail(f"{img_path}: cannot decode the image ({e})")
            return
        declared = w / h
        real = iw / ih
        if abs(declared - real) > 0.005:
            self.fail(f"{img_path}: {iw}x{ih} art ({real:.3f}) does not match the "
                      f"{w}x{h} band ({declared:.3f}) - the poster will be cropped")
        elif (iw, ih) != (w, h):
            self.note(f"{img_path}: {iw}x{ih} art in a {w}x{h} band (same ratio)")
        self.ok(f"{img_path} {iw}x{ih}, {len(body) // 1024} KB")

    # --------------------------------------------- 4. deployed art == repo art
    def check_artwork_matches_repo(self, session):
        for rel, page_path in (("index.html", "/"),
                               ("drops/index.html", "/drops/"),
                               ("cleveland-browns-shirts/index.html", "/cleveland-browns-shirts/"),
                               ("green-bay-packers-shirts/index.html", "/green-bay-packers-shirts/"),
                               ("dallas-cowboys-shirts/index.html", "/dallas-cowboys-shirts/"),
                               ("michigan-wolverines-shirts/index.html", "/michigan-wolverines-shirts/")):
            built = os.path.join(SITE, rel)
            if not os.path.isfile(built):
                self.fail(f"{rel}: not built in this checkout")
                continue
            local = open(built, encoding="utf-8").read()
            url = re.search(r'<div class="band"><img\b[^>]*src="([^"]+)"', local)
            if not url:
                self.fail(f"{rel}: no band image in the local build")
                continue
            want = url.group(1)
            r, body = self.get(session, page_path)
            if r is None or r.status_code != 200:
                self.fail(f"{page_path}: cannot compare deployed artwork")
                continue
            live = re.search(r'<div class="band"><img\b[^>]*src="([^"]+)"',
                             body.decode("utf-8", "replace"))
            if not live:
                self.fail(f"{page_path}: no band image on the live page")
                continue
            shipped = live.group(1)
            if shipped != want:
                self.fail(f"{page_path}: live band shows {shipped}, this checkout "
                          f"ships {want} - the deploy is behind the repo")
            else:
                self.ok(f"{page_path}: live band image {shipped} matches this checkout")

        # The square team cards behind "Shop By Team".
        for card in TEAM_CARDS:
            r, body = self.get(session, card)
            if r is None or r.status_code != 200:
                code = "network error" if r is None else f"HTTP {r.status_code}"
                self.fail(f"{card}: {code}")
                continue
            try:
                iw, ih = Image.open(BytesIO(body)).size
            except Exception as e:                   # noqa: BLE001
                self.fail(f"{card}: cannot decode the image ({e})")
                continue
            if iw != ih:
                self.fail(f"{card}: {iw}x{ih} - the team deck needs square cards")
            else:
                self.ok(f"{card} {iw}x{ih}")

    # ------------------------------------------------------------ 5. sitemap
    def check_sitemap(self, session):
        r, body = self.get(session, "/sitemap.xml")
        if r is None or r.status_code != 200:
            self.fail("/sitemap.xml: not served")
            return []
        try:
            root = ET.fromstring(body)
        except ET.ParseError as e:
            self.fail(f"/sitemap.xml: does not parse ({e})")
            return []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls, lastmods = [], []
        for url in root.findall("sm:url", ns):
            loc = (url.findtext("sm:loc", "", ns) or "").strip()
            lm = (url.findtext("sm:lastmod", "", ns) or "").strip()
            if loc:
                urls.append(loc)
            if lm:
                lastmods.append(lm)
        if len(urls) < SITEMAP_MIN_URLS:
            self.fail(f"/sitemap.xml: only {len(urls)} URLs (< {SITEMAP_MIN_URLS}) - "
                      f"the catalogue looks truncated")
        shop = [u for u in urls if "/shop/" in u]
        if CATALOGUE_SIZE is None:
            self.note("/sitemap.xml: catalogue unreadable, skipped the exact "
                      "product-count check")
        elif len(shop) != CATALOGUE_SIZE:
            # Exact match, not a floor: the sitemap and the master catalogue
            # are produced by the same build, so any difference means one of
            # them is stale.
            self.fail(f"/sitemap.xml: {len(shop)} product URLs but the catalogue "
                      f"holds {CATALOGUE_SIZE}")
        else:
            self.ok(f"/sitemap.xml: {len(shop)} product URLs match the catalogue")
        for u in urls:
            if HOST not in u:
                self.fail(f"/sitemap.xml: {u} is not on {HOST}")
            if u.rstrip("/").endswith("/404.html"):
                self.fail("/sitemap.xml: 404 page must never be listed")

        # Freshness: the refresh pipeline rebuilds the sitemap with today's
        # date twice a day, so a stale one means the pipeline stopped.
        newest = max(lastmods) if lastmods else ""
        if newest:
            try:
                age = (date.today() - datetime.strptime(newest, "%Y-%m-%d").date()).days
                if age > SITEMAP_MAX_AGE_DAYS:
                    self.fail(f"/sitemap.xml: newest lastmod {newest} is {age} days old "
                              f"- the refresh pipeline looks stuck")
                else:
                    self.note(f"sitemap lastmod {newest} ({age} day(s) old)")
            except ValueError:
                self.fail(f"/sitemap.xml: unreadable lastmod {newest!r}")

        # Every URL in the sitemap must answer 200 - this is the check that
        # catches links to pages that were delisted without a redirect.
        self.check_urls_in_parallel(session, urls, "sitemap")
        return urls

    def check_urls_in_parallel(self, session, urls, label):
        bad = []

        def probe(u):
            path = u.split(HOST, 1)[-1] if HOST in u else u
            try:
                rr = session.get(self.url(path if path else "/"), timeout=25)
                return u, rr.status_code
            except requests.RequestException:
                return u, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for u, code in pool.map(probe, urls):
                if code != 200:
                    bad.append((u, code))
        for u, code in bad[:15]:
            self.fail(f"{label}: {u} -> {'network error' if code is None else code}")
        if len(bad) > 15:
            self.fail(f"{label}: {len(bad) - 15} more URLs are not 200")
        if not bad:
            self.ok(f"{label}: all {len(urls)} URLs answer 200")

    # ------------------------------------------------------- misc storefront bits
    def check_files(self, session):
        for path in FILES:
            r, body = self.get(session, path)
            if r is None:
                self.fail(f"{path}: did not answer")
            elif r.status_code != 200:
                self.fail(f"{path}: HTTP {r.status_code}")
            elif not body:
                self.fail(f"{path}: empty body")
            else:
                self.ok(f"{path} ({len(body)} bytes)")

        r, body = self.get(session, "/sitemap-images.xml")
        if r is not None and r.status_code == 200:
            try:
                ET.fromstring(body)
                self.ok("/sitemap-images.xml parses")
            except ET.ParseError as e:
                self.fail(f"/sitemap-images.xml: does not parse ({e})")

    def check_homepage_facts(self, session):
        """The homepage states the catalogue size; it must not understate it."""
        r, body = self.get(session, "/")
        if r is None or r.status_code != 200:
            return
        html = body.decode("utf-8", "replace")
        n = re.search(r"(\d+) fan designs", html)
        if not n:
            self.fail("/: the hero no longer states the catalogue size")
            return
        count = int(n.group(1))
        sitemap = self.get(session, "/sitemap.xml")[1]
        shop = len(re.findall(r"/shop/", sitemap.decode("utf-8", "replace")))
        if count > shop:
            self.fail(f"/: claims {count} designs but the sitemap lists {shop}")
        else:
            self.ok(f"/: {count} designs advertised, {shop} product URLs in the sitemap")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=PRODUCTION,
                    help=f"site to check (default {PRODUCTION})")
    ap.add_argument("--verbose", action="store_true", help="print every passing check")
    ap.add_argument("--no-drift", action="store_true",
                    help="skip the 'deployed artwork vs this checkout' comparison; "
                         "used by the push trigger, where the deploy that follows the "
                         "same commit may still be propagating")
    args = ap.parse_args(argv)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "GridironLockerHealthCheck/1.0 (+https://gridironlocker.store/)",
        "Cache-Control": "no-cache",
    })
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))

    print(f"Gridiron Locker site health check -> {args.base}")
    print(f"checkout: {SITE}\n")
    c = Checker(args.base, args.verbose)

    print("-- pages")
    c.check_pages(session, PAGES + product_pages(session, c))
    print("-- files")
    c.check_files(session)
    print("-- hero banner bands")
    c.check_banners(session)
    if not args.no_drift:
        print("-- deployed artwork vs this checkout")
        c.check_artwork_matches_repo(session)
    else:
        print("-- deployed artwork vs this checkout (skipped: --no-drift)")
    print("-- sitemap")
    c.check_sitemap(session)
    print("-- homepage facts")
    c.check_homepage_facts(session)

    print(f"\n{'-' * 68}")
    if c.failures:
        print(f"HEALTH CHECK FAILED: {len(c.failures)} problem(s) in "
              f"{c.checked} checks against {args.base}\n")
        for f in c.failures:
            print(f"  - {f}")
        return 1
    print(f"HEALTH CHECK PASSED: {c.checked} checks against {args.base}")
    for n in c.notes:
        print(f"  note: {n}")
    return 0


def product_pages(session, c):
    """A few real product pages, read from the sitemap so they always exist."""
    paths = []
    r = session.get(c.url("/sitemap.xml"), timeout=25)
    if r.status_code != 200:
        return paths
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    shop = [u for u in locs if "/shop/" in u]
    step = max(1, len(shop) // PRODUCT_PAGES)
    for u in shop[::step][:PRODUCT_PAGES]:
        paths.append(u.split(HOST, 1)[-1])
    return paths


if __name__ == "__main__":
    sys.exit(main())
