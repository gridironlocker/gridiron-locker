#!/usr/bin/env python3
"""Tests for the hardened trend-feed fetch path (src/trends.py).

Why this file exists
--------------------
Google News throttles GitHub Actions datacenter IPs unpredictably. On
2026-09-23 the 06:15 UTC refresh run (35827081394) failed with exit code 1
because all four collection feeds failed inside the same minute - same commit
had succeeded 15 hours earlier, so nothing but the network mood changed.
The fetch path now retries retryable statuses with backoff (session-level,
tested here only as "non-200 = provider failure") and falls back to Bing News
RSS per collection before declaring the feed dead. These tests pin that
behaviour without touching the network.

Run with either:
    python3 tests/test_trends_fetch.py
    python3 -m pytest tests/
"""
import datetime
import os
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import trends


GOOGLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Google News</title>
<item>
  <title>Browns name Shedeur Sanders the starter for Sunday - ESPN</title>
  <link>https://news.google.com/rss/articles/abc123</link>
  <pubDate>Tue, 22 Sep 2026 12:34:00 GMT</pubDate>
  <source url="https://www.espn.com">ESPN</source>
</item>
<item>
  <title>Myles Garrett quiet in practice - cleveland.com</title>
  <link>https://news.google.com/rss/articles/def456</link>
  <pubDate>Tue, 22 Sep 2026 09:00:00 GMT</pubDate>
  <source url="https://www.cleveland.com">cleveland.com</source>
</item>
</channel></rss>"""

# Bing News RSS: standard RSS 2.0, generally no per-item <source>, and no
# server-side when: window - hence the client-side WINDOW_DAYS filter.
NOW = datetime.datetime(2026, 9, 23, 12, 0, 0, tzinfo=datetime.timezone.utc)
BING_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Bing News</title>
<item>
  <title>Packers rally behind Jordan Love in fourth quarter</title>
  <link>https://example.com/packers-love</link>
  <pubDate>Wed, 23 Sep 2026 06:15:00 GMT</pubDate>
</item>
<item>
  <title>Preseason look at the Packers depth chart</title>
  <link>https://example.com/packers-preseason</link>
  <pubDate>Sat, 01 Aug 2026 18:00:00 GMT</pubDate>
</item>
<item>
  <title>Notes from Packers camp</title>
  <link>https://example.com/camp-notes</link>
  <pubDate>not a real date</pubDate>
</item>
</channel></rss>"""

EMPTY_RSS = (b'<?xml version="1.0" encoding="UTF-8"?>'
             b'<rss version="2.0"><channel><title>x</title></channel></rss>')


class FakeResp:
    def __init__(self, status=200, body=b""):
        self.status_code = status
        self.content = body


class FakeSession:
    """Plays a scripted list of responses/exceptions, recording URLs."""

    def __init__(self, plan):
        self.plan = list(plan)
        self.urls = []

    def get(self, url, timeout=30):
        self.urls.append(url)
        step = self.plan.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


class ParseTests(unittest.TestCase):
    def test_google_items_strip_source_suffix(self):
        items = trends.parse_google_items(ET.fromstring(GOOGLE_RSS))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["title"],
                         "Browns name Shedeur Sanders the starter for Sunday")
        self.assertEqual(items[0]["source"], "ESPN")
        self.assertTrue(items[1]["url"].endswith("def456"))

    def test_bing_items_enforce_window(self):
        items = trends.parse_bing_items(ET.fromstring(BING_RSS), now=NOW)
        titles = [i["title"] for i in items]
        # fresh item kept, August pre-window item dropped, bad-date item kept
        self.assertIn("Packers rally behind Jordan Love in fourth quarter", titles)
        self.assertNotIn("Preseason look at the Packers depth chart", titles)
        self.assertIn("Notes from Packers camp", titles)
        self.assertEqual(items[0]["source"], "")


class FetchTests(unittest.TestCase):
    def setUp(self):
        self._real = trends.SESSION

    def tearDown(self):
        trends.SESSION = self._real

    def fetch_with(self, plan, ckey="cleveland-browns"):
        fake = FakeSession(plan)
        trends.SESSION = fake
        return trends.fetch(ckey), fake.urls

    def test_google_healthy_short_circuits(self):
        items, urls = self.fetch_with([FakeResp(200, GOOGLE_RSS)])
        self.assertEqual(len(items), 2)
        self.assertEqual(len(urls), 1)
        self.assertIn("news.google.com", urls[0])

    def test_google_429_falls_back_to_bing(self):
        items, urls = self.fetch_with([FakeResp(429), FakeResp(200, BING_RSS)],
                                      ckey="green-bay-packers")
        self.assertEqual(len(items), 2)  # 3 minus the out-of-window one
        self.assertIn("news.google.com", urls[0])
        self.assertIn("bing.com", urls[1])
        self.assertTrue(any("Jordan Love" in i["title"] for i in items))

    def test_empty_google_feed_is_treated_as_failure(self):
        # Google sometimes answers a throttle with 200 + a hollow feed.
        items, urls = self.fetch_with([FakeResp(200, EMPTY_RSS),
                                       FakeResp(200, BING_RSS)],
                                      ckey="green-bay-packers")
        self.assertTrue(items)
        self.assertEqual(len(urls), 2)

    def test_transport_error_falls_back(self):
        items, urls = self.fetch_with([ConnectionError("tls eof"),
                                       FakeResp(200, BING_RSS)],
                                      ckey="green-bay-packers")
        self.assertTrue(items)
        self.assertEqual(len(urls), 2)

    def test_all_providers_failed_returns_empty(self):
        items, urls = self.fetch_with([FakeResp(503), FakeResp(429)])
        self.assertEqual(items, [])
        self.assertEqual(len(urls), 2)

    def test_unparseable_body_falls_back(self):
        items, urls = self.fetch_with([FakeResp(200, b"<html>nope</html>"),
                                       FakeResp(200, BING_RSS)],
                                      ckey="green-bay-packers")
        self.assertTrue(items)
        self.assertEqual(len(urls), 2)

    def test_no_session_is_clean_failure(self):
        trends.SESSION = None
        self.assertEqual(trends.fetch("dallas-cowboys"), [])

    def test_bing_url_uses_collection_query(self):
        self.assertIn("Michigan%20Wolverines%20football",
                      trends.bing_feed_url("michigan"))


if __name__ == "__main__":
    unittest.main()
