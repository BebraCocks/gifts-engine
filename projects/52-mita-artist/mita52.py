"""Мита в ролике 52: клипы Gemini (build/clips/<имя>), позы ChatGPT «тычок» (frames_aligned), жуткие картинки
creep_a/b/c (полунабросок), переходы ластиком (стирает) и карандашом (дорисовывает) вместо ходьбы.
Все фигуры приводятся к одному росту MITA_H (правило автора: габариты Миты одинаковые)."""
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
SHEETS = HERE / 'input' / 'mita' / 'sheets'
MITA_H = 820
FOOT = 1560
STAND = 997.0           # рост стоя в клипах Gemini (px исходника 720×1280)
CFPS = 24
LEFT = 300
POKE_SEQ = ['poke_1', 'poke_2a', 'poke_m1', 'poke_m2', 'poke_m3', 'poke_2b', 'poke_2c', 'poke_3', 'poke_4', 'poke_5',
            'poke_6', 'poke_7', 'poke_8', 'poke_9']
POSE_H = 930.0


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


@functools.lru_cache(maxsize=200)
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
    T.append(dict(t0=-1, t1=E.BUCKET_IN, kind='clip', name='hook', x=540, off=0.0, mode='pp', base=0.0))
    T.append(dict(t0=E.BUCKET_IN, t1=E.OUT_START, kind='clip', name='bucket_in', x=540, off=E.BUCKET_OFF, mode='once'))
    T.append(dict(t0=E.OUT_START, t1=E.OUT_START + 4.4, kind='clip', name='bucket_out', x=540, off=0.25, mode='once'))
    T.append(dict(t0=E.OUT_START + 4.4, t1=E.ERASE1, kind='clip', name='talk', x=540, off=0.0, mode='pp'))
    T.append(dict(t0=E.ERASE1, t1=E.CREEPY, kind='poke', x=LEFT))
    T.append(dict(t0=E.CREEPY, t1=E.CREEPY_END, kind='creepy', x=540))
    T.append(dict(t0=E.CREEPY_END, t1=E.CREEPY_END + 2.95, kind='clip', name='glass_heart', x=540, off=0.0, mode='once'))
    T.append(dict(t0=E.CREEPY_END + 2.95, t1=E.ERASE2, kind='clip', name='talk', x=540, off=3.0, mode='pp'))
    T.append(dict(t0=E.ERASE2, t1=DUR + 5, kind='clip', name='choice', x=LEFT, off=0.0, mode='once', hold=4.6))
    return T


TRACK = _track()
MOVES = [(E.ERASE1, 540, LEFT), (E.ERASE2, 540, LEFT)]     # стереть в старом месте → дорисовать в новом
MOVE_D = 0.5


def seg_at(t):
    for i, s in enumerate(TRACK):
        if s['t0'] <= t < s['t1']:
            return i, s
    return len(TRACK) - 1, TRACK[-1]


def x_of(t):
    i, s = seg_at(t)
    if s['kind'] == 'creepy':
        return 540
    return s['x']


# ------------------------------------------------------------------ позы
_AL = False


def _ensure():
    global _AL
    if _AL:
        return
    if not all((SP.AL / f'{n}.png').exists() for n in POKE_SEQ):
        SP.align_all(POKE_SEQ)
    anim.FR = SP.AL
    anim.pose.cache_clear()
    _AL = True


def pose_img(arr):
    s = MITA_H / POSE_H
    im = Image.fromarray(arr)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    return im, (384 * s, 990 * s)


POKE_KEYS = None


def poke_keys():
    """(время, поза): тычок медленный, отдёргивание быстрое, испуг держится."""
    t0 = E.POKE - 0.55
    ks = [(t0, 'poke_1'), (E.POKE - 0.1, 'poke_1'), (E.POKE + 0.12, 'poke_2a'), (E.POKE + 0.3, 'poke_m1'),
          (E.POKE + 0.45, 'poke_m2'), (E.POKE + 0.57, 'poke_m3'), (E.POKE + 0.66, 'poke_2b'), (E.POKE + 0.74, 'poke_2c'),
          (E.POKE + 0.82, 'poke_3'), (E.POKE + 0.92, 'poke_4'), (E.POKE + 1.02, 'poke_5'), (E.POKE + 1.25, 'poke_5'),
          (E.POKE + 1.4, 'poke_6'), (E.POKE + 1.55, 'poke_7'), (E.POKE + 1.7, 'poke_8'), (E.POKE + 1.85, 'poke_9')]
    return ks


def poke_frame(t):
    ks = poke_keys()
    if t <= ks[0][0]:
        return anim.pose('poke_1')
    for (ta, na), (tb, nb) in zip(ks, ks[1:]):
        if t < tb:
            if na == nb:
                return anim.pose(na)
            return anim.morph(na, nb, ease((t - ta) / (tb - ta)))
    return anim.pose(ks[-1][1])


def poke_tip(t):
    """Где кончик кисти у позы тычка (для подарка в цепях): в кадре 768×1024 ≈ (720, 300)."""
    s = MITA_H / POSE_H
    return LEFT + (720 - 384) * s, FOOT - (990 - 300) * s


# ------------------------------------------------------------------ жуть
@functools.lru_cache(maxsize=4)
def creep(name):
    im = Image.open(SHEETS / f'creep_{name}_al.png').convert('RGBA')
    s = MITA_H / 1426.0
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im, (522 * s, 1461 * s)


