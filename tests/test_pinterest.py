#!/usr/bin/env python3
"""Pinterest Catalog + Verified Merchant contract.

Pinterest ingests a hosted CSV once a day and fails the WHOLE file on one bad
header, an unknown availability value, a comma inside an image URL or a link
that does not land on the product it describes. It also re-checks the domain
claim (<meta name="p:domain_verify">) and, for the Verified Merchant Program,
expects the Tag's pagevisit / checkout events. This file pins each of those so
a refactor cannot quietly un-ship the catalogue again.

What this covers, and why each rule exists:

- the feed is written INTO site/ by the build (site/feeds/pinterest.csv), not
  copied from marketing/. sync_marketing() withholds every .csv on purpose,
  which is why /marketing/pinterest_feed.csv 404'd for Pinterest;
- one row per live design in build.ALL, no more and no fewer - the feed can
  never list a retired slug or a held design;
- every value follows the retail catalogue spec (field names, "24.99 USD",
  "in stock", "new", https image links with commas encoded);
- the Pinterest Tag never loads before consent, and is not emitted at all
  while no Tag ID is configured;
- the privacy page describes exactly what the build ships.

Everything here reads the committed site/ or calls pure functions on build;
nothing rebuilds or writes.
"""
import csv
import io
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "src"))
import build  # noqa: E402

FEED = os.path.join(SITE, "feeds", "pinterest.csv")
REQUIRED = ["id", "title", "description", "link", "image_link", "price", "availability"]


def read(rel):
    with open(os.path.join(SITE, rel), encoding="utf-8") as fh:
        return fh.read()


