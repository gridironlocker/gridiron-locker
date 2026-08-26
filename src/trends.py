#!/usr/bin/env python3
"""Fetch live headlines per collection and score which designs are trending.

Runs on a schedule from GitHub Actions. Writes data/trends.json which build.py
reads to (a) tag products Trending / Throwback automatically and (b) publish a
real, sourced "latest headlines" block on collection pages and the season hub.

No API keys required - uses public Google News RSS.
"""
import json, os, re, sys, html, datetime
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from collections_data import COLLECTIONS, ORDER
from viralstyle import make_session

UA = {"User-Agent": "Mozilla/5.0 (compatible; GridironLockerBot/1.0)"}
WINDOW_DAYS = 10

# Query used against Google News, per collection
QUERIES = {
    "cleveland-browns": "Cleveland Browns",
    "green-bay-packers": "Green Bay Packers",
    "dallas-cowboys": "Dallas Cowboys",
    "michigan": "Michigan Wolverines football",
}

# People a design might reference. Each entry: canonical -> match patterns.
# Multi-word patterns avoid false hits on common words like "love".
ENTITIES = {
    "cleveland-browns": {
        "shedeur sanders": ["shedeur", "sanders"],
        "deshaun watson": ["deshaun watson", "watson"],
        "joe flacco": ["flacco"],
        "myles garrett": ["myles garrett", "garrett"],
        "kevin stefanski": ["stefanski"],
        "denzel ward": ["denzel ward"],
        "todd monken": ["monken"],
    },
    "green-bay-packers": {
        "jordan love": ["jordan love"],
        "micah parsons": ["micah parsons", "parsons"],
        "robert tonyan": ["tonyan"],
        "josh jacobs": ["josh jacobs"],
        "matt lafleur": ["lafleur"],
    },
    "michigan": {
        "bryce underwood": ["bryce underwood", "underwood"],
        "jj mccarthy": ["mccarthy", "j.j. mccarthy"],
        "kyle whittingham": ["whittingham"],
        "jordan marshall": ["jordan marshall"],
    },
    "dallas-cowboys": {
        "dak prescott": ["dak prescott", "prescott"],
        "ceedee lamb": ["ceedee lamb", "ceedee"],
    },
}

# Design-text tokens -> entity. Used to connect a product to a person.
DESIGN_TOKENS = {
    "cleveland-browns": {
        "sanders": "shedeur sanders", "shedeur": "shedeur sanders",
        "flacco": "joe flacco", "joe ": "joe flacco",
        "garrett": "myles garrett", "myles": "myles garrett",
        "stefanski": "kevin stefanski", "kevin": "kevin stefanski",
        "dawgfather": "kevin stefanski", "denzel": "denzel ward",
    },
    "green-bay-packers": {
        "jordan": "jordan love", "10ve": "jordan love", "love": "jordan love",
        "tonyan": "robert tonyan", "parsons": "micah parsons",
    },
    "michigan": {
        "mccarthy": "jj mccarthy", "underwood": "bryce underwood",
    },
    "dallas-cowboys": {},
}

HOT_MIN = 3          # >= this many mentions in the window = trending
THROWBACK_MAX = 0    # <= this many mentions = throwback

# Opponent / unrelated team names that can leak into the ticker from live news
# (e.g. "Cardinals" because Dallas played them in preseason). We sell four teams
# only, so keep other NFL/college team names out of headlines and the moving bar.
OTHER_TEAMS = set("""
cardinals bills broncos denver seahawks saints giants eagles chiefs steelers ravens
bengals texans colts titans jaguars raiders chargers rams 49ers lions bears vikings
panthers falcons buccaneers dolphins jets patriots commanders titans buffalo minnesota
missouri notre dame alabama georgia tennessee tcu oklahoma arizona washington
""".split())


def strip_tags(t):
    return re.sub(r"<[^>]+>", "", html.unescape(t or "")).strip()


SESSION = make_session()


