"""39-lucky-cells «Проверь свою чуйку» (v6: коробки, только баллы, финал 5 + 5, золотая коробка с бомбой) — бумага серии «Что дороже?» (точечная сетка, чернила), шесть ячеек.
Сверху три синие ячейки (подарки из телеги, Lottie полным циклом), снизу три красные (настоящие фото вещей).
Таймер 5 с над ячейками; на ответе ячейки переворачиваются по очереди, у каждой — цена и баллы 100 / 300 / 500.
Финал: таблица из пяти уровней. Content time t -> RGB frame; RubUp via banner.Breaks (same in audio.py)."""
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
from script import (LINES, ROUNDS, TON_RUB, TIMER, HOOK, HOOK_BADGE, TITLE, TAGS, TEASER, LEVELS, SUM_TITLE, COMMENTS,
                    ACC)
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, SWAP, HOLD
from words import WORDS
from events import AD_STOP, E
import photos

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2)

BG, GRID, INK, MUTED, LIGHT, GOLD = (config.BACKGROUND, config.GRID, config.INK, config.MUTED, config.LIGHT,
                                     config.ACCENT)
BLUE, RED = config.BLUE, config.RED
WHITE = (255, 255, 255)
ROWCOL = (BLUE, RED)
GIFTS = [[str(gifts_api.model_file(g, m, 'json')) for g, m, _ in r['blue']] for r in ROUNDS]

CW, CH, GAP = 312, 352, 22
XS = [W / 2 + (k - 1) * (CW + GAP) for k in range(3)]
YS = [708, 1150]                 # blue row, red row (centres)
TAG_Y = (502, 942)
TIMER_Y = 400
CAP_TOP = 1398
PILL_Y = 1590
GIFT_PX = 196                    # Lottie raster on the open card
FLIP = 0.30                      # one card flip, s
STEP = 0.075                     # delay between cards in the reveal cascade


# ------------------------------------------------------------------ helpers
def cl(x):
    return min(1.0, max(0.0, x))


def sm(a, b, t):
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, k):
    return a + (b - a) * k


def spr(t0, t, f=2.0, z=0.55):
    return fx.spring(t - t0, f, z) if t > t0 else 0.0


def mix(c1, c2, k):
    return tuple(int(round(lerp(a, b, k))) for a, b in zip(c1, c2))


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


def text(c, s, size, weight, color, cx, cy, a=1.0, sc=1.0, rot=0.0, maxw=None):
    if a <= 0.004 or sc <= 0.01:
        return
    im = label(s, size, weight, color)
    if maxw:
        sc *= min(1.0, maxw / im.width)
    fx.over(c, fx.warp(im, cx, cy, sc, sc, rot), a)


def put(c, im, cx, cy, sx=1.0, a=1.0, rot=0.0, sy=None):
    sy = sx if sy is None else sy
    if a > 0.004 and sx > 0.01 and sy > 0.01:
        fx.over(c, fx.warp(im, cx, cy, sx, sy, rot), a)


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


# ------------------------------------------------------------------ boxes (v6: boxes with «?», points only, final 5 + 5)
def layout(r):
    """(n per row, cell w, cell h, xs, row ys, tag ys) of round r."""
    if len(ROUNDS[r]['blue']) == 5:
        w, h, gap = 188, 236, 10
        xs = [W / 2 + (k - 2) * (w + gap) for k in range(5)]
        return 5, w, h, xs, (668, 962), (522, 816)
    return 3, CW, CH, XS, YS, TAG_Y


GOLD_C = (232, 168, 20)
GOLD_XY = (W / 2, 1218)
GOLD_SZ = 150


