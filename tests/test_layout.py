#!/usr/bin/env python3
"""Regression tests for the storefront layout and the generated site.

Run with either:
    python3 tests/test_layout.py          (stdlib unittest, no extra deps)
    python3 -m pytest tests/              (if pytest is installed)

The tests read the checked-in `site/` output, so run `python3 src/build.py`
first when you change `src/build.py` or `src/style.css`.

Covered:
  * CTA colours: #49a59c / #3a847d in both src/style.css and src/build.py.
  * /collections/: circular team portraits (4 desktop / 2 mobile), no
    "What you will find in each collection", four homepage-style team product
    sections (four cards + "View all" each, homepage ordering, no duplicates).
  * Team collection pages: no countdown, compact hero, ticker directly after
    the hero, product grid before trust / description / season news / trend
    panels, team-specific ticker, <= 3 Fan Trend Index rows, 2-col mobile grid,
    description kept below the products.
  * Countdowns outside collection pages are unchanged.
  * Homepage: rounded horizontal "Shop By Team" nav cards with circular
    thumbnails (2 desktop / 1 mobile), no "Why this locker", compact four-entry
    Fan Trend Index strip; the full index page still lists everything.
  * Product pages: Google-merchant Product schema (PeopleAudience, validFrom,
    shippingRate, deliveryTime, hasMerchantReturnPolicy) sourced from the
    SHIP_US / RETURN_POLICY / DELIVERY_TIME constants.
  * Artwork hygiene: no PNG masters in site/img (they live in artwork-source/).
  * Preserved: team accents, hero images, product count, checkout links, SEO
    metadata, dynamic catalogue counts, no missing local references.
"""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

from collections_data import COLLECTIONS, ORDER  # noqa: E402

