# Growth strategy audit — 14 priority areas (2026-11-08)

Audit of gridironlocker.store against the 14 growth areas, grounded in the
repo's actual state and the data we hold. Evidence rules, same as the rest of
this repo's report series: **verified numbers are cited with their source;
estimates are labeled `[EST]`; nothing is invented** — where a number does not
exist (search volumes, competitor prices, AOV, margins), this report says so
instead of guessing.

---

## 0. Baseline — what the data actually says

**Organic search (Search Console, export dropped 2026-11-05, imported verbatim
to `data/seo/gsc_export.json`):**

- 24 clicks / 1,037 impressions across 74 page rows and 107 query rows. The
  export does not record the date window it covered — re-export with the range
  noted before trend math.
- Best pages: home `/` 65 impr / 12 clicks / pos 6.0; `/michigan-wolverines-shirts/`
  277 impr / 0 clicks / pos 35.7; `/green-bay-packers-shirts/` 121 impr / 0 clicks /
  pos 33.9.
- Best queries: `gridiron cap locker` 8 clicks / pos 4.3 (branded); `michigan vs
  everybody shirt` 35 impr / pos 7.3; `gridiron fan gear` 14 impr / pos 11.9;
  `beware of dawgs` 3 impr / pos 8.7.
- Near-first-page (position 8–20): 13 queries but only 30 impressions — the
  volume sits on page 3–5 (`michigan shirts` 33 impr / pos 45.3, `green bay
  packers shirt` 41 impr / pos 39.7, `dearborn michigan t-shirts` 15 impr / pos 37.1).
- Indexing: 17 "alternate page with proper canonical" (Failed), 2 "crawled – not
  indexed" (Failed), 2 "Not found (404)" (Not Started — awaiting your Validate
  Fix click), 73 "discovered – not indexed" (Started), 0 duplicate (Passed).

**Off-site (site-explorer snapshot 2026-10-29, `data/seo/backlinks.json`):**
6 URLs with a total of **7 backlinks** — 6 point at `/cleveland-browns-shirts`,
1 at the `http://` homepage variant. Domain-wide link authority is effectively
zero; this is the single best explanation for money queries sitting at
positions 30–45.

**Store:** catalogue-live.json = **95 live products** (50 Mayzing / 45
Viralstyle), 130 sitemap URLs. ⚠️ The brief says "84 active products" — no repo
number matches 84 (feed = 95 items, Merchant = 81 approved + 14 under review).
Please tell me where the 84 comes from so the catalogue can be reconciled.

