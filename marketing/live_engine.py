#!/usr/bin/env python3
"""
Live Engine — replaces the repetitive platform_package with vault-driven unique copy.

Reads:
- data/products.json, facts.json, order.json, trends.json, people.json
- src/collections_data.py SEASON

Writes:
- marketing/plan.json (new unique version)
- marketing/live_drops.json (public benefit page data)
- marketing/pinterest_feed.csv (Pinterest bulk upload ready)

This is the "real work that makes benefit" — unique, trend-catching, reliable.
"""
from __future__ import annotations
import json, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETING_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(MARKETING_DIR))

from collections_data import SEASON, COLLECTIONS
from copy_vault import generate_caption, generate_hashtags, VOICES, get_headline_for_product, clean_headline

# Reuse scoring logic from original plan.py
sys.path.insert(0, str(ROOT))
from marketing.plan import (
    build_people_lookup, score_design, collection_trend_stage,
    compute_opportunity, BEST_TIMES, PLATFORMS, BASE_SCORE, SEASON_BONUS,
    HEADLINE_NAME_BONUS, HEADLINE_BONUS_CAP, THEME_BONUS, THROWBACK_PENALTY,
    collection_info, make_calendar, make_news_gaps
)

def read_json(p: Path):
    with p.open(encoding="utf-8") as f:
        return json.load(f)

def build_designs_unique(products, facts, order, trends, people):
    people_lookup = build_people_lookup(people)
    scored = []
    term_coverage = {}
    entity_coverage = {}
    for row in order:
        slug = row.get("slug")
        ckey = row.get("col")
        product = products[slug]
        fact = facts[slug]
        trend = trends.get("collections", {}).get(ckey, {})
        score = score_design(row, product, fact, trend, SEASON[ckey])
        for term in score["season_search_terms"]:
            term_coverage[term] = term_coverage.get(term, 0) + 1
        for ent in score["headline_name_matches"]:
            if int(ent["repeated_mentions"] or 0) >= 2:
                entity_coverage[ent["name"]] = entity_coverage.get(ent["name"], 0) + 1
        scored.append((row, ckey, slug, product, fact, trend, score))

    designs = []
    for row, ckey, slug, product, fact, trend, score in scored:
        info = collection_info(ckey)
        opportunity = compute_opportunity(
            ckey, fact, product, score, trend, SEASON[ckey],
            people_lookup, term_coverage, entity_coverage,
        )
        # NEW: unique platform packages from vault
        platforms = {}
        for platform in PLATFORMS:
            caption = generate_caption(ckey, platform, product, fact, trends, slug)
            hashtags = generate_hashtags(ckey, fact, platform, slug)
            # Keep original prompt generation for compatibility
            from marketing.plan import scene_prompt
            try:
                prompt = scene_prompt(ckey, str(fact.get("theme","classic")).lower(), platform, bool(score["throwback"]))
            except Exception:
                prompt = f"{info['scene']}; game-day editorial"
            platforms[platform] = {
                "caption": caption,
                "hashtags": hashtags,
                "prompt": prompt,
            }

        item = {
            "slug": slug,
            "source_index": row.get("i"),
            "collection": ckey,
            "collection_label": info["label"],
            "name": fact.get("name") or product.get("title") or slug,
            "catalogue_title": product.get("title",""),
            "design_text": fact.get("art",""),
            "theme": fact.get("theme","classic"),
            "product_type": fact.get("type","Apparel"),
            "price_usd": product.get("price_usd"),
            "product_url": product.get("url",""),
            "image_url": product.get("front",""),
            "keywords": fact.get("kw",[]),
            "score": score["score"],
            "score_breakdown": score,
            "opportunity": opportunity,
            "platforms": platforms,
            "live_headline": get_headline_for_product(ckey, slug, fact, trends),
        }
        designs.append(item)

    designs.sort(key=lambda x: (-int(x["score"]), -int(x["score_breakdown"]["score_raw"]), int(x["source_index"] or 999999)))
    for rank, item in enumerate(designs, start=1):
        item["rank"] = rank
        reasons = []
        br = item["score_breakdown"]
        if br["season_search_terms"]:
            reasons.append("2026 search match")
        if br["headline_name_bonus"]:
            reasons.append("repeated headline name")
        if br["playoff_or_player_bonus"]:
            reasons.append("playoff/player theme")
        if br["throwback"]:
            reasons.append("throwback penalty")
        item["reasons"] = reasons or ["evergreen catalogue fit"]
    return designs

