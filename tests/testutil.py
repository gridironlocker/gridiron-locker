#!/usr/bin/env python3
"""Shared helpers for the marketing-generator tests.

Why this exists
---------------
``marketing/plan.py``, ``commercial_agent.py``, ``three_day_pulse.py``,
``social_watch.py`` and ``publisher.py`` each resolve their input and output
paths from ``Path(__file__).resolve().parent.parent`` - i.e. from *wherever the
file physically lives*. Running them in-place therefore rewrites the tracked
artefacts in ``marketing/``:

    M marketing/commercial-brief.json
    M marketing/plan.json
    M marketing/social-signals.json
    M marketing/three-day-pulse.json

That is not acceptable for a test suite. ``.github/workflows/refresh.yml``
commits with ``git add -A``, so a developer (or a CI job) that runs the tests
and then pushes would commit whatever the generators last emitted - including a
degraded, network-starved ``social-signals.json`` that silently replaces the
curated evidence with error stubs.

``generator_sandbox()`` copies just the files the generators read into a
temporary tree and runs them *there*. The generators resolve their paths from
their own ``__file__``, so the copy writes into the copy. The real repository is
never touched, and the tests still exercise the real generator code end to end.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The generators import SEASON / COLLECTIONS from src/, so the Python sources
#: and config have to exist in the sandbox at the same relative paths.
_SRC_GLOB = ("*.py", "config.json")

#: Everything the generators read out of data/. Copied wholesale - it is small
#: (<1 MB) and copying it all means a generator that grows a new input file
#: keeps working without this list being updated.
_DATA_GLOB = ("*.json",)

#: marketing/ holds both the generators and the artefacts they read back
#: (plan.json -> commercial_agent.py, social-signals.json -> three_day_pulse.py).
#: marketing/social/ is multi-megabyte image kit no generator reads, so it is
#: deliberately not copied.
_MARKETING_GLOB = ("*.py", "*.json", "*.csv")


@contextlib.contextmanager
def generator_sandbox():
    """Yield the ``Path`` of a throwaway repo copy safe to run generators in.

    The tree is deleted on exit, so a test run leaves no artefacts behind -
    not even the gitignored ``marketing/publish-results.json``.
    """
    tmp = Path(tempfile.mkdtemp(prefix="gridiron-marketing-"))
    try:
        for top, patterns in (
            ("src", _SRC_GLOB),
            ("data", _DATA_GLOB),
            ("marketing", _MARKETING_GLOB),
        ):
            src_dir = ROOT / top
            dst_dir = tmp / top
            dst_dir.mkdir(parents=True, exist_ok=True)
            for pattern in patterns:
                for item in src_dir.glob(pattern):
                    if item.is_file():
                        shutil.copy2(item, dst_dir / item.name)
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_generator(sandbox: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    """Run ``marketing/<script>`` inside the sandbox and fail loudly if it dies.

    ``sys.dont_write_bytecode`` is set for the child so a test run cannot leave
    ``__pycache__`` directories behind in the sandbox (or, if anything ever
    resolves back to the real tree, in the repository).
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, os.path.join("marketing", script), *args],
        cwd=sandbox,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def read_json(path: Path):
    """Read a generated artefact from the sandbox."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)
