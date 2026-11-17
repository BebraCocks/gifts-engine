"""«Мита: подарки, которые можно только скрафтить» — 1080×1920, 60 fps. Кадр — чистая функция времени содержания.
Белый фон со звёздной картой и сменой оттенка по частям, раскладка как в 49/50: заголовок сверху, NFT/сравнения,
Мита (клипы Gemini, mita51.py), боковые панели, субтитры под ней. Цены — data/craft_2026-11-17.json (Fragment)."""
import functools
import json
import math
import re
import sys
import wave
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
import events as E
import mita51 as M
from timeline import DUR, ON, END, AD_STOP, TAKES
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
DATA = json.loads((HERE / 'data' / 'craft_2026-11-17.json').read_text(encoding='utf-8'))
RATE = DATA['ton_rub']
DECOR = HERE / 'input' / 'decor'
UFONT = HERE / 'input' / 'fonts'
WHITE = (255, 255, 255)
INK = (28, 26, 60)
MUTED = (112, 110, 140)
NAVY = (30, 34, 82)
GOLD = (236, 176, 52)
PINK = (226, 54, 120)
RED = (200, 36, 52)
TIER_COL = {'необычная': (60, 170, 110), 'редкая': (60, 120, 220), 'эпическая': (140, 80, 210), 'легендарная': (226, 160, 30)}
PANEL_W, PANEL_H = 240, 300
SIDE_Y = 1420
LX, RX = 150, 930
SUB_Y = 872
SUB_Y_CREEPY = 1800
DC = 'Desk Calendar'
REG = ['Balloon Face', 'Burning Time', 'Deadline', 'Fawkes Night']          # обычные модели календаря (не крафт)
CHEAP_MODELS = [(DC, m) for m in ('Vacation', 'April Fools', 'Launch Date', 'New Year', 'Space Era', 'Artwork',
                                  'Frog Day', 'Grimoire', 'Weekly Set', 'Cat Seasons', 'Zeus')] + \
               [('Jingle Bells', m) for m in ('Festive Night', 'Steampunk', 'Orchestra', 'Spring Knell')]


def floor_ton(g, m):
    for c in DATA['gifts'][g]['crafted']:
        if c['model'] == m and c['floor']:
            return c['floor'][0][1]
    return None


def rub_of(g, m):
    return round(floor_ton(g, m) * RATE)


REG_FLOOR = DATA['gifts'][DC]['regular_floor'][0][1]
FOUR_RUB = round(4 * REG_FLOOR * RATE)
_cs = [c for c in DATA['gifts'][DC]['crafted'] if c['floor']]
N_CHEAP, N_ALL = sum(c['floor'][0][1] < 4 * REG_FLOOR for c in _cs), len(_cs)


def rub(v):
    return f'{v:,} ₽'.replace(',', ' ')


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.35):
    return ease((t - t0) / d)


def window_a(t, t0, t1, d=0.3):
    return appear(t, t0, d) * (1 - appear(t, t1 - d, d))


def pop(t, t0, d=0.45):
    return fx.ease_out_back(fx.clamp01((t - t0) / d)) if t < t0 + d else 1.0


# ------------------------------------------------------------------ картинки
def put(canvas, im, cx, cy, s=1.0, a=1.0, rot=0.0, anchor=None):
    if im is None or a <= 0.003 or s <= 0.003:
        return
    fx.over(canvas, fx.warp(im, cx, cy, s, s, rot, anchor), a)


@functools.lru_cache(None)
def text(s, size, weight='Bold', color=INK, shadow=False):
    return fx.text_img(((s, color),), size, weight, shadow)


@functools.lru_cache(None)
def multi(parts, size, weight='Bold', shadow=False):
    return fx.text_img(parts, size, weight, shadow)


@functools.lru_cache(None)
def ufont(weight, size):
    return ImageFont.truetype(str(UFONT / f'Unbounded-{weight}.ttf'), size)


@functools.lru_cache(None)
def utext(s_, size, weight='SemiBold', color=INK):
    f = ufont(weight, size)
    l, t_, r, b_ = f.getbbox(s_)
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (r + 16, asc + desc + 16), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8, 8), s_, font=f, fill=color + (255,))
    return im


@functools.lru_cache(None)
def upill(s_, fill, size, tcol, weight='SemiBold'):
    f = ufont(weight, size)
    tw = int(f.getlength(s_))
    h_ = int(size * 1.9)
    w_ = tw + h_
    S = 2
    im = Image.new('RGBA', (w_ * S, h_ * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w_ * S - 1, h_ * S - 1], h_ * S // 2, fill=fill + (255,))
    d.text((w_ * S / 2, h_ * S / 2), s_, font=ufont(weight, size * S), fill=tcol + (255,), anchor='mm')
    return im.resize((w_, h_), Image.LANCZOS)


@functools.lru_cache(None)
def nft(g, m, size):
    return Image.open(gifts_api.model_png(g, m, 512)).convert('RGBA').resize((size, size), Image.LANCZOS)


@functools.lru_cache(None)
def nft_grey(g, m, size, k=0.85):
    im = nft(g, m, size)
    a = np.array(im).astype(np.float32)
    lum = a[..., :3].mean(-1, keepdims=True)
    a[..., :3] = a[..., :3] * (1 - k) + (lum * 0.55 + np.array([40, 20, 24])) * k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


@functools.lru_cache(None)
def decor(name, w=None):
    im = Image.open(DECOR / f'{name}.png').convert('RGBA')
    if w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    return im


@functools.lru_cache(None)
def glow(c, size=512, power=1.8):
    g = fx.radial(size, (255, 255, 255), power, 1.0)
    arr = np.array(g)
    arr[..., :3] = c
    return Image.fromarray(arr)


@functools.lru_cache(None)
def panel(w=PANEL_W, h=PANEL_H, border=(232, 222, 190)):
    im = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0))
    im.alpha_composite(fx.soft_shadow(w, h, 34, 18, 0.16).resize((w + 60, h + 60)))
    im.alpha_composite(fx.rounded(w, h, 34, (255, 255, 255, 238), border + (255,), 3), (30, 26))
    return im


