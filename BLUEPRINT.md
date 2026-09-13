# Gridiron Locker — Project Blueprint

> One document that explains what this project is, how it's built, where the
> money flows, and what the open decisions are. Last updated 2026-08-30.

---

## 1. What this project is

**Gridiron Locker** is a print-on-demand football fan-apparel business run as a
static website. The site is an SEO storefront that ranks for fan keywords
("cleveland browns shirts", "go pack go tee", …) and sends every visitor to the
real **Viralstyle** checkout. Nothing is shipped from here — Viralstyle
fulfills on demand, so there is zero inventory and zero warehouse risk.

- **Site:** https://gridironlocker.github.io/gridiron-locker
- **Store backend:** Viralstyle (4 store collections, one per team)
- **Operator timezone:** Africa/Casablanca
- **Audience:** US football fans (America/New_York)

### Money flow

```
Buyer searches  →  Google ranks a product page  →  visitor lands on site
→  clicks "Buy"  →  Viralstyle campaign checkout  →  Viralstyle prints & ships
→  Viralstyle pays out the campaign revenue
```

The website is a ranking engine; Viralstyle is the fulfillment + payment layer.

---

## 2. Repository map

```
gridiron-locker/
├── .github/workflows/    # all four share `concurrency.group: pages-deploy`
│   │                     # except health-check, which only reads (see §6)
│   ├── deploy.yml        # publishes ./site to GitHub Pages on push to main
│   ├── refresh.yml       # daily automation (see §6)
│   ├── health-check.yml  # daily check of the LIVE site (ops/health_check.py)
│   └── add-campaign.yml  # manual dispatch: capture Viralstyle slugs → data/
├── site/                 # the generated storefront (deployed as-is) · 76 MB img/
│   ├── *.html            # 206 files: 197 public (85 are noindex redirect
│   │                     # stubs) + 9 internal ops/ & marketing/
│   └── img/              # 1,726 self-hosted images (product + hero/lifestyle)
├── src/                  # the generator (Python, no third-party runtime deps)
│   ├── build.py          # builds every HTML page, schema, sitemap, robots
│   ├── catalog.py        # per-design copy facts (name / art / kw / theme)
│   ├── collections_data.py  # collection brand data + SEASON (2026 context)
│   ├── landing.py        # product-page copy generator (the SEO landing page)
│   ├── seocopy.py        # template-varied page copy
│   ├── trends.py         # builds the headline trend report
│   ├── scout.py / hq.py  # internal ops dashboards (noindex)
│   ├── indexnow.py       # pings search engines on rebuild
│   ├── nudge_google.py   # GSC live inspection + WebSub after deploy
│   ├── make_offline.py / set_site.py / crop_art.py / drops_page.py
│   └── config.json       # site name, domain, email, twitter, IndexNow key
├── tests/                # 145 tests · `python3 -m unittest discover -s tests -p "test_*.py"`
│   ├── test_layout.py    # 118 guard rails on the built site/ (the contract)
│   ├── test_health_check.py # 16 tests for ops/health_check.py (need requirements-dev.txt)
│   ├── test_three_day_pulse.py / test_commercial_agent.py # run the marketing
│   │                       # generators inside a throwaway copy of the repo
│   └── testutil.py       # that sandbox - see §13, tests must not mutate the repo
├── data/                 # the source-of-truth snapshots
│   ├── collections.json / facts.json / order.json / delisted.json
│   ├── products.json / products_live.json
│   ├── mayzing_products.json / mayzing_michigan.json  # Cleveland + Michigan
│   │                       # catalogues, migrated off Viralstyle 2026-09-12
│   ├── fulfillment.json  # partner naming + 'hold' list for the migration
│   ├── creators.json     # Joe's picks + INTERNAL commission terms
│   ├── live_drops.json / campaigns_extra.json
│   ├── trends.json       # headline snapshot (10-day window)
│   └── people.json       # current vs throwback player/coach context (added)
├── marketing/            # promotion planning (does NOT touch site/)
│   ├── plan.py           # scores every live design → writes plan.json
│   ├── commercial_agent.py # NFL fan commerce scoring + daily predictor
│   ├── social_watch.py    # public web/social signal collector
│   ├── three_day_pulse.py # rolling 3-day trend-to-product brief
│   ├── publisher.py       # dry-run/official API publishing adapters
│   ├── plan.json         # full queue, legacy calendar, best-times, gaps
│   ├── three-day-pulse.json # short-lived today/tomorrow/+2 copy brief
│   ├── social-signals.json # source status + public trend evidence
│   ├── commercial-brief.json # top-five matches, tests, economics
│   ├── performance-memory.json # measured learnings input (never invented)
│   ├── approved-images.json # owner-approved public image manifest
│   ├── dashboard.html    # the planner UI (8 tabs, led by 3-day pulse)
│   ├── tz-verify.js      # timezone conversion tests
│   ├── social-accounts.md
│   └── social/           # content kit + images (see §8)
├── artwork-source/       # 62 MB of PNG masters - source art, NEVER deployed (see §13)
├── scrape_list.py / scrape_products.py / dl.py   # crawl Viralstyle
├── replay_updates.py     # re-injects the hand-added campaigns a re-crawl drops
├── add_campaign.py       # capture one Viralstyle slug into data/campaigns_extra.json
├── qa_audit.py           # read-only SEO/schema/link audit of site/ (no network)
├── qa_http.py            # the same over HTTP against a running server
├── ops/health_check.py   # production health check (the live-site gate)
├── requirements-dev.txt  # requests / bs4 / lxml / Pillow - tooling + tests only
├── sheet.py / shot.py
├── product-index.csv     # 111-row product index (was stale at "135")
├── trend-report.md       # auto-generated trend report
└── README.md / HOW-TO-ADD-A-DESIGN.md / DEPLOY-GITHUB.txt / QA-REPORT.md
    / SITE-BLUEPRINT.md / DESIGN-BLUEPRINT.md / TREND-MASTER-GRIDIRONLOCKER.md
```

