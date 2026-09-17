"""Conservative duplicate detection.

The same person/business can appear as an Apple-podcasts row, a website row
and a manual row. We link duplicates using public signals only:

* exact public business email  -> CONFIRMED_MATCH
* same registered website domain (different platform) -> CONFIRMED_MATCH
* same username across platforms -> CONFIRMED_MATCH
* same exact display/business name AND overlapping team -> POSSIBLE_MATCH

No fuzzy name matching, no guessing. Uncertain links are recorded, never
merged silently.
"""
from __future__ import annotations

import urllib.parse

_MULTI_PART_TLDS = {
    ".co.uk", ".org.uk", ".com.au", ".co.nz", ".org.au", ".com.br",
    ".co.jp", ".com.mx", ".co.za",
}


def registered_domain(url_or_host: str) -> str:
    """example: https://www.podsite.co.uk/feed -> podsite.co.uk"""
    if not url_or_host:
        return ""
    host = urllib.parse.urlsplit(url_or_host).netloc or url_or_host
    host = host.lower().strip()
    if "@" in host:
        host = host.split("@", 1)[1]
    host = host.split(":")[0].split("/")[0].strip(".")
    if not host:
        return ""
    labels = host.split(".")
    if len(labels) < 2:
        return host
    for multi in _MULTI_PART_TLDS:
        if host.endswith(multi) and len(labels) >= 3:
            return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def normalize_username(username: str) -> str:
    return (username or "").lower().strip().lstrip("@").strip()


def detect_links(repo, prospect: dict, prospect_id: int) -> list[dict]:
    """Record cross-platform matches for a freshly stored prospect."""
    found: list[dict] = []
    email = (prospect.get("public_email") or "").lower().strip()
    username = normalize_username(prospect.get("username"))
    domain = registered_domain(prospect.get("website") or "")
    name = (prospect.get("display_name") or "").strip().lower()

    others = repo.conn.execute(
        "SELECT * FROM prospects WHERE id != ?", (prospect_id,)
    ).fetchall()
    for row in others:
        other = {key: row[key] for key in row.keys()}
        if other.get("platform") == prospect.get("platform"):
            continue  # same-platform duplicates are handled by identity upsert
        other_domain = registered_domain(other.get("website") or "")
        other_email = (other.get("public_email") or "").lower().strip()
        other_name = (other.get("display_name") or "").strip().lower()
        other_username = normalize_username(other.get("username"))

        basis, confidence = None, None
        if email and email == other_email:
            basis, confidence = "same public business email", "CONFIRMED_MATCH"
        elif domain and domain == other_domain and domain not in ("", "linktr.ee"):
            basis, confidence = f"same website domain ({domain})", "CONFIRMED_MATCH"
        elif username and username == other_username and username not in ("", "admin"):
            basis, confidence = f"same username ({username})", "CONFIRMED_MATCH"
        elif (
            name and len(name) > 5 and name == other_name
            and prospect.get("team") and other.get("team") == prospect.get("team")
            and domain and domain == other_domain
        ):
            basis, confidence = "same public business name + site", "POSSIBLE_MATCH"

        if basis:
            repo.add_match(prospect_id, other["id"], basis, confidence)
            found.append({
                "prospect_id": other["id"],
                "basis": basis,
                "confidence": confidence,
            })
    return found
