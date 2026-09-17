"""SQLite persistence for the OSINT prospect engine.

Schema follows the engine spec's data model, extended with:

* evidence columns (source_url, contact_source_url) — every prospect must be
  traceable to where its information came from;
* first_seen_at / last_seen_at / last_verified_at freshness triple;
* an evidence_hash used to detect profile changes between runs so a
  prospect is never re-reported as "new" when nothing changed;
* separate suppression, cross-platform match and run-log tables.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    platform_user_id TEXT,
    username TEXT,
    display_name TEXT,
    profile_url TEXT,
    website TEXT,
    team TEXT,
    teams TEXT DEFAULT '[]',
    prospect_type TEXT,
    bio TEXT,
    public_email TEXT,
    email_category TEXT,
    contact_source TEXT,
    contact_source_url TEXT,
    email_verified TEXT,
    email_verification_method TEXT,
    location_if_public TEXT,
    followers INTEGER,
    following INTEGER,
    post_count INTEGER,
    engagement_estimate REAL,
    relevance_score INTEGER,
    commercial_score INTEGER,
    confidence_score INTEGER,
    score_breakdown TEXT,
    score_reason TEXT,
    priority TEXT,
    source_url TEXT,
    linked_profiles TEXT DEFAULT '[]',
    last_activity_at TEXT,
    first_seen_at TEXT,
    discovered_at TEXT,
    last_seen_at TEXT,
    last_verified_at TEXT,
    status TEXT NOT NULL DEFAULT 'NEW',
    notes TEXT DEFAULT '',
    evidence_hash TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_prospects_identity
    ON prospects(platform, platform_user_id);
CREATE INDEX IF NOT EXISTS idx_prospects_team ON prospects(team);
CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_prospects_email ON prospects(public_email);

CREATE TABLE IF NOT EXISTS suppression (
    key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    reason TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id_a INTEGER NOT NULL,
    prospect_id_b INTEGER NOT NULL,
    basis TEXT NOT NULL,
    confidence TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    mode TEXT,
    new INTEGER DEFAULT 0,
    updated INTEGER DEFAULT 0,
    unchanged INTEGER DEFAULT 0,
    suppressed_hits INTEGER DEFAULT 0,
    collectors TEXT DEFAULT '[]'
);
"""

#: Fields hashed for change detection (a change re-verifies + re-scores).
_EVIDENCE_FIELDS = (
    "display_name", "username", "bio", "website", "public_email",
    "followers", "post_count", "prospect_type", "team", "linked_profiles",
)

_PROSPECT_COLUMNS = [
    "platform", "platform_user_id", "username", "display_name",
    "profile_url", "website", "team", "teams", "prospect_type", "bio",
    "public_email", "email_category", "contact_source", "contact_source_url",
    "email_verified", "email_verification_method", "location_if_public",
    "followers", "following", "post_count", "engagement_estimate",
    "relevance_score", "commercial_score", "confidence_score",
    "score_breakdown", "score_reason", "priority", "source_url",
    "linked_profiles", "last_activity_at", "first_seen_at", "discovered_at",
    "last_seen_at", "last_verified_at", "status", "notes", "evidence_hash",
]


