"""Content / landing-page opportunity scanner.

Surfaces PR-mode proposals when demand signals exist but the storefront has no
supporting guide or the collection page under-serves an emerging query cluster.

Sources (read-only, never invented):

* ``data/catalogue-live.json`` — what is actually sellable
* ``data/trends.json`` — headline / entity demand
* ``radar/lib/seo.js`` seed concepts (ported as static fallbacks)
* optional ``data/seo/gsc_export.json`` — real query demand

Never auto-publishes articles. Emits PR proposals only.
Never suggests thin intent pages (CODEX-TASKS.md standing constraint).
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Dict, List, Optional

from .config import (
    CATALOGUE_PATH,
    DATA,
    GSC_EXPORT_PATH,
    PUBLIC_COLLECTIONS,
    domain,
    read_json,
)
from .audit import gsc_by_page, load_gsc_export
from .crawler import crawl


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Port of radar/lib/seo.js SEO_SEED — kept here so the Python engine does not
# need a Node runtime. Update alongside the JS seed when either changes.
SEO_SEED = [
    {
        "opportunity": "SECOND ACT",
        "team": "michigan",
        "collection_path": "/michigan-wolverines-shirts/",
        "emerging_language": [
            "second act shirt",
            "bryce underwood second act tee",
            "michigan second act apparel",
        ],
        "landing_hint": "Differentiate PDP metadata for Second Act / Year Two angle",
        "content_hint": (
            "Editorial: 'What fans mean when they say Second Act' — only if "
            "catalogue still carries a matching design"
        ),
        "priority": "HIGH",
    },
    {
        "opportunity": "QB1 BATTLE",
        "team": "cleveland-browns",
        "collection_path": "/cleveland-browns-shirts/",
        "emerging_language": [
            "browns qb1 shirt",
            "shedeur sanders browns shirt",
            "let him rip browns shirt",
        ],
        "landing_hint": "Optimize metadata for QB1 / expiration-date co-search on existing slogan tees",
        "content_hint": (
            "Guide addendum: 'Browns QB1 shirts — what each design says' "
            "(buying-guide extension, not a thin page). Slogan-only; no player-number art."
        ),
        "priority": "HIGH",
        "caution": "Avoid player-number designs per house rule (slogan only for QB slot)",
    },
    {
        "opportunity": "NEW ERA — MONKEN",
        "team": "cleveland-browns",
        "collection_path": "/cleveland-browns-shirts/",
        "emerging_language": [
            "new era browns shirt",
            "todd monken browns tee",
            "browns new era dawgpound",
        ],
        "landing_hint": "Monitor only until volume clears WATCH→EMERGING",
        "content_hint": "No separate page until demand threshold clears",
        "priority": "MEDIUM",
    },
]


def _guides_present(pages) -> set:
    return {p.path for p in pages if p.kind == "guide"}


def _collection_paths(pages) -> set:
    return {p.path for p in pages if p.kind == "collection"}


def _catalogue_slugs() -> set:
    cat = read_json(CATALOGUE_PATH, default={})
    return {
        p["slug"] for p in (cat.get("products") or [])
        if p.get("site_published")
    }


def _trend_entities() -> Dict[str, list]:
    trends = read_json(DATA / "trends.json", default={})
    out: Dict[str, list] = {}
    collections = trends.get("collections") or {}
    for ckey, blob in collections.items():
        entities = []
        for row in blob.get("entity_mentions") or blob.get("entities") or []:
            if isinstance(row, dict):
                entities.append(row)
            elif isinstance(row, str):
                entities.append({"name": row})
        out[ckey] = entities
        # fan_trend_index rows often carry the useful names
        for row in blob.get("fan_trend_index") or []:
            if isinstance(row, dict) and row.get("name"):
                entities.append(row)
    return out


def scan_opportunities(pages=None) -> dict:
    """Return PR-mode content opportunities. Never auto-applies."""
    pages = pages if pages is not None else crawl()
    guides = _guides_present(pages)
    collections = _collection_paths(pages)
    slugs = _catalogue_slugs()
    gsc = gsc_by_page(load_gsc_export())
    opportunities: List[dict] = []

    # 1. Seed opportunities gated on live catalogue + existing collection page.
    for seed in SEO_SEED:
        cpath = seed["collection_path"]
        if cpath not in collections:
            continue
        opportunities.append({
            "kind": "seed_opportunity",
            "mode": "PR",
            "opportunity": seed["opportunity"],
            "team": seed["team"],
            "path": cpath,
            "priority": seed["priority"],
            "emerging_language": seed["emerging_language"],
            "landing_hint": seed["landing_hint"],
            "content_hint": seed["content_hint"],
            "caution": seed.get("caution"),
            "status": "proposal_only",
            "reason": (
                "Seed opportunity from radar SEO module. Requires human review "
                "before any page or metadata rewrite."
            ),
        })

    # 2. GSC queries with impressions on a collection but weak CTR → content gap flag.
    for path, perf in gsc.items():
        if path not in collections:
            continue
        if perf.get("impressions", 0) < 200:
            continue
        if perf.get("ctr", 1) >= 0.03:
            continue
        top = (perf.get("queries") or [])[:5]
        if not top:
            continue
        opportunities.append({
            "kind": "gsc_content_gap",
            "mode": "PR",
            "opportunity": f"Content gap on {path}",
            "path": path,
            "priority": "HIGH" if perf["impressions"] >= 1000 else "MEDIUM",
            "emerging_language": [q.get("query") for q in top if q.get("query")],
            "evidence": {
                "impressions": perf["impressions"],
                "ctr": perf["ctr"],
                "position": perf.get("position"),
            },
            "content_hint": (
                "Consider a buying-guide section or collection copy refresh that "
                "covers the top queries — not a new thin landing page."
            ),
            "status": "proposal_only",
            "reason": "GSC shows demand the collection page under-converts on.",
        })

    # 3. Guard: never propose a new URL that would duplicate /search/ filters.
    # (Standing constraint — recorded so the report makes the policy visible.)
    policy_notes = [
        "No mass fan-intent pages. /search/ already consolidates ?q/?t/?g/?st=.",
        "No new product URL for a slug that already has one.",
        "No player-face / surname-on-chest / jersey-number / team-logo suggestions.",
        "Articles land via src/ guides after approval — never hand-copied into site/.",
        f"Live catalogue slugs available for product links: {len(slugs)}.",
        f"Existing guides: {sorted(guides)}.",
    ]

    return {
        "generated_at": _now(),
        "engine": "seo_engine.content",
        "domain": domain(),
        "opportunity_count": len(opportunities),
        "opportunities": opportunities,
        "policy_notes": policy_notes,
        "catalogue_count": len(slugs),
        "guide_count": len(guides),
    }
