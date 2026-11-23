"""«NFT-подарки в Стандоффе?!» — 1080×1920, 60 fps. Кадр — чистая функция времени содержания.
4 локации ChatGPT (комната, арена, магазин мерча, студия), Мита — клипы Gemini (4 наряда, логотип RubUp на одежде,
баннера нет). Переходы между нарядами: «загрузка матча» (скан), «распаковка» (коробка), «затвор камеры», «свайп ленты».
Экраны в локациях показывают идеи: брелоки на оружии, граффити, скин, агент, кубок, живые NFT, окно промокода,
мерч с QR-бирками, награда авторам в окне подарка Telegram."""
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
import frames
import fx
import mita55 as M
import events as E
from timeline import DUR, ON, END
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
A = HERE / 'build' / 'assets'
WHITE = (255, 255, 255)
INK = (28, 22, 44)
PINK = (236, 64, 150)
ORANGE = (255, 128, 30)
VIOLET = (140, 80, 235)
GOLD = (255, 196, 70)
CYAN = (70, 210, 255)
SUB_Y = 1752

# локации: картинка ChatGPT 1024×1536 «по высоте», масштаб k, сдвиг dy; где стоит Мита
LOC = {'room': dict(k=1.06, dy=-57, foot=1640, cx=540), 'arena': dict(k=1.0, dy=0, foot=1580, cx=540),
       'shop': dict(k=1.08, dy=-77, foot=1640, cx=540), 'studio': dict(k=1.0, dy=0, foot=1605, cx=540)}

# Мита: (начало, клип, локация, опорные точки «время ролика → время клипа»)
T1S = E.T1[0] + E.T1[1] * 0.5
T2S = E.T2[0] + E.T2[1] * 0.45
T3S = E.T3[0] + E.T3[1] * 0.5
T4S = E.T4[0] + E.T4[1] * 0.5
SEGS = [
    (0.0, 'hook', [(0.0, 0.2), (2.5, 2.4), (4.6, 3.9), (6.0, 5.1), (7.6, 6.6), (8.2, 7.1)]),
    (T1S - 0.4, 'gamer1', [(7.3, 0.3), (8.0, 0.9), (10.9, 3.4), (13.6, 5.2), (15.25, 7.0)]),
    (15.2, 'gamer2', [(15.2, 0.4), (19.2, 4.6), (20.6, 6.3), (22.5, 8.4), (24.8, 9.8)]),
    (24.75, 'gamer3', [(24.75, 0.6), (26.5, 2.2), (28.6, 4.2), (30.4, 5.3), (31.4, 6.5)]),
    (T2S - 0.1, 'collector1', [(30.7, 0.2), (33.3, 2.2), (36.2, 4.2), (37.4, 5.3), (39.0, 7.0), (41.5, 8.6),
                               (42.4, 9.5)]),
    (42.35, 'collector2', [(42.35, 0.3), (43.6, 1.6), (45.6, 3.7), (46.6, 4.6), (48.0, 6.3), (54.5, 9.9)]),
    (T3S - 0.3, 'blogger1', [(53.8, 0.3), (55.6, 2.2), (57.3, 3.4), (58.75, 4.4)]),
    (58.75, 'blogger2', [(58.75, 0.6), (60.6, 2.1), (62.8, 3.8), (64.4, 5.0), (66.2, 6.6), (67.9, 8.2)]),
    (67.9, 'blogger3', [(67.9, 0.5), (71.9, 2.5), (73.0, 3.2), (75.0, 5.6), (76.3, 7.2)]),
    (T4S - 0.3, 'outro', [(75.7, 0.3), (77.8, 2.6), (80.0, 3.6), (82.0, 5.0), (83.4, 5.4), (85.0, 7.2),
                          (85.6, 7.8), (86.6, 9.0), (87.6, 9.9)]),
]
SAME = {('gamer1', 'gamer2'), ('gamer2', 'gamer3'), ('collector1', 'collector2'), ('blogger1', 'blogger2'),
        ('blogger2', 'blogger3')}


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.3):
    return ease((t - t0) / d)


def window(t, t0, t1, d=0.3):
    return appear(t, t0, d) * (1 - appear(t, t1 - d, d))


def pop(t, t0, d=0.4):
    return fx.ease_out_back(fx.clamp01((t - t0) / d)) if t < t0 + d else 1.0


def put(cv, im, cx, cy, s=1.0, a=1.0, rot=0.0, anchor=None, add=False):
    if im is None or a <= 0.003 or s <= 0.003:
        return
    fx.over(cv, fx.warp(im, cx, cy, s, s, rot, anchor), a, add=add)


@functools.lru_cache(None)
def asset(name, size=None, h=None):
    im = Image.open(A / f'{name}.png').convert('RGBA')
    if size:
        s = size / max(im.size)
    elif h:
        s = h / im.height
    else:
        return im
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


@functools.lru_cache(None)
def text(s, size, weight='Heavy', color=WHITE, shadow=False):
    return fx.text_img(((s, color),), size, weight, shadow)


@functools.lru_cache(None)
def multi(parts, size, weight='Heavy', shadow=False):
    return fx.text_img(parts, size, weight, shadow)


@functools.lru_cache(None)
def pill(s, fill, size, tcol=WHITE):
    return fx.solid_pill(s, fill, size, tcol)


@functools.lru_cache(None)
def glow(c, n=512):
    g = np.array(fx.radial(n, (255, 255, 255), 1.8, 1.0))
    g[..., :3] = c
    return Image.fromarray(g)


def sparkles(cv, t, t0, cx, cy, spread, n=14, col=GOLD, dur=0.9):
    k = t - t0
    if not 0 <= k < dur:
        return
    rng = np.random.default_rng(int(t0 * 1000) + int(cx))

    def draw(d, mp, S):
        for _ in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            sp = rng.uniform(0.4, 1.0) * spread
            r = ease(k / dur) * sp
            x, y = mp(cx + math.cos(ang) * r, cy + math.sin(ang) * r)
            size = (1 - k / dur) * rng.uniform(10, 24) * S
            fx.sparkle(d, x, y, size, col + (int(255 * (1 - k / dur)),))
    fx.over(cv, fx.draw_rgba((cx - spread - 40, cy - spread - 40, cx + spread + 40, cy + spread + 40), draw))


