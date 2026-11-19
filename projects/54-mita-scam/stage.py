"""Постановка v4: детектив + Мита-мошенница в каждой схеме (клипы Gemini, build/clips/<имя>).
Каждый актёр — список сегментов; сегмент — кусочно-линейные куски (t0, t1, кадр0, кадр1, x0, x1) по одному клипу.
Проходы: Gemini держит персонажа в центре кадра («беговая дорожка»), по экрану двигаем кодом со скоростью опорной
стопы (build/clips/gait.json) — стопы не скользят. Мошенницы нарисованы лицом влево; слева от детектива — зеркально.
Стыки клипов: следующий клип начинается с позы, где закончился предыдущий + наплыв XF."""
import functools
import json
from pathlib import Path

import numpy as np
from PIL import Image

import events as E
import mita54 as M
from timeline import DUR

HERE = Path(__file__).resolve().parent
CLIPS = HERE / 'build' / 'clips'
GEO = json.loads((CLIPS / 'geom.json').read_text())
GAIT = json.loads((CLIPS / 'gait.json').read_text())
FPS = 24
H = M.DET_H
FOOT = M.FOOT
XF = 0.22
C, DL, DR = 540, 300, 780          # детектив: центр / левее (мошенница справа) / правее (мошенница слева)
SR, SL = 820, 260                  # где стоит мошенница
OFF = 470                          # откуда заходит мошенница (от своего места; за краем экрана)
RUN_V = 950                        # скорость убегания по экрану, px/с
NEW = {'listen', 'step'} | {f's{k}_{p}' for k in range(1, 6) for p in ('walkin', 'talk', 'run')}


def scale(name):
    g = GEO[name]
    return H / (g['bot'] - g['top'])


@functools.lru_cache(maxsize=160)
def frame(name, idx, flip):
    """Кадр клипа в масштабе H; якорь — центр стоп и подошвы ПЕРВОГО кадра (клипы стоят ровно, прыжки и шаги — живые).
    Края кадра клипа растушёваны (линии скорости, купюры не обрываются линией)."""
    g = GEO[name]
    im = Image.open(CLIPS / name / f'f{idx + 1:04d}.png')
    s = scale(name)
    a = np.array(im)
    h, w = a.shape[:2]
    e = 48
    ry = np.clip(np.minimum(np.arange(h), h - 1 - np.arange(h)) / e, 0, 1)
    rx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / e, 0, 1)
    ry[h - 60:] = 1                                       # низ (пол) не растушёвываем — там стопы
    a[..., 3] = (a[..., 3] * np.minimum(ry[:, None], rx[None, :])).astype(np.uint8)
    im = Image.fromarray(a).resize((round(w * s), round(h * s)), Image.BILINEAR)
    ax = g['hx'] * s
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        ax = im.width - ax
    return im, (ax, g['bot'] * s)


def nidx(name, local):
    return int(max(0, min(GEO[name]['n'] - 1, round(local * FPS))))


# ------------------------------------------------------------------ сегменты
def seg(name, pieces, flip=False, kind='new', hold=None):
    """pieces: [(t0, t1, l0, l1, x0, x1)]; hold=(a, b): после последнего куска — пинг-понг локального времени в [a, b]."""
    return dict(name=name, pieces=pieces, flip=flip, kind=kind, hold=hold, t0=pieces[0][0], t1=pieces[-1][1])


def state(sg, t):
    """(локальное время клипа, x) сегмента в момент t."""
    p = sg['pieces']
    for t0, t1, l0, l1, x0, x1 in p:
        if t0 <= t <= t1:
            u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return l0 + (l1 - l0) * u, x0 + (x1 - x0) * u
    t0, t1, l0, l1, x0, x1 = p[-1] if t > p[-1][1] else p[0]
    if t < p[0][0]:
        return l0, x0
    if sg['hold']:
        a, b = sg['hold']
        d = t - t1
        span = b - a
        q = d % (2 * span)
        loc = (a + q) if q < span else (b - (q - span))
        return loc, x1
    return l1, x1


