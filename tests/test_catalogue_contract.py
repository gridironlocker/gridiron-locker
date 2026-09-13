#!/usr/bin/env python3
"""Tests for data/catalogue-live.json - the storefront -> marketing contract.

Owned by Arena (storefront side). marketing/ reads this contract and must never
write it; see AGENTS.md section 3.2 and CODEX-TASKS.md Task 1.

The contract exists because marketing used to read data/products.json - a stale
113-slug Viralstyle crawl - as "the catalogue", which put 55 unpurchasable
designs into the promotion queue. These tests make it impossible for the
contract to silently become the thing it was created to replace: wrong, stale,
or disagreeing with the build and the pages actually on disk.

Run with:
    python3 tests/test_catalogue_contract.py
    python3 -m unittest discover -s tests -p "test_*.py"
"""
import datetime
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
SITE = os.path.join(ROOT, "site")
CONTRACT_PATH = os.path.join(ROOT, "data", "catalogue-live.json")

sys.path.insert(0, SRC)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

import build  # noqa: E402  (import is read-only; no pages are written)
import catalogue_contract as cc  # noqa: E402


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_file(path):
    """Never open(...).read() inline - it leaks the handle until GC collects it,
    which surfaces as a ResourceWarning in CI. See AGENTS.md section 6."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class ContractExists(unittest.TestCase):
    def test_committed_contract_is_present(self):
        """refresh.yml regenerates this on every build, so it must be committed.

        If it is missing, marketing has no authoritative catalogue and will fall
        back to the stale crawl - the exact failure this file prevents.
        """
        self.assertTrue(
            os.path.isfile(CONTRACT_PATH),
            "data/catalogue-live.json is missing. Run: python3 src/build.py && "
            "python3 src/catalogue_contract.py")

    def test_contract_names_its_own_generator(self):
        c = read_json(CONTRACT_PATH)
        self.assertEqual(c["generator"], "src/catalogue_contract.py")
        self.assertIn("build.ALL", c["source"])
        self.assertIn("contract", c, "the contract must state its own terms")


class ContractMatchesTheBuild(unittest.TestCase):
    """The contract is derived from build.ALL, so it must agree with it exactly.

    These tests import build (read-only) rather than regenerating the contract,
    because a test run must not write to the repository - see AGENTS.md section 4.
    """

    @classmethod
    def setUpClass(cls):
        cls.c = read_json(CONTRACT_PATH)
        cls.live = {i["slug"] for i in build.ALL}

    def test_same_slug_set_as_the_build(self):
        contract_slugs = {p["slug"] for p in self.c["products"]}
        self.assertEqual(
            contract_slugs, self.live,
            "data/catalogue-live.json disagrees with src/build.py. Regenerate it: "
            "python3 src/catalogue_contract.py")

    def test_count_and_per_collection_match(self):
        self.assertEqual(self.c["count"], len(build.ALL))
        self.assertEqual(self.c["count"], len(self.c["products"]))
        expected = {k: len(build.MODEL[k]) for k in build.ORDER}
        self.assertEqual(self.c["per_collection"], expected)
        self.assertEqual(sum(self.c["per_collection"].values()), self.c["count"])

    def test_every_entry_carries_the_fields_marketing_needs(self):
        required = ("slug", "name", "collection", "partner", "url", "buy_url",
                    "price_usd", "site_published")
        for p in self.c["products"]:
            for field in required:
                self.assertIn(field, p, f"{p.get('slug')}: missing {field}")
            self.assertTrue(p["slug"] and p["name"], p)
            self.assertTrue(p["buy_url"],
                            f"{p['slug']}: no buy_url - a design nobody can purchase")
            self.assertIsInstance(p["price_usd"], (int, float), p["slug"])

    def test_urls_are_absolute_and_point_at_real_pages(self):
        """A relative URL here would be useless to marketing, and a URL with no
        file behind it is how a queue ends up promoting a 404."""
        for p in self.c["products"]:
            self.assertTrue(
                p["url"].startswith(build.DOMAIN + "/shop/"),
                f"{p['slug']}: url is not an absolute storefront URL: {p['url']!r}")
            rel = p["url"].replace(build.DOMAIN, "").strip("/")
            self.assertTrue(
                os.path.isfile(os.path.join(SITE, rel, "index.html")),
                f"{p['slug']}: {p['url']} has no page on disk")

    def test_partner_is_one_of_the_two_real_partners(self):
        for p in self.c["products"]:
            self.assertIn(p["partner"], ("Viralstyle", "Mayzing"),
                          f"{p['slug']}: unknown partner {p['partner']!r}")
        partners = {p["partner"] for p in self.c["products"]}
        self.assertEqual(len(partners), 2,
                         "both fulfilment partners should be represented")

    def test_no_unpublished_designs_are_offered(self):
        self.assertEqual(
            self.c["unpublished_but_in_catalogue"], [],
            "the catalogue contains designs with no published page; marketing "
            "would promote something a customer cannot reach")
        self.assertTrue(all(p["site_published"] for p in self.c["products"]))


class ContractIsNotStale(unittest.TestCase):
    def test_generated_today_utc(self):
        """The contract is regenerated on every build, and refresh.yml builds
        twice a day, so it should carry today's UTC date.

        Tolerance of one day absorbs a run between midnight UTC and the 06:15
        refresh - the same reasoning as BuildFreshness in test_layout.py. If this
        fails, the refresh pipeline has stopped landing, not the contract.
        """
        c = read_json(CONTRACT_PATH)
        stamp = datetime.date.fromisoformat(c["generated"])
        today = datetime.datetime.now(datetime.timezone.utc).date()
        self.assertLessEqual(stamp, today,
                             f"contract is dated in the future: {stamp}")
        self.assertLessEqual(
            (today - stamp).days, 1,
            f"STALE CONTRACT: data/catalogue-live.json was generated {stamp} and "
            f"refresh.yml should have regenerated it today. Run: "
            f"python3 src/build.py && python3 src/catalogue_contract.py")


class ContractExposesTheGates(unittest.TestCase):
    """The excluded counts are what let a reader reconcile 113 -> 84 without
    re-deriving the merge. If they go missing, the next person to debug a
    shrinking catalogue has to rediscover the hold list from scratch."""

    def test_excluded_counts_are_present_and_sane(self):
        c = read_json(CONTRACT_PATH)
        ex = c["excluded"]
        for key in ("delisted", "fulfillment_hold", "stale_crawl_slugs"):
            self.assertIn(key, ex)
            self.assertIsInstance(ex[key], int, key)
        self.assertIn("note", ex)
        self.assertIn("NOT the catalogue", ex["note"],
                      "the note must warn against using the crawl as a catalogue")

    def test_excluded_counts_match_the_data_files(self):
        ex = read_json(CONTRACT_PATH)["excluded"]
        delisted = read_json(os.path.join(ROOT, "data", "delisted.json"))
        fulfillment = read_json(os.path.join(ROOT, "data", "fulfillment.json"))
        crawl = read_json(os.path.join(ROOT, "data", "products.json"))
        self.assertEqual(ex["delisted"], len(delisted.get("slugs", {})))
        self.assertEqual(ex["fulfillment_hold"], len(fulfillment.get("hold", [])))
        self.assertEqual(ex["stale_crawl_slugs"], len(crawl))

    def test_contract_is_smaller_than_the_stale_crawl(self):
        """The whole point: the contract must NOT be the crawl.

        If these two numbers ever match, something has reverted to publishing
        the raw crawl as the catalogue and the 55-ghost regression is back.
        """
        c = read_json(CONTRACT_PATH)
        self.assertLess(
            c["count"], c["excluded"]["stale_crawl_slugs"],
            "the contract now equals the raw Viralstyle crawl - it has stopped "
            "applying the delisted and fulfillment-hold gates")


class EmitterIsSafe(unittest.TestCase):
    def test_emitter_does_not_import_or_write_the_site(self):
        """catalogue_contract.py reads site/ to verify pages exist; it must never
        write there. src/build.py is the only writer of site/."""
        src = read_file(os.path.join(SRC, "catalogue_contract.py"))
        self.assertNotIn('open(SITE', src)
        self.assertNotIn("shutil", src)
        self.assertNotIn("build.main()", src)
        self.assertIn('if __name__ == "__main__":', src,
                      "the emitter must be import-safe")

    def test_page_is_published_rejects_redirect_stubs(self):
        """A retired slug keeps a noindex stub at the same path. Publishing a
        stub as a sellable design would send marketing to a tombstone."""
        stub_dir = os.path.join(SITE, "shop")
        stubs = []
        for d in sorted(os.listdir(stub_dir)):
            f = os.path.join(stub_dir, d, "index.html")
            if os.path.isfile(f):
                with open(f, encoding="utf-8") as fh:
                    if "data-gl-redirect" in fh.read():
                        stubs.append(d)
        self.assertTrue(stubs, "expected retired-slug redirect stubs under site/shop/")
        for slug in stubs[:10]:
            self.assertFalse(cc.page_is_published(slug),
                             f"{slug}: a redirect stub was reported as a published product")
        contract_slugs = {p["slug"] for p in read_json(CONTRACT_PATH)["products"]}
        self.assertFalse(contract_slugs & set(stubs),
                         "the contract contains redirect stubs")

    def test_validate_rejects_a_broken_contract(self):
        """The emitter must refuse to publish a contract marketing cannot trust."""
        good = read_json(CONTRACT_PATH)

        broken = json.loads(json.dumps(good))
        broken["products"] = []
        self.assertTrue(cc.validate(broken), "an empty contract must fail validation")

        broken = json.loads(json.dumps(good))
        broken["count"] = broken["count"] + 1
        self.assertTrue(cc.validate(broken), "a wrong count must fail validation")

        broken = json.loads(json.dumps(good))
        broken["products"][0]["buy_url"] = ""
        self.assertTrue(cc.validate(broken), "a design with no buy_url must fail")

        broken = json.loads(json.dumps(good))
        broken["products"][0]["partner"] = "Printful"
        self.assertTrue(cc.validate(broken), "an unknown partner must fail")

        broken = json.loads(json.dumps(good))
        broken["products"].append(dict(broken["products"][0]))
        self.assertTrue(cc.validate(broken), "duplicate slugs must fail")

        self.assertEqual(cc.validate(good), [],
                         "the committed contract should validate clean")


if __name__ == "__main__":
    unittest.main()
