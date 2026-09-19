#!/usr/bin/env python3
"""CLI for the Gridiron SEO Engine.

Examples::

    python3 -m seo_engine audit
    python3 -m seo_engine decide
    python3 -m seo_engine apply --dry-run
    python3 -m seo_engine apply --commit          # write overrides.json
    python3 -m seo_engine apply --commit --with-pr # also write PR proposals
    python3 -m seo_engine verify
    python3 -m seo_engine opportunities
    python3 -m seo_engine run                     # audit→decide→apply(dry)→report
    python3 -m seo_engine run --commit            # full AUTO loop

Default is always dry-run / report-only. Nothing touches production HTML.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .apply import apply_decisions
from .audit import run_audit
from .config import (
    AUDIT_PATH,
    DECISIONS_PATH,
    MODE_AUTO,
    MODE_HUMAN,
    MODE_PR,
    OVERRIDES_PATH,
    ensure_seo_dirs,
    write_json,
)
from .content import scan_opportunities
from .decide import decide
from .verify import record_verification, verify_overrides


def _print_json(payload) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _print_audit_summary(report: dict) -> None:
    print(f"SEO audit @ {report['generated_at']}")
    print(f"  pages: {report['page_count']}  indexable: {report['indexable_count']}")
    print(f"  gsc rows: {report['gsc_rows']}  gsc pages: {report['gsc_pages']}")
    print(f"  findings: {report['finding_count']}")
    if report.get("by_severity"):
        sev = report["by_severity"]
        print(f"  severity: high={sev.get('high', 0)}  "
              f"medium={sev.get('medium', 0)}  low={sev.get('low', 0)}")
    if report.get("by_type"):
        print("  by type:")
        for t, n in sorted(report["by_type"].items(), key=lambda kv: -kv[1]):
            print(f"    {t:28s} {n}")


def _print_decide_summary(report: dict) -> None:
    s = report.get("summary") or {}
    print(f"SEO decisions @ {report['generated_at']}")
    print(f"  actions: {report['action_count']}")
    print(f"  AUTO ready: {s.get(MODE_AUTO, 0)}  "
          f"PR: {s.get(MODE_PR, 0)}  "
          f"HUMAN: {s.get(MODE_HUMAN, 0)}  "
          f"observe: {s.get('observe', 0)}")
    top = (report.get("actions") or [])[:10]
    if top:
        print("  top actions:")
        for a in top:
            ch = ",".join(a.get("changes") or {}.keys()) or "—"
            print(f"    [{a['mode']:5s}] {a['score']:5.1f}  {a['type']:24s}  "
                  f"{a['path']}  ({ch})")


def cmd_audit(args: argparse.Namespace) -> int:
    report = run_audit(gsc_path=args.gsc)
    # Strip the heavy pages dump from the default saved artefact unless --full.
    saved = dict(report)
    if not args.full:
        saved.pop("pages", None)
    if args.save or args.json_out:
        ensure_seo_dirs()
        write_json(Path(args.json_out) if args.json_out else AUDIT_PATH, saved)
    if args.json:
        _print_json(saved if not args.full else report)
    else:
        _print_audit_summary(report)
        if args.save or args.json_out:
            print(f"  wrote {args.json_out or AUDIT_PATH}")
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    if args.audit:
        audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    elif AUDIT_PATH.is_file():
        audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    else:
        audit = run_audit()
        slim = dict(audit)
        slim.pop("pages", None)
        ensure_seo_dirs()
        write_json(AUDIT_PATH, slim)
    report = decide(audit)
    if args.save or args.json_out:
        ensure_seo_dirs()
        write_json(Path(args.json_out) if args.json_out else DECISIONS_PATH, report)
    if args.json:
        _print_json(report)
    else:
        _print_decide_summary(report)
        if args.save or args.json_out:
            print(f"  wrote {args.json_out or DECISIONS_PATH}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    if args.decisions:
        decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    elif DECISIONS_PATH.is_file():
        decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    else:
        # Build the chain on the fly.
        audit = run_audit()
        decisions = decide(audit)
        ensure_seo_dirs()
        slim = dict(audit)
        slim.pop("pages", None)
        write_json(AUDIT_PATH, slim)
        write_json(DECISIONS_PATH, decisions)

    modes = [MODE_AUTO]
    if args.with_pr:
        modes.append(MODE_PR)
    if args.with_human:
        modes.append(MODE_HUMAN)

    dry_run = not args.commit
    result = apply_decisions(decisions, dry_run=dry_run, modes=modes)
    if args.json:
        _print_json(result)
    else:
        print(f"SEO apply @ {result['generated_at']}  dry_run={result['dry_run']}")
        print(f"  AUTO changes: {result['auto_count']}")
        for row in result["auto"][:15]:
            fields = ", ".join(row["changes"].keys())
            print(f"    {row['path']}  [{fields}]")
        if result["auto_count"] > 15:
            print(f"    … +{result['auto_count'] - 15} more")
        if result["pr_count"]:
            print(f"  PR proposals: {result['pr_count']} actions")
            for row in result["pr"]:
                print(f"    {row.get('md') or '(dry-run)'}")
        if result["human_count"]:
            print(f"  HUMAN flags: {result['human_count']}")
        if not dry_run and result["auto_count"]:
            print(f"  overrides written → {OVERRIDES_PATH}")
            print("  next: python3 src/build.py   # materialise into site/")
            print("        python3 -m seo_engine verify")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    report = verify_overrides()
    if args.record:
        record_verification(report)
    if args.json:
        _print_json(report)
    else:
        print(f"SEO verify @ {report['generated_at']}")
        print(f"  overrides: {report['override_count']}  "
              f"pass={report['passed']}  fail={report['failed']}  "
              f"missing_file={report['missing_file']}")
        for row in report["results"]:
            if row["status"] != "pass" or args.verbose:
                print(f"    [{row['status']}] {row['path']}")
                for field, check in (row.get("checks") or {}).items():
                    mark = "ok" if check.get("ok") else "FAIL"
                    print(f"      {field}: {mark}")
    # Non-zero only on hard fails (not on missing_file — that just means
    # "rebuild not run yet", which is an expected state mid-loop).
    return 1 if report["failed"] else 0


def cmd_opportunities(args: argparse.Namespace) -> int:
    report = scan_opportunities()
    if args.json:
        _print_json(report)
    else:
        print(f"SEO opportunities @ {report['generated_at']}")
        print(f"  count: {report['opportunity_count']}  "
              f"catalogue: {report['catalogue_count']}  "
              f"guides: {report['guide_count']}")
        for opp in report["opportunities"]:
            print(f"  [{opp.get('priority', '?'):6s}] {opp.get('opportunity')}  "
                  f"→ {opp.get('path')}")
            if opp.get("emerging_language"):
                print(f"           lang: {', '.join(opp['emerging_language'][:3])}")
        print("  policy:")
        for note in report["policy_notes"]:
            print(f"    - {note}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Full loop: audit → decide → apply → (optional) verify."""
    print("== audit ==")
    audit = run_audit(gsc_path=args.gsc)
    slim = dict(audit)
    slim.pop("pages", None)
    ensure_seo_dirs()
    write_json(AUDIT_PATH, slim)
    _print_audit_summary(audit)

    print("\n== decide ==")
    decisions = decide(audit)
    write_json(DECISIONS_PATH, decisions)
    _print_decide_summary(decisions)

    print("\n== apply ==")
    modes = [MODE_AUTO]
    if args.with_pr:
        modes.append(MODE_PR)
    dry_run = not args.commit
    result = apply_decisions(decisions, dry_run=dry_run, modes=modes)
    print(f"  dry_run={result['dry_run']}  auto={result['auto_count']}  "
          f"pr={result['pr_count']}")
    if not dry_run and result["auto_count"]:
        print(f"  wrote {OVERRIDES_PATH}")
        print("  rebuild required before verify can pass:")
        print("    python3 src/build.py && python3 -m seo_engine verify")

    print("\n== opportunities ==")
    opps = scan_opportunities()
    print(f"  {opps['opportunity_count']} content opportunities (PR-only)")

    if args.commit and args.verify_after:
        print("\n== verify ==")
        v = verify_overrides()
        record_verification(v)
        print(f"  pass={v['passed']} fail={v['failed']} missing={v['missing_file']}")

    print("\nDone. Controlled autonomy: AUTO only touches data/seo/overrides.json.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seo_engine",
        description=f"Gridiron SEO Engine v{__version__} — controlled-autonomy SEO",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="Crawl site/ and emit findings")
    a.add_argument("--gsc", help="Path to GSC export JSON")
    a.add_argument("--save", action="store_true", help=f"Write {AUDIT_PATH}")
    a.add_argument("--json-out", help="Write report to this path")
    a.add_argument("--json", action="store_true", help="Print full JSON")
    a.add_argument("--full", action="store_true", help="Include per-page dump")
    a.set_defaults(func=cmd_audit)

    d = sub.add_parser("decide", help="Turn audit findings into ranked actions")
    d.add_argument("--audit", help="Path to audit JSON (default: last_audit.json)")
    d.add_argument("--save", action="store_true")
    d.add_argument("--json-out")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_decide)

    ap = sub.add_parser("apply", help="Apply AUTO actions (dry-run by default)")
    ap.add_argument("--decisions", help="Path to decisions JSON")
    ap.add_argument("--commit", action="store_true",
                    help="Actually write data/seo/overrides.json")
    ap.add_argument("--with-pr", action="store_true",
                    help="Also write PR proposal files")
    ap.add_argument("--with-human", action="store_true",
                    help="Also write HUMAN flag files")
    ap.add_argument("--json", action="store_true")
    ap.set_defaults(func=cmd_apply)

    v = sub.add_parser("verify", help="Confirm overrides landed in site/")
    v.add_argument("--record", action="store_true",
                   help="Append summary to learning_memory.json")
    v.add_argument("--verbose", action="store_true")
    v.add_argument("--json", action="store_true")
    v.set_defaults(func=cmd_verify)

    o = sub.add_parser("opportunities", help="Scan content/landing opportunities")
    o.add_argument("--json", action="store_true")
    o.set_defaults(func=cmd_opportunities)

    r = sub.add_parser("run", help="Full audit→decide→apply loop")
    r.add_argument("--gsc", help="Path to GSC export JSON")
    r.add_argument("--commit", action="store_true",
                   help="Write overrides (still never edits site/ directly)")
    r.add_argument("--with-pr", action="store_true")
    r.add_argument("--verify-after", action="store_true",
                   help="Run verify after commit (expects site/ already rebuilt)")
    r.set_defaults(func=cmd_run)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