---

## 3. The storefront (site/)

> Counts verified 2026-09-13 against the committed build. Re-derive them with
> `python3 qa_audit.py` (catalogue, per-collection split, audited pages) and
> `grep -o '<loc>' site/sitemap.xml | wc -l` (sitemap size) — do not trust this
> section if those disagree.

- **206 HTML files:** 197 public + 9 internal (`ops/`, `marketing/`). Of the
  public set, **85 are noindex redirect stubs** for retired slugs, leaving
  **112 indexable pages**: home, 4 collections, **84 product pages**, 5 buying
  guides, `/search/`, `/drops/`, `/fan-trend-index/`, `/2026-season/`,
  `/michigan/joe/`, and the trust pages (size guide / shipping / FAQ / about /
  contact / trademark notice / privacy / 404).
- **Collections:** Green Bay Packers (37) · Cleveland Browns (19) · Michigan
  (18) · Dallas (10). Fulfilment split: **Viralstyle 47 / Mayzing 37** —
  Cleveland and Michigan check out on Mayzing, Green Bay and Dallas on
  Viralstyle, and every shipping/returns claim on a page is scoped to the
  partner that actually prints that design.
- **Product page is an SEO landing page, NOT a mini-checkout.** Gridiron Locker
  does discovery and persuasion; the fulfilment partner does configuration and
  the transaction. So a product page carries a big gallery, the design story,
  the *verified* apparel styles / colourways / sizes, product details, shipping
  and an FAQ — and exactly one conversion action, **SHOP NOW →**, placed three
  times (hero, mid-page band, sticky mobile bar). There is deliberately **no
  style picker, no size picker, no colourway picker and no checkout button**.
  `tests/test_layout.py::ProductPages` enforces this and fails the build if a
  picker comes back.
- **No fabricated trust signals.** No star ratings, no review counts, no
  compare-at pricing, no "only N left", no urgency strip. Checkout happens on
  the partner, so there is no sales feed to justify a "best seller" badge —
  the honest substitute is the **Trending Now** rail driven by the Fan Trend
  Index. `test_no_fabricated_trust_signals` bans the literal strings
  `aggregateRating`, `ratingValue`, `reviewCount`, `class="stars"`,
  `class="strike"`, `class="save"`, "left in stock", "selling fast", "Hurry".
- **SEO:** unique title/description/canonical/OG+Twitter cards per page;
  schema.org JSON-LD (Organization, WebSite+SearchAction, CollectionPage,
  ItemList, Product+Offer, BreadcrumbList, FAQPage, Article);
  `robots.txt` + `sitemap.xml` (**108 URLs**) + `sitemap-images.xml`.
  *AggregateRating is **not** emitted* — an earlier revision of this document
  claimed it was, which is exactly the kind of fabricated signal the guard
  rails above forbid.
- **Imagery:** 1,726 files under `site/img/` (self-hosted Viralstyle WebPs +
  hero/lifestyle art), plus 44 designs still hot-linking Mayzing CDN mockups.
  The PNG masters live in `artwork-source/` and are never deployed — see §13 on
  the repository weight that costs.
