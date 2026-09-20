# Gridiron Locker — Site Audit (deep)

**Date:** 2026-09-20 (UTC)
**Auditor:** Arena Agent (independent pass, not a re-run of prior audits)
**Production:** https://gridironlocker.store/ — verified serving the 2026-09-20 auto-refresh build (`last-modified: Sun, 20 Sep 2026 06:29:46 GMT`, `server: GitHub.com`)
**Local state:** this branch = `origin/main` @ `ef6e899` ("Auto-refresh: trends + rebuild 2026-09-20") + one copy fix (see §4)

---

## 1. Executive summary

The machine is healthy; the business is invisible. Every technical gate passes, the twice-daily automation works, production is fresh — **but the site has effectively zero search indexation one month after launch, the public GitHub repo outranks the store for its own brand name, and the two checkout hand-offs undermine the prices the storefront advertises.** The 2026-09-19 audit's critical IP finding is unchanged and both hero marks and player-name products remain live on **both** the storefront and the partner checkout.

| Severity | Count | Headline |
|---|---:|---|
| Critical | 2 | Near-zero search indexation; IP/policy conflict still live (unchanged from 09-19) |
| High | 3 | Public repo leaks the entire playbook (and outranks the store); checkout currency/title mismatch; internal intel still public |
| Medium | 6 | Season copy stale on game day; homepage image weight (w=1000 PNGs); drops queue drift worsening; generator copy garble (fixed here); unverified JOE10; no security headers (F) |
| Low | 4 | README factual drift; no UTMs on buy URLs; near-duplicate products & weak slugs (unchanged); long meta descriptions (unchanged) |

---

## 2. What I verified live today (new checks, not in prior audits)