def draw_creepy(cv, t, put, a=1.0):
    for name, t0, d in (('a', -1, 0.0), ('b', E.CREEP_B, 0.7), ('c', E.CREEP_C, 0.5)):
        k = 1.0 if t0 < 0 else ease((t - t0) / d)
        if k <= 0:
            break
        im, anc = creep(name)
        put(cv, im, 540, FOOT, 1.0, a * k, anchor=anc)


# ------------------------------------------------------------------ рисование
def _clip_draw(cv, s, t, put, a=1.0, x=None):
    lt = t - s['t0'] + s['off'] if s['t0'] > -1 else t + s['off']
    if s.get('hold') and lt > s['hold']:
        lt = s['hold']
    im, anc = clip_img(s['name'], clip_index(s['name'], lt, s['mode']))
    put(cv, im, s['x'] if x is None else x, FOOT, 1.0, a, anchor=anc)


def _seg_draw(cv, s, t, put, a=1.0, x=None):
    if s['kind'] == 'clip':
        _clip_draw(cv, s, t, put, a, x)
    elif s['kind'] == 'poke':
        im, anc = pose_img(poke_frame(t))
        put(cv, im, s['x'] if x is None else x, FOOT, 1.0, a, anchor=anc)
    elif s['kind'] == 'creepy':
        draw_creepy(cv, t, put, a)


def wipe_alpha(img, k, from_top=True):
    """Стереть/проявить: сверху вниз доля k видна (карандаш) или скрыта (ластик)."""
    a = np.array(img)
    h = a.shape[0]
    yy = np.arange(h, dtype=np.float32)[:, None]
    edge = k * (h + 40) - 20
    m = np.clip((edge - yy) / 20 + 0.5, 0, 1)
    a = a.copy()
    a[..., 3] = (a[..., 3] * m).astype(np.uint8)
    return Image.fromarray(a)


def draw(cv, t, put, shadow=None, tool=None):
    """tool(kind, x, y, k) — рисует ластик/карандаш во время перемещения."""
    _ensure()
    i, s = seg_at(t)
    for (tm, x0, x1) in MOVES:
        if tm <= t < tm + 2 * MOVE_D:
            u = (t - tm) / MOVE_D
            prev = TRACK[i - 1] if s['t0'] == tm else s
            if u < 1:                                   # ластик стирает старую Миту
                cur = prev if s['t0'] == tm else s
                k = ease(u)
                _draw_wiped(cv, cur, tm - 1e-3 if s['t0'] == tm else t, put, x0, k, erase=True)
                if tool:
                    tool('eraser', x0, FOOT - MITA_H * (1 - k) - 20, u)
            else:                                       # карандаш дорисовывает в новом месте
                k = ease(u - 1)
                _draw_wiped(cv, s, t, put, x1, k, erase=False)
                if tool:
                    tool('pencil', x1 + 60, FOOT - MITA_H * (1 - k), u - 1)
            return
    if shadow and s['kind'] != 'creepy':
        shadow(cv, x_of(t), FOOT)
    _seg_draw(cv, s, t, put)
    # растворение между соседними клипами
    if i > 0 and t - s['t0'] < 0.25:
        p = TRACK[i - 1]
        if p['kind'] == s['kind'] == 'clip' and p['x'] == s['x']:
            _seg_draw(cv, p, s['t0'] - 1e-3, put, 1 - ease((t - s['t0']) / 0.25))
    # выход из жути: полунабросок растворяется под вихрем краски
    if i > 0 and TRACK[i - 1]['kind'] == 'creepy' and t - s['t0'] < 0.9:
        draw_creepy(cv, s['t0'] - 1e-3, put, 1 - ease((t - s['t0']) / 0.9))


def _draw_wiped(cv, s, t, put, x, k, erase):
    """Миту рисуем во временный слой, потом стираем/проявляем сверху вниз."""
    from fx import draw_rgba  # noqa
    tmp = np.zeros((1920, 1080, 4), np.float32)
    _seg_draw(tmp, s, t, put, 1.0, x)
    a = tmp[..., 3]
    yy = np.arange(1920, dtype=np.float32)[:, None]
    top = FOOT - MITA_H - 30
    edge = top + k * (MITA_H + 60)
    if erase:
        m = np.clip((yy - edge) / 20 + 0.5, 0, 1)
    else:
        m = np.clip((edge - yy) / 20 + 0.5, 0, 1)
    m = m[..., None] if m.ndim == 2 else m
    al = a[..., None] * m                                  # tmp — премультиплицированный (фон чёрный, альфа 0..1)
    cv[..., :3] = cv[..., :3] * (1 - al) + tmp[..., :3] * m


def draw_ad(cv, bt, put, a=1.0, x=540, foot=660, h=600):
    """Реклама: Мита у мольберта над баннером (клип easel). Масштаб — по высоте h (мольберт выше Миты)."""
    lt = max(0.0, bt + 0.4)
    g = GEO['easel']
    n = g['n']
    f = int(lt * CFPS)
    p = f % (2 * n - 2)
    idx = p if p < n else 2 * n - 2 - p
    im = Image.open(CLIPS / 'easel' / f'f{idx + 1:04d}.png')
    s = h / (g['bot'] - 210)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    put(cv, im, x, foot, 1.0, a, anchor=(362 * s, g['bot'] * s))
    return lt
