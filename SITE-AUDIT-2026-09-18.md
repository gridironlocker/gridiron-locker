# Gridiron Locker — Independent Site Audit

**Site:** https://gridironlocker.store/ · **Date:** 2026-09-18
**Repo state audited:** `64dbf89` ("Auto-refresh: trends + rebuild 2026-09-18"), branch `arena/01a0b62c-gridiron-locker`
**Scope:** the live production site, cross-checked against the repo that generates it.

---

## 0. Method, and why this audit is not a repeat of `QA-REPORT.md`

`QA-REPORT.md` (2026-09-12) is a good document and its gates are real. I re-ran
all of them first:

| Gate | Result |
|---|---|
| `python3 -m unittest discover -s tests -p "test_*.py"` | **220 passed, 17 skipped, 0 failed** |
| `python3 qa_audit.py` | **TOTAL: 0** — all 15 categories PASS |
| `python3 qa_http.py http://127.0.0.1:8123` | **PASS** — 108/108 sitemap URLs 200, 0 dead links, 0 broken images, 84/84 CTAs match catalogue, 85/85 stubs valid |
| Live-vs-repo parity | **Identical.** Spot-checked `/`, `/shop/milf/`, `/ops/board/`, `/marketing/*` — production serves exactly what is committed |

So the existing harness is green and the build is honest. **Every finding below is
something that harness is structurally unable to see.** `qa_audit.py` validates
`site/` against `build.ALL`, and `build.ALL` is derived from the same `data/`
files the pages are built from — so it can confirm the site faithfully renders
its inputs, but it cannot tell you the *inputs* are wrong, that the site leaks
files it shouldn't serve, that a legal claim in the copy contradicts a policy
document, or that a form silently loses leads.

**Environment limitation, stated plainly:** this sandbox has no outbound network
(`curl` fails with `SSL_ERROR_SYSCALL` for every host, including example.com).
Live checks were done through the platform's page-fetch proxy, which returns
rendered content but **not HTTP response headers**. So I could not measure TTFB,
cache headers, compression, security headers, HTTP→HTTPS or www canonicalisation,
or run Lighthouse. Section 8 lists exactly what needs a real browser run.

**28 findings: 4 critical, 5 high, 9 medium, 10 low.**

---

## 1. CRITICAL

### C1 — Internal business files are publicly served on production

`src/build.py:4802 sync_marketing()` and `:4821 sync_ops()` `shutil.copytree()` the
entire `marketing/` and `ops/` trees into `site/`, and `deploy.yml` uploads `site/`
as-is. GitHub Pages serves everything in that directory. **4.0 MB of internal
material is live at guessable URLs**, verified fetched from production:

| Live URL | What it exposes |
|---|---|
| `/marketing/REVENUE_PLAYBOOK.md` | Full revenue strategy, sitemap-priority tactics, the copy engine's internals, cron commands. Also leaks agent↔owner chat: *"You complained: no life, not trend-catching, same caption repeated. Fixed."* |
| `/marketing/social/competitor-playbook.md` | Named competitor research — BreakingT's "moment merch" model, their CrowdBreak platform, the NFL's creator strategy |
| `/marketing/social-accounts.md` | Every social handle **plus follower counts: `@gridironlocker` has 4 followers, `@gridironlocker1` has 94**, internal notes on which handle is really active, and a 10-row shortlist of unused handles |
| `/marketing/plan.py`, `live_engine.py`, `publisher.py`, `commercial_agent.py`, `copy_vault.py`, `social_watch.py`, `three_day_pulse.py` | Python source |
| `/marketing/run_daily.sh`, `/ops/board/build.py`, `/ops/health_check.py` | Shell + Python source |
| `/marketing/plan.json`, `commercial-brief.json`, `performance-memory.json`, `social-signals.json`, `approved-images.json`, `three-day-pulse.json`, `pinterest_feed.csv` | Commercial planning data |
| `/ops/board/`, `/ops/scout/`, `/ops/scout/scout.json`, `/ops/hq/`, `/ops/creators/`, `/ops/design-drop/`, `/ops/marketing/` | The unreleased design roadmap — slot names, garments and **exact hex colours** (`#FF6A13` on ink black, `#FFCB05` on `#00274C`) — plus the trend-scoring formula, `gaps` and `dead_campaigns` |

`noindex,nofollow,noarchive` and `robots.txt` `Disallow` are **not access control**.
They ask crawlers politely; they do nothing against a human, a scraper, or a
competitor who types the URL. Worse, `Disallow: /marketing/` and `Disallow: /ops/`
in a public `robots.txt` *advertise* exactly where to look.

`QA-REPORT.md` §2 asserts *"Zero developer/build leakage on public pages: no `.py`,
`.csv`, `python3`…"* That check greps the **HTML body of public pages**. It is true
and it is beside the point — the `.py` and `.csv` files are themselves reachable.

**Fix.** Publishing an internal dashboard on the same host as the storefront is the
root cause. Options, best first:

1. **Stop deploying them.** Add an allowlist to `sync_marketing()` / `sync_ops()` so
   only `dashboard.html` / `index.html` + their assets are copied, never `.py`, `.sh`,
   `.md`, `.json`, `.csv`. ~10 lines, and it fixes the whole class.
2. **Move the dashboards off the public host** — a private GitHub Pages repo, or an
   artifact of `refresh.yml`. They are `noindex` anyway, so nothing SEO is lost.
3. If they must stay, **gate them** — Cloudflare Access / Netlify password protection
   in front of `/ops/*` and `/marketing/*`. Not possible on plain GitHub Pages.

Also rotate anything sensitive already published. The follower counts and the
competitor research are now in Google's cache and the Wayback Machine whether or
not you delete them.

---

### C2 — The shipped site violates the repo's own "never print this" table

`DESIGN-BLUEPRINT.md` §2 is unambiguous. It applies to *"the artwork, the mockups,
the product title, the alt text and the ad copy"*:

> | Never | Why | Use instead |
> | A player's face, silhouette or photo | Likeness + trademark exposure | Type-only slogan |
> | A player's surname on the chest | Same, plus it dates the shirt | City, chant or era slogan |
> | A jersey number | Reads as a name-by-another-means | EST year, EST city, no numerals |
> | **Team logos, wordmarks, helmet marks** | **Directly claimed IP** | Original geometry + colour |
> | Press/action photography | Copyright + likeness | Hand-drawn line art |

§7 makes it a shipping gate: *"No face, no surname, no number, no team mark."*
`ops/board/` restates it: *"Slogan law. Identity slogans, not player faces… no face,
no surname, no number."*

**The shipped site violates every row of that table, in three layers.** I inspected
the actual image files, not just the markup.

**(a) `/collections/` uses four official team marks as UI icons.** `img/browns-logo1.webp`,
`img/green-bay-logo1.webp`, `img/dallas-logo1.webp`, `img/michigan-logo1.webp` (58–86 KB
each) are reproductions of the registered marks: the Browns Dawg Pound bulldog over the
"CLEVELAND BROWNS EST 1946" wordmark, the Packers G-oval in a "GREEN BAY PACKERS
ESTABLISHED 1919" roundel, the Cowboys star roundel, and the Michigan block "M" with
"MICHIGAN / Wolverines / 1817" — the Michigan file still carries a visible **®** symbol.
They sit on an indexable, sitemap-listed page linked from the main nav, and all four are
served with `alt=""`, i.e. marked decorative. This is the §2 row *"Directly claimed IP"*
verbatim. The NCAA's block M and the NFL's helmet/oval/star marks are among the most
enforced marks in sport; there is no descriptive-use or fair-use defence for
reproducing them as your own site's collection icons.

