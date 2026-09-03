# How to add a new design from Viralstyle to your storefront

Your site is built as **static HTML pages** that are generated from the data you
already have in Viralstyle. Adding a new design is a 2-part job:

1. **Publish the design on Viralstyle** (you do this in your Viralstyle account).
2. **Refresh your site so it picks up the new design** (the automated pipeline below).

You never hand-write a product page. The scraper + builder generate one for every
design automatically.

---

## Part 1 — On Viralstyle (the source of truth)

1. Log in to Viralstyle and create your design **in one of your 4 store collections**:
   - Cleveland Browns → `.../Cleveland-Browns`
   - Dallas → `.../dallas-vintage-sports`
   - Green Bay Packers → `.../Packss`
   - Michigan → `.../MICHIG`
2. Publish / make it live. Note the **product slug** in the URL, e.g.
   `https://viralstyle.com/kebystore/my-new-design`.

That's it on their side. The slug is all the scraper needs.

---

## Part 2 — Refresh your site (choose ONE path)

### Option A — Fully automatic (recommended, no coding)
The included **GitHub Actions workflow** re-crawls Viralstyle, downloads new images,
and rebuilds the site every day. If you're on a phone / don't want to touch code:

1. Make sure the workflow file is in your repo:
   `.github/workflows/refresh.yml`
2. When you publish a new design on Viralstyle, **just wait for the next daily run**
   (06:15 UTC) or trigger it manually:
   - GitHub → your repo → **Actions** → **Refresh site** → **Run workflow**.
3. GitHub Pages deploys the rebuilt site automatically.

> **The design publishes itself.** As of the automatic-publishing change, a newly crawled
> slug no longer needs a hand-written entry before it can go live: the build synthesises a
> product name, artwork line and keywords from the scraped campaign, writes the full product
> page, schema, sitemap and RSS entry, and prints
> `auto-published N new design(s) on generated copy: <slug>`.
> Previously a new slug crashed the whole build with a `KeyError` and took the site down.
>
> The generated copy is deliberately plain, so **add the design's SEO text** (below) when you
> get a chance to make the page rank properly.

### Option B — Run it yourself (if you have the code)
From the project folder on your computer:

```bash
# 1. Re-scan the collection pages for new designs
python scrape_list.py

# 2. Crawl each design's full product data + images
python scrape_products.py

# 3. Download the high-res product images
python dl.py

# 4. Rebuild all HTML pages
python src/build.py
```

Then push the `site/` folder to GitHub Pages.

---

## Step 3 — Add SEO text for the new design (1 small edit, once per design)

The crawler brings in the product automatically, but each product page's rich SEO copy
(name, artwork text, long-tail keywords) lives in **`src/catalog.py`** and is hand-tuned.

Open `src/catalog.py` and add one line for your new design using its **slug**:

```python
"my-new-design": dict(
    name="Dallas Star Vintage Football Tee",      # product page H1 / title
    art="LONE STAR ATHLETICS - EST 1960",          # text printed on the garment
    kw=["dallas vintage tee", "lone star football shirt", "texas star tee"],
    theme="retro",                                  # player | funny | retro | city | classic | family | halloween | playoff
),
```

Then rebuild (`python src/build.py`) and redeploy. The page, the schema, the
sitemap entry and the RSS feed are all created from this one line.

---

## What happens automatically

For every design, the pipeline creates:
- a dedicated SEO product page under `site/shop/<slug>/`
- Product JSON-LD schema (name, image, price, rating, offers)
- the buy button linking straight to that design's Viralstyle checkout
- a sitemap.xml entry, RSS feed entry, and breadcrumbs
- the design appears on its collection page and in the Trending rail (if hot)

## Retiring a design (player left, mark you cannot use)

Deleting copy is not enough - the crawler will just pick the campaign up again on the next run.
Add the slug to **`data/retired.json`** with a short reason:

```json
{ "retired": { "flacco-fever": "left the team" } }
```

Rebuild. The design disappears from every page, the sitemap, the RSS feed, the trend rails, the
marketing plan and the ops board, and its previously built page under `site/shop/<slug>/` is
deleted. The ops dashboard lists retired designs separately from dead campaigns so you can tell
"we pulled this" apart from "the crawl broke". Remove the line to bring it back.

## Removing a design

Delete the line in `src/catalog.py` (or leave it — dead campaigns are auto-skipped),
then re-run the build. The scraper already ignores closed/dead campaigns.
