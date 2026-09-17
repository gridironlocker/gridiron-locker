"""X (Twitter) collector — DISABLED (no sustainable free legitimate access).

* X's Terms of Service prohibit scraping or automated access outside the
  official API.
* The official API's search endpoints are not available on a sustainable
  free tier (the engine targets $0/month; the spec forbids paid APIs without
  explicit approval).

Manual CSV import is the supported path for public contact information the
owner copies from public X business profiles while browsing normally.
"""
from __future__ import annotations

from .base import BaseCollector, CollectorStatus

REASON = (
    "X ToS prohibits scraping; official search API requires a paid tier "
    "($0/month target, no paid APIs without approval); manual import supported"
)


class XCollector(BaseCollector):
    name = "x"
    live = False

    def discover(self, ctx) -> tuple[list[dict], CollectorStatus]:
        return [], self.stub_status(REASON)