**(b) Every hero banner depicts the same marks on merchandise.** `hero-home.jpg` — the
**homepage LCP, seen by every visitor and crawler** — shows four garments printed with
the Browns helmet mark + "DAWG POUND", the Packers G-oval, and the Cowboys star.
`hero-cleveland.jpg` shows five more, including the helmet mark three times and the
bulldog. These are the LCP element on `/` and all four collection pages: the
most-viewed images on the site are the most infringing ones.

**(c) 14 live products name a real person.** 12 of them put the name in the `<title>`,
meta description, meta keywords, H1, alt text and `Product` schema:

| URL | Product | Breach |
|---|---|---|
| `/shop/limited-edition-grb41/` | Jordan Love 10 Packers Shirt | surname + number + **action photo** |
| `/shop/limited-edition-grb36/` | Jordan Love 10 Flag Number Shirt | surname + number |
| `/shop/limited-edition-grb31/` | Jordan Love 10 Green Bay Hoodie | surname + number |
| `/shop/limited-edition-grb30/` | Jordan Freaking Love Shirt | surname |
| `/shop/limited-edition-grb34-1/` | Jordan Freaking Love Packers Beanie | surname |
| `/shop/limited-edition-grb33/` | All You Need Is Love 10 Helmet Shirt | surname + number |
| `/shop/limited-edition-grb24/` | Love 10 Jersey Back Shirt | surname + number |
| `/shop/limited-edition-grb12/` | What Would Jordan Do Retro Shirt | first name |
| `/shop/limited-edition-grb11/` | Jordan Love Is All You Need Shirt | full name |
| `/shop/limited-edition-grb4/` | Let The 10VE Begin Green Bay Shirt | name-pun + number |
| `/shop/bryce-19/` | Bryce 19 | first name + jersey number |
| `/shop/second-act-qb19-vintage-football/` | Second Act QB19 Vintage Football | first name + QB number |
| `/shop/denzel-rock-out/` | Denzel Rock Out | first name |
| `/shop/make-them-know-your-name/` | Make Them Know Your Name | keywords name Denzel Ward |

18 pages carry alt text advertising a **photograph of the player**, e.g.
`alt="Fan-made Packers t-shirt with JORDAN LOVE 10 with Jordan Love action photo graphic"`.

`/trademark-notice/` claims *"Team, city and player names are used descriptively."*
That defence covers writing "Packers fan shirt". It does **not** cover (a) reproducing
the registered marks as your own UI, (b) hero photography of garments printed with
them, or (c) selling a hoodie bearing a player's name, jersey number and photograph —
the last is commercial appropriation (right of publicity, a *state-law* claim that is
**not** defended by the First Amendment the way nominative use is), and the photograph
itself is almost certainly a licensed press image belonging to a third party.

This is the largest single legal exposure on the site, and the site's own blueprint
already says so, twice. The cause is process, not intent: layers (b) and (c) came in
from the Viralstyle/Mayzing partner catalogues and layer (a) from downloaded badge
graphics, and the §7 gate was only ever applied to in-house designs. The mockups also
appear to be third-party stock compositions (the Dallas file has a baked-in
transparency checkerboard at its edges), so there is a *copyright* question in the
source imagery independent of the trademark one.

**Fix.** Decide, and write the decision down:
- **Layer (a) — remove now.** Replace the four `*-logo1.webp` icons with original
  geometry per §2 ("Original geometry + colour": a helmet silhouette drawn from
  scratch, or a type-only lockup). Four small files, one template change, no URL
  churn. There is no argument for keeping them.
- **Layer (b) — reshoot/recomposite the heroes** so the garments carry only in-house
  slogan art, or crop the marks out. This touches the LCP element on five pages, so do
  it alongside H4's image pipeline.
- **Layer (c) — delist or accept.** Adding the 14 slugs to `data/delisted.json` is the
  safe path; the 85-stub redirect machinery already handles it. It costs 14 of 84
  designs and 12 of the 37 Green Bay designs, which is a real hole. The alternative is
  amending the blueprint to permit imported partner designs under a documented risk
  acceptance — and then removing the "descriptive use" sentence from
  `/trademark-notice/`, because for those pages it is not accurate.

Either way, do not leave a written policy the shipped site contradicts — in a dispute
that document is discoverable and it establishes you knew.

---

### C3 — The privacy policy misdescribes the tracking the site actually does

`/privacy/` (`src/build.py:3110`, `:3116`) states:

> **Analytics** — We may use **privacy-respecting analytics** to count page views…
> This uses **aggregate data only**.
> **Cookies** — **No advertising cookies are set by this site.** Any cookies set
> after you click through belong to the checkout platform.

Reality (`src/build.py:984`, `:989`): every page loads
**Google Analytics 4 `G-5RHGJSLZNG`** from `googletagmanager.com`, and `app.js`
fires **event-level** hits — `colorway_interaction`, `custom_design_submit`,
`newsletter_signup`, plus per-button CTA reporting.

All three claims are wrong:
- GA4 is not what "privacy-respecting analytics" means in normal usage (that phrase
  denotes Plausible/Fathom/self-hosted Matomo). The site loads Google's tracker.
- GA4 sets **first-party cookies (`_ga`, `_ga_*`) on `gridironlocker.store`** — so
  cookies *are* set by this site, contradicting the policy outright.
- The data is per-event and per-visitor, not aggregate.

There is **no consent banner or CMP anywhere on the site**, while the store advertises
"Worldwide shipping" and actively targets EEA/UK buyers. GA4 without a consent gate is
a GDPR/ePrivacy exposure, and an inaccurate privacy policy is a separate one (it is
also what FTC enforcement and the UK CMA look at first).

**Fix.** Pick one:
- Switch to a genuinely privacy-respecting analytics product and the policy becomes
  true as written; **or**
- Keep GA4 and (a) rewrite `/privacy/` to name Google Analytics, its cookies, its
  retention and a link to Google's policy, and (b) add a consent gate for EEA/UK
  traffic that blocks `gtag` until consent.

Do not leave the current state: the policy actively denies a tracker that runs
sitewide.

---

### C4 — The lead-capture form can silently lose inquiries

This is the site's primary conversion path — *"Have an idea? We design it."* is one
of two hero CTAs — and `/contact/` sends everyone to it. It has four independent
failure modes.

**a) No `action` attribute in the HTML.** `src/build.py:1834` emits
`<form id="customForm" method="POST" … novalidate>`. The action is injected at
runtime by `app.js:149`: `form.action='https://formsubmit.co/'+atob(CUSTOM_EMAIL)`.
With JS disabled, blocked, or slow, the form POSTs to **the current URL** — a
static host answers 404/405 and the message is gone. `novalidate` also removes
native validation, so the form is entirely JS-dependent.

**b) `no-cors` makes success undetectable.** `app.js:167` and `:327`:
```js
fetch(form.action,{method:'POST',body:data,mode:'no-cors'}).then(function(){ … })
```
A `no-cors` response is **opaque** — `.then()` fires on *any* completed request and
the status is unreadable. So the user always sees *"Thank you! Your idea is on its
way. We will reply within 1-2 days"* even when FormSubmit returns 404 (endpoint not
activated), 4xx or 5xx. The `.catch()` fallback only triggers on a network failure.
**Confirmed false-success path.**

**c) The timeout guard is a dead no-op.** `app.js` (built from `src/build.py:4210`):
```js
setTimeout(function(){if(!ok){}},1500);
```
Empty body. This was plainly meant to be "if it hasn't succeeded in 1.5 s, fall back
to `mailto:`". It does nothing, so the intended safety net never fires.

