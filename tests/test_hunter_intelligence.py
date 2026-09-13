#!/usr/bin/env python3
"""Regression tests for the Hunter intelligence layer (src/hunter_intelligence.py).

The bug these exist to stop coming back: the old HQ called every Google News
headline "TRENDING - 1 mentions" and turned it into a generic "post your Browns
shirt" card. So the ladder is tested directly - one headline can never be a
trend, OPPORTUNITY needs a matched design, and article ideas only exist at
OPPORTUNITY and above.

The pure-function tests need no data files. The two that read the repository
read ``data/`` and ``marketing/`` read-only; the one that runs ``src/hq.py``
does it inside the throwaway copy from ``tests/testutil.py`` so a test run never
rewrites the tracked ``ops/hq/index.html`` or ``trend-report.md``.
"""
import datetime as dt
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hunter_intelligence as HI  # noqa: E402
from testutil import generator_sandbox  # noqa: E402

UTC = dt.timezone.utc


def item(text, source="google_news", outlet=None, minutes_ago=10, team="cleveland-browns",
         kind="news", url="https://example.test/1", published=""):
    """A pool item shaped exactly like build_pool() produces."""
    ts = dt.datetime.now(UTC) - dt.timedelta(minutes=minutes_ago)
    entry = {"team": team, "source": source, "outlet": outlet or source, "kind": kind,
             "text": HI._norm(text), "display": text, "raw": text, "url": url,
             "published": published, "ts": ts, "age_min": minutes_ago, "metrics": {}}
    entry["demand"] = HI._demand_kind(entry)
    entry["weight"] = HI.ITEM_WEIGHTS[entry["demand"]]
    return entry


class LevelLadder(unittest.TestCase):
    """classify_level checks ACTION and OPPORTUNITY first, then TREND/SIGNAL/HEADLINE."""

    def test_single_headline_is_never_a_trend(self):
        """The exact bug from the screenshot: 1 mention must not read TRENDING."""
        for confidence in (50, 75, 90, 100):
            self.assertEqual(
                HI.classify_level(confidence, commercial={"type": "exact"}, items=1,
                                  sources=1, velocity={"pct": 500.0}, timing_open=True),
                "HEADLINE",
                f"confidence {confidence} on one headline should still be HEADLINE")

    def test_utility_listings_cannot_buy_a_signal(self):
        """Weighted demand floor: three TV listings are not a fan reaction."""
        self.assertEqual(
            HI.classify_level(80, commercial={"type": "exact"}, items=3, sources=3,
                              velocity={"pct": 200.0}, weighted=0.75, timing_open=True),
            "HEADLINE")

    def test_action_is_checked_before_opportunity(self):
        level = HI.classify_level(75, commercial={"type": "exact"}, items=5, sources=3,
                                  velocity={"pct": 60.0}, timing_open=True)
        self.assertEqual(level, "ACTION")
        self.assertEqual(
            HI.classify_level(74, commercial={"type": "exact"}, items=5, sources=3,
                              velocity={"pct": 60.0}, timing_open=True),
            "OPPORTUNITY")

    def test_opportunity_needs_a_matched_design(self):
        """90% confidence with nothing to sell is a TREND, not an OPPORTUNITY."""
        for commercial in ({"type": "none"}, {"type": "team"}, None):
            self.assertIn(
                HI.classify_level(90, commercial=commercial, items=6, sources=4,
                                  velocity={"pct": 80.0}, timing_open=True),
                ("TREND", "SIGNAL"))

    def test_action_needs_an_open_window(self):
        self.assertEqual(
            HI.classify_level(88, commercial={"type": "exact"}, items=6, sources=4,
                              velocity={"pct": 80.0}, timing_open=False),
            "OPPORTUNITY")

    def test_trend_needs_acceleration(self):
        flat = {"pct": 0.0, "accelerating": False}
        rising = {"pct": 120.0, "accelerating": True}
        self.assertEqual(HI.classify_level(40, items=4, sources=3, velocity=flat), "SIGNAL")
        self.assertEqual(HI.classify_level(40, items=4, sources=3, velocity=rising), "TREND")

    def test_one_outlet_repeating_itself_is_not_a_signal(self):
        self.assertEqual(
            HI.classify_level(70, commercial={"type": "exact"}, items=9, sources=1,
                              velocity={"pct": 90.0}),
            "HEADLINE")

    def test_ladder_order_is_action_down_to_headline(self):
        self.assertEqual(HI.LEVELS, ("HEADLINE", "SIGNAL", "TREND", "OPPORTUNITY", "ACTION"))
        self.assertEqual(HI.SHOWN_FROM, "SIGNAL")
        self.assertEqual((HI.ACTION_MIN, HI.OPPORTUNITY_MIN), (75, 60))


