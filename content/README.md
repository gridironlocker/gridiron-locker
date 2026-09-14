# content/ — publish-ready SEO articles (NOT deployed)

This directory holds drafted, WordPress-ready articles and their supporting metadata.
**Nothing here is published, and nothing here is a build input.** `src/build.py` does not
read this folder, and it must never be made to — same separation rule as `marketing/`
(`AGENTS.md` §3.4). If an article is approved for the storefront, it is implemented in
`src/` by the storefront owner and re-emitted into `site/`; it is not hand-copied into `site/`.

## Files in this batch — Browns QB1 (2026-09-14)

| File | What it is |
|---|---|
| `2026-09-14-browns-qb1-watson-sanders.md` | Full deliverable: research log, trend scoring, fact-check ledger, SEO package, internal-link plan, product/design opportunity, image briefs + alt text, sources, self-audit |
| `2026-09-14-browns-qb1-watson-sanders-wordpress.html` | The article body, ready to paste into a Custom HTML block. SEO meta is in the leading HTML comment |
| `2026-09-14-browns-qb1-faq-schema.json` | Valid `FAQPage` JSON-LD, 9 questions, matching the article's FAQ block exactly |

## Facts are dated. Re-verify before publishing.

Every score, stat, quote and record in this batch was verified on **2026-09-14**. The article
is deliberately built around a decision clock (Week 2 in Tampa on Sep 20, home opener Sep 27),
so it stays useful *after* the news moves — but the Quick Answer block must be updated the
moment a Week 3 starter is named. Do not publish it on Sep 21 still saying "Monday's announcement."

## Product claims are gated on `data/catalogue-live.json`

Only one product is named in this article (`make-them-know-your-name`), and it was checked
against the live catalogue contract: sellable, published, $21.00, Men's T-Shirt, Dark Chocolate,
S–5XL, fulfilled by Mayzing.

**This is load-bearing, because it is the trap in this repo:** all `sanders-*-special-edition`
slugs are retired `noindex` stubs (`site/shop/sanders-*/` = "Moved"), yet `marketing/`'s planners
— which read the stale `data/products.json` — still rank them at the top of their queues
(`AGENTS.md` §5). `trend-report.md` for 2026-09-14 also emitted a `viralstyle.com/kebystore/...`
URL for the Cowboys. **Do not link to either from content.** Read `data/catalogue-live.json`
instead, and treat its `site_published` flag as the only permission slip.
