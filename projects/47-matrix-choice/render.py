"""47-matrix-choice «Синяя или красная» — Морфеус (голова + ладони) на белом, едва видимые бегущие 0/1.
NFT в левой ладони (синий ореол), вещь в правой (красный). Content time t -> RGB frame; RubUp via AdBreaks:
during the ad Morpheus moves below the banner and agents assemble above it from code, look around, then look down at
him; he looks up at them; they dissolve as the banner ends (author, 2026-11-13). STORYBOARD.md §2–3."""
import functools
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import banner
import captions
import frames
import fx
import gifts_api
import lottie
import matrix
import character as ch
import photos
from script import LINES, ROUNDS, GIFT_RUB, THING_RUB, BADGE, SUBTITLE, HOOK, TEASER, TIMER
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO
from words import WORDS
from events import AD_STOP, E, WIN, TRICK_NFT, TRICK_THING, LOSE_T, WIN_GONE, FISTS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
INK = (22, 24, 28)
MUTED = (120, 126, 132)
GREEN = (0, 166, 81)
BLUE = (40, 110, 255)
RED = (235, 45, 45)
SIDE_COL = (BLUE, RED)
ITEM_POS = ((268.0, 1030.0), (812.0, 1030.0))
GIFTS = [str(gifts_api.model_file(g, m, 'json')) for g, m, *_ in ROUNDS]
GIFT_PX = 330
MONO = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'
SYMB = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def cl(x):
    return min(1.0, max(0.0, x))


def sm(a, b, t):
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def spr(t0, t, f=2.2, z=0.55):
    return fx.spring(t - t0, f, z) if t > t0 else 0.0


def lerp(a, b, k):
    return a + (b - a) * k


def put(c, im, cx, cy, sc=1.0, a=1.0, rot=0.0, sx=None, anchor=None, add=False):
    if im is None or a <= 0.004 or sc <= 0.01:
        return
    sy = sc
    sxv = sc if sx is None else sx
    if abs(sxv) < 0.01:
        return
    if sxv < 0:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        sxv = -sxv
    fx.over(c, fx.warp(im, cx, cy, sxv, sy, rot, anchor=anchor), a, add=add)


