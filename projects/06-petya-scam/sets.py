"""Backgrounds drawn in code (flat 2D, no outlines), each cached once: 1080×1920 RGBA.

room(mode)   — Petya's room seen from his desk: wall, window, posters, shelf, bed corner; modes 'eve' (warm
               evening), 'night' (blue, moon), 'party' (dark + coloured light blobs).
desk(mode)   — the desk edge in front of a bust (separate layer, drawn over the character).
bedroom()    — Petya asleep: night window, pillow, blanket (the head is added by the renderer).
dima_room()  — a younger kid's room: light green, planet poster, daylight window.
katya_flat() — a rich flat: cream walls, panoramic window with a dusk city, monstera, gold floor lamp.
"""
import functools
import math
import random

import numpy as np
from PIL import Image, ImageFilter

from art import Layer, mixc, shade

W, H = 1080, 1920


def _grad(top, bot, w=W, h=H):
    a = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    rgb = np.array(top, np.float32) * (1 - a) + np.array(bot, np.float32) * a
    rgb = np.repeat(rgb, w, axis=1)
    return Image.fromarray(np.dstack([rgb, np.full((h, w, 1), 255, np.float32)]).astype(np.uint8), 'RGBA')


PAL = {
    'eve': dict(wall=((238, 214, 186), (214, 182, 156)), sky=((255, 170, 120), (255, 214, 160)), light=1.0,
                wood=(170, 112, 76), poster=((70, 110, 190), (240, 90, 80))),
    'night': dict(wall=((52, 60, 98), (34, 38, 70)), sky=((16, 22, 54), (40, 52, 104)), light=0.4,
                  wood=(84, 62, 70), poster=((44, 62, 112), (120, 56, 74))),
    'party': dict(wall=((46, 30, 74), (24, 16, 44)), sky=((12, 14, 40), (30, 30, 80)), light=0.3,
                  wood=(70, 46, 64), poster=((60, 50, 130), (150, 50, 110))),
}


def _window(L, x0, y0, w, h, sky, moon=False, stars=False, city=False, seed=1):
    L.poly([(x0 - 22, y0 - 22), (x0 + w + 22, y0 - 22), (x0 + w + 22, y0 + h + 22), (x0 - 22, y0 + h + 22)],
           (246, 244, 240) if not moon else (150, 160, 190))
    sk = Image.new('RGBA', (w, h))
    g = _grad(sky[0], sky[1], w, h)
    sk.alpha_composite(g)
    L.im.paste(g.resize((w * L.ss, h * L.ss)), (int(x0 * L.ss), int(y0 * L.ss)))
    rnd = random.Random(seed)
    if stars:
        for _ in range(26):
            x, y = x0 + rnd.uniform(10, w - 10), y0 + rnd.uniform(10, h * 0.7)
            r = rnd.uniform(1.6, 3.4)
            L.ell(x, y, r, r, (255, 250, 220), alpha=rnd.uniform(0.5, 1))
    if moon:
        L.ell(x0 + w * 0.7, y0 + h * 0.28, 46, 46, (255, 246, 210))
        L.ell(x0 + w * 0.7, y0 + h * 0.28, 90, 90, (255, 246, 210), alpha=0.15, blur=20)
    if city:
        for k in range(9):
            bx = x0 + k * w / 9
            bh = rnd.uniform(0.18, 0.5) * h
            col = mixc(sky[1], (20, 20, 40), 0.55)
            L.poly([(bx, y0 + h), (bx, y0 + h - bh), (bx + w / 9 - 6, y0 + h - bh), (bx + w / 9 - 6, y0 + h)], col)
            for yy in range(int(y0 + h - bh + 14), int(y0 + h - 10), 26):
                for xx in range(int(bx + 8), int(bx + w / 9 - 14), 20):
                    if rnd.random() < 0.45:
                        L.poly([(xx, yy), (xx + 8, yy), (xx + 8, yy + 11), (xx, yy + 11)], (255, 214, 130))
    # frame bars
    fc = (246, 244, 240) if not moon else (150, 160, 190)
    L.poly([(x0 + w / 2 - 8, y0), (x0 + w / 2 + 8, y0), (x0 + w / 2 + 8, y0 + h), (x0 + w / 2 - 8, y0 + h)], fc)
    L.poly([(x0, y0 + h * 0.42 - 8), (x0 + w, y0 + h * 0.42 - 8), (x0 + w, y0 + h * 0.42 + 8),
            (x0, y0 + h * 0.42 + 8)], fc)


