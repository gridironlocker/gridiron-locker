"""Permanent suppression list.

A contact that opts out, asks for no further contact, bounces repeatedly or
is clearly irrelevant is marked SUPPRESS. Future collection runs may still
*see* the account (it is public), but the engine records it with status
SUPPRESS immediately and it is never exported as contactable.

Storage: a CSV (spec: data/osint/suppression.csv — relocated to
marketing/osint/state/suppression.csv because the repository contract forbids
marketing code writing to data/) mirrored into the DB suppression table.
The CSV is the durable, human-readable record; the DB copy is the fast index.
"""
from __future__ import annotations

import csv
from pathlib import Path

from . import config, db
from .dedupe import normalize_username, registered_domain

CSV_FIELDS = ["key", "kind", "reason", "created_at"]
KINDS = ("email", "username", "domain", "url", "platform_id")


def _csv_path() -> Path:
    return config.suppression_csv_path()


def load_into_db(repo) -> int:
    """(Re)load the suppression CSV into the DB table. Returns row count."""
    path = _csv_path()
    repo.conn.execute("DELETE FROM suppression")
    if not path.exists():
        repo.conn.commit()
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("key"):
                repo.conn.execute(
                    "INSERT OR IGNORE INTO suppression (key, kind, reason, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        row["key"].strip().lower(),
                        (row.get("kind") or "").strip() or "email",
                        (row.get("reason") or "").strip(),
                        row.get("created_at") or db.utcnow(),
                    ),
                )
    repo.conn.commit()
    return repo.conn.execute("SELECT COUNT(*) FROM suppression").fetchone()[0]


def append(key: str, kind: str, reason: str = "") -> None:
    key = (key or "").strip().lower()
    if not key:
        raise ValueError("suppression key cannot be empty")
    if kind not in KINDS:
        raise ValueError(f"unknown suppression kind {kind!r}; expected one of {KINDS}")
    path = _csv_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            existing = {row.get("key", "").strip().lower() for row in csv.DictReader(handle)}
    if key in existing:
        return
    is_new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerow(
            {"key": key, "kind": kind, "reason": reason, "created_at": db.utcnow()}
        )


def keys_for_prospect(prospect: dict) -> set[str]:
    """Every suppression key a prospect would match against."""
    keys: set[str] = set()
    email = (prospect.get("public_email") or "").lower().strip()
    if email:
        keys.add(email)
    username = normalize_username(prospect.get("username"))
    if username:
        keys.add(username)
        keys.add(f"{prospect.get('platform')}:{username}")
    domain = registered_domain(prospect.get("website") or "")
    if domain:
        keys.add(domain)
    url = (prospect.get("profile_url") or "").lower().strip()
    if url:
        keys.add(url)
    return keys


def add_from_prospect(repo, prospect: dict, reason: str) -> list[str]:
    """Suppress every key of a prospect (used when a row is marked SUPPRESS)."""
    added = []
    for key in sorted(keys_for_prospect(prospect)):
        kind = (
            "email" if "@" in key
            else "domain" if "." in key and "/" not in key
            else "url" if key.startswith("http")
            else "username"
        )
        append(key, kind, reason)
        repo.conn.execute(
            "INSERT OR IGNORE INTO suppression (key, kind, reason, created_at) "
            "VALUES (?, ?, ?, ?)",
            (key, kind, reason, db.utcnow()),
        )
        added.append(key)
    repo.conn.commit()
    return added


def suppressed_keys(repo) -> set[str]:
    return {row["key"] for row in repo.conn.execute("SELECT key FROM suppression")}


def is_suppressed(repo, prospect: dict) -> bool:
    return bool(keys_for_prospect(prospect) & suppressed_keys(repo))


def list_all(repo) -> list[dict]:
    return [
        dict(row)
        for row in repo.conn.execute("SELECT * FROM suppression ORDER BY created_at")
    ]
