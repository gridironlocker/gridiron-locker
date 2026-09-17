"""Tests for the OSINT public/private split.

* the PUBLIC surface — ``marketing/osint/page/prospects.json`` (committed)
  and the rendered ``ops/prospects/`` dashboard (robots-disallowed, noindex,
  password-gated) — must be aggregate-only: counts, fixed vocabularies and
  timestamps, never a prospect-identifying value;
* the PRIVATE surface — ``python3 -m marketing.osint ui`` — shows full rows
  but only on localhost behind a per-launch token, and never writes outside
  ``OSINT_STATE_DIR``;
* ``audit.py`` proves both halves on the real tree.

Everything runs offline: fixture databases in temp dirs, the dashboard on an
ephemeral localhost port, no network, no repository mutation.
"""
from __future__ import annotations

import contextlib
import http.client
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from marketing.osint import audit as audit_mod  # noqa: E402
from marketing.osint import config, db, page as page_mod  # noqa: E402
from marketing.osint import ui as ui_mod  # noqa: E402
from tests.testutil import snapshot_tree  # noqa: E402

import prospects_page  # noqa: E402

#: Fixed test password (NOT the real page password — fixtures only).
TEST_PASSWORD = "test-page-pass-12"

LEAK_STRINGS = (
    "Test Michigan Football Podcast",
    "Big House Tailgate Show",
    "gobluemedia",
    "info@examplepod.com",
    "contact@dawgblogfans.com",
    "examplepod.com",
    "dawgblogfans.com",
    "atlantis",
)