- **Trademark framing:** "fan-made / independent / not affiliated" disclaimers
  sitewide + a dedicated trademark notice with a takedown route. *(See §9 —
  this framing does not protect the social accounts.)*


---

## 4. Data pipeline (Viralstyle → data → site)

```
Viralstyle store (source of truth)
   │  scrape_list.py        # re-crawl the 4 collections for new/removed slugs
   │  scrape_products.py    # pull details for every product
   │  dl.py                 # download product imagery
   ▼
data/*.json                 # collections, products, facts, order, trends
   │  src/build.py          # regenerates every page, schema, sitemap
   ▼
site/  ──(deploy.yml)──▶   GitHub Pages
```

New products need one line of copy facts in `src/catalog.py`
(`name`, `art`, `kw`, `theme`) so the generated page reads like a human wrote it.

---

## 5. The marketing planner (marketing/)

`plan.py` reads the data snapshots + `SEASON` and writes one file:
`marketing/plan.json`. It never imports the site generator and never writes
under `site/` — planning and storefront are fully separated.

**Scoring model** (each design starts at 50, clamped 0–100):
- `+22` when the design matches a 2026 search term from `SEASON[collection]["hot"]`
- `+12` per repeated headline mention of a named entity (cap +30)
- `+6` when the theme is "playoff" or "player"
- `-25` when the design is a throwback

**Dashboard** (`dashboard.html`, 8 tabs): **3-day pulse** · Product queue ·
Best times · News gaps · **Who's who** · Opportunities · **Commercial agent** ·
Image prompts. The 3-day pulse is the primary rolling brief: it refreshes from
public web/social evidence, matches existing products, and prepares only today,
tomorrow, and +2 days. The Commercial agent remains the deeper scoring and
strategy view without claiming unavailable analytics or cost data. All times are
authored in `America/New_York` and converted to the viewer's zone
(Africa/Casablanca for the operator) in-browser.

`marketing/commercial_agent.py` writes `commercial-brief.json`; it reads the
headline snapshot, scored planner, season calendar, and the human-maintained
`performance-memory.json`. It does not publish. Current team/player-named
social creative is held until licensing is verified.

---

## 6. Automation (the "autonomous SEO program")

Two GitHub Actions:

- **deploy.yml** — on every push to `main`, uploads `./site` to GitHub Pages.
- **refresh.yml** — daily at **06:15 UTC**: re-crawls Viralstyle on Mondays,
  refreshes trend data, rebuilds the site, and commits as
  `Auto-refresh: trends + rebuild <date>` (commit `6cbcc26` is the latest).

Net result: the storefront self-updates without touching code.

---

## 7. Season intelligence (2026)

From `src/collections_data.py:SEASON` + `data/trends.json`:

| Collection | Live storyline | Opener | Hot search terms |
|---|---|---|---|
| Cleveland Browns | **Sanders vs Watson QB1** (Watson named starter Aug 24) | Sep 13 @ Jacksonville | "shedeur sanders shirt", "browns qb1 2026 shirt" |
| Green Bay Packers | Jordan Love QB1, Micah Parsons on roster | Sep 13 @ Minnesota | "jordan love 2026 shirt", "go pack go 2026 tee" |
| Dallas Cowboys | Prime-time SNF opener | Sep 13 @ NY Giants | "cowboys week 1 shirt", "dallas 2026 shirt" |
| Michigan | Bryce Underwood captain, Whittingham's 1st season | **Sep 5** vs W. Michigan | "bryce underwood shirt", "go blue 2026 tee" |

**Who's who** (`data/people.json`, surfaced in the dashboard tab):

| Person | Role | Status |
|---|---|---|
| Deshaun Watson | Browns starting QB | Current (no design yet) |
| Shedeur Sanders | Browns rookie QB | Current — promote |
| Jordan Love | Packers QB1 | Current — promote |
| Bryce Underwood | Michigan QB + captain | Current (no design yet) |
| Todd Monken / Kyle Whittingham / Micah Parsons | HC / HC / LB | Current (no design yet) |
| Denzel Ward | Browns CB | Current — promote |
| Joe Flacco · Myles Garrett · Kevin Stefanski · J.J. McCarthy | former | **Throwback — do not use** |

---

## 8. Social media system

Live accounts: X `@gridironlocker1` & `@gridironlocker` · Instagram `@gridironlocker1` · Threads `@gridironlocker1` · Facebook `GridironLocker` · Pinterest `gridironlockergear` · YouTube `@Gridironlocker` · TikTok `@gridironlocker`. (Note: old bare Instagram `@gridironlocker` was disabled; active handle is `@gridironlocker1`).

`marketing/social/` holds the content kit:

