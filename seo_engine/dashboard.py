#!/usr/bin/env python3
"""Generate the private SEO Engine dashboard at ops/seo (published at /ops/seo/).

Published at /ops/seo/ on the live domain. Same delivery pattern as
ops/scout + ops/board: seo_engine/dashboard.py writes ops/seo/index.html;
src/build.py: sync_ops() regenerates it on every build and copies ops/ → site/ops/
via the same allowlist.

The page is noindex + robots Disallow: /ops/ (see site/robots.txt). Never linked
from public nav; listed only from ops/index.html.

Shows the last audit snapshot, the AUTO / PR / HUMAN action queue,
current overrides, GSC status, verification history, and PR content opportunities.
All numbers are read from data/seo/*.json — never invented.

Usage:
    python3 -m seo_engine.dashboard
    python3 seo_engine/dashboard.py
"""

from __future__ import annotations

import html
import json
import os
import sys
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "ops" / "seo"

# Reuse engine config paths (stdlib only). Must support two entrypoints:
#   python3 -m seo_engine.dashboard          (relative import works)
#   spec_from_file_location("gl_seo_dashboard") via src/build.py  (no package)
# so we try relative first, then absolute via ROOT on sys.path.
try:
    from .config import (  # type: ignore[import-not-found, attr-defined]
        AUDIT_PATH,
        DECISIONS_PATH,
        GSC_EXPORT_PATH,
        MEMORY_PATH,
        OVERRIDES_PATH,
        read_json,
    )
except (ImportError, ValueError):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from seo_engine.config import (  # type: ignore[import-not-found]
        AUDIT_PATH,
        DECISIONS_PATH,
        GSC_EXPORT_PATH,
        MEMORY_PATH,
        OVERRIDES_PATH,
        read_json,
    )


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def esc(v: Any) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def _load_all() -> Dict[str, Any]:
    """Collect all SEO artefacts; missing file → empty/default so dashboard never crashes."""
    audit = read_json(AUDIT_PATH, default={}) or {}
    decisions = read_json(DECISIONS_PATH, default={}) or {}
    overrides = read_json(OVERRIDES_PATH, default={}) or {}
    gsc = read_json(GSC_EXPORT_PATH, default={}) or {}
    memory = read_json(MEMORY_PATH, default={}) or {}
    # opportunities are PR-only and depend on crawl + catalogue — guard heavily.
    try:
        try:
            from .content import scan_opportunities  # type: ignore
        except (ImportError, ValueError):
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from seo_engine.content import scan_opportunities  # type: ignore
        opps = scan_opportunities()
    except Exception as e:
        opps = {
            "opportunity_count": 0,
            "opportunities": [],
            "policy_notes": [f"opportunity scan failed: {e}"],
            "generated_at": _now(),
        }
    # enrich audit with decision summary if decisions missing but audit present
    return {
        "audit": audit,
        "decisions": decisions,
        "overrides": overrides,
        "gsc": gsc,
        "memory": memory,
        "opportunities": opps,
        "generated_at": _now(),
    }


