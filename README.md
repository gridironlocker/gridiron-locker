# Gridiron Locker — SEO storefront for your Viralstyle collections

A complete static website that ranks for **your** keywords and sends every visitor to the real
Viralstyle checkout. Nothing is sold here, so your Viralstyle campaigns carry zero extra risk.

**Live preview:** running on port 3000 (see the preview panel).

---

## What's in the box

| Item | Count |
|---|---|
| HTML pages | **153** |
| Product pages (one per design) | **134** |
| Collection pages | 4 |
| SEO buying guides (articles) | 4 |
| Info/trust pages | Size guide, Shipping, FAQ, About, Contact, Trademark notice, Privacy, 404 |
| Product images self-hosted | **1,011** |
| Broken links / invalid schema | **0** |

Collections: Cleveland Browns (78), Green Bay Packers (34), Michigan (12), Dallas (10).

### 4 dead campaigns found
These slugs no longer return product data on Viralstyle and were excluded — relaunch them and
re-run the build to add them:
`limited-edition-go-b-r-o-w-n-s`, `it-s-not-a-team-logo-browns-it-s-a-famil`,
`limited-edition-grb41`, `limited-edition-m`

---

## Why this converts

- **NFLShop-style product page**: big gallery + colourway swatches, style chips, size selector,
  price + slashed compare-at price + save %, star rating, urgency strip, trust badges,
  sticky mobile buy bar that never leaves the screen.
- **gvartwork-style visuals**: dark premium theme, cinematic AI hero art per collection, and each
  collection re-skins the accent colour (orange / gold / silver-navy / maize).
- **Mobile first**: 2-up product grid on phones, tap-friendly targets, sticky CTA, no layout shift
  (every image has width/height), lazy loading below the fold.
- **Every CTA** goes to the exact Viralstyle campaign URL for that design.

## Why it ranks

- Unique `<title>`, meta description, canonical, OG + Twitter cards on all 153 pages.
- **Real copy, not filler.** I read all 134 artworks and wrote each page around what the design
  actually says (e.g. "Limited Edition GRB37" is now *This Girl Loves The Pack Shirt*). Descriptions
  are template-varied so no two pages read the same.
- **Schema.org JSON-LD**: Organization, WebSite + SearchAction, CollectionPage, ItemList,
  Product + Offer + AggregateRating, BreadcrumbList, FAQPage, Article. All validated.
- `robots.txt` + `sitemap.xml` (152 URLs, lastmod/priority/changefreq).
- Internal linking: home → collections → products → related products → guides → back to collection.
- 4 long-form buying guides targeting research keywords ("michigan fan apparel buying guide").
- Trademark-safe framing: "fan-made / independent / not affiliated" disclaimers sitewide plus a
  dedicated trademark notice with a takedown route. This is what keeps aggressive keyword use
  defensible while your Viralstyle listings stay clean.

---

## Deploy it (5 minutes, free)

The `site/` folder is a plain static site — no build step, no server needed.

**Easiest — Netlify or Cloudflare Pages:** drag the `site` folder onto
app.netlify.com/drop (or Cloudflare Pages → Direct Upload). Done, HTTPS included.

**GitHub Pages:** push the contents of `site/` to a repo, Settings → Pages → deploy from branch.

### Before you go live — one edit
Open `src/config.json` and set your real domain and email:

```json
{ "site_name": "Gridiron Locker", "domain": "https://yourdomain.com", "email": "you@yourdomain.com" }
```

Then rebuild: `python3 src/build.py`
(Every canonical URL, OG tag, sitemap entry and schema block updates automatically.)

### Day 1 after launch
1. Google Search Console → add the domain → submit `/sitemap.xml`.
2. Bing Webmaster Tools → same.
3. Paste your GA4 / Meta Pixel snippet into the `head()` function in `src/build.py` and rebuild —
   buy-button clicks already fire a `buy_click` event if `gtag` exists.

---

## Keeping it updated

```bash
python3 scrape_list.py        # re-crawl the 4 collections for new/removed products
python3 scrape_products.py    # pull details for every product
python3 dl.py                 # download any new imagery
python3 src/build.py          # rebuild the site
```

New products need one line of copy facts in `src/catalog.py`
(`name`, `art`, `kw`, `theme`) — that's what makes the page read like a human wrote it.

## Files

