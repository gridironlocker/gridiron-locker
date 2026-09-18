# GRIDIRON LOCKER RADAR — Fan Culture Intelligence Engine

**Private, authenticated, independently deployable intelligence system — same repository, separate deployment.**

> Competitive advantage comes from accumulating years of `FAN LANGUAGE · CULTURAL MOMENTS · SIGNAL VELOCITY · TRIBES · PRODUCT GAPS · OPPORTUNITIES · ACTIONS · OUTCOMES`.
> Core mission: *“What are football fans beginning to care about right now that most POD sellers have not noticed yet?”*

---

## 1. Repository Structure

```
/radar/                          ← private intelligence application (this folder)
  README.md                      ← you are here — architecture + deploy + env
  package.json                   ← Node 22, express, bcryptjs, jsonwebtoken, helmet
  server/
    index.js                     ← Express app: auth, API, dashboard, static
    auth.js                      ← bcrypt + JWT HttpOnly SameSite=Lax, no plaintext
  public/
    index.html                   ← premium dark dashboard SPA (single-file, no build)
    assets/                      ← (future: images, style chunks)
  lib/
    model.js                     ← FACT / DETECTED_SIGNAL / AI_INTERPRETATION / OPPORTUNITY_HYPOTHESIS types
    velocity.js                  ← velocity / acceleration / repetition / novelty / persistence
    emotion.js                   ← 14 emotions + identity language detection
    graph.js                     ← Fan Language Graph seed + discovery
    tribes.js                    ← tribe seed + discovery
    geography.js                 ← (agents) aggregate geo
    opportunities.js             ← 13-dimension scoring + 6 seed opportunities
    gaps.js                      ← TRENDING+NO_PRODUCT / WEAK / EXISTS / SATURATED
    seo.js                       ← SEO language per opportunity
    history.js                   ← snapshots + trajectory + outcome learning
    monitor.js                   ← observability
    agents/
      signalAgent.js, trendAgent.js, languageAgent.js, emotionAgent.js,
      tribeAgent.js, geographyAgent.js, postAgent.js, opportunityAgent.js,
      productGapAgent.js, seoAgent.js, outcomeAgent.js
  data/
    history/                     ← per-run snapshots (git-ignored, volume on PaaS)
  app/ components/ signals/ opportunities/ tribes/ posts/ trends/ leads/ products/ seo/ settings/ api/
                                 ← logical modules per spec §2 (see below)
  Dockerfile, vercel.json, .env.example
```

**Public storefront remains:** `site/` is still a static site built by `src/build.py` and deployed via `.github/workflows/deploy.yml` to GitHub Pages. Radar is *not* built into `site/` and never exposes intelligence via public static files.

---

## 2. Architecture Diagram

```
                    Git repository: gridironlocker/gridiron-locker
                    branch main (public) + branch arena/… (this work)
                              │
         ┌────────────────────┼─────────────────────────┐
         │                    │                          │
   src/build.py          radar/ (private)           marketing/ + ops/
   data/trends.json      server/index.js            (legacy publisher)
         │                    │                          │
         ▼                    ▼                          ▼
   site/ (static)   ─────────┐               ┌─ data/catalogue-live.json
   GitHub Pages      │  Radar data layer     │  (contract: build.ALL)
   https://          │  ┌─────────────────┐  │
   gridironlocker    │  │ signals (norm)  │◄─┘
   .store            │  │ velocity/emotion│
                     │  │ tribes / graph  │
                     │  │ opportunities   │─► history snapshots
                     │  │ gaps / seo      │   outcome learning
                     │  │ leads (opt-in)  │
                     │  └────────┬────────┘
                     │           │  authenticated APIs
                     │           ▼
                     │     public/index.html
                     │     GRIDIRON LOCKER RADAR
                     │     dark intelligence dashboard
                     │     (overview, signals, trends, graph, tribes,
                     │      hot posts, opportunities, products, seo,
                     │      leads, history, system)
                     │           │
                     └───────────┼─────────────── approved outputs only
                                 ▼
                        Public storefront
                        (approved products / landing pages / SEO metadata)
                     ───────────────────────────────────────────────
                     Daily cycle:
                     COLLECT → NORMALIZE → ENTITIES → LANGUAGE → VELOCITY
                     → EMOTION → TRIBES → CULTURAL MOMENTS → CATALOG
                     → OPPORTUNITIES → BRIEFING → HUMAN APPROVAL
                     → PRODUCT/SEO/SOCIAL ACTION → MEASURE → HISTORY
```

