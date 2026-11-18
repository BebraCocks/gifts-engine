"""«Новогодние подарки спустя почти два года + слух о перчатках» — 1080×1920, 60 fps. Кадр — чистая функция времени.
Комната с большим окном (ChatGPT): за стеклом ночной городок (окна гаснут/загораются, снег, салют, сияние),
на ёлке за окном загораются шары — по одному на подарок. Цены — градусник (вырос — красный, упал — синий иней).
Жуть — иней ползёт по экрану, Мита становится ледяной статуей, на стекле — морозный отпечаток (без наезда).
Реклама — Мита наряжает ёлку над баннером, под баннером пролетает Санта. Финал — варежки «Верю / Не верю».
Петля — снежный шар: в конце снег заметает кадр, в начале оседает."""
import functools
import math
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import banner
import frames
import fx
import gifts_api
import lottie
import events as E
import mita53 as M
from timeline import DUR, ON, END, AD_STOP
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
KEYED = HERE / 'build' / 'keyed'
DECOR = HERE / 'input' / 'decor'
UFONT = HERE.parent / '51-mita-craft' / 'input' / 'fonts'
INK = (30, 34, 62)
WHITE = (255, 255, 255)
ICE = (150, 210, 255)
FROST = (220, 240, 255)
WARM = (255, 196, 110)
RED = (232, 70, 64)
GOLD = (246, 196, 72)
CARAMEL = (196, 128, 70)
SUB_Y = 1628
WIN_S, WIN_X = 1.25, -100            # окно 1024×1536 → высота 1920, обрезано по 100 px с боков
TOWN_S, TOWN_Y = 1080 / 1024, 100


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.35):
    return ease((t - t0) / d)


def window_a(t, t0, t1, d=0.3):
    return appear(t, t0, d) * (1 - appear(t, t1 - d, d))


def pop(t, t0, d=0.45):
    return fx.ease_out_back(fx.clamp01((t - t0) / d)) if t < t0 + d else 1.0


def put(canvas, im, cx, cy, s=1.0, a=1.0, rot=0.0, anchor=None):
    if im is None or a <= 0.003 or s <= 0.003:
        return
    fx.over(canvas, fx.warp(im, cx, cy, s, s, rot, anchor), a)


@functools.lru_cache(None)
def ufont(weight, size):
    return ImageFont.truetype(str(UFONT / f'Unbounded-{weight}.ttf'), size)


@functools.lru_cache(None)
def utext(s_, size, weight='ExtraBold', color=WHITE, stroke=0, scol=INK):
    f = ufont(weight, size)
    l, t_, r, b_ = f.getbbox(s_, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 24, b_ - t_ + 24), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((12 - l, 12 - t_), s_, font=f, fill=color + (255,), stroke_width=stroke,
                            stroke_fill=scol + (255,))
    return im


@functools.lru_cache(None)
def multi(parts, size, weight='Heavy'):
    return fx.text_img(parts, size, weight, False)


@functools.lru_cache(None)
def pill(s_, fill, size=30, tcol=WHITE, outline=None):
    """Плашка-«льдинка»: скруглённая, с белой каймой и снежной шапкой сверху."""
    f = ufont('ExtraBold', size)
    tw = int(f.getlength(s_))
    w_, h_ = tw + 2 * size + 10, int(size * 2.1)
    S = 2
    im = Image.new('RGBA', ((w_ + 20) * S, (h_ + 26) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((10 * S, 16 * S, (10 + w_) * S, (16 + h_) * S), h_ * S // 2, fill=fill + (255,),
                        outline=(outline or (255, 255, 255)) + (235,), width=3 * S)
    rng = np.random.default_rng(len(s_) + size)
    for k in range(int(w_ / 26)):                       # снежная шапка
        x = (22 + k * 26 + rng.uniform(-4, 4)) * S
        r = rng.uniform(9, 15) * S
        d.ellipse((x - r, 16 * S - r * 0.55, x + r, 16 * S + r * 0.75), fill=(250, 252, 255, 255))
    d.text(((10 + w_ / 2) * S, (16 + h_ / 2 + 2) * S), s_, font=ufont('ExtraBold', size * S), fill=tcol + (255,),
           anchor='mm')
    return im.resize((w_ + 20, h_ + 26), Image.LANCZOS)


@functools.lru_cache(None)
def keyed(name, w=None, h=None, crop=True):
    im = Image.open(KEYED / f'{name}.png').convert('RGBA')
    if crop:
        im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
    if w:
        im = im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)
    elif h:
        im = im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)
    return im


GIFT = {'hat': 'Santa Hat', 'cookie': 'Ginger Cookie', 'bell': 'Sleigh Bell', 'stock': 'Xmas Stocking',
        'mitt': 'Snow Mittens', 'globe': 'Snow Globe', 'jingle': 'Jingle Bells', 'cane': 'Candy Cane',
        'wreath': 'Winter Wreath', 'drink': 'Holiday Drink'}


@functools.lru_cache(None)
def gift_path(key):
    return str(gifts_api.original_file(GIFT[key], 'tgs'))


TON_RUB = 86          # ≈ $1,04 за TON × ≈83 ₽ за $ (18.11.2026)


def rub(ton):
    v = int(round(ton * TON_RUB / 10.0) * 10)
    return '~' + f'{v:,}'.replace(',', ' ') + ' ₽'


def gift_frame(key, t, size, off=0.0):
    return lottie.frame(gift_path(key), t, size=size, offset=off)


@functools.lru_cache(maxsize=32)
def radial(size, rgb, power=2.0):
    return fx.radial(size, rgb, power, 1.0)


@functools.lru_cache(maxsize=16)
def badge_img(d, ring=(196, 212, 242)):
    """Подложка под подарок — ёлочный шар: матовое белое стекло с голубым отливом, серебряный колпачок с петелькой,
    снежная шапка сверху, морозные снежинки по краю, глянцевый блик и искорки."""
    S = 2
    pad = 40
    n = (d + 2 * pad) * S
    R = d * S / 2
    cx, cy = n / 2, n / 2 + 6 * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    sh = Image.new('L', (n, n), 0)
    ImageDraw.Draw(sh).ellipse((cx - R, cy - R + 10 * S, cx + R, cy + R + 10 * S), fill=120)
    im.paste((24, 36, 80, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(14 * S)))
    # стекло: радиальный градиент белый → бледно-голубой
    yy, xx = np.mgrid[:n, :n].astype(np.float32)
    r = np.sqrt((xx - cx + R * 0.25) ** 2 + (yy - cy + R * 0.3) ** 2) / (R * 1.35)
    body = np.dstack([255 - 28 * r, 255 - 18 * r, np.full_like(r, 255)]).clip(0, 255)
    mask = Image.new('L', (n, n), 0)
    ImageDraw.Draw(mask).ellipse((cx - R, cy - R, cx + R, cy + R), fill=255)
    im.paste(Image.fromarray(body.astype(np.uint8)), (0, 0), mask)
    d_ = ImageDraw.Draw(im)
    # морозные снежинки по краю стекла
    for k in range(7):
        ang = k * 2 * math.pi / 7 + 0.3
        snowflake(d_, cx + R * 0.76 * math.cos(ang), cy + R * 0.76 * math.sin(ang), R * 0.13,
                  (205, 222, 248, 255), max(1, int(1.6 * S)))
    # каёмки: цветная + серебряная тонкая
    d_.ellipse((cx - R, cy - R, cx + R, cy + R), outline=ring + (255,), width=int(7 * S))
    d_.ellipse((cx - R + 9 * S, cy - R + 9 * S, cx + R - 9 * S, cy + R - 9 * S), outline=(214, 222, 238, 255),
               width=int(2 * S))
    # глянцевый блик
    hl = Image.new('L', (n, n), 0)
    ImageDraw.Draw(hl).arc((cx - R * 0.8, cy - R * 0.8, cx + R * 0.8, cy + R * 0.8), 200, 250, fill=200,
                           width=int(R * 0.09))
    im.paste((255, 255, 255, 255), (0, 0), hl.filter(ImageFilter.GaussianBlur(2 * S)))
    # снежная шапка на макушке
    rng = np.random.default_rng(int(d))
    for k in range(9):
        ang = math.pi * (1.18 + 0.64 * k / 8)
        x, y = cx + R * 0.97 * math.cos(ang), cy + R * 0.97 * math.sin(ang)
        rr = R * rng.uniform(0.13, 0.19)
        d_.ellipse((x - rr, y - rr * 0.8, x + rr, y + rr * 0.8), fill=(255, 255, 255, 255), outline=(222, 232, 250, 255),
                   width=S)
    # серебряный колпачок с рёбрами и петелькой
    cw, ch = R * 0.42, R * 0.2
    top = cy - R - ch * 0.55
    d_.ellipse((cx - cw * 0.28, top - ch * 1.25, cx + cw * 0.28, top - ch * 0.15), outline=(170, 178, 196, 255),
               width=int(3.5 * S))
    d_.rounded_rectangle((cx - cw / 2, top - ch * 0.4, cx + cw / 2, top + ch * 0.75), int(4 * S), fill=(212, 218, 232, 255),
                         outline=(150, 158, 178, 255), width=int(2 * S))
    for q in range(1, 5):
        x = cx - cw / 2 + cw * q / 5
        d_.line((x, top - ch * 0.35, x, top + ch * 0.7), fill=(170, 178, 196, 255), width=int(1.5 * S))
    # искорки
    for (fx_, fy_, fr) in ((0.98, -0.62, 0.11), (-1.02, 0.42, 0.08), (0.82, 0.86, 0.07)):
        fx.sparkle(d_, cx + R * fx_, cy + R * fy_, R * fr, (255, 236, 170, 255))
    return im.resize((n // S, n // S), Image.LANCZOS)


KIND = {'hat': 0, 'cookie': 1, 'stock': 2, 'bell': 3, 'mitt': 0, 'globe': 2, 'jingle': 3, 'cane': 1, 'wreath': 3, 'drink': 0}
BAUBLES = None


@functools.lru_cache(maxsize=64)
def bauble(kind, d):
    """Рамка-подложка (ChatGPT, 4 вида): масштаб такой, чтобы пустая середина была диаметром d."""
    import json
    meta = json.loads((KEYED / 'baubles.json').read_text())[kind]
    im = Image.open(KEYED / f'bauble_{kind}.png').convert('RGBA')
    s = d / meta['d']
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    return im, (meta['cx'] * s, meta['cy'] * s)


def gift_badge(cv, im, x, y, s=1.0, a=1.0, rot=0.0, kind='hat'):
    d = int(max(im.size) * 1.08)
    fr, anc = bauble(KIND.get(kind, 0), d)
    hw = max(anc[0], fr.width - anc[0]) * s + 10           # рамка целиком в кадре: не обрезается краем экрана
    x = min(max(x, hw), W - hw)
    put(cv, radial(128, (20, 30, 70)), x, y + 18 * s, d / 128 * 1.25 * s, 0.25 * a)     # мягкая тень
    put(cv, fr, x, y, s, a, rot * 0.5, anchor=anc)
    put(cv, im, x, y, s * 0.86, a, rot)


# ------------------------------------------------------------------ городок за окном
SKY0, SKY1 = (20, 28, 70), (52, 66, 128)
WALL, FLOOR = (46, 58, 112), (64, 80, 140)
# ------------------------------------------------------------------ фон: стена и окно с городком (картинки автора)
WIN_S = 0.56                                  # окно 1254×1254 → ≈702 px
WIN_X0, WIN_Y0 = 540 - 1254 * WIN_S / 2, 46
GLASS = (110, 262, 1145, 1030)                # стекло в координатах window_min.png
ORN_SRC = [(978, 693), (1035, 768), (955, 862), (1073, 910), (1003, 966)]
STAR_SRC = (1000, 495)
GROUND_Y = 1475
SILL_Y = int(WIN_Y0 + 1100 * WIN_S)


def wpt(x, y):
    return WIN_X0 + x * WIN_S, WIN_Y0 + y * WIN_S


GLASS_F = (*wpt(GLASS[0], GLASS[1]), *wpt(GLASS[2], GLASS[3]))


@functools.lru_cache(None)
def wall():
    im = Image.open(DECOR / 'wall.png').convert('RGB')
    im = im.resize((round(im.width * H / im.height), H), Image.LANCZOS)
    x0 = (im.width - W) // 2
    a = np.array(im.crop((x0, 0, x0 + W, H))).astype(np.float32)
    return a * 0.9 + 255 * 0.1                 # снежинки на стене чуть бледнее


@functools.lru_cache(None)
def window_layers():
    src = Image.open(KEYED / 'window_min.png').convert('RGBA')
    raw = np.array(Image.open(DECOR / 'window_min.png').convert('RGB')).astype(np.float32)
    w_ = round(src.width * WIN_S)
    h_ = round(src.height * WIN_S)
    im = np.array(src.resize((w_, h_), Image.LANCZOS)).astype(np.float32)
    rr = cv2.resize(raw, (w_, h_), interpolation=cv2.INTER_AREA)
    r, g, b = rr[..., 0], rr[..., 1], rr[..., 2]
    lit = np.clip((r - 185) / 40, 0, 1) * np.clip((g - 150) / 40, 0, 1) * np.clip((150 - b) / 50 + 0.3, 0, 1)
    gy0, gy1 = int(GLASS[1] * WIN_S), int(GLASS[3] * WIN_S)
    lit[:int(600 * WIN_S)] = 0                                 # только окна домов (не луна, не гирлянда)
    lit = cv2.GaussianBlur(lit, (0, 0), 0.8)
    rgb = im[..., :3]
    dark = rgb * (1 - 0.9 * lit[..., None]) + np.array([38, 44, 92], np.float32) * 0.9 * lit[..., None]
    m = (lit > 0.3).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((5, 5), np.uint8)))
    order = np.zeros(n, np.float32)
    if n > 1:
        order[1:] = cen[1:, 0] / w_
        order = (order - order[1:].min()) / max(1e-6, order[1:].max() - order[1:].min())
    order[0] = 0
    # стекло: скруглённый прямоугольник
    gm = Image.new('L', (w_, h_), 0)
    ImageDraw.Draw(gm).rounded_rectangle((GLASS[0] * WIN_S, GLASS[1] * WIN_S, GLASS[2] * WIN_S, GLASS[3] * WIN_S),
                                         int(70 * WIN_S), fill=255)
    gmask = np.array(gm, np.float32) / 255
    X0, Y0 = int(round(WIN_X0)), WIN_Y0
    def place(arr, fill=0.0):
        out = np.full((H, W) + arr.shape[2:], fill, np.float32)
        xs0, xs1 = max(0, X0), min(W, X0 + w_)
        out[Y0:Y0 + h_, xs0:xs1] = arr[:, xs0 - X0:xs1 - X0]
        return out
    alpha = place(im[..., 3] / 255)
    return dict(on=place(rgb), off=place(dark), alpha=alpha, labs=place(lab.astype(np.float32)).astype(np.int32),
                order=order, glass=place(gmask))


