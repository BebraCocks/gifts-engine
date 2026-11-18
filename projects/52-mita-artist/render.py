"""«Мита-художница: подарки, которым ещё не дорисовали скины» — 1080×1920, 60 fps. Кадр — чистая функция времени.
Фон — лист бумаги, на котором по ходу ролика копятся брызги краски и каракули на полях. Подарки «рисуются» линиями и
заливаются цветом. Жуть — тетрадь в клетку (без наезда), выход — вихрь краски. Реклама — мастерская скинов.
Финал — змейка из подарков на экране кнопочного телефона + выбор. Петля — лист бумаги в начале и в конце."""
import functools
import json
import math
import re
import sys
import colorsys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
import banner
import frames
import fx
import gifts_api
import events as E
import mita52 as M
from timeline import DUR, ON, END, AD_STOP
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
GIFTS = HERE / 'input' / 'gifts'
DECOR = HERE / 'input' / 'decor'
DECOR51 = HERE.parent / '51-mita-craft' / 'input' / 'decor'
UFONT = HERE.parent / '51-mita-craft' / 'input' / 'fonts'
INK = (34, 30, 56)
MUTED = (118, 112, 136)
WHITE = (255, 255, 255)
TEAL = (32, 178, 170)
YELLOW = (246, 196, 52)
ORANGE = (244, 128, 48)
BLUE = (66, 136, 226)
RED = (220, 54, 60)
PINK = (232, 70, 130)
PAINTS = [TEAL, YELLOW, ORANGE, BLUE, (150, 90, 210), RED]
SUB_Y = 1628
SIDE_Y = 1170
LX, RX = 150, 930
PANEL_W, PANEL_H = 240, 300
HUNDRED = json.loads((HERE / 'data' / 'hundred_models.json').read_text(encoding='utf-8'))
# готовность скинов (оценка по карточке @ideanode)
CARD = [('plane', 0.92), ('icecream', 0.78), ('star', 0.62), ('sandcastle', 0.58), ('horse', 0.62), ('coconut', 0.6),
        ('kulich', 0.56), ('may1', 0.34), ('eight', 0.14), ('contest', 0.04), ('chain', 0.02), ('sneakers', 0.0),
        ('shirt', 0.0), ('briefcase', 0.0), ('tomb', 0.0), ('coffin', 0.0), ('dove', 0.0)]


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
def utext(s_, size, weight='SemiBold', color=INK):
    f = ufont(weight, size)
    l, t_, r, b_ = f.getbbox(s_)
    asc, desc = f.getmetrics()
    im = Image.new('RGBA', (r + 16, asc + desc + 16), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8, 8), s_, font=f, fill=color + (255,))
    return im


@functools.lru_cache(None)
def multi(parts, size, weight='Heavy'):
    return fx.text_img(parts, size, weight, False)


@functools.lru_cache(None)
def brush_pill(s_, col, size=28, tcol=WHITE, seed=0):
    """Плашка в виде мазка краски (неровные края, капли)."""
    f = ufont('ExtraBold', size * 2)
    tw = int(f.getlength(s_))
    S = 2
    w_, h_ = tw + 90 * S, int(size * 2.2) * S
    im = Image.new('RGBA', (w_, h_ + 20 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed + len(s_))
    n = 14
    top = [(w_ * k / n, 8 * S + rng.uniform(-5, 5) * S) for k in range(n + 1)]
    bot = [(w_ * k / n, h_ - 6 * S + rng.uniform(-6, 6) * S) for k in range(n, -1, -1)]
    pts = [(10 * S, h_ * 0.5)] + top[1:-1] + [(w_ - 6 * S, h_ * 0.45)] + bot[1:-1]
    d.polygon(pts, fill=col + (255,))
    for k in range(3):
        x = rng.uniform(0.2, 0.8) * w_
        d.ellipse([x - 6 * S, h_ - 8 * S, x + 6 * S, h_ + (8 + 6 * k) * S], fill=col + (255,))
    d.text((w_ / 2, h_ / 2 + 2 * S), s_, font=f, fill=tcol + (255,), anchor='mm')
    return im.resize((w_ // S, (h_ + 20 * S) // S), Image.LANCZOS)


@functools.lru_cache(None)
def gift(name, size):
    im = Image.open(GIFTS / f'{name}.png').convert('RGBA')
    s = size / max(im.size)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


@functools.lru_cache(None)
def decor(name, w):
    p = DECOR / f'{name}.png'
    if not p.exists():
        p = DECOR51 / f'{name}.png'
    im = Image.open(p).convert('RGBA')
    return im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)


@functools.lru_cache(maxsize=64)
def sketch(name, size):
    """Карандашный набросок подарка: контуры + лёгкая штриховка, серый графит."""
    im = gift(name, size) if name != 'chain' else chain_gift(size)
    a = np.array(im).astype(np.float32)
    al = a[..., 3] / 255
    lum = (a[..., :3].mean(-1) * al + 255 * (1 - al)).astype(np.uint8)
    e1 = cv2.Canny(lum, 40, 110).astype(np.float32) / 255
    e2 = cv2.Canny((al * 255).astype(np.uint8), 50, 150).astype(np.float32) / 255
    e = np.clip(cv2.GaussianBlur(np.maximum(e1 * 0.8, e2), (0, 0), 0.6) * 1.6, 0, 1)
    hatch = ((np.add.outer(np.arange(a.shape[0]), np.arange(a.shape[1])) % 9) < 1.5).astype(np.float32)
    shade = (1 - lum / 255.0) * al
    alpha = np.clip(np.maximum(e, hatch * shade * 0.45) + al * 0.08, 0, 1)
    rgb = np.zeros(a.shape[:2] + (3,), np.float32) + np.array([88, 86, 96], np.float32)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8))


@functools.lru_cache(maxsize=64)
def grey(name, size, k=0.9):
    im = gift(name, size) if name != 'chain' else chain_gift(size)
    a = np.array(im).astype(np.float32)
    lum = a[..., :3].mean(-1, keepdims=True)
    a[..., :3] = a[..., :3] * (1 - k) + (lum * 0.8 + 30) * k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


@functools.lru_cache(maxsize=8)
def chain_gift(size):
    """Засекреченный подарок: тёмная коробка со знаком вопроса под крест-накрест цепями (рисуем сами)."""
    S = 2
    n = size * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([n * 0.12, n * 0.18, n * 0.88, n * 0.9], int(n * 0.08), fill=(70, 60, 92, 255),
                        outline=(40, 34, 56, 255), width=int(6 * S))
    d.rectangle([n * 0.44, n * 0.18, n * 0.56, n * 0.9], fill=(220, 70, 110, 255))
    d.ellipse([n * 0.33, n * 0.06, n * 0.5, n * 0.22], outline=(220, 70, 110, 255), width=int(10 * S))
    d.ellipse([n * 0.5, n * 0.06, n * 0.67, n * 0.22], outline=(220, 70, 110, 255), width=int(10 * S))
    d.text((n / 2, n * 0.55), '?', font=ufont('ExtraBold', int(n * 0.42)), fill=(255, 255, 255, 255), anchor='mm')
    for (x0, y0, x1, y1) in ((0.02, 0.2, 0.98, 0.88), (0.02, 0.88, 0.98, 0.2)):
        L = 11
        for k in range(L + 1):
            u = k / L
            x, y = (x0 + (x1 - x0) * u) * n, (y0 + (y1 - y0) * u) * n
            r = n * 0.045
            if k % 2:
                d.ellipse([x - r * 1.3, y - r * 0.7, x + r * 1.3, y + r * 0.7], outline=(150, 156, 170, 255), width=int(7 * S))
            else:
                d.ellipse([x - r * 0.7, y - r * 1.3, x + r * 0.7, y + r * 1.3], outline=(196, 200, 210, 255), width=int(7 * S))
    return im.resize((size, size), Image.LANCZOS)