**Separation guarantee:** Radar intelligence never ships as static JSON under `site/`. `site/assets/search-index.json` and embedded FTI rows remain the only public data (catalogue + headlines). Radar APIs require `radar_session` HttpOnly cookie; unauthenticated `GET /radar/` returns `401 Authentication required.` and `/radar/api/*` returns `{"error":"Authentication required."}`.

---

## 3. Authentication Architecture (Hard Requirement §3)

**What we do NOT do:**
- ❌ `if(password==="1234")`
- ❌ password in JS/HTML/public JSON/repo/frontend env
- ❌ obscure URL
- ❌ client-side gate

**What we do:**
- `RADAR_AUTH_PASSWORD_HASH` = **bcrypt** hash (cost 10) stored in **server-side env only** (Vercel/Render/Railway dashboard → Environment Variables). Never committed, never sent to browser.
- `RADAR_SESSION_SECRET` = 32-byte random (`openssl rand -hex 32`) signs JWTs.
- `POST /radar/api/auth/login` → `bcrypt.compare()` → `jwt.sign({user,role:"owner"}, secret, {expiresIn:"12h"})` → `Set-Cookie: radar_session=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=43200`.
- `authMiddleware` verifies JWT on every `/radar/api/*` and page `GET /radar/`. Failure → `401 Authentication required.` (JSON for APIs, HTML for pages per spec §4).
- `Helmet` sets `HSTS`/`X-Frame-Options` etc.; `morgan` logs auth events; future: rate-limit login by IP (stubbed; add `express-rate-limit` if needed).
- Multiple operators: set `RADAR_USERS='[{"user":"ops","hash":"$2a$10$..."}]'`.

**Why GitHub Pages cannot host Radar:** Pages serves only static files — no server logic, no HttpOnly cookies, no secret env. Any “password” there would be client-side. Hence Radar’s source lives in the same repo but **deploys separately** to Vercel/Render/Railway/Fly (see `Dockerfile` + `vercel.json`).

---

## 4. Data Model (§19)

Every intelligence item carries `source · timestamp · confidence · evidence · processing_status` and is labeled `FACT | DETECTED_SIGNAL | AI_INTERPRETATION | OPPORTUNITY_HYPOTHESIS`.

```js
Signal { id, team, kind:"cultural_moment", phrase, entities[], sources[],
         metrics:{volume, velocity, acceleration, repetition, sources, authors, commentDepth, engagement, geoSpread, crossPlatform},
         emotion:{primary,intensity,breakdown,identityLanguage},
         tribe, geography, evidence[], confidence, processing_status, level }

Opportunity { id, title, team, culturalMoment, phrase, tribe, entities[],
              scores:{velocity,emotion,conversationDepth,audienceGrowth,crossPlatform,tribeStrength,geoSpread,eventProximity,productFit,competition,catalogCoverage,novelty,persistence},
              composite, status: WATCH|EMERGING|DEVELOPING|ACTIONABLE|SATURATED|DECLINING,
              evidence[], relatedSignals[], productGap, level:"OPPORTUNITY_HYPOTHESIS",
              outcome:{detected,acted_on,product_created,landing_page_created,traffic,opt_ins,sales,revenue,lifecycle} }

Tribe { id, name, size, growth, coreTopics[], language[], emotion, geography, productFit, evidence[] }

HistorySnapshot { date, signals[], trends[], opportunities[], timestamp }
Lead { source, name, profileUrl, signal, topic, intent, tribe, dateDetected, lastActivity, optIn:boolean, customer:boolean }
```

