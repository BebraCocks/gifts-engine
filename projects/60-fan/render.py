"""«Что будет, если насрать на вентилятор»: 2D, всё кодом. Кадр — чистая функция времени содержания.

    python -B projects/60-fan/render.py --frames 0,600       # пробные кадры (номера кадров вывода)
    python -B projects/60-fan/render.py --video out.mp4      # видеоряд (вызывает build.py)
"""
import functools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import banner  # noqa: E402
import frames  # noqa: E402
from kit import *  # noqa: E402,F401,F403
from kit import (W, H, FPS, INK, YEL, RED, WHITE, SKIN, HOOD, POO, POO_D, POO_L, GAS, S, E, DUR, cl, sm, eo, eio,
                 spring, lerp, mix, noise, font, text_spr, put, canvas, done, P, oval, rrect, thick, grad_t, hero,
                 head_spr, body_spr, talk_open, panel, label, counter_text, pop, gauge, bar, stamp, draw_caps,
                 blueprint)  # noqa: E402
from events import AD_STOP  # noqa: E402

BR = banner.Breaks([AD_STOP], cy=H / 2)
METAL = (196, 204, 220)
FAN_BLUE = (90, 170, 240)


# ------------------------------------------------------------------ вентилятор
@functools.lru_cache(4)
def blades_spr(R=260):
    im, d = canvas(2 * R + 20, 2 * R + 20)
    c = R + 10
    for k in range(3):
        a = math.radians(k * 120)
        pts = []
        for i in range(13):
            v = i / 12
            ang = a + math.radians(-26 + 52 * v)
            rr = R * (0.98 - 0.12 * abs(v - 0.5))
            pts.append((c + math.cos(ang) * rr, c + math.sin(ang) * rr))
        pts = [(c + math.cos(a - 0.35) * 40, c + math.sin(a - 0.35) * 40)] + pts + \
              [(c + math.cos(a + 0.35) * 40, c + math.sin(a + 0.35) * 40)]
        d.polygon([tuple(P(*p)) for p in pts], fill=FAN_BLUE + (230,), outline=INK, width=5 * SS)
    return done(im)


@functools.lru_cache(4)
def grille_spr(R=260):
    im, d = canvas(2 * R + 60, 2 * R + 60)
    c = R + 30
    d.ellipse(P(c - R - 22, c - R - 22, c + R + 22, c + R + 22), outline=INK, width=16 * SS)
    d.ellipse(P(c - R - 18, c - R - 18, c + R + 18, c + R + 18), outline=WHITE, width=8 * SS)
    for rr in (R * 0.3, R * 0.55, R * 0.8):
        d.ellipse(P(c - rr, c - rr, c + rr, c + rr), outline=(235, 238, 246, 230), width=4 * SS)
    for k in range(24):
        a = math.radians(k * 15)
        d.line(P(c + math.cos(a) * 60, c + math.sin(a) * 60, c + math.cos(a) * (R + 14), c + math.sin(a) * (R + 14)),
               fill=(235, 238, 246, 220), width=3 * SS)
    oval(d, c, c, 62, 62, WHITE)
    oval(d, c, c, 40, 40, FAN_BLUE)
    d.text(P(c, c), '3', font=font(40 * SS), fill=WHITE, anchor='mm')
    return done(im)


@functools.lru_cache(4)
def stand_spr(R=260):
    im, d = canvas(420, 760)
    rrect(d, (190, 0, 230, 640), 14, METAL)
    oval(d, 210, 690, 190, 54, METAL)
    oval(d, 210, 676, 150, 34, (220, 226, 238), None)
    for k, col in enumerate(((120, 220, 120), YEL, RED)):
        oval(d, 150 + k * 60, 690, 16, 10, col, INK, 3)
    rrect(d, (150, 0, 270, 110), 30, (230, 234, 244))           # мотор сзади
    return done(im)


def fan(im, cx, cy, t, scale=1.0, speed=1.0, yaw=0.0, stand=True, angle=None):
    """Вентилятор: (cx, cy) — центр решётки. speed 0..1 — доля полных оборотов (1300 об/мин)."""
    R = 260
    if stand:
        put(im, stand_spr(), cx, cy + 40 * scale, scale, anchor=(0.5, 0.0))
    head = Image.new('RGBA', (2 * R + 60, 2 * R + 60), (0, 0, 0, 0))
    c = R + 30
    ang = (t * 360 * 21.7 * speed) if angle is None else angle      # 1300 об/мин ≈ 21,7 об/с
    b = blades_spr()
    if speed > 0.25:     # размытие: несколько полупрозрачных копий + диск
        d = ImageDraw.Draw(head)
        d.ellipse((c - R + 4, c - R + 4, c + R - 4, c + R - 4), fill=FAN_BLUE + (int(90 * speed),))
        for k in range(4):
            put(head, b, c, c, 1.0, -(ang + k * 9) % 360, 0.35)
    else:
        put(head, b, c, c, 1.0, -ang % 360)
    put(head, grille_spr(), c, c)
    if abs(yaw) > 0.01:
        k = max(0.12, math.cos(yaw))
        head = head.resize((max(1, int(head.size[0] * k)), head.size[1]), Image.BILINEAR)
    put(im, head, cx + math.sin(yaw) * 40 * scale, cy, scale)


# ------------------------------------------------------------------ «посылка»
@functools.lru_cache(16)
def poo_spr(face='calm', L=220):
    im, d = canvas(L + 40, 120)
    rrect(d, (10, 14, L + 30, 106), 46, POO)
    for k in range(1, 4):
        x = 10 + (L + 20) * k / 4
        d.arc(P(x - 26, 18, x + 26, 102), 300, 60, fill=POO_D, width=5 * SS)
    d.rounded_rectangle(P(40, 26, L - 20, 42), 8 * SS, fill=POO_L)
    cx = (L + 40) / 2
    if face == 'calm':
        for s in (-1, 1):
            oval(d, cx + s * 22, 58, 10, 12, WHITE, INK, 3)
            oval(d, cx + s * 22 + 2, 61, 5, 6, INK, None)
        d.arc(P(cx - 14, 66, cx + 14, 86), 20, 160, fill=INK, width=4 * SS)
    elif face == 'scared':
        for s in (-1, 1):
            oval(d, cx + s * 24, 56, 13, 16, WHITE, INK, 3)
            oval(d, cx + s * 24, 58, 4, 5, INK, None)
        oval(d, cx, 86, 9, 11, (60, 20, 20), None)
    return done(im)