# ------------------------------------------------------------------ фоны
@functools.lru_cache(None)
def bg(name):
    c = LOC[name]
    im = Image.open(HERE / 'input' / 'rooms' / f'{name}.png').convert('RGB')
    s = H / im.height * c['k']
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    left = (im.width - W) // 2
    top = round((im.height - H) / 2 - c['dy'])
    a = np.asarray(im, np.float32)[top:top + H, left:left + W]
    assert a.shape[:2] == (H, W), (name, a.shape)
    return a


def canvas(name):
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = bg(name)
    cv[..., 3] = 255
    return cv


def mita_seg(t):
    j = 0
    for i, s in enumerate(SEGS):
        if t >= s[0]:
            j = i
    return j


def draw_mita(cv, t, loc, alpha=1.0, j=None):
    c = LOC[loc]
    j = mita_seg(t) if j is None else j
    _, name, keys = SEGS[j]
    cur = M.placed(name, keys, t, c['cx'], c['foot'])
    if j > 0 and (SEGS[j - 1][1], name) in SAME and t - SEGS[j][0] < M.XF:
        prev = M.placed(SEGS[j - 1][1], SEGS[j - 1][2], t, c['cx'], c['foot'])
        cur = M.blend(prev, cur, ease((t - SEGS[j][0]) / M.XF))
    put(cv, glow((10, 0, 20), 256), c['cx'], c['foot'] - 4, 1.4, 0.35 * alpha)
    fx.over(cv, cur, alpha)


# ------------------------------------------------------------------ брелок на оружии
WEAPON_RING = {'knife': (0.885, 0.80), 'akr': (0.46, 0.50), 'skin_akr': (0.47, 0.52), 'deagle': (0.40, 0.55)}
CHARM_TOP = 0.06          # кольцо брелока — верх картинки


def weapon_charm(cv, t, weapon, charm, cx, cy, wwidth, t0, a=1.0, charm_h=None):
    im = asset(weapon, size=wwidth)
    put(cv, im, cx, cy, 1.0, a)
    rx, ry = WEAPON_RING[weapon]
    px, py = cx - im.width / 2 + rx * im.width, cy - im.height / 2 + ry * im.height
    ch = asset(charm, h=charm_h or int(wwidth * 0.24))
    u = max(0.0, t - t0)
    ang = 0.42 * math.exp(-u * 1.1) * math.sin(u * 5.2) + 0.07 * math.sin(t * 2.3)
    put(cv, ch, px, py, 1.0, a, ang, anchor=(ch.width / 2, ch.height * CHARM_TOP))


# ------------------------------------------------------------------ комната (хук, итог)
MON = (262, 601, 500, 380)          # центр и размер экрана монитора


def screen_label(cv, s, cx, cy, a, col=WHITE, size=30):
    put(cv, text(s, size, 'Heavy', col, True), cx, cy, 1.0, a)


def room_scene(cv, t):
    mx, my, mw, mh = MON
    if t < E.T2[0]:                                   # хук: на мониторе нож с брелоком-лисой
        put(cv, glow((255, 120, 200)), mx, my, 0.75, 0.22)
        weapon_charm(cv, t, 'knife', 'charm_fox', mx, my - 30, 420, -0.6, charm_h=150)
        screen_label(cv, 'NFT × STANDOFF 2', mx, my + 150, 1.0, (255, 150, 220), 28)
    else:                                             # итог: на мониторе скин-автомат с брелоком-кактусом
        put(cv, glow((140, 255, 120)), mx, my, 0.75, 0.18)
        weapon_charm(cv, t, 'skin_akr', 'charm_cactus', mx, my - 20, 460, E.T4[0], charm_h=120)
    if t > E.T4[0]:
        outro_scene(cv, t)


def outro_scene(cv, t):
    ic = [('charm_fox', 'ИГРЫ', ORANGE), ('merch_plush', 'МЕРЧ', PINK), ('award', 'БЛОГЕРЫ', VIOLET)]
    k = ease((t - E.MERGE) / 0.6)
    gone = appear(t, E.CARDS[0] - 0.4, 0.3)
    for i, (nm, lab, col) in enumerate(ic):
        a = appear(t, E.SUM[i], 0.25) * (1 - gone)
        if a <= 0:
            continue
        x0, y0 = (220, 540, 860)[i], 470
        x, y = x0 + (540 - x0) * k, y0 + (470 - y0) * k
        s = (0.7 + 0.3 * pop(t, E.SUM[i])) * (1 - 0.6 * k)
        put(cv, glow(col), x, y, 0.55 * s, 0.35 * a)
        put(cv, asset(nm, size=230), x, y + 4 * math.sin(t * 2 + i), s, a * (1 - k))
        put(cv, pill(lab, col, 28), x, y + 150, s, a * (1 - k))
    b = appear(t, E.MERGE + 0.45, 0.3) * (1 - gone)
    if b > 0:
        put(cv, glow(GOLD), 540, 470, 1.3, 0.35 * b * (0.8 + 0.2 * math.sin(t * 5)))
        put(cv, asset('obj7', size=330), 540, 470 + 6 * math.sin(t * 2.4), 0.7 + 0.3 * pop(t, E.MERGE + 0.45), b,
            0.05 * math.sin(t * 1.7))
        sparkles(cv, t, E.MERGE + 0.45, 540, 470, 300, 18)
    for i in range(3):
        a = appear(t, E.CARDS[i], 0.25)
        if a <= 0:
            continue
        x = (230, 540, 850)[i]
        s = 0.7 + 0.3 * pop(t, E.CARDS[i])
        nm, lab, col = ic[i]
        put(cv, fx.rounded(270, 330, 38, (255, 255, 255, 240), col + (255,), 6), x, 500, s, a)
        put(cv, text(str(i + 1), 120, 'Heavy', col), x, 410, s, a)
        put(cv, asset(nm, size=140), x, 540, s, a, 0.06 * math.sin(t * 2 + i))
        put(cv, text(lab, 34, 'Heavy', INK), x, 630, s, a)


