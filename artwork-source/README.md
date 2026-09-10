# artwork-source

Original hand-made banner artwork (PNG masters) kept for reference only.

Nothing in this folder is served. The live banners are the five JPGs in
`site/img/hero-*.jpg`. The whole set was replaced on September 10, 2026 with
the owner's latest uploads (`hero-home1.png`, `hero-cleveland1.png`,
`hero-dallas1.png`, `hero-greenbay1.png`, `hero-michigan1.png` as uploaded) and
is archived here as the "…2" masters:

| Master (this folder)             | Live file                      | Exported  |
|----------------------------------|--------------------------------|-----------|
| `gridironlocker-hero-image2.png` | `site/img/hero-home.jpg`       | 2048x768  |
| `Cleveland browns banner2.png`   | `site/img/hero-cleveland.jpg`  | 2048x768  |
| `Dallas cowboys banner2.png`     | `site/img/hero-dallas.jpg`     | 2048x768  |
| `green bay banner2.png`          | `site/img/hero-greenbay.jpg`   | 2048x768  |
| `Mich banner2.png`               | `site/img/hero-michigan.jpg`   | 2048x768  |

Every master in the set is **2048x768**, so the site uses *one* band ratio
(`.cbanner .band{aspect-ratio:2048/768}` in `src/style.css`) for the homepage,
`/drops/` and the four collection pages. The band is never cropped and never
letterboxed: the poster's wordmark, headline and all five product shots show at
every breakpoint. These progressive JPGs use quality 85 and 4:2:0 chroma
subsampling, with metadata stripped; each is under 750 KB:

```bash
convert artwork-source/gridironlocker-hero-image2.png -strip -sampling-factor 4:2:0 \
  -interlace Plane -quality 85 site/img/hero-home.jpg
```

The square "Shop By Team" cards (`site/img/team-*.jpg`, 640x640) are **crops**
of the team banners, produced by `src/crop_art.py`. Every caption is painted
into the left ~1030px of each banner, so the script's crop box starts at
`x=1280`: the cards are product photography only and never repeat a headline
that the card's own HTML type already carries. Re-run `python3 src/crop_art.py`
after replacing a team banner.

If you replace a banner, measure the new master first, export the JPG at its
exact native size (quality 85, keep it under 750 KB), and then update:

* the band ratio in `src/style.css` (only if the new art is not 2048:768),
* the `width`/`height` attributes in `src/build.py` (home page + collection
  pages) and `src/drops_page.py` (which reuses the home poster),
* that hero's URL cache version — home `?v=5`, teams `?v=4` in
  `src/build.py` / `src/collections_data.py`,
* the expectations in `tests/test_layout.py` and the `BANNERS` table in
  `ops/health_check.py`.

`ops/health_check.py` (the daily production check) re-measures the deployed
JPGs against the ratios the HTML declares, so a cropped poster or a stray PNG
master fails the daily run instead of going unnoticed. PNG masters must stay in
this folder, never in the deployed `site/img/` directory.

The previous masters (`gridironlocker.png.png`, `gridironlocker1.png`,
`gridironlocker-hero-image1.png`, `Cleveland browns banner.png`,
`Cleveland browns banner1.png`, `Dallas cowboys banner.png`,
`Dallas cowboys banner1.png`, `green bay banner.png`, `green bay banner1.png`,
`Mich banner.png`, `Mich banner1.png`) remain archived here; they are no longer
referenced by any page, and the two derived crops they fed
(`site/img/hero-locker.jpg`, `site/img/hero-locker-sm.jpg`) were retired with
them. The old home posters had a type-free right-hand third that could be
cropped into a side-panel hero; the new poster has artwork out to both edges,
so the homepage shows the whole band and puts its copy underneath instead.

`custom-tee1.png` is the master of the homepage custom-design photo
(`site/img/custom-tee1.jpg`), archived here because `site/img/` ships JPG/WebP
only.

`custom-apparel-series/` holds an earlier alternate "Gridiron Locker Custom
Apparel" banner set (1933x813): same five slots, different creative. Preserved
here so nothing is lost; not referenced by any page.
