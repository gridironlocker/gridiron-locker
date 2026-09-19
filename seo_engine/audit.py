"""Technical + on-page SEO auditor.

Reads the crawl inventory and optional GSC export. Emits structured findings
the decider turns into AUTO / PR / HUMAN actions. Never mutates the site.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from .config import (
    DESC_MAX,
    DESC_MIN,
    GSC_EXPORT_PATH,
    TITLE_MAX,
    TITLE_MIN,
    domain,
    read_json,
)
from .crawler import Page, crawl


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_gsc_export(path=None) -> List[dict]:
    """Optional GSC performance rows.

    Expected shape (one row per page or page+query)::

        {
          "rows": [
            {
              "page": "https://gridironlocker.store/michigan-wolverines-shirts/",
              "query": "michigan football shirts",
              "clicks": 12,
              "impressions": 840,
              "ctr": 0.014,
              "position": 12.4
            }
          ]
        }

    Absent file → empty list. Never invents numbers.
    """
    data = read_json(path or GSC_EXPORT_PATH, default={})
    rows = data.get("rows") if isinstance(data, dict) else data
    return list(rows or [])


def _page_key(url_or_path: str) -> str:
    d = domain()
    if url_or_path.startswith("http"):
        url_or_path = url_or_path.replace(d, "")
    if not url_or_path.startswith("/"):
        url_or_path = "/" + url_or_path
    if not url_or_path.endswith("/") and "." not in url_or_path.rsplit("/", 1)[-1]:
        url_or_path += "/"
    return url_or_path


def gsc_by_page(rows: List[dict]) -> Dict[str, dict]:
    """Aggregate GSC rows to per-page totals + top queries."""
    agg: Dict[str, dict] = {}
    for row in rows:
        page = row.get("page") or row.get("url") or ""
        if not page:
            continue
        key = _page_key(page)
        bucket = agg.setdefault(key, {
            "clicks": 0, "impressions": 0, "position_sum": 0.0,
            "position_n": 0, "queries": [],
        })
        clicks = float(row.get("clicks") or 0)
        imps = float(row.get("impressions") or 0)
        pos = row.get("position")
        bucket["clicks"] += clicks
        bucket["impressions"] += imps
        if pos is not None:
            bucket["position_sum"] += float(pos) * (imps or 1)
            bucket["position_n"] += (imps or 1)
        q = row.get("query")
        if q:
            bucket["queries"].append({
                "query": q,
                "clicks": clicks,
                "impressions": imps,
                "ctr": row.get("ctr"),
                "position": pos,
            })
    for key, bucket in agg.items():
        imps = bucket["impressions"] or 0
        bucket["ctr"] = (bucket["clicks"] / imps) if imps else 0.0
        bucket["position"] = (
            bucket["position_sum"] / bucket["position_n"]
            if bucket["position_n"] else None
        )
        bucket["queries"].sort(key=lambda q: -q["impressions"])
        del bucket["position_sum"]
        del bucket["position_n"]
    return agg


def _finding(ftype: str, path: str, severity: str, detail: str,
             evidence: Optional[dict] = None, suggested: Optional[dict] = None) -> dict:
    return {
        "type": ftype,
        "path": path,
        "severity": severity,          # low|medium|high
        "detail": detail,
        "evidence": evidence or {},
        "suggested": suggested or {},
    }


def _expected_canonical(path: str) -> str:
    return domain() + (path if path.startswith("/") else "/" + path)


def audit_pages(pages: List[Page], gsc: Optional[Dict[str, dict]] = None) -> List[dict]:
    """Return a flat list of findings across the inventory."""
    gsc = gsc or {}
    findings: List[dict] = []

    title_owners: Dict[str, List[str]] = defaultdict(list)
    desc_owners: Dict[str, List[str]] = defaultdict(list)

    for p in pages:
        if p.kind == "stub" or p.noindex:
            # Redirect stubs are deliberately noindex; skip SEO polish noise.
            continue
        if p.path.endswith("404.html") or p.path == "/404.html":
            continue

        # --- title ---
        if not p.title:
            findings.append(_finding(
                "missing_title", p.path, "high",
                "Page has no <title>.",
                suggested={"title": _default_title_for(p)},
            ))
        else:
            tlen = len(p.title)
            if tlen > TITLE_MAX:
                findings.append(_finding(
                    "title_too_long", p.path, "medium",
                    f"Title is {tlen} chars (budget {TITLE_MAX}).",
                    evidence={"title": p.title, "length": tlen},
                    suggested={"title": _trim_title(p.title)},
                ))
            elif tlen < TITLE_MIN and p.kind in ("product", "collection", "guide", "home"):
                findings.append(_finding(
                    "title_too_short", p.path, "low",
                    f"Title is {tlen} chars (min useful ~{TITLE_MIN}).",
                    evidence={"title": p.title, "length": tlen},
                ))
            title_owners[p.title.strip().lower()].append(p.path)

        # --- meta description ---
        if not p.meta_description:
            findings.append(_finding(
                "missing_description", p.path, "high",
                "Page has no meta description.",
                suggested={"meta_description": _default_description_for(p)},
            ))
        else:
            dlen = len(p.meta_description)
            if dlen > DESC_MAX:
                findings.append(_finding(
                    "description_too_long", p.path, "medium",
                    f"Meta description is {dlen} chars (budget {DESC_MAX}).",
                    evidence={"meta_description": p.meta_description, "length": dlen},
                    suggested={"meta_description": _trim_desc(p.meta_description)},
                ))
            elif dlen < DESC_MIN and p.kind in ("product", "collection", "guide", "home"):
                findings.append(_finding(
                    "description_too_short", p.path, "low",
                    f"Meta description is {dlen} chars (min useful ~{DESC_MIN}).",
                    evidence={"meta_description": p.meta_description, "length": dlen},
                ))
            desc_owners[p.meta_description.strip().lower()].append(p.path)

        # --- canonical ---
        expected = _expected_canonical(p.path)
        if not p.canonical:
            findings.append(_finding(
                "missing_canonical", p.path, "high",
                "Page has no rel=canonical.",
                suggested={"canonical": expected},
            ))
        elif p.canonical.rstrip("/") != expected.rstrip("/"):
            # Mismatch is informational — build.py owns canonicals; flag only.
            findings.append(_finding(
                "canonical_mismatch", p.path, "medium",
                f"Canonical {p.canonical!r} != expected {expected!r}.",
                evidence={"canonical": p.canonical, "expected": expected},
            ))

        # --- Open Graph ---
        if not p.og_title and p.kind in ("product", "collection", "home", "guide"):
            findings.append(_finding(
                "missing_og_title", p.path, "low",
                "Missing og:title.",
                suggested={"og_title": p.title},
            ))
        if not p.og_description and p.kind in ("product", "collection", "home", "guide"):
            findings.append(_finding(
                "missing_og_description", p.path, "low",
                "Missing og:description.",
                suggested={"og_description": p.meta_description},
            ))

        # --- H1 ---
        if p.kind in ("product", "collection", "guide", "home", "static"):
            if not p.h1:
                findings.append(_finding(
                    "missing_h1", p.path, "high",
                    "Page has no H1.",
                ))
            elif len(p.h1) > 1:
                findings.append(_finding(
                    "multiple_h1", p.path, "medium",
                    f"Page has {len(p.h1)} H1 elements.",
                    evidence={"h1": p.h1},
                ))

        # --- image alt ---
        missing_alts = [img for img in p.image_alts if img.get("missing")]
        if missing_alts:
            findings.append(_finding(
                "missing_image_alt", p.path, "medium",
                f"{len(missing_alts)} image(s) missing alt text.",
                evidence={"count": len(missing_alts),
                          "samples": [i.get("src") for i in missing_alts[:5]]},
            ))

        # --- GSC-backed weak CTR (only when real data is present) ---
        perf = gsc.get(p.path)
        if perf and perf.get("impressions", 0) >= 100 and perf.get("ctr", 1) < 0.02:
            top_q = (perf.get("queries") or [{}])[0]
            findings.append(_finding(
                "weak_ctr_title", p.path, "medium",
                (f"GSC: {int(perf['impressions'])} impressions, "
                 f"CTR {perf['ctr']*100:.1f}%, pos {perf.get('position')}. "
                 f"Top query: {top_q.get('query')!r}."),
                evidence={
                    "impressions": perf["impressions"],
                    "clicks": perf["clicks"],
                    "ctr": perf["ctr"],
                    "position": perf.get("position"),
                    "top_query": top_q.get("query"),
                    "current_title": p.title,
                },
                suggested=_ctr_title_suggestion(p, top_q.get("query")),
            ))

    # --- duplicates across the indexable set ---
    for title, owners in title_owners.items():
        if len(owners) > 1 and title:
            for path in owners:
                findings.append(_finding(
                    "duplicate_title", path, "high",
                    f"Title shared with {len(owners) - 1} other page(s).",
                    evidence={"title": title, "owners": owners},
                ))
    for desc, owners in desc_owners.items():
        if len(owners) > 1 and desc:
            for path in owners:
                findings.append(_finding(
                    "duplicate_description", path, "high",
                    f"Meta description shared with {len(owners) - 1} other page(s).",
                    evidence={"owners": owners},
                ))

    return findings


def _default_title_for(p: Page) -> str:
    if p.h1:
        base = p.h1[0]
        candidate = f"{base} | Gridiron Locker"
        return candidate if len(candidate) <= TITLE_MAX else base[:TITLE_MAX]
    slug = p.path.strip("/").split("/")[-1].replace("-", " ").title()
    return f"{slug} | Gridiron Locker"[:TITLE_MAX]


def _default_description_for(p: Page) -> str:
    if p.h1:
        body = (
            f"{p.h1[0]} — independent, fan-made football apparel from Gridiron Locker. "
            f"Printed on demand and shipped worldwide."
        )
    else:
        body = (
            "Independent, fan-made football apparel from Gridiron Locker. "
            "Printed on demand and shipped worldwide."
        )
    return _trim_desc(body)


def _trim_title(title: str) -> str:
    if len(title) <= TITLE_MAX:
        return title
    # Prefer dropping the brand suffix, then truncating on a word boundary.
    for suffix in (" | Gridiron Locker", " - Gridiron Locker", " | Gridiron"):
        if title.endswith(suffix) and len(title) - len(suffix) >= TITLE_MIN:
            return title[: -len(suffix)]
    cut = title[: TITLE_MAX - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" |-–,.")


def _trim_desc(desc: str) -> str:
    if len(desc) <= DESC_MAX:
        return desc
    cut = desc[: DESC_MAX - 3].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.-") + "..."


def _ctr_title_suggestion(p: Page, query: Optional[str]) -> dict:
    """Propose a title that surfaces the query the page already almost ranks for.

    Conservative: keep the product/collection identity, weave the query phrase
    in, stay inside the SERP budget. Never invent brand claims.
    """
    if not query:
        return {}
    q = query.strip()
    # Collection pages: "{Query Phrase} | Gridiron Locker"
    if p.kind == "collection":
        candidate = f"{q.title()} | Gridiron Locker"
        if len(candidate) > TITLE_MAX:
            candidate = f"{q.title()}"
        return {"title": candidate[:TITLE_MAX], "query": q}
    # Product pages: keep product name, swap the intent segment.
    name = (p.h1[0] if p.h1 else (p.title or "").split("|")[0]).strip()
    if not name:
        return {}
    candidate = f"{name} | {q.title()} | Gridiron Locker"
    if len(candidate) > TITLE_MAX:
        candidate = f"{name} | {q.title()}"
    if len(candidate) > TITLE_MAX:
        candidate = name
    return {"title": candidate[:TITLE_MAX], "query": q}


def run_audit(site=None, gsc_path=None) -> dict:
    """Full audit. Returns a machine report; caller decides whether to persist."""
    from .config import SITE
    pages = crawl(site or SITE)
    gsc_rows = load_gsc_export(gsc_path)
    gsc = gsc_by_page(gsc_rows)
    findings = audit_pages(pages, gsc)

    by_type = Counter(f["type"] for f in findings)
    by_severity = Counter(f["severity"] for f in findings)
    indexable = [p for p in pages if not p.noindex and p.kind != "stub"]

    return {
        "generated_at": _now(),
        "engine": "seo_engine.audit",
        "domain": domain(),
        "page_count": len(pages),
        "indexable_count": len(indexable),
        "gsc_rows": len(gsc_rows),
        "gsc_pages": len(gsc),
        "finding_count": len(findings),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "findings": findings,
        "pages": [p.to_dict() for p in pages],
    }
