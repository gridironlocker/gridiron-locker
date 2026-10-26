# Growth & Sales Recovery Plan — 2026-10-26

**Question:** 2+ months, zero sales. Is it something on the site? What's the quick fix?  
**Constraints honored:** no changes to existing images, titles, product copy, or collections.  
**Companion docs:** `SITE-AUDIT-2026-10-26.md` (technical audit), `marketing/REVENUE_PLAYBOOK.md` (content engine).

---

## 1. The verdict in one paragraph

The site is not what's blocking sales. The site is technically clean (0 broken links, 96/96 correct
checkouts, fast crawl budget, valid schema) — **but almost nobody arrives**. Two months of peak NFL
season through 96 designs across four fanbases producing zero orders means the qualified-visitor
count is close to zero (warm fan traffic converts ~1–2%; even 300 real visitors should have produced
sales). The problem is **distribution and measurement**, not the storefront. And because analytics
is half-switched-off (details below), the store has been flying blind while the funnel dried up.

## 2. What I checked (and found)

### 2.1 Search visibility & backlinks — the real bottleneck

- **Your own brand name is owned by GitHub, not the store.** Search "gridironlocker" and the top
  result is `github.com/gridironlocker/gridiron-locker`. The storefront is not the #1 result for
  its own brand.
- **Money keywords are monopolized by incumbents.** For "cleveland browns funny shirts"-type
  queries, page one is: official shops (shop.clevelandbrowns.com, nflshop.com, fanatics.com,
  '47/Rally House) **plus Etsy, TeePublic, Redbubble, eBay, Walmart**. The fan-art/funny niche is
  held by Etsy sellers with 100–3,500+ sales, review moats, and **free shipping** at $20–27.
- **Backlink profile ≈ zero.** No discoverable third-party mentions, no press, no forum presence.
  A young domain with no authority cannot outrank Etsy/Fanatics in months — it takes years or
  off-site demand generation.
- **Implication:** more on-site SEO tweaks cannot fix a distribution problem. The store needs to go
  where the buyers already are.

### 2.2 Analytics — half-blind

| Channel | State | Problem |
|---|---|---|
| GA4 (`G-5RHGJSLZNG`) | Live but **consent-gated** | The tag never loads until a visitor opts in. GA4 sees a small fraction of real traffic and no funnel data for the rest. |
| Pinterest Tag | **Dead — `pinterest_tag_id` is empty** (`src/config.json`) | PR #127 built the integration; the tag ID was never pasted in. Zero Pinterest conversions/traffic attribution possible. |
| Search Console | Verified, but `data/seo/gsc_export.json` is **empty** | No query, position, or CTR data anywhere in the repo. The SEO engine's weak-CTR detection is blind. |
| Merchant Center feed | Built (`/feeds/google-merchant.xml`) | Operator-side setup (claim, scheduled fetch, shipping) unverified. Fan-merch disapprovals likely — check Diagnostics. |
| Partner checkout sales | Mayzing/Viralstyle dashboards | The only source of truth for orders — and it says 0. |

**30-minute measurement fix (operator steps):**
1. Search Console → Performance → last 3 months → Export → paste the rows into
   `data/seo/gsc_export.json` (schema documented in the file). Then `python3 -m seo_engine audit`
   reports weak-CTR pages and real query gaps.
2. Pinterest Business → Ads Manager → create Tag → paste the ID into `src/config.json`
   (`pinterest_tag_id`) → next rebuild loads it for consenting visitors. Also confirm the catalog
   data source `https://gridironlocker.store/feeds/pinterest.csv` is scheduled daily.
3. Merchant Center → confirm the daily fetch of `/feeds/google-merchant.xml` ran and read
   Diagnostics. Start with free listings only.
4. Read GA4 with the consent caveat in mind — under-reporting is expected; look at trends, not absolutes.

### 2.3 Why the site itself still leaks buyers (fixes need your sign-off, content is frozen)

1. **The site ejects shoppers at the moment of interest.** Since PRs #198/#202 every product card
   hands off straight to `gridironlocker.shop`. Good for checkout friction; bad because the buyer
   lands on a *different, plainer* store (theme mismatch documented in `MAYZING-STORE-THEME.md`),
   and **your pixels never see the checkout side** — you can't retarget cart abandoners.
2. **Zero social proof by policy.** No reviews, no ratings, no "sold" signals (the repo
   deliberately bans fabricated ones — correct — but there is also no *real* review import from the
   partner stores, no UGC wall).
3. **No email/lead capture.** Every visitor who doesn't buy on the first visit is gone forever.
4. **No trust bridge** between "cool fan design" and "give a stranger $27 + shipping" —
   the domain is unknown; the checkout is on yet another unknown domain.

## 3. The quick solution — sequenced by speed-to-revenue

### This week (do in this order)

1. **Sell where the buyers already are: list the catalogue on Etsy.** This is the fastest honest
   path to the first sale. The SERP evidence is unambiguous — Etsy owns "funny browns shirt",
   "dawg pound shirt", "michigan bet shirt" with built-in search demand and buyer trust. Start
   with the 10 best-selling-silhouette designs, free shipping baked into the price ($24.99–27.99),
   real mockups you already have. eBay is the same play for vintage-flavored designs. (TeePublic/
   Redbubble are the zero-inventory alternative.)
2. **Switch measurement on** (§2.2, 30 minutes) — so every later decision has data.
3. **Micro paid tests: $10–20/day for 7 days** on Pinterest Ads (catalog feed is built) and Meta/
   TikTok, 2–3 designs, creative tied to this week's games. Two goals: first sales, and a
   retargeting audience of store visitors. At $0.30–0.80 CPC this buys 300–1,000 real visits —
   more qualified traffic than SEO currently produces in a month. Kill what doesn't convert;
   scale what does.
4. **Activate the creator lockers.** Joe, Bella and The Typical Browns Fan Show already have pages.
   Brief them to post game-day content linking their locker every game week; offer a simple
   affiliate cut (Mayzing supports creator-attributed links — the UTM plumbing is already in).

### This month

5. **Newsjack with the trend engine you already built** (`/drops/`, `radar/`) — the
   trade deadline (Nov 4), rivalry week, Michigan–Ohio State (Nov 28) are all buying moments.
   Ship a design within 24h of each storyline and push it through Pinterest + creators.
6. **Bing Webmaster + IndexNow** — free, five minutes, non-Google surface area.
7. **Real limited drops** ("this design retires Sunday") — real urgency converts and is legal
   when it's true.

### Next (needs a content unfreeze — propose, don't apply)

- Real-review integration from Mayzing/Viralstyle order feedback; UGC wall.
- Email capture (exit-intent + post-click) — the single biggest structural leak.
- Theme continuity with the Mayzing store (the `MAYZING-STORE-THEME.md` spec is ready).
- Retargeting pixels on the store side.

## 4. "Black hacks" — the honest answer

You asked what black-hat tricks I would use. Straight answer: **none of them, and for this
business specifically they are close to suicidal.** Not a moral lecture — a risk calculation:

- **Your entire business is Google organic traffic + two supplier platforms.** The known black-hat
  toolkit — bought/PBN backlinks, fake reviews and ratings, bot traffic, engagement pods, cloaked
  doorway pages, keyword-stuffed hidden text, negative SEO against competitors, spam DMs — is
  exactly what Google's manual-action teams and marketplace fraud teams look for. One penalty or
  one Mayzing/Viralstyle policy ban and the store is done. There is no second traffic channel to
  fall back on.
- **You are already carrying unresolved IP exposure** (player likenesses and team marks — the
  critical finding in `SITE-AUDIT-2026-10-26.md`). Black-hat tactics make the brand *visible* to
  precisely the rights holders and platform trust-and-safety teams you least want attention from.
- **Fake reviews are now literally illegal** in the US and EU (FTC rule, EU UCPD), not just
  against policy — and a store with zero sales posting glowing reviews is trivially detectable.
- They also **don't work anymore** for a store at zero: fake signals inflate nothing when there is
  no real traffic to convert.

What I will happily build instead — the aggressive versions of each, minus the deception:

| Tempting black-hat move | Why it fails here | The aggressive-but-clean version |
|---|---|---|
| Buy backlinks / PBN | Manual action = total collapse | Digital PR stunts, creator links, real mentions in fan media, subreddit AMAs |
| Fake reviews / sold counters | Illegal, banned, detectable | Seed free product to 10 real fans for honest reviews; import real partner-store reviews |
| Bot traffic / engagement pods | Zero revenue, poisons analytics | $10/day real paid traffic with conversion tracking |
| Cloaking / doorways / hidden text | Deindex risk | Programmatic SEO done properly (already yours) + the `/drops/` freshness engine |
| Negative SEO / click fraud on rivals | Harms third parties; I won't build it | Outbid them on long-tail ad keywords they ignore |
| Spam DMs / follow-unfollow bots | Account bans | Creator affiliate program with real commissions |
| Fake scarcity | Kills trust when exposed | Real limited drops with real retire dates |

The fastest *legitimate* lever — marketplaces and paid tests from §3 — outperforms every
black-hat trick within weeks, with the business still alive afterward.

## 5. What I changed today (code + SEO only)

| Change | File | Effect |
|---|---|---|
| 3 meta descriptions trimmed to 158 chars | `data/seo/overrides.json` | SERP snippets won't be cut mid-sentence; lands at next auto-rebuild. **Titles untouched.** |
| `dl.py` now has a `__main__` guard | `dl.py` | Importing it is side-effect free (it used to download and rewrite `data/products_live.json` on import) |

Everything else from the audit that would touch images/titles/collections is deliberately **not**
applied, per your instruction.

## 6. What I need from you

1. **GSC export** pasted into `data/seo/gsc_export.json` (or give the go-ahead for me to add a CSV
   importer to the SEO engine).
2. **Pinterest Tag ID** created and pasted (I'll wire the config value in).
3. **Decision: which demand channel first** — Etsy/eBay listings, paid micro-tests, or creator
   activation. All three are ready to execute; they need your accounts and a small budget.
4. **A date for the IP/legal decision** on player-named designs — it caps everything above.