ORNAMENTS = [wpt(*p) for p in ORN_SRC]
STAR = wpt(*STAR_SRC)


def orn_xy(j):
    return ORNAMENTS[j]


def lights_state(t):
    """Окна домов за стеклом: функция (порядок окна) → 0..1."""
    ck = creepy_k(t)
    if E.SPREAD - 0.2 <= t < E.PRICE + 1.5:
        u0 = ease((t - (E.SPREAD - 0.2)) / 0.35)          # быстро гаснут
        def f(order):
            x = np.clip((t - (E.SPREAD + 0.6 + order * 3.2)) / 0.25, 0, 1)   # загораются цепочкой слева направо
            on = x * x * (3 - 2 * x)
            return (1 - u0) + u0 * on
        return f
    return lambda order: np.full_like(order, 1 - 0.92 * ck)


def snowfall(cv, t, n=90, seed=7, y0=0, y1=1180, speed=(70, 150), alpha=0.85, scale=1.0, freeze=0.0, x0=0, x1=W):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(x0, x1, n)
    ph = rng.uniform(0, 1, n)
    sp = rng.uniform(*speed, n)
    rs = rng.uniform(1.6, 4.6, n) * scale
    sw = rng.uniform(0.5, 1.6, n)
    tt = t * (1 - 0.85 * freeze)

    def draw(d, mp, S):
        span = y1 - y0 + 40
        for i in range(n):
            y = y0 - 20 + (ph[i] * span + tt * sp[i]) % span
            x = x0 + (xs[i] - x0 + 18 * math.sin(tt * sw[i] + ph[i] * 6)) % (x1 - x0)
            X, Y = mp(x, y)
            r = rs[i] * S
            d.ellipse((X - r, Y - r, X + r, Y + r), fill=(255, 255, 255, int(200 * alpha)))
    fx.over(cv, fx.draw_rgba((x0, y0, x1, y1), draw))


def fireworks(cv, t):
    """Салют за окном в момент превращения."""
    gx0, gy0, gx1, gy1 = GLASS_F
    pts = ((E.FLASH - 0.05, gx0 + 0.3 * (gx1 - gx0), gy0 + 120, (255, 214, 140)),
           (E.FLASH + 0.3, gx0 + 0.72 * (gx1 - gx0), gy0 + 90, ICE),
           (E.FLASH + 0.65, gx0 + 0.52 * (gx1 - gx0), gy0 + 170, (255, 240, 250)))
    for j, (t0, x, y, col) in enumerate(pts):
        u = (t - t0) / 1.4
        if not 0 <= u < 1:
            continue
        rng = np.random.default_rng(j + 3)
        ang = rng.uniform(0, 2 * math.pi, 22)
        sp = rng.uniform(55, 110, 22)
        r_ = fx.ease_out(u)

        def draw(d, mp, S, ang=ang, sp=sp, r_=r_, u=u, x=x, y=y, col=col):
            for a_, s_ in zip(ang, sp):
                px, py = x + math.cos(a_) * s_ * r_, y + math.sin(a_) * s_ * r_ + 30 * u * u
                X, Y = mp(px, py)
                rr = (4 - 2.6 * u) * S
                d.ellipse((X - rr, Y - rr, X + rr, Y + rr), fill=col + (int(255 * (1 - u) ** 1.2),))
        fx.over(cv, fx.draw_rgba((x - 160, y - 160, x + 160, y + 190), draw))
        put(cv, radial(256, col), x, y, 1.1, 0.35 * (1 - u))


def aurora(cv, t, a):
    if a <= 0:
        return
    gx0, gy0, gx1, gy1 = GLASS_F
    def draw(d, mp, S):
        for k, (col, yb) in enumerate((((90, 220, 210), gy0 + 40), ((150, 120, 255), gy0 + 80), ((120, 200, 255), gy0 + 120))):
            pts = []
            for i in range(0, 31):
                x = gx0 + i * (gx1 - gx0) / 30
                y = yb + 30 * math.sin(i * 0.4 + t * 0.9 + k) + 14 * math.sin(i * 0.9 - t * 1.3)
                pts.append(mp(x, y))
            for j in range(len(pts) - 1):
                (x0, y0), (x1, y1) = pts[j], pts[j + 1]
                d.polygon([(x0, y0), (x1, y1), (x1, y1 + 80 * S), (x0, y0 + 80 * S)], fill=col + (int(70 * a),))
    fx.over(cv, fx.draw_rgba((gx0, gy0, gx1, gy0 + 300), draw))


def tree_lights(cv, t):
    """Шары на ёлке за окном загораются: шапка, пряник, колокольчик — тёплым; носок — холодным, слабо."""
    seq = [(GIFTS[0][1] + 0.5, WARM, 1.0), (E.COOKIE + 0.5, (255, 220, 160), 1.0), (E.BELL + 0.5, GOLD, 1.0),
           (E.STOCK + 0.5, ICE, 0.45), (E.TEASE + 0.3, (255, 250, 255), 1.0)]
    ck = creepy_k(t)
    for j, (t0, col, k) in enumerate(seq):
        a = appear(t, t0, 0.4) * k * (1 - 0.85 * ck)
        if a <= 0:
            continue
        x, y = orn_xy(j)
        tw = 0.85 + 0.15 * math.sin(t * 3 + j)
        put(cv, radial(128, col), x, y, 0.55 * tw, a)
        put(cv, radial(64, WHITE), x, y, 0.28, a * 0.8)
    a = appear(t, E.MOVE2 + 0.2, 0.5)
    if a > 0:
        x, y = STAR
        put(cv, radial(128, (255, 236, 170)), x, y, 0.9 + 0.12 * math.sin(t * 4), a)


