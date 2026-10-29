#!/usr/bin/env python3
"""Tests for the Gridiron SEO Engine.

Stdlib only. Does not mutate the repository: overrides / memory writes go
through temporary paths, and the crawl reads the committed site/ read-only.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from seo_engine import __version__  # noqa: E402
from seo_engine.audit import (  # noqa: E402
    audit_pages,
    gsc_by_page,
    load_gsc_export,
    run_audit,
)
from seo_engine.config import (  # noqa: E402
    MODE_AUTO,
    MODE_HUMAN,
    MODE_PR,
    SAFE_TYPES,
)
from seo_engine.content import scan_opportunities  # noqa: E402
from seo_engine.crawler import Page, crawl, parse_page  # noqa: E402
from seo_engine.decide import decide  # noqa: E402
from seo_engine import apply as apply_mod  # noqa: E402
from seo_engine import verify as verify_mod  # noqa: E402
from seo_engine.import_gsc import build_export as import_build  # noqa: E402
from seo_engine.import_gsc import pct as import_pct  # noqa: E402


class Version(unittest.TestCase):
    def test_version_present(self):
        self.assertTrue(__version__)


class Crawler(unittest.TestCase):
    def test_crawl_finds_public_pages(self):
        pages = crawl()
        paths = {p.path for p in pages}
        self.assertIn("/", paths)
        self.assertIn("/michigan-wolverines-shirts/", paths)
        self.assertIn("/cleveland-browns-shirts/", paths)
        # ops/marketing must stay out
        self.assertFalse(any(p.path.startswith("/ops/") for p in pages))
        self.assertFalse(any(p.path.startswith("/marketing/") for p in pages))

    def test_collection_kind(self):
        pages = {p.path: p for p in crawl()}
        self.assertEqual(pages["/michigan-wolverines-shirts/"].kind, "collection")

    def test_product_pages_classified(self):
        products = [p for p in crawl() if p.kind == "product"]
        self.assertGreaterEqual(len(products), 50)
        for p in products[:5]:
            self.assertTrue(p.path.startswith("/shop/"))
            self.assertTrue(p.title)
            self.assertTrue(p.canonical)

    def test_parse_page_extracts_meta(self):
        site = ROOT / "site" / "michigan-wolverines-shirts" / "index.html"
        page = parse_page("/michigan-wolverines-shirts/", site)
        self.assertTrue(page.title)
        self.assertTrue(page.meta_description)
        self.assertIn("gridironlocker.store", page.canonical or "")
        self.assertTrue(page.h1)
        self.assertTrue(page.has_json_ld)


class Audit(unittest.TestCase):
    def test_run_audit_shape(self):
        report = run_audit()
        self.assertIn("findings", report)
        self.assertIn("by_type", report)
        self.assertIn("page_count", report)
        self.assertGreater(report["page_count"], 50)
        self.assertEqual(report["engine"], "seo_engine.audit")

    def test_gsc_absent_file_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = load_gsc_export(Path(tmp) / "nope.json")
        self.assertEqual(rows, [])

    def test_gsc_export_live_rows_schema(self):
        # The live export is operator-supplied data: whatever is present
        # must match the row contract (numbers never invented, types right).
        for row in load_gsc_export():
            self.assertTrue(str(row.get("page", "")).startswith("http"), row)
            self.assertIsInstance(row.get("clicks"), (int, float))
            self.assertIsInstance(row.get("impressions"), (int, float))
            ctr = row.get("ctr")
            self.assertIsInstance(ctr, (int, float))
            self.assertGreaterEqual(ctr, 0.0)
            self.assertLessEqual(ctr, 1.0)
            self.assertIsInstance(row.get("position"), (int, float))

    def test_gsc_aggregation(self):
        rows = [
            {
                "page": "https://gridironlocker.store/michigan-wolverines-shirts/",
                "query": "michigan football shirts",
                "clicks": 10,
                "impressions": 500,
                "ctr": 0.02,
                "position": 11.0,
            },
            {
                "page": "https://gridironlocker.store/michigan-wolverines-shirts/",
                "query": "go blue tee",
                "clicks": 2,
                "impressions": 100,
                "ctr": 0.02,
                "position": 15.0,
            },
        ]
        agg = gsc_by_page(rows)
        key = "/michigan-wolverines-shirts/"
        self.assertIn(key, agg)
        self.assertEqual(agg[key]["clicks"], 12)
        self.assertEqual(agg[key]["impressions"], 600)
        self.assertEqual(len(agg[key]["queries"]), 2)

    def test_missing_title_finding(self):
        pages = [Page(path="/fake/", file="/dev/null", title=None, kind="static")]
        findings = audit_pages(pages)
        types = {f["type"] for f in findings}
        self.assertIn("missing_title", types)

    def test_weak_ctr_requires_gsc(self):
        pages = crawl()
        # No GSC → no weak_ctr_title
        findings = audit_pages(pages, gsc={})
        self.assertNotIn("weak_ctr_title", {f["type"] for f in findings})

    def test_weak_ctr_with_gsc(self):
        pages = [p for p in crawl() if p.path == "/michigan-wolverines-shirts/"]
        self.assertTrue(pages)
        gsc = {
            "/michigan-wolverines-shirts/": {
                "clicks": 5,
                "impressions": 500,
                "ctr": 0.01,
                "position": 14.0,
                "queries": [{"query": "michigan football shirts", "impressions": 500}],
            }
        }
        findings = audit_pages(pages, gsc=gsc)
        weak = [f for f in findings if f["type"] == "weak_ctr_title"]
        self.assertEqual(len(weak), 1)
        self.assertIn("title", weak[0].get("suggested") or {})


class ImportGsc(unittest.TestCase):
    def _write(self, tmp, name, text):
        (Path(tmp) / name).write_text(text, encoding="utf-8")

    def test_pct_conversion(self):
        self.assertEqual(import_pct("22.22%"), 0.2222)
        self.assertEqual(import_pct("0%"), 0.0)
        self.assertEqual(import_pct("100%"), 1.0)

    def test_import_is_faithful(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "Pages.csv",
                        "Top pages,Clicks,Impressions,CTR,Position\n"
                        "https://gridironlocker.store/,12,54,22.22%,5.44\n"
                        "https://gridironlocker.store/shop/x/,0,7,0%,41\n")
            self._write(tmp, "Queries.csv",
                        "Top queries,Clicks,Impressions,CTR,Position\n"
                        "gridiron cap locker,6,13,46.15%,3.46\n")
            self._write(tmp, "Devices.csv",
                        "Device,Clicks,Impressions,CTR,Position\n"
                        "Mobile,13,315,4.13%,14.45\n")
            self._write(tmp, "Filters.csv",
                        "Filter,Value\nSearch type,Web (text-based)\n")
            data = import_build(Path(tmp))

        self.assertEqual(len(data["rows"]), 2)
        top = data["rows"][0]
        self.assertEqual(top["page"], "https://gridironlocker.store/")
        self.assertEqual(top["clicks"], 12)
        self.assertEqual(top["impressions"], 54)
        self.assertEqual(top["ctr"], 0.2222)
        self.assertEqual(top["position"], 5.44)
        # query table preserved separately, never attached to a page
        self.assertEqual(data["queries"][0]["query"], "gridiron cap locker")
        self.assertNotIn("page", data["queries"][0])
        # labels survive for every table
        self.assertEqual(data["devices"][0]["device"], "Mobile")
        self.assertEqual(data["filters"][0]["value"], "Web (text-based)")
        # totals never drift from the export
        self.assertEqual(sum(r["clicks"] for r in data["rows"]), 12)
        self.assertEqual(sum(r["impressions"] for r in data["rows"]), 61)

    def test_requires_pages_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                import_build(Path(tmp))

    def test_chart_dispatch_and_preserve(self):
        # Chart.csv exists in both export flavours: header decides routing,
        # and a missing performance chart must not wipe a previous import.
        from seo_engine.import_gsc import build_indexing

        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "Pages.csv",
                        "Top pages,Clicks,Impressions,CTR,Position\n"
                        "https://gridironlocker.store/,12,54,22.22%,5.44\n")
            self._write(tmp, "Chart.csv",
                        "Date,Not indexed,Indexed,Impressions\n"
                        "2026-10-23,94,78,20\n")
            self._write(tmp, "Critical issues.csv",
                        "Reason,Source,Validation,Pages\n"
                        "Not found (404),Website,Not Started,2\n")
            self._write(tmp, "Non-critical issues.csv",
                        "Reason,Source,Validation,Pages\n")
            self._write(tmp, "Metadata.csv", "Property,Value\nSitemap,All known pages\n")
            previous = {"daily": [{"date": "2026-09-29", "clicks": 0,
                                   "impressions": 8, "ctr": 0.0, "position": 21.4}]}
            perf = import_build(Path(tmp), previous=previous)
            indexing = build_indexing(Path(tmp))

        # indexing chart never lands in the performance daily table
        self.assertEqual(perf["daily"][0]["date"], "2026-09-29")
        # indexing tables land in the indexing export
        self.assertEqual(indexing["property"], "All known pages")
        self.assertEqual(indexing["daily"][0]["not_indexed"], 94)
        self.assertEqual(indexing["daily"][0]["indexed"], 78)
        self.assertEqual(indexing["issues"][0]["pages"], 2)
        self.assertEqual(indexing["non_critical_issues"], [])

    def test_indexing_blank_cells_stay_null(self):
        from seo_engine.import_gsc import build_indexing

        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "Chart.csv",
                        "Date,Not indexed,Indexed,Impressions\n"
                        "2026-09-02,,,0\n")
            indexing = build_indexing(Path(tmp))
        self.assertIsNone(indexing["daily"][0]["not_indexed"])
        self.assertIsNone(indexing["daily"][0]["indexed"])
        self.assertEqual(indexing["daily"][0]["impressions"], 0)

    def test_indexing_requires_some_csv(self):
        from seo_engine.import_gsc import build_indexing

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                build_indexing(Path(tmp))


class IssueUrls(unittest.TestCase):
    """data/seo/gsc_issue_urls.json - the operator-pasted URL-level
    drill-down behind the aggregate indexing counts. Verbatim data: the
    only rule is that it must never drift from gsc_indexing.json."""

    def test_shape_and_counts_match_indexing_export(self):
        urls = json.loads((ROOT / "data" / "seo" / "gsc_issue_urls.json").read_text())
        idx = json.loads((ROOT / "data" / "seo" / "gsc_indexing.json").read_text())
        # zero-page rows (e.g. the Passed duplicate-canonical check) have no
        # URLs to drill into and stay out of the URL file
        expect_reasons = {r["reason"] for r in idx["issues"] if r["pages"]}
        self.assertEqual(set(urls["issues"]), expect_reasons)
        for reason, rows in urls["issues"].items():
            expect = next(r["pages"] for r in idx["issues"] if r["reason"] == reason)
            self.assertEqual(len(rows), expect, reason)
            for row in rows:
                self.assertTrue(row["url"].startswith("https://gridironlocker.store/"), row)
                self.assertIn("last_crawled", row)
                lc = row["last_crawled"]
                self.assertTrue(lc is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}", lc), row)


class Decide(unittest.TestCase):
    def test_modes_partition(self):
        audit = {
            "generated_at": "2026-09-19T00:00:00Z",
            "findings": [
                {
                    "type": "missing_title",
                    "path": "/x/",
                    "severity": "high",
                    "detail": "no title",
                    "evidence": {},
                    "suggested": {"title": "X | Gridiron Locker"},
                },
                {
                    "type": "url_change",
                    "path": "/old/",
                    "severity": "high",
                    "detail": "move",
                    "evidence": {},
                    "suggested": {},
                },
            ],
        }
        report = decide(audit, overrides={"pages": {}})
        modes = {a["type"]: a["mode"] for a in report["actions"]}
        self.assertEqual(modes["missing_title"], MODE_AUTO)
        self.assertEqual(modes["url_change"], MODE_HUMAN)

    def test_safe_types_are_auto(self):
        for t in SAFE_TYPES:
            audit = {
                "findings": [{
                    "type": t,
                    "path": "/p/",
                    "severity": "medium",
                    "detail": t,
                    "evidence": {},
                    "suggested": {"title": "T"} if "title" in t or t.startswith("weak")
                    else ({"meta_description": "D" * 80} if "description" in t
                          else ({"canonical": "https://x/"} if "canonical" in t
                                else {"og_title": "O"} if "og_title" in t
                                else {"og_description": "O"} if "og_description" in t
                                else {})),
                }]
            }
            report = decide(audit, overrides={"pages": {}})
            # missing_image_alt has no suggested payload → observe, still AUTO mode
            actions = [a for a in report["actions"] if a["type"] == t]
            self.assertTrue(actions, msg=t)
            self.assertEqual(actions[0]["mode"], MODE_AUTO, msg=t)

    def test_skips_already_applied_override(self):
        audit = {
            "findings": [{
                "type": "missing_title",
                "path": "/x/",
                "severity": "high",
                "detail": "no title",
                "evidence": {},
                "suggested": {"title": "Already Set"},
            }]
        }
        overrides = {"pages": {"/x/": {"title": "Already Set"}}}
        report = decide(audit, overrides=overrides)
        # identical override → action dropped
        self.assertEqual(report["actions"], [])


class Apply(unittest.TestCase):
    def test_dry_run_writes_nothing(self):
        decisions = {
            "actions": [{
                "id": "seo-test0001",
                "mode": MODE_AUTO,
                "type": "missing_title",
                "path": "/dry-run-test/",
                "severity": "high",
                "score": 50,
                "status": "ready_auto",
                "detail": "test",
                "evidence": {},
                "changes": {"title": "Dry Run Title | Gridiron Locker"},
                "reason": "test",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            ovr_path = Path(tmp) / "overrides.json"
            with mock.patch.object(apply_mod, "OVERRIDES_PATH", ovr_path), \
                 mock.patch.object(apply_mod, "PROPOSALS_DIR", Path(tmp) / "proposals"), \
                 mock.patch.object(apply_mod, "ensure_seo_dirs", lambda: Path(tmp).mkdir(exist_ok=True)):
                # load_overrides reads OVERRIDES_PATH
                result = apply_mod.apply_decisions(decisions, dry_run=True)
                self.assertTrue(result["dry_run"])
                self.assertEqual(result["auto_count"], 1)
                self.assertFalse(ovr_path.exists())

    def test_commit_writes_overrides(self):
        decisions = {
            "actions": [{
                "id": "seo-test0002",
                "mode": MODE_AUTO,
                "type": "missing_description",
                "path": "/commit-test/",
                "severity": "high",
                "score": 50,
                "status": "ready_auto",
                "detail": "test",
                "evidence": {},
                "changes": {
                    "meta_description": (
                        "Independent fan-made football apparel from Gridiron Locker. "
                        "Printed on demand and shipped worldwide to supporters."
                    )
                },
                "reason": "test",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            ovr_path = Path(tmp) / "overrides.json"
            prop_dir = Path(tmp) / "proposals"
            prop_dir.mkdir()
            with mock.patch.object(apply_mod, "OVERRIDES_PATH", ovr_path), \
                 mock.patch.object(apply_mod, "PROPOSALS_DIR", prop_dir):
                result = apply_mod.apply_decisions(decisions, dry_run=False)
                self.assertEqual(result["auto_count"], 1)
                self.assertTrue(ovr_path.is_file())
                data = json.loads(ovr_path.read_text(encoding="utf-8"))
                self.assertIn("/commit-test/", data["pages"])
                self.assertIn("meta_description", data["pages"]["/commit-test/"])
                self.assertEqual(len(data["history"]), 1)

    def test_pr_mode_writes_proposal(self):
        decisions = {
            "actions": [{
                "id": "seo-pr0001",
                "mode": MODE_PR,
                "type": "collection_content_rewrite",
                "path": "/michigan-wolverines-shirts/",
                "severity": "medium",
                "score": 40,
                "status": "needs_pr",
                "detail": "rewrite",
                "evidence": {},
                "changes": {},
                "reason": "test",
            }]
        }
        with tempfile.TemporaryDirectory() as tmp:
            ovr_path = Path(tmp) / "overrides.json"
            prop_dir = Path(tmp) / "proposals"
            prop_dir.mkdir()
            with mock.patch.object(apply_mod, "OVERRIDES_PATH", ovr_path), \
                 mock.patch.object(apply_mod, "PROPOSALS_DIR", prop_dir):
                result = apply_mod.apply_decisions(
                    decisions, dry_run=False, modes=[MODE_PR]
                )
                self.assertEqual(result["pr_count"], 1)
                mds = list(prop_dir.glob("pr-*.md"))
                self.assertEqual(len(mds), 1)
                self.assertIn("SEO Engine PR proposal", mds[0].read_text(encoding="utf-8"))


class Verify(unittest.TestCase):
    def test_empty_overrides_pass(self):
        report = verify_mod.verify_overrides(overrides={"pages": {}})
        self.assertEqual(report["override_count"], 0)
        self.assertEqual(report["failed"], 0)

    def test_detects_unapplied_override(self):
        # Point at a real page but with a title that is not on disk.
        overrides = {
            "pages": {
                "/michigan-wolverines-shirts/": {
                    "title": "THIS TITLE DOES NOT EXIST ON DISK",
                    "change_id": "seo-fake",
                }
            }
        }
        report = verify_mod.verify_overrides(overrides=overrides)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["results"][0]["status"], "fail")

    def test_outcome_requires_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = Path(tmp) / "memory.json"
            with mock.patch.object(verify_mod, "MEMORY_PATH", mem):
                with self.assertRaises(ValueError):
                    verify_mod.record_outcome(
                        "seo-x", "/x/", before={}, after={}, source=""
                    )


class Content(unittest.TestCase):
    def test_scan_returns_seed_opportunities(self):
        report = scan_opportunities()
        self.assertGreaterEqual(report["opportunity_count"], 1)
        self.assertTrue(report["policy_notes"])
        # Every opportunity is proposal-only
        for opp in report["opportunities"]:
            self.assertEqual(opp.get("status"), "proposal_only")
            self.assertEqual(opp.get("mode"), "PR")

    def test_policy_blocks_thin_pages(self):
        report = scan_opportunities()
        joined = " ".join(report["policy_notes"]).lower()
        self.assertIn("intent", joined)


class BuildIntegration(unittest.TestCase):
    """Confirm src/build.py exposes the override hook and applies it in head()."""

    def test_seo_overrides_for_helper(self):
        sys.path.insert(0, str(ROOT / "src"))
        import build  # noqa: WPS433
        # Empty overrides by default in committed file
        self.assertIsInstance(build.seo_overrides_for("/michigan-wolverines-shirts/"), dict)

    def test_head_applies_title_override(self):
        sys.path.insert(0, str(ROOT / "src"))
        import build  # noqa: WPS433
        fake = {
            "/override-hook-test/": {
                "title": "Override Hook Title",
                "meta_description": (
                    "Override hook description long enough to look like a real "
                    "meta description for the SEO engine integration test."
                ),
            }
        }
        original = build._SEO_OVERRIDES
        try:
            build._SEO_OVERRIDES = fake
            html_out = build.head(
                "Original Title | Gridiron Locker",
                "Original description that should be replaced by the override payload.",
                "/override-hook-test/",
            )
        finally:
            build._SEO_OVERRIDES = original
        self.assertIn("<title>Override Hook Title</title>", html_out)
        self.assertIn('content="Override hook description', html_out)
        self.assertIn('property="og:title" content="Override Hook Title"', html_out)

    def test_head_ignores_empty_override(self):
        sys.path.insert(0, str(ROOT / "src"))
        import build  # noqa: WPS433
        html_out = build.head(
            "Plain Title | Gridiron Locker",
            "A plain description used when no override is present for this path at all.",
            "/no-such-override-path-ever/",
        )
        self.assertIn("<title>Plain Title | Gridiron Locker</title>", html_out)


class Cli(unittest.TestCase):
    def test_cli_audit_runs(self):
        from seo_engine.__main__ import main
        rc = main(["audit"])
        self.assertEqual(rc, 0)

    def test_cli_run_dry(self):
        from seo_engine.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            # Redirect artefacts so the test cannot dirty the repo.
            audit_p = Path(tmp) / "audit.json"
            dec_p = Path(tmp) / "dec.json"
            ovr_p = Path(tmp) / "overrides.json"
            import seo_engine.__main__ as main_mod
            import seo_engine.config as cfg
            with mock.patch.object(main_mod, "AUDIT_PATH", audit_p), \
                 mock.patch.object(main_mod, "DECISIONS_PATH", dec_p), \
                 mock.patch.object(main_mod, "OVERRIDES_PATH", ovr_p), \
                 mock.patch.object(main_mod, "ensure_seo_dirs", lambda: Path(tmp).mkdir(exist_ok=True)), \
                 mock.patch.object(cfg, "SEO_DATA", Path(tmp)), \
                 mock.patch("seo_engine.__main__.write_json",
                            side_effect=lambda p, payload: Path(p).write_text(
                                json.dumps(payload), encoding="utf-8")):
                rc = main(["run"])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()


class Backlinks(unittest.TestCase):
    """data/seo/backlinks.json - faithful copy of the 2026-10-29 site-explorer
    URL export. Verbatim rule: values match the CSV, totals are computed, and
    no vendor attribution is invented."""

    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(Path("data/seo/backlinks.json").read_text(encoding="utf-8"))

    def test_rows_match_export(self):
        rows = self.doc["rows"]
        self.assertEqual(len(rows), 6)
        self.assertEqual([c for c in self.doc["columns"]],
                         ["URL", "Impressions", "Clicks", "Last crawled",
                          "Discovered on", "HTTP code", "Document size", "Backlinks"])
        by = {r["url"]: r for r in rows}
        self.assertEqual(by["https://gridironlocker.store"]["backlinks"], 0)
        self.assertEqual(by["http://gridironlocker.store"]["backlinks"], 1)
        cle = by["https://gridironlocker.store/cleveland-browns-shirts"]
        self.assertEqual(cle["backlinks"], 6)
        self.assertEqual(cle["last_crawled"], "2026-10-09")
        self.assertEqual(cle["document_size"], 74191)

    def test_totals_computed_not_stated(self):
        self.assertEqual(self.doc["totals"]["backlinks"],
                         sum(r["backlinks"] for r in self.doc["rows"]))
        self.assertEqual(self.doc["totals"]["backlinks"], 7)
        self.assertEqual(self.doc["totals"]["urls"], 6)

    def test_host_scope_and_types(self):
        for r in self.doc["rows"]:
            self.assertTrue(r["url"].startswith(("http://gridironlocker.store",
                                                 "https://gridironlocker.store")), r["url"])
            self.assertIsInstance(r["backlinks"], int)
            self.assertIsInstance(r["impressions"], int)


class WeakCtrDescription(unittest.TestCase):
    """weak_ctr_description: page-1 weak CTR rule. Descriptions are the only
    writable field - titles stay observe-only per the standing content freeze."""

    def setUp(self):
        import seo_engine.audit as audit
        audit._DESC_OVERRIDE_CACHE = None  # isolate the override guard per test

    def test_suggestion_shape_cap_and_no_title(self):
        from seo_engine.audit import _weak_ctr_description_suggestion
        class P:  # minimal page stand-in
            h1 = ["Beware Of Dawg"]
            title = "Beware Of Dawg | Gridiron Locker"
            meta_description = "old"
            kind = "product"
        sugg = _weak_ctr_description_suggestion(P(), "beware of dawgs")
        self.assertEqual(set(sugg) - {"query"}, {"meta_description"})
        self.assertLessEqual(len(sugg["meta_description"]), 158)
        self.assertIn("beware of dawgs", sugg["meta_description"])
        self.assertIn("Printed after you order", sugg["meta_description"])

    def test_mode_is_auto_but_title_freeze_holds(self):
        from seo_engine.config import SAFE_TYPES, MODE_AUTO
        from seo_engine.decide import _mode_for
        self.assertIn("weak_ctr_description", SAFE_TYPES)
        self.assertEqual(_mode_for("weak_ctr_description"), MODE_AUTO)

    def test_approved_overrides_are_never_reproposed(self):
        from seo_engine.audit import _has_description_override
        # '/' carries an approved description trim (seo-engine apply history).
        self.assertTrue(_has_description_override("/"))
        self.assertFalse(_has_description_override("/shop/nonexistent/"))
