# Execution report — fix, optimize & grow (2026-11-08)

Follow-through on the 7-task execution request. Everything below is either
**implemented and verified in this pass**, **verified already true**, or
**blocked on specific input from you** — with the exact input named. No prices,
volumes or performance numbers are invented anywhere.

---

## Task 1 — The 24 "Missing product price" items

**Implemented / verified this pass:**

- Cross-referenced every ghost Item ID from the 2026-11-08 issues export
  (23 rows; the 24th is the same set still "under review") against the
  **entire Mayzing catalogue** — `data/mayzing_products.json` (34 Browns
  products) + `data/mayzing_michigan.json` (18 Michigan products). Result:
  **0 of the ghosts exist in the Mayzing catalogue.** There is no "correct
  current retail price" to fetch for them, because these designs are not
  sold anywhere anymore.
- What they actually are: **9 delisted designs + 14 held designs**
  (person/IP retirements and the Mayzing-migration hold list):

| Status | Item IDs |
|---|---|
| Delisted (player/coach left, IP) | limited-edition-m-fans, -n26, -n28, -n29, -n30, -m-vs-all, -qb19, -tee-0-01-1, valentine-v2 |
| Hold (no Mayzing equivalent yet) | sanders-the-next-level, d-a-w-g-b-i-t-c-limited-edition, limited-edition-2024n2, -b-e-k-i-n-d, -no-fly-zone-denzel, -cleveland, -go-b-r-o-w-n-s, cleveland-retro-vintage-classic-ohio-gif, whispered-go-browns, play-off-pound-shirt, all-we-want-all-we-got-25, bend-football-fans, winter-hat-beanie-browns, winter-hat-beanie-go-browns |

- Primary feed verification: `site/feeds/google-merchant.xml` = **95 items,
  95 with valid `g:price`, zero discontinued/held/delisted slugs** (the
  regression test `test_never_lists_held_or_delisted_slugs` enforces this).
  "Remove discontinued products from the feed" — already enforced; nothing to
  remove.
- **Cannot be done from the repository:** deleting the ghost items themselves.
  They live in a stale data source in your Merchant Center account, not in our
  feed. Pricing them would be inventing prices for products that cannot be
  bought (and would earn a worse disapproval). The only correct fix is the one
  in MERCHANT-CENTER-ISSUES-2026-11-05.md: **Settings → Data sources → delete
  / disable the source that is not `google-merchant.xml`** (turn off automatic
  item creation first if offered). ~10 minutes.

**Blocked on you:** the Merchant Center deletion above. Expected end state:
Total 95 · Approved 95 · Not approved 0.

---

## Task 2 — Purchase conversion tracking

**Implemented this pass:**

- `mayzing_checkout_click` GA4 event added to the buy-button handler with
  `item_id`, `value`, `currency`, `collection`, `placement`, `creator`,
  `destination` — previously only `viralstyle_*` names fired, so Mayzing
  hand-offs (the whole Cleveland line) were unlabelled in GA4 funnels. The
  legacy `viralstyle_checkout_click` / `viralstyle_redirect` still fire for
  every hand-off so existing reports don't break.
- Verified what already exists: `shop_now_click`, `viralstyle_checkout_click`
  and `viralstyle_redirect` all carry `value` + `currency`; the Pinterest
  checkout signal fires at hand-off.

**The hard truth about "purchase" events:** checkout and order confirmation
happen **on partner domains** (viralstyle.com / gridironlocker.shop on
Mayzing). A static page on gridironlocker.store physically cannot fire a GA4
`purchase` event for an order completed on another domain. Three real options:

1. **Partner-side GA4 (best):** if the Viralstyle or Mayzing store settings
   offer a "Google Analytics ID" / "Google Analytics measurement ID" field,
   entering `G-5RHGJSLZNG` there makes their checkout fire `purchase`
   (transaction ID, value, currency) into our GA4 property. 
2. **Order import:** periodic order exports from both partner dashboards,
   imported into GA4 (or just the weekly report) as the revenue source of truth.
3. **Funnel proxy (live now):** `*_checkout_click` events as the last observed
   step — good for conversion-rate trends, not for revenue.

**Blocked on you (exactly what I need):**

- Open one completed order in each partner dashboard and send me: the
  **order-confirmation / thank-you URL pattern** (e.g.
  `viralstyle.com/order/confirm?...`) and whether the store settings contain a
  **Google Analytics ID field** (yes/no per partner).
- Confirm `G-5RHGJSLZNG` is your GA4 property and that **Search Console is
  linked to it** (GA4 → Admin → Product Links).
