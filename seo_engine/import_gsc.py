"""Import Google Search Console CSV exports into ``data/seo/``.

Two Search Console export flavours are supported, detected per CSV by
header (never by filename alone — ``Chart.csv`` exists in both):

**Performance export** (Performance → Export → CSV) → ``data/seo/gsc_export.json``

    Pages.csv                (required — becomes rows[])
    Queries.csv              (optional — kept under ``queries``)
    Chart.csv                (optional — daily series, kept under ``daily``)
    Devices.csv              (optional — kept under ``devices``)
    Countries.csv            (optional — kept under ``countries``)
    Search appearance.csv    (optional — kept under ``search_appearance``)
    Filters.csv              (optional — kept under ``filters``)

**Page Indexing export** (Page indexing → Export → CSV) → ``data/seo/gsc_indexing.json``

    Metadata.csv             (optional — property/sitemap context)
    Chart.csv                (optional — Date, Not indexed, Indexed, Impressions)
    Critical issues.csv      (optional — reason/source/validation/pages)
    Non-critical issues.csv  (optional — same shape)

Faithful import only: numbers are copied verbatim (percent strings become
decimal fractions, blank chart cells stay ``null`` — blank is not zero).
Nothing is invented or estimated. Performance tables absent from the drop
directory are preserved from any previous import, never silently dropped.

``rows[]`` carries the row contract consumed by ``seo_engine.audit`` and
``seo_engine.content`` (page + optional query). The Performance export does
not attribute queries to pages, so ``rows[]`` is page-level and the query
table is preserved separately — never guessed onto a page.

Usage::

    python3 -m seo_engine.import_gsc path/to/export-dir
    python3 -m seo_engine.import_gsc path/to/export-dir --out /tmp/gsc.json
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .config import GSC_EXPORT_PATH, GSC_INDEXING_PATH

REQUIRED = "Pages.csv"
INDEXING_OUT = GSC_INDEXING_PATH

# First-column label in the GSC CSV → canonical key used in the JSON tables.
_LABEL_KEYS = {
    "Top pages": "page",
    "Top queries": "query",
    "Date": "date",
    "Country": "country",
    "Device": "device",
    "Search Appearance": "search_appearance",
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pct(value: str) -> float:
    """GSC percent string ('22.22%') → decimal fraction (0.2222)."""
    v = (value or "").strip().replace("%", "")
    if not v:
        return 0.0
    return round(float(v) / 100.0, 6)


def count(value: str) -> int:
    """GSC integer string ('1,234') → int."""
    return int((value or "0").strip().replace(",", "") or 0)


def nullable_count(value: str):
    """Blank cell → None (blank ≠ zero), else int."""
    v = (value or "").strip().replace(",", "")
    return int(v) if v else None


def number(value: str) -> float:
    """GSC decimal string ('39.68') → float."""
    v = (value or "").strip().replace(",", "")
    return float(v) if v else 0.0


def load_csv(path: Path) -> List[Dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def csv_headers(path: Path) -> List[str]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.reader(fh).__next__()) if path.stat().st_size else []


def _metric_rows(raw: List[Dict]) -> List[Dict]:
    """Convert one Performance metric table into JSON rows (label key + 4 metrics).

    The label key comes from the file's actual first-column header
    ('Top pages', 'Top queries', 'Date', 'Country', 'Device',
    'Search Appearance') via ``_LABEL_KEYS``.
    """
    out = []
    for row in raw:
        if not row:
            continue
        label = next(iter(row))  # first CSV column header, in file order
        item: Dict[str, object] = {}
        key = _LABEL_KEYS.get(label)
        if key:
            item[key] = (row.get(label) or "").strip()
        item["clicks"] = count(row.get("Clicks", ""))
        item["impressions"] = count(row.get("Impressions", ""))
        item["ctr"] = pct(row.get("CTR", ""))
        item["position"] = number(row.get("Position", ""))
        out.append(item)
    return out


def _is_performance_chart(path: Path) -> bool:
    return "Clicks" in csv_headers(path)


def _is_indexing_chart(path: Path) -> bool:
    return "Not indexed" in csv_headers(path)


def build_export(csv_dir: Path, previous: Optional[dict] = None) -> dict:
    """Build the Performance export dict from CSVs in ``csv_dir``.

    ``previous`` (a previously imported dict) supplies tables whose CSVs are
    absent this time — verbatim data preserved, never invented.
    """
    pages_path = csv_dir / REQUIRED
    if not pages_path.exists():
        raise FileNotFoundError(f"{pages_path} not found — {REQUIRED} is required")

    tables = {
        "Queries.csv": "queries",
        "Chart.csv": "daily",
        "Devices.csv": "devices",
        "Countries.csv": "countries",
        "Search appearance.csv": "search_appearance",
    }
    preserved = previous or {}

    data: Dict[str, object] = {
        "schema_version": 1,
        "updated": _now(),
        "source": (
            "Imported by seo_engine.import_gsc from a Search Console "
            "Performance CSV export. rows[] are page-level aggregates "
            "(clicks, impressions, ctr as decimal fraction, position). "
            "The export's 'Top queries' table has no page attribution, so "
            "query-level aggregates live under 'queries' and are never "
            "attached to a page. All numbers are copied verbatim."
        ),
        "contract": (
            "Each row: page (absolute URL), optional query, clicks, "
            "impressions, ctr, position. Used by seo_engine.audit for "
            "weak-CTR detection and by seo_engine.content for content-gap "
            "proposals."
        ),
    }

    data["rows"] = _metric_rows(load_csv(pages_path))

    for filename, key in tables.items():
        path = csv_dir / filename
        if filename == "Chart.csv" and path.exists() and not _is_performance_chart(path):
            continue  # indexing chart (same filename in that export flavour)
        if path.exists():
            data[key] = _metric_rows(load_csv(path))
        elif key in preserved:
            data[key] = preserved[key]
    if "daily" not in data and "daily" in preserved:
        data["daily"] = preserved["daily"]
        data["source"] += (" Table 'daily' preserved from the previous import "
                           "(its CSV was absent from this drop).")

    filters_path = csv_dir / "Filters.csv"
    if filters_path.exists():
        data["filters"] = [
            {"filter": (r.get("Filter") or "").strip(), "value": (r.get("Value") or "").strip()}
            for r in load_csv(filters_path)
        ]
    elif "filters" in preserved:
        data["filters"] = preserved["filters"]

    return data


def build_indexing(csv_dir: Path) -> dict:
    """Build the Page Indexing (coverage) export dict from CSVs in ``csv_dir``."""
    found = [csv_dir / n for n in ("Metadata.csv", "Chart.csv", "Critical issues.csv",
                                   "Non-critical issues.csv")]
    if not any(p.exists() and (p.name != "Chart.csv" or _is_indexing_chart(p)) for p in found):
        raise FileNotFoundError(
            f"no Page Indexing CSVs found in {csv_dir} (Metadata.csv / Chart.csv "
            f"/ Critical issues.csv / Non-critical issues.csv)")

    data: Dict[str, object] = {
        "schema_version": 1,
        "updated": _now(),
        "source": (
            "Imported by seo_engine.import_gsc from a Search Console Page "
            "Indexing (coverage) CSV export. All numbers copied verbatim; "
            "blank chart cells stay null. issue counts are Google's page "
            "counts at export time."
        ),
        "property": None,
        "issues": [],
        "non_critical_issues": [],
        "daily": [],
    }

    meta_path = csv_dir / "Metadata.csv"
    if meta_path.exists():
        for row in load_csv(meta_path):
            key = (row.get("Property") or "").strip().lower()
            if key == "sitemap":
                data["property"] = (row.get("Value") or "").strip()

    chart_path = csv_dir / "Chart.csv"
    if chart_path.exists() and _is_indexing_chart(chart_path):
        data["daily"] = [
            {
                "date": (r.get("Date") or "").strip(),
                "not_indexed": nullable_count(r.get("Not indexed", "")),
                "indexed": nullable_count(r.get("Indexed", "")),
                "impressions": count(r.get("Impressions", "")),
            }
            for r in load_csv(chart_path)
        ]

    issues_path = csv_dir / "Critical issues.csv"
    if issues_path.exists():
        data["issues"] = [
            {
                "reason": (r.get("Reason") or "").strip(),
                "source": (r.get("Source") or "").strip(),
                "validation": (r.get("Validation") or "").strip(),
                "pages": count(r.get("Pages", "")),
            }
            for r in load_csv(issues_path)
        ]

    noncrit_path = csv_dir / "Non-critical issues.csv"
    if noncrit_path.exists():
        data["non_critical_issues"] = [
            {
                "reason": (r.get("Reason") or "").strip(),
                "source": (r.get("Source") or "").strip(),
                "validation": (r.get("Validation") or "").strip(),
                "pages": count(r.get("Pages", "")),
            }
            for r in load_csv(noncrit_path)
        ]

    return data


def import_export(csv_dir, out_path=None) -> Path:
    csv_dir = Path(csv_dir)
    out = Path(out_path or GSC_EXPORT_PATH)
    previous = {}
    if out.exists():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = {}
    data = build_export(csv_dir, previous=previous)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def import_indexing(csv_dir, out_path=None) -> Path:
    csv_dir = Path(csv_dir)
    out = Path(out_path or INDEXING_OUT)
    data = build_indexing(csv_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="seo_engine.import_gsc", description=__doc__)
    ap.add_argument("csv_dir", help="directory containing the GSC CSV export(s)")
    ap.add_argument("--out", default=None,
                    help=f"performance output path (default: {GSC_EXPORT_PATH})")
    ap.add_argument("--indexing-out", default=None,
                    help=f"indexing output path (default: {INDEXING_OUT})")
    args = ap.parse_args(argv)

    csv_dir = Path(args.csv_dir)
    wrote_any = False

    if (csv_dir / REQUIRED).exists():
        out = import_export(csv_dir, args.out)
        data = json.loads(out.read_text(encoding="utf-8"))
        n_rows = len(data.get("rows") or [])
        n_queries = len(data.get("queries") or [])
        clicks = sum(r.get("clicks", 0) for r in data.get("rows") or [])
        imps = sum(r.get("impressions", 0) for r in data.get("rows") or [])
        print(f"wrote {out} — {n_rows} page rows ({clicks} clicks, {imps} impressions), "
              f"{n_queries} query rows preserved")
        wrote_any = True

    try:
        out = import_indexing(csv_dir, args.indexing_out)
    except FileNotFoundError:
        out = None
    if out is not None:
        data = json.loads(out.read_text(encoding="utf-8"))
        latest = next((d for d in reversed(data.get("daily") or [])
                       if d.get("indexed") is not None), None)
        summary = ""
        if latest:
            summary = (f" — latest {latest['date']}: {latest['indexed']} indexed / "
                       f"{latest['not_indexed']} not indexed")
        print(f"wrote {out} — {len(data.get('issues') or [])} critical issue rows"
              f"{summary}")
        wrote_any = True

    if not wrote_any:
        print(f"no recognised GSC CSVs in {csv_dir}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