**Merchant Center (your 2026-11-08 screenshot + issues export):** 81 approved,
clicks +566% over 28 days; 23 ghost items "Missing product price" (retired
slugs from a stale source — deletion steps in
MERCHANT-CENTER-ISSUES-2026-11-05.md; the site side is fenced since PR #236).

**Tracking:** GA4 `G-5RHGJSLZNG` is installed site-wide with 11 custom events
(`product_page_view`, `shop_now_click`, `viralstyle_checkout_click`,
`viralstyle_redirect`, `collection_click`, `related_product_click`,
`colorway_interaction`, `custom_cta_click`, `custom_design_submit`,
`newsletter_signup`, `creator_attribution_set`). Outbound links carry UTMs
(`utm_source=site`, `utm_medium=product_card|social`, `utm_campaign={collection}`).
No purchase event exists — checkout completes on Viralstyle/Mayzing domains.

**Site surface:** 95 PDPs, 4 team hubs, 9 guides, 6 creator pages,
fan-trend-index, drops, 2026-season, search, FAQ, size guide, shipping,
how-ordering-works, trademark notice, privacy, contact. `llms.txt`, `feed.xml`,
`sitemap-images.xml` (234 images), Shopping-crawler robots fence on retired URLs.

**Prior art this audit builds on (do not re-do):** CRO-AUDIT-2026-10-28.md,
GROWTH-PLAN-2026-10-26.md, TURNAROUND-PLAN-2026-10-29.md (incl. §7 operator
checklist), KEYWORD-RESEARCH-2026-10-29.md, SITE-AUDIT-2026-11-08.md,
MERCHANT-CENTER-ISSUES-2026-11-05.md.

---

## 1. Low-competition, high-intent keyword research

- **Implemented:** KEYWORD-RESEARCH-2026-10-29.md covers head demand for the
  four teams, GSC-verified demand, relative trend signals (explicitly
  `[RELATIVE]`, no invented volumes) and deliberate non-targets. 95/95 products
  mapped in `data/seo/product_keywords.json` (primary + ≤4 secondary keywords,
  intent label per product). `seo_engine` pipeline keeps the map regenerable.
- **Missing / improve:** no refresh cadence (the map is a snapshot); local and
  gift-intent long-tail barely covered (`dearborn michigan t-shirts` gets
  impressions with only one guide targeting it); no competitor SERP-gap
  analysis; no volume tool — everything is GSC + relative signal.
- **Need from you:** nothing mandatory. Optional: a paid keyword-tool seat if
  you want vendor volume numbers (otherwise the "no invented volumes" rule
  stands and GSC remains the only quantified demand source).
- **I can implement:** quarterly map refresh from GSC + `data/trends.json`;
  query→page gap list; keyword briefs for every new page/design before it ships.
- **Your approval / manual action:** none.
- **Expected impact:** indirect but foundational — areas 2, 3 and 5 only
  target the right phrases because this map exists. Direct traffic effect is
  small on its own.

## 2. Product SEO and Google first-page ranking opportunities

- **Implemented:** full SEO rewrite shipped (PR #232): title tags with brand
  ≤60ch, unique titles casefolded, metas 140–158ch with real facts (price,
  sizes, partner), description hooks ≤42ch, Product+Offer+Breadcrumb JSON-LD on
  every PDP (627 blocks parse clean), canonicals 130/130, sitemap exact. A
  weak-CTR rule flags pages with impressions and zero clicks automatically.
- **Missing / improve:** the 14 weak-CTR opportunities from
  SITE-AUDIT-2026-11-08.md are **logged but unapplied** (waiting on you) —
  including PDPs sitting at positions 5–7 with real impressions
  (`limited-edition-cleveland-football-beware-of-the-dawgs` 59 impr / pos 6.4,
  `limited-edition-grb2` 40 impr / pos 6.8). The two biggest impression pages
  (Michigan hub 277, Green Bay hub 121) rank on page 3–5: meta alone will not
  fix that — they need authority (area 7) and depth (area 5).
- **Need from you:** your go-ahead for the 13 meta rewrites (product metas are
  generator-owned since #232 — standing note says wait for a go-ahead); an
  explicit un-freeze if the Green Bay hub title should change (collection
  content is frozen).
- **I can implement:** the weak-CTR pass via `data/seo/overrides.json` +
  rebuild + gates; query→page targeting tables; FAQ blocks where missing.
- **Your approval / manual action:** see above; nothing else.
- **Expected impact:** highest near-term organic lever. Pages at pos 5–7 with
  impressions and 0% CTR are being seen and rejected in the SERP; fixing the
  snippet is the cheapest available clicks. `[EST]` industry CTR curves say
  position 7→3 multiplies CTR several-fold — I will not put traffic numbers on
  it without measurement after the change.

## 3. Optimization of all active products

- **Implemented:** 95/95 products keyword-mapped and rewritten (titles, title
  tags, metas, descriptions, hooks); prices and availability in schema and
  feed; image alt 100%; unique-title and no-stale-slug regression tests; the
  feed is contract-tested (95 priced items, held/delisted slugs banned).
- **Missing / improve:** reconcile the "84" figure (I count 95 live PDPs / 95
  feed items / 81 Merchant-approved); the 14 weak-CTR items above; no
  per-product FAQ schema (hubs have FAQPage schema, PDPs do not); feed lacks
  `size`, `color`, `item_group_id` attributes (Google's apparel
  recommendations — warnings, not disapprovals).
- **Need from you:** the source of "84"; go-ahead for the weak-CTR pass.
- **I can implement:** weak-CTR pass; PDP FAQ blocks + schema; feed attribute
  enrichment (size range as `size` attribute, `item_group_id` per design);
  title/meta iteration after GSC data refreshes.
- **Your approval / manual action:** weak-CTR go-ahead.
- **Expected impact:** moderate and compounding — better SERP snippets now,
  better feed matching for Shopping over the next weeks.

## 4. Trending football team and player searches

- **Implemented:** real trend machinery already runs daily:
  `src/hunter_intelligence.py` → `trend-report.md` + `data/trends.json`
  (fan_trend_index 0–100, moments), live `/fan-trend-index/` page + home chips,
  Google News RSS ticker, `data/live_drops.json`, and a commercial brief
  (`marketing/commercial-brief.json`) with an opportunity model. Current index:
  #1 Shedeur Sanders 100, #2 Deshaun Watson 65, #3 Kyle Whittingham 52,
  #4 Micah Parsons 32. SEO policy already excludes what must not be targeted
  (KEYWORD-RESEARCH §5).
- **Missing / improve:** the loop is advisory only (it says "post this now" —
  nothing publishes); no moment-driven landing content; social posting is
  manual; player-name **merchandise** is an IP dead end (51 delisted designs
  and 66 held exist precisely because of player/coach IP) — demand for player
  terms cannot be served with product.
- **Need from you:** approval for trend-driven **content** pages (commentary,
  gift/roundup angles — no player-name products); your social execution, or an
  X API token for the existing integration.
- **I can implement:** game-week moment pages and "trend → product" modules on
  hubs (slogan/city-pride angles only); a weekly trend digest page; wire
  moments to the safe catalogue.
- **Your approval / manual action:** content-page go-ahead; any player-name
  design needs explicit IP sign-off (my recommendation stays no).
- **Expected impact:** spiky, event-driven traffic capture during game weeks;
  modest steady-state. Sales effect concentrates on Michigan/Cleveland where
  the trend index and the impressions both live.

## 5. Dedicated team and division collection pages

- **Implemented:** 4 team hubs (Cleveland, Green Bay, Dallas, Michigan) + the
  `/collections/` index + 4 team buying guides; FAQPage schema on hubs; hubs
  are already our two biggest impression pages.
- **Missing / improve:** **no division pages at all** (AFC North, NFC North,
  NFC East, Big Ten — nothing), no state/city hubs (Dearborn intent has
  impressions and one guide), no league-level landing; hub content is thin
  versus the queries it ranks for (`michigan shirts` at pos 45.3 for the
  Michigan hub means Google is not convinced the page answers the query).
- **Need from you:** nothing — new pages have always been allowed. Flag only:
  team names/logos stay out of imagery per the IP rules; division names in
  text are factual.
- **I can implement:** 4 division landing pages (their own URLs, sitemap,
  JSON-LD, interlinks to team hubs), a city/state guide expansion (Dearborn
  already proves the pattern), hub depth blocks (FAQ, size/fit, gift angles).
- **Your approval / manual action:** none for new pages; existing collection
  page content stays frozen unless you say otherwise.
- **Expected impact:** **high** — these pages target the exact queries that
  already show impressions (41 impr green bay packers shirt, 33 impr michigan
  shirts, 15 impr dearborn michigan t-shirts) and give the backlink campaign
  (area 7) something worth linking to.

## 6. Internal linking between products and collections

- **Implemented:** global nav to all hubs; breadcrumbs with BreadcrumbList
  schema; related-product rail on PDPs (with `related_product_click` events);
  cross-collection art pages (Oct 21 scaffolding); guides → hub links; home →
  everywhere; creator pages link their picks; search page + sitemaps.
- **Missing / improve:** no three-level silo (division → team → product)
  because division pages don't exist; guides don't deep-link to individual
  PDPs consistently; no "other teams" cross-module on hubs (fans of one team
  browse others — the drop-page pattern shows cross-team movement).
- **Need from you:** nothing.
- **I can implement:** silo links with the division build; guide→PDP deep
  links; hub cross-team module; footer link architecture review.
- **Your approval / manual action:** none.
- **Expected impact:** moderate–high and compounding; cheap to do and it
  multiplies the value of areas 5 and 7.

## 7. Backlinks and sports community partnerships

- **Implemented:** the site-explorer snapshot is imported and tracked
  (`data/seo/backlinks.json`); creator pages + attribution events give partners
  a landing point; trademark notice + guide/gift content gives outreach
  something non-salesy to link.
- **Missing / improve:** 7 total links, 0 on most pages — the root cause of
  positions 30–45. No prospect list, no outreach, no community presence
  (Browns Backers clubs, tailgate blogs, college fan forums, podcast show
  notes). One link hits the `http://` variant instead of `https://` (worth
  reclaiming).
- **Need from you:** **outreach is a human job** — I draft, you send from your
  name/accounts. Any budget for sponsorships/ads needs your call (link buying
  is off the table). Community accounts you already have (forums, Facebook
  groups, X) are the fastest channel.
- **I can implement:** prospect list from research; outreach email/DM
  templates; linkable-asset plan (size guide, gift guide 2026, fan-trend index
  as a data story); podcast/local-media pitch kit; the http→https link reclaim
  email.
- **Your approval / manual action:** sending outreach in your name; any spend.
- **Expected impact:** **high for competitive head terms, slow-burn** (weeks to
  months). Nothing else moves `michigan shirts` from position 45 to page 1.

## 8. Google AI search and shopping optimization

- **Implemented:** `llms.txt` present; robots.txt allows GPTBot / PerplexityBot /
  ClaudeBot; Product+Offer JSON-LD everywhere; Merchant feed with
  `identifier_exists=no`, partner-scoped shipping, price on 100% of items;
  free listings live and growing (81 approved, +566% clicks); Shopping
  crawlers fenced from retired URLs (PR #236) so ghost items can't refill.
- **Missing / improve:** the 23 ghost items await your source deletion;
  `llms.txt` is minimal (no product/FAQ digest); FAQPage schema exists on hubs
  but not on `/faq/`, guides or PDPs; feed lacks size/color/item_group_id;
  AI-overview traffic is not separately measurable in GSC (Google limitation —
  say so rather than pretend).
- **Need from you:** Merchant source deletion (the manual step); confirmation
  the account-level shipping service covers Mayzing items (the 50 Mayzing feed
  items carry no `g:shipping` and rely on it).
- **I can implement:** `llms.txt` expansion (catalogue digest, policies, FAQ);
  FAQPage schema rollout; feed attribute enrichment; Merchant feed polish
  (product_type taxonomy depth).
- **Your approval / manual action:** the two Merchant items above.
- **Expected impact:** moderate and rising — Shopping already sends the only
  measurable non-organic clicks; AI citations are unmeasurable but cheap to
  court.

## 9. Google Images and lifestyle product images

- **Implemented:** `sitemap-images.xml` (234 product images), alt text 100%,
  og:image + twitter cards per page, Googlebot-Image allowed, heroes exist for
  all hubs and creator pages.
- **Missing / improve:** product imagery is mockup-only (supplier mockups) —
  lifestyle/on-model imagery is the known image-CTR limiter; the hero-image
  refresh (realistic, IP-safe banners) is **paused on your standing order**;
  product images themselves are frozen; Pinterest claim verified but pinning is
  not running as a program.
- **Need from you:** resume/confirm the hero-image task; any real lifestyle
  photography you own (customer photos with permission = gold, but must be
  real); Pinterest posting decision.
- **I can implement:** the paused hero replacement the moment you say go
  (briefs already prepared: IP-safe, no official marks/logos/player numbers);
  alt-text refinement; Pinterest feed hygiene.
- **Your approval / manual action:** image freeze policy is yours — hero
  banners are the only currently un-frozen category and even that task awaits
  your restart order.
- **Expected impact:** moderate (image SERP + shopping CTR); lifestyle imagery
  is also the conversion lever in area 13.

## 10. Competitor pricing and promotional strategies

- **Implemented:** pricing is real and partner-sourced ($21.99–$45.99 retail
  across garments); the no-fake-discount policy is enforced by tests and
  review; `marketing/commercial-brief.json` has an economics model ready —
  with every input still null (`NEEDS_COST_INPUTS`).
- **Missing / improve:** no competitor price matrix; no promotional strategy
  (no codes, no bundles, no seasonal offers); AOV unknown; margin per garment
  unknown — so revenue-priority ranking today is necessarily qualitative.
- **Need from you:** unit economics (POD cost per garment from Viralstyle/
  Mayzing, platform fees, any order-value data from those dashboards); your
  approval for discount codes and where they may be applied (checkout-touching
  = approval-required per standing rule); named competitors if you track any.
- **I can implement:** competitor research + pricing matrix document; promo
  calendar draft (game days, holidays, drops); code mechanics documentation
  for the partner platforms; feed sale-price attributes when a real promo runs.
- **Your approval / manual action:** every live price/promo change; economics
  inputs.
- **Expected impact:** medium on conversion and AOV; also unlocks real
  break-even math for any future ad spend (TURNAROUND-PLAN §5).

## 11. New product designs based on actual demand

- **Implemented:** demand signals exist and are wired: GSC queries (Michigan +
  Green Bay demand is loud and unserved), fan_trend_index, `live_drops.json`,
  opportunity model in the commercial brief, and the Mayzing launch workflow
  (HOW-TO-ADD-A-DESIGN.md, `data/mayzing_products.json` → auto-enters the
  feed). IP governance is codified: delisted.json records 51 retirements with
  person/reason, hold list 66, trademark-notice page.
- **Missing / improve:** design production is the bottleneck — demand says
  Michigan depth and Green Bay depth, and both lines are thin; the loudest
  demand is player-driven and that is exactly the IP-walled area (Sanders
  terms, QB19, Vs Everybody — all retired/held on purpose); no design briefs
  exist against the safe slogan/city/wordmark space.
- **Need from you:** design execution (your Canva/designer/Mayzing uploads);
  explicit IP boundary confirmations for anything name-adjacent; which garment
  types to expand (hoodies/sweatshirts carry the Michigan queries).
- **I can implement:** demand-backed design briefs (query + trend evidence per
  brief, safe-angle list: slogans, city pride, colors, typography, vintage
  marks with no protected logos); pre-written titles/metas/keywords so a new
  design launches SEO-complete; launch checklists.
- **Your approval / manual action:** every design that ships; any IP-risk
  judgment call.
- **Expected impact:** **high for revenue** — impressions without product depth
  cannot convert. This is the biggest catalogue-side gap.

## 12. Technical SEO, auto-tagging and conversion tracking

- **Implemented:** technical audit clean (SITE-AUDIT-2026-11-08: titles/metas/
  canonicals 130/130, 627 JSON-LD blocks, 0 broken links, 499 stubs correct,
  health 60/60, 441 tests + 671 subtests); GA4 site-wide; 11 custom events
  covering the whole pre-checkout funnel incl. `viralstyle_checkout_click`;
  UTM auto-tagging on every outbound partner link; Bing + Pinterest verified;
  sitemaps + RSS feed; robots discipline (Shopping fence, AI crawlers allowed).
- **Missing / improve:** **true purchase conversion is invisible** — checkout
  completes on viralstyle.com / mayzing.com and neither is our domain; Mayzing
  handoff has no named checkout event (only the Viralstyle pair exists);
  whether `G-5RHGJSLZNG` is your property and GA↔GSC are linked is unverified
  from here; GSC validation is pending (404 ×2 "Not Started", alternate
  canonical ×17 "Failed"); no consent-mode or server-side tracking (static
  GitHub Pages can't do server-side).
- **Need from you:** confirm GA4 ownership/access and that Search Console is
  linked to it; the GSC "Validate Fix" click; periodic order exports from
  Viralstyle + Mayzing (the only source of truth for revenue); whether the
  Mayzing platform supports its own analytics/UTM acceptance.
- **I can implement:** Mayzing checkout-click event parity; UTM taxonomy
  extension (guide/drops campaigns); GSC issue fixes where repo-side;
  quarterly GSC re-import + weak-CTR refresh; a simple orders-tracking sheet
  format for your exports.
- **Your approval / manual action:** access + clicks above.
- **Expected impact:** measurement is a multiplier, not a line item — every
  other area's impact claim depends on it.

## 13. Customer trust, reviews and checkout optimization

- **Implemented:** PDP trust links (Shipping, Returns, Size guide,
  how-ordering-works), FAQPage schema on hubs, trademark-notice + privacy +
  contact pages, size selection before the partner handoff, the full CRO audit
  and its fixes (CRO-AUDIT-2026-10-28.md + scorecard work), and the standing
  no-fabricated-reviews/discounts/scarcity policy.
- **Missing / improve:** zero customer reviews anywhere (no platform, no
  import, no post-purchase ask); no payment-method/trust badges on PDPs;
  checkout itself is partner-hosted so our control ends at the handoff; the
  newsletter form relays through formsubmit.co to a Gmail inbox (fragile, and
  it is the only "account" surface we own).
- **Need from you:** a reviews-platform decision (Judge.me / Loox / Google
  Customer Reviews — several have free tiers but need your account and their
  policies respected; reviews must be real — no seeding); whether
  Viralstyle/Mayzing order emails can carry a review request (their templates,
  their rules).
- **I can implement:** trust-badge placement with factual copy only; PDP FAQ
  schema; "how ordering works" clarity improvements; review-collection flow
  design + on-site rendering the moment a real source exists.
- **Your approval / manual action:** platform signup; anything touching the
  checkout handoff.
- **Expected impact:** medium–high conversion — real social proof is the
  classic print-on-demand gap, but it can only be filled with real reviews.

## 14. Repeat purchases, loyalty and customer retention

- **Implemented:** "Join the locker" newsletter section (home) with GA4
  `newsletter_signup` events and a honeypot-protected form; drops page and
  creator attribution (return-visit hooks exist editorially).
- **Missing / improve:** no ESP — subscribers land in a Gmail inbox via a free
  relay with no welcome flow, segments, or campaigns; no loyalty/referral
  program; no repeat-purchase identification (checkout is on partner domains —
  we never see the customer); no win-back.
- **Need from you:** an email platform account (Mailchimp / Klaviyo / Brevo all
  have free tiers — your account, your billing relationship even at $0); the
  form destination change; your OK on the email voice/frequency promise shown
  ("one email a week").
- **I can implement:** ESP form integration; automation map (welcome → team
  segment → game-day → drop); team-preference capture (segment by the UTM
  campaign they arrived on); a loyalty page concept (referral code mechanics
  need partner support to redeem — document what's possible).
- **Your approval / manual action:** ESP account; privacy-page text review for
  the new processor.
- **Expected impact:** medium now, compounding forever — an owned list is the
  only channel immune to rankings/algorithm shifts; today the store has none.

---

## Prioritized execution roadmap (revenue impact first)

**P0 — this week (biggest effect per hour):**

| # | Action | Area | Owner | Why first |
|---|--------|------|-------|-----------|
| 1 | Merchant ghost-source deletion (Settings → Data sources) | 8/12 | you, ~10 min | the shopping surface must be 95/95/0 clean before anything else pushes traffic at it |
| 2 | Weak-CTR meta pass on 13 PDPs (+ Green Bay hub title if you un-freeze it) | 2/3 | me, on your go | pages at pos 5–7 with impressions are already visible and being rejected in SERPs |
| 3 | GA4 access confirm + GSC "Validate Fix" click + Mayzing checkout event parity | 12 | you + me | measurement floor; everything after this can be judged |
| 4 | Division hub pages ×4 + hub depth blocks + silo links | 5/6 | me | targets the 277+121+41+33+15 impressions already sitting at page 3–5 |

**P1 — weeks 2–3:**

| # | Action | Area | Owner | Why |
|---|--------|------|-------|-----|
| 5 | Backlink sprint: linkable assets + outreach kit, you send (hubs first) | 7 | me→you | only thing that moves positions 30–45; slow-burn so start now |
| 6 | Michigan + Green Bay design briefs (demand-backed, IP-safe angles), you produce | 11 | me→you | the store's biggest demand is unserved by the catalogue |
| 7 | Reviews platform decision + first real review flow | 13 | you→me | conversion gap on every PDP |
| 8 | ESP setup + welcome/game-day automations | 14 | you→me | start owning the audience |

**P2 — month horizon:**

| # | Action | Area | Owner |
|---|--------|------|-------|
| 9 | Trend-moment content pages for game weeks | 4 | me (approval per page batch) |
| 10 | Competitor price matrix + promo calendar (needs economics inputs) | 10 | me, after your inputs |
| 11 | AI surface expansion: llms.txt digest, FAQPage rollout, feed size/color attrs | 8/3 | me |
| 12 | Hero-image program restart (paused; resumes on your order) | 9 | me |
| 13 | Quarterly keyword + GSC refresh loop (calendarized) | 1/2 | me |

---

## Everything I need from you (consolidated)

**Data / access**
1. The source of "84 active products" (I verify 95 live PDPs / 95 feed items).
2. Confirm GA4 `G-5RHGJSLZNG` is yours and Search Console is linked to it
   (invite if you want me reading reports directly; otherwise keep pasting
   exports).
3. Unit economics: POD cost per garment, platform fees, and any AOV/order data
   from the Viralstyle and Mayzing dashboards (even rough, labeled as such).
4. Periodic order/revenue exports (monthly is fine) — the only revenue source
   of truth.

**Clicks (small, high value)**
5. Merchant Center: delete/disable the ghost data source
   (MERCHANT-CENTER-ISSUES-2026-11-05.md, updated steps).
6. Search Console: "Validate Fix" on the 2× 404 issue.

**Approvals / decisions**
7. Go-ahead for the weak-CTR meta pass; separately, the Green Bay hub title
   (collection content is currently frozen).
8. Reviews platform choice; ESP choice (both can be $0 tiers).
9. Discount codes: approve or reject for this season (checkout-touching =
   approval required).
10. Hero-image task: resume yes/no (it is paused on your standing order).
11. IP boundary confirmation for trend-led work: player/coach names on
    products stay banned unless you explicitly overrule (my recommendation:
    keep them banned).

**Human channel**
12. Outreach: say "yes, draft the outreach" and I will prepare every message;
    you send from your own accounts. Same for community participation
    (Browns Backers, fan forums, podcasts).
13. Social execution (or an X API token for the existing integration).

Everything not on this list, I can build from this repository without further
input — starting with roadmap P0 items 2 and 4 the moment you give the word.