def walk(t0, x0, x1, name='step', pre=(1.2, 1.5), w1=3.3, post=3.7, cyc=(1.92, 2.67), flip_for_right=True):
    """Детектив идёт x0→x1: поворот в профиль, шаги (цикл 1.92↔2.67 добавляет/убирает шаг), поворот к камере."""
    s = scale(name)
    vw = GAIT[name]['v'] * s
    dist = abs(x1 - x0)
    base = w1 - pre[1]
    per = cyc[1] - cyc[0]
    n = round((dist / vw - base) / per)
    n = max(-1, n)
    tw = base + n * per
    flip = (x1 > x0) and flip_for_right
    pieces = [(t0, t0 + pre[1] - pre[0], pre[0], pre[1], x0, x0)]
    t = pieces[-1][1]
    # шаги: куски локального времени
    legs = []
    if n < 0:
        legs = [(pre[1], cyc[0]), (cyc[1], w1)]
    else:
        legs = [(pre[1], cyc[1])] + [(cyc[0], cyc[1])] * (n - 1 if n > 0 else 0) + ([(cyc[0], w1)] if n > 0 else [(cyc[1], w1)])
        if n == 0:
            legs = [(pre[1], w1)]
    xa = x0
    for la, lb in legs:
        d = (lb - la) / tw * (x1 - x0)
        pieces.append((t, t + lb - la, la, lb, xa, xa + d))
        t += lb - la
        xa += d
    pieces.append((t, t + post - w1, w1, post, x1, x1))
    return seg(name, pieces, flip), pieces[-1][1]


def listen(t0, x, say_end, toward_left):
    """Повернулась к мошеннице, слушает (пинг-понг 2.0–6.2), после её фразы — поворот к камере (6.3→7.6)."""
    p1 = (t0, t0 + 2.0, 0.0, 2.0, x, x)
    span_end = max(t0 + 2.0, say_end + 0.05)
    # пинг-понг вручную, чтобы поворот назад начался из близкой позы
    pieces = [p1]
    t, loc, up = t0 + 2.0, 2.0, True
    while t < span_end - 1e-6:
        d = min(span_end - t, (6.2 - loc) if up else (loc - 2.0))
        nl = loc + d if up else loc - d
        pieces.append((t, t + d, loc, nl, x, x))
        t, loc = t + d, nl
        if loc >= 6.2 - 1e-6 or loc <= 2.0 + 1e-6:
            up = not up
    pieces.append((t, t + 0.25, loc, 6.3, x, x))
    pieces.append((t + 0.25, t + 0.25 + 1.3, 6.3, 7.6, x, x))
    return seg('listen', pieces, toward_left), pieces[-1][1]


def old(name, t0, t1, x, off=0.0, mode='once'):
    """Старые клипы детектива (говорит в камеру, лупа, штамп…) — через mita54 (якорь стоп в каждом кадре)."""
    return dict(name=name, kind='old', t0=t0, t1=t1, x=x, off=off, mode=mode)


# ------------------------------------------------------------------ мошенницы
WALKIN = {1: (4.2, 4.5), 2: (4.0, 4.6), 3: (4.2, 4.4), 4: (4.4, 5.5), 5: (4.0, 4.5)}     # (конец шагов, стоит)
RUN = {1: (0.7, 2.3), 2: (0.6, 2.5), 3: (1.0, 2.4), 4: (0.5, 3.2), 5: (0.8, 2.5)}         # (вздрогнула, побежала)
RUN_END = {1: 9.9, 2: 9.9, 3: 6.3, 4: 9.9, 5: 4.9}


def scammer(k, right, arrive, stamp):
    xs = SR if right else SL
    flip = not right
    out = 1 if right else -1                     # куда уходит за кадр
    segs = []
    # заход
    nm = f's{k}_walkin'
    wend, stand = WALKIN[k]
    vw = GAIT[nm]['v'] * scale(nm)
    tw = OFF / vw
    lw0 = max(0.65, wend - tw)
    tw = wend - lw0
    ta = arrive - (stand - wend)
    segs.append(seg(nm, [(ta - tw, ta, lw0, wend, xs + out * OFF, xs), (ta, arrive, wend, stand, xs, xs)], flip))
    # говорит
    nm = f's{k}_talk'
    t_run = stamp - RUN[k][0]
    segs.append(seg(nm, [(arrive, t_run, 0.0, t_run - arrive, xs, xs)], flip, hold=None))
    if t_run - arrive > 9.8:
        segs[-1] = seg(nm, [(arrive, arrive + 9.8, 0.0, 9.8, xs, xs)], flip, hold=(6.0, 9.8))
        segs[-1]['t1'] = t_run
    # разоблачение и побег
    nm = f's{k}_run'
    st, rs = RUN[k]
    t_go = t_run + rs
    tout = OFF / RUN_V
    segs.append(seg(nm, [(t_run, t_go, 0.0, rs, xs, xs),
                         (t_go, t_go + tout, rs, min(RUN_END[k], rs + tout), xs, xs + out * (OFF + 200))], flip))
    return segs


