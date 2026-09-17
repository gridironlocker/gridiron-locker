"""Transparent, explainable opportunity scoring (0-100).

Weighting (fixed by the engine spec):

    Team relevance              25
    Football activity           20
    Audience size               15
    Engagement                  15
    Commercial relevance        10
    Public contact availability 10
    Freshness                    5

Every component returns (points, reason). Unknown data scores 0 and says so —
the engine never fabricates engagement or audience numbers. A separate
confidence score reflects how much real evidence backs the record, and a
commercial_score re-weights the business angle.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from . import config, PRIORITY_BANDS

_WEIGHTS = {
    "team_relevance": 25,
    "football_activity": 20,
    "audience": 15,
    "engagement": 15,
    "commercial": 10,
    "contact": 10,
    "freshness": 5,
}


def _days_since(value: str | None) -> int | None:
    if not value:
        return None
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
    ):
        try:
            parsed = dt.datetime.strptime(text, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return max(0, (dt.datetime.now(dt.timezone.utc) - parsed).days)
        except ValueError:
            continue
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        try:
            parsed = dt.datetime(*(int(g) for g in match.groups()), tzinfo=dt.timezone.utc)
            return max(0, (dt.datetime.now(dt.timezone.utc) - parsed).days)
        except ValueError:
            return None
    return None


def _text_blob(prospect: dict) -> str:
    parts = [
        prospect.get("display_name") or "",
        prospect.get("username") or "",
        prospect.get("bio") or "",
        prospect.get("website") or "",
        prospect.get("profile_url") or "",
    ]
    return " ".join(p for p in parts if p).lower()


def _teams_matching(blob: str, keywords: dict[str, dict] | None = None) -> list[dict]:
    keywords = keywords or config.load_all_keywords()
    matches = []
    for team, data in keywords.items():
        strong = [t for t in data.get("strong_terms", []) if t in blob]
        weak = [t for t in data.get("terms", []) if t in blob]
        if strong or weak:
            matches.append({"team": team, "strong": strong, "weak": weak})
    return matches


def score(prospect: dict, keywords: dict[str, dict] | None = None) -> dict:
    keywords = keywords or config.load_all_keywords()
    blob = _text_blob(prospect)
    breakdown: dict[str, dict] = {}

    # -- team relevance (25) -----------------------------------------------
    team_matches = _teams_matching(blob, keywords)
    name_blob = (prospect.get("display_name") or "").lower()
    if team_matches:
        best = max(team_matches, key=lambda m: (len(m["strong"]), len(m["weak"])))
        if best["strong"] and any(t in name_blob for t in best["strong"]):
            points, why = 25, f"strong {best['team']} identity in the name"
        elif best["strong"]:
            points, why = 22, f"strong {best['team']} signals ({', '.join(best['strong'][:2])})"
        else:
            points, why = 15, f"general {best['team']} terms in bio/profile"
        teams = [m["team"] for m in team_matches]
    else:
        points, why = 0, "no target-team keywords found"
        teams = [prospect["team"]] if prospect.get("team") else []
    breakdown["team_relevance"] = {"points": points, "max": 25, "why": why}

    # -- football activity (20) ----------------------------------------------
    age = _days_since(prospect.get("last_activity_at"))
    volume = prospect.get("post_count") or 0
    if age is None and not volume:
        points, why = 0, "no activity evidence available (not fabricating)"
    else:
        if age is None:
            recency, why = 0, "recency unknown"
        elif age <= 7:
            recency, why = 16, f"active within {age or 1} day(s)"
        elif age <= 30:
            recency, why = 14, f"active within {age} days"
        elif age <= 90:
            recency, why = 9, f"last activity ~{age} days ago"
        elif age <= 180:
            recency, why = 5, f"last activity ~{age} days ago"
        else:
            recency, why = 1, f"dormant since ~{age} days ago"
        if isinstance(volume, (int, float)) and volume >= 100:
            bulk, bulk_why = 4, f"{int(volume)} episodes/posts published"
        elif isinstance(volume, (int, float)) and volume >= 25:
            bulk, bulk_why = 3, f"{int(volume)} episodes/posts published"
        else:
            bulk, bulk_why = (1, "limited published volume") if volume else (0, "")
        points = recency + bulk
        why = "; ".join(x for x in (why, bulk_why) if x)
    breakdown["football_activity"] = {"points": points, "max": 20, "why": why}

    # -- audience (15) --------------------------------------------------------
    followers = prospect.get("followers") or 0
    if followers is None or followers == 0:
        points, why = 0, "audience size unknown (not fabricating)"
    elif followers >= 100_000:
        points, why = 15, f"{followers:,} followers/subscribers"
    elif followers >= 25_000:
        points, why = 13, f"{followers:,} followers/subscribers"
    elif followers >= 5_000:
        points, why = 10, f"{followers:,} followers/subscribers"
    elif followers >= 1_000:
        points, why = 7, f"{followers:,} followers/subscribers"
    elif followers >= 100:
        points, why = 4, f"{followers:,} followers/subscribers"
    else:
        points, why = 2, f"tiny audience ({followers:,})"
    breakdown["audience"] = {"points": points, "max": 15, "why": why}

    # -- engagement (15) — NEVER fabricated ------------------------------------
    engagement = prospect.get("engagement_estimate")
    if engagement is None:
        points, why = 0, "engagement not measured — never fabricated"
    else:
        try:
            ratio = float(engagement)
        except (TypeError, ValueError):
            ratio = 0.0
        if ratio >= 0.05:
            points, why = 15, f"strong measured engagement (~{ratio:.0%})"
        elif ratio >= 0.02:
            points, why = 11, f"healthy measured engagement (~{ratio:.0%})"
        elif ratio > 0:
            points, why = 6, f"modest measured engagement (~{ratio:.0%})"
        else:
            points, why = 0, "measured engagement near zero"
    breakdown["engagement"] = {"points": points, "max": 15, "why": why}

    # -- commercial relevance (10) ----------------------------------------------
    commercial_signals = []
    if prospect.get("public_email"):
        commercial_signals.append("public business email")
    bio = (prospect.get("bio") or "").lower()
    website = (prospect.get("website") or "").lower()
    if re.search(r"(shop|store|merch|gear|apparel|tees|teespring)", bio + " " + website):
        commercial_signals.append("sells merchandise")
    if re.search(r"(sponsor|advertis|partnership|promo code)", bio):
        commercial_signals.append("monetised content")
    if prospect.get("prospect_type") == "SPORTS_BUSINESS":
        commercial_signals.append("football-fan business")
    if commercial_signals:
        points = min(10, 3 * len(commercial_signals))
        why = " + ".join(commercial_signals)
    else:
        points, why = 0, "no commercial signals found"
    breakdown["commercial"] = {"points": points, "max": 10, "why": why}

    # -- public contact availability (10) -----------------------------------------
    email = prospect.get("public_email")
    verdict = prospect.get("email_verified")
    contact_source = prospect.get("contact_source") or ""
    if email and str(verdict).startswith("VERIFIED"):
        points, why = 10, f"public business email ({contact_source or 'published contact'})"
    elif email:
        points, why = 8, "public email found, not yet verified"
    elif "contact" in (website or "") or re.search(r"contact", bio):
        points, why = 5, "contact page available, no published email"
    elif prospect.get("profile_url"):
        points, why = 2, "social profile only (DM)"
    else:
        points, why = 0, "no public contact route"
    breakdown["contact"] = {"points": points, "max": 10, "why": why}

    # -- freshness (5) --------------------------------------------------------------
    if age is None:
        points, why = 0, "no freshness evidence"
    elif age <= 7:
        points, why = 5, "fresh: active this week"
    elif age <= 30:
        points, why = 4, "fresh: active this month"
    elif age <= 90:
        points, why = 2, "moderately fresh"
    else:
        points, why = 0, "stale"
    breakdown["freshness"] = {"points": points, "max": 5, "why": why}

    total = sum(part["points"] for part in breakdown.values())
    total = max(0, min(100, total))

    # -- commercial score (business angle, 0-100) --------------------------------------
    commercial = (
        breakdown["contact"]["points"] / 10 * 30
        + breakdown["audience"]["points"] / 15 * 25
        + breakdown["team_relevance"]["points"] / 25 * 25
        + breakdown["commercial"]["points"] / 10 * 20
    )
    commercial = round(commercial)

    # -- confidence: how much of the record is real evidence ----------------------------
    evidence_fields = [
        prospect.get("display_name"), prospect.get("profile_url"),
        prospect.get("website"), prospect.get("last_activity_at"),
        prospect.get("followers") not in (None, 0), prospect.get("public_email"),
    ]
    confidence = round(100 * sum(1 for f in evidence_fields if f) / len(evidence_fields))

    priority = next(
        label for threshold, label in PRIORITY_BANDS if total >= threshold
    )

    reasons = [
        part["why"] for part in breakdown.values() if part["points"] > 0
    ]
    score_reason = "; ".join(reasons) if reasons else "insufficient evidence"

    return {
        "relevance_score": total,
        "commercial_score": commercial,
        "confidence_score": confidence,
        "priority": priority,
        "breakdown": breakdown,
        "score_reason": score_reason,
        "teams": teams,
    }


def format_breakdown(result: dict) -> str:
    lines = [f"Score: {result['relevance_score']}"]
    for name, part in result["breakdown"].items():
        lines.append(f"  {name}: {part['points']}/{part['max']} — {part['why']}")
    lines.append(f"  priority: {result['priority']}")
    return "\n".join(lines)