@functools.lru_cache(64)
def splat_spr(seed, r=40):
    rnd = random.Random(seed)
    im, d = canvas(r * 5, r * 5)
    c = r * 2.5
    pts = []
    n = 14
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * rnd.uniform(0.7, 1.25)
        pts.append((c + math.cos(a) * rr, c + math.sin(a) * rr))
    d.polygon([tuple(P(*p)) for p in pts], fill=POO_D)
    oval(d, c, c, r * 0.75, r * 0.75, POO, None)
    for i in range(9):
        a = rnd.uniform(0, 2 * math.pi)
        rr = r * rnd.uniform(1.4, 2.3)
        s = r * rnd.uniform(0.08, 0.22)
        oval(d, c + math.cos(a) * rr, c + math.sin(a) * rr, s, s, POO_D, None)
    oval(d, c - r * 0.3, c - r * 0.3, r * 0.2, r * 0.14, POO_L, None)
    return done(im)


def drops(im, pts, t=0, col=POO):
    d = ImageDraw.Draw(im)
    for x, y, r in pts:
        if r < 1:
            continue
        d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=POO_D)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)


# ------------------------------------------------------------------ комната
SPLATS = []                  # (x, y, r, seed, когда, где)
_rnd = random.Random(60)
for i in range(46):          # фронт: обои/шторы/ТВ — во время L11
    SPLATS.append((_rnd.uniform(60, 1020), _rnd.uniform(420, 1280), _rnd.uniform(14, 36), i, 0))
for i in range(60):          # поворот: вся комната — во время L12
    SPLATS.append((_rnd.uniform(20, 1060), _rnd.uniform(380, 1480), _rnd.uniform(10, 32), 100 + i, 1))


def splat_time(i):
    x, y, r, seed, grp = SPLATS[i]
    if grp == 0:
        return S['L11'] + 0.2 + (i / 46) * 2.6
    # при повороте брызги идут «волной» слева направо и обратно
    ph = x / W
    return S['L12'] + 1.0 + ph * 2.4 + (0 if i % 2 else 2.4 * (1 - ph))


def room_front(im, t, dirty=True, light=1.0):
    d = ImageDraw.Draw(im)
    # обои
    for x in range(0, W, 90):
        d.rectangle((x, 0, x + 45, 1500), fill=(212, 226, 244))
    for x in range(45, W, 180):
        for y in range(60, 1500, 160):
            d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(190, 208, 236))
    # окно со шторами
    d.rounded_rectangle((70, 420, 420, 860), 16, fill=(160, 214, 255), outline=INK, width=8)
    d.line((245, 420, 245, 860), fill=INK, width=8)
    for x0, x1 in ((40, 150), (340, 450)):
        d.rectangle((x0, 380, x1, 1000), fill=(236, 110, 120), outline=INK, width=6)
        for xx in range(x0 + 20, x1, 26):
            d.line((xx, 384, xx, 996), fill=(210, 86, 100), width=4)
    d.rectangle((20, 370, 470, 392), fill=INK)
    # телевизор
    d.rounded_rectangle((560, 620, 1010, 900), 18, fill=(30, 34, 50), outline=INK, width=8)
    d.rounded_rectangle((580, 640, 990, 880), 8, fill=(70, 120, 200))
    d.rectangle((600, 900, 970, 1120), fill=(170, 120, 80), outline=INK, width=6)
    d.line((600, 1010, 970, 1010), fill=INK, width=5)
    # пол
    d.rectangle((0, 1500, W, H), fill=(170, 120, 84))
    for y in range(1500, H, 70):
        d.line((0, y, W, y), fill=(150, 104, 70), width=4)
    if dirty:
        for i, (x, y, r, seed, grp) in enumerate(SPLATS):
            u = t - splat_time(i)
            if u > 0:
                put(im, splat_spr(seed % 12), x, y, (r / 40) * (0.6 + 0.4 * eo(u / 0.12)), (seed * 37) % 360)


# ------------------------------------------------------------------ сцены
def sc01(t):
    """Хук: включённый вентилятор, «посылка» висит над ним, вопрос."""
    u = t - S['L01']
    im = blueprint(t, (34, 30, 70), (70, 40, 60))
    label(im, 'НАСРАТЬ', 540, 470, 140, (200, 140, 90), 12, 1 + 0.03 * math.sin(t * 6), -4)
    label(im, 'НА ВЕНТИЛЯТОР?', 540, 610, 100, WHITE, 10, 1 + 0.03 * math.sin(t * 6 + 1), 2)
    fan(im, 540, 1230, t, 0.95, 1.0)
    # колбаска висит над решёткой и дрожит
    put(im, poo_spr('scared'), 540 + 6 * noise(t * 3, 1), 860 + 12 * math.sin(t * 3), 1.0, 8 * math.sin(t * 2))
    d = ImageDraw.Draw(im)
    for k in range(3):   # поток воздуха
        yy = 1000 + k * 30 - (t * 300) % 90
        d.arc((360, yy - 30, 720, yy + 30), 200, 340, fill=WHITE + (120,), width=5)
    v = u - 2.6
    if v > 0:
        stamp(im, 'НЕ ПОВТОРЯТЬ!', 540, 1700, v, RED, 90, -6)
    v = u - 3.8
    if v > 0:
        for i, f in enumerate(('40 см', '1300 об/мин', '= ?')):
            uu = v - i * 0.15
            put(im, text_spr(f, 56, YEL, 'Heavy', 6), 190 + i * 350, 760, pop(uu), -6 + i * 6, cl(uu / 0.15))
    return im


