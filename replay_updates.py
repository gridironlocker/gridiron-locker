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


def scrape_entry(slug, c):
    cid, base = c["campaign"], c["base"]
    asset = f"https://assets.viralstyle.com/campaigns/{cid}/{base}"
    # Viralstyle mockup keys are three-part: <design>-<colour>-<style>. Every
    # swatch mockup on the campaign page repeats the design id (the first
    # component of the base key) in front of its own two-part key, so it has
    # to be re-attached when building the asset URLs (verified against the
    # live pages: .../vZ4xZz-pa62v9q-a163Wxx-front-small.jpg etc).
    design = base.split("-")[0]
    swatches = sorted({
        f"https://assets.viralstyle.com/campaigns/{cid}/{design}-{k}-front-small.jpg"
        for k in c["swatch_keys"]
    })
    return {
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
        local = f"/img/p/{slug}-{tag}.jpg"
        if os.path.isfile(os.path.join(ROOT, "site", local.lstrip("/"))):
            img[tag] = local
    entry["img"] = img
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
