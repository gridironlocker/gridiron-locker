# Gridiron Locker promotion planner

This folder is a standalone, internal promotion-planning dashboard. It does not build or modify the storefront.

It now includes the **NFL Fan Commerce Marketing Agent** role: a commercial
trend-and-product decision layer, not just an SEO/content writer. The role
matches current signals to existing products, applies fan-psychology and
apparel-style lenses, creates a five-product daily predictor, builds a
pre-game runway, exposes POD-economics guardrails, and stops unsafe social
creative at the licensing gate.

## Separation contract

- `plan.py` reads `data/products.json`, `data/facts.json`, `data/order.json`, `data/trends.json`, and `SEASON` from `src/collections_data.py`.
- `plan.py` writes one generated file: `marketing/plan.json`.
- `commercial_agent.py` reads the plan and writes one generated file: `marketing/commercial-brief.json`.
- `performance-memory.json` is a human-maintained input, not an automatically invented analytics feed.
- Neither marketing script imports the website generator or writes anything under `site/`.
- GitHub Pages publishes the storefront in `site/` and the marketing planner at `/marketing/dashboard.html`.
- Scene prompts describe only mood, light, texture, composition, and environment. They do not request logos, team marks, player likenesses, or recognizable people.

## Run it

From the repository root:

```bash
python3 marketing/social_watch.py
python3 marketing/plan.py
python3 marketing/commercial_agent.py
python3 marketing/three_day_pulse.py
python3 marketing/publisher.py       # dry-run by default
```

`commercial_agent.py` writes `marketing/commercial-brief.json` from the plan
and trend snapshot. It also reads `marketing/performance-memory.json`, whose
empty seed is intentional: only measured learnings with a source should be
added. The brief labels Reddit, X, TikTok Creative Center, Instagram, YouTube,
Google Search/Trends, Pinterest Trends, competitor feeds, analytics, orders,
and POD cost data as unavailable until real connectors are added; it never
fabricates those signals.

The script validates the ordered catalogue and regenerates `marketing/plan.json` with every live design. It has no third-party Python dependencies.

To view the dashboard locally, serve the folder so the browser can fetch its sibling JSON file:

```bash
cd marketing
python3 -m http.server 8000
```

Then open <http://localhost:8000/dashboard.html>. Opening the HTML with `file://` can block the `plan.json` fetch in some browsers.

## Dashboard tabs

- **Post queue** — every design ranked by its “post this next” score, with searchable collection filters and copy buttons for all five platform packages.
- **3-day pulse** — the primary view. Each row gets its own creative angle (identity, news reaction, throwback, humor, gift, styling), hook, and platform-specific captions; angles, hooks, and products do not repeat within the horizon. It expires and regenerates from the latest web/social signals, with existing-product matches, fan emotion, trend evidence, captions, ad copy, image status, and compliance decision for today, tomorrow, and +2 days.
- **Product queue** — the catalogue fallback for browsing and reviewing existing designs. The older 14-day plan remains in `plan.json` for reference but is not the rolling publishing brief.
- **Best times** — practical starting windows for Instagram, TikTok, Facebook, X, and Pinterest in `America/New_York`.
- **Who's who** — current vs throwback player/coach context, so shared data is self-explanatory.
- **Opportunities** — the TREND-MASTER view: per-design opportunity score (0–100, weighted factors), evidence confidence, trend stage, opportunity type, decision (PUBLISH / IMPROVE / MONITOR / REJECT), the seven opportunity gates, and a social-compliance risk flag.
- **Commercial agent** — the NFL Fan Commerce Marketing Agent view: top five existing-product matches, fan motivation/emotion, design style, platform selection, SEO terms, hooks, timing, risk, game runways, A/B tests, and economics/conversion guardrails. It is decision support only and requires human approval.

## Live signal collection and publishing