# ------------------------------------------------------------------ арена (идея 1)
SCR = (540, 590)                    # центр полезной области экрана арены (видимая часть над головой Миты)


@functools.lru_cache(None)
def promo_window():
    im = Image.open(HERE / 'input' / 'props' / 'promo_window.png').convert('RGBA')
    s = 400 / im.height
    return im.resize((round(im.width * s), 400), Image.LANCZOS), s


PROMO_CODE = 'TG-SO2-MITA'


def arena_items(cv, t):
    cx, cy = SCR
    items = [
        (E.T1[0] + E.T1[1], E.SO2, 'title'), (E.SO2, E.CHARM, 'akr'), (E.CHARM, E.GRAF, 'knife'),
        (E.GRAF, E.SKIN, 'graffiti'), (E.SKIN, E.AGENT, 'skin'), (E.AGENT, E.TOURN, 'agent'),
        (E.TOURN, E.NFT3, 'trophy'), (E.NFT3, E.PROMO, 'nft'), (E.PROMO, E.T2[0] + 0.4, 'promo')]
    for t0, t1, kind in items:
        a = window(t, t0, t1 + 0.12, 0.22)
        if a <= 0:
            continue
        s = 0.85 + 0.15 * pop(t, t0, 0.35)
        if kind == 'title':
            r = window(t, t0, t0 + 0.9, 0.12)
            if r > 0:
                put(cv, text('ROUND 1', 96, 'Heavy', ORANGE, True), cx, cy, 0.8 + 0.3 * pop(t, t0, 0.3), r)
            b = appear(t, t0 + 0.8, 0.25)
            put(cv, text('ИДЕЯ 1', 64, 'Heavy', WHITE, True), cx, cy - 90, s, a * b)
            put(cv, text('КОЛЛАБОРАЦИЯ С ИГРАМИ', 44, 'Heavy', ORANGE, True), cx, cy - 20, s, a * b)
            for i, nm in enumerate(('obj0', 'gift_fox', 'obj2')):
                put(cv, asset(nm, size=120), cx - 200 + 200 * i, cy + 110 + 8 * math.sin(t * 3 + i), s, a * b)
        elif kind == 'akr':
            screen_label(cv, 'STANDOFF 2 × TELEGRAM', cx, cy - 170, a, ORANGE, 34)
            weapon_charm(cv, t, 'akr', 'charm_fox', cx, cy - 20, 820, t0, a, charm_h=170)
            screen_label(cv, 'российские разработчики', cx, cy + 165, a, WHITE, 28)
        elif kind == 'knife':
            weapon_charm(cv, t, 'knife', 'charm_cactus', cx - 40, cy - 30, 640, t0, a, charm_h=200)
            put(cv, pill('БРЕЛОК-ПОДАРОК', ORANGE, 30), cx, cy + 165, s, a)
        elif kind == 'graffiti':
            u = ease((t - t0) / 0.45)
            im = asset('graffiti', h=330)
            w = max(1, int(im.width * u))
            put(cv, im.crop((0, 0, w, im.height)), cx - im.width / 2 + w / 2, cy - 15, 1.0, a)
            if u < 1:
                sparkles(cv, t, t0, cx - im.width / 2 + w, cy, 90, 10, (120, 255, 80), 0.45)
            put(cv, pill('ГРАФФИТИ', PINK, 30), cx, cy + 165, s, a)
        elif kind == 'skin':
            x = cx + 420 * (1 - ease((t - t0) / 0.35))
            weapon_charm(cv, t, 'skin_akr', 'charm_heart', x, cy - 30, 860, t0, a, charm_h=150)
            put(cv, asset('sticker', h=110), x + 300, cy - 110, 1.0, a, 0.15)
            put(cv, pill('СКИН', (90, 200, 40), 30), cx, cy + 165, s, a)
        elif kind == 'agent':
            put(cv, glow(PINK), cx, cy, 0.9, 0.3 * a)
            put(cv, asset('agent', h=360), cx - 120, cy + 3 * math.sin(t * 2), s, a)
            put(cv, asset('gift_fox', size=150), cx + 170, cy - 40 + 8 * math.sin(t * 2.5), s, a, 0.08)
            put(cv, pill('АГЕНТ', VIOLET, 30), cx + 170, cy + 110, s, a)
        elif kind == 'trophy':
            put(cv, glow(GOLD), cx, cy - 20, 1.2, 0.35 * a * (0.8 + 0.2 * math.sin(t * 6)))
            put(cv, asset('trophy', h=360), cx, cy - 10 + 4 * math.sin(t * 2), s, a)
            put(cv, pill('ПРИЗ ТУРНИРА', GOLD, 30, INK), cx - 300, cy - 120, s, a)
            sparkles(cv, t, t0 + 0.1, cx, cy - 120, 220, 16)
        elif kind == 'nft':
            for i, nm in enumerate(('fox', 'heart', 'cactus')):
                ai = a * appear(t, t0 + 0.12 * i, 0.25)
                x = cx - 300 + 300 * i
                put(cv, glow((255, 140, 220)), x, cy - 20, 0.5, 0.3 * ai)
                put(cv, M.nft(nm, t + i, 230), x, cy - 20, 0.8 + 0.2 * pop(t, t0 + 0.12 * i), ai)
                put(cv, pill('1 из 1', (40, 30, 60), 24), x, cy + 125, 1.0, ai)
            put(cv, text('УНИКАЛЬНЫЕ NFT', 40, 'Heavy', (255, 150, 220), True), cx, cy - 175, 1.0, a)
        elif kind == 'promo':
            pw, ps = promo_window()
            put(cv, pw, cx, cy, s, a)
            fx0 = cx - pw.width / 2 * s
            fy0 = cy - pw.height / 2 * s
            k = fx.clamp01((t - E.TYPE0) / (E.APPLY - 0.1 - E.TYPE0))
            code = PROMO_CODE[:int(len(PROMO_CODE) * k + 0.001)]
            cur = '|' if (t * 2.5) % 1 < 0.55 and t < E.APPLY + 0.3 else ''
            put(cv, text(code + cur, 34, 'Heavy', WHITE), fx0 + 471 * ps * s, fy0 + 228 * ps * s, 1.0, a)
            if E.APPLY <= t < E.APPLY + 0.3:          # кнопка «ПРИМЕНИТЬ» нажата
                put(cv, glow(WHITE), fx0 + 480 * ps * s, fy0 + 517 * ps * s, 0.6, 0.5 * a)
            ok = appear(t, E.APPLY + 0.1, 0.2)
            if ok > 0:
                put(cv, pill('ПРОМОКОД АКТИВИРОВАН', (40, 190, 90), 26), cx, cy - 150, 1.0, a * ok)


