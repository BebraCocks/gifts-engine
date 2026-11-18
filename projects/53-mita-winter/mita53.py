"""Мита в ролике 53: клипы Gemini (build/clips/<имя>), жуткие картинки creep_a/b/c (иней → лёд → статуя).
Переход «по погоде»: коробка (клип A) → вспышка → ленты разматываются (клип B задом наперёд).
Перемещение — «снежная россыпь»: Мита рассыпается снежинками и собирается в новом месте (без ходьбы).
Все фигуры приводятся к одному росту MITA_H (правило автора: габариты Миты одинаковые)."""
import functools
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import events as E
from timeline import AD_STOP, DUR

HERE = Path(__file__).resolve().parent
CLIPS = HERE / 'build' / 'clips'
KEYED = HERE / 'build' / 'keyed'
GEO = json.loads((CLIPS / 'geom.json').read_text())
MITA_H = 820
FOOT = 1560
STAND = 998.0
CFPS = 24
LEFT = 300


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


@functools.lru_cache(maxsize=160)
def clip_img(name, idx):
    g = GEO[name]
    im = Image.open(CLIPS / name / f'f{idx + 1:04d}.png')
    s = MITA_H / STAND
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    return im, (g['hx'] * s, g['bot'] * s)


def clip_index(name, lt, mode):
    n = GEO[name]['n']
    f = max(0, int(lt * CFPS))
    if mode == 'once':
        return min(n - 1, f)
    p = f % (2 * n - 2)
    return p if p < n else 2 * n - 2 - p


# ------------------------------------------------------------------ дорожка
def _track():
    T = []
    a = T.append
    a(dict(t0=-1, t1=E.BOX_IN, kind='clip', name='hook', x=540, off=0.0, mode='once'))
    a(dict(t0=E.BOX_IN, t1=E.FLASH, kind='box_a', x=540))
    a(dict(t0=E.FLASH, t1=E.B_END, kind='box_b', x=540))
    a(dict(t0=E.B_END, t1=E.COOKIE, kind='clip', name='talk', x=540, off=0.0, mode='pp'))
    a(dict(t0=E.COOKIE, t1=E.BELL + 0.1, kind='clip', name='breath', x=540, off=0.0, mode='once'))
    a(dict(t0=E.BELL + 0.1, t1=E.CREEPY, kind='clip', name='talk', x=540, off=1.0, mode='pp'))
    a(dict(t0=E.CREEPY, t1=E.CREEPY_END, kind='creepy', x=540))
    a(dict(t0=E.CREEPY_END, t1=E.MOVE1, kind='clip', name='talk', x=540, off=4.0, mode='pp'))
    a(dict(t0=E.MOVE1, t1=E.MOVE2, kind='clip', name='talk', x=LEFT, off=6.5, mode='pp'))
    a(dict(t0=E.MOVE2, t1=DUR + 5, kind='clip', name='globe', x=540, off=0.0, mode='once', hold=9.5))
    return T


TRACK = _track()
MOVES = [(E.MOVE1, 540, LEFT), (E.MOVE2, LEFT, 540)]
MOVE_D = 0.42


def seg_at(t):
    for i, s in enumerate(TRACK):
        if s['t0'] <= t < s['t1']:
            return i, s
    return len(TRACK) - 1, TRACK[-1]


def x_of(t):
    for tm, x0, x1 in MOVES:
        if tm <= t < tm + MOVE_D:
            return x0
    return seg_at(t)[1]['x']


# ------------------------------------------------------------------ жуть
@functools.lru_cache(maxsize=4)
def creep(name):
    im = Image.open(KEYED / f'creep_{name}.png').convert('RGBA')
    a = np.array(im)[..., 3]
    ys, xs = np.nonzero(a > 215)
    top, bot = ys.min(), ys.max()
    low = ys > bot - 40
    fx = (xs[low].min() + xs[low].max()) / 2
    ga = np.array(Image.open(KEYED / 'creep_a.png'))[..., 3]
    yy = np.nonzero(ga > 215)[0]
    s = MITA_H / float(yy.max() - yy.min()) * 1.005
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im, (fx * s, bot * s)


def creepy_stage(t):
    """0..2: доля перехода a→b→c."""
    if t < E.CREEP_B:
        return 0.0
    if t < E.CREEP_C:
        return ease((t - E.CREEP_B) / 1.0)
    return 1.0 + ease((t - E.CREEP_C) / 1.0)


def draw_creepy(cv, t, put, a=1.0):
    st = creepy_stage(t)
    ims = [('a', 1.0)]
    if st > 0:
        ims.append(('b', min(1.0, st)))
    if st > 1:
        ims.append(('c', st - 1))
    for name, k in ims:
        im, anc = creep(name)
        put(cv, im, 540, FOOT, 1.0, a * k, anchor=anc)