def snowflake(d, x, y, r, col, w):
    for q in range(6):
        ang = q * math.pi / 3
        x2, y2 = x + r * math.cos(ang), y + r * math.sin(ang)
        d.line((x, y, x2, y2), fill=col, width=w)
        for f in (0.5, 0.75):
            mx, my = x + r * f * math.cos(ang), y + r * f * math.sin(ang)
            for sgn in (-1, 1):
                a2 = ang + sgn * 0.7
                d.line((mx, my, mx + r * 0.28 * math.cos(a2), my + r * 0.28 * math.sin(a2)), fill=col, width=w)



@functools.lru_cache(None)
def garland_points():
    w = np.array(Image.open(DECOR / 'window_min.png').convert('RGB')).astype(int)
    br = (w[..., 0] + w[..., 1] + w[..., 2] > 600)
    br[240:] = False
    n, lab, st, cen = cv2.connectedComponentsWithStats(br.astype(np.uint8))
    pts = [wpt(cx, cy) for (cx, cy), s_ in zip(cen[1:], st[1:, 4]) if s_ >= 40]
    return pts


def room(cv, t):
    ck = creepy_k(t)
    for j, (x, y) in enumerate(garland_points()):
        tw = 0.55 + 0.45 * math.sin(t * 2.6 + j * 1.7) ** 2
        put(cv, radial(64, WARM if j % 2 else ICE), x, y, 0.75, tw * 0.75 * (1 - 0.85 * ck))


@functools.lru_cache(None)
def stocking_parts():
    im = Image.open(KEYED / 'stockings.png').convert('RGBA')
    runs = [(70, 340), (369, 632), (661, 930), (947, 1213), (1238, 1498)]
    s = 0.5
    out = []
    for x0, x1 in runs:
        p = im.crop((x0 - 12, 200, x1 + 12, 800))
        p = p.resize((round(p.width * s), round(p.height * s)), Image.LANCZOS)
        out.append((p, ((x0 + x1) / 2 - 768) * s * 1.5))
    string = im.crop((0, 210, 1536, 260)).resize((1060, 25), Image.LANCZOS)
    out = [out[0], out[1], out[3], out[2], out[4]]          # голубой носок — правее Миты, чтобы было видно
    out = [(p, d_) for (p, _), d_ in zip(out, [o[1] for o in sorted(out, key=lambda q: q[1])])]
    return out, string


def stockings(cv, t):
    parts, string = stocking_parts()
    k = appear(t, E.STOCK - 0.25, 0.6) * (1 - appear(t, E.CREEPY_END + 0.8, 0.6))
    if k <= 0:
        return
    y = SILL_Y + 70 - 160 * (1 - k)
    ck = creepy_k(t)
    put(cv, string, 540, y + 12, 1.0, k)
    for j, (p, dx) in enumerate(parts):
        if abs(dx) < 120:                # за Митой носок не виден — не рисуем
            continue
        amp = 0.05 * (1 - ck)
        rot = amp * math.sin(t * 1.4 + j * 1.1)
        sad = 0.0
        if j == 3:                      # голубой носок — «его никто не берёт»: никнет и тускнеет
            sad = appear(t, E.STOCK_NOBODY, 0.6) * (1 - appear(t, E.CREEPY_END + 0.5, 0.6))
            rot += 0.12 * sad
        put(cv, p, 540 + dx, y + 6, 1.0, k * (1.0 - 0.35 * sad), rot, anchor=(p.width / 2, 8))
        if j == 3 and sad > 0:
            put(cv, radial(128, ICE), 540 + dx, y + 150, 1.2, 0.25 * sad)


def easter_egg(cv, t):
    """Пасхалка: снеговик с синими хвостиками (как у Миты) в углу; реагирует: жуть — закрыл глаза, ×2 — удивился,
    финал — машет."""
    pose = 'snowman'
    if E.CREEPY - 0.1 <= t < E.CREEPY_END + 0.3:
        pose = 'snowman_scared'
    elif E.PRICE_X2 - 0.1 <= t < E.PRICE_X2 + 1.8 or E.HOOK_X <= t < E.HOOK_X + 1.4:
        pose = 'snowman_surprised'
    elif t >= E.CHOICE - 0.3 or E.B_END <= t < E.B_END + 1.2:
        pose = 'snowman_wave'
    im = keyed(pose, h=250)
    wave_ = 0.06 * math.sin(t * 2.2) * (1 - creepy_k(t))
    put(cv, im, 978, 1835, 1.0, 1.0, wave_, anchor=(im.width / 2, im.height))


def mita_shadow(cv, x, y):
    def draw(d, mp, S):
        X, Y = mp(x, y + 2)
        d.ellipse([X - 160 * S, Y - 20 * S, X + 160 * S, Y + 20 * S], fill=(20, 30, 70, 60))
    fx.over(cv, fx.draw_rgba((x - 180, y - 30, x + 180, y + 30), draw))


def background(t):
    cv = np.zeros((H, W, 4), np.float32)
    cv[..., :3] = wall()
    L = window_layers()
    ck = creepy_k(t)
    st = lights_state(t)(L['order'])
    st[0] = 1.0
    k = st[L['labs']][..., None]
    win = L['off'] + (L['on'] - L['off']) * k
    a = L['alpha'][..., None]
    cv[..., :3] = cv[..., :3] * (1 - a) + win * a
    gx0, gy0, gx1, gy1 = GLASS_F
    put(cv, radial(256, (250, 240, 200)), *wpt(320, 390), 0.7, 0.25 * (1 - 0.7 * ck))
    aurora(cv, t, appear(t, E.MOVE2, 1.0))
    fireworks(cv, t)
    tree_lights(cv, t)
    snowfall(cv, t, 30, 7, gy0, gy1, (35, 70), 0.6, 0.7, ck, gx0, gx1)
    snowfall(cv, t, 14, 11, gy0, gy1, (70, 120), 0.85, 1.0, ck, gx0, gx1)
    # рама поверх эффектов (всё, что вне стекла)
    fa = (L['alpha'] * (1 - L['glass']))[..., None]
    cv[..., :3] = cv[..., :3] * (1 - fa) + L['on'] * fa
    room(cv, t)
    stockings(cv, t)
    cv[..., 3] = 255
    return cv


# ------------------------------------------------------------------ градусник
THERMO_H = 620
TUBE = dict(x0=482, x1=540, top=250, bulb=(511, 1190), r=88)       # в координатах thermo.png 1024×1536 (до обрезки)
THERMO_MAX = 14.0


@functools.lru_cache(None)
def thermo_img(h):
    im = Image.open(KEYED / 'thermo.png').convert('RGBA')
    box = im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox()
    im = im.crop(box)
    s = h / im.height
    return im.resize((round(im.width * s), h), Image.LANCZOS), box, s


def slot_price(cv, x, y, t, t0, target, a=1.0, w=250, spin=0.9, fast=False, before=None):
    """Цена как барабан игрового автомата: цифры крутятся и встают на target (TON) с щелчком."""
    reel = keyed('ico_reel', w=w)
    put(cv, reel, x, y, 1.0, a)
    k = fx.clamp01((t - t0) / spin)
    if before is not None and t < t0:
        put(cv, utext(before, int(w * 0.15), 'ExtraBold', (190, 220, 255)), x, y + 4, 1.0, a)
        return
    if k < 1:
        rng = np.random.default_rng(int(t * (40 if fast else 22)))
        val = f'{rng.integers(1, 99)}'
        off = 30 * math.sin(t * (70 if fast else 45))
        put(cv, utext(val + ' TON', int(w * 0.17), 'ExtraBold', (255, 236, 170)), x, y + 4 + off * (1 - k), 1.0, a * 0.85)
    else:
        bump = fx.ease_out_back(fx.clamp01((t - t0 - spin) / 0.3))
        put(cv, utext(f'{target:g} TON', int(w * 0.17), 'ExtraBold', (255, 236, 170)), x, y + 4, 0.8 + 0.2 * bump, a)


def thermo(cv, cx, cy, h, level, col, a=1.0, frost=0.0, rising=0.0, t=0.0):
    """level 0..THERMO_MAX (TON). Жидкость рисуется внутри трубки; frost — иней на трубке (подешевел)."""
    im, box, s = thermo_img(h)
    x0 = cx - im.width / 2
    y0 = cy - h / 2
    put(cv, fx.soft_shadow(im.width - 20, h - 20, 40, 22, 0.35), cx + 8, cy + 16, 1.0, a)
    put(cv, im, cx, cy, 1.0, a)
    tx0 = x0 + (TUBE['x0'] - box[0]) * s
    tx1 = x0 + (TUBE['x1'] - box[0]) * s
    ttop = y0 + (TUBE['top'] - box[1]) * s
    bx, by = x0 + (TUBE['bulb'][0] - box[0]) * s, y0 + (TUBE['bulb'][1] - box[1]) * s
    br = TUBE['r'] * s
    lv = fx.clamp01(level / THERMO_MAX)
    ytop = by - br * 0.6 - (by - br * 0.6 - ttop) * lv

    def draw(d, mp, S):
        X0, Y0 = mp(tx0, ytop)
        X1, Y1 = mp(tx1, by)
        d.rounded_rectangle((X0, Y0, X1, Y1), int((X1 - X0) / 2), fill=col + (235,))
        BX, BY = mp(bx, by)
        R = br * S * 0.86
        d.ellipse((BX - R, BY - R, BX + R, BY + R), fill=col + (240,))
        if Y1 - R > Y0 + 14 * S:
            d.rounded_rectangle((X0 + (X1 - X0) * 0.18, Y0 + 6 * S, X0 + (X1 - X0) * 0.38, Y1 - R), 6 * S,
                                fill=(255, 255, 255, 90))
    fx.over(cv, fx.draw_rgba((x0, y0, x0 + im.width, y0 + h), draw), a)
    if frost > 0:                              # 3. цена упала — трубку затягивает ледяная корка
        put(cv, radial(128, ICE), cx, (ytop + by) / 2, 1.6, a * frost * 0.45)
        crust = keyed('ico_frost', w=int((tx1 - tx0) * 2.6))
        for q in range(3):
            put(cv, crust, cx, ytop + 40 + q * 110, 1.0, a * fx.clamp01(frost * 3 - q), math.pi / 2)
    if rising > 0:                             # 3. цена растёт — по столбику поднимаются пузырьки
        bub = keyed('ico_bubbles', w=int((tx1 - tx0) * 1.7))
        for q in range(3):
            ph = (t * 0.7 + q / 3) % 1
            yb = by - br * 0.5 - (by - br * 0.5 - ytop) * ph
            put(cv, bub, (tx0 + tx1) / 2 + 6 * math.sin(t * 5 + q), yb, 0.6 + 0.3 * ph, a * rising * math.sin(math.pi * ph))
    return ytop