def arena_fly(cv, t):
    """Голда, кейс и стикер вылетают из экрана к зрителю."""
    for nm, t0, x1, y1, lab in (('gold', E.GOLD, 230, 1050, 'G 500'), ('case', E.CASE, 860, 1080, 'КЕЙС'),
                               ('sticker', E.STICK, 840, 760, 'СТИКЕРЫ')):
        u = (t - t0) / 0.5
        if u < 0 or t > E.T2[0] + 0.3:
            continue
        k = ease(u)
        x, y = SCR[0] + (x1 - SCR[0]) * k, SCR[1] + (y1 - SCR[1]) * k - 120 * math.sin(math.pi * min(1, u))
        s = 0.35 + 0.65 * k
        put(cv, glow(GOLD), x, y, 0.6 * s, 0.3)
        put(cv, asset(nm, size=260), x, y + 6 * math.sin(t * 3), s, 1.0, 0.1 * math.sin(t * 2))
        if u > 0.8:
            put(cv, pill(lab, ORANGE if nm != 'sticker' else PINK, 26), x, y + 150 * s, 1.0, appear(t, t0 + 0.4))
        sparkles(cv, t, t0 + 0.45, x, y, 160, 12)


def arena_scene(cv, t):
    arena_items(cv, t)


# ------------------------------------------------------------------ магазин мерча (идея 2)
PLUSH = (190, 838, 230)       # x, низ (полка), высота
HOODIE = (905, 425, 330)      # x, верх (вешалка), высота
FIGURE = (870, 1372, 255)     # x, низ (витрина), высота


