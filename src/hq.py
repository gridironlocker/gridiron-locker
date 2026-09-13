#!/usr/bin/env python3
"""Simplified HQ - Hunter + Article Factory.

You post, I hunt. No more scout/marketing dashboards.

This generates ops/hq/index.html with:
1. Today's Hunt - what fans are talking about per team
2. What to Post - social ideas (you create caption/image and post)
3. Article Ideas - Medium / Quora / Reddit drafts (you post yourself)

Usage:
    python3 src/hq.py
"""
import datetime
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "ops", "hq")
TRENDS_PATH = os.path.join(ROOT, "data", "trends.json")

def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)

def load_json(rel, default):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default

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
"""

def build_hunt():
    trends = load_json("data/trends.json", {})
    generated = trends.get("generated", "-")
    collections = trends.get("collections", {})
    
    # For article ideas, also load product gaps if available
    try:
        sys.path.insert(0, os.path.join(ROOT, "src"))
        import build as B
        all_slugs = {it["slug"] for it in B.ALL}
    except Exception:
        all_slugs = set()
        B = None

    hunt = []
    article_ideas = []

    # Process each collection
    for ckey, cdata in collections.items():
        headlines = cdata.get("headlines", [])[:8]  # top 8
        entities = cdata.get("entities", {})  # name -> mentions etc or list?
        # entities format varies - handle both dict and list
        # In trends.json, entities is often dict of name -> {mentions, fti, status}
        # Let's normalize
        top_entities = []
        if isinstance(entities, dict):
            for name, info in entities.items():
                if isinstance(info, dict):
                    mentions = info.get("mentions", 0)
                    fti = info.get("fti", info.get("FTI", 0))
                    status = info.get("status", "steady")
                else:
                    mentions = info
                    fti = 0
                    status = "steady"
                top_entities.append((name, mentions, fti, status))
        elif isinstance(entities, list):
            # list of dicts
            for e in entities:
                if isinstance(e, dict):
                    name = e.get("name") or e.get("entity") or str(e)
                    mentions = e.get("mentions", 0)
                    fti = e.get("fti", e.get("FTI", 0))
                    status = e.get("status", "steady")
                    top_entities.append((name, mentions, fti, status))
        
        top_entities.sort(key=lambda x: x[1], reverse=True)
        
        # Build hunt items for this collection
        for name, mentions, fti, status in top_entities[:3]:  # top 3 per collection
            if mentions == 0:
                continue
            # Find related headlines
            related = [h for h in headlines if name.split()[0].lower() in (h.get("title","").lower())][:3]
            hunt.append({
                "collection": ckey,
                "entity": name,
                "mentions": mentions,
                "fti": fti,
                "status": status,
                "headlines": related or headlines[:2],
                "gap": name.replace(" ","-") not in all_slugs if all_slugs else False
            })

            # Article idea for trending entity
            if mentions >= 2:
                # Medium idea
                article_ideas.append({
                    "type": "Medium",
                    "collection": ckey,
                    "entity": name,
                    "title": f"{name.title()} Is Trending: What {ckey.replace('-',' ').title()} Fans Are Saying Right Now",
                    "angle": f"Why {name.title()} is hot today, fan reactions, and best gift ideas for {ckey.replace('-',' ')} fans",
                    "where": "Medium - publication: NFL Fan Culture, Football Life",
                    "outline": [
                        f"Hook: {name.title()} is everywhere today ({mentions} mentions)",
                        "What happened (use 1-2 headlines)",
                        "Fan reaction - what people are saying",
                        f"Gift idea: link to your {ckey} shirt (if you have it) or suggest making one",
                        "Close with question to drive comments"
                    ],
                    "image_idea": f"Photo of {name.title()} or fan crowd + your {ckey} shirt mockup side by side",
                    "link": f"/{ckey}-shirts/ or specific product if you have {name.replace(' ','-')} design"
                })
                # Quora idea
                article_ideas.append({
                    "type": "Quora",
                    "collection": ckey,
                    "entity": name,
                    "title": f"Why is {name.title()} trending among {ckey.replace('-',' ').title()} fans?",
                    "angle": "Answer a real Quora question",
                    "where": f"Quora - search: '{name} {ckey}' and answer top question",
                    "outline": [
                        "Answer: here's why trending (1 paragraph)",
                        "Add context from headlines",
                        "Mention you run a fan store, link to relevant collection as source for fans",
                        "End with helpful tip, not salesy"
                    ],
                    "image_idea": f"Simple graphic: {name.title()} stats or quote",
                    "link": f"/{ckey}-shirts/"
                })
                # Reddit idea
                article_ideas.append({
                    "type": "Reddit",
                    "collection": ckey,
                    "entity": name,
                    "title": f"{ckey.replace('-',' ').title()}: {name.title()} discussion + vintage fan gear",
                    "angle": f"Join r/{ckey.split('-')[0]} or r/nfl discussion",
                    "where": f"Reddit - r/Browns, r/GreenBayPackers, r/cowboys, r/MichiganWolverines",
                    "outline": [
                        f"Post about {name.title()} news, ask fans opinion",
                        "In comments, share your vintage design if relevant (don't spam OP)",
                        "Be a fan first, store second"
                    ],
                    "image_idea": f"Game photo or your shirt flatlay, not too promo",
                    "link": f"Only in comments if asked, or profile link"
                })

    # If no hunt data, fallback to headlines
    if not hunt:
        for ckey, cdata in collections.items():
            headlines = cdata.get("headlines", [])[:3]
            for h in headlines:
                hunt.append({
                    "collection": ckey,
                    "entity": h.get("title","Trending")[:40],
                    "mentions": 1,
                    "fti": 0,
                    "status": "trending",
                    "headlines": [h],
                    "gap": False
                })

    return {
        "generated": generated,
        "hunt": hunt[:12],  # max 12
        "articles": article_ideas[:12],  # max 12
        "collections": collections
    }

def render(d):
    gen = d["generated"]
    hunt = d["hunt"]
    articles = d["articles"]

    hunt_html = ""
    for item in hunt:
        headlines_html = "".join(
            f'<li><a href="{esc(h.get("url",""))}" target="_blank">{esc(h.get("title",""))}</a> <span class="muted small">— {esc(h.get("source",""))}</span></li>'
            for h in item["headlines"][:3]
        )
        badge_class = "trending" if item["status"]=="trending" else "steady" if item["status"]=="steady" else "quiet"
        gap_note = " <span class='badge trending'>GAP - no design yet</span>" if item["gap"] else ""
        # Post idea
        collection_nice = item["collection"].replace("-"," ").title()
        post_idea = f"{item['entity'].title()} is hot in {collection_nice}. Fans talking about it now. Post your {collection_nice} shirt with angle: '{item['entity'].title()} moment'"

        hunt_html += f"""
        <div class="item">
          <b>{esc(item['entity'].title())} <span class="badge {badge_class}">{esc(item['status'])} {item['mentions']} mentions</span>{gap_note}</b>
          <div class="muted small">{esc(collection_nice)} • FTI {esc(item['fti'])}</div>
          <div style="margin:8px 0"><b>What they talking about:</b><ul>{headlines_html}</ul></div>
          <div class="small"><b>Post idea for you:</b> {esc(post_idea)}<br><b>Image idea:</b> {esc(item['entity'].title())} + your {esc(collection_nice)} tee mockup</div>
        </div>
        """

    articles_html = ""
    for art in articles:
        outline_html = "".join(f"<li>{esc(o)}</li>" for o in art["outline"])
        articles_html += f"""
        <div class="item">
          <b>[{esc(art['type'])}] {esc(art['title'])}</b>
          <div class="muted small">Collection: {esc(art['collection'])} • Entity: {esc(art['entity'])} • Where: {esc(art['where'])}</div>
          <div style="margin:8px 0"><b>Angle:</b> {esc(art['angle'])}<br><b>Link to:</b> <span class="kbd">{esc(art['link'])}</span></div>
          <div><b>Outline:</b><ul>{outline_html}</ul></div>
          <div class="small"><b>Image idea:</b> {esc(art['image_idea'])}</div>
        </div>
        """

    if not hunt_html:
        hunt_html = "<p class='muted'>No trends today — data/trends.json empty or old. Run src/trends.py</p>"
    if not articles_html:
        articles_html = "<p class='muted'>No article ideas — need trending entities with mentions >=2</p>"

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
 <span class="pill">Trend data: {esc(gen)} • {len(hunt)} hunts • {len(articles)} article ideas</span>
</div></div>
<main class="wrap">
<section>
 <h1>You post, <span style="color:var(--green)">I hunt</span></h1>
 <p class="lead">No more dashboards. I hunt what fans talk about, you create caption/image and post yourself. For Medium/Quora/Reddit, I draft article + image idea, you post yourself. Safe for Google, no auto-spam.</p>
</section>

<section>
 <h2>🔥 Today's Hunt — What they talking about</h2>
 <p class="muted small">Each card = one trending topic. Headlines are real from Google News. Post idea is for YOU to make and post on socials.</p>
 <div class="grid">{hunt_html}</div>
</section>

<section>
 <h2>📝 Article Ideas — Medium / Quora / Reddit</h2>
 <p class="muted small">I draft, you post yourself. Each has title, where to post, outline, image idea, and where to link. 2-3 per week max, white-hat.</p>
 <div class="grid">{articles_html}</div>
</section>

<section>
 <h2>How to use</h2>
 <div class="card">
  <p><b>Social:</b> Pick 1-2 hunts/day, make your own image + caption (your style), post to Pinterest, FB, X, Insta. You know your audience best.</p>
  <p><b>Articles:</b> Pick 1 article idea, copy title/outline, write in your voice (or use draft as base), add image idea, post on Medium/Quora/Reddit yourself. Link back naturally to /collections/ or product.</p>
  <p><b>Safe:</b> Nothing auto-posts. You approve everything. No thin content on main site. Backlinks are off-site, helpful, not spammy.</p>
  <p class="muted small">Generated {esc(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))} by src/hq.py • Data: data/trends.json • Next: python3 src/trends.py to refresh</p>
 </div>
</section>

<footer><div class="wrap"><span>Hunter • you post, I hunt • noindex</span><span>Gridiron Locker</span></div></footer>
</main>
</body>
</html>
"""

