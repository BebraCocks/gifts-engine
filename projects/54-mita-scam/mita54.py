"""Мита в ролике 54: клипы Gemini (build/clips/<имя>) + картинки ChatGPT (детектив, жуть creep_1…5).
Мита весь ролик слева (x=LEFT), в финале — в центре. Ноги закреплены: якорь — центр стоп в КАЖДОМ кадре.
Рост: обычная Мита (до кепки) MITA_H, детектив с кепкой DET_H (кепка добавляет ~5 %)."""
import functools
import json
from pathlib import Path

import numpy as np
from PIL import Image

import events as E
from timeline import DUR

HERE = Path(__file__).resolve().parent
CLIPS = HERE / 'build' / 'clips'
KEYED = HERE / 'build' / 'keyed'
GEO = json.loads((CLIPS / 'geom.json').read_text())
MITA_H = 800
DET_H = 860
FOOT = 1560
CFPS = 24
LEFT = 290
LENS_X = 300            # v4: перевоплощение левее центра (там детектив стоит весь первый акт)
STAMP_HIT = 5.4          # в клипе stamp второй удар (ноги вместе) — кадр удара
STAMP_A, STAMP_B = 4.55, 6.9


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


@functools.lru_cache(maxsize=220)
def clip_img(name, idx):
    g = GEO[name]
    im = Image.open(CLIPS / name / f'f{idx + 1:04d}.png')
    a = np.array(im)[..., 3]
    ys, xs = np.nonzero(a > 128)
    bot = ys.max()
    low = ys > bot - 40
    fx = (xs[low].min() + xs[low].max()) / 2              # центр стоп именно в этом кадре — ноги не «плывут»
    h = (DET_H if name != 'hook' else MITA_H) / (g['bot'] - g['top'])
    im = im.resize((round(im.width * h), round(im.height * h)), Image.BILINEAR)
    return im, (fx * h, g['bot'] * h)


def clip_n(name):
    return GEO[name]['n']


def idx_at(name, lt, mode='once'):
    n = clip_n(name)
    f = max(0, int(lt * CFPS))
    if mode == 'once':
        return min(n - 1, f)
    p = f % (2 * n - 2)
    return p if p < n else 2 * n - 2 - p


@functools.lru_cache(maxsize=8)
def still(name):
    """Статичная картинка ChatGPT (detective / creep_k) в масштабе DET_H, якорь — центр стоп."""
    im = Image.open(KEYED / f'{name}.png').convert('RGBA')
    ref = np.array(Image.open(KEYED / 'creep_1.png'))[..., 3]
    ys, xs = np.nonzero(ref > 200)
    h = DET_H / float(ys.max() - ys.min())
    a = np.array(im)[..., 3]
    ys2, xs2 = np.nonzero(a > 200)
    bot = ys2.max()
    low = ys2 > bot - 40
    fx = (xs2[low].min() + xs2[low].max()) / 2
    im = im.resize((round(im.width * h), round(im.height * h)), Image.LANCZOS)
    return im, (fx * h, bot * h)


# ------------------------------------------------------------------ дорожка: (t0, t1, вид, параметры)
RIGHT = 790
CENTER = 540