@functools.lru_cache(None)
def phone_frame(w=300, h=560):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 46, fill=(16, 16, 26, 255), outline=(90, 90, 110, 255), width=6)
    d.rounded_rectangle([14, 14, w - 15, h - 15], 36, fill=(34, 40, 60, 255))
    d.rounded_rectangle([w // 2 - 45, 22, w // 2 + 45, 38], 8, fill=(10, 10, 16, 255))
    return im


def creepy_k(t):
    return ease((t - E.CREEPY) / 0.35) * (1 - ease((t - E.CREEPY_END + 0.1) / 0.15))


def shop_scene(cv, t):
    ck = creepy_k(t)
    # «всё это — внутри экрана»: парящий экран с автоматом
    a = window(t, E.SCREEN, E.HOLD + 0.35, 0.3)
    if a > 0:
        put(cv, fx.rounded(560, 330, 34, (14, 14, 24, 245), (90, 210, 255, 255), 5), 540, 520, 1.0, a)
        weapon_charm(cv, t, 'skin_akr', 'charm_cactus', 540, 500, 470, E.SCREEN, a, charm_h=110)
    h = window(t, E.HOLD, E.MERCH + 0.4, 0.3)        # NFT «в руках»
    if h > 0:
        put(cv, glow((140, 255, 120)), 540, 1060, 0.6, 0.4 * h)
        put(cv, M.nft('cactus', t, 190), 540, 1060 - 10 * pop(t, E.HOLD, 0.5), 0.6 + 0.4 * pop(t, E.HOLD), h)
        sparkles(cv, t, E.HOLD + 0.2, 540, 1060, 150, 12, (140, 255, 120))
    # мерч появляется на полке, вешалке, в витрине
    x, b, hh = PLUSH
    pa = appear(t, E.PLUSH, 0.25) * (1 - appear(t, E.CREEPY + 0.25, 0.2))
    if pa > 0:
        im = asset('merch_plush', h=hh)
        put(cv, im, x, b - im.height / 2, 0.7 + 0.3 * pop(t, E.PLUSH), pa)
        sparkles(cv, t, E.PLUSH, x, b - hh / 2, 150, 12, PINK)
    x, top, hh = HOODIE
    ha = appear(t, E.HOODIE, 0.25)
    if ha > 0:
        im = asset('merch_hoodie', h=hh)
        put(cv, im, x, top + im.height / 2, 1.0, ha, 0.03 * math.sin(t * 1.6), anchor=(im.width / 2, 0))
        sparkles(cv, t, E.HOODIE, x, top + hh / 2, 160, 12, GOLD)
    x, b, hh = FIGURE
    fa = appear(t, E.FIGURE, 0.25)
    if fa > 0:
        im = asset('merch_figure', h=hh)
        put(cv, im, x, b - im.height / 2, 0.7 + 0.3 * pop(t, E.FIGURE), fa)
        sparkles(cv, t, E.FIGURE, x, b - hh / 2, 140, 12, PINK)
    for i, (nm, lab, col, tt) in enumerate((('merch_plush', 'игрушки', PINK, E.PLUSH), ('merch_hoodie', 'худи', INK, E.HOODIE),
                                            ('merch_figure', 'фигурки', VIOLET, E.FIGURE))):
        la = window(t, tt + 0.1, E.QR, 0.25)
        if la > 0:
            px, py = ((PLUSH[0], PLUSH[1] + 40), (HOODIE[0], HOODIE[1] + HOODIE[2] + 40), (FIGURE[0], FIGURE[1] - 300))[i]
            put(cv, pill(lab, col, 28), px, py, 0.8 + 0.2 * pop(t, tt + 0.1), la)
    # QR-бирки
    for i, (nm, px, py) in enumerate((('tag_cactus', 330, 745), ('tag_hoodie', 905, 865), ('tag_fox', 1010, 1215))):
        qa = appear(t, E.QR + 0.12 * i, 0.25) * (1 - ck) * (1 - appear(t, E.CREEPY, 0.2))
        if qa > 0:
            im = asset(nm, h=190)
            put(cv, im, px, py + im.height / 2, 0.7 + 0.3 * pop(t, E.QR + 0.12 * i), qa,
                0.08 * math.sin(t * 2.2 + i), anchor=(im.width / 2, 0))
    u = (t - E.SCAN) / 0.8                           # скан-луч по бирке худи
    if 0 <= u < 1:
        y = 865 + 40 + 120 * u
        put(cv, glow((255, 40, 60), 256), 905, y, 0.9, 0.5)
        fx.over(cv, fx.draw_rgba((820, y - 4, 990, y + 4), lambda d, mp, S: d.rectangle(
            [*mp(820, y - 2), *mp(990, y + 2)], fill=(255, 50, 70, 255))), 1.0)
    r = window(t, E.RARE, E.CREEPY - 0.1, 0.25)       # редкая модель в телефоне
    if r > 0:
        s = 0.7 + 0.3 * pop(t, E.RARE)
        put(cv, glow((140, 255, 120)), 540, 480, 1.0, 0.35 * r)
        put(cv, phone_frame(), 540, 480, s, r)
        put(cv, M.nft('cactus', t, 210), 540, 450, s, r)
        put(cv, pill('РЕДКАЯ МОДЕЛЬ', (60, 190, 60), 26), 540, 640, s, r)
        sparkles(cv, t, E.RARE + 0.15, 540, 480, 260, 16, (140, 255, 120))


def shop_creepy(cv, t):
    """Свет гаснет; плюшевый кактус на полке оживает (клип Gemini), в темноте светятся глаза."""
    ck = creepy_k(t)
    if ck <= 0:
        return
    fl = 1.0 if (math.sin(t * 29) > -0.4 and math.sin(t * 7.3) > -0.8) else 0.55
    cv[..., :3] *= 1 - 0.78 * ck * fl
    x, b, hh = PLUSH
    u = max(0.0, t - E.CREEPY)
    ct = M.clip_time([(0, 0.5), (2.4, 3.0), (4.5, 5.0), (6.0, 6.5)], u)
    im = M.nft_sprite('plush_creepy', M.idx('plush_creepy', ct), int(hh * 1.02))
    put(cv, glow((120, 20, 60)), x, b - hh / 2, 0.9, 0.5 * ck)
    put(cv, im, x, b - im.height / 2 + 6, 1.0, ck)
    e = ease((u - 2.6) / 0.6) * ck
    if e > 0:
        for dx in (-34, 34):
            put(cv, glow((255, 40, 170), 128), x + dx, b - hh * 0.55, 0.45, 0.9 * e, add=True)


# ------------------------------------------------------------------ студия (идея 3)
SSCR = (540, 513, 760, 380)       # центр и размер экрана студии
RING = (124, 1010)


@functools.lru_cache(None)
def tg_card():
    """Окно подарка Telegram: Creator Award #274 (владелец — Мита), 274/1 000 выпущено, ценность ~1 250 000 ₽."""
    w, h = 860, 520
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], 40 * S, fill=(30, 36, 46, 250))
    d.rounded_rectangle([0, 0, 360 * S, h * S - 1], 40 * S, fill=(52, 66, 86, 255))
    d.rectangle([320 * S, 0, 360 * S, h * S - 1], fill=(52, 66, 86, 255))
    rng = np.random.default_rng(3)
    for _ in range(26):                                # узор фона подарка: маленькие звёзды
        x, y = rng.uniform(20, 340) * S, rng.uniform(20, h - 20) * S
        fx.sparkle(d, x, y, rng.uniform(6, 11) * S, (90, 110, 140, 255))
    f = lambda sz, wt='Semibold': fx.font(wt, sz * S)
    d.text((180 * S, 420 * S), 'Creator Award', font=f(30, 'Bold'), fill=(255, 255, 255, 255), anchor='mm')
    d.text((180 * S, 458 * S), '#274', font=f(26), fill=(170, 180, 200, 255), anchor='mm')
    rows = [('Владелец', 'Mita'), ('Модель', 'Golden Camera'), ('Фон', 'Midnight'), ('Количество', '274/1 000 выпущено'),
            ('Ценность', '~1 250 000 ₽')]
    x0, y0, rh = 380, 40, 88
    for i, (k, v) in enumerate(rows):
        y = y0 + i * rh
        d.rounded_rectangle([x0 * S, y * S, (w - 24) * S, (y + rh - 10) * S], 16 * S, outline=(64, 72, 88, 255),
                            width=2 * S)
        d.text(((x0 + 20) * S, (y + rh / 2 - 5) * S), k, font=f(26, 'Bold'), fill=(235, 238, 245, 255), anchor='lm')
        col = (90, 170, 255, 255) if k == 'Владелец' else (235, 238, 245, 255)
        vx = x0 + 230 + (56 if k == 'Владелец' else 0)
        d.text((vx * S, (y + rh / 2 - 5) * S), v, font=f(26), fill=col, anchor='lm')
    im = im.resize((w, h), Image.LANCZOS)
    av = Image.open(HERE / 'input' / 'props' / 'avatar.png').convert('RGBA').resize((46, 46), Image.LANCZOS)
    m = Image.new('L', (46, 46), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 45, 45], fill=255)
    im.paste(av, (x0 + 230, y0 + 16), m)
    return im


