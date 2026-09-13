#!/usr/bin/env python3
"""HQ - the Hunter board.

Same dashboard, same look, new brain. The intelligence lives in
src/hunter_intelligence.py; this file only renders what it returns.

What changed underneath, and why:

  before  12 headlines -> 12 "TRENDING" cards -> "post your Browns shirt with
          angle: <headline>". A single Google News story counted as a trend.
  now     every topic is graded on the ladder HEADLINE -> SIGNAL -> TREND ->
          OPPORTUNITY -> ACTION. HEADLINE is filtered off the board and named in
          the "filtered" section instead. What is shown has evidence (volume,
          outlets, velocity, sentiment, game state), a matched design, a platform
          plan and a confidence score. Article ideas only exist for OPPORTUNITY
          and above, i.e. confidence >= 60 AND a design that matches.

Usage:
    python3 src/hq.py
"""
import datetime
import html
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "ops", "hq")
sys.path.insert(0, os.path.join(ROOT, "src"))

try:
    import hunter_intelligence as HI
except Exception as _exc:  # pragma: no cover - keep the dashboard alive
    HI = None
    HI_IMPORT_ERROR = _exc
else:
    HI_IMPORT_ERROR = None


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def css():
    return """
:root{color-scheme:dark;--ink:#eef5ff;--muted:#93a6c2;--canvas:#070e1a;--panel:#0f1e36;--line:rgba(178,203,238,.13);--line2:rgba(178,203,238,.25);--blue:#7cc8ff;--green:#72e0ba;--orange:#ffb15a;--red:#ff7d7d}
*{box-sizing:border-box}body{margin:0;min-width:320px;color:var(--ink);line-height:1.55;background:var(--canvas);font-family:Inter,ui-sans-serif,system-ui,sans-serif}
.topbar{position:sticky;top:0;z-index:30;border-bottom:1px solid var(--line);background:rgba(7,14,26,.92);backdrop-filter:blur(18px)}
.topbar-inner{width:min(1100px,calc(100% - 32px));margin:0 auto;min-height:60px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 0}
.brand{font-weight:800;letter-spacing:-.02em}.brand small{display:block;font-weight:600;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;font-size:.62rem}
.pill{padding:6px 12px;border:1px solid var(--line2);border-radius:999px;color:var(--muted);background:rgba(255,255,255,.03);font-size:.8rem}
.wrap{width:min(1100px,calc(100% - 32px));margin:0 auto}
section{padding:28px 0 8px}h1{margin:0 0 8px;font-size:clamp(1.6rem,3vw,2.2rem)}h2{margin:0 0 10px;font-size:1.2rem}h3{margin:18px 0 8px;font-size:1rem}
.lead{color:var(--muted);max-width:80ch;margin:0 0 18px}
.card{border:1px solid var(--line);border-radius:16px;background:var(--panel);padding:18px 20px;margin-top:14px}
.muted{color:var(--muted)}.small{font-size:.82rem}.mono{font-family:ui-monospace,monospace}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.7rem;font-weight:700;text-transform:uppercase}
.trending{background:var(--green);color:#062b1c}.steady{background:var(--blue);color:#04121f}.quiet{background:rgba(255,255,255,.08);color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.item{border:1px solid var(--line);border-radius:12px;padding:14px;background:rgba(255,255,255,.02)}
.item b{display:block;margin-bottom:4px}.item a{color:var(--blue)}
ul{margin:8px 0;padding-left:18px}li{margin:4px 0}
.kbd{font-family:ui-monospace,monospace;background:rgba(255,255,255,.06);padding:1px 6px;border-radius:6px;font-size:.78em}
footer{padding:30px 0;color:var(--muted);font-size:.8rem;border-top:1px solid var(--line);margin-top:30px}

/* --- Hunter board additions (same palette, same panel language) --- */
.board{border:1px solid var(--line2);border-radius:16px;background:linear-gradient(180deg,rgba(114,224,186,.07),rgba(15,30,54,0));padding:18px 20px;margin-top:14px}
.board h2{margin:0 0 6px}
.board .answer{font-size:1.05rem;font-weight:700;margin:6px 0 12px}
.facts{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:10px 0 0}
.facts div{border:1px solid var(--line);border-radius:10px;padding:9px 11px;background:rgba(255,255,255,.02)}
.facts span{display:block;color:var(--muted);font-size:.66rem;letter-spacing:.09em;text-transform:uppercase}
.facts b{font-size:.86rem;font-weight:700}
.opp{border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin-top:14px;background:rgba(255,255,255,.02)}
.opp-head{display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}
.opp-head .ttl{font-weight:800;font-size:1.02rem}
.rank{color:var(--muted);font-weight:800;font-size:.8rem;letter-spacing:.06em}
.evi{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:8px;margin:12px 0 0}
.evi div{border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:rgba(255,255,255,.02)}
.evi span{display:block;color:var(--muted);font-size:.64rem;letter-spacing:.09em;text-transform:uppercase;margin-bottom:2px}
.evi b{font-size:.85rem;font-weight:700;line-height:1.3}
.evi i{display:block;font-style:normal;color:var(--muted);font-size:.72rem;line-height:1.35}
.box{border:1px solid var(--line2);border-radius:12px;padding:11px 14px;margin-top:10px;background:rgba(255,255,255,.03)}
.box h4{margin:0 0 5px;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}
.box ul{margin:2px 0 0;padding-left:16px}
.box .arrow{color:var(--green);font-weight:700}
.quote{border-left:2px solid var(--line2);padding:2px 0 2px 11px;margin:10px 0 0}
.quote p{margin:0;font-size:.95rem}
.bar{height:6px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;background:var(--green)}
.lvl-ACTION{background:var(--green);color:#062b1c}
.lvl-OPPORTUNITY{background:var(--blue);color:#04121f}
.lvl-TREND{background:var(--orange);color:#2a1503}
.lvl-SIGNAL{background:rgba(255,255,255,.16);color:var(--ink)}
.lvl-HEADLINE{background:rgba(255,255,255,.07);color:var(--muted)}
.conf{font-variant-numeric:tabular-nums;font-weight:800}
.ladder{display:grid;gap:6px;margin-top:10px}
.ladder div{display:flex;gap:10px;align-items:baseline;border:1px solid var(--line);border-radius:10px;padding:7px 11px;background:rgba(255,255,255,.02)}
.ladder .badge{min-width:96px;text-align:center}
"""


