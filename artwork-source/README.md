# artwork-source

Original hand-made banner artwork (PNG masters) kept for reference only.

Nothing in this folder is served. The live hero banners are the five JPGs in
`site/img/hero-*.jpg`. The four team banners were exported at native size from
the owner's September 6, 2026 upload (`c62d105`); the home banner was replaced
on September 8, 2026 with the owner's later upload, which arrived as
`site/img/banner hero image1.png` and is archived here as
`gridironlocker-hero-image1.png`:

| Master (this folder)           | Live file                     | Size     |
|--------------------------------|-------------------------------|----------|
| `gridironlocker-hero-image1.png` | `site/img/hero-home.jpg`       | 1983x793 |
| `Cleveland browns banner1.png`  | `site/img/hero-cleveland.jpg`  | 1933x813 |
| `Dallas cowboys banner1.png`    | `site/img/hero-dallas.jpg`     | 1933x813 |
| `green bay banner1.png`         | `site/img/hero-greenbay.jpg`   | 1933x813 |
| `Mich banner1.png`              | `site/img/hero-michigan.jpg`   | 1933x813 |

The site's banner band ratios (`1983/793` home, `1933/813` team pages) match
this art exactly so it displays full/uncropped; `/drops/` reuses the home
poster inside the compact layout, so it carries `.homeband` to keep the home
ratio. These progressive JPGs use quality 85 and 4:2:0 chroma subsampling,
with metadata stripped; each is under 750 KB. For example, to reproduce the
home export with ImageMagick:

```bash
convert artwork-source/gridironlocker-hero-image1.png -strip -sampling-factor 4:2:0 \
  -interlace Plane -quality 85 site/img/hero-home.jpg
```

If you replace a banner, measure the new master first, export the JPG at its
exact native size (quality 85, keep it under 750 KB), and update the band ratio
in `src/style.css`, the `width`/`height` attributes in `src/build.py` (both the
home page and `/drops/`, which reuses the home poster) and the matching layout
assertions in `tests/test_layout.py`. Bump that hero's URL cache version in
`src/build.py` / `src/collections_data.py` (home `?v=4`, teams still `?v=3`).
PNG masters must stay here, never in the deployed `site/img/` directory.

The home poster is a finished piece of art - wordmark, eyebrow, headline and
two support lines are baked into the pixels - so the copy block under the band
must never restate them. `tests/test_layout.py::Homepage::
test_hero_copy_does_not_repeat_the_artwork` is the guard.

The previous masters (`gridironlocker.png.png`, `gridironlocker1.png`,
`Cleveland browns banner.png`, `Dallas cowboys banner.png`, `green bay
banner.png`, and `Mich banner.png`) remain archived here at 1774x887 and
1933x814 (home) and 1828x860 (teams); they are no longer referenced by any
page.

`custom-apparel-series/` holds an earlier alternate "Gridiron Locker Custom
Apparel" banner set (1933x813): same five slots, different creative. Preserved
here so nothing is lost; not referenced by any page.