# ------------------------------------------------------------------ сцена подарков (шапка, пряник, колокольчик, носок)
GIFTS = [  # ключ, начало, цена, цвет жидкости, подпись, комментарий (время, текст), иней
    ('hat', max(E.HAT, E.B_END + 0.25), 9.0, RED, 'ШАПКА САНТЫ', (E.HAT_PAPA, 'К ПРАЗДНИКУ!'), 0.0, '↑ ДОРОЖАЕТ'),
    ('cookie', E.COOKIE, 6.0, (236, 160, 80), 'ПРЯНИК', (E.COOKIE_MAMA, 'КАК СВИТЕР!'), 0.0, '= БЕЗ ИЗМЕНЕНИЙ'),
    ('bell', E.BELL, 13.0, GOLD, 'КОЛОКОЛЬЧИК', (E.BELL_FRIEND, 'ЗВОНКАЯ ЦЕНА!'), 0.0, 'САМЫЙ ДОРОГОЙ'),
    ('stock', E.STOCK, 5.0, (110, 170, 240), 'НОСОК', (E.STOCK_NOBODY, 'НИКТО НЕ БЕРЁТ…'), 1.0, 'САМЫЙ ДЕШЁВЫЙ'),
]
GIFT_END = E.CREEPY + 0.3


def gift_idx(t):
    j = -1
    for k, g in enumerate(GIFTS):
        if t >= g[1]:
            j = k
    return j


@functools.lru_cache(maxsize=8)
def bite_mask(size):
    m = Image.new('L', (size, size), 255)
    d = ImageDraw.Draw(m)
    for (x, y, r) in ((0.83, 0.2, 0.15), (0.94, 0.33, 0.12), (0.72, 0.1, 0.11)):
        d.ellipse(((x - r) * size, (y - r) * size, (x + r) * size, (y + r) * size), fill=0)
    return m


def scene_gifts(cv, t):
    if not (GIFTS[0][1] - 0.1 <= t < GIFT_END + 0.4):
        return
    a_all = 1 - appear(t, GIFT_END - 0.1, 0.4)
    j = gift_idx(t)
    if j < 0:
        return
    key, t0, price, col, name, (tc, comment), frost, tag = GIFTS[j]
    prev = GIFTS[j - 1] if j > 0 else None
    # градусник слева: уровень плавно перетекает от прошлого подарка
    lv0 = prev[2] if prev else 0.0
    u = ease((t - t0 - 0.25) / 0.9)
    lv = lv0 + (price - lv0) * u
    c0 = np.array(prev[3] if prev else col, np.float32)
    c = tuple(int(v) for v in c0 + (np.array(col, np.float32) - c0) * u)
    ta = appear(t, GIFTS[0][1] - 0.05, 0.4) * a_all
    rise = (1.0 if key in ('hat',) else 0.0) * u
    thermo(cv, 150, 960, THERMO_H, lv, c, ta, frost * u, rise, t)
    slot_price(cv, 150, 535, t, t0 + 0.1, price, ta, 240)
    put(cv, pill(rub(price), (196, 128, 70), 26), 150, 652 + 6 * math.sin(t * 2), pop(t, t0 + 0.45), ta)
    put(cv, pill(tag, (230, 80, 70) if j in (0, 2) else (90, 130, 200) if j == 3 else (130, 110, 90), 26),
        215, 1310, pop(t, t0 + 0.9), ta * appear(t, t0 + 0.9))
    # подарок — «ёлочная игрушка» на нитке справа, качается
    ga = appear(t, t0, 0.3) * a_all
    sw = 0.08 * math.sin(t * 1.7)
    gx, gy = 858 + 14 * math.sin(t * 1.3), 930 + 12 * math.sin(t * 1.9)        # справа на уровне Миты — заполняет середину
    size = 330
    im = gift_frame(key, t - t0, 512)
    im = im.resize((size, size), Image.LANCZOS)
    if key == 'cookie' and t >= E.COOKIE_BITE:
        im = im.copy()
        im.putalpha(Image.fromarray(np.minimum(np.array(im.getchannel('A')),
                                               np.array(bite_mask(size))).astype(np.uint8)))
    if key == 'stock':
        g = ease((t - E.STOCK_NOBODY) / 0.8)
        if g > 0:
            arr = np.array(im).astype(np.float32)
            lum = arr[..., :3].mean(-1, keepdims=True)
            arr[..., :3] = arr[..., :3] * (1 - 0.6 * g) + (lum * 0.7 + np.array(ICE) * 0.25) * 0.6 * g
            im = Image.fromarray(arr.clip(0, 255).astype(np.uint8))

    def string(d, mp, S):
        X0, Y0 = mp(850, 60)
        X1, Y1 = mp(gx, gy - size * 0.42)
        d.line((X0, Y0, X1, Y1), fill=(220, 225, 240, 230), width=int(3 * S))
    p = pop(t, t0, 0.5)
    lt = t - t0
    if key == 'hat':                            # шапка падает сверху со «скоростным» росчерком
        fall = ease(lt / 0.45)
        gy = gy - (1 - fall) * 900
        if lt < 0.6:
            put(cv, keyed('ico_swoosh', w=260), gx - 40, gy - 260, 1.0, ga * (1 - lt / 0.6), -0.4)
        p = 1.0 if lt > 0.45 else 0.9
    elif key == 'cookie':                       # пряник «выпекается»: выходит из облачка пара, золотистое свечение
        put(cv, keyed('fog', w=420), gx, gy + 20, 0.8 + 0.4 * ease(lt / 1.2), ga * (1 - ease((lt - 0.5) / 0.8)) * 0.8)
        put(cv, radial(256, (255, 200, 120)), gx, gy, 2.2, ga * 0.5 * (1 - ease((lt - 0.6) / 1.0)))
        p = 0.5 + 0.5 * ease(lt / 0.7)
    elif key == 'bell':                         # колокольчик звенит: качается, звуковые волны
        sw = 0.22 * math.sin(lt * 14) * math.exp(-lt * 1.5) + 0.05 * math.sin(t * 2)
        for q in range(2):
            ph = (lt * 1.3 + q * 0.5) % 1
            put(cv, keyed('ico_waves', w=360), gx, gy, 0.8 + 0.6 * ph, ga * (1 - ph) * 0.9)
    elif key == 'stock':                        # носок спускается на нитке и грустно покачивается
        drop = fx.ease_out_back(fx.clamp01(lt / 0.8))
        gy = gy - (1 - drop) * 600
        sw = 0.1 * math.sin(t * 1.2)
        def thread(d, mp, S, gx=gx, gy=gy):
            X0, Y0 = mp(gx, 0)
            X1, Y1 = mp(gx, gy - 190)
            d.line((X0, Y0, X1, Y1), fill=(200, 210, 235, 255), width=int(3 * S))
        fx.over(cv, fx.draw_rgba((gx - 10, 0, gx + 10, max(10, gy - 180)), thread), ga)
        p = 1.0
    gift_badge(cv, im, gx, gy, p, ga, sw * 0.6, key)
    # комментарий Миты зрителю
    ca = appear(t, tc, 0.3) * a_all * (1 - appear(t, (GIFTS[j + 1][1] if j + 1 < len(GIFTS) else GIFT_END) - 0.3, 0.3))
    if ca > 0:
        cp = pill(comment, (196, 128, 70) if key != 'stock' else (80, 110, 170), 28)
        put(cv, cp, W - cp.width / 2 - 14, gy + size * 0.64 + 4 * math.sin(t * 2.4),
            pop(t, tc, 0.45), ca, -0.04)
    # пустота снизу справа: цена две недели назад (Fragment, 04.11 → 17.11)
    was = {'hat': 7, 'cookie': 6, 'bell': 12, 'stock': 5}[key]
    wa = appear(t, t0 + 1.2, 0.3) * a_all * (1 - appear(t, (GIFTS[j + 1][1] if j + 1 < len(GIFTS) else GIFT_END) - 0.3, 0.3))
    if wa > 0:
        arrow = '↑' if price > was else ('=' if price == was else '↓')
        put(cv, keyed('ico_reel', w=300), 860, 1330, pop(t, t0 + 1.2), wa)
        put(cv, utext('БЫЛО', 24, 'ExtraBold', (190, 220, 255)), 860, 1296, pop(t, t0 + 1.2), wa)
        put(cv, utext(f'{was} TON {arrow}', 40, 'ExtraBold', (255, 236, 170)), 860, 1346, pop(t, t0 + 1.3), wa)
    # крошки при «надкусывании»
    if key == 'cookie' and E.COOKIE_BITE <= t < E.COOKIE_BITE + 1.2:
        u2 = (t - E.COOKIE_BITE) / 1.2
        def crumbs(d, mp, S):
            rng = np.random.default_rng(5)
            for k in range(12):
                x = gx + 90 + rng.uniform(-30, 50) + rng.uniform(-60, 60) * u2
                y = gy - 110 + 380 * u2 * u2 * rng.uniform(0.6, 1.2)
                X, Y = mp(x, y)
                r = rng.uniform(4, 8) * S
                d.ellipse((X - r, Y - r, X + r, Y + r), fill=(200, 130, 70, int(255 * (1 - u2))))
        fx.over(cv, fx.draw_rgba((gx - 100, gy - 200, gx + 300, gy + 420), crumbs))
    # колокольчик: искры
    if key == 'bell':
        def sp(d, mp, S):
            for k in range(6):
                ang = t * 1.4 + k * 1.05
                X, Y = mp(gx + 190 * math.cos(ang), gy + 170 * math.sin(ang))
                fx.sparkle(d, X, Y, (10 + 5 * math.sin(t * 6 + k)) * S, (255, 236, 160, 230))
        fx.over(cv, fx.draw_rgba((gx - 240, gy - 240, gx + 240, gy + 240), sp), ga)


# ------------------------------------------------------------------ дыхание на стекло: пряник (4-я стена)
FOG_X, FOG_Y = 400, 900


