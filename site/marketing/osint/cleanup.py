"""Data-retention cleanup.

Removes prospects not seen for N days (default 180) while ALWAYS preserving:

* suppression records (permanent by design);
* rows in protected statuses (CONTACTED, INTERESTED, CUSTOMER, PARTNER,
  NOT_INTERESTED, SUPPRESS, ...) so history is never lost.

Dry-run by default; --apply performs the deletion.
"""
from __future__ import annotations

from . import db

DEFAULT_DAYS = 180


def cleanup(repo, days: int = DEFAULT_DAYS, apply: bool = False) -> dict:
    protected = [
        "SUPPRESS", "NOT_INTERESTED", "CUSTOMER", "PARTNER", "CONTACTED",
        "REPLIED", "INTERESTED", "BOUNCED",
    ]
    if apply:
        removed = repo.delete_stale(days, protected)
        return {"mode": "apply", "days": days, "removed": len(removed), "ids": removed}
    cutoff = db._iso_days_ago(days)
    placeholders = ", ".join("?" for _ in protected)
    row = repo.conn.execute(
        f"SELECT COUNT(*) FROM prospects WHERE last_seen_at < ? "
        f"AND status NOT IN ({placeholders})",
        [cutoff, *protected],
    ).fetchone()
    return {"mode": "dry-run", "days": days, "would_remove": row[0]}
