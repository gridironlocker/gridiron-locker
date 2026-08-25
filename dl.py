import json,os,requests
from concurrent.futures import ThreadPoolExecutor
P=json.load(open('data/products.json'))
dead=[k for k,v in P.items() if not v.get('front')]
for k in dead: P.pop(k)
os.makedirs('site/img/p',exist_ok=True)
S=requests.Session(); S.headers.update({'User-Agent':'Mozilla/5.0'})

def hi(u):
    """Swap Viralstyle small/detail variants for the large mockup if available."""
    return (u.replace('-front-small.jpg','-front-large.jpg')
             .replace('-back-small.jpg','-back-large.jpg')
             .replace('-detail.jpg','-large.jpg')
             .replace('-small.jpg','-large.jpg'))

jobs=[]
for slug,v in P.items():
    urls=[('front',v['front']),('back',v.get('back'))]
    sw=[u for u in v.get('swatches',[]) if u][:6]
    for i,u in enumerate(sw): urls.append((f'c{i}',u))
    local={}
    for tag,u in urls:
        if not u: continue
        fn=f'site/img/p/{slug}-{tag}.jpg'
        local[tag]=fn.replace('site/','/')
        # c* swatches: prefer the large mockup; fall back to the small one.
        if tag.startswith('c'):
            jobs.append((hi(u),fn,u))
        else:
            jobs.append((u,fn,None))
    v['img']=local

def go(j):
    u,fn,fallback=j
    # always re-pull c* swatches so the large version replaces the old small one
    if not fn.endswith('c.jpg') and not any(fn.endswith(f'-c{i}.jpg') for i in range(10)):
        if os.path.exists(fn) and os.path.getsize(fn)>1000:
            return 1
    def dl(url):
        try:
            r=S.get(url,timeout=90)
            if r.status_code==200 and len(r.content)>3000:
                return r.content
        except Exception:
            pass
        return None
    data=dl(u)
    if data is None and fallback:
        data=dl(fallback)
    if data:
        open(fn,'wb').write(data); return 1
    return 0

with ThreadPoolExecutor(max_workers=16) as ex:
    ok=sum(ex.map(go,jobs))
print('downloaded',ok,'/',len(jobs),'products',len(P),'dead',dead)
json.dump(P,open('data/products_live.json','w'),indent=1)
