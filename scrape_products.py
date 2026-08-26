"""Pull full product data for every design in data/collections.json.

Writes data/products.json. Uses src/viralstyle.py for the connection.

SAFETY: a product that fails to crawl keeps its previously committed record
rather than being written as an error stub. dl.py drops records with no front
image, so an error stub would silently delete a live product page.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from viralstyle import get_product, make_session  # noqa: E402

WORKERS = int(os.environ.get("VS_WORKERS", "6"))
OUT = 'data/products.json'

cols = json.load(open('data/collections.json'))
prev = {}
if os.path.exists(OUT):
    try:
        prev = json.load(open(OUT))
    except Exception:
        prev = {}

session = make_session(pool=WORKERS * 2)


def parse(slug):
    t = get_product(slug, session=session)
    if not t:
        return {'slug': slug, 'error': 1}
    s = BeautifulSoup(t, 'lxml')
    meta = {m.get('property') or m.get('name'): m.get('content') for m in s.find_all('meta')}
    txt = re.sub(r'\s+', ' ', s.get_text(' '))
    imgs = [i.get('src') for i in s.find_all('img')
            if i.get('src') and 'assets.viralstyle.com/campaigns' in i.get('src')]
    front = [i for i in imgs if '-front-large' in i]
    back = [i for i in imgs if '-back-large' in i]
    swatch = sorted(set(i for i in imgs if '-front-small' in i))

    styles = []
    m = re.search(r'SELECT STYLE (.*?) SELECT COLOR', txt)
    if m:
        for part in re.findall(r"([A-Za-z0-9\'\-\. ]+?) - (?:Rs|\$)[\d,\.]+", m.group(1)):
            styles.append(part.strip())

    d = re.search(r'About Product (.*?)(?: MEASUREMENT NOTES| KEY FEATURES| Recommended Products)', txt)
    desc = d.group(1).strip() if d else ''
    feat = re.search(r'KEY FEATURES: (.*?)(?: MEASUREMENT NOTES| CARE INSTRUCTIONS| Recommended)', txt)

    rec = {
        'slug': slug,
        'title': (meta.get('og:title') or '').strip(),
        'price_usd': meta.get('product:price:amount'),
        'brand': meta.get('product:brand'),
        'url': f'https://viralstyle.com/kebystore/{slug}',
        'front': front[0] if front else None,
        'back': back[0] if back else None,
        'swatches': swatch[:12],
        'styles': styles,
        'desc': desc[:600],
        'features': (feat.group(1)[:800] if feat else ''),
    }
    # A page that renders but exposes no imagery/price is not usable either.
    if not rec['front'] or not rec['price_usd']:
        rec['error'] = 1
    return rec


allp = []
for k, c in cols.items():
    for p in c['products']:
        allp.append((k, p['slug']))
print('total', len(allp), f'(workers={WORKERS})')

res, recovered, dead = {}, 0, []
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for r in ex.map(lambda x: parse(x[1]), allp):
        slug = r['slug']
        if r.get('error'):
            old = prev.get(slug)
            if old and old.get('front'):
                res[slug] = old          # keep the last good record
                recovered += 1
                print(f"{slug} FAILED - kept previous record")
            else:
                res[slug] = r            # genuinely dead campaign
                dead.append(slug)
                print(f"{slug} FAILED - no previous data (dead campaign?)")
        else:
            res[slug] = r
            print(slug, r.get('price_usd'), len(r.get('swatches', [])))

json.dump(res, open(OUT, 'w'), indent=1)
ok = sum(1 for r in res.values() if not r.get('error'))
print(f"\nwrote {OUT}: {ok} live, {recovered} kept from previous, {len(dead)} dead")
if dead:
    print('dead:', ', '.join(dead))
