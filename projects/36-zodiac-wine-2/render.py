"""36-zodiac-wine-2 «Гороскоп из телеги», часть 2 (код части 1, 35-zodiac-wine). Ночное небо со звёздами; хук — зодиакальный круг из 12 кружек Spiced Wine,
затем 4 знака: кружка-герой крупно (~600 px), за ней рисуется созвездие знака, свечение цвета напитка.
Финал — круг возвращается, «А ТВОЙ ЗНАК?» + «ПИШИ В КОММЕНТАРИЯХ».
Content time t -> RGB frame; RubUp via banner.Breaks (same in audio.py)."""
import functools
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import banner
import captions
import frames
import fx
import gifts_api
import lottie
import config
from script import (NEXT, LINES, GIFT, RARITY, SIGNS, WHEEL, GLYPHS, HOOK, HOOK_BADGE, PART, TEASER, FORECAST, OUTRO_1, OUTRO_2,
                    COMMENTS,
                    ACC)
from timeline import DUR, ON, END, KEY, SIGN_IN, OUTRO, SWAP, AD_STOP
from words import WORDS
from events import E, FORECAST as FC

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2)

BG, STAR, INK, MUTED, LINE, GOLD = config.BACKGROUND, config.STAR, config.INK, config.MUTED, config.LINE, config.GOLD
GRID, WHITE = config.GRID, config.WHITE


def dark(col, k=0.66):
    """Sign colour for text and lines on paper (the drink colours are too light to read)."""
    return tuple(int(v * k) for v in col)
FILES = {m: str(gifts_api.model_file(GIFT, m, 'json')) for m in WHEEL}
HERO = [s[0] for s in SIGNS]
HERO_IDX = [WHEEL.index(m) for m in HERO]           # part 2: 0 Aries, 1 Taurus, 2 Gemini, 3 Cancer
FIRST, LAST = HERO_IDX[0], HERO_IDX[3]
WHEEL_OUT_SC, WHEEL_OUT_A = (1.1, 1.0) if WHEEL[HERO_IDX[3]] in NEXT else (0.92, 0.32)   # = draw_wheel outro            # leaves the wheel first / flies back in the outro

HS = 720                     # hero Lottie raster (the mug fills ~90% of the canvas height)
HC = (540.0, 895.0)          # hero centre
MUG_DX = -0.047              # the mug sits right of the canvas centre: shift by this × size
WS = 208                     # wheel mug raster
WC = (540.0, 960.0)          # wheel centre
WR = 300.0                   # wheel radius
GR = 432.0                   # glyph ring radius
OMEGA = 11.0                 # wheel spin, degrees per second
DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


# ------------------------------------------------------------------ helpers
def cl(x):
    return min(1.0, max(0.0, x))


def sm(a, b, t):
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, k):
    return a + (b - a) * k


def spr(t0, t, f=2.0, z=0.55):
    return fx.spring(t - t0, f, z) if t > t0 else 0.0


