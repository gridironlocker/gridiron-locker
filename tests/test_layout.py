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
  * The kickoff countdown bar is gone from every page, the CSS and app.js.
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
  * Bella's /michigan/bella/: seven Silent Touch listings, six accessible
    apparel-category buttons that swap every design to that garment plus a
    second row of buttons for the five t-shirt listings - each swap drawn from
    the live store capture (data-apparel), with a design that did not list the
    style taken out of the grid (never greyed out), and the
    campus hero banner, the #efefed canvas and the VIP10 promo banner (10% off
    at checkout, with a copyable code).
  * Preserved: team accents, hero images, product count, checkout links, SEO
    metadata, dynamic catalogue counts, no missing local references.
"""
import json
import os
import re
import sys
import datetime
import unittest
from html import unescape, escape as escape_html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SRC = os.path.join(ROOT, "src")
IMG = os.path.join(SITE, "img")
sys.path.insert(0, SRC)

from collections_data import COLLECTIONS, ORDER  # noqa: E402
import landing  # noqa: E402

CTA, CTA_HOVER = "#49a59c", "#3a847d"

# Sitemap dates are source metadata and are intentionally not treated as a
# build heartbeat.  The live health check validates their format/non-future
# property; this layout suite validates the rendered site and schema invariants.


def iso_date(value, ctx=""):
    """Parse an ISO ``YYYY-MM-DD`` string into a date, with a useful failure.

    Schema.org date fields are only machine-readable if they are real ISO
    dates, so every date assertion in this suite goes through here rather than
    comparing strings.
    """
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise AssertionError(f"{ctx}: {value!r} is not an ISO YYYY-MM-DD date") from None


def utc_today():
    """Today in UTC - the clock the build and the refresh cron both run on.

    ``src/build.py`` stamps dynamic schema dates from ``build.utc_today()``.
    Sitemap ``lastmod`` is deliberately different: it comes from source
    metadata and is tested as a stable page date in ``tests/test_sitemap.py``.
    Comparing dynamic dates against the *local* date here would make this suite
    disagree with the artefact for part of every day on any machine that is not
    on UTC (the operator is on Africa/Casablanca, UTC+1).
    """
    return datetime.datetime.now(datetime.timezone.utc).date()


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_json(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def page(rel):
    return read(os.path.join(SITE, rel))


def json_ld_nodes(html):
    return [json.loads(m.group(1))
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


# Mayzing storefront catalogues: slug -> product record. Cleveland/Browns moved
# on 2026-09-12 and Michigan followed, so neither collection appears in the
# Viralstyle crawl (data/products_live.json) any more. Tests that want "the
# catalogue" must not read that one file - the master is the crawl plus these
# two Mayzing files, which is exactly what src/build.py merges in MODEL.
# data/delisted.json retires a slug from EVERY source: build_model() skips a
# delisted slug whether it arrives via the Viralstyle crawl or a Mayzing
# capture (the capture stays truthful to the storefront; the page still has
# to go), so the live page set is each Mayzing file minus the delisted slugs.
DELISTED = set(load_json("data/delisted.json").get("slugs", {}))
MAYZING = {p["slug"]: p for p in load_json("data/mayzing_products.json")["products"]
           if p["slug"] not in DELISTED}

# Prices are changed in Mayzing admin, so src/scrape_mayzing_prices.py captures
# them and src/build.py prefers the capture over the curated record. Tests must
# resolve the same way or they pin yesterday's price.
try:
    _PRICES = load_json("data/mayzing_prices.json")["collections"]
except Exception:
    _PRICES = {}


def live_price(ckey, product):
    """The price the built site should show for one Mayzing product."""
    rec = (_PRICES.get(ckey) or {}).get(product["slug"]) or {}
    try:
        value = float(str(rec.get("price_usd") or ""))
    except ValueError:
        value = 0.0
    return "%.2f" % (value if 0 < value < 1000 else float(product["price_usd"]))
MICHIGAN = {p["slug"]: p for p in load_json("data/mayzing_michigan.json")["products"]
            if p["slug"] not in DELISTED}
# Retired designs a Mayzing capture still lists (e.g. milf, retired 2026-09-19
# for brand safety). They must build as noindex redirect stubs, never pages.
MAYZING_RETIRED = {p["slug"]: "cleveland-browns"
                   for p in load_json("data/mayzing_products.json")["products"]
                   if p["slug"] in DELISTED}
MAYZING_RETIRED.update({p["slug"]: "michigan"
                        for p in load_json("data/mayzing_michigan.json")["products"]
                        if p["slug"] in DELISTED})
# slug -> (record, collection key) for every design on a Mayzing storefront.
MAYZING_ALL = dict({s: (p, "cleveland-browns") for s, p in MAYZING.items()},
                   **{s: (p, "michigan") for s, p in MICHIGAN.items()})


def mayzing_partner(slug):
    """Fulfillment partner for a slug: Mayzing for migrated collections,
    Viralstyle for Dallas and Green Bay."""
    return "Mayzing" if slug in MAYZING_ALL else "Viralstyle"


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


class BuildFreshness(unittest.TestCase):
    """Is the committed site the one the refresh pipeline last produced?

    These tests are about *staleness*, which the rest of this suite is not: the
    layout and schema assertions describe invariants that must hold for a build
    of any age, while a build that stopped being refreshed is a dead pipeline.
    Keeping the two apart is the point - before this class existed, the only
    staleness signal in the suite was ``assertEqual(validFrom, build.TODAY)``
    inside a merchant-schema test, so a missed refresh reported itself as
    "Product schema is wrong on 84 pages", which sends you to the wrong file.

    The dates come from ``site/sitemap.xml`` and are expected to vary by page.
    A separate sitemap regression test checks source-date selection and build
    determinism; this class only checks that committed dates are valid and not
    accidentally in the future.
    """

    @classmethod
    def setUpClass(cls):
        cls.sitemap = page("sitemap.xml")
        cls.stamps = sorted(set(re.findall(r"<lastmod>([^<]+)</lastmod>", cls.sitemap)))

    def test_sitemap_has_page_specific_source_dates(self):
        self.assertTrue(self.stamps, "sitemap.xml has no <lastmod> entries")
        self.assertGreater(
            len(self.stamps), 1,
            "sitemap.xml unexpectedly uses one build date for every URL; "
            "lastmod must represent page/source changes")

    def test_sitemap_dates_are_not_from_the_future(self):
        for stamp in self.stamps:
            self.assertLessEqual(
                iso_date(stamp, "sitemap lastmod"), utc_today(),
                f"the committed sitemap contains future date {stamp}; check "
                "the source metadata and UTC clock")


class StructuredData(unittest.TestCase):
    def test_fan_trend_dataset_declares_license(self):
        """Google Dataset rich results warn when Dataset.license is omitted."""
        html = page("fan-trend-index/index.html")
        dataset = next((n for n in json_ld_nodes(html) if n.get("@type") == "Dataset"), None)
        self.assertIsNotNone(dataset, "/fan-trend-index/ must publish Dataset schema")
        domain = load_json("src/config.json")["domain"].rstrip("/")
        self.assertEqual(dataset.get("license"), f"{domain}/fan-trend-index/#license")
        self.assertIn('id="license"', html, "Dataset.license must point at visible license terms")


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
            if k == "cleveland-browns":
                # Mayzing rebuild: the collection is sourced from
                # data/mayzing_products.json, not the Viralstyle crawl.
                expected = len(MAYZING)
            elif k == "michigan":
                # Michigan migrated too: data/mayzing_michigan.json is its
                # catalogue, so the Viralstyle crawl no longer lists it.
                expected = len(MICHIGAN)
            else:
                expected = self._crawl_count(cols, live, delisted, k)
            card = re.search(r'<a class="teamcircle[^"]*"[^>]*href="[^"]*%s/"[^>]*>.*?</a>'
                             % COLLECTIONS[k]["slug"], self.html, re.S).group(0)
            self.assertIn(f"{expected} designs", card, k)

    @staticmethod
    def _crawl_count(cols, live, delisted, k):
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
        return expected


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
            self.assertIn('id="sort"', html, k)
            self.assertIn('id="nores"', html, k)
            self.assertIn("No designs match that search.", html, k)

    def test_apparel_filter_buttons_never_hide_listed_garments(self):
        """The team-page apparel buttons must ship every garment the collection
        actually lists, with a real mockup, and only flag a category when no
        design in the collection lists it. Regression guard: an earlier cut
        emitted T-shirts only and every other tile said "not listed yet" while
        the campaign records (and site/img/p) carried hoodie, crewneck and
        tank-top listings."""
        import build  # noqa: E402
        for k, html in self.pages.items():
            self.assertIn('<section id="apparel" class="gcategory-row"', html, k)
            self.assertLess(html.index('<section id="apparel"'),
                            html.index('<section id="grid"'), k)
            self.assertIn('<div class="grid" id="pg">', html, k)
            attr = re.search(r'<section id="grid" data-apparel="([^"]*)"', html)
            self.assertIsNotNone(attr, k)
            payload = json.loads(unescape(attr.group(1)))
            items = build.MODEL[k]
            self.assertTrue(payload, k)
            # every design that lists a garment ships that garment
            shipped = {c for c, _ in build.APPAREL_CATEGORIES}
            for it in items:
                own = build.apparel_category(it["garment"])
                if own in shipped and it["slug"] in payload:
                    self.assertIn(own, payload[it["slug"]],
                                  f"{k}/{it['slug']} lost its {own} listing")
            # no tile is shipped for a category that is not in the table, and
            # none of those categories may linger in the payload
            for groups in payload.values():
                self.assertFalse(set(groups) - shipped, k)
            # the flag is only allowed on a category nothing in the
            # collection lists, and listed categories never carry it
            listed = {cat for groups in payload.values() for cat in groups}
            for m in re.finditer(r'<button class="gcategory-tile" type="button" '
                                 r'data-gcat="([^"]+)"[^>]*>(.*?)</button>', html, re.S):
                cat, inner = m.group(1), m.group(2)
                flagged = 'gcategory-flag' in inner
                self.assertEqual(flagged, cat not in listed,
                                 f"{k}: {cat} flag disagrees with its listings")
            # any mockup a swap points at must exist in site/img/p
            for groups in payload.values():
                for rows in groups.values():
                    for row in rows:
                        img = row["image"]
                        if img and not img.startswith("http"):
                            rel = img[3:] if img.startswith("../") else img.lstrip("/")
                            self.assertTrue(
                                os.path.isfile(os.path.join(SITE, rel)),
                                f"{k}: missing mockup {img}")

    def test_apparel_filter_removes_cards_instead_of_greying_them(self):
        """A category shows only the designs sold in it.

        The team-page buttons must take a design that has no listing for the
        chosen garment out of the grid. Greying it and leaving it in place was
        the earlier behaviour and reads as dead stock on the shelf."""
        js = page("assets/app.js")
        start = js.index("// ---------- team collection apparel buttons")
        end = js.index("// ----------", start + 10)
        team = js[start:end]
        self.assertIn("card.hidden=true", team)
        self.assertNotIn("is-muted", team, "team cards must not be greyed")
        # the shelf count and the empty state follow the grid
        self.assertIn("function refreshCount()", team)
        self.assertIn("noresEl", team)
        # and no rule greys a team card any more
        self.assertNotIn(".card.is-muted", self.css)

    def test_hover_back_view_never_shows_another_garment(self):
        """The hover image is a back view of the design on ONE garment.

        The store captures a back render per design, never per garment, so a
        card swapped to a hoodie/tank/crop has no matching back. It must hide
        the hover image instead of flashing the t-shirt back the design was
        first shot on, and put it back when the tile is cleared."""
        js = page("assets/app.js")
        start = js.index("// ---------- team collection apparel buttons")
        end = js.index("// ----------", start + 10)
        team = js[start:end]
        # the hover image swaps to entry.back when provided and hides otherwise
        self.assertIn("if(entry&&entry.back){", team)
        self.assertIn("card._back.src=entry.back;", team)
        # the back view is captured and its garment class compared
        self.assertIn("querySelector('.ph img.alt')", team)
        self.assertIn("card._ownCat=categoryOf(card.getAttribute('data-type')", team)
        self.assertIn("var shown=entry?categoryOf(entry.garment):'';", team)
        self.assertIn("card._back.hidden=true", team)
        # clearing the tile brings the original hover image back
        self.assertIn("card._back.hidden=false", team)
        # and the hidden back stays hidden on hover
        self.assertIn(".card .ph img.alt[hidden]{display:none}", self.css)
        self.assertIn(".card:hover .ph img.alt{opacity:1}", self.css)
        # every team page ships the two slots for the script to work on
        for k in COLLECTIONS:
            html = self.pages[k]
            self.assertIn('<img class="alt"', html, k)

    def test_apparel_payload_is_generated_not_hand_edited(self):
        """site/ is disposable: the buttons and the payload must come from
        src/build.py, otherwise the twice-daily rebuild silently reverts them."""
        with open(os.path.join(ROOT, "src", "build.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("def apparel_filter_html(", src)
        self.assertIn("data-apparel=", src)
        self.assertIn("team collection apparel buttons", src)

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

    def test_hero_carries_the_team_positioning_line(self):
        """Each collection hero leads with its own fan-positioning line
        ("Built for the Dawg Pound.", "Saturdays in Ann Arbor start here." ...)
        so the four team pages stop feeling like four copies of one
        template. The line is a short, factual, non-infringing positioning
        sentence from collections_data, never a claim of affiliation."""
        for k, html in self.pages.items():
            c = COLLECTIONS[k]
            pos = c["position"]
            self.assertIn(pos, html, k)
            # it lives in the hero copy block, above the H1
            hero = between(html, '<section class="cbanner compact"', "</section>")
            self.assertIn(f'<p class="posline">{pos}</p>', hero, k)
            self.assertLess(hero.index("posline"), hero.index("<h1>"), k)
            # and it stays short: one line of positioning, not a paragraph
            self.assertLessEqual(len(pos), 60, k)

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


class NoCountdownAnywhere(unittest.TestCase):
    """The kickoff countdown bar was retired site-wide.

    It used to live on the homepage season band and the Week 1 guide; the
    purchase countdowns were removed long before that. Nothing may bring it
    back: no .cdbar markup, no data-deadline, no ticking script, no styles.
    """

    def test_homepage_and_week1_guide_have_no_countdown(self):
        for rel in ("index.html", "guides/2026-week-1-shirts/index.html"):
            html = page(rel)
            self.assertNotIn('class="cdbar"', html, rel)
            self.assertNotIn("data-deadline", html, rel)
            self.assertNotIn('id="cd-d"', html, rel)

    def test_countdown_script_and_styles_removed(self):
        self.assertNotIn("kickoff countdown", page("assets/app.js"))
        css = page("assets/style.css")
        self.assertNotIn(".cdbar", css)
        self.assertNotIn(".cd{", css)
        self.assertNotIn(".cd b", css)


class ProductPages(unittest.TestCase):
    """Conversion + merchant schema on every built product page."""

    @classmethod
    def setUpClass(cls):
        shop = os.path.join(SITE, "shop")
        cls.pages = {d: h for d, h in
                     ((d, read(os.path.join(shop, d, "index.html")))
                      for d in sorted(os.listdir(shop))
                      if os.path.isfile(os.path.join(shop, d, "index.html")))
                     # Retired URLs carry a noindex redirect stub, not a
                     # product page: no Product schema, no CTA, no gallery.
                     # Those are asserted in RedirectStubs.
                     if "data-gl-redirect" not in h}
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
            hrefs = re.findall(r'<a class="btn[^"]*shopnow" href="([^"]+)"', html)
            self.assertTrue(hrefs, slug)
            if slug in MAYZING_ALL:
                # Cleveland and Michigan: every CTA hands off to the product's
                # own Mayzing checkout URL on gridironlocker.shop.
                for href in hrefs:
                    self.assertEqual(href, MAYZING_ALL[slug][0]["checkout_url"], slug)
                continue
            # every CTA points at this product's own Viralstyle campaign
            for href in hrefs:
                self.assertEqual(href, live[slug]["url"], slug)
            # and no other outbound purchase link sneaks onto the page
            for href in re.findall(r'href="(https://viralstyle\.com[^"]*)"', html):
                self.assertEqual(href, live[slug]["url"], slug)

    def test_cta_explains_the_handoff(self):
        for slug, html in self.pages.items():
            partner = mayzing_partner(slug)
            self.assertIn(f"on the {partner} product page", html, slug)
            # the 30-day replacement window is Viralstyle's published policy;
            # Mayzing publishes none, so it must not appear on those pages
            if partner == "Viralstyle":
                self.assertIn("30-day misprint replacement", html, slug)
            else:
                self.assertNotIn("30-day misprint replacement", html, slug)
            # the buybox is a summary, not a form: the hand-off is stated once
            # beside the mid-page CTA (plus the band line and the FAQ), so the
            # two duplicate notes that used to sit under the hero button stay off.
            self.assertEqual(html.count('class="ctanote'), 1, slug)
            self.assertNotIn("Checkout is completed there", html, slug)
            self.assertNotIn("Final garment style, colour, size and quantity", html, slug)

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

    def test_value_line_under_h1(self):
        """Every product page sells the moment, not just the graphic: a short
        fan-focused value line sits between the H1 and the description. It is
        one glance-sized line (not a paragraph, not a second heading) and it
        varies across the catalogue like the story does."""
        lines = {}
        for slug, html in self.pages.items():
            m = re.search(r"<h1>.*?</h1>\s*<p class=\"value\">(.*?)</p>\s*<p class=\"herodeck\">",
                          html, re.S)
            self.assertIsNotNone(m, slug)
            line = m.group(1).strip()
            self.assertGreater(len(line), 8, slug)
            self.assertLessEqual(len(line), 140, slug)
            self.assertNotIn("<", line, slug)                 # no markup in the line
            lines.setdefault(re.sub(r"\s+", " ", line), []).append(slug)
        cap = max(4, len(self.pages) // 8)
        self.assertLess(max(len(v) for v in lines.values()), cap)

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
            partner = mayzing_partner(slug)
            self.assertIn(f"{partner} product page", section, slug)

    def test_colour_claims_match_the_campaign_data(self):
        import build  # noqa: E402
        by_slug = {it["slug"]: it for it in build.ALL}
        for slug, html in self.pages.items():
            it = by_slug[slug]
            if it["colours"] > 1:
                self.assertIn(f"{it['colours']} colour variations", html, slug)
                self.assertIn(f"{it['colours']} colourways", html, slug)
            elif slug in MAYZING_ALL:
                # A Mayzing product ships in one verified colourway.
                self.assertIn(f"one colourway: {MAYZING_ALL[slug][0]['colour_name']}",
                              html, slug)
                self.assertNotIn("colour variations", html, slug)
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
        """Merchant terms must match the partner that actually prints it.

        Viralstyle publishes a US rate, a delivery window and a 30-day
        replacement window, so its offers carry them. Mayzing publishes none
        of the three (its page says only that delivery times vary by
        location), so a Mayzing offer must carry neither - quoting
        Viralstyle's $4.95 on a Mayzing product is a false merchant claim.
        """
        import build  # noqa: E402
        seen = {"Viralstyle": 0, "Mayzing": 0}
        for slug, html in self.pages.items():
            d = self.product_ld(html)
            self.assertIsNotNone(d, slug)
            self.assertEqual(d["audience"]["@type"], "PeopleAudience", slug)
            self.assertIn(d["audience"]["suggestedGender"], ("unisex", "female", "male"), slug)
            o = d["offers"]
            # validFrom is the date the build stamped, so it must be a real ISO
            # date that is not in the future and sits inside the offer window.
            # It is deliberately NOT compared against today's date: the site
            # under test is a committed artefact that may legitimately have been
            # built yesterday, and equating the two turned a stale build into a
            # bogus "merchant schema is wrong" failure. Build staleness is
            # asserted on its own terms in BuildFreshness, where the failure
            # message names the real cause.
            valid_from = iso_date(o["validFrom"], f"{slug}: offers.validFrom")
            self.assertLessEqual(valid_from, utc_today(),
                                 f"{slug}: offers.validFrom is in the future")
            self.assertLess(o["validFrom"], o["priceValidUntil"], slug)
            self.assertLess(valid_from,
                            iso_date(o["priceValidUntil"], f"{slug}: offers.priceValidUntil"),
                            f"{slug}: the offer window must not be empty or inverted")
            partner = o["seller"]["name"]
            self.assertIn(partner, seen, slug)
            seen[partner] += 1
            terms = build.partner_offer_terms(partner)
            self.assertEqual({k: o.get(k) for k in terms}, terms, slug)
            if partner == "Viralstyle":
                self.assertEqual(o["hasMerchantReturnPolicy"], build.VIRALSTYLE_RETURN, slug)
                self.assertEqual(o["shippingDetails"], build.VIRALSTYLE_SHIP, slug)
                self.assertEqual(o["shippingDetails"]["shippingRate"]["value"], "4.95", slug)
                self.assertEqual(o["hasMerchantReturnPolicy"]["merchantReturnDays"], 30, slug)
                dt = o["shippingDetails"]["deliveryTime"]
                self.assertEqual(dt["@type"], "ShippingDeliveryTime", slug)
                self.assertIn("handlingTime", dt, slug)
                self.assertIn("transitTime", dt, slug)
            else:
                # Mayzing publishes a broad, non-price shipping window and an
                # explicit no-returns category; it must not inherit Viralstyle's
                # $4.95 rate or 30-day replacement terms.
                self.assertEqual(o["shippingDetails"], build.MAYZING_SHIP, slug)
                self.assertEqual(o["hasMerchantReturnPolicy"], build.MAYZING_RETURN, slug)
                self.assertNotIn("4.95", json.dumps(o), slug)
        # both partners must actually be represented, or the branch above
        # would pass while asserting nothing
        self.assertGreater(seen["Viralstyle"], 0, seen)
        self.assertGreater(seen["Mayzing"], 0, seen)

    def test_merchant_constants_defined_once(self):
        src = read(os.path.join(SRC, "build.py"))
        for name in ("VIRALSTYLE_SHIP", "VIRALSTYLE_RETURN", "VIRALSTYLE_DELIVERY_TIME"):
            self.assertEqual(len(re.findall(r"^%s = " % name, src, re.M)), 1, name)
        self.assertNotIn('"shippingDetails": {"@type": "OfferShippingDetails"', src)

    def test_shipping_copy_is_partner_scoped(self):
        """A Mayzing page must not quote Viralstyle's rate or window, and a
        Viralstyle page must not claim Mayzing's checkout-time wording."""
        import build  # noqa: E402
        rate = "$" + build.VIRALSTYLE_SHIP["shippingRate"]["value"]
        window = build.VIRALSTYLE_DELIVERY_TIME
        v = m = 0
        for slug, html in self.pages.items():
            partner = self.product_ld(html)["offers"]["seller"]["name"]
            if partner == "Viralstyle":
                v += 1
                self.assertIn(rate, html, slug)
                self.assertIn(window, html, slug)
            else:
                m += 1
                self.assertNotIn(rate, html, slug)
                self.assertNotIn(window, html, slug)
                # The page must name the partner that actually ships it and
                # point the shopper at checkout instead of quoting a figure
                # Mayzing does not publish.
                self.assertIn(f"printed and shipped by {partner}", html.replace("\n", " "), slug)
                self.assertIn("shown at checkout", html.replace("\n", " "), slug)
        # the neutral branch must really omit both Viralstyle facts
        neutral = landing.shipping_copy(build.VIRALSTYLE_DELIVERY_TIME,
                                        build.VIRALSTYLE_SHIP["shippingRate"]["value"],
                                        col={"key": "michigan"})
        self.assertNotIn(rate, neutral)
        self.assertNotIn(build.VIRALSTYLE_DELIVERY_TIME, neutral)
        self.assertIn("Mayzing", neutral)
        viral = landing.shipping_copy(build.VIRALSTYLE_DELIVERY_TIME,
                                      build.VIRALSTYLE_SHIP["shippingRate"]["value"],
                                      col={"key": "dallas-cowboys"})
        self.assertIn(rate, viral)
        self.assertIn(build.VIRALSTYLE_DELIVERY_TIME, viral)
        self.assertGreater(v, 0)
        self.assertGreater(m, 0)

    def test_no_global_printed_in_usa_claim(self):
        """The sitewide announcement bar appears on every page, so it may not
        state a production location only one partner can support."""
        import build  # noqa: E402
        for slug, html in self.pages.items():
            promo = re.search(r'<div class="promo">(.*?)</div>', html, re.S)
            self.assertIsNotNone(promo, slug)
            self.assertNotIn("in the USA", promo.group(1), slug)


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
        self.assertIn('<h1 class="hero-title">', hero)
        self.assertEqual(self.html.count("<h1"), 1)          # exactly one H1
        # The 5-second test: the crawlable copy answers WHAT (fan-made
        # football gear), WHO (all four teams, named - the poster shows
        # them, the copy says them), WHY (original artwork + custom) and
        # WHERE (CTAs go to products and to the custom form). The hero is a
        # value proposition, not two links to editorial pages.
        self.assertIn("Fan-Made Football", hero)
        self.assertIn("Your Team. Your Colors.", hero)
        self.assertIn("Your Game Day.", hero)
        self.assertIn("Original fan-made football gear for Browns, Packers, Michigan", hero)
        self.assertIn("Cowboys fans", hero)
        self.assertIn("We design it.", hero)
        self.assertIn("Shop The Locker", hero)
        self.assertIn("Custom Design", hero)
        self.assertIn("./#shop-the-locker", hero)
        self.assertIn("./#custom-design", hero)
        self.assertRegex(hero, r"\d+ fan designs")
        # Size range is derived from the catalogue, not typed: the Mayzing
        # Gildan blanks sell S-5XL, so a hard-coded S-3XL understated it.
        import build  # noqa: E402
        self.assertIn(build.SIZE_RANGE_EN, hero)
        self.assertNotIn("3XL</span>", hero)
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
        banner_css = between(self.css, "COLLECTION / PAGE BANNER", "TRUST STRIP")
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
            '<section class="customsec"',        # custom design (differentiator)
            'class="trust-label"',               # why Gridiron Locker
            '<section class="wksec"',            # 2026 season (editorial)
            '<section class="teamsec"',          # deeper team browsing
            '<section class="guidesec"',         # buying guides
            '<section class="ftisec"',           # fan trend index
            '<section class="brandsec"',         # newsletter
            '<section class="finalcta"',         # final shop CTA
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
        """Card counts must equal the built catalogue exactly - one source of
        truth, so a page can never report a total the build disagrees with."""
        import build  # noqa: E402
        sec = between(self.html, '<section class="teamdeck-sec" id="shop-by-team">', "</section>")
        counts = [int(n) for n in re.findall(r"(\d+) designs", sec)]
        self.assertEqual(len(counts), len(ORDER))
        for k, n in zip(ORDER, counts):
            self.assertEqual(n, len(build.MODEL[k]), k)
        self.assertEqual(sum(counts), build.N_DESIGNS)
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
        # The per-team blurb is the team's positioning line - a complete
        # sentence. The old banner[:150] slice cut two of the four teams
        # mid-word ("...printed on tees, hoodi"), which this guards against.
        allsec = "".join(secs)
        for k in ORDER:
            self.assertIn(COLLECTIONS[k]["position"], allsec, k)
        for bad in ("hoodi\n", "crewn\n"):
            self.assertNotIn(bad, allsec)

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
        self.assertIn("Start Your Custom Design", sec)
        self.assertIn('id="customForm"', sec)
        self.assertIn('data-formsubmit="1"', sec)
        for field in ('name="name"', 'name="email"', 'name="team"', 'name="garment"',
                      'name="idea"', 'name="details"', 'name="_subject"', 'name="_honey"'):
            self.assertIn(field, sec, field)
        # "Your idea" is the point of the form: it is a textarea (the most
        # important field), and the three-step flow makes the service
        # understandable in one glance - no multi-step application implied.
        self.assertIn('textarea name="idea"', sec)
        # Custom requests are currently available for Michigan only. Keep
        # the blank placeholder and required selection on the homepage.
        team = re.search(r'<select name="team"(?P<attrs>[^>]*)>'
                         r'(?P<options>.*?)</select>', sec, re.S)
        self.assertIsNotNone(team)
        self.assertIn("required", team.group("attrs"))
        self.assertIn('<option value="">Choose</option>', team.group("options"))
        options = re.findall(r'<option(?:\s[^>]*)?>(.*?)</option>',
                             team.group("options"), re.S)
        self.assertEqual(options, ["Choose", "Michigan"])
        for step in ("<b>01</b><span>Your idea</span>",
                     "<b>02</b><span>Our design</span>",
                     "<b>03</b><span>Your shirt</span>"):
            self.assertIn(step, sec, step)
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
        """The leaderboard is never truncated - but it only lists people the
        catalogue is allowed to promote (data/people.json status == current)."""
        import build
        fti = page("fan-trend-index/index.html")
        rows = build.fti_rows(None)
        self.assertEqual(fti.count('class="fti-card reveal"'), len(rows))
        self.assertGreater(len(rows), 4)
        people = load_json("data/people.json")
        retired = [p["name"] for p in people.get("people", [])
                   if p.get("status") != "current"]
        self.assertTrue(retired, "expected people.json to carry non-current names")
        for name in retired:
            self.assertNotRegex(
                fti, r"\b%s\b\s+\d{1,3}\b" % re.escape(name),
                f"retired/non-current {name!r} still has a scored FTI row")

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
        # Pinterest Business domain claim (Settings → Claim → website).
        self.assertIn(
            '<meta name="p:domain_verify" content="b4b50fd5812ff9c5767ca434904b504b">',
            self.html)
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
        # rendered designs = catalogue entries that still have artwork;
        # assert a floor so a silent data regression is caught loudly
        # (79 designs after the two deliberate catalogue culls: PR #90 held
        # 60 Cleveland designs back, the Mayzing rebuild re-listed 13)
        self.assertGreaterEqual(len(re.findall(r'<article class="card', self.html)), 60)

    def test_filter_dimensions_present(self):
        for marker in ('id="q"', 'id="sort"', 'id="price"',
                       '<option value="player">', '<option value="funny">',
                       '<option value="retro">', '<option value="family">',
                       'data-team="cleveland-browns"', 'data-type="T-Shirt"'):
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
        built = [d for d in os.listdir(shop) if os.path.isfile(os.path.join(shop, d, "index.html"))
                 and "data-gl-redirect" not in read(os.path.join(shop, d, "index.html"))]
        self.assertGreaterEqual(len(built), 60)
        for slug in built:
            html = read(os.path.join(shop, slug, "index.html"))
            if slug in MAYZING_ALL:
                # Cleveland + Michigan: Mayzing checkout URL on gridironlocker.shop
                self.assertIn(MAYZING_ALL[slug][0]["checkout_url"], html, slug)
            else:
                self.assertIn(live[slug]["url"], html, slug)   # Viralstyle checkout link intact

    def test_no_missing_local_references(self):
        from urllib.parse import unquote

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
                    # Decode the way a browser does: a URL is percent-encoded
                    # (Bella's campus hero banner is a .png with spaces in its
                    # filename), the file on disk is not.
                    val = unquote(val.split("#")[0].split("?")[0])
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
            # A noindex redirect stub for a retired URL carries NO canonical
            # (see test_redirect_stub_has_no_canonical): it forwards with a
            # meta refresh instead. `found` is therefore None for stubs and the
            # `if not found` guard above already skipped them - so anything that
            # reaches here is an indexable page that must canonicalise to
            # itself.
            self.assertNotIn("data-gl-redirect", html,
                             f"{rel} is a redirect stub and must not carry a canonical")
            self.assertEqual(found.group(1), own, rel)
            self.assertIn(found.group(1), locs, f"{rel} canonical is missing from sitemap.xml")
            checked += 1
        self.assertGreaterEqual(checked, 100)

    def test_redirect_stub_has_no_canonical(self):
        """A retired-URL redirect stub sends exactly one signal: a redirect.

        Google's guidance is never to combine noindex with rel=canonical, and
        never to canonicalise a page to a URL it is not a duplicate of. The old
        stub did both (noindex + canonical to the collection it forwards to),
        which parked every retired URL under Search Console's "Alternate page
        with proper canonical tag" and made that fix impossible to validate.
        The stub now carries NO canonical - only noindex, an instant meta
        refresh and a visible fallback link - so Google reads it as a plain
        redirect. This test also proves no stub self-canonicalises (which would
        contradict the redirect just as loudly).
        """
        shop = os.path.join(SITE, "shop")
        stubs = 0
        for d in sorted(os.listdir(shop)):
            index = os.path.join(shop, d, "index.html")
            if not os.path.isfile(index):
                continue
            html = read(index)
            if "data-gl-redirect" not in html:
                continue
            stubs += 1
            self.assertNotIn('<link rel="canonical"', html,
                             f"stub {d} must not carry any canonical tag")
            self.assertIn('name="robots" content="noindex', html,
                          f"stub {d} must stay noindex")
            self.assertRegex(html, r'<meta http-equiv="refresh" content="0;url=',
                             f"stub {d} must redirect via meta refresh")
        self.assertGreaterEqual(stubs, 50, "expected the retired-URL redirect stubs")