@functools.lru_cache(None)
def box_body(col, w, h, n, mark='?'):
    """A closed gift box without its lid: coloured body, a lighter ribbon, a big «?» and the number."""
    S = 2
    lid = int(h * 0.24)
    W2, H2 = w * S, (h + 12) * S
    im = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = max(12, w // 9) * S
    d.rounded_rectangle([6 * S, (lid - 6) * S + 12 * S, W2 - 6 * S, H2 - 1], r, fill=mix(col, INK, 0.4) + (255,))
    d.rounded_rectangle([6 * S, (lid - 6) * S, W2 - 6 * S, h * S - 1], r, fill=col + (255,))
    rib = int(w * 0.13) * S
    d.rectangle([W2 // 2 - rib // 2, (lid - 6) * S, W2 // 2 + rib // 2, h * S - 2 * S], fill=mix(col, WHITE, 0.35) + (255,))
    qs = int(h * 0.42)
    cy = ((lid + h) / 2) * S
    f = fx.font('Heavy', qs * S)
    for dx, dy, c in ((3, 4, mix(col, INK, 0.45)), (0, 0, WHITE)):
        d.text((W2 / 2 + dx * S, cy + dy * S), mark, font=f, fill=c + (255,), anchor='mm')
    if n:
        br = int(w * 0.09) * S
        x0, y0 = 14 * S + br, (lid + 8) * S + br
        d.ellipse([x0 - br, y0 - br, x0 + br, y0 + br], fill=WHITE + (255,))
        d.text((x0, y0 + S), str(n), font=fx.font('Heavy', int(br * 1.25)), fill=col + (255,), anchor='mm')
    return im.resize((w, h + 12), Image.LANCZOS)


@functools.lru_cache(None)
def box_lid(col, w, h):
    S = 2
    lid = int(h * 0.24)
    W2, H2 = (w + 8) * S, (lid + 8) * S
    im = Image.new('RGBA', (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = max(10, w // 10) * S
    d.rounded_rectangle([0, 6 * S, W2 - 1, H2 - 1], r, fill=mix(col, INK, 0.4) + (255,))
    d.rounded_rectangle([0, 0, W2 - 1, H2 - 7 * S], r, fill=mix(col, WHITE, 0.12) + (255,))
    rib = int(w * 0.13) * S
    d.rectangle([W2 // 2 - rib // 2, 0, W2 // 2 + rib // 2, H2 - 7 * S], fill=mix(col, WHITE, 0.45) + (255,))
    bw = int(w * 0.16) * S                                                     # bow
    for sx in (-1, 1):
        d.ellipse([W2 // 2 + (0 if sx > 0 else -bw * 2), -bw // 2, W2 // 2 + (bw * 2 if sx > 0 else 0), bw // 2 + 4 * S],
                  outline=mix(col, WHITE, 0.45) + (255,), width=5 * S)
    return im.resize((w + 8, lid + 8), Image.LANCZOS)


def lid_offset(h):
    """Centre of the lid relative to the box centre."""
    lid = int(h * 0.24)
    return -(h + 12) / 2 + (lid + 8) / 2 - 2


@functools.lru_cache(None)
def open_card(r, row, k):
    """Open face without the Lottie: white card, coloured frame, gold rim for the best of the row, name (no price)."""
    n, w, h = layout(r)[:3]
    col = ROWCOL[row]
    rd = ROUNDS[r]
    pts = (rd['blue_pts'], rd['red_pts'])[row][k]
    best = pts == max((rd['blue_pts'], rd['red_pts'])[row])
    S = 2
    im = Image.new('RGBA', (w * S, (h + 12) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rr = max(14, w // 9) * S
    d.rounded_rectangle([0, 12 * S, w * S - 1, (h + 12) * S - 1], rr, fill=mix(col, INK, 0.38) + (255,))
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], rr, fill=col + (255,))
    d.rounded_rectangle([8 * S, 8 * S, w * S - 8 * S, h * S - 8 * S], rr - 6 * S, fill=WHITE + (255,),
                        outline=GOLD + (255,) if best else None, width=7 * S if best else 0)
    im = im.resize((w, h + 12), Image.LANCZOS)
    if row == 1:
        ph = photos.sprite(rd['red'][k][0])
        box = (0.66 * w, 0.56 * h)
        sc = min(box[0] / ph.width, box[1] / ph.height)
        ph = ph.resize((round(ph.width * sc), round(ph.height * sc)), Image.LANCZOS)
        im.alpha_composite(ph, (w // 2 - ph.width // 2, int(0.37 * h) - ph.height // 2))
    name = rd['blue'][k][0] if row == 0 else rd['red'][k][1]
    lb = label(name, 33 if n == 3 else 24, 'Heavy', INK)
    if lb.width > w - 26:
        lb = lb.resize((w - 26, round(lb.height * (w - 26) / lb.width)), Image.LANCZOS)
    im.alpha_composite(lb, (w // 2 - lb.width // 2, int(0.78 * h) - lb.height // 2))
    return im


def points_pill(pts, small=False):
    size = 30 if small else 40
    if pts >= 5000:
        return pill(f'★ {pts}', size, GOLD, WHITE, padx=20 if small else 26)
    return pill(str(pts), size - 2, WHITE, INK, INK, padx=20 if small else 30)


def card_face(r, row, k, t):
    im = open_card(r, row, k)
    if row == 0:
        n, w, h = layout(r)[:3]
        im = im.copy()
        g = lottie.frame(GIFTS[r][k], t + 0.31 * k + 0.17 * r, size=int(GIFT_PX if n == 3 else 0.66 * w))
        im.alpha_composite(g, (w // 2 - g.width // 2, int(0.38 * h) - g.height // 2))
    return im


def step(r):
    return STEP if layout(r)[0] == 3 else 0.05


def flip_t(r, row, k):
    n = layout(r)[0]
    return REVEAL[r] + step(r) * (n * row + k)


def round_at(t):
    r = 0
    for k, t0 in enumerate(ROUND_IN):
        if t >= t0 - SWAP:
            r = k
    return r


def leave_t(r):
    """Open cards of round r start flying out (next round or the outro)."""
    return ROUND_IN[r + 1] - SWAP if r + 1 < len(ROUND_IN) else OUTRO


def draw_cells(c, t):
    r = round_at(t)
    for rr in sorted({r} if r == 0 else {r - 1, r}):
        n, w, h, xs, ys, _ = layout(rr)
        for row in (0, 1):
            for k in range(n):
                j = n * row + k
                x, y = xs[k], ys[row]
                if rr == 0:
                    kin = 0.86 + 0.14 * spr(-0.06 + 0.035 * j, t, 2.2, 0.5)
                else:
                    kin = spr(ROUND_IN[rr] - SWAP + 0.16 + 0.03 * j, t, 2.3, 0.72)
                if kin <= 0.01:
                    continue
                t_out = leave_t(rr) + 0.03 * j
                o = sm(t_out, t_out + 0.32, t)
                if o >= 1:
                    continue
                sc = kin * (1 - 0.35 * o)
                a = 1 - o
                dy = 260 * o * o + 7 * math.sin(t * 2.3 + j * 1.27)          # a gentle float, each box its own phase
                rot = ((k - (n - 1) / 2) * 0.12) * o + 0.028 * math.sin(t * 1.7 + j * 0.83)
                tf = flip_t(rr, row, k)
                col = ROWCOL[row]
                if t < tf:                                                    # closed box
                    sc *= 1 + 0.018 * math.sin(t * 2.2 + j * 0.9)
                    if rr == 0 and t < ROUND_IN[0] + 0.5:
                        hit = E['blue'] if row == 0 else E['red']
                        sc *= 1 + 0.10 * fx.bump(t - hit - 0.03 * k, 3.0, 6.0) if t > hit else 1.0
                    if TIMER0[rr] <= t < REVEAL[rr]:
                        rot += 0.03 * math.sin(t * 9.0 + j * 1.7) * sm(REVEAL[rr] - 2.0, REVEAL[rr], t)
                    put(c, box_body(col, w, h, k + 1), x, y + dy, sc, a, rot)
                    put(c, box_lid(col, w, h), x, y + dy + lid_offset(h) * sc, sc, a, rot)
                    continue
                # open: the lid flies up, the card pops out of the box
                kl = cl((t - tf) / 0.42)
                if kl < 1:
                    put(c, box_lid(col, w, h), x + (k - (n - 1) / 2) * 30 * kl, y + lid_offset(h) - 150 * kl + 120 * kl * kl,
                        sc, a * (1 - kl), (0.6 if k % 2 else -0.6) * kl)
                kc = spr(tf + 0.04, t, 2.6, 0.5)
                pts = (ROUNDS[rr]['blue_pts'], ROUNDS[rr]['red_pts'])[row][k]
                pop = 1 + (0.08 if pts >= 5000 else 0.0) * fx.bump(t - tf - 0.3, 2.6, 5.0)
                put(c, card_face(rr, row, k, t), x, y + dy, sc * lerp(0.6, 1.0, cl(kc)) * pop, a * cl(kc * 3), rot)
                kp = spr(tf + 0.3, t, 2.5, 0.5)
                if kp > 0.01:
                    put(c, points_pill(pts, n == 5), x, y + dy + h / 2 - 6, sc * kp, a * cl(kp * 3), rot)


# ------------------------------------------------------------------ the gold box (final round)
@functools.lru_cache(None)
def bomb_sprite():                  # v6, not used since v7 (black hole)
    S = 2
    s = 150
    im = Image.new('RGBA', (s * S, s * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, r = 70 * S, 86 * S, 52 * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 30, 38, 255))
    d.ellipse([cx - r * 0.55, cy - r * 0.65, cx - r * 0.1, cy - r * 0.25], fill=(90, 92, 110, 255))
    d.rounded_rectangle([cx + 22 * S, cy - 62 * S, cx + 46 * S, cy - 38 * S], 5 * S, fill=(60, 60, 72, 255))
    d.line([(cx + 34 * S, cy - 62 * S), (cx + 48 * S, cy - 78 * S), (cx + 62 * S, cy - 74 * S)], fill=(150, 110, 60, 255),
           width=6 * S, joint='curve')
    for ang in range(0, 360, 45):                                            # the spark
        a = math.radians(ang)
        rr = (16 if ang % 90 == 0 else 10) * S
        d.line([(cx + 64 * S, cy - 76 * S), (cx + 64 * S + rr * math.cos(a), cy - 76 * S + rr * math.sin(a))],
               fill=(255, 190, 40, 255), width=4 * S)
    return im.resize((s, s), Image.LANCZOS)


def gold_shake(t):
    """Small screen shake when the hole opens (px)."""
    k = t - E['gold_open']
    if 0 <= k < 0.35:
        amp = 5 * (1 - k / 0.35)
        return int(round(amp * math.sin(k * 90))), int(round(amp * 0.6 * math.cos(k * 77)))
    return 0, 0


def draw_gold(c, t):
    if t < ROUND_IN[4] - SWAP:
        return
    x, y = GOLD_XY
    kin = spr(ROUND_IN[4] - SWAP + 0.5, t, 2.2, 0.6)
    if kin <= 0.01:
        return
    o = sm(OUTRO, OUTRO + 0.32, t)
    if o >= 1:
        return
    a = 1 - o
    y += 260 * o * o
    go = E['gold_open']
    if t < go:
        glow = 0.5 + 0.5 * math.sin(t * 4.0)
        disc(c, x, y, GOLD_SZ * 0.62 * kin, mix(BG, GOLD_C, 0.25 + 0.15 * glow), a)
        shake = 0.06 * math.sin(t * 40) * sm(go - 0.5, go, t)
        put(c, box_body(GOLD_C, GOLD_SZ, GOLD_SZ, 0, '?'), x, y, kin, a, shake)
        put(c, box_lid(GOLD_C, GOLD_SZ, GOLD_SZ), x, y + lid_offset(GOLD_SZ) * kin, kin, a, shake)
        text(c, 'ЗОЛОТАЯ', 26, 'Heavy', GOLD, x, y + GOLD_SZ / 2 + 30, a * kin)
        text(c, 'открывать не обязательно', 24, 'Semibold', MUTED, x, y + GOLD_SZ / 2 + 62, a * kin)
        return
    # v7 (author): a black hole instead of the bomb. It opens, sucks in «1000», then the gold box itself, and closes.
    k = t - go
    T_PTS, T_BOX, T_CLOSE = 0.7, 2.0, 3.1          # «1000» gets sucked in · the box gets sucked in · the hole closes
    grow = spr(go, t, 1.6, 0.7)
    close = sm(go + T_CLOSE, go + T_CLOSE + 0.45, t)
    hr = 64 * cl(grow) * (1 - close) + 18 * fx.bump(t - go - T_CLOSE - 0.45, 3.0, 8.0) * (t > go + T_CLOSE + 0.45)
    kl = cl(k / 0.45)                                                         # the lid is blown off
    if kl < 1:
        put(c, box_lid(GOLD_C, GOLD_SZ, GOLD_SZ), x + 60 * kl, y + lid_offset(GOLD_SZ) - 200 * kl, 1, a * (1 - kl), 1.4 * kl)
    # the box: shakes, then spirals into the hole
    kb = sm(go + T_BOX, go + T_BOX + 0.9, t)
    if kb < 1:
        ang = 6.0 * kb * kb
        rad = 70 * (1 - kb)
        bx, by = x + rad * math.cos(ang * 2.2), y + 6 + 14 * (1 - kb) + rad * 0.4 * math.sin(ang * 2.2)
        jit = 0.05 * math.sin(t * 50) * (1 - kb) * sm(go, go + 0.3, t)
        bdy = 30 * (1 - kb) * sm(go, go + 0.4, t)                             # it slides down a little: the hole sits on it
        put(c, box_body(GOLD_C, GOLD_SZ, GOLD_SZ, 0, '?'), bx, by + bdy, max(0.02, 1 - kb), a * (1 - kb ** 3), ang + jit)
    if hr > 0.5:
        swirl = t * 5.0
        disc(c, x, y + 6, hr * 1.55, (178, 140, 220), a * 0.25)                 # glow
        for j in range(3):                                                    # the accretion ring: three arcs that spin
            a0 = math.degrees(swirl * (1 + 0.3 * j)) + 120 * j
            arc(c, x, y + 6, hr * (1.18 + 0.12 * j), a0, a0 + 200, ((150, 90, 230), (240, 140, 60), (110, 160, 255))[j],
                max(3, hr * 0.12), a * 0.9)
        disc(c, x, y + 6, hr, (14, 12, 22), a)
        disc(c, x, y + 6, hr * 0.62, (4, 3, 8), a)
    # «1000» appears above and spirals in
    kp = spr(go + 0.35, t, 2.4, 0.55)
    ks = sm(go + T_PTS, go + T_PTS + 1.1, t)
    if kp > 0.01 and ks < 1:
        ang = 7.0 * ks * ks
        rad = 150 * (1 - ks)
        px, py = x + rad * math.sin(ang), y + 6 - rad * math.cos(ang)
        put(c, pill('1000', 44, GOLD, WHITE, padx=28), px, py, max(0.02, 1.15 * kp * (1 - ks)), a * cl(kp * 3), ang)
    # after the hole closes: what the viewer lost
    kr = spr(go + T_CLOSE + 0.5, t, 2.4, 0.5)
    if kr > 0.01:
        put(c, pill('−1000', 40, (214, 48, 48), WHITE, padx=26), x, y, max(0.01, kr), a * cl(kr * 3))
        text(c, 'ЧЁРНАЯ ДЫРА', 26, 'Heavy', MUTED, x, y + 62, a * cl(kr * 2))
        text(c, 'у тех, кто открыл', 24, 'Semibold', MUTED, x, y + 94, a * cl(kr * 2))


# ------------------------------------------------------------------ header, timer, tags
def draw_timer(c, t):
    r = round_at(t)
    if t < ROUND_IN[0] or t >= OUTRO:
        return
    ton = sm(TIMER0[r] - 0.05, TIMER0[r] + 0.25, t) * (1 - sm(REVEAL[r], REVEAL[r] + 0.3, t))
    if ton <= 0.01:
        return
    rad = lerp(22, 74, ton)                                      # v7: a bigger timer, a real 5 s count
    disc(c, W / 2, TIMER_Y, rad + 5, INK, ton)
    disc(c, W / 2, TIMER_Y, rad, WHITE, ton)
    left = cl((REVEAL[r] - t) / TIMER)
    arc(c, W / 2, TIMER_Y, rad - 11, -90, 270, LIGHT, 13, ton)
    arc(c, W / 2, TIMER_Y, rad - 11, -90 + 360 * (1 - left), 270, GOLD, 13, ton)
    n = max(1, math.ceil((REVEAL[r] - t) - 1e-6))
    tick = REVEAL[r] - n
    k = 1 + 0.22 * fx.bump(t - tick, 3.0, 7.0) if t >= tick else 1.0
    text(c, str(min(5, n)), 66, 'Heavy', GOLD if n <= 2 else INK, W / 2, TIMER_Y, ton, k * lerp(0.6, 1.0, ton))


def draw_tags(c, t):
    r = round_at(t)
    ty = layout(r)[5]
    if r == 4:                                                    # final: the tags slide to the 5 + 5 layout
        k = sm(ROUND_IN[4] - SWAP, ROUND_IN[4] - SWAP + 0.4, t)
        ty = tuple(lerp(a, b, k) for a, b in zip(TAG_Y, layout(4)[5]))
    for row in (0, 1):
        t0 = E['blue'] if row == 0 else E['red']
        k = spr(t0 - 0.05, t, 2.4, 0.55)
        a = cl(k * 2) * (1 - sm(OUTRO, OUTRO + 0.3, t))
        if a <= 0.004:
            continue
        put(c, pill(TAGS[row], 28, ROWCOL[row], WHITE, padx=22), W / 2, ty[row], max(0.01, k), a)


def draw_header(c, t):
    # hook: the bet from frame 0
    ah = 1 - sm(E['hook_out'] - 0.15, E['hook_out'] + 0.1, t)
    if ah > 0.004:
        k1 = 0.8 + 0.2 * spr(-0.05, t, 2.2, 0.5)
        k2 = 0.75 + 0.25 * spr(0.1, t, 2.2, 0.5)
        k3 = 1 + 0.14 * fx.bump(t - 1.4, 3.0, 6.0)                         # «БОЛЬШЕ 5000?» pulses
        text(c, HOOK[0], 92, 'Heavy', INK, W / 2, 208 + 30 * (1 - k1), ah, k1)
        text(c, HOOK[1], 58, 'Heavy', GOLD, W / 2, 290 + 30 * (1 - k1), ah, k1)
        text(c, HOOK[2], 92, 'Heavy', INK, W / 2, 374 + 30 * (1 - k2), ah, k2 * k3)
        put(c, pill(HOOK_BADGE, 38, GOLD, WHITE), W / 2, CAP_TOP + 40, k2, ah)
    if t >= OUTRO:
        ko = sm(OUTRO + 0.1, OUTRO + 0.4, t)
        text(c, 'ТВОЙ УРОВЕНЬ', 31, 'Semibold', GOLD, W / 2, 208, ko)
        text(c, SUM_TITLE, 78, 'Heavy', INK, W / 2, 302, ko, 0.9 + 0.1 * spr(OUTRO + 0.1, t))
        return
    a = sm(E['hook_out'] - 0.05, E['hook_out'] + 0.3, t)
    if a <= 0.004:
        return
    if t < ROUND_IN[0] - 0.1:
        rl = 'КАК ИГРАТЬ'
    else:
        r = max([k for k in range(5) if t >= ROUND_IN[k] - 0.1] or [0])
        rl = 'ФИНАЛ · РАУНД 5 / 5' if r == 4 else f'РАУНД {r + 1} / 5'
    text(c, rl, 31, 'Semibold', GOLD if 'ФИНАЛ' in rl else MUTED, W / 2, 208, a)
    kt = spr(E['pick'] - 0.1, t, 2.2, 0.55) if t < ROUND_IN[0] else 1.0
    text(c, TITLE, 60, 'Heavy', INK, W / 2, 286, a * cl(kt * 2), 0.85 + 0.15 * kt, maxw=1000)
    # rules: 100 · 300 · 500 under the title, where the timer will be
    km = spr(E['more'] - 0.05, t, 2.3, 0.5)
    am = cl(km * 2) * (1 - sm(TIMER0[0] - 0.3, TIMER0[0], t))
    if am > 0.004:
        for k, (pts, x) in enumerate(((100, -200), (1000, 0), (5000, 200))):
            kk = spr(E['more'] + 0.12 * k, t, 2.4, 0.5)
            put(c, points_pill(pts), W / 2 + x, TIMER_Y, max(0.01, kk), am * cl(kk * 2))
        text(c, 'дешевле', 26, 'Semibold', MUTED, W / 2 - 200, TIMER_Y + 50, am)
        text(c, 'дороже', 26, 'Semibold', MUTED, W / 2 + 200, TIMER_Y + 50, am)


def draw_teaser(c, t):
    """Retention before RubUp: the freeze frame of the ad shows this pill."""
    t0 = END[KEY['a3']] - 0.15
    if not (t0 <= t < ROUND_IN[3] - SWAP):
        return
    k = spr(t0, t, 2.4, 0.5)
    a = cl(k * 2) * (1 - sm(max(AD_STOP + 0.02, ROUND_IN[3] - SWAP - 0.3), ROUND_IN[3] - SWAP, t))
    put(c, pill(TEASER, 40, GOLD, WHITE), W / 2, PILL_Y, max(0.01, k) * (1 + 0.05 * fx.bump(t - t0 - 0.5, 3.0, 6.0)), a)


# ------------------------------------------------------------------ outro: levels
@functools.lru_cache(None)
def level_row(i):
    lo, hi, name = LEVELS[i]
    top = i == len(LEVELS) - 1
    S = 2
    w, h = 960, 128
    fill = GOLD if top else WHITE
    tc = WHITE if top else INK
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], 30 * S, fill=fill + (255,), outline=INK + (255,), width=5 * S)
    d.text((40 * S, 64 * S), f'{lo}–{hi}', font=fx.font('Heavy', 40 * S), fill=tc + (255,), anchor='lm')
    f = fx.font('Heavy', 38 * S)
    d.text((w * S - 40 * S, 64 * S), name, font=f, fill=(tc if top else INK) + (255,), anchor='rm')
    return im.resize((w, h), Image.LANCZOS)


def draw_levels(c, t):
    if t < OUTRO + 0.2:
        return
    for i in range(len(LEVELS)):
        t0 = E['sum'] + 0.05 + 0.16 * i
        k = spr(t0, t, 2.2, 0.55)
        if k <= 0.01:
            continue
        y = 500 + i * 152
        top = i == len(LEVELS) - 1
        pulse = 1 + (0.04 * math.sin((t - t0) * 5.0) * sm(t0 + 0.5, t0 + 1.0, t) if top else 0.0)
        put(c, level_row(i), W / 2 + 120 * (1 - k), y, (0.9 + 0.1 * k) * pulse, cl(k * 2))


def draw_outro(c, t):
    if t < E['comments']:
        return
    k = spr(E['comments'], t, 2.0, 0.5)
    put(c, pill(COMMENTS, 38, GOLD, WHITE), W / 2, PILL_Y, max(0.01, k), cl(k * 2))


# ------------------------------------------------------------------ captions
def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=960, top=CAP_TOP, size=50, weight='Semibold',
                        max_lines=2, color=INK, accent_color=GOLD, shadow=False, fade_out=0.2, rise=10)


@functools.lru_cache(None)
def _frame():
    """A quiet stylised frame: a rounded line inset from the edges, dotted corners (v7: fill the empty paper)."""
    S = 2
    im = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = mix(BG, MUTED, 0.32) + (255,)
    m, r = 34 * S, 48 * S
    d.rounded_rectangle([m, m, W * S - m, H * S - m], r, outline=col, width=3 * S)
    m2 = 48 * S
    d.rounded_rectangle([m2, m2, W * S - m2, H * S - m2], r - 14 * S, outline=mix(BG, MUTED, 0.18) + (255,), width=2 * S)
    for cx, cy in ((m, m), (W * S - m, m), (m, H * S - m), (W * S - m, H * S - m)):     # corner diamonds
        q = 11 * S
        d.polygon([(cx, cy - q), (cx + q, cy), (cx, cy + q), (cx - q, cy)], fill=BG + (255,), outline=col, width=3 * S)
    for x in range(160 * S, W * S - 150 * S, 38 * S):                                         # top / bottom ticks
        for y in (m, H * S - m):
            d.ellipse([x - 3 * S, y - 3 * S, x + 3 * S, y + 3 * S], fill=col)
    return np.asarray(im.resize((W, H), Image.LANCZOS)).copy()


@functools.lru_cache(None)
def doodle(kind, size):
    """Faint outline icons on the paper: gift box, star, «?», coin, sparkle."""
    S = 3
    s = size * S
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = mix(BG, MUTED, 0.38) + (255,)
    lw = max(2, size // 14) * S
    p = lw
    if kind == 'box':
        d.rounded_rectangle([p, s * 0.32, s - p, s - p], 5 * S, outline=col, width=lw)
        d.rounded_rectangle([0 + p // 2, s * 0.18, s - p // 2, s * 0.34], 4 * S, outline=col, width=lw)
        d.line([(s / 2, s * 0.18), (s / 2, s - p)], fill=col, width=lw)
        d.arc([s * 0.22, 0, s * 0.5, s * 0.24], 180, 360, fill=col, width=lw)
        d.arc([s * 0.5, 0, s * 0.78, s * 0.24], 180, 360, fill=col, width=lw)
    elif kind == 'star':
        pts = [(s / 2 + (s / 2 - p) * (1 if k % 2 == 0 else 0.45) * math.cos(math.radians(-90 + 36 * k)),
                s / 2 + (s / 2 - p) * (1 if k % 2 == 0 else 0.45) * math.sin(math.radians(-90 + 36 * k))) for k in range(10)]
        d.line(pts + [pts[0]], fill=col, width=lw, joint='curve')
    elif kind == 'q':
        d.text((s / 2, s / 2), '?', font=fx.font('Heavy', int(s * 0.9)), fill=col, anchor='mm')
    elif kind == 'coin':
        d.ellipse([p, p, s - p, s - p], outline=col, width=lw)
        d.ellipse([s * 0.25, s * 0.25, s * 0.75, s * 0.75], outline=col, width=max(1, lw // 2))
    else:                                                                                   # sparkle
        d.line([(s / 2, p), (s / 2, s - p)], fill=col, width=lw)
        d.line([(p, s / 2), (s - p, s / 2)], fill=col, width=lw)
        d.line([(s * 0.3, s * 0.3), (s * 0.7, s * 0.7)], fill=col, width=max(1, lw // 2))
        d.line([(s * 0.7, s * 0.3), (s * 0.3, s * 0.7)], fill=col, width=max(1, lw // 2))
    return im.resize((size, size), Image.LANCZOS)


# (kind, x, y, size, phase): the empty top corners and the bottom band under the captions
DOODLES = [('box', 112, 128, 70, 0.0), ('star', 968, 120, 54, 1.1), ('q', 240, 410, 46, 2.0), ('sparkle', 930, 400, 40, 0.6),
           ('coin', 120, 470, 40, 2.6), ('sparkle', 975, 290, 34, 1.7), ('q', 960, 470, 40, 0.3),
           ('box', 150, 1650, 84, 0.9), ('star', 330, 1770, 50, 2.3), ('q', 540, 1700, 60, 1.4), ('coin', 735, 1785, 46, 0.2),
           ('box', 925, 1665, 76, 2.8), ('sparkle', 92, 1560, 36, 1.9), ('sparkle', 990, 1560, 34, 0.7),
           ('star', 120, 1835, 38, 1.2), ('q', 975, 1840, 40, 2.1)]


def draw_decor(c, t):
    fx.over(c, (Image.fromarray(_frame()), 0, 0))
    for k, (kind, x, y, size, ph) in enumerate(DOODLES):
        put(c, doodle(kind, size), x + 6 * math.sin(t * 0.7 + ph), y + 9 * math.sin(t * 0.9 + ph * 1.7), 1.0, 0.9,
            0.15 * math.sin(t * 0.5 + ph))


def render_at(t):
    c = _bg().copy()
    draw_decor(c, t)
    draw_header(c, t)
    draw_timer(c, t)
    draw_cells(c, t)
    draw_gold(c, t)
    draw_tags(c, t)                 # tags stay readable over popping cells
    draw_levels(c, t)
    draw_teaser(c, t)
    draw_outro(c, t)
    dx, dy = gold_shake(t)
    if dx or dy:
        c = np.roll(c, (dy, dx), axis=(0, 1))
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
