"""v5 (2026-11-21): Мита — клипы Gemini (input/mita/video, 720×1280, 24 fps, зелёный фон) вместо покадровых поз ChatGPT.
Каждая сцена — отрезок клипа; время клипа задаётся опорными точками (время ролика → время клипа), чтобы жесты
ложились на слова. Ключ — по «зелёности» (как key54), масштаб — одна высота Миты во всех клипах, якорь — центр стоп
опорного кадра клипа (Мита стоит на подиуме бутика и не «гуляет» между клипами). Стыки — смешивание 0,3 с,
кружение — жёсткая смена красный → готика на заднем ракурсе под вспышкой."""
import functools
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import fx
import events as E
from timeline import AD_STOP, DUR

HERE = Path(__file__).resolve().parent
VID = HERE / 'input' / 'mita' / 'video'
CFPS = 24
MH = 800                 # видимая высота Миты (макушка — подошвы), px
FOOT = 1552              # подошвы на подиуме бутика
CX = 540
XF = 0.3                 # смешивание соседних клипов, с

# геометрия опорного кадра: высота Миты, центр стоп, подошвы (замер по альфе; hang — высота тела без перекладины)
GEO = {
    'hook': (987, 356.5, 1177), 'spin_red': (991, 356.5, 1177), 'spin_goth': (995, 377.5, 1175),
    'card': (1053, 377.5, 1211), 'pumpkin': (1063, 379.5, 1217), 'locket': (1051, 384.5, 1217),
    'rare': (1047, 379.5, 1203), 'demand': (1043, 380.5, 1203), 'glow': (1045, 381.5, 1203),
    'plain': (1041, 393.5, 1203), 'hang': (997, 344.5, 1177), 'outro': (997, 377.5, 1177),
}
BOX = {'spin_red', 'spin_goth', 'glow'}          # искры/свечение на зелёном: мягче ключ, зелень убираем сильнее

SW = E.SPIN + 0.48                                 # смена наряда: красный клип спиной к камере (0,9 с клипа)
P = E.PRICE
SEGS = [   # (начало, клип, опорные точки (время ролика, время клипа))
    (0.0, 'hook', [(0.0, 0.15), (10.0, 10.15)]),
    (E.SPIN - 0.12, 'spin_red', [(E.SPIN - 0.12, 0.30), (SW, 0.90)]),
    (SW, 'spin_goth', [(SW, 0.05), (SW + 3.0, 3.05)]),
    (8.0, 'card', [(8.0, 1.2), (12.4, 5.6)]),
    (12.35, 'pumpkin', [(12.35, 1.25), (18.8, 7.7)]),
    (18.75, 'locket', [(18.75, 0.0), (24.3, 5.55)]),
    (E.CREEPY - 0.1, 'rare', [(E.CREEPY - 0.1, 0.24), (26.75, 2.85), (27.6, 3.5), (28.9, 4.8), (29.9, 5.3),
                               (31.7, 6.2), (32.6, 7.2), (33.1, 8.2), (AD_STOP + 0.2, 9.85)]),
    (AD_STOP + 0.02, 'demand', [(AD_STOP + 0.02, 0.3), (35.5, 1.0), (36.9, 2.2), (38.8, 3.5), (40.1, 4.9),
                                (41.5, 5.6), (42.6, 6.7)]),
    (E.GLOW - 0.2, 'glow', [(E.GLOW - 0.2, 0.2), (44.0, 1.6), (47.5, 4.3), (48.6, 5.4)]),
    (E.PLAIN - 0.05, 'plain', [(E.PLAIN - 0.05, 0.0), (49.7, 1.6), (50.8, 2.6)]),
    (P - 0.05, 'hang', [(P - 0.05, 0.3), (55.2, 4.85)]),
    (E.OUTRO - 0.05, 'outro', [(E.OUTRO - 0.05, 0.1), (56.0, 1.0), (57.0, 2.6), (57.9, 3.5), (58.6, 5.0), (DUR + 2, 8.6)]),
]
HARD = {'spin_goth'}                               # без смешивания (вспышка)
HANG_LIFT = 230                                    # насколько поднимается Мита вместе с ценой
MIRROR_T0 = E.CREEPY + 0.16                        # отражение в нише начинает поворот


