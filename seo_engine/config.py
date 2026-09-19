"""Engine constants and paths. Stdlib only — import-safe, no network, no writes."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"
SEO_DATA = DATA / "seo"
OVERRIDES_PATH = SEO_DATA / "overrides.json"
AUDIT_PATH = SEO_DATA / "last_audit.json"
DECISIONS_PATH = SEO_DATA / "last_decisions.json"
PROPOSALS_DIR = SEO_DATA / "proposals"
MEMORY_PATH = SEO_DATA / "learning_memory.json"
GSC_EXPORT_PATH = SEO_DATA / "gsc_export.json"
CATALOGUE_PATH = DATA / "catalogue-live.json"
CONFIG_PATH = ROOT / "src" / "config.json"

# Automation modes (controlled autonomy — never unrestricted live rewrites).
MODE_AUTO = "AUTO"      # low-risk, reversible metadata / alt / canonical
MODE_PR = "PR"          # content rewrites, new guides, major meta clusters
MODE_HUMAN = "HUMAN"    # URL changes, deletes, merges, redirects

# Risk classes the decider assigns.
SAFE_TYPES = frozenset({
    "missing_title",
    "missing_description",
    "title_too_long",
    "title_too_short",
    "description_too_long",
    "description_too_short",
    "missing_canonical",
    "missing_og_title",
    "missing_og_description",
    "missing_image_alt",
    "duplicate_title",
    "duplicate_description",
    "weak_ctr_title",       # GSC-backed title tweak when export is present
})

PR_TYPES = frozenset({
    "new_guide_article",
    "collection_content_rewrite",
    "product_content_rewrite",
    "internal_link_cluster",
    "schema_enrichment",
})

HUMAN_TYPES = frozenset({
    "url_change",
    "page_delete",
    "page_merge",
    "redirect_remap",
    "collection_restructure",
})

# SERP budgets (characters). Google's display is fluid; these are QA gates.
TITLE_MIN = 30
TITLE_MAX = 60
DESC_MIN = 70
DESC_MAX = 158

# Pages the engine must never propose changes for.
EXCLUDED_PREFIXES = ("/ops/", "/marketing/", "/404")
# Verification tokens / non-pages.
NOT_PAGES = ("google", "BingSiteAuth", "a7f3c19b")

PUBLIC_COLLECTIONS = (
    "cleveland-browns-shirts",
    "dallas-cowboys-shirts",
    "green-bay-packers-shirts",
    "michigan-wolverines-shirts",
)


def load_site_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def domain() -> str:
    return load_site_config()["domain"].rstrip("/")


def ensure_seo_dirs() -> None:
    SEO_DATA.mkdir(parents=True, exist_ok=True)
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default=None):
    if not path.is_file():
        return default if default is not None else {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload) -> None:
    ensure_seo_dirs()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)
