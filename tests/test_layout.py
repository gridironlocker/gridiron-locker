#!/usr/bin/env python3
"""Regression tests for the storefront layout and the generated site.

Run with either:
    python3 tests/test_layout.py          (stdlib unittest, no extra deps)
    python3 -m pytest tests/              (if pytest is installed)

The tests read the checked-in `site/` output, so run `python3 src/build.py`
first when you change `src/build.py` or `src/style.css`.

Covered:
  * CTA colours: #49a59c / #3a847d in both src/style.css and src/build.py.
  * /collections/: circular team logo marks (4 desktop / 2 mobile), no
    "What you will find in each collection", four homepage-style team product
    sections (four cards + "View all" each, homepage ordering, no duplicates).
  * Team collection pages: no countdown, compact hero, ticker directly after
    the hero, product grid before trust / description / season news / trend
    panels, team-specific ticker, <= 3 Fan Trend Index rows, 2-col mobile grid,
    description kept below the products.
  * Countdowns outside collection pages are unchanged.
  * Homepage hero: the approved 2048:768 poster shown whole as a band (the same
    band component, ratio and image the collection pages use), with the
    editorial copy block - crawlable <h1>, CTAs, live catalogue facts - beneath
    it, so the artwork is never cropped and never restated in text.
  * Homepage: rounded horizontal "Shop By Team" nav cards with circular
    logo thumbnails (2 desktop / 1 mobile), no "Why this locker", compact four-entry
    Fan Trend Index strip; the full index page still lists everything.
  * Product pages: one live "Order in Xd Yh Zm" order-by chip (.uc) per page
    with an ISO deadline + the app.js ticker, seamless-checkout copy, and
    Google-merchant Product schema (PeopleAudience, validFrom, shippingRate,
    deliveryTime, hasMerchantReturnPolicy) sourced from the SHIP_US /
    RETURN_POLICY / DELIVERY_TIME constants.
  * Team collection pages are product-first: no Fan Trend Index / moments /
    headline panels (those live on /2026-season/ and /fan-trend-index/), and
    live ticker terms are team-safe (no raw headline words, no opponents).
  * Artwork hygiene: no PNG masters in site/img (they live in artwork-source/).
  * Preserved: team accents, hero images, product count, checkout links, SEO
    metadata, dynamic catalogue counts, no missing local references.
"""
import json
import os
import re
import sys
import unittest
from html import unescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SRC = os.path.join(ROOT, "src")
IMG = os.path.join(SITE, "img")
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
            self.assertIn(os.path.basename(c["logo"]), card)           # logo mark, uncropped
            self.assertNotIn(os.path.basename(c["hero"]), card)        # hero photo no longer used
            self.assertIn(c["name"], card)                              # clear name
            self.assertRegex(card, r"\d+ designs")                      # design count
            self.assertIn("&rarr;", card)                               # navigation arrow
        # Circle + subtle team-colour outline + uncropped logo
        port = css_block(self.css, ".tportrait")
        self.assertIn("border-radius:50%", port)
        self.assertIn("border:2px solid var(--ca)", port)
        img = css_block(self.css, ".tportrait img")
        self.assertIn("border-radius:50%", img)
        self.assertIn("object-fit:contain", img)

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

    def test_hub_is_navigation_with_trending_row(self):
        # /collections/ is a navigation hub, not a duplicate of the
        # homepage: one circle per team plus a single store-wide trending
        # row. The four per-team product grids lived here before and forced
        # visitors to scroll ~16 teaser cards before choosing a side.
        self.assertNotIn('class="teamsec"', self.html)
        self.assertIn("Trending Across", self.html)
        self.assertEqual(len(re.findall(r'<article class="card', self.html)), 8)
        self.assertIn('./drops/', self.html)


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
                if any((isinstance(f, str) and f.startswith("/") and os.path.isfile(os.path.join(SITE, f.lstrip("/")))
                        or (isinstance(f, str) and f.startswith("https://assets.viralstyle.com/")))
                       for f in img.values()):
                    expected += 1
            card = re.search(r'<a class="teamcircle[^"]*"[^>]*href="[^"]*%s/"[^>]*>.*?</a>'
                             % COLLECTIONS[k]["slug"], self.html, re.S).group(0)
            self.assertIn(f"{expected} designs", card, k)


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
        # the compact band inherits the set's one ratio; only the copy tightens
        self.assertNotIn("aspect-ratio", comp)

    def test_hero_bands_are_uncropped(self):
        # Every banner in the set - the home poster and the four team banners -
        # is 2048x768, so one ratio locks the band at every breakpoint and the
        # full artwork shows: no cropping to a 16:9 box, no wide strips, and no
        # per-page ratio overrides left to drift.
        base = css_block(self.css, ".cbanner .band")
        self.assertIn("aspect-ratio:2048/768", base)
        for html, name in ((page("index.html"), "home"), (page("drops/index.html"), "drops")):
            self.assertRegex(html,
                             r'<div class="band"><img\b[^>]*width="2048" height="768"', name)
        for k, html in self.pages.items():
            self.assertRegex(html,
                             r'<div class="band"><img\b[^>]*width="2048" height="768"', k)
        # the superseded ratios and the /drops/ ratio override are gone
        for ratio in ("16/9", "32/9", "21/9", "5/1", "1983/793", "1933/813"):
            self.assertNotIn(f"aspect-ratio:{ratio}", self.css, ratio)
        self.assertNotIn("homeband", self.css)

    def test_trust_in_product_zone_then_description_news_trends(self):
        for k, html in self.pages.items():
            sec = html.index('<section id="grid"')
            cards = html.index('<div class="grid" id="pg">')
            self.assertLess(html.index('class="ticker"'), sec, k)
            # the purchase-confidence strip sits with the products (toolbar
            # zone), not below a 60-card grid nobody scrolls past
            self.assertLess(sec, html.index('class="trust"'), k)
            self.assertLess(html.index('class="trust"'), cards, k)
            self.assertLess(cards, html.index("In The 2026 Season"), k)
            self.assertLess(cards, html.index("About the "), k)
            for marker in ('class="ftibox"', 'class="newsbox', 'class="trendbox"'):
                if marker in html:
                    self.assertLess(cards, html.index(marker), f"{k}: {marker}")

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

    def test_ticker_live_terms_are_team_safe(self):
        # Raw headline words (roster, practice, opponent names...) must never
        # become "<Word> <Team> shirts" terms. Every live term is built from a
        # tracked player/coach name or the team's own evergreen vocabulary.
        import build  # noqa: E402  (uses the same TRENDS the site was built from)
        generic = {"roster", "practice", "squad", "western", "football", "watch",
                   "free", "second", "opener", "controversial", "trade", "hail", "mary"}
        for k, html in self.pages.items():
            tick = re.search(r'<div class="ticker">(.*?)</div></div>', html, re.S).group(1)
            terms = re.findall(r"<i[^>]*>(.*?)</i>", tick)
            for t in terms:
                first = t.split()[0].lower()
                self.assertNotIn(first, generic, f"{k}: generic ticker term {t!r}")
                self.assertNotIn(first, build.OTHER_TEAMS, f"{k}: other-team ticker term {t!r}")
            for word in build.TICKER_OPPONENTS.get(k, ()):
                self.assertNotRegex(tick, r"(?i)\b%s\b %s shirts" % (word, COLLECTIONS[k]["short"]),
                                    f"{k}: opponent {word!r} in ticker")

    def test_product_first_no_trend_panels(self):
        # Product-first: the Fan Trend Index leaderboard, live player moments
        # and the headline list live on /2026-season/ and /fan-trend-index/
        # only. A team page keeps a one-line season note plus links to both.
        for k, html in self.pages.items():
            self.assertNotIn('class="ftibox"', html, k)
            self.assertNotIn('class="newsbox', html, k)
            self.assertEqual(html.count('class="fti-row"'), 0, k)
            self.assertIn('class="trendbox"', html, k)
            # links are relativised in the built output (../2026-season/index.html)
            self.assertRegex(html, r'href="(?:/|\.\./)2026-season/(?:index\.html)?"', k)
            self.assertRegex(html, r'href="(?:/|\.\./)fan-trend-index/(?:index\.html)?"', k)
        hub = page("2026-season/index.html")
        self.assertIn('class="ftibox"', hub)
        self.assertIn('class="newsbox', hub)

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

    def test_purchase_countdowns_removed_everywhere(self):
        self.assertTrue(self.pages)
        banned = ("Order in", "ships in 2", "data-orderby", "class=\"uc", "order-by countdown chip")
        for slug, html in self.pages.items():
            for term in banned:
                self.assertNotIn(term, html, slug)
        for term in ("Order in", "data-orderby", ".uc[data-orderby]", "ships in 2"):
            self.assertNotIn(term, self.js, term)
        self.assertNotIn(".uc", self.css)

    # ---- SEO landing page, not a mini-checkout -------------------------
    # Gridiron Locker = discovery + persuasion + SEO. Viralstyle =
    # configuration + transaction. These tests are the guard rail on that
    # separation: a product page may PRESENT verified options, never let the
    # visitor pick them here.

    def test_no_mini_checkout_controls(self):
        """No style / size / colourway picker and no checkout button."""
        self.assertTrue(self.pages)
        banned_markup = ('class="stylechip', 'class="swatch', 'class="size"',
                         'class="size ', 'class="sizes"', 'class="swatchrow"',
                         'class="stylelist"', 'class="opts"', "Colourway preview",
                         "checkoutnote", "<select", "<form")
        banned_copy = ("Continue to Secure Checkout", "Add to bag", "Add to cart",
                       "Secure Checkout &rarr;", "Buy Now &rarr;",
                       "You're almost there")
        for slug, html in self.pages.items():
            for term in banned_markup + banned_copy:
                self.assertNotIn(term, html, f"{slug}: {term}")
        # the retired controls must be gone from the shared assets too
        for term in (".stylechip", ".swatch", ".sizes{", ".size{", ".checkoutnote", ".opts{"):
            self.assertNotIn(term, self.css, term)
        for term in ("'.size'", ".stylechip", ".swatch"):
            self.assertNotIn(term, self.js, term)

    def test_shop_now_is_the_only_conversion_action(self):
        live = load_json("data/products_live.json")
        for slug, html in self.pages.items():
            ctas = re.findall(r'<a class="btn[^"]*shopnow"[^>]*>(.*?)</a>', html, re.S)
            self.assertGreaterEqual(len(ctas), 3, slug)      # hero + band + sticky
            for label in ctas:
                self.assertIn("Shop Now", label, slug)
            # every CTA points at this product's own Viralstyle campaign
            hrefs = re.findall(r'<a class="btn[^"]*shopnow" href="([^"]+)"', html)
            self.assertTrue(hrefs, slug)
            for href in hrefs:
                self.assertEqual(href, live[slug]["url"], slug)
            # and no other outbound purchase link sneaks onto the page
            for href in re.findall(r'href="(https://viralstyle\.com[^"]*)"', html):
                self.assertEqual(href, live[slug]["url"], slug)

    def test_cta_explains_the_handoff(self):
        for slug, html in self.pages.items():
            self.assertIn("on the Viralstyle product page", html, slug)
            self.assertIn("Gridiron Locker never takes payment", html, slug)
            self.assertIn("30-day misprint replacement", html, slug)

    def test_top_and_bottom_cta(self):
        """A visitor must never have to scroll back up to convert."""
        for slug, html in self.pages.items():
            hero = html.index('data-placement="hero"')
            band = html.index('data-placement="footer_band"')
            self.assertLess(hero, band, slug)
            self.assertIn('data-placement="sticky_bar"', html, slug)
            self.assertLess(hero, html.index('<h2 id="colours">Available Colours</h2>'), slug)
            self.assertIn('data-placement="apparel"', html, slug)

    def test_handoff_is_tracked(self):
        """Product landing page -> Viralstyle CTR must be measurable."""
        self.assertIn("shop_now_click", self.js)
        self.assertIn("placement:d.placement", self.js)
        self.assertIn("viralstyle_checkout_click", self.js)      # legacy event kept
        self.assertIn("product_page_view", self.js)
        self.assertIn("viralstyle_redirect", self.js)
        self.assertIn("colorway_interaction", self.js)
        self.assertIn("related_product_click", self.js)
        self.assertIn("collection_click", self.js)
        for slug, html in self.pages.items():
            for attr in ("data-slug=", "data-price=", "data-collection=", "data-placement="):
                self.assertIn(attr, html, slug)

    def test_landing_page_sections_present(self):
        wanted = ("Available Colours", "The Idea Behind The Design", "Why It Stands Out",
                  "Who It's For", "Built for Game Day",
                  "Size Information", "Product Details", "Shipping &amp; Delivery",
                  "Frequently Asked Questions", "Ready to gear up?")
        for slug, html in self.pages.items():
            for section in wanted:
                self.assertIn(section, html, f"{slug}: {section}")
            # non-apparel items say "Available Products" instead
            self.assertTrue("Available Apparel" in html or "Available Products" in html, slug)

    def test_h1_is_the_product_name(self):
        live = load_json("data/products_live.json")
        for slug, html in self.pages.items():
            h1 = re.search(r"<h1>(.*?)</h1>", html, re.S).group(1).strip()
            self.assertTrue(h1, slug)
            self.assertNotIn("<", h1, slug)
            self.assertIn(h1, html, slug)
            self.assertNotIn("Shop", h1, slug)

    def test_titles_and_metas_are_unique_per_product(self):
        import build  # noqa: E402
        names = {it["slug"]: it["name"] for it in build.ALL}
        titles = {}
        metas = {}
        for slug, html in self.pages.items():
            t = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
            m = re.search(r'<meta name="description" content="(.*?)">', html, re.S).group(1)
            # 60 chars is the SERP budget; a design whose own name is longer
            # than that falls back to the bare name rather than truncating it.
            if len(unescape(t)) > 60:
                self.assertEqual(unescape(t), names[slug], slug)
            self.assertLessEqual(len(unescape(m)), 160, f"{slug}: {m}")
            self.assertGreater(len(unescape(m)), 70, f"{slug}: {m}")
            titles.setdefault(t, []).append(slug)
            metas.setdefault(m, []).append(slug)
        dupe_t = {k: v for k, v in titles.items() if len(v) > 1}
        dupe_m = {k: v for k, v in metas.items() if len(v) > 1}
        self.assertEqual(dupe_t, {})
        self.assertEqual(dupe_m, {})

    def test_product_copy_is_not_boilerplate(self):
        """The template is shared; the story must not be."""
        stories = {}
        shorts = {}
        whys = {}
        for slug, html in self.pages.items():
            m = re.search(r"<h2>The Idea Behind The Design</h2>(.*?)</div>", html, re.S)
            self.assertIsNotNone(m, slug)
            stories.setdefault(re.sub(r"\s+", " ", m.group(1)), []).append(slug)
            d = re.search(r'<p class="herodeck">(.*?)</p>', html, re.S)
            self.assertIsNotNone(d, slug)
            shorts.setdefault(re.sub(r"\s+", " ", d.group(1)), []).append(slug)
            w = re.search(r"<h2>Why It Stands Out</h2>(.*?)</div>", html, re.S)
            self.assertIsNotNone(w, slug)
            whys.setdefault(re.sub(r"\s+", " ", w.group(1)), []).append(slug)
        # with 100+ designs, a handful of hash collisions is fine; one giant
        # identical block across the catalogue is not.
        cap = max(4, len(self.pages) // 8)
        self.assertLess(max(len(v) for v in stories.values()), cap)
        self.assertLess(max(len(v) for v in shorts.values()), cap)
        self.assertLess(max(len(v) for v in whys.values()), cap)

    def test_no_invented_colour_names(self):
        """Colour NAMES are not in the crawled data, so we must never print them
        as if they were verified swatches."""
        named = re.compile(r'class="(?:swatch|colorchip|colourchip)"')
        for slug, html in self.pages.items():
            self.assertIsNone(named.search(html), slug)
            body = html.split('<h2 id="colours">Available Colours</h2>', 1)
            if len(body) < 2:
                self.fail(slug)
            section = body[1].split("</section>", 1)[0]
            self.assertIn("Viralstyle product page", section, slug)

    def test_colour_claims_match_the_campaign_data(self):
        import build  # noqa: E402
        by_slug = {it["slug"]: it for it in build.ALL}
        for slug, html in self.pages.items():
            it = by_slug[slug]
            if it["colours"] > 1:
                self.assertIn(f"{it['colours']} colour variations", html, slug)
                self.assertIn(f"{it['colours']} colourways", html, slug)
            else:
                self.assertIn("Multiple colour options may be available", html, slug)
                self.assertNotIn("colour variations", html, slug)

    def test_style_and_size_claims_match_the_campaign_data(self):
        import build  # noqa: E402
        by_slug = {it["slug"]: it for it in build.ALL}
        for slug, html in self.pages.items():
            it = by_slug[slug]
            if len(it["styles"]) > 1:
                self.assertIn(f"{len(it['styles'])} garment styles", html, slug)
                for style in it["styles"]:
                    self.assertIn(style.replace("'", "&#x27;"), html, f"{slug}: {style}")
            if it["garment"] not in ("Mug", "Phone Case", "Beanie"):
                sizes = it["sizes_avail"]
                self.assertIn(f"Sizes {sizes[0]}-{sizes[-1]}", html, slug)
                # a campaign that stops at 2XL must not advertise 3XL
                for absent in [s for s in build.SIZES if s not in sizes]:
                    self.assertNotIn(f"-{absent}<", html, f"{slug}: {absent}")

    def test_no_fabricated_trust_signals(self):
        """No invented ratings, reviews, review counts, stock or discounts."""
        for slug, html in self.pages.items():
            for term in ("aggregateRating", "reviewCount", "ratingValue", "fan ratings",
                         'class="stars"', 'class="strike"', 'class="save"',
                         "Save 3", "left in stock", "Only ", "selling fast",
                         "Limited stock", "Hurry"):
                self.assertNotIn(term, html, f"{slug}: {term}")

    def test_related_products_same_collection(self):
        """Related rail is 4-8 designs from the same collection, never mixed."""
        import build  # noqa: E402
        by_slug = {it["slug"]: it for it in build.ALL}
        for slug, html in self.pages.items():
            block = html.split('id="related"', 1)
            self.assertEqual(len(block), 2, slug)
            section = block[1].split("</section>", 1)[0]
            hrefs = re.findall(r'href="(?:\.\./)+shop/([^/]+)/"', section)
            # cards + maybe none else; related grid only
            grid = section.split('class="grid related"', 1)
            self.assertEqual(len(grid), 2, slug)
            cards = re.findall(r'<article class="card[^"]*" data-slug="([^"]+)"',
                               grid[1].split("linkrow", 1)[0])
            self.assertGreaterEqual(len(cards), min(4, len(build.MODEL[by_slug[slug]["col"]]) - 1), slug)
            self.assertLessEqual(len(cards), 8, slug)
            own = by_slug[slug]["col"]
            for other in cards:
                self.assertNotEqual(other, slug, slug)
                self.assertEqual(by_slug[other]["col"], own, f"{slug} -> {other}")

    def test_internal_linking(self):
        import build  # noqa: E402
        by_slug = {it["slug"]: it for it in build.ALL}
        for slug, html in self.pages.items():
            col = build.COLLECTIONS[by_slug[slug]["col"]]
            for href in (f'/{col["slug"]}/', "/collections/",
                         f'/guides/{col["slug"]}-buying-guide/', "/2026-season/",
                         "/drops/", "/size-guide/"):
                self.assertIn(href.lstrip("/"), html, f"{slug}: {href}")

    def test_breadcrumb_and_faq_schema(self):
        for slug, html in self.pages.items():
            types = set()
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',
                                 html, re.S):
                types.add(json.loads(m.group(1)).get("@type"))
            for t in ("BreadcrumbList", "Product", "FAQPage", "Organization"):
                self.assertIn(t, types, f"{slug}: {t}")

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
        home = "/img/hero-home.jpg?v=5"          # repostered 2026-09-10
        heroes = [home] + [COLLECTIONS[k]["hero"] for k in ORDER]
        self.assertTrue(home.endswith("?v=5"), home)
        for k in ORDER:                          # team banners repostered too
            self.assertTrue(COLLECTIONS[k]["hero"].endswith("?v=4"), COLLECTIONS[k]["hero"])
        for url in heroes:
            hero = os.path.join(SITE, url.lstrip("/").split("?")[0])
            self.assertTrue(os.path.isfile(hero), hero)
            self.assertLess(os.path.getsize(hero), 750 * 1024, hero)
        # the PNG masters of the current set are archived, never deployed
        for master in ("gridironlocker-hero-image2.png", "Cleveland browns banner2.png",
                       "Dallas cowboys banner2.png", "green bay banner2.png",
                       "Mich banner2.png"):
            self.assertTrue(os.path.isfile(
                os.path.join(ROOT, "artwork-source", master)), master)
        # ...and the retired crops from the previous set are no longer shipped
        for dead in ("hero-locker.jpg", "hero-locker-sm.jpg"):
            self.assertFalse(os.path.exists(os.path.join(IMG, dead)), dead)

    def test_team_card_crops_hold_no_painted_headline(self):
        # The square homepage team cards are crops of the team banners. Every
        # caption in the set is painted into the left ~1030px, so the crop box
        # must start at or right of x=1280: otherwise a card repeats the
        # headline its own HTML type already carries.
        src = read(os.path.join(SRC, "crop_art.py"))
        box = re.search(r"CROP\s*=\s*\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", src)
        self.assertIsNotNone(box, "crop_art.py must define a single CROP box")
        x0, y0, x1, y1 = (int(v) for v in box.groups())
        self.assertGreaterEqual(x0, 1280, "crop must clear the painted caption")
        self.assertEqual((y0, y1), (0, 768), "crop must span the artwork's full height")
        self.assertEqual(x1, 2048, "crop must reach the right edge of the banner")
        cards = {"cleveland-browns": "team-cleveland.jpg",
                 "green-bay-packers": "team-greenbay.jpg",
                 "dallas-cowboys": "team-dallas.jpg",
                 "michigan": "team-michigan.jpg"}
        for k in ORDER:
            art = os.path.join(SITE, "img", cards[k])
            self.assertTrue(os.path.isfile(art), art)


