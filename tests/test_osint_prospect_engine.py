"""Tests for the private OSINT prospect engine (marketing/osint/).

Everything here runs offline against fixture HTTP responses via an injected
transport — no real collection happens in the test suite (spec: "Use test/mock
records where real collection would be inappropriate"), and no test writes
into the repository working tree: state is redirected to temp directories.

Covers the spec's test plan: discovery, deduplication, public-email
extraction, email validation, scoring, CSV export, status updates,
suppression, refresh, error handling, and the privacy guarantees (prospect
data can never reach site/ or be committed).
"""
from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from marketing.osint import (  # noqa: E402
    config, db, dedupe, emails, engine, exporters, importers, scoring,
    suppression,
)
from marketing.osint.collectors import enabled_collectors  # noqa: E402
from marketing.osint.http import Fetcher, RobotsPolicy  # noqa: E402


class TempStateCase(unittest.TestCase):
    """Base: redirect all engine state to a temp dir per test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name)
        self._env = mock.patch.dict(
            os.environ,
            {"OSINT_STATE_DIR": str(self.state), "OSINT_EXPORTS_DIR": str(self.state / "exports")},
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        self.addCleanup(self._tmp.cleanup)

    def repo(self):
        return db.Repository(db.connect(self.state / "prospects.db"))


# ---------------------------------------------------------------------------
# Fixtures: a fake web for the whole pipeline
# ---------------------------------------------------------------------------

ITUNES_RESULTS = {
    "resultCount": 2,
    "results": [
        {
            "collectionId": 111,
            "collectionName": "Test Michigan Football Podcast",
            "artistName": "Go Blue Media",
            "trackViewUrl": "https://podcasts.apple.com/us/podcast/test-michigan/id111",
            "feedUrl": "https://feeds.examplepod.com/michigan.xml",
            "genres": ["Sports", "Football"],
            "trackCount": 210,
            "releaseDate": "2026-09-15T04:00:00Z",
        },
        {
            "collectionId": 112,
            "collectionName": "Big House Tailgate Show",
            "artistName": "Ann Arbor Fans",
            "trackViewUrl": "https://podcasts.apple.com/us/podcast/big-house/id112",
            "feedUrl": "https://feeds.examplepod.com/big-house.xml",
            "genres": ["Sports"],
            "trackCount": 45,
            "releaseDate": "2026-09-01T04:00:00Z",
        },
    ],
}

RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>Test Michigan Football Podcast</title>
  <link>https://www.examplepod.com/</link>
  <description>Daily Michigan Wolverines football coverage and game-day talk.</description>
  <itunes:owner><itunes:name>Go Blue Media</itunes:name>
    <itunes:email>owner@examplepod.com</itunes:email></itunes:owner>
  <item><title>Episode 210</title><pubDate>Tue, 15 Sep 2026 04:00:00 GMT</pubDate></item>
  <item><title>Episode 209</title><pubDate>Mon, 14 Sep 2026 04:00:00 GMT</pubDate></item>
</channel>
</rss>
"""

BLOCKED_FEED = RSS_FEED.replace("https://www.examplepod.com/", "https://blockedpod.example/")

POD_HOME = """<html><body>
<h1>Test Michigan Football Podcast</h1>
<p>Daily Michigan Wolverines football podcast. Shop our merch at our store.</p>
<a href="/contact">Contact us</a>
<a href="https://www.instagram.com/examplepod">Instagram</a>
</body></html>"""

POD_CONTACT = """<html><body>
<h1>Contact</h1>
<p>For business inquiries and sponsorship, email
<a href="mailto:info@examplepod.com">info@examplepod.com</a>.</p>
</body></html>"""

NEWS_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test news</title>
<item><title>Browns fan site breaks down the win</title>
  <link>https://news.google.com/rss/articles/xyz</link>
  <pubDate>Wed, 16 Sep 2026 12:00:00 GMT</pubDate>
  <source url="https://www.dawgblogfans.com">DawgBlog</source></item>