def studio_scene(cv, t):
    cx, cy, sw, sh = SSCR
    on = appear(t, E.IDEA3 + 0.3, 0.15)
    put(cv, glow((255, 240, 255)), RING[0], RING[1], 0.9, 0.35 * on, add=True)   # кольцевая лампа
    cv[..., :3] *= 0.9 + 0.1 * on
    if (t * 1.6) % 1 < 0.6:                                                        # REC на камере
        put(cv, glow((255, 30, 30), 128), 1006, 1083, 0.3, 0.9, add=True)
        put(cv, text('REC', 26, 'Heavy', (255, 70, 70), True), 1000, 1030, 1.0, 1.0)
    a = window(t, E.T3[0] + E.T3[1], E.VIEWS + 0.1, 0.25)
    if a > 0:
        put(cv, text('ИДЕЯ 3', 60, 'Heavy', WHITE, True), cx, cy - 90, 1.0, a)
        put(cv, text('ПОДАРКИ ДЛЯ АВТОРОВ', 44, 'Heavy', (255, 120, 210), True), cx, cy - 25, 1.0, a)
        for i, nm in enumerate(('obj5', 'obj6', 'obj8')):
            put(cv, asset(nm, size=110), cx - 190 + 190 * i, cy + 100 + 8 * math.sin(t * 3 + i), 1.0, a)
    v = window(t, E.VIEWS, E.AWARD + 0.25, 0.2)
    if v > 0:
        k = ease((t - E.VIEWS) / (E.VIEWS_HIT - E.VIEWS))
        n = int(round(100000 * k / 100) * 100)
        put(cv, text(f'{n:,}'.replace(',', ' '), 110, 'Heavy', WHITE, True), cx, cy - 20,
            1.0 + 0.08 * math.sin(math.pi * fx.clamp01((t - E.VIEWS_HIT) / 0.3)), v)
        put(cv, text('просмотров', 40, 'Heavy', (255, 120, 210), True), cx, cy + 80, 1.0, v)
    w_ = window(t, E.AWARD, E.TGCARD + 0.2, 0.2)
    if w_ > 0:
        u = ease((t - E.AWARD) / 0.4)
        put(cv, glow(GOLD), cx, cy, 1.1, 0.4 * w_)
        put(cv, M.nft('award', t, 300), cx, cy - 300 * (1 - u), 0.7 + 0.3 * u, w_)
        sparkles(cv, t, E.AWARD + 0.38, cx, cy, 280, 18)
    c = window(t, E.TGCARD, E.GRID + 0.1, 0.25)
    if c > 0:
        s = 0.8 + 0.2 * pop(t, E.TGCARD)
        card = tg_card()
        put(cv, card, cx, cy + 30, s, c)
        ax, ay = cx + (-card.width / 2 + 180) * s, cy + 30 + (-card.height / 2 + 200) * s
        put(cv, M.nft('award', t, 250), ax, ay, s, c)
        if t > E.LIMIT:
            hl = 0.5 + 0.5 * math.sin((t - E.LIMIT) * 9)
            ry = cy + 30 + (-card.height / 2 + 40 + 3 * 88 + 39) * s
            fx.over(cv, fx.draw_rgba((cx - 60, ry - 46, cx + 420, ry + 46), lambda d, mp, S: d.rounded_rectangle(
                [*mp(cx - 50 * s, ry - 39 * s), *mp(cx + 406 * s, ry + 39 * s)], 16 * S, outline=(255, 200, 70, 255),
                width=int(4 * S))), c * (0.5 + 0.5 * hl))
    g = appear(t, E.GRID, 0.2) * (1 - appear(t, E.T4[0] + 0.3, 0.2))
    if g > 0:
        n = min(12, int(1 + 11 * fx.clamp01((t - E.GRID) / 3.2)))
        tw, th = 104, 170
        for i in range(n):
            r_, c_ = divmod(i, 6)
            x = cx - sw / 2 + 70 + c_ * 124
            y = cy - sh / 2 + 100 + r_ * 186
            put(cv, asset(f'thumb{i % 6}', h=th), x, y, pop(t, E.GRID + i * 0.27, 0.3), g)
        m_ = appear(t, E.MILLION - 0.4, 0.3)
        if m_ > 0:
            k = ease((t - E.MILLION + 0.4) / 0.8)
            put(cv, fx.rounded(640, 170, 34, (20, 14, 34, 235), (255, 90, 190, 255), 5), cx, cy, 1.0, g * m_)
            put(cv, text(f'{int(1000000 * k):,}+'.replace(',', ' '), 84, 'Heavy', WHITE, True), cx, cy - 20, 1.0, g * m_)
            put(cv, text('зрителей узнают о подарках', 30, 'Heavy', (255, 140, 210), True), cx, cy + 50, 1.0, g * m_)


# ------------------------------------------------------------------ сцена по локации
def loc_at(t):
    if t < T1S:
        return 'room'
    if t < T2S:
        return 'arena'
    if t < T3S:
        return 'shop'
    if t < T4S:
        return 'studio'
    return 'room'


def scene(loc, t, j=None):
    cv = canvas(loc)
    if loc == 'room':
        room_scene(cv, t)
    elif loc == 'arena':
        arena_scene(cv, t)
    elif loc == 'shop':
        shop_scene(cv, t)
    elif loc == 'studio':
        studio_scene(cv, t)
    if loc == 'shop':
        shop_creepy(cv, t)
    ck = creepy_k(t) if loc == 'shop' else 0.0
    draw_mita(cv, t, loc, 1.0 - 0.55 * ck, j)
    if loc == 'arena':
        arena_fly(cv, t)
    return cv