class Velocity(unittest.TestCase):
    def test_rising_window_is_a_percentage(self):
        items = ([item("a", minutes_ago=m) for m in (2, 5, 9, 14)] +
                 [item("b", minutes_ago=m) for m in (70, 80, 95, 110)])
        vel = HI.compute_velocity(items)
        self.assertEqual(vel["window_minutes"], 60)
        self.assertEqual(vel["recent"], 4)
        self.assertEqual(vel["baseline"], 4)
        self.assertEqual(vel["pct"], 0.0)
        self.assertFalse(vel["accelerating"])
        self.assertIn("/ 60 min", vel["label"])

    def test_falling_coverage_is_reported_as_falling(self):
        items = [item("a", minutes_ago=m) for m in (5,)] + [item("b", minutes_ago=m) for m in (70, 80, 90, 100)]
        vel = HI.compute_velocity(items)
        self.assertLess(vel["pct"], 0)
        self.assertTrue(vel["label"].startswith("↓"))
        self.assertFalse(vel["accelerating"])

    def test_a_new_burst_is_not_a_fake_percentage(self):
        """No baseline means 'new', not infinity - and it still counts as accelerating."""
        items = [item("a", minutes_ago=m) for m in (3, 25)]
        vel = HI.compute_velocity(items)
        self.assertIsNone(vel["pct"])
        self.assertEqual(vel["baseline"], 0)
        self.assertTrue(vel["accelerating"])
        self.assertIn("new", vel["label"])

    def test_no_timestamps_is_said_out_loud(self):
        undated = [item("a")]
        for it in undated:
            it["ts"] = None
        self.assertIsNone(HI.compute_velocity(undated)["pct"])
        self.assertEqual(HI.compute_velocity(undated)["label"], "no timestamped evidence")


class Sentiment(unittest.TestCase):
    def test_cleveland_defiance_is_named_in_cleveland_words(self):
        brain = HI.TEAM_BRAINS["cleveland-browns"]
        out = HI.analyze_sentiment(["they're counting Cleveland out again",
                                    "time to prove them wrong", "nobody believes in us"], brain)
        self.assertEqual(out["label"], "defiant")
        self.assertGreater(out["strength"], 0)
        hit_words = [w for words in out["hits"].values() for w, _ in words]
        self.assertIn("counting", hit_words)
        self.assertIn("prove them wrong", hit_words)

    def test_michigan_house_motto_reads_defiant_only_in_michigan(self):
        text = ["respond - nothing given, everything earned"]
        michigan = HI.analyze_sentiment(text, HI.TEAM_BRAINS["michigan"])
        cleveland = HI.analyze_sentiment(text, HI.TEAM_BRAINS["cleveland-browns"])
        self.assertEqual(michigan["label"], "defiant")
        self.assertNotEqual(michigan["label"], cleveland["label"])

    def test_no_evidence_is_neutral_not_invented(self):
        out = HI.analyze_sentiment(["the weather is fine"], HI.TEAM_BRAINS["dallas-cowboys"])
        self.assertEqual(out["label"], "neutral")
        self.assertEqual(out["strength"], 0.0)

    def test_four_brains_are_actually_distinct(self):
        brains = HI.TEAM_BRAINS
        self.assertEqual(set(brains), {"cleveland-browns", "green-bay-packers",
                                       "dallas-cowboys", "michigan"})
        players = {t: set(b["players"]) for t, b in brains.items()}
        topics = {t: {x["key"] for x in b["topics"]} for t, b in brains.items()}
        for team, names in players.items():
            for other, other_names in players.items():
                if team != other:
                    self.assertNotEqual(names, other_names)
                    # Each brain must own players the others do not. Micah Parsons
                    # legitimately appears in both Dallas (Doomsday memory) and
                    # Green Bay (he is a Packer now), so overlap is allowed but it
                    # can never be the whole brain.
                    self.assertGreaterEqual(len(names - other_names), 3,
                                            f"{team} has no players of its own vs {other}")
        # Topic keys are unique per team - no shared topic definitions.
        for team, keys in topics.items():
            for other, other_keys in topics.items():
                if team != other:
                    self.assertFalse(keys & other_keys, f"{team}/{other} share topics")
        self.assertIn("underwood-era", topics["michigan"])
        self.assertIn("recruiting", topics["michigan"])
        self.assertIn("no-fly-zone", topics["cleveland-browns"])
        self.assertIn("love-era", topics["green-bay-packers"])
        self.assertIn("doomsday", topics["dallas-cowboys"])