class Homepage(unittest.TestCase):
    """The storefront funnel: brand -> team -> product -> trending -> editorial.

    These assertions exist because the homepage's job changed: it is no longer
    a long, beautiful catalogue, it is a shopping funnel. Products have to be
    reachable inside the first two or three viewports, the team collections
    have to be one tap from anywhere, and the header must stay free of
    account/cart furniture this store does not own.
    """

    def setUp(self):
        self.html = page("index.html")
        self.css = page("assets/style.css")
        self.js = page("assets/app.js")

    # ---------------------------------------------------------------- header
    def test_header_has_no_account_or_cart_ui(self):
        for marker in ('id="acctBtn"', 'id="cartBtn"', 'id="acctPop"', 'id="cartPop"',
                       'id="cartCount"', 'class="navico', 'aria-label="Cart"',
                       'aria-label="Account"'):
            self.assertNotIn(marker, self.html, marker)
        for marker in ("acctBtn", "cartBtn", "cartCount", "acctPop", "cartPop"):
            self.assertNotIn(marker, self.js, marker)
        for marker in (".navico", ".header-pop"):
            self.assertNotIn(marker, self.css, marker)

    def test_header_keeps_every_shopping_destination_and_search(self):
        nav = between(self.html, '<nav class="menubar"', "</nav>")
        for href in ["./collections/"] + [f'./{COLLECTIONS[k]["slug"]}/' for k in ORDER] \
                + ["./drops/", "./guides/"]:
            self.assertIn(f'href="{href}"', nav, href)
        # search survives in the header (desktop input + mobile panel)
        self.assertIn('class="navsearch"', self.html)
        self.assertIn('class="gsearch"', self.html)
        self.assertIn('id="ms"', self.html)

    # ------------------------------------------------------------------ hero
    def test_hero_is_the_whole_poster_plus_a_copy_block(self):
        # The owner's poster is a finished wide piece of art whose wordmark and
        # headline are painted into the pixels, so the homepage shows it whole
        # (native 2048:768 band) instead of cropping it into a side panel, and
        # puts its own crawlable headline in the copy block underneath.
        hero = between(self.html, '<section class="cbanner home"', "</section>")
        band = re.search(r'<div class="band"><img\b[^>]*>', hero).group(0)
        self.assertIn("hero-home.jpg?v=5", band)
        self.assertIn('width="2048" height="768"', band)
        self.assertIn('fetchpriority="high"', band)
        self.assertNotIn('loading="lazy"', band)
        self.assertIn('alt="', band)
        self.assertIn("Football. Fans. Culture.", hero)
        self.assertIn('<h1 class="hero-title">', hero)
        self.assertEqual(self.html.count("<h1"), 1)          # exactly one H1
        self.assertIn("Original fan-made apparel for the teams we love.", hero)
        self.assertIn("Four cities. Four fanbases. One locker.", hero)
        self.assertIn("Shop By Team", hero)
        self.assertIn("Trending Now", hero)
        self.assertIn("./collections/", hero)
        self.assertIn("./drops/", hero)
        self.assertRegex(hero, r"\d+ fan designs")
        self.assertIn("S&ndash;3XL", hero)
        self.assertIn("Worldwide shipping", hero)
        # ONE headline voice: the block must not restate the poster's brushwork
        # under itself. "Keep it." (a marker-font second headline with a yellow
        # slash) used to sit there, copying the "FOOTBALL LIVES HERE" painted in
        # the artwork above it. The yellow survives only as .hero-rule.
        self.assertNotIn("hero-brush", hero)
        self.assertNotIn("hero-brush", self.css)
        self.assertNotIn("Keep it.", hero)
        self.assertIn('class="hero-rule"', hero)
        self.assertEqual(hero.count("<h1"), 1)
        # the hero headline is visible text (crawlable), not sr-only
        self.assertIn("position:absolute", css_block(self.css, ".sr-only"))
        # the band keeps the artwork's native ratio, so the poster never crops
        self.assertIn("aspect-ratio:2048/768", css_block(self.css, ".cbanner .band"))
        # the home band reuses the collection band: no ratio of its own
        self.assertNotIn("aspect-ratio", css_block(self.css, ".cbanner.home .band"))

    def test_hero_stays_short_enough_to_reveal_the_shop(self):
        # A 2048:768 band plus a compact copy block: on a phone the band is
        # ~40vh and the copy is about one screen, so "Shop By Team" is one
        # flick away.
        band = css_block(self.css, ".cbanner .band")
        self.assertNotIn("min-height", band)                 # never letterboxed
        self.assertIn("aspect-ratio:2048/768", band)
        mob = media_rules(self.css, 560)
        self.assertIn(".cbanner.home .cb-in{padding:20px 16px 24px}", mob)

    # --------------------------------------------------------- funnel order
    def test_hero_copy_block_is_one_centred_statement(self):
        # The block under the poster used to fight itself: three headline-ish
        # rows, and two rules for .hero-title in two different parts of the
        # stylesheet, so whichever came later sized the H1. One scoped block
        # owns the copy now, and the type scale is stated exactly once.
        hero_css = between(self.css, "HERO COPY BLOCK", "Section head tools")
        for sel in (".cbanner.home .hero-copy", ".cbanner.home .hero-kicker",
                    ".cbanner.home .hero-title", ".cbanner.home .hero-sub",
                    ".cbanner.home .hero-cta", ".cbanner.home .hero-facts"):
            self.assertIn(sel + "{", hero_css, sel)
        # centred, one column, capped measure
        self.assertIn("align-items:center", css_block(self.css, ".cbanner.home .hero-copy"))
        self.assertIn("text-align:center", css_block(self.css, ".cbanner.home .hero-copy"))
        # the ONLY rules that size the home H1: the banner block above keeps its
        # collection-title defaults and must not also carry home-hero sizing,
        # which is how two halves of the file ended up fighting over the block.
        banner_css = between(self.css, "COLLECTION / PAGE BANNER", "COUNTDOWN BAR")
        for sel in (".cbanner.home .hero-title", ".cbanner.home .hero-sub",
                    ".cbanner.home .hero-kicker", ".cbanner.home .btnrow"):
            self.assertNotIn(sel, banner_css, sel)
        self.assertIn(".cbanner.home .cb-in{padding:24px 16px 28px}", banner_css)
        # the two CTAs are a matched pair that cannot overflow a phone
        cta = css_block(self.css, ".cbanner.home .hero-cta")
        self.assertIn("justify-content:center", cta)
        self.assertIn("white-space:nowrap", css_block(self.css, ".cbanner.home .hero-cta .btn"))
        mob = media_rules(self.css, 560)
        self.assertIn(".cbanner.home .hero-cta .btn{flex:1 1 0;min-width:0", mob)

    def test_moving_bars_actually_move(self):
        """Both ticker bars are real marquees, not wrapped static lists.

        The bars used to scroll. When the keyframes were deleted the tracks kept
        `flex-wrap:wrap`, so each bar became a ragged paragraph of keywords that
        never moved - "the moving bars not moving and ruined". They must:
          * animate the track with a keyframe ending at -50% (the track holds
            the real items plus an identical aria-hidden clone, so -50% loops
            with no seam and no jump),
          * carry a --dur measured from their own content, so a short keyword
            list does not sprint and a wall of headlines does not crawl,
          * stay on one line, with items that cannot wrap or shrink,
          * pause on hover/focus so a headline can be clicked, not chased,
          * degrade to a plain horizontal scroll, clone hidden, when the
            visitor has asked for reduced motion.
        """
        track = css_block(self.css, ".ticker .track,.newsticker .track")
        self.assertIn("animation:tickmove var(--dur,34s) linear infinite", track)
        self.assertIn("flex-wrap:nowrap", track)
        self.assertNotIn("flex-wrap:wrap", track)
        self.assertIn("@keyframes tickmove", self.css)
        self.assertIn("translate3d(-50%,0,0)", self.css)
        self.assertIn("animation-play-state:paused", self.css)
        for sel in (".ticker i", ".newsticker i"):
            self.assertIn("white-space:nowrap", css_block(self.css, sel), sel)
            self.assertIn("flex:none", css_block(self.css, sel), sel)
        self.assertIn(".tk-clone{display:none}", self.css)   # reduced-motion fallback

    def test_moving_bars_carry_a_seamless_track(self):
        for rel, cls in (("index.html", "newsticker"),
                         (f"{COLLECTIONS['cleveland-browns']['slug']}/index.html", "ticker")):
            html = page(rel)
            bar = re.search(r'<div class="%s">(.*?)</div></div>' % cls, html, re.S)
            self.assertTrue(bar, f"{rel}: {cls} bar missing")
            track = bar.group(1)
            self.assertEqual(track.count('<div class="track"'), 1, rel)
            m = re.search(r'<div class="track" style="--dur:(\d+\.\d)s">', track)
            self.assertTrue(m, f"{rel}: track needs an inline --dur")
            self.assertLess(10.0, float(m.group(1)), rel)
            self.assertGreater(300.0, float(m.group(1)), rel)
            # exactly one clone, marked presentational
            self.assertEqual(track.count('<span class="tk-clone" aria-hidden="true">'), 1, rel)
            run, _, clone = track.partition('<span class="tk-clone"')
            self.assertEqual(len(re.findall(r"<i\b", run)), len(re.findall(r"<i\b", clone)),
                             f"{rel}: clone must repeat every term for a seamless loop")
            self.assertIn("<i", clone, rel)

    def test_news_bar_clone_carries_no_links(self):
        # The readable bar links out to the news sources; the loop's clone is
        # visual only, so no term is duplicated in the tab order or in the
        # outbound links of the page.
        news = re.search(r'<div class="newsticker">(.*?)</div></div>', self.html, re.S).group(1)
        run, _, clone = news.partition('<span class="tk-clone"')
        self.assertIn("<a ", run)
        self.assertNotIn("<a ", clone)
        self.assertNotIn("href", clone)

    def test_product_first_funnel_order(self):
        markers = [
            '<section class="cbanner home"',      # brand
            'class="shopbar"',                   # sticky shop nav (desktop)
            '<section class="teamdeck-sec"',     # which team?
            '<section class="lockersec"',        # Shop The Locker (products)
            '<section class="trendsec"',         # Trending Now (products)
            '<section class="wksec"',            # 2026 season (editorial)
            '<section class="teamsec"',          # deeper team browsing
            '<section class="guidesec"',         # buying guides
            '<section class="customsec"',        # custom design
            '<section class="ftisec"',           # fan trend index
            '<section class="brandsec"',         # newsletter
            "<footer>",
        ]
        pos = 0
        for m in markers:
            i = self.html.index(m, pos)
            self.assertGreater(i, pos, "order: %s" % m)
            pos = i
        # products must come before every editorial band
        first_product = self.html.index('class="pcard')
        for later in ('<section class="wksec"', '<section class="guidesec"',
                      '<section class="ftisec"', 'class="newsticker"'):
            self.assertLess(first_product, self.html.index(later), later)

    def test_main_landmark_and_skip_link(self):
        self.assertIn('<a class="skip" href="#main">', self.html)
        self.assertIn('<main id="main">', self.html)
        self.assertEqual(self.html.count("</main>"), 1)

    # ---------------------------------------------------------- shop by team
    def test_shop_by_team_cards_are_whole_card_links(self):
        sec = between(self.html, '<section class="teamdeck-sec" id="shop-by-team">', "</section>")
        self.assertIn("Shop By", sec)
        cards = re.findall(r'<a class="teamcard[^"]*"[^>]*href="([^"]+)"(.*?)</a>', sec, re.S)
        self.assertEqual(len(cards), len(ORDER))
        for k, (href, card) in zip(ORDER, cards):
            c = COLLECTIONS[k]
            self.assertEqual(href, f'./{c["slug"]}/')                 # whole card links
            self.assertIn(c["short"], card)
            self.assertIn(c["phrase"], card)                          # cultural phrase
            self.assertRegex(card, r"\d+ designs")                    # live count
            self.assertIn("&rarr;", card)                             # arrow affordance
            self.assertNotIn("<button", card)
            art = os.path.basename(f'/img/team-{k.split("-")[0]}.jpg')
            self.assertIn("/img/team-", card)
        # four across, two on tablets and phones - never four tall stacked cards
        self.assertIn("repeat(4,minmax(0,1fr))", css_block(self.css, ".teamdeck-grid"))
        self.assertIn(".teamdeck-grid{grid-template-columns:repeat(2,minmax(0,1fr))",
                      media_rules(self.css, 980))
        self.assertNotIn(".teamdeck-grid{grid-template-columns:1fr", media_rules(self.css, 560))

    def test_team_card_counts_match_the_live_catalogue(self):
        live = load_json("data/collections.json")
        sec = between(self.html, '<section class="teamdeck-sec" id="shop-by-team">', "</section>")
        counts = [int(n) for n in re.findall(r"(\d+) designs", sec)]
        self.assertEqual(len(counts), len(ORDER))
        for k, n in zip(ORDER, counts):
            self.assertGreater(n, 0, k)
            self.assertLessEqual(n, len(live[k]["products"]), k)      # never invented
        self.assertIn(f"{sum(counts)} fan designs", self.html)        # hero total agrees

    # ------------------------------------------------------- shop the locker
    def test_shop_the_locker_is_a_product_rail_right_after_the_teams(self):
        self.assertLess(self.html.index('<section class="teamdeck-sec"'),
                        self.html.index('<section class="lockersec"'))
        sec = between(self.html, '<section class="lockersec"', "</section>")
        self.assertIn("Shop The", sec)
        self.assertIn("Fan-made gear worth wearing on game day.", sec)
        self.assertGreaterEqual(sec.count('class="pcard'), 8)
        # never a dead end: a rail-end tile plus an "all designs" link
        self.assertIn('class="rail-end" href="./collections/"', sec)
        self.assertIn('href="./search/"', sec)
        # desktop arrows exist and are wired; touch just swipes
        self.assertIn('class="rail-nav" data-rail="lockerRail"', sec)
        self.assertEqual(sec.count('<button class="rn"'), 2)
        self.assertIn("rail-nav", self.js)
        rail = css_block(self.css, ".prail")
        self.assertIn("overflow-x:auto", rail)
        self.assertIn("scroll-snap-type:x proximity", rail)
        self.assertIn("flex:0 0 clamp(200px,23vw,252px)", css_block(self.css, ".prail>*"))

    def test_product_cards_are_clean_and_normalised(self):
        card = re.search(r'<a class="pcard[^>]*>.*?</a>', self.html, re.S).group(0)
        for part in ('class="pc-ph"', "<img", 'class="pc-meta"', "<h3 class=\"pc-name\"",
                     'class="pc-price"', "View design"):
            self.assertIn(part, card, part)
        self.assertIn("$", card)
        self.assertNotIn("<button", card)                     # the tile is one link
        ph = css_block(self.css, ".pc-ph")
        self.assertIn("aspect-ratio:1/1", ph)                 # one shape for every mockup
        self.assertIn("object-fit:contain", css_block(self.css, ".pc-ph img"))
        # no fake urgency anywhere on the page
        low = self.html.lower()
        for banned in ("only 3 left", "hurry", "selling fast", "best seller", "bestseller",
                       "limited time offer", "act now"):
            self.assertNotIn(banned, low, banned)

    def test_every_homepage_product_link_is_a_real_product_page(self):
        slugs = set(re.findall(r'<a class="pcard[^"]*" href="\./shop/([^/]+)/"', self.html))
        self.assertGreaterEqual(len(slugs), 20)
        for slug in slugs:
            self.assertTrue(os.path.isfile(os.path.join(SITE, "shop", slug, "index.html")), slug)

    # -------------------------------------------------------------- trending
    def test_trending_now_is_a_four_column_grid_of_real_designs(self):
        sec = between(self.html, '<section class="trendsec" id="trending">', "</section>")
        self.assertIn("Trending", sec)
        self.assertEqual(sec.count('class="pcard'), 8)
        self.assertIn('href="./drops/"', sec)
        self.assertIn("View All Designs", sec)
        self.assertNotIn("best seller", sec.lower())
        self.assertIn("repeat(4,minmax(0,1fr))", css_block(self.css, ".pgrid.four"))
        self.assertIn(".pgrid.four{grid-template-columns:repeat(2,minmax(0,1fr))",
                      media_rules(self.css, 700))

    # ---------------------------------------------------------------- season
    def test_season_block_is_editorial_and_data_driven(self):
        sec = between(self.html, '<section class="wksec" id="season">', "</section>")
        self.assertIn("2026 season", sec)
        self.assertRegex(sec, r"The Season Is <span[^>]*>(Live|Almost Here)")
        self.assertIn("Explore The Season", sec)
        self.assertIn('href="./2026-season/"', sec)

    # ------------------------------------------------------- team collections
    def test_team_sections_and_counts(self):
        secs = re.findall(r'<section class="teamsec"(.*?)</section>', self.html, re.S)
        self.assertEqual(len(secs), 4)
        for s in secs:
            self.assertEqual(len(re.findall(r'<a class="pcard', s)), 4)
            self.assertIn("Explore", s)

    # ---------------------------------------------------------------- guides
    def test_guides_sit_below_the_products_and_link_real_pages(self):
        self.assertLess(self.html.index('<section class="trendsec"'),
                        self.html.index('<section class="guidesec"'))
        sec = between(self.html, '<section class="guidesec"', "</section>")
        for href in ("./guides/2026-week-1-shirts/", "./guides/", "./size-guide/", "./shipping/"):
            self.assertIn(f'href="{href}"', sec, href)
        for href in set(re.findall(r'href="\.\/([^"]*)"', sec)):
            self.assertTrue(os.path.isfile(os.path.join(SITE, href, "index.html")), href)

    # ---------------------------------------------------------------- custom
    def test_custom_design_form_is_preserved(self):
        sec = between(self.html, '<section class="customsec" id="custom-design">', "</section>")
        self.assertIn("Your idea.", sec)
        self.assertIn("Request Custom Apparel", sec)
        self.assertIn('id="customForm"', sec)
        self.assertIn('data-formsubmit="1"', sec)
        for field in ('name="name"', 'name="email"', 'name="team"', 'name="garment"',
                      'name="idea"', 'name="details"', 'name="_subject"', 'name="_honey"'):
            self.assertIn(field, sec, field)
        self.assertIn('id="formmsg"', sec)
        # the homepage does not also fire the floating custom-design popup
        self.assertNotIn('id="csPop"', self.html)
        self.assertIn('id="csPop"', page("cleveland-browns-shirts/index.html"))

    # ------------------------------------------------------- index/newsletter
    def test_compact_four_entry_fti_strip(self):
        sec = between(self.html, '<section class="ftisec">', "</section>")
        self.assertEqual(sec.count('class="fti-chip"'), 4)
        self.assertIn('href="./fan-trend-index/"', sec)
        self.assertIn("repeat(4,minmax(0,1fr))", css_block(self.css, ".fti-chips"))

    def test_full_index_page_retained(self):
        fti = page("fan-trend-index/index.html")
        data = load_json("data/trends.json")
        rows = (data.get("fan_trend_index") or {}).get("rows") or []
        self.assertEqual(fti.count('class="fti-card reveal"'), len(rows))
        self.assertGreater(len(rows), 4)

    def test_newsletter_is_last_and_still_works(self):
        sec = between(self.html, '<section class="brandsec" id="newsletter">', "</section>")
        self.assertIn("Stay In The", sec)
        self.assertIn("Football culture, new designs and game-day inspiration.", sec)
        self.assertIn('id="newsForm"', sec)
        self.assertIn('id="newsEmail"', sec)
        self.assertIn("Join", sec)
        self.assertLess(self.html.index('<section class="ftisec"'),
                        self.html.index('<section class="brandsec"'))

    # ------------------------------------------------- sticky shop navigation
    def test_sticky_shop_navigation_desktop_and_mobile(self):
        bar = between(self.html, '<div class="shopbar" id="shopbar">', "</div>\n<nav")
        for k in ORDER:
            self.assertIn(f'href="./{COLLECTIONS[k]["slug"]}/"', bar, k)
        self.assertIn('href="./drops/"', bar)
        self.assertIn('href="./search/"', bar)
        self.assertIn("position:sticky", media_rules(self.css, 0) + self.css)
        self.assertIn(".shopbar{display:none}", self.css)
        mob = between(self.html, '<nav class="mobshop" id="mobshop"', "</nav>")
        self.assertIn("#shop-by-team", mob)
        self.assertIn("#trending", mob)
        self.assertIn('href="./search/"', mob)
        self.assertIn("hidden", self.html[self.html.index('<nav class="mobshop"'):][:200])
        self.assertIn("env(safe-area-inset-bottom)", css_block(self.css, ".mobshop"))
        self.assertIn("mobshop", self.js)

    # ---------------------------------------------------------------- footer
    def test_footer_columns(self):
        foot = self.html[self.html.index("<footer>"):]
        for head in ("Shop", "Help", "Brand", "Compliance"):
            self.assertIn(f"<h2>{head}</h2>", foot, head)
        for href in ("./collections/", "./drops/", "./faq/", "./shipping/", "./contact/",
                     "./about/", "./guides/", "./trademark-notice/", "./privacy/"):
            self.assertIn(f'href="{href}"', foot, href)
        self.assertIn("not affiliated with", foot)
        for banned in ("official merchandise", "officially licensed", "authorized dealer"):
            self.assertNotIn(banned, foot.lower(), banned)

    # ------------------------------------------------------------------- SEO
    def test_seo_and_hero_preserved(self):
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/">', self.html)
        self.assertIn("hero-home.jpg?v=5", self.html)          # OG image = new poster
        self.assertIn('"@type":"WebSite"', self.html)
        self.assertIn('"@type":"Organization"', self.html)
        self.assertIn('"@type":"ItemList"', self.html)
        self.assertIn('<meta name="description"', self.html)
        # heading order never skips a level
        levels = [int(t) for t in re.findall(r"<h([1-3])[ >]", self.html)]
        self.assertEqual(levels[0], 1)
        for prev, cur in zip(levels, levels[1:]):
            self.assertLessEqual(cur - prev, 1)

    def test_below_the_fold_imagery_is_lazy(self):
        body = self.html[self.html.index('<section class="teamdeck-sec"'):]
        imgs = re.findall(r"<img [^>]*>", body)
        self.assertGreater(len(imgs), 20)
        eager = [i for i in imgs if 'loading="lazy"' not in i]
        self.assertLessEqual(len(eager), 6, eager[:3])         # only the first rail tiles
        for img in imgs:
            self.assertIn("alt=", img)
            self.assertIn("width=", img)
            self.assertIn("height=", img)


