"""Backgrounds and props, drawn in code (flat storybook style, soft gradients, no outlines). Cached images.

shop_wall()   — the watchmaker's back wall: wallpaper, shelves with gifts and time price tags, wainscot.
counter_top(), counter_front() — textures for the 3D counter planes.
safe_body(), safe_door() — round safe in the wall; the door swings open as a 3D quad.
lamp()        — pendant lamp; glow is added by the renderer.
clock(t, r, kind) — wall clock with live hands.
room_night()  — Лёва's room at night (window, city, moon).
kitchen(desat) — grandma's kitchen at dusk: table, pie under a towel, empty chair, wall calendar.
"""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx
import gifts_api as G
from art import Layer, ellipse_pts, mixc, shade


def _grad(w, h, top, bottom, noise=0.0, seed=1):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.asarray(top, np.float32)[None, None] * (1 - t) + np.asarray(bottom, np.float32)[None, None] * t
    a = np.repeat(a, w, 1)
    if noise:
        rng = np.random.default_rng(seed)
        a += rng.normal(0, noise, (h, w, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')


def _vignette(im, strength=0.45):
    w, h = im.size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w * 0.62)) ** 2 + ((y - h / 2) / (h * 0.58)) ** 2)
    k = 1 - strength * np.clip(d - 0.55, 0, 1) ** 1.4
    a = np.asarray(im, np.float32)
    a[..., :3] *= k[..., None]
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


@functools.lru_cache(None)
def gift_png(name, size, model=None):
    p = G.model_png(name, model, 512) if model else G.original_png(name, 512)
    return Image.open(p).convert('RGBA').resize((size, size), Image.LANCZOS)


def _tag(text, w=120, h=58, col=(244, 232, 204)):
    L = Layer(w + 20, h + 40)
    L.poly([(10, 30), (w - 6, 30), (w + 10, 30 + h / 2), (w - 6, 30 + h), (10, 30 + h)], col)
    L.ell(w - 6, 30 + h / 2, 5, 5, (120, 80, 60))
    L.stroke([(w - 6, 30 + h / 2), (w + 8, 4)], 2.2, (200, 170, 120))
    im = L.image()
    d = ImageDraw.Draw(im)
    d.text((w / 2 + 2, 30 + h / 2), text, font=fx.font('Bold', 24), fill=(96, 56, 40), anchor='mm')
    return im


SHELF_GIFTS = [
    [('Crystal Ball', 'неделя'), ('Genie Lamp', '3 года'), ('Love Potion', 'свидание'), ('Top Hat', 'выпускной'),
     ('Toy Bear', 'детство')],
    [('Eternal Rose', 'юность'), ('Perfume Bottle', '2 часа'), ('Mini Oscar', 'мечта'), ('Hex Pot', 'ночь'),
     ('Vintage Cigar', 'отпуск')],
    [('Timeless Book', 'зима'), ('Heart Locket', 'первый поцелуй'), ('Magic Potion', 'утро'),
     ('Signet Ring', 'свадьба'), ('Lunar Snake', 'год')],
]

WALL_W, WALL_H = 1500, 2100          # px; 400 px per metre -> 3.75 × 5.25 m