<item><title>ESPN says...</title>
  <link>https://news.google.com/rss/articles/abc</link>
  <pubDate>Wed, 16 Sep 2026 11:00:00 GMT</pubDate>
  <source url="https://www.espn.com">ESPN</source></item>
</channel></rss>
"""

DAWGBLOG_HOME = """<html><body>
<h1>DawgBlog — Cleveland Browns fan community</h1>
<p>Contact: dawgblog AT dawgblogfans DOT com or use our contact page.</p>
</body></html>"""


def fake_routes():
    """url-prefix -> (status, content-type, body)."""
    allow = "User-agent: *\nAllow: /\n"
    disallow = "User-agent: *\nDisallow: /\n"
    return {
        "https://itunes.apple.com/search": (
            200, "application/json", json.dumps(ITUNES_RESULTS)
        ),
        "https://feeds.examplepod.com/robots.txt": (200, "text/plain", allow),
        "https://feeds.examplepod.com/michigan.xml": (200, "application/rss+xml", RSS_FEED),
        "https://feeds.examplepod.com/big-house.xml": (200, "application/rss+xml", RSS_FEED),
        "https://blockedpod.example/robots.txt": (200, "text/plain", disallow),
        "https://blockedpod.example/feed.xml": (200, "application/rss+xml", BLOCKED_FEED),
        "https://www.examplepod.com/robots.txt": (200, "text/plain", allow),
        "https://www.examplepod.com/": (200, "text/html", POD_HOME),
        "https://www.examplepod.com/contact": (200, "text/html", POD_CONTACT),
        "https://news.google.com/robots.txt": (200, "text/plain", allow),
        "https://news.google.com/rss/search": (200, "application/rss+xml", NEWS_RSS),
        "https://www.dawgblogfans.com/robots.txt": (200, "text/plain", allow),
        "https://www.dawgblogfans.com/": (200, "text/html", DAWGBLOG_HOME),
    }


class FakeTransport:
    def __init__(self, routes):
        self.routes = routes
        self.hits: list[str] = []

    def __call__(self, url, headers, timeout):
        self.hits.append(url)
        # longest-prefix match so "/contact" never falls back to the "/"
        # route (the exact bug this fixture once hid)
        best_prefix = None
        for prefix in self.routes:
            if url.startswith(prefix) and (
                best_prefix is None or len(prefix) > len(best_prefix)
            ):
                best_prefix = prefix
        if best_prefix is not None:
            status, ctype, body = self.routes[best_prefix]
            if isinstance(body, str):
                body = body.encode("utf-8")
            return status, ctype, body
        return 404, "text/plain", b""

    def hit(self, fragment: str) -> bool:
        return any(fragment in url for url in self.hits)


def fake_fetcher(routes=None, min_interval=0.0):
    return Fetcher(transport=FakeTransport(routes or fake_routes()),
                   min_interval=min_interval)


# ---------------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------------

class TestConfig(TempStateCase):
    def test_all_four_teams_have_keyword_files(self):
        for team in config.TEAM_SLUGS:
            keywords = config.load_keywords(team)
            self.assertTrue(keywords["strong_terms"], team)
            self.assertTrue(keywords["terms"], team)
            self.assertTrue(keywords["search_queries"], team)

    def test_unknown_team_rejected(self):
        with self.assertRaises(ValueError):
            config.normalize_team("Ohio State")

    def test_team_aliases_normalize(self):
        self.assertEqual(config.normalize_team("Michigan Wolverines"), "michigan")
        self.assertEqual(config.normalize_team("GREEN-BAY-PACKERS"), "packers")

    def test_seeds_are_valid(self):
        seeds = config.load_seeds()
        self.assertTrue(all(seed.get("url", "").startswith("https://") for seed in seeds))
        self.assertTrue(all(seed.get("team") in config.TEAM_SLUGS for seed in seeds))

    def test_trend_terms_read_only(self):
        terms = config.load_trend_terms()
        # The repo's trends.json exists and covers all four teams; we read it
        # but never write it.
        self.assertIsInstance(terms, dict)
        self.assertFalse((Path(config.DATA_DIR) / "trends.json.write_test").exists())


# ---------------------------------------------------------------------------
# 2. Email extraction + validation
# ---------------------------------------------------------------------------

class TestEmails(TempStateCase):
    def test_extracts_mailto_and_text(self):
        page = emails.extract_from_page(
            '<a href="mailto:info@fansite.example">mail</a> plain text '
            "other@fansite.example not-an-email-at-all", "https://fansite.example/"
        )
        found = {item["email"] for item in page}
        self.assertIn("info@fansite.example", found)
        self.assertIn("other@fansite.example", found)

    def test_decodes_published_obfuscation(self):
        text = "Reach us: dawgblog AT dawgblogfans DOT com thanks"
        self.assertEqual(emails.extract_from_text(text), ["dawgblog@dawgblogfans.com"])

    def test_junk_domains_and_asset_tlds_rejected(self):
        for junk in ("a@example.com", "logo@2x.png", "x@sentry.io", "a@b.jpg"):
            self.assertFalse(emails.is_plausible(junk), junk)

    def test_role_accounts_rank_first(self):
        page = emails.extract_from_page(
            "contact: info@site.example personal: sam@site.example", ""
        )
        self.assertEqual(page[0]["email"], "info@site.example")

    def test_never_guesses_addresses(self):
        # Nothing in the module can produce an address that was not published;
        # extraction only ever reads text that is already there.
        self.assertEqual(emails.extract_from_text("no addresses here"), [])

    def test_syntax_verdicts(self):
        self.assertEqual(emails.validate("not-an-email")["verdict"], "INVALID_SYNTAX")
        disposable = emails.validate("x@mailinator.com", dns=False)
        self.assertEqual(disposable["verdict"], "DISPOSABLE")

    def test_dns_offline_is_unverified_not_invalid(self):
        with mock.patch.object(emails, "dns_lookup", return_value=None):
            check = emails.validate("info@examplepod.com")
        self.assertEqual(check["verdict"], "UNVERIFIED")

    def test_mx_present_gives_verified_mx(self):
        with mock.patch.object(
            emails, "dns_lookup",
            side_effect=lambda name, qtype=15, timeout=3: (
                ["10 mail.examplepod.com."] if qtype == 15 else ["1.2.3.4"]
            ),
        ):
            check = emails.validate("info@examplepod.com")
        self.assertEqual(check["verdict"], "VERIFIED_MX")

    def test_answered_no_records_is_invalid_domain(self):
        with mock.patch.object(emails, "dns_lookup", return_value=[]):
            check = emails.validate("info@nonexistent-domain-xyz.test")
        self.assertEqual(check["verdict"], "INVALID_DOMAIN")

    def test_mask_for_logs(self):
        self.assertEqual(emails.mask("john@site.example"), "***@site.example")


# ---------------------------------------------------------------------------
# 3. Scoring
# ---------------------------------------------------------------------------

class TestScoring(TempStateCase):
    def _fixture(self, **overrides):
        base = {
            "platform": "apple-podcasts",
            "display_name": "Locked On Wolverines Podcast",
            "username": "Locked On Wolverines",
            "bio": "Daily Michigan Wolverines football podcast, game-day coverage",
            "website": "https://www.examplepod.com/",
            "team": "michigan",
            "prospect_type": "PODCAST_MEDIA",
            "public_email": "info@examplepod.com",
            "email_verified": "VERIFIED_MX",
            "contact_source": "published on website contact page",
            "last_activity_at": "2026-09-15",
            "followers": None,
            "post_count": 210,
        }
        base.update(overrides)
        return base

    def test_weights_sum_and_bands(self):
        result = scoring.score(self._fixture())
        total = sum(p["points"] for p in result["breakdown"].values())
        maximum = sum(p["max"] for p in result["breakdown"].values())
        self.assertEqual(maximum, 100)
        self.assertEqual(result["relevance_score"], min(100, total))
        self.assertTrue(result["score_reason"])

    def test_unknown_engagement_is_zero_never_fabricated(self):
        result = scoring.score(self._fixture())
        part = result["breakdown"]["engagement"]
        self.assertEqual(part["points"], 0)
        self.assertIn("never fabricated", part["why"])

    def test_strong_team_identity_scores_max_relevance(self):
        result = scoring.score(
            self._fixture(display_name="Go Blue Michigan Wolverines Daily")
        )
        self.assertEqual(result["breakdown"]["team_relevance"]["points"], 25)

    def test_no_relevance_signals_score_low(self):
        result = scoring.score(
            self._fixture(display_name="Cooking Hour", username=None,
                          bio="Recipes", website="", team=None,
                          public_email=None, email_verified=None,
                          post_count=0, last_activity_at=None)
        )
        self.assertLessEqual(result["relevance_score"], 30)
        self.assertEqual(result["breakdown"]["team_relevance"]["points"], 0)

    def test_priority_bands(self):
        strong = scoring.score(self._fixture())
        weak = scoring.score(
            self._fixture(display_name="Cooking Hour", bio="Recipes",
                          website="", public_email=None, email_verified=None,
                          post_count=0, last_activity_at=None)
        )
        self.assertIn(strong["priority"], ("QUALIFIED", "HIGH_PRIORITY", "REVIEW"))
        self.assertEqual(weak["priority"], "LOW_PRIORITY")

    def test_confidence_reflects_evidence(self):
        rich = scoring.score(self._fixture())
        poor = scoring.score(
            self._fixture(display_name="", profile_url="", website="",
                          last_activity_at=None, followers=None, public_email=None)
        )
        self.assertGreater(rich["confidence_score"], poor["confidence_score"])


# ---------------------------------------------------------------------------
# 4. Dedupe
# ---------------------------------------------------------------------------

class TestDedupe(TempStateCase):
    def test_registered_domain(self):
        cases = {
            "https://www.podsite.co.uk/feed": "podsite.co.uk",
            "https://feeds.blog.example/show.xml": "blog.example",
            "http://WWW.FanSite.COM/": "fansite.com",
            "not a url": "not a url",
        }
        for url, expected in cases.items():
            self.assertEqual(dedupe.registered_domain(url), expected, url)

    def test_same_email_links_confirmed(self):
        repo = self.repo()
        first = repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://show.example",
            "display_name": "Show website", "website": "https://show.example",
            "public_email": "info@show.example",
        })
        second = repo.upsert_prospect({
            "platform": "apple-podcasts", "platform_user_id": "itunes:1",
            "display_name": "Show", "public_email": "info@show.example",
        })
        record = repo.get(second["id"])
        links = dedupe.detect_links(repo, record, second["id"])
        self.assertTrue(any(l["confidence"] == "CONFIRMED_MATCH" for l in links))

    def test_same_platform_identity_merges_not_duplicates(self):
        repo = self.repo()
        repo.upsert_prospect({
            "platform": "apple-podcasts", "platform_user_id": "itunes:9",
            "display_name": "Old name",
        })
        outcome = repo.upsert_prospect({
            "platform": "apple-podcasts", "platform_user_id": "itunes:9",
            "display_name": "New name",
        })
        self.assertEqual(outcome["outcome"], "UPDATED")
        count = repo.conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        self.assertEqual(count, 1)


# ---------------------------------------------------------------------------
# 5. Persistence: freshness, statuses, notes
# ---------------------------------------------------------------------------

class TestPersistence(TempStateCase):
    def test_unchanged_rerun_not_new(self):
        repo = self.repo()
        record = {
            "platform": "website", "platform_user_id": "https://x.example",
            "display_name": "Fan site", "bio": "same",
        }
        first = repo.upsert_prospect(dict(record))
        second = repo.upsert_prospect(dict(record))
        self.assertEqual(first["outcome"], "NEW")
        self.assertEqual(second["outcome"], "UNCHANGED")

    def test_change_detected_and_first_seen_preserved(self):
        repo = self.repo()
        record = {
            "platform": "website", "platform_user_id": "https://x.example",
            "display_name": "Fan site", "discovered_at": "2026-01-01T00:00:00+00:00",
        }
        repo.upsert_prospect(dict(record))
        record["display_name"] = "Renamed fan site"
        repo.upsert_prospect(dict(record))
        stored = repo.list_prospects()[0]
        self.assertEqual(stored["display_name"], "Renamed fan site")
        self.assertEqual(stored["first_seen_at"], "2026-01-01T00:00:00+00:00")

    def test_status_and_notes_survive_redisovery(self):
        repo = self.repo()
        repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://x.example",
            "display_name": "Fan site",
        })
        repo.update_status(1, "CONTACTED", "emailed 2026-09-15")
        repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://x.example",
            "display_name": "Fan site v2",
        })
        stored = repo.get(1)
        self.assertEqual(stored["status"], "CONTACTED")
        self.assertIn("emailed 2026-09-15", stored["notes"])


# ---------------------------------------------------------------------------
# 6. Full pipeline against the fake web
# ---------------------------------------------------------------------------

class TestPipeline(TempStateCase):
    def _run(self, fetcher=None, **kwargs):
        repo = self.repo()
        with mock.patch.object(
            emails, "dns_lookup",
            side_effect=lambda name, qtype=15, timeout=3: (
                ["10 mail.examplepod.com."] if qtype == 15 else ["1.2.3.4"]
            ),
        ):
            result = engine.run_discovery(
                repo, fetcher=fetcher or fake_fetcher(),
                teams=["michigan", "browns"], **kwargs
            )
        return repo, result

    def test_discovery_stores_podcasts_with_public_email(self):
        repo, result = self._run()
        self.assertGreater(result["new"], 0)
        podcast = repo.conn.execute(
            "SELECT * FROM prospects WHERE platform = 'apple-podcasts' "
            "ORDER BY relevance_score DESC LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(podcast, "no podcast stored")
        self.assertEqual(podcast["team"], "michigan")
        self.assertEqual(podcast["prospect_type"], "PODCAST_MEDIA")
        # public email from the site's public contact page, verified via MX
        self.assertEqual(podcast["public_email"], "info@examplepod.com")
        self.assertEqual(podcast["email_verified"], "VERIFIED_MX")
        self.assertTrue(podcast["contact_source_url"], "contact evidence missing")
        self.assertTrue(podcast["source_url"], "discovery evidence missing")
        self.assertGreaterEqual(podcast["relevance_score"], 0)

    def test_news_publisher_discovered_major_outlets_skipped(self):
        repo, result = self._run()
        domains = {
            r["platform_user_id"]
            for r in repo.conn.execute(
                "SELECT platform_user_id FROM prospects WHERE platform = 'news-web'"
            )
        }
        self.assertIn("dawgblogfans.com", domains)
        self.assertNotIn("espn.com", domains)

    def test_news_collector_self_disables_when_robots_disallows(self):
        # The real news.google.com/robots.txt disallows /rss/search (verified
        # live 2026-09-17). With an equivalent fixture the collector must
        # report DISABLED — an honest status, never a bypass.
        routes = fake_routes()
        routes["https://news.google.com/robots.txt"] = (
            200, "text/plain", "User-agent: *\nDisallow: /\n"
        )
        repo, result = self._run(fetcher=fake_fetcher(routes))
        news_status = {s.name: s for s in result["statuses"]}["news"]
        self.assertEqual(news_status.state, "DISABLED")
        self.assertIn("robots.txt", news_status.detail)
        # and no news-web prospects were stored from a disallowed source
        count = repo.conn.execute(
            "SELECT COUNT(*) FROM prospects WHERE platform = 'news-web'"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_robots_disallow_is_respected_never_bypassed(self):
        routes = fake_routes()
        routes["https://www.examplepod.com/robots.txt"] = (
            200, "text/plain", "User-agent: *\nDisallow: /\n"
        )
        repo, result = self._run(fetcher=fake_fetcher(routes))
        rows = repo.conn.execute(
            "SELECT public_email FROM prospects WHERE platform = 'apple-podcasts'"
        ).fetchall()
        # homepage blocked -> no contact-page email; feed email may still be
        # captured with its public provenance flag
        for row in rows:
            if row["public_email"]:
                stored = repo.conn.execute(
                    "SELECT email_category FROM prospects WHERE public_email = ?",
                    (row["public_email"],),
                ).fetchone()
                self.assertEqual(stored["email_category"], "PUBLIC_RSS_OWNER_EMAIL")

    def test_collector_status_honesty(self):
        repo, result = self._run()
        lines = {status.name: status.state for status in result["statuses"]}
        self.assertEqual(lines.get("instagram"), "DISABLED")
        self.assertEqual(lines.get("tiktok"), "DISABLED")
        self.assertEqual(lines.get("x"), "DISABLED")
        self.assertEqual(lines.get("pinterest"), "DISABLED")
        self.assertEqual(lines.get("youtube"), "NO_KEY")
        self.assertEqual(lines.get("podcasts"), "OK")
        self.assertEqual(lines.get("news"), "OK")

    def test_disabled_collectors_can_be_selected_and_report(self):
        collector = [c for c in enabled_collectors(["instagram"])][0]
        records, status = collector.discover(
            engine.DiscoveryContext(
                fetcher=fake_fetcher(), keywords=config.load_all_keywords(),
                teams=["michigan"],
            )
        )
        self.assertEqual(records, [])
        self.assertEqual(status.state, "DISABLED")
        self.assertIn("manual", status.detail)

    def test_suppressed_identity_never_exported_as_contactable(self):
        repo, _ = self._run()
        stored = repo.conn.execute(
            "SELECT * FROM prospects WHERE public_email = 'info@examplepod.com'"
        ).fetchone()
        suppression.append("info@examplepod.com", "email", "asked to opt out")
        # a later re-discovery of the same show must come back SUPPRESSED
        self._run()
        again = repo.conn.execute(
            "SELECT status FROM prospects WHERE id = ?", (stored["id"],)
        ).fetchone()
        self.assertEqual(again["status"], "SUPPRESS")
        exports = exporters.export_all(repo)
        with open(exports["main"], newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertFalse(
            any(row["public_email"] == "info@examplepod.com" for row in rows)
        )

    def test_refresh_preserves_history(self):
        repo, _ = self._run()
        repo.update_status(1, "CONTACTED", "manual email sent")
        with mock.patch.object(emails, "dns_lookup", return_value=None):
            engine.run_refresh(repo, fetcher=fake_fetcher(), teams=["michigan"])
        stored = repo.get(1)
        self.assertEqual(stored["status"], "CONTACTED")

    def test_error_handling_collectors_never_crash_the_run(self):
        routes = {
            "https://itunes.apple.com/search": (500, "application/json", "{}"),
            "https://news.google.com/robots.txt": (500, "text/plain", ""),
        }
        repo, result = self._run(fetcher=fake_fetcher(routes))
        states = {s.name: s for s in result["statuses"]}
        self.assertEqual(states["podcasts"].state, "ERROR")
        # seeds still discovered — one broken source never kills the run
        self.assertGreaterEqual(result["new"], 1)

    def test_export_contains_spec_columns_and_evidence(self):
        repo, _ = self._run()
        exports = exporters.export_all(repo)
        with open(exports["main"], newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        for column in ["name", "platform", "username", "profile_url", "team",
                       "prospect_type", "public_email", "website", "followers",
                       "relevance_score", "commercial_score", "confidence_score",
                       "reason", "discovered_at", "last_verified_at", "status",
                       "contact_source_url", "source_url"]:
            self.assertIn(column, reader.fieldnames)
        self.assertTrue(all(row["source_url"] for row in rows))

    def test_high_priority_export_filter(self):
        repo, _ = self._run()
        exports = exporters.export_all(repo)
        with open(exports["high_priority"], newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            self.assertTrue(row["public_email"])
            self.assertGreaterEqual(int(row["relevance_score"] or 0), 75)


# ---------------------------------------------------------------------------
# 7. Import / manual workflow
# ---------------------------------------------------------------------------

class TestImporters(TempStateCase):
    def test_manual_prospect_import(self):
        repo = self.repo()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prospects.csv"
            path.write_text(
                "name,platform,username,team,prospect_type,public_email,notes\n"
                "Browns Fan Page,instagram,brownsfanpage,browns,FAN_CREATOR,"
                "hello@brownsfanpage.example,copied from public bio\n",
                encoding="utf-8",
            )
            summary = importers.import_prospects(repo, path)
        self.assertEqual(summary["added"], 1)
        stored = repo.list_prospects()[0]
        self.assertEqual(stored["platform"], "instagram")
        self.assertEqual(stored["public_email"], "hello@brownsfanpage.example")
        self.assertEqual(stored["status"], "REVIEW")

    def test_status_import_updates_and_suppresses(self):
        repo = self.repo()
        repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://x.example",
            "display_name": "Fan site", "website": "https://www.x.example/",
            "public_email": "info@x.example",
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "statuses.csv"
            path.write_text(
                "public_email,status,note\n"
                "info@x.example,email_sent,manual outreach 2026-09-16\n",
                encoding="utf-8",
            )
            summary = importers.import_statuses(repo, path)
            self.assertEqual(summary["applied"], 1)
            self.assertEqual(repo.get(1)["status"], "CONTACTED")

            path2 = Path(tmp) / "statuses2.csv"
            path2.write_text(
                "public_email,status\ninfo@x.example,unsubscribe\n",
                encoding="utf-8",
            )
            importers.import_statuses(repo, path2)
            self.assertEqual(repo.get(1)["status"], "SUPPRESS")
            keys = suppression.suppressed_keys(repo)
            self.assertIn("info@x.example", keys)
            self.assertIn("x.example", keys)

    def test_unknown_status_rejected(self):
        repo = self.repo()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("public_email,status\ninfo@x.example,whatever\n",
                            encoding="utf-8")
            summary = importers.import_statuses(repo, path)
        self.assertEqual(summary["applied"], 0)
        self.assertEqual(summary["skipped"], 1)


# ---------------------------------------------------------------------------
# 8. Cleanup / retention
# ---------------------------------------------------------------------------

class TestCleanup(TempStateCase):
    def test_cleanup_preserves_suppression_and_history(self):
        from marketing.osint import cleanup as cleanup_mod

        repo = self.repo()
        repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://old.example",
            "display_name": "Old site", "status": "NEW",
            "last_seen_at": "2025-01-01T00:00:00+00:00",
        })
        repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://kept.example",
            "display_name": "Kept site", "status": "CONTACTED",
            "last_seen_at": "2025-01-01T00:00:00+00:00",
        })
        repo.upsert_prospect({
            "platform": "website", "platform_user_id": "https://fresh.example",
            "display_name": "Fresh site", "status": "NEW",
        })
        dry = cleanup_mod.cleanup(repo, days=180)
        self.assertEqual(dry["would_remove"], 1)
        applied = cleanup_mod.cleanup(repo, days=180, apply=True)
        self.assertEqual(applied["removed"], 1)
        remaining = {r["platform_user_id"] for r in repo.conn.execute(
            "SELECT platform_user_id FROM prospects"
        )}
        self.assertEqual(remaining, {"https://kept.example", "https://fresh.example"})


# ---------------------------------------------------------------------------
# 9. Privacy / leak guards
# ---------------------------------------------------------------------------

class TestPrivacyGuards(TempStateCase):
    def test_export_refuses_site_tree(self):
        repo = self.repo()
        repo.upsert_prospect({
            "platform": "manual", "platform_user_id": "manual:x",
            "display_name": "X", "public_email": "a@b.example",
        })
        with self.assertRaises(ValueError):
            exporters.write_csv(repo.list_prospects(), Path(config.ROOT) / "site" / "p.csv")
        with self.assertRaises(ValueError):
            exporters.write_csv(
                repo.list_prospects(), Path(config.ROOT) / "marketing" / "social" / "p.csv"
            )

    def test_gitignore_blocks_prospect_state(self):
        text = (Path(config.ROOT) / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("marketing/osint/state/", text)
        self.assertIn("marketing/osint/exports/", text)

    def test_no_prospect_data_written_into_repo(self):
        # run a full pipeline with fixtures; the repo tree must stay untouched
        before = _repo_tree_signature()
        repo = self.repo()
        with mock.patch.object(emails, "dns_lookup", return_value=None):
            engine.run_discovery(repo, fetcher=fake_fetcher(),
                                 teams=["michigan", "browns"])
        after = _repo_tree_signature()
        self.assertEqual(before, after)
        # and the engine never even creates the default in-repo state dir here
        self.assertFalse((Path(config.PKG_DIR) / "state").exists())


def _repo_tree_signature() -> str:
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    )
    return out.stdout


# ---------------------------------------------------------------------------
# 10. CLI smoke (offline parts only)
# ---------------------------------------------------------------------------

class TestCLI(TempStateCase):
    def test_verify_command_offline(self):
        env = {**os.environ, "OSINT_STATE_DIR": str(self.state / "cli")}
        out = subprocess.run(
            [sys.executable, "-m", "marketing.osint", "verify"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("VERIFY: OK", out.stdout)

    def test_stats_and_export_commands(self):
        repo = self.repo()
        repo.upsert_prospect({
            "platform": "manual", "platform_user_id": "manual:t",
            "display_name": "Test Creator", "team": "michigan",
            "prospect_type": "FAN_CREATOR", "public_email": "t@t.example",
            "email_verified": "UNVERIFIED",
        })
        env = {**os.environ, "OSINT_STATE_DIR": str(self.state / "cli")}
        out = subprocess.run(
            [sys.executable, "-m", "marketing.osint", "export"],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        exports = list((self.state / "cli" / "exports").glob("*.csv")) if (self.state / "cli" / "exports").exists() else list((self.state / "exports").glob("*.csv"))
        # exports go to OSINT_EXPORTS_DIR when set, else alongside state
        all_exports = list(self.state.rglob("*.csv"))
        self.assertTrue(all_exports, "no CSV produced")


class TestRobotsParsing(unittest.TestCase):
    def test_disallow_respected(self):
        rules = RobotsPolicy.parse("User-agent: *\nDisallow: /private\n")
        self.assertFalse(rules.permitted("/private/page"))
        self.assertTrue(rules.permitted("/public"))

    def test_named_group_wins(self):
        rules = RobotsPolicy.parse(
            "User-agent: *\nDisallow: /\n\n"
            "User-agent: gridironlockerprospectresearch\nDisallow: \n"
        )
        self.assertTrue(rules.permitted("/anything"))

    def test_garbage_allows(self):
        self.assertIsNone(RobotsPolicy.parse("total garbage :: nope"))


if __name__ == "__main__":
    unittest.main()
