# Gridiron Locker — Site Audit

**Date:** 2026-09-19 (UTC)  
**Production:** <https://gridironlocker.store/>  
**Repository state:** `b8de34d` (`Auto-refresh: trends + rebuild 2026-09-19`)  
**Scope:** generated public site, local HTTP behavior, SEO/schema, links/assets, fulfilment CTAs, responsive safeguards, live-production spot checks, legal/brand-risk rules, and public-data exposure.

## Executive summary

The storefront is technically healthy: all tests pass, every sitemap URL returns 200 locally, internal links and local images resolve, product CTAs match the catalogue, schema/metadata checks pass, and production is serving the current 2026-09-19 build.

The site is **not clear to treat as low-risk**, however. One critical legal/brand-policy issue remains, and internal commercial intelligence is still publicly downloadable. Performance and third-party image resilience also need work.

| Severity | Open groups | Main issue |
|---|---:|---|
| Critical | 1 | Published products and hero artwork conflict with the repository's own IP/design rules |
| High | 3 | Public commercial/ops data, unoptimised responsive assets, unverified `JOE10` claim |
| Medium | 6 | Public form policy, hot-linked product images, duplicate designs, weak slugs, dropped campaigns, long descriptions |

## Verification results

| Check | Result |
|---|---|
| Unit/guard-rail suite | **286 passed, 17 skipped, 0 failed** |
| `qa_audit.py` | **TOTAL: 0** across 15 categories; 194 public pages audited |
| `qa_http.py http://127.0.0.1:8123` | **PASS** |
| Sitemap HTTP check | **107/107 return 200** |
| Internal links | **107 targets, 0 dead** |
| Local images | **382 referenced, 0 broken** |
| Product CTAs | **83/83 correct** |
| Retired URL stubs | **86/86 valid** |
| Responsive CSS safeguard | No fixed widths over 360px; 18 max-width breakpoints |
| Deep policy audit | **1 critical, 2 high, 5 medium** (expected non-zero) |
| SEO engine audit | 3 medium findings: descriptions over its preferred length |
| Working tree before audit | Clean |

The 17 skipped tests are the live health-check module because its optional `requests`/Pillow dependencies are not installed in this environment. The static and local-HTTP checks still ran. Remote Mayzing assets could not be independently fetched by `qa_http.py`; all 43 were reported as unreachable rather than confirmed healthy or broken.

## Findings

### Critical — IP/design-policy conflict remains live

`qa_deep.py` reports 20 policy violations:

- Five hero banners show garments carrying official helmet/oval/star marks.
- Fourteen live products use player names, surnames, numbers, or player photography, contrary to `DESIGN-BLUEPRINT.md` §2.
- Examples include `Jordan Love 10 Packers Shirt`, `Bryce 19`, and `Denzel Rock Out`.

This is not merely a lint preference: it conflicts with the project's written shipping gate and creates trademark, copyright, and publicity-right exposure. Production spot-checking confirms these products are currently presented and indexable.

**Recommendation:** obtain an owner/legal decision immediately. Delist or noindex the affected products and replace hero art, or formally revise the policy only after rights have been verified. Do not silence the deep-audit gate without resolving the underlying decision.

### High — commercial and operations intelligence is publicly downloadable

Source-code leakage has been reduced, but sensitive generated data remains anonymously accessible in production. Verified examples:

- `/marketing/commercial-brief.json` — about 646 KB; product opportunity rankings, operating model, creative strategy, source coverage, experiments, diagnostics, and limitations.
- `/marketing/plan.json` — about 1.0 MB; marketing queue, calendar, opportunity model, strategy, and compliance data.
- `/ops/scout/scout.json` — trend formula, headline evidence, catalogue economics, gaps, tracked names, and dead-campaign counts.
- Public dashboards remain under `/marketing/` and `/ops/`.

`noindex` and `robots.txt` are not access controls. In fact, the disallowed paths advertise the location of these surfaces.

**Recommendation:** remove ops/marketing dashboards and JSON from the GitHub Pages artifact. Publish them as private CI artifacts or behind authenticated hosting. If a public dashboard is intentional, generate a separate redacted dataset containing only information acceptable for competitors and crawlers to download.