def sc02(t):
    u = t - S['L02']
    im = blueprint(t)
    spd = eo(u / 4.0)
    fan(im, 540, 1000, t, 1.05, spd)
    d = ImageDraw.Draw(im)
    # размер 40 см
    a = cl((u - 1.0) / 0.5)
    if a > 0:
        y = 650
        d.line((260, y, 260 + 560 * a, y), fill=YEL, width=8)
        d.polygon([(260, y), (290, y - 18), (290, y + 18)], fill=YEL)
        if a >= 1:
            d.polygon([(820, y), (790, y - 18), (790, y + 18)], fill=YEL)
        label(im, '40 см', 540, y - 56, 72, YEL, 8, alpha=a)
    # обороты
    panel(im, (140, 1580, 940, 1800), (20, 24, 40, 230), ol=WHITE, w=4)
    label(im, counter_text(1300 * spd), 420, 1690, 120, GAS, 0)
    label(im, 'об/мин', 760, 1690, 60, WHITE, 0)
    return im


@functools.lru_cache(2)
def car_spr():
    im, d = canvas(340, 160)
    rrect(d, (10, 60, 330, 130), 30, RED)
    d.polygon([tuple(P(80, 62)), tuple(P(120, 16)), tuple(P(240, 16)), tuple(P(280, 62))], fill=RED, outline=INK,
              width=6 * SS)
    d.polygon([tuple(P(110, 58)), tuple(P(134, 28)), tuple(P(174, 28)), tuple(P(174, 58))], fill=(170, 220, 255))
    d.polygon([tuple(P(186, 58)), tuple(P(186, 28)), tuple(P(228, 28)), tuple(P(254, 58))], fill=(170, 220, 255))
    for x in (80, 260):
        oval(d, x, 130, 28, 28, (40, 40, 50))
        oval(d, x, 130, 12, 12, METAL, None)
    return done(im)


def sc03(t):
    u = t - S['L03']
    im = blueprint(t, (20, 30, 64), (40, 30, 70))
    fan(im, 540, 820, t, 0.85, 1.0, stand=False)
    # «кончик лопасти» — светящаяся точка с хвостом по окружности
    d = ImageDraw.Draw(im)
    R = 0.85 * 252
    a0 = t * 2 * math.pi * 1.3        # для глаза замедлено
    for k in range(18):
        a = a0 - k * 0.07
        x, y = 540 + math.cos(a) * R, 820 + math.sin(a) * R
        r = 16 - k * 0.8
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 220, 80, 255 - k * 13))
    label(im, 'кончик лопасти', 540, 1110, 48, YEL, 6)
    gauge(im, 300, 1450, 200, 100 * eo((u - 0.4) / 1.6), 120, 'кончик', ' км/ч', t, red_from=90)
    # машина на трассе — та же скорость
    v = u - 1.8
    if v > 0:
        put(im, car_spr(), lerp(1200, 790, eo(v / 0.7)) + 6 * math.sin(t * 20), 1400, 0.9)
        d.line((620, 1490, 1060, 1490), fill=WHITE + (180,), width=5)
        for k in range(5):
            xx = 1060 - ((t * 900 + k * 100) % 440)
            d.line((xx, 1490, xx + 40, 1490), fill=INK, width=5)
        label(im, 'как машина на трассе', 800, 1560, 42, WHITE, 5, alpha=cl(v / 0.3))
    return im


def sc04(t):
    u = t - S['L04']
    im = blueprint(t, (40, 24, 64), (70, 30, 60))
    # лопасти «по очереди»: замедленно, каждая подсвечивается
    ang = u * 360 * 0.6
    fan(im, 540, 820, t, 0.85, 0.0, stand=False, angle=ang)
    d = ImageDraw.Draw(im)
    for k in range(3):
        put(im, text_spr(str(k + 1), 70, YEL, 'Heavy', 8), 540 + math.cos(math.radians(-ang + 120 * k - 90)) * 150 * 0.85 * -1 * -1,
            820 + math.sin(math.radians(-ang + 120 * k - 90)) * 150 * 0.85, pop(u - 0.2 - k * 0.25))
    n = int(65 * eo((u - 1.2) / 1.6))
    panel(im, (140, 1240, 940, 1520), (255, 214, 64, 250))
    label(im, f'{n}', 540, 1340, 150, INK, 0, 1 + 0.06 * math.sin(t * 40) * cl((u - 1.2) / 0.3))
    label(im, 'ударов в секунду', 540, 1460, 56, INK, 0)
    # метроном ударов
    for k in range(13):
        x = 120 + k * 70
        on = (u * 65 / 6 + k) % 13 < 1
        d.ellipse((x - 18, 1640 - 18, x + 18, 1640 + 18), fill=(RED if on else (80, 80, 120)) + (255,))
    return im


@functools.lru_cache(2)
def scale_spr():
    im, d = canvas(460, 300)
    rrect(d, (20, 120, 440, 290), 30, (236, 240, 248))
    rrect(d, (130, 170, 330, 250), 14, (40, 50, 60))
    oval(d, 230, 110, 190, 26, METAL)
    return done(im)