# Locked-in hero / logo URLs from current main - must never drift.
# Heroes are still the Mayzing-sourced JPEGs. The second element used to pin
# `/img/<team>-logo1.webp` - rasterised official team marks - which the site no
# longer publishes; it is now the generated fan-made lockup for that collection.
HERO_LOGO_LOCK = {
    "cleveland-browns": ("/img/hero-cleveland.jpg?v=4", "/img/lockups/browns.svg"),
    "dallas-cowboys": ("/img/hero-dallas.jpg?v=4", "/img/lockups/dallas.svg"),
    "green-bay-packers": ("/img/hero-greenbay.jpg?v=4", "/img/lockups/green-bay.svg"),
    "michigan": ("/img/hero-michigan.jpg?v=4", "/img/lockups/michigan.svg"),
}


class MayzingBrownsRebuild(unittest.TestCase):
    """Regression coverage for the Cleveland/Browns Mayzing rebuild.

    The whole collection is sourced from data/mayzing_products.json - every
    product live on the Mayzing Browns storefront (gridironlocker.shop/p/browns).
    The invariants: a Viralstyle re-crawl can never resurrect a Cleveland page,
    no Cleveland page references Viralstyle or links off gridironlocker.shop,
    and designs held back (no Mayzing equivalent) stay off the storefront.
    """

    # The seven Viralstyle-era pages the rebuild deleted (PR #90 destinations).
    OLD_CLEVELAND_PAGES = [
        "make-them-know-your-name-denzel-1", "ohio-cleveland-fans",
        "playoffs-never-giveup", "lets-go-cleveland", "limited-edition-c2",
        "limited-edition-d-w-a-g", "limited-edition-go-b-r-o-w-n-s",
    ]

    @classmethod
    def setUpClass(cls):
        cls.cols = load_json("data/collections.json")

    def test_collection_mirrors_the_mayzing_file(self):
        """Cleveland's page set is the Mayzing file, full stop.

        data/collections.json deliberately still carries the old Viralstyle
        slugs (zero overlap with Mayzing) so the catalogue shape stays
        readable by other tools - build.py must not source Cleveland from it,
        or a re-crawl would resurrect Viralstyle pages.
        """
        import build  # noqa: E402
        built = [it["slug"] for it in build.MODEL["cleveland-browns"]]
        self.assertEqual(sorted(built), sorted(MAYZING),
                         "Cleveland pages must mirror mayzing_products.json")
        self.assertGreaterEqual(len(built), 13)
        stale = [p["slug"] for p in self.cols["cleveland-browns"]["products"]]
        self.assertEqual(set(stale) & set(MAYZING), set(),
                         "collections.json Cleveland entry is the retired Viralstyle list")
        for slug in stale:
            self.assertNotIn(slug, built, f"retired Viralstyle slug {slug} got a page")

    def test_product_pages_with_mayzing_checkout_and_no_viralstyle(self):
        built = {d for d in os.listdir(os.path.join(SITE, "shop"))
                 if os.path.isfile(os.path.join(SITE, "shop", d, "index.html"))}
        for slug in MAYZING:
            self.assertIn(slug, built, slug)
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertNotIn("viralstyle", html.lower(), slug)
            self.assertIn(MAYZING[slug]["checkout_url"], html, slug)
            hrefs = re.findall(r'<a class="btn[^"]*shopnow" href="([^"]+)"', html)
            self.assertGreaterEqual(len(hrefs), 3, slug)      # hero + band + sticky
            for href in hrefs:
                self.assertTrue(href.startswith("https://gridironlocker.shop/"),
                                f"{slug}: {href}")

    def test_collection_page_lists_exactly_the_mayzing_products(self):
        html = page(f"{COLLECTIONS['cleveland-browns']['slug']}/index.html")
        n = re.search(r'"numberOfItems":\s*(\d+)', html)
        self.assertEqual(int(n.group(1)), len(MAYZING))
        listed = set(re.findall(r'"url":"https://gridironlocker\.store/shop/([a-z0-9-]+)/"', html))
        self.assertEqual(listed, set(MAYZING))
        self.assertNotIn("viralstyle", html.lower())

    def test_held_and_retired_cleveland_designs_have_no_pages(self):
        """A held/retired Cleveland design must never get a sellable page back.

        Its URL does still resolve - a retired URL that 404s strands an
        indexed, externally linked page - but only as a noindex redirect stub
        that forwards to the Mayzing Browns collection. What must not exist is
        a product page: no Product schema, no SHOP NOW, and no Viralstyle
        hand-off. That is the original guard rail, asserted more precisely.
        """
        shop = os.path.join(SITE, "shop")
        built = {d for d in os.listdir(shop)
                 if os.path.isfile(os.path.join(shop, d, "index.html"))}
        for slug in list(load_json("data/fulfillment.json")["hold"]) + \
                list(self.OLD_CLEVELAND_PAGES):
            if slug not in built:
                continue
            html = read(os.path.join(shop, slug, "index.html"))
            why = f"retired design {slug}"
            self.assertIn("data-gl-redirect", html, f"{why} must be a redirect stub")
            self.assertIn('name="robots" content="noindex', html, f"{why} stub must be noindex")
            self.assertNotIn('"@type":"Product"', html.replace(" ", ""),
                             f"{why} must not publish Product schema")
            self.assertNotIn("viralstyle", html.lower(),
                             f"{why} must never hand a customer to Viralstyle")
            self.assertRegex(html, r'data-gl-redirect="/cleveland-browns-shirts/"',
                             f"{why} must forward to the Browns collection")

    def test_single_variant_story_on_every_mayzing_page(self):
        """A Mayzing product is ONE style, ONE colourway, one flat price - and
        the page must say so instead of the crawled-campaign hedging."""
        for slug, p in MAYZING.items():
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertIn(f"one colourway: {p['colour_name']}", html, slug)
            self.assertIn(f"{p['sizes'][0]} to {p['sizes'][-1]}", html, slug)
            self.assertIn(f"This design is ${live_price('cleveland-browns', p)} on Mayzing",
                          html, slug)

    def test_live_price_capture_reaches_every_page(self):
        """A price changed in Mayzing admin must reach the site without a
        hand edit, and the marketing contract must agree with it."""
        prices = load_json("data/mayzing_prices.json")
        self.assertEqual(prices.get("currency"), "USD")
        catalogue = {p["slug"]: p for p in load_json("data/catalogue-live.json")["products"]}
        checked = 0
        for ckey, products in (("cleveland-browns", MAYZING),
                               ("michigan", MICHIGAN)):
            captured = (prices.get("collections") or {}).get(ckey) or {}
            for slug, p in products.items():
                rec = captured.get(slug)
                if not rec:
                    continue                       # record price is the fallback
                want = "%.2f" % float(rec["price_usd"])
                html = read(os.path.join(SITE, "shop", slug, "index.html"))
                # The page states one flat price in prose, in the buy box and
                # in the Product schema; all three must agree.
                self.assertIn(f"This design is ${want} on Mayzing", html, slug)
                self.assertIn(f'"price":"{want}"', html, slug)
                self.assertIn(f"${want}", html, slug)
                if slug in catalogue:
                    self.assertAlmostEqual(float(catalogue[slug]["price_usd"]),
                                           float(want), places=2, msg=slug)
                checked += 1
        self.assertGreaterEqual(checked, 40,
                                "price capture must cover both team stores")

    def test_swapped_cards_show_the_garment_price(self):
        """The store prices each garment separately, so a card swapped to a
        hoodie must not keep showing the design's t-shirt price."""
        # every captured listing carries its own price...
        apparel = load_json("data/mayzing_apparel.json")["collections"]
        priced = [row for prods in apparel.values()
                  for groups in prods.values()
                  for rows in groups.values() for row in rows if row.get("price")]
        self.assertGreaterEqual(len(priced), 100, "category capture lost its prices")
        for row in priced:
            self.assertRegex(row["price"], r"^[0-9]+\.[0-9]{2}$")
        # ...and the team page payload carries it per garment
        html = read(os.path.join(SITE, COLLECTIONS["cleveland-browns"]["slug"],
                                 "index.html"))
        blob = re.search(r'data-apparel="([^"]+)"', html).group(1)
        payload = json.loads(unescape(blob))
        hoodies = [e for groups in payload.values() for e in groups.get("hoodies", [])]
        self.assertTrue(hoodies, "Browns hoodie listings missing from the payload")
        for entry in hoodies:
            self.assertIn("price", entry)
            self.assertRegex(entry["price"], r"^[0-9]+\.[0-9]{2}$")
        # the script swaps the price and puts the design's own price back
        js = page("assets/app.js")
        start = js.index("// ---------- team collection apparel buttons")
        team = js[start:js.index("// ----------", start + 10)]
        self.assertIn("card._priceEl=card.querySelector('.price')", team)
        self.assertIn("card._priceEl.textContent='$'+entry.price", team)
        self.assertIn("card._priceEl.textContent=card._priceTxt", team)

    def test_img_p_stays_webp_only(self):
        pdir = os.path.join(SITE, "img", "p")
        bad = [f for f in os.listdir(pdir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        self.assertEqual(bad, [], bad)

    def test_hero_and_logo_urls_unchanged(self):
        for k, (hero, logo) in HERO_LOGO_LOCK.items():
            self.assertEqual(COLLECTIONS[k]["hero"], hero, k)
            self.assertEqual(COLLECTIONS[k]["logo"], logo, k)
            self.assertTrue(os.path.exists(os.path.join(SITE, logo.lstrip("/"))), logo)
        for k in ORDER:
            html = page(f"{COLLECTIONS[k]['slug']}/index.html")
            self.assertIn(COLLECTIONS[k]["hero"].split("?")[0], html, k)

    def test_no_official_mark_files_anywhere(self):
        """No page may reference a rasterised official team mark."""
        for dirpath, _dirs, files in os.walk(SITE):
            for f in files:
                if re.search(r"logo[12]\.webp$", f):
                    self.fail(f"official-mark asset back in site/: {f}")
        for rel in ("collections/index.html", "index.html"):
            html = page(rel)
            self.assertNotRegex(html, r"logo[12]\.webp", rel)



# Michigan migrated to the Mayzing storefront on 2026-09-12, so the two
# Viralstyle "0-01" campaigns this class used to pin no longer exist in any
# catalogue. The regression it was written for still matters, so it now runs
# against the real Michigan catalogue in data/mayzing_michigan.json: every
# Michigan design must have a page, its own Mayzing checkout URL, copy facts,
# and images that are never double-prefixed with the store domain.
MICHIGAN_NAMES = {slug: p["name"] for slug, p in MICHIGAN.items()}


class MichiganMayzingProducts(unittest.TestCase):
    """Michigan/Wolverines is served from the Mayzing storefront.

    Its mockups are hot-linked from the Mayzing CDN until dl.py localises
    them, so abs_url() must let remote URLs through untouched - never prefix
    the store domain a second time.
    """

    @classmethod
    def setUpClass(cls):
        cls.michigan = MICHIGAN
        cls.cols = load_json("data/collections.json")

    def test_slugs_in_source_catalogue(self):
        self.assertGreaterEqual(len(self.michigan), 15)
        for slug, p in self.michigan.items():
            self.assertTrue(p.get("checkout_url", "").startswith("https://gridironlocker.shop/"),
                            slug)

    def test_belong_to_michigan_collection(self):
        """Michigan's page set is the Mayzing file minus data/delisted.json, and
        the build must agree with it - neither a Viralstyle re-crawl nor a fresh
        Mayzing capture may resurrect a page."""
        import build  # noqa: E402
        built = {it["slug"] for it in build.MODEL["michigan"]}
        self.assertEqual(built, set(self.michigan),
                         "Michigan pages must mirror data/mayzing_michigan.json")
        for slug in self.michigan:
            self.assertIn(slug, built, slug)
        self.assertFalse(built & DELISTED,
                         f"delisted designs rebuilt as pages: {sorted(built & DELISTED)}")

    def test_retired_michigan_designs_have_no_pages(self):
        """A Michigan design retired via data/delisted.json stays in the
        Mayzing capture (the file mirrors the storefront) but must never get a
        sellable page back. Its URL still resolves - only as a noindex redirect
        stub forwarding to the Michigan collection: no Product schema, no
        checkout hand-off, and no sitemap/search entry. This is the Cleveland
        guard rail (test_held_and_retired_cleveland_designs_have_no_pages)
        applied to the second Mayzing collection."""
        retired = sorted(s for s, col in MAYZING_RETIRED.items() if col == "michigan")
        if not retired:
            self.skipTest("no retired design is listed in data/mayzing_michigan.json")
        shop = os.path.join(SITE, "shop")
        sitemap = page("sitemap.xml")
        search = page("assets/search-index.json")
        for slug in retired:
            why = f"retired design {slug}"
            fp = os.path.join(shop, slug, "index.html")
            self.assertTrue(os.path.isfile(fp), f"{why} must keep a stub, never 404")
            html = read(fp)
            self.assertIn("data-gl-redirect", html, f"{why} must be a redirect stub")
            self.assertIn('name="robots" content="noindex', html, f"{why} stub must be noindex")
            self.assertRegex(html, r'data-gl-redirect="/michigan-wolverines-shirts/"',
                             f"{why} must forward to the Michigan collection")
            self.assertNotIn('"@type":"Product"', html.replace(" ", ""),
                             f"{why} must not publish Product schema")
            self.assertNotIn("gridironlocker.shop/", html,
                             f"{why} must not hand a customer to checkout")
            self.assertNotIn(f"/shop/{slug}/", sitemap, f"{why} must leave the sitemap")
            self.assertNotIn(f"/shop/{slug}/", search, f"{why} must leave site search")

    def test_product_pages_generated_with_checkout(self):
        for slug, p in self.michigan.items():
            fp = os.path.join(SITE, "shop", slug, "index.html")
            self.assertTrue(os.path.isfile(fp), slug)
            html = read(fp)
            self.assertIn(p["checkout_url"], html, slug)
            self.assertIn("https://gridironlocker.store/michigan-wolverines-shirts/", html, slug)
            self.assertNotIn("viralstyle", html.lower(), slug)

    def test_remote_fallback_and_no_double_prefix(self):
        for slug, p in self.michigan.items():
            img = p.get("img", {})
            self.assertIn("front", img, slug)
            for tag, url in img.items():
                self.assertTrue(url.startswith("https://"), f"{slug} {tag} {url}")
                self.assertNotIn("gridironlocker.storehttps://", url, f"{slug} {tag}")
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertNotIn("gridironlocker.storehttps://", html, slug)

    def test_schema_and_sitemap_use_remote_images(self):
        # The Product schema hot-links the Mayzing CDN until dl.py lands local
        # WebP; once local, abs_url() prefixes the store domain. Either is
        # valid - a double-prefixed URL is not.
        for slug in self.michigan:
            html = read(os.path.join(SITE, "shop", slug, "index.html"))
            self.assertIn('"image":[', html, slug)
            snippet = html.split('"image":[', 1)[1][:600]
            self.assertTrue(
                "mayzing.com" in snippet or "/img/p/" + slug in snippet, slug)
            self.assertNotIn("https://gridironlocker.storehttps://", html, slug)
        sm = page("sitemap-images.xml")
        for slug in self.michigan:
            self.assertIn(slug, sm, slug)
            self.assertNotIn("gridironlocker.storehttps://", sm, slug)

    def test_catalogue_copy_added(self):
        from catalog import CATALOG
        for slug in self.michigan:
            self.assertIn(slug, CATALOG, slug)
            self.assertTrue(CATALOG[slug].get("name"), slug)


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
        import build  # noqa: E402
        live = {it["slug"] for it in build.ALL}   # master catalogue, both partners
        row = self.html[self.html.index('id="picks"'):
                        self.html.index('id="locker"')]
        slugs = re.findall(r'<a class="jfeat[^"]*" href="[^"]*?/shop/([a-z0-9-]+)/\?creator=JOE"',
                           row)
        self.assertEqual(len(slugs), 4, slugs)
        self.assertEqual(slugs, self.creators["featured"])
        for s in slugs:
            self.assertIn(s, live, s)

    def test_grid_is_exactly_the_curated_picks(self):
        import build  # noqa: E402
        live = {it["slug"] for it in build.ALL}   # master catalogue, both partners
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
        from urllib.parse import unquote

        fp = os.path.join(SITE, "michigan/joe/index.html")
        attr = re.compile(r'(?:src|data-src|href|content)="([^"]+)"')
        for m in attr.finditer(self.html):
            val = m.group(1).strip()
            if not (val.startswith("/") or val.startswith("./") or val.startswith("../")):
                continue
            val = unquote(val.split("#")[0].split("?")[0])
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


class BellaLocker(unittest.TestCase):
    """Bella's supplier-linked collection and boutique-style landing page."""

    def setUp(self):
        self.html = page("michigan/bella/index.html")
        self.joe = page("michigan/joe/index.html")
        self.css = page("assets/style.css")
        self.cre = load_json("data/creators.json")["creators"]["bella"]
        self.catalog = self.cre["store_catalogue"]
        self.girly = self.cre["girly"]

    def test_seven_supplier_products_are_scoped_to_bella(self):
        import build  # noqa: E402

        items = build.creator_items(self.cre)
        self.assertEqual(len(items), 7)
        self.assertEqual([item["slug"] for item in items], self.cre["picks"])
        self.assertEqual([p["slug"] for p in self.catalog["products"]], self.cre["picks"])
        for item in items:
            self.assertTrue(item["external_store"])
            self.assertTrue(item["source_url"].startswith("https://silenttouch.store/"))
            self.assertEqual(item["col"], "michigan")

    def test_each_design_links_to_its_supplier_listing_with_attribution(self):
        from urllib.parse import parse_qs, urlsplit

        cards = re.findall(r'<article class="gproduct".*?</article>', self.html, re.S)
        products = {item["slug"]: item for item in self.catalog["products"]}
        self.assertEqual(len(cards), 7)
        self.assertEqual(
            re.findall(r'<article class="gproduct" data-slug="([^"]+)"', self.html),
            self.cre["picks"])
        for slug, card in zip(self.cre["picks"], cards):
            product = products[slug]
            source = urlsplit(product["source_url"])
            links = re.findall(r'href="(https://silenttouch\.store[^"]+)"', card)
            self.assertEqual(len(links), 2, slug)
            for href in links:
                parsed = urlsplit(unescape(href))
                query = parse_qs(parsed.query)
                self.assertEqual(parsed.netloc, "silenttouch.store")
                self.assertEqual(parsed.path, source.path)
                self.assertEqual(query.get("productId"), [product["product_id"]])
                self.assertEqual(query.get("creator"), ["BELLA"])
                self.assertEqual(query.get("utm_source"), ["creator"])
                self.assertEqual(query.get("utm_medium"), ["referral"])
                self.assertEqual(query.get("utm_campaign"), ["creator-BELLA"])
            self.assertIn('target="_blank"', card)
            self.assertIn('rel="noopener noreferrer"', card)
            self.assertIn(escape_html(product["image"]), card)
            self.assertIn("Explore available styles", card)
            expected_price = f"${float(product['price_usd']):.2f}"
            self.assertIn(
                f'<div class="gproduct-meta"><span>{escape_html(product["garment"])}</span>'
                f'<b>{expected_price}</b></div>',
                card)

    def test_logo_lockup_starts_with_a_capital(self):
        """The lockup is her signature, not a label: "Bella’s", not "bella’s".

        The script line used to be lower-cased on the way out, so a record
        that authored "Bella’s" rendered "bella’s" in the handwriting face.
        Only the first letter is touched; the rest is the record's own casing.
        """
        script = re.search(r'<span class="glogo-script">([^<]*)</span>', self.html)
        self.assertIsNotNone(script)
        value = script.group(1)
        self.assertTrue(value[0].isupper(), value)
        self.assertEqual(value[0], "B")
        serif = re.search(r'<span class="glogo-serif">([^<]*)</span>', self.html)
        self.assertEqual(serif.group(1), "COLLECTION")

    def test_page_loads_app_js_exactly_once(self):
        """The girly page drops the sitewide footer - and with it the only
        place the page shell emitted a script - so /michigan/bella/ shipped
        no JavaScript at all and every button on it was inert. The page now
        closes with the same load the footer gives every other page: app.js
        exactly once, deferred, and the document properly closed."""
        loads = re.findall(r'<script src="[^"]*assets/app\.js(?:\?v=[0-9a-f]{8})?"[^>]*></script>',
                           self.html)
        self.assertEqual(len(loads), 1)
        self.assertIn("defer", loads[0])
        self.assertTrue(self.html.endswith("</body></html>"))
        # the shell page (footer included) still loads it exactly once too
        self.assertEqual(
            len(re.findall(r'src="[^"]*assets/app\.js(?:\?v=[0-9a-f]{8})?"',
                           self.joe)), 1)

    def test_storewide_apparel_options_are_named_without_promising_per_design_stock(self):
        """The category tiles name the styles her store showed and the page
        stays light on words: no standing caveat paragraph, no live status
        essay, no per-card disclaimer - the swap, the on-card tag and each
        design's own product page carry the details."""
        text = unescape(self.html)
        for category in self.catalog["categories"]:
            self.assertIn(f"<span>{category}</span>", text)
        for kind in ("T-shirts", "Hoodies", "Sweatshirts", "Long Sleeves",
                     "Tank Tops", "Caps & Hats"):
            self.assertIn(kind, text)
        # the chips' screen-reader counts still date the check
        self.assertIn(self.catalog["apparel_captured"], text)
        self.assertIn(f"listed by 7 of 7 designs in the {self.catalog['apparel_captured']} check", text)
        # ...but the wordy standing note, the live status line, the muted-card
        # badge and the per-card disclaimer are gone
        self.assertNotIn("gcategory-note", self.html)
        self.assertNotIn("gcatStatus", self.html)
        self.assertNotIn("gcategory-status", self.html)
        self.assertNotIn("when it was checked on", text)
        self.assertNotIn("Tap the active style", text)
        self.assertNotIn("Confirm on the product page", text)
        self.assertNotIn("Confirm this design’s styles", text)
        self.assertNotIn("gproduct-badge", self.html)
        self.assertNotIn("gproduct-note", self.html)
        # every category lists real garments for at least one design, so the
        # empty-category flag ("not listed yet") does not render either
        self.assertNotIn("not listed yet", text)
        # apparel tiles carry no price; each card in the locker shows its USD price
        apparel = self.html[self.html.index('id="apparel"'):self.html.index('id="locker"')]
        locker = self.html[self.html.index('id="locker"'):self.html.index('id="about"')]
        self.assertNotIn("$", apparel)
        self.assertIn("$23.00", locker)
        self.assertIn("$30.00", locker)

    def test_apparel_categories_are_buttons_that_swap_the_products(self):
        """The six store-wide categories are real buttons that change the
        displayed garment. Non-cap choices keep every design reachable and
        mute unavailable styles; Caps & Hats lists only designs with a cap.
        A category the store never listed still says so instead of swapping."""
        labels = self.catalog["categories"]
        styles = self.catalog["apparel_styles"]
        self.assertEqual(len(labels), 6)
        buttons = re.findall(r'<button class="gcategory-tile"[^>]*>.*?</button>',
                             self.html, re.S)
        self.assertEqual(len(buttons), len(labels))
        slugs = ["t-shirts", "hoodies", "sweatshirts", "long-sleeves", "tank-tops",
                 "caps-hats"]
        self.assertEqual(list(styles), slugs)
        for button, label, slug in zip(buttons, labels, slugs):
            self.assertIn('type="button"', button)
            self.assertIn(f'data-gcat="{slug}"', button)
            self.assertIn('aria-controls="gcollectionGrid"', button)
            self.assertIn('aria-pressed="false"', button)   # nothing selected yet
            self.assertIn(f"<span>{escape_html(label)}</span>", button)  # accessible name
            self.assertIn("<svg", button)
            wanted = escape_html(styles[slug][0]) if styles[slug] else ""
            self.assertIn(f'data-gstyle="{wanted}"', button)
        # caps and hats: the store's hats filter lists a Heavy Cotton Cap for
        # four of the seven designs, so the tile offers that swap - no
        # empty-category flag anywhere on the page
        self.assertEqual(styles["caps-hats"], ["Heavy Cotton Cap"])
        self.assertIn('data-gstyle="Heavy Cotton Cap"', buttons[-1])
        self.assertNotIn("gcategory-flag", self.html)

        # The second row of buttons covers the five t-shirt listings, each
        # carrying the style it shows and the number of designs that listed it.
        counts = {}
        for product in self.catalog["products"]:
            for rows in (product["apparel"] or {}).values():
                for row in rows:
                    counts[row["garment"]] = counts.get(row["garment"], 0) + 1
        chips = re.findall(r'<button class="gstyle-chip"[^>]*>.*?</button>', self.html, re.S)
        self.assertEqual(len(chips), 5)
        for chip, style in zip(chips, styles["t-shirts"]):
            self.assertIn('type="button"', chip)
            self.assertIn('data-gcat="t-shirts"', chip)
            self.assertIn(f'data-gstyle="{escape_html(style)}"', chip)
            self.assertIn('aria-controls="gcollectionGrid"', chip)
            self.assertIn('aria-pressed="false"', chip)
            self.assertIn(f'<span class="gstyle-name">{escape_html(style)}</span>', chip)
            shown = re.search(r'<span class="gstyle-count" aria-hidden="true">(\d+)</span>', chip)
            self.assertIsNotNone(shown, style)
            self.assertEqual(int(shown.group(1)), counts[style], style)
            self.assertIn(f"listed by {counts[style]} of 7 designs in the "
                          f"{self.catalog['apparel_captured']} check", unescape(chip))
        row = re.search(r'<div class="gstyle-row"([^>]*)>', self.html)
        self.assertIsNotNone(row)
        self.assertIn('role="group"', row.group(1))
        self.assertIn("hidden", row.group(1))   # revealed only for a tee style

        # the tiles are grouped under their heading - no standing-caveat
        # paragraph to describe them any more
        tiles = re.search(r'<div class="gcategory-tiles"([^>]*)>', self.html)
        self.assertIsNotNone(tiles)
        self.assertIn('role="group"', tiles.group(1))
        self.assertIn('aria-labelledby="gcatHeading"', tiles.group(1))
        self.assertNotIn("aria-describedby", tiles.group(1))

        # the grid carries the captured matrix the swap reads - and nothing
        # else: the pink per-card "Showing {style}" badge was removed on
        # request, so neither the template nor the card markup ships
        grid = re.search(r'<div class="ggrid" id="gcollectionGrid" data-apparel="([^"]*)">',
                         self.html, re.S)
        self.assertIsNotNone(grid)
        self.assertNotIn("data-showing", self.html)
        payload = json.loads(unescape(grid.group(1)))
        self.assertEqual(list(payload), self.cre["picks"])

        # the behaviour itself, and the fact that it is page-scoped, live in app.js
        js = page("assets/app.js")
        for term in (".gcategory-tile[data-gcat]", ".gstyle-chip[data-gstyle]",
                     "data-apparel", "card.hidden=false", "card.hidden=true",
                     "aria-pressed", "is-swapped", "scrollIntoView",
                     "prefers-reduced-motion"):
            self.assertIn(term, js, term)
        # a design with no listing in the chosen style leaves the grid; it is
        # never left behind greyed out (the creator block now matches the rule
        # the team pages already followed)
        self.assertIn("if(cat)card.hidden=true", js)
        self.assertNotIn("is-muted", js, "no creator card is greyed out any more")
        self.assertNotIn("is-muted", self.css)
        self.assertNotIn("gproduct-badge", js)
        self.assertNotIn("gcatStatus", js)
        # the removed pink card badge stays removed: no markup on the page, no
        # hook in the script, no rule in the stylesheet
        self.assertNotIn("gproduct-gtag", self.html)
        self.assertNotIn("gproduct-gtag", js)
        self.assertNotIn("data-showing", js)
        self.assertNotIn("gproduct-gtag", self.css)
        self.assertIn("var row=document.querySelector('.gcategory-tiles'); if(!row)return;", js)
        self.assertIn("var grid=document.querySelector('.ggrid[data-apparel]'); if(!grid)return;", js)
        # the swap updates both card links, the garment label and the USD price,
        # and restores all three when cleared
        bella_js = js[js.index("// ---------- creator apparel-style buttons"):]
        self.assertIn(".gproduct-meta span", bella_js)
        self.assertIn(".gproduct-meta b", bella_js)
        self.assertIn("entry.price", bella_js)
        self.assertIn("card._price", bella_js)

        # Regression model for the partial category: derive the cards that the
        # Caps & Hats click is allowed to leave in the grid from the same JSON
        # payload consumed by app.js. This deliberately does not hard-code the
        # four names; if the captured catalogue changes, the expected list
        # follows its audited matrix while still pinning the list-only rule.
        cap_style = styles["caps-hats"][0]
        self.assertEqual(cap_style, "Heavy Cotton Cap")
        cap_slugs = [
            slug for slug, groups in payload.items()
            if any(row["garment"] == cap_style
                   for row in groups.get("caps-hats", []))
        ]
        self.assertEqual(len(cap_slugs), 4)
        self.assertEqual(
            cap_slugs,
            ["michigan-heart", "navy-maize-m", "michigan-vs-all",
             "bold-maize-m-streetwear"])
        no_cap_slugs = [slug for slug in self.cre["picks"]
                        if slug not in cap_slugs]
        self.assertEqual(len(no_cap_slugs), 3)
        for slug in cap_slugs:
            rows = payload[slug]["caps-hats"]
            self.assertEqual(len(rows), 1, slug)
            self.assertEqual(rows[0]["garment"], "Heavy Cotton Cap")
            self.assertTrue(rows[0]["image"], slug)
            self.assertTrue(rows[0]["url"], slug)
        for slug in no_cap_slugs:
            self.assertNotIn("caps-hats", payload[slug])

        # The initial HTML remains complete and indexable: hiding is applied
        # only after an explicit click, and clearing that pressed choice must
        # restore all seven cards. The order below matters because restore()
        # runs before the branch that takes a design out of the grid.
        self.assertNotIn('<article class="gproduct" hidden', self.html)
        bella_js = js[js.index("// ---------- creator apparel-style buttons"):]
        restore_at = bella_js.index("card.hidden=false")
        remove_at = bella_js.index("if(cat)card.hidden=true")
        self.assertLess(restore_at, remove_at)
        self.assertIn("if(cat===nextCat&&garment===nextGarment)", bella_js)
        self.assertIn("{cat=null;garment=null;exact=false;}", bella_js)
        self.assertIn("if(!cat)return;", bella_js)

    def test_swapped_garments_match_what_bellas_store_publishes(self):
        """The matrix a click shows is the matrix her live store showed.

        Every garment in data/creators.json was captured from the store's own
        category filter pages on 2026-10-12 (?category=hoodie / sweatshirt /
        long_sleeve / tank_top / hats, which list one product per design; each
        listing's own "Product" field names the garment), so the page payload
        must carry exactly those listings - and the coverage must stay the
        store's: no invented garment, no invented design.
        """
        from urllib.parse import parse_qs, urlsplit

        # coverage as captured from the filters: 7/7/6/4/3 tee listings, a
        # hoodie, sweatshirt, long sleeve and tank top for every one of the
        # seven designs, and a Heavy Cotton Cap for four of them.
        counts = {}
        artworks = {}
        for product in self.catalog["products"]:
            for cat, rows in (product["apparel"] or {}).items():
                self.assertIn(cat, self.catalog["apparel_styles"])
                for row in rows:
                    counts[row["garment"]] = counts.get(row["garment"], 0) + 1
                    art = re.search(r"s:([0-9a-f]+)-", row["image"])
                    self.assertIsNotNone(art, row["image"])
                    artworks.setdefault(art.group(1), set()).add(row["garment"])
                    self.assertTrue(row["product_id"])
                    self.assertTrue(row["product_id"] in row["url"], row["url"])
                    self.assertTrue(float(row["price_usd"]) > 0, row)
                    self.assertIs(row["price_seen"], True)
        self.assertEqual(counts, {
            "Women's Fitted Tee": 7, "Men's T-shirt": 7, "Premium T-Shirt": 6,
            "Ladies Slim T-Shirt": 5, "Women's V-neck Tee": 4,
            "Essential Hoodie": 7, "Unisex Sweatshirt": 7,
            "Unisex Tank Top": 7, "Long Sleeve T-Shirt": 7,
            "Heavy Cotton Cap": 4})
        self.assertEqual(self.catalog["apparel_styles"]["caps-hats"],
                         ["Heavy Cotton Cap"])
        # the long-sleeve and tank filters listed one product for every
        # design; the caps listing is the four Heavy Cotton Caps the store's
        # hats filter showed, as captured
        for cat, wanted in (("long-sleeves", self.cre["picks"]),
                            ("tank-tops", self.cre["picks"]),
                            ("caps-hats", ["michigan-heart", "navy-maize-m",
                                           "michigan-vs-all",
                                           "bold-maize-m-streetwear"])):
            slugs = [product["slug"] for product in self.catalog["products"]
                     if product["apparel"].get(cat)]
            self.assertEqual(slugs, wanted, cat)
        # the s: artwork id is not a garment label: one uuid is shared by a
        # ladies slim tee, a tank top and a long sleeve, which is why every
        # label above had to be page-verified instead of decoded from the URL
        self.assertEqual(artworks["293b0ab4"],
                         {"Ladies Slim T-Shirt", "Unisex Tank Top", "Long Sleeve T-Shirt"})

        # the page payload carries the captured matrix, the signed mockup,
        # the attributed listing URL and the formatted USD price
        grid = re.search(r'<div class="ggrid" id="gcollectionGrid" data-apparel="([^"]*)">',
                         self.html, re.S)
        self.assertIsNotNone(grid)
        self.assertNotIn("price_seen", grid.group(1))
        payload = json.loads(unescape(grid.group(1)))
        self.assertEqual(list(payload), self.cre["picks"])
        by_slug = {product["slug"]: product for product in self.catalog["products"]}
        for slug, product in by_slug.items():
            self.assertEqual(sorted(payload[slug]), sorted(product["apparel"]))
            for cat, rows in product["apparel"].items():
                self.assertEqual([entry["garment"] for entry in payload[slug][cat]],
                                 [row["garment"] for row in rows])
                for entry, row in zip(payload[slug][cat], rows):
                    # the mockup URL is the signed one, copied verbatim
                    self.assertEqual(entry["image"], row["image"])
                    self.assertEqual(entry["price"], f"${float(row['price_usd']):.2f}")
                    self.assertIn("sig:", entry["image"])
                    self.assertIn(",w:500/image.png", entry["image"])
                    parsed = urlsplit(unescape(entry["url"]))
                    query = parse_qs(parsed.query)
                    self.assertEqual(parsed.netloc, "silenttouch.store")
                    self.assertEqual(parsed.path, f"/{slug}")
                    self.assertEqual(query.get("productId"), [row["product_id"]])
                    self.assertEqual(query.get("creator"), ["BELLA"])
                    self.assertEqual(query.get("utm_campaign"), ["creator-BELLA"])
        # each card's own category ids are the categories it actually listed
        cards = re.findall(r'<article class="gproduct" data-slug="([^"]+)" '
                           r'data-creator="BELLA" data-gcat="([^"]*)"', self.html)
        self.assertEqual([slug for slug, _ in cards], self.cre["picks"])
        for slug, cats in cards:
            self.assertEqual(sorted(cats.split()), sorted(by_slug[slug]["apparel"]), slug)
    def test_boutique_banner_local_navigation_and_anchors(self):
        self.assertEqual(self.cre["hero"],
                         "/michigan/bella/Smiling Michigan Campus Portrait.png")
        self.assertEqual((self.cre["hero_w"], self.cre["hero_h"]), (1894, 830))
        self.assertEqual(self.girly["hero_image"], self.cre["hero"])
        self.assertEqual(self.girly["hero_alt"], self.cre["hero_alt"])
        self.assertTrue(os.path.isfile(os.path.join(
            SITE, "michigan/bella/Smiling Michigan Campus Portrait.png")))
        # a space is not a legal URL character, so the build percent-encodes the
        # banner path everywhere it emits it as a URL
        self.assertIn('class="gbanner-photo" '
                      'src="../../michigan/bella/Smiling%20Michigan%20Campus%20Portrait.png"',
                      self.html)
        self.assertIn('<meta property="og:image" content="https://gridironlocker.store'
                      '/michigan/bella/Smiling%20Michigan%20Campus%20Portrait.png">',
                      self.html)
        self.assertNotIn("bella-banner.jpg", self.html)
        self.assertIn('width="1894" height="830"', self.html)
        self.assertIn('alt="Smiling Michigan fan in a navy MICHIGAN tee', self.html)
        self.assertIn("fetchpriority=\"high\"", self.html)
        self.assertIn('class="logo glogo"', self.html)
        nav = re.search(r'<nav class="bellanav".*?</nav>', self.html, re.S)
        self.assertIsNotNone(nav)
        for link in ('href="../../"', 'href="#locker"', 'href="#apparel"',
                     'href="#about"', 'href="#custom-form"'):
            self.assertIn(link, nav.group(0))
        # the inquiry form sits below the whole grid, so the menu carries the
        # only shortcut to it - and the label says what it is
        self.assertIn('href="#custom-form">Custom Design</a>', nav.group(0))
        self.assertLess(self.html.index('class="bellanav"'),
                        self.html.index('<main id="main" class="jlock jlock-girly">'))
        ids = re.findall(r'id="([^"]+)"', self.html)
        self.assertEqual(len(ids), len(set(ids)))
        for anchor in re.findall(r'href="#([^"]+)"', self.html):
            self.assertIn(anchor, ids, f"missing anchor target #{anchor}")

    def test_lockup_keeps_the_visitor_inside_bellas_collection(self):
        """Her script lockup is the collection's OWN masthead, not the
        storefront GL wordmark, so tapping it must leave the visitor on
        /michigan/bella/.

        It shipped as ``href="/"``, which relativise() rewrote to ``../../``:
        the Gridiron Locker homepage. A shopper who tapped the wordmark that
        says "bella's COLLECTION" was thrown out of the collection she was
        browsing - the one exit this page is built to avoid, in the slot a
        visitor's eye goes to first.

        The link now carries the creator's own canonical path (the same
        ``path`` page_creator canonicalises and sitemaps), so a future girly
        creator page cannot inherit Bella's URL by accident. Every other page
        - Joe's included - still renders the storefront wordmark -> homepage.
        """
        logo = re.search(r'<a class="logo glogo" href="([^"]+)"', self.html)
        self.assertIsNotNone(logo, "Bella's masthead lockup is missing")
        # two directories deep, so /michigan/bella/ relativises to this
        self.assertEqual(logo.group(1), "../../michigan/bella/")
        # and that href resolves to her own page, not the site root
        landing = os.path.normpath(os.path.join(SITE, "michigan/bella",
                                                logo.group(1)))
        self.assertEqual(landing, os.path.join(SITE, "michigan", "bella"))
        self.assertTrue(os.path.isfile(os.path.join(landing, "index.html")))
        self.assertNotIn('class="logo glogo" href="../../"', self.html)
        # Joe's page keeps the storefront wordmark, pointed at the homepage
        self.assertIn('class="logo" href="../../"', self.joe)

    def test_banner_store_link_is_hidden_when_the_creator_asks(self):
        """Bella's banner offers one action, not two: ``hide_banner_store_link``
        drops the "Visit Silent Touch" link that restated the storefront the
        cards already open, and leaves the "Shop now" anchor CTA beside it.
        The store notes further down the page are deliberately untouched - a
        shopper still needs to know where checkout happens."""
        self.assertTrue(self.girly["hide_banner_store_link"])
        actions = re.search(r'<div class="gbanner-actions">(.*?)</div>', self.html, re.S)
        self.assertIsNotNone(actions)
        self.assertIn('class="gbtn gbtn-maize" href="#locker"', actions.group(0))
        self.assertNotIn("gbanner-link", actions.group(0))
        self.assertNotIn("Visit Silent Touch", actions.group(0))
        # nowhere else on the page revived the class either
        self.assertNotIn("gbanner-link", self.html)
        # the note under the grid still names the store the cards open on
        self.assertIn("Each design opens on", self.html)
        self.assertIn("silenttouch.store", self.html)

    def test_requested_canvas_banner_and_category_styles_are_bella_scoped(self):
        self.assertIn('body[data-creator-page="BELLA"]{background:#efefed', self.css)
        for selector in (".jlock-girly .gbanner-photo{", ".jlock-girly .gcategory-tiles{",
                         ".jlock-girly .gcategory-tile{", ".jlock-girly .gabout-copy{",
                         '.jlock-girly .gcategory-tile:focus-visible{',
                         '.jlock-girly .gcategory-tile[aria-pressed="true"]{',
                         ".jlock-girly .gcategory-flag{",
                         ".jlock-girly .gstyle-row{", ".jlock-girly .gstyle-chip{",
                         '.jlock-girly .gstyle-chip:focus-visible{',
                         '.jlock-girly .gstyle-chip[aria-pressed="true"]{',
                         ".jlock-girly .gstyle-count{", ".jlock-girly .gstyle-sr{",
                         ".jlock-girly .gproduct[hidden]{display:none}",
                         ".jlock-girly .gcustom-grid{", ".jlock-girly .gcustom-img{"):
            self.assertIn(selector, self.css)
        self.assertNotIn(".gbanner-art", self.css)
        self.assertIn("prefers-reduced-motion:reduce", self.css)
        tablet = media_rules(self.css, 980)
        self.assertIn(".jlock-girly .gcategory-tiles{grid-template-columns:repeat(3", tablet)
        mobile = media_rules(self.css, 760)
        self.assertIn(".jlock-girly .gbanner-photo{object-position:66% center}", mobile)

    def test_vip10_promo_is_clear_well_placed_and_the_custom_inquiry_form_remains(self):
        """VIP10 is the offer the owner asked for on Bella's page.

        It must be readable at a glance (10% off + the exact code), land in the
        first viewport (a banner above the hero) and be restated where the
        shopper picks designs and hands off to checkout. Every promo placement
        keeps its wording to "at checkout" with no store name (the owner asked
        for no Silent Touch in the promo copy); the prose beside them still
        names the store where checkout happens - never this site.
        """
        self.assertEqual(self.cre.get("promo"), {"code": "VIP10", "pct": 10})
        main = between(self.html, '<main id="main" class="jlock jlock-girly">', "</main>")

        # primary placement: above the hero banner, not buried below the grid
        self.assertLess(main.index('class="gpromobar"'), main.index('class="gbanner"'))
        bar = between(main, '<aside class="gpromobar"', "</aside>")
        for bit in ("10% off", "your order", "Use code", "VIP10", "Copy",
                    "at checkout"):
            self.assertIn(bit, bar, bit)
        self.assertNotIn("Silent Touch", bar)
        self.assertIn('data-copy-code="VIP10"', bar)
        self.assertIn('aria-label="Copy promo code VIP10"', bar)

        # second placement: directly above the product grid
        head = between(main, '<div class="gcollection-head">', "</div>")
        self.assertIn('class="gcollection-promo"', head)
        pill = between(head, '<p class="gcollection-promo">', "</p>")
        for bit in ("10% off", "with code", "<strong>VIP10</strong>",
                    "at checkout"):
            self.assertIn(bit, pill, bit)
        self.assertNotIn("Silent Touch", pill)

        # and again beside the hand-off under the grid
        note = between(main, '<p class="gstore-note">', "</p>")
        self.assertIn('class="gstore-promo"', note)
        promo_span = between(note, '<span class="gstore-promo">', "</span>")
        self.assertIn("10% off your order", promo_span)
        self.assertIn("<strong>VIP10</strong>", promo_span)
        self.assertIn("at checkout", promo_span)
        self.assertNotIn("Silent Touch", promo_span)
        # the prose beside the promo still names the store checkout happens on
        self.assertIn("Each design opens on", note)
        self.assertIn("Silent Touch", note)

        # the FAQ schema (this page has no visible FAQ block) answers it too
        faq = next(node for node in json_ld_nodes(self.html)
                   if node.get("@type") == "FAQPage")
        faq_text = json.dumps(faq)
        self.assertIn("VIP10", faq_text)
        self.assertIn("10% off", faq_text)

        # copy control is wired; the code itself never depends on JavaScript
        self.assertIn("gpromobar-code[data-copy-code]", page("assets/app.js"))
        for selector in (".jlock-girly .gpromobar{", ".jlock-girly .gpromobar-code{",
                         ".jlock-girly .gpromobar-copy{",
                         ".jlock-girly .gcollection-head>p.gcollection-promo{",
                         ".jlock-girly .gstore-promo{"):
            self.assertIn(selector, self.css)
        self.assertIn(".jlock-girly .gpromobar-rule{display:none}",
                      media_rules(self.css, 760))
        # the generic sitewide promo bar is still not revived on her page
        self.assertNotIn('class="promo"', self.html.lower())
        # and Bella's banner never leaks onto Joe's page (or vice versa)
        self.assertNotIn("gpromobar", self.joe)

        self.assertNotIn("class=\"gcustom-note\"", self.html)
        self.assertIn('id="customForm"', self.html)
        self.assertIn('data-formsubmit="1"', self.html)
        self.assertIn('name="idea"', self.html)
        # the custom offer carries the same custom-tee photo the main site's
        # custom-design section shows, beside the form
        self.assertIn('class="gcustom-img"', self.html)
        self.assertIn("custom-tee1.jpg", self.html)
        self.assertIn('alt="Custom t-shirt design - make your own fan apparel"', self.html)
        self.assertLess(self.html.index('class="gcustom-img"'),
                        self.html.index('id="custom-form"'))

        # custom-tee1.jpg is a 2:3 portrait. Let its intrinsic aspect ratio
        # render the complete image: fixed heights and breakpoint max-heights
        # used to cut off the bottom of the photo beside the form.
        image_rule = css_block(self.css, ".jlock-girly .gcustom-img img")
        self.assertIn("width:100%", image_rule)
        self.assertIn("height:auto", image_rule)
        self.assertIn("object-fit:contain", image_rule)
        self.assertNotIn("object-fit:cover", image_rule)
        self.assertNotIn("max-height", image_rule)
        self.assertNotIn("object-position", image_rule)
        self.assertNotIn(".jlock-girly .gcustom-img img{max-height:",
                         media_rules(self.css, 760))
        self.assertNotIn(".jlock-girly .gcustom-img img{max-height:",
                         media_rules(self.css, 430))

    def test_page_is_indexable_and_schema_uses_supplier_listings(self):
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/michigan/bella/">',
                      self.html)
        self.assertIn("<loc>https://gridironlocker.store/michigan/bella/</loc>",
                      page("sitemap.xml"))
        self.assertIn('data-creator-page="BELLA"', self.html)
        self.assertNotIn('name="robots" content="noindex', self.html)
        nodes = json_ld_nodes(self.html)
        collection = next(node for node in nodes if node.get("@type") == "CollectionPage")
        urls = [entry.get("url") for entry in collection["about"]["itemListElement"]]
        self.assertEqual(urls, [product["source_url"]
                                 for product in self.catalog["products"]])

    def test_joe_and_the_public_michigan_catalogue_are_not_replaced(self):
        import build  # noqa: E402

        self.assertNotIn("bellanav", self.joe)
        self.assertNotIn("gproduct", self.joe)
        self.assertIn('class="jfeat"', self.joe)
        bella_slugs = {product["slug"] for product in self.catalog["products"]}
        public_slugs = {item["slug"] for item in build.MODEL["michigan"]}
        self.assertTrue(bella_slugs.isdisjoint(public_slugs))

    def test_local_asset_references_resolve(self):
        from urllib.parse import unquote

        fp = os.path.join(SITE, "michigan/bella/index.html")
        attr = re.compile(r'(?:src|data-src|href|content)="([^"]+)"')
        for match in attr.finditer(self.html):
            value = unescape(match.group(1).strip())
            if not (value.startswith("/") or value.startswith("./") or value.startswith("../")):
                continue
            # the campus hero banner is a .png with spaces in its filename, and
            # the build percent-encodes it in URLs
            value = unquote(value.split("#")[0].split("?")[0])
            if value in ("", "/", "./"):
                continue
            target = (os.path.join(SITE, value.lstrip("/")) if value.startswith("/")
                      else os.path.join(os.path.dirname(fp), value))
            target = os.path.normpath(target)
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            self.assertTrue(os.path.isfile(target), f"{fp}: {value}")


class CrystalMarieLocker(unittest.TestCase):
    """Crystal Marie's Browns collection - Bella's locker, Browns palette.

    This is the first creator locker curated from THIS site's own catalogue
    (the Cleveland Browns collection) instead of a captured partner store, so
    it has to prove three things at once:

    * the whole live Browns collection ships in the collection page's own
      order (newest -> oldest), minus designs hidden on request, and every
      card opens the local product page with ``?creator=CRYSTAL``;
    * the CRYSTAL discount (10% off) is stated clearly in the same three
      placements as Bella's VIP10 offer and never promises a checkout this
      site does not run;
    * the browns skin is scoped - no Bella copy, no browns rule reaching her
      page, and a disclaimer naming the Browns/NFL rather than Michigan.
    """

    def setUp(self):
        import build  # noqa: E402

        self.build = build
        self.html = page("crystal/index.html")
        self.cre = load_json("data/creators.json")["creators"]["crystal"]
        # the page's own depth ("../" at /crystal/, "../../" at a nested slug),
        # so a future move does not need every path assertion rewritten
        self.prefix = "../" * max(1, len([part for part
                                          in self.cre["page_slug"].split("/") if part]))
        self.bella = page("michigan/bella/index.html")
        self.css = page("assets/style.css")

    def test_page_is_indexable_sitemapped_and_closes_with_app_js(self):
        self.assertIn('<link rel="canonical" '
                      'href="https://gridironlocker.store/crystal/">',
                      self.html)
        self.assertIn("<loc>https://gridironlocker.store/crystal/</loc>",
                      page("sitemap.xml"))
        self.assertIn('data-creator-page="CRYSTAL"', self.html)
        self.assertNotIn('name="robots" content="noindex', self.html)
        self.assertTrue(self.html.endswith("</body></html>"))
        loads = re.findall(r'<script src="[^"]*assets/app\.js(?:\?v=[0-9a-f]{8})?"[^>]*></script>',
                           self.html)
        self.assertEqual(len(loads), 1)
        self.assertIn("defer", loads[0])

    def test_the_locker_carries_the_whole_live_browns_collection(self):
        items = self.build.creator_items(self.cre)
        live = [item["slug"] for item in self.build.MODEL["cleveland-browns"]]
        # the locker reads like the collection page: the catalogue order it is
        # built in (newest capture first), not her picks-first order
        self.assertEqual(self.cre.get("order"), "newest")
        self.assertEqual([item["slug"] for item in items], live)
        self.assertEqual(self.cre.get("include_collection"), True)
        # Her record lists every Browns design explicitly today. The equality
        # is not pinned: include_collection stays on, so a design the Mayzing
        # crawl adds tomorrow still reaches her page - and the page's own
        # "ALL {n} BROWNS DESIGNS" count follows it - without a failing build.
        self.assertTrue(set(self.cre["picks"]) <= set(live))
        self.assertTrue(set(live) <= set(self.cre["picks"]) | set(live))
        cards = re.findall(r'<article class="gproduct" data-slug="([^"]+)"',
                           self.html)
        self.assertEqual(cards, [item["slug"] for item in items])
        self.assertEqual(len(set(cards)), len(cards))
        # every design opens the local product page, still creator-tagged
        for slug in cards:
            block = re.search(r'<article class="gproduct" data-slug="%s".*?</article>'
                              % re.escape(slug), self.html, re.S).group(0)
            self.assertIn(f'href="{self.prefix}shop/{slug}/?creator=CRYSTAL"', block)
            self.assertIn('data-creator="CRYSTAL"', block)
            # a local hand-off stays in this tab; the arrow says so too
            self.assertNotIn('target="_blank"', block)
            self.assertIn("See sizes &amp; price", block)
        self.assertNotIn('href=""', self.html)
        self.assertNotIn("silenttouch.store", self.html)
        self.assertNotIn("Explore available styles", self.html)

    def test_crystal_code_is_ten_percent_off_in_all_three_placements(self):
        self.assertEqual(self.cre.get("promo"), {"code": "CRYSTAL", "pct": 10})
        main = between(self.html,
                       '<main id="main" class="jlock jlock-girly" data-theme="browns">',
                       "</main>")
        # primary placement: above the hero, in the first viewport
        self.assertLess(main.index('class="gpromobar"'), main.index('class="gbanner"'))
        bar = between(main, '<aside class="gpromobar"', "</aside>")
        for bit in ("10% off", "your order", "Use code", "CRYSTAL", "Copy",
                    "at checkout"):
            self.assertIn(bit, bar, bit)
        self.assertIn('data-copy-code="CRYSTAL"', bar)
        self.assertIn('aria-label="Copy promo code CRYSTAL"', bar)
        # second placement: directly above the product grid
        head = between(main, '<div class="gcollection-head">', "</div>")
        self.assertIn('<span>10% off</span> with code <strong>CRYSTAL</strong> '
                      "at checkout", head)
        # third: beside the hand-off under the grid
        note = between(main, '<p class="gstore-note">', "</p>")
        self.assertIn("10% off your order", note)
        self.assertIn("<strong>CRYSTAL</strong>", note)
        # no other creator's code or partner store leaked onto this page
        for other in ("VIP10", "JOE10", "Silent Touch"):
            self.assertNotIn(other, self.html, other)
        # the code is copyable-but-visible, never dependent on JavaScript
        self.assertIn('class="gpromobar-code-value">CRYSTAL', bar)
        self.assertIn("gpromobar-code[data-copy-code]", page("assets/app.js"))

    def test_browns_skin_is_scoped_and_leaves_bellas_page_alone(self):
        self.assertEqual(self.cre.get("skin"), "browns")
        self.assertIn('data-theme="browns"', self.html)
        # the page-chrome palette keys off the SKIN, not off one creator, so
        # every browns locker (Crystal Marie's, Amber's) gets it for free
        self.assertIn('data-creator-skin="browns"', self.html)
        self.assertIn('body[data-creator-skin="browns"]{background:#f4ead9', self.css)
        self.assertNotIn('body[data-creator-page="CRYSTAL"]', self.css)
        for selector in ('.jlock-girly[data-theme="browns"] .gbanner-panel{',
                         '.jlock-girly[data-theme="browns"] .gbtn-maize{',
                         '.jlock-girly[data-theme="browns"] .gpromobar{',
                         '.jlock-girly[data-theme="browns"] .gscript{',
                         '.jlock-girly[data-theme="browns"] .gproduct{',
                         '.jlock-girly[data-theme="browns"] .gproduct-link{'):
            self.assertIn(selector, self.css)
        # the browns palette is unreachable from Bella's and Joe's pages, whose
        # own skin blocks still ship untouched
        self.assertNotIn('data-theme="browns"', self.bella)
        self.assertNotIn('data-theme="browns"', page("michigan/joe/index.html"))
        self.assertIn('body[data-creator-page="BELLA"]{background:#efefed', self.css)
        self.assertIn(".jlock-girly .gbtn-maize{background:#e99aaa", self.css)

    def test_copy_is_browns_first_and_never_claims_michigan(self):
        text = unescape(self.html)
        self.assertIn('<span class="gscript">Crystal’s</span>', text)
        self.assertIn("<h2>Shop the Browns Collection</h2>", text)
        # the head counts the live locker, so the promise cannot drift from it
        total = len(self.build.creator_items(self.cre))
        self.assertIn(f"<p class=\"goverline\">ALL {total} BROWNS DESIGNS</p>", text)
        self.assertIn("Crystal Marie’s Browns Collection", text)
        self.assertIn('aria-label="Crystal’s Collection home"', text)
        self.assertIn('aria-label="Crystal’s Collection"', text)
        self.assertNotIn("Bella", text)
        self.assertNotIn("Michigan", text)
        legal = between(text, '<p class="glegal">', "</p>")
        self.assertIn("Independent fan-made apparel.", legal)
        self.assertIn("Cleveland Browns", legal)
        self.assertIn("the NFL", legal)
        # the hero is the browns banner, deployed as a JPG at its native size
        # the filename is reused when the art is replaced, so the banner URL
        # carries the creator's cache version - a returning visitor must not
        # keep the old photo out of their browser/CDN cache
        hero_v = self.cre["girly"]["hero_v"]
        self.assertIn(f'src="{self.prefix}img/hero-crystal.jpg?v={hero_v}"',
                      self.html)
        w, h = self.cre["hero_w"], self.cre["hero_h"]
        self.assertIn(f'width="{w}" height="{h}"', self.html)
        self.assertEqual((w, h), (1916, 821))   # the 2026-10-24 replacement
        self.assertTrue(os.path.isfile(os.path.join(SITE, "img/hero-crystal.jpg")))
        # the banner describes what is actually in the photo
        self.assertIn("Cleveland Browns tee on a lakefront boardwalk", self.html)
        # PNG masters never ship
        self.assertFalse(os.path.isfile(os.path.join(SITE, "img",
                                                     "crystal-marie-banner.png")))
        self.assertFalse(os.path.isfile(os.path.join(SITE, "img",
                                                     "hero-crystal1.png")))

    def test_grid_order_matches_the_collection_page(self):
        """"from new to old, as the order on gridironlocker".

        Her grid reads exactly like /cleveland-browns-shirts/: the catalogue
        order the build captures (newest -> oldest), so a visitor who knows the
        store sees the same designs in the same sequence.
        """
        collection = page("cleveland-browns-shirts/index.html")
        team_order = re.findall(r'class="card[^"]*"[^>]*data-slug="([^"]+)"',
                                collection)
        her_order = re.findall(r'<article class="gproduct" data-slug="([^"]+)"',
                               self.html)
        self.assertTrue(team_order)
        self.assertEqual(her_order, team_order)
        # newest capture first: the 2026-10-14 wave leads, the older single-tee
        # designs trail
        self.assertEqual(her_order[0], "cleveland-victory-monday")
        self.assertEqual(her_order[-1], "ohio-cle")

    def test_the_hidden_design_is_gone_and_its_url_forwards(self):
        """One design was hidden on request: it leaves every surface.

        No card on her page, nothing on the Browns collection page, nothing in
        the search index, the feed or the sitemap - and its product URL answers
        with the same noindex redirect stub the retired designs use, so an old
        link lands on the collection instead of a 404.
        """
        slug = "dawg-pound-cleveland-skyline"
        self.assertNotIn(f'data-slug="{slug}"', self.html)
        self.assertNotIn(slug, page("cleveland-browns-shirts/index.html"))
        self.assertNotIn(slug, page("sitemap.xml"))
        self.assertNotIn(slug, page("assets/search-index.json"))
        self.assertNotIn(slug, page("feed.xml"))
        self.assertNotIn(slug, self.cre["picks"])
        stub = page(f"shop/{slug}/index.html")
        self.assertIn('<meta name="robots" content="noindex,follow">', stub)
        self.assertIn('<meta http-equiv="refresh" '
                      'content="0;url=https://gridironlocker.store/cleveland-browns-shirts/">',
                      stub)
        self.assertNotIn('rel="canonical"', stub)

    def test_the_short_url_is_the_page_and_the_old_one_forwards(self):
        """Her locker lives at /crystal/; /browns/crystal-marie/ forwards to it.

        The old address is already on shared links and stickers, and GitHub
        Pages has no server-side 301 - so the old path keeps a stub with the
        same single signal the retired product pages use: an instant meta
        refresh, noindex,follow, no canonical (a redirect stub and the page it
        forwards to are not duplicates), and a self-referencing og:url.
        """
        # the live page, its canonical and its sitemap entry
        self.assertTrue(self.html)
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/crystal/">',
                      self.html)
        sitemap = page("sitemap.xml")
        self.assertIn("<loc>https://gridironlocker.store/crystal/</loc>", sitemap)
        self.assertNotIn("browns/crystal-marie", sitemap)

        # the old address is a stub that forwards, never a second live page
        old = page("browns/crystal-marie/index.html")
        self.assertIn('<meta http-equiv="refresh" '
                      'content="0;url=https://gridironlocker.store/crystal/">', old)
        self.assertIn('<meta name="robots" content="noindex,follow">', old)
        self.assertIn('data-gl-redirect="/crystal/"', old)
        self.assertIn('content="https://gridironlocker.store/browns/crystal-marie/"', old)
        self.assertNotIn('rel="canonical"', old)
        self.assertNotIn("gcategory-tiles", old)      # no second copy of the page
        self.assertNotIn("gproduct", old)

        # hosts that read _redirects answer with a real 301
        self.assertIn("/browns/crystal-marie/ /crystal/ 301",
                      page("_redirects"))

        # every internal route to her locker uses the short URL
        self.assertIn('href="./crystal/"', page("index.html"))
        self.assertIn(f'href="../crystal/"',
                      page("cleveland-browns-shirts/index.html"))

    def test_logo_lockup_starts_with_a_capital(self):
        """Crystal's lockup opens "Crystal’s" in the script face.

        The first letter is upper-cased from the creator record; everything
        after it keeps the record's own casing.
        """
        script = re.search(r'<span class="glogo-script">([^<]*)</span>', self.html)
        self.assertIsNotNone(script)
        value = script.group(1)
        self.assertEqual(value[0], "C")
        self.assertEqual(value, self.cre["girly"]["hero_script"])
        self.assertIn('aria-label="Crystal’s Collection home"', self.html)

    def test_a_style_filter_removes_designs_that_do_not_list_it(self):
        """A style tile lists only the designs sold in that style.

        Greying the rest out was the earlier behaviour: click "Tank Tops" and
        thirty t-shirts stayed on the shelf, greyed like dead stock. The
        creator block now takes them out of the grid - the same rule the team
        collection pages already followed - and clearing the tile brings every
        card back.
        """
        js = page("assets/app.js")
        block = js[js.index("// ---------- creator apparel-style buttons"):]
        self.assertIn("if(cat)card.hidden=true", block)
        self.assertNotIn("is-muted", block)
        # restore() runs first, so clearing the choice un-hides every card
        self.assertLess(block.index("card.hidden=false"),
                        block.index("if(cat)card.hidden=true"))
        # nothing is hidden in the shipped HTML: the removal only happens on a
        # click, so the page a crawler sees is still the whole collection
        self.assertNotIn('<article class="gproduct" hidden', self.html)
        self.assertNotIn("is-muted", self.css)

    def test_assets_are_cache_versioned_on_the_creator_page(self):
        """Pages caches /assets/* for 10 minutes, so the script URL is versioned.

        app.js is what moves the apparel tiles and the filter chips. Shipping
        new markup with an unversioned script URL hands a returning visitor the
        previous build's JavaScript - the buttons render and do nothing.
        """
        self.assertRegex(self.html, r'app\.js\?v=[0-9a-f]{8}"')
        self.assertRegex(self.html, r'style\.css\?v=[0-9a-f]{8}"')

    def test_faq_schema_answers_the_discount_and_the_disclaimer(self):
        faq = next(node for node in json_ld_nodes(self.html)
                   if node.get("@type") == "FAQPage")
        blob = json.dumps(faq)
        self.assertIn("CRYSTAL", blob)
        self.assertIn("10% off", blob)
        self.assertIn("Cleveland Browns", blob)
        self.assertNotIn("Michigan", blob)
        collection = next(node for node in json_ld_nodes(self.html)
                          if node.get("@type") == "CollectionPage")
        self.assertEqual(collection["about"]["numberOfItems"],
                         len(self.build.creator_items(self.cre)))

    def test_anchors_resolve_and_no_empty_apparel_section_ships(self):
        nav = re.search(r'<nav class="bellanav".*?</nav>', self.html, re.S)
        self.assertIsNotNone(nav)
        for link in (f'href="{self.prefix}"', 'href="#locker"', 'href="#about"'):
            self.assertIn(link, nav.group(0))
        # "Custom Design" jumps straight to the inquiry form instead of making
        # the visitor scroll the whole grid to find it
        self.assertIn('href="#custom-form">Custom Design</a>', nav.group(0))
        form = between(self.html, 'id="custom-form"', "</form>")
        self.assertIn('id="customForm"', form)
        self.assertIn('name="idea"', form)
        self.assertIn(".jlock-girly #custom-form{scroll-margin-top:96px}", self.css)
        self.assertLess(self.html.index('class="bellanav"'),
                        self.html.index('<main id="main" class="jlock jlock-girly"'))
        ids = re.findall(r'id="([^"]+)"', self.html)
        self.assertEqual(len(ids), len(set(ids)))
        for anchor in re.findall(r'href="#([^"]+)"', self.html):
            self.assertIn(anchor, ids, f"missing anchor target #{anchor}")
        # A locally curated locker DOES have a garment matrix now - the same
        # Mayzing category capture the Browns collection page swaps to - so the
        # tile row, the payload and the #apparel nav entry must all be present.
        self.assertIn("gcategory-tiles", self.html)
        self.assertIn("data-apparel=", self.html)
        self.assertIn('href="#apparel"', self.html)
        self.assertLess(self.html.index('id="apparel"'),
                        self.html.index('id="locker"'))

    def test_apparel_filter_buttons_swap_every_design_to_real_listings(self):
        """Crystal's locker carries the same garment filter as the collection.

        The tiles come from data/mayzing_apparel.json - the Mayzing category
        pages, which are the only authority on which garments a design is
        actually sold in. Every tile, chip and payload entry therefore points at
        a real listing with that listing's own mockup, checkout URL and price
        (tee $23, hoodie $40, sweatshirt $36, tank $23, crop $24); nothing is
        invented and no design loses its card.
        """
        from urllib.parse import parse_qs, urlsplit

        matrix = self.build.apparel_matrix(self.build.creator_items(self.cre),
                                           prefix=self.prefix)
        self.assertTrue(matrix)
        payload = json.loads(unescape(
            re.search(r'data-apparel="([^"]*)"', self.html).group(1)))
        self.assertEqual(set(payload), set(matrix))
        # every design in the locker is reachable through the filter
        cards = re.findall(r'<article class="gproduct" data-slug="([^"]+)" '
                           r'data-creator="CRYSTAL"(?: data-gcat="([^"]*)")?', self.html)
        self.assertEqual(len(cards), len(self.build.creator_items(self.cre)))
        cat_label = {"t-shirts": "T-Shirts", "hoodies": "Hoodies",
                     "sweatshirts": "Sweatshirts", "tank-tops": "Tank Tops",
                     "crop-tops": "Crop Tops"}
        tiles = re.findall(r'<button class="gcategory-tile"[^>]*data-gcat="([^"]+)"'
                           r'[^>]*data-gstyle="([^"]*)"[^>]*>.*?<span>([^<]+)</span>',
                           self.html, re.S)
        self.assertEqual([t[0] for t in tiles],
                         ["t-shirts", "hoodies", "sweatshirts", "tank-tops",
                          "crop-tops"])
        self.assertEqual([t[2] for t in tiles], [cat_label[t[0]] for t in tiles])
        for cat, style, _label in tiles:
            style = unescape(style)          # the attribute is HTML-escaped once
            garments = {row["garment"] for groups in matrix.values()
                        for row in groups.get(cat, [])}
            self.assertTrue(garments, cat)
            # This locker filters by garment CLASS, so the tile carries the
            # category's own label - the exact styles live on the chips below.
            self.assertEqual(style, cat_label[cat])
        # the tile row matches by garment CLASS on this locker (two tee styles)
        self.assertIn('data-apparel-loose="1"', self.html)
        # the second row of chips exposes the individual styles
        chips = re.findall(r'<button class="gstyle-chip"[^>]*data-gcat="([^"]+)"'
                           r'[^>]*data-gstyle="([^"]*)"', self.html)
        self.assertTrue(chips)
        for cat, style in chips:
            self.assertIn(unescape(style),
                          {r["garment"] for rows in matrix.values()
                           for r in rows.get(cat, [])})
        # payload entries: real mockups, real prices, creator attribution
        for slug, groups in payload.items():
            self.assertTrue(groups, slug)
            for cat, rows in groups.items():
                for row in rows:
                    self.assertTrue(row["image"].startswith("https://")
                                    or row["image"].startswith(self.prefix), row)
                    self.assertTrue(row["price"].startswith("$"), row)
                    self.assertNotEqual(row["image"], row["back"], row)
                    query = parse_qs(urlsplit(row["url"]).query)
                    self.assertEqual(query.get("creator"), ["CRYSTAL"], row["url"])
        self.assertIn("$40.00", self.html)   # a hoodie keeps its own price
        self.assertIn("$23.00", self.html)

    def test_a_filter_leaves_exactly_the_designs_that_list_it(self):
        """The chip numbers are the cards that stay on screen.

        A filter may only ever show designs the store actually lists in that
        style: the rest are removed from the grid (never greyed out, and never
        pulled back in from another cut). The counts printed on the chips are
        therefore the visible card count, and a chip is exact while a tile
        filters by garment class.
        """
        matrix = self.build.apparel_matrix(self.build.creator_items(self.cre),
                                           prefix=self.prefix)
        payload = json.loads(unescape(
            re.search(r'data-apparel="([^"]*)"', self.html).group(1)))
        chip_rows = re.findall(
            r'<button class="gstyle-chip"[^>]*data-gcat="([^"]+)"[^>]*'
            r'data-gstyle="([^"]*)"[^>]*>.*?'
            r'<span class="gstyle-count"[^>]*>(\d+)<',
            self.html, re.S)
        counts = {(cat, unescape(style)): int(n) for cat, style, n in chip_rows}
        self.assertTrue(counts)
        for (cat, style), printed in counts.items():
            listed = sum(1 for groups in payload.values()
                         if any(row["garment"] == style
                                for rows in groups.values() for row in rows))
            self.assertEqual(printed, listed, style)
            # the chip only ever offers a style the category really lists
            self.assertIn(style, {row["garment"] for rows in matrix.values()
                                  for row in rows.get(cat, [])})
        # a tile is a garment class, so its coverage is the designs listing it
        for cat in {c for c, _ in counts}:
            listed = sum(1 for groups in payload.values() if groups.get(cat))
            self.assertGreater(listed, 0, cat)
        # and the block implements both rules: exact chips, class-wide tiles
        js = page("assets/app.js")
        block = js[js.index("// ---------- creator apparel-style buttons"):]
        self.assertIn("if(!entry&&cat&&loose&&!exact)", block)
        self.assertIn("false);", block)   # a tile click
        self.assertIn(",true);", block)   # a chip click

    def test_local_asset_references_resolve(self):
        from urllib.parse import unquote

        fp = os.path.join(SITE, "crystal/index.html")
        attr = re.compile(r'(?:src|data-src|href|content)="([^"]+)"')
        for match in attr.finditer(self.html):
            value = unescape(match.group(1).strip())
            if not (value.startswith("/") or value.startswith("./")
                    or value.startswith("../")):
                continue
            value = unquote(value.split("#")[0].split("?")[0])
            if value in ("", "/", "./"):
                continue
            target = (os.path.join(SITE, value.lstrip("/")) if value.startswith("/")
                      else os.path.join(os.path.dirname(fp), value))
            target = os.path.normpath(target)
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            self.assertTrue(os.path.isfile(target), f"{fp}: {value}")


