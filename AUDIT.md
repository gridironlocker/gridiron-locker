# Gridiron Locker — Repository Audit Report
**Date:** 2026-09-18 (UTC) — branch `arena/01a0b668-gridiron-locker` @ `64dbf89`
**Auditor:** Senior Software Architect / AI Product Engineer (Arena Agent)
**Scope:** Full repository — public storefront `site/`, generators `src/`, data `data/`, marketing `marketing/`, ops `ops/`, CI `.github/workflows/`, assets, config

---

## 1. Inventory — What Exists Today

### Public storefront (`site/`)
- **206 HTML files** (197 public + 9 internal) — verified via `qa_audit.py`
- **108 sitemap URLs** = 84 product pages + 24 indexable pages; 85 retired-slug redirect stubs (noindex, not in sitemap)
- **4 collections:** Green Bay Packers (37), Michigan (18), Cleveland Browns (19), Dallas Cowboys (10)
- **Fulfillment split:** Viralstyle 47 / Mayzing 37 (Cleveland + Michigan migrated, Dallas/GB still Viralstyle via `data/fulfillment.json`)
- **1 creator collab:** `/michigan/joe/` (Joe's Michigan Locker, `data/creators.json`)
- **SEO surfaces:** buying guides (5), `/2026-season/`, `/fan-trend-index/`, `/drops/`, `/search/`, `/collections/`, `/guides/`, static pages (size-guide, shipping, FAQ, about, contact, trademark, privacy, 404)
- **Schema:** Organization, WebSite+SearchAction, CollectionPage, ItemList, Product+Offer (partner-scoped), BreadcrumbList, FAQPage, Article, Dataset — **0 invalid schema, 0 broken links** (validated daily)
- **Assets:** `site/assets/style.css` (copied from `src/style.css` per build), `site/assets/search-index.json` (live search), `site/assets/app.js` (search, filters, gallery, creator attribution cookie `gl_creator`, GA4 hand-off tracking), hero art (2048×768), per-product WebP galleries
- **Analytics:** GA4 `G-5RHGJSLZNG` — `shop_now_click`, `creator_attribution_set`, `custom_design_submit`, etc.

### Generators (`src/`)
| File | Role |
|------|------|
| `src/build.py` (4,902 LOC) | Single generator for every public page; reads `data/*`, `src/config.json`, `src/collections_data.py`, `src/catalog.py`/`auto_copy.py`, `data/trends.json`; writes `site/` + relativises for GitHub Pages project URLs |
| `src/collections_data.py` | `COLLECTIONS`, `ORDER`, `SEASON`, `NEXT_GAME` — single source of truth for 4 teams' branding, openers, headlines |
| `src/catalog.py` | Hand-written `CATALOG` facts (name/art/kw/theme) per slug — overrides `data/facts.json` |
| `src/auto_copy.py` | Fallback derivation for crawled slugs without hand-written facts |
| `src/trends.py` | Live headline fetcher (Google News RSS, no API key) → `data/trends.json` + `trend-report.md`; scoring: `HOT_MIN=3`, `FTI = 100 * mentions / peak` |
| `src/hunter_intelligence.py` | **Ladder:** HEADLINE→SIGNAL→TREND→OPPORTUNITY→ACTION; evidence from `data/trends.json` + `marketing/social-signals.json`; confidence weights (`volume 16 / sources 10 / fan_reaction 18 / recency 18 / velocity 14 / sentiment 8 / game_state 8 / commercial 8`), caps fan_reaction at 6 without connector |
| `src/drops_page.py` | `/drops/` renderer (benefit engine) |
| `src/scout.py`, `src/hq.py`, `ops/board/build.py` | Internal ops dashboards → `ops/scout/`, `ops/hq/`, `ops/board/` (copied to `site/ops/` per build) |
| `src/catalogue_contract.py` | Publishes `data/catalogue-live.json` (sellable designs) for marketing half |
| `src/crop_art.py`, `src/style.css` | Art derivation + source stylesheet |
| `src/config.json` | Domain `https://gridironlocker.store`, email b64, socials, IndexNow key |

### Data (`data/`)
- `data/products_live.json` (298 KB, ~84 live), `data/products.json` (251 KB stale crawl artefact, 113 slugs), `data/mayzing_products.json` + `data/mayzing_michigan.json` (Mayzing exports), `data/catalogue-live.json` (authoritative sellable), `data/collections.json`, `data/facts.json`, `data/content_dates.json` (stable sitemap dates), `data/delisted.json` (retired slugs), `data/fulfillment.json`, `data/creators.json`, `data/trends.json` (generated 2026-09-18, window 10d), `data/people.json`, `data/order.json`, `marketing/social-signals.json` (Google News + optional Reddit/X), `marketing/live_drops.json`, `trend-report.md`

### Marketing (`marketing/`)
- `marketing/plan.py`, `marketing/live_engine.py` (queue builders, respect delisted + ended campaigns), `marketing/commercial_agent.py`, `marketing/copy_vault.py`, `marketing/publisher.py` (API adapters dry-run), `marketing/three_day_pulse.py` → `marketing/three-day-pulse.json` + `marketing/dashboard.html`/`live.html`, `marketing/social_watch.py`, Pinterest feed, `marketing/REVENUE_PLAYBOOK.md`

### CI (`/.github/workflows/`)
- `deploy.yml` — pushes `site/` to GitHub Pages
- `refresh.yml` — **twice daily 06:15 & 15:15 UTC:** re-crawls Viralstyle (Mon), fetches headlines, re-scores trends, rebuilds, sanity gates (product count, sitemap, missing refs), publishes catalogue contract, runs guard-rail tests (non-blocking), commits+bases+pushes, deploys Pages, pings IndexNow/WebSub
- `health-check.yml` + `ops/health_check.py` — live-site checker (key URLs, sitemap, JSON-LD, artwork, freshness)

### Tests (`tests/`)
- `test_layout.py` (108 KB, ~145 guard rails), `test_catalogue_contract.py`, `test_hunter_intelligence.py`, `test_three_day_pulse.py`, `test_health_check.py`, `test_sitemap.py`, `test_commercial_agent.py`

---

## 2. Architecture Assessment

**Strengths**
- Single `src/build.py` is reproducible (UTC-pinned `TODAY`, deterministic sitemap dates via `data/content_dates.json`, no mtime dependence) and fully link-relativised for both custom domain + GitHub Pages project URL
- SEO discipline: unique title/meta/canonical/OG/Twitter per page, partner-scoped merchant schema (no invented shipping on Mayzing), no fake ratings, redirect stubs for retired slugs, relativise avoids duplicate `index.html` twins
- Trend pipeline is honest: counts mentions, flags gaps (trending with no design), never claims sales without feed
- Ops/monitor loop exists (refresh + health-check + Scout/HQ boards)

**Limitations / Tech Debt**
- **Monolith generator:** `build.py` ~4.9 kLOC does chrome (header/footer/hero/tickers), model (`build_model()`/`mayzing_item()`), page renderers (home/collection/product/guides/season/fti/drops), sitemap/robots/feed/llms/assets, relativise, sync. No separation between data, rendering, and publish phases — hard to extend without regression
- **No historical memory:** `data/trends.json` is overwritten each run; velocity is thresholded (`HOT_MIN`/`THROWBACK_MAX`) not tracked as trajectory; no snapshot log to answer “what happened last 5× this narratively accelerated?”
- **Static site only:** No server component — cannot host private authenticated surfaces, server-side filtering, or owner-only intelligence without exposing JSON via public static files (current `site/assets/search-index.json` + embedded FTI rows are public by design, but any richer intelligence would leak the same way)
- **Marketing generator divergence:** `marketing/plan.py` + `live_engine.py` duplicate catalogue logic vs `build.py` (historically read stale `data/products.json`; now mitigated via `catalogue-live.json` contract but still a second model)
- **Ticker/FTI source narrow:** 1 source (Google News RSS) — velocity is sparse; data/trends.json has no Reddit/X unless manually wired + secrets provided; no persistence of cross-platform spread

---

## 3. Bugs / Duplicated Logic / Findings

| Area | Finding | Severity |
|------|---------|----------|
| **Data hygiene** | `product-index.csv` (111 rows) is a stale hand-maintained export not written by any generator; disagrees with live catalogue (84) — documented in README as “not a build output” but still ships in repo | Low |
| **Retired asset guard** | `build.py:build_model()` correctly skips `DELIVERED`/`FUL_HOLD` but `src/seocopy.py` + `src/landing.py` still generate copy for delisted slugs if called directly | Low |
| **Workflows** | `refresh.yml` `continue-on-error: true` for tests means storefront can deploy with red guard rails (intentional trade-off documented, but masks real failures) | Medium |
| **Marketing ops** | `marketing/social-signals.json` is checked in with live Google News items but has no fan-community signal until Reddit/X tokens are set — board caps confidence at `FAN_REACTION_CAPPED=6` and never reaches ACTION (honest but invisible to owner without docs) | Medium |
| **Copy drift** | `src/collections_data.py` `SEASON[ckey].headline/status/result` are hand-edited season context, not derived from `data/trends.json` — can stale if not updated weekly | Medium |
| **Images** | New Viralstyle campaigns hot-link `assets.viralstyle.com` until `dl.py` runs; refresh only runs `dl.py` Mondays — mid-week new products render via supplier CDN for days | Low |

---

## 4. Security Assessment

| Area | Current state | Risk |
|------|---------------|------|
| **Internal dashboards** | `/ops/scout/`, `/ops/hq/`, `/ops/board/`, `/marketing/dashboard.html` are published to GitHub Pages as static files under `site/ops/` + `site/marketing/` with `noindex,follow` + `Disallow` in robots.txt but **no authentication** — obscure-URL only; anyone who guesses `/ops/scout/` gets FTI leaderboard, gaps, headlines, dead-campaign list | **High** (information disclosure; not exploitable for PII but leaks roadmap) |
| **Storefront** | Static, no secrets in client bundle except `CFG.email_b64` (base64, trivially decodable) + GA4 ID + `gl_creator` cookie (90-day, `SameSite=Lax`, not HttpOnly) — acceptable for public shop but not for private intelligence | Low |
| **Forms** | `assets/app.js` assembles FormSubmit `https://formsubmit.co/<b64-email>` client-side; honeypot only, no server-side CAPTCHA/rate-limit | Low (spam) |
| **No auth surface yet** | No private `/radar/` — so no credential storage issue yet, but also no path to secure it on GitHub Pages (Pages cannot host authenticated server logic) | **Architecture decision required** |
| **Headers** | No CSP, no HSTS, no `X-Frame-Options` — static Pages default; not critical for shop but would be for admin surface | Medium |
| **Secrets** | No `.env` committed; `requirements-dev.txt` only; social connectors use optional env (`X_BEARER_TOKEN`) but not wired to GitHub Secrets in workflows | OK |

**Conclusion:** Public storefront security posture is appropriate for a static hand-off shop. **Private intelligence cannot be hosted on GitHub Pages** — any static-file “password gate” would be trivially bypassable (client-side check, enumerated JSON, robots-ignored scan). Radar needs a separately deployable, server-authenticated application.

---

## 5. Performance

- **Build:** ~1–2 s locally; `dl.py` image fetch dominates (425 images, ~30–50 MB)
- **Pages:** 84 product pages, 1.18 KB avg HTML, hero `fetchpriority=high`, thumbnails lazy, `prefers-reduced-motion` respected, scroll-reveal gating avoids white-screen on JS failure
- **Lighthouse risks:** `site/assets/search-index.json` ~84 rows uncompressed; no image CDN/CDN cache headers (GitHub Pages default); no AVIF/WebP negotiation beyond downloaded WebPs; fine for 84 SKUs but not for 1k+ with current `src/style.css` bundle (86 KB)

---

## 6. Recommendations (Radar Prerequisites)

1. **Keep storefront static on GitHub Pages** (`deploy.yml` uploads `site/` only) — do not add server logic there
2. **Add Radar as a separate deploy** in `/radar/` (same repo, independent artifact) to an auth-capable host (Vercel/Render/Railway/Fly) — real server-side session auth, env secrets, no intelligence in public static files
3. **Introduce historical snapshot store** (per-run `data/trends.json` archive + `radar/data/history/*.json`) so velocity/acceleration/repetition are computed from trajectory, not single window count
4. **Unify catalogue contract**: marketing + Radar + storefront all read `data/catalogue-live.json` (derived from `build.ALL`) — never `data/products.json`
5. **Harden internal surfaces:** either gate `/ops/*` via Radar auth or remove from Pages artifact and serve only via Radar
6. **Document env/secrets model** and never commit `RADAR_*` credentials — see `radar/.env.example`

---

*This audit preserves the working storefront. Radar is an additive application per spec §1–§30; no public page URL, schema, or fulfilment hand-off is changed by its addition except where explicitly approved (e.g., approved products/SEO metadata promoted from Radar to storefront).*
