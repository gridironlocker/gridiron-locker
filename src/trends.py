#!/usr/bin/env python3
"""Fetch live headlines per collection and score which designs are trending.

Runs on a schedule from GitHub Actions. Writes data/trends.json which build.py
reads to (a) tag products Trending / Throwback automatically, (b) publish a
real, sourced "latest headlines" block on collection pages and the season hub,
(c) score a Fan Trend Index (0-100 vs the hottest name in the window), and
(d) attach live player moments (headlines that name a tracked player/coach).

No API keys required - uses public Google News RSS.
"""
import json, os, re, sys, html, datetime
import xml.etree.ElementTree as ET
from urllib.parse import quote

try:
    import requests
except ImportError:  # enrich-only / unit tests don't need the network client
    requests = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from collections_data import COLLECTIONS, ORDER

# A plain browser UA: Google News rate-limits self-identifying bots hard,
# especially from datacenter IPs (GitHub Actions runners hop IP pools).
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
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

# Fan Trend Index: 0-100 scale of a tracked name vs the hottest name in the
# same 10-day headline window. Transparent and evidence-based — not a ranking
# we invent. FTI = round(100 * mentions / peak_mentions).
FTI_FORMULA = "round(100 * entity_mentions / peak_mentions_in_window)"

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


def entities_in_title(ckey, title):
    """Return tracked names that actually appear in a headline (word-boundary)."""
    blob = (title or "").lower()
    found = []
    for canon, pats in ENTITIES.get(ckey, {}).items():
        for p in pats:
            if re.search(r"\b" + re.escape(p) + r"\b", blob):
                found.append(canon)
                break
    return found


def covered_entities(ckey):
    return set(DESIGN_TOKENS.get(ckey, {}).values())


def fti_status(mentions):
    if mentions >= HOT_MIN:
        return "trending"
    if mentions <= THROWBACK_MAX:
        return "quiet"
    return "steady"


def enrich(data):
    """Turn raw headlines + mention counts into a Fan Trend Index and player moments.

    Safe to call on an already-enriched snapshot (idempotent). Does not fetch
    anything — it only reshapes the data the daily Google News crawl already
    produced, so the storefront can ship the feature even when feeds are stale.
    """
    if not isinstance(data, dict):
        return data
    cols = data.get("collections") or {}
    peak = 0
    for c in cols.values():
        for n in (c.get("entity_mentions") or {}).values():
            try:
                peak = max(peak, int(n))
            except (TypeError, ValueError):
                pass

    rows = []
    all_moments = []
    for ckey in ORDER:
        c = cols.get(ckey)
        if not c:
            continue
        covered = covered_entities(ckey)
        moments = []
        for h in c.get("headlines") or []:
            title = h.get("title") or ""
            ents = entities_in_title(ckey, title)
            if not ents:
                continue
            moment = {
                "title": title,
                "url": h.get("url") or "",
                "source": h.get("source") or "",
                "pub": h.get("pub") or "",
                "entities": ents,
                "collection": ckey,
            }
            moments.append(moment)
            all_moments.append(moment)
        c["moments"] = moments

        fti = []
        mentions = c.get("entity_mentions") or {}
        for name, n in sorted(mentions.items(), key=lambda x: (-int(x[1] or 0), x[0])):
            try:
                n = int(n)
            except (TypeError, ValueError):
                n = 0
            idx = round(100 * n / peak) if peak else 0
            row = {
                "name": name,
                "mentions": n,
                "index": idx,
                "status": fti_status(n),
                "gap": bool(n >= HOT_MIN and name not in covered),
                "shoppable": name in covered,
            }
            fti.append(row)
            rows.append(dict(row, collection=ckey))
        c["fan_trend_index"] = fti

    rows.sort(key=lambda r: (-r["index"], -r["mentions"], r["name"]))
    data["fan_trend_index"] = {
        "formula": FTI_FORMULA,
        "peak_mentions": peak,
        "window_days": data.get("window_days", WINDOW_DAYS),
        "generated": data.get("generated"),
        "rows": rows,
    }
    data["moments"] = all_moments
    return data