@functools.lru_cache(None)
def shop_wall():
    w, h = WALL_W, WALL_H
    im = _grad(w, h, (88, 52, 40), (58, 34, 28), noise=2.0)
    d = ImageDraw.Draw(im)
    for x in range(0, w, 60):                                       # wallpaper stripes
        d.rectangle([x, 0, x + 26, h], fill=(96, 58, 44, 255))
    for x in range(30, w, 120):                                     # tiny gold dots between stripes
        for y in range(40, h, 110):
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(150, 104, 62, 255))
    # wainscot
    d.rectangle([0, 1520, w, h], fill=(78, 44, 30, 255))
    d.rectangle([0, 1508, w, 1532], fill=(112, 68, 42, 255))
    for x in range(40, w, 300):
        d.rounded_rectangle([x, 1580, x + 240, 2040], 14, outline=(62, 34, 24, 255), width=8)
    # shelves with gifts and time-price tags
    for r, row in enumerate(SHELF_GIFTS):
        y = 470 + r * 360
        d.rectangle([60, y, w - 60, y + 26], fill=(122, 76, 46, 255))
        d.rectangle([60, y + 26, w - 60, y + 40], fill=(70, 40, 28, 255))
        for k, (name, tag) in enumerate(row):
            x = 70 + k * 272 + (r % 2) * 40
            sh = Image.new('RGBA', (220, 40), (0, 0, 0, 0))
            ImageDraw.Draw(sh).ellipse([20, 8, 200, 32], fill=(30, 16, 10, 120))
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (x - 5, y - 24))
            g = gift_png(name, 210)
            im.alpha_composite(g, (x - 5, y - 200))
            tg = _tag(tag, w=max(110, 16 * len(tag) + 30))
            im.alpha_composite(tg, (x + 40, y + 30))
    return _vignette(im, 0.35)


@functools.lru_cache(None)
def counter_top():
    w, h = 1600, 520
    im = _grad(w, h, (150, 94, 58), (122, 74, 44))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(4)
    for y in range(0, h, 104):
        d.line([(0, y), (w, y)], fill=(98, 58, 34, 255), width=3)
    for _ in range(140):                                            # grain
        y = rng.uniform(0, h)
        x = rng.uniform(-200, w)
        d.line([(x, y), (x + rng.uniform(120, 420), y + rng.uniform(-3, 3))], fill=(136, 84, 50, 255), width=2)
    d.rectangle([0, h - 26, w, h], fill=(206, 160, 90, 255))            # brass edge strip
    return im


@functools.lru_cache(None)
def counter_front():
    w, h = 1600, 700
    im = _grad(w, h, (98, 58, 36), (64, 36, 24))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 22], fill=(196, 150, 84, 255))
    for x in range(60, w, 380):
        d.rounded_rectangle([x, 80, x + 320, 640], 18, outline=(52, 28, 18, 255), width=10)
        d.rounded_rectangle([x + 22, 102, x + 298, 618], 12, outline=(116, 72, 44, 255), width=4)
    return im


@functools.lru_cache(None)
def safe_body():
    L = Layer(560, 560)
    L.ell(280, 280, 270, 270, (46, 44, 50))
    L.ell(280, 280, 236, 236, (20, 16, 18))
    L.ell(280, 300, 200, 200, (255, 214, 120), alpha=0.0)
    return L.image()


@functools.lru_cache(None)
def safe_door():
    L = Layer(500, 500)
    L.ell(250, 250, 240, 240, (126, 128, 138))
    L.ell(250, 250, 222, 222, (98, 100, 112))
    L.ell(250, 250, 200, 200, (112, 114, 126))
    for k in range(12):                                             # rivets
        a = k * math.pi / 6
        L.ell(250 + 212 * math.cos(a), 250 + 212 * math.sin(a), 8, 8, (160, 162, 172))
    L.ell(250, 250, 70, 70, (210, 172, 96))                         # brass dial
    L.ell(250, 250, 52, 52, (168, 128, 66))
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        L.stroke([(250, 250), (250 + 110 * math.cos(a), 250 + 110 * math.sin(a))], 14, (196, 160, 90))
    L.ell(250, 250, 18, 18, (240, 210, 140))
    return L.image()


@functools.lru_cache(None)
def lamp():
    L = Layer(420, 900)
    L.stroke([(210, 0), (210, 640)], 6, (40, 30, 28), smooth=False)
    L.poly([(110, 760), (150, 650), (270, 650), (310, 760)], (54, 92, 74))
    L.poly([(150, 650), (180, 630), (240, 630), (270, 650)], (40, 70, 58))
    L.ell(210, 762, 100, 18, (255, 226, 150))
    return L.image()