def drawn_gift(cv, t, name, x, y, size, t0, a=1.0, greyed=0.0, bob=True, anim=None):
    """Подарок «рисуется»: сначала карандашный контур сверху вниз, потом заливка цветом снизу вверх."""
    if t < t0:
        return
    k = (t - t0) / 0.7
    yy = y + (6 * math.sin(t * 2 + x * 0.01) if bob else 0)
    sk = sketch(name, size)
    if k < 1:
        put(cv, wipe(sk, min(1, k * 2), True), x, yy, 1.0, a)
    col_k = fx.clamp01(k * 2 - 1)
    if col_k <= 0:
        return
    img = anim_frame(anim, t, size) if anim and greyed < 0.01 else None
    img = img or gift(name, size)
    if greyed > 0:
        put(cv, img, x, yy, 1.0, a * (1 - greyed))
        put(cv, grey(name, size), x, yy - 6 * greyed, 1.0, a * greyed)
        return
    put(cv, wipe(img, col_k, False) if col_k < 1 else img, x, yy, 1.0, a)
    if k < 1.3:
        paint_specks(cv, t, t0 + 0.35, x, yy, size * 0.6)


def wipe(im, k, from_top):
    a = np.array(im)
    h = a.shape[0]
    yy = np.arange(h, dtype=np.float32)[:, None]
    if from_top:
        m = np.clip((k * (h + 30) - 15 - yy) / 15 + 0.5, 0, 1)
    else:
        m = np.clip((yy - (h - k * (h + 30) + 15)) / 15 + 0.5, 0, 1)
    a = a.copy()
    a[..., 3] = (a[..., 3] * m).astype(np.uint8)
    return Image.fromarray(a)


@functools.lru_cache(maxsize=420)
def _anim_png(name, idx, size):
    im = Image.open(GIFTS / name / f'f{idx:03d}.png').convert('RGBA')
    s = size * 1.25 / max(im.size)
    return im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)


@functools.lru_cache(None)
def _anim_n(name):
    return len(list((GIFTS / name).glob('f*.png'))), float((GIFTS / name / 'fps.txt').read_text())


def anim_frame(name, t, size):
    n, f = _anim_n(name)
    return _anim_png(name, int(t * f) % n + 1, size)


def paint_specks(cv, t, t0, cx, cy, spread, n=12):
    k = t - t0
    if not 0 <= k < 0.8:
        return
    rng = np.random.default_rng(int(t0 * 997 + cx))
    def draw(d, mp, S):
        for j in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            r = ease(k / 0.8) * rng.uniform(0.5, 1.0) * spread
            X, Y = mp(cx + math.cos(ang) * r, cy + math.sin(ang) * r)
            rr = (1 - k / 0.8) * rng.uniform(5, 11) * S
            c = PAINTS[j % len(PAINTS)]
            d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=c + (int(230 * (1 - k / 0.8)),))
    fx.over(cv, fx.draw_rgba((cx - spread - 30, cy - spread - 30, cx + spread + 30, cy + spread + 30), draw))


@functools.lru_cache(None)
def panel(w=PANEL_W, h=PANEL_H):
    im = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0))
    im.alpha_composite(fx.soft_shadow(w, h, 30, 18, 0.14).resize((w + 60, h + 60)))
    im.alpha_composite(fx.rounded(w, h, 26, (255, 253, 246, 245), (236, 226, 200, 255), 3), (30, 26))
    return im


def tape(cv, x, y, a, col=(250, 226, 140), rot=0.0):
    put(cv, fx.rounded(90, 30, 4, col + (200,)), x, y, 1.0, a, rot)


def txt_panel(cv, t, x, t0, t1, top, big, bot, big_col=INK):
    """Боковая панель-«листок на скотче»."""
    a = window_a(t, t0, t1, 0.3)
    if a <= 0:
        return
    s = 0.7 + 0.3 * pop(t, t0)
    rot = 0.04 if x > 540 else -0.04
    put(cv, panel(), x, SIDE_Y, s, a, rot)
    tape(cv, x, SIDE_Y - PANEL_H / 2 + 6, a, (250, 226, 140) if x < 540 else (170, 225, 215), -rot * 3)
    put(cv, utext(top, 20, 'SemiBold', MUTED), x, SIDE_Y - 92, s, a)
    im = utext(big, 44, 'ExtraBold', big_col)
    put(cv, im, x, SIDE_Y - 4, s * min(1.0, 205 / im.width), a)
    put(cv, utext(bot, 20, 'SemiBold', MUTED), x, SIDE_Y + 84, s, a)


