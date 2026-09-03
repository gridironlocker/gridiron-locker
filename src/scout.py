#!/usr/bin/env python3
"""Generate the internal ops dashboard at ops/scout (published at /ops/scout/).

Scout is a private, noindex operations view over the same data that powers the
storefront: live trend intelligence (src/trends.py), catalogue health
(products.json vs products_live.json), design gaps, and pipeline freshness.

It is regenerated on every `src/build.py` run (the daily refresh workflow calls
build.py), so the dashboard always reflects the latest crawl + trend data.

Usage:
    python3 src/scout.py            # write ops/scout/index.html + scout.json
"""
import json
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "ops", "scout")


def esc(v):
    return (str(v or "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def load_build():
    """Import the storefront generator in module mode and reuse its model."""
    import build
    return build


def slugify(s):
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def money(v):
    try:
        return "$%.2f" % float(v)
    except (TypeError, ValueError):
        return "-"


def short_date(iso):
    if not iso:
        return "-"
    try:
        return datetime.date.fromisoformat(str(iso)[:10]).strftime("%b %d, %Y")
    except ValueError:
        return str(iso)


def moment_date(pub):
    if not pub:
        return ""
    try:
        d = datetime.datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %Z")
        return d.strftime("%b %d")
    except (ValueError, TypeError):
        try:
            d = datetime.datetime.strptime(pub[:25].strip(), "%a, %d %b %Y %H:%M:%S")
            return d.strftime("%b %d")
        except (ValueError, TypeError):
            return str(pub)[:10]


# ------------------------------------------------------------------ data model
def collect():
    build = load_build()
    TRENDS = build.TRENDS
    COLS = build.COLLECTIONS
    MODEL = build.MODEL
    ALL = build.ALL
    try:
        P_ALL = json.load(open(os.path.join(ROOT, "data/products.json")))
    except Exception:
        P_ALL = {}

    # live products only actually mapped into a collection (skip orphan slugs)
    live_slugs = {it["slug"] for it in ALL}
    # Retired designs are deliberately withheld, not broken - report them apart
    # from dead campaigns so the operator is not chasing phantom crawl failures.
    retired = getattr(build, "RETIRED", {}) or {}
    dead = sorted(set(P_ALL.keys()) - live_slugs - set(retired))
    dead_rows = [
        dict(slug=s, title=P_ALL[s].get("title", ""), url=P_ALL[s].get("url", ""))
        for s in dead
    ]
    retired_rows = [
        dict(slug=s, reason=retired[s],
             title=(P_ALL.get(s) or {}).get("title", ""),
             url=(P_ALL.get(s) or {}).get("url", ""))
        for s in sorted(retired)
    ]

    images = sum(len(it["gallery"]) for it in ALL)
    prices = [it["price"] for it in ALL if isinstance(it.get("price"), (int, float))]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0

    fti_rows = (TRENDS.get("fan_trend_index") or {}).get("rows") or []
    gaps = [r for r in fti_rows if r.get("gap")]
    moments = TRENDS.get("moments") or []

    collections = []
    for ckey in COLS.keys():
        col = COLS[ckey]
        items = MODEL.get(ckey, [])
        tcols = TRENDS.get("collections", {}).get(ckey, {}) or {}
        c_prices = [it["price"] for it in items if isinstance(it.get("price"), (int, float))]
        c_avg = round(sum(c_prices) / len(c_prices), 2) if c_prices else 0
        collections.append(dict(
            key=ckey,
            short=col.get("short", ckey),
            name=col.get("name", ckey),
            slug=col.get("slug", slugify(ckey)),
            store=col.get("store", ""),
            products=len(items),
            avg_price=c_avg,
            hot=sum(1 for it in items if it.get("trend") == "hot"),
            throwback=sum(1 for it in items if it.get("trend") == "throwback"),
            gaps=[g for g in gaps if g.get("collection") == ckey],
            top_terms=(tcols.get("top_terms") or [])[:8],
            headline_count=tcols.get("headline_count", len(tcols.get("headlines") or [])),
            headlines=(tcols.get("headlines") or [])[:5],
            fti_count=len(tcols.get("fan_trend_index") or []),
        ))

    products = []
    for it in ALL:
        col = COLS[it["col"]]
        products.append(dict(
            slug=it["slug"],
            name=it["name"],
            art=it.get("art", ""),
            collection=col.get("short", it["col"]),
            collection_key=it["col"],
            garment=it.get("garment", ""),
            theme=it.get("theme", ""),
            price=it["price"],
            trend=it.get("trend") or "",
            url=it.get("url", ""),
            buy=it.get("buy", ""),
        ))

    payload = dict(
        generated=TRENDS.get("generated"),
        window_days=TRENDS.get("window_days", 10),
        fti_formula=(TRENDS.get("fan_trend_index") or {}).get("formula", ""),
        peak_mentions=(TRENDS.get("fan_trend_index") or {}).get("peak_mentions", 0),
        stats=dict(
            products=len(ALL),
            collections=len(COLS),
            images=images,
            avg_price=avg_price,
            hot=sum(1 for it in ALL if it.get("trend") == "hot"),
            throwback=sum(1 for it in ALL if it.get("trend") == "throwback"),
            steady=sum(1 for it in ALL if not it.get("trend")),
            gaps=len(gaps),
            moments=len(moments),
            tracked_names=len(fti_rows),
            dead_campaigns=len(dead_rows),
            retired=len(retired_rows),
        ),
        fti_rows=fti_rows,
        gaps=[dict(r) for r in gaps],
        collections=collections,
        dead_campaigns=dead_rows,
        retired=retired_rows,
        moments=[
            dict(title=m.get("title"), url=m.get("url"), source=m.get("source"),
                 pub=m.get("pub"), collection=m.get("collection"),
                 entities=m.get("entities") or [])
            for m in moments
        ],
    )
    return (build, payload, products, fti_rows, gaps, moments, collections,
            dead_rows, retired_rows)


# ------------------------------------------------------------------ rendering
def css():
    return """
:root{color-scheme:dark;--ink:#eef5ff;--muted:#93a6c2;--mut2:#c0cfe4;--canvas:#070e1a;
--canvas2:#0b1526;--panel:#0f1e36;--panel2:#142842;--line:rgba(178,203,238,.13);
--line2:rgba(178,203,238,.25);--blue:#7cc8ff;--blue2:#3d9df5;--green:#72e0ba;
--orange:#ffb15a;--pink:#ec9cff;--red:#ff7d7d;
font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;min-width:320px;color:var(--ink);line-height:1.55;
background:radial-gradient(circle at 8% -8%,rgba(61,157,245,.20),transparent 38rem),
radial-gradient(circle at 96% 4%,rgba(114,224,186,.10),transparent 34rem),var(--canvas)}
button,input,select{font:inherit}button{cursor:pointer}a{color:var(--blue);text-decoration:none}
a:hover{color:#c2e7ff}
.topbar{position:sticky;top:0;z-index:20;border-bottom:1px solid var(--line);
background:rgba(7,14,26,.88);backdrop-filter:blur(18px)}
.topbar-inner,.wrap{width:min(1400px,calc(100% - 48px));margin:0 auto}
.topbar-inner{min-height:70px;display:flex;gap:18px;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:12px;font-weight:800;letter-spacing:-.02em}
.mark{display:grid;place-items:center;width:36px;height:36px;border-radius:11px;
color:#05121f;background:linear-gradient(135deg,var(--blue),var(--green));font-weight:850}
.brand small{display:block;font-weight:600;color:var(--muted);letter-spacing:.14em;
text-transform:uppercase;font-size:.62rem}
.pill{display:inline-flex;align-items:center;gap:7px;padding:7px 13px;border:1px solid var(--line2);
border-radius:999px;color:var(--mut2);background:rgba(255,255,255,.03);font-size:.8rem;white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green)}
section{padding:46px 0 10px}
h1{margin:0 0 10px;font-size:clamp(1.6rem,3.4vw,2.5rem);letter-spacing:-.03em;line-height:1.15}
h2{margin:0 0 6px;font-size:1.25rem;letter-spacing:-.02em}
h3{font-size:.95rem;margin:0 0 10px;letter-spacing:-.01em}
.lead{color:var(--muted);max-width:76ch;margin:0 0 22px}
.muted{color:var(--muted)} .small{font-size:.8rem} .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi{border:1px solid var(--line);border-radius:16px;padding:16px 18px;background:linear-gradient(180deg,var(--panel),var(--canvas2))}
.kpi b{display:block;font-size:1.7rem;line-height:1.1;letter-spacing:-.03em}
.kpi span{color:var(--muted);font-size:.78rem}
.grid2{display:grid;grid-template-columns:1.35fr 1fr;gap:22px}
@media(max-width:980px){.grid2{grid-template-columns:1fr}}
.card{border:1px solid var(--line);border-radius:18px;background:var(--panel);padding:20px 22px;
box-shadow:0 14px 44px rgba(0,0,0,.22)}
.card + .card{margin-top:22px}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th{color:var(--muted);font-weight:650;text-align:left;padding:9px 10px;border-bottom:1px solid var(--line2);
font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:middle}
tr:hover td{background:rgba(124,200,255,.045)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.bar{display:flex;align-items:center;gap:8px;min-width:130px}
.bar i{display:block;height:7px;border-radius:99px;background:linear-gradient(90deg,var(--blue2),var(--blue))}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.7rem;font-weight:700;
letter-spacing:.03em;text-transform:uppercase;border:1px solid transparent}
.trending{color:#062b1c;background:var(--green)}.steady{color:#04121f;background:var(--blue)}
.quiet{color:#0a1423;background:var(--pink)}.gap{color:#26180a;background:var(--orange)}
.dead{color:#2b0f0f;background:var(--red)}
.colcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
.colcard{border:1px solid var(--line);border-radius:18px;background:var(--panel);padding:18px 20px}
.colcard h3{font-size:1.02rem}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.chip{padding:3px 9px;border-radius:999px;border:1px solid var(--line2);color:var(--mut2);font-size:.7rem;background:rgba(255,255,255,.02)}
.calls{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.call{border:1px solid rgba(255,177,90,.4);border-radius:14px;padding:13px 15px;background:rgba(255,177,90,.06)}
.call b{color:var(--orange)}
.moments{display:flex;flex-direction:column;gap:12px}
.moment{display:flex;gap:12px;align-items:flex-start;padding:11px 13px;border:1px solid var(--line);border-radius:13px;background:rgba(255,255,255,.018)}
.moment .meta{color:var(--muted);font-size:.76rem;margin-top:3px}
.tools{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
input,select{background:var(--canvas2);border:1px solid var(--line2);color:var(--ink);
border-radius:11px;padding:9px 12px;outline:none}
input:focus,select:focus{border-color:var(--blue2)}
input[type=search]{flex:1;min-width:200px}
details{margin-top:14px;border:1px solid var(--line);border-radius:12px;padding:10px 14px;background:rgba(255,255,255,.015)}
summary{cursor:pointer;color:var(--mut2);font-size:.82rem}
pre{overflow:auto;max-height:420px;font-size:.72rem;color:var(--mut2)}
footer{padding:40px 0 56px;color:var(--muted);font-size:.8rem;border-top:1px solid var(--line);margin-top:40px}
footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
.kbd{font-family:ui-monospace,monospace;background:rgba(255,255,255,.06);padding:1px 6px;border-radius:6px;font-size:.78em}
.stash{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px}
.stash a{color:var(--mut2)}
"""


def kpi_card(value, label):
    return f'<div class="kpi"><b>{value}</b><span>{label}</span></div>'


def status_badge(trend):
    if trend == "hot":
        return '<span class="badge trending">Trending</span>'
    if trend == "throwback":
        return '<span class="badge quiet">Throwback</span>'
    return '<span class="badge steady">Steady</span>'


def design_badge(r, build):
    if r.get("gap"):
        return '<span class="badge gap">GAP - no design</span>'
    try:
        shop = build.products_for_entity(r.get("collection"), r["name"], 1)
    except Exception:
        shop = []
    if shop:
        return (f'<a class="badge steady" style="text-decoration:none" '
                f'href="{esc(shop[0]["url"])}">In locker - {esc(money(shop[0]["price"]))}</a>')
    return '<span class="badge steady">In locker</span>'


def render(build, payload, products, fti_rows, gaps, moments, collections,
           dead_rows, retired_rows):
    p = payload
    s = p["stats"]
    raw = dict(payload)
    raw["moments"] = raw.get("moments") or []

    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="theme-color" content="#070e1a">
<title>Scout - Ops Dashboard | Gridiron Locker</title>
<style>{css()}</style>
</head>
<body>
<div class="topbar"><div class="topbar-inner">
 <div class="brand"><span class="mark">S</span><span>Scout<small>Gridiron Locker - Internal Ops</small></span></div>
 <span class="pill"><span class="dot"></span>Data refresh {esc(short_date(p["generated"]))} &middot; {p["window_days"]}-day window</span>
</div></div>
<main class="wrap">
<section>
 <h1>Operations <span style="color:var(--green)">Scout</span></h1>
 <p class="lead">Internal view over the storefront pipeline: catalogue health, live Fan Trend
 Index, design gaps and headline intelligence. Regenerated on every build
 (<span class="kbd">src/scout.py</span> &rarr; <span class="kbd">src/build.py</span>); the nightly
 GitHub Actions refresh keeps this fresh. Not indexed - internal use only.</p>
 <div class="kpis">
  {kpi_card(s["products"], "Live designs")}
  {kpi_card(s["collections"], "Collections")}
  {kpi_card(s["images"], "Hosted product images")}
  {kpi_card(money(s["avg_price"]), "Average price")}
  {kpi_card(f'{s["hot"]} / {s["throwback"]}', "Trending / throwback")}
  {kpi_card(s["gaps"], "Design gaps")}
  {kpi_card(s["moments"], "Player moments")}
  {kpi_card(p["peak_mentions"], "Peak mentions (window)")}
  {kpi_card(s["dead_campaigns"], "Dead campaigns")}
 </div>
</section>

<section>
 <h2>Fan Trend Index</h2>
 <p class="muted small">0&ndash;100 share-of-voice vs the hottest name in the window.
 Formula: <code>{esc(p["fti_formula"])}</code></p>
 <div class="card">
 <table>
 <thead><tr><th>#</th><th>Name</th><th>Collection</th><th class="num">Mentions</th><th>FTI</th><th>Status</th><th>Design</th></tr></thead>
 <tbody>
 {''.join(_fti_row(i, r, build) for i, r in enumerate(fti_rows, 1))}
 </tbody>
 </table>
 </div>
</section>

<section>
 <h2>Collections</h2>
 <div class="colcards">
 {''.join(_collection_card(c, build) for c in collections)}
 </div>
</section>

<section>
 <h2>Latest headlines by collection</h2>
 <div class="colcards">
 {''.join(_headline_card(c) for c in collections)}
 </div>
</section>

<section>
 <h2>Catalogue watch</h2>
 <div class="card">
  <div class="tools">
   <input id="q" type="search" placeholder="Search design, art, theme...">
   <select id="fcol"></select>
   <select id="ftrend">
    <option value="">All statuses</option>
    <option value="hot">Trending</option>
    <option value="throwback">Throwback</option>
    <option value="steady">Steady</option>
   </select>
   <span class="muted small" id="count"></span>
  </div>
  <table>
  <thead><tr><th>Design</th><th>Collection</th><th>Garment</th><th>Theme</th><th class="num">Price</th><th>Status</th><th>Link</th></tr></thead>
  <tbody id="rows">
  {''.join(_product_row(sl) for sl in products)}
  </tbody>
  </table>
 </div>
 {_dead_card(dead_rows) if dead_rows else ''}
 {_retired_card(retired_rows)}
 <div class="card" style="margin-top:22px">
  <h3>Design gaps - build these next</h3>
  <p class="muted small">Names scoring on the news feeds with no matching design in the locker.
  Highest FTI = highest priority.</p>
  <div class="calls">
  {''.join(_gap_call(r, build) for r in gaps) or '<p class="muted">No gaps right now.</p>'}
  </div>
 </div>
</section>

<section>
 <h2>Latest player moments</h2>
 <div class="card">
  <div class="moments">
  {''.join(_moment(m) for m in moments[:15])}
  </div>
  <p class="muted small" style="margin:14px 0 0">{len(moments)} moments captured in this window.
  <a href="/fan-trend-index/">Public Fan Trend Index &rarr;</a></p>
 </div>
</section>

<section>
 <h2>Pipeline &amp; provenance</h2>
 <div class="grid2">
  <div class="card">
   <h3>Where this data comes from</h3>
   <table>
    <tbody>
     <tr><td>Trend pipeline</td><td class="mono small">src/trends.py</td><td>news crawler + FTI scoring</td></tr>
     <tr><td>Catalogue source</td><td class="mono small">data/products_live.json</td><td>crawled from Viralstyle</td></tr>
     <tr><td>Storefront build</td><td class="mono small">src/build.py</td><td>writes site/ incl. ops/scout</td></tr>
     <tr><td>Publishing</td><td class="mono small">.github/workflows/deploy.yml</td><td>GitHub Pages &rarr; /ops/scout/</td></tr>
     <tr><td>Daily refresh</td><td class="mono small">.github/workflows/refresh.yml</td><td>06:15 &amp; 15:15 UTC</td></tr>
    </tbody>
   </table>
   <div class="stash">
    <a href="scout.json">Raw snapshot (scout.json)</a>
    <a href="./" >This dashboard</a>
    <a href="../">/ops/ index</a>
   </div>
  </div>
  <div class="card">
   <h3>Quick links</h3>
   <div class="stash" style="flex-direction:column;gap:8px">
    <a href="/fan-trend-index/">Public Fan Trend Index</a>
    <a href="/2026-season/">2026 season hub</a>
    <a href="/">Storefront home</a>
   </div>
   <p class="muted small" style="margin-top:16px">Scout is generated by
   <span class="kbd">src/scout.py</span> from the same JSON the storefront uses, so numbers here
   always match the live build. Headline-linked stories belong to their publishers.</p>
  </div>
 </div>
</section>

<details><summary>Inspect raw data (JSON)</summary><pre>{esc(json.dumps(payload, indent=1))}</pre></details>

<footer><div class="wrap">
 <span>Scout &middot; internal ops dashboard &middot; noindex</span>
 <span>Generated {esc(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))} by src/scout.py</span>
</div></footer>
</main>
<script>
(function(){{
 var rows=[].slice.call(document.querySelectorAll('#rows tr'));
 var q=document.getElementById('q'),fc=document.getElementById('fcol'),
     ft=document.getElementById('ftrend'),cnt=document.getElementById('count');
 var cols={{}};rows.forEach(function(r){{var c=r.dataset.col;cols[c]=(cols[c]||0)+1;}});
 Object.keys(cols).sort().forEach(function(c){{
   var o=document.createElement('option');o.value=c;o.textContent=c;fc.appendChild(o);}});
 function apply(){{
   var t=(q.value||'').toLowerCase(),c=fc.value,tr=ft.value,n=0;
   rows.forEach(function(r){{
     var ok=(!t||r.dataset.text.indexOf(t)>-1)&&(!c||r.dataset.col===c)&&(!tr||r.dataset.trend===tr);
     r.style.display=ok?'':'none';if(ok)n++;}});
   cnt.textContent=n+' of '+rows.length+' designs';}}
 q.addEventListener('input',apply);fc.addEventListener('change',apply);
 ft.addEventListener('change',apply);apply();
}})();
</script>
</body>
</html>
"""
    return head


def _fti_row(i, r, build):
    st = esc(r.get("status") or "")
    dot = '<span class="badge trending">Trending</span>' if st == "trending" \
        else ('<span class="badge steady">Steady</span>' if st == "steady"
              else '<span class="badge quiet">Quiet</span>')
    col = build.COLLECTIONS.get(r.get("collection"), {}).get("short", r.get("collection"))
    return (f'<tr><td>{i}</td><td><b>{esc(build.pretty_name(r["name"]))}</b></td>'
            f'<td>{esc(col)}</td><td class="num">{r.get("mentions", 0)}</td>'
            f'<td><div class="bar"><i style="width:{min(100, int(r.get("index") or 0))}%">'
            f'</i><b>{int(r.get("index") or 0)}</b></div></td><td>{dot}</td>'
            f'<td>{design_badge(r, build)}</td></tr>')


def _collection_card(c, build):
    gaps = "".join(f'<span class="chip" style="border-color:rgba(255,177,90,.5);color:var(--orange)">'
                   f'{esc(build_pretty(build, g.get("name")))}</span>'
                   for g in c.get("gaps") or [])
    terms = "".join(f'<span class="chip">{esc(t)}</span>' for t in c.get("top_terms") or [])
    return f"""<div class="colcard">
 <h3>{esc(c["name"])}</h3>
 <p class="muted small">{c["products"]} designs &middot; avg {money(c["avg_price"])} &middot;
 {c["hot"]} trending &middot; {c["throwback"]} throwback &middot; {c["headline_count"]} headlines</p>
 <p class="small" style="margin:8px 0 0"><b>Top terms</b></p>
 <div class="chips">{terms or '<span class="chip">-</span>'}</div>
 <p class="small" style="margin:10px 0 0"><b>Gaps</b></p>
 <div class="chips">{gaps or '<span class="chip">none</span>'}</div>
 <p class="small" style="margin:12px 0 0"><a href="/{esc(c["slug"])}/">Collection page &rarr;</a>
 &nbsp;<a href="{esc(c["store"])}" rel="noopener">Store &rarr;</a></p>
</div>"""


def _headline_card(c):
    lis = "".join(f'<li><a href="{esc(h.get("url"))}" rel="noopener">{esc(h.get("title"))}</a>'
                  f'<br><span class="muted small">{esc(h.get("source", ""))}</span></li>'
                  for h in c.get("headlines") or [])
    return f"""<div class="colcard">
 <h3>{esc(c["name"])} headlines</h3>
 <ul class="moments" style="list-style:none;padding:0;margin:0;gap:9px">
 {lis or '<li class="muted small">No headlines captured this window.</li>'}
 </ul>
</div>"""


def _product_row(it):
    text = esc((it["name"] + " " + it.get("art", "") + " " + it.get("theme", "")).lower())
    trend_val = it.get("trend") or "steady"
    cls = "badge trending" if it.get("trend") == "hot" else \
        ("badge quiet" if it.get("trend") == "throwback" else "badge steady")
    label = "Trending" if it.get("trend") == "hot" else \
        ("Throwback" if it.get("trend") == "throwback" else "Steady")
    return (f'<tr data-col="{esc(it["collection"])}" data-trend="{trend_val}" data-text="{text}">'
            f'<td><b>{esc(it["name"])}</b><br><span class="muted small">{esc(it.get("art", ""))}</span></td>'
            f'<td>{esc(it["collection"])}</td><td>{esc(it.get("garment", ""))}</td>'
            f'<td class="muted">{esc(it.get("theme", ""))}</td><td class="num">{money(it.get("price"))}</td>'
            f'<td><span class="{cls}">{label}</span></td>'
            f'<td><a href="{esc(it.get("buy", ""))}" rel="noopener">Shop &rarr;</a></td></tr>')


def _retired_card(rows):
    """Designs intentionally pulled from the storefront (data/retired.json)."""
    if not rows:
        return ""
    return f"""<div class="card" style="margin-top:22px;border-color:rgba(255,196,120,.35)">
 <h3><span class="badge">Retired designs</span> withheld from the storefront</h3>
 <p class="muted small">These campaigns may still be live on Viralstyle, but the player, coach or
 mark they depict has left, so they are not published. Edit <span class="mono">data/retired.json</span>
 to restore one.</p>
 <table><thead><tr><th>Slug</th><th>Design</th><th>Reason</th></tr></thead><tbody>
 {''.join(f'<tr><td class="mono small">{esc(x["slug"])}</td>'
          f'<td>{esc(x.get("title", ""))}</td><td class="small">{esc(x["reason"])}</td></tr>'
          for x in rows)}
 </tbody></table></div>"""


def _dead_card(rows):
    return f"""<div class="card" style="margin-top:22px;border-color:rgba(255,125,125,.35)">
 <h3><span class="badge dead">Dead campaigns</span> removed from the build</h3>
 <p class="muted small">These slugs exist in data/products.json but no longer return live product
 data on Viralstyle, so they are excluded from the storefront. Relaunch and re-crawl to restore.</p>
 <table><thead><tr><th>Slug</th><th>Title</th><th>Link</th></tr></thead><tbody>
 {''.join(f'<tr><td class="mono small">{esc(x["slug"])}</td><td>{esc(x.get("title", ""))}</td>'
          f'<td><a href="{esc(x.get("url", ""))}" rel="noopener">Viralstyle &rarr;</a></td></tr>'
          for x in rows)}
 </tbody></table></div>"""


def _gap_call(r, build):
    return (f'<div class="call"><b>{esc(build_pretty(build, r["name"]))}</b><br>'
            f'<span class="muted small">{esc(r.get("collection", ""))} &middot; '
            f'{r.get("mentions", 0)} mentions &middot; FTI {int(r.get("index") or 0)}</span></div>')


def build_pretty(build, name):
    try:
        if build is not None:
            return build.pretty_name(name)
    except Exception:
        pass
    return " ".join(w.title() for w in str(name).replace("-", " ").split())


def _moment(m):
    ents = "".join(f'<span class="chip">{esc(build_pretty(None, e))}</span>'
                   for e in (m.get("entities") or [])[:3])
    col = esc(m.get("collection", ""))
    return (f'<div class="moment"><div style="min-width:0">'
            f'<a href="{esc(m.get("url"))}" rel="noopener">{esc(m.get("title"))}</a>'
            f'<div class="meta">{esc(m.get("source", ""))} &middot; {esc(moment_date(m.get("pub")))}'
            f' &middot; <span class="mono">{col}</span></div></div>'
            f'<div class="chips" style="margin:0 0 0 auto;flex:none;max-width:42%">{ents}</div></div>')


def main():
    (build, payload, products, fti_rows, gaps, moments, collections,
     dead_rows, retired_rows) = collect()
    html = render(build, payload, products, fti_rows, gaps, moments, collections,
                  dead_rows, retired_rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(OUT_DIR, "scout.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
    print(f"ops/scout: {payload['stats']['products']} designs, "
          f"{payload['stats']['gaps']} gaps, {payload['stats']['moments']} moments "
          f"(data {payload.get('generated')})")


if __name__ == "__main__":
    main()
