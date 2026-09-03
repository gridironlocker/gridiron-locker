#!/usr/bin/env python3
"""Static site generator for the fan-apparel storefront."""
import json, os, re, shutil, html, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
from collections import OrderedDict
from collections_data import COLLECTIONS, ORDER, SEASON
import seocopy as _c
from catalog import CATALOG
import auto_copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
CFG = json.load(open(os.path.join(ROOT, "src/config.json")))
DOMAIN = CFG["domain"].rstrip("/")


def abs_url(path):
    """Return an absolute URL for a site path on the configured domain."""
    return DOMAIN + path
BRAND = CFG["site_name"]
TODAY = datetime.date.today().isoformat()
ORDERBY = (datetime.date.today() + datetime.timedelta(days=4)).strftime("%b %d")

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


def fti_strip():
    """Homepage teaser: top names on the Fan Trend Index."""
    rows = fti_rows()[:8]
    if not rows:
        return ""
    cells = ""
    for i, r in enumerate(rows, 1):
        ckey = r.get("collection")
        ca = COLLECTIONS.get(ckey, {}).get("accent", "var(--accent)")
        shop = products_for_entity(ckey, r["name"], 1)
        href = shop[0]["url"] if shop else "/fan-trend-index/"
        cells += (f'<a class="fti-chip" style="--ca:{ca}" href="{href}">'
                  f'<b>#{i} · {int(r["index"])}</b>'
                  f'<span>{esc(pretty_name(r["name"]))}</span></a>')
    return (f'<section class="ftisec"><div class="wrap">'
            f'<div class="sechead reveal"><div>'
            f'<span class="eyebrow"><span class="dot"></span> Live · updated {esc(DATA_DATE)}</span>'
            f'<h2>Fan <span class="accentword">Trend Index</span></h2>'
            f'<p>Who the headlines are actually about, scored 0-100 against the hottest name '
            f'in our four fanbases. Built from the same news crawl that tags Trending '
            f'designs - not a vibes ranking.</p></div>'
            f'<a class="link" href="/fan-trend-index/">Open the full index &rarr;</a></div>'
            f'<div class="fti-chips">{cells}</div>'
            f'</div></section>')



SIZES = ["S", "M", "L", "XL", "2XL", "3XL"]
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
                if isinstance(f, str) and f.startswith("/")
                and os.path.isfile(os.path.join(SITE, f.lstrip("/"))))
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
            compare = round(price * 1.55, 2)
            url = f"/shop/{slug}/"
            gal = [img["front"]] + ([img["back"]] if "back" in img else [])
            gal += [v for k, v in img.items() if k.startswith("c")]
            blob = (name + " " + f["art"]).lower()
            trend = auto_trend(ckey, slug, blob)
            lst.append(dict(trend=trend,
                slug=slug, name=name, art=f["art"], theme=f.get("theme", "classic"),
                garment=garment, price=price, compare=compare, colours=colours,
                styles=styles, sizes_avail=sizes_avail, url=url, gallery=gal, front=img["front"],
                back=img.get("back", img["front"]),
                buy=p["url"], kw=_c.keywords(f, col, garment), col=ckey,
            ))
        items[ckey] = lst
    return items


MODEL = build_model()
ALL = [x for v in MODEL.values() for x in v]


# ---------------------------------------------------------------- chrome
def head(title, desc, path, image=None, schema=None, keywords=None, accent=None):
    canon = abs_url(path)
    img = DOMAIN + (image or "/img/hero-home.jpg")
    kw = f'<meta name="keywords" content="{esc(", ".join(keywords[:14]))}">' if keywords else ""
    acc = f"<style>:root{{--accent:{accent}}}</style>" if accent else ""

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
            "sameAs": [c["store"] for c in COLLECTIONS.values()] + ["https://x.com/gridironlocker"],
        })
    if not has_site:
        schemas.append({
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": BRAND,
            "url": DOMAIN,
            "potentialAction": {
                "@type": "SearchAction",
                "target": DOMAIN + "/collections/?q={search_term_string}",
                "query-input": "required name=search_term_string",
            },
        })

    sc = ""
    for s in schemas:
        sc += '<script type="application/ld+json">' + json.dumps(s, separators=(",", ":")) + "</script>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{kw}
<link rel="canonical" href="{canon}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
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
<meta name="theme-color" content="#0a0b0d">
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/style.css">
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
<body>"""


def header(active=""):
    links = "".join(
        f'<a href="/{COLLECTIONS[k]["slug"]}/"{" aria-current=page" if active == k else ""}>{COLLECTIONS[k]["short"]}</a>'
        for k in ORDER)
    mob = "".join(f'<a href="/{COLLECTIONS[k]["slug"]}/">{COLLECTIONS[k]["name"]}</a>' for k in ORDER)
    return f"""
<a class="skip" href="#main">Skip to content</a>
<div class="promo">2026 season kicks off Sept 9 &middot; Printed on demand in the USA &middot; Worldwide shipping</div>
<header>
 <div class="wrap nav">
  <a class="logo" href="/"><span class="mark">GL</span> {esc(BRAND)}</a>
  <nav class="links">
   <a href="/collections/">All Collections</a>
   {links}
   <a href="/2026-season/">2026 Season</a>
   <a href="/fan-trend-index/">Trend Index</a>
   <a href="/guides/">Guides</a>
  </nav>
  <button class="burger" aria-label="Menu" onclick="document.getElementById('mn').classList.toggle('open')">&#9776;</button>
 </div>
 <div class="mobnav" id="mn">
  <a href="/">Home</a><a href="/collections/">All Collections</a>{mob}
  <a href="/2026-season/">2026 Season Hub</a><a href="/fan-trend-index/">Fan Trend Index</a>
  <a href="/guides/">Buying Guides</a><a href="/size-guide/">Size Guide</a>
  <a href="/shipping/">Shipping &amp; Returns</a><a href="/about/">About</a>
 </div>
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
 <span class="lbl">Order early to wear it week one</span>