# ------------------------------------------------------------------ переходы
def seg_of_loc(loc, t):
    j = mita_seg(t)
    want = {'room': ('hook', 'outro'), 'arena': ('gamer',), 'shop': ('collector',), 'studio': ('blogger',)}[loc]
    while j > 0 and not SEGS[j][1].startswith(want):
        j -= 1
    while j < len(SEGS) - 1 and not SEGS[j][1].startswith(want):
        j += 1
    return j


def transition(t):
    """(кадр, None) во время перехода, иначе None."""
    for (t0, d), a, b, kind in ((E.T1, 'room', 'arena', 'scan'), (E.T2, 'arena', 'shop', 'box'),
                                (E.T3, 'shop', 'studio', 'shutter'), (E.T4, 'studio', 'room', 'swipe')):
        u = (t - t0) / d
        if not 0 <= u < 1:
            continue
        ja, jb = seg_of_loc(a, t - 0.001 if kind else t), seg_of_loc(b, t)
        if a == 'room':
            ja = 0
        if b == 'room':
            jb = len(SEGS) - 1
        if kind == 'scan':
            A_, B_ = scene(a, t, ja), scene(b, t, jb)
            y = int(H * (1 - ease(u)))
            out = A_.copy()
            out[y:] = B_[y:]
            put(out, glow(ORANGE), 540, y, 3.0, 0.7, add=True)
            fx.over(out, fx.draw_rgba((0, y - 6, W, y + 6), lambda dr, mp, S: dr.rectangle(
                [*mp(0, y - 3), *mp(W, y + 3)], fill=(255, 190, 90, 255))), 1.0)
            rng = np.random.default_rng(int(t * 60))
            for _ in range(40):                         # пиксели «собирают» новую сцену
                px, py = rng.integers(0, W), y + rng.integers(-60, 60)
                sz = int(rng.integers(6, 18))
                if 0 <= py < H - sz:
                    out[py:py + sz, px:px + sz, :3] = out[py:py + sz, px:px + sz, :3] * 0.3 + np.array(ORANGE) * 0.7
            return out
        if kind == 'box':
            sw = u >= 0.45
            out = scene(b if sw else a, t, jb if sw else ja)
            fall = ease(u / 0.35)
            y = -500 + (1250 + 500) * fall
            sq = 1.0 + (0.12 * math.sin(math.pi * fx.clamp01((u - 0.35) / 0.15)) if u > 0.35 else 0)
            open_k = ease((u - 0.55) / 0.35)
            box = asset('obj7', size=760)
            put(out, box, 540, y, 1.0 + 0.25 * open_k, 1 - open_k, 0.0)
            if u > 0.55:
                sparkles(out, t, E.T2[0] + E.T2[1] * 0.55, 540, 1150, 520, 30, PINK, 1.0)
                sparkles(out, t, E.T2[0] + E.T2[1] * 0.58, 540, 1150, 420, 24, GOLD, 1.0)
            return out
        if kind == 'shutter':
            sw = u >= 0.5
            out = scene(b if sw else a, t, jb if sw else ja)
            r = 1200 * (1 - ease(u / 0.45)) if u < 0.5 else 1200 * ease((u - 0.55) / 0.45)
            yy, xx = np.ogrid[:H, :W]
            ang = np.arctan2(yy - 960, xx - 540) + u * 2.5
            rr = np.hypot(yy - 960, xx - 540) * (1 + 0.08 * np.cos(6 * ang))      # шестигранная «диафрагма»
            m = (rr > r)[..., None]
            out[..., :3] = np.where(m, out[..., :3] * 0.04, out[..., :3])
            if sw:
                rec = appear(t, t0 + d * 0.55, 0.1)

                def vf(dr, mp, S):
                    for (x, y, dx, dy) in ((60, 300, 1, 1), (1020, 300, -1, 1), (60, 1620, 1, -1), (1020, 1620, -1, -1)):
                        X, Y = mp(x, y)
                        dr.line([X, Y, X + dx * 90 * S, Y], fill=(255, 255, 255, 230), width=int(6 * S))
                        dr.line([X, Y, X, Y + dy * 90 * S], fill=(255, 255, 255, 230), width=int(6 * S))
                fx.over(out, fx.draw_rgba((0, 0, W, H), vf), rec)
            return out
        if kind == 'swipe':
            k = ease(u)
            A_, B_ = scene(a, t, ja), scene(b, t, jb)
            off = int(H * k)
            out = np.empty_like(A_)
            out[:H - off] = A_[off:]
            out[H - off:] = B_[:off]
            return out
    return None


# ------------------------------------------------------------------ интерфейс поверх
SECT = [(0.0, T1S, 'NFT-ПОДАРКИ В СТАНДОФФЕ?!', PINK), (T1S, T2S, 'ИДЕЯ 1 · ИГРЫ', ORANGE),
        (T2S, T3S, 'ИДЕЯ 2 · МЕРЧ', PINK), (T3S, T4S, 'ИДЕЯ 3 · БЛОГЕРЫ', VIOLET),
        (T4S, DUR + 1, 'КАКАЯ ИДЕЯ ЛУЧШЕ?', PINK)]


def headline(cv, t):
    for t0, t1, s, col in SECT:
        a = (1.0 if t0 <= 0 else appear(t, t0, 0.25)) * (1 - appear(t, t1 - 0.2, 0.2))
        if a > 0:
            im = pill(s, col, 50)
            put(cv, im, 540, 140 + 8 * (1 - a), min(1.0, 1000 / im.width) * (1 + 0.015 * math.sin(t * 3)), a)