def ease(x):
    return fx.smooth(fx.clamp01(x))


def clip_time(keys, t):
    if t <= keys[0][0]:
        return keys[0][1] + (t - keys[0][0])
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if t <= t1:
            return c0 + (c1 - c0) * (t - t0) / (t1 - t0)
    return keys[-1][1] + (t - keys[-1][0])


# ------------------------------------------------------------------ чтение и ключ
def bg_of(f):
    c = np.concatenate([f[:24, :24].reshape(-1, 3), f[:24, -24:].reshape(-1, 3), f[-24:, :24].reshape(-1, 3),
                        f[-24:, -24:].reshape(-1, 3)])
    return np.median(c, 0).astype(np.float32)


def key(f, soft=0.75, mode='normal'):
    bg = bg_of(f)
    x = f.astype(np.float32)
    gr = x[..., 1] - np.maximum(x[..., 0], x[..., 2])
    g0 = float(bg[1] - max(bg[0], bg[2]))
    a = np.clip((g0 * 0.92 - gr) / (g0 * soft), 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.6)
    a[a < 0.04] = 0
    aa = np.maximum(a, 1e-3)[..., None]
    fg = (x - (1 - a[..., None]) * bg) / aa
    fg = np.where(a[..., None] > 0.02, fg, 0)
    if mode == 'box':
        r_, b_ = fg[..., 0], fg[..., 2]
        fg[..., 1] = np.minimum(fg[..., 1], 0.5 * (r_ + b_) + 0.25 * np.abs(r_ - b_))
    else:
        fg[..., 1] = np.minimum(fg[..., 1], np.maximum(fg[..., 0], fg[..., 2]) * 1.04 + 4)
    return np.dstack([fg.clip(0, 255), a * 255]).astype(np.uint8)


class Reader:
    """Последовательное чтение кадров (воркеры идут по кадрам вперёд — перемотка редкая)."""

    def __init__(self, name):
        self.path = str(VID / f'{name}.mp4')
        self.cap = cv2.VideoCapture(self.path)
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.pos = 0

    def get(self, i):
        i = max(0, min(self.n - 1, i))
        if i < self.pos or i > self.pos + 48:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            self.pos = i
        f = None
        while self.pos <= i:
            ok, f = self.cap.read()
            self.pos += 1
            if not ok:
                break
        return None if f is None else cv2.cvtColor(f, cv2.COLOR_BGR2RGB)


@functools.lru_cache(None)
def reader(name):
    return Reader(name)


@functools.lru_cache(maxsize=48)
def raw(name, i):
    return reader(name).get(i)


@functools.lru_cache(maxsize=40)
def sprite(name, i):
    """Ключ + масштаб к высоте MH; возвращает (RGBA PIL, якорь x, якорь y) — якорь = центр стоп опорного кадра."""
    f = raw(name, i)
    k = key(f, 1.0 if name in BOX else 0.75, 'box' if name in BOX else 'normal')
    if name == 'hang':                                    # пурпурная перекладина → бордовая линия графика
        x = f.astype(np.int16)
        m = (x[..., 0] > 150) & (x[..., 2] > 150) & (x[..., 1] < 130)
        m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        k[m, :3] = (150, 24, 52)
        k[m, 3] = 255
    h_, fx_, fy_ = GEO[name]
    s = MH / h_
    # края кадра клипа растушёвываем (искры не обрываются линией), низ — нет (там стопы)
    hh, ww = k.shape[:2]
    e = 40
    ry = np.clip(np.minimum(np.arange(hh), hh - 1 - np.arange(hh)) / e, 0, 1)
    rx = np.clip(np.minimum(np.arange(ww), ww - 1 - np.arange(ww)) / e, 0, 1)
    ry[hh - 60:] = 1
    k[..., 3] = (k[..., 3] * np.minimum(ry[:, None], rx[None, :])).astype(np.uint8)
    im = Image.fromarray(k).resize((round(ww * s), round(hh * s)), Image.BILINEAR)
    return im, fx_ * s, fy_ * s


