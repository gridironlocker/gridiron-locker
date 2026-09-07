#!/usr/bin/env python3
"""Turn the latest public trend signals into a rolling three-day buying plan.

The output is intentionally short-lived: today, tomorrow, and the following
 day. Run it after every trend/social collection. It matches the existing
catalogue; it does not invent new products or publish content.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = ROOT / "marketing" / "plan.json"
SIGNALS_PATH = ROOT / "marketing" / "social-signals.json"
OUTPUT_PATH = ROOT / "marketing" / "three-day-pulse.json"
IMAGES_PATH = ROOT / "marketing" / "approved-images.json"

PLATFORMS = ("instagram", "facebook", "x", "tiktok", "pinterest")
TEAM_ALIASES = {
    "cleveland-browns": ("cleveland", "browns", "dawg", "dawg pound"),
    "green-bay-packers": ("green bay", "packers", "cheesehead", "go pack go"),
    "dallas-cowboys": ("dallas", "cowboys", "texas football"),
    "michigan": ("michigan", "wolverines", "go blue", "ann arbor"),
}
EMOTIONS = {
    "hyped": ("hyped", ("hype", "excited", "big game", "playoff", "prime time", "let's go")),
    "hopeful": ("hopeful", ("believe", "future", "breakout", "qb1", "next", "hope")),
    "confident": ("confident", ("win", "dominant", "defense", "ready", "contender")),
    "worried": ("worried", ("injury", "hurt", "question", "concern", "struggle", "loss")),
    "angry": ("angry", ("fire", "bad call", "embarrassing", "angry", "frustrated")),
    "nostalgic": ("nostalgic", ("retro", "vintage", "old school", "remember")),
    "mocking": ("mocking", ("meme", "lol", "fraud", "overrated", "rivalry")),
    "disappointed": ("disappointed", ("disappoint", "lost", "decline", "missed")),
}


def read(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def numeric_price(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def source_items(signals: dict[str, Any], team: str) -> list[dict[str, Any]]:
    return [row for row in signals.get("items", []) if row.get("team") == team]


def trend_for(team: str, plan: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    rows = source_items(signals, team)
    text = " ".join(clean(row.get("text")) for row in rows).lower()
    strategy = next((row for row in plan.get("strategy", []) if row.get("collection") == team), {})
    season = plan.get("season_context", {}).get(team, {})
    signal_counts = []
    for emotion, (_, words) in EMOTIONS.items():
        count = sum(text.count(word) for word in words)
        signal_counts.append((count, emotion))
    _, emotion = max(signal_counts) if signal_counts else (0, "confident")
    if not text:
        emotion = "confident"
    top = rows[0].get("text", "") if rows else strategy.get("headline", "") or season.get("headline", "")
    stage = "ACCELERATING" if len(rows) >= 8 else "EMERGING" if len(rows) >= 3 else "MAINSTREAM"
    return {
        "team": team,
        "story": clean(top),
        "emotion": emotion,
        "stage": stage,
        "signal_count": len(rows),
        "sources": [{"source": row.get("source"), "text": row.get("text"), "url": row.get("url")} for row in rows[:5]],
        "evidence": "public signal collector" if rows else "season/headline snapshot fallback",
    }


def product_signal(product: dict[str, Any], trend: dict[str, Any]) -> float:
    text = " ".join(str(product.get(key, "")) for key in ("name", "design_text", "theme", "keywords")).lower()
    story = trend["story"].lower()
    aliases = TEAM_ALIASES.get(product.get("collection", ""), ())
    team_match = any(alias in text or alias in story for alias in aliases)
    theme = str(product.get("theme", "classic")).lower()
    value = float(product.get("score", 50) or 50) + float((product.get("opportunity") or {}).get("score", 50) or 50) * 0.35
    value += 18 if team_match else 0
    value += 12 if theme in {"player", "playoff"} and trend["emotion"] in {"hyped", "hopeful", "confident"} else 0
    value += 10 if theme == "retro" and trend["emotion"] == "nostalgic" else 0
    return value


def compliance(product: dict[str, Any]) -> dict[str, Any]:
    risk = (product.get("opportunity") or {}).get("compliance") or {}
    level = risk.get("level", "unknown")
    blocked = bool(risk.get("social_blocked", True))
    return {
        "level": level,
        "blocked": blocked,
        "decision": "HOLD_LICENSE_REVIEW" if blocked else "ELIGIBLE_FOR_APPROVAL",
    }


def copy_pack(product: dict[str, Any], trend: dict[str, Any]) -> dict[str, Any]:
    name = clean(product.get("name"))
    team = clean(product.get("collection_label"))
    product_url = clean(product.get("product_url"))
    emotion = trend["emotion"]
    story = trend["story"] or f"{team} fan conversation"
    hook = {
        "hyped": f"The {team} moment is getting louder. This is the piece for fans who are already locked in.",
        "hopeful": f"Some fans wear the team. Others wear the belief. {name} is for the second group.",
        "confident": f"Defense, identity, and a look that does not need a generic slogan: {name}.",
        "worried": f"When the football conversation gets tense, fan identity still matters: {name}.",
        "angry": f"For the fans who have something to say after that football conversation: {name}.",
        "nostalgic": f"Old-school football energy, made for the way fans dress now: {name}.",
        "mocking": f"Only the people who follow this football conversation will get {name}.",
        "disappointed": f"The result changes. The fan identity does not: {name}.",
    }.get(emotion, f"A fan-first football look for the moment: {name}.")
    ad = f"{hook} The current signal: {story}. Explore the existing product page and verify licensing before promotion."
    return {
        "hook": hook,
        "ad_copy": ad,
        "captions": {
            "instagram": f"{hook} {team} fans, save this for game day. Trend context: {story} Review the product page before publishing.",
            "facebook": f"{hook} The conversation right now: {story} See the product details and confirm the compliance gate before publishing. {product_url}".strip(),
            "x": (f"{hook} {story} {product_url}"[:277] + "…") if len(f"{hook} {story} {product_url}") > 280 else f"{hook} {story} {product_url}".strip(),
            "tiktok": f"POV: the {team} conversation shifts and you already have the fit. {hook} Verify the product and risk gate before posting.",
            "pinterest": f"{name}: a {team} game-day outfit and football fan style idea inspired by the current conversation. Validate the trend, product, and licensing before publishing.",
        },
        "pinterest": {
            "title": f"{team} Game Day Outfit: {name}",
            "description": f"A searchable football fan style draft for {name}, tied to {emotion} fan energy. Use only after the product and licensing review.",
            "keywords": [clean(keyword) for keyword in (product.get("keywords") or [])[:5]] + [f"{team} game day outfit", "football fan apparel"],
        },
    }


def images_for(images: dict[str, Any], slug: str) -> dict[str, Any]:
    return images.get(slug, {}) if isinstance(images, dict) else {}


def main() -> None:
    plan = read(PLAN_PATH, {})
    signals = read(SIGNALS_PATH, {"items": [], "sources": {}})
    images = read(IMAGES_PATH, {})
    products = plan.get("queue", [])
    generated = dt.date.today()
    days = []
    for offset in range(3):
        date = generated + dt.timedelta(days=offset)
        selected = []
        for team in TEAM_ALIASES:
            trend = trend_for(team, plan, signals)
            candidates = [product for product in products if product.get("collection") == team]
            candidates.sort(key=lambda product: product_signal(product, trend), reverse=True)
            if candidates:
                product = candidates[offset % min(3, len(candidates))]
                risk = compliance(product)
                selected.append({
                    "product": product.get("name"),
                    "slug": product.get("slug"),
                    "product_url": product.get("product_url"),
                    "team": product.get("collection_label"),
                    "trend": trend,
                    "fan_emotion": trend["emotion"],
                    "product_signal_score": round(product_signal(product, trend), 1),
                    "copy": copy_pack(product, trend),
                    "risk": risk,
                    "image": images_for(images, product.get("slug", "")),
                    "publish": {
                        "allow_auto_publish": False,
                        "reason": "Requires approved image, official platform connection, and human approval." if risk["blocked"] else "Requires approved image and official platform connection.",
                    },
                })
        selected.sort(key=lambda row: row["product_signal_score"], reverse=True)
        days.append({"date": date.isoformat(), "label": "today" if offset == 0 else "tomorrow" if offset == 1 else "+2 days", "opportunities": selected[:5]})

    connected = [name for name, value in (signals.get("sources") or {}).items() if value.get("status") == "connected"]
    payload = {
        "meta": {
            "generated_on": generated.isoformat(),
            "generator": "marketing/three_day_pulse.py",
            "horizon_days": 3,
            "refresh_rule": "Regenerate after every web/social signal collection; this is not an evergreen content calendar.",
            "connected_sources": connected,
            "human_approval_required": True,
            "auto_publish_enabled": False,
        },
        "mission": "Find what fans are talking about now, match it to an existing product, and prepare only the next three days of platform-native copy.",
        "days": days,
        "publishing": {
            "mode": "DRY_RUN",
            "official_apis_only": True,
            "image_rule": "Every publishable row needs a public approved image URL in marketing/approved-images.json.",
            "blocked_until": ["human approval", "official platform connection", "approved image", "compliance clearance"],
        },
        "signal_limits": signals.get("sources", {}),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(len(day["opportunities"]) for day in days)
    print(f"wrote {OUTPUT_PATH} · {total} short-lived opportunities · horizon 3 days · connected sources: {', '.join(connected) or 'none'}")


if __name__ == "__main__":
    main()
