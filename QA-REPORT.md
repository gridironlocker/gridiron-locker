# Gridiron Locker — Technical, SEO & Content Audit + Fixes

**Date:** 2026-09-12 · **Branch:** `arena/01a0969c-gridiron-locker` · **Base:** `e904145` (current `main`)

Scope: audit *and fix*. GridironLocker.store stays the customer-facing storefront;
Viralstyle and Mayzing stay fulfillment/checkout partners only.

---

## 1. Canonical catalogue — one source of truth

Everything below is computed by `src/build.py` from the merged master catalogue
(`data/products_live.json` + `data/mayzing_products.json` + `data/mayzing_michigan.json`).
No count is hand-maintained anywhere.

| Collection | Designs | Partner | Buy host |
|---|---|---|---|
| Green Bay Packers | 37 | Viralstyle | viralstyle.com |
| Cleveland Browns | 19 | Mayzing | gridironlocker.shop |
| Michigan | 18 | Mayzing | gridironlocker.shop |
| Dallas Cowboys | 10 | Viralstyle | viralstyle.com |
| **Total** | **84** | **Mayzing 37 / Viralstyle 47** | |

Sitemap: **108 URLs** (84 products + 4 collections + 20 content pages).
Public pages: **194** audited. Redirect stubs: **85**.

Build output confirms: `catalogue: 84 designs across 4 collections, sizes S-5XL, Mayzing 37 / Viralstyle 47`.

> **Proof the single source of truth works:** this branch was rebased onto a `main`
> whose Michigan catalogue had grown from 15 to 18 designs. Every count above moved
> to the new totals on rebuild with **zero code edits** — homepage, nav, collection
> pages, SEO copy, footer, sitemap and both QA gates all followed automatically.

**Zero partner↔host mismatches** — every Mayzing product points at `gridironlocker.shop`,
every Viralstyle product at `viralstyle.com`, verified per-product against the catalogue.

---

## 2. What was fixed

### Fulfillment & copy accuracy
- Removed global "everything is Viralstyle" language; replaced with neutral
  partner wording. Shipping/return terms are now emitted per partner
  (`partner_offer_terms()` / `partner_ship_badges()`).
- Removed the Viralstyle `$4.95` shipping rate and 30-day misprint window from
  the **37 Mayzing** pages — those figures are unverifiable on Mayzing's storefront.
- `shippingDetails` / `hasMerchantReturnPolicy` schema now emitted for Viralstyle only.
- `/shipping/` rewritten partner-neutral; footer currency line defers to checkout.
- Removed "Printed on demand in the USA" (unverifiable global claim).
- Cleveland/Michigan garment labels left **verbatim** — "Men's T-Shirt" and
  "Classic Unisex T-shirt" match the live Mayzing storefront exactly.

### Counts (no hard-coded numbers)
- New catalogue-facts block (`N_DESIGNS`, `N_COLLECTIONS`, `COLLECTION_COUNTS`,
  `SIZE_RANGE*`) feeds homepage, nav, collection counts, SEO copy, footer and llms.txt.
- `ops/board` was stale at 129 → regenerated to **84**.
- **`ops/health_check.py`** asserted `>= 100` product URLs in the sitemap, so it
  *failed a complete build*. Now derives the expected count from `build.ALL` and
  asserts an **exact** match.
- **`.github/workflows/refresh.yml`** publish gate read `data/products_live.json`
  (113 rows, Viralstyle-only) as "the catalogue" and used a magic `< 100` floor.
  It now reads the merged master catalogue (84), requires the sitemap's product
  URLs to **equal** it, and rejects duplicate `<loc>` entries.
  Verified end-to-end: the gate reads 84 products / 108 URLs and passes.
- README / DEPLOY-GITHUB.txt corrected (they claimed 154 pages, 130 products,
  Cleveland 64 — all wrong), and now state that counts come from the build.

### Redirects (retired + migrated URLs)
- **85** retired URLs (31 delisted + 57 fulfillment `hold`) get stubs: meta-refresh,
  `location.replace()`, canonical to target, `noindex,follow`, full OG/Twitter,
  visible fallback link.
- No retired slug has a same-name active replacement, so each forwards to **its own
  collection page** — never the homepage.
- `site/_redirects` provides true 301s on Netlify/Cloudflare.

### SEO
- Exactly one H1 per page; unique titles and meta descriptions (4 over-long metas trimmed).
- Canonical correct on every indexable page; stubs correctly canonical to their target.
- Internal linking verified home → collections → products → related, guides → products,
  nav, season hub, trending.
- **`site/404.html`** had `data-root="./"`, which broke the search-index fetch and
  every suggestion href at arbitrary URL depth. Now `"/"`. Its links are root-absolute.

### Structured data
- Product / Offer / Organization / WebSite / BreadcrumbList / FAQPage on every page.
- **No AggregateRating anywhere** — no invented reviews, ratings, prices or availability.
- **Mug schema bug:** `limited-edition-grb35` (a mug) declared
  `"size": ["S","M","L","XL","2XL","3XL"]` while the visible page correctly said
  "This is not an apparel item, so there is no size to choose." Schema now omits
  `size` for non-apparel via a shared `landing.NON_APPAREL` predicate.
  Verified: 80 apparel pages keep `size`, 1 mug has none, 0 defects.
