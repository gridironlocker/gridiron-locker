# AGENTS.md — Gridiron Locker

Instructions for AI coding agents working in this repository. Read this before
changing anything. `README.md` explains the project to humans; this file defines
who is allowed to change what, and which interfaces are load-bearing.

Two agents currently work here. This file exists so they behave as two
specialists on one project rather than two writers on one file.

---

## 1. The operating agreement

**Arena** — primary agent for the storefront and its build system.
**ChatGPT / Codex** — marketing, trend intelligence, automation, content
distribution, analytics, growth systems.

The split is by *path*, not by topic, because paths are what actually collide:

| Path | Owner | Notes |
|---|---|---|
| `site/**` | **Arena** | Generated output. Never hand-edit; change `src/` and rebuild. |
| `src/**` | **Arena** | The generator. Runtime is stdlib-only — do not add third-party imports. |
| `artwork-source/**` | **Arena** | PNG masters. Never deployed. |
| `marketing/**` | **ChatGPT** | Planners, generators, dashboards, social kit. |
| `ops/**` | **shared** | `ops/health_check.py` = Arena. `ops/scout`, `ops/board`, `ops/marketing`, `ops/hq` are *generated* — see §3.4. |
| `data/**` | **shared, read-mostly** | Written by the scrapers and by hand. See §3.2 — this is the most dangerous directory in the repo. |
| `tests/**` | **split** | `test_layout.py`, `test_health_check.py` = Arena. `test_three_day_pulse.py`, `test_commercial_agent.py` = ChatGPT. `testutil.py` = shared contract. |
| `.github/workflows/**` | **shared** | `refresh.yml` contains *both* lanes. See §3.5. |
| Root `.md` docs | **Arena** | `BLUEPRINT.md` §5/§8 are the marketing sections — coordinate before editing those. |

### The git situation right now

- `refresh.yml` commits to **`main`** twice a day as `gridiron-bot`
  (`Auto-refresh: trends + rebuild <date>`).
- Arena works on `arena/*` session branches and does not push to `main`.
- **Both agents branch from the same `main`, which moves underneath you twice a
  day.** Rebase before you push, and never force-push `main`.
- `refresh.yml` and `add-campaign.yml` used to run `git pull --rebase -X theirs`,
  which silently discarded human (and agent) edits on conflict. That has been
  removed — a conflict now fails the run loudly. If you see that failure,
  resolve it by hand; do not reintroduce `-X theirs`.

---

## 2. Before you change anything

Run these. They are fast and they are the difference between "I think it works"
and "it works."

```bash
python3 -m unittest discover -s tests -p "test_*.py"   # 145 tests, ~1s, no deps
python3 qa_audit.py                                    # read-only SEO/schema audit of site/
```

`qa_audit.py` must print `TOTAL: 0`. If you changed `src/`, also run
`python3 src/build.py` first — but read §3.1 before you do, because a rebuild
re-stamps every date in `site/` and produces a large diff.

`tests/test_health_check.py` skips all 16 of its tests unless
`requests` + `Pillow` are installed (`pip install -r requirements-dev.txt`).
A fully-skipped run still prints `OK`, so **check the skip count**, not just the
exit code.

---

## 3. The shared contracts

These are the interfaces between the two halves. Changing one side without the
other is how this repo breaks.

### 3.1 `site/` is generated — and a rebuild is not a no-op

`src/build.py` writes every page, the sitemap, robots, feeds and assets. It
stamps `validFrom`, `<lastmod>`, `datePublished` and `dateModified` from
`build.utc_today()`. So **rebuilding on a different UTC day than the last commit
produces a diff on every single page**, even when nothing else changed.

Consequences:

- Do not rebuild as a way of "checking" something. `qa_audit.py` and
  `tests/test_layout.py` both read the committed `site/` and need no rebuild.
- If you must rebuild, expect a date-only diff and say so in the commit message.
- Never commit a partial rebuild. `site/` is all-or-nothing.
- `build.py`'s `main()` also *deletes* orphan artwork from `site/img/`. Rebuild
  without network access and you can delete images you cannot re-download.

### 3.2 The catalogue has exactly one source of truth — and it is not any one file

This is the single most important contract in the repository, and it is
currently violated. See §5.

| File | What it actually is |
|---|---|
| `data/products.json` | A **stale** Viralstyle crawl snapshot. 113 slugs. **Not the catalogue.** |
| `data/products_live.json` | The Viralstyle half only. Also 113 slugs, also stale. |
| `data/mayzing_products.json` | Cleveland/Browns catalogue on Mayzing (19). |
| `data/mayzing_michigan.json` | Michigan catalogue on Mayzing (18). |
| `data/campaigns_extra.json` | Hand-added campaigns a re-crawl would drop; re-injected by `replay_updates.py`. |
| `data/delisted.json` | 31 slugs retired by hand (departed players, pulled artwork). |
| `data/fulfillment.json` | Partner naming **plus a `hold` list of 57 slugs** withheld from Viralstyle pending Mayzing upload. |

