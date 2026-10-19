#!/usr/bin/env python3
"""Capture the Mayzing storefront's garment categories for the team pages.

The team collection pages carry the same apparel-style filter buttons as
Bella's locker: six category tiles that swap each design's mockup to the
garment that design actually lists. Bella's matrix lives in
data/creators.json; the Mayzing team stores expose it as category filter
pages, one per garment:

    https://gridironlocker.shop/p/browns?category=tshirt
    https://gridironlocker.shop/p/browns?category=hoodie
    https://gridironlocker.shop/p/browns?category=sweatshirt
    https://gridironlocker.shop/p/browns?category=tank_top
    https://gridironlocker.shop/p/browns?category=crop_tops

This script fetches each of those pages and writes data/mayzing_apparel.json:
per collection, per design slug, per storefront category, the listings that
design genuinely has - each with the garment label the store itself uses, the
signed w:500 mockup and the exact checkout URL (productId included).

Two rules, both inherited from Bella's locker:

* nothing is invented - a design appears under a category only because the
  store listed it there;
* no price is stored. The storefront quotes USD or NOK depending on session
  geo (data/mayzing_products.json documents the same trap), so a captured
  price would be wrong for most visitors. The category page's own listing is
  the price source of truth.

Run it with no arguments; it only writes when every page parsed. The refresh
workflow runs it before the build, so a product added to the store shows up on
the site on the next refresh without anyone editing the JSON by hand.

    python3 src/scrape_mayzing_apparel.py            # write the file
    python3 src/scrape_mayzing_apparel.py --dry-run  # report counts only
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from urllib.parse import parse_qs, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "mayzing_apparel.json")

#: collection key -> (storefront slug, collectionId)
STORES = {
    "cleveland-browns": ("browns", "P19bpeU2x_Ng"),
    "michigan": ("michigan", "YYMlCmwgKG__"),
}

#: storefront category query value -> the site's category key
CATEGORIES = [
    ("tshirt", "t-shirts"),
    ("hoodie", "hoodies"),
    ("sweatshirt", "sweatshirts"),
    ("tank_top", "tank-tops"),
    ("crop_tops", "crop-tops"),
]

#: The store's own garment labels. Longest first so "Cropped Baggy T-shirt"
#: wins over "Cropped T-shirt" and "Unisex Hoodie" over a bare "Hoodie".
GARMENTS = [
    "Classic Unisex T-shirt",
    "Cropped Baggy T-shirt",
    "Essential Sweatshirt",
    "Unisex Sweatshirt",
    "Cropped T-shirt",
    "Essential Hoodie",
    "Unisex Hoodie",
    "Women's Tank Top",
    "Unisex Tank Top",
    "Men's T-shirt",
    "Premium T-Shirt",
    "Heavy Cotton Cap",
    "Knit Beanie",
]

UA = ("Mozilla/5.0 (compatible; GridironLockerCatalogue/1.0; "
      "+https://gridironlocker.store/)")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def garment_of(text):
    """The store's garment label inside a card's text, or ''."""
    for g in GARMENTS:
        if g in text:
            return g
    return ""


def parse_page(html):
    """Every listing on one category page.

    Parsing is deliberately structural rather than class-name based: the
    storefront is a Next.js app whose CSS class hashes change between
    deploys, but every card is an <a> whose href carries productId= and
    which wraps the mockup <img> and the card text. Reading those three
    things survives a redesign; matching on hashed class names does not.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover - the workflow installs bs4
        print("beautifulsoup4 is required: pip install beautifulsoup4 lxml",
              file=sys.stderr)
        raise SystemExit(2)
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "productId=" not in href:
            continue
        parts = urlsplit(href)
        qs = parse_qs(parts.query)
        pid = (qs.get("productId") or [""])[0]
        slug = parts.path.strip("/").split("/")[-1]
        if not pid or not slug:
            continue
        garment = garment_of(a.get_text(" ", strip=True))
        if not garment:
            continue
        img = a.find("img")
        src = ""
        if img:
            src = img.get("src") or img.get("data-src") or ""
            if src.startswith("/_next/image"):
                # The storefront proxies mockups through its own image
                # optimiser; the signed CDN URL is the query parameter.
                inner = (parse_qs(urlsplit(src).query).get("url") or [""])[0]
                if inner:
                    src = inner
        if src.startswith("/"):
            src = "https://gridironlocker.shop" + src
        if href.startswith("/"):
            # The card links are root-relative on the storefront; store the
            # absolute checkout URL so the site can use it verbatim.
            href = "https://gridironlocker.shop" + href
        out.append({"slug": slug, "garment": garment,
                    "image": src, "url": href})
    return out


def scrape(dry_run=False):
    by_collection = {}
    summary = []
    for ckey, (store, _cid) in STORES.items():
        products = {}
        for cat_param, cat_key in CATEGORIES:
            url = ("https://gridironlocker.shop/p/%s?category=%s"
                   % (store, cat_param))
            try:
                rows = parse_page(fetch(url))
            except (urllib.error.URLError, OSError) as exc:
                print("  ! %s/%s: %s" % (ckey, cat_param, exc), file=sys.stderr)
                return None
            seen = set()
            kept = 0
            for row in rows:
                # one listing per design per category: the store can show the
                # same design in several colours, and the first card is the
                # colourway its mockup is signed for.
                if row["slug"] in seen:
                    continue
                seen.add(row["slug"])
                entry = {"garment": row["garment"],
                         "image": row["image"],
                         "url": row["url"]}
                products.setdefault(row["slug"], {}).setdefault(cat_key, []).append(entry)
                kept += 1
            summary.append((ckey, cat_key, kept))
        by_collection[ckey] = products

    for ckey, cat_key, n in summary:
        print("  %-18s %-13s %d" % (ckey, cat_key, n))
    if dry_run:
        return by_collection

    payload = {
        "_doc": (
            "Mayzing storefront garment categories, captured from each store's "
            "category filter page (tshirt, hoodie, sweatshirt, tank_top, "
            "crop_tops) by src/scrape_mayzing_apparel.py. Per collection, per "
            "design slug, per category: the listings that design genuinely "
            "has, with the garment label the store itself uses, the signed "
            "w:500 mockup and the exact checkout URL. src/build.py turns this "
            "into the team pages' apparel filter buttons. No prices are stored "
            "here on purpose - the storefront quotes USD or NOK depending on "
            "session geo. Regenerated by the refresh workflow; do not hand-edit."
        ),
        "captured": date.today().isoformat(),
        "source": "https://gridironlocker.shop/p/{store}?category={category}",
        "categories": {c: k for c, k in CATEGORIES},
        "collections": by_collection,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    total = sum(len(c) for c in by_collection.values())
    print("wrote %s: %d designs across %d collections"
          % (os.path.relpath(OUT, ROOT), total, len(by_collection)))
    return by_collection


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report counts without writing the data file")
    args = ap.parse_args(argv)
    if scrape(dry_run=args.dry_run) is None:
        print("scrape failed - keeping the existing data file", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