def sparkle_burst(cv, t, t0, cx, cy, spread, n=14, col=(255, 196, 70), d=0.9):
    k = t - t0
    if not 0 <= k < d:
        return
    rng = np.random.default_rng(int(t0 * 1000) + int(cx))
    def draw(dr, mp, S):
        for j in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            r = ease(k / d) * rng.uniform(0.4, 1.0) * spread
            x, y = mp(cx + math.cos(ang) * r, cy + math.sin(ang) * r * 1.1)
            fx.sparkle(dr, x, y, (1 - k / d) * rng.uniform(10, 24) * S, col + (int(255 * (1 - k / d)),))
    fx.over(cv, fx.draw_rgba((cx - spread - 60, cy - spread * 1.2 - 60, cx + spread + 60, cy + spread * 1.2 + 60), draw))


def magic_nft(cv, t, g, m, x, y, size, t0, a=1.0, glow_col=(255, 205, 90), grey=False, bob=True):
    """NFT держится магией: мягкое сияние, лёгкое покачивание, искорки по кругу (без карточек)."""
    if t < t0:
        return
    p = pop(t, t0)
    yy = y + (7 * math.sin(t * 2.1 + x * 0.013) if bob else 0)
    put(cv, glow(glow_col), x, yy, size / 512 * 1.55 * p, a * (0.55 + 0.1 * math.sin(t * 3 + x)))
    put(cv, nft_grey(g, m, size) if grey else nft(g, m, size), x, yy, p, a)
    if a > 0.3 and not grey:
        def draw(dr, mp, S):
            for j in range(3):
                ang = t * 1.6 + j * 2.1 + x * 0.01
                X, Y = mp(x + math.cos(ang) * size * 0.58, yy + math.sin(ang) * size * 0.5)
                tw = 0.5 + 0.5 * math.sin(t * 5 + j)
                fx.sparkle(dr, X, Y, (5 + 6 * tw) * S, (255, 214, 110, int(200 * a * tw)))
        fx.over(cv, fx.draw_rgba((x - size, yy - size, x + size, yy + size), draw))
    sparkle_burst(cv, t, t0, x, yy, size * 0.7, 10)


def framed_nft(cv, t, g, m, x, y, t0, a=1.0, w=230, label=None, lcol=None, price=None, pcol=INK, note=None, hi=False):
    """NFT в золотой рамке (сравнения): рамка — из листа декора, под ней редкость, цена и подпись."""
    if t < t0:
        return
    p = pop(t, t0)
    fr = decor('frame', w)
    if hi:
        put(cv, glow((255, 200, 80)), x, y, w / 512 * 1.9 * p, a * (0.55 + 0.25 * math.sin(t * 5)))
    put(cv, fx.rounded(int(w * 0.8), int(fr.height * 0.78), 18, (255, 252, 244, 255)), x, y, p, a)
    put(cv, nft(g, m, int(fr.height * 0.66)), x, y + 2 * math.sin(t * 2 + x), p, a)
    put(cv, fr, x, y, p, a)
    yy = y + fr.height / 2 + 30
    if label:
        put(cv, upill(label, lcol or MUTED, 20, WHITE), x, yy, p, a)
        yy += 52
    if price:
        put(cv, utext(price, 30, 'ExtraBold', pcol), x, yy, p, a)
        yy += 44
    if note:
        put(cv, utext(note, 20, 'SemiBold', MUTED), x, yy, p, a)


def put_panel(cv, cx, cy, a, t0, t, h=PANEL_H):
    s = 0.7 + 0.3 * pop(t, t0)
    put(cv, panel(PANEL_W, h), cx, cy, s, a)
    return s


def txt_panel(cv, t, x, t0, t1, top, big, bot, big_col=NAVY):
    a = window_a(t, t0, t1, 0.3)
    if a <= 0:
        return
    s = put_panel(cv, x, SIDE_Y, a, t0, t)
    put(cv, utext(top, 20, 'SemiBold', MUTED), x, SIDE_Y - 100, s, a)
    im = utext(big, 44, 'ExtraBold', big_col)
    put(cv, im, x, SIDE_Y - 8, s * min(1.0, 205 / im.width), a)
    put(cv, utext(bot, 20, 'SemiBold', MUTED), x, SIDE_Y + 84, s, a)


def bars(cv, t, x, t0, t1, vals, labs, cols, top):
    a = window_a(t, t0, t1, 0.3)
    if a <= 0:
        return
    put_panel(cv, x, SIDE_Y, a, t0, t)
    g = ease((t - t0 - 0.2) / 0.8)
    base, maxh, hi = SIDE_Y + 92, 150, max(vals)
    n = len(vals)
    for j, (v, lab, col) in enumerate(zip(vals, labs, cols)):
        h = max(8, maxh * (v / hi) ** 0.6 * g)
        bx = x + (j - (n - 1) / 2) * (190 / n)
        def bar(d, mp, S, h=h, bx=bx, col=col):
            x0, y0 = mp(bx - 26, base - h)
            x1, y1 = mp(bx + 26, base)
            d.rounded_rectangle([x0, y0, x1, y1], int(10 * S), fill=col + (int(255 * a),))
        fx.over(cv, fx.draw_rgba((bx - 34, base - maxh - 10, bx + 34, base + 4), bar))
        put(cv, utext(lab, 15, 'SemiBold', INK), bx, base + 22, 1.0, a)
    put(cv, utext(top, 18, 'SemiBold', MUTED), x, SIDE_Y - 118, 1.0, a)


