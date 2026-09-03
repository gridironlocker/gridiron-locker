#!/usr/bin/env python3
"""Generate the private one-monitor operator board at ops/board.

The board is ONE screen: header, KPI strip, three scrolling columns, footer.
No tabs, no page scroll - it is meant to sit on the operator's monitor and be
read at a glance. It is a control room, not the storefront: it is never linked
from public nav, and /ops/ is Disallow-ed in robots.txt.

Layout
------
  LEFT    Kickoff clock   - live countdown to every Week 1 kickoff
  MIDDLE  Week 1 drop     - the eight DESIGN-BLUEPRINT.md §5b slots, by status
  RIGHT   Live signal     - Fan Trend Index, gaps, latest headlines

Data comes from the same snapshots the storefront is built from
(data/trends.json, data/people.json, data/products_live.json) plus the live
model in src/build.py, so the board can never drift from the public site.

Usage:
    python3 ops/board/build.py       # write ops/board/index.html
"""
import datetime
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

OUT_DIR = os.path.join(ROOT, "ops", "board")
GUIDE = "/guides/2026-week-1-shirts/"
DROP = "design-drop/index.html"
SCOUT = "scout/index.html"


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def load(name):
    """Read a data snapshot; return {} instead of exploding if it is missing."""
    path = os.path.join(ROOT, "data", name)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def kickoff_date(se):
    try:
        return datetime.date.fromisoformat(str(se.get("kickoff", ""))[:10])
    except ValueError:
        return None


# ------------------------------------------------------------------ collection
def collect():
    import build as B  # the storefront generator - single source of truth

    trends = B.TRENDS
    people = load("people.json").get("people", [])
    today = datetime.date.today()

    clocks = []
    for k in B.WEEK1_ORDER:
        se = B.SEASON[k]
        kick = kickoff_date(se)
        clocks.append(dict(
            key=k, short=B.COLLECTIONS[k]["short"], accent=B.COLLECTIONS[k]["accent"],
            game=B.week1_game(se), kickoff=se.get("kickoff", ""),
            days=(kick - today).days if kick else None,
            slots=len(B.WEEK1_SLATE[k]),
            live=sum(1 for s in B.WEEK1_SLATE[k] if s["status"] == "live"),
        ))

    slots = []
    for k in B.WEEK1_ORDER:
        c = B.COLLECTIONS[k]
        for i, s in enumerate(B.WEEK1_SLATE[k]):
            sibling = B.week1_sibling(k, i)
            # A slot whose declared sibling has been retired now shows a
            # substitute. Flag it so the operator knows the brief drifted.
            declared = s.get("sibling")
            retired_sibling = declared in (getattr(B, "RETIRED", {}) or {})
            slots.append(dict(
                slot=s["slot"], key=k, short=c["short"], accent=c["accent"],
                slogan=s["slogan"], garment=s["garment"], palette=s["palette"],
                note=s["note"], status=s["status"],
                sibling=sibling["name"] if sibling else "",
                retired_sibling=retired_sibling,
                declared_sibling=declared or "",
            ))

    fti = list(trends.get("fan_trend_index", {}).get("rows", []))[:8]
    headlines = []
    for k in B.WEEK1_ORDER:
        for h in trends.get("collections", {}).get(k, {}).get("headlines", [])[:2]:
            headlines.append(dict(short=B.COLLECTIONS[k]["short"],
                                  accent=B.COLLECTIONS[k]["accent"],
                                  title=h.get("title", ""), url=h.get("url", ""),
                                  source=h.get("source", "")))
    gaps = [p for p in people if p.get("status") == "current" and not p.get("design_count")]

    stats = dict(
        designs=len(B.ALL),
        hot=sum(1 for x in B.ALL if x.get("trend") == "hot"),
        slots=len(slots),
        live_slots=sum(1 for s in slots if s["status"] == "live"),
        gaps=len(gaps),
        generated=trends.get("generated") or "-",
        window=trends.get("window_days", 10),
        guide=B.DOMAIN + GUIDE,
    )
    return B, clocks, slots, fti, headlines, gaps, stats


