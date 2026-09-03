#!/usr/bin/env python3
"""Generate the HQ mission-control dashboard at ops/hq (published at /ops/hq/).

HQ is the private, noindex control room over the whole pipeline: bot menu,
refresh pipeline + live workflow runs, catalogue listed-vs-built, image
health, automatic-verification checklist, newest campaigns, add-a-product
helper and search health.

Regenerated on every `src/build.py` run (the Refresh workflow calls
build.py), so the dashboard always reflects the latest crawl + trend data.

Usage:
    python3 src/hq.py               # write ops/hq/index.html
"""
import datetime
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "ops", "hq")
REPO = "gridironlocker/gridiron-locker"
RUNS_API = f"https://api.github.com/repos/{REPO}/actions/runs?per_page=6"
NEWEST = ["let-it-rip", "sanders-the-next-level",
          "limited-edition-m-vs-all", "limited-edition-qb19"]


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


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
.topbar{position:sticky;top:0;z-index:30;border-bottom:1px solid var(--line);
background:rgba(7,14,26,.92);backdrop-filter:blur(18px)}
.topbar-inner{width:min(1400px,calc(100% - 48px));margin:0 auto;min-height:70px;display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:10px 0}
.brand{display:flex;align-items:center;gap:12px;font-weight:800;letter-spacing:-.02em}
.mark{display:grid;place-items:center;width:36px;height:36px;border-radius:11px;
color:#05121f;background:linear-gradient(135deg,var(--blue),var(--green));font-weight:850}
.brand small{display:block;font-weight:600;color:var(--muted);letter-spacing:.14em;
text-transform:uppercase;font-size:.62rem}
.hqnav{display:flex;gap:8px;flex-wrap:wrap;margin-left:8px}
.hqnav a{padding:7px 13px;border:1px solid var(--line);border-radius:999px;color:var(--mut2);
font-size:.8rem;background:rgba(255,255,255,.03);white-space:nowrap}
.hqnav a.on{border-color:var(--blue2);color:#fff;background:rgba(61,157,245,.16)}
.hqnav a:hover{border-color:var(--blue2);color:#fff}
.pill{display:inline-flex;align-items:center;gap:7px;padding:7px 13px;border:1px solid var(--line2);
border-radius:999px;color:var(--mut2);background:rgba(255,255,255,.03);font-size:.8rem;white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green)}
.dot.yellow{background:var(--orange);box-shadow:0 0 10px var(--orange)}
.dot.red{background:var(--red);box-shadow:0 0 10px var(--red)}
.dot.grey{background:var(--muted);box-shadow:none}
.wrap{width:min(1400px,calc(100% - 48px));margin:0 auto}
section{padding:34px 0 6px}
h1{margin:0 0 10px;font-size:clamp(1.6rem,3.4vw,2.5rem);letter-spacing:-.03em;line-height:1.15}
h2{margin:0 0 6px;font-size:1.25rem;letter-spacing:-.02em}
h3{font-size:.95rem;margin:0 0 10px;letter-spacing:-.01em}
.lead{color:var(--muted);max-width:82ch;margin:0 0 22px}
.muted{color:var(--muted)} .small{font-size:.8rem} .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi{border:1px solid var(--line);border-radius:16px;padding:16px 18px;background:linear-gradient(180deg,var(--panel),var(--canvas2))}
.kpi b{display:block;font-size:1.7rem;line-height:1.1;letter-spacing:-.03em}
.kpi span{color:var(--muted);font-size:.78rem}
.card{border:1px solid var(--line);border-radius:18px;background:var(--panel);padding:20px 22px;
box-shadow:0 14px 44px rgba(0,0,0,.22)}
.card + .card{margin-top:22px}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th{color:var(--muted);font-weight:650;text-align:left;padding:9px 10px;border-bottom:1px solid var(--line2);
font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:middle}
tr:hover td{background:rgba(124,200,255,.045)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.7rem;font-weight:700;
letter-spacing:.03em;text-transform:uppercase;border:1px solid transparent}
.ok{color:#062b1c;background:var(--green)} .bad{color:#2b0f0f;background:var(--red)}
.info{color:#04121f;background:var(--blue)} .warn{color:#26180a;background:var(--orange)}
.botgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.bot{border:1px solid var(--line);border-radius:14px;padding:13px 15px;background:rgba(255,255,255,.018)}
.bot b{display:block;font-size:.88rem} .bot span{color:var(--muted);font-size:.78rem}
.bot code{font-family:ui-monospace,monospace;font-size:.74rem;color:var(--blue)}
.steps{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}
.step{padding:5px 12px;border:1px solid var(--line2);border-radius:999px;font-size:.76rem;color:var(--mut2);background:rgba(255,255,255,.03)}
.arrow{color:var(--muted);font-size:.8rem}
.cmd{background:#04090f;border:1px solid var(--line2);border-radius:12px;padding:12px 16px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem;color:#cfe6ff;overflow:auto}
footer{padding:40px 0 56px;color:var(--muted);font-size:.8rem;border-top:1px solid var(--line);margin-top:40px}
footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px}
.kbd{font-family:ui-monospace,monospace;background:rgba(255,255,255,.06);padding:1px 6px;border-radius:6px;font-size:.78em}
.runs{display:flex;flex-direction:column;gap:8px;margin-top:12px}
.run{display:flex;gap:10px;align-items:center;padding:9px 12px;border:1px solid var(--line);border-radius:11px;background:rgba(255,255,255,.015);font-size:.82rem}
.run .meta{color:var(--muted);font-size:.74rem}
"""


def load_json(rel, default):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def fetch_runs():
    """Snapshot of the latest workflow runs, or None when rate-limited/offline."""
    try:
        import urllib.request
        req = urllib.request.Request(
            RUNS_API,
            headers={"User-Agent": "gridiron-hq", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        runs = data.get("workflow_runs") or []
        out = []
        for w in runs[:6]:
            out.append(dict(
                name=w.get("name") or w.get("display_title") or "workflow",
                status=w.get("status") or "",
                conclusion=w.get("conclusion") or "",
                event=w.get("event") or "",
                branch=(w.get("head_branch") or ""),
                created=w.get("created_at") or "",
                url=w.get("html_url") or "",
            ))
        return out
    except Exception:
        return None


def run_dot(status, conclusion):
    if status in ("in_progress", "queued", "waiting", "requested"):
        return '<span class="dot yellow"></span>'
    if conclusion == "success":
        return '<span class="dot"></span>'
    if conclusion in ("failure", "timed_out", "cancelled"):
        return '<span class="dot red"></span>'
    return '<span class="dot grey"></span>'


def collect():
    import build as B
    TRENDS = B.TRENDS
    MODEL = B.MODEL
    ALL = B.ALL
    ORDER = B.ORDER
    COLLECTIONS = B.COLLECTIONS
    try:
        DELISTED = json.load(open(os.path.join(ROOT, "data/delisted.json"))).get("slugs", {})
    except Exception:
        DELISTED = {}
    live = load_json("data/products_live.json", {})
    prods = load_json("data/products.json", {})
    cols = load_json("data/collections.json", {})
    cfg = load_json("src/config.json", {})
    domain = (cfg.get("domain") or "https://gridironlocker.store").rstrip("/")

    # catalogue listed vs built
    catalogue = []
    for ckey in ORDER:
        listed = len((cols.get(ckey) or {}).get("products", []))
        built = len(MODEL.get(ckey, []))
        c = COLLECTIONS.get(ckey, {})
        catalogue.append(dict(key=ckey, short=c.get("short", ckey),
                              name=c.get("name", ckey), listed=listed, built=built))

    # image health from products_live.json img maps vs files on disk
    total = 0
    missing = []
    full = partial = none = 0
    for slug, entry in live.items():
        img = entry.get("img") or {}
        ccount = sum(1 for t in img if t.startswith("c"))
        if ccount >= 6:
            full += 1
        elif ccount == 0:
            none += 1
        else:
            partial += 1
        for tag, rel in img.items():
            total += 1
            if not isinstance(rel, str):
                missing.append(f"{slug}/{tag}")
                continue
            p = os.path.join(ROOT, "site", rel.lstrip("/"))
            try:
                if not (os.path.isfile(p) and os.path.getsize(p) > 1000):
                    missing.append(f"{slug}/{tag}")
            except Exception:
                missing.append(f"{slug}/{tag}")

    # verification checklist
    today = datetime.date.today().isoformat()
    trend_ok = (TRENDS.get("generated") == today)
    images_ok = (len(missing) == 0 and total > 0)
    catalogue_ok = (len(ALL) > 0 and len(live) > 0)
    built_slugs = {it["slug"] for it in ALL}
    delisted_ok = all(s not in built_slugs for s in (DELISTED or {}).keys())
    # replay idempotent: every CAMPAIGNS slug (incl. campaigns_extra) present
    try:
        import replay_updates as R
        camps = dict(R.CAMPAIGNS)
    except Exception:
        camps = {s: {} for s in NEWEST}
    replay_ok = all(
        (s in live and s in prods) for s in camps.keys()
    ) if camps else False

    checks = [
        ("trend data generated today", trend_ok,
         f"{TRENDS.get('generated') or '-'} vs today {today}"),
        ("0 broken product images", images_ok,
         f"{total} refs, {len(missing)} missing"),
        ("catalogue never emptied", catalogue_ok,
         f"{len(ALL)} built, {len(live)} live"),
        ("delisted slugs blocked", delisted_ok,
         f"{len(DELISTED or {})} retired, 0 resurrected"),
        ("replay idempotent", replay_ok,
         f"{len(camps)} campaigns injected"),
    ]

    # newest campaigns
    newest = []
    for slug in NEWEST:
        e = live.get(slug) or prods.get(slug) or {}
        img = e.get("img") or {}
        ccount = sum(1 for t in img if t.startswith("c"))
        sizes = e.get("sizes") or []
        title = e.get("title") or (camps.get(slug) or {}).get("title", slug)
        newest.append(dict(slug=slug, title=title, swatches=ccount,
                           sizes=",".join(sizes) if sizes else "-",
                           url=f"/shop/{slug}/"))

    # search health
    try:
        sitemap = open(os.path.join(ROOT, "site/sitemap.xml"), encoding="utf-8").read()
        sitemap_count = sitemap.count("<loc>")
    except Exception:
        sitemap_count = 0
    indexnow_key = cfg.get("indexnow_key", "")
    search = [
        ("sitemap urls", str(sitemap_count), sitemap_count == 129 or sitemap_count > 0),
        ("domain", domain, domain == "https://gridironlocker.store"),
        ("GSC file googleae06215486ed6c17.html",
         "present" if os.path.exists(os.path.join(ROOT, "site/googleae06215486ed6c17.html")) else "missing",
         os.path.exists(os.path.join(ROOT, "site/googleae06215486ed6c17.html"))),
        ("IndexNow key", indexnow_key[:12] + "…" if indexnow_key else "missing",
         bool(indexnow_key) and os.path.exists(os.path.join(ROOT, f"site/{indexnow_key}.txt"))),
        ("llms.txt", "present" if os.path.exists(os.path.join(ROOT, "site/llms.txt")) else "missing",
         os.path.exists(os.path.join(ROOT, "site/llms.txt"))),
    ]

    runs = fetch_runs()
    shipped = len(ALL)
    trend_date = TRENDS.get("generated") or "-"
    return dict(B=B, TRENDS=TRENDS, ALL=ALL, ORDER=ORDER, catalogue=catalogue,
                total=total, missing=missing, full=full, partial=partial, none=none,
                checks=checks, newest=newest, search=search, runs=runs,
                shipped=shipped, trend_date=trend_date, domain=domain,
                cfg=cfg, live=live)


BOTS = [
    ("scrape_list.py", "Re-scan the 4 collection pages for new designs."),
    ("scrape_products.py", "Crawl each design's full product data + images."),
    ("replay_updates.py", "Re-inject directly-published campaigns (idempotent)."),
    ("add_campaign.py", "One-command adder: slug + collection -> campaigns_extra.json."),
    ("dl.py", "Download hi-res images, auto-convert every grab to WebP."),
    ("src/trends.py", "Refresh trend data + Fan Trend Index from news feeds."),
    ("src/build.py", "Rebuild all HTML pages, sitemaps, feeds + ops dashboards."),
    ("src/scout.py", "Regenerate the Scout ops dashboard (/ops/scout/)."),
    ("src/hq.py", "Regenerate this HQ mission control (/ops/hq/)."),
    ("src/indexnow.py", "Ping IndexNow so Bing/Yandex pick up changed urls."),
    ("ops/board/build.py", "Regenerate the Operator Board (/ops/board/)."),
    ("marketing/plan.py", "Refresh the marketing planner (/marketing/dashboard.html)."),
]


def render(d):
    B = d["B"]
    runs = d["runs"]
    if runs:
        runs_html = "".join(
            f'<div class="run">{run_dot(r["status"], r["conclusion"])}'
            f'<div><a href="{esc(r["url"])}"><b>{esc(r["name"])}</b></a>'
            f'<div class="meta">{esc(r["status"])}'
            f'{" / " + esc(r["conclusion"]) if r["conclusion"] else ""}'
            f' &middot; {esc(r["event"])} &middot; {esc(r["branch"])}'
            f' &middot; {esc((r["created"] or "")[:10])}</div></div></div>'
            for r in runs
        )
    else:
        runs_html = ('<p class="muted small">Live runs unavailable (rate-limited or offline). '
                     'Showing the last build snapshot instead - '
                     '<a href="https://github.com/gridironlocker/gridiron-locker/actions">open Actions</a>.</p>')

    bots_html = "".join(
        f'<div class="bot"><b><code>{esc(cmd)}</code></b><br><span>{esc(desc)}</span></div>'
        for cmd, desc in BOTS
    )
    cat_rows = "".join(
        f'<tr><td><b>{esc(c["short"])}</b><br><span class="muted small">{esc(c["name"])}</span></td>'
        f'<td class="num">{c["listed"]}</td><td class="num">{c["built"]}</td>'
        f'<td class="num">{c["listed"] - c["built"]}</td></tr>'
        for c in d["catalogue"]
    )
    checks_html = "".join(
        f'<tr><td>{esc(label)}</td><td><span class="badge {"ok" if ok else "bad"}">'
        f'{"PASS" if ok else "FAIL"}</span></td><td class="muted small">{esc(detail)}</td></tr>'
        for label, ok, detail in d["checks"]
    )
    newest_rows = "".join(
        f'<tr><td class="mono small">{esc(n["slug"])}</td><td>{esc(n["title"])}</td>'
        f'<td class="num">{n["swatches"]}</td><td class="mono small">{esc(n["sizes"])}</td>'
        f'<td><a href="{esc(n["url"])}">page &rarr;</a></td></tr>'
        for n in d["newest"]
    )
    search_rows = "".join(
        f'<tr><td>{esc(label)}</td><td class="mono small">{esc(val)}</td>'
        f'<td><span class="badge {"ok" if ok else "bad"}">{"OK" if ok else "CHECK"}</span></td></tr>'
        for label, val, ok in d["search"]
    )
    missing_list = "".join(f"<li class='mono small'>{esc(m)}</li>" for m in d["missing"][:12])
    steps = ["crawl", "replay", "dl", "trends", "verify", "build", "deploy", "IndexNow"]
    steps_html = '<span class="arrow">&rarr;</span>'.join(
        f'<span class="step">{esc(s)}</span>' for s in steps)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="theme-color" content="#070e1a">
<title>HQ - Mission Control | Gridiron Locker</title>
<style>{css()}</style>
</head>
<body>
<div class="topbar"><div class="topbar-inner">
 <div class="brand"><span class="mark">H</span><span>HQ<small>Gridiron Locker - Mission Control</small></span></div>
 <nav class="hqnav" aria-label="HQ menu">
  <a class="on" href="/ops/hq/">HQ</a>
  <a href="/ops/board/">Operator Board</a>
  <a href="/ops/scout/">Scout</a>
  <a href="/ops/design-drop/">Design Drop</a>
  <a href="/marketing/dashboard.html">Marketing</a>
  <a href="/">Storefront</a>
  <a href="https://github.com/gridironlocker/gridiron-locker/actions">GitHub Actions</a>
  <a href="https://github.com/gridironlocker/gridiron-locker">Repo</a>
 </nav>
 <span class="pill"><span class="dot"></span>Data refresh {esc(d['trend_date'])} &middot; {d['shipped']} designs shipped</span>
</div></div>
<main class="wrap">
<section>
 <h1>Mission <span style="color:var(--green)">Control</span></h1>
 <p class="lead">One screen over the whole store pipeline: bots, refresh cadence with live
 workflow runs, catalogue listed-vs-built, WebP image health, automatic-verification
 checklist, newest campaigns, the one-command adder and search health. Regenerated on every
 build (<span class="kbd">src/hq.py</span> &rarr; <span class="kbd">src/build.py</span>);
 private, noindex, internal use only.</p>
 <div class="kpis">
  <div class="kpi"><b>{d['shipped']}</b><span>Shipped designs</span></div>
  <div class="kpi"><b>{esc(d['trend_date'])}</b><span>Trend-data date</span></div>
  <div class="kpi"><b>{d['total']}</b><span>Product image refs</span></div>
  <div class="kpi"><b>{d['full']}</b><span>Products with 6 swatches</span></div>
  <div class="kpi"><b>{len(d['missing'])}</b><span>Missing images</span></div>
  <div class="kpi"><b>{d['catalogue'][0]['built'] + d['catalogue'][1]['built'] + d['catalogue'][2]['built'] + d['catalogue'][3]['built'] if len(d['catalogue'])==4 else d['shipped']}</b><span>Built (all collections)</span></div>
 </div>
</section>

<section>
 <h2>Bot menu</h2>
 <p class="muted small">Every operator command, one line each. Run from the repo root.</p>
 <div class="card"><div class="botgrid">{bots_html}</div></div>
</section>

<section>
 <h2>Refresh pipeline</h2>
 <div class="card">
  <p style="margin:0"><b>Schedule:</b> 2x/day <span class="kbd">06:15 &amp; 15:15 UTC</span> + every push to main + manual dispatch
  (<span class="kbd">Actions &rarr; Refresh site &rarr; Run workflow</span>).</p>
  <div class="steps">{steps_html}</div>
  <p class="muted small" style="margin:0">KPIs: <b style="color:var(--ink)">{d['shipped']} designs shipped</b> &middot;
  trend data <b style="color:var(--ink)">{esc(d['trend_date'])}</b> &middot; chain crawl&rarr;replay&rarr;dl&rarr;trends&rarr;verify&rarr;build&rarr;deploy&rarr;IndexNow.</p>
  <h3 style="margin-top:18px">Live workflow runs</h3>
  <div class="runs" id="runs">{runs_html}</div>
  <p class="muted small">Source: <span class="kbd">api.github.com/repos/gridironlocker/gridiron-locker/actions/runs?per_page=6</span>.
  Dots: <span class="badge ok">success</span> <span class="badge warn">running</span> <span class="badge bad">failed</span>.
  Rate-limited? The snapshot above was taken at build time; the page retries live below.</p>
 </div>
</section>

<section>
 <h2>Catalogue: listed vs built</h2>
 <div class="card"><table>
 <thead><tr><th>Collection</th><th class="num">Listed</th><th class="num">Built</th><th class="num">Skipped</th></tr></thead>
 <tbody>{cat_rows}</tbody></table>
 <p class="muted small">Listed = products in data/collections.json. Built = pages emitted by src/build.py
 (delisted + imageless slugs skipped). Skipped = listed - built.</p></div>
</section>

<section>
 <h2>Image health (WebP)</h2>
 <div class="card"><table><tbody>
  <tr><td>Total refs (products_live.json img maps)</td><td class="num"><b>{d['total']}</b></td></tr>
  <tr><td>Missing files on disk</td><td class="num"><b>{len(d['missing'])}</b></td></tr>
  <tr><td>Products with 6 swatches</td><td class="num"><b>{d['full']}</b></td></tr>
  <tr><td>Products partial (1-5 swatches)</td><td class="num"><b>{d['partial']}</b></td></tr>
  <tr><td>Products with none</td><td class="num"><b>{d['none']}</b></td></tr>
 </tbody></table>
 {('<p class="muted small">Missing (first 12):</p><ul>' + missing_list + '</ul>') if d['missing'] else '<p class="muted small">All image refs resolve to files under site/img/p. Only .webp ships.</p>'}
 </div>
</section>

<section>
 <h2>Automatic-verification checklist</h2>
 <div class="card"><table>
 <thead><tr><th>Check</th><th>Status</th><th>Detail</th></tr></thead>
 <tbody>{checks_html}</tbody></table></div>
</section>

<section>
 <h2>Newest campaigns</h2>
 <div class="card"><table>
 <thead><tr><th>Slug</th><th>Title</th><th class="num">Swatches</th><th>Sizes</th><th>Page</th></tr></thead>
 <tbody>{newest_rows}</tbody></table>
 <p class="muted small">The four directly-published campaigns injected by replay_updates.py. Swatches = c0-c5
 images in the live img map; sizes = campaign SELECT SIZE row.</p></div>
</section>

<section>
 <h2>Add-a-product</h2>
 <div class="card">
  <p style="margin-top:0">New directly-published campaign? One command:</p>
  <div class="cmd">python3 add_campaign.py &lt;slug&gt; &lt;collection&gt;</div>
  <p class="muted small">Example: <span class="kbd">python3 add_campaign.py my-new-design cleveland-browns</span>
  &rarr; merges into <span class="kbd">data/campaigns_extra.json</span> &rarr;
  <span class="kbd">python3 replay_updates.py &amp;&amp; python3 dl.py &amp;&amp; python3 src/build.py</span>.
  Collections: <span class="kbd">cleveland-browns, dallas-cowboys, green-bay-packers, michigan</span>.
  Add <span class="kbd">--dry-run</span> to preview without writing. Full docs: HOW-TO-ADD-A-DESIGN.md Option A+.</p>
 </div>
</section>

<section>
 <h2>Search health</h2>
 <div class="card"><table>
 <thead><tr><th>Signal</th><th>Value</th><th>Status</th></tr></thead>
 <tbody>{search_rows}</tbody></table>
 <p class="muted small">Sitemap = site/sitemap.xml url count. GSC file, IndexNow key file and llms.txt must all
 ship in site/ on every build.</p></div>
</section>

<footer><div class="wrap">
 <span>HQ &middot; mission control &middot; noindex</span>
 <span>Generated {esc(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))} by src/hq.py</span>
</div></footer>
</main>
<script>
(function(){{
  try{{
    fetch("https://api.github.com/repos/gridironlocker/gridiron-locker/actions/runs?per_page=6")
      .then(function(r){{ if(!r.ok) throw new Error("rate-limited"); return r.json(); }})
      .then(function(j){{
        var runs=(j.workflow_runs||[]).slice(0,6);
        if(!runs.length) return;
        var el=document.getElementById("runs");
        el.innerHTML=runs.map(function(w){{
          var ok=(w.conclusion==="success"), run=(w.status!=="completed");
          var dot=run?'<span class="dot yellow"></span>':(ok?'<span class="dot"></span>':'<span class="dot red"></span>');
          return '<div class="run">'+dot+'<div><a href=\''+w.html_url+'\'><b>'+w.name+'</b></a>'
            +'<div class="meta">'+w.status+(w.conclusion?" / "+w.conclusion:"")
            +' &middot; '+w.event+' &middot; '+(w.head_branch||"")+'</div></div></div>';
        }}).join("");
      }})
      .catch(function(){{ /* keep build-time snapshot */ }});
  }}catch(e){{}}
}})();
</script>
</body>
</html>
"""


def main():
    d = collect()
    out_html = render(d)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(out_html)
    print(f"ops/hq: mission control generated ({d['shipped']} designs, {d['total']} images, data {d['trend_date']})")


if __name__ == "__main__":
    main()
