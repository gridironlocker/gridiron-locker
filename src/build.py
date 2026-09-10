#!/usr/bin/env python3
"""Static site generator for the fan-apparel storefront."""
import json, os, re, shutil, html, sys, datetime, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from collections import OrderedDict
from collections_data import COLLECTIONS, ORDER, SEASON, NEXT_GAME
import seocopy as _c
import landing as _l
from catalog import CATALOG
import auto_copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
CFG = json.load(open(os.path.join(ROOT, "src/config.json")))
DOMAIN = CFG["domain"].rstrip("/")


def abs_url(path):
    """Return an absolute URL for a site path on the configured domain.

    Idempotent for full URLs: a freshly added campaign can hot-link its
    Viralstyle mockups while dl.py has not downloaded them locally yet, and
    those must pass through untouched instead of becoming domain+URL.
    """
    if not path:
        return path
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return DOMAIN + path
BRAND = CFG["site_name"]
TODAY = datetime.date.today().isoformat()
STYLE_PATH = os.path.join(ROOT, "src/style.css")
STYLE_VERSION = hashlib.sha256(open(STYLE_PATH, "rb").read()).hexdigest()[:8]
CTA = "#49a59c"
CTA_HOVER = "#3a847d"

# ---------------------------------------------------------- merchant schema
# Google Merchant listings (rich results + free product listings) require
# shipping and return details on every Offer, and flag the fixed
# "priceValidUntil"-only offers we used to publish as incomplete. These three
# constants are the single source of truth for the merchant facts, all taken
# from the print partner's published buyer policies (viralstyle.com/terms,
# viralstyle.zendesk.com "Printing and Shipping" / "When will I receive my
# item(s)?"): standard US shipping from $4.95, 3-5 business days of production
# (up to 7-14 at peak) then 2-3 business days domestic transit, and a 30-day
# replacement window for misprinted / damaged / defective items. If the
# partner changes a policy, change it here and every product page follows.
SHIP_US = {
    "@type": "OfferShippingDetails",
    "shippingRate": {"@type": "MonetaryAmount", "value": "4.95", "currency": "USD"},
    "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "US"},
    "deliveryTime": {
        "@type": "ShippingDeliveryTime",
        "handlingTime": {"@type": "QuantitativeValue", "minValue": 3, "maxValue": 7,
                         "unitCode": "DAY"},
        "transitTime": {"@type": "QuantitativeValue", "minValue": 2, "maxValue": 5,
                        "unitCode": "DAY"},
    },
}
# Human-readable twin of SHIP_US["deliveryTime"]: production + transit, US.
DELIVERY_TIME = "5-12 business days"
RETURN_POLICY = {
    "@type": "MerchantReturnPolicy",
    "applicableCountry": "US",
    "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
    "merchantReturnDays": 30,
    "returnMethod": "https://schema.org/ReturnByMail",
    "returnFees": "https://schema.org/FreeReturn",
    "refundType": "https://schema.org/ExchangeRefund",
    "itemCondition": "https://schema.org/DamagedCondition",
}

# ------------------------------------------------------------------- socials
# Every live brand profile, verified 2026-09-05. The footer used to link a
# single X account (@gridironlocker, 4 followers) while the 94-follower
# @gridironlocker1 - plus Instagram, Threads, Facebook, Pinterest and YouTube -
# got nothing, and the Organization/WebSite sameAs arrays pointed at four
# Viralstyle supplier storefronts instead of our own profiles. One list now
# feeds both, so a profile can never be linked in one place and forgotten in
# the other. TikTok is deliberately absent: the handle is unconfirmed.
SOCIALS = [
    ("X (@gridironlocker)",  "https://x.com/gridironlocker"),
    ("X (@gridironlocker1)", "https://x.com/gridironlocker1"),
    ("Instagram", "https://www.instagram.com/gridironlocker1"),
    ("Threads",   "https://www.threads.net/@gridironlocker1"),
    ("Facebook",  "https://www.facebook.com/GridironLocker/"),
    ("Pinterest", "https://www.pinterest.com/gridironlockergear/"),
    ("YouTube",   "https://www.youtube.com/@Gridironlocker"),
]
# Attribution tag for footer clicks only - never appended to sameAs, which must
# stay canonical for search engines.
SOCIAL_UTM = "?utm_source=site&utm_medium=social"

P = json.load(open(os.path.join(ROOT, "data/products_live.json")))
COLS = json.load(open(os.path.join(ROOT, "data/collections.json")))

# Retired designs (players/coaches who left the team). A re-crawl must never
# resurrect a page for one of these slugs, so build_model() skips them outright.
try:
    DELISTED = json.load(open(os.path.join(ROOT, "data/delisted.json"))).get("slugs", {})
except Exception:
    DELISTED = {}

# Effective per-design copy. Hand-written copy lives in src/catalog.py and wins
# over data/facts.json. For any crawled slug with no hand-written entry,
# src/auto_copy.py derives name / art / kw / theme from the campaign's own store
# title plus live trend topics, so a re-crawl can never crash the build.
_FACTS_RAW = json.load(open(os.path.join(ROOT, "data/facts.json")))
FACTS = dict(_FACTS_RAW)
for ckey in ORDER:
    for entry in COLS.get(ckey, {}).get("products", []):
        slug = entry["slug"]
        if slug in CATALOG or slug in FACTS:
            continue
        FACTS[slug] = auto_copy.derive(slug, P.get(slug) or {}, ckey)
FACTS.update(CATALOG)  # hand-written copy wins

# Unknown themes must never crash the build - fall back to "classic".
_KNOWN_THEMES = {"player", "funny", "playoff", "classic", "retro", "city", "family", "halloween"}
for _f in FACTS.values():
    if isinstance(_f, dict) and _f.get("theme") not in _KNOWN_THEMES:
        _f["theme"] = "classic"

# live trend data produced by src/trends.py (optional - site builds fine without it)
try:
    TRENDS = json.load(open(os.path.join(ROOT, "data/trends.json")))
except Exception:
    TRENDS = {"generated": None, "collections": {}}
try:
    OVERRIDES = json.load(open(os.path.join(ROOT, "data/trend_overrides.json")))
except Exception:
    OVERRIDES = {}
try:
    from trends import DESIGN_TOKENS, HOT_MIN, OTHER_TEAMS, enrich, FTI_FORMULA
except ImportError:
    DESIGN_TOKENS = {}
    HOT_MIN = 3
    OTHER_TEAMS = set()
    FTI_FORMULA = "round(100 * entity_mentions / peak_mentions_in_window)"
    def enrich(data):
        return data
DATA_DATE = TRENDS.get("generated") or TODAY
enrich(TRENDS)

# Creator collaborations (data/creators.json). A creator gets a dedicated,
# permanently-addressable collection page (e.g. /michigan/joe/) whose every
# internal link carries ?creator=<ID> and whose visitors are tagged with a
# persistent attribution cookie, so the Viralstyle hand-off on ANY product
# page stays attributable to the creator (see the attribution block in
# assets/app.js). Commission terms live in the same record but are INTERNAL:
# commission.customer_facing=false means the rate never renders on public
# pages - customers see the collaboration, not the affiliate math.
try:
    CREATORS = json.load(open(os.path.join(ROOT, "data/creators.json"))).get("creators", {})
except Exception:
    CREATORS = {}


def creator_items(cre):
    """Resolve a creator's curated picks against the live MODEL, in order.

    Unknown / delisted / imageless slugs are skipped silently so a stale
    curation can never crash the build or ship a broken card; the curated
    order is otherwise preserved (that order IS the curation).
    """
    by_slug = {x["slug"]: x for x in MODEL.get(cre.get("collection_key"), [])}
    out, seen = [], set()
    for slug in cre.get("picks", []):
        if slug in by_slug and slug not in seen:
            seen.add(slug)
            out.append(by_slug[slug])
    return out


def creator_by_collection(ckey):
    """First creator whose page belongs to this collection (for cross-links)."""
    for cre in CREATORS.values():
        if cre.get("collection_key") == ckey:
            return cre
    return None


def creator_page_meta(cre):
    """One-line public description of a creator page (feed / llms.txt)."""
    c = COLLECTIONS[cre.get("collection_key", "michigan")]
    return (f"A {c['short']} collection selected with {cre['display_name']} - "
            f"hand-picked designs, printed on demand and shipped worldwide.")


def auto_trend(ckey, slug, blob):
    """Trending decided from live headline volume, with manual override."""
    if slug in OVERRIDES:
        return OVERRIDES[slug]
    ent = None
    for tok in sorted(DESIGN_TOKENS.get(ckey, {}), key=len, reverse=True):
        if tok in blob:
            ent = DESIGN_TOKENS[ckey][tok]
            break
    if not ent:
        return ""
    counts = TRENDS.get("collections", {}).get(ckey, {}).get("entity_mentions", {})
    if ent not in counts:
        return ""
    n = counts[ent]
    if n >= HOT_MIN:
        return "hot"
    if n <= 0:
        return "throwback"
    return ""


def headline_block(ckey, limit=5):
    c = TRENDS.get("collections", {}).get(ckey)
    if not c or not c.get("headlines"):
        return ""
    lis = ""
    for h in c["headlines"][:limit]:
        src = f' <span class="muted">({esc(h["source"])})</span>' if h.get("source") else ""
        lis += (f'<li><a href="{esc(h["url"])}" target="_blank" rel="nofollow noopener">'
                f'{esc(h["title"])}</a>{src}</li>')
    return (f'<div class="newsbox"><h3>Latest {esc(COLLECTIONS[ckey]["short"])} headlines</h3>'
            f'<ul class="news">{lis}</ul>'
            f'<p class="muted" style="font-size:.76rem;margin:10px 0 0">Headlines auto-refreshed '
            f'{esc(DATA_DATE)} from public news feeds. Linked stories belong to their publishers; '
            f'we are not affiliated with them.</p></div>')

_NICE_NAMES = {
    "jj mccarthy": "J.J. McCarthy",
    "ceedee lamb": "CeeDee Lamb",
    "dak prescott": "Dak Prescott",
    "shedeur sanders": "Shedeur Sanders",
    "deshaun watson": "Deshaun Watson",
    "bryce underwood": "Bryce Underwood",
    "kyle whittingham": "Kyle Whittingham",
    "jordan love": "Jordan Love",
    "josh jacobs": "Josh Jacobs",
    "matt lafleur": "Matt LaFleur",
    "micah parsons": "Micah Parsons",
}


def pretty_name(name):
    key = str(name or "").strip().lower()
    if key in _NICE_NAMES:
        return _NICE_NAMES[key]
    return " ".join(w.upper() if w in ("jj", "qb", "qb1") else w.title()
                    for w in key.replace("-", " ").split())


def entity_for_product(ckey, slug, blob):
    for tok in sorted(DESIGN_TOKENS.get(ckey, {}), key=len, reverse=True):
        if tok in blob:
            return DESIGN_TOKENS[ckey][tok]
    return None


def products_for_entity(ckey, entity, limit=3):
    toks = [t for t, e in DESIGN_TOKENS.get(ckey, {}).items() if e == entity]
    if not toks:
        return []
    out = []
    for it in MODEL.get(ckey, []):
        blob = (it["name"] + " " + it["art"]).lower()
        if any(tok in blob for tok in toks):
            out.append(it)
        if len(out) >= limit:
            break
    return out


def fti_rows(ckey=None):
    rows = (TRENDS.get("fan_trend_index") or {}).get("rows") or []
    if ckey:
        rows = [r for r in rows if r.get("collection") == ckey]
    return rows


def fti_block(ckey=None, limit=8, heading=None):
    """Compact Fan Trend Index leaderboard used on collection / season pages."""
    rows = fti_rows(ckey)[:limit]
    if not rows:
        return ""
    peak = (TRENDS.get("fan_trend_index") or {}).get("peak_mentions") or 0
    lis = ""
    for r in rows:
        name = pretty_name(r["name"])
        shop = products_for_entity(r.get("collection") or ckey, r["name"], 1)
        href = shop[0]["url"] if shop else "/fan-trend-index/"
        gap = ' <span class="fti-gap">no design yet</span>' if r.get("gap") else ""
        st = esc(r.get("status") or "")
        lis += (f'<a class="fti-row" href="{href}">'
                f'<span class="fti-name">{esc(name)}</span>'
                f'<span class="fti-bar"><i style="width:{int(r["index"])}%"></i></span>'
                f'<span class="fti-score">{int(r["index"])}</span>'
                f'<span class="fti-meta">{int(r["mentions"])} mentions · {st}{gap}</span>'
                f'</a>')
    title = heading or ("Fan Trend Index" if not ckey else
                        f'{esc(COLLECTIONS[ckey]["short"])} Fan Trend Index')
    return (f'<div class="ftibox"><div class="ftibox-head">'
            f'<h3>{title}</h3>'
            f'<a class="link" href="/fan-trend-index/">Full index &rarr;</a></div>'
            f'<p class="muted" style="font-size:.76rem;margin:0 0 12px">0-100 vs the hottest '
            f'name in the last {(TRENDS.get("fan_trend_index") or {}).get("window_days", 10)}-day '
            f'headline window (peak {peak} mentions). Formula: <code>{esc(FTI_FORMULA)}</code>.</p>'
            f'<div class="fti-board">{lis}</div></div>')


def moments_block(ckey=None, entity=None, limit=5):
    """Headlines that name a tracked player/coach, with shop chips."""
    if ckey:
        moments = (TRENDS.get("collections", {}).get(ckey, {}) or {}).get("moments") or []
    else:
        moments = TRENDS.get("moments") or []
    if entity:
        moments = [m for m in moments if entity in (m.get("entities") or [])]
    moments = moments[:limit]
    if not moments:
        return ""
    lis = ""
    for m in moments:
        who = "".join(
            f'<span class="who">{esc(pretty_name(e))}</span>' for e in (m.get("entities") or []))
        src = f'<span class="muted">{esc(m["source"])}</span>' if m.get("source") else ""
        shop_html = ""
        seen = set()
        for e in (m.get("entities") or [])[:2]:
            if e in seen:
                continue
            seen.add(e)
            picks = products_for_entity(m.get("collection") or ckey, e, 1)
            if picks:
                shop_html += (f'<a class="moment-shop" href="{picks[0]["url"]}">Shop '
                              f'{esc(pretty_name(e))} &rarr;</a>')
            elif e:
                shop_html += '<span class="fti-gap">no design in the locker yet</span>'
        lis += (f'<li class="moment"><div class="moment-who">{who}</div>'
                f'<a href="{esc(m.get("url") or "#")}" target="_blank" rel="nofollow noopener">'
                f'{esc(m.get("title") or "")}</a> {src}{shop_html}</li>')
    label = "Live player moments"
    if entity:
        label = f'Live {esc(pretty_name(entity))} moments'
    elif ckey:
        label = f'Live {esc(COLLECTIONS[ckey]["short"])} player moments'
    return (f'<div class="newsbox momentsbox"><h3>{label}</h3>'
            f'<ul class="moments">{lis}</ul>'
            f'<p class="muted" style="font-size:.76rem;margin:10px 0 0">Moments are public headlines '
            f'that name a player or coach we track. Auto-refreshed {esc(DATA_DATE)}. '
            f'Stories belong to their publishers; we are not affiliated with them.</p></div>')


FTI_STRIP_LIMIT = 4      # homepage strip: one compact row of four names
FTI_COLLECTION_LIMIT = 3  # per-collection panel: at most three rows


def fti_strip(limit=FTI_STRIP_LIMIT):
    """Homepage teaser: a compact strip of the top names on the Fan Trend Index.

    Four entries only - the full leaderboard lives on /fan-trend-index/.
    """
    rows = fti_rows()[:limit]
    if not rows:
        return ""
    cells = ""
    for i, r in enumerate(rows, 1):
        ckey = r.get("collection")
        tv = theme_vars(ckey) if ckey in COLLECTIONS else ""
        shop = products_for_entity(ckey, r["name"], 1)
        href = shop[0]["url"] if shop else "/fan-trend-index/"
        team = esc(COLLECTIONS[ckey]["short"]) if ckey in COLLECTIONS else ""
        cells += (f'<a class="fti-chip" style="{tv}" href="{href}">'
                  f'<b>#{i} · {int(r["index"])}</b>'
                  f'<span>{esc(pretty_name(r["name"]))}</span>'
                  f'<em>{team}</em></a>')
    return (f'<section class="ftisec"><div class="wrap">'
            f'<div class="sechead reveal"><div>'
            f'<span class="eyebrow"><span class="dot"></span> Live · updated {esc(DATA_DATE)}</span>'
            f'<h2>Fan <span class="accentword">Trend Index</span></h2>'
            f'<p>Who the headlines are actually about, scored 0-100 against the hottest name '
            f'in our four fanbases.</p></div>'
            f'<a class="link" href="/fan-trend-index/">Full index &rarr;</a></div>'
            f'<div class="fti-chips">{cells}</div>'
            f'</div></section>')



SIZES = ["S", "M", "L", "XL", "2XL", "3XL"]

# Shopper-facing style filters: the design themes that actually map to a
# purchase intent. "classic" is the catch-all for the untagged majority, so
# it is not offered as a chip - choosing no style chip means all styles.
SHOP_STYLE_CHIPS = [("player", "Player designs"), ("funny", "Funny"),
                    ("retro", "Vintage"), ("family", "Gift")]
URLS = []  # (loc, priority, changefreq)


def esc(s):
    return html.escape(str(s), quote=True)


def write(path, content):
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    content = re.sub(r"\s*(?:&mdash;|—)\s*", " - ", content)
    open(full, "w", encoding="utf-8").write(content)


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-+", "-", s)


# ---------------------------------------------------------------- build model
def build_model():
    items = OrderedDict()
    for ckey in ORDER:
        col = COLLECTIONS[ckey]
        col["key"] = ckey
        lst = []
        for entry in COLS[ckey]["products"]:
            slug = entry["slug"]
            if slug in DELISTED:
                continue
            if slug not in P:
                continue
            p, f = P[slug], FACTS[slug]
            # A crawled product with no images is skipped - there is nothing to show.
            # Keep only images that actually ship in site/ - a failed dl.py pass
            # must never put broken <img> tags (gallery thumbs, colourway swatches,
            # style-chip previews) on a product page. When dl.py later downloads
            # the real swatches they automatically rejoin the gallery on the next
            # build, so this guard is self-healing in the refresh workflow.
            img = p.get("img") or {}
            img = OrderedDict(
                (t, f) for t, f in img.items()
                if isinstance(f, str) and (
                    (f.startswith("/") and os.path.isfile(os.path.join(SITE, f.lstrip("/"))))
                    # A newly added campaign may have valid Viralstyle assets
                    # before the local image downloader has run successfully.
                    # Keep those remote assets as a temporary fallback.
                    or f.startswith("https://assets.viralstyle.com/")
                ))
            if not img:
                continue
            if "front" not in img:
                # front never downloaded but another mockup exists - feature it
                img["front"] = next(iter(img.values()))
            styles = [s for s in p.get("styles", []) if s]
            # Sizes actually offered by the campaign (captured by the scraper /
            # replay); fall back to the store-wide S-3XL range. A campaign that
            # stops at 2XL must not offer 3XL on the product page.
            sizes_avail = [s for s in (p.get("sizes") or SIZES) if s in SIZES] or list(SIZES)
            name = f["name"]
            garment = _c.garment_of(f, name, styles)
            colours = max(1, sum(1 for k in img if k.startswith("c")))
            price = float(p["price_usd"])
            url = f"/shop/{slug}/"
            gal = [img["front"]] + ([img["back"]] if "back" in img else [])
            gal += [v for k, v in img.items() if k.startswith("c")]
            blob = (name + " " + f["art"]).lower()
            trend = auto_trend(ckey, slug, blob)
            lst.append(dict(trend=trend,
                slug=slug, name=name, art=f["art"], theme=f.get("theme", "classic"),
                garment=garment, price=price, colours=colours,
                styles=styles, sizes_avail=sizes_avail, url=url, gallery=gal, front=img["front"],
                back=img.get("back", img["front"]),
                buy=p["url"], kw=_l.keywords(f, col, garment, name), col=ckey,
                features=p.get("features") or "",
            ))
        items[ckey] = lst
    return items


MODEL = build_model()
ALL = [x for v in MODEL.values() for x in v]

# Homepage per-team section order ONLY: the collection that kicks off next
# (NEXT_GAME, computed at import) goes first, original ORDER breaks ties.
# Everything else - hero slider, "Shop By Team" grid, schema, nav, footer,
# /collections/ index, sitemap, data files, product cross-links - keeps the
# fixed ORDER above untouched.
HOMEPAGE_ORDER = sorted(ORDER, key=lambda k: (NEXT_GAME.get(k) or "9999", ORDER.index(k)))


# ---------------------------------------------------------------- chrome
def theme_vars(ckey):
    """Collection accent tokens with shared CTA colors.

    Returned as a bare `--x:y;...` string so the same tokens can be dropped
    either at :root (a page that belongs to exactly one collection) or inline
    on a single element (a shared page listing several collections). Team
    identity stays in the accent tokens; CTA colors are the same everywhere.
    """
    c = COLLECTIONS[ckey]
    return (f"--ca:{c['accent']};--ca-ink:{c['accent_ink']};"
            f"--ca-tint:{c['accent_tint']};--ca-2:{c['accent2']};"
            f"--btn:{CTA};--btn-h:{CTA_HOVER};--accent:{c['accent']}")


