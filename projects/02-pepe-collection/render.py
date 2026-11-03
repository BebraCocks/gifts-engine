"""02 · Pepe v5 — the plush dog travels through five worlds on what each gift could buy.

Scenes (content seconds): hook+swamp 0–20.3 · night street 20.3–29.19 · sewer 29.19–37.3 ·
space 37.3–45.7 · kitchen 45.7–end. Hidden cuts sit inside fast camera moves, darkness or flashes.
Frame = pure function of content time t. RubUp is inserted by banner.Breaks (events.AD_STOP).
    python -B render.py --frames 600,1500     (content frames, no ad)
    python -B render.py --video build/video_only.mp4   (only after «собирай», via engine/tools/build.py)
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
from timeline import DUR
from events import AD_STOP

W, H, FPS = 1080, 1920, 60
HW, HH = W // 2, H // 2
SHUTTER = 0.5 / FPS
BR = banner.Breaks([AD_STOP], cy=H / 2)
SW = [20.30, 29.19, 37.30, 45.70]          # scene switches


def scene_index(t):
    return sum(t >= s for s in SW)


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_in(x):
    x = min(1.0, max(0.0, x))
    return x * x


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) * (1 - x)


def v3(*a):
    return np.array(a, float)


def bez(p0, p1, p2, u):
    return (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u * u * p2


def mix(a, b, u):
    return a + (b - a) * u


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
MINT = (170, 228, 190)
PEPE = (120, 205, 85)
GOLD = (255, 214, 102)
INK = (20, 22, 20)
PAPER = (246, 238, 214)
MOON = np.array([0.155, 0.255, 1.0]); MOON /= np.linalg.norm(MOON)

# ================================================================ assets
DOG_ANIM = str(gifts_api.original_file('Resistance Dog', 'json'))


class Gift:
    def __init__(self, gift, model, pos, size=2.0, phase=None, anchor=0.88):
        self.anim = str(gifts_api.model_file(gift, model, 'json'))
        self.dur = lottie.info(self.anim)['duration']
        self.pos, self.size, self.anchor = v3(*pos), size, anchor
        self.phase = phase or (lambda t, d=self.dur: t % d)


def cyc(t, at, c_at, d):
    return (t - at + c_at) % d


HP = Gift('Kissed Frog', 'Happy Pepe', (0, 0, 0))
PW = Gift('Scared Cat', 'Pepe Paws', (3.6, 0, 6.2), phase=lambda t: cyc(t, 23.95, 1.17, 2.333))
TU = Gift('Heart Locket', 'Turtles', (0.5, 0.75, 7.0), phase=lambda t: 0.0 if t < 29.35 else (t - 29.35) % 3.0)
MG = Gift('Spring Basket', 'Meme God', (3.0, -0.6, 4.0), anchor=0.5)
BP = Gift('Easter Egg', 'Boiled Pepe', (0.5, 0, 3.2), size=1.8, phase=lambda t: cyc(t, 46.6, 0.9, 3.0))
DECOR = [Gift('Ice Cream', 'Cryo Pepe', (-6.5, 0, 9), size=1.6), Gift('Jester Hat', 'Pepe Hop', (13.5, 0, 15), size=1.6),
         Gift('Tama Gadget', 'Pepe Feels', (-8.5, 0, 18), size=1.6), Gift('Party Sparkler', 'Le Pepe', (9.5, 0, 6), size=1.6),
         Gift('Pool Float', 'Pool Pepe', (5.0, 0, 16), size=1.6), Gift('Jack-in-the-Box', 'Shy Pepe', (-4.0, 0, 13), size=1.6)]
for k, g in enumerate(DECOR):
    g.phase = (lambda t, d=g.dur, o=k * 0.37: (t + o) % d)
LID = Gift('Heart Locket', 'Turtles', (10.4, 0, 3.0), size=1.5, phase=lambda t: 0.0)   # open manhole lid on the street

# ---------------------------------------------------------------- vehicles (own drawings, no logos)
OUT = (28, 22, 30)


def _wheel(d, cx, cy, r):
    d.ellipse([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], fill=OUT)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(38, 38, 44))
    d.ellipse([cx - r * 0.48, cy - r * 0.48, cx + r * 0.48, cy + r * 0.48], fill=(190, 192, 200), outline=OUT, width=5)
    for k in range(5):
        a = k * 2 * math.pi / 5
        x, y = cx + r * 0.28 * math.cos(a), cy + r * 0.28 * math.sin(a)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(110, 110, 118))


def make_car(kind):
    """-> (back layer, front layer, driver window centre (x, y) in px, dog height px). Side view, facing right."""
    Wc, Hc = 1000, 480
    back = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0))
    front = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0))
    db, df = ImageDraw.Draw(back), ImageDraw.Draw(front)
    if kind == 'small':
        body, cab, wheels, r = (150, 236, 850, 386), [(225, 240), (285, 96), (705, 96), (800, 240)], (300, 700), 64
        color, dark = (150, 205, 225), (95, 150, 175)
        windows = [[(262, 230), (305, 116), (490, 116), (490, 230)], [(510, 230), (510, 116), (690, 116), (770, 230)]]
        win = (600, 175)
    else:
        body, cab, wheels, r = (55, 228, 955, 384), [(245, 232), (330, 112), (650, 112), (760, 232)], (235, 770), 70
        color = (196, 38, 46) if kind == 'zhiguli' else (255, 204, 0)
        dark = (140, 22, 30) if kind == 'zhiguli' else (205, 150, 0)
        windows = [[(278, 222), (346, 130), (485, 130), (485, 222)], [(505, 222), (505, 130), (640, 130), (728, 222)]]
        win = (595, 180)
    db.polygon(cab, fill=(36, 30, 44))
    df.polygon(cab, fill=color, outline=OUT, width=10)
    for wpoly in windows:
        df.polygon(wpoly, fill=(170, 210, 235, 80), outline=OUT, width=8)
    x0, y0, x1, y1 = body
    df.rounded_rectangle(body, radius=46, fill=color, outline=OUT, width=10)
    df.rectangle([x0 + 10, y1 - 46, x1 - 10, y1 - 12], fill=dark)
    df.line([(495, y0 + 6), (495, y1 - 14)], fill=OUT, width=6)
    df.rounded_rectangle([420, y0 + 40, 470, y0 + 54], radius=6, fill=OUT)
    df.rounded_rectangle([630, y0 + 40, 680, y0 + 54], radius=6, fill=OUT)
    df.ellipse([x1 - 46, y0 + 26, x1 - 6, y0 + 66], fill=(255, 236, 150), outline=OUT, width=6)
    df.rounded_rectangle([x0 + 4, y0 + 30, x0 + 34, y0 + 74], radius=8, fill=(230, 40, 40), outline=OUT, width=5)
    if kind == 'zhiguli':
        df.rounded_rectangle([x1 - 20, y0 + 92, x1 + 30, y0 + 122], radius=10, fill=(205, 208, 215), outline=OUT, width=6)
        df.rounded_rectangle([x0 - 30, y0 + 92, x0 + 20, y0 + 122], radius=10, fill=(205, 208, 215), outline=OUT, width=6)
    if kind == 'taxi':
        for k in range(18):
            cx = x0 + 60 + k * 46
            for row in range(2):
                fill = OUT if (k + row) % 2 == 0 else (250, 250, 250)
                df.rectangle([cx, y0 + 70 + row * 20, cx + 46, y0 + 90 + row * 20], fill=fill)
        df.rounded_rectangle([415, 52, 575, 112], radius=12, fill=(255, 236, 120), outline=OUT, width=8)
        df.text((495, 82), 'ТАКСИ', font=fx.font('Heavy', 40), fill=OUT, anchor='mm')
    for wx in wheels:
        _wheel(df, wx, y1, r)
    return back, front, win, 300 if kind != 'small' else 290


CARS = {k: make_car(k) for k in ('zhiguli', 'small', 'taxi')}


def make_scooter():
    im = Image.new('RGBA', (760, 640), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(520, 520), (585, 150)], fill=OUT, width=40)
    d.line([(520, 520), (585, 150)], fill=(70, 200, 190), width=24)
    d.rounded_rectangle([530, 128, 660, 160], radius=14, fill=OUT)
    d.rounded_rectangle([120, 488, 540, 528], radius=16, fill=(40, 42, 50), outline=OUT, width=8)
    d.rectangle([140, 494, 520, 502], fill=(70, 200, 190))
    _wheel(d, 150, 560, 52)
    _wheel(d, 560, 560, 52)
    return im


SCOOTER = make_scooter()


def make_pot():
    im = Image.new('RGBA', (900, 760), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 330, 120, 380], radius=20, fill=(60, 60, 66), outline=OUT, width=8)
    d.rounded_rectangle([780, 330, 880, 380], radius=20, fill=(60, 60, 66), outline=OUT, width=8)
    d.rounded_rectangle([110, 280, 790, 740], radius=60, fill=(170, 176, 186), outline=OUT, width=12)
    for k in range(6):
        x = 170 + k * 22
        d.line([(x, 320), (x, 700)], fill=(205, 210, 220), width=8)
    d.ellipse([90, 230, 810, 340], fill=(140, 146, 156), outline=OUT, width=12)
    d.ellipse([130, 250, 770, 325], fill=(150, 200, 225))
    for k in range(14):
        x, y, r = 170 + (k * 97) % 560, 262 + (k * 37) % 50, 8 + (k * 13) % 14
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], outline=(235, 245, 255), width=4)
    return im


POT = make_pot()


def text_sprite(text, size, weight='Heavy', fill=INK, stroke=0, stroke_fill=None):
    f = fx.font(weight, size)
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    l, t_, r, b = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 8, b - t_ + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t_), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill or fill)
    return im


# ================================================================ comic page (hook)
PG0 = v3(0, 3.2, -10)
PAGE_W, PAGE_H = 1200, 2000
PAGE_WORLD_H = 4.0


def inked(im, outline=10):
    im = im.convert('RGBA')
    a = im.split()[3]
    rgb = im.convert('RGB').quantize(6).convert('RGB')
    big = a.filter(ImageFilter.MaxFilter(outline * 2 + 1))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', im.size, INK + (255,)), (0, 0), big)
    out.paste(rgb, (0, 0), a)
    return out


def balloon(text, size=74, pad=(56, 44)):
    ts = text_sprite(text, size, 'Heavy')
    w, h = ts.width + pad[0] * 2, ts.height + pad[1] * 2
    im = Image.new('RGBA', (w + 20, h + 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(w * 0.30, h - 10), (w * 0.22, h + 95), (w * 0.48, h - 10)], fill=INK)
    d.ellipse([4, 4, w + 4, h + 4], fill=INK)
    d.ellipse([12, 12, w - 4, h - 4], fill=(255, 255, 255))
    d.polygon([(w * 0.32 + 6, h - 24), (w * 0.24 + 12, h + 66), (w * 0.46, h - 24)], fill=(255, 255, 255))
    im.alpha_composite(ts, (pad[0] + 4, pad[1] + 4))
    return im


def halftone(w, h, color, step=22, rmax=6.5):
    im = Image.new('RGBA', (w, h), color + (255,))
    d = ImageDraw.Draw(im)
    for y in range(0, h, step):
        for x in range((y // step) % 2 * step // 2, w, step):
            r = rmax * (0.45 + 0.55 * y / h)
            d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * 0.86) for c in color) + (255,))
    return im


PANELS = [(40, 40, 1160, 620), (40, 650, 1160, 1380), (40, 1410, 1160, 1960)]


def build_page_base():
    grain = np.random.default_rng(5).normal(0, 6, (PAGE_H, PAGE_W, 1))
    arr = np.clip(np.full((PAGE_H, PAGE_W, 3), PAPER, np.float32) + grain, 0, 255).astype(np.uint8)
    im = Image.fromarray(np.dstack([arr, np.full((PAGE_H, PAGE_W), 255, np.uint8)]), 'RGBA')
    for (x0, y0, x1, y1), c in zip(PANELS, [(214, 236, 196), (250, 222, 160), (205, 222, 240)]):
        im.alpha_composite(halftone(x1 - x0, y1 - y0, c), (x0, y0))
        ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], outline=INK, width=12)
    d = ImageDraw.Draw(im)
    cap = text_sprite('МЭТТ ФУРИ · КОМИКС', 46, 'Heavy')
    im.alpha_composite(cap, (600 - cap.width // 2, 92))
    d.rounded_rectangle([150, 1520, 1050, 1900], radius=34, fill=(32, 36, 44), outline=INK, width=10)
    d.rectangle([186, 1556, 1014, 1864], fill=(236, 240, 228))
    d.rectangle([186, 1556, 1014, 1604], fill=(120, 150, 110))
    lab = text_sprite('интернет-форум', 34, 'Bold', fill=(250, 250, 250))
    im.alpha_composite(lab, (600 - lab.width // 2, 1560))
    return im


PAGE_BASE = build_page_base()
FROG_INK = inked(Image.open(gifts_api.original_png('Plush Pepe', 512)).convert('RGBA').resize((560, 560), Image.LANCZOS), 9)
FACE = inked(Image.open(gifts_api.model_png('Kissed Frog', 'Happy Pepe', 256)).convert('RGBA').resize((120, 120), Image.LANCZOS), 4)
S2005 = text_sprite('2005', 230, 'Heavy')
S2008 = text_sprite('2008', 120, 'Heavy')
BALLOON = balloon('Feels good, man')
FACE_SLOTS = [(250 + (k % 6) * 132 + (k // 6 % 2) * 30, 1640 + (k // 6) * 74) for k in range(18)]
FACE_T = [6.75 + 0.055 * k + 0.02 * math.sin(k * 3.1) for k in range(18)]


def stamp(x):
    if x <= 0:
        return 0.0, 1.6
    return min(1.0, x / 0.12), max(0.2, 1.0 + 0.6 * math.exp(-x * 9) * math.cos(x * 14))


def paste_scaled(dst, spr, cx, cy, s, alpha=1.0):
    if alpha <= 0.01 or s <= 0.01:
        return
    w, h = max(1, int(spr.width * s)), max(1, int(spr.height * s))
    im = spr.resize((w, h), Image.BILINEAR)
    if alpha < 0.999:
        im.putalpha(Image.fromarray((np.asarray(im.split()[3], np.float32) * alpha).astype(np.uint8)))
    dst.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


def page_image(t):
    im = PAGE_BASE.copy()
    a, s = stamp(t - 0.35)
    paste_scaled(im, S2005, 600, 340, s, a)
    reveal = ease((t - 1.40) / 1.25)
    if reveal > 0:
        frog = FROG_INK.copy()
        hh = frog.height
        m = np.clip((reveal * (hh + 60) - np.arange(hh)) / 60.0, 0, 1)[:, None] * np.ones((1, frog.width))
        frog.putalpha(Image.fromarray((np.asarray(frog.split()[3], np.float32) * m).astype(np.uint8)))
        im.alpha_composite(frog, (int(600 - frog.width / 2 - 140), int(1380 - 40 - frog.height)))
    if t > 3.27:
        x = t - 3.27
        paste_scaled(im, BALLOON, 690, 800, max(0.05, fx.ease_out_back(min(1, x / 0.28), 2.2) * 0.92), min(1, x / 0.08))
    a, s = stamp(t - 5.10)
    paste_scaled(im, S2008, 600, 1470, s, a)
    for (x, y), t0 in zip(FACE_SLOTS, FACE_T):
        if t > t0:
            paste_scaled(im, FACE, x, y, max(0.05, fx.ease_out_back(min(1, (t - t0) / 0.18), 2.6) * 0.62))
    return im


def page_center(t):
    e = ease((t - 8.25) / 1.15)
    return PG0 + v3(0.6 * e, 10.0 * e * e, 2.5 * e), math.radians(28 * e * e)


# ================================================================ camera (keyframes per scene)
def K(t, C, T, roll=0.0, fov=50.0, flow=1.0):
    return (t, v3(*C), v3(*T), roll, fov, flow)


def hermite(keys, t, idx):
    kt = [k[0] for k in keys]
    if t <= kt[0]:
        return np.asarray(keys[0][idx], float)
    if t >= kt[-1]:
        return np.asarray(keys[-1][idx], float)
    i = max(j for j in range(len(kt) - 1) if kt[j] <= t)
    t0, t1 = kt[i], kt[i + 1]
    dt = t1 - t0

    def tan(j):
        a, b = max(j - 1, 0), min(j + 1, len(kt) - 1)
        return (np.asarray(keys[b][idx], float) - np.asarray(keys[a][idx], float)) / max(kt[b] - kt[a], 1e-6) * keys[j][5]
    p1, p2 = np.asarray(keys[i][idx], float), np.asarray(keys[i + 1][idx], float)
    m1, m2 = tan(i) * dt, tan(i + 1) * dt
    u = (t - t0) / dt
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2


P = PG0
HPL = v3(0, 0.95, 0)
DOG0 = v3(-1.0, 0, -1.6)                   # dog's pad in the swamp
CAR_PAD = v3(3.2, 0, 1.0)
KEYS = [
    [   # 0: hook + swamp
        K(0.00, P + v3(0.10, 0.62, -3.35), P + v3(0, 0.62, 0), 2.0, 50, 0.3),
        K(1.25, P + v3(0.04, 0.58, -3.15), P + v3(0, 0.58, 0), 0.6, 50),
        K(2.35, P + v3(-0.06, 0.02, -3.55), P + v3(0, 0.0, 0), -1.0, 50),
        K(3.05, P + v3(0.0, -0.02, -3.3), P + v3(0, -0.02, 0), -0.3, 50, 0.3),
        K(3.50, P + v3(0.14, 0.14, -2.55), P + v3(0.14, 0.14, 0), -3.0, 50),
        K(4.40, P + v3(0.06, 0.08, -2.72), P + v3(0.06, 0.08, 0), -2.0, 50, 0.4),
        K(5.30, P + v3(0, -1.36, -3.35), P + v3(0, -1.38, 0), 1.5, 50),
        K(8.05, P + v3(0, -1.30, -3.70), P + v3(0, -1.31, 0), 0.5, 50, 0.4),
        K(8.55, P + v3(0, -1.0, -4.9), P + v3(0, -0.7, 0), -2.0, 52),
        K(9.70, (-2.4, 3.4, -10.0), (-0.6, 0.6, 0.5), -4.0, 54),
        K(11.10, (-1.45, 1.15, -5.3), (-0.8, 0.75, -1.0), 0.0, 50, 0.4),
        K(12.30, (-1.35, 1.10, -5.0), (-0.8, 0.75, -1.0), 0.0, 50, 0.3),
        K(12.95, (-0.35, 1.35, -6.6), HPL, 0.8, 50),
        K(13.30, (-0.30, 1.25, -6.3), HPL, 0.5, 50, 0.4),
        K(17.30, (-0.15, 1.20, -5.7), HPL, 0.3, 50, 0.3),
        K(18.15, (1.9, 1.40, -6.0), (2.6, 0.9, 0.9), 0.0, 50, 0.6),
        K(19.15, (1.1, 1.65, -7.6), (1.4, 0.9, 0.2), 0.0, 50, 0.4),
        K(19.75, (2.0, 1.40, -7.0), (3.2, 0.8, 0.9), -2.0, 50, 0.8),
        K(20.30, (5.6, 1.30, -6.0), (8.6, 0.8, 1.0), -10.0, 56),
    ],
    [   # 1: night street (road along x, facades at z = 8)
        K(20.30, (-4.2, 1.3, -5.0), (-1.4, 0.8, 2.0), -8.0, 56),
        K(21.00, (-0.3, 1.3, -5.6), (0.2, 0.9, 2.0), 0.0, 50, 0.5),
        K(22.25, (2.6, 1.3, -1.4), (3.6, 1.0, 6.2), 0.0, 50, 0.5),
        K(23.90, (2.7, 1.25, -1.0), (3.6, 1.0, 6.2), 0.0, 50, 0.3),
        K(24.70, (1.3, 1.35, -4.8), (1.3, 0.8, 1.8), 0.0, 50, 0.5),
        K(25.90, (1.4, 1.3, -4.6), (1.6, 0.8, 1.8), 0.0, 50, 0.3),
        K(26.65, (3.6, 1.3, -4.4), (4.0, 0.8, 1.6), -1.0, 50),
        K(27.30, (7.0, 1.5, -3.8), (8.4, 0.6, 2.0), -3.0, 52),
        K(28.30, (9.0, 3.2, -1.0), (9.0, -1.0, 2.0), 0.0, 52),
        K(29.19, (9.0, 2.3, 1.0), (9.0, -3.0, 2.0), 3.0, 50, 0.3),
    ],
    [   # 2: sewer (tunnel along z)
        K(29.19, (-0.2, 1.6, -1.8), (-0.6, 1.4, 3.4), 2.0, 52),
        K(29.90, (-0.3, 1.3, -0.9), (0.0, 1.1, 5.0), 0.0, 50, 0.4),
        K(31.00, (0.15, 1.25, 0.2), (0.5, 1.2, 7.0), 0.0, 50, 0.5),
        K(34.60, (0.05, 1.2, 0.9), (0.5, 1.2, 7.0), 0.0, 50, 0.3),
        K(35.40, (-0.6, 1.3, -0.2), (-0.9, 0.9, 3.4), 0.0, 50, 0.5),
        K(36.40, (-0.6, 1.2, 0.3), (-0.9, 1.6, 3.4), 0.0, 52, 0.6),
        K(37.30, (-0.8, 2.6, 2.0), (-0.9, 9.0, 3.4), -6.0, 60),
    ],
    [   # 3: space
        K(37.30, (0.0, -3.5, -5.5), (0.0, -1.0, 0.0), 6.0, 60),
        K(38.30, (0.1, 0.6, -4.6), (0.0, 0.3, 0.0), 0.0, 52, 0.5),
        K(39.50, (0.3, 0.6, -4.4), (0.2, 0.3, 0.0), 0.0, 52, 0.3),
        K(40.30, (1.8, 0.4, -1.6), (3.0, 0.0, 4.0), 0.0, 52, 0.5),
        K(42.40, (1.9, 0.4, -1.3), (3.0, 0.0, 4.0), 0.0, 50, 0.3),
        K(43.30, (0.7, 0.7, -4.6), (0.6, 0.0, 0.6), 0.0, 50, 0.5),
        K(44.60, (0.7, 0.7, -4.4), (0.6, -0.2, 0.6), 0.0, 50, 0.4),
        K(45.70, (0.8, -9.0, -4.0), (0.6, -16.0, 1.5), 8.0, 62),
    ],
    [   # 4: kitchen (counter y = 0, back wall z = 6, window on the right)
        K(45.70, (-1.6, 2.6, -2.4), (-1.8, 0.6, 2.6), -4.0, 56),
        K(46.40, (0.2, 1.3, -2.6), (0.4, 0.9, 3.2), 0.0, 50, 0.5),
        K(48.20, (0.3, 1.25, -2.3), (0.4, 0.9, 3.2), 0.0, 50, 0.3),
        K(48.90, (1.0, 1.45, -4.0), (1.2, 0.7, 2.2), 0.0, 50, 0.5),
        K(50.80, (1.1, 1.40, -3.8), (1.3, 0.7, 2.2), 0.0, 50, 0.3),
        K(DUR, (1.4, 2.2, -6.2), (2.6, 2.3, 6.0), 0.0, 52, 0.4),
    ],
]
SHAKES = [(3.27, 0.03, 9), (18.30, 0.06, 8), (21.0, 0.04, 9), (23.95, 0.05, 11), (29.40, 0.05, 8), (30.55, 0.07, 8),
          (36.35, 0.08, 9), (46.0, 0.05, 9)]


def camera(t):
    keys = KEYS[scene_index(t)]
    C, T = hermite(keys, t, 1), hermite(keys, t, 2)
    roll, fov = float(hermite(keys, t, 3)), float(hermite(keys, t, 4))
    drift = v3(0.03 * math.sin(t * 1.3), 0.025 * math.sin(t * 1.7 + 1), 0)
    for t0, amp, f in SHAKES:
        if t0 <= t < t0 + 1.0:
            k = amp * math.exp(-(t - t0) * 6)
            drift = drift + v3(k * math.sin((t - t0) * f * 6.28), k * math.sin((t - t0) * f * 5.1 + 1), 0)
    return C + drift, T + drift * 0.5, math.radians(roll + 0.6 * math.sin(t * 0.9)), fov


def basis(C, T, roll):
    f = T - C; f = f / np.linalg.norm(f)
    r = np.cross([0, 1, 0], f)
    if np.linalg.norm(r) < 1e-6:
        r = np.array([1.0, 0, 0])
    r = r / np.linalg.norm(r)
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

    def rays(self):
        a, b = _gx / self.F, _gy / self.F
        dx = self.f[0] + a * self.r[0] - b * self.u[0]
        dy = self.f[1] + a * self.r[1] - b * self.u[1]
        dz = self.f[2] + a * self.r[2] - b * self.u[2]
        n = np.sqrt(dx * dx + dy * dy + dz * dz)
        return dx / n, dy / n, dz / n


_gx, _gy = np.meshgrid((np.arange(HW) + 0.5) * 2 - W / 2, (np.arange(HH) + 0.5) * 2 - H / 2)

# ================================================================ backgrounds (per pixel, half res)
rng = np.random.default_rng(20261103)


def treeline(az):
    return (0.03 + 0.016 * np.sin(az * 7 + 1) + 0.01 * np.sin(az * 23 + 2)
            + 0.006 * np.sin(az * 61) + 0.004 * np.abs(np.sin(az * 140)))


def night_sky(dx, dy, dz, trees=True, zen=ZENITH, hor=HORIZON):
    n = np.sqrt(dx * dx + dy * dy + dz * dz)
    e = dy / n
    k = np.clip(e / 0.55, 0, 1); k = (k * k * (3 - 2 * k))[..., None]
    col = hor + (zen - hor) * k
    m = np.clip((dx * MOON[0] + dy * MOON[1] + dz * MOON[2]) / n, 0, 1)
    col = col + MOONLIGHT * (0.10 * m ** 40 + 0.05 * m ** 6)[..., None]
    if trees:
        tree = e < treeline(np.arctan2(dx, dz))
        col = np.where(tree[..., None], TREES + (FOG - TREES) * 0.25, col)
    return col


PADS = [(0.0, 0.05, 1.25, 0.6), (DOG0[0], DOG0[2], 0.75, 2.0), (CAR_PAD[0], CAR_PAD[2], 2.2, 4.0)]
PADS += [(g.pos[0], g.pos[2] + 0.05, 1.0, rng.uniform(0, 6.28)) for g in DECOR]
for _ in range(110):
    x, z = rng.uniform(-14, 18), rng.uniform(-8, 40)
    if all((x - a) ** 2 + (z - b) ** 2 > (r + 0.9) ** 2 for a, b, r, _ in PADS):
        PADS.append((x, z, rng.uniform(0.35, 0.9), rng.uniform(0, 6.28)))
PADS = np.array(PADS, np.float32)


def bg_swamp(cam, t):
    dx, dy, dz = cam.rays()
    out = night_sky(dx, dy, dz)
    water = dy < -1e-4
    if water.any():
        wx, wy, wz = dx[water], dy[water], dz[water]
        tt = -cam.C[1] / wy
        x, z = cam.C[0] + tt * wx, cam.C[2] + tt * wz
        dist = tt
        px = 0.045 * (np.sin(1.3 * x + 2.1 * t) + 0.6 * np.sin(2.9 * z - 1.4 * t + 0.7 * x))
        pz = 0.07 * (np.sin(1.7 * z + 1.6 * t) + 0.5 * np.sin(3.7 * x + 2.3 * t))
        att = np.clip(4.0 / (dist + 4.0), 0.15, 1)
        rx, ry, rz = wx + px * att, -wy, wz + pz * att
        refl = night_sky(rx[None], ry[None], rz[None])[0]
        m = np.clip((rx * MOON[0] + ry * MOON[1] + rz * MOON[2]) / np.sqrt(rx * rx + ry * ry + rz * rz), 0, 1)
        glint = (0.75 * m ** 2500 + 0.09 * m ** 200)[:, None] * MOONLIGHT
        col = WATER + refl * (0.35 + 0.55 * (1 - np.abs(wy)) ** 4)[:, None] + glint
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
            c = col[near]
            col[near] = c + (pc + MOONLIGHT * (0.12 * np.clip(1 - dn / rad, 0, 1))[:, None] - c) * cover[:, None]
        fog = (1 - np.exp(-dist / 22.0))[:, None] * 0.85
        out[water] = col + (FOG - col) * fog
    return out


def hash2(a, b):
    return np.modf(np.sin(a * 12.9898 + b * 78.233) * 43758.5453)[0] % 1.0


CITY_ZEN, CITY_HOR = np.array([6, 8, 22], np.float32), np.array([44, 34, 70], np.float32)
FACADE_Z = 8.0
HOLE = v3(9.0, 0, 2.2)
LAMPS_X = np.arange(-8, 30, 8.0)


def bld_height(seg):
    return 7.0 + 9.0 * hash2(seg, 3.3)


def bg_street(cam, t):
    dx, dy, dz = cam.rays()
    out = night_sky(dx, dy, dz, trees=False, zen=CITY_ZEN, hor=CITY_HOR)
    C = cam.C
    tf = np.where(dz > 1e-4, (FACADE_Z - C[2]) / np.maximum(dz, 1e-4), np.inf)
    fx_, fy_ = C[0] + tf * dx, C[1] + tf * dy
    seg = np.floor(np.nan_to_num(fx_, posinf=0.0, neginf=0.0) / 6.0)
    hb = bld_height(seg)
    facade = np.isfinite(tf) & (fy_ < hb) & (fy_ > 0)
    tg = np.where(dy < -1e-4, -C[1] / np.minimum(dy, -1e-4), np.inf)
    ground = (tg < tf) | (~facade & (dy < -1e-4))
    facade &= ~ground
    if facade.any():
        x, y, s = fx_[facade], fy_[facade], seg[facade]
        base = np.stack([40 + 30 * hash2(s, 1.1), 34 + 20 * hash2(s, 2.2), 48 + 30 * hash2(s, 4.4)], -1)
        col, row = np.floor(x / 1.6), np.floor(y / 2.4)
        u, v = x / 1.6 - col, y / 2.4 - row
        inwin = (u > 0.22) & (u < 0.78) & (v > 0.25) & (v < 0.75) & (y > 1.0)
        lit = hash2(col + s * 7, row) > 0.5
        warm = np.array([255, 196, 110], np.float32) * (0.65 + 0.35 * hash2(col, row + 9))[:, None]
        cool = np.array([24, 30, 52], np.float32)
        c = np.where(inwin[:, None], np.where(lit[:, None], warm, cool), base)
        shop = (y < 1.0) & (np.abs((x % 6.0) - 3.0) < 1.8)
        c = np.where(shop[:, None], np.array([90, 200, 210], np.float32) * 0.8, c)
        fog = (1 - np.exp(-tf[facade] / 40.0))[:, None] * 0.5
        out[facade] = c + (CITY_HOR - c) * fog
    if ground.any():
        tgg = tg[ground]
        x, z = C[0] + tgg * dx[ground], C[2] + tgg * dz[ground]
        c = np.zeros((len(x), 3), np.float32) + np.array([26, 28, 36], np.float32)
        side = z > 5.0
        c[side] = [56, 54, 64]
        c[(z > 4.85) & (z < 5.0)] = [120, 118, 128]
        lane = (np.abs(z - 2.5) < 0.07) & ((x % 3.0) < 1.6)
        c[lane] = [200, 196, 170]
        for lx in LAMPS_X:
            d2 = (x - lx) ** 2 + (z - 5.4) ** 2
            c += np.array([255, 190, 110], np.float32) * (0.45 * np.exp(-d2 / 7.0))[:, None]
        shine = 0.5 + 0.5 * np.sin(x * 3.1 + z * 1.7)
        c += 6 * shine[:, None]
        hd = np.sqrt((x - HOLE[0]) ** 2 + (z - HOLE[2]) ** 2)
        rim = (hd < 1.0) & (hd > 0.86)
        c[rim] = [70, 70, 78]
        c[hd <= 0.86] = [3, 3, 5]
        fog = (1 - np.exp(-tgg / 45.0))[:, None] * 0.6
        out[ground] = c + (CITY_HOR - c) * fog
    return out


TUN_C, TUN_R, WATER_Y = 1.8, 2.6, 0.45
SHAFT = (-0.9, 3.4, 0.75)                  # x, z, radius of the hole in the tunnel roof
LAMPS_Z = np.arange(-8, 40, 7.0)


def bg_sewer(cam, t):
    dx, dy, dz = cam.rays()
    C = cam.C
    oy = C[1] - TUN_C
    a = dx * dx + dy * dy
    b = 2 * (C[0] * dx + oy * dy)
    c = C[0] ** 2 + oy ** 2 - TUN_R ** 2
    tc = (-b + np.sqrt(np.maximum(b * b - 4 * a * c, 0))) / np.maximum(2 * a, 1e-6)
    tw = np.where(dy < -1e-4, (WATER_Y - C[1]) / np.minimum(dy, -1e-4), np.inf)
    water = tw < tc
    out = np.zeros(dx.shape + (3,), np.float32)
    # bricks
    m = ~water
    x, y, z = C[0] + tc[m] * dx[m], C[1] + tc[m] * dy[m], C[2] + tc[m] * dz[m]
    th = np.arctan2(y - TUN_C, x)
    u = th * TUN_R / 0.26
    row = np.floor(u)
    zz = z / 0.55 + 0.5 * (row % 2)
    mort = (np.abs(u - row - 0.5) > 0.42) | (np.abs(zz - np.floor(zz) - 0.5) > 0.45)
    tone = 0.75 + 0.25 * hash2(row, np.floor(zz))
    col = np.array([92, 52, 42], np.float32) * tone[:, None]
    col[mort] = [40, 30, 28]
    green = np.clip(1 - (y - WATER_Y) / 3.0, 0, 1)
    col += np.array([30, 120, 50], np.float32) * (0.55 * green)[:, None]
    for lz in LAMPS_Z:
        d2 = (z - lz) ** 2 + (y - 3.9) ** 2 * 0.5
        col += np.array([255, 200, 120], np.float32) * (0.5 * np.exp(-d2 / 3.0))[:, None]
    shaft = (np.sqrt((x - SHAFT[0]) ** 2 + (z - SHAFT[1]) ** 2) < SHAFT[2]) & (y > TUN_C + 1.5)
    col[shaft] = [4, 10, 8]
    fog = (1 - np.exp(-tc[m] / 14.0))[:, None]
    out[m] = col * (1 - fog) + np.array([4, 12, 8], np.float32) * fog
    if water.any():
        tww = tw[water]
        x, z = C[0] + tww * dx[water], C[2] + tww * dz[water]
        rip = 0.5 + 0.5 * np.sin(x * 4 + t * 2.0) * np.sin(z * 3 - t * 1.5)
        col = np.array([40, 150, 60], np.float32) * (0.55 + 0.3 * rip)[:, None]
        for lz in LAMPS_Z:
            col += np.array([255, 220, 140], np.float32) * (0.35 * np.exp(-((z - lz) ** 2) / 1.2 - (x ** 2) / 0.4))[:, None]
        fog = (1 - np.exp(-tww / 14.0))[:, None]
        out[water] = col * (1 - fog) + np.array([4, 12, 8], np.float32) * fog
    return out


def _nebula():
    r = np.random.default_rng(42)
    tex = np.zeros((256, 512, 3), np.float32)
    for color, scale, power in (((120, 40, 180), 30, 2.2), ((30, 140, 170), 18, 2.5), ((220, 70, 140), 10, 3.0)):
        n = Image.fromarray((r.random((256, 512)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(scale))
        a = np.asarray(n, np.float32) / 255.0
        a = (a - a.min()) / (a.max() - a.min() + 1e-6)
        tex += np.asarray(color, np.float32) * (a ** power)[..., None] * 0.9
    return tex


NEBULA = _nebula()
PLANET, PLANET_R = v3(-24, 4, 60), 13.0
RING_N = np.array([0.25, 0.92, -0.3]); RING_N /= np.linalg.norm(RING_N)
EARTH, EARTH_R = v3(0, -95, 20), 75.0
SUN = np.array([0.7, 0.45, -0.55]); SUN /= np.linalg.norm(SUN)


def sphere_hit(C, dx, dy, dz, P0, R):
    ox, oy, oz = C - P0
    b = ox * dx + oy * dy + oz * dz
    c = ox * ox + oy * oy + oz * oz - R * R
    disc = b * b - c
    t = -b - np.sqrt(np.maximum(disc, 0))
    return np.where((disc > 0) & (t > 0), t, np.inf)


def bg_space(cam, t):
    dx, dy, dz = cam.rays()
    az = (np.arctan2(dx, dz) / (2 * np.pi) + 0.5) * 511
    el = (np.arcsin(np.clip(dy, -1, 1)) / np.pi + 0.5) * 255
    x0, y0 = np.floor(az).astype(int), np.floor(el).astype(int).clip(0, 254)
    fx_, fy_ = (az - x0)[..., None], (el - y0)[..., None]
    x0 %= 512; x1 = (x0 + 1) % 512
    out = (NEBULA[y0, x0] * (1 - fx_) * (1 - fy_) + NEBULA[y0, x1] * fx_ * (1 - fy_)
           + NEBULA[y0 + 1, x0] * (1 - fx_) * fy_ + NEBULA[y0 + 1, x1] * fx_ * fy_) + np.array([2, 3, 10], np.float32)
    C = cam.C
    for P0, R, kind in ((PLANET, PLANET_R, 'planet'), (EARTH, EARTH_R, 'earth')):
        th = sphere_hit(C, dx, dy, dz, P0, R)
        hit = np.isfinite(th)
        if kind == 'planet':
            denom = dx * RING_N[0] + dy * RING_N[1] + dz * RING_N[2]
            tr = ((P0 - C) @ RING_N) / np.where(np.abs(denom) < 1e-5, 1e-5, denom)
            rx, ry, rz = C[0] + tr * dx - P0[0], C[1] + tr * dy - P0[1], C[2] + tr * dz - P0[2]
            rr = np.sqrt(rx * rx + ry * ry + rz * rz) / R
            ring = (tr > 0) & (rr > 1.35) & (rr < 2.3) & ~(hit & (th < tr))
            band = 0.6 + 0.4 * np.sin(rr * 40)
            out[ring] = out[ring] * 0.3 + np.array([230, 200, 160], np.float32) * (0.75 * band[ring])[:, None]
        if hit.any():
            tt = th[hit]
            nx, ny, nz = (C[0] + tt * dx[hit] - P0[0]) / R, (C[1] + tt * dy[hit] - P0[1]) / R, (C[2] + tt * dz[hit] - P0[2]) / R
            lam = np.clip(nx * SUN[0] + ny * SUN[1] + nz * SUN[2], 0, 1) * 0.9 + 0.08
            rim = (1 - np.abs(nx * dx[hit] + ny * dy[hit] + nz * dz[hit])) ** 3
            if kind == 'planet':
                base = np.array([210, 140, 80], np.float32) * (0.8 + 0.2 * np.sin(ny * 22))[:, None]
                atm = np.array([255, 180, 120], np.float32)
            else:
                land = np.sin(nx * 9 + 1) * np.sin(nz * 7) + 0.5 * np.sin(ny * 13 + nx * 5) > 0.35
                base = np.where(land[:, None], np.array([70, 130, 60], np.float32), np.array([30, 80, 190], np.float32))
                cloud = (np.sin(nx * 23 + nz * 11) * np.sin(ny * 17) > 0.55)
                base[cloud] = [235, 240, 250]
                atm = np.array([120, 180, 255], np.float32)
            out[hit] = base * lam[:, None] + atm * (0.6 * rim)[:, None]
    return out


WALL_Z, WIN = 6.0, (1.6, 4.6, 1.5, 4.3)    # window x0, x1, y0, y1 on the back wall
KLIGHT = v3(0.0, 5.0, 1.0)


def bg_kitchen(cam, t):
    dx, dy, dz = cam.rays()
    C = cam.C
    INF = np.inf

    def plane(den, num):
        return np.where(np.abs(den) > 1e-5, num / np.where(np.abs(den) > 1e-5, den, 1), INF)
    ts = [plane(dz, WALL_Z - C[2]), plane(dx, -6.0 - C[0]), plane(dx, 8.0 - C[0]), plane(dy, -C[1]), plane(dy, 6.0 - C[1])]
    ts = [np.where(tt > 1e-4, tt, INF) for tt in ts]
    which = np.argmin(np.stack(ts), 0)
    tmin = np.min(np.stack(ts), 0)
    x, y, z = C[0] + tmin * dx, C[1] + tmin * dy, C[2] + tmin * dz
    out = np.zeros(dx.shape + (3,), np.float32)
    # back wall: tiles + window
    m = which == 0
    tu, tv = x[m] / 0.5, y[m] / 0.5
    grout = (np.abs(tu - np.round(tu)) < 0.05) | (np.abs(tv - np.round(tv)) < 0.05)
    col = np.where(grout[:, None], np.array([185, 172, 152], np.float32), np.array([236, 226, 205], np.float32))
    inwin = (x[m] > WIN[0]) & (x[m] < WIN[1]) & (y[m] > WIN[2]) & (y[m] < WIN[3])
    frame = (x[m] > WIN[0] - 0.15) & (x[m] < WIN[1] + 0.15) & (y[m] > WIN[2] - 0.15) & (y[m] < WIN[3] + 0.15) & ~inwin
    mull = inwin & ((np.abs(x[m] - (WIN[0] + WIN[1]) / 2) < 0.05) | (np.abs(y[m] - (WIN[2] + WIN[3]) / 2) < 0.05))
    if inwin.any():
        sky = night_sky(dx[m][inwin], dy[m][inwin] - 0.12, dz[m][inwin])
        col[inwin] = sky
        mx = (dx[m][inwin] * MOON[0] + (dy[m][inwin] - 0.12) * MOON[1] + dz[m][inwin] * MOON[2])
        col[inwin] += MOONLIGHT * (1.2 * np.clip(mx, 0, 1) ** 700 + 0.35 * np.clip(mx, 0, 1) ** 90)[:, None]
    col[frame | mull] = [120, 80, 50]
    out[m] = col
    out[which == 1] = [196, 160, 120]
    out[which == 2] = [196, 160, 120]
    m = which == 3
    grain = 0.85 + 0.15 * np.sin(x[m] * 9 + np.sin(z[m] * 3) * 2)
    out[m] = np.array([156, 104, 64], np.float32) * grain[:, None]
    out[which == 4] = [214, 196, 168]
    # warm light falloff
    d2 = (x - KLIGHT[0]) ** 2 + (y - KLIGHT[1]) ** 2 + (z - KLIGHT[2]) ** 2
    light = 0.45 + 0.75 * np.exp(-d2 / 60.0)
    winmask = (which == 0) & (x > WIN[0]) & (x < WIN[1]) & (y > WIN[2]) & (y < WIN[3])
    out = np.where(winmask[..., None], out, out * light[..., None])
    return out


BG = [bg_swamp, bg_street, bg_sewer, bg_space, bg_kitchen]

# ================================================================ compositing helpers
_cache = {}


def glow(radius, color, core=0.6):
    key = ('g', int(radius), tuple(int(c) for c in color), core)
    if key not in _cache:
        r = max(2, int(radius))
        y, x = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(x * x + y * y) / r
        g = np.clip(1 - d, 0, 1) ** 2.2 * (1 - core) + np.exp(-(d / 0.18) ** 2) * core
        val = (g[..., None] * (np.asarray(color, np.float32) / 255.0)).astype(np.float32)
        if len(_cache) > 600:
            _cache.clear()
        _cache[key] = val
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


def place(canvas, img, sx, sy, scale, angle, alpha=1.0, flip=False, tint=None, sxy=(1.0, 1.0)):
    w, h = img.size
    kx, ky = scale * sxy[0], scale * sxy[1]
    if kx <= 1e-4 or ky <= 1e-4:
        return
    ca, sa = math.cos(angle), math.sin(angle)
    hw, hh = w * kx / 2, h * ky / 2
    ex, ey = abs(ca) * hw + abs(sa) * hh, abs(sa) * hw + abs(ca) * hh
    ox, oy = int(max(0, math.floor(sx - ex))), int(max(0, math.floor(sy - ey)))
    bx, by = int(min(W, math.ceil(sx + ex))), int(min(H, math.ceil(sy + ey)))
    if bx - ox < 2 or by - oy < 2:
        return
    a_, b_ = ca / kx, -sa / kx
    d_, e_ = sa / ky, ca / ky
    c_ = (ca * (ox - sx) - sa * (oy - sy)) / kx + w / 2
    f_ = (sa * (ox - sx) + ca * (oy - sy)) / ky + h / 2
    if flip:
        d_, e_, f_ = -d_, -e_, h - f_
    out = img.transform((bx - ox, by - oy), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BILINEAR)
    arr = np.asarray(out, np.float32)
    if tint is not None:
        arr = arr.copy(); arr[..., :3] *= tint[0]; arr[..., 3] *= tint[1]
    blend(canvas, arr, ox, oy, alpha)


def billboard(canvas, cam, img, base, world_h, anchor=0.9, rot=0.0, sxy=(1.0, 1.0), alpha=1.0, reflect_y=None, world_w=None):
    """Upright sprite standing on `base` (world). anchor = fraction of image height where the base is."""
    w, h = img.size
    world_w = world_w or world_h * w / h
    up = v3(0, 1, 0)
    centre = base + up * (anchor - 0.5) * world_h * sxy[1]
    sx, sy, z = cam.project(centre)
    if z < 0.3:
        return None
    s = cam.F * world_h / z / h
    if not (-w * s < sx < W + w * s and -h * s < sy < H + h * s):
        return None
    if reflect_y is not None:
        mirror = centre.copy(); mirror[1] = 2 * reflect_y - centre[1]
        rx, ry, rz = cam.project(mirror)
        if rz > 0.3:
            place(canvas, img, rx, ry, s, cam.roll - rot, alpha, flip=True, tint=(0.55, 0.35), sxy=sxy)
    place(canvas, img, sx, sy, s, cam.roll + rot, alpha, sxy=sxy)
    return sx, sy, s


def lottie_img(anim, phase, px):
    q = int(min(1024, max(96, math.ceil(px / 96) * 96)))
    return lottie.frame(anim, phase, q)


def draw_gift(canvas, cam, g, t, reflect_y=None, sxy=(1.0, 1.0), rot=0.0):
    z = cam.project(g.pos)[2]
    if z < 0.3:
        return
    img = lottie_img(g.anim, g.phase(t), cam.F * g.size / z)
    billboard(canvas, cam, img, g.pos, g.size, g.anchor, rot, sxy, reflect_y=reflect_y)


# ================================================================ the dog and its rides
DOG_H = 1.15


def dog_img(t, px):
    return lottie_img(DOG_ANIM, t % 3.0, px)


def car_img(kind, t, dog=True):
    back, front, win, dh = CARS[kind]
    im = back.copy()
    if dog:
        d = dog_img(t, dh).resize((dh, dh), Image.BILINEAR)
        im.alpha_composite(d, (int(win[0] - dh / 2), int(win[1] - dh * 0.30)))
    im.alpha_composite(front)
    return im


def scooter_img(t, dog=True):
    im = SCOOTER.copy()
    if dog:
        d = dog_img(t, 380).resize((380, 380), Image.BILINEAR)
        im.alpha_composite(d, (150, 120))
    return im


CAR_LEN = 3.8                               # world length of a car sprite (1000 px)


def draw_vehicle(canvas, cam, img, base, length, rot=0.0, sxy=(1.0, 1.0), reflect_y=None, alpha=1.0):
    h_world = length * img.height / img.width
    billboard(canvas, cam, img, base, h_world, 0.96, rot, sxy, alpha, reflect_y)


def pop(t, t0, dur=0.35):
    """Scale-in with overshoot: 0 before t0."""
    if t < t0:
        return 0.0
    return fx.ease_out_back(min(1.0, (t - t0) / dur), 2.4)


def hop(p0, p1, t, t0, t1, height=1.2):
    u = ease((t - t0) / (t1 - t0))
    p = p0 + (p1 - p0) * u
    return p + v3(0, height * 4 * u * (1 - u), 0), u


# ---------------------------------------------------------------- per-scene objects
def objects_swamp(canvas, cam, t):
    items = []
    for g in [HP] + DECOR:
        items.append((cam.project(g.pos)[2], lambda g=g: draw_gift(canvas, cam, g, t, reflect_y=0.0)))
    # car drops onto its pad, the dog hops in, the car drives off to the right
    car_base = CAR_PAD.copy()
    if t >= 17.9:
        u = (t - 17.9) / 0.45
        if u < 1:
            car_base[1] = 5.0 * (1 - ease_in(u))
        sq = fx.bump(max(0.0, t - 18.35), 3.0, 6.0) if t > 18.35 else 0.0
        if t > 19.75:
            car_base[0] += 14.0 * (t - 19.75) ** 2
        in_car = t >= 19.72
        img = car_img('zhiguli', t, dog=in_car)
        items.append((cam.project(car_base)[2], lambda img=img, b=car_base, sq=sq:
                      draw_vehicle(canvas, cam, img, b, CAR_LEN, sxy=(1 + 0.08 * sq, 1 - 0.1 * sq), reflect_y=0.0)))
    if 18.35 <= t < 19.25:                           # splash when the car lands on its pad
        age = (t - 18.35) / 0.9
        for i in range(34):
            a = i / 34 * 6.283
            p = CAR_PAD + v3(math.cos(a) * (1.4 + 1.6 * age), 0.15 + 2.2 * age - 3.2 * age * age, math.sin(a) * 0.6 * (0.5 + age))
            x, y, z = cam.project(p)
            if z > 0.3:
                add(canvas, glow(cam.F * 0.07 / z, (200, 235, 255), 0.6), x, y, 0.9 * (1 - age))
    if t < 19.72:
        base, rot, sxy = DOG0.copy(), 0.0, (1.0, 1.0)
        if 11.45 <= t < 12.45:                       # «Что на них купишь?» — a puzzled tilt
            rot = 0.22 * math.sin((t - 11.45) * math.pi * 2) * math.sin((t - 11.45) * math.pi)
        if 19.20 <= t < 19.72:                       # «Поехали!» — hop into the car
            base, u = hop(DOG0, CAR_PAD + v3(0.6, 0.6, -0.05), t, 19.20, 19.72, 1.4)
            sxy = (1 - 0.35 * u, 1 - 0.35 * u)
        breathe = 1 + 0.02 * math.sin(t * 3)
        img = dog_img(t, 400)
        items.append((cam.project(base)[2], lambda img=img, b=base, r=rot, s=sxy:
                      billboard(canvas, cam, img, b, DOG_H, 0.98, r, (s[0], s[1] * breathe), reflect_y=0.0)))
    for _, fn in sorted(items, key=lambda it: -it[0]):
        fn()


def objects_street(canvas, cam, t):
    items = []
    # street lamps
    for lx in LAMPS_X:
        top = v3(lx, 4.6, 5.4)
        x0, y0, z0 = cam.project(v3(lx, 0, 5.4)); x1, y1, z1 = cam.project(top)
        if z0 > 0.3 and -200 < x0 < W + 200:
            items.append((z0, lambda a=(x0, y0, x1, y1, z0): _pole(canvas, cam, a)))
    items.append((cam.project(PW.pos)[2], lambda: draw_gift(canvas, cam, PW, t)))
    items.append((cam.project(LID.pos)[2], lambda: draw_gift(canvas, cam, LID, t)))
    # car arrives from the left and parks
    u = ease_out((t - 20.30) / 0.75)
    car_x = -7.5 + 7.5 * u
    in_car = t < 25.20
    img = car_img('zhiguli', t, dog=in_car)
    sq = fx.bump(max(0.0, t - 21.0), 3.0, 6.0) if t > 21.0 else 0.0
    cb = v3(car_x, 0, 2.0)
    items.append((cam.project(cb)[2], lambda: draw_vehicle(canvas, cam, img, cb, CAR_LEN, sxy=(1 + 0.05 * sq, 1 - 0.06 * sq))))
    # scooter pops in on «электросамокат», the dog hops on, rides to the open manhole and falls in
    if t >= 24.30:
        sc0 = v3(2.6, 0, 1.4)
        sb = sc0.copy()
        dog_on = t >= 25.65
        if t > 26.0:
            sb[0] = mix(2.6, HOLE[0], ease_in(min(1.0, (t - 26.0) / 1.55)))
        fall = max(0.0, t - 27.55)
        k = 1.0
        if fall > 0:
            sb[0] = HOLE[0]
            sb[1] = -3.0 * fall * fall
            k = max(0.0, 1 - fall / 0.6)
        if k > 0:
            img_s = scooter_img(t, dog=dog_on)
            s = pop(t, 24.30)
            items.append((cam.project(sb)[2], lambda: billboard(canvas, cam, img_s, sb, 1.5 * s * k, 0.93, 0.25 * fall,
                                                                    alpha=min(1, k * 2))))
        if 25.20 <= t < 25.65:
            base, uu = hop(v3(0.6, 0.6, 1.95), sc0 + v3(-0.2, 0.2, -0.05), t, 25.20, 25.65, 1.0)
            img_d = dog_img(t, 300)
            items.append((cam.project(base)[2], lambda: billboard(canvas, cam, img_d, base, DOG_H * 0.8, 0.98)))
    for _, fn in sorted(items, key=lambda it: -it[0]):
        fn()


def _pole(canvas, cam, a):
    x0, y0, x1, y1, z0 = a
    layer = Image.new('L', (W, H), 0)
    ImageDraw.Draw(layer).line([(x0, y0), (x1, y1)], fill=255, width=max(2, int(cam.F * 0.12 / z0)))
    box = layer.getbbox()
    if box:
        bx0, by0, bx1, by1 = box
        al = np.asarray(layer.crop(box), np.float32)[..., None] / 255.0
        c = canvas[by0:by1, bx0:bx1]
        c += (np.array([20, 20, 28], np.float32) - c) * al
    add(canvas, glow(cam.F * 0.9 / z0, (255, 200, 120), 0.3), x1, y1, 0.8)


def objects_sewer(canvas, cam, t):
    items = []
    items.append((cam.project(TU.pos)[2], lambda: draw_gift(canvas, cam, TU, t, reflect_y=WATER_Y)))
    for lz in LAMPS_Z:
        x, y, z = cam.project(v3(0, 3.95, lz))
        if z > 0.3:
            add(canvas, glow(cam.F * 0.5 / z, (255, 210, 130), 0.4), x, y, 0.6)
    # dog: falls from the roof shaft, floats, then the slime geyser throws it up
    land = v3(SHAFT[0], WATER_Y - 0.15, SHAFT[1])
    if t < 29.62:
        u = ease_in((t - 29.19) / 0.43)
        base = land + v3(0, 4.0 * (1 - u), 0)
    elif t < 36.30:
        base = land + v3(0, 0.05 * math.sin(t * 2.6), 0)
    else:
        base = land + v3(0, 12.0 * ease_in((t - 36.30) / 1.0), 0)
    rot = 0.15 * math.sin(t * 1.7) if t < 36.3 else -0.5 * (t - 36.3)
    img = dog_img(t, 400)
    items.append((cam.project(base)[2], lambda: billboard(canvas, cam, img, base, DOG_H, 0.98, rot, reflect_y=WATER_Y)))
    for _, fn in sorted(items, key=lambda it: -it[0]):
        fn()
    # splash
    if 29.6 <= t < 30.4:
        age = (t - 29.6) / 0.8
        for i in range(26):
            a = i / 26 * 6.283
            p = land + v3(math.cos(a) * (0.3 + 1.2 * age), 0.2 + 1.6 * age - 2.6 * age * age, math.sin(a) * 0.4 * age)
            x, y, z = cam.project(p)
            if z > 0.3:
                add(canvas, glow(cam.F * 0.07 / z, (150, 255, 140), 0.6), x, y, 1 - age)
    # geyser: bubbles first, then a column of slime under the dog
    if 35.30 <= t < 37.4:
        for i in range(70):
            t0 = 35.30 + i * 0.022
            age = (t - t0) / 0.9
            if 0 < age < 1:
                strong = t > 36.25
                h = (0.4 + (11.0 if strong else 0.6) * ease_out(age))
                p = land + v3(0.35 * math.sin(i * 2.1), h * (0.6 + 0.4 * math.sin(i * 1.3) ** 2), 0.3 * math.cos(i * 1.7))
                x, y, z = cam.project(p)
                if z > 0.3:
                    add(canvas, glow(cam.F * (0.18 if strong else 0.08) / z, (120, 255, 90), 0.5), x, y, 0.9 * (1 - age))


def objects_space(canvas, cam, t):
    items = []
    items.append((cam.project(MG.pos)[2], lambda: draw_gift(canvas, cam, MG, t)))
    dogp = v3(0.0, 0.0, 0.0)
    if t < 38.3:
        dogp = v3(0, -7.0 * (1 - ease_out((t - 37.3) / 1.0)), 0)
    dogp = dogp + v3(0, 0.08 * math.sin(t * 1.4), 0)
    car_b = v3(0.4, -0.55, 0.7)
    if t >= 44.55:
        car_b = car_b + v3(0, -16.0 * ease_in((t - 44.55) / 1.15), 0)
    if t < 44.2:
        img = dog_img(t, 400)
        rot = 0.25 * math.sin(t * 0.9)
        items.append((cam.project(dogp)[2], lambda: billboard(canvas, cam, img, dogp, DOG_H, 0.5, rot)))
    elif t < 44.55:
        base, u = hop(dogp, car_b + v3(0.4, 0.6, 0), t, 44.2, 44.55, 0.8)
        img = dog_img(t, 300)
        items.append((cam.project(base)[2], lambda: billboard(canvas, cam, img, base, DOG_H * (1 - 0.3 * u), 0.5)))
    if t >= 42.65:
        s = pop(t, 42.65)
        imgc = car_img('small', t, dog=t >= 44.55)
        rot = 0.0 if t < 44.55 else -0.35 * ease((t - 44.55) / 0.4)
        items.append((cam.project(car_b)[2], lambda: draw_vehicle(canvas, cam, imgc, car_b, CAR_LEN * 0.85 * s, rot)))
        if t >= 44.6:                                   # re-entry flames trailing up
            for i in range(40):
                age = ((t - 44.6) * 3 + i / 40) % 1.0
                p = car_b + v3(0.2 * math.sin(i * 2.7), 0.4 + 2.5 * age, -0.2)
                x, y, z = cam.project(p)
                if z > 0.3:
                    add(canvas, glow(cam.F * 0.35 * (1 - age) / z, (255, 140 + int(80 * (1 - age)), 40), 0.4), x, y, 0.8 * (1 - age))
    for _, fn in sorted(items, key=lambda it: -it[0]):
        fn()


def objects_kitchen(canvas, cam, t):
    items = []
    pot_base = v3(-2.8, 0, 3.8)
    items.append((cam.project(pot_base)[2], lambda: billboard(canvas, cam, POT, pot_base, 2.6, 0.97)))
    items.append((cam.project(BP.pos)[2], lambda: draw_gift(canvas, cam, BP, t)))
    small_b = v3(-1.3, 0, 2.2)
    if t < 46.05:                                   # the small car drops out of the steam
        u = ease_in((t - 45.7) / 0.35)
        small_b = small_b + v3(-1.2 * (1 - u), 3.2 * (1 - u), 1.0 * (1 - u))
    sq = fx.bump(max(0.0, t - 46.05), 3.0, 6.0) if t > 46.05 else 0.0
    imgs = car_img('small', t, dog=t < 49.3)
    items.append((cam.project(small_b)[2], lambda: draw_vehicle(canvas, cam, imgs, small_b, CAR_LEN * 0.85, sxy=(1 + 0.08 * sq, 1 - 0.1 * sq))))
    if t >= 48.55:
        taxi_b = v3(2.4, 0, 2.0)
        if t > 50.95:
            taxi_b[0] += 9.0 * (t - 50.95) ** 2
        s = pop(t, 48.55)
        imgt = car_img('taxi', t, dog=t >= 49.75)
        items.append((cam.project(taxi_b)[2], lambda: draw_vehicle(canvas, cam, imgt, taxi_b, CAR_LEN * s)))
    if 49.3 <= t < 49.75:
        base, u = hop(v3(-1.0, 0.5, 2.15), v3(2.6, 0.6, 1.95), t, 49.3, 49.75, 1.3)
        img = dog_img(t, 300)
        items.append((cam.project(base)[2], lambda: billboard(canvas, cam, img, base, DOG_H * 0.8, 0.98)))
    for _, fn in sorted(items, key=lambda it: -it[0]):
        fn()
    if 46.05 <= t < 46.9:                            # flour-like puff when the small car lands
        age = (t - 46.05) / 0.85
        for i in range(24):
            a = i / 24 * 6.283
            p = v3(-1.3, 0.1, 2.2) + v3(math.cos(a) * (1.0 + 1.4 * age), 0.4 * age + 0.2 * abs(math.sin(i)), math.sin(a) * 0.5)
            x, y, z = cam.project(p)
            if z > 0.3:
                add(canvas, glow(cam.F * (0.18 + 0.3 * age) / z, (255, 240, 215), 0.0), x, y, 0.45 * (1 - age))
    mx, my, mz = cam.project(v3(3.75, 3.65, WALL_Z - 0.02))      # the moon seen through the window
    if mz > 0.3:
        add(canvas, glow(cam.F * 0.55 / mz, (190, 220, 200), 0.0), mx, my, 0.35)
        add(canvas, glow(cam.F * 0.16 / mz, (255, 255, 240), 0.95), mx, my, 1.0)
    # steam from the pot
    for i in range(40):
        age = ((t * 0.35) + i / 40) % 1.0
        p = pot_base + v3(0.9 * math.sin(i * 1.9 + t * 0.7), 2.4 + 3.0 * age, 0.2 * math.cos(i * 2.3))
        x, y, z = cam.project(p)
        if z > 0.3:
            add(canvas, glow(cam.F * (0.35 + 0.6 * age) / z, (255, 255, 255), 0.0), x, y, 0.22 * (1 - age))


OBJECTS = [objects_swamp, objects_street, objects_sewer, objects_space, objects_kitchen]

# ---------------------------------------------------------------- swamp extras: stars, moon, reeds, fireflies
STARS = rng.normal(size=(900, 3)); STARS[:, 1] = np.abs(STARS[:, 1]) + 0.02
STARS /= np.linalg.norm(STARS, axis=1, keepdims=True)
STAR_MAG = rng.uniform(0.25, 1.0, 900) ** 2.5
SPACE_STARS = rng.normal(size=(2200, 3)); SPACE_STARS /= np.linalg.norm(SPACE_STARS, axis=1, keepdims=True)
SPACE_MAG = rng.uniform(0.2, 1.0, 2200) ** 3
NF = 200
FIREFLIES = np.column_stack([rng.uniform(-10, 14, NF), rng.uniform(0.25, 3.4, NF), rng.uniform(-6, 30, NF)])
FF_PHASE = rng.uniform(0, 6.28, (NF, 4))


def reed_cluster(cx, cz, n, hmin, hmax, seed):
    r = np.random.default_rng(seed)
    return [(cx + r.uniform(-0.45, 0.45), cz + r.uniform(-0.3, 0.3), r.uniform(hmin, hmax),
             r.uniform(-0.25, 0.25), r.uniform(0, 6.28), r.random() < 0.55) for _ in range(n)]


REEDS = sum((reed_cluster(x, z, 8, 1.2, 2.8, i) for i, (x, z) in enumerate(
    [(-4.5, 6), (3.5, 13), (12, 15.5), (-1.5, 14), (10.5, 5), (-7, 2), (8, 26), (-3.6, -3.2), (6.6, -1.0), (-5.5, 0.5)])), [])


def draw_reeds(canvas, cam, t):
    layer = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(layer)
    for bx, bz, h, lean, ph, head in REEDS:
        sway = lean + 0.07 * math.sin(t * 1.6 + ph)
        base = v3(bx, 0.0, bz); top = v3(bx + sway, h, bz)
        x0, y0, z0 = cam.project(base); x1, y1, z1 = cam.project(top)
        if z0 < 0.25 or z1 < 0.25 or max(x0, x1) < -50 or min(x0, x1) > W + 50:
            continue
        d.line([(x0, y0), (x1, y1)], fill=255, width=max(1, int(cam.F * 0.035 / z0)))
        if head:
            hc = cam.project(base + (top - base) * 0.82)
            hw = max(2, cam.F * 0.06 / z0); hh = max(4, cam.F * 0.34 / z0)
            d.ellipse([hc[0] - hw, hc[1] - hh / 2, hc[0] + hw, hc[1] + hh / 2], fill=255)
    box = layer.getbbox()
    if box:
        x0, y0, x1, y1 = box
        a = np.asarray(layer.crop(box), np.float32)[..., None] / 255.0
        c = canvas[y0:y1, x0:x1]
        c += (TREES * 1.1 - c) * a


def sky_points(canvas, cam, pts, mags, t, trees):
    sx, sy, sz = cam.project(cam.C + pts * 100)
    vis = (sz > 0) & (sx > -4) & (sx < W + 4) & (sy > -4) & (sy < H + 4)
    if trees:
        vis &= pts[:, 1] > treeline(np.arctan2(pts[:, 0], pts[:, 2])) + 0.01
    for i in np.nonzero(vis)[0]:
        add(canvas, glow(3 + 3 * mags[i], (230, 240, 255), 0.85), sx[i], sy[i], mags[i] * (0.8 + 0.2 * math.sin(t * 3 + i)))


# ================================================================ one sharp sub-frame
def scene(t):
    k = scene_index(t)
    cam = Cam(t)
    canvas = None
    pc, prot = page_center(t)
    psx, psy, pz = cam.project(pc) if k == 0 else (0, 0, -1)
    s_page = cam.F * PAGE_WORLD_H / pz / PAGE_H if pz > 0.2 else 0
    covered = (k == 0 and pz > 0.2 and psx - PAGE_W * s_page / 2 < -30 and psx + PAGE_W * s_page / 2 > W + 30
               and psy - PAGE_H * s_page / 2 < -30 and psy + PAGE_H * s_page / 2 > H + 30)
    if covered:
        canvas = np.zeros((H, W, 3), np.float32)
    else:
        bg = BG[k](cam, t)
        canvas = np.asarray(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
        if k in (0, 1):
            sky_points(canvas, cam, STARS[:400] if k == 1 else STARS, STAR_MAG, t, trees=(k == 0))
            mx, my, mz = cam.project(cam.C + MOON * 100)
            if mz > 0:
                add(canvas, glow(cam.F * 0.18, (190, 220, 200), 0.0), mx, my, 0.35)
                add(canvas, glow(cam.F * 0.045, (255, 255, 240), 0.95), mx, my, 1.0)
        if k == 3:
            sky_points(canvas, cam, SPACE_STARS, SPACE_MAG, t, trees=False)
        if k == 0:
            draw_reeds(canvas, cam, t)
        OBJECTS[k](canvas, cam, t)
        if k == 0:
            for i, (bx, by, bz) in enumerate(FIREFLIES):
                ph = FF_PHASE[i]
                p = v3(bx + 0.35 * math.sin(t * 0.7 + ph[0]), by + 0.2 * math.sin(t * 1.1 + ph[1]), bz + 0.35 * math.sin(t * 0.5 + ph[2]))
                x, y, z = cam.project(p)
                if z > 0.5 and -60 < x < W + 60 and -60 < y < H + 60:
                    add(canvas, glow(max(4, cam.F * 0.1 / z), FIREFLY, 0.5), x, y, (0.35 + 0.65 * max(0.0, math.sin(t * 2.2 + ph[3])) ** 2) * 1.1)
    if k == 0 and pz > 0.2 and t < 10.0:
        place(canvas, page_image(t), psx, psy, s_page, cam.roll + prot, alpha=1.0 - ease((t - 9.0) / 0.4))
    return canvas


# ================================================================ screen-space text (top), flashes, balloon
def _shadowed(draw_fn, h):
    im = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    sh = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(sh), 4, (0, 0, 0, 190))
    draw_fn(ImageDraw.Draw(im), 0, None)
    return np.asarray(Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), im), np.float32)


def card_parts(title, sub, value, item, note):
    def top(d, off, col):
        d.text((W / 2, 70 + off), title, font=fx.font('Bold', 88), fill=col or (255, 255, 255, 255), anchor='mm')
        if sub:
            d.text((W / 2, 148 + off), sub, font=fx.font('Semibold', 44), fill=col or MINT + (255,), anchor='mm')

    def bottom(d, off, col):
        d.text((W / 2, 50 + off), value, font=fx.font('Heavy', 76), fill=col or GOLD + (255,), anchor='mm')
        d.text((W / 2, 122 + off), item, font=fx.font('Semibold', 50), fill=col or (255, 255, 255, 255), anchor='mm')
        if note:
            d.text((W / 2, 180 + off), note, font=fx.font('Medium', 30), fill=col or (170, 190, 180, 255), anchor='mm')
    return _shadowed(top, 200), _shadowed(bottom, 220)


# (title, sub, value, item, note), name in/out, value in
CARDS = [
    (card_parts('Happy Pepe', 'в подарке Kissed Frog', '≈ 87 000 ₽', '= старые «Жигули»', '912,9 Gram · 1 Gram ≈ 95 ₽ · 03.11.2026'), 12.60, 19.70, 18.05),
    (card_parts('Pepe Paws', 'в подарке Scared Cat', '≈ 28 000 ₽', '= электросамокат', '290 Gram · 1 Gram ≈ 95 ₽ · 03.11.2026'), 21.45, 25.95, 24.45),
    (card_parts('Turtles', 'в подарке Heart Locket · 19 шт.', 'не продаются', 'ни за какие деньги', 'лотов нет · 03.11.2026'), 31.55, 35.30, 33.75),
    (card_parts('Meme God', 'шанс выпадения 1 из 1000', '≈ 71 000 ₽', '= маленькая старая машина', '745 Gram · 1 Gram ≈ 95 ₽ · 03.11.2026'), 39.85, 44.40, 42.65),
    (card_parts('Boiled Pepe', 'в подарке Easter Egg', '≈ 880 ₽', '= поездка на такси', '9,26 Gram · 1 Gram ≈ 95 ₽ · 03.11.2026'), 46.35, 50.90, 48.55),
]
CARD_Y = 130
QUESTION = card_parts('Что на них купишь?', None, '', '', None)[0]
FINAL_BALLOON = balloon('Feels good, man', 70)


def sparkle_sprite(size, rot):
    key = ('sp', size, int(rot * 10) % 63)
    if key not in _cache:
        s = size * 4
        im = Image.new('L', (s, s), 0)
        pts = []
        for k in range(8):
            rr = s * (0.48 if k % 2 == 0 else 0.13)
            a = rot + k * math.pi / 4
            pts.append((s / 2 + rr * math.cos(a), s / 2 + rr * math.sin(a)))
        ImageDraw.Draw(im).polygon(pts, fill=255)
        g = np.asarray(im.resize((size, size), Image.LANCZOS), np.float32)[..., None] / 255.0
        _cache[key] = g * (np.asarray(GOLD, np.float32) / 255.0)
    return _cache[key]


def overlay(canvas, t):
    for (top, bottom), t0, t1, tv in CARDS:
        a = ease((t - t0) / 0.35) * (1 - ease((t - t1) / 0.3))
        if a > 0:
            blend(canvas, top, 0, CARD_Y - 30 * (1 - a), a)
            b = ease((t - tv) / 0.3) * (1 - ease((t - t1) / 0.3))
            if b > 0:
                sc = 1 + 0.25 * (1 - ease((t - tv) / 0.25))
                blend(canvas, bottom, 0, CARD_Y + 200 + 20 * (1 - b), b) if sc < 1.01 else \
                    place(canvas, Image.fromarray(bottom.astype(np.uint8), 'RGBA'), W / 2, CARD_Y + 310, sc, 0.0, b)
    for _, t0, t1, tv in CARDS:
        age = (t - tv) / 0.8
        if 0 <= age < 1:
            for i in range(18):
                ang = i / 18 * 6.283 + 0.3
                r = 120 + 360 * fx.ease_out(age) * (0.7 + 0.3 * math.sin(i * 3.7))
                x, y = W / 2 + math.cos(ang) * r, CARD_Y + 290 + math.sin(ang) * r * 0.45
                add(canvas, sparkle_sprite(int(26 * (1 - age) + 6), ang + t * 4), x, y, 1.0 - age)
    a = ease((t - 11.40) / 0.25) * (1 - ease((t - 12.45) / 0.25))
    if a > 0:
        blend(canvas, QUESTION, 0, CARD_Y + 20, a)
    if t > 51.06:
        x = t - 51.06
        place(canvas, FINAL_BALLOON, W / 2 + 30, 430, max(0.05, fx.ease_out_back(min(1, x / 0.3), 2.2)), math.radians(-4), min(1, x / 0.08))
    # transition light: sewer darkness fade-in, slime flash, cloud/steam white
    flashes = [(29.19, 29.75, (0, 0, 0), 'out'), (37.15, 37.55, (150, 255, 120), 'peak'), (45.50, 46.05, (255, 255, 255), 'peak')]
    for t0, t1, col, mode in flashes:
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            a = (1 - u) if mode == 'out' else math.sin(math.pi * u) ** 0.7
            canvas += (np.asarray(col, np.float32) - canvas) * a


# ================================================================ frame with motion blur
def subframes(t):
    a, b = Cam(t - SHUTTER / 2), Cam(t + SHUTTER / 2)
    k = scene_index(t)
    probes = {0: [HP.pos + v3(0, 0.8, 0), DOG0, CAR_PAD, page_center(t)[0]], 1: [v3(0, 1, 2), PW.pos, HOLE],
              2: [TU.pos, v3(SHAFT[0], 1, SHAFT[1])], 3: [MG.pos, v3(0, 0, 0)], 4: [BP.pos, v3(2.4, 0.5, 2.0)]}[k]
    move = 0.0
    for Pw in probes:
        x0, y0, z0 = a.project(Pw); x1, y1, z1 = b.project(Pw)
        if z0 > 0.3 and z1 > 0.3:
            move = max(move, math.hypot(x1 - x0, y1 - y0))
    near_switch = any(abs(t - s) < 0.05 for s in SW)
    return int(min(12, max(6 if near_switch else 1, math.ceil(move / 5))))


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