class TempStateCase(unittest.TestCase):
    """Base: redirect engine state AND page output to temp dirs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state = Path(self._tmp.name)
        self._env = mock.patch.dict(
            os.environ,
            {
                "OSINT_STATE_DIR": str(self.state),
                "OSINT_EXPORTS_DIR": str(self.state / "exports"),
                "OSINT_PAGE_DIR": str(self.state / "page"),
            },
        )
        self._env.start()
        self.addCleanup(self._env.stop)
        self.addCleanup(self._tmp.cleanup)

    def repo(self):
        return db.Repository(db.connect(self.state / "prospects.db"))

    def seed(self, repo):
        rows = [
            dict(
                platform="apple-podcasts", platform_user_id="pod-1",
                username="gobluemedia", display_name="Test Michigan Football Podcast",
                profile_url="https://podcasts.example/p1",
                website="https://www.examplepod.com/", team="michigan",
                prospect_type="PODCAST_MEDIA", public_email="info@examplepod.com",
                email_verified="VERIFIED_MX", followers=1200, post_count=210,
                relevance_score=82, commercial_score=70, confidence_score=60,
                score_breakdown={"team_relevance": {"points": 22, "max": 25}},
                score_reason="fixture", priority="QUALIFIED", status="NEW",
            ),
            dict(
                platform="website", platform_user_id="site-1",
                username="dawgblog", display_name="Big House Tailgate Show",
                website="https://www.dawgblogfans.com/", team="browns",
                prospect_type="BLOG_WEBSITE", public_email="contact@dawgblogfans.com",
                email_verified="UNVERIFIED", followers=800, post_count=90,
                relevance_score=91, commercial_score=80, confidence_score=55,
                score_breakdown={}, score_reason="fixture",
                priority="HIGH_PRIORITY", status="REVIEW",
            ),
            dict(
                platform="manual", platform_user_id="man-1",
                username="bluefan99", display_name="Blue Fan Clips",
                team="michigan", prospect_type="FAN_CREATOR",
                relevance_score=55, commercial_score=40, confidence_score=30,
                score_breakdown={}, score_reason="fixture",
                priority="LOW_PRIORITY", status="NEW",
            ),
            dict(
                platform="manual", platform_user_id="man-2",
                username="strange", display_name="Weird Row",
                team="atlantis", prospect_type="ALIEN",
                relevance_score=70, commercial_score=10, confidence_score=10,
                score_breakdown={}, score_reason="fixture",
                priority="BOGUS", status="CUSTOMER",
            ),
        ]
        ids = [repo.upsert_prospect(row)["id"] for row in rows]
        run_id = repo.start_run("discover")
        repo.finish_run(run_id, new=4, updated=0, unchanged=1, suppressed_hits=0)
        return ids


# ---------------------------------------------------------------------------
# Committed page data: aggregate-only
# ---------------------------------------------------------------------------

class PageDataTest(TempStateCase):
    def test_aggregates_match_database(self):
        repo = self.repo()
        self.seed(repo)
        data = page_mod.build_page_data(repo, TEST_PASSWORD, generated_at="2026-09-17T00:00:00+00:00")
        self.assertEqual(data["totals"]["prospects"], 4)
        self.assertEqual(data["totals"]["with_public_email"], 2)
        self.assertEqual(data["totals"]["verified_email"], 1)
        self.assertEqual(data["by_team"]["michigan"], 2)
        self.assertEqual(data["by_team"]["browns"], 1)
        self.assertEqual(data["by_team"]["packers"], 0)
        self.assertEqual(data["by_team"]["cowboys"], 0)
        self.assertEqual(data["by_type"]["PODCAST_MEDIA"], 1)
        self.assertEqual(data["by_priority"]["HIGH_PRIORITY"], 1)
        self.assertEqual(data["by_status"]["CUSTOMER"], 1)
        # untrusted free-text values fold into "other", never published raw
        self.assertEqual(data["by_team"]["other"], 1)
        self.assertEqual(data["by_type"]["other"], 1)
        self.assertEqual(data["by_priority"]["other"], 1)
        self.assertEqual(data["last_run"]["new"], 4)
        self.assertEqual(data["last_run"]["mode"], "discover")

    def test_page_data_contains_no_prospect_values(self):
        repo = self.repo()
        self.seed(repo)
        data = page_mod.build_page_data(repo, TEST_PASSWORD)
        dumped = json.dumps(data, sort_keys=True)
        for leak in LEAK_STRINGS:
            self.assertNotIn(leak, dumped)
        self.assertEqual(page_mod.validate_page_data(data), [])
        self.assertNotEqual(page_mod.validate_page_data({"totals": {}}), [])

    def test_password_required_and_minimum_length(self):
        from marketing.osint import __main__ as cli

        with mock.patch.dict(os.environ):
            os.environ.pop(page_mod.PASSWORD_ENV_VAR, None)
            with self.assertRaises(SystemExit):
                page_mod.require_password()
            os.environ[page_mod.PASSWORD_ENV_VAR] = "too-short"
            with self.assertRaises(SystemExit):
                page_mod.require_password()
            os.environ[page_mod.PASSWORD_ENV_VAR] = TEST_PASSWORD
            self.assertEqual(page_mod.require_password(), TEST_PASSWORD)
        # the subcommands are registered and build-page works end to end
        parser = cli.build_parser()
        for name, func in (("ui", "cmd_ui"), ("build-page", "cmd_build_page"),
                           ("audit", "cmd_audit")):
            self.assertEqual(parser.parse_args([name]).func.__name__, func)
        repo = self.repo()
        self.seed(repo)
        with mock.patch.dict(os.environ, {page_mod.PASSWORD_ENV_VAR: TEST_PASSWORD}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["build-page"]), 0)
        written = self.state / "page" / "prospects.json"
        self.assertTrue(written.is_file())
        self.assertEqual(page_mod.validate_page_data(json.loads(written.read_text())), [])

    def test_hash_is_salted_sha256_and_verifies(self):
        import hashlib

        expected = hashlib.sha256((page_mod.SALT_PREFIX + TEST_PASSWORD).encode()).hexdigest()
        self.assertEqual(page_mod.hash_password(TEST_PASSWORD), expected)
        self.assertRegex(page_mod.hash_password(TEST_PASSWORD), r"^[0-9a-f]{64}$")
        self.assertTrue(page_mod.verify_password(TEST_PASSWORD, expected))
        self.assertFalse(page_mod.verify_password("wrong-password-1", expected))
        self.assertNotEqual(
            page_mod.hash_password(TEST_PASSWORD), page_mod.hash_password("other-pass-word")
        )

    def test_write_refuses_paths_outside_page_dir(self):
        repo = self.repo()
        self.seed(repo)
        data = page_mod.build_page_data(repo, TEST_PASSWORD)
        out = page_mod.write_page_data(data)
        self.assertTrue(out.is_file())
        # byte-stable output keeps regeneration diffs meaningful
        self.assertEqual(out.read_text(encoding="utf-8"), json.dumps(data, indent=2, sort_keys=True) + "\n")
        for forbidden in (
            ROOT / "site" / "prospects.json",
            ROOT / "data" / "prospects.json",
            self.state / "sneaky.json",
        ):
            with self.assertRaises(ValueError, msg=str(forbidden)):
                page_mod.write_page_data(data, forbidden)
        self.assertFalse((ROOT / "site" / "prospects.json").exists())


# ---------------------------------------------------------------------------
# Rendered dashboard: gated, noindex, aggregate-only
# ---------------------------------------------------------------------------

class RenderTest(TempStateCase):
    def _data(self):
        repo = self.repo()
        self.seed(repo)
        return page_mod.build_page_data(repo, TEST_PASSWORD)

    def test_render_embeds_gate_and_hash_not_password(self):
        data = self._data()
        html_text = prospects_page.render(data)
        self.assertNotIn(TEST_PASSWORD, html_text)
        self.assertIn(data["password_sha256"], html_text)
        self.assertIn("data-pass-sha256", html_text)
        # renderer and builder must hash with the same salt (kept in sync by test)
        self.assertEqual(prospects_page.GATE_SALT_PREFIX, page_mod.SALT_PREFIX)
        self.assertIn(page_mod.SALT_PREFIX, html_text)

    def test_render_has_noindex_and_no_canonical_and_relative_links_only(self):
        html_text = prospects_page.render(self._data())
        self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">', html_text)
        self.assertNotIn("canonical", html_text.lower())
        self.assertNotRegex(html_text, r'(?:href|src|data-src)="\s*/')
        self.assertNotIn("http", html_text.lower())

    def test_render_contains_aggregates_and_no_email_pattern(self):
        html_text = prospects_page.render(self._data())
        self.assertIn("<b>4</b>", html_text)  # total prospects card
        self.assertIn("Michigan Wolverines", html_text)  # team label, not a prospect name
        self.assertIsNone(audit_mod.EMAIL_LIKE.search(html_text))
        for leak in LEAK_STRINGS:
            self.assertNotIn(leak, html_text)

    def test_render_placeholder_when_data_missing(self):
        html_text = prospects_page.render(None)
        self.assertIn(audit_mod.PLACEHOLDER_MARKER, html_text)
        self.assertIn("noindex", html_text)
        self.assertNotIn("data-pass-sha256", html_text)
        self.assertIsNone(prospects_page.load_data(self.state / "nope" / "missing.json"))

    def test_render_is_deterministic(self):
        data = self._data()
        self.assertEqual(prospects_page.render(data), prospects_page.render(data))
        written = page_mod.write_page_data(data)
        self.assertEqual(prospects_page.render(prospects_page.load_data(written)),
                         prospects_page.render(data))


# ---------------------------------------------------------------------------
# Audit: proves the split on a tree
# ---------------------------------------------------------------------------

class AuditTest(TempStateCase):
    def _sandbox(self):
        tmp = Path(tempfile.mkdtemp(prefix="gridiron-audit-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = self.repo()
        self.seed(repo)
        data = page_mod.build_page_data(repo, TEST_PASSWORD)
        (tmp / "marketing" / "osint" / "page").mkdir(parents=True)
        (tmp / "marketing" / "osint" / "page" / "prospects.json").write_text(
            json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
        )
        rendered = prospects_page.render(data)
        for rel in ("ops/prospects/index.html", "site/ops/prospects/index.html"):
            target = tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
        (tmp / ".gitignore").write_text(
            "__pycache__/\nmarketing/osint/state/\nmarketing/osint/exports/\n",
            encoding="utf-8",
        )
        return tmp

    def test_audit_clean_on_real_tree(self):
        result = audit_mod.audit_tree(ROOT)
        self.assertEqual(result.findings, [])

    def test_audit_flags_planted_email_in_page(self):
        root = self._sandbox()
        self.assertEqual(audit_mod.audit_tree(root).findings, [])
        page = root / "site" / "ops" / "prospects" / "index.html"
        page.write_text(page.read_text(encoding="utf-8") + "\n<!-- leak@example.com -->\n",
                        encoding="utf-8")
        findings = audit_mod.audit_tree(root).findings
        self.assertTrue(any("email-like" in f for f in findings), findings)
        # findings never echo the leaked content itself
        self.assertNotIn("leak@example.com", " ".join(findings))

    def test_audit_flags_planted_database_and_exports(self):
        root = self._sandbox()
        (root / "site" / "ops" / "prospects.db").write_text("db", encoding="utf-8")
        (root / "ops").mkdir(exist_ok=True)
        (root / "ops" / "gridiron_prospects_2026-09-17.csv").write_text("x", encoding="utf-8")
        (root / "marketing" / "high_priority_contacts_2026-09-17.csv").write_text(
            "x", encoding="utf-8")
        # ...while the sanctioned private homes stay silent
        (root / "marketing" / "osint" / "state").mkdir(parents=True)
        (root / "marketing" / "osint" / "state" / "prospects.db").write_text("db", encoding="utf-8")
        (root / "marketing" / "osint" / "exports").mkdir(parents=True)
        (root / "marketing" / "osint" / "exports" / "gridiron_prospects_x.csv").write_text(
            "x", encoding="utf-8")
        findings = audit_mod.audit_tree(root).findings
        self.assertEqual(len(findings), 3, findings)
        self.assertFalse(any("osint/state" in f or "osint/exports" in f for f in findings))

    def test_audit_requires_gitignore_guards(self):
        root = self._sandbox()
        (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        findings = audit_mod.audit_tree(root).findings
        self.assertTrue(any(".gitignore" in f for f in findings), findings)
        (root / ".gitignore").unlink()
        self.assertTrue(any(".gitignore" in f for f in audit_mod.audit_tree(root).findings))


# ---------------------------------------------------------------------------
# Private dashboard: token-gated, local-only
# ---------------------------------------------------------------------------

class DashboardTest(TempStateCase):
    TOKEN = "test-token-abc123"

    def setUp(self):
        super().setUp()
        self.repo_obj = self.repo()
        self.ids = self.seed(self.repo_obj)
        db_path = self.state / "prospects.db"
        self.server = ui_mod.make_server(
            "127.0.0.1", 0, self.TOKEN,
            lambda: db.Repository(db.connect(db_path)),
        )
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()
        self.addCleanup(self._stop_server)

    def _stop_server(self):
        self.server.shutdown()
        self._thread.join(timeout=10)
        self.server.server_close()

    def _request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = (response.status, response.read().decode("utf-8"),
                  response.getheader("Location"))
        conn.close()
        return result

    def _get(self, path, token=True):
        if token is True:
            path += ("&" if "?" in path else "?") + urllib.parse.urlencode({"token": self.TOKEN})
        headers = {"X-Osint-Token": self.TOKEN} if token == "header" else None
        return self._request("GET", path, headers=headers)

    def _post(self, path, fields, token=True):
        if token is True:
            fields = {**fields, "token": self.TOKEN}
        body = urllib.parse.urlencode(fields).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if token == "header":
            headers["X-Osint-Token"] = self.TOKEN
        return self._request("POST", path, body=body, headers=headers)

    def test_ui_requires_token(self):
        status, body, _ = self._get("/", token=False)
        self.assertEqual(status, 403)
        for leak in LEAK_STRINGS:
            self.assertNotIn(leak, body)
        status, _, _ = self._request(
            "GET", "/?token=wrong-token")
        self.assertEqual(status, 403)
        for via in (True, "header"):
            status, body, _ = self._get("/", token=via)
            self.assertEqual(status, 200)
            self.assertIn("OSINT overview", body)

    def test_ui_lists_and_details_prospects(self):
        status, body, _ = self._get("/prospects")
        self.assertEqual(status, 200)
        # private surface: full rows ARE visible behind the token
        self.assertIn("Test Michigan Football Podcast", body)
        self.assertIn("info@examplepod.com", body)
        status, body, _ = self._get("/prospects?team=michigan")
        self.assertEqual(status, 200)
        self.assertIn("Test Michigan Football Podcast", body)
        self.assertNotIn("Big House Tailgate Show", body)
        status, body, _ = self._get("/prospects?q=dawgblogfans")
        self.assertIn("Big House Tailgate Show", body)
        status, body, _ = self._get(f"/prospect?id={self.ids[0]}")
        self.assertEqual(status, 200)
        self.assertIn("team_relevance", body)
        status, _, _ = self._get("/prospect?id=999999")
        self.assertEqual(status, 404)

    def test_ui_status_and_note_actions_update_db(self):
        prospect_id = self.ids[0]
        status, _, location = self._post(
            "/prospect/status", {"id": str(prospect_id), "to": "CONTACTED"})
        self.assertEqual(status, 303)
        self.assertIn(f"/prospect?id={prospect_id}", location)
        self.assertEqual(self.repo_obj.get(prospect_id)["status"], "CONTACTED")
        status, _, _ = self._post(
            "/prospect/note", {"id": str(prospect_id), "text": "sent intro 2026-09-17"})
        self.assertEqual(status, 303)
        self.assertIn("sent intro", self.repo_obj.get(prospect_id)["notes"])
        # writes need the token too, and reject unknown statuses
        status, _, _ = self._post(
            "/prospect/status", {"id": str(prospect_id), "to": "REPLIED"}, token=False)
        self.assertEqual(status, 403)
        self.assertEqual(self.repo_obj.get(prospect_id)["status"], "CONTACTED")
        status, _, _ = self._post(
            "/prospect/status", {"id": str(prospect_id), "to": "NOPE"})
        self.assertEqual(status, 400)

    def test_ui_run_leaves_no_repo_mutations(self):
        before = snapshot_tree()
        self._get("/")
        self._get("/prospects?team=browns")
        self._get(f"/prospect?id={self.ids[1]}")
        self._post("/prospect/status", {"id": str(self.ids[1]), "to": "REPLIED"})
        self._post("/prospect/note", {"id": str(self.ids[1]), "text": "called back"})
        self.assertEqual(snapshot_tree(), before)


# ---------------------------------------------------------------------------
# Publish guards: the page stays out of crawlers/nav, state out of the mirror
# ---------------------------------------------------------------------------

class PublishGuardsTest(unittest.TestCase):
    def test_page_not_in_sitemap_nav_and_robots_disallows_ops(self):
        site = ROOT / "site"
        self.assertNotIn("ops/prospects", (site / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertNotIn("ops/prospects", (site / "index.html").read_text(encoding="utf-8"))
        self.assertIn("Disallow: /ops/", (site / "robots.txt").read_text(encoding="utf-8"))
        # ...but reachable from the private ops index, which is itself noindex
        ops_index = (site / "ops" / "index.html").read_text(encoding="utf-8")
        self.assertIn("prospects/index.html", ops_index)
        self.assertIn("noindex", ops_index)
        page = (site / "ops" / "prospects" / "index.html").read_text(encoding="utf-8")
        self.assertIn("noindex", page)
        self.assertNotIn("ops/prospects", (ROOT / "data" / "catalogue-live.json").read_text())

    def test_sync_mirror_excludes_private_state(self):
        import build  # noqa: E402  (src/ is on sys.path; import is read-only)

        ignore = build._sync_ignore_private
        self.assertEqual(
            ignore("/r/marketing/osint", ["state", "exports", "page", "db.py", "keywords"]),
            {"state", "exports", "page"},
        )
        self.assertEqual(ignore("/r/marketing/osint/state", ["prospects.db"]), {"prospects.db"})
        self.assertEqual(
            ignore("/r/marketing/osint/exports", ["gridiron_prospects_x.csv"]),
            set(),  # the whole exports dir is pruned one level up; csv names pass through
        )
        self.assertEqual(ignore("/r/ops", ["scout.json", "leak.db"]), {"leak.db"})
        self.assertEqual(ignore("/r/marketing", ["plan.json", "__pycache__"]), {"__pycache__"})
        # ...and both mirrors actually use the filter
        import inspect

        self.assertIn("ignore=_sync_ignore_private", inspect.getsource(build.sync_marketing))
        self.assertIn("ignore=_sync_ignore_private", inspect.getsource(build.sync_ops))