CTA, CTA_HOVER = "#49a59c", "#3a847d"


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_json(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def page(rel):
    return read(os.path.join(SITE, rel))


def collection_pages():
    return {k: page(f"{COLLECTIONS[k]['slug']}/index.html") for k in ORDER}


def css_block(css, selector):
    """Return the declarations of the first rule whose selector list == selector."""
    m = re.search(re.escape(selector) + r"\{([^}]*)\}", css)
    return m.group(1) if m else ""


def media_rules(css, max_width):
    """Concatenate every @media(max-width:<max_width>px) block."""
    out = ""
    for m in re.finditer(r"@media\s*\(max-width:\s*%dpx\)\s*\{" % max_width, css):
        depth, i = 1, m.end()
        while depth and i < len(css):
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        out += css[m.end():i - 1]
    return out


def between(text, first, second):
    """Assert-friendly helper: text between the first occurrences of two markers."""
    a = text.index(first)
    b = text.index(second, a)
    return text[a:b]


class SourcesExist(unittest.TestCase):
    def test_build_outputs_present(self):
        for rel in ("index.html", "collections/index.html", "assets/style.css",
                    "fan-trend-index/index.html", "2026-season/index.html"):
            self.assertTrue(os.path.isfile(os.path.join(SITE, rel)), rel)
        for k in ORDER:
            self.assertTrue(os.path.isfile(
                os.path.join(SITE, COLLECTIONS[k]["slug"], "index.html")), k)


class CTAColours(unittest.TestCase):
    def test_style_css_defaults(self):
        css = read(os.path.join(SRC, "style.css"))
        root = css_block(css, ":root")
        self.assertIn(f"--btn:{CTA}", root)
        self.assertIn(f"--btn-h:{CTA_HOVER}", root)
        self.assertIn("background:var(--btn)", css_block(css, ".btn"))
        self.assertIn("background:var(--btn-h)", css_block(css, ".btn:hover"))

    def test_build_py_constants(self):
        src = read(os.path.join(SRC, "build.py"))
        self.assertIn(f'CTA = "{CTA}"', src)
        self.assertIn(f'CTA_HOVER = "{CTA_HOVER}"', src)

    def test_every_scoped_token_pair_is_teal(self):
        pairs = set()
        for base, _, files in os.walk(SITE):
            if os.sep + "ops" in base or os.sep + "marketing" in base:
                continue
            for f in files:
                if f.endswith(".html"):
                    pairs.update(re.findall(r"--btn:(#[0-9a-fA-F]{6});--btn-h:(#[0-9a-fA-F]{6})",
                                            read(os.path.join(base, f))))
        self.assertTrue(pairs, "no scoped CTA tokens found")
        self.assertEqual(pairs, {(CTA, CTA_HOVER)})

    def test_shipped_stylesheet_matches_source(self):
        self.assertEqual(read(os.path.join(SRC, "style.css")), page("assets/style.css"))


class CollectionsIndex(unittest.TestCase):
    def setUp(self):
        self.html = page("collections/index.html")
        self.css = page("assets/style.css")

    def test_circular_team_portraits_replace_image_tiles(self):
        self.assertNotIn('class="colcard"', self.html)
        self.assertNotIn('class="colgrid"', self.html)
        cards = re.findall(r'<a class="teamcircle[^"]*"[^>]*>(.*?)</a>', self.html, re.S)
        self.assertEqual(len(cards), len(ORDER))
        for k, card in zip(ORDER, cards):
            c = COLLECTIONS[k]
            self.assertIn('class="tportrait"', card)
            self.assertIn(os.path.basename(c["hero"]), card)          # existing hero, cropped
            self.assertIn(c["name"], card)                              # clear name
            self.assertRegex(card, r"\d+ designs")                      # design count
            self.assertIn("&rarr;", card)                               # navigation arrow
        # Circle + subtle team-colour outline
        port = css_block(self.css, ".tportrait")
        self.assertIn("border-radius:50%", port)
        self.assertIn("border:2px solid var(--ca)", port)
        self.assertIn("border-radius:50%", css_block(self.css, ".tportrait img"))

    def test_four_columns_desktop_two_mobile(self):
        self.assertIn("repeat(4,minmax(0,1fr))", css_block(self.css, ".teamcircles"))
        mob = media_rules(self.css, 900)
        self.assertIn(".teamcircles{grid-template-columns:repeat(2,minmax(0,1fr))", mob)

    def test_what_you_will_find_removed(self):
        self.assertNotIn("What you will find in each collection", self.html)

    def test_team_descriptions_stay_on_collection_pages(self):
        for k, html in collection_pages().items():
            c = COLLECTIONS[k]
            self.assertIn(f"About the {c['name']} Collection", html)
            # first sentence of the intro is rendered on the collection page
            first = c["intro"].format(**c).split(".")[0]
            self.assertIn(first, html)

    def test_four_team_product_sections(self):
        secs = re.findall(r'<section class="teamsec"(.*?)</section>', self.html, re.S)
        self.assertEqual(len(secs), 4)
        shorts = [re.search(r'<span class="accentword">([^<]+)</span> Collection', s).group(1)
                  for s in secs]
        self.assertEqual(sorted(shorts), sorted(COLLECTIONS[k]["short"] for k in ORDER))
        self.assertEqual(len(set(shorts)), 4, "duplicate team section")   # no duplicate Green Bay
        self.assertEqual(shorts.count("Green Bay"), 1)
        for s in secs:
            self.assertEqual(len(re.findall(r'<article class="card', s)), 4)
            self.assertRegex(s, r"View all \d+ [A-Za-z ]+ designs")

    def test_reuses_homepage_ordering(self):
        home = page("index.html")
        order = lambda h: re.findall(  # noqa: E731
            r'<section class="teamsec".*?<span class="accentword">([^<]+)</span> Collection', h, re.S)
        self.assertEqual(order(self.html), order(home))

    def test_counts_are_dynamic(self):
        live = load_json("data/products_live.json")
        cols = load_json("data/collections.json")
        try:
            delisted = load_json("data/delisted.json").get("slugs", {})
        except Exception:
            delisted = {}
        for k in ORDER:
            expected = 0
            for e in cols[k]["products"]:
                s = e["slug"]
                if s in delisted or s not in live:
                    continue
                img = live[s].get("img") or {}
                if any(isinstance(f, str) and f.startswith("/")
                       and os.path.isfile(os.path.join(SITE, f.lstrip("/"))) for f in img.values()):
                    expected += 1
            card = re.search(r'<a class="teamcircle[^"]*"[^>]*href="[^"]*%s/index\.html"[^>]*>.*?</a>'
                             % COLLECTIONS[k]["slug"], self.html, re.S).group(0)
            self.assertIn(f"{expected} designs", card, k)
            self.assertIn(f"View all {expected} {COLLECTIONS[k]['short']} designs", self.html)


class TeamCollectionPages(unittest.TestCase):
    def setUp(self):
        self.pages = collection_pages()
        self.css = page("assets/style.css")

    def test_no_countdown(self):
        for k, html in self.pages.items():
            self.assertNotIn('class="cdbar"', html, k)
            self.assertNotIn("data-deadline", html, k)
            self.assertNotIn('id="cd-d"', html, k)

    def test_compact_hero_then_ticker(self):
        for k, html in self.pages.items():
            self.assertIn('<section class="cbanner compact"', html, k)
            hero_end = html.index("</section>", html.index('class="cbanner compact"'))
            after = html[hero_end + len("</section>"):].lstrip()
            self.assertTrue(after.startswith('<div class="ticker">'),
                            f"{k}: ticker must immediately follow the hero")
        comp = css_block(self.css, ".cbanner.compact .band")
        self.assertIn("aspect-ratio:16/9", comp)

    def test_hero_bands_are_uncropped(self):
        # All five hero banners (home + four teams) are 1920x1080 (16:9) art;
        # the banner band must stay 16:9 at every breakpoint so none of them
        # get cropped to a wide strip.
        base = css_block(self.css, ".cbanner .band")
        self.assertIn("aspect-ratio:16/9", base)
        for ratio in ("32/9", "21/9", "5/1"):
            self.assertNotIn(f"aspect-ratio:{ratio}", self.css, ratio)

    def test_grid_before_trust_description_news_trends(self):
        for k, html in self.pages.items():
            grid = html.index('<section id="grid"')
            self.assertLess(html.index('class="ticker"'), grid, k)
            self.assertLess(grid, html.index('class="trust"'), k)
            self.assertLess(grid, html.index("In The 2026 Season"), k)
            self.assertLess(grid, html.index("About the "), k)
            for marker in ('class="ftibox"', 'class="newsbox', 'class="trendbox"'):
                if marker in html:
                    self.assertLess(grid, html.index(marker), f"{k}: {marker}")

    def test_grid_is_complete_and_tooling_present(self):
        for k, html in self.pages.items():
            n = int(re.search(r'id="count"[^>]*>(\d+) designs', html).group(1))
            grid = re.search(r'<div class="grid" id="pg">(.*?)</div>\s*<p class="muted center" id="nores"',
                             html, re.S).group(1)
            self.assertEqual(len(re.findall(r'<article class="card', grid)), n, k)
            self.assertIn('id="q" type="search"', html, k)
            self.assertIn('data-f="all"', html, k)
            self.assertIn('id="sort"', html, k)
            self.assertIn('id="nores"', html, k)
            self.assertIn("No designs match that search.", html, k)

    def test_ticker_is_team_specific(self):
        markers = {
            "cleveland-browns": ["Dawg Pound", "Shedeur Sanders", "Brownies"],
            "green-bay-packers": ["Go Pack Go", "Cheesehead", "Jordan Love"],
            "dallas-cowboys": ["Dallas vintage", "Texas pride", "Doomsday"],
            "michigan": ["Michigan vs Everybody", "Bryce Underwood", "Go Blue"],
        }
        for k, html in self.pages.items():
            tick = re.search(r'<div class="ticker">(.*?)</div></div>', html, re.S).group(1)
            self.assertTrue(any(m in tick for m in markers[k]), k)
            for other, ms in markers.items():
                if other != k:
                    for m in ms:
                        self.assertNotIn(m, tick, f"{k} ticker leaks {other} term {m!r}")
            self.assertIn(COLLECTIONS[k]["short"], tick, k)

    def test_at_most_three_trend_rows(self):
        for k, html in self.pages.items():
            self.assertLessEqual(html.count('class="fti-row"'), 3, k)

    def test_mobile_grid_is_two_columns(self):
        mob = media_rules(self.css, 560)
        self.assertIn(".grid{grid-template-columns:repeat(2,1fr)", mob)

    def test_hero_images_and_seo_preserved(self):
        for k, html in self.pages.items():
            c = COLLECTIONS[k]
            self.assertIn(os.path.basename(c["hero"]), html, k)
            self.assertIn(f'<link rel="canonical" href="https://gridironlocker.store/{c["slug"]}/">', html)
            self.assertIn(f"<title>{c['name']} | Gridiron Locker</title>", html)
            self.assertIn('<meta name="description"', html)
            self.assertIn('"@type":"CollectionPage"', html)
            self.assertIn('"@type":"FAQPage"', html)
            self.assertIn(f"--ca:{c['accent']}", html, k)   # team accent kept


class CountdownsElsewhere(unittest.TestCase):
    def test_homepage_and_week1_guide_keep_countdown(self):
        for rel in ("index.html", "guides/2026-week-1-shirts/index.html"):
            html = page(rel)
            self.assertIn('class="cdbar"', html, rel)
            self.assertIn("data-deadline", html, rel)
            self.assertIn('id="cd-d"', html, rel)

    def test_countdown_script_still_shipped(self):
        self.assertIn("kickoff countdown", page("assets/app.js"))


class ProductPages(unittest.TestCase):
    """Conversion + merchant schema on every built product page."""

    @classmethod
    def setUpClass(cls):
        shop = os.path.join(SITE, "shop")
        cls.pages = {d: read(os.path.join(shop, d, "index.html"))
                     for d in sorted(os.listdir(shop))
                     if os.path.isfile(os.path.join(shop, d, "index.html"))}
        cls.css = page("assets/style.css")
        cls.js = page("assets/app.js")

    @staticmethod
    def product_ld(html):
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            d = json.loads(m.group(1))
            if d.get("@type") == "Product":
                return d
        return None

    def test_merchant_schema_on_every_offer(self):
        import build  # noqa: E402
        for slug, html in self.pages.items():
            d = self.product_ld(html)
            self.assertIsNotNone(d, slug)
            self.assertEqual(d["audience"]["@type"], "PeopleAudience", slug)
            self.assertIn(d["audience"]["suggestedGender"], ("unisex", "female", "male"), slug)
            o = d["offers"]
            self.assertEqual(o["validFrom"], build.TODAY, slug)
            self.assertLess(o["validFrom"], o["priceValidUntil"], slug)
            self.assertEqual(o["hasMerchantReturnPolicy"], build.RETURN_POLICY, slug)
            self.assertEqual(o["shippingDetails"], build.SHIP_US, slug)
            self.assertEqual(o["shippingDetails"]["shippingRate"]["value"], "4.95", slug)
            self.assertEqual(o["hasMerchantReturnPolicy"]["merchantReturnDays"], 30, slug)
            dt = o["shippingDetails"]["deliveryTime"]
            self.assertEqual(dt["@type"], "ShippingDeliveryTime", slug)
            self.assertIn("handlingTime", dt, slug)
            self.assertIn("transitTime", dt, slug)

    def test_merchant_constants_defined_once(self):
        src = read(os.path.join(SRC, "build.py"))
        for name in ("SHIP_US", "RETURN_POLICY", "DELIVERY_TIME"):
            self.assertEqual(len(re.findall(r"^%s = " % name, src, re.M)), 1, name)
        self.assertNotIn('"shippingDetails": {"@type": "OfferShippingDetails"', src)


class ArtworkHygiene(unittest.TestCase):
    def test_no_orphan_artwork_in_site_img(self):
        # site/img is deployed wholesale; PNG masters live in artwork-source/.
        img = os.path.join(SITE, "img")
        pngs = [f for f in os.listdir(img) if f.lower().endswith(".png")]
        self.assertEqual(pngs, [], pngs)
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "artwork-source")))
        for k in ORDER:
            hero = os.path.join(SITE, COLLECTIONS[k]["hero"].lstrip("/"))
            self.assertTrue(os.path.isfile(hero), hero)
            self.assertLess(os.path.getsize(hero), 750 * 1024, hero)


