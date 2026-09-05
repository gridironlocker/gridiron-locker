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
    m=re.search(r'SELECT STYLE (.*?) SELECT COLOR',txt)
    if m:
        for part, price in re.findall(r'([A-Za-z0-9\'\-\. ]+?) - (?:Rs|\$)([\d,\.]+)',m.group(1)):
            part=part.strip()
            if not part: continue
            styles.append(part)
            try: style_prices[part]=float(price.replace(',',''))
            except Exception: pass
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
