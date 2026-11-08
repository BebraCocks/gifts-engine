"""41-price-duel-17 «Шлем или самокат» — код 09–12/31/38/40 («весы на бумаге»).
09-price-duel: «весы на бумаге». Тёплая бумага с точечной сеткой, чернильные линии, один томатный акцент.
Слева на весах — NFT-подарок (Lottie, полный цикл), справа — вещь из жизни (плоский рисунок кодом).
Ось весов — таймер на 5 с. На ответе весы падают в сторону дорогой вещи, выпадают ценники и штамп «ДОРОЖЕ».
Content time t -> RGB frame; RubUp via banner.Breaks (same in audio.py)."""
import functools
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw
import banner
import captions
import frames
import fx
import gifts_api
import lottie
import config
from script import (LINES, ROUNDS, TON_RUB, TIMER, HOOK, HOOK_SIZES, HOOK_BADGE, HOOK_NAMES, TEASER, SIDES, OUTRO_1, OUTRO_2, ACC,
                    OUTRO_TAG, COMMENTS)
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, SWAP
from words import WORDS
from events import AD_STOP, E, WIN
import photos as things          # real photos as stickers (author, 2026-11-06); things.py = drawn v1

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2)

BG, GRID, INK, MUTED, LIGHT, ACC = (config.BACKGROUND, config.GRID, config.INK, config.MUTED, config.LIGHT,
                                     config.ACCENT)
PAPER = BG
GIFTS = [str(gifts_api.model_file(g, m, 'json')) for g, m, *_ in ROUNDS]
GS = 512                       # Lottie raster size
GIFT_SC = 0.66                 # -> ≈ 348 px on screen
THING_SC = 1.0

PIV = (540.0, 590.0)           # pivot of the scale = the timer
L = 300.0                      # half beam
ROPE = 382.0                   # beam end -> plate
PLATE_W = 330.0
POST_Y = 1292.0
ITEM_UP = 162.0                # item centre above the plate
SRC = [r[7] for r in ROUNDS]


# ------------------------------------------------------------------ helpers
def cl(x):
    return min(1.0, max(0.0, x))


def sm(a, b, t):
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, k):
    return a + (b - a) * k


def spr(t0, t, f=2.0, z=0.55):
    return fx.spring(t - t0, f, z) if t > t0 else 0.0


