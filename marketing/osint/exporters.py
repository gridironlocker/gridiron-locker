"""CSV export — the manual-outreach handoff.

Two files per export date (spec: EXPORT):

* gridiron_prospects_YYYY-MM-DD.csv        — everything not suppressed
* high_priority_contacts_YYYY-MM-DD.csv    — configurable high-bar filter

Safety guards:

* refuses to write anywhere under site/ or marketing/social/ (prospect data
  must never reach the deployed website);
* excluded statuses (default SUPPRESS, NOT_INTERESTED) never leave the DB.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from . import config

COLUMNS = [
    "name", "platform", "username", "profile_url", "team", "prospect_type",
    "public_email", "website", "followers", "relevance_score",
    "commercial_score", "confidence_score", "reason", "discovered_at",
    "last_verified_at", "status",
    # evidence/QC columns (spec: QUALITY CONTROL — every row traceable)
    "priority", "contact_source", "contact_source_url", "source_url",
    "email_verified", "email_category", "teams", "id",
]

FORBIDDEN_PREFIXES = ("site/", "marketing/social/", "ops/")


def _row(prospect: dict) -> dict:
    return {
        "name": prospect.get("display_name") or "",
        "platform": prospect.get("platform") or "",
        "username": prospect.get("username") or "",
        "profile_url": prospect.get("profile_url") or "",
        "team": prospect.get("team") or "",
        "prospect_type": prospect.get("prospect_type") or "",
        "public_email": prospect.get("public_email") or "",
        "website": prospect.get("website") or "",
        "followers": prospect.get("followers") if prospect.get("followers") is not None else "",
        "relevance_score": prospect.get("relevance_score") if prospect.get("relevance_score") is not None else "",
        "commercial_score": prospect.get("commercial_score") if prospect.get("commercial_score") is not None else "",
        "confidence_score": prospect.get("confidence_score") if prospect.get("confidence_score") is not None else "",
        "reason": prospect.get("score_reason") or "",
        "discovered_at": prospect.get("discovered_at") or "",
        "last_verified_at": prospect.get("last_verified_at") or "",
        "status": prospect.get("status") or "",
        "priority": prospect.get("priority") or "",
        "contact_source": prospect.get("contact_source") or "",
        "contact_source_url": prospect.get("contact_source_url") or "",
        "source_url": prospect.get("source_url") or "",
        "email_verified": prospect.get("email_verified") or "",
        "email_category": prospect.get("email_category") or "",
        "teams": ",".join(prospect.get("teams") or []),
        "id": prospect.get("id"),
    }


def _safe_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    repo_root = config.ROOT.resolve()
    try:
        relative = str(resolved.relative_to(repo_root))
    except ValueError:
        return resolved  # outside the repo entirely (tests, CI temp dirs)
    relative += "/"
    for prefix in FORBIDDEN_PREFIXES:
        if relative.startswith(prefix):
            raise ValueError(
                f"refusing to export prospect data to {path} — it is inside the "
                f"deployed/generated website tree ({prefix}...)"
            )
    return resolved


def write_csv(prospects: list[dict], path: Path) -> Path:
    path = _safe_path(Path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for prospect in prospects:
            writer.writerow(_row(prospect))
    return path


def export_all(
    repo,
    out_dir: Path | None = None,
    min_score: int = 0,
    team: str | None = None,
    require_email: bool = False,
    exclude_statuses: list[str] | None = None,
    today: str | None = None,
) -> dict[str, Path]:
    exclude = exclude_statuses or ["SUPPRESS", "NOT_INTERESTED"]
    out_dir = Path(out_dir) if out_dir else config.exports_dir()
    today = today or dt.date.today().isoformat()

    main = repo.list_prospects(
        min_score=min_score, team=team, exclude_statuses=exclude
    )
    main_path = write_csv(main, out_dir / f"gridiron_prospects_{today}.csv")

    high = [
        p for p in main
        if (p.get("relevance_score") or 0) >= 75 and p.get("public_email")
    ]
    high_path = write_csv(high, out_dir / f"high_priority_contacts_{today}.csv")
    return {
        "main": main_path,
        "main_count": len(main),
        "high_priority": high_path,
        "high_priority_count": len(high),
    }
