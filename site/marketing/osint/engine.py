"""Discovery pipeline: collectors -> validation -> dedupe -> suppression ->
scoring -> SQLite.

One run:

1. loads keywords (+ trend terms from the repo's existing trend system,
   read-only) and the suppression list;
2. runs every enabled collector, honestly recording each status;
3. enriches website-bearing prospects with public contact data (robots-
   checked, bounded);
4. validates public emails honestly (no test emails, no SMTP);
5. suppresses known opt-outs (status SUPPRESS, never exported as contactable);
6. scores every prospect and upserts it with full freshness tracking.

The pipeline NEVER sends email and NEVER writes outside its state/exports
directories (env-overridable for tests and CI).
"""
from __future__ import annotations

from . import config, db, dedupe, emails, scoring, suppression
from .collectors import enabled_collectors
from .collectors.base import DiscoveryContext
from .collectors.websites import enrich_website
from .http import Fetcher

#: Statuses whose rows survive cleanup — suppression records are permanent.
PROTECTED_STATUSES = [
    "SUPPRESS", "NOT_INTERESTED", "CUSTOMER", "PARTNER", "CONTACTED",
    "REPLIED", "INTERESTED", "BOUNCED",
]

#: Per-collector hard cap on prospects accepted in one run (junk guard).
MAX_RECORDS_PER_COLLECTOR = 60


def run_discovery(
    repo,
    fetcher: Fetcher | None = None,
    teams: list[str] | None = None,
    collector_names: list[str] | None = None,
    max_queries_per_team: int = 4,
    trend_aware: bool = True,
    dry_run: bool = False,
    enrich: bool = True,
) -> dict:
    fetcher = fetcher or Fetcher()
    teams = teams or config.TEAM_SLUGS
    keywords = config.load_all_keywords()
    trend_terms = config.load_trend_terms() if trend_aware else {}
    ctx = DiscoveryContext(
        fetcher=fetcher,
        keywords=keywords,
        teams=teams,
        trend_terms=trend_terms,
        max_queries_per_team=max_queries_per_team,
        dry_run=dry_run,
    )

    suppression.load_into_db(repo)
    suppressed_keys = suppression.suppressed_keys(repo)
    statuses = []
    counts = {"new": 0, "updated": 0, "unchanged": 0, "suppressed_hits": 0}
    run_id = repo.start_run("discover" if not dry_run else "dry-run")

    for collector in enabled_collectors(collector_names):
        try:
            records, status = collector.discover(ctx)
        except Exception as err:  # noqa: BLE001 — a broken collector must
            # never take the whole run down, but it IS reported honestly.
            from .collectors.base import CollectorStatus

            records = []
            status = CollectorStatus(
                name=collector.name, state="ERROR", detail=f"{type(err).__name__}: {err}"
            )
        statuses.append(status)
        if dry_run:
            continue

        accepted = records[:MAX_RECORDS_PER_COLLECTOR]
        for record in accepted:
            _store(repo, record, suppressed_keys, counts, enrich, fetcher, ctx)

    repo.finish_run(run_id, new=counts["new"], updated=counts["updated"],
                    unchanged=counts["unchanged"],
                    suppressed_hits=counts["suppressed_hits"],
                    collectors=[s.line() for s in statuses])
    return {"statuses": statuses, **counts}


def _store(repo, record: dict, suppressed_keys: set[str], counts: dict,
           enrich: bool, fetcher, ctx) -> None:
    # shared website enrichment for any prospect with a website
    if enrich and not ctx.dry_run and (record.get("website") or "").startswith("http"):
        try:
            updates = enrich_website(fetcher, record)
            record.update({k: v for k, v in updates.items() if v or k == "website"})
        except Exception:  # noqa: BLE001 — enrichment failures degrade gracefully
            pass

    # honest email validation (syntax + DNS, never sends anything)
    if record.get("public_email"):
        check = emails.validate(record["public_email"], dns=True)
        record["email_verified"] = check["verdict"]
        record["email_verification_method"] = check["method"]
        if check["verdict"] in ("INVALID_SYNTAX", "INVALID_DOMAIN"):
            record.pop("public_email", None)
            record.pop("email_category", None)
            record["email_verified"] = None
    else:
        record["email_verified"] = record.get("email_verified")

    # suppression: opt-outs are recorded but never contactable
    keys = suppression.keys_for_prospect(record)
    if keys & suppressed_keys:
        record["status"] = "SUPPRESS"
        record["notes"] = record.get("notes") or "matched suppression list"

    scored = scoring.score(record, keywords=ctx.keywords)
    record.update({
        "relevance_score": scored["relevance_score"],
        "commercial_score": scored["commercial_score"],
        "confidence_score": scored["confidence_score"],
        "score_breakdown": scored["breakdown"],
        "score_reason": scored["score_reason"],
        "priority": scored["priority"],
        "teams": scored["teams"] or record.get("teams") or [],
    })
    # the keyword-driven team assignment (from the prospect's own public
    # text) wins over the query that happened to find it
    if record["teams"]:
        record["team"] = record["teams"][0]

    result = repo.upsert_prospect(record)
    counts_key = {
        "NEW": "new", "UPDATED": "updated", "UNCHANGED": "unchanged",
    }.get(result["outcome"])
    if counts_key:
        counts[counts_key] += 1
    if record.get("status") == "SUPPRESS":
        # upsert deliberately never overwrites status, so a rediscovered
        # opt-out has to be forced — suppression is permanent (spec).
        repo.update_status(result["id"], "SUPPRESS")
        counts["suppressed_hits"] += 1
    if result["outcome"] == "NEW":
        dedupe.detect_links(repo, record, result["id"])


def run_refresh(repo, fetcher: Fetcher | None = None, teams: list[str] | None = None,
                stale_days: int = 14) -> dict:
    """Re-run discovery AND re-verify existing prospects that have a website
    (bounded), then rescore everything. Existing status/notes are preserved."""
    result = run_discovery(repo, fetcher=fetcher, teams=teams)
    fetcher = fetcher or Fetcher()
    repo.rescore_all(scoring)
    verified = 0
    stale = repo.conn.execute(
        "SELECT * FROM prospects WHERE website IS NOT NULL AND website != '' "
        "AND (last_verified_at IS NULL OR last_verified_at < ?) LIMIT 40",
        (db._iso_days_ago(stale_days),),
    ).fetchall()
    for row in stale:
        prospect = db.row_to_prospect(row)
        updates = enrich_website(fetcher, prospect)
        if updates:
            for key, value in updates.items():
                if value:
                    prospect[key] = value
            scored = scoring.score(prospect)
            prospect.update({
                "relevance_score": scored["relevance_score"],
                "commercial_score": scored["commercial_score"],
                "confidence_score": scored["confidence_score"],
                "score_breakdown": scored["breakdown"],
                "score_reason": scored["score_reason"],
                "priority": scored["priority"],
            })
            repo.upsert_prospect(prospect)
        repo.conn.execute(
            "UPDATE prospects SET last_verified_at = ? WHERE id = ?",
            (db.utcnow(), prospect["id"]),
        )
        repo.conn.commit()
        verified += 1
    result["reverified"] = verified
    return result
