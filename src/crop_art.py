#!/usr/bin/env python3
"""Derive the storefront's square team-card art from the approved team banners.

Every banner in the set is authored as a wide 2048x768 piece: the painted GL
wordmark and the team headline sit on the left, the product photography runs
across the right. The collection pages and /drops/ use those banners whole, as
full-width bands, so nothing is ever cropped there.

The one place a banner cannot be used raw is the homepage "Shop By Team" deck,
whose cards are square. This script cuts the product-led square on the right of
each team banner - shirts, hoodies and helmets with no headline in frame, so
four cards side by side do not repeat the same type four times.

Nothing here invents artwork: every output is a crop + resize of an approved
source file that already ships in site/img/. Re-run after replacing a banner:

    python3 src/crop_art.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "site", "img")

# (source, crop box, output size, output name, jpeg quality)
# The boxes start at x=1280 because that is where every banner's painted
# headline and support line have ended - the crop is pure product photography.
CROP = (1280, 0, 2048, 768)
JOBS = [
    ("hero-cleveland.jpg", CROP, (640, 640), "team-cleveland.jpg", 82),
    ("hero-greenbay.jpg", CROP, (640, 640), "team-greenbay.jpg", 82),
    ("hero-dallas.jpg", CROP, (640, 640), "team-dallas.jpg", 82),
    ("hero-michigan.jpg", CROP, (640, 640), "team-michigan.jpg", 82),
]


def main():
    for src, box, size, out, quality in JOBS:
        im = Image.open(os.path.join(IMG, src)).convert("RGB").crop(box)
        im = im.resize(size, Image.LANCZOS)
        path = os.path.join(IMG, out)
        im.save(path, quality=quality, optimize=True, progressive=True)
        print(f"{out}: {size[0]}x{size[1]}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    main()
