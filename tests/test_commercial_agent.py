#!/usr/bin/env python3
"""Regression tests for the NFL Fan Commerce Marketing Agent brief.

The generators are run inside a throwaway copy of the repository (see
``tests/testutil.py``). Running them in-place would overwrite the tracked
``marketing/*.json`` artefacts, which ``refresh.yml`` then commits with
``git add -A`` - a test run must never be able to mutate the repository.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from testutil import generator_sandbox, read_json, run_generator  # noqa: E402


class CommercialBrief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._sandbox_cm = generator_sandbox()
        cls.sandbox = cls._sandbox_cm.__enter__()
        run_generator(cls.sandbox, "plan.py")
        run_generator(cls.sandbox, "commercial_agent.py")
        cls.brief = read_json(cls.sandbox / "marketing" / "commercial-brief.json")

    @classmethod
    def tearDownClass(cls):
        cls._sandbox_cm.__exit__(None, None, None)

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