**The real catalogue is the merged set that `src/build.py` computes**, after
applying `delisted` and `fulfillment.hold`. It is currently **84 designs**:
green-bay-packers 37 · cleveland-browns 19 · michigan 18 · dallas-cowboys 10.

Rules:

- **Never treat `data/products.json` or `data/products_live.json` as "the
  products."** They are crawl artefacts. Reading either one as a catalogue is
  the bug documented in §5.
- To get the authoritative list in Python: `sys.path.insert(0, "src"); import
  build; {i["slug"] for i in build.ALL}`. Importing `build` is read-only and has
  no side effects. `refresh.yml:114` already does exactly this in its sanity gate.
- Never write to `data/` from anything in `marketing/`. `data/` is the shared
  input layer; if marketing needs derived state it writes to `marketing/`.
- `data/order.json` is **regenerated by `sheet.py`** as a side effect of making
  contact sheets. Do not hand-edit it and do not import `sheet.py`.

### 3.3 Product URLs and SEO are frozen

Every product URL (`/shop/<slug>/`), collection URL, canonical tag, OG/Twitter
card, JSON-LD block and sitemap entry is load-bearing. Preserve them unless
there is a strong reason and you have said so explicitly.

- Retired slugs get a **noindex redirect stub** at the same path, never a 404
  and never a reused slug. 85 stubs exist today.
- `tests/test_layout.py` encodes the SEO contract as executable assertions. If
  your change makes it fail, your change is wrong — do not weaken the test to
  make it pass. Ask first.
- **No fabricated trust signals.** No `aggregateRating`, `ratingValue`,
  `reviewCount`, star markup, compare-at pricing, "only N left", or urgency
  copy. There is no sales feed to justify any of them, and
  `test_no_fabricated_trust_signals` fails the build if they appear. This is a
  business rule, not a style preference.
- **No mini-checkout on product pages.** No style/size/colourway picker, no
  checkout button. Gridiron Locker does discovery and SEO; the fulfilment
  partner does configuration and the transaction. One CTA: `SHOP NOW →`.
- Shipping and returns claims are **partner-scoped**. Never quote Viralstyle's
  $4.95 or 30-day window on a Mayzing product, or vice versa.

### 3.4 Marketing artefacts must never become a hard build input

`src/build.py` reads `data/` and `src/`. It must not *require* anything in
`marketing/`. Where a marketing artefact does inform a page
(`data/live_drops.json` → `/drops/`), the build guards it — it filters to slugs
that actually have a published page and degrades to empty rather than failing.

Keep that property. If a marketing generator breaks, produces a stub, or runs
without network, **the storefront must still build and deploy.** That is why
`refresh.yml` marks the marketing steps `continue-on-error`.

The reverse also holds: `ops/scout/`, `ops/board/`, `ops/marketing/` and
`ops/hq/` are **generated** by `src/scout.py` / `src/build.py` during the build.
Do not hand-edit their `index.html`. If a dashboard needs to change, change the
generator and let the build re-emit it. They are `noindex` and
robots-disallowed; keep them that way — they contain internal economics.

### 3.5 `refresh.yml` is two pipelines wearing one coat

Steps in order: crawl (`scrape_list` → `scrape_products` → `replay_updates` →
`dl.py`) → `trends.py` → marketing (`social_watch`, `plan`, `live_engine`,
`commercial_agent`, `three_day_pulse`, `publisher`) → `build.py` → sanity gate →
test suite → commit → deploy → `nudge_google` → `indexnow` → live health check.

- Arena owns the crawl, the build, the gates and the deploy.
- ChatGPT owns the marketing block.
- **Neither agent should reorder or delete the other's steps.** Adding a step is
  fine; put it in your own block.
- The crawl steps hit **Viralstyle, your supplier**. Do not increase their
  frequency. Anything that needs to run more often must run in the
  trends → build → deploy → indexnow segment, which touches no supplier.
- All three mutating workflows share `concurrency.group: pages-deploy` so two
  `actions/deploy-pages` calls can never overlap. Keep it that way; a new
  workflow that commits or deploys must join that group.

### 3.6 Repo hygiene

`.git` is already **103.5 MiB** with 2,116 tracked files, and `refresh.yml`
commits with `git add -A` twice a day. So:

- **Never commit generated artefacts.** `site-offline/` (~86 MB, built by
  `src/make_offline.py`), `__pycache__/`, `marketing/publish-results.json` and
  build scratch are gitignored. Do not un-ignore them.
- Do not add new binary assets to `marketing/social/` or `artwork-source/`
  without saying so — those are what pushed the pack over 100 MB.