def build_live_drops(designs, trends):
    """Top trending products with live headlines — for public /drops/ page"""
    # Filter top 24 by score, but prioritize those with headline matches
    trending = sorted(designs, key=lambda d: (0 if d["score_breakdown"]["headline_name_bonus"] else 1, -d["score"]))[:24]
    drops = []
    for d in trending:
        ckey = d["collection"]
        col = COLLECTIONS.get(ckey, {})
        drops.append({
            "slug": d["slug"],
            "name": d["name"],
            "collection": ckey,
            "collection_label": d["collection_label"],
            "collection_short": col.get("short", ckey),
            "theme": d["theme"],
            "price": d["price_usd"],
            "image": d["image_url"],
            "url": d["product_url"],
            "headline": d["live_headline"],
            "caption": d["platforms"]["instagram"]["caption"],
            "score": d["score"],
            "reasons": d["reasons"],
            "art": d["design_text"],
        })
    return {
        "generated": dt.date.today().isoformat(),
        "count": len(drops),
        "drops": drops,
        "trends_date": trends.get("generated"),
    }

def build_pinterest_feed(designs):
    """CSV ready for Pinterest bulk upload — unique titles/descriptions"""
    rows = []
    for d in designs[:60]:  # top 60 for Pinterest
        title = d["platforms"]["pinterest"]["caption"][:100]  # Pinterest title limit 100
        # Build description with SEO
        desc = d["platforms"]["pinterest"]["caption"]
        # Ensure unique: add collection voice
        voice = VOICES.get(d["collection"], {})
        city = voice.get("city","")
        # Pinterest requires: title, description, link, image, board
        rows.append({
            "title": title,
            "description": desc + f" | {d['collection_label']} fan style | S-3XL, printed on demand, ships worldwide.",
            "link": d["product_url"],
            "image_url": d["image_url"],
            "board": f"{d['collection_label']} Fan Style",
            "tags": ", ".join(d["platforms"]["pinterest"]["hashtags"]),
        })
    return rows