**d) No contact details anywhere.** `/contact/` (363 words) offers no email address,
no phone and no postal address — it only points back at this form. `/privacy/` tells
users to *"Ask via the contact form"* to exercise their data rights, which routes a
GDPR request through the form that can silently fail. The only real address is
base64-hidden in JS and decodes to a **personal Gmail** (`itsnoury65@gmail.com`);
the comment calls this "anti-harvesting", but base64 is encoding, not protection —
it is trivially reversible and I reversed it in seconds.

Also: `_captcha` is `false` on a publicly exposed FormSubmit endpoint, and the
newsletter form (`src/build.py:1906`) shares defects (a) and (b).

**Fix.**
1. Put a real `action="https://formsubmit.co/<address>"` in the HTML and drop
   `novalidate`, so the form works with zero JS. Keep the JS as an enhancement.
2. Remove `mode:'no-cors'` and handle the actual response status. FormSubmit's AJAX
   endpoint returns JSON you *can* read; if you keep `no-cors`, at minimum replace
   the optimistic success message with a neutral "we've sent that — if you don't
   hear back, email us".
3. Fill in `setTimeout(function(){if(!ok){fallback()}},1500);`.
4. Publish a real contact address on `/contact/` and `/privacy/`. A branded address
   (`hello@gridironlocker.store`) also removes the trust cost of a Gmail on a
   storefront. Consider enabling `_captcha`.

---

## 2. HIGH

### H1 — The homepage Michigan card reports two different games

`src/collections_data.py:250`, Michigan:
```
'opener':   'Final &middot; Sept 5 vs Western Michigan'
'headline': 'Michigan beat No. 11 Oklahoma 17-10 on Sept 12.'
```
Rendered on the homepage (`site/index.html:212-213`) as one card:

> **Michigan** — Final · Sept 5 vs Western Michigan
> Michigan beat No. 11 Oklahoma 17-10 on Sept 12.

The label names the Western Michigan game; the sentence describes the Oklahoma game.
The three NFL cards are internally consistent — only Michigan's `opener` was never
advanced past week 1. Live on the homepage right now.

**Root cause is bigger than the one field.** `src/build.py` hard-codes season prose
in at least four places outside `SEASON` — `:3320` (*"Week 1 of the 2026 season is
complete: Michigan beat Western Michigan on Sept 5 with a last-second Hail Mary"*),
`:3368`, `:3466`, `:3484`. Those strings cannot be updated by editing the data file,
so they will keep drifting every week.

**Fix.** Advance Michigan's `opener` to the Oklahoma game (or make the card derive
its label from `kickoff` + `result` so the two cannot disagree), then move the four
hard-coded passages onto `SEASON`. Add a test asserting, per collection, that the
date in `opener` matches the date in `headline` and `kickoff` — that assertion would
have caught this.

### H2 — A 10%-off promo code sits on the highest-priority page and may not be redeemable

`/michigan/joe/` — sitemap **priority 0.9** (higher than every product page at 0.8),
linked from **all 109 pages** via the footer — says:

> **10% OFF YOUR ORDER · USE CODE: JOE10 · Enter the code at checkout.**

But checkout does not happen on this site. Every CTA hands off to Mayzing
(`gridironlocker.shop`) or Viralstyle. **The code must exist in the partner's cart**,
and `QA-REPORT.md` §5.3 already lists this as unverified: *"Confirm it is live in the
Mayzing cart before it ships."* It shipped.

If `JOE10` is not configured on Mayzing, the site's most prominent commercial page
makes a discount claim it cannot honour — a consumer-protection problem, and a
guaranteed support complaint from every creator-referred visitor. Hard-coded in four
places: `src/build.py:2393, 2436, 2480, 2550`.

**Fix.** Verify the code in the Mayzing cart today. If it is not live, pull the claim
until it is. Then scope the wording to the partner where it actually applies, since
the page mixes Mayzing and Viralstyle products and one code cannot cover both.

### H3 — `pinterest_feed.csv` is publicly served and wrong on all three dimensions

`https://gridironlocker.store/marketing/pinterest_feed.csv` — 60 rows, and the
publicly-served `REVENUE_PLAYBOOK.md` instructs *"Pinterest Business → Bulk Create →
upload CSV"*. If anyone follows that instruction:

- **60/60 rows link to raw supplier URLs** (`viralstyle.com/kebystore/…`). **0** link
  to gridironlocker.store. Every pin would send the buyer **straight to Viralstyle**,
  bypassing the storefront and handing away the customer relationship and all SEO equity.
- **44/60 rows point at designs with no live page** — 39 are retired `noindex`
  redirect stubs, 5 do not resolve to a product. The top three rows are the
  `sanders-*-special-edition` designs that `AGENTS.md` §5 already flags as
  "unpurchasable".
- **All 60 claim "S-3XL"**, but 37 of the 84 catalogue products are Mayzing Gildan
  5000 in **S-5XL** — which the site's own product pages state correctly.

This is the public-facing tail of the two-planner bug in `AGENTS.md` §5: both planners
read the stale 113-slug `data/products.json` and neither applies
`data/fulfillment.json`'s `hold` list.

**Fix.** Unpublish the CSV as part of C1 regardless. Then regenerate it from
`data/catalogue-live.json` (which is exactly what that contract file was built for),
assert every row's `link` is a `gridironlocker.store/shop/` URL with a published page,
and derive the size string from each product's `sizes_avail` instead of hard-coding it.

### H4 — Hero images are ~400 KB with no responsive variants, on the LCP element

| File | Weight | Declared size | `srcset` |
|---|---|---|---|
| `img/hero-home.jpg` | **441 KB** | 2048×768 | none |
| `img/hero-greenbay.jpg` | 397 KB | 2048×768 | none |
| `img/hero-michigan.jpg` | 388 KB | 2048×768 | none |
| `img/hero-cleveland.jpg` | 377 KB | 2048×768 | none |
| `img/hero-dallas.jpg` | 380 KB | 2048×768 | none |
| `img/custom-tee1.jpg` | 216 KB | — | none |

Across the whole site: **`srcset` 0 · `sizes` 0 · `<picture>` 0.** A 375 px phone
downloads the same 2048 px / 441 KB file as a 4K desktop. These are the LCP element
on the homepage and all four collection pages — so this is the single biggest lever
on mobile Core Web Vitals, which `QA-REPORT.md` §5.6 lists as never measured.

To their credit: `fetchpriority="high"` on the hero, `loading="lazy"` on 27/28
product-page images, and explicit `width`/`height` on **every** image (0 CLS risk
from missing dimensions — better than most sites).

Also render-blocking: **`style.css` is 84 KB unminified**, `app.js` 30 KB, homepage
HTML 60 KB, and two third-party Google Fonts origins (extra DNS + TLS + a
render-blocking stylesheet). `site/` totals 84 MB across 1,720 image files.

**Fix.** Emit WebP/AVIF plus 640/1024/2048 `srcset` with `sizes` for the six heroes
(expected: 441 KB → ~60–90 KB on mobile, a ~4× LCP improvement). Minify CSS/JS in
`build.py`. Self-host the two font files with `font-display:swap` and a `preconnect`,
or move to a system-font stack. `qa_http.py` already parses the stylesheet — extend
it to assert the hero has a `srcset`.

### H5 — `/drops/` silently publishes 16 of its 24 designs, and nothing reports the loss