CSS = r"""
:root{color-scheme:dark;--ink:#eef5ff;--muted:#93a6c2;--mut2:#c0cfe4;--canvas:#070e1a;
--canvas2:#0b1526;--panel:#0f1e36;--panel2:#142842;--line:rgba(178,203,238,.13);
--line2:rgba(178,203,238,.22);--blue:#7cc8ff;--blue2:#3d9df5;--green:#72e0ba;--orange:#ffb15a;
--pink:#ec9cff;--red:#ff7d7d;--yellow:#ffe08a;
font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;min-width:320px;color:var(--ink);line-height:1.55;
background:radial-gradient(circle at 8% -8%,rgba(61,157,245,.16),transparent 38rem),
radial-gradient(circle at 96% 4%,rgba(114,224,186,.08),transparent 34rem),var(--canvas)}
a{color:var(--blue);text-decoration:none}a:hover{color:#c2e7ff}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.topbar{position:sticky;top:0;z-index:20;border-bottom:1px solid var(--line);
background:rgba(7,14,26,.90);backdrop-filter:blur(16px)}
.topbar-inner,.wrap{width:min(1200px,calc(100% - 48px));margin:0 auto}
.topbar-inner{min-height:62px;display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:10px 0}
.brand{display:flex;align-items:center;gap:12px;font-weight:850;letter-spacing:-.03em}
.mark{display:grid;place-items:center;width:38px;height:38px;border-radius:11px;
color:#05121f;background:linear-gradient(135deg,var(--blue),var(--green));font-weight:900;font-size:1.05rem}
.brand small{display:block;font-weight:650;color:var(--muted);letter-spacing:.11em;
text-transform:uppercase;font-size:.60rem}
.pill{display:inline-flex;align-items:center;gap:7px;padding:6px 12px;border:1px solid var(--line2);
border-radius:999px;color:var(--mut2);background:rgba(255,255,255,.03);font-size:.78rem;white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green)}
.pill.warn{border-color:rgba(255,125,125,.45);color:var(--red);background:rgba(255,125,125,.08)}
.pill.warn .dot{background:var(--red);box-shadow:0 0 10px var(--red)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{border:1px solid var(--line);border-radius:16px;padding:14px 16px;background:linear-gradient(180deg,var(--panel),var(--canvas2))}
.kpi b{display:block;font-size:1.55rem;line-height:1.1;letter-spacing:-.03em}
.kpi span{color:var(--muted);font-size:.70rem;letter-spacing:.09em;text-transform:uppercase}
.kpi em{font-style:normal;color:var(--mut2);font-size:.75rem}
section{padding:22px 0 6px}h1{margin:0 0 8px;font-size:clamp(1.5rem,3vw,2.1rem);letter-spacing:-.03em;line-height:1.15}
h2{margin:0 0 6px;font-size:1.18rem;letter-spacing:-.02em}h3{margin:16px 0 8px;font-size:.98rem}
.lead{color:var(--muted);max-width:82ch;margin:0 0 16px}
.card{border:1px solid var(--line);border-radius:18px;background:var(--panel);padding:18px 20px;box-shadow:0 12px 36px rgba(0,0,0,.18)}
.card + .card{margin-top:16px}
.grid2{display:grid;grid-template-columns:1.15fr .85fr;gap:16px}
@media(max-width:940px){.grid2{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;font-size:.84rem}
th{color:var(--muted);font-weight:650;text-align:left;padding:8px 10px;border-bottom:1px solid var(--line2);
font-size:.69rem;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:hover td{background:rgba(124,200,255,.04)}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.67rem;font-weight:800;
letter-spacing:.06em;text-transform:uppercase;border:1px solid transparent;white-space:nowrap}
.s-high{color:#3b0f0f;background:var(--red)}.s-medium{color:#2a1c05;background:var(--orange)}
.s-low{color:#0a1a2e;background:var(--blue)}.m-auto{color:#052b1c;background:var(--green)}
.m-pr{color:#0d1d2f;background:var(--blue)}.m-human{color:#2a0e2a;background:var(--pink)}
.st-auto{color:#052b1c;background:var(--green)}.st-needs{color:#fff;background:rgba(255,255,255,.14);border-color:var(--line2)}
.st-observe{color:var(--muted);background:rgba(255,255,255,.06)}
.kbd{font-family:ui-monospace,monospace;background:rgba(255,255,255,.06);padding:1px 6px;border-radius:6px;font-size:.78em}
.muted{color:var(--muted)} .small{font-size:.80rem} .mono{font-family:ui-monospace,monospace}
.changes{font-size:.78rem;color:var(--mut2);line-height:1.35;word-break:break-word}
.changes b{color:var(--ink)}
.bar{height:6px;border-radius:99px;background:rgba(255,255,255,.08);overflow:hidden;min-width:92px}
.bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--blue2),var(--blue))}
.foot{padding:28px 0 46px;color:var(--muted);font-size:.80rem;border-top:1px solid var(--line);margin-top:32px}
.foot .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:14px}
ul{margin:8px 0;padding-left:18px}li{margin:4px 0}
details{margin-top:12px;border:1px solid var(--line);border-radius:12px;padding:10px 14px;background:rgba(255,255,255,.01)}
summary{cursor:pointer;color:var(--mut2);font-size:.82rem}
pre{overflow:auto;max-height:420px;font-size:.70rem;color:var(--mut2);white-space:pre-wrap;word-break:break-word;background:rgba(0,0,0,.18);padding:12px;border-radius:10px;border:1px solid var(--line)}
.ops-nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.ops-nav a{padding:6px 12px;border:1px solid var(--line2);border-radius:999px;background:rgba(255,255,255,.03);font-size:.78rem;color:var(--mut2)}
.ops-nav a:hover{color:var(--ink);border-color:rgba(178,203,238,.35)}
"""


