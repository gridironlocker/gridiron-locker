#!/usr/bin/env python3
"""Regression tests for the NFL Fan Commerce Marketing Agent brief."""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class CommercialBrief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "marketing/plan.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [sys.executable, "marketing/commercial_agent.py"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        with open(os.path.join(ROOT, "marketing", "commercial-brief.json"), encoding="utf-8") as handle:
            cls.brief = json.load(handle)

    def test_role_is_commercial_and_requires_approval(self):
        meta = self.brief["meta"]
        self.assertEqual(meta["role_id"], "nfl-fan-commerce-marketing-agent")
        self.assertTrue(meta["human_approval_required"])
        self.assertFalse(meta["auto_publish"])

    def test_predictor_returns_five_existing_products(self):
        rows = self.brief["top_5_products_today"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(row["slug"] and row["product"] for row in rows))
        self.assertTrue(all(0 <= row["opportunity_score"] <= 100 for row in rows))
        self.assertTrue(all(row["creative_style"] and row["fan_motivation"] for row in rows))

    def test_compliance_gate_is_not_hidden(self):
        rows = self.brief["top_5_products_today"]
        self.assertTrue(all(row["risk"]["action"] == "HOLD_LICENSE_REVIEW" for row in rows))
        self.assertIn("licensing", rows[0]["decision_reason"].lower())

    def test_external_sources_and_economics_are_honest(self):
        self.assertEqual(self.brief["economics"]["status"], "NEEDS_COST_INPUTS")
        self.assertEqual(self.brief["source_registry"]["pinterest_trends"]["status"], "not_connected")
        self.assertEqual(self.brief["source_registry"]["nfl_news"]["status"], "wired")

    def test_runway_and_experiment_engine_present(self):
        self.assertEqual(len(self.brief["event_runway"]), 4)
        self.assertEqual([row["horizon"] for row in self.brief["event_runway"][0]["horizons"]], ["today", "tomorrow", "3 days", "7 days", "30 days"])
        self.assertEqual(len(self.brief["experiments"]), 4)
        self.assertEqual(self.brief["repurposing_engine"]["pinterest_pins"], 5)


if __name__ == "__main__":
    unittest.main()
