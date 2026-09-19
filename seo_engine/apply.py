"""Apply decided actions under controlled autonomy.

AUTO path
    Merge safe field changes into ``data/seo/overrides.json``.
    Never writes ``site/**``. A subsequent ``python3 src/build.py`` is what
    materialises the change into HTML — and that rebuild is an operator /
    refresh-pipeline step, not something this module triggers by default.

PR path
    Write a markdown + JSON proposal under ``data/seo/proposals/`` that a
    human (or a later GitHub Action) can turn into a pull request.

HUMAN path
    Record the flag only. No files that affect the storefront are touched.

Default mode is dry-run: print the plan, write nothing.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional

from .config import (
    MODE_AUTO,
    MODE_HUMAN,
    MODE_PR,
    OVERRIDES_PATH,
    PROPOSALS_DIR,
    ensure_seo_dirs,
    read_json,
    write_json,
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def load_overrides() -> dict:
    data = read_json(OVERRIDES_PATH, default=None)
    if not data:
        return {
            "schema_version": 1,
            "updated": None,
            "generator": "seo_engine.apply",
            "contract": (
                "Page-level SEO overrides consumed by src/build.py. "
                "Keys under pages are URL paths ('/shop/slug/', '/michigan-wolverines-shirts/'). "
                "Supported fields: title, meta_description, og_title, og_description. "
                "Never hand-edit site/; change overrides and rebuild."
            ),
            "pages": {},
            "history": [],
        }
    data.setdefault("pages", {})
    data.setdefault("history", [])
    return data


def _apply_auto(actions: List[dict], overrides: dict, dry_run: bool) -> List[dict]:
    applied = []
    pages = overrides.setdefault("pages", {})
    for action in actions:
        if action["mode"] != MODE_AUTO or action.get("status") != "ready_auto":
            continue
        changes = action.get("changes") or {}
        if not changes:
            continue
        path = action["path"]
        entry = dict(pages.get(path) or {})
        before = {k: entry.get(k) for k in changes}
        entry.update(changes)
        entry["updated_at"] = _now()
        entry["change_id"] = action["id"]
        entry["reason"] = action.get("reason")
        entry["type"] = action.get("type")
        if not dry_run:
            pages[path] = entry
            overrides.setdefault("history", []).append({
                "id": action["id"],
                "path": path,
                "at": _now(),
                "type": action.get("type"),
                "before": before,
                "after": changes,
            })
            # Cap history so the file cannot grow without bound under daily cron.
            overrides["history"] = overrides["history"][-200:]
        applied.append({
            "id": action["id"],
            "path": path,
            "changes": changes,
            "dry_run": dry_run,
        })
    if applied and not dry_run:
        overrides["updated"] = _today()
        overrides["generator"] = "seo_engine.apply"
        write_json(OVERRIDES_PATH, overrides)
    return applied


def _apply_pr(actions: List[dict], dry_run: bool) -> List[dict]:
    written = []
    pr_actions = [a for a in actions if a["mode"] == MODE_PR]
    if not pr_actions:
        return written
    ensure_seo_dirs()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_at": _now(),
        "engine": "seo_engine.apply",
        "kind": "pr_proposal",
        "action_count": len(pr_actions),
        "actions": pr_actions,
        "instructions": (
            "Review each action. For approved items, either (a) encode the change "
            "in data/seo/overrides.json / src/ and open a PR, or (b) dismiss. "
            "Do not merge anything that invents trust signals, player likeness claims, "
            "or thin intent pages (AGENTS.md §3.3, CODEX-TASKS.md standing constraint)."
        ),
    }
    md_lines = [
        f"# SEO Engine PR proposal — {stamp}",
        "",
        f"Generated: `{payload['generated_at']}`",
        f"Actions: **{len(pr_actions)}**",
        "",
        "These changes are **not** applied. Review, then encode approved items",
        "via `data/seo/overrides.json` + rebuild, or via `src/` for content work.",
        "",
        "| ID | Type | Path | Severity | Score | Detail |",
        "|---|---|---|---|---|---|",
    ]
    for a in pr_actions:
        md_lines.append(
            f"| `{a['id']}` | {a['type']} | `{a['path']}` | {a.get('severity')} | "
            f"{a.get('score')} | {a.get('detail', '').replace('|', '/')} |"
        )
    md_lines += ["", "## Change payloads", ""]
    for a in pr_actions:
        md_lines.append(f"### `{a['id']}` — {a['type']} on `{a['path']}`")
        md_lines.append("")
        md_lines.append(f"- Reason: {a.get('reason')}")
        md_lines.append(f"- Evidence: `{json.dumps(a.get('evidence') or {}, ensure_ascii=False)[:300]}`")
        md_lines.append(f"- Proposed changes: `{json.dumps(a.get('changes') or {}, ensure_ascii=False)}`")
        md_lines.append("")

    if not dry_run:
        json_path = PROPOSALS_DIR / f"pr-{stamp}.json"
        md_path = PROPOSALS_DIR / f"pr-{stamp}.md"
        write_json(json_path, payload)
        md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        written.append({"json": str(json_path), "md": str(md_path), "count": len(pr_actions)})
    else:
        written.append({"json": None, "md": None, "count": len(pr_actions), "dry_run": True})
    return written


def _apply_human(actions: List[dict], dry_run: bool) -> List[dict]:
    """HUMAN actions are logged into the latest proposal bundle only."""
    human = [a for a in actions if a["mode"] == MODE_HUMAN]
    if not human:
        return []
    ensure_seo_dirs()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_at": _now(),
        "kind": "human_flags",
        "action_count": len(human),
        "actions": human,
        "note": "No automatic change. Operator decision required.",
    }
    if not dry_run:
        path = PROPOSALS_DIR / f"human-{stamp}.json"
        write_json(path, payload)
        return [{"json": str(path), "count": len(human)}]
    return [{"json": None, "count": len(human), "dry_run": True}]


def apply_decisions(
    decisions: dict,
    *,
    dry_run: bool = True,
    modes: Optional[List[str]] = None,
) -> dict:
    """Apply a decisions report.

    ``modes`` defaults to ``[AUTO]`` only — PR/HUMAN require an explicit opt-in
    so a cron job cannot accidentally dump proposal spam or, worse, claim to
    have "handled" a human decision.
    """
    modes = modes or [MODE_AUTO]
    actions = decisions.get("actions") or []
    overrides = load_overrides()

    result = {
        "generated_at": _now(),
        "dry_run": dry_run,
        "modes": modes,
        "auto": [],
        "pr": [],
        "human": [],
    }
    if MODE_AUTO in modes:
        result["auto"] = _apply_auto(actions, overrides, dry_run=dry_run)
    if MODE_PR in modes:
        result["pr"] = _apply_pr(actions, dry_run=dry_run)
    if MODE_HUMAN in modes:
        result["human"] = _apply_human(actions, dry_run=dry_run)

    result["auto_count"] = len(result["auto"])
    result["pr_count"] = sum(x.get("count", 0) for x in result["pr"])
    result["human_count"] = sum(x.get("count", 0) for x in result["human"])
    result["overrides_path"] = str(OVERRIDES_PATH)
    return result
