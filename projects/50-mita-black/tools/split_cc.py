"""Нарезка ключованного листа по связным областям (руки/волосы могут заходить за трети). python3 split_cc.py лист_key.png имя1,имя2,имя3 [outdir]"""
import sys
from PIL import Image
import numpy as np, cv2
src, names = sys.argv[1], sys.argv[2].split(',')
out = sys.argv[3] if len(sys.argv) > 3 else '..'
a = np.array(Image.open(src))
m = (a[..., 3] > 30).astype(np.uint8)
n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((25, 25), np.uint8)))
comps = sorted([i for i in range(1, n) if st[i, 4] > 20000], key=lambda i: st[i, 0])
assert len(comps) == len(names), [tuple(st[i]) for i in comps]
for name, i in zip(names, comps):
    b = a.copy(); b[..., 3] = np.where((lab == i) & (m > 0), a[..., 3], 0)
    p = Image.fromarray(b); p = p.crop(p.getbbox()); p.save(f'{out}/{name}.png'); print(name, p.size)