`data/live_drops.json` holds 24 entries; `/drops/` renders 16 cards. `src/build.py`
filters to slugs with a published page and `src/drops_page.py:119` guards again — so
the storefront is safe, exactly as `AGENTS.md` §5 says. But the 8 discarded drops
vanish without a trace, and the public `REVENUE_PLAYBOOK.md` still advertises
*"24 live cards"*. `/drops/` carries the **highest priority in the sitemap (0.95)**
and is the page the marketing plan pushes hardest, so a third of its content going
missing is a commercial problem, not a cosmetic one.

**Fix.** `AGENTS.md` assigns the planner consolidation to ChatGPT, and it should stay
there. What the storefront half can do now is make the loss visible: log the filtered
slugs at build time and fail the `refresh.yml` sanity gate when the drop rate exceeds
a threshold, so a silently-empty `/drops/` can never deploy again.

---

## 3. MEDIUM

### M1 — "MILF" is a live, indexed product with auto-generated copy that doesn't understand it

`/shop/milf/` is in the sitemap, linked from `/search/`, priced $21.00 on Mayzing.
The generated copy treats it as a wholesome tailgate joke:

> *"MILF is a punchline Michigan fans will get without a briefing, printed at the
> size a tailgate needs."*
> *"A piece carrying MILF is meant to sit in that weekly habit…"*
> FAQ: *"What is printed on the MILF?"* · *"What colours does the MILF come in?"* ·
> *"Is the MILF official…"*

The FAQ substitutes the product name into a noun slot where it does not parse. Beyond
the awkwardness: this single page can disqualify the whole domain from Google
Shopping, the Meta catalogue, Pinterest (which the playbook depends on) and most
payment-processor review queues — all of which apply adult-content filters at the
**domain** level.

**Fix.** Delist it (`data/delisted.json` → automatic `noindex` stub), or relist it
under a title the filters will pass and hand-write the copy. Then add an adult-term
blocklist to the ingest path so the next one is caught before it ships.

### M2 — Duplicate and near-duplicate designs cannibalise each other

`qa_audit.py` checks slug uniqueness, which passes. It does not check that two slugs
are the same shirt:

| Designs | URLs |
|---|---|
| **`Cle Browns`** — *identical name on both* | `/shop/cle-browns/`, `/shop/cle-browns-light/` |
| No Fly Zone | `/shop/no-fly-zone/`, `/shop/limited-edition-no-fly-zone/` |
| Respond Nothing Given Everything Earned | `/shop/respond-nothing-given-everything-earned/`, `/shop/respond-nothing-given-everything-earned-tee/` |
| Michigan BET | `/shop/michigan-bet/`, `/shop/michigan-bet-vintage/` |
| Cheese Heart Green Bay | `/shop/limited-edition-grb32/` (shirt), `/shop/limited-edition-grb35/` (mug) |
| M vs Everybody | `/shop/m-vs-everybody/`, `/shop/michigan-v-everybody/` |
| Second Act | `/shop/second-act/`, `/shop/second-act-qb19-vintage-football/` |
| BET M | `/shop/bet-m/`, `/shop/michigan-bet/` |

The identical-name pair is worst: two indexable pages, two sitemap entries, the same
visible title, competing for one query. Several appear adjacent in the same homepage
carousel — the shopper sees the same shirt twice.

**Fix.** Where they are genuinely the same artwork, retire one to a stub and 301 it to
the survivor (the machinery exists). Where they are real variants (shirt vs mug),
differentiate the `<title>` and H1 so they are not duplicates. Add a
normalised-name collision check to `qa_audit.py` so new ones are caught at build time.

### M3 — Misspelled and truncated URLs are permanent

| URL | Product | Problem |
|---|---|---|
| `/shop/dwag/` | **DAWG** | transposed letters — and the alt text reads `DAWG - DWAG` on the homepage, collections, Cleveland and search pages |
| `/shop/be-awar-of-dawg/` | **Beware Of Dawg** | alt text renders as `BE AWAR OF DAWG` on 4 high-traffic pages |
| `/shop/limited-edition-h-a-i-l-mary/` | Limited Edition Hail Mary | slugify exploded the letters: `h-a-i-l` |
| `/shop/dallas-texas-vintage-athletic-sports-sty/` | Dallas Texas Est 1841 Grey | truncated mid-word at 40 chars |
| `/shop/dallas-texas-vintage-athletic-style-t-sh/` | Dallas 1960 Football Helmet White | truncated |
| `/shop/dallas-football-vintage-athletic-style-f/` | Dallas Football 1960 Helmet Vintage | truncated to a single letter |
| `/shop/cleveland-retro-vintage-classic-ohio-shi-1/` | — | truncated, plus a `-1` collision suffix |
| `/shop/it-s-not-a-team-logo-browns-it-s-a-famil/` | — | truncated |
| `/shop/respond-nothing-given-everything-earned-tee/` | — | 47 chars |
| `/shop/lets-go-cle-copy/` | Let's Go CLE | `-copy` suffix leaked from the CMS |

`AGENTS.md` §3.3 freezes product URLs, correctly — so these need **new clean slugs
plus 301s from the old**, not edits. Two caveats before touching `dwag` and
`be-awar-of-dawg`: the misspelling originates in the partner's campaign data, so the
typo may be **printed on the garment**. Check the artwork first — if the shirt really
says "DWAG", the title is accurate and only the URL and surrounding copy need work.
If it says "DAWG", the alt text on four high-traffic pages is a visible typo.

Either way, `-copy` and the single-letter truncations should not survive.

### M4 — Boilerplate copy at scale, with internal jargon leaking to customers

Verbatim repetition across indexable product pages:

| Phrase | Pages |
|---|---|
| "that is the brief, not a moodboard" | **54** |
| "the printed line stays" | **54** |
| "with a drink in the other hand" | 20 |
| "stays on that side of the argument" | 13 |
| "names a feeling" | 6 |
| "do more work than a paragraph ever will" | 6 |
| "colourway" | 166 |

"brief" and "moodboard" are design-agency jargon — a shopper buying a $21 tee does
not read "that is the brief, not a moodboard" as reassurance. And 54 near-identical
paragraphs across 84 indexable pages is exactly the thin-content pattern Google's
helpful-content system targets; it is also why the MILF page reads so oddly.

**Fix.** Widen the copy vault (it already generates 20 openers per team for social —
apply the same idea to product prose), and add a build-time check that no sentence
appears on more than N product pages. Strip internal jargon from the customer-facing
templates.

### M5 — Malformed RSS feed

`site/feed.xml`:
- `<lastBuildDate>2026-09-18</lastBuildDate>` — **not RFC 822**. RSS 2.0 requires
  `Thu, 18 Sep 2026 00:00:00 GMT`. Many parsers reject or mis-order this.
- **Zero `<pubDate>` elements** on any of the 5 items, so readers cannot order or
  date them.
- Each `<guid>` is `…#2026-09-18` — the guid changes **daily**, so every consumer
  sees all 5 items as brand new forever. That is a feed-spam pattern aggregators drop.
- Only 5 items, all collection pages. A feed titled *"new and trending fan designs"*
  never lists a design.
- Item descriptions advertise *"Trending: shedeur sanders shirt, sanders browns qb
  shirt"* — search terms for designs that are retired stubs (see H3).

Source: `src/build.py:3983`. **Fix.** RFC-822 dates, stable per-item guids, `pubDate`
on every item, and feed actual designs from `catalogue-live.json`.

### M6 — Orphan verification file deployed inside a content directory

`site/2026-season/googleae06215486ed6c17.html` — a stale copy of the Google
site-verification file, committed and live at
`/2026-season/googleae06215486ed6c17.html`. It has no `<title>`, no meta description
and no H1, and is not in the sitemap. `src/build.py:3887` writes only the root copy,
and `build.py`'s orphan cleanup prunes only `site/img/` — so anything written into a
content directory by an older build persists forever.

