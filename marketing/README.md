# Gridiron Locker promotion planner

This folder is a standalone, internal promotion-planning dashboard. It does not build or modify the storefront.

## Separation contract

- `plan.py` reads `data/products.json`, `data/facts.json`, `data/order.json`, `data/trends.json`, and `SEASON` from `src/collections_data.py`.
- `plan.py` writes one generated file: `marketing/plan.json`.
- It does not import the website generator or write anything under `site/`.
- GitHub Pages publishes the storefront in `site/` and the marketing planner at `/marketing/dashboard.html`.
- Scene prompts describe only mood, light, texture, composition, and environment. They do not request logos, team marks, player likenesses, or recognizable people.

## Run it

From the repository root:

```bash
python3 marketing/plan.py
```

The script validates the ordered catalogue and regenerates `marketing/plan.json` with all 134 designs. It has no third-party Python dependencies.

To view the dashboard locally, serve the folder so the browser can fetch its sibling JSON file:

```bash
cd marketing
python3 -m http.server 8000
```

Then open <http://localhost:8000/dashboard.html>. Opening the HTML with `file://` can block the `plan.json` fetch in some browsers.

## Dashboard tabs

- **Post queue** — every design ranked by its “post this next” score, with searchable collection filters and copy buttons for all five platform packages.
- **14-day calendar** — one featured design per day with platform-specific times, captions, hashtags, and copy buttons.
- **Best times** — practical starting windows for Instagram, TikTok, Facebook, X, and Pinterest in `America/New_York`.
- **Who's who** — current vs throwback player/coach context, so shared data is self-explanatory.
- **Opportunities** — the TREND-MASTER view: per-design opportunity score (0–100, weighted factors), evidence confidence, trend stage, opportunity type, decision (PUBLISH / IMPROVE / MONITOR / REJECT), the seven opportunity gates, and a social-compliance risk flag.

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
- `queue` — 134 complete design records with product links, source image links, scores, breakdowns, five platform packages, and a TREND-MASTER `opportunity` record;
- `calendar` — 14 days × five platform-specific scheduled posts;
- `best_times` — timing guidance used by the calendar;
- `news_gaps` — current uncovered names and recent source headlines;
- `image_prompts` — the prompt-only view used by the final dashboard tab;
- `who_is_who` — current vs throwback player/coach context from `data/people.json`;
- `opportunity_model` — the weighted factor model, decision bands, and evidence notes;
- `strategy` — per-collection trend stage, headline, and top opportunity;
- `compliance` — licensing status and the social-blocked / social-safe design counts.

Run the generator again after refreshing the four data snapshots or the season context. The output stays inside `marketing/` so planning updates cannot change the deployable storefront.