| Check | Method | Result |
|---|---|---|
| Production freshness | response headers via securityheaders.com | Serving today's 06:29 UTC build ✅ |
| Search indexation | Bing `site:gridironlocker.store` | **0 URLs from the domain** — results are entirely unrelated pages ❌ |
| Brand visibility | web search "gridiron locker football shirts" | Store absent; **the public GitHub repo is the top result for the brand** ❌ |
| Viralstyle hand-off (`grb41`) | fetched campaign page | Campaign **is live** (README's "dead campaign" note is wrong) — but shows raw title "Limited Edition GRB41" and non-USD default (SR93.96 from this vantage) ⚠️ |
| Mayzing hand-off | fetched https://gridironlocker.shop/ | Live, 37 items — but priced in **NOK 209** (Norwegian krone) vs "$21" on the storefront, and it sells the same player-name products ("Bryce 19", "Denzel Rock Out") ⚠️ |
| Security headers | securityheaders.com scan | **Grade F** — no HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy; plus lax `access-control-allow-origin: *` (GitHub Pages default) ⚠️ |
| 404 experience | fetched non-existent URL | Good: branded "Fourth & Long" page, helpful links, consent banner ✅ |
| Internal intel leak | fetched `/marketing/commercial-brief.json` | **Still publicly downloadable** (646 KB, 81 chunks of strategy) ❌ |
| JOE10 | fetched `/michigan/joe/` | Still advertised, still unverified; partner site now banners "10% off all orders applied in cart" — relationship between the two claims is undefined ⚠️ |
| Homepage weight | parsed HTML | 21 remote Mayzing **PNG mockups at `w:1000`** on the homepage; the CDN honours a width param (the partner's own store uses `w:500`) — the single biggest untapped perf win ❌ |
| Copy determinism | `src/landing.py` | `pick()` is md5(slug+salt)-seeded → copy is stable across rebuilds ✅ (also means the copy bug below is stable and fixable once) |
| Repo's own QA | `qa_audit.py` re-run after rebuild | **TOTAL: 0** across all categories; 43/43 remote images on Mayzing CDN; 0 pages with un-hinted imgs ✅ |

## 3. Findings

### Critical 1 — The SEO-first store is not in the search index (business-critical)
Two independent probes agree: Bing holds **no pages** from the domain for `site:`, and a brand+category query surfaces only the GitHub repo, not the store. The whole operating model ("SEO storefront") is downstream of an index that hasn't materialised. The site is ~1 month old, has no backlinks I can detect, and no crawl-demand signals beyond sitemaps + IndexNow pings. Verification files for GSC (×2) and Bing are deployed — but there's no evidence anyone has read the coverage reports inside those consoles.

**Do next (this week):**
1. Open Google Search Console + Bing Webmaster Tools (they're already verified — files are live). Read **Coverage/Pages**: is this "Crawled – currently not indexed", "Discovered – not crawled", or blocked?
2. Expect the diagnosis to be *quality*: 83 template-generated pages with near-identical boilerplate ("The print process shapes…", "Lambeau weather is the filter…") and no external links. The fix is **fewer, better pages + first external links**, not more pages.
3. Seed crawl demand: 2–3 dofollow links from real profiles/communities (creator social bios, Reddit fan-community wikis where allowed, partner marketplace profiles), submit key pages manually in both consoles.
4. Track "indexed pages" as a KPI in the ops board — it matters more than any on-page tweak right now.

### Critical 2 — IP/policy conflict: unchanged, now confirmed on both storefronts
Verified today: hero art renders the Browns helmet mark, Packers "G", Cowboys star (I viewed `hero-home.jpg` directly), and 35 generated pages name/number players (Jordan Love, Bryce, Denzel). The same player products are also sold on `gridironlocker.shop`. This still contradicts `DESIGN-BLUEPRINT.md` §2 and the repo's own shipping gate, and `qa_deep.py` still reports the violations. **Owner/legal decision remains the blocker.** Options, in order of de-risking:
- **Delist the 14 player products + replace 5 hero arts** (safe, costs catalogue breadth in the short term), or
- **Pivot player pages to "moment" framing** (e.g. "Go Pack Go" chants, game results, fan rituals) with original art only, and 301 the player slugs to their collection pages, or
- Formally accept the risk in writing (not recommended; publicity rights + platform takedowns usually arrive at the worst time — e.g. the week sales start).

### High 1 — The public GitHub repo is a full intelligence leak (and it outranks you)
Search engines index `github.com/gridironlocker/gridiron-locker`. Publicly readable today: the entire growth strategy, fulfilment economics and split, revenue playbook, marketing agent internals, season plans, **and every audit document — including written admissions of the critical IP violations**. Any competitor (or rights-holder's counsel) can read the operation end-to-end.

**Do next:** move the repo to private (Pages requires a paid plan for private repos — cheap at this stakes level), or split: a minimal public repo (site output + deploy) and a private repo (docs, `data/`, `marketing/`, `ops/`, audits). At minimum, strip the audit/strategy/markdown corpus from the public repo and request removal of cached copies. This also partially mitigates the `/marketing/*.json` + `/ops/*` exposure on the storefront (still recommend removing those from the published artifact, as flagged on 09-19 — verified still live today).

### High 2 — Checkout hand-off contradicts the storefront's prices and names
- Mayzing path: storefront says **$21.00**, `gridironlocker.shop` shows **NOK 209** (from this vantage; if geo-based, US visitors may still see NOK as the default currency).
- Viralstyle path: storefront says **"Jordan Love 10 Packers Shirt — $24.99"**, campaign page shows **"Limited Edition GRB41"** with a non-USD default.

Price-shock at the moment of maximum intent is the most expensive conversion leak a hand-off store can have. **Do next:** check both partner dashboards for (a) store default currency → USD, (b) geo-currency widget, (c) campaign display titles matching storefront names. Verify from a US IP. This is a partner-settings fix, not a code fix — potentially the highest-ROI hour of the month.

### High 3 — Internal intelligence still published (unchanged)
`/marketing/commercial-brief.json`, `/marketing/plan.json`, `/ops/scout/*`, dashboards — all anonymously downloadable today (verified). `noindex` + robots Disallow are not access control. Remove them from the Pages artifact; keep them as CI artifacts or serve from an authenticated surface. 3.8 MB of strategy currently ships with every deploy.

### Medium 1 — Season freshness is manual where it matters most
Today (Sept 20) collection pages still say "Cleveland travels to Tampa Bay for Week 2" — the game kicks off **today at 17:00 UTC** (`NEXT_GAME` knows this; the hand-edited `SEASON.status/result/kickoff` fields don't). Tomorrow the whole site will be one day stale and nothing in the pipeline will fix it, because `trends.py` refreshes headlines but `SEASON` is human-edited. For a site whose entire pitch is *freshness*, this is the weak link.
**Do next:** derive `status`/`result` from a small structured feed (ESPN/NFL JSON or a 10-line scores API call) in the refresh workflow; fall back to the hand-edited values when the feed is down. Tests already pin headline/kickoff agreement — extend them to pin "no past-tense game described in future tense after kickoff+4h".

### Medium 2 — Homepage ships ~21 full-size PNG mockups
All Mayzing mockups are requested at `w:1000` PNG; the CDN accepts a width param (the partner's own storefront requests `w:500`). Combined with 371–441 KB hero JPGs (no `srcset`) and 86 KB unminified CSS, mobile LCP is likely 4–6 s. **Do next (in order of wins):** request `w:600` (or the CDN's WebP variant if supported) in `build.py`'s mockup URL builder — a one-line change; generate 800/1200/1600 WebP hero variants + `srcset`; minify `style.css`; self-host/subset fonts. Then measure with a real Lighthouse mobile run.

### Medium 3 — Drops queue is rotting faster
Build now discards **11 of 24** queued drops (yesterday: 8). The queue references campaigns that no longer exist upstream. **Do next:** prune `marketing/live_drops.json` to pages that exist; alert when the discarded count grows.

### Medium 4 — Generator copy garble (fixed in this branch) + template non-sequiturs
`src/landing.py` produced *"If that is the If JORDAN LOVE 10 is the read you wanted…"* on **18 product pages** (deterministic variant). **Fixed here** (§4). Also spotted: orphan sentences like "This design sits on that side of the fence." with no antecedent — worth a copy pass over `_story_*` variants; and the boilerplate story blocks are the likely "thin/duplicated" quality signal suppressing indexation (see Critical 1 — these two problems are the same problem).

### Medium 5 — JOE10 still unverified (unchanged), now with a twist
The partner storefront banners "10% off all orders applied in cart" — if that's automatic, JOE10 is redundant (fine) or double-discount risk (bad) or false (worse). Verify in the Mayzing dashboard, then either keep with terms ("stacks/expires X") or drop the claim.

### Medium 6 — No security headers (F grade, verified)
GitHub Pages can't set custom response headers. Practical mitigations without leaving Pages: put Cloudflare (free) in front of the domain for HSTS/nosniff/XFO/Referrer-Policy + caching; a basic CSP can also come from a `<meta http-equiv="Content-Security-Policy">` tag (limited but non-zero). Low urgency for a static shop, but it's a 30-minute fix at the DNS level.

### Low (unchanged or minor)
- **README drift:** says `limited-edition-grb41` is a *dead* campaign (it's live — I bought-nothing-but-verified today), says Mayzing 37 (build says 36), says some mockups hot-link Viralstyle (qa_audit: 43/43 now Mayzing). The README ranks for your brand — make it accurate or minimal.
- **No UTMs on buy URLs:** `shop_now` CTAs go out bare. Add `?utm_source=gridironlocker.store&utm_medium=product_page&utm_campaign={collection}` so partner analytics (and you) can attribute; also lets you A/B hero vs sticky CTA later.
- Near-duplicate products ("Cle Browns" ×3 at three colourways), weak slugs (`be-awar-of-dawg`), 3 long meta descriptions — all still open from 09-19, all cheap to fix once the indexation question is answered (deduping *before* you know what Google indexes risks throwing away equity; check GSC first).

## 4. Fixed in this branch (safe, verified)
- **`src/landing.py` — garbled story closer** ("If that is the If …") → regenerated the site: **19 product pages now read correctly**, 0 residual occurrences, `qa_audit.py` TOTAL: 0, build reproducible offline in ~1.5 s, diff surgical (product pages + deterministic dashboard/report churn only).

## 5. What I'd do next — priority order

**This week (blocking, mostly not code):**
1. Owner decision on player products + hero marks (Critical 2) — the longer it's live, the more indexable the exposure becomes.
2. Repo visibility: private or split (High 1). Remove `/marketing/` + `/ops/` from the published site.
3. GSC + Bing console read-out: what is actually indexed and why not the rest (Critical 1). Set "indexed pages" as the ops KPI.
4. Partner currency/title audit on Viralstyle + Mayzing from a US IP (High 2); verify JOE10 in the same sitting.
5. Automate SEASON result/status from a scores feed (Medium 1).

**This month (performance + resilience):**
6. `w:600` mockup URLs + hero `srcset`/WebP + minified CSS; real mobile Lighthouse before/after (Medium 2).
7. Cloudflare in front for headers (Medium 6); self-host Mayzing mockups or make remote-image failure blocking in the scheduled check (per 09-19).
8. Prune drops queue; dedupe near-dupes and fix weak slugs *after* the GSC read-out tells you what's indexed; UTMs on buy URLs.

**This quarter (strategy — my honest take):**
9. **Reduce catalogue, increase uniqueness.** 83 templated pages is a content-farm footprint in 2026's search climate; 30 genuinely distinct pages (real fan stories, real photos, creator collabs like Joe's — which is the best page on the site) will out-index and out-convert them.
10. **Don't depend on organic alone.** The Pinterest feed exists — activate it; seed 2–3 creator relationships like Joe's; the FTI/trend engine is genuinely differentiated — package it as a shareable weekly page others link to (that's your backlink strategy).
11. **Close the measurement loop.** GA4 sees `shop_now_click`, but nothing sees purchases. Even a weekly manual reconciliation of partner order counts (or their postback/API if offered) turns the ops boards from intelligence theatre into a P&L.

## 6. Limitations
No direct outbound network from the sandbox — all live checks went through the platform's page fetcher (which follows the same geo/vantage for every request). SERP results, currency defaults, and headers could differ from a US vantage; the currency finding in particular needs a US-IP confirmation. No real-browser Lighthouse/CLS/INP run, no screen-reader pass, no purchase transaction, no access to GSC/Bing consoles or GA4. The exhaustive link/schema/CTA crawl was re-run locally against today's build (`qa_audit.py` TOTAL: 0).
