"""«Мита объясняет монохромы» — 1080×1920, 60 fps. Кадр — чистая функция времени содержания.
Карточки подарков: живые Lottie-модели (gifts_api + lottie) на градиенте фона из API, подписи — data/cards_2026-11-15.json.
Мита — арты автора (input/mita), позы по сценам, смена наряда со вспышкой, кружение на «наряды».
Ритм: сильные доли музыки (events.BEATS) — лёгкий толчок кадра, пульс света и подпрыгивание Миты."""
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
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import banner
import frames
import fx
import gifts_api
import lottie
import events as E
from timeline import DUR, ON, END, AD_STOP, TAKES
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
DATA = json.loads((HERE / 'data' / 'cards_2026-11-15.json').read_text(encoding='utf-8'))
CARDS = DATA['cards']
MITA = HERE / 'input' / 'mita'
MITA_H = 880            # рост Миты в кадре, px
MITA_FOOT = 1915
WHITE = (255, 255, 255)
INK = (30, 24, 48)
MUTED = (118, 112, 140)
ACCENT = (226, 54, 120)


# ------------------------------------------------------------------ helpers
def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.35):
    return ease((t - t0) / d)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rub(v):
    return f'≈ {v:,} ₽'.replace(',', ' ')


def pct(v):
    return (f'{v:.1f}'.rstrip('0').rstrip('.') + '%').replace('.', ',')


@functools.lru_cache(None)
def backdrop_hex(gift, name):
    b = [x for x in gifts_api.backdrops(gift) if x['name'] == name][0]['hex']
    return b['centerColor'], b['edgeColor']


@functools.lru_cache(None)
def tile_bg(gift, backdrop, size, radius):
    c, e = (np.array(hexrgb(h), np.float32) for h in backdrop_hex(gift, backdrop))
    yy, xx = np.mgrid[0:size, 0:size] / size - 0.5
    r = np.clip(np.sqrt(xx ** 2 + yy ** 2) / 0.7, 0, 1)[..., None]
    rgb = c * (1 - r) + e * r
    im = Image.fromarray(rgb.astype(np.uint8)).convert('RGBA')
    mask = Image.new('L', (size * 2, size * 2), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size * 2 - 1, size * 2 - 1], radius * 2, fill=255)
    im.putalpha(mask.resize((size, size), Image.LANCZOS))
    return im


@functools.lru_cache(None)
def model_path(gift, model):
    return str(gifts_api.model_file(gift, model, 'json'))


def gift_tile(gift, model, backdrop, size, t, radius=None):
    radius = radius or int(size * 0.16)
    im = tile_bg(gift, backdrop, size, radius).copy()
    g = lottie.frame(model_path(gift, model), t, size=int(size * 0.84))
    off = (size - g.size[0]) // 2
    im.alpha_composite(g, (off, off))
    return im


@functools.lru_cache(None)
def text(s, size, weight='Bold', color=INK, shadow=False):
    return fx.text_img(((s, color),), size, weight, shadow)


@functools.lru_cache(None)
def multi(parts, size, weight='Bold', shadow=False):
    return fx.text_img(parts, size, weight, shadow)


def put(canvas, im, cx, cy, s=1.0, a=1.0, rot=0.0, anchor=None):
    if im is None or a <= 0.003 or s <= 0.003:
        return
    fx.over(canvas, fx.warp(im, cx, cy, s, s, rot, anchor), a)


# ------------------------------------------------------------------ voice envelope (talk bounce)
@functools.lru_cache(None)
def voice_env():
    fps = 60
    env = np.zeros(int(DUR * fps) + 2)
    for k, p in TAKES.items():
        with wave.open(str(p)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
            sr = w.getframerate()
        hop = sr // fps
        n = len(x) // hop
        r = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1))
        s = int(ON[k] * fps)
        env[s:s + n] = np.maximum(env[s:s + n], r[:len(env) - s])
    env = env / (np.percentile(env[env > 0], 90) + 1e-9)
    return np.convolve(np.clip(env, 0, 1.2), np.ones(5) / 5, 'same')


def talk(t):
    e = voice_env()
    i = int(t * 60)
    return float(e[i]) if 0 <= i < len(e) else 0.0


def beat_pulse(t, decay=7.0):
    b = E.BEATS[(E.BEATS <= t) & (E.BEATS > t - 0.6)]
    if not len(b):
        return 0.0
    return float(np.exp(-(t - b.max()) * decay))


# ------------------------------------------------------------------ Mita
@functools.lru_cache(None)
def mita(name, mirror=False):
    im = Image.open(MITA / f'{name}.png').convert('RGBA')
    s = MITA_H / im.height
    im = im.resize((max(1, int(im.width * s)), MITA_H), Image.LANCZOS)
    return ImageOps.mirror(im) if mirror else im


@functools.lru_cache(None)
def silhouette(name, mirror=False):
    im = mita(name, mirror)
    w = Image.new('RGBA', im.size, (255, 255, 255, 0))
    w.putalpha(im.getchannel('A'))
    return w


SPIN_SEQ = [('normal_explain', False), ('spin_1_threequarter', False), ('spin_2_profile', False),
            ('spin_3_backthreequarter', False), ('spin_4_back', False), ('spin_3_backthreequarter', True),
            ('spin_2_profile', True), ('spin_1_threequarter', True), ('normal_explain', False)]
SPIN_DUR = 0.72
POSES = [  # (с какого времени, поза, смена наряда)
    (0.0, 'normal_sly', False),
    (ON[2], 'normal_explain', False),
    (E.TYPE1, 'pink_explain', True),
    (E.TYPE2, 'clash_explain', True),
    (ON[7] + 0.1, 'clash_confused', False),
    (E.SEEN, 'normal_explain', True),
    (E.TEASE, 'normal_secret', False),
    (E.TYPE3, 'bw_explain', True),
    (E.WHY, 'bw_proud', False),
    (E.OUTRO, 'bw_explain', False),
    (E.CREEPY, 'bw_wink', False),
]


def pose_at(t):
    cur = POSES[0]
    for p in POSES:
        if t >= p[0]:
            cur = p
    return cur


