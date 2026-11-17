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
    'astro_a': 'astro_explain astro_scope astro_star',
    'snap_k1': 'snap_idle snap_click snap_wind', 'snap_i1': 'snap_up1 snap_up2 snap_up3', 'snap_i2': 'snap_dn1 snap_dn2 snap_dn3',
    'snap_i3': 'snap_pre snap_post snap_wind75', 'snap_i4': 'snap_rise1 snap_rise2 snap_peak',
    'snap_k2': 'astro_peak astro_land astro_cape', 'snap_i5': 'astro_fall1 astro_fall2 astro_fall3',
    'snap_i6': 'astro_look1 astro_look2 astro_look3', 'snap_i7': 'astro_rel1 astro_rel2 astro_rel3',
    'snap_i8': 'astro_sc1 astro_sc2 astro_sc3',
    'cast_k': 'cast_1 cast_5 cast_9', 'cast_i1': 'cast_2 cast_3 cast_4', 'cast_i2': 'cast_6 cast_7 cast_8', 'cast_i3': 'cast_h1 cast_h2 cast_h3',
    'fear_k': 'fear_1 fear_4 fear_7', 'fear_i1': 'fear_2 fear_3 fear_35', 'fear_i2': 'fear_5 fear_6 fear_65', 'fear_x1': 'fear_37 fear_55 fear_62', 'fear_x2': 'fear_45 fear_52 fear_53',
    'creep_k': 'creep_1 creep_4 creep_7', 'creep_i1': 'creep_2 creep_5 creep_8',
    'up_k': 'up_1 up_5 up_9', 'up_i1': 'up_2 up_4 up_7', 'up_i2': 'up_3 up_6 up_8',
    'hmm_k': 'hmm_1 hmm_5 hmm_9', 'hmm_i1': 'hmm_3 hmm_7 hmm_10',
    'down_k': 'down_1 down_5 down_9', 'down_i1': 'down_3 down_7 down_loop',
    'two_k': 'two_1 two_5 two_9', 'two_i1': 'two_3 two_7 two_10',
    'jump_k': 'jump_1 jump_5 jump_9', 'jump_i1': 'jump_2 jump_3 jump_4', 'jump_i2': 'jump_6 jump_7 jump_8',
    'sweep_k': 'sweep_1 sweep_5 sweep_9', 'sweep_i1': 'sweep_3 sweep_7 sweep_10',
    'walk_k': 'walk_a walk_b walk_c', 'walk_i1': 'walk_ab walk_bc walk_d', 'walk_i2': 'walk_cd walk_da walk_a2',
    'walk_i3': 'walk_x1 walk_x2 walk_x3', 'walk_i4': 'walk_x4 walk_x5 walk_x6', 'walk_i5': 'walk_x7 walk_x8 walk_x9',
    'walk_i6': 'walk_y1 walk_y2 walk_y3',
}
THIRDS = set()            # бюсты касаются друг друга — режем строго по третям
CW = 768


def despill(a):
    a = a.astype(np.int16)
    a[..., 1] = np.minimum(a[..., 1], np.maximum(a[..., 0], a[..., 2]) + 4)
    sp = a[..., 1] > a[..., 0]
    a[..., 1] = np.where(sp, (a[..., 0] + a[..., 2]) // 2, a[..., 1])
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