@functools.lru_cache(None)
def fog_patch():
    rng = np.random.default_rng(4)
    n = cv2.resize(rng.random((24, 24)).astype(np.float32), (520, 520), interpolation=cv2.INTER_CUBIC)
    yy, xx = np.mgrid[:520, :520]
    r = np.sqrt((xx - 260) ** 2 + (yy - 260) ** 2) / 260
    a = np.clip(1 - r, 0, 1) ** 0.8 * (0.6 + 0.4 * n)
    arr = np.dstack([np.full((520, 520, 3), 242, np.float32), np.clip(a * 260, 0, 235)]).astype(np.uint8)
    return Image.fromarray(arr)


def breath_glass(cv, t):
    t0 = E.COOKIE
    if not (t0 <= t < E.BELL + 0.6):
        return
    fa = ease((t - t0 - 0.5) / 1.0) * (1 - appear(t, E.BELL + 0.1, 0.5))
    put(cv, keyed('fog', w=420), FOG_X, FOG_Y, 0.85 + 0.15 * ease((t - t0 - 0.5) / 1.4), fa * 0.4)
    # «пишет пальцем»: цифры проявляются слева направо
    k = ease((t - t0 - 2.0) / 2.2)
    if k > 0:
        im = utext('6 TON', 100, 'ExtraBold', (250, 252, 255), 3, (170, 190, 220))
        arr = np.array(im)
        cut = int(arr.shape[1] * k)
        arr[:, cut:, 3] = 0
        put(cv, Image.fromarray(arr), FOG_X - 10, FOG_Y - 10, 1.0, fa * 0.9, -0.06)


# ------------------------------------------------------------------ жуть
def creepy_k(t):
    return ease((t - E.CREEPY) / 0.9) * (1 - ease((t - E.CREEPY_END) / 0.7))


@functools.lru_cache(None)
def vignette():
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.6)) ** 2)
    return np.clip(r - 0.35, 0, 1)[..., None]


def creepy_room(cv, t, k):
    """Комната темнеет и холодеет: синий оттенок + виньетка."""
    if k <= 0:
        return
    tint = np.array([0.36, 0.42, 0.7], np.float32)
    cv[..., :3] *= (1 - k) + k * tint
    cv[..., :3] *= 1 - 0.7 * k * vignette()


BALL_D = 600                      # диаметр пустой середины шара
BALL_TOP = 400                    # верх рамки шара, когда он опустился


@functools.lru_cache(None)
def ball_frame():
    """Стеклянный ёлочный шар (рамка автора) с прозрачной серединой — внутри будет Мита."""
    im, (cx, cy) = bauble(0, BALL_D)
    arr = np.array(im).astype(np.float32)
    yy, xx = np.mgrid[:arr.shape[0], :arr.shape[1]].astype(np.float32)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (BALL_D / 2)
    inner = np.clip((1.0 - r) / 0.04, 0, 1)
    arr[..., 3] *= 1 - inner * 0.9                 # середина почти прозрачная, лёгкий отлив стекла
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)), (cx, cy)


@functools.lru_cache(None)
def frost_ring():
    rng = np.random.default_rng(5)
    n = cv2.resize(rng.random((24, 24)).astype(np.float32), (BALL_D, BALL_D), interpolation=cv2.INTER_CUBIC)
    yy, xx = np.mgrid[:BALL_D, :BALL_D].astype(np.float32)
    r = np.sqrt((xx - BALL_D / 2) ** 2 + (yy - BALL_D / 2) ** 2) / (BALL_D / 2)
    a = np.clip((r - 0.55 - 0.15 * n) / 0.3, 0, 1) * (r < 1)
    return a


@functools.lru_cache(maxsize=48)
def glass_mita(idx):
    im = Image.open(HERE / 'build' / 'clips' / 'glass' / f'f{idx + 1:04d}.png').convert('RGBA')
    s = 520 / 998.0
    im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
    return im, (360 * s, 1179 * s)


def creepy_ball(cv, t):
    """Жуть: Мита внутри огромного ёлочного шара — висит на нитке, качается, стекло затягивает иней, трещина."""
    if not (E.CREEPY <= t < E.CREEPY_END):
        return
    u = ease((t - E.CREEPY) / 0.9)
    frame, (fcx, fcy) = ball_frame()
    D = BALL_D
    # внутренность шара: тёмное стекло + Мита + снежинки, по кругу
    inside = np.zeros((D, D, 4), np.float32)
    yy, xx = np.mgrid[:D, :D].astype(np.float32)
    rr = np.sqrt((xx - D / 2) ** 2 + (yy - D / 2) ** 2) / (D / 2)
    disc = np.clip((1 - rr) / 0.01, 0, 1)
    inside[..., :3] = np.array([24, 32, 70], np.float32) + np.array([40, 50, 90], np.float32) * (1 - rr[..., None])
    inside[..., 3] = disc * 0.9
    lt = t - E.CREEPY
    idx = min(239, int(lt * 24))
    mi, (ax, ay) = glass_mita(idx)
    tmp = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    tmp.alpha_composite(mi, (int(D / 2 - ax), int(D * 0.94 - ay)))
    m = np.array(tmp).astype(np.float32)
    ma = m[..., 3:4] / 255 * disc[..., None]
    cold = ease((t - E.CREEP_B) / 1.5)
    mrgb = m[..., :3] * (1 - 0.35 * cold) + np.array([150, 190, 255]) * 0.35 * cold
    inside[..., :3] = inside[..., :3] * (1 - ma) + mrgb * ma
    inside[..., 3] = np.maximum(inside[..., 3], ma[..., 0])
    # иней по краю стекла
    fk = 0.25 + 0.75 * ease((t - E.CREEP_B) / 2.5)
    fr = frost_ring()[..., None] * fk
    inside[..., :3] = inside[..., :3] * (1 - fr * 0.85) + np.array([232, 244, 255]) * fr * 0.85
    inside[..., 3] = np.maximum(inside[..., 3], fr[..., 0] * disc)
    ball = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    inside[..., 3] *= 255
    ball.alpha_composite(Image.fromarray(inside.clip(0, 255).astype(np.uint8)), (int(fcx - D / 2), int(fcy - D / 2)))
    ck_ = appear(t, E.CREEP_C, 0.25)
    if ck_ > 0:                                   # трещина
        cr = keyed('crack', w=int(D * 0.95))
        ball.alpha_composite(Image.fromarray((np.array(cr).astype(np.float32) * [1, 1, 1, ck_]).astype(np.uint8)),
                             (int(fcx - cr.width / 2 + 40), int(fcy - cr.height / 2 - 60)))
    ball.alpha_composite(frame)
    # висит на нитке и качается
    rot = 0.05 * math.sin((t - E.CREEPY) * 1.3)
    top_y = -frame.height + (BALL_TOP + frame.height) * u
    piv = (fcx, 0)
    def string(d, mp, S):
        X0, Y0 = mp(540, -10)
        X1, Y1 = mp(540 + math.sin(rot) * 0, top_y + 6)
        d.line((X0, Y0, X1, Y1), fill=(200, 210, 235, 255), width=int(3 * S))
    fx.over(cv, fx.draw_rgba((520, -20, 560, max(10, top_y + 20)), string))
    put(cv, radial(256, (120, 170, 255)), 540, top_y + fcy, 3.2, 0.35 * u)
    put(cv, ball, 540, top_y, 1.0, 1.0, rot, anchor=piv)
    if E.CREEP_C <= t < E.CREEP_C + 0.25:
        cv[..., :3] += (255 - cv[..., :3]) * 0.35 * (1 - (t - E.CREEP_C) / 0.25)


def ice_burst(cv, t):
    """Выход из жути: шар разлетается осколками (картинки автора) + снежный взрыв + вспышка."""
    u = (t - E.CREEPY_END) / 1.0
    if not 0 <= u < 1:
        return
    frame, (fcx, fcy) = ball_frame()
    cx, cy = 540, BALL_TOP + fcy
    put(cv, keyed('burst', w=700), cx, cy, 0.6 + 1.0 * fx.ease_out(u), (1 - u) ** 1.5)
    rng = np.random.default_rng(12)
    for i in range(14):
        sh = keyed(f'shard_{i % 6}', w=int(rng.uniform(70, 150)))
        ang = rng.uniform(0, 2 * math.pi)
        sp = rng.uniform(300, 650)
        x = cx + math.cos(ang) * sp * fx.ease_out(u)
        y = cy + math.sin(ang) * sp * fx.ease_out(u) + 600 * u * u
        put(cv, sh, x, y, 1.0, 1 - u, ang + u * rng.uniform(-6, 6))
    if u < 0.25:
        cv[..., :3] += (255 - cv[..., :3]) * (0.6 * (1 - u / 0.25))


# ------------------------------------------------------------------ заполнение боков (правило автора: без пустот)
SIDE_ITEMS = [('globe', 150, 985, 0.0), ('cane', 200, 1335, 1.3), ('jingle', 930, 960, 0.7), ('drink', 885, 1270, 2.1),
              ('wreath', 160, 720, 2.9)]
# подписи: название и цена (Fragment floor, 17.11.2026 — input/decor/PRICES.md)
SIDE_INFO = {'globe': ('СНЕЖНЫЙ ШАР', 8), 'cane': ('ЛЕДЕНЕЦ', 5), 'jingle': ('БУБЕНЦЫ', 12), 'drink': ('НАПИТОК', 6),
             'wreath': ('ВЕНОК', 6)}


def side_free(t):
    """Насколько бока свободны (0..1): в хуке, превращении, перед рекламой. Во время подарков, слуха и финала — заняты."""
    g0 = GIFTS[0][1]
    a = 1 - appear(t, g0 - 0.4, 0.4)                               # хук + превращение
    a += appear(t, E.CREEPY_END + 0.2, 0.5) * (1 - appear(t, E.MOVE1 - 0.2, 0.3))   # перед рекламой
    a += appear(t, E.MOVE2 + 0.4, 0.5)                                              # финал
    return fx.clamp01(a)