# ------------------------------------------------------------------ фон: лист бумаги + копящиеся брызги и каракули
@functools.lru_cache(None)
def paper():
    rng = np.random.default_rng(52)
    base = np.ones((H, W, 3), np.float32) * np.array([252, 250, 244], np.float32)
    n = rng.normal(0, 2.2, (H // 4, W // 4)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)
    base += n[..., None]
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    base -= yy * 8
    return base


@functools.lru_cache(None)
def splash_layer(i):
    rng = np.random.default_rng(100 + i)
    S = 2
    side = rng.integers(0, 4)
    x = rng.uniform(40, W - 40) if side < 2 else (rng.uniform(20, 160) if side == 2 else rng.uniform(920, 1060))
    y = rng.uniform(220, 1880) if side >= 2 else (rng.uniform(190, 260) if side == 0 else rng.uniform(1760, 1890))
    r = rng.uniform(10, 26)
    c = PAINTS[rng.integers(len(PAINTS))]
    im = Image.new('RGBA', (int(8 * r) * S, int(8 * r) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = 4 * r * S
    d.ellipse([cx - r * S, cy - r * S, cx + r * S, cy + r * S], fill=c + (110,))
    for k in range(7):
        a = rng.uniform(0, 6.28)
        rr = r * rng.uniform(1.3, 2.6) * S
        s = r * rng.uniform(0.15, 0.35) * S
        d.ellipse([cx + math.cos(a) * rr - s, cy + math.sin(a) * rr - s, cx + math.cos(a) * rr + s, cy + math.sin(a) * rr + s], fill=c + (110,))
    return im.resize((im.width // S, im.height // S), Image.LANCZOS), x, y


@functools.lru_cache(None)
def doodle_layer(i):
    rng = np.random.default_rng(300 + i)
    x = rng.uniform(30, 180) if i % 2 else rng.uniform(900, 1050)
    y = rng.uniform(300, 1500)
    S = 2
    im = Image.new('RGBA', (180 * S, 140 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    kind = i % 4
    col = (130, 128, 140, 120)
    if kind == 0:   # спираль
        pts = [(90 * S + math.cos(a) * a * 6 * S, 70 * S + math.sin(a) * a * 6 * S) for a in np.linspace(0, 10, 60)]
        d.line(pts, fill=col, width=3 * S)
    elif kind == 1:  # звёздочка
        pts = [(90 * S + math.cos(a) * (40 if k % 2 == 0 else 16) * S, 70 * S + math.sin(a) * (40 if k % 2 == 0 else 16) * S)
               for k, a in enumerate(np.linspace(-math.pi / 2, 1.5 * math.pi, 11))]
        d.line(pts, fill=col, width=3 * S)
    elif kind == 2:  # сердечко
        pts = [(90 * S + 16 * math.sin(a) ** 3 * 2.4 * S, 70 * S - (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) * 2.4 * S)
               for a in np.linspace(0, 2 * math.pi, 60)]
        d.line(pts, fill=col, width=3 * S)
    else:           # волнистая линия
        pts = [(20 * S + k * 4 * S, 70 * S + math.sin(k * 0.4) * 18 * S) for k in range(36)]
        d.line(pts, fill=col, width=3 * S)
    return im.resize((180, 140), Image.LANCZOS), x, y


def background(t):
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = paper()
    cv[..., 3] = 255
    # брызги и каракули копятся: в начале лист чистый, к концу — «живой»
    n_spl = int(min(22, 2 + t * 0.38))
    for i in range(n_spl):
        im, x, y = splash_layer(i)
        t_i = (i - 2) / 0.38
        put(cv, im, x, y, 0.6 + 0.4 * pop(t, t_i, 0.3), 1.0)
    n_dd = int(min(10, t * 0.18))
    for i in range(n_dd):
        im, x, y = doodle_layer(i)
        put(cv, im, x, y, 1.0, appear(t, i / 0.18, 0.6))
    return cv


# ------------------------------------------------------------------ заголовок
def headline_items():
    return [
        (E.G_KULICH, E.MANY, 'ПОДАРКИ БЕЗ СКИНОВ', PINK),
        (E.MANY, E.CARD, 'ИХ ЦЕЛАЯ КУЧА', ORANGE),
        (E.CARD, E.ERASE1, 'КАРТОЧКА ГОТОВНОСТИ', TEAL),
        (E.ERASE1 + 0.3, E.CREEPY, 'ЗАСЕКРЕЧЕН', (110, 90, 170)),
        (E.CREEPY_END + 0.5, E.WHY, 'ОБЕЩАЮТ ДО КОНЦА ГОДА', TEAL),
        (E.WHY, AD_STOP + 0.3, 'ПОЧЕМУ ТАК ДОЛГО?', ORANGE),
        (ON[9], E.CONTEST, 'СКИНОВ НА ПОДАРОК', BLUE),
        (E.CONTEST, E.KEEP, 'КОНКУРСНЫЕ СКИНЫ', YELLOW),
        (E.KEEP, E.ERASE2, 'ХРАНИ КУЛИЧ', PINK),
    ]


def headline(cv, t):
    for t0, t1, s_, col in headline_items():
        a = window_a(t, t0, t1, 0.25)
        if a > 0:
            im = brush_pill(s_, col, 30, INK if col == YELLOW else WHITE)
            put(cv, im, 540, 150, min(1.0, 1000 / im.width) * (0.85 + 0.15 * pop(t, t0, 0.35)), a, -0.02)


# ------------------------------------------------------------------ сцены
HOOK3 = [('kulich', 230, 470, 'kulich_anim', E.G_KULICH), ('icecream', 540, 420, 'icecream_anim', E.G_ICE),
         ('star', 850, 470, 'star_anim', E.G_STAR)]


def scene_hook(cv, t):
    a = 1 - appear(t, E.MANY + 0.3, 0.4)
    if a <= 0 or t < E.G_KULICH:
        return
    g = ease((t - E.NO_SKIN) / 0.6)
    for name, x, y, an, t0 in HOOK3:
        drawn_gift(cv, t, name, x, y, 230, t0, a, greyed=g, anim=an)
        if g > 0.3:     # грустная капелька краски стекает
            u = ((t - E.NO_SKIN) % 1.4) / 1.4
            put(cv, glow_dot(), x + 60, y + 60 + 40 * u, 1.0, a * g * (1 - u))
    txt_panel(cv, t, LX, E.G_STAR + 1.0, E.MANY + 0.3, 'вышли', 'год+', 'назад')
    txt_panel(cv, t, RX, E.NO_SKIN + 0.2, E.MANY + 0.3, 'скинов', '0', 'до сих пор', RED)


@functools.lru_cache(None)
def glow_dot():
    im = Image.new('RGBA', (40, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([10, 22, 30, 42], fill=TEAL + (220,))
    d.polygon([(20, 6), (12, 30), (28, 30)], fill=TEAL + (220,))
    return im


MANY_POS = [(120 + (i % 6) * 168, 300 + (i // 6) * 150) for i in range(18)]


def scene_many(cv, t):
    """«Целая куча»: невышедшие подарки высыпают серыми набросками над Митой."""
    a = window_a(t, E.MANY, E.CARD + 0.4, 0.3)
    if a <= 0:
        return
    names = [c[0] for c in CARD]
    for j, name in enumerate(names):
        x, y = MANY_POS[j]
        t0 = E.MANY + 0.05 * j
        if t < t0:
            continue
        p = pop(t, t0, 0.4)
        # к началу карточки — слетаются в строки карточки
        u = ease((t - (E.CARD - 0.2)) / 0.6)
        tx, ty = card_pos(j)
        xx, yy = x + (tx - x) * u, y + (ty - y) * u
        put(cv, sketch(name, 120), xx, yy + 5 * math.sin(t * 3 + j), p * (1 - 0.6 * u), a * (1 - u))


def card_pos(j):
    col, row = divmod(j, 9)
    return (150 if col == 0 else 600), 258 + row * 48


def scene_card(cv, t):
    """Карточка готовности: строки подарков, полоски — мазки краски, счётчик ≈ 296 / 850."""
    a = window_a(t, E.CARD, E.ERASE1 + 0.2, 0.35)
    if a <= 0:
        return
    put(cv, fx.rounded(1000, 520, 30, (255, 253, 246, 240), (236, 226, 200, 255), 3), 540, 470, 0.92 + 0.08 * pop(t, E.CARD), a)
    for j, (name, frac) in enumerate(CARD):
        x, y = card_pos(j)
        t0 = E.CARD + 0.25 + 0.06 * j
        if t < t0:
            continue
        hi = 0.0
        if name == 'plane':
            hi = window_a(t, E.FIN_PLANE, E.ERASE1, 0.25)
        elif name == 'icecream':
            hi = window_a(t, E.FIN_ICE, E.ERASE1, 0.25)
        low = window_a(t, E.FIN_NONE, E.ERASE1, 0.25) if frac <= 0.05 else 0.0
        if hi > 0:
            put(cv, fx.rounded(440, 54, 14, (255, 236, 160, 255)), x + 180, y, 1.0, a * hi)
        if low > 0:
            put(cv, fx.rounded(440, 54, 14, (255, 222, 222, 255)), x + 180, y, 1.0, a * low * 0.8)
        im = gift(name, 46) if name != 'chain' else chain_gift(46)
        put(cv, im, x, y + (3 * math.sin(t * 6) if hi > 0 else 0), pop(t, t0, 0.3) * (1 + 0.15 * hi), a)
        # мазок-полоска
        g = frac * ease((t - t0 - 0.15) / 0.9)
        bar(cv, x + 40, y, 300, 26, g, a, j)
        if hi > 0:
            put(cv, decor(['tube_full_teal', 'tube_full_yellow'][name == 'icecream'], 40), x + 380, y - 2, pop(t, E.FIN_PLANE if name == 'plane' else E.FIN_ICE), a * hi, 0.2)
        if low > 0:
            put(cv, decor(['tube_empty_blue', 'tube_empty_red', 'tube_empty_purple'][j % 3], 40), x + 380, y, pop(t, E.FIN_NONE + 0.04 * j), a * low, -0.25)
    # счётчик
    k = fx.ease_out(fx.clamp01((t - E.CARD - 1.2) / 1.6))
    v = int(296 * k)
    put(cv, utext(f'≈ {v} / 850', 34, 'ExtraBold', TEAL), 300, 690, 1.0, a * appear(t, E.CARD + 1.2, 0.3))
    if t > E.THIRD:
        put(cv, brush_pill('≈ ТРЕТЬ', ORANGE, 24), 800, 690, pop(t, E.THIRD), a, -0.08)
    put(cv, utext('по данным @ideanode', 16, 'SemiBold', MUTED), 160, 830, 1.0, a * 0.85)


def bar(cv, x0, y, w, h, frac, a, seed):
    if a <= 0:
        return
    def draw(d, mp, S, frac=frac):
        X0, Y0 = mp(x0, y - h / 2)
        X1, Y1 = mp(x0 + w, y + h / 2)
        d.rounded_rectangle([X0, Y0, X1, Y1], int(h * S / 2), fill=(232, 226, 214, int(255 * a)))
        if frac > 0.004:
            rng = np.random.default_rng(seed)
            xe = X0 + (X1 - X0) * frac
            pts = [(X0, Y0 + 3 * S)]
            for k in range(8):
                pts.append((X0 + (xe - X0) * (k + 1) / 8, Y0 + rng.uniform(1, 5) * S))
            pts += [(xe + 6 * S, (Y0 + Y1) / 2)]
            for k in range(8, -1, -1):
                pts.append((X0 + (xe - X0) * k / 8, Y1 - rng.uniform(1, 5) * S))
            d.polygon(pts, fill=TEAL + (int(255 * a),))
    fx.over(cv, fx.draw_rgba((x0 - 4, y - h, x0 + w + 14, y + h), draw))


def scene_chain(cv, t):
    """Засекреченный подарок в цепях: тычок кисточкой → выезжает вперёд и дёргается → медленно уезжает."""
    a = window_a(t, E.ERASE1 + 0.6, E.CREEPY + 0.1, 0.3)
    if a <= 0:
        return
    tx, ty = M.poke_tip(t)
    x0, y0 = tx + 150, ty - 10
    u = t - E.POKE_HIT
    jump = 0.0
    shake = (0.0, 0.0)
    if u > 0:
        jump = ease(u / 0.18) * (1 - ease((u - 1.6) / 0.8))
        k = 1 - ease((u - 1.2) / 0.6)
        shake = (8 * k * math.sin(t * 61), 5 * k * math.sin(t * 47 + 1))
    s = 1 + 0.25 * jump
    x = x0 + 40 * jump + shake[0]
    y = y0 + shake[1]
    put(cv, fx.radial(256, (120, 90, 200), 2.0, 1.0), x, y, 1.0 + 0.4 * jump, a * (0.35 + 0.3 * jump))
    put(cv, chain_gift(220), x, y, s, a, 0.06 * math.sin(t * 40) * jump)
    if 0 < u < 0.6:     # «звяк» — линии удара
        def draw(d, mp, S):
            for j in range(9):
                ang = j * 2 * math.pi / 9
                r0, r1 = 140 + 60 * u, 180 + 90 * u
                X0, Y0 = mp(x + math.cos(ang) * r0, y + math.sin(ang) * r0)
                X1, Y1 = mp(x + math.cos(ang) * r1, y + math.sin(ang) * r1)
                d.line([X0, Y0, X1, Y1], fill=(110, 90, 170, int(220 * (1 - u / 0.6))), width=int(5 * S))
        fx.over(cv, fx.draw_rgba((x - 300, y - 300, x + 300, y + 300), draw))
    txt_panel(cv, t, RX, E.ERASE1 + 0.8, E.CREEPY + 0.1, 'скины', '???', 'засекречено', (110, 90, 170))


# ------------------------------------------------------------------ жуть: тетрадь в клетку
def creepy_k(t):
    return appear(t, E.CREEPY, 0.4) * (1 - ease((t - E.CREEPY_END) / 0.9))


@functools.lru_cache(None)
def notebook():
    S = 1
    im = Image.new('RGBA', (W, H), (240, 240, 236, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 48):
        d.line([(x, 0), (x, H)], fill=(160, 186, 214, 255), width=2)
    for y in range(0, H, 48):
        d.line([(0, y), (W, y)], fill=(160, 186, 214, 255), width=2)
    d.line([(120, 0), (120, H)], fill=(214, 90, 96, 255), width=4)
    # пасхалка: каляка-Мита на полях
    cx, cy = 62, 1540
    d.ellipse([cx - 22, cy - 120, cx + 22, cy - 76], outline=(90, 90, 100, 255), width=3)
    d.line([(cx - 26, cy - 112), (cx - 44, cy - 60)], fill=(70, 70, 120, 255), width=4)
    d.line([(cx + 26, cy - 112), (cx + 44, cy - 60)], fill=(70, 70, 120, 255), width=4)
    d.line([(cx, cy - 76), (cx, cy - 20)], fill=(90, 90, 100, 255), width=3)
    d.polygon([(cx - 26, cy - 20), (cx + 26, cy - 20), (cx, cy - 66)], outline=(90, 90, 100, 255))
    d.line([(cx - 10, cy - 20), (cx - 14, cy + 20)], fill=(90, 90, 100, 255), width=3)
    d.line([(cx + 10, cy - 20), (cx + 14, cy + 20)], fill=(90, 90, 100, 255), width=3)
    d.arc([cx - 10, cy - 104, cx + 10, cy - 88], 20, 160, fill=(90, 90, 100, 255), width=2)
    return np.array(im).astype(np.float32)


@functools.lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - 540) / 640) ** 2 + ((yy - 1000) / 1050) ** 2)
    return np.clip((r - 0.5) / 0.6, 0, 1) ** 1.3


def creepy_bg(cv, t, k):
    nb = notebook()
    cv[..., :3] = cv[..., :3] * (1 - k) + nb[..., :3] * k
    v = vignette() * k * 0.65
    cv[..., :3] *= (1 - v[..., None])


CREEP_SK = [('kulich', 230, 420), ('plane', 540, 360), ('eight', 850, 420)]


def scene_creepy(cv, t, k):
    if k <= 0:
        return
    rng = np.random.default_rng(int(t * 60))
    sh = 3 + 5 * ease((t - E.CREEP_B) / 1.0)
    for j, (name, x, y) in enumerate(CREEP_SK):
        dx, dy = rng.normal(0, sh), rng.normal(0, sh * 0.6)
        put(cv, sketch(name, 230), x + dx, y + dy, 1.0, k, 0.05 * math.sin(t * 29 + j))
    # карандашная пыль
    def draw(d, mp, S):
        r2 = np.random.default_rng(9)
        for j in range(60):
            x0, y0, sp = r2.uniform(0, W), r2.uniform(0, H), r2.uniform(10, 30)
            y = (y0 - t * sp) % H
            X, Y = mp(x0 + math.sin(t + j) * 10, y)
            rr = r2.uniform(1.5, 3.5) * S
            d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=(90, 90, 100, int(120 * k)))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), draw))


def paint_swirl(cv, t):
    """Выход из жути: струи краски закручиваются спиралью вокруг Миты и заливают набросок цветом."""
    u = (t - E.CREEPY_END + 0.15) / 1.1
    if not 0 <= u < 1:
        return
    cx, cy = 540, M.FOOT - M.MITA_H / 2
    def draw(d, mp, S):
        for j, c in enumerate(PAINTS):
            ph = j * 2 * math.pi / len(PAINTS)
            pts = []
            for q in range(40):
                v = q / 39
                ang = ph + 7 * u + v * 2.4
                r = (80 + 420 * (1 - ease(u))) * (0.4 + 0.6 * v) + 30
                pts.append(mp(cx + math.cos(ang) * r, cy + math.sin(ang) * r * 1.4))
            alpha = int(230 * math.sin(math.pi * u))
            d.line(pts, fill=c + (alpha,), width=int((14 + 10 * math.sin(math.pi * u)) * S), joint='curve')
    fx.over(cv, fx.draw_rgba((0, 100, W, 1800), draw))


# ------------------------------------------------------------------ после жути
def scene_designers(cv, t):
    a = window_a(t, E.CREEPY_END + 0.6, E.WHY + 0.1, 0.35)
    if a <= 0:
        return
    put(cv, decor('sketchbook_open', 860), 540, 460, 0.9 + 0.1 * pop(t, E.CREEPY_END + 0.6), a)
    put(cv, utext('новых NFT', 40, 'ExtraBold', INK), 330, 420, 1.0, a)
    put(cv, utext('больше нет', 32, 'SemiBold', MUTED), 330, 478, 1.0, a)
    k = ease((t - E.NO_NEW) / 0.35)
    if k > 0:
        def draw(d, mp, S):
            X0, Y0 = mp(220, 452)
            X1, Y1 = mp(220 + 220 * k, 440)
            d.line([X0, Y0, X1, Y1], fill=RED + (int(230 * a),), width=int(7 * S))
        fx.over(cv, fx.draw_rgba((200, 410, 460, 480), draw))
    put(cv, utext('дорисуют', 40, 'ExtraBold', TEAL), 720, 420, 1.0, a * appear(t, E.YEAR_END - 1.0, 0.3))
    put(cv, utext('до конца года', 32, 'SemiBold', INK), 720, 478, 1.0, a * appear(t, E.YEAR_END - 0.8, 0.3))
    c = ease((t - E.YEAR_END) / 0.5)
    if c > 0:
        def circ(d, mp, S):
            pts = []
            for q in range(int(60 * c) + 2):
                ang = q / 60 * 2 * math.pi * 1.08 - 0.3
                pts.append(mp(720 + math.cos(ang) * 175, 450 + math.sin(ang) * 66))
            d.line(pts, fill=RED + (int(230 * a),), width=int(6 * S), joint='curve')
        fx.over(cv, fx.draw_rgba((520, 360, 920, 540), circ))
        put(cv, decor('marker', 110), 720 + math.cos(c * 6.8 - 0.3) * 175 + 30, 450 + math.sin(c * 6.8 - 0.3) * 66 - 30, 1.0,
            a * (1 - appear(t, E.YEAR_END + 0.6, 0.3)), -0.6)
    put(cv, decor('stickies', 150), 900, 650, 1.0, a * appear(t, E.CREEPY_END + 1.2, 0.3), 0.1)
    txt_panel(cv, t, LX, E.NO_NEW, E.WHY + 0.1, 'новых NFT', 'нет', 'по словам дизайнеров', RED)
    txt_panel(cv, t, RX, E.YEAR_END, E.WHY + 0.1, 'скины', 'до НГ', 'обещают', TEAL)


def scene_why(cv, t):
    a = window_a(t, E.WHY, AD_STOP + 0.6, 0.3)
    if a <= 0:
        return
    rot = 0.08 * math.sin(t * 2)
    put(cv, decor('hourglass', 230), 540, 470, pop(t, E.WHY), a, rot)
    for j in range(3):
        k = appear(t, E.WHY + 0.3 + 0.2 * j, 0.25)
        put(cv, brush_pill('?', [ORANGE, TEAL, PINK][j], 34), 300 + 240 * j + (0 if j != 1 else 0), 330 + (60 if j != 1 else 0),
            0.7 + 0.3 * pop(t, E.WHY + 0.3 + 0.2 * j), a * k, (j - 1) * 0.2)


@functools.lru_cache(None)
def mini_sketch(name, size, j):
    im = sketch(name, size)
    return im


def fan(cv, t, cx, cy, n_cards, imgs, t0, a, label, col):
    """Веер из n карточек раскрывается; на верхних — картинки скинов."""
    if t < t0:
        return
    k = ease((t - t0) / 0.8)
    spread = math.radians(120) * k
    vis = min(n_cards, 26)
    for j in range(vis):
        ang = -spread / 2 + spread * j / max(1, vis - 1)
        x = cx + math.sin(ang) * 170
        y = cy - math.cos(ang) * 170 + 170
        card = fx.rounded(120, 160, 12, (255, 253, 246, 255), (210, 204, 190, 255), 2)
        put(cv, card, x, y, 1.0, a, ang)
        put(cv, imgs[j % len(imgs)], x, y, 1.0, a, ang)
    put(cv, brush_pill(label, col, 30), cx, cy + 260, pop(t, t0 + 0.4), a)


@functools.lru_cache(None)
def hundred_imgs():
    out = []
    for m in HUNDRED:
        im = Image.open(gifts_api.model_png('Homemade Cake', m, 256)).convert('RGBA').resize((100, 100), Image.LANCZOS)
        out.append(im)
    return out


def scene_fifty(cv, t):
    a = window_a(t, ON[9] - 0.1, E.CONTEST + 0.2, 0.3)
    if a <= 0:
        return
    sk = [sketch(n, 100) for n in ('kulich', 'star', 'icecream', 'horse', 'plane')]
    fan(cv, t, 290, 330, 50, sk, E.FAN50, a, '≈ 50 скинов', TEAL)
    fan(cv, t, 790, 330, 100, hundred_imgs(), E.FAN100, a, 'до 100', ORANGE)
    txt_panel(cv, t, LX, E.FAN50 + 0.3, E.CONTEST + 0.2, 'на подарок', '≈ 50', 'скинов', TEAL)
    txt_panel(cv, t, RX, E.FAN100 + 0.3, E.CONTEST + 0.2, 'у вышедших', '100', 'бывает', ORANGE)


def scene_contest(cv, t):
    a = window_a(t, E.CONTEST, E.KEEP + 0.2, 0.3)
    if a <= 0:
        return
    drawn_gift(cv, t, 'contest', 540, 440, 260, E.CONTEST, a)
    put(cv, decor('rosette_gold', 110), 650, 360, pop(t, E.CONTEST + 0.6), a * appear(t, E.CONTEST + 0.6, 0.2), 0.2)
    for j in range(4):
        t0 = E.CONTEST_ART + 0.18 * j
        k = appear(t, t0, 0.25)
        if k <= 0:
            continue
        x = [160, 330, 750, 920][j]
        y = [560, 330, 330, 560][j]
        put(cv, fx.rounded(130, 150, 8, (255, 255, 255, 255), (190, 180, 160, 255), 3), x, y, pop(t, t0), a * k, (j - 1.5) * 0.08)
        put(cv, sketch(['contest', 'horse', 'kulich', 'star'][j], 100), x, y - 6, pop(t, t0), a * k, (j - 1.5) * 0.08)
        put(cv, decor('rosette_blue' if j % 2 else 'rosette_gold', 56), x + 50, y - 60, pop(t, t0 + 0.15), a * k)
    txt_panel(cv, t, LX, E.CONTEST + 0.5, E.KEEP + 0.2, 'скины', 'конкурс', 'от участников', YELLOW)


def scene_keep(cv, t):
    a = window_a(t, E.KEEP, E.ERASE2 + 0.3, 0.3)
    if a <= 0:
        return
    x, y, size = 540, 450, 300
    c = ease((t - E.REPAINT) / 0.9)
    yy = y + 5 * math.sin(t * 2)
    if c < 1:
        put(cv, grey('kulich', size), x, yy, pop(t, E.KEEP), a)
    if c > 0:
        img = anim_frame('kulich_anim', t, size) if t > E.REPAINT + 0.9 else gift('kulich', size)
        put(cv, wipe(img, c, False) if c < 1 else img, x, yy, 1.0, a)
        # кисточка водит по куличу
        if c < 1:
            bx = x - 120 + 240 * ((c * 4) % 1 if int(c * 4) % 2 == 0 else 1 - (c * 4) % 1)
            put(cv, decor('pencil', 120), bx + 40, yy + size / 2 - c * size - 40, 1.0, a, -0.5)
            paint_specks(cv, t, E.REPAINT + 0.2, x, yy, 160)
    if t > E.VINTAGE:
        put(cv, brush_pill('почти винтаж', (170, 120, 70), 24), 760, 300, pop(t, E.VINTAGE), a, 0.12)
    up = window_a(t, E.UPGRADE, E.ERASE2 + 0.3, 0.25)
    if up > 0:
        put(cv, fx.radial(256, (255, 220, 120), 2.0, 1.0), x, yy, 1.6, a * up * 0.6)
        put(cv, brush_pill('↑ улучшить', TEAL, 26), 540, 650, pop(t, E.UPGRADE), a * up)
    txt_panel(cv, t, LX, E.KEEP + 0.4, E.ERASE2 + 0.3, 'храни', 'кулич', 'не продавай', PINK)
    txt_panel(cv, t, RX, E.REPAINT, E.ERASE2 + 0.3, 'дорисуют', 'скин', 'и улучшишь', TEAL)


# ------------------------------------------------------------------ финал: змейка на кнопочном телефоне + выбор
SNAKE_GIFTS = ['kulich', 'plane', 'icecream', 'star', 'horse', 'sandcastle', 'coconut', 'may1', 'eight', 'contest',
               'sneakers', 'shirt', 'briefcase', 'tomb', 'coffin', 'dove']
PX0, PY0, PX1, PY1 = 120, 150, 960, 600          # экран
CELL = 70
GW, GH = 12, 6


def snake_path():
    """Путь головы по клеткам: змейка ползёт по кругу и поворачивает под прямым углом (петля)."""
    pts = []
    x, y = 0, 1
    seq = [(1, 0)] * 10 + [(0, 1)] * 3 + [(-1, 0)] * 10 + [(0, -1)] * 3
    for dx, dy in seq:
        pts.append((x, y))
        x, y = x + dx, y + dy
    return pts


PATH = snake_path()


@functools.lru_cache(None)
def phone_body():
    im = Image.new('RGBA', (PX1 - PX0 + 90, PY1 - PY0 + 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], 54, fill=(58, 62, 74, 255), outline=(30, 32, 40, 255), width=6)
    d.rounded_rectangle([im.width // 2 - 70, 26, im.width // 2 + 70, 40], 7, fill=(30, 32, 40, 255))
    d.rounded_rectangle([45, 75, im.width - 45, im.height - 45], 16, fill=(190, 200, 110, 255))
    for i in range(GW):
        for j in range(GH):
            x, y = 45 + 20 + i * CELL, 75 + 70 + j * CELL
            if x + CELL <= im.width - 50 and y + CELL <= im.height - 50:
                d.rectangle([x + 2, y + 2, x + CELL - 2, y + CELL - 2], fill=(182, 192, 104, 255))
    f = ufont('ExtraBold', 30)
    d.text((70, 92), 'СКИНОВ  296 / 850', font=f, fill=(48, 58, 30, 255))
    d.text((im.width - 70, 92), '16+', font=f, fill=(48, 58, 30, 255), anchor='ra')
    return im


@functools.lru_cache(maxsize=32)
def snake_seg(name, head):
    seg = Image.new('RGBA', (CELL, CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(seg)
    d.rounded_rectangle([2, 2, CELL - 2, CELL - 2], 14, fill=(48, 58, 30, 255))
    g = gift(name, CELL - 14)
    seg.alpha_composite(g, ((CELL - g.width) // 2, (CELL - g.height) // 2))
    if head:
        d = ImageDraw.Draw(seg)
        d.ellipse([CELL - 26, 6, CELL - 10, 22], fill=(255, 255, 255, 255))
        d.ellipse([CELL - 21, 10, CELL - 14, 18], fill=(0, 0, 0, 255))
    return seg


def scene_snake(cv, t):
    a = appear(t, E.ERASE2 - 0.2, 0.4)
    if a <= 0:
        return
    body = phone_body()
    bx, by = (PX0 + PX1) / 2, (PY0 + PY1) / 2 + 30
    put(cv, body, bx, by, 0.9 + 0.1 * pop(t, E.ERASE2 - 0.2), a)
    ox, oy = bx - body.width / 2 + 45 + 20, by - body.height / 2 + 75 + 70
    step = 0.22                                       # рывками, как в настоящей игре
    k = int(max(0.0, t - E.ERASE2) / step)
    L = min(len(SNAKE_GIFTS), 6 + k // 3)
    for s in range(L):
        idx = (k - s) % len(PATH)
        gx, gy = PATH[idx]
        put(cv, snake_seg(SNAKE_GIFTS[s], s == 0), ox + gx * CELL + CELL / 2, oy + gy * CELL + CELL / 2, 1.0, a)
    # «еда» — капля краски
    fi = (k // 9 * 7 + 4) % len(PATH)
    gx, gy = PATH[fi]
    put(cv, glow_dot(), ox + gx * CELL + CELL / 2, oy + gy * CELL + CELL / 2, 1.2, a * (0.6 + 0.4 * math.sin(t * 8)))


def scene_choice(cv, t):
    a = appear(t, E.CHOICE, 0.3)
    if a <= 0:
        return
    hot = int((t - E.CHOICE) / 0.7) % 2
    for j, (lab, col) in enumerate((('Кулич', TEAL), ('Самолётик', ORANGE))):
        y = 1080 + j * 150
        im = brush_pill(lab, col, 42, WHITE, seed=j)
        p = pop(t, E.CHOICE + 0.12 * j)
        put(cv, im, 820, y, (0.8 + 0.2 * p) * (1.06 if j == hot else 1.0), a * appear(t, E.CHOICE + 0.12 * j, 0.25))
    hy = 1080 + hot * 150
    put(cv, decor('pencil', 110), 560 + 6 * math.sin(t * 8), hy - 10, 1.0, a, 0.9)



# ------------------------------------------------------------------ заполнение: подарки по краям, детали в углах, реакции
DRIFT = ['sandcastle', 'coconut', 'horse', 'may1', 'dove', 'eight', 'shirt', 'sneakers']


def drifting(cv, t):
    for side in (0, 1):
        for m in range(3):
            ph = (t * 0.035 + m / 3 + side * 0.17) % 1.0
            y = 1960 - ph * 2000
            x = (52, 1028)[side] + math.sin(t * 0.8 + m * 2 + side) * 14
            al = 0.55 * min(1.0, ph * 6, (1 - ph) * 6)
            put(cv, gift(DRIFT[(m * 2 + side) % len(DRIFT)], 80), x, y, 1.0, al, math.sin(t * 0.7 + m) * 0.15)


CORNERS = [  # (с, по, предмет, ширина, x, y)
    (0.3, E.MANY, [('tube_full_teal', 70, 110, 1730), ('stickies', 120, 975, 1720)]),
    (E.CARD, E.ERASE1, [('washi', 130, 110, 1720), ('tube_full_yellow', 70, 980, 1730)]),
    (E.ERASE1, E.CREEPY, [('eraser', 120, 980, 1720)]),
    (E.CREEPY_END, AD_STOP, [('marker', 120, 110, 1720), ('sketchbook', 130, 975, 1710)]),
    (ON[9], E.CONTEST, [('tube_full_orange', 70, 110, 1730), ('washi', 130, 975, 1720)]),
    (E.CONTEST, E.KEEP, [('star_sticker', 90, 110, 1720), ('rosette_blue', 90, 980, 1720)]),
    (E.KEEP, E.ERASE2, [('tube_empty_red', 70, 110, 1730), ('stickies', 120, 975, 1720)]),
    (E.ERASE2, DUR + 5, [('tube_full_teal', 70, 980, 1730)]),
]


def decor_corners(cv, t):
    for t0, t1, lst in CORNERS:
        a = window_a(t, t0 + 0.3, t1, 0.4)
        if a <= 0:
            continue
        for j, (name, w, x, y) in enumerate(lst):
            if x < 300 and M.x_of(t) < 450:
                continue
            put(cv, decor(name, w), x, y + 6 * math.sin(t * 1.6 + x), pop(t, t0 + 0.3 + 0.15 * j), a * 0.95,
                0.08 * math.sin(t * 0.9 + j))


def easter_egg(cv, t):
    a = window_a(t, E.FAN50 + 0.6, E.FAN50 + 2.2, 0.25)
    if a > 0:
        put(cv, decor('cartridge', 90), 960, 330, pop(t, E.FAN50 + 0.6), a, 0.3)


REACT = [(E.G_STAR + 0.4, '?'), (E.NO_SKIN + 0.4, 'drop'), (E.THIRD + 0.3, '!'), (E.FIN_NONE + 0.4, 'drop'),
         (E.FAN100 + 0.3, '!'), (E.CONTEST_ART + 0.3, 'heart'), (E.UPGRADE + 0.1, 'heart')]


def heart(d, X, Y, r, col):
    d.ellipse([X - r, Y - r, X, Y], fill=col)
    d.ellipse([X, Y - r, X + r, Y], fill=col)
    d.polygon([(X - r, Y - r * 0.45), (X + r, Y - r * 0.45), (X, Y + r * 0.95)], fill=col)


def reactions(cv, t):
    for t0, kind in REACT:
        k = t - t0
        if not 0 <= k < 1.3:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 0.9) / 0.4))
        p = fx.ease_out_back(fx.clamp01(k / 0.35))
        x, y = M.x_of(t) + 190, M.FOOT - M.MITA_H + 40 - 40 * ease(k / 1.3)
        if kind in ('!', '?'):
            put(cv, brush_pill(kind, ORANGE if kind == '!' else BLUE, 36), x, y, 0.6 + 0.4 * p, a, -0.15)
        else:
            def icon(d, mp, S, kind=kind, a=a, p=p, x=x, y=y):
                X, Y = mp(x, y)
                r = 26 * S * (0.6 + 0.4 * p)
                if kind == 'heart':
                    heart(d, X, Y, r, PINK + (int(255 * a),))
                else:
                    d.ellipse([X - r * 0.6, Y - r * 0.2, X + r * 0.6, Y + r], fill=TEAL + (int(230 * a),))
                    d.polygon([(X, Y - r), (X - r * 0.55, Y + r * 0.2), (X + r * 0.55, Y + r * 0.2)], fill=TEAL + (int(230 * a),))
            fx.over(cv, fx.draw_rgba((x - 60, y - 70, x + 60, y + 60), icon))


# ------------------------------------------------------------------ ведро краски (переход в художницу)
def bucket_fx(cv, t, front):
    """Ведро падает сверху, опрокидывается над Митой; всплеск краски на миг закрывает её; краска стекает."""
    x = 540
    head = M.FOOT - M.MITA_H
    t_fall0 = E.SPLASH - 0.75
    if not front and t_fall0 <= t < E.SPLASH + 0.25:
        if t < E.SPLASH - 0.12:
            u = ease((t - t_fall0) / 0.63)
            y = -150 + (head - 170 + 150) * u
            put(cv, decor('bucket', 210), x + 30 * math.sin(t * 9), y, 1.0, 1.0, 0.15 * math.sin(t * 12))
        else:
            u = (t - (E.SPLASH - 0.12)) / 0.37
            put(cv, decor('bucket_pour', 290), x + 60, head - 140, 1.0, 1 - ease((u - 0.6) / 0.4), 2.6)
    if front:
        u = (t - E.SPLASH) / 1.4
        if 0 <= u < 1:
            cover = math.exp(-((t - E.SPLASH - 0.18) / 0.16) ** 2)
            def draw(d, mp, S):
                rng = np.random.default_rng(5)
                cx, cy = x, head + M.MITA_H * 0.45
                for j in range(22):          # капли и потёки
                    ang = rng.uniform(0, 2 * math.pi)
                    r = 60 + (rng.uniform(150, 420)) * ease(u * 2.2)
                    X, Y = mp(cx + math.cos(ang) * r * 0.8, cy + math.sin(ang) * r * 1.2 + 260 * u * u)
                    rr = rng.uniform(10, 26) * S * (1 - u)
                    d.ellipse([X - rr, Y - rr, X + rr, Y + rr], fill=TEAL + (int(240 * (1 - u)),))
                if cover > 0.02:              # густой всплеск на миг закрывает Миту целиком
                    X, Y = mp(cx, cy)
                    R = (240 + 160 * cover) * S
                    pts = []
                    for q in range(96):
                        ang = q / 96 * 2 * math.pi
                        rr = R * (0.86 + 0.1 * math.sin(ang * 5) + 0.05 * math.sin(q * 1.7))
                        pts.append((X + math.cos(ang) * rr * 0.75, Y + math.sin(ang) * rr * 1.5))
                    d.polygon(pts, fill=TEAL + (int(255 * min(1, cover * 1.4)),))
                # потёки по Мите вниз
                for j in range(9):
                    dx = -130 + j * 32
                    y0 = head + 40
                    y1 = y0 + 200 + 560 * ease(u * 1.3) + (j % 3) * 40
                    X0, Y0 = mp(cx + dx, y0)
                    X1, Y1 = mp(cx + dx, y1)
                    al = int(200 * (1 - ease((u - 0.55) / 0.45)))
                    d.line([X0, Y0, X1, Y1], fill=TEAL + (al,), width=int((10 + (j % 3) * 4) * S))
                    d.ellipse([X1 - 10 * S, Y1 - 6 * S, X1 + 10 * S, Y1 + 14 * S], fill=TEAL + (al,))
            fx.over(cv, fx.draw_rgba((60, head - 300, 1020, M.FOOT + 120), draw))


def move_tool(cv):
    def tool(kind, x, y, u):
        if kind == 'eraser':
            put(cv, decor('eraser', 170), x + 40 * math.sin(u * 30), y, 1.0, 1.0, -0.3)
            def crumbs(d, mp, S):
                rng = np.random.default_rng(int(u * 100))
                for j in range(10):
                    X, Y = mp(x + rng.uniform(-120, 120), y + rng.uniform(20, 160))
                    r = rng.uniform(3, 7) * S
                    d.ellipse([X - r, Y - r, X + r, Y + r], fill=(240, 236, 228, 230))
            fx.over(cv, fx.draw_rgba((x - 150, y, x + 150, y + 200), crumbs))
        else:
            put(cv, decor('pencil', 150), x + 30 * math.sin(u * 40), y - 40, 1.0, 1.0, 0.0)
    return tool


def mita_shadow(cv, x, y):
    def draw(d, mp, S):
        X, Y = mp(x, y + 2)
        d.ellipse([X - 150 * S, Y - 18 * S, X + 150 * S, Y + 18 * S], fill=(60, 50, 110, 40))
    fx.over(cv, fx.draw_rgba((x - 170, y - 30, x + 170, y + 30), draw))


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
    acc = RED if creepy else ORANGE
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = acc if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (INK if on else (160, 154, 170))
        parts.append(((' ' if j else '') + _disp(w[0]).upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    p = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    put(cv, fx.rounded(pw, 84, 30, (255, 253, 246, 236), (236, 226, 200, 255), 3), 540, SUB_Y, 0.85 + 0.15 * p, 1.0)
    put(cv, im, 540, SUB_Y, sc * (0.85 + 0.15 * p), 1.0)


# ------------------------------------------------------------------ глитч на входе в жуть
GLITCH = [(E.CREEPY - 0.04, 0.2, 0.8), (E.CREEP_C + 0.1, 0.08, 0.45)]


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
            out[y:y + h] = np.roll(img[y:y + h], int(rng.normal(0, 60 * k)), axis=1)
        y += h
    f = out.astype(np.float32)
    f[::3] *= 0.85
    f[..., 1] *= 0.9
    mix = min(1.0, 0.35 + k)
    return np.clip(img * (1 - mix) + f * mix, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    ck = creepy_k(t)
    if ck > 0:
        creepy_bg(cv, t, ck)
    if ck < 1:
        drifting(cv, t)
        decor_corners(cv, t)
        scene_hook(cv, t)
        scene_many(cv, t)
        scene_card(cv, t)
        scene_chain(cv, t)
        scene_designers(cv, t)
        scene_why(cv, t)
        scene_fifty(cv, t)
        scene_contest(cv, t)
        scene_keep(cv, t)
        scene_snake(cv, t)
        easter_egg(cv, t)
    scene_creepy(cv, t, ck)
    bucket_fx(cv, t, False)
    if t != AD_STOP:
        M.draw(cv, t, put, mita_shadow if ck < 0.5 else None, move_tool(cv))
    bucket_fx(cv, t, True)
    paint_swirl(cv, t)
    if ck < 0.5:
        scene_choice(cv, t)
        reactions(cv, t)
        headline(cv, t)
    if not (AD_STOP - 0.02 <= t < AD_STOP + 0.1):
        subtitles(cv, t)
    img = np.clip(cv[..., :3], 0, 255).astype(np.uint8)
    g = glitch_at(t)
    if g > 0:
        img = glitch(img, g, int(t * 60))
    return img


# ------------------------------------------------------------------ реклама: мастерская скинов (баннер не закрыт)
BAN_TOP = int(H / 2 - 283)
BAN_BOT = int(H / 2 + 284)


@functools.lru_cache(None)
def skin_kulich(size):
    """«Новый скин» кулича: перекраска (бирюза+золото) — его дорисовывают во время рекламы."""
    im = np.array(gift('kulich', size)).astype(np.float32)
    rgb = im[..., :3] / 255
    hsv = cv2.cvtColor(rgb.astype(np.float32), cv2.COLOR_RGB2HSV)
    hsv[..., 0] = (hsv[..., 0] + 150) % 360
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 1)
    out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB) * 255
    return Image.fromarray(np.dstack([out, im[..., 3]]).clip(0, 255).astype(np.uint8))


def ad_overlay(c, t):
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    lt = M.draw_ad(cv, bt, put, a, 540, BAN_TOP - 14, 600)
    # под баннером: лист бумаги, на нём рождается скин кулича
    py0 = BAN_BOT + 30
    sheet_h = H - py0 - 40
    put(cv, fx.rounded(700, sheet_h, 20, (255, 253, 246, 255), (220, 210, 190, 255), 4), 540, py0 + sheet_h / 2, 1.0, a)
    tape(cv, 300, py0 + 4, a, (250, 226, 140), -0.15)
    tape(cv, 780, py0 + 4, a, (170, 225, 215), 0.15)
    size = min(sheet_h - 80, 520)
    cx, cy = 540, py0 + sheet_h / 2
    B = BR.B
    k1 = fx.clamp01(lt / (B * 0.35))                    # контур
    k2 = fx.clamp01((lt - B * 0.35) / (B * 0.4))        # заливка мазками
    k3 = fx.clamp01((lt - B * 0.75) / (B * 0.15))       # блики и штамп
    sk = sketch('kulich', size)
    put(cv, wipe(sk, k1, True), cx, cy, 1.0, a * (1 - 0.6 * k2))
    if k2 > 0:
        img = skin_kulich(size)
        put(cv, wipe(img, k2, False) if k2 < 1 else img, cx, cy, 1.0, a)
        if k2 < 1:
            put(cv, decor('pencil', 110), cx - 140 + 280 * ((k2 * 5) % 1), cy + size / 2 - k2 * size, 1.0, a, -0.4)
    if k3 > 0:
        put(cv, fx.radial(256, (255, 230, 150), 2.0, 1.0), cx, cy, 2.2, a * k3 * 0.5)
        put(cv, brush_pill('СКИН ГОТОВ!', RED, 30), cx + 170, cy + size / 2 - 40, pop(lt, B * 0.75 + 0.1, 0.4), a * k3, -0.18)
    return cv[..., :3]


TOTAL = BR.out_dur(DUR)
LOOP_D = 0.35


def out_frame(t, i=None):
    img = ad_overlay(BR.render(render_at, t, i).astype(np.float32), t)
    # петля: лист бумаги «переворачивается» — выезжает в конце и уезжает в начале
    u_out = (t - (TOTAL - LOOP_D)) / LOOP_D
    u_in = t / LOOP_D
    edge = None
    if 0 <= u_out <= 1:
        edge = W * (1 - ease(u_out))
    elif 0 <= u_in < 1:
        edge = -W * ease(u_in)
    if edge is not None:
        x0 = int(max(0, edge))
        x1 = int(min(W, edge + W))
        if x1 > x0:
            img = np.array(img, np.float32)
            img[:, x0:x1] = paper()[:, x0:x1]
            sh = max(0, x0 - 18)
            img[:, sh:x0] *= np.linspace(1, 0.82, x0 - sh, dtype=np.float32)[None, :, None] if x0 > sh else 1
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