def censor(im, box, t):
    """Пиксельная «цензура» с надписью."""
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    if x1 - x0 < 20 or y1 - y0 < 20:
        return
    reg = im.crop((x0, y0, x1, y1))
    small = reg.resize((max(1, (x1 - x0) // 34), max(1, (y1 - y0) // 34)), Image.BILINEAR)
    reg = small.resize((x1 - x0, y1 - y0), Image.NEAREST)
    im.paste(reg, (x0, y0))
    label(im, 'ЦЕНЗУРА', (x0 + x1) / 2, (y0 + y1) / 2, 58, WHITE, 6, rot=-5)


def sc05(t):
    u = t - S['L05']
    dur = E['L05'] - S['L05']
    im = room_bg(t)
    if u < 3.2:
        # весы: 130 г
        put(im, scale_spr(), 540, 1300, 1.2)
        drop = 900 * (1 - eo(u / 0.5))
        put(im, poo_spr('calm'), 540, 1150 - drop, 1.1)
        g = 130 * eo((u - 0.45) / 0.8)
        label(im, counter_text(g, ' г'), 540, 1415, 64, GAS, 0)
        label(im, '≈ 130 г', 540, 820, 110, POO, 10, pop(u - 1.3), -5)
        put(im, text_spr('средняя «посылка»', 52, INK, 'Heavy', 0), 540, 930, pop(u - 1.5))
        return im
    v = u - 3.2
    # присаживается над решёткой (сверху, за кадром — цензура)
    fan(im, 540, 1360, t, 0.85, 1.0)
    hy = lerp(500, 760, eo(v / 0.8))
    hero(im, 540, hy, 0.9, 'smug' if v < 2.2 else 'happy', talk_open(t, 'L05'), chair=False)
    censor(im, (330, hy - 40, 750, hy + 160), t)
    rel = dur - 3.2 - 0.5
    if v > rel:
        put(im, poo_spr('scared'), 540, hy + 180 + 400 * (v - rel) ** 2, 0.8)
    return im


def room_bg(t):
    im = grad_t((214, 228, 246), (196, 214, 238))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90):
        d.rectangle((x, 0, x + 45, 1580), fill=(222, 234, 248))
    d.rectangle((0, 1580, W, H), fill=(170, 120, 84))
    for y in range(1580, H, 70):
        d.line((0, y, W, y), fill=(150, 104, 70), width=4)
    d.rounded_rectangle((60, 380, 320, 640), 14, fill=(255, 248, 230), outline=INK, width=7)
    d.ellipse((150, 450, 230, 530), fill=(250, 200, 80))
    d.rounded_rectangle((780, 400, 1020, 700), 14, fill=(160, 214, 255), outline=INK, width=7)
    return im


def sc06(t):
    """Замедленное падение: линейка 50 см и таймер 0,32 с."""
    u = t - S['L06']
    dur = E['L06'] - S['L06']
    im = blueprint(t, (24, 24, 40), (44, 34, 60))
    fall = eio(u / (dur * 0.95))
    fan(im, 560, 1400, t, 0.8, 0.12)                 # slow-mo: лопасти еле ползут
    d = ImageDraw.Draw(im)
    # линейка
    d.rounded_rectangle((120, 560, 210, 1230), 10, fill=YEL, outline=INK, width=6)
    for k in range(11):
        y = 570 + k * 65
        d.line((120, y, 160 if k % 2 else 180, y), fill=INK, width=5)
    label(im, '50 см', 165, 500, 52, YEL, 6)
    put(im, poo_spr('scared'), 560, lerp(560, 1150, fall), 0.85, 25 * fall)
    for k in range(4):   # штрихи движения
        yy = lerp(560, 1150, fall) - 70 - k * 40
        d.line((520, yy, 600, yy), fill=WHITE + (160 - k * 35,), width=5)
    panel(im, (620, 450, 1010, 640), (20, 24, 40, 230), ol=WHITE, w=4)
    label(im, f'{0.32 * fall:.2f} с'.replace('.', ','), 815, 545, 100, GAS, 0)
    label(im, 'SLOW-MO', 815, 720, 60, RED, 6, alpha=0.6 + 0.4 * math.sin(t * 6))
    return im


@functools.lru_cache(4)
def tennis_spr(phase=0):
    im, d = canvas(340, 520)
    thick(d, [(150, 330), (120, 500)], 30, (60, 70, 120))
    thick(d, [(180, 330), (220, 500)], 30, (60, 70, 120))
    rrect(d, (110, 180, 220, 340), 40, WHITE)
    oval(d, 165, 120, 54, 54, SKIN)
    d.chord(P(108, 64, 222, 140), 180, 360, fill=(240, 80, 80))
    oval(d, 180, 116, 6, 7, INK, None)
    ang = -60 if phase == 0 else 30
    hx, hy = 210 + math.cos(math.radians(ang)) * 40, 200 + math.sin(math.radians(ang)) * 40
    thick(d, [(205, 200), (hx, hy)], 24, SKIN)
    rx, ry = hx + math.cos(math.radians(ang)) * 90, hy + math.sin(math.radians(ang)) * 90
    d.line(P(hx, hy, rx, ry), fill=INK, width=10 * SS)
    oval(d, rx + math.cos(math.radians(ang)) * 50, ry + math.sin(math.radians(ang)) * 50, 46, 60, (250, 250, 250, 0),
         INK, 8)
    return done(im)


def sc07(t):
    """Удар первой лопасти + сравнение с подачей теннисиста."""
    u = t - S['L07']
    im = blueprint(t, (40, 20, 40), (70, 30, 50))
    hit = 0.25
    shake = 18 * math.exp(-6 * max(0, u - hit)) * noise(t * 4, 2) if u > hit else 0
    fan(im, 540 + shake, 760, t, 0.75, 0.0, stand=False, angle=(-90 + 140 * eo(u / hit)) if u < hit else 50 + u * 40)
    d = ImageDraw.Draw(im)
    if u < hit:
        put(im, poo_spr('scared'), 540, 620, 0.8)
    else:
        v = u - hit
        # колбаска разламывается и улетает кусками
        for k in range(3):
            put(im, poo_spr('none' if k else 'scared', 70), 540 + (k - 1) * 260 * eo(v / 0.4) + 40 * k,
                620 - 180 * eo(v / 0.4) + 600 * v * v, 0.8, (k - 1) * 200 * v)
        if v < 0.3:
            d.ellipse((540 - 300 * v * 3, 620 - 300 * v * 3, 540 + 300 * v * 3, 620 + 300 * v * 3),
                      outline=WHITE + (int(255 * (1 - v / 0.3)),), width=14)
        label(im, 'БАМ!', 760, 470, 130, YEL, 12, pop(v, 0.25), 10, alpha=cl(1.6 - v))
        k = eo(v / 0.6)
        pts = [(540 + dx * (80 + 380 * k), 760 + dy * (60 + 300 * k) + 40 * v, r * 0.8) for dx, dy, r in DROPS[:90]]
        drops(im, pts)
    # теннисист
    v = u - 1.6
    if v > 0:
        panel(im, (60, 1180, 1020, 1760), (255, 255, 255, 230))
        put(im, tennis_spr(0 if (v % 1.2) < 0.6 else 1), 260, 1470, 0.9)
        bx = 400 + ((v % 1.2) / 1.2) * 600
        d = ImageDraw.Draw(im)
        d.ellipse((bx - 22, 1330 - 22, bx + 22, 1330 + 22), fill=(220, 240, 60), outline=INK, width=4)
        for k in range(4):
            d.line((bx - 40 - k * 40, 1330, bx - 70 - k * 40, 1330), fill=(200, 210, 60, 200 - k * 40), width=6)
        label(im, 'подача любителя', 720, 1440, 54, INK, 0, alpha=cl(v / 0.3))
        label(im, '≈ 100 км/ч', 720, 1540, 90, RED, 0, pop(v - 0.2))
        label(im, '= удар лопасти', 720, 1650, 50, (90, 90, 120), 0, alpha=cl((v - 2.0) / 0.3))
    return im


DROPS = [(random.Random(i).uniform(-1, 1), random.Random(i + 5).uniform(-1, 1), random.Random(i + 9).uniform(3, 11))
         for i in range(220)]


def sc08(t):
    """Ещё 6 ударов за 0,1 с — облако брызг."""
    u = t - S['L08']
    dur = E['L08'] - S['L08']
    im = blueprint(t, (40, 20, 40), (60, 30, 50))
    fan(im, 540, 900, t, 0.8, 1.0, stand=False)
    # 6 ударов-вспышек
    d = ImageDraw.Draw(im)
    for k in range(6):
        tk = 0.3 + k * 0.32
        v = u - tk
        if 0 <= v < 0.2:
            r = 120 + 400 * v
            d.ellipse((540 - r, 900 - r, 540 + r, 900 + r), outline=YEL + (int(255 * (1 - v / 0.2)),), width=10)
    n = int(cl((u - 0.3) / 1.9) * 6 + 0.999) if u > 0.3 else 0
    panel(im, (300, 1380, 780, 1560), (255, 214, 64, 250))
    label(im, f'+{n} ударов', 540, 1470, 80, INK, 0, 1 + 0.08 * math.sin(t * 30) * (n < 6))
    label(im, 'за 0,1 с', 540, 1630, 64, WHITE, 6)
    # облако брызг растёт после 3-го удара
    k = eo((u - 1.2) / 2.0)
    if k > 0:
        pts = []
        for dx, dy, r in DROPS:
            rr = 120 + 420 * k * (0.4 + 0.6 * abs(dx))
            pts.append((540 + dx * rr + 10 * math.sin(t * 3 + dy * 9), 900 + dy * rr * 0.8, r * (0.6 + 0.6 * k)))
        drops(im, pts)
    if u > dur * 0.7:
        label(im, 'облако брызг', 540, 380 + 0, 80, POO_L, 8, pop(u - dur * 0.7), -4)
    return im


def sc09(t):
    """План комнаты сверху: веер брызг до стены за 1/7 с."""
    u = t - S['L09']
    dur = E['L09'] - S['L09']
    im = grad_t((236, 230, 218), (226, 218, 204))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 140, 420, 940, 1220            # 4 × 4 м
    d.rectangle((x0 - 24, y0 - 24, x1 + 24, y1 + 24), fill=INK)
    d.rectangle((x0, y0, x1, y1), fill=(250, 246, 236))
    for k in range(1, 4):
        d.line((x0 + k * 200, y0, x0 + k * 200, y1), fill=(220, 214, 200), width=3)
        d.line((x0, y0 + k * 200, x1, y0 + k * 200), fill=(220, 214, 200), width=3)
    # мебель сверху
    d.rounded_rectangle((180, 460, 420, 600), 20, fill=(150, 190, 240), outline=INK, width=5)   # диван
    d.rectangle((640, 440, 900, 480), fill=(40, 40, 60))                                        # ТВ
    d.rounded_rectangle((720, 900, 900, 1180), 16, fill=(240, 200, 150), outline=INK, width=5)  # кровать
    # вентилятор сверху
    fx, fy = 540, 1120
    d.rounded_rectangle((fx - 70, fy - 20, fx + 70, fy + 20), 10, fill=FAN_BLUE, outline=INK, width=5)
    d.ellipse((fx - 30, fy - 10, fx + 30, fy + 60), fill=METAL, outline=INK, width=5)
    # линейка 4 м
    d.line((x1 + 60, y0, x1 + 60, y1), fill=RED, width=6)
    label(im, '4 м', x1 + 60, (y0 + y1) / 2, 50, RED, 6, rot=90)
    # веер
    k = cl((u - 0.8) / 1.0)
    if k > 0:
        reach = 700 * eo(k)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        dl.pieslice((fx - reach, fy - reach, fx + reach, fy + reach), 225, 315, fill=POO + (80,))
        im.alpha_composite(lay)
        pts = []
        for i, (dx, dy, r) in enumerate(DROPS[:120]):
            a = math.radians(270 + dx * 45)
            rr = reach * (0.6 + 0.4 * abs(dy))
            px, py = fx + math.cos(a) * rr, fy + math.sin(a) * rr
            pts.append((min(max(px, x0 + 6), x1 - 6), max(py, y0 + 6), r * 0.8))
        drops(im, pts)
        if k >= 1:
            for i, (dx, dy, r) in enumerate(DROPS[:40]):
                put(im, splat_spr(i % 12), x0 + 40 + (i * 19) % 720, y0 + 10, 0.35)
    v = u - (dur - 2.6)
    if v > 0:
        panel(im, (200, 1340, 880, 1580), (20, 24, 40, 230), ol=WHITE, w=4)
        label(im, 'до стены', 540, 1400, 52, (180, 190, 220), 0)
        label(im, '1/7 с', 540, 1500, 110, YEL, 0, pop(v))
    label(im, 'вид сверху', 540, 1720, 50, (120, 110, 100), 0)
    return im


def eye(im, cx, cy, r, lid):
    d = ImageDraw.Draw(im)
    d.ellipse((cx - r - 10, cy - r * 0.62 - 10, cx + r + 10, cy + r * 0.62 + 10), fill=INK)
    d.ellipse((cx - r, cy - r * 0.62, cx + r, cy + r * 0.62), fill=WHITE)
    d.ellipse((cx - r * 0.38, cy - r * 0.38, cx + r * 0.38, cy + r * 0.38), fill=(80, 150, 90))
    d.ellipse((cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18), fill=INK)
    d.ellipse((cx - r * 0.1 + 20, cy - r * 0.2, cx + 20, cy - r * 0.1), fill=WHITE)
    if lid > 0:
        top = cy - r * 0.62 - 12
        d.rectangle((cx - r - 12, top, cx + r + 12, top + (r * 1.24 + 24) * lid), fill=SKIN)
        d.line((cx - r - 12, top + (r * 1.24 + 24) * lid, cx + r + 12, top + (r * 1.24 + 24) * lid), fill=INK, width=8)


def sc10(t):
    """Моргание (1/3 с) против брызг (1/7 с)."""
    u = t - S['L10']
    im = blueprint(t, (24, 30, 60), (50, 30, 70))
    # циклический повтор: брызги долетают раньше, чем закрылся глаз
    cyc = 1.6
    ph = (u % cyc)
    lid = cl(ph / 0.33) if ph < 0.33 else max(0.0, 1 - (ph - 0.33) / 0.2)
    eye(im, 540, 760, 300, lid)
    if ph > 0.14:
        for i in range(10):
            rnd = random.Random(i)
            put(im, splat_spr(i), 540 + rnd.uniform(-260, 260), 760 + rnd.uniform(-160, 160), 0.6)
    elif ph > 0.04:
        pts = [(540 + dx * 500 * (1 - ph / 0.14), 760 + dy * 400 * (1 - ph / 0.14), r) for dx, dy, r in DROPS[:60]]
        drops(im, pts)
    bar(im, 100, 1300, 760, 50, 0.8 * (1 / 7) / (1 / 3) * cl(u / 0.8), POO_L, 'Брызги долетают', '0,14 с')
    bar(im, 100, 1480, 760, 50, 0.8 * cl((u - 0.5) / 0.8), (120, 200, 250), 'Моргание', '0,33 с')
    if u > 2.0:
        stamp(im, 'НЕ УСПЕЛ', 540, 1700, u - 2.0, RED, 90, -6)
    return im


def sc11(t):
    """Комната: брызги на обоях, шторах, ТВ; отскок — в лицо."""
    u = t - S['L11']
    dur = E['L11'] - S['L11']
    im = grad_t((214, 228, 246), (200, 216, 240))
    room_front(im, t)
    fan(im, 540, 1300, t, 0.7, 1.0, stand=True)
    # подписи по очереди
    for i, (txt, x, y) in enumerate((('обои', 830, 380), ('шторы', 245, 1050), ('телевизор', 785, 600))):
        put(im, text_spr(txt, 50, RED, 'Heavy', 6), x, y, pop(u - 0.6 - i * 0.6))
    v = u - (dur - 3.4)
    if v > 0:
        # крупный план героя: брызги в лицо
        k = eo(v / 0.4)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, int(150 * k)))
        im.alpha_composite(lay)
        hero(im, 540, lerp(2400, 1900, k), 1.7, 'shock' if v < 1.6 else 'scared', 1, chair=False)
        if v > 1.2:
            for i in range(9):
                rnd = random.Random(i + 7)
                put(im, splat_spr(i), 540 + rnd.uniform(-150, 150), 1900 - 560 + rnd.uniform(-130, 110),
                    0.35 * eo((v - 1.2 - i * 0.04) / 0.1))
            label(im, 'ПРЯМО В ЛИЦО', 540, 820, 90, YEL, 10, pop(v - 1.4), -4)
    return im