def side_fill(cv, t):
    a = side_free(t) * (1 - creepy_k(t))
    if a <= 0:
        return
    for j, (key, x, y, ph) in enumerate(SIDE_ITEMS):
        if key == 'wreath' and t < E.GLOVES_Q:
            continue
        dy = 22 * math.sin(t * 0.9 + ph)
        dx = 10 * math.sin(t * 0.6 + ph * 1.7)
        gi = gift_frame(key, t, 256, ph).resize((140, 140), Image.LANCZOS)
        gift_badge(cv, gi, x + dx, y + dy, 0.95, a * appear(t, 0.2 + 0.15 * j, 0.4), 0.06 * math.sin(t + ph), key)
        nm, pr = SIDE_INFO[key]
        ia = a * appear(t, 0.5 + 0.15 * j, 0.3)
        cx_ = min(max(x + dx, 120), 960)
        put(cv, pill(nm, (60, 76, 140), 22), cx_, y + dy + 98, 1.0, ia)
        put(cv, pill(f'{pr} TON · {rub(pr)}', (196, 128, 70), 20), cx_, y + dy + 142, 1.0, ia)
    # искорки-снежинки между ними
    def sp(d, mp, S):
        for k in range(10):
            side = k % 2
            x = (60 + 190 * ((k * 0.37) % 1)) if side == 0 else (830 + 200 * ((k * 0.53) % 1))
            y = 700 + (k * 97 + t * 25) % 760
            X, Y = mp(x, y)
            fx.sparkle(d, X, Y, (7 + 4 * math.sin(t * 3 + k)) * S, (200, 220, 250, int(200 * a)))
    fx.over(cv, fx.draw_rgba((0, 680, W, 1480), sp))


# ------------------------------------------------------------------ хук: силуэт перчаток со знаком вопроса
def scene_hook(cv, t):
    """Хук: «Обычные зимние перчатки… взлетели в цене в разы. И всё — из-за одного слуха.»"""
    a = appear(t, E.GLOVES_Q, 0.35) * (1 - appear(t, E.BOX_IN + 0.3, 0.4))
    if a <= 0:
        return
    x, y = 540, 420 + 10 * math.sin(t * 2)
    jump = fx.ease_out_back(fx.clamp01((t - E.HOOK_X) / 0.5)) * (1 - ease((t - E.HOOK_X - 0.8) / 0.6))
    y -= 50 * jump
    im = gift_frame('mitt', t, 512).resize((300, 300), Image.LANCZOS)
    put(cv, radial(256, (255, 236, 170)), x, y, 2.2, 0.35 * a)
    gift_badge(cv, im, x, y, pop(t, E.GLOVES_Q, 0.5) * (1 + 0.08 * jump), a, 0.05 * math.sin(t * 3), 'mitt')
    # «в разы!» — стрелка вверх и плашка
    xa = appear(t, E.HOOK_X, 0.25)
    if xa > 0:
        put(cv, utext('↑', 120, 'ExtraBold', RED, 6, WHITE), x + 230, y - 40 - 30 * jump, pop(t, E.HOOK_X, 0.45), a * xa)
        put(cv, pill('В РАЗЫ!', RED, 34), x + 210, y + 90, pop(t, E.HOOK_X + 0.1, 0.45), a * xa, 0.08)
    ra = appear(t, E.HOOK_RUMOR, 0.25)
    if ra > 0:
        put(cv, pill('СЛУХ?', (60, 76, 140), 36), x - 220, y + 120, pop(t, E.HOOK_RUMOR, 0.45), a * ra, -0.08)
        put(cv, utext('?', 120, 'ExtraBold', WHITE, 6, (60, 90, 170)), x - 210, y - 70, pop(t, E.HOOK_RUMOR + 0.1),
            a * ra, -0.15 + 0.08 * math.sin(t * 4))


# ------------------------------------------------------------------ коробка: «пуф» при появлении/исчезновении
def poof(cv, t, t0, x, y, n=22, col=(255, 255, 255), spread=180):
    u = (t - t0) / 0.6
    if not 0 <= u < 1:
        return
    put(cv, keyed('burst', w=520), x, y, (spread / 240) * (0.4 + 0.9 * fx.ease_out(u)), (1 - u) ** 1.3, u * 0.6)


def transform_fx(cv, t):
    poof(cv, t, E.BOX_IN - 0.05, 700, 1450, 18, (255, 240, 220), 140)       # коробка появляется
    poof(cv, t, E.BOX_POOF, 700, 1450, 18, (255, 240, 220), 140)            # коробка исчезает
    # вспышка-склейка (обычная → пряничная)
    u = (t - (E.FLASH - 0.18)) / 0.45
    if 0 <= u < 1:
        k = math.sin(math.pi * u) ** 1.3
        put(cv, radial(256, (255, 248, 236)), 540, 1150, 4.2, k)
        cv[..., :3] += (255 - cv[..., :3]) * (0.82 * k)


def box_cover(cv, t):
    """Коробка из клипа B исчезает сама (её убираем после разворота лент)."""
    return


# ------------------------------------------------------------------ перчатки ведут себя иначе (перед рекламой)
def scene_tease(cv, t):
    if not (E.CREEPY_END - 0.1 <= t < AD_STOP + 0.1):
        return
    a = appear(t, E.CREEPY_END + 0.2, 0.4)
    jump = ease((t - E.TEASE_JUMP) / 0.5)
    for j, key in enumerate(('hat', 'cookie', 'bell', 'stock')):
        x = (130, 290, 790, 950)[j]
        y = 400 + 8 * math.sin(t * 2 + j)
        gi = gift_frame(key, t, 256, j * 0.4).resize((150, 150), Image.LANCZOS)
        if jump > 0:
            arr = np.array(gi).astype(np.float32)
            lum = arr[..., :3].mean(-1, keepdims=True)
            arr[..., :3] = arr[..., :3] * (1 - 0.7 * jump) + lum * 0.7 * jump
            gi = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
        gift_badge(cv, gi, x, y, pop(t, E.CREEPY_END + 0.2 + 0.1 * j) * (1 - 0.15 * jump), a * (1 - 0.3 * jump), 0.0, key)
    ta = appear(t, E.TEASE, 0.3)
    if ta > 0:
        y = 380 - 120 * fx.ease_out_back(fx.clamp01((t - E.TEASE_JUMP) / 0.6)) + 10 * math.sin(t * 3)
        sh = 0.12 * math.sin(t * 26) * jump * (1 - ease((t - E.TEASE_JUMP - 0.8) / 0.4))
        put(cv, radial(256, (255, 236, 170)), 540, y, 2.0 + 0.5 * jump, 0.45 * ta)
        im = gift_frame('mitt', t, 512).resize((260, 260), Image.LANCZOS)
        gift_badge(cv, im, 540, y, pop(t, E.TEASE, 0.5) * (1 + 0.25 * jump), ta, sh, 'mitt')
        if jump > 0:
            for k, (dx, dy, r) in enumerate(((-170, -60, -0.3), (170, -80, 0.3), (0, -200, 0.0))):
                put(cv, utext('!' if k < 2 else '?', 90, 'ExtraBold', (255, 220, 120), 5, INK), 540 + dx, y + dy,
                    pop(t, E.TEASE_JUMP + 0.15 * k), jump, r + 0.1 * math.sin(t * 5 + k))


# ------------------------------------------------------------------ слух: видео → пост → удалён
CARD_X, CARD_Y, CARD_W, CARD_H = 790, 830, 440, 760


@functools.lru_cache(None)
def card_base(dark):
    w, h = CARD_W, CARD_H
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 46, fill=(20, 22, 40, 255) if dark else (246, 248, 255, 255),
                        outline=(255, 255, 255, 255), width=6)
    return im


def scene_rumor(cv, t):
    if not (E.MOVE1 <= t < E.SPREAD + 0.5):
        return
    a = appear(t, E.MOVE1 + 0.3, 0.4) * (1 - appear(t, E.SPREAD, 0.4))
    if a <= 0:
        return
    cx, cy = CARD_X, CARD_Y + 8 * math.sin(t * 1.6)
    flip = ease((t - E.RUMOR_POST) / 0.5)
    sx = max(0.02, abs(math.cos(math.pi * flip)))
    post = flip >= 0.5
    deleted = t >= E.RUMOR_DEL + 0.4
    tilt = -0.04
    if not post:
        card = keyed('card_video', w=440)
        fx.over(cv, fx.warp(card, cx, cy, sx, 1.0, tilt), a)
        gi = gift_frame('mitt', t, 512).resize((270, 270), Image.LANCZOS)
        fx.over(cv, fx.warp(gi, cx - 20, cy - 40 + 22 * abs(math.sin(t * 3.2)), sx, 1.0, tilt), a)
        put(cv, utext('СЛИВ?!', 52, 'ExtraBold', WHITE, 4, RED), cx - 20, cy - 250, sx * pop(t, E.RUMOR_VIDEO + 0.2), a, tilt)
    elif not deleted:
        card = keyed('card_post', w=460)
        fx.over(cv, fx.warp(card, cx, cy, sx, 1.0, tilt), a)
        gi = gift_frame('mitt', t, 512).resize((230, 230), Image.LANCZOS)
        fx.over(cv, fx.warp(gi, cx, cy + 110, sx, 1.0, tilt), a)
        put(cv, pill('ЗИМНИЙ КРАФТ?', (60, 90, 170), 30), cx, cy + 340, sx * pop(t, E.RUMOR_POST + 0.4), a, tilt)
        if t >= E.RUMOR_DEL:
            poof(cv, t, E.RUMOR_DEL, cx, cy, 30, (230, 240, 255), 300)
    # под карточкой: что это и сколько просмотров
    lab = 'ВИДЕО В ТИКТОКЕ' if not post else ('ПОСТ В КАНАЛЕ' if not deleted else 'ВИСЕЛ ПАРУ МИНУТ')
    put(cv, pill(lab, (40, 52, 104), 28), cx, 1300, 1.0, a)
    views = int(1_250_000 * ease((t - E.RUMOR_VIDEO) / 3.0))
    put(cv, keyed('ico_video', w=90), cx - 150, 1395, 1.0, a * appear(t, E.RUMOR_VIDEO, 0.3))
    put(cv, utext(f'{views:,}'.replace(',', ' '), 40, 'ExtraBold', INK), cx + 30, 1395, 1.0, a * appear(t, E.RUMOR_VIDEO, 0.3))
    if deleted:
        da = appear(t, E.RUMOR_DEL + 0.4, 0.3)
        card = keyed('card_deleted', w=470)
        put(cv, card, cx, cy, pop(t, E.RUMOR_DEL + 0.4), a * da, tilt)
        put(cv, utext('ПОСТ УДАЛЁН', 34, 'ExtraBold', (90, 96, 120)), cx + 50, cy - 6, pop(t, E.RUMOR_DEL + 0.5), a * da,
            tilt)