- Brand never implies official/licensed affiliation.

### Social / images / search
- Per-product OG image verified on all 84 pages — **0** use a generic homepage image.
- 382 local image references, **0 broken**.
- Search index: **84 rows = 84 live products**, 0 dead/retired/duplicate entries.

### Content hygiene
- Zero developer/build leakage on public pages: no `.py`, `.csv`, `python3`, `npm`,
  `git push`, `data/*.json`, `src/*.py`, `build.py`, or admin references.
- `/ops/` and `/marketing/` are not linked from any public page and are
  `Disallow`ed in robots.txt.

---

## 3. Verification gates (all run, all passing)

| Gate | Command | Result |
|---|---|---|
| Unit/integration | `pytest tests/ -q` | **141 passed, 0 skipped** (base was 15 failed / 98 passed) |
| Static site audit | `python3 qa_audit.py` | **TOTAL: 0**, all 16 categories PASS |
| Live HTTP crawl | `python3 qa_http.py http://127.0.0.1:8123` | **PASS** |
| Repo health check | `ops/health_check.py --base … --no-drift` | **49 checks PASSED** |
| Rebuild | `python3 src/build.py` | 84 products, 4 collections, 108 urls |

HTTP crawl detail: 108/108 sitemap URLs return 200 · 108 internal link targets,
0 dead · 382 local images, 0 broken · 84/84 product CTAs match the catalogue `buy`
URL exactly · 85/85 redirect stubs valid (200 + `noindex` + `data-gl-redirect` +
visible link + live target) · CSS has 17 responsive breakpoints, no fixed widths
over 360px.

Static audit categories, all PASS: `fulfilment`, `catalogue-count`, `shipping-claims`,
`seo-title`, `seo-h1`, `seo-meta`, `seo-canonical`, `structured-data`, `links`,
`images`, `sitemap`, `robots`, `social`, `internal-content`, `ip-language`.

---

## 4. Items I checked and deliberately did NOT change

- **"S to 3XL" in `src/seocopy.py`** — flagged earlier as stale. It is **correct**:
  the string appears on 46 Viralstyle pages, and every Viralstyle product's
  `sizes_avail` is exactly `S,M,L,XL,2XL,3XL`. All 37 Mayzing pages (Gildan 5000)
  correctly show S–5XL and carry no such string. Changing it would have introduced
  an error.
- **Garment labels** ("Men's T-Shirt" / "Classic Unisex T-shirt") — verbatim-accurate
  against the live Mayzing storefront; not "normalised".
- **Dallas and Green Bay fulfillment** — untouched, per instruction. Only their
  displayed counts became dynamic.
- **"Worldwide shipping"** — retained (true for both partners); an earlier removal
  was reverted.
- **Mayzing store currency** — not changed, per instruction.

---

## 5. Needs manual verification (could not be confirmed from this environment)

1. **Mayzing mockup images are hot-linked.** 44 unique images point at
   `buyer-experience-gateway.mayzing.com` with signed `sig:` params. This sandbox
   has no TLS egress to that host, so I could **not** confirm they load. The
   signatures may expire. Recommended: run `dl.py` to self-host them.
2. **GitHub Pages cannot emit server-side 301s.** `site/_redirects` gives real 301s
   on Netlify/Cloudflare. On Pages the stubs fall back to meta-refresh + JS, which
   passes link equity less reliably. If the site is hosted on Pages, consider a
   Pages-native redirect layer.
3. **`JOE10` promo code** is hard-coded copy in 4 places in `src/build.py`. Confirm
   it is live in the Mayzing cart before it ships.
4. **Mayzing currency rendering** — the same Mayzing store renders Browns in NOK and
   Michigan in USD (per-collection/geo behaviour on Mayzing's side, documented in
   `data/mayzing_products.json`). Our site shows USD $21.00, matching the intended
   config. On-site wording now defers final price/tax to checkout.
5. **Browser click-through** — I verified all 84 CTA `href`s by HTTP against the
   master catalogue (stronger than reading source), but I could not click them in a
   real browser from here. Worth one manual pass on mobile.
6. **Page speed / Core Web Vitals** — no Lighthouse run available here. Asset
   hygiene is good (2 pages with eager images, no oversized fixed widths).

---

## 6. Files changed (source)

```
.github/workflows/refresh.yml   publish gate now derives from the master catalogue
ops/health_check.py             sitemap gate derived from the catalogue
ops/board/index.html            regenerated (129 → 84)
src/build.py                    catalogue facts, partner scoping, redirects,
                                404 data-root, non-apparel schema
src/landing.py                  partner-scoped shipping copy, NON_APPAREL
src/collections_data.py         partner_of()
tests/test_layout.py            14 introduced failures reconciled,
                                15 stale pre-existing failures fixed
tests/test_health_check.py      updated for the derived gate
README.md, DEPLOY-GITHUB.txt    corrected stale counts
site/                           regenerated
qa_audit.py                     static audit harness (16 categories)
qa_http.py                      live HTTP crawl harness
```