def head(title, desc, path, image=None, schema=None, keywords=None, col=None,
         noindex=False, body_attrs=""):
    canon = abs_url(path)
    # The 404 page is served (with a 200 on GitHub Pages) for every mistyped or
    # stale URL under the domain, so an "index,follow" 404 invites Google to
    # index unlimited not-found URLs as duplicates of one another. It is the
    # one page that must stay out of the index.
    robots = ("noindex,follow" if noindex
              else "index,follow,max-image-preview:large,max-snippet:-1")
    img = abs_url(image or "/img/hero-home.jpg?v=4")
    kw = f'<meta name="keywords" content="{esc(", ".join(keywords[:14]))}">' if keywords else ""
    # A page that belongs to one collection wears that collection's tokens at
    # :root, so its chips and rules are team-coloured while CTAs stay teal.
    # Shared pages keep neutral accents and colour individual elements.
    acc = f"<style>:root{{{theme_vars(col)}}}</style>" if col else ""

    rendered_title = html.unescape(title)
    if len(rendered_title) > 60 and title.endswith(f" | {BRAND}"):
        candidate = title[:-len(f" | {BRAND}")]
        if len(html.unescape(candidate)) <= 60:
            title = candidate

    schemas = list(schema or [])
    has_org = any(isinstance(s, dict) and s.get("@type") == "Organization" for s in schemas)
    has_site = any(isinstance(s, dict) and s.get("@type") == "WebSite" for s in schemas)
    if not has_org:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": BRAND,
            "url": DOMAIN,
            "logo": DOMAIN + "/img/favicon.svg",
            "sameAs": [u for _, u in SOCIALS],
        })
    if not has_site:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": BRAND,
            "url": DOMAIN,
            "potentialAction": {
                "@type": "SearchAction",
                # Real endpoint: the /search/ catalogue page pre-applies ?q=
                # (see page_search + the app.js filter). Every page of the
                # site carries this, so the advertised search must work
                # sitewide and never 404.
                "target": DOMAIN + "/search/?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        })

    sc = ""
    for s in schemas:
        sc += '<script type="application/ld+json">' + json.dumps(s, separators=(",", ":")) + "</script>"
    # data-root: the site-root prefix for THIS page's depth ("./", "../",
    # "../../"). The global search dropdown and /search/ deep links are built
    # at runtime from the JSON index with root-absolute paths, so the browser
    # needs the same prefix relativise() uses for static links. This is what
    # keeps search working on a GitHub Pages project URL, not just the custom
    # domain.
    if path.endswith(".html"):
        root_prefix = "./"
    else:
        depth = len([seg for seg in path.split("/") if seg])
        root_prefix = "./" if depth == 0 else "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{kw}
<link rel="canonical" href="{canon}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="{'product' if path.startswith('/shop/') else 'website'}">
<meta property="og:site_name" content="{esc(BRAND)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{img}">
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/style.css?v={STYLE_VERSION}">
<script>document.documentElement.className+=" js"</script>
{acc}
{sc}
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-5RHGJSLZNG"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-5RHGJSLZNG');
</script>
</head>
<body data-root="{root_prefix}"{body_attrs}>
"""


def season_promo():
    """Sitewide promo clause, derived from SEASON (never a hardcoded date).

    The hardcoded "2026 season kicks off Sept 9" sat on every page while the
    homepage put Michigan first for a Sept 5 game, so the banner contradicted
    the page underneath it. This reads the earliest 2026 opener instead: once
    that date has arrived the season is live, so the line can never go stale
    again and never needs a manual edit per fixture.
    """
    first = min(SEASON[k]["kickoff"][:10] for k in ORDER)
    if first <= TODAY:
        return "2026 season is live"
    d = datetime.date.fromisoformat(first)
    month = "Sept" if d.month == 9 else d.strftime("%b")   # house style: "Sept 5"
    return f"2026 season kicks off {month} {d.day}"


def header(active=""):
    """Site header, shared by every page.

    Two rows: the logo row (logo + search), then a FULL-WIDTH menu bar that
    stays visible at every viewport. The bar is the eight shopping
    destinations - All Collections, the four teams, Trending (/drops/, the
    store-wide headline-scored entry point for visitors with no team
    preference), Guides and Shop The Locker - centred, and it scrolls
    sideways when they no longer fit instead of collapsing into a hamburger.
    Phones previously buried the store's main entrances behind a burger tap;
    the bar keeps them one glance away. Secondary destinations (Home, 2026
    Season Hub, Fan Trend Index, Buying Guides, Size Guide, Shipping, About)
    live in the footer, so removing the toggle hides nothing.

    "Shop The Locker" anchors the homepage's full-catalogue rail
    (#shop-the-locker); from any other page it lands on the homepage and
    scrolls down to that rail.

    There is deliberately NO account or cart control. Checkout happens on the
    fulfilment partner, so an account icon led to an explainer popover and a
    cart icon to a favourites hint - two pieces of storefront furniture that
    promised state this site does not own, in the two slots a visitor's eye
    goes to first. The header's only job is product discovery.

    Still the only sane way to make a nav change: edit it here, never in the
    built site/*.html files, because the daily refresh workflow re-runs this
    generator.
    """
    links = "".join(
        f'<a href="/{COLLECTIONS[k]["slug"]}/"{" aria-current=page" if active == k else ""}>{COLLECTIONS[k]["short"]}</a>'
        for k in ORDER)
    search_ico = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="11" cy="11" r="6.2"/><path d="M20 20l-4.3-4.3"/></svg>'
    return f"""\
<a class="skip" href="#main">Skip to content</a>
<div class="promo">{season_promo()} &middot; Printed on demand in the USA &middot; Worldwide shipping</div>
<header>
 <div class="wrap nav">
  <a class="logo" href="/"><span class="mark">GL</span><span class="wordmark">{esc(BRAND)}</span></a>
  <div class="navtools">
   <span class="navsearch" role="search">
    <input class="gsearch" type="search" placeholder="Search designs..." aria-label="Search all designs" autocomplete="off">
    <span class="gs-ico" aria-hidden="true">{search_ico}</span>
   </span>
   <button class="searchbtn" aria-label="Search designs"
    onclick="var m=document.getElementById('ms');m.classList.toggle('open');var i=m.querySelector('input');if(m.classList.contains('open')&&i)i.focus()">{search_ico}</button>
  </div>
 </div>
 <nav class="menubar" aria-label="Shop">
  <div class="mb-track">
   <a href="/collections/">All Collections</a>
   {links}
   <a href="/drops/">Trending</a>
   <a href="/guides/">Guides</a>
   <a href="/#shop-the-locker">Shop The Locker</a>
  </div>
 </nav>
 <div class="mobsearch" id="ms"><span class="gs"><input class="gsearch" type="search"
  placeholder="Search all {len(ALL)} designs..." aria-label="Search all designs" autocomplete="off"></span></div>
</header>"""



def countdown_bar(ckey=None):
    if ckey:
        se = SEASON[ckey]
        label = COLLECTIONS[ckey]["short"] + " kickoff"
    else:
        se = SEASON["cleveland-browns"]
        label = "NFL Week 1 kickoff"
    return f"""<div class="cdbar"><div class="wrap in">
 <span class="lbl">{label} &middot; {se['opener']}</span>
 <span class="cd" data-deadline="{se['kickoff']}">
  <b id="cd-d">--<span>Days</span></b><b id="cd-h">--<span>Hrs</span></b>
  <b id="cd-m">--<span>Min</span></b><b id="cd-s">--<span>Sec</span></b>
 </span>
 <span class="lbl">Kickoff information only · arrival before a specific game is not guaranteed</span>
</div></div>"""


def audience_gender(it):
    """schema.org suggestedGender for a design, read from its campaign styles.

    Viralstyle campaigns list every cut they are sold in ("Women's V-Neck",
    "Mens V-Neck", ...). A design offered in both men's and women's cuts is
    unisex; one offered only in women's cuts is female. Mugs, beanies and
    phone cases have no cut, so they are unisex too.
    """
    styles = " ".join(it.get("styles") or []).lower()
    women = "women" in styles or "ladies" in styles
    men = re.search(r"\bmen'?s\b|unisex", styles) is not None
    if women and not men:
        return "female"
    return "unisex"



# Evergreen ticker terms, keyed by collection so a team page never scrolls
# another team's slogans. The store-wide terms are appended on every page.
TEAM_TICKER_TERMS = {
    "cleveland-browns": [("Shedeur Sanders fan shirts", 1), ("Dawg Pound apparel", 0),
                         ("Here We Go Brownies", 0), ("Cleveland skyline tees", 0)],
    "green-bay-packers": [("Go Pack Go tees", 0), ("Jordan Love 10 shirts", 1),
                          ("Cheesehead Nation", 0), ("Lambeau tribute crewnecks", 0)],
    "dallas-cowboys": [("Dallas vintage tees", 0), ("Texas pride shirts", 0),
                       ("Doomsday Defense tees", 1), ("Star-city lettering", 0)],
    "michigan": [("Michigan vs Everybody", 0), ("Bryce Underwood era", 1),
                 ("Go Blue crewnecks", 0), ("Maize and navy tees", 0)],
}
STORE_TICKER_TERMS = [
    ("Week 1 game day fits", 1), ("Sizes S-3XL", 0),
    ("Printed on demand", 0), ("Worldwide shipping", 0),
]
# All-team list for shared pages (season hub): the teams' terms interleaved
# round-robin so every collection is represented before the 16-term cap.
TICKER_TERMS = [t for row in zip(*(TEAM_TICKER_TERMS[k] for k in ORDER)) for t in row] \
    + STORE_TICKER_TERMS


# Headline words that are never a shirt anyone searches for. The live
# top_terms feed is raw word frequency from the news pipeline, so without
# this list the Cleveland ticker scrolled "Roster Cleveland shirts" and the
# Michigan one "Western Michigan shirts" - an opponent's name on our own
# team page. Generic football vocabulary + newsroom filler.
TICKER_STOPWORDS = set("""
roster practice squad depth chart trade rumors rumor injury injuries report
update updates news preview recap watch stream free live opener game games
season week schedule odds pick picks prediction predictions score scores
final highlights highlight controversial second first football team players
player coach quarterback offense defense kickoff sunday saturday monday
thursday friday tonight today yesterday tomorrow week1 vs versus against
""".split())
# Multi-word opponent / other-programme names that OTHER_TEAMS (single words)
# cannot catch, e.g. Michigan's opener "Western Michigan".
TICKER_OPPONENTS = {
    "michigan": {"western", "central", "eastern", "ohio", "state", "buckeyes", "spartans",
                 "irish", "nebraska", "wisconsin", "penn", "usc", "oregon"},
    "cleveland-browns": {"jacksonville"},
    "green-bay-packers": {"minnesota"},
    "dallas-cowboys": {"giants", "york"},
}


def ticker_live_terms(ckey, limit=3):
    """Team-safe live ticker terms for one collection.

    A live term only qualifies if it is a tracked entity's surname or a
    non-generic word that is not another team, not an opponent, not a
    stopword and not part of the collection's own name. Everything that
    survives is rendered as "<Word> <Team> shirts" - never another team's
    name on this team's page.
    """
    c = COLLECTIONS[ckey]
    own = set(re.findall(r"[a-z]+", f"{c['short']} {c['team']} {c['name']} {c['city']}".lower()))
    blocked = OTHER_TEAMS | TICKER_STOPWORDS | TICKER_OPPONENTS.get(ckey, set()) | own
    mentions = (TRENDS.get("collections", {}).get(ckey, {}) or {}).get("entity_mentions") or {}
    tracked_words = {w for e, n in mentions.items() if n > 0 for w in e.split()}
    out = []
    for t in (TRENDS.get("collections", {}).get(ckey, {}) or {}).get("top_terms", []):
        w = t.lower().strip()
        if len(w) <= 3 or not w.isalpha() or w in blocked:
            continue
        # generic words only get through when they are a tracked player/coach
        if w not in tracked_words and w not in {x for row in TEAM_TICKER_TERMS[ckey]
                                                for x in row[0].lower().split()}:
            continue
        term = f"{pretty_name(w)} {c['short']} shirts"
        if term not in [x for x, _ in out]:
            out.append((term, 1))
        if len(out) >= limit:
            break
    return out


def ticker(ckey=None):
    """Moving keyword bar. With a collection key it is strictly that team's
    terms (team-safe live news terms + that team's evergreen slogans + store
    terms); shared pages interleave all four teams."""
    live = []
    for k in ([ckey] if ckey else ORDER):
        live += ticker_live_terms(k)
    evergreen = (TEAM_TICKER_TERMS[ckey] + STORE_TICKER_TERMS) if ckey else TICKER_TERMS
    terms = (live + list(evergreen))[:16]
    run = "".join(f'<i class="{"hot" if h else ""}">{esc(t)}</i>' for t, h in terms)
    run_dup = run.replace('<i ', '<i aria-hidden="true" ')
    return f'<div class="ticker"><div class="track">{run}{run_dup}</div></div>'


def newsticker():
    """Moving bar of LIVE news headlines (not product cards) pulled from trends.json."""
    items = []
    for k in ORDER:
        short = COLLECTIONS[k]["short"]
        for h in TRENDS.get("collections", {}).get(k, {}).get("headlines", [])[:3]:
            t = h.get("title", "").strip()
            if len(t) > 3:
                items.append((f"[{short}] {t}", h.get("url", "")))
    if not items:
        return ""
    run = "".join(
        f'<a href="{esc(u)}" target="_blank" rel="nofollow noopener"><i class="hot">{esc(t)}</i></a>'
        for t, u in items) or ""
    run2 = run.replace('<a href', '<a aria-hidden="true" tabindex="-1" href')
    return f'<div class="newsticker"><div class="track">{run}{run2}</div></div>'


def season_section():
    """Homepage 2026 Season block: the editorial beat, placed AFTER shopping.

    Everything on it is read from SEASON (src/collections_data.py) - opener,
    kickoff timestamp and the one-line status per team - so nothing here can
    drift into invented scores, stats or news. The headline itself is derived:
    once the earliest opener has passed, the season is live.
    """
    first = min(SEASON[k]["kickoff"][:10] for k in ORDER)
    live = first <= TODAY
    title = ("The Season Is <span class=\"accentword\">Live.</span>" if live
             else "The Season Is <span class=\"accentword\">Almost Here.</span>")
    rows = ""
    for k in ORDER:
        c, se = COLLECTIONS[k], SEASON[k]
        rows += f"""<a class="wk reveal" style="{theme_vars(k)}" href="/{c['slug']}/">
 <b class="wk-name">{esc(c['short'])}</b>
 <span class="wk-game">{se['opener']}</span>
 <span class="wk-note">{esc(se['headline'])}</span>
 <span class="wk-go">Shop {esc(c['short'])} &rarr;</span>
</a>"""
    return f"""<section class="wksec" id="season"><div class="wrap">
 <div class="wkhead reveal">
  <span class="eyebrow"><span class="dot"></span> 2026 season</span>
  <h2>{title}</h2>
  <p>Current football culture, fan energy and designs for game day. Here is how the openers
  look for every team we cover. Delivery timing is an estimate, and arrival before a specific
  game is not guaranteed.</p>
 </div>
</div>
{countdown_bar()}
<div class="wrap">
 <div class="wkgrid">{rows}</div>
 <div class="wkcta"><a class="btn" href="/2026-season/">Explore The Season &rarr;</a>
  <a class="link" href="/drops/">Trending drops &rarr;</a></div>
</div></section>"""


def team_portrait(k, size=96, cls="tportrait"):
    """Circular team thumbnail showing the team's logo mark.

    The portrait is the official-style logo (helmet / G / star / block M)
    masked to a circle with a subtle ring in the team's primary colour
    (drawn with the --ca token, so accents stay data-driven). The image is
    rendered with object-fit:contain so the mark is never cropped.
    """
    c = COLLECTIONS[k]
    return (f'<span class="{cls}"><img src="{c["logo"]}" alt="" loading="lazy" '
            f'decoding="async" width="{size}" height="{size}"></span>')


def team_nav_card(k, cls="teamnav reveal"):
    """Homepage 'Shop By Team' entry: rounded horizontal card, circle thumb,
    name, live design count and an arrow."""
    c = COLLECTIONS[k]
    return (f'<a class="{cls}" style="{theme_vars(k)}" href="/{c["slug"]}/">'
            f'{team_portrait(k, 72)}'
            f'<span class="tn-body"><span class="cnt">{len(MODEL[k])} designs</span>'
            f'<b class="tn-name">{esc(c["name"])}</b>'
            f'<span class="tn-sub">{esc(c["city"])} &middot; {esc(c["chant"])}</span></span>'
            f'<span class="go" aria-hidden="true">&rarr;</span></a>')


def team_circle_card(k):
    """/collections/ entry: circular portrait with a team-colour outline, the
    collection name, the live design count and an arrow."""
    c = COLLECTIONS[k]
    return (f'<a class="teamcircle reveal" style="{theme_vars(k)}" href="/{c["slug"]}/">'
            f'{team_portrait(k, 160)}'
            f'<b class="tc-name">{esc(c["name"])}</b>'
            f'<span class="tc-count">{len(MODEL[k])} designs</span>'
            f'<span class="tc-go">Shop {esc(c["short"])} <span aria-hidden="true">&rarr;</span></span></a>')


def team_section(k, limit=4, exclude=()):
    """One per-team product block: heading, blurb, four cards, collection CTA.

    Deeper browsing for a visitor who already knows their side, so it sits
    below the store-wide product surfaces. The card count is deliberately
    small (4) - this is a door into the collection, not the collection.
    """
    c = COLLECTIONS[k]
    # Prefer designs this page has not shown yet, then top up from the front
    # of the collection so the block is always full.
    picks = [x for x in MODEL[k] if x["slug"] not in exclude][:limit]
    have = {x["slug"] for x in picks}
    if len(picks) < limit:
        picks += [x for x in MODEL[k] if x["slug"] not in have][:limit - len(picks)]
    tcards = "".join(product_card(i) for i in picks)
    return f"""<section class="teamsec" style="{theme_vars(k)}"><div class="wrap">
 <div class="sechead reveal">
  <div><span class="eyebrow"><span class="dot"></span> {len(MODEL[k])} designs</span>
   <h2><span class="accentword">{esc(c['short'])}</span> Collection</h2>
   <p>{esc(c['banner'][:150])}</p></div>
  <a class="link" href="/{c['slug']}/">Explore {esc(c['short'])} &rarr;</a>
 </div>
 <div class="pgrid four">{tcards}</div>
</div></section>"""


def trust():
    return """<div class="trust">
 <div><b>Worldwide Shipping</b>Tracked to your door</div>
 <div><b>S &ndash; 3XL</b>Unisex &amp; women's cuts</div>
 <div><b>Premium Fan Art</b>Original designs</div>
 <div><b>Checkout on Viralstyle</b>Card &amp; PayPal</div>
</div>"""


def footer(popup=True):
    """Sitewide footer: Shop / Help / Brand / Compliance, then the fan-made
    disclaimer. The columns mirror the header's shopping destinations so the
    bottom of any page is a second, complete route back into the catalogue.

    `popup` renders the once-per-session custom-design offer. The homepage
    passes False: it already carries the full custom-design section, and a
    floating card there would fight the mobile shopping bar for the same
    corner of a phone screen.
    """
    cl = "".join(f'<a href="/{COLLECTIONS[k]["slug"]}/">{COLLECTIONS[k]["short"]}</a>' for k in ORDER)
    # Creator collab pages are a permanent Shop destination (one link each,
    # e.g. Joe's locker at /michigan/joe/).
    cl_creators = "".join(
        f'<a href="/{v["page_slug"]}/">{esc(v["page_name"])}</a>' for v in CREATORS.values())
    soc = "".join(f'<a href="{u}{SOCIAL_UTM}" target="_blank" rel="noopener">{esc(n)}</a>' for n, u in SOCIALS)
    cspop = """
<div class="cs-pop" id="csPop" role="dialog" aria-modal="true" aria-label="Custom design offer" hidden>
 <button class="cs-pop-close" id="csPopClose" aria-label="Close">&#10005;</button>
 <img src="/img/custom-tee-pop.jpg" alt="Custom t-shirt design" loading="lazy" width="780" height="1302">
 <div class="cs-pop-body">
  <span class="cs-pop-kicker">Made to order</span>
  <h3>Want a <span class="accentword">Custom Design</span>?</h3>
  <p>Your nickname, catchphrase or team slogan - printed on tees, hoodies, mugs &amp; more. No minimum order.</p>
  <button class="btn lg" id="csPopGo">Tell Us Your Idea &rarr;</button>
 </div>
</div>""" if popup else ""
    return f"""
<footer>
 <div class="wrap">
  <div class="fgrid">
   <div>
    <div class="logo" style="margin-bottom:12px"><span class="mark">GL</span> {esc(BRAND)}</div>
    <p>{esc(CFG['tagline'])}. Independent, fan-made football graphics printed on demand and
    shipped worldwide. {len(ALL)} designs across {len(ORDER)} collections.</p>
   </div>
   <div><h2>Shop</h2><a href="/collections/">All Collections</a>{cl}{cl_creators}
    <a href="/drops/">Trending</a><a href="/search/">All Designs</a></div>
   <div><h2>Help</h2><a href="/faq/">FAQ</a><a href="/shipping/">Shipping</a>
    <a href="/shipping/">Returns</a><a href="/size-guide/">Size Guide</a>
    <a href="/contact/">Contact</a></div>
   <div><h2>Brand</h2><a href="/about/">About</a><a href="/#custom-design">Custom Design</a>
    <a href="/guides/">Buying Guides</a><a href="/2026-season/">2026 Season</a>
    <a href="/fan-trend-index/">Fan Trend Index</a></div>
   <div><h2>Compliance</h2><a href="/trademark-notice/">Trademark Notice</a>
    <a href="/privacy/">Privacy Policy</a>
    <h2 style="margin-top:16px">Follow</h2>{soc}</div>
  </div>
  <div class="disclaim"><strong>Independent fan store.</strong> {esc(BRAND)} is not affiliated with,
   endorsed by, sponsored by or licensed by the National Football League, any NFL club, the NCAA,
   any university or any player. All team names, city names and player names are used descriptively
   to identify the fan community a design is made for. All trademarks are the property of their
   respective owners. Artwork is original, fan-created work.</div>
  <div class="legal">&copy; {datetime.date.today().year} {esc(BRAND)}. All rights reserved.
   Prices shown in USD and set by the fulfilment partner; final price, colour and size options are
   confirmed at checkout.</div>
 </div>
</footer>{cspop}
<button class="totop" id="totop" aria-label="Back to top">&uarr;</button>
<div class="toast" id="favMsg" aria-live="polite" hidden></div>
<script src="/assets/app.js" defer></script>
</body></html>"""


def crumbs(pairs, current=None):
    out, sch = [], []
    for i, (label, href) in enumerate(pairs):
        if href:
            out.append(f'<a href="{href}">{esc(label)}</a>')
        else:
            out.append(f"<span style='opacity:1;margin:0'>{esc(label)}</span>")
        loc = href if href else (current or "/")
        sch.append({"@type": "ListItem", "position": i + 1, "name": label,
                    "item": DOMAIN + loc})
    return ('<div class="wrap"><nav class="crumbs" aria-label="Breadcrumb">'
            + "<span>/</span>".join(out) + "</nav></div>",
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": sch})


def card(it, eager=False):
    lazy = "" if eager else ' loading="lazy" decoding="async"'
    tag = {"player": "Player", "funny": "Funny", "retro": "Vintage", "playoff": "Playoff",
           "halloween": "All-Over", "family": "Gift", "city": "City", "classic": "Classic"}.get(it["theme"], "")
    cls = "tagpill"
    if it.get("trend") == "hot":
        tag, cls = "Trending", "tagpill hot"
    tv = theme_vars(it["col"])
    # data-type / data-team / data-theme power the /search/ catalogue
    # filters (app.js) - the team pages read the same attributes and ignore
    # the dimensions they do not offer. The .qv button is a sibling of the
    # card link (never nested inside it - an interactive control inside an
    # <a> is invalid HTML) and opens the shared quick-view modal. .fav is a
    # device-side favourite toggle (localStorage, no backend).
    return f"""<article class="card reveal" data-slug="{it['slug']}" data-type="{esc(it['garment'])}" data-team="{it['col']}" data-theme="{it['theme']}" style="{tv}">
 <a href="{it['url']}" aria-label="{esc(it['name'])}">
  <div class="ph"><span class="{cls}">{tag}</span><span class="glow"></span><span class="sweep"></span>
   <img src="{it['front']}" alt="{esc(it['name'])} - {esc(it['art'][:70])}" width="530" height="630"{lazy}>
   <img class="alt" src="{it['back']}" alt="{esc(it['name'])} back view" width="530" height="630" loading="lazy" decoding="async">
  </div>
  <div class="body">
   <span class="meta">{esc(it['garment'])}</span>
   <h3>{esc(it['name'])}</h3>
   <span class="price">${it['price']:.2f}</span>
  </div>
 </a>
 <button class="qv" type="button" aria-label="Quick view {esc(it['name'])}">Quick view</button>
 <button class="fav" type="button" aria-label="Favourite {esc(it['name'])}" aria-pressed="false" data-slug="{it['slug']}"><svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.4 4.8 13.2a4.6 4.6 0 1 1 6.5-6.5l.7.7.7-.7a4.6 4.6 0 1 1 6.5 6.5Z"/></svg></button></article>"""


def product_card(it, eager=False):
    """Homepage product tile - the reusable ProductCard.

    One <a>, so the whole tile is the link (image, team + garment, name,
    price and a "View design" affordance). Nothing else: no quick-view
    chrome, no favourite heart, no sale badge, no countdown, no "only 3
    left". The catalogue pages keep the richer card() because they need the
    filter attributes and quick view; the homepage's only job is to move a
    visitor to a product page in one tap.

    Images are normalised by CSS (square box, object-fit:contain, white
    background) so a mug and a hoodie mockup occupy exactly the same area -
    the intrinsic width/height attributes stay on the tag so the grid never
    shifts while the artwork loads.
    """
    lazy = "" if eager else ' loading="lazy" decoding="async"'
    hot = '<span class="pc-hot">Trending</span>' if it.get("trend") == "hot" else ""
    c = COLLECTIONS[it["col"]]
    return (f'<a class="pcard reveal" href="{it["url"]}" style="{theme_vars(it["col"])}" '
            f'data-slug="{it["slug"]}">'
            f'<span class="pc-ph">{hot}'
            f'<img src="{it["front"]}" alt="{esc(it["name"])} - {esc(it["art"][:70])}" '
            f'width="530" height="630"{lazy}></span>'
            f'<span class="pc-body">'
            f'<span class="pc-meta">{esc(c["short"])} &middot; {esc(it["garment"])}</span>'
            f'<h3 class="pc-name">{esc(it["name"])}</h3>'
            f'<span class="pc-foot"><span class="pc-price">${it["price"]:.2f}</span>'
            f'<span class="pc-go">View design <i aria-hidden="true">&rarr;</i></span></span>'
            f'</span></a>')


def rail_nav(rail_id):
    """Desktop-only scroll affordance for a ProductRail (touch just swipes)."""
    return (f'<span class="rail-nav" data-rail="{rail_id}">'
            f'<button class="rn" type="button" data-dir="-1" aria-controls="{rail_id}"'
            f' aria-label="Scroll products left"><span aria-hidden="true">&larr;</span></button>'
            f'<button class="rn" type="button" data-dir="1" aria-controls="{rail_id}"'
            f' aria-label="Scroll products right"><span aria-hidden="true">&rarr;</span></button></span>')


def product_rail(items, rail_id, cta_href, cta_label):
    """Reusable ProductRail: a horizontal, scroll-snapping row of ProductCards
    that ends in a "view all" tile, so the rail is never a dead end.

    Desktop shows four tiles with the fifth peeking (the affordance that says
    "this scrolls"); phones swipe it natively instead of stacking a dozen
    cards vertically."""
    tiles = "".join(product_card(it, eager=(n < 2)) for n, it in enumerate(items))
    end = (f'<a class="rail-end" href="{cta_href}"><span class="re-lab">{cta_label}</span>'
           f'<span class="re-go" aria-hidden="true">&rarr;</span></a>')
    return f'<div class="prail" id="{rail_id}">{tiles}{end}</div>'


def locker_picks(limit=10):
    """Products for the "Shop The Locker" rail: a round-robin across the four
    collections (next kickoff first), each lane led by its headline-hot
    designs. Every fanbase is represented in the first four tiles, and no
    slug is hard-coded, so a re-crawl re-balances the rail automatically."""
    lanes = []
    for k in HOMEPAGE_ORDER:
        hot = [x for x in MODEL[k] if x.get("trend") == "hot"]
        lanes.append(hot + [x for x in MODEL[k] if x.get("trend") != "hot"])
    picks, i = [], 0
    while len(picks) < limit and any(len(lane) > i for lane in lanes):
        for lane in lanes:
            if i < len(lane) and len(picks) < limit:
                picks.append(lane[i])
        i += 1
    return picks


def shop_the_locker(limit=10, picks=None):
    """The first product surface on the homepage, directly under Shop By Team.

    A visitor who has not picked a side still meets real merchandise inside
    the second viewport - price, name and a link into the product page -
    instead of another editorial band."""
    picks = locker_picks(limit) if picks is None else picks
    if len(picks) < 4:
        return ""
    return f"""<section class="lockersec" id="shop-the-locker"><div class="wrap">
 <div class="sechead reveal"><div>
  <span class="eyebrow"><span class="dot"></span> In the locker &middot; {len(ALL)} designs</span>
  <h2>Shop The <span class="accentword">Locker</span></h2>
  <p>Fan-made gear worth wearing on game day.</p></div>
  <span class="sechead-tools">{rail_nav('lockerRail')}
   <a class="link" href="/search/">All {len(ALL)} designs &rarr;</a></span></div>
 {product_rail(picks, 'lockerRail', '/collections/', 'View all designs')}
</div></section>"""


def trending_now(limit=8, exclude=()):
    """Store-wide 'Trending Now' grid.

    Honesty matters here: there is no sales feed (checkout happens on the
    fulfilment partner), so a 'best seller' label would be a fake badge. The
    grid shows the designs the live Fan Trend Index is actually scoring hot
    in the last 10 days of public team headlines, with the rest of the
    catalogue filling any gap so it never looks thin. Re-scored every build.

    `exclude` holds the slugs a previous section already showed, so the
    homepage spends its cards on as much of the catalogue as it can instead
    of printing the same four designs three times.
    """
    fresh = [x for x in ALL if x["slug"] not in exclude]
    picks = [x for x in fresh if x.get("trend") == "hot"][:limit]
    have = {x["slug"] for x in picks}
    if len(picks) < limit:
        picks += [x for x in fresh if x["slug"] not in have][:limit - len(picks)]
    have = {x["slug"] for x in picks}
    if len(picks) < limit:   # tiny catalogue: repeats beat an empty shelf
        picks += [x for x in ALL if x["slug"] not in have][:limit - len(picks)]
    if len(picks) < 4:
        return ""
    tiles = "".join(product_card(i) for i in picks)
    return f"""<section class="trendsec" id="trending"><div class="wrap">
 <div class="sechead reveal"><div><span class="eyebrow"><span class="dot"></span> Fresh from the headlines</span>
  <h2>Trending <span class="accentword">Now</span></h2>
  <p>The designs this week's team headlines are pushing - re-scored daily from public news.</p></div>
  <a class="link" href="/drops/">All live drops &rarr;</a></div>
 <div class="pgrid four">{tiles}</div>
 <div class="secfoot"><a class="btn" href="/search/">View All Designs &rarr;</a>
  <a class="link" href="/collections/">Shop by team &rarr;</a></div>
</div></section>"""


def team_card(k):
    """Homepage 'Shop By Team' entry - the reusable TeamCard.

    A single <a>: the whole card is the link, the arrow is only an
    affordance. Cinematic team artwork (a product-led crop of the team's
    banner, see src/crop_art.py), the team name in display type, the fan
    phrase, the live design count and an arrow CTA. The four cards share one
    composition, one type treatment and one lighting philosophy - only the
    colour tokens and the artwork change."""
    c = COLLECTIONS[k]
    art = TEAM_CARD_ART[k]
    return (f'<a class="teamcard reveal" style="{theme_vars(k)}" href="/{c["slug"]}/">'
            f'<span class="tc-ph"><img src="{art}" alt="{esc(c["short"])} fan gear - hoodie, '
            f'beanie and helmet in team colours" loading="lazy" decoding="async" '
            f'width="620" height="695">'
            f'<span class="tc-shade" aria-hidden="true"></span>'
            f'<span class="tc-over"><b class="tc-name">{esc(c["short"])}</b>'
            f'<span class="tc-phrase">{esc(c["phrase"])}</span></span></span>'
            f'<span class="tc-body"><span class="tc-count">{len(MODEL[k])} designs</span>'
            f'<span class="tc-go">Shop {esc(c["short"])} <i aria-hidden="true">&rarr;</i></span>'
            f'</span></a>')


def shop_by_team():
    """Section 1 of the funnel after the hero: which team are you?"""
    cards = "".join(team_card(k) for k in ORDER)
    return f"""<section class="teamdeck-sec" id="shop-by-team"><div class="wrap">
 <div class="sechead reveal"><div>
  <span class="eyebrow"><span class="dot"></span> Four teams &middot; four fanbases</span>
  <h2>Shop By <span class="accentword">Team</span></h2>
  <p>Four dedicated collections, each with its own artwork language, colour palette and fan
  slang. Pick your side.</p></div>
  <a class="link" href="/collections/">All collections &rarr;</a></div>
 <div class="teamdeck-grid">{cards}</div>
</div></section>"""


def shop_nav():
    """Compact shopping navigation for a visitor who is already deep in the page.

    Two renderings of the same idea, each shown only where it belongs:
      * desktop - a slim sticky strip that parks under the header once the
        hero has scrolled away, so the team collections are one click away
        from anywhere on the page;
      * phones - a fixed bottom bar (Shop by team / Trending / All designs)
        that appears after the hero and hides again over the footer, where
        the same links are already on screen. Safe-area padding keeps it
        clear of the iOS home indicator.
    """
    links = "".join(f'<a href="/{COLLECTIONS[k]["slug"]}/">{esc(COLLECTIONS[k]["short"])}</a>'
                    for k in ORDER)
    return f"""<div class="shopbar" id="shopbar">
 <div class="wrap sb-in">
  <span class="sb-lab">Shop</span>
  <nav class="sb-links" aria-label="Shop collections">{links}
   <a href="/drops/">Trending</a></nav>
  <a class="sb-all" href="/search/">All {len(ALL)} designs <span aria-hidden="true">&rarr;</span></a>
 </div>
</div>
<nav class="mobshop" id="mobshop" aria-label="Shop shortcuts" hidden>
 <a href="#shop-by-team">Shop by team</a>
 <a href="#trending">Trending</a>
 <a href="/search/">All designs</a>
</nav>"""


# Homepage hero. Two-part editorial composition matching the storefront
# reference art: a textured white copy block on the left ("FOOTBALL. FANS.
# CULTURE." / "GEAR UP." / brush "KEEP IT.") and, on the right, the cinematic
# locker-room panel from the same artwork - hoodies, helmets, a football and
# the brush strokes, no people. The headline is real HTML text (crawlable,
# responsive, translatable), never a picture of type, and everything that can
# change - catalogue size, sizes, delivery - is rendered from the live model.
HERO_ART = "/img/hero-locker.jpg"
HERO_ART_SM = "/img/hero-locker-sm.jpg"
# Product-led crops of the four team banners, generated by src/crop_art.py.
TEAM_CARD_ART = {
    "cleveland-browns": "/img/team-cleveland.jpg",
    "green-bay-packers": "/img/team-greenbay.jpg",
    "dallas-cowboys": "/img/team-dallas.jpg",
    "michigan": "/img/team-michigan.jpg",
}


def home_banner():
    """Split editorial hero: ~40% copy panel, ~60% cinematic football imagery.

    Kept deliberately short (about 78vh on a desktop, far less on a phone) so
    "Shop By Team" is already in view, or one flick away, when the page
    settles. The hero image is the LCP element: it is eager, high-priority
    and served in two widths - never lazy-loaded.
    """
    n = len(ALL)
    return f"""<section class="hero editorial" id="hero"><div class="wrap hero-grid">
 <div class="hero-copy">
  <span class="hero-kicker">Football. Fans. Culture.</span>
  <h1 class="hero-title">Gear <span class="up">Up.</span></h1>
  <span class="hero-brush">Keep it.</span>
  <p class="hero-sub">Original fan-made apparel for the teams we love.<br>
  Four cities. Four fanbases. One locker.</p>
  <div class="btnrow">
   <a class="btn lg" href="/collections/">Shop By Team &rarr;</a>
   <a class="btn ghost lg" href="/drops/">Trending Now &rarr;</a>
  </div>
  <div class="hero-facts"><span>{n} fan designs</span><span>S&ndash;3XL</span><span>Worldwide shipping</span></div>
 </div>
 <div class="hero-stage">
  <img class="hero-art" src="{HERO_ART}"
   srcset="{HERO_ART_SM} 760w, {HERO_ART} 1400w"
   sizes="(max-width:920px) 100vw, 58vw"
   alt="{esc(BRAND)} fan-made hoodies, football helmets and a football lined up in a locker room"
   width="1400" height="827" fetchpriority="high" decoding="async">
 </div>
</div></section>"""


def guide_grid():
    """Buying guides - editorial cards, below the shopping experience.

    Every card points at a page that already exists (the four team buying
    guides, the Week 1 guide, the size guide); no invented URLs, no invented
    titles. Guides answer the questions a first-time fan-apparel buyer asks
    once they have seen the product, which is why they sit here and not
    above the catalogue."""
    cards = "".join([
        '<a class="guide-card reveal" href="/guides/2026-week-1-shirts/">'
        '<span class="gc-kick">Game day</span>'
        '<b>What To Wear On Game Day</b>'
        '<span class="gc-sub">The 2026 Week 1 fan-shirt guide: what fans are wearing for the '
        'openers, team by team.</span><span class="gc-go">Read the guide &rarr;</span></a>',
        '<a class="guide-card reveal" href="/guides/">'
        '<span class="gc-kick">Team shirts</span>'
        '<b>Team Shirt Guide</b>'
        '<span class="gc-sub">Cleveland, Green Bay, Dallas and Michigan - what makes a good '
        'shirt for each fanbase.</span><span class="gc-go">All buying guides &rarr;</span></a>',
        '<a class="guide-card reveal" href="/size-guide/">'
        '<span class="gc-kick">Fit</span>'
        '<b>How To Pick The Right Fan Fit</b>'
        '<span class="gc-sub">Measurements for every cut we print, S-3XL, unisex and '
        "women's.</span><span class=\"gc-go\">Size guide &rarr;</span></a>",
        '<a class="guide-card reveal" href="/shipping/">'
        '<span class="gc-kick">Delivery</span>'
        '<b>Shipping &amp; Returns</b>'
        f'<span class="gc-sub">Printed on demand in the USA, {DELIVERY_TIME} to your door, '
        '30-day misprint replacement.</span><span class="gc-go">Read the details &rarr;</span></a>',
    ])
    return f"""<section class="guidesec" id="guides"><div class="wrap">
 <div class="sechead reveal"><div>
  <span class="eyebrow"><span class="dot"></span> Know what you are buying</span>
  <h2>Buying <span class="accentword">Guides</span></h2>
  <p>Sizing, shipping and game-day answers in one place - no guesswork before checkout.</p></div>
  <a class="link" href="/guides/">All guides &rarr;</a></div>
 <div class="guide-grid">{cards}</div>
</div></section>"""


def custom_design():
    """Compact custom-design section. The form is unchanged - same field
    names, same FormSubmit hidden inputs, same #customForm / #formmsg hooks
    app.js binds to - it is only re-framed so it reads as one confident
    offer instead of a second storefront."""
    return f"""<section class="customsec" id="custom-design"><div class="wrap">
 <div class="customrow reveal">
  <div class="customimg">
   <img src="/img/custom-tee1.png" alt="Custom t-shirt design - make your own fan apparel"
    loading="lazy" decoding="async" width="1024" height="1536">
  </div>
  <div class="customform">
   <span class="eyebrow"><span class="dot"></span> Made to order</span>
   <h2>Your idea.<br>Your colors.<br><span class="accentword">Your game day.</span></h2>
   <p class="cf-lead">Want something different? A nickname, a catchphrase, a family crest, a
   group slogan, a memorial, a gift for your crew - we turn it into original fan apparel you can
   buy one at a time.</p>
   <form id="customForm"
         method="POST" data-formsubmit="1" aria-label="Custom design request form" novalidate>
    <div class="cf-head">Tell us about your idea</div>
    <p class="cf-sub">Send us the details and we'll reply with a proof and a price.</p>
    <input type="hidden" name="_subject" value="New Custom Design Request from your website">
    <input type="hidden" name="_template" value="table">
    <input type="hidden" name="_captcha" value="false">
    <input type="text" name="_honey" style="display:none" tabindex="-1" autocomplete="off">
    <div class="row">
     <label>Your name<input type="text" name="name" required placeholder="John Doe" autocomplete="name"></label>
     <label>Your email<input type="email" name="email" required placeholder="you@example.com" autocomplete="email"></label>
    </div>
    <div class="row">
     <label>Team / theme<select name="team" required>
      <option value="">Choose</option><option>Cleveland</option><option>Green Bay</option>
      <option>Dallas</option><option>Michigan</option><option>Other / custom</option></select></label>
     <label>Garment<select name="garment">
      <option value="">Choose</option><option>T-Shirt</option><option>Hoodie</option>
      <option>Sweatshirt</option><option>Long Sleeve</option><option>Mug</option><option>Beanie</option>
      <option>Other</option></select></label>
    </div>
    <label>Your idea<input type="text" name="idea" required
     placeholder="e.g. 'GO BROWNS', a nickname, a catchphrase"></label>
    <label>Anything else?<textarea name="details" rows="3"
     placeholder="Sizes, quantity, or the story behind the design (optional)"></textarea></label>
    <button class="btn block lg" type="submit">Request Custom Apparel &rarr;</button>
    <p class="formmsg" id="formmsg" aria-live="polite">We'll reply by email, usually within 1&ndash;2 days.</p>
   </form>
  </div>
 </div>
</div></section>"""


def brand_newsletter():
    """Bottom email signup. Static-site friendly: FormSubmit fallback handled
    in app.js, so no backend and no third-party account required. Kept
    deliberately small - it is the last thing on the page, not the loudest."""
    return f"""<section class="brandsec" id="newsletter"><div class="wrap">
 <div class="brand-grid">
  <div class="brand-copy reveal">
   <span class="eyebrow"><span class="dot"></span> Join the locker</span>
   <h2>Stay In The <span>Locker.</span></h2>
   <p>Football culture, new designs and game-day inspiration. One email a week, no spam.</p>
   <div class="brand-tags"><span>Cleveland</span><span>Green Bay</span><span>Dallas</span><span>Michigan</span></div>
  </div>
  <form class="newsform reveal" id="newsForm" method="POST" aria-label="Newsletter signup" novalidate>
   <input type="hidden" name="_subject" value="Newsletter signup">
   <input type="hidden" name="_template" value="table">
   <input type="hidden" name="_captcha" value="false">
   <input type="text" name="_honey" style="display:none" tabindex="-1" autocomplete="off">
   <label for="newsEmail">Email address</label>
   <span class="nf-row"><input id="newsEmail" type="email" name="email" required placeholder="you@example.com" autocomplete="email">
   <button class="btn" type="submit">Join &rarr;</button></span>
   <p class="formmsg" id="newsMsg" aria-live="polite">We only email about the locker. Unsubscribe anytime.</p>
  </form>
 </div>
</div></section>"""


def quick_find():
    """Landing-page product finder: live search + one-tap shortlists.

    Visitors land on / or /collections/ and used to meet the news ticker, a
    countdown and four 4-card teasers before any real product surface - the
    only path to a design was scrolling or remembering a team. This panel
    sits directly under the hero: type a player, slogan, city or garment and
    get live suggestions, or tap a shortlist chip that opens /search/ with
    the filter already applied. Trending chips come from the Fan Trend Index
    (only names that have a design to shop).
    """
    n = len(ALL)
    counts = {}
    for it in ALL:
        counts[it["garment"]] = counts.get(it["garment"], 0) + 1
    top = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:5]
    team_chips = "".join(
        f'<a class="qf-chip" style="{theme_vars(k)}" href="/search/?t={k}">{esc(COLLECTIONS[k]["short"])}</a>'
        for k in ORDER)
    type_chips = "".join(
        f'<a class="qf-chip" href="/search/?g={esc(g)}">{esc(g)}s <em>{c}</em></a>'
        for g, c in top)
    trend_chips = ""
    for r in fti_rows():
        ck = r.get("collection")
        if not ck or ck not in COLLECTIONS:
            continue
        if not products_for_entity(ck, r["name"], 1):
            continue
        trend_chips += (f'<a class="qf-chip hot" style="{theme_vars(ck)}" '
                        f'href="/search/?q={esc(r["name"])}">{esc(pretty_name(r["name"]))} '
                        f'<em>trending</em></a>')
        if trend_chips.count("qf-chip hot") >= 4:
            break
    return f"""<section class="quickfind" id="quickfind"><div class="wrap">
 <div class="qf-head reveal">
  <span class="eyebrow"><span class="dot"></span> {n} designs &middot; live search</span>
  <h2>Find A <span class="accentword">Design</span></h2>
  <p>Search by player, slogan, team or garment - or tap a shortlist and you are in.</p>
 </div>
 <div class="qf-box reveal">
  <span class="gs"><input class="gsearch" type="search"
   placeholder='Try "Shedeur", "Dawg Pound", "hoodie" or "mug"'
   aria-label="Search all designs" autocomplete="off"></span>
  <div class="qf-chips"><a class="qf-chip" href="/search/">All designs <em>{n}</em></a>
   {team_chips}{type_chips}
   <a class="qf-chip" href="/search/?st=player">Player designs</a>
   <a class="qf-chip" href="/search/?st=funny">Funny</a>
   <a class="qf-chip" href="/search/?st=retro">Vintage</a>
   <a class="qf-chip" href="/search/?st=family">Gift</a>
   {trend_chips}</div>
 </div>
</div></section>"""


# ---------------------------------------------------------------- pages
def page_home():
    """The storefront homepage.

    Section order is the funnel, and it is deliberate:

        HERO -> SHOP BY TEAM -> SHOP THE LOCKER -> TRENDING NOW ->
        2026 SEASON -> TEAM COLLECTIONS -> GUIDES -> CUSTOM -> TREND INDEX ->
        NEWSLETTER -> FOOTER

    Brand, then team, then product - a visitor meets real merchandise inside
    the second viewport instead of scrolling through four editorial bands to
    find out what is for sale. Everything below "2026 Season" is the
    editorial/authority half of the page and is ordered by how many visitors
    it serves.
    """
    path = "/"
    # Each product surface skips what the surface above it already showed, so
    # the homepage puts as much of the catalogue in front of a visitor as it
    # can instead of repeating the same handful of designs.
    locker = locker_picks()
    shown = {x["slug"] for x in locker}
    trending = trending_now(exclude=shown)
    shown |= set(re.findall(r'href="/shop/([^/]+)/"', trending))
    # Per-team sections - never mix teams. Ordered by next kickoff so the team
    # playing soonest is the first block you meet.
    team_sections = ""
    for k in HOMEPAGE_ORDER:
        block = team_section(k, exclude=shown)
        shown |= set(re.findall(r'href="/shop/([^/]+)/"', block))
        team_sections += block
    schema = [
        {"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": DOMAIN,
         "logo": DOMAIN + "/img/favicon.svg",
         "description": f"Independent fan-made football apparel store with {len(ALL)} original designs.",
         "sameAs": [u for _, u in SOCIALS]},
        {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": DOMAIN,
         "potentialAction": {"@type": "SearchAction",
                             "target": DOMAIN + "/search/?q={search_term_string}",
                             "query-input": "required name=search_term_string"}},
        {"@context": "https://schema.org", "@type": "ItemList",
         "itemListElement": [{"@type": "ListItem", "position": n + 1, "url": DOMAIN + f"/{COLLECTIONS[k]['slug']}/",
                              "name": COLLECTIONS[k]["name"]} for n, k in enumerate(ORDER)]},
    ]
    desc = (f"Fan-made football tees, hoodies and gear across {len(ORDER)} team collections: "
            f"Cleveland, Green Bay, Dallas and Michigan. {len(ALL)} original designs, S-3XL, shipped worldwide.")
    body = f"""<main id="main">
{home_banner()}
{shop_nav()}
{shop_by_team()}
{shop_the_locker(picks=locker)}
{trending}
{trust()}
{season_section()}
<div class="light">
{team_sections}
</div>
{guide_grid()}
{custom_design()}
{fti_strip()}
{newsticker()}
{brand_newsletter()}
</main>"""
    URLS.append((DOMAIN + "/", "1.0", "daily"))
    write("index.html", head(f"{BRAND} | {CFG['tagline']}", desc, path, "/img/hero-home.jpg?v=4", schema,
                             ["football fan shirts", "nfl fan t shirts", "custom football tees",
                              "cleveland browns shirts", "green bay packers shirts",
                              "dallas cowboys shirt", "michigan football shirt"])
          + header() + body + footer(popup=False))


def page_collections_index():
    path = "/collections/"
    # Circular team portraits in the fixed ORDER - this page is a navigation
    # hub, not a duplicate of the homepage. The four per-team product grids
    # used to live here and forced visitors to scroll ~16 teaser cards before
    # choosing a side; they are replaced by one store-wide trending row.
    cards = "".join(team_circle_card(k) for k in ORDER)
    hot = [x for x in ALL if x.get("trend") == "hot"]
    have = {x["slug"] for x in hot}
    trending = (hot + [x for x in ALL if x["slug"] not in have])[:8]
    trend_cards = "".join(card(i, eager=(n < 4)) for n, i in enumerate(trending))
    cb, cbs = crumbs([("Home", "/"), ("Collections", None)], path)
    schema = [cbs, {"@context": "https://schema.org", "@type": "CollectionPage",
                    "name": "All Collections", "url": DOMAIN + path,
                    "hasPart": [{"@type": "CollectionPage", "name": COLLECTIONS[k]["name"],
                                 "url": DOMAIN + f"/{COLLECTIONS[k]['slug']}/"} for k in ORDER]}]
    desc = ("Shop fan-made football collections: Cleveland Browns, Green Bay Packers, Dallas "
            "and Michigan tees & hoodies. Sizes S-3XL, worldwide shipping.")
    body = f"""{cb}<main id="main"><section style="padding-top:6px"><div class="wrap">
 <h1>All Football Fan Collections</h1>
 <p class="muted" style="max-width:70ch">Four team collections, {len(ALL)} original designs. Each
 collection has its own colour palette, slang and artwork style - pick your side below.</p>
 {quick_find()}
 <h2 class="sr-only">Browse Collections</h2>
 <div class="teamcircles">{cards}</div>
</div></section>
<div class="light">
<section class="trendinghub"><div class="wrap">
 <div class="sechead reveal"><div><span class="eyebrow"><span class="dot"></span> Fresh from the headlines</span>
  <h2>Trending Across <span class="accentword">All Teams</span></h2>
  <p>No team preference yet? These are the designs the last 10 days of
  headlines are pushing - re-scored daily from public news.</p></div>
  <a class="link" href="/drops/">All live drops &rarr;</a></div>
 <div class="grid">{trend_cards}</div>
</div></section>
</div>
</main>"""
    URLS.append((DOMAIN + path, "0.9", "weekly"))
    write("collections/index.html", head("All Football Fan Collections | " + BRAND, desc, path,
                                         "/img/hero-home.jpg?v=4", schema) + header() + body + footer())


def page_search():
    """/search/ - the browse-all catalogue: every design, one page, filterable.

    The SearchAction schema advertises `?q=` and the header search hands
    people here with ?t=/ ?g=/ ?q= deep links, so this page is a real
    indexable catalogue (it is in the sitemap on purpose): the complete grid
    plus team / garment filters and sorting, all client-side. ?q=, ?t= and
    ?g= pre-apply on load (app.js) so Google sitelinks and the header search
    land on the right view.
    """
    path = "/search/"
    n = len(ALL)
    prices = sorted(x["price"] for x in ALL)
    # Garment chips in catalogue-size order (most stock first).
    counts = {}
    for it in ALL:
        counts[it["garment"]] = counts.get(it["garment"], 0) + 1
    types = sorted(counts, key=lambda t: (-counts[t], t))
    type_chips = '<button class="chip on" data-f="all">All</button>' + "".join(
        f'<button class="chip" data-f="{esc(t)}">{esc(t)}s</button>' for t in types)
    team_chips = ('<button class="chip on" data-team="all">All teams</button>' + "".join(
        f'<button class="chip" data-team="{k}">{esc(COLLECTIONS[k]["short"])}</button>'
        for k in ORDER))
    style_chips = '<button class="chip on" data-st="all">All styles</button>' + "".join(
        f'<button class="chip" data-st="{v}">{label}</button>' for v, label in SHOP_STYLE_CHIPS)
    cards = "".join(card(i, eager=(x < 4)) for x, i in enumerate(ALL))
    cb, cbs = crumbs([("Home", "/"), ("All Designs", None)], path)
    schema = [cbs, {"@context": "https://schema.org", "@type": "CollectionPage",
                    "name": "All Fan Designs", "url": DOMAIN + path,
                    "description": f"Every fan-made design in the locker: {n} designs "
                                   "across Cleveland, Green Bay, Dallas and Michigan.",
                    "isPartOf": {"@type": "WebSite", "name": BRAND, "url": DOMAIN},
                    "mainEntity": {"@type": "ItemList", "numberOfItems": n,
                                   "itemListElement": [
                                       {"@type": "ListItem", "position": x + 1,
                                        "url": DOMAIN + i["url"], "name": i["name"]}
                                       for x, i in enumerate(ALL)]}}]
    desc = (f"Search and browse all {n} fan-made football designs - Cleveland, Green Bay, "
            f"Dallas and Michigan tees, hoodies, mugs and beanies from ${prices[0]:.2f}. "
            "Filter by team or garment, sizes S-3XL, worldwide shipping.")
    body = f"""{cb}<main id="main"><section style="padding-top:6px"><div class="wrap">
 <h1>Browse &amp; Search All {n} Designs</h1>
 <p class="muted" style="max-width:70ch">The whole locker in one place. Type a player, slogan,
 city or garment - or narrow it down with the team and garment filters below.</p>
</div></section>
<div class="light"><div class="wrap">
 <div class="toolswrap">
  <div class="tools">
   <span class="gs"><input id="q" class="gsearch" type="search"
    placeholder="Search all designs - player, slogan, team..."
    aria-label="Search all designs" autocomplete="off"></span>
   <select id="price" aria-label="Price">
    <option value="any">Any price</option><option value="u20">Under $20</option>
    <option value="20-25">$20 - $25</option><option value="25-30">$25 - $30</option>
    <option value="o30">$30+</option>
   </select>
   <select id="sort" aria-label="Sort">
    <option value="feat">Featured</option><option value="lo">Price: low to high</option>
    <option value="hi">Price: high to low</option><option value="az">Name A-Z</option>
   </select>
  </div>
  <div class="chipsrow"><span class="chipslabel">Team</span><div class="chips">{team_chips}</div></div>
  <div class="chipsrow"><span class="chipslabel">Garment</span><div class="chips">{type_chips}</div></div>
  <div class="chipsrow"><span class="chipslabel">Style</span><div class="chips">{style_chips}</div></div>
 </div>
 <p class="muted" id="count" style="font-size:.85rem">{n} designs</p>
 <h2 class="sr-only">All Designs</h2>
 <div class="grid" id="pg">{cards}</div>
 <p class="muted center" id="nores" style="display:none;padding:40px 0">No designs match that
 search. <a class="link" href="/collections/">Browse a collection instead</a></p>
</div></div></main>"""
    URLS.append((DOMAIN + path, "0.6", "daily"))
    write("search/index.html",
          head(f"Search All {n} Fan Designs | {BRAND}", desc, path, "/img/hero-home.jpg?v=4",
               schema, ["all fan shirts", "search football fan apparel",
                        "football fan design search", "custom fan tee search"])
          + header() + body + footer())


def page_collection(k):
    c = COLLECTIONS[k]
    items = MODEL[k]
    path = f"/{c['slug']}/"
    prices = sorted(x["price"] for x in items)
    types = sorted({x["garment"] for x in items})
    chips = '<button class="chip on" data-f="all">All</button>' + "".join(
        f'<button class="chip" data-f="{esc(t)}">{esc(t)}s</button>' for t in types)
    present = {x["theme"] for x in items}
    style_chips = '<button class="chip on" data-st="all">All styles</button>' + "".join(
        f'<button class="chip" data-st="{v}">{label}</button>' for v, label in SHOP_STYLE_CHIPS
        if v in present)
    cards = "".join(card(i, eager=(n < 4)) for n, i in enumerate(items))
    cb, cbs = crumbs([("Home", "/"), ("Collections", "/collections/"), (c["short"], None)], path)
    schema = [cbs,
              {"@context": "https://schema.org", "@type": "CollectionPage", "name": c["h1"],
               "url": DOMAIN + path, "description": c["intro"].format(**c),
               "isPartOf": {"@type": "WebSite", "name": BRAND, "url": DOMAIN},
               "mainEntity": {"@type": "ItemList", "numberOfItems": len(items),
                              "itemListElement": [
                                  {"@type": "ListItem", "position": n + 1, "url": DOMAIN + i["url"],
                                   "name": i["name"]} for n, i in enumerate(items)]}},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                  for q, a in [
                      (f"How many {c['short']} designs are available?",
                       f"There are currently {len(items)} original designs in this collection, priced "
                       f"from ${prices[0]:.2f} to ${prices[-1]:.2f}, across {len(types)} product types: "
                       + ", ".join(types) + "."),
                      ("Are these officially licensed?",
                       "No. These are independent fan-made graphics. They are not affiliated with, "
                       "endorsed by or licensed by any league, club, university or player."),
                      ("What sizes do you carry?",
                       "Unisex sizes S through 3XL on apparel, plus women's cuts on many designs. "
                       "Full measurements are listed on every product page and in the size guide."),
                  ] + list(c.get("faq_extra", []))]}]
    desc = (f"{c['name']} - {len(items)} fan-made designs from ${prices[0]:.2f}. "
            f"{', '.join(types[:3])}, sizes S-3XL. Printed on demand, ships worldwide.")
    # Collection switch tabs: a visitor 40 products deep in Cleveland can jump
    # to Green Bay without back-buttoning to the header - keeps them browsing.
    swtabs = "".join(
        f'<a class="swt" style="{theme_vars(x)}" href="/{COLLECTIONS[x]["slug"]}/"'
        f'{" aria-current=page" if x == k else ""}>{esc(COLLECTIONS[x]["short"])}</a>'
        for x in ORDER) + '<a class="swt swt-all" href="/collections/">All</a>'
    se = SEASON[k]
    lore = "".join(f"<li>{esc(x)}</li>" for x in c["lore"])
    kwlinks = " &middot; ".join(esc(x) for x in c["keywords"])
    # Creator cross-link: the team that has a creator collaboration gets a
    # one-line pointer at the bottom of its collection page (data-driven -
    # a future creator page appears here automatically).
    cre_link = ""
    cre = creator_by_collection(k)
    if cre:
        cre_link = (f'<p><b>New &mdash; {esc(cre["page_name"])}:</b> a creator-curated '
                    f'capsule from this collection, built with {esc(cre["display_name"])}, '
                    f'a {esc(cre["role"])}. '
                    f'<a class="link" href="/{cre["page_slug"]}/">Visit '
                    f'{esc(cre["display_name"])}\'s locker &rarr;</a></p>')
    # Page order: compact hero -> this team's moving ticker -> the complete
    # searchable / filterable / sortable grid -> trust strip -> a short season
    # note and the collection description. No countdown here (the countdown
    # stays on the homepage / Week 1 guide, untouched).
    #
    # Product-first: the Fan Trend Index leaderboard, live player moments and
    # the headline list used to sit here too, pushing the buying-guide copy
    # ~2 screens further down and duplicating /2026-season/ and
    # /fan-trend-index/ on every team page. They now live only on those two
    # hubs; the team page keeps a one-line pointer to each.
    fti_top = fti_rows(k)[:1]
    fti_note = ""
    if fti_top:
        r = fti_top[0]
        fti_note = (f' Hottest name in the {esc(c["short"])} headlines this week: '
                    f'<strong>{esc(pretty_name(r["name"]))}</strong> '
                    f'(Fan Trend Index {int(r["index"])}/100).')
    body = f"""
<main id="main"><section class="cbanner compact" style="padding:0">
 <div class="band"><img src="{c['hero']}" alt="{esc(c['name'])} banner" width="1933" height="813" fetchpriority="high"></div>
 <div class="cb-in">
  <span class="eyebrow"><span class="dot"></span> {len(items)} designs &middot; from ${prices[0]:.2f}</span>
  <h1>{esc(c['h1'])}</h1>
  <p class="lede">{esc(c['banner'])}</p>
  <p class="vs">Checkout collection: <b>{esc(c['vs_name'])}</b></p>
 </div>
</section>
{ticker(k)}
<div class="light">
{cb}
<section id="grid" style="padding-top:4px"><div class="wrap">
 <div class="toolswrap">
  <div class="sw" aria-label="Switch collection">{swtabs}</div>
  <div class="tools">
   <input id="q" type="search" placeholder="Search {esc(c['short'])} designs..." aria-label="Search designs">
   <div class="chips">{chips}</div>
   <select id="price" aria-label="Price">
    <option value="any">Any price</option><option value="u20">Under $20</option>
    <option value="20-25">$20 - $25</option><option value="25-30">$25 - $30</option>
    <option value="o30">$30+</option>
   </select>
   <select id="sort" aria-label="Sort">
    <option value="feat">Featured</option><option value="lo">Price: low to high</option>
    <option value="hi">Price: high to low</option><option value="az">Name A-Z</option>
   </select>
  </div>
  <div class="chipsrow"><span class="chipslabel">Style</span><div class="chips">{style_chips}</div></div>
 </div>
 {trust()}
 <p class="muted" id="count" style="font-size:.85rem">{len(items)} designs</p>
 <h2 class="sr-only">Collection Designs</h2>
 <div class="grid" id="pg">{cards}</div>
 <p class="muted center" id="nores" style="display:none;padding:40px 0">No designs match that search.</p>
</div></section>
<section style="border-top:1px solid var(--line)"><div class="wrap prose reveal">
 <h2>{esc(c['short'])} In The 2026 Season</h2>
 <div class="trendbox"><b><span class="dot"></span> Season update &middot; {TODAY}</b>
  {esc(se['headline'])} {esc(se['status'])}.{(" " + esc(se['legacy_note'])) if se['legacy_note'] else ""}{fti_note}</div>
 <p>Fans searching for {", ".join(esc(x) for x in se['hot'][:3])} land here. Kickoff is
 <strong>{esc(re.sub('&middot;', '-', se['opener']))}</strong>, so anything ordered in the next week
 Delivery timing is an estimate; arrival before a specific game is not guaranteed. Live headlines, player moments and the full
 {esc(c['short'])} leaderboard are on the <a class="link" href="/2026-season/">2026 season hub</a>
 and the <a class="link" href="/fan-trend-index/">Fan Trend Index</a>.</p>
 <h2>About the {esc(c['name'])} Collection</h2>
 <p>{esc(c['intro'].format(**c))} Prices start at <strong>${prices[0]:.2f}</strong> and the range
 covers {len(types)} product types: {esc(', '.join(types))}. Everything is unisex unless the design
 name says otherwise, and every apparel item runs from S to 3XL.</p>
 <ul>{lore}</ul>
 <h2>Popular searches in this collection</h2>
 <p class="muted">{kwlinks}</p>
 <h2>How ordering works</h2>
 <p>Pick a design and open its product page. That page is where the design, the garment styles,
 the colourways, the sizing and the shipping facts live. When you are ready, tap <strong>Shop
 Now</strong> and you land on the Viralstyle product page for that exact campaign, where you
 choose garment style, colour and size and complete the order. Items are printed after the order
 is placed and shipped worldwide with tracking.</p>
 <p><a class="link" href="/guides/{c['slug']}-buying-guide/">Read the {esc(c['short'])} buying guide &rarr;</a></p>
 {cre_link}
</div></section>
</div>
</main>"""
    URLS.append((DOMAIN + path, "0.9", "daily"))
    write(f"{c['slug']}/index.html",
         head(f"{c['name']} | {BRAND}", desc, path, c["hero"], schema,
               c["keywords"] + se["hot"], col=k)
          + header(k) + body + footer())


def page_creator(ckey="joe"):
    """Creator collaboration page: Joe's Michigan Locker.

    A creator gets ONE permanent, addressable destination
    (``/{page_slug}/``, e.g. /michigan/joe/) that he links from social
    media. The page is a premium, team-coloured shopping surface for the
    creator's hand-picked designs (data/creators.json: ``picks`` /
    ``featured``), and it is the attribution root of the collaboration:

    * every internal product link carries ``?creator=<ID>`` so the
      product page refreshes the persistent ``gl_creator`` cookie, and
    * assets/app.js then tags the outbound Viralstyle hand-off on ANY
      page with ``creator=<ID>`` + UTM, so orders stay attributed to the
      creator for the cookie window (90 days) - direct link, organic
      search, bookmark or deep link.

    The commission rate in the creator record is INTERNAL: it documents
    what the owner owes the creator (net product sales, excl. taxes /
    shipping / refunds / cancellations / chargebacks) and never renders
    on the customer-facing page.
    """
    cre = CREATORS.get(ckey)
    if not cre:
        return
    ckey_col = cre["collection_key"]
    c = COLLECTIONS[ckey_col]
    items = creator_items(cre)
    if not items:
        print(f"creator {ckey!r}: no live picks - page skipped")
        return
    track = (cre.get("attribution") or {}).get("creator_id") or cre["id"]
    path = f"/{cre['page_slug']}/"
    prices = sorted(x["price"] for x in items)
    minp, maxp = prices[0], prices[-1]
    cre_page_desc = (f"Joe's Michigan Locker: Michigan football gear selected with Joe. "
                     f"Game-day tees, crewnecks and vintage-inspired designs, printed on "
                     f"demand and shipped worldwide.")
    types = sorted({x["garment"] for x in items})
    feat_slugs = [s for s in cre.get("featured", []) if s in {x["slug"] for x in items}]
    by_slug = {x["slug"]: x for x in items}
    feat = [by_slug[s] for s in feat_slugs] or items[:4]
    kw = ["joe's michigan locker", "michigan football shirt", "go blue t-shirt",
          "michigan vs everybody shirt", "ann arbor football gear", "qb19 shirt",
          "michigan sweatshirt", "maize and navy tee", "michigan game day shirt",
          "wolverines fan gear"]

    def jlink(it):
        """Internal product link that carries the creator id forward."""
        return f"/shop/{it['slug']}/?creator={track}"

    def jcard(it, cls, eager=False):
        lazy = "" if eager else ' loading="lazy" decoding="async"'
        tag = {"player": "Player Story", "retro": "Vintage", "funny": "Culture"}.get(it["theme"], "Game Day")
        return (f'<a class="{cls}" href="{jlink(it)}" '
                f'data-slug="{it["slug"]}" data-price="{it["price"]:.2f}" '
                f'data-creator="{track}" data-collection="{ckey_col}">'
                f'<span class="jph"><img src="{it["front"]}" '
                f'alt="{esc(it["name"])} - {esc(it["art"][:70])}" '
                f'width="530" height="630"{lazy}></span>'
                f'<span class="jb">'
                f'<h3 class="jname">{esc(it["name"])}</h3>'
                f'<span class="jmeta">{esc(it["garment"])} &middot; {esc(c["short"])}</span>'
                f'<span class="jfoot"><span class="jprice">${it["price"]:.2f}</span>'
                f'<span class="jtag">{tag}</span></span>'
                f'</span>'
                f'<span class="jshop" aria-hidden="true">Shop <i>&rarr;</i></span>'
                f'</a>')

    feat_cards = "".join(jcard(it, "jfeat", eager=(n < 2)) for n, it in enumerate(feat))
    grid_cards = "".join(jcard(it, "jcard", eager=(n < 2)) for n, it in enumerate(items))

    faq = [
        ("What is Joe's Michigan Locker?",
         "A creator collaboration: Joe, a Michigan football creator, hand-picks "
         "designs from Gridiron Locker's Michigan collection and builds this "
         "dedicated locker for his audience. It is one permanent link - new "
         "designs are added to Joe's locker without ever changing it."),
        ("Are these officially licensed Michigan products?",
         "No. Everything here is independent, fan-made artwork. Gridiron Locker "
         "is not affiliated with, endorsed by or licensed by the University of "
         "Michigan, the NCAA or any player. All trademarks are the property of "
         "their respective owners."),
        ("How does ordering work?",
         "Tap any design to see the full story, garment styles, colours and "
         "sizing. Then Shop Now opens the checkout page for that exact design, "
         "where you choose garment style, colour and size. Items are printed on "
         "demand and shipped worldwide with tracking."),
    ]

    cb, cbs = crumbs([("Home", "/"), ("Michigan", f"/{c['slug']}/"),
                      ("Joe's Michigan Locker", None)], path)
    schema = [cbs,
              {"@context": "https://schema.org", "@type": "CollectionPage",
               "name": "Joe's Michigan Locker", "url": DOMAIN + path,
               "description": cre_page_desc,
               "isPartOf": {"@type": "WebSite", "name": BRAND, "url": DOMAIN},
               "about": {"@type": "ItemList", "numberOfItems": len(items),
                         "itemListElement": [
                             {"@type": "ListItem", "position": n + 1,
                              "url": DOMAIN + f"/shop/{x['slug']}/", "name": x["name"]}
                             for n, x in enumerate(items)]}},
              {"@context": "https://schema.org", "@type": "FAQPage",
               "mainEntity": [
                   {"@type": "Question", "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": a}}
                   for q, a in faq]}]

    desc_bits = f"{len(items)} hand-picked designs &middot; from ${minp:.2f} &middot; " \
                f"{', '.join(types[:3])} &middot; printed on demand &middot; ships worldwide"
    body = f"""
<main id="main" class="jlock">
<section class="jhero">
 <div class="wrap jhero-grid">
  <div class="jcopy">
   <span class="jeyebrow"><span class="jdiamond"></span> A Gridiron Locker &times; Joe Collaboration</span>
   <h1>JOE'S MICHIGAN <span class="jgold">LOCKER</span></h1>
   <p class="jsub">Michigan football gear selected with Joe.</p>
   <p class="jsupp">Built for Michigan fans. Powered by Gridiron Locker.</p>
   <div class="jctas">
    <a class="jbtn" href="#picks">Shop Joe's Picks</a>
    <a class="jbtn ghost" href="/{c['slug']}/">All Michigan</a>
   </div>
   <p class="jfacts">{desc_bits}</p>
  </div>
  <div class="jart">
   <img src="/img/hero-joe.jpg" alt="Vintage football on a locker-room bench beside folded navy and maize shirts"
    width="1933" height="813" fetchpriority="high" decoding="async">
  </div>
 </div>
</section>

<section class="jintro">
 <div class="wrap">
  <span class="jeyebrow"><span class="jdiamond"></span> Joe's Picks</span>
  <h2>A locker built by a fan</h2>
  <blockquote class="jquote">
   <p>Joe has teamed up with Gridiron Locker to bring Michigan fans a collection of
   designs built around the moments, stories and culture that make Michigan football special.</p>
   <cite>Joe &times; Gridiron Locker</cite>
  </blockquote>
  <p class="jnote">This is not an official Michigan store. It is a creator-curated selection of
  independent, fan-made artwork from Gridiron Locker's Michigan collection - hand-picked by Joe
  for his audience, printed on demand in the USA and shipped worldwide.</p>
 </div>
</section>

<section id="picks" class="jpicks">
 <div class="wrap">
  <div class="jsechead">
   <span class="jeyebrow"><span class="jdiamond"></span> Featured</span>
   <h2>Joe's Top Picks</h2>
   <p>Four designs Joe is most excited to see on the street this season.</p>
  </div>
  <div class="jfeat-row">{feat_cards}</div>
 </div>
</section>

<section id="locker" class="jgridsec">
 <div class="wrap">
  <div class="jsechead">
   <span class="jeyebrow"><span class="jdiamond"></span> The Locker</span>
   <h2>Joe's Michigan Collection</h2>
   <p>Every design in this locker was picked by Joe from the Gridiron Locker Michigan
   collection - game-day tees, crewnecks and vintage-inspired pieces with original artwork.
   No official logos, no licensed assets: just Michigan football culture.</p>
  </div>
  <div class="jtrustwrap">{trust()}</div>
  <div class="jgrid">{grid_cards}</div>
 </div>
</section>

<section class="jfaq">
 <div class="wrap">
  <div class="jsechead">
   <span class="jeyebrow"><span class="jdiamond"></span> Good to know</span>
   <h2>Frequently Asked Questions</h2>
  </div>
  {"".join(f'<details class="jqa"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in faq)}
 </div>
</section>

<section class="jcollab">
 <div class="wrap center">
  <h2>YOU'RE IN JOE'S LOCKER.</h2>
  <p>Every order placed through Joe's collection supports the collaboration and helps us
  create more Michigan football designs together.</p>
 </div>
</section>

<section class="jfinal">
 <div class="wrap center">
  <span class="jeyebrow navy"><span class="jdiamond navy"></span> Joe &times; Gridiron Locker</span>
  <h2>JOE'S MICHIGAN LOCKER</h2>
  <p>More Michigan designs coming as we build this collection together.</p>
  <a class="jbtn navy" href="#locker">Shop The Locker</a>
 </div>
</section>
<div class="jbar">
 <span class="jbar-l"><b>Joe's Michigan Locker</b><span>from ${minp:.2f}</span></span>
 <a class="jbtn" href="#picks">Shop Picks</a>
</div>
</main>"""

    URLS.append((DOMAIN + path, "0.9", "weekly"))
    write(f"{cre['page_slug']}/index.html",
          head(f"{cre['page_name']} | {BRAND}", cre_page_desc, path, "/img/hero-joe.jpg",
               schema, kw, col=ckey_col, body_attrs=f' data-creator-page="{track}"')
          + header(ckey_col) + body + footer())


def shop_now_cta(it, placement, label="Shop Now", size="lg", block=True):
    """The one and only conversion control on a product page.

    Every CTA is instrumented identically so the funnel metric we care about -
    product landing page -> Viralstyle CTR - is measurable per placement
    (hero, mid-page, footer band, mobile sticky bar). The click fires a
    `shop_now_click` GA4 event and a legacy `viralstyle_checkout_click` event
    so historical reporting keeps working.
    """
    cls = "btn" + (" block" if block else "") + (f" {size}" if size else "")
    return (f'<a class="{cls} shopnow" href="{it["buy"]}" target="_blank" rel="noopener"'
            f' data-slug="{it["slug"]}" data-price="{it["price"]:.2f}"'
            f' data-collection="{it["col"]}" data-placement="{placement}">'
            f'{label} <span aria-hidden="true">&rarr;</span></a>')


def cta_note(it, colours):
    """The sentence that removes the uncertainty about what happens next."""
    bits = ["garment style"]
    if colours > 1:
        bits.append("colour")
    if it["garment"] not in ("Mug", "Phone Case", "Beanie"):
        bits.append("size")
    listed = ", ".join(bits[:-1]) + " and " + bits[-1] if len(bits) > 1 else bits[0]
    return (f'<p class="ctanote">Choose your {listed} on the Viralstyle product page. '
            f'Checkout is completed there &ndash; Gridiron Locker never takes payment.</p>')


def page_product(it):
    """One design = one SEO landing page.

    Gridiron Locker does discovery and persuasion; Viralstyle does
    configuration and the transaction. So this page carries NO style picker,
    NO size picker, NO colour picker and NO checkout button - only product
    information and a SHOP NOW hand-off. Images remain browsable (a gallery is
    not a purchase control) and every option list is presented as verified
    information about the campaign, never as something to select here.
    """
    c = COLLECTIONS[it["col"]]
    f = FACTS[it["slug"]]
    path = it["url"]
    slug = it["slug"]
    price = f"{it['price']:.2f}"
    sizes = it["sizes_avail"]
    styles = it["styles"]
    colours = it["colours"]
    theme = it["theme"] if it["theme"] in _l.THEME_CONCEPT else "classic"

    title = _l.meta_title(it["name"], BRAND, slug=slug, col=c,
                          garment=it["garment"], theme=theme, art=it["art"])
    metad = _l.meta_description(slug, it["name"], c, it["garment"], price, styles,
                                colours, sizes, art=it["art"])
    hero_deck = _l.short_description(slug, it["name"], it["art"], c, it["garment"], theme)
    story_html = _l.design_story(slug, f, c, it["art"], theme, it["garment"])
    why_html = _l.why_it_stands_out(slug, f, c, it["art"], theme, it["garment"])
    who_html = _l.who_its_for(slug, c, theme, it["garment"], price,
                              name=it["name"], art=it["art"])
    wear_html = _l.gameday_wear(slug, c, it["garment"], it["art"])
    styles_html = _l.styles_copy(slug, styles, it["garment"])
    colour_html = _l.colour_copy(colours)
    size_html = _l.size_copy(slug, sizes, it["garment"])
    ship_html = _l.shipping_copy(DELIVERY_TIME, SHIP_US["shippingRate"]["value"])
    bullets = _l.details_bullets(it["garment"], styles, sizes, colours, price,
                                 features=it.get("features") or "")
    faq = _l.faqs(slug, f, c, it["garment"], price, colours, styles, sizes)
    kws = _l.keywords(f, c, it["garment"], it["name"])
    stage_alt = _l.image_alt(it["name"], it["art"], it["garment"], c["team"])

    # ---- gallery (informational imagery, not a configurator) --------------
    thumbs = "".join(
        f'<button class="thumb{" on" if n == 0 else ""}" data-src="{g}" type="button"'
        f' aria-label="View image {n+1} of {esc(it["name"])}">'
        f'<img src="{g}" alt="{esc(_l.image_alt(it["name"], it["art"], it["garment"], c["team"], n+1))}" '
        f'loading="lazy" width="120" height="140"></button>'
        for n, g in enumerate(it["gallery"][:10]))

    # ---- verified option displays ----------------------------------------
    stylelist = "".join(f'<li>{esc(s)}</li>' for s in styles)
    stylehtml = (f'<ul class="stylegrid">{stylelist}</ul>' if styles else "")

    colour_mockups = it["gallery"][2:12] if colours > 1 else []
    colourhtml = ""
    if colour_mockups:
        tiles = "".join(
            f'<button type="button" class="cwtile" data-src="{g}" '
            f'aria-label="View campaign mockup {n+1} of {esc(it["name"])}">'
            f'<img src="{g}" alt="{esc(_l.image_alt(it["name"], it["art"], it["garment"], c["team"], n+1))} '
            f'campaign mockup" loading="lazy" width="180" height="180"></button>'
            for n, g in enumerate(colour_mockups))
        colourhtml = (f'<div class="cwgrid">{tiles}</div>'
                      f'<p class="muted small">Colour previews are shown to help you choose your look. '
                      f'Final colour selection is made on Viralstyle.</p>')

    _CHART = {"S": (18, 28), "M": (20, 29), "L": (22, 30),
              "XL": (24, 31), "2XL": (26, 32), "3XL": (28, 33)}
    chart_rows = "".join(
        f"<tr><td>{s}</td><td>{_CHART[s][0]}</td><td>{_CHART[s][1]}</td></tr>"
        for s in sizes if s in _CHART)
    chart_html = ""
    if chart_rows and it["garment"] not in ("Mug", "Phone Case", "Beanie"):
        chart_html = (f'<table><tr><th>Size</th><th>Chest width (in)</th><th>Body length (in)</th></tr>'
                      f'{chart_rows}</table>'
                      f'<p class="muted small">Lay a shirt you already own flat and compare - it '
                      f'beats guessing. Full guide: <a href="/size-guide/">size guide</a>.</p>')

    bl = "".join(f"<li>{esc(b)}</li>" for b in bullets)
    faqhtml = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>"
                      for q, a in faq)

    # ---- internal linking -------------------------------------------------
    # Same collection only (never random unrelated teams). Prefer the same
    # design theme, then similar price. Spec wants 4-8 related products.
    rel = [x for x in MODEL[it["col"]] if x["slug"] != slug]
    rel = sorted(rel, key=lambda x: (x["theme"] != it["theme"], abs(x["price"] - it["price"])))[:6]
    relhtml = "".join(card(r) for r in rel)
    disclose = esc(_l.disclosure())

    cb, cbs = crumbs([("Home", "/"), ("Collections", "/collections/"),
                      (c["short"], f"/{c['slug']}/"), (it["name"], None)], path)

    # ---- structured data: real data only ---------------------------------
    # No aggregateRating, no review count, no fake sale price, no invented
    # inventory. The Offer points at the Viralstyle campaign because that is
    # where the transaction actually happens.
    schema_product = {
        "@context": "https://schema.org", "@type": "Product",
        "name": it["name"], "sku": slug,
        "description": re.sub(r"\s+", " ", hero_deck)[:600].strip(),
        "image": [abs_url(g) for g in it["gallery"][:6]],
        "brand": {"@type": "Brand", "name": BRAND},
        "category": f"{c['name']} > {it['garment']}",
        "size": sizes,
        # PeopleAudience (not the generic Audience) is what Google's
        # merchant listing spec reads for apparel gender targeting.
        "audience": {"@type": "PeopleAudience", "audienceType": f"{c['team']} fans",
                     "suggestedGender": audience_gender(it)},
        "offers": {"@type": "Offer", "url": it["buy"], "priceCurrency": "USD",
                   "price": price, "availability": "https://schema.org/InStock",
                   "itemCondition": "https://schema.org/NewCondition",
                   "validFrom": TODAY,
                   "priceValidUntil": f"{datetime.date.today().year + 1}-12-31",
                   "seller": {"@type": "Organization", "name": "Viralstyle"},
                   "shippingDetails": SHIP_US,
                   "hasMerchantReturnPolicy": RETURN_POLICY},
    }
    feats = (it.get("features") or "").lower()
    if "cotton" in feats and "poly" in feats:
        schema_product["material"] = "Cotton/Polyester"
    elif "cotton" in feats:
        schema_product["material"] = "Cotton"
    elif "acrylic" in feats:
        schema_product["material"] = "Acrylic"
    elif "polyester" in feats:
        schema_product["material"] = "Polyester"
    schema = [cbs, schema_product,
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q,
                   "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]

    se = SEASON[it["col"]]
    blob = (it["name"] + " " + it["art"]).lower()
    ent = entity_for_product(it["col"], slug, blob)
    fti_hit = next((r for r in fti_rows(it["col"]) if r["name"] == ent), None) if ent else None
    if it.get("trend") == "hot":
        fti_note = (f' Fan Trend Index {int(fti_hit["index"])}/100 '
                    f'({int(fti_hit["mentions"])} headline mentions).'
                    if fti_hit else "")
        trendhtml = (f'<div class="trendbox"><b><span class="dot"></span> Trending right now</b>'
                     f'{esc(se["headline"])} This design is one of the most searched in the '
                     f'{esc(c["short"])} collection this week.{fti_note}</div>')
    else:
        trendhtml = ""
    # Player-moment headlines stay off the conversion fold; the PDP is a
    # landing page, not a news hub.

    band_bits = [f"From ${price}"]
    if len(styles) > 1:
        band_bits.append(f"{len(styles)} garment styles")
    if colours > 1:
        band_bits.append(f"{colours} colourways")
    if it["garment"] not in ("Mug", "Phone Case", "Beanie"):
        band_bits.append(f"sizes {sizes[0]}-{sizes[-1]}")
    band_line = (", ".join(band_bits)
                 + ". Style, colour and size are chosen on the Viralstyle product page, "
                   "where the order is completed.")

    style_badge = (f"{len(styles)} garment styles" if len(styles) > 1
                   else (esc(styles[0]) if styles else esc(it["garment"])))
    colour_badge = (f"{colours} colourways" if colours > 1 else "Colours on Viralstyle")
    size_badge = (f"Sizes {sizes[0]}-{sizes[-1]}"
                  if it["garment"] not in ("Mug", "Phone Case", "Beanie") else "One size")

    body = f"""<main id="main" class="pdp-page" data-slug="{slug}" data-collection="{it['col']}" data-price="{price}"><div class="light">
{cb}
<div class="wrap"><div class="pdp">
 <div class="gallery">
  <div class="stage"><img id="stage" src="{it['gallery'][0]}" alt="{esc(stage_alt)}"
   width="530" height="630" fetchpriority="high"></div>
  <div class="thumbs">{thumbs}</div>
 </div>
 <div class="buybox">
  <span class="eyebrow">{esc(c['name'])}</span>
  <h1>{esc(it['name'])}</h1>
  <p class="herodeck">{esc(hero_deck)}</p>
  <div class="pricerow"><span class="pricebig">${price}</span>
   <span class="pricefrom">starting price &middot; set by style on Viralstyle</span></div>
  {trendhtml}
  <ul class="atglance">
   <li><b>Design</b>{esc(_l.title_case_art(it['art']))}</li>
   <li><b>Apparel</b>{style_badge}</li>
   <li><b>Colours</b>{colour_badge}</li>
   <li><b>Sizes</b>{size_badge}</li>
  </ul>
  {shop_now_cta(it, "hero")}
  {cta_note(it, colours)}
  <p class="ctanote flow">Final garment style, colour, size and quantity selection is completed on Viralstyle.</p>
  <div class="badges"><span class="badge">Fan-made, unofficial design</span>
   <span class="badge">Printed on demand</span>
   <span class="badge">US shipping from ${SHIP_US['shippingRate']['value']}</span>
   <span class="badge">30-day misprint replacement</span>
   <span class="badge">Worldwide delivery</span></div>
  <p class="muted small">Jump to: <a href="#colours">colourways</a> &middot;
   <a href="#apparel">apparel</a> &middot; <a href="#story">story</a> &middot;
   <a href="#sizing">sizing</a> &middot; <a href="#faq">FAQ</a></p>
 </div>
</div></div>

<section style="border-top:1px solid var(--line)"><div class="wrap">
 <h2 id="colours">Available Colours</h2>
 <div class="prose" style="max-width:80ch">{colour_html}</div>
 {colourhtml}
</div></section>

<section id="apparel" style="border-top:1px solid var(--line)"><div class="wrap">
 <h2>{_l.apparel_heading(it["garment"])}</h2>
 <div class="prose" style="max-width:80ch">{styles_html}</div>
 {stylehtml}
 <div class="midcta">
  {shop_now_cta(it, "apparel")}
  <p class="ctanote">Choose your garment style, colour and size on Viralstyle before completing your purchase.</p>
 </div>
</div></section>

<section id="story" style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="prose reveal storycopy"><h2>The Idea Behind The Design</h2>{story_html}</div>
</div></section>

<section id="why" style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="prose reveal"><h2>Why It Stands Out</h2>{why_html}</div>
</div></section>

<section id="who" style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="detailcols">
  <div class="panel"><h2 style="margin-top:0">Who It's For</h2>{who_html}</div>
  <div class="panel"><h2 style="margin-top:0">Built for Game Day</h2>{wear_html}</div>
 </div>
 <p class="disclose">{disclose}</p>
</div></section>

<section id="sizing" style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="detailcols">
  <div class="panel"><h2 style="margin-top:0">Size Information</h2>
   <div class="prose" style="max-width:none">{size_html}</div>
   {chart_html}</div>
  <div class="panel"><h2 style="margin-top:0">Product Details</h2>
   <ul class="feat">{bl}</ul></div>
 </div>
</div></section>

<section id="shipping" style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="prose" style="max-width:80ch"><h2>Shipping &amp; Delivery</h2>{ship_html}</div>
</div></section>

<section id="faq" style="border-top:1px solid var(--line)"><div class="wrap">
 <h2>{esc(it['name'])} &ndash; Frequently Asked Questions</h2>
 <div style="max-width:80ch">{faqhtml}</div>
</div></section>

<section class="ctaband"><div class="wrap">
 <div class="ctaband-in">
  <div>
   <span class="eyebrow">Ready to gear up?</span>
   <h2>Get the {esc(it['name'])}</h2>
   <p>{esc(band_line)}</p>
  </div>
  <div class="ctaband-act">
   {shop_now_cta(it, "footer_band")}
   {cta_note(it, colours)}
  </div>
 </div>
</div></section>

<section id="related" style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="sechead"><div><h2>More From {esc(c['short'])}</h2>
  <p>Same collection, same print partner, same hand-off to Viralstyle.</p></div>
  <a class="link col-link" href="/{c['slug']}/" data-collection="{it['col']}">View all {len(MODEL[it['col']])} designs &rarr;</a></div>
 <div class="grid related">{relhtml}</div>
 <div class="linkrow">
  <a class="link col-link" href="/{c['slug']}/" data-collection="{it['col']}">{esc(c['name'])} collection</a>
  <a class="link" href="/collections/">All collections</a>
  <a class="link" href="/guides/{c['slug']}-buying-guide/">{esc(c['short'])} buying guide</a>
  <a class="link" href="/2026-season/">2026 season hub</a>
  <a class="link" href="/drops/">Trending designs</a>
  <a class="link" href="/size-guide/">Size guide</a>
 </div>
</div></section>
</div>

<div class="sticky">
 <span class="p">${price}</span>
 {shop_now_cta(it, "sticky_bar", label="Shop Now", size="", block=False)}
</div></main>"""
    URLS.append((DOMAIN + path, "0.8", "weekly"))
    write(f"shop/{slug}/index.html",
          head(title, metad, path, it["front"], schema, kws, col=it["col"])
          + header(it["col"]) + body + footer())


# ---------------------------------------------------------------- static pages
def simple_page(slug, title, desc, h1, inner, prio="0.5", schema=None, crumb_label=None):
    path = f"/{slug}/" if slug else "/"
    cb, cbs = crumbs([("Home", "/"), (crumb_label or h1, None)], path)
    sc = [cbs] + (schema or [])
    body = f"""{cb}<main id="main"><section style="padding-top:6px"><div class="wrap prose">
 <h1>{esc(h1)}</h1>{inner}</div></section></main>"""
    URLS.append((DOMAIN + path, prio, "monthly"))
    write(f"{slug}/index.html", head(f"{title} | {BRAND}", desc, path, None, sc)
          + header() + body + footer())


def page_static():
    simple_page("size-guide", "Size Guide & Measurements", 
        "Size charts for fan-made tees, hoodies, crewnecks and long sleeves: chest, length and sleeve measurements for sizes S to 3XL, plus how to measure at home.",
        "Size Guide", """
<p>Every apparel item on this site runs <strong>S to 3XL</strong> in a unisex cut unless the design
name says "women's". Measurements below are the garment laid flat, in inches. If you are between
sizes, or you want a relaxed drape, order one size up.</p>
<h2>Unisex t-shirt</h2>
<table><tr><th>Size</th><th>Neck</th><th>Chest width</th><th>Body length</th><th>Sleeve length</th></tr>
<tr><td>S</td><td>17"</td><td>18"</td><td>28"</td><td>8"</td></tr>
<tr><td>M</td><td>17.5"</td><td>20"</td><td>29"</td><td>8.2"</td></tr>
<tr><td>L</td><td>18"</td><td>22"</td><td>30"</td><td>9"</td></tr>
<tr><td>XL</td><td>19"</td><td>24"</td><td>31"</td><td>9.5"</td></tr>
<tr><td>2XL</td><td>20"</td><td>26"</td><td>32"</td><td>10"</td></tr>
<tr><td>3XL</td><td>21"</td><td>28"</td><td>33"</td><td>10.5"</td></tr></table>
<h2>Hoodies and crewneck sweatshirts</h2>
<p>Fleece styles are cut roomier than the tees. Chest width runs roughly 1 inch wider per size and
the body sits about 1 inch longer. Keep your normal size for a classic fit, size down for a slimmer
silhouette, size up if you layer.</p>
<h2>How to measure at home</h2>
<ul>
<li><strong>Body width:</strong> lay the garment flat and measure across the chest 1 inch below the armhole.</li>
<li><strong>Body length:</strong> measure from the centre back neckline seam straight down to the front hem.</li>
<li><strong>Sleeve length:</strong> from the centre back neck to the shoulder seam, then along the edge to the sleeve end.</li>
<li><strong>Best trick:</strong> measure a shirt you already love and match the numbers.</li>
</ul>
<h2>Beanies, mugs and phone cases</h2>
<p>Beanies are one size fits most adults. Mugs are 11 oz ceramic. Phone cases are selected by exact
device model on the Viralstyle product page.</p>
<h2>Care</h2>
<p>Machine wash warm inside out with like colours, non-chlorine bleach only if needed, tumble dry
medium, do not iron directly onto the print. All-over printed items are dye-sublimated, so the
artwork cannot crack or peel.</p>""", "0.6")

    simple_page("shipping", "Shipping & Returns",
        "How print-on-demand shipping works: production times, worldwide delivery, tracking, and "
        "how returns and misprint replacements are handled.",
        "Shipping & Returns", """
<h2>How print on demand works</h2>
<p>Nothing on this site is pre-printed. When you order, the design is printed on the garment you
chose and then shipped. That is why the catalogue can hold hundreds of designs without anything
selling out, and why delivery takes a little longer than warehouse retail.</p>
<h2>Production time</h2>
<p>Most campaigns print within a few business days of the order being placed. Larger campaign runs
close on a set date and print together, which is shown on the Viralstyle product page for that
design.</p>
<h2>Delivery</h2>
<p>Worldwide shipping is available. Domestic US orders typically arrive fastest; international
orders vary by destination and customs. Tracking is issued when the parcel is dispatched.</p>
<h2>Returns, exchanges and misprints</h2>
<p>Because each item is made to order, returns are handled by the fulfilment partner under their
return policy shown on Viralstyle. If an item arrives misprinted, damaged or the wrong size was sent,
contact support with a photo and your order number and it will be replaced.</p>
<h2>Wrong size ordered?</h2>
<p>Check the <a href="/size-guide/">size guide</a> before ordering - it is the single biggest cause
of avoidable exchanges. If you are between sizes, go up.</p>
<h2>Questions</h2>
<p>Send a message via the <a href="/contact/">contact form</a> with your order number and we will chase it for you.</p>""", "0.5")

    faq_items = [
        ("Are these officially licensed NFL or NCAA products?",
         "No. Every design here is independent fan art created by an independent designer. This store "
         "is not affiliated with, endorsed by, sponsored by or licensed by the NFL, any NFL club, the "
         "NCAA, any university or any player. Team, city and player names are used descriptively."),
        ("Where do I actually pay?",
         "On Viralstyle. Gridiron Locker is the storefront and the design library; it never takes "
         "payment. Every Shop Now button opens the Viralstyle product page for that exact design, "
         "where you pick garment style, colour and size and complete checkout."),
        ("What payment methods are accepted?",
         "Major credit and debit cards and PayPal, processed by Viralstyle on their checkout."),
        ("What sizes are available?",
         "S to 3XL on apparel, in unisex and women's cuts depending on the style. Beanies are one "
         "size, mugs are 11 oz, phone cases are chosen by device model."),
        ("How long until it arrives?",
         "A few business days of production, then standard tracked shipping. Delivery is an estimate; "
         "arrival before a specific game is not guaranteed."),
        ("Can I get a design on a different garment?",
         "Many designs are offered on tees, women's cuts, tanks, V-necks, hoodies, crewnecks and long "
         "sleeves. The verified style list for each design is on its product page here, and the "
         "selection itself happens on Viralstyle."),
        ("Do you ship internationally?",
         "Yes, worldwide shipping is available with tracking."),
        ("Can I request a custom design?",
         "Yes - send it through the custom design form on the home page with the idea, the team, the phrase you want and the "
         "garment + size. We handle the artwork and send a quote, usually within 1-2 days. Custom fan "
         "graphics are made to order one at a time."),
    ]
    simple_page("faq", "Frequently Asked Questions",
        "Answers on licensing, sizing, printing, payment, worldwide shipping, returns and custom "
        "design requests for our fan-made football apparel.",
        "Frequently Asked Questions",
        "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq_items),
        "0.6", [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in faq_items]}])

    simple_page("about", "About Us",
        f"{BRAND} is an independent fan-apparel studio making original football graphics for "
        f"Cleveland, Green Bay, Dallas and Michigan supporters. Here is how and why.",
        f"About {BRAND}", f"""
<p><strong>{esc(BRAND)}</strong> is a small independent apparel studio. We design original graphics
for football fan bases and print them on demand, one order at a time.</p>
<p>The catalogue currently holds <strong>{len(ALL)} designs</strong> across four collections:
{", ".join(f'<a href="/{COLLECTIONS[k]["slug"]}/">{COLLECTIONS[k]["name"]}</a>' for k in ORDER)}.</p>
<h2>What we make</h2>
<p>Graphic tees, women's cuts, tanks, V-necks, hoodies, crewneck sweatshirts, all-over printed long
sleeves, knit beanies, ceramic mugs and phone cases. Everything is unisex sized S to 3XL unless
stated.</p>
<h2>How we design</h2>
<p>Every graphic starts with something fans actually say. Dawg Pound. Go Pack Go. Michigan vs
Everybody. Doomsday Defense. We build the typography and illustration around the phrase, not the
other way round, which is why these read from across a stadium concourse.</p>
<h2>Independent and unlicensed - on purpose</h2>
<p>We are not a league store. We do not claim to be. Read our
<a href="/trademark-notice/">trademark notice</a> for the full position.</p>
<h2>Contact</h2>
<p>Send us a note via the <a href="/contact/">contact form</a>. We answer every message.</p>""", "0.5")

    simple_page("trademark-notice", "Trademark & Intellectual Property Notice",
        "Our position on trademarks: independent fan-made artwork, descriptive use of team and city "
        "names, no league affiliation, and our takedown process.",
        "Trademark & Intellectual Property Notice", f"""
<p><strong>{esc(BRAND)} is an independent store.</strong> We are not affiliated with, endorsed by,
sponsored by, approved by or licensed by the National Football League, any NFL member club, the
NCAA, any university, any athletics department, any player or any players' association.</p>
<h2>Descriptive use</h2>
<p>Team names, city names, state names, nicknames and player names appear on this site only to
describe the fan community a design is made for, and to help fans find artwork relevant to them.
No sponsorship, endorsement or affiliation is claimed or implied.</p>
<h2>Ownership of marks</h2>
<p>All trademarks, service marks, team names and logos referenced remain the property of their
respective owners. Any use here is nominative and descriptive.</p>
<h2>Original artwork</h2>
<p>The graphics sold through this site are original works created by independent designers. They are
not reproductions of official league or club merchandise.</p>
<h2>Rights holder? Contact us</h2>
<p>If you own a trademark or copyright and believe a listing infringes it, send a message via the
<a href="/contact/">contact form</a> with the listing URL, the mark or work concerned,
proof of ownership and your contact details. Verified requests are actioned promptly - listings are
removed from this site and the takedown is forwarded to the fulfilment platform.</p>
<h2>Fulfilment</h2>
<p>Orders are fulfilled and payment is processed by a third-party print-on-demand platform, which
operates its own intellectual property policy and takedown procedure.</p>""", "0.4")

    simple_page("privacy", "Privacy Policy",
        "What data this site collects, what it does not, cookies, analytics and third-party checkout.",
        "Privacy Policy", f"""
<p>Last updated {TODAY}.</p>
<h2>What we collect</h2>
<p>This site is a storefront catalogue. It does not take payments and does not collect names,
addresses or card details. If you email us, we hold your message and address only to reply.</p>
<h2>Analytics</h2>
<p>We may use privacy-respecting analytics to count page views and understand which designs are
popular. This uses aggregate data only.</p>
<h2>Third-party checkout</h2>
<p>Buy buttons open a third-party print-on-demand platform. Anything you enter there - name, address,
payment details - is governed by that platform's own privacy policy, not this one.</p>
<h2>Cookies</h2>
<p>No advertising cookies are set by this site. Any cookies set after you click through belong to the
checkout platform.</p>
<h2>Your rights</h2>
<p>Ask via the <a href="/contact/">contact form</a> what we hold about you or to have
it deleted.</p>""", "0.3")

    simple_page("contact", "Contact Us",
        "Get in touch about an order, a sizing question, a custom fan design request or a trademark "
        "concern.", "Contact Us", f"""
<p>We are a small team and we answer every email.</p>
<div class="panel"><h2>Contact form</h2><p>Use the <a href="../#customForm" style="color:var(--accent)">custom design form on the home page</a> - every message lands straight with us.</p>
<p class="muted">Include your order number if your question is about a delivery.</p></div>
<h2>What to contact us about</h2>
<ul>
<li><strong>Order status</strong> - include your order number and the email you checked out with.</li>
<li><strong>Sizing</strong> - tell us your usual size and we will point you at the right one.</li>
<li><strong>Custom designs</strong> - the team, the phrase and the garment you want.</li>
<li><strong>Wholesale or bulk</strong> - team, group and family orders are quoted separately.</li>
<li><strong>Trademark concerns</strong> - see the <a href="/trademark-notice/">trademark notice</a>.</li>
</ul>""", "0.4")


# ---------------------------------------------------------------- guides (SEO articles)
WEEK1_PATH = "/guides/2026-week-1-shirts/"
# Week 1 2026 slate - the public face of DESIGN-BLUEPRINT.md §5b. Ordered by
# kickoff so the earliest game (Michigan, Sept 5) leads. `status` is internal:
# it feeds ops/board and ops/design-drop and is never rendered on a public page.
WEEK1_SLATE = OrderedDict((
    ("michigan", [
        dict(slot="W1-07", slogan="MICHIGAN VS EVERYBODY", garment="Sweatshirt",
             palette="#FFCB05 on #00274C", status="live", sibling="limited-edition-m-fans-n30",
             note="The oldest grudge in the Big Ten, four words long."),
        dict(slot="W1-08", slogan="BET", garment="Tee",
             palette="Maize on navy", status="art", sibling="limited-edition-m-fans-n28",
             note="Three letters, one syllable, zero explanation needed."),
    ]),
    ("cleveland-browns", [
        dict(slot="W1-01", slogan="LET IT RIP", garment="Tee + hoodie",
             palette="#FF6A13 on ink black", status="art", sibling="all-we-want-all-we-got-25",
             note="Quarterback slot - slogan only. No face, no name, no number."),
        dict(slot="W1-02", slogan="NEW ERA", garment="Crewneck + tee",
             palette="Bone on #311D00", status="art", sibling="d-a-w-g-s-limited-edition",
             note="Same slot, second read: a new staff, a new season, new gear."),
    ]),
    ("green-bay-packers", [
        dict(slot="W1-03", slogan="GO PACK GO", garment="Tee",
             palette="#2BAE66 + gold", status="live", sibling="limited-edition-grb5",
             note="The chant, stencilled. Works in September and in January."),
        dict(slot="W1-04", slogan="SUNDAY FUNDAY", garment="Crewneck",
             palette="Cream on forest", status="art", sibling="limited-edition-grb25",
             note="For the 16:25 kickoff that turns into the whole afternoon."),
    ]),
    ("dallas-cowboys", [
        dict(slot="W1-05", slogan="STAR CITY", garment="Tee",
             palette="#8FA0B8 on #0B1B33", status="brief", sibling="vintage-texas-pride",
             note="Texas pride without borrowing anybody's logo."),
        dict(slot="W1-06", slogan="DOOMSDAY", garment="Vintage tee",
             palette="Washed silver", status="live", sibling="doomsday-defense-tee",
             note="One word, distressed, straight out of a 1970s programme."),
    ]),
))
WEEK1_ORDER = list(WEEK1_SLATE)
# Slogan-led kickoff copy for the public page. Deliberately free of player and
# coach names: the Week 1 story is the slogan, not the depth chart.
WEEK1_LINES = {
    "michigan": "The earliest kickoff in the locker, and the first home Saturday of the season.",
    "cleveland-browns": "First road trip of a new season - orange on the road, orange at home.",
    "green-bay-packers": "A late-afternoon divisional kickoff, which in Minnesota means layers.",
    "dallas-cowboys": "Prime time, Sunday night, the biggest stage of Week 1.",
}
# Slogan-led themes. Week 1 picks prefer these over player art: the house rule
# is identity slogans, not player faces (DESIGN-BLUEPRINT.md §1).
WEEK1_THEMES = ("playoff", "city", "retro", "classic", "funny")


def week1_game(se):
    """'Sept 13 at Jacksonville' - strips the 'Week 1 &middot;' prefix cleanly."""
    return se["opener"].split("&middot;")[-1].strip()


def week1_picks(k, n=4):
    """Live sibling designs for a Week 1 slot (DESIGN-BLUEPRINT.md §5c).

    Declared siblings first (so the page matches the drop brief), then
    slogan-led themes, then the rest of the collection. Never returns an empty
    list, so a shopper can never land on an empty grid.
    """
    items = MODEL.get(k) or []
    by_slug = {x["slug"]: x for x in items}
    picks, have = [], set()
    # 1. the sibling each slot declares (keeps the drop brief and the page in sync)
    for slot in WEEK1_SLATE.get(k, []):
        it = by_slug.get(slot.get("sibling"))
        if it and it["slug"] not in have:
            picks.append(it)
            have.add(it["slug"])
    # 2. slogan-led themes
    for x in items:
        if len(picks) >= n:
            break
        if x["theme"] in WEEK1_THEMES and x["slug"] not in have:
            picks.append(x)
            have.add(x["slug"])
    # 3. whatever is left - a Week 1 grid is never empty
    for x in items:
        if len(picks) >= n:
            break
        if x["slug"] not in have:
            picks.append(x)
            have.add(x["slug"])
    return picks[:n]


def week1_sibling(k, i):
    """The live design standing in for Week 1 slot i (ops board / design drop)."""
    picks = week1_picks(k, 4)
    if not picks:
        return None
    return picks[i] if i < len(picks) else picks[0]



def page_week1_graphics():
    """Week 1 2026 public guide: kickoff dates + the slogan graphics to wear."""
    path = WEEK1_PATH
    cb, cbs = crumbs([("Home", "/"), ("Guides", "/guides/"), ("2026 Week 1 Shirts", None)], path)

    rows = ""
    for k in WEEK1_ORDER:
        c, se = COLLECTIONS[k], SEASON[k]
        kick = datetime.date.fromisoformat(se["kickoff"][:10])
        rows += (f'<tr><td><a href="/{c["slug"]}/">{esc(c["short"])}</a></td>'
                 f'<td>{kick.strftime("%a %b")} {kick.day}</td>'
                 f'<td>{esc(week1_game(se))}</td>'
                 f'<td>{" &middot; ".join(esc(s["slogan"]) for s in WEEK1_SLATE[k])}</td></tr>')

    blocks = ""
    for k in WEEK1_ORDER:
        c, se = COLLECTIONS[k], SEASON[k]
        kick = datetime.date.fromisoformat(se["kickoff"][:10])
        slots = WEEK1_SLATE[k]
        chips = "".join(
            f'<span style="display:inline-block;border:1px solid var(--line);'
            f'background:var(--ca-tint);color:var(--ca-ink);'
            f'border-radius:999px;padding:6px 13px;font-size:.74rem;font-weight:700;'
            f'letter-spacing:.05em">{esc(s["slogan"])}</span>' for s in slots)
        notes = "".join(f'<li><strong>{esc(s["slogan"])}</strong> &mdash; {esc(s["note"])} '
                        f'<span class="muted" style="font-size:.8rem">'
                        f'({esc(s["garment"])})</span></li>' for s in slots)
        picks = week1_picks(k, 4)
        blocks += f"""<div class="panel reveal" style="margin-bottom:20px;{theme_vars(k)};
border-top:3px solid var(--ca)">
 <h2 style="color:var(--ca-ink)">{esc(c['short'])} &middot; Week 1 &mdash; {esc(week1_game(se))}</h2>
 <p class="muted" style="margin:0 0 10px">Kickoff {kick.strftime('%A, %b')} {kick.day} &middot;
 {esc(WEEK1_LINES[k])}</p>
 <div class="chips" style="margin:0 0 12px">{chips}</div>
 <p>The Week 1 direction for {esc(c['short'])} is slogan-first &mdash; chant lettering, city and state
 shapes, era marks. No faces, no surnames, no numbers: a slogan outlives a depth chart.</p>
 <ul style="margin:0 0 16px">{notes}</ul>
 <div class="grid">{''.join(card(i) for i in picks)}</div>
 <p style="margin:14px 0 0"><a class="link" href="/{c['slug']}/">All {len(MODEL[k])} {esc(c['short'])} designs &rarr;</a></p>
</div>"""

    faqs = [
        ("When should I order a Week 1 shirt?",
         "Everything is printed after you order it. Delivery is an estimate: 5-12 business days in the US, "
         "with longer international transit possible; arrival before a specific game is not guaranteed."),
        ("Are these shirts officially licensed?",
         "No. Gridiron Locker is an independent, fan-made store. Designs are original artwork that "
         "uses team and city words descriptively to say who a design is for. We are not affiliated "
         "with, endorsed by or licensed by any league, club or university."),
        ("Do the Week 1 designs use player names, faces or numbers?",
         "No. The house rule is identity slogans, not player faces: chants, cities, eras and jokes "
         "in type. That is also why the graphics stay wearable long after a roster changes."),
        ("What size should I buy for a game day layer?",
         "Everything is unisex S to 3XL. Measure a shirt you own flat across the chest and match the "
         "number on the size guide - 18 inches for S through 28 inches for 3XL. Between sizes, or "
         "layering over a hoodie, go up one."),
        ("Can I get a Week 1 slogan on a hoodie, crewneck, beanie or mug?",
         "Yes. Most slogans run across tees, hoodies, crewnecks, long sleeves, beanies and mugs - "
         "each design's product page lists the styles its campaign actually offers, and you pick "
         "the garment and colourway on Viralstyle."),
        ("Do you ship outside the United States?",
         "Yes, worldwide with tracked dispatch. See the shipping page for current estimates before "
         "you order for a specific kickoff date."),
    ]
    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in faqs)
    faq_schema = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q,
                                  "acceptedAnswer": {"@type": "Answer", "text": a}}
                                 for q, a in faqs]}

    next_k = min(WEEK1_ORDER, key=lambda k: SEASON[k]["kickoff"])
    title = "2026 Week 1 Fan Shirts: Kickoff Fits &amp; Slogan Tees"
    desc = ("Week 1 2026 kickoff fits for Michigan, Cleveland, Green Bay and Dallas: kickoff dates, "
            "the slogan tees and crewnecks to order now, sizing and print-on-demand lead times.")
    art = {"@context": "https://schema.org", "@type": "Article",
           "headline": "2026 Week 1 Fan Shirts: Kickoff Fits &amp; Slogan Tees",
           "description": desc, "datePublished": TODAY, "dateModified": DATA_DATE,
           "author": {"@type": "Organization", "name": BRAND},
           "publisher": {"@type": "Organization", "name": BRAND},
           "mainEntityOfPage": DOMAIN + path, "image": DOMAIN + "/img/hero-home.jpg?v=4"}
    body = f"""{cb}<main id="main"><section style="padding-top:6px"><div class="wrap prose">
<h1>{title}</h1>
<p class="muted">Updated {TODAY} &middot; {sum(len(v) for v in WEEK1_SLATE.values())} Week 1 graphics &middot;
{len(ALL)} designs in the locker</p>
<p>Week 1 of the 2026 season lands across two weekends: <strong>Michigan opens on Sept 5</strong>
against Western Michigan, and the NFL Sunday slate kicks off on <strong>Sept 13</strong> with
Cleveland at Jacksonville, Green Bay at Minnesota and Dallas in prime time against the Giants.
Everything below is printed after you order it. Delivery timing is an estimate, and arrival before a specific game is not guaranteed.</p>
<h2>Week 1 at a glance</h2>
<table>
<tr><th>Team</th><th>Kickoff</th><th>Week 1</th><th>Slogan direction</th></tr>
{rows}
</table>
<h2>The Week 1 graphics</h2>
<p>Eight slots, two per team. The rule for every one of them: identity slogans, not player faces.
Chant lettering, city outlines, era marks and one-word statement prints - nothing that needs a
roster move to stay true.</p>
{blocks}
<h2>How a Week 1 graphic gets made</h2>
<p>Each design starts as a slogan, not a photograph. The slogan is set in one accent colour from the
team's palette, printed inside a 12 by 16 inch area on the chest, and checked on the lightest and
darkest garment it will ever be sold on. If it only works on one, it is not finished. Then it is
exported at 4500 by 5400 pixels, 300 dpi, transparent background, and only then does it get a
product page.</p>
<h2>Buying for kickoff</h2>
<p>Pick the garment from the weather first and the graphic second. Early September is still shirt
weather in most places; anything after Thanksgiving is hoodie and crewneck territory. Sizes run
S to 3XL in a unisex cut - see the <a href="/size-guide/">size guide</a> before you order, and
remember that a beanie or a mug is the one gift that cannot be the wrong size.</p>
<p><a class="btn" href="/collections/">Shop every collection &rarr;</a></p>
<h2>Week 1 FAQ</h2>
{faq_html}
<p class="muted" style="font-size:.82rem">Independent fan store. Gridiron Locker is not affiliated
with, endorsed by, sponsored by or licensed by the National Football League, any NFL club, the NCAA,
any university or any player. Team and city names are used descriptively. All artwork is original,
fan-created work.</p>
</div></section></main>"""
    URLS.append((DOMAIN + path, "0.7", "weekly"))
    write("guides/2026-week-1-shirts/index.html",
          head(f"2026 Week 1 Fan Shirts: Kickoff Fits & Slogan Tees | {BRAND}", desc, path,
               "/img/hero-home.jpg?v=4", [cbs, art, faq_schema],
               ["week 1 fan shirt", "2026 week 1 football tee", "kickoff game day shirt",
                "michigan week 1 shirt", "cleveland week 1 shirt", "packers week 1 shirt",
                "dallas week 1 shirt", "slogan football tee"])
          + header() + countdown_bar(next_k) + body + footer())


def page_guides():
    week1_card = ('<div class="panel" style="margin-bottom:14px;border-top:3px solid var(--ink)">'
                  '<h3><a href="/guides/2026-week-1-shirts/">2026 Week 1 Fan Shirts: '
                  'Kickoff Fits &amp; Slogan Tees</a></h3>'
                  '<p class="muted" style="margin:0">Every Week 1 kickoff date, the slogan direction '
                  'for each team and the graphics to order now &mdash; Michigan opens Sept 5, the NFL '
                  'Sunday slate is Sept 13.</p></div>')
    cards = week1_card
    for k in ORDER:
        c = COLLECTIONS[k]
        cards += (f'<div class="panel" style="margin-bottom:14px"><h3><a href="/guides/{c["slug"]}-buying-guide/">'
                  f'The {esc(c["short"])} Fan Apparel Buying Guide</a></h3>'
                  f'<p class="muted" style="margin:0">How to pick between {len(MODEL[k])} designs: sizing, '
                  f'garment styles, gift picks and what each graphic actually says.</p></div>')
    simple_page("guides", "Football Fan Apparel Buying Guides",
        "Buying guides for football fan apparel: how to choose sizes, garment styles and designs for "
        "Cleveland, Green Bay, Dallas and Michigan supporters.",
        "Buying Guides", f"""
<p>Practical guides for picking the right fan piece - written for people buying for themselves and
people buying gifts.</p>
<h2 class="sr-only">Team Buying Guides</h2>{cards}""", "0.6")

    for k in ORDER:
        c = COLLECTIONS[k]
        items = MODEL[k]
        prices = sorted(x["price"] for x in items)
        by_theme = {}
        for i in items:
            by_theme.setdefault(i["theme"], []).append(i)
        secs = ""
        theme_titles = {"player": "Player tribute designs", "funny": "Funny designs",
                        "retro": "Vintage and retro designs", "playoff": "Playoff and big-game designs",
                        "city": "City and state pride designs", "classic": "Classic everyday designs",
                        "family": "Gift designs for family and partners",
                        "halloween": "All-over print statement designs"}
        for t, lst in sorted(by_theme.items(), key=lambda x: -len(x[1])):
            links = "".join(f'<li><a href="{i["url"]}">{esc(i["name"])}</a> - {esc(i["art"][:90])} '
                            f'(${i["price"]:.2f})</li>' for i in lst[:8])
            secs += f"<h2>{theme_titles.get(t, t.title())}</h2><ul>{links}</ul>"
        path = f"/guides/{c['slug']}-buying-guide/"
        cb, cbs = crumbs([("Home", "/"), ("Guides", "/guides/"), (c["short"], None)], path)
        title = f"{c['short']} Fan Apparel Buying Guide {datetime.date.today().year}"
        desc = (f"How to choose from {len(items)} {c['short']} fan designs: sizing, garment styles, "
                f"gift picks and price ranges from ${prices[0]:.2f}.")
        art = {"@context": "https://schema.org", "@type": "Article", "headline": title,
               "description": desc, "datePublished": TODAY, "dateModified": DATA_DATE,
               "author": {"@type": "Organization", "name": BRAND},
               "publisher": {"@type": "Organization", "name": BRAND},
               "mainEntityOfPage": DOMAIN + path, "image": DOMAIN + c["hero"]}
        body = f"""{cb}<section style="padding-top:6px"><div class="wrap prose">
<h1>{esc(title)}</h1>
<p class="muted">Updated {TODAY} &middot; {len(items)} designs reviewed &middot; from ${prices[0]:.2f}</p>
<img src="{c['hero']}" alt="{esc(c['name'])}" style="border-radius:14px;margin:18px 0" loading="lazy" width="1200" height="500">
<p>{esc(c['intro'].format(**c))}</p>
<h2>Start with the garment, not the graphic</h2>
<p>The single most common mistake is falling for a design and then picking the wrong garment. If you
will wear it into a stadium in December, buy the crewneck or hoodie. If it is a September opener or
a watch party indoors, the ring-spun cotton tee is the better call. Mugs and beanies are the safest
gifts because sizing cannot go wrong.</p>
<h2>Then get the size right</h2>
<p>Everything is unisex S to 3XL. Chest width goes 18, 20, 22, 24, 26, 28 inches across the sizes.
Measure a shirt you already own flat across the chest and match the number - see the full
<a href="/size-guide/">size guide</a>. Between sizes? Go up, especially on fleece.</p>
{secs}
<h2>Price range</h2>
<p>This collection runs from <strong>${prices[0]:.2f}</strong> to <strong>${prices[-1]:.2f}</strong>.
Tees sit at the low end, hoodies and all-over prints at the top. Everything is printed after you
order, so there is no clearance rack and no sold-out sizes.</p>
<h2>Buying as a gift</h2>
<p>Pick a design that is not tied to a single player - player-specific graphics age with the roster,
while city, mascot and slogan designs stay wearable for years. If you are unsure of size, a beanie
or mug removes the risk entirely.</p>
<h2>Shop the collection</h2>
<p><a class="btn" href="/{c['slug']}/">Browse all {len(items)} {esc(c['short'])} designs &rarr;</a></p>
</div></section>"""
        URLS.append((DOMAIN + path, "0.7", "monthly"))
        write(f"guides/{c['slug']}-buying-guide/index.html",
              head(f"{title} | {BRAND}", desc, path, c["hero"], [cbs, art], c["keywords"], col=k)
              + header(k) + body + footer())




def page_season():
    path = "/2026-season/"
    cb, cbs = crumbs([("Home", "/"), ("2026 Season", None)], path)
    blocks = ""
    for k in ORDER:
        c, se = COLLECTIONS[k], SEASON[k]
        picks = [x for x in MODEL[k] if x.get("trend") == "hot"][:4] or MODEL[k][:4]
        note = ('<p class="muted">' + esc(se["legacy_note"]) + "</p>") if se["legacy_note"] else ""
        blocks += f"""<div class="panel reveal" style="margin-bottom:20px;border-top:3px solid var(--ca);{theme_vars(k)}">
 <h2 style="color:var(--ca-ink)">{esc(c['short'])} &middot; {esc(se['opener'].replace('&middot;','-'))}</h2>
 <p><strong>{esc(se['headline'])}</strong> {esc(se['status'])}.</p>
 {note}
 <p class="muted" style="font-size:.85rem">Searched this week: {", ".join(esc(x) for x in se['hot'])}</p>
 {fti_block(k, 5)}
 {moments_block(k, limit=4)}
 {headline_block(k, 3)}
 <div class="grid" style="margin-top:14px">{''.join(card(i) for i in picks)}</div>
 <p style="margin-top:16px"><a class="link" href="/{c['slug']}/">All {len(MODEL[k])} {esc(c['short'])} designs &rarr;</a></p>
</div>"""
    desc = ("2026 football season hub: Week 1 dates, what changed on each roster, and the fan shirts "
            "trending right now for Cleveland, Green Bay, Dallas and Michigan supporters.")
    logo = {"@type": "ImageObject", "url": DOMAIN + "/img/hero-home.jpg?v=4"}
    schema = [cbs, {"@context": "https://schema.org", "@type": "Article",
                    "headline": "2026 Season Fan Apparel Hub",
                    "description": desc, "image": DOMAIN + "/img/hero-home.jpg?v=4",
                    "datePublished": TODAY, "dateModified": DATA_DATE,
                    "author": {"@type": "Organization", "name": f"{BRAND} Fan Desk",
                               "url": DOMAIN + path},
                    "publisher": {"@type": "Organization", "name": BRAND, "logo": logo},
                    "mainEntityOfPage": DOMAIN + path}]
    body = f"""{ticker()}<main id="main"><div class="light">{cb}
<section style="padding-top:6px"><div class="wrap">
 <h1>The 2026 Season <span class="accentword">Fan Shirt Hub</span></h1>
 <p class="muted" style="font-size:.85rem;margin-top:8px">By the {BRAND} Fan Desk &middot;
 re-checked daily from live team news &middot; updated {DATA_DATE}</p>
 <p class="muted" style="max-width:72ch">Updated {DATA_DATE}. The NFL season kicks off Wednesday
 <strong>September 9</strong>, with the first full Sunday slate on <strong>September 13</strong>.
 College football starts earlier - Michigan opens <strong>September 5</strong>. Here is what changed
 on each roster this year, and which designs fans are buying because of it.
 See the <a class="link" href="/fan-trend-index/">Fan Trend Index</a> for the 0–100 score behind
 every Trending tag.</p>
 {fti_block(None, 8, heading="Fan Trend Index · all four fanbases")}
 <div style="margin-top:26px">{blocks}</div>
 <div class="prose" style="margin-top:34px">
  <h2>Why roster changes matter when you buy a fan shirt</h2>
  <p>Player-name graphics are the fastest-moving part of any fan wardrobe. A quarterback change can
  turn a best-seller into a closet piece overnight - which is exactly why we retire designs the
  moment a player or coach leaves the roster, and label the live ones <strong>Trending</strong>
  instead of quietly leaving them undated. If you want something that stays wearable for a decade,
  buy city, mascot or slogan artwork: Dawg Pound, Go Pack Go, Michigan vs Everybody and Dallas
  Texas designs never expire.</p>
  <h2>Order timing for Week 1</h2>
  <p>Everything is printed on demand, so allow a few business days for production plus shipping. To
  wear something for the opener, order roughly a week to ten days out. After that, aim for the
  following home game.</p>
  <p><a class="btn" href="/collections/">Shop all collections &rarr;</a></p>
 </div>
</div></section></div></main>"""
    URLS.append((DOMAIN + path, "0.9", "weekly"))
    write("2026-season/index.html",
          head(f"2026 Season Fan Shirt Hub | {BRAND}", desc, path, "/img/hero-home.jpg?v=4", schema,
               [x for k in ORDER for x in SEASON[k]["hot"]])
          + header() + body + footer())


def page_fti():
    """Public Fan Trend Index + live player moments — the news pipeline, scored."""
    path = "/fan-trend-index/"
    cb, cbs = crumbs([("Home", "/"), ("Fan Trend Index", None)], path)
    fti = TRENDS.get("fan_trend_index") or {}
    rows = fti.get("rows") or []
    peak = fti.get("peak_mentions") or 0
    window = fti.get("window_days", 10)
    board = ""
    for i, r in enumerate(rows, 1):
        ckey = r.get("collection")
        c = COLLECTIONS.get(ckey, {})
        tv = theme_vars(ckey) if ckey in COLLECTIONS else ""
        picks = products_for_entity(ckey, r["name"], 2)
        if picks:
            shop = "".join(
                f'<a class="moment-shop" href="{p["url"]}">{esc(p["name"])} · ${p["price"]:.2f}</a>'
                for p in picks)
        elif r.get("gap"):
            shop = ('<span class="fti-gap">Trending — no design in the locker yet. '
                    '<a href="/contact/">Request a custom</a></span>')
        else:
            shop = '<span class="muted">No matching design</span>'
        board += (
            f'<article class="fti-card reveal" style="{tv}">'
            f'<div class="fti-rank">#{i}</div>'
            f'<div class="fti-body">'
            f'<h3>{esc(pretty_name(r["name"]))}</h3>'
            f'<p class="muted">{esc(c.get("short") or ckey)} · {esc(r.get("status") or "")} · '
            f'{int(r["mentions"])} headline mentions</p>'
            f'<div class="fti-bar lg"><i style="width:{int(r["index"])}%"></i></div>'
            f'<div class="fti-scoreline"><b>{int(r["index"])}</b> <span>FTI</span></div>'
            f'<div class="fti-shop">{shop}</div>'
            f'</div></article>')
    gaps = [r for r in rows if r.get("gap")]
    gap_html = ""
    if gaps:
        items = "".join(
            f'<li><strong>{esc(pretty_name(g["name"]))}</strong> '
            f'({esc(COLLECTIONS.get(g.get("collection"), {}).get("short") or "")}) · '
            f'FTI {int(g["index"])}, {int(g["mentions"])} mentions</li>'
            for g in gaps)
        gap_html = (f'<div class="panel" style="margin:22px 0">'
                    f'<h2>Product gaps the news is already writing</h2>'
                    f'<p class="muted">These names cleared the trending bar ({HOT_MIN}+ mentions) '
                    f'and we do not have a design yet. That is the product roadmap, not a slogan.</p>'
                    f'<ul>{items}</ul></div>')
    moments_html = moments_block(None, limit=16)
    desc = (f"Fan Trend Index for Cleveland, Green Bay, Dallas and Michigan — "
            f"0–100 score of who the last {window} days of headlines are actually about, "
            f"plus live player moments tied to shoppable designs.")
    schema = [cbs, {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f"{BRAND} Fan Trend Index",
        "description": desc,
        "url": DOMAIN + path,
        "dateModified": DATA_DATE,
        "creator": {"@type": "Organization", "name": BRAND, "url": DOMAIN},
        "variableMeasured": "Fan Trend Index (0-100 vs peak headline mentions)",
        "measurementTechnique": FTI_FORMULA,
    }, {
        "@context": "https://schema.org", "@type": "ItemList",
        "name": "Fan Trend Index leaderboard",
        "numberOfItems": len(rows),
        "itemListElement": [
            {"@type": "ListItem", "position": n + 1,
             "name": pretty_name(r["name"]),
             "description": f"FTI {int(r['index'])} · {int(r['mentions'])} mentions"}
            for n, r in enumerate(rows[:20])
        ],
    }]
    body = f"""{cb}<main id="main"><div class="light">
<section style="padding-top:6px"><div class="wrap">
 <span class="eyebrow"><span class="dot"></span> Live · {esc(DATA_DATE)} · {window}-day window</span>
 <h1>Fan <span class="accentword">Trend Index</span></h1>
 <p class="muted" style="max-width:72ch">The news pipeline, scored. Every day we pull public
 headlines for Cleveland, Green Bay, Dallas and Michigan, count how often each tracked player
 or coach is named, and turn that count into a 0–100 index against the hottest name in the
 window (peak this run: <strong>{peak} mentions</strong>). Formula:
 <code>{esc(FTI_FORMULA)}</code>. This is the same evidence that tags designs
 <strong>Trending</strong> — now readable as a leaderboard,
 with the headlines (live player moments) attached.</p>
 <div class="stats" style="margin:26px 0 8px">
  <div class="stat"><b>{len(rows)}</b><span>Tracked names</span></div>
  <div class="stat"><b>{peak}</b><span>Peak mentions</span></div>
  <div class="stat"><b>{len(TRENDS.get("moments") or [])}</b><span>Player moments</span></div>
  <div class="stat"><b>{len(gaps)}</b><span>Design gaps</span></div>
 </div>
 <div class="fti-grid" style="margin-top:28px">{board}</div>
 {gap_html}
 <div style="margin-top:28px">{moments_html}</div>
 <div class="prose" style="margin-top:34px">
  <h2>How to read this</h2>
  <p><strong>100</strong> is whoever the headlines named most in the window — not a claim they
  are the best player, the most searched, or the most bought. It is a share-of-voice score
  from the feeds we already crawl. Names at 0 are quiet this window. Names at
  {HOT_MIN}+ mentions get Trending.</p>
  <p>Linked stories belong to their publishers. {esc(BRAND)} is independent fan-made apparel,
  not affiliated with any team, league, university or player.
  <a class="link" href="/2026-season/">Back to the 2026 season hub →</a></p>
 </div>
</div></section></div></main>"""
    URLS.append((DOMAIN + path, "0.8", "daily"))
    write("fan-trend-index/index.html",
          head(f"Fan Trend Index | {BRAND}", desc, path, "/img/hero-home.jpg?v=4", schema,
               ["fan trend index", "nfl player trends 2026", "browns trending players",
                "packers trending players", "michigan football trends"])
          + header() + body + footer())


# ---------------------------------------------------------------- drops — live benefit engine
def page_drops():
    """Public /drops/ page — live trending products with unique headline-aware copy.

    This is the benefit-first page: it catches trending searches (e.g. 'Shedeur Sanders shirt')
    with fresh daily content, unique per-team voices, and real headlines. Google ranks fresh,
    unique, headline-rich pages. Pinterest pins from this feed live for months.
    """
    try:
        from drops_page import page_drops_html
    except Exception as e:
        print(f"drops page generation failed: {e}")
        return
    path = "/drops/"
    cb, cbs = crumbs([("Home", "/"), ("Live Drops", None)], path)

    # Build lookup for full product data
    lookup = {it["slug"]: it for it in ALL}

    drops_body = page_drops_html(COLLECTIONS, ORDER, lookup)

    desc = (f"Today's trending fan drops — live from the headlines. {len(lookup)} designs, "
            f"4 team voices, 0 recycled captions. Updated daily from real team news for "
            f"Cleveland, Green Bay, Dallas and Michigan fans.")

    # Load drops for schema. Same dead-link guard as drops_page.py: only drops
    # whose product page the build actually published may enter the ItemList —
    # schema URLs must never point at delisted pages that 404.
    try:
        drops_data = json.load(open(os.path.join(ROOT, "data/live_drops.json"), encoding="utf-8"))
        drops_list = [d for d in drops_data.get("drops", []) if d.get("slug") in lookup][:12]
    except Exception:
        drops_list = []

    schema = [
        cbs,
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "Today's Trending Fan Drops",
            "description": desc,
            "url": DOMAIN + path,
            "dateModified": TODAY,
            "isPartOf": {"@type": "WebSite", "name": BRAND, "url": DOMAIN},
            "mainEntity": {
                "@type": "ItemList",
                "numberOfItems": len(drops_list),
                "itemListElement": [
                    {"@type": "ListItem", "position": n+1, "url": DOMAIN + f"/shop/{d['slug']}/", "name": d["name"]}
                    for n, d in enumerate(drops_list)
                ],
            },
        },
    ]

    body = f"""{ticker()}<div class="light">{cb}{drops_body}</div>"""

    URLS.append((DOMAIN + path, "0.95", "daily"))
    write("drops/index.html",
          head(f"Today's Trending Fan Drops — Live | {BRAND}", desc, path,
               "/img/hero-home.jpg?v=4", schema,
               ["trending fan shirts", "live drops", "shedeur sanders shirt",
                "browns roster shirt", "michigan miracle shirt", "packers trending",
                "dallas trending shirt", "today's drops", "fan gear trending"])
          + header() + body + footer())


# ---------------------------------------------------------------- extras
def page_404():
    body = """<main id="main"><section><div class="wrap center" style="padding:70px 0">
<h1>Fourth &amp; Long</h1><p class="muted">That page does not exist. Try a collection instead.</p>
<div class="btnrow" style="justify-content:center">
<a class="btn" href="/collections/">All Collections</a>
<a class="btn ghost" href="/">Home</a></div></div></section></main>"""
    write("404.html", head("Page not found | " + BRAND, "The page you requested could not be found. Browse fan-made football apparel across Cleveland, Green Bay, Dallas and Michigan collections at Gridiron Locker.", "/404.html", noindex=True)
          + header() + body + footer())


def assets():
    # The stylesheet is a SOURCE file (src/style.css) copied out on every
    # build. It used to live in site/assets/ and be hand-edited, which meant
    # the only copy of the design lived in the generated directory the refresh
    # workflow rewrites. Emitting it here keeps site/ fully disposable.
    with open(os.path.join(ROOT, "src/style.css"), encoding="utf-8") as fh:
        write("assets/style.css", fh.read())

    # Search index for the sitewide header autocomplete and the /search/
    # catalogue. One compact row per live design, built from the same MODEL
    # that feeds the grids, so re-crawls and delistings propagate on every
    # build. Image paths are root-absolute; the client prefixes the page's
    # data-root (GitHub Pages project URLs included).
    srows = []
    for it in ALL:
        c = COLLECTIONS[it["col"]]
        blob = " ".join([it["name"], it["art"], " ".join(it["kw"] or []),
                         c["name"], c["short"], c["city"], it["garment"], it["theme"]])
        srows.append({"n": it["name"], "u": it["url"], "i": it["front"],
                      "t": it["col"], "ts": c["short"], "g": it["garment"],
                      "p": it["price"], "h": 1 if it.get("trend") == "hot" else 0,
                      "k": blob.lower()})
    write("assets/search-index.json", json.dumps(srows, separators=(",", ":")))

    # Google Search Console HTML verification must be emitted by every build.
    # Keep this alongside the generated assets so a rebuild cannot remove it.
    write("googleae06215486ed6c17.html", "google-site-verification: googleae06215486ed6c17.html")
    write("robots.txt", f"""# {BRAND} - independent fan apparel storefront
# Everything here is meant to be crawled and indexed.

User-agent: *
Disallow: /marketing/plan.json
# ops/ is the private control room (operator board, scout, design drop) - not
# part of the storefront, and never linked from public nav.
Disallow: /ops/
Allow: /

# Product imagery is a ranking asset - let image crawlers in
User-agent: Googlebot-Image
Allow: /img/

User-agent: Bingbot
Allow: /

# AI answer engines (send buyers too)
User-agent: GPTBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: ClaudeBot
Allow: /

# Be gentle, not aggressive
Crawl-delay: 1

Sitemap: {DOMAIN}/sitemap.xml
Sitemap: {DOMAIN}/sitemap-images.xml
""")
    urls = "".join(
        f"<url><loc>{u}</loc><lastmod>{TODAY}</lastmod>"
        f"<changefreq>{cf}</changefreq><priority>{pr}</priority></url>"
        for u, pr, cf in URLS)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>")

    # Image sitemap: associate each product page with every locally hosted product
    # image, allowing Google Images to discover the catalogue independently of
    # the rendered HTML.
    image_urls = []
    for it in ALL:
        seen = set()
        images = []
        for image in it["gallery"]:
            image = abs_url(image)
            if image not in seen:
                seen.add(image)
                images.append(image)
        if images:
            image_urls.append(
                '<url><loc>' + esc(DOMAIN + it["url"]) + '</loc>'
                + ''.join('<image:image><image:loc>' + esc(image) + '</image:loc></image:image>'
                          for image in images)
                + '</url>')
    write("sitemap-images.xml", '<?xml version="1.0" encoding="UTF-8"?>'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
          + ''.join(image_urls) + '</urlset>')
    # Neutral mark: the same near-black square + white glyph as the header
    # logo. The old orange football was the last piece of the retired
    # orange-on-black identity and it clashed with the white storefront.
    write("img/favicon.svg", """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#111418"/>
<ellipse cx="32" cy="32" rx="20" ry="12" fill="#ffffff"/>
<path d="M20 32h24M32 26v12" stroke="#111418" stroke-width="3" stroke-linecap="round"/></svg>""")
    # RSS/Atom feed - a discovery channel search engines and readers poll
    fitems = ""
    for k in ORDER:
        c = COLLECTIONS[k]
        se = SEASON[k]
        link = f"{DOMAIN}/{c['slug']}/"
        desc = (f"{len(MODEL[k])} fan designs for {c['name']}. {se['headline']} "
                f"Trending: {', '.join(se['hot'][:3])}.")
        fitems += (f"<item><title>{esc(c['name'])} - updated {DATA_DATE}</title>"
                   f"<link>{link}</link><guid isPermaLink='false'>{link}#{DATA_DATE}</guid>"
                   f"<description>{esc(desc)}</description></item>")
    for cre in CREATORS.values():
        u = DOMAIN + f"/{cre['page_slug']}/"
        fitems += (f"<item><title>{esc(cre['page_name'])} - updated {DATA_DATE}</title>"
                   f"<link>{u}</link><guid isPermaLink='false'>{u}#{DATA_DATE}</guid>"
                   f"<description>{esc(creator_page_meta(cre))}</description></item>")
    for it in [x for x in ALL if x.get("trend") == "hot"][:12]:
        u = DOMAIN + it["url"]
        fitems += (f"<item><title>{esc(it['name'])}</title><link>{u}</link>"
                   f"<guid isPermaLink='false'>{u}</guid>"
                   f"<description>{esc(it['art'])} - ${it['price']:.2f}</description></item>")
    write("feed.xml", '<?xml version="1.0" encoding="UTF-8"?>'
          '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
          f'<title>{esc(BRAND)} - new and trending fan designs</title>'
          f'<link>{DOMAIN}/</link>'
          '<atom:link rel="hub" href="https://pubsubhubbub.appspot.com"/>'
          f'<description>{esc(CFG["tagline"])}</description>'
          f'<lastBuildDate>{DATA_DATE}</lastBuildDate><language>en-us</language>'
          + fitems + '</channel></rss>')

    # llms.txt - token-efficient brand index for AI answer engines (ChatGPT,
    # Perplexity, Gemini, Claude). Facts + current state + key links: what LLMs
    # can quote and recommend when someone asks "where can I buy a X team shirt".
    hot = [x for x in ALL if x.get("trend") == "hot"]
    featured = (hot or ALL)[:10]
    col_lines = "\n".join(
        f"- [{COLLECTIONS[k]['name']}]({DOMAIN}/{COLLECTIONS[k]['slug']}/) - "
        f"{len(MODEL[k])} fan designs. {SEASON[k]['headline']}" for k in ORDER)
    prod_lines = "\n".join(
        f"- [{it['name']}]({DOMAIN}{it['url']}) - {it['garment']}, ${it['price']:.2f}"
        for it in featured)
    creator_lines = "\n".join(
        f"- [{cre['page_name']}]({DOMAIN}/{cre['page_slug']}/) - creator collaboration: "
        f"{creator_page_meta(cre)}" for cre in CREATORS.values())
    write("llms.txt", f"""# {BRAND}

> {CFG['tagline']} - independent, fan-made football apparel (graphic tees, hoodies,
> crewnecks, beanies, mugs) for Cleveland Browns, Green Bay Packers, Dallas Cowboys
> and Michigan Wolverines fans. Print-on-demand, sizes S-3XL, worldwide shipping.
> Fan-made and independent; not affiliated with any team, league or university.

## Collections
{col_lines}

## Trending now (as of {DATA_DATE}, from live team news)
{prod_lines}

## Key pages
- [Search all designs]({DOMAIN}/search/) - live search + team/garment filters across the full {len(ALL)}-design catalogue
- [2026 Season Hub]({DOMAIN}/2026-season/) - Week 1 dates, roster changes, trending designs
- [Fan Trend Index]({DOMAIN}/fan-trend-index/) - 0-100 score of who the headlines are about, plus live player moments
- [Buying guides]({DOMAIN}/guides/) - how to pick the right fan shirt per team
- [2026 Week 1 fan shirts]({DOMAIN}/guides/2026-week-1-shirts/) - Week 1 kickoff dates (Michigan Sept 5, NFL Sunday Sept 13) and the slogan tees to order
{creator_lines}
- [Custom apparel]({DOMAIN}/contact/) - custom name, colourway and crew orders

## Facts
- {len(ALL)} original designs across 4 collections
- Every design is printed on demand; nothing is warehoused
- Trend tags (Trending) are re-scored daily from public team news
""")

    # IndexNow ownership key (Bing / Yandex / Naver instant submission)
    write(f"{CFG.get('indexnow_key','')}.txt", CFG.get("indexnow_key", ""))

    write("site.webmanifest", json.dumps({
        "name": BRAND, "short_name": BRAND, "start_url": "/", "display": "standalone",
        "background_color": "#0a0b0d", "theme_color": "#0a0b0d",
        "icons": [{"src": "/img/favicon.svg", "sizes": "any", "type": "image/svg+xml"}]}, indent=1))
    write("assets/app.js", """
// ---------- gallery ----------
var CUSTOM_EMAIL="__EMAIL__";
function setStage(b){
  var s=document.getElementById('stage'); if(!s)return;
  if(!b.dataset.src)return;
  s.src=b.dataset.src; s.style.animation='none'; void s.offsetWidth; s.style.animation='';
}
function toggleGroup(sel,me){
  document.querySelectorAll(sel).forEach(function(x){x.classList.remove('on')});
  me.classList.add('on');
}
// Thumbnails only. A product page has no style / size / colour selector by
// design: Gridiron Locker presents the design, Viralstyle configures and sells
// it. The gallery is imagery, not a purchase control.
document.querySelectorAll('.thumb').forEach(function(b){
  b.addEventListener('click',function(){setStage(b);toggleGroup('.thumb',b);});
});

// Colourway mockups are gallery previews, not selectors. Clicking one only
// swaps the stage image; style/colour/size are still chosen on Viralstyle.
document.querySelectorAll('.cwtile').forEach(function(b,i){
  b.addEventListener('click',function(){
    setStage(b);
    try{gtag('event','colorway_interaction',{
      item_id:(document.querySelector('main.pdp-page')||{}).dataset&&document.querySelector('main.pdp-page').dataset.slug,
      index:i+1,destination:'gallery'
    });}catch(e){}
  });
});

// ---------- creator attribution: referral param -> persistent cookie ----------
// Creator collab pages (e.g. Joe's Michigan Locker at /michigan/joe/) send
// visitors through ?creator=<ID>. The first such touch sets a persistent
// cookie (gl_creator, 90-day sliding TTL); while that cookie is present the
// outbound Viralstyle hand-off on ANY page is tagged with creator=<ID> +
// UTM before the click, so an order stays attributed to the creator even
// when the buyer later returns via search, a bookmark or a deep link.
// Commission reconciliation is an off-site exercise (ops/creators) - this
// block is purely the attribution plumbing and never shows a rate to users.
(function(){
  var KEY='gl_creator', TTL=90*86400;
  function setCk(v){try{document.cookie=KEY+'='+encodeURIComponent(v)+'; max-age='+TTL+'; path=/; SameSite=Lax';}catch(e){}}
  function cur(){
    try{var m=document.cookie.match(new RegExp('(?:^|; )'+KEY+'=([^;]*)'));return m?m[1]:'';}catch(e){return ''}
  }
  var p='';
  try{p=(new URLSearchParams(location.search).get('creator')||'').trim().toUpperCase();}catch(e){}
  if(p&&/^[A-Z0-9_-]{1,32}$/.test(p)&&cur()!==p){
    setCk(p);
    try{gtag('event','creator_attribution_set',{creator_id:p,page:location.pathname,referrer:document.referrer||''});}catch(e){}
  }
  var c=cur();
  window.GL_CREATOR=c;
  if(!c)return;
  var onCreatorPage=!!document.body.getAttribute('data-creator-page');
  try{
    gtag('event',onCreatorPage?'creator_page_view':'creator_session',{
      creator_id:onCreatorPage?document.body.getAttribute('data-creator-page'):c,
      page:location.pathname
    });
  }catch(e){}
  // Tag every outbound checkout link (Shop Now on product pages, any direct
  // creator CTA) so the order URL itself carries the attribution.
  var tag='creator='+encodeURIComponent(c)+'&utm_source=creator&utm_medium=referral&utm_campaign=creator-'+encodeURIComponent(c);
  document.querySelectorAll('a[href*="viralstyle.com"]').forEach(function(a){
    var h=a.getAttribute('href');
    if(!h||/[?&](creator|utm_source)=/.test(h))return;
    a.setAttribute('href',h+(h.indexOf('?')<0?'?':'&')+tag);
  });
})();

// ---------- SHOP NOW hand-off tracking ----------
// The only conversion action on a product page. Every button reports its
// placement (hero / apparel / footer_band / sticky_bar) so the metric that
// matters - product landing page -> Viralstyle click-through rate - is
// measurable, and so we can see WHICH CTA earns the click. The creator
// dimension (window.GL_CREATOR, set above from the persistent cookie) is
// attached to every event so attributed vs organic hand-offs split cleanly.
document.querySelectorAll('a.shopnow').forEach(function(a){
  a.addEventListener('click',function(){
    var d=a.dataset||{};
    try{gtag('event','shop_now_click',{
      item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
      collection:d.collection,placement:d.placement,creator:window.GL_CREATOR||'',
      destination:'viralstyle.com'
    });}catch(e){}
    // legacy event name kept so existing GA4 reports do not break
    try{gtag('event','viralstyle_checkout_click',{
      item:d.slug,price:parseFloat(d.price||'0'),collection:d.collection,
      placement:d.placement,creator:window.GL_CREATOR||'',destination:'viralstyle.com'
    });}catch(e){}
    try{gtag('event','viralstyle_redirect',{
      item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
      collection:d.collection,placement:d.placement,creator:window.GL_CREATOR||'',
      destination:'viralstyle.com'
    });}catch(e){}
  });
});

// ---------- product landing analytics ----------
(function(){
  var page=document.querySelector('main.pdp-page');
  if(!page)return;
  var d=page.dataset||{};
  try{gtag('event','product_page_view',{
    item_id:d.slug,value:parseFloat(d.price||'0'),currency:'USD',
    collection:d.collection
  });}catch(e){}
  document.querySelectorAll('#related .related a[href*="/shop/"]').forEach(function(a){
    a.addEventListener('click',function(){
      try{gtag('event','related_product_click',{
        item_id:d.slug,related:a.getAttribute('href'),collection:d.collection
      });}catch(e){}
    });
  });
  document.querySelectorAll('a.col-link').forEach(function(a){
    a.addEventListener('click',function(){
      try{gtag('event','collection_click',{
        item_id:d.slug,collection:a.dataset.collection||d.collection,
        href:a.getAttribute('href')
      });}catch(e){}
    });
  });
})();

// ---------- custom design form (FormSubmit, no backend needed) ----------
// The destination address is assembled at runtime from a base64 token so the
// owner's email never appears in the page source (anti-harvesting).
(function(){
  var form=document.getElementById('customForm'); if(!form)return;
  form.action='https://formsubmit.co/'+atob(CUSTOM_EMAIL);
  var msg=document.getElementById('formmsg');
  var btn=form.querySelector('button[type=submit]');
  form.addEventListener('submit',function(e){
    var name=form.querySelector('input[name=name]').value.trim(),
        email=form.querySelector('input[name=email]').value.trim(),
        idea=form.querySelector('input[name=idea]').value.trim();
    if(!name||!email||!idea){msg.style.color='#c0392b';msg.textContent='Please fill in your name, email and the idea.';e.preventDefault();return;}
    e.preventDefault();
    if(btn)btn.disabled=true;
    if(msg){msg.style.color='';msg.textContent='Sending your idea...';}
    var data=new FormData(form);
    var ok=false;
    try{
      fetch(form.action,{method:'POST',body:data,mode:'no-cors'}).then(function(){
        ok=true;
        if(msg)msg.textContent='Thank you '+name+'! Your idea is on its way. We will reply to '+email+' within 1-2 days.';
        form.reset(); if(btn)btn.disabled=false;
      }).catch(function(){fallback()});
      setTimeout(function(){if(!ok){}},1500);
    }catch(err){fallback()}
    function fallback(){
      // read() tolerates a field that is not on this version of the form -
      // the mailto fallback must never throw, it is the last resort.
      function read(sel){var el=form.querySelector(sel);return el?el.value:'';}
      var body='Name: '+name+'\\nEmail: '+email+'\\nTeam/theme: '+read('select[name=team]')+'\\nGarment: '+read('select[name=garment]')+'\\nIdea: '+idea+'\\nDetails: '+read('textarea[name=details]');
      window.location.href='mailto:'+atob(CUSTOM_EMAIL)+'?subject='+encodeURIComponent('Custom Design Request from '+name)+'&body='+encodeURIComponent(body);
      if(msg)msg.textContent='Opening your email app with your request - hit send and we will get back to you within 1-2 days.';
    }
  });
})();

// ---------- custom shirt popup (once per session, after scroll) ----------
(function(){
  var pop=document.getElementById('csPop');
  if(!pop)return;
  // sessionStorage: show once per browser session, not on every page
  var done;
  try{ done=sessionStorage.getItem('csPopShown'); }catch(e){}
  if(done)return;
  var shown=false;
  function maybeShow(){
    if(shown)return;
    var sc=window.scrollY||0;
    // show once the visitor has scrolled ~ 1.5 viewport heights
    if(sc > (window.innerHeight||800)*1.5){
      shown=true;
      pop.hidden=false;
      requestAnimationFrame(function(){requestAnimationFrame(function(){pop.classList.add('on');});});
      try{ sessionStorage.setItem('csPopShown','1'); }catch(e){}
    }
  }
  window.addEventListener('scroll',maybeShow,{passive:true});
  maybeShow();
  var close=document.getElementById('csPopClose');
  var go=document.getElementById('csPopGo');
  function dismiss(){
    pop.classList.remove('on');
    setTimeout(function(){pop.hidden=true;},350);
  }
  if(close)close.addEventListener('click',dismiss);
  if(go)go.addEventListener('click',function(){
    dismiss();
    var target=document.querySelector('.customsec')||document.querySelector('.customform');
    if(target){target.scrollIntoView({behavior:'smooth',block:'start'});return;}
    // no custom section on this page - send them to the one on the homepage
    location.href=(document.body.getAttribute('data-root')||'./')+'#custom-design';
  });
})();

// ---------- product rails: arrow controls (pointer devices) ----------
// Touch swipes the rail natively; the arrows page it by one viewport-width
// of tiles and disable themselves at each end so they never lie.
(function(){
  var navs=[].slice.call(document.querySelectorAll('.rail-nav'));
  if(!navs.length)return;
  navs.forEach(function(nav){
    var rail=document.getElementById(nav.getAttribute('data-rail'));
    if(!rail)return;
    var btns=[].slice.call(nav.querySelectorAll('.rn'));
    function sync(){
      var max=rail.scrollWidth-rail.clientWidth-2;
      btns.forEach(function(b){
        var back=b.getAttribute('data-dir')==='-1';
        b.disabled = max<=0 || (back ? rail.scrollLeft<=2 : rail.scrollLeft>=max);
      });
    }
    var calm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    btns.forEach(function(b){
      b.addEventListener('click',function(){
        var step=Math.max(240,Math.round(rail.clientWidth*0.86));
        rail.scrollBy({left:step*parseInt(b.getAttribute('data-dir'),10),
                       behavior:calm?'auto':'smooth'});
      });
    });
    rail.addEventListener('scroll',sync,{passive:true});
    window.addEventListener('resize',sync);
    sync();
  });
})();

// ---------- mobile shopping bar (homepage) ----------
// A compact "Shop by team / Trending / All designs" bar so a visitor deep in
// the page never has to scroll back to the header. It appears once the hero
// is gone and hides again over the footer, where the same links already are.
(function(){
  var bar=document.getElementById('mobshop');
  if(!bar)return;
  var hero=document.getElementById('hero'), foot=document.querySelector('footer');
  var nearFooter=false;
  if(foot&&'IntersectionObserver' in window){
    new IntersectionObserver(function(en){
      nearFooter=en[0].isIntersecting; update();
    },{rootMargin:'0px 0px -40% 0px'}).observe(foot);
  }
  function update(){
    var past=(window.scrollY||0) > (hero?hero.offsetHeight*0.75:400);
    var show=past&&!nearFooter;
    if(show===!bar.hidden)return;
    bar.hidden=!show;
    document.body.classList.toggle('has-mobshop',show);
  }
  window.addEventListener('scroll',update,{passive:true});
  window.addEventListener('resize',update);
  update();
})();

// ---------- favourites (device-side, no backend) ----------
(function(){
  var key='gl_favs';
  function read(){ try{return JSON.parse(localStorage.getItem(key)||'[]');}catch(e){return [];} }
  function write(a){ try{localStorage.setItem(key,JSON.stringify(a));}catch(e){} }
  var msg=document.getElementById('favMsg');
  function toast(t){
    if(!msg)return;
    msg.textContent=t; msg.hidden=false; msg.classList.add('on');
    clearTimeout(msg._t); msg._t=setTimeout(function(){msg.classList.remove('on');msg.hidden=true;},1600);
  }
  document.querySelectorAll('.card .fav').forEach(function(b){
    var slug=b.getAttribute('data-slug');
    function draw(){
      var on=read().indexOf(slug)>-1;
      b.classList.toggle('on',on); b.setAttribute('aria-pressed',on?'true':'false');
    }
    draw();
    b.addEventListener('click',function(e){
      e.preventDefault(); e.stopPropagation();
      var a=read(), i=a.indexOf(slug), card=b.closest('.card'),
          nm=card?card.querySelector('h3').textContent:'design';
      if(i>-1){a.splice(i,1); toast('Removed "'+nm+'" from favourites.');}
      else{a.unshift(slug); toast('Saved "'+nm+'" to favourites.');}
      write(a); draw();
    });
  });
})();

// ---------- newsletter signup (FormSubmit, no backend needed) ----------
(function(){
  var form=document.getElementById('newsForm'); if(!form)return;
  form.action='https://formsubmit.co/'+atob(CUSTOM_EMAIL);
  var msg=document.getElementById('newsMsg'), btn=form.querySelector('button');
  form.addEventListener('submit',function(e){
    e.preventDefault();
    var email=form.querySelector('input[name=email]').value.trim();
    if(!email||email.indexOf('@')<1){
      if(msg){msg.style.color='#c0392b';msg.textContent='Please enter a valid email address.';}
      return;
    }
    if(btn)btn.disabled=true;
    if(msg){msg.style.color='';msg.textContent='Joining the locker...';}
    fetch(form.action,{method:'POST',body:new FormData(form),mode:'no-cors'}).then(function(){
      if(msg)msg.textContent='Welcome to the locker. Check your inbox to confirm.';
      form.reset(); if(btn)btn.disabled=false;
    }).catch(function(){
      if(msg)msg.textContent='Almost there - email us directly to join.';
      if(btn)btn.disabled=false;
    });
  });
})();

// ---------- scroll reveal (progressive enhancement: never hide without JS) ----------
// The `.pre` gate is added HERE, at runtime, so content is visible by default:
// if this file is blocked, slow, or an earlier statement throws, nothing is
// ever hidden and the page still paints in full (no white screen). When this
// runs (deferred, before first paint), below-fold elements hide and fade up
// on scroll; in-viewport elements are revealed synchronously in the same task
// so there is no flash.
(function(){
  var els=[].slice.call(document.querySelectorAll('.reveal'));
  if(!els.length)return;
  els.forEach(function(e){e.classList.add('pre')});
  function inView(el){
    try{
      var r=el.getBoundingClientRect(), h=window.innerHeight||800;
      return r.top < h*0.94 && r.bottom > 0;
    }catch(err){return true;}
  }
  var below=[];
  els.forEach(function(e){ if(inView(e)){e.classList.add('in');} else {below.push(e);} });
  if(!below.length)return;
  if(!('IntersectionObserver' in window)){below.forEach(function(e){e.classList.add('in')});return;}
  var io=new IntersectionObserver(function(en){
    en.forEach(function(e,i){
      if(e.isIntersecting){
        var el=e.target;
        setTimeout(function(){el.classList.add('in')}, Math.min(i*70,350));
        io.unobserve(el);
      }
    });
  },{rootMargin:'0px 0px -8% 0px',threshold:.06});
  below.forEach(function(e){io.observe(e)});
  // Safety net: never leave content invisible (slow IO, odd embeds, no scroll).
  setTimeout(function(){
    below.forEach(function(e){e.classList.add('in')});
  },2600);
})();

// ---------- count up ----------
(function(){
  var st=[].slice.call(document.querySelectorAll('[data-count]'));
  if(!st.length||!('IntersectionObserver' in window))return;
  var io=new IntersectionObserver(function(en){
    en.forEach(function(e){
      if(!e.isIntersecting)return;
      var el=e.target,to=parseInt(el.dataset.count,10),t0=null;
      function step(ts){
        if(!t0)t0=ts; var p=Math.min((ts-t0)/1100,1);
        el.textContent=Math.floor(to*(1-Math.pow(1-p,3))).toLocaleString();
        if(p<1)requestAnimationFrame(step);
      }
      requestAnimationFrame(step); io.unobserve(el);
    });
  },{threshold:.4});
  st.forEach(function(e){io.observe(e)});
})();

// ---------- kickoff countdown ----------
(function(){
  var box=document.querySelector('.cd'); if(!box)return;
  var end=new Date(box.dataset.deadline).getTime();
  var d=document.getElementById('cd-d'),h=document.getElementById('cd-h'),
      m=document.getElementById('cd-m'),s=document.getElementById('cd-s');
  function pad(n){return (n<10?'0':'')+n}
  function tick(){
    var gap=end-Date.now();
    if(gap<0){gap=0}
    var dd=Math.floor(gap/864e5),hh=Math.floor(gap%864e5/36e5),
        mm=Math.floor(gap%36e5/6e4),ss=Math.floor(gap%6e4/1e3);
    d.childNodes[0].nodeValue=dd; h.childNodes[0].nodeValue=pad(hh);
    m.childNodes[0].nodeValue=pad(mm); s.childNodes[0].nodeValue=pad(ss);
  }
  tick(); setInterval(tick,1000);
})();


// ---------- sticky header + back to top ----------
(function(){
  var hd=document.querySelector('header'), tt=document.getElementById('totop');
  function on(){
    var y=window.scrollY||0;
    hd&&hd.classList.toggle('stuck',y>10);
    tt&&tt.classList.toggle('on',y>700);
  }
  window.addEventListener('scroll',on,{passive:true}); on();
  tt&&tt.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'})});
})();

// ---------- collection filter / search / sort (team pages + /search/) ----------
// Four independent dimensions: garment (chip[data-f]), team (chip[data-team]),
// style/theme (chip[data-st], read from the card's data-theme attribute) and
// price (#price select). A page only emits the controls it offers, so the
// other dimensions stay at their defaults and behaviour is unchanged.
(function(){
  var grid=document.getElementById('pg'); if(!grid)return;
  var cards=[].slice.call(grid.children);
  var q=document.getElementById('q'), sort=document.getElementById('sort'),
      count=document.getElementById('count'), nores=document.getElementById('nores');
  var typeFilter='all', teamFilter='all', styleFilter='all', priceFilter='any';
  function price(c){return parseFloat(c.querySelector('.price').textContent.replace('$',''))}
  function name(c){return c.querySelector('h3').textContent.toLowerCase()}
  function typeOf(c){return c.getAttribute('data-type')||c.querySelector('.meta').textContent.trim()}
  function teamOf(c){return c.getAttribute('data-team')||''}
  function styleOf(c){return c.getAttribute('data-theme')||''}
  function inPrice(p){
    if(priceFilter==='u20')return p<20;
    if(priceFilter==='20-25')return p>=20&&p<25;
    if(priceFilter==='25-30')return p>=25&&p<30;
    if(priceFilter==='o30')return p>=30;
    return true;
  }
  function apply(){
    var term=(q?q.value:'').toLowerCase().trim(), n=0;
    cards.forEach(function(c){
      var ok=(typeFilter==='all'||typeOf(c)===typeFilter)&&
             (teamFilter==='all'||teamOf(c)===teamFilter)&&
             (styleFilter==='all'||styleOf(c)===styleFilter)&&
             inPrice(price(c))&&
             (!term||c.textContent.toLowerCase().indexOf(term)>-1);
      c.style.display=ok?'':'none'; if(ok){n++;c.classList.add('in');}
    });
    if(count)count.textContent=n+' design'+(n===1?'':'s');
    if(nores)nores.style.display=n?'none':'block';
  }
  function resort(){
    var v=sort.value, arr=cards.slice();
    if(v==='lo')arr.sort(function(a,b){return price(a)-price(b)});
    if(v==='hi')arr.sort(function(a,b){return price(b)-price(a)});
    if(v==='az')arr.sort(function(a,b){return name(a)<name(b)?-1:1});
    arr.forEach(function(c){grid.appendChild(c)});
  }
  function markType(v){document.querySelectorAll('.chip[data-f]').forEach(function(x){
    x.classList.toggle('on',x.getAttribute('data-f')===v);});}
  function markTeam(v){document.querySelectorAll('.chip[data-team]').forEach(function(x){
    x.classList.toggle('on',x.getAttribute('data-team')===v);});}
  function markStyle(v){document.querySelectorAll('.chip[data-st]').forEach(function(x){
    x.classList.toggle('on',x.getAttribute('data-st')===v);});}
  if(q)q.addEventListener('input',apply);
  if(sort)sort.addEventListener('change',resort);
  document.querySelectorAll('.chip[data-f]').forEach(function(b){
    b.addEventListener('click',function(){typeFilter=b.getAttribute('data-f');markType(typeFilter);apply();});
  });
  document.querySelectorAll('.chip[data-team]').forEach(function(b){
    b.addEventListener('click',function(){teamFilter=b.getAttribute('data-team');markTeam(teamFilter);apply();});
  });
  document.querySelectorAll('.chip[data-st]').forEach(function(b){
    b.addEventListener('click',function(){styleFilter=b.getAttribute('data-st');markStyle(styleFilter);apply();});
  });
  var priceSel=document.getElementById('price');
  if(priceSel)priceSel.addEventListener('change',function(){priceFilter=priceSel.value;apply();});
  // Deep links: /search/?q=... (header search + SearchAction), ?t=team,
  // ?g=garment, ?st=style (the landing quick-finder chips deep-link styles)
  var u=new URLSearchParams(location.search), tu=u.get('t'), gu=u.get('g'),
      su=u.get('st'), uq=u.get('q');
  if(gu)typeFilter=gu; if(tu)teamFilter=tu; if(su)styleFilter=su; if(uq&&q)q.value=uq;
  markType(typeFilter); markTeam(teamFilter); markStyle(styleFilter); apply();
})();

// ---------- global design search: live suggestions for every .gsearch ----------
// One shared index (assets/search-index.json) powers the header search on
// every page, the landing-page quick finder and the /search/ page input.
// Suggestions link straight to product pages; "See all results" and Enter
// land on /search/?q=... with the term pre-applied - the same URL the
// SearchAction schema advertises.
(function(){
  var inputs=[].slice.call(document.querySelectorAll('.gsearch'));
  if(!inputs.length)return;
  var ROOT=document.body.getAttribute('data-root')||'./';
  var DATA=null, pend=null;
  function load(){
    if(pend)return pend;
    pend=fetch(ROOT+'assets/search-index.json',{cache:'force-cache'})
      .then(function(r){return r.json()})
      .catch(function(){return null;});
    pend.then(function(d){if(Array.isArray(d))DATA=d;});
    return pend;
  }
  function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');}
  function imgFor(i){return /^https?:/.test(i)?i:ROOT+i;}
  function allUrl(term){return ROOT+'search/?q='+encodeURIComponent(term);}
  function matches(term){
    if(!DATA)return [];
    term=term.toLowerCase();
    var out=[];
    for(var i=0;i<DATA.length;i++){
      var it=DATA[i], n=it.n.toLowerCase(), s=0;
      if(n.indexOf(term)===0)s=3;
      else if(n.indexOf(term)>-1)s=2;
      else if((it.k||'').indexOf(term)>-1)s=1;
      if(s>0)out.push([s,it]);
    }
    out.sort(function(a,b){return b[0]-a[0]||a[1].p-b[1].p;});
    return out.slice(0,8).map(function(x){return x[1];});
  }
  function render(dd,term){
    var list=matches(term);
    var html='';
    for(var i=0;i<list.length;i++){
      var it=list[i];
      html+='<a class="gs-item" href="'+ROOT+it.u+'" data-i="'+i+'">'
           +'<img src="'+imgFor(it.i)+'" alt="" width="40" height="48" loading="lazy">'
           +'<span class="gs-txt"><span class="gs-n">'+esc(it.n)
           +(it.h?' <span class="gs-hot">Trending</span>':'')
           +'</span><span class="gs-m">'+esc(it.ts)+' \u00b7 '+esc(it.g)+' \u00b7 $'+it.p.toFixed(2)+'</span></span></a>';
    }
    html+='<a class="gs-all" href="'+allUrl(term)+'">See all results for \u201c'+esc(term)+'\u201d &rarr;</a>';
    dd.innerHTML=html; dd.hidden=false;
  }
  var pairs=[];
  inputs.forEach(function(inp){
    var wrap=inp.closest('.gs, .navsearch')||inp.parentElement;
    var dd=document.createElement('div');
    dd.className='gs-dd'; dd.hidden=true; dd.setAttribute('role','listbox');
    wrap.appendChild(dd);
    var active=0, pair=null;
    function items(){return [].slice.call(dd.querySelectorAll('.gs-item'));}
    function close(){dd.hidden=true;}
    function markActive(){items().forEach(function(el,i){el.classList.toggle('on',i===active);});}
    function open(){
      var term=inp.value.trim();
      if(term.length<2){close();return;}
      render(dd,term); active=0; markActive();
    }
    function pairClose(){pair&&pair.close();}
    pair={close:close};
    inp.addEventListener('input',open);
    inp.addEventListener('focus',function(){load(); if(inp.value.trim().length>=2)open();});
    inp.addEventListener('keydown',function(e){
      if(e.key==='Escape'){close();return;}
      if(dd.hidden)return;
      if(e.key==='ArrowDown'||e.key==='ArrowUp'){
        e.preventDefault();
        var n=items().length; if(!n)return;
        active=(active+(e.key==='ArrowDown'?1:n-1))%n; markActive();
      } else if(e.key==='Enter'){
        var it=items()[active];
        if(it){e.preventDefault();window.location.href=it.getAttribute('href');}
        else if(inp.value.trim()){e.preventDefault();window.location.href=allUrl(inp.value.trim());}
      }
    });
    inp.addEventListener('blur',function(){setTimeout(function(){dd.hidden=true;},150);});
    dd.addEventListener('mousedown',function(e){e.preventDefault();});
    pairs.push(pair);
  });
  document.addEventListener('mousedown',function(e){
    pairs.forEach(function(p){p.close();});
  });
  // "/" jumps to the header search from anywhere on the page (except while
  // the visitor is already typing in a field).
  document.addEventListener('keydown',function(e){
    if(e.key!=='/')return;
    var t=document.activeElement&&document.activeElement.tagName;
    if(t==='INPUT'||t==='TEXTAREA'||t==='SELECT')return;
    var h=document.querySelector('.navsearch .gsearch')||document.querySelector('.gsearch');
    if(h){e.preventDefault();h.focus();}
  });
  load();
})();

// ---------- quick view: peek at a design without leaving the grid ----------
// Every card carries a .qv button (sibling of the card link, never nested
// inside it). One shared modal is built once and refilled from the card's
// own DOM, so no product data is duplicated across the 127 cards. The CTA
// hands off to the full product landing page; Viralstyle handles checkout.
(function(){
  var qs=[].slice.call(document.querySelectorAll('.card .qv'));
  if(!qs.length)return;
  var modal=document.createElement('div');
  modal.className='qvmodal'; modal.hidden=true;
  modal.innerHTML='<div class="qv-overlay"></div>'
    +'<div class="qv-box" role="dialog" aria-modal="true" aria-label="Quick view">'
    +'<button class="qv-close" type="button" aria-label="Close quick view">&#10005;</button>'
    +'<div class="qv-imgs"><img class="qv-front" alt="" width="150" height="178">'
    +'<img class="qv-back" alt="" width="150" height="178"></div>'
    +'<div class="qv-info"><span class="qv-team"></span><h3 class="qv-name"></h3>'
    +'<span class="qv-meta"></span><span class="qv-price"></span>'
    +'<a class="btn block qv-cta" href="#">See the full design &rarr;</a>'
    +'<p class="muted qv-note">The design story, apparel styles, colours and sizing are on the product page. Orders are completed on Viralstyle.</p>'
    +'</div></div>';
  document.body.appendChild(modal);
  var closeBtn=modal.querySelector('.qv-close');
  function pretty(s){return (s||'').replace(/-/g,' ').replace(/\\b\\w/g,function(ch){return ch.toUpperCase();});}
  function open(card){
    var a=card.querySelector('a'), front=card.querySelector('.ph > img'),
        back=card.querySelector('.ph img.alt'),
        name=card.querySelector('h3'), meta=card.querySelector('.meta'),
        priceEl=card.querySelector('.price');
    if(!a||!front)return;
    var b=modal.querySelector('.qv-back');
    modal.querySelector('.qv-front').src=front.getAttribute('src');
    if(back){b.src=back.getAttribute('src');b.hidden=false;}else{b.hidden=true;}
    modal.querySelector('.qv-name').textContent=name?name.textContent:'';
    modal.querySelector('.qv-team').textContent=pretty(card.getAttribute('data-team'));
    modal.querySelector('.qv-meta').textContent=meta?meta.textContent:'';
    modal.querySelector('.qv-price').textContent=priceEl?priceEl.textContent:'';
    modal.querySelector('.qv-cta').href=a.getAttribute('href');
    modal.hidden=false;
    requestAnimationFrame(function(){modal.classList.add('on');});
    document.body.style.overflow='hidden';
    closeBtn.focus();
  }
  function close(){
    modal.classList.remove('on');
    setTimeout(function(){modal.hidden=true;},220);
    document.body.style.overflow='';
  }
  qs.forEach(function(b){
    b.addEventListener('click',function(e){
      e.preventDefault(); e.stopPropagation();
      open(b.closest('.card'));
    });
  });
  closeBtn.addEventListener('click',close);
  modal.querySelector('.qv-overlay').addEventListener('click',close);
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&!modal.hidden)close();
  });
})();
""".replace("__EMAIL__", CFG["email_b64"]))


RELATIVISE = re.compile(r'(\s(?:href|src|data-src)=")(/(?!/)[^"]*)(")')
RELATIVISE_SRCSET = re.compile(r'(\ssrcset=")([^"]*)(")')


def split_url(url):
    """Split "/path/?q=1#frag" into ("/path/", "?q=1#frag").

    The query/fragment tail must survive relativising untouched, otherwise a
    directory link like "/collections/?q=browns" would have its trailing slash
    appended after the query string.
    """
    cut = len(url)
    for ch in "?#":
        i = url.find(ch)
        if i != -1:
            cut = min(cut, i)
    return url[:cut], url[cut:]


def relativise():
    """Rewrite root-absolute internal links to relative ones so the site works on
    GitHub Pages project URLs (user.github.io/repo/) and at a custom domain.

    Directory links keep their trailing slash ("../collections/") and are never
    expanded to "../collections/index.html". GitHub Pages serves both spellings
    with a 200 and does not redirect one to the other, so emitting the
    index.html form published a second crawlable URL for all 138 pages while
    <link rel="canonical"> pointed at the directory form. Googlebot only ever
    discovers URLs it can follow, so every internally-linked page was the
    non-canonical twin - Search Console reported the site as duplicates
    ("Alternate page with proper canonical tag" / "Duplicate without
    user-selected canonical") and split its ranking signals in half.

    Internal links now match abs_url()/the sitemap exactly, so a crawl finds one
    URL per page. The file:// build, which genuinely needs explicit index.html
    filenames because no server resolves directory indexes there, is produced
    separately by src/make_offline.py.
    """
    n = 0
    for base, _, files in os.walk(SITE):
        for f in files:
            if not f.endswith(".html"):
                continue
            fp = os.path.join(base, f)
            rel_dir = os.path.dirname(os.path.relpath(fp, SITE))
            depth = 0 if rel_dir in ("", ".") else len(rel_dir.split(os.sep))
            prefix = "./" if depth == 0 else "../" * depth

            def repl(m):
                pre, url, post = m.groups()
                path, tail = split_url(url)
                path = path.lstrip("/")
                # A basename with no dot is a page, not a file: canonicalise it
                # to the trailing-slash directory form ("/faq" -> "faq/").
                if path and "." not in os.path.basename(path.rstrip("/")):
                    path = path.rstrip("/") + "/"
                return pre + prefix + path + tail + post

            def repl_srcset(m):
                # srcset="URL [descriptor], ..." - rewrite each root-absolute
                # candidate URL (the homepage hero's responsive image used to
                # keep "/img/..." here, 404ing on project URLs / file://).
                pre, value, post = m.groups()
                out = []
                for chunk in value.split(","):
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    bits = chunk.split()
                    url = bits[0]
                    if url.startswith("/") and not url.startswith("//"):
                        path, tail = split_url(url)
                        url = prefix + path.lstrip("/") + tail
                    bits[0] = url
                    out.append(" ".join(bits))
                return pre + ", ".join(out) + post

            t = open(fp, encoding="utf-8").read()
            t = RELATIVISE.sub(repl, t)
            t = RELATIVISE_SRCSET.sub(repl_srcset, t)
            open(fp, "w", encoding="utf-8").write(t)
            n += 1
    return n


def sync_marketing():
    """Copy the marketing planner into the built site so GitHub Pages publishes
    /marketing/dashboard.html and /marketing/plan.json.

    We copy real files (not a symlink) so the checked-in site/marketing folder is
    always a real directory that the Pages artifact can upload directly, and so a
    rebuild can never swap it for a symlink. The files under site/marketing track
    the marketing/ sources and are committed (deploy.yml uploads ./site as-is)."""
    m_dir = os.path.join(ROOT, "marketing")
    s_m_dir = os.path.join(SITE, "marketing")
    if not os.path.exists(m_dir):
        return
    if os.path.islink(s_m_dir) or os.path.isfile(s_m_dir):
        os.unlink(s_m_dir)
    elif os.path.isdir(s_m_dir):
        shutil.rmtree(s_m_dir)
    shutil.copytree(m_dir, s_m_dir)


def sync_ops():
    """Regenerate and publish the internal ops dashboard: ops/scout -> site/ops.

    Same pattern as sync_marketing(): scout.py writes ops/scout from the live
    data files, we copy the whole ops/ folder into the built site so GitHub
    Pages publishes /ops/scout/. A regeneration failure is non-fatal so the
    storefront rebuild never breaks because of the dashboard.
    """
    try:
        import scout
        scout.main()
    except Exception as e:
        print("ops/scout generation failed, keeping existing files:", e)
        return
    try:
        import hq
        hq.main()
    except Exception as e:
        print("ops/hq generation failed, keeping existing files:", e)
        return
    o_dir = os.path.join(ROOT, "ops")
    s_o_dir = os.path.join(SITE, "ops")
    if not os.path.exists(o_dir):
        return
    if os.path.islink(s_o_dir) or os.path.isfile(s_o_dir):
        os.unlink(s_o_dir)
    elif os.path.isdir(s_o_dir):
        shutil.rmtree(s_o_dir)
    shutil.copytree(o_dir, s_o_dir)


def main():
    page_home()
    page_collections_index()
    page_search()
    for k in ORDER:
        page_collection(k)
    for ckey in CREATORS:
        page_creator(ckey)
    for it in ALL:
        page_product(it)
    page_guides()
    page_week1_graphics()
    page_season()
    page_fti()
    page_drops()
    page_static()
    page_404()
    assets()
    write(".nojekyll", "")
    sync_marketing()
    sync_ops()
    n = relativise()
    print(f"homepage team order (next kickoff first): {', '.join(HOMEPAGE_ORDER)}")
    print(f"relative-linked {n} pages for GitHub Pages / offline")
    print(f"built {len(ALL)} products, {len(ORDER)} collections, {len(URLS)} urls")


if __name__ == "__main__":
    main()
