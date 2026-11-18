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
        'mitt': 'Snow Mittens'}


@functools.lru_cache(None)
def gift_path(key):
    return str(gifts_api.original_file(GIFT[key], 'tgs'))


def gift_frame(key, t, size, off=0.0):
    return lottie.frame(gift_path(key), t, size=size, offset=off)


@functools.lru_cache(maxsize=32)
def radial(size, rgb, power=2.0):
    return fx.radial(size, rgb, power, 1.0)


# ------------------------------------------------------------------ городок за окном
SKY0, SKY1 = (20, 28, 70), (52, 66, 128)
WALL, FLOOR = (46, 58, 112), (64, 80, 140)
WIN_BOX = (70, 150, 1010, 940)            # окно: x0, y0, x1, y1 (низ = подоконник)
SILL_Y = 940
TREE_X = 862
ORNAMENTS = [(844, 640), (884, 700), (826, 760), (900, 820), (858, 880)]
STAR = (TREE_X, 506)


@functools.lru_cache(None)
def town_layers():
    """Минимализм: плоское небо-градиент, луна, звёзды, силуэты домов с окнами, ёлка из треугольников."""
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    sky = np.array(SKY0, np.float32) + (np.array(SKY1, np.float32) - np.array(SKY0, np.float32)) * np.clip(yy * 2.1, 0, 1)
    base = np.broadcast_to(sky, (H, W, 3)).copy()
    img = Image.fromarray(base.astype(np.uint8))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(8)
    for _ in range(40):                                      # звёзды
        x, y = rng.uniform(90, 990), rng.uniform(170, 560)
        r = rng.uniform(1.2, 2.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(235, 238, 255))
    d.ellipse((165, 245, 275, 355), fill=(250, 244, 214))   # луна
    d.ellipse((150, 230, 250, 330), fill=tuple(int(v) for v in sky[int(290)][0][0] * 0 + np.array(SKY0) * 0 + (0, 0, 0))) if False else None
    lab = Image.new('I', (W, H), 0)
    dl = ImageDraw.Draw(lab)
    houses = []
    x = 40
    while x < 1040:
        w_ = int(rng.uniform(105, 160))
        h_ = int(rng.uniform(120, 230))
        houses.append((x, SILL_Y - h_, x + w_, SILL_Y))
        x += w_ + int(rng.uniform(-6, 10))
    off_c, on_c = (40, 50, 104), (255, 204, 120)
    on_img = img.copy()
    don = ImageDraw.Draw(on_img)
    k = 0
    for j, (x0, y0, x1, y1) in enumerate(houses):
        col = (30, 38, 86) if j % 2 else (36, 45, 96)
        for dd in (d, don):
            dd.rectangle((x0, y0, x1, y1), fill=col)
            dd.polygon([(x0 - 8, y0), ((x0 + x1) / 2, y0 - 46), (x1 + 8, y0)], fill=col)
            dd.polygon([(x0 - 12, y0 + 2), ((x0 + x1) / 2, y0 - 50), (x1 + 12, y0 + 2), ((x0 + x1) / 2, y0 - 34)],
                       fill=(226, 234, 252))
        for wy in range(y0 + 26, y1 - 40, 54):
            for wx in range(x0 + 18, x1 - 30, 42):
                k += 1
                d.rectangle((wx, wy, wx + 20, wy + 26), fill=off_c)
                don.rectangle((wx, wy, wx + 20, wy + 26), fill=on_c)
                dl.rectangle((wx - 3, wy - 3, wx + 23, wy + 29), fill=k)
    # ёлка
    for dd in (d, don):
        for i, (top, half, bot) in enumerate(((520, 64, 680), (610, 96, 800), (710, 128, 920))):
            dd.polygon([(TREE_X, top), (TREE_X - half, bot), (TREE_X + half, bot)], fill=(24, 72, 84))
            dd.polygon([(TREE_X, top), (TREE_X - half, bot), (TREE_X - half + 18, bot - 6), (TREE_X, top + 16)],
                       fill=(228, 236, 252))
        dd.rectangle((TREE_X - 12, 918, TREE_X + 12, SILL_Y), fill=(60, 44, 50))
        for (ox, oy) in ORNAMENTS:
            dd.ellipse((ox - 15, oy - 15, ox + 15, oy + 15), fill=(196, 206, 228))
        sx, sy = STAR
        dd.polygon([(sx + 22 * math.cos(-math.pi / 2 + q * math.pi / 5) * (1 if q % 2 == 0 else 0.45),
                     sy + 22 * math.sin(-math.pi / 2 + q * math.pi / 5) * (1 if q % 2 == 0 else 0.45)) for q in range(10)],
                   fill=(214, 220, 236))
    full_off = np.array(img, np.float32)
    full_on = np.array(on_img, np.float32)
    labs = np.array(lab, np.int32)
    n = k + 1
    order = np.zeros(n, np.float32)
    ys, xs = np.nonzero(labs)
    sums = np.bincount(labs[ys, xs], weights=xs, minlength=n)
    cnt = np.bincount(labs[ys, xs], minlength=n) + 1e-6
    order = (sums / cnt) / W
    order[0] = 0
    order = (order - order[1:].min()) / max(1e-6, order[1:].max() - order[1:].min())
    order[0] = 0
    return full_on, full_off, labs, order, None


