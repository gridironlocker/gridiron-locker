import requests, json, re, os
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
h={'User-Agent':'Mozilla/5.0'}
cols=json.load(open('data/collections.json'))
S=requests.Session(); S.headers.update(h)

def get(slug):
    u=f'https://viralstyle.com/kebystore/{slug}?_escaped_fragment_='
    for _ in range(3):
        try:
            t=S.get(u,timeout=45).text
            if len(t)>20000: return t
        except Exception: pass
    return None

def thumb_row(soup):
    """Thumbnail mockups from the campaign's product-design-thumbnail row, in
    DISPLAYED order (never sorted) and de-duplicated keeping first occurrence.

    Verified on the live campaign pages: this row holds one mockup per style,
    in the same order as the SELECT STYLE list, so index N of this list is the
    real garment mockup for style N.
    """
    out, seen = [], set()
    for i in soup.find_all('img'):
        u = i.get('src') or ''
        if 'assets.viralstyle.com' not in u or '-front-small.jpg' not in u:
            continue
        alt = (i.get('alt') or '').strip().lower()
        cls = ' '.join(i.get('class') or []).lower()
        parent_cls = ' '.join((i.parent.get('class') or []) if i.parent is not None else []).lower()
        if not ('product design thumbnail' in alt
                or 'product-design-thumbnail' in cls
                or 'product-design-thumbnail' in parent_cls):
            continue
        if u in seen:
            continue
        seen.add(u); out.append(u)
    return out


def base_style_index(html_text, styles):
    """Index in `styles` of the style shown by the main -front-large mockup.

    Viralstyle labels it in the alt text, e.g.
    alt="THREADFAST Premium Unisex Tee, front view, White color".
    Returns None when it cannot be resolved (callers then distrust the row).
    """
    alts = re.findall(r'alt="([^"]*?),\s*(?:front|back) view[^"]*"', html_text, re.I)
    for alt in alts:
        low = alt.lower()
        best = None
        for n, s in enumerate(styles):
            sl = str(s).strip().lower()
            if sl and sl in low and (best is None or len(sl) > len(styles[best].strip())):
                best = n
        if best is not None:
            return best
    return None


def parse(slug):
    t=get(slug)
    if not t: return {'slug':slug,'error':1}
    s=BeautifulSoup(t,'lxml')
    meta={m.get('property') or m.get('name'):m.get('content') for m in s.find_all('meta')}
    txt=re.sub(r'\s+',' ',s.get_text(' '))
    imgs=[i.get('src') for i in s.find_all('img') if i.get('src') and 'assets.viralstyle.com/campaigns' in i.get('src')]
    front=[i for i in imgs if '-front-large' in i]
    back=[i for i in imgs if '-back-large' in i]
    swatch=sorted(set(i for i in imgs if '-front-small' in i))
    # styles (keep name + Rs price pairs for garment-variant pricing)
    styles=[]
    style_prices={}
    m=re.search(r'SELECT STYLE (.*?) SELECT (?:COLOR|SIZE)',txt)
    if m:
        for part, price in re.findall(r'([A-Za-z0-9\'\-\.\u2019 ]+?) - (?:Rs|\$)([\d,\.]+)',m.group(1)):
            part=part.strip()
            if not part: continue
            styles.append(part)
            try: style_prices[part]=float(price.replace(',',''))
            except Exception: pass
    # One garment mockup per style, in displayed order, guarded for consistency:
    # the row must have exactly one thumb per style AND the base mockup must sit
    # at the same position as the base style, otherwise we refuse the mapping
    # (build.py then falls back to the parent front image + a garment badge,
    # which is always better than showing a wrong mockup).
    style_thumbs = thumb_row(s)
    base_key = None
    if front:
        mm = re.search(r'/([A-Za-z0-9\-]+)-front-large\.jpg', front[0])
        base_key = mm.group(1) if mm else None
    ok = bool(style_thumbs) and len(style_thumbs) == len(styles)
    if ok:
        bi = base_style_index(t, styles)
        ti = next((n for n, u in enumerate(style_thumbs)
                   if base_key and f'/{base_key}-front-small.jpg' in u), None)
        ok = bi is not None and ti is not None and bi == ti
    if not ok:
        style_thumbs = None
    # description block
    d=re.search(r'About Product (.*?)(?: MEASUREMENT NOTES| KEY FEATURES| Recommended Products)',txt)
    desc=d.group(1).strip() if d else ''
    feat=re.search(r'KEY FEATURES: (.*?)(?: MEASUREMENT NOTES| CARE INSTRUCTIONS| Recommended)',txt)
    return {
      'slug':slug,
      'title':(meta.get('og:title') or '').strip(),
      'price_usd':meta.get('product:price:amount'),
      'brand':meta.get('product:brand'),
      'url':f'https://viralstyle.com/kebystore/{slug}',
      'front':front[0] if front else None,
      'back':back[0] if back else None,
      'swatches':swatch[:12],
      'styles':styles,
      'style_prices':style_prices,
      'style_thumbs':style_thumbs,
      'desc':desc[:600],
      'features':(feat.group(1)[:800] if feat else ''),
    }

allp=[]
for k,c in cols.items():
    for p in c['products']: allp.append((k,p['slug']))
print('total',len(allp))
res={}
with ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(lambda x: parse(x[1]), allp):
        res[r['slug']]=r
        print(r['slug'], r.get('price_usd'), len(r.get('swatches',[])), r.get('error',''))
json.dump(res,open('data/products.json','w'),indent=1)
print('errors',sum(1 for r in res.values() if r.get('error')))
