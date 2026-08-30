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
├── .github/workflows/
│   ├── deploy.yml        # publishes ./site to GitHub Pages on push to main
│   └── refresh.yml       # daily automation (see §6)
├── site/                 # the generated storefront (deployed as-is)
│   ├── *.html            # 158 pages: home, collections, 134 products, guides, trust pages
│   └── img/              # 1,019 self-hosted images (1,011 product + hero/lifestyle)
├── src/                  # the generator (Python, no third-party runtime deps)
│   ├── build.py          # builds every HTML page, schema, sitemap, robots
│   ├── catalog.py        # per-design copy facts (name / art / kw / theme)
│   ├── collections_data.py  # collection brand data + SEASON (2026 context)
│   ├── seocopy.py        # template-varied page copy
│   ├── trends.py         # builds the headline trend report
│   ├── indexnow.py       # pings search engines on rebuild
│   ├── make_offline.py / set_site.py
│   └── config.json       # site name, domain, email, twitter, IndexNow key
├── data/                 # the source-of-truth snapshots
│   ├── collections.json / facts.json / order.json
│   ├── products.json / products_live.json
│   ├── trends.json       # headline snapshot (10-day window)
│   └── people.json       # current vs throwback player/coach context (added)
├── marketing/            # promotion planning (does NOT touch site/)
│   ├── plan.py           # scores 134 designs → writes plan.json
│   ├── plan.json         # full queue, calendar, best-times, gaps, who's-who
│   ├── dashboard.html    # the planner UI (6 tabs)
│   ├── tz-verify.js      # timezone conversion tests
│   ├── social-accounts.md
│   └── social/           # content kit + images (see §8)
├── scrape_list.py / scrape_products.py / dl.py   # crawl Viralstyle
├── sheet.py / shot.py
├── product-index.csv     # 135-row product index
├── trend-report.md       # auto-generated trend report
└── README.md / HOW-TO-ADD-A-DESIGN.md / DEPLOY-GITHUB.txt
```

---

## 3. The storefront (site/)

- **158 HTML pages:** home, 4 collections, **134 product pages**, 4 buying
  guides, size guide / shipping / FAQ / about / contact / trademark notice /
  privacy / 404.
- **Collections:** Cleveland Browns (78) · Green Bay Packers (34) · Michigan
  (12) · Dallas (10).
- **Product page** mimics NFLShop: gallery + colourway swatches, style chips,
  size selector, price + slashed compare-at + save %, star rating, urgency
  strip, trust badges, sticky mobile buy bar.
- **SEO:** unique title/description/canonical/OG+Twitter cards per page;
  schema.org JSON-LD (Organization, WebSite+SearchAction, CollectionPage,
  ItemList, Product+Offer+AggregateRating, BreadcrumbList, FAQPage, Article);
  `robots.txt` + `sitemap.xml` + `sitemap-images.xml`.
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

**Dashboard** (`dashboard.html`, 6 tabs): Post queue · 14-day calendar ·
Best times · News gaps · **Who's who** · Image prompts. All times are authored
in `America/New_York` and converted to the viewer's zone (Africa/Casablanca
for the operator) in-browser.

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

Live accounts: X `@gridironlocker` · TikTok `@gridironlocker` · YouTube
`@Gridironlocker` · Pinterest `gridironlockergear` · Facebook (numeric profile
ID — vanity URL not yet claimed) · Instagram `@gridironlocker` **(disabled)**.

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
- **In flight:** Instagram re-launch + compliance decision (§9).

---

## 11. Command cheat sheet

```bash
python3 scrape_list.py        # re-crawl the 4 collections (Mondays / manual)
python3 scrape_products.py    # pull details for every product
python3 dl.py                 # download new imagery
python3 src/trends.py         # refresh the headline trend report
python3 src/build.py          # rebuild the site from data/
python3 marketing/plan.py     # regenerate marketing/plan.json (134 designs)

# preview the planner
cd marketing && python3 -m http.server 8000   # open /dashboard.html

# verify timezone conversions
node marketing/tz-verify.js
```

---

## 12. Open questions

1. **Compliance direction** — license, pivot to original designs, or status quo? (§9)
2. **New Instagram account** — what handle/bio/content under the chosen direction?
3. **Facebook vanity URL** — claim `facebook.com/gridironlocker` or leave numeric?
4. **Content gaps** — designs for Watson, Underwood, Monken, Whittingham, Parsons?