# --------------------------------------------------------------------- render
CSS = """
:root{color-scheme:dark;--ink:#eef3fb;--muted:#8fa1bd;--canvas:#070c15;--panel:#0e1826;
--panel2:#132135;--line:rgba(160,190,225,.14);--line2:rgba(160,190,225,.26);
--blue:#79c6ff;--green:#5fe0ac;--orange:#ffb15a;--pink:#ec9cff;--red:#ff8181;
--font:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;font-family:var(--font);color:var(--ink);background:
radial-gradient(circle at 6% -10%,rgba(121,198,255,.16),transparent 36rem),
radial-gradient(circle at 98% 0%,rgba(95,224,172,.10),transparent 32rem),var(--canvas);
display:flex;flex-direction:column;overflow:hidden;font-size:14px;line-height:1.45}
a{color:var(--blue);text-decoration:none}a:hover{color:#c2e7ff}
header{border-bottom:1px solid var(--line);background:rgba(7,12,21,.85);backdrop-filter:blur(14px)}
.hdr{display:flex;align-items:center;gap:14px;padding:12px 18px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;font-weight:850;letter-spacing:-.02em;font-size:1.05rem}
.mark{display:grid;place-items:center;width:32px;height:32px;border-radius:10px;font-size:.8rem;
font-weight:900;color:#05121f;background:linear-gradient(135deg,var(--blue),var(--green))}
.brand small{display:block;font-size:.6rem;letter-spacing:.16em;text-transform:uppercase;
color:var(--muted);font-weight:700}
.pill{display:inline-flex;align-items:center;gap:7px;padding:5px 11px;border-radius:999px;
border:1px solid var(--line2);color:#c3d3e8;background:rgba(255,255,255,.03);font-size:.74rem;white-space:nowrap}
.pill.warn{border-color:rgba(255,129,129,.5);color:var(--red);background:rgba(255,129,129,.08)}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 9px var(--green)}
.hdr .spacer{margin-left:auto}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;padding:10px 18px 12px}
.kpi{border:1px solid var(--line);border-radius:13px;padding:9px 13px;
background:linear-gradient(180deg,var(--panel),var(--canvas))}
.kpi b{display:block;font-size:1.35rem;line-height:1.1;letter-spacing:-.03em}
.kpi span{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.08em}
.board{flex:1;min-height:0;display:grid;grid-template-columns:1fr 1.3fr 1fr;gap:12px;
padding:0 18px 12px}
.col{min-height:0;overflow:auto;border:1px solid var(--line);border-radius:16px;
background:rgba(14,24,38,.72);padding:12px 13px}
.col::-webkit-scrollbar{width:8px}
.col::-webkit-scrollbar-thumb{background:rgba(160,190,225,.18);border-radius:99px}
.colhead{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 10px;
padding-bottom:8px;border-bottom:1px solid var(--line)}
.colhead h2{margin:0;font-size:.82rem;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.colhead em{font-style:normal;font-size:.7rem;color:var(--muted)}
.card{border:1px solid var(--line);border-radius:13px;background:var(--panel2);padding:11px 12px;margin-bottom:9px}
.card:last-child{margin-bottom:0}
.clock{border-left:3px solid var(--ca)}
.clock .top{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.clock b{font-size:.98rem}
.clock .t{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.86rem;color:var(--blue);
font-variant-numeric:tabular-nums}
.clock .g{color:var(--muted);font-size:.78rem}
.clock .bar{height:5px;border-radius:99px;background:rgba(255,255,255,.07);margin-top:8px;overflow:hidden}
.clock .bar i{display:block;height:100%;background:var(--ca)}
.slot{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center}
.slot .id{font-family:ui-monospace,Menlo,monospace;font-size:.68rem;color:var(--muted)}
.slot .nm{font-weight:750;letter-spacing:.01em}
.slot .sub{color:var(--muted);font-size:.74rem}
.badge{padding:3px 9px;border-radius:999px;font-size:.66rem;font-weight:850;letter-spacing:.06em;
text-transform:uppercase;border:1px solid transparent;white-space:nowrap}
.s-live{color:#052318;background:var(--green)}
.s-art{color:#05202f;background:var(--blue)}
.s-brief{color:#2a1a06;background:var(--orange)}
.s-upload{color:#2a0a2a;background:var(--pink)}
.rule{border:1px solid rgba(255,177,90,.45);background:rgba(255,177,90,.07);border-radius:12px;
padding:9px 11px;color:#ffd7a8;font-size:.78rem;margin-bottom:9px}
.rule b{color:var(--orange)}
.frow{display:grid;grid-template-columns:1fr auto auto;gap:9px;align-items:center;
padding:7px 0;border-bottom:1px solid var(--line)}
.frow:last-child{border-bottom:0}
.frow .who{font-size:.82rem}
.frow .idx{font-family:ui-monospace,Menlo,monospace;font-size:.78rem;color:var(--blue)}
.meter{width:74px;height:5px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden}
.meter i{display:block;height:100%;background:linear-gradient(90deg,var(--blue),var(--green))}
.hl{padding:7px 0;border-bottom:1px solid var(--line);font-size:.8rem}
.hl:last-child{border-bottom:0}
.hl span{display:inline-block;padding:1px 7px;border-radius:6px;font-size:.64rem;font-weight:800;
letter-spacing:.06em;text-transform:uppercase;margin-right:6px}
footer{border-top:1px solid var(--line);padding:9px 18px;display:flex;gap:16px;align-items:center;
flex-wrap:wrap;color:var(--muted);font-size:.74rem;background:rgba(7,12,21,.7)}
footer code{font-family:ui-monospace,Menlo,monospace;color:#cfe2ff;background:rgba(255,255,255,.05);
padding:1px 6px;border-radius:6px}
footer .spacer{margin-left:auto}
@media(max-width:1100px){body{overflow:auto;height:auto}
 .board{grid-template-columns:1fr}.col{overflow:visible;max-height:none}}
"""