# ----------------------------------------------------------------- rendering
def _age(minutes):
    if minutes is None:
        return "no timestamp"
    if minutes < 60:
        return f"{minutes} min ago"
    if minutes < 1440:
        return f"{round(minutes / 60)} h ago"
    return f"{round(minutes / 1440)} d ago"


def _evidence_grid(opp, payload):
    e = opp["evidence"]
    vel = e["velocity"]
    sent = e["sentiment"]
    game = e["game"]
    fan_posts = e["fan_posts"]
    fan_line = f"{fan_posts} fan post(s)" if fan_posts else "0 fan posts observed"
    fan_note = payload["fan_note"] if not fan_posts else "connected: " + ", ".join(payload["fan_sources_live"])
    rows = [
        ("Fan discussion", fan_line, fan_note),
        ("Phrase velocity", vel.get("label", "not measurable"), vel.get("note", "")),
        ("News", f"{e['sources']} outlets · {e['items']} items",
         f"{e['utility']} utility listing(s) excluded as non-demand" if e["utility"]
         else "outlets carrying the reaction"),
        ("Sentiment", sent.get("label", "neutral"), sent.get("note", "")),
        ("Game state", game.get("label", "unknown"), game.get("season_note", "")),
        ("Confidence", f"{opp['confidence']}%",
         " · ".join(f"{p['label']} {p['points']:g}/{p['max']}" for p in opp["confidence_parts"])),
    ]
    cells = "".join(
        f'<div><span>{esc(label)}</span><b>{esc(value)}</b><i>{esc(note)}</i></div>'
        for label, value, note in rows
    )
    names = []
    for ent in e.get("entities") or []:
        # trends.json calls anything with a mention "trending". We show its count
        # as evidence and our own level as the verdict - that is the whole point
        # of the rewrite.
        names.append(
            f'{esc(ent["name"].title())} — {ent["mentions"]} window mention(s), FTI {esc(ent["fti"])}'
            f'{" · jersey " + esc(ent["jersey"]) if ent.get("jersey") else ""}'
            f'{" · no design yet" if ent.get("gap") else ""}'
        )
    entity_line = ""
    if names:
        entity_line = (f'<div class="muted small" style="margin-top:8px">Tracked names: '
                       f'{"; ".join(names)} <span class="muted">(trends.json labels these '
                       f'"trending"; the board grades them on the ladder instead)</span></div>')
    return f'<div class="evi">{cells}</div>{entity_line}'


