"""YouTube collector — official YouTube Data API v3 (legitimate, key-gated).

Uses the owner's own API key (env: YOUTUBE_API_KEY, the same variable the
existing marketing stack already supports). Without a key the collector
reports NO_KEY and does nothing — an honest status, never a bypass.

What it collects, all public via the official API:
* channels matching team keyword searches (search.list, type=channel);
* subscriber/video counts and description (channels.list);
* a business email ONLY when the channel itself publishes one in its public
  description with contact intent nearby — never guessed.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse

from .. import emails
from .base import BaseCollector, CollectorStatus, DiscoveryContext

API = "https://www.googleapis.com/youtube/v3"
_CONTACT_INTENT = re.compile(
    r"(?i)(business|contact|inquiries|inquiry|collab|sponsor|partnership|"
    r"advertis|booking|reach( me| us)?)"
)


def _extract_public_email(description: str) -> str | None:
    """Only an address the channel publicly publishes WITH contact intent."""
    if not description:
        return None
    for address in emails.extract_from_text(description):
        idx = description.lower().find(address)
        window = description.lower()[max(0, idx - 80): idx + len(address) + 80]
        if _CONTACT_INTENT.search(window):
            return address
    return None


class YouTubeCollector(BaseCollector):
    name = "youtube"
    live = True

    def __init__(self) -> None:
        self.key = os.environ.get("YOUTUBE_API_KEY", "").strip()

    def discover(self, ctx: DiscoveryContext) -> tuple[list[dict], CollectorStatus]:
        if not self.key:
            return [], CollectorStatus(
                name=self.name, state="NO_KEY",
                detail="set YOUTUBE_API_KEY to enable (official Data API v3, free quota)",
            )
        status = CollectorStatus(name=self.name, state="OK")
        records: list[dict] = []
        errors = 0
        for team in ctx.teams:
            data = ctx.keywords.get(team, {})
            queries = list(data.get("search_queries", []))
            for term in ctx.trend_terms.get(team, [])[:1]:
                queries.append(f"{term} channel")
            for query in queries[: ctx.max_queries_per_team]:
                if ctx.dry_run:
                    continue
                found, error = self._search(query, team, ctx)
                errors += error
                records.extend(found)
        # de-duplicate channels across queries/teams
        by_id: dict[str, dict] = {}
        for record in records:
            existing = by_id.get(record["platform_user_id"])
            if existing:
                merged_teams = list(dict.fromkeys(existing["teams"] + record["teams"]))
                existing["teams"] = merged_teams
                existing["team"] = merged_teams[0]
            else:
                by_id[record["platform_user_id"]] = record
        status.found = len(by_id)
        status.errors = errors
        if errors and not by_id:
            status.state = "ERROR"
            status.detail = f"{errors} API request(s) failed (check quota/key)"
        return list(by_id.values()), status

    def _search(self, query: str, team: str, ctx: DiscoveryContext):
        url = API + "/search?" + urllib.parse.urlencode(
            {
                "part": "snippet", "q": query, "type": "channel",
                "maxResults": ctx.limit_per_query, "key": self.key,
            }
        )
        response = ctx.fetcher.fetch(url, robots=False)
        if not response.ok():
            return [], 1
        try:
            payload = json.loads(response.text() or "{}")
        except json.JSONDecodeError:
            return [], 1
        channel_ids = [item["id"]["channelId"] for item in payload.get("items", [])
                       if item.get("id", {}).get("channelId")]
        if not channel_ids:
            return [], 0
        detail_url = API + "/channels?" + urllib.parse.urlencode(
            {"part": "snippet,statistics", "id": ",".join(channel_ids), "key": self.key}
        )
        detail_response = ctx.fetcher.fetch(detail_url, robots=False)
        if not detail_response.ok():
            return [], 1
        try:
            details = json.loads(detail_response.text() or "{}")
        except json.JSONDecodeError:
            return [], 1
        records = []
        for item in details.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {}) or {}
            channel_id = item.get("id")
            title = snippet.get("title") or ""
            if not channel_id or not title:
                continue
            description = snippet.get("description") or ""
            followers = _safe_int(stats.get("subscriberCount"))
            record = {
                "platform": "youtube",
                "platform_user_id": f"yt:{channel_id}",
                "username": snippet.get("customUrl") or title,
                "display_name": title,
                "profile_url": f"https://www.youtube.com/channel/{channel_id}",
                "website": None,
                "team": team,
                "teams": [team],
                "prospect_type": (
                    "PODCAST_MEDIA" if re.search(r"(?i)podcast", title + description)
                    else "FAN_CREATOR"
                ),
                "bio": description[:500],
                "source_url": detail_url,
                "followers": followers,
                "post_count": _safe_int(stats.get("videoCount")),
                "last_activity_at": None,
            }
            public_email = _extract_public_email(description)
            if public_email:
                record["public_email"] = public_email
                record["email_category"] = "PUBLIC_BUSINESS_EMAIL"
                record["contact_source"] = "published in public channel description"
                record["contact_source_url"] = record["profile_url"]
            records.append(record)
        return records, 0


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
