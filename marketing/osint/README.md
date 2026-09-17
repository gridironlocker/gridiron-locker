# Gridiron Locker — Private OSINT Prospect Engine

A private, modular prospect-discovery system that finds publicly available
football fan/creator/community prospects for Gridiron Locker outreach,
scores them, and exports them for **manual** review. It never sends email,
never touches the public storefront, and never commits prospect data to this
(public) repository.

    python3 -m marketing.osint discover
    python3 -m marketing.osint refresh
    python3 -m marketing.osint export
    python3 -m marketing.osint stats
    python3 -m marketing.osint verify [--live]

---

## 1. Safety model (enforced in code, not just policy)

| Rule | How it is enforced |
|---|---|
| Only public, intended-for-contact data | Collectors read documented public APIs, public RSS feeds and public web pages |
| No login/paywall/CAPTCHA/anti-bot bypass | There is no bypass code anywhere; a robots.txt `Disallow` skips the site (`http.py`) |
| Never guess emails | `emails.py` only *extracts* published addresses (incl. `name AT domain DOT com` obfuscations); no address is ever generated |
| No SMTP, no test emails | Validation = syntax + DNS MX/A + disposable list; anything uncertain is `UNVERIFIED` |
| Never send email | No outbound mail code exists; outreach is manual by design |
| Respect rate limits | Per-host minimum interval (2.5 s), response size cap, query budgets per run |
| No private-person harvesting | Only business/creator/community accounts with public contact intent |

## 2. Data sources — what is live, what is disabled and why