def _commercial_box(opp):
    com = opp["commercial"]
    design = com.get("design") or {}
    if not design:
        return ('<div class="box"><h4>Commercial match</h4>'
                '<p class="small muted">No design on the shelf answers this demand. '
                'That is a gap to design, not a post to make.</p></div>')
    sellable = ('<span class="badge trending">sellable</span>' if design.get("sellable")
                else '<span class="badge quiet">crawl artefact - not in sellable catalogue</span>')
    price = esc(design.get("price", ""))
    link = (f'<a href="{esc(design.get("url", ""))}" target="_blank" rel="noopener">'
            f'{esc(design.get("title", ""))}</a>' if design.get("url") else esc(design.get("title", "")))
    alts = ""
    if com.get("alternates"):
        alts = ('<div class="muted small" style="margin-top:6px">Also on the shelf: '
                + "; ".join(esc(a["title"]) + (" (not sellable)" if not a.get("sellable") else "")
                            for a in com["alternates"]) + "</div>")
    return f"""<div class="box"><h4>Commercial match — {esc(com.get("type", ""))}</h4>
 <p style="margin:0"><span class="arrow">→</span> {link} {price} {sellable}</p>
 <div class="small muted" style="margin-top:4px">{esc(com.get("campaign", ""))} · matched because {esc(com.get("reason", ""))}</div>
 <div class="small" style="margin-top:6px"><b>Creative angle:</b> {esc(com.get("angle", ""))}</div>{alts}</div>"""


def _action_box(opp):
    if not opp.get("actions"):
        return ('<div class="box"><h4>Recommended action</h4>'
                '<p class="small muted">No posting plan yet — this is a watch item, '
                'not a post. It becomes an action at OPPORTUNITY with a matched design.</p></div>')
    rows = "".join(
        f'<li><span class="arrow">→</span> <b>{esc(a["platform"])}:</b> {esc(a["play"])} '
        f'<span class="muted">({esc(a["when"])})</span>'
        + (f'<br><span class="muted small">{esc(a["detail"])}</span>' if a.get("detail") else "")
        + "</li>"
        for a in opp["actions"]
    )
    return f'<div class="box"><h4>Recommended action</h4><ul>{rows}</ul></div>'


def _sources_list(opp):
    items = opp.get("items") or []
    if not items:
        return ""
    tag = {"fan": "fan", "moment": "moment", "news": "news", "utility": "utility"}
    rows = ""
    for it in items[:5]:
        link = (f'<a href="{esc(it["url"])}" target="_blank" rel="noopener">{esc(it["text"])}</a>'
                if it.get("url") else esc(it["text"]))
        rows += (f'<li>{link} <span class="muted small">— {esc(it["source"])} · '
                 f'{tag.get(it.get("demand", ""), it.get("demand", ""))} · '
                 f'{esc(_age(it.get("age_min")))}</span></li>')
    return f'<div class="box"><h4>Evidence — what was actually published</h4><ul>{rows}</ul></div>'


