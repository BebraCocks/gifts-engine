"""Нарезка листов ChatGPT (зелёный/синий фон) на отдельные RGBA → build/assets/<имя>.png.
Ключ по «доминирующему каналу» фона: g−max(r,b) для зелёного, b−max(r,g) для синего."""
import json
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / 'build' / 'assets'


def bg_of(f):
    c = np.concatenate([f[:16, :16].reshape(-1, 3), f[:16, -16:].reshape(-1, 3), f[-16:, :16].reshape(-1, 3),
                        f[-16:, -16:].reshape(-1, 3)])
    return np.median(c, 0).astype(np.float32)


def key(f, soft=0.75, despill=True):
    bg = bg_of(f)
    ch = int(np.argmax(bg))
    oth = [i for i in range(3) if i != ch]
    x = f.astype(np.float32)
    sc = x[..., ch] - np.maximum(x[..., oth[0]], x[..., oth[1]])
    s0 = float(bg[ch] - max(bg[oth[0]], bg[oth[1]]))
    a = np.clip((s0 * 0.9 - sc) / (s0 * soft), 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.6)
    a[a < 0.04] = 0
    aa = np.maximum(a, 1e-3)[..., None]
    fg = (x - (1 - a[..., None]) * bg) / aa
    fg = np.where(a[..., None] > 0.02, fg, 0)
    if despill:
        lim = np.maximum(fg[..., oth[0]], fg[..., oth[1]]) * 1.04 + 4
        fg[..., ch] = np.where(a < 0.98, np.minimum(fg[..., ch], lim), fg[..., ch])
    return np.dstack([fg.clip(0, 255), a * 255]).astype(np.uint8)


def _cuts(proj, n):
    """Границы n частей: минимум проекции около равных долей (±22 %)."""
    L = len(proj)
    sm = np.convolve(proj, np.ones(9) / 9, 'same')
    cuts = [0]
    for k in range(1, n):
        c = L * k / n
        lo, hi = int(c - 0.22 * L / n), int(c + 0.22 * L / n)
        cuts.append(lo + int(np.argmin(sm[lo:hi])))
    return cuts + [L]


def save_crop(k, nm):
    a = k[..., 3]
    m = a > 50
    if not m.any():
        print('!! пусто', nm)
        return
    ys, xs = np.nonzero(m)
    sub = k[max(0, ys.min() - 6):ys.max() + 7, max(0, xs.min() - 6):xs.max() + 7].copy()
    sub[..., 3][sub[..., 3] < 12] = 0
    Image.fromarray(sub).save(OUT / f'{nm}.png')
    print(nm, sub.shape[1], sub.shape[0])


def split(name, src, names, rows=1, cols=3):
    f = np.array(Image.open(HERE / src).convert('RGB'))
    k = key(f)
    m = (k[..., 3] > 60).astype(np.float32)
    rc = _cuts(m.sum(1), rows)
    i = 0
    for r in range(rows):
        band = m[rc[r]:rc[r + 1]]
        nc = cols[r] if isinstance(cols, (list, tuple)) else cols
        cc = _cuts(band.sum(0), nc)
        for c in range(nc):
            if i < len(names) and names[i]:
                save_crop(k[rc[r]:rc[r + 1], cc[c]:cc[c + 1]], names[i])
            i += 1


SHEETS = [
    ('weapons', 'input/weapons/weapons_sheet.png', ['knife', 'akr', 'deagle'], 3, 1),
    ('charms', 'input/props/charms.png', ['charm_fox', 'charm_heart', 'charm_cactus'], 1, 3),
    ('gifts', 'input/props/gifts_new.png', ['gift_fox', 'gift_heart', 'gift_cactus'], 1, 3),
    ('merch', 'input/props/merch_sheet.png', ['merch_plush', 'merch_hoodie', 'merch_figure'], 1, 3),
    ('skins', 'input/props/skins_sheet.png', ['skin_akr', 'graffiti_heart_old', 'agent_old'], 2, [1, 2]),
    ('graf', 'input/props/graffiti_sticker.png', ['graffiti', 'sticker'], 1, 2),
    ('gold', 'input/props/gold_case.png', ['gold', 'case'], 1, 2),
    ('rewards', 'input/props/rewards_sheet.png', ['trophy_old', 'cases', 'gold_pile', 'promo_card'], 2, 2),
    ('qr', 'input/props/qr_tags.png', ['tag_cactus', 'tag_hoodie', 'tag_fox'], 1, 3),
    ('emotes', 'input/decor/emotes.png', [f'emo{i}' for i in range(9)], 3, 3),
    ('objects', 'input/decor/objects.png', [f'obj{i}' for i in range(9)], 3, 3),
    ('thumbs', 'input/props/thumbs.png', [f'thumb{i}' for i in range(6)], 2, 3),
]
SINGLE = [('trophy', 'input/props/trophy.png'), ('agent', 'input/props/agent.png'),
          ('award', 'input/props/creator_award.png')]

if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    for name, src, names, r, c in SHEETS:
        if not only or name in only:
            split(name, src, names, r, c)
    for nm, src in SINGLE:
        if not only or nm in only:
            save_crop(key(np.array(Image.open(HERE / src).convert('RGB'))), nm)
    if not only or 'skins' in only:                  # в полосе автомата — голова агента: оставляем крупнейший кусок
        k = np.array(Image.open(OUT / 'skin_akr.png'))
        m = cv2.dilate((k[..., 3] > 40).astype(np.uint8), np.ones((15, 15), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        k[..., 3] = k[..., 3] * (lab == 1 + np.argmax(st[1:, 4]))
        im = Image.fromarray(k)
        im.crop(im.getbbox()).save(OUT / 'skin_akr.png')