class GameState(unittest.TestCase):
    def test_live_window_uses_the_real_kickoff(self):
        kickoff = HI._parse_ts(HI._SEASON["cleveland-browns"]["kickoff"])
        now = kickoff + dt.timedelta(minutes=40)
        pool = {"items": [item("opening drive ends in an interception", minutes_ago=4)], "now": now}
        state = HI.get_game_state("cleveland-browns", pool, now)
        self.assertEqual(state["state"], "live")
        self.assertTrue(state["timing_open"])
        self.assertEqual(state["minutes"], 40)

    def test_finished_game_with_fresh_result_coverage_is_still_a_window(self):
        now = dt.datetime.now(UTC)
        pool = {"items": [item("Michigan upsets Oklahoma in the final minute", minutes_ago=120,
                               team="michigan")], "now": now}
        state = HI.get_game_state("michigan", pool, now)
        self.assertEqual(state["state"], "recent-result")
        self.assertTrue(state["timing_open"])

    def test_next_week_is_a_window_and_next_month_is_not(self):
        now = HI._parse_ts(HI._NEXT_GAME["dallas-cowboys"]) - dt.timedelta(days=3)
        self.assertTrue(HI.get_game_state("dallas-cowboys", {"items": []}, now)["timing_open"])
        later = HI._parse_ts(HI._NEXT_GAME["dallas-cowboys"]) + dt.timedelta(days=3)
        state = HI.get_game_state("dallas-cowboys", {"items": []}, later)
        self.assertEqual(state["state"], "off-week")
        self.assertFalse(state["timing_open"])


class CommercialMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = HI.load_products()

    def test_no_fly_zone_finds_the_denzel_design(self):
        topic = {"commercial": ["no fly zone", "denzel"], "campaign": "NO FLY ZONE"}
        match = HI.find_commercial_match("cleveland-browns", topic, self.products)
        self.assertEqual(match["type"], "exact")
        self.assertIn("no fly zone", match["design"]["title"].lower())
        self.assertTrue(match["design"]["sellable"])
        self.assertTrue(match["design"]["url"].startswith("http"))
        self.assertTrue(match["design"]["price"].startswith("$"))

    def test_a_demand_we_own_no_design_for_never_claims_a_match(self):
        """No Watson design exists - the board must not pretend one does."""
        topic = {"commercial": ["deshaun watson", "watson 4"], "campaign": "QB1"}
        match = HI.find_commercial_match("cleveland-browns", topic, self.products)
        self.assertEqual(match["type"], "team")
        self.assertNotIn("watson", match["design"]["title"].lower())
        # The reason must name a generic team term, never a Watson design.
        self.assertRegex(match["reason"], r"'(browns|cleveland|dawg|dwag|go browns|cle|ohio)'")

    def test_a_team_with_no_shelf_at_all_is_a_gap(self):
        match = HI.find_commercial_match("nowhere-team",
                                        {"commercial": ["unicorn tee"]}, self.products)
        self.assertEqual(match["type"], "none")
        self.assertIsNone(match["design"])

    def test_sellable_beats_the_stale_crawl(self):
        """products_live.json holds dead campaigns; catalogue-live.json is the truth."""
        topic = {"commercial": ["denzel", "no fly zone"], "campaign": "NO FLY ZONE"}
        match = HI.find_commercial_match("cleveland-browns", topic, self.products)
        self.assertTrue(match["design"]["sellable"])
        self.assertNotIn("crawl artefact", match["reason"])

    def test_a_womens_cut_is_not_pushed_on_a_gameday_post(self):
        gameday = HI.find_commercial_match(
            "dallas-cowboys", {"commercial": ["dallas football", "star", "dallas"]}, self.products)
        pride = HI.find_commercial_match(
            "dallas-cowboys", {"commercial": ["this girl loves", "texas pride", "flag"],
                               "women": True}, self.products)
        self.assertNotIn("this girl", gameday["design"]["title"].lower())
        self.assertIn("this girl", pride["design"]["title"].lower())