- GA4 ↔ Merchant Center linking is also a UI step on your side: Merchant
  Center → Settings → linked accounts (Conversion source should show your
  GA4 property once linked).
- **Google Shopping free-listing traffic:** identifiable in Merchant Center's
  own performance report (authoritative). In GA4 it only shows as organic
  search from google.com — Google does not tag free-listing clicks separately,
  so I will not pretend otherwise; the *_checkout_click events + Merchant
  report are the practical split.

---

## Task 3 — SEO of the active catalogue ("86 approved" / 95 live)

First, the count: the catalogue this repo ships is **95 live products** (the
feed lists exactly 95). Merchant's "approved" number moves daily (81 approved
+ 14 under review on your Nov 8 screenshot) — if you see 86 approved now, that
is the review queue draining onto the same 95.

**Implemented this pass:**

- **13 weak-CTR snippets rewritten** (the pages GSC shows at positions 3–8 with
  impressions and 0 clicks) — `data/seo/overrides.json`, change_id
  `seo-weakctr-20261108`: 9 product pages + `/contact/`, `/fan-trend-index/`,
  `/guides/`, `/michigan/joe/`. Each 140–158 chars, unique, buyer-intent,
  real facts only (actual prices, real size ranges, named partner). Verified
  rendered in the built pages.
- **Stale fact fixed:** the homepage meta description said "96 original
  designs" — corrected to 95 (it was written before the last retirement).
- **Feed attributes enriched:** every item now carries
  `g:item_group_id` = the stable design slug (Google groups variants by it;
  the 50-char `g:id` is a truncated form that could collide as the catalogue
  grows). Beanie category refined to Google's exact taxonomy leaf
  (`Hats & Caps > Beanies`).