- `site/` — the deployable website
- `src/build.py` — generator · `src/copy.py` — copywriting engine · `src/catalog.py` — per-design facts
- `src/collections_data.py` — collection SEO/brand data · `src/config.json` — your settings
- `product-index.csv` — all 134 products: name, design text, price, site URL, Viralstyle URL, keywords
- `data/` — scraped source data

---

---

# UPDATE 24 Aug 2026 - v2

## 1. The dark/white "dead box" look is fixed
Product photos now sit on a **lit pedestal**: a soft radial gradient, an inner rim highlight, a
drop shadow under the garment and a **team-coloured glow** that intensifies on hover. The card also
gets a team-colour top bar, a light sweep, and the image zooms while the back view cross-fades in.
No more white rectangles punched into a dark page.

## 2. The site now moves
- **Live countdown to kickoff** in the header bar (real ticking clock, per collection).
- **Scrolling keyword ticker** with trending terms highlighted in accent colour.
- **Scroll-reveal animations** with stagger on every section and card.
- **Animated number counters** (134 designs / 4 collections / 1,011 photos).
- Hero: slow Ken Burns zoom + drifting colour blobs.
- Buttons with shine sweep, animated nav underlines, hover lift on everything,
  sticky-header shadow, floating back-to-top button.
- All motion respects `prefers-reduced-motion`, and there is a JS-failure safety net so content
  can never be stuck invisible.

## 3. Vivid team-colour imagery
All five hero images were regenerated in true team palettes - blazing orange smoke for Cleveland,
green-and-gold blizzard for Green Bay, navy-and-silver Texas dusk for Dallas, maize-and-navy
stadium for Michigan.

**On real team logos:** I deliberately did not use them. Reproducing an NFL or university logo is
straight trademark infringement and it is exactly what gets stores shut down and payment accounts
frozen. Instead the site leans hard on **team colours**, which are not protectable the same way.
Every collection now re-skins the entire page - accents, glows, badges, buttons - to its own
palette. You get the visual identity without the legal exposure.

## 4. 2026 season intelligence (researched today)
Your catalogue had drifted out of date. The site now handles this honestly and turns it into SEO:

| Finding | What the site does |
|---|---|
| Shedeur Sanders vs Watson QB battle, decision this week | Sanders designs tagged **Trending**, surfaced on the homepage and season hub |
| Joe Flacco no longer on the roster | Flacco designs tagged **Throwback** |
| Myles Garrett traded June 2026 | Garrett designs tagged **Throwback** |
| Stefanski out, Todd Monken in as HC | Stefanski / "Run The Ball Kevin" tagged **Throwback** |
| J.J. McCarthy gone, Bryce Underwood is QB1 and a 2026 captain | McCarthy tagged **Throwback**, Underwood keywords targeted |
| Jordan Love still Green Bay QB1 | Love designs tagged **Trending** |

New **`/2026-season/` hub page** covers Week 1 dates (NFL kicks off Sept 9, first Sunday Sept 13,
Michigan opens Sept 5), what changed per roster, and the designs trending because of it.
Product pages show a live "order by [date] to wear it for Week 1" line.

## 5. Built for GitHub Pages (no DNS required)
- **All internal links are now relative** - the site works at `username.github.io/repo/`,
  at a custom domain, and by double-clicking `index.html`. One build, three environments.
- `.nojekyll` added so GitHub serves every file as-is.
- **robots.txt rewritten**: welcomes Google, Bing, Google Images and AI answer engines
  (GPTBot, PerplexityBot, ClaudeBot), with a polite `Crawl-delay: 1`.
- Sitemap regenerates with your live URL automatically.

### Publish it
Follow **`DEPLOY-GITHUB.txt`** - copy/paste commands, about 5 minutes. The key step:

```bash
python3 src/set_site.py https://YOURNAME.github.io/gridiron-locker
```

That one command rewrites every canonical URL, OG tag, schema block, robots.txt and sitemap entry.

### v3 fixes (24 Aug 2026, later)
- **Moving top bar bug fixed.** The promo bar was animated with `translateX`, which pushed the whole
  document sideways and created horizontal scroll - that is why the header and headings looked cut
  off. It now animates its gradient position instead, so nothing moves in the layout.
  Verified: **0px horizontal overflow** on desktop, collection, product and mobile.
