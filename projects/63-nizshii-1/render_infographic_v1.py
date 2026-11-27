"""«Низший» 1/1 — пробный фрагмент. Тёмная кинематографичная инфографика (референс автора 2026-11-24):
глубокий тёмно-синий фон, один крупный неоновый образ на мысль, медленный наезд камеры, мягкие переходы размытием,
крупные субтитры Oswald по центру с акцентным словом, мелкий системный HUD сверху. Кадр — чистая функция времени.

    python -B projects/63-nizshii-1/render.py --frames 1.0,5.0,10.5,18.0     # пробные кадры
    python -B engine/tools/build.py projects/63-nizshii-1 --approved --name nizshii_1_test_v1
"""
import functools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
import banner  # noqa: E402
import frames  # noqa: E402
from timeline_test import S, E, DUR, CAPS, SC2, SC3, STAMP  # noqa: E402
from events_test import AD_STOPS, OK, BEATS, MEMORY_DRAIN, NAME_GLITCH, FACE_GLITCH, HEY  # noqa: E402

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks(AD_STOPS, cy=H / 2)
F = HERE / 'fonts'

BG0, BG1 = (5, 8, 15), (13, 23, 41)
BLUE = (88, 172, 236)
GREEN = (92, 255, 152)
RED = (238, 66, 58)
WHITE = (238, 242, 247)
DIM = (112, 132, 160)
OLD = (196, 184, 160)        # старческие конечности


# ------------------------------------------------------------------ утилиты
def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(x):
    x = cl(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return cl((t - a) / (b - a)) if b > a else float(t >= a)


@functools.lru_cache(None)
def font(name, size):
    return ImageFont.truetype(str(F / name), size)


def cap_font(size):
    return font('Oswald-700.ttf', size)


def mono(size, bold=False):
    return font('JetBrainsMono-Bold.ttf' if bold else 'JetBrainsMono-Medium.ttf', size)


def glow(img, r=14, k=2):
    """RGBA спрайт со свечением: размытая копия под оригиналом."""
    g = img.filter(ImageFilter.GaussianBlur(r))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    for _ in range(k):
        out.alpha_composite(g)
    out.alpha_composite(img)
    return out


def alpha(img, a):
    if a >= 0.999:
        return img
    im = img.copy()
    im.putalpha(im.getchannel('A').point(lambda v: int(v * cl(a))))
    return im


def put(base, spr, cx, cy, a=1.0, scale=1.0):
    if a <= 0.003:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    spr = alpha(spr, a)
    base.alpha_composite(spr, (int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))))


def text_spr(text, fnt, fill, pad=30, shadow=0.0):
    box = fnt.getbbox(text)
    w, h = box[2] - box[0] + pad * 2, box[3] - box[1] + pad * 2
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - box[0], pad - box[1] + 4), text, font=fnt, fill=(0, 0, 0, int(255 * shadow)))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d.text((pad - box[0], pad - box[1]), text, font=fnt, fill=fill)
    return im


def hash01(*a):
    return (math.sin(sum(v * (12.9898 + 7.1 * i) for i, v in enumerate(a)) * 43758.5453) % 1 + 1) % 1


# ------------------------------------------------------------------ фон
@functools.lru_cache(None)
def background():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    yy = np.linspace(-1, 1, H)[:, None] * 1.55
    base = np.array(BG0)[None, None] * (1 - y[..., None]) * 0.4 + np.array(BG1)[None, None] * (0.6 + 0.4 * y[..., None])
    r = np.sqrt(x ** 2 + (yy + 0.15) ** 2)
    glow_c = np.exp(-r ** 2 / 0.35)[..., None] * np.array([10, 28, 52])[None, None]
    vig = np.clip(1 - 0.75 * (r / 1.6) ** 2.2, 0.15, 1)[..., None]
    img = np.clip((base + glow_c) * vig, 0, 255).astype(np.uint8)
    return Image.fromarray(img, 'RGB').convert('RGBA')


def dust(im, t, n=70, col=(140, 180, 230)):
    d = ImageDraw.Draw(im)
    for i in range(n):
        x0, y0, sp, sz = hash01(i, 1) * W, hash01(i, 2) * H, 8 + hash01(i, 3) * 22, 1 + hash01(i, 4) * 2.4
        y = (y0 - t * sp) % H
        x = x0 + math.sin(t * 0.3 + i) * 12
        a = int(40 + 80 * hash01(i, 5) * (0.6 + 0.4 * math.sin(t * 1.3 + i)))
        d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=col + (a,))