def orn_xy(j):
    return ORNAMENTS[j]


def lights_state(t):
    """Состояние окон городка: функция (порядок кластера) → 0..1."""
    ck = creepy_k(t)
    if E.SPREAD - 0.2 <= t < E.PRICE + 1.5:
        u0 = ease((t - (E.SPREAD - 0.2)) / 0.35)          # быстро гаснут
        def f(order):
            x = np.clip((t - (E.SPREAD + 0.6 + order * 3.2)) / 0.25, 0, 1)   # загораются цепочкой слева направо
            on = x * x * (3 - 2 * x)
            return (1 - u0) + u0 * on
        return f
    return lambda order: np.full_like(order, 1 - 0.92 * ck)


def town(t):
    on, off, labs, order, litm = town_layers()
    st = lights_state(t)(order)
    st[0] = 1.0
    k = st[labs][..., None]
    img = off + (on - off) * k
    # мерцание окон (кое-где свет «живой»)
    return img


def snowfall(cv, t, n=90, seed=7, y0=0, y1=1180, speed=(70, 150), alpha=0.85, scale=1.0, freeze=0.0):
    rng = np.random.default_rng(seed)
    xs = rng.uniform(0, W, n)
    ph = rng.uniform(0, 1, n)
    sp = rng.uniform(*speed, n)
    rs = rng.uniform(1.6, 4.6, n) * scale
    sw = rng.uniform(0.5, 1.6, n)
    tt = t * (1 - 0.85 * freeze)

    def draw(d, mp, S):
        span = y1 - y0 + 40
        for i in range(n):
            y = y0 - 20 + (ph[i] * span + tt * sp[i]) % span
            x = (xs[i] + 22 * math.sin(tt * sw[i] + ph[i] * 6)) % W
            X, Y = mp(x, y)
            r = rs[i] * S
            d.ellipse((X - r, Y - r, X + r, Y + r), fill=(255, 255, 255, int(200 * alpha)))
    fx.over(cv, fx.draw_rgba((0, y0, W, y1), draw))


def fireworks(cv, t):
    """Салют за окном в момент превращения."""
    for j, (t0, x, y, col) in enumerate(((E.FLASH - 0.05, 300, 330, (255, 214, 140)), (E.FLASH + 0.3, 760, 260, ICE),
                                         (E.FLASH + 0.65, 520, 420, (255, 240, 250)))):
        u = (t - t0) / 1.4
        if not 0 <= u < 1:
            continue
        rng = np.random.default_rng(j + 3)
        ang = rng.uniform(0, 2 * math.pi, 26)
        sp = rng.uniform(90, 170, 26)
        r_ = fx.ease_out(u)

        def draw(d, mp, S, ang=ang, sp=sp, r_=r_, u=u, x=x, y=y, col=col):
            for a_, s_ in zip(ang, sp):
                px, py = x + math.cos(a_) * s_ * r_, y + math.sin(a_) * s_ * r_ + 40 * u * u
                X, Y = mp(px, py)
                rr = (4.5 - 3 * u) * S
                d.ellipse((X - rr, Y - rr, X + rr, Y + rr), fill=col + (int(255 * (1 - u) ** 1.2),))
        fx.over(cv, fx.draw_rgba((x - 220, y - 220, x + 220, y + 260), draw))
        put(cv, radial(256, col), x, y, 1.6, 0.35 * (1 - u))


def aurora(cv, t, a):
    if a <= 0:
        return
    def draw(d, mp, S):
        for k, (col, yb) in enumerate((((90, 220, 210), 200), ((150, 120, 255), 260), ((120, 200, 255), 330))):
            pts = []
            for i in range(0, 41):
                x = i * W / 40
                y = yb + 50 * math.sin(i * 0.35 + t * 0.9 + k) + 25 * math.sin(i * 0.9 - t * 1.3)
                pts.append(mp(x, y))
            for j in range(len(pts) - 1):
                (x0, y0), (x1, y1) = pts[j], pts[j + 1]
                d.polygon([(x0, y0), (x1, y1), (x1, y1 + 120 * S), (x0, y0 + 120 * S)],
                          fill=col + (int(70 * a),))
    im = fx.draw_rgba((0, 100, W, 560), draw)
    fx.over(cv, im)


def tree_lights(cv, t):
    """Шары на ёлке за окном загораются: шапка, пряник, колокольчик — тёплым; носок — холодным, слабо."""
    seq = [(E.HAT + 0.5, WARM, 1.0), (E.COOKIE + 0.5, (255, 220, 160), 1.0), (E.BELL + 0.5, GOLD, 1.0),
           (E.STOCK + 0.5, ICE, 0.45), (E.TEASE + 0.3, (255, 250, 255), 1.0)]
    ck = creepy_k(t)
    for j, (t0, col, k) in enumerate(seq):
        a = appear(t, t0, 0.4) * k * (1 - 0.85 * ck)
        if a <= 0:
            continue
        x, y = orn_xy(j)
        tw = 0.85 + 0.15 * math.sin(t * 3 + j)
        put(cv, radial(128, col), x, y, 0.75 * tw, a)
        put(cv, radial(64, WHITE), x, y, 0.35, a * 0.8)
    # звезда на макушке — в финале
    a = appear(t, E.MOVE2 + 0.2, 0.5)
    if a > 0:
        x, y = STAR
        put(cv, radial(128, (255, 236, 170)), x, y, 1.1 + 0.15 * math.sin(t * 4), a)