@functools.lru_cache(maxsize=4)
def room(mode='eve'):
    P = PAL[mode]
    base = _grad(*P['wall'])
    L = Layer(W, H, ss=2)
    L.im = base.resize((W * 2, H * 2))
    night = mode != 'eve'
    _window(L, 90, 300, 380, 460, P['sky'], moon=night, stars=night, seed=3)
    # curtain
    L.shape([(40, 250), (120, 250), (100, 600), (130, 820), (50, 840)], shade((200, 90, 70), 0.9 if night else 1))
    # posters
    c1, c2 = P['poster']
    L.poly([(640, 330), (900, 312), (912, 640), (650, 652)], c1)
    L.ell(775, 470, 70, 70, (255, 214, 90) if not night else (180, 160, 90))           # planet
    L.ell(775, 470, 120, 22, (255, 255, 255), rot=-0.3, alpha=0.6)
    L.poly([(930, 700), (1060, 690), (1066, 900), (938, 906)], c2)
    L.stroke([(960, 760), (1000, 800), (1040, 740)], 10, (255, 255, 255), alpha=0.8)  # game «zigzag»
    # shelf with little things
    L.poly([(560, 800), (900, 800), (900, 822), (560, 822)], P['wood'])
    L.poly([(580, 730), (610, 730), (610, 800), (580, 800)], (90, 140, 200))
    L.poly([(616, 744), (644, 744), (644, 800), (616, 800)], (230, 120, 80))
    L.poly([(650, 720), (676, 720), (676, 800), (650, 800)], (240, 200, 90))
    L.ell(800, 770, 30, 30, (120, 200, 140))
    L.poly([(840, 760), (880, 760), (876, 800), (844, 800)], (240, 240, 240))
    # LED strip along the ceiling (glows at night / party)
    led = (120, 90, 255) if mode == 'party' else (255, 120, 200) if night else (255, 240, 220)
    L.poly([(0, 120), (W, 120), (W, 132), (0, 132)], led, alpha=0.9 if night else 0.4)
    if night:
        L.poly([(0, 132), (W, 132), (W, 260), (0, 260)], led, alpha=0.18, blur=30)
    im = L.image()
    if mode == 'party':
        rnd = random.Random(4)
        glow = Layer(W, H, ss=1)
        for _ in range(7):
            col = rnd.choice([(255, 60, 180), (60, 200, 255), (255, 200, 60), (140, 80, 255)])
            glow.ell(rnd.uniform(0, W), rnd.uniform(200, 1300), rnd.uniform(160, 300), rnd.uniform(160, 300), col,
                     alpha=0.35, blur=60)
        im.alpha_composite(glow.image())
    return im


@functools.lru_cache(maxsize=4)
def desk(mode='eve'):
    P = PAL[mode]
    L = Layer(W, H, ss=2)
    top = P['wood']
    L.poly([(-10, 1500), (W + 10, 1490), (W + 10, 1560), (-10, 1570)], mixc(top, (255, 255, 255), 0.15))
    L.poly([(-10, 1566), (W + 10, 1556), (W + 10, H), (-10, H)], shade(top, 0.8))
    # lamp
    L.poly([(130, 1500), (150, 1500), (150, 1300), (130, 1300)], (60, 60, 70))
    L.shape([(70, 1300), (210, 1300), (180, 1220), (100, 1220)], (240, 200, 90) if mode == 'eve' else (90, 90, 110))
    L.poly([(90, 1494), (190, 1494), (190, 1506), (90, 1506)], (60, 60, 70))
    # mug
    L.poly([(900, 1420), (970, 1420), (964, 1500), (906, 1500)], (240, 90, 80))
    L.stroke([(968, 1440), (995, 1452), (966, 1480)], 8, (240, 90, 80))
    return L.image()


@functools.lru_cache(maxsize=1)
def bedroom():
    P = PAL['night']
    L = Layer(W, H, ss=2)
    L.im = _grad((40, 46, 86), (24, 28, 56)).resize((W * 2, H * 2))
    _window(L, 300, 220, 480, 520, P['sky'], moon=True, stars=True, seed=7)
    L.ell(540, 700, 520, 320, (180, 200, 255), alpha=0.08, blur=60)            # moonlight
    # bed: headboard, mattress, pillow
    L.poly([(-20, 960), (120, 960), (120, 1700), (-20, 1700)], (90, 70, 96))
    L.poly([(60, 1180), (W + 20, 1180), (W + 20, 1520), (60, 1520)], (226, 228, 240))
    L.poly([(60, 1500), (W + 20, 1500), (W + 20, H), (60, H)], (70, 56, 84))
    L.shape([(110, 1080), (420, 1060), (460, 1180), (420, 1270), (110, 1280), (80, 1180)], (238, 240, 250))
    return L.image()


@functools.lru_cache(maxsize=1)
def blanket():
    L = Layer(W, H, ss=2)
    bm = L.shape([(300, 1300), (520, 1180), (800, 1150), (1100, 1170), (1100, 1560), (300, 1560), (260, 1440)],
                 (92, 120, 200))
    L.shape([(300, 1300), (520, 1180), (800, 1150), (1100, 1170), (1100, 1230), (520, 1250), (300, 1360)],
            (120, 150, 220), clip=bm)
    for k in range(4):
        L.stroke([(420 + k * 170, 1260), (470 + k * 170, 1480)], 6, (80, 104, 180), alpha=0.6)
    return L.image()


