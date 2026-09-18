#!/usr/bin/env python3
"""Regression coverage for source-based sitemap dates and URL quality."""
import datetime
import importlib.util
import os
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, os.path.join(ROOT, "src"))
import build  # noqa: E402


NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
IMAGE_NS = {"sm": NS["sm"], "image": "http://www.google.com/schemas/sitemap-image/1.1"}


def read_xml(name):
    with open(os.path.join(SITE, name), encoding="utf-8") as fh:
        return ET.fromstring(fh.read())


def sitemap_rows(name="sitemap.xml"):
    root = read_xml(name)
    return {
        node.findtext("sm:loc", "", NS): node.findtext("sm:lastmod", "", NS)
        for node in root.findall("sm:url", NS)
    }


class SitemapDates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = sitemap_rows()
        cls.image_rows = sitemap_rows("sitemap-images.xml")

    def test_lastmod_is_deterministic_without_source_changes(self):
        """Two evaluations of the same source state must be byte-for-byte equal."""
        first = {url: build.sitemap_lastmod(url) for url in self.rows}
        second = {url: build.sitemap_lastmod(url) for url in self.rows}
        self.assertEqual(first, second)
        self.assertEqual(first, self.rows)

    def test_product_dates_use_source_or_stable_fallback_not_today(self):
        today = build.TODAY
        product_rows = {u: d for u, d in self.rows.items() if "/shop/" in u}
        self.assertTrue(product_rows)
        self.assertTrue(
            all(value != today for value in product_rows.values()),
            "product <lastmod> must not be the build date")
        # These are source facts already present in the repository: the newest
        # Browns campaign was added on Sept 10, and Mayzing captured the
        # migrated catalogue on Sept 12.
        self.assertEqual(
            self.rows[build.DOMAIN + "/shop/limited-edition-no-fly-zone/"],
            "2026-09-10")
        self.assertEqual(
            self.rows[build.DOMAIN + "/shop/bryce-19/"],
            "2026-09-12")
        self.assertEqual(
            self.rows[build.DOMAIN + "/shop/limited-edition-grb5/"],
            build.SITEMAP_DATE_FALLBACK)

    def test_changing_one_product_source_date_changes_only_that_product(self):
        """A product date must not fan out to hubs or unrelated products."""
        target = build.DOMAIN + "/shop/limited-edition-grb5/"
        original = build.PRODUCT_LASTMODS[target.replace(build.DOMAIN, "")]
        before = {url: build.sitemap_lastmod(url) for url in self.rows}
        try:
            build.PRODUCT_LASTMODS[target.replace(build.DOMAIN, "")] = "2026-09-15"
            after = {url: build.sitemap_lastmod(url) for url in self.rows}
        finally:
            build.PRODUCT_LASTMODS[target.replace(build.DOMAIN, "")] = original
        changed = {url for url in before if before[url] != after[url]}
        self.assertEqual(changed, {target})
        self.assertEqual(after[target], "2026-09-15")

    def test_sitemap_has_valid_unique_canonical_directory_urls(self):
        self.assertEqual(len(self.rows), 108)
        self.assertEqual(len(self.rows), len(set(self.rows)))
        for url, lastmod in self.rows.items():
            self.assertTrue(url.startswith(build.DOMAIN + "/"), url)
            self.assertFalse("?" in url or "#" in url, url)
            self.assertTrue(url.endswith("/"), url)
            self.assertNotIn("http://", url)
            self.assertNotIn("/404", url)
            self.assertRegex(lastmod, r"^\d{4}-\d{2}-\d{2}$")
            self.assertLessEqual(datetime.date.fromisoformat(lastmod), build.utc_today())

    def test_image_sitemap_matches_product_urls_and_dates(self):
        product_urls = {u for u in self.rows if "/shop/" in u}
        self.assertEqual(set(self.image_rows), product_urls)
        self.assertEqual(
            {u: self.image_rows[u] for u in product_urls},
            {u: self.rows[u] for u in product_urls})
        root = read_xml("sitemap-images.xml")
        for node in root.findall("sm:url", IMAGE_NS):
            images = node.findall("image:image/image:loc", IMAGE_NS)
            self.assertTrue(images)
            for image in images:
                self.assertTrue(image.text.startswith("https://"), image.text)


@unittest.skipUnless(importlib.util.find_spec("requests"),
                     "requests is optional for the stdlib sitemap tests")
class SearchConsoleDiagnostics(unittest.TestCase):
    def test_inspection_classification_is_conservative(self):
        import nudge_google  # noqa: E402
        self.assertEqual(
            nudge_google.classify_index_state("PASS", "Submitted and indexed"),
            "indexed")
        self.assertEqual(
            nudge_google.classify_index_state("NEUTRAL", "Discovered - currently not indexed"),
            "discovered_but_not_indexed")
        self.assertEqual(
            nudge_google.classify_index_state("NEUTRAL", "Crawled - currently not indexed"),
            "crawled_but_not_indexed")
        self.assertEqual(
            nudge_google.classify_index_state("NEUTRAL", "Some future Google wording"),
            "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