class SearchCatalogue(unittest.TestCase):
    def setUp(self):
        self.html = page("search/index.html")
        self.js = page("assets/app.js")

    def test_all_designs_indexed(self):
        # rendered designs = live feed entries that still have artwork;
        # assert a floor so a silent data regression is caught loudly
        self.assertGreaterEqual(len(re.findall(r'<article class="card', self.html)), 100)

    def test_filter_dimensions_present(self):
        for marker in ('id="q"', 'id="sort"', 'id="price"',
                       'data-st="player"', 'data-st="funny"',
                       'data-st="retro"', 'data-st="family"',
                       'data-team="cleveland-browns"', 'data-f="T-Shirt"'):
            self.assertIn(marker, self.html, marker)
        for opt in ("Under $20", "$20 - $25", "$25 - $30", "$30+"):
            self.assertIn(opt, self.html, opt)

    def test_cards_carry_filter_attributes(self):
        for marker in ("data-type=", "data-team=", "data-theme="):
            self.assertIn(marker, self.html, marker)

    def test_quick_view_button_on_every_card(self):
        self.assertEqual(len(re.findall(r'class="qv"', self.html)),
                         len(re.findall(r'<article class="card', self.html)))

    def test_quick_view_modal_wired(self):
        for marker in ("qvmodal", "qv-overlay", "qv-cta", "Quick view"):
            self.assertIn(marker, self.js, marker)

    def test_style_filter_reads_theme_attribute(self):
        self.assertIn("styleOf", self.js)
        self.assertIn("data-theme", self.js)


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


