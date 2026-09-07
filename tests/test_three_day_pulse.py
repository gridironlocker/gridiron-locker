#!/usr/bin/env python3
"""Regression tests for the rolling three-day trend-to-product pulse."""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ThreeDayPulse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, "marketing/social_watch.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, "marketing/plan.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, "marketing/three_day_pulse.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run([sys.executable, "marketing/publisher.py"], cwd=ROOT, check=True, capture_output=True, text=True)
        with open(os.path.join(ROOT, "marketing", "three-day-pulse.json"), encoding="utf-8") as handle:
            cls.pulse = json.load(handle)
        with open(os.path.join(ROOT, "marketing", "publish-results.json"), encoding="utf-8") as handle:
            cls.publish = json.load(handle)
        with open(os.path.join(ROOT, "marketing", "social-signals.json"), encoding="utf-8") as handle:
            cls.signals = json.load(handle)

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

    def test_publisher_defaults_to_dry_run(self):
        self.assertEqual(self.publish["mode"], "dry_run")
        self.assertTrue(all(row["status"] == "dry_run" for row in self.publish["results"]))


if __name__ == "__main__":
    unittest.main()
