#!/usr/bin/env python3
"""Build the commercial NFL fan marketing brief.

This is the executable companion to the NFL Fan Commerce Marketing Agent role.
It intentionally does not publish, call social APIs, or invent market data. It
turns the repository's existing trend snapshot and scored product catalogue into
an inspectable decision brief, and labels every unavailable signal so a future
connector can be added without pretending it already exists.

Inputs:
  data/trends.json, src/collections_data.py, marketing/plan.json,
  marketing/performance-memory.json (optional)

Output:
  marketing/commercial-brief.json
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MARKETING_DIR = ROOT / "marketing"
PLAN_PATH = MARKETING_DIR / "plan.json"
TRENDS_PATH = ROOT / "data" / "trends.json"
MEMORY_PATH = MARKETING_DIR / "performance-memory.json"
OUTPUT_PATH = MARKETING_DIR / "commercial-brief.json"

sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))
from collections_data import SEASON  # noqa: E402

ROLE_ID = "nfl-fan-commerce-marketing-agent"
ROLE_NAME = "NFL Fan Commerce Marketing Agent"

FAN_MOTIVATIONS = {
    "identity": {
        "label": "Identity",
        "question": "What does wearing this say about the fan?",
        "signals": ["team/city language", "fan-base language", "everyday wearability"],
    },
    "player_belief": {
        "label": "Player belief",
        "question": "Which player or number does the fan believe in?",
        "signals": ["player", "number", "breakout story", "future-facing copy"],
    },
    "emotion": {
        "label": "Emotion",
        "question": "What feeling does the design let the fan wear?",
        "signals": ["hope", "confidence", "anger", "resilience", "hype"],
    },
    "culture": {
        "label": "Culture",
        "question": "What ritual, chant, nickname, or in-group reference does it share?",
        "signals": ["tailgate", "chants", "inside jokes", "game-day rituals"],
    },
    "defensive_identity": {
        "label": "Defensive identity",
        "question": "Does it express toughness, trenches, pressure, or defense-first pride?",
        "signals": ["defense", "trenches", "the wall", "pressure", "no fly zone"],
    },
    "nostalgia": {
        "label": "Nostalgia",
        "question": "What era, memory, or old-school visual language is being reclaimed?",
        "signals": ["retro", "vintage", "heritage", "aged print", "old-school"],
    },
    "rivalry": {
        "label": "Rivalry",
        "question": "What side is the fan choosing?",
        "signals": ["versus", "everyone", "challenge", "opponent banter"],
    },
    "humor": {
        "label": "Humor",
        "question": "What would only this fan group understand?",
        "signals": ["joke", "wordplay", "self-aware frustration", "shareability"],
    },
    "belief": {
        "label": "Belief",
        "question": "What future outcome is the fan willing to declare early?",
        "signals": ["next year", "never give up", "we believe", "underdog"],
    },
    "fashion": {
        "label": "Fashion",
        "question": "Would the fan wear it when they are not watching football?",
        "signals": ["minimal", "streetwear", "oversized", "vintage wash", "outfit"],
    },
    "moment": {
        "label": "Moment",
        "question": "Which play, result, or turning point does it preserve?",
        "signals": ["game result", "play", "breakout", "reaction", "this was that"],
    },
}

DESIGN_STYLES = [
    "vintage", "distressed", "oversized", "minimalist", "streetwear", "retro",
    "collegiate", "aggressive", "illustrated", "typography-heavy", "player-focused",
    "number-focused", "slogan-focused", "mascot-inspired", "defense/trench",
    "old-school newspaper", "racing-inspired", "workwear", "luxury sportswear",
    "washed/aged", "heavyweight graphic", "hand-drawn", "photographic", "collage",
]

SOURCE_REGISTRY = {
    "nfl_news": {"status": "wired", "source": "data/trends.json via Google News RSS", "cadence": "twice daily workflow"},
    "team_news": {"status": "wired", "source": "collection feeds in data/trends.json", "cadence": "twice daily workflow"},
    "player_news": {"status": "wired", "source": "tracked entity mentions and moments", "cadence": "twice daily workflow"},
    "injuries_trades_signings_coaching": {"status": "partial", "source": "detected only when present in captured headlines", "cadence": "headline window"},
    "game_results_upcoming_games": {"status": "partial", "source": "src/collections_data.py season snapshot", "cadence": "season snapshot"},
    "reddit": {"status": "not_connected", "source": "connector required", "cadence": None},
    "x": {"status": "not_connected", "source": "connector required", "cadence": None},
    "tiktok_creative_center": {"status": "not_connected", "source": "manual/API import required", "cadence": None},
    "instagram": {"status": "not_connected", "source": "account disabled; do not automate", "cadence": None},
    "youtube": {"status": "not_connected", "source": "connector required", "cadence": None},
    "google_search_trends": {"status": "not_connected", "source": "Search Console/Trends connector required", "cadence": None},
    "pinterest_trends": {"status": "not_connected", "source": "Pinterest Trends connector required", "cadence": None},
    "competitors": {"status": "manual_only", "source": "no live rival catalogue feed is wired", "cadence": None},
}

PLATFORM_PLAYBOOKS = {
    "instagram": {"job": "discovery and saves", "formats": ["Reels", "product imagery", "Stories"], "optimize_for": ["saves", "shares", "product discovery"]},
    "pinterest": {"job": "evergreen search and outfit discovery", "formats": ["vertical pins", "idea-led product imagery"], "optimize_for": ["search intent", "saves", "seasonal and gift discovery"]},
    "tiktok": {"job": "fast creative learning", "formats": ["native short video", "creator-style fit checks"], "optimize_for": ["hook rate", "watch time", "comments", "fast experiments"]},
    "x": {"job": "real-time football conversation", "formats": ["reaction", "question", "original visual"], "optimize_for": ["timing", "replies", "conversation"]},
    "facebook": {"job": "community and shareable product discovery", "formats": ["original posts", "community prompts", "product stories"], "optimize_for": ["shares", "comments", "clicks"]},
}

CONTENT_REPURPOSING = {
    "reel": 1,
    "stories": 3,
    "pinterest_pins": 5,
    "x_posts": 2,
    "facebook_post": 1,
    "tiktok": 1,
    "product_page_seo_angle": 1,
    "blog_opportunity": 1,
}

CREATIVE_CONCEPTS = [
    ("Premium product detail", "Make the graphic and garment quality the hero."),
    ("Stadium tunnel", "Place the product in a charged but logo-free game-day environment."),
    ("Defensive identity", "Translate the design into toughness, trenches, or mentality."),
    ("Game-day outfit", "Show how the piece works as an outfit, not only as fan merch."),
    ("Close-up graphic", "Let typography, number, texture, or print treatment carry the frame."),
    ("Vintage sports poster", "Use archival composition and print texture without copying protected art."),
    ("Streetwear fit", "Frame the product as everyday style beyond the stadium."),
    ("Fan reaction", "Use a question or reaction prompt; do not fabricate a fan testimonial."),
    ("Storyline connection", "Connect only to a verified current moment and hold names at the compliance gate."),
    ("Gift angle", "Help a buyer choose the piece for a fan, occasion, or game-day ritual."),
]

EXPERIMENTS = [
    {"id": "hook-player", "variant": "Player/storyline hook", "control": "generic product announcement", "metric": "product-page clicks and assisted orders"},
    {"id": "hook-identity", "variant": "Fan-identity hook", "control": "generic product announcement", "metric": "saves, shares, and product-page clicks"},
    {"id": "hook-fashion", "variant": "Fashion/outfit hook", "control": "game-day-only framing", "metric": "saves, outbound clicks, conversion rate"},
    {"id": "hook-game-day", "variant": "Game-day timing hook", "control": "evergreen timing", "metric": "click-through rate and conversion rate"},
]

EMOTION_BY_THEME = {
    "player": ("belief", "hopeful"),
    "playoff": ("moment", "hyped"),
    "funny": ("humor", "amused"),
    "retro": ("nostalgia", "nostalgic"),
    "family": ("culture", "warm"),
    "city": ("identity", "proud"),
    "classic": ("identity", "confident"),
    "halloween": ("humor", "playful"),
}


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def normalized(text: Any) -> str:
    return re.sub(r"[^a-z0-9/ -]+", " ", str(text or "").lower())


def infer_styles(item: dict[str, Any]) -> list[str]:
    text = normalized(" ".join(str(item.get(k, "")) for k in ("name", "design_text", "theme", "product_type")))
    theme = str(item.get("theme", "classic")).lower()
    styles: list[str] = []

    def add(*values: str) -> None:
        for value in values:
            if value in DESIGN_STYLES and value not in styles:
                styles.append(value)

    if theme == "retro" or any(x in text for x in ("vintage", "1960", "heritage")):
        add("vintage", "retro", "washed/aged")
    if theme == "player" or any(x in text for x in ("player", "qb", "number", "signature")):
        add("player-focused", "number-focused")
    if theme == "playoff" or any(x in text for x in ("defense", "determined", "never give")):
        add("aggressive", "slogan-focused", "defense/trench")
    if theme == "funny" or any(x in text for x in ("funny", "joke", "beer", "coach")):
        add("typography-heavy", "hand-drawn")
    if theme == "city" or any(x in text for x in ("est ", "ohio", "texas", "wisconsin")):
        add("collegiate", "workwear", "typography-heavy")
    if theme == "family":
        add("hand-drawn", "fashion")
    if "hoodie" in text or "sweatshirt" in text or "crewneck" in text:
        add("streetwear", "heavyweight graphic")
    if not styles:
        add("slogan-focused", "typography-heavy")
    return styles[:5]


def infer_motivation(item: dict[str, Any]) -> tuple[str, str]:
    theme = str(item.get("theme", "classic")).lower()
    if theme in EMOTION_BY_THEME:
        return EMOTION_BY_THEME[theme]
    return ("identity", "confident")


def matched_trend(item: dict[str, Any], plan: dict[str, Any], trends: dict[str, Any]) -> dict[str, Any]:
    ckey = item.get("collection", "")
    collection = trends.get("collections", {}).get(ckey, {})
    opp = item.get("opportunity", {}) or {}
    entities = (item.get("score_breakdown", {}) or {}).get("headline_name_matches", [])
    entity = next((x for x in entities if int(x.get("mentions", 0) or 0) > 0), None)
    strategy = next((x for x in plan.get("strategy", []) if x.get("collection") == ckey), {})
    if entity:
        label = entity.get("name", "current storyline")
        mentions = int(entity.get("mentions", 0) or 0)
        signal = f"{label} conversation ({mentions} captured headline mentions)"
    else:
        label = strategy.get("headline") or collection.get("query") or "football fan demand"
        signal = label
        mentions = 0
    return {
        "signal": signal,
        "entity": label,
        "mentions": mentions,
        "stage": opp.get("trend_stage", "MAINSTREAM"),
        "source_count": len(collection.get("headlines", []) or []),
        "evidence": "captured headline snapshot" if collection else "no collection trend snapshot",
    }


def timing_score(stage: str, theme: str) -> int:
    values = {"ACCELERATING": 95, "EMERGING": 80, "MAINSTREAM": 62, "SATURATED": 42, "DECLINING": 15}
    score = values.get(stage, 50)
    if theme in {"playoff", "player"}:
        score += 4
    return clamp(score)


def commercial_factors(item: dict[str, Any], trend: dict[str, Any], styles: list[str]) -> dict[str, int]:
    opp = item.get("opportunity", {}) or {}
    source_factors = opp.get("factors", {}) or {}
    theme = str(item.get("theme", "classic")).lower()
    score = int(item.get("score", 50) or 50)
    price = float(item.get("price_usd") or 0) if str(item.get("price_usd") or "").replace(".", "", 1).isdigit() else 0
    level = (opp.get("compliance", {}) or {}).get("level", "low")

    demand = clamp(score * 0.65 + int(source_factors.get("audience", 50)) * 0.35)
    trend_relevance = clamp(int(source_factors.get("search", 40)) * 0.45 + int(source_factors.get("velocity", 30)) * 0.55)
    motivation, _ = infer_motivation(item)
    fan_emotion = clamp(62 + (16 if motivation in {"moment", "player_belief", "belief"} else 8) + (8 if theme in {"playoff", "player", "funny"} else 0))
    visual_strength = clamp(52 + len(styles) * 7 + (12 if item.get("image_url") else 0) + (8 if len(str(item.get("design_text", ""))) >= 12 else 0))
    commercial_potential = clamp(55 + (18 if price >= 30 else 10 if price >= 24 else 0) + (12 if "streetwear" in styles or "heavyweight graphic" in styles else 0))
    seasonality = timing_score(trend.get("stage", "MAINSTREAM"), theme)
    # This is pressure, unlike plan.py's competitive-weakness factor: higher is worse.
    competition_pressure = clamp(100 - int(source_factors.get("competition", 50)))
    ip_risk = {"low": 10, "medium": 60, "high": 95}.get(level, 60)
    versatility = clamp(54 + len(styles) * 7 + (12 if theme in {"funny", "retro", "family", "classic"} else 5))
    return {
        "demand": demand,
        "trend_relevance": trend_relevance,
        "fan_emotion": fan_emotion,
        "visual_strength": visual_strength,
        "commercial_potential": commercial_potential,
        "seasonality": seasonality,
        "competition_pressure": competition_pressure,
        "ip_compliance_risk": ip_risk,
        "content_versatility": versatility,
    }


def opportunity_score(factors: dict[str, int]) -> tuple[int, float]:
    # Geometric mean keeps one weak commercial input from being hidden by a
    # large audience score. It is the normalized form of the requested
    # Demand × Trend × Fan Emotion × Commercial Fit × Timing equation.
    core_keys = ("demand", "trend_relevance", "fan_emotion", "commercial_potential", "seasonality")
    values = [max(1, factors[key]) / 100 for key in core_keys]
    core = 100 * math.prod(values) ** (1 / len(values))
    adjusted = core * (1 - factors["competition_pressure"] / 400)
    return clamp(adjusted), round(core, 1)


def hook_for(item: dict[str, Any], motivation: str, emotion: str, trend: dict[str, Any]) -> str:
    name = str(item.get("name", "this design"))
    hooks = {
        "identity": f"Some fans wear the team. Others wear the mentality — {name}.",
        "player_belief": f"The design for fans who still believe in the next chapter: {name}.",
        "emotion": f"Built for the feeling that makes game day matter: {name}.",
        "culture": f"The in-group reference your football people will recognize: {name}.",
        "defensive_identity": f"For fans who believe the trenches set the tone: {name}.",
        "nostalgia": f"Old-school football energy, rebuilt for the way fans dress now: {name}.",
        "rivalry": f"You know exactly which side you are on: {name}.",
        "humor": f"Only football fans will get why {name} exists.",
        "belief": f"Built for the fans who never stopped believing: {name}.",
        "fashion": f"Football does not have to look generic: {name}.",
        "moment": f"This is the feeling fans want to remember: {name}.",
    }
    return hooks.get(motivation, hooks["identity"])


def creative_concepts(item: dict[str, Any], trend: dict[str, Any]) -> list[dict[str, str]]:
    """Return ten distinct jobs for one existing product, not ten duplicates."""
    return [
        {"concept": name, "job": job, "product": str(item.get("name", "")), "trend": trend.get("signal", "")}
        for name, job in CREATIVE_CONCEPTS
    ]


def pinterest_seo_package(item: dict[str, Any]) -> dict[str, Any]:
    """Draft Pinterest discovery assets without claiming search-volume data."""
    collection = str(item.get("collection_label", "football"))
    name = str(item.get("name", "football apparel"))
    keywords = list(dict.fromkeys(item.get("keywords") or []))
    return {
        "status": "DRAFT_NO_PINTEREST_TRENDS_CONNECTED",
        "title_variants": [
            f"{name} Game Day Outfit Idea",
            f"{collection} Football Apparel Style",
            f"Football Fan Gift: {name}",
            f"{collection} Tailgate Outfit Inspiration",
            f"Football Streetwear: {name}",
        ],
        "keyword_clusters": {
            "product": keywords[:4],
            "outfit": [f"{collection} game day outfit", "football tailgate outfit", "football streetwear"],
            "gift": ["football fan gift", "game day gift idea", "football apparel gift"],
            "identity": [f"{collection} fan apparel", "football fan style", "football identity shirt"],
        },
        "description": f"A draft search-led description for {name}; validate wording and licensing before publishing.",
        "image_concepts": ["outfit detail", "tailgate texture", "gift-ready product still"],
        "keyword_stuffing_check": "Use one primary cluster and a few natural supporting terms; do not paste every keyword into the description.",
    }


def action_for(factors: dict[str, int], score: int) -> tuple[str, str]:
    if factors["ip_compliance_risk"] >= 50:
        return "HOLD_LICENSE_REVIEW", "Team/player identifiers detected; do not publish social creative until licensing/compliance is cleared."
    if score >= 70:
        return "PUBLISH", "Commercial opportunity is strong and the social risk gate is clear."
    if score >= 55:
        return "IMPROVE", "Promising product; sharpen the creative angle or collect stronger demand evidence."
    return "MONITOR", "Keep watching the signal; do not spend production effort yet."


def top_opportunities(plan: dict[str, Any], trends: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in plan.get("queue", []):
        styles = infer_styles(item)
        motivation, emotion = infer_motivation(item)
        trend = matched_trend(item, plan, trends)
        factors = commercial_factors(item, trend, styles)
        score, core = opportunity_score(factors)
        action, action_reason = action_for(factors, score)
        platforms = ["pinterest", "instagram"] if ("vintage" in styles or "fashion" in styles or "retro" in styles) else ["tiktok", "instagram"]
        if trend["mentions"] >= 2:
            platforms = ["x", "tiktok", "instagram"]
        keywords = list(dict.fromkeys([*(item.get("keywords") or []), f"{item.get('collection_label', '')} football apparel", "football game day outfit"]))[:8]
        rows.append({
            "product": item.get("name"),
            "slug": item.get("slug"),
            "team": item.get("collection_label"),
            "trend": trend["signal"],
            "trend_stage": trend["stage"],
            "fan_emotion": emotion,
            "fan_motivation": motivation,
            "creative_style": styles,
            "platforms": platforms,
            "seo_keywords": keywords,
            "hook": hook_for(item, motivation, emotion, trend),
            "sentiment": {"label": emotion, "method": "theme plus captured headline proxy", "confidence": "low until community/analytics connectors are added"},
            "creative_concepts": creative_concepts(item, trend),
            "pinterest_seo": pinterest_seo_package(item),
            "cta": "Review product page and shop after the compliance gate clears.",
            "risk": {"score": factors["ip_compliance_risk"], "level": (item.get("opportunity", {}).get("compliance", {}) or {}).get("level", "unknown"), "action": action},
            "timing": {"stage": trend["stage"], "recommendation": "CREATE NOW" if trend["stage"] == "ACCELERATING" else "PREPARE" if trend["stage"] == "EMERGING" else "EVERGREEN TEST"},
            "factors": factors,
            "core_multiplicative_score": core,
            "opportunity_score": score,
            "decision": action,
            "decision_reason": action_reason,
        })
    rows.sort(key=lambda row: (-row["opportunity_score"], row["product"] or ""))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def event_runway() -> list[dict[str, Any]]:
    runway = []
    for ckey, context in SEASON.items():
        kickoff = context.get("kickoff", "")
        runway.append({
            "team": ckey,
            "event": context.get("opener", "upcoming game"),
            "kickoff": kickoff,
            "horizons": [
                {"horizon": "today", "job": "Identify the verified story and the existing product match."},
                {"horizon": "tomorrow", "job": "Draft the next platform-native angle and check the risk gate."},
                {"horizon": "3 days", "job": "Build the storyline creative and begin the A/B test."},
                {"horizon": "7 days", "job": "Prepare the identity, outfit, and game-day runway."},
                {"horizon": "30 days", "job": "Reserve evergreen, gift, and seasonal opportunities; do not overproduce."},
            ],
            "runway": [
                {"offset": "-7d", "job": "identity/product", "content": "Lead with fan identity and an existing product match."},
                {"offset": "-3d", "job": "player/storyline", "content": "Use a verified storyline only; choose the strongest product match."},
                {"offset": "-1d", "job": "game-day product", "content": "Show outfit utility, product detail, and clear timing."},
                {"offset": "game day", "job": "reaction", "content": "Respond to the verified moment on the platform where it is happening."},
                {"offset": "+1d", "job": "result/emotion", "content": "Match the result emotion; second-push a winner only after evidence."},
            ],
        })
    return runway


def economics_schema() -> dict[str, Any]:
    return {
        "status": "NEEDS_COST_INPUTS",
        "inputs": {
            "retail_price": "product price from catalogue",
            "pod_cost": None,
            "shipping_cost": None,
            "platform_fee": None,
            "discount": None,
            "ad_cost": None,
            "average_order_value": None,
        },
        "formulas": {
            "gross_profit": "retail_price - pod_cost - shipping_cost - platform_fee - discount",
            "contribution_profit": "gross_profit - ad_cost",
            "cac": "ad_spend / new_customers",
            "roas": "revenue / ad_spend",
            "break_even_roas": "1 / contribution_margin_rate",
            "conversion_rate": "orders / qualified_sessions",
            "aov": "revenue / orders",
        },
        "decision_rule": "Attention is not success until traffic converts and contribution profit remains positive.",
        "missing_data_action": "Do not claim profit, CAC, ROAS, or break-even performance until POD, shipping, fee, discount, ad, and order data are connected.",
    }


def funnel_diagnostics() -> dict[str, Any]:
    return {
        "status": "UNMEASURED_WITHOUT_ANALYTICS_CONNECTOR",
        "stages": [
            {"stage": "post", "failure_signal": "views without saves, shares, or profile visits", "diagnosis": "creative or hook problem"},
            {"stage": "profile", "failure_signal": "profile visits without link taps", "diagnosis": "positioning, trust, or CTA problem"},
            {"stage": "website", "failure_signal": "link taps without product-page engagement", "diagnosis": "landing-page relevance or speed problem"},
            {"stage": "product_page", "failure_signal": "product views without checkout clicks", "diagnosis": "offer, imagery, copy, price, or trust problem"},
            {"stage": "checkout", "failure_signal": "checkout starts without purchases", "diagnosis": "checkout friction, shipping, payment, or economics problem"},
            {"stage": "purchase", "failure_signal": "orders without contribution profit", "diagnosis": "POD economics or acquisition-cost problem"},
        ],
        "required_events": ["content_impression", "save", "share", "profile_visit", "outbound_click", "product_view", "checkout_start", "purchase", "revenue", "cost"],
    }


def main() -> None:
    plan = read_json(PLAN_PATH, {})
    trends = read_json(TRENDS_PATH, {})
    memory = read_json(MEMORY_PATH, {"schema_version": 1, "learnings": [], "observations": []})
    if not plan.get("queue"):
        raise SystemExit("marketing/plan.json is missing or has no queue; run python3 marketing/plan.py first")

    opportunities = top_opportunities(plan, trends)
    brief = {
        "meta": {
            "generated_on": dt.date.today().isoformat(),
            "generator": "marketing/commercial_agent.py",
            "role_id": ROLE_ID,
            "role_name": ROLE_NAME,
            "human_approval_required": True,
            "auto_publish": False,
            "inputs": ["marketing/plan.json", "data/trends.json", "src/collections_data.py:SEASON", "marketing/performance-memory.json"],
        },
        "mission": "Find the football moment a fan wants to wear, match it to an existing product, adapt the creative to the platform, and prove attention became profitable action.",
        "operating_loop": ["NFL events", "trend detection", "fan sentiment", "search demand", "design/product match", "commercial opportunity score", "creative angle", "platform adaptation", "human approval", "traffic", "sales", "performance data", "learning"],
        "source_registry": SOURCE_REGISTRY,
        "fan_psychology": FAN_MOTIVATIONS,
        "sentiment_model": {
            "supported_labels": ["excited", "angry", "hopeful", "confident", "worried", "mocking", "nostalgic", "hyped", "disappointed"],
            "current_method": "theme and headline proxy only",
            "confidence_rule": "Do not call inferred emotion measured sentiment until conversation or analytics connectors provide evidence.",
        },
        "design_style_taxonomy": DESIGN_STYLES,
        "creative_director": {"concept_count_per_product": len(CREATIVE_CONCEPTS), "concepts": [name for name, _ in CREATIVE_CONCEPTS]},
        "platform_playbooks": PLATFORM_PLAYBOOKS,
        "opportunity_model": {
            "factors": ["demand", "trend_relevance", "fan_emotion", "visual_strength", "commercial_potential", "seasonality", "competition_pressure", "ip_compliance_risk", "content_versatility"],
            "formula": "normalized geometric mean of Demand × Trend relevance × Fan emotion × Commercial potential × Timing, with a competition-pressure adjustment; IP/compliance risk remains a hard publishing gate",
            "score_range": [0, 100],
            "interpretation": "Scores are decision support, not sales forecasts. Missing external demand, competitor, analytics, and cost inputs lower confidence or block a publish decision.",
        },
        "top_5_products_today": opportunities[:5],
        "all_product_opportunities": opportunities,
        "event_runway": event_runway(),
        "repurposing_engine": CONTENT_REPURPOSING,
        "experiments": EXPERIMENTS,
        "economics": economics_schema(),
        "conversion_diagnostics": funnel_diagnostics(),
        "performance_memory": memory,
        "predictor": {
            "question": "If I were an NFL fan today, what shirt would I actually want to wear?",
            "not": "What generic content should Gridiron Locker post?",
            "required_inputs": ["what fans are talking about", "what they feel", "what they search", "what they wear", "what designs perform", "what products already exist", "what football moment is coming"],
            "output": "top_5_products_today",
        },
        "limitations": [
            "Google News headline data is connected; Reddit, X, TikTok Creative Center, Instagram, YouTube, Google Trends, Pinterest Trends, rival catalogues, and performance analytics are not connected in this repository.",
            "POD cost, shipping, platform fees, discount, advertising, order, and revenue inputs are not present, so profit claims are intentionally withheld.",
            "All social output is a draft for human review. Current team/player-named designs are held by the compliance gate because licensing is unverified.",
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    top = brief["top_5_products_today"]
    print(f"wrote {OUTPUT_PATH} · {len(opportunities)} products scored · top 5 prepared · human approval required")
    for row in top:
        print(f"  {row['opportunity_score']:>3} {row['decision']:<18} {row['product']}")


if __name__ == "__main__":
    main()