def frame_at(name, ct):
    n = reader(name).n
    u = ct * CFPS
    if u > n - 1:                                         # хвост клипа — «маятник» по последней секунде
        span = CFPS
        q = (u - (n - 1)) % (2 * span)
        u = (n - 1) - (q if q < span else 2 * span - q)
    return sprite(name, int(max(0, min(n - 1, round(u)))))


def seg_index(t):
    k = 0
    for j, s in enumerate(SEGS):
        if t >= s[0]:
            k = j
    return k


def hang_dy(t):
    return -HANG_LIFT * ease((t - (P + 0.9)) / 3.4)


def placed(j, t):
    _, name, keys = SEGS[j]
    im, ax, ay = frame_at(name, clip_time(keys, t))
    dy = hang_dy(t) if name == 'hang' else 0.0
    return im, int(round(CX - ax)), int(round(FOOT - ay + dy))


def blend(a, b, k):
    """Смешать два размещённых RGBA (premultiplied) → один размещённый."""
    (ia, xa, ya), (ib, xb, yb) = a, b
    x0, y0 = int(min(xa, xb)), int(min(ya, yb))
    x1 = int(max(xa + ia.width, xb + ib.width)) + 1
    y1 = int(max(ya + ia.height, yb + ib.height)) + 1
    acc = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
    for im, x, y, w in ((ia, xa, ya, 1 - k), (ib, xb, yb, k)):
        arr = np.asarray(im, np.float32)
        al = arr[..., 3:4] / 255.0
        ox, oy = int(round(x - x0)), int(round(y - y0))
        acc[oy:oy + arr.shape[0], ox:ox + arr.shape[1], :3] += arr[..., :3] * al * w
        acc[oy:oy + arr.shape[0], ox:ox + arr.shape[1], 3] += al[..., 0] * w
    al = np.maximum(acc[..., 3:4], 1e-4)
    rgb = np.where(acc[..., 3:4] > 1e-4, acc[..., :3] / al, 0)
    out = np.dstack([rgb, acc[..., 3] * 255]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out), x0, y0


def mita_placed(t):
    j = seg_index(t)
    cur = placed(j, t)
    if j > 0 and SEGS[j][1] not in HARD:
        k = (t - SEGS[j][0]) / XF
        if k < 1:
            return blend(placed(j - 1, t), cur, ease(k))
    return cur


def bar_screen(t):
    """Где на экране перекладина (линия графика) в сцене «висит»: (x левый, x правый, y)."""
    h_, fx_, fy_ = GEO['hang']
    s = MH / h_
    ox, oy = CX - fx_ * s, FOOT - fy_ * s + hang_dy(t)
    return ox + 164 * s, ox + 559 * s, oy + 100 * s


@functools.lru_cache(None)
def shadow_img():
    return fx.radial(256, (20, 10, 20), 1.6, 1.0).resize((360, 64))


def draw(cv, t, alpha=1.0):
    if t >= E.CREEPY - 0.1 and t < E.CREEPY_END + 0.2:
        pass                                              # во время жути Мита та же (шепчет), её не прячем
    name = SEGS[seg_index(t)][1]
    if name != 'hang' or hang_dy(t) > -20:
        fx.over(cv, fx.warp(shadow_img(), CX, FOOT - 4, 1.0, 1.0, 0.0), 0.35 * alpha)
    else:
        k = min(1.0, -hang_dy(t) / HANG_LIFT)
        fx.over(cv, fx.warp(shadow_img(), CX, FOOT - 4, 1.0 - 0.4 * k, 1.0 - 0.4 * k, 0.0), 0.35 * alpha * (1 - 0.6 * k))
    fx.over(cv, mita_placed(t), alpha)


# ------------------------------------------------------------------ отражение в нише (жуть)
@functools.lru_cache(maxsize=40)
def mirror_sprite(i, w):
    f = raw('creepy_mirror', i)
    k = key(f)
    im = Image.fromarray(k).transpose(Image.FLIP_LEFT_RIGHT)
    s = w / im.width
    return im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR), s


def mirror_frame(t, w):
    u = max(0.0, t - MIRROR_T0)
    n = reader('creepy_mirror').n
    i = int(min(n - 1, round(u * CFPS)))
    return mirror_sprite(i, w)
