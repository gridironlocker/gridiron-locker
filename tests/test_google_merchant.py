#!/usr/bin/env python3
"""Google Merchant Center feed contract.

Merchant Center ingests site/feeds/google-merchant.xml on a daily scheduled
fetch (https://gridironlocker.store/feeds/google-merchant.xml). Like
Pinterest, Google fails items (or the whole file) on malformed XML, a wrong
price format, an unknown availability value or a link that leaves the claimed
domain. Two Google-specific rules also carry business weight here:

- identifier_exists=no on every item: print-on-demand fan apparel has no
  GTIN/MPN, and without the flag Google disapproves each item for
  "missing GTIN";
- shipping is PARTNER-SCOPED, the same contract the page schema follows:
  Viralstyle publishes a $4.95 US standard rate so its items carry it;
  Mayzing publishes no rate, so its items must carry none (inventing one
  would misquote the checkout).

Everything here reads the committed site/ or calls pure functions on build;
nothing rebuilds or writes.
"""
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "src"))
import build  # noqa: E402

FEED = os.path.join(SITE, "feeds", "google-merchant.xml")
G = "{http://base.google.com/ns/1.0}"
REQUIRED = ["id", "title", "description", "image_link", "price",
            "availability", "condition", "brand", "identifier_exists"]


def feed_items():
    root = ET.parse(FEED).getroot()
    return root.findall("./channel/item")


def gtext(item, field):
    el = item.find(G + field)
    return (el.text or "") if el is not None else ""


