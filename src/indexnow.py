#!/usr/bin/env python3
"""Submit changed URLs to IndexNow (Bing, Yandex, Naver, Seznam).

Google deprecated its sitemap ping endpoint in June 2023 - for Google the
correct signal is an accurate <lastmod> in sitemap.xml plus Search Console,
which the build already produces. IndexNow covers the rest and is instant.

Run after a rebuild:  python3 src/indexnow.py
"""
import json, os, re, sys
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "src/config.json")))
DOMAIN = CFG["domain"].rstrip("/")
KEY = CFG.get("indexnow_key", "")

if not KEY:
    print("No indexnow_key in src/config.json - skipping.")
    sys.exit(0)

if "YOURNAME" in DOMAIN or "example" in DOMAIN:
    print(f"Domain still a placeholder ({DOMAIN}) - run src/set_site.py first. Skipping.")
    sys.exit(0)

host = re.sub(r"^https?://", "", DOMAIN).split("/")[0]

sitemap = os.path.join(ROOT, "site/sitemap.xml")
if not os.path.exists(sitemap):
    print("No sitemap.xml - run src/build.py first.")
    sys.exit(0)

urls = re.findall(r"<loc>(.*?)</loc>", open(sitemap, encoding="utf-8").read())

# Prioritise the pages that actually change: home, collections, season hub, feed.
priority = [u for u in urls if u.rstrip("/").count("/") <= 4 or "2026-season" in u]
payload_urls = (priority + [u for u in urls if u not in priority])[:9000]

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
            break
    except Exception as e:
        print(f"{endpoint} -> error {e}")