class Confidence(unittest.TestCase):
    def test_weights_sum_to_a_hundred(self):
        self.assertEqual(sum(HI.WEIGHTS.values()), 100)

    def test_fan_reaction_is_capped_while_no_fan_connector_is_attached(self):
        evidence = {"items": 12, "weighted": 24.0, "sources": 6, "fan_posts": 0,
                    "velocity": {"pct": 400.0, "accelerating": True},
                    "sentiment": {"strength": 1.0}, "game": {"state": "live"},
                    "commercial": {"type": "exact"}, "freshness_min": 5}
        out = HI.compute_confidence(evidence)
        fan = [p for p in out["parts"] if p["key"] == "fan_reaction"][0]
        self.assertLessEqual(fan["points"], HI.FAN_REACTION_CAPPED)
        self.assertIn("no fan posts", fan["note"])
        self.assertLess(out["score"], 100)

    def test_connecting_a_fan_source_unlocks_the_rest_of_the_scale(self):
        base = {"items": 12, "weighted": 24.0, "sources": 6,
                "velocity": {"pct": 400.0, "accelerating": True},
                "sentiment": {"strength": 1.0}, "game": {"state": "live"},
                "commercial": {"type": "exact"}, "freshness_min": 5}
        without = HI.compute_confidence(dict(base, fan_posts=0))["score"]
        with_fans = HI.compute_confidence(dict(base, fan_posts=30))["score"]
        self.assertGreater(with_fans, without)
        self.assertEqual(with_fans, 100)

    def test_stale_and_flat_scores_lower_than_fresh_and_rising(self):
        stale = HI.compute_confidence({"items": 3, "weighted": 3.0, "sources": 2,
                                       "fan_posts": 0, "velocity": {"pct": -60.0},
                                       "sentiment": {"strength": 0.1},
                                       "game": {"state": "off-week"},
                                       "commercial": {"type": "team"},
                                       "freshness_min": 60 * 40})
        fresh = HI.compute_confidence({"items": 8, "weighted": 16.0, "sources": 4,
                                       "fan_posts": 0, "velocity": {"pct": 150.0},
                                       "sentiment": {"strength": 0.9},
                                       "game": {"state": "live"},
                                       "commercial": {"type": "exact"},
                                       "freshness_min": 12})
        self.assertGreater(fresh["score"], stale["score"])
        self.assertLessEqual(fresh["score"], 100)