SPREAD_TAGS = [(0.0, 'ПЕРЧАТКИ?!', 820, 300, (232, 70, 64)), (0.4, 'КРАФТ!!', 700, 560, (196, 128, 70)),
               (0.8, 'СЛИВ?', 930, 700, (60, 90, 170)), (1.2, 'ПРАВДА?..', 760, 860, (110, 116, 140))]


def scene_spread(cv, t):
    if not (E.SPREAD <= t < E.PRICE + 0.4):
        return
    a = 1 - appear(t, E.PRICE - 0.1, 0.4)
    for dt, s_, x, y, col in SPREAD_TAGS:
        t0 = E.SPREAD + 0.2 + dt
        put(cv, pill(s_, col, 40), x + 6 * math.sin(t * 2 + x), y + 6 * math.cos(t * 2.2 + y), pop(t, t0),
            a * appear(t, t0, 0.2), 0.06 * math.sin(x))
    for k, (s_, w0, ico) in enumerate((('БЛОГЕРЫ', 'блогеры', 'ico_video'), ('КАНАЛЫ', 'каналы', 'ico_mega'),
                                       ('ЧАТЫ', 'чаты', 'ico_chat'))):
        t0 = E.at(w0, 0, ON[10]) - 0.1
        y = 1010 + k * 130
        put(cv, keyed(ico, w=120), 700, y, pop(t, t0), a * appear(t, t0, 0.2))
        put(cv, pill(s_, (40, 52, 104), 34), 860, y, pop(t, t0 + 0.1), a * appear(t, t0, 0.2))
    # охваты: мегафон и растущий счётчик
    oa = a * appear(t, E.SPREAD + 0.1, 0.3)
    put(cv, keyed('ico_mega', w=170), 690, 1420, pop(t, E.SPREAD + 0.1), oa, -0.1)
    reach = int(1_250_000 + 3_750_000 * ease((t - E.SPREAD) / 4.0))
    put(cv, utext(f'{reach:,}'.replace(',', ' '), 40, 'ExtraBold', INK), 900, 1400, 1.0, oa)
    put(cv, utext('ОХВАТЫ ↑', 24, 'ExtraBold', RED), 900, 1448, 1.0, oa)
    # письма-слухи летят к домикам за окном (окна загораются цепочкой — lights_state)
    gx0, gy0, gx1, gy1 = GLASS_F
    for q in range(8):
        tq = E.SPREAD + 0.5 + q * 0.4
        u = (t - tq) / 0.9
        if not 0 <= u < 1:
            continue
        tx = gx0 + (gx1 - gx0) * (q + 0.5) / 8
        ty = gy1 - 80
        sx_, sy_ = 790, 1000
        x = sx_ + (tx - sx_) * ease(u)
        y = sy_ + (ty - sy_) * ease(u) - 160 * math.sin(math.pi * u)
        put(cv, keyed('ico_mail', w=110), x, y, 1 - 0.4 * u, a * (1 - ease((u - 0.8) / 0.2)), -0.3 + 0.6 * u)


RARE_MITT = ['Astronaut', 'Diamond Hands', 'Fire Nation', 'Polaris', 'Jelly Bears']


def scene_price(cv, t):
    if not (E.PRICE <= t < E.TRUTH + 0.4):
        return
    a = appear(t, E.PRICE + 0.1, 0.35) * (1 - appear(t, E.TRUTH - 0.1, 0.4))
    up = ease((t - E.PRICE_NOW) / 1.3)
    lv = 3.5 + (10 - 3.5) * up
    col = tuple(int(v) for v in np.array((110, 170, 240)) + (np.array(RED) - np.array((110, 170, 240))) * up)
    thermo(cv, 880, 1040, 760, lv, col, a, (1 - up) * appear(t, E.PRICE_THEN, 0.3), up, t)
    slot_price(cv, 600, 790, t, E.PRICE_NOW - 0.2, 10, a, 250, 1.2, True, '3–4 TON')
    gi = gift_frame('mitt', t, 512).resize((230, 230), Image.LANCZOS)
    put(cv, radial(256, WARM), 880, 470, 1.6, 0.4 * a)
    gift_badge(cv, gi, 880, 470 + 10 * math.sin(t * 2), pop(t, E.PRICE + 0.1), a, 0.0, 'mitt')
    put(cv, pill('ТОГДА: 3–4 TON · ~260–345 ₽', (80, 110, 170), 30), 470, 560, pop(t, E.PRICE_THEN), a * appear(t, E.PRICE_THEN, 0.2))
    put(cv, pill('СЕЙЧАС: 10 TON · ' + rub(10), (232, 70, 64), 32), 490, 650, pop(t, E.PRICE_NOW + 0.4),
        a * appear(t, E.PRICE_NOW + 0.4, 0.2))
    if t >= E.PRICE_X2:
        put(cv, keyed('x2', w=280), 620, 960, pop(t, E.PRICE_X2, 0.5), a, -0.1)
    # редкие модели перчаток — веером пролетают за градусником
    for q, mdl in enumerate(RARE_MITT):
        tq = E.PRICE_THEN + 0.2 + q * 0.2
        k = appear(t, tq, 0.4)
        if k <= 0:
            continue
        rx, ry = (560, 690, 560, 690, 625)[q], (1110, 1190, 1270, 1350, 1440)[q]
        mi = lottie.frame(str(gifts_api.model_file('Snow Mittens', mdl, 'tgs')), t, size=256, offset=q * 0.3)
        mi = mi.resize((120, 120), Image.LANCZOS)
        gift_badge(cv, mi, rx, ry + 8 * math.sin(t * 2 + q), k * 0.85, a * k, 0.1 * math.sin(t + q), ('mitt', 'stock', 'bell', 'cookie', 'mitt')[q])


def scene_truth(cv, t):
    if not (E.TRUTH <= t < E.MOVE2 + 0.4):
        return
    a = appear(t, E.TRUTH + 0.1, 0.35) * (1 - appear(t, E.MOVE2, 0.4))
    put(cv, radial(256, ICE), 820, 620, 2.2, 0.45 * a)
    put(cv, keyed('ice_q', h=380), 820, 620 + 14 * math.sin(t * 2), pop(t, E.TRUTH + 0.1, 0.5), a, 0.06 * math.sin(t * 1.5))
    put(cv, pill('НИКТО НЕ ЗНАЕТ', (60, 76, 140), 28), 820, 850, pop(t, E.TRUTH + 1.0), a * appear(t, E.TRUTH + 1.0, 0.2))
    put(cv, pill('СКОРЕЕ ВСЕГО — СЛУХ', (110, 116, 140), 26), 820, 940, pop(t, E.TRUTH_NO),
        a * appear(t, E.TRUTH_NO, 0.2), -0.05)
    k = ease((t - E.TRUTH_MARKET) / 1.0)
    ra = appear(t, E.TRUTH + 0.4, 0.3) * (1 - appear(t, E.TRUTH_MARKET - 0.2, 0.3))
    if ra > 0:
        put(cv, keyed('card_deleted', w=440), 820, 1150, pop(t, E.TRUTH + 0.4), a * ra, -0.04)
        put(cv, utext('ПОСТ УДАЛЁН', 32, 'ExtraBold', (90, 96, 120)), 870, 1144, 1.0, a * ra, -0.04)
        put(cv, keyed('emo_quest', h=90), 1000, 1050, 1.0, a * ra, 0.2 + 0.1 * math.sin(t * 3))
    if k > 0:
        put(cv, keyed('card_chart', w=470), 820, 1150, pop(t, E.TRUTH_MARKET), a)
        put(cv, radial(128, (255, 120, 100)), 820 + 205, 1150 - 110, 0.6 + 0.2 * math.sin(t * 5), 0.6 * a * k)
        put(cv, pill('РЫНОК ПОВЕРИЛ', (232, 70, 64), 26), 820, 1340, pop(t, E.TRUTH_MARKET + 0.4),
            a * appear(t, E.TRUTH_MARKET + 0.4, 0.2))


# ------------------------------------------------------------------ финал: снежный шар-гадалка «Верю / Не верю»
@functools.lru_cache(None)
def globe_big():
    im = keyed('globe', h=560)
    return im, (im.width * 0.5, im.height * 0.38, im.width * 0.355)      # центр и радиус стеклянной сферы


def scene_choice(cv, t):
    """Мита трясёт шар (клип globe); над ней — увеличенный шар: метель, по очереди «ВЕРЮ» / «НЕ ВЕРЮ», ответа нет."""
    t0 = E.MOVE2 + 0.8
    if t < t0:
        return
    im, (scx, scy, sr) = globe_big()
    gx, gy = 540, 470
    a = appear(t, t0, 0.35)
    shake = (E.MOVE2 + 1.0 <= t < E.MOVE2 + 3.4)
    rot = 0.07 * math.sin(t * 24) if shake else 0.015 * math.sin(t * 2)
    dy = 10 * math.sin(t * 24) if shake else 6 * math.sin(t * 2)
    put(cv, radial(256, (220, 236, 255)), gx, gy, 2.6, 0.5 * a)
    put(cv, im, gx, gy + dy, pop(t, t0, 0.5), a, rot)
    # центр сферы на экране
    cx = gx - im.width / 2 + scx
    cy = gy + dy - im.height / 2 + scy
    # слова по очереди: метель «гадает»
    lt = t - (E.MOVE2 + 1.1)
    if lt > 0:
        k = int(lt / 0.55)
        ph = (lt / 0.55) % 1
        word, col = (('ВЕРЮ', (196, 110, 50)), ('НЕ ВЕРЮ', (60, 100, 190)))[k % 2]
        wa = math.sin(math.pi * ph) ** 0.6 * a
        if t > E.CHOICE + 0.4:                                     # ответа нет — снег не оседает: «?»
            word, col, wa = '?', (60, 100, 190), a * (0.75 + 0.25 * math.sin(t * 3))
        put(cv, utext(word, 46 if len(word) > 4 else 90, 'ExtraBold', WHITE, 5, col), cx, cy, 0.9 + 0.1 * wa, wa)
    # метель внутри сферы
    def snow(d, mp, S):
        rng = np.random.default_rng(4)
        sp = 3.0 if shake else 0.8
        for i in range(46):
            ang = rng.uniform(0, 2 * math.pi) + t * sp * rng.uniform(0.5, 1.2)
            rad = sr * 0.85 * math.sqrt(rng.uniform(0, 1))
            X, Y = mp(cx + rad * math.cos(ang), cy + rad * math.sin(ang) * 0.9)
            r = rng.uniform(2.5, 6) * S
            d.ellipse((X - r, Y - r, X + r, Y + r), fill=(255, 255, 255, 235))
    fx.over(cv, fx.draw_rgba((cx - sr, cy - sr, cx + sr, cy + sr), snow), a)
    put(cv, pill('РЕШАТЬ ТЕБЕ!', (60, 76, 140), 30), gx, gy + im.height * 0.5 + 10, pop(t, E.CHOICE), appear(t, E.CHOICE, 0.2))
    put(cv, pill('ПИШИ В КОММЕНТАРИЯХ!', (196, 128, 70), 28), gx, gy + im.height * 0.5 + 70, pop(t, E.CHOICE + 0.3),
        appear(t, E.CHOICE + 0.3, 0.2))