There are three verification artefacts at the root (`google7e05d1ab…html`,
`googleae0621…html`, `a7f3c19b…txt`) plus `BingSiteAuth.xml`; the duplicate Google
files suggest an abandoned Search Console property.

**Fix.** Delete the orphan and generalise the cleanup pass to prune any file under
`site/` that the current build did not write. Note this must not delete the Mayzing
hot-links' local copies — see M8.

### M7 — `/ops/board/` states a rule the public site breaks

The board says: *"These names are internal tracking. **They never appear on art, on a
public page, or in a caption.**"* But `/2026-season/` and `/fan-trend-index/` publish
those exact names with 0–100 scores and mention counts — Deshaun Watson 100, Bryce
Underwood 38, Shedeur Sanders 24, Dak Prescott 18, and so on.

Also, `data/people.json`'s own rule is *"Only promote CURRENT players and coaches.
Anyone flagged throwback… must not be used or mentioned"* — yet the public Cleveland
trend index lists **Joe Flacco (0 mentions · quiet)**, a player the same page
describes as departed and whose designs were retired.

Neither is a catastrophe, but both mean the internal policy documents no longer
describe the site. Same class of problem as C2: written rules the output contradicts.

**Fix.** Decide whether the trend index is public-facing (it is — it is indexed and
in the sitemap), then correct the board's claim. Drop retired entities from the
public index, or add a `status` filter so `people.json`'s rule is enforced in code.

### M8 — 44 product mockups are hot-linked to Mayzing with signed URLs

`QA-REPORT.md` §5.1 raised this and it is still open. 44 unique images point at
`buyer-experience-gateway.mayzing.com` with `sig:` signature parameters. If those
signatures expire, or Mayzing rate-limits or blocks cross-origin hot-linking, **44
product mockups break at once** — including images on the homepage carousel. I could
not test them: this sandbox has no route to that host, and `qa_http.py` correctly
reports them as "unreachable from sandbox" rather than broken, which means the gate
passes whether or not they work.

There is a second cost: every product view makes cross-origin requests to a third
party, adding latency and disclosing visitor IPs to Mayzing — which `/privacy/` does
not mention (see C3).

**Fix.** Run `dl.py` to self-host them, as the QA report already recommends. Note
`dl.py` has no `if __name__ == "__main__"` guard and executes on import
(`AGENTS.md` §6) — add the guard first.

### M9 — `no-cors` + opaque analytics: no way to know if anything is working

Beyond C4's form, the same `no-cors` pattern means there is no error telemetry at
all. Combined with GA4 events firing into a property nobody has confirmed is
receiving data, the site currently has **no verified signal for whether the custom
design form or the newsletter form has ever worked**. Given `_captcha=false` and a
FormSubmit endpoint that requires one-time email activation, "it has never
delivered a single message" is a live possibility.

**Fix.** Submit a test inquiry through the production form and confirm it arrives.
Check the GA4 realtime report. Then add a synthetic post-deploy check to
`refresh.yml` (it already runs `ops/health_check.py` against production).

---

## 4. LOW

| # | Finding | Detail |
|---|---|---|
| L1 | Heading-order skips | `/2026-season/` and `/fan-trend-index/` jump h1 → h3. WCAG 2.1 SC 1.3.1 / best practice. |
| L2 | 4 images with empty `alt` | Present but blank; confirm they are genuinely decorative and add `role="presentation"`, or write alt text. |
| L3 | 2 meta descriptions over 165 chars | `/guides/2026-week-1-shirts/` (169) and `/shop/it-s-not-a-team-logo-browns-it-s-a-famil/` (166) — will clip in the SERP. |
| L4 | Truncated slug in a meta description | *"It S Not A Team Logo Browns It S A Family Crest EST 1946 Shirt"* — apostrophes stripped by the slugify, then reused as prose. Reads as broken English. |
| L5 | Redundant gallery images | All **84** product pages render at least one image twice; the Green Bay pages carry 28 `<img>` tags for 20 unique images. The `thumbs` strip duplicates the main gallery (`front`, `c0`–`c5`). All lazy-loaded, so byte cost is bounded — but the shopper sees the same picture twice in the gallery, and on single-image Mayzing products "view 1" *is* the hero. |
| L6 | 85 redirect stubs share one `<title>` and one H1 | 35× "Cleveland design moved", 2× "Michigan design moved", 85× H1 "This design moved". They are `noindex,follow` so there is no SERP impact — acceptable by design, noted for completeness. |
| L7 | Three verification files + `BingSiteAuth.xml` at root | Likely an abandoned Search Console property. Also `site/google7e05d1ab221dce85.html` is duplicated at the repo root. |
| L8 | `Crawl-delay: 1` in `robots.txt` | Google ignores it entirely; it only throttles Bing/Yandex. Harmless, but it is not doing what it looks like it is doing. |
| L9 | 30 images neither lazy nor priority-hinted | Outside the hero/product-image paths — mostly icons and section art. Add `loading="lazy"` or `decoding="async"`. |
| L10 | Personal Gmail as the business contact | See C4(d). Trust cost on a storefront, independent of the fragility issue. |

---

## 5. What is genuinely good

Worth saying, because it is unusual and it makes the above fixable rather than fatal:

- **The single-source-of-truth catalogue works.** 84 designs, 4 collections, and every
  count on the homepage, nav, collection pages, SEO copy, footer, sitemap and `llms.txt`
  is derived, not hand-maintained. `QA-REPORT.md`'s rebase story (Michigan 15→18 with
  zero code edits) is credible and I verified the property holds.
- **Prices are perfectly consistent.** I cross-checked every `$` figure rendered next
  to every product link on every page against the catalogue: **0 disagreements**, and
  no product name appears at two prices.
- **Zero CLS risk from images.** Every `<img>` on the site carries explicit `width`
  and `height` — 0 missing. Better than most production storefronts.
- **Zero fabricated trust signals.** No `aggregateRating`, `reviewCount`, star markup,
  compare-at pricing or "only N left" anywhere — verified, and pinned by
  `test_no_fabricated_trust_signals`.
- **Link and image integrity is real.** 108/108 sitemap URLs 200, 0 dead internal
  links across 108 targets, 382 local images all resolve, 84/84 CTAs match the
  catalogue `buy` URL exactly, 85/85 redirect stubs valid with correct `noindex`,
  `data-gl-redirect` and live targets.