def _opportunity_card(opp, payload):
    com = opp["commercial"]
    design = com.get("design") or {}
    signal = opp.get("fan_signal") or {}
    head = f"""<div class="opp-head">
 <span class="rank">#{opp['rank']}</span>
 <span class="ttl">{esc(opp['title'])}</span>
 <span class="badge lvl-{esc(opp['level'])}">{esc(opp['level'])}</span>
 <span class="badge quiet">{esc(opp['team_label'])}</span>
 <span class="conf">{opp['confidence']}%</span>
 <span>{esc(opp['status_emoji'])} {esc(opp['status'])}</span>
</div>"""
    signal_html = ""
    if signal.get("quote"):
        # Say what the line actually is. Until a fan connector is attached this is
        # journalism, and the board must not dress it up as a fan quote.
        label = "Fan signal" if signal.get("demand") == "fan" else "Signal (news-sourced - no fan connector)"
        signal_html = f"""<div class="quote"><div class="muted small">{esc(label)}</div>
 <p>“{esc(signal['quote'])}”</p>
 <div class="muted small">{esc(signal.get('outlet') or signal.get('source') or '')} · {esc(_age(signal.get('age_min')))}
 · {esc(signal.get('demand') or signal.get('kind') or '')}</div></div>"""
    match_line = (f'{esc(design.get("title"))} {esc(design.get("price", ""))}'
                  if design.get("title") else "no matched design")
    return f"""<div class="opp">
{head}
<div class="muted small">{esc(opp['team_full'])} · {esc(opp['nick'])} · matched design: {match_line}</div>
{signal_html}
<div class="small" style="margin-top:8px"><b>Why fans care:</b> {esc(opp['why'])}</div>
{_evidence_grid(opp, payload)}
<div class="bar" title="confidence {opp['confidence']}%"><i style="width:{opp['confidence']}%"></i></div>
{_commercial_box(opp)}
{_action_box(opp)}
{_sources_list(opp)}
<div class="muted small" style="margin-top:8px">Status {esc(opp['status_emoji'])} {esc(opp['status'])} — {esc(opp['status_why'])}</div>
</div>"""


def _filtered_section(payload):
    rows = ""
    for opp in payload["filtered"]:
        e = opp["evidence"]
        rows += (f'<li><b>{esc(opp["team_label"])}</b> — {esc(opp["title"])} '
                 f'<span class="muted small">({e["items"]} reaction item(s), {e["sources"]} outlet(s), '
                 f'confidence {opp["confidence"]}%, {esc(opp["commercial"]["type"])} match)</span></li>')
    ladder = "".join(
        f'<div><span class="badge lvl-{esc(step["level"])}">{esc(step["level"])}</span>'
        f'<span class="small">{esc(step["rule"])}</span>'
        f'<span class="muted small">{"shown" if step["shown"] else "filtered off the board"}</span></div>'
        for step in payload["ladder"]
    )
    if not rows:
        rows = '<li class="muted">Nothing was filtered this run — every tracked topic cleared SIGNAL.</li>'
    counts = payload["counts"]
    tally = " · ".join(f"{lvl} {counts.get(lvl, 0)}" for lvl in
                       ("ACTION", "OPPORTUNITY", "TREND", "SIGNAL", "HEADLINE"))
    return f"""<section>
 <h2>🚫 Filtered as HEADLINE — {len(payload['filtered'])} topic(s)</h2>
 <p class="muted small">A published story is not a trend. These topics had coverage but not a
 reaction: too few items, one outlet, or nothing but TV listings. They are listed so you can see
 what was dropped and why — they never become a card, and they never earn an article.</p>
 <div class="card"><ul>{rows}</ul>
 <div class="muted small" style="margin-top:8px">This run: {esc(tally)}</div>
 <h3>The ladder</h3><div class="ladder">{ladder}</div></div>
</section>"""


