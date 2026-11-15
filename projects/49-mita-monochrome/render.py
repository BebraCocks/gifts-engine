"""«Мита объясняет монохромы» — 1080×1920, 60 fps. Кадр — чистая функция времени содержания.
Карточки подарков: живые Lottie-модели (gifts_api + lottie) на градиенте фона из API, подписи — data/cards_2026-11-15.json.
Мита — арты автора (input/mita), позы по сценам, смена наряда со вспышкой, кружение на «наряды».
Ритм: сильные доли музыки (events.BEATS) — лёгкий толчок кадра, пульс света и подпрыгивание Миты."""
import functools
import json
import math
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

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
DATA = json.loads((HERE / 'data' / 'cards_2026-11-15.json').read_text(encoding='utf-8'))
CARDS = DATA['cards']
MITA = HERE / 'input' / 'mita'
MITA_H = 880            # рост Миты в кадре, px
MITA_FOOT = 1915
WHITE = (255, 255, 255)
MUTED = (178, 176, 205)
ACCENT = (255, 214, 102)


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
def text(s, size, weight='Bold', color=WHITE, shadow=True):
    return fx.text_img(((s, color),), size, weight, shadow)


@functools.lru_cache(None)
def multi(parts, size, weight='Bold', shadow=True):
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
    (E.TEASE, 'normal_secret', True),
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


def sparkles(cv, t, t0, cx, cy, spread, n=14, col=(255, 255, 255)):
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
    (E.TEASE, (40, 30, 70), (80, 50, 110)),
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
    top, bot = np.array([16, 12, 32], np.float32), np.array([8, 6, 18], np.float32)
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
    put(cv, tinted_glow(q(c1)), 240 + 80 * math.sin(t * 0.31), 560 + 60 * math.cos(t * 0.27), 2.6, 0.32 + 0.12 * p)
    put(cv, tinted_glow(q(c2)), 860 + 70 * math.cos(t * 0.23), 1250 + 90 * math.sin(t * 0.29), 2.9, 0.26 + 0.1 * p)
    # плывущие искорки
    def dots(d, mp, S):
        rng = np.random.default_rng(7)
        for j in range(26):
            x0, y0, sp, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(12, 40), rng.uniform(2, 5)
            y = (y0 - t * sp) % H
            x = x0 + math.sin(t * 0.8 + j) * 14
            a = int(70 + 60 * math.sin(t * 1.7 + j * 1.3))
            X, Y = mp(x, y)
            d.ellipse([X - r * S, Y - r * S, X + r * S, Y + r * S], fill=(255, 255, 255, max(0, a)))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), dots))
    return cv