class Homepage(unittest.TestCase):
    def setUp(self):
        self.html = page("index.html")
        self.css = page("assets/style.css")

    def test_shop_by_team_nav_cards(self):
        sec = between(self.html, '<section class="teamnavsec">', "</section>")
        self.assertIn("Shop By Team", sec)
        cards = re.findall(r'<a class="teamnav[^"]*"[^>]*>(.*?)</a>', sec, re.S)
        self.assertEqual(len(cards), len(ORDER))
        for k, card in zip(ORDER, cards):
            c = COLLECTIONS[k]
            self.assertIn('class="tportrait"', card)
            self.assertIn(c["name"], card)
            self.assertRegex(card, r"\d+ designs")
            self.assertIn("&rarr;", card)
        self.assertNotIn('class="colcard', self.html)
        nav = css_block(self.css, ".teamnav")
        self.assertIn("display:flex", nav)                      # horizontal
        self.assertIn("border-radius:18px", nav)                # rounded
        self.assertIn("repeat(2,minmax(0,1fr))", css_block(self.css, ".teamnav-grid"))
        self.assertIn(".teamnav-grid{grid-template-columns:1fr", media_rules(self.css, 760))

    def test_why_this_locker_removed(self):
        self.assertNotIn("Why this locker", self.html)
        self.assertNotIn('class="whystrip"', self.html)
        self.assertNotIn("whystrip", self.css)

    def test_compact_four_entry_fti_strip(self):
        sec = between(self.html, '<section class="ftisec">', "</section>")
        self.assertEqual(sec.count('class="fti-chip"'), 4)
        self.assertIn('href="./fan-trend-index/index.html"', sec)
        self.assertIn("repeat(4,minmax(0,1fr))", css_block(self.css, ".fti-chips"))

    def test_full_index_page_retained(self):
        fti = page("fan-trend-index/index.html")
        data = load_json("data/trends.json")
        rows = (data.get("fan_trend_index") or {}).get("rows") or []
        self.assertEqual(fti.count('class="fti-card reveal"'), len(rows))
        self.assertGreater(len(rows), 4)

    def test_team_sections_and_counts(self):
        secs = re.findall(r'<section class="teamsec"(.*?)</section>', self.html, re.S)
        self.assertEqual(len(secs), 4)
        for s in secs:
            self.assertEqual(len(re.findall(r'<article class="card', s)), 4)
        total = sum(int(n) for n in re.findall(r"View all (\d+) [A-Za-z ]+ designs", self.html))
        self.assertIn(f"{total} fan designs", self.html)   # banner count is the live total

    def test_seo_and_hero_preserved(self):
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/">', self.html)
        self.assertIn("hero-home.jpg", self.html)
        self.assertIn('"@type":"WebSite"', self.html)
        self.assertIn('"@type":"Organization"', self.html)