class CanonicalUrls(unittest.TestCase):
    """One crawlable URL per page.

    GitHub Pages serves /faq/ and /faq/index.html with a 200 and redirects
    neither to the other, so linking the index.html spelling published a
    second, non-canonical URL for every page - the only one Googlebot could
    discover by following links. Search Console reported the whole storefront
    as duplicates and split its ranking signals. These tests keep internal
    links, <link rel="canonical"> and the sitemap on the same single URL.
    """

    # /ops/ is the private control room: robots.txt disallows it, nothing links
    # to it publicly, and its pages carry no canonical tag.
    def storefront_pages(self):
        for base, _, files in os.walk(SITE):
            for f in files:
                if not f.endswith(".html"):
                    continue
                fp = os.path.join(base, f)
                rel = os.path.relpath(fp, SITE)
                if rel.split(os.sep)[0] in ("ops", "marketing"):
                    continue
                yield rel, read(fp)

    def test_no_internal_link_uses_the_index_html_spelling(self):
        offenders = []
        for rel, html in self.storefront_pages():
            for href in re.findall(r'(?:href|src|data-src)="((?:\.{1,2}/|/)[^"]*)"', html):
                if re.search(r"(?:^|/)index\.html(?:[?#]|$)", href):
                    offenders.append(f"{rel}: {href}")
        self.assertEqual(offenders, [], "internal links must use the canonical directory URL")

    def test_page_links_keep_a_trailing_slash(self):
        offenders = []
        for rel, html in self.storefront_pages():
            for href in re.findall(r'href="((?:\.{1,2}/)[^"]*)"', html):
                path = re.split(r"[?#]", href, 1)[0]
                if not path or path.endswith("/"):
                    continue
                if "." in os.path.basename(path):   # a real file (.css/.webp/.xml)
                    continue
                offenders.append(f"{rel}: {href}")
        self.assertEqual(offenders, [], "directory links must end in / to match the canonical URL")

    def test_every_internal_link_target_is_its_own_canonical(self):
        """Following any internal link lands on a page that self-canonicalises.

        This is the assertion that actually catches the duplicate-URL bug: it
        resolves each link to the page it serves and compares that page's
        canonical tag with the URL that was linked.
        """
        domain = load_json("src/config.json")["domain"].rstrip("/")
        mismatches = []
        for rel, html in self.storefront_pages():
            here = os.path.dirname(os.path.join(SITE, rel))
            for href in re.findall(r'href="((?:\.{1,2}/)[^"]*)"', html):
                path = re.split(r"[?#]", href, 1)[0]
                target = os.path.normpath(os.path.join(here, path))
                if not os.path.isdir(target):
                    continue
                index = os.path.join(target, "index.html")
                if not os.path.isfile(index):
                    continue
                linked = domain + "/" + os.path.relpath(target, SITE).replace(os.sep, "/") + "/"
                linked = linked.replace("/./", "/")
                found = re.search(r'<link rel="canonical" href="([^"]+)"', read(index))
                if found and found.group(1) != linked:
                    mismatches.append(f"{rel} -> {href}: canonical {found.group(1)} != {linked}")
        self.assertEqual(mismatches, [])

    def test_404_is_noindex_and_absent_from_the_sitemap(self):
        html = page("404.html")
        self.assertIn('<meta name="robots" content="noindex,follow">', html)
        self.assertNotIn("<loc>https://gridironlocker.store/404.html</loc>", page("sitemap.xml"))

    def test_real_pages_stay_indexable(self):
        for rel in ("index.html", "collections/index.html", "faq/index.html",
                    "cleveland-browns-shirts/index.html"):
            self.assertIn('content="index,follow,max-image-preview:large,max-snippet:-1"',
                          page(rel), rel)

    def test_canonical_matches_sitemap_and_own_location(self):
        sm = page("sitemap.xml")
        locs = set(re.findall(r"<loc>([^<]+)</loc>", sm))
        domain = load_json("src/config.json")["domain"].rstrip("/")
        checked = 0
        for rel, html in self.storefront_pages():
            found = re.search(r'<link rel="canonical" href="([^"]+)"', html)
            if not found or not rel.endswith("index.html"):
                continue
            own = domain + "/" + os.path.dirname(rel).replace(os.sep, "/")
            own = (own + "/").replace("//", "/").replace(":/", "://")
            self.assertEqual(found.group(1), own, rel)
            self.assertIn(found.group(1), locs, f"{rel} canonical is missing from sitemap.xml")
            checked += 1
        self.assertGreaterEqual(checked, 100)