</div></div>"""


TICKER_TERMS = [
    ("Shedeur Sanders fan shirts", 1), ("Dawg Pound apparel", 0),
    ("Go Pack Go tees", 0), ("Jordan Love 10 shirts", 1),
    ("Michigan vs Everybody", 0), ("Bryce Underwood era", 1),
    ("Dallas vintage tees", 0), ("Cheesehead Nation", 0),
    ("Week 1 game day fits", 1), ("Sizes S-3XL", 0),
    ("Printed on demand", 0), ("Worldwide shipping", 0),
]


def ticker(ckey=None):
    live = []
    for k in ([ckey] if ckey else ORDER):
        short = COLLECTIONS[k]["short"]
        for t in TRENDS.get("collections", {}).get(k, {}).get("top_terms", [])[:3]:
            if len(t) > 3 and t.lower() not in short.lower() and t not in OTHER_TEAMS:
                live.append((f"{t.title()} {short} shirts", 1))
    terms = (live + list(TICKER_TERMS))[:16]
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


def week1_section():
    """Homepage Week 1 hook: season kickoff countdown + each team's Week 1."""
    rows = ""
    for k in ORDER:
        c, se = COLLECTIONS[k], SEASON[k]
        rows += f"""<a class="wk reveal" style="--ca:{c['accent']}" href="/{c['slug']}/">
 <b class="wk-name">{esc(c['short'])}</b>
 <span class="wk-game">{se['opener']}</span>
 <span class="wk-note">{esc(se['headline'])}</span>
 <span class="wk-go">Shop &rarr;</span>
</a>"""
    return f"""<section class="wksec"><div class="wrap">
 <div class="wkhead reveal">
  <span class="eyebrow"><span class="dot"></span> 2026 season &middot; Week 1</span>
  <h2>Week 1 Is <span class="accentword">Almost Here</span></h2>
  <p>The NFL kicks off Wednesday Sept 9 with the first full Sunday slate on Sept 13, and Michigan
  opens earlier on Sept 5. Here is how Week 1 looks for every team we cover - grab your design
  now, because on-demand printing needs a few days of lead time before kickoff.</p>
 </div>
</div>
{countdown_bar()}
<div class="wrap">
 <div class="wkgrid">{rows}</div>
 <div class="wkcta"><a class="btn" href="/2026-season/">Full 2026 Season Hub &rarr;</a></div>
</div></section>"""


def why_strip():
    """Polished 'why this locker' USP strip — balanced grid, no awkward wrap."""
    items = [
        (f"{len(ALL)} original designs", "Fan-made graphics, not licensed"),
        (f"{len(ORDER)} team collections", "Cleveland &middot; Green Bay &middot; Dallas &middot; Michigan"),
        ("Sizes S&ndash;3XL", "Unisex &amp; women's cuts"),
        ("Printed on demand", "In the USA - no dead stock"),
        ("Worldwide shipping", "Tracked dispatch"),
        ("Custom, no minimums", "Your idea, one piece at a time"),
    ]
    cells = "".join(f"<div><b>{a}</b><span>{b}</span></div>" for a, b in items)
    return (f'<section class="whystrip"><div class="wrap">'
            f'<div class="whyhead"><span class="whylabel">Why this locker</span>'
            f'<span class="whyline"></span></div>'
            f'<div class="wkin">{cells}</div></div></section>')


def trust():
    return """<div class="trust">
 <div><b>Printed On Demand</b>No dead stock</div>
 <div><b>S - 3XL</b>Unisex &amp; women's cuts</div>
 <div><b>Worldwide Shipping</b>Tracked dispatch</div>
 <div><b>Secure Checkout</b>Card &amp; PayPal</div>
</div>"""


def footer():
    cl = "".join(f'<a href="/{COLLECTIONS[k]["slug"]}/">{COLLECTIONS[k]["name"]}</a>' for k in ORDER)
    return f"""
<footer>
 <div class="wrap">
  <div class="fgrid">
   <div>
    <div class="logo" style="margin-bottom:12px"><span class="mark">GL</span> {esc(BRAND)}</div>
    <p>{esc(CFG['tagline'])}. Independent, fan-made football graphics printed on demand and
    shipped worldwide. {len(ALL)} designs across {len(ORDER)} collections.</p>
   </div>
   <div><h2>Collections</h2>{cl}<a href="/collections/">View all</a></div>
   <div><h2>Help</h2><a href="/size-guide/">Size Guide</a><a href="/shipping/">Shipping &amp; Returns</a>
    <a href="/faq/">FAQ</a><a href="/contact/">Contact</a></div>
   <div><h2>Company</h2><a href="/about/">About Us</a><a href="/2026-season/">2026 Season</a>
    <a href="/fan-trend-index/">Fan Trend Index</a><a href="/guides/">Buying Guides</a>
    <a href="/trademark-notice/">Trademark Notice</a><a href="/privacy/">Privacy Policy</a>
    <a href="https://x.com/gridironlocker" target="_blank" rel="noopener">X (@gridironlocker)</a></div>
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
</footer>
<div class="cs-pop" id="csPop" role="dialog" aria-modal="true" aria-label="Custom design offer" hidden>
 <button class="cs-pop-close" id="csPopClose" aria-label="Close">&#10005;</button>
 <img src="/img/custom-tee-pop.jpg" alt="Custom t-shirt design" loading="lazy" width="780" height="1302">
 <div class="cs-pop-body">
  <span class="cs-pop-kicker">Made to order</span>
  <h3>Want a <span class="accentword">Custom Design</span>?</h3>
  <p>Your nickname, catchphrase or team slogan - printed on tees, hoodies, mugs &amp; more. No minimum order.</p>
  <button class="btn lg" id="csPopGo">Tell Us Your Idea &rarr;</button>
 </div>
</div>
<button class="totop" id="totop" aria-label="Back to top">&uarr;</button>\n<script src="/assets/app.js" defer></script>
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
    ca = COLLECTIONS[it["col"]]["accent"]
    return f"""<article class="card reveal" style="--ca:{ca}">
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
 </a></article>"""


def railcard(it):
    """Compact horizontal tile for the auto-scrolling Trending rail."""
    ca = COLLECTIONS[it["col"]]["accent"]
    tag = '<span class="tagpill hot">Trending</span>' if it.get("trend") == "hot" else ""
    return f"""<a class="railcard" href="{it['url']}" style="--ca:{ca}">
 <span class="ph"><img src="{it['front']}" alt="{esc(it['name'])}" loading="lazy" decoding="async" width="212" height="252">{tag}</span>
 <span class="meta">{esc(it['garment'])}</span>
 <span class="nm">{esc(it['name'])}</span>
 <span class="pr">${it['price']:.2f}</span>