class AmberLocker(unittest.TestCase):
    """Amber's Browns collection - the second locker on the Browns catalogue.

    Same contract as Crystal Marie's: the girly layout, the browns skin, the
    whole live Browns collection in the collection page's own order (newest ->
    oldest), every card on the local product page with ``?creator=AMBER``.

    Two lockers over ONE collection is exactly where a copy-paste would leak:
    one page's promo code, hero photo or attribution could end up on the
    other. These tests pin Amber's own code, artwork and attribution, and pin
    the shared parts (the skin, the collection page's cross-links) as shared.
    """

    def setUp(self):
        import build  # noqa: E402

        self.build = build
        self.html = page("amber/index.html")
        self.cre = load_json("data/creators.json")["creators"]["amber"]
        self.prefix = "../" * max(1, len([part for part
                                          in self.cre["page_slug"].split("/") if part]))
        self.css = page("assets/style.css")
        self.team = page("cleveland-browns-shirts/index.html")

    def test_page_is_indexable_sitemapped_and_closes_with_app_js(self):
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/amber/">',
                      self.html)
        self.assertIn("<loc>https://gridironlocker.store/amber/</loc>",
                      page("sitemap.xml"))
        self.assertIn('data-creator-page="AMBER"', self.html)
        self.assertNotIn('name="robots" content="noindex', self.html)
        self.assertTrue(self.html.endswith("</body></html>"))
        loads = re.findall(r'<script src="[^"]*assets/app\.js(?:\?v=[0-9a-f]{8})?"[^>]*></script>',
                           self.html)
        self.assertEqual(len(loads), 1)
        self.assertIn("defer", loads[0])

    def test_the_grid_is_the_whole_browns_collection_in_catalogue_order(self):
        """"Same as Crystal's one" includes the order: newest -> oldest."""
        self.assertEqual(self.cre.get("order"), "newest")
        self.assertTrue(self.cre.get("include_collection"))
        live = self.build.creator_items(self.cre)
        self.assertEqual([item["slug"] for item in live],
                         [item["slug"] for item in self.build.MODEL["cleveland-browns"]])
        cards = re.findall(r'<article class="gproduct" data-slug="([^"]+)"', self.html)
        self.assertEqual(cards, [item["slug"] for item in live])
        team_cards = re.findall(r'class="card[^"]*"[^>]*data-slug="([^"]+)"', self.team)
        self.assertEqual(cards, team_cards)
        self.assertEqual(cards[0], "cleveland-victory-monday")
        self.assertEqual(cards[-1], "ohio-cle")
        self.assertIn(f'<p class="goverline">ALL {len(cards)} BROWNS DESIGNS</p>',
                      unescape(self.html))
        self.assertEqual(cards.count("dawg-pound-cleveland-skyline"), 0)

    def test_every_card_forwards_amber_attribution(self):
        self.assertEqual(self.cre["attribution"]["creator_id"], "AMBER")
        cards = re.findall(r'<article class="gproduct".*?</article>', self.html, re.S)
        self.assertEqual(len(cards), 33)
        for block in cards:
            self.assertIn("?creator=AMBER", block, block[:90])
            self.assertIn('data-creator="AMBER"', block)
            self.assertNotIn("creator=CRYSTAL", block)

    def test_amber_code_is_ten_percent_off_in_all_three_placements(self):
        self.assertEqual(self.cre.get("promo"), {"code": "AMBER", "pct": 10})
        bar = self.html[self.html.find('class="gpromobar"'):]
        bar = bar[:bar.find("</div>", bar.find("</div>") + 1)]
        self.assertIn("<strong>10% off</strong> your order", bar)
        self.assertIn("Use code", bar)
        self.assertIn('data-copy-code="AMBER"', bar)
        self.assertIn('aria-label="Copy promo code AMBER"', bar)
        self.assertIn('class="gpromobar-code-value">AMBER', bar)
        self.assertIn('<span>10% off</span> with code <strong>AMBER</strong>',
                      self.html)                                     # pill above the grid
        self.assertIn("with code <strong>AMBER</strong> at checkout", self.html)
        self.assertNotIn("CRYSTAL", self.html)
        self.assertNotIn("Crystal", unescape(self.html))

    def test_hero_and_copy_are_ambers_not_crystals(self):
        self.assertEqual(self.cre["hero"], "/img/hero-amber.jpg")
        hero_v = self.cre["girly"]["hero_v"]
        self.assertIn(f'src="{self.prefix}img/hero-amber.jpg?v={hero_v}"', self.html)
        self.assertNotIn("hero-crystal", self.html)
        self.assertTrue(os.path.isfile(os.path.join(SITE, "img/hero-amber.jpg")))
        text = unescape(self.html)
        self.assertIn('<span class="gscript">Amber’s</span>', text)
        self.assertIn("Amber’s Browns Collection", text)
        self.assertIn('aria-label="Amber’s Collection home"', text)
        self.assertIn("AMBER’S PICK 01", text)
        self.assertIn("AMBER’S PICK 33", text)
        self.assertIn("use code amber", text.lower())
        # her own custom-design inquiry, not a copy of Crystal's subject line
        self.assertIn('id="custom-form"', self.html)
        self.assertIn("New Custom Design Request from Amber's Browns Locker", text)

    def test_browns_skin_is_shared_not_copied(self):
        """One palette block serves both lockers: the skin is keyed by name."""
        self.assertEqual(self.cre.get("skin"), "browns")
        self.assertIn('data-creator-skin="browns"', self.html)
        self.assertIn('data-creator-skin="browns"', page("crystal/index.html"))
        self.assertIn('data-theme="browns"', self.html)
        self.assertEqual(self.css.count('body[data-creator-skin="browns"]{background:#f4ead9'), 1)
        self.assertNotIn('body[data-creator-page="AMBER"]', self.css)
        self.assertNotIn('body[data-creator-page="CRYSTAL"]', self.css)
        # and the disclaimer names the Browns/NFL, never Michigan
        self.assertIn("Cleveland Browns, the NFL or any player", unescape(self.html))
        self.assertNotIn("Michigan", unescape(self.html))

    def test_the_collection_page_and_navigation_link_both_lockers(self):
        """A Browns collection with two capsules must not hide one of them."""
        for href in ('href="../crystal/"', 'href="../amber/"'):
            self.assertIn(href, self.team)
            self.assertIn(href, page("collections/index.html"))
        self.assertIn("Crystal Marie", self.team)
        self.assertIn("Amber", self.team)
        llms = page("llms.txt")
        self.assertIn("https://gridironlocker.store/amber/", llms)
        self.assertIn("https://gridironlocker.store/amber/", page("feed.xml"))


