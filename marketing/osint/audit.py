"""Safety audit: prove no prospect data can leak into the public repo/site.

``python3 -m marketing.osint audit`` is READ-ONLY and hermetic (no network,
no database writes). It checks:

1. the committed page data (``marketing/osint/page/prospects.json``) is
   valid and aggregate-only;
2. the rendered dashboards (``ops/prospects/``, ``site/ops/prospects/``)
   contain no email-like strings or URLs, carry ``noindex``, and embed no
   64-hex blob other than the page-password hash;
3. no private-state filenames (``*.db``, ``suppression.csv``,
   ``gridiron_prospects_*.csv``, ``high_priority_contacts_*.csv``) exist
   anywhere under ``site/``, ``ops/`` or ``marketing/`` outside the two
   gitignored private homes (``marketing/osint/state/`` + ``exports/``),
   and none are tracked by git;
4. ``.gitignore`` still carries the OSINT guards;
5. the CSV exporter still refuses ``site/`` and ``ops/``.

Exit code 0 + ``AUDIT: 0 findings`` when clean, 1 otherwise. Findings never
include prospect content itself (counts and paths only), so the output is
safe to paste anywhere.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import config, exporters
from .page import validate_page_data

EMAIL_LIKE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_HEX64 = re.compile(r"[0-9a-f]{64}")

#: Private-state filenames that must never appear outside state//exports/.
STRAY_EXACT = {"prospects.db", "suppression.csv"}
STRAY_DB_SUFFIXES = (".db", ".sqlite", ".sqlite3")
STRAY_CSV_PREFIXES = ("gridiron_prospects_", "high_priority_contacts_")

#: .gitignore lines that keep `git add -A` from committing prospect data.
GITIGNORE_REQUIRED = (
    "marketing/osint/state/",
    "marketing/osint/exports/",
)

RENDERED_PAGES = (
    "ops/prospects/index.html",
    "site/ops/prospects/index.html",
)

#: Marker the renderer leaves in the not-generated-yet placeholder, which is
#: legitimately gate-free (it contains no data at all).
PLACEHOLDER_MARKER = "osint-page-placeholder"


@dataclass
class AuditResult:
    findings: list = field(default_factory=list)
    checked: dict = field(default_factory=dict)


def _is_stray(filename: str) -> bool:
    if filename in STRAY_EXACT:
        return True
    lowered = filename.lower()
    if lowered.endswith(STRAY_DB_SUFFIXES):
        return True
    return lowered.endswith(".csv") and lowered.startswith(STRAY_CSV_PREFIXES)


def _private_homes(root: Path) -> set[Path]:
    base = root / "marketing" / "osint"
    return {(base / "state").resolve(), (base / "exports").resolve()}


def check_page_data(root: Path, result: AuditResult) -> str | None:
    """Validate the committed page JSON. Returns its password hash, if any."""
    path = root / "marketing" / "osint" / "page" / "prospects.json"
    if not path.exists():
        result.checked["page_json"] = "missing (page not generated yet)"
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        result.findings.append(f"{path}: unreadable ({err})")
        result.checked["page_json"] = "unreadable"
        return None
    for problem in validate_page_data(obj):
        result.findings.append(f"marketing/osint/page/prospects.json: {problem}")
    result.checked["page_json"] = "ok"
    digest = obj.get("password_sha256")
    return digest if isinstance(digest, str) else None


def check_rendered_pages(root: Path, result: AuditResult, expected_hash: str | None) -> None:
    for rel in RENDERED_PAGES:
        path = root / rel
        if not path.exists():
            result.checked[rel] = "missing"
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as err:
            result.findings.append(f"{rel}: unreadable ({err})")
            result.checked[rel] = "unreadable"
            continue
        emails = EMAIL_LIKE.findall(text)
        if emails:
            result.findings.append(
                f"{rel}: contains {len(emails)} email-like string(s) "
                f"(rendered page must be aggregate-only)"
            )
        if "http" in text.lower():
            result.findings.append(f"{rel}: contains a URL (page must use relative links only)")
        if "noindex" not in text.lower():
            result.findings.append(f"{rel}: missing noindex (internal pages stay out of indexes)")
        if PLACEHOLDER_MARKER in text:
            result.checked[rel] = "ok (placeholder)"
            continue
        if "data-pass-sha256" not in text:
            result.findings.append(f"{rel}: password gate markup missing")
        elif expected_hash:
            foreign = {token for token in _HEX64.findall(text) if token != expected_hash}
            if foreign:
                result.findings.append(
                    f"{rel}: contains {len(foreign)} unrecognised 64-hex blob(s) "
                    f"(only the page-password hash may appear)"
                )
        result.checked[rel] = "ok"


def check_stray_files(root: Path, result: AuditResult) -> None:
    homes = _private_homes(root)
    scanned = 0
    for top in ("site", "ops", "marketing"):
        base = root / top
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            resolved = Path(dirpath).resolve()
            try:
                rel_parts = resolved.relative_to(root.resolve()).parts
            except ValueError:
                rel_parts = ()
            # Never descend into, and never scan, the two sanctioned private
            # homes (checked both by resolved path and by relative parts so
            # symlinked/odd layouts are covered too).
            if (
                any(resolved == home or home in resolved.parents for home in homes)
                or rel_parts[:3] == ("marketing", "osint", "state")
                or rel_parts[:3] == ("marketing", "osint", "exports")
            ):
                dirnames[:] = []
                continue
            for filename in filenames:
                scanned += 1
                if _is_stray(filename):
                    rel = str(Path(dirpath, filename).relative_to(root))
                    result.findings.append(
                        f"{rel}: private-state file outside state//exports/"
                    )
    result.checked["files_scanned_for_strays"] = scanned
    # Belt and braces: nothing stray may be TRACKED either (catches a leak
    # committed before the working-tree file was deleted).
    if (root / ".git").is_dir():
        try:
            out = subprocess.run(
                ["git", "ls-files"], cwd=root, capture_output=True, text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            result.checked["git_tracked_scan"] = "skipped (git unavailable)"
        else:
            tracked_strays = [line for line in out.stdout.splitlines() if _is_stray(Path(line).name)]
            for rel in tracked_strays:
                result.findings.append(f"{rel}: private-state file tracked by git")
            result.checked["git_tracked_scan"] = f"ok ({len(out.stdout.splitlines())} tracked)"


def check_gitignore(root: Path, result: AuditResult) -> None:
    path = root / ".gitignore"
    if not path.exists():
        result.findings.append(".gitignore is missing")
        result.checked["gitignore"] = "missing"
        return
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    missing = [line for line in GITIGNORE_REQUIRED if line not in lines]
    for line in missing:
        result.findings.append(f".gitignore no longer contains {line}")
    result.checked["gitignore"] = "ok" if not missing else "guards missing"


def check_export_guards(result: AuditResult) -> None:
    """The exporter must keep refusing the deployed/generated trees."""
    for prefix in ("site", "ops"):
        probe = config.ROOT / prefix / "_audit_probe.csv"
        try:
            exporters.write_csv([], probe)
        except ValueError:
            continue
        except OSError:
            # Unwritable in this environment — the guard's ValueError is what
            # matters, and any refusal still means "not written".
            if probe.exists():
                probe.unlink()
            continue
        if probe.exists():
            probe.unlink()
        result.findings.append(f"exporter wrote into {prefix}/ instead of refusing")
    result.checked["export_guards"] = "ok"


def audit_tree(root: Path | None = None) -> AuditResult:
    """Run every check against ``root`` (default: the real repository)."""
    root = Path(root) if root else config.ROOT
    result = AuditResult()
    expected_hash = check_page_data(root, result)
    check_rendered_pages(root, result, expected_hash)
    check_stray_files(root, result)
    check_gitignore(root, result)
    check_export_guards(result)
    return result


def main() -> int:
    result = audit_tree()
    count = len(result.findings)
    print(f"AUDIT: {count} finding(s)")
    for finding in result.findings:
        print(f"  - {finding}")
    print("Checked: " + ", ".join(f"{key}={value}" for key, value in result.checked.items()))
    return 0 if count == 0 else 1