def draw_mita(cv, t):
    t0, name, change = pose_at(t)
    mirror = False
    if E.SPIN <= t < E.SPIN + SPIN_DUR:
        k = min(len(SPIN_SEQ) - 1, int((t - E.SPIN) / SPIN_DUR * len(SPIN_SEQ)))
        name, mirror = SPIN_SEQ[k]
    im = mita(name, mirror)
    since = t - t0
    pop = fx.spring(fx.clamp01(since / 0.5)) if since < 0.5 else 1.0
    sq = 1 + 0.035 * (1 - pop)                      # сжатие при смене позы
    tk = talk(t)
    bob = math.sin(t * 2.1) * 4 - 9 * beat_pulse(t, 9)
    sy = (1 + 0.006 * math.sin(t * 2.6) + 0.012 * tk) / sq
    sx = sq * (1 - 0.004 * tk)
    cx = 540 + math.sin(t * 0.7) * 6
    if E.SPIN <= t < E.SPIN + SPIN_DUR:
        bob -= 18 * math.sin(math.pi * (t - E.SPIN) / SPIN_DUR)
    creepy = ease((t - E.CREEPY) / 2.0)
    if creepy > 0:                                   # финал: Мита медленно приближается
        s = 1 + 0.07 * creepy
        sx, sy = sx * s, sy * s
    placed = fx.warp(im, cx, MITA_FOOT + bob, sx, sy, 0.0, (im.width / 2, im.height))
    shadow = fx.radial(256, (0, 0, 0), 1.6, 0.55)
    put(cv, shadow.resize((420, 70)), cx, MITA_FOOT - 4, 1.0, 0.8)
    fx.over(cv, placed)
    if change and since < 0.55:                      # смена наряда: белая вспышка по силуэту + искры
        a = (1 - since / 0.55) ** 1.5
        sil = silhouette(name, mirror)
        fx.over(cv, fx.warp(sil, cx, MITA_FOOT + bob, sx, sy, 0.0, (im.width / 2, im.height)), a * 0.9)
        sparkles(cv, t, t0, cx, MITA_FOOT - MITA_H * 0.55, 360)


def sparkles(cv, t, t0, cx, cy, spread, n=14, col=(255, 180, 60)):
    k = t - t0
    if not 0 <= k < 0.9:
        return
    rng = np.random.default_rng(int(t0 * 1000))
    def draw(d, mp, S):
        for j in range(n):
            ang = rng.uniform(0, 2 * math.pi)
            sp = rng.uniform(0.4, 1.0) * spread
            r = ease(k / 0.9) * sp
            x, y = mp(cx + math.cos(ang) * r, cy + math.sin(ang) * r * 1.3)
            size = (1 - k / 0.9) * rng.uniform(10, 24) * S
            fx.sparkle(d, x, y, size, col + (int(255 * (1 - k / 0.9)),))
    fx.over(cv, fx.draw_rgba((cx - spread - 60, cy - spread * 1.4 - 60, cx + spread + 60, cy + spread * 1.4 + 60), draw))


# ------------------------------------------------------------------ background
TINTS = [  # (время, цвет свечения 1, цвет свечения 2)
    (0.0, (120, 70, 200), (220, 90, 160)),
    (E.TYPE1, (240, 90, 170), (255, 150, 200)),
    (E.TYPE2, (60, 170, 255), (255, 200, 40)),
    (E.SEEN, (130, 80, 220), (240, 110, 170)),
    (E.TEASE, (150, 120, 220), (90, 70, 160)),
    (E.TYPE3, (210, 210, 220), (90, 90, 100)),
    (E.WHY, (130, 80, 220), (240, 110, 170)),
    (E.CREEPY, (150, 20, 40), (60, 10, 30)),
]


def tint_at(t):
    a = TINTS[0]
    for k in range(len(TINTS)):
        if t >= TINTS[k][0]:
            a = TINTS[k]
            prev = TINTS[k - 1] if k else TINTS[0]
            m = ease((t - TINTS[k][0]) / 0.6)
            c1 = tuple(p * (1 - m) + q * m for p, q in zip(prev[1], a[1]))
            c2 = tuple(p * (1 - m) + q * m for p, q in zip(prev[2], a[2]))
    return c1, c2


@functools.lru_cache(None)
def base_bg():
    yy = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([252, 250, 255], np.float32), np.array([240, 236, 248], np.float32)
    return np.broadcast_to(top * (1 - yy) + bot * yy, (H, W, 3)).astype(np.float32)


@functools.lru_cache(None)
def glow_sprite():
    return fx.radial(512, (255, 255, 255), 1.8, 1.0)


@functools.lru_cache(None)
def tinted_glow(c):
    g = glow_sprite().copy()
    arr = np.array(g)
    arr[..., :3] = c
    return Image.fromarray(arr)


def background(t):
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = base_bg()
    cv[..., 3] = 255
    c1, c2 = tint_at(t)
    p = beat_pulse(t, 5)
    q = lambda c: tuple(int(v) for v in c)
    put(cv, tinted_glow(q(c1)), 230 + 80 * math.sin(t * 0.31), 560 + 60 * math.cos(t * 0.27), 2.8, 0.16 + 0.07 * p)
    put(cv, tinted_glow(q(c2)), 860 + 70 * math.cos(t * 0.23), 1300 + 90 * math.sin(t * 0.29), 3.0, 0.13 + 0.06 * p)
    fx.over(cv, (grid_dots(), 0, 0))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), lambda d, mp, S: confetti(d, mp, S, t)))
    return cv