class TestGoogleMerchantFeed(unittest.TestCase):
    def test_feed_exists_in_site(self):
        self.assertTrue(os.path.exists(FEED),
                        "site/feeds/google-merchant.xml missing - the build "
                        "must write it (assets()), Merchant Center fetches it")

    def test_valid_xml_rss_with_google_namespace(self):
        root = ET.parse(FEED).getroot()
        self.assertEqual(root.tag, "rss")
        self.assertEqual(root.get("version"), "2.0")
        self.assertIsNotNone(root.find("./channel/title"))

    def test_one_item_per_live_design(self):
        ids = sorted(gtext(i, "id") for i in feed_items())
        live = sorted(build.google_item_id(i["slug"]) for i in build.ALL)
        self.assertEqual(ids, live,
                         "feed must list exactly the live catalogue - no "
                         "retired slugs, no held designs, no omissions")

    def test_ids_obey_google_limit_and_stay_stable(self):
        ids = [gtext(i, "id") for i in feed_items()]
        self.assertTrue(all(len(sid) <= 50 for sid in ids))
        self.assertEqual(len(ids), len(set(ids)), "feed ids must be unique")
        for item in build.ALL:
            slug = item["slug"]
            if len(slug) <= 50:
                self.assertEqual(build.google_item_id(slug), slug)
        self.assertEqual(
            build.google_item_id(
                "limited-edition-cleveland-football-beware-of-the-dawgs"),
            "limited-edition-cleveland-football-beware-b0e407b2")
        # item_group_id carries the stable design slug (pre-hash): Google
        # groups variants by it, and unlike the truncated id the slug never
        # changes when the catalogue grows.
        groups = {gtext(i, "item_group_id"): gtext(i, "id")
                  for i in feed_items()}
        self.assertEqual(len(groups), len(build.ALL),
                         "one item_group_id per live design")
        for item in build.ALL:
            self.assertEqual(groups.get(item["slug"]),
                             build.google_item_id(item["slug"]), item["slug"])

    def test_required_fields_on_every_item(self):
        for item in feed_items():
            for f in REQUIRED:
                self.assertTrue(gtext(item, f),
                                f"item {gtext(item, 'id')!r} missing g:{f}")
            link = item.find("link")
            self.assertIsNotNone(link, "un-namespaced <link> required")
            self.assertTrue((link.text or "").strip())

    def test_value_vocabularies(self):
        for item in feed_items():
            sid = gtext(item, "id")
            self.assertRegex(gtext(item, "price"), r"^\d+\.\d{2} USD$", sid)
            self.assertEqual(gtext(item, "availability"), "in stock", sid)
            self.assertEqual(gtext(item, "condition"), "new", sid)
            self.assertEqual(gtext(item, "identifier_exists"), "no",
                             f"{sid}: POD apparel has no GTIN/MPN - without "
                             "identifier_exists=no Google disapproves it")

    def test_links_stay_on_claimed_domain(self):
        urls = {build.google_item_id(i["slug"]): build.DOMAIN + i["url"]
                for i in build.ALL}
        for item in feed_items():
            sid = gtext(item, "id")
            link = item.find("link").text
            self.assertEqual(link, urls[sid],
                             f"{sid}: link must be the product page on the "
                             "claimed domain, exactly as published")
            self.assertTrue(gtext(item, "image_link").startswith("https://"), sid)

    def test_shipping_is_partner_scoped(self):
        partner = {build.google_item_id(i["slug"]): i["partner"]
                   for i in build.ALL}
        for item in feed_items():
            sid = gtext(item, "id")
            ship = item.find(G + "shipping")
            if partner[sid] == "Viralstyle":
                self.assertIsNotNone(ship, f"{sid}: Viralstyle items carry "
                                           "the published $4.95 US rate")
                self.assertEqual(ship.find(G + "price").text, "4.95 USD", sid)
                self.assertEqual(ship.find(G + "country").text, "US", sid)
            else:
                self.assertIsNone(ship, f"{sid}: Mayzing publishes no rate - "
                                        "never invent one in the feed")

    def test_matches_pure_generator(self):
        """Committed feed == what build.google_feed_xml() produces now."""
        with open(FEED, encoding="utf-8") as fh:
            on_disk = fh.read()
        self.assertEqual(on_disk, build.google_feed_xml(),
                         "site/feeds/google-merchant.xml drifted from the "
                         "generator - rebuild (python3 src/build.py)")

    def test_never_lists_held_or_delisted_slugs(self):
        """Google Merchant cleanup (2026-11-05 product-issues export).

        21 free-listing items were flagged "Missing product price". Every one
        is a retired design: either delisted.json (supplier campaign ended
        2026-09-12) or data/fulfillment.json 'hold' (withheld until the design
        is uploaded to Mayzing - no sellable page exists to price). Their
        Merchant items are stale crawl/upload data living in some other data
        source, not this feed. This test keeps it that way: a held or delisted
        slug may never enter the feed, and every item must carry a price - the
        exact attribute Google reported missing.
        """
        import json
        with open(os.path.join(ROOT, "data", "fulfillment.json")) as fh:
            held = set(json.load(fh)["hold"])
        with open(os.path.join(ROOT, "data", "delisted.json")) as fh:
            delisted = set(json.load(fh)["slugs"])
        banned = {build.google_item_id(s) for s in held | delisted}
        ids = [gtext(it, "id") for it in feed_items()]
        leaked = sorted(set(ids) & banned)
        self.assertEqual(leaked, [], f"held/delisted slugs in the feed: {leaked}")
        for it in feed_items():
            self.assertTrue(gtext(it, "price").strip(),
                            f"missing price attribute: {gtext(it, 'id')}")

    def test_no_commas_in_image_links(self):
        # Shared with the Pinterest contract: Mayzing mockup URLs are
        # comma-separated parameter lists; the encoded form is what both
        # ingesters get, so one URL serves both feeds and the CDN cache.
        for item in feed_items():
            for f in ("image_link", "additional_image_link"):
                v = gtext(item, f)
                self.assertNotIn(",", v, gtext(item, "id"))