# ------------------------------------------------------------------ эмоции над головой (картинки автора)
REACT = [(E.HOOK_X, 'excl'), (E.HOOK_RUMOR, 'quest'), (E.B_END + 0.1, 'sparkle'), (E.HAT_PAPA, 'flake'),
         (E.COOKIE_MAMA + 0.3, 'heart'), (E.BELL_FRIEND, 'notes'), (E.STOCK_NOBODY, 'tear'), (E.TEASE, 'excl'),
         (E.RUMOR_DEL + 0.3, 'sweat'), (E.SPREAD_ALL, 'surprise'), (E.PRICE_X2, 'surprise'), (E.TRUTH + 1.0, 'quest'),
         (E.CHOICE, 'heart')]


def reactions(cv, t):
    for t0, kind in REACT:
        k = t - t0
        if not 0 <= k < 1.4:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 1.0) / 0.4))
        p = fx.ease_out_back(fx.clamp01(k / 0.35))
        x0 = M.x_of(t)
        head = M.FOOT - M.MITA_H
        if kind == 'sweat':
            x, y, rot, h = x0 + 105, head + 70, -0.5, 70
        elif kind == 'tear':
            x, y, rot, h = x0 - 120, head + 30 - 30 * ease(k / 1.4), 0.1, 80
        else:
            x, y, rot, h = x0 + 150, head + 10 - 40 * ease(k / 1.4), 0.12 * math.sin(k * 6), 110
        put(cv, keyed(f'emo_{kind}', h=h), x, y, 0.6 + 0.4 * p, a, rot)


# ------------------------------------------------------------------ перемещение «снежной россыпью»
def snow_poof(cv):
    def tool(x, u, out):
        rng = np.random.default_rng(int(x) + (1 if out else 2))

        def draw(d, mp, S):
            for i in range(40):
                px = x + rng.uniform(-170, 170)
                py = M.FOOT - rng.uniform(0, M.MITA_H)
                drift = (u if out else 1 - u)
                X, Y = mp(px + 60 * drift * math.sin(i), py - 120 * drift + 30 * math.sin(i * 1.3))
                r = rng.uniform(3, 8) * S * (math.sin(math.pi * min(1, u)) + 0.2)
                d.ellipse((X - r, Y - r, X + r, Y + r), fill=(255, 255, 255, 230))
        fx.over(cv, fx.draw_rgba((x - 260, M.FOOT - M.MITA_H - 180, x + 260, M.FOOT + 40), draw))
    return tool


# ------------------------------------------------------------------ субтитры
def _disp(w):
    return re.sub(r'[.,:;…!?]+$', '', w.replace('«', '').replace('»', ''))


def _chunks():
    out, cur = [], []
    for w in WORDS:
        if cur and (len(cur) >= 3 or cur[-1][3] != w[3] or sum(len(x[0]) for x in cur) + len(w[0]) > 20
                    or re.search(r'[.!?…:,—]$', cur[-1][0])):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


CHUNKS = _chunks()


def subtitles(cv, t):
    ch = None
    for k, c in enumerate(CHUNKS):
        t0 = c[0][1] - 0.06
        t1 = CHUNKS[k + 1][0][1] - 0.06 if k + 1 < len(CHUNKS) else c[-1][2] + 0.6
        t1 = min(t1, c[-1][2] + 0.7)
        if t0 <= t < t1:
            ch, start = c, t0
            break
    if ch is None:
        return
    creepy = creepy_k(t) > 0.5
    acc = (120, 190, 255) if creepy else (214, 120, 50)
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = acc if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (INK if on else (160, 164, 186))
        parts.append(((' ' if j else '') + _disp(w[0]).upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    p = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    put(cv, fx.rounded(pw, 84, 30, (250, 252, 255, 238), (210, 222, 245, 255), 3), 540, SUB_Y, 0.85 + 0.15 * p, 1.0)
    put(cv, im, 540, SUB_Y, sc * (0.85 + 0.15 * p), 1.0)


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    ck = creepy_k(t)
    easter_egg(cv, t)
    side_fill(cv, t)
    scene_hook(cv, t)
    scene_gifts(cv, t)
    if t != AD_STOP:
        M.draw(cv, t, put, mita_shadow if ck < 0.5 else None, snow_poof(cv))
    transform_fx(cv, t)
    breath_glass(cv, t)
    scene_tease(cv, t)
    scene_rumor(cv, t)
    scene_spread(cv, t)
    scene_price(cv, t)
    scene_truth(cv, t)
    scene_choice(cv, t)
    reactions(cv, t)
    if ck > 0:
        creepy_room(cv, t, ck)
    creepy_ball(cv, t)
    ice_burst(cv, t)
    if not (AD_STOP - 0.02 <= t < AD_STOP + 0.1):
        subtitles(cv, t)
    return np.clip(cv[..., :3], 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ реклама: ёлка над баннером, Санта под баннером
BAN_TOP = int(H / 2 - 283)
BAN_BOT = int(H / 2 + 284)


@functools.lru_cache(maxsize=300)
def santa_frame(idx, w):
    im = Image.open(HERE / 'build' / 'clips' / 'santa' / f'f{idx + 1:04d}.png')
    box = (0, 120, 1280, 620)
    im = im.crop(box)
    return im.resize((w, round(im.height * w / im.width)), Image.BILINEAR)


def ad_overlay(c, t):
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    snowfall(cv, t, 50, 21, 0, BAN_TOP, (60, 120), 0.9 * a, 1.0)
    snowfall(cv, t, 60, 23, BAN_BOT, H, (60, 120), 0.9 * a, 1.1)
    M.draw_ad(cv, bt, put, a, 1080, BAN_TOP - 10, 560)
    put(cv, pill('С НАСТУПАЮЩИМ!', (196, 128, 70), 30), 300, BAN_TOP - 330 + 8 * math.sin(t * 2), pop(bt, 0.4), a, -0.06)
    put(cv, keyed('globe', h=230), 260, BAN_TOP - 125, 1.0, a, 0.04 * math.sin(t * 1.5))
    # Санта пролетает под баннером слева направо
    B = BR.B
    u = fx.clamp01((bt + 0.2) / max(1.0, B + 0.2))
    sw = 900
    x = -sw / 2 - 40 + (W + sw + 80) * u
    y = BAN_BOT + 330 + 30 * math.sin(bt * 2.2)
    idx = int((bt + 1.0) * 24) % 240
    put(cv, santa_frame(idx, sw), x, y, 1.0, a, -0.04)
    # хвост искр за санями
    def trail(d, mp, S):
        rng = np.random.default_rng(3)
        for i in range(30):
            k = i / 30
            X, Y = mp(x - sw * 0.42 - 380 * k + rng.uniform(-20, 20), y + 60 + 40 * math.sin(k * 6 + bt * 3))
            fx.sparkle(d, X, Y, (10 - 7 * k) * S, (255, 240, 200, int(230 * (1 - k))))
    fx.over(cv, fx.draw_rgba((x - sw / 2 - 460, y - 120, x - sw / 2 + 40, y + 200), trail), a)
    return cv[..., :3]


TOTAL = BR.out_dur(DUR)
LOOP_D = 0.55


def snow_cover(img, k, seed_t):
    """Петля «снежный шар»: снег заметает кадр (k→1) / оседает (k→0)."""
    if k <= 0:
        return img
    cv = np.dstack([img.astype(np.float32), np.full(img.shape[:2], 255, np.float32)])
    def draw(d, mp, S):
        rng = np.random.default_rng(77)
        for i in range(260):
            x = rng.uniform(0, W)
            y = rng.uniform(-100, H + 100) + 120 * math.sin(seed_t * 3 + i)
            X, Y = mp(x, y)
            r = rng.uniform(14, 40) * S * k
            d.ellipse((X - r, Y - r, X + r, Y + r), fill=(255, 255, 255, 255))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), draw), min(1.0, k * 1.4))
    cv[..., :3] += (np.array([238, 244, 255]) - cv[..., :3]) * max(0, k - 0.55) / 0.45
    return cv[..., :3]


def globe_shake(img, t):
    """В конце ролика на подоконник встаёт снежный шар и встряхивается."""
    t0 = TOTAL - 1.6
    if t < t0:
        return img
    cv = np.dstack([img.astype(np.float32), np.full(img.shape[:2], 255, np.float32)])
    u = t - t0
    sh = 0.18 * math.sin(u * 26) * ease((u - 0.5) / 0.2)
    put(cv, keyed('globe', h=240), 540, 1800 + 20 * math.sin(u * 26) * ease((u - 0.5) / 0.2), pop(t, t0, 0.45), 1.0, sh,
        anchor=None)
    return cv[..., :3]


def out_frame(t, i=None):
    img = ad_overlay(BR.render(render_at, t, i).astype(np.float32), t)
    k_end = ease((t - (TOTAL - LOOP_D)) / LOOP_D)
    k_start = 1 - ease(t / LOOP_D)
    img = snow_cover(img, max(k_end, k_start), t)
    return np.clip(img, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return out_frame(i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--content' in sys.argv or '--out' in sys.argv:
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        key = '--content' if '--content' in sys.argv else '--out'
        fn = render_at if key == '--content' else out_frame
        for s in sys.argv[sys.argv.index(key) + 1].split(','):
            Image.fromarray(fn(float(s))).save(out / f'{key[2]}{float(s):06.2f}.png')
            print(key, s)
        raise SystemExit
    frames.cli(out_frame, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