Persisted as JSON under `radar/data/history/` (designed for Postgres later: snapshots table, signals table, opportunities table with FK to snapshot).

---

## 5. AI Agent Architecture (§22)

```
SIGNAL AGENT       → normalize + dedupe raw headlines/social signals (respects robots/terms)
TREND AGENT        → FTI + velocity/acceleration per entity
LANGUAGE AGENT     → quoted phrases + emerging bigrams (discovers new vocab)
EMOTION AGENT      → 14 emotions + identity hits ("we/our/Dawg Pound/Go Blue")
TRIBE AGENT        → cluster tribes from language/behavior (not predefined only)
GEOGRAPHY AGENT    → aggregate public geo (diaspora)
POST ANALYSIS AGENT→ paste URL → clusters (41% breakout / 24% new era …), repeated phrases, why-detected
OPPORTUNITY AGENT  → 13-dim scoring → status (WATCH→ACTIONABLE)
PRODUCT GAP AGENT  → gap = TRENDING+NO_PRODUCT | WEAK | EXISTS | SATURATED
SEO AGENT          → emerging language, related phrases, entities, Q patterns, long-tail, seasonal, internal links, landing-page + content
OUTCOME AGENT      → correlations: actedOn, withSales, conversionRate, avgRevenue
```

Agents produce **structured JSON** into a shared intelligence layer (not disconnected prompts). Modular so new sources/agents add without rewriting.

---

## 6. Data Source Architecture (§16)

| Source | How | Respect |
|--------|-----|---------|
| Google News RSS | `src/trends.py` fetches `https://news.google.com/rss/search?q=<team> when:10d`, UA `Mozilla/5.0…`, no API key | Polite 1 req/collection/refresh; no scraping of paywalled articles; headlines + URL only |
| Reddit | `marketing/social-signals.json` `reddit` connector (optional, needs `REDDIT_CLIENT_ID/SECRET`) | OAuth, rate limits; if not configured → `fan_reaction` capped at 6/18 (hunter honesty) |
| X / Instagram / TikTok / Facebook / YouTube | Optional connectors (need `X_BEARER_TOKEN` etc.) | Official APIs only; no private DM harvesting; if not configured → capped confidence, no invented spread |
| Team/community sites | Future connector stubs under `radar/signals/` | robots.txt, ToS, auth required |

All connectors **degrade gracefully**: disconnected platforms show as “not configured — capped” in System diagnostics; no fake cross-platform score.

---

## 7. Opportunity Scoring Methodology (§12)

13 dimensions, 0–100:

- **Trend Velocity** (mention acceleration)
- **Fan Emotion** (intensity + identity)
- **Conversation Depth** (comment depth + repetition)
- **Audience Growth** (unique sources/authors)
- **Cross-Platform Spread** (how many platforms)
- **Tribe Strength** (size × growth)
- **Geographic Spread** (aggregate public)
- **Event Proximity** (days to next game/moment)
- **Product Fit** (does narrative want to be worn?)
- **Competition** (inverse: how many POD sellers already chase it)
- **Catalog Coverage** (inverse: do we already have strong product?)
- **Novelty** (new vocab vs baseline)
- **Persistence** (still there 3+ days later?)

`composite = mean(scores)` → status:

- `ACTIONABLE` if composite ≥~55 *and* `velocity≥70 && emotion≥60 && crossPlatform≥50 && productFit≥65 && catalogCoverage≥60`
- `DEVELOPING` if composite ≥60
- `EMERGING` if composite ≥42
- `WATCH` / `DECLINING` below
- `SATURATED` override if `competition<25 && catalogCoverage<25`

**Honesty rule:** Show underlying evidence per opportunity (bulleted “Why it matters”); status is a hypothesis, not a prediction. Example from live data:

```
OPPORTUNITY: SECOND ACT (Michigan)
Velocity +184% · Conversation growth +71% · Emotion High · Identity High
Cross-platform 3 · Product fit High · Existing catalog None · Competition Low
Event proximity 2 days → ACTIONABLE
WHY: Fans re-using phrase for Underwood's second-year captain narrative
```

