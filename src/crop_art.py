#!/usr/bin/env python3
"""Derive the homepage art crops from the approved Gridiron Locker banners.

The storefront artwork is authored as wide banners (1983x793 for the home
poster, 1933x813 per team) with the brand lockup painted into the image. Those
files are perfect for a full-width band on a collection page, but the homepage
needs two other shapes:

  * the hero's cinematic panel - the right-hand two thirds of the home poster
    (hoodies, helmets, football, brush strokes, locker room) with the painted
    "GEAR UP. KEEP IT." headline cropped away, because the homepage renders
    that headline as real, crawlable HTML text next to it;
  * the "Shop By Team" cards - a tall, product-led crop of each team banner
    that deliberately excludes the painted "GRIDIRON LOCKER / CUSTOM APPAREL"
    lockup, so four cards side by side do not repeat the same words four
    times and the card's own HTML typography carries the message.

Cropping (instead of shipping the full banners) is also the single biggest
homepage performance win: the four team banners are ~350 KB each at 1933px
wide but are painted into ~280px cards, so the browser used to download
1.4 MB of artwork to render 4 thumbnails.

Nothing here invents artwork: every output is a crop + resize of an approved
source file that already ships in site/img/. Re-run after replacing a banner:

    python3 src/crop_art.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "site", "img")

# (source, crop box, output width, output name, jpeg quality)
# Boxes are in source pixels. The team boxes stop at x=600 because the painted
# lockup on every team banner starts at ~x=616.
JOBS = [
    ("hero-home.jpg", (640, 0, 1983, 793), 1400, "hero-locker.jpg", 80),
    ("hero-home.jpg", (640, 0, 1983, 793), 760, "hero-locker-sm.jpg", 78),
    ("hero-cleveland.jpg", (0, 140, 600, 813), 620, "team-cleveland.jpg", 80),
    ("hero-greenbay.jpg", (0, 140, 600, 813), 620, "team-greenbay.jpg", 80),
    ("hero-dallas.jpg", (0, 140, 600, 813), 620, "team-dallas.jpg", 80),
    ("hero-michigan.jpg", (0, 140, 600, 813), 620, "team-michigan.jpg", 80),
]


def main():
    for src, box, width, out, quality in JOBS:
        im = Image.open(os.path.join(IMG, src)).convert("RGB").crop(box)
        height = round(width * im.height / im.width)
        im = im.resize((width, height), Image.LANCZOS)
        path = os.path.join(IMG, out)
        im.save(path, quality=quality, optimize=True, progressive=True)
        print(f"{out}: {width}x{height}  {os.path.getsize(path) // 1024} KB")


if __name__ == "__main__":
    main()