def chips(cv, t):
    cur = 0 if t < T1S else 1 if t < T2S else 2 if t < T3S else 3 if t < T4S else 4
    labs = ('ИГРЫ', 'МЕРЧ', 'БЛОГЕРЫ')
    for i in range(3):
        if cur == 0:
            s, fill, tc = f'{i + 1} · ?', (255, 255, 255), INK
        else:
            on = cur == i + 1
            done = cur > i + 1
            s = f'{i + 1} · {labs[i]}'
            fill = (ORANGE, PINK, VIOLET)[i] if on else ((40, 30, 60) if done or cur == 4 else (255, 255, 255))
            tc = WHITE if (on or done or cur == 4) else INK
        put(cv, pill(s, fill, 27, tc), 540 + (i - 1) * 250, 230, 1.0 + (0.06 * math.sin(t * 6) if cur == i + 1 else 0), 1.0)


EMO = [(E.HOOK_Q, 0), (14.3, 1), (E.TOURN + 0.3, 7), (E.APPLY + 0.2, 8), (33.6, 3), (E.PLUSH + 0.3, 2),
       (E.CREEPY + 0.3, 4), (55.4, 5), (E.LIMIT + 0.2, 7), (E.WINK + 0.2, 6), (E.MERGE + 0.3, 8), (E.CARDS[0], 0)]


def emotes(cv, t):
    loc = loc_at(t)
    top = LOC[loc]['foot'] - M.MH
    for t0, i in EMO:
        k = t - t0
        if not 0 <= k < 1.4:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 1.0) / 0.4))
        x = 720 + 5 * math.sin(t * 3)
        y = top + 40 - 30 * ease(k / 1.4)
        put(cv, asset(f'emo{i}', size=120), x, y, 0.6 + 0.4 * pop(t, t0, 0.35), a, -0.12 + 0.05 * math.sin(t * 5))


FLOAT = {'room': ('obj7', 'obj8'), 'arena': ('obj0', 'obj1'), 'shop': ('obj3', 'obj4'), 'studio': ('obj5', 'obj6')}


def floaters(cv, t):
    if creepy_k(t) > 0.2:
        return
    loc = loc_at(t)
    for side, nm in enumerate(FLOAT[loc]):
        x = (92, 988)[side] + 8 * math.sin(t * 0.9 + side * 2)
        y = 1470 + 14 * math.sin(t * 1.3 + side * 1.7)
        put(cv, glow((255, 200, 240)), x, y, 0.35, 0.25)
        put(cv, asset(nm, size=125), x, y, 1.0, 1.0, 0.12 * math.sin(t * 0.8 + side))


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
        t0 = c[0][1] - 0.06 if k else -1.0
        t1 = CHUNKS[k + 1][0][1] - 0.06 if k + 1 < len(CHUNKS) else c[-1][2] + 0.6
        t1 = min(t1, c[-1][2] + 0.7)
        if t0 <= t < t1:
            ch, start = c, t0
            break
    if ch is None:
        return
    acc = next(col for t0, t1, s, col in SECT if t0 <= t < t1)
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = acc if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (INK if on else (150, 144, 170))
        parts.append(((' ' if j else '') + w[0].strip('«»').upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    p = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    put(cv, fx.rounded(pw, 84, 30, (255, 255, 255, 235), acc + (255,), 3), 540, SUB_Y, 0.85 + 0.15 * p, 1.0)
    put(cv, im, 540, SUB_Y, sc * (0.85 + 0.15 * p), 1.0)


GLITCH = [(E.CREEPY - 0.04, 0.2, 0.8), (E.CREEPY + 2.5, 0.08, 0.5), (E.T3[0] - 0.08, 0.16, 1.0)]


def glitch_at(t):
    for t0, d, s_ in GLITCH:
        u = (t - t0) / d
        if 0 <= u < 1:
            return s_ * math.sin(math.pi * u) ** 0.6
    return 0.0


def glitch(img, k, seed):
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
    f[..., 0] = np.minimum(255, f[..., 0] * 1.25 + 30 * k)
    f[..., 1] *= 0.7
    mix = min(1.0, 0.35 + k)
    return np.clip(img * (1 - mix) + f * mix, 0, 255).astype(np.uint8)


def creepy_zoom(cv, t):
    """Единственный наезд в ролике: на жуткой сцене камера медленно подъезжает к плюшевому кактусу."""
    ck = creepy_k(t)
    if ck <= 0:
        return cv
    z = 1.0 + 0.22 * ease((t - E.CREEPY) / 4.5) * ck
    px, py = PLUSH[0] + 60, PLUSH[1] - PLUSH[2] / 2
    Mx = np.float32([[z, 0, (1 - z) * px], [0, z, (1 - z) * py]])
    return cv2.warpAffine(cv, Mx, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def render_at(t):
    cv = transition(t)
    if cv is None:
        cv = scene(loc_at(t), t)
    cv = creepy_zoom(cv, t)
    ck = creepy_k(t)
    if ck < 0.5:
        floaters(cv, t)
        headline(cv, t)
        chips(cv, t)
    else:                                              # жуть: красная виньетка
        yy, xx = np.ogrid[:H, :W]
        v = np.clip(np.hypot((yy - 900) / H, (xx - 300) / W) * 1.6, 0, 1)[..., None]
        cv[..., :3] = cv[..., :3] * (1 - 0.6 * v * ck) + np.array([60, 0, 10], np.float32) * 0.6 * v * ck
    emotes(cv, t)
    subtitles(cv, t)
    img = np.clip(cv[..., :3], 0, 255).astype(np.uint8)
    g = glitch_at(t)
    if g > 0:
        img = glitch(img, g, int(t * 60))
    return img


def frame_bytes(i):
    return render_at(i / FPS).tobytes()


if __name__ == '__main__':
    if '--out' in sys.argv:
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--out') + 1].split(','):
            Image.fromarray(render_at(float(s))).save(out / f'o{float(s):06.2f}.png')
            print('o', s, flush=True)
        raise SystemExit
    frames.cli(render_at, frame_bytes, W, H, FPS, int(DUR * FPS))
