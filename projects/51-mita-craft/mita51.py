"""Мита в ролике 51: клипы Gemini (build/clips/<имя>, tools/key_clips.py), щелчок-переход (snap_preview) и жуткий
наезд (позы creep_* → крупный план по пояс calm → mid → жуткий). Всё — чистые функции времени содержания.
draw(cv, t, put) рисует Миту; x_of(t) — где она стоит (для раскладки сцен)."""
import functools
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import anim
import snap_preview as SP
import events as E
from timeline import ON, END, AD_STOP, DUR

HERE = Path(__file__).resolve().parent
CLIPS = HERE / 'build' / 'clips'
GEO = json.loads((CLIPS / 'geom.json').read_text())
MITA_H = 820              # рост Миты в кадре (макушка → подошва)
FOOT = 1560
CFPS = 24                 # клипы Gemini — 24 к/с (аниме-темп)
CREEP_OUT = 0.7
XF = 0.28                 # длительность растворения между клипами
LEFT = 320                # Мита стоит слева (справа — сравнения)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ клипы
@functools.lru_cache(maxsize=160)
def clip_img(name, idx, h=MITA_H):
    g = GEO[name]
    im = Image.open(CLIPS / name / f'f{idx + 1:04d}.png')
    s = h / (g['bot'] - g['top'])
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    return im, (g['hx'] * s, g['bot'] * s)


def clip_index(name, lt, mode):
    n = GEO[name]['n']
    f = max(0, int(lt * GEO[name].get('fps', CFPS)))
    if mode == 'once':
        return min(n - 1, f)
    if mode == 'loop':
        return f % n
    p = f % (2 * n - 2)                                   # туда-обратно: без скачка на стыке
    return p if p < n else 2 * n - 2 - p


# ------------------------------------------------------------------ дорожка: (начало, конец, вид, параметры)
def _track():
    T = []
    T.append(dict(t0=-1, t1=E.KNOCK, kind='clip', name='hook_normal', x=540, off=1.0, mode='once'))
    T.append(dict(t0=E.KNOCK, t1=E.KNOCK + 3.1, kind='clip', name='knock', x=540, off=0.0, mode='once'))
    T.append(dict(t0=E.KNOCK + 3.1, t1=E.SNAP, kind='clip', name='hook_normal', x=540, off=E.KNOCK + 4.1, mode='once'))
    T.append(dict(t0=E.SNAP, t1=E.SNAP + E.SNAP_DUR, kind='snap', x=540))
    if E.WALK1 > E.SNAP + E.SNAP_DUR + 0.05:
        T.append(dict(t0=E.SNAP + E.SNAP_DUR, t1=E.WALK1, kind='clip', name='talk', x=540, off=0.0, mode='pp'))
    # отходит влево: разворот ≈ 1 с, потом шаги
    w1 = 0.95 + walk_len(540, LEFT) + 0.15
    T.append(dict(t0=E.WALK1, t1=E.WALK1 + w1, kind='walk', name='walk_left', x0=540, x1=LEFT,
                  m0=E.WALK1 + 0.95, off=0.0))
    T.append(dict(t0=E.WALK1 + w1, t1=E.CREEPY, kind='clip', name='talk', x=LEFT, off=2.0, mode='pp'))
    T.append(dict(t0=E.CREEPY, t1=E.CREEPY_END, kind='creepy', x=LEFT))
    T.append(dict(t0=E.CREEPY_END, t1=E.TEASE, kind='clip', name='palm', x=540, off=0.6, mode='pp'))
    T.append(dict(t0=E.TEASE, t1=E.EPIC, kind='clip', name='think', x=540, off=0.0, mode='once'))
    T.append(dict(t0=E.EPIC, t1=E.EPIC + 1.9, kind='clip', name='nope', x=540, off=0.35, mode='once'))
    T.append(dict(t0=E.EPIC + 1.9, t1=E.SWEEP - 2.55, kind='clip', name='talk', x=540, off=4.0, mode='pp'))
    T.append(dict(t0=E.SWEEP - 2.55, t1=E.WALK2, kind='clip', name='sweep', x=540, off=0.0, mode='once'))
    T.append(dict(t0=E.WALK2, t1=E.WALK2 + w1, kind='walk', name='walk_left', x0=540, x1=LEFT,
                  m0=E.WALK2 + 0.95, off=0.0))
    T.append(dict(t0=E.WALK2 + w1, t1=DUR + 5, kind='clip', name='talk', x=LEFT, off=6.0, mode='pp'))
    return T



def seg_at(t):
    for i, s in enumerate(TRACK):
        if s['t0'] <= t < s['t1']:
            return i, s
    return len(TRACK) - 1, TRACK[-1]


WALK_V = 285.0            # px/с — скорость опорной стопы в клипе ходьбы (замер): так ноги не скользят по полу
WALK_ACC = 0.18           # с — разгон и торможение