class BoardPayload(unittest.TestCase):
    """The whole board, built from the tracked data files."""

    @classmethod
    def setUpClass(cls):
        cls.payload = HI.hunt_opportunities()

    def test_headline_level_never_reaches_the_board(self):
        # No assumption that the news cycle is busy: on a quiet night the board
        # may be empty, and the invariants below still have to hold.
        for opp in self.payload["opportunities"]:
            self.assertIn(opp["level"], ("SIGNAL", "TREND", "OPPORTUNITY", "ACTION"))
            self.assertGreaterEqual(HI.LEVEL_RANK[opp["level"]], HI.LEVEL_RANK["SIGNAL"])
        self.assertEqual(self.payload["counts"]["HEADLINE"], len(self.payload["filtered"]))

    def test_opportunities_are_ranked_by_level_then_confidence(self):
        keys = [(HI.LEVEL_RANK[o["level"]], o["confidence"]) for o in self.payload["opportunities"]]
        self.assertEqual(keys, sorted(keys, reverse=True))
        self.assertEqual([o["rank"] for o in self.payload["opportunities"]],
                         list(range(1, len(self.payload["opportunities"]) + 1)))

    def test_every_shown_card_has_real_evidence(self):
        for opp in self.payload["opportunities"]:
            e = opp["evidence"]
            self.assertGreaterEqual(e["items"], HI.SIGNAL_MIN_ITEMS, opp["title"])
            self.assertGreaterEqual(e["sources"], HI.SIGNAL_MIN_SOURCES, opp["title"])
            self.assertGreaterEqual(e["weighted"], HI.SIGNAL_MIN_WEIGHT, opp["title"])
            self.assertTrue(e["velocity"].get("label"))
            self.assertTrue(e["sentiment"].get("label"))
            self.assertTrue(e["game"].get("label"))
            self.assertLessEqual(opp["confidence"], 100)
            self.assertIn(opp["status"], ("READY", "PREP", "WATCH", "STALE"))
            self.assertTrue(opp["status_emoji"])

    def test_opportunity_and_above_always_have_something_to_sell(self):
        for opp in self.payload["opportunities"]:
            if opp["level"] in ("OPPORTUNITY", "ACTION"):
                self.assertGreaterEqual(opp["confidence"], HI.OPPORTUNITY_MIN)
                self.assertIn(opp["commercial"]["type"], ("exact", "campaign"), opp["title"])
                self.assertTrue(opp["commercial"]["design"], opp["title"])
                self.assertTrue(opp["actions"], "an opportunity needs a posting plan")
            if opp["level"] == "ACTION":
                self.assertGreaterEqual(opp["confidence"], HI.ACTION_MIN)
                self.assertTrue(opp["evidence"]["game"]["timing_open"])

    def test_article_ideas_only_exist_for_opportunity_plus(self):
        eligible = {o["team"] for o in self.payload["opportunities"]
                    if o["level"] in ("OPPORTUNITY", "ACTION") and o["commercial"].get("design")}
        if not eligible:
            # Quiet news cycle: nothing at OPPORTUNITY+ with a matched design
            # means the article list must be empty - no drafting from thinner
            # evidence.
            self.assertEqual(self.payload["articles"], [])
        for art in self.payload["articles"]:
            self.assertIn(art["team"], eligible)
            self.assertIn(art["type"], ("Medium", "Quora", "Reddit"))
        ineligible = {o["team"] for o in self.payload["opportunities"]
                      if o["level"] in ("SIGNAL", "TREND")} - eligible
        for art in self.payload["articles"]:
            self.assertNotIn(art["team"], ineligible)

    def test_the_board_answers_the_question(self):
        board = self.payload["board"]
        if not self.payload["opportunities"]:
            # Nothing on the board, nothing to answer - an empty night is a
            # None board, not an invented recommendation.
            self.assertIsNone(board)
            return
        self.assertIsNotNone(board)
        for field in ("answer", "product", "platform", "timing", "confidence",
                      "level", "status", "status_emoji", "creative", "campaign"):
            self.assertTrue(board.get(field), f"board answer is missing {field}")

    def test_disconnected_fan_sources_are_reported_not_faked(self):
        self.assertEqual(self.payload["fan_sources_live"], [])
        # fan_connector_state has two honest disconnected phrasings - "no fan
        # connector configured in marketing/social-signals.json" and "no fan
        # posts observed - ...". Both must be accepted; asserting one exact
        # sentence fails whenever the other is the truth.
        self.assertIn("no fan", self.payload["fan_note"])
        for opp in self.payload["opportunities"]:
            self.assertEqual(opp["evidence"]["fan_posts"], 0)

    def test_utility_listings_are_counted_but_excluded(self):
        """'How to watch' copy must show up as excluded, never as demand.

        ``all_items`` is everything a topic matched; ``utility`` is the TV
        listing / how-to-watch slice of it; ``items`` is the reaction left
        after those are removed. The arithmetic must close for every card on
        the board - busy night or quiet - instead of assuming the current
        data happens to contain utility copy.
        """
        for opp in self.payload["opportunities"]:
            e = opp["evidence"]
            self.assertGreaterEqual(e["all_items"], 0, opp["title"])
            self.assertGreaterEqual(e["items"], 0, opp["title"])
            self.assertGreaterEqual(e["utility"], 0, opp["title"])
            self.assertEqual(
                e["items"] + e["utility"], e["all_items"],
                f"{opp['title']}: utility listings are counted in all_items "
                "but must be excluded from the reaction")

    def test_a_quiet_news_day_gives_an_empty_board_not_a_crash(self):
        """Feeds that come back empty must yield an empty board, not a crash.

        A dead Reddit feed plus a Google News drought is a real, recurring
        state of the world. The honest output is "nothing cleared SIGNAL",
        with the gap named - never an exception and never invented demand.
        """
        payload = HI.hunt_opportunities(trends={}, signals={}, products={})
        self.assertEqual(payload["opportunities"], [])
        self.assertEqual(payload["filtered"], [])
        self.assertEqual(payload["articles"], [])
        self.assertIsNone(payload["board"])
        self.assertEqual(
            payload["counts"],
            {"SIGNAL": 0, "TREND": 0, "OPPORTUNITY": 0, "ACTION": 0, "HEADLINE": 0})
        self.assertEqual(payload["fan_sources_live"], [])
        self.assertIn("no fan", payload["fan_note"])
        for team, meta in payload["teams"].items():
            self.assertEqual(meta["shown"], 0, team)
            self.assertEqual(meta["best"], "", team)

    def test_the_old_generic_advice_is_gone_from_the_payload(self):
        blob = repr(self.payload).lower()
        self.assertNotIn("post your cleveland browns shirt with angle", blob)
        self.assertNotIn("1 mentions", blob)