# ------------------------------------------------------------------ text sprites
@functools.lru_cache(4096)
def label(s, size, weight, color, mono=False):
    f = ImageFont.truetype(MONO, size) if mono else fx.font(weight, size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    pad = 6
    im = Image.new('RGBA', (int(r - l) + 2 * pad, int(b - t) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=f, fill=color + (255,), anchor='ls')
    return im


def text(c, s, size, weight, color, cx, cy, a=1.0, sc=1.0, mono=False, maxw=None):
    if a <= 0.004:
        return
    im = label(s, size, weight, color, mono)
    if maxw and im.width * sc > maxw:
        sc = maxw / im.width
    put(c, im, cx, cy, sc, a)


@functools.lru_cache(256)
def pill(s, size, fill_, tcol, mono=False, padx=28):
    f = ImageFont.truetype(MONO, size) if mono else fx.font('Heavy', size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    w, hh = int(r - l) + 2 * padx, int(size * 1.7)
    S = 2
    im = Image.new('RGBA', (w * S, hh * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w * S - 3, hh * S - 3], hh * S // 2, fill=fill_ + (255,))
    fS = ImageFont.truetype(MONO, size * S) if mono else fx.font('Heavy', size * S)
    d.text((w * S / 2, hh * S / 2), s, font=fS, fill=tcol + (255,), anchor='mm')
    return im.resize((w, hh), Image.LANCZOS)


@functools.lru_cache(16)
def halo(color, r=230):
    """Soft coloured glow + a thin pill-coloured rim, on white."""
    n = 2 * r
    yy, xx = np.mgrid[:n, :n]
    d = np.hypot(xx - r + 0.5, yy - r + 0.5) / r
    a = np.clip(1 - d, 0, 1) ** 1.6 * 0.55
    rim = np.clip(1 - np.abs(d - 0.78) / 0.025, 0, 1) * 0.35
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = color
    im[..., 3] = (np.clip(a + rim, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(im).filter(ImageFilter.GaussianBlur(3))


@functools.lru_cache(4)
def knight():
    f = ImageFont.truetype(SYMB, 92)
    im = Image.new('RGBA', (110, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((55, 62), '♞', font=f, fill=(48, 34, 22, 255), anchor='mm', stroke_width=2, stroke_fill=(245, 225, 190, 255))
    return im


@functools.lru_cache(4)
def flower():
    S = 4
    n = 90 * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    for k in range(10):
        a = 2 * math.pi * k / 10
        x, y = c + math.cos(a) * 24 * S, c + math.sin(a) * 24 * S
        d.ellipse([x - 16 * S, y - 10 * S, x + 16 * S, y + 10 * S], fill=(255, 92 + 8 * (k % 2), 170, 255))
    rot = im.rotate(18, resample=Image.BICUBIC)
    d = ImageDraw.Draw(rot)
    d.ellipse([c - 13 * S, c - 13 * S, c + 13 * S, c + 13 * S], fill=(255, 214, 60, 255))
    return rot.resize((90, 90), Image.LANCZOS)


@functools.lru_cache(4)
def star4(r=34):
    n = 2 * r
    yy, xx = np.mgrid[:n, :n] - r + 0.5
    a = np.clip(1 - (np.abs(xx) * np.abs(yy)) ** 0.5 / (r * 0.18), 0, 1) * np.clip(1 - np.hypot(xx, yy) / r, 0, 1)
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = (255, 236, 120)
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im)


# ------------------------------------------------------------------ background
def page(t, dim=0.0):
    bg = matrix.rain_bg(t, cell=26, seed=0)
    c = np.empty((H, W, 3), np.float32)
    c[:] = 255
    c *= (1 - 0.075 * bg)[..., None]
    return c


def green_rain(c, t, env):
    if env <= 0.003:
        return
    g = matrix.rain_bg(t, cell=22, seed=3, speed_px=(700, 600), period=14.0, gaps=0.35)
    k = (g * env * 0.85)[..., None]
    c[:] = c * (1 - k) + np.array((0, 175, 70), np.float32) * k


def rain_env(t):
    """Green code: the intro pour, a short burst before RubUp, the finale."""
    e = fx.smooth(t / 0.18) * (1 - fx.smooth((t - 1.05) / 0.85))
    e = max(e, 0.45 * sm(E['dissolve'] - 0.2, E['dissolve'] + 0.6, t))
    return e


# ------------------------------------------------------------------ the timeline of poses / faces
def _faces():
    f = [(0.0, 'calm')]
    for r in range(5):
        f.append((ON[1 + 3 * r], 'calm'))
        f.append((TRICK_NFT[r][0], 'look_left'))
        f.append((TRICK_THING[r][0], 'look_up' if r == 3 else 'look_right'))
        f.append((REVEAL[r] - 0.05, 'calm'))
        f.append((REVEAL[r] + 0.15, 'over_glasses' if r == 4 else ('smirk' if WIN[r] == 0 else 'brow')))
        if r == 0:
            f.append((LOSE_T[0] - 0.05, 'blow'))
            f.append((LOSE_T[0] + 0.75, 'calm'))
        else:
            f.append((LOSE_T[r] + 0.9, 'calm'))
    f.append((OUTRO, 'calm'))
    f.append((E['dissolve'] - 0.9, 'over_glasses'))
    return sorted(f)


FACES = _faces()
HEAD_G = [('nod', rv + 0.05) for rv in REVEAL] + [('tilt', ON[1 + 3 * r] + 0.1) for r in range(5)]
GLINTS = (E['formed'] + 0.05, TRICK_NFT[3][0] + 0.3, OUTRO + 1.0)


def _poses(side):
    p = [(0.0, 'fist')]
    for r in range(5):
        p += [(ROUND_IN[r], 'half'), (ROUND_IN[r] + 0.11, 'open')]
        if side == 0 and r == 4:                                     # the cap spins on the index finger
            p += [(TRICK_NFT[4][0], 'point_up'), (TRICK_NFT[4][1], 'open')]
        if side == 0 and r == 1:                                     # the watch is crushed in the fist
            p += [(LOSE_T[1] + 0.05, 'squeeze')]
        if side == 1 and r == 1:                                     # catches the tossed drill
            p += [(TRICK_THING[1][0] + 0.5, 'catch'), (TRICK_THING[1][0] + 0.75, 'open')]
        p += [(FISTS[r], 'half'), (FISTS[r] + 0.1, 'fist')]
    p += [(OUTRO + 0.35, 'half'), (OUTRO + 0.46, 'open')]          # the outro: a blue and a red pill
    p += [(E['dissolve'] - 0.5, 'half'), (E['dissolve'] - 0.4, 'fist')]
    return sorted(p)


POSES = (_poses(0), _poses(1))
HAND_G = [('offer', ROUND_IN[r] + 0.12, 'both') for r in range(5)] + \
         [('shake', LOSE_T[1] + 0.1, 0), ('weigh', REVEAL[0], 0)] + \
         [('shake', TRICK_THING[1][0] + 0.75, 1), ('shake', TRICK_THING[4][0] + 0.3, 1)]


# ------------------------------------------------------------------ Morpheus
INTRO = [('head', ch.HEAD_POS, 0.12, 1.75), ('fist0', ch.HAND_POS[0], 0.28, 1.6), ('fist1', ch.HAND_POS[1], 0.36, 1.55)]


@functools.lru_cache(None)
def _intro_sprites():
    def sc(im, s):
        return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    matrix.register('head', sc(*ch.head('calm')))
    for side in (0, 1):
        matrix.register(f'fist{side}', sc(*ch.hand(side, 'fist')))
    return True


def draw_morpheus(c, t, pos_head=None, pos_hands=None, scale=1.0, faces=None, alpha=1.0):
    """Intro assembly from code, then the photo rig; at the end he drains into code."""
    _intro_sprites()
    if t < 2.12 and pos_head is None:
        for key, (px, py), t0, dur in INTRO:
            if t < t0 + dur:
                arr, _ = matrix.assemble(t, key, t0, dur, seed={'head': 1, 'fist0': 2, 'fist1': 3}[key])
                if key == 'head':
                    dx, dy, rot, _ = ch.head_motion(t, ())
                else:
                    dx, dy, rot, _ = ch.hand_motion(t, 0 if key == 'fist0' else 1, ())
                im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
                fx.over(c, fx.warp(im, px + dx, py + dy, 1.0))
            elif key == 'head':
                ch.draw_head(c, t, FACES, HEAD_G, glints=GLINTS)
            else:
                ch.draw_hand(c, t, int(key[-1]), POSES[int(key[-1])], HAND_G)
        return
    k = 1.0 if t < E['dissolve'] else max(0.0, 1 - (t - E['dissolve']) / 1.1)
    if k >= 0.999:
        ch.draw_head(c, t, faces or FACES, HEAD_G, glints=GLINTS, pos=pos_head or ch.HEAD_POS, extra_sc=scale, a=alpha)
        for side in (0, 1):
            ch.draw_hand(c, t, side, POSES[side], HAND_G, pos=None if pos_hands is None else pos_hands[side],
                         extra_sc=scale, a=alpha)
        return
    # finale: drains into green code (cells → glyphs → gone), the same language as the intro
    name = 'over_glasses'
    im, s = ch.head(name)
    put(c, matrix.code_mix(im, k, t, seed=11, cell=14, fall=120), ch.HEAD_POS[0], ch.HEAD_POS[1], s)
    for side in (0, 1):
        him, hs = ch.hand(side, 'fist')
        put(c, matrix.code_mix(him, k, t, seed=12 + side, cell=14, fall=120), *ch.HAND_POS[side], hs)


# ------------------------------------------------------------------ items
def round_at(t):
    r = 0
    for k in range(5):
        if t >= ROUND_IN[k] - 0.05:
            r = k
    return r


def gift_im(r, t):
    return lottie.frame(GIFTS[r], t + 0.41 * r, size=GIFT_PX)


def thing_im(r):
    return photos.sprite(ROUNDS[r][3])


def item_base(r, side, t):
    """Float above the palm: (cx, cy, sc, rot, sx, alpha_code_k). k: 0..1 how much of the picture is assembled."""
    px, py = ITEM_POS[side]
    bob = 6 * math.sin(2 * math.pi * (t / 2.4) + side * 1.7 + r)
    k_in = sm(ROUND_IN[r] + 0.05 + 0.08 * side, ROUND_IN[r] + 0.6 + 0.08 * side, t)
    up = 0.0
    if t >= REVEAL[r] and WIN[r] == side:
        up = -36 * spr(REVEAL[r], t, 1.8, 0.6)
    return px, py + bob + up, k_in


def trick(r, side, t, im, cx, cy):
    """Returns (im, cx, cy, sc, rot, sx, anchor, extra_draw) for the timer tricks (one after another)."""
    sc, rot, sx, anchor, extra = 1.0, 0.0, None, None, []
    w0, w1 = (TRICK_NFT if side == 0 else TRICK_THING)[r]
    u = (t - w0) / (w1 - w0)
    if not 0 <= u <= 1:
        if side == 1 and r == 2 and t > w0:                     # the cactus flower stays after blooming
            extra.append(('flower', 1.0))
        return im, cx, cy, sc, rot, sx, anchor, extra
    if side == 0:
        if r == 0:      # signet ring flipped like a coin
            v = cl(u / 0.8)
            cy -= 270 * 4 * v * (1 - v)
            sx = math.cos(2 * math.pi * 2 * v)
            if abs(sx) < 0.06:
                sx = 0.06 if sx >= 0 else -0.06
        elif r == 1:    # watch swings like a pendulum from a point above
            ang = 0.5 * math.sin(2 * math.pi * 1.4 * u) * (1 - 0.4 * u) * math.sin(math.pi * u) ** 0.5
            anchor = (im.width / 2, 0)
            cy -= im.height / 2 + 40 * math.sin(math.pi * u)
            rot = ang
        elif r == 2:    # ring spins like a top
            sx = math.cos(2 * math.pi * 3.2 * u) * (0.35 + 0.65 * (1 - math.sin(math.pi * u) * 0.5))
            if abs(sx) < 0.06:
                sx = 0.06
            cx += 26 * math.sin(2 * math.pi * u)
            rot = 0.08 * math.sin(2 * math.pi * 3.2 * u)
        elif r == 3:    # glint across the glasses
            extra.append(('glint', u))
            sc = 1 + 0.05 * math.sin(math.pi * u)
        elif r == 4:    # cap spins on the fingertip
            hand_top = ch.HAND_POS[0][1] - 205
            cy = lerp(cy, hand_top - 70, sm(0, 0.12, u)) if u < 0.88 else lerp(hand_top - 70, cy, sm(0.88, 1, u))
            sx = math.cos(2 * math.pi * 3.0 * u)
            if abs(sx) < 0.06:
                sx = 0.06
            rot = 0.1 * math.sin(2 * math.pi * 3.0 * u + 1)
            sc = 0.82
    else:
        if r == 0:      # a knight hops over the board twice
            extra.append(('knight', u))
            for land in (0.29, 0.79):
                cy += 8 * fx.bump(u - land, 3.0, 9.0)
        elif r == 1:    # drill tossed, spins, caught, two short bursts
            v = cl(u / 0.37)
            cy -= 300 * 4 * v * (1 - v)
            rot = -2 * math.pi * fx.smooth(v)
            for b0, b1 in ((0.395, 0.63), (0.684, 0.895)):
                if b0 <= u <= b1:
                    cx += 5 * math.sin(u * 900)
                    cy += 3 * math.cos(u * 1100)
                    rot += 0.03 * math.sin(u * 700)
                    extra.append(('buzz', (u - b0) / (b1 - b0)))
        elif r == 2:    # cactus flower blooms
            extra.append(('flower', fx.ease_out_back(cl(u / 0.45), 1.6)))
        elif r == 3:    # telescope extends, a star twinkles where it points
            sc = 1 + 0.07 * sm(0, 0.4, u)
            anchor = (im.width / 2, im.height)
            cy += im.height / 2
            extra.append(('star', u))
        elif r == 4:    # chainsaw: pull-start jerk, then the engine runs
            if u < 0.12:
                cx -= 18 * math.sin(math.pi * u / 0.12)
            elif u < 0.88:
                cx += 3 * math.sin(u * 1300)
                cy += 2.5 * math.cos(u * 1700)
                extra.append(('smoke', (u - 0.12) / 0.76))
    return im, cx, cy, sc, rot, sx, anchor, extra


def draw_extra(c, kind, v, cx, cy, im, t):
    if kind == 'knight':
        pts = [(-95, 10), (-15, -20), (85, 15)]
        seg = 0 if v < 0.5 else 1
        w = (v - 0.5 * seg) / 0.5
        x0, y0 = pts[seg]
        x1, y1 = pts[seg + 1]
        x, y = lerp(x0, x1, w), lerp(y0, y1, w) - 120 * 4 * w * (1 - w)
        put(c, knight(), cx + x, cy + y - 45, 0.9, cl(v * 8) * cl((1 - v) * 8 + 0.3))
    elif kind == 'flower':
        put(c, flower(), cx + 4, cy - im.height / 2 + 18, 0.9 * v, 1.0, rot=0.3 * v)
    elif kind == 'glint':
        hh, ww = im.height, im.width
        yy, xx = np.mgrid[:hh, :ww]
        x = -0.3 * ww + v * 1.6 * ww
        band = np.clip(1 - np.abs((xx - x) + 0.6 * (yy - hh / 2)) / 26.0, 0, 1)
        g = np.zeros((hh, ww, 4), np.uint8)
        g[..., :3] = 255
        g[..., 3] = (band * np.asarray(im)[..., 3] / 255 * 230 * math.sin(math.pi * v)).astype(np.uint8)
        put(c, Image.fromarray(g), cx, cy, 1.0, 1.0, add=True)
        if v > 0.6:
            put(c, star4(), cx + ww * 0.32, cy - hh * 0.18, 0.6 + 0.6 * math.sin(math.pi * (v - 0.6) / 0.4), 1.0)
    elif kind == 'star':
        k = math.sin(math.pi * cl((v - 0.35) / 0.65))
        put(c, star4(), cx + 170, cy - 330, 0.4 + 0.9 * k, k, rot=v * 1.5)
    elif kind == 'buzz':
        for j in range(3):
            a = 0.5 * (1 - v)
            x0 = cx - 175 - 18 * j
            fx.over(c, fx.draw_rgba((x0 - 30, cy - 70 + 25 * j - 6, x0 + 4, cy - 70 + 25 * j + 6), lambda d, m, S, x0=x0, j=j:
                    d.line([m(x0 - 26, cy - 70 + 25 * j), m(x0, cy - 70 + 25 * j)], fill=MUTED + (255,), width=round(3 * S))), a)
    elif kind == 'smoke':
        for j in range(5):
            age = (v * 1.4 - j * 0.18)
            if 0 < age < 1:
                r = 10 + 34 * age
                x = cx - 150 - 30 * age + 8 * j
                y = cy - 30 - 90 * age
                fx.over(c, fx.draw_rgba((x - r - 2, y - r - 2, x + r + 2, y + r + 2), lambda d, m, S, x=x, y=y, r=r:
                        d.ellipse([*m(x - r, y - r), *m(x + r, y + r)], fill=(170, 172, 176, 255))), 0.45 * (1 - age))


def defeat(c, r, side, t, im, cx, cy):
    """The loser's own defeat (events.DEFEAT). Returns True while it draws the item itself."""
    u = t - LOSE_T[r]
    if u < 0:
        return False
    if r == 0:          # Morpheus blows the chess away
        v = cl(u / 0.9)
        k = 1 - cl((u - 0.25) / 0.6)
        put(c, matrix.code_mix(im, k, t, seed=21, cell=12), cx + 520 * v ** 1.6, cy - 160 * v, 1 - 0.3 * v, 1.0,
            rot=-0.7 * v)
    elif r == 1:        # the watch is crushed in the fist
        v = cl(u / 0.35)
        sy = 1 - 0.85 * v
        put(c, im, cx, lerp(cy, ch.HAND_POS[0][1] - 40, v), 1.0, 1 - cl((u - 0.3) / 0.12), sx=1 + 0.35 * v)
        if 0.3 < u < 0.9:
            w = (u - 0.3) / 0.6
            for j in range(9):
                a = 2 * math.pi * j / 9 + 0.4
                x = cx + math.cos(a) * 160 * w
                y = ch.HAND_POS[0][1] - 40 + math.sin(a) * 110 * w + 260 * w * w
                fx.over(c, fx.draw_rgba((x - 9, y - 9, x + 9, y + 9), lambda d, m, S, x=x, y=y, j=j:
                        d.rectangle([*m(x - 6, y - 4), *m(x + 6, y + 4)], fill=(90, 98, 104, 255) if j % 2 else (60, 200, 90, 255))), 1 - w)
    elif r == 2:        # a black hole opens and pulls the cactus in
        v = cl(u / 1.0)
        hr = 150 * math.sin(math.pi * cl(u / 1.25)) ** 0.7
        if hr > 1:
            hole = Image.new('RGBA', (int(2 * hr) + 8, int(2 * hr) + 8), (0, 0, 0, 0))
            d = ImageDraw.Draw(hole)
            o = hr + 4
            d.ellipse([o - hr, o - hr, o + hr, o + hr], fill=(8, 10, 12, 255))
            hole = hole.filter(ImageFilter.GaussianBlur(hr * 0.12))
            put(c, hole, cx, cy, 1.0, 0.92)
            for j in range(26):                          # glyphs spiralling in
                a0 = 2 * math.pi * j / 26 + u * (3 + j % 3)
                rr = (hr * 2.1) * (1 - ((u * 1.2 + j * 0.037) % 1))
                x, y = cx + math.cos(a0) * rr, cy + math.sin(a0) * rr * 0.8
                text(c, '01'[j % 2], 26, 'Heavy', GREEN, x, y, 0.8, mono=True)
        k = cl(1 - v)
        put(c, im, cx, cy, max(0.02, k), k ** 0.5, rot=6 * v * v)
    elif r == 3:        # lenses crack, then crumble into falling pixels
        a = np.asarray(im)
        if u < 0.35:
            put(c, im, cx, cy, 1.0)
            k = cl(u / 0.15)
            pts = [(0, 0), (-40, -18), (-70, 10), (-110, -6)], [(0, 0), (35, 22), (80, 8), (120, 30)], [(0, 0), (8, -36), (30, -60)]
            for p in pts:
                q = [(cx + x * k, cy - 20 + y * k) for x, y in p]
                fx.over(c, fx.draw_rgba((cx - 130, cy - 90, cx + 130, cy + 60), lambda d, m, S, q=q:
                        d.line([m(*pt) for pt in q], fill=(255, 255, 255, 255), width=round(3 * S))), 0.95)
        else:
            w = u - 0.35
            cell = 14
            hh, ww = a.shape[:2]
            for y0 in range(0, hh, cell):
                for x0 in range(0, ww, cell):
                    blk = a[y0:y0 + cell, x0:x0 + cell]
                    if blk[..., 3].mean() < 60:
                        continue
                    seed = (x0 * 31 + y0 * 17) % 97 / 97
                    yy = cy - hh / 2 + y0 + 900 * max(0, w - 0.1 * seed) ** 2
                    xx = cx - ww / 2 + x0 + (seed - 0.5) * 140 * w
                    if yy > H:
                        continue
                    col = tuple(int(v) for v in blk[..., :3].reshape(-1, 3).mean(0))
                    fx.over(c, fx.draw_rgba((xx - 1, yy - 1, xx + cell + 1, yy + cell + 1), lambda d, m, S, xx=xx, yy=yy, col=col:
                            d.rectangle([*m(xx, yy), *m(xx + cell - 2, yy + cell - 2)], fill=col + (255,))), cl(1 - w / 0.9))
    elif r == 4:        # chainsaw glitches like a broken signal and is squeezed into a pixel cube
        if u < 0.55:
            a = np.asarray(im).copy()
            rng = np.random.default_rng(int(t * 60))
            for _ in range(7):
                y0 = rng.integers(0, a.shape[0] - 10)
                hgt = rng.integers(4, 26)
                a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], rng.integers(-40, 40), axis=1)
            g = Image.fromarray(a)
            put(c, g, cx + 6, cy, 1.0, 0.5)
            rr = np.asarray(g).copy()
            rr[..., 1:3] = 0
            put(c, Image.fromarray(rr), cx - 8, cy, 1.0, 0.35, add=True)
            put(c, g, cx, cy, 1.0, 0.7)
        else:
            w = cl((u - 0.55) / 0.35)
            s = lerp(1.0, 0.0, w)
            put(c, im, cx, cy, max(0.02, s), 1 - w * 0.3, sx=max(0.02, s * (1 - 0.6 * w)))
            side_px = 40
            if w >= 1:
                fall = (u - 0.9)
                y = cy + 1400 * fall * fall
                fx.over(c, fx.draw_rgba((cx - 26, y - 26, cx + 26, y + 26), lambda d, m, S, y=y:
                        d.rectangle([*m(cx - side_px / 2, y - side_px / 2), *m(cx + side_px / 2, y + side_px / 2)], fill=(0, 166, 81, 255))),
                        cl(1 - fall / 0.6))
    return True


def draw_items(c, t):
    if t < ROUND_IN[0]:
        return draw_hook_pair(c, t)
    if t > OUTRO:
        return
    r = round_at(t)
    for side in (0, 1):
        im = gift_im(r, t) if side == 0 else thing_im(r)
        cx, cy, k = item_base(r, side, t)
        # winner dissolves into code, loser plays its defeat
        win = WIN[r] == side
        if win and t >= WIN_GONE[r]:
            k = 1 - cl((t - WIN_GONE[r]) / 0.4)
        if k <= 0.003:
            continue
        hal = 1.0
        if t >= REVEAL[r]:
            hal = lerp(1.0, 1.7 if win else 0.35, sm(REVEAL[r], REVEAL[r] + 0.35, t))
        if not win and t >= LOSE_T[r]:
            hal *= 1 - cl((t - LOSE_T[r]) / 0.4)
        pulse = 1 + 0.03 * math.sin(t * 3.1 + side)
        put(c, halo(SIDE_COL[side]), cx, cy, pulse * (1.1 if win and t > REVEAL[r] else 1.0), cl(hal) * k)
        if not win and defeat(c, r, side, t, im, cx, cy):
            continue
        im2, x, y, sc, rot, sx, anchor, extra = trick(r, side, t, im, cx, cy)
        shown = matrix.code_mix(im2, k, t, seed=31 + r * 2 + side, cell=12) if k < 0.999 else im2
        put(c, shown, x, y, sc, 1.0, rot, sx=None if sx is None else sx * sc, anchor=anchor)
        for kind, v in extra:
            draw_extra(c, kind, v, x, y, im2, t)


def draw_hook_pair(c, t):
    """Hook: the final pair already floats over the fists with hidden prices."""
    a = 1 - sm(ROUND_IN[0] - 0.35, ROUND_IN[0], t)
    if a <= 0.004:
        return
    k = sm(0.45, 1.3, t) * a
    for side in (0, 1):
        im = gift_im(4, t) if side == 0 else thing_im(4)
        px, py = ITEM_POS[side]
        py -= 30 - 6 * math.sin(t * 2.6 + side)
        put(c, halo(SIDE_COL[side]), px, py, 0.95, k)
        put(c, matrix.code_mix(im, k, t, seed=5 + side, cell=12), px, py, 0.82, 1.0)
        kp = spr(1.2 + 0.1 * side, t, 2.4, 0.5)
        put(c, pill('? ₽', 46, SIDE_COL[side], (255, 255, 255)), px, py + 200, max(0.01, kp), a * cl(kp * 2))


# ------------------------------------------------------------------ texts: hook, header, prices, timer
def draw_hook(c, t):
    a = 1 - sm(END[0] - 0.05, END[0] + 0.25, t)
    if a <= 0.004:
        return
    k1 = 0.85 + 0.15 * spr(-0.05, t, 2.2, 0.5)
    text(c, HOOK[0], 84, 'Heavy', INK, 540, 118, a, k1, maxw=980)
    text(c, HOOK[1], 84, 'Heavy', INK, 540, 210, a, k1, maxw=980)
    kp = spr(1.6, t, 2.4, 0.5)
    put(c, pill(HOOK[2], 40, GREEN, (255, 255, 255), mono=True), 540, 300, max(0.01, kp), a * cl(kp * 2))


def score_at(t):
    s = [0, 0]
    for r in range(5):
        if t >= REVEAL[r] + 0.3:
            s[WIN[r]] += 1
    return s


def draw_header(c, t):
    a = sm(END[0], END[0] + 0.35, t)
    if a <= 0.004:
        return
    if t < OUTRO:
        r = round_at(t)
        text(c, 'ЧТО ДОРОЖЕ?', 74, 'Heavy', INK, 540, 104, a)
        g, th = SUBTITLE[r]
        ga = a * sm(ROUND_IN[r], ROUND_IN[r] + 0.3, t) * (1 - sm(FISTS[r], FISTS[r] + 0.2, t) if r < 4 else 1)
        lg, lt = label(g, 36, 'Heavy', BLUE), label(th, 36, 'Heavy', RED)
        vs = label('vs', 30, 'Semibold', MUTED)
        tw = lg.width + vs.width + lt.width
        x = 540 - tw / 2
        put(c, lg, x + lg.width / 2, 172, 1.0, ga)
        put(c, vs, x + lg.width + vs.width / 2, 172, 1.0, ga)
        put(c, lt, x + lg.width + vs.width + lt.width / 2, 172, 1.0, ga)
        lab_ = 'ФИНАЛ' if r == 4 else f'РАУНД {r + 1}/5'
    else:
        ko = sm(OUTRO, OUTRO + 0.3, t)
        text(c, 'ТЕЛЕГА ПОБЕДИЛА 3:2', 66, 'Heavy', INK, 540, 104, ko)
        b, rr = label('СИНЯЯ', 52, 'Heavy', BLUE), label('КРАСНАЯ?', 52, 'Heavy', RED)
        mid = label('ИЛИ', 44, 'Heavy', INK)
        kk = sm(OUTRO + 0.9, OUTRO + 1.2, t)
        tw = b.width + mid.width + rr.width
        x = 540 - tw / 2
        put(c, b, x + b.width / 2, 178, 1.0, kk)
        put(c, mid, x + b.width + mid.width / 2, 178, 1.0, kk)
        put(c, rr, x + b.width + mid.width + rr.width / 2, 178, 1.0, kk)
        lab_ = None
    s = score_at(t)
    log = f'> ТЕЛЕГА {s[0]} : {s[1]} ЖИЗНЬ' + (f'   · {lab_}' if lab_ else '')
    last = max([REVEAL[r] + 0.3 for r in range(5) if t >= REVEAL[r] + 0.3] or [-9])
    kb = 1 + 0.18 * fx.bump(t - last, 3.0, 6.0) if last > 0 else 1.0
    text(c, log, 28, 'Heavy', GREEN, 540, 236, a, kb, mono=True)


def draw_prices(c, t):
    if t < REVEAL[0] or t > OUTRO:
        return
    r = round_at(t)
    if t < REVEAL[r]:
        return
    k = spr(REVEAL[r], t, 2.4, 0.55)
    a = cl(k * 2) * (1 - sm(FISTS[r] - 0.1, FISTS[r] + 0.15, t))
    for side in (0, 1):
        win = WIN[r] == side
        s = GIFT_RUB[r] if side == 0 else THING_RUB[r]
        im = pill(s, 40 if win else 34, SIDE_COL[side], (255, 255, 255))
        put(c, im, ITEM_POS[side][0], 1468, max(0.01, k), a * (1.0 if win else 0.7))
        sub = 'в телеге' if side == 0 else ROUNDS[r][6]
        text(c, sub, 26, 'Semibold', MUTED, ITEM_POS[side][0], 1524, a * cl(k))
        if win:
            kb = spr(REVEAL[r] + 0.2, t, 2.2, 0.45)
            put(c, pill(BADGE[r], 44, INK, (255, 255, 255)), ITEM_POS[side][0] + (110 if side == 0 else -110), 850,
                max(0.01, kb), a * cl(kb * 2), rot=-0.08 if side == 0 else 0.08)


def draw_timer(c, t):
    """Terminal countdown under the hands: > 00:05 … 00:01, a tick a second; the last second red."""
    for r in range(5):
        t0 = TIMER0[r]
        if t0 - 0.2 <= t < REVEAL[r] + 0.35:
            a = sm(t0 - 0.2, t0, t) * (1 - sm(REVEAL[r] + 0.1, REVEAL[r] + 0.35, t))
            n = max(0, math.ceil(REVEAL[r] - t - 1e-6))
            col = RED if n <= 1 else GREEN
            tick = REVEAL[r] - n
            kk = 1 + 0.16 * fx.bump(t - tick, 3.0, 8.0) if t >= tick else 1.0
            cur = '_' if int(t * 3) % 2 else ' '
            text(c, f'> ВРЕМЯ 00:0{min(5, n)}{cur}', 40, 'Heavy', col, 540, 1600, a, kk, mono=True)
            frac = cl((REVEAL[r] - t) / TIMER)
            x0, x1 = 300, 780
            fx.over(c, fx.draw_rgba((x0 - 4, 1628, x1 + 4, 1642), lambda d, m, S: (
                d.rectangle([*m(x0, 1632), *m(x1, 1638)], fill=(220, 226, 222, 255)),
                d.rectangle([*m(x0, 1632), *m(x0 + (x1 - x0) * frac, 1638)], fill=col + (255,)))), a)


def draw_teaser(c, t, ad=False, ad_a=1.0):
    t0 = END[KEY['a3']] - 0.1
    if not (t0 <= t < ROUND_IN[3] + 0.3) and not ad:
        return
    k = 1.0 if ad else spr(t0, t, 2.4, 0.5)
    a = ad_a if ad else cl(k * 2) * (1 - sm(ROUND_IN[3], ROUND_IN[3] + 0.3, t))
    put(c, pill(TEASER, 34, RED, (255, 255, 255), mono=True), 540, 108 if ad else 1600, max(0.01, k), a)


def draw_outro(c, t):
    if t < OUTRO + 0.3:
        return
    # a blue and a red pill in the open palms — the choice
    k = sm(OUTRO + 0.5, OUTRO + 1.1, t) * (1 - sm(E['dissolve'] - 0.55, E['dissolve'] - 0.4, t))
    for side in (0, 1):
        x, y = ch.HAND_POS[side][0], ch.HAND_POS[side][1] - 40
        im = pill('    ', 30, SIDE_COL[side], SIDE_COL[side], padx=34)
        put(c, halo(SIDE_COL[side], 120), x, y, 1.0, k)
        put(c, matrix.code_mix(im, k, t, seed=41 + side, cell=10), x, y, 1.0, 1.0, rot=0.5 if side == 0 else -0.5)
    kc = spr(OUTRO + 2.2, t, 2.0, 0.5)
    put(c, pill('ПИШИ В КОММЕНТАРИЯХ ↓', 38, INK, (255, 255, 255)), 540, 1600, max(0.01, kc), cl(kc * 2))


# ------------------------------------------------------------------ captions
CAP = captions.Captions([captions.phrase(WORDS[k], accent=(), end=END[k] + 0.25) for k in range(1, len(LINES)) if WORDS[k]],
                        width=780, top=1680, size=44, weight='Semibold', max_lines=2, color=INK,
                        accent_color=GREEN, shadow=False, fade_out=0.2, rise=8)


# ------------------------------------------------------------------ the ad scene (author: agents above, Morpheus below)
AGENTS = [(200.0, 425.0, 'down_right'), (540.0, 400.0, 'down'), (880.0, 425.0, 'down_left')]
AGENT_SC = 0.5


def draw_ad_scene(c, t_content, u, bt, B, header_a=0.0):
    """u: seconds since the break began (output), bt: banner time. Morpheus slides below the banner and looks up;
    agents assemble above it from code, look around, then all look down at him; they dissolve as the banner ends."""
    total = 2 * banner.RAMP + banner.PRE + B + banner.POST
    m = fx.smooth((u - 0.05) / 0.75) * (1 - fx.smooth((u - (total - 0.85)) / 0.75))
    head_pos = (540.0, lerp(ch.HEAD_POS[1], 1445.0, m))
    hands = ((lerp(ch.HAND_POS[0][0], 372.0, m), lerp(ch.HAND_POS[0][1], 1712.0, m)),
             (lerp(ch.HAND_POS[1][0], 708.0, m), lerp(ch.HAND_POS[1][1], 1712.0, m)))
    sc = lerp(1.0, 0.6, m)
    faces = [(0.0, 'calm'), (t_content + 0.001, 'calm')]
    if bt > 0.9 and bt < B + 0.2:
        faces = [(0.0, 'look_up')]
    ch.draw_head(c, t_content + u, faces, (), pos=head_pos, extra_sc=sc)
    for side in (0, 1):
        ch.draw_hand(c, t_content + u, side, [(0.0, 'fist')], (), pos=hands[side], extra_sc=sc)
    for j, (x, y, look) in enumerate(AGENTS):
        k = cl((bt - 0.25 - 0.3 * j) / 0.6) * (1 - cl((bt - (B - 0.55 + 0.15 * j)) / 0.5))
        if k <= 0.003:
            continue
        seq = [(-9, 'front'), (1.3 + 0.25 * j, 'left' if j != 1 else 'right'), (2.1 + 0.2 * j, 'right' if j != 1 else 'left'),
               (2.9, 'front'), (3.35 + 0.12 * j, look)]
        name = [n for s, n in seq if bt >= s][-1]
        im = ch.agent(name)
        bob = 3 * math.sin((t_content + u) * 1.7 + j)
        put(c, matrix.code_mix(im, k, t_content + u, seed=51 + j, cell=12, fall=80 if bt > B - 0.6 else 0),
            x, y + bob, AGENT_SC, 1.0)
    draw_teaser(c, t_content, ad=True, ad_a=1 - header_a)


class AdBreaks(banner.Breaks):
    def render(self, render_at, t, i=None, fps=60):
        ph = self.phase(t)
        if ph is None:
            return render_at(self.content_t(t))
        k, u = self._local(t)
        ct = self.content_t(t)
        c = render_at(ct, ad=(u, ph['bt'], self.B), raw=True)
        c *= 1 - banner.DIM * ph['dim']
        bt = ph['bt']
        n, bfps = banner.info()
        if 0 <= bt < self.B:
            rgb, al = banner._frame(min(n - 1, int(bt * bfps * self.speed)))
            y0 = int(self.cy) - rgb.shape[0] // 2
            reg = c[y0:y0 + rgb.shape[0], :rgb.shape[1]]
            reg[:] = reg * (1 - al) + rgb * al
        return np.clip(c, 0, 255).astype(np.uint8)


BR = AdBreaks([AD_STOP], cy=H / 2)


def render_at(t, ad=None, raw=False):
    c = page(t)
    green_rain(c, t, rain_env(t))
    if ad is None:
        draw_morpheus(c, t)
        draw_items(c, t)
        draw_header(c, t)
        draw_hook(c, t)
        draw_prices(c, t)
        draw_timer(c, t)
        draw_teaser(c, t)
        draw_outro(c, t)
        fx.over(c, CAP.layer(t))
    else:
        u, bt, B = ad
        fade = 1 - fx.smooth(u / 0.4) * (1 - fx.smooth((u - (2 * banner.RAMP + banner.PRE + B + banner.POST - 0.4)) / 0.4))
        if fade > 0.01:                     # the header and score fade out under the ad and come back
            tmp = c.copy()
            draw_header(tmp, t)
            c[:] = c * (1 - fade) + tmp * fade
        draw_ad_scene(c, t, u, bt, B, header_a=fade)
    return c if raw else np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
