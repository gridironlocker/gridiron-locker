"""Gridiron Locker — private OSINT prospect engine.

A modular, stdlib-only prospect discovery system. See README.md in this
directory for the full design, the safety rules and the dependency research.

Command line (run from the repository root):

    python3 -m marketing.osint discover
    python3 -m marketing.osint refresh
    python3 -m marketing.osint export
    python3 -m marketing.osint stats
    python3 -m marketing.osint verify

This package NEVER sends email, never writes to data/ and never writes to
site/. All state lives under marketing/osint/state/ (gitignored).
"""

__version__ = "1.0.0"

#: Prospect lifecycle statuses (see README.md "Manual outreach workflow").
STATUSES = [
    "NEW",
    "REVIEW",
    "QUALIFIED",
    "CONTACTED",
    "REPLIED",
    "INTERESTED",
    "CUSTOMER",
    "PARTNER",
    "NOT_INTERESTED",
    "BOUNCED",
    "SUPPRESS",
]

#: Prospect type buckets (spec: PROSPECT TYPES).
PROSPECT_TYPES = [
    "FAN_CREATOR",
    "FAN_COMMUNITY",
    "BLOG_WEBSITE",
    "PODCAST_MEDIA",
    "SPORTS_BUSINESS",
    "OTHER",
]

#: Score bands (spec: PRIORITY LEVELS).
PRIORITY_BANDS = [
    (90, "HIGH_PRIORITY"),
    (75, "QUALIFIED"),
    (60, "REVIEW"),
    (0, "LOW_PRIORITY"),
]

#: Email categories. Only PUBLIC_BUSINESS_EMAIL is auto-imported from
#: collection; anything else must be entered by hand.
EMAIL_CATEGORIES = [
    "PUBLIC_BUSINESS_EMAIL",
    "PUBLIC_RSS_OWNER_EMAIL",   # public, but provenance flagged for review
    "MANUAL",
]