`social_watch.py` checks public Google News and Reddit signals without a
credential, and uses official X, Meta Page, and YouTube APIs when the following
GitHub Actions secrets are configured: `X_BEARER_TOKEN`, `META_PAGE_ID`,
`META_PAGE_ACCESS_TOKEN`, and `YOUTUBE_API_KEY`. TikTok, Pinterest Trends, and
Instagram remain explicitly disconnected until their official app access and
policy/licensing requirements are satisfied. The collector writes
`social-signals.json` and records errors instead of claiming a source was read.

`three_day_pulse.py` converts those signals into `three-day-pulse.json`. It only
plans today, tomorrow, and +2 days, then chooses existing products and creates
platform-specific copy. Add owner-approved public image URLs by product slug to
`approved-images.json`; the publisher never invents or downloads an image.

`publisher.py` uses official APIs only and is a dry run by default. The
refresh workflow invokes it with `--publish`, but it remains a dry run unless
both repository variables `AUTO_PUBLISH=true` and `PUBLISH_APPROVED=true` are
set. Live mode also requires approved image URLs, clear compliance, and platform
credentials. Facebook Pages and Pinterest still-image publishing are supported
adapters; X, TikTok, YouTube, and Instagram are blocked until their required
official media/app flows are configured. Browser automation and password-based
posting are intentionally not supported.

## Timezone handling

All times in `plan.json` are authored in `America/New_York`. In the browser the dashboard converts them to the viewer’s device timezone (`Intl` resolved zone — `Africa/Casablanca` for the operator), anchoring each calendar post on its own plan date and each best-times window on the matching weekday inside the 14-day span, so DST shifts in either zone are respected. The source ET time is shown alongside every converted time, and posts that roll past midnight locally get a `+1d` badge. When the device is already on the plan zone, the dashboard shows the original plan times unchanged.

The conversion helpers live inline in `dashboard.html` between the `tz-helpers-start/end` markers. Verify them against known cases with:

```bash
node marketing/tz-verify.js
```
- **News gaps** — names present in the recent headline snapshot that do not have a catalogue design, plus copyable opportunity notes and source headlines.
- **Image prompts** — one mood-and-environment prompt per design and platform format, with prompt copy buttons.

## Score model

Scores start at 50 and are clamped to 0–100:

```text
50 base
+22 when the design matches a 2026 search term from SEASON[collection]["hot"]
+12 for each repeated recent headline mention of a named entity, capped at +30
 +6 when the facts theme is "playoff" or "player"
-25 when the design is a throwback
```

A named entity is joined to a design through the design name, art description, or keyword copy. The recent mention counts come from `data/trends.json`; a name must appear at least twice in that snapshot before its mentions count as repeated. A zero-mention named design is treated as throwback, matching the season-aware planning intent. An old-fashioned visual style by itself is not automatically a roster throwback.

Each queue item keeps a `score_breakdown`, matched 2026 search terms, matched headline names, and reasons so the score is inspectable rather than a black box.

## Plan JSON shape

The generated JSON contains:

- `meta` and `score_rules` — provenance, source files, platform list, and scoring constants;
- `season_context` — the current season status, opener, search terms, and legacy notes;
- `queue` — complete design records with product links, source image links, scores, breakdowns, five platform packages, and a TREND-MASTER `opportunity` record;
- `calendar` — legacy 14-day planner for reference;
- `three-day-pulse.json` — rolling three-day product/trend/copy brief refreshed from current signals;
- `social-signals.json` — source statuses and public trend evidence used by the rolling pulse;
- `best_times` — timing guidance used by the calendar;
- `news_gaps` — current uncovered names and recent source headlines;
- `image_prompts` — the prompt-only view used by the final dashboard tab;
- `who_is_who` — current vs throwback player/coach context from `data/people.json`;
- `opportunity_model` — the weighted factor model, decision bands, and evidence notes;
- `strategy` — per-collection trend stage, headline, and top opportunity;
- `compliance` — licensing status and the social-blocked / social-safe design counts.

Run the generator again after refreshing the four data snapshots or the season context. The output stays inside `marketing/` so planning updates cannot change the deployable storefront.