def utcnow() -> str:
    import datetime as _dt

    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def evidence_hash(record: dict) -> str:
    payload = {field: record.get(field) for field in _EVIDENCE_FIELDS}
    return hashlib.sha1(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = Path(path) if path else config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def row_to_prospect(row: sqlite3.Row) -> dict:
    prospect = {key: row[key] for key in row.keys()}
    for field in ("teams", "linked_profiles", "score_breakdown"):
        value = prospect.get(field)
        if isinstance(value, str) and value:
            try:
                prospect[field] = json.loads(value)
            except json.JSONDecodeError:
                prospect[field] = [] if field != "score_breakdown" else {}
        elif value is None:
            prospect[field] = [] if field != "score_breakdown" else {}
    return prospect


class Repository:
    """All database access goes through here (keeps SQL in one place)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # -- prospects --------------------------------------------------------
    def upsert_prospect(self, record: dict) -> dict:
        """Insert or merge one prospect. Returns
        {id, outcome} where outcome is NEW / UPDATED / UNCHANGED / SUPPRESSED.
        Status, notes and first_seen of an existing row are always preserved."""
        now = utcnow()
        record = {**record}
        record.setdefault("status", "NEW")
        record["evidence_hash"] = evidence_hash(record)
        record["teams"] = json.dumps(record.get("teams") or [])
        record["linked_profiles"] = json.dumps(record.get("linked_profiles") or [])
        record["score_breakdown"] = json.dumps(record.get("score_breakdown") or {})
        record.setdefault("last_seen_at", now)

        identity = (
            record.get("platform"),
            record.get("platform_user_id") or record.get("username") or "",
        )
        existing = self.find_by_identity(*identity)
        if existing:
            changed = existing["evidence_hash"] != record["evidence_hash"]
            updates = {
                key: record.get(key)
                for key in _PROSPECT_COLUMNS
                if key not in ("status", "notes", "first_seen_at", "discovered_at")
            }
            updates["last_seen_at"] = now
            updates["last_verified_at"] = now
            # never blank out data the old row had but the new one lacks
            for key in list(updates):
                if updates[key] in (None, "", []) and existing.get(key) not in (None, "", [], "{}", "[]"):
                    updates[key] = existing[key]
            # teams are merged (union) so a prospect found via two team
            # queries keeps both affiliations
            updates["teams"] = json.dumps(_merge_teams(existing, record))
            updates["evidence_hash"] = record["evidence_hash"] if changed else existing["evidence_hash"]
            # the three JSON columns must stay JSON strings even when the
            # value came from an existing (already-decoded) row
            for field in ("linked_profiles", "score_breakdown"):
                if isinstance(updates.get(field), (list, dict)):
                    updates[field] = json.dumps(updates[field])
            self.conn.execute(
                f"UPDATE prospects SET {', '.join(f'{k} = ?' for k in updates)} "
                f"WHERE id = ?",
                [*updates.values(), existing["id"]],
            )
            self.conn.commit()
            return {
                "id": existing["id"],
                "outcome": "UPDATED" if changed else "UNCHANGED",
            }

        record.setdefault("first_seen_at", record.get("discovered_at") or now)
        record.setdefault("discovered_at", now)
        record.setdefault("last_verified_at", now)
        columns = [c for c in _PROSPECT_COLUMNS if c in record]
        self.conn.execute(
            f"INSERT INTO prospects ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            [record.get(c) for c in columns],
        )
        self.conn.commit()
        prospect_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {"id": prospect_id, "outcome": "NEW"}

    def find_by_identity(self, platform: str, platform_user_id: str) -> dict | None:
        if not platform_user_id:
            return None
        row = self.conn.execute(
            "SELECT * FROM prospects WHERE platform = ? AND platform_user_id = ?",
            (platform, platform_user_id),
        ).fetchone()
        return row_to_prospect(row) if row else None

    def find_by_email(self, email: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM prospects WHERE lower(public_email) = ?",
            ((email or "").lower(),),
        ).fetchall()
        return [row_to_prospect(r) for r in rows]

    def find_by_website_domain(self, domain: str) -> list[dict]:
        if not domain:
            return []
        rows = self.conn.execute(
            "SELECT * FROM prospects WHERE website LIKE ?",
            (f"%{domain}%",),
        ).fetchall()
        return [row_to_prospect(r) for r in rows if domain in (r["website"] or "")]

    def get(self, prospect_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM prospects WHERE id = ?", (prospect_id,)
        ).fetchone()
        return row_to_prospect(row) if row else None

    def update_status(self, prospect_id: int, status: str, note: str | None = None) -> bool:
        from . import STATUSES

        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}; expected one of {STATUSES}")
        fields = {"status": status, "last_verified_at": utcnow()}
        if note:
            existing = self.get(prospect_id)
            sep = "\n" if existing and existing.get("notes") else ""
            fields["notes"] = f"{(existing or {}).get('notes', '')}{sep}{note}"
        self.conn.execute(
            f"UPDATE prospects SET {', '.join(f'{k} = ?' for k in fields)} WHERE id = ?",
            [*fields.values(), prospect_id],
        )
        self.conn.commit()
        if status == "SUPPRESS":
            prospect = self.get(prospect_id)
            if prospect:
                from . import suppression

                suppression.add_from_prospect(self, prospect, "marked SUPPRESS via CLI")
        return True

    def add_note(self, prospect_id: int, text: str) -> bool:
        existing = self.get(prospect_id)
        if not existing:
            return False
        sep = "\n" if existing.get("notes") else ""
        self.conn.execute(
            "UPDATE prospects SET notes = ? WHERE id = ?",
            (f"{existing['notes']}{sep}{text}", prospect_id),
        )
        self.conn.commit()
        return True

    def rescore_all(self, scorer) -> int:
        rows = self.conn.execute("SELECT * FROM prospects").fetchall()
        for row in rows:
            prospect = row_to_prospect(row)
            scored = scorer.score(prospect)
            self.conn.execute(
                "UPDATE prospects SET relevance_score = ?, commercial_score = ?, "
                "confidence_score = ?, score_breakdown = ?, score_reason = ?, "
                "priority = ? WHERE id = ?",
                (
                    scored["relevance_score"], scored["commercial_score"],
                    scored["confidence_score"],
                    json.dumps(scored["breakdown"]), scored["score_reason"],
                    scored["priority"], prospect["id"],
                ),
            )
        self.conn.commit()
        return len(rows)

    def list_prospects(
        self,
        min_score: int = 0,
        team: str | None = None,
        require_email: bool = False,
        exclude_statuses: list[str] | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        query = (
            "SELECT * FROM prospects WHERE "
            "(relevance_score IS NULL OR relevance_score >= ?)"
        )
        params: list = [min_score]
        if team:
            query += " AND team = ?"
            params.append(team)
        if require_email:
            query += " AND public_email IS NOT NULL AND public_email != ''"
        if exclude_statuses:
            query += f" AND status NOT IN ({', '.join('?' for _ in exclude_statuses)})"
            params.extend(exclude_statuses)
        query += " ORDER BY relevance_score DESC, discovered_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        return [row_to_prospect(r) for r in self.conn.execute(query, params).fetchall()]

    # -- matches -----------------------------------------------------------
    def add_match(self, a: int, b: int, basis: str, confidence: str) -> None:
        existing = self.conn.execute(
            "SELECT id FROM matches WHERE (prospect_id_a = ? AND prospect_id_b = ?) "
            "OR (prospect_id_a = ? AND prospect_id_b = ?)",
            (a, b, b, a),
        ).fetchone()
        if not existing:
            self.conn.execute(
                "INSERT INTO matches (prospect_id_a, prospect_id_b, basis, confidence, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (a, b, basis, confidence, utcnow()),
            )
            self.conn.commit()

    def list_matches(self, confidence: str | None = None) -> list[dict]:
        if confidence:
            rows = self.conn.execute(
                "SELECT * FROM matches WHERE confidence = ? ORDER BY created_at DESC",
                (confidence,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM matches ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    # -- runs ---------------------------------------------------------------
    def start_run(self, mode: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs (started_at, mode) VALUES (?, ?)", (utcnow(), mode)
        )
        self.conn.commit()
        return cur.lastrowid

    def finish_run(self, run_id: int, **counts) -> None:
        self.conn.execute(
            "UPDATE runs SET finished_at = ?, new = ?, updated = ?, unchanged = ?, "
            "suppressed_hits = ?, collectors = ? WHERE id = ?",
            (
                utcnow(), counts.get("new", 0), counts.get("updated", 0),
                counts.get("unchanged", 0), counts.get("suppressed_hits", 0),
                json.dumps(counts.get("collectors", [])), run_id,
            ),
        )
        self.conn.commit()

    def last_run(self) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    # -- cleanup ------------------------------------------------------------
    def delete_stale(self, days: int, protected_statuses: list[str]) -> list[int]:
        cutoff = _iso_days_ago(days)
        placeholders = ", ".join("?" for _ in protected_statuses)
        rows = self.conn.execute(
            f"SELECT id FROM prospects WHERE last_seen_at < ? "
            f"AND status NOT IN ({placeholders})",
            [cutoff, *protected_statuses],
        ).fetchall()
        ids = [r["id"] for r in rows]
        if ids:
            marks = ", ".join("?" for _ in ids)
            self.conn.execute(f"DELETE FROM prospects WHERE id IN ({marks})", ids)
            self.conn.commit()
        return ids


def _merge_teams(existing: dict, record: dict) -> list[str]:
    def as_list(value) -> list[str]:
        if isinstance(value, list):
            return [t for t in value if t]
        if isinstance(value, str) and value:
            try:
                return [t for t in json.loads(value) if t]
            except json.JSONDecodeError:
                return []
        return []

    merged = as_list(existing.get("teams")) + [
        t for t in as_list(record.get("teams")) if t not in as_list(existing.get("teams"))
    ]
    return list(dict.fromkeys(merged))


def _iso_days_ago(days: int) -> str:
    import datetime as _dt

    return (
        _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=days)
    ).replace(microsecond=0).isoformat()
