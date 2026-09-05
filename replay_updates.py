#!/usr/bin/env python3
"""Replay the final unpushed storefront updates.

Idempotent delta applied on top of main (post #21):

  (a) Inject 4 directly-scraped Viralstyle campaigns into
      data/products.json, data/products_live.json and data/collections.json.
      The campaigns are live under https://viralstyle.com/kebystore/<slug>
      but are NOT members of the store's collection listing pages, so they are
      merged in directly rather than relying on scrape_list.py.
  (b) Point src/config.json at the custom domain (https://gridironlocker.store)
      and write site/CNAME (GitHub Pages custom-domain file).
  (c) Add an abs_url() helper to src/build.py (idempotent text patch).

Run from the repo root:  python3 replay_updates.py
Safe to run repeatedly.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# (a) Directly-scraped campaigns (captured 2026-09-03 from the live pages).
# Swatch list is the set of -front-small mockups on the campaign page; the
# project's parser stores it sorted, so we sort here too.
# ---------------------------------------------------------------------------
CAMPAIGNS = {
    "let-it-rip": {
        "title": "Let it Rip",
        "price_usd": "24.99",
        "brand": "THREADFAST",
        "campaign": "b88423c0-6cfe-6024-25ce-d63bab291b5e",
        "base": "vZ4xZz-y0WG3ez-bX6W5E1",
        "swatch_keys": [
            "y0WG3ez-bX6W5E1", "pa62v9q-a163Wxx", "Bao8YLo-3W1e4nq",
            "a163ryY-WmoG486", "3W1eyMw-58EGlpK", "WmoGLP0-8GPz7mk",
            "58EGBVD-vo6l08o", "8GPzObe-9MqYnGA", "vo6lBXV-kZMBy0G",
            "9MqYOEY-n86xXL9", "kZMBaGJ-y0WGJkw",
        ],
        "styles": [
            "Premium Unisex Tee", "Women's Tank Top", "Unisex Cotton Tee",
            "Unisex Hoodie", "Mens V-Neck", "Men's Tank Top",
            "Women's V-Neck", "Crew Neck Sweatshirt", "Dry Sport Tee",
            "Signature Soft Tee", "Women's Crew Tee",
        ],
        "style_prices": {
            "Premium Unisex Tee": 2361.31,
            "Women's Tank Top": 2408.0,
            "Unisex Cotton Tee": 2408.0,
            "Unisex Hoodie": 3494.74,
            "Mens V-Neck": 2549.0,
            "Men's Tank Top": 2408.0,
            "Women's V-Neck": 2549.0,
            "Crew Neck Sweatshirt": 3116.93,
            "Dry Sport Tee": 2643.0,
            "Signature Soft Tee": 2455.0,
            "Women's Crew Tee": 2455.0,
        },
        # Thumbnail row in DISPLAYED order: one mockup per style,
        # positionally aligned with "styles" above (verified live).
        "style_thumbs": [
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-y0WG3ez-bX6W5E1-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-pa62v9q-a163Wxx-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-Bao8YLo-3W1e4nq-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-a163ryY-WmoG486-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-3W1eyMw-58EGlpK-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-WmoGLP0-8GPz7mk-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-58EGBVD-vo6l08o-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-8GPzObe-9MqYnGA-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-vo6lBXV-kZMBy0G-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-9MqYOEY-n86xXL9-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/b88423c0-6cfe-6024-25ce-d63bab291b5e/vZ4xZz-kZMBaGJ-y0WGJkw-front-small.jpg",
        ],
        "desc": ("Let it Rip Let it Rip PREMIUM UNISEX TEE A favorite in any "
                 "wardrobe, this super comfy tee has the ring spun cotton feel "
                 "that everyone will love."),
        "features": ("- Preshrunk 100% combed ring spun cotton "
                     "- Blended preshrunk ring spun cotton/polyester in heather "
                     "- 4.5 oz - 30 singles - Semi-fitted - Tubular construction "
                     "- Seamed collar - Shoulder to shoulder taping "
                     "- Double-needle sleeve and bottom hems - Tear away label"),
        "collection": "cleveland-browns",
        "sizes": ["S", "M", "L", "XL", "2XL", "3XL"],   # SELECT SIZE on the live page
        "list_price_inr": "Rs2,361.31",
    },
    "sanders-the-next-level": {
        "title": "Sanders The Next Level",
        "price_usd": "21.99",
        "brand": "THREADFAST",
        "campaign": "14b50ed3-e367-e7a4-25a6-ad74f334ddf8",
        "base": "pGrlGK-pa62vbb-a163Wl0",
        "swatch_keys": [
            "pa62vbb-a163Wl0", "Bao8YR1-3W1e42R", "ZQVzDJX-WmoG4Ww",
            "1MBOkPz-58EGlKn", "xx3mary-8GPz7JW", "EvokMQa-vo6l0Oz",
            "2MZlnYo-9MqYnz2", "RAoKbnb-kZMByAM", "P9oPAJQ-n86xXvp",
            "qeQR9LY-y0WGJ4K", "K2w1Lyl-pa62byK",
        ],
        "styles": [
            "Premium Unisex Tee", "Women's Tank Top", "Unisex Cotton Tee",
            "Unisex Hoodie", "Mens V-Neck", "Women's Crew Tee",
            "Men's Tank Top", "Crew Neck Sweatshirt", "Women's V-Neck",
            "Dry Sport Tee", "Signature Soft Tee",
        ],
        "style_prices": {
            "Premium Unisex Tee": 2077.84,
            "Women's Tank Top": 2120.0,
            "Unisex Cotton Tee": 2120.0,
            "Unisex Hoodie": 3075.2,
            "Mens V-Neck": 2250.0,
            "Women's Crew Tee": 2165.0,
            "Men's Tank Top": 2120.0,
            "Crew Neck Sweatshirt": 2742.75,
            "Women's V-Neck": 2250.0,
            "Dry Sport Tee": 2320.0,
            "Signature Soft Tee": 2165.0,
        },
        # Thumbnail row in DISPLAYED order: one mockup per style,
        # positionally aligned with "styles" above (verified live).
        "style_thumbs": [
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-pa62vbb-a163Wl0-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-Bao8YR1-3W1e42R-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-ZQVzDJX-WmoG4Ww-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-1MBOkPz-58EGlKn-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-xx3mary-8GPz7JW-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-EvokMQa-vo6l0Oz-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-2MZlnYo-9MqYnz2-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-RAoKbnb-kZMByAM-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-P9oPAJQ-n86xXvp-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-qeQR9LY-y0WGJ4K-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/14b50ed3-e367-e7a4-25a6-ad74f334ddf8/pGrlGK-K2w1Lyl-pa62byK-front-small.jpg",
        ],
        "desc": ("Sanders The Next Level Sanders The Next Level PREMIUM UNISEX "
                 "TEE A favorite in any wardrobe, this super comfy tee has the "
                 "ring spun cotton feel that everyone will love."),
        "features": ("- Preshrunk 100% combed ring spun cotton "
                     "- Blended preshrunk ring spun cotton/polyester in heather "
                     "- 4.5 oz - 30 singles - Semi-fitted - Tubular construction "
                     "- Seamed collar - Shoulder to shoulder taping "
                     "- Double-needle sleeve and bottom hems - Tear away label"),
        "collection": "cleveland-browns",
        "sizes": ["S", "M", "L", "XL", "2XL", "3XL"],   # SELECT SIZE on the live page
        "list_price_inr": "Rs2,077.84",
    },
    "limited-edition-m-vs-all": {
        "title": "Limited Edition M vs All",
        "price_usd": "21.99",
        "brand": "GILDAN",
        "campaign": "77f9b350-bdde-7ac4-d502-82912a02413a",
        "base": "x210xm-ZQVz9lk-WmoG4v1",
        "swatch_keys": [
            "ZQVz9lk-WmoG4v1", "xx3m1QO-8GPz7nl", "2MZloK7-9MqYnyJ",
            "P9oP6WK-n86xX73", "K2w1Abm-pa62b7J", "lK6ZP9X-ZQVzJbO",
            "mb61ekw-xx3mrbE", "JnoZGKE-2MZlYWK", "zb5J2K2-P9oPJ41",
        ],
        "styles": [
            "Women's Crew Tee", "Premium Unisex Tee", "Signature Soft Tee",
            "Unisex Hoodie", "Crew Neck Sweatshirt", "Mens V-Neck",
            "Women's V-Neck", "Men's Tank Top", "Women's Tank Top",
        ],
        "style_prices": {
            "Women's Crew Tee": 2165.0,
            "Premium Unisex Tee": 2077.84,
            "Signature Soft Tee": 2165.0,
            "Unisex Hoodie": 3075.2,
            "Crew Neck Sweatshirt": 2742.75,
            "Mens V-Neck": 2250.0,
            "Women's V-Neck": 2250.0,
            "Men's Tank Top": 2120.0,
            "Women's Tank Top": 2120.0,
        },
        # Thumbnail row in DISPLAYED order: one mockup per style,
        # positionally aligned with "styles" above (verified live).
        "style_thumbs": [
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-ZQVz9lk-WmoG4v1-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-xx3m1QO-8GPz7nl-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-2MZloK7-9MqYnyJ-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-P9oP6WK-n86xX73-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-K2w1Abm-pa62b7J-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-lK6ZP9X-ZQVzJbO-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-mb61ekw-xx3mrbE-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-JnoZGKE-2MZlYWK-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/77f9b350-bdde-7ac4-d502-82912a02413a/x210xm-zb5J2K2-P9oPJ41-front-small.jpg",
        ],
        "desc": ("Limited Edition M vs All Limited Edition M vs All WOMEN'S "
                 "CREW TEE The classic cotton look and feel you love from a "
                 "brand you trust...when it comes to t-shirts, it gets no "
                 "better than that"),
        "features": ("- Preshrunk 100% cotton "
                     "- Blended cotton/polyester in antique, heather, neon, "
                     "and safety colors - 5.3 oz "
                     "- Missy contoured silhouette with side seams "
                     "- Seamless double needle 1/2\" collar "
                     "- Taped neck and shoulders - Cap sleeves "
                     "- Double needle sleeve and bottom hems "
                     "- Tear away labels"),
        "collection": "michigan",
        "sizes": ["S", "M", "L", "XL", "2XL"],        # live page stops at 2XL (Women's Crew Tee)
        "list_price_inr": "Rs2,077.84",
    },
    "limited-edition-qb19": {
        "title": "Limited Edition QB19",
        "price_usd": "24.99",
        "brand": "BELLA",
        "campaign": "09c4bf65-b4c2-7234-1945-17df320b5bea",
        "base": "D8nY8Q-3W1emzy-Dvo9qDo",
        "swatch_keys": [
            "QkoqPK6-MxoEBay", "APo5v82-onDEG5y", "3W1emzy-Dvo9qDo",
            "WmoG5Ja-VkomlyA", "8GPzlro-7LR4zDQ", "9MqYR0o-wkabJBl",
            "n86xwA0-APo5RD5", "pa62rAk-a163WK5", "a163MVq-WmoG4pJ",
        ],
        "styles": [
            "Women's Crew Tee", "Premium Unisex Tee", "Signature Soft Tee",
            "Unisex Hoodie", "Crew Neck Sweatshirt", "Mens V-Neck",
            "Women's V-Neck", "Men's Tank Top", "Women's Tank Top",
        ],
        "style_prices": {
            "Women's Crew Tee": 2455.0,
            "Premium Unisex Tee": 2361.31,
            "Signature Soft Tee": 2455.0,
            "Unisex Hoodie": 3494.74,
            "Crew Neck Sweatshirt": 3116.93,
            "Mens V-Neck": 2549.0,
            "Women's V-Neck": 2549.0,
            "Men's Tank Top": 2408.0,
            "Women's Tank Top": 2408.0,
        },
        # Thumbnail row in DISPLAYED order: one mockup per style,
        # positionally aligned with "styles" above (verified live).
        "style_thumbs": [
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-QkoqPK6-MxoEBay-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-APo5v82-onDEG5y-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-3W1emzy-Dvo9qDo-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-WmoG5Ja-VkomlyA-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-8GPzlro-7LR4zDQ-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-9MqYR0o-wkabJBl-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-n86xwA0-APo5RD5-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-pa62rAk-a163WK5-front-small.jpg",
            "https://assets.viralstyle.com/campaigns/09c4bf65-b4c2-7234-1945-17df320b5bea/D8nY8Q-a163MVq-WmoG4pJ-front-small.jpg",
        ],
        "desc": ("Limited Edition QB19 Limited Edition QB19 SIGNATURE SOFT TEE "
                 "This updated unisex essential fits like a well-loved favorite, "
                 "featuring a crew neck, short sleeves and designed with "
                 "superior Airlume combed and ring-spun cotton. Offered in a "
                 "variety of solid and heather colors."),
        "features": ("- Solid Colors: 100% Airlume combed and ring-spun cotton "
                     "- Heather Colors: 52% Airlume combed and ring-spun cotton, "
                     "48% poly - Semi-Fitted - Tear away label"),
        "collection": "michigan",
        "sizes": ["S", "M", "L", "XL", "2XL", "3XL"],   # SELECT SIZE on the live page
        "list_price_inr": "Rs2,361.31",
    },
}

# Fallback per-style Rs prices for the older Sanders designs that come from
# scrape_products.py (not from CAMPAIGNS/campaigns_extra). Capsule values mirror
# the live SELECT STYLE block: cheapest tee is the min, hoodie ~1.48x min,
# crewneck ~1.32x min, so variant USD lands at $34.99/$30.99 off a $22.99 base.
SANDERS_STYLE_PRICES = {
    "sanders-13-special-edition": {
        "Premium Unisex Tee": 2172.56,
        "Unisex Cotton Tee": 2215.0,
        "Signature Soft Tee": 2260.0,
        "Women's Crew Tee": 2260.0,
        "Mens V-Neck": 2350.0,
        "Women's V-Neck": 2350.0,
        "Unisex Hoodie": 3215.39,
        "Crew Neck Sweatshirt": 2867.78,
    },
    "sanders-12-special-edition": {
        "Premium Unisex Tee": 2172.56,
        "Unisex Cotton Tee": 2215.0,
        "Signature Soft Tee": 2260.0,
        "Women's Crew Tee": 2260.0,
        "Mens V-Neck": 2350.0,
        "Women's V-Neck": 2350.0,
        "Unisex Hoodie": 3215.39,
        "Crew Neck Sweatshirt": 2867.78,
    },
    "sanders-special-edition": {
        "Premium Unisex Tee": 2172.56,
        "Unisex Cotton Tee": 2215.0,
        "Signature Soft Tee": 2260.0,
        "Women's Crew Tee": 2260.0,
        "Mens V-Neck": 2350.0,
        "Women's V-Neck": 2350.0,
        "Unisex Hoodie": 3215.39,
        "Crew Neck Sweatshirt": 2867.78,
    },
}

DOMAIN = "https://gridironlocker.store"
PLACEHOLDER_THUMB = ("data:image/gif;base64,"
                     "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
        fh.write("\n")


def hi(url):
    """Swap Viralstyle small/detail variants for the large mockup (dl.py)."""
    return (url.replace("-front-small.jpg", "-front-large.jpg")
                .replace("-back-small.jpg", "-back-large.jpg")
                .replace("-detail.jpg", "-large.jpg")
                .replace("-small.jpg", "-large.jpg"))


def _merge_extra_campaigns():
    """Merge data/campaigns_extra.json into CAMPAIGNS (idempotent).

    Accepts a dict {slug: entry} or a list of entries each with a slug key.
    Invalid/missing files are ignored gracefully so replay never crashes.
    """
    try:
        path = os.path.join(ROOT, "data/campaigns_extra.json")
        if not os.path.exists(path):
            return
        extra = json.load(open(path, encoding="utf-8"))
        if isinstance(extra, list):
            conv = {}
            for e in extra:
                if isinstance(e, dict) and e.get("slug"):
                    slug = e.pop("slug")
                    conv[slug] = e
            extra = conv
        if not isinstance(extra, dict):
            print("campaigns_extra merge skipped: invalid format")
            return
        merged = []
        for slug, entry in extra.items():
            if isinstance(entry, dict):
                CAMPAIGNS[slug] = entry
                merged.append(slug)
        if merged:
            print("merged campaigns_extra:", ", ".join(sorted(merged)))
    except Exception as e:
        print("campaigns_extra merge skipped:", e)


_merge_extra_campaigns()


def scrape_entry(slug, c):
    cid, base = c["campaign"], c["base"]
    asset = f"https://assets.viralstyle.com/campaigns/{cid}/{base}"
    # Viralstyle mockup keys are three-part: <design>-<colour>-<style>. Every
    # swatch mockup on the campaign page repeats the design id (the first
    # component of the base key) in front of its own two-part key, so it has
    # to be re-attached when building the asset URLs (verified against the
    # live pages: .../vZ4xZz-pa62v9q-a163Wxx-front-small.jpg etc).
    # add_campaign.py stores full 3-part keys already prefixed, so only prefix
    # when the design id is missing - never double-prefix.
    design = base.split("-")[0]
    urls = set()
    for k in c["swatch_keys"]:
        kk = k if k.startswith(design + "-") else f"{design}-{k}"
        urls.add(f"https://assets.viralstyle.com/campaigns/{cid}/{kk}-front-small.jpg")
    swatches = sorted(urls)
    entry = {
        "slug": slug,
        "title": c["title"],
        "price_usd": c["price_usd"],
        "brand": c["brand"],
        "url": f"https://viralstyle.com/kebystore/{slug}",
        "front": asset + "-front-large.jpg",
        "back": asset + "-back-large.jpg",
        "swatches": swatches,
        "styles": list(c["styles"]),
        "sizes": list(c.get("sizes") or ["S", "M", "L", "XL", "2XL", "3XL"]),
        "desc": c["desc"],
        "features": c["features"],
    }
    # Per-style Rs prices for garment-variant pricing (optional passthrough).
    if isinstance(c.get("style_prices"), dict) and c["style_prices"]:
        try:
            entry["style_prices"] = {k: float(v) for k, v in c["style_prices"].items()}
        except Exception:
            pass
    # Per-style garment mockups in DISPLAYED order (optional passthrough): one
    # thumbnail per style, positionally aligned with entry["styles"]. Kept in
    # order - never sorted - and only when the length matches the style list,
    # so a variant can never inherit another garment's mockup.
    thumbs = c.get("style_thumbs")
    if isinstance(thumbs, list) and thumbs and len(thumbs) == len(entry["styles"]):
        seen, clean = set(), []
        for u in thumbs:
            if not isinstance(u, str) or "-front-small.jpg" not in u or u in seen:
                clean = None
                break
            seen.add(u)
            clean.append(u)
        if clean and len(clean) == len(entry["styles"]):
            entry["style_thumbs"] = clean
    return entry


def with_img_map(entry):
    """Attach the local image map dl.py writes into products_live.json.

    Only images that actually exist under site/ are advertised - a failed
    dl.py pass must never put broken images on the product pages (build.py
    applies the same guard when it renders). Once dl.py downloads the real
    c0-c5 swatches, the next replay/build cycle picks them up again."""
    slug = entry["slug"]
    urls = [("front", entry["front"]), ("back", entry.get("back"))]
    for i, u in enumerate(entry.get("swatches", [])[:6]):
        urls.append((f"c{i}", u))
    img = {}
    for tag, u in urls:
        if not u:
            continue
        webp = f"/img/p/{slug}-{tag}.webp"
        jpg = f"/img/p/{slug}-{tag}.jpg"
        if os.path.isfile(os.path.join(ROOT, "site", webp.lstrip("/"))):
            img[tag] = webp
        elif os.path.isfile(os.path.join(ROOT, "site", jpg.lstrip("/"))):
            img[tag] = jpg
    entry["img"] = img
    # Per-garment variant mockups dl.py writes as <slug>-<garment>.webp, kept
    # only when the file really exists (same self-healing rule as img above).
    vimg = {}
    for garment in ("hoodie", "crewneck", "tank-top", "v-neck", "long-sleeve"):
        rel = f"/img/p/{slug}-{garment}.webp"
        if os.path.isfile(os.path.join(ROOT, "site", rel.lstrip("/"))):
            vimg[garment] = rel
    if vimg:
        entry["variant_img"] = vimg
    return entry


def inject_data():
    products = load(os.path.join(ROOT, "data/products.json"))
    live = load(os.path.join(ROOT, "data/products_live.json"))
    cols = load(os.path.join(ROOT, "data/collections.json"))

    for slug, c in CAMPAIGNS.items():
        entry = scrape_entry(slug, c)
        products[slug] = entry                    # idempotent overwrite
        live[slug] = with_img_map(dict(entry))    # same data + img map

        col = cols.get(c["collection"])
        if col is None:
            raise SystemExit(f"missing collection: {c['collection']}")
        col_products = col.setdefault("products", [])
        # Move the campaign to the front so it is visible on the homepage
        # (homepage shows the first 4 designs per team) and at the top of the
        # collection grid, not buried underneath dozens of older designs.
        col_products[:] = [p for p in col_products if p.get("slug") != slug]
        col_products.insert(0, {
            "slug": slug,
            "thumb": PLACEHOLDER_THUMB,
            "title": f"{c['title']} {c['list_price_inr']}",
        })

    # Backfill style_prices for older Sanders designs (scrape-sourced, not in
    # CAMPAIGNS). Idempotent: only fills when missing, never overwrites live
    # scraped values.
    for slug, sp in SANDERS_STYLE_PRICES.items():
        for store in (products, live):
            if slug in store and not store[slug].get("style_prices"):
                store[slug]["style_prices"] = dict(sp)

    save(os.path.join(ROOT, "data/products.json"), products)
    save(os.path.join(ROOT, "data/products_live.json"), live)
    save(os.path.join(ROOT, "data/collections.json"), cols)
    print("data: injected", len(CAMPAIGNS), "campaigns")


def inject_config():
    cfg_path = os.path.join(ROOT, "src/config.json")
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if cfg.get("domain") != DOMAIN:
        cfg["domain"] = DOMAIN
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
            fh.write("\n")
        print("config: domain ->", DOMAIN)
    else:
        print("config: domain already", DOMAIN)
    with open(os.path.join(ROOT, "site/CNAME"), "w", encoding="utf-8") as fh:
        fh.write(DOMAIN.replace("https://", "") + "\n")
    print("CNAME: written")


def inject_build_helper():
    path = os.path.join(ROOT, "src/build.py")
    src = open(path, encoding="utf-8").read()
    if "def abs_url(" in src:
        print("build.py: abs_url() already present")
        return
    anchor = 'DOMAIN = CFG["domain"].rstrip("/")\n'
    helper = (
        anchor +
        '\n\ndef abs_url(path):\n'
        '    """Return an absolute URL for a site path on the configured domain."""\n'
        '    return DOMAIN + path\n'
    )
    if anchor not in src:
        raise SystemExit("build.py: anchor not found")
    src = src.replace(anchor, helper, 1)
    # Use the helper for canonical/SEO URLs (behaviour-neutral).
    src = src.replace("    canon = DOMAIN + path\n",
                      "    canon = abs_url(path)\n", 1)
    src = src.replace("            image = DOMAIN + image\n",
                      "            image = abs_url(image)\n", 1)
    open(path, "w", encoding="utf-8").write(src)
    print("build.py: abs_url() helper added")


if __name__ == "__main__":
    inject_data()
    inject_config()
    inject_build_helper()
    print("replay complete")
