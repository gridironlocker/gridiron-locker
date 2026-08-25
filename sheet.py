import json,os
from PIL import Image, ImageDraw, ImageFont
P=json.load(open('data/products_live.json'))
C=json.load(open('data/collections.json'))
order=[]
for k,c in C.items():
    for p in c['products']:
        if p['slug'] in P: order.append((k,p['slug']))
os.makedirs('sheets',exist_ok=True)
try: F=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",22)
except: F=ImageFont.load_default()
CELL=460; LAB=34; COLS=4; ROWS=3; PER=COLS*ROWS
sheets=[]
for si in range(0,len(order),PER):
    chunk=order[si:si+PER]
    W=COLS*CELL; H=ROWS*(CELL+LAB)
    canvas=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(canvas)
    for i,(col,slug) in enumerate(chunk):
        r,c=divmod(i,COLS)
        x,y=c*CELL, r*(CELL+LAB)
        fp='site'+P[slug]['img']['front']
        try:
            im=Image.open(fp).convert('RGB'); im.thumbnail((CELL-8,CELL-8))
            canvas.paste(im,(x+4,y+LAB+4))
        except Exception as e: pass
        d.rectangle([x,y,x+CELL,y+LAB],fill='black')
        d.text((x+6,y+6), f"[{si+i}] {slug[:38]}", fill='yellow', font=F)
        d.rectangle([x,y,x+CELL-1,y+LAB+CELL-1],outline='red',width=2)
    fn=f'sheets/sheet{si//PER:02d}.jpg'; canvas.save(fn,quality=82); sheets.append(fn)
json.dump([{'i':i,'col':c,'slug':s} for i,(c,s) in enumerate(order)],open('data/order.json','w'),indent=1)
print(len(order),'products',len(sheets),'sheets')
