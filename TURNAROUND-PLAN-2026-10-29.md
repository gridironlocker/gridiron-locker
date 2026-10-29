# Gridiron Locker — 30-Day Turnaround Plan

**Date:** 2026-10-29 · **Stance:** owner-investor · **Evidence base:** generated site (631 pages),
GSC imports (18 clicks / 651 impressions per 28d), CRO-AUDIT-2026-10-28.md, catalogue data,
and the research in GROWTH-PLAN-2026-10-26.md. Live partner checkouts and ad dashboards are
outside this sandbox — those items are marked **[operator]** and never assumed.

**The honest diagnosis in one line:** this is not a broken store — it is a *trustworthy store
that nobody visits and that cannot measure what little happens*. 651 impressions/28 days is a
traffic problem; the partner-handoff moment is a trust problem; the empty tag IDs are a blindness
problem. Design polish is not the bottleneck.

---

## 1. The 10 changes, ranked by likely effect on sales

| # | Change | Evidence | Effect on sales | Effort | Status |
|---|--------|----------|-----------------|--------|--------|
| 1 | **Get buying traffic: TikTok Shop US + daily short-form + fan communities** | 18 clicks/28d; TikTok Shop US = 6% fee + Made-to-Order listing type (3–14d handling) built for POD; FYP distributes by watch-time, not followers | The entire difference between ≈0 and real revenue | M (time) | **[operator]** plan in §4 |
| 2 | **Kill the partner-handoff trust cliff on-site** | CRO audit: trust opacity at the handoff moment = confirmed conversion risk; the store redirects payment to Mayzing/Viralstyle | Lifts every visitor who already exists | S | ✅ **shipped this pass** |
| 3 | **Turn measurement on (Pinterest Tag, Meta Pixel, GSC Validate Fix)** | src/config.json tag IDs empty; funnel is invisible; 2 stale 404s still awaiting validation | Makes every later dollar survivable; enables #10 | S (30 min) | **[operator]** §4 |
| 4 | **Q4 gift-season capture** | Gifting = the one guaranteed apparel demand wave; catalogue spans $19.99–$36.99 with size-proof options (mugs) | Seasonal revenue that exists only Nov–Dec | S | ✅ **shipped this pass** |
| 5 | **IP pivot: retire 14 player-identity designs → phrase/joke replacements** | qa_deep: 14 live products use player names/numbers/photography; Etsy research: best-sellers are zero-logo phrase designs ("Rebuilding Since 1964", Dawg Pound jokes) | Protects the store's existence on every ad/marketplace + the proven seller style | M | ⚠️ needs approval to delist; replacements queued |
| 6 | **One consistent offer story (fix the 7 partner-cart discount codes)** | CRO audit: 7 unverifiable promo codes sit in partner carts | Removes checkout whiplash; protects price integrity | S | **[operator]** (partner admin) |
| 7 | **Email lifecycle: welcome + gift-season + post-purchase-help flows** | Newsletter capture already ships (FormSubmit); no ESP, no flows | Repeat revenue; compounds with #1 | M | **[operator]** ESP choice; front-end exists |
| 8 | **Merchandise by demand: merge the 7 duplicate design clusters, curate hot lists from trend data** | 7 dup clusters dilute SEO and choice; drops page = data-limited (3 CLE slugs unpublished) | +conversion on the pages that get traffic | M | ⚠️ merging = delisting → approval |
| 9 | **Mobile buy-path polish: sticky Shop Now bar + size-confidence module on PDP** | Mobile is the majority of retail traffic (assumption, labeled); PDP CTA already instrumented by placement | Moderate lift on mobile shop_now_click rate | S–M | planned (needs visual QA on device) |
| 10 | **Paid amplification discipline: $100/$500/$1k ladder, winners only** | Research: Spark Ads boost organic winners; In-Feed $20/day min; never scale before tracking (#3) | Scales only what already works | n/a | gated on #3 |

**Why #1 outranks on-site work:** at ~1 visitor/day, even a 2× conversion lift rounds to zero.
**Why #2 and #3 still come next:** #1 without #3 burns money blind; #1 without #2 wastes the click.

---

## 2. What was implemented and verified in this pass (2026-10-29)

| Change | What shipped | Verification |
|---|---|---|
| #2 Trust cliff | **New `/how-ordering-works/`** — the canonical explainer: 3-step flow, who does what (Gridiron Locker vs Mayzing/Viralstyle), prices/shipping/discount truth, delivery estimates, returns + misprint path, order-help promise. Linked from **footer Help column ("How It Works")**, the **trust strip on homepage + collections**, **every PDP hand-off note**, and the **collection "How ordering works" block**. Article + FAQPage schema. | 422 tests + 670 subtests pass; qa_audit TOTAL 0; qa_http PASS; health 60/60 |
| #4 Gift season | **New `/guides/football-fan-gift-guide-2026/`** — budget-band picks computed from the live catalogue at build time (delisting-safe), team picks for all four fanbases (slogan/retro/funny only — no player-identity art promoted), gifting-without-size guide, honest "order early" estimates (no invented deadlines), gift FAQ. On the guides index; cross-links size guide, shipping, how-it-works. | same gate set; sitemap 128→130 (test changelog) |
| #2/#4 hygiene | trust-strip line, PDP micro-link, collection explainer link, footer entry — all additive; no existing titles, images or collection content changed (frozen-content constraint held). | tests pin the new link topology (`HowOrderingPage`, `GiftGuidePage`) |

Nothing above claims a fix to traffic or tracking — those are #1 and #3, operator-side.

---

## 3. Verified problems vs hypotheses

**Verified (data/code):** near-zero organic traffic (18 clicks/651 imp, GSC); page-1 only for
brand-ish terms; money keywords pos 20–40; brand SERP = GitHub, ~0 backlinks; measurement blind
(empty Pinterest tag, no Meta Pixel); 2 stale 404s in GSC (fix shipped, validation pending);
14 IP-risk designs; 7 dup clusters; 7 partner-cart promo codes; 82 hot-linked CDN images.

**Hypotheses (need the analytics from #3):** handoff drop-off magnitude per placement (north-star
`product_page_view → shop_now_click` exists but has no data); mobile vs desktop intent mix; which
design families convert; whether gift traffic converts better than team traffic.

---

## 4. 30-day plan

| Days | Actions | Priority | Impact | Difficulty | Success metric |
|---|---|---|---|---|---|
| **1–3** | Operator: Pinterest Tag ID → `src/config.json`; Meta Pixel; GSC **"Validate Fix"** for the 2 404s; open TikTok Shop US seller account (6% fee, Made-to-Order type). Verify `shop_now_click` fires with `data-placement` in GA4 realtime. | P0 | Unlocks everything | S | events visible per placement; GSC validation sent | 
| **4–7** | Email: pick an ESP, point the existing newsletter form at it; write 3 flows (welcome / gift-season / order-help). Fix the 7 partner-cart codes to one consistent policy **[operator, partner admin]**. Draft the 5 phrase/joke replacement designs for the IP-risk list. | P0 | Trust + retention base | S–M | 1 consistent offer story; 3 flows live |
| **8–14** | Ship the IP pivot (delist 14 — **needs your go** — and publish replacements). TikTok: post 5×/week using the search-proven phrases ("second act", "dawg life", "let him rip" energy), 3-second hooks, reply-as-video. First micro-creator seeding (product-for-post). | P0 | Revenue + survivability | M | 0 player-identity designs live; 10+ posts shipped |
| **15–21** | Acquisition experiments: TikTok Shop listings mirror the 4 collections; Spark-boost the best organic post ($20/day cap); join 3–5 fan communities (X, Reddit team subs) with value-first participation, not link spam. Gift guide promoted in bio/pinned. | P1 | First attributable sales | M | CAC measured; ≥1 attributable order |
| **22–30** | Read the north-star funnel by placement; kill what doesn't work; double down on what does. Curate drops/hot lists from real trend data (merge dup clusters — approval). Only now consider Meta retargeting ($20/day) and Google Shopping prep (feed). | P1 | Efficiency | M | conversion baseline per placement; next-month plan |

---

## 5. Where the first $100 / $500 / $1,000 goes

- **$100:** shipping costs for 2–3 micro-creator product-for-post deals (~$35 each) + one Spark-boost of the best organic TikTok. Nothing else.
- **$500:** creator seeding (8–10 micro creators) + Spark winners + TikTok Shop listing boosts. Still zero on Meta/Google.
- **$1,000:** + Meta retargeting **only after the pixel is verified** ($20/day), + TikTok Shop ads on the 2–3 listings with proven clicks. **Never** Google Shopping before feed + tracking exist — that is how you pay to learn nothing.

---

## 6. KPIs (current baselines; estimates labeled)

| KPI | Baseline (verified) | 30-day target |
|---|---|---|
| Organic clicks / 28d | 18 | 40+ (gift content + indexing) |
| `shop_now_click` / `product_page_view` | unknown (no data) | measured per placement (est. 8–15% target once visible) |
| Attributable orders | 0 | first ≥1, then trend |
| Email list | 0 collected to ESP | ESP wired, flows live |
| IP-risk designs live | 14 | 0 (pending your delist go) |
| GSC not-indexed stale 404s | 2 (fix live, unvalidated) | validated |

Revenue, AOV, CAC and ROAS cannot be honestly baselined — the store has no attributable sales and
no tracking. They begin at #3 and the plan reports them only once real.

---

## 7. Operator checklist (the only things code cannot do)

1. Pinterest Tag ID → `src/config.json` (`pinterest_tag_id` is empty).
2. Meta Pixel ID (none configured).
3. GSC → **"Validate Fix"** for the two September 404s (redirects already ship).
4. TikTok Shop US seller account + Made-to-Order listing type.
5. Partner admin: reconcile the 7 discount codes.
6. **Approve** the delisting of the 14 IP-risk designs (I queue the replacements first).
7. ESP choice for the newsletter (front-end already posts via FormSubmit).
8. FormSubmit captcha configuration (CRO-audit item).

---

*Constraints honored throughout: no fabricated reviews, discounts, scarcity or testimonials; no
pricing/payment/checkout changes; existing images/titles/collections untouched; Etsy and Merch by
Amazon permanently out of scope.*