- **Accessibility fundamentals.** 0 images missing `alt`, skip links on all 109 real
  pages, `aria-live="polite"` on form status, and the custom-design form uses
  **implicit `<label>` wrapping** — which is valid HTML and satisfies WCAG 3.3.2.
  (My first pass flagged these as unlabelled because I only matched `for=`; that was
  my error, not the site's.)
- **No oversized fixed widths** anywhere in the CSS (0 rules >360 px) and 18 real
  responsive breakpoints.
- **Structured data is complete and correct.** Product/Offer/Organization/WebSite/
  BreadcrumbList/FAQPage/CollectionPage/Article/ItemList across 107–109 pages, all
  JSON-LD parses, 0 schema price mismatches, and the mug correctly omits `size`.
- **The trademark framing is consistently present** on every page — every page carries
  the not-affiliated disclaimer, and `/trademark-notice/` and `/faq/` are well-written
  (487 and 565 words). The *wording* is right; the problem (C2) is that the imagery and
  the catalogue don't match it.
- **The gates are honest.** 220 tests, and `ops/health_check.py` + the `refresh.yml`
  publish gate derive their expected counts from the build instead of asserting magic
  numbers. That is why they pass for the right reasons.

---

## 6. Suggested order of work

**Today** (each is small, and each closes a live exposure):
1. **C1** — allowlist `sync_marketing()` / `sync_ops()` so `.py`, `.sh`, `.md`,
   `.json`, `.csv` are never deployed. ~10 lines. Also removes H3 automatically.
2. **C4c** — fill in the dead `setTimeout` body. One line.
3. **H1** — advance Michigan's `opener` to the Oklahoma game. One field.
4. **H2** — verify `JOE10` in the Mayzing cart; pull the claim if it is not live.
5. **M1** — delist `/shop/milf/`.
6. **C2(a)** — swap the four `*-logo1.webp` icons on `/collections/` for original
   geometry. Four files, one template. The single highest-value line-item here.

**This week:**
7. **C3** — fix `/privacy/` or replace GA4; add a consent gate if GA4 stays.
8. **C4a/b/d** — real `action`, drop `no-cors`, publish a contact address.
9. **C2(b,c)** — recomposite the five heroes without the marks, and decide
   delist-vs-amend on the 14 player-name/photo products. Write whichever decision you
   make into `DESIGN-BLUEPRINT.md`, so the policy and the site agree again.
9. **H4** — responsive `srcset` + WebP/AVIF for the six heroes; minify CSS/JS.
10. **M6, M5** — delete the orphan, fix the feed dates/guids.

**Then:**
10. **H5, H3** — make the `/drops/` loss visible; regenerate the Pinterest feed from
    `catalogue-live.json`. (The planner consolidation itself stays with ChatGPT per
    `AGENTS.md` §5.)
11. **M2, M3, M4** — deduplicate, re-slug with 301s, widen the copy vault.
12. **M8** — run `dl.py` to self-host the 44 Mayzing mockups (add its `__main__`
    guard first).

**New gates worth adding** so these classes cannot return — all fit the existing
`qa_audit.py` / `qa_http.py` pattern:
- No `.py`/`.sh`/`.md`/`.csv`/`.json` under `site/marketing/` or `site/ops/`.
- Per collection: the date in `opener` == the date in `headline` == `kickoff`.
- Every product name in `DESIGN-BLUEPRINT` §2's forbidden set (surname, number,
  photo) — i.e. make the §7 checklist executable.
