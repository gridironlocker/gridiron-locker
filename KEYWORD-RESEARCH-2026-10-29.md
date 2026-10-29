# Keyword Research — Football Fan Apparel (US) — October 2026

**Method.** Three evidence tiers, never mixed:
**[VERIFIED]** our Google Search Console (28 days ending 2026-10-26, web, US-weighted) — real
impressions and positions for our own pages; impressions are the honest relative-demand signal.
**[ESTIMATED]** third-party published studies (tool: Google Keyword Planner or equivalent, as
cited, with dates) — figures are as-published, not current tool exports.
**[RELATIVE]** trend indicators (TikTok Shop search pages, Pinterest trend reports, press
coverage) — direction only, no volumes.
No volume below is invented. Competition notes come from the live SERP (Etsy, Fanatics, TeePublic,
Amazon, Dick's, Macy's dominate head terms).

## 1. Head demand for our four teams

| Keyword family | Demand | Tier | Source | Intent | Competition |
|---|---|---|---|---|---|
| Dallas Cowboys clothing terms (shirt/gear/apparel…) | ~351,349/mo combined | ESTIMATED | RushOrderTees study via CW33, Sep 2025 | Commercial | Extreme (Fanatics/Nike/official) |
| Green Bay Packers clothing terms | ~288,817/mo combined | ESTIMATED | same study | Commercial | Extreme |
| Dallas Cowboys merch terms ("merch", "merch near me"…) | ~179,008/mo combined | ESTIMATED | Oddspedia via Licensing Intl., Sep 2024 | Commercial | High |
| "dallas cowboys jersey"-family | ~51,593/mo | ESTIMATED | ShirtMax/GKeyword Planner, Aug 2024 | Commercial | High |
| "green bay packers jersey"-family | ~22,967/mo | ESTIMATED | same | Commercial | High |
| "dallas cowboys" / "green bay packers" head terms | 6.12M / 3.35M per mo US | ESTIMATED | Logical Media, 2023 (dated) | Mixed | Extreme |

**Take:** we cannot win head terms. The money is in long-tail phrase/slogan queries where our
phrase-first catalogue actually matches intent.

## 2. Verified demand already touching our pages (GSC, 28d)

| Query | Impr. | Pos. | Intent | Maps to |
|---|---:|---:|---|---|
| green bay packers shirt | 41 | 39.7 | Commercial | GB collection + all GB PDPs |
| michigan shirts | 25 | 44.6 | Commercial | Michigan collection/PDPs |
| packers shirt | 15 | 37.1 | Commercial | GB PDPs |
| dearborn michigan t-shirts / apparel / sweatshirts | 24 | 44–59 | Commercial geo | Michigan buying-guide addendum (shipped) |
| gridiron fan gear | 11 | 11 | Navigational/brand | Homepage |
| michigan t shirt(s) / michigan shirt / michigan football shirt | 30+ | 34–55 | Commercial | Michigan PDP titles |
| michigan vs everybody (shirt/gear/sweatshirt/crewneck/vs the world) | 12 | 33–59 | Commercial slogan | Vs Everybody guide (shipped) + PDP titles |
| beware of dawgs | 3 | 8.7 | Commercial slogan | Dawgs PDPs |
| funny green bay packers shirts | 2 | 36.5 | Commercial | GB funny PDPs |
| retro / throwback green bay packers shirt | 3 | 38–44 | Commercial vintage | GB retro PDPs |
| all you need is love packers shirt | 1 | 10 | Commercial slogan | grb33 |
| go blue shirt | 2 | 46 | Commercial slogan | Go Blue PDP |
| cleveland browns tie dye shirt | 1 | 38 | Commercial gap | design-queue idea |
| packers dad shirt / michigan dad shirt | 3 | 39–42 | Gift gap | gift guide keywords |
| michigan rose bowl shirt(s)/sweatshirt | 3 | 42–48 | Vintage gap | design-queue idea |
| business is finished michigan / michigan lock it in | 3 | 40–56 | Slogan gap | design-queue (phrase-safe) |

## 3. Trend signals [RELATIVE]

- **Slogan/phrase economy is the POD sweet spot.** Etsy "Browns Shirt" market and TeePublic tags
  show best-sellers are zero-logo phrases ("Another Week Without a W", "Rebuilding Since 1964",
  "This Team Makes Me Drink", "Dawg Pound Definition"). Our phrase catalogue matches this exactly.
- **"Michigan Vs. Everybody Shirt" is a live TikTok Shop search term** (TikTok Shop US search
  page, Apr 2026) with related searches "michigan wolverines shirt", "Michigan outfit" — the
  phrase crossed from stadium chant to shopping query (10k+ items sold in 48h at launch, AP via
  9and10news, Nov 2023).
- **Vintage/retro wave:** Pinterest UK "vintage football shirts" +125% in 6 months (The
  Independent, Jun 2026); "vintage soccer jersey" +200% YoY (Pinterest May 2026 report via The
  Spinoff). Note: soccer-led; for our niche it validates "vintage/retro {team} shirt" long-tails
  (already visible in our GSC: "retro green bay packers shirt").
- **Game-day is the category word** (VS PINK x NFL collection sold out in days, USA Today, Aug
  2026): "game day {team} shirt/outfit" language is how shoppers browse.
- **Gift season:** Etsy "nfl fan apparel gift" market live; "Christmas Gift for {Team} Fans" is
  standard listing language by November.

## 4. Keyword → on-page mapping (implemented in data/seo/product_keywords.json)

All 96 live products mapped: `listing_title` (product title), `primary_keyword`, up to 4
`secondary_keywords`, `description_hook`, `intent`. Composition rules (seo_engine/keywords.py):

1. Slogan-led products (funny/classic/statement + player tributes): primary = the phrase fans
   type + team + garment ("dawg life cleveland browns shirt", "jordan freaking love green bay
   packers shirt").
2. Theme-led products: "funny|vintage|game day + team + garment" matching live query language.
3. Listing titles gain the team + garment word when missing ("Playoffs" → "Playoffs Cleveland
   Browns Shirt"); already-optimized names are kept verbatim.

**Realistic ranking plan:** page-1-adjacent slogan terms (beware of dawgs, all you need is love),
page-2-3 long-tails (funny/retro packers, michigan phrase family), and the Dearborn geo cluster.
Head terms stay out of reach until authority grows (7 known backlinks, 6 on one URL).

## 5. What we deliberately do NOT target

Player-transfer rumors, other teams' phrases, "official/licensed" terms (we are fan-made and say
so), and any keyword our products cannot satisfy (thin-page rule). Product titles never claim
affiliation; team words are used descriptively per the trademark notice.