JS = """
function pad(n){return n<10?'0'+n:''+n}
function tick(){
  document.querySelectorAll('[data-deadline]').forEach(function(el){
    var end=new Date(el.dataset.deadline).getTime(), now=Date.now(), d=end-now;
    var out=el.querySelector('.t');
    if(isNaN(end)||!out) return;
    if(d<=0){out.textContent='KICKED OFF';return}
    var days=Math.floor(d/86400000), hrs=Math.floor(d/3600000)%24,
        mins=Math.floor(d/60000)%60, secs=Math.floor(d/1000)%60;
    out.textContent=days+'d '+pad(hrs)+':'+pad(mins)+':'+pad(secs);
  });
}
tick(); setInterval(tick,1000);
"""


def render(clocks, slots, fti, headlines, gaps, stats):
    # ---- kickoff clock -------------------------------------------------
    left = ""
    for c in clocks:
        left += f"""<div class="card clock" style="--ca:{c['accent']}" data-deadline="{esc(c['kickoff'])}">
 <div class="top"><b>{esc(c['short'])}</b><span class="t">--</span></div>
 <div class="g">{esc(c['game'])}</div>
 <div class="bar"><i style="width:{clocks_width(c)}%"></i></div>
</div>"""
    live_line = f"{stats['live_slots']} of {stats['slots']} Week 1 slots live"
    left += f"""<div class="card">
 <div class="g" style="color:var(--muted)">{esc(live_line)} &middot; {stats['designs']} designs in the locker &middot;
 {stats['hot']} tagged trending.</div>
</div>"""

    # ---- week 1 drop ---------------------------------------------------
    mid = """<div class="rule"><b>Slogan law.</b> Identity slogans, not player faces. The Cleveland
 quarterback slot is <b>slogan only</b> (LET IT RIP / NEW ERA): no face, no surname, no number.
 A slot may be <i>brief</i> in here - the public page still shows a live sibling, never a gap.</div>"""
    for k in dict.fromkeys(s["key"] for s in slots):
        rows = [s for s in slots if s["key"] == k]
        body = ""
        for s in rows:
            body += f"""<div class="slot">
 <span class="id">{esc(s['slot'])}</span>
 <span><span class="nm">{esc(s['slogan'])}</span><br>
  <span class="sub">{esc(s['garment'])} &middot; {esc(s['palette'])} &middot; sibling: {esc(s['sibling'])}{
   ' &middot; declared sibling ' + esc(s['declared_sibling']) + ' RETIRED - substituted'
   if s.get('retired_sibling') else ''}</span></span>
 <span class="badge s-{esc(s['status'])}">{esc(s['status'])}</span>
</div>"""
        mid += f"""<div class="card" style="border-left:3px solid {rows[0]['accent']}">
 <div class="colhead" style="border:0;padding:0;margin-bottom:8px">
  <h2 style="color:{rows[0]['accent']}">{esc(rows[0]['short'])}</h2>
  <em>{sum(1 for s in rows if s['status'] == 'live')}/{len(rows)} live</em></div>
 {body}</div>"""
    mid += f"""<div class="card"><a href="{DROP}">Open the Week 1 design drop &rarr;</a>
 <span style="color:var(--muted);font-size:.78rem">Art briefs, export list, upload checklist.</span></div>"""

    # ---- live signal ---------------------------------------------------
    right = ""
    for r in fti:
        idx = int(r.get("index", 0) or 0)
        name = str(r.get("name", "")).title()
        flag = '<span class="badge s-brief">gap</span>' if r.get("gap") else ""
        right += f"""<div class="frow"><span class="who">{esc(name)} {flag}</span>
 <span class="meter"><i style="width:{min(100, idx)}%"></i></span>
 <span class="idx">{idx}</span></div>"""
    if gaps:
        names = ", ".join(esc(str(g.get("name", "")).title()) for g in gaps[:5])
        right += f"""<div class="rule" style="margin-top:10px"><b>Open gaps:</b> {names}.
 Slogan-led designs only - no faces, no numbers.<br>
 These names are internal tracking. They never appear on art, on a public page,
 or in a caption.</div>"""
    for h in headlines[:8]:
        right += (f'<div class="hl"><span style="color:{h["accent"]}">{esc(h["short"])}</span>'
                  f'<a href="{esc(h["url"])}" target="_blank" rel="noopener">{esc(h["title"][:110])}</a></div>')

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="theme-color" content="#070c15">
<title>Operator Board | Gridiron Locker</title>
<style>{CSS}</style>
</head>
<body>
<header><div class="hdr">
 <div class="brand"><span class="mark">GL</span> Operator Board
  <small>Gridiron Locker &middot; control room</small></div>
 <span class="pill warn"><span class="dot" style="background:var(--red);box-shadow:0 0 9px var(--red)"></span>
  Private &middot; not the storefront</span>
 <span class="pill"><span class="dot"></span> Trend data {esc(stats['generated'])} &middot; {esc(stats['window'])}d window</span>
 <span class="spacer"></span>
 <span class="pill"><a href="../{SCOUT}">Scout &rarr;</a></span>
 <span class="pill"><a href="../{DROP}">Design drop &rarr;</a></span>
 <span class="pill"><a href="{esc(stats['guide'])}" target="_blank" rel="noopener">Public Week 1 guide &rarr;</a></span>
