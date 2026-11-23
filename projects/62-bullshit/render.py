"""«Что будет, если постоянно нести х*йню»: 2D, всё кодом. Кадр — чистая функция времени. Без рекламы.

    python -B projects/62-bullshit/render.py --video out.mp4      # видеоряд (вызывает build.py)
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
from kit import (W, H, FPS, INK, YEL, RED, WHITE, SKIN, HOOD, PANTS, GAS, POO, POO_D, S, E, DUR, cl, sm, eo, eio,
                 lerp, mix, noise, font, text_spr, put, canvas, done, P, oval, rrect, thick, grad_t, hero, head_spr,
                 body_spr, talk_open, panel, label, counter_text, pop, bar, stamp, draw_caps, blueprint, puff_spr,
                 gauge)  # noqa: E402
from props import room_bg, check, friend_spr  # noqa: E402
from events import AD_STOPS  # noqa: E402

SS = 2
BR = banner.Breaks(AD_STOPS, cy=H / 2)
PINK = (246, 150, 170)
PINK_D = (210, 100, 130)
NONSENSE = ['БЛА-БЛА', 'ФАКТ!', '100%', 'ЗУБ ДАЮ', 'Я ЧИТАЛ', 'ЗЕМЛЯ — КУБ', 'КОТЫ — ШПИОНЫ', 'ВАЙ-ФАЙ ЛЕЧИТ',
            'ЛУНЫ НЕТ', 'Я ЭКСПЕРТ', 'ИНФА 100', 'МНЕ БРАТ СКАЗАЛ']


def D(k):
    return E[k] - S[k]


# ------------------------------------------------------------------ реквизит
def speech_bubble(im, cx, cy, text, scale=1.0, rot=0.0, alpha=1.0, col=INK):
    spr = text_spr(text, 46, col, 'Heavy', 0)
    w, h = spr.size
    b = Image.new('RGBA', (w + 60, h + 70), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((4, 4, w + 56, h + 40), 26, fill=WHITE + (255,), outline=INK + (255,), width=5)
    d.polygon([(30, h + 38), (60, h + 38), (24, h + 66)], fill=WHITE + (255,), outline=INK + (255,))
    d.line((32, h + 38, 58, h + 38), fill=WHITE + (255,), width=6)
    b.alpha_composite(spr, (30, 18))
    put(im, b, cx, cy, scale, rot, alpha)


def nonsense_stream(im, t, x0, y0, rate=2.2, spread=380, n=6, up=900, seed=0):
    """Пузыри чепухи вылетают изо рта и уплывают вверх."""
    for i in range(n):
        ph = (t * rate / n + i / n) % 1
        rnd = random.Random(i + seed * 31 + int(t * rate / n + i / n) * 7)
        txt = NONSENSE[(i + int(t * rate / n + i / n) * 3 + seed) % len(NONSENSE)]
        x = x0 + rnd.uniform(-spread, spread) * ph
        y = y0 - up * ph
        a = cl(ph / 0.1) * (1 - cl((ph - 0.8) / 0.2))
        speech_bubble(im, x, y, txt, 0.5 + 0.5 * eo(ph / 0.2), rnd.uniform(-10, 10), a)


@functools.lru_cache(4)
def brain_spr(mode='run', glasses=False):
    im, d = canvas(300, 320)
    # ножки
    if mode != 'none':
        for s, ph in ((-1, 0), (1, 1)):
            ang = 0.5 if (mode == 'run') == bool(ph) else -0.5
            x0, y0 = 150 + s * 40, 210
            thick(d, [(x0, y0), (x0 + math.sin(ang) * 50, y0 + 90)], 18, PINK_D)
            oval(d, x0 + math.sin(ang) * 50 + 14, y0 + 96, 22, 12, INK, None)
    oval(d, 150, 130, 130, 100, PINK)
    for k in range(5):   # извилины
        d.arc(P(40 + k * 40, 60, 110 + k * 40, 160), 200, 340, fill=PINK_D, width=6 * SS)
        d.arc(P(50 + k * 38, 110, 120 + k * 38, 200), 20, 160, fill=PINK_D, width=6 * SS)
    d.line(P(150, 40, 150, 220), fill=PINK_D, width=6 * SS)
    for s in (-1, 1):
        oval(d, 150 + s * 40, 120, 18, 22, WHITE, INK, 4)
        oval(d, 150 + s * 40 + 3, 124, 8, 9, INK, None)
    if glasses:
        for s in (-1, 1):
            oval(d, 150 + s * 40, 120, 30, 22, (30, 30, 40), INK, 3)
        d.line(P(120, 118, 180, 118), fill=INK, width=5 * SS)
    d.arc(P(120, 150, 180, 190), 20, 160, fill=INK, width=5 * SS)
    return done(im)


@functools.lru_cache(2)
def mouth_spr(open_=True):
    im, d = canvas(320, 260)
    for s in (-1, 1):   # ножки
        thick(d, [(160 + s * 40, 170), (160 + s * 70, 250)], 18, (200, 60, 70))
    oval(d, 160, 110, 140, 80, (230, 70, 80))
    if open_:
        oval(d, 160, 110, 100, 46, (90, 20, 30), None)
        rrect(d, (80, 70, 240, 92), 6, WHITE)
        oval(d, 170, 135, 40, 18, (240, 120, 130), None)
    else:
        d.line(P(40, 110, 280, 110), fill=(120, 30, 40), width=8 * SS)
    return done(im)


@functools.lru_cache(4)
def mom_spr(mode='listen'):
    im, d = canvas(460, 620)
    cx, cy = 230, 230
    rrect(d, (cx - 180, cy + 150, cx + 180, 620), 90, (180, 120, 200))       # халат
    for k in range(5):
        oval(d, cx - 120 + k * 60, cy + 260, 14, 14, (240, 200, 240), None)
    oval(d, cx, cy, 116, 124, SKIN)
    for k in range(5):   # бигуди
        a = math.radians(200 + k * 35)
        oval(d, cx + math.cos(a) * 110, cy - 30 + math.sin(a) * 110, 30, 30, (250, 150, 180), INK, 4)
    d.chord(P(cx - 116, cy - 130, cx + 116, cy - 10), 180, 360, fill=(140, 90, 60))
    for s in (-1, 1):
        if mode == 'sigh':
            d.arc(P(cx + s * 42 - 20, cy - 16, cx + s * 42 + 20, cy + 14), 200, 340, fill=INK, width=6 * SS)
        else:
            oval(d, cx + s * 42, cy - 6, 12, 14, INK, None)
        d.line(P(cx + s * 42 - 22, cy - 40, cx + s * 42 + 22, cy - 40 + (8 if mode == 'sigh' else 0) * s), fill=INK,
               width=6 * SS)
    if mode == 'sigh':
        oval(d, cx, cy + 60, 22, 16, (140, 50, 60))
    else:
        d.line(P(cx - 30, cy + 60, cx + 30, cy + 60), fill=INK, width=6 * SS)
    return done(im)


@functools.lru_cache(2)
def hr_spr(stamp_up=False):
    im, d = canvas(460, 600)
    cx, cy = 230, 220
    rrect(d, (cx - 180, cy + 150, cx + 180, 600), 70, (60, 70, 90))         # пиджак
    d.polygon([tuple(P(cx, cy + 150)), tuple(P(cx - 40, cy + 300)), tuple(P(cx, cy + 340)), tuple(P(cx + 40, cy + 300))],
              fill=WHITE)
    oval(d, cx, cy, 110, 118, SKIN)
    d.chord(P(cx - 116, cy - 130, cx + 116, cy - 10), 180, 360, fill=(60, 40, 30))
    for s in (-1, 1):
        oval(d, cx + s * 40, cy - 6, 26, 20, (220, 236, 255), INK, 5)
        oval(d, cx + s * 40, cy - 4, 7, 8, INK, None)
    d.line(P(cx - 14, cy - 6, cx + 14, cy - 6), fill=INK, width=5 * SS)
    d.arc(P(cx - 34, cy + 40, cx + 34, cy + 76), 20, 160, fill=INK, width=6 * SS)
    return done(im)


@functools.lru_cache(2)
def scientist_spr():
    im, d = canvas(440, 600)
    cx, cy = 220, 220
    rrect(d, (cx - 170, cy + 150, cx + 170, 600), 70, (250, 250, 252))
    oval(d, cx, cy, 108, 116, SKIN)
    for k in range(7):   # растрёпанные волосы
        a = math.radians(190 + k * 26)
        d.line(P(cx + math.cos(a) * 90, cy + math.sin(a) * 90, cx + math.cos(a) * 150, cy + math.sin(a) * 150),
               fill=(220, 220, 225), width=18 * SS)
    for s in (-1, 1):
        oval(d, cx + s * 40, cy - 4, 28, 22, (230, 240, 255), INK, 6)
        oval(d, cx + s * 40, cy - 2, 7, 8, INK, None)
    d.line(P(cx - 12, cy - 4, cx + 12, cy - 4), fill=INK, width=5 * SS)
    d.arc(P(cx - 30, cy + 50, cx + 30, cy + 80), 200, 340, fill=INK, width=6 * SS)
    return done(im)


def phone(im, cx, cy, w=560, h=1000, scale=1.0):
    d = ImageDraw.Draw(im)
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle((x0 - 18, y0 - 18, x0 + w + 18, y0 + h + 18), 70, fill=(30, 30, 40), outline=INK, width=6)
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), 56, fill=(232, 238, 246))
    d.rounded_rectangle((cx - 80, y0 + 14, cx + 80, y0 + 44), 15, fill=(30, 30, 40))
    return x0, y0


def msg(im, x, y, text, me=True, alpha=1.0, size=40):
    spr = text_spr(text, size, WHITE if me else INK, 'Bold', 0)
    w, h = spr.size
    b = Image.new('RGBA', (w + 44, h + 30), (0, 0, 0, 0))
    ImageDraw.Draw(b).rounded_rectangle((0, 0, w + 43, h + 29), 24, fill=((70, 130, 240) if me else (255, 255, 255)) + (255,))
    b.alpha_composite(spr, (22, 15))
    put(im, b, x, y, 1.0, 0, alpha, anchor=(1.0 if me else 0.0, 0.0))
    return h + 30


def burger_bg(t, top=(250, 236, 210), bot=(240, 220, 190)):
    return grad_t(top, bot)


# ------------------------------------------------------------------ сцены
def sc01(t):
    u = t - S['B01']
    im = blueprint(t, (40, 26, 70), (80, 30, 70))
    hero(im, 540, 1500, 1.0, 'smug' if u < 3 else 'happy', talk_open(t, 'B01') or int(t * 9) % 2, chair=True)
    nonsense_stream(im, t, 540, 1080, rate=2.6, spread=420, n=7, up=420)
    label(im, 'НЕСТИ Х*ЙНЮ', 540, 440, 120, YEL, 12, 1 + 0.03 * math.sin(t * 6), -4)
    label(im, '24/7', 540, 570, 90, WHITE, 10, 1 + 0.05 * math.sin(t * 8 + 1), 3)
    return im


def sc02(t):
    u = t - S['B02']
    dur = D('B02')
    im = blueprint(t, (24, 30, 64), (50, 30, 80))
    words = 16000 * eo(u / 2.4)
    panel(im, (100, 400, 980, 640), (255, 214, 64, 250))
    label(im, counter_text(words), 540, 490, 140, INK, 0)
    label(im, 'слов в день', 540, 595, 56, INK, 0)
    v = u - dur * 0.55
    gauge(im, 540, 1000, 260, 100 * eo(v / 1.2) if v > 0 else 3, 100, 'Х*ЙНЕМЕТР', '%', t, red_from=60)
    hero(im, 540, 1720, 0.5, 'smug', talk_open(t, 'B02'), chair=False)
    nonsense_stream(im, t, 540, 1520, rate=4.0, spread=420, n=6, up=380, seed=2)
    return im


@functools.lru_cache(2)
def book_spr():
    im, d = canvas(420, 90)
    rrect(d, (6, 6, 414, 84), 10, (150, 40, 40))
    d.rectangle(P(30, 6, 46, 84), fill=(220, 180, 80))
    d.text(P(230, 45), 'ВОЙНА И МИР', font=font(34 * SS), fill=(250, 220, 150), anchor='mm')
    return done(im)


def sc03(t):
    u = t - S['B03']
    dur = D('B03')
    im = grad_t((246, 236, 216), (226, 210, 186))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1700, W, H), fill=(170, 120, 84))
    n = int(10 * eo((u - 0.6) / (dur * 0.5)))
    for k in range(n):
        put(im, book_spr(), 540 + (k % 2) * 16 - 8, 1650 - k * 84, 1.0, (k % 3 - 1) * 1.5)
    v = 5840000 * eo(u / 2.0)
    panel(im, (120, 380, 960, 560), (255, 255, 255, 240))
    label(im, counter_text(v) + ' слов', 540, 470, 90, INK, 0)
    label(im, f'×{n}', 880, 1100 - n * 20, 120, RED, 10)
    if u > dur * 0.72:
        # паутина и «0 читателей»
        d = ImageDraw.Draw(im)
        cx, cy = 900, 650
        for k in range(8):
            a = k * math.pi / 4
            d.line((cx, cy, cx + math.cos(a) * 160, cy + math.sin(a) * 160), fill=(200, 200, 210), width=3)
        for r in (50, 100, 150):
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(200, 200, 210), width=3)
        stamp(im, 'ЧИТАТЕЛЕЙ: 0', 360, 700, u - dur * 0.72, RED, 70, -6)
    return im


def sc04(t):
    u = t - S['B04']
    dur = D('B04')
    im = grad_t((200, 220, 250), (170, 196, 240))
    x0, y0 = phone(im, 540, 1020, 700, 1000)
    d = ImageDraw.Draw(im)
    d.rectangle((x0, y0 + 60, x0 + 700, y0 + 160), fill=(250, 252, 255))
    label(im, 'Друзья (3)', 540, y0 + 110, 46, INK, 0)
    y = y0 + 200
    seq = [('Я понял, Земля — куб', True, 0.2), ('А коты — шпионы', True, 0.6), ('И вай-фай лечит', True, 1.0),
           ('ага', False, 1.8), ('Я серьёзно!!!', True, 2.4), ('Это ФАКТ', True, 2.7)]
    for txt, me, t0 in seq:
        if u > t0:
            a = cl((u - t0) / 0.15)
            hh = msg(im, x0 + 670 if me else x0 + 30, y, txt, me, a, 50)
            y += hh + 18
    v = u - dur * 0.75
    if v > 0:
        # колокольчик перечёркнут
        cx, cy = 300, 1700
        k = pop(v)
        d = ImageDraw.Draw(im)
        r = 120 * k
        if r > 10:
            d.ellipse((cx - r - 20, cy - r - 20, cx + r + 20, cy + r + 20), fill=(240, 74, 74, 240))
            d.pieslice((cx - r * 0.6, cy - r * 0.7, cx + r * 0.6, cy + r * 0.5), 180, 360, fill=WHITE)
            d.rectangle((cx - r * 0.6, cy - r * 0.1, cx + r * 0.6, cy + r * 0.35), fill=WHITE)
            d.ellipse((cx - r * 0.15, cy + r * 0.35, cx + r * 0.15, cy + r * 0.6), fill=WHITE)
            d.line((cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8), fill=INK, width=int(18 * k))
        label(im, 'БЕЗ ЗВУКА', 700, 1700, 80, RED, 8, pop(v - 0.2), -4)
    return im


def sc05(t):
    u = t - S['B05']
    dur = D('B05')
    im = room_bg(t)
    sigh = dur * 0.45 < u < dur * 0.7
    put(im, mom_spr('sigh' if sigh else 'listen'), 790, 1300 + (10 * math.sin(u * 3) if sigh else 0), 1.15)
    hero(im, 280, 1600, 0.75, 'happy', talk_open(t, 'B05') or int(t * 9) % 2, chair=False)
    nonsense_stream(im, t, 280, 1200, rate=3.0, spread=200, n=5, up=500, seed=5)
    if sigh:
        label(im, '*вздох*', 790, 700, 70, INK, 0, pop(u - dur * 0.45), 5)
    v = u - dur * 0.72
    if v > 0:
        panel(im, (520, 420, 1020, 700), (255, 255, 255, 245))
        put(im, text_spr('ЗАПИСЬ К ВРАЧУ', 44, INK, 'Heavy', 0), 770, 490, pop(v))
        put(im, text_spr('завтра, 9:00', 40, (90, 90, 110), 'Bold', 0), 770, 560, pop(v - 0.1))
        put(im, text_spr('СРОЧНО', 50, RED, 'Heavy', 0), 770, 640, pop(v - 0.2), -6)
    return im


def sc06(t):
    """Гонка: рот впереди, мозг отстаёт."""
    u = t - S['B06']
    dur = D('B06')
    im = grad_t((140, 200, 250), (210, 236, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1300, W, H), fill=(200, 110, 80))                 # беговая дорожка
    for k in range(4):
        d.line((0, 1380 + k * 140, W, 1380 + k * 140), fill=WHITE, width=6)
    off = (t * 900) % 200
    for x in range(-200, W + 200, 200):
        d.line((x - off, 1300, x - off - 60, H), fill=(220, 140, 110), width=6)
    bob = abs(math.sin(t * 14)) * 30
    put(im, mouth_spr(int(t * 10) % 2 == 0), 800, 1200 - bob, 1.1, -5)
    gap = 300 + 80 * math.sin(u * 1.5)
    put(im, brain_spr('run' if int(t * 8) % 2 else 'run2'), 800 - gap - 120, 1210 - abs(math.sin(t * 12 + 1)) * 26, 1.0, -8)
    for k in range(3):   # пот
        x = 800 - gap - 240 - k * 30
        y = 1100 + ((t * 300 + k * 40) % 120)
        d.ellipse((x - 10, y - 14, x + 10, y + 14), fill=(120, 190, 250))
    nonsense_stream(im, t, 860, 1060, rate=3.5, spread=200, n=5, up=600, seed=6)
    if u > dur * 0.5:
        d = ImageDraw.Draw(im)
        y = 1560
        d.line((800 - gap - 120, y, 800, y), fill=RED, width=8)
        for x in (800 - gap - 120, 800):
            d.line((x, y - 24, x, y + 24), fill=RED, width=8)
        label(im, 'отстаёт на 2 предложения', 540, 1650, 52, WHITE, 6, pop(u - dur * 0.5))
    label(im, 'РОТ', 800, 950, 60, RED, 6)
    label(im, 'МОЗГ', 800 - gap - 120, 960, 60, PINK_D, 6)
    return im


def sc07(t):
    """20 % энергии — мозг уходит в отпуск на море."""
    u = t - S['B07']
    dur = D('B07')
    split = dur * 0.4
    if u < split:
        im = blueprint(t, (24, 30, 64), (40, 30, 70))
        put(im, brain_spr('none'), 540, 760, 1.6)
        # батарейка
        d = ImageDraw.Draw(im)
        bx, by = 240, 1180
        d.rounded_rectangle((bx, by, bx + 600, by + 220), 30, outline=WHITE, width=10)
        d.rectangle((bx + 600, by + 70, bx + 640, by + 150), fill=WHITE)
        k = eo(u / 1.0)
        d.rounded_rectangle((bx + 20, by + 20, bx + 20 + 560 * 0.2 * k * 5 * 0.2 + 1, by + 200), 16, fill=GAS)
        label(im, '20%', 540, by + 110, 110, WHITE, 8)
        label(im, 'энергии тела', 540, by + 300, 56, WHITE, 6)
        return im
    v = u - split
    im = grad_t((120, 200, 250), (230, 246, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((800, 300, 980, 480), fill=(255, 220, 90))
    d.rectangle((0, 1150, W, 1400), fill=(60, 150, 220))
    for k in range(6):
        y = 1180 + k * 40
        d.arc((-40 + (t * 60 + k * 70) % 160, y - 20, 1120, y + 20), 0, 180, fill=(200, 230, 255), width=4)
    d.rectangle((0, 1400, W, H), fill=(246, 220, 160))
    # зонтик и шезлонг
    d.line((260, 1400, 260, 1040), fill=INK, width=10)
    d.pieslice((60, 960, 460, 1160), 180, 360, fill=RED, outline=INK, width=6)
    walk = eo(v / 1.2)
    put(im, brain_spr('run', glasses=True), lerp(1150, 520, walk), 1480 - abs(math.sin(t * 10)) * 20 * (walk < 1), 1.45)
    # чемодан
    d = ImageDraw.Draw(im)
    sx = lerp(1150, 520, walk) + 210
    d.rounded_rectangle((sx - 70, 1490, sx + 70, 1630), 14, fill=(240, 150, 60), outline=INK, width=6)
    d.arc((sx - 30, 1470, sx + 30, 1520), 180, 360, fill=INK, width=8)
    panel(im, (120, 1680, 960, 1820), (255, 255, 255, 240))
    label(im, 'МОЗГ В ОТПУСКЕ', 540, 1750, 70, INK, 0, pop(v - 0.3))
    # чайки
    for k in range(3):
        x = (t * 80 + k * 300) % (W + 200) - 100
        y = 600 + k * 70 + 20 * math.sin(t * 3 + k)
        d.arc((x - 30, y - 10, x, y + 20), 200, 340, fill=INK, width=5)
        d.arc((x, y - 10, x + 30, y + 20), 200, 340, fill=INK, width=5)
    return im


def sc08(t):
    u = t - S['B08']
    dur = D('B08')
    im = grad_t((236, 240, 246), (210, 218, 232))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1450, W, H), fill=(160, 170, 190))
    hired = dur * 0.45
    put(im, hr_spr(), 780, 1180, 1.0)
    d.rounded_rectangle((420, 1380, 1080, 1480), 14, fill=(150, 100, 70), outline=INK, width=8)
    hero(im, 230, 1640, 0.85, 'smug', talk_open(t, 'B08'), chair=True)
    if u < hired:
        speech_bubble(im, 330, 700, 'Я УМЕЮ ЛЕТАТЬ', 1.3, -3, cl(u / 0.2))
    else:
        v = u - hired
        stamp(im, 'ПРИНЯТ!', 760, 760, v, (60, 170, 80), 100, -8)
    v = u - dur * 0.72
    if v > 0:
        panel(im, (140, 420, 940, 560), (240, 74, 74, 250))
        label(im, 'ОТДЕЛ МАРКЕТИНГА', 540, 490, 60, WHITE, 0, pop(v))
    return im


@functools.lru_cache(4)
def topic_spr(kind):
    im, d = canvas(360, 360)
    if kind == 0:   # монета
        oval(d, 180, 180, 150, 150, (245, 180, 40))
        oval(d, 180, 180, 115, 115, (250, 205, 80), (200, 140, 30), 6)
        d.text(P(180, 180), '₿', font=font(150 * SS), fill=(200, 130, 20), anchor='mm')
    elif kind == 1:  # коллайдер
        oval(d, 180, 180, 150, 150, (220, 226, 240))
        oval(d, 180, 180, 110, 110, (40, 50, 80), INK, 4)
        oval(d, 180, 180, 100, 100, (220, 226, 240), None)
        for k in range(6):
            a = k * math.pi / 3
            oval(d, 180 + math.cos(a) * 130, 180 + math.sin(a) * 130, 12, 12, (90, 160, 250), None)
        d.line(P(40, 320, 120, 260), fill=(160, 120, 80), width=14 * SS)       # гаечный ключ
        oval(d, 128, 254, 22, 22, (160, 120, 80), None)
    else:            # кот
        org = (246, 160, 70)
        for s in (-1, 1):
            d.polygon([tuple(P(180 + s * 60, 120)), tuple(P(180 + s * 110, 30)), tuple(P(180 + s * 20, 90))], fill=org,
                      outline=INK, width=6 * SS)
        oval(d, 180, 190, 140, 120, org)
        for s in (-1, 1):
            oval(d, 180 + s * 50, 170, 20, 24, (180, 230, 90), INK, 4)
            oval(d, 180 + s * 50, 172, 6, 18, INK, None)
        oval(d, 180, 220, 12, 9, (230, 110, 120), None)
    return done(im)


def sc09(t):
    u = t - S['B09']
    dur = D('B09')
    im = grad_t((30, 20, 50), (70, 30, 90))
    d = ImageDraw.Draw(im)
    # сцена и прожекторы
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for s in (-1, 1):
        dl.polygon([(540 + s * 500, 0), (540 + s * 420, 0), (540 + s * 40, 1700), (540 + s * 300, 1700)],
                   fill=(255, 240, 180, 50))
    im.alpha_composite(lay)
    d.rectangle((0, 1700, W, H), fill=(90, 40, 40))
    # экран с темами
    d.rounded_rectangle((140, 380, 940, 900), 20, fill=(20, 24, 40), outline=WHITE, width=6)
    idx = 0 if u < dur * 0.35 else (1 if u < dur * 0.65 else 2)
    names = ['КРИПТА', 'РЕМОНТ КОЛЛАЙДЕРА', 'ВОСПИТАНИЕ КОТОВ']
    seg_t = [0, dur * 0.35, dur * 0.65][idx]
    put(im, topic_spr(idx), 540, 610, pop(u - seg_t, 0.3) * 0.95)
    label(im, names[idx], 540, 840, 52, YEL, 0, pop(u - seg_t - 0.1))
    hero(im, 540, 1560, 0.85, 'smug', talk_open(t, 'B09'), chair=False)
    d = ImageDraw.Draw(im)
    d.line((430, 1080, 380, 940), fill=(50, 50, 60), width=10)            # указка
    panel(im, (200, 1740, 880, 1860), (255, 214, 64, 250))
    label(im, 'ЭКСПЕРТ ВО ВСЁМ', 540, 1800, 60, INK, 0)
    return im


def sc10(t):
    """Миллион подписчиков, х*йня распространяется сетью."""
    u = t - S['B10']
    dur = D('B10')
    im = grad_t((14, 20, 40), (30, 30, 70))
    d = ImageDraw.Draw(im)
    subs = 1000000 * eo(u / 2.0)
    panel(im, (120, 380, 960, 620), (255, 255, 255, 245))
    label(im, counter_text(subs), 540, 470, 120, RED, 0)
    label(im, 'подписчиков', 540, 575, 50, INK, 0)
    # сеть: узлы загораются волной от центра
    cx, cy = 540, 1260
    k = eo((u - dur * 0.55) / (dur * 0.45))
    nodes = [(cx, cy)] + [(cx + math.cos(i * 2.4) * (60 + i * 9), cy + math.sin(i * 2.4) * (60 + i * 9) * 0.9)
                          for i in range(1, 60)]
    for i, (x, y) in enumerate(nodes[1:], 1):
        j = int(i * 0.6)
        px, py = nodes[j]
        lit = (i / 60) < k
        d.line((px, py, x, y), fill=(255, 90, 90) if lit else (70, 80, 120), width=3)
    for i, (x, y) in enumerate(nodes):
        lit = (i / 60) < k
        r = 12 if i else 30
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 90, 90) if lit else (90, 100, 150))
    put(im, head_spr('smug', 0, 0), cx, cy - 10, 0.35)
    if u > dur * 0.55:
        label(im, 'СКОРОСТЬ ИНТЕРНЕТА', 540, 1820, 60, YEL, 6, pop(u - dur * 0.55))
    if u > dur * 0.3:
        label(im, '«ВЕРИМ!»', 840, 760, 70, WHITE, 6, pop(u - dur * 0.3), 8)
    return im


def sc11(t):
    """Закон Брандолини: опровергнуть в 10 раз труднее."""
    u = t - S['B11']
    dur = D('B11')
    im = blueprint(t, (24, 34, 60), (40, 40, 80))
    put(im, scientist_spr(), 260 + 6 * math.sin(t * 3), 1500, 0.9)
    put(im, scientist_spr(), 820 + 6 * math.sin(t * 3 + 1), 1520, 0.85)
    v = u - dur * 0.25
    if v > 0:
        panel(im, (80, 380, 1000, 520), (255, 255, 255, 240))
        label(im, 'ЗАКОН БРАНДОЛИНИ', 540, 450, 66, INK, 0, pop(v))
    w = u - dur * 0.5
    if w > 0:
        bar(im, 90, 660, 860, 56, 0.1 * eo(w / 0.6), (255, 120, 120), 'Сказать х*йню', '1', 1.0)
        bar(im, 90, 860, 860, 56, 0.85 * eo((w - 0.5) / 1.4), (120, 200, 250), 'Опровергнуть х*йню', '×10', cl((w - 0.5) / 0.3))
    # пот учёных
    d = ImageDraw.Draw(im)
    for k in range(4):
        x = 260 + (k % 2) * 560 + 90
        y = 1180 + ((t * 260 + k * 50) % 140)
        d.ellipse((x - 9, y - 13, x + 9, y + 13), fill=(120, 190, 250))
    return im


def sc12(t):
    u = t - S['B12']
    dur = D('B12')
    im = grad_t((236, 240, 246), (210, 218, 232))
    # слева учёный пишет статью, справа ты штампуешь видео
    put(im, scientist_spr(), 270, 1450, 0.8)
    d = ImageDraw.Draw(im)
    d.rectangle((60, 600, 500, 1100), fill=WHITE, outline=INK, width=6)
    lines = int(12 * cl(u / dur) * 0.25)
    for k in range(max(1, lines)):
        d.line((100, 660 + k * 40, 460 - (k % 3) * 40, 660 + k * 40), fill=(150, 150, 160), width=6)
    label(im, 'СТАТЬЯ: 3%', 280, 1150, 50, INK, 0)
    hero(im, 800, 1620, 0.7, 'happy', talk_open(t, 'B12'), chair=False)
    n = int(100 * eo(u / (dur * 0.9)))
    for k in range(min(n, 30)):
        x = 600 + (k % 6) * 75
        y = 640 + (k // 6) * 90
        d.rounded_rectangle((x, y, x + 64, y + 72), 10, fill=(240, 60, 60), outline=INK, width=3)
        d.polygon([(x + 24, y + 20), (x + 24, y + 52), (x + 48, y + 36)], fill=WHITE)
    label(im, f'ВИДЕО: {n}', 800, 1150, 60, RED, 0)
    return im


def sc13(t):
    u = t - S['B13']
    dur = D('B13')
    im = grad_t((40, 20, 80), (90, 40, 120))
    d = ImageDraw.Draw(im)
    # зодиакальный круг
    cx, cy, r = 540, 1060, 400
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=YEL, width=8)
    d.ellipse((cx - r + 60, cy - r + 60, cx + r - 60, cy + r - 60), outline=YEL, width=4)
    for k in range(12):
        a = t * 0.4 + k * math.pi / 6
        d.line((cx + math.cos(a) * (r - 60), cy + math.sin(a) * (r - 60), cx + math.cos(a) * r, cy + math.sin(a) * r),
               fill=YEL, width=4)
        label(im, '★', cx + math.cos(a + 0.26) * (r - 30), cy + math.sin(a + 0.26) * (r - 30), 36, YEL, 0)
    for k in range(20):   # блёстки
        rnd = random.Random(k)
        x, y = rnd.uniform(0, W), rnd.uniform(300, 1700)
        s = 3 + 3 * math.sin(t * 5 + k)
        d.ellipse((x - s, y - s, x + s, y + s), fill=WHITE)
    d.rectangle((0, 1640, W, H), fill=(30, 20, 50))
    d.ellipse((700, 1640, 960, 1720), fill=(90, 60, 140), outline=INK, width=6)
    hero(im, 540, 1420, 0.8, 'smug', talk_open(t, 'B13'), chair=False)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse((730, 1450, 930, 1650), fill=(160, 200, 255, 170))
    im.alpha_composite(lay)
    if u > dur * 0.45:
        panel(im, (110, 400, 970, 510), (255, 214, 64, 250))
        label(im, 'ГОРОСКОП С ЭКСПЕРТОМ', 540, 455, 50, INK, 0, pop(u - dur * 0.45))
    label(im, 'ЭФИР', 150, 1760, 70, RED, 8)
    d = ImageDraw.Draw(im)
    d.ellipse((40, 1740, 76, 1776), fill=RED if int(t * 2) % 2 else (90, 20, 20))
    return im


def sc14(t):
    """Суп горит — никто не верит."""
    u = t - S['B14']
    dur = D('B14')
    im = grad_t((250, 236, 210), (236, 214, 180))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1250, W, H), fill=(120, 120, 130))
    d.rectangle((60, 1150, 600, 1260), fill=(80, 80, 90), outline=INK, width=6)       # плита
    # кастрюля
    d.rounded_rectangle((140, 900, 520, 1160), 30, fill=(180, 186, 200), outline=INK, width=8)
    d.rectangle((100, 960, 140, 990), fill=INK)
    d.rectangle((520, 960, 560, 990), fill=INK)
    fire = cl(u / 1.5)
    for k in range(7):   # пламя под и над кастрюлей
        x = 170 + k * 50
        h = (60 + 30 * math.sin(t * 13 + k)) * (0.5 + fire)
        d.polygon([(x - 22, 1160), (x, 1160 - h), (x + 22, 1160)], fill=(255, 150, 40))
        h2 = 80 * fire * (1 + 0.3 * math.sin(t * 11 + k))
        d.polygon([(x - 20, 900), (x, 900 - h2), (x + 20, 900)], fill=(255, 120, 30))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for k in range(5):   # дым
        ph = (t * 0.4 + k / 5) % 1
        r = 60 + 120 * ph
        dl.ellipse((330 - r + 40 * math.sin(k), 820 - 600 * ph - r, 330 + r, 820 - 600 * ph + r),
                   fill=(60, 60, 70, int(160 * (1 - ph) * fire)))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
    hero(im, 820, 1650, 0.8, 'scared', 1, chair=False)
    speech_bubble(im, 760, 860, 'У МЕНЯ ГОРИТ СУП!', 1.05, 4, cl(u / 0.2), RED)
    # ответы друзей
    v = u - dur * 0.45
    if v > 0:
        x0, y0 = phone(im, 300, 1520, 420, 460)
        yy = y0 + 70
        for txt, t0 in (('ага', 0.0), ('ну-ну', 0.3), ('опять х*йня', 0.6)):
            if v > t0:
                yy += msg(im, x0 + 30, yy, txt, False, cl((v - t0) / 0.15), 36) + 14
    if u > dur * 0.8:
        stamp(im, 'R.I.P. СУП', 540, 520, u - dur * 0.8, INK, 90, -6)
    return im


def loop_arrow(im, cx, cy, r, t, col=YEL):
    d = ImageDraw.Draw(im)
    a0 = t * 120
    d.arc((cx - r, cy - r, cx + r, cy + r), a0, a0 + 300, fill=col, width=26)
    a = math.radians(a0 + 300)
    ex, ey = cx + math.cos(a) * r, cy + math.sin(a) * r
    tx, ty = -math.sin(a), math.cos(a)
    d.polygon([(ex + tx * 50, ey + ty * 50), (ex - math.cos(a) * 40, ey - math.sin(a) * 40),
               (ex + math.cos(a) * 40, ey + math.sin(a) * 40)], fill=col)


def sc15(t):
    u = t - S['B15']
    dur = D('B15')
    im = blueprint(t, (40, 26, 70), (80, 30, 70))
    q = dur * 0.35
    hero(im, 540, 1650, 1.0, 'smug' if u < q else 'shock', talk_open(t, 'B15'), chair=False)
    if u < q:
        label(im, 'АККУРАТНЕЕ', 540, 520, 110, YEL, 10, pop(u - 0.2), -4)
        label(im, 'С Х*ЙНЁЙ', 540, 650, 110, WHITE, 10, pop(u - 0.4), 3)
    else:
        v = u - q
        label(im, 'ЭТО ВИДЕО —', 540, 470, 90, WHITE, 8, pop(v))
        label(im, 'ТОЖЕ Х*ЙНЯ?', 540, 590, 110, RED, 10, pop(v - 0.2), -4)
        if v > dur * 0.3:
            loop_arrow(im, 540, 950, 170, t)
            label(im, 'ПОСМОТРИ ЕЩЁ РАЗ', 540, 1200, 66, YEL, 8, pop(v - dur * 0.3))
    return im


SCENES = [('B01', sc01), ('B02', sc02), ('B03', sc03), ('B04', sc04), ('B05', sc05), ('B06', sc06), ('B07', sc07),
          ('B08', sc08), ('B09', sc09), ('B10', sc10), ('B11', sc11), ('B12', sc12), ('B13', sc13), ('B14', sc14),
          ('B15', sc15)]
STARTS = [0.0] + [S[k] - 0.12 for k, _ in SCENES[1:]]
WIPES = {'B04', 'B07', 'B10', 'B13', 'B15'}


def bubble_wipe(im, u, dur=0.6):
    """Переход: экран засыпает пузырями чепухи."""
    k = 1 - abs(u) / (dur / 2)
    if k <= 0:
        return
    k = sm(k)
    for i in range(16):
        rnd = random.Random(i + 700)
        speech_bubble(im, rnd.uniform(-60, W + 60), rnd.uniform(-60, H + 60), NONSENSE[i % len(NONSENSE)],
                      0.3 + 2.8 * k * rnd.uniform(0.8, 1.1), rnd.uniform(-15, 15))


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
            bubble_wipe(im, t - s, 0.6)
    draw_caps(im, t)
    end = DUR - t
    if end < 0.8:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.8)))))
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