def feed_rows():
    with open(FEED, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class PinterestFeedFile(unittest.TestCase):
    """The committed site/feeds/pinterest.csv - what Pinterest actually fetches."""

    def test_feed_is_published_under_site_not_marketing(self):
        self.assertTrue(os.path.exists(FEED), "site/feeds/pinterest.csv missing - "
                        "assets() must write it on every build")
        # The old location is withheld by PUBLISH_EXT and must stay withheld:
        # the catalogue lives at ONE fetchable URL.
        self.assertFalse(os.path.exists(os.path.join(SITE, "marketing", "pinterest_feed.csv")))
        self.assertEqual(build.PINTEREST_FEED_PATH, "feeds/pinterest.csv")

    def test_header_is_exactly_the_documented_columns(self):
        with open(FEED, encoding="utf-8", newline="") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, build.PINTEREST_FEED_COLUMNS)
        for col in REQUIRED:
            self.assertIn(col, header, col)

    def test_one_row_per_live_design(self):
        rows = feed_rows()
        live = {i["slug"] for i in build.ALL}
        self.assertEqual({r["id"] for r in rows}, live)
        self.assertEqual(len(rows), len(build.ALL))          # no duplicate ids
        retired = set(build.retired_slugs())
        self.assertFalse({r["id"] for r in rows} & retired)

    def test_required_fields_are_never_blank(self):
        for r in feed_rows():
            for col in REQUIRED:
                self.assertTrue(r[col].strip(), f"{r['id']}: blank {col}")

    def test_links_land_on_the_storefront_product_page(self):
        for r in feed_rows():
            self.assertEqual(r["link"], f"{build.DOMAIN}/shop/{r['id']}/", r["id"])
            self.assertTrue(os.path.exists(os.path.join(SITE, "shop", r["id"], "index.html")),
                            f"{r['id']}: feed links to a page that does not exist")
            self.assertNotIn("viralstyle.com", r["link"])
            self.assertNotIn("mayzing", r["link"])

    def test_image_links_are_https_absolute_and_comma_free(self):
        for r in feed_rows():
            for col in ("image_link", "additional_image_link"):
                u = r[col]
                if not u:
                    continue
                self.assertTrue(u.startswith("https://"), f"{r['id']}: {col} not https: {u}")
                self.assertNotIn(",", u, f"{r['id']}: {col} contains a comma - Pinterest "
                                         f"cannot process it (encode as %2C)")
                self.assertNotIn(" ", u)
                self.assertLessEqual(len(u), 2000)
                if u.startswith(build.DOMAIN + "/"):
                    local = u[len(build.DOMAIN) + 1:].split("?")[0]
                    self.assertTrue(os.path.exists(os.path.join(SITE, local)),
                                    f"{r['id']}: {col} -> missing local file {local}")
            if r["additional_image_link"]:
                self.assertNotEqual(r["additional_image_link"], r["image_link"], r["id"])

    def test_value_vocabularies_follow_the_spec(self):
        live = {i["slug"]: i for i in build.ALL}
        for r in feed_rows():
            self.assertRegex(r["price"], r"^\d+\.\d{2} USD$", r["id"])
            self.assertNotEqual(r["price"], "0.00 USD", r["id"])
            self.assertEqual(r["price"], f"{live[r['id']]['price']:.2f} USD", r["id"])
            self.assertEqual(r["availability"], "in stock", r["id"])
            self.assertEqual(r["condition"], "new", r["id"])
            self.assertEqual(r["brand"], build.BRAND, r["id"])
            self.assertIn(r["gender"], ("", "unisex"), r["id"])
            self.assertIn(r["age_group"], ("", "adult"), r["id"])
            self.assertIn(r["custom_label_0"], ("Mayzing", "Viralstyle"), r["id"])
            self.assertEqual(r["custom_label_0"], live[r["id"]]["partner"], r["id"])
            self.assertEqual(r["custom_label_1"], live[r["id"]]["col"], r["id"])
            self.assertLessEqual(len(r["id"]), 127)
            self.assertLessEqual(len(r["title"]), 500)
            self.assertLessEqual(len(r["description"]), 10000)
            self.assertLessEqual(len(r["link"]), 511)

    def test_google_product_category_matches_the_garment(self):
        live = {i["slug"]: i for i in build.ALL}
        for r in feed_rows():
            g = live[r["id"]]["garment"]
            self.assertEqual(r["google_product_category"],
                             build._PIN_GPC.get(g, build._PIN_GPC_DEFAULT), r["id"])
            self.assertRegex(r["product_type"], r"^Fan Apparel > [^>]+ > [^>]+$", r["id"])
            self.assertTrue(r["product_type"].endswith(g), r["id"])

    def test_text_fields_are_plain_and_on_brand(self):
        for r in feed_rows():
            for col in ("title", "description"):
                self.assertNotRegex(r[col], r"<[a-z/][^>]*>", f"{r['id']}: HTML in {col}")
                self.assertNotIn("&amp;", r[col])
                self.assertNotIn("&#", r[col])
            # fan-made / independent framing is the trademark defence - it
            # must reach Pinterest too, not just the landing page
            self.assertRegex((r["title"] + " " + r["description"]).lower(),
                             r"fan-made|independent", r["id"])
            for banned in ("officially licensed", "official merchandise", "authorized dealer"):
                self.assertNotIn(banned, r["description"].lower(), r["id"])

    def test_feed_is_not_treated_as_a_page(self):
        self.assertNotIn("feeds/pinterest", read("sitemap.xml"))
        self.assertNotIn("feeds/pinterest", read("sitemap-images.xml"))
        # and robots does not fence it off - Pinterest's fetcher must get in
        for line in read("robots.txt").splitlines():
            if line.lower().startswith("disallow:"):
                self.assertNotIn("/feeds", line)


