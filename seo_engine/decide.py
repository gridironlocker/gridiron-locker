"""Decide automation mode per finding and emit ranked actions.

    AUTO   — low-risk metadata / alt / canonical. Applied via overrides.json.
    PR     — content / new pages / major rewrites. Written as a proposal file.
    HUMAN  — URL / delete / merge / redirect. Flagged only; never auto-touched.

This is the controlled-autonomy gate. The engine does the work; the operator
keeps final control on anything that can hurt the live storefront.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Dict, List, Optional

from .config import (
    HUMAN_TYPES,
    MODE_AUTO,
    MODE_HUMAN,
    MODE_PR,
    PR_TYPES,
    SAFE_TYPES,
    read_json,
    OVERRIDES_PATH,
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _action_id(ftype: str, path: str, payload: dict) -> str:
    raw = f"{ftype}|{path}|{sorted(payload.items())}"
    return "seo-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]


def _mode_for(ftype: str) -> str:
    if ftype in SAFE_TYPES:
        return MODE_AUTO
    if ftype in PR_TYPES:
        return MODE_PR
    if ftype in HUMAN_TYPES:
        return MODE_HUMAN
    # Unknown types default to PR — never silent auto on novel classes.
    return MODE_PR


# Severity weight for ranking.
_SEV = {"high": 30, "medium": 15, "low": 5}

# Type weight: prefer fixes that move CTR / indexability.
_TYPE_WEIGHT = {
    "missing_title": 40,
    "missing_description": 35,
    "missing_canonical": 35,
    "duplicate_title": 30,
    "duplicate_description": 25,
    "weak_ctr_title": 28,
    "title_too_long": 18,
    "description_too_long": 14,
    "missing_h1": 22,
    "missing_image_alt": 12,
    "missing_og_title": 8,
    "missing_og_description": 8,
    "title_too_short": 6,
    "description_too_short": 6,
    "canonical_mismatch": 10,
    "multiple_h1": 10,
}


def _score(finding: dict) -> float:
    base = _SEV.get(finding.get("severity"), 5)
    base += _TYPE_WEIGHT.get(finding.get("type"), 5)
    # Boost when GSC evidence is attached.
    ev = finding.get("evidence") or {}
    if ev.get("impressions"):
        base += min(20.0, float(ev["impressions"]) / 100.0)
    if ev.get("ctr") is not None and ev["ctr"] < 0.02:
        base += 8
    return base


def _already_applied(path: str, field: str, overrides: dict) -> bool:
    pages = (overrides or {}).get("pages") or {}
    entry = pages.get(path) or {}
    return field in entry and entry[field]


def _build_action(finding: dict, overrides: dict) -> Optional[dict]:
    ftype = finding["type"]
    mode = _mode_for(ftype)
    suggested = dict(finding.get("suggested") or {})
    path = finding["path"]

    # Skip findings with nothing actionable yet (e.g. short title w/o rewrite).
    if mode == MODE_AUTO and not suggested:
        # Still surface for the report, but mark as observe-only.
        return {
            "id": _action_id(ftype, path, {"observe": True}),
            "mode": MODE_AUTO,
            "type": ftype,
            "path": path,
            "severity": finding.get("severity"),
            "score": _score(finding),
            "status": "observe",
            "detail": finding.get("detail"),
            "evidence": finding.get("evidence") or {},
            "changes": {},
            "reason": "No safe auto-fix payload; flagged for observation only.",
        }

    changes = {}
    if "title" in suggested:
        changes["title"] = suggested["title"]
    if "meta_description" in suggested:
        changes["meta_description"] = suggested["meta_description"]
    if "canonical" in suggested:
        changes["canonical"] = suggested["canonical"]
    if "og_title" in suggested:
        changes["og_title"] = suggested["og_title"]
    if "og_description" in suggested:
        changes["og_description"] = suggested["og_description"]

    # Skip AUTO actions whose target field is already overridden to the same value.
    if mode == MODE_AUTO and changes:
        skip = True
        for field, value in changes.items():
            current = ((overrides.get("pages") or {}).get(path) or {}).get(field)
            if current != value:
                skip = False
                break
        if skip and all(
            _already_applied(path, f, overrides) for f in changes
        ):
            return None

    status = {
        MODE_AUTO: "ready_auto",
        MODE_PR: "needs_pr",
        MODE_HUMAN: "needs_human",
    }[mode]

    return {
        "id": _action_id(ftype, path, changes or {"t": ftype}),
        "mode": mode,
        "type": ftype,
        "path": path,
        "severity": finding.get("severity"),
        "score": round(_score(finding), 2),
        "status": status,
        "detail": finding.get("detail"),
        "evidence": finding.get("evidence") or {},
        "changes": changes,
        "reason": _reason(ftype, finding),
    }


def _reason(ftype: str, finding: dict) -> str:
    reasons = {
        "missing_title": "Indexable page without a title tag cannot rank or earn CTR.",
        "missing_description": "Meta description drives SERP snippet CTR when Google uses it.",
        "missing_canonical": "Canonical protects against duplicate-URL signal split.",
        "title_too_long": "Titles past ~60 chars are truncated in SERPs; front-load the value.",
        "description_too_long": "Descriptions past ~158 chars are truncated in SERPs.",
        "duplicate_title": "Duplicate titles split relevance and confuse snippet selection.",
        "duplicate_description": "Duplicate descriptions weaken snippet uniqueness.",
        "weak_ctr_title": "Search Console shows impressions with weak CTR — title is the lever.",
        "missing_image_alt": "Alt text aids accessibility and image search discovery.",
        "missing_og_title": "og:title controls link previews on social / iMessage / Slack.",
        "missing_og_description": "og:description controls link-preview body copy.",
        "missing_h1": "A single H1 anchors on-page topical relevance.",
        "canonical_mismatch": "User canonical disagrees with the expected absolute URL.",
    }
    return reasons.get(ftype, finding.get("detail") or ftype)


def decide(audit_report: dict, overrides: Optional[dict] = None) -> dict:
    """Turn an audit report into a ranked action list."""
    overrides = overrides if overrides is not None else read_json(OVERRIDES_PATH, default={})
    findings = audit_report.get("findings") or []
    actions: List[dict] = []
    for finding in findings:
        # canonical_mismatch is report-only in v1 — build.py owns canonicals.
        if finding["type"] == "canonical_mismatch":
            action = _build_action(finding, overrides)
            if action:
                action["mode"] = MODE_HUMAN
                action["status"] = "needs_human"
                actions.append(action)
            continue
        if finding["type"] in ("missing_h1", "multiple_h1"):
            # H1s come from product/collection source data; changing them is PR.
            action = _build_action(finding, overrides)
            if action:
                action["mode"] = MODE_PR
                action["status"] = "needs_pr"
                action["changes"] = {}
                actions.append(action)
            continue
        action = _build_action(finding, overrides)
        if action:
            actions.append(action)

    actions.sort(key=lambda a: (-a["score"], a["path"], a["type"]))

    summary = {
        MODE_AUTO: sum(1 for a in actions if a["mode"] == MODE_AUTO and a["status"] == "ready_auto"),
        MODE_PR: sum(1 for a in actions if a["mode"] == MODE_PR),
        MODE_HUMAN: sum(1 for a in actions if a["mode"] == MODE_HUMAN),
        "observe": sum(1 for a in actions if a["status"] == "observe"),
    }

    return {
        "generated_at": _now(),
        "engine": "seo_engine.decide",
        "source_audit_at": audit_report.get("generated_at"),
        "action_count": len(actions),
        "summary": summary,
        "actions": actions,
        "policy": {
            "auto": sorted(SAFE_TYPES),
            "pr": sorted(PR_TYPES),
            "human": sorted(HUMAN_TYPES),
            "note": (
                "AUTO writes data/seo/overrides.json only. "
                "src/build.py must be re-run to emit site/. "
                "PR/HUMAN never touch production without operator approval."
            ),
        },
    }
