# custom-apparel-series (alternate banner set, not live)

The "Gridiron Locker Custom Apparel" banner series (1933x813 PNG masters):
team-gear flat-lays under a `GRIDIRON LOCKER / CUSTOM APPAREL` headline, plus
the `YOUR DESIGN HERE / MAKE IT YOURS` home variant.

Moved here from `site/img/` on 2026-09-06: `site/img/` ships wholesale to
GitHub Pages and must not carry multi-MB unreferenced PNGs (see
`ArtworkHygiene` in `tests/test_layout.py`). The live heroes are exported
from the team-name masters in the parent folder instead.

To put this set live, export JPGs to `site/img/hero-*.jpg` and update the
band ratios in `src/style.css` (1933/813 home, 1933/813 teams) plus the
`width`/`height` attributes in `src/build.py`.