# ------------------------------------------------------------------ headline
HEADS = [  # (с, по, строки, малая подпись)
    (0.0, ON[3] - 0.15, ('Почему одинаковые', 'подарки стоят по-разному?'), 'Мита объясняет'),
    (ON[3] - 0.15, E.TYPE1, ('Монохром',), None),
    (E.TYPE1, E.TYPE2, ('Вид 1', 'цвет в цвет'), None),
    (E.TYPE2, E.TEASE, ('Вид 2', 'одинаковые названия'), None),
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
            col = ACCENT if (j == 0 and len(lines) == 2 and s.startswith('Вид')) else WHITE
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
    hl = (255, 236, 120) if highlight > 0.5 else WHITE
    l1 = multi((('Модель ', MUTED), (c['model'], hl), ('  ' + pct(c['model_pct']), ACCENT)), 27, 'Semibold')
    l2 = multi((('Фон ', MUTED), (c['backdrop'], hl), ('  ' + pct(c['backdrop_pct']), ACCENT)), 27, 'Semibold')
    put(cv, l1, cx, cy + (TILE / 2 + 32) * s, s, a)
    put(cv, l2, cx, cy + (TILE / 2 + 68) * s, s, a)
    if highlight > 0:
        g = tinted_glow((255, 230, 90))
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
        cy = 700
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
        put(cv, multi(((c['model'], WHITE), (' · ', MUTED), (c['backdrop'], MUTED)), 28, 'Semibold'), cx, cy + 215 * s / 1.25, 1.0, a)
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
            put(cv, fx.solid_pill('МОНОХРОМ', (255, 255, 255), 30, (30, 20, 50)), cx, cy - 190 * s, 1.0, a * focus)
    # счётчик видов 1 · 2 · 3
    for j in range(3):
        tj = E.COUNTER + 0.29 * j
        a = appear(t, tj, 0.25) * (1 - out)
        if a > 0:
            ps = fx.ease_out_back(fx.clamp01((t - tj) / 0.4))
            put(cv, fx.solid_pill(str(j + 1), ((240, 110, 180), (90, 170, 255), (235, 235, 240))[j], 40,
                                  (20, 15, 35) if j == 2 else WHITE), 400 + 140 * j, 300, 0.5 + 0.5 * ps, a)


def scene_type1(cv, t):
    if not (E.TYPE1 - 0.1 <= t < E.TYPE2 + 0.4):
        return
    card_row(cv, t, 'type1', E.TYPE1, zoom_i=0, zoom_t=E.TYPE1_ZOOM, t_out=E.TYPE2 - 0.05)


def scene_type2(cv, t):
    if not (E.TYPE2 - 0.1 <= t < E.TEASE + 0.4):
        return
    card_row(cv, t, 'type2', E.TYPE2, zoom_i=0, zoom_t=E.TYPE2_COLOR - 0.2, zoom_len=1.5, t_out=E.TEASE - 0.05,
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
    put(cv, fx.soft_shadow(300, 300, 48, 26, 0.6), 540, 700 + 16, s, a)
    put(cv, gift_tile(left['gift'], left['model'], left['backdrop'], 300, t_an), 540, 700, s, a * (1 - m))
    put(cv, gift_tile(right['gift'], right['model'], right['backdrop'], 300, t_an), 540, 700, s, a * m)
    lab = 'хаос' if m < 0.5 else 'порядок'
    col = (150, 150, 170) if m < 0.5 else ACCENT
    put(cv, text(lab, 46, 'Heavy', col), 540, 960, 1.0, a)
    if m > 0.95:
        sparkles(cv, t, E.ORDER + 0.8, 540, 700, 260, 12, (255, 220, 240))
    # «видно сразу»: проценты зачёркнуты, вокруг — сердечки
    k = appear(t, E.SEEN + 0.3, 0.3)
    if k > 0:
        pc = multi((('0,9%', MUTED), ('  ·  ', MUTED), ('2%', MUTED)), 34, 'Semibold')
        put(cv, pc, 540, 1030, 1.0, a * k * 0.9)
        def strike(d, mp, S):
            x0, y = mp(540 - 110 * k, 1030)
            x1, _ = mp(540 + 110 * k, 1030)
            d.line([x0, y, x1, y], fill=(236, 72, 120, 255), width=int(5 * S))
        fx.over(cv, fx.draw_rgba((400, 1000, 680, 1060), strike), a)
        hearts(cv, t, E.SEEN + 0.3, a)


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
    headline(cv, t)
    scene_hook(cv, t)
    scene_type1(cv, t)
    scene_type2(cv, t)
    scene_tease(cv, t)
    scene_type3(cv, t)
    scene_why(cv, t)
    scene_outro(cv, t)
    draw_mita(cv, t)
    # вспышка на «чёрно-белый» после рекламы
    fl = math.exp(-max(0.0, t - E.TYPE3) * 6) if t >= E.TYPE3 else 0.0
    if fl > 0.01:
        cv[..., :3] = cv[..., :3] * (1 - fl * 0.85) + 255 * fl * 0.85
    vignette(cv, t)
    return np.clip(cv[..., :3], 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--times' in sys.argv:                      # быстрый просмотр по временам содержания: --times 1.2,5,7
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--times') + 1].split(','):
            Image.fromarray(render_at(float(s))).save(out / f't{float(s):06.2f}.png')
            print('t', s)
        raise SystemExit
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