class LaqualaRoyalLocker(unittest.TestCase):
    """Laquala Royal's Browns locker at /laquala/ - Crystal Marie's page again.

    Third locker over the same collection, so the risk is no longer a copy-paste
    mistake between two pages but a *generalisation* mistake: a shared helper
    that quietly assumes two creators, or one creator's name, code or attribution
    bleeding into the newest page. These tests pin her own address, code, artwork
    and attribution, and keep the shared grid honest.
    """

    def setUp(self):
        import build  # noqa: E402

        self.build = build
        self.html = page("laquala/index.html")
        self.cre = load_json("data/creators.json")["creators"]["laquala"]
        self.prefix = "../" * max(1, len([part for part
                                          in self.cre["page_slug"].split("/") if part]))
        self.team = page("cleveland-browns-shirts/index.html")

    def test_she_lives_at_the_bare_short_url(self):
        self.assertEqual(self.cre["page_slug"], "laquala")
        self.assertFalse(self.cre.get("page_slug_moved_from"))
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/laquala/">',
                      self.html)
        self.assertIn("<loc>https://gridironlocker.store/laquala/</loc>",
                      page("sitemap.xml"))
        self.assertIn('data-creator-page="LAQUALA"', self.html)
        self.assertNotIn('name="robots" content="noindex', self.html)
        self.assertTrue(self.html.endswith("</body></html>"))

    def test_the_grid_is_the_whole_browns_collection_newest_first(self):
        live = [item["slug"] for item in self.build.creator_items(self.cre)]
        self.assertEqual(live, [item["slug"] for item in self.build.MODEL["cleveland-browns"]])
        cards = re.findall(r'<article class="gproduct" data-slug="([^"]+)"', self.html)
        self.assertEqual(cards, live)
        self.assertEqual(cards, re.findall(r'class="card[^"]*"[^>]*data-slug="([^"]+)"',
                                           self.team))
        self.assertEqual(len(cards), 33)
        self.assertIn('<p class="goverline">ALL 33 BROWNS DESIGNS</p>', unescape(self.html))
        self.assertIn("LAQUALA’S PICK 01", unescape(self.html))
        self.assertIn("LAQUALA’S PICK 33", unescape(self.html))

    def test_every_card_forwards_her_own_attribution(self):
        self.assertEqual(self.cre["attribution"]["creator_id"], "LAQUALA")
        cards = re.findall(r'<article class="gproduct".*?</article>', self.html, re.S)
        self.assertEqual(len(cards), 33)
        for block in cards:
            self.assertIn("?creator=LAQUALA", block, block[:90])
            self.assertIn('data-creator="LAQUALA"', block)

    def test_laquala_code_is_ten_percent_off_and_no_other_creator_leaks(self):
        self.assertEqual(self.cre.get("promo"), {"code": "LAQUALA", "pct": 10})
        self.assertIn('data-copy-code="LAQUALA"', self.html)          # promo bar
        self.assertIn('<span>10% off</span> with code <strong>LAQUALA</strong>', self.html)
        self.assertIn("with code <strong>LAQUALA</strong> at checkout", self.html)
        text = unescape(self.html)
        for other in ("Crystal", "Amber", "Bella", "Joe"):
            self.assertNotIn(other, text)
        self.assertNotIn("creator=CRYSTAL", self.html)
        self.assertNotIn("creator=AMBER", self.html)

    def test_hero_and_copy_are_hers(self):
        self.assertEqual(self.cre["hero"], "/img/hero-laquala.jpg")
        hero_v = self.cre["girly"]["hero_v"]
        self.assertIn(f'src="{self.prefix}img/hero-laquala.jpg?v={hero_v}"', self.html)
        self.assertNotIn("hero-crystal", self.html)
        self.assertNotIn("hero-amber", self.html)
        self.assertTrue(os.path.isfile(os.path.join(SITE, "img/hero-laquala.jpg")))
        text = unescape(self.html)
        # the collection is branded with her full name in the hero and the
        # masthead, while the address stays the short /laquala/
        self.assertIn('<span class="gscript">Laquala Royal’s</span>', text)
        self.assertIn('<span class="gtitle">Collection</span>', text)
        self.assertIn("Laquala Royal’s Browns Collection", text)
        self.assertIn('aria-label="Laquala Royal’s Collection home"', text)
        self.assertIn('aria-label="Laquala Royal’s Collection"', text)
        self.assertEqual(self.cre["page_slug"], "laquala")
        self.assertIn("New Custom Design Request from Laquala Royal's Browns Locker", text)
        # shared browns skin, not a third palette block
        self.assertEqual(self.cre.get("skin"), "browns")
        self.assertIn('data-creator-skin="browns"', self.html)
        self.assertEqual(page("assets/style.css").count(
            'body[data-creator-skin="browns"]{background:#f4ead9'), 1)

    def test_a_long_name_keeps_the_address_and_the_other_lockers_untouched(self):
        """Full-name branding is a label, not a route: /laquala/ must not move.

        The nav bar label defaults to the first name; her record overrides it so
        a screen reader hears the name she brands under, and the override must
        not leak onto the other lockers.
        """
        self.assertIn("<loc>https://gridironlocker.store/laquala/</loc>",
                      page("sitemap.xml"))
        self.assertNotIn("laquala-royal", page("sitemap.xml"))
        self.assertIn('aria-label="Amber’s Collection"', page("amber/index.html"))
        self.assertIn('aria-label="Crystal’s Collection"',
                      page("crystal/index.html"))
        self.assertIn('aria-label="Bella’s Collection"',
                      page("michigan/bella/index.html"))

    def test_three_browns_capsules_are_all_linked(self):
        for href in ('href="../crystal/"', 'href="../amber/"', 'href="../laquala/"'):
            self.assertIn(href, self.team)
            self.assertIn(href, page("collections/index.html"))
        self.assertIn("Laquala Royal", self.team)
        self.assertIn("https://gridironlocker.store/laquala/", page("llms.txt"))
        self.assertIn("https://gridironlocker.store/laquala/", page("feed.xml"))


