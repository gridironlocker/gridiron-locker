"""Aggregate-only public page data for the OSINT prospect engine.

``python3 -m marketing.osint build-page`` reads the PRIVATE local database,
reduces it to COUNTS (no names, emails, URLs or any other value that could
identify a prospect), seals it with a salted SHA-256 of the page password,
and writes the COMMITTED file ``marketing/osint/page/prospects.json``.

``src/prospects_page.py`` renders the deployed dashboard
(``site/ops/prospects/``, robots-disallowed + noindex + password gate) from
that JSON. This package never writes to ``site/`` or ``data/`` itself — the
page directory is the only committed output this module touches, and
``validate_page_data()`` + ``audit.py`` + the test suite all enforce that it
stays aggregate-only.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from pathlib import Path

from . import EMAIL_CATEGORIES  # noqa: F401  (re-exported for template authors)
from . import PRIORITY_BANDS, PROSPECT_TYPES, STATUSES, config

#: Committed page-data format version (bumped if the schema changes).
PAGE_VERSION = 1

#: File the renderer reads. Committed, aggregate-only, safe for a public repo.
PAGE_FILENAME = "prospects.json"

#: Passwords shorter than this are rejected at build time.
MIN_PASSWORD_LEN = 12

#: Domain-separation prefix for the page-password hash. The deployed gate's
#: JavaScript must hash with this exact prefix (see src/prospects_page.py);
#: a test asserts the two stay in sync.
SALT_PREFIX = "gl-osint-page-v1:"

#: Env var carrying the page password at build time. The password itself is
#: NEVER written anywhere — only its salted SHA-256 leaves this module.
PASSWORD_ENV_VAR = "OSINT_PAGE_PASSWORD"

PRIORITY_NAMES = [name for _, name in PRIORITY_BANDS]

_EMAIL_LIKE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def page_dir() -> Path:
    """Committed page-data directory (overridable for tests)."""
    return Path(os.environ.get("OSINT_PAGE_DIR") or config.PKG_DIR / "page")


def page_json_path() -> Path:
    return page_dir() / PAGE_FILENAME


def hash_password(password: str) -> str:
    """Salted SHA-256 hex of the page password (what gets committed)."""
    return hashlib.sha256((SALT_PREFIX + password).encode("utf-8")).hexdigest()


def verify_password(password: str, expected_hex: str) -> bool:
    try:
        return hmac.compare_digest(hash_password(password), expected_hex)
    except (TypeError, ValueError):
        return False


def require_password() -> str:
    """Read the page password from the environment or explain how to set it."""
    password = os.environ.get(PASSWORD_ENV_VAR)
    if not password:
        raise SystemExit(
            f"{PASSWORD_ENV_VAR} is not set — the page password is never stored "
            f"in the repo, so pass it in the environment, e.g.\n"
            f"  {PASSWORD_ENV_VAR}=... python3 -m marketing.osint build-page"
        )
    if len(password) < MIN_PASSWORD_LEN:
        raise SystemExit(
            f"page password too short ({len(password)} chars) — "
            f"minimum is {MIN_PASSWORD_LEN}"
        )
    return password


def _bucket(value: str | None, known: list[str]) -> str:
    """Map a free-text column onto a fixed public vocabulary.

    ``team`` / ``prospect_type`` / ``priority`` / ``status`` can all arrive
    via manual CSV import, so their raw values are untrusted: only the fixed
    vocabularies are published, everything else folds into ``"other"``.
    """
    return value if value in known else "other"


def _counts(rows: list, known: list[str]) -> dict[str, int]:
    tallies: dict[str, int] = {key: 0 for key in [*known, "other"]}
    for value in rows:
        tallies[_bucket(value, known)] += 1
    return tallies


def build_page_data(repo, password: str, *, generated_at: str | None = None) -> dict:
    """Reduce the private database to publishable aggregate counts.

    Returns the exact object ``write_page_data()`` commits. Only integers,
    fixed-vocabulary keys, timestamps and the password hash — a test asserts
    the serialised form contains no email-like string, no URL and no ``@``.
    """
    from . import db as db_mod

    teams = [r["team"] for r in repo.conn.execute("SELECT team FROM prospects")]
    types = [r["prospect_type"] for r in repo.conn.execute("SELECT prospect_type FROM prospects")]
    priorities = [r["priority"] for r in repo.conn.execute("SELECT priority FROM prospects")]
    statuses = [r["status"] for r in repo.conn.execute("SELECT status FROM prospects")]
    with_email = repo.conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE public_email IS NOT NULL AND public_email != ''"
    ).fetchone()[0]
    verified = repo.conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE email_verified LIKE 'VERIFIED%'"
    ).fetchone()[0]
    suppressed = repo.conn.execute("SELECT COUNT(*) FROM suppression").fetchone()[0]

    last_run = repo.last_run()
    last_run_payload = None
    if last_run:
        last_run_payload = {
            key: last_run.get(key)
            for key in (
                "mode", "started_at", "finished_at", "new", "updated",
                "unchanged", "suppressed_hits",
            )
        }

    return {
        "version": PAGE_VERSION,
        "generated_at": generated_at or db_mod.utcnow(),
        "password_sha256": hash_password(password),
        "team_labels": dict(config.TEAM_LABELS),
        "totals": {
            "prospects": len(teams),
            "with_public_email": with_email,
            "verified_email": verified,
            "suppressed_identities": suppressed,
        },
        "by_team": _counts(teams, config.TEAM_SLUGS),
        "by_type": _counts(types, PROSPECT_TYPES),
        "by_priority": _counts(priorities, PRIORITY_NAMES),
        "by_status": _counts(statuses, STATUSES),
        "last_run": last_run_payload,
    }


def write_page_data(data: dict, path: Path | None = None) -> Path:
    """Write page data into the page directory ONLY (committed, PII-free).

    Refuses any destination outside ``page_dir()`` — mirroring the exporter's
    refusal to write into the deployed tree, in the other direction.
    """
    target = Path(path) if path else page_json_path()
    base = page_dir().resolve()
    resolved = target.resolve() if target.is_absolute() else (Path.cwd() / target).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(
            f"refusing to write page data to {target} — page data lives in {base} only"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return resolved


def load_page_data(path: Path | None = None) -> dict | None:
    """Read committed page data, or None when it has not been generated yet."""
    target = Path(path) if path else page_json_path()
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError(f"{target}: invalid JSON ({err})")


def validate_page_data(obj) -> list[str]:
    """Schema + aggregate-only checks. Returns problems (empty = valid)."""
    problems: list[str] = []
    if not isinstance(obj, dict):
        return ["page data is not a JSON object"]
    if obj.get("version") != PAGE_VERSION:
        problems.append(f"version is {obj.get('version')!r}, expected {PAGE_VERSION}")
    digest = obj.get("password_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        problems.append("password_sha256 is not a 64-char lowercase hex digest")
    if not isinstance(obj.get("generated_at"), str) or not obj["generated_at"]:
        problems.append("generated_at is missing")
    labels = obj.get("team_labels")
    if not isinstance(labels, dict) or any(t not in labels for t in config.TEAM_SLUGS):
        problems.append("team_labels must cover every team slug")

    def _check_counts(name: str, known: list[str]) -> None:
        section = obj.get(name)
        if not isinstance(section, dict):
            problems.append(f"{name} is not an object")
            return
        for key in [*known, "other"]:
            value = section.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                problems.append(f"{name}.{key} is not a non-negative int")
        for key in section:
            if key not in (*known, "other"):
                problems.append(f"{name} has unexpected key {key!r}")

    totals = obj.get("totals")
    if not isinstance(totals, dict):
        problems.append("totals is not an object")
    else:
        for key in ("prospects", "with_public_email", "verified_email", "suppressed_identities"):
            value = totals.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                problems.append(f"totals.{key} is not a non-negative int")
    _check_counts("by_team", config.TEAM_SLUGS)
    _check_counts("by_type", PROSPECT_TYPES)
    _check_counts("by_priority", PRIORITY_NAMES)
    _check_counts("by_status", STATUSES)
    last_run = obj.get("last_run")
    if last_run is not None and not isinstance(last_run, dict):
        problems.append("last_run must be null or an object")

    # The aggregate-only guarantee, enforced on the serialised bytes: counts,
    # fixed vocabularies and timestamps never contain '@' or URLs, so any
    # occurrence means a prospect-identifying value slipped into the schema.
    dumped = json.dumps(obj, sort_keys=True)
    if _EMAIL_LIKE.search(dumped):
        problems.append("page data contains an email-like string (must be aggregate-only)")
    if "@" in dumped:
        problems.append("page data contains '@' (must be aggregate-only)")
    if "http" in dumped.lower():
        problems.append("page data contains a URL (must be aggregate-only)")
    return problems