NEW_BROWNS = [
    "limited-edition-no-fly-zone-denzel",
    "limited-edition-rock-out-denzel",
    "limited-edition-the-wall-graham",
]
NEW_BROWNS_URLS = {
    "limited-edition-no-fly-zone-denzel":
        "https://viralstyle.com/kebystore/limited-edition-no-fly-zone-denzel",
    "limited-edition-rock-out-denzel":
        "https://viralstyle.com/kebystore/limited-edition-rock-out-denzel",
    "limited-edition-the-wall-graham":
        "https://viralstyle.com/kebystore/limited-edition-the-wall-graham",
}
NEW_ZERO_ONE = [
    "limited-edition-0-01-football",
    "limited-edition-0-01-h-a-i-l",
]
NEW_ZERO_ONE_URLS = {
    "limited-edition-0-01-football":
        "https://viralstyle.com/kebystore/limited-edition-0-01-football",
    "limited-edition-0-01-h-a-i-l":
        "https://viralstyle.com/kebystore/limited-edition-0-01-h-a-i-l",
}
# Locked-in hero / logo URLs from current main - must never drift.
HERO_LOGO_LOCK = {
    "cleveland-browns": ("/img/hero-cleveland.jpg?v=4", "/img/browns-logo1.webp?v=1"),
    "dallas-cowboys": ("/img/hero-dallas.jpg?v=4", "/img/dallas-logo1.webp?v=1"),
    "green-bay-packers": ("/img/hero-greenbay.jpg?v=4", "/img/green-bay-logo1.webp?v=1"),
    "michigan": ("/img/hero-michigan.jpg?v=4", "/img/michigan-logo1.webp?v=1"),
}