# ------------------------------------------------------------------ сцена 1: тело собирают
HX, HY, HR = 540, 700, 74
TORSO = [(418, 800), (662, 800), (690, 840), (640, 1110), (650, 1200), (430, 1200), (440, 1110), (390, 840)]
ARMS = [[(400, 830), (352, 1010), (338, 1190)], [(680, 830), (728, 1010), (742, 1190)]]
LEGS = [[(470, 1200), (462, 1380), (456, 1540)], [(610, 1200), (618, 1380), (624, 1540)]]
SEAMS = [(400, 830), (680, 830), (470, 1200), (610, 1200)]


@functools.lru_cache(None)
def body_mask():
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    d.polygon(TORSO, fill=255)
    d.ellipse((HX - HR, HY - HR, HX + HR, HY + HR), fill=255)
    d.rectangle((HX - 26, HY + HR - 10, HX + 26, 805), fill=255)
    return m


@functools.lru_cache(None)
def torso_spr():
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(TORSO, outline=BLUE + (255,), width=6)
    d.ellipse((HX - HR, HY - HR, HX + HR, HY + HR), outline=BLUE + (255,), width=6)
    d.line([(HX - 26, HY + HR - 4), (HX - 26, 800)], fill=BLUE + (255,), width=6)
    d.line([(HX + 26, HY + HR - 4), (HX + 26, 800)], fill=BLUE + (255,), width=6)
    # мышцы торса: еле заметные линии пресса
    for k in range(3):
        y = 960 + k * 55
        d.line([(500, y), (580, y)], fill=BLUE + (90,), width=3)
    d.line([(540, 880), (540, 1130)], fill=BLUE + (70,), width=3)
    return glow(im, 12, 2)


@functools.lru_cache(None)
def limb_spr(kind, i):
    pts = (ARMS if kind == 'arm' else LEGS)[i]
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line(pts, fill=OLD + (255,), width=16, joint='curve')
    d.line(pts, fill=(30, 34, 44, 255), width=8, joint='curve')
    for x, y in pts:
        d.ellipse((x - 9, y - 9, x + 9, y + 9), outline=OLD + (255,), width=4)
    if kind == 'arm' and i == 0:                       # раздутый больной локоть
        x, y = pts[1]
        d.ellipse((x - 22, y - 22, x + 22, y + 22), outline=(214, 92, 120, 255), width=6)
    return glow(im, 8, 1)


def water(t):
    lvl = eio(ramp(t, S['S1'] + 0.1, OK['S1'] + 0.6))
    if lvl <= 0:
        return None
    top, bot = 610, 1205
    y = bot - (bot - top) * lvl
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    wave = [(x, y + 7 * math.sin(x / 38 + t * 5)) for x in range(360, 721, 12)]
    yi = int(y)
    for yy in range(max(0, yi - 10), bot + 10, 3):          # градиент без перекрытий: ярче у поверхности
        k = cl((yy - y) / max(1.0, bot - y))
        d.rectangle((360, yy, 720, yy + 2), fill=(int(80 - 40 * k), int(175 - 75 * k), 255, int(205 - 85 * k)))
    d.polygon(wave + [(720, yi - 12), (360, yi - 12)], fill=(0, 0, 0, 0))   # над волной пусто
    d.line(wave, fill=(170, 225, 255, 255), width=5)
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    out.paste(layer, (0, 0), Image.composite(layer.getchannel('A'), Image.new('L', (W, H), 0), body_mask()))
    return glow(out, 10, 1)


def ecg_value(tau):
    v = 0.0
    for b in BEATS:
        x = tau - b
        v += -0.25 * math.exp(-((x + 0.06) / 0.02) ** 2) + 1.0 * math.exp(-(x / 0.014) ** 2) \
            - 0.45 * math.exp(-((x - 0.035) / 0.015) ** 2) + 0.22 * math.exp(-((x - 0.2) / 0.05) ** 2)
    return v


