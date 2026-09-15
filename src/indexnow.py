#!/usr/bin/env python3
"""Submit changed URLs to IndexNow (Bing, Yandex, Naver, Seznam).

Google deprecated its sitemap ping endpoint in June 2023 - for Google the
correct signal is an accurate <lastmod> in sitemap.xml plus Search Console,
which the build already produces. IndexNow covers the rest and is instant.

    python3 src/indexnow.py              # submit the whole sitemap (manual run)
    python3 src/indexnow.py --changed    # submit only what this build changed

``--changed`` reads data/build-manifest.json, which src/build.py writes at the
end of every build: a URL is "changed" when its lastmod equals the build date,
i.e. when its content fingerprint moved. That keeps the twice-daily refresh and
every deploy from re-announcing 108 unchanged pages, which is the kind of noise
that gets a domain's IndexNow submissions rate-limited.

Run after a rebuild:  python3 src/indexnow.py --changed
"""
import argparse
import json
import os
import re
import sys

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

with open(sitemap, encoding="utf-8") as fh:
    xml = fh.read()
urls = re.findall(r"<loc>(.*?)</loc>", xml)


def changed_urls():
    """Sitemap URLs this build re-dated, per the build manifest."""
    manifest = os.path.join(ROOT, "data/build-manifest.json")
    if os.path.isfile(manifest):
        try:
            with open(manifest, encoding="utf-8") as fh:
                data = json.load(fh)
        except (ValueError, OSError) as e:
            print(f"manifest unreadable ({e}) - falling back to sitemap dates")
        else:
            built = data.get("built")
            pages = data.get("pages", {})
            return [u for u, e in pages.items() if e.get("lastmod") == built]
    # No manifest: the newest <lastmod> in the sitemap is the build date, so
    # treat that as "changed" - the same set, derived from the artefact.
    stamps = re.findall(r"<lastmod>(.*?)</lastmod>", xml)
    if not stamps:
        return []
    newest = max(stamps)
    pairs = re.findall(r"<loc>(.*?)</loc><lastmod>(.*?)</lastmod>", xml)
    return [u for u, d in pairs if d == newest]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--changed", action="store_true",
                    help="submit only URLs whose content changed in the latest build")
    args = ap.parse_args()

    if args.changed:
        urls_to_send = changed_urls()
        if not urls_to_send:
            print("IndexNow: nothing changed in this build - nothing submitted.")
            return
    else:
        # a full submission: the top of the site first, the long tail after
        priority = [u for u in urls
                    if u.rstrip("/").count("/") <= 4 or "2026-season" in u]
        urls_to_send = (priority + [u for u in urls if u not in priority])[:9000]

    body = {
        "host": host,
        "key": KEY,
        "keyLocation": f"{DOMAIN}/{KEY}.txt",
        "urlList": urls_to_send,
    }

    import requests
    for endpoint in ("https://api.indexnow.org/IndexNow", "https://www.bing.com/indexnow"):
        try:
            r = requests.post(endpoint, json=body, timeout=45,
                              headers={"Content-Type": "application/json; charset=utf-8"})
            print(f"{endpoint} -> {r.status_code} ({len(urls_to_send)} urls)")
            if r.status_code in (200, 202):
                break
        except Exception as e:
            print(f"{endpoint} -> error {e}")


if __name__ == "__main__":
    main()
