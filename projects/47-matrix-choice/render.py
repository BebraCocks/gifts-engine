"""47-matrix-choice «Синяя или красная» v3 — Морфеус (голова + ладони) на белом, ярко-зелёные бегущие 0/1.
NFT над левой ладонью (синий ореол), вещь над правой (красный). Content time t -> RGB frame; RubUp via AdBreaks
(agents above the banner, Morpheus below). Author's v3 notes: bright green rain; one trick per round, alternating;
realistic fists (6-frame strip); no flat 2D flips; physical defeats; halos on appearance; a background motif per round.
STORYBOARD.md §2–3, events.py."""
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
import lipsync
from script import LINES, ROUNDS, GIFT_RUB, THING_RUB, BADGE, SUBTITLE, HOOK, TEASER, TIMER
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO
from words import WORDS
from events import (AD_STOP, E, WIN, TRICK, TRICK_SIDE, LOSE_T, WIN_GONE, FISTS, OPEN_DUR, CRUSH, HOOK_OPEN, REEL_T,
                    REEL_LAND)

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
INK = (22, 24, 28)
MUTED = (110, 116, 122)
GREEN = (0, 160, 70)
BLUE = (30, 105, 255)
RED = (235, 40, 40)
SIDE_COL = (BLUE, RED)
GIFTS = [str(gifts_api.model_file(g, m, 'json')) for g, m, *_ in ROUNDS]
GIFT_PX = 300
MONO = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf'
SYMB = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
G = 2600.0                     # px/s² — gravity for everything that falls (one value for the whole video)


def cl(x):
    return min(1.0, max(0.0, x))


def sm(a, b, t):
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def spr(t0, t, f=2.2, z=0.55):
    return fx.spring(t - t0, f, z) if t > t0 else 0.0


def lerp(a, b, k):
    return a + (b - a) * k


def put(c, im, cx, cy, sc=1.0, a=1.0, rot=0.0, anchor=None, add=False, sy=None):
    if im is None or a <= 0.004 or sc <= 0.01:
        return
    fx.over(c, fx.warp(im, cx, cy, sc, sc if sy is None else sy, rot, anchor=anchor), a, add=add)


def dot(c, x, y, r, col, a=1.0):
    if a > 0.004 and r > 0.3:
        fx.over(c, fx.draw_rgba((x - r - 2, y - r - 2, x + r + 2, y + r + 2),
                                lambda d, m, S: d.ellipse([*m(x - r, y - r), *m(x + r, y + r)], fill=col + (255,))), a)