class ThreeNewBrownsProducts(unittest.TestCase):
    """Regression coverage for the three added Cleveland Browns designs."""

    @classmethod
    def setUpClass(cls):
        cls.products = load_json("data/products.json")
        cls.live = load_json("data/products_live.json")
        cls.cols = load_json("data/collections.json")

    def test_slugs_in_source_catalogue(self):
        for slug in NEW_BROWNS:
            self.assertIn(slug, self.products, slug)
            self.assertIn(slug, self.live, slug)

    def test_belong_to_cleveland_browns_collection(self):
        slugs = [p["slug"] for p in self.cols["cleveland-browns"]["products"]]
        for slug in NEW_BROWNS:
            self.assertIn(slug, slugs, slug)
        # The exact count is deliberately not locked: the daily refresh
        # re-crawls the catalogue, so the size legitimately drifts (85 when
        # the three designs above were added, 66 at the last refresh). What
        # must never change is that the three added slugs stay in the
        # collection (asserted above) and it is still a real catalogue.
        self.assertGreaterEqual(len(slugs), 60)

    def test_product_pages_generated_with_checkout_and_images(self):
        for slug in NEW_BROWNS:
            fp = os.path.join(SITE, "shop", slug, "index.html")
            self.assertTrue(os.path.isfile(fp), slug)
            html = read(fp)
            self.assertIn(NEW_BROWNS_URLS[slug], html, slug)       # checkout preserved
            self.assertIn('https://gridironlocker.store/cleveland-browns-shirts/', html, slug)
            img = self.live[slug].get("img", {})
            self.assertIn("front", img, slug)
            for tag, rel in img.items():
                self.assertTrue(os.path.isfile(os.path.join(SITE, rel.lstrip("/"))),
                                f"{slug} {rel}")

    def test_all_local_product_images_are_valid_webp(self):
        for slug in NEW_BROWNS:
            for tag, rel in self.live[slug].get("img", {}).items():
                self.assertTrue(rel.endswith(".webp"), f"{slug} {rel}")
                with open(os.path.join(SITE, rel.lstrip("/")), "rb") as fh:
                    head = fh.read(12)
                self.assertTrue(head.startswith(b"RIFF") and head[8:12] == b"WEBP",
                                f"{slug} {rel} is not a WebP")

    def test_no_png_or_jpg_masters_for_new_products(self):
        imgdir = os.path.join(SITE, "img")
        for base, _, files in os.walk(imgdir):
            for f in files:
                low = f.lower()
                if any(low.startswith(s) for s in NEW_BROWNS):
                    self.assertTrue(low.endswith(".webp"), f"{base}/{f}")
        # product mockups dir must stay WebP-only
        pdir = os.path.join(imgdir, "p")
        bad = [f for f in os.listdir(pdir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        self.assertEqual(bad, [], bad)

    def test_no_countdown_or_delivery_deadline_language_on_new_pages(self):
        banned = ("Order in", "data-orderby", 'class="uc', "ships in 2",
                  "Arrives before kickoff", "Wear it for Week 1", "Arrives by Week 1",
                  "before the opener", "in time for Week 1")
        for slug in NEW_BROWNS:
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            for term in banned:
                self.assertNotIn(term, html, f"{slug}: {term}")

    def test_shipping_facts_and_disclaimer_on_new_pages(self):
        for slug in NEW_BROWNS:
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertIn("US shipping from $4.95", html, slug)
            self.assertIn("5-12 business days", html, slug)
            self.assertIn("independent fan", html.lower(), slug)

    def test_no_missing_local_references_on_new_pages(self):
        attr = re.compile(r'(?:src|data-src|href|content)="([^"]+)"')
        for slug in NEW_BROWNS:
            fp = os.path.join(SITE, "shop", slug, "index.html")
            for m in attr.finditer(read(fp)):
                val = m.group(1).strip()
                if not val.startswith("/") or val.startswith("//"):
                    continue
                val = val.split("#")[0].split("?")[0]
                if val in ("", "/"):
                    continue
                cand = os.path.normpath(os.path.join(SITE, val.lstrip("/")))
                if os.path.isdir(cand):
                    cand = os.path.join(cand, "index.html")
                self.assertTrue(os.path.isfile(cand), f"{slug}: {val}")

    def test_hero_and_logo_urls_unchanged(self):
        for k, (hero, logo) in HERO_LOGO_LOCK.items():
            self.assertEqual(COLLECTIONS[k]["hero"], hero, k)
            self.assertEqual(COLLECTIONS[k]["logo"], logo, k)
        for k in ORDER:
            html = page(f"{COLLECTIONS[k]['slug']}/index.html")
            self.assertIn(COLLECTIONS[k]["hero"].split("?")[0], html, k)


NEW_ZERO_ONE_NAMES = {
    "limited-edition-0-01-football": "Limited Edition 0-01 Football Michigan Tee",
    "limited-edition-0-01-h-a-i-l": "Limited Edition 0-01 H A I L Michigan Tee",
}


class MichiganZeroOneProducts(unittest.TestCase):
    """Regression coverage for the two Michigan 0-01 designs.

    These campaigns are added before the daily refresh downloads their
    mockups, so their product pages hot-link Viralstyle assets until dl.py
    produces local WebP. abs_url() must let those remote URLs through
    untouched - never prefix the store domain a second time.
    """

    @classmethod
    def setUpClass(cls):
        cls.products = load_json("data/products.json")
        cls.live = load_json("data/products_live.json")
        cls.cols = load_json("data/collections.json")

    def test_slugs_in_source_catalogue(self):
        for slug in NEW_ZERO_ONE:
            self.assertIn(slug, self.products, slug)
            self.assertIn(slug, self.live, slug)

    def test_belong_to_michigan_collection(self):
        slugs = [p["slug"] for p in self.cols["michigan"]["products"]]
        for slug in NEW_ZERO_ONE:
            self.assertIn(slug, slugs, slug)
        self.assertGreaterEqual(len(slugs), 17)

    def test_product_pages_generated_with_checkout(self):
        for slug in NEW_ZERO_ONE:
            fp = os.path.join(SITE, "shop", slug, "index.html")
            self.assertTrue(os.path.isfile(fp), slug)
            html = read(fp)
            self.assertIn(NEW_ZERO_ONE_URLS[slug], html, slug)
            self.assertIn("https://gridironlocker.store/michigan-wolverines-shirts/", html, slug)
            self.assertIn(NEW_ZERO_ONE_NAMES[slug], html, slug)

    def test_remote_fallback_and_no_double_prefix(self):
        for slug in NEW_ZERO_ONE:
            img = self.live[slug].get("img", {})
            self.assertIn("front", img, slug)
            for tag, rel in img.items():
                if rel.startswith("/"):
                    self.assertTrue(
                        os.path.isfile(os.path.join(SITE, rel.lstrip("/"))),
                        f"{slug} {rel}")
                else:
                    self.assertTrue(
                        rel.startswith("https://assets.viralstyle.com/"),
                        f"{slug} {rel}")
                self.assertNotIn("gridironlocker.storehttps://", rel, f"{slug} {rel}")
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertNotIn("gridironlocker.storehttps://", html, slug)

    def test_schema_and_sitemap_use_remote_images(self):
        # Until dl.py lands local WebP the Product schema hot-links Viralstyle
        # assets; once they are local, abs_url() prefixes the store domain.
        # Either is valid - a double-prefixed URL is not.
        for slug in NEW_ZERO_ONE:
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertIn('"image":[', html, slug)
            snippet = html.split('"image":[', 1)[1][:500]
            self.assertTrue(
                "assets.viralstyle.com" in snippet
                or "/img/p/" + slug in snippet,
                slug)
            self.assertNotIn("https://gridironlocker.storehttps://", html, slug)
        sm = page("sitemap-images.xml")
        for slug in NEW_ZERO_ONE:
            self.assertIn(slug, sm, slug)
            self.assertNotIn("gridironlocker.storehttps://", sm, slug)

    def test_catalogue_copy_added(self):
        from catalog import CATALOG
        for slug in NEW_ZERO_ONE:
            self.assertIn(slug, CATALOG, slug)
            self.assertEqual(CATALOG[slug]["name"], NEW_ZERO_ONE_NAMES[slug], slug)


class CreatorCollab(unittest.TestCase):
    """Joe's Michigan Locker: the dedicated creator collection at /michigan/joe/.

    Guard rails for the creator-collaboration contract:
    * one permanent, addressable page with the exact brief copy,
    * the curation in data/creators.json is what ships - no more, no less,
    * every product link carries ?creator=JOE (the attribution forward),
    * the commission rate stays OFF the customer-facing page (internal only),
    * nothing reads as an official University of Michigan store.
    """

    def setUp(self):
        self.html = page("michigan/joe/index.html")
        self.js = page("assets/app.js")
        self.css = page("assets/style.css")
        self.creators = load_json("data/creators.json")["creators"]["joe"]

    def test_page_exists_and_is_indexable(self):
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/michigan/joe/">',
                      self.html)
        self.assertIn('content="index,follow,max-image-preview:large,max-snippet:-1"',
                      self.html)
        self.assertIn("<loc>https://gridironlocker.store/michigan/joe/</loc>",
                      page("sitemap.xml"))
        self.assertIn("data-creator-page=\"JOE\"", self.html)

    def test_brief_copy_is_present(self):
        h1 = unescape(re.search(r"<h1>(.*?)</h1>", self.html, re.S).group(1))
        self.assertEqual(h1.replace("<span class=\"jgold\">", "").replace("</span>", ""),
                         "JOE'S MICHIGAN LOCKER")
        for line in ("Michigan football gear, hand-picked by Joe.",
                     "10% OFF YOUR ORDER",
                     "USE CODE: JOE10",
                     "Shop Joe's Picks",
                     "Joe has teamed up with Gridiron Locker to bring Michigan fans",
                     "More Michigan designs coming as we build this collection together.",
                     "Shop The Locker"):
            self.assertIn(line, self.html, line)
        # The brief removes the old support lines and the over-claim that every
        # order is attributed to Joe.
        for stale in ("Powered by Gridiron Locker",
                      "YOU'RE IN JOE'S LOCKER.",
                      "Every order placed through Joe's collection supports the collaboration"):
            self.assertNotIn(stale, self.html, stale)

    def test_no_commission_terms_on_customer_page(self):
        low = self.html.lower()
        self.assertNotIn("20%", low)
        self.assertNotIn("commission", low)
        # \b so the honest "not affiliated with" disclaimer does not trip this
        self.assertIsNone(re.search(r"\baffiliate\b", low))
        self.assertNotIn("referral code", low)

    def test_not_an_official_university_store(self):
        low = self.html.lower()
        for banned in ("official university of michigan store",
                       "officially licensed michigan product. yes",
                       "authorized retailer", "university of michigan license"):
            self.assertNotIn(banned, low, banned)
        self.assertIn("not an official michigan store", low)
        self.assertIn("not affiliated with, endorsed by or licensed by the university of michigan",
                      low)

    def test_featured_row_matches_creators_json(self):
        live = load_json("data/products_live.json")
        row = self.html[self.html.index('id="picks"'):
                        self.html.index('id="locker"')]
        slugs = re.findall(r'<a class="jfeat[^"]*" href="[^"]*?/shop/([a-z0-9-]+)/\?creator=JOE"',
                           row)
        self.assertEqual(len(slugs), 4, slugs)
        self.assertEqual(slugs, self.creators["featured"])
        for s in slugs:
            self.assertIn(s, live, s)

    def test_grid_is_exactly_the_curated_picks(self):
        live = load_json("data/products_live.json")
        sec = self.html[self.html.index('id="locker"'):
                        self.html.index('class="jfaq"')]
        slugs = re.findall(r'<a class="jcard[^"]*" href="[^"]*?/shop/([a-z0-9-]+)/\?creator=JOE"',
                           sec)
        self.assertEqual(slugs, self.creators["picks"])
        for s in slugs:
            self.assertIn(s, live, s)

    def test_every_card_carries_price_shop_and_creator_tag(self):
        for m in re.finditer(r'<a class="j(?:feat|card)"(.*?)(?=<a class="j(?:feat|card)|</section>)',
                             self.html, re.S):
            block = m.group(1)
            self.assertIn("?creator=JOE", block, block[:80])
            self.assertIn("$", block)
            self.assertIn('class="jshop"', block)
            self.assertIn("width=\"530\" height=\"630\"", block)  # no layout shift

    def test_local_references_resolve(self):
        fp = os.path.join(SITE, "michigan/joe/index.html")
        attr = re.compile(r'(?:src|data-src|href|content)="([^"]+)"')
        for m in attr.finditer(self.html):
            val = m.group(1).strip()
            if not (val.startswith("/") or val.startswith("./") or val.startswith("../")):
                continue
            val = val.split("#")[0].split("?")[0]
            if val in ("", "/", "./"):
                continue
            cand = os.path.normpath(
                os.path.join(SITE, val.lstrip("/")) if val.startswith("/")
                else os.path.normpath(os.path.join(os.path.dirname(fp), val)))
            if os.path.isdir(cand):
                cand = os.path.join(cand, "index.html")
            self.assertTrue(os.path.isfile(cand), f"{fp}: {val}")

    def test_attribution_plumbing_in_app_js(self):
        for term in ("gl_creator", "creator_attribution_set", "creator_page_view",
                     "creator_session", "utm_campaign", "GL_CREATOR",
                     "TTL=90*86400", "SameSite=Lax"):
            self.assertIn(term, self.js, term)
        self.assertIn("creator:window.GL_CREATOR", self.js)

    def test_hero_art_ships_and_is_light(self):
        hero = os.path.join(SITE, "img/hero-joe.jpg")
        self.assertTrue(os.path.isfile(hero))
        self.assertLess(os.path.getsize(hero), 750 * 1024)
        self.assertNotIn("hero-joe.jpg",
                         [f for f in os.listdir(os.path.join(SITE, "img"))
                          if f.lower().endswith(".png")])

    def test_mobile_first_grid_and_tap_targets(self):
        mob = media_rules(self.css, 760)
        self.assertIn(".jbar{display:flex", mob)
        self.assertIn("main.jlock{padding-bottom:82px}", mob)
        self.assertIn(".jlock .jbtn{", self.css)
        self.assertIn("min-height:48px", self.css)

    def test_footer_advertises_the_locker(self):
        home = page("index.html")
        self.assertIn('href="./michigan/joe/"', home)

    def test_michigan_collection_links_to_the_locker(self):
        mich = page("michigan-wolverines-shirts/index.html")
        self.assertIn('href="../michigan/joe/"', mich)
        self.assertIn("Joe&#x27;s Michigan Locker", mich)

    def test_schema_is_a_collection_with_itemlist_and_faq(self):
        self.assertIn('"@type":"CollectionPage"', self.html)
        self.assertIn('"@type":"ItemList"', self.html)
        self.assertIn('"@type":"FAQPage"', self.html)
        self.assertIn('"@type":"BreadcrumbList"', self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