class PinterestFeedGenerator(unittest.TestCase):
    """Pure functions on build - checked without a rebuild."""

    def test_rows_match_the_committed_file(self):
        generated = build.pinterest_feed_rows()
        committed = feed_rows()
        self.assertEqual([r["id"] for r in generated], [r["id"] for r in committed])
        for g, c in zip(generated, committed):
            self.assertEqual(g["link"], c["link"])
            self.assertEqual(g["image_link"], c["image_link"])
            self.assertEqual(g["price"], c["price"])

    def test_csv_render_quotes_every_field_and_round_trips(self):
        text = build.pinterest_feed_csv()
        first = text.splitlines()[0]
        self.assertEqual(first, ",".join(f'"{c}"' for c in build.PINTEREST_FEED_COLUMNS))
        self.assertNotIn("\r", text)
        parsed = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(parsed), len(build.ALL))

    def test_image_url_encoding(self):
        self.assertEqual(build.pinterest_image_url("/img/p/x-front.webp"),
                         build.DOMAIN + "/img/p/x-front.webp")
        self.assertEqual(
            build.pinterest_image_url("https://cdn.example/mockups/id:1,sig:abc,w:1000/image.png"),
            "https://cdn.example/mockups/id:1%2Csig:abc%2Cw:1000/image.png")
        self.assertEqual(build.pinterest_image_url(""), "")

    def test_every_mayzing_mockup_is_encoded_not_dropped(self):
        # 35 of the 37 Mayzing designs have no local mockup, so the remote
        # (comma-laden) URL is the only image there is. It must be present.
        for r in build.pinterest_feed_rows():
            if r["custom_label_0"] == "Mayzing" and "mayzing.com" in r["image_link"]:
                self.assertIn("%2C", r["image_link"], r["id"])


class PinterestDomainClaim(unittest.TestCase):

    def test_verify_token_comes_from_config_and_is_on_every_page(self):
        cfg = build.CFG
        self.assertTrue(cfg.get("pinterest_verify"))
        self.assertEqual(build.PINTEREST_VERIFY, cfg["pinterest_verify"])
        tag = f'<meta name="p:domain_verify" content="{cfg["pinterest_verify"]}">'
        # Retired slugs are bare noindex redirect stubs (no head()), and the
        # internal dashboards are not Pinterest's business. Everything else
        # that renders a page must carry the claim.
        stubs = {f"shop/{s}" for s in build.retired_slugs()}
        missing = []
        for dirpath, _dirs, files in os.walk(SITE):
            rel = os.path.relpath(dirpath, SITE).replace(os.sep, "/")
            if rel.startswith(("ops", "marketing")) or rel in stubs:
                continue
            if "index.html" in files and tag not in read(os.path.join(rel, "index.html")):
                missing.append(rel)
        self.assertEqual(missing, [], missing[:10])
        # and every LIVE product page in particular - Pinterest re-verifies
        # against the product URLs in the feed
        for it in build.ALL:
            self.assertIn(tag, read(f"shop/{it['slug']}/index.html"), it["slug"])

    def test_head_omits_the_meta_when_no_token_is_configured(self):
        saved = build.PINTEREST_VERIFY
        try:
            build.PINTEREST_VERIFY = ""
            self.assertNotIn("p:domain_verify", build.head("t", "d", "/"))
        finally:
            build.PINTEREST_VERIFY = saved