def clock(t, r=90, face=(246, 236, 214), rim=(196, 150, 84), speed=1.0, phase=0.0):
    """Wall clock with hands depending on t (minute hand fast — time is running)."""
    L = Layer(2 * r + 20, 2 * r + 20, ss=2)
    c = r + 10
    L.ell(c, c, r, r, rim)
    L.ell(c, c, r * 0.86, r * 0.86, face)
    for k in range(12):
        a = k * math.pi / 6
        L.stroke([(c + r * 0.72 * math.sin(a), c - r * 0.72 * math.cos(a)),
                  (c + r * 0.8 * math.sin(a), c - r * 0.8 * math.cos(a))], max(2, r * 0.05), (90, 70, 60),
                 smooth=False)
    m = (t * speed * 0.5 + phase) % 1.0
    hh = (t * speed * 0.5 / 12 + phase * 0.7) % 1.0
    for frac, ln, wd in ((hh, 0.45, 0.07), (m, 0.68, 0.045)):
        a = frac * 2 * math.pi
        L.stroke([(c, c), (c + r * ln * math.sin(a), c - r * ln * math.cos(a))], max(2, r * wd), (60, 44, 40),
                 smooth=False)
    L.ell(c, c, r * 0.07, r * 0.07, (180, 60, 50))
    return L.image()


# ------------------------------------------------------------------ Лёва's room
ROOM_W, ROOM_H = 1400, 2300


