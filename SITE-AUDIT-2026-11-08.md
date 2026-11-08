# Site & SEO audit - 2026-11-08

State audited: `main` at f24e086 (auto-refresh 2026-11-08), rebuilt locally -
95 products, 4 collections, 130 URLs, 629 generated HTML pages (130 indexable,
499 noindex redirect stubs for held/delisted designs).

## Verdict

The site is technically sound. Two real defects found, both fixed here. One
fresh data import (Search Console, 2026-11-05 drop). Fourteen CTR opportunities
logged with evidence - none acted on without a go-ahead. Everything else below
is a clean bill of health with counts.

## Defects found and fixed

1. **Duplicate title tags (high)** - `/shop/browns-cle/` and `/shop/cle-browns/`
   shipped `CLE Cleveland Browns Shirt | Gridiron Locker` and `Cle Cleveland
   Browns Shirt | Gridiron Locker`. Google folds letter case, so the two pages
   competed as duplicates. The title-uniqueness pass in `seo_engine/keywords.py`
   compared titles case-sensitively; it now collides on `casefold()` and assigns
   the second title its garment variant (`Cle Cleveland Browns T-Shirt`).
   `tests/test_layout.py::test_titles_and_metas_are_unique_per_product` now
   matches case-folded, so this class of bug cannot ship again.

2. **Meta-length false positive (medium)** - the SEO engine counted HTML-escaped
   source text (`Y&#x27;all` = 9 chars) instead of the rendered snippet Google
   measures (`Y'all` = 4), flagging `/shop/vintage-country/` as 165 chars when
   the real description is 155. `seo_engine/crawler.py` now decodes entities at
   parse time, so every length rule (title + description) counts what Google
   sees.

After the fixes: `seo_engine audit` reports **high=0, description issues=0**.

## Fresh data imported (verbatim)

The 2026-11-05 Search Console drop (performance + page indexing) was imported
via `seo_engine.import_gsc`: 74 page rows (24 clicks, 1,037 impressions), 107
query rows, 5 issue rows - all counts copied as exported, no inference.

## Indexing status (Search Console, snapshot 2026-11-05)

| Reason | Pages | Validation |
|---|---|---|
| Alternate page with proper canonical tag | 17 | Failed |
| Crawled - currently not indexed | 2 | Failed |
| Not found (404) | 2 | **Not Started** |
| Discovered - currently not indexed | 73 | Started |
| Duplicate, Google chose different canonical than user | 0 | Passed |

Operator asks that stand:
- **Validate Fix on the 2 "Not found (404)" pages** - still "Not Started"
  (unchanged since the 2026-10-23 snapshot). One click in Search Console.
- The 17 "Alternate page with proper canonical" are the retired-design redirect
  stubs behaving as designed (noindex + canonical to the live collection);
  Google keeps labelling them until validation passes.

## CTR opportunities (evidence: GSC 2026-11-05; not acted on)

14 zero-click pages with impressions, flagged by the weak-CTR rule:

| Page | Impressions | Pos | Note |
|---|---|---|---|
| /green-bay-packers-shirts/ | 121 | 34.1 | **title** lever - but collection titles are frozen; needs owner approval |
| /shop/limited-edition-cleveland-football-beware-of-the-dawgs/ | 59 | 6.4 | description lever (product, generator-owned hook) |
| /shop/limited-edition-grb2/ | 40 | 6.8 | description lever |
| /shop/dallas-football-vintage-style-tee/ | 12 | 5.1 | description lever |
| /shop/limited-edition-grb36/ | 11 | 7.7 | description lever |
| /shop/dallas-football-vintage-athletic-style-f/ | 9 | 5.0 | description lever |
| /shop/limited-edition-grb20/ | 7 | 4.0 | description lever |
| /shop/limited-edition-cleveland-football/ + 6 more (4-6 impr each) | - | - | description levers |

Product snippets are generator-owned since the 2026-10-29 rewrite (hand
overrides were retired deliberately); the lever is the hook copy in
`seo_engine/keywords.py`, not per-product overrides. Sample sizes are small
(4-59 impressions) - worth batching with the next copy pass rather than
individually. Say the word and it gets a pass.

## Check matrix (all green)

| Check | Result |
|---|---|
| Title uniqueness (case-folded), length, whitespace, repeated words | 130/130 clean |
| Meta descriptions present, rendered length, uniqueness | 130/130 clean (6 utility/guide pages under 110 chars - acceptable, noted) |
| Canonical tags present and self-consistent | 130/130 clean |
| JSON-LD parse + Product/Offer price + availability + BreadcrumbList | 627 blocks clean |
| Internal links resolve (no broken hrefs on indexable pages) | clean |
| No live page links into a retired stub | clean |
| Sitemap = indexable set exactly, lastmod format, robots.txt + Sitemap line | 130/130 clean |
| Image alt text (non-decorative) | clean |
| Retired stubs: noindex + instant redirect, valid targets | 499/499 clean |
| Google Merchant feed: 95 items, every one priced, domain-locked links | clean |
| Primary keyword present on its PDP (post-rewrite contract) | 95/95 clean |
| Full test suite | 437 tests + 671 subtests passed |

## Related status (not site defects)

- **Google Merchant**: all 95 products in "Pending initial review" since the
  2026-11-05 data-source cleanup; Google quotes up to 3 business days (expect a
  verdict by ~2026-11-10). The 21 stale disapproved items are gone (0 not
  approved).
- **Feed hygiene guard** (from the 2026-11-05 triage) holds: held/delisted
  slugs can never enter the Merchant feed.
