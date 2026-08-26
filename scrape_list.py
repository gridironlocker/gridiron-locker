"""Re-crawl the 4 Viralstyle collections for new / removed designs.

Writes data/collections.json. Uses src/viralstyle.py for the connection so a
blocked request retries and reports instead of silently producing an empty
collection.

SAFETY: if a collection comes back empty or badly shrunken, the existing
committed data for that collection is kept. A failed crawl must never be able
to wipe the catalogue and delete 134 product pages on the next build.
"""
import json
import os
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from viralstyle import get_store_page, make_session  # noqa: E402

MAX_PAGES = 15
# If a re-crawl returns fewer than this fraction of the known products, treat it
# as a partial/blocked crawl and keep what we already have.
SHRINK_GUARD = 0.6

cols = {
    'cleveland-browns': {'path': 'Cleveland-Browns', 'name': 'ORANGE AND BROWN COLLECTION'},
    'dallas-cowboys':   {'path': 'dallas-vintage-sports', 'name': 'DALLAS VINTAGE SPORTS'},
    'green-bay-packers': {'path': 'Packss', 'name': 'PACKS'},
    'michigan':         {'path': 'MICHIG', 'name': 'MICHIGAN'},
}

OUT = 'data/collections.json'
prev = {}
if os.path.exists(OUT):
    try:
        prev = json.load(open(OUT))
    except Exception:
        prev = {}

session = make_session()
out = {}
failed = []

for key, c in cols.items():
    seen, title, page = [], '', 1
    while page <= MAX_PAGES:
        t = get_store_page(c['path'], page, session=session)
        if not t:
            print(f"{key} page {page}: no usable HTML - stopping this collection")
            break
        s = BeautifulSoup(t, 'lxml')
        if s.title and s.title.string:
            title = s.title.string
        links = []
        for a in s.find_all('a', href=True):
            href = a['href']
            if href.startswith('/kebystore/') and href.count('/') == 2:
                slug = href.split('/')[-1]
                img = a.find('img')
                links.append({'slug': slug,
                              'thumb': (img.get('src') if img else None),
                              'title': a.get_text(' ', strip=True)})
        known = {x['slug'] for x in seen}
        new = [l for l in links if l['slug'] not in known]
        print(key, page, len(links), 'new', len(new))
        if not new:
            break
        seen += new
        page += 1

    old = prev.get(key, {}).get('products', [])
    if not seen:
        print(f"  !! {key}: crawl produced nothing - keeping {len(old)} existing products")
        failed.append(key)
        out[key] = prev.get(key, {'meta': c, 'store_title': '', 'products': []})
        continue
    if old and len(seen) < len(old) * SHRINK_GUARD:
        print(f"  !! {key}: only {len(seen)} of {len(old)} products returned "
              f"(<{int(SHRINK_GUARD*100)}%) - looks like a partial crawl, keeping existing")
        failed.append(key)
        out[key] = prev[key]
        continue

    out[key] = {'meta': c, 'store_title': title, 'products': seen}
    delta = len(seen) - len(old)
    print(f"{key} TOTAL {len(seen)} ({delta:+d} vs committed)")

json.dump(out, open(OUT, 'w'), indent=1)
total = sum(len(v['products']) for v in out.values())
print(f"wrote {OUT}: {total} products across {len(out)} collections")
if failed:
    print(f"WARNING: kept existing data for: {', '.join(failed)}")