@functools.lru_cache(4096)
def label(s, size, weight, color):
    f = ImageFont.truetype(DEJAVU, size) if weight == 'glyph' else fx.font(weight, size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    pad = 6
    im = Image.new('RGBA', (int(r - l) + 2 * pad, int(b - t) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=f, fill=color + (255,), anchor='ls')
    return im


def text(c, s, size, weight, color, cx, cy, a=1.0, sc=1.0, rot=0.0):
    if a <= 0.004 or sc <= 0.01:
        return
    fx.over(c, fx.warp(label(s, size, weight, color), cx, cy, sc, sc, rot), a)


def put(c, im, cx, cy, sc=1.0, a=1.0, rot=0.0, add=False):
    if a > 0.004 and sc > 0.01:
        fx.over(c, fx.warp(im, cx, cy, sc, sc, rot), a, add=add)


@functools.lru_cache(256)
def pill(s, size, fill_, tcol, outline=None, padx=34):
    f = fx.font('Heavy', size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    w, hh = int(r - l) + 2 * padx, int(size * 1.8)
    S = 2
    im = Image.new('RGBA', (w * S, hh * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w * S - 3, hh * S - 3], hh * S // 2, fill=None if fill_ is None else fill_ + (255,),
                        outline=None if outline is None else outline + (255,), width=0 if outline is None else 3 * S)
    d.text((w * S / 2, hh * S / 2), s, font=fx.font('Heavy', size * S), fill=tcol + (255,), anchor='mm')
    return im.resize((w, hh), Image.LANCZOS)


@functools.lru_cache(64)
def ring(r, width, color):
    S = 2
    n = int(2 * (r + width + 2))
    im = Image.new('RGBA', (n * S, n * S), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([(n / 2 - r) * S, (n / 2 - r) * S, (n / 2 + r) * S, (n / 2 + r) * S],
                               outline=color + (255,), width=round(width * S))
    return im.resize((n, n), Image.LANCZOS)


@functools.lru_cache(64)
def dot(r, color):
    S = 4
    n = int(2 * r + 4)
    im = Image.new('RGBA', (n * S, n * S), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([(n / 2 - r) * S, (n / 2 - r) * S, (n / 2 + r) * S, (n / 2 + r) * S],
                               fill=color + (255,))
    return im.resize((n, n), Image.LANCZOS)


@functools.lru_cache(16)
def sparkle_img(r, color):
    S = 4
    n = int(2 * r + 4)
    im = Image.new('RGBA', (n * S, n * S), (0, 0, 0, 0))
    fx.sparkle(ImageDraw.Draw(im), n * S / 2, n * S / 2, r * S, color + (255,))
    return im.resize((n, n), Image.LANCZOS)


@functools.lru_cache(16)
def glow(color, n=1000, peak=0.42):
    """Soft light behind the hero; float alpha + triangular dither -> no 8-bit banding on the dark sky."""
    yy, xx = (np.mgrid[0:n, 0:n] + 0.5) / n - 0.5
    r = np.sqrt(xx ** 2 + (yy * 1.05) ** 2) * 2
    a = np.clip(1 - r, 0, 1) ** 2.4 * peak
    rng = np.random.default_rng(7)
    a = a * 255 + (rng.random((n, n)) - rng.random((n, n)))
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = color
    im[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
    return Image.fromarray(im, 'RGBA')


@functools.lru_cache(8)
def big_glyph(glyph, color, size=860):
    """Background sign, one style for all 12: the DejaVu glyph as a line drawing — 7 px outline + a faint fill."""
    from PIL import ImageFilter
    f = ImageFont.truetype(DEJAVU, size)
    l, t, r, b = f.getbbox(glyph)
    pad = 30
    m = Image.new('L', (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(m).text((pad - l, pad - t), glyph, font=f, fill=255)
    edge = np.asarray(m.filter(ImageFilter.MaxFilter(15)), np.float32) - np.asarray(m, np.float32)
    fill = np.asarray(m, np.float32)
    a = np.clip(edge * 1.0 + fill * 0.28, 0, 255)
    im = np.zeros(a.shape + (4,), np.uint8)
    im[..., :3] = color
    im[..., 3] = a.astype(np.uint8)
    return Image.fromarray(im, 'RGBA').filter(ImageFilter.GaussianBlur(1.2))


def draw_big_glyph(c, t, s, a):
    """Half-transparent sign behind the hero: fades in with the scene, slow drift and breathing."""
    if a <= 0.004:
        return
    col = SIGNS[s][5]
    u = t - SIGN_IN[s]
    put(c, big_glyph(SIGNS[s][2], col), HC[0] + 14 * math.sin(u * 0.5), HC[1] - 10 + 10 * math.cos(u * 0.4),
        lerp(0.9, 1.0, a) * (1 + 0.015 * math.sin(u * 0.9)), 0.42 * a, math.radians(2.5 * math.sin(u * 0.35)))


# ------------------------------------------------------------------ sky
RNG = np.random.default_rng(35)
TWINKLE = [(RNG.uniform(0, W), RNG.uniform(0, H), RNG.uniform(1.4, 2.6), RNG.uniform(0, 6.3), RNG.uniform(0.6, 1.4))
           for _ in range(46)]


@functools.lru_cache(None)
def _bg():
    """Flat paper + a static dot grid (series look, no gradients)."""
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    step = 54
    for y in range(step // 2, H, step):
        for x in range(step // 2 + 9, W, step):
            d.ellipse([x - 2.2, y - 2.2, x + 2.2, y + 2.2], fill=GRID)
    return np.asarray(im, np.float32).copy()


def draw_sky(c, t):
    for x, y, r, ph, sp in TWINKLE[:22]:                     # a few amber sparkles breathe on the paper
        a = 0.25 + 0.5 * (0.5 + 0.5 * math.sin(t * sp * 2.2 + ph))
        put(c, sparkle_img(r * 3.2, STAR), x, y, 1.0, a)


# ------------------------------------------------------------------ constellations (stylised, x/y in -1..1)
CONST = {
    'Aries Rum': ([(-0.88, 0.62), (-0.28, 0.26), (-0.06, 0.06), (0.46, -0.22), (0.84, -0.66)],
                  [(0, 1), (1, 2), (2, 3), (3, 4)], 3),
    'Taurus-tini': ([(-0.36, 0.56), (0.04, 0.16), (0.86, -0.76), (-0.26, 0.12), (0.34, -0.86), (-0.84, 0.82)],
                    [(0, 1), (1, 2), (0, 3), (3, 4), (0, 5)], 1),
    'Gin Gemini': ([(-0.36, -0.86), (-0.46, -0.2), (-0.56, 0.4), (-0.72, 0.86), (-0.88, -0.3),
                    (0.16, -0.8), (0.16, -0.14), (0.22, 0.46), (0.38, 0.86), (0.64, -0.04)],
                   [(0, 1), (1, 2), (2, 3), (1, 4), (5, 6), (6, 7), (7, 8), (6, 9), (0, 5), (1, 6)], 5),
    'Cancer Collins': ([(0.0, 0.02), (-0.08, -0.8), (-0.62, 0.78), (0.58, 0.62), (-0.04, -0.28)],
                       [(0, 4), (4, 1), (0, 2), (0, 3)], 2),
}
CBOX = (452.0, 360.0)                 # half sizes of the constellation box around the hero


def draw_const(c, t, s, a):
    if a <= 0.004:
        return
    pts, segs, bright = CONST[HERO[s]]
    col = SIGNS[s][5]
    P = [(HC[0] + x * CBOX[0], HC[1] + y * CBOX[1]) for x, y in pts]
    t0 = SIGN_IN[s] + 0.15
    per = 1.5 / len(segs)
    lay = fx.draw_rgba((0, int(HC[1] - CBOX[1] - 30), W, int(HC[1] + CBOX[1] + 30)), lambda d, m, S: [
        d.line([m(*P[i]), m(*lerp_pt(P[i], P[j], cl((t - t0 - k * per) / per)))], fill=dark(col, 0.8) + (255,),
               width=round(2.6 * S))
        for k, (i, j) in enumerate(segs) if t > t0 + k * per])
    fx.over(c, lay, 0.6 * a)
    shown = {segs[0][0]} | {j for k, (i, j) in enumerate(segs) if t > t0 + (k + 0.9) * per} | \
            {i for k, (i, j) in enumerate(segs) if t > t0 + k * per}
    fl = fx.bump(t - FC[s], 2.0, 3.0) if t > FC[s] else 0.0        # forecast: the stars flash once
    for i, (x, y) in enumerate(P):
        if i not in shown:
            continue
        first = min([t0 + k * per for k, (p, q) in enumerate(segs) if i in (p, q)] or [t0])
        k = spr(first, t, 3.0, 0.5)
        r = (7.5 if i == bright else 4.6) * (1 + 0.6 * abs(fl))
        put(c, glow(col, 64, 0.9), x, y, 0.9 * k * (1.6 if i == bright else 1.0), a * 0.5)
        put(c, dot(r, dark(col, 0.7)), x, y, max(0.02, k), a)


def lerp_pt(p, q, k):
    return (lerp(p[0], q[0], k), lerp(p[1], q[1], k))


# ------------------------------------------------------------------ wheel (hook + outro)
def wheel_angle(k, t):
    """Degrees of mug k on the wheel. Hook: the first hero arrives at the top when sign 1 starts."""
    if t < OUTRO:
        return -90 + 30 * (k - FIRST) + OMEGA * (SIGN_IN[0] - t)
    return -90 + 30 * (k - LAST) - OMEGA * 0.5 * (t - OUTRO)        # outro: the last hero back at the top


def wheel_pos(k, t, rad=WR):
    a = math.radians(wheel_angle(k, t))
    return WC[0] + rad * math.cos(a), WC[1] + rad * math.sin(a)


def wheel_phase(k, t):
    if t < OUTRO:
        return t - SIGN_IN[0] + 0.25 * (k - FIRST)
    return t - SIGN_IN[3] + 0.25 * (k - LAST)


def mug(c, m, phase, cx, cy, size, sc, a, rot=0.0):
    im = lottie.frame(FILES[m], phase, size=size)
    put(c, im, cx + MUG_DX * size * sc, cy, sc, a, rot)


def draw_wheel(c, t):
    hook = t < SIGN_IN[0] + 0.3
    if hook:
        vis = 1 - sm(SIGN_IN[0] - 0.55, SIGN_IN[0] - 0.05, t)
        grow = 1 + 0.25 * sm(SIGN_IN[0] - 0.55, SIGN_IN[0] - 0.05, t)
    elif t >= OUTRO - 0.1:
        vis = sm(OUTRO - 0.1, OUTRO + 0.45, t)
        grow = lerp(1.25, 1.0, fx.smooth(vis))
    else:
        return
    if vis <= 0.004:
        return
    rad = WR * grow
    put(c, ring(GR - 62, 1.6, LINE), WC[0], WC[1], grow, 0.45 * vis)
    put(c, ring(GR + 44, 1.2, LINE), WC[0], WC[1], grow, 0.3 * vis)
    k4 = sm(E['four'] - 0.1, E['four'] + 0.4, t) if hook else 0.0
    order = sorted(range(12), key=lambda k: (k in HERO_IDX))         # chosen mugs on top
    for k in order:
        chosen = k in HERO_IDX
        if hook and k == FIRST and t > SIGN_IN[0] - 0.55:            # the first hero leaves the wheel
            continue
        if not hook and k == LAST and t < OUTRO + 0.5:              # the last hero flies back from the centre
            continue
        x, y = wheel_pos(k, t, rad)
        gx, gy = wheel_pos(k, t, GR * grow)
        pop = 0.75 + 0.25 * spr(-0.02 * k, t, 2.4, 0.55) if hook else 1.0   # frame 0 shows the whole wheel
        rip = 0.12 * fx.bump(t - E['twelve'] - 0.05 * k, 2.6, 5.0) if hook else 0.0
        if hook:
            sc = lerp(0.82, 1.0, pop) * (1 + rip) * (lerp(1.0, 1.28, k4) if chosen else lerp(1.0, 0.86, k4))
            a = vis * (1.0 if chosen else lerp(1.0, 0.38, k4))
        else:
            sc = grow * (1.1 if WHEEL[k] in NEXT else 0.92)
            a = vis * (1.0 if WHEEL[k] in NEXT else 0.32)             # outro: the 4 signs of part 3 are lit
        mug(c, WHEEL[k], wheel_phase(k, t), x, y, WS, sc, a)
        gcol = GOLD if (chosen and k4 > 0.5) or (not hook and WHEEL[k] in NEXT) else MUTED
        text(c, GLYPHS[k], 44, 'glyph', gcol, gx, gy, a if not hook else vis, 1.0)


def draw_wheel_centre(c, t):
    if t >= SIGN_IN[0]:
        return
    vis = 1 - sm(SIGN_IN[0] - 0.6, SIGN_IN[0] - 0.2, t)
    k12 = spr(E['twelve'] - 0.05, t, 2.4, 0.5)
    k4 = sm(E['four'] - 0.1, E['four'] + 0.25, t)
    a12 = vis * cl(k12 * 2)
    k4 = 0.0                                          # «ЧАСТЬ 1» is in the title from frame 0 (v2)
    text(c, '12', 150, 'Heavy', GOLD, WC[0], WC[1] - 24, a12, max(0.01, k12))
    text(c, 'ЗНАКОВ', 38, 'Heavy', INK, WC[0], WC[1] + 72, a12)
    text(c, PART.split()[0], 38, 'Heavy', INK, WC[0], WC[1] - 92, vis * k4)          # «ЧАСТЬ 1» on «первая часть»
    text(c, PART.split()[1], 150, 'Heavy', GOLD, WC[0], WC[1] + 10, vis * k4, lerp(0.6, 1.0, k4))


def draw_hook_title(c, t):
    a = 1 - sm(SIGN_IN[0] - 0.5, SIGN_IN[0] - 0.15, t)
    if a <= 0.004:
        return
    k1 = 0.84 + 0.16 * spr(-0.05, t, 2.2, 0.5)          # readable from frame 0
    k2 = 0.8 + 0.2 * spr(0.1, t, 2.2, 0.5)
    put(c, pill(PART, 40, None, GOLD, GOLD), 540, 132 + 24 * (1 - k1), k1, a)
    text(c, HOOK[0], 112, 'Heavy', GOLD, 540, 236 + 24 * (1 - k1), a, k1)
    text(c, HOOK[1], 60, 'Heavy', INK, 540, 334 + 24 * (1 - k2), a, k2)
    kb = 1 + 0.12 * fx.bump(t - E['four'] - 0.3, 3.0, 5.0)
    put(c, pill(HOOK_BADGE, 38, GOLD, WHITE), 540, 430 + 24 * (1 - k2), k2 * kb, a)


# ------------------------------------------------------------------ the four signs
def sign_at(t):
    s = -1
    for k, t0 in enumerate(SIGN_IN):
        if t >= t0 - SWAP - 0.25:
            s = k
    return s


def hero_motion(t, s):
    """(cx, cy, scale, alpha, rot) of sign s's hero mug."""
    if s == 0:                                                  # flies in from the top of the wheel
        k = sm(SIGN_IN[0] - 0.55, SIGN_IN[0] + 0.2, t)
        x0, y0 = wheel_pos(FIRST, SIGN_IN[0] - 0.55, WR)
        x, y = lerp(x0, HC[0], k), lerp(y0, HC[1], k)
        sc = lerp(WS / HS * 1.28, 1.0, k)
        a = float(t >= SIGN_IN[0] - 0.55)
        rot = 0.0
    else:                                                       # drops in from above
        t_in = SIGN_IN[s] - 0.38
        k = spr(t_in, t, 1.9, 0.62)
        x, y, sc, a, rot = HC[0], lerp(-420, HC[1], k), lerp(0.7, 1.0, cl(k)), float(t >= t_in), 0.0
    y += 9 * math.sin((t - SIGN_IN[s]) * 1.7) * sm(SIGN_IN[s], SIGN_IN[s] + 0.6, t)
    if s < 3:                                                   # leaves to the left, the next one drops
        t_out = SIGN_IN[s + 1] - SWAP - 0.2
        o = sm(t_out, t_out + 0.45, t)
        x -= 820 * o * o
        y -= 120 * o
        rot -= 0.35 * o
        a *= 1 - sm(t_out + 0.3, t_out + 0.45, t)
    else:                                                       # outro: back to its place on the wheel
        o = sm(OUTRO - 0.1, OUTRO + 0.5, t)
        gx, gy = wheel_pos(LAST, t, WR)                        # its live spot on the turning wheel
        x, y = lerp(x, gx, o), lerp(y, gy, o)
        sc = lerp(sc, WS / HS * WHEEL_OUT_SC, o)
        a *= lerp(1.0, WHEEL_OUT_A, o) * (t < OUTRO + 0.5)     # the wheel's own mug takes over: no double
    return x, y, sc, a, rot


def scene_alpha(t, s):
    a = sm(SIGN_IN[s] - 0.32, SIGN_IN[s] + 0.1, t)
    end = SIGN_IN[s + 1] - SWAP - 0.2 if s < 3 else OUTRO - 0.1
    return a * (1 - sm(end, end + 0.3, t))


def draw_sign(c, t):
    s = sign_at(t)
    if s < 0:
        return
    for ss in sorted({max(0, s - 1), s}):
        a = scene_alpha(t, ss)
        col = SIGNS[ss][5]
        x, y, sc, ha, rot = hero_motion(t, ss)
        if ha <= 0.004 and a <= 0.004:
            continue
        draw_big_glyph(c, t, ss, a)
        put(c, glow(col), HC[0], HC[1] + 10, 1.0 * (0.9 + 0.1 * math.sin(t * 1.3)), a * 0.75)
        draw_const(c, t, ss, a)
        if ha > 0.004:
            # sparkles fly out of the mug on the forecast
            if FC[ss] < t < FC[ss] + 1.6:
                for i in range(12):
                    ang = i * 2 * math.pi / 12 + 0.4 * ss
                    u = (t - FC[ss]) / 1.6
                    d = 200 + 260 * fx.ease_out(u)
                    put(c, sparkle_img(13 if i % 2 else 9, dark(SIGNS[ss][5], 0.85)), HC[0] + d * math.cos(ang),
                        HC[1] + 0.85 * d * math.sin(ang), 1.0, ha * (1 - u) * cl(u * 8))
            mug(c, HERO[ss], t - SIGN_IN[ss], x, y, HS, sc, ha, rot)
        draw_sign_text(c, t, ss, a)


def draw_sign_text(c, t, s, a):
    if a <= 0.004:
        return
    model, name, glyph, dates, elem, col, ton, count = SIGNS[s]
    k = spr(SIGN_IN[s] - 0.05, t, 2.2, 0.55)
    rise = 26 * (1 - cl(k))
    text(c, f'{PART} · ЗНАК {s + 1} / 4', 30, 'Semibold', MUTED, 540, 150, a)
    put(c, ring(56, 3, dark(col)), 540, 254 + rise, max(0.01, k), a)
    text(c, glyph, 66, 'glyph', dark(col), 540, 254 + rise, a, max(0.01, k))
    text(c, name, 100, 'Heavy', INK, 540, 392 + rise, a)
    text(c, dates, 36, 'Semibold', MUTED, 540, 464 + rise, a)
    kf = 0.0                                   # v3: no «ПРОГНОЗ» pill (author), the element chip stays
    put(c, pill(f'СТИХИЯ · {elem}', 32, None, dark(col), dark(col)), 540, 532 + rise, 1.0, a * (1 - kf))
    k2 = sm(SIGN_IN[s] + 0.2, SIGN_IN[s] + 0.55, t)
    text(c, model, 60, 'Heavy', dark(col), 540, 1276 + 16 * (1 - k2), a * k2)
    text(c, f'модель {GIFT} · {RARITY} · {ton} TON', 30, 'Semibold', MUTED, 540, 1330 + 16 * (1 - k2), a * k2)


def draw_teaser(c, t):
    """Retention before RubUp: the ad freeze frame shows what is still ahead."""
    t0 = END[KEY['s2']] + 0.1
    t1 = SIGN_IN[2] - SWAP - 0.2
    if not (t0 <= t < t1 + 0.3):
        return
    k = spr(t0, t, 2.4, 0.5)
    a = cl(k * 2) * (1 - sm(t1, t1 + 0.3, t))
    put(c, pill(TEASER, 38, GOLD, WHITE), 540, 1580, max(0.01, k) * (1 + 0.05 * fx.bump(t - t0 - 0.5, 3.0, 6.0)), a)


def draw_outro(c, t):
    if t < OUTRO:
        return
    k = spr(OUTRO + 0.1, t, 2.0, 0.55)
    text(c, OUTRO_1, 104, 'Heavy', GOLD, 540, 250 + 24 * (1 - cl(k)), cl(k * 2), max(0.01, lerp(0.8, 1.0, cl(k))))
    k2 = sm(OUTRO + 0.4, OUTRO + 0.8, t)
    text(c, OUTRO_2, 62, 'Heavy', INK, 540, 345, k2)
    kc = spr(E['comments'], t, 2.0, 0.5)
    if t >= E['comments']:
        put(c, pill(COMMENTS, 40, GOLD, WHITE), 540, 1580, max(0.01, kc) * (1 + 0.05 * math.sin((t - E['comments']) * 4)),
            cl(kc * 2))


# ------------------------------------------------------------------ captions
CAP = captions.Captions([captions.phrase(WORDS[k], accent=ACC, end=END[k] + 0.2) for k in range(len(LINES))],
                        width=940, top=1400, size=50, weight='Semibold', max_lines=2, color=INK, accent_color=GOLD,
                        shadow=False, fade_out=0.2, rise=10)


def render_at(t):
    c = _bg().copy()
    draw_sky(c, t)
    draw_sign(c, t)
    draw_wheel(c, t)
    draw_wheel_centre(c, t)
    draw_hook_title(c, t)
    draw_outro(c, t)
    draw_teaser(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
