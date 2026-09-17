"""Collector registry.

Each collector is independently enable/disable-able (spec: DATA SOURCES).
Platforms that cannot currently be accessed without violating their terms of
service ship as DISABLED stubs with the reason documented in code and in
../README.md — no bypass is ever implemented.

Environment toggles:

    OSINT_DISABLE_COLLECTORS=instagram,tiktok      # extra disables
    OSINT_ENABLE_COLLECTORS=podcasts,websites      # allow-list
"""
from __future__ import annotations

import os

from .base import BaseCollector, CollectorStatus, DiscoveryContext
from .podcasts import PodcastsCollector
from .websites import WebsitesCollector
from .news import NewsCollector
from .youtube import YouTubeCollector
from .instagram import InstagramCollector
from .tiktok import TikTokCollector
from .x_twitter import XCollector
from .pinterest import PinterestCollector

#: Order matters only for log readability.
ALL_COLLECTORS = [
    PodcastsCollector,
    NewsCollector,
    WebsitesCollector,
    YouTubeCollector,
    InstagramCollector,
    TikTokCollector,
    XCollector,
    PinterestCollector,
]


def enabled_collectors(selected: list[str] | None = None) -> list[BaseCollector]:
    disable = {
        name.strip().lower()
        for name in os.environ.get("OSINT_DISABLE_COLLECTORS", "").split(",")
        if name.strip()
    }
    allow = os.environ.get("OSINT_ENABLE_COLLECTORS", "").strip()
    allow_set = {name.strip().lower() for name in allow.split(",")} if allow else None
    out: list[BaseCollector] = []
    for cls in ALL_COLLECTORS:
        collector = cls()
        name = collector.name.lower()
        if selected and name not in {s.strip().lower() for s in selected}:
            continue
        if allow_set is not None and name not in allow_set:
            continue
        if name in disable:
            continue
        out.append(collector)
    return out
