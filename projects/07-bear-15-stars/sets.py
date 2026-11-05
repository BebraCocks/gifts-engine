"""Backgrounds and props of «Мишка за 15 звёзд» (flat 2D, own drawing). All cached; W×H = 1080×1920.

show()            the «top-3» stage: violet gradient, gold stars, soft spotlight
room(phase)       a small room with a window; phase 0..1 = day → night → day (the window sky)
street()          a warm city sidewalk: brick wall, shop window, kerb
sofa_room()       living room: sofa, lamp, plant, rug
card(rank)        the place card «N МЕСТО» (bronze / silver / gold, gold gets a crown)
sign()            cardboard «НА ЛЕКАРСТВА», text only (author, 2026-11-05)
legs(phase, col)  a passer-by from the knees down, walking cycle
"""
import functools
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import tg
from art import Layer, mixc, shade

W, H = 1080, 1920
GOLD = (255, 200, 70)


def _grad(top, bot, w=W, h=H):
    k = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    rgb = np.array(top, np.float32) * (1 - k) + np.array(bot, np.float32) * k
    rgb = np.broadcast_to(rgb, (h, w, 3))
    return Image.fromarray(rgb.astype(np.uint8), 'RGB').convert('RGBA')


def star_pts(cx, cy, r, inner=0.45, rot=-math.pi / 2):
    return [(cx + r * (1 if i % 2 == 0 else inner) * math.cos(rot + i * math.pi / 5),
             cy + r * (1 if i % 2 == 0 else inner) * math.sin(rot + i * math.pi / 5)) for i in range(10)]


@functools.lru_cache(None)
def show():
    im = _grad((70, 40, 160), (22, 14, 62))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = np.exp(-((xx - W / 2) ** 2 / (2 * 420 ** 2) + (yy - 760) ** 2 / (2 * 620 ** 2)))[..., None]
    a = np.asarray(im).astype(np.float32)
    a[..., :3] += glow * np.array((70, 50, 120), np.float32)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    L = Layer(W, H, ss=2)
    rnd = random.Random(15)
    for _ in range(46):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(8, 26)
        L.poly(star_pts(x, y, r), GOLD, alpha=rnd.uniform(0.10, 0.35))
    for _ in range(160):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(1.5, 3.5)
        L.ell(x, y, r, r, (255, 255, 255), alpha=rnd.uniform(0.2, 0.7))
    im.alpha_composite(L.image())
    return im