def _render(data: Dict[str, Any]) -> str:
    audit: Dict[str, Any] = data.get("audit") or {}
    decisions: Dict[str, Any] = data.get("decisions") or {}
    overrides: Dict[str, Any] = data.get("overrides") or {}
    gsc: Dict[str, Any] = data.get("gsc") or {}
    memory: Dict[str, Any] = data.get("memory") or {}
    opps: Dict[str, Any] = data.get("opportunities") or {}
    gen_at: str = data.get("generated_at") or _now()

    # derived numbers — defensive defaults so missing artefacts never 500
    finding_count = audit.get("finding_count") or len(audit.get("findings") or [])
    page_count = audit.get("page_count", "?")
    indexable = audit.get("indexable_count", "?")
    by_sev = audit.get("by_severity") or {}
    by_type = audit.get("by_type") or {}
    gsc_rows = audit.get("gsc_rows")
    if gsc_rows is None:
        # fall back to gsc.json rows length
        rows = gsc.get("rows") or []
        gsc_rows = len(rows) if isinstance(rows, list) else "?"
    gsc_pages = audit.get("gsc_pages", "?")
    audit_at = audit.get("generated_at") or "—"
    domain = audit.get("domain") or ""
    # decisions summary
    actions: List[Dict[str, Any]] = decisions.get("actions") or []
    summary = decisions.get("summary") or {}
    auto_ready = summary.get("AUTO", summary.get("auto", 0))
    pr_count = summary.get("PR", summary.get("pr", 0))
    human_count = summary.get("HUMAN", summary.get("human", 0))
    observe = summary.get("observe", 0)
    decisions_at = decisions.get("generated_at") or "—"
    # overrides
    pages = overrides.get("pages") or {}
    overrides_count = len(pages)
    history = overrides.get("history") or []
    # memory
    verifs = memory.get("verifications") or []
    outcomes = memory.get("outcomes") or []
    # opportunities
    opp_count = opps.get("opportunity_count", len(opps.get("opportunities") or []))
    opp_list = opps.get("opportunities") or []
    policy_notes = opps.get("policy_notes") or []

    # helpers rendered inline
    def pill(label: str, val: Any, warn: bool = False) -> str:
        cls = "pill warn" if warn else "pill"
        col = "var(--red)" if warn else "var(--green)"
        return f'<span class="{cls}"><span class="dot" style="background:{col};box-shadow:0 0 10px {col}"></span>{esc(label)} {esc(val)}</span>'

    # boards header pills
    audit_warn = finding_count == "?" or finding_count is None
    auto_warn = auto_ready is None or auto_ready == 0  # not an error — just colour
    # KPI values
    # Build severity chips
    sev_high = by_sev.get("high", 0)
    sev_med = by_sev.get("medium", 0)
    sev_low = by_sev.get("low", 0)

    # --- findings table helpers ---
    sev_class = {"high": "s-high", "medium": "s-medium", "low": "s-low"}
    mode_class = {"AUTO": "m-auto", "PR": "m-pr", "HUMAN": "m-human"}
    findings: List[Dict[str, Any]] = list(audit.get("findings") or [])
    # stable order: severity high→medium→low then path
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    findings_sorted = sorted(findings, key=lambda f: (sev_rank.get(f.get("severity"), 9), f.get("path", ""), f.get("type", "")))

    # actions split
    auto_actions = [a for a in actions if a.get("mode") == "AUTO"]
    pr_actions = [a for a in actions if a.get("mode") == "PR"]
    human_actions = [a for a in actions if a.get("mode") == "HUMAN"]

    def changes_html(changes: Dict[str, Any]) -> str:
        if not changes:
            return '<span class="muted">—</span>'
        parts = []
        for k, v in changes.items():
            vv = esc(v if not isinstance(v, str) else (v[:160] + "…" if len(v) > 160 else v))
            parts.append(f"<b>{esc(k)}</b>: {vv}")
        return "<br>".join(parts) or '<span class="muted">—</span>'

    def finding_row(f: Dict[str, Any]) -> str:
        t = esc(f.get("type", ""))
        path = esc(f.get("path", ""))
        sev = esc(f.get("severity", ""))
        detail = esc(f.get("detail", ""))[:220]
        cls = sev_class.get(str(f.get("severity", "")).lower(), "s-low")
        return (
            f'<tr><td><code class="small">{path}</code></td>'
            f'<td><span class="badge {cls}">{sev}</span></td>'
            f'<td><span class="kbd">{t}</span></td>'
            f'<td class="small" style="max-width:38ch">{detail}</td></tr>'
        )

    def action_row(a: Dict[str, Any]) -> str:
        path = esc(a.get("path", ""))
        typ = esc(a.get("type", ""))
        sev = esc(a.get("severity", ""))
        score = a.get("score", "")
        status = esc(a.get("status", ""))
        # map status badge
        if status == "ready_auto":
            st_cls, st_lbl = "st-auto", "AUTO · ready"
        elif status == "needs_pr":
            st_cls, st_lbl = "st-needs", "needs PR"
        elif status == "needs_human":
            st_cls, st_lbl = "st-needs", "needs human"
        elif status == "observe":
            st_cls, st_lbl = "st-observe", "observe"
        else:
            st_cls, st_lbl = "st-needs", status or "—"
        detail = esc(a.get("detail", ""))[:220]
        changes = changes_html(a.get("changes") or {})
        reason = esc(a.get("reason", ""))[:260]
        return (
            f'<tr>'
            f'<td><code class="small">{path}</code></td>'
            f'<td><span class="kbd">{typ}</span><br><span class="badge {sev_class.get(str(sev).lower(),"s-low")}" style="margin-top:4px;display:inline-block">{sev}</span></td>'
            f'<td class="num">{esc(score)}</td>'
            f'<td class="changes">{changes}</td>'
            f'<td class="small" style="max-width:30ch">{detail}<br><span class="muted">{reason}</span></td>'
            f'<td><span class="badge {st_cls}">{esc(st_lbl)}</span></td>'
            f'</tr>'
        )

    # overrides table rows — cap at 18 for readability, full json in <details>
    overrides_rows = ""
    if not pages:
        overrides_rows = '<tr><td colspan="3" class="muted small">No active overrides — <code>data/seo/overrides.json</code> is empty. AUTO writes land here after <code>apply --commit</code> and are applied on next <code>src/build.py</code>.</td></tr>'
    else:
        for path in sorted(pages.keys())[:20]:
            entry = pages[path] or {}
            fields = ", ".join(f"<b>{esc(k)}</b>" for k in entry.keys() if not k.startswith("_"))
            # short preview for value
            preview = ""
            for k in ("title", "meta_description", "og_title", "og_description"):
                if entry.get(k):
                    v = entry[k]
                    if len(str(v)) > 110:
                        v = str(v)[:110] + "…"
                    preview += f"{esc(k)}: {esc(v)}<br>"
            if not preview:
                preview = '<span class="muted">—</span>'
            overrides_rows += (
                f'<tr><td><code class="small">{esc(path)}</code></td>'
                f'<td class="small">{fields or "<span class=muted>—</span>"}</td>'
                f'<td class="changes">{preview}</td></tr>'
            )
        if len(pages) > 20:
            overrides_rows += f'<tr><td colspan="3" class="muted small">… and {len(pages)-20} more (see raw JSON below)</td></tr>'

    # learning memory rows
    verif_rows = ""
    if not verifs:
        verif_rows = '<tr><td colspan="5" class="muted small">No verifications yet — run <code>python3 -m seo_engine verify --record</code> after a rebuild to record pass/fail.</td></tr>'
    else:
        for v in reversed(verifs[-10:]):
            verif_rows += (
                f'<tr><td class="mono small">{esc(v.get("at","—"))}</td>'
                f'<td class="num">{esc(v.get("override_count","—"))}</td>'
                f'<td class="num" style="color:var(--green)">{esc(v.get("passed","—"))}</td>'
                f'<td class="num" style="color:var(--red)">{esc(v.get("failed","—"))}</td>'
                f'<td class="num muted">{esc(v.get("missing_file","—"))}</td></tr>'
            )

    # opportunities rows
    opp_rows = ""
    if not opp_list:
        opp_rows = '<tr><td colspan="4" class="muted small">No active opportunities. Seed gaps are PR-only proposals — see policy notes below. GSC content gaps appear automatically when <code>data/seo/gsc_export.json</code> has real impressions.</td></tr>'
    else:
        for o in opp_list[:12]:
            opp_rows += (
                f'<tr>'
                f'<td><span class="badge m-pr">{esc(o.get("priority","—"))}</span> <span class="kbd" style="margin-left:6px">{esc(o.get("opportunity","—"))}</span></td>'
                f'<td><code class="small">{esc(o.get("path") or o.get("collection_path") or "—")}</code></td>'
                f'<td class="small">{esc(o.get("landing_hint") or o.get("content_hint") or o.get("reason") or "")[:180]}</td>'
                f'<td class="small muted">{", ".join(esc(x) for x in (o.get("emerging_language") or [])[:3])}</td>'
                f'</tr>'
            )

    # by-type list for KPI context
    by_type_lines = ""
    if by_type:
        # sorted desc by count
        for t, n in sorted(by_type.items(), key=lambda kv: -kv[1]):
            by_type_lines += f'<span class="kbd">{esc(t)}</span> <span class="muted">{n}</span> &nbsp; '
        by_type_lines = by_type_lines.strip() or '<span class="muted">—</span>'
    else:
        by_type_lines = '<span class="muted">no findings — clean audit</span>'

    gsc_note = ""
    gsc_rows_val = gsc.get("rows")
    if isinstance(gsc_rows_val, list) and len(gsc_rows_val) == 0:
        gsc_note = "Empty — paste a Search Console export into <code>data/seo/gsc_export.json</code> to enable CTR-aware titles and GSC content gaps. See <code>seo_engine/README.md</code>. Numbers are never invented."
    elif isinstance(gsc_rows_val, list) and len(gsc_rows_val) > 0:
        gsc_note = f"{len(gsc_rows_val)} row(s) present — engine uses them for <span class=kbd>weak_ctr_title</span> detection."
    else:
        gsc_note = "No <code>gsc_export.json</code> — technical audit only (still useful)."

    # historic overrides history
    hist_note = ""
    if history:
        hist_note = f"{len(history)} change(s) in history (last: {esc(history[-1].get('at') or history[-1].get('date') or '—')})"
    else:
        hist_note = "No committed changes yet."

    top_findings_preview = ""
    if findings_sorted:
        # show first 14
        top_findings_preview = "\n".join(finding_row(f) for f in findings_sorted[:14])
        if len(findings_sorted) > 14:
            top_findings_preview += f'\n<tr><td colspan="4" class="muted small">… {len(findings_sorted)-14} more findings in raw JSON</td></tr>'
    else:
        top_findings_preview = '<tr><td colspan="4" class="muted small">No findings — the site is clean against the audited rules (title / description budgets, canonical, OG, H1, duplicate titles, GSC CTR when data is present).</td></tr>'

    # build final HTML
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="theme-color" content="#070e1a">
<title>SEO Engine — Ops Dashboard | Gridiron Locker</title>
<style>{CSS}</style>
</head>
<body>
<div class="topbar"><div class="topbar-inner">
 <div class="brand"><span class="mark">SEO</span><span>SEO Engine <small>Gridiron Locker · ops / seo · noindex</small></span></div>
 <span class="pill"><span class="dot"></span>Audit {esc(audit_at)}</span>
 <span class="pill">Decisions {esc(decisions_at)}</span>
 <span class="pill">{esc(domain or "gridironlocker.store")}</span>
 <span class="pill"><a href="../index.html">← Ops index</a></span>
