#!/usr/bin/env python3
"""Capture the live Mayzing price of every Browns and Michigan product.

The storefront cannot be reached from the build environment, so this runs on a
GitHub runner (same as src/scrape_mayzing_apparel.py) and writes
data/mayzing_prices.json. src/build.py prefers these prices over the
hand-captured `price_usd` in data/mayzing_products.json / data/mayzing_michigan.json,
so a price the owner changes in Mayzing admin reaches the site on the next
refresh instead of needing a hand edit of 52 records.

The storefront quotes USD or NOK depending on session geo, and a NOK number
written into a $ field would be wrong for every visitor. The guesser is
therefore strict: a price is only recorded when the page renders a dollar
amount (the JSON-LD offer, a price meta tag, or a `$NN.NN` in the body). If a
product has no dollar price the run REFUSES TO WRITE anything, so a
geo-redirected runner can never corrupt the file - the previous good capture
stays in place.

    python3 src/scrape_mayzing_prices.py            # write the capture
    python3 src/scrape_mayzing_prices.py --dry-run  # report, write nothing
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "mayzing_prices.json")

#: collection key -> the curated product file listing its designs
SOURCES = [
    ("cleveland-browns", "data/mayzing_products.json"),
    ("michigan", "data/mayzing_michigan.json"),
]

UA = ("Mozilla/5.0 (compatible; GridironLockerCatalogue/1.0; "
      "+https://gridironlocker.store/)")

#: "$23.00" / "$1,234.00" in the rendered body.
DOLLAR = re.compile(r"\$\s?([0-9][0-9,]*\.[0-9]{2})")
#: A non-dollar currency token, used to explain a refusal clearly.
FOREIGN = re.compile(r"\b(NOK|SEK|DKK|EUR|GBP)\b|(?:\d[ .,]?\d*\s?kr)\b", re.I)
JSONLD = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)
META_PRICE = re.compile(
    r'<meta[^>]+(?:property|name)="(?:product:price:amount|og:price:amount)"'
    r'[^>]+content="([0-9][0-9.,]*)"', re.I)


def fetch(url, timeout=30, tries=3):
    """GET a page, retrying the transient failures the CDN throws."""
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last


def _clean(raw):
    """'1,234.00' -> '1234.00'; rejects anything that is not a sane price."""
    try:
        value = float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return ""
    if not (0 < value < 1000):
        return ""
    return "%.2f" % value


def _jsonld_price(html):
    for block in JSONLD.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if not isinstance(node, dict):
                continue
            offers = node.get("offers")
            for offer in (offers if isinstance(offers, list) else [offers]):
                if isinstance(offer, dict):
                    price = _clean(offer.get("price") or offer.get("lowPrice"))
                    if price:
                        return price, "json-ld"
    return "", ""


def parse_price(html):
    """(price, source) for one product page, or ('', reason).

    Ordered most- to least-structured: the merchant feed the storefront
    publishes, then a price meta tag, then the rendered `$NN.NN`.
    """
    price, src = _jsonld_price(html)
    if price:
        return price, src
    m = META_PRICE.search(html)
    if m:
        price = _clean(m.group(1))
        if price:
            return price, "meta"
    m = DOLLAR.search(html)
    if m:
        price = _clean(m.group(1))
        if price:
            return price, "text"
    if FOREIGN.search(html):
        return "", "non-USD currency on the page"
    return "", "no price found"


def load_records(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return json.load(fh)


def scrape(dry_run=False):
    captured = {}
    problems = []
    rows = []
    for ckey, path in SOURCES:
        doc = load_records(path)
        products = doc.get("products") or []
        per = {}
        for product in products:
            slug = product.get("slug") or ""
            url = product.get("checkout_url") or ""
            if not slug or not url:
                problems.append("%s: %r has no checkout_url" % (ckey, slug))
                continue
            try:
                html = fetch(url)
            except (urllib.error.URLError, OSError) as exc:
                problems.append("%s/%s: fetch failed: %s" % (ckey, slug, exc))
                continue
            price, source = parse_price(html)
            if not price:
                problems.append("%s/%s: %s" % (ckey, slug, source))
                continue
            per[slug] = {
                "price_usd": price,
                "garment": product.get("garment") or "",
                "product_id": product.get("product_id") or "",
                "source": source,
            }
            rows.append((ckey, slug, product.get("price_usd") or "", price, source))
        captured[ckey] = per

    print("%-18s %-46s %9s %9s %s" % ("collection", "design", "was", "now", "read"))
    for ckey, slug, was, now, source in rows:
        flag = "" if _clean(was) == now else "  <- changed"
        print("%-18s %-46s %9s %9s %-6s%s" % (ckey, slug[:46], was, now, source, flag))
    changed = sum(1 for _, _, was, now, _ in rows if _clean(was) != now)
    print("\n%d products read, %d prices differ from the committed capture"
          % (len(rows), changed))

    if problems:
        print("\nREFUSING TO WRITE - %d product(s) had no USD price:" % len(problems),
              file=sys.stderr)
        for p in problems:
            print("  ! " + p, file=sys.stderr)
        return None
    if dry_run:
        return captured

    payload = {
        "_doc": (
            "Live Mayzing storefront prices for the Browns and Michigan "
            "collections, captured from each product's own checkout page by "
            "src/scrape_mayzing_prices.py. This file is machine-written: it "
            "exists so a price changed in Mayzing admin reaches the site "
            "without hand-editing data/mayzing_products.json or "
            "data/mayzing_michigan.json. src/build.py prefers a price here "
            "and falls back to the curated product record when a design is "
            "missing. Only dollar prices are recorded - the storefront quotes "
            "NOK depending on session geo, and a run that cannot read a USD "
            "price on every product refuses to write at all."
        ),
        "captured": date.today().isoformat(),
        "currency": "USD",
        "source": "https://gridironlocker.shop/<handle>?collectionId=...&productId=...",
        "collections": captured,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return captured


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report the prices without writing the data file")
    args = ap.parse_args(argv)
    if scrape(dry_run=args.dry_run) is None:
        print("price capture failed - keeping the existing data file",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