def walk_pos(s, t):
    """Сдвиг по трапеции скорости: разгон WALK_ACC, ровно WALK_V, торможение — стопы «стоят» на полу."""
    D = abs(s['x1'] - s['x0'])
    v, a_t = WALK_V, WALK_ACC
    cruise = max(0.0, (D - v * a_t) / v)
    u = t - s['m0']
    if u <= 0:
        d = 0.0
    elif u < a_t:
        d = 0.5 * v / a_t * u * u
    elif u < a_t + cruise:
        d = 0.5 * v * a_t + v * (u - a_t)
    elif u < 2 * a_t + cruise:
        w = u - a_t - cruise
        d = 0.5 * v * a_t + v * cruise + v * w - 0.5 * v / a_t * w * w
    else:
        d = D
    return s['x0'] + math.copysign(min(d, D), s['x1'] - s['x0'])


def walk_len(x0, x1):
    D = abs(x1 - x0)
    return WALK_ACC * 2 + max(0.0, (D - WALK_V * WALK_ACC) / WALK_V)


def seg_x(s, t):
    if s['kind'] == 'walk':
        return walk_pos(s, t)
    if s['kind'] == 'creepy':
        return s['x'] + (540 - s['x']) * ease((t - E.CREEPY - 0.4) / (E.CREEPY_CLOSE - E.CREEPY))
    return s['x']


TRACK = _track()


def x_of(t):
    return seg_x(seg_at(t)[1], t)


# ------------------------------------------------------------------ позы ChatGPT (щелчок, жуть) — выровненные кадры
_ALIGNED = False


def _ensure_aligned():
    global _ALIGNED
    if _ALIGNED:
        return
    need = list(SP.SEQ) + ['creep_1', 'creep_2', 'creep_4']
    if not all((SP.AL / f'{n}.png').exists() for n in need):
        SP.align_all(need)
    anim.FR = SP.AL
    anim.pose.cache_clear()
    _ALIGNED = True


POSE_H = 968.0            # рост позы в выровненном кадре 768×1024 (подошва — y 990)


def pose_img(arr, h=MITA_H):
    s = h / POSE_H
    im = Image.fromarray(arr)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    return im, (384 * s, 990 * s)


# ------------------------------------------------------------------ жуткий наезд
CREEP_SEQ = ['creep_1', 'creep_2', 'creep_4']
ZOOM = 2.39               # во сколько раз крупнее к моменту крупного плана


def creep_zoom(t):
    return 1 + (ZOOM - 1) * ease((t - E.CREEPY - 0.3) / (E.CREEPY_CLOSE + 0.3 - E.CREEPY - 0.3))


def creep_pose(t):
    span = (E.CREEPY_CLOSE - E.CREEPY) / (len(CREEP_SEQ) - 1)
    u = max(0.0, (t - E.CREEPY) / span)
    i = min(len(CREEP_SEQ) - 2, int(u))
    return anim.morph(CREEP_SEQ[i], CREEP_SEQ[i + 1], ease(u - i))


@functools.lru_cache(maxsize=8)
def closeup(name):
    return Image.open(HERE / 'input' / 'mita' / 'sheets' / f'{name}_key.png').convert('RGBA')


# крупный план по пояс: макушка → низ картинки ≈ 1.95 роста головы-до-пояса; подгоняем по высоте головы
BUCKLE = (392.0, 378.0)
CLOSE_BUCKLE = (560.0, 1170.0)
CLOSE_H = 1000            # высота картинки крупного плана в кадре (1536 px исходника)
CLOSE_BOTTOM = 1920       # низ картинки (подол юбки) — над субтитрами она растворяется


def draw_creepy(cv, t, put, mult=1.0):
    """Возвращает True, если Миту нарисовала жуть."""
    z = creep_zoom(t)
    x = seg_x(TRACK[seg_at(t)[0]], t)
    a_close = ease((t - E.CREEPY_CLOSE) / 0.55)
    if a_close < 1:
        im, (ax, ay) = pose_img(creep_pose(t), MITA_H)
        sp = MITA_H / POSE_H
        # якорь — пряжка ремня (392, 378 в выровненной позе); к крупному плану она приходит туда же,
        # где пряжка на картинке крупного плана (560, 1170 из 1024×1536) — растворение без «двойной головы»
        bx0, by0 = x + (BUCKLE[0] - 384) * sp, FOOT - (990 - BUCKLE[1]) * sp
        cs = CLOSE_H / 1536
        bx1, by1 = 540 + (CLOSE_BUCKLE[0] - 512) * cs, CLOSE_BOTTOM - (1536 - CLOSE_BUCKLE[1]) * cs
        k = (z - 1) / (ZOOM - 1)
        wx, wy = bx0 + (bx1 - bx0) * k, by0 + (by1 - by0) * k
        put(cv, im, wx, wy, z, 1.0, anchor=(BUCKLE[0] * sp, BUCKLE[1] * sp))
    if a_close > 0:
        s = CLOSE_H / 1536 * (1 + 0.035 * ease((t - E.CREEPY_CLOSE) / 3.0))
        y_bot = CLOSE_BOTTOM
        for name, t0, d in (('creep_closeup_calm', E.CREEPY_CLOSE, 0.55), ('creep_closeup_mid', E.CREEPY_MID, 0.6),
                            ('creep_closeup', E.CREEPY_FULL, 0.5)):
            a = ease((t - t0) / d)
            if a <= 0:
                break
            put(cv, closeup(name), 540, y_bot, s, mult * a * (a_close if name == 'creep_closeup_calm' else 1.0),
                anchor=(512, 1536))
    return True