# ------------------------------------------------------------------ text sprites
@functools.lru_cache(4096)
def label(s, size, weight, color, mono=False):
    f = ImageFont.truetype(MONO, size) if mono else fx.font(weight, size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    pad = 6
    im = Image.new('RGBA', (int(r - l) + 2 * pad, int(b - t) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=f, fill=color + (255,), anchor='ls')
    return im


@functools.lru_cache(512)
def backed(s, size, weight, color, mono=False):
    """Text on a soft white plate so it stays readable over the bright green rain."""
    im = label(s, size, weight, color, mono)
    pad = 14
    S = 2
    w, h = im.width + 2 * pad, im.height + pad
    base = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(base).rounded_rectangle([0, 0, w * S - 1, h * S - 1], 18 * S, fill=(255, 255, 255, 236))
    base = base.resize((w, h), Image.LANCZOS)
    base.alpha_composite(im, (pad, pad // 2))
    return base


def text(c, s, size, weight, color, cx, cy, a=1.0, sc=1.0, mono=False, maxw=None, plate=True):
    if a <= 0.004:
        return
    im = backed(s, size, weight, color, mono) if plate else label(s, size, weight, color, mono)
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
def halo(color, r=200):
    """A soft, quiet glow behind the item (author: «не такой яркий… просто небольшое сияние, свечение»)."""
    n = 2 * r
    yy, xx = np.mgrid[:n, :n]
    d = np.hypot(xx - r + 0.5, yy - r + 0.5) / r
    a = np.clip(1 - d, 0, 1) ** 2.2 * 0.42
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = color
    im[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(im).filter(ImageFilter.GaussianBlur(8))


@functools.lru_cache(8)
def glow_glyph(ch_, size=34):
    """A white 0/1 with a bright lime glow — stands out from the green rain (smoke, sparks, gravity)."""
    f = ImageFont.truetype(MONO, size)
    n = size * 2
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((n / 2, n / 2), ch_, font=f, fill=(150, 255, 90, 255), anchor='mm')
    glow = im.filter(ImageFilter.GaussianBlur(size * 0.22))
    g = np.asarray(glow).astype(np.float32)
    g[..., 3] = np.clip(g[..., 3] * 2.2, 0, 255)
    out = Image.fromarray(g.astype(np.uint8))
    core = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(core).text((n / 2, n / 2), ch_, font=f, fill=(255, 255, 255, 255), anchor='mm',
                              stroke_width=3, stroke_fill=(0, 90, 40, 255))
    out.alpha_composite(core)
    return out


@functools.lru_cache(8)
def wisp(r=46, col=(20, 150, 70)):
    n = 2 * r
    yy, xx = np.mgrid[:n, :n]
    d = np.hypot(xx - r + 0.5, yy - r + 0.5) / r
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = col
    im[..., 3] = (np.clip(1 - d, 0, 1) ** 1.6 * 230).astype(np.uint8)
    return Image.fromarray(im).filter(ImageFilter.GaussianBlur(4))


@functools.lru_cache(16)
def piece(ch_, dark):
    f = ImageFont.truetype(SYMB, 64)
    im = Image.new('RGBA', (80, 86), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((40, 46), ch_, font=f, fill=((40, 28, 18) if dark else (232, 205, 160)) + (255,),
                            anchor='mm', stroke_width=2, stroke_fill=((235, 215, 180) if dark else (90, 60, 30)) + (255,))
    return im


@functools.lru_cache(4)
def star4(r=34, col=(255, 236, 120)):
    n = 2 * r
    yy, xx = np.mgrid[:n, :n] - r + 0.5
    a = np.clip(1 - (np.abs(xx) * np.abs(yy)) ** 0.5 / (r * 0.18), 0, 1) * np.clip(1 - np.hypot(xx, yy) / r, 0, 1)
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = col
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im)


# ------------------------------------------------------------------ background: bright green code + round motifs
RAIN_DARK = np.array((0, 135, 50), np.float32)
RAIN_HEAD = np.array((0, 215, 80), np.float32)


def rain_speed(t):
    """Bullet time in the final round: the rain nearly stops during the countdown and starts again on the answer."""
    k = sm(TIMER0[4] - 0.3, TIMER0[4] + 0.6, t) * (1 - sm(REVEAL[4] - 0.1, REVEAL[4] + 0.4, t))
    return 1 - 0.85 * k


def _rain_time(t):
    """Integrated time so a speed change never makes the rain jump."""
    a0, a1, b0, b1 = TIMER0[4] - 0.3, TIMER0[4] + 0.6, REVEAL[4] - 0.1, REVEAL[4] + 0.4
    ts = np.linspace(0, t, max(2, int(t * 30)))
    return float(np.trapezoid([rain_speed(x) for x in ts], ts)) if t > a0 else t


def page(t):
    tr = _rain_time(t)
    g, hd = matrix.rain_bg(tr, cell=36, seed=0, speed_px=(190, 280), with_head=True, gaps=0.08, period=16.0)
    c = np.empty((H, W, 3), np.float32)
    c[:] = 255
    # keep the title band and the caption band calmer so the text reads (still green, just lighter)
    yy = np.arange(H, dtype=np.float32)[:, None]
    band = 1 - 0.25 * (np.clip(1 - np.abs(yy - 150) / 150, 0, 1) + np.clip(1 - np.abs(yy - 1640) / 110, 0, 1))
    a = (np.clip(0.58 + 0.5 * g, 0, 1) * (g > 0.02) * band)[..., None]
    c[:] = c * (1 - a) + RAIN_DARK * a
    hh = (0.95 * hd * band)[..., None]
    c[:] = c * (1 - hh) + RAIN_HEAD * hh
    return c


def green_flood(c, t, env):
    if env <= 0.003:
        return
    g = matrix.rain_bg(t, cell=22, seed=3, speed_px=(700, 600), period=14.0, gaps=0.35)
    k = (g * env * 0.9)[..., None]
    c[:] = c * (1 - k) + np.array((0, 175, 70), np.float32) * k


def flood_env(t):
    e = fx.smooth(t / 0.15) * (1 - fx.smooth((t - 0.75) / 0.6))
    return max(e, 0.5 * sm(E['dissolve'] - 0.2, E['dissolve'] + 0.6, t))


def round_live(r, t):
    """0..1 visibility of round r's background motif."""
    t1 = FISTS[r] + 0.2 if r < 4 else OUTRO + 0.2
    return sm(ROUND_IN[r] - 0.1, ROUND_IN[r] + 0.5, t) * (1 - sm(t1 - 0.3, t1, t))


def bg_motif(c, t):
    for r in range(5):
        a = round_live(r, t)
        if a <= 0.004:
            continue
        [motif_chess, motif_clock, motif_gravity, motif_stars, motif_ripples][r](c, t, a)


def motif_chess(c, t, a):
    """R1: a big chessboard of green squares fades in behind everything, squares lighting up one by one."""
    n, s = 8, 120
    x0, y0 = 540 - n * s / 2, 760 - n * s / 2
    def draw(d, m, S):
        for i in range(n):
            for j in range(n):
                if (i + j) % 2:
                    k = cl((t - ROUND_IN[0] - 0.05 * ((i * 3 + j * 5) % 11)) / 0.4)
                    if k > 0:
                        d.rectangle([*m(x0 + i * s, y0 + j * s), *m(x0 + (i + 1) * s, y0 + (j + 1) * s)],
                                    fill=(0, 170, 75, int(60 * k)))
        d.rectangle([*m(x0, y0), *m(x0 + n * s, y0 + n * s)], outline=(0, 150, 60, 140), width=round(3 * S))
    fx.over(c, fx.draw_rgba((x0 - 4, y0 - 4, x0 + n * s + 4, y0 + n * s + 4), draw), a)


def motif_clock(c, t, a):
    """R2: a huge clock face of green ticks; the second hand jumps with every timer second."""
    cx, cy, R = 540, 760, 470
    r = 1
    secs = 0 if t < TIMER0[r] else min(5, int(t - TIMER0[r]) + 1)
    kick = fx.bump(t - (TIMER0[r] + secs - 1), 3.0, 8.0) if secs else 0
    ang = -math.pi / 2 + 2 * math.pi * (secs / 60 * 5) + 0.05 * kick
    def draw(d, m, S):
        for k in range(60):
            q = 2 * math.pi * k / 60
            r0 = R - (40 if k % 5 == 0 else 18)
            d.line([m(cx + math.cos(q) * r0, cy + math.sin(q) * r0), m(cx + math.cos(q) * R, cy + math.sin(q) * R)],
                   fill=(0, 160, 70, 150 if k % 5 == 0 else 90), width=round((6 if k % 5 == 0 else 3) * S))
        d.ellipse([*m(cx - R, cy - R), *m(cx + R, cy + R)], outline=(0, 150, 60, 110), width=round(3 * S))
        d.line([m(cx, cy), m(cx + math.cos(ang) * (R - 60), cy + math.sin(ang) * (R - 60))], fill=(220, 40, 40, 170),
               width=round(5 * S))
        d.ellipse([*m(cx - 12, cy - 12), *m(cx + 12, cy + 12)], fill=(220, 40, 40, 200))
    fx.over(c, fx.draw_rgba((cx - R - 6, cy - R - 6, cx + R + 6, cy + R + 6), draw), a)


def ring_pos():
    return item_anchor(0, GIFT_H[2])


def motif_gravity(c, t, a):
    """R3: the Black Hole ring pulls the code: 0/1 glyphs spiral into it while it levitates and when it eats the cactus."""
    cx, cy = ring_pos()
    w0, w1 = TRICK[2]
    k = max(sm(w0, w0 + 0.5, t) * (1 - sm(w1 - 0.3, w1 + 0.2, t)), sm(LOSE_T[2] - 0.1, LOSE_T[2] + 0.3, t) * (1 - sm(LOSE_T[2] + 1.2, LOSE_T[2] + 1.5, t)))
    if k <= 0.004:
        return
    for j in range(46):
        base = (j * 0.618) % 1
        life = (t * 0.55 + base) % 1
        rr = 520 * (1 - life) ** 1.3 + 30
        q = 2 * math.pi * base * 7 + life * 5.0
        x, y = cx + math.cos(q) * rr, cy + math.sin(q) * rr * 0.85
        put(c, glow_glyph('01'[j % 2]), x, y, 0.5 + 0.6 * (1 - life), a * k * cl(life * 4) * (0.4 + 0.6 * life))


def motif_stars(c, t, a):
    """R4: a constellation fades in over the code; a shooting star crosses where the telescope points."""
    pts = [(150, 330), (300, 260), (430, 380), (650, 300), (820, 230), (960, 360), (880, 520), (180, 560)]
    def draw(d, m, S):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            d.line([m(x0, y0), m(x1, y1)], fill=(0, 150, 60, 110), width=round(2 * S))
    fx.over(c, fx.draw_rgba((0, 150, W, 660), draw), a)
    for k, (x, y) in enumerate(pts):
        tw = 0.6 + 0.4 * math.sin(t * 3.3 + k * 1.7)
        put(c, star4(), x, y, 0.45 * tw + 0.15, a)
    w0, w1 = TRICK[3]
    u = (t - (w0 + 1.2)) / 0.9
    if 0 <= u <= 1:
        x, y = lerp(980, 560, u), lerp(200, 430, u)
        for j in range(12):
            dot(c, x + j * 14, y - j * 7.4, 6 - j * 0.45, (255, 220, 90), (1 - j / 12) * math.sin(math.pi * u))
        put(c, star4(), x, y, 0.9, math.sin(math.pi * u))


def motif_ripples(c, t, a):
    """R5 (bullet time): concentric ripples spread from the centre while the rain almost stops."""
    k = sm(TIMER0[4] - 0.2, TIMER0[4] + 0.4, t) * (1 - sm(REVEAL[4], REVEAL[4] + 0.4, t))
    if k <= 0.004:
        return
    cx, cy = 540, 820
    def draw(d, m, S):
        for j in range(4):
            ph = ((t - TIMER0[4]) * 0.45 + j / 4) % 1
            r = 80 + ph * 760
            al = int(150 * (1 - ph))
            d.ellipse([*m(cx - r, cy - r * 0.9), *m(cx + r, cy + r * 0.9)], outline=(0, 150, 60, al), width=round(4 * S))
    fx.over(c, fx.draw_rgba((0, 0, W, H), draw), a * k)


# ------------------------------------------------------------------ hands (realistic 6-frame fist strip)
STRIP = 6
HAND_SC = 400.0 / 576.0        # open palm (strip frame 0) ≈ 400 px wide on screen
PALM = (51.0, -35.0)           # palm surface point relative to the hand centre (left hand; mirrored for the right)


@functools.lru_cache(None)
def strip_im(side, k):
    return Image.open(ch.SP / f'hand_{"L" if side == 0 else "R"}_close_{k}.png').convert('RGBA')


@functools.lru_cache(None)
def pose_im(side, name):
    return Image.open(ch.SP / f'hand_{"L" if side == 0 else "R"}_{name}.png').convert('RGBA')


def strip_p(side, t):
    """Strip position 0 (open palm) … 5 (fist, knuckles to camera) from the round events."""
    p = 5.0
    keys = [(HOOK_OPEN, 0.30, 5, 0)]
    for r in range(5):
        if r:
            keys.append((ROUND_IN[r], OPEN_DUR, 5, 0))
        if side == 0 and r == 1:                                     # the watch is crushed in the left hand
            t0 = LOSE_T[1]
            keys.append((t0 + CRUSH['close'][0], CRUSH['close'][1] - CRUSH['close'][0], 0, 5))
            keys.append((t0 + CRUSH['open'][0], CRUSH['open'][1] - CRUSH['open'][0], 5, 0))
        keys.append((FISTS[r], 0.28, 0, 5))
    keys.append((OUTRO + 0.35, OPEN_DUR, 5, 0))
    keys.append((E['dissolve'] - 0.5, 0.28, 0, 5))
    for t0, d, a, b in sorted(keys):
        if t >= t0:
            p = lerp(a, b, fx.smooth((t - t0) / d)) if t < t0 + d else b
    return p


def hand_extra(side, t):
    """(dx, dy, rot, override pose name or None) for tricks and the crush sequence."""
    ph = 0.0 if side == 0 else math.pi
    dx, dy, rot = 0.0, 5.0 * math.sin(t * 2 * math.pi / 3.2 + ph + 1.6), 0.015 * math.sin(t * 2 * math.pi / 3.9 + ph)
    pose = None
    if side == 0:                                                     # R2 crush: shake, then tilt to drop crumbs
        u = t - LOSE_T[1]
        a0, a1 = CRUSH['shake']
        if a0 <= u < a1:
            dx += 7 * math.sin(u * 2 * math.pi * 14) * (1 - (u - a0) / (a1 - a0) * 0.4)
            dy += 3 * math.cos(u * 2 * math.pi * 11)
            rot += 0.035 * math.sin(u * 2 * math.pi * 9)
        tl = sm(LOSE_T[1] + CRUSH['tilt'][0], LOSE_T[1] + CRUSH['tilt'][1], t) * (1 - sm(LOSE_T[1] + CRUSH['level'][0], LOSE_T[1] + CRUSH['level'][1], t))
        rot += 0.42 * tl                                             # fingers (screen-left) go down
        w0, w1 = TRICK[4]                                            # R5: index finger up for the cap
        if w0 + 0.30 <= t < w1 - 0.25:
            pose = 'point_up'
    if side == 1:
        w0, w1 = TRICK[1]                                            # R2 drill: the palm gives under the catch
        dy += 18 * fx.bump(t - (w0 + 1.15), 2.2, 5.0)
    for r in range(5):                                               # palms present the new pair
        dy -= 10 * fx.bump(t - ROUND_IN[r] - 0.25, 1.6, 3.5)
    if t >= REVEAL[0]:                                               # the winner's palm lifts a little on the reveal
        for r in range(5):
            if REVEAL[r] <= t < FISTS[r]:
                dy += (-14 if WIN[r] == side else 10) * spr(REVEAL[r], t, 1.8, 0.6)
    return dx, dy, rot, pose


def hand_xy(side):
    return ch.HAND_POS[side]


def draw_hand(c, t, side, pos=None, sc=1.0, a=1.0, force_fist=False):
    px, py = pos or hand_xy(side)
    dx, dy, rot, pose = hand_extra(side, t) if pos is None else (0.0, 0.0, 0.0, None)
    rot = rot if side == 0 else -rot
    if pose == 'point_up':
        im = pose_im(side, 'point_up')
        put(c, im, px + dx + (10 if side == 0 else -10), py + dy - 60, 400 / 522 * sc, a, rot)
        return
    p = 5.0 if force_fist else strip_p(side, t)
    k0 = int(math.floor(p))
    f = p - k0
    put(c, strip_im(side, k0), px + dx, py + dy, HAND_SC * sc, a, rot)
    if f > 0.02 and k0 + 1 < STRIP:                               # next frame fades in over an opaque base (no ghost)
        put(c, strip_im(side, k0 + 1), px + dx, py + dy, HAND_SC * sc, a * f, rot)


def palm_point(side, t=None):
    px, py = hand_xy(side)
    dx, dy = (0.0, 0.0) if t is None else hand_extra(side, t)[:2]
    return (px + (PALM[0] if side == 0 else -PALM[0]) + dx, py + PALM[1] + dy)


# ------------------------------------------------------------------ head
def _faces():
    f = [(0.0, 'calm3')]
    for r in range(5):
        f.append((ON[1 + 3 * r], 'calm3'))
        w0, w1 = TRICK[r]
        side = TRICK_SIDE[r]
        if r == 3:
            f.append((w0, 'look_up'))                                # the telescope: he looks at the star
        elif r == 4:
            f.append((w0 + 0.2, 'look_left_down'))                   # balancing the cap on his finger
        else:
            f.append((w0, 'look_left_down' if side == 0 else 'look_right'))
        f.append((w1, 'calm3'))
        if r == 0:
            f.append((ON[3] - 0.1, 'knowing'))
        else:
            f.append((REVEAL[r] + 0.12, 'over_glasses' if r == 4 else ('knowing' if WIN[r] == 0 else 'brows_up')))
        if r == 0:                                                   # turns to the chess and blows it away
            f += [(LOSE_T[0] - 0.12, 'after_blow_right'), (LOSE_T[0] - 0.02, 'blow_right'),
                  (LOSE_T[0] + 0.55, 'after_blow_right')]
        elif r == 1:
            f += [(LOSE_T[1] - 0.1, 'look_left_down'), (LOSE_T[1] + CRUSH['level'][1], 'calm3')]
        elif r == 2:
            f += [(LOSE_T[2], 'brows_up'), (LOSE_T[2] + 1.3, 'calm3')]
        else:
            f.append((LOSE_T[r] + 0.9, 'calm3'))
    f.append((OUTRO, 'calm3'))
    f.append((OUTRO + 1.6, 'knowing'))
    f.append((E['dissolve'] - 0.9, 'over_glasses'))
    out = []
    for t0, name in sorted(f):                      # a turned head while speaking would freeze the lips: wait
        if name not in FRONTAL:
            for k in range(len(LINES)):
                if ON[k] - 0.05 <= t0 < END[k]:
                    t0 = END[k] + 0.05
        out.append((t0, name))
    out.sort()
    for k in range(len(LINES)):                     # every line starts on a frontal face
        cur = [n for t0, n in out if t0 <= ON[k] - 0.1]
        if cur and cur[-1] not in FRONTAL:
            out.append((ON[k] - 0.12, 'calm3'))
    return sorted(out)


FRONTAL = {'calm3', 'knowing', 'brows_up', 'over_glasses'}
MOUTH_C = (0.5, 0.775)        # mouth centre in a frontal head (fractions of the sprite)


@functools.lru_cache(64)
def mouth_patch(face, vis):
    """The viseme's mouth + jaw, scaled onto `face` (same width, tops aligned), colour-matched, feathered ellipse."""
    F, _ = ch.head(face)
    V, _ = ch.head(vis)
    s_ = F.width / V.width
    V2 = V.resize((F.width, round(V.height * s_)), Image.LANCZOS)
    can = Image.new('RGBA', F.size, (0, 0, 0, 0))
    can.alpha_composite(V2.crop((0, 0, F.width, min(F.height + 30, V2.height))), (0, 0))
    a = np.asarray(can).astype(np.float32)
    f = np.asarray(F).astype(np.float32)
    h, w = F.height, F.width
    yy, xx = np.mgrid[:h, :w]
    e = ((xx - MOUTH_C[0] * w) / (0.21 * w)) ** 2 + ((yy - MOUTH_C[1] * h) / (0.13 * h)) ** 2
    m = np.clip((1.0 - e) / 0.45, 0, 1)
    ring = (e > 0.6) & (e < 1.0) & (a[..., 3] > 200) & (f[..., 3] > 200)
    if ring.sum() > 50:                                   # match skin tone at the seam
        gain = f[ring][:, :3].mean(0) / (a[ring][:, :3].mean(0) + 1e-6)
        a[..., :3] = np.clip(a[..., :3] * gain, 0, 255)
    a[..., 3] = a[..., 3] / 255 * m * (f[..., 3] / 255) * 255
    return Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))


def draw_head_ls(c, t, pos=None, extra_sc=1.0):
    """Morpheus' head with lip sync: the face rig (ch.draw_head) + the viseme's mouth on frontal faces."""
    vis, openness = lipsync.mouth(t)
    pos = pos or ch.HEAD_POS
    p2 = (pos[0], pos[1] + 3.0 * openness)               # the jaw moves the head a hair
    ch.draw_head(c, t, FACES, HEAD_G, glints=GLINTS, pos=p2, extra_sc=extra_sc)
    if not vis:
        return
    dx, dy, rot, sc = ch.head_motion(t, HEAD_G)
    items, t_sw = ch._mix(FACES, t)
    pop = 1 + 0.025 * fx.bump(t - t_sw, 2.6, 6.0)
    for face, fw in items:
        if face not in FRONTAL or fw <= 0.01:
            continue
        _, s = ch.head(face)
        for v, vw in vis:
            put(c, mouth_patch(face, 'v_' + v), p2[0] + dx, p2[1] + dy, s * sc * pop * extra_sc, fw * vw, rot)


FACES = _faces()
HEAD_G = [('nod', rv + 0.05) for rv in REVEAL] + [('tilt', ON[1 + 3 * r] + 0.1) for r in range(5)]
GLINTS = (E['formed'] + 0.05, OUTRO + 1.0)


# ------------------------------------------------------------------ Morpheus (intro from code, rig, finale into code)
INTRO = [('head', ch.HEAD_POS, 0.06, 1.18), ('fist0', ch.HAND_POS[0], 0.16, 1.08), ('fist1', ch.HAND_POS[1], 0.22, 1.04)]


@functools.lru_cache(None)
def _intro_sprites():
    def sc(im, s):
        return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    matrix.register('head', sc(*ch.head('calm3')))
    for side in (0, 1):
        matrix.register(f'fist{side}', sc(strip_im(side, 5), HAND_SC))
    return True


def draw_morpheus(c, t):
    _intro_sprites()
    if t < HOOK_OPEN - 0.01:
        for key, (px, py), t0, dur in INTRO:
            if t < t0 + dur:
                arr, _ = matrix.assemble(t, key, t0, dur, seed={'head': 1, 'fist0': 2, 'fist1': 3}[key])
                if key == 'head':
                    dx, dy, rot, _ = ch.head_motion(t, ())
                else:
                    dx, dy, rot, _ = hand_extra(int(key[-1]), t)
                im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
                fx.over(c, fx.warp(im, px + dx, py + dy, 1.0))
            elif key == 'head':
                draw_head_ls(c, t)
            else:
                draw_hand(c, t, int(key[-1]))
        return
    k = 1.0 if t < E['dissolve'] else max(0.0, 1 - (t - E['dissolve']) / 1.1)
    if k >= 0.999:
        draw_head_ls(c, t)
        return
    im, s = ch.head('over_glasses')
    put(c, matrix.code_mix(im, k, t, seed=11, cell=14, fall=140), ch.HEAD_POS[0], ch.HEAD_POS[1], s)


def draw_hands(c, t):
    if t < HOOK_OPEN - 0.01:
        return
    k = 1.0 if t < E['dissolve'] else max(0.0, 1 - (t - E['dissolve']) / 1.1)
    if k >= 0.999:
        for side in (0, 1):
            draw_hand(c, t, side)
        return
    for side in (0, 1):
        put(c, matrix.code_mix(strip_im(side, 5), k, t, seed=12 + side, cell=14, fall=140), *ch.HAND_POS[side], HAND_SC)


# ------------------------------------------------------------------ items
def gift_im(r, t):
    return lottie.frame(GIFTS[r], t + 0.41 * r, size=GIFT_PX)


@functools.lru_cache(None)
def _gift_box(r):
    bb = gift_im(r, 0.0).getbbox()
    return bb


@functools.lru_cache(None)
def gift_h(r):
    bb = _gift_box(r)
    return bb[3] - bb[1], (bb[1] + bb[3]) / 2 - GIFT_PX / 2     # visible height, centre offset of the visible part


class _GiftH(dict):
    """Visible gift heights, computed lazily in the worker: rendering Lottie at import time (before the render pool
    forks) deadlocks rlottie's internal threads in the children (v3 build hang, 2026-11-13)."""
    def __missing__(self, r):
        self[r] = gift_h(r)[0]
        return self[r]


GIFT_H = _GiftH()


def thing_im(r):
    return photos.sprite(ROUNDS[r][3])


def item_anchor(side, h, t=None, float_gap=26.0):
    """Centre for an item of visible height h hovering just above the palm (author: «чуть парят»)."""
    x, y = palm_point(side, t)
    return x, y - float_gap - h / 2


def round_at(t):
    r = 0
    for k in range(5):
        if t >= ROUND_IN[k] - 0.05:
            r = k
    return r


def item_state(r, side, t):
    """Where the item is and how it is drawn: (im, cx, cy, sc, rot, k_code, extra list, anchor)."""
    if side == 0:
        im = gift_im(r, t)
        h, off = gift_h(r)
        cx, cy = item_anchor(0, h, t)
        cy -= off                                        # Lottie frames have padding: align the visible part
    else:
        im = thing_im(r)
        cx, cy = item_anchor(1, im.height, t)
    cy += 6 * math.sin(2 * math.pi * t / 2.4 + side * 1.7 + r)          # hovering
    k = 1.0 if r == 0 else sm(ROUND_IN[r] + 0.08 + 0.10 * side, ROUND_IN[r] + 0.62 + 0.10 * side, t)
    sc, rot, extra, anchor = 1.0, 0.0, [], None
    if t >= REVEAL[r] and WIN[r] == side:
        cy -= 30 * spr(REVEAL[r], t, 1.8, 0.6)
    if TRICK_SIDE[r] == side:
        cx, cy, sc, rot, extra, anchor = trick(r, t, im, cx, cy)
    return im, cx, cy, sc, rot, k, extra, anchor


def toss(u, h_up, turns, land_u):
    """Parabolic toss from rest (u=0) back to the same height (u=land_u), tumbling `turns` full turns in-plane."""
    v = cl(u / land_u)
    return -h_up * 4 * v * (1 - v), -2 * math.pi * turns * v


def trick(r, t, im, cx, cy):
    w0, w1 = TRICK[r]
    u = (t - w0) / (w1 - w0)
    sc, rot, extra, anchor = 1.0, 0.0, [], None
    if not 0 <= u <= 1:
        return cx, cy, sc, rot, extra, anchor
    if r == 0:                     # genie lamp: rubbed — it sways, then green code smoke curls up from the spout
        sway = math.sin(math.pi * cl(u / 0.45))
        rot = 0.10 * math.sin(u * 2 * math.pi * 3.2) * sway
        cx += 8 * math.sin(u * 2 * math.pi * 3.2) * sway
        cy -= 10 * sm(0.4, 0.55, u) * (1 - sm(0.9, 1.0, u))
        extra.append(('smoke', u))
    elif r == 1:                   # drill: tossed, one tumble, caught, two short bursts (chuck spins)
        dy, rot = toss(u, 300, 1, 0.34)
        cy += dy
        for b0, b1 in ((0.40, 0.55), (0.66, 0.80)):
            if b0 <= u <= b1:
                q = (u - b0) / (b1 - b0)
                cx += 4 * math.sin(t * 2 * math.pi * 45)
                cy += 2 * math.cos(t * 2 * math.pi * 52)
                rot += 0.025 * math.sin(t * 2 * math.pi * 31)
                extra.append(('chuck', q))
    elif r == 2:                   # black hole ring: rises, turns slowly in-plane, the code spirals into it
        lift = sm(0.0, 0.25, u) * (1 - sm(0.8, 1.0, u))
        cy -= 70 * lift
        rot = 0.6 * math.sin(math.pi * u) * lift
        extra.append(('lens', lift))
    elif r == 3:                   # telescope: a small adjustment towards the star (pivot at the tripod head)
        rot = -0.035 * math.sin(math.pi * cl((u - 0.1) / 0.5))
        anchor = (im.width * 0.55, im.height * 0.42)
        cx += (anchor[0] - im.width / 2)
        cy += (anchor[1] - im.height / 2)
    elif r == 4:                   # cap: tossed tumbling, lands on the raised index finger and balances on it
        hx, hy = ch.HAND_POS[0]
        tip = (hx + 25.0, hy - 60 - 605 * (400 / 522) / 2 + 4)
        bb = _gift_box(4)
        ax, ay = (bb[0] + bb[2]) / 2, bb[3] - 14            # the cap's underside rests on the fingertip
        at_tip = (tip[0] - (ax - im.width / 2), tip[1] - (ay - im.height / 2))
        if u < 0.42:
            v = u / 0.42
            dy, rr = toss(u, 300, 1.5, 0.42)
            cx, cy = lerp(cx, at_tip[0], fx.smooth(v)), lerp(cy, at_tip[1], fx.smooth(v)) + dy
            rot = rr
        elif u < 0.86:
            q = (u - 0.42) * (w1 - w0)
            anchor = (ax, ay)
            cx, cy = tip[0] + 3 * math.sin(q * 9), tip[1]
            rot = 0.22 * math.sin(q * 6.0) * math.exp(-q * 0.5) + 0.05 * math.sin(q * 17)
            extra.append(('balance', q))
        else:
            v = (u - 0.86) / 0.14
            hx0, hy0 = cx, cy
            cx, cy = lerp(at_tip[0], hx0, fx.smooth(v)), lerp(at_tip[1], hy0, fx.smooth(v)) - 120 * 4 * v * (1 - v)
            rot = -2 * math.pi * 0.5 * v
    return cx, cy, sc, rot, extra, anchor


def draw_extra(c, kind, v, cx, cy, im, t):
    if kind == 'smoke':                                 # code smoke from the lamp's spout (left in the model)
        sx, sy = cx - im.width * 0.36, cy - im.height * 0.06
        k = sm(0.35, 0.5, v) * (1 - sm(0.88, 1.0, v))
        if v < 0.35:
            return
        for j in range(18):                          # soft lime smoke curling up
            life = ((v - 0.35) * 1.8 + j / 18) % 1
            x = sx - 40 * life + 55 * math.sin(life * 6 + j * 0.7) * life
            y = sy - 380 * life
            put(c, wisp(), x, y, 0.5 + 1.4 * life, k * 0.75 * (1 - life) * cl(life * 5))
        for j in range(22):                          # glowing code inside the smoke
            life = ((v - 0.35) * 2.2 + j / 22) % 1
            x = sx - 30 * life + 45 * math.sin(life * 7 + j) * life
            y = sy - 380 * life
            put(c, glow_glyph('01'[j % 2]), x, y, 0.6 + 0.7 * life, k * (1 - life) * cl(life * 6))
        return
    if kind == 'chuck':                                 # spinning chuck blur at the drill's nose (left in the photo)
        x, y = cx - im.width * 0.42, cy - im.height * 0.34
        for j in range(3):
            q = t * 60 + j * 2.1
            fx.over(c, fx.draw_rgba((x - 40, y - 40, x + 40, y + 40), lambda d, m, S, q=q:
                    d.arc([*m(x - 34, y - 30), *m(x + 34, y + 30)], math.degrees(q), math.degrees(q) + 70,
                          fill=(90, 96, 104, 255), width=round(4 * S))), 0.7)
    elif kind == 'lens':                                # gravitational lensing ring around the black hole
        def draw(d, m, S):
            for j in range(3):
                r = 175 + 22 * j + 6 * math.sin(t * 4 + j)
                d.ellipse([*m(cx - r, cy - r), *m(cx + r, cy + r)], outline=(10, 12, 16, int(120 - 35 * j)), width=round(3 * S))
        fx.over(c, fx.draw_rgba((cx - 250, cy - 250, cx + 250, cy + 250), draw), v)
    elif kind == 'balance':                             # spin streaks around the cap balanced on the finger
        for j in range(2):
            a0 = math.degrees(t * 9 + j * math.pi)
            fx.over(c, fx.draw_rgba((cx - 170, cy - 210, cx + 170, cy - 40), lambda d, m, S, a0=a0:
                    d.arc([*m(cx - 160, cy - 200), *m(cx + 160, cy - 60)], a0, a0 + 50, fill=(70, 74, 80, 255),
                          width=round(3 * S))), 0.45)


# --- defeats -------------------------------------------------------------------------------------------------
CHESS = [('♟', 1), ('♞', 1), ('♜', 0), ('♝', 1), ('♛', 0), ('♟', 0), ('♚', 1), ('♜', 1), ('♟', 1), ('♝', 0)]


def defeat(c, r, side, t, im, cx, cy):
    u = t - LOSE_T[r]
    if u < 0:
        return False
    if r == 0:          # Morpheus turns to the chess and blows: gust lines, the board slides off, pieces tumble away
        gust = sm(0.0, 0.12, u) * (1 - sm(0.45, 0.7, u))
        if gust > 0:                                     # a visible cone of air from the lips to the board
            mx, my = ch.HEAD_POS[0] + 60, ch.HEAD_POS[1] + 155
            for j in range(11):
                ph = (u * 2.6 + j / 11) % 1
                spread = (j - 5) * 13
                x0 = lerp(mx, cx + 40, ph)
                y0 = lerp(my, cy - 30, ph) + spread * ph * 1.6
                ln = 46 + 70 * ph
                def draw(d, m, S, x0=x0, y0=y0, ln=ln, spread=spread):
                    d.arc([*m(x0 - ln, y0 - 22), *m(x0 + ln * 0.3, y0 + 22)], 300, 350 if spread < 0 else 20,
                          fill=(120, 150, 170, 255), width=round(5 * S))
                    d.line([m(x0 - ln, y0), m(x0, y0 + spread * 0.05)], fill=(150, 175, 195, 255), width=round(4 * S))
                fx.over(c, fx.draw_rgba((x0 - ln - 6, y0 - 30, x0 + ln * 0.4 + 6, y0 + 30), draw),
                        0.9 * gust * math.sin(math.pi * ph))
        v = max(0.0, u - 0.12)
        bx = cx + 300 * v + 0.5 * 1800 * v * v
        by = cy - 120 * v + 0.5 * G * 0.25 * v * v
        if bx < W + 400:
            put(c, im, bx, by, 1.0, 1.0, rot=-0.9 * v)
        for j, (sym, dark) in enumerate(CHESS):          # pieces fly off: own speed, spin, gravity
            seed = (j * 37 % 11) / 11
            vx = 700 + 600 * seed
            vy = -700 - 500 * ((j * 53 % 7) / 7)
            x = cx - 120 + 26 * j + vx * v
            y = cy - 40 + vy * v + 0.5 * G * v * v
            if y < H + 100 and v > 0:
                put(c, piece(sym, dark), x, y, 0.75, 1.0, rot=(4 + 3 * seed) * v * (1 if j % 2 else -1))
    elif r == 1:        # watch: sinks into the palm, the fist closes and shakes, opens, palm tilts, crumbs fall
        px, py = palm_point(0, t)
        c0, c1 = CRUSH['close']
        if u < c1:
            v = u / c1
            put(c, im, lerp(cx, px, v), lerp(cy, py - 30, v), 1 - 0.35 * v, 1.0, sy=(1 - 0.35 * v) * (1 - 0.3 * v))
        # crumbs: appear when the fist opens, slide to the fingers when the palm tilts, then fall
        o0 = CRUSH['open'][1]
        if u >= o0:
            tilt_t = LOSE_T[1] + CRUSH['tilt'][0]
            for j in range(16):
                sd = ((j * 41) % 17) / 17
                x = px - 60 + 120 * sd
                y = py - 8 - 10 * ((j * 13) % 5) / 5
                q = t - tilt_t - 0.03 * (j % 5)
                if q > 0:                                    # slide toward the fingertips (screen-left), then fall
                    x -= 260 * q + 400 * q * q
                    if x < px - 200:
                        fall = (px - 200 - x) / 300
                        y += 0.5 * G * fall * fall + 40 * fall
                    else:
                        y += 70 * q
                if y > H:
                    continue
                col = (70, 76, 82) if j % 3 else ((40, 190, 90) if j % 2 else (150, 156, 162))
                rr = 5 + 4 * sd
                fx.over(c, fx.draw_rgba((x - rr - 2, y - rr - 2, x + rr + 2, y + rr + 2), lambda d, m, S, x=x, y=y, rr=rr, col=col:
                        d.polygon([m(x - rr, y), m(x, y - rr * 0.8), m(x + rr, y + rr * 0.3), m(x - rr * 0.3, y + rr)],
                                  fill=col + (255,))))
    elif r == 2:        # the ring's black hole pulls the cactus across: spiral path, stretched toward the hole, gone
        hx, hy = ring_pos()
        v = cl(u / 1.15)
        hr = 85 * math.sin(math.pi * cl(u / 1.45)) ** 0.6
        if hr > 1:
            hole = Image.new('RGBA', (int(2 * hr) + 10, int(2 * hr) + 10), (0, 0, 0, 0))
            o = hr + 5
            ImageDraw.Draw(hole).ellipse([o - hr, o - hr, o + hr, o + hr], fill=(6, 8, 10, 255))
            put(c, hole.filter(ImageFilter.GaussianBlur(hr * 0.15)), hx, hy, 1.0, 0.9)
        e = v ** 1.8
        ang = math.atan2(hy - cy, hx - cx)
        q = e * 2.2 * math.pi
        rr = math.hypot(hx - cx, hy - cy) * (1 - e)
        x = hx + math.cos(ang + math.pi + q) * rr
        y = hy + math.sin(ang + math.pi + q) * rr * 0.8
        s = max(0.02, 1 - e)
        if v < 1:
            put(c, im, x, y, s, 1.0, rot=q, sy=s * (1 - 0.5 * e))
    elif r == 3:        # lenses crack, then the glasses break into pieces that fall with gravity
        a = np.asarray(im)
        if u < 0.38:
            put(c, im, cx, cy, 1.0)
            k = cl(u / 0.16)
            pts = ([(0, 0), (-40, -16), (-74, 10), (-112, -6)], [(0, 0), (36, 22), (82, 8), (118, 30)],
                   [(0, 0), (8, -34), (30, -58)])
            for p in pts:
                qq = [(cx + x * k, cy - 18 + y * k) for x, y in p]
                fx.over(c, fx.draw_rgba((cx - 130, cy - 90, cx + 130, cy + 60), lambda d, m, S, qq=qq:
                        d.line([m(*pt) for pt in qq], fill=(255, 255, 255, 255), width=round(3 * S))), 0.95)
        else:
            w = u - 0.38
            cell = 16
            hh, ww = a.shape[:2]
            for y0 in range(0, hh, cell):
                for x0 in range(0, ww, cell):
                    blk = a[y0:y0 + cell, x0:x0 + cell]
                    if blk[..., 3].mean() < 60:
                        continue
                    sd = (x0 * 31 + y0 * 17) % 97 / 97
                    yy = cy - hh / 2 + y0 + 0.5 * G * max(0, w - 0.08 * sd) ** 2
                    xx = cx - ww / 2 + x0 + (sd - 0.5) * 160 * w
                    if yy > H:
                        continue
                    col = tuple(int(v) for v in blk[..., :3].reshape(-1, 3).mean(0))
                    rot_ = (sd - 0.5) * 6 * w
                    piece_im = Image.fromarray(np.ascontiguousarray(blk))
                    put(c, piece_im, xx + cell / 2, yy + cell / 2, 1.0, 1.0, rot=rot_)
    elif r == 4:        # chainsaw glitches like a broken signal, squeezed into a green pixel cube that falls
        if u < 0.55:
            a = np.asarray(im).copy()
            rng = np.random.default_rng(int(t * 60))
            for _ in range(8):
                y0 = int(rng.integers(0, a.shape[0] - 10))
                hgt = int(rng.integers(4, 26))
                a[y0:y0 + hgt] = np.roll(a[y0:y0 + hgt], int(rng.integers(-40, 40)), axis=1)
            g = Image.fromarray(a)
            rr = np.asarray(g).copy()
            rr[..., 1:3] = 0
            put(c, Image.fromarray(rr), cx - 8, cy, 1.0, 0.35, add=True)
            put(c, g, cx, cy, 1.0, 1.0)
        else:
            w = cl((u - 0.55) / 0.3)
            s = lerp(1.0, 0.0, w)
            if w < 1:
                put(c, im, cx, cy, max(0.02, s), 1.0, sy=max(0.02, s * (1 - 0.5 * w)))
            fall = max(0.0, u - 0.85)
            y = cy + 0.5 * G * fall * fall
            if y < H + 40:
                box = (cx - 24, y - 24, cx + 24, y + 24)
                fx.over(c, fx.draw_rgba(box, lambda d, m, S, y=y:
                        d.rectangle([*m(cx - 20, y - 20), *m(cx + 20, y + 20)], fill=(0, 166, 81, 255))), cl(w * 3))
    return True


def draw_items(c, t):
    if t < ROUND_IN[0]:
        return draw_hook_pair(c, t)
    if t > OUTRO:
        return
    r = round_at(t)
    for side in (0, 1):
        im, cx, cy, sc, rot, k, extra, anchor = item_state(r, side, t)
        win = WIN[r] == side
        if win and t >= WIN_GONE[r]:
            k = 1 - cl((t - WIN_GONE[r]) / 0.4)
        if k <= 0.003:
            continue
        # aura: flashes on when the item assembles, brighter for the winner, dims for the loser
        flash = 1 + 0.35 * fx.bump(t - ROUND_IN[r] - 0.35 - 0.1 * side, 2.0, 4.0)
        hal = 1.0
        if t >= REVEAL[r]:
            hal = lerp(1.0, 1.25 if win else 0.35, sm(REVEAL[r], REVEAL[r] + 0.35, t))
        if not win and t >= LOSE_T[r]:
            hal *= 1 - cl((t - LOSE_T[r]) / 0.35)
        pulse = 1 + 0.03 * math.sin(t * 3.1 + side)
        hx, hy = (cx, cy) if anchor is None else (cx - (anchor[0] - im.width / 2), cy - (anchor[1] - im.height / 2))
        if TRICK_SIDE[r] == side and r in (0, 1, 4):         # the aura stays where the item hovers during a toss
            hx, hy = item_anchor(side, GIFT_H[r] if side == 0 else im.height)
        if not win and defeat(c, r, side, t, im, cx, cy):
            continue
        shown = matrix.code_mix(im, k, t, seed=31 + r * 2 + side, cell=12) if k < 0.999 else im
        put(c, shown, cx, cy, sc, 1.0, rot, anchor=anchor)
        for kind, v in extra:
            if kind != 'motion':
                draw_extra(c, kind, v, cx, cy, im, t)


def draw_halos(c, t):
    """Auras sit behind the items AND the hands (the hands are lit by them, not painted over)."""
    if HOOK_OPEN <= t < ROUND_IN[0]:
        return hook_halos(c, t)
    if t > OUTRO + 0.3:
        k = sm(OUTRO + 0.5, OUTRO + 1.1, t) * (1 - sm(E['dissolve'] - 0.55, E['dissolve'] - 0.42, t))
        for side in (0, 1):
            x, y = palm_point(side, t)
            put(c, halo(SIDE_COL[side], 110), x, y - 26, 1.0, k)
        return
    if t < ROUND_IN[0] or t > OUTRO:
        return
    r = round_at(t)
    for side in (0, 1):
        im, cx, cy, sc, rot, k, extra, anchor = item_state(r, side, t)
        win = WIN[r] == side
        if win and t >= WIN_GONE[r]:
            k = 1 - cl((t - WIN_GONE[r]) / 0.4)
        if k <= 0.003:
            continue
        flash = 1 + 0.35 * fx.bump(t - ROUND_IN[r] - 0.35 - 0.1 * side, 2.0, 4.0)
        hal = 1.0
        if t >= REVEAL[r]:
            hal = lerp(1.0, 1.25 if win else 0.35, sm(REVEAL[r], REVEAL[r] + 0.35, t))
        if not win and t >= LOSE_T[r]:
            hal *= 1 - cl((t - LOSE_T[r]) / 0.35)
        pulse = 1 + 0.03 * math.sin(t * 3.1 + side)
        hx, hy = item_anchor(side, GIFT_H[r] if side == 0 else im.height, t)
        put(c, halo(SIDE_COL[side]), hx, hy, pulse * k ** 0.5 * (1.12 if win and t > REVEAL[r] else 1.0), cl(hal * flash) * k)


REEL_NFT = ['Plush Pepe', 'Swiss Watch', 'Signet Ring', 'Diamond Ring', 'Top Hat', 'Record Player', 'Mini Oscar',
            'Astral Shard', 'Electric Skull', 'Precious Peach', 'Heroic Helmet', 'Ion Gem', 'Perfume Bottle',
            'Neko Helmet', "Durov's Glasses", 'Crystal Ball', 'Love Potion']
REEL_THING = ['drill', 'headphones', 'telescope', 'iron', 'cactus', 'kettle', 'chainsaw', 'microwave']


@functools.lru_cache(64)
def reel_nft(name):
    im = Image.open(gifts_api.original_png(name, 256)).convert('RGBA')
    im = im.crop(im.getbbox())
    s_ = 250 / max(im.size)
    return im.resize((round(im.width * s_), round(im.height * s_)), Image.LANCZOS)


def reel_state(t):
    """(index of the current switch, seconds since it) or (None, 0) before the reels start."""
    k = None
    for i, ts in enumerate(REEL_T):
        if t >= ts:
            k = i
    return k, (t - REEL_T[k]) if k is not None else 0.0


def draw_hook_pair(c, t):
    if t < HOOK_OPEN + 0.06 or t >= ROUND_IN[0]:
        return
    k, since = reel_state(t)
    if k is None:
        return
    last = k == len(REEL_T) - 1
    for side in (0, 1):
        if last:                                    # landed: round 1's pair, exactly where round 1 continues
            im, cx, cy, sc, rot, kk, extra, anchor = item_state(0, side, t)
        else:
            if side == 0:
                im = reel_nft(REEL_NFT[(k * 7 + 3) % len(REEL_NFT)])
            else:
                im = photos.sprite(REEL_THING[(k * 5 + 1) % len(REEL_THING)])
            cx, cy = item_anchor(side, im.height, t)
            sc = 0.85
        drop = 46 * (1 - fx.smooth(since / 0.06))          # each new item snaps in from above like a reel
        pop = 1 + (0.14 if last else 0.07) * fx.bump(since, 3.0, 7.0)
        put(c, im, cx, cy - drop, sc * pop, 1.0)


def hook_halos(c, t):
    k, since = reel_state(t)
    if k is None:
        return
    a = sm(HOOK_OPEN, HOOK_OPEN + 0.25, t)
    land = 1 + 0.6 * fx.bump(t - REEL_LAND, 2.0, 4.0) if t >= REEL_LAND else 1.0
    for side in (0, 1):
        x, y = item_anchor(side, 260, t)
        put(c, halo(SIDE_COL[side]), x, y, 1.0, cl(a * land))


# ------------------------------------------------------------------ texts: hook, header, prices, timer
@functools.lru_cache(8)
def hook_line2():
    a_, b_ = label('ИЛИ ', 80, 'Heavy', INK), label('РЕАЛЬНОСТЬ?', 80, 'Heavy', RED)
    plate = Image.new('RGBA', (a_.width + b_.width + 28, max(a_.height, b_.height) + 12), (255, 255, 255, 236))
    plate.alpha_composite(a_, (14, (plate.height - a_.height) // 2))
    plate.alpha_composite(b_, (14 + a_.width, (plate.height - b_.height) // 2))
    return plate


def hook_slam_t():
    from words import wt
    return wt(0, 'Угадай') - 0.04


HOOK_SLAM = hook_slam_t()


def draw_hook(c, t):
    a = 1 - sm(END[0] - 0.05, END[0] + 0.25, t)
    if a <= 0.004:
        return
    k1 = 0.9 + 0.1 * spr(-0.05, t, 2.2, 0.5)
    k2 = 0.9 + 0.1 * spr(0.30, t, 2.2, 0.5)
    text(c, 'NFT', 96, 'Heavy', BLUE, 540, 100, a, k1)                         # the question from frame 0
    put(c, hook_line2(), 540, 196, min(k2, 980 / hook_line2().width), a)
    ts = HOOK_SLAM
    if t >= ts:
        ks = spr(ts, t, 2.6, 0.45)
        sc = lerp(2.2, 1.0, cl(ks)) if ks < 1 else 1 + 0.04 * fx.bump(t - ts - 0.2, 3, 6)
        put(c, pill(HOOK[2], 44, GREEN, (255, 255, 255), mono=True), 540, 292, sc, a * cl(ks * 3), rot=-0.03)


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
        text(c, 'ЧТО ДОРОЖЕ?', 72, 'Heavy', INK, 540, 96, a)
        g, th = SUBTITLE[r]
        ga = a * sm(ROUND_IN[r], ROUND_IN[r] + 0.3, t) * (1 - sm(FISTS[r], FISTS[r] + 0.2, t) if r < 4 else 1)
        if ga > 0.004:
            lg, lt = label(g, 36, 'Heavy', BLUE), label(th, 36, 'Heavy', RED)
            vs = label('vs', 30, 'Semibold', MUTED)
            tw = lg.width + vs.width + lt.width
            plate = Image.new('RGBA', (tw + 30, max(lg.height, lt.height) + 10), (255, 255, 255, 236))
            x0 = 15
            for im in (lg, vs, lt):
                plate.alpha_composite(im, (x0, (plate.height - im.height) // 2))
                x0 += im.width
            put(c, plate, 540, 166, 1.0, ga)
        lab_ = 'ФИНАЛ' if r == 4 else f'РАУНД {r + 1}/5'
    else:
        ko = sm(OUTRO, OUTRO + 0.3, t)
        text(c, 'ТЕЛЕГА ПОБЕДИЛА 3:2', 66, 'Heavy', INK, 540, 96, ko)
        kk = sm(OUTRO + 0.9, OUTRO + 1.2, t)
        if kk > 0.004:
            b, rr = label('СИНЯЯ', 52, 'Heavy', BLUE), label('КРАСНАЯ?', 52, 'Heavy', RED)
            mid = label(' ИЛИ ', 44, 'Heavy', INK)
            plate = Image.new('RGBA', (b.width + mid.width + rr.width + 30, b.height + 10), (255, 255, 255, 236))
            x0 = 15
            for im in (b, mid, rr):
                plate.alpha_composite(im, (x0, (plate.height - im.height) // 2))
                x0 += im.width
            put(c, plate, 540, 170, 1.0, kk)
        lab_ = None
    s = score_at(t)
    log = f'> ТЕЛЕГА {s[0]} : {s[1]} ЖИЗНЬ' + (f'  · {lab_}' if lab_ else '')
    last = max([REVEAL[r] + 0.3 for r in range(5) if t >= REVEAL[r] + 0.3] or [-9])
    kb = 1 + 0.18 * fx.bump(t - last, 3.0, 6.0) if last > 0 else 1.0
    text(c, log, 28, 'Heavy', GREEN, 540, 232, a, kb, mono=True)


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
        put(c, im, ch.HAND_POS[side][0], 1468, max(0.01, k), a * (1.0 if win else 0.75))
        sub = 'в телеге' if side == 0 else ROUNDS[r][6]
        text(c, sub, 26, 'Semibold', MUTED, ch.HAND_POS[side][0], 1524, a * cl(k))
        if win:
            kb = spr(REVEAL[r] + 0.2, t, 2.2, 0.45)
            put(c, pill(BADGE[r], 44, INK, (255, 255, 255)), ch.HAND_POS[side][0] + (120 if side == 0 else -120), 860,
                max(0.01, kb), a * cl(kb * 2), rot=-0.08 if side == 0 else 0.08)


def draw_timer(c, t):
    """Terminal countdown under the hands: > ВРЕМЯ 00:05 … 00:01, a tick a second; the last second red."""
    for r in range(5):
        t0 = TIMER0[r]
        if t0 - 0.2 <= t < REVEAL[r] + 0.35:
            a = sm(t0 - 0.2, t0, t) * (1 - sm(REVEAL[r] + 0.1, REVEAL[r] + 0.35, t))
            n = max(0, math.ceil(REVEAL[r] - t - 1e-6))
            col = RED if n <= 1 else GREEN
            tick = REVEAL[r] - n
            kk = 1 + 0.16 * fx.bump(t - tick, 3.0, 8.0) if t >= tick else 1.0
            cur = '_' if int(t * 3) % 2 else ' '
            text(c, f'> ВРЕМЯ 00:0{min(5, n)}{cur}', 40, 'Heavy', col, 540, 1596, a, kk, mono=True)
            frac = cl((REVEAL[r] - t) / TIMER)
            x0, x1 = 300, 780
            fx.over(c, fx.draw_rgba((x0 - 4, 1630, x1 + 4, 1646), lambda d, m, S: (
                d.rectangle([*m(x0, 1634), *m(x1, 1640)], fill=(220, 226, 222, 255)),
                d.rectangle([*m(x0, 1634), *m(x0 + (x1 - x0) * frac, 1640)], fill=col + (255,)))), a)


def draw_teaser(c, t, ad=False, ad_a=1.0):
    t0 = END[KEY['a3']] - 0.1
    if not (t0 <= t < ROUND_IN[3] + 0.3) and not ad:
        return
    k = 1.0 if ad else spr(t0, t, 2.4, 0.5)
    a = ad_a if ad else cl(k * 2) * (1 - sm(ROUND_IN[3], ROUND_IN[3] + 0.3, t))
    put(c, pill(TEASER, 34, RED, (255, 255, 255), mono=True), 540, 108 if ad else 1596, max(0.01, k), a)


@functools.lru_cache(4)
def capsule(color):
    """A pill like in the film: two-tone glossy capsule."""
    w, h, S = 120, 54, 3
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w * S - 3, h * S - 3], h * S // 2, fill=color + (255,))
    d.rounded_rectangle([14 * S, 8 * S, w * S - 22 * S, 18 * S], 6 * S, fill=(255, 255, 255, 120))
    return im.resize((w, h), Image.LANCZOS)


def draw_outro(c, t):
    if t < OUTRO + 0.3:
        return
    # the choice: a blue and a red pill appear on the open palms, lying on them (not floating)
    k = sm(OUTRO + 0.5, OUTRO + 1.1, t) * (1 - sm(E['dissolve'] - 0.55, E['dissolve'] - 0.42, t))
    for side in (0, 1):
        x, y = palm_point(side, t)
        put(c, matrix.code_mix(capsule(SIDE_COL[side]), k, t, seed=41 + side, cell=8), x, y - 26, 1.0, 1.0,
            rot=0.35 if side == 0 else -0.35)
    kc = spr(OUTRO + 2.2, t, 2.0, 0.5)
    put(c, pill('ПИШИ В КОММЕНТАРИЯХ ↓', 38, INK, (255, 255, 255)), 540, 1596, max(0.01, kc), cl(kc * 2))


# ------------------------------------------------------------------ captions
CAP = captions.Captions([captions.phrase(WORDS[k], accent=(), end=END[k] + 0.25) for k in range(1, len(LINES)) if WORDS[k]],
                        width=820, top=1680, size=46, weight='Bold', max_lines=2, color=INK,
                        accent_color=GREEN, shadow=False, fade_out=0.2, rise=8)


def caption_layer(c, t):
    lay = CAP.layer(t)
    if lay is None:
        return
    im, x0, y0 = lay
    bb = im.getbbox()
    if bb is None:
        return
    pad = 16
    x1, y1, x2, y2 = x0 + bb[0] - pad, y0 + bb[1] - pad // 2, x0 + bb[2] + pad, y0 + bb[3] + pad // 2
    al = np.asarray(im)[..., 3].max() / 255
    fx.over(c, fx.draw_rgba((x1, y1, x2, y2), lambda d, m, S: d.rounded_rectangle([*m(x1, y1), *m(x2, y2)], 18 * S,
            fill=(255, 255, 255, 236))), al)
    fx.over(c, lay)


# ------------------------------------------------------------------ camera / screen effects (one place, pure functions of t)
def _shakes():
    ev = [(E['formed'], 10.0), (HOOK_SLAM, 12.0)]
    ev += [(rv, 9.0) for rv in REVEAL]
    ev += [(LOSE_T[1] + CRUSH['shake'][0], 4.0), (LOSE_T[2] + 1.0, 7.0), (LOSE_T[4] + 0.55, 6.0)]
    return ev


SHAKES = _shakes()
GLITCHES = [f + 0.12 for f in FISTS[:4]] + [END[KEY['a3']] - 0.2, OUTRO - 0.05]


def post_fx(frame, t):
    """Screen shake on impacts, a punch-in + side-coloured flash on every reveal, an RGB-split glitch on round changes."""
    dx = dy = 0.0
    for t0, amp in SHAKES:
        u = t - t0
        if 0 <= u < 0.5:
            e = amp * math.exp(-u * 9)
            dx += e * math.sin(u * 2 * math.pi * 17 + t0)
            dy += e * 0.7 * math.cos(u * 2 * math.pi * 13 + t0)
    zoom = 1.0
    for rv in REVEAL:
        u = t - rv
        if 0 <= u < 0.45:
            zoom += 0.035 * math.exp(-u * 8)
    if zoom > 1.0005:
        im = Image.fromarray(frame)
        w2, h2 = W / zoom, H / zoom
        im = im.crop((int((W - w2) / 2), int((H - h2) / 2), int((W + w2) / 2), int((H + h2) / 2))).resize((W, H), Image.BILINEAR)
        frame = np.asarray(im).copy()
    if abs(dx) >= 1 or abs(dy) >= 1:
        frame = np.roll(frame, (int(round(dy)), int(round(dx))), axis=(0, 1))
    for r, rv in enumerate(REVEAL):                              # winner-side tinted flash
        u = t - rv
        if 0 <= u < 0.3:
            a = 0.16 * (1 - u / 0.3)
            col = np.array(SIDE_COL[WIN[r]], np.float32)
            frame = (frame * (1 - a) + col * a).astype(np.uint8)
    if t >= HOOK_SLAM and t - HOOK_SLAM < 0.22:
        a = 0.35 * (1 - (t - HOOK_SLAM) / 0.22)
        frame = (frame * (1 - a) + 255 * a).astype(np.uint8)
    for g0 in GLITCHES:                                          # RGB split + slices for ~0.2 s
        u = t - g0
        if 0 <= u < 0.2:
            k = math.sin(math.pi * u / 0.2)
            f = frame.copy()
            sh = int(10 * k)
            f[..., 0] = np.roll(frame[..., 0], sh, axis=1)
            f[..., 2] = np.roll(frame[..., 2], -sh, axis=1)
            rng = np.random.default_rng(int(t * 60))
            for _ in range(6):
                y0 = int(rng.integers(0, H - 40))
                hh = int(rng.integers(8, 60))
                f[y0:y0 + hh] = np.roll(f[y0:y0 + hh], int(rng.integers(-60, 60) * k), axis=1)
            frame = f
    return frame


def draw_sparks(c, t):
    """Green code sparks burst out of each item as it assembles (and out of the pills in the hook)."""
    bursts = [(ROUND_IN[r] + 0.32 + 0.1 * side, r, side) for r in range(1, 5) for side in (0, 1)]
    bursts += [(REEL_LAND + 0.02 + 0.06 * side, 0, side) for side in (0, 1)]       # the reels land
    for t0, r, side in bursts:
        u = t - t0
        if not 0 <= u < 0.7:
            continue
        x0, y0 = palm_point(side, t)
        y0 -= 170
        for j in range(14):
            a = 2 * math.pi * j / 14 + r
            sp = 380 + 160 * ((j * 7) % 5) / 5
            x = x0 + math.cos(a) * sp * u
            y = y0 + math.sin(a) * sp * u + 0.5 * G * 0.35 * u * u
            put(c, glow_glyph('01'[j % 2]), x, y, 0.75, (1 - u / 0.7))


# ------------------------------------------------------------------ the ad scene (agents above, Morpheus below)
AGENTS = [(200.0, 425.0, 'down_right'), (540.0, 400.0, 'down'), (880.0, 425.0, 'down_left')]
AGENT_SC = 0.5


def draw_ad_scene(c, t_content, u, bt, B, header_a=0.0):
    total = 2 * banner.RAMP + banner.PRE + B + banner.POST
    m = fx.smooth((u - 0.05) / 0.75) * (1 - fx.smooth((u - (total - 0.85)) / 0.75))
    head_pos = (540.0, lerp(ch.HEAD_POS[1], 1445.0, m))
    hands = ((lerp(ch.HAND_POS[0][0], 372.0, m), lerp(ch.HAND_POS[0][1], 1712.0, m)),
             (lerp(ch.HAND_POS[1][0], 708.0, m), lerp(ch.HAND_POS[1][1], 1712.0, m)))
    sc = lerp(1.0, 0.6, m)
    faces = [(0.0, 'look_up')] if 0.9 < bt < B + 0.2 else [(0.0, 'calm3')]
    ch.draw_head(c, t_content + u, faces, (), pos=head_pos, extra_sc=sc)
    for side in (0, 1):
        draw_hand(c, t_content + u, side, pos=hands[side], sc=sc, force_fist=True)
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
    green_flood(c, t, flood_env(t))
    if ad is None:
        bg_motif(c, t)
        draw_morpheus(c, t)
        draw_halos(c, t)
        draw_hands(c, t)
        draw_items(c, t)
        draw_sparks(c, t)
        draw_header(c, t)
        draw_hook(c, t)
        draw_prices(c, t)
        draw_timer(c, t)
        draw_teaser(c, t)
        draw_outro(c, t)
        caption_layer(c, t)
    else:
        u, bt, B = ad
        fade = 1 - fx.smooth(u / 0.4) * (1 - fx.smooth((u - (2 * banner.RAMP + banner.PRE + B + banner.POST - 0.4)) / 0.4))
        if fade > 0.01:
            tmp = c.copy()
            draw_header(tmp, t)
            c[:] = c * (1 - fade) + tmp * fade
        draw_ad_scene(c, t, u, bt, B, header_a=fade)
    if raw:
        return c
    out = np.clip(c, 0, 255).astype(np.uint8)
    return post_fx(out, t) if ad is None else out


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