def sc12(t):
    """Режим поворота: разбрызгиватель обходит всю комнату."""
    u = t - S['L12']
    im = grad_t((214, 228, 246), (200, 216, 240))
    room_front(im, t)
    yaw = 0.9 * math.sin(u * 1.4) if u > 0.8 else 0
    fan(im, 540, 1300, t, 0.7, 1.0, yaw=yaw)
    # струя брызг в сторону поворота
    if u > 0.8:
        pts = []
        for i, (dx, dy, r) in enumerate(DROPS[:90]):
            ph = (t * 1.3 + i * 0.011) % 1
            a = -math.pi / 2 + yaw * 1.1 + dx * 0.25
            rr = 140 + 900 * ph
            pts.append((540 + math.cos(a) * rr, 1300 + math.sin(a) * rr * 0.9, r * (1 - ph * 0.5)))
        drops(im, pts)
    label(im, 'РЕЖИМ ПОВОРОТА', 540, 1700, 72, WHITE, 8, pop(u - 0.4), alpha=1.0)
    d = ImageDraw.Draw(im)
    d.arc((340, 1560, 740, 1660), 200, 340, fill=YEL + (255,), width=8)
    return im


def sc13(t):
    """Запах: вентилятор гоняет воздух, запах уходит в коридор."""
    u = t - S['L13']
    dur = E['L13'] - S['L13']
    im = grad_t((236, 230, 218), (226, 218, 204))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 120, 420, 760, 1220
    d.rectangle((x0 - 24, y0 - 24, x1 + 24, y1 + 24), fill=INK)
    d.rectangle((x0, y0, x1, y1), fill=(250, 246, 236))
    d.rectangle((x1 + 24, y0, 1060, y1), fill=(232, 224, 210))       # коридор
    d.rectangle((x1, 760, x1 + 24, 900), fill=(200, 150, 100))       # дверь (щель)
    label(im, 'коридор', 910, 470, 44, (120, 110, 100), 0)
    fx, fy = 440, 1140
    d.rounded_rectangle((fx - 70, fy - 20, fx + 70, fy + 20), 10, fill=FAN_BLUE, outline=INK, width=5)
    # вихри воздуха
    k = cl(u / (dur * 0.6))
    for j in range(5):
        r = 80 + j * 55
        a0 = t * 160 + j * 50
        d.arc((440 - r, 820 - r, 440 + r, 820 + r), a0, a0 + 200, fill=(120, 160, 90, 120 + 20 * j), width=8)
    # дымка запаха — растёт
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    dl.rectangle((x0, y0, x1, y1), fill=(150, 170, 80, int(110 * k)))
    c2 = cl((u - dur * 0.6) / (dur * 0.35))
    if c2 > 0:
        dl.rectangle((x1, y0, x1 + 24 + int(276 * c2), y1), fill=(150, 170, 80, int(110 * c2)))
    lay = lay.filter(ImageFilter.GaussianBlur(20))
    im.alpha_composite(lay)
    for j in range(4):   # волнистые линии
        ph = (t * 0.5 + j / 4) % 1
        xs = lerp(300, x1 + 200 * c2, ph)
        pts = [(xs + 20 * math.sin(yy / 25 + t * 5 + j), yy) for yy in range(700, 960, 10)]
        d = ImageDraw.Draw(im)
        d.line(pts, fill=(130, 160, 60, int(220 * (1 - ph))), width=8)
    # таймер «2 мин»
    m = 2 * eo(u / (dur * 0.6))
    panel(im, (200, 1340, 880, 1560), (20, 24, 40, 230), ol=WHITE, w=4)
    label(im, 'весь воздух комнаты', 540, 1395, 46, (180, 190, 220), 0)
    label(im, f'{m:.1f} мин'.replace('.', ','), 540, 1490, 90, GAS, 0)
    if c2 > 0.3:
        put(im, puff_face_nose(), 910, 1000 + 8 * math.sin(t * 4), pop(u - dur * 0.75))
    return im