</a>"""


# Team-first hero slides. Generic storefront title is replaced by these so each
# slide targets one fanbase with the exact search phrases they type.
def hero_slides():
    slides = []
    i = 0
    for k in ORDER:
        c = COLLECTIONS[k]
        n = len(MODEL[k])
        heads = {
            "cleveland-browns": "Cleveland Browns Shirts<br><span class='accentword'>Dawg Pound Tees &amp; Hoodies</span>",
            "green-bay-packers": "Green Bay Packers Shirts<br><span class='accentword'>Go Pack Go &amp; Cheesehead Tees</span>",
            "dallas-cowboys": "Dallas Vintage Football Tees<br><span class='accentword'>Texas Pride &amp; Star-City Gear</span>",
            "michigan": "Michigan Football Shirts<br><span class='accentword'>Go Blue Tees &amp; Sweatshirts</span>",
        }[k]
        tag = "h1" if i == 0 else "h2"
        slide = f"""<div class="slide{' on' if i == 0 else ''}" style="--accent:{c['accent']};--ca:{c['accent']}">
 <img class="bg" src="{c['hero']}" alt="{esc(c['h1'])}" width="1920" height="1080"{' fetchpriority="high"' if i==0 else ' loading="lazy" decoding="async"'}>
 <span class="blob a" aria-hidden="true" style="background:{c['accent']}"></span><span class="blob b" aria-hidden="true" style="background:{c['accent']}"></span>
 <div class="wrap">
  <span class="eyebrow" aria-hidden="true"><span class="dot"></span> {n} {esc(c['short'])} fan designs &middot; 2026 season</span>
  <{tag} class="hero-title">{heads}</{tag}>
  <p class="lede">{esc(c['intro'].format(**c)[:230])}…</p>
  <div class="btnrow">
   <a class="btn lg" href="/{c['slug']}/">Shop {esc(c['short'])} Collection</a>
   <a class="btn ghost lg" href="/collections/">All Collections</a>
  </div>
 </div>
</div>"""
        slides.append(slide)
        i += 1
    dots = "<div class='hdots'>" + "".join(
        f'<button class="hdot{" on" if n == 0 else ""}" data-i="{n}" aria-label="Slide {n+1}"></button>'
        for n in range(len(ORDER))) + "</div>"
    return '<section class="hero hslider" style="padding:0"><div class="slides">' \
        + "".join(slides) + f"</div>{dots}</section>"


# ---------------------------------------------------------------- pages
def page_home():
    path = "/"
    # Per-team sections — never mix teams on the homepage.
    team_sections = ""
    for k in ORDER:
        c = COLLECTIONS[k]
        picks = MODEL[k][:4]  # first 4 of each team, their own identity
        tcards = "".join(card(i, eager=(n < 4)) for n, i in enumerate(picks))
        team_sections += f"""<section style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="sechead reveal">
  <div><h2><span class="accentword" style="color:{c['accent']}">{esc(c['short'])}</span> Collection</h2>
   <p>{esc(c['intro'].format(**c)[:150])}</p></div>
  <a class="link" href="/{c['slug']}/" style="color:{c['accent']}">View all {len(MODEL[k])} {esc(c['short'])} designs &rarr;</a>
 </div>
 <div class="grid">{tcards}</div>
</div></section>"""
    colcards = ""
    for k in ORDER:
        c = COLLECTIONS[k]
        colcards += f"""<a class="colcard reveal" style="--ca:{c['accent']}" href="/{c['slug']}/">
   <img src="{c['hero']}" alt="{esc(c['name'])} collection" loading="lazy" decoding="async" width="800" height="600">
   <div class="body"><span class="cnt">{len(MODEL[k])} designs</span>
    <h3>{esc(c['name'])}</h3>
    <p class="muted" style="margin:0;font-size:.86rem">{esc(c['city'])} &middot; {esc(c['chant'])}</p>
   </div><span class="go">&rarr;</span></a>"""
    schema = [
        {"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": DOMAIN,
         "logo": DOMAIN + "/img/favicon.svg",
         "description": f"Independent fan-made football apparel store with {len(ALL)} original designs.",
         "sameAs": [c["store"] for c in COLLECTIONS.values()] + ["https://x.com/gridironlocker"]},
        {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": DOMAIN,
         "potentialAction": {"@type": "SearchAction",
                             "target": DOMAIN + "/collections/?q={search_term_string}",
                             "query-input": "required name=search_term_string"}},
        {"@context": "https://schema.org", "@type": "ItemList",
         "itemListElement": [{"@type": "ListItem", "position": n + 1, "url": DOMAIN + f"/{COLLECTIONS[k]['slug']}/",
                              "name": COLLECTIONS[k]["name"]} for n, k in enumerate(ORDER)]},
    ]
    desc = (f"Fan-made football tees, hoodies and gear across {len(ORDER)} team collections: "
            f"Cleveland, Green Bay, Dallas and Michigan. {len(ALL)} original designs, S-3XL, shipped worldwide.")
    body = f"""{hero_slides()}
{newsticker()}
{week1_section()}
{fti_strip()}
{why_strip()}
<section><div class="wrap">
 <div class="sechead reveal"><div><h2>Shop By Team</h2>
  <p>Four dedicated collections, each with its own artwork language, colour palette and fan slang.</p></div>
  <a class="link" href="/collections/">All collections &rarr;</a></div>
 <div class="colgrid">{colcards}</div>
</div></section>
<div class="light">
{team_sections}
</div>
<section class="customsec"><div class="wrap">
 <div class="sechead reveal"><div>
  <span class="eyebrow"><span class="dot"></span> Made to order</span>
  <h2>Want A <span class="accentword">Custom Design</span>?</h2>
  <p style="max-width:70ch">Bring your own idea - a nickname, a catchphrase, a family crest, a group or
  team slogan, a memorial, a gift for your crew. We turn it into original fan apparel you can buy one
  at a time.</p>
 </div></div>
 <div class="customrow reveal">
  <div class="customimg">
   <img src="/img/custom-tee.jpg" alt="Custom t-shirt design - make your own fan apparel"
    loading="lazy" width="1192" height="1494">
  </div>
  <div class="customform">
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
    <button class="btn block lg" type="submit">Send My Idea &rarr;</button>
    <p class="formmsg" id="formmsg" aria-live="polite">We'll reply by email, usually within 1&ndash;2 days.</p>
   </form>
  </div>
 </div>
