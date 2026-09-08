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
        self.assertIn("aspect-ratio:1933/813", comp)

    def test_hero_bands_are_uncropped(self):
        # The homepage hero is now an editorial HTML/text collage. The
        # collection banner bands still match their real art's native ratio
        # (home poster 1983x793, teams 1933x813) at every breakpoint so the
        # full banner shows and none of them get cropped to a 16:9 box or a
        # wide strip.
        base = css_block(self.css, ".cbanner .band")
        self.assertIn("aspect-ratio:1983/793", base)
        comp = css_block(self.css, ".cbanner.compact .band")
        self.assertIn("aspect-ratio:1933/813", comp)
        # /drops/ shows the home poster inside the compact layout, so it keeps
        # the home ratio instead of the team one.
        self.assertIn("aspect-ratio:1983/793",
                      css_block(self.css, ".cbanner.compact.homeband .band"))
        # the home page now uses the HTML hero + one cinematic art panel;
        # /drops/ + team pages keep the full banner bands
        self.assertRegex(page("index.html"), r'<section class="hero editorial"')
        self.assertRegex(page("index.html"), r'class="hero-art"')
        self.assertRegex(page("drops/index.html"),
                         r'<div class="band"><img\b[^>]*width="1983" height="793"')
        for k, html in self.pages.items():
            self.assertRegex(html,
                             r'<div class="band"><img\b[^>]*width="1933" height="813"', k)
        for ratio in ("16/9", "32/9", "21/9", "5/1"):
            self.assertNotIn(f"aspect-ratio:{ratio}", self.css, ratio)

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

    def test_seamless_checkout_copy(self):
        for slug, html in self.pages.items():
            self.assertIn("You're almost there - finish on our print partner's secure checkout.",
                          html, slug)
            self.assertNotIn("This opens our print partner's secure checkout in a new tab", html, slug)
            self.assertIn("Continue to Secure Checkout", html, slug)
            self.assertIn("30-day misprint replacement", html, slug)

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
        home = "/img/hero-home.jpg?v=4"          # swapped 2026-09-08
        heroes = [home] + [COLLECTIONS[k]["hero"] for k in ORDER]
        self.assertTrue(home.endswith("?v=4"), home)
        for k in ORDER:                          # team banners unchanged
            self.assertTrue(COLLECTIONS[k]["hero"].endswith("?v=3"), COLLECTIONS[k]["hero"])
        for url in heroes:
            hero = os.path.join(SITE, url.lstrip("/").split("?")[0])
            self.assertTrue(os.path.isfile(hero), hero)
            self.assertLess(os.path.getsize(hero), 750 * 1024, hero)
        # the home poster's PNG master is archived, never deployed
        self.assertTrue(os.path.isfile(
            os.path.join(ROOT, "artwork-source", "gridironlocker-hero-image1.png")))


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
        nav = between(self.html, '<nav class="links"', "</nav>")
        for href in ["./collections/"] + [f'./{COLLECTIONS[k]["slug"]}/' for k in ORDER] \
                + ["./drops/", "./guides/"]:
            self.assertIn(f'href="{href}"', nav, href)
        # search survives in the header (desktop input + mobile panel)
        self.assertIn('class="navsearch"', self.html)
        self.assertIn('class="gsearch"', self.html)
        self.assertIn('id="ms"', self.html)

    # ------------------------------------------------------------------ hero
    def test_hero_is_split_editorial_plus_cinematic_art(self):
        hero = between(self.html, '<section class="hero editorial"', "</section>")
        self.assertIn("Football. Fans. Culture.", hero)
        self.assertIn('<h1 class="hero-title">', hero)
        self.assertEqual(self.html.count("<h1"), 1)          # exactly one H1
        self.assertIn("Keep it.", hero)
        self.assertIn("Original fan-made apparel for the teams we love.", hero)
        self.assertIn("Four cities. Four fanbases. One locker.", hero)
        self.assertIn("Shop By Team", hero)
        self.assertIn("Trending Now", hero)
        self.assertIn("./collections/", hero)
        self.assertIn("./drops/", hero)
        self.assertRegex(hero, r"\d+ fan designs")
        self.assertIn("S&ndash;3XL", hero)
        self.assertIn("Worldwide shipping", hero)
        # the LCP image is eager, prioritised and responsive - never lazy
        art = re.search(r'<img class="hero-art"[^>]*>', hero).group(0)
        self.assertIn('fetchpriority="high"', art)
        self.assertNotIn('loading="lazy"', art)
        self.assertIn("srcset=", art)
        self.assertIn('width="1400"', art)
        self.assertIn('alt="', art)
        for name in ("hero-locker.jpg", "hero-locker-sm.jpg"):
            f = os.path.join(SITE, "img", name)
            self.assertTrue(os.path.isfile(f), name)
            self.assertLess(os.path.getsize(f), 300 * 1024, name)
        # the hero headline is visible text (crawlable), not sr-only
        self.assertIn("position:absolute", css_block(self.css, ".sr-only"))

    def test_hero_stays_short_enough_to_reveal_the_shop(self):
        grid = css_block(self.css, ".hero-grid")
        self.assertIn("min-height:min(78vh,660px)", grid)
        mob = media_rules(self.css, 920)
        self.assertIn(".hero-grid{grid-template-columns:1fr", mob)
        self.assertIn(".hero-stage{order:-1}", mob)

    # --------------------------------------------------------- funnel order
    def test_product_first_funnel_order(self):
        markers = [
            '<section class="hero editorial"',   # brand
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
        self.assertIn("hero-home.jpg?v=4", self.html)          # OG image unchanged
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
    "cleveland-browns": ("/img/hero-cleveland.jpg?v=3", "/img/browns-logo1.webp?v=1"),
    "dallas-cowboys": ("/img/hero-dallas.jpg?v=3", "/img/dallas-logo1.webp?v=1"),
    "green-bay-packers": ("/img/hero-greenbay.jpg?v=3", "/img/green-bay-logo1.webp?v=1"),
    "michigan": ("/img/hero-michigan.jpg?v=3", "/img/michigan-logo1.webp?v=1"),
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
        for slug in NEW_ZERO_ONE:
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertIn('"image":[', html, slug)
            self.assertIn("assets.viralstyle.com", html.split('"image":[', 1)[1][:400], slug)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
