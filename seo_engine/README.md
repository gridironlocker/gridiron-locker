# Gridiron SEO Engine

Controlled-autonomy SEO for the Gridiron Locker static storefront.

```
        GSC (optional) + site/ crawl + catalogue + trends
                         │
                         ▼
                    AI / rule DECISION
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
          AUTO          PR          HUMAN
            │            │            │
            ▼            ▼            ▼
   data/seo/overrides  proposals/   flags only
            │            │
            ▼            ▼
      src/build.py    you review
            │            │
            └─────┬──────┘
                  ▼
               site/  →  deploy  →  verify  →  learn
```

## Why this shape (not "AI rewrites the live site")

Copied from production-tested architectures, then adapted to **this** repo:

| Model | What we took |
|---|---|
| **RankEngine** | audit → decide → apply → **verify** loop |
| **Ahrefs Agent A** | ecommerce ranking awareness + competitor posture |
| **Open-source Agentic SEO** | GSC + crawler + Git-friendly outputs |
| **Claude SEO Agent** | fixes against the **codebase**, not the CDN |

And the hard constraint from `AGENTS.md`:

> `site/**` is generated. Never hand-edit; change `src/` and rebuild.

So the engine **never** patches `site/**/*.html`. AUTO changes land in
`data/seo/overrides.json`; `src/build.py` reads them on the next rebuild.

## Modes

| Mode | What | How it lands |
|---|---|---|
| **AUTO** | missing/too-long title & description, weak-CTR title (when GSC data exists), missing OG tags | `data/seo/overrides.json` → rebuild |
| **PR** | new guides, collection rewrites, internal-link clusters, schema enrichment | `data/seo/proposals/pr-*.md` for human review |
| **HUMAN** | URL change, delete, merge, redirect remap | `data/seo/proposals/human-*.json` — flag only |

## Commands

```bash
# Report-only full loop (default — safe)
python3 -m seo_engine run

# Step by step
python3 -m seo_engine audit --save
python3 -m seo_engine decide --save
python3 -m seo_engine apply                  # dry-run
python3 -m seo_engine apply --commit         # write overrides.json
python3 -m seo_engine opportunities

# After a rebuild:
python3 src/build.py
python3 -m seo_engine verify --record
python3 qa_audit.py                          # must stay TOTAL: 0
```

## GSC data (optional, makes the engine smarter)

Drop a Search Console export into `data/seo/gsc_export.json`:

```json
{
  "rows": [
    {
      "page": "https://gridironlocker.store/michigan-wolverines-shirts/",
      "query": "michigan football shirts",
      "clicks": 12,
      "impressions": 840,
      "ctr": 0.014,
      "position": 12.4
    }
  ]
}
```

No rows → engine still runs technical audit; it just will not emit
`weak_ctr_title` or GSC content-gap opportunities. **Numbers are never invented.**

## What AUTO will not do

- Edit `site/` directly
- Change product URLs, H1s, or schema without a PR
- Create thin fan-intent landing pages (`/search/` already covers filters)
- Add fabricated ratings, stock scarcity, or "official" claims
- Stuff `<meta name="keywords">` as a ranking strategy
- Touch `/ops/` or `/marketing/`

## Integration with the existing build

`src/build.py::head()` and the product/collection page builders read
`data/seo/overrides.json` via `seo_overrides_for(path)`. If an override
supplies `title` / `meta_description` / `og_*`, those win over the generated
defaults. Empty file = zero behaviour change.

## Learning loop

`data/seo/learning_memory.json` stores:

- verification pass/fail after each apply+rebuild
- operator-supplied before/after GSC rows keyed by `change_id`

That is the compounding asset. Without real GSC numbers it stays empty on
purpose — same rule as `marketing/performance-memory.json`.

## Ownership

| Path | Owner |
|---|---|
| `seo_engine/**` | Arena (storefront / build lane) |
| `data/seo/**` | shared read; engine writes |
| `src/build.py` override hook | Arena |
| GSC export feed | ChatGPT / operator (Task 3 territory) |
