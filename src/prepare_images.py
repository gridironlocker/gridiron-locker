#!/usr/bin/env python3
"""Generate the responsive image variants the storefront ships.

Why this exists
---------------
Every hero band is a full-bleed 2048x768 poster and it is the LCP element on
the page it opens. Until now the markup carried a single ``src``, so a phone
on 4G downloaded the full-size master (371-441 KB) to paint a 390 px wide
band. The band markup now ships a ``srcset`` pointing at the WebP candidates
this script produces, and ``src`` stays the original master so the declared
``width``/``height`` contract - and ``ops/health_check.py``, which downloads
``src`` and enforces the 2048:768 ratio - is untouched.

It also slims the four collection logo avatars. They are displayed at 150 px
(``.teamcircle .tportrait``) but shipped at up to 1018 px: ``michigan-logo1``
alone was 891 KB for a 150 px circle. They are re-derived from the lossless
PNG masters in ``artwork-source/`` (never from the compressed WebP) at the
2x size the CSS actually needs.

ImageMagick rather than Pillow because the generator runtime is stdlib-only
(AGENTS.md 3.1) and Pillow is not installed in the build sandbox.

The script is idempotent and only ever writes files that are not masters: run
it after adding or replacing hero art, then rebuild ``site/``.

    python3 src/prepare_images.py            # regenerate variants
    python3 src/prepare_images.py --check    # report sizes, write nothing
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "site", "img")
ART = os.path.join(ROOT, "artwork-source")

# Full-bleed heroes: home + the page the four collection banners share.
# hero-joe.jpg is deliberately absent - it is 137 KB and renders in a half-width
# grid column, so a variant would cost more repo bytes than it saves.
BAND_HEROES = ("hero-home", "hero-cleveland", "hero-greenbay", "hero-dallas",
               "hero-michigan")

# Candidate widths for a 100vw band. 1024 covers a 390 px phone at 2x, 1600
# covers a 540 px phone at 3x, and anything wider keeps the JPEG master.
HERO_WIDTHS = (1024, 1600)
HERO_QUALITY = 78

# The logo avatars are 150 CSS px wide, so 320 px is the 2x asset.
LOGO_WIDTH = 320
LOGO_QUALITY = 86

# artwork-source name -> deployed name, for the logos that have a lossless master.
LOGO_MASTERS = {
    "browns-logo1": "browns-logo1.png",
    "dallas-logo1": "dallas-logo1.png",
    "green-bay-logo1": "green bay-logo1.png",
    "michigan-logo1": "michigan-logo1.png",
}


def run(argv):
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(argv[:3])}... failed:\n{r.stderr.strip()}")
    return r


def dims(path):
    return run(["identify", "-format", "%wx%h", path]).stdout.strip()


def kb(path):
    return os.path.getsize(path) / 1024


def hero_variants(check):
    total_before = total_after = 0
    for stem in BAND_HEROES:
        master = os.path.join(IMG, stem + ".jpg")
        if not os.path.isfile(master):
            print(f"  {stem}.jpg: missing - skipped")
            continue
        before = kb(master)
        total_before += before
        line = [f"  {stem}.jpg {dims(master)} {before:.0f} KB -> "]
        built = []
        for width in HERO_WIDTHS:
            out = os.path.join(IMG, f"{stem}-{width}.webp")
            if check:
                if os.path.isfile(out):
                    built.append(f"{width}w {kb(out):.0f} KB")
                else:
                    built.append(f"{width}w MISSING")
                continue
            run(["convert", master, "-resize", f"{width}x", "-strip",
                 "-quality", str(HERO_QUALITY), "-define", "webp:method=6", out])
            built.append(f"{width}w {kb(out):.0f} KB")
            total_after += kb(out)
        line.append(", ".join(built))
        print("".join(line))
    if not check:
        print(f"  hero variants written: {total_after:.0f} KB of WebP "
              f"alongside {total_before:.0f} KB of masters")


def logo_variants(check):
    saved = 0
    for stem, master_name in LOGO_MASTERS.items():
        deployed = os.path.join(IMG, stem + ".webp")
        master = os.path.join(ART, master_name)
        if not os.path.isfile(master):
            print(f"  {stem}: no master in artwork-source, kept as-is")
            continue
        before = kb(deployed) if os.path.isfile(deployed) else 0
        tmp = deployed + ".tmp.webp"
        if check:
            print(f"  {stem}.webp {dims(deployed)} {before:.0f} KB -> "
                  f"would be {LOGO_WIDTH}px wide from {master_name}")
            continue
        run(["convert", master, "-resize", f"{LOGO_WIDTH}x{LOGO_WIDTH}",
             "-strip", "-quality", str(LOGO_QUALITY),
             "-define", "webp:method=6", tmp])
        os.replace(tmp, deployed)
        after = kb(deployed)
        saved += before - after
        print(f"  {stem}.webp {before:.0f} KB -> {after:.0f} KB "
              f"({dims(deployed)} from {master_name})")
    if not check:
        print(f"  logo avatars slimmed by {saved:.0f} KB")


def main():
    check = "--check" in sys.argv[1:]
    for tool in ("convert", "identify"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} not found - install ImageMagick")
    print("hero bands (srcset candidates):")
    hero_variants(check)
    print("collection logo avatars (re-derived from the PNG masters):")
    logo_variants(check)
    if check:
        print("\n--check: nothing written")


if __name__ == "__main__":
    main()
