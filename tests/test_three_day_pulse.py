#!/usr/bin/env python3
"""Regression tests for the rolling three-day trend-to-product pulse.

The generators are run inside a throwaway copy of the repository (see
``tests/testutil.py``). Running them in-place would overwrite the tracked
``marketing/*.json`` artefacts, which ``refresh.yml`` then commits with
``git add -A`` - a test run must never be able to mutate the repository.
"""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from testutil import ROOT, generator_sandbox, read_json, run_generator  # noqa: E402


class ThreeDayPulse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._sandbox_cm = generator_sandbox()
        cls.sandbox = cls._sandbox_cm.__enter__()
        run_generator(cls.sandbox, "social_watch.py")
        run_generator(cls.sandbox, "plan.py")
        run_generator(cls.sandbox, "three_day_pulse.py")
        run_generator(cls.sandbox, "publisher.py")
        cls.pulse = read_json(cls.sandbox / "marketing" / "three-day-pulse.json")
        cls.publish = read_json(cls.sandbox / "marketing" / "publish-results.json")
        cls.signals = read_json(cls.sandbox / "marketing" / "social-signals.json")

    @classmethod
    def tearDownClass(cls):
        cls._sandbox_cm.__exit__(None, None, None)

    def test_exactly_three_short_lived_days(self):
        self.assertEqual(self.pulse["meta"]["horizon_days"], 3)
        self.assertEqual(len(self.pulse["days"]), 3)
        self.assertEqual([day["label"] for day in self.pulse["days"]], ["today", "tomorrow", "+2 days"])

    def test_rows_have_product_trend_copy_and_risk(self):
        rows = [row for day in self.pulse["days"] for row in day["opportunities"]]
        self.assertTrue(rows)
        self.assertTrue(all(row["slug"] and row["trend"] and row["copy"]["ad_copy"] for row in rows))
        self.assertTrue(all(set(row["copy"]["captions"]) >= {"instagram", "facebook", "x", "tiktok", "pinterest"} for row in rows))
        self.assertTrue(all("decision" in row["risk"] for row in rows))

    def test_source_failure_is_explicit_and_not_called_live(self):
        source = self.signals["sources"]["google_news"]
        self.assertIn(source["status"], {"connected", "error"})
        if source.get("reason"):
            self.assertNotEqual(source["status"], "connected")
        self.assertEqual(self.pulse["meta"]["auto_publish_enabled"], False)

    def test_creative_is_distinct_per_row(self):
        rows = [row for day in self.pulse["days"] for row in day["opportunities"]]
        hooks = [row["copy"]["hook"] for row in rows]
        self.assertEqual(len(set(hooks)), len(hooks), "every pulse row needs its own hook")
        templates = [row["copy"]["hook_template"] for row in rows]
        self.assertEqual(len(set(templates)), len(templates), "hook templates must not repeat across the pulse")
        slugs = [row["slug"] for row in rows]
        self.assertEqual(len(set(slugs)), len(slugs), "the same product must not repeat across days")
        for day in self.pulse["days"]:
            angles = [row["copy"]["angle"] for row in day["opportunities"]]
            self.assertEqual(len(set(angles)), len(angles), "one creative angle per day per row")
        for row in rows:
            captions = row["copy"]["captions"]
            self.assertEqual(len(set(captions.values())), len(captions), "platform captions must differ")
            self.assertLessEqual(len(captions["x"]), 280)
            self.assertTrue(row["creative_angle"])
            self.assertIn(row["copy"]["angle_label"], row["copy"]["pinterest"]["description"])

    def test_publisher_defaults_to_dry_run(self):
        self.assertEqual(self.publish["mode"], "dry_run")
        self.assertTrue(all(row["status"] == "dry_run" for row in self.publish["results"]))

    def test_generators_never_touch_the_real_repository(self):
        """The whole point of the sandbox: prove it actually holds.

        Each generator resolves its output path from its own ``__file__``, so a
        sandboxed run writes into the sandbox. If anyone ever "simplifies"
        ``testutil.generator_sandbox`` back to running the scripts in place, the
        tracked marketing artefacts would be rewritten by a test run and
        committed by ``refresh.yml``'s ``git add -A``. This compares the tracked
        files against the pristine HEAD blobs so that regression fails here,
        loudly, instead of showing up as a mystery diff in someone's commit.
        """
        tracked = (
            "marketing/commercial-brief.json",
            "marketing/plan.json",
            "marketing/social-signals.json",
            "marketing/three-day-pulse.json",
        )
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", *tracked],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(
            status,
            "",
            "running the marketing generators modified tracked artefacts; the "
            "test sandbox is leaking into the repository:\n" + status,
        )


if __name__ == "__main__":
    unittest.main()