# ------------------------------------------------------------------ комната (минимализм: рама-линии, подоконник, гирлянда)
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


GROUND_Y = 1490


@functools.lru_cache(None)
def window_layer():
    """Белая стена с бледными снежинками, окно-«картина» с голубой рамой, подоконник, снежный сугроб внизу."""
    S = 2
    im = Image.new('RGBA', (W * S, H * S), (250, 252, 255, 255))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(14)
    for _ in range(34):                                    # бледные снежинки на стене
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        x0, y0, x1, y1 = WIN_BOX
        if x0 - 30 < x < x1 + 30 and y0 - 30 < y < y1 + 40:
            continue
        snowflake(d, x * S, y * S, rng.uniform(18, 42) * S, (226, 234, 248, 255), int(3 * S))
    x0, y0, x1, y1 = WIN_BOX
    d.rounded_rectangle(((x0 - 10) * S, (y0 - 6) * S, (x1 + 10) * S, (y1 + 16) * S), 34 * S, fill=(214, 224, 244, 255))
    d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), 28 * S, fill=(0, 0, 0, 0))
    lw = 12
    col = (180, 198, 232, 255)
    d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), 28 * S, outline=col, width=lw * S)
    d.rectangle(((540 - lw / 2) * S, y0 * S, (540 + lw / 2) * S, y1 * S), fill=col)
    d.rectangle((x0 * S, (470 - lw / 2) * S, x1 * S, (470 + lw / 2) * S), fill=col)
    d.rounded_rectangle(((x0 - 34) * S, SILL_Y * S, (x1 + 34) * S, (SILL_Y + 30) * S), 12 * S, fill=(232, 238, 252, 255),
                        outline=(196, 210, 238, 255), width=3 * S)
    for k in range(34):                                    # снег на подоконнике
        x = rng.uniform(x0 - 20, x1 + 20)
        r = rng.uniform(9, 20)
        d.ellipse(((x - r) * S, (SILL_Y - r * 0.55) * S, (x + r) * S, (SILL_Y + r * 0.45) * S), fill=(255, 255, 255, 255),
                  outline=(214, 226, 248, 255), width=S)
    # сугроб: волнистый край, голубая тень снизу
    pts = [(0, H * S)]
    for i in range(0, 41):
        x = i * W / 40
        y = GROUND_Y + 26 * math.sin(i * 0.55) + 14 * math.sin(i * 1.3 + 1)
        pts.append((x * S, y * S))
    pts.append((W * S, H * S))
    d.polygon(pts, fill=(236, 243, 255, 255))
    d.line(pts[1:-1], fill=(196, 212, 242, 255), width=4 * S)
    for i in range(18):                                    # блёстки на снегу
        x, y = rng.uniform(0, W), rng.uniform(GROUND_Y + 50, H - 20)
        snowflake(d, x * S, y * S, rng.uniform(6, 12) * S, (206, 220, 248, 255), 2 * S)
    im = im.resize((W, H), Image.LANCZOS)
    out = np.array(im).astype(np.float32)
    out[..., 3] /= 255
    out[..., :3] *= out[..., 3:4]
    return out


@functools.lru_cache(None)
def garland_points():
    pts = []
    for i in range(17):
        x = 60 + i * 60
        y = 112 + 24 * math.sin(math.pi * ((x - 60) % 240) / 240)
        pts.append((x, y))
    return pts


def room(cv, t):
    wl = window_layer()
    cv[..., :3] = cv[..., :3] * (1 - wl[..., 3:4]) + wl[..., :3]
    ck = creepy_k(t)
    pts = garland_points()

    def wire(d, mp, S):
        d.line([mp(x, y) for x, y in pts], fill=(200, 210, 235, 255), width=int(3 * S))
        for j, (x, y) in enumerate(pts):
            X, Y = mp(x, y + 8)
            d.ellipse((X - 7 * S, Y - 9 * S, X + 7 * S, Y + 9 * S), fill=(255, 214, 130, 255) if j % 2 else (190, 220, 255, 255))
    fx.over(cv, fx.draw_rgba((0, 80, W, 160), wire))
    for j, (x, y) in enumerate(pts):
        tw = 0.55 + 0.45 * math.sin(t * 2.6 + j * 1.7) ** 2
        put(cv, radial(64, WARM if j % 2 else ICE), x, y + 8, 0.7, tw * 0.8 * (1 - 0.8 * ck))


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
    y = 990
    ck = creepy_k(t)
    put(cv, string, 540, y + 12, 1.0, 1.0)
    for j, (p, dx) in enumerate(parts):
        if abs(dx) < 120:                # за Митой носок не виден — не рисуем
            continue
        amp = 0.05 * (1 - ck)
        rot = amp * math.sin(t * 1.4 + j * 1.1)
        sad = 0.0
        if j == 3:                      # голубой носок — «его никто не берёт»: никнет и тускнеет
            sad = appear(t, E.STOCK_NOBODY, 0.6) * (1 - appear(t, E.CREEPY_END + 0.5, 0.6))
            rot += 0.12 * sad
        put(cv, p, 540 + dx, y + 6, 1.0, 1.0 - 0.35 * sad, rot, anchor=(p.width / 2, 8))
        if j == 3 and sad > 0:
            put(cv, radial(128, ICE), 540 + dx, y + 150, 1.2, 0.25 * sad)


