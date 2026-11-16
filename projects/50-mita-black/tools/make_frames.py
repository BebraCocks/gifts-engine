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
    'hook_a': 'hook_peek hook_step hook_wave', 'hook_b': 'hook_in_a hook_in_b hook_in_c',
    'card_a': 'card_1 card_2 card_3', 'card_b': 'card_in_a card_in_b card_in_c',
    'ufc': 'ufc_sit_1 ufc_sit_2 ufc_sit_3',
    'jump_a': 'jump_crouch jump_peak jump_land', 'jump_b': 'jump_takeoff jump_fall jump_recover', 'jump_c': 'jump_notice jump_prep jump_calm',
    'creepy_a': 'creepy_1 creepy_2 creepy_3', 'creepy_b': 'creepy_in_a creepy_in_b creepy_in_c',
    'knob_a': 'knob_1 knob_2 knob_3', 'knob_b': 'knob_in_a knob_in_b knob_watch',
    'adsit_a': 'ad_sit_1 ad_sit_2 ad_sit_3', 'adsit_b': 'ad_sit_in_a ad_sit_in_b ad_sit_thumb',
    'run_a': 'run_1 run_2 run_3', 'run_b': 'run_4 run_5 run_6',
    'phone_a': 'phone_1 phone_2 phone_3', 'phone_b': 'phone_in_a phone_in_b phone_hug',
    'kick_a': 'kick_1 kick_2 kick_3', 'kick_b': 'kick_in_a kick_in_b kick_dust',
    'hang_a': 'hang_1 hang_2 hang_3', 'hang_b': 'hang_in_a hang_in_b hang_grab',
    'two_a': 'two_1 two_2 two_3', 'two_b': 'two_in_a two_in_b two_point',
    'box_a': 'box_guard box_jab box_win',
    'pump_a': 'pump_1 pump_2 pump_3', 'pump_b': 'pump_in_a pump_in_b pump_point',
}
THIRDS = {'creepy_a', 'creepy_b'}            # бюсты касаются друг друга — режем строго по третям
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
