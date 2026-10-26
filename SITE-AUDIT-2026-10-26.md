# Gridiron Locker — Site Audit

**Date:** 2026-10-26 (UTC)  
**Production:** <https://gridironlocker.store/>  
**Repository state:** `a998571` (`Auto-refresh: trends + rebuild 2026-10-26`) plus the three fixes applied by this audit (see §4)  
**Scope:** everything the audit suite covers — test gate, static SEO/schema, deep policy audit, local HTTP crawl of the deployed build, deployment health check, catalogue-contract integrity, pipeline hygiene, and the open items carried from `SITE-AUDIT-2026-09-18/19` and `AGENTS.md`.

## Executive summary

The storefront itself is healthy and the deploy pipeline's gate is green again — but only after this audit found and fixed a **silently broken test gate plus two silent pipeline failures**. The generated site passes every structural check: 400/400 tests, `qa_audit.py` TOTAL: 0, 127/127 sitemap URLs live, zero dead links, zero broken local images, every CTA correct, 60/60 health checks.

What keeps the store **not clear to treat as low-risk** is the same critical IP/design-policy exposure flagged in September (still unresolved, still live), unverifiable discount-code claims on 7 pages, hero asset weight, and internal commercial data that is still anonymously downloadable despite being robots-disallowed.

| Severity | Open groups | Main issue |
|---|---:|---|
| Critical | 1 | Published products and hero artwork conflict with the repository's own IP/design rules (carried from 09-18/09-19) |
| High | 3 | Unverified discount codes on 7 pages; unoptimised LCP/asset delivery; internal commercial data publicly downloadable |
| Medium | 6 | Form policy, dropped `/drops/` designs, near-duplicate designs, weak slugs, repeated copy, hot-linked signed CDN images |
| Low | 1 | 279 images with empty `alt` and no `role="presentation"` |
| Fixed in this audit | 3 | Red test gate (dual-listed design), `replay_updates.py` silent no-op, `scrape_list.py` data-loss on failed crawl |

**Note on live production:** this sandbox has no network route to `gridironlocker.store` (egress is restricted to GitHub/PiPy/npm hosts), so production could not be fetched directly. Every check below ran against the exact committed `site/` build that `refresh.yml` deploys, served over HTTP. The daily `.github/workflows/health-check.yml` (which runs `ops/health_check.py` against production) remains the production-side proof and should be read alongside this report.

## 1. Verification results

| Check | Result |
|---|---|
| Unit/guard-rail suite (`.venv`, `requirements-dev.txt`) | **400 passed, 0 failed, 0 skipped** |
| Same suite without dev deps | 400 run, 1 failed, 17 skipped (16 health-check + 1) — see §2.1 |
| `python3 qa_audit.py` | **TOTAL: 0** across 15 categories; 617 public pages audited |
| Catalogue | 96 designs — GB 36 · CLE 33 · MICH 17 · DAL 10; Mayzing 50 / Viralstyle 46 |
| `python3 qa_deep.py` | CRITICAL=1, HIGH=2, MEDIUM=6, LOW=1 (expected non-zero; see §3) |
| `python3 qa_http.py http://127.0.0.1:8123` | **PASS** |
| Sitemap | 127/127 URLs return 200 |
| Internal links | 33 targets, 0 dead |
| Local images | 382 referenced, 0 broken |
| Remote partner images | 82 unique (Mayzing CDN, signed URLs), 0 confirmed broken, 82 unreachable-from-sandbox |
| Product CTAs | 96/96 point at the right partner checkout |
| Retired-URL redirect stubs | 116/116 valid, noindex, redirecting |
| Responsive CSS safeguard | No fixed widths >360px; 26 max-width breakpoints |
| `ops/health_check.py --base <local mirror>` | **60 checks PASSED** (pages, assets, hero bands, deployed-artwork match, sitemap, homepage facts) |
| robots/noindex discipline | `/ops/`, `/marketing/` disallowed and noindex; verification tokens excluded from the page count |
| Working tree before audit | Clean |

## 2. Gate defects found and fixed

### 2.1 RED TEST GATE — `limited-edition-no-fly-zone` was dual-listed (fixed)

`tests/test_layout.py::MayzingBrownsRebuild::test_collection_mirrors_the_mayzing_file` was failing on `main`:

```
AssertionError: Items in the first set but not the second:
'limited-edition-no-fly-zone' : collections.json Cleveland entry is the retired Viralstyle list
```

**Root cause.** The same design is live on **both** partner storefronts: on Mayzing (`data/mayzing_products.json`, Gildan 5000, $23, real `gridironlocker.shop` checkout) **and** still listed on the Viralstyle Cleveland storefront ($21, THREADFAST). `scrape_list.py` captures the live Viralstyle listing into `data/collections.json`, so the slug sat in both the fossil list and the Mayzing catalogue — exactly the overlap the test forbids ("a dual-listed slug is a customer handed to the wrong partner"). Evidence: the `collections.json` entry carries the scraper's listing-price title (`"…Rs2,001.09"`, INR anchor text) and the lazy-load placeholder thumb, and `data/products_live.json` holds a full successful Viralstyle scrape of the campaign. The campaign was originally hand-added 2026-09-10 via `add_campaign.py` (README) and its Mayzing equivalent was captured 2026-09-12; nobody retired the Viralstyle side.