def ecg(im, t, a):
    if a <= 0:
        return
    x0, x1, y0 = 150, 930, 1650
    span = 1.6
    lay = Image.new('RGBA', (W, 240), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cur = x0 + (x1 - x0) * (((t - S['S3']) / span) % 1.0) if t > S['S3'] else x0
    pts = []
    for x in range(x0, x1 + 1, 4):
        dt = (cur - x) / (x1 - x0) * span
        if dt < 0:
            dt += span
        tau = t - dt
        pts.append((x, 120 - 95 * ecg_value(tau)))
    d.line([(x0, 120), (x1, 120)], fill=GREEN + (40,), width=2)
    d.line(pts, fill=GREEN + (255,), width=4, joint='curve')
    d.ellipse((cur - 7, pts[min(len(pts) - 1, (int(cur) - x0) // 4)][1] - 7, cur + 7,
               pts[min(len(pts) - 1, (int(cur) - x0) // 4)][1] + 7), fill=(220, 255, 230, 255))
    lay = glow(lay, 9, 2)
    put(im, lay, W / 2, y0, a)


def system_lines(im, t):
    rows = [('S1', 'ГИДРАЦИЯ'), ('S2', 'КОМПЛЕКТАЦИЯ'), ('S3', 'РЕАНИМАЦИЯ')]
    f = mono(40, True)
    for k, (key, word) in enumerate(rows):
        t0 = S[key] - 0.05
        if t < t0:
            continue
        y = 300 + k * 78
        n = int(len(word) * ramp(t, t0, t0 + 0.45))
        dots = '.' * int(10 * ramp(t, t0 + 0.4, OK[key]))
        txt = '> ' + word[:n] + (' ' + dots if n == len(word) else '')
        cur = '_' if (t * 3) % 1 < 0.5 and t < OK[key] else ''
        ImageDraw.Draw(im).text((110, y), txt + cur, font=f, fill=GREEN + (230,))
        if t >= OK[key]:
            u = t - OK[key]
            spr = text_spr('УСПЕШНО', f, GREEN + (255,), pad=18)
            spr = glow(spr, 8, 1 if u > 0.25 else 3)
            put(im, spr, 840, y + 24, eo(u / 0.15), 1 + 0.25 * (1 - eo(u / 0.2)))


def scene1(t):
    im = background().copy()
    dust(im, t)
    # тело
    a_body = eo(ramp(t, 0.15, 0.9))
    w = water(t)
    if w:
        im.alpha_composite(w)
    pulse = sum(math.exp(-((t - b) / 0.12) ** 2) for b in BEATS)
    put(im, torso_spr(), W / 2, H / 2, a_body * (0.8 + 0.2 * min(1, pulse)))
    if pulse > 0.02:
        heart = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
        ImageDraw.Draw(heart).ellipse((110, 110, 190, 190), fill=RED + (255,))
        put(im, glow(heart, 30, 3), 575, 880, min(1, pulse) * 0.9)
    # конечности въезжают по очереди
    limbs = [('arm', 0, -140, 0), ('arm', 1, 140, 0), ('leg', 0, -60, 140), ('leg', 1, 60, 140)]
    for j, (kind, i, dx, dy) in enumerate(limbs):
        u = eo(ramp(t, S['S2'] + 0.15 + j * 0.16, S['S2'] + 0.55 + j * 0.16))
        if u > 0:
            put(im, limb_spr(kind, i), W / 2 + dx * (1 - u), H / 2 + dy * (1 - u), u)
    # швы на стыках — зелёные кольца на «успешно»
    s = ramp(t, OK['S2'], OK['S2'] + 0.5)
    if s > 0:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for x, y in SEAMS:
            r = 20 + 30 * (1 - eo(s))
            d.ellipse((x - r, y - r, x + r, y + r), outline=GREEN + (int(255 * (1 - 0.6 * s)),), width=5)
        im.alpha_composite(glow(lay, 8, 1))
    ecg(im, t, eo(ramp(t, S['S3'], S['S3'] + 0.3)))
    system_lines(im, t)
    return im


# ------------------------------------------------------------------ сцена 2: профиль без памяти
CX, CY, CW, CH = 540, 900, 880, 600


@functools.lru_cache(None)
def card_base():
    im = Image.new('RGBA', (CW + 80, CH + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 40 + CW, 40 + CH), 18, fill=(11, 19, 33, 238), outline=BLUE + (255,), width=3)
    im = glow(im, 16, 1)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 40 + CW, 40 + CH), 18, fill=(11, 19, 33, 245))
    d.rounded_rectangle((40, 40, 40 + CW, 40 + CH), 18, outline=BLUE + (255,), width=3)
    d.line((40, 112, 40 + CW, 112), fill=BLUE + (90,), width=2)
    d.text((76, 62), 'ПРОФИЛЬ · НИЗШИЙ', font=mono(28, True), fill=DIM)
    d.ellipse((CW - 180, 72, CW - 164, 88), fill=GREEN)
    d.text((CW - 150, 62), 'В СЕТИ', font=mono(26, True), fill=GREEN)
    # аватар: капюшон без лица
    ax, ay = 40 + 190, 40 + 330
    d.ellipse((ax - 140, ay - 140, ax + 140, ay + 140), outline=BLUE + (120,), width=3)
    d.chord((ax - 110, ay - 120, ax + 110, ay + 150), 180, 360, outline=BLUE + (255,), width=6)
    d.line((ax - 110, ay + 15, ax - 120, ay + 130), fill=BLUE + (255,), width=6)
    d.line((ax + 110, ay + 15, ax + 120, ay + 130), fill=BLUE + (255,), width=6)
    d.ellipse((ax - 62, ay - 70, ax + 62, ay + 70), fill=(2, 3, 6, 255))
    lx = 40 + 400
    for k, lab in enumerate(('ИМЯ', 'ЛИЦО', 'ПАМЯТЬ')):
        d.text((lx, 40 + 170 + k * 140), lab, font=mono(28, True), fill=DIM)
    return im


def card(t, t_in):
    im = card_base().copy()
    d = ImageDraw.Draw(im)
    lx, f = 40 + 400, cap_font(58)
    for k, (gl, key) in enumerate(((NAME_GLITCH, 'name'), (FACE_GLITCH, 'face'))):
        y = 40 + 205 + k * 140
        if t < gl:
            n = 7 + int(3 * hash01(int(t * 12), k))
            d.text((lx, y), '█' * n, font=mono(44, True), fill=(70, 86, 110, 255))
        else:
            u = t - gl
            jit = (hash01(int(t * 40), k) - 0.5) * 26 * (1 - ramp(u, 0, 0.3))
            d.text((lx + jit, y - 6), 'НЕ НАЙДЕНО', font=f, fill=RED + (255,))
    # шкала памяти
    y = 40 + 205 + 2 * 140 + 10
    m = 1 - eio(ramp(t, MEMORY_DRAIN, MEMORY_DRAIN + 0.7))
    col = tuple(int(a * m + b * (1 - m)) for a, b in zip(BLUE, RED))
    d.rounded_rectangle((lx, y, lx + 380, y + 26), 8, outline=col + (255,), width=3)
    if m > 0.01:
        d.rounded_rectangle((lx + 5, y + 5, lx + 5 + 370 * m, y + 21), 5, fill=col + (255,))
    d.text((lx + 400, y - 8), f'{int(round(100 * m))}%', font=mono(36, True), fill=col + (255,))
    # глитч лица
    if t >= FACE_GLITCH:
        u = t - FACE_GLITCH
        ax, ay = 40 + 190, 40 + 330
        for i in range(14):
            yy = ay - 70 + i * 10
            w = 40 + 80 * hash01(i, int(t * 20))
            d.rectangle((ax - w, yy, ax + w * hash01(i, 3), yy + 5), fill=RED + (int(150 * (1 - ramp(u, 0.2, 0.9)) + 40),))
        d.text((ax, ay), '?', font=cap_font(120), fill=RED + (255,), anchor='mm')
    return glow(im, 6, 0) if False else im


def scene2(t):
    im = background().copy()
    dust(im, t + 3)
    u = eo(ramp(t, SC2, SC2 + 0.6))
    c = card(t, SC2)
    put(im, c, CX, CY + 60 * (1 - u), u, 0.94 + 0.06 * u)
    return im


# ------------------------------------------------------------------ сцена 3: крик и номер
@functools.lru_cache(None)
def number_spr():
    f = cap_font(560)
    im = text_spr('11', f, WHITE + (255,), pad=70, shadow=0.9)
    halo = text_spr('11', f, BLUE + (110,), pad=70).filter(ImageFilter.GaussianBlur(26))
    halo.alpha_composite(im)
    return halo


@functools.lru_cache(None)
def barcode_spr():
    im = Image.new('RGBA', (560, 130), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 10
    i = 0
    while x < 540:
        w = 3 + int(7 * hash01(i, 9))
        d.rectangle((x, 10, x + w, 90), fill=GREEN + (230,))
        x += w + 4 + int(6 * hash01(i, 4))
        i += 1
    d.text((280, 112), 'НОМЕР 0011 · НИЗШИЙ (ДОБРОВОЛЬНЫЙ)', font=mono(22, True), fill=GREEN + (230,), anchor='mm')
    return glow(im, 6, 1)


ORANGE = (255, 128, 52)


@functools.lru_cache(None)
def yorka_spr():
    """однорукая Йорка: короткая стрижка, шрам, правого плеча нет — силуэт с неоновым контуром"""
    im = Image.new('RGBA', (700, 1100), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hx, hy = 300, 330
    d.ellipse((hx - 105, hy - 120, hx + 105, hy + 120), fill=(8, 10, 16, 255), outline=ORANGE + (255,), width=7)
    for k in range(7):                                    # рваная короткая стрижка
        a = math.pi * (1.05 + k * 0.13)
        x0, y0 = hx + 110 * math.cos(a), hy + 125 * math.sin(a)
        d.line((x0, y0, x0 + 28 * math.cos(a - 0.5), y0 + 28 * math.sin(a - 0.5)), fill=ORANGE + (255,), width=6)
    d.polygon([(hx - 55, hy + 105), (hx + 45, hy + 110), (hx + 60, hy + 210), (hx - 70, hy + 205)],
              fill=(8, 10, 16, 255))
    body = [(hx - 70, hy + 200), (hx + 70, hy + 205), (hx + 250, hy + 300), (hx + 300, 1100), (hx - 260, 1100),
            (hx - 230, hy + 330)]
    d.polygon(body, fill=(8, 10, 16, 255), outline=ORANGE + (255,), width=7)
    d.ellipse((hx - 260, hy + 300, hx - 190, hy + 370), outline=ORANGE + (200,), width=6)       # культя
    d.line((hx - 160, hy - 20, hx - 120, hy + 40), fill=ORANGE + (180,), width=5)               # шрам
    d.chord((hx - 105, hy + 25, hx - 55, hy + 80), 90, 270, fill=ORANGE + (255,))               # открытый рот
    return glow(im, 16, 2)


def scene3(t):
    im = background().copy()
    dust(im, t + 7)
    # карточка уходит вперёд и размывается от крика
    u = ramp(t, HEY, HEY + 0.4)
    if u < 1:
        c = card(t, SC2)
        if u > 0:
            c = c.filter(ImageFilter.GaussianBlur(14 * u))
        put(im, c, CX, CY, 1 - eo(u), 1 + 0.35 * eo(u))
    # звуковые кольца крика из правого края
    rings = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(rings)
    for k, (t0, t1, text, acc) in enumerate(c for c in CAPS if c[0] >= S['Y1'] - 0.01):
        for j in range(3):
            v = (t - t0 - j * 0.12) / 0.9
            if 0 < v < 1:
                r = 60 + 620 * eo(v)
                d.ellipse((800 - r, 720 - r, 800 + r, 720 + r), outline=RED + (int(200 * (1 - v)),), width=5)
    out = ramp(t, STAMP - 0.25, STAMP + 0.05)
    if t < STAMP + 0.4:
        im.alpha_composite(alpha(glow(rings, 10, 1), 1 - out))
    yi = eo(ramp(t, HEY - 0.15, HEY + 0.25))
    if yi > 0 and out < 1:
        bob = math.sin(t * 9) * 6 * (1 - out)
        put(im, yorka_spr(), 1050 + 260 * (1 - yi) + 300 * eo(out), 900 + bob, yi * (1 - out), 0.88)
    # номер 11 — удар печати
    if t >= STAMP:
        v = t - STAMP
        sc = 1.0 + 0.45 * (1 - eo(v / 0.2))
        put(im, number_spr(), W / 2, 860, eo(v / 0.1), sc * (1 + 0.02 * v))
        put(im, barcode_spr(), W / 2, 1270, eo(ramp(v, 0.25, 0.6)))
        if v < 0.12:
            im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(70 * (1 - v / 0.12)))))
    return im


# ------------------------------------------------------------------ камера, HUD, подписи
def shake(t):
    a = 0.0
    for t0, amp in ((HEY, 22), (STAMP, 30)):
        v = t - t0
        if 0 <= v < 0.5:
            a += amp * math.exp(-v * 9)
    return (math.sin(t * 91) * a, math.cos(t * 77) * a)


def camera(im, t):
    if t < SC2:
        z, cy = 1.0 + 0.09 * eio(t / SC2), H / 2 + 40
    elif t < SC3:
        z, cy = 1.02 + 0.07 * eio((t - SC2) / (SC3 - SC2)), H / 2
    else:
        z, cy = 1.0 + 0.05 * eio((t - SC3) / (DUR - SC3)), H / 2 - 20
    sx, sy = shake(t)
    drift = math.sin(t * 0.35) * 10
    cx = W / 2 + drift + sx
    cy += sy
    # аффинное: пиксель экрана (x, y) <- мир ((x - W/2)/z + cx, (y - H/2)/z + cy)
    return im.transform((W, H), Image.AFFINE, (1 / z, 0, cx - W / 2 / z, 0, 1 / z, cy - H / 2 / z),
                        resample=Image.BILINEAR)


def blur_mix(a, b, u):
    """мягкий переход: обе картинки размываются, b проявляется"""
    r = 18 * math.sin(math.pi * u)
    if r > 0.5:
        small = (W // 3, H // 3)
        a = a.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 3)).resize((W, H), Image.BILINEAR)
        b = b.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 3)).resize((W, H), Image.BILINEAR)
    return Image.blend(a, b, eio(u))


def hud(im, t):
    a = eo(ramp(t, 0.1, 0.8))
    if a <= 0:
        return
    lay = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse((62, 118, 78, 134), fill=(GREEN if (t * 1.2) % 1 < 0.7 else (40, 90, 60)) + (255,))
    d.text((92, 108), 'ЧАСТЬ 1 · ПРОБУЖДЕНИЕ', font=mono(29, True), fill=DIM)
    d.text((1018, 100), 'ДЕНЬ 1', font=mono(46, True), fill=WHITE, anchor='ra')
    if t < SC2:
        st, col = 'СТАТУС: ЗАГРУЗКА' + '.' * (int(t * 3) % 4), DIM
    elif t < STAMP:
        st, col = 'ПАМЯТЬ: ' + ('СТЁРТА' if t >= MEMORY_DRAIN else 'ПРОВЕРКА'), (RED if t >= MEMORY_DRAIN else DIM)
    else:
        st, col = 'НОМЕР: 11', GREEN
    d.text((1018, 158), st, font=mono(24, True), fill=col, anchor='ra')
    im.alpha_composite(alpha(lay, a), (0, 0))


@functools.lru_cache(None)
def cap_spr(text, acc):
    f = cap_font(104)
    words = text.split(' ')
    parts = []
    for w_ in words:
        col = RED if acc and w_ == acc else WHITE
        parts.append(text_spr(w_, f, col + (255,), pad=34, shadow=0.85))
    gap = -40
    w = sum(p.width for p in parts) + gap * (len(parts) - 1)
    h = max(p.height for p in parts)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    x = 0
    for p in parts:
        im.alpha_composite(p, (x, (h - p.height) // 2))
        x += p.width + gap
    if im.width > W - 60:
        k = (W - 60) / im.width
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    return im


def captions(im, t):
    for t0, t1, text, acc in CAPS:
        if t0 - 0.02 <= t < t1:
            u_in, u_out = ramp(t, t0, t0 + 0.14), ramp(t, t1 - 0.1, t1)
            put(im, cap_spr(text, acc), W / 2, 1460 - 18 * (1 - eo(u_in)), eo(u_in) * (1 - u_out),
                1.06 - 0.06 * eo(u_in))


def render_at(t):
    if t < SC2 - 0.25:
        im = camera(scene1(t), t)
    elif t < SC2 + 0.25:
        im = blur_mix(camera(scene1(t), t), camera(scene2(t), t), (t - (SC2 - 0.25)) / 0.5)
    elif t < SC3:
        im = camera(scene2(t), t)
    else:
        im = camera(scene3(t), t)
        if HEY <= t < HEY + 0.35:
            im.alpha_composite(Image.new('RGBA', (W, H), RED + (int(110 * (1 - (t - HEY) / 0.35)),)))
    hud(im, t)
    captions(im, t)
    a_in = ramp(t, 0, 0.35)
    a_out = ramp(t, DUR - 0.6, DUR)
    k = a_in * (1 - a_out)
    if k < 1:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - k)))))
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