def main():
    d = build_hunt()
    out_html = render(d)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(out_html)
    
    # Also write a simple markdown report for easy reading
    md_path = os.path.join(ROOT, "trend-report.md")
    try:
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(f"# Hunt Report - {d['generated']}\n\n")
            fh.write(f"Generated: {datetime.datetime.utcnow().isoformat()} UTC\n\n")
            fh.write("## Today's Hunt\n\n")
            for item in d["hunt"]:
                fh.write(f"- **{item['entity'].title()}** ({item['collection']}) - {item['mentions']} mentions, FTI {item['fti']}, {item['status']}\n")
                for h in item["headlines"][:2]:
                    fh.write(f"  - {h.get('title','')} - {h.get('source','')} - {h.get('url','')}\n")
                fh.write(f"  - Post idea: {item['entity'].title()} hot in {item['collection']}\n\n")
            fh.write("## Article Ideas\n\n")
            for art in d["articles"]:
                fh.write(f"- **[{art['type']}] {art['title']}**\n")
                fh.write(f"  - Where: {art['where']}\n")
                fh.write(f"  - Angle: {art['angle']}\n")
                fh.write(f"  - Link: {art['link']}\n")
                fh.write(f"  - Image: {art['image_idea']}\n\n")
    except Exception as e:
        print(f"Failed to write md: {e}")

    print(f"HQ hunter generated: {len(d['hunt'])} hunts, {len(d['articles'])} articles, data {d['generated']}")

if __name__ == "__main__":
    main()
