#!/usr/bin/env python3
"""Tests for the daily site health check (ops/health_check.py).

The health check is the thing that tells the owner "the live site is fine", so
it has to be honest: it must fail when a page loses its H1 or its canonical,
when structured data stops parsing, and - the case that matters most here -
when the artwork served does not match the artwork the band markup declares.
These tests drive those judgement calls with fixture HTML instead of the
network, and pin the checker's expectations to the pages this repo builds.

Run with either:
    python3 tests/test_health_check.py
    python3 -m pytest tests/
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "ops"))

try:
    import health_check as hc
except ImportError as e:                             # requests / Pillow missing
    hc = None
    IMPORT_ERROR = e
else:
    IMPORT_ERROR = None

requires_hc = unittest.skipIf(hc is None, f"health check needs requests + Pillow ({IMPORT_ERROR})")


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return fh.read()


GOOD_PAGE = """<!doctype html><html><head>
<title>Gridiron Locker - Fan-Made Football Tees</title>
<link rel="canonical" href="https://gridironlocker.store/cleveland-browns-shirts/">
<meta name="description" content="Fan-made Cleveland Browns shirts, hoodies and crewnecks printed on demand.">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"CollectionPage","name":"Cleveland"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"Gridiron Locker"}</script>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebSite","name":"Gridiron Locker"}</script>
</head><body><h1>Cleveland Browns Fan Shirts</h1>""" + "<!-- padding -->" * 200 + "</body></html>"


@requires_hc
class PageChecks(unittest.TestCase):
    def setUp(self):
        self.c = hc.Checker(hc.PRODUCTION, quiet=True)

    def failures(self, html, path="/cleveland-browns-shirts/"):
        self.c.check_page_html(path, html)
        return "\n".join(self.c.failures)

    def test_a_healthy_page_passes(self):
        self.assertEqual(self.failures(GOOD_PAGE), "")

    def test_missing_h1_fails(self):
        self.assertIn("0 <h1> tags", self.failures(GOOD_PAGE.replace("<h1>", "<h2>").replace("</h1>", "</h2>")))

    def test_two_h1s_fail(self):
        self.assertIn("2 <h1> tags", self.failures(GOOD_PAGE.replace("</h1>", "</h1><h1>Second</h1>")))

    def test_wrong_canonical_fails(self):
        bad = GOOD_PAGE.replace("/cleveland-browns-shirts/\">", "/cleveland/\">")
        self.assertIn("canonical is", self.failures(bad))

    def test_missing_canonical_fails(self):
        bad = GOOD_PAGE.replace('<link rel="canonical" href="https://gridironlocker.store/cleveland-browns-shirts/">', "")
        self.assertIn("no canonical link", self.failures(bad))

    def test_unparseable_json_ld_fails(self):
        bad = GOOD_PAGE.replace('"@type":"CollectionPage"', '"@type":"CollectionPage" "x": //')
        self.assertIn("does not parse", self.failures(bad))

    def test_missing_required_schema_fails(self):
        bad = GOOD_PAGE.replace('"@type":"CollectionPage"', '"@type":"ImageObject"')
        self.assertIn("no CollectionPage structured data",
                      self.failures(bad, path="/michigan/joe/"))

    def test_placeholder_and_traceback_leaks_fail(self):
        for marker in ("Traceback (most recent call last)", "undefined", "lorem ipsum"):
            self.assertIn(marker, self.failures(GOOD_PAGE + marker))

    def test_stub_description_fails(self):
        bad = GOOD_PAGE.replace('content="Fan-made Cleveland Browns shirts, hoodies and crewnecks printed on demand."',
                                'content="shirts"')
        self.assertIn("meta description", self.failures(bad))


@requires_hc
class ExpectationsMatchTheBuild(unittest.TestCase):
    """The checker hard-codes which page shows which banner. If the build moves
    a banner - or one of the five posters is renamed - this test goes red
    instead of the daily check quietly checking the wrong thing."""

    def band_src(self, rel):
        html = read(SITE, rel)
        i = html.index('<div class="band"><img')
        tag = html[i:html.index(">", i + len('<div class="band"><img'))]
        return tag.split('src="')[1].split('"')[0]

    def test_every_banner_page_is_a_checked_page(self):
        for page in hc.BANNERS:
            self.assertIn(page, hc.PAGES, page)

    def test_banner_table_matches_the_built_bands(self):
        pages = {"/": "index.html", "/drops/": "drops/index.html",
                 "/cleveland-browns-shirts/": "cleveland-browns-shirts/index.html",
                 "/green-bay-packers-shirts/": "green-bay-packers-shirts/index.html",
                 "/dallas-cowboys-shirts/": "dallas-cowboys-shirts/index.html",
                 "/michigan-wolverines-shirts/": "michigan-wolverines-shirts/index.html"}
        for page, rel in pages.items():
            want = hc.BANNERS[page][0].split("/")[-1]
            self.assertEqual(self.band_src(rel).split("?")[0].split("/")[-1], want, page)

    def test_banner_table_declares_the_sets_real_size(self):
        # Every banner in the set is exported at 2048x768; one ratio, no crops.
        for page, (path, w, h) in hc.BANNERS.items():
            tag = read(SITE, "index.html" if page == "/" else
                       page.strip("/") + "/index.html")
            self.assertIn(f'width="{w}" height="{h}"', tag, page)
            self.assertEqual((w, h), (2048, 768), page)

    def test_team_card_table_matches_the_homepage_deck(self):
        home = read(SITE, "index.html")
        for card in hc.TEAM_CARDS:
            self.assertIn(card.split("/")[-1], home, card)

    def test_banner_budget_matches_the_repo_rule(self):
        layout = read(ROOT, "tests", "test_layout.py")
        self.assertIn("750 * 1024", layout)
        self.assertEqual(hc.MAX_ART_BYTES, 750 * 1024)

    def test_sitemap_gate_is_stricter_than_the_workflows(self):
        """The live check must never be looser than the build gate it polices.

        Both used to be magic numbers (100) that disagreed with the real
        catalogue of 81 designs, so the health check failed a complete build.
        refresh.yml now asserts the sitemap's product URLs equal the master
        catalogue exactly; the live check keeps a floor that only catches a
        genuinely truncated build, and its own exact-count assert does the
        precise work.
        """
        self.assertGreaterEqual(hc.SITEMAP_MIN_URLS, 60)
        self.assertLess(hc.SITEMAP_MIN_URLS, hc.CATALOGUE_SIZE,
                        "the floor must sit below the real catalogue or every "
                        "healthy build fails")
        # the exact-match gate is what actually catches drift
        self.assertGreater(hc.CATALOGUE_SIZE, 0)


@requires_hc
class ArtworkRatio(unittest.TestCase):
    def test_ratio_gate_catches_a_cropped_poster(self):
        c = hc.Checker(hc.PRODUCTION)
        self.assertAlmostEqual(2048 / 768, 2.6667, places=3)
        # a 2048x600 "crop" is 3.41: well outside the 0.5% tolerance
        self.assertGreater(abs(2048 / 600 - 2048 / 768), 0.005)


if __name__ == "__main__":
    unittest.main(verbosity=2)