@functools.lru_cache(2)
def puff_face_nose():
    """Сосед в коридоре зажимает нос."""
    im, d = canvas(240, 300)
    rrect(d, (50, 190, 190, 300), 40, (160, 120, 200))
    oval(d, 120, 120, 80, 84, SKIN)
    for s in (-1, 1):
        d.line(P(120 + s * 30 - 12, 100, 120 + s * 30 + 12, 112), fill=INK, width=6 * SS)
    oval(d, 120, 150, 22, 18, (240, 170, 150))
    thick(d, [(60, 250), (110, 152)], 22, SKIN)
    d.arc(P(92, 170, 148, 200), 200, 340, fill=INK, width=5 * SS)
    return done(im)


@functools.lru_cache(2)
def bucket_spr():
    im, d = canvas(220, 220)
    d.polygon([tuple(P(30, 60)), tuple(P(190, 60)), tuple(P(170, 210)), tuple(P(50, 210))], fill=(90, 160, 240),
              outline=INK, width=6 * SS)
    d.arc(P(30, 0, 190, 120), 180, 360, fill=INK, width=6 * SS)
    oval(d, 110, 62, 80, 14, (200, 230, 255))
    return done(im)


@functools.lru_cache(2)
def bin_spr():
    im, d = canvas(300, 360)
    d.polygon([tuple(P(30, 60)), tuple(P(270, 60)), tuple(P(240, 350)), tuple(P(60, 350))], fill=(110, 120, 130),
              outline=INK, width=6 * SS)
    for x in (100, 150, 200):
        d.line(P(x, 90, x - 6 + (x - 150) * 0.1, 320), fill=(80, 90, 100), width=6 * SS)
    rrect(d, (14, 40, 286, 76), 12, (90, 100, 110))
    return done(im)


