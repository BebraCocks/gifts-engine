"""Хромакей листа с фоном #00FF00 → RGBA с подавлением зелёной каймы. python3 chroma_key.py лист.jpg тег → тег_key.png"""
from PIL import Image
import numpy as np
def box(m,r):
    c=np.pad(m.astype(float),((r+1,r),(r+1,r)),mode='edge').cumsum(0).cumsum(1);k=2*r+1
    return (c[k:,k:]-c[:-k,k:]-c[k:,:-k]+c[:-k,:-k])/(k*k)
def grow(cur,allow):
    cur=cur&allow
    while True:
        n=cur.copy();n[1:]|=cur[:-1];n[:-1]|=cur[1:];n[:,1:]|=cur[:,:-1];n[:,:-1]|=cur[:,1:];n&=allow
        if (n==cur).all(): return cur
        cur=n
import sys
for src,o in [(sys.argv[1],sys.argv[2])]:
    a=np.array(Image.open(src).convert('RGB')).astype(float)
    r,g,b=a[...,0],a[...,1],a[...,2]
    d=np.sqrt((r-3)**2+(g-254)**2+(b-3)**2)
    A=np.clip((d-45)/70,0,1)
    # only keep transparency in regions connected to border-bg (avoid holes inside sweater)
    bgcore=d<60
    seed=np.zeros_like(bgcore);seed[0]=seed[-1]=True;seed[:,0]=seed[:,-1]=True
    near=box(grow(seed,bgcore),4)>0
    # enclosed green pockets (between hair and arm) — also bg if large & pure
    A=np.where(near|bgcore,A,1.0)
    tr=A<0.5
    edge=box(tr,4)>0
    sweater=(r>95)&(g>140)&(b<110)&(box(tr,4)<0.5)
    lim=np.maximum(r,b)+8
    g2=np.where(edge&~sweater,np.minimum(g,lim),g)
    # sweater edge: pull spill toward sweater hue only for very green pixels
    g2=np.where(edge&sweater,np.minimum(g2,r*1.9+30),g2)
    A=np.where(box(tr,1)>0.3,A*0.6,A)
    g2=np.where((r<80)|(o!='mix'),np.minimum(g2,np.maximum(r,b)+8),g2)
    out=np.dstack([r,g2,b,A*255]).clip(0,255).astype(np.uint8)
    Image.fromarray(out,'RGBA').save(o+'_key.png')
    print(o,(A>0.5).mean())
