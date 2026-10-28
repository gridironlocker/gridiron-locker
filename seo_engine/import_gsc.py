"""Import a Google Search Console Performance export (CSV bundle) into
``data/seo/gsc_export.json``.

Faithful import only: numbers are copied from the export verbatim (percent
strings become decimal fractions). Nothing is invented, estimated, or
aggregated across tables.

Expected files inside the export directory (Search Console → Performance →
Export → CSV):

    Pages.csv                (required — becomes rows[])
    Queries.csv              (optional — kept under ``queries``)
    Chart.csv                (optional — daily series, kept under ``daily``)
    Devices.csv              (optional — kept under ``devices``)
    Countries.csv            (optional — kept under ``countries``)
    Search appearance.csv    (optional — kept under ``search_appearance``)
    Filters.csv              (optional — kept under ``filters``)

``rows[]`` carries the row contract consumed by ``seo_engine.audit`` and
``seo_engine.content`` (page + optional query). This export format does not
attribute queries to pages, so ``rows[]`` is page-level and the query table
is preserved separately — never guessed onto a page.

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

from .config import GSC_EXPORT_PATH

REQUIRED = "Pages.csv"

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


def number(value: str) -> float:
    """GSC decimal string ('39.68') → float."""
    v = (value or "").strip().replace(",", "")
    return float(v) if v else 0.0


def load_csv(path: Path) -> List[Dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _metric_rows(raw: List[Dict]) -> List[Dict]:
    """Convert one GSC metric table into JSON rows (label key + 4 metrics).

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


def build_export(csv_dir: Path) -> dict:
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
        if path.exists():
            data[key] = _metric_rows(load_csv(path))

    filters_path = csv_dir / "Filters.csv"
    if filters_path.exists():
        data["filters"] = [
            {"filter": (r.get("Filter") or "").strip(), "value": (r.get("Value") or "").strip()}
            for r in load_csv(filters_path)
        ]

    return data


def import_export(csv_dir, out_path=None) -> Path:
    csv_dir = Path(csv_dir)
    out = Path(out_path or GSC_EXPORT_PATH)
    data = build_export(csv_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="seo_engine.import_gsc", description=__doc__)
    ap.add_argument("csv_dir", help="directory containing the GSC CSV export")
    ap.add_argument("--out", default=None, help=f"output path (default: {GSC_EXPORT_PATH})")
    args = ap.parse_args(argv)

    out = import_export(args.csv_dir, args.out)
    data = json.loads(out.read_text(encoding="utf-8"))
    n_rows = len(data.get("rows") or [])
    n_queries = len(data.get("queries") or [])
    clicks = sum(r.get("clicks", 0) for r in data.get("rows") or [])
    imps = sum(r.get("impressions", 0) for r in data.get("rows") or [])
    print(f"wrote {out} — {n_rows} page rows ({clicks} clicks, {imps} impressions), "
          f"{n_queries} query rows preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