def sc14(t):
    """Уборка полдня; вентилятор — в мусорку."""
    u = t - S['L14']
    dur = E['L14'] - S['L14']
    im = grad_t((214, 228, 246), (200, 216, 240))
    room_front(im, t, dirty=False)
    # грязь уходит по мере уборки
    clean = eo(u / (dur * 0.6))
    for i, (x, y, r, seed, grp) in enumerate(SPLATS):
        if (i / len(SPLATS)) > clean:
            put(im, splat_spr(seed % 12), x, y, r / 40, (seed * 37) % 360)
    # часы: стрелки крутятся
    d = ImageDraw.Draw(im)
    cx, cy, R = 850, 300, 110
    d.ellipse((cx - R - 8, cy - R - 8, cx + R + 8, cy + R + 8), fill=INK)
    d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=WHITE)
    a = math.radians(-90 + u * 720)
    d.line((cx, cy, cx + math.cos(a) * 90, cy + math.sin(a) * 90), fill=INK, width=8)
    a = math.radians(-90 + u * 60)
    d.line((cx, cy, cx + math.cos(a) * 60, cy + math.sin(a) * 60), fill=RED, width=10)
    label(im, 'полдня', cx, cy + R + 50, 50, INK, 0)
    # герой с ведром
    sway = 30 * math.sin(t * 10)
    hero(im, 330 + sway * 0.2, 1500, 0.8, 'strain' if u < dur * 0.6 else 'calm', 0, chair=False)
    put(im, bucket_spr(), 140, 1700, 0.9)
    d.ellipse((330 + 180 + sway - 40, 1180 - 30, 330 + 180 + sway + 40, 1180 + 30), fill=(250, 220, 80),
              outline=INK, width=5)
    # вентилятор летит в мусорку
    v = u - dur * 0.6
    put(im, bin_spr(), 860, 1660, 0.9)
    if v > 0:
        k = eo(v / 0.9)
        fx = lerp(560, 860, k)
        fy = lerp(1200, 1560, k) - 300 * math.sin(math.pi * k)
        put(im, grille_spr(), fx, fy, 0.45 * (1 - 0.3 * k), 300 * k)
        if k >= 1:
            stamp(im, 'НА ВЫБРОС', 740, 1380, v - 0.9, RED, 64, 8)
    else:
        fan(im, 620, 1250, t, 0.55, 0.0)
    return im


