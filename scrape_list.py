import requests, json, re
from bs4 import BeautifulSoup
h={'User-Agent':'Mozilla/5.0'}
cols={
 'cleveland-browns':{'path':'Cleveland-Browns','name':'ORANGE AND BROWN COLLECTION'},
 'dallas-cowboys':{'path':'dallas-vintage-sports','name':'DALLAS VINTAGE SPORTS'},
 'green-bay-packers':{'path':'Packss','name':'PACKS'},
 # Michigan migrated to Mayzing (see data/mayzing_michigan.json) - do NOT
 # re-crawl it from Viralstyle, or the daily refresh would resurrect a
 # Viralstyle Michigan collection in data/collections.json.
}
# A design that now lives on a Mayzing storefront must never land in
# collections.json: tests/test_layout.py pins the file as the retired
# Viralstyle list with zero overlap with the Mayzing catalogue - a
# dual-listed slug is the same design sold on two partner storefronts.
# Same rule as the Michigan exclusion above, applied per slug as designs
# migrate (e.g. limited-edition-no-fly-zone, 2026-10-26).
mayzing={'cleveland-browns':'mayzing_products.json','michigan':'mayzing_michigan.json'}
try: delisted=set(json.load(open('data/delisted.json'))['slugs'])
except Exception: delisted=set()
def migrated(key):
    f=mayzing.get(key)
    if not f: return set()
    try: return {p['slug'] for p in json.load(open('data/'+f))['products']}-delisted
    except Exception as e: print('mayzing filter skipped:',e); return set()
# Keep the previous catalogue around: a fetch failure used to write empty
# product lists over the whole file, while refresh.yml's "keeping existing
# data" fallback never fired because the script still exited 0.
try: existing=json.load(open('data/collections.json'))
except Exception: existing={}
out={}
for key,c in cols.items():
    seen=[]; page=1
    while page<=15:
        u=f"https://viralstyle.com/store/kebystore/{c['path']}/{page}?_escaped_fragment_="
        try: t=requests.get(u,headers=h,timeout=40).text
        except Exception as e: print('err',u,e); break
        s=BeautifulSoup(t,'lxml')
        title=s.title.string if s.title else ''
        links=[]
        for a in s.find_all('a',href=True):
            href=a['href']
            if href.startswith('/kebystore/') and href.count('/')==2:
                slug=href.split('/')[-1]
                img=a.find('img')
                links.append({'slug':slug,'thumb':(img.get('src') if img else None),'title':a.get_text(' ',strip=True)})
        new=[l for l in links if l['slug'] not in {x['slug'] for x in seen}]
        print(key,page,len(links),'new',len(new))
        if not new: break
        seen+=new; page+=1
    if not seen:
        # Fetch failed (or the listing is gone): keep whatever the last good
        # crawl wrote instead of emptying the collection.
        print(key,'crawl produced nothing - keeping existing data')
        if key in existing: out[key]=existing[key]
        continue
    moved=migrated(key)
    dropped=[p['slug'] for p in seen if p['slug'] in moved]
    keep=[p for p in seen if p['slug'] not in moved]
    if dropped: print(key,'dropped, migrated to Mayzing:',', '.join(sorted(dropped)))
    out[key]={'meta':c,'store_title':title,'products':keep}
    print(key,'TOTAL',len(keep))
json.dump(out,open('data/collections.json','w'),indent=1)
