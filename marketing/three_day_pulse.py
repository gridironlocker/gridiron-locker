#!/usr/bin/env python3
"""Turn the latest public trend signals into a rolling three-day buying plan.

The output is intentionally short-lived: today, tomorrow, and the following
 day. Run it after every trend/social collection. It matches the existing
catalogue; it does not invent new products or publish content.
"""
from __future__ import annotations

import datetime as dt
import hashlib
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


def trend_for(team: str, plan: dict[str, Any], signals: dict[str, Any], variant: int = 0) -> dict[str, Any]:
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
    if rows:
        top = rows[variant % len(rows)].get("text", "")
    else:
        top = strategy.get("headline", "") or season.get("headline", "")
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


ANGLES = (
    {
        "id": "identity",
        "label": "Fan identity statement",
        "themes": ("player", "classic", "city"),
        "emotions": ("confident", "hyped"),
        "shape": "Say who you root for before you say a word.",
    },
    {
        "id": "news_react",
        "label": "News reaction",
        "themes": ("player", "playoff"),
        "emotions": ("hyped", "worried", "angry"),
        "shape": "React to the storyline that is moving right now.",
    },
    {
        "id": "throwback",
        "label": "Throwback / heritage",
        "themes": ("retro", "classic"),
        "emotions": ("nostalgic", "disappointed"),
        "shape": "Anchor the product in the era fans keep bringing up.",
    },
    {
        "id": "humor",
        "label": "Inside-joke humor",
        "themes": ("funny", "halloween"),
        "emotions": ("mocking", "angry", "disappointed"),
        "shape": "Lean on the joke only this fanbase understands.",
    },
    {
        "id": "gift",
        "label": "Gift / relationship",
        "themes": ("family", "halloween"),
        "emotions": ("hopeful", "nostalgic"),
        "shape": "Frame the product as a gift for a specific person.",
    },
    {
        "id": "styling",
        "label": "Outfit styling",
        "themes": ("city", "classic", "retro"),
        "emotions": ("confident", "hopeful"),
        "shape": "Show how the piece is worn, not just what it says.",
    },
)

HOOK_TEMPLATES = {
    "identity": (
        "You can spot a real {team} fan before kickoff. {line}",
        "{team} fandom is not a costume - it is a wardrobe decision. {line}",
        "No slogan, no filler: {line}",
    ),
    "news_react": (
        "Everyone in the {team} timeline is arguing about the same thing today. {line}",
        "The storyline moved this morning; the merch shelf did not. {line}",
        "One headline, one {team} reaction piece: {line}",
    ),
    "throwback": (
        "Fans keep bringing up the old {team} era, so here it is on cotton. {line}",
        "Some {team} looks aged well. {line}",
        "Throwback energy, current fit: {line}",
    ),
    "humor": (
        "If you know, you know. {line}",
        "Made for the {team} group chat that never behaves. {line}",
        "This one is either a joke or a confession. {line}",
    ),
    "gift": (
        "There is one {team} fan in every family who is impossible to shop for. {line}",
        "Buy it for them and they will wear it every Sunday. {line}",
        "Gift-ready {team} pick: {line}",
    ),
    "styling": (
        "Game day fit, weekday wearable. {line}",
        "Pair it with denim and forget it is fan gear. {line}",
        "How {team} fans are actually dressing this season: {line}",
    ),
}

CTAS = (
    "Tap through to the product page.",
    "Full details on the listing.",
    "Sizes and colours are on the product page.",
    "Link in bio for the listing.",
    "See it on the shop page.",
)

TIKTOK_OPENERS = (
    "POV:",
    "Nobody asked, but:",
    "Fit check:",
    "Storytime, short version:",
    "Three seconds of {team} truth:",
)

IG_OPENERS = (
    "Saved for Sunday.",
    "Closet upgrade.",
    "Locked in.",
    "One piece, whole mood.",
    "Read the shirt.",
)


def seed_for(*parts: Any) -> int:
    return int(hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:8], 16)


def pick(options: tuple, seed: int, salt: int = 0) -> Any:
    return options[(seed + salt) % len(options)]


def angle_for(product: dict[str, Any], trend: dict[str, Any], seed: int, avoid: set[str] | None = None) -> dict[str, Any]:
    theme = str(product.get("theme", "classic")).lower()
    emotion = trend["emotion"]
    avoid = avoid or set()
    scored = []
    for index, angle in enumerate(ANGLES):
        score = 0
        if theme in angle["themes"]:
            score += 3
        if emotion in angle["emotions"]:
            score += 2
        if angle["id"] in avoid:
            score -= 6
        scored.append((score, -((seed + index) % len(ANGLES)), angle))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return scored[0][2]


def design_line(product: dict[str, Any]) -> str:
    text = clean(product.get("design_text"))
    if not text:
        return clean(product.get("name"))
    parts = [part.strip() for part in re.split(r"[-|,]", text) if part.strip()]
    phrase = parts[0] if parts else text
    return phrase if phrase.isupper() else phrase.upper()