- No Git LFS is configured. If you need large files, raise it rather than
  committing them.
- Prefer editing existing files over adding new ones. If you add a file, it
  should be small, text, and owned by exactly one agent.

---

## 4. Hard rules

1. **One design → exactly one URL.** Never create a second page for a slug that
   already has one, and never reuse a retired slug.
2. **Never write to `data/` from `marketing/`.**
3. **Never hand-edit `site/`.** It is output.
4. **Never weaken a test to make it pass.** The tests are the spec.
5. **Never run `src/indexnow.py`, `src/nudge_google.py`, `marketing/publisher.py
   --publish`, or `ops/health_check.py` against production as a side effect of
   testing.** These ping live endpoints for the real domain.
6. **Never commit secrets.** `src/config.json` holds a public IndexNow key and a
   base64 contact email — both intentional. Workflow secrets live in GitHub, not
   in the repo.
7. **A test run must not mutate the repository.** If you add a test that runs a
   generator, use `tests/testutil.py::generator_sandbox`. See §6.
8. **Preserve the fan-made / independent / not-affiliated framing** on every
   page you touch. It is the entire trademark defence.

---

## 5. Known open issue — the boundary bug (owner: both)

As of 2026-09-13 the marketing queue is out of sync with the catalogue:

- `marketing/plan.py:1187` reads `data/products.json` — the **stale** 113-slug
  crawl — and filters it against `data/delisted.json` (31 slugs).
- It never reads `data/fulfillment.json`'s `hold` list (57 slugs).
- Result: **55 of 96 queue rows point at designs with no published page**, and
  they carry raw `viralstyle.com` URLs. The three highest-scoring rows in
  `commercial-brief.json`'s `top_5_products_today` are three unpurchasable
  Sanders designs.
- `data/live_drops.json` has **8 of 24** drops pointing at unpublished designs.
  The storefront is safe — `build.py` filters them by `slug in lookup` — but it
  drops them *silently*, so `/drops/` renders 16 and nothing reports the loss.

**Proposed division of labour** (agreed interface, so neither agent has to edit
the other's code):

- **Arena** publishes the contract: extend the existing sanity-gate step in
  `refresh.yml` (which already does `import build`) to emit a machine-readable
  `data/catalogue-live.json` — the authoritative sellable slugs, their
  collection, partner and published URL — on every build. Additive; one file.
- **ChatGPT** consumes it: `marketing/plan.py` filters its queue against
  `catalogue-live.json` instead of reading `data/products.json` directly, and
  `live_engine.py` reports drops it had to discard rather than swallowing them.

Neither agent should fix this by rewriting the other's module.

---

## 6. Landmines — things that will bite you

**These scripts execute on import.** They have no `if __name__ == "__main__"`
guard, so importing them runs them:

| Script | What importing it does |
|---|---|
| `dl.py` | Crawls Viralstyle, writes images into `site/img/` |
| `scrape_list.py` | Crawls the 4 collections, writes `data/` |
| `scrape_products.py` | Crawls every product, writes `data/` |
| `sheet.py` | Builds contact sheets **and overwrites `data/order.json`** |

`src/make_offline.py` and `src/set_site.py` were fixed and are now import-safe.
If you touch any of the four above for another reason, add the guard while you
are in there — it is a two-line change.

**Other things that have already caused damage:**

- `marketing/social_watch.py` **overwrites `marketing/social-signals.json` with
  error stubs when it has no network.** Run it in a sandbox, never in place,
  unless you intend to replace curated evidence.
- `tests/test_three_day_pulse.py` and `tests/test_commercial_agent.py` used to
  run the real generators in the working tree, which rewrote four tracked files
  (up to 5,953 deleted lines). They now use `generator_sandbox()`. If you add a
  generator test, do the same.
- `json.load(open(...))` leaks the handle and depends on the platform default
  encoding. `src/build.py` now has a `read_json()` helper — use it, or a `with`
  block. Roughly 20 leaks remain in one-off tools; documented in
  `BLUEPRINT.md` §13.
- Dates: use `build.utc_today()`, never `datetime.date.today()`. The cron and
  the freshness gate are UTC; the operator is UTC+1. A local-date build
  disagrees with CI for the last hour of every UTC day.
- `unittest discover -s tests -t .` needs `tests/__init__.py` to exist. It does.
  Don't delete it.

---

## 7. Commit style

- Imperative subject, under ~72 chars. Explain *why* in the body, especially
  when a change is fixing a failure mode rather than adding a feature.
- Never commit `site/` and `src/` changes in separate commits that land
  out of order — the tests read the committed `site/`, so a `src/` change
  without its rebuild leaves the repo red.
- If your commit touches the other agent's paths, say so in the first line of
  the body.