def fetch(ckey):
    q = quote(QUERIES[ckey] + f" when:{WINDOW_DAYS}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    root = None
    for attempt in range(3):
        try:
            r = SESSION.get(url, headers=UA, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            root = ET.fromstring(r.content)
            break
        except Exception as e:
            print(f"  ! {ckey}: feed error (try {attempt+1}/3) {e}")
            if attempt < 2:
                import time as _t
                _t.sleep(2 * (attempt + 1))
    if root is None:
        return []
    out = []
    for it in root.findall(".//item"):
        title = strip_tags(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        src_el = it.find("source")
        src = strip_tags(src_el.text) if src_el is not None else ""
        if not title:
            continue
        # Google News puts " - Source" at the end of titles
        if src and title.endswith(" - " + src):
            title = title[: -(len(src) + 3)].strip()
        out.append({"title": title, "url": link, "source": src, "pub": pub})
    return out


def main():
    today = datetime.date.today().isoformat()
    data = {"generated": today, "window_days": WINDOW_DAYS, "collections": {}}

    # Previous run's data. If a feed fails today we reuse it rather than writing
    # zeroed mention counts - zeros would flip every "Trending" badge on the
    # site to "Throwback" and rewrite the season hub with empty headlines.
    prev_path = os.path.join(ROOT, "data", "trends.json")
    try:
        prev = json.load(open(prev_path)).get("collections", {})
    except Exception:
        prev = {}
    stale = []

    for ckey in ORDER:
        items = fetch(ckey)
        if not items and prev.get(ckey, {}).get("headlines"):
            print(f"  !! {ckey}: feed empty - reusing previous trend data")
            data["collections"][ckey] = prev[ckey]
            stale.append(ckey)
            continue
        blob = " ".join(i["title"] for i in items).lower()

        counts = {}
        for canon, pats in ENTITIES.get(ckey, {}).items():
            n = 0
            for p in pats:
                n += len(re.findall(r"\b" + re.escape(p) + r"\b", blob))
            counts[canon] = n

        # headline keywords: most common meaningful words, for the ticker
        words = re.findall(r"[a-z]{4,}", blob)
        stop = set("""with from that this what will have they team game games season week
            news says said after before their there could would about into more than when
            first over back down being under while play plays player players report reports
            preseason camp""".split())
        freq = {}
        for w in words:
            if w in stop or w in OTHER_TEAMS:
                continue
            freq[w] = freq.get(w, 0) + 1
        top = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:12]]

        # entities in the news that we have NO product for = revenue gap
        toks = DESIGN_TOKENS.get(ckey, {})
        covered = set(toks.values())
        gaps = [e for e, n in counts.items() if n >= HOT_MIN and e not in covered]

        data["collections"][ckey] = {
            "gaps": gaps,
            "query": QUERIES[ckey],
            "headlines": items[:8],
            "entity_mentions": counts,
            "top_terms": top,
            "headline_count": len(items),
        }
        if gaps:
            print(f"    OPPORTUNITY - trending with no design: {', '.join(gaps)}")
        hot = [k for k, v in counts.items() if v >= HOT_MIN]
        cold = [k for k, v in counts.items() if v <= THROWBACK_MAX]
        print(f"  {ckey}: {len(items)} headlines | hot={hot} | quiet={cold}")

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    out = os.path.join(ROOT, "data", "trends.json")

    if stale:
        data["stale_collections"] = stale
    # If every feed failed there is nothing new to say - leave the file alone so
    # the site keeps yesterday's valid trend scoring.
    if len(stale) == len(ORDER) and prev:
        print("  !! all feeds failed - leaving data/trends.json untouched")
        return
    json.dump(data, open(out, "w"), indent=1)
    print(f"wrote {out}" + (f" (stale: {', '.join(stale)})" if stale else ""))

    lines = [f"# Trend report - {today}", "",
             f"Headline window: last {WINDOW_DAYS} days. Auto-generated by src/trends.py.", ""]
    for ckey in ORDER:
        c = data["collections"][ckey]
        lines.append(f"## {COLLECTIONS[ckey]['name']}")
        lines.append("")
        mm = sorted(c["entity_mentions"].items(), key=lambda x: -x[1])
        lines.append("| Name | Headline mentions | Status |")
        lines.append("|---|---|---|")
        for name, n in mm:
            st = "TRENDING" if n >= HOT_MIN else ("quiet - throwback" if n == 0 else "steady")
            lines.append(f"| {name} | {n} | {st} |")
        if c["gaps"]:
            lines.append("")
            lines.append(f"**Product gap:** trending with no design in the catalogue - "
                         f"**{', '.join(c['gaps'])}**")
        lines.append("")
        lines.append("Recent headlines:")
        for h in c["headlines"][:5]:
            lines.append(f"- [{h['title']}]({h['url']}) - {h['source']}")
        lines.append("")
    rep = os.path.join(ROOT, "trend-report.md")
    open(rep, "w").write("\n".join(lines))
    print(f"wrote {rep}")


if __name__ == "__main__":
    main()
