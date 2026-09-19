"""Verify that applied overrides actually land in the built ``site/``.

RankEngine-style closed loop: after a rebuild, re-read the live HTML and
confirm each override field matches. Records pass/fail into learning memory
so the engine can stop retrying no-ops and double down on what works.
"""
from __future__ import annotations

import datetime as dt
import re
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional

from .config import (
    MEMORY_PATH,
    OVERRIDES_PATH,
    SITE,
    read_json,
    write_json,
)
from .crawler import parse_page


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path_to_file(url_path: str, site: Path = SITE) -> Optional[Path]:
    rel = url_path.lstrip("/")
    if not rel or rel.endswith("/"):
        candidate = site / rel / "index.html"
    elif rel.endswith(".html"):
        candidate = site / rel
    else:
        candidate = site / rel / "index.html"
    return candidate if candidate.is_file() else None


def verify_overrides(
    overrides: Optional[dict] = None,
    site: Path = SITE,
) -> dict:
    overrides = overrides if overrides is not None else read_json(OVERRIDES_PATH, default={})
    pages = overrides.get("pages") or {}
    results = []
    passed = failed = missing = 0

    for path, entry in sorted(pages.items()):
        fpath = _path_to_file(path, site)
        if not fpath:
            results.append({
                "path": path,
                "status": "missing_file",
                "detail": "No built HTML at this path — rebuild required or path is wrong.",
            })
            missing += 1
            continue
        page = parse_page(path, fpath)
        checks = {}
        ok = True
        if "title" in entry and entry["title"]:
            match = (page.title or "") == entry["title"]
            checks["title"] = {"expected": entry["title"], "actual": page.title, "ok": match}
            ok = ok and match
        if "meta_description" in entry and entry["meta_description"]:
            match = (page.meta_description or "") == entry["meta_description"]
            checks["meta_description"] = {
                "expected": entry["meta_description"],
                "actual": page.meta_description,
                "ok": match,
            }
            ok = ok and match
        if "og_title" in entry and entry["og_title"]:
            match = (page.og_title or "") == entry["og_title"]
            checks["og_title"] = {"expected": entry["og_title"], "actual": page.og_title, "ok": match}
            ok = ok and match
        if "og_description" in entry and entry["og_description"]:
            match = (page.og_description or "") == entry["og_description"]
            checks["og_description"] = {
                "expected": entry["og_description"],
                "actual": page.og_description,
                "ok": match,
            }
            ok = ok and match

        status = "pass" if ok else "fail"
        if status == "pass":
            passed += 1
        else:
            failed += 1
        results.append({
            "path": path,
            "status": status,
            "change_id": entry.get("change_id"),
            "checks": checks,
        })

    report = {
        "generated_at": _now(),
        "engine": "seo_engine.verify",
        "override_count": len(pages),
        "passed": passed,
        "failed": failed,
        "missing_file": missing,
        "results": results,
    }
    return report


def record_verification(report: dict, memory_path=None) -> dict:
    """Append a verification summary into learning memory (no invented metrics)."""
    path = Path(memory_path) if memory_path else MEMORY_PATH
    memory = read_json(path, default=None) or {
        "schema_version": 1,
        "purpose": (
            "Measured outcomes of SEO Engine changes. Only verification results "
            "and operator-supplied GSC before/after rows. Never invent traffic numbers."
        ),
        "verifications": [],
        "outcomes": [],
    }
    memory.setdefault("verifications", []).append({
        "at": report.get("generated_at"),
        "passed": report.get("passed"),
        "failed": report.get("failed"),
        "missing_file": report.get("missing_file"),
        "override_count": report.get("override_count"),
    })
    memory["verifications"] = memory["verifications"][-100:]
    memory["last_updated"] = _now()
    write_json(path, memory)
    return memory


def record_outcome(
    change_id: str,
    path: str,
    *,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    note: str = "",
    source: str = "operator",
) -> dict:
    """Record a measured before/after for a change. Used once GSC data exists.

    ``before`` / ``after`` should be real GSC aggregates
    ``{clicks, impressions, ctr, position}`` — never estimated.
    """
    memory = read_json(MEMORY_PATH, default=None) or {
        "schema_version": 1,
        "verifications": [],
        "outcomes": [],
    }
    row = {
        "date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "change_id": change_id,
        "path": path,
        "before": before,
        "after": after,
        "note": note,
        "source": source,
    }
    if not source:
        raise ValueError("outcome rows require a source")
    memory.setdefault("outcomes", []).append(row)
    memory["last_updated"] = _now()
    write_json(MEMORY_PATH, memory)
    return row
