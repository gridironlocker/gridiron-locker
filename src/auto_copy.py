#!/usr/bin/env python3
"""Auto-generated copy for crawled designs that have no hand-written entry.

When a fresh Viralstyle crawl surfaces a slug that has no entry in
`src/catalog.py` (and no existing record in `data/facts.json`), `build.py`
calls :func:`derive` to fabricate safe, human-ish copy so a re-crawl can never
resurrect a page with no name, art, keywords or theme - or crash the build.

Derivation rules:

- `name` and `art` come from the campaign's own store title (the text the
  storefront already crawled). No player face, no invented copy.
- `kw` is built from that title plus live trend topics taken from
  `data/trends.json` headlines, with every player and coach name stripped out
  so auto-generated keywords never promote a departed name.
- `theme` defaults to ``"classic"``; it is only upgraded to ``"player"`` when a
  tracked name actually appears in the store title.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Common words to drop from auto-generated keywords (mirrors src/trends.py).
STOP = set("""
with from that this what will have they team game games season week news says
said after before their there could would about into more than when first over
back down being under while play plays player players report reports preseason
camp nfl browns packers michigan dallas cowboys wolverines store design
""".split())


def _load_json(path):
    try:
        with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def people_names():
    """Every tracked player / coach name plus each word of those names, lowercased.

    Sources: ``data/people.json`` (current + former) and the canonical entity
    names scored in ``data/trends.json``. These tokens are stripped from any
    auto-generated keyword so a departed name can never be re-promoted.
    """
    names = set()
    people = (_load_json("data/people.json") or {}).get("people") or []
    for p in people:
        n = (p.get("name") or "").strip().lower()
        if not n:
            continue
        names.add(n)
        for w in re.split(r"\s+", n):
            if len(w) > 1:
                names.add(w)
    trends = _load_json("data/trends.json") or {}
    for c in (trends.get("collections") or {}).values():
        for e in (c.get("entity_mentions") or {}):
            e = (e or "").strip().lower()
            if e:
                names.add(e)
                for w in re.split(r"\s+", e):
                    if len(w) > 1:
                        names.add(w)
    return names


def _tokens(text):
    return re.findall(r"[a-z]{4,}", (text or "").lower())


def trend_topics(ckey, limit=6):
    """Trend topics for a collection, taken from live ``trends.json`` headlines."""
    trends = _load_json("data/trends.json") or {}
    col = (trends.get("collections") or {}).get(ckey) or {}
    blob = " ".join((h.get("title") or "") for h in col.get("headlines") or [])
    freq = {}
    for w in _tokens(blob):
        if w in STOP:
            continue
        freq[w] = freq.get(w, 0) + 1
    topics = [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:limit]]
    if topics:
        return topics
    # Headlines empty? Fall back to the crawl's pre-computed top terms.
    return [t for t in (col.get("top_terms") or []) if t][:limit]


def _titlecase(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    if not s:
        return ""
    out = []
    for w in s.split():
        if w.lower() in ("qb", "qb1", "nfl", "est", "usa", "wi", "oh", "tx", "vs"):
            out.append(w.upper())
        elif len(w) > 1:
            out.append(w[0].upper() + w[1:])
        else:
            out.append(w.upper())
    return " ".join(out)


def derive(slug, product, ckey):
    """Return a ``{name, art, kw, theme}`` facts dict for a crawled design."""
    title = (product.get("title") or "").strip()
    if not title:
        title = re.sub(r"[-_]+", " ", slug).strip()
    title = re.sub(r"\s+", " ", title).strip()
    name = _titlecase(title) or _titlecase(slug)
    art = title.upper() or name.upper()

    names = people_names()
    kw = []
    seen = set()
    for w in _tokens(title + " " + " ".join(trend_topics(ckey))):
        if w in names or w in STOP:
            continue
        if w not in seen:
            seen.add(w)
            kw.append(w)
    if not kw:
        kw = ["fan apparel", "football gear"]

    theme = "classic"
    blob = title.lower()
    for n in sorted(names, key=len, reverse=True):
        if len(n) > 2 and n in blob:
            theme = "player"
            break

    return {"name": name, "art": art, "kw": kw, "theme": theme}
