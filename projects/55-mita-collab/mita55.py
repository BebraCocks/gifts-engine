"""Клипы Gemini для 55: Мита (4 наряда, зелёный фон) и живые NFT (синий/зелёный фон).
Ключ — по доминирующему каналу фона (кадр за кадром). Мита: одна высота MH во всех клипах, якорь — центр стоп
опорного (первого) кадра клипа. Время клипа — опорные точки «время ролика → время клипа» (жесты под слова)."""
import functools
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
GEO = json.loads((HERE / 'data' / 'geom.json').read_text())
CFPS = 24
MH = 780
XF = 0.3
VID = {n: HERE / 'input' / 'mita' / 'video' / f'{n}.mp4' for n in
       ('hook', 'gamer1', 'gamer2', 'gamer3', 'collector1', 'collector2', 'plush_creepy', 'blogger1', 'blogger2',
        'blogger3', 'outro')}
VID.update({n: HERE / 'input' / 'nft' / f'{n}.mp4' for n in ('fox', 'heart', 'cactus', 'award')})


def bg_of(f):
    c = np.concatenate([f[:24, :24].reshape(-1, 3), f[:24, -24:].reshape(-1, 3), f[-24:, :24].reshape(-1, 3),
                        f[-24:, -24:].reshape(-1, 3)])
    return np.median(c, 0).astype(np.float32)


def key(f, soft=0.8):
    bg = bg_of(f)
    ch = int(np.argmax(bg))
    o = [i for i in range(3) if i != ch]
    x = f.astype(np.float32)
    sc = x[..., ch] - np.maximum(x[..., o[0]], x[..., o[1]])
    s0 = max(20.0, float(bg[ch] - max(bg[o[0]], bg[o[1]])))
    a = np.clip((s0 * 0.85 - sc) / (s0 * soft), 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.6)
    a[a < 0.05] = 0
    aa = np.maximum(a, 1e-3)[..., None]
    fg = (x - (1 - a[..., None]) * bg) / aa
    fg = np.where(a[..., None] > 0.02, fg, 0)
    lim = np.maximum(fg[..., o[0]], fg[..., o[1]]) * 1.04 + 4
    fg[..., ch] = np.where(a < 0.98, np.minimum(fg[..., ch], lim), fg[..., ch])
    return np.dstack([fg.clip(0, 255), a * 255]).astype(np.uint8)


class Reader:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.pos = 0

    def get(self, i):
        i = max(0, min(self.n - 1, i))
        if i < self.pos or i > self.pos + 48:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            self.pos = i
        f = None
        while self.pos <= i:
            ok, fr = self.cap.read()
            self.pos += 1
            if not ok:
                break
            f = fr
        return cv2.cvtColor(f, cv2.COLOR_BGR2RGB)


@functools.lru_cache(None)
def reader(name):
    return Reader(VID[name])


@functools.lru_cache(maxsize=24)
def keyed(name, i):
    return key(reader(name).get(i))


def idx(name, ct, pingpong=True):
    n = reader(name).n
    u = ct * CFPS
    if u > n - 1:
        span = CFPS * 1.5
        q = (u - (n - 1)) % (2 * span)
        u = (n - 1) - (q if q < span else 2 * span - q)
    return int(max(0, min(n - 1, round(u))))


def clip_time(keys, t):
    if t <= keys[0][0]:
        return keys[0][1] + (t - keys[0][0])
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        if t <= t1:
            return c0 + (c1 - c0) * (t - t0) / (t1 - t0)
    return keys[-1][1] + (t - keys[-1][0])


# ------------------------------------------------------------------ Мита
@functools.lru_cache(maxsize=40)
def mita_sprite(name, i):
    k = keyed(name, i).copy()
    g = GEO[name]
    hh, ww = k.shape[:2]
    e = 36
    ry = np.clip(np.minimum(np.arange(hh), hh - 1 - np.arange(hh)) / e, 0, 1)
    rx = np.clip(np.minimum(np.arange(ww), ww - 1 - np.arange(ww)) / e, 0, 1)
    ry[hh - 80:] = 1
    k[..., 3] = (k[..., 3] * np.minimum(ry[:, None], rx[None, :])).astype(np.uint8)
    s = MH / (g['bot'] - g['top'])
    im = Image.fromarray(k).resize((round(ww * s), round(hh * s)), Image.BILINEAR)
    return im, g['hx'] * s, g['bot'] * s


def placed(name, keys, t, cx, foot):
    im, ax, ay = mita_sprite(name, idx(name, clip_time(keys, t)))
    return im, int(round(cx - ax)), int(round(foot - ay))


def blend(a, b, k):
    (ia, xa, ya), (ib, xb, yb) = a, b
    x0, y0 = min(xa, xb), min(ya, yb)
    x1, y1 = max(xa + ia.width, xb + ib.width), max(ya + ia.height, yb + ib.height)
    acc = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
    for im, x, y, w in ((ia, xa, ya, 1 - k), (ib, xb, yb, k)):
        arr = np.asarray(im, np.float32)
        al = arr[..., 3:4] / 255.0
        acc[y - y0:y - y0 + arr.shape[0], x - x0:x - x0 + arr.shape[1], :3] += arr[..., :3] * al * w
        acc[y - y0:y - y0 + arr.shape[0], x - x0:x - x0 + arr.shape[1], 3] += al[..., 0] * w
    al = np.maximum(acc[..., 3:4], 1e-4)
    rgb = np.where(acc[..., 3:4] > 1e-4, acc[..., :3] / al, 0)
    return Image.fromarray(np.dstack([rgb, acc[..., 3] * 255]).clip(0, 255).astype(np.uint8)), x0, y0


# ------------------------------------------------------------------ живые NFT
@functools.lru_cache(maxsize=96)
def nft_sprite(name, i, size):
    k = keyed(name, i)
    g = GEO[name]
    m = 70
    x0, x1 = max(0, g['x0'] - m), min(g['w'], g['x1'] + m)
    y0, y1 = max(0, g['top'] - m), min(g['h'], g['bot'] + m)
    sub = Image.fromarray(k[y0:y1, x0:x1])
    s = size / max(g['x1'] - g['x0'], g['bot'] - g['top'])
    return sub.resize((max(1, round(sub.width * s)), max(1, round(sub.height * s))), Image.BILINEAR)


def nft(name, t, size, speed=1.0):
    """Кадр живого NFT размером ~size (по большей стороне объекта); цикл «туда-обратно» по 0,4–9,6 с клипа."""
    q = (t * speed) % 18.4
    ct = 0.4 + (q if q < 9.2 else 18.4 - q)
    return nft_sprite(name, idx(name, ct), int(size))
