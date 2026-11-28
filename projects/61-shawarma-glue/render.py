"""«Шаурма с вокзала + суперклей»: 2D, всё кодом. Кадр — чистая функция времени содержания. Без рекламы.

    python -B projects/61-shawarma-glue/render.py --frames 0,600   # пробные кадры (номера кадров)
    python -B projects/61-shawarma-glue/render.py --video out.mp4  # видеоряд (вызывает build.py)
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
from kit import (W, H, FPS, INK, YEL, RED, WHITE, SKIN, HOOD, HOOD_D, PANTS, GAS, GAS_L, POO, POO_D, POO_L, S, E,
                 DUR, cl, sm, eo, eio, spring, lerp, mix, noise, font, text_spr, put, canvas, done, P, oval, rrect,
                 thick, grad_t, hero, head_spr, body_spr, talk_open, panel, label, counter_text, pop, bar, stamp,
                 draw_caps, blueprint, puff_spr)  # noqa: E402
from props import splat_spr, drops, room_bg, censor, DROPS, check, friend_spr  # noqa: E402
from events import AD_STOPS  # noqa: E402

BR = banner.Breaks(AD_STOPS, cy=H / 2)
LAVASH = (238, 206, 150)
LAVASH_D = (200, 160, 100)
MEAT = (170, 90, 50)
TILE = (220, 214, 200)
GREEN_SICK = (150, 200, 110)


# ------------------------------------------------------------------ реквизит
@functools.lru_cache(4)
def shawarma_spr(bites=0):
    """Шаурма в лаваше (рулет наискосок). bites 0..3 — сколько откушено."""
    im, d = canvas(300, 520)
    top = 40 + bites * 90
    rrect(d, (70, top, 230, 500), 70, LAVASH)
    for k in range(4):
        y = top + 60 + k * 100
        if y < 480:
            d.arc(P(70, y - 40, 230, y + 40), 20, 160, fill=LAVASH_D, width=5 * SS)
    # начинка сверху
    for k in range(6):
        x = 90 + k * 24
        oval(d, x, top + 10 + (k % 2) * 8, 18, 14, (MEAT if k % 3 else (90, 180, 80)), INK, 3)
    rrect(d, (60, 380, 240, 500), 20, (250, 250, 250))                     # бумажка
    d.text(P(150, 440), 'ШАУРМА', font=font(28 * SS), fill=RED, anchor='mm')
    return done(im)


SS = 2


@functools.lru_cache(2)
def glue_spr():
    im, d = canvas(380, 140)
    rrect(d, (10, 30, 280, 110), 30, (240, 240, 245))
    rrect(d, (40, 44, 250, 96), 12, (230, 60, 60), None)
    d.text(P(145, 70), 'СУПЕРКЛЕЙ', font=font(26 * SS), fill=WHITE, anchor='mm')
    d.polygon([tuple(P(280, 40)), tuple(P(360, 64)), tuple(P(360, 76)), tuple(P(280, 100))], fill=(200, 200, 210),
              outline=INK, width=5 * SS)
    oval(d, 366, 70, 10, 10, (250, 250, 200))
    return done(im)


@functools.lru_cache(4)
def seller_spr(shrug=False):
    im, d = canvas(480, 600)
    cx, cy = 240, 210
    rrect(d, (cx - 190, cy + 150, cx + 190, 600), 80, (250, 250, 250))       # фартук/футболка
    rrect(d, (cx - 120, cy + 190, cx + 120, 600), 30, (230, 230, 230))
    d.text(P(cx, cy + 300), 'ШАУРМА', font=font(34 * SS), fill=RED, anchor='mm')
    if shrug:
        for s in (-1, 1):
            thick(d, [(cx + s * 170, cy + 200), (cx + s * 230, cy + 130), (cx + s * 210, cy + 60)], 46, (250, 250, 250))
            oval(d, cx + s * 210, cy + 50, 30, 28, SKIN)
    oval(d, cx, cy, 120, 126, SKIN)
    d.chord(P(cx - 124, cy - 140, cx + 124, cy - 10), 180, 360, fill=(250, 250, 250))   # колпак
    rrect(d, (cx - 90, cy - 200, cx + 90, cy - 70), 40, (250, 250, 250))
    for s in (-1, 1):
        oval(d, cx + s * 42, cy - 4, 12, 14, INK, None)
        d.line(P(cx + s * 42 - 22, cy - 36, cx + s * 42 + 22, cy - 30 - (12 if shrug else 0) * s), fill=INK,
               width=7 * SS)
    oval(d, cx, cy + 48, 74, 24, (40, 30, 30), None)                       # усы
    oval(d, cx, cy + 20, 18, 14, (230, 160, 140))
    return done(im)


@functools.lru_cache(2)
def spit_spr():
    """Вертел с мясом."""
    im, d = canvas(260, 560)
    d.line(P(130, 0, 130, 560), fill=(150, 150, 160), width=12 * SS)
    d.polygon([tuple(P(60, 60)), tuple(P(200, 60)), tuple(P(170, 500)), tuple(P(90, 500))], fill=MEAT, outline=INK,
              width=6 * SS)
    for k in range(9):
        y = 90 + k * 46
        d.arc(P(66 + k * 3, y - 20, 194 - k * 3, y + 20), 10, 170, fill=(130, 60, 30), width=5 * SS)
    return done(im)


@functools.lru_cache(4)
def pigeon_spr(peck=False):
    im, d = canvas(200, 170)
    oval(d, 100, 100, 70, 48, (150, 156, 176))
    d.polygon([tuple(P(30, 90)), tuple(P(0, 70)), tuple(P(6, 120))], fill=(120, 126, 146), outline=INK, width=4 * SS)
    hy = 70 if not peck else 110
    oval(d, 158, hy, 30, 28, (130, 136, 160))
    oval(d, 152, hy - 6, 6, 6, (240, 120, 40), None)
    d.polygon([tuple(P(184, hy - 4)), tuple(P(200, hy + 4)), tuple(P(184, hy + 10))], fill=(220, 180, 90))
    d.arc(P(110, 70, 170, 120), 200, 320, fill=(120, 200, 160), width=6 * SS)
    for x in (90, 115):
        d.line(P(x, 145, x - 4, 168), fill=(230, 120, 90), width=5 * SS)
    return done(im)


@functools.lru_cache(4)
def bacteria_spr(seed=0, hat=True):
    rnd = random.Random(seed)
    im, d = canvas(180, 200)
    col = [(120, 210, 90), (150, 200, 60), (100, 190, 140), (190, 210, 70)][seed % 4]
    oval(d, 90, 120, 62, 56, col)
    for k in range(6):
        a = k * math.pi / 3 + 0.3
        d.line(P(90 + math.cos(a) * 60, 120 + math.sin(a) * 54, 90 + math.cos(a) * 84, 120 + math.sin(a) * 76),
               fill=INK, width=4 * SS)
    for s in (-1, 1):
        oval(d, 90 + s * 22, 112, 12, 14, WHITE, INK, 3)
        oval(d, 90 + s * 22 + 2, 115, 5, 6, INK, None)
    d.chord(P(64, 120, 116, 160), 0, 180, fill=(120, 40, 50), outline=INK, width=3 * SS)
    if hat:
        hc = [(240, 80, 120), (80, 160, 240), (250, 200, 60)][seed % 3]
        d.polygon([tuple(P(66, 74)), tuple(P(114, 74)), tuple(P(92 + rnd.uniform(-8, 8), 6))], fill=hc, outline=INK,
                  width=4 * SS)
        oval(d, 92, 8, 10, 10, YEL, None)
    return done(im)


@functools.lru_cache(4)
def surgeon_spr(kind='surgeon', eyes='stare'):
    im, d = canvas(480, 640)
    cx, cy = 240, 220
    gown = (110, 190, 170) if kind == 'surgeon' else (240, 150, 190)
    rrect(d, (cx - 190, cy + 150, cx + 190, 640), 80, gown)
    oval(d, cx, cy, 118, 124, SKIN)
    d.chord(P(cx - 124, cy - 140, cx + 124, cy + 0), 180, 360, fill=gown)                # шапочка
    rrect(d, (cx - 110, cy + 20, cx + 110, cy + 110), 30, (170, 210, 240))            # маска
    for k in range(3):
        d.line(P(cx - 90, cy + 40 + k * 22, cx + 90, cy + 40 + k * 22), fill=(140, 180, 220), width=3 * SS)
    for s in (-1, 1):
        if eyes == 'stare':
            oval(d, cx + s * 44, cy - 20, 18, 14, WHITE, INK, 4)
            oval(d, cx + s * 44, cy - 20, 6, 7, INK, None)
            d.line(P(cx + s * 44 - 24, cy - 52, cx + s * 44 + 24, cy - 46 - 10 * s), fill=INK, width=7 * SS)
        else:   # sad
            d.arc(P(cx + s * 44 - 18, cy - 36, cx + s * 44 + 18, cy - 8), 200, 340, fill=INK, width=6 * SS)
    return done(im)


@functools.lru_cache(2)
def acetone_spr():
    im, d = canvas(200, 320)
    rrect(d, (70, 10, 130, 70), 10, (240, 80, 120))
    rrect(d, (20, 60, 180, 310), 40, (220, 240, 255))
    rrect(d, (34, 140, 166, 240), 12, WHITE)
    d.text(P(100, 175), 'АЦЕТОН', font=font(30 * SS), fill=RED, anchor='mm')
    d.text(P(100, 215), '100%', font=font(26 * SS), fill=INK, anchor='mm')
    return done(im)


@functools.lru_cache(2)
def cake_spr():
    im, d = canvas(440, 380)
    rrect(d, (40, 170, 400, 360), 30, (250, 220, 230))
    rrect(d, (40, 170, 400, 220), 30, (240, 120, 160))
    for k in range(5):
        x = 100 + k * 60
        rrect(d, (x - 8, 90, x + 8, 175), 6, (120, 190, 250))
    d.text(P(220, 290), '80', font=font(70 * SS), fill=(240, 120, 160), anchor='mm')
    return done(im)


def flames(im, xs, y, t):
    d = ImageDraw.Draw(im)
    for k, x in enumerate(xs):
        h = 34 + 6 * math.sin(t * 14 + k)
        d.polygon([(x - 12, y), (x, y - h), (x + 12, y)], fill=(255, 170, 40))
        d.polygon([(x - 6, y), (x, y - h * 0.55), (x + 6, y)], fill=(255, 240, 150))


def fat_hero(im, x, y, scale, k, expr='calm', mouth=0, t=0.0, squash=0.0, bob=0.0, pants_button=True):
    """Герой с надутым животом. k 0..1: 0 — обычный, 1 — почти шар. (x, y) — точка сиденья."""
    y = y + bob
    if k < 0.98:
        put(im, body_spr(), x, y, scale, anchor=(0.5, 470 / 760))
    else:   # шар: короткие ножки
        d = ImageDraw.Draw(im)
        for s in (-1, 1):
            d.rounded_rectangle((x + s * 90 * scale - 40 * scale, y + 120 * scale, x + s * 90 * scale + 40 * scale,
                                 y + 240 * scale), 30 * scale, fill=PANTS, outline=INK, width=max(2, int(6 * scale)))
            d.ellipse((x + s * 100 * scale - 55 * scale, y + 220 * scale, x + s * 100 * scale + 55 * scale,
                       y + 262 * scale), fill=(236, 236, 240), outline=INK, width=max(2, int(5 * scale)))
    if k > 0.01:
        rx = (150 + 250 * k) * scale * (1 + 0.04 * math.sin(t * 9) * k + squash)
        ry = (130 + 260 * k) * scale * (1 + 0.04 * math.cos(t * 9) * k - squash)
        cx, cy = x, y - 110 * scale - 120 * k * scale
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.ellipse((cx - rx - 7, cy - ry - 7, cx + rx + 7, cy + ry + 7), fill=INK)
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=HOOD)
        d.ellipse((cx - rx * 0.6, cy - ry * 0.75, cx - rx * 0.2, cy - ry * 0.45), fill=(120, 210, 200))
        if pants_button:
            d.ellipse((cx - 14 * scale, cy + ry - 40 * scale, cx + 14 * scale, cy + ry - 12 * scale),
                      fill=(230, 190, 60), outline=INK, width=3)
        for s in (-1, 1):   # ручки
            d.ellipse((cx + s * rx - 30 * scale, cy - 20 * scale, cx + s * rx + 30 * scale, cy + 40 * scale),
                      fill=SKIN, outline=INK, width=max(2, int(4 * scale)))
        im.alpha_composite(lay)
        hy = cy - ry - 60 * scale
    else:
        hy = y - 320 * scale
    put(im, head_spr(expr, mouth, 0), x, hy, scale, anchor=(0.5, 0.62))


def rumble_lines(im, cx, cy, r, t, col=INK):
    d = ImageDraw.Draw(im)
    for k in range(3):
        a = 0.8 * k - 0.8
        rr = r + 30 + 10 * math.sin(t * 20 + k)
        for s in (-1, 1):
            x0 = cx + s * rr * math.cos(a)
            y0 = cy + rr * math.sin(a)
            d.arc((x0 - 30, y0 - 30, x0 + 30, y0 + 30), 90 - 60 if s > 0 else 90 + 60, 90 + 60 if s > 0 else 270 - 60,
                  fill=col, width=6)


def station_bg(t):
    im = grad_t((180, 200, 220), (150, 170, 196))
    d = ImageDraw.Draw(im)
    for x in range(-40, W, 240):   # арки вокзала
        d.rounded_rectangle((x, 300, x + 200, 1300), 100, fill=(200, 214, 230), outline=(140, 156, 180), width=6)
    d.rectangle((0, 1300, W, H), fill=TILE)
    for y in range(1300, H, 80):
        d.line((0, y, W, y), fill=(200, 194, 180), width=4)
    # табло
    d.rounded_rectangle((640, 330, 1040, 470), 16, fill=(20, 24, 30), outline=INK, width=6)
    d.text((660, 360), 'МОСКВА  08:15', font=font(34, 'Bold'), fill=(255, 190, 60))
    d.text((660, 410), 'ЗАДЕРЖАН', font=font(34, 'Bold'), fill=RED)
    return im


def kiosk(im, t, x=540, y=1300):
    d = ImageDraw.Draw(im)
    d.rectangle((x - 420, y - 700, x + 420, y), fill=(240, 200, 80), outline=INK, width=8)
    d.rectangle((x - 360, y - 620, x + 360, y - 240), fill=(250, 240, 210), outline=INK, width=6)
    d.rectangle((x - 460, y - 820, x + 460, y - 700), fill=RED, outline=INK, width=8)
    label(im, 'ШАУРМА 24/7', x, y - 760, 76, WHITE, 0)
    d.rectangle((x - 440, y - 260, x + 440, y - 200), fill=(170, 120, 80), outline=INK, width=6)


# ------------------------------------------------------------------ сцены
def sc01(t):
    u = t - S['A01']
    im = station_bg(t)
    kiosk(im, t)
    put(im, spit_spr(), 360, 900, 0.8, 2 * math.sin(t * 3))
    put(im, shawarma_spr(), 300 + 6 * math.sin(t * 3), 1500, 0.8, -15)
    label(im, '+', 540, 1500, 140, WHITE, 10, 1 + 0.08 * math.sin(t * 6))
    put(im, glue_spr(), 790, 1500 + 8 * math.sin(t * 3 + 1), 0.9, 10)
    label(im, '= ?', 540, 1730, 110, YEL, 10, 1 + 0.05 * math.sin(t * 5))
    # пар над шаурмой
    d = ImageDraw.Draw(im)
    for j in range(3):
        ph = (t * 0.7 + j / 3) % 1
        xs = 270 + j * 30
        d.line([(xs + 12 * math.sin(yy / 18 + t * 4 + j), yy) for yy in range(int(1300 - ph * 80), int(1400 - ph * 80), 8)],
               fill=(130, 170, 60, int(220 * (1 - ph))), width=7)
    v = u - (E['A01'] - S['A01']) * 0.62
    if v > 0:
        stamp(im, 'НЕ ПОВТОРЯТЬ!', 700, 1000, v, RED, 84, -6)
    return im


def sc02(t):
    u = t - S['A02']
    dur = E['A02'] - S['A02']
    im = station_bg(t)
    kiosk(im, t)
    put(im, spit_spr(), 300, 860, 0.85, 3 * math.sin(t * 2))
    shrug = u > dur * 0.7
    put(im, seller_spr(shrug), 760, 960 + 4 * math.sin(t * 2), 0.85)
    d = ImageDraw.Draw(im)
    for k in range(4):   # мухи над мясом
        a = t * (3 + k) + k
        fx, fy = 300 + math.cos(a) * (90 + 10 * k), 720 + math.sin(a * 1.4) * 60
        d.ellipse((fx - 8, fy - 8, fx + 8, fy + 8), fill=INK)
        d.ellipse((fx - 16, fy - 16, fx - 3, fy - 5), fill=(255, 255, 255, 200))
    # бирки «вчера / позавчера»
    tags = (('ВЧЕРА?', 0.22, -8), ('ПОЗАВЧЕРА?', 0.45, 6))
    for j, (txt, f, r) in enumerate(tags):
        v = u - dur * f
        if v > 0:
            put(im, text_spr(txt, 58, INK, 'Heavy', 0), 300, 1420 + j * 110, pop(v), r)
    if u > dur * 0.1:
        label(im, 'СРОК ГОДНОСТИ: ???', 540, 1720, 60, RED, 6, pop(u - dur * 0.1))
    if shrug:
        label(im, '?', 960, 640, 120, YEL, 10, pop(u - dur * 0.7), 10)
    return im


def sc03(t):
    u = t - S['A03']
    dur = E['A03'] - S['A03']
    im = station_bg(t)
    kiosk(im, t, 540, 1200)
    put(im, spit_spr(), 360, 760, 0.8)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1200, W, H), fill=TILE)
    # голуби огибают ларёк дугой
    for k in range(4):
        ph = (u * 0.22 + k * 0.25) % 1
        x = lerp(-120, 1200, ph)
        y = 1500 + 260 * math.sin(math.pi * ph) + k * 30
        put(im, pigeon_spr(int(t * 4 + k) % 2 == 0), x, y, 1.3)
    # знак «не ешьте тут» от голубей
    v = u - 0.6
    if v > 0:
        put(im, text_spr('ГОЛУБИ: «НЕТ»', 60, WHITE, 'Heavy', 8), 540, 700, pop(v), -4)
    # голубь с окурком
    v = u - dur * 0.62
    if v > 0:
        panel(im, (600, 1560, 1020, 1860), (255, 255, 255, 240))
        put(im, pigeon_spr(True), 760, 1710, 0.9)
        d = ImageDraw.Draw(im)
        d.rectangle((850, 1745, 900, 1760), fill=(240, 240, 240), outline=INK)
        d.rectangle((830, 1745, 852, 1760), fill=(230, 150, 60), outline=INK)
        label(im, 'ест окурки', 810, 1610, 44, INK, 0, pop(v))
    return im


def sc04(t):
    u = t - S['A04']
    dur = E['A04'] - S['A04']
    im = room_bg(t)
    eat = dur * 0.35
    if u < eat:
        bites = min(3, int(u / (eat / 4)))
        hero(im, 540, 1450, 0.95, 'happy', talk_open(t, 'A04') if bites % 2 else 1, chair=False)
        put(im, shawarma_spr(bites), 680, 1180 + 10 * math.sin(t * 8), 0.75, -25)
        for k in range(bites * 3):   # крошки
            rnd = random.Random(k)
            d = ImageDraw.Draw(im)
            x, y = 600 + rnd.uniform(-60, 60), 1250 + (u * 300 + rnd.uniform(0, 400)) % 400
            d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=LAVASH_D)
        label(im, 'ДО КРОШКИ', 540, 520, 80, INK, 0, pop(u - 0.4), -4)
        return im
    v = u - eat
    hero(im, 540, 1300, 0.95, 'smug', talk_open(t, 'A04'), chair=False)
    censor(im, (330, 1260, 750, 1480), t)
    put(im, glue_spr(), lerp(1000, 700, eo(v / 0.5)), 1380, 0.9, 30)
    if v > 0.6:
        d = ImageDraw.Draw(im)
        # таймер 10 с
        k = cl((v - 0.6) / 2.0)
        cx, cy, R = 220, 760, 130
        d.ellipse((cx - R - 10, cy - R - 10, cx + R + 10, cy + R + 10), fill=INK)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=WHITE)
        if k > 0.01:
            d.pieslice((cx - R + 12, cy - R + 12, cx + R - 12, cy + R - 12), -90, -90 + 360 * k, fill=(230, 70, 70))
        label(im, f'{max(0, 10 - int(k * 10))} с', cx, cy, 90, INK, 0)
        if k >= 1:
            stamp(im, 'СХВАЧЕНО', 740, 760, v - 2.6, RED, 80, -6)
    return im


def gut_bg(t):
    im = grad_t((90, 30, 50), (60, 20, 40))
    d = ImageDraw.Draw(im)
    # извилистая кишка
    for k in range(5):
        y = 420 + k * 300
        pts = [(x, y + 80 * math.sin(x / 140 + k + t * 0.6)) for x in range(-40, W + 60, 20)]
        d.line(pts, fill=(230, 130, 140), width=230)
        d.line(pts, fill=(250, 170, 170), width=170)
        d.line([(x, yy - 50) for x, yy in pts], fill=(255, 200, 200), width=10)
    return im


def sc05(t):
    u = t - S['A05']
    dur = E['A05'] - S['A05']
    im = gut_bg(t)
    # диско-шар и лучи
    d = ImageDraw.Draw(im)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for k in range(6):
        a = t * 1.5 + k * math.pi / 3
        col = [(255, 80, 160), (80, 200, 255), (255, 230, 80)][k % 3]
        dl.polygon([(540, 460), (540 + math.cos(a) * 1400 - 60, 460 + math.sin(a) * 1400),
                    (540 + math.cos(a) * 1400 + 60, 460 + math.sin(a) * 1400)], fill=col + (60,))
    im.alpha_composite(lay)
    d = ImageDraw.Draw(im)
    d.line((540, 0, 540, 380), fill=INK, width=6)
    d.ellipse((470, 380, 610, 520), fill=(200, 210, 230), outline=INK, width=6)
    for k in range(5):
        d.line((480, 400 + k * 25, 600, 400 + k * 25), fill=(150, 160, 180), width=3)
    # танцующие бактерии
    n = int(2 + 10 * eo(u / 2.0))
    for i in range(n):
        rnd = random.Random(i + 10)
        x = 140 + (i % 4) * 260 + rnd.uniform(-40, 40)
        y = 820 + (i // 4) * 330 + 30 * abs(math.sin(t * 6 + i))
        put(im, bacteria_spr(i), x, y, 0.95 + 0.1 * math.sin(t * 6 + i), 15 * math.sin(t * 6 + i))
    label(im, 'ВЕЧЕРИНКА!', 540, 640, 100, YEL, 10, 1 + 0.06 * math.sin(t * 12), -4)
    # пузыри газа
    v = u - dur * 0.55
    if v > 0:
        for i in range(14):
            rnd = random.Random(i + 70)
            ph = (t * 0.5 + rnd.random()) % 1
            put(im, puff_spr(40, i % 6, True), rnd.uniform(80, 1000), 1800 - ph * 1300, 0.5 + ph * 0.6,
                alpha=0.9 * (1 - ph ** 3))
        stamp(im, '+ ГАЗ', 540, 1700, v, GAS, 110, -6)
    return im


def sc06(t):
    u = t - S['A06']
    dur = E['A06'] - S['A06']
    im = gut_bg(t)
    # дверь «ВЫХОД», заклеенная крест-накрест
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((300, 820, 780, 1600), 20, fill=(90, 140, 90), outline=INK, width=10)
    d.rectangle((340, 700, 740, 800), fill=(60, 200, 90), outline=INK, width=6)
    label(im, 'ВЫХОД', 540, 750, 64, WHITE, 0)
    # газ толпится у двери
    for i in range(10):
        rnd = random.Random(i + 3)
        ph = (t * 0.6 + rnd.random()) % 1
        x = 540 + rnd.uniform(-420, 420) * (1 - 0.6 * ph)
        put(im, puff_spr(46, i % 6, True), x, lerp(400, 760, ph) + rnd.uniform(-40, 40), 0.7, alpha=0.95)
    k = cl((u - dur * 0.35) / 0.5)
    if k > 0:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        for sgn in (-1, 1):
            dl.line((540 - 260 * k, 1210 - sgn * 400 * k, 540 + 260 * k, 1210 + sgn * 400 * k), fill=(250, 250, 230, 255),
                    width=70)
        im.alpha_composite(lay)
        label(im, 'СУПЕРКЛЕЙ', 540, 1210, 60, RED, 6, k, -50)
    if u > dur * 0.78:
        stamp(im, 'НАГЛУХО', 540, 1760, u - dur * 0.78, RED, 110, -6)
    return im


def sc07(t):
    u = t - S['A07']
    dur = E['A07'] - S['A07']
    im = room_bg(t)
    k = 0.55 * eo(u / (dur * 0.6))
    shake = 4 * noise(t * 4, 1) * (u > dur * 0.45)
    fat_hero(im, 540 + shake, 1450, 0.9, k, 'shock', 0, t)
    if u > dur * 0.45:
        rumble_lines(im, 540, 1200, 300, t)
        label(im, 'ТР-Р-Р-Р', 540 + 8 * noise(t * 5, 2), 760, 110, (200, 120, 60), 10, 1 + 0.05 * math.sin(t * 30), -4)
        # трактор-иконка
        d = ImageDraw.Draw(im)
        x0, y0 = 760, 840
        d.rounded_rectangle((x0, y0, x0 + 200, y0 + 90), 14, fill=(240, 80, 60), outline=INK, width=6)
        d.rectangle((x0 + 110, y0 - 70, x0 + 190, y0), fill=(240, 80, 60), outline=INK, width=6)
        d.ellipse((x0 - 10, y0 + 50, x0 + 90, y0 + 150), fill=INK)
        d.ellipse((x0 + 140, y0 + 80, x0 + 210, y0 + 150), fill=INK)
        label(im, 'на морозе', x0 + 100, y0 + 200, 40, (100, 140, 200), 5)
    label(im, 'ВОЗДУШНЫЙ ШАР', 540, 500, 70, WHITE, 8, pop(u - 0.3))
    return im


def sc08(t):
    """Пуговица — пулей в телевизор. Опять."""
    u = t - S['A08']
    dur = E['A08'] - S['A08']
    im = room_bg(t)
    d = ImageDraw.Draw(im)
    # телевизор справа
    d.rounded_rectangle((640, 760, 1040, 1020), 16, fill=(30, 34, 50), outline=INK, width=8)
    d.rounded_rectangle((660, 780, 1020, 1000), 8, fill=(70, 120, 200))
    d.rectangle((700, 1020, 980, 1200), fill=(170, 120, 80), outline=INK, width=6)
    pop_t = dur * 0.25
    hit = pop_t + 0.35
    fat_hero(im, 300, 1550, 0.75, 0.62, 'shock' if u > pop_t else 'strain', 0, t, pants_button=u < pop_t)
    if pop_t < u < hit:
        f = (u - pop_t) / (hit - pop_t)
        bx, by = lerp(300, 840, f), lerp(1440, 890, f)
        d = ImageDraw.Draw(im)
        for k in range(6):
            d.line((bx - 40 - k * 30, by + 30 + k * 30 * 0.6, bx - 60 - k * 30, by + 42 + k * 30 * 0.6), fill=WHITE + (200,),
                   width=6)
        d.ellipse((bx - 18, by - 18, bx + 18, by + 18), fill=(230, 190, 60), outline=INK, width=4)
    if u >= hit:
        d = ImageDraw.Draw(im)
        cx, cy = 840, 890
        for k in range(10):   # трещины
            a = k * 0.63
            d.line((cx, cy, cx + math.cos(a) * 180, cy + math.sin(a) * 110), fill=WHITE, width=5)
        d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=(230, 190, 60), outline=INK, width=4)
        label(im, 'ДЗЫНЬ!', 840, 680, 90, YEL, 10, pop(u - hit), 8)
    if u > dur * 0.78:
        stamp(im, 'ОПЯТЬ', 540, 520, u - dur * 0.78, RED, 120, -6)
        label(im, '(см. видео про вентилятор)', 540, 640, 38, INK, 0, alpha=cl((u - dur * 0.82) / 0.3))
    return im


def bubble(im, box, text, size=60, col=INK, tail=(0, 1)):
    panel(im, box, (255, 255, 255, 245), r=40)
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    tx = x0 + (x1 - x0) * (0.3 if tail[0] < 0 else 0.7)
    d.polygon([(tx - 24, y1 - 2), (tx + 24, y1 - 2), (tx + tail[0] * 40, y1 + 60)], fill=WHITE)
    label(im, text, (x0 + x1) / 2, (y0 + y1) / 2, size, col, 0)


def sc09(t):
    u = t - S['A09']
    dur = E['A09'] - S['A09']
    im = room_bg(t)
    fat_hero(im, 540, 1560, 0.7, 0.75, 'calm', talk_open(t, 'A09'), t)
    nod = 0
    if u > dur * 0.72:
        nod = 20 * abs(math.sin((u - dur * 0.72) * 6))
    for i, (kind, x) in enumerate((('girl', 170), ('boy', 910))):
        put(im, friend_spr(kind, 'shock' if u < dur * 0.45 else 'smile'), x, 1450 + (nod if u > dur * 0.72 else 0), 0.9)
    if u < dur * 0.45:
        bubble(im, (60, 420, 520, 620), 'Ты чего', 56, INK, (-1, 1))
        label(im, 'такой круглый?', 290, 560, 40, (90, 90, 110), 0)
    v = u - dur * 0.45
    if v > 0:
        bubble(im, (330, 500, 750, 700), 'Шаурма.', 72, (200, 120, 60), (0, 1))
    if u > dur * 0.72:
        label(im, '*понимающе кивают*', 540, 900, 52, INK, 0, pop(u - dur * 0.72), -3)
    return im


def sc10(t):
    u = t - S['A10']
    dur = E['A10'] - S['A10']
    im = grad_t((150, 200, 250), (210, 236, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1640, W, H), fill=(120, 190, 100))
    # пытается взлететь: подпрыгивает и плюхается
    jump = abs(math.sin(u * 2.4)) * 140 * (1 - cl((u - dur * 0.55) / 0.6))
    fat_hero(im, 540, 1500 - jump, 0.75, 1.0, 'calm' if u < dur * 0.55 else 'scared', 0, t, squash=0.06 * (jump < 10))
    # весы «газ vs воздух»
    v = u - 0.8
    if v > 0:
        panel(im, (80, 380, 1000, 700), (255, 255, 255, 235))
        d = ImageDraw.Draw(im)
        d.line((240, 600, 840, 600), fill=INK, width=10)
        d.polygon([(520, 600), (560, 600), (540, 660)], fill=INK)
        put(im, puff_spr(46, 1, True), 300, 540, 0.8)
        put(im, puff_spr(46, 2, False, (220, 230, 240)), 780, 540, 0.8)
        label(im, 'газ', 300, 470, 44, INK, 0)
        label(im, 'воздух', 780, 470, 44, INK, 0)
        label(im, '≈', 540, 520, 90, RED, 0)
    if u > dur * 0.5:
        stamp(im, 'НЕ ВЗЛЕТИТ', 540, 820, u - dur * 0.5, RED, 90, -6)
    if u > dur * 0.7:
        label(im, 'большой · грустный · урчащий', 540, 1780, 48, INK, 0, pop(u - dur * 0.7))
    return im


def sc11(t):
    u = t - S['A11']
    dur = E['A11'] - S['A11']
    im = room_bg(t)
    split = dur * 0.45
    if u < split:
        fat_hero(im, 540, 1550, 0.75, 1.0, 'calm', 0, t)
        # знак «огнеопасно» на животе
        d = ImageDraw.Draw(im)
        cx, cy, r = 540, 1300, 100
        k = pop(u - 0.3)
        r *= k
        if r > 10:
            d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(240, 60, 50), outline=WHITE, width=6)
            d.polygon([(cx, cy - r * 0.55), (cx + r * 0.3, cy + r * 0.3), (cx - r * 0.3, cy + r * 0.3)], fill=WHITE)
        for j, (sym, x) in enumerate((('H₂', 300), ('CH₄', 780))):
            v = u - 0.8 - j * 0.3
            if v > 0:
                panel(im, (x - 130, 430, x + 130, 640), (255, 255, 255, 240))
                put(im, text_spr(sym, 96, RED if j else (60, 140, 240), 'Heavy', 0), x, 535, pop(v))
        label(im, 'ОГНЕОПАСНО', 540, 760, 90, RED, 10, pop(u - 0.5), -4)
        return im
    v = u - split
    # день рождения бабушки — без тебя
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((100, 1300, 980, 1420), 20, fill=(200, 150, 110), outline=INK, width=8)
    put(im, cake_spr(), 540, 1150, 1.1)
    flames(im, [408 + k * 66 for k in range(5)], 1042, t)
    label(im, 'С ДНЁМ РОЖДЕНИЯ, БАБУЛЯ!', 540, 520, 56, (240, 120, 160), 6)
    # запрещающий знак с героем
    put(im, head_spr('scared', 0, 0), 860, 760, 0.8)
    d = ImageDraw.Draw(im)
    d.ellipse((860 - 130, 760 - 130, 860 + 130, 760 + 130), outline=RED, width=22)
    d.line((860 - 92, 760 - 92, 860 + 92, 760 + 92), fill=RED, width=22)
    stamp(im, 'БЕЗ ТЕБЯ', 360, 760, v - 0.4, RED, 90, -6)
    return im


def sc12(t):
    u = t - S['A12']
    dur = E['A12'] - S['A12']
    im = room_bg(t)
    pull = dur * 0.4
    tug = 30 * math.sin(u * 14) if u < pull else 0
    fat_hero(im, 540 + tug * 0.3, 1550, 0.8, 0.9, 'strain' if u < pull else 'scared', 0, t)
    censor(im, (360, 1480, 720, 1700), t)
    if u > pull:
        v = u - pull
        d = ImageDraw.Draw(im)
        for k in range(18):   # волоски разлетаются
            rnd = random.Random(k)
            a = rnd.uniform(math.pi, 2 * math.pi)
            r = 120 + 700 * eo(v / 0.8) * rnd.uniform(0.5, 1)
            x, y = 540 + math.cos(a) * r, 1600 + math.sin(a) * r * 0.6 + 400 * v * v
            d.line((x, y, x + 10, y + 22), fill=INK, width=4)
        label(im, 'АЙ!!!', 540, 560, 170, RED, 12, pop(v, 0.25), -6)
        panel(im, (120, 720, 960, 960), (255, 255, 255, 240))
        put(im, text_spr('ЭПИЛЯЦИЯ: бесплатно', 56, INK, 'Heavy', 0), 540, 790, pop(v - 0.3))
        put(im, text_spr('воск: не использовался', 44, (120, 120, 140), 'Bold', 0), 540, 880, pop(v - 0.6))
        check(im, 920, 790, True)
    return im


def hospital_bg(t):
    im = grad_t((230, 244, 246), (200, 224, 230))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1500, W, H), fill=(180, 200, 210))
    for x in range(0, W, 120):
        d.line((x, 1500, x - 200, H), fill=(160, 184, 196), width=4)
    d.rounded_rectangle((60, 330, 360, 560), 14, fill=(200, 236, 250), outline=INK, width=6)
    d.rectangle((150, 380, 270, 420), fill=RED)
    d.rectangle((190, 340, 230, 460), fill=RED)
    return im


def sc13(t):
    u = t - S['A13']
    dur = E['A13'] - S['A13']
    im = hospital_bg(t)
    stare_end = dur * 0.3
    # каталка с героем-шаром
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((80, 1560, 640, 1620), 20, fill=(200, 205, 215), outline=INK, width=6)
    for x in (140, 580):
        d.ellipse((x - 30, 1680, x + 30, 1740), fill=INK)
        d.line((x, 1620, x, 1680), fill=INK, width=8)
    fat_hero(im, 360, 1450, 0.55, 1.0, 'scared', 0, t)
    put(im, surgeon_spr('surgeon', 'stare'), 800, 1140, 0.95)
    if u < stare_end:
        label(im, '. . .', 800, 760, 110, INK, 0, alpha=cl(u / 0.4))
    v = u - stare_end
    if v > 0:
        put(im, acetone_spr(), 940, lerp(1700, 1280, eo(v / 0.6)), 0.9, 8)
        if v > 0.8:
            panel(im, (100, 420, 980, 600), (255, 255, 255, 240))
            label(im, 'ацетон растворяет суперклей', 540, 510, 50, INK, 0, pop(v - 0.8))
    w = u - dur * 0.7
    if w > 0:
        bubble(im, (520, 660, 1040, 900), 'ВСЕМ НА 10 М!', 60, RED, (1, 1))
        d = ImageDraw.Draw(im)
        for k in range(3):   # медперсонал убегает
            x = lerp(900, 1300, eo(w / 0.8)) + k * 60
            d.ellipse((x - 30, 1300, x + 30, 1360), fill=(240, 150, 190))
            d.rounded_rectangle((x - 40, 1360, x + 40, 1500), 20, fill=(240, 150, 190))
    return im


def sc14(t):
    """Клей растворён: шар носится по палате, сдуваясь."""
    u = t - S['A14']
    dur = E['A14'] - S['A14']
    im = hospital_bg(t)
    go = dur * 0.35
    if u < go:
        fat_hero(im, 540, 1450, 0.7, 1.0, 'scared', 0, t, squash=0.03 * math.sin(t * 30))
        d = ImageDraw.Draw(im)
        for k in range(5):   # капли ацетона
            y = 900 + ((t * 600 + k * 80) % 400)
            d.ellipse((520 + k * 10 - 8, y - 12, 520 + k * 10 + 8, y + 12), fill=(200, 230, 255), outline=INK)
        label(im, '3… 2… 1…', 540, 640, 110, RED, 10, 1 + 0.05 * math.sin(t * 20))
        return im
    v = u - go
    # траектория-петля как у сдувающегося шарика
    path = []
    for i in range(60):
        s_ = v - i * 0.02
        if s_ < 0:
            break
        x = 540 + 380 * math.sin(s_ * 5.3) * math.cos(s_ * 1.7)
        y = 1100 + 520 * math.sin(s_ * 3.9 + 1) * math.cos(s_ * 2.3)
        path.append((x, y))
    d = ImageDraw.Draw(im)
    for i, (x, y) in enumerate(path[1:], 1):
        r = 60 * (1 - i / 60)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(150, 170, 80, int(180 * (1 - i / 60))))
    k = max(0.0, 1 - v / (dur - go))
    hx, hy = path[0] if path else (540, 1100)
    fat_hero(im, hx, hy + 200 * 0.6, 0.6, k, 'shock', 1, t)
    label(im, 'ПФФФФФФ', 540 + 10 * noise(t * 4, 1), 520, 130, GREEN_SICK, 12, 1 + 0.06 * math.sin(t * 25), -5)
    # зелёная дымка заполняет палату
    lay = Image.new('RGBA', (W, H), (130, 160, 60, int(120 * cl(v / 2.0))))
    im.alpha_composite(lay)
    return im


def sc15(t):
    u = t - S['A15']
    dur = E['A15'] - S['A15']
    im = grad_t((140, 190, 240), (200, 230, 250))
    d = ImageDraw.Draw(im)
    # здание больницы, из окон валит газ
    d.rectangle((120, 600, 960, 1600), fill=(236, 240, 244), outline=INK, width=8)
    d.rectangle((420, 520, 660, 620), fill=WHITE, outline=INK, width=6)
    d.rectangle((520, 530, 560, 610), fill=RED)
    d.rectangle((500, 550, 580, 590), fill=RED)
    for r_ in range(3):
        for c in range(4):
            x, y = 180 + c * 200, 680 + r_ * 220
            d.rectangle((x, y, x + 120, y + 150), fill=(140, 180, 90), outline=INK, width=5)
            ph = (t * 0.8 + c * 0.3 + r_ * 0.2) % 1
            put(im, puff_spr(30, (c + r_) % 6, False, (150, 180, 90)), x + 60, y - ph * 140, 0.6 + ph, alpha=1 - ph)
    d.rectangle((0, 1600, W, H), fill=(120, 190, 100))
    panel(im, (160, 400, 920, 520), (255, 240, 140, 250))
    label(im, 'ЗАКРЫТО НА ПРОВЕТРИВАНИЕ', 540, 460, 48, INK, 0, pop(u - 0.2))
    # хирург и медсестра уходят с заявлениями
    for j, (kind, t0) in enumerate((('surgeon', dur * 0.35), ('nurse', dur * 0.75))):
        v = u - t0
        if v > 0:
            x = lerp(540, 1250, cl(v / 3.0)) - j * 0
            put(im, surgeon_spr(kind, 'sad'), x - 200 + j * 0, 1560, 0.6)
            panel(im, (x - 300, 1300, x - 110, 1420), (255, 255, 255, 250), r=10)
            label(im, 'ЗАЯВЛЕНИЕ', x - 205, 1360, 26, INK, 0)
    if u > dur * 0.82:
        label(im, 'тоже.', 300, 1780, 70, INK, 0, pop(u - dur * 0.82))
    return im


def sc16(t):
    u = t - S['A16']
    dur = E['A16'] - S['A16']
    im = station_bg(t)
    kiosk(im, t)
    put(im, spit_spr(), 300, 860, 0.85)
    put(im, seller_spr(False), 760, 960, 0.85)
    hero(im, 540, 1600, 0.85, 'happy', talk_open(t, 'A16'), chair=False)
    put(im, shawarma_spr(0), 700, 1420 + 8 * math.sin(t * 4), 0.65, -25)
    if u > dur * 0.4:
        stamp(im, 'ВКУСНАЯ', 560, 1000, u - dur * 0.4, (200, 120, 60), 90, -6)
    if u > dur * 0.7:
        put(im, glue_spr(), 300, 1400, 0.8, -10)
        label(im, 'ЗАВТРА: ЕЩЁ ОДНУ', 540, 1820, 60, YEL, 8, pop(u - dur * 0.7))
    return im


SCENES = [('A01', sc01), ('A02', sc02), ('A03', sc03), ('A04', sc04), ('A05', sc05), ('A06', sc06), ('A07', sc07),
          ('A08', sc08), ('A09', sc09), ('A10', sc10), ('A11', sc11), ('A12', sc12), ('A13', sc13), ('A14', sc14),
          ('A15', sc15), ('A16', sc16)]
STARTS = [0.0] + [S[k] - 0.12 for k, _ in SCENES[1:]]
WIPES = {'A04', 'A05', 'A07', 'A13', 'A15', 'A16'}


def gas_wipe(im, u, dur=0.6):
    k = 1 - abs(u) / (dur / 2)
    if k <= 0:
        return
    k = sm(k)
    for i in range(14):
        rnd = random.Random(i + 500)
        put(im, puff_spr(120, 300 + i % 5, False, (150, 190, 90)), rnd.uniform(-80, W + 80), rnd.uniform(-80, H + 80),
            0.2 + 4.2 * k * rnd.uniform(0.7, 1.1), rnd.uniform(-20, 20))


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
            gas_wipe(im, t - s, 0.6)
    draw_caps(im, t)
    end = DUR - t
    if end < 0.8:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.8)))))
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