@functools.lru_cache(None)
def grid_dots():
    """Едва заметная точечная сетка — фон не пустой, но не шумит."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(24, H, 48):
        for x in range(24 + (24 if (y // 48) % 2 else 0), W, 48):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(150, 140, 190, 46))
    return im


CONF = [(236, 72, 120), (120, 90, 230), (255, 190, 60), (70, 190, 230), (150, 220, 160), (30, 24, 48)]


def confetti(d, mp, S, t):
    """Пастельное конфетти и мерцающие звёздочки, медленно плывут вверх."""
    rng = np.random.default_rng(11)
    for j in range(34):
        x0, y0, sp = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(10, 34)
        kind, col = rng.integers(0, 3), CONF[rng.integers(0, len(CONF))]
        size, rot0, vr = rng.uniform(5, 11), rng.uniform(0, 6.3), rng.uniform(-1.5, 1.5)
        y = (y0 - t * sp) % (H + 40) - 20
        x = x0 + math.sin(t * 0.6 + j) * 18
        X, Y = mp(x, y)
        r = size * S
        a = 120 if col != (30, 24, 48) else 60
        if kind == 0:
            d.ellipse([X - r * 0.6, Y - r * 0.6, X + r * 0.6, Y + r * 0.6], fill=col + (a,))
        elif kind == 1:
            ang = rot0 + vr * t
            pts = [(X + math.cos(ang + k * math.pi / 2 + 0.5) * r, Y + math.sin(ang + k * math.pi / 2 + 0.5) * r * 0.45)
                   for k in range(4)]
            d.polygon(pts, fill=col + (a,))
        else:
            tw = 0.5 + 0.5 * math.sin(t * 2.4 + j * 1.7)
            fx.sparkle(d, X, Y, r * (0.6 + 0.6 * tw), col + (int(60 + 120 * tw),))


# ------------------------------------------------------------------ headline
HEADS = [  # (с, по, строки, малая подпись)
    (0.0, ON[3] - 0.15, ('Почему одинаковые', 'подарки стоят по-разному?'), 'Мита объясняет'),
    (ON[3] - 0.15, E.TYPE1, ('Монохром',), None),
    (E.TYPE1, E.TYPE2, ('Вид 1', 'цвет в цвет'), None),
    (E.TYPE2, E.SEEN, ('Вид 2', 'одинаковые названия'), None),
    (E.SEEN, E.TEASE, ('Монохром', 'видно сразу'), None),
    (E.TEASE, E.TYPE3, ('Вид 3', '???'), None),
    (E.TYPE3, E.WHY, ('Вид 3', 'чёрно-белый'), None),
    (E.WHY, E.OUTRO, ('Почему это', 'так нравится?'), None),
    (E.OUTRO, DUR + 1, ('А у тебя есть', 'монохром?'), None),
]


def headline(cv, t):
    for t0, t1, lines, sub in HEADS:
        a = appear(t, t0, 0.3) * (1 - appear(t, t1 - 0.25, 0.25))
        if a <= 0:
            continue
        y = 150 + 14 * (1 - a)
        big = 70 if len(lines) == 1 else 60
        for j, s in enumerate(lines):
            col = ACCENT if (j == 0 and len(lines) == 2 and s.startswith('Вид')) else INK
            put(cv, text(s, big if not s.startswith('Вид') else 52, 'Heavy', col), 540, y + j * (big + 14), 1.0, a)
        if sub:
            pill = fx.solid_pill(sub, (236, 72, 120), 30)
            put(cv, pill, 540, y + len(lines) * (big + 14) + 22, 1.0, a)


# ------------------------------------------------------------------ cards
CARD_Y = 600           # центр плитки
TILE = 300


def card(cv, t, c, cx, cy, s, a, t_anim, highlight=0.0, dim=0.0, mark=None):
    """Карточка: название коллекции, плитка (фон + живая модель), модель/фон с %, цена."""
    if a <= 0:
        return
    a = a * max(0.0, 1 - 0.7 * dim)
    tile = gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t_anim)
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), cx, cy + 14 * s, s, a)
    put(cv, tile, cx, cy, s, a)
    put(cv, text(c['gift'], 34, 'Heavy'), cx, cy - (TILE / 2 + 34) * s, s, a)
    hl = (226, 54, 120) if highlight > 0.5 else INK
    l1 = multi((('Модель ', MUTED), (c['model'], hl), ('  ' + pct(c['model_pct']), ACCENT)), 27, 'Semibold')
    l2 = multi((('Фон ', MUTED), (c['backdrop'], hl), ('  ' + pct(c['backdrop_pct']), ACCENT)), 27, 'Semibold')
    put(cv, l1, cx, cy + (TILE / 2 + 32) * s, s, a)
    put(cv, l2, cx, cy + (TILE / 2 + 68) * s, s, a)
    if highlight > 0:
        g = tinted_glow((255, 200, 60))
        for yy in (TILE / 2 + 30, TILE / 2 + 64):
            put(cv, g.resize((300, 60)), cx, cy + yy * s, s, 0.35 * highlight * a)
    put(cv, text(rub(c['rub']), 42, 'Heavy', ACCENT), cx, cy + (TILE / 2 + 116) * s, s, a)
    st = 'продан на Fragment' if c['status'] == 'Sold' else 'в продаже на Fragment'
    put(cv, text(st, 21, 'Medium', MUTED, False), cx, cy + (TILE / 2 + 154) * s, s, a * 0.9)
    if mark:
        put(cv, mark, cx + TILE * 0.36 * s, cy - TILE * 0.36 * s, s, a)


XS = (185, 540, 895)


def card_row(cv, t, key, t_in, zoom_i=None, zoom_t=None, zoom_len=1.9, t_out=None, highlight_t=None, mark_t=None):
    cs = CARDS[key]
    pops = E.CARD_POPS[key]
    z = 0.0
    if zoom_t is not None:
        z = appear(t, zoom_t, 0.4) * (1 - appear(t, zoom_t + zoom_len, 0.45))
    out = appear(t, t_out, 0.3) if t_out else 0.0
    order = [j for j in range(3) if j != zoom_i] + ([zoom_i] if zoom_i is not None else [])
    for j in order:
        tj = pops[j] - 0.08
        a = appear(t, tj, 0.3) * (1 - out)
        if a <= 0:
            continue
        pop = fx.ease_out_back(fx.clamp01((t - tj) / 0.45)) if t < tj + 0.45 else 1.0
        s = 0.95 * (0.6 + 0.4 * pop) * (1 + 0.025 * beat_pulse(t, 8))
        cx, cy = XS[j], CARD_Y + 30 * (1 - a)
        dim = 0.0
        if zoom_i is not None:
            if j == zoom_i:
                cx, cy = cx + (540 - cx) * z, cy - 40 * z
                s *= 1 + 0.36 * z
            else:
                dim = z * 1.3
        hl = appear(t, highlight_t, 0.25) if highlight_t else 0.0
        mk = None
        if mark_t and t >= mark_t:
            mk = neq_badge()
            mk = fx.fade(mk, appear(t, mark_t, 0.25))
        card(cv, t, cs[j], cx, cy, s, a, t - tj, hl, dim, mk)


@functools.lru_cache(None)
def neq_badge():
    return fx.solid_pill('≠ цвет', (230, 60, 80), 26)


# ------------------------------------------------------------------ scenes
def scene_hook(cv, t):
    left, right = CARDS['hook']
    out = appear(t, E.TYPE1 - 0.35, 0.35)
    if out >= 1:
        return
    a0 = appear(t, 0.05, 0.4)
    focus = appear(t, E.INTRO, 0.4)          # «правая — монохром»: левая уходит в тень, правая в центр
    spin_away = appear(t, E.SPIN - 0.2, 0.4)
    for j, c in enumerate((left, right)):
        tj = E.HOOK_POPS[j] - 0.08
        a = appear(t, tj, 0.35) * a0 * (1 - out)
        pop = fx.ease_out_back(fx.clamp01((t - tj) / 0.5)) if t < tj + 0.5 else 1.0
        s = 1.25 * (0.6 + 0.4 * pop) * (1 + 0.02 * beat_pulse(t, 8))
        cx = (290, 790)[j]
        cy = 640
        if j == 0:
            a *= 1 - 0.7 * focus
            s *= 1 - 0.15 * focus
        else:
            cx += (540 - cx) * focus * 0.35
            s *= 1 + 0.12 * focus
        a *= 1 - 0.55 * spin_away
        tile = gift_tile(c['gift'], c['model'], c['backdrop'], 300, t - tj)
        put(cv, fx.soft_shadow(300, 300, 48, 26, 0.6), cx, cy + 16 * s, s, a)
        put(cv, tile, cx, cy, s, a)
        put(cv, multi(((c['model'], INK), (' · ', MUTED), (c['backdrop'], MUTED)), 28, 'Semibold'), cx, cy + 215 * s / 1.25, 1.0, a)
        price = c['rub']
        if j == 1:                      # цена правой растёт ×10 на «в десять раз»
            k = fx.clamp01((t - (E.PRICE_X10 - 0.5)) / 0.5)
            price = int(round((left['rub'] + (c['rub'] - left['rub']) * ease(k)) / 10) * 10) if k < 1 else c['rub']
            if t < E.PRICE_X10 - 0.5:
                price = None
        if price is not None:
            put(cv, text(rub(price), 44, 'Heavy', ACCENT), cx, cy + 268 * s / 1.25, 1.0, a)
        elif t > 0.6:
            put(cv, text('≈ ? ₽', 44, 'Heavy', ACCENT), cx, cy + 268 * s / 1.25, 1.0, a)
        if j == 1 and t >= E.PRICE_X10:
            k = t - E.PRICE_X10
            ps = fx.spring(fx.clamp01(k / 0.6))
            put(cv, fx.solid_pill('×10', (236, 72, 120), 40), cx + 130 * s, cy - 150 * s, 0.6 + 0.4 * ps, a)
        if j == 1 and focus > 0:
            put(cv, fx.solid_pill('МОНОХРОМ', (30, 24, 48), 30), cx, cy - 190 * s, 1.0, a * focus)
    # счётчик видов 1 · 2 · 3
    for j in range(3):
        tj = E.COUNTER + 0.29 * j
        a = appear(t, tj, 0.25) * (1 - out)
        if a > 0:
            ps = fx.ease_out_back(fx.clamp01((t - tj) / 0.4))
            put(cv, fx.solid_pill(str(j + 1), ((240, 110, 180), (90, 170, 255), (30, 24, 48))[j], 40, WHITE), 400 + 140 * j, 300, 0.5 + 0.5 * ps, a)


def scene_type1(cv, t):
    if not (E.TYPE1 - 0.1 <= t < E.TYPE2 + 0.4):
        return
    card_row(cv, t, 'type1', E.TYPE1, zoom_i=0, zoom_t=E.TYPE1_ZOOM, t_out=E.TYPE2 - 0.05)


def scene_type2(cv, t):
    if not (E.TYPE2 - 0.1 <= t < E.SEEN + 0.4):
        return
    card_row(cv, t, 'type2', E.TYPE2, zoom_i=0, zoom_t=E.TYPE2_COLOR - 0.2, zoom_len=1.5, t_out=E.SEEN - 0.05,
             highlight_t=E.TYPE2_NAMES, mark_t=E.TYPE2_COLOR)


@functools.lru_cache(None)
def mystery_tile():
    im = fx.rounded(TILE, TILE, 46, (24, 20, 40, 255), (120, 100, 170, 255), 3)
    q = text('?', 150, 'Heavy', (170, 150, 230), False)
    im = im.copy()
    im.alpha_composite(q, ((TILE - q.width) // 2, (TILE - q.height) // 2))
    return im


def scene_tease(cv, t):
    if not (E.TEASE - 0.1 <= t < E.TYPE3 + 0.5):
        return
    flash = appear(t, E.TYPE3 - 0.02, 0.2)
    for j in range(3):
        tj = E.CARD_POPS['tease'][j] - 0.08
        a = appear(t, tj, 0.35) * (1 - flash)
        if a <= 0:
            continue
        wob = math.sin(t * 3 + j) * 0.03
        put(cv, mystery_tile(), XS[j], CARD_Y + 20 * (1 - a), 0.92 * (1 + 0.03 * beat_pulse(t, 8)), a, wob)


def scene_type3(cv, t):
    if not (E.TYPE3 - 0.05 <= t < E.WHY + 0.4):
        return
    card_row(cv, t, 'type3', E.TYPE3 - 0.15, zoom_i=2, zoom_t=E.TYPE3_ZOOM, zoom_len=2.4, t_out=E.WHY - 0.05)


def scene_why(cv, t):
    if not (E.WHY - 0.1 <= t < E.OUTRO + 0.4):
        return
    out = appear(t, E.OUTRO - 0.1, 0.3)
    a = appear(t, E.WHY + 0.1, 0.35) * (1 - out)
    left, right = CARDS['hook']
    m = appear(t, E.ORDER, 0.8)                         # хаос → порядок: фон «подстраивается» под подарок
    s = 1.45 * (1 + 0.025 * beat_pulse(t, 7))
    t_an = t - E.WHY
    put(cv, fx.soft_shadow(300, 300, 48, 26, 0.6), 540, 640 + 16, s, a)
    put(cv, gift_tile(left['gift'], left['model'], left['backdrop'], 300, t_an), 540, 640, s, a * (1 - m))
    put(cv, gift_tile(right['gift'], right['model'], right['backdrop'], 300, t_an), 540, 640, s, a * m)
    lab = 'хаос' if m < 0.5 else 'порядок'
    col = MUTED if m < 0.5 else ACCENT
    put(cv, text(lab, 46, 'Heavy', col), 540, 900, 1.0, a)
    if m > 0.95:
        sparkles(cv, t, E.ORDER + 0.8, 540, 640, 260, 12, (236, 72, 120))


def scene_seen(cv, t):
    """«Монохром видно сразу»: монохромный подарок крупно, проценты зачёркнуты, вокруг — сердечки."""
    if not (E.SEEN - 0.1 <= t < E.TEASE + 0.4):
        return
    out = appear(t, E.TEASE - 0.1, 0.3)
    a = appear(t, E.SEEN, 0.35) * (1 - out)
    c = CARDS['hook'][1]
    s = 1.45 * (1 + 0.025 * beat_pulse(t, 7))
    put(cv, fx.soft_shadow(300, 300, 48, 26, 0.6), 540, 640 + 16, s, a)
    put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], 300, t - E.SEEN), 540, 640, s, a)
    k = appear(t, E.SEEN + 1.6, 0.3)                    # «никаких процентов»
    pc = multi((('Модель 0,9%', MUTED), ('   ', MUTED), ('Фон 2%', MUTED)), 34, 'Semibold')
    put(cv, pc, 540, 900, 1.0, a * appear(t, E.SEEN + 0.4, 0.3))
    if k > 0:
        def strike(d, mp, S):
            x0, y = mp(540 - 190 * k, 902)
            x1, _ = mp(540 + 190 * k, 902)
            d.line([x0, y, x1, y], fill=(236, 72, 120, 255), width=int(6 * S))
        fx.over(cv, fx.draw_rgba((330, 870, 750, 930), strike), a)
    hearts(cv, t, E.SEEN + 0.4, a)

def hearts(cv, t, t0, a):
    def draw(d, mp, S):
        rng = np.random.default_rng(3)
        for j in range(10):
            ph = (t - t0 - j * 0.18)
            if ph < 0:
                continue
            ph = ph % 1.8
            x = 540 + rng.uniform(-330, 330)
            y = 980 - ph * 300
            al = int(255 * min(1, ph * 4) * max(0, 1 - ph / 1.8))
            r = rng.uniform(16, 28) * S
            X, Y = mp(x, y)
            col = (255, 90, 140, al)
            d.ellipse([X - r, Y - r, X, Y], fill=col)
            d.ellipse([X, Y - r, X + r, Y], fill=col)
            d.polygon([(X - r, Y - r * 0.45), (X + r, Y - r * 0.45), (X, Y + r * 0.9)], fill=col)
    fx.over(cv, fx.draw_rgba((150, 520, 930, 1040), draw), a)


def scene_outro(cv, t):
    if t < E.OUTRO - 0.1:
        return
    picks = (CARDS['type1'][0], CARDS['type2'][0], CARDS['type3'][2])
    for j, c in enumerate(picks):
        tj = E.CARD_POPS['outro'][j] - 0.08
        a = appear(t, tj, 0.35)
        if a <= 0:
            continue
        pop = fx.ease_out_back(fx.clamp01((t - tj) / 0.45))
        s = 0.88 * (0.6 + 0.4 * pop) * (1 + 0.025 * beat_pulse(t, 8))
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), XS[j], 610 + 14, s, a)
        put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - tj), XS[j], 610, s, a)
        put(cv, text(('цвет в цвет', 'названия', 'чёрно-белый')[j], 28, 'Semibold', MUTED), XS[j], 775, 1.0, a)
    k = appear(t, E.OUTRO + 0.9, 0.35)
    put(cv, fx.solid_pill('Пиши в комментариях', (236, 72, 120), 34), 540, 860, 0.8 + 0.2 * k, k)


# ------------------------------------------------------------------ v4: наполнение кадра
SIDE_Y = 1400          # центр боковых панелей
LX, RX = 172, 908      # центры левой и правой панелей
PANEL_W, PANEL_H = 300, 330


def scene_key(t):
    if t < E.TYPE1:
        return 'intro'
    if t < E.TYPE2:
        return 'type1'
    if t < E.SEEN:
        return 'type2'
    if t < E.TEASE:
        return 'seen'
    if t < E.TYPE3:
        return 'tease'
    if t < E.WHY:
        return 'type3'
    if t < E.OUTRO:
        return 'why'
    return 'outro'


def window_a(t, t0, t1, d=0.3):
    return appear(t, t0, d) * (1 - appear(t, t1 - d, d))


@functools.lru_cache(None)
def panel(w=PANEL_W, h=PANEL_H):
    im = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0))
    sh = fx.soft_shadow(w, h, 34, 18, 0.18)
    im.alpha_composite(sh.resize((w + 60, h + 60)))
    im.alpha_composite(fx.rounded(w, h, 34, (255, 255, 255, 236), (232, 224, 246, 255), 2), (30, 26))
    return im


def put_panel(cv, cx, cy, a, pop_t, t, h=PANEL_H):
    pop = fx.ease_out_back(fx.clamp01((t - pop_t) / 0.45)) if t < pop_t + 0.45 else 1.0
    put(cv, panel(PANEL_W, h), cx, cy, 0.7 + 0.3 * pop, a)
    return 0.7 + 0.3 * pop


# ---- большая бледная цифра вида за Митой
@functools.lru_cache(None)
def big_digit(d):
    return text(d, 760, 'Heavy', (234, 227, 246))


def big_number(cv, t):
    for d, t0, t1 in (('1', E.TYPE1, E.TYPE2), ('2', E.TYPE2, E.SEEN), ('3', E.TEASE, E.WHY)):
        a = window_a(t, t0, t1, 0.4)
        if a > 0:
            put(cv, big_digit(d), 540, 1330 + 30 * (1 - a), 1.0 + 0.015 * beat_pulse(t, 6), a)


# ---- полоса прогресса «вид 1 · 2 · 3»
def progress(cv, t):
    a = window_a(t, E.INTRO + 0.6, E.OUTRO + 0.4, 0.4)
    if a <= 0:
        return
    cur = {'type1': 0, 'type2': 1, 'seen': 1, 'tease': 2, 'type3': 2}.get(scene_key(t), -1)
    for j in range(3):
        on = j == cur
        done = cur > j or scene_key(t) in ('why', 'outro')
        fill = ACCENT if on else ((30, 24, 48) if done else (226, 220, 238))
        tc = WHITE if (on or done) else MUTED
        put(cv, fx.solid_pill(f'вид {j + 1}', fill, 22, tc), 540 + (j - 1) * 150, 64, 1.0 + (0.06 * beat_pulse(t, 8) if on else 0), a)


# ---- плывущие подарки по краям (живые модели текущей сцены), за всем остальным
DRIFT = {'intro': [('hook', 1), ('hook', 0)], 'type1': [('type1', 1), ('type1', 2)], 'type2': [('type2', 1), ('type2', 2)],
         'seen': [('hook', 1), ('type1', 2)], 'tease': [], 'type3': [('type3', 0), ('type3', 1)],
         'why': [('type1', 1), ('type3', 2)], 'outro': [('type1', 0), ('type3', 0)]}


def drifting_gifts(cv, t):
    k = scene_key(t)
    for side, (key, i) in enumerate(DRIFT[k]):
        c = CARDS[key][i]
        for m in range(2):
            ph = (t * 0.045 + m * 0.5 + side * 0.25) % 1.0
            y = 1900 - ph * 1900
            x = (58, 1022)[side] + math.sin(t * 0.9 + m * 2 + side) * 16
            a = 0.42 * min(1.0, ph * 6, (1 - ph) * 6)
            g = lottie.frame(model_path(c['gift'], c['model']), t + m, size=110)
            put(cv, g, x, y, 1.0, a, math.sin(t * 0.7 + m) * 0.15)


# ---- субтитры с подсветкой текущего слова
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


def _disp(w):
    return re.sub(r'[.,:;…]+$', '', w.replace('«', '').replace('»', ''))


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
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = ACCENT if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (INK if on else (150, 144, 170))
        parts.append(((' ' if j else '') + _disp(w[0]).upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    pop = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    plate = fx.rounded(pw, 84, 30, (255, 255, 255, 228), (236, 228, 248, 255), 2)
    put(cv, plate, 540, 990, 0.85 + 0.15 * pop, 1.0)
    put(cv, im, 540, 990, sc * (0.85 + 0.15 * pop), 1.0)


# ---- реакции над Митой
REACT = [(E.PRICE_X10, '!'), (E.SPIN, 'note'), (E.TYPE1_ZOOM, 'heart'), (E.TYPE2_COLOR, '?'),
         (E.TYPE3 + 0.15, '!'), (E.TYPE3_ZOOM, 'heart'), (E.ORDER, 'heart'), (E.CREEPY + 0.3, 'dots')]


def reactions(cv, t):
    for t0, kind in REACT:
        k = t - t0
        if not 0 <= k < 1.3:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 0.9) / 0.4))
        pop = fx.ease_out_back(fx.clamp01(k / 0.35))
        x, y = 700, 1075 - 40 * ease(k / 1.3)
        if kind in ('!', '?'):
            put(cv, fx.solid_pill(kind, ACCENT if kind == '!' else (90, 120, 230), 44), x, y, 0.6 + 0.4 * pop, a, -0.15)
            if kind == '?':                       # капелька пота
                def drop(d, mp, S):
                    X, Y = mp(615, 1110 + 30 * ease(k / 1.3))
                    r = 11 * S
                    d.polygon([(X, Y - r * 1.8), (X - r, Y), (X + r, Y)], fill=(120, 190, 255, int(220 * a)))
                    d.ellipse([X - r, Y - r, X + r, Y + r], fill=(120, 190, 255, int(220 * a)))
                fx.over(cv, fx.draw_rgba((580, 1060, 650, 1160), drop))
        else:
            def icon(d, mp, S):
                X, Y = mp(x, y)
                r = 26 * S * (0.6 + 0.4 * pop)
                if kind == 'heart':
                    col = (236, 72, 120, int(255 * a))
                    d.ellipse([X - r, Y - r, X, Y], fill=col)
                    d.ellipse([X, Y - r, X + r, Y], fill=col)
                    d.polygon([(X - r, Y - r * 0.45), (X + r, Y - r * 0.45), (X, Y + r * 0.95)], fill=col)
                elif kind == 'note':
                    col = (120, 90, 230, int(255 * a))
                    d.ellipse([X - r * 0.9, Y, X, Y + r * 0.7], fill=col)
                    d.rectangle([X - r * 0.15, Y - r * 1.2, X, Y + r * 0.35], fill=col)
                    d.polygon([(X, Y - r * 1.2), (X + r * 0.7, Y - r * 0.8), (X, Y - r * 0.6)], fill=col)
                else:
                    for j in range(3):
                        rr = r * 0.28
                        cxx = X - r + j * r
                        d.ellipse([cxx - rr, Y - rr, cxx + rr, Y + rr], fill=(30, 24, 48, int(200 * a)))
            fx.over(cv, fx.draw_rgba((x - 60, y - 70, x + 60, y + 60), icon))


# ---- правая панель: шанс сочетания
CHANCE = [  # (с, по, подпись, формула, итог)
    (E.INTRO + 0.4, E.SPIN - 0.4, 'Sweetheart + Fandango', '0,9% × 2%', '≈ 1 из 5 600'),
    (E.TYPE1 + 0.9, E.TYPE2, 'Whip Cupcake', '1,5% × 1,5%', '≈ 1 из 4 400'),
    (E.TYPE2 + 0.9, E.SEEN, 'Big Year', '2,9% × 1,2%', '≈ 1 из 2 900'),
    (E.TYPE3 + 0.7, E.WHY, 'Love Potion', '2% × 1,5%', '≈ 1 из 3 300'),
]


def side_right(cv, t):
    for t0, t1, who, f, res in CHANCE:
        a = window_a(t, t0, t1, 0.3)
        if a <= 0:
            continue
        s = put_panel(cv, RX, SIDE_Y, a, t0, t)
        y = SIDE_Y - 115
        put(cv, text('шанс сочетания', 24, 'Semibold', MUTED), RX, y, s, a)
        put(cv, text(who, 26, 'Bold'), RX, y + 52 * s, s, a)
        put(cv, text(f, 40, 'Heavy'), RX, y + 120 * s, s, a)
        put(cv, text(res, 40, 'Heavy', ACCENT), RX, y + 185 * s, s, a)


# ---- левая панель: по сценам
@functools.lru_cache(None)
def model_color(gift, model):
    im = np.array(Image.open(gifts_api.model_png(gift, model, size=128)).convert('RGBA')).astype(float)
    px = im[..., :3][im[..., 3] > 160]
    return tuple(int(v) for v in np.median(px, 0))


def bars(cv, t, t0, a, lo, hi, lo_lab, hi_lab, mult):
    s = put_panel(cv, LX, SIDE_Y, a, t0, t)
    g = ease((t - t0 - 0.2) / 0.8)
    base = SIDE_Y + 105
    maxh = 150
    for j, (v, lab, col) in enumerate(((lo, lo_lab, (190, 184, 210)), (hi, hi_lab, ACCENT))):
        h = max(8, maxh * (v / hi) * g)
        x = LX - 62 + 124 * j
        def bar(d, mp, S, h=h, x=x, col=col):
            x0, y0 = mp(x - 38, base - h)
            x1, y1 = mp(x + 38, base)
            d.rounded_rectangle([x0, y0, x1, y1], int(12 * S), fill=col + (int(255 * a),))
        fx.over(cv, fx.draw_rgba((x - 45, base - maxh - 10, x + 45, base + 4), bar))
        put(cv, text(lab, 22, 'Bold', INK if j == 0 else ACCENT), x, base + 26, 1.0, a)
    put(cv, text(mult, 38, 'Heavy', ACCENT), LX + 62, base - maxh * g - 30, 1.0, a * g)
    put(cv, text('обычная  ·  монохром', 20, 'Semibold', MUTED), LX, SIDE_Y - 140, 1.0, a)


def chips(cv, t, t0, a, c1, c2, merge, ok, label):
    s = put_panel(cv, LX, SIDE_Y, a, t0, t)
    m = ease(merge)
    for j, col in enumerate((c1, c2)):
        cx = LX + (-58 + 116 * j) * (1 - 0.5 * m * ok)
        def dot(d, mp, S, cx=cx, col=col):
            X, Y = mp(cx, SIDE_Y - 30)
            r = 52 * S
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=col + (int(255 * a),), outline=(255, 255, 255, int(255 * a)), width=int(4 * S))
        fx.over(cv, fx.draw_rgba((LX - 140, SIDE_Y - 100, LX + 140, SIDE_Y + 40), dot))
    put(cv, text('подарок   фон', 22, 'Semibold', MUTED), LX, SIDE_Y - 112, 1.0, a)
    sign = '✓' if ok else '≠'
    put(cv, fx.solid_pill(label, (60, 180, 120) if ok else (230, 60, 80), 26), LX, SIDE_Y + 90, 1.0, a * fx.clamp01(merge * 2))


def side_left(cv, t):
    hook_l, hook_r = CARDS['hook']
    # хук: столбики цены ×10
    a = window_a(t, E.PRICE_X10 - 0.3, E.SPIN - 0.4)
    if a > 0:
        bars(cv, t, E.PRICE_X10 - 0.3, a, hook_l['rub'], hook_r['rub'], '865 ₽', '8 653 ₽', '×10')
    # кружение: анонс трёх видов
    a = window_a(t, E.SPIN - 0.4, E.TYPE1)
    if a > 0:
        put_panel(cv, LX, SIDE_Y, a, E.SPIN - 0.4, t)
        put(cv, text('впереди', 22, 'Semibold', MUTED), LX, SIDE_Y - 135, 1.0, a)
        for j, c in enumerate((CARDS['type1'][0], CARDS['type2'][0], CARDS['type3'][2])):
            tile = gift_tile(c['gift'], c['model'], c['backdrop'], 84, t)
            put(cv, tile, LX - 60, SIDE_Y - 70 + j * 92, 1.0, a)
            put(cv, text(('цвет в цвет', 'названия', 'чёрно-белый')[j], 22, 'Bold'), LX + 50, SIDE_Y - 70 + j * 92, 1.0, a)
    # вид 1: цвет подарка и фона сливаются
    a = window_a(t, E.TYPE1 + 0.6, E.TYPE2)
    if a > 0:
        c = CARDS['type1'][0]
        chips(cv, t, E.TYPE1 + 0.6, a, model_color(c['gift'], c['model']), hexrgb(backdrop_hex(c['gift'], c['backdrop'])[0]),
              (t - E.TYPE1 - 1.2) / 1.0, 1, 'цвет в цвет ✓')
    # вид 2: названия совпали, цвет — нет
    a = window_a(t, E.TYPE2 + 0.6, E.SEEN)
    if a > 0:
        c = CARDS['type2'][0]
        if t < E.TYPE2_COLOR - 0.3:
            put_panel(cv, LX, SIDE_Y, a, E.TYPE2 + 0.6, t)
            k = appear(t, E.TYPE2_NAMES, 0.3)
            put(cv, text('модель', 22, 'Semibold', MUTED), LX, SIDE_Y - 120, 1.0, a)
            put(cv, text('Cyberpunk', 34, 'Heavy'), LX, SIDE_Y - 82, 1.0, a)
            put(cv, text('=', 46, 'Heavy', ACCENT), LX, SIDE_Y - 25, 1.0, a * k)
            put(cv, text('фон', 22, 'Semibold', MUTED), LX, SIDE_Y + 25, 1.0, a)
            put(cv, text('Cyberpunk', 34, 'Heavy'), LX, SIDE_Y + 63, 1.0, a)
            put(cv, fx.solid_pill('названия ✓', (60, 180, 120), 24), LX, SIDE_Y + 125, 1.0, a * k)
        else:
            chips(cv, t, E.TYPE2_COLOR - 0.3, a, model_color(c['gift'], c['model']),
                  hexrgb(backdrop_hex(c['gift'], c['backdrop'])[0]), (t - E.TYPE2_COLOR) / 0.6, 0, 'цвет ≠')
    # «видно сразу»: глаз
    a = window_a(t, E.SEEN + 0.3, E.TEASE)
    if a > 0:
        put_panel(cv, LX, SIDE_Y, a, E.SEEN + 0.3, t)
        blink = 1 - 0.85 * max(0.0, math.sin(t * 2.2) ** 40)
        def eye(d, mp, S):
            X, Y = mp(LX, SIDE_Y - 30)
            w, h = 95 * S, 55 * S * blink
            d.ellipse([X - w, Y - h, X + w, Y + h], fill=(255, 255, 255, int(255 * a)), outline=(30, 24, 48, int(255 * a)), width=int(6 * S))
            r = min(34 * S, h)
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=(236, 72, 120, int(255 * a)))
            for k_ in range(7):
                ang = -math.pi + k_ * math.pi / 6
                d.line([X + math.cos(ang) * 120 * S, Y + math.sin(ang) * 90 * S, X + math.cos(ang) * 145 * S,
                        Y + math.sin(ang) * 110 * S], fill=(255, 190, 60, int(255 * a)), width=int(6 * S))
        fx.over(cv, fx.draw_rgba((LX - 150, SIDE_Y - 150, LX + 150, SIDE_Y + 60), eye))
        put(cv, text('сразу видно', 30, 'Heavy'), LX, SIDE_Y + 95, 1.0, a)
    # тизер: «?»
    a = window_a(t, E.TEASE + 0.2, E.TYPE3 + 0.2)
    if a > 0:
        put_panel(cv, LX, SIDE_Y, a, E.TEASE + 0.2, t)
        put(cv, text('?', 200, 'Heavy', ACCENT), LX, SIDE_Y - 10, 1.0, a, math.sin(t * 5) * 0.12)
    # вид 3: столбики цены Love Potion · Milkshake
    a = window_a(t, E.TYPE3 + 0.7, E.WHY)
    if a > 0:
        c = CARDS['type3'][2]
        lo = round(c['model_floor_ton'] * DATA['ton_rub'])
        bars(cv, t, E.TYPE3 + 0.7, a, lo, c['rub'], f'{lo:,} ₽'.replace(',', ' '), f"{c['rub']:,} ₽".replace(',', ' '),
             f"×{c['rub'] / lo:.0f}")
    # почему нравится: хаос → порядок
    a = window_a(t, E.WHY + 0.3, E.OUTRO)
    if a > 0:
        put_panel(cv, LX, SIDE_Y, a, E.WHY + 0.3, t)
        m = ease((t - E.ORDER) / 0.8)
        rng = np.random.default_rng(5)
        cols = [(236, 72, 120), (120, 90, 230), (255, 190, 60), (70, 190, 230), (150, 220, 160), (30, 24, 48)]
        def blocks(d, mp, S):
            for j in range(6):
                x0, y0 = LX + rng.uniform(-100, 100), SIDE_Y + rng.uniform(-110, 50)
                r0 = rng.uniform(-0.8, 0.8)
                x1, y1 = LX - 100 + (j % 3) * 100, SIDE_Y - 70 + (j // 3) * 95
                x, y = x0 + (x1 - x0) * m, y0 + (y1 - y0) * m
                col = tuple(int(c0 + (p - c0) * m) for c0, p in zip(cols[j], (236, 72, 120)))
                rot = r0 * (1 - m)
                pts = [(x + math.cos(rot + q * math.pi / 2 + math.pi / 4) * 46, y + math.sin(rot + q * math.pi / 2 + math.pi / 4) * 46) for q in range(4)]
                d.polygon([mp(px, py) for px, py in pts], fill=col + (int(255 * a),))
        fx.over(cv, fx.draw_rgba((LX - 150, SIDE_Y - 160, LX + 150, SIDE_Y + 120), blocks))
        put(cv, text('порядок' if m > 0.5 else 'хаос', 30, 'Heavy', ACCENT if m > 0.5 else MUTED), LX, SIDE_Y + 125, 1.0, a)
    # финал: печатающийся комментарий
    a = window_a(t, E.OUTRO + 0.5, DUR + 2)
    if a > 0:
        put_panel(cv, LX, SIDE_Y, a, E.OUTRO + 0.5, t, 240)
        put(cv, text('новый комментарий', 22, 'Semibold', MUTED), LX, SIDE_Y - 75, 1.0, a)
        def dots(d, mp, S):
            for j in range(3):
                ph = math.sin(t * 6 - j * 0.9)
                X, Y = mp(LX - 50 + j * 50, SIDE_Y + 10 - 10 * max(0, ph))
                r = 15 * S
                d.ellipse([X - r, Y - r, X + r, Y + r], fill=(236, 72, 120, int(255 * a * (0.5 + 0.5 * max(0, ph)))))
        fx.over(cv, fx.draw_rgba((LX - 100, SIDE_Y - 40, LX + 100, SIDE_Y + 50), dots))



def vignette(cv, t):
    c = ease((t - E.CREEPY) / 1.8)
    if c <= 0:
        return
    yy, xx = np.ogrid[0:H, 0:W]
    r = np.sqrt(((xx - 540) / 620) ** 2 + ((yy - 1250) / 1100) ** 2)
    v = np.clip((r - 0.45) / 0.7, 0, 1) ** 1.4 * 0.85 * c
    cv[..., :3] *= (1 - v)[..., None]


def render_at(t):
    cv = background(t)
    big_number(cv, t)
    drifting_gifts(cv, t)
    progress(cv, t)
    headline(cv, t)
    scene_hook(cv, t)
    scene_type1(cv, t)
    scene_type2(cv, t)
    scene_seen(cv, t)
    scene_tease(cv, t)
    scene_type3(cv, t)
    scene_why(cv, t)
    scene_outro(cv, t)
    side_left(cv, t)
    side_right(cv, t)
    draw_mita(cv, t)
    reactions(cv, t)
    subtitles(cv, t)
    # вспышка на «чёрно-белый» после рекламы
    fl = math.exp(-max(0.0, t - E.TYPE3) * 6) if t >= E.TYPE3 else 0.0
    if fl > 0.01:
        cv[..., :3] = cv[..., :3] * (1 - fl * 0.9) + 12 * fl * 0.9
    vignette(cv, t)
    return np.clip(cv[..., :3], 0, 255).astype(np.uint8)


@functools.lru_cache(None)
def teaser_base():
    c = CARDS['type3'][2]
    return c


@functools.lru_cache(None)
def ad_panel():
    im = Image.new('RGBA', (W, 662), (0, 0, 0, 0))
    m = Image.new('L', (W, 662), 0)
    ImageDraw.Draw(m).rounded_rectangle([30, 30, W - 30, 650], 48, fill=240)
    im.paste((252, 250, 255, 255), (0, 0), m)
    return im


def ad_overlay(c, t):
    """Во время RubUp над баннером (не поверх него): «Угадай подарок» — силуэт самого дорогого чёрно-белого
    подарка проясняется за время рекламы, отсчёт до ответа. Ответ — сразу после рекламы («Чёрно-белый монохром!»)."""
    ph = BR.phase(t)
    if ph is None:
        return c
    a = ph['dim']
    bt = ph['bt']
    prog = fx.clamp01(bt / BR.B)
    cv = c.astype(np.float32)
    cv = np.dstack([cv, np.full(cv.shape[:2], 255, np.float32)])
    fx.over(cv, (ad_panel(), 0, 8), a)
    put(cv, text('Угадай подарок', 54, 'Heavy'), 540, 130, 1.0, a)
    cc = teaser_base()
    tile = gift_tile(cc['gift'], cc['model'], cc['backdrop'], 300, t)
    blur = 26 * (1 - prog) ** 1.3 + 2
    dark = 0.85 * (1 - prog) ** 1.2
    tl = tile.filter(ImageFilter.GaussianBlur(blur))
    arr = np.array(tl).astype(np.float32)
    arr[..., :3] *= 1 - dark
    tl = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    wob = 1 + 0.03 * math.sin(t * 4)
    put(cv, fx.soft_shadow(300, 300, 48, 26, 0.5), 540, 395 + 14, 0.95 * wob, a)
    put(cv, tl, 540, 395, 0.95 * wob, a)
    left = max(0, math.ceil(BR.B - max(0.0, bt)))
    lab = f'ответ через {left}' if left > 0 else 'ответ!'
    put(cv, fx.solid_pill(lab, ACCENT, 32), 540, 600, 1.0 + 0.04 * math.sin(t * 6), a)
    return cv[..., :3]


def out_frame(t, i=None):
    return np.clip(ad_overlay(BR.render(render_at, t, i).astype(np.float32), t), 0, 255).astype(np.uint8)


def frame_bytes(i):
    return out_frame(i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--times' in sys.argv:                      # быстрый просмотр по временам содержания: --times 1.2,5,7
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--times') + 1].split(','):
            Image.fromarray(render_at(float(s))).save(out / f't{float(s):06.2f}.png')
            print('t', s)
        raise SystemExit
    if '--out' in sys.argv:                        # просмотр по ВЫХОДНОМУ времени (с рекламой): --out 40,43
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--out') + 1].split(','):
            Image.fromarray(out_frame(float(s))).save(out / f'o{float(s):06.2f}.png')
            print('o', s)
        raise SystemExit
    frames.cli(out_frame, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