**Fix applied (tests are the spec — data/code fixed, never the test):**

1. `data/collections.json` — removed the dual-listed slug from the Cleveland fossil list (hand-edit of a shared data file, sanctioned by `AGENTS.md` §3.2).
2. `scrape_list.py` — drops slugs that are live in the matching Mayzing catalogue (minus `delisted.json`), per collection, so the next crawl cannot re-add it or any future migrated design. Same rule as the existing whole-Michigan exclusion, applied per slug.
3. `replay_updates.py` — `inject_data()` now refuses to inject a Mayzing-live slug anywhere (it could re-pollute the fossil list via `campaigns_extra.json`).

**Operator action still recommended:** close/unpublish the `limited-edition-no-fly-zone` campaign on Viralstyle. The same design should not be sold on two storefronts at two prices; the pipeline now keeps the site's data clean either way.

### 2.2 `replay_updates.py` was a silent no-op on every refresh (fixed)

`inject_data()` raised `SystemExit("missing collection: michigan")` because `data/collections.json` no longer has a `michigan` key (scrape_list stopped crawling Michigan when it migrated to Mayzing). The step's `|| echo "replay injection failed, keeping existing data"` in `refresh.yml` masked it, so **every** refresh run lost campaign re-injection, `config.json`/`CNAME` re-pointing, and the `abs_url` patch — with a green tick. This also explains why `collections.json` still showed scraper-format titles rather than the replay injection format.

**Fix applied:** campaigns whose collection is absent from `collections.json` (i.e. migrated to Mayzing) are skipped individually and loudly instead of aborting the whole injection; skipped campaigns are skipped everywhere, including `products*.json`; the final log line now reports `injected N of M`. Verified with a network-free dry run: the 2 Cleveland campaigns re-inject, all 8 Michigan/Mayzing ones skip, no `michigan` key is ever created.

### 2.3 `scrape_list.py` could wipe the catalogue on a failed crawl (fixed)

A network failure on the first listing page left `seen=[]` and the script **overwrote every collection with an empty product list**, exiting 0 — so `refresh.yml`'s "list crawl failed, keeping existing data" fallback never fired and "keeping existing data" was a lie. `data/` is the most dangerous directory in the repo; this was a live data-loss path.

**Fix applied:** if a collection's crawl produces nothing, the previous entry is kept and a warning printed. Also noted as latent: `limited-edition-go-blue` sits in `data/campaigns_extra.json` while being live on Mayzing Michigan — the new replay guard neutralises it, but the stale entry can be retired whenever the campaign file is next curated.

## 3. Open findings (no change made — need owner/business decisions)

### Critical — IP/design-policy conflict remains live (carried from 09-18/09-19)

`qa_deep.py` reports 20 policy violations: five hero banners show garments printed with official helmet/oval/star marks, and 14 live products use player names, surnames, jersey numbers, or player photography (`Denzel Rock Out`, `Jordan Love 10 Packers Shirt`, `Bryce 19`, `Second Act QB19`, …) contrary to `DESIGN-BLUEPRINT.md` §2. This is trademark, copyright and publicity-right exposure, not a lint preference.

**Recommendation (unchanged):** owner/legal decision now — delist or noindex the affected designs and replace hero art, or formally revise the policy after rights are verified. Never silence the gate without resolving the decision.

### High — unverifiable discount codes on 7 pages

`amber/`, `crystal/`, `des/`, `laquala/`, `michigan/bella/`, `michigan/joe/`, `thetypicalbrownsfanshow/` advertise codes (`AMBER`, `CRYSTAL`, `DESTINY`, `LAQUALA`, `VIP10`, `JOE10`, `ORTIZ`) "redeemable at checkout" — but checkout happens on Mayzing/Viralstyle. If the code does not exist in the partner cart, the claim cannot be honoured and is misleading.

**Recommendation:** verify each code in the partner cart; remove or reword the ones that do not exist; state the partner-scoped terms next to each code.

### High — asset weight / delivery efficiency

- 7 hero/LCP JPEGs are 215–431 KB unoptimised (`/img/hero-home.jpg` 431 KB, `/img/hero-cleveland.jpg` 376 KB, …).
- Zero `srcset`/`sizes`/`<picture>` site-wide — a 375px phone downloads the same 2048px hero as a desktop. Biggest single lever on mobile LCP.
- `style.css` is 129 KB, unminified and render-blocking; Google Fonts adds a render-blocking third-party origin.