@functools.lru_cache(maxsize=1)
def dima_room():
    L = Layer(W, H, ss=2)
    L.im = _grad((206, 236, 214), (176, 214, 190)).resize((W * 2, H * 2))
    _window(L, 620, 300, 360, 440, ((140, 200, 255), (210, 236, 255)), seed=2)
    L.ell(700, 520, 60, 26, (255, 255, 255), alpha=0.9)
    L.ell(760, 500, 46, 30, (255, 255, 255), alpha=0.9)
    L.poly([(90, 330), (420, 316), (430, 700), (100, 712)], (40, 50, 110))
    for k in range(12):
        L.ell(120 + (k * 37) % 290, 350 + (k * 71) % 330, 3, 3, (255, 255, 230))
    L.ell(260, 520, 80, 80, (240, 140, 90))
    L.ell(260, 520, 140, 26, (255, 230, 180), rot=0.35, alpha=0.7)
    L.poly([(0, 1480), (W, 1470), (W, H), (0, H)], (150, 110, 90))
    return L.image()


@functools.lru_cache(maxsize=1)
def katya_flat():
    L = Layer(W, H, ss=2)
    L.im = _grad((246, 236, 226), (228, 212, 198)).resize((W * 2, H * 2))
    _window(L, 60, 200, 960, 900, ((120, 90, 160), (255, 170, 150)), city=True, seed=11)
    # sheer curtains
    L.poly([(30, 170), (150, 170), (130, 1130), (30, 1140)], (255, 250, 245), alpha=0.75)
    L.poly([(930, 170), (1050, 170), (1050, 1140), (950, 1130)], (255, 250, 245), alpha=0.75)
    # gold floor lamp
    L.poly([(950, 1600), (962, 1600), (962, 980), (950, 980)], (210, 170, 90))
    L.shape([(890, 990), (1020, 990), (990, 900), (920, 900)], (250, 236, 210))
    L.ell(956, 960, 120, 120, (255, 220, 160), alpha=0.25, blur=30)
    # monstera
    for a, r in ((-2.4, 190), (-1.9, 220), (-1.3, 200), (-2.8, 160), (-1.6, 150)):
        cx, cy = 140 + math.cos(a) * r * 0.6, 1420 + math.sin(a) * r
        L.ell(cx, cy, 70, 42, (70, 140, 90), rot=a)
        L.stroke([(140, 1460), (cx, cy)], 6, (60, 120, 80))
    L.poly([(80, 1440), (200, 1440), (186, 1600), (94, 1600)], (240, 240, 236))
    L.poly([(0, 1560), (W, 1550), (W, H), (0, H)], (210, 190, 170))
    return L.image()


@functools.lru_cache(maxsize=4)
def blurred(name, mode=None, r=22, dark=0.35):
    im = {'room': lambda: room(mode), 'katya': katya_flat, 'dima': dima_room, 'bed': bedroom}[name]()
    im = im.filter(ImageFilter.GaussianBlur(r))
    a = np.asarray(im, np.float32)
    a[..., :3] *= 1 - dark
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


# ------------------------------------------------------------------ places for full-body poses (2026-11-05)
@functools.lru_cache(maxsize=4)
def room_floor(mode='eve'):
    """Petya's room with the floor visible (for standing / walking / jumping)."""
    P = PAL[mode]
    im = room(mode).copy()
    L = Layer(W, H, ss=2)
    wood = mixc(P['wood'], (255, 255, 255), 0.1)
    L.poly([(0, 1460), (W, 1460), (W, H), (0, H)], wood)
    for k in range(7):
        y = 1500 + k * 64 + k * k * 4
        L.stroke([(0, y), (W, y)], 3, shade(wood, 0.85), alpha=0.6)
    L.poly([(0, 1440), (W, 1440), (W, 1466), (0, 1466)], shade(wood, 0.75))
    L.ell(540, 1720, 420, 120, (200, 80, 90) if mode == 'eve' else (90, 70, 130), alpha=0.85)
    L.ell(540, 1720, 360, 96, (230, 120, 110) if mode == 'eve' else (120, 96, 160), alpha=0.6)
    im.alpha_composite(L.image())
    return im


