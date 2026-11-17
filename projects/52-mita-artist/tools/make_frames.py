"""Листы ChatGPT (sheets/*_key.png, 1536×1024, по 3 позы) → кадры с ОБЩЕЙ привязкой: холст 768×1024, центр = центр трети листа.
Позы одного движения ChatGPT рисует в одинаковом масштабе и на одной линии пола, поэтому кадры совпадают без подгонки.
Куски (карточка в воздухе, ручка) относятся к трети по центру масс. Зелёный отсвет убирается. → input/mita/frames/<имя>.png"""
import json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

M = Path(__file__).resolve().parents[1] / 'input' / 'mita'
SHEETS = {
    'poke_k': 'poke_1 poke_5 poke_9', 'poke_i1': 'poke_2 poke_3 poke_4', 'poke_i2': 'poke_6 poke_7 poke_8', 'poke_i3': 'poke_2a poke_2b poke_2c',
}
THIRDS = set()            # бюсты касаются друг друга — режем строго по третям
CW = 768


def despill(a):
    """52: в наряде мятный и бирюзовый — зелёный отсвет чистим ТОЛЬКО по краю фигуры (полупрозрачная кайма
    и полоса 3 px внутрь), иначе мятное платье становится серо-голубым."""
    a = a.astype(np.int16)
    al = a[..., 3]
    solid = (al > 250).astype(np.uint8)
    edge = (al <= 250) | (cv2.erode(solid, np.ones((7, 7), np.uint8)) == 0)
    g = np.minimum(a[..., 1], np.maximum(a[..., 0], a[..., 2]) + 4)
    a[..., 1] = np.where(edge, g, a[..., 1])
    return a.clip(0, 255).astype(np.uint8)


meta = {}
for sh, names in SHEETS.items():
    a = np.array(Image.open(M / 'sheets' / f'{sh}_key.png').convert('RGBA'))
    a = despill(a)
    H, W = a.shape[:2]
    m = (a[..., 3] > 8).astype(np.uint8)
    third = np.zeros((H, W), np.int8) - 1
    if sh in THIRDS:
        for k in range(3):
            third[:, k * W // 3:(k + 1) * W // 3] = k
    else:
        n, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((9, 9), np.uint8)))
        for i in range(1, n):
            if st[i, 4] < 60:
                continue
            third[lab == i] = min(2, int(cen[i][0] // (W / 3)))
    for k, name in enumerate(names.split()):
        cx = int((k + 0.5) * W / 3)
        c = np.zeros((H, CW, 4), np.uint8)
        x0 = cx - CW // 2
        sx0, sx1 = max(0, x0), min(W, x0 + CW)
        sel = (third[:, sx0:sx1] == k) & (m[:, sx0:sx1] > 0)
        part = a[:, sx0:sx1].copy()
        part[..., 3] = np.where(sel, part[..., 3], 0)
        c[:, sx0 - x0:sx1 - x0] = part
        Image.fromarray(c).save(M / 'frames' / f'{name}.png')
        ys, xs = np.nonzero(c[..., 3] > 40)
        mg = (c[..., 0] > 180) & (c[..., 2] > 180) & (c[..., 1] < 110) & (c[..., 3] > 0)
        meta[name] = dict(sheet=sh, top=int(ys.min()), bottom=int(ys.max()), left=int(xs.min()), right=int(xs.max()), magenta=int(mg.sum()))
(M / 'frames' / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
print(len(meta), 'кадров')
for k, v in meta.items():
    print(k, v)
