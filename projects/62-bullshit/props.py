"""Реквизит ролика 61 (перенесён из 60-fan): кляксы, брызги, фон комнаты, цензура, галочка, друзья."""
import functools
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from kit import *  # noqa: F401,F403
from kit import (W, H, INK, YEL, RED, WHITE, SKIN, POO, POO_D, POO_L, canvas, done, P, oval, rrect, thick, put,
                 label, grad_t)


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



DROPS = [(random.Random(i).uniform(-1, 1), random.Random(i + 5).uniform(-1, 1), random.Random(i + 9).uniform(3, 11))
         for i in range(220)]


def check(im, x, y, ok=True):
    d = ImageDraw.Draw(im)
    d.ellipse((x - 26, y - 26, x + 26, y + 26), fill=((70, 190, 90) if ok else RED) + (255,), outline=INK, width=4)
    if ok:
        d.line((x - 12, y, x - 3, y + 10, x + 13, y - 10), fill=WHITE, width=7, joint='curve')
    else:
        d.line((x - 10, y - 10, x + 10, y + 10), fill=WHITE, width=7)
        d.line((x + 10, y - 10, x - 10, y + 10), fill=WHITE, width=7)



@functools.lru_cache(32)
def friend_spr(kind='girl', expr='smile'):
    """Друг/подруга по пояс, 440x560, центр лица (220, 230)."""
    im, d = canvas(440, 560)
    cx, cy = 220, 230
    shirt = (240, 140, 60) if kind == 'girl' else (130, 90, 200)
    hair = (120, 60, 30) if kind == 'girl' else (30, 26, 40)
    if kind == 'girl':
        rrect(d, (cx - 140, cy - 120, cx + 140, cy + 200), 110, hair)
    rrect(d, (cx - 170, cy + 160, cx + 170, 560), 80, shirt)
    rrect(d, (cx - 36, cy + 90, cx + 36, cy + 170), 10, SKIN)
    oval(d, cx, cy, 120, 126, SKIN)
    if kind == 'girl':
        d.chord(P(cx - 126, cy - 136, cx + 126, cy + 20), 180, 360, fill=hair)
        d.chord(P(cx - 60, cy - 120, cx + 130, cy - 10), 180, 360, fill=hair)
    else:
        for k in range(9):
            a = math.radians(200 + k * 17.5)
            oval(d, cx + math.cos(a) * 112, cy - 20 + math.sin(a) * 112, 40, 40, hair, None)
    ey = cy - 10
    if expr == 'smile':
        for s_ in (-1, 1):
            oval(d, cx + s_ * 44, ey, 13, 16, INK, None)
            oval(d, cx + s_ * 44 + 4, ey - 6, 5, 5, WHITE, None)
        d.chord(P(cx - 50, cy + 30, cx + 50, cy + 90), 0, 180, fill=(140, 40, 50), outline=INK, width=5 * SS)
    elif expr == 'shock':
        for s_ in (-1, 1):
            oval(d, cx + s_ * 46, ey - 4, 26, 32, WHITE, INK, 5)
            oval(d, cx + s_ * 46, ey - 2, 7, 8, INK, None)
        oval(d, cx, cy + 70, 24, 30, (120, 40, 50))
    else:   # disgust: прищур, язык
        for s_ in (-1, 1):
            d.line(P(cx + s_ * 46 - 22, ey - 6 * s_, cx + s_ * 46 + 22, ey + 6 * s_), fill=INK, width=8 * SS)
        d.arc(P(cx - 50, cy + 40, cx + 50, cy + 90), 200, 340, fill=INK, width=7 * SS)
        oval(d, cx + 10, cy + 84, 22, 24, (236, 110, 120))
    for s_ in (-1, 1):
        d.ellipse(P(cx + s_ * 78 - 18, cy + 30, cx + s_ * 78 + 18, cy + 46), fill=(240, 150, 140, 140))
    return done(im)


FRECKLES = [(random.Random(i).uniform(-95, 95), random.Random(i + 31).uniform(-60, 80),
             random.Random(i + 77).uniform(4, 11)) for i in range(34)]


def freckles(im, cx, cy, scale, k, seed=0):
    d = ImageDraw.Draw(im)
    n = int(len(FRECKLES) * k)
    for i in range(n):
        fx, fy, r = FRECKLES[(i + seed * 7) % len(FRECKLES)]
        r *= scale
        x, y = cx + fx * scale, cy + fy * scale
        d.ellipse((x - r, y - r, x + r, y + r), fill=POO_D)
        d.ellipse((x - r * 0.6, y - r * 0.7, x + r * 0.5, y + r * 0.3), fill=POO)


