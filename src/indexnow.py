#!/usr/bin/env python3
"""Submit genuinely changed URLs to IndexNow (Bing and partners).

Google deprecated its sitemap ping endpoint in June 2023 - for Google the
correct signal is an accurate <lastmod> in sitemap.xml plus Search Console,
which the build already produces. IndexNow covers the other participating
engines, but it should not be used as a repeated bulk-submission loop.

This script compares the current sitemap with the previous committed sitemap
(``HEAD^``). It submits only new URLs or URLs whose <lastmod> changed, with a
small cap. If no previous sitemap is available it skips rather than sending
an unbounded first-run batch.

Run after a rebuild/commit:  python3 src/indexnow.py
"""
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "src/config.json"), encoding="utf-8") as fh:
    CFG = json.load(fh)
DOMAIN = CFG["domain"].rstrip("/")
KEY = CFG.get("indexnow_key", "")
MAX_INDEXNOW_URLS = 50
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def sitemap_dates(xml_bytes):
    """Return ``{loc: lastmod}`` from a sitemap, or an empty mapping."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        print(f"Could not parse sitemap: {exc}")
        return {}
    return {
        (node.findtext("sm:loc", "", SITEMAP_NS) or "").strip():
        (node.findtext("sm:lastmod", "", SITEMAP_NS) or "").strip()
        for node in root.findall("sm:url", SITEMAP_NS)
        if (node.findtext("sm:loc", "", SITEMAP_NS) or "").strip()
    }


def previous_sitemap_dates():
    """Read the parent commit's sitemap without relying on filesystem mtimes."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD^:site/sitemap.xml"],
            cwd=ROOT, capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Could not read previous sitemap: {exc}")
        return {}
    if result.returncode != 0:
        return {}
    return sitemap_dates(result.stdout)


def changed_urls(current, previous):
    """New or source-date-changed URLs, ranked for the bounded payload."""
    changed = [u for u, stamp in current.items()
               if previous.get(u) != stamp]

    def rank(url):
        path = url.split(DOMAIN, 1)[-1]
        if path in ("", "/"):
            return (0, path)
        if "/shop/" not in path and "/guides/" not in path:
            return (1, path)
        if "/guides/" in path:
            return (2, path)
        return (3, path)

    return sorted(changed, key=rank)[:MAX_INDEXNOW_URLS]


def main():
    if not KEY:
        print("No indexnow_key in src/config.json - skipping.")
        return 0
    if "YOURNAME" in DOMAIN or "example" in DOMAIN:
        print(f"Domain still a placeholder ({DOMAIN}) - run src/set_site.py first. Skipping.")
        return 0

    sitemap = os.path.join(ROOT, "site/sitemap.xml")
    if not os.path.exists(sitemap):
        print("No sitemap.xml - run src/build.py first.")
        return 0
    with open(sitemap, "rb") as fh:
        current = sitemap_dates(fh.read())
    if not current:
        print("No valid sitemap URLs - skipping IndexNow.")
        return 0

    previous = previous_sitemap_dates()
    if not previous:
        print("No previous committed sitemap baseline - skipping bulk IndexNow submission.")
        return 0

    payload_urls = changed_urls(current, previous)
    if not payload_urls:
        print("No new or source-date-changed URLs - skipping IndexNow.")
        return 0
    print(f"IndexNow: {len(payload_urls)} changed URL(s) (cap {MAX_INDEXNOW_URLS}); "
          "unchanged URLs are not resubmitted")

    host = re.sub(r"^https?://", "", DOMAIN).split("/")[0]
    body = {
        "host": host,
        "key": KEY,
        "keyLocation": f"{DOMAIN}/{KEY}.txt",
        "urlList": payload_urls,
    }

    for endpoint in ("https://api.indexnow.org/IndexNow", "https://www.bing.com/indexnow"):
        try:
            r = requests.post(endpoint, json=body, timeout=45,
                              headers={"Content-Type": "application/json; charset=utf-8"})
            print(f"{endpoint} -> {r.status_code} ({len(payload_urls)} urls)")
            if r.status_code in (200, 202):
                return 0
        except Exception as exc:
            print(f"{endpoint} -> error {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
