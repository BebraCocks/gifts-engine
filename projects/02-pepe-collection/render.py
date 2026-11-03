"""02 · Pepe — night-swamp world, one continuous camera, live Lottie gifts, RubUp in the centre.

Frame = pure function of content time t (seconds). Times come from voice (timeline.py / events.py).
    python -B render.py --frames 0,600,1100         (content frames, no ad)
    python -B render.py --video build/video_only.mp4  (only after «собирай», via engine/tools/build.py)
"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import banner
import frames
import fx
import gifts_api
import lottie
import config
from timeline import DUR, ON, END
from events import AD_STOP

W, H, FPS = 1080, 1920, 60
HW, HH = W // 2, H // 2
SHUTTER = 0.5 / FPS
BR = banner.Breaks([AD_STOP], cy=H / 2)

# ================================================================ palette
ZENITH = np.array([3, 7, 14], np.float32)
HORIZON = np.array([20, 50, 50], np.float32)
FOG = np.array([22, 52, 50], np.float32)
WATER = np.array([3, 13, 13], np.float32)
TREES = np.array([5, 15, 15], np.float32)
PAD = np.array([38, 92, 44], np.float32)
PAD_DARK = np.array([18, 50, 26], np.float32)
MOONLIGHT = np.array([225, 240, 215], np.float32)
FIREFLY = (200, 255, 120)
STAR_C = np.array([255, 222, 90], np.float32)
MINT = (170, 228, 190)
PEPE = (120, 205, 85)
INK = (20, 22, 20)
PAPER = (246, 238, 214)

MOON = np.array([0.155, 0.255, 1.0]); MOON /= np.linalg.norm(MOON)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def v3(*a):
    return np.array(a, float)


# ================================================================ gifts in the world
SIZE = 2.0


class Gift:
    def __init__(self, gift, model, pos, hover=0.0, size=SIZE, pad=1.25, phase=None):
        self.anim = str(gifts_api.model_file(gift, model, 'json'))
        self.dur = lottie.info(self.anim)['duration']
        self.pos, self.hover, self.size, self.pad = v3(*pos), hover, size, pad
        self.phase = phase or (lambda t, d=self.dur: t % d)

    def center(self, t):
        return self.pos + v3(0, self.hover + self.size * 0.38, 0)

    def look(self):
        return self.pos + v3(0, self.hover + 0.95 * self.size / SIZE, 0)


def cyc(t, at, c_at, d):
    """Lottie phase such that cycle time c_at happens at content time `at`."""
    return (t - at + c_at) % d


# Story events (content seconds), from the estimated word times of the selected takes.
STAR_T0, STAR_T1 = 18.65, 19.60          # Happy Pepe's star flies to Pepe Dream
Z_T0 = 22.85                             # Zzz rise from Pepe Dream -> Plush Pepe
OPEN_T = 30.15                           # «Открой» -> Turtles cycle starts
SLIME_T0 = 34.80                         # slime column rises to Meme God
DIVE_T0 = 39.45                          # dive to Pepe Bag
PAINT_T0 = 42.95                         # spray paint -> Pepe Paws
SCARE_T = 45.10                          # spider scares the cat («но стоит»)
JUMP_T0 = 48.35                          # cat jumps -> Boiled Pepe
FEELS_T = 51.27                          # final «Feels good, man»

HP = Gift('Kissed Frog', 'Happy Pepe', (0, 0, 0), phase=lambda t: cyc(t, 18.60, 1.22, 2.5))
PD = Gift("Durov's Glasses", 'Pepe Dream', (7.5, 0, 9), hover=0.55, pad=1.15, phase=lambda t: cyc(t, STAR_T1, 0.55, 3.0))
PP = Gift('Resistance Dog', 'Plush Pepe', (3, 0, 17))
TU = Gift('Heart Locket', 'Turtles', (-3.5, 0, 24), phase=lambda t: 0.0 if t < OPEN_T else (t - OPEN_T) % 3.0)
MG = Gift('Spring Basket', 'Meme God', (-2, 10.5, 33), pad=0)
PB = Gift('Loot Bag', 'Pepe Bag', (4, 0, 40), phase=lambda t: cyc(t, 42.85, 0.6, 3.0))
PW = Gift('Scared Cat', 'Pepe Paws', (11, 0, 46), phase=lambda t: cyc(t, SCARE_T, 1.17, 2.333))
BP = Gift('Easter Egg', 'Boiled Pepe', (5.5, 0, 53), phase=lambda t: cyc(t, 49.60, 0.9, 3.0))
MAIN = [HP, PD, PP, TU, MG, PB, PW, BP]
EXTRA = [Gift('Ice Cream', 'Cryo Pepe', (-6.5, 0, 9), size=1.6, pad=1.0),
         Gift('Jester Hat', 'Pepe Hop', (13.5, 0, 15), size=1.6, pad=1.0),
         Gift('Tama Gadget', 'Pepe Feels', (-8.5, 0, 18), size=1.6, pad=1.0),
         Gift('Party Sparkler', 'Le Pepe', (14.5, 0, 3), size=1.6, pad=1.0),
         Gift('Jack-in-the-Box', 'Shy Pepe', (-1.5, 0, 36), size=1.6, pad=1.0),
         Gift('Pool Float', 'Pool Pepe', (9.5, 0, 31), size=1.6, pad=1.0)]
for k, g in enumerate(EXTRA):
    g.phase = (lambda t, d=g.dur, o=k * 0.37: (t + o) % d)
ALL = MAIN + EXTRA

rng = np.random.default_rng(20261103)
PADS = [(g.pos[0], g.pos[2] + 0.05, g.pad, rng.uniform(0, 6.28)) for g in ALL if g.pad]
for _ in range(170):
    x, z = rng.uniform(-14, 20), rng.uniform(-8, 64)
    if all((x - a) ** 2 + (z - b) ** 2 > (r + 0.9) ** 2 for a, b, r, _ in PADS):
        PADS.append((x, z, rng.uniform(0.35, 0.9), rng.uniform(0, 6.28)))
PADS = np.array(PADS, np.float32)

STARS = rng.normal(size=(900, 3)); STARS[:, 1] = np.abs(STARS[:, 1]) + 0.02
STARS /= np.linalg.norm(STARS, axis=1, keepdims=True)
STAR_MAG = rng.uniform(0.25, 1.0, 900) ** 2.5
STAR_PHASE = rng.uniform(0, 6.28, 900)
NF = 320
FIREFLIES = np.column_stack([rng.uniform(-12, 18, NF), rng.uniform(0.25, 3.4, NF), rng.uniform(-6, 60, NF)])
FIREFLIES[:40, 1] = rng.uniform(6, 13, 40)                  # a few high ones near Meme God
FIREFLIES[:40, 2] = rng.uniform(24, 38, 40)
FF_PHASE = rng.uniform(0, 6.28, (NF, 4))


def reed_cluster(cx, cz, n, hmin, hmax, seed):
    r = np.random.default_rng(seed)
    return [(cx + r.uniform(-0.45, 0.45), cz + r.uniform(-0.3, 0.3), r.uniform(hmin, hmax),
             r.uniform(-0.25, 0.25), r.uniform(0, 6.28), r.random() < 0.55) for _ in range(n)]


BACK_REEDS = sum((reed_cluster(x, z, 9, 1.0, 2.4, i) for i, (x, z) in enumerate(
    [(-4.5, 6), (3.5, 13), (12, 15.5), (-1.5, 14), (10.5, 5), (-7, 2), (14, 22), (5, 20), (-8, 27), (8, 26),
     (-5, 33), (10, 36), (0, 47), (15, 50), (-2, 56), (9, 58), (16, 41)])), [])
FRONT_REEDS = sum((reed_cluster(x, z, 7, 1.6, 3.2, 50 + i) for i, (x, z) in enumerate(
    [(-2.9, -3.6), (2.6, -2.2), (5.2, 1.8), (2.4, 4.4), (10.6, 7.6), (0.6, 13.0), (-0.8, 19.5), (-5.8, 21.0),
     (7.2, 37.0), (8.2, 42.6), (14.2, 43.0), (3.2, 48.0), (8.0, 50.0)])), [])


def treeline(az):
    return (0.03 + 0.016 * np.sin(az * 7 + 1) + 0.01 * np.sin(az * 23 + 2)
            + 0.006 * np.sin(az * 61) + 0.004 * np.abs(np.sin(az * 140)))


# ================================================================ comic page (hook)
PG0 = v3(0, 3.2, -10)                    # page centre in the world, faces the camera (-z)
PAGE_W, PAGE_H = 1200, 2000
PAGE_WORLD_H = 4.0                       # 1 page px = 0.002 world units


def page_y(py):
    return (1000 - py) * PAGE_WORLD_H / PAGE_H


def inked(im, outline=10):
    im = im.convert('RGBA')
    a = im.split()[3]
    rgb = im.convert('RGB').quantize(6).convert('RGB')
    big = a.filter(ImageFilter.MaxFilter(outline * 2 + 1))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', im.size, INK + (255,)), (0, 0), big)
    out.paste(rgb, (0, 0), a)
    return out


def text_sprite(text, size, weight='Heavy', fill=INK, stroke=0, stroke_fill=None):
    f = fx.font(weight, size)
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    l, t_, r, b = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 8, b - t_ + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t_), text, font=f, fill=fill, stroke_width=stroke,
                            stroke_fill=stroke_fill or fill)
    return im


def balloon(text, size=74, pad=(56, 44)):
    ts = text_sprite(text, size, 'Heavy')
    w, h = ts.width + pad[0] * 2, ts.height + pad[1] * 2
    im = Image.new('RGBA', (w + 20, h + 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(w * 0.30, h - 10), (w * 0.22, h + 95), (w * 0.48, h - 10)], fill=INK)
    d.polygon([(w * 0.32 + 6, h - 20), (w * 0.24 + 10, h + 72), (w * 0.46, h - 20)], fill=(255, 255, 255))
    d.ellipse([4, 4, w + 4, h + 4], fill=INK)
    d.ellipse([12, 12, w - 4, h - 4], fill=(255, 255, 255))
    d.polygon([(w * 0.32 + 6, h - 24), (w * 0.24 + 12, h + 66), (w * 0.46, h - 24)], fill=(255, 255, 255))
    im.alpha_composite(ts, (pad[0] + 4, pad[1] + 4))
    return im


def halftone(w, h, color, step=22, rmax=6.5, seed=0):
    im = Image.new('RGBA', (w, h), color + (255,))
    d = ImageDraw.Draw(im)
    for y in range(0, h, step):
        for x in range((y // step) % 2 * step // 2, w, step):
            r = rmax * (0.45 + 0.55 * y / h)
            d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * 0.86) for c in color) + (255,))
    return im


PANELS = [(40, 40, 1160, 620), (40, 650, 1160, 1380), (40, 1410, 1160, 1960)]


def build_page_base():
    im = Image.new('RGBA', (PAGE_W, PAGE_H), PAPER + (255,))
    grain = np.random.default_rng(5).normal(0, 6, (PAGE_H, PAGE_W, 1))
    arr = np.clip(np.asarray(im, np.float32)[..., :3] + grain, 0, 255).astype(np.uint8)
    im = Image.fromarray(np.dstack([arr, np.full((PAGE_H, PAGE_W), 255, np.uint8)]), 'RGBA')
    fills = [(214, 236, 196), (250, 222, 160), (205, 222, 240)]
    for (x0, y0, x1, y1), c in zip(PANELS, fills):
        im.alpha_composite(halftone(x1 - x0, y1 - y0, c), (x0, y0))
        ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], outline=INK, width=12)
    d = ImageDraw.Draw(im)
    cap = text_sprite('МЭТТ ФУРИ · КОМИКС', 46, 'Heavy')
    im.alpha_composite(cap, (600 - cap.width // 2, 92))
    # panel C: an old monitor frame
    d.rounded_rectangle([150, 1520, 1050, 1900], radius=34, fill=(32, 36, 44), outline=INK, width=10)
    d.rectangle([186, 1556, 1014, 1864], fill=(236, 240, 228))
    d.rectangle([186, 1556, 1014, 1604], fill=(120, 150, 110))
    lab = text_sprite('4chan  /b/', 34, 'Bold', fill=(250, 250, 250))
    im.alpha_composite(lab, (600 - lab.width // 2, 1560))
    return im


PAGE_BASE = build_page_base()
FROG_SRC = Image.open(gifts_api.original_png('Plush Pepe', 512)).convert('RGBA')
FROG_INK = inked(FROG_SRC.resize((560, 560), Image.LANCZOS), 9)
FACE = inked(Image.open(gifts_api.model_png('Kissed Frog', 'Happy Pepe', 256)).convert('RGBA').resize((120, 120), Image.LANCZOS), 4)
S2005 = text_sprite('2005', 230, 'Heavy', fill=INK)
S2008 = text_sprite('2008', 120, 'Heavy', fill=INK)
BALLOON = balloon('Feels good, man')
FACE_SLOTS = [(250 + (k % 6) * 132 + (k // 6 % 2) * 30, 1640 + (k // 6) * 74) for k in range(18)]
FACE_T = [7.40 + 0.055 * k + 0.02 * math.sin(k * 3.1) for k in range(18)]


def stamp(x):
    """0 -> big and transparent, 1 -> settled; with a small overshoot."""
    if x <= 0:
        return 0.0, 1.6
    a = min(1.0, x / 0.12)
    s = 1.0 + 0.6 * math.exp(-x * 9) * math.cos(x * 14)
    return a, max(0.2, s)


def paste_scaled(dst, spr, cx, cy, s, alpha=1.0):
    if alpha <= 0.01 or s <= 0.01:
        return
    w, h = max(1, int(spr.width * s)), max(1, int(spr.height * s))
    im = spr.resize((w, h), Image.BILINEAR)
    if alpha < 0.999:
        a = np.asarray(im.split()[3], np.float32) * alpha
        im.putalpha(Image.fromarray(a.astype(np.uint8)))
    dst.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


def page_image(t):
    im = PAGE_BASE.copy()
    a, s = stamp(t - 0.40)
    paste_scaled(im, S2005, 600, 340, s, a)
    # panel B: the frog is being drawn (wipe from top), then the balloon pops on «Feels»
    reveal = ease((t - 1.40) / 1.25)
    if reveal > 0:
        frog = FROG_INK.copy()
        hh = frog.height
        edge = reveal * (hh + 60)
        m = np.clip((edge - np.arange(hh)) / 60.0, 0, 1)[:, None] * np.ones((1, frog.width))
        al = np.asarray(frog.split()[3], np.float32) * m
        frog.putalpha(Image.fromarray(al.astype(np.uint8)))
        bob = 6 * math.sin(max(0, t - 3.6) * 9) * math.exp(-max(0, t - 3.6) * 2) if t > 3.6 else 0
        im.alpha_composite(frog, (int(600 - frog.width / 2 - 140), int(1380 - 40 - frog.height + bob)))
    if t > 4.38:
        x = t - 4.38
        s = fx.ease_out_back(min(1, x / 0.28), 2.2)
        paste_scaled(im, BALLOON, 690, 800, max(0.05, s * 0.92), min(1, x / 0.08))
    a, s = stamp(t - 6.20)
    paste_scaled(im, S2008, 600, 1470, s, a)
    for (x, y), t0 in zip(FACE_SLOTS, FACE_T):
        if t > t0:
            s = fx.ease_out_back(min(1, (t - t0) / 0.18), 2.6)
            paste_scaled(im, FACE, x, y, max(0.05, s * 0.62), 1.0)
    return im


def page_center(t):
    e = ease((t - 8.25) / 1.15)
    return PG0 + v3(0.6 * e, 10.0 * e * e, 2.5 * e), math.radians(28 * e * e)


# ================================================================ camera keyframes
def K(t, C, T, roll=0.0, fov=50.0, flow=1.0):
    return (t, v3(*C), v3(*T), roll, fov, flow)


HPL, PDL, PPL, TUL, MGL, PBL, PWL, BPL = (g.look() for g in MAIN)
P = PG0
KEYS = [
    K(0.00, P + v3(0.10, 0.62, -3.35), P + v3(0, 0.62, 0), 2.0, 50, 0.3),
    K(1.25, P + v3(0.04, 0.58, -3.15), P + v3(0, 0.58, 0), 0.6, 50),
    K(2.35, P + v3(-0.06, 0.02, -3.55), P + v3(0, 0.0, 0), -1.0, 50),
    K(4.15, P + v3(0.0, -0.02, -3.3), P + v3(0, -0.02, 0), -0.3, 50, 0.3),
    K(4.62, P + v3(0.14, 0.14, -2.55), P + v3(0.14, 0.14, 0), -3.0, 50),
    K(5.55, P + v3(0.06, 0.08, -2.72), P + v3(0.06, 0.08, 0), -2.0, 50, 0.4),
    K(6.35, P + v3(0, -1.36, -3.35), P + v3(0, -1.38, 0), 1.5, 50),
    K(8.05, P + v3(0, -1.30, -3.70), P + v3(0, -1.31, 0), 0.5, 50, 0.4),
    K(8.55, P + v3(0, -1.0, -4.9), P + v3(0, -0.7, 0), -2.0, 52),
    K(9.55, (-1.8, 7.2, -13.5), (2.5, 0, 8), -6.0, 56),
    K(12.05, (-0.8, 6.4, -11.0), (2.5, 0, 6), -2.0, 54, 0.5),
    K(12.95, (-0.3, 1.35, -6.5), HPL, 0.8, 50),
    K(13.30, (-0.25, 1.25, -6.2), HPL, 0.5, 50, 0.4),
    K(18.60, (-0.12, 1.15, -5.3), HPL, 0.3, 50, 0.3),
    K(19.15, (2.8, 2.6, -1.0), (4.5, 2.5, 5.0), -17.0, 59),
    K(20.15, PD.pos + v3(-2.0, 1.3, -6.6), PDL, -1.0, 51, 0.5),
    K(22.85, PD.pos + v3(-1.7, 1.2, -5.9), PDL, 0.5, 50, 0.3),
    K(23.45, (5.2, 3.3, 6.0), (5.0, 4.2, 12.0), 8.0, 55),
    K(24.05, PP.pos + v3(0.3, 1.15, -5.3), PPL, 1.0, 50, 0.5),
    K(27.05, PP.pos + v3(0.2, 1.10, -4.7), PPL, -0.5, 50, 0.4),
    K(28.35, TU.pos + v3(1.2, 0.85, -6.6), TUL, -2.0, 48),
    K(29.90, TU.pos + v3(0.15, 0.80, -5.4), TUL, -0.5, 47, 0.2),
    K(30.30, TU.pos + v3(0.15, 0.80, -5.35), TUL, -0.5, 47, 0.2),
    K(30.75, TU.pos + v3(0.10, 0.88, -4.6), TUL + v3(0, 0.15, 0), 2.0, 50),
    K(31.65, TU.pos + v3(0.0, 0.95, -5.3), TUL + v3(0, 0.10, 0), 0.0, 52, 0.5),
    K(34.80, TU.pos + v3(-0.1, 0.95, -5.6), TUL, -0.5, 52, 0.3),
    K(35.30, (-3.2, 5.0, 21.0), (-2.6, 9.0, 30.0), 14.0, 58),
    K(35.90, MG.pos + v3(0.4, -0.5, -5.6), MGL, 3.0, 52, 0.5),
    K(39.40, MG.pos + v3(0.3, -0.5, -5.1), MGL, 0.0, 50, 0.3),
    K(39.90, (1.5, 5.0, 31.5), (4.0, 1.0, 40.0), -12.0, 62),
    K(40.35, PB.pos + v3(0.3, 1.15, -5.3), PBL, 0.0, 50, 0.5),
    K(42.90, PB.pos + v3(0.2, 1.10, -4.8), PBL, 0.5, 50, 0.3),
    K(43.30, (7.5, 1.6, 37.5), (9.0, 1.2, 44.0), -14.0, 56),
    K(43.70, PW.pos + v3(0.3, 1.15, -5.3), PWL, -1.0, 50, 0.5),
    K(48.30, PW.pos + v3(0.2, 1.10, -4.7), PWL, 0.5, 50, 0.3),
    K(48.75, (8.5, 1.8, 44.0), (7.0, 1.0, 50.0), 10.0, 54),
    K(49.20, BP.pos + v3(0.3, 1.15, -5.3), BPL, 0.0, 50, 0.5),
    K(51.10, BP.pos + v3(0.25, 1.12, -4.8), BPL, 0.0, 50, 0.3),
    K(51.95, (12.2, 4.0, 52.0), BPL, -8.0, 54),
    K(DUR, (7.5, 7.2, 63.0), (3.5, 1.2, 36.0), -3.0, 56, 0.4),
]
KT = [k[0] for k in KEYS]


def hermite(t, idx):
    if t <= KT[0]:
        return np.asarray(KEYS[0][idx], float)
    if t >= KT[-1]:
        return np.asarray(KEYS[-1][idx], float)
    i = max(j for j in range(len(KT) - 1) if KT[j] <= t)
    t0, t1 = KT[i], KT[i + 1]
    dt = t1 - t0

    def tan(j):
        a, b = max(j - 1, 0), min(j + 1, len(KT) - 1)
        m = (np.asarray(KEYS[b][idx], float) - np.asarray(KEYS[a][idx], float)) / max(KT[b] - KT[a], 1e-6)
        return m * KEYS[j][5]
    p1, p2 = np.asarray(KEYS[i][idx], float), np.asarray(KEYS[i + 1][idx], float)
    m1, m2 = tan(i) * dt, tan(i + 1) * dt
    u = (t - t0) / dt
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2


SHAKES = [(4.38, 0.035, 9), (19.60, 0.05, 8), (31.35, 0.07, 8), (SCARE_T, 0.06, 11), (JUMP_T0, 0.05, 9)]


def bez(p0, p1, p2, u):
    return (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u * u * p2


S0 = HP.center(0) + v3(SIZE * 0.20, SIZE * 0.03, -0.15)
S_CTRL = v3(2.4, 3.6, 2.2)


def star_pos(t):
    u = ease((t - STAR_T0) / (STAR_T1 - STAR_T0)) if t > STAR_T0 else 0.0
    return bez(S0, S_CTRL, PD.center(STAR_T1) + v3(0, 0.05, -0.2), u)


def camera(t):
    C, T = hermite(t, 1), hermite(t, 2)
    roll, fov = float(hermite(t, 3)), float(hermite(t, 4))
    w_star = ease((t - (STAR_T0 - 0.1)) / 0.3) * (1 - ease((t - (STAR_T1 - 0.2)) / 0.4))
    if w_star > 0:
        T = T + (star_pos(min(t + 0.06, STAR_T1)) - T) * w_star * 0.6
    drift = v3(0.03 * math.sin(t * 1.3), 0.025 * math.sin(t * 1.7 + 1), 0)
    for t0, amp, f in SHAKES:
        if t0 <= t < t0 + 1.0:
            k = amp * math.exp(-(t - t0) * 6)
            drift = drift + v3(k * math.sin((t - t0) * f * 6.28), k * math.sin((t - t0) * f * 5.1 + 1), 0)
    return C + drift, T + drift * 0.5, math.radians(roll + 0.6 * math.sin(t * 0.9)), fov


def basis(C, T, roll):
    f = T - C; f = f / np.linalg.norm(f)
    r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r)
    u = np.cross(f, r)
    cr, sr = math.cos(roll), math.sin(roll)
    return f, cr * r + sr * u, -sr * r + cr * u


class Cam:
    def __init__(self, t):
        self.C, T, self.roll, fov = camera(t)
        self.f, self.r, self.u = basis(self.C, T, self.roll)
        self.F = (H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, Pw):
        d = np.asarray(Pw, float) - self.C
        z = d @ self.f
        zz = np.maximum(z, 1e-3)
        return W / 2 + self.F * (d @ self.r) / zz, H / 2 - self.F * (d @ self.u) / zz, z


# ================================================================ background (per pixel, half res)
_gx, _gy = np.meshgrid((np.arange(HW) + 0.5) * 2 - W / 2, (np.arange(HH) + 0.5) * 2 - H / 2)


def sky(dx, dy, dz):
    n = np.sqrt(dx * dx + dy * dy + dz * dz)
    e = dy / n
    k = np.clip(e / 0.55, 0, 1); k = (k * k * (3 - 2 * k))[..., None]
    col = HORIZON + (ZENITH - HORIZON) * k
    m = np.clip((dx * MOON[0] + dy * MOON[1] + dz * MOON[2]) / n, 0, 1)
    col = col + MOONLIGHT * (0.10 * m ** 40 + 0.05 * m ** 6)[..., None]
    tree = e < treeline(np.arctan2(dx, dz))
    return np.where(tree[..., None], TREES + (FOG - TREES) * 0.25, col)


def background(cam, t):
    a, b = _gx / cam.F, _gy / cam.F
    dx = cam.f[0] + a * cam.r[0] - b * cam.u[0]
    dy = cam.f[1] + a * cam.r[1] - b * cam.u[1]
    dz = cam.f[2] + a * cam.r[2] - b * cam.u[2]
    out = sky(dx, dy, dz)
    water = dy < -1e-4
    if water.any():
        wx, wy, wz = dx[water], dy[water], dz[water]
        tt = -cam.C[1] / wy
        x, z = cam.C[0] + tt * wx, cam.C[2] + tt * wz
        n = np.sqrt(wx * wx + wy * wy + wz * wz)
        dist = tt * n
        px = 0.045 * (np.sin(1.3 * x + 2.1 * t) + 0.6 * np.sin(2.9 * z - 1.4 * t + 0.7 * x))
        pz = 0.07 * (np.sin(1.7 * z + 1.6 * t) + 0.5 * np.sin(3.7 * x + 2.3 * t))
        att = np.clip(4.0 / (dist + 4.0), 0.15, 1)
        rx, ry, rz = wx / n + px * att, -wy / n, wz / n + pz * att
        refl = sky(rx[None], ry[None], rz[None])[0]
        m = np.clip((rx * MOON[0] + ry * MOON[1] + rz * MOON[2]) / np.sqrt(rx * rx + ry * ry + rz * rz), 0, 1)
        glint = (0.75 * m ** 2500 + 0.09 * m ** 200)[:, None] * MOONLIGHT
        fres = (0.35 + 0.55 * (1 - np.abs(wy / n)) ** 4)[:, None]
        col = WATER + refl * fres + glint
        aa = 0.012 * dist + 0.01
        xmin, xmax, zmin, zmax = x.min(), x.max(), z.min(), z.max()
        for cx, cz, rad, notch in PADS:
            if cx + rad < xmin or cx - rad > xmax or cz + rad < zmin or cz - rad > zmax:
                continue
            ddx, ddz = x - cx, z - cz
            d = np.sqrt(ddx * ddx + ddz * ddz)
            near = d < rad + aa
            if not near.any():
                continue
            dn = d[near]
            ang = np.arctan2(ddz[near], ddx[near]) - notch
            cut = np.clip((np.cos(ang) - 0.965) / 0.02, 0, 1) * np.clip(dn / (rad * 0.25), 0, 1)
            cover = np.clip((rad - dn) / aa[near], 0, 1) * (1 - cut)
            vein = 0.5 + 0.5 * np.cos(ang * 9)
            rim = np.clip((dn / rad - 0.82) / 0.18, 0, 1)
            pc = PAD_DARK + (PAD - PAD_DARK) * (0.55 + 0.25 * vein[:, None] + 0.35 * rim[:, None])
            spec = MOONLIGHT * (0.12 * np.clip(1 - dn / rad, 0, 1))[:, None]
            c = col[near]
            col[near] = c + (pc + spec - c) * cover[:, None]
        fog = (1 - np.exp(-dist / 22.0))[:, None] * 0.85
        out[water] = col + (FOG - col) * fog
    return out


# ================================================================ compositing helpers
_cache = {}


def glow(radius, color, core=0.6):
    key = ('g', int(radius), tuple(int(c) for c in color), core)
    if key not in _cache:
        r = max(2, int(radius))
        y, x = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(x * x + y * y) / r
        g = np.clip(1 - d, 0, 1) ** 2.2 * (1 - core) + np.exp(-(d / 0.18) ** 2) * core
        _cache[key] = (g[..., None] * (np.asarray(color, np.float32) / 255.0)).astype(np.float32)
        if len(_cache) > 600:
            _cache.clear()
    return _cache[key]


def star_sprite(size, rot):
    size = max(8, int(size))
    key = ('s', size, int(rot * 20) % 126)
    if key not in _cache:
        s = size * 4
        im = Image.new('L', (s, s), 0)
        pts = []
        for k in range(10):
            rr = s * (0.48 if k % 2 == 0 else 0.21)
            a = rot + k * math.pi / 5 - math.pi / 2
            pts.append((s / 2 + rr * math.cos(a), s / 2 + rr * math.sin(a)))
        ImageDraw.Draw(im).polygon(pts, fill=255)
        _cache[key] = np.asarray(im.resize((size, size), Image.LANCZOS), np.float32)[..., None] / 255.0
    return _cache[key]


def add(canvas, spr, cx, cy, gain=1.0):
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    canvas[ya:yb, xa:xb] += spr[ya - y0:yb - y0, xa - x0:xb - x0] * (255.0 * gain)


def blend(canvas, rgba, x0, y0, alpha=1.0):
    h, w = rgba.shape[:2]
    x0, y0 = int(round(x0)), int(round(y0))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb or alpha <= 0.003:
        return
    s = rgba[ya - y0:yb - y0, xa - x0:xb - x0]
    a = s[..., 3:4] * (alpha / 255.0)
    c = canvas[ya:yb, xa:xb]
    c += (s[..., :3] - c) * a


def place(canvas, img, sx, sy, scale, angle, alpha=1.0, flip=False, tint=None):
    """Draw RGBA PIL `img` centred at (sx, sy), scaled and rotated (radians, CCW), clipped to the frame."""
    w, h = img.size
    ca, sa = math.cos(angle), math.sin(angle)
    hw, hh = w * scale / 2, h * scale / 2
    ex, ey = abs(ca) * hw + abs(sa) * hh, abs(sa) * hw + abs(ca) * hh
    ox, oy = int(max(0, math.floor(sx - ex))), int(max(0, math.floor(sy - ey)))
    bx, by = int(min(W, math.ceil(sx + ex))), int(min(H, math.ceil(sy + ey)))
    if bx - ox < 2 or by - oy < 2:
        return
    s = scale
    a_, b_ = ca / s, -sa / s
    d_, e_ = sa / s, ca / s
    c_ = (ca * (ox - sx) - sa * (oy - sy)) / s + w / 2
    f_ = (sa * (ox - sx) + ca * (oy - sy)) / s + h / 2
    if flip:
        d_, e_, f_ = -d_, -e_, h - f_
    out = img.transform((bx - ox, by - oy), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BILINEAR)
    arr = np.asarray(out, np.float32)
    if tint is not None:
        arr = arr.copy(); arr[..., :3] *= tint[0]; arr[..., 3] *= tint[1]
    blend(canvas, arr, ox, oy, alpha)


def lottie_img(g, t, px):
    q = int(min(1024, max(96, math.ceil(px / 96) * 96)))
    return lottie.frame(g.anim, g.phase(t), q)


def draw_gift(canvas, cam, g, t, scale=(1.0, 1.0)):
    c = g.center(t)
    if g is PD:
        c = c + v3(0, 0.06 * math.sin(t * 2.4) - 0.1 * squash(t), 0)
    sx, sy, z = cam.project(c)
    if z < 0.3:
        return
    px = cam.F * g.size / z
    if px < 6 or not (-px < sx < W + px and -px < sy < H + px):
        return
    im = lottie_img(g, t, px)
    if scale != (1.0, 1.0):
        im = im.resize((max(4, int(im.width * scale[0])), max(4, int(im.height * scale[1]))), Image.BILINEAR)
    s = px / lottie_img(g, t, px).width
    if g.pad:                                   # reflection in the water plane
        mirror = c.copy(); mirror[1] = -c[1]
        rx, ry, rz = cam.project(mirror)
        if rz > 0.3:
            place(canvas, im, rx, ry, s, cam.roll, 1.0, flip=True, tint=(0.55, 0.36))
    place(canvas, im, sx, sy, s, cam.roll)


def squash(t):
    return fx.bump(min(1.0, max(0.0, (t - STAR_T1) / 0.6)), 3.0, 5.0) if t >= STAR_T1 else 0.0


def draw_reeds(canvas, cam, reeds, t, color, wind=1.0, zmin=-1e9, zmax=1e9):
    layer = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(layer)
    for bx, bz, h, lean, ph, head in reeds:
        if abs(bz - cam.C[2]) > 40:
            continue
        sway = lean + 0.06 * wind * math.sin(t * 1.6 + ph)
        base = v3(bx, 0.0, bz); top = v3(bx + sway, h, bz)
        x0, y0, z0 = cam.project(base); x1, y1, z1 = cam.project(top)
        if z0 < 0.25 or z1 < 0.25 or not (zmin <= z0 < zmax):
            continue
        if max(x0, x1) < -50 or min(x0, x1) > W + 50:
            continue
        wpx = max(1.0, cam.F * 0.035 / z0)
        mid = cam.project(base + (top - base) * 0.55 + v3(sway * 0.3, 0, 0))
        d.line([(x0, y0), (mid[0], mid[1]), (x1, y1)], fill=255, width=int(wpx))
        if head:
            hc = cam.project(base + (top - base) * 0.82)
            hw = max(2, cam.F * 0.06 / z0); hh = max(4, cam.F * 0.34 / z0)
            d.ellipse([hc[0] - hw, hc[1] - hh / 2, hc[0] + hw, hc[1] + hh / 2], fill=255)
    box = layer.getbbox()
    if not box:
        return
    x0, y0, x1, y1 = box
    a = np.asarray(layer.crop(box), np.float32)[..., None] / 255.0
    c = canvas[y0:y1, x0:x1]
    c += (np.asarray(color, np.float32) - c) * a


# ================================================================ particles (carriers between gifts)
def particles(canvas, cam, t):
    def world_glow(p, r_world, color, gain, core=0.6):
        x, y, z = cam.project(p)
        if z > 0.3 and -100 < x < W + 100 and -100 < y < H + 100:
            add(canvas, glow(max(2, cam.F * r_world / z), color, core), x, y, gain)

    # star: trail, body, impact
    if STAR_T0 - 0.1 <= t <= STAR_T1 + 0.8:
        k = np.arange(0, 120)
        taus = STAR_T0 + k * 0.009
        for tau in taus[(taus <= min(t, STAR_T1)) & (taus > t - 0.55)]:
            age = (t - tau) / 0.55
            j = v3(math.sin(tau * 91.7), math.sin(tau * 53.3 + 1), math.sin(tau * 71.1 + 2)) * 0.06 * (1 + 2 * age)
            world_glow(star_pos(tau) + j + v3(0, -0.25 * age * age, 0), 0.05 * (1 - age), (255, 225, 110),
                       (1 - age) ** 1.5 * 0.55, 0.7)
        if t < STAR_T1 + 0.05:
            x, y, z = cam.project(star_pos(t))
            grow = ease((t - (STAR_T0 - 0.08)) / 0.12)
            if z > 0.3 and grow > 0:
                size = cam.F * 0.42 / z * grow
                add(canvas, glow(size * 1.3, (255, 210, 80), 0.25), x, y, 0.55)
                add(canvas, star_sprite(size, t * 9.0) * STAR_C / 255.0, x, y, 1.0)
        if t >= STAR_T1:
            age = (t - STAR_T1) / 0.7
            if age < 1:
                cx, cy, cz = cam.project(PD.center(STAR_T1))
                if cz > 0.3:
                    add(canvas, glow(cam.F * (0.9 + 0.8 * age) / cz, (255, 230, 140), 0.1), cx, cy, (1 - age) ** 2 * 0.8)
                for i in range(22):
                    a = i / 22 * 6.283 + 0.4
                    rr = (0.4 + 1.5 * ease(age)) * (0.8 + 0.3 * math.sin(i * 7.1))
                    p = PD.center(STAR_T1) + v3(math.cos(a) * rr, math.sin(a) * rr * 0.8 - 0.4 * age * age, -0.3)
                    x, y, z = cam.project(p)
                    if z > 0.3:
                        add(canvas, star_sprite(cam.F * 0.12 / z * (1 - age), a) * STAR_C / 255.0, x, y, 1 - age)
    # Zzz: rise from Pepe Dream and lead the camera up and over to Plush Pepe
    if Z_T0 <= t <= Z_T0 + 1.4:
        for i in range(3):
            u = (t - Z_T0 - i * 0.14) / 1.15
            if 0 < u < 1:
                p = bez(PD.center(t) + v3(0.4, 0.8, 0), v3(6.0, 4.2, 9.5), v3(4.4, 4.0, 13.5), ease(u)) + v3(0.4 * i, 0.3 * i, 0)
                x, y, z = cam.project(p)
                if z > 0.3:
                    spr = Z_SPR[i]
                    sc = cam.F * (0.55 - 0.12 * i) / z / spr.height
                    place(canvas, spr, x, y, sc, cam.roll + 0.3 * math.sin(t * 5 + i), alpha=min(1, u * 6) * (1 - ease((u - 0.75) / 0.25)))
    # slime column: from the open manhole up to Meme God
    if SLIME_T0 - 0.1 <= t <= SLIME_T0 + 1.6:
        for i in range(60):
            t0 = SLIME_T0 - 0.1 + i * 0.016
            u = (t - t0) / 0.95
            if 0 < u < 1:
                p = bez(TU.center(t) + v3(0, 0.3, 0), v3(-3.4, 6.5, 26.0), MG.center(t) + v3(0, -1.0, -0.6), ease(u))
                p = p + v3(0.18 * math.sin(i * 2.3 + t * 6), 0.15 * math.sin(i * 1.7), 0.18 * math.cos(i * 3.1))
                world_glow(p, 0.16 * (1 - 0.6 * u), (120, 255, 90), 0.75 * (1 - u ** 3), 0.5)
    # spray paint: from the bag towards the cat
    if PAINT_T0 - 0.05 <= t <= PAINT_T0 + 1.1:
        cols = [(255, 80, 200), (90, 220, 255), (255, 230, 70), (140, 255, 120)]
        for i in range(48):
            t0 = PAINT_T0 + i * 0.012
            u = (t - t0) / 0.75
            if 0 < u < 1:
                p = bez(PB.center(t) + v3(0.3, 0.5, -0.2), v3(8.0, 2.8, 41.0), PW.center(t) + v3(-1.2, 0.6, -0.6), ease(u))
                p = p + v3(0.3 * math.sin(i * 1.9), 0.25 * math.sin(i * 2.7), 0.3 * math.cos(i * 1.3)) * (0.3 + u)
                world_glow(p, 0.11, cols[i % 4], 0.8 * (1 - u ** 2), 0.75)


Z_SPR = [text_sprite('Z', 150, 'Heavy', fill=(170, 90, 255), stroke=6, stroke_fill=(80, 30, 140)) for _ in range(3)]


# ================================================================ one sharp sub-frame
def scene(t):
    cam = Cam(t)
    pc, prot = page_center(t)
    canvas = None
    # the page can fill the frame completely during the hook: skip the world behind it then
    psx, psy, pz = cam.project(pc)
    page_px = cam.F * PAGE_WORLD_H / pz if pz > 0.2 else 0
    s = page_px / PAGE_H
    covered = pz > 0.2 and abs(cam.roll - prot) < 0.2 and (psx - PAGE_W * s / 2 < -30 and psx + PAGE_W * s / 2 > W + 30
                                                        and psy - page_px / 2 < -30 and psy + page_px / 2 > H + 30)
    if covered:
        canvas = np.zeros((H, W, 3), np.float32)
    else:
        bg = background(cam, t)
        canvas = np.asarray(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
        sx, sy, sz = cam.project(cam.C + STARS * 100)
        az = np.arctan2(STARS[:, 0], STARS[:, 2])
        vis = (sz > 0) & (STARS[:, 1] > treeline(az) + 0.01) & (sx > -4) & (sx < W + 4) & (sy > -4) & (sy < H + 4)
        for i in np.nonzero(vis)[0]:
            tw = 0.75 + 0.25 * math.sin(t * 3 + STAR_PHASE[i])
            add(canvas, glow(3 + 3 * STAR_MAG[i], (230, 240, 255), 0.85), sx[i], sy[i], STAR_MAG[i] * tw * 0.9)
        mx, my, mz = cam.project(cam.C + MOON * 100)
        if mz > 0:
            add(canvas, glow(cam.F * 0.18, (190, 220, 200), 0.0), mx, my, 0.35)
            add(canvas, glow(cam.F * 0.045, (255, 255, 240), 0.95), mx, my, 1.0)
        draw_reeds(canvas, cam, BACK_REEDS, t, TREES * 1.1)
        items = []
        for g in ALL:
            z = cam.project(g.center(t))[2]
            if z > 0.3:
                items.append((z, g))
        # front reeds behind the nearest gift are drawn before the gifts (depth order)
        znear = min([z for z, g in items if g in MAIN] or [1e9])
        draw_reeds(canvas, cam, FRONT_REEDS, t, (2, 6, 6), wind=1.4, zmin=znear)
        for z, g in sorted(items, key=lambda it: -it[0]):
            sq = squash(t) if g is PD else 0.0
            draw_gift(canvas, cam, g, t, (1 + 0.16 * sq, 1 - 0.14 * sq) if sq else (1.0, 1.0))
        particles(canvas, cam, t)
        for i, (bx, by, bz) in enumerate(FIREFLIES):
            if abs(bz - cam.C[2]) > 30:
                continue
            ph = FF_PHASE[i]
            p = v3(bx + 0.35 * math.sin(t * 0.7 + ph[0]), by + 0.2 * math.sin(t * 1.1 + ph[1]), bz + 0.35 * math.sin(t * 0.5 + ph[2]))
            x, y, z = cam.project(p)
            if z < 0.5 or not (-60 < x < W + 60 and -60 < y < H + 60):
                continue
            blink = 0.35 + 0.65 * max(0.0, math.sin(t * 2.2 + ph[3])) ** 2
            add(canvas, glow(max(4, cam.F * 0.1 / z), FIREFLY, 0.5), x, y, blink * 1.1)
        draw_reeds(canvas, cam, FRONT_REEDS, t, (2, 6, 6), wind=1.4, zmax=znear)
    if pz > 0.2 and t < 10.0:
        place(canvas, page_image(t), psx, psy, s, cam.roll + prot, alpha=1.0 - ease((t - 9.0) / 0.4))
    return canvas


# ================================================================ screen-space text (crisp, after motion blur)
def card(title, sub, stats):
    tf, sf, nf, df = fx.font('Bold', 92), fx.font('Semibold', 44), fx.font('Semibold', 46), fx.font('Medium', 30)
    im = Image.new('RGBA', (W, 330), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for layer, off, col in ((sh, 4, (0, 0, 0, 170)), (im, 0, None)):
        d = ImageDraw.Draw(layer)
        d.text((W / 2, 60 + off), title, font=tf, fill=col or (255, 255, 255, 255), anchor='mm')
        d.text((W / 2, 145 + off), sub, font=sf, fill=col or MINT + (255,), anchor='mm')
        d.text((W / 2, 220 + off), stats, font=nf, fill=col or PEPE + (255,), anchor='mm')
        d.text((W / 2, 284 + off), 'данные на 03.11.2026', font=df, fill=col or (150, 175, 160, 255), anchor='mm')
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    return np.asarray(Image.alpha_composite(sh, im), np.float32)


def top_title(lines):
    im = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for layer, off, col in ((sh, 4, (0, 0, 0, 180)), (im, 0, None)):
        d = ImageDraw.Draw(layer)
        y = 70
        for text, size, weight, color in lines:
            d.text((W / 2, y + off), text, font=fx.font(weight, size), fill=col or color + (255,), anchor='mm')
            y += size * 1.25
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    return np.asarray(Image.alpha_composite(sh, im), np.float32)


# (sprite, t_in, t_out, dx_out, dy_out) — exit direction opposes the camera move
CARDS = [
    (card('Happy Pepe', 'в подарке Kissed Frog', '80 шт. · 0,5% · от 912,9 TON'), 12.95, 18.55, -520, 0),
    (card('Pepe Dream', "в подарке Durov's Glasses", '43 шт. · 1% · от 499,79 TON'), 19.90, 22.90, 0, 260),
    (card('Plush Pepe', 'в подарке Resistance Dog', '163 шт. · 1,2% · от 799 TON'), 24.00, 27.10, 520, 0),
    (card('Turtles', 'в подарке Heart Locket', '19 шт. · 1% · нет в продаже'), 31.60, 34.80, 0, 300),
    (card('Meme God', 'в подарке Spring Basket', '179 шт. · 0,1% · от 745 TON'), 36.00, 39.45, 0, -300),
    (card('Pepe Bag', 'в подарке Loot Bag', '73 шт. · 0,5% · от 650 TON'), 40.35, 42.95, -520, 0),
    (card('Pepe Paws', 'в подарке Scared Cat', '521 шт. · 3% · от 290 TON'), 43.75, 48.35, 520, 0),
    (card('Boiled Pepe', 'в подарке Easter Egg', '3225 шт. · 2% · от 9,26 TON'), 49.25, 51.15, 0, 200),
]
CARD_Y = 1480
TITLES = [
    (top_title([('Pepe', 120, 'Heavy', (255, 255, 255)), ('коллекция NFT-подарков Telegram', 46, 'Semibold', MINT)]), 9.45, 12.10),
    (top_title([('Самый редкий?', 96, 'Heavy', (255, 255, 255))]), 27.60, 30.45),
    (top_title([('Редкость ≠ цена', 96, 'Heavy', (255, 255, 255))]), 47.35, 48.40),
]
FINAL_BALLOON = np.asarray(balloon('Feels good, man', 70), np.float32)


def overlay(canvas, t):
    for spr, t0, t1, dx, dy in CARDS:
        a = ease((t - t0) / 0.4)
        o = ease((t - t1) / 0.32)
        if a > 0 and o < 1:
            blend(canvas, spr, dx * o, CARD_Y + 40 * (1 - a) + dy * o, a * (1 - o))
    for spr, t0, t1 in TITLES:
        a = ease((t - t0) / 0.35) * (1 - ease((t - t1) / 0.3))
        if a > 0:
            blend(canvas, spr, 0, 150 + 30 * (1 - a), a)
    if t > FEELS_T:
        x = t - FEELS_T
        s = fx.ease_out_back(min(1, x / 0.3), 2.2)
        im = Image.fromarray(FINAL_BALLOON.astype(np.uint8), 'RGBA')
        place(canvas, im, W / 2 + 40, 470, max(0.05, s), math.radians(-4), min(1, x / 0.08))


# ================================================================ frame with motion blur
def probes(t):
    return [g.center(t) for g in MAIN] + [page_center(t)[0]]


def subframes(t):
    a, b = Cam(t - SHUTTER / 2), Cam(t + SHUTTER / 2)
    move = 0.0
    for Pw in probes(t):
        x0, y0, z0 = a.project(Pw); x1, y1, z1 = b.project(Pw)
        if z0 > 0.3 and z1 > 0.3 and -300 < x0 < W + 300 and -300 < y0 < H + 300:
            move = max(move, math.hypot(x1 - x0, y1 - y0))
    return int(min(12, max(1, math.ceil(move / 5))))


_vy, _vx = np.mgrid[0:H, 0:W]
VIGNETTE = (1 - 0.38 * (((_vx - W / 2) / (W * 0.75)) ** 2 + ((_vy - H / 2) / (H * 0.7)) ** 2))[..., None].astype(np.float32)
del _vy, _vx


def render_at(t):
    t = min(max(t, 0.0), DUR - 1e-6)
    n = subframes(t)
    if n == 1:
        acc = scene(t)
    else:
        acc = sum(scene(t + (k + 0.5) / n * SHUTTER - SHUTTER / 2) for k in range(n)) / n
    acc *= VIGNETTE
    overlay(acc, t)
    acc += np.random.default_rng(int(t * FPS)).normal(0, 1.6, (H, W, 1)).astype(np.float32)
    return np.clip(acc, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(render_at, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