def easter_egg(cv, t):
    """Пасхалка: снеговик с синими хвостиками (как у Миты) в углу, иногда машет."""
    im = keyed('snowman', h=250)
    wave_ = 0.06 * math.sin(t * 2.2) * (1 - creepy_k(t))
    put(cv, im, 978, 1835, 1.0, 1.0, wave_, anchor=(im.width / 2, im.height))


def mita_shadow(cv, x, y):
    def draw(d, mp, S):
        X, Y = mp(x, y + 2)
        d.ellipse([X - 160 * S, Y - 20 * S, X + 160 * S, Y + 20 * S], fill=(20, 30, 70, 60))
    fx.over(cv, fx.draw_rgba((x - 180, y - 30, x + 180, y + 30), draw))


def background(t):
    cv = np.zeros((H, W, 4), np.float32)
    cv[..., :3] = town(t)
    ck = creepy_k(t)
    put(cv, radial(256, (250, 240, 200)), 220, 300, 1.1, 0.3 * (1 - 0.7 * ck))
    aurora(cv, t, appear(t, E.MOVE2, 1.0))
    fireworks(cv, t)
    tree_lights(cv, t)
    snowfall(cv, t, 50, 7, 150, 940, (45, 90), 0.6, 0.8, ck)
    snowfall(cv, t, 26, 11, 150, 940, (90, 160), 0.85, 1.2, ck)
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


def thermo(cv, cx, cy, h, level, col, a=1.0, frost=0.0):
    """level 0..THERMO_MAX (TON). Жидкость рисуется внутри трубки; frost — иней на трубке (подешевел)."""
    im, box, s = thermo_img(h)
    x0 = cx - im.width / 2
    y0 = cy - h / 2
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
    if frost > 0:
        put(cv, radial(128, ICE), cx, (ytop + by) / 2, 1.6, a * frost * 0.45)
    return ytop


