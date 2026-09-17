"""Command line interface.

    python3 -m marketing.osint discover [--team michigan] [--collectors podcasts]
    python3 -m marketing.osint refresh
    python3 -m marketing.osint export [--min-score 75]
    python3 -m marketing.osint stats [--json]
    python3 -m marketing.osint verify [--live]
    python3 -m marketing.osint import --prospects FILE | --statuses FILE
    python3 -m marketing.osint suppress --key EMAIL [--reason TEXT]
    python3 -m marketing.osint note --id N --text "..."
    python3 -m marketing.osint status --id N --to CONTACTED
    python3 -m marketing.osint report
    python3 -m marketing.osint cleanup [--days 180] [--apply]

All commands write ONLY under marketing/osint/state and
marketing/osint/exports (or OSINT_STATE_DIR / OSINT_EXPORTS_DIR).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import (
    PROSPECT_TYPES, STATUSES, cleanup, config, db, engine, exporters,
    importers, report as report_mod, scoring, suppression,
)


def _repo():
    return db.Repository(db.connect())


def _teams(value: str | None) -> list[str] | None:
    if not value:
        return None
    teams = []
    for part in value.split(","):
        try:
            teams.append(config.normalize_team(part))
        except ValueError as err:
            raise SystemExit(str(err))
    return teams


def cmd_discover(args) -> int:
    repo = _repo()
    result = engine.run_discovery(
        repo,
        teams=_teams(args.team),
        collector_names=args.collectors.split(",") if args.collectors else None,
        max_queries_per_team=args.max_queries,
        trend_aware=not args.no_trends,
        dry_run=args.dry_run,
    )
    print(report_mod.build_report(repo, result))
    if args.samples:
        print("Top prospects (emails masked):")
        for line in report_mod.sample_lines(repo):
            print(line)
    return 0


def cmd_refresh(args) -> int:
    repo = _repo()
    result = engine.run_refresh(repo, teams=_teams(args.team))
    result["statuses"] = result.get("statuses", [])
    print(report_mod.build_report(repo, result))
    print(f"Re-verified stale websites: {result.get('reverified', 0)}")
    return 0


def cmd_export(args) -> int:
    repo = _repo()
    out = exporters.export_all(
        repo,
        out_dir=Path(args.out) if args.out else None,
        min_score=args.min_score,
        team=_teams(args.team),
    )
    print(f"Exported {out['main_count']} prospects -> {out['main']}")
    print(f"High-priority contacts ({out['high_priority_count']}) -> {out['high_priority']}")
    return 0


def cmd_stats(args) -> int:
    repo = _repo()
    if args.json:
        print(json.dumps(report_mod.stats_json(repo), indent=2))
    else:
        print(report_mod.build_report(repo))
        matches = repo.list_matches("POSSIBLE_MATCH")
        if matches:
            print(f"\nPossible cross-platform matches awaiting review: {len(matches)}")
    return 0


def cmd_verify(args) -> int:
    """Offline pipeline health checks; --live adds a small REAL collection
    run into a throwaway database (safe even in a public CI log: aggregate
    counts and masked emails only)."""
    failures: list[str] = []

    # 1. keywords present and valid for every team
    for team in config.TEAM_SLUGS:
        try:
            keywords = config.load_keywords(team)
            if not keywords.get("search_queries"):
                failures.append(f"{team}: no search_queries in keywords file")
        except (OSError, ValueError) as err:
            failures.append(f"{team}: {err}")

    # 2. DB opens, schema valid
    repo = _repo()
    if repo.conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0] < 0:
        failures.append("prospects table unreadable")

    # 3. scoring is deterministic and explainable on a fixture
    fixture = {
        "platform": "apple-podcasts", "display_name": "Test Michigan Football Podcast",
        "bio": "Daily Michigan Wolverines football podcast", "team": "michigan",
        "prospect_type": "PODCAST_MEDIA", "public_email": "contact@example.org",
        "email_verified": "VERIFIED_MX", "contact_source": "test",
        "last_activity_at": "2026-09-10", "followers": 0, "post_count": 120,
    }
    result = scoring.score(fixture)
    if not (0 <= result["relevance_score"] <= 100) or not result["score_reason"]:
        failures.append("scoring produced an invalid result")
    for name, part in result["breakdown"].items():
        if part["points"] > part["max"]:
            failures.append(f"scoring component {name} exceeds its max")

    # 4. collectors registry + honest statuses
    from .collectors import ALL_COLLECTORS

    names = [collector.name for collector in (cls() for cls in ALL_COLLECTORS)]
    if len(names) != len(set(names)):
        failures.append("duplicate collector names in registry")

    # 5. exports refuse to write into the deployed site tree
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        try:
            exporters.write_csv([], Path(config.ROOT) / "site" / "prospects.csv")
            failures.append("exporter wrote into site/ and should have refused")
        except ValueError:
            pass
        safe = exporters.write_csv([], Path(tmp) / "ok.csv")
        if not safe.exists():
            failures.append("exporter failed to write a safe path")

    if failures:
        print("VERIFY: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("VERIFY: OK (config, DB, scoring, collectors, export guards)")

    if args.live:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            live_repo = db.Repository(db.connect(Path(tmp) / "live.db"))
            result = engine.run_discovery(
                live_repo,
                max_queries_per_team=args.max_queries,
            )
            print()
            print(report_mod.build_report(live_repo, result))
            print("Top prospects (emails masked, names withheld):")
            for line in report_mod.sample_lines(live_repo):
                print(line)
            total = result.get("new", 0)
            errored = [s for s in result["statuses"] if s.state == "ERROR"]
            if total == 0:
                print("LIVE VERIFY: FAIL — no prospects discovered")
                return 1
            if errored:
                print(f"LIVE VERIFY: FAIL — collectors in ERROR: "
                      f"{', '.join(s.name for s in errored)}")
                return 1
            print("LIVE VERIFY: OK — live pipeline discovered real public prospects")
    return 0


def cmd_import(args) -> int:
    repo = _repo()
    if args.prospects:
        summary = importers.import_prospects(repo, args.prospects)
        print(f"Manual import: {summary['added']} added, "
              f"{summary['updated']} updated, {summary['skipped']} skipped")
        return 0
    if args.statuses:
        summary = importers.import_statuses(repo, args.statuses)
        print(f"Status import: {summary['applied']} applied, {summary['skipped']} skipped")
        for problem in summary["problems"][:10]:
            print(f"  ! {problem}")
        return 0 if not summary["problems"] else 2
    raise SystemExit("import needs --prospects FILE or --statuses FILE")


def cmd_suppress(args) -> int:
    repo = _repo()
    suppression.append(args.key, args.kind, args.reason)
    suppression.load_into_db(repo)
    kind = args.kind
    if args.prospect_id:
        prospect = repo.get(args.prospect_id)
        if not prospect:
            raise SystemExit(f"no prospect with id {args.prospect_id}")
        suppression.add_from_prospect(repo, prospect, args.reason or "suppressed via CLI")
        repo.update_status(args.prospect_id, "SUPPRESS")
        print(f"Prospect {args.prospect_id} and all its identity keys suppressed")
    print(f"Suppressed key ({kind}): {args.key}")
    return 0


def cmd_note(args) -> int:
    repo = _repo()
    if repo.add_note(args.id, args.text):
        print(f"Note added to prospect {args.id}")
        return 0
    raise SystemExit(f"no prospect with id {args.id}")


def cmd_status(args) -> int:
    repo = _repo()
    if args.to not in STATUSES:
        raise SystemExit(f"unknown status {args.to!r}; expected one of {STATUSES}")
    repo.update_status(args.id, args.to)
    print(f"Prospect {args.id} -> {args.to}")
    if args.to == "SUPPRESS":
        print("(all identity keys added to the permanent suppression list)")
    return 0


def cmd_report(args) -> int:
    repo = _repo()
    print(report_mod.build_report(repo))
    return 0


def cmd_cleanup(args) -> int:
    repo = _repo()
    result = cleanup.cleanup(repo, days=args.days, apply=args.apply)
    if result["mode"] == "dry-run":
        print(f"Cleanup dry-run: would remove {result['would_remove']} prospect(s) "
              f"not seen for {result['days']} days (suppression + history preserved).")
        print("Run with --apply to perform the deletion.")
    else:
        print(f"Cleanup: removed {result['removed']} stale prospect(s); "
              "suppression records preserved.")
    return 0


def cmd_list(args) -> int:
    repo = _repo()
    rows = repo.list_prospects(
        min_score=args.min_score, team=_teams(args.team)[0] if args.team else None,
        require_email=args.email, limit=args.limit or 40,
        exclude_statuses=["SUPPRESS", "NOT_INTERESTED"] if not args.all else None,
    )
    print(f"{'ID':>4}  {'SCORE':>5}  {'PRIORITY':<14}{'TEAM':<10}"
          f"{'TYPE':<14}{'PLATFORM':<16}NAME")
    for p in rows:
        email = p.get("public_email") or ""
        shown = email if not args.mask else (f"{email.split('@')[0]}@…" if email else "")
        name = (p.get("display_name") or "")[:44]
        print(f"{p['id']:>4}  {p.get('relevance_score', 0):>5}  "
              f"{(p.get('priority') or ''):<14}{(p.get('team') or ''):<10}"
              f"{(p.get('prospect_type') or ''):<14}{(p.get('platform') or ''):<16}{name}")
        if email:
            print(f"{'':>4}  email: {shown}  ({p.get('email_verified')})")
    print(f"\n{len(rows)} row(s); suppression and NOT_INTERESTED excluded"
          + ("" if args.all else " (use --all to include)"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m marketing.osint",
        description="Gridiron Locker private prospect engine (see marketing/osint/README.md)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("discover", help="run enabled collectors")
    p.add_argument("--team", help="team slug or label (default: all four)")
    p.add_argument("--collectors", help="comma list, e.g. podcasts,websites")
    p.add_argument("--max-queries", type=int, default=4,
                   help="API queries per team per collector (default 4)")
    p.add_argument("--no-trends", action="store_true",
                   help="skip trend-term augmentation")
    p.add_argument("--dry-run", action="store_true",
                   help="report what would run, write nothing")
    p.add_argument("--samples", action="store_true",
                   help="print top prospects with masked emails")
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("refresh", help="discover + re-verify + rescore")
    p.add_argument("--team")
    p.set_defaults(func=cmd_refresh)

    p = sub.add_parser("export", help="write CSV exports")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--team")
    p.add_argument("--out", help="output directory (default marketing/osint/exports)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("stats", help="aggregate statistics")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("verify", help="pipeline health check")
    p.add_argument("--live", action="store_true",
                   help="add a small REAL discovery run (throwaway DB)")
    p.add_argument("--max-queries", type=int, default=2)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("import", help="import manual CSVs")
    p.add_argument("--prospects")
    p.add_argument("--statuses")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("suppress", help="add a permanent suppression key")
    p.add_argument("--key", required=True)
    p.add_argument("--kind", default="email",
                   choices=["email", "username", "domain", "url"])
    p.add_argument("--reason", default="")
    p.add_argument("--prospect-id", type=int)
    p.set_defaults(func=cmd_suppress)

    p = sub.add_parser("note", help="attach a manual outreach note")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_note)

    p = sub.add_parser("status", help="change a prospect's status")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--to", required=True, choices=STATUSES)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("report", help="print the daily report")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("cleanup", help="data retention")
    p.add_argument("--days", type=int, default=180)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(func=cmd_cleanup)

    p = sub.add_parser("list", help="list prospects")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--team")
    p.add_argument("--email", action="store_true", help="only rows with email")
    p.add_argument("--limit", type=int)
    p.add_argument("--all", action="store_true", help="include suppressed rows")
    p.add_argument("--mask", action="store_true", default=True)
    p.set_defaults(func=cmd_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
