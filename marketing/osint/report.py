"""Aggregate reporting — the daily OSINT report.

Reports are aggregate by design: counts, splits and collector status. Email
addresses are ALWAYS masked, so a report is safe to paste into CI logs of a
public repository (which is exactly where the verification workflow runs).
"""
from __future__ import annotations

from . import config
from .emails import mask

LINE = "=" * 64


def build_report(repo, run_result: dict | None = None) -> str:
    run_result = run_result or {}
    statuses = run_result.get("statuses") or []
    today_count = repo.conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE date(discovered_at) = date('now')"
    ).fetchone()[0]

    by_team = {
        row["team"] or "(none)": row["n"]
        for row in repo.conn.execute(
            "SELECT team, COUNT(*) AS n FROM prospects GROUP BY team ORDER BY n DESC"
        )
    }
    by_type = {
        row["prospect_type"] or "(none)": row["n"]
        for row in repo.conn.execute(
            "SELECT prospect_type, COUNT(*) AS n FROM prospects "
            "GROUP BY prospect_type ORDER BY n DESC"
        )
    }
    with_email = repo.conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE public_email IS NOT NULL AND public_email != ''"
    ).fetchone()[0]
    verified_email = repo.conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE email_verified LIKE 'VERIFIED%'"
    ).fetchone()[0]
    by_priority = {
        row["priority"] or "(none)": row["n"]
        for row in repo.conn.execute(
            "SELECT priority, COUNT(*) AS n FROM prospects GROUP BY priority"
        )
    }
    suppressed = repo.conn.execute("SELECT COUNT(*) FROM suppression").fetchone()[0]

    lines = [
        LINE,
        "GRIDIRON LOCKER OSINT REPORT",
        LINE,
        f"New prospects (this run): {run_result.get('new', 0)}",
        f"Updated: {run_result.get('updated', 0)}  "
        f"Unchanged: {run_result.get('unchanged', 0)}  "
        f"Suppressed hits: {run_result.get('suppressed_hits', 0)}",
        f"Discovered today: {today_count}",
        "",
        "By team:",
    ]
    for team in config.TEAM_SLUGS:
        lines.append(f"  {config.TEAM_LABELS[team]}: {by_team.get(team, 0)}")
    for extra, count in by_team.items():
        if extra not in ("michigan", "browns", "packers", "cowboys", "(none)"):
            lines.append(f"  {extra}: {count}")

    lines += ["", "By prospect type:"]
    lines += [f"  {ptype}: {count}" for ptype, count in by_type.items()]

    lines += [
        "",
        f"Public business emails: {with_email} "
        f"(passing honest validation: {verified_email})",
        f"Suppression list entries: {suppressed}",
        "",
        "Priority bands:",
    ]
    lines += [f"  {band}: {count}" for band, count in by_priority.items()]

    if statuses:
        lines += ["", "Collector status (failures are never hidden):"]
        lines += [f"  {status.line()}  [found={status.found} errors={status.errors}]"
                  for status in statuses]

    lines += ["", LINE]
    return "\n".join(lines)


def sample_lines(repo, limit: int = 5, min_score: int = 0) -> list[str]:
    """A few top prospects with emails masked — safe for public CI logs."""
    rows = repo.list_prospects(min_score=min_score, limit=limit)
    out = []
    for prospect in rows:
        email = mask(prospect["public_email"]) if prospect.get("public_email") else "-"
        out.append(
            f"  [{prospect['priority']}] {prospect.get('prospect_type','?')} "
            f"score={prospect.get('relevance_score', 0)} team={prospect.get('team','?')} "
            f"email={email}"
        )
    return out


def stats_json(repo, run_result: dict | None = None) -> dict:
    run_result = run_result or {}
    payload = {
        "new": run_result.get("new", 0),
        "updated": run_result.get("updated", 0),
        "unchanged": run_result.get("unchanged", 0),
        "suppressed_hits": run_result.get("suppressed_hits", 0),
        "total": repo.conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0],
        "with_public_email": repo.conn.execute(
            "SELECT COUNT(*) FROM prospects WHERE public_email IS NOT NULL AND public_email != ''"
        ).fetchone()[0],
        "verified_email": repo.conn.execute(
            "SELECT COUNT(*) FROM prospects WHERE email_verified LIKE 'VERIFIED%'"
        ).fetchone()[0],
        "by_team": {},
        "by_type": {},
        "by_priority": {},
        "collectors": [s.line() for s in run_result.get("statuses", [])],
    }
    for row in repo.conn.execute(
        "SELECT team, COUNT(*) n FROM prospects GROUP BY team"
    ):
        payload["by_team"][row["team"]] = row["n"]
    for row in repo.conn.execute(
        "SELECT prospect_type, COUNT(*) n FROM prospects GROUP BY prospect_type"
    ):
        payload["by_type"][row["prospect_type"]] = row["n"]
    for row in repo.conn.execute(
        "SELECT priority, COUNT(*) n FROM prospects GROUP BY priority"
    ):
        payload["by_priority"][row["priority"]] = row["n"]
    return payload