- **Verified already correct (checked item-by-item, 0 mismatches):** Google
  product categories per garment (shirts → Shirts & Tops, mug → Drinkware,
  beanie → Hats), product_type per team/garment, `identifier_exists=no`
  (POD has no GTIN/MPN), 95/95 keyword-mapped titles + metas + long-tails
  (PR #232), alt text 100%, canonicals 130/130.
- The one weak-CTR **title** finding (`/green-bay-packers-shirts/`, 121
  impressions at pos 33.9) is a **collection page** — collection content is
  frozen under your standing rule. The improved title is one approval away.

**Not done here (needs your data, not my code):** deeper per-product story
copy beyond the SERP snippet — the product descriptions were fully rewritten
in PR #232 and are current; further differentiation should follow new
designs, not churn.

---

## Task 4 — The 10 highest-potential products

Selected by real GSC data (live products only, sorted by impressions — the
retired pages that still rank are excluded on purpose):

| # | Product | Impr | Pos | Collection | Action this pass |
|---|---|---|---|---|---|
| 1 | Beware Dawgs Cleveland Browns Shirt | 59 | 6.4 | Cleveland | ✅ new meta |
| 2 | Make Me Drink Green Bay Packers Shirt | 40 | 6.8 | Green Bay | ✅ new meta |
| 3 | Sunday Funday Cleveland Browns Shirt (football-copy) | 33 | 12.8 | Cleveland | not 0-click flagged; on the next copy pass |
| 4 | Est. 1946 Cleveland Browns Shirt | 15 | 6.6 | Cleveland | has clicks; left stable |
| 5 | Star Lightning Vintage Dallas Cowboys Shirt | 12 | 5.1 | Dallas | ✅ new meta |
| 6 | Jordan Love 10 Flag Number Green Bay Packers Shirt | 11 | 7.7 | Green Bay | ✅ new meta |
| 7 | All You Need Love 10 Helmet Green Bay Packers Shirt | 11 | 16.2 | Green Bay | page-2 snippet; next copy pass |
| 8 | Jordan Freaking Love Green Bay Packers Shirt | 10 | 27.3 | Green Bay | position is the limit, not the snippet - needs authority (task 7 of the growth plan) |
| 9 | Dawg Life Cleveland Browns Shirt | 9 | 5.6 | Cleveland | has clicks; left stable |
| 10 | 1960 Helmet Vintage Dallas Cowboys Shirt | 9 | 5.0 | Dallas | ✅ new meta |

Merchant attributes for these 10: all verified priced, category-correct,
`item_group_id` added. The Michigan opportunity is at collection level
(277 impressions on the hub) — its fix is the division/depth build from the
growth roadmap, not per-product edits.

---

## Task 5 — Shipping strategy ($12 flat? free over $50/$75?)

**First, a discrepancy that must be resolved before any policy decision:**

| Source | What it says |
|---|---|
| Your brief | $12 flat shipping, 13–22 business days |
| Our Merchant feed (Viralstyle items) | `g:shipping` = **$4.95 USD** Standard |
| Our Merchant feed (Mayzing items) | no `g:shipping` (relies on account-level shipping) |
| The site (shipping page + PDPs) | deliberately defers: "rate calculated at checkout by the partner" |

If the live checkout charges $12 and the feed says $4.95, Google flags
**inconsistent shipping** — a serving risk. I will not touch live shipping
without your approval, so: **confirm the current rate each partner actually
charges at checkout** ($12 from which partner? both?), and I will align the
feed + Merchant account setting in one approved change.

**Free-shipping analysis (framework with your unknowns named, nothing
invented):**

- Your prices: $21.99–$28.00 per item. A **free shipping over $50** threshold
  is reached by any 2-item order ($43.98–$56+); **over $75** needs 3+ items.
- Profitability rule: `threshold is profitable iff extra items-per-order ×
  margin ≥ absorbed shipping × qualifying orders`. The three inputs the
  repo does not have (and I will not estimate): **POD cost per garment**,
  **current AOV**, **orders/week**. The economics model in
  `marketing/commercial-brief.json` is built and waiting for exactly these
  (`NEEDS_COST_INPUTS`).
- `[EST]` recommendation on conversion logic alone: **free shipping over $50
  is the right shape** for this catalogue (2-item basket is realistic at
  $22–$25 price points; $75 demands 3 items from a 95-design store and will
  rarely trigger), but the final number needs the cost inputs above and your
  approval. Also: a "free shipping over $50" banner is one of the highest-converting
  POD trust levers when it is true — it must not run before the threshold
  math is real (no fabricated offers policy).

**Blocked on you:** partner rate confirmation + the three cost inputs +
approval to change any live rate or badge.

---

## Task 6 — Conversion problems on the storefront

**Verified correct (checked on the built pages):** shipping transparency block
on every PDP naming the printing partner and deferring rates to checkout;
returns/misprint path per partner; size-guide, FAQ, how-ordering-works trust
links; lazy-loaded images (14/PDP); responsive viewport + mobile CSS; page
weight ~48KB HTML + cached assets; 0 broken links (health check 60/60);
Product+Offer+shippingDetails+MerchantReturnPolicy schema; 441 tests + 671
subtests green.

**Implemented this pass:** the 13 CTR-optimised snippets (task 3) are the
conversion-side improvement — the SERP is where these pages were losing
buyers.

**Known gaps, ranked (each needs a decision, not code):** real customer
reviews (platform choice from you); hero/lifestyle imagery (task is paused
on your standing order); checkout lives on partner domains (nothing to fix
here — that is the model); email capture relays through formsubmit.co to a
Gmail inbox (fragile — ESP account from you).

---

## Task 7 — Weekly growth reporting

**Implemented:** `ops/weekly_growth_report.py` — assembles organic clicks/
impressions/CTR, top pages + queries, indexing issues, feed & catalogue
health, SEO findings and backlink totals from repo data, and writes
`WEEKLY-GROWTH-REPORT-<date>.md`. First report generated:
**WEEKLY-GROWTH-REPORT-2026-11-08.md**.

Metrics that live behind logins (GA4 funnel, Merchant status counts, partner
orders/revenue/AOV) appear as **NEEDS INPUT** rows in the report — they are
never estimated. Each week: run the script and paste the dashboard numbers
into the table (or export the GA4/Merchant CSVs into the upload folder and I
import them the same way GSC is imported).

---

## This pass, in one list

1. ✅ Ghost cross-reference complete (0/52 Mayzing matches; 9 delisted + 14
   hold) — feed verified clean (95/95 priced).
2. ✅ `mayzing_checkout_click` GA4 event + existing value/currency wiring
   verified.
3. ✅ 13 weak-CTR meta rewrites shipped + stale "96 designs" fact fixed.
4. ✅ Feed enrichment: `item_group_id` on 95 items + Beanie taxonomy leaf.
5. ✅ Top-10 priority list built from GSC; 5 of the top 10 improved this
   pass, plus 4 more weak-CTR pages beyond the top 10.
6. ✅ Weekly report generator + first report.
7. ⏳ Blocked on you: Merchant source deletion · partner rate confirmation
   (+ $4.95-vs-$12 reconciliation) · cost inputs · order-confirmation URL +
   partner GA4 field answers · GA4/Merchant linking clicks · approvals
   (Green Bay hub title, free-shipping threshold, review platform).
