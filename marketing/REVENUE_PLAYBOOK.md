# Revenue Playbook — Live Drops System (Benefit-First)

This replaces the old "marketing dashboard only" approach. You complained: no life, not trend-catching, same caption repeated. Fixed.

## What we built (useful, reliable, money-making)

### 1. Public SEO page: /drops/
- **File:** `src/drops_page.py` → builds `site/drops/index.html`
- **What it is:** 24 live cards, each = trending headline + product + unique caption + price + image
- **Why it makes money:**
  - Ranks for "Shedeur Sanders shirt", "Browns roster shirt", "Michigan Miracle shirt" — real searches people do after news breaks
  - Fresh daily → Google loves fresh unique content
  - 0.95 priority in sitemap (highest), CollectionPage + ItemList schema
  - Filter chips + search, works on mobile
  - Example: "How long before Todd Monken turns to Shedeur Sanders..." → Sanders QB 12 shirt with caption "Here We Go Brownies isn't a chant, it's a survival skill..."
- **Nav:** Added to header + mobile menu, linked from homepage

### 2. Unique copy engine — no more repetition
- **Files:** `marketing/copy_vault.py` + `marketing/live_engine.py`
- **Old:** same template for all teams → spam signal, ignored
- **New:**
  - 20 openers per team, 15 hooks, 10 closers
  - Browns: Dawg Pound, Muni Lot, Lake Erie cold, Factory of Sadness, Bark
  - Packers: Cheesehead, Frozen Tundra, Lambeau, Go Pack Go, Titletown
  - Dallas: Star City, Doomsday, Texas swagger, Big D, Lone Star
  - Michigan: Go Blue, Maize vs Everybody, Bet, Big House, Maize out
  - Result: 100% unique Instagram, 100% unique X, 100% unique_copy = true
  - Each caption includes headline keyword for SEO

### 3. Pinterest traffic machine — 60 pins
- **File:** `marketing/pinterest_feed.csv`
- **What:** 60 rows, title ≤100 chars, description + "S-3XL, printed on demand, ships worldwide", board, tags, image URL, product URL
- **Example title:** "Sanders QB 12 Signature Shirt - Dawg Pound Game Day Outfit Idea | Cleveland Browns Fan Style"
- **Why benefit:** Pins live 3-6 months, drive search traffic, bulk upload ready. No API needed.
- **How to use:** Pinterest Business → Bulk Create → upload CSV

### 4. Live data pipeline — reliable, no API keys
- **Input:** `products_live.json` (the live catalogue) + `trends.json` (headlines, entity mentions, etc.)
- **Output:**
  - `marketing/live_drops.json` (24 items, score 100 top, with price, image, art, caption, headline)
  - `marketing/plan.json` (one record per live design, each with unique per-platform captions)
  - `marketing/pinterest_feed.csv` (60 pins)
- **No failures:** No Etsy API, no TLS, no "not_configured". First-party data only. If trends.json updates, page updates on next build.

### 5. Revenue dashboards
- **marketing/live.html** — NEW benefit dashboard (this file's companion)
  - Live KPIs, top 3 to post today, trending names, filterable 24 cards, copy buttons, Pinterest table
  - Action-oriented, not planning-oriented
- **marketing/dashboard.html** — existing planner now shows UNIQUE captions (fixed)
- **site/drops/** — public money page

## Daily workflow (4 steps, 10 minutes)

```bash
# 1. Update trends (you already have trends.json updating via your pipeline)
# 2. Regenerate live drops + unique copy
python marketing/live_engine.py

# 3. Rebuild site (includes /drops/ + new sitemap)
python src/build.py

# 4. Check
# - site/drops/index.html has 24 cards
# - marketing/pinterest_feed.csv has 60 rows
# - marketing/plan.json has unique_copy true
```

Then:
1. Post top 3 drops to IG/TikTok/FB/X using captions in `marketing/plan.json` or `live.html`
2. Upload `pinterest_feed.csv` to Pinterest
3. Link bio to `/drops/` — always fresh
4. Commit & push — GitHub Pages publishes

## Proof it's fixed

- Repetition: `python marketing/live_engine.py` prints `unique IG: 100%, unique X: 100%`
- Trend-catch: each drop-card shows `🔥 Browns announce initial 53-man roster...` as reason
- Dynamic: `live_drops.json` has `generated: 2026-09-08`, `trends_date: 2026-09-07`
- Public benefit: `site/drops/index.html` is 47KB, 24 cards, CollectionPage schema, not a dashboard
- Sitemap: /drops/ priority 0.95 daily (highest)

## Files changed/created

- src/drops_page.py (new)
- src/build.py (added page_drops() call, nav link /drops/)
- marketing/copy_vault.py (new, 20 openers per team)
- marketing/live_engine.py (new, headline→product matching + unique captions + pinterest)
- marketing/live.html (new, revenue dashboard)
- marketing/live_drops.json (24 drops)
- marketing/pinterest_feed.csv (60 pins)
- marketing/plan.json (regenerated with unique_copy)

## What to do next (real benefit)

- Add /drops/ to main nav CTA and Instagram bio today — it's the only page that is always trending
- Schedule 3 posts/day from live.html top 3 — they already have unique captions
- Bulk upload Pinterest CSV — 60 pins = 60 search entry points
- Set cron: `0 9 * * * cd /path && python marketing/live_engine.py && python src/build.py && git add . && git commit -m "daily drops" && git push`

This is reliable, useful, benefit-first — not just internal tools.