def _track():
    """Каждая схема — своя мизансцена: Мита меняет сторону (телефон — на противоположной), свои клипы-жесты."""
    pre = STAMP_HIT - STAMP_A
    post = STAMP_B - STAMP_HIT
    L, R, C = LEFT, RIGHT, CENTER
    T = [dict(t0=-1, kind='clip', name='hook', off=0.0, mode='pp', x=L),
         dict(t0=E.LENS1, kind='clip', name='talk', off=0.0, mode='pp', x=L),
         dict(t0=E.OFFER + 0.3, kind='clip', name='phone', off=0.2, mode='once', x=L),
         dict(t0=E.LANG - 0.3, kind='clip', name='lens', off=0.6, mode='once', x=L),
         dict(t0=E.STAMP1 - pre, kind='clip', name='stamp', off=STAMP_A - (E.STAMP1 - pre), mode='once', abs=True, x=L),
         dict(t0=E.STAMP1 + post, kind='clip', name='talk', off=2.0, mode='pp', x=R),
         dict(t0=E.CREEPY, kind='creepy', x=C),
         dict(t0=E.CREEPY_END, kind='clip', name='talk', off=4.0, mode='pp', x=L),
         dict(t0=E.LINK, kind='clip', name='talk', off=1.0, mode='pp', x=R),
         dict(t0=E.LINK_LENS, kind='clip', name='lens', off=0.6, mode='once', x=R),
         dict(t0=E.STAMP3 - 1.1, kind='clip', name='shock', off=0.6, mode='once', x=R),
         dict(t0=E.SWAP, kind='clip', name='talk', off=5.0, mode='pp', x=L),
         dict(t0=E.STAMP4 - 0.7, kind='clip', name='nono', off=0.4, mode='once', x=L),
         dict(t0=E.GUAR, kind='clip', name='talk', off=3.0, mode='pp', x=R),
         dict(t0=E.STAMP5 - pre, kind='clip', name='stamp', off=STAMP_A - (E.STAMP5 - pre), mode='once', abs=True, x=R),
         dict(t0=E.MEMO, kind='clip', name='point', off=0.3, mode='once', x=L),
         dict(t0=E.MOVE2, kind='clip', name='choice', off=0.0, mode='once', hold=9.4, x=C)]
    T.sort(key=lambda s: s['t0'])
    for i in range(len(T) - 1):
        T[i]['t1'] = T[i + 1]['t0']
    T[-1]['t1'] = DUR + 5
    return T


TRACK = _track()
MOVE_D = 0.45
MOVES = [(s['t0'], TRACK[i - 1]['x'], s['x']) for i, s in enumerate(TRACK)
         if i > 0 and s['x'] != TRACK[i - 1]['x'] and s['kind'] != 'creepy' and TRACK[i - 1]['kind'] != 'creepy']


def phone_x(t):
    """Телефон — всегда на стороне, противоположной Мите; при перестановке переезжает."""
    def side(x):
        return RIGHT + 10 if x < CENTER else (LEFT if x > CENTER else None)
    i, s = seg_at(t)
    j = i
    while side(TRACK[j]['x']) is None and j > 0:
        j -= 1
    cur = side(TRACK[j]['x'])
    for tm, x0, x1 in MOVES:
        if tm <= t < tm + MOVE_D * 1.6:
            u = ease((t - tm) / (MOVE_D * 1.6))
            a = side(x0) if side(x0) is not None else cur
            b = side(x1) if side(x1) is not None else a
            return a + (b - a) * u
    return cur


def seg_at(t):
    for i, s in enumerate(TRACK):
        if s['t0'] <= t < s['t1']:
            return i, s
    return len(TRACK) - 1, TRACK[-1]


def x_of(t):
    for tm, x0, x1 in MOVES:
        if tm <= t < tm + MOVE_D:
            return x0
    return seg_at(t)[1].get('x', LEFT)


CREEP_KEYS = ['creep_1', 'creep_2', 'creep_3', 'creep_4', 'creep_5']


def creep_frames(t):
    """Плавная смена 5 картинок жути: [(имя, альфа)]."""
    u = (t - E.CREEPY - 0.3) / max(0.5, (E.CREEPY_END - E.CREEPY - 0.9))
    u = max(0.0, min(1.0, u)) * 4
    k = int(u)
    if k >= 4:
        return [('creep_5', 1.0)]
    f = ease(u - k)
    return [(CREEP_KEYS[k], 1.0), (CREEP_KEYS[k + 1], f)]