def build_plan(products, facts, order, trends, people):
    if len(order) != 134:
        raise ValueError(f"Expected 134 designs, got {len(order)}")
    designs = build_designs_unique(products, facts, order, trends, people)
    generated_on = dt.date.today()
    gaps = make_news_gaps(trends)

    strategy = []
    for ckey, value in SEASON.items():
        trend = trends.get("collections", {}).get(ckey, {})
        stage, stage_note = collection_trend_stage(value, trend)
        members = [i for i in designs if i["collection"] == ckey]
        top = max(members, key=lambda x: x["opportunity"]["score"]) if members else None
        strategy.append({
            "collection": ckey,
            "collection_label": collection_info(ckey)["label"],
            "trend_stage": stage,
            "trend_stage_note": stage_note,
            "headline": value.get("headline",""),
            "status": value.get("status",""),
            "hot_terms": value.get("hot",[]),
            "top_opportunity": {
                "slug": top["slug"],
                "name": top["name"],
                "opportunity_score": top["opportunity"]["score"],
                "decision": top["opportunity"]["decision"],
                "trend_stage": top["opportunity"]["trend_stage"],
                "opportunity_type": top["opportunity"]["opportunity_type"],
            } if top else None,
        })

    compliance_summary = {
        "licensing_status": "UNVERIFIED",
        "restriction": "Promotional social content must not use team names, player names, player likenesses, or protected marks until licensing is verified.",
        "social_blocked_designs": sum(1 for i in designs if i["opportunity"]["compliance"]["social_blocked"]),
        "social_safe_designs": sum(1 for i in designs if i["opportunity"]["compliance"]["social_safe"]),
        "high_risk_designs": sum(1 for i in designs if i["opportunity"]["compliance"]["level"]=="high"),
    }

    image_prompts = [
        {
            "rank": item["rank"],
            "slug": item["slug"],
            "name": item["name"],
            "collection": item["collection_label"],
            "score": item["score"],
            "prompts": {p: item["platforms"][p]["prompt"] for p in PLATFORMS},
        } for item in designs
    ]

    return {
        "meta": {
            "generated_on": generated_on.isoformat(),
            "generator": "marketing/live_engine.py + copy_vault.py (unique per team)",
            "standalone": True,
            "design_count": len(designs),
            "platforms": list(PLATFORMS),
            "source_files": ["data/products.json","data/facts.json","data/order.json","data/trends.json","data/people.json","src/collections_data.py:SEASON","marketing/copy_vault.py"],
            "output_file": "marketing/plan.json",
            "trend_window_days": trends.get("window_days"),
            "trends_generated_on": trends.get("generated"),
            "vault_version": "v1 - team-specific voices, 20+ openers per team, headline-aware",
        },
        "score_rules": {
            "base": BASE_SCORE,
            "season_search_term": SEASON_BONUS,
            "repeated_headline_name": HEADLINE_NAME_BONUS,
            "headline_name_bonus_cap": HEADLINE_BONUS_CAP,
            "playoff_or_player_theme": THEME_BONUS,
            "throwback": THROWBACK_PENALTY,
            "final_score_range": [0,100],
        },
        "season_context": {
            ckey: {
                "status": v.get("status",""),
                "headline": v.get("headline",""),
                "kickoff": v.get("kickoff",""),
                "opener": v.get("opener",""),
                "search_terms": v.get("hot",[]),
                "legacy_note": v.get("legacy_note",""),
            } for ckey, v in SEASON.items()
        },
        "summary": {
            "design_count": len(designs),
            "top_score": designs[0]["score"],
            "throwback_count": sum(1 for i in designs if i["score_breakdown"]["throwback"]),
            "season_match_count": sum(1 for i in designs if i["score_breakdown"]["season_search_terms"]),
            "headline_gap_count": sum(len(g["gaps"]) for g in gaps),
            "headline_count": sum(int(g["headline_count"] or 0) for g in gaps),
            "unique_copy": True,
            "vault": "team-specific voices, headline injection",
        },
        "queue": designs,
        "calendar": make_calendar(designs, generated_on),
        "best_times": {
            "timezone": "America/New_York",
            "method": "Practical starting windows for a two-week test",
            "platforms": [{"key": p, **BEST_TIMES[p]} for p in PLATFORMS],
        },
        "news_gaps": gaps,
        "image_prompts": image_prompts,
        "who_is_who": {
            "rules": people.get("rules",""),
            "people": people.get("people",[]),
        },
        "opportunity_model": {
            "weights": {
                "audience": 20, "search": 15, "velocity": 15, "gap": 15,
                "competition": 10, "business": 10, "authority": 5, "longevity": 5, "distribution": 5
            },
            "decision_bands": {
                "PUBLISH": "opportunity score >=70 and confidence >=35",
                "IMPROVE": "opportunity score >=55",
                "MONITOR": "below threshold or low confidence",
                "REJECT": "throwback / departed player-coach",
            },
        },
        "strategy": strategy,
        "compliance": compliance_summary,
    }

def main():
    products = read_json(ROOT / "data" / "products.json")
    facts = read_json(ROOT / "data" / "facts.json")
    order = read_json(ROOT / "data" / "order.json")
    trends = read_json(ROOT / "data" / "trends.json")
    people = read_json(ROOT / "data" / "people.json")

    plan = build_plan(products, facts, order, trends, people)

    # Write plan.json (overwrites old repetitive version)
    out = MARKETING_DIR / "plan.json"
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(f"wrote {out} · {plan['summary']['design_count']} designs · top {plan['summary']['top_score']} · unique copy v1")

    # Write live_drops.json
    drops = build_live_drops(plan["queue"], trends)
    drops_path = MARKETING_DIR / "live_drops.json"
    drops_path.write_text(json.dumps(drops, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(f"wrote {drops_path} · {drops['count']} drops")

    # Write pinterest feed CSV
    pinterest_rows = build_pinterest_feed(plan["queue"])
    csv_path = MARKETING_DIR / "pinterest_feed.csv"
    import csv
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["title","description","link","image_url","board","tags"])
        w.writeheader()
        w.writerows(pinterest_rows)
    print(f"wrote {csv_path} · {len(pinterest_rows)} pins")

    # Also write a JSON version for site build
    data_drops = ROOT / "data" / "live_drops.json"
    data_drops.write_text(json.dumps(drops, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(f"wrote {data_drops} for site build")

if __name__ == "__main__":
    main()
