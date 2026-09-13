#!/usr/bin/env python3
"""Emit data/catalogue-live.json - the contract between storefront and marketing.

Why this file exists
--------------------
The marketing half of this repo (marketing/plan.py, marketing/live_engine.py)
used to read data/products.json as "the catalogue". That file is a *stale
Viralstyle crawl artefact* holding 113 slugs, while the real catalogue - the
merged set src/build.py computes from products_live.json plus both Mayzing
files, minus data/delisted.json and data/fulfillment.json's `hold` list - is 84.

The result was that 55 of 96 rows in the marketing queue pointed at designs with
no published page, and the three highest-scoring products in
marketing/commercial-brief.json were unpurchasable. See CODEX-TASKS.md Task 1.

Rather than have marketing re-derive the merge (which would be a second,
divergent source of truth - the exact failure mode that caused this), the
storefront *publishes* the answer and marketing *consumes* it. One writer, one
reader, one direction.

Ownership: this script and its output are Arena's (storefront side). Marketing
reads data/catalogue-live.json and must not write it. This is a deliberate,
documented exception to "marketing never writes to data/" - the exception is
that *the storefront* writes this one file, so marketing never has to.

Run it after a build:

    python3 src/build.py && python3 src/catalogue_contract.py

It is also run by .github/workflows/refresh.yml immediately after the rebuild,
so the committed contract always matches the committed site.
"""
from __future__ import annotations

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "data", "catalogue-live.json")

sys.path.insert(0, os.path.join(ROOT, "src"))
sys.dont_write_bytecode = True

import build  # noqa: E402  (path set immediately above; import is read-only)


def _utc_today() -> str:
    """Same clock as the build. Never datetime.date.today() - see AGENTS.md §6."""
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def page_is_published(slug: str) -> bool:
    """Is there a real product page for this slug on disk?

    Retired slugs keep a noindex redirect stub at the same path, so the file
    existing is not enough - the stub carries `data-gl-redirect`. Marketing must
    never promote a stub: it is a tombstone, not a product.
    """
    path = os.path.join(SITE, "shop", slug, "index.html")
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as fh:
        return "data-gl-redirect" not in fh.read()


def excluded_counts() -> dict:
    """How many slugs each gate withheld, so a reader can reconcile the numbers.

    If the catalogue ever shrinks unexpectedly, this says which gate did it
    instead of leaving marketing to guess whether a re-crawl lost designs.
    """
    def _load(rel, default):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            return default
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    delisted = _load(os.path.join("data", "delisted.json"), {})
    fulfillment = _load(os.path.join("data", "fulfillment.json"), {})
    crawl = _load(os.path.join("data", "products.json"), {})
    return {
        "delisted": len(delisted.get("slugs", {}) or {}),
        "fulfillment_hold": len(fulfillment.get("hold", []) or []),
        "stale_crawl_slugs": len(crawl),
        "note": (
            "stale_crawl_slugs is data/products.json - the raw Viralstyle crawl. "
            "It is NOT the catalogue and must never be used as one. "
            "count = stale_crawl_slugs + mayzing additions - delisted - hold - "
            "unpublished; reconcile via build.MODEL, not by arithmetic here."
        ),
    }


def build_contract(check_pages: bool = True) -> dict:
    products = []
    unpublished = []
    for item in build.ALL:
        slug = item["slug"]
        published = page_is_published(slug) if check_pages else True
        if not published:
            unpublished.append(slug)
        products.append({
            "slug": slug,
            "name": item.get("name", ""),
            "collection": item.get("col", ""),
            "partner": item.get("partner", ""),
            "url": build.abs_url(item.get("url", "")),
            "buy_url": item.get("buy", ""),
            "price_usd": item.get("price"),
            "garment": item.get("garment", ""),
            "theme": item.get("theme", ""),
            "site_published": published,
        })

    products.sort(key=lambda p: (p["collection"], p["slug"]))

    return {
        "generated": _utc_today(),
        "generator": "src/catalogue_contract.py",
        "source": "src/build.py :: build.ALL - the merged master catalogue",
        "contract": (
            "This is the ONLY authoritative list of sellable designs. Marketing "
            "must filter every queue, brief, drop and pin against it. Do not read "
            "data/products.json or data/products_live.json as a catalogue: both "
            "are stale crawl artefacts. Written by the storefront on every build; "
            "marketing reads it and never writes it."
        ),
        "count": len(products),
        "per_collection": {
            k: len(v) for k, v in sorted(
                ((k, build.MODEL[k]) for k in build.ORDER), key=lambda kv: kv[0])
        },
        "products": products,
        "excluded": excluded_counts(),
        "unpublished_but_in_catalogue": unpublished,
    }


def validate(contract: dict) -> list[str]:
    """Fail loudly rather than publishing a contract marketing cannot trust."""
    errors = []
    products = contract["products"]

    if not products:
        errors.append("contract is empty - build.ALL produced no products")

    slugs = [p["slug"] for p in products]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    if dupes:
        errors.append(f"duplicate slugs in contract: {sorted(dupes)[:10]}")

    if contract["count"] != len(products):
        errors.append(f"count {contract['count']} != {len(products)} products")

    for p in products:
        if not p["url"].startswith("http"):
            errors.append(f"{p['slug']}: url is not absolute: {p['url']!r}")
        if not p["buy_url"]:
            errors.append(f"{p['slug']}: no buy_url - a design nobody can purchase")
        if p["partner"] not in ("Viralstyle", "Mayzing"):
            errors.append(f"{p['slug']}: unknown partner {p['partner']!r}")
        if not p["site_published"]:
            errors.append(f"{p['slug']}: in build.ALL but no product page on disk")

    if sum(contract["per_collection"].values()) != contract["count"]:
        errors.append("per_collection does not sum to count")

    return errors


def main() -> int:
    if not os.path.isdir(SITE):
        print(f"FAIL: {SITE} does not exist - run python3 src/build.py first")
        return 1

    contract = build_contract()
    errors = validate(contract)
    if errors:
        print(f"FAIL: refusing to publish a broken catalogue contract "
              f"({len(errors)} problem(s)):")
        for e in errors[:30]:
            print(f"  - {e}")
        return 1

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(contract, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    per = ", ".join(f"{k}={v}" for k, v in contract["per_collection"].items())
    print(f"wrote {os.path.relpath(OUT, ROOT)} - {contract['count']} sellable "
          f"designs ({per})")
    print(f"  excluded: delisted={contract['excluded']['delisted']} "
          f"hold={contract['excluded']['fulfillment_hold']} "
          f"(stale crawl held {contract['excluded']['stale_crawl_slugs']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