# ------------------------------------------------------------------ щелчок-переход
def snap_scale():
    return MITA_H / (POSE_H * 0.72)          # пиксели превью 540×960 → кадр


def draw_snap(cv, t, put, over_rgba):
    lt = t - E.SNAP
    k = snap_scale()
    c = SP.circle(lt)
    if c:
        im, on = c
        im = im.resize((round(im.width * k), round(im.height * k)), Image.BILINEAR)
        put(cv, im, 540, FOOT, 1.0, 1.0)
    a = SP.mita_at(min(lt, SP.TOTAL - 1e-3))
    im, (ax, ay) = pose_img(a)
    rise = ease((lt - SP.T[SP.SEQ.index('snap_wind75')]) / (SP.FLASH - SP.T[SP.SEQ.index('snap_wind75')])) * \
        (1 - ease((lt - SP.FLASH) / (SP.T[SP.SEQ.index('astro_land')] - SP.FLASH)))
    put(cv, im, 540, FOOT - 70 * rise * k, 1.0, 1.0, anchor=(ax, ay))
    return c[1] if c else 0.0


def snap_flash(t):
    lt = t - E.SNAP
    return math.exp(-((lt - SP.FLASH) / 0.09) ** 2)


# ------------------------------------------------------------------ рисование
def _draw_seg(cv, s, t, put, a=1.0):
    if s['kind'] == 'clip':
        lt = (t - s['t0'] + s['off']) if s['t0'] > -1 else (t + s['off'])
        im, anc = clip_img(s['name'], clip_index(s['name'], lt, s['mode']))
        put(cv, im, seg_x(s, t), FOOT, 1.0, a, anchor=anc)
    elif s['kind'] == 'walk':
        lt = t - s['t0'] + s['off']
        im, anc = clip_img(s['name'], clip_index(s['name'], lt, 'once'))
        put(cv, im, seg_x(s, t), FOOT, 1.0, a, anchor=anc)
    elif s['kind'] == 'snap':
        draw_snap(cv, t, put, None)
    elif s['kind'] == 'creepy':
        draw_creepy(cv, t, put)


def draw(cv, t, put, shadow=None):
    _ensure_aligned()
    i, s = seg_at(t)
    if shadow and s['kind'] not in ('creepy',):
        shadow(cv, x_of(t), FOOT)
    after_creepy = i > 0 and TRACK[i - 1]['kind'] == 'creepy' and t - s['t0'] < CREEP_OUT + 0.5
    if after_creepy:
        # Мита стоит выше крупного плана: сначала растворяется крупный план, потом проявляется обычная Мита
        _draw_seg(cv, s, t, put, ease((t - s['t0'] - 0.35) / 0.5))
        if t - s['t0'] < CREEP_OUT:
            draw_creepy(cv, s['t0'] - 1e-3, put, 1 - ease((t - s['t0']) / CREEP_OUT))
    else:
        _draw_seg(cv, s, t, put)
    # растворение: предыдущий сегмент поверх, гаснет за XF (кроме входа/выхода жути и щелчка — там свои переходы)
    if i > 0 and t - s['t0'] < XF:
        p = TRACK[i - 1]
        if p['kind'] in ('clip', 'walk') and s['kind'] in ('clip', 'walk'):
            _draw_seg(cv, p, t, put, 1 - ease((t - s['t0']) / XF))
        elif p['kind'] == 'clip' and s['kind'] == 'snap':
            _draw_seg(cv, p, t, put, 1 - ease((t - s['t0']) / 0.18))
        elif p['kind'] == 'creepy':
            pass
        elif p['kind'] == 'snap' and s['kind'] in ('clip', 'walk'):
            _draw_seg(cv, p, t, put, 1 - ease((t - s['t0']) / XF))


def draw_ad(cv, bt, put, x=540, foot=700, h=560, a=1.0):
    """Реклама: Мита стоит на верхнем крае баннера и колдует вниз (клип cast_down)."""
    lt = max(0.0, bt + 0.4)
    im, anc = clip_img('cast_down', clip_index('cast_down', lt, 'pp'), h)
    put(cv, im, x, foot, 1.0, a, anchor=anc)
    return lt
