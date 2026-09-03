#!/usr/bin/env python3
"""One-command campaign adder for directly-published Viralstyle campaigns.

Usage:
    python3 add_campaign.py <slug> <collection-key> [--dry-run]

Fetches https://viralstyle.com/kebystore/<slug>?_escaped_fragment_=,
parses the campaign into the same entry shape replay_updates.py expects,
and merges {slug: entry} into data/campaigns_extra.json (idempotent
overwrite). Run python3 replay_updates.py + dl.py + src/build.py afterwards,
or wait for the next Refresh workflow run.

Example:
    python3 add_campaign.py my-new-design cleveland-browns
"""
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0"
SIZES_ORDER = ["S", "M", "L", "XL", "2XL", "3XL"]


def fetch(slug):
    url = f"https://viralstyle.com/kebystore/{slug}?_escaped_fragment_="
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    last = None
    for attempt in range(3):
        try:
            r = s.get(url, timeout=45)
            t = r.text
            if len(t) > 20000:
                return t
            last = f"short page ({len(t)} chars)"
        except Exception as e:
            last = str(e)
    print(f"fetch failed for {slug}: {last}", file=sys.stderr)
    return None


def parse(html, slug, collection):
    soup = BeautifulSoup(html, "lxml")
    meta = {m.get("property") or m.get("name"): m.get("content") for m in soup.find_all("meta")}
    txt = re.sub(r"\s+", " ", soup.get_text(" "))

    # campaign id + base mockup key from the front-large asset
    m = re.search(
        r"assets\.viralstyle\.com/campaigns/([0-9a-fA-F\-]{8,})/([A-Za-z0-9\-]+)-front-large\.jpg",
        html,
    )
    if not m:
        raise SystemExit(f"could not find campaign asset for slug: {slug}")
    cid, base = m.group(1), m.group(2)

    # swatch keys: KEEP full 3-part keys as they appear in the page
    swatch_keys = sorted(
        set(
            re.findall(
                r"assets\.viralstyle\.com/campaigns/[0-9a-fA-F\-]+/([A-Za-z0-9\-]+)-front-small\.jpg",
                html,
            )
        )
    )

    # styles inside "SELECT STYLE ... SELECT COLOR|SIZE"
    styles = []
    m = re.search(r"SELECT STYLE(.*?)SELECT (?:COLOR|SIZE)", txt)
    if m:
        for part in re.findall(r"([A-Za-z0-9'\-\.\u2019 ]+?) - (?:Rs|\$)[\d,\.]+", m.group(1)):
            part = part.strip()
            if part:
                styles.append(part)

    # sizes: "SELECT SIZE (.*?) SELECT QUANTITY", strip label + ALL spaces,
    # then consume S,M,L,XL,2XL,3XL in order from the concatenated blob
    # (pages render it as Select SizeSMLXL2XL3XL).
    sizes = []
    m = re.search(r"SELECT SIZE(.*?)SELECT QUANTITY", txt)
    if m:
        blob = re.sub(r"\s+", "", m.group(1))
        blob = re.sub(r"(?i)^selectsize", "", blob)
        upper = blob.upper()
        pos = 0
        for sz in SIZES_ORDER:
            idx = upper.find(sz, pos)
            if idx != -1:
                sizes.append(sz)
                pos = idx + len(sz)
    if not sizes:
        sizes = list(SIZES_ORDER)

    # desc with doubled leading title deduped via backreference
    desc = ""
    m = re.search(r"About Product(.*?)(KEY FEATURES|MEASUREMENT NOTES|Recommended Products)", txt)
    if m:
        desc = m.group(1).strip()
        desc = re.sub(r"^(.+?)\1", r"\1", desc)

    features = ""
    m = re.search(r"KEY FEATURES: ?(.*?)(MEASUREMENT NOTES|CARE INSTRUCTIONS|Recommended)", txt)
    if m:
        features = m.group(1).strip()

    title = (meta.get("og:title") or "").strip()
    price_usd = meta.get("product:price:amount")
    brand = meta.get("product:brand")
    m = re.search(r"Rs[\d,\.]+", txt)
    list_price_inr = m.group(0) if m else ""

    return {
        "title": title,
        "price_usd": price_usd,
        "brand": brand,
        "campaign": cid,
        "base": base,
        "swatch_keys": swatch_keys,
        "styles": styles,
        "desc": desc,
        "features": features,
        "collection": collection,
        "sizes": sizes,
        "list_price_inr": list_price_inr,
    }


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    dry = "--dry-run" in argv
    if len(args) != 2:
        print("usage: python3 add_campaign.py <slug> <collection-key> [--dry-run]")
        return 2
    slug, collection = args

    cols = json.load(open(os.path.join(ROOT, "data/collections.json"), encoding="utf-8"))
    if collection not in cols:
        print(f"invalid collection-key: {collection} (expected one of {sorted(cols)})",
              file=sys.stderr)
        return 2

    html = fetch(slug)
    if not html:
        return 1
    entry = parse(html, slug, collection)
    print(f"parsed {slug}: campaign={entry['campaign']} base={entry['base']} "
          f"swatches={len(entry['swatch_keys'])} styles={len(entry['styles'])} "
          f"sizes={','.join(entry['sizes'])} title={entry['title']!r}")

    if dry:
        print(json.dumps({slug: entry}, indent=1))
        print("dry-run: not writing data/campaigns_extra.json")
        return 0

    path = os.path.join(ROOT, "data/campaigns_extra.json")
    try:
        existing = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    except Exception:
        existing = {}
    if isinstance(existing, list):
        conv = {}
        for e in existing:
            if isinstance(e, dict) and e.get("slug"):
                s = e.pop("slug")
                conv[s] = e
        existing = conv
    if not isinstance(existing, dict):
        existing = {}
    existing[slug] = entry  # idempotent overwrite
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=1)
        fh.write("\n")
    print(f"wrote {slug} -> data/campaigns_extra.json ({len(existing)} campaigns)")
    print("next: python3 replay_updates.py && python3 dl.py && python3 src/build.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
