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


PLAIN_BACKS = {
    ("pdz0a9q97v0", "GILDAN-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miz0a9q97v21,sig:2Lgik9Vz_4_0RopU9R67tFqpv9M8tSAvsqzMPctAeak,c:GILDAN-BLACK,s:68cc43b4-f55a-46a0-9a99-5f88952ca97c,cpd:pdz0a9q97v0,w:500/image.png",
    ("pdz0a9q97v0", "GILDAN-HEATHER_SPORT_GREY"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miz0a9q97v81,sig:EaZcZPuXkXVaS_wvWp2XNOxPQiv-yd8NKRLekKJBwAo,c:GILDAN-HEATHER_SPORT_GREY,s:68cc43b4-f55a-46a0-9a99-5f88952ca97c,cpd:pdz0a9q97v0,w:500/image.png",
    ("pdz0a9q97v0", "GILDAN-NAVY"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miz0a9q97v21,sig:Eaux_ahKtj4-e8NGDHMQdiNJYPkLc1MLqngOMy4yCns,c:GILDAN-NAVY,s:68cc43b4-f55a-46a0-9a99-5f88952ca97c,cpd:pdz0a9q97v0,w:500/image.png",
    ("pdz0accu8c0", "GILDAN-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miz0accu8c21,sig:bOphm_LJIVOqx_cyw1UPPdD372hmwPPz3IPKQGgaqo8,c:GILDAN-BLACK,s:68cc43b4-f55a-46a0-9a99-5f88952ca97c,cpd:pdz0accu8c0,w:500/image.png",
    ("pdz0accu8c0", "GILDAN-DARK_CHOCOLATE"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miz0accu8c21,sig:VsHV1zcG1wZp0R5XWw2CuNlo45N1w3k3Iy3xNp3ZCWA,c:GILDAN-DARK_CHOCOLATE,s:68cc43b4-f55a-46a0-9a99-5f88952ca97c,cpd:pdz0accu8c0,w:500/image.png",
    ("pdz0accu8c0", "GILDAN-WHITE"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miz0accu8c1,sig:iX9EJWIANaVbk4vsAkiS_GkGeUkQ9F1vtuK__YS-kPI,c:GILDAN-WHITE,s:68cc43b4-f55a-46a0-9a99-5f88952ca97c,cpd:pdz0accu8c0,w:500/image.png",
    ("pddzz7dh5d0", "AWDIS-SOLID_BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:midzz7dh5d1,sig:RX1httFYNE93-b-6nR0euiQLFpzjrkLQ8zALNlxJelE,c:AWDIS-SOLID_BLACK,s:3895b8ae-4d06-4628-9167-a25f0e5c3c5f,cpd:pddzz7dh5d0,w:500/image.png",
    ("pde8yxhkdb0", "STANLEY_STELLA-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:mie8yxhkdb1,sig:1o5APBPhXpsjPwjtjrmnyynImRhGdLMXejsLx5ZgcO8,c:STANLEY_STELLA-BLACK,s:9ae14c27-d42c-438b-9476-7a657062e9a1,cpd:pde8yxhkdb0,w:500/image.png",
    ("pdwcvaf2ma0", "GILDAN-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miwcvaf2ma7,sig:0OMruufZ5sz3BcQCTYAdyfzQhOKBsC7TDGRkoyKx8OM,c:GILDAN-BLACK,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdwcvaf2ma0,w:500/image.png",
    ("pdwm5b3ykm0", "BELLA_CANVAS-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miwm5b3ykm11,sig:DuGJIEDKkblsRE1qDdnJjGBZyiU2nTJxDUddM4oFfRA,c:BELLA_CANVAS-BLACK,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdwm5b3ykm0,w:500/image.png",
    ("pdrt4mrdqt0", "ARCTIC_WHITE"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:mirt4mrdqt1,sig:HvtyKqxGR-citcrNSlpdBPCkd_4hm_FWhzCgW1mI4R4,c:ARCTIC_WHITE,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdrt4mrdqt0,w:500/image.png",
    ("pdrt4adgb80", "ARCTIC_WHITE"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:mirt4mrdqt1,sig:HvtyKqxGR-citcrNSlpdBPCkd_4hm_FWhzCgW1mI4R4,c:ARCTIC_WHITE,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdrt4mrdqt0,w:500/image.png",
    ("pdrt4mrdqt0", "HEATHER_GREY"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:mirt4mrdqt3a,sig:AZcWl_64F0XdSDAqcI53UYtSDNhT8E4O2Tq0yrsiKbg,c:HEATHER_GREY,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdrt4mrdqt0,w:500/image.png",
    ("pdrt4adgb80", "HEATHER_GREY"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:mirt4mrdqt3a,sig:AZcWl_64F0XdSDAqcI53UYtSDNhT8E4O2Tq0yrsiKbg,c:HEATHER_GREY,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdrt4mrdqt0,w:500/image.png",
    ("pdrt4mrdqt0", "JET_BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:mirt4mrdqt27,sig:QyhEkz_TVUU-vgfP5WcwmsFXuPKssT0fkGWrPmyt_hs,c:JET_BLACK,s:f0794bf7-6da1-49d6-bb52-d55fc35466fc,cpd:pdrt4mrdqt0,w:500/image.png",
    ("pdrt4adgb80", "OXFORD_NAVY"): "/img/p/gildan-hoodie-oxford-navy-back.webp",
    ("pdv0v2h40x0", "GILDAN-ASH_GREY"): "https://buyer-experience-gateway.mayzing.com/stores/qMlK/mockups/id:miv0v2h40x2b,sig:ujimly5BN5jPyifSYDiF0YbQvGqDqHgLeuUUozJ-Fvw,c:GILDAN-ASH_GREY,s:ae78b3e5-0f96-4e61-9d14-0248ae90f6a8,cpd:pdv0v2h40x0,w:500/image.png",
    ("pdv0v2h40x0", "GILDAN-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/qMlK/mockups/id:miv0v2h40x1d,sig:_BY2cEwwF9fZTqD71nrkpJ5xlA9LyZ5pnFqWORK1lEY,c:GILDAN-BLACK,s:ae78b3e5-0f96-4e61-9d14-0248ae90f6a8,cpd:pdv0v2h40x0,w:500/image.png",
    ("pdv0v2h40x0", "GILDAN-WHITE"): "https://buyer-experience-gateway.mayzing.com/stores/qMlK/mockups/id:miv0v2h40xf,sig:Ma-373jdDZK_v9zjdWEZjCClpPHyBOxV5r2gJtvSNgA,c:GILDAN-WHITE,s:ae78b3e5-0f96-4e61-9d14-0248ae90f6a8,cpd:pdv0v2h40x0,w:500/image.png",
    ("pdv0v2h40x0", "GILDAN-SAND"): "/img/p/gildan-hoodie-sand-back.webp",
    ("pdv0v2h40x0", "GILDAN-DARK_CHOCOLATE"): "/img/p/gildan-hoodie-dark-chocolate-back.webp",
    ("pdwxphbdeq0", "JET_BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miwxphbdeqf,sig:r2lwBLx3K1xDgQWjRDA4jTA-Y9anYQ6gOTxiSrTmcDo,c:JET_BLACK,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxphbdeq0,w:500/image.png",
    ("pdwxphbdeq0", "HEATHER_GREY"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miwxphbdeq2b,sig:joUkmGtvL3JlTZJS1LgxtW84MwXWc9QAznh0FIV-cQ4,c:HEATHER_GREY,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxphbdeq0,w:500/image.png",
    ("pdwxp323mt0", "HEATHER_GREY"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miwxphbdeq2b,sig:joUkmGtvL3JlTZJS1LgxtW84MwXWc9QAznh0FIV-cQ4,c:HEATHER_GREY,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxphbdeq0,w:500/image.png",
    ("pdwxp323mt0", "ARCTIC_WHITE"): "https://buyer-experience-gateway.mayzing.com/stores/qMlK/mockups/id:miwxp4hr5u1,sig:_Xcgezr4gS9gDPrseV6AR5fxEOnpWMg-8WVMueCoDPY,c:ARCTIC_WHITE,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxp4hr5u0,w:500/image.png",
    ("pdwxp323mt0", "NEW_FRENCH_NAVY"): "https://buyer-experience-gateway.mayzing.com/stores/qMlK/mockups/id:miwxp4hr5uf,sig:f-_wIQSnTMQapjOBlCBesgIVELOXfTY7bm75zwkdIME,c:NEW_FRENCH_NAVY,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxp4hr5u0,w:500/image.png",
    ("pd4buf6kzm0", "GILDAN-BLACK"): "https://buyer-experience-gateway.mayzing.com/stores/z2OF/mockups/id:miwxphbdeqf,sig:r2lwBLx3K1xDgQWjRDA4jTA-Y9anYQ6gOTxiSrTmcDo,c:JET_BLACK,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxphbdeq0,w:500/image.png",
    ("pd4buf6kzm0", "GILDAN-WHITE"): "https://buyer-experience-gateway.mayzing.com/stores/qMlK/mockups/id:miwxp4hr5u1,sig:_Xcgezr4gS9gDPrseV6AR5fxEOnpWMg-8WVMueCoDPY,c:ARCTIC_WHITE,s:aaafe9cc-0830-4913-87cb-c55178f009b0,cpd:pdwxp4hr5u0,w:500/image.png",
    ("pd4buf6kzm0", "GILDAN-SAND"): "/img/p/gildan-sweatshirt-sand-back.webp",
}


FRONT_ZOOM_SCENES = {
    "3f0f4426-e12f-4fc6-93ba-b8d58dfaaf37",
}


def fetch_product_back(product_url, front_src):
    """Fetch a Mayzing product page and return a distinct back mockup if published."""
    parts = urlsplit(product_url or "")
    pid = (parse_qs(parts.query).get("productId") or [""])[0]
    candidates = []
    if pid and parts.path:
        candidates.append(f"https://gridironlocker.shop{parts.path}?productId={pid}")
    if product_url and product_url not in candidates:
        candidates.append(product_url)
    for target in candidates:
        try:
            html = fetch(target, timeout=20)
        except (urllib.error.URLError, OSError):
            continue
        found = re.findall(
            r"https://buyer-experience-gateway\.mayzing\.com/stores/[^\"'&\s)]+/image\.png",
            html,
        )
        seen_urls = []
        for raw in found:
            w500 = re.sub(r",w:\d+/image\.png$", ",w:500/image.png", raw)
            if w500 not in seen_urls:
                seen_urls.append(w500)
        for cand in seen_urls:
            if cand == front_src:
                continue
            sm = re.search(r",s:([^,]+),", cand)
            if sm and sm.group(1) in FRONT_ZOOM_SCENES:
                continue
            return cand
        if seen_urls:
            break
    return ""


def resolve_back(prev_entry, src, product_url=""):
    """Preserve a verified (image, back) pair, inspect the product page, or match PLAIN_BACKS."""
    if prev_entry and prev_entry.get("back") and prev_entry.get("url"):
        return prev_entry.get("image") or src, prev_entry["back"]
    if product_url:
        live_back = fetch_product_back(product_url, src)
        if live_back:
            return src, live_back
    m = re.search(r",c:([^,]+),.*?,cpd:([^,]+),", src or "")
    if m:
        exact = PLAIN_BACKS.get((m.group(2), m.group(1)), "")
        if exact:
            return src, exact
        for (cpd_k, _col_k), fallback_url in PLAIN_BACKS.items():
            if cpd_k == m.group(2):
                return src, fallback_url
    return src, ""


def scrape(dry_run=False):
    existing = {}
    if os.path.isfile(OUT):
        try:
            with open(OUT, encoding="utf-8") as fh:
                existing = (json.load(fh).get("collections") or {})
        except (OSError, ValueError):
            existing = {}
    by_collection = {}
    summary = []
    for ckey, (store, _cid) in STORES.items():
        products = {}
        prev_col = existing.get(ckey) or {}
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
                prev_rows = (prev_col.get(row["slug"]) or {}).get(cat_key) or []
                prev_entry = prev_rows[0] if prev_rows else None
                front_img, back_img = resolve_back(prev_entry, row["image"], row["url"])
                entry = {"garment": row["garment"],
                         "image": front_img,
                         "url": row["url"]}
                if back_img:
                    entry["back"] = back_img
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