# ------------------------------------------------------------------ дорожки
def _det():
    D = []
    pre, post = M.STAMP_HIT - M.STAMP_A, M.STAMP_B - M.STAMP_HIT
    D.append(old('talk', E.LENS1, E.OFFER + 0.15, C, 0.0, 'pp'))
    # 1 оффер: справа
    w, t = walk(E.OFFER + 0.15, C, DL)
    D.append(w)
    lsn, t = listen(t, DL, E.OFFER_SAY_END, False)
    D.append(lsn)
    D.append(old('talk', t, E.LANG - 0.3, DL, 1.0, 'pp'))
    D.append(old('lens', E.LANG - 0.3, E.STAMP1 - pre, DL, 0.6))
    D.append(old('stamp', E.STAMP1 - pre, E.STAMP1 + 0.35, DL, M.STAMP_A))
    # 2 клон: слева → детектив переходит направо
    w, t = walk(E.STAMP1 + 0.35, DL, DR)          # сразу после удара штампа — уступает место «клону»
    D.append(w)
    lsn, t = listen(t, DR, E.CLONE_SAY_END, True)
    D.append(lsn)
    D.append(old('talk', t, E.ASK, DR, 2.0, 'pp'))
    D.append(old('phone', E.ASK, E.CREEPY, DR, 0.2))
    # жуть — отдельная сцена (render), потом крючок в центре
    D.append(old('talk', E.CREEPY_END, E.LINK + 0.1, C, 4.0, 'pp'))
    # 3 ссылка: справа
    w, t = walk(E.LINK + 0.1, C, DL)
    D.append(w)
    lsn, t = listen(t, DL, E.LINK_SAY_END, False)
    D.append(lsn)
    D.append(old('lens', t, E.STAMP3 - 1.1, DL, 0.6))
    D.append(old('shock', E.STAMP3 - 1.1, E.STAMP3 + 0.9, DL, 0.6))
    # 4 обмен: слева
    w, t = walk(E.STAMP3 + 0.9, DL, DR)
    D.append(w)
    lsn, t = listen(t, DR, E.SWAP_SAY_END, True)
    D.append(lsn)
    D.append(old('nono', t, E.STAMP4 + 0.9, DR, 0.4))
    # 5 гарант: справа
    w, t = walk(E.STAMP4 + 0.9, DR, DL)
    D.append(w)
    lsn, t = listen(t, DL, E.GUAR_SAY_END, False)
    D.append(lsn)
    D.append(old('stamp', t, E.STAMP5 + post, DL, M.STAMP_A - (E.STAMP5 - pre - t)))
    D.append(old('talk', E.STAMP5 + post, E.MEMO - 0.6, DL, 3.0, 'pp'))
    w, t = walk(E.MEMO - 0.6, DL, C)
    D.append(w)
    D.append(old('point', t, E.MOVE2, C, 0.3))
    D.append(dict(old('choice', E.MOVE2, DUR + 5, C, 0.0), hold=9.4))
    for a, b in zip(D, D[1:]):
        a['t1'] = b['t0']
    return D


DET = _det()
SCAM = [scammer(1, True, E.OFFER_SAY - 0.25, E.STAMP1), scammer(2, False, E.CLONE_SAY - 0.25, E.STAMP2),
        scammer(3, True, E.LINK_SAY - 0.25, E.STAMP3), scammer(4, False, E.SWAP_SAY - 0.25, E.STAMP4),
        scammer(5, True, E.GUAR_SAY - 0.25, E.STAMP5)]


def _draw_seg(cv, sg, t, put, a=1.0, shadow=None):
    if sg['kind'] == 'old':
        lt = t - sg['t0'] + sg['off']
        if sg.get('hold') and lt > sg['hold']:
            lt = sg['hold']
        im, anc = M.clip_img(sg['name'], M.idx_at(sg['name'], lt, sg['mode']))
        x = sg['x']
    else:
        loc, x = state(sg, t)
        im, anc = frame(sg['name'], nidx(sg['name'], loc), sg['flip'])
    if shadow and a > 0.5:
        shadow(cv, x, FOOT)
    put(cv, im, x, FOOT, 1.0, a, anchor=anc)
    return x


def _active(segs, t):
    for i, sg in enumerate(segs):
        if sg['t0'] <= t < sg['t1']:
            return i
    return None


def draw_track(cv, segs, t, put, shadow=None):
    i = _active(segs, t)
    if i is None:
        return None
    sg = segs[i]
    x = _draw_seg(cv, sg, t, put, 1.0, shadow)
    if i > 0 and t - sg['t0'] < XF and abs(segs[i - 1]['t1'] - sg['t0']) < 1e-3:
        u = (t - sg['t0']) / XF
        _draw_seg(cv, segs[i - 1], sg['t0'] - 1e-3, put, 1 - u * u * (3 - 2 * u))
    return x


def det_x(t):
    i = _active(DET, t)
    if i is None:
        return C
    sg = DET[i]
    return sg['x'] if sg['kind'] == 'old' else state(sg, t)[1]


def draw(cv, t, put, shadow=None):
    for segs in SCAM:
        draw_track(cv, segs, t, put, shadow)
    draw_track(cv, DET, t, put, shadow)
