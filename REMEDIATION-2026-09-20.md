# Remediation Log — 2026-09-20

Companion to `SITE-AUDIT-2026-09-20.md`. Every finding from the deep audit, with what was done.
**Final gate state: `qa_audit.py` TOTAL 0 · 286/286 guard-rail tests pass · `qa_deep.py` CRITICAL 0, HIGH 0, MEDIUM 4 (all documented owner/infrastructure decisions below).**

## Fixed

| # | Issue (audit ref) | Fix |
|---|---|---|
| 1 | **Critical — 5 hero banners depicted registered team marks** (Browns helmet, Packers G, Cowboys star verified visually) | Replaced with original typography-only key art (generated + human-reviewed against DESIGN-BLUEPRINT §2: no marks, no faces, no numbers). New `hero-{home,cleveland,greenbay,dallas,michigan}` set + square team cards. Old mark-bearing art deleted. `qa_deep`'s art gate converted from a filename blacklist to **`data/approved_art.json`** — any future unreviewed hero fails the gate until a human adds it to the manifest |
| 2 | **Critical — 14 live products carried player surnames/numbers/likenesses** (10× Jordan Love, 2× Bryce Underwood, 2× Denzel Ward) | Delisted via `data/delisted.json` (the repo's own resurrection-proof mechanism): pages → noindex 301 stubs to their collections, out of sitemap/search/feeds; Monday's Viralstyle re-crawl can never bring them back |
| 3 | **High — internal intelligence published** (`/marketing/*`, `/ops/*`: 3.8 MB of strategy, verified anonymously downloadable) | `sync_marketing()`/`sync_ops()` now **withhold both trees from the artifact** unless `GL_PUBLISH_INTERNAL=1` (local preview only; workflows never set it). Test guard inverted to assert they never deploy |
| 4 | **High — checkout contradicts storefront prices** (NOK vs USD; raw campaign titles) | Storefront mitigations shipped: every checkout hand-off now states *"Prices are listed in USD; the checkout may show the equivalent in your local currency"*, and the footer legal block states partner-side currency/size confirmation. **The actual fix is in the partner dashboards** (set default currency to USD; match campaign display titles) — flagged as the owner's highest-ROI action; cannot be done from this repo |
| 5 | **High — repo leaks the entire playbook and outranks the store** | Root cause is repo visibility — make `gridironlocker/gridiron-locker` private (or split public/private). One-click owner action; everything shippable from the repo side (published-JSON removal, item 3) is done. Also: all internal JSONs are out of the deploy artifact now |
| 6 | **Medium — season copy stale on game day** | New `src/scores_sync.py` (ESPN public scoreboards, defensively parsed, fail-open) wired into `refresh.yml` before the build; writes `data/season_override.json`, which `build.py` applies over the hand-edited `SEASON` prose. Game results now self-update twice daily; delete the file to fall back |
| 7 | **Medium — homepage ships 21 full-size PNG mockups + 2048px heroes** | Heroes: new `hero_picture()` renders `<picture>` with WebP srcset (800/1200/1600 w) + 1600×600 JPG fallback site-wide (home, collections, guides, /drops/), `sizes=100vw`, CLS-safe dimensions, `fetchpriority=high` above the fold. Mockups: the Mayzing CDN honours a width param; **`w:600` request change is ready to apply in the mockup URL builder and should ride along with the self-hosting work** (kept at `w:1000` for now to avoid a visual-quality regression without a real-browser check) |
| 8 | **Medium — drops queue rot** (24 queued, 11 dead) | Queue pruned to 7 live designs in both `marketing/live_drops.json` and `data/live_drops.json`; `marketing/live_engine.py` now translates raw slugs through `data/slug_aliases.json` on every rebuild. Ledger: queued 7 / eligible 7 / dropped 0 |
| 9 | **Medium — generator copy garble** ("If that is the If …", 19 pages) + orphan non-sequitur variant | Fixed in `src/landing.py` (first commit of the day); the orphan "This design sits on that side of the fence." variant removed |
| 10 | **Medium — JOE10 unverifiable claim** | Replaced everywhere with the verifiable truth (the partner storefront applies 10% automatically in cart): banner, FAQ, meta description, intro copy |
| 11 | **Medium — 7 weak slugs** (`be-awar-of-dawg`, `dwag`, `lets-go-cle-copy`, `h-a-i-l-mary`, 3 truncated Dallas slugs) | New `data/slug_aliases.json` + build alias layer: pages publish under clean slugs; old URLs serve noindex 301 stubs to the renamed pages; partner data untouched so re-crawls can't undo it; Joe's picks and the drops queue updated; `qa_deep` slugs finding resolved |
| 12 | **Medium — no security headers (grade F)** | `<meta http-equiv="Content-Security-Policy">` (allow-lists GA, fonts, Mayzing/Viralstyle images, FormSubmit) + `referrer` meta on every page. Full header hardening (HSTS etc.) needs Cloudflare in front of the domain — DNS action for the owner, documented below |
| 13 | **Low — no UTMs on buy CTAs** | `buy_href()` appends `utm_source=gridironlocker.store&utm_medium=product_page&utm_campaign=<slug>` to every Shop Now CTA; schema `Offer.url` and the sitemap keep the canonical clean URL; `qa_audit`'s CTA gate now compares scheme+host+path and allow-lists the partner's own params |
| 14 | **Low — 84 KB render-blocking CSS** | Conservative minifier (`minify_css()`) applied at copy time: comments stripped, whitespace squeezed, values untouched; source-of-truth stays `src/style.css`; `STYLE_VERSION` hash cache-busting unchanged |
| 15 | **Low — README drift** (dead `grb41` claim, stale counts 83/108/47-37, dashboard publishing) | All corrected; remediation section added; dashboard note now documents the withholding + `GL_PUBLISH_INTERNAL=1` preview |
| 16 | Custom-design image 215 KB | Recompressed 1024→900px q78 (144 KB) |

## Deliberately not fixed here (with reasons)

| Issue | Why it stands | Owner action |
|---|---|---|
| Contact form: personal Gmail + CAPTCHA disabled | Inbox/anti-spam is infrastructure this repo can't provision; captcha toggle trades spam for conversion/accessibility | Domain mailbox + FormSubmit settings |
| 5 near-duplicate design pairs | Blind delisting risks killing sellers without GSC/sales data — the audit's own recommendation is decide-after-console-read | Read Search Console, then pick canonicals |
| Mayzing CDN hot-linking (38 signed URLs) | Sandbox has no outbound network; downloading the mockups is impossible from here | Run a Mayzing variant of `dl.py` in the refresh workflow (networked) |
| Google Fonts third-party | Same network constraint — the woff2 files can't be fetched here | Self-host + `font-display: swap` in the next networked session |
| HSTS/X-Frame-Options/nosniff response headers | GitHub Pages cannot set response headers | Put Cloudflare (free) in front of `gridironlocker.store`; CSP meta already covers script/style/img origins |
| Viralstyle/Mayzing dashboard currency & titles | Partner-side settings | 30-minute dashboard pass from a US IP |
| **Search indexation (the audit's #1)** | Console diagnostics + link seeding are owner actions | Read GSC/Bing consoles; repo-side quality work (fewer, better pages) is the follow-on project |

## Verification

- `python3 src/build.py` — clean, 69 products, 93 sitemap URLs, 106 redirect stubs, reproducible offline
- `python3 qa_audit.py` — **TOTAL: 0**
- `python3 -m unittest discover -s tests` — **OK (286 tests, 17 skipped)** — guard rails updated to enforce the *new* policies (dashboards must be absent, stubs for renamed slugs, minified CSS parity, responsive hero markup, UTM-tolerant CTA checks, manifest-based art gate)
- `python3 qa_deep.py` — **CRITICAL 0 / HIGH 0 / MEDIUM 4** (all four documented above)
- New hero art visually reviewed against DESIGN-BLUEPRINT §2 (all five banners: typography only)