</div></div>

<main class="wrap" style="padding:28px 0 10px">
 <h1>SEO Engine <span style="color:var(--green)">Ops Dashboard</span></h1>
 <p class="lead">Controlled-autonomy loop — <span class="kbd">audit → decide → apply → verify → learn</span>. AUTO writes only <code>data/seo/overrides.json</code>; <code>src/build.py</code> materialises into <code>site/</code>. PR / HUMAN are proposal-only and never touch production without operator approval. No fabricated metrics.</p>

 <div class="ops-nav">
  <a href="../scout/index.html">Scout</a>
  <a href="../board/index.html">Board</a>
  <a href="../hq/index.html">HQ</a>
  <a href="../marketing/index.html">Marketing</a>
  <a href="#audit">Audit snapshot</a>
  <a href="#actions">Actions</a>
  <a href="#overrides">Overrides</a>
  <a href="#gsc">GSC</a>
 </div>

 <!-- KPI strip -->
 <div class="kpis">
  <div class="kpi"><b>{esc(page_count)}</b><span>Pages crawled</span><br><em class="small">{esc(indexable)} indexable · stubs excluded</em></div>
  <div class="kpi"><b>{esc(finding_count)}</b><span>Findings</span><br><em class="small"><span class="badge s-high" style="font-size:.62rem">high {sev_high}</span> <span class="badge s-medium" style="font-size:.62rem">med {sev_med}</span> <span class="badge s-low" style="font-size:.62rem">low {sev_low}</span></em></div>
  <div class="kpi"><b style="color:var(--green)">{esc(auto_ready)}</b><span>AUTO ready</span><br><em class="small">→ data/seo/overrides.json</em></div>
  <div class="kpi"><b>{esc(pr_count)}</b><span>PR proposals</span><br><em class="small">needs human review</em></div>
  <div class="kpi"><b>{esc(human_count)}</b><span>HUMAN flags</span><br><em class="small">URL / delete / merge</em></div>
  <div class="kpi"><b>{esc(overrides_count)}</b><span>Active overrides</span><br><em class="small">{esc(hist_note)}</em></div>
  <div class="kpi"><b>{esc(gsc_rows)}</b><span>GSC rows</span><br><em class="small">{esc(gsc_pages)} pages covered</em></div>
  <div class="kpi"><b>{len(verifs)}</b><span>Verifications</span><br><em class="small">{len(outcomes)} measured GSC outcomes</em></div>
 </div>

 <div class="grid2">
  <div class="card">
   <h2>Audit snapshot</h2>
   <p class="muted small">From <code>data/seo/last_audit.json</code> @ <span class="mono">{esc(audit_at)}</span> · domain {esc(domain or "—")} · engine {esc(audit.get("engine","—"))}</p>
   <p class="small muted">By type: {by_type_lines}</p>
   <p class="small muted">By severity: <span class="badge s-high">high {sev_high}</span> <span class="badge s-medium">medium {sev_med}</span> <span class="badge s-low">low {sev_low}</span> · GSC rows {esc(gsc_rows)}, pages {esc(gsc_pages)} · Page count {esc(page_count)}, indexable {esc(indexable)}</p>
   <p class="small">{esc(gsc_note)}</p>
  </div>
  <div class="card">
   <h2>Contract</h2>
   <p class="small" style="margin-top:6px"><b>AUTO</b> writes <code>data/seo/overrides.json</code> fields: <code>title</code> · <code>meta_description</code> · <code>og_title</code> · <code>og_description</code>. Rebuild required before <code>verify</code> can pass. <b>PR</b> proposals land under <code>data/seo/proposals/</code> · <b>HUMAN</b> never auto-applies.</p>
   <p class="small muted">Still forbidden: fabricated trust signals, thin fan-intent pages at scale, meta-keywords stuffing, player-likeness / team-logo suggestions. <code>site/</code> is never hand-edited — see AGENTS.md §3.3.</p>
   <p class="small">Runbook: <code class="kbd">python3 -m seo_engine run</code> (dry-run) · <code class="kbd">python3 -m seo_engine apply --commit</code> then <code class="kbd">python3 src/build.py</code> then <code class="kbd">python3 -m seo_engine verify --record</code></p>
   <p class="small muted">Generated {esc(gen_at)} · <span class="kbd">seo_engine/dashboard.py</span> → <span class="kbd">ops/seo/index.html</span> → <span class="kbd">site/ops/seo/</span></p>
  </div>
 </div>

 <section id="audit">
  <div class="card">
   <h2>Audit findings <span class="muted" style="font-weight:600">· {esc(finding_count)} total</span></h2>
   <p class="muted small">Crawl of <code>site/</code> (indexable pages only — redirect stubs & noindex pages excluded). Full list also in <code>data/seo/last_audit.json</code>.</p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>Path</th><th>Severity</th><th>Type</th><th>Detail</th></tr></thead>
    <tbody>{top_findings_preview}</tbody>
   </table>
   </div>
   <details><summary>Raw audit JSON (first 40 findings)</summary><pre>{esc(json.dumps(dict(audit, findings=findings_sorted[:40]) if findings else audit, indent=2, ensure_ascii=False)[:7000])}</pre></details>
  </div>
 </section>

 <section id="actions">
  <div class="card">
   <h2>AUTO / PR / HUMAN actions <span class="muted" style="font-weight:600">· {len(actions)} total</span></h2>
   <p class="muted small">From <code>data/seo/last_decisions.json</code> @ <span class="mono">{esc(decisions_at)}</span> · AUTO <span class="badge m-auto">{esc(auto_ready)}</span> · PR <span class="badge m-pr">{esc(pr_count)}</span> · HUMAN <span class="badge m-human">{esc(human_count)}</span> · observe {esc(observe)}</p>

   <h3 style="color:var(--green)">AUTO · ready to apply</h3>
   <p class="small muted">Low-risk metadata/OG trims that <code>apply --commit</code> writes to <code>data/seo/overrides.json</code>. Rebuild to land in live HTML; <code>verify</code> confirms.</p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>Path</th><th>Type</th><th>Score</th><th>Changes</th><th>Detail · reason</th><th>Status</th></tr></thead>
    <tbody>
     {"".join(action_row(a) for a in auto_actions[:18]) if auto_actions else '<tr><td colspan="6" class="muted small">No AUTO-ready actions. Audit is clean or suggestions are already overridden. (observe-only rows still appear in raw decisions JSON.)</td></tr>'}
    </tbody>
   </table>
   </div>
   {f'<p class="small muted">… +{len(auto_actions)-18} more AUTO rows in raw JSON</p>' if len(auto_actions) > 18 else ''}

   <h3>PR · needs human review</h3>
   <p class="small muted">Content rewrites, new guides, internal-link clusters, schema enrichment — proposal files under <code>data/seo/proposals/</code>; never auto-merged.</p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>Path</th><th>Type</th><th>Score</th><th>Changes</th><th>Detail</th><th>Status</th></tr></thead>
    <tbody>
     {"".join(action_row(a) for a in pr_actions[:12]) if pr_actions else '<tr><td colspan="6" class="muted small">No PR actions queued.</td></tr>'}
    </tbody>
   </table>
   </div>

   <h3>HUMAN · flag only</h3>
   <p class="small muted">URL changes, deletes, merges, redirect remaps — flagged, never auto-applied.</p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>Path</th><th>Type</th><th>Score</th><th>Changes</th><th>Detail</th><th>Status</th></tr></thead>
    <tbody>
     {"".join(action_row(a) for a in human_actions[:12]) if human_actions else '<tr><td colspan="6" class="muted small">No HUMAN flags.</td></tr>'}
    </tbody>
   </table>
   </div>
   <details><summary>Raw decisions JSON</summary><pre>{esc(json.dumps(decisions, indent=2, ensure_ascii=False)[:9000])}</pre></details>
  </div>
 </section>

 <section id="overrides">
  <div class="card">
   <h2>Active overrides <span class="muted" style="font-weight:600">· {esc(overrides_count)} page(s)</span></h2>
   <p class="muted small">Live file: <code>data/seo/overrides.json</code> (schema v{esc(overrides.get("schema_version","—"))}) · updated {esc(overrides.get("updated") or "—")} · {esc(hist_note)}. Keys are URL paths (<code>/shop/slug/</code>, <code>/michigan-wolverines-shirts/</code>). Supported fields: <code>title</code> · <code>meta_description</code> · <code>og_title</code> · <code>og_description</code>.</p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>Path</th><th>Fields</th><th>Preview</th></tr></thead>
    <tbody>{overrides_rows}</tbody>
   </table>
   </div>
   <details><summary>Raw overrides.json</summary><pre>{esc(json.dumps(overrides, indent=2, ensure_ascii=False)[:8000])}</pre></details>
  </div>
 </section>

 <section id="gsc" style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
  <div class="card" style="margin-top:0">
   <h2>GSC export</h2>
   <p class="small">{esc(gsc_note)}</p>
   <p class="muted small">File: <code>data/seo/gsc_export.json</code> · rows {esc(gsc_rows)}</p>
   <pre style="margin-top:8px">{esc(json.dumps(gsc if len(json.dumps(gsc, ensure_ascii=False)) < 4000 else dict(rows=(gsc.get("rows") or [])[:6], _truncated=f"... +{max(0, len(gsc.get('rows') or [])-6)} rows", **{k:v for k,v in gsc.items() if k!='rows'}), indent=2, ensure_ascii=False)[:3800])}</pre>
   <p class="small muted">Real CTR / impressions are only shown when this file has rows. Without it the engine still audits titles / descriptions / canonical / OG.</p>
  </div>
  <div class="card" style="margin-top:0">
   <h2>Learning loop</h2>
   <p class="small">Verifications recorded after each <code>apply --commit</code> + rebuild via <code>verify --record</code>. Compounds over time; without real GSC it stays small on purpose. Outcomes are operator-supplied GSC before/after rows keyed by change.</p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>When</th><th>Overrides</th><th>Pass</th><th>Fail</th><th>Missing</th></tr></thead>
    <tbody>{verif_rows}</tbody>
   </table>
   </div>
   <p class="small muted" style="margin-top:10px">Tracked outcomes: {len(outcomes)} · Memory file: <code>data/seo/learning_memory.json</code> · Last updated {esc(memory.get("last_updated") or "—")}</p>
   <details><summary>Raw learning_memory.json</summary><pre>{esc(json.dumps(memory, indent=2, ensure_ascii=False)[:6000])}</pre></details>
  </div>
 </section>

 <section>
  <div class="card">
   <h2>Content opportunities <span class="muted" style="font-weight:600">· PR-only · {esc(opp_count)}</span></h2>
   <p class="muted small">Seed concepts (from radar) + GSC gaps. Producing any page still needs a guide/collective rewrite PR — no thin intent pages. Policy: <em>{esc("; ".join(policy_notes[:3]) or "—")}</em></p>
   <div style="overflow:auto">
   <table>
    <thead><tr><th>Opportunity</th><th>Path</th><th>Hint</th><th>Emerging language</th></tr></thead>
    <tbody>{opp_rows}</tbody>
   </table>
   </div>
   <details><summary>Full policy notes + raw opportunities</summary>
    <ul>{"".join(f"<li class='small'><code class='muted'>{esc(n)}</code></li>" for n in policy_notes)}</ul>
    <pre>{esc(json.dumps(opps, indent=2, ensure_ascii=False)[:7000])}</pre>
   </details>
  </div>
 </section>

 <section>
  <div class="card" style="border-color:rgba(114,224,186,.28)">
   <h2 style="color:var(--green)">How to run</h2>
   <p class="small"><code class="kbd">python3 -m seo_engine run</code> — report-only full loop (safe default). Add <code class="kbd">--commit</code> to let AUTO write <code>overrides.json</code>.</p>
   <p class="small"><code class="kbd">python3 -m seo_engine audit --save</code> · <code class="kbd">python3 -m seo_engine decide --save</code> · <code class="kbd">python3 -m seo_engine apply</code> (dry) · <code class="kbd">python3 -m seo_engine apply --commit</code> (writes)</p>
   <p class="small"><code class="kbd">python3 src/build.py</code> — materialise overrides into HTML · <code class="kbd">python3 -m seo_engine verify --record</code> · <code class="kbd">python3 qa_audit.py</code> must stay <b>TOTAL: 0</b></p>
   <p class="small muted">Do not hand-edit <code>site/</code> for SEO content — see AGENTS.md §3.3. Overrides go through <code>data/seo/overrides.json</code> + rebuild.</p>
  </div>
 </section>