def _seg_draw(cv, s, t, put, a=1.0, x=None):
    x = s.get('x', LEFT) if x is None else x
    if s['kind'] == 'clip':
        lt = t - s['t0'] + s['off'] if s['t0'] > -1 else t + s['off']
        if s.get('abs'):
            lt = t + s['off']
        if s.get('hold') and lt > s['hold']:
            lt = s['hold']
        im, anc = clip_img(s['name'], idx_at(s['name'], lt, s.get('mode', 'once')))
        put(cv, im, x, FOOT, 1.0, a, anchor=anc)
    elif s['kind'] == 'creepy':
        for name, k in creep_frames(t):
            im, anc = still(name)
            put(cv, im, x, FOOT, 1.0, a * k, anchor=anc)


def draw(cv, t, put, shadow=None):
    i, s = seg_at(t)
    for tm, x0, x1 in MOVES:                                 # перестановка: растворяется тут — проявляется там
        if tm <= t < tm + 2 * MOVE_D:
            u = (t - tm) / MOVE_D
            if u < 1:
                p = TRACK[i - 1] if s['t0'] == tm else s
                _seg_draw(cv, p, tm - 1e-3, put, 1 - ease(u), x0)
            else:
                if shadow:
                    shadow(cv, x1, FOOT)
                _seg_draw(cv, s, t, put, ease(u - 1), x1)
            return
    if shadow:
        shadow(cv, x_of(t), FOOT)
    if s['kind'] == 'clip' and s['name'] == 'choice' and t - s['t0'] < 0.5:
        p = TRACK[i - 1]
        u = ease((t - s['t0']) / 0.5)
        _seg_draw(cv, p, s['t0'] - 1e-3, put, 1 - u)
        _seg_draw(cv, s, t, put, u)
        return
    _seg_draw(cv, s, t, put)
    if i > 0 and t - s['t0'] < 0.22 and TRACK[i - 1].get('x') == s.get('x'):
        _seg_draw(cv, TRACK[i - 1], s['t0'] - 1e-3, put, 1 - ease((t - s['t0']) / 0.22))


def lens_reveal(cv, t, put, lens_im, lens_geom):
    """Перевоплощение: лупа проходит сверху вниз, под стеклом и выше центра — детектив, ниже — обычная Мита."""
    u = ease((t - E.LENS0) / (E.LENS1 - E.LENS0))
    gcx, gcy, gr, sc = lens_geom
    cy = FOOT - MITA_H - 160 + (MITA_H + 260) * u
    cx = LENS_X + 40 * np.sin(u * 6)
    tmp_n = np.zeros(cv.shape[:2] + (4,), np.float32)
    tmp_d = np.zeros_like(tmp_n)
    im, anc = clip_img('hook', idx_at('hook', t, 'pp'))
    put(tmp_n, im, LENS_X, FOOT, 1.0, 1.0, anchor=anc)
    dim, danc = still('detective')
    put(tmp_d, dim, LENS_X, FOOT, 1.0, 1.0, anchor=danc)
    H, W = cv.shape[:2]
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    inside = (xx - cx) ** 2 + (yy - cy) ** 2 < (gr * sc) ** 2
    m = np.clip((cy - yy) / 30, 0, 1)
    m = np.maximum(m, inside.astype(np.float32))[..., None]
    mix = tmp_d * m + tmp_n * (1 - m)
    a = mix[..., 3:4]
    cv[..., :3] = cv[..., :3] * (1 - a) + mix[..., :3]
    put(cv, lens_im, cx - (gcx - lens_im.width / 2), cy - (gcy - lens_im.height / 2), 1.0, 1.0, 0.0)
    return cx, cy


def draw_ad(cv, bt, put, a=1.0, x=540, foot=660, h=560):
    lt = max(0.0, bt + 1.2)
    name = 'case'
    g = GEO[name]
    n = g['n']
    f = 26 + int(lt * CFPS) % (2 * (n - 26) - 2)
    m = n - 26
    idx = 26 + (f - 26 if f - 26 < m else 2 * m - 2 - (f - 26))
    idx = min(n - 1, max(26, idx))
    im = Image.open(CLIPS / name / f'f{idx + 1:04d}.png')
    s = h / (g['bot'] - g['top'])
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    put(cv, im, x, foot, 1.0, a, anchor=(g['hx'] * s, g['bot'] * s))
