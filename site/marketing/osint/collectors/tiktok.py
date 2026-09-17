"""TikTok collector — DISABLED (no legitimate automated access path).

* TikTok's Terms of Service prohibit scraping and automated access without
  written permission.
* The Research API is restricted to approved academic/non-profit researchers;
  the Display API requires approved app scopes for content you own. Neither
  offers public creator search for commercial prospecting.

Manual CSV import is the supported path for public TikTok business contact
information the owner copies while browsing normally.
"""
from __future__ import annotations

from .base import BaseCollector, CollectorStatus

REASON = (
    "TikTok ToS prohibits scraping; Research API is restricted to approved "
    "academics; manual CSV import supported instead"
)


class TikTokCollector(BaseCollector):
    name = "tiktok"
    live = False

    def discover(self, ctx) -> tuple[list[dict], CollectorStatus]:
        return [], self.stub_status(REASON)
