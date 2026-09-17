"""Instagram collector — DISABLED (no legitimate automated access path).

Why, in full (also documented in ../README.md):

* Instagram's Terms of Use prohibit automated collection/scraping. There is
  no robots.txt exemption and no public search API for third-party profiles.
* The Instagram Basic Display API was shut down (December 2024). The Graph
  API only exposes accounts you own or business accounts you manage.
* Open-source tools (e.g. Instaloader, MIT, actively maintained as of 2026)
  work by logging in a real account or hitting logged-out endpoints that
  Instagram rate-limits and ToS-prohibits; the engine spec explicitly forbids
  bypassing platform access controls, so they are not used.

What works instead: the CSV import path (python3 -m marketing.osint import
--prospects FILE) ingests public business emails/links that the owner copies
by hand from public Instagram business profiles while browsing normally.
"""
from __future__ import annotations

from .base import BaseCollector, CollectorStatus, DiscoveryContext

REASON = (
    "Instagram ToS prohibits automated collection; no public API since Basic "
    "Display API shutdown (Dec 2024); manual CSV import supported instead"
)


class InstagramCollector(BaseCollector):
    name = "instagram"
    live = False

    def discover(self, ctx: DiscoveryContext) -> tuple[list[dict], CollectorStatus]:
        return [], self.stub_status(REASON)