@functools.lru_cache(None)
def room_night():
    w, h = ROOM_W, ROOM_H
    im = _grad(w, h, (30, 36, 74), (18, 20, 44), noise=1.5)
    L = Layer(w, h, ss=1)
    L.im = im
    # window with night city
    wx0, wy0, wx1, wy1 = 760, 380, 1260, 1100
    sky = _grad(wx1 - wx0, wy1 - wy0, (38, 56, 120), (82, 70, 140))
    im.alpha_composite(sky, (wx0, wy0))
    L = Layer(w, h, ss=2)
    L.im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0))
    L.ell(1120, 520, 52, 52, (250, 240, 210))                      # moon
    L.ell(1120, 520, 120, 120, (250, 240, 210), alpha=0.12, blur=30)
    rng = np.random.default_rng(7)
    x = wx0
    while x < wx1:                                                  # skyline
        bw = rng.uniform(40, 90)
        bh = rng.uniform(120, 360)
        L.poly([(x, wy1), (x, wy1 - bh), (x + bw, wy1 - bh), (x + bw, wy1)], (24, 28, 58))
        for yy in np.arange(wy1 - bh + 20, wy1 - 10, 26):
            for xx in np.arange(x + 8, x + bw - 10, 18):
                if rng.random() < 0.35:
                    L.poly([(xx, yy), (xx + 8, yy), (xx + 8, yy + 10), (xx, yy + 10)], (255, 214, 130))
        x += bw + 4
    for k in range(30):
        L.ell(rng.uniform(wx0, wx1), rng.uniform(wy0, wy0 + 300), 2, 2, (255, 255, 255), alpha=0.7)
    over = L.image()
    im.alpha_composite(over)
    d = ImageDraw.Draw(im)
    d.rectangle([wx0 - 24, wy0 - 24, wx1 + 24, wy0], fill=(56, 60, 104, 255))
    d.rectangle([wx0 - 24, wy1, wx1 + 24, wy1 + 34], fill=(56, 60, 104, 255))
    d.rectangle([wx0 - 24, wy0, wx0, wy1], fill=(56, 60, 104, 255))
    d.rectangle([wx1, wy0, wx1 + 24, wy1], fill=(56, 60, 104, 255))
    d.rectangle([(wx0 + wx1) // 2 - 9, wy0, (wx0 + wx1) // 2 + 9, wy1], fill=(56, 60, 104, 255))
    # moonlight patch on the wall
    glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon([(wx0, wy1 + 40), (wx1, wy1 + 40), (wx1 - 200, h), (wx0 - 500, h)],
                                 fill=(120, 140, 220, 40))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    # poster + shelf
    d.rounded_rectangle([170, 420, 520, 900], 10, fill=(54, 46, 90, 255))
    d.rounded_rectangle([196, 446, 494, 874], 6, fill=(90, 66, 120, 255))
    d.ellipse([250, 520, 440, 710], fill=(236, 120, 110, 255))
    d.rectangle([120, 1180, 640, 1204], fill=(70, 58, 100, 255))
    for k, c in enumerate([(200, 90, 90), (90, 160, 150), (230, 190, 110), (120, 110, 200)]):
        d.rectangle([150 + k * 46, 1060, 186 + k * 46, 1180], fill=c + (255,))
    return _vignette(im, 0.5)


@functools.lru_cache(None)
def bed_front():
    L = Layer(1400, 700)
    L.shape([(-100, 260), (300, 180), (700, 220), (1100, 170), (1500, 240), (1500, 700), (-100, 700)],
            (72, 82, 150))
    L.shape([(-100, 380), (400, 320), (900, 360), (1500, 330), (1500, 700), (-100, 700)], (58, 66, 128))
    for k in range(6):
        L.stroke([(k * 260 - 40, 420), (k * 260 + 80, 520)], 10, (84, 96, 170), alpha=0.7)
    return L.image()


# ------------------------------------------------------------------ grandma's kitchen
KIT_W, KIT_H = 1400, 2300


@functools.lru_cache(None)
def kitchen():
    w, h = KIT_W, KIT_H
    im = _grad(w, h, (176, 186, 206), (140, 146, 170), noise=1.2)
    d = ImageDraw.Draw(im)
    # tiles band
    for y in range(1100, 1500, 70):
        for x in range(0, w, 70):
            d.rectangle([x + 3, y + 3, x + 67, y + 67], fill=(196, 204, 220, 255))
    # window at dusk
    wx0, wy0, wx1, wy1 = 140, 300, 760, 1020
    im.alpha_composite(_grad(wx1 - wx0, wy1 - wy0, (90, 110, 170), (246, 176, 130)), (wx0, wy0))
    d.rectangle([wx0 - 26, wy0 - 26, wx1 + 26, wy0], fill=(238, 236, 228, 255))
    d.rectangle([wx0 - 26, wy1, wx1 + 40, wy1 + 40], fill=(238, 236, 228, 255))
    d.rectangle([wx0 - 26, wy0, wx0, wy1], fill=(238, 236, 228, 255))
    d.rectangle([wx1, wy0, wx1 + 26, wy1], fill=(238, 236, 228, 255))
    d.rectangle([(wx0 + wx1) // 2 - 10, wy0, (wx0 + wx1) // 2 + 10, wy1], fill=(238, 236, 228, 255))
    # curtains
    L = Layer(w, h, ss=2)
    L.im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0))
    for s, x in ((1, wx0 - 40), (-1, wx1 + 40)):
        L.shape([(x, wy0 - 60), (x + s * 160, wy0 - 60), (x + s * 110, wy0 + 300), (x + s * 140, wy1 + 60),
                 (x, wy1 + 80)], (226, 120, 112))
        L.stroke([(x + s * 50, wy0 - 40), (x + s * 60, wy1 + 40)], 8, (204, 100, 96), alpha=0.7)
    # plant on the sill
    L.poly([(560, wy1 - 70), (640, wy1 - 70), (628, wy1), (572, wy1)], (196, 110, 80))
    for a in (-0.7, -0.2, 0.3, 0.8):
        L.ell(600 + 50 * math.sin(a), wy1 - 120 - 30 * math.cos(a), 24, 50, (90, 150, 100), rot=a)
    # wall calendar nail
    L.ell(1050, 420, 8, 8, (90, 80, 90))
    # framed photo: two simple silhouettes (grandma and little Лёва), warm frame
    L.poly([(900, 900), (1220, 900), (1220, 1110), (900, 1110)], (190, 150, 100))
    L.poly([(918, 918), (1202, 918), (1202, 1092), (918, 1092)], (248, 232, 206))
    L.ell(1010, 990, 34, 38, (200, 180, 190))
    L.ell(1010, 950, 30, 22, (236, 236, 236))
    L.shape([(950, 1092), (970, 1040), (1050, 1040), (1070, 1092)], (170, 130, 160))
    L.ell(1120, 1012, 24, 26, (230, 196, 170))
    L.shape([(1086, 1092), (1100, 1052), (1140, 1052), (1154, 1092)], (80, 150, 150))
    L.ell(1120, 994, 26, 16, (90, 64, 56))
    im.alpha_composite(L.image())
    # table + cloth
    L = Layer(w, h, ss=2)
    L.im = Image.new('RGBA', (w * 2, h * 2), (0, 0, 0, 0))
    L.poly([(-50, 1560), (w + 50, 1560), (w + 50, h), (-50, h)], (226, 220, 236))
    for x in range(-50, w + 50, 90):
        L.poly([(x, 1560), (x + 45, 1560), (x + 45, h), (x, h)], (214, 120, 120), alpha=0.35)
    for y in range(1600, h, 90):
        L.poly([(-50, y), (w + 50, y), (w + 50, y + 45), (-50, y + 45)], (214, 120, 120), alpha=0.25)
    # empty chair back on the right
    L.poly([(1040, 1240), (1260, 1240), (1250, 1560), (1050, 1560)], (150, 104, 76))
    L.poly([(1070, 1270), (1230, 1270), (1222, 1380), (1078, 1380)], (176, 126, 92))
    im.alpha_composite(L.image())
    return _vignette(im, 0.35)


@functools.lru_cache(None)
def pie_plate():
    """Pie under a checked towel on a plate, a teacup next to it (sprite 900×420)."""
    L = Layer(900, 420)
    L.ell(380, 330, 300, 60, (250, 250, 252))
    L.ell(380, 322, 260, 48, (230, 232, 240))
    L.ell(380, 300, 230, 60, (206, 140, 76))                     # pie: side
    pm = L.ell(380, 270, 230, 62, (232, 170, 96))                  # top crust
    for k in range(-3, 4):                                          # lattice
        L.stroke([(380 + k * 56 - 30, 222), (380 + k * 56 + 30, 318)], 9, (246, 196, 120), clip=pm)
        L.stroke([(380 + k * 56 + 30, 222), (380 + k * 56 - 30, 318)], 9, (246, 196, 120), clip=pm)
    L.ell(380, 270, 230, 62, (180, 110, 60), alpha=0.0)
    L.shape([(150, 300), (190, 210), (300, 196), (340, 260), (260, 330)], (244, 240, 234))     # towel corner
    for k in range(3):
        L.stroke([(200 + k * 40, 316), (236 + k * 36, 214)], 10, (214, 110, 110), alpha=0.7)
    # teacup
    L.ell(780, 360, 80, 18, (240, 240, 246))
    cm = L.shape([(712, 270), (848, 270), (836, 340), (724, 340)], (246, 246, 250))
    L.ell(780, 272, 68, 14, (170, 110, 80))
    L.stroke([(846, 290), (880, 300), (870, 330), (838, 326)], 10, (246, 246, 250))
    return L.image()


def wall_calendar(day, weekday='суббота', month='ноябрь'):
    """Paper wall calendar sheet showing `day` and its weekday."""
    L = Layer(300, 380)
    L.poly([(20, 30), (280, 30), (280, 360), (20, 360)], (246, 244, 238))
    L.poly([(20, 30), (280, 30), (280, 110), (20, 110)], (214, 92, 92))
    im = L.image()
    d = ImageDraw.Draw(im)
    d.text((150, 72), month, font=fx.font('Bold', 34), fill=(255, 255, 255), anchor='mm')
    d.text((150, 222), str(day), font=fx.font('Heavy', 140), fill=(60, 56, 70), anchor='mm')
    d.text((150, 322), weekday, font=fx.font('Bold', 34), fill=(200, 80, 80) if weekday == 'суббота' else
           (90, 86, 100), anchor='mm')
    return im