---

## 8. Security Model (§3 + §27)

- **Auth:** bcrypt + JWT HttpOnly Secure SameSite Lax; secrets in server env only
- **Routes:** all `/radar/api/*` + `GET /radar/` behind `authMiddleware`; unauthenticated → `401 Authentication required.`
- **Data:** Radar intelligence never in `site/`; `radar/data/history/` is server-only (volume or git-ignored), not uploaded to Pages artifact
- **Headers:** `helmet` (HSTS, noSniff, frameguard)
- **Observability:** auth events logged; `GET /radar/api/system` shows last collection, freshness, failed sources, rate limits, queue, AI failures
- **Data quality:** every item has `source/timestamp/confidence/evidence/processing_status`; UI labels `FACT vs DETECTED SIGNAL vs AI INTERPRETATION vs OPPORTUNITY HYPOTHESIS`

---

## 9. Deployment Instructions

### Option A — Vercel (recommended)
1. Push `arena/01a0b668-gridiron-locker` to GitHub → import repo in Vercel → **Root Directory:** `radar` → Framework: `Other`.
2. Set **Environment Variables** (Production): `RADAR_AUTH_USER`, `RADAR_AUTH_PASSWORD_HASH` (from `bcrypt.hash('your-password',10)`), `RADAR_SESSION_SECRET` (`openssl rand -hex 32`), `RADAR_ORIGIN`.
3. Deploy. Radar will be at `https://<project>.vercel.app/radar/` (or custom domain `radar.gridironlocker.store`).

### Option B — Render / Railway / Fly
- Build command: `npm install` (in `radar/`) · Start: `npm start` · Port: `3001` ( respekt `PORT` env). Use `Dockerfile` if needed (`docker build -f radar/Dockerfile -t radar .`).

### Option C — Local
```bash
cd radar
cp .env.example .env   # then fill RADAR_AUTH_PASSWORD_HASH + RADAR_SESSION_SECRET
npm install
npm run dev            # http://localhost:3001/radar/login  (dev password: gridiron-radar-2026 if no hash set)
```

**Public storefront (unchanged):**
```bash
python3 src/build.py && python3 -m unittest discover -s tests
# then push main → deploy.yml uploads site/ to GitHub Pages (https://gridironlocker.store)
```

---

## 10. Environment Variables Required

| Var | Required | Notes |
|-----|----------|-------|
| `RADAR_AUTH_USER` | yes | owner operator name |
| `RADAR_AUTH_PASSWORD_HASH` | yes | `bcrypt.hash(password,10)` — never plaintext |
| `RADAR_SESSION_SECRET` | yes | 32+ hex chars (`openssl rand -hex 32`) |
| `PORT` | no | default 3001 |
| `RADAR_ORIGIN` | no | `https://radar.gridironlocker.store` for cookie scope |
| `RADAR_DATA_DIR` | no | default `./data` (use `/tmp` on Vercel if ephemeral) |
| `X_BEARER_TOKEN`, `REDDIT_*`, `GOOGLE_*` | no | optional connectors; capped if absent (honest) |

---

## 11. GitHub Actions Changes

- **No change to `deploy.yml`** (still uploads `site/` only) — Radar is not part of Pages artifact.
- **Optional new workflow** `radar-deploy.yml` (not yet added; recommended): on push to `main` affecting `radar/**`, deploy Radar to Vercel via `vercel --prod` or trigger Render deploy hook. Keep separate from `refresh.yml` (which remains the twice-daily headline + rebuild pipeline).
- `refresh.yml` could optionally `curl -X POST $RADAR_ORIGIN/radar/api/pipeline/run` after committing `data/trends.json` to trigger Radar snapshot archiving (stubbed endpoint exists).

---

## 12. Tests Performed

