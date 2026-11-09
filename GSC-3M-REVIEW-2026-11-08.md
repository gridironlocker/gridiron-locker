# GSC 3-Month Export Review — 2026-11-08
**Source:** user-uploaded Search Console exports (Performance: Web (text-based), **Last 3 months**
≈ 2026-09-02 → 2026-11-06) + Page Indexing coverage export. Imported via
`seo_engine.import_gsc` (74 page rows, 111 queries, 66 daily points — window now recorded,
closing the old "window NOT recorded" gap). All numbers verbatim from the export.

## Headline numbers (3 months, Web search)
| Metric | Value |
|---|---|
| Clicks / Impressions | **29 / 1,055** (Devices: mobile 20/603 pos 11.4 · desktop 8/442 pos 30.0 · tablet 1/10) |
| Countries | US 23/936 (pos 19.6) · Morocco 4/10 (pos 2.1 — likely owner testing) · CA 0/36 (pos 11.4) |
| Best CTR pages | home 14.1% (17 clk, pos 6.3) · /index.html 18.2% · shipping 6.3% · est-1946 PDP 4.8% |
| Indexing (last point, Oct 23) | 78 indexed / 94 not indexed; **"Duplicate, Google chose different canonical" → PASSED, 0 pages**; alt-canonical 17 / 404 2 / crawled-not 2 / discovered 73 all **validation Started** (user clicked Validate Fix ✓) |

## Findings → actions taken this pass
1. **index.html canonical split (biggest leak).** Google indexed directory `index.html` variants as
   separate URLs: Michigan hub variant **293 impr** at pos 34.5 (clean hub got none), Cleveland hub
   split 18+18, home variant 22 impr/4 clk, plus ghost-product variants. → **Fixed:** `_redirects`
   now 301s every `/path/index.html` → `/path/` (force rules, Netlify/Cloudflare honoured; canonical
   tags remain the defense on GitHub Pages).
2. **"michigan vs everybody shirt" — 35 impr at pos 7.26, 0 clicks.** The impressions land on a
   **retired design's stub** (`limited-edition-m-vs-all`, incl. its variant at pos 2.12) while the
   live guide + 2 live designs get none. → Guide meta override (`seo-gsc3m-20261108`): exact phrase
   front-loaded. The drain happens via the redirect/canonical work; the guide is positioned to
   inherit the query.
3. **"gridiron fan gear" — 32 impr at pos 11, 0 clicks** (3rd-largest query). → Home meta override:
   "Gridiron Locker fan gear: …" exact phrase front-loaded, facts kept ("95 original designs").
4. **Weak-CTR PDPs already treated (PR #238, change_id seo-weakctr-20261108):** beware-of-the-dawgs
   67 impr @6.6 · grb2 41 @6.8 · cleveland-football-copy 38 @12.6 · grb33 19 · grb36 14 · star
   lightning 14 @5.2 · 1960 helmet 18 @5.3 — this export predates the new metas; **re-measure 2–3
   weeks post-deploy** before further edits.

## Retired designs still earning page-1 impressions (= re-listing demand evidence)
| Retired design | Impr | Pos | Note |
|---|---|---|---|
| limited-edition-m-fans (variant) | 46 | 5.4 | "Michigan Fans" concept ranks top-5 |
| tee-0-01-1 | 14 | 9.3 | |
| limited-edition-m-vs-all (10+8) | 18 | 11.4 / **2.1** | captures the vs-everybody query |
| limited-edition-qb19 | 6 | 7.2 | QB19 moment demand |
| whispered-go-browns | 3 | 7.7 | hold-list "So I Whispered Go Browns" family |
| go-b-r-o-w-n-s | 1 (+1 clk) | 6.0 | got a click at pos 6 |
| m-fans-n26/n28/n29/n30 | 17 | 7–10 | split across variants |
| sanders-the-next-level, no-fly-zone-denzel, 2024n2, lfg, b-e-k-i-n-d, d-a-w-g | 1–2 each | 3–21 | long tail |

These impressions die at stubs (delisted/hold per your "drop" decision) — they do not convert.
**Use as the priority order if any designs return via the Mayzing re-listing workflow.**
Note: all ghost pages above are unpriced; pricing them remains off-limits (0/52 Mayzing matches).

## Updated measurement baseline (3-month window, for the weekly report)
| Query cluster | Impr | Pos | Status |
|---|---|---|---|
| gridiron cap locker (brand) | 29 | 3.8 | 9 clk, 31% CTR ✓ healthy |
| green bay packers shirt | 41 | 39.7 | title test live (PR #241) |
| michigan vs everybody shirt | 35 | 7.3 | meta override live; watch ghost drain |
| gridiron fan gear | 32 | 11 | home meta override live |
| michigan shirts / t shirts / t shirt | 48 | 38–51 | depth play (hub content) |
| dearborn michigan t-shirts + apparel | 25 | 55–59 | Dearborn guide section; candidate future landing |
| cleveland football shirts | 9 | 44.6 | hub meta candidate next pass |
| packers shirt | 15 | 37.1 | covered by title test |

**Remaining asks unchanged:** ghost data-source deletion (Merchant) · shipping ruling · tracking
config · design approvals. Next GSC re-measure: ~Nov 22–29 (2–3 weeks post meta batch).
