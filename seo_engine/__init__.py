"""Gridiron SEO Engine — controlled-autonomy SEO for a Git static storefront.

Architecture (copied from production-tested patterns, adapted to this repo):

    RankEngine loop     audit → decide → apply → verify → learn
    Ahrefs Agent A      ecommerce ranking + competitor awareness
    Agentic SEO         GSC + crawler + AI + GitHub
    Claude SEO Agent    code-based fixes against the codebase

Hard rules (see AGENTS.md):

* ``site/`` is *generated*. The engine NEVER hand-edits HTML under ``site/``.
* Safe changes write ``data/seo/overrides.json``; ``src/build.py`` consumes it.
* High-impact changes emit a PR proposal under ``data/seo/proposals/``.
* Structural / URL / delete work is HUMAN-only and never auto-applied.
* No fabricated trust signals, no thin intent pages, no meta-keywords stuffing.

Public entry points:

    python3 -m seo_engine audit
    python3 -m seo_engine decide
    python3 -m seo_engine apply --mode auto|dry-run
    python3 -m seo_engine verify
    python3 -m seo_engine run          # full loop, dry-run by default
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