def _articles_section(articles):
    if not articles:
        return """<section>
 <h2>📝 Article Ideas — Medium / Quora / Reddit</h2>
 <div class="card"><p class="muted">No article ideas. Articles are only drafted for OPPORTUNITY
 and above — confidence ≥ 60 with a design that matches. Nothing today cleared that bar, and a
 headline does not earn a 900-word post.</p></div>
</section>"""
    cards = ""
    for art in articles:
        outline = "".join(f"<li>{esc(o)}</li>" for o in art["outline"])
        cards += f"""
        <div class="item">
          <b>[{esc(art['type'])}] {esc(art['title'])}</b>
          <div class="muted small">Team: {esc(art['team'])} • Where: {esc(art['where'])}</div>
          <div style="margin:8px 0"><b>Angle:</b> {esc(art['angle'])}<br><b>Link to:</b> <span class="kbd">{esc(art['link'])}</span></div>
          <div><b>Outline:</b><ul>{outline}</ul></div>
          <div class="small"><b>Evidence:</b> {esc(art['evidence'])}</div>
          <div class="small"><b>Image idea:</b> {esc(art['image_idea'])}</div>
        </div>"""
    return f"""<section>
 <h2>📝 Article Ideas — Medium / Quora / Reddit</h2>
 <p class="muted small">Only for OPPORTUNITY and above: a trend, a matched design and commercial
 intent. You write it in your voice and post it yourself — nothing auto-publishes.</p>
 <div class="grid">{cards}</div>
</section>"""


def _board_section(payload):
    board = payload.get("board")
    if not board:
        return """<div class="card"><p class="muted">No opportunity cleared SIGNAL this run.
 Nothing to post — that is the correct answer when the evidence is not there.</p></div>"""
    return f"""<div class="board">
 <h2>🎯 Best thing Gridiron Locker should do right now</h2>
 <p class="answer">{esc(board['answer'])}</p>
 <div class="facts">
  <div><span>Team</span><b>{esc(board['team'])}</b></div>
  <div><span>Product</span><b>{esc(board['product'])}</b></div>
  <div><span>Platform</span><b>{esc(board['platform'])}</b></div>
  <div><span>Timing</span><b>{esc(board['timing'])}</b></div>
  <div><span>Confidence</span><b>{board['confidence']}% · {esc(board['level'])}</b></div>
  <div><span>Status</span><b>{esc(board['status_emoji'])} {esc(board['status'])}</b></div>
 </div>
 <div class="small" style="margin-top:10px"><b>Creative angle:</b> {esc(board['creative'])}</div>
 <div class="small"><b>Campaign:</b> {esc(board['campaign'])}</div>
 <div class="small muted" style="margin-top:6px"><b>Why:</b> {esc(board['why'])}</div>
</div>"""


def _team_strip(payload):
    cells = ""
    for team, meta in payload["teams"].items():
        game = meta["game"]
        cells += (f'<div><span>{esc(meta["short"])}</span>'
                  f'<b>{meta["shown"]} shown · {meta["filtered"]} filtered</b>'
                  f'<i>{esc(game.get("label", ""))}</i></div>')
    return f'<div class="facts" style="margin-top:14px">{cells}</div>'