# ------------------------------------------------------------------ сцена подарков (шапка, пряник, колокольчик, носок)
GIFTS = [  # ключ, начало, цена, цвет жидкости, подпись, комментарий (время, текст), иней
    ('hat', E.HAT, 9.0, RED, 'ШАПКА САНТЫ', (E.HAT_PAPA, 'ПАПЕ — НА ПРАЗДНИК'), 0.0, '↑ ДОРОЖАЕТ'),
    ('cookie', E.COOKIE, 6.0, (236, 160, 80), 'ПРЯНИК', (E.COOKIE_MAMA, 'МАМЕ К ЧАЮ'), 0.0, '= БЕЗ ИЗМЕНЕНИЙ'),
    ('bell', E.BELL, 13.0, GOLD, 'КОЛОКОЛЬЧИК', (E.BELL_FRIEND, 'ПОДРУГЕ… ИЛИ СЕБЕ'), 0.0, 'САМЫЙ ДОРОГОЙ'),
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
    if not (E.HAT - 0.1 <= t < GIFT_END + 0.4):
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
    ta = appear(t, E.HAT - 0.05, 0.4) * a_all
    thermo(cv, 150, 960, THERMO_H, lv, c, ta, frost * u)
    put(cv, pill(f'{price:g} TON', (40, 52, 104), 40), 150, 600 + 6 * math.sin(t * 2), pop(t, t0 + 0.3), ta)
    put(cv, pill(tag, (230, 80, 70) if j in (0, 2) else (90, 130, 200) if j == 3 else (130, 110, 90), 26),
        215, 1310, pop(t, t0 + 0.9), ta * appear(t, t0 + 0.9))
    # подарок — «ёлочная игрушка» на нитке справа, качается
    ga = appear(t, t0, 0.3) * a_all
    sw = 0.08 * math.sin(t * 1.7)
    gx, gy = 850 + 120 * math.sin(sw), 470
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
    fx.over(cv, fx.draw_rgba((600, 40, 1080, gy), string), ga)
    put(cv, radial(256, WARM if key != 'stock' else ICE), gx, gy, 1.7, 0.35 * ga)
    p = pop(t, t0, 0.5)
    put(cv, im, gx, gy, p, ga, sw * 0.6)
    put(cv, pill(name, (60, 76, 140), 32), gx, gy + size * 0.52, pop(t, t0 + 0.2), ga)
    # комментарий Миты зрителю
    ca = appear(t, tc, 0.3) * a_all * (1 - appear(t, (GIFTS[j + 1][1] if j + 1 < len(GIFTS) else GIFT_END) - 0.3, 0.3))
    if ca > 0:
        put(cv, pill(comment, (196, 128, 70) if key != 'stock' else (80, 110, 170), 26), 810, 712 + 6 * math.sin(t * 2.4),
            pop(t, tc, 0.45), ca, -0.04)
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
    put(cv, fog_patch(), FOG_X, FOG_Y, 0.6 + 0.15 * ease((t - t0 - 0.5) / 1.4), fa * 0.8)
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
def frost_tex():
    """Иней: дымка у краёв + веточки-«папоротники», растущие от краёв внутрь."""
    rng = np.random.default_rng(31)
    base = np.zeros((H // 8, W // 8), np.float32)
    for k, sc in enumerate((5, 11, 23)):
        n = rng.random((max(2, sc * 16 // 9), sc)).astype(np.float32)
        base += cv2.resize(n, (W // 8, H // 8), interpolation=cv2.INTER_CUBIC) * (0.6 ** k)
    base = (base - base.min()) / (base.max() - base.min())
    base = cv2.resize(base, (W, H), interpolation=cv2.INTER_CUBIC)
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    edge = np.minimum(np.minimum(xx, W - xx) / W, np.minimum(yy, H - yy) / H * 0.9) + (base - 0.5) * 0.035
    ferns = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(ferns)

    def branch(x, y, ang, ln, depth):
        if depth == 0 or ln < 6:
            return
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        d.line((x, y, x2, y2), fill=200 - 30 * (4 - depth), width=max(1, depth - 1))
        for side in (-1, 1):
            branch(x + (x2 - x) * 0.5, y + (y2 - y) * 0.5, ang + side * rng.uniform(0.6, 1.0), ln * 0.45, depth - 1)
        branch(x2, y2, ang + rng.uniform(-0.25, 0.25), ln * 0.7, depth - 1)
    for i in range(170):
        side = rng.integers(4)
        if side == 0:
            x, y, ang = rng.uniform(0, W), 0, math.pi / 2
        elif side == 1:
            x, y, ang = rng.uniform(0, W), H, -math.pi / 2
        elif side == 2:
            x, y, ang = 0, rng.uniform(0, H), 0.0
        else:
            x, y, ang = W, rng.uniform(0, H), math.pi
        branch(x, y, ang + rng.uniform(-0.6, 0.6), rng.uniform(60, 150), 4)
    ferns = cv2.GaussianBlur(np.array(ferns, np.float32) / 255, (0, 0), 0.8)
    return edge, ferns


def frost(cv, t, k):
    """Иней ползёт от краёв экрана к центру (кромка неровная, с веточками)."""
    if k <= 0:
        return
    edge, ferns = frost_tex()
    reach = 0.02 + 0.10 * k
    m = np.clip((reach - edge) / 0.045, 0, 1)
    m = np.clip(m * 0.5 + ferns * np.clip((reach * 1.6 - edge) / 0.05, 0, 1) * 0.9, 0, 0.92)
    col = np.array([228, 242, 255], np.float32)
    cv[..., :3] = cv[..., :3] * (1 - m[..., None]) + col * m[..., None]


@functools.lru_cache(None)
def vignette():
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.6)) ** 2)
    return np.clip(r - 0.35, 0, 1)[..., None]


def creepy_room(cv, t, k):
    if k <= 0:
        return
    tint = np.array([0.42, 0.5, 0.78], np.float32)
    cv[..., :3] *= (1 - k) + k * tint
    cv[..., :3] *= 1 - 0.75 * k * vignette()
    # отпечаток ладони на стекле (снаружи)
    ha = appear(t, E.HANDPRINT, 1.4) * k
    if ha > 0:
        im = keyed('handprint', h=380)
        arr = np.array(im).astype(np.float32)
        lum = arr[..., :3].mean(-1, keepdims=True)
        arr[..., :3] = np.clip(lum * np.array([0.82, 0.93, 1.08]) + np.array([10, 20, 40]), 0, 255)
        put(cv, Image.fromarray(arr.astype(np.uint8)), 300, 330, 0.92 + 0.08 * ha, ha * 0.9, -0.12)


def ice_particles(cv, t, k):
    if k <= 0:
        return
    def draw(d, mp, S):
        rng = np.random.default_rng(9)
        for i in range(60):
            x = rng.uniform(0, W)
            y = (rng.uniform(0, H) - t * rng.uniform(10, 30)) % H
            X, Y = mp(x + 10 * math.sin(t + i), y)
            r = rng.uniform(1.5, 3.5) * S
            d.ellipse((X - r, Y - r, X + r, Y + r), fill=(220, 240, 255, int(200 * k)))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), draw))


def ice_burst(cv, t):
    """Выход из жути: ледяная статуя разлетается осколками + вспышка."""
    u = (t - E.CREEPY_END) / 0.9
    if not 0 <= u < 1:
        return
    rng = np.random.default_rng(12)

    def draw(d, mp, S):
        for i in range(46):
            ang = rng.uniform(0, 2 * math.pi)
            sp = rng.uniform(250, 700)
            x0, y0 = 540 + rng.uniform(-120, 120), 1150 + rng.uniform(-380, 380)
            x = x0 + math.cos(ang) * sp * fx.ease_out(u)
            y = y0 + math.sin(ang) * sp * fx.ease_out(u) + 500 * u * u
            X, Y = mp(x, y)
            r = rng.uniform(8, 20) * S
            rot = ang + u * 6
            pts = [(X + r * math.cos(rot + q * 2.1), Y + r * math.sin(rot + q * 2.1) * 0.7) for q in range(3)]
            d.polygon(pts, fill=(205, 235, 255, int(240 * (1 - u))), outline=(255, 255, 255, int(255 * (1 - u))))
    fx.over(cv, fx.draw_rgba((0, 200, W, H), draw))
    if u < 0.3:
        cv[..., :3] += (255 - cv[..., :3]) * (0.55 * (1 - u / 0.3))


# ------------------------------------------------------------------ хук: силуэт перчаток со знаком вопроса
def scene_hook(cv, t):
    # прошлогодние подарки — маленькие игрушки на гирлянде (хук: «помнишь?»)
    for j, key in enumerate(('hat', 'cookie', 'bell', 'stock')):
        tj = 0.35 + 0.25 * j
        aj = appear(t, tj, 0.4) * (1 - appear(t, E.BOX_IN + 0.3, 0.4))
        if aj <= 0:
            continue
        x = 140 + j * 120 if j < 2 else 140 + j * 120
        y = 300 + 30 * (j % 2) + 6 * math.sin(t * 2 + j)
        gi = gift_frame(key, t, 256, j * 0.4).resize((130, 130), Image.LANCZOS)
        put(cv, gi, x, y, pop(t, tj, 0.45), aj * (1 - 0.0))
    a = appear(t, E.GLOVES_Q, 0.35) * (1 - appear(t, E.BOX_IN + 0.3, 0.4))
    if a <= 0:
        return
    im = gift_frame('mitt', t, 512).resize((300, 300), Image.LANCZOS)
    arr = np.array(im).astype(np.float32)
    k = 1 - ease((t - E.GLOVES_Q - 1.2) / 1.0) * 0.35       # силуэт: почти чёрный, к концу проступает цвет
    arr[..., :3] *= (1 - 0.9 * k)
    arr[..., :3] += np.array([30, 40, 90]) * 0.9 * k
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    x, y = 820, 470 + 12 * math.sin(t * 2)
    put(cv, radial(256, ICE), x, y, 1.9, 0.45 * a)
    put(cv, im, x, y, pop(t, E.GLOVES_Q, 0.5), a, 0.05 * math.sin(t * 3))
    put(cv, utext('?', 150, 'ExtraBold', WHITE, 6, (60, 90, 170)), x + 120, y - 120, pop(t, E.GLOVES_Q + 0.25),
        a, 0.15 + 0.08 * math.sin(t * 4))
    put(cv, pill('ПЕРЕПОЛОХ!', (60, 90, 170), 28), x - 10, y + 210, pop(t, E.GLOVES_Q + 1.5), a)


# ------------------------------------------------------------------ коробка: «пуф» при появлении/исчезновении
def poof(cv, t, t0, x, y, n=22, col=(255, 255, 255), spread=180):
    u = (t - t0) / 0.6
    if not 0 <= u < 1:
        return
    rng = np.random.default_rng(int(t0 * 10))

    def draw(d, mp, S):
        for i in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            r0 = rng.uniform(0.3, 1.0) * spread
            X, Y = mp(x + math.cos(ang) * r0 * fx.ease_out(u), y + math.sin(ang) * r0 * fx.ease_out(u) * 0.8)
            r = rng.uniform(5, 12) * (1 - u) * S
            fx.sparkle(d, X, Y, r * 1.6, col + (int(255 * (1 - u)),))
    fx.over(cv, fx.draw_rgba((x - spread - 40, y - spread - 40, x + spread + 40, y + spread + 40), draw))
    put(cv, radial(256, col), x, y, 1.2 * (0.5 + u), 0.5 * (1 - u))


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
        put(cv, gi, x, y, pop(t, E.CREEPY_END + 0.2 + 0.1 * j) * (1 - 0.15 * jump), a * (1 - 0.3 * jump))
    ta = appear(t, E.TEASE, 0.3)
    if ta > 0:
        y = 380 - 120 * fx.ease_out_back(fx.clamp01((t - E.TEASE_JUMP) / 0.6)) + 10 * math.sin(t * 3)
        sh = 0.12 * math.sin(t * 26) * jump * (1 - ease((t - E.TEASE_JUMP - 0.8) / 0.4))
        put(cv, radial(256, (255, 236, 170)), 540, y, 2.0 + 0.5 * jump, 0.45 * ta)
        im = gift_frame('mitt', t, 512).resize((260, 260), Image.LANCZOS)
        put(cv, im, 540, y, pop(t, E.TEASE, 0.5) * (1 + 0.25 * jump), ta, sh)
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
    sx = abs(math.cos(math.pi * flip))
    post = flip >= 0.5
    deleted = t >= E.RUMOR_DEL + 0.6
    tilt = -0.04
    if not post:
        put(cv, card_base(True), cx, cy, 1.0, a, tilt)
        gi = gift_frame('mitt', t, 512).resize((280, 280), Image.LANCZOS)
        put(cv, gi, cx, cy - 20 + 25 * abs(math.sin(t * 3.2)), sx, a, tilt)
        put(cv, utext('СЛИВ?!', 52, 'ExtraBold', WHITE, 4, RED), cx, cy - 290, sx * pop(t, E.RUMOR_VIDEO + 0.2), a, tilt)
        for k in range(3):                                       # кнопки справа: сердце, коммент, «поделиться»
            put(cv, radial(64, WHITE), cx + 170, cy + 80 + k * 90, 0.5 * sx, a * 0.9)
        prog = ((t - E.MOVE1) / 3.0) % 1
        put(cv, fx.rounded(int(360 * prog) + 4, 10, 5, (255, 80, 110, 255)), cx - 180 + 180 * prog, cy + 330, sx, a)
        put(cv, utext('▶', 70, 'ExtraBold', WHITE), cx - 150, cy + 250, sx, a * 0.8)
    elif not deleted:
        put(cv, card_base(False), cx, cy, 1.0, a, tilt)
        put(cv, radial(64, (90, 120, 200)), cx - 150, cy - 300, 1.0 * sx, a)
        put(cv, utext('КАНАЛ', 30, 'ExtraBold', INK), cx - 40, cy - 300, sx, a, tilt)
        for k in range(4):
            put(cv, fx.rounded(300 - 50 * (k % 2), 22, 11, (190, 196, 220, 255)), cx - 10, cy - 200 + k * 46, sx,
                a * 0.95, tilt)
        gi = gift_frame('mitt', t, 512).resize((230, 230), Image.LANCZOS)
        put(cv, gi, cx, cy + 90, sx, a, tilt)
        put(cv, utext('ЗИМНИЙ КРАФТ?', 34, 'ExtraBold', (60, 90, 170)), cx, cy + 260, sx, a, tilt)
        # «пара минут»: таймер тает
        k = fx.clamp01((t - E.RUMOR_POST) / max(0.5, E.RUMOR_DEL - E.RUMOR_POST))
        put(cv, fx.rounded(int(300 * (1 - k)) + 6, 12, 6, (232, 70, 64, 255)), cx, cy + 330, 1.0, a, tilt)
        # удаление: пост рассыпается снежинками
        if t >= E.RUMOR_DEL:
            poof(cv, t, E.RUMOR_DEL, cx, cy, 30, (230, 240, 255), 260)
    if deleted:
        da = appear(t, E.RUMOR_DEL + 0.6, 0.3)
        put(cv, pill('ПОСТ УДАЛЁН', (110, 116, 140), 34), cx, cy - 20, pop(t, E.RUMOR_DEL + 0.6), a * da, tilt)
        put(cv, utext('×', 120, 'ExtraBold', (232, 70, 64), 6, WHITE), cx, cy - 170, pop(t, E.RUMOR_DEL + 0.7), a * da)


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
    for k, (s_, w0) in enumerate((('БЛОГЕРЫ', 'блогеры'), ('КАНАЛЫ', 'каналы'), ('ЧАТЫ', 'чаты'))):
        t0 = E.at(w0, 0, ON[10]) - 0.1
        y = 1010 + k * 110
        put(cv, pill(s_, (40, 52, 104), 40), 800, y, pop(t, t0), a * appear(t, t0, 0.2))


def scene_price(cv, t):
    if not (E.PRICE <= t < E.TRUTH + 0.4):
        return
    a = appear(t, E.PRICE + 0.1, 0.35) * (1 - appear(t, E.TRUTH - 0.1, 0.4))
    up = ease((t - E.PRICE_NOW) / 1.3)
    lv = 3.5 + (10 - 3.5) * up
    col = tuple(int(v) for v in np.array((110, 170, 240)) + (np.array(RED) - np.array((110, 170, 240))) * up)
    thermo(cv, 880, 1040, 760, lv, col, a, (1 - up) * appear(t, E.PRICE_THEN, 0.3))
    gi = gift_frame('mitt', t, 512).resize((230, 230), Image.LANCZOS)
    put(cv, radial(256, WARM), 880, 470, 1.6, 0.4 * a)
    put(cv, gi, 880, 470 + 10 * math.sin(t * 2), pop(t, E.PRICE + 0.1), a)
    put(cv, pill('ТОГДА: 3–4 TON', (80, 110, 170), 34), 520, 560, pop(t, E.PRICE_THEN), a * appear(t, E.PRICE_THEN, 0.2))
    put(cv, pill('СЕЙЧАС: 10 TON', (232, 70, 64), 38), 540, 650, pop(t, E.PRICE_NOW + 0.4),
        a * appear(t, E.PRICE_NOW + 0.4, 0.2))
    if t >= E.PRICE_X2:
        put(cv, utext('×2+', 130, 'ExtraBold', (255, 230, 120), 7, (150, 40, 40)), 660, 880,
            pop(t, E.PRICE_X2, 0.5), a, -0.12)


def scene_truth(cv, t):
    if not (E.TRUTH <= t < E.MOVE2 + 0.4):
        return
    a = appear(t, E.TRUTH + 0.1, 0.35) * (1 - appear(t, E.MOVE2, 0.4))
    put(cv, radial(256, ICE), 820, 620, 2.2, 0.45 * a)
    put(cv, utext('?', 300, 'ExtraBold', (235, 245, 255), 10, (90, 140, 210)), 820, 620 + 14 * math.sin(t * 2),
        pop(t, E.TRUTH + 0.1, 0.5), a, 0.08 * math.sin(t * 1.5))
    put(cv, pill('НИКТО НЕ ЗНАЕТ', (60, 76, 140), 28), 820, 850, pop(t, E.TRUTH + 1.0), a * appear(t, E.TRUTH + 1.0, 0.2))
    put(cv, pill('СКОРЕЕ ВСЕГО — СЛУХ', (110, 116, 140), 26), 820, 940, pop(t, E.TRUTH_NO),
        a * appear(t, E.TRUTH_NO, 0.2), -0.05)
    k = ease((t - E.TRUTH_MARKET) / 1.0)
    if k > 0:
        def chart(d, mp, S):
            pts = [(640, 1250), (700, 1230), (760, 1238), (820, 1180), (880, 1150), (940, 1070), (1000, 1010)]
            n = 1 + int(k * (len(pts) - 1))
            q = [mp(*p) for p in pts[:n + 1]]
            if len(q) > 1:
                d.line(q, fill=(232, 70, 64, 255), width=int(9 * S), joint='curve')
            X, Y = q[-1]
            d.ellipse((X - 11 * S, Y - 11 * S, X + 11 * S, Y + 11 * S), fill=(255, 255, 255, 255))
        put(cv, fx.rounded(440, 320, 30, (246, 248, 255, 235), (255, 255, 255, 255), 4), 820, 1150, pop(t, E.TRUTH_MARKET),
            a)
        fx.over(cv, fx.draw_rgba((600, 980, 1040, 1290), chart), a)
        put(cv, pill('РЫНОК ПОВЕРИЛ', (232, 70, 64), 26), 820, 1340, pop(t, E.TRUTH_MARKET + 0.4),
            a * appear(t, E.TRUTH_MARKET + 0.4, 0.2))


# ------------------------------------------------------------------ финал: варежки «Верю / Не верю»
@functools.lru_cache(None)
def mitten(side):
    im = Image.open(KEYED / 'mittens.png').convert('RGBA')
    im = im.crop((0, 280, 506, 1100) if side == 0 else (510, 280, 1024, 1100))
    arr = np.array(im).astype(np.float32)
    arr[..., 3] = np.where(arr[..., 3] < 200, arr[..., 3] * 0.0, arr[..., 3])   # срезаем ореол (смешался с зелёным)
    im = Image.fromarray(arr.astype(np.uint8))
    im = im.crop(im.getchannel('A').getbbox())
    return im.resize((270, round(im.height * 270 / im.width)), Image.LANCZOS)


def scene_choice(cv, t):
    if t < E.MOVE2 + 0.2:
        return
    lt = t - E.MOVE2
    for side, (x, word, col, glow, t_on) in enumerate(((175, 'ВЕРЮ', CARAMEL, WARM, 0.5), (905, 'НЕ ВЕРЮ', (80, 120, 190),
                                                                                         ICE, 2.2))):
        a = appear(lt, t_on - 0.3, 0.4)
        if a <= 0:
            continue
        hl = 0.5 + 0.5 * math.sin((lt - t_on) * 4) if lt > t_on else 0
        y = 1010 + 10 * math.sin(t * 2 + side)
        put(cv, radial(256, glow), x, y, 1.8, a * (0.35 + 0.25 * hl))
        im = mitten(side)
        put(cv, im, x, y, pop(lt, t_on - 0.3, 0.5) * (1 + 0.04 * hl), a, (-0.08 if side == 0 else 0.08))
        put(cv, utext(word, 30 if side == 0 else 26, 'ExtraBold', WHITE, 3, INK), x + (10 if side == 0 else -12), y - 25,
            pop(lt, t_on - 0.1, 0.5), a, (-0.08 if side == 0 else 0.08))
    put(cv, pill('ПИШИ В КОММЕНТАРИЯХ!', (196, 128, 70), 28), 540, 470, pop(t, E.CHOICE + 0.3), appear(t, E.CHOICE + 0.3, 0.2))


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
    if ck > 0:
        creepy_room(cv, t, ck)
        frost(cv, t, ck * ease((t - E.CREEPY) / 4.5) if t < E.CREEPY_END else ck)
        ice_particles(cv, t, ck)
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
    img = globe_shake(img, t)
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
