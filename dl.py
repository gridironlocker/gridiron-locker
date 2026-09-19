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

def to_webp(fn):
    """Convert a transient .jpg to .webp (q82, method 6), then remove the jpg.

    Returns the .webp path on success, None on failure (jpg removed either way).
    """
    webp = fn[:-4] + '.webp' if fn.endswith('.jpg') else fn + '.webp'
    try:
        from PIL import Image
        Image.open(fn).convert('RGB').save(webp, 'WEBP', quality=82, method=6)
        os.remove(fn)
        return webp
    except Exception:
        try:
            if os.path.exists(fn):
                os.remove(fn)
        except Exception:
            pass
        return None

jobs=[]
for slug,v in P.items():
    urls=[('front',v['front']),('back',v.get('back'))]
    sw=[u for u in v.get('swatches',[]) if u][:6]
    for i,u in enumerate(sw): urls.append((f'c{i}',u))
    local={}
    for tag,u in urls:
        if not u: continue
        jpg=f'site/img/p/{slug}-{tag}.jpg'
        webp=jpg[:-4]+'.webp'
        local[tag]=webp.replace('site/','/')
        # c* swatches: prefer the large mockup; fall back to the small one and
        # then to the bare -front variant so a renamed asset still downloads.
        if tag.startswith('c'):
            jobs.append((hi(u),jpg,[u,hi(u).replace('-front-large.jpg','-front.jpg')]))
        else:
            jobs.append((u,jpg,None))
    v['img']=local

def go(j):
    u,fn,fallbacks=j
    webp=fn[:-4]+'.webp' if fn.endswith('.jpg') else fn+'.webp'
    # front/back: skip download if the .webp already exists and is healthy.
    # c* swatches: always re-pull so the large version replaces the old one.
    is_c = any(fn.endswith(f'-c{i}.jpg') for i in range(10))
    if not is_c:
        if os.path.exists(webp) and os.path.getsize(webp)>1000:
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
        open(fn,'wb').write(data)
        return 1 if to_webp(fn) else 0
    return 0

with ThreadPoolExecutor(max_workers=16) as ex:
    ok=sum(ex.map(go,jobs))

# A download that never succeeded must not stay advertised in the live data:
# build.py renders whatever img map it is given, so prune tags whose file is
# missing and say so in the log. Re-running after the assets come back online
# restores them automatically (c* swatches are always re-pulled above).
# Legacy .jpg files on disk are converted to .webp first so an old cache
# still heals the map instead of being pruned.
missed=[]
for k,v in P.items():
    for tag,rel in list((v.get('img') or {}).items()):
        path=os.path.join('site',rel.lstrip('/'))
        # If the advertised .webp is missing, try converting a legacy .jpg twin.
        if path.endswith('.webp') and not (os.path.exists(path) and os.path.getsize(path)>1000):
            legacy=path[:-5]+'.jpg'
            if os.path.exists(legacy) and os.path.getsize(legacy)>1000:
                if to_webp(legacy) and os.path.exists(path) and os.path.getsize(path)>1000:
                    continue
            (v.get('img') or {}).pop(tag,None)
            missed.append(f'{k}/{tag}')
        elif not (os.path.exists(path) and os.path.getsize(path)>1000):
            (v.get('img') or {}).pop(tag,None)
            missed.append(f'{k}/{tag}')
print('downloaded',ok,'/',len(jobs),'products',len(P),'dead',dead)
if missed:
    print('pruned missing img entries:',len(missed))
    for m in missed[:24]: print('  -',m)
# Only one format ever ships: delete any stray .jpg twins of .webp files.
try:
    d='site/img/p'
    for fn in os.listdir(d):
        if fn.endswith('.jpg'):
            twin=os.path.join(d,fn[:-4]+'.webp')
            if os.path.exists(twin):
                try: os.remove(os.path.join(d,fn))
                except Exception: pass
except Exception:
    pass
json.dump(P,open('data/products_live.json','w'),indent=1)