- **Light catalogue theme.** The product grids and the whole product page are now on a soft
  off-white (#f5f8fc) with white cards, so the page background matches the product photo
  backgrounds. No more bright white squares punched into a black page - much easier on the eyes.
  Header, hero, countdown, ticker and footer stay dark for contrast.
- Fixed a real contrast bug: the "Key features" list was light grey on white.

### v4 - flattened the visual stack (24 Aug 2026)
The catalogue looked "layered and messy" because **three surfaces were stacked** behind every
product: the grey page, then a card with its own gradient panel + inner rim highlight + coloured
glow, then the product mockup's own white JPEG square. Four edges, three shades.

Now there is **one surface**: white card, white photo area, grey page. The mockup's white
background dissolves into the card because they are the exact same white. Removed the photo-panel
gradient, the inset rim, the coloured glow halo, the shine sweep and the image drop-shadow.
What remains is a single 1px border, one soft shadow, and a gentle lift + 4% image zoom on hover.
Same treatment on the product page gallery and thumbnails.

## Current state
154 pages · 438 schema blocks · **0 broken links** · **0 invalid schema** · 0 console errors · **0px horizontal overflow**.


---

# v5 - AUTOMATED TRENDING (24 Aug 2026)

## It now updates itself after deployment

`.github/workflows/refresh.yml` runs **daily at 06:15 UTC** on GitHub's servers (free), with a
manual "Run workflow" button too:

1. **Pulls live headlines** for all four teams from public Google News RSS - no API key needed.
2. **Re-scores every design automatically.** It counts how often each player/coach is mentioned in
   the last 10 days and tags products: 3+ mentions = **Trending**, 0 mentions = **Throwback**.
3. **Publishes the real headlines** on each collection page and the season hub, with source
   attribution and `rel="nofollow noopener"` links.
4. **Rebuilds all 154 pages** with a fresh `lastmod` and `dateModified`.
5. **Commits and pushes** - GitHub Pages redeploys on its own.
6. **Pings IndexNow** so Bing, Yandex and Naver recrawl within minutes.
7. **Mondays:** also re-crawls Viralstyle for new/removed designs and pulls new images.

It validated itself on the first run - with zero manual input it independently reached the same
conclusions I did by hand:

| Detected | Mentions | Auto-tag |
|---|---|---|
| Shedeur Sanders | 25 | Trending |
| Deshaun Watson | 50 | Trending (no product) |
| Todd Monken | 14 | Trending (no product) |
| Bryce Underwood | 11 | Trending (no product) |
| Kyle Whittingham | 9 | Trending (no product) |
| Joe Flacco | 0 | Throwback |
| Myles Garrett | 0 | Throwback |
| Kevin Stefanski | 0 | Throwback |
| J.J. McCarthy | 0 | Throwback |

Result: 3 Trending, 29 Throwback, 102 neutral - and it flags **product gaps**: names trending in
the news that you have no design for. That is your product roadmap, generated for you every day in
`trend-report.md` (also uploaded as a workflow artifact).

**Manual override:** create `data/trend_overrides.json` like
`{"some-product-slug": "hot"}` to force a tag regardless of the news.

## What this does and does not do for rankings

Being straight with you:

- **It does** get you recrawled faster (accurate `lastmod` is the signal Google actually uses -
  their sitemap ping endpoint was retired in June 2023), keeps time-sensitive pages relevant for
  queries like "browns qb 2026 shirt", and adds a `feed.xml` discovery channel.
- **It does not** guarantee first-page rankings. Freshness is a tiebreaker, not a trump card.
  Rankings still come from content depth, real backlinks, and click-through.
- **The real lever** is the gap report: publishing a design the week a player becomes the story is
  what wins those searches. The automation tells you when; you still have to make the shirt.

## New files
- `src/trends.py` - headline fetcher + trend scorer + gap report
- `src/indexnow.py` - instant Bing/Yandex/Naver submission
- `.github/workflows/refresh.yml` - the daily scheduler
- `site/feed.xml` - RSS feed of trending designs
- `trend-report.md` - your daily opportunity briefing


## What I'd do next (say the word)

1. **Rename the generic campaigns on Viralstyle** to the names in `product-index.csv` — those
   titles are keyword-optimised and it will lift your Viralstyle-native traffic too.
2. Fix or relaunch the 4 dead campaigns.
3. Dallas has only 10 designs and Michigan 12 — both are big search markets. Worth expanding.
4. Add a blog cadence (game-week posts) — cheapest way to build topical authority.
