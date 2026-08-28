#!/usr/bin/env python3
"""Build the standalone promotion plan consumed by dashboard.html.

The generator is deliberately small and dependency-free. It reads the scraped
catalogue and the season/news snapshots, then writes exactly one generated
artifact: marketing/plan.json.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# Keep an import of the season snapshot from creating a cache file in src/.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
MARKETING_DIR = Path(__file__).resolve().parent
OUTPUT = MARKETING_DIR / "plan.json"
SRC_DIR = ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
from collections_data import SEASON  # noqa: E402  (path is set immediately above)


PLATFORMS = ("instagram", "tiktok", "facebook", "x", "pinterest")
BASE_SCORE = 50
SEASON_BONUS = 22
HEADLINE_NAME_BONUS = 12
HEADLINE_BONUS_CAP = 30
THEME_BONUS = 6
THROWBACK_PENALTY = -25

# These labels and palettes are presentation data for the planning tool. They
# are not imported from the storefront generator, so this dashboard remains a
# separate concern from the website build.
COLLECTION_INFO = {
    "cleveland-browns": {
        "label": "Cleveland Browns",
        "short": "Cleveland",
        "audience": "Dawg Pound fans",
        "tags": ["dawgpound", "clevelandfootball", "brownsfans"],
        "scene": (
            "Rain-fresh autumn tailgate at dawn beside an empty stadium concourse; "
            "ember orange and deep cocoa illumination, wet pavement reflections, "
            "drifting mist"
        ),
    },
    "green-bay-packers": {
        "label": "Green Bay Packers",
        "short": "Green Bay",
        "audience": "Cheesehead Nation fans",
        "tags": ["cheeseheadnation", "greenbayfootball", "packersfans"],
        "scene": (
            "Frosty lakeside morning near an empty stadium walkway; evergreen shadows, "
            "warm green and golden sunrise, breath-cold air, wood-and-metal textures"
        ),
    },
    "dallas-cowboys": {
        "label": "Dallas Cowboys",
        "short": "Dallas",
        "audience": "Dallas football fans",
        "tags": ["dallasfootball", "texasfootball", "dallasfans"],
        "scene": (
            "Late-summer Texas dusk on a wide concrete plaza near an empty stadium; "
            "burnt-sunset glow, midnight blue shadows, silver highlights, dry warm air"
        ),
    },
    "michigan": {
        "label": "Michigan Wolverines",
        "short": "Michigan",
        "audience": "Go Blue fans",
        "tags": ["goblue", "michiganfootball", "collegegameday"],
        "scene": (
            "Crisp early-autumn morning on a tree-lined college-town avenue leading "
            "toward an empty stadium; maize sunrise and deep navy shade, light fog, "
            "leaves skittering across pavement"
        ),
    },
}

# The aliases mirror the entity vocabulary used by the trend snapshot, with a
# few design-text spellings (10VE and J.J.) added for reliable catalogue joins.
ENTITY_ALIASES = {
    "shedeur sanders": ("shedeur sanders", "shedeur", "sanders"),
    "deshaun watson": ("deshaun watson", "deshaun", "watson"),
    "joe flacco": ("joe flacco", "joe", "flacco"),
    "myles garrett": ("myles garrett", "myles", "garrett"),
    "kevin stefanski": ("kevin stefanski", "kevin", "stefanski"),
    "denzel ward": ("denzel ward", "denzel"),
    "todd monken": ("todd monken", "todd", "monken"),
    "jordan love": ("jordan love", "10ve", "love"),
    "micah parsons": ("micah parsons", "micah", "parsons"),
    "robert tonyan": ("robert tonyan", "robert", "tonyan"),
    "josh jacobs": ("josh jacobs", "josh", "jacobs"),
    "matt lafleur": ("matt lafleur", "lafleur"),
    "bryce underwood": ("bryce underwood", "bryce", "underwood"),
    "jj mccarthy": ("jj mccarthy", "j j mccarthy", "mccarthy"),
    "kyle whittingham": ("kyle whittingham", "kyle", "whittingham"),
    "jordan marshall": ("jordan marshall", "jordan marshall"),
    "dak prescott": ("dak prescott", "dak", "prescott"),
    "ceedee lamb": ("ceedee lamb", "ceedee", "lamb"),
}

GENERIC_MERCH_WORDS = {
    "a",
    "an",
    "and",
    "for",
    "the",
    "shirt",
    "shirts",
    "tee",
    "tees",
    "tshirt",
    "tshirts",
    "hoodie",
    "hoodies",
    "sweatshirt",
    "sweatshirts",
    "crewneck",
    "crewnecks",
    "apparel",
    "gear",
    "top",
    "tops",
    "2026",
}

# The prompt builder only emits environmental and mood language. Keep this
# guard close to the generator so a future edit cannot accidentally turn a
# scene prompt into a request for protected or recognizable imagery.
PROMPT_FORBIDDEN = re.compile(
    r"\b(?:logo|logos|team\s+mark|team\s+marks|player|players|likeness|likenesses)\b",
    re.IGNORECASE,
)

PROMPT_MOODS = {
    "playoff": "charged anticipation, high contrast, and a determined atmosphere",
    "player": "focused momentum, confident calm, and an energized atmosphere",
    "funny": "playful warmth, bright contrast, and a lighthearted atmosphere",
    "family": "welcoming warmth, soft contrast, and a joyful atmosphere",
    "city": "grounded pride, open space, and a confident atmosphere",
    "retro": "nostalgic warmth, gentle film grain, and an easygoing atmosphere",
    "halloween": "moody twilight, dramatic shadows, and a mischievous atmosphere",
    "classic": "communal energy, clean contrast, and an optimistic atmosphere",
    "throwback": "nostalgic warmth, muted contrast, and a reflective atmosphere",
}

PROMPT_FORMATS = {
    "instagram": "vertical 4:5 framing",
    "tiktok": "vertical 9:16 framing with a strong center of calm negative space",
    "facebook": "horizontal 16:9 framing",
    "x": "horizontal 16:9 framing with a wide horizon",
    "pinterest": "vertical 2:3 framing with an airy editorial composition",
}

BEST_TIMES = {
    "instagram": {
        "label": "Instagram",
        "windows": ["Tue–Thu · 11:30–13:00", "Sun · 18:00–20:00"],
        "default_time": "12:00",
        "why": "A lunch scroll and a Sunday evening game-day reset catch both planning and browsing intent.",
    },
    "tiktok": {
        "label": "TikTok",
        "windows": ["Tue–Thu · 18:30–21:00", "Sat · 10:00–12:00"],
        "default_time": "19:30",
        "why": "Evening leisure time gives short-form hooks room to travel before the next day’s conversations.",
    },
    "facebook": {
        "label": "Facebook",
        "windows": ["Wed–Fri · 12:00–14:00", "Sun · 17:30–20:00"],
        "default_time": "18:30",
        "why": "Midday sharing and pregame family-group browsing are useful for gift and group-buy intent.",
    },
    "x": {
        "label": "X",
        "windows": ["Mon–Fri · 08:00–10:00", "Game days · 30 min before kickoff"],
        "default_time": "09:00",
        "why": "Morning news and pregame conversation are the best moments for a timely one-line hook.",
    },
    "pinterest": {
        "label": "Pinterest",
        "windows": ["Fri–Sun · 19:00–22:00", "Sat · 09:00–11:00"],
        "default_time": "20:30",
        "why": "Weekend evening saves and Saturday planning support evergreen outfit and gift discovery.",
    },
}

PLATFORM_TAG_LIMITS = {
    "instagram": 12,
    "tiktok": 8,
    "facebook": 6,
    "x": 4,
    "pinterest": 12,
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value: Any) -> str:
    """Lowercase searchable text and make punctuation behave like spaces."""
    text = html.unescape(str(value or "")).lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def words(value: Any) -> set[str]:
    return set(normalize(value).split())


def contains_alias(search_text: str, alias: str) -> bool:
    normalized_text = f" {normalize(search_text)} "
    normalized_alias = normalize(alias)
    if not normalized_alias:
        return False
    return f" {normalized_alias} " in normalized_text


def collection_info(ckey: str) -> dict[str, Any]:
    if ckey in COLLECTION_INFO:
        return COLLECTION_INFO[ckey]
    label = ckey.replace("-", " ").title()
    return {
        "label": label,
        "short": label.split()[0],
        "audience": f"{label} fans",
        "tags": [normalize(ckey).replace(" ", "")],
        "scene": "A calm game-day morning near an empty stadium; seasonal light, open air, and inviting textures",
    }


def searchable_text(product: dict[str, Any], fact: dict[str, Any]) -> str:
    fields: list[str] = [
        product.get("title", ""),
        product.get("desc", ""),
        fact.get("name", ""),
        fact.get("art", ""),
        " ".join(str(x) for x in fact.get("kw", [])),
    ]
    return " ".join(fields)


def season_term_matches(search_text: str, terms: Iterable[str]) -> list[str]:
    """Match exact hot queries plus safe multi-word variants.

    A product can be a match when an apparel suffix or the year is absent from
    its catalogue copy, but it still needs at least two meaningful query words.
    This keeps a generic one-word query such as "packers 2026 shirt" from
    making every catalogue item a season match.
    """
    normalized_text = normalize(search_text)
    text_words = set(normalized_text.split())
    matched: list[str] = []
    for term in terms:
        normalized_term = normalize(term)
        if not normalized_term:
            continue
        if f" {normalized_term} " in f" {normalized_text} ":
            matched.append(term)
            continue
        signal_words = [
            token
            for token in normalized_term.split()
            if token not in GENERIC_MERCH_WORDS and len(token) > 1
        ]
        if len(signal_words) >= 2 and all(token in text_words for token in signal_words):
            matched.append(term)
    return matched


def matched_entities(ckey: str, search_text: str, trend: dict[str, Any]) -> list[dict[str, Any]]:
    """Join a design to named entities and retain the recent mention counts."""
    counts = trend.get("entity_mentions", {}) if isinstance(trend, dict) else {}
    matches: list[dict[str, Any]] = []
    for entity, raw_count in counts.items():
        try:
            mentions = max(0, int(raw_count))
        except (TypeError, ValueError):
            mentions = 0
        aliases = ENTITY_ALIASES.get(entity.lower(), (entity,))
        if any(contains_alias(search_text, alias) for alias in aliases):
            # One or zero mentions is not a repeated name. A hot name earns
            # +12 for each recent mention, with the overall +30 cap below.
            repeated_mentions = mentions if mentions >= 2 else 0
            matches.append(
                {
                    "name": entity,
                    "mentions": mentions,
                    "repeated_mentions": repeated_mentions,
                    "throwback_signal": mentions == 0,
                }
            )
    return matches


def make_hashtags(ckey: str, fact: dict[str, Any], platform: str) -> list[str]:
    info = collection_info(ckey)
    candidates: list[str] = [
        *info["tags"],
        "footballstyle",
        "gameday",
        "fanmade",
        fact.get("theme", "football"),
        *[str(x) for x in fact.get("kw", [])[:4]],
        fact.get("name", ""),
    ]
    if platform == "pinterest":
        candidates += ["footballgift", "gamedayoutfit"]
    elif platform == "tiktok":
        candidates += ["footballtok", "fitcheck"]
    elif platform == "instagram":
        candidates += ["footballfans", "tailgatestyle"]
    elif platform == "x":
        candidates += ["football", "nflfans"]

    output: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        tag = "#" + re.sub(r"[^a-z0-9]", "", normalize(candidate))
        if tag == "#" or tag in seen or len(tag) <= 2:
            continue
        seen.add(tag)
        output.append(tag)
        if len(output) >= PLATFORM_TAG_LIMITS[platform]:
            break
    return output


def scene_prompt(ckey: str, theme: str, platform: str, throwback: bool) -> str:
    info = collection_info(ckey)
    mood_key = "throwback" if throwback else (theme if theme in PROMPT_MOODS else "classic")
    prompt = (
        f"{info['scene']}; {PROMPT_MOODS[mood_key]}; "
        f"{PROMPT_FORMATS[platform]}, cinematic editorial atmosphere, "
        "natural light, tactile detail, and generous negative space"
    )
    if PROMPT_FORBIDDEN.search(prompt):
        raise ValueError(f"Unsafe protected-imagery language in generated prompt for {ckey}")
    return prompt


def trim_x(text: str, limit: int = 280) -> str:
    if len(text) <= limit:
        return text
    suffix = "…"
    return text[: limit - len(suffix)].rstrip(" ,;:") + suffix


def platform_package(
    ckey: str,
    product: dict[str, Any],
    fact: dict[str, Any],
    score_info: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    info = collection_info(ckey)
    name = str(fact.get("name") or product.get("title") or product.get("slug"))
    url = str(product.get("url", ""))
    context = "2026 season energy" if score_info["season_search_terms"] else "game-day energy"
    audience = info["audience"]
    hashtags: dict[str, list[str]] = {
        platform: make_hashtags(ckey, fact, platform) for platform in PLATFORMS
    }
    captions = {
        "instagram": (
            f"{name} brings {context} to your next {info['short']} game-day fit. "
            f"Made for {audience.lower()}, printed on demand, and ready for the next big weekend. "
            "Save this idea and tap through to see the design."
        ),
        "tiktok": (
            f"POV: {info['short']} game day just found its statement piece. "
            f"{name} is fan-made, printed on demand, and built for {context}. "
            "Show us the fit."
        ),
        "facebook": (
            f"Looking for a fresh {info['short']} football look? {name} keeps the mood focused "
            f"without trying too hard. It is an independent fan-made design, printed on demand "
            f"for {audience.lower()}. Explore it here: {url}"
        ),
        "x": trim_x(
            f"{name} - {info['short']} {context}. Fan-made and printed on demand. {url}"
        ),
        "pinterest": (
            f"{name}: an independent {info['short']} football style idea for game days, "
            f"tailgates, and gift lists. Save this {context} look and explore the design at {url}"
        ),
    }
    return {
        platform: {
            "caption": captions[platform],
            "hashtags": hashtags[platform],
            "prompt": scene_prompt(
                ckey,
                str(fact.get("theme", "classic")).lower(),
                platform,
                bool(score_info["throwback"]),
            ),
        }
        for platform in PLATFORMS
    }


def score_design(
    row: dict[str, Any],
    product: dict[str, Any],
    fact: dict[str, Any],
    trend: dict[str, Any],
    season: dict[str, Any],
) -> dict[str, Any]:
    text = searchable_text(product, fact)
    matched_terms = season_term_matches(text, season.get("hot", []))
    entities = matched_entities(row["col"], text, trend)
    headline_repeat_count = sum(item["repeated_mentions"] for item in entities)
    headline_bonus = min(HEADLINE_BONUS_CAP, HEADLINE_NAME_BONUS * headline_repeat_count)
    theme = str(fact.get("theme", "classic")).lower()
    theme_bonus = THEME_BONUS if theme in {"playoff", "player"} else 0
    explicit_throwback = bool(fact.get("throwback", False)) or theme == "throwback"
    throwback_entities = [item["name"] for item in entities if item["throwback_signal"]]
    throwback = explicit_throwback or bool(throwback_entities)
    throwback_penalty = THROWBACK_PENALTY if throwback else 0
    season_bonus = SEASON_BONUS if matched_terms else 0
    raw_score = BASE_SCORE + season_bonus + headline_bonus + theme_bonus + throwback_penalty
    final_score = max(0, min(100, raw_score))

    return {
        "score": final_score,
        "score_raw": raw_score,
        "base": BASE_SCORE,
        "season_search_terms": matched_terms,
        "season_search_term_bonus": season_bonus,
        "headline_name_matches": entities,
        "headline_name_repeat_count": headline_repeat_count,
        "headline_name_bonus": headline_bonus,
        "playoff_or_player_theme": theme in {"playoff", "player"},
        "playoff_or_player_bonus": theme_bonus,
        "throwback": throwback,
        "throwback_entities": throwback_entities,
        "throwback_penalty": throwback_penalty,
    }


def build_designs(
    products: dict[str, Any],
    facts: dict[str, Any],
    order: list[dict[str, Any]],
    trends: dict[str, Any],
) -> list[dict[str, Any]]:
    designs: list[dict[str, Any]] = []
    for row in order:
        slug = row.get("slug")
        ckey = row.get("col")
        if not slug or not ckey:
            raise ValueError(f"Malformed order row: {row!r}")
        if slug not in products:
            raise ValueError(f"Order row {slug!r} is missing from data/products.json")
        if slug not in facts:
            raise ValueError(f"Order row {slug!r} is missing from data/facts.json")
        if ckey not in SEASON:
            raise ValueError(f"Order row {slug!r} has no season snapshot for {ckey!r}")

        product = products[slug]
        fact = facts[slug]
        trend = trends.get("collections", {}).get(ckey, {})
        score = score_design(row, product, fact, trend, SEASON[ckey])
        info = collection_info(ckey)
        item: dict[str, Any] = {
            "slug": slug,
            "source_index": row.get("i"),
            "collection": ckey,
            "collection_label": info["label"],
            "name": fact.get("name") or product.get("title") or slug,
            "catalogue_title": product.get("title", ""),
            "design_text": fact.get("art", ""),
            "theme": fact.get("theme", "classic"),
            "product_type": fact.get("type", "Apparel"),
            "price_usd": product.get("price_usd"),
            "product_url": product.get("url", ""),
            "image_url": product.get("front", ""),
            "keywords": fact.get("kw", []),
            "score": score["score"],
            "score_breakdown": score,
        }
        item["platforms"] = platform_package(ckey, product, fact, score)
        designs.append(item)

    designs.sort(
        key=lambda item: (
            -int(item["score"]),
            -int(item["score_breakdown"]["score_raw"]),
            int(item["source_index"] if item["source_index"] is not None else 999999),
        )
    )
    for rank, item in enumerate(designs, start=1):
        item["rank"] = rank
        reasons: list[str] = []
        breakdown = item["score_breakdown"]
        if breakdown["season_search_terms"]:
            reasons.append("2026 search match")
        if breakdown["headline_name_bonus"]:
            reasons.append("repeated headline name")
        if breakdown["playoff_or_player_bonus"]:
            reasons.append("playoff/player theme")
        if breakdown["throwback"]:
            reasons.append("throwback penalty")
        item["reasons"] = reasons or ["evergreen catalogue fit"]
    return designs


def make_calendar(designs: list[dict[str, Any]], start_date: dt.date) -> list[dict[str, Any]]:
    scheduled = designs[:14]
    calendar: list[dict[str, Any]] = []
    for offset in range(14):
        day = start_date + dt.timedelta(days=offset)
        focus = scheduled[offset]
        posts = []
        for platform in PLATFORMS:
            package = focus["platforms"][platform]
            posts.append(
                {
                    "platform": platform,
                    "platform_label": BEST_TIMES[platform]["label"],
                    "time": BEST_TIMES[platform]["default_time"],
                    "rank": focus["rank"],
                    "slug": focus["slug"],
                    "name": focus["name"],
                    "score": focus["score"],
                    "caption": package["caption"],
                    "hashtags": package["hashtags"],
                }
            )
        calendar.append(
            {
                "date": day.isoformat(),
                "weekday": day.strftime("%A"),
                "focus_rank": focus["rank"],
                "focus_slug": focus["slug"],
                "focus_name": focus["name"],
                "focus_collection": focus["collection_label"],
                "focus_score": focus["score"],
                "posts": posts,
            }
        )
    return calendar


def make_news_gaps(trends: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for ckey in SEASON:
        info = collection_info(ckey)
        trend = trends.get("collections", {}).get(ckey, {})
        mentions = trend.get("entity_mentions", {})
        gaps = []
        for name in trend.get("gaps", []):
            count = int(mentions.get(name, 0) or 0)
            gap_copy = (
                f"Opportunity: explore an independent fan-made {info['short']} concept "
                f"around {name.title()} while the conversation is active ({count} recent headline mentions). "
                "Validate the current context before publishing."
            )
            gaps.append(
                {
                    "name": name,
                    "mentions": count,
                    "angle": f"Current conversation around {name.title()}",
                    "copy_text": gap_copy,
                }
            )
        output.append(
            {
                "collection": ckey,
                "collection_label": info["label"],
                "query": trend.get("query", ""),
                "headline_count": trend.get("headline_count", 0),
                "gaps": gaps,
                "top_headlines": trend.get("headlines", [])[:5],
                "covered_names": [
                    {"name": name, "mentions": int(count or 0)}
                    for name, count in sorted(
                        mentions.items(), key=lambda pair: (-int(pair[1] or 0), pair[0])
                    )
                ],
            }
        )
    return output


def build_plan(
    products: dict[str, Any],
    facts: dict[str, Any],
    order: list[dict[str, Any]],
    trends: dict[str, Any],
) -> dict[str, Any]:
    if len(order) != 134:
        raise ValueError(f"Expected 134 designs in data/order.json; found {len(order)}")
    if len({row.get("slug") for row in order}) != 134:
        raise ValueError("data/order.json must contain 134 unique design slugs")

    designs = build_designs(products, facts, order, trends)
    if len(designs) != 134:
        raise ValueError(f"Expected 134 generated designs; found {len(designs)}")

    generated_on = dt.date.today()
    gaps = make_news_gaps(trends)
    image_prompts = [
        {
            "rank": item["rank"],
            "slug": item["slug"],
            "name": item["name"],
            "collection": item["collection_label"],
            "score": item["score"],
            "prompts": {
                platform: item["platforms"][platform]["prompt"] for platform in PLATFORMS
            },
        }
        for item in designs
    ]

    return {
        "meta": {
            "generated_on": generated_on.isoformat(),
            "generator": "marketing/plan.py",
            "standalone": True,
            "design_count": len(designs),
            "platforms": list(PLATFORMS),
            "source_files": [
                "data/products.json",
                "data/facts.json",
                "data/order.json",
                "data/trends.json",
                "src/collections_data.py:SEASON",
            ],
            "output_file": "marketing/plan.json",
            "trend_window_days": trends.get("window_days"),
            "trends_generated_on": trends.get("generated"),
        },
        "score_rules": {
            "base": BASE_SCORE,
            "season_search_term": SEASON_BONUS,
            "repeated_headline_name": HEADLINE_NAME_BONUS,
            "headline_name_bonus_cap": HEADLINE_BONUS_CAP,
            "playoff_or_player_theme": THEME_BONUS,
            "throwback": THROWBACK_PENALTY,
            "final_score_range": [0, 100],
            "headline_note": "A name must occur at least twice in the recent headline snapshot to count as repeated; each mention contributes +12 until the +30 cap.",
        },
        "season_context": {
            ckey: {
                "status": value.get("status", ""),
                "headline": value.get("headline", ""),
                "kickoff": value.get("kickoff", ""),
                "opener": value.get("opener", ""),
                "search_terms": value.get("hot", []),
                "legacy_note": value.get("legacy_note", ""),
            }
            for ckey, value in SEASON.items()
        },
        "summary": {
            "design_count": len(designs),
            "top_score": designs[0]["score"],
            "throwback_count": sum(
                1 for item in designs if item["score_breakdown"]["throwback"]
            ),
            "season_match_count": sum(
                1 for item in designs if item["score_breakdown"]["season_search_terms"]
            ),
            "headline_gap_count": sum(len(group["gaps"]) for group in gaps),
            "headline_count": sum(int(group["headline_count"] or 0) for group in gaps),
        },
        "queue": designs,
        "calendar": make_calendar(designs, generated_on),
        "best_times": {
            "timezone": "America/New_York",
            "method": "Practical starting windows for a two-week test; compare saves, clicks, and replies before changing the cadence.",
            "platforms": [
                {"key": platform, **BEST_TIMES[platform]} for platform in PLATFORMS
            ],
        },
        "news_gaps": gaps,
        "image_prompts": image_prompts,
    }


def main() -> None:
    products = read_json(ROOT / "data" / "products.json")
    facts = read_json(ROOT / "data" / "facts.json")
    order = read_json(ROOT / "data" / "order.json")
    trends = read_json(ROOT / "data" / "trends.json")
    plan = build_plan(products, facts, order, trends)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {OUTPUT} · {plan['summary']['design_count']} designs · "
        f"top score {plan['summary']['top_score']} · "
        f"{plan['summary']['headline_gap_count']} news gaps"
    )


if __name__ == "__main__":
    main()
