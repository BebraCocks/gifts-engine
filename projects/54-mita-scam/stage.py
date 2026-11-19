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
C, DL = 540, 300                   # детектив: центр (финал) / левее центра (мошенница справа)
DR = DL + 428                      # правее центра: ровно длина её полного прохода (4 шага) — стопы не скользят
SR, SL = 820, 260                  # где стоит мошенница
OFF = 470                          # откуда заходит мошенница (от своего места; за краем экрана)
RUN_V = 950                        # скорость убегания по экрану, px/с
RUN_RATE = 1.6                     # испуг перед побегом проигрываем быстрее — убегает раньше
GONE_PAUSE = 0.05                  # детектив трогается сразу, как мошенница скрылась за кадром
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


def walk(t0, x0, x1, name='step', pre=(1.2, 1.5), w1=3.3, post=3.7):
    """Детектив идёт x0→x1: поворот в профиль, полный проход клипа без вырезок (DL↔DR = длина её шагов), поворот к камере."""
    flip = x1 > x0
    tw = w1 - pre[1]
    pieces = [(t0, t0 + pre[1] - pre[0], pre[0], pre[1], x0, x0)]
    t = pieces[-1][1]
    pieces.append((t, t + tw, pre[1], w1, x0, x1))
    t += tw
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
WALKIN = {1: (4.2, 4.5), 2: (4.0, 4.6), 3: (4.2, 4.4), 4: (4.4, 4.6), 5: (4.0, 4.5)}     # (конец шагов, стоит)
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
    # говорит (до побега; если дольше клипа — пинг-понг конца)
    st, rs = RUN[k]
    t_run = stamp - st / RUN_RATE
    nm = f's{k}_talk'
    if t_run - arrive <= 9.8:
        segs.append(seg(nm, [(arrive, t_run, 0.0, t_run - arrive, xs, xs)], flip))
    else:
        segs.append(seg(nm, [(arrive, arrive + 9.8, 0.0, 9.8, xs, xs)], flip, hold=(6.0, 9.8)))
        segs[-1]['t1'] = t_run
    # разоблачение (испуг быстрее, RUN_RATE) и побег за край экрана
    nm = f's{k}_run'
    t_go = t_run + rs / RUN_RATE
    tout = 1000 / RUN_V
    segs.append(seg(nm, [(t_run, t_go, 0.0, rs, xs, xs),
                         (t_go, t_go + tout, rs, min(RUN_END[k], rs + tout), xs, xs + out * 1000)], flip))
    return segs


def _det():
    D = []
    pre, post = M.STAMP_HIT - M.STAMP_A, M.STAMP_B - M.STAMP_HIT
    # хук → 1 оффер: детектив всё время левее центра, мошенница заходит справа
    D.append(old('hook', 0.0, E.LENS0, DL, 0.0, 'pp'))                    # обычная Мита до лупы (лупа — в render)
    D.append(dict(old('talk', E.LENS1, E.OFFER_SAY - 0.3, DL, 0.0, 'pp'), nojoin=True))
    lsn, t = listen(E.OFFER_SAY - 0.3, DL, E.OFFER_SAY_END, False)
    D.append(lsn)
    D.append(old('talk', t, E.LANG - 0.3, DL, 1.0, 'pp'))
    D.append(old('lens', E.LANG - 0.3, E.STAMP1 - pre, DL, 0.6))
    D.append(old('stamp', E.STAMP1 - pre, E.STAMP1 + post, DL, M.STAMP_A))
    D.append(old('talk', E.STAMP1 + post, gone(1) + GONE_PAUSE, DL, 2.0, 'pp'))
    # 2 клон: слева → детектив переходит направо
    w, t = walk(gone(1) + GONE_PAUSE, DL, DR)
    D.append(w)
    lsn, t = listen(max(t, E.CLONE_SAY - 0.3), DR, E.CLONE_SAY_END, True)
    D.append(lsn)
    D.append(old('talk', t, E.ASK, DR, 2.0, 'pp'))
    D.append(old('phone', E.ASK, E.CREEPY, DR, 0.2))
    # жуть — отдельная сцена (render); после неё детектив снова левее центра (крючок, реклама)
    D.append(dict(old('talk', E.CREEPY_END - 0.3, E.LINK_SAY - 0.3, DL, 4.0, 'pp'), nojoin=True))
    # 3 ссылка: справа
    lsn, t = listen(E.LINK_SAY - 0.3, DL, E.LINK_SAY_END, False)
    D.append(lsn)
    if E.STAMP3 - 1.1 - t > 0.8:
        D.append(old('lens', t, E.STAMP3 - 1.1, DL, 0.6))
    D.append(old('shock', min(t, E.STAMP3 - 1.1) if E.STAMP3 - 1.1 - t <= 0.8 else E.STAMP3 - 1.1, E.STAMP3 + 0.9, DL, 0.6))
    D.append(old('talk', E.STAMP3 + 0.9, gone(3) + GONE_PAUSE, DL, 1.0, 'pp'))
    # 4 обмен: слева
    w, t = walk(gone(3) + GONE_PAUSE, DL, DR)
    D.append(w)
    lsn, t = listen(max(t, E.SWAP_SAY - 0.3), DR, E.SWAP_SAY_END, True)
    D.append(lsn)
    D.append(old('nono', t, gone(4) + GONE_PAUSE, DR, 0.4))
    # 5 гарант: справа
    w, t = walk(gone(4) + GONE_PAUSE, DR, DL)
    D.append(w)
    lsn, t = listen(max(t, E.GUAR_SAY - 0.3), DL, E.GUAR_SAY_END, False)
    D.append(lsn)
    D.append(old('stamp', t, E.STAMP5 + post, DL, M.STAMP_A - (E.STAMP5 - pre - t)))
    D.append(old('talk', E.STAMP5 + post, E.MEMO, DL, 3.0, 'pp'))
    # памятка — там же; финал — в центр (растворяется → проявляется, облачко «пуф»)
    D.append(old('point', E.MEMO, E.MOVE2, DL, 0.3))
    D.append(dict(old('choice', E.MOVE2, DUR + 5, C, 0.0), hold=9.4, xf=0.45))
    for a, b in zip(D, D[1:]):
        if not b.get('nojoin'):
            a['t1'] = b['t0']
    return D