def write_report(data):
    today = data.get("generated") or datetime.date.today().isoformat()
    window = data.get("window_days", WINDOW_DAYS)
    fti = data.get("fan_trend_index") or {}
    rows = fti.get("rows") or []
    peak = fti.get("peak_mentions") or 0

    lines = [f"# Trend report - {today}", "",
             f"Headline window: last {window} days. Auto-generated by src/trends.py.",
             "",
             "## Fan Trend Index",
             "",
             f"FTI = `{FTI_FORMULA}`. Peak mentions in this window: **{peak}** "
             f"(that name scores 100; everyone else is relative to them).",
             "",
             "| Rank | Name | Collection | Mentions | FTI | Status | Shop |",
             "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        shop = "gap — no design" if r.get("gap") else ("in locker" if r.get("shoppable") else "—")
        lines.append(
            f"| {i} | {r['name']} | {r.get('collection','')} | {r['mentions']} | "
            f"{r['index']} | {r['status']} | {shop} |")

    lines += ["", "## Live player moments", ""]
    moments = data.get("moments") or []
    if not moments:
        lines.append("_No tracked names appeared in the captured headlines._")
        lines.append("")
    else:
        for m in moments[:24]:
            who = ", ".join(m.get("entities") or []) or "locker"
            src = f" — {m['source']}" if m.get("source") else ""
            lines.append(f"- **{who}** — [{m['title']}]({m.get('url','')}){src}")
        lines.append("")

    for ckey in ORDER:
        c = data.get("collections", {}).get(ckey, {})
        lines.append(f"## {COLLECTIONS[ckey]['name']}")
        lines.append("")
        mm = sorted((c.get("entity_mentions") or {}).items(), key=lambda x: -x[1])
        lines.append("| Name | Headline mentions | Status | FTI |")
        lines.append("|---|---|---|---|")
        by_name = {r["name"]: r for r in (c.get("fan_trend_index") or [])}
        for name, n in mm:
            st = "TRENDING" if n >= HOT_MIN else ("quiet - throwback" if n == 0 else "steady")
            idx = by_name.get(name, {}).get("index", "")
            lines.append(f"| {name} | {n} | {st} | {idx} |")
        if c.get("gaps"):
            lines.append("")
            lines.append(f"**Product gap:** trending with no design in the catalogue - "
                         f"**{', '.join(c['gaps'])}**")
        lines.append("")
        player_moments = c.get("moments") or []
        if player_moments:
            lines.append("Live player moments:")
            for h in player_moments[:5]:
                who = ", ".join(h.get("entities") or [])
                lines.append(f"- **{who}** — [{h['title']}]({h['url']}) - {h.get('source','')}")
            lines.append("")
        lines.append("Recent headlines:")
        for h in (c.get("headlines") or [])[:5]:
            lines.append(f"- [{h['title']}]({h['url']}) - {h['source']}")
        lines.append("")
    rep = os.path.join(ROOT, "trend-report.md")
    open(rep, "w").write("\n".join(lines))
    print(f"wrote {rep}")
    return rep


def fetch(ckey):
    if requests is None:
        print(f"  ! {ckey}: requests not installed")
        return []
    q = quote(QUERIES[ckey] + f" when:{WINDOW_DAYS}d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code != 200:
            print(f"  ! {ckey}: HTTP {r.status_code} from Google News (possible rate limit)")
            return []
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"  ! {ckey}: feed error {e}")
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

    for ckey in ORDER:
        items = fetch(ckey)
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

    total = sum(len(c["headlines"]) for c in data["collections"].values())
    if total == 0:
        # Zero headlines across all four teams cannot be real news silence; it
        # means every feed failed. Keep the existing data and fail the run so
        # the workflow turns red instead of publishing an emptied site.
        print("ERROR: all feeds failed - keeping existing data/trends.json untouched")
        sys.exit(1)

    enrich(data)

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    out = os.path.join(ROOT, "data", "trends.json")
    json.dump(data, open(out, "w"), indent=1)
    print(f"wrote {out}")
    write_report(data)


def enrich_existing():
    """Reshape data/trends.json without hitting Google News (used in the sandbox)."""
    path = os.path.join(ROOT, "data", "trends.json")
    data = json.load(open(path))
    enrich(data)
    json.dump(data, open(path, "w"), indent=1)
    print(f"enriched {path} "
          f"({len((data.get('fan_trend_index') or {}).get('rows') or [])} FTI rows, "
          f"{len(data.get('moments') or [])} player moments)")
    write_report(data)
    return data


if __name__ == "__main__":
    if "--enrich-only" in sys.argv:
        enrich_existing()
    else:
        main()