class DesLocker(unittest.TestCase):
    """des❤️🐞's Browns locker at /des/ - Crystal Marie's page with emoji branding.

    The brand is an emoji handle ("des❤️🐞") while the address is the plain
    ASCII "des". That split is the thing worth pinning: the emoji lives in the
    copy, the title and the labels, and never in a path, a query string or a
    canonical - a percent-encoded emoji URL is share-hostile and would fork the
    page's identity the first time someone copied it out of a browser bar.
    """

    BRAND = "des\u2764\ufe0f\U0001f41e"

    def setUp(self):
        import build  # noqa: E402

        self.build = build
        self.html = page("des/index.html")
        self.cre = load_json("data/creators.json")["creators"]["des"]
        self.team = page("cleveland-browns-shirts/index.html")

    def test_the_address_is_plain_ascii_des(self):
        self.assertEqual(self.cre["page_slug"], "des")
        self.assertTrue(self.cre["page_slug"].isascii())
        self.assertIn('<link rel="canonical" href="https://gridironlocker.store/des/">',
                      self.html)
        self.assertIn("<loc>https://gridironlocker.store/des/</loc>", page("sitemap.xml"))
        self.assertTrue(os.path.isdir(os.path.join(SITE, "des")))
        # the brand never leaks into a path or a query string
        for bad in ("%EF%B8%8F", "%F0%9F%90%9E", "/des❤", "creator=DES❤"):
            self.assertNotIn(bad, self.html)
            self.assertNotIn(bad, page("sitemap.xml"))

    def test_the_grid_is_the_whole_browns_collection_newest_first(self):
        live = [item["slug"] for item in self.build.creator_items(self.cre)]
        self.assertEqual(live, [item["slug"] for item in self.build.MODEL["cleveland-browns"]])
        cards = re.findall(r'<article class="gproduct" data-slug="([^"]+)"', self.html)
        self.assertEqual(cards, live)
        self.assertEqual(cards, re.findall(r'class="card[^"]*"[^>]*data-slug="([^"]+)"',
                                           self.team))
        self.assertEqual(len(cards), 33)
        self.assertNotIn("dawg-pound-cleveland-skyline", cards)

    def test_every_card_forwards_the_destiny_attribution(self):
        self.assertEqual(self.cre["attribution"]["creator_id"], "DESTINY")
        cards = re.findall(r'<article class="gproduct".*?</article>', self.html, re.S)
        self.assertEqual(len(cards), 33)
        for block in cards:
            self.assertIn("?creator=DESTINY", block, block[:90])
            self.assertIn('data-creator="DESTINY"', block)

    def test_destiny_code_is_ten_percent_off_and_nothing_else_leaks(self):
        self.assertEqual(self.cre.get("promo"), {"code": "DESTINY", "pct": 10})
        self.assertIn('data-copy-code="DESTINY"', self.html)
        self.assertIn("<strong>10% off</strong> your order", self.html)
        self.assertIn('<span>10% off</span> with code <strong>DESTINY</strong>', self.html)
        self.assertIn("with code <strong>DESTINY</strong> at checkout", self.html)
        text = unescape(self.html)
        for other in ("Crystal", "Amber", "Laquala", "Bella", "Joe"):
            self.assertNotIn(other, text)
        for other in ("CRYSTAL", "AMBER", "LAQUALA"):
            self.assertNotIn(f"creator={other}", self.html)

    def test_the_emoji_brand_ships_in_the_copy_and_the_labels(self):
        self.assertEqual(self.cre["display_name"], "Destiny Elizabeth")
        text = unescape(self.html)
        self.assertIn(f'<span class="gscript">Des{self.BRAND[3:]}</span>', text)
        self.assertIn(f"Des{self.BRAND[3:]} Collection home", text)
        self.assertIn(f"Des{self.BRAND[3:]} Collection", text)
        self.assertIn(f"{self.BRAND.upper()} PICK 01", text)
        self.assertIn(f"{self.BRAND.upper()} PICK 33", text)
        self.assertIn(f"{self.BRAND} Browns Collection", text)
        self.assertIn("Destiny Elizabeth", text)
        self.assertIn("New Custom Design Request from " + self.BRAND, text)

    def test_hero_is_her_own_artwork(self):
        self.assertEqual(self.cre["hero"], "/img/hero-des.jpg")
        self.assertIn('src="../img/hero-des.jpg?v=1"', self.html)
        for other in ("hero-crystal", "hero-amber", "hero-laquala"):
            self.assertNotIn(other, self.html)
        self.assertTrue(os.path.isfile(os.path.join(SITE, "img/hero-des.jpg")))
        self.assertIn('data-creator-skin="browns"', self.html)

    def test_all_four_browns_capsules_are_linked(self):
        for href in ('href="../crystal/"', 'href="../amber/"',
                     'href="../laquala/"', 'href="../des/"'):
            self.assertIn(href, self.team)
            self.assertIn(href, page("collections/index.html"))
        self.assertIn("https://gridironlocker.store/des/", page("llms.txt"))
        self.assertIn("https://gridironlocker.store/des/", page("feed.xml"))