# ------------------------------------------------------------------ дорожки
def gone(k):
    """Когда мошенница k скрылась за краем экрана."""
    rn = SCAM[k - 1][2]
    t_go = rn['pieces'][1][0]
    return t_go + 440 / RUN_V


SCAM = [scammer(1, True, E.OFFER_SAY - 0.25, E.STAMP1), scammer(2, False, E.CLONE_SAY - 0.25, E.STAMP2),
        scammer(3, True, E.LINK_SAY - 0.25, E.STAMP3), scammer(4, False, E.SWAP_SAY - 0.25, E.STAMP4),
        scammer(5, True, E.GUAR_SAY - 0.25, E.STAMP5)]
DET = _det()


def _img(sg, t):
    if sg['kind'] == 'old':
        lt = t - sg['t0'] + sg['off']
        if sg.get('hold') and lt > sg['hold']:
            lt = sg['hold']
        im, anc = M.clip_img(sg['name'], M.idx_at(sg['name'], lt, sg['mode']))
        return im, anc, sg['x']
    loc, x = state(sg, t)
    im, anc = frame(sg['name'], nidx(sg['name'], loc), sg['flip'])
    return im, anc, x


def _body_x(im, anc, x):
    """Центр корпуса на экране (ряды плеч–пояса): по нему сводим стыки клипов."""
    a = np.array(im.getchannel('A'))
    h = a.shape[0]
    band = a[int(h * 0.30):int(h * 0.50)] > 128
    cols = np.nonzero(band.any(0))[0]
    return x - anc[0] + (cols.min() + cols.max()) / 2 if len(cols) else x


@functools.lru_cache(maxsize=64)
def _seam(key, i):
    segs = TRACKS[key]
    a, b = segs[i - 1], segs[i]
    pa = _body_x(*_img(a, b['t0'] - 1e-3))
    pb = _body_x(*_img(b, b['t0']))
    return pa - pb


SEAM_T = 0.35


def _draw_seg(cv, sg, t, put, a=1.0, shadow=None, dx=0.0):
    im, anc, x = _img(sg, t)
    x += dx
    if shadow and a > 0.5:
        shadow(cv, x, FOOT)
    put(cv, im, x, FOOT, 1.0, a, anchor=anc)
    return x


def _active(segs, t):
    for i, sg in enumerate(segs):
        if sg['t0'] <= t < sg['t1']:
            return i
    return None


def draw_track(cv, key, t, put, shadow=None):
    segs = TRACKS[key]
    i = _active(segs, t)
    if i is None:
        return None
    sg = segs[i]
    joined = i > 0 and abs(segs[i - 1]['t1'] - sg['t0']) < 1e-3 and not sg.get('nojoin')
    xf = sg.get('xf')
    if joined and xf and t - sg['t0'] < 2 * xf:            # перестановка: там растворяется — тут проявляется
        u = (t - sg['t0']) / xf
        if u < 1:
            _draw_seg(cv, segs[i - 1], sg['t0'] - 1e-3, put, 1 - u * u * (3 - 2 * u), shadow)
        else:
            _draw_seg(cv, sg, t, put, (u - 1) * (u - 1) * (3 - 2 * (u - 1)) if u < 2 else 1.0, shadow)
        return sg.get('x')
    dx = 0.0
    if joined and t - sg['t0'] < SEAM_T:                   # стык клипов: плавно гасим смещение корпуса
        u = (t - sg['t0']) / SEAM_T
        dx = _seam(key, i) * (1 - u * u * (3 - 2 * u))
    x = _draw_seg(cv, sg, t, put, 1.0, shadow, dx)
    if joined and t - sg['t0'] < XF:
        u = (t - sg['t0']) / XF
        _draw_seg(cv, segs[i - 1], sg['t0'] - 1e-3, put, 1 - u * u * (3 - 2 * u))
    return x


def det_x(t):
    i = _active(DET, t)
    if i is None:
        return C
    sg = DET[i]
    return sg['x'] if sg['kind'] == 'old' else state(sg, t)[1]


TRACKS = {'det': DET, **{f's{k}': SCAM[k - 1] for k in range(1, 6)}}


def draw(cv, t, put, shadow=None):
    for k in range(1, 6):
        draw_track(cv, f's{k}', t, put, shadow)
    draw_track(cv, 'det', t, put, shadow)