</div>
<div class="kpis">
 <div class="kpi"><b>{stats['designs']}</b><span>Designs live</span></div>
 <div class="kpi"><b>{stats['hot']}</b><span>Trending now</span></div>
 <div class="kpi"><b>{stats['live_slots']}/{stats['slots']}</b><span>Week 1 slots live</span></div>
 <div class="kpi"><b>{stats['gaps']}</b><span>Content gaps</span></div>
 <div class="kpi"><b>{len(fti)}</b><span>Tracked entities</span></div>
 <div class="kpi"><b>{len(headlines)}</b><span>Fresh headlines</span></div>
</div></header>

<div class="board">
 <section class="col"><div class="colhead"><h2>Kickoff clock</h2><em>Week 1 2026</em></div>{left}</section>
 <section class="col"><div class="colhead"><h2>Week 1 drop</h2><em>DESIGN-BLUEPRINT &sect;5b</em></div>{mid}</section>
 <section class="col"><div class="colhead"><h2>Live signal</h2><em>FTI &amp; headlines</em></div>{right}</section>
</div>

<footer>
 <span>Kickoff clock runs in your local time (operator: Africa/Casablanca).</span>
 <span><code>python3 ops/board/build.py</code> to regenerate &middot;
 <code>python3 src/trends.py &amp;&amp; python3 src/build.py</code> to refresh everything.</span>
 <span class="spacer"></span>
 <span>/ops/ is Disallow-ed in robots.txt. Never link this page from public nav.</span>
</footer>
<script>{JS}</script>
</body></html>
"""


def clocks_width(c):
    """Progress bar: 100% when the season started, scaled back over 14 days."""
    days = c.get("days")
    if days is None:
        return 0
    if days <= 0:
        return 100
    return max(4, 100 - min(96, int(days / 14 * 100)))


def main():
    B, clocks, slots, fti, headlines, gaps, stats = collect()
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(render(clocks, slots, fti, headlines, gaps, stats))
    print(f"ops/board: {stats['slots']} Week 1 slots ({stats['live_slots']} live), "
          f"{len(clocks)} kickoffs, {stats['designs']} designs "
          f"(trend data {stats['generated']})")


if __name__ == "__main__":
    main()