- No `*-logo*` team-mark asset referenced from any public page (the §2 "directly
  claimed IP" row, as a filename allowlist check).
- Normalised-name collisions across live products.
- Hero images must carry `srcset`.
- Adult-term blocklist on ingested campaign names.
- No sentence appearing on more than N product pages.

---

## 7. What I could not verify from this environment

Stated so nobody assumes it was checked:

1. **All HTTP response headers** — no outbound network in this sandbox, and the
   available fetch path returns rendered content only. Unmeasured: TTFB, cache-control,
   compression (Brotli/Gzip), `Content-Security-Policy`, `X-Content-Type-Options`,
   `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy`. GitHub Pages
   sets some of these itself; a custom `CNAME` behind Cloudflare would need checking.
2. **Core Web Vitals** — no Lighthouse or CrUX run. H4 is reasoned from asset weights
   and the absence of `srcset`, not from a measured LCP.
3. **HTTP→HTTPS, `www`→apex canonicalisation, and trailing-slash redirects** — needs
   header inspection. A bare `CNAME` file means GitHub Pages handles this; worth one
   manual check that all four variants 301 to one canonical host.
4. **Whether the 44 Mayzing hot-linked images actually load** (M8) — no route to
   `buyer-experience-gateway.mayzing.com`. `qa_http.py` reports "unreachable from
   sandbox", which is honest but means the gate cannot catch a break.
5. **Whether the 84 buy URLs resolve** — `qa_http.py` proves each CTA `href` matches
   the catalogue exactly (a stronger check than reading source), but not that
   Viralstyle/Mayzing still serve those campaigns. A dead supplier campaign would
   show as a live button leading nowhere.
6. **Whether `JOE10` works** (H2) and **whether the FormSubmit endpoint is activated**
   (C4, M9) — both need a real browser and a real cart.
7. **Mobile click-through and visual QA** — no browser here.
8. **Search Console / indexation state** — how many of the 108 URLs are actually
   indexed, and whether the 85 stubs and the `/ops/`, `/marketing/` paths have been
   crawled or cached despite `noindex`.

---

## 8. Reproducing this audit

```bash
python3 -m unittest discover -s tests -p "test_*.py"    # 220 passed, 17 skipped
python3 qa_audit.py                                     # TOTAL: 0
cd site && python3 -m http.server 8123 --bind 0.0.0.0 &
python3 qa_http.py http://127.0.0.1:8123                # HTTP QA: PASS
python3 qa_deep.py                                      # the gap checks — see below
```

`qa_deep.py` (added alongside this report) encodes the checks that found the findings
above and that `qa_audit.py` structurally cannot: deployed-internal-file exposure,
team-mark / forbidden-design assets and terms per `DESIGN-BLUEPRINT` §2,
analytics-vs-privacy-policy contradiction, form `action`/`no-cors`/dead-timeout,
season `opener`-vs-`headline` date mismatch, unverified promo codes, duplicate and
near-duplicate designs, slug hygiene, boilerplate repetition, hero `srcset`/weight,
feed RFC-822 validity, and orphan files under `site/`. It exits 1 while any CRITICAL
remains, so it can join the `refresh.yml` gate.

`qa_deep.py` groups evidence under one tag per issue, so its counts (5 critical tags,
5 high, 7 medium, 3 low) map onto — but do not equal — the 28 findings listed above;
read the report for findings, the harness for regression detection.

Two honest limits on `qa_deep.py`: the team-mark and hero checks match by filename
convention and are annotated with what visual inspection confirmed (a linter cannot
*see* a logo — a periodic human pass over `site/img/` is still required), and the
near-duplicate / boilerplate checks are heuristics whose thresholds are meant to be
tuned, not trusted blindly.

---

## 9. Fixes applied (2026-09-18, same day)

Everything below was fixed in `src/` (and `data/`) and the whole site rebuilt —
`site/` is generated output and was never hand-edited. Each fix is pinned by a
test in `tests/test_layout.py` (class `AuditFixes20260918`) and/or a check in
`qa_deep.py`, so it cannot silently regress on the next rebuild.

### 9.1 Fixed

| Finding | What changed |
|---|---|
| **C1** internal files publicly served | `sync_marketing()` / `sync_ops()` no longer `copytree` the source trees. A new `PUBLISH_EXT` allowlist (`.html .css .js .json .svg .png .jpg .jpeg .webp .ico`) plus `_copy_publishable()` publish 20 of 35 `marketing/` files and 8 `ops/` files; `.py .sh .md .csv .txt` stay in the repo. `site/` now contains **zero** `.py/.sh/.md/.csv/.txt` files — `pinterest_feed.csv`, `REVENUE_PLAYBOOK.md`, `social-accounts.md` and the sync scripts are no longer served (**this also closes H3's exposure half**). The build prints what it published vs withheld. |
| **C2 / L2** official team marks | `site/img/{browns,dallas,green-bay,michigan}-logo1.webp` (rasterised official marks) are **removed from the repo**. `lockup_svg()` in `build.py` now generates original fan-made badges — octagon, city name, abbreviation, `EST` year from `collections_data`, collection palette, "FAN MADE · EST" line — written to `/img/lockups/*.svg` on every build, with descriptive alt text. |
| **C3** privacy policy misdescribed tracking | `/privacy/` rewritten to match what the code does: names **Google Analytics 4** with the measurement ID, states the **opt-in** model, lists the `gl_analytics` cookie, adds a *Fonts and product images* section disclosing **Google Fonts** and the **Mayzing image CDN** (both load pre-consent and see the visitor's IP), says social links are plain outbound links, and states the cookie position precisely instead of the over-broad "no advertising cookies are set by this site". Rights requests now go to a real `mailto:`. |
| **C4** lead capture could silently lose inquiries | Analytics is consent-gated (`window.glLoadAnalytics()` injects `gtag.js` only after the banner records `gl_analytics=1`; nothing loads on decline). The custom-design form posts to a real FormSubmit action, `novalidate` is gone, and `app.js` uses FormSubmit's **AJAX** endpoint so a rejected submission reports failure instead of a fake success. The dead `setTimeout(function(){if(!x){}},…)` guard and the opaque `no-cors` post are removed (**also closes M9**). The contact address is published in plain text on `/contact/` and `/privacy/`. |
| **H1** homepage Michigan card reported two games | All season prose is now **derived** from `collections_data.SEASON`: `season_slate_sentence()`, `season_recap_long()`, `season_recap_short()`, `week1_dates_line()`. The four hand-written sites (homepage cards, `/2026-season/`, `/guides/`, `/guides/2026-week-1-shirts/`) plus the feed's key-pages line were replaced. One card can no longer carry two dates: a test asserts every card string equals a `SEASON["opener"]` and that its `Sept N` matches that team's `kickoff`. |
| **H5** `/drops/` silently discarded 8 of 24 designs | The build now prints `WARNING /drops/: 8 of 24 queued drops have no published page…` and writes `data/drops-dropped.json` (`generated / queued / eligible / shown / dropped`), which `qa_deep.py` checks for arithmetic consistency. |
| **M4** boilerplate copy + agency jargon | `LAYER_NOTE` for t-shirts is now 5 leads × 5 tails composed into **25 distinct single sentences** (was one sentence on 81 pages); `COL_VOICE["sunday"]` and `["mark"]` are variant lists picked per slug; the short-description tail is drawn from a 14-line pool; and the story/why/who/gift/gameday lines now carry a per-design token (`name`, `phrase`, `art_title`) instead of a fixed clause. "That is the brief, not a moodboard" and "The brief for …" are gone from customer copy. **Result: no marketing sentence repeats on more than 10 of the 84 product pages**, verified by a new region-scoped generic check (§9.3). |
| **M5** malformed RSS | `feed.xml` items carry RFC-822 `<pubDate>` and `<lastBuildDate>` (`_rfc822()`), stable non-dated `<guid>`s, and only live designs. A test parses every date with `email.utils.parsedate_to_datetime` and asserts each advertised `/products/<slug>/` exists. |
| **M6 / L7** orphan verification file | `assets()` walks `site/` and deletes any verification file (`googleae*.html`, `google7e05*.html`, `a7f3c19b*.txt`, `BingSiteAuth.xml`) found outside the site root; `site/2026-season/googleae06215486ed6c17.html` is removed. A test asserts those filenames only ever exist at the root. |
| **M7** `/ops/board/` rule the public site broke | `_retired_people()` reads `data/people.json` and `fti_rows()` filters out everyone whose `status` is not `current`, so the public Fan Trend Index no longer scores retired names. |
| **L1** heading-order skips | `fti_block()` takes a `level` argument (season hub now emits `<h2>`), and `/fan-trend-index/` gained `<h2>This window's leaderboard</h2>`. A test walks all 196 public pages and fails on any `h{n} → h{n+2}` jump. |
| **L3** over-long meta descriptions | `/guides/2026-week-1-shirts/` shortened (169 → 149) and the stub page now sits at 115. |
| **L4** truncated slug echoed as prose | `_stub_display_name()` suppresses crawl-mangled retired names ("It S Not A Team Logo Browns It S A Family Crest EST 1946 Shirt") in the stub `<title>`, meta/OG/Twitter description and visible sentence, falling back to "This design" / "<collection> design moved". Clean names are still echoed. |
| **L5** duplicated gallery images | `page_product()` de-duplicates `gallery` via `dict.fromkeys`, and the thumbnail strip is only rendered when there is more than one unique view — so single-image products no longer show "view 1" that *is* the hero. |
| **L8** `Crawl-delay: 1` | Removed from the generated `robots.txt` (it bound only to the preceding `ClaudeBot` group while looking sitewide, and Google ignores it). `README.md` and `SITE-BLUEPRINT.md` updated to match. |
| **L9** 30 images neither lazy nor hinted | New `hint(eager)` helper: eager cards get `fetchpriority="high" decoding="async"` instead of nothing, and the two card renderers that bypassed it (`card()`, the `/michigan/joe/` creator card) now use it. `qa_audit.py` reports **0** un-hinted `<img>`. |
| **F8** alt text printing crawl typos | `landing.typo_variant()` (equal / anagram / Levenshtein ≤ 2 after stripping non-alphanumerics) suppresses the artwork line when it is a mangled copy of the curated name; `card_alt()` is now used by **all three** card renderers, so `Beware Of Dawg - BE AWAR OF DAWG` is gone from `/cleveland-browns-shirts/`, `/collections/`, `/search/`, the creator page and the homepage. |
| **M2** *(correction)* | Duplicate **titles** were already mitigated before this audit by `_DUP_NAMES`, which qualifies SERP title/meta with the colourway (`Cle Browns - Sand` vs `- Natural`) while H1s stay verbatim. `qa_deep.py` now *verifies that mitigation* (unique colourway + unique `<title>` per pair) instead of re-reporting the shared design name. Only near-duplicate **designs** remain, which is a curation decision (§9.2). |

### 9.2 Deferred — needs an owner decision, or assets this environment cannot produce

These are deliberately **not** silently executed: each either costs revenue, needs
partner access, or needs tooling the sandbox does not have (no network egress, no
Pillow, no way to recomposite photography).

| Finding | Why it is still open | What closes it |
|---|---|---|
| **C2** 14 live player products (`Jordan Love 10 …`, `Bryce 19`, `Denzel Rock Out`, …) breach `DESIGN-BLUEPRINT` §2 | Delisting them removes ~17% of the catalogue and its revenue; that is the owner's call, not a linter's. | Owner decision: delist, or amend §2 and re-run `qa_deep.py`. `qa_deep.py` still fails (exit 1) until then — intentionally. |
| **C2** 5 hero banners show garments printed with official marks | Recompositing needs new artwork/photography. | New hero art without club marks, then re-run the gate. |
| **H2** `JOE10` advertised as redeemable "at checkout" | Checkout happens on Mayzing/Viralstyle; the code cannot be verified from here. | Confirm the code exists in the partner cart, or drop the claim from `/michigan/joe/`. |
| **H4** heroes ~370–430 KB, no `srcset`/`<picture>`, 84 KB unminified CSS, third-party fonts | Needs image tooling (Pillow/cwebp) and font files — unavailable offline. | Optimise + responsive variants + self-hosted fonts with `font-display:swap`. |
| **M8** 44 mockups hot-linked to Mayzing with signed URLs | `dl.py` needs network egress to download and re-host. | Run `dl.py` (add its `__main__` guard), commit the files, repoint the URLs. |
| **M1** `/shop/milf/` is live and indexed, with copy that does not understand the name | Brand-safety vs revenue is an owner decision. | Delist/noindex, or keep and accept domain-level adult filtering. |
| **M2** 5 near-duplicate design pairs | Curation: which of each pair is the canonical design. | Merge or differentiate the pairs. |
| **M3** misspelled / truncated slugs (`be-awar-of-dawg`, `dwag`, `…-sty`, `…-t-sh`, `h-a-i-l-mary`) | The spelling comes from the partner campaign and may be **printed on the garment**; renaming URLs also needs 301 stubs. | Check the artwork, then rename with `site/_redirects` stubs (the machinery exists). |
| **M9(forms)** `_captcha=false`; personal Gmail as the business address | Spam filtering vs conversion, and whether to buy a domain mailbox, are owner calls. | Enable captcha / move to a domain address; the base64 in `app.js` is a fallback, not obfuscation, and the address is now published plainly on purpose. |
| **L6** 85 stubs share titles/H1s | `noindex,follow`, no SERP impact; acceptable by design. | Nothing required. |
| **L10** personal Gmail as contact | Same decision as above. | Domain mailbox. |

### 9.3 Gate changes

`qa_deep.py` was updated so it verifies fixes rather than asserting old defects:

- `internal-exposure-src` is no longer an unconditional CRITICAL — it reads
  `sync_marketing()` / `sync_ops()` and fails only if `shutil.copytree` returns or
  `_copy_publishable()` disappears.
- `INTERNAL_BAD` dropped `.json` (the dashboards legitimately fetch their JSON) and
  kept `.py .sh .md .csv .txt`.
- The consent checks now test what the code does: no static `gtag.js` `<script>`,
  `gl_analytics` re-checked on later page views, and `/privacy/` must name every
  service that actually runs (GA4, FormSubmit, Google Fonts, Mayzing).
- New: generated-lockup presence + no `logo[12].webp` anywhere; `drops-dropped.json`
  arithmetic; a **region-scoped generic duplicate-sentence check** (any 8+-word
  sentence repeated across >10 live product pages inside `#story`/`#why`/`#who`,
  with legally required notices allowlisted because they *must* be identical).
- The hard-coded-season-date scan ignores comments and docstrings (the original run
  reported 7 "hard-coded dates" that were 6 comments plus one real string), the
  `no-cors` check matches actual `mode:'no-cors'` usage rather than prose about it,
  the drops finding is MEDIUM and describes the build-time warning accurately, and
  the `/ops/board/` policy check only scores **non-current** people (`Jordan Love`
  is current, so his scored row is correct).

`tests/test_layout.py`: 220 → **236 tests**. Fifteen new ones in
`AuditFixes20260918` (season prose vs `SEASON`, recap grammar, consent gating,
form endpoints, feed validity, stray verification files, generated lockups,
crawl-typo alts, image load hints, heading order, FTI retirement filter,
unpublished source files, drops accounting, gallery duplicates) and a
`test_no_official_mark_files_anywhere`. Three existing tests pinned the *old*
behaviour and were rewritten to pin the new one, keeping their original intent:
`test_collection_logos_are_light` (now checks the generated SVG lockups are small
**and** that the official-mark webps do not come back),
`test_full_index_page_retained` (leaderboard still not truncated, but must exclude
non-current people), and `test_hero_and_logo_urls_unchanged` (heroes still locked;
the logo lock now points at the generated lockups).

### 9.4 Gate results after the fixes

```
python3 -m unittest discover -s tests   # Ran 236 tests … OK (skipped=17)
python3 src/build.py                    # built 84 products, 4 collections, 108 urls
                                        # + WARNING /drops/: 8 of 24 queued drops …
python3 qa_audit.py                     # TOTAL: 0 · un-hinted <img> pages: 0
python3 qa_http.py http://127.0.0.1:8123  # PASS · 108 URLs, 0 dead links,
                                        # 0 broken local images, 85 stubs OK
python3 qa_deep.py                      # CRITICAL=1 HIGH=2 MEDIUM=6 LOW=0 (exit 1)
```

Before the fixes `qa_deep.py` reported **CRITICAL=5 HIGH=5 MEDIUM=7 LOW=3**. What
remains is exactly §9.2: the design-law CRITICAL (owner decision), two HIGH
(partner-verified promo code, image/font performance) and six MEDIUM (form policy,
drops accounting now informational, brand safety, near-duplicate curation,
partner-data slugs, hot-linked imagery). `qa_deep.py` is *intended* to keep exiting
1 until the design-law decision is taken — it is the only CRITICAL left, and it is a
business call, not an oversight.

Build output is deterministic: a second `python3 src/build.py` leaves `site/`
byte-identical (`index.html`, `feed.xml`, `sitemap.xml` verified by checksum).

*Note: `ops/board/index.html`, `ops/hq/index.html` and `ops/scout/index.html` were
already modified in the working tree by the ops/marketing tooling before this work
and were left untouched and uncommitted here — this pass only changed how those
trees are **published**, not how they are generated.*

### 9.5 Follow-up (2026-09-19) — the deploy surface, closed properly

The next pass took §6 item 1 and §9.2's "generalise the cleanup" advice to their
conclusion, on the owner's instruction to strip unused pages and unwanted files
from the site.

| Finding | What changed on 2026-09-19 |
|---|---|
| **C1** internal files served publicly | The halfway fix (a `PUBLISH_EXT` allowlist) is **gone**: `build.py` no longer copies `marketing/` or `ops/` into `site/` at all. `never_publish_internal()` deletes any such tree found in `site/`, so an old deploy's copies cannot linger, and `generate_dashboards()` still regenerates the dashboards into the repo for local viewing. 28 files / 4.1 MB left the artifact: `plan.json` (1.0 MB), `commercial-brief.json` (630 KB), `social-signals.json`, `scout.json`, the ops control rooms, `dashboard.html`, `live.html` and 10 social mockups. `robots.txt` now has **no `Disallow` lines** — they were advertising `/ops/` and `/marketing/` while not protecting them. §6 item 1 ("only `dashboard.html` + assets") is superseded. |
| **M6** orphan files | Generalised from "verification files" to **any** file the build does not reference: `prune_unreferenced_assets()` removed **1,337 files / 56.6 MB** (77% of `site/img/`) — artwork for the 112 retired/hold slugs whose stub pages are text-only, legacy `-hoodie/-crewneck/-v-neck/-tank-top` renders the storefront never shows, and the orphaned official Packers logo webp §9.1 had left behind. `site/` is **83 MB → 23 MB, 1,958 files → 593**. `dl.py` now skips `delisted` + `fulfillment.hold` slugs so the crawl and the prune stop fighting, and gained the `__main__` guard §6 asked for. |
| **H4** partial | The 56 KB `assets/search-index.json` was fetched unconditionally by every page; `app.js` now loads it on focus/typing with an idle warm-up, so it is off the first paint on all 195 pages. Heroes, `srcset` and font self-hosting remain open (§9.2). |
| determinism | `_redirects` order varied per process (`FUL_HOLD` is a set), which contradicted §9.4's "byte-identical" claim. `retired_slugs()` now iterates `sorted(FUL_HOLD)`; two consecutive builds produce zero diff. |

Deliberately **not** removed: the 85 noindex redirect stubs at retired `/shop/<slug>/`
URLs (§H3/L6) — they are the published contract for retired slugs, and `qa_http.py`
verifies all 85. Kept but flagged for the owner: the duplicate root verification file
`google7e05d1ab221dce85.html`, which may still be a live Search Console property.

Gates after this pass: `tests` 240 OK (skipped=17), `qa_audit.py` `TOTAL: 0`,
`qa_http.py` PASS (108 URLs, 0 dead links, 0 broken local images, 85 stubs OK),
`qa_deep.py` CRITICAL=1 HIGH=2 MEDIUM=6 — unchanged from §9.4, i.e. only the
deferred design-law decision remains. Three new tests in
`tests/test_layout.py::DeploySurface20260919` pin it, and `qa_deep.py` now fails
loudly if an internal tree reappears in `site/` or unreferenced artwork returns.
