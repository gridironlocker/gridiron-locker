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
        # c* swatches: prefer the large mockup; fall back to the small one and
        # then to the bare -front variant so a renamed asset still downloads.
        if tag.startswith('c'):
            jobs.append((hi(u),fn,[u,hi(u).replace('-front-large.jpg','-front.jpg')]))
        else:
            jobs.append((u,fn,None))
    v['img']=local

def go(j):
    u,fn,fallbacks=j
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
    if data is None:
        for alt in fallbacks or []:
            data=dl(alt)
            if data is not None:
                break
    if data:
        open(fn,'wb').write(data); return 1
    return 0

with ThreadPoolExecutor(max_workers=16) as ex:
    ok=sum(ex.map(go,jobs))

# A download that never succeeded must not stay advertised in the live data:
# build.py renders whatever img map it is given, so prune tags whose file is
# missing and say so in the log. Re-running after the assets come back online
# restores them automatically (c* swatches are always re-pulled above).
missed=[]
for k,v in P.items():
    for tag,rel in list((v.get('img') or {}).items()):
        path=os.path.join('site',rel.lstrip('/'))
        if not (os.path.exists(path) and os.path.getsize(path)>1000):
            (v.get('img') or {}).pop(tag,None)
            missed.append(f'{k}/{tag}')
print('downloaded',ok,'/',len(jobs),'products',len(P),'dead',dead)
if missed:
    print('pruned missing img entries:',len(missed))
    for m in missed[:24]: print('  -',m)
json.dump(P,open('data/products_live.json','w'),indent=1)
