#!/usr/bin/env python3
"""Nudge Google for indexing after a deploy.

Two independent jobs, neither fatal to the workflow:

1) GSC live URL Inspection - only runs if GSC_SA_JSON (a service-account key,
   written to a file by the workflow) is present. Determines which product
   pages changed in this push (falling back to the newest slugs in the
   sitemap when the diff is empty, e.g. after a rebase) and asks the URL
   Inspection API to do a *live* inspection of each one, capped at 50 URLs.
   This doesn't index anything by itself, but it forces Google to look and
   surfaces verdict/coverageState in the run log.

2) WebSub (PubSubHubbub) feed ping - always runs. Tells the public hub that
   site/feed.xml changed so any hub subscriber (including Google's own feed
   consumers) refetches it immediately instead of on the next poll.

Run after a rebuild + deploy:  python3 src/nudge_google.py
"""
import json, os, re, subprocess, sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "src/config.json")))
DOMAIN = CFG["domain"].rstrip("/")

GSC_SITE_URL = f"{DOMAIN}/"
HUB_URL = "https://pubsubhubbub.appspot.com"
MAX_URLS = 50


def gsc_inspect():
    """Live URL Inspection API nudge for changed /shop/<slug>/ product pages."""
    key_path = os.environ.get("GSC_SA_JSON_PATH")
    if not key_path or not os.path.isfile(key_path):
        print("GSC_SA_JSON not set - skipping")
        return

    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError:
        print("google-auth not installed - skipping GSC inspection")
        return

    scopes = ["https://www.googleapis.com/auth/webmasters"]
    try:
        creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
        creds.refresh(GoogleAuthRequest())
    except Exception as e:
        print(f"GSC credential load/refresh failed: {e} - skipping GSC inspection")
        return

    urls = changed_product_urls()
    if not urls:
        print("No product URLs to inspect - skipping GSC inspection")
        return

    urls = urls[:MAX_URLS]
    print(f"GSC live inspection: {len(urls)} url(s)")

    endpoint = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }
    for url in urls:
        body = {
            "inspectionUrl": url,
            "siteUrl": GSC_SITE_URL,
            "inspectionType": "INDEX_STATUS",
            "liveInspection": True,
        }
        try:
            r = requests.post(endpoint, headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                result = r.json().get("inspectionResult", {})
                idx = result.get("indexStatusResult", {})
                verdict = idx.get("verdict", "?")
                coverage = idx.get("coverageState", "?")
                print(f"  {url} -> verdict={verdict} coverageState={coverage}")
            else:
                print(f"  {url} -> HTTP {r.status_code}: {r.text[:300]}")
        except Exception as e:
            print(f"  {url} -> error {e}")


def changed_product_urls():
    """Product URLs touched by this push, mapped from site/shop/<slug>/index.html."""
    slugs = []
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main", "HEAD", "--", "site/shop/*/index.html"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        for line in out.stdout.splitlines():
            m = re.match(r"site/shop/([^/]+)/index\.html$", line.strip())
            if m:
                slugs.append(m.group(1))
    except Exception as e:
        print(f"git diff for changed products failed: {e}")

    if slugs:
        print(f"changed product slugs (git diff): {len(slugs)}")
    else:
        print("git diff empty (e.g. pushed via rebase) - falling back to newest sitemap slugs")
        sitemap = os.path.join(ROOT, "site/sitemap.xml")
        if os.path.isfile(sitemap):
            text = open(sitemap, encoding="utf-8").read()
            shop_urls = [u for u in re.findall(r"<loc>(.*?)</loc>", text) if "/shop/" in u]
            for u in shop_urls[-10:]:
                m = re.search(r"/shop/([^/]+)/?$", u.rstrip("/"))
                if m:
                    slugs.append(m.group(1))

    seen = set()
    urls = []
    for s in slugs:
        if s in seen:
            continue
        seen.add(s)
        urls.append(f"{DOMAIN}/shop/{s}/")
    return urls


def feed_path():
    """Return the site-relative path of the RSS/Atom feed build.py emits."""
    for candidate in ("feed.xml", "atom.xml", "rss.xml"):
        if os.path.isfile(os.path.join(ROOT, "site", candidate)):
            return candidate
    return None


def websub_ping():
    """POST a WebSub/PubSubHubbub publish notification for the feed."""
    fp = feed_path()
    if not fp:
        print("No feed file found in site/ - skipping WebSub ping")
        return
    feed_url = f"{DOMAIN}/{fp}"
    try:
        r = requests.post(
            f"{HUB_URL}/publish",
            data={"hub.mode": "publish", "hub.url": feed_url},
            timeout=30,
        )
        print(f"WebSub ping for {feed_url} -> HTTP {r.status_code}")
        if r.status_code != 200:
            print(f"  (non-200 is fine, hub may just be slow) body: {r.text[:200]}")
    except Exception as e:
        print(f"WebSub ping failed: {e} (non-fatal)")


if __name__ == "__main__":
    print("== GSC live inspection ==")
    gsc_inspect()
    print("== WebSub feed ping ==")
    websub_ping()