class ConversionUpgrades(unittest.TestCase):
    """The conversion pass: truthful trust strip, faster PDP hand-off,
    visible custom-design service, completed funnel analytics.

    Each test pins an improvement made without touching artwork, prices,
    URLs, fulfilment links or the pinned layout skeleton.
    """

    @classmethod
    def setUpClass(cls):
        cls.home = page("index.html")
        cls.css = page("assets/style.css")
        cls.js = page("assets/app.js")
        shop = os.path.join(SITE, "shop")
        cls.pages = {d: read(os.path.join(shop, d, "index.html"))
                     for d in sorted(os.listdir(shop))
                     if os.path.isfile(os.path.join(shop, d, "index.html"))
                     and "data-gl-redirect" not in
                     read(os.path.join(shop, d, "index.html"))}

    def test_trust_strip_is_truthful(self):
        # No unsupported "premium" superlative and no hard-coded size run
        # (the catalogue sells S-5XL; the strip used to say S-3XL).
        sec = between(self.home, 'class="trust"', "</div>\n</div>")
        for cell in ("Fan-Made Designs", "Made To Order",
                     "Worldwide Shipping", "Secure Checkout"):
            self.assertIn(cell, sec, cell)
        self.assertNotIn("Premium", sec)
        self.assertNotIn("3XL", sec)

    def test_pdp_cta_follows_price(self):
        # The hero Shop Now sits directly under the price row - above the
        # facts grid - with a one-line ordering note naming the partner.
        for slug, html in self.pages.items():
            hero = html.index('data-placement="hero"')
            self.assertLess(hero, html.index('class="atglance"'), slug)
            note = re.search(r'<p class="handoff-note">(.*?)</p>', html, re.S)
            self.assertIsNotNone(note, slug)
            self.assertIn("Checkout happens on", note.group(1), slug)
            # still exactly one canonical .ctanote (mid-page); the hero note
            # is a distinct, shorter line, not a duplicate
            self.assertEqual(html.count('class="ctanote'), 1, slug)

    def test_pdp_custom_band_is_a_link_not_a_checkout(self):
        # A custom-design cross-sell above the related rail: plain link, no
        # .shopnow class, no form/select (still banned on PDPs).
        for slug, html in self.pages.items():
            band = between(html, 'class="customband"', 'id="related"')
            self.assertIn("Want It With Your Name On It?", band, slug)
            self.assertIn("You dream it. We design it.", band, slug)
            m = re.search(r'<a class="link custom-link" data-placement="([^"]+)" '
                          r'href="([^"]*#custom-design)"', band)
            self.assertIsNotNone(m, slug)
            self.assertNotIn("shopnow", band, slug)

    def test_custom_section_states_the_proposition(self):
        sec = between(self.home,
                      '<section class="customsec" id="custom-design">',
                      "</section>")
        self.assertIn("You dream it. We design it.", sec)
        # pass 2: the proposition is now the 3-step flow (idea -> design ->
        # shirt) instead of four chips; the lead still tells the visitor
        # exactly what to send (team, colors, phrase or concept)
        for step in ("<b>01</b><span>Your idea</span>",
                     "<b>02</b><span>Our design</span>",
                     "<b>03</b><span>Your shirt</span>"):
            self.assertIn(step, sec, step)
        self.assertIn("the team, the colors and the", sec)
        self.assertIn("phrase or concept", sec)
        # the idea field is the star of the form: a textarea, required,
        # sitting above the team/garment logistics
        idea = sec.index('name="idea"')
        team = sec.index('name="team"')
        self.assertLess(idea, team, "idea must come before the logistics")
        self.assertIn("required", sec[idea - 200:idea + 200])
        # the inquiry framing + every pinned field still on the form
        self.assertIn('name="colors"', sec)
        self.assertIn("A free inquiry, not an order", sec)
        for field in ('name="name"', 'name="email"', 'name="team"',
                      'name="garment"', 'name="idea"', 'name="details"'):
            self.assertIn(field, sec, field)

    def test_custom_design_is_in_site_navigation(self):
        nav = between(self.home, '<nav class="menubar"', "</nav>")
        self.assertIn("Custom Design", nav)
        self.assertIn("#custom-design", nav)

    def test_collection_pages_carry_a_custom_band(self):
        for k, html in collection_pages().items():
            band = between(html, 'class="customband"', "In The 2026 Season")
            self.assertIn("Your Team. Your Colors. Your Phrase.", band, k)
            self.assertIn(COLLECTIONS[k]["short"], band, k)
            self.assertIn("#custom-design", band, k)

    def test_social_and_font_hints_in_head(self):
        self.assertIn('<meta name="twitter:site" content="@gridironlocker">',
                      self.home)
        self.assertIn('<link rel="preconnect" '
                      'href="https://fonts.googleapis.com">', self.home)
        self.assertIn('<link rel="preconnect" '
                      'href="https://fonts.gstatic.com" crossorigin>',
                      self.home)

    def test_funnel_analytics_completed(self):
        for event in ("custom_cta_click", "custom_design_submit",
                      "newsletter_signup"):
            self.assertIn(event, self.js, event)
        # no lead PII in the analytics payload: team/garment dimensions only
        submit = between(self.js, "custom_design_submit", "});")
        self.assertNotIn("name+", submit)
        self.assertNotIn("email+", submit)

    def test_new_styles_shipped(self):
        for sel in (".handoff-note{", ".customband{", ".customband-in{",
                    ".cf-dream{",
                    # conversion pass 2: value line, 3-step flow, positioning
                    # line, why-strip label and the dark final shop CTA
                    ".value{", ".cf-flow{", ".cbanner .posline{",
                    ".trust-label{", ".finalcta{"):
            self.assertIn(sel, self.css, sel)
        # phones swipe thumbnails instead of stacking them over the buybox
        mob = media_rules(self.css, 920)
        self.assertIn(".thumbs{display:flex;overflow-x:auto", mob)

    def test_collection_logos_are_light(self):
        # The collection crests are generated SVG lockups (original fan-made
        # badges) instead of the official team marks that used to ship as
        # 96px webp portraits - the Michigan one was 890KB at 1018px.
        for f in ("michigan.svg", "dallas.svg", "browns.svg", "green-bay.svg"):
            path = os.path.join(IMG, "lockups", f)
            self.assertTrue(os.path.exists(path), path)
            self.assertLess(os.path.getsize(path), 8 * 1024, f)
            with open(path, encoding="utf-8") as fh:
                svg = fh.read()
            self.assertIn("FAN MADE", svg, f)
        # and the official-mark files must not come back
        for f in ("michigan-logo1.webp", "dallas-logo1.webp",
                  "browns-logo1.webp", "green-bay-logo1.webp"):
            self.assertFalse(os.path.exists(os.path.join(IMG, f)), f)