| Collector | Status | Access path | Notes |
|---|---|---|---|
| `podcasts` | **LIVE** | Apple iTunes Search API (public, documented, no key) | Team-keyword search → public directory metadata → the show's own public RSS feed (description, website, `itunes:owner` contact email, latest episode date) |
| `news` | **LIVE** | Google News RSS (public feed, same source the repo's trend system already uses) | Finds independent publishers covering our teams; major national outlets are skipped |
| `websites` | **LIVE** | Curated seeds (`seeds/websites.json`) + shared website enrichment | Robots-checked crawl of homepage + up to 2 contact-ish pages per site; extracts only published emails; records public social links (stored, never crawled) |
| `youtube` | **LIVE with key** | Official YouTube Data API v3 | Set `YOUTUBE_API_KEY`. Public channel search + statistics; a business email only when the channel itself publishes one in its description with contact intent |
| `instagram` | **DISABLED** | — | Instagram ToS prohibits automated collection; Basic Display API shut down Dec 2024; Graph API only covers accounts you own. Manual CSV import instead |
| `tiktok` | **DISABLED** | — | ToS prohibits scraping; Research API is restricted to approved academics. Manual CSV import instead |
| `x` | **DISABLED** | — | ToS prohibits scraping; official search API requires a paid tier (engine targets $0/month). Manual CSV import instead |
| `pinterest` | **DISABLED** | — | ToS prohibits scraping; official API has no public creator search. Manual CSV import instead |

Toggles: `OSINT_ENABLE_COLLECTORS=podcasts,websites` (allow-list) /
`OSINT_DISABLE_COLLECTORS=news` / `--collectors podcasts` on the CLI.

## 3. Open-source tool research (required by the spec)

Evaluated before coding; **none were adopted**. The engine is stdlib-only
(`urllib`, `sqlite3`, `csv`, `json`, `xml`, `html.parser`, `socket`), matching
the repository's no-third-party-runtime-deps philosophy.

| Tool | License / maintenance (checked 2026-09) | Why not used |
|---|---|---|
| **Instaloader** | MIT; actively maintained (13k+ stars) | Works by logging in a real account or hammering logged-out endpoints Instagram ToS-prohibits and rate-limits; account-ban risk; and it downloads profiles by name — it has no prospect *search*. Violates this engine's own no-bypass rule |
| **Maigret** | MIT; actively maintained (v0.5.0, 3,000+ sites) | Builds a dossier on a *person* by username across thousands of sites. This is a business-prospect engine, not a person-investigation tool; the mass automated cross-site probing also violates many target sites' ToS |
| **Sherlock** | MIT; community-maintained | Same category as Maigret (username enumeration across platforms), same problems |
| instagrapi / private APIs | MIT | Require impersonating a logged-in client — explicitly forbidden |

Selected dependencies: **none**. Zero third-party packages, $0/month, no
supply-chain surface. The legitimate sources (iTunes Search, Google News RSS,
public websites, YouTube Data API) are all reachable with the standard
library.

## 4. Where the data lives (public repo safety)

This repository is **public** and `refresh.yml` commits with `git add -A`
twice a day, so prospect data (emails!) can never live in the tree:

```
marketing/osint/state/      <- gitignored: prospects.db, suppression.csv
marketing/osint/exports/    <- gitignored: CSV exports
```

Both paths are enforced in `.gitignore` **and** in code: the exporter refuses
to write under `site/`, `marketing/social/` or `ops/`, and every CLI command
honours `OSINT_STATE_DIR` / `OSINT_EXPORTS_DIR` overrides (used by tests and
CI so a verification run writes nothing into the repo).

> Deviation from the spec, on purpose: the spec suggested
> `data/osint/suppression.csv`, but the repository contract (AGENTS.md §3.2 /
> hard rule 2) says marketing code must never write to `data/`. Suppression
> lives at `marketing/osint/state/suppression.csv` instead — same semantics,
> one gitignored tree for all private state.

## 5. How to run (locally — this is the normal mode)

```bash
# discover prospects for all four teams (podcasts + news + websites)
python3 -m marketing.osint discover

# one team only, more queries per team
python3 -m marketing.osint discover --team michigan --max-queries 6

# see what would run, write nothing
python3 -m marketing.osint discover --dry-run

# full refresh: discover + re-verify stale websites + rescore everything
python3 -m marketing.osint refresh

# CSV exports (all + high-priority) into marketing/osint/exports/
python3 -m marketing.osint export --min-score 75

# aggregate stats / daily report (emails always masked)
python3 -m marketing.osint stats
python3 -m marketing.osint report

# browse what's stored
python3 -m marketing.osint list --min-score 60 --email
```

YouTube collection additionally needs your own free API key:

```bash
export YOUTUBE_API_KEY=...   # same variable the marketing stack already uses
python3 -m marketing.osint discover --collectors youtube
```

## 6. Manual outreach workflow

The engine's job ends at export. Humans send the email.

```bash
# after you send email by hand:
python3 -m marketing.osint status --id 42 --to CONTACTED
python3 -m marketing.osint note --id 42 --text "sent 2026-09-17, Michigan angle"

# or bulk-import a spreadsheet of outcomes:
python3 -m marketing.osint import --statuses outcomes.csv
```

`outcomes.csv` columns: `public_email` (or `id` / `username`), `status`
(`email_sent`, `reply_received`, `interested`, `not_interested`,
`unsubscribe`, `bounced`, ...), optional `note`. `unsubscribe`/`opt_out` map
to permanent suppression.

Manual prospects (the legitimate path for Instagram/TikTok/X/Pinterest —
public info you copy while browsing normally):

```bash
python3 -m marketing.osint import --prospects manual.csv
```

Columns: `name,platform,username,profile_url,website,team,prospect_type,
public_email,contact_source_url,followers,notes`.

## 7. Suppression (permanent)

```bash
python3 -m marketing.osint suppress --key someone@example.com --reason "opted out"
python3 -m marketing.osint suppress --key fansite.com --kind domain --reason "asked no contact"
python3 -m marketing.osint status --id 42 --to SUPPRESS   # suppresses every identity key of #42
```

Suppressed identities are re-recorded on rediscovery but always with status
`SUPPRESS`, are excluded from every export, and survive cleanup forever.
Storage: `state/suppression.csv` (durable) mirrored into the DB.

## 8. Scoring (explainable, 0–100)

`Team relevance 25 · Football activity 20 · Audience 15 · Engagement 15 ·
Commercial relevance 10 · Public contact 10 · Freshness 5`

Every component carries a reason string; `score_reason` and the JSON
`score_breakdown` are stored per prospect and exported (`reason` column).
Unknown data scores **0** and says so — engagement numbers are never
fabricated. Bands: 90+ HIGH_PRIORITY · 75+ QUALIFIED · 60+ REVIEW · else
LOW_PRIORITY. A separate `commercial_score` re-weights the business angle and
`confidence_score` measures how much real evidence backs the row.

## 9. Trend-aware discovery

`discover` reads the repository's existing trend system
(`data/trends.json`, read-only) and augments each team's search queries with
current subjects (player/coach names from `gaps` + `entity_mentions`), so
discovery follows what fans are talking about *now*. `--no-trends` disables.

## 10. Retention & cleanup

```bash
python3 -m marketing.osint cleanup            # dry-run
python3 -m marketing.osint cleanup --days 180 --apply
```

Removes prospects not seen for N days, preserving suppression records and
every protected status (CONTACTED, INTERESTED, CUSTOMER, PARTNER, ...).

## 11. Scheduling

The engine is **not** wired into the public `refresh.yml` on purpose: this
repository is public, so scheduled runs here could not keep the resulting
prospect database anywhere safe. Options:

1. **Local (recommended)**: run `discover`/`refresh` on your own machine —
   data stays in gitignored local files. A weekly `refresh` + `export` is the
   intended rhythm.
2. **CI health check**: `.github/workflows/osint-verify.yml` runs the test
   suite plus a small *real* live discovery run on a GitHub runner (full
   network) into a throwaway database, printing aggregate counts and masked
   emails only — safe for public logs, and it proves the live pipeline works
   on every change to this package. It stores and commits nothing.
3. **If the repo ever goes private**: duplicate that workflow with a cron
   trigger and an artifact upload; the engine code needs no changes.

## 12. Verification

```bash
python3 -m marketing.osint verify         # offline checks (config, DB, scoring, guards)
python3 -m marketing.osint verify --live  # + a small REAL discovery run into a temp DB
```

`verify --live` fails if zero prospects are discovered or any enabled
collector hard-errors — the pipeline's health is measured by real output,
not by code existing.

## 13. Layout

```
marketing/osint/
  __main__.py     CLI            engine.py    pipeline orchestration
  config.py       paths/keywords db.py        SQLite repository
  scoring.py      explainable    dedupe.py    cross-platform matching
  emails.py       extraction+DNS suppression.py permanent opt-outs
  http.py         polite fetcher exporters.py CSV (+ site/ write guard)
  importers.py    manual CSVs    report.py    aggregate reporting
  cleanup.py      retention      keywords/    one JSON per team
  collectors/     one module per source (stubs included, honestly DISABLED)
  seeds/          curated website seeds
  state/          gitignored runtime data   exports/  gitignored CSVs
```

## 14. Limitations (honest list)

* Instagram/TikTok/X/Pinterest are import-only (see §2). That is a feature of
  the safety model, not a missing feature.
* Audience/engagement for podcasts is usually unknown → those score
  components are 0 with an explicit reason. Podcasts are scored on content,
  activity and contactability.
* `itunes:owner` emails are public-by-design but not always *deliberately*
  published for contact; they are imported with category
  `PUBLIC_RSS_OWNER_EMAIL` so a human sees the provenance before outreach.
* Google News RSS surfaces publishers, not individual creators; discovery
  quality depends on the keyword files (`keywords/*.json` — tune freely).
* The 2.5 s/host politeness delay means a full four-team run with website
  enrichment takes minutes. That is intentional.
