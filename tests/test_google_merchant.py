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

    def test_no_commas_in_image_links(self):
        # Shared with the Pinterest contract: Mayzing mockup URLs are
        # comma-separated parameter lists; the encoded form is what both
        # ingesters get, so one URL serves both feeds and the CDN cache.
        for item in feed_items():
            for f in ("image_link", "additional_image_link"):
                v = gtext(item, f)
                self.assertNotIn(",", v, gtext(item, "id"))


if __name__ == "__main__":
    unittest.main()