@functools.lru_cache(maxsize=4)
def bed_left(mode='night'):
    """A bed on the left half (Petya sits on it while chatting): headboard, mattress top at y≈1260."""
    L = Layer(W, H, ss=2)
    night = mode != 'eve'
    frame = (96, 74, 100) if night else (150, 104, 80)
    L.poly([(-40, 920), (70, 920), (70, 1600), (-40, 1600)], frame)
    L.poly([(-40, 1250), (700, 1250), (700, 1560), (-40, 1560)], (222, 226, 240) if not night else (150, 160, 200))
    L.poly([(-40, 1236), (700, 1236), (700, 1262), (-40, 1262)], (240, 242, 250) if not night else (170, 180, 220))
    bl = (92, 120, 200) if not night else (60, 80, 150)
    L.shape([(300, 1250), (700, 1240), (700, 1580), (260, 1580), (240, 1420)], bl)
    L.shape([(30, 1110), (200, 1100), (230, 1180), (210, 1250), (30, 1256)], (238, 240, 250) if not night
            else (180, 190, 225))
    L.poly([(-40, 1560), (700, 1560), (700, 1640), (-40, 1640)], shade(frame, 0.8))
    return L.image()


@functools.lru_cache(maxsize=1)
def sofa():
    """Katya's velvet sofa (behind her, she sits on the cushion at y≈1312)."""
    L = Layer(W, H, ss=2)
    v, v2 = (226, 170, 180), (196, 138, 152)
    L.shape([(90, 1060), (990, 1060), (1000, 1330), (80, 1330)], v)
    for k in range(3):
        L.stroke([(240 + k * 300, 1090), (240 + k * 300, 1300)], 5, v2, alpha=0.7)
    L.shape([(60, 1290), (1020, 1290), (1030, 1400), (50, 1400)], mixc(v, (255, 255, 255), 0.12))
    L.poly([(50, 1390), (1030, 1390), (1030, 1500), (50, 1500)], v2)
    for s in (-1, 1):
        x = 540 + s * 470
        L.shape([(x - 70, 1160), (x + 70, 1160), (x + 80, 1500), (x - 80, 1500)], v)
        L.ell(x, 1170, 75, 40, mixc(v, (255, 255, 255), 0.15))
    for x in (120, 960):
        L.poly([(x - 12, 1500), (x + 12, 1500), (x + 8, 1560), (x - 8, 1560)], (200, 160, 80))
    L.ell(800, 1250, 70, 60, (255, 236, 200), rot=0.3)            # a pillow
    return L.image()


@functools.lru_cache(maxsize=1)
def corridor():
    """School corridor in one-point perspective (Dima walks towards the camera). 1400×2490, zoom it in."""
    w, h = 1400, 2490
    L = Layer(w, h, ss=1)
    L.im = _grad((236, 244, 236), (210, 226, 214), w, h).resize((w, h))
    vx, vy = w / 2, h * 0.43
    # floor
    L.poly([(0, h), (w, h), (vx + 160, vy + 120), (vx - 160, vy + 120)], (196, 176, 150))
    for k in range(1, 14):
        f = (k / 14) ** 2
        y = vy + 120 + (h - vy - 120) * f
        L.stroke([(vx - 160 - (vx - 0 - 160) * f, y), (vx + 160 + (w - vx - 160) * f, y)], 3, (170, 150, 128),
                 smooth=False)
    # ceiling
    L.poly([(0, 0), (w, 0), (vx + 160, vy - 260), (vx - 160, vy - 260)], (246, 248, 244))
    for k in range(1, 6):
        f = (k / 6) ** 2
        y = vy - 260 - (vy - 260) * f
        hw = 60 + 300 * f
        L.poly([(vx - hw, y - 10 * (1 + f * 3)), (vx + hw, y - 10 * (1 + f * 3)), (vx + hw, y), (vx - hw, y)],
               (255, 255, 236))
    # back wall with a door and a window
    L.poly([(vx - 160, vy - 260), (vx + 160, vy - 260), (vx + 160, vy + 120), (vx - 160, vy + 120)], (200, 222, 206))
    L.poly([(vx - 60, vy - 120), (vx + 60, vy - 120), (vx + 60, vy + 120), (vx - 60, vy + 120)], (170, 120, 90))
    # lockers on both side walls
    for s in (-1, 1):
        for k in range(8):
            f0, f1 = ((k) / 8) ** 1.6, ((k + 0.9) / 8) ** 1.6
            def P(f, yy):
                x = vx + s * (160 + (vx - 160) * f) if s > 0 else vx - (160 + (vx - 160) * f)
                top = vy - 120 - (vy - 120 - h * 0.22) * f
                bot = vy + 120 + (h * 0.86 - vy - 120) * f
                return (x, top + (bot - top) * yy)
            col = (238, 140, 70) if k % 2 == 0 else (90, 150, 210)
            L.poly([P(f0, 0), P(f1, 0), P(f1, 1), P(f0, 1)], col)
            L.stroke([P((f0 + f1) / 2, 0.15), P((f0 + f1) / 2, 0.85)], 2 + 6 * f1, shade(col, 0.8), smooth=False)
    return L.image()