@functools.lru_cache(None)
def _bg():
    """Flat paper + a static dot grid (no gradients: they band in 8-bit video)."""
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    step = 54
    for y in range(step // 2, H, step):
        for x in range(step // 2 + 9, W, step):
            d.ellipse([x - 2.2, y - 2.2, x + 2.2, y + 2.2], fill=GRID)
    return np.asarray(im, np.float32).copy()


@functools.lru_cache(4096)
def label(s, size, weight, color):
    f = fx.font(weight, size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    pad = 6
    im = Image.new('RGBA', (int(r - l) + 2 * pad, int(b - t) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=f, fill=color + (255,), anchor='ls')
    return im


def text(c, s, size, weight, color, cx, cy, a=1.0, sc=1.0, rot=0.0):
    if a <= 0.004 or sc <= 0.01:
        return
    fx.over(c, fx.warp(label(s, size, weight, color), cx, cy, sc, sc, rot), a)


def put(c, im, cx, cy, sc=1.0, a=1.0, rot=0.0):
    if a > 0.004 and sc > 0.01:
        fx.over(c, fx.warp(im, cx, cy, sc, sc, rot), a)


def _box(pts, pad):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(0, min(xs) - pad), max(0, min(ys) - pad), min(W, max(xs) + pad), min(H, max(ys) + pad))


def line(c, pts, color, width=6.0, a=1.0):
    if a <= 0.004:
        return

    def draw(d, m, S):
        q = [m(x, y) for x, y in pts]
        r = width * S / 2
        d.line(q, fill=color + (255,), width=max(1, round(width * S)), joint='curve')
        for x, y in (q[0], q[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))
    fx.over(c, fx.draw_rgba(_box(pts, width * 2 + 4), draw), a)


def disc(c, cx, cy, r, color, a=1.0):
    if a > 0.004 and r > 0.5:
        fx.over(c, fx.draw_rgba((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2),
                                lambda d, m, S: d.ellipse([*m(cx - r, cy - r), *m(cx + r, cy + r)],
                                                          fill=color + (255,))), a)


def arc(c, cx, cy, r, a0, a1, color, width, a=1.0):
    if a <= 0.004 or a1 - a0 < 0.5:
        return
    fx.over(c, fx.draw_rgba((cx - r - width, cy - r - width, cx + r + width, cy + r + width),
                            lambda d, m, S: d.arc([*m(cx - r, cy - r), *m(cx + r, cy + r)], a0, a1,
                                                  fill=color + (255,), width=round(width * S))), a)


@functools.lru_cache(256)
def pill(s, size, fill_, tcol, outline=None, padx=30, h=None):
    f = fx.font('Heavy', size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    w = int(r - l) + 2 * padx
    hh = h or int(size * 1.75)
    S = 2
    im = Image.new('RGBA', (w * S, hh * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w * S - 3, hh * S - 3], hh * S // 2, fill=None if fill_ is None else fill_ + (255,),
                        outline=None if outline is None else outline + (255,), width=0 if outline is None else 5 * S)
    d.text((w * S / 2, hh * S / 2), s, font=fx.font('Heavy', size * S), fill=tcol + (255,), anchor='mm')
    return im.resize((w, hh), Image.LANCZOS)


@functools.lru_cache(None)
def stamp():
    """«ДОРОЖЕ» rubber stamp: tomato outline + text."""
    S = 2
    f = fx.font('Heavy', 46 * S)
    l, t, r, b = f.getbbox('ДОРОЖЕ', anchor='ls')
    w, h = int(r - l) + 56 * S, 92 * S
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4 * S, 4 * S, w - 4 * S, h - 4 * S], 14 * S, outline=ACC + (255,), width=6 * S)
    d.text((w / 2, h / 2 + 2 * S), 'ДОРОЖЕ', font=f, fill=ACC + (255,), anchor='mm')
    return im.resize((w // S, h // S), Image.LANCZOS)


def rub(v):
    s = f'{int(round(v)):,}'.replace(',', ' ')
    return s + ' ₽'


def gift_rub(r):
    v = ROUNDS[r][5] * TON_RUB
    return v if v < 1000 else round(v / 100) * 100


# ------------------------------------------------------------------ the scale
def active_round(t):
    r = 0
    for k, t0 in enumerate(ROUND_IN):
        if t >= t0 - SWAP:
            r = k
    return r


def beam_angle(t):
    """Degrees, positive = right side down. Wobbles while undecided, falls to the dearer side on the answer."""
    if t < ROUND_IN[0]:                                         # hook: a nervous swing
        ang = 9.0 * math.sin(t * 5.2) * (0.4 + 0.6 * sm(0.0, 0.6, t))
        return ang
    r = active_round(t)
    ang = 0.0
    land = ROUND_IN[r] + 0.18
    ang += 3.5 * fx.bump(t - land, 2.6, 4.5) * (1 if r % 2 else -1)       # items land: a small jolt
    if TIMER0[r] <= t < REVEAL[r]:
        ang += 2.2 * math.sin((t - TIMER0[r]) * 2 * math.pi * 0.62) * sm(TIMER0[r], TIMER0[r] + 0.8, t)
    side = 1 if WIN[r] else -1
    k = spr(REVEAL[r], t, 1.7, 0.42)
    ang += side * 11.0 * k
    if r + 1 < len(ROUND_IN):                                   # back to level before the next round
        ang *= 1 - sm(ROUND_IN[r + 1] - SWAP, ROUND_IN[r + 1] - SWAP + 0.4, t)
    if t > OUTRO:                                               # outro: undecided again, «Пепе или Гранту?»
        ang *= 1 - sm(OUTRO, OUTRO + 0.6, t)
        ang += 5.0 * math.sin((t - OUTRO) * 2.4) * sm(OUTRO + 0.3, OUTRO + 1.2, t)
    return ang


def geometry(t):
    th = math.radians(beam_angle(t))
    ex, ey = L * math.cos(th), L * math.sin(th)
    ends = ((PIV[0] - ex, PIV[1] - ey), (PIV[0] + ex, PIV[1] + ey))
    plates = [(x, y + ROPE) for x, y in ends]
    return ends, plates


def draw_scale(c, t, ends, plates):
    a = 1.0
    line(c, [(PIV[0], PIV[1]), (PIV[0], POST_Y)], INK, 9, a)                         # post
    fx.over(c, fx.draw_rgba((PIV[0] - 120, POST_Y - 6, PIV[0] + 120, POST_Y + 22), lambda d, m, S:
            d.rounded_rectangle([*m(PIV[0] - 110, POST_Y - 2), *m(PIV[0] + 110, POST_Y + 16)], 9 * S,
                                fill=INK + (255,))), a)
    for (x, y), (px, py) in zip(ends, plates):
        line(c, [(x, y), (px - PLATE_W / 2 + 18, py)], INK, 3, a)                    # ropes
        line(c, [(x, y), (px + PLATE_W / 2 - 18, py)], INK, 3, a)
    line(c, [ends[0], ends[1]], INK, 11, a)                                          # beam
    for x, y in ends:
        disc(c, x, y, 9, INK, a)
    for px, py in plates:                                                            # shallow bowls
        x0, x1 = px - PLATE_W / 2, px + PLATE_W / 2
        fx.over(c, fx.draw_rgba((x0 - 8, py - 8, x1 + 8, py + 34), lambda d, m, S, x0=x0, x1=x1, py=py: (
            d.chord([*m(x0, py - 26), *m(x1, py + 26)], 0, 180, fill=LIGHT + (255,), outline=INK + (255,),
                    width=round(5 * S)))), a)


def draw_timer(c, t):
    """The pivot: a plain hub, or the 5 s timer ring with the digit."""
    r = active_round(t) if t >= ROUND_IN[0] else -1
    ton = 0.0
    if r >= 0 and t < OUTRO:
        ton = sm(TIMER0[r] - 0.05, TIMER0[r] + 0.25, t) * (1 - sm(REVEAL[r], REVEAL[r] + 0.3, t))
    rad = lerp(16, 66, ton)
    disc(c, PIV[0], PIV[1], rad + 5, INK)
    disc(c, PIV[0], PIV[1], rad, PAPER if ton > 0.02 else INK)
    if ton <= 0.02:
        return
    left = cl((REVEAL[r] - t) / TIMER)
    arc(c, PIV[0], PIV[1], rad - 9, -90, 270, LIGHT, 10, ton)
    arc(c, PIV[0], PIV[1], rad - 9, -90 + 360 * (1 - left), 270, ACC, 10, ton)
    n = max(1, math.ceil((REVEAL[r] - t) - 1e-6))
    tick = REVEAL[r] - n                                            # moment this digit appeared
    k = 1 + 0.22 * fx.bump(t - tick, 3.0, 7.0) if t >= tick else 1.0
    text(c, str(min(5, n)), 54, 'Heavy', ACC if n <= 2 else INK, PIV[0], PIV[1], ton, k * lerp(0.6, 1.0, ton))


# ------------------------------------------------------------------ items, labels, prices
def item_motion(t, r, side):
    """(dx, dy, scale, alpha, rot) of round r's item on its plate: drops in from above while the previous pair
    slides out sideways (they overlap, the pans are never empty)."""
    t_in = ROUND_IN[r] - (SWAP - 0.1 if r else 0.25) + 0.06 * side     # v2: round 1 overlaps the hook pair leaving
    k = spr(t_in, t, 2.1, 0.55)
    dx, dy, sc, a, rot = 0.0, lerp(-600, 0, k), 1.0, float(t >= t_in), 0.0
    if r + 1 < len(ROUND_IN):
        t_out = ROUND_IN[r + 1] - SWAP + 0.04 * side
        o = sm(t_out, t_out + 0.45, t)
        dx += (760 if side else -760) * o * o
        dy -= 140 * o
        rot += (0.45 if side else -0.45) * o
        a *= 1 - sm(t_out + 0.32, t_out + 0.45, t)
    return dx, dy, sc, a, rot


def draw_items(c, t, plates):
    if t < ROUND_IN[0]:                                            # hook v2: the final pair from frame 0, prices hidden
        j = 4
        k = spr(-0.3, t, 2.4, 0.6)
        o = sm(ROUND_IN[0] - 0.4, ROUND_IN[0], t)                  # the pair flies off, round 1 drops in
        for side in (0, 1):
            px, py = plates[side]
            dx = (760 if side else -760) * o * o
            if side == 0:
                put(c, lottie.frame(GIFTS[j], t, size=GS), px + dx, py - ITEM_UP, GIFT_SC * 0.92 * k, 1 - o)
            else:
                put(c, things.sprite(ROUNDS[j][3]), px + dx, py - ITEM_UP, THING_SC * 0.92 * k, 1 - o)
            kp = spr(0.25 + 0.1 * side, t, 2.4, 0.5) * (1 + 0.08 * math.sin(t * 7.0 + side))
            put(c, pill('? ₽', 52, None, INK, INK), px + dx, py + 120, max(0.01, kp), (1 - o) * cl(kp * 2))
            text(c, HOOK_NAMES[side], 38, 'Heavy', INK, px + dx, py + 54, (1 - o) * cl(k))
        return
    r = active_round(t)
    for rr in {max(0, r - 1), r}:
        for side in (0, 1):
            dx, dy, sc, a, rot = item_motion(t, rr, side)
            if a <= 0.004:
                continue
            px, py = plates[side]
            if side == 0:
                put(c, lottie.frame(GIFTS[rr], t + 0.37 * rr, size=GS), px + dx, py - ITEM_UP + dy, GIFT_SC * sc, a,
                    rot)
            else:
                put(c, things.sprite(ROUNDS[rr][3]), px + dx, py - ITEM_UP + dy, THING_SC * sc, a, rot)


def draw_labels(c, t, plates):
    if t < ROUND_IN[0]:
        return
    r = active_round(t)
    gift, model, rar, kind, (n1, n2), ton, price = ROUNDS[r][:7]
    t_in = ROUND_IN[r] + 0.15
    a_in = sm(t_in, t_in + 0.3, t)
    a_out = 1.0 if r + 1 >= len(ROUND_IN) else 1 - sm(ROUND_IN[r + 1] - SWAP, ROUND_IN[r + 1] - SWAP + 0.25, t)
    if t > OUTRO:
        a_out *= 1 - sm(OUTRO, OUTRO + 0.3, t) * 0       # names stay in the outro, prices go
    a = a_in * a_out
    rows = ((gift, f'модель {model}'), (n1, n2))
    for side in (0, 1):
        px, py = plates[side]
        rise = 18 * (1 - a_in)
        for txt, size, wt, col, dy in ((rows[side][0], 44, 'Heavy', INK, 70), (rows[side][1], 31, 'Semibold', MUTED, 117)):
            fit = min(1.0, 400 / max(1, label(txt, size, wt, col).width))      # long names shrink to stay in frame
            text(c, txt, size, wt, col, px, py + dy + rise, a, fit)
    # prices on the answer
    k = sm(REVEAL[r] - 0.02, REVEAL[r] + 0.22, t)
    if k <= 0:
        return
    pa = a_out * (1 - sm(OUTRO, OUTRO + 0.35, t))
    vals = (gift_rub(r), price)
    for side in (0, 1):
        px, py = plates[side]
        win = WIN[r] == side
        s = ('≈ ' if side == 0 else '') + rub(vals[side])
        im = pill(s, 46, ACC if win else None, (255, 255, 255) if win else INK, None if win else INK)
        kk = spr(REVEAL[r] + 0.06 * side, t, 2.6, 0.5)
        put(c, im, px, py + 200 - 30 * (1 - kk), max(0.01, kk), pa)
        sub = 'в телеге' if side == 0 else SRC[r]           # no «TON» on screen (crypto wording, 2026-11-08)
        text(c, sub, 29, 'Semibold', MUTED, px, py + 266, pa * k)
        if win:                                                   # the stamp lands on the dearer one
            ks = spr(REVEAL[r] + 0.12, t, 2.2, 0.45)
            put(c, stamp(), px + (16 if side else -16), py - ITEM_UP - 150, lerp(2.4, 1.18, cl(ks)), pa * cl(ks * 3),
                -0.16 if side == 0 else 0.14)


# ------------------------------------------------------------------ titles, score, hook, outro
def score_at(t):
    s = [0, 0]
    for r in range(5):
        if t >= REVEAL[r] + 0.15:
            s[WIN[r]] += 1
    return s


def draw_header(c, t):
    a = sm(E['hook_q'] + 0.08, E['hook_q'] + 0.4, t)            # after the hook text has gone (v2)
    if a <= 0.004:
        return
    s = score_at(t)
    # score: ПОДАРОК 0 : 0 ЖИЗНЬ
    y = 196
    text(c, SIDES[0], 32, 'Heavy', MUTED, 318, y, a)
    text(c, SIDES[1], 32, 'Heavy', MUTED, 778, y, a)
    for side, x in ((0, 476), (1, 604)):
        last = max([REVEAL[r] + 0.15 for r in range(5) if WIN[r] == side and t >= REVEAL[r] + 0.15] or [-9])
        k = 1 + 0.45 * fx.bump(t - last, 3.0, 6.5) if last > 0 else 1.0
        text(c, str(s[side]), 62, 'Heavy', ACC if last > 0 and t - last < 0.6 else INK, x, y, a, k)
    text(c, ':', 56, 'Heavy', INK, 540, y - 3, a)
    # round label + title
    if t < OUTRO:
        r = max([k for k in range(5) if t >= ROUND_IN[k] - 0.1] or [0])
        rl = 'ФИНАЛ' if r == 4 else f'РАУНД {r + 1} / 5'
        text(c, rl, 31, 'Semibold', ACC if r == 4 else MUTED, 540, 290, a)
        text(c, 'ЧТО ДОРОЖЕ?', 84, 'Heavy', INK, 540, 386, a)
    else:
        ko = sm(OUTRO, OUTRO + 0.3, t)
        k2 = sm(E['which'] - 0.15, E['which'] + 0.15, t)
        text(c, OUTRO_TAG, 31, 'Semibold', ACC, 540, 290, ko * k2)
        text(c, OUTRO_1, 78, 'Heavy', INK, 540, 386 - 20 * k2, ko * (1 - k2))
        text(c, OUTRO_2, 78, 'Heavy', INK, 540, 386 + 20 * (1 - k2), k2)


def draw_hook(c, t):
    a = 1 - sm(E['hook_q'] - 0.15, E['hook_q'] + 0.1, t)
    if a <= 0.004:
        return
    k1 = 0.8 + 0.2 * spr(-0.05, t, 2.2, 0.5)         # the whole bet is readable from the first frame
    k2 = 0.75 + 0.25 * spr(0.08, t, 2.2, 0.5)
    k3 = 1 + 0.12 * fx.bump(t - 0.55, 3.0, 6.0)
    fit = [min(1.0, 980 / label(s, z, 'Heavy', INK).width) for s, z in zip(HOOK, HOOK_SIZES)]   # long lines stay in frame
    text(c, HOOK[0], HOOK_SIZES[0], 'Heavy', INK, 540, 200 + 30 * (1 - k1), a, k1 * fit[0])
    text(c, HOOK[1], HOOK_SIZES[1], 'Heavy', ACC, 540, 288 + 30 * (1 - k1), a, k1 * fit[1])
    text(c, HOOK[2], HOOK_SIZES[2], 'Heavy', INK, 540, 376 + 30 * (1 - k2), a, k2 * fit[2])
    put(c, pill(HOOK_BADGE, 38, ACC, (255, 255, 255)), 540, 478 + 30 * (1 - k2), k2 * k3, a)


def draw_teaser(c, t):
    """Retention before RubUp: the promised final is still ahead (the ad freeze frame shows this pill)."""
    t0 = END[KEY['a3']] - 0.15
    if not (t0 <= t < ROUND_IN[3] - SWAP):
        return
    k = spr(t0, t, 2.4, 0.5)
    a = cl(k * 2) * (1 - sm(max(AD_STOP + 0.02, ROUND_IN[3] - SWAP - 0.3), ROUND_IN[3] - SWAP, t))   # full on the ad freeze
    put(c, pill(TEASER, 40, ACC, (255, 255, 255)), 540, 1338, max(0.01, k) * (1 + 0.05 * fx.bump(t - t0 - 0.5, 3.0, 6.0)), a)


def draw_outro(c, t):
    k = spr(E['comments'], t, 2.0, 0.5)
    if t < E['comments']:
        return
    put(c, pill(COMMENTS, 40, ACC, (255, 255, 255)), 540, 1338, max(0.01, k), cl(k * 2))


# ------------------------------------------------------------------ captions
def _phr(k):
    acc = ACC
    return captions.phrase(WORDS[k], accent=acc, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=900, top=1400, size=52, weight='Semibold',
                        max_lines=2, color=INK, accent_color=ACC, shadow=False, fade_out=0.2, rise=10)


def render_at(t):
    c = _bg().copy()
    ends, plates = geometry(t)
    draw_scale(c, t, ends, plates)
    draw_items(c, t, plates)
    draw_timer(c, t)
    draw_labels(c, t, plates)
    draw_header(c, t)
    draw_hook(c, t)
    draw_teaser(c, t)
    draw_outro(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