class AuditFixes20260918(unittest.TestCase):
    """Regression coverage for the 2026-09-18 site audit
    (SITE-AUDIT-2026-09-18.md). Each test pins one fixed defect so it cannot
    silently come back on the next rebuild."""

    # ---------------------------------------------------- F1 season prose
    def test_season_prose_matches_the_data(self):
        """Every week/result line on the homepage must come from SEASON -
        no hand-written date or opponent may disagree with the data."""
        import collections_data as cd
        home = page("index.html")
        cards = [unescape(c).replace("&middot;", "\u00b7")
                 for c in re.findall(r'wk-game">([^<]+)</span>', home)]
        self.assertTrue(cards, "homepage has no week/result cards")
        openers = {unescape(v["opener"]).replace("&middot;", "\u00b7")
                   for v in cd.SEASON.values() if v.get("opener")}
        for c in cards:
            self.assertIn(c, openers, f"card {c!r} is not a SEASON opener string")
            for d in re.findall(r"Sept (\d+)", c):
                team = next(k for k, v in cd.SEASON.items()
                            if unescape(v.get("opener", "")).replace("&middot;", "\u00b7") == c)
                kick = cd.SEASON[team]["kickoff"]
                self.assertEqual(int(d), int(kick[8:10]),
                                 f"{team}: card says Sept {d}, kickoff is {kick}")
        # exactly one Michigan line, and it is the Oklahoma game (not an NFL one)
        mich = [c for c in cards if "Oklahoma" in c]
        self.assertEqual(len(mich), 1, mich)
        self.assertEqual(len(cards), len(cd.SEASON), cards)

    def test_recap_sentences_are_grammatical(self):
        for rel in ("index.html", "guides/index.html",
                    "guides/2026-week-1-shirts/index.html"):
            txt = unescape(re.sub(r"<[^>]+>", " ", page(rel)))
            self.assertNotRegex(txt, r"\bno\. \d+ [a-z]", rel)
            self.assertNotRegex(txt, r"\bSept \d+, \d{4}\b.*\bWeek 1\b.*\bSept 13\b.*\bSept 12\b",
                                rel)

    # ------------------------------------------------------ F2/F3 privacy
    def test_analytics_is_consent_gated(self):
        js = page("assets/app.js")
        home = page("index.html")
        self.assertIn("googletagmanager", home + js)
        self.assertIn("gl_analytics", js)
        self.assertIn("Allow analytics", js)
        # the tag itself may only be injected after consent - never by a
        # static <script src> in the head
        self.assertNotRegex(
            home, r'<script[^>]+src="https://www\.googletagmanager\.com/gtag/js')
        self.assertIn("window.glLoadAnalytics", home)
        self.assertIn("gl_analytics=1", home)
        priv = page("privacy/index.html")
        for tool in ("Google Analytics 4", "FormSubmit", "Google Fonts", "Mayzing"):
            self.assertIn(tool, priv, tool)
        self.assertIn("opt-in", priv)
        self.assertIn("gl_analytics", priv)
        self.assertIn("mailto:", page("contact/index.html"))

    # ------------------------------------------------------------ F4 forms
    def test_forms_post_to_a_real_endpoint(self):
        home = page("index.html")
        js = page("assets/app.js")
        self.assertIn('action="https://formsubmit.co/', home)
        self.assertNotIn("novalidate", home)
        self.assertIn("formsubmit.co/ajax/", js)
        self.assertNotRegex(js, r"mode:\s*['\"]no-cors['\"]")
        self.assertNotRegex(js, r"setTimeout\(function\(\)\{if\(!\w+\)\{\}\}")

    # ------------------------------------------------------------ F5 feeds
    def test_feed_is_valid_rss(self):
        from email.utils import parsedate_to_datetime
        x = page("feed.xml")
        items = re.findall(r"<item>(.*?)</item>", x, re.S)
        self.assertTrue(items)
        for it in items:
            self.assertIn("<pubDate>", it)
            self.assertIn("<guid", it)
            d = re.search(r"<pubDate>([^<]+)</pubDate>", it).group(1)
            parsedate_to_datetime(d)          # raises if not RFC-822
            self.assertNotRegex(re.search(r"<guid[^>]*>([^<]+)</guid>", it).group(1),
                                r"#\d{4}-\d{2}-\d{2}$")
        lbd = re.search(r"<lastBuildDate>([^<]+)</lastBuildDate>", x).group(1)
        parsedate_to_datetime(lbd)
        for slug in re.findall(r"<link>[^<]*/products/([^/<]+)</link>", x):
            self.assertTrue(os.path.isdir(os.path.join(SITE, "products", slug)), slug)

    # ------------------------------------------------- F6/F7 assets and IP
    def test_no_stray_verification_files(self):
        for dirpath, _dirs, files in os.walk(SITE):
            for f in files:
                if re.match(r"^(google|bing|a7f3c19b)[a-z0-9]*\.(html|txt|xml)$", f):
                    self.assertEqual(os.path.relpath(dirpath, SITE), ".",
                                     f"stray verification file in {dirpath}: {f}")

    def test_collections_use_generated_lockups(self):
        col = page("collections/index.html")
        self.assertEqual(col.count("/img/lockups/"), 4)
        for m in re.finditer(r'<img src="/img/lockups/([^"]+)" alt="([^"]+)"', col):
            self.assertTrue(os.path.exists(os.path.join(IMG, "lockups", m.group(1))))
            self.assertIn("original fan-made badge", m.group(2))
            self.assertRegex(m.group(2), r"est \d{4}")

    # ------------------------------------------------------------- F8 alts
    def test_no_alt_repeats_a_crawl_typo_of_the_name(self):
        """Where the partner's artwork line is a crawl-mangled version of the
        curated name ("Beware Of Dawg" / "BE AWAR OF DAWG"), no page may print
        the pair - on the homepage, the team pages, /collections/ or /search/."""
        import build
        offenders = []
        for it in build.ALL:
            art = it.get("art") or ""
            if not build._l.typo_variant(it["name"], art):
                continue
            pair = f'alt="{it["name"]} - {art[:70]}"'
            for dirpath, _dirs, files in os.walk(SITE):
                for f in files:
                    if f.endswith(".html") and pair in page(
                            os.path.relpath(os.path.join(dirpath, f), SITE)):
                        offenders.append((it["slug"], os.path.relpath(dirpath, SITE)))
        self.assertEqual(offenders, [], offenders[:5])

    def test_eager_card_images_are_hinted(self):
        """Every <img> is either lazy or priority-hinted (audit L9)."""
        unhinted = []
        for dirpath, _dirs, files in os.walk(SITE):
            for f in files:
                if not f.endswith(".html"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), SITE)
                for tag in re.findall(r"<img\b[^>]*>", page(rel), re.I):
                    if "loading=" not in tag and "fetchpriority" not in tag:
                        unhinted.append((rel, tag[:70]))
        self.assertEqual(unhinted, [], unhinted[:6])

    def test_alt_text_uses_the_curated_name(self):
        """Crawl-mangled design names (missing apostrophes, anagram-ish
        truncations) must never reach an alt attribute."""
        bad = []
        for dirpath, _dirs, files in os.walk(SITE):
            for f in files:
                if not f.endswith(".html"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), SITE)
                for alt in re.findall(r'alt="([^"]{3,120})"', page(rel)):
                    a = unescape(alt)
                    if re.search(r"\b\w S \w", a) or re.search(r"\bIts \w", a):
                        bad.append((rel, a))
        self.assertEqual(bad, [], bad[:5])

    # --------------------------------------------------------- F10 headings
    def test_no_heading_level_skips(self):
        skips = []
        for dirpath, _dirs, files in os.walk(SITE):
            for f in files:
                if not f.endswith(".html"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, f), SITE)
                if "/ops/" in "/" + rel or rel.startswith("marketing/"):
                    continue
                levels = [int(m) for m in re.findall(r"<h([1-6])[ >]", page(rel))]
                for a, b in zip(levels, levels[1:]):
                    if b - a > 1:
                        skips.append((rel, f"h{a}->h{b}"))
                        break
        self.assertEqual(skips, [], skips[:8])

    # ------------------------------------------------------------- F11 FTI
    def test_fti_only_promotes_current_people(self):
        import build
        rows = build.fti_rows(None)
        people = load_json("data/people.json")
        retired = {p["name"] for p in people.get("people", [])
                   if p.get("status") != "current"}
        self.assertTrue(retired)
        for r in rows:
            self.assertNotIn(r.get("name"), retired, r.get("name"))

    # --------------------------------------------- F13 published internals
    def test_no_source_files_are_published(self):
        leaked = []
        for sub in ("marketing", "ops"):
            base = os.path.join(SITE, sub)
            if not os.path.isdir(base):
                continue
            for dirpath, _dirs, files in os.walk(base):
                for f in files:
                    if f.lower().endswith((".py", ".sh", ".md", ".csv", ".txt")):
                        leaked.append(os.path.relpath(os.path.join(dirpath, f), SITE))
        self.assertEqual(leaked, [], leaked)
        # the dashboards still get the JSON they fetch
        self.assertTrue(os.path.exists(os.path.join(SITE, "ops", "scout", "scout.json")))

    # ----------------------------------------------------------- F14 drops
    def test_unshipped_drops_are_recorded(self):
        dd = load_json("data/drops-dropped.json")
        for key in ("generated", "queued", "eligible", "shown", "dropped"):
            self.assertIn(key, dd)
        self.assertEqual(dd["queued"], dd["eligible"] + len(dd["dropped"]), dd)
        self.assertEqual(dd["shown"], min(dd["eligible"], 12), dd)

    # --------------------------------------------------------- F15 gallery
    def test_product_galleries_have_no_duplicates(self):
        dupes, pads = [], []
        for dirpath, _dirs, files in os.walk(os.path.join(SITE, "products")):
            if "index.html" not in files:
                continue
            rel = os.path.relpath(os.path.join(dirpath, "index.html"), SITE)
            html = page(rel)
            thumbs = re.findall(r'class="thumb"[^>]*>\s*<img src="([^"]+)"', html)
            if len(thumbs) != len(set(thumbs)):
                dupes.append(rel)
            if len(set(thumbs)) <= 1 and thumbs:
                pads.append(rel)
        self.assertEqual(dupes, [], dupes[:5])
        self.assertEqual(pads, [], pads[:5])