class CatalogueIntegrity(unittest.TestCase):
    def test_all_products_and_checkout_links(self):
        live = load_json("data/products_live.json")
        shop = os.path.join(SITE, "shop")
        built = [d for d in os.listdir(shop) if os.path.isfile(os.path.join(shop, d, "index.html"))]
        self.assertGreaterEqual(len(built), 100)
        for slug in built:
            html = read(os.path.join(shop, slug, "index.html"))
            self.assertIn(live[slug]["url"], html, slug)   # Viralstyle checkout link intact

    def test_no_missing_local_references(self):
        attr = re.compile(r'(?:src|data-src|href|content)="([^"]+)"')
        missing = []
        for base, _, files in os.walk(SITE):
            for f in files:
                if not f.endswith(".html"):
                    continue
                fp = os.path.join(base, f)
                for m in attr.finditer(read(fp)):
                    val = m.group(1).strip()
                    if val.startswith("//") or not (val.startswith("/") or val.startswith("../")
                                                    or val.startswith("./")):
                        continue
                    val = val.split("#")[0].split("?")[0]
                    if val in ("", "/", "./"):
                        continue
                    cand = (os.path.normpath(os.path.join(SITE, val.lstrip("/"))) if val.startswith("/")
                            else os.path.normpath(os.path.join(os.path.dirname(fp), val)))
                    if os.path.isdir(cand):
                        cand = os.path.join(cand, "index.html")
                    if not os.path.isfile(cand):
                        missing.append(f"{os.path.relpath(fp, SITE)}: {val}")
        self.assertEqual(missing, [])

    def test_sitemap_depth(self):
        sm = page("sitemap.xml")
        self.assertGreaterEqual(len(re.findall(r"<loc>", sm)), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
