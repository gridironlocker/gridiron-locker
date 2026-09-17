"""CSV import — the two directions of the manual workflow.

1. --prospects: add public data the owner collected by hand while browsing
   normally (the legitimate path for Instagram/TikTok/X/Pinterest, whose
   platforms cannot be automated). Manual rows are marked source=manual-import
   and their contact info is treated as manually verified.

2. --statuses: update outreach statuses after the owner sends email by hand
   (email_sent, reply_received, interested, ...). The engine itself NEVER
   sends anything.
"""
from __future__ import annotations

import csv

from . import emails, scoring, suppression

#: Friendly status aliases the owner may type in the spreadsheet.
STATUS_ALIASES = {
    "email_sent": "CONTACTED",
    "sent": "CONTACTED",
    "reply_received": "REPLIED",
    "replied": "REPLIED",
    "interested": "INTERESTED",
    "customer": "CUSTOMER",
    "partner": "PARTNER",
    "not_interested": "NOT_INTERESTED",
    "unsubscribe": "SUPPRESS",      # opt-outs are permanent (spec: SUPPRESSION)
    "opt_out": "SUPPRESS",
    "suppressed": "SUPPRESS",
    "suppress": "SUPPRESS",
    "bounced": "BOUNCED",
    "new": "NEW",
    "review": "REVIEW",
    "qualified": "QUALIFIED",
}

REQUIRED_PROSPECT_FIELDS = ["name"]
OPTIONAL_PROSPECT_FIELDS = [
    "platform", "username", "profile_url", "website", "team", "prospect_type",
    "public_email", "contact_source_url", "followers", "notes", "bio",
]


def import_prospects(repo, path) -> dict:
    """Manual prospect additions from CSV. Returns counts."""
    added = updated = skipped = 0
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            name = row.get("name", "")
            if not name:
                skipped += 1
                continue
            platform = (row.get("platform") or "manual").lower()
            key = row.get("username") or row.get("profile_url") or row.get("website") or name
            record = {
                "platform": platform,
                "platform_user_id": f"manual:{key.lower()}",
                "username": row.get("username") or None,
                "display_name": name,
                "profile_url": row.get("profile_url") or None,
                "website": row.get("website") or None,
                "team": row.get("team") or None,
                "teams": [row["team"]] if row.get("team") else [],
                "prospect_type": (row.get("prospect_type") or "OTHER").upper(),
                "bio": row.get("bio") or None,
                "source_url": "manual-import",
                "notes": row.get("notes") or "",
                "status": "REVIEW",
            }
            email = row.get("public_email", "")
            if email:
                address = emails.clean_address(email)
                if address:
                    check = emails.validate(address, dns=True)
                    record["public_email"] = address
                    record["email_category"] = "MANUAL"
                    record["contact_source"] = "manual entry"
                    record["contact_source_url"] = row.get("contact_source_url") or None
                    record["email_verified"] = check["verdict"]
                    record["email_verification_method"] = check["method"]
            followers = row.get("followers", "")
            if followers.isdigit():
                record["followers"] = int(followers)
            scored = scoring.score(record)
            record.update({
                "relevance_score": scored["relevance_score"],
                "commercial_score": scored["commercial_score"],
                "confidence_score": scored["confidence_score"],
                "score_breakdown": scored["breakdown"],
                "score_reason": scored["score_reason"],
                "priority": scored["priority"],
            })
            outcome = repo.upsert_prospect(record)["outcome"]
            if outcome == "NEW":
                added += 1
            else:
                updated += 1
    return {"added": added, "updated": updated, "skipped": skipped}


def import_statuses(repo, path) -> dict:
    """Apply outreach outcome CSV (id or email/username keyed)."""
    applied = skipped = 0
    problems: list[str] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            raw_status = row.get("status") or row.get("new_status") or ""
            status = STATUS_ALIASES.get(raw_status.lower(), raw_status.upper())
            from . import STATUSES

            if status not in STATUSES:
                problems.append(f"unknown status {raw_status!r} for row {row}")
                skipped += 1
                continue
            prospect = None
            if row.get("id", "").isdigit():
                prospect = repo.get(int(row["id"]))
            if prospect is None and row.get("public_email"):
                matches = repo.find_by_email(row["public_email"])
                prospect = matches[0] if matches else None
            if prospect is None and row.get("username"):
                found = repo.conn.execute(
                    "SELECT * FROM prospects WHERE lower(username) = ? LIMIT 1",
                    (row["username"].lower().lstrip("@"),),
                ).fetchone()
                prospect = dict(found) if found else None
            if prospect is None:
                problems.append(f"no prospect matched row: {row}")
                skipped += 1
                continue
            repo.update_status(prospect["id"], status, row.get("note") or None)
            if status == "SUPPRESS":
                full = repo.get(prospect["id"])
                suppression.add_from_prospect(repo, full, "imported SUPPRESS status")
            applied += 1
    return {"applied": applied, "skipped": skipped, "problems": problems}