class BacksideHoverEveryCard(unittest.TestCase):
    """Every product card across every public page - and every garment swap on
    team and creator pages - must reveal a distinct backside image on hover."""

    CARD_PATTERNS = (
        ("card", re.compile(r'<article class="card[^"]*"[^>]*>(.*?)</article>', re.S)),
        ("pcard", re.compile(r'<a class="pcard[^"]*"[^>]*>(.*?)</a>', re.S)),
        ("gproduct", re.compile(r'<article class="gproduct"[^>]*>(.*?)</article>', re.S)),
        ("jfeat", re.compile(r'<a class="jfeat"[^>]*>(.*?)</a>', re.S)),
        ("jcard", re.compile(r'<a class="jcard"[^>]*>(.*?)</a>', re.S)),
        ("drop-card", re.compile(r'<article class="drop-card[^"]*"[^>]*>(.*?)</article>', re.S)),
    )

    def test_every_public_product_card_has_distinct_backside_hover_image(self):
        counts = {k: 0 for k, _ in self.CARD_PATTERNS}
        for root, _, files in os.walk(SITE):
            rel_dir = os.path.relpath(root, SITE).replace(os.sep, "/")
            if rel_dir.startswith(("marketing", "ops")):
                continue
            for fname in files:
                if not fname.endswith(".html"):
                    continue
                fp = os.path.join(root, fname)
                html = read(fp)
                for kind, pat in self.CARD_PATTERNS:
                    for m in pat.finditer(html):
                        counts[kind] += 1
                        block = m.group(1)
                        imgs = re.findall(r"<img\b[^>]*>", block)
                        alt_m = re.search(
                            r'<img[^>]*\bclass="[^"]*\balt\b[^"]*"[^>]*\bsrc="([^"]+)"',
                            block,
                        )
                        self.assertIsNotNone(alt_m, f"{fp} [{kind}] missing img.alt")
                        main_srcs = [
                            re.search(r'\bsrc="([^"]+)"', tag).group(1)
                            for tag in imgs
                            if 'class="alt"' not in tag and re.search(r'\bsrc="([^"]+)"', tag)
                        ]
                        self.assertTrue(main_srcs, f"{fp} [{kind}] missing main img")
                        msrc = unescape(main_srcs[0])
                        asrc = unescape(alt_m.group(1))
                        self.assertTrue(asrc, f"{fp} [{kind}] empty alt src")
                        self.assertNotEqual(msrc, asrc,
                                            f"{fp} [{kind}] hover equals front ({msrc})")
                        for src in (msrc, asrc):
                            if not src.startswith("http"):
                                resolved = os.path.normpath(
                                    os.path.join(os.path.dirname(fp), src.split("?")[0]))
                                self.assertTrue(os.path.isfile(resolved),
                                                f"{fp} [{kind}] missing {resolved}")
        for kind, count in counts.items():
            self.assertGreater(count, 0, f"expected {kind} cards in built site")

    def test_every_apparel_swap_entry_carries_distinct_backside_image(self):
        targets = [f"{COLLECTIONS[k]['slug']}/index.html" for k in ORDER] + [
            "michigan/bella/index.html"
        ]
        for rel in targets:
            fp = os.path.join(SITE, rel)
            html = page(rel)
            gm = re.search(r'data-apparel="([^"]*)"', html)
            self.assertIsNotNone(gm, rel)
            payload = json.loads(unescape(gm.group(1)))
            self.assertTrue(payload, rel)
            for slug, groups in payload.items():
                for cat, rows in groups.items():
                    for r in rows:
                        im = r.get("image") or ""
                        bk = r.get("back") or ""
                        self.assertTrue(im, f"{rel} [{slug}/{cat}/{r.get('garment')}] missing image")
                        self.assertTrue(bk, f"{rel} [{slug}/{cat}/{r.get('garment')}] missing back")
                        self.assertNotEqual(im, bk, f"{rel} [{slug}/{cat}] front==back")
                        for src in (im, bk):
                            if not src.startswith("http"):
                                resolved = os.path.normpath(
                                    os.path.join(os.path.dirname(fp), src.split("?")[0]))
                                self.assertTrue(os.path.isfile(resolved),
                                                f"{rel} [{slug}/{cat}] missing {resolved}")

    def test_hover_css_and_creator_swap_wiring_ship(self):
        css = page("assets/style.css")
        for rule in (".card:hover .ph img.alt{opacity:1}",
                     ".pcard:hover .pc-ph img.alt",
                     ".jlock .jcard:hover .jph img.alt",
                     ".jlock-girly .gproduct:hover .gproduct-art img.alt"):
            self.assertIn(rule, css)
        drops = page("drops/index.html")
        self.assertIn(".drop-card:hover .drop-img img.alt", drops)
        js = page("assets/app.js")
        bella_js = js[js.index("// ---------- creator apparel-style buttons"):]
        self.assertIn("entry.back", bella_js)
        self.assertIn("card._backSrc", bella_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