GARMENTS = (
    ("hoodie", "hoodie"),
    ("sweatshirt", "sweatshirt"),
    ("crewneck", "crewneck"),
    ("long sleeve", "long-sleeve tee"),
    ("beanie", "beanie"),
    ("mug", "mug"),
    ("phone case", "phone case"),
    ("women", "women's tee"),
    ("shirt", "tee"),
    ("tee", "tee"),
)


def garment(product: dict[str, Any]) -> str:
    kind = clean(product.get("product_type")) or "Apparel"
    if kind != "Apparel":
        return kind.lower()
    name = clean(product.get("name")).lower()
    for needle, word in GARMENTS:
        if needle in name:
            return word
    return "tee"


def product_line(product: dict[str, Any]) -> str:
    price = numeric_price(product.get("price_usd"))
    word = garment(product)
    return f"{word} at ${price:.2f}" if price else word


def copy_pack(product: dict[str, Any], trend: dict[str, Any], date: str, rank: int, avoid_angles: set[str] | None = None) -> dict[str, Any]:
    name = clean(product.get("name"))
    slug = clean(product.get("slug"))
    team = clean(product.get("collection_label"))
    product_url = clean(product.get("product_url"))
    emotion = trend["emotion"]
    story = trend["story"] or f"{team} fan conversation"
    seed = seed_for(slug, date, rank, trend["story"][:40], angle_salt := len(story) % 7)
    angle = angle_for(product, trend, seed, avoid_angles)
    keywords = [clean(keyword) for keyword in (product.get("keywords") or []) if clean(keyword)]
    primary_keyword = keywords[0] if keywords else f"{team} shirt".lower()
    line = f"\u201c{design_line(product)}\u201d on a {product_line(product)}."
    hook_template = pick(HOOK_TEMPLATES[angle["id"]], seed, rank + angle_salt)
    hook = hook_template.format(team=team, line=line)
    cta = pick(CTAS, seed, rank + 1)
    ad = " ".join([
        hook,
        f"Angle: {angle['label'].lower()}. Signal driving it: {story}",
        f"Product: {name} ({primary_keyword}).",
        "Verify licensing and the live listing before promotion.",
    ])
    instagram = " ".join([
        pick(IG_OPENERS, seed, rank + 2),
        hook,
        f"Why now: {story}",
        cta,
        " ".join(f"#{re.sub(r'[^a-z0-9]', '', keyword.lower())}" for keyword in ([team] + keywords[:2])),
    ])
    facebook = " ".join([
        hook,
        f"Context for {team} fans: {story}",
        f"It is a {product_line(product)} from the {team} collection.",
        cta,
        product_url,
    ]).strip()
    x_body = f"{hook} {story[:90].rstrip()} {product_url}".strip()
    x_post = (x_body[:277].rstrip() + "\u2026") if len(x_body) > 280 else x_body
    tiktok = " ".join([
        pick(TIKTOK_OPENERS, seed, rank + 3).format(team=team),
        hook,
        f"Script beat: {angle['shape']}",
        "Show the print, then the fit, then the price.",
    ])
    pinterest_caption = " ".join([
        f"{name} - {primary_keyword} idea for {team} fans.",
        angle["shape"],
        f"{product_line(product).capitalize()}.",
    ])
    return {
        "angle": angle["id"],
        "hook_template": hook_template,
        "angle_label": angle["label"],
        "hook": hook,
        "ad_copy": ad,
        "captions": {
            "instagram": instagram,
            "facebook": facebook,
            "x": x_post,
            "tiktok": tiktok,
            "pinterest": pinterest_caption,
        },
        "pinterest": {
            "title": f"{name}: {primary_keyword.title()}",
            "description": f"{angle['label']} pin for {team} fans feeling {emotion}. {line} Use only after the product and licensing review.",
            "keywords": (keywords[:5] or [primary_keyword]) + [f"{team} game day outfit", "football fan apparel"],
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
    used_slugs: set[str] = set()
    used_hooks: set[str] = set()
    for offset in range(3):
        date = generated + dt.timedelta(days=offset)
        selected = []
        used_angles: set[str] = set()
        for index, team in enumerate(TEAM_ALIASES):
            trend = trend_for(team, plan, signals, variant=offset + index)
            candidates = [product for product in products if product.get("collection") == team]
            candidates.sort(key=lambda product: product_signal(product, trend), reverse=True)
            fresh = [product for product in candidates if product.get("slug") not in used_slugs]
            pool = fresh or candidates
            if not pool:
                continue
            product = pool[0]
            used_slugs.add(product.get("slug", ""))
            risk = compliance(product)
            copy = copy_pack(product, trend, date.isoformat(), len(selected), used_angles)
            attempts = 0
            while copy["hook_template"] in used_hooks and attempts < 6:
                attempts += 1
                copy = copy_pack(product, trend, date.isoformat(), len(selected) + attempts, used_angles)
            used_angles.add(copy["angle"])
            used_hooks.add(copy["hook_template"])
            selected.append({
                "product": product.get("name"),
                "slug": product.get("slug"),
                "product_url": product.get("product_url"),
                "team": product.get("collection_label"),
                "trend": trend,
                "fan_emotion": trend["emotion"],
                "creative_angle": copy["angle_label"],
                "product_signal_score": round(product_signal(product, trend), 1),
                "copy": copy,
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