# ------------------------------------------------------------------ фон: белый + звёздная карта, оттенок по частям
TINTS = [  # (с какого времени, верх, низ)
    (0.0, (252, 248, 255), (242, 234, 252)),
    (E.SNAP + 1.5, (248, 248, 255), (232, 236, 252)),
    (E.BURN - 0.2, (255, 246, 240), (252, 228, 218)),
    (E.CREEPY_END, (246, 250, 255), (230, 238, 252)),
    (E.TEASE, (252, 248, 255), (238, 232, 252)),
    (E.EPIC, (248, 255, 252), (228, 246, 240)),
    (E.SHUFFLE, (255, 248, 252), (250, 230, 240)),
    (E.CHEAP, (248, 248, 252), (232, 232, 244)),
    (E.WHY, (255, 248, 246), (252, 234, 232)),
    (E.OUTRO, (250, 248, 255), (238, 232, 252)),
]


def tint_at(t):
    cur = TINTS[0]
    prev = TINTS[0]
    for k in TINTS:
        if t >= k[0]:
            prev, cur = cur, k
    u = ease((t - cur[0]) / 0.8)
    top = np.array(prev[1]) * (1 - u) + np.array(cur[1]) * u
    bot = np.array(prev[2]) * (1 - u) + np.array(cur[2]) * u
    return top.astype(np.float32), bot.astype(np.float32)


@functools.lru_cache(None)
def _yy():
    return np.linspace(0, 1, H, dtype=np.float32)[:, None, None]


@functools.lru_cache(None)
def starmap():
    """Едва заметная звёздная карта: созвездия, точки, кольцо зодиака за Митой. Рисуется один раз."""
    S = 2
    im = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(51)
    col = (60, 64, 130)
    for _ in range(9):                                    # созвездия
        cx, cy = rng.uniform(60, W - 60), rng.uniform(260, H - 300)
        pts = [(cx + rng.normal(0, 70), cy + rng.normal(0, 60)) for _ in range(int(rng.integers(4, 7)))]
        pts.sort(key=lambda p: p[0])
        for a, b in zip(pts, pts[1:]):
            d.line([a[0] * S, a[1] * S, b[0] * S, b[1] * S], fill=col + (34,), width=2 * S)
        for x, y in pts:
            fx.sparkle(d, x * S, y * S, 7 * S, col + (70,))
    for _ in range(160):                                  # звёздная пыль
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.2, 2.6)
        d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=col + (int(rng.uniform(26, 60)),))
    cx, cy, R = 540, 1060, 470                            # кольцо зодиака
    for rr, w_ in ((R, 3), (R - 46, 2)):
        d.ellipse([(cx - rr) * S, (cy - rr) * S, (cx + rr) * S, (cy + rr) * S], outline=col + (26,), width=w_ * S)
    zf = ImageFont.truetype(str(UFONT / 'Unbounded-SemiBold.ttf'), 30 * S)
    for k in range(12):
        a = k * math.pi / 6 - math.pi / 2
        x0, y0 = cx + math.cos(a) * (R - 46), cy + math.sin(a) * (R - 46)
        x1, y1 = cx + math.cos(a) * R, cy + math.sin(a) * R
        d.line([x0 * S, y0 * S, x1 * S, y1 * S], fill=col + (30,), width=2 * S)
        am = a + math.pi / 12
        fx.sparkle(d, (cx + math.cos(am) * (R - 23)) * S, (cy + math.sin(am) * (R - 23)) * S, 8 * S, col + (40,))
    return im.resize((W, H), Image.LANCZOS)


def background(t):
    top, bot = tint_at(t)
    yy = _yy()
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = top * (1 - yy) + bot * yy
    cv[..., 3] = 255
    put(cv, starmap(), 540 + 6 * math.sin(t * 0.12), 960 + 8 * math.sin(t * 0.09), 1.0, 1.0)
    # дрейфующие звёздочки
    def draw(d, mp, S):
        rng = np.random.default_rng(7)
        for j in range(26):
            x0, y0, sp = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 26)
            y = (y0 - t * sp) % (H + 40) - 20
            x = x0 + math.sin(t * 0.5 + j) * 16
            X, Y = mp(x, y)
            tw = 0.5 + 0.5 * math.sin(t * 2.2 + j * 1.7)
            c = GOLD if j % 3 else (150, 140, 220)
            fx.sparkle(d, X, Y, (5 + 6 * tw) * S, c + (int(50 + 90 * tw),))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), draw))
    return cv


# ------------------------------------------------------------------ заголовок
def headline_items():
    return [
        (E.HOOK_NFT, E.SNAP, 'ПОДАРКИ ТОЛЬКО ИЗ КРАФТА', PINK),
        (E.SNAP + E.SNAP_DUR, E.BURN - 0.1, 'КРАФТ: ОТ 1 ДО 4 ПОДАРКОВ', NAVY),
        (E.BURN - 0.1, E.CREEPY, 'НЕ ПОВЕЗЛО — ВСЁ СГОРЕЛО', RED),
        (E.CREEPY_END + 0.3, E.TIERS[0], 'ЕСТЬ ТОЛЬКО В КРАФТЕ', NAVY),
        (E.TIERS[0], E.TEASE, '4 УРОВНЯ РЕДКОСТИ', NAVY),
        (E.TEASE, AD_STOP + 0.2, 'РЕЖЕ ЗНАЧИТ ДОРОЖЕ?', NAVY),
        (E.EPIC + 0.2, E.SHUFFLE, 'ОДНА РЕДКОСТЬ — РАЗНАЯ ЦЕНА', NAVY),
        (E.SHUFFLE, E.CHEAP, 'НЕОБЫЧНАЯ ДОРОЖЕ ЛЕГЕНДАРКИ', NAVY),
        (E.SWEEP, E.WHY, 'ДЕШЕВЛЕ ПОТРАЧЕННОГО', RED),
        (E.WHY, E.OUTRO, 'ЦЕНУ ДЕЛАЮТ ЛЮДИ', NAVY),
        (E.OUTRO, DUR + 5, 'А ТЫ БЫ РИСКНУЛ?', PINK),
    ]


