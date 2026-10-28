#!/usr/bin/env python3
"""Generate responsive width variants of the big hero/feature images.

The masters in site/img/ are 2048px-wide JPEGs (370-430 KB) that every phone
was downloading whole - the single biggest mobile LCP cost on the store. This
writes 960w and 1440w JPEG siblings (quality 72) next to each master so
src/build.py can emit a srcset and a phone can fetch ~100 KB instead.

    .venv/bin/python make_hero_variants.py        # (re)generate missing variants
    .venv/bin/python make_hero_variants.py --force  # regenerate all

Needs Pillow (requirements-dev.txt). Run from the repo root after replacing
any hero. src/build.py picks the variants up automatically when the files
exist and falls back to the single master when they do not.
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, "site", "img")

# Hero masters over ~200 KB - the smaller creator heroes (130-175 KB) ship as-is.
MASTERS = [
    "hero-home.jpg",
    "hero-cleveland.jpg",
    "hero-greenbay.jpg",
    "hero-dallas.jpg",
    "hero-michigan.jpg",
    "hero-thetypicalbrownsfanshow.jpg",
    "custom-tee1.jpg",
]
WIDTHS = (960, 1440)
QUALITY = 72


def main() -> int:
    force = "--force" in sys.argv
    made = 0
    for name in MASTERS:
        src = os.path.join(IMG, name)
        if not os.path.isfile(src):
            print("missing master:", name)
            continue
        im = Image.open(src)
        for w in WIDTHS:
            if w >= im.width:
                continue
            stem, ext = os.path.splitext(name)
            out = os.path.join(IMG, f"{stem}-{w}{ext}")
            if os.path.exists(out) and not force:
                continue
            h = round(im.height * w / im.width)
            im.resize((w, h), Image.LANCZOS).convert("RGB").save(
                out, "JPEG", quality=QUALITY, optimize=True, progressive=True
            )
            print(f"{os.path.basename(out):40s} {w}x{h}  {os.path.getsize(out)//1024}KB")
            made += 1
    print("variants written:", made)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