class PinterestTagConsent(unittest.TestCase):
    """The Tag rides the GA4 opt-in - never a static script, never a pixel."""

    def test_no_tag_id_means_no_pinterest_script_anywhere(self):
        if build.PINTEREST_TAG:
            self.skipTest("a Pinterest Tag ID is configured")
        self.assertEqual(build.pinterest_tag_snippet(), "")
        for rel in ("index.html", "privacy/index.html", "shop/%s/index.html" % build.ALL[0]["slug"]):
            html = read(rel)
            self.assertNotIn("pinimg.com", html, rel)
            self.assertNotIn("pintrk(", html, rel)
            self.assertNotIn("glLoadPinterest", html, rel)
        priv = re.sub(r"\s+", " ", read("privacy/index.html"))
        self.assertIn("No Pinterest script runs on this site", priv)
        self.assertIn("No advertising cookies are written by this site", priv)

    def test_configured_tag_is_consent_gated(self):
        saved = build.PINTEREST_TAG
        try:
            build.PINTEREST_TAG = "2612345678901"
            head = build.head("t", "d", "/")
            snippet = build.pinterest_tag_snippet()
            self.assertIn(snippet, head)
            self.assertIn("window.glLoadPinterest", snippet)
            self.assertIn("pintrk('load', \"2612345678901\")", snippet)
            self.assertIn("pintrk('page')", snippet)
            self.assertIn("gl_analytics=1", snippet)
            # the loader is the ONLY path to core.js: no static <script src>,
            # no <noscript> pixel (which would fire without consent)
            self.assertNotRegex(head, r'<script[^>]+src="https://s\.pinimg\.com')
            self.assertNotIn("ct.pinterest.com", head)
            self.assertNotIn("<noscript", head)
            # the loader body only runs inside glLoadPinterest or on cookie=1
            self.assertLess(snippet.index("window.glLoadPinterest = function"),
                            snippet.index("s.pinimg.com/ct/core.js"))
        finally:
            build.PINTEREST_TAG = saved

    def test_app_js_wires_consent_and_the_vmp_events(self):
        js = read("assets/app.js")
        # Allow -> both loaders; the Pinterest one guarded so unconfigured
        # builds do not throw
        self.assertIn("if(v==='1'&&window.glLoadAnalytics) window.glLoadAnalytics();", js)
        self.assertIn("if(v==='1'&&window.glLoadPinterest) window.glLoadPinterest();", js)
        # every pintrk call goes through the try/catch helper
        self.assertIn("function glPin(ev,data){try{pintrk('track',ev,data);}catch(e){}}", js)
        self.assertEqual(len(re.findall(r"\bpintrk\(", js)), 1, "raw pintrk() call outside glPin")
        for ev in ("pagevisit", "checkout", "viewcategory"):
            self.assertIn(f"glPin('{ev}'", js, ev)
        # product_id must be the slug so it joins to the feed's id column
        self.assertIn("product_id:d.slug", js)
        self.assertIn("currency:'USD'", js)
        # the banner copy matches the build state
        if build.PINTEREST_TAG:
            self.assertIn("Pinterest Tag", js)
        else:
            self.assertIn("No advertising cookies, and we never sell data.", js)
            self.assertNotIn("__CONSENT_COPY__", js)

    def test_collection_pages_are_marked_for_viewcategory(self):
        from collections_data import COLLECTIONS, ORDER
        for k in ORDER:
            html = read(f"{COLLECTIONS[k]['slug']}/index.html")
            self.assertIn(f'<body data-root="../" data-collection-page="{k}">', html, k)
        self.assertNotIn("data-collection-page", read("index.html"))
        self.assertNotIn("data-collection-page", read("shop/%s/index.html" % build.ALL[0]["slug"]))

    def test_privacy_page_documents_pinterest(self):
        priv = read("privacy/index.html")
        self.assertIn("<h2>Pinterest</h2>", priv)
        self.assertIn("domain-verification meta tag", priv)
        if build.PINTEREST_TAG:
            self.assertIn("Pinterest Tag", priv)
            self.assertIn("_pin_unauth", priv)
            self.assertIn("policy.pinterest.com/privacy-policy", priv)


class LiveEngineStorefrontLinks(unittest.TestCase):
    """marketing/live_engine.py must hand Pinterest / drops the storefront URL,
    not the supplier campaign URL from the crawl."""

    def test_storefront_url(self):
        sys.path.insert(0, os.path.join(ROOT, "marketing"))
        import live_engine  # noqa: E402  (import is read-only)
        self.assertEqual(live_engine.DOMAIN, build.DOMAIN)
        self.assertEqual(live_engine.storefront_url("the-wall"), f"{build.DOMAIN}/shop/the-wall/")
        src = open(os.path.join(ROOT, "marketing", "live_engine.py"), encoding="utf-8").read()
        self.assertIn('"product_url": storefront_url(slug)', src)
        self.assertNotIn('"product_url": product.get("url"', src)


if __name__ == "__main__":
    unittest.main()