# ------------------------------------------------------------------ рисование
def _clip_draw(cv, s, t, put, a=1.0, x=None, name=None, lt=None):
    if lt is None:
        lt = t - s['t0'] + s['off'] if s['t0'] > -1 else t + s['off']
        if s.get('hold') and lt > s['hold']:
            lt = s['hold']
    nm = name or s['name']
    im, anc = clip_img(nm, clip_index(nm, lt, s.get('mode', 'once')))
    put(cv, im, s['x'] if x is None else x, FOOT, 1.0, a, anchor=anc)


def box_time(s, t):
    if s['kind'] == 'box_a':
        return 'box_a', E.A0 + (t - s['t0']) * E.A_SPD
    return 'box_b', max(E.B1, E.B0 - (t - s['t0']) * E.B_SPD)


def _seg_draw(cv, s, t, put, a=1.0, x=None):
    k = s['kind']
    if k == 'clip':
        _clip_draw(cv, s, t, put, a, x)
    elif k in ('box_a', 'box_b'):
        nm, lt = box_time(s, t)
        _clip_draw(cv, dict(s, mode='once'), t, put, a, x, nm, lt)
    elif k == 'creepy':
        pass                      # жуть рисует render.py: Мита внутри ёлочного шара (клип glass)


@functools.lru_cache(maxsize=2)
def _noise():
    rng = np.random.default_rng(53)
    n = rng.random((60, 34)).astype(np.float32)
    return cv2.resize(n, (1080, 1920), interpolation=cv2.INTER_CUBIC)


def _draw_dissolve(cv, s, t, put, x, k, out):
    """Снежная россыпь: пиксели исчезают (out) / проявляются по шуму, сверху вниз с подмешиванием."""
    tmp = np.zeros((1920, 1080, 4), np.float32)
    _seg_draw(tmp, s, t, put, 1.0, x)
    yy = (np.arange(1920, dtype=np.float32)[:, None] - (FOOT - MITA_H)) / MITA_H
    order = np.clip(0.55 * _noise() + 0.45 * (yy if out else 1 - yy), 0, 1)
    th = k * 1.25 - 0.12
    m = np.clip((order - th) / 0.12, 0, 1) if out else np.clip((th - order) / 0.12, 0, 1)
    m = m[..., None]
    cv[..., :3] = cv[..., :3] * (1 - tmp[..., 3:4] * m) + tmp[..., :3] * m


def draw(cv, t, put, shadow=None, poof=None):
    """poof(x, k, out) — рисует снежинки во время перемещения."""
    i, s = seg_at(t)
    for (tm, x0, x1) in MOVES:
        if tm <= t < tm + 2 * MOVE_D:
            u = (t - tm) / MOVE_D
            if u < 1:
                prev = TRACK[i - 1] if s['t0'] == tm else s
                _draw_dissolve(cv, prev, tm - 1e-3, put, x0, ease(u), True)
                if poof:
                    poof(x0, u, True)
            else:
                _draw_dissolve(cv, s, t, put, x1, ease(u - 1), False)
                if poof:
                    poof(x1, u - 1, False)
            return
    if shadow and s['kind'] != 'creepy':
        shadow(cv, x_of(t), FOOT)
    _seg_draw(cv, s, t, put)
    # растворение между соседними сегментами на одном месте
    if i > 0 and t - s['t0'] < 0.25:
        p = TRACK[i - 1]
        if p['x'] == s['x'] and p['kind'] != 'creepy' and s['kind'] != 'box_b':
            _seg_draw(cv, p, s['t0'] - 1e-3, put, 1 - ease((t - s['t0']) / 0.25))
    # вход в жуть: пряник «перетекает» в первую стадию инея
    if s['kind'] == 'creepy' and t - s['t0'] < 0.6:
        p = TRACK[i - 1]
        _seg_draw(cv, p, s['t0'] - 1e-3, put, 1 - ease((t - s['t0']) / 0.6))


def draw_ad(cv, bt, put, a=1.0, right=1080, foot=660, h=560):
    """Реклама: Мита наряжает ёлку над баннером (клип tree). Правый край клипа = край экрана (ёлка обрезана Gemini)."""
    lt = max(0.0, bt + 0.6)
    g = GEO['tree']
    n = g['n']
    f = 18 + int(lt * CFPS) % (2 * (n - 18) - 2)
    m = n - 18
    idx = 18 + (f - 18 if f - 18 < m else 2 * m - 2 - (f - 18))
    idx = min(n - 1, max(18, idx))
    im = Image.open(CLIPS / 'tree' / f'f{idx + 1:04d}.png')
    s = h / (g['bot'] - g['top'])
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    put(cv, im, right, foot, 1.0, a, anchor=(im.width, g['bot'] * s))