### High — mobile LCP and asset delivery

- Hero JPGs are 371–431 KB (homepage: 431 KB).
- There is no `srcset`, `sizes`, or `<picture>` usage site-wide.
- `style.css` is 84 KB and unminified/render-blocking.
- Google Fonts adds external connection and render cost.

A phone downloads the same 2048px hero as desktop. This is the clearest likely Core Web Vitals bottleneck, although a real-browser Lighthouse/WebPageTest run is still needed to measure field-like LCP/CLS/INP.

**Recommendation:** generate AVIF/WebP responsive variants, add `srcset`/`sizes`, minify/split critical CSS, and self-host/subset fonts with `font-display: swap`.

### High — unverified discount promise

`/michigan/joe/` advertises `JOE10` as redeemable at checkout, but checkout occurs with fulfilment partners. The repository cannot prove the code exists there.

**Recommendation:** verify the promotion in the partner cart and add an expiry/terms source, or remove the claim.

### Medium — external image dependency

There are 741 image tags referencing 43 unique signed Mayzing CDN URLs. A signature expiry, path change, or rate limit can break many product cards at once. The local HTTP gate cannot currently verify these remote images.

**Recommendation:** self-host approved product mockups, preserve an attribution/source record, and make remote-image failure blocking in a network-enabled scheduled check.

### Medium — form/contact policy

The public FormSubmit endpoint disables CAPTCHA. The contact address is a personal Gmail mailbox and is plainly published (base64 elsewhere does not prevent harvesting).

**Recommendation:** use a domain mailbox and enable anti-spam controls that preserve accessibility and conversion.

### Medium — catalogue curation and URL quality

- Five near-duplicate product pairs remain.
- Seven weak slugs are truncated, CMS-suffixed, letter-exploded, or misspelled (`be-awar-of-dawg`, `dwag`, etc.).
- The typo may originate in partner artwork, so inspect the actual design before renaming.

**Recommendation:** choose canonical products for duplicate pairs. For corrected slugs, preserve permanent redirects and retired stubs so existing links and search equity are not lost.

### Medium — dropped campaign inputs

The drops feed contains 24 designs, but 8 have no published page and are discarded during build. This is now logged rather than silent, but it still signals upstream catalogue drift.

**Recommendation:** remove stale queue entries or restore their catalogue records; alert when the discarded count increases.

### Medium — three long meta descriptions

The SEO engine flags `/` (163 characters), `/2026-season/` (164), and `/about/` (165). They remain below `qa_audit.py`'s hard 175-character ceiling, so this is optimization rather than a correctness defect.

**Recommendation:** trim each to roughly 150–160 characters while preserving intent and differentiators.

## What is working well

- Catalogue count and collection splits are consistent: **83 products** across Cleveland 19, Green Bay 37, Dallas 10, Michigan 17.
- Fulfilment CTAs and partner routing are consistent for all products.
- Canonicals, one-H1 rules, titles, social metadata, structured data, sitemap, robots directives, and local image/link integrity pass the strict audit.
- No fabricated rating/review or urgency signals were detected.
- Retired product URLs preserve controlled redirect stubs rather than becoming broken links.
- The build has useful automated safeguards and a deep audit that intentionally refuses to hide unresolved business-risk decisions.

## Recommended order of work

1. **Owner/legal:** decide the 14 player-related products and replace the five mark-bearing heroes.
2. **Privacy/competitive:** stop publishing internal dashboards and commercial JSON on the storefront domain.
3. **Trust:** verify or remove `JOE10`.
4. **Performance:** responsive modern hero assets, then CSS/font optimization; validate with Lighthouse/WebPageTest on mobile.
5. **Resilience:** self-host Mayzing imagery or add a network-enabled hard failure check.
6. **Hygiene:** resolve duplicate products, malformed slugs, dropped campaigns, and the three long descriptions.

## Audit limitations

This run did not use a full browser performance profiler, assistive-technology session, checkout transaction, or authenticated fulfilment account. HTTP response security headers, real-device interaction, payment behavior, email delivery, and the actual validity of `JOE10` therefore remain unverified. Production content was spot-checked through the available web fetcher; the exhaustive link/image/CTA crawl was run against the committed build through a local HTTP server.