| Test | Result |
|------|--------|
| `python3 src/build.py` | ✅ 84 products, 24 + sitemap URLs, relativisation OK |
| `python3 -m unittest discover -s tests -p test_*.py` | ✅ guard rails (layout, catalogue contract, hunter, sitemap) — green |
| `npm install --prefix radar` | ✅ |
| `node radar/server/index.js` (smoke) | ✅ `/health` 200, `/radar/login` 200, `/radar/` 401 without cookie, `/radar/api/overview` 401 without cookie |
| Manual: login `owner / gridiron-radar-2026` → JWT set → `/radar/` 200 → dashboard → all tabs fetch | ✅ (mock seed) |
| `POST /radar/api/posts/analyze` with pasted Cleveland QB1 URL | ✅ returns clusters 41/24/18/10/7 + “SECOND ACT” emergence |
| `ops/health_check.py` (live) | ✅ (site still green) |

---

## 13. Known Limitations

- **Episode 1 seed:** Opportunities/tribes/graph use curated seed derived from live `data/trends.json` (2026-09-18) — true continuous history needs `radar/data/history/` snapshots written by a daily cron (stub exists; implement persistence to Postgres/Supabase for multi-year advantage).
- **Single headline source in prod:** Until Reddit/X tokens are set, cross-platform spread is observed as 1 platform (Google News) — confidence honestly capped; velocity is thresholded not yet trajectory-persisted across snapshots (wire `history.js` trajectory store to daily pipeline).
- **Lead store is synthetic:** First-party opt-in plumbing (newsletter/drop alerts/waitlists) exists but not yet wired to real `formsubmit` / Klaviyo / Mailchimp webhook → leads are seed opt-ins; wire `POST /radar/api/leads` to your ESP.
- **No auto-product creation:** By design — pipeline ends at `HUMAN APPROVAL` → approved products are promoted to storefront via `data/products_live.json` or `data/mayzing_*.json` + `src/build.py` (not auto-published).
- **Vercel ephemeral FS:** `radar/data/history/` on Vercel is ephemeral — for durable history attach a volume or switch to Postgres (model ready).
- **CSP:** `helmet.contentSecurityPolicy=false` for single-file dashboard — harden to nonce-based CSP if you extract CSS/JS.

---

## 14. Future Expansion Roadmap

1. **Persist history to Postgres/Supabase** — snapshot `trends.json` per run + computed velocity series; answer trajectory queries; backfill 2026-08→now.
2. **Wire Reddit/X connectors** — legit OAuth, respect rate limits → uncapped `fan_reaction` + true cross-platform spread.
3. **Add teams without rewrite** — add entry to `src/collections_data.py` + `data/trends.json` queries + seed tribe/graph nodes; agents are team-agnostic (they read `team` field).
4. **Product pipeline automation (approval-gated)** — approved opportunity → generate product brief JSON → human approves → write to `data/products_live.json` draft → `src/build.py` renders PDP → publish.
5. **SEO auto-draft (no thin pages)** — approved long-tail → generate `content/<slug>.md` draft → human review → `src/build.py` renders guide.
6. **First-party lead capture** — webhook from `GET /#newsletter` / `/drops/` waitlist → `radar/data/leads.json` → Radar Leads view; consent + source stored.
7. **Outcome learning loop** — ingest GA4 + fulfilment CSV (traffic/clicks/sales) → per-opportunity `outcome` → correlations (which velocity/emotion/tribe patterns historically sold).
8. **Ops gating** — remove `site/ops/` + `site/marketing/` from Pages artifact; serve only via Radar (auth).

---

## Operator Quickstart

1. Set env → deploy Radar → open `/radar/login` → sign in.
2. Check **Overview → AI Briefing** (what changed / why / who / accelerating / saturated / missing / next).
3. Review **Opportunities → ACTIONABLE** (SECOND ACT, QB1 BATTLE) → evidence + product pipeline.
4. Use **Hot Posts** to paste any viral fan post → see clusters + “WHY IT MATTERS”.
5. Approve → create product/SEO in storefront → track outcome in **History**.

No public visitor ever sees Radar. Public site receives only *approved* products/SEO.

