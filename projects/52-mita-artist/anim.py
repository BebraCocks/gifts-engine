"""Плавная анимация Миты из ключевых поз ChatGPT (input/mita/frames/*.png, холст 768×1024 с общей привязкой).

• morph(a, b, k) — промежуточный кадр между позами: оптический поток DIS в обе стороны, встречное
  деформирование и смешивание (как «досчёт» кадров в аниме). Поток считается один раз на пару (кэш).
• Track — дорожка ключей [(время, поза)]: между соседними ключами поза перетекает плавно (ease),
  в паузах — «дыхание». Кадр квантуется до 1/24 перехода, чтобы кэш работал.
• magenta(img) — маска магентовых заглушек (карточка, экран, шар, перекладина, ручка): компоненты от 250 px."""
import functools
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

FR = Path(__file__).resolve().parent / 'input' / 'mita' / 'frames'
CW, CH = 768, 1024
Q = 24                                  # квантование доли перехода


@functools.lru_cache(None)
def pose(name):
    return np.array(Image.open(FR / f'{name}.png').convert('RGBA'))


def _gray(a):
    al = a[..., 3:4].astype(np.float32) / 255
    rgb = a[..., :3].astype(np.float32) * al + 128 * (1 - al)      # над серым — поток видит и контур, и детали
    g = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    return g


def _anchor(a):
    """Центр «головы и корпуса» — центр масс верхних 40 % силуэта (для грубого совмещения поз перед потоком)."""
    al = a[..., 3] > 60
    ys, xs = np.nonzero(al)
    y0, y1 = ys.min(), ys.max()
    sel = ys < y0 + 0.4 * (y1 - y0)
    return np.array([xs[sel].mean(), ys[sel].mean()], np.float32)


@functools.lru_cache(None)
def _shift(n1, n2):
    return _anchor(pose(n2)) - _anchor(pose(n1))


