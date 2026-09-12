import os
import requests, json, re
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.abspath(__file__))
h={'User-Agent':'Mozilla/5.0'}
cols={
 'cleveland-browns':{'path':'Cleveland-Browns','name':'ORANGE AND BROWN COLLECTION'},
 'dallas-cowboys':{'path':'dallas-vintage-sports','name':'DALLAS VINTAGE SPORTS'},
 'green-bay-packers':{'path':'Packss','name':'PACKS'},
 'michigan':{'path':'MICHIG','name':'MICHIGAN'},
}
PLACEHOLDER_THUMB = ('data:image/gif;base64,'
                     'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')


def mayzing_collection(c):
    """Return the migrated Browns catalogue in the legacy list shape.

    Cleveland no longer comes from Viralstyle.  Keeping this exception in the
    crawler is important: the refresh job runs scrape_list.py before
    replay_updates.py, so a normal crawl must not replace the 19 live Mayzing
    products with the old 67-item Viralstyle collection.
    """
    with open(os.path.join(ROOT, 'data', 'mayzing_products.json'), encoding='utf-8') as fh:
        source = json.load(fh)
    return {
        'meta': c,
        'store_title': f"Collection - {c['name']} - Mayzing",
        'products': [
            {'slug': product['slug'], 'thumb': PLACEHOLDER_THUMB,
             'title': product['name']}
            for product in source.get('products', [])
        ],
    }


out={}
for key,c in cols.items():
    if key == 'cleveland-browns':
        out[key] = mayzing_collection(c)
        print(key, 'TOTAL', len(out[key]['products']), '(Mayzing source)')
        continue
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
    out[key]={'meta':c,'store_title':title,'products':seen}
    print(key,'TOTAL',len(seen))
json.dump(out,open('data/collections.json','w'),indent=1)