</main>

<footer class="foot"><div class="wrap">
  <span>SEO Engine dashboard · ops/seo · noindex · robots Disallow: /ops/ · <span class="mono">{esc(gen_at)}</span> · <a href="../index.html">Ops Index</a></span>
  <span class="muted">Audit verdict: <b style="color:{'var(--green)' if finding_count==0 else 'var(--orange)'}">{esc(finding_count)} finding(s)</b> · AUTO {esc(auto_ready)} · PR {esc(pr_count)} · HUMAN {esc(human_count)} · <a href="https://github.com/gridironlocker/gridiron-locker/blob/main/seo_engine/README.md">README</a></span>
</div></footer>
</body>
</html>
"""


def main() -> int:
    data = _load_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html_out = OUT_DIR / "index.html"
    rendered = _render(data)
    html_out.write_text(rendered, encoding="utf-8")
    print(f"seo_engine dashboard: wrote {html_out} ({len(rendered)} bytes)")
    # also ensure audit/decisions files exist for the build's verification step
    # (they are expected by the dashboard but not required for the storefront)
    # If they were missing, _load_all already handled it — now ensure they are
    # persisted so the next build's dashboard has history.
    try:
        try:
            from .config import AUDIT_PATH, DECISIONS_PATH, ensure_seo_dirs, write_json  # type: ignore
            from .audit import run_audit  # type: ignore
            from .decide import decide  # type: ignore
        except (ImportError, ValueError):
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from seo_engine.config import AUDIT_PATH, DECISIONS_PATH, ensure_seo_dirs, write_json
            from seo_engine.audit import run_audit
            from seo_engine.decide import decide
        # Back-fill last_audit/last_decisions if absent so ops/seo always has a snapshot
        if not AUDIT_PATH.is_file():
            audit = run_audit()
            slim = dict(audit)
            slim.pop("pages", None)
            ensure_seo_dirs()
            write_json(AUDIT_PATH, slim)
        if not DECISIONS_PATH.is_file():
            audit_data = read_json(AUDIT_PATH, default={})
            if not audit_data:
                audit_data = run_audit()
                slim = dict(audit_data)
                slim.pop("pages", None)
                ensure_seo_dirs()
                write_json(AUDIT_PATH, slim)
            dec = decide(audit_data)
            ensure_seo_dirs()
            write_json(DECISIONS_PATH, dec)
    except Exception as e:
        # non-fatal — dashboard is already written
        print(f"seo_engine dashboard: back-fill skipped: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
