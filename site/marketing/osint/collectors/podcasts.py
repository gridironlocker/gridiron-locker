"""Podcast collector — Apple iTunes Search API (public, documented, no key).

Why this source: the iTunes Search API is Apple's official, publicly
documented JSON endpoint intended exactly for third-party discovery. It
returns public directory metadata for podcasts matching team keywords:
name, author, website (via the public RSS feed), episode count, latest
release date.

Per-prospect enrichment, still public-only:
* the podcast's own public RSS feed (linked from the directory record) gives
  the channel description, the show website and the latest episode date;
* the ``itunes:owner`` email is published in that public feed by the show
  owner (Apple requires a real contact address there). It is imported with
  category PUBLIC_RSS_OWNER_EMAIL so a human reviewer can see the provenance
  before any outreach.

The API endpoint is a documented JSON API, so robots.txt is not the
applicable access contract (same convention the website crawlers use in
reverse); every other fetch (feeds, websites) IS robots-checked.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import xml.etree.ElementTree as ET

from .base import BaseCollector, CollectorStatus, DiscoveryContext

API = "https://itunes.apple.com/search"
NAMESPACE_ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

_JUNK_GENRES = {"Arts", "Business", "Comedy", "Education", "Health & Fitness",
                "History", "Leisure", "Music", "Society & Culture", "TV & Film"}


def build_queries(ctx: DiscoveryContext, team: str) -> list[str]:
    data = ctx.keywords.get(team, {})
    queries = list(data.get("search_queries", []))
    for term in ctx.trend_terms.get(team, [])[:2]:
        queries.append(f"{term} podcast")
    return queries


class PodcastsCollector(BaseCollector):
    name = "podcasts"
    live = True

    def discover(self, ctx: DiscoveryContext) -> tuple[list[dict], CollectorStatus]:
        status = CollectorStatus(name=self.name, state="OK")
        records: list[dict] = []
        errors = 0
        for team in ctx.teams:
            queries = build_queries(ctx, team)[: ctx.max_queries_per_team]
            for query in queries:
                if ctx.dry_run:
                    continue
                url = API + "?" + urllib.parse.urlencode(
                    {
                        "term": query,
                        "media": "podcast",
                        "limit": ctx.limit_per_query,
                        "country": "US",
                    }
                )
                try:
                    response = ctx.fetcher.fetch(url, robots=False)
                    if not response.ok():
                        errors += 1
                        continue
                    payload = json.loads(response.text() or "{}")
                except (json.JSONDecodeError, ValueError):
                    errors += 1
                    continue
                for item in payload.get("results", []):
                    record = self._record_from_api(item, team, url)
                    if record:
                        records.append(record)
        # RSS enrichment is done by the pipeline (shared with websites), but
        # feed URLs discovered here are attached so enrichment can use them.
        enriched, enrich_errors = self._attach_feeds(ctx, records)
        status.found = len(enriched)
        status.errors = errors + enrich_errors
        if not enriched and errors and not records:
            status.state = "ERROR"
            status.detail = f"{errors} API request(s) failed"
        elif enrich_errors and not errors:
            status.detail = f"{len(enriched)} podcasts; {enrich_errors} feed fetches failed"
        return enriched, status

    # ------------------------------------------------------------------
    def _record_from_api(self, item: dict, team: str, source_url: str) -> dict | None:
        name = (item.get("collectionName") or "").strip()
        collection_id = item.get("collectionId")
        if not name or not collection_id:
            return None
        artist = (item.get("artistName") or "").strip()
        genres = [g for g in (item.get("genres") or []) if g not in _JUNK_GENRES]
        bio = " — ".join(x for x in [artist, ", ".join(genres[:3])] if x)
        return {
            "platform": "apple-podcasts",
            "platform_user_id": f"itunes:{collection_id}",
            "username": artist or name,
            "display_name": name,
            "profile_url": item.get("trackViewUrl") or "",
            "feed_url": item.get("feedUrl") or "",
            "website": None,                     # filled from the public feed
            "team": team,
            "teams": [team],
            "prospect_type": "PODCAST_MEDIA",
            "bio": bio[:500],
            "source_url": source_url,
            "post_count": item.get("trackCount") or 0,
            "last_activity_at": (item.get("releaseDate") or "")[:10] or None,
        }

    def _attach_feeds(self, ctx: DiscoveryContext, records: list[dict]):
        """Fetch each podcast's public RSS feed for website/description/email.

        Kept bounded: one feed per prospect, robots-checked, rate-limited by
        the shared fetcher. Failures degrade to directory data only.
        """
        errors = 0
        for record in records:
            feed_url = record.pop("feed_url", None)
            if not feed_url or ctx.dry_run:
                continue
            response = ctx.fetcher.fetch(feed_url, robots=True)
            if not response.ok():
                errors += 1
                continue
            try:
                root = ET.fromstring(response.text())
            except ET.ParseError:
                errors += 1
                continue
            channel = root.find("channel")
            if channel is None:
                errors += 1
                continue
            link = channel.findtext("link") or ""
            if link:
                record["website"] = link
            description = (
                channel.findtext("description")
                or channel.findtext(f"{NAMESPACE_ITUNES}summary")
                or ""
            )
            if description:
                record["bio"] = f"{record.get('bio', '')} — {description}"[:500].strip(" —")
            owner_email = channel.findtext(f"{NAMESPACE_ITUNES}owner/{NAMESPACE_ITUNES}email")
            if owner_email and re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", owner_email):
                record["public_email"] = owner_email.strip().lower()
                record["email_category"] = "PUBLIC_RSS_OWNER_EMAIL"
                record["contact_source"] = "public RSS itunes:owner"
                record["contact_source_url"] = feed_url
            latest = channel.findall("item/pubDate")
            if latest:
                record["last_activity_at"] = latest[0].text
        return records, errors