| File | Purpose |
|---|---|
| `social-accounts.md` | handles, bios (no emojis), account registry + fixes |
| `post-ready.md` | Title → Image/Video → Caption → Hashtags → Post time, current-verified |
| `content-pack.md` | full image set, 7 video scripts, 7-day schedule, engagement rules |
| `competitor-playbook.md` | rival research + trend highlight |
| `*.jpg` | AI-rendered fashion-editorial mockups (logo-free, faces cropped) |

Posting-time rule baked into all captions: **Casablanca = US Eastern + 5 hours**
(Aug–Oct 2026).

---

## 9. ⚠️ The compliance problem (the live fork)

**Instagram permanently disabled `@gridironlocker`** for Community Standards.
This is the NFL/team trademark pattern: unlicensed team names + player names
("Cowboys", "Browns", "Dawg Pound", "Packers", "Michigan", Shedeur Sanders,
Jordan Love) were used in bios, captions, and hashtags. The "not affiliated"
disclaimer on the site does not make that legal or acceptable to Meta.

Consequences to plan around:
- Facebook is the same company as Instagram — same risk, same enforcement.
- TikTok, YouTube, and Pinterest also remove unlicensed merch on IP complaints.
- New accounts are device/IP/phone-linked, so repeats get taken down faster.

**Three paths (decision needed):**
1. **Get licensed** — NFLPA (player names/likenesses), CLC (college marks), or
   a licensed POD partner. Durable but expensive/slow; rarely viable solo.
2. **Pivot to original designs** — keep "Gridiron Locker" football culture,
   drop ALL team names, player names, logos, and likenesses. The only version
   that reliably survives on Meta/TikTok.
3. **Keep the current model** — accounts will keep expiring.

The whole social kit in `marketing/social/` was built for the pre-disable model;
it needs a compliance rework before the new Instagram account (or any current
account) posts again.

---

## 10. Status snapshot

- **Deployed:** storefront live on GitHub Pages; daily auto-refresh active.
- **Merged (PRs 1–12):** site launch, SEO program cycle 1, marketing dashboard,
  Morocco-timezone posting times, design polish.
- **Open PR #13** (`arena/01a04a8b-gridiron-locker`): social launch kit,
  competitor playbook, dashboard "Who's who" tab.
- **In flight:** Compliance-safe publishing on `@gridironlocker1` and live drops traffic (§9).

---

## 11. Command cheat sheet

```bash
python3 scrape_list.py        # re-crawl the 4 collections (Mondays / manual)
python3 scrape_products.py    # pull details for every product
python3 dl.py                 # download new imagery
python3 src/trends.py         # refresh the headline trend report
python3 src/build.py          # rebuild the site from data/
python3 marketing/live_engine.py  # regenerate marketing/plan.json + live_drops.json + pinterest_feed.csv

# preview the planner
cd marketing && python3 -m http.server 8000   # open /live.html or /dashboard.html

# verify timezone conversions
node marketing/tz-verify.js
```

---

## 12. Open questions

1. **Compliance direction** — license, pivot to original fan-culture designs, or status quo? (§9)
2. **Active Instagram account** — verified as `@gridironlocker1` using safe fan-culture copy from copy_vault.
3. **Facebook vanity URL** — claimed at `facebook.com/GridironLocker`.
4. **Content gaps** — designs for Watson, Underwood, Monken, Whittingham, Parsons?

---

## 13. Repository weight and hygiene (open, deliberate)

Measured 2026-09-13:

| | |
|---|---|
| `.git` pack | **103.5 MiB** |
| Tracked files | **2,116** |
| `site/img/` | **76 MB**, 1,726 files |
| `artwork-source/` | **62 MB**, 28 tracked PNGs (several ~3 MB) |
| `.webp` in repo | **1,711** |
| Git LFS | **not in use** (`.gitattributes` is only `* text=auto`) |

**Why this matters.** `artwork-source/` is source art: `src/crop_art.py` derives
the deployed hero and team-card crops from it, and the PNG masters themselves
are never copied into `site/`. So 62 MB is downloaded by every clone and by
`actions/checkout@v4` in four workflows, purely to be ignored. On top of that
`refresh.yml` runs twice a day and commits with `git add -A`, and the 1,711
regenerated WebPs churn the pack on every refresh. GitHub's soft warning lands
at 1 GB and the hard block at 100 MB *per file*, so this is a slow-burn problem,
not an emergency — but CI checkout time grows monotonically and never recovers.

