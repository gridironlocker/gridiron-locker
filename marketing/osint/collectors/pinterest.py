"""Pinterest collector — DISABLED (no legitimate automated access path).

* Pinterest's Terms of Service prohibit automated scraping.
* The official Pinterest API requires an approved developer app and only
  exposes the authenticated user's own boards/pins — there is no public
  creator/profile search endpoint for prospecting.

The existing marketing stack already plans Pinterest organically
(marketing/pinterest_feed.csv); prospect discovery stays manual-CSV-import.
"""
from __future__ import annotations

from .base import BaseCollector, CollectorStatus

REASON = (
    "Pinterest ToS prohibits scraping; official API has no public creator "
    "search; manual CSV import supported instead"
)


class PinterestCollector(BaseCollector):
    name = "pinterest"
    live = False

    def discover(self, ctx) -> tuple[list[dict], CollectorStatus]:
        return [], self.stub_status(REASON)