def render(d):
    counts = d["counts"]
    opportunities = d["opportunities"]
    articles = d["articles"]
    cards = "".join(_opportunity_card(o, d) for o in opportunities)
    if not cards:
        cards = ("<div class='card'><p class='muted'>Nothing cleared SIGNAL. No fan reaction, "
                 "no trend, no post. Run <span class='kbd'>python3 src/trends.py</span> and "
                 "<span class='kbd'>python3 marketing/social_watch.py</span> to refresh the "
                 "evidence.</p></div>")

    connector_rows = "".join(
        f'<li><b>{esc(name)}</b> — {esc(meta.get("status"))}'
        + (f' <span class="muted small">{esc(meta.get("reason"))}</span>' if meta.get("reason") else "")
        + f' <span class="muted small">({meta.get("items", 0)} items)</span></li>'
        for name, meta in (d.get("connectors") or {}).items()
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>HQ - Hunter | Gridiron Locker</title>
<style>{css()}</style>
</head>
<body>
<div class="topbar"><div class="topbar-inner">
 <div class="brand">HUNTER<small>Gridiron Locker - You post, I hunt</small></div>
 <span class="pill">Trend data: {esc(d['generated'])} • {len(opportunities)} opportunities • {len(articles)} article ideas • {counts.get('HEADLINE', 0)} headlines filtered</span>
</div></div>
<main class="wrap">
<section>
 <h1>You post, <span style="color:var(--green)">I hunt</span></h1>
 <p class="lead">I hunt fan demand, not headlines. Every card below has evidence, a matched
 design, a platform plan and a confidence score. A single published story is a HEADLINE and is
 filtered off this board — only SIGNAL and above is shown, and only OPPORTUNITY and above earns
 an article idea.</p>
 {_board_section(d)}
 {_team_strip(d)}
</section>

<section>
 <h2>🔥 Opportunities — ranked by confidence</h2>
 <p class="muted small">Ranked by level, then confidence, then how fresh and shippable they are.
 Evidence is real: outlet names, timestamps and velocity measured on the items below. Fan-post
 counts are zero while X and Reddit are disconnected — see the connector list at the bottom.</p>
 {cards}
</section>

{_articles_section(articles)}

{_filtered_section(d)}

<section>
 <h2>How to use</h2>
 <div class="card">
  <p><b>Start at the top.</b> The green card answers "what do we do right now". Post that, on that
  platform, at that time. The rest of the list is the queue behind it.</p>
  <p><b>Read the evidence before you post.</b> Fan discussion, phrase velocity, outlets, sentiment,
  game state and confidence are all measured from the files named at the bottom — nothing here is
  guessed. If the fan-discussion row says zero, the level was earned on journalism, not fans, and
  the confidence is capped for exactly that reason.</p>
  <p><b>Commercial match first, caption second.</b> The box names the design that answers the
  demand and the creative angle for it. "Sellable" means it is in the live catalogue with a real
  buy link; "crawl artefact" means the campaign may be gone — check before you post it.</p>
  <p><b>Articles only for OPPORTUNITY+.</b> Medium / Quora / Reddit drafts appear only when there
  is a trend, a matched design and commercial intent. Write them in your voice, post them
  yourself.</p>
  <p><b>Filtered is not hidden.</b> HEADLINE-level topics are listed with their counts so you can
  see what was dropped and why.</p>
  <h3>Data + connectors</h3>
  <p class="muted small">Sources: <span class="kbd">data/trends.json</span> (headlines,
  entity_mentions, fan_trend_index, top_terms) · <span class="kbd">marketing/social-signals.json</span>
  (reddit, google_news, x when configured) · <span class="kbd">data/products_live.json</span> +
  <span class="kbd">data/catalogue-live.json</span> (commercial match and sellable check).</p>
  <ul class="small">{connector_rows}</ul>
  <p class="muted small">Generated {esc(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))} by src/hq.py
  • signals snapshot {esc(d.get('signals_generated') or '-')} • as of {esc(d.get('as_of') or '-')}
  • Next: <span class="kbd">python3 src/trends.py</span> then
  <span class="kbd">python3 marketing/social_watch.py</span> to refresh</p>
 </div>
</section>