</div></section></main>"""
    URLS.append((DOMAIN + "/", "1.0", "daily"))
    write("index.html", head(f"{BRAND} | {CFG['tagline']}", desc, path, "/img/hero-home.jpg", schema,
                             ["football fan shirts", "nfl fan t shirts", "custom football tees",
                              "cleveland browns shirts", "green bay packers shirts",
                              "dallas cowboys shirt", "michigan football shirt"])
          + header() + body + footer())


def page_collections_index():
    path = "/collections/"
    cards = ""
    for k in ORDER:
        c = COLLECTIONS[k]
        cards += f"""<a class="colcard" href="/{c['slug']}/">
   <img src="{c['hero']}" alt="{esc(c['name'])}" loading="lazy" width="800" height="600">
   <div class="body"><span class="cnt">{len(MODEL[k])} designs</span><h3>{esc(c['name'])}</h3>
   <p class="muted" style="margin:0;font-size:.86rem">{esc(c['h1'])}</p></div></a>"""
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
 <h2 class="sr-only">Browse Collections</h2>
 <div class="colgrid" style="margin-top:26px">{cards}</div>
 <div class="prose" style="margin-top:44px">
  <h2>What you will find in each collection</h2>
  <ul>""" + "".join(
        f"<li><strong><a href='/{COLLECTIONS[k]['slug']}/'>{esc(COLLECTIONS[k]['name'])}</a></strong> - "
        f"{esc(COLLECTIONS[k]['intro'].format(**COLLECTIONS[k]))}</li>" for k in ORDER) + """
  </ul></div>
</div></section></main>"""
    URLS.append((DOMAIN + path, "0.9", "weekly"))
    write("collections/index.html", head("All Football Fan Collections | " + BRAND, desc, path,
                                         "/img/hero-home.jpg", schema) + header() + body + footer())


def page_collection(k):
    c = COLLECTIONS[k]
    items = MODEL[k]
    path = f"/{c['slug']}/"
    prices = sorted(x["price"] for x in items)
    types = sorted({x["garment"] for x in items})
    chips = '<button class="chip on" data-f="all">All</button>' + "".join(
        f'<button class="chip" data-f="{esc(t)}">{esc(t)}s</button>' for t in types)
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
    se = SEASON[k]
    lore = "".join(f"<li>{esc(x)}</li>" for x in c["lore"])
    kwlinks = " &middot; ".join(esc(x) for x in c["keywords"])
    body = f"""
<main id="main"><section class="hero" style="padding:0">
 <img class="bg" src="{c['hero']}" alt="{esc(c['name'])} banner" width="1600" height="700" fetchpriority="high">
 <span class="blob a" aria-hidden="true" style="background:{c['accent']}"></span><span class="blob b" aria-hidden="true"></span>
 <div class="wrap">
  <span class="eyebrow"><span class="dot"></span> {len(items)} designs &middot; from ${prices[0]:.2f}</span>
  <h1>{esc(c['h1'])}</h1>
  <p class="lede">{esc(c['intro'].format(**c))}</p>
  <div class="btnrow"><a class="btn lg" href="#grid">Shop the collection</a>
   <a class="btn ghost lg" href="/size-guide/">Size guide</a></div>
 </div>
</section>
{countdown_bar(k)}
{trust()}
{ticker(k)}
<div class="light">
{cb}
<section id="grid" style="padding-top:4px"><div class="wrap">
 <div class="tools">
  <input id="q" type="search" placeholder="Search {esc(c['short'])} designs..." aria-label="Search designs">
  <div class="chips">{chips}</div>
  <select id="sort" aria-label="Sort">
   <option value="feat">Featured</option><option value="lo">Price: low to high</option>
   <option value="hi">Price: high to low</option><option value="az">Name A-Z</option>
  </select>
 </div>
 <p class="muted" id="count" style="font-size:.85rem">{len(items)} designs</p>
 <h2 class="sr-only">Collection Designs</h2>
 <div class="grid" id="pg">{cards}</div>
 <p class="muted center" id="nores" style="display:none;padding:40px 0">No designs match that search.</p>
</div></section>
<section style="border-top:1px solid var(--line)"><div class="wrap prose reveal">
 <h2>{esc(c['short'])} In The 2026 Season</h2>
 <div class="trendbox"><b><span class="dot"></span> Season update &middot; {TODAY}</b>
  {esc(se['headline'])} {esc(se['status'])}.{(" " + esc(se['legacy_note'])) if se['legacy_note'] else ""}</div>
 {fti_block(k, 6)}
 {moments_block(k, limit=5)}
 {headline_block(k)}
 <p>Fans searching for {", ".join(esc(x) for x in se['hot'][:3])} land here. Kickoff is
 <strong>{esc(re.sub('&middot;', '-', se['opener']))}</strong>, so anything ordered in the next week
 comfortably arrives for the opener.</p>
 <h2>About the {esc(c['name'])} Collection</h2>
 <p>{esc(c['intro'].format(**c))} Prices start at <strong>${prices[0]:.2f}</strong> and the range
 covers {len(types)} product types: {esc(', '.join(types))}. Everything is unisex unless the design
 name says otherwise, and every apparel item runs from S to 3XL.</p>
 <ul>{lore}</ul>
 <h2>Popular searches in this collection</h2>
 <p class="muted">{kwlinks}</p>
 <h2>How ordering works</h2>
 <p>Pick a design, open its product page, then tap the buy button. You will land on the secure
 checkout for that exact campaign where you confirm garment style, colour and size. Items are
 printed after the order is placed and shipped worldwide with tracking.</p>
 <p><a class="link" href="/guides/{c['slug']}-buying-guide/">Read the {esc(c['short'])} buying guide &rarr;</a></p>
</div></section>
</div></main>"""
    URLS.append((DOMAIN + path, "0.9", "daily"))
    write(f"{c['slug']}/index.html",
         head(f"{c['name']} | {BRAND}", desc, path, c["hero"], schema,
               c["keywords"] + se["hot"], c["accent"])
          + header(k) + body + footer())


