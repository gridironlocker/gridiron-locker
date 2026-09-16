#!/usr/bin/env python3
"""Run bounded, diagnostic discovery checks after a deploy.

Two independent jobs, neither fatal to the workflow:

1) Search Console URL Inspection - only runs when the workflow has provided a
   service-account key via ``GSC_SA_JSON_PATH``. It inspects only product pages
   changed in this push (falling back to a small newest-sitemap sample after a
   rebase), capped at 50 URLs. URL Inspection is diagnostic: it does *not*
   submit a URL, request indexing, force a crawl, or guarantee a fresh crawl.
   The API response can report the current verdict/coverage state, last crawl,
   Google's canonical, the user canonical, and sitemap evidence when Google
   provides them. A JSON report can be written with ``GSC_REPORT_PATH``.

2) WebSub (PubSubHubbub) feed ping - always runs. Tells the public hub that
   site/feed.xml changed so any hub subscriber can refetch it immediately.
   This is a feed notification, not a Google indexing request.

Run after a rebuild + deploy:  python3 src/nudge_google.py
"""
import datetime
import json, os, re, subprocess, sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "src/config.json"), encoding="utf-8") as fh:
    CFG = json.load(fh)
DOMAIN = CFG["domain"].rstrip("/")

GSC_SITE_URL = f"{DOMAIN}/"
HUB_URL = "https://pubsubhubbub.appspot.com"
MAX_URLS = 50


def classify_index_state(verdict, coverage):
    """Map Google's words to conservative, report-only buckets.

    Search Console does not expose a universal site-wide count through URL
    Inspection. These labels are therefore per inspected URL and retain the
    original API strings in the report; unknown wording is never guessed.
    """
    text = (coverage or "").lower()
    if "submitted and indexed" in text or "url is on google" in text:
        return "indexed"
    if "discovered" in text and "not indexed" in text:
        return "discovered_but_not_indexed"
    if "crawled" in text and "not indexed" in text:
        return "crawled_but_not_indexed"
    if verdict in ("FAIL", "ERROR"):
        return "inspection_error"
    return "unknown"


def inspection_record(url, idx=None, error=None):
    """Normalise fields that URL Inspection actually returns.

    ``sitemap`` is the API's evidence that Google associated the inspected URL
    with a submitted sitemap; it is not a count of all submitted URLs. The
    distinction is kept explicit so this tool cannot fabricate a site-wide
    submitted/indexed metric.
    """
    idx = idx or {}
    verdict = idx.get("verdict")
    coverage = idx.get("coverageState")
    sitemaps = idx.get("sitemap") or []
    if isinstance(sitemaps, str):
        sitemaps = [sitemaps]
    row = {
        "url": url,
        "verdict": verdict,
        "coverage_state": coverage,
        "state": classify_index_state(verdict, coverage),
        "submitted_via_sitemap": bool(sitemaps),
        "sitemap_evidence": sitemaps,
        "last_crawl": idx.get("lastCrawlTime"),
        "google_canonical": idx.get("googleCanonical"),
        "user_canonical": idx.get("userCanonical"),
        "robots_txt_state": idx.get("robotsTxtState"),
        "indexing_state": idx.get("indexingState"),
        "page_fetch_state": idx.get("pageFetchState"),
    }
    if error:
        row["inspection_error"] = error
        row["state"] = "inspection_error"
    return row


def write_gsc_report(records, requested_urls):
    """Write an optional machine-readable report without changing the site.

    The workflow sends this to /tmp and stores it as a workflow artifact. Local
    callers can choose another path with GSC_REPORT_PATH. No report is written
    by default, which keeps a diagnostic run from dirtying the checkout.
    """
    path = os.environ.get("GSC_REPORT_PATH")
    summary = {"indexed": 0, "discovered_but_not_indexed": 0,
               "crawled_but_not_indexed": 0, "inspection_error": 0, "unknown": 0}
    for row in records:
        summary[row.get("state", "unknown")] = summary.get(row.get("state", "unknown"), 0) + 1
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "requested_url_count": len(requested_urls),
        "inspected_url_count": len(records),
        "summary": summary,
        "records": records,
        "limitations": [
            "URL Inspection is diagnostic only; it does not submit URLs or request indexing.",
            "This report covers only the inspected sample, not a site-wide Search Console count.",
            "submitted_via_sitemap is true only when the API returned sitemap evidence for that URL.",
            "The API may omit last crawl or canonical fields when Google has no value to report.",
        ],
    }
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
        print(f"GSC inspection report: {path}")
    print("GSC inspection summary (sample only): "
          + ", ".join(f"{k}={v}" for k, v in sorted(summary.items())))
    return report


def gsc_inspect():
    """Bounded URL Inspection diagnostics for changed product pages."""
    key_path = os.environ.get("GSC_SA_JSON_PATH")
    if not key_path or not os.path.isfile(key_path):
        print("GSC_SA_JSON_PATH not set - skipping URL Inspection (diagnostic only)")
        return

    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError:
        print("google-auth not installed - skipping GSC URL Inspection")
        return

    scopes = ["https://www.googleapis.com/auth/webmasters"]
    try:
        creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
        creds.refresh(GoogleAuthRequest())
    except Exception as e:
        print(f"GSC credential load/refresh failed: {e} - skipping URL Inspection")
        return

    urls = changed_product_urls()
    if not urls:
        print("No product URLs to inspect - skipping URL Inspection")
        return

    urls = urls[:MAX_URLS]
    print(f"GSC URL Inspection diagnostics: {len(urls)} url(s); no indexing request is made")

    endpoint = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }
    records = []
    for url in urls:
        # The URL Inspection API accepts the inspection request fields below.
        # It reports Google's current diagnostics; there is no submit/index
        # request field or indexing request in this call.
        body = {
            "inspectionUrl": url,
            "siteUrl": GSC_SITE_URL,
            "languageCode": "en-US",
        }
        try:
            r = requests.post(endpoint, headers=headers, json=body, timeout=60)
            if r.status_code == 200:
                result = r.json().get("inspectionResult", {})
                idx = result.get("indexStatusResult", {})
                row = inspection_record(url, idx)
                print(f"  {url} -> state={row['state']} verdict={row['verdict'] or '?'} "
                      f"coverageState={row['coverage_state'] or '?'} "
                      f"lastCrawl={row['last_crawl'] or '?'}")
            else:
                error = f"HTTP {r.status_code}: {r.text[:300]}"
                row = inspection_record(url, error=error)
                print(f"  {url} -> {error}")
        except Exception as e:
            row = inspection_record(url, error=str(e))
            print(f"  {url} -> error {e}")
        records.append(row)
    return write_gsc_report(records, urls)


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
