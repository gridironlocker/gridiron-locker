#!/usr/bin/env python3
"""Publish approved three-day pulse rows through official platform APIs.

Default is a dry run. Live publishing requires BOTH AUTO_PUBLISH=true and
PUBLISH_APPROVED=true, an approved public image URL, and the platform's official
credential. No browser automation or credential storage is used.

This first adapter intentionally supports still-image publishing where the
platform API supports it (Facebook Pages, Instagram via Meta Graph API, and Pinterest).
X, TikTok, and YouTube need platform-specific media/OAuth/app approval and are reported
as blocked instead of being faked.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PULSE_PATH = ROOT / "marketing" / "three-day-pulse.json"
OUTPUT_PATH = ROOT / "marketing" / "publish-results.json"


def post_form(url: str, fields: dict[str, Any]) -> dict[str, Any]:
    body = urllib.parse.urlencode({key: value for key, value in fields.items() if value is not None}).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={"User-Agent": "GridironLockerPublisher/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "GridironLockerPublisher/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def facebook(row: dict[str, Any], image_url: str) -> dict[str, Any]:
    page_id = os.getenv("META_PAGE_ID", "").strip()
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    if not page_id or not token:
        return {"status": "not_configured", "reason": "META_PAGE_ID and META_PAGE_ACCESS_TOKEN are required."}
    try:
        response = post_form(f"https://graph.facebook.com/v20.0/{page_id}/photos", {"url": image_url, "caption": row["copy"]["captions"]["facebook"], "published": "true", "access_token": token})
        return {"status": "published", "response": response}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def pinterest(row: dict[str, Any], image_url: str) -> dict[str, Any]:
    token = os.getenv("PINTEREST_ACCESS_TOKEN", "").strip()
    board_id = os.getenv("PINTEREST_BOARD_ID", "").strip()
    if not token or not board_id:
        return {"status": "not_configured", "reason": "PINTEREST_ACCESS_TOKEN and PINTEREST_BOARD_ID are required."}
    pin = row["copy"]["pinterest"]
    payload = {"board_id": board_id, "title": pin["title"], "description": pin["description"], "link": row.get("product_url", ""), "media_source": {"source_type": "image_url", "url": image_url}}
    try:
        response = post_json("https://api.pinterest.com/v5/pins", payload, token)
        return {"status": "published", "response": response}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def instagram(row: dict[str, Any], image_url: str) -> dict[str, Any]:
    ig_user_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "").strip()
    token = os.getenv("META_PAGE_ACCESS_TOKEN", "").strip()
    if not ig_user_id or not token:
        return {
            "status": "not_configured",
            "reason": "INSTAGRAM_ACCOUNT_ID and META_PAGE_ACCESS_TOKEN are required to publish to @gridironlocker1 via Instagram Graph API.",
        }
    try:
        creation = post_form(
            f"https://graph.facebook.com/v20.0/{ig_user_id}/media",
            {"image_url": image_url, "caption": row["copy"]["captions"]["instagram"], "access_token": token},
        )
        container_id = creation.get("id")
        if not container_id:
            return {"status": "error", "reason": f"Container creation failed: {creation}"}
        published = post_form(
            f"https://graph.facebook.com/v20.0/{ig_user_id}/media_publish",
            {"creation_id": container_id, "access_token": token},
        )
        return {"status": "published", "response": published}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def unsupported(platform: str) -> dict[str, Any]:
    reasons = {
        "x": "X image publishing needs a user-authorized media upload connection; text-only automation is intentionally not enabled here.",
        "tiktok": "TikTok requires an approved Content Posting API app and video media; an image-only row cannot be auto-published.",
        "youtube": "YouTube requires an authorized video upload flow; an image-only row cannot be auto-published.",
    }
    return {"status": "unsupported", "reason": reasons.get(platform, "No official adapter configured.")}


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run or publish approved three-day pulse rows.")
    parser.add_argument("--publish", action="store_true", help="Attempt official API publishing; dry-run is the default.")
    args = parser.parse_args()
    pulse = json.loads(PULSE_PATH.read_text(encoding="utf-8"))
    live = args.publish and os.getenv("AUTO_PUBLISH", "false").lower() == "true" and os.getenv("PUBLISH_APPROVED", "false").lower() == "true"
    results = []
    for day in pulse.get("days", []):
        for row in day.get("opportunities", []):
            for platform in ("facebook", "pinterest", "instagram", "x", "tiktok"):
                image_url = (row.get("image") or {}).get(platform, "")
                result = {"date": day.get("date"), "slug": row.get("slug"), "platform": platform, "status": "dry_run"}
                if not live:
                    result["reason"] = "Dry run. Set AUTO_PUBLISH=true and PUBLISH_APPROVED=true only after reviewing the pulse and configuring official APIs."
                elif not image_url:
                    result.update({"status": "blocked", "reason": "No approved public image URL for this product/platform."})
                elif row.get("risk", {}).get("blocked"):
                    result.update({"status": "blocked", "reason": "Compliance gate is not clear."})
                elif platform == "facebook":
                    result.update(facebook(row, image_url))
                elif platform == "instagram":
                    result.update(instagram(row, image_url))
                elif platform == "pinterest":
                    result.update(pinterest(row, image_url))
                else:
                    result.update(unsupported(platform))
                results.append(result)
    payload = {"mode": "live" if live else "dry_run", "official_apis_only": True, "results": results}
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT_PATH} · {len(results)} platform actions · mode {payload['mode']}")


if __name__ == "__main__":
    main()