def sc15(t):
    """Английская идиома."""
    u = t - S['L15']
    dur = E['L15'] - S['L15']
    im = blueprint(t, (60, 30, 40), (90, 40, 40))
    # хаос вокруг: крутятся предметы
    for i in range(8):
        a = t * (0.8 + i * 0.1) + i
        r = 380 + 40 * math.sin(t + i)
        put(im, splat_spr(i), 540 + math.cos(a) * r, 1000 + math.sin(a) * r * 1.3, 0.6, t * 90 + i * 40)
    panel(im, (60, 560, 1020, 1060), (255, 252, 240, 250))
    label(im, '🇬🇧' if False else 'ИДИОМА', 540, 630, 50, (150, 140, 130), 0)
    label(im, 'SH*T HITS', 540, 760, 120, INK, 0, pop(u - 0.4))
    label(im, 'THE FAN', 540, 900, 120, FAN_BLUE, 0, pop(u - 0.6))
    v = u - dur * 0.55
    if v > 0:
        panel(im, (140, 1180, 940, 1420), (240, 74, 74, 250))
        label(im, '= всё пошло', 540, 1255, 70, WHITE, 0, pop(v))
        label(im, 'к чертям', 540, 1350, 70, WHITE, 0, pop(v - 0.1))
    fan(im, 540, 1660, t, 0.6, 1.0, stand=False)
    pts = []
    for i, (dx, dy, r) in enumerate(DROPS[:80]):
        ph = (t * 1.1 + i * 0.0125) % 1
        a = -math.pi / 2 + dx * 0.9
        pts.append((540 + math.cos(a) * (150 + 500 * ph), 1660 + math.sin(a) * (110 + 90 * ph), r * (1 - 0.5 * ph)))
    drops(im, pts)
    return im


def sc16(t):
    """Финал: грязная комната, открывается дверь — мама."""
    u = t - S['L16']
    dur = E['L16'] - S['L16']
    im = grad_t((214, 228, 246), (200, 216, 240))
    room_front(im, t + 100)                     # все брызги на месте
    k = cl((u - 1.6) / 0.5)
    # дверь справа открывается: полоса света + силуэт
    d = ImageDraw.Draw(im)
    dx0, dx1 = 760, 1060
    d.rectangle((dx0, 300, dx1, 1500), fill=(120, 80, 50), outline=INK, width=8)
    if k > 0:
        w = int((dx1 - dx0) * k)
        d.rectangle((dx0, 300, dx0 + w, 1500), fill=(255, 244, 200))
        # силуэт мамы
        mx = dx0 + w * 0.5
        d.ellipse((mx - 60, 500, mx + 60, 640), fill=(40, 30, 50))
        d.polygon([(mx - 110, 1500), (mx - 70, 680), (mx + 70, 680), (mx + 110, 1500)], fill=(40, 30, 50))
        d.ellipse((mx - 70, 440, mx + 70, 560), fill=(40, 30, 50))            # причёска
        label(im, '!', mx + 120, 440, 160, RED, 10, pop(u - 1.9), 8)
    hero(im, 360, 1500, 0.95, 'happy' if u < 1.6 else 'scared', talk_open(t, 'L16') if u < 1.6 else 0, chair=False)
    for i in range(6):
        rnd = random.Random(i + 3)
        put(im, splat_spr(i), 360 + rnd.uniform(-70, 70), 1500 - 330 + rnd.uniform(-60, 50), 0.22)
    if u > 2.2:
        label(im, 'МАМА?!', 360, 820, 120, YEL, 12, pop(u - 2.2), -6)
    return im


SCENES = [('L01', sc01), ('L02', sc02), ('L03', sc03), ('L04', sc04), ('L05', sc05), ('L06', sc06), ('L07', sc07),
          ('L08', sc08), ('L09', sc09), ('L10', sc10), ('L11', sc11), ('L12', sc12), ('L13', sc13), ('L14', sc14),
          ('L15', sc15), ('L16', sc16)]
STARTS = [0.0] + [S[k] - 0.12 for k, _ in SCENES[1:]]
WIPES = {'L05', 'L09', 'L11', 'L14', 'L16'}


def splash_wipe(im, u, dur=0.6):
    """Переход «шлепок»: коричневые кляксы закрывают кадр и исчезают."""
    k = 1 - abs(u) / (dur / 2)
    if k <= 0:
        return
    k = sm(k)
    for i in range(12):
        rnd = random.Random(i + 900)
        put(im, splat_spr(i), rnd.uniform(-60, W + 60), rnd.uniform(-60, H + 60), 0.3 + 4.0 * k * rnd.uniform(0.8, 1.1),
            rnd.uniform(0, 360))


def scene_index(t):
    i = 0
    for k, s in enumerate(STARTS):
        if t >= s:
            i = k
    return i


def render_at(t):
    i = scene_index(t)
    key, fn = SCENES[i]
    im = fn(t)
    u = t - STARTS[i]
    if i > 0 and key not in WIPES and u < 0.22:
        s = 1 + 0.07 * (1 - eo(u / 0.22))
        w2, h2 = int(W / s), int(H / s)
        im = im.crop(((W - w2) // 2, (H - h2) // 2, (W - w2) // 2 + w2, (H - h2) // 2 + h2)).resize((W, H), Image.BILINEAR)
        if u < 0.06:
            im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(120 * (1 - u / 0.06)))))
    for k, s in enumerate(STARTS[1:], 1):
        if SCENES[k][0] in WIPES and abs(t - s) < 0.3:
            splash_wipe(im, t - s, 0.6)
    draw_caps(im, t)
    end = DUR - t
    if end < 0.8:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.8)))))
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
