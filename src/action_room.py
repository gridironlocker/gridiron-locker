#!/usr/bin/env python3
"""Build an evidence-first marketing action room from existing trend data."""
from pathlib import Path
import datetime as dt
import html
import json
import re

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ops" / "action"
DATA = ROOT / "data" / "trends.json"
SOCIAL = ROOT / "marketing" / "social-signals.json"

TEAMS = {
    "cleveland-browns": "Cleveland Browns",
    "green-bay-packers": "Green Bay Packers",
    "michigan": "Michigan Wolverines",
    "dallas-cowboys": "Dallas Cowboys",
}
WEIGHTS = {"trend":25,"search":20,"fan":15,"competition":15,"product":15,"commercial":10}
STOP = set("the and for with from this that are was were have has had your you our their about into today game games week watch live what when where how who why".split())

def read(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def norm(v): return re.sub(r"[^a-z0-9 ]+", " ", str(v or "").lower()).strip()

def products():
    data = read(ROOT/"data"/"products.json", {})
    if not data: data = read(ROOT/"data"/"products_live.json", {})
    order = read(ROOT/"data"/"order.json", [])
    out=[]
    for row in order:
        p=data.get(row.get("slug"), {})
        if not p: continue
        slug=row.get("slug")
        out.append({"slug":slug,"team":row.get("col"),"title":p.get("title",slug),"text":norm(p.get("title","")+" "+p.get("desc","")),"url":"https://gridironlocker.store/shop/"+slug+"/","image":p.get("front","")})
    return out

def phrases(items):
    c={}
    for item in items:
        words=[w for w in norm(item.get("text","")).split() if len(w)>2 and w not in STOP]
        for n in (2,3):
            for i in range(len(words)-n+1):
                p=" ".join(words[i:i+n])
                c[p]=c.get(p,0)+1
    return sorted(c.items(), key=lambda x:-x[1])[:8]

def main():
    trends=read(DATA,{})
    social=read(SOCIAL,{})
    all_items=[]
    for source,payload in (social.get("sources") or {}).items():
        for item in payload.get("items",[]) or []:
            all_items.append({"source":source,"team":item.get("team"),"text":item.get("text","")})
    for team,col in (trends.get("collections") or {}).items():
        for h in col.get("headlines",[])[:20]: all_items.append({"source":"snapshot","team":team,"text":h.get("title","")})
    ps=products(); actions=[]
    for team,label in TEAMS.items():
        col=(trends.get("collections") or {}).get(team,{})
        em=sorted((col.get("entity_mentions") or {}).items(), key=lambda x:-int(x[1] or 0))
        team_items=[x for x in all_items if x.get("team")==team]
        pr=phrases(team_items)
        topic=pr[0][0] if pr else (em[0][0] if em else label)
        matches=[]
        for p in ps:
            if p["team"]!=team: continue
            score=sum(1 for w in norm(topic).split() if w in p["text"])*10
            if score: matches.append((score,p))
        matches.sort(key=lambda x:-x[0])
        product=matches[0][1] if matches else None
        trend=min(100,(int(em[0][1]) if em else 0)*3)
        fan=min(100,(pr[0][1] if pr else 0)*20)
        product_score=product and min(100,matches[0][0]+20) or 0
        commercial=70 if product else 30
        competition=50
        score=round(trend*.25+min(100,trend+10)*.20+fan*.15+(100-competition)*.15+product_score*.15+commercial*.10)
        confidence=min(90,35+(15 if em else 0)+(15 if pr else 0)+(15 if product else 0)+(15 if social.get("sources") else 0))
        decision="PUBLISH" if score>=70 and product else "IMPROVE" if score>=55 and product else "DESIGN GAP" if score>=55 else "MONITOR"
        actions.append({"team":team,"label":label,"topic":topic,"score":score,"confidence":confidence,"decision":decision,"product":product,"phrase":pr[:5],"entity":em[:5],"evidence_count":len(team_items)})
    actions.sort(key=lambda x:(-x["score"],-x["confidence"]))
    data={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source_date":trends.get("generated"),"weights":WEIGHTS,"top_action":actions[0] if actions else None,"actions":actions}
    (ROOT/"marketing").mkdir(exist_ok=True)
    (ROOT/"marketing"/"action-room.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    OUT.mkdir(parents=True,exist_ok=True)
    cards=[]
    for a in actions:
        p=a["product"]
        ph=a["phrase"][0][0] if a["phrase"] else "none captured"
        prod=(f'<a href="{html.escape(p["url"],quote=True)}">{html.escape(p["title"])}</a>' if p else '<span>No matching product — design gap</span>')
        cards.append(f'<article><b>{html.escape(a["label"])}</b><strong>{a["score"]}/100</strong><em>{a["decision"]}</em><h2>{html.escape(a["topic"])}</h2><p>Fan phrase: <b>{html.escape(ph)}</b></p><p>Product: {prod}</p><small>Confidence {a["confidence"]}% · {a["evidence_count"]} signals</small></article>')
    top=actions[0] if actions else None
    page='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Action Room · Gridiron Locker</title><style>body{margin:0;background:#07101d;color:#eef5ff;font:15px/1.5 system-ui}main{max-width:1100px;margin:auto;padding:30px}article{background:#0e1b2e;border:1px solid #29405e;border-radius:16px;padding:18px;margin:12px 0}strong{float:right;font-size:22px}em{display:inline-block;margin-left:10px;padding:3px 8px;border-radius:12px;background:#72e0ba;color:#062b1c;font-style:normal;font-size:11px;font-weight:800}h1{font-size:34px}h2{color:#7cc8ff}a{color:#7cc8ff}small{color:#91a5c1}</style><main><h1>⚡ ACTION ROOM</h1><p>Evidence → opportunity → product → action. A recommendation room, not an auto-publisher.</p>'''+(''.join(cards))+f'<p><small>Generated {html.escape(data["generated_at"])} · source snapshot {html.escape(str(data["source_date"]))}</small></p></main>'
    (OUT/"index.html").write_text(page,encoding="utf-8")
    print("action room generated",len(actions))

if __name__=="__main__": main()