def headline(cv, t):
    for t0, t1, s_, col in headline_items():
        a = window_a(t, t0, t1, 0.25)
        if a > 0:
            im = upill(s_, col, 30, WHITE if col != GOLD else INK)
            put(cv, im, 540, 150, min(1.0, 1000 / im.width) * (0.85 + 0.15 * pop(t, t0, 0.35)), a)


# ------------------------------------------------------------------ сцены
def scene_hook(cv, t):
    a = 1 - appear(t, E.SNAP - 0.1, 0.35)
    if a <= 0 or t < E.HOOK_NFT:
        return
    trio = [(DC, 'Celestial Map', 250, 560), ('Jingle Bells', 'Maneki Neko', 540, 450), ('Resistance Dog', 'Satoshi', 830, 560)]
    for j, (g, m, x, y) in enumerate(trio):
        magic_nft(cv, t, g, m, x, y, 220, E.HOOK_NFT + 0.14 * j, a)
    # «только сделать из других подарков»: четыре обычных календаря слетаются в центральный
    k = (t - E.HOOK_CRAFT) / 0.8
    if 0 <= k < 1:
        for j, m in enumerate(REG):
            sx, sy = (90 if j % 2 == 0 else 990), (330 if j < 2 else 820)
            u = fx.ease_in(k)
            put(cv, nft(DC, m, 110), sx + (540 - sx) * u, sy + (450 - sy) * u, 1 - 0.6 * u, a * (1 - 0.3 * u))
    sparkle_burst(cv, t, E.HOOK_CRAFT + 0.8, 540, 450, 200, 18)
    txt_panel(cv, t, LX, E.HOOK_NO, E.SNAP - 0.05, 'улучшить', 'нельзя', 'не выпадут')
    txt_panel(cv, t, RX, E.HOOK_CRAFT + 0.2, E.SNAP - 0.05, 'только', 'крафт', 'из подарков', PINK)


SLOT_XY = [(700, 500), (900, 500), (700, 700), (900, 700)]