**Not fixed here, on purpose.** Reclaiming the space means `git filter-repo`
across the whole history, which rewrites every commit SHA. That is destructive,
it invalidates any open PR or local clone, and it needs a mirror backup first.
It is an owner decision, not something to slip into a bug-fix branch.

**Recommended, in order:**

1. **Stop the bleeding (safe, no rewrite).** Track `artwork-source/` with Git
   LFS, or move it to a GitHub Release asset / object storage and leave a
   pointer file. Add the derived `site/img/*.webp` to LFS too. This caps future
   growth immediately.
2. **Then reclaim (destructive, planned).** `git filter-repo` to purge the
   historical PNG blobs, with a full mirror backup and a coordinated re-clone.
   Note `refresh.yml`'s bot commits will need re-authenticating against the new
   history.
3. **Consider not committing `site/` at all.** It is a build artefact, fully
   reproducible from `data/` + `src/`. Building it in the deploy workflow
   instead of committing it would remove ~76 MB of churn from history forever —
   at the cost of making `deploy.yml` need the generator, and of losing the
   ability to eyeball a diff of the published HTML. Trade-off, not an obvious
   win; the guard-rail tests currently read the committed `site/`, which is
   genuinely useful.

### Test-suite hygiene (fixed 2026-09-13)

Two rules that were broken and are now enforced:

- **A test run must not mutate the repository.** `test_three_day_pulse.py` and
  `test_commercial_agent.py` used to shell out to the real marketing generators
  in place, which rewrote four tracked files (`plan.json`, `social-signals.json`,
  `three-day-pulse.json`, `commercial-brief.json`) — up to 5,953 deleted lines
  when run without network, because `social_watch.py` happily overwrites good
  evidence with error stubs. Combined with `refresh.yml`'s `git add -A`, a
  developer who ran the tests and pushed would commit a degraded marketing
  brain. They now run inside `tests/testutil.py::generator_sandbox`, a
  throwaway copy of `src/` + `data/` + `marketing/*.py|json`, and
  `test_generators_never_touch_the_real_repository` fails the suite if a tracked
  artefact ever changes during a run.
- **A build being out of date is not a schema defect.** `test_layout.py` used to
  assert `offers.validFrom == build.TODAY`, so on any day where the committed
  site had not yet been rebuilt the suite reported "merchant schema is wrong on
  84 pages" — a message that sends you to the wrong file. That assertion is now
  a real invariant (valid ISO date, not in the future, inside the offer window)
  and staleness is asserted separately in `BuildFreshness`, which fails with
  `STALE BUILD: … refresh.yml should have rebuilt it today` and tells you to go
  look at the Actions runs. Tolerance is `MAX_BUILD_AGE_DAYS = 2`: refresh runs
  twice daily, so a healthy repo is never more than a day behind, and the slack
  only absorbs a run between midnight UTC and the 06:15 refresh.

`src/build.py` also stopped depending on the machine's local timezone —
`utc_today()` is now the single definition of "today", matching the UTC cron in
`refresh.yml` and its freshness gate. Previously a local rebuild in
Africa/Casablanca (UTC+1) stamped tomorrow's date for the last hour of each UTC
day, so a hand-run build disagreed with CI's output.

### Scripts that run on import (partially fixed)

Several top-level scripts execute at *import* time because they have no
`if __name__ == "__main__"` guard. That is survivable for a CLI script you only
ever run, but it means no tool can safely import them to inspect or test them:

| Script | What importing it does | Status |
|---|---|---|
| `src/make_offline.py` | deletes and rebuilds an **86 MB** `site-offline/` tree | **fixed** — work moved into `main()`, guard added |
| `src/set_site.py` | rewrites `src/config.json`, then runs a full build | safe in practice: exits on `len(sys.argv) < 2` first. Its unclosed-handle write was fixed (a real race — it spawned `build.py` as a child process to read the file it had not flushed) |
| `dl.py` | crawls Viralstyle and writes images into `site/img/` | not fixed — exits early on `IndexError` without argv, and touching the scrapers risks the refresh pipeline |
| `scrape_list.py` | crawls the 4 collections, writes `data/` | not fixed — same reasoning |
| `scrape_products.py` | crawls every product, writes `data/` | not fixed — same reasoning |
| `sheet.py` | builds contact sheets, **overwrites `data/order.json`** | not fixed — needs Pillow, so the import fails before the write on any machine without it |

The rule this violates is the same one the test sandbox exists for: *reading*
code should not mutate the repository. If you touch these files for any other
reason, add the guard while you are in there — each is a two-line change
(`def main():` + `if __name__ == "__main__": main()`), and `sheet.py` is the one
worth doing first, because silently regenerating `data/order.json` is a build
input, not an output.
