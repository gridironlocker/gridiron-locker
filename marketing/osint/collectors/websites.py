"""Website collector — public websites only, robots.txt respected.

Two discovery paths, both bounded:

* curated seeds (seeds/websites.json) — fan communities and blogs the owner
  has vetted;
* website enrichment for any prospect that carries a website URL (podcast
  sites, news publishers found by the news collector).

Enrichment fetches at most the homepage + two contact-ish pages per site,
extracting only publicly published business emails, the site description and
public social profile links (for cross-platform matching — links are stored,
never crawled, because we do not scrape social platforms).

A robots.txt disallow, an unreachable host or a CAPTCHA/login wall simply
skips that site; no bypass is attempted, ever.
"""
from __future__ import annotations

import re
import urllib.parse

from .. import emails
from .base import BaseCollector, CollectorStatus, DiscoveryContext

_CONTACT_LINK_RE = re.compile(
    r"(?i)(contact|about|impressum|reach|connect|team|press)"
)
_SOCIAL_HOSTS = {
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "x.com": "x",
    "twitter.com": "x",
    "pinterest.com": "pinterest",
    "youtube.com": "youtube",
    "facebook.com": "facebook",
}
_MAX_CONTACT_PAGES = 2


def _absolute(base: str, href: str) -> str | None:
    try:
        joined = urllib.parse.urljoin(base, href)
    except ValueError:
        return None
    split = urllib.parse.urlsplit(joined)
    if split.scheme not in ("http", "https"):
        return None
    return joined


class WebsitesCollector(BaseCollector):
    name = "websites"
    live = True

    def discover(self, ctx: DiscoveryContext) -> tuple[list[dict], CollectorStatus]:
        from .. import config

        status = CollectorStatus(name=self.name, state="OK")
        records: list[dict] = []
        seeds = [
            seed
            for seed in config.load_seeds()
            if seed.get("team") in ctx.teams
        ]
        for seed in seeds:
            records.append({
                "platform": "website",
                "platform_user_id": seed["url"],
                "username": None,
                "display_name": seed.get("name") or seed["url"],
                "profile_url": seed["url"],
                "website": seed["url"],
                "team": seed["team"],
                "teams": [seed["team"]],
                "prospect_type": seed.get("prospect_type") or "BLOG_WEBSITE",
                "bio": seed.get("note") or "",
                "source_url": seed["url"],
            })
        status.found = len(records)
        if not records:
            status.state = "SKIPPED"
            status.detail = "no seeds for the selected team(s)"
        return records, status


def enrich_website(fetcher, record: dict) -> dict:
    """Crawl one public website for public contact data. Returns updates.

    This is the shared enrichment step the pipeline applies to every prospect
    that has a website URL, regardless of which collector found it.
    """
    updates: dict = {}
    website = record.get("website") or record.get("profile_url") or ""
    if not website.startswith(("http://", "https://")):
        return updates
    home = fetcher.fetch(website, robots=True)
    if not home.ok():
        return updates

    from ..http import parse_html

    parser = parse_html(home.body)
    blob = f"{parser.text[:1500]}"

    # public social profile links — recorded for dedupe, never crawled
    linked: list[dict] = []
    seen: set[str] = set()
    for href in parser.links:
        absolute = _absolute(home.url, href)
        if not absolute:
            continue
        host = urllib.parse.urlsplit(absolute).netloc.lower().removeprefix("www.")
        for social_host, platform in _SOCIAL_HOSTS.items():
            if host == social_host or host.endswith("." + social_host):
                path = urllib.parse.urlsplit(absolute).path.strip("/")
                handle = path.split("/")[0] if path else ""
                if handle and handle.lower() not in {"p", "channel", "c", "watch", "hashtag"}:
                    key = f"{platform}:{handle.lower()}"
                    if key not in seen:
                        seen.add(key)
                        linked.append({"platform": platform, "handle": handle, "url": absolute})
    if linked:
        updates["linked_profiles"] = linked

    # candidate contact pages
    contact_pages: list[str] = []
    for href in parser.links:
        absolute = _absolute(home.url, href)
        if not absolute:
            continue
        if urllib.parse.urlsplit(absolute).netloc != urllib.parse.urlsplit(home.url).netloc:
            continue
        tail = urllib.parse.urlsplit(absolute).path.lower()
        if _CONTACT_LINK_RE.search(tail) and absolute not in contact_pages:
            contact_pages.append(absolute)
        if len(contact_pages) >= _MAX_CONTACT_PAGES:
            break

    # email extraction: home page first, then contact pages
    candidates = emails.extract_from_page(home.body, home.url)
    for page in contact_pages:
        response = fetcher.fetch(page, robots=True)
        if not response.ok():
            continue
        page_candidates = emails.extract_from_page(response.body, page)
        for candidate in page_candidates:
            candidate["page"] = page
        candidates.extend(page_candidates)

    if candidates:
        best = candidates[0]
        updates["public_email"] = best["email"]
        updates["email_category"] = "PUBLIC_BUSINESS_EMAIL"
        updates["contact_source"] = "published on website contact page"
        updates["contact_source_url"] = best.get("page") or home.url

    if not record.get("bio") and blob:
        updates["bio"] = blob[:400]
    return updates
