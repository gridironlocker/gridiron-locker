# SEO status — 15 Sep 2026

Snapshot taken by Arena from the repo, the GitHub API and the live site.
Read-only: nothing in `site/` or `src/` was changed to produce this.

## Verdict

| Area | Status |
|---|---|
| Technical SEO on the built site | **Green** — verified, 0 defects over 194 pages |
| Crawl / index plumbing | **Green** — sitemaps, robots, IndexNow, GSC+Bing tokens, daily live health check |
| Measurement of traffic | **Missing** — no traffic data reaches the repo at all |
| Organic traffic | **Unproven** — domain is 12 days old; GSC/GA4 access needed to answer |

## What is solid (with the numbers)

- `python3 qa_audit.py` → `TOTAL: 0`. 194 public pages audited; all 15 checks PASS
  (seo-title, seo-h1, seo-meta, seo-canonical, structured-data, links, images,
  sitemap, robots, social, internal-content, ip-language, fulfilment, catalogue-count,
  shipping-claims).
- 108 URLs in `sitemap.xml` (84 product pages + collections, guides, hubs) plus a
  66 KB `sitemap-images.xml`. `robots.txt` allows Googlebot, Bingbot, image crawlers
  and the AI answer engines, and disallows only `/marketing/` and `/ops/`.
- 84 sellable product pages, **~1,500–1,700 words each** (e.g. `/shop/bryce-19/` =
  1,697 words), unique `<title>`/meta description per page — **0 duplicate
  descriptions** across all 108 indexable URLs.
- GA4 `G-5RHGJSLZNG` on every indexable page; `shop_now_click` carries
  `slug` / `price` / `collection` / `placement` / `creator`.
- Search-engine ownership: two Google verification tokens
  (`googleae06215486ed6c17.html`, `google7e05d1ab221dce85.html`),
  `BingSiteAuth.xml`, IndexNow key `a7f3c19b…txt` (hosted and submitted from
  `refresh.yml`).
- GitHub Pages: `cname = gridironlocker.store`, HTTPS certificate **approved** for
  apex + www (expires 2026-12-02). `https_enforced` is **false** — see findings.
- Automation, all green in the last 24 h: `refresh.yml` rebuilds + re-indexes twice
  daily, `deploy.yml` publishes on push, `health-check.yml` re-checks production
  daily (last run 13 h ago, success).

## Why "did we start getting traffic" cannot be answered from here

1. **Nothing in the repo measures traffic.** `marketing/performance-memory.json`
   has `learnings: []`, `observations: []`, `last_updated: null`.
   `marketing/commercial_agent.py` still reports
   `google_search_trends: {"status": "not_connected"}`. CODEX-TASKS Task 3
   (the GA4/GSC importer) is unchecked — that is the only thing that would make
   this question self-answering.
2. **The sandbox cannot reach GA4/GSC.** Egress is restricted to GitHub; the GSC
   API path needs the `GSC_SA_JSON` service-account secret, and repo secrets are not
   readable from here (`gh secret list` → 403).
3. **Public index checks were inconclusive.** A web search for the brand returns the
   GitHub repo, not the store; Bing's `site:` query returned unrelated results;
   DuckDuckGo and Mojeek served captchas; the Wayback API is offline. So there is
   **no observable organic footprint yet** — but that is *not* the same as proof of
   non-indexation.

## Timeline (matters for expectations)

- 2026-08-25 — repo created, site first published at `gridironlocker.github.io`;
  GSC + Bing verification files and the IndexNow key uploaded the same day.
- 2026-09-03 — `site/CNAME` added; first Pages deploy of the new workflow 20:47 UTC;
  HTTPS cert issued for the custom domain.
- 2026-09-15 — 12 days on `gridironlocker.store`, 84 designs live, sitemap rebuilt.

A brand-new domain with ~108 fresh pages competing with established retailers
should expect impressions to trickle in over weeks, not days. An empty GA4 at day
12 is normal; the useful signal is whether **impressions** trend up in GSC.

## Findings and suggested order of work