def rays(t, cx=540, cy=760, n=14, alpha=0.10):
    """Slowly rotating light rays (additive layer)."""
    lay = Image.new('L', (W // 2, H // 2), 0)
    d = ImageDraw.Draw(lay)
    for k in range(n):
        a0 = t * 0.25 + k * 2 * math.pi / n
        a1 = a0 + math.pi / n * 0.55
        R = 2400
        d.polygon([(cx / 2, cy / 2), (cx / 2 + R * math.cos(a0), cy / 2 + R * math.sin(a0)),
                   (cx / 2 + R * math.cos(a1), cy / 2 + R * math.sin(a1))], fill=int(255 * alpha))
    lay = lay.filter(ImageFilter.GaussianBlur(12)).resize((W, H), Image.BILINEAR)
    return lay


@functools.lru_cache(maxsize=64)
def room(phase_q):
    """phase_q: quantised 0..1 (0 day, 0.5 night). Window sky + sun/moon arc; walls follow the light."""
    ph = phase_q
    night = 0.5 - 0.5 * math.cos(2 * math.pi * ph)          # 0 day .. 1 night
    wall = mixc((246, 222, 196), (70, 70, 120), night * 0.85)
    im = _grad(wall, shade(wall, 0.86))
    L = Layer(W, H, ss=2)
    # window
    x0, y0, w, h = 190, 260, 700, 760
    L.poly([(x0 - 30, y0 - 30), (x0 + w + 30, y0 - 30), (x0 + w + 30, y0 + h + 30), (x0 - 30, y0 + h + 30)],
           mixc((255, 255, 255), (150, 150, 190), night))
    sky_top = mixc((120, 190, 250), (16, 20, 58), night)
    sky_bot = mixc((200, 232, 255), (54, 46, 110), night)
    sky = _grad(sky_top, sky_bot, w, h)
    im.alpha_composite(L.image())
    L = Layer(W, H, ss=2)
    im.alpha_composite(sky, (x0, y0))
    # sun or moon on an arc
    a = math.pi * (1 - (ph * 2 % 1.0))
    bx, by = x0 + w / 2 + 300 * math.cos(a), y0 + h * 0.78 - 520 * math.sin(a)
    if night < 0.5:
        L.ell(bx, by, 70, 70, (255, 220, 110))
        L.ell(bx, by, 110, 110, (255, 230, 150), alpha=0.35, blur=10)
    else:
        L.ell(bx, by, 56, 56, (246, 244, 226))
        L.ell(bx + 22, by - 12, 50, 50, sky_top)
        rnd = random.Random(3)
        for _ in range(26):
            L.ell(x0 + rnd.uniform(20, w - 20), y0 + rnd.uniform(20, h * 0.6), 2.5, 2.5, (255, 255, 255),
                  alpha=(night - 0.5) * 2)
    # city skyline
    rnd = random.Random(9)
    x = x0
    bcol = mixc((150, 170, 200), (30, 30, 66), night)
    while x < x0 + w:
        bw, bh = rnd.uniform(70, 140), rnd.uniform(160, 380)
        L.poly([(x, y0 + h), (x, y0 + h - bh), (x + bw, y0 + h - bh), (x + bw, y0 + h)], bcol)
        if night > 0.5:
            for wy in range(int(y0 + h - bh + 20), int(y0 + h - 20), 46):
                for wx in range(int(x + 14), int(x + bw - 20), 34):
                    if rnd.random() < 0.4:
                        L.poly([(wx, wy), (wx + 14, wy), (wx + 14, wy + 20), (wx, wy + 20)], (255, 214, 120))
        x += bw + 6
    # frame cross
    fc = mixc((255, 255, 255), (150, 150, 190), night)
    L.poly([(x0 + w / 2 - 12, y0), (x0 + w / 2 + 12, y0), (x0 + w / 2 + 12, y0 + h), (x0 + w / 2 - 12, y0 + h)], fc)
    L.poly([(x0, y0 + h * 0.45 - 12), (x0 + w, y0 + h * 0.45 - 12), (x0 + w, y0 + h * 0.45 + 12),
            (x0, y0 + h * 0.45 + 12)], fc)
    # sill + desk
    L.poly([(x0 - 60, y0 + h + 30), (x0 + w + 60, y0 + h + 30), (x0 + w + 40, y0 + h + 70),
            (x0 - 40, y0 + h + 70)], shade(fc, 0.9))
    im.alpha_composite(L.image())
    return im


@functools.lru_cache(None)
def street():
    im = _grad((250, 214, 170), (236, 196, 160))
    L = Layer(W, H, ss=2)
    # brick wall
    wall = (196, 112, 86)
    L.poly([(0, 0), (W, 0), (W, 1380), (0, 1380)], wall)
    rnd = random.Random(4)
    for r in range(0, 1380, 54):
        off = 0 if (r // 54) % 2 == 0 else 60
        for c in range(-60, W + 60, 120):
            col = mixc(wall, (150, 80, 62), rnd.uniform(0.0, 0.45))
            L.poly([(c + off + 4, r + 4), (c + off + 116, r + 4), (c + off + 116, r + 50), (c + off + 4, r + 50)], col)
    # shop window with a gift poster
    L.poly([(560, 250), (1020, 250), (1020, 900), (560, 900)], (60, 52, 70))
    L.poly([(580, 270), (1000, 270), (1000, 880), (580, 880)], (130, 190, 220))
    L.poly([(580, 270), (720, 270), (580, 520)], (200, 232, 250), alpha=0.5)
    L.poly([(540, 200), (1040, 200), (1040, 250), (540, 250)], (60, 130, 110))
    # pipe + a poster on the wall
    L.poly([(70, 0), (110, 0), (110, 1380), (70, 1380)], (120, 120, 130))
    L.poly([(170, 420), (470, 400), (480, 760), (180, 780)], (244, 236, 210))
    L.poly(star_pts(325, 560, 90), GOLD)
    # sidewalk + kerb + road
    L.poly([(0, 1380), (W, 1380), (W, 1760), (0, 1760)], (190, 184, 178))
    for x in range(-100, W + 200, 230):
        L.stroke([(x, 1380), (x - 120, 1760)], 4, (160, 154, 150), smooth=False)
    L.poly([(0, 1380), (W, 1380), (W, 1400), (0, 1400)], (150, 140, 136))
    L.poly([(0, 1760), (W, 1760), (W, 1800), (0, 1800)], (210, 206, 200))
    L.poly([(0, 1800), (W, 1800), (W, H), (0, H)], (70, 70, 78))
    im.alpha_composite(L.image())
    return im


@functools.lru_cache(None)
def sofa_room():
    im = _grad((226, 206, 240), (196, 176, 220))
    L = Layer(W, H, ss=2)
    # picture frame + lamp + plant
    L.poly([(300, 300), (780, 300), (780, 640), (300, 640)], (250, 244, 236))
    L.poly([(326, 326), (754, 326), (754, 614), (326, 614)], (150, 200, 230))
    L.poly([(326, 614), (480, 450), (600, 560), (680, 480), (754, 560), (754, 614)], (90, 160, 110))
    L.ell(640, 400, 34, 34, (255, 226, 120))
    L.poly([(900, 700), (1040, 700), (1010, 820), (930, 820)], (255, 210, 120))
    L.poly([(964, 820), (976, 820), (980, 1300), (960, 1300)], (90, 80, 90))
    L.ell(970, 760, 160, 120, (255, 230, 160), alpha=0.25, blur=20)
    for k in range(7):
        a = -0.9 + k * 0.3
        L.ell(90 + 90 * math.sin(a), 980 - 120 * math.cos(a) * 0.6, 26, 70, (70, 150, 96), rot=a)
    L.poly([(50, 1000), (140, 1000), (130, 1120), (60, 1120)], (210, 120, 90))
    # floor + rug
    L.poly([(0, 1450), (W, 1450), (W, H), (0, H)], (176, 132, 104))
    L.ell(540, 1700, 520, 120, (240, 120, 120), alpha=0.85)
    L.ell(540, 1700, 420, 88, (250, 200, 120), alpha=0.6)
    im.alpha_composite(L.image())
    return im


@functools.lru_cache(None)
def sofa_front():
    """The sofa seat and arms (drawn over the hero's lower body)."""
    L = Layer(W, H, ss=2)
    col, sh = (90, 120, 200), (70, 94, 166)
    L.poly([(60, 1300), (1020, 1300), (1040, 1520), (40, 1520)], shade(col, 0.95))                  # seat
    L.shape([(-20, 1120), (40, 1080), (130, 1100), (150, 1180), (150, 1560), (-20, 1560)], sh)      # arms
    L.shape([(1100, 1120), (1040, 1080), (950, 1100), (930, 1180), (930, 1560), (1100, 1560)], sh)
    for x in (120, 960):
        L.poly([(x - 16, 1520), (x + 16, 1520), (x + 10, 1580), (x - 10, 1580)], (70, 50, 40))
    return L.image()


@functools.lru_cache(None)
def sofa_back():
    L = Layer(W, H, ss=2)
    col = (90, 120, 200)
    L.shape([(30, 1100), (60, 900), (200, 860), (880, 860), (1020, 900), (1050, 1100), (1050, 1300), (30, 1300)],
            col)
    for x in (300, 540, 780):
        L.stroke([(x, 900), (x, 1240)], 5, shade(col, 0.85), alpha=0.6)
    return L.image()


# ------------------------------------------------------------------ props
RANKS = {1: ((205, 128, 72), (150, 84, 44)), 2: ((206, 212, 226), (140, 148, 170)), 3: ((255, 206, 80), (214, 150, 30))}


@functools.lru_cache(maxsize=8)
def card(rank, back=False):
    w, h = 600, 760
    im = Image.new('RGBA', (w, h + 160), (0, 0, 0, 0))
    L = Layer(w, h + 160, ss=2)
    c, s = RANKS[rank]
    L.ell(w / 2, h + 120, 240, 26, (0, 0, 0), alpha=0.28, blur=10)
    m = L.mask([(0, 160), (w, 160), (w, h + 100), (0, h + 100)])
    m = Image.new('L', (w * 2, (h + 160) * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([12, 320, w * 2 - 12, (h + 100) * 2], 80, fill=255)
    L.fill(m, s)
    m2 = Image.new('L', m.size, 0)
    ImageDraw.Draw(m2).rounded_rectangle([12, 320, w * 2 - 12, (h + 80) * 2], 80, fill=255)
    L.fill(m2, c)
    L.poly([(40, 200), (260, 200), (60, 520)], (255, 255, 255), alpha=0.18, clip=m2)
    im.alpha_composite(L.image())
    d = ImageDraw.Draw(im)
    if back:
        f = tg.font('Heavy', 300)
        d.text((w / 2, 160 + (h - 80) / 2), '?', font=f, fill=s, anchor='mm')
    else:
        f = tg.font('Heavy', 330)
        d.text((w / 2, 160 + 300), str(rank), font=f, fill=(255, 255, 255), anchor='mm')
        f2 = tg.font('Heavy', 78)
        d.text((w / 2, 160 + 590), 'МЕСТО', font=f2, fill=(255, 255, 255), anchor='mm')
    if rank == 3 and not back:
        L = Layer(w, h + 160, ss=2)
        L.poly([(170, 190), (190, 40), (250, 120), (300, 10), (350, 120), (410, 40), (430, 190)], GOLD)
        L.poly([(170, 170), (430, 170), (430, 200), (170, 200)], (214, 150, 30))
        for x in (190, 300, 410):
            L.ell(x, 30 if x == 300 else 50, 18, 18, (255, 90, 90))
        im.alpha_composite(L.image())
    return im


@functools.lru_cache(None)
def sign():
    w, h = 640, 440
    L = Layer(w, h, ss=2)
    L.poly([(14, 30), (626, 10), (630, 420), (6, 432)], (196, 150, 98))
    L.poly([(30, 40), (610, 26), (612, 404), (24, 414)], (212, 168, 114))
    L.stroke([(60, 80), (200, 70)], 3, (170, 124, 80), alpha=0.6)
    L.stroke([(420, 380), (580, 372)], 3, (170, 124, 80), alpha=0.6)
    im = L.image()
    d = ImageDraw.Draw(im)
    f = tg.font('Heavy', 84)
    for k, (line, y) in enumerate((('НА', 160), ('ЛЕКАРСТВА', 280))):      # text only (author, 2026-11-05)
        d.text((w / 2 + (k - 0.5) * 6, y), line, font=f, fill=(46, 40, 50), anchor='mm')
    return im


@functools.lru_cache(None)
def cup():
    L = Layer(200, 220, ss=2)
    L.poly([(30, 40), (170, 40), (150, 210), (50, 210)], (250, 250, 250))
    L.poly([(30, 40), (170, 40), (165, 80), (35, 80)], (220, 80, 80))
    L.ell(100, 40, 70, 14, (180, 180, 186))
    return L.image()


@functools.lru_cache(None)
def coin(size=90):
    L = Layer(size, size, ss=3)
    L.ell(size / 2, size / 2, size * 0.46, size * 0.46, (214, 150, 30))
    L.ell(size / 2, size / 2, size * 0.38, size * 0.38, GOLD)
    L.poly(star_pts(size / 2, size / 2, size * 0.22), (214, 150, 30))
    return L.image()


@functools.lru_cache(maxsize=160)
def legs(phase_q, col, shoe):
    """A passer-by from the hips down (box 520×960, hips at y≈20, soles at y≈930), walking right. phase 0..1."""
    L = Layer(520, 960, ss=2)
    for s in (0.5, 0):                         # far leg first
        p = 2 * math.pi * (phase_q + s)
        sw = math.sin(p)
        lift = max(0.0, math.cos(p))
        hip = (260 + 20 * sw, 20)
        knee = (260 + 110 * sw + 30 * lift, 470 - 20 * lift)
        foot = (260 + 190 * sw, 880 - 70 * lift)
        c = col if s == 0 else shade(col, 0.82)
        L.stroke([hip, knee], 120, c, smooth=False)
        L.stroke([knee, foot], 104, c, smooth=False)
        L.stroke([(foot[0] - 30, foot[1] - 40), (foot[0] + 20, foot[1] - 36)], 96, shade(c, 0.9), smooth=False)
        sc = shoe if s == 0 else shade(shoe, 0.8)
        L.shape([(foot[0] - 70, foot[1] - 30), (foot[0] + 40, foot[1] - 40), (foot[0] + 110, foot[1] + 4),
                 (foot[0] + 104, foot[1] + 44), (foot[0] - 74, foot[1] + 46)], sc)
        L.poly([(foot[0] - 76, foot[1] + 32), (foot[0] + 108, foot[1] + 32), (foot[0] + 104, foot[1] + 48),
                (foot[0] - 74, foot[1] + 50)], (250, 250, 250) if sum(sc) < 300 else (60, 60, 64))
    L.poly([(150, 0), (370, 0), (380, 80), (140, 80)], shade(col, 0.9))     # the hem of a coat/belt
    return L.image()


@functools.lru_cache(None)
def tumbleweed(size=260):
    L = Layer(size, size, ss=2)
    rnd = random.Random(2)
    c = size / 2
    for _ in range(46):
        a0, r0 = rnd.uniform(0, 6.28), rnd.uniform(0, size * 0.45)
        a1, r1 = rnd.uniform(0, 6.28), rnd.uniform(0, size * 0.45)
        L.stroke([(c + r0 * math.cos(a0), c + r0 * math.sin(a0)), (c, c), (c + r1 * math.cos(a1), c + r1 * math.sin(a1))],
                 4, mixc((176, 140, 90), (120, 90, 60), rnd.random()))
    return L.image()


@functools.lru_cache(None)
def like_button(size=520):
    L = Layer(size, size, ss=2)
    c = size / 2
    L.ell(c, c + 14, c * 0.92, c * 0.92, (170, 30, 60), alpha=0.5, blur=8)
    L.ell(c, c, c * 0.92, c * 0.92, (255, 70, 100))
    L.ell(c - 60, c - 90, c * 0.5, c * 0.3, (255, 255, 255), alpha=0.2)
    im = L.image()
    e = tg._emoji('👍', int(size * 0.5))
    im.alpha_composite(e, ((size - e.width) // 2, (size - e.height) // 2))
    return im
