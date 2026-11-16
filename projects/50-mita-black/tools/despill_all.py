"""Убирает зелёный отсвет хромакея: G не выше max(R,B), а где G > R — G = (R+B)/2 (у Миты нет зелёного в одежде). python3 despill_all.py файлы…"""
import sys
from PIL import Image
import numpy as np
for f in sys.argv[1:]:
    a = np.array(Image.open(f).convert('RGBA')).astype(np.int16)
    lim = np.maximum(a[..., 0], a[..., 2])
    a[..., 1] = np.minimum(a[..., 1], lim + 4)
    # отсвет на коже/кружеве: G выше R (у кожи и золота всегда R > G) → G = среднее R и B
    spill = a[..., 1] > a[..., 0]
    a[..., 1] = np.where(spill, (a[..., 0] + a[..., 2]) // 2, a[..., 1])
    Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(f)
    print('ok', f)
