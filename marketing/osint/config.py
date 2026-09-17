"""Configuration for the OSINT prospect engine.

Everything is configuration-file driven per the spec: team keyword lists live
in keywords/*.json and website seeds in seeds/websites.json, never hard-coded
into collectors.

Path overrides (used by the test suite and the CI verification workflow so no
prospect data ever lands inside the repository working tree):

    OSINT_STATE_DIR    default: marketing/osint/state
    OSINT_EXPORTS_DIR  default: marketing/osint/exports

Data/ is read-only to this package (repo contract: marketing never writes to
data/). The existing trend system at data/trends.json is read to make
discovery trend-aware; nothing is written back.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent.parent          # repository root
DATA_DIR = ROOT / "data"              # READ-ONLY for this package
KEYWORDS_DIR = PKG_DIR / "keywords"
SEEDS_FILE = PKG_DIR / "seeds" / "websites.json"

#: The four Gridiron Locker audiences.
TEAM_SLUGS = ["michigan", "browns", "packers", "cowboys"]

TEAM_LABELS = {
    "michigan": "Michigan Wolverines",
    "browns": "Cleveland Browns",
    "packers": "Green Bay Packers",
    "cowboys": "Dallas Cowboys",
}

#: Trend-system collection slugs (data/trends.json) for each audience team.
TREND_COLLECTION = {
    "michigan": "michigan",
    "browns": "cleveland-browns",
    "packers": "green-bay-packers",
    "cowboys": "dallas-cowboys",
}


def state_dir() -> Path:
    return Path(os.environ.get("OSINT_STATE_DIR") or PKG_DIR / "state")


def exports_dir() -> Path:
    return Path(os.environ.get("OSINT_EXPORTS_DIR") or PKG_DIR / "exports")


def db_path() -> Path:
    return state_dir() / "prospects.db"


def suppression_csv_path() -> Path:
    return state_dir() / "suppression.csv"


def load_keywords(team: str) -> dict:
    """Load one team's keyword file. Raises FileNotFoundError with a clear
    message if missing — keywords are required, not optional."""
    path = KEYWORDS_DIR / f"{team}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"keyword file missing: {path} (every team needs one; "
            f"expected one of {TEAM_SLUGS})"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("label", "strong_terms", "terms", "search_queries"):
        if field not in data:
            raise ValueError(f"{path}: missing required field {field!r}")
    return data


def load_all_keywords() -> dict[str, dict]:
    return {team: load_keywords(team) for team in TEAM_SLUGS}


def load_seeds() -> list[dict]:
    """Curated public website seeds (seeds/websites.json). May be empty."""
    if not SEEDS_FILE.exists():
        return []
    data = json.loads(SEEDS_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("seeds", [])


def load_trend_terms(max_per_team: int = 3) -> dict[str, list[str]]:
    """Read the existing trend system (READ-ONLY) and return current
    people/subjects per team that discovery should search around.

    Returns {} when the trends file is absent or unreadable — trend-aware
    discovery degrades gracefully to the static keyword lists.
    """
    path = DATA_DIR / "trends.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    collections = data.get("collections", {})
    out: dict[str, list[str]] = {}
    for team, coll_slug in TREND_COLLECTION.items():
        coll = collections.get(coll_slug, {})
        terms: list[str] = []
        for gap in coll.get("gaps", []) or []:
            if isinstance(gap, str) and gap not in terms:
                terms.append(gap.lower().strip())
        for ent in (coll.get("entity_mentions", {}) or {}).keys():
            if isinstance(ent, str) and ent.lower().strip() not in terms:
                terms.append(ent.lower().strip())
        out[team] = terms[:max_per_team]
    return out


def normalize_team(value: str) -> str:
    """Accept 'michigan', 'Michigan Wolverines', 'michigan-wolverines', ..."""
    v = value.lower().strip().replace("-", " ").replace("_", " ")
    for slug, label in TEAM_LABELS.items():
        if v == slug or v == label.lower():
            return slug
    raise ValueError(f"unknown team {value!r} — expected one of {TEAM_SLUGS}")