**Recommendation:** responsive hero derivatives (or `srcset`), compress heroes to an LCP budget (~150 KB), minify/critically inline CSS, self-host the fonts with `font-display: swap`.

### High — internal commercial data is still anonymously downloadable (carried from 09-19)

`/marketing/commercial-brief.json` (~646 KB), `/marketing/plan.json` (~1.0 MB) and `/ops/scout/scout.json` (~28 KB) are still deployed. `robots.txt` disallows `/marketing/` and `/ops/`, but robots is not access control — anyone can fetch the URLs directly. The files contain product opportunity rankings, operating model, marketing queues and catalogue economics.

**Recommendation:** stop deploying them (build-time exclusion), or move them behind real auth. Keep the dashboards `noindex` regardless.

### Medium — six groups

1. **Forms:** the FormSubmit contact endpoint has `_captcha` disabled (spam/back-end abuse surface); the contact address is base64-"obfuscated" personal mail (`itsnoury65@gmail.com`) — base64 is encoding, not anti-harvesting.
2. **`/drops/` dropped designs:** 3 of 24 queued designs have no published page and are discarded at build (`sanders-13-special-edition`, `sanders-12-special-edition`, `sanders-special-edition`) — stale `data/live_drops.json` entries for retired campaigns.
3. **Near-duplicate designs (7 clusters):** `cle-browns` ×3, `no-fly-zone` ×2 (`/shop/limited-edition-no-fly-zone/` vs `/shop/no-fly-zone/`), `1946 cleveland football` ×2, `cheese heart green bay` (shirt vs mug), `cleveland football` ×2, `michigan bet` ×2, `respond nothing given everything earned` ×2. Canonicalise or retire one side per cluster.
4. **Weak slugs (9):** truncated/CMS-suffixed (`lets-go-cle-copy`, `dallas-texas-vintage-athletic-sports-sty`, `limited-edition-cleveland-football-copy`), letter-exploded (`limited-edition-h-a-i-l-mary`), over-long (54 chars), partner-data typos (`be-awar-of-dawg`, `dwag` — check the printed garment before "fixing"). URLs are frozen by contract (`AGENTS.md` §3.3): change only with a redirect plan.
5. **Thin/duplicate copy:** 6 marketing sentences repeat across >10 product pages (worst: 13 pages share the Lake Erie weather line).
6. **Hot-linked signed CDN images:** 1,458 `<img>` tags (82 unique) hot-link the Mayzing CDN with signed URLs; if signatures expire they all break at once. `dl.py` self-hosting is the cure (add its `__main__` guard first — `qa_deep` notes the current script would run at import).

### Low — accessibility

279 images have empty `alt` without `role="presentation"` (decorative thumbs). Fix in `src/` generators, not `site/`.

### Housekeeping / doc drift

- README count table says 87 products / 597 public pages / 111 sitemap URLs; the build now holds **96 / 617 / 127** (the README itself says not to trust the table — re-run `src/build.py` footer or `qa_audit.py`).
- `AGENTS.md` says "145 tests"; the suite is now **400**.
- SEO engine (dry-run, as designed) has 3 ready AUTO actions: `description_too_long` on `/`, `/2026-season/`, `/about/`. Apply via `python3 -m seo_engine apply --commit` when wanted.
- Known open issue `AGENTS.md` §5 is still open: two divergent `build_plan()` implementations (`marketing/plan.py:999` and `marketing/live_engine.py:210`) — owner ChatGPT, see `CODEX-TASKS.md` Task 1.

## 4. What changed during this audit

| File | Change |
|---|---|
| `data/collections.json` | removed the dual-listed `limited-edition-no-fly-zone` entry from the Cleveland fossil list |
| `scrape_list.py` | skips Mayzing-live slugs (minus delisted); keeps existing data instead of writing empty lists when a crawl fails |
| `replay_updates.py` | `inject_data()` no longer aborts on absent collections; never injects Mayzing-live slugs; honest `injected N of M` log |

Nothing under `site/` changed — no rebuild was needed (the built pages were already correct; the defect was in shared data and the crawler pipeline). All 400 tests, `qa_audit.py`, `qa_http.py` and `ops/health_check.py` were re-run after the fixes and are green.

## 5. Priority actions

1. **Legal/IP decision** on the hero artwork and the 14 player-identifying designs (critical, carried).
2. **Verify the 7 discount codes** in the partner carts; remove or fix claims that cannot be honoured.
3. **Close the `limited-edition-no-fly-zone` Viralstyle campaign** (dual-listed design; pipeline is now guarded, the supplier side is not).
4. **Stop deploying `/marketing/*.json` + `/ops/scout/scout.json`**, or put them behind auth.
5. **Asset pass:** hero `srcset`/compression, minified CSS, self-hosted fonts.
6. Then the medium list: `/drops/` data cleanup, duplicate-design canonicalisation, copy de-duplication, `dl.py` self-hosting, contact-form hardening.