def _translate(a, d):
    M = np.float32([[1, 0, d[0]], [0, 1, d[1]]])
    return cv2.warpAffine(a, M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


@functools.lru_cache(maxsize=40)
def _flow(n1, n2):
    """Остаточный поток n1→(n2, сдвинутая к n1 по якорю). DIS medium на 1/2 разрешения + сглаживание."""
    d = _shift(n1, n2)
    a = _gray(pose(n1))
    b = _gray(_translate(pose(n2), -d))
    h_, w_ = a.shape[:2]
    a2, b2 = cv2.resize(a, (w_ // 2, h_ // 2), interpolation=cv2.INTER_AREA), cv2.resize(b, (w_ // 2, h_ // 2), interpolation=cv2.INTER_AREA)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    dis.setFinestScale(0)
    dis.setPatchSize(12)
    dis.setPatchStride(3)
    dis.setGradientDescentIterations(40)
    dis.setVariationalRefinementIterations(8)
    dis.setVariationalRefinementAlpha(30.0)
    f = dis.calc(a2, b2, None)
    f = cv2.GaussianBlur(f, (0, 0), 1.5)
    return cv2.resize(f, (w_, h_), interpolation=cv2.INTER_LINEAR) * 2


@functools.lru_cache(maxsize=40)
def _flow_rev(n1, n2):
    """Поток (n2, совмещённая с n1) → n1."""
    d = _shift(n1, n2)
    a = _gray(_translate(pose(n2), -d))
    b = _gray(pose(n1))
    h_, w_ = a.shape[:2]
    a2, b2 = cv2.resize(a, (w_ // 2, h_ // 2), interpolation=cv2.INTER_AREA), cv2.resize(b, (w_ // 2, h_ // 2), interpolation=cv2.INTER_AREA)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    dis.setFinestScale(0)
    dis.setPatchSize(12)
    dis.setPatchStride(3)
    dis.setGradientDescentIterations(40)
    dis.setVariationalRefinementIterations(8)
    dis.setVariationalRefinementAlpha(30.0)
    f = dis.calc(a2, b2, None)
    f = cv2.GaussianBlur(f, (0, 0), 1.5)
    return cv2.resize(f, (w_, h_), interpolation=cv2.INTER_LINEAR) * 2


@functools.lru_cache(None)
def _grid(h, w):
    return np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))


def _warp(img, flow, k):
    gx, gy = _grid(img.shape[0], img.shape[1])
    mx = gx - flow[..., 0] * k
    my = gy - flow[..., 1] * k
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def _premul(a):
    f = a.astype(np.float32)
    f[..., :3] *= f[..., 3:4] / 255
    return f


@functools.lru_cache(maxsize=48)
def morph_q(n1, n2, qk):
    k = qk / Q
    if qk <= 0:
        return pose(n1)
    if qk >= Q:
        return pose(n2)
    d = _shift(n1, n2)
    A = _premul(pose(n1))
    B = _premul(_translate(pose(n2), -d))                 # n2, совмещённая с n1 по якорю
    fab, fba = _flow(n1, n2), _flow_rev(n1, n2)
    wa = _translate(_warp(A, fab, k), d * k)
    wb = _translate(_warp(B, fba, 1 - k), d * k)
    u = max(0.0, min(1.0, (k - 0.3) / 0.4))
    s = u * u * (3 - 2 * u)                               # резкая смена в середине — меньше «двойных» контуров
    m = wa * (1 - s) + wb * s
    al = np.clip(m[..., 3:4], 1e-3, 255)
    rgb = np.clip(m[..., :3] * 255 / al, 0, 255)
    out = np.concatenate([rgb, np.clip(m[..., 3:4], 0, 255)], -1)
    return out.astype(np.uint8)


def morph(n1, n2, k):
    return morph_q(n1, n2, int(round(max(0.0, min(1.0, k)) * Q)))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


class Track:
    """keys: [(t, pose)], переход в позу ключа длится до его времени от момента (t - dur). Последний держится.
    dur по умолчанию — 0.22 с (или до предыдущего ключа, если ближе)."""

    def __init__(self, keys, dur=0.22):
        self.keys = sorted(keys)
        self.dur = dur

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1], ks[0][1], 0.0
        for i in range(1, len(ks)):
            t1, n1 = ks[i]
            t0, n0 = ks[i - 1]
            d = min(self.dur, t1 - t0)
            if t < t1 - d:
                return n0, n0, 0.0
            if t < t1:
                return n0, n1, ease((t - (t1 - d)) / d)
        return ks[-1][1], ks[-1][1], 0.0

    def frame(self, t):
        a, b, k = self.at(t)
        return morph(a, b, k) if a != b else pose(a)

    def name(self, t):
        a, b, k = self.at(t)
        return b if k >= 0.5 else a


def loop(names, t, period):
    """Плавный цикл по позам (бег, болтание ногами): t → кадр с морфом между соседями."""
    n = len(names)
    f = (t / period * n) % n
    i = int(f)
    return morph(names[i], names[(i + 1) % n], f - i)


def pingpong(names, t, period):
    seq = list(names) + list(names[-2:0:-1])
    return loop(seq, t, period)


def magenta(img, min_area=250):
    """(маска 0..1 float32, список компонент: (x, y, w, h, площадь, центр, точки контура)). Магента — R,B высокие, G низкий."""
    r, g, b, a = [img[..., i].astype(np.int16) for i in range(4)]
    m = ((r > 150) & (b > 150) & (g < 120) & (r - g > 90) & (b - g > 90) & (a > 20)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    keep = np.zeros_like(m)
    comps = []
    for i in range(1, n):
        if st[i, 4] < min_area:
            continue
        keep[lab == i] = 1
        ys, xs = np.nonzero(lab == i)
        comps.append(dict(x=int(st[i, 0]), y=int(st[i, 1]), w=int(st[i, 2]), h=int(st[i, 3]), area=int(st[i, 4]),
                          c=(float(cen[i][0]), float(cen[i][1])), pts=np.stack([xs, ys], 1).astype(np.float32)))
    soft = cv2.GaussianBlur(cv2.dilate(keep, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 0.8)
    return np.clip(soft, 0, 1), comps


def quad_of(comp):
    """4 угла магентовой карточки/экрана (минимальный повёрнутый прямоугольник), по часовой от верхнего левого."""
    rect = cv2.minAreaRect(comp['pts'])
    box = cv2.boxPoints(rect)
    s = box.sum(1)
    d = np.diff(box, axis=1)[:, 0]
    tl, br = box[np.argmin(s)], box[np.argmax(s)]
    tr, bl = box[np.argmin(d)], box[np.argmax(d)]
    return np.array([tl, tr, br, bl], np.float32)


def fill_quad(img, mask, quad, tile, inset=0.0):
    """Вписать RGBA-картинку tile в четырёхугольник quad (перспектива), только внутри маски магенты."""
    th, tw = tile.shape[:2]
    src = np.array([[0, 0], [tw, 0], [tw, th], [0, th]], np.float32)
    q = quad.copy()
    if inset:
        c = q.mean(0)
        q = c + (q - c) * (1 - inset)
    M = cv2.getPerspectiveTransform(src, q)
    warped = cv2.warpPerspective(tile, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)).astype(np.float32)
    return warped


def replace_magenta(img, painter, min_area=250):
    """painter(comps, shape) → RGBA float32 картинка того же размера (что рисовать вместо магенты).
    Магента становится прозрачной, сверху (только в маске) кладётся результат painter."""
    mask, comps = magenta(img, min_area)
    if not comps:
        return img
    out = img.astype(np.float32)
    out[..., 3] *= 1 - mask
    if painter is not None:
        p = painter(comps, img.shape)
        if p is not None:
            pa = (p[..., 3:4] / 255) * mask[..., None]
            out[..., :3] = out[..., :3] * (1 - pa) + p[..., :3] * pa
            out[..., 3:4] = out[..., 3:4] + (255 - out[..., 3:4]) * pa
    return np.clip(out, 0, 255).astype(np.uint8)


def breathe(t, amp=1.0):
    """Лёгкое «дыхание» (масштаб по вертикали) и покачивание."""
    return 1 + 0.006 * amp * math.sin(t * 2.4), 2.5 * amp * math.sin(t * 0.9)


def pingpong_name(names, t, period):
    seq = list(names) + list(names[-2:0:-1])
    n = len(seq)
    f = (t / period * n) % n
    return seq[int(round(f)) % n]