def scene_craft(cv, t):
    t0, t1 = E.SNAP + E.SNAP_DUR + 0.3, E.CREEPY + 0.05
    a = window_a(t, t0, t1, 0.3)
    if a <= 0:
        return
    burn = (t - E.BURN) / 0.9
    # слоты
    for j, (x, y) in enumerate(SLOT_XY):
        put(cv, fx.rounded(170, 150, 26, (255, 255, 255, 200), (226, 214, 176, 255), 3), x, y, 1.0, a * 0.95)
        ts = E.SLOTS[j]
        if t < ts:
            continue
        sh = 0.0
        if 0 <= burn < 1.6:
            sh = 6 * math.sin(t * 70 + j) * (1 - fx.clamp01(burn - 0.6))
        if burn < 0.55:
            magic_nft(cv, t, DC, REG[j], x + sh, y, 118, ts, a, bob=False)
            if burn > 0:
                put(cv, glow((255, 120, 40)), x, y, 0.5 + 0.4 * burn, a * burn * 1.6)
        else:
            k = fx.clamp01((burn - 0.55) / 0.4)
            put(cv, nft_grey(DC, REG[j], 118), x + sh, y, 1.0, a * (1 - k))
            put(cv, decor('ash', 130), x + sh, y + 10, 0.6 + 0.4 * k, a * k)
            put(cv, glow((255, 110, 30)), x, y + 20, 0.35, a * (1 - k) * 0.9)
    # магический круг и «шанс»
    sa = a * appear(t, E.CHANCE - 0.4, 0.4)
    if sa > 0:
        dim = 1 - 0.55 * fx.clamp01(burn)
        put(cv, glow((255, 200, 90)), 800, 1150, 0.75, sa * 0.5 * dim)
        put(cv, decor('sigil', 280), 800, 1150, 1.0, sa * dim, rot=t * 0.35)
        # шкала шанса — растёт с числом подарков, но до конца не доходит
        bw, bh, bx, by = 380, 34, 800, 1420
        fill = (0.25 + 0.63 * ease((t - E.CHANCE) / 1.3)) * dim
        put(cv, utext('шанс', 22, 'SemiBold', MUTED), bx, by - 46, 1.0, sa)
        put(cv, fx.rounded(bw, bh, bh // 2, (232, 228, 244, 255)), bx, by, 1.0, sa)
        fw = max(bh, int(bw * fill))
        put(cv, fx.rounded(fw, bh, bh // 2, GOLD + (255,)), bx - bw / 2 + fw / 2, by, 1.0, sa)
        na = sa * appear(t, E.NEVER, 0.3)
        if na > 0:
            def gap(d, mp, S):
                x0, y0 = mp(bx + bw / 2 - 30, by - 26)
                x1, y1 = mp(bx + bw / 2 - 30, by + 26)
                d.line([x0, y0, x1, y1], fill=RED + (int(255 * na),), width=int(5 * S))
            fx.over(cv, fx.draw_rgba((bx + bw / 2 - 50, by - 40, bx + bw / 2 - 10, by + 40), gap))
            put(cv, upill('до конца — никогда', RED, 20, WHITE), bx, by + 60, 0.8 + 0.2 * pop(t, E.NEVER), na)


CREEP_NFT = [('Jingle Bells', 'Yule Bells', 240), (DC, 'Balloon Face', 540), ('Resistance Dog', 'Chosen One', 840)]


def scene_creepy_nfts(cv, t):
    """Три сгоревших подарка из разных коллекций дрожат от страха над Митой (в жуткой сцене)."""
    a = appear(t, E.CREEPY + 0.3, 0.5) * (1 - ease((t - E.CREEPY_END) / 0.9))
    if a <= 0:
        return
    rng = np.random.default_rng(int(t * 60))
    for j, (g, m, x) in enumerate(CREEP_NFT):
        y = 560 + (24 if j == 1 else 0)
        sh = 3 + 5 * ease((t - E.CREEPY_MID) / 1.0)
        dx, dy = rng.normal(0, sh), rng.normal(0, sh * 0.6)
        put(cv, glow((200, 20, 30)), x, y, 0.62, a * 0.5)
        put(cv, nft_grey(g, m, 210, 0.7), x + dx, y + dy, 1.0, a * 0.95, rot=0.04 * math.sin(t * 31 + j))
        put(cv, decor('ash', 150), x + dx * 0.5, y + 118, 1.0, a * 0.8)


TIER_ROW = [('необычная', DC, 'Vacation'), ('редкая', DC, 'Grimoire'), ('эпическая', DC, 'Kronos'),
            ('легендарная', DC, 'Celestial Map')]
TIER_X = [150, 390, 690, 930]


def palm_xy(t):
    """Где ладонь Миты в клипе palm (≈ 215, 400 в кадре клипа 720×1280)."""
    g = M.GEO['palm']
    s = M.MITA_H / (g['bot'] - g['top'])
    return M.x_of(t) + (212 - g['hx']) * s, M.FOOT + (400 - g['bot']) * s


def scene_tiers(cv, t):
    a = window_a(t, E.CREEPY_END + 0.05, E.TEASE + 0.1, 0.3)
    if a <= 0:
        return
    # над ладонью — модель, которой нет нигде, кроме крафта
    px, py = palm_xy(t)
    k = ease((t - E.TIERS[3]) / 0.5)
    tx, ty = TIER_X[3], 520
    if t >= E.TIER_ONLY:
        x = px + (tx - px) * k
        y = py - 110 + (ty - (py - 110)) * k
        magic_nft(cv, t, DC, 'Celestial Map', x, y, int(170 - 20 * k), E.TIER_ONLY, a)
    for j, (lab, g, m) in enumerate(TIER_ROW[:3]):
        magic_nft(cv, t, g, m, TIER_X[j], 520, 150, E.TIERS[j], a)
    for j, (lab, g, m) in enumerate(TIER_ROW):
        if t >= E.TIERS[j]:
            put(cv, upill(lab, TIER_COL[lab], 19, WHITE), TIER_X[j], 640, pop(t, E.TIERS[j]), a)
    txt_panel(cv, t, RX, E.TIER_ONLY + 0.5, E.TEASE, 'больше', 'нигде', 'только крафт')
    txt_panel(cv, t, LX, E.TIERS[3] + 0.3, E.TEASE, 'редкости', '4', 'уровня')


def scene_tease(cv, t):
    a = window_a(t, E.TEASE, AD_STOP + 0.6, 0.3)
    if a <= 0:
        return
    for j, (lab, g, m) in enumerate(TIER_ROW):
        x = TIER_X[j]
        put(cv, nft(g, m, 120), x, 470 + 4 * math.sin(t * 2 + j), 1.0, a)
        put(cv, upill(lab, TIER_COL[lab], 17, WHITE), x, 560, 1.0, a)
        k = appear(t, E.TEASE + 0.25 + 0.2 * j, 0.3)
        put(cv, utext('₽' * (j + 1), 34, 'ExtraBold', GOLD), x, 625, 0.7 + 0.3 * k, a * k)
    k = appear(t, E.TEASE + 1.2, 0.35)
    put(cv, utext('?', 110, 'ExtraBold', PINK), 540, 740 + 8 * math.sin(t * 4), 0.6 + 0.4 * pop(t, E.TEASE + 1.2), a * k)
    txt_panel(cv, t, LX, E.TEASE + 0.3, AD_STOP + 0.5, 'реже', 'дороже', 'логично?')
    txt_panel(cv, t, RX, E.TEASE + 0.6, AD_STOP + 0.5, 'проверим', 'цены', 'с Fragment', PINK)


def scene_epic(cv, t):
    a = window_a(t, E.EPIC_BASE, E.SHUFFLE + 0.05, 0.3)
    if a <= 0:
        return
    framed_nft(cv, t, DC, 'Balloon Face', 190, 470, E.EPIC_BASE, a, 220, 'обычная', MUTED,
               rub(round(REG_FLOOR * RATE)), MUTED, 'не из крафта')
    framed_nft(cv, t, DC, 'Mánadagr', 540, 470, E.EPIC_CHEAP, a, 220, 'эпическая', TIER_COL['эпическая'],
               rub(rub_of(DC, 'Mánadagr')), INK, '≈ как кружка')
    framed_nft(cv, t, DC, 'Týsdagr', 890, 470, E.EPIC_RICH, a, 220, 'эпическая', TIER_COL['эпическая'],
               rub(rub_of(DC, 'Týsdagr')), PINK, '≈ как AirPods', hi=t > E.EPIC_RICH + 0.4)
    bars(cv, t, LX, E.EPIC_CHEAP + 0.4, E.SHUFFLE, [rub_of(DC, 'Mánadagr'), rub_of(DC, 'Týsdagr')],
         ['Mánadagr', 'Týsdagr'], [TIER_COL['эпическая'], PINK], 'обе эпические')
    txt_panel(cv, t, RX, E.EPIC_RICH + 0.5, E.SHUFFLE, 'редкость', 'одна', 'цена — разная', PINK)


def scene_shuffle(cv, t):
    a = window_a(t, E.SHUFFLE, E.CHEAP + 0.1, 0.3)
    if a <= 0:
        return
    framed_nft(cv, t, DC, 'Týsdagr', 190, 470, E.SHUFFLE + 0.2, a, 220, 'эпическая', TIER_COL['эпическая'],
               rub(rub_of(DC, 'Týsdagr')), MUTED)
    framed_nft(cv, t, DC, 'Celestial Map', 540, 470, E.SHUF_LEG, a, 220, 'легендарная', TIER_COL['легендарная'],
               rub(rub_of(DC, 'Celestial Map')), INK, 'самая дорогая')
    framed_nft(cv, t, DC, 'Shuffle', 890, 470, E.SHUF_SHOW, a, 220, 'необычная', TIER_COL['необычная'],
               rub(rub_of(DC, 'Shuffle')), PINK, 'дороже всех', hi=t > E.SHUF_X2)
    sparkle_burst(cv, t, E.SHUF_X2, 890, 470, 220, 18)
    bars(cv, t, LX, E.SHUF_LEG + 0.3, E.CHEAP, [rub_of(DC, 'Celestial Map'), rub_of(DC, 'Shuffle')],
         ['легенд.', 'Shuffle'], [TIER_COL['легендарная'], PINK], 'цена')
    txt_panel(cv, t, RX, E.SHUF_X2 + 0.2, E.CHEAP, 'необычная', 'дороже', 'легендарки', PINK)


def hand_after_sweep(t):
    g = M.GEO['sweep']
    s = M.MITA_H / (g['bot'] - g['top'])
    return M.x_of(t) + (690 - g['hx']) * s, M.FOOT + (430 - g['bot']) * s


GRID = [(110 + (i % 5) * 215, 300 + (i // 5) * 175) for i in range(15)]


def scene_cheap(cv, t):
    a = window_a(t, E.SWEEP, E.WHY + 0.4, 0.3)
    if a <= 0:
        return
    hx, hy = hand_after_sweep(E.SWEEP + 0.2)
    for j, ((g, m), (x, y)) in enumerate(zip(CHEAP_MODELS, GRID)):
        t0 = E.SWEEP + 0.05 + 0.06 * j
        k = ease((t - t0) / 0.6)
        if k <= 0:
            continue
        px, py = hx + (x - hx) * k, hy + (y - hy) * k - 120 * math.sin(math.pi * k)
        put(cv, nft(g, m, 110), px, py + 4 * math.sin(t * 2 + j), 0.4 + 0.6 * k, a * 0.92)
        if k > 0.95:
            r = rub_of(g, m)
            put(cv, upill(rub(r), (255, 255, 255), 15, MUTED), x, y + 70, 1.0, a * appear(t, t0 + 0.6, 0.3))
    # «чем четыре подарка, которые на них потратили»
    fa = a * appear(t, E.FOUR, 0.3)
    if fa > 0:
        s = put_panel(cv, LX, SIDE_Y, fa, E.FOUR, t)
        put(cv, utext('потратили', 19, 'SemiBold', MUTED), LX, SIDE_Y - 105, s, fa)
        for j, m in enumerate(REG):
            put(cv, nft(DC, m, 64), LX - 66 + 44 * j, SIDE_Y - 40 + (8 if j % 2 else 0), s, fa)
        put(cv, utext(rub(FOUR_RUB), 30, 'ExtraBold', RED), LX, SIDE_Y + 36, s, fa)
        put(cv, utext('4 подарка', 19, 'SemiBold', MUTED), LX, SIDE_Y + 88, s, fa)
    txt_panel(cv, t, RX, E.FOUR + 0.5, E.WHY, 'дешевле', f'{N_CHEAP} из {N_ALL}', 'моделей', RED)


def heart(d, X, Y, r, col):
    d.ellipse([X - r, Y - r, X, Y], fill=col)
    d.ellipse([X, Y - r, X + r, Y], fill=col)
    d.polygon([(X - r, Y - r * 0.45), (X + r, Y - r * 0.45), (X, Y + r * 0.95)], fill=col)


def scene_why(cv, t):
    a = window_a(t, E.WHY + 0.3, E.OUTRO + 0.1, 0.35)
    if a <= 0:
        return
    x, y = 770, 560
    magic_nft(cv, t, DC, 'Shuffle', x, y, 280, E.WHY + 0.3, a)
    la = a * appear(t, E.LOVE, 0.3)
    if la > 0:
        def draw(d, mp, S):
            rng = np.random.default_rng(3)
            for j in range(14):
                st = E.LOVE + rng.uniform(0, 1.2)
                u = ((t - st) / 1.6) % 1.0 if t > st else -1
                if u < 0:
                    continue
                X, Y = mp(x + rng.uniform(-170, 170) + 20 * math.sin(t * 3 + j), y + 120 - u * 360)
                heart(d, X, Y, (12 + 8 * rng.random()) * S, PINK + (int(220 * la * (1 - u)),))
        fx.over(cv, fx.draw_rgba((x - 260, y - 300, x + 260, y + 220), draw))
    put(cv, upill('нравится — значит дорого', NAVY, 21, WHITE), x, 770, pop(t, E.LOVE), la)
    txt_panel(cv, t, RX, E.WHY + 0.8, E.OUTRO, 'цену делает', 'не шанс', 'а люди', PINK)


def scene_outro(cv, t):
    a = appear(t, E.OUTRO, 0.35)
    if a <= 0:
        return
    put(cv, glow((255, 200, 90)), 770, 540, 0.7, a * 0.5)
    put(cv, decor('sigil', 280), 770, 540, pop(t, E.OUTRO), a, rot=t * 0.5)
    put(cv, utext('?', 100, 'ExtraBold', PINK), 770, 520 + 6 * math.sin(t * 4), pop(t, E.OUTRO + 0.2), a)
    k = appear(t, E.OUTRO_PILL, 0.3)
    put(cv, upill('Пиши в комментариях', PINK, 28, WHITE), 740, 760, 0.8 + 0.2 * pop(t, E.OUTRO_PILL), k)
    put(cv, decor('moon', 150), 960, 330, 1.0, a * 0.9, rot=0.08 * math.sin(t))
    put(cv, decor('telescope', 170), 600, 330, 1.0, a * 0.9)


def decor_corners(cv, t):
    """Мелкие детали звездочёта по частям ролика (не «китайский квартал»: 1–2 предмета на часть)."""
    items = [
        (E.SNAP + E.SNAP_DUR, E.BURN, 'moon', 150, 120, 330),
        (E.CREEPY_END + 0.3, E.TEASE, 'astrolabe', 120, 960, 1680),
        (E.EPIC, E.SHUFFLE, 'scroll', 120, 110, 1680),
        (E.SHUFFLE, E.CHEAP, 'telescope', 130, 975, 1690),
        (E.WHY, E.OUTRO, 'sparkles', 150, 960, 330),
    ]
    for t0, t1, name, w, x, y in items:
        a = window_a(t, t0 + 0.3, t1, 0.4)
        if a > 0:
            put(cv, decor(name, w), x, y + 6 * math.sin(t * 1.6 + x), pop(t, t0 + 0.3), a * 0.9)


# ------------------------------------------------------------------ жуть: тьма, красный туман, виньетка
@functools.lru_cache(None)
def fog_tex():
    rng = np.random.default_rng(4)
    n = rng.random((60, 70)).astype(np.float32)
    n = cv2.resize(n, (W * 2, H), interpolation=cv2.INTER_CUBIC)
    n = cv2.GaussianBlur(n, (0, 0), 60)
    n = (n - n.min()) / (n.max() - n.min())
    return n


@functools.lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - 540) / 620) ** 2 + ((yy - 1000) / 1050) ** 2)
    return np.clip((r - 0.55) / 0.6, 0, 1) ** 1.4


FADE_DARK = 1.1          # тьма уходит постепенно (автор: «не моментально, а рассеивается»)
FADE_FOG = 2.2           # туман рассеивается ещё дольше — редеет и уплывает вверх


def creepy_k(t):
    return appear(t, E.CREEPY, 0.35) * (1 - ease((t - E.CREEPY_END) / FADE_DARK))


def fog_k(t):
    return appear(t, E.CREEPY, 0.5) * (1 - ease((t - E.CREEPY_END) / FADE_FOG))


def creepy_bg(cv, t, k):
    dark = np.array([22, 4, 8], np.float32)
    yy = _yy()
    base = dark * (1 - yy) + np.array([60, 8, 14], np.float32) * yy
    cv[..., :3] = cv[..., :3] * (1 - k) + base * k


def creepy_fx(cv, t, k):
    fk = fog_k(t)
    f = fog_tex()
    off = int(t * 40) % W
    fog = f[:, off:off + W]
    lift = max(0.0, t - E.CREEPY_END)                     # при рассеивании туман уплывает вверх и редеет клочьями
    if lift > 0:
        fog = np.roll(fog, -int(lift * 160), axis=0)
        fog = np.clip((fog - 0.35 * ease(lift / FADE_FOG)) / (1 - 0.35 * ease(lift / FADE_FOG)), 0, 1)
    yy = _yy()[..., 0]
    alpha = (0.25 + 0.55 * yy) * fog * fk
    # пока светлеет, красный туман бледнеет до лёгкой белёсой дымки (на белом фоне — не «розовые пятна»)
    col = np.array([170, 14, 30], np.float32) * k + np.array([250, 244, 252], np.float32) * (1 - k)
    alpha = alpha * (0.45 + 0.55 * k)
    cv[..., :3] = cv[..., :3] * (1 - alpha[..., None] * 0.8) + col * alpha[..., None] * 0.8
    v = vignette() * k * 0.9
    cv[..., :3] *= (1 - v[..., None])


# ------------------------------------------------------------------ глитчи (вход и выход жути)
GLITCH = [(E.CREEPY - 0.04, 0.22, 0.9, True), (E.CREEPY + 1.2, 0.06, 0.4, True),
          (E.CREEPY_FULL + 0.1, 0.08, 0.5, True), (E.CREEPY_END - 0.05, 0.14, 0.45, True)]


def glitch_at(t):
    best = None
    for t0, d, s_, red in GLITCH:
        u = (t - t0) / d
        if 0 <= u < 1:
            k = s_ * math.sin(math.pi * u) ** 0.6
            if best is None or k > best[0]:
                best = (k, red)
    return best


def glitch(img, k, red, seed):
    rng = np.random.default_rng(seed)
    out = img.copy()
    y = 0
    while y < H:
        h = int(rng.integers(6, 64))
        if rng.random() < 0.55:
            out[y:y + h] = np.roll(img[y:y + h], int(rng.normal(0, 70 * k)), axis=1)
        y += h
    sh = int(6 + 22 * k)
    out[..., 0] = np.roll(out[..., 0], sh, axis=1)
    out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    f = out.astype(np.float32)
    f[::3] *= 0.8
    if red:
        f[..., 0] = np.minimum(255, f[..., 0] * 1.25 + 30 * k)
        f[..., 1] *= 0.7
        f[..., 2] *= 0.75
    mix = min(1.0, 0.35 + k)
    return np.clip(img * (1 - mix) + f * mix, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ субтитры
def _disp(w):
    return re.sub(r'[.,:;…!?]+$', '', w.replace('«', '').replace('»', ''))


def _chunks():
    out, cur = [], []
    for w in WORDS:
        if cur and (len(cur) >= 3 or cur[-1][3] != w[3] or sum(len(x[0]) for x in cur) + len(w[0]) > 20
                    or re.search(r'[.!?…:,]$', cur[-1][0])):
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
    acc = (255, 70, 80) if creepy else (PINK if t < E.SNAP + 1.5 else (214, 150, 20))
    base_col = (235, 220, 225) if creepy else INK
    dim_col = (120, 80, 90) if creepy else (150, 144, 170)
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = acc if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (base_col if on else dim_col)
        parts.append(((' ' if j else '') + _disp(w[0]).upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    p = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    fill = (30, 6, 12, 220) if creepy else (255, 255, 255, 232)
    border = (120, 20, 34) if creepy else (234, 222, 190)
    sy = SUB_Y_CREEPY if creepy else SUB_Y
    put(cv, fx.rounded(pw, 84, 30, fill, border + (255,), 3), 540, sy, 0.85 + 0.15 * p, 1.0)
    put(cv, im, 540, sy, sc * (0.85 + 0.15 * p), 1.0)


# ------------------------------------------------------------------ Мита: тень и щелчок
def mita_shadow(cv, x, y):
    put(cv, fx.radial(256, (60, 50, 110), 2.0, 1.0), x, y + 4, 1.0, 0.0)
    def draw(d, mp, S):
        X, Y = mp(x, y + 2)
        d.ellipse([X - 150 * S, Y - 18 * S, X + 150 * S, Y + 18 * S], fill=(60, 50, 110, 46))
    fx.over(cv, fx.draw_rgba((x - 170, y - 30, x + 170, y + 30), draw))


def snap_sparks(cv, t):
    lt = t - E.SNAP
    import snap_preview as SP
    if not 0 <= lt < E.SNAP_DUR:
        return
    on = ease((lt - SP.CLICK) / 0.5) * (1 - ease((lt - SP.FLASH - 0.5) / 0.9))
    if on <= 0:
        return
    k = M.snap_scale()
    def draw(d, mp, S):
        rng = np.random.default_rng(3)
        for j in range(30):
            u = ((lt - SP.CLICK) * rng.uniform(0.3, 0.6) + rng.uniform(0, 1)) % 1.0
            x = 540 + rng.uniform(-190, 190) * k * (1 - 0.3 * u)
            y = M.FOOT - u * 700 * k
            X, Y = mp(x, y)
            r = rng.uniform(2, 5) * 1.6 * S
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(255, 215, 120, int(220 * on * (1 - u))))
    fx.over(cv, fx.draw_rgba((60, 300, 1020, 1920), draw))
    # столб света
    a = on * 0.45
    if a > 0.01:
        put(cv, glow((255, 220, 140), 512, 1.2), 540, M.FOOT - 380, 1.5, a)


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    ck = creepy_k(t)
    if ck > 0:
        creepy_bg(cv, t, ck)
    if ck < 1:
        scene_hook(cv, t)
        scene_craft(cv, t)
        scene_tiers(cv, t)
        scene_tease(cv, t)
        scene_epic(cv, t)
        scene_shuffle(cv, t)
        scene_cheap(cv, t)
        scene_why(cv, t)
        scene_outro(cv, t)
        decor_corners(cv, t)
    scene_creepy_nfts(cv, t)
    if t != AD_STOP:
        M.draw(cv, t, put, mita_shadow if ck < 0.5 else None)
    snap_sparks(cv, t)
    if fog_k(t) > 0:
        creepy_fx(cv, t, ck)
    if ck < 0.4:
        headline(cv, t)
    if not (AD_STOP - 0.02 <= t < AD_STOP + 0.1):
        subtitles(cv, t)
    f = M.snap_flash(t) if E.SNAP <= t < E.SNAP + E.SNAP_DUR else 0.0
    if f > 0.01:
        cv[..., :3] = cv[..., :3] * (1 - min(1, f * 1.1)) + np.array([255, 252, 235], np.float32) * min(1, f * 1.1)
    img = np.clip(cv[..., :3], 0, 255).astype(np.uint8)
    g = glitch_at(t)
    if g:
        img = glitch(img, g[0], g[1], int(t * 60))
    return img


# ------------------------------------------------------------------ реклама: Мита на баннере колдует вниз
BAN_TOP = int(H / 2 - 283)
BAN_BOT = int(H / 2 + 284)


def ad_overlay(c, t):
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    lt = M.draw_ad(cv, bt, put, 540, BAN_TOP + 26, 600, a)
    # под баннером: золотой круг, искры и маленькие крафтовые NFT вылетают из него (баннер не закрыт)
    on = a * ease((lt - 1.6) / 0.6)
    if on > 0:
        cy = BAN_BOT + 120
        put(cv, glow((255, 200, 90)), 540, cy, 1.4, on * 0.55)
        sig = decor('sigil', 520).resize((520, 170), Image.LANCZOS)
        put(cv, sig, 540, cy, 1.0, on, rot=0.0)
        def draw(d, mp, S):
            rng = np.random.default_rng(9)
            for j in range(24):
                u = ((lt * rng.uniform(0.3, 0.6)) + rng.uniform(0, 1)) % 1.0
                x = 540 + rng.uniform(-250, 250)
                y = cy + 40 - u * 90
                X, Y = mp(x, y)
                fx.sparkle(d, X, Y, rng.uniform(6, 13) * S * (1 - u), (255, 214, 110, int(230 * on * (1 - u))))
        fx.over(cv, fx.draw_rgba((240, cy - 80, 840, cy + 80), draw))
        for j, (g, m) in enumerate(CHEAP_MODELS[:6]):
            st = 1.9 + j * 0.45
            u = ((lt - st) % 2.7) / 1.1 if lt > st else -1
            if 0 <= u < 1:
                side = -1 if j % 2 else 1
                x = 540 + side * (60 + 260 * ease(u))
                y = cy - 30 - 120 * math.sin(math.pi * u) + 140 * u * u
                put(cv, nft(g, m, 90), x, y, 0.5 + 0.5 * math.sin(math.pi * min(1, u * 1.4)), on * (1 - fx.clamp01((u - 0.8) / 0.2)))
    return cv[..., :3]


def out_frame(t, i=None):
    return np.clip(ad_overlay(BR.render(render_at, t, i).astype(np.float32), t), 0, 255).astype(np.uint8)


def frame_bytes(i):
    return out_frame(i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--out' in sys.argv:
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--out') + 1].split(','):
            Image.fromarray(out_frame(float(s))).save(out / f'o{float(s):06.2f}.png')
            print('o', s)
        raise SystemExit
    if '--content' in sys.argv:
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--content') + 1].split(','):
            Image.fromarray(render_at(float(s))).save(out / f'c{float(s):06.2f}.png')
            print('c', s)
        raise SystemExit
    frames.cli(out_frame, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