1. **Confirm Search Console is actually live for `gridironlocker.store`.** Two
   different Google tokens exist, one of which probably belongs to the old
   `github.io` property. Confirm the `gridironlocker.store` property is verified in
   the right account with `sitemap.xml` submitted; same for Bing. Nothing else in
   the programme can be judged until this is certain.
2. **Wire the traffic importer (CODEX-TASKS Task 3, `marketing/` — not Arena's
   path).** GA4 + GSC → `performance-memory.json` rows with `date` and `source`.
   This also unblocks Task 5.
3. **Enforce HTTPS.** Pages currently serves `http://gridironlocker.store/` with a
   200 and no redirect (verified live). Canonicals are https so it is not a
   duplicate-content emergency, but the Pages setting should be switched on.
4. **`<lastmod>` is not credible.** Every build re-stamps all 108 URLs with today's
   date, so crawlers see "everything changed today, every day" and will start
   ignoring the field. Stamping only pages whose content hash changed is a small,
   contained fix in `src/build.py`.
5. **85 noindex redirect stubs are half the shop-shaped URL space.** They funnel
   retired player/search intent into generic collection pages. Remap the ones that
   actually get impressions to the nearest product page — blocked on item 2.
6. **51 product slugs are machine names** (`/shop/limited-edition-grb36/`), which
   carry no keyword value. Titles are good, so this is a weak signal, not a defect;
   new slugs should be keyword-shaped.
7. **Housekeeping, not SEO:** `tests/test_three_day_pulse.py` fails
   (8 unique hook templates for 9 rows) — marketing-side test, does not block deploys.

## Standing risk worth naming

The highest-intent pages are player-named designs (Sanders, Denzel, Bryce 19,
Jordan Love). If any of them are pulled for trademark/NIL reasons, the ranking
equity accumulated on that URL dies with it. Team- and slogan-shaped designs are
the ones that can hold rank for years.

## Reproduce this snapshot

```bash
python3 qa_audit.py                                  # expect TOTAL: 0
python3 -m unittest discover -s tests -p "test_*.py" # expect 1 known failure
gh api repos/gridironlocker/gridiron-locker/pages | jq '.https_certificate,.https_enforced'
gh run list --limit 10
```

---

## Fixes shipped (2026-09-15, after this snapshot)

Written up here so the next reader knows what moved and what it was worth.

| Fix | Measured effect |
|---|---|
| Hero bands now ship a `srcset` (1024w / 1600w WebP + the 2048w master) | A phone on a 390 px band downloads **74-90 KB instead of 371-441 KB** - the LCP element on the homepage and all four collection pages. Generated by `src/prepare_images.py`; `src` stays the master, so og:image and the health check's ratio/byte budget are untouched. |
| The four collection logo avatars re-derived from the PNG masters at 320 px | **1.85 MB -> 75 KB** (`michigan-logo1.webp` alone was 891 KB for a 150 px circle). |
| `<lastmod>` is now earned per URL, not stamped on all 108 twice a day | A rebuild with unchanged content re-dates nothing; a page that changes takes today's date. Verified both ways. `data/build-manifest.json` is the build's memory of it; `tests/test_layout.py::LastmodIsEarned` holds the rule. |
| IndexNow submissions are diff-based (`--changed`) and fire on every deploy, not only on the twice-daily refresh | New or edited pages are submitted within minutes of the deploy that published them, instead of waiting up to 12 hours - and unchanged pages are no longer re-announced twice a day. |
| `_redirects` and the retired-slug stubs are generated in a stable order | The file churned on every rebuild because it iterated a `set`; the twice-daily bot commit carried the noise. |
| The refresh commits explicit paths instead of `git add -A`; `__pycache__` can no longer reach the published site | Internal files can no longer be swept into a commit (or a deploy) by accident. |

Not done, and why: the GA4/GSC importer (findings 2 and 5) is `marketing/` work
and needs the Search Console property confirmed first - a human, in an account,
not a repo change. Question titles for the 51 machine slugs (finding 6) are
deliberately skipped: the titles carry the keywords, and changing live URLs
would throw away whatever indexing they already have.
