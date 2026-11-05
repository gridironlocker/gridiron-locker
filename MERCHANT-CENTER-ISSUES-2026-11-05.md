# Google Merchant product issues - triage (2026-11-05)

Source: the operator's Merchant Center export `product_issues_2026-11-05_19-12-27.csv`
(21 items, free listings, US). Every row carries the same issue: **Missing product
price** (`SEVERITY_DISAPPROVED`, `NOT_ELIGIBLE_OR_DISAPPROVED`, "Add a price to the
[price] attribute in your product data source").

## TL;DR

Do **not** add prices. All 21 items are designs this store deliberately does not
sell - 7 supplier campaigns that ended and 14 Cleveland designs sitting on the
fulfilment `hold` list waiting for a Mayzing upload. Google's item data is stale
crawl/upload residue from the pre-September Viralstyle pages. The fix is to
**delete these 21 items (or the stale data source that serves them) in Merchant
Center** - one operator action, steps below. Nothing in this repo feeds them.

## The 21 items

| Item ID | Google's stale title | Off-store status | Why it is off the store |
|---|---|---|---|
| `limited-edition-m-fans-n28` | Bet M Michigan Sweatshirt | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |
| `limited-edition-m-fans-n26` | Michigan Bet Block Sweatshirt | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |
| `sanders-the-next-level` | Shedeur Sanders The Next Level Shirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-m-fans` | Michigan Vs Everybody Navy Sweatshirt | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |
| `d-a-w-g-b-i-t-c-limited-edition` | Cleveland Bitcoin Bulldawgs Sweatshirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-2024n2` | Dawg Life Bulldog Sweatshirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-m-vs-all` | Michigan M Vs All Tee | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |
| `limited-edition-m-fans-n30` | Michigan Vs Everybody Grey Sweatshirt | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |
| `limited-edition-b-e-k-i-n-d` | Be Kind Cleveland Elf Sweatshirt | vintage Cleveland tee | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `cleveland-retro-vintage-classic-ohio-gif` | Vintage Cleveland Script Hoodie | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-no-fly-zone-denzel` | No Fly Zone Denzel Ward Browns Shirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-tee-0-01-1` | Limited Edition 0-01 Michigan Tee | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |
| `whispered-go-browns` | So I Whispered Go Browns Funny Shirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `play-off-pound-shirt` | Playoff Pound And Determined Shirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `all-we-want-all-we-got-25` | Cleveland Under Dawgs Playoffs Shirt | Cleveland fan shirt | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `winter-hat-beanie-browns` | Browns Orange Winter Beanie | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-cleveland` | Cleveland Bulldog Red Sweatshirt | Gridiron Locker | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-go-b-r-o-w-n-s` | Limited Edition Go B R O W N S | fan-made Cleveland t-shirt | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `winter-hat-beanie-go-browns` | Go Browns Orange Winter Beanie | Cleveland football apparel | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `bend-football-fans` | Bend & Snap Funny Football Shirt | Cleveland humour tee | fulfillment hold | awaiting Mayzing upload; withheld from storefront |
| `limited-edition-m-fans-n29` | Michigan Bet Ornate Sweatshirt | Gridiron Locker | delisted.json | supplier campaign ended (2026-09-12) |

Every one of these slugs is either in `data/delisted.json` or in the `hold` list of
`data/fulfillment.json` - both documented, deliberate removals from the September
Viralstyle-to-Mayzing migration. Their pages are `noindex` "design moved" redirect
stubs pointing at the relevant collection; none has a buy path anywhere.

## What we verified in the repo

- **The scheduled-fetch feed never contained them.** `site/feeds/google-merchant.xml`
  (the data source documented in the README: Merchant Center -> Products -> Data
  sources -> Scheduled fetch, daily) shipped 89 items at creation on 2026-10-03 and
  95 today (96 until the 2026-11-05 refresh retired `limited-edition-grb25`);
  every historical version carries a price on every item and excludes
  retired and held slugs by design. The flagged IDs appear in no version.
- **The sitemap does not list them** and the stub pages are `noindex`.
- **The Mayzing catalogues do not contain them** (`data/mayzing_products.json`,
  `data/mayzing_michigan.json`, both captured 2026-09-12) - they are Viralstyle-era
  campaigns (`data/products.json`), so Mayzing cannot be the source either.
- **Their Google titles are pre-rewrite page titles** ("... | Cleveland humour tee"
  style), i.e. Google captured these items when the full PDPs still existed, before
  the September migration, and has not refreshed them from any current source.
- A regression test now pins the feed contract: `tests/test_google_merchant.py::
  test_never_lists_held_or_delisted_slugs` fails the build if a held or delisted
  slug ever enters the feed, or if any feed item lacks a price.

## Operator action (Merchant Center) - decided 2026-11-05: drop the 21 items

1. Open `merchants.google.com` -> the account -> left menu **Products -> Data
   sources**.
2. Skip the source that shows `https://gridironlocker.store/feeds/google-merchant.xml`
   (the healthy scheduled fetch - it never served these items). For each other
   source (likely an **"Automatic feed from website"** or an **uploaded file**,
   the "US" label of the export), open it -> **Items** tab -> paste
   `sanders-the-next-level` in the item search. The source that finds it is the
   stale one.
3. Preferred: delete that whole stale source (**⋮ / More actions -> Delete /
   Remove**). It serves nothing the store still sells. If it is an automatic
   website feed, also confirm auto-creation is off afterwards. The scheduled
   fetch remains the single product source.
   Alternative: in that source's Items tab, select all its not-approved items
   (they are exactly these 21) -> **⋮ -> Delete**.
4. Do **not** click "Add a price" or "Request review" on these items - the
   landing pages sell nothing, so any approval would only fail again.
5. Verify: **Products -> All items** - the 21 disappear within a few days of
   Google processing the deletion; the issues report history can lag up to
   ~30 days before it looks clean.

(Button labels vary slightly between account UIs - if something looks
different, capture what you see and it can be mapped.)

## Why not to "fix" it by adding a price

- These products have **no sellable page**: the stubs redirect to collection pages,
  and the supplier campaigns for the Michigan group have ended entirely. A priced
  item whose landing page cannot sell violates Google's feed-to-landing rules and
  earns a worse disapproval later.
- `limited-edition-no-fly-zone-denzel` and `sanders-the-next-level` are player-name
  designs already withheld under the IP-risk policy - re-listing them would promote
  exactly what the hold exists to stop.
- The `hold` list exists to keep customers away from the dead Viralstyle checkout
  ("so no customer is handed to Viralstyle") - free listings to a dead end would
  undo that.

## When these designs should come back to Google

The documented hold workflow already covers it - no new process needed:

1. Upload the design to Mayzing (operator action on the Mayzing storefront).
2. Remove its slug from `hold` in `data/fulfillment.json` and add the product to
   `data/mayzing_products.json`.
3. Rebuild - the page returns and the design re-enters
   `site/feeds/google-merchant.xml` automatically with its Mayzing price.

The 7 "supplier campaign ended" slugs are gone for good unless the campaign is
recreated on Mayzing first (same workflow).

Process gap noted while triaging: `limited-edition-grb25` (retired by the
2026-11-05 refresh) sits in neither `delisted.json` nor the `hold` list - its
stub comes from the stale-crawl path. Future retirements should record the
slug and reason in `data/delisted.json` so feeds, sitemap pins and Merchant
cleanup all follow automatically.
