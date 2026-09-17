"""Collector interface shared by every data source module."""
from __future__ import annotations

from dataclasses import dataclass, field

#: States a collector can report. FAILED collectors are never hidden.
STATES = ("OK", "DISABLED", "NO_KEY", "ROBOTS_BLOCKED", "ERROR", "SKIPPED")


@dataclass
class CollectorStatus:
    name: str
    state: str                 # one of STATES
    detail: str = ""
    found: int = 0
    errors: int = 0

    def line(self) -> str:
        return f"{self.name}: {self.state}" + (f" ({self.detail})" if self.detail else "")


@dataclass
class DiscoveryContext:
    """Everything a collector needs: polite fetcher, keywords, teams, budget."""
    fetcher: object
    keywords: dict[str, dict]                       # team -> keyword dict
    teams: list[str]                                # selected team slugs
    trend_terms: dict[str, list[str]] = field(default_factory=dict)
    max_queries_per_team: int = 4
    limit_per_query: int = 5
    dry_run: bool = False


class BaseCollector:
    """Subclasses implement discover() and return (records, status)."""

    name: str = "base"
    #: True when the collector performs live network discovery (vs a stub).
    live: bool = False

    def discover(self, ctx: DiscoveryContext) -> tuple[list[dict], CollectorStatus]:
        raise NotImplementedError

    def stub_status(self, detail: str) -> CollectorStatus:
        return CollectorStatus(name=self.name, state="DISABLED", detail=detail)