class TestShoppingCrawlerRobots(unittest.TestCase):
    """Retired /shop/ URLs must be fenced out for Shopping crawlers.

    Google's Shopping crawler (Storebot-Google) re-reads product URLs it
    once knew. Every retired /shop/ URL answers with a redirect stub that
    carries no price - the product is gone - and each re-read strips the
    price off the legacy Merchant Center item, refilling the account with
    "Missing product price" ghost items (21 on 2026-11-05, 24 on 2026-11-08;
    every ghost Item ID was a retired design slug). robots.txt is the only
    lever the site has: the stubs must stay crawlable for Googlebot (the
    retirement redirect is Search-critical) while the Shopping crawlers are
    locked out of every stub path. Live product pages stay allowed -
    Shopping verifies the offers on them - and the redirect-target
    collections stay open too. The disallow list is generated from the
    retired catalogue on each build (src/build.py), so a new retirement is
    fenced automatically; these tests pin that the fence and the stub
    population can never drift apart.
    """

    SHOPPING_UAS = ("Storebot-Google", "AdsBot-Google")

    @staticmethod
    def _groups():
        """robots.txt user-agent groups: ua token -> Disallow paths.

        Consecutive User-agent lines share the rules that follow them; a
        User-agent line after rules starts a new group. Comments and blank
        lines are separators only in the loose sense - they are stripped.
        """
        groups, pending, in_rules = {}, [], False
        with open(os.path.join(SITE, "robots.txt")) as fh:
            for raw in fh:
                line = raw.split("#", 1)[0].strip()
                if not line:
                    continue
                low = line.lower()
                if low.startswith("user-agent:"):
                    if in_rules:
                        pending, in_rules = [], False
                    pending.append(line.split(":", 1)[1].strip())
                elif low.startswith(("allow:", "disallow:")):
                    # Allow: is a rule line too - it closes the user-agent
                    # run, per RFC 9309. Only Disallow: paths are collected.
                    if low.startswith("disallow:"):
                        for ua in pending:
                            groups.setdefault(ua, []).append(
                                line.split(":", 1)[1].strip())
                    in_rules = True
        return groups

    @staticmethod
    def _disallowed(paths, url):
        """robots.txt prefix match incl. the '$' end-of-match anchor."""
        for d in paths:
            if not d:
                continue
            if d.endswith("$"):
                if url == d[:-1]:
                    return True
            elif url.startswith(d):
                return True
        return False

    @staticmethod
    def _stub_paths():
        """Every redirect stub under /shop/ as its URL path.

        Walks the built site (not the data files) so the test sees exactly
        what a crawler can fetch: a stub is any page carrying the
        data-gl-redirect marker - slug stubs at /shop/<slug>/ plus the
        garment-variant tombstones at /shop/<slug>/<style>/.
        """
        out = []
        shop = os.path.join(SITE, "shop")
        for slug in sorted(os.listdir(shop)):
            base = os.path.join(shop, slug)
            if not os.path.isdir(base):
                continue
            idx = os.path.join(base, "index.html")
            if os.path.exists(idx) and "data-gl-redirect" in open(idx).read():
                out.append(f"/shop/{slug}/")
            for sub in sorted(os.listdir(base)):
                vidx = os.path.join(base, sub, "index.html")
                if (os.path.isdir(os.path.join(base, sub))
                        and os.path.exists(vidx)
                        and "data-gl-redirect" in open(vidx).read()):
                    out.append(f"/shop/{slug}/{sub}/")
        return out

    def test_shopping_crawlers_are_named_in_robots(self):
        robots = open(os.path.join(SITE, "robots.txt")).read()
        for ua in self.SHOPPING_UAS:
            self.assertIn(f"User-agent: {ua}", robots,
                          f"{ua} group missing from robots.txt - Shopping "
                          "crawlers must be fenced out of retired /shop/ URLs")

    def test_every_stub_is_fenced_for_every_shopping_crawler(self):
        stubs = self._stub_paths()
        self.assertGreater(len(stubs), 400,
                           "stub population collapsed - the walk or the "
                           "retired catalogue is broken")
        groups = self._groups()
        for ua in self.SHOPPING_UAS:
            rules = groups.get(ua, [])
            self.assertTrue(rules, f"{ua} has no Disallow rules")
            missing = [p for p in stubs
                       if not self._disallowed(rules, p)
                       and not self._disallowed(rules, p.rstrip("/"))]
            self.assertEqual(missing, [],
                             f"{ua} can read stub pages: {missing[:10]}")

    def test_live_product_pages_stay_crawlable(self):
        groups = self._groups()
        for ua in self.SHOPPING_UAS:
            rules = groups.get(ua, [])
            blocked = [i["slug"] for i in build.ALL
                       if self._disallowed(rules, i["url"])
                       or self._disallowed(rules, i["url"].rstrip("/"))]
            self.assertEqual(blocked, [],
                             f"{ua} is fenced out of LIVE product pages: "
                             f"{blocked} - Shopping must verify offers on them")

    def test_googlebot_and_star_keep_the_shop(self):
        # The retirement redirect only works if Googlebot can still fetch
        # the stubs, and the '*' group must never fence /shop/ either.
        groups = self._groups()
        for ua in ("*", "Googlebot-Image"):
            rules = groups.get(ua, [])
            fenced = [d for d in rules if d.startswith("/shop")]
            self.assertEqual(fenced, [],
                             f"{ua} group fences /shop: {fenced}")


if __name__ == "__main__":
    unittest.main()