<footer><div class="wrap"><span>Hunter • you post, I hunt • noindex</span><span>Gridiron Locker</span></div></footer>
</main>
</body>
</html>
"""


def build_board():
    """Run the intelligence layer and hand back its payload."""
    if HI is None:
        raise RuntimeError(f"hunter_intelligence unavailable: {HI_IMPORT_ERROR}")
    return HI.hunt_opportunities()


def write_report(payload):
    """trend-report.md - the same board as plain text."""
    board = payload.get("board") or {}
    lines = [f"# Hunt Report - {payload['generated']}", "",
             f"Generated: {payload.get('as_of', '')} by src/hunter_intelligence.py", "",
             f"Ladder: {' · '.join(f'{k} {v}' for k, v in payload['counts'].items())}", "",
             f"Fan connectors: {payload['fan_note']}", "",
             "## What to do right now", ""]
    if board:
        lines += [f"**{board['answer']}**", "",
                  f"- Product: {board['product']} {board.get('product_url', '')}",
                  f"- Platform: {board['platform']} · Timing: {board['timing']}",
                  f"- Confidence: {board['confidence']}% ({board['level']}) · {board['status_emoji']} {board['status']}",
                  f"- Campaign: {board.get('campaign', '')}",
                  f"- Creative: {board.get('creative', '')}",
                  f"- Why: {board.get('why', '')}", ""]
    else:
        lines += ["Nothing cleared SIGNAL this run - the correct answer is not to post.", ""]

    lines += ["## Opportunities (SIGNAL and above)", ""]
    for opp in payload["opportunities"]:
        e = opp["evidence"]
        com = opp["commercial"]
        design = com.get("design") or {}
        signal = opp.get("fan_signal") or {}
        lines += [
            f"### {opp['rank']}. {opp['title']} - {opp['team_full']}",
            f"- Level: {opp['level']} · Confidence: {opp['confidence']}% · {opp['status_emoji']} {opp['status']} ({opp['status_why']})",
            f"- Fan signal: \"{signal.get('quote', '')}\" - {signal.get('outlet', '')} ({_age(signal.get('age_min'))})",
            f"- Evidence: {e['items']} reaction items ({e['weighted']} weighted) · {e['sources']} outlets"
            f" · {e['utility']} utility listings excluded · {e['fan_posts']} fan posts",
            f"- Phrase velocity: {e['velocity'].get('label', '')}",
            f"- Sentiment: {e['sentiment'].get('label', '')} - {e['sentiment'].get('note', '')}",
            f"- Game state: {e['game'].get('label', '')}",
            f"- Commercial: {com.get('type')} - {design.get('title', 'none')}"
            f" {design.get('price', '')} {'(sellable)' if design.get('sellable') else '(crawl artefact)'}"
            f" - {com.get('campaign', '')}",
            f"- Why fans care: {opp.get('why', '')}",
        ]
        if e.get("entities"):
            lines.append("- Tracked names: " + "; ".join(
                f"{ent['name']} ({ent['mentions']} window mentions, FTI {ent['fti']})"
                for ent in e["entities"]))
        for act in opp.get("actions") or []:
            lines.append(f"- Action: {act['platform']} - {act['play']} ({act['when']})")
        for it in (opp.get("items") or [])[:4]:
            lines.append(f"  - {it['text']} - {it['source']} ({_age(it.get('age_min'))}) {it.get('url', '')}")
        lines.append("")

    lines += [f"## Filtered as HEADLINE ({len(payload['filtered'])})", ""]
    for opp in payload["filtered"]:
        e = opp["evidence"]
        lines.append(f"- {opp['team_label']} - {opp['title']}: {e['items']} reaction item(s), "
                     f"{e['sources']} outlet(s), confidence {opp['confidence']}% - not a reaction")
    lines.append("")

    lines += ["## Article ideas (OPPORTUNITY+ only)", ""]
    if not payload["articles"]:
        lines.append("- None. Articles need confidence >= 60 plus a matched design.")
    for art in payload["articles"]:
        lines += [f"- **[{art['type']}] {art['title']}**",
                  f"  - Where: {art['where']}",
                  f"  - Angle: {art['angle']}",
                  f"  - Link: {art['link']}",
                  f"  - Image: {art['image_idea']}", ""]
    return "\n".join(lines) + "\n"


def main():
    payload = build_board()
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render(payload))
    try:
        with open(os.path.join(ROOT, "trend-report.md"), "w", encoding="utf-8") as fh:
            fh.write(write_report(payload))
    except Exception as e:  # the dashboard is the deliverable; the report is not
        print(f"Failed to write trend-report.md: {e}")

    counts = payload["counts"]
    print(f"HQ hunter: {len(payload['opportunities'])} opportunities "
          f"({counts.get('ACTION', 0)} action / {counts.get('OPPORTUNITY', 0)} opportunity / "
          f"{counts.get('TREND', 0)} trend / {counts.get('SIGNAL', 0)} signal), "
          f"{counts.get('HEADLINE', 0)} headlines filtered, {len(payload['articles'])} article ideas, "
          f"data {payload['generated']}")
    if payload.get("board"):
        print(f"  best move: {payload['board']['answer']}")
    return payload


if __name__ == "__main__":
    main()
