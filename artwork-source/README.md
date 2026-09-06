# artwork-source

Original hand-made banner artwork (PNG masters) kept for reference only.

Nothing in this folder is served. The live hero banners are the five JPGs in
`site/img/hero-*.jpg`, exported from these masters at native size:

| Master (this folder)          | Live file                    | Size      |
|-------------------------------|------------------------------|-----------|
| `gridironlocker.png.png`      | `site/img/hero-home.jpg`     | 1774x887  |
| `Cleveland browns banner.png` | `site/img/hero-cleveland.jpg`| 1828x860  |
| `Dallas cowboys banner.png`   | `site/img/hero-dallas.jpg`   | 1828x860  |
| `green bay banner.png`        | `site/img/hero-greenbay.jpg` | 1828x860  |
| `Mich banner.png`             | `site/img/hero-michigan.jpg` | 1828x860  |

The site's banner band ratios (`1774/887` home, `1828/860` team pages) match
this art exactly so it displays full/uncropped. If you replace a banner,
export the new JPG at the art's native size (quality ~85, keep it under
750 KB) and update the band ratio + the `width`/`height` attributes in
`src/build.py` to match.

`custom-apparel-series/` holds the alternate "Gridiron Locker Custom Apparel"
banner set (1933x813): same five slots, different creative. Preserved here so
nothing is lost; not referenced by any page.