class GeneratedDashboard(unittest.TestCase):
    """src/hq.py must run and emit the dashboard + report without touching the repo."""

    @classmethod
    def setUpClass(cls):
        cls._sandbox = generator_sandbox()
        cls.root = cls._sandbox.__enter__()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        cls.proc = subprocess.run([sys.executable, os.path.join("src", "hq.py")],
                                  cwd=cls.root, capture_output=True, text=True, env=env)
        cls.html = (cls.root / "ops" / "hq" / "index.html").read_text(encoding="utf-8")
        cls.report = (cls.root / "trend-report.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._sandbox.__exit__(None, None, None)

    def test_generator_exits_clean_and_reports_the_ladder(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertIn("opportunities", self.proc.stdout)
        self.assertIn("headlines filtered", self.proc.stdout)

    def test_dashboard_keeps_the_ui_and_noindex(self):
        self.assertIn('<meta name="robots" content="noindex,nofollow,noarchive">', self.html)
        self.assertIn("<title>HQ - Hunter | Gridiron Locker</title>", self.html)
        self.assertIn("You post,", self.html)
        self.assertIn("--canvas:#070e1a", self.html)

    def test_dashboard_shows_evidence_product_action_and_status(self):
        # The evidence grid, commercial box, action box, board answer and the
        # status emojis are per-card content. On a quiet night the board is
        # empty and the honest dashboard is the "Nothing cleared SIGNAL" state
        # plus the section chrome and the five-badge ladder - so the per-card
        # needles are only required when a card actually exists.
        quiet = "Nothing cleared SIGNAL" in self.html
        needles = ("Opportunities — ranked by confidence", "Filtered as HEADLINE",
                   "The ladder")
        if not quiet:
            needles += ('class="evi"', "Commercial match", "Recommended action",
                        "Best thing Gridiron Locker should do right now",
                        "Phrase velocity", "Game state")
        for needle in needles:
            self.assertIn(needle, self.html, f"missing {needle}")
        # The ladder always renders all five level badges, busy or quiet.
        self.assertRegex(self.html, r'class="badge lvl-(ACTION|OPPORTUNITY|TREND|SIGNAL)"')
        if not quiet:
            self.assertRegex(self.html, r"[🟢🟡⚪🔴]")

    def test_generic_headline_advice_is_gone(self):
        self.assertNotIn("with angle:", self.html)
        self.assertNotIn(">trending 1 mentions<", self.html)
        self.assertNotIn("FTI 0</div>", self.html)

    def test_report_matches_the_board(self):
        self.assertIn("## What to do right now", self.report)
        self.assertIn("## Filtered as HEADLINE", self.report)
        self.assertIn("## Article ideas (OPPORTUNITY+ only)", self.report)
        if "Nothing cleared SIGNAL this run" in self.report:
            # Quiet night: the report says so out loud and invents no levels.
            self.assertNotRegex(self.report, r"Level: (ACTION|OPPORTUNITY|TREND|SIGNAL)")
        else:
            self.assertRegex(self.report, r"Level: (ACTION|OPPORTUNITY|TREND|SIGNAL)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
