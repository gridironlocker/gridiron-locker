"""News collector — Google News RSS (public feed, same source as the repo's
existing trend system in marketing/social_watch.py).

Purpose: discover *who publishes* about our four teams. Each article's
publisher becomes a BLOG_WEBSITE / media prospect; the article itself is
stored as evidence. Major national publishers are skipped (outreach to ESPN
is not a prospect; an independent Browns blog is). The publisher's public
website is then enriched by the shared website step for contact data.
"""
from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET

from .base import BaseCollector, CollectorStatus, DiscoveryContext

FEED = "https://news.google.com/rss/search"

#: National/mega publishers that are not realistic prospects for a small
#: fan-apparel brand. Deliberately a small, conservative blocklist.
MAJOR_PUBLISHERS = {
    "espn.com", "nfl.com", "cbssports.com", "sports.yahoo.com", "yahoo.com",
    "foxsports.com", "nbcnews.com", "cnn.com", "nytimes.com", "apnews.com",
    "si.com", "bleacherreport.com", "profootballfocus.com", "usatoday.com",
    "washingtonpost.com", "theguardian.com", "bbc.com", "reuters.com",
    "abcnews.go.com", "msn.com", "aol.com", "news.google.com",
    "youtube.com", "facebook.com", "twitter.com", "x.com", "reddit.com",
    "instagram.com", "tiktok.com", "amazon.com", "wikipedia.org",
    "github.com", "medium.com",
}


def _registered_domain(url: str) -> str:
    from ..dedupe import registered_domain

    return registered_domain(url)


class NewsCollector(BaseCollector):
    name = "news"
    live = True

    def discover(self, ctx: DiscoveryContext) -> tuple[list[dict], CollectorStatus]:
        status = CollectorStatus(name=self.name, state="OK")
        records: list[dict] = []
        seen_domains: set[str] = set()
        errors = 0
        for team in ctx.teams:
            data = ctx.keywords.get(team, {})
            queries = [f"{data.get('label', team)} fan site", f"{data.get('label', team)} blog"]
            if ctx.trend_terms.get(team):
                queries.insert(0, f"{ctx.trend_terms[team][0]} {team} fan")
            for query in queries[: max(1, ctx.max_queries_per_team // 2)]:
                if ctx.dry_run:
                    continue
                url = FEED + "?" + urllib.parse.urlencode({"q": query})
                response = ctx.fetcher.fetch(url, robots=True)
                if not response.ok():
                    errors += 1
                    continue
                try:
                    root = ET.fromstring(response.text())
                except ET.ParseError:
                    errors += 1
                    continue
                for item in root.iter("item"):
                    source = item.find("source")
                    publisher_url = (source.get("url") or "") if source is not None else ""
                    publisher_name = (source.text or "").strip() if source is not None else ""
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    pub = (item.findtext("pubDate") or "").strip()
                    if not publisher_url or not publisher_name:
                        continue
                    domain = _registered_domain(publisher_url)
                    if not domain or domain in MAJOR_PUBLISHERS or domain in seen_domains:
                        continue
                    seen_domains.add(domain)
                    records.append({
                        "platform": "news-web",
                        "platform_user_id": domain,
                        "username": None,
                        "display_name": publisher_name,
                        "profile_url": f"https://{domain}/",
                        "website": f"https://{domain}/",
                        "team": team,
                        "teams": [team],
                        "prospect_type": "BLOG_WEBSITE",
                        "bio": f"publisher of: {title}"[:400],
                        "source_url": link or publisher_url,
                        "last_activity_at": pub or None,
                    })
        status.found = len(records)
        status.errors = errors
        if errors and not records:
            status.state = "ERROR"
            status.detail = "Google News RSS unreachable or robots-disallowed"
        elif not records:
            status.state = "SKIPPED"
            status.detail = "no independent publishers found for the selected team(s)"
        return records, status
