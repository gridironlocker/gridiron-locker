import json,os,sys,requests
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
from viralstyle import make_session
P=json.load(open('data/products.json'))
dead=[k for k,v in P.items() if not v.get('front')]
for k in dead: P.pop(k)
os.makedirs('site/img/p',exist_ok=True)
S=make_session()

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

# SAFETY: products_live.json is what build.py turns into pages. Never let a bad
# crawl shrink it dramatically - that would silently delete live product pages.
LIVE='data/products_live.json'
if os.path.exists(LIVE):
    try: old=json.load(open(LIVE))
    except Exception: old={}
    if old and len(P) < len(old)*0.6:
        print(f'ABORT: refusing to write {len(P)} products over {len(old)} existing '
              f'(<60%). Crawl looks partial - keeping {LIVE} unchanged.')
        raise SystemExit(1)
    # carry forward any product the crawl lost but whose images are still on disk
    for slug,v in old.items():
        if slug not in P and v.get('img'):
            front=v['img'].get('front','')
            if front and os.path.exists('site'+front):
                P[slug]=v
                print('kept previously-built product',slug)
json.dump(P,open(LIVE,'w'),indent=1)