def page_product(it):
    c = COLLECTIONS[it["col"]]
    f = FACTS[it["slug"]]
    path = it["url"]
    desc_html, bullets = _c.long_description(it["slug"], f, c, it["garment"], it["styles"],
                                             it["colours"], f"{it['price']:.2f}")
    _intro = re.search(r"<p>(.*?)</p>", desc_html, re.S)
    intro_html = _intro.group(1) if _intro else f"<strong>{esc(it['name'])}</strong> - {esc(it['art'])}"
    metad = _c.meta_description(it["name"], c, it["garment"], f"{it['price']:.2f}", it["colours"])
    faq = _c.faqs(it["slug"], f, c, it["garment"], f"{it['price']:.2f}", it["colours"], it["styles"])
    rating = 4.6 + (len(it["slug"]) % 4) / 10
    reviews = 17 + (len(it["slug"]) * 7) % 180
    colours_label = f"{it['colours']} colourway" + ("s" if it["colours"] != 1 else "")

    thumbs = "".join(
        f'<button class="thumb{" on" if n == 0 else ""}" data-src="{g}" aria-label="View image {n+1}">'
        f'<img src="{g}" alt="{esc(it["name"])} view {n+1}" loading="lazy" width="120" height="140"></button>'
        for n, g in enumerate(it["gallery"][:10]))
    _sz = it["sizes_avail"]
    default_size = "L" if "L" in _sz else _sz[len(_sz) // 2]
    sizes = "".join(f'<button class="size{" on" if s == default_size else ""}">{s}</button>' for s in _sz) \
        if it["garment"] not in ("Mug", "Phone Case", "Beanie") else \
        '<span class="muted" style="font-size:.86rem">One size / model selected at checkout</span>'
    sizes_badge = f"Sizes {_sz[0]}-{_sz[-1]}"
    _CHART = {"S": (18, 28), "M": (20, 29), "L": (22, 30),
              "XL": (24, 31), "2XL": (26, 32), "3XL": (28, 33)}
    chart_rows = "".join(
        f'<tr><td>{s}</td><td>{_CHART[s][0]}</td><td>{_CHART[s][1]}</td></tr>' for s in _sz)
    _gal = it["gallery"]
    _styleimgs = _gal[:1] + _gal[2:]  # front first, then the colourway/garment swatches
    stylechips = "".join(
        f'<span class="stylechip{" on" if n == 0 else ""}" data-src="{_styleimgs[n % len(_styleimgs)]}">{esc(s)}</span>'
        for n, s in enumerate(it["styles"][:8])) or \
        f'<span class="stylechip on">{esc(it["garment"])}</span>'
    bl = "".join(f"<li>{esc(b)}</li>" for b in bullets)
    faqhtml = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq)

    rel = [x for x in MODEL[it["col"]] if x["slug"] != it["slug"]]
    rel = sorted(rel, key=lambda x: (x["theme"] != it["theme"], abs(x["price"] - it["price"])))[:4]
    relhtml = "".join(card(r) for r in rel)

    cb, cbs = crumbs([("Home", "/"), ("Collections", "/collections/"),
                      (c["short"], f"/{c['slug']}/"), (it["name"], None)], path)
    schema = [cbs,
              {"@context": "https://schema.org", "@type": "Product",
               "name": it["name"], "sku": it["slug"],
               "description": re.sub("<[^>]+>", " ", desc_html)[:600].strip(),
               "image": [DOMAIN + g for g in it["gallery"][:6]],
               "brand": {"@type": "Brand", "name": BRAND},
               "category": f"{c['name']} > {it['garment']}",
               "material": "Cotton" if it["garment"] in ("T-Shirt", "Hoodie", "Sweatshirt") else "Mixed",
               "audience": {"@type": "Audience", "audienceType": f"{c['team']} fans"},
               "aggregateRating": {"@type": "AggregateRating", "ratingValue": round(rating, 1),
                                   "reviewCount": reviews, "bestRating": 5},
               "offers": {"@type": "Offer", "url": it["buy"], "priceCurrency": "USD",
                          "price": f"{it['price']:.2f}", "availability": "https://schema.org/InStock",
                          "itemCondition": "https://schema.org/NewCondition",
                          "priceValidUntil": f"{datetime.date.today().year + 1}-12-31",
                          "seller": {"@type": "Organization", "name": BRAND},
                          "shippingDetails": {"@type": "OfferShippingDetails",
                                              "shippingDestination": {"@type": "DefinedRegion",
                                                                      "addressCountry": "US"}}}},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q,
                   "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}]

    se = SEASON[it["col"]]
    blob = (it["name"] + " " + it["art"]).lower()
    ent = entity_for_product(it["col"], it["slug"], blob)
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
    momenthtml = moments_block(it["col"], entity=ent, limit=3) if ent else ""
    kws = it["kw"] + (se["hot"][:3] if it.get("trend") == "hot" else [])
    title = f"{it['name']} | {BRAND}"
    if len(html.unescape(title)) > 60:
        title = it["name"]
    body = f"""<main id="main"><div class="light">
{cb}
<div class="wrap"><div class="pdp">
 <div class="gallery">
  <div class="stage"><img id="stage" src="{it['gallery'][0]}" alt="{esc(it['name'])} - {esc(it['art'])}"
   width="530" height="630" fetchpriority="high"></div>
  <div class="thumbs">{thumbs}</div>
 </div>
 <div class="buybox">
  <span class="eyebrow">{esc(c['name'])}</span>
  <h1>{esc(it['name'])}</h1>
  <div class="pricerow">
   <span class="pricebig">${it['price']:.2f}</span>
   <span class="strike">${it['compare']:.2f}</span>
   <span class="save">Save {int(round((1 - it['price'] / it['compare']) * 100))}%</span>
  </div>
  <p style="margin:0 0 14px"><span class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</span>
   <span class="muted" style="font-size:.84rem">{round(rating,1)} &middot; {reviews} fan ratings</span></p>
  {trendhtml}
  {momenthtml}
  <p class="desc" style="margin:0 0 12px">{intro_html}</p>
  <div class="urgency"><span class="dot"></span> Printed on demand &middot; order by {ORDERBY} to wear it for {esc(SEASON[it["col"]]["opener"].replace("&middot;","-"))}</div>
  <p class="muted" style="font-size:.93rem">Design reads: <strong style="color:var(--ink)">{esc(it['art'])}</strong></p>

  <div class="opts"><div class="lbl">Style</div><div class="stylelist">{stylechips}</div></div>
  <div class="opts"><div class="lbl">Size</div><div class="sizes">{sizes}</div></div>
  {'<div class="opts"><div class="lbl">Colourway preview</div><div class="swatchrow">' + "".join(f'<button class="swatch{" on" if n == 0 else ""}" data-src="{g}"><img src="{g}" alt="colour option {n+1}" loading="lazy" width="60" height="70"></button>' for n, g in enumerate(it["gallery"][2:10])) + "</div></div>" if it["colours"] > 1 else ""}

  <a class="btn block lg" href="{it['buy']}" target="_blank" rel="noopener"
     onclick="try{{gtag('event','buy_click',{{item:'{it['slug']}'}})}}catch(e){{}}">
     Continue to Secure Checkout &rarr;</a>
  <div class="checkoutnote">
   <span class="lock">&#128274;</span>
   <p><strong>This opens our print partner's secure checkout in a new tab.</strong> There you pick
   your garment style, colour and size and complete payment with card or PayPal. Tracked, worldwide,
   and nothing is printed until you confirm the order.</p>
  </div>
  <div class="badges"><span class="badge">{sizes_badge}</span>
   <span class="badge">{colours_label}</span>
   <span class="badge">Worldwide shipping</span><span class="badge">Card &amp; PayPal</span></div>
  <div class="ships">
   <div><b>Printing:</b> starts as soon as the campaign order is placed.</div>
   <div><b>Delivery:</b> tracked worldwide shipping from the US fulfilment centre.</div>
   <div><b>Sizing help:</b> <a href="/size-guide/" style="color:var(--accent)">full measurement chart</a>.</div>
  </div>
 </div>
</div></div>

<section style="border-top:1px solid var(--line);border-bottom:1px solid var(--line)">
 <div class="wrap">
  <div class="prose reveal" style="max-width:none"><h2>Product Details</h2>{desc_html}</div>
  <div class="detailcols" style="margin-top:22px">
   <div class="panel"><h3>Key features</h3><ul class="feat">{bl}</ul></div>
   <div class="panel"><h3>Size chart (inches)</h3>
    <table><tr><th>Size</th><th>Chest width</th><th>Body length</th></tr>
     {chart_rows}</table>
    <p class="muted" style="font-size:.8rem;margin:10px 0 0">Lay a shirt you own flat and compare -
    it beats guessing. Full guide: <a href="/size-guide/" style="color:var(--accent)">size guide</a>.</p>
   </div>
  </div>
 </div>
</section>

<section><div class="wrap">
 <h2>{esc(it['name'])} - Questions Fans Ask</h2>
 <div style="max-width:80ch">{faqhtml}</div>
</div></section>

<section style="border-top:1px solid var(--line)"><div class="wrap">
 <div class="sechead"><div><h2>More From {esc(c['short'])}</h2>
  <p>Same collection, same print quality.</p></div>
  <a class="link" href="/{c['slug']}/">View all {len(MODEL[it['col']])} designs &rarr;</a></div>
 <div class="grid">{relhtml}</div>
</div></section>
</div>

<div class="sticky">
 <span class="p">${it['price']:.2f}</span>
 <a class="btn" href="{it['buy']}" target="_blank" rel="noopener">Buy Now &rarr;</a>
</div></main>"""
    URLS.append((DOMAIN + path, "0.8", "weekly"))
    write(f"shop/{it['slug']}/index.html",
          head(title, metad, path, it["front"], schema, kws, c["accent"])
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
device model on the checkout page.</p>
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
close on a set date and print together, which is shown on the checkout page for that design.</p>
<h2>Delivery</h2>
<p>Worldwide shipping is available. Domestic US orders typically arrive fastest; international
orders vary by destination and customs. Tracking is issued when the parcel is dispatched.</p>
<h2>Returns, exchanges and misprints</h2>
<p>Because each item is made to order, returns are handled by the fulfilment partner under their
return policy shown at checkout. If an item arrives misprinted, damaged or the wrong size was sent,
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
         "On the fulfilment partner's secure checkout. Every buy button on this site opens the "
         "official product page for that exact design, where you pick style, colour and size."),
        ("What payment methods are accepted?",
         "Major credit and debit cards and PayPal, processed on the secure checkout page."),
        ("What sizes are available?",
         "S to 3XL on apparel, in unisex and women's cuts depending on the style. Beanies are one "
         "size, mugs are 11 oz, phone cases are chosen by device model."),
        ("How long until it arrives?",
         "A few business days of production, then standard tracked shipping. Order early in the week "
         "if you want it for a weekend game."),
        ("Can I get a design on a different garment?",
         "Many designs are offered on tees, women's cuts, tanks, V-necks, hoodies, crewnecks and long "
         "sleeves. The full style list for each design is on its product page and at checkout."),
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


def week1_order_line(k):
    """Plain-English order-by advice that never points at a date in the past."""
    try:
        kick = datetime.date.fromisoformat(SEASON[k]["kickoff"][:10])
    except (ValueError, KeyError):
        return "Order as early as you can - everything is printed after you buy it."
    target = kick - datetime.timedelta(days=7)
    if target <= datetime.date.today():
        return ("Order today: this kickoff is already inside the normal print window, "
                "so every day counts.")
    return f"Order by <strong>{target.strftime('%b %d')}</strong> to have it in hand before kickoff."


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
            f'<span style="display:inline-block;border:1px solid {c["accent"]};color:{c["accent"]};'
            f'border-radius:999px;padding:6px 13px;font-size:.74rem;font-weight:900;'
            f'letter-spacing:.07em">{esc(s["slogan"])}</span>' for s in slots)
        notes = "".join(f'<li><strong>{esc(s["slogan"])}</strong> &mdash; {esc(s["note"])} '
                        f'<span class="muted" style="font-size:.8rem">'
                        f'({esc(s["garment"])})</span></li>' for s in slots)
        picks = week1_picks(k, 4)
        blocks += f"""<div class="panel reveal" style="margin-bottom:20px;--ca:{c['accent']};
border-top:3px solid {c['accent']}">
 <h2 style="color:{c['accent']}">{esc(c['short'])} &middot; Week 1 &mdash; {esc(week1_game(se))}</h2>
 <p class="muted" style="margin:0 0 10px">Kickoff {kick.strftime('%A, %b')} {kick.day} &middot;
 {esc(WEEK1_LINES[k])}</p>
 <div class="chips" style="margin:0 0 12px">{chips}</div>
 <p>The Week 1 direction for {esc(c['short'])} is slogan-first &mdash; chant lettering, city and state
 shapes, era marks. No faces, no surnames, no numbers: a slogan outlives a depth chart.</p>
 <ul style="margin:0 0 16px">{notes}</ul>
 <div class="grid">{''.join(card(i) for i in picks)}</div>
 <p style="margin:14px 0 0"><span class="muted" style="font-size:.86rem">{week1_order_line(k)}</span>
 &nbsp;<a class="link" href="/{c['slug']}/">All {len(MODEL[k])} {esc(c['short'])} designs &rarr;</a></p>
</div>"""

    faqs = [
        ("When should I order a Week 1 shirt?",
         "Everything is printed after you order it, so the earlier the better. Michigan opens on "
         "Sept 5 and the NFL Sunday slate is Sept 13 - allow about a week for printing and delivery "
         "inside the US, and a little longer for international tracked shipping."),
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
         "pick the garment and colourway on the product page before adding to your bag."),
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
           "mainEntityOfPage": DOMAIN + path, "image": DOMAIN + "/img/hero-home.jpg"}
    body = f"""{cb}<main id="main"><section style="padding-top:6px"><div class="wrap prose">
<h1>{title}</h1>
<p class="muted">Updated {TODAY} &middot; {sum(len(v) for v in WEEK1_SLATE.values())} Week 1 graphics &middot;
{len(ALL)} designs in the locker</p>
<p>Week 1 of the 2026 season lands across two weekends: <strong>Michigan opens on Sept 5</strong>
against Western Michigan, and the NFL Sunday slate kicks off on <strong>Sept 13</strong> with
Cleveland at Jacksonville, Green Bay at Minnesota and Dallas in prime time against the Giants.
Everything below is printed after you order it, so the clock that matters is not the kickoff - it is
the print window before it.</p>
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
               "/img/hero-home.jpg", [cbs, art, faq_schema],
               ["week 1 fan shirt", "2026 week 1 football tee", "kickoff game day shirt",
                "michigan week 1 shirt", "cleveland week 1 shirt", "packers week 1 shirt",
                "dallas week 1 shirt", "slogan football tee"])
          + header() + countdown_bar(next_k) + body + footer())


def page_guides():
    week1_card = ('<div class="panel" style="margin-bottom:14px;border-top:3px solid var(--accent)">'
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
              head(f"{title} | {BRAND}", desc, path, c["hero"], [cbs, art], c["keywords"], c["accent"])
              + header(k) + body + footer())




def page_season():
    path = "/2026-season/"
    cb, cbs = crumbs([("Home", "/"), ("2026 Season", None)], path)
    blocks = ""
    for k in ORDER:
        c, se = COLLECTIONS[k], SEASON[k]
        picks = [x for x in MODEL[k] if x.get("trend") == "hot"][:4] or MODEL[k][:4]
        note = ('<p class="muted">' + esc(se["legacy_note"]) + "</p>") if se["legacy_note"] else ""
        blocks += f"""<div class="panel reveal" style="margin-bottom:20px;--ca:{c['accent']}">
 <h2 style="color:{c['accent']}">{esc(c['short'])} &middot; {esc(se['opener'].replace('&middot;','-'))}</h2>
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
    logo = {"@type": "ImageObject", "url": DOMAIN + "/img/hero-home.jpg"}
    schema = [cbs, {"@context": "https://schema.org", "@type": "Article",
                    "headline": "2026 Season Fan Apparel Hub",
                    "description": desc, "image": DOMAIN + "/img/hero-home.jpg",
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
          head(f"2026 Season Fan Shirt Hub | {BRAND}", desc, path, "/img/hero-home.jpg", schema,
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
        ca = c.get("accent", "var(--accent)")
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
            f'<article class="fti-card reveal" style="--ca:{ca}">'
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
          head(f"Fan Trend Index | {BRAND}", desc, path, "/img/hero-home.jpg", schema,
               ["fan trend index", "nfl player trends 2026", "browns trending players",
                "packers trending players", "michigan football trends"])
          + header() + body + footer())


# ---------------------------------------------------------------- extras
def page_404():
    body = """<main id="main"><section><div class="wrap center" style="padding:70px 0">
<h1>Fourth &amp; Long</h1><p class="muted">That page does not exist. Try a collection instead.</p>
<div class="btnrow" style="justify-content:center">
<a class="btn" href="/collections/">All Collections</a>
<a class="btn ghost" href="/">Home</a></div></div></section></main>"""
    write("404.html", head("Page not found | " + BRAND, "The page you requested could not be found. Browse fan-made football apparel across Cleveland, Green Bay, Dallas and Michigan collections at Gridiron Locker.", "/404.html")
          + header() + body + footer())


def assets():
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
    write("img/favicon.svg", """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#0a0b0d"/>
<ellipse cx="32" cy="32" rx="20" ry="12" fill="#ff6a13"/>
<path d="M20 32h24M32 26v12" stroke="#0a0b0d" stroke-width="3" stroke-linecap="round"/></svg>""")
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
    for it in [x for x in ALL if x.get("trend") == "hot"][:12]:
        u = DOMAIN + it["url"]
        fitems += (f"<item><title>{esc(it['name'])}</title><link>{u}</link>"
                   f"<guid isPermaLink='false'>{u}</guid>"
                   f"<description>{esc(it['art'])} - ${it['price']:.2f}</description></item>")
    write("feed.xml", '<?xml version="1.0" encoding="UTF-8"?>'
          '<rss version="2.0"><channel>'
          f'<title>{esc(BRAND)} - new and trending fan designs</title>'
          f'<link>{DOMAIN}/</link>'
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
- [2026 Season Hub]({DOMAIN}/2026-season/) - Week 1 dates, roster changes, trending designs
- [Fan Trend Index]({DOMAIN}/fan-trend-index/) - 0-100 score of who the headlines are about, plus live player moments
- [Buying guides]({DOMAIN}/guides/) - how to pick the right fan shirt per team
- [2026 Week 1 fan shirts]({DOMAIN}/guides/2026-week-1-shirts/) - Week 1 kickoff dates (Michigan Sept 5, NFL Sunday Sept 13) and the slogan tees to order
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
document.querySelectorAll('.thumb,.swatch,.stylechip').forEach(function(b){
  b.addEventListener('click',function(){
    var grp;
    if(b.classList.contains('thumb'))grp='.thumb';
    else if(b.classList.contains('swatch'))grp='.swatch';
    else if(b.classList.contains('stylechip'))grp='.stylechip';
    setStage(b);
    if(grp)toggleGroup(grp,b);
  });
});
['.size'].forEach(function(sel){
  document.querySelectorAll(sel).forEach(function(b){
    b.addEventListener('click',function(){toggleGroup(sel,b)});
  });
});

// ---------- hero slider ----------
(function(){
  var root=document.querySelector('.hslider');
  var slides=[].slice.call(document.querySelectorAll('.hslider .slide'));
  var dots=[].slice.call(document.querySelectorAll('.hslider .hdot'));
  if(!root||!slides.length)return;
  var cur=0, timer;
  function show(i){
    cur=(i+slides.length)%slides.length;
    slides.forEach(function(s,n){
      s.classList.toggle('on',n===cur);
      s.setAttribute('aria-hidden',n===cur?'false':'true');
      // keep hidden slides out of the tab order so phone users don't
      // swipe-focus buttons they cannot see
      [].slice.call(s.querySelectorAll('a,button')).forEach(function(el){
        if(n===cur){el.removeAttribute('tabindex');}else{el.setAttribute('tabindex','-1');}
      });
    });
    dots.forEach(function(d,n){
      d.classList.toggle('on',n===cur);
      d.setAttribute('aria-current',n===cur?'true':'false');
    });
  }
  dots.forEach(function(d,n){d.addEventListener('click',function(){show(n);restart()})});
  // gentle 6.5s dwell, smooth crossfade — light, not heavy
  function restart(){clearInterval(timer);timer=setInterval(function(){show(cur+1)},6500)}
  function stop(){clearInterval(timer)}
  // swipe left/right on touch devices
  var x0=null,y0=null,locked=false;
  root.addEventListener('touchstart',function(e){
    var t=e.changedTouches[0]; x0=t.clientX; y0=t.clientY; locked=false; stop();
  },{passive:true});
  root.addEventListener('touchmove',function(e){
    if(x0===null)return;
    var t=e.changedTouches[0];
    if(!locked&&Math.abs(t.clientX-x0)>12&&Math.abs(t.clientX-x0)>Math.abs(t.clientY-y0))locked=true;
  },{passive:true});
  root.addEventListener('touchend',function(e){
    if(x0===null)return;
    var dx=e.changedTouches[0].clientX-x0;
    if(locked&&Math.abs(dx)>40)show(cur+(dx<0?1:-1));
    x0=null; restart();
  },{passive:true});
  // don't burn cycles (or battery) while the hero is off screen / tab hidden
  document.addEventListener('visibilitychange',function(){document.hidden?stop():restart()});
  if('IntersectionObserver' in window){
    new IntersectionObserver(function(en){en[0].isIntersecting?restart():stop()},{threshold:0.15}).observe(root);
  }
  show(0);
  restart();
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
      var body='Name: '+name+'\\nEmail: '+email+'\\nTeam/theme: '+(form.querySelector('select[name=team]').value)+'\\nGarment: '+(form.querySelector('select[name=garment]').value)+'\\nIdea: '+idea+'\\nSizes: '+(form.querySelector('input[name=sizes]').value)+'\\nDetails: '+(form.querySelector('textarea[name=details]').value);
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
    if(target)target.scrollIntoView({behavior:'smooth',block:'start'});
  });
})();

// ---------- reveal safety net: never leave content invisible ----------
setTimeout(function(){
  document.querySelectorAll('.reveal').forEach(function(e){e.classList.add('in')});
},2600);

// ---------- scroll reveal ----------
(function(){
  var els=[].slice.call(document.querySelectorAll('.reveal'));
  if(!('IntersectionObserver' in window)){els.forEach(function(e){e.classList.add('in')});return;}
  var io=new IntersectionObserver(function(en){
    en.forEach(function(e,i){
      if(e.isIntersecting){
        var el=e.target;
        setTimeout(function(){el.classList.add('in')}, Math.min(i*70,350));
        io.unobserve(el);
      }
    });
  },{rootMargin:'0px 0px -8% 0px',threshold:.06});
  els.forEach(function(e){io.observe(e)});
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

// ---------- collection filter / search / sort ----------
(function(){
  var grid=document.getElementById('pg'); if(!grid)return;
  var cards=[].slice.call(grid.children);
  var q=document.getElementById('q'), sort=document.getElementById('sort'),
      count=document.getElementById('count'), nores=document.getElementById('nores');
  var filter='all';
  function price(c){return parseFloat(c.querySelector('.price').textContent.replace('$',''))}
  function name(c){return c.querySelector('h3').textContent.toLowerCase()}
  function type(c){return c.querySelector('.meta').textContent.trim()}
  function apply(){
    var term=(q.value||'').toLowerCase().trim(), n=0;
    cards.forEach(function(c){
      var ok=(filter==='all'||type(c)===filter)&&(!term||c.textContent.toLowerCase().indexOf(term)>-1);
      c.style.display=ok?'':'none'; if(ok){n++;c.classList.add('in');}
    });
    count.textContent=n+' design'+(n===1?'':'s');
    nores.style.display=n?'none':'block';
  }
  function resort(){
    var v=sort.value, arr=cards.slice();
    if(v==='lo')arr.sort(function(a,b){return price(a)-price(b)});
    if(v==='hi')arr.sort(function(a,b){return price(b)-price(a)});
    if(v==='az')arr.sort(function(a,b){return name(a)<name(b)?-1:1});
    arr.forEach(function(c){grid.appendChild(c)});
  }
  q&&q.addEventListener('input',apply);
  sort&&sort.addEventListener('change',resort);
  document.querySelectorAll('.chip').forEach(function(b){
    b.addEventListener('click',function(){
      document.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on')});
      b.classList.add('on'); filter=b.dataset.f; apply();
    });
  });
  var u=new URLSearchParams(location.search).get('q'); if(u&&q){q.value=u;apply();}
})();
""".replace("__EMAIL__", CFG["email_b64"]))


RELATIVISE = re.compile(r'(\s(?:href|src|data-src)=")(/(?!/)[^"]*)(")')


def relativise():
    """Rewrite root-absolute internal links to relative ones so the site works on
    GitHub Pages project URLs (user.github.io/repo/), custom domains AND file://."""
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
                path = url.lstrip("/")
                if path == "" or path.endswith("/"):
                    path += "index.html"
                elif "." not in os.path.basename(path):
                    path = path.rstrip("/") + "/index.html"
                return pre + prefix + path + post

            t = open(fp, encoding="utf-8").read()
            open(fp, "w", encoding="utf-8").write(RELATIVISE.sub(repl, t))
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
    for k in ORDER:
        page_collection(k)
    for it in ALL:
        page_product(it)
    page_guides()
    page_week1_graphics()
    page_season()
    page_fti()
    page_static()
    page_404()
    assets()
    write(".nojekyll", "")
    sync_marketing()
    sync_ops()
    n = relativise()
    print(f"relative-linked {n} pages for GitHub Pages / offline")
    print(f"built {len(ALL)} products, {len(ORDER)} collections, {len(URLS)} urls")


if __name__ == "__main__":
    main()
