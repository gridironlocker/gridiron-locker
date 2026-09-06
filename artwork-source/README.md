# artwork-source

Original hand-made banner artwork (PNG masters) kept for reference only.

Nothing in this folder is served. The live hero banners are the five JPGs in
`site/img/hero-*.jpg`, exported at native size from the owner's September 6,
2026 upload (`c62d105`):

| Master (this folder)           | Live file                     | Size     |
|--------------------------------|-------------------------------|----------|
| `gridironlocker1.png`           | `site/img/hero-home.jpg`       | 1933x814 |
| `Cleveland browns banner1.png`  | `site/img/hero-cleveland.jpg`  | 1933x813 |
| `Dallas cowboys banner1.png`    | `site/img/hero-dallas.jpg`     | 1933x813 |
| `green bay banner1.png`         | `site/img/hero-greenbay.jpg`   | 1933x813 |
| `Mich banner1.png`              | `site/img/hero-michigan.jpg`   | 1933x813 |

The site's banner band ratios (`1933/814` home, `1933/813` team pages) match
this art exactly so it displays full/uncropped. These progressive JPGs use
quality 85 and 4:2:0 chroma subsampling, with metadata stripped; each is under
750 KB. For example, to reproduce the home export with ImageMagick:

```bash
convert artwork-source/gridironlocker1.png -strip -sampling-factor 4:2:0 \
  -interlace Plane -quality 85 site/img/hero-home.jpg
```

If you replace a banner, measure the new master first, export the JPG at its
exact native size (quality 85, keep it under 750 KB), and update the band ratio
in `src/style.css`, the `width`/`height` attributes in `src/build.py`, and the
matching layout assertions in `tests/test_layout.py`. Bump the hero URL cache
version in `src/build.py` and `src/collections_data.py` (currently `?v=3`).
PNG masters must stay here, never in the deployed `site/img/` directory.

The previous masters (`gridironlocker.png.png`, `Cleveland browns banner.png`,
`Dallas cowboys banner.png`, `green bay banner.png`, and `Mich banner.png`)
remain archived here at 1774x887 (home) and 1828x860 (teams); they are no longer
referenced by any page.

`custom-apparel-series/` holds an earlier alternate "Gridiron Locker Custom
Apparel" banner set (1933x813): same five slots, different creative. Preserved
here so nothing is lost; not referenced by any page.
