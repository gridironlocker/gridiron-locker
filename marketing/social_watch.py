#!/usr/bin/env python3
"""Collect public trend signals for the three-day marketing pulse.

The collector uses official APIs when credentials are configured and a small
public Reddit/Google News read for public discovery. It never scrapes private
accounts, stores direct messages, or pretends a disconnected platform was
observed. Missing credentials are a normal, explicit status in the output.

Environment variables (all optional):
  X_BEARER_TOKEN, META_PAGE_ID, META_PAGE_ACCESS_TOKEN, YOUTUBE_API_KEY

The output is intentionally a compact evidence layer, not a publishing queue.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "marketing" / "social-signals.json"
TIMEOUT = 15
USER_AGENT = "GridironLockerTrendWatch/1.0 (public trend research; contact via repository)"

TEAMS = {
    "cleveland-browns": {"label": "Cleveland Browns", "query": "Cleveland Browns"},
    "green-bay-packers": {"label": "Green Bay Packers", "query": "Green Bay Packers"},
    "dallas-cowboys": {"label": "Dallas Cowboys", "query": "Dallas Cowboys"},
    "michigan": {"label": "Michigan football", "query": "Michigan Wolverines football"},
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def request_bytes(url: str, headers: dict[str, str] | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def request_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(request_bytes(url, headers).decode("utf-8"))


def item(source: str, team: str, text: str, url: str = "", published: str = "", metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source": source,
        "team": team,
        "text": re.sub(r"\s+", " ", html.unescape(text or "")).strip(),
        "url": url,
        "published": published,
        "metrics": metrics or {},
    }


def google_news(team: str, query: str) -> tuple[str, list[dict[str, Any]], str | None]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    try:
        root = ET.fromstring(request_bytes(url, {"Accept": "application/rss+xml, application/xml"}))
        rows = []
        for node in root.findall("./channel/item")[:20]:
            rows.append(item("google_news", team, node.findtext("title", ""), node.findtext("link", ""), node.findtext("pubDate", "")))
        return "connected", rows, None
    except Exception as exc:  # network failures must not erase the last plan
        return "error", [], str(exc)


def reddit(team: str, query: str) -> tuple[str, list[dict[str, Any]], str | None]:
    url = "https://www.reddit.com/search.json?" + urllib.parse.urlencode({"q": query, "sort": "new", "t": "day", "limit": 15, "raw_json": 1})
    try:
        data = request_json(url, {"Accept": "application/json"})
        rows = []
        for child in (data.get("data", {}).get("children") or []):
            post = child.get("data", {})
            rows.append(item("reddit", team, post.get("title", ""), "https://www.reddit.com" + post.get("permalink", ""), str(post.get("created_utc", "")), {"score": post.get("score", 0), "comments": post.get("num_comments", 0), "subreddit": post.get("subreddit", "")}))
        return "connected", rows, None
    except Exception as exc:
        return "error", [], str(exc)


def x_recent(team: str, query: str) -> tuple[str, list[dict[str, Any]], str | None]:
    token = os.getenv("X_BEARER_TOKEN", "").strip()
    if not token:
        return "not_configured", [], "Set X_BEARER_TOKEN to use the official X recent-search API."
    params = {"query": f'({query}) -is:retweet lang:en', "max_results": "20", "tweet.fields": "created_at,public_metrics"}
    url = "https://api.x.com/2/tweets/search/recent?" + urllib.parse.urlencode(params)
    try:
        data = request_json(url, {"Authorization": f"Bearer {token}"})
        rows = []
        for post in data.get("data", []) or []:
            metrics = post.get("public_metrics", {})
            rows.append(item("x", team, post.get("text", ""), "https://x.com/i/web/status/" + post.get("id", ""), post.get("created_at", ""), metrics))
        return "connected", rows, None
    except Exception as exc:
        return "error", [], str(exc)


def facebook_page(team: str) -> tuple[str, list[dict[str, Any]], str | None]:
    page_id = os.getenv("META_PAGE_ID", "").strip()
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not token:
        return "not_configured", [], "Set META_PAGE_ID and META_PAGE_ACCESS_TOKEN for the official Meta Page feed API."
    params = {"fields": "message,created_time,permalink_url,shares,comments.summary(true),reactions.summary(true)", "limit": "20", "access_token": token}
    url = "https://graph.facebook.com/v20.0/" + urllib.parse.quote(page_id, safe="") + "?" + urllib.parse.urlencode(params)
    try:
        data = request_json(url)
        rows = []
        for post in data.get("posts", {}).get("data", []) or data.get("data", []) or []:
            rows.append(item("facebook_page", team, post.get("message", ""), post.get("permalink_url", ""), post.get("created_time", "")))
        return "connected", rows, None
    except Exception as exc:
        return "error", [], str(exc)


def youtube(team: str, query: str) -> tuple[str, list[dict[str, Any]], str | None]:
    key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not key:
        return "not_configured", [], "Set YOUTUBE_API_KEY to use the official YouTube Data API."
    params = {"part": "snippet", "q": query, "type": "video", "order": "date", "maxResults": "10", "key": key}
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
    try:
        data = request_json(url)
        rows = []
        for video in data.get("items", []) or []:
            snippet = video.get("snippet", {})
            video_id = video.get("id", {}).get("videoId", "")
            rows.append(item("youtube", team, snippet.get("title", ""), "https://www.youtube.com/watch?v=" + video_id, snippet.get("publishedAt", "")))
        return "connected", rows, None
    except Exception as exc:
        return "error", [], str(exc)


def unavailable(source: str, reason: str) -> dict[str, Any]:
    return {"status": "not_configured", "reason": reason, "items": []}


def main() -> None:
    generated = now()
    sources: dict[str, Any] = {
        "google_news": {"status": "pending", "items": [], "reason": None},
        "reddit": {"status": "pending", "items": [], "reason": None},
        "x": {"status": "pending", "items": [], "reason": None},
        "facebook": {"status": "pending", "items": [], "reason": None},
        "youtube": {"status": "pending", "items": [], "reason": None},
        "instagram": unavailable("instagram", "The Gridiron Locker Instagram account is disabled; no automation is attempted."),
        "tiktok": unavailable("tiktok", "TikTok publishing/research access requires an approved official app connection."),
        "pinterest": unavailable("pinterest", "Pinterest Trends access requires an approved official API connection."),
    }
    # src/trends.py already maintains a repository snapshot from the web. Keep
    # it as honest fallback evidence when a live request fails or is rate-limited.
    snapshot = json.loads((ROOT / "data" / "trends.json").read_text(encoding="utf-8")) if (ROOT / "data" / "trends.json").exists() else {}
    sources["repository_trend_snapshot"] = {"status": "snapshot", "generated": snapshot.get("generated"), "items": [], "reason": "Existing source snapshot; not a substitute for a live social connector."}
    for team, collection in (snapshot.get("collections") or {}).items():
        for headline in collection.get("headlines", []) or []:
            sources["repository_trend_snapshot"]["items"].append(item("repository_trend_snapshot", team, headline.get("title", ""), headline.get("url", ""), headline.get("pub", "")))
    for team, context in TEAMS.items():
        for source_name, getter in (
            ("google_news", lambda: google_news(team, context["query"])),
            ("reddit", lambda: reddit(team, context["query"])),
            ("x", lambda: x_recent(team, context["query"])),
            ("youtube", lambda: youtube(team, context["query"])),
        ):
            status, rows, reason = getter()
            sources[source_name]["status"] = status
            sources[source_name]["items"].extend(rows)
            if reason and not sources[source_name].get("reason"):
                sources[source_name]["reason"] = reason

    # The Meta Page feed is not team-search; capture it once per run when configured.
    status, rows, reason = facebook_page("all-teams")
    sources["facebook"]["status"] = status
    sources["facebook"]["items"].extend(rows)
    if reason and not sources["facebook"].get("reason"):
        sources["facebook"]["reason"] = reason

    all_items = [entry for source in sources.values() for entry in source.get("items", [])]
    payload = {
        "generated_at": generated,
        "window": "current public signals; source-specific lookback",
        "privacy": "Public discovery signals only. No direct messages or private account data are collected.",
        "sources": sources,
        "items": all_items,
        "summary": {"connected_sources": sorted(name for name, value in sources.items() if value.get("status") == "connected"), "item_count": len(all_items)},
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} · {len(all_items)} public signals · connected: {', '.join(payload['summary']['connected_sources']) or 'none'}")


if __name__ == "__main__":
    main()
