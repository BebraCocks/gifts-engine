"""«Мита: почему чёрный фон дороже всех» — 1080×1920, 60 fps. Кадр — чистая функция времени содержания.
Белый фон с микродеталями (как 49), раскладка «Б»: заголовок сверху, карточки, Мита, субтитры под ней.
Подарки — живые Lottie-модели (gifts_api) на градиенте фона из API; цены — data/lots_2026-11-16.json (Fragment).
Начало: Мита в обычном наряде, на «переоденусь» — кружение-переход в готику (вспышка на заднем ракурсе)."""
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
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
import banner
import frames
import fx
import gifts_api
import lottie
import music
import events as E
from timeline import DUR, ON, END, AD_STOP, TAKES
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
DATA = json.loads((HERE / 'data' / 'lots_2026-11-16.json').read_text(encoding='utf-8'))
LOTS = DATA['lots']
BLK = json.loads((HERE / 'data' / 'black_2026-11-16.json').read_text(encoding='utf-8'))
MITA = HERE / 'input' / 'mita'
MITA_OLD = HERE.parent / '49-mita-monochrome' / 'input' / 'mita'
MITA_H = 760
MITA_FOOT = 1540
WHITE = (255, 255, 255)
INK = (30, 24, 48)
MUTED = (118, 112, 140)
WINE = (150, 24, 52)            # бордовый акцент готики
ACCENT = (226, 54, 120)
GOLD = (255, 190, 60)
THEME = dict(accent=ACCENT, border=(232, 224, 246))
UFONT = HERE / 'input' / 'fonts'
BEATS = music.beats_in_content()
CONF = [(236, 72, 120), (120, 90, 230), (255, 190, 60), (70, 190, 230), (150, 220, 160), (30, 24, 48)]
PANEL_W, PANEL_H = 280, 320
SIDE_Y = 1150
LX, RX = 168, 836


def lot(g, k):
    return LOTS[f'{g}|{k}']


def beat_pulse(t, decay=7.0):
    b = BEATS[(BEATS <= t) & (BEATS > t - 0.6)]
    return float(np.exp(-(t - b.max()) * decay)) if len(b) else 0.0


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.35):
    return ease((t - t0) / d)


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rub(v):
    return f'≈ {v:,} ₽'.replace(',', ' ')


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


@functools.lru_cache(None)
def silhouette(name, mirror=False):
    im = mita(name, mirror)
    w = Image.new('RGBA', im.size, (255, 255, 255, 0))
    w.putalpha(im.getchannel('A'))
    return w


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


@functools.lru_cache(None)
def grid_dots():
    """Едва заметная точечная сетка — фон не пустой, но не шумит."""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for y in range(24, H, 48):
        for x in range(24 + (24 if (y // 48) % 2 else 0), W, 48):
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(150, 140, 190, 46))
    return im


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


def window_a(t, t0, t1, d=0.3):
    return appear(t, t0, d) * (1 - appear(t, t1 - d, d))


@functools.lru_cache(None)
def panel(w=PANEL_W, h=PANEL_H, border=(232, 224, 246)):
    im = Image.new('RGBA', (w + 60, h + 60), (0, 0, 0, 0))
    sh = fx.soft_shadow(w, h, 34, 18, 0.18)
    im.alpha_composite(sh.resize((w + 60, h + 60)))
    im.alpha_composite(fx.rounded(w, h, 34, (255, 255, 255, 236), border + (255,), 3), (30, 26))
    return im


def put_panel(cv, cx, cy, a, pop_t, t, h=PANEL_H):
    pop = fx.ease_out_back(fx.clamp01((t - pop_t) / 0.45)) if t < pop_t + 0.45 else 1.0
    put(cv, panel(PANEL_W, h, THEME['border']), cx, cy, 0.7 + 0.3 * pop, a)
    return 0.7 + 0.3 * pop


def _disp(w):
    return re.sub(r'[.,:;…]+$', '', w.replace('«', '').replace('»', ''))


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
def upill(s_, fill, size, tcol):
    f = ufont('SemiBold', size)
    tw = int(f.getlength(s_))
    h_ = int(size * 1.9)
    w_ = tw + h_
    S = 2
    im = Image.new('RGBA', (w_ * S, h_ * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w_ * S - 1, h_ * S - 1], h_ * S // 2, fill=fill + (255,))
    d.text((w_ * S / 2, h_ * S / 2), s_, font=ufont('SemiBold', size * S), fill=tcol + (255,), anchor='mm')
    return im.resize((w_, h_), Image.LANCZOS)


# ------------------------------------------------------------------ Mita
@functools.lru_cache(None)
def mita(name, mirror=False):
    p = MITA / f'{name}.png'
    if not p.is_file():
        p = MITA_OLD / f'{name}.png'                # обычный наряд и его кружение — из ролика 49
    im = Image.open(p).convert('RGBA')
    s = MITA_H / im.height
    im = im.resize((max(1, int(im.width * s)), MITA_H), Image.LANCZOS)
    return ImageOps.mirror(im) if mirror else im


# кружение-переход: обычный наряд 0°→180° (spin_a00…a08), на заднем ракурсе вспышка, готика 180°→360° (зеркальные gspin)
SPIN_SEQ = [(f'spin_a{k:02d}', False) for k in range(9)] + [(f'gspin_a{k:02d}', True) for k in range(7, -1, -1)]
SPIN_DUR = 1.05
SPIN_SWAP = 8 / (len(SPIN_SEQ) - 1)                  # доля оборота, где наряд меняется (задний ракурс)
POSES = [  # (с какого времени, поза, вспышка)
    (0.0, 'normal_sly', False),
    (E.HOOK_PRICE, 'normal_surprised', False),
    (ON[2], 'normal_explain', False),
    (E.SPIN + SPIN_DUR, 'goth_explain', False),
    (E.PLAYER, 'goth_luxury', False),
    (E.LOCKET_HIT, 'goth_shock', True),
    (E.RARITY, 'goth_secret', False),
    (E.DEMAND, 'goth_wow', True),
    (E.GLOW, 'goth_explain', False),
    (E.PLAIN, 'goth_fi', False),
    (E.PRICE, 'goth_explain', False),
    (E.OUTRO, 'goth_luxury', False),
]


def pose_at(t):
    cur = POSES[0]
    for p in POSES:
        if t >= p[0]:
            cur = p
    return cur


def spin_k(t):
    return ease((t - E.SPIN) / SPIN_DUR) if E.SPIN <= t < E.SPIN + SPIN_DUR else None


def wind(cv, t, front):
    t0, t1 = E.SPIN - 0.12, E.SPIN + SPIN_DUR + 0.45
    if not t0 <= t < t1:
        return
    k = (t - t0) / (t1 - t0)
    env = fx.smooth(fx.clamp01(k / 0.2)) * (1 - fx.smooth(fx.clamp01((k - 0.6) / 0.4)))
    cx, base = 540, MITA_FOOT
    rot = (t - t0) * 9.0
    def draw(d, mp, S):
        for j, (hy, rx, ry, w, ph) in enumerate(((0.12, 250, 46, 7, 0.0), (0.34, 290, 58, 9, 2.1),
                                                   (0.56, 270, 52, 7, 4.0), (0.76, 220, 40, 5, 1.2))):
            cy = base - MITA_H * hy
            a0 = rot * (1.15 - 0.1 * j) + ph
            pts = []
            for q in range(26):
                ang = a0 + q * 0.085
                sn = math.sin(ang)
                if (sn > 0) != front:
                    if pts:
                        break
                    continue
                pts.append(mp(cx + math.cos(ang) * rx, cy + sn * ry))
            for q in range(1, len(pts)):
                fade = q / len(pts)
                c = (200, 190, 215) if q < len(pts) * 0.5 else WINE
                d.line([pts[q - 1], pts[q]], fill=c + (int(210 * env * fade),), width=max(1, int(w * S * (0.4 + 0.6 * fade))))
        if front:
            rng = np.random.default_rng(23)
            for j in range(18):
                st = rng.uniform(0, 0.55)
                u = (k - st) / 0.45
                if not 0 < u < 1:
                    continue
                ang = rng.uniform(0, 2 * math.pi) + u * 3.0
                r = 120 + u * rng.uniform(220, 380)
                X, Y = mp(cx + math.cos(ang) * r, base - MITA_H * rng.uniform(0.1, 0.8) - u * 120)
                al = int(230 * env * (1 - u))
                if j % 3 == 0:
                    fx.sparkle(d, X, Y, rng.uniform(8, 15) * S, GOLD + (al,))
                else:                                   # тёмно-бордовые лепестки роз
                    rr = rng.uniform(6, 11) * S
                    a2 = ang * 2
                    pts = [(X + math.cos(a2) * rr * 1.6, Y + math.sin(a2) * rr * 1.6), (X + math.cos(a2 + 1.57) * rr * 0.6, Y + math.sin(a2 + 1.57) * rr * 0.6),
                           (X - math.cos(a2) * rr * 1.6, Y - math.sin(a2) * rr * 1.6), (X - math.cos(a2 + 1.57) * rr * 0.6, Y - math.sin(a2 + 1.57) * rr * 0.6)]
                    d.polygon(pts, fill=WINE + (al,))
    fx.over(cv, fx.draw_rgba((cx - 520, base - MITA_H - 260, cx + 520, base + 40), draw))


def draw_mita(cv, t):
    t0, name, flash = pose_at(t)
    mirror, blend = False, None
    k = spin_k(t)
    if k is not None:
        f = k * (len(SPIN_SEQ) - 1)
        i = min(len(SPIN_SEQ) - 2, int(f))
        name, mirror = SPIN_SEQ[i]
        blend = (SPIN_SEQ[i + 1], f - i)
    im = mita(name, mirror)
    since = t - t0
    pop = fx.spring(fx.clamp01(since / 0.5)) if since < 0.5 else 1.0
    sq = 1 + 0.035 * (1 - pop)
    tk = talk(t)
    bob = math.sin(t * 2.1) * 4 - 8 * beat_pulse(t, 9)
    sy = (1 + 0.006 * math.sin(t * 2.6) + 0.012 * tk) / sq
    sx = sq * (1 - 0.004 * tk)
    cx = 540 + math.sin(t * 0.7) * 6
    if k is not None:
        bob -= 18 * math.sin(math.pi * (t - E.SPIN) / SPIN_DUR)
    placed = fx.warp(im, cx, MITA_FOOT + bob, sx, sy, 0.0, (im.width / 2, im.height))
    put(cv, fx.radial(256, (0, 0, 0), 1.6, 0.55).resize((420, 70)), cx, MITA_FOOT - 4, 1.0, 0.8)
    fx.over(cv, placed)
    if blend:
        (n2, m2), w2 = blend
        im2 = mita(n2, m2)
        fx.over(cv, fx.warp(im2, cx, MITA_FOOT + bob, sx, sy, 0.0, (im2.width / 2, im2.height)), fx.smooth(fx.clamp01(w2)))
        # вспышка на заднем ракурсе — смена наряда
        d = abs(k - SPIN_SWAP)
        if d < 0.16:
            a = (1 - d / 0.16) ** 1.4
            fx.over(cv, fx.warp(silhouette(name, mirror), cx, MITA_FOOT + bob, sx, sy, 0.0, (im.width / 2, im.height)), a * 0.95)
    if k is not None and abs(k - SPIN_SWAP) < 0.02:
        pass
    swap_t = E.SPIN + SPIN_DUR * 0.62
    sparkles(cv, t, swap_t, cx, MITA_FOOT - MITA_H * 0.55, 380, 18, GOLD)
    if flash and since < 0.55:
        a = (1 - since / 0.55) ** 1.5
        fx.over(cv, fx.warp(silhouette(name, mirror), cx, MITA_FOOT + bob, sx, sy, 0.0, (im.width / 2, im.height)), a * 0.8)
        sparkles(cv, t, t0, cx, MITA_FOOT - MITA_H * 0.55, 340)


# ------------------------------------------------------------------ background (белый, микродетали)
def background(t):
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = base_bg()
    cv[..., 3] = 255
    goth = fx.smooth(fx.clamp01((t - E.SPIN - 0.6) / 0.8))
    c1 = tuple(int(a * (1 - goth) + b * goth) for a, b in zip((120, 70, 200), (150, 40, 80)))
    c2 = tuple(int(a * (1 - goth) + b * goth) for a, b in zip((220, 90, 160), (60, 50, 90)))
    p = beat_pulse(t, 5)
    put(cv, tinted_glow(c1), 230 + 80 * math.sin(t * 0.31), 560 + 60 * math.cos(t * 0.27), 2.8, 0.14 + 0.06 * p)
    put(cv, tinted_glow(c2), 860 + 70 * math.cos(t * 0.23), 1300 + 90 * math.sin(t * 0.29), 3.0, 0.11 + 0.05 * p)
    fx.over(cv, (grid_dots(), 0, 0))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), lambda d, mp, S: confetti(d, mp, S, t)))
    return cv


# ------------------------------------------------------------------ заголовок
HEADS = [
    (0.0, E.X7, 'Почему чёрный фон дороже?', None),
    (E.X7, E.PLAYER, 'Чёрный = ×7', 'в среднем'),
    (E.PLAYER, E.LOCKET, 'Дороже проигрывателя', None),
    (E.LOCKET, E.RARITY, '17 миллионов ₽?!', None),
    (E.RARITY, E.TEASE, 'Но он не редкий', None),
    (E.TEASE, AD_STOP + 0.4, 'Так почему?', None),
    (AD_STOP + 0.4, E.GLOW, 'Всё дело в спросе', None),
    (E.GLOW, E.PLAIN, 'Чёрный выделяет', None),
    (E.PLAIN, E.PRICE, 'Обычный фон', None),
    (E.PRICE, E.OUTRO, 'Спрос > цена ↑', None),
    (E.OUTRO, DUR + 1, 'Люкс или минимум?', None),
]


def headline(cv, t):
    for t0, t1, s, sub in HEADS:
        a = appear(t, t0, 0.3) * (1 - appear(t, t1 - 0.25, 0.25))
        if a <= 0:
            continue
        y = 150 + 10 * (1 - a)
        im = text(s, 52, 'Heavy')
        put(cv, im, 540, y, min(1.0, 1000 / im.width), a)
        if sub:
            put(cv, fx.solid_pill(sub, WINE, 24), 540, y + 56, 1.0, a)


# ------------------------------------------------------------------ карточки
TILE = 300


def card(cv, c, cx, cy, s, a, t_anim, price_txt=None, price_col=None, label=True, dim=0.0):
    if a <= 0:
        return
    a *= 1 - 0.7 * dim
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), cx, cy + 14 * s, s, a)
    put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t_anim), cx, cy, s, a)
    if label:
        put(cv, text(c['gift'], 30, 'Heavy'), cx, cy - (TILE / 2 + 30) * s, s, a)
        bcol = INK if c['backdrop'] == 'Black' else MUTED
        put(cv, multi((('Фон ', MUTED), (c['backdrop'], bcol)), 26, 'Semibold'), cx, cy + (TILE / 2 + 30) * s, s, a)
    pt = price_txt if price_txt is not None else rub(c['rub'])
    put(cv, text(pt, 42, 'Heavy', price_col or (WINE if c['backdrop'] == 'Black' else MUTED)), cx, cy + (TILE / 2 + 76) * s, s, a)


def pop_in(t, t0, d=0.45):
    return fx.ease_out_back(fx.clamp01((t - t0) / d)) if t < t0 + d else 1.0


def pair(cv, t, left, right, t_in, t_out, cy=500, s0=1.0, lp=None, rp=None, gap=520, rcol=None):
    out = appear(t, t_out - 0.3, 0.3) if t_out else 0.0
    for j, c in enumerate((left, right)):
        tj = t_in + 0.25 * j
        a = appear(t, tj, 0.3) * (1 - out)
        s = s0 * (0.6 + 0.4 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
        card(cv, c, 540 + (j - 0.5) * gap, cy, s, a, t - tj, (lp, rp)[j], rcol if j else None)


# ---- 1. хук: кекс обычный vs чёрный
def scene_hook(cv, t):
    if t >= E.X7 + 0.3:
        return
    L, R = lot('Whip Cupcake', 'floor'), lot('Whip Cupcake', 'black_floor')
    k = fx.clamp01((t - E.HOOK_PRICE) / 0.6)
    rp = None if k >= 1 else (rub(int(round((L['rub'] + (R['rub'] - L['rub']) * ease(k)) / 10) * 10)) if k > 0 else '≈ ? ₽')
    pair(cv, t, L, R, 0.1, E.SPIN - 0.1, cy=520, s0=1.05, rp=rp)
    if t >= E.HOOK_PRICE + 0.6:
        ps = fx.spring(fx.clamp01((t - E.HOOK_PRICE - 0.6) / 0.6))
        put(cv, fx.solid_pill(f"×{R['rub'] / L['rub']:.1f}".replace('.', ','), WINE, 40), 830, 340, 0.6 + 0.4 * ps,
            1 - appear(t, E.SPIN - 0.4, 0.3))


# ---- 3. в семь раз: три пары
X7G = ['Top Hat', 'Big Year', 'Snow Globe']


def scene_x7(cv, t):
    if not (E.X7 - 0.1 <= t < E.PLAYER + 0.3):
        return
    out = appear(t, E.PLAYER - 0.3, 0.3)
    for j, g in enumerate(X7G):
        L, R = lot(g, 'floor'), lot(g, 'black_floor')
        tj = E.X7 + 0.3 + 0.35 * j
        a = appear(t, tj, 0.3) * (1 - out)
        if a <= 0:
            continue
        y = 340 + j * 205
        s = 0.5 * (0.6 + 0.4 * pop_in(t, tj))
        for side, c in enumerate((L, R)):
            x = 150 + side * 390
            put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, y + 8, s, a)
            put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - tj), x, y, s, a)
            put(cv, text(c['gift'], 20, 'Heavy'), x, y - 92, 1.0, a)
            put(cv, text(rub(c['rub']), 34, 'Heavy', WINE if side else MUTED), x + 180, y, 1.0, a)
        put(cv, fx.solid_pill(f"×{R['ton'] / L['ton']:.0f}", WINE, 28), 965, y, 1.0, a * appear(t, tj + 0.3, 0.3))
    if t >= E.X7_BADGE:
        ps = fx.spring(fx.clamp01((t - E.X7_BADGE) / 0.6))
        put(cv, utext('в среднем ×7', 44, 'ExtraBold', WINE), 540, 950, 0.6 + 0.4 * ps, 1 - out)


# ---- 4. дешевле, чем проигрыватель
def scene_player(cv, t):
    if not (E.PLAYER - 0.1 <= t < E.LOCKET + 0.3):
        return
    L, R = lot('Whip Cupcake', 'black_floor'), lot('Record Player', 'floor')
    pair(cv, t, L, R, E.PLAYER + 0.1, E.LOCKET, cy=520, s0=1.0, rcol=MUTED)
    if t >= E.PLAYER_HIT:
        a = appear(t, E.PLAYER_HIT, 0.25) * (1 - appear(t, E.LOCKET - 0.3, 0.3))
        put(cv, text('>', 90, 'Heavy', WINE), 540, 520, 0.7 + 0.3 * pop_in(t, E.PLAYER_HIT), a)


# ---- 5. медальон за 17 млн
def scene_locket(cv, t):
    if not (E.LOCKET - 0.1 <= t < E.RARITY + 0.3):
        return
    L, R = lot('Heart Locket', 'floor'), lot('Heart Locket', 'black_floor')
    k = fx.clamp01((t - E.LOCKET_HIT) / 0.9)
    rp = '≈ ? ₽' if k <= 0 else ('≈ ' + f"{(L['rub'] + (R['rub'] - L['rub']) * ease(k)) / 1e6:.1f}".replace('.', ',') + ' млн ₽')
    pair(cv, t, L, R, E.LOCKET + 0.1, E.RARITY, cy=520, s0=1.0, rp=rp)
    if t >= E.LOCKET_HIT + 0.9:
        a = 1 - appear(t, E.RARITY - 0.3, 0.3)
        put(cv, fx.solid_pill('выставлен на Fragment', INK, 24), 800, 880, 1.0, a)


# ---- 6. редкость: Black = Burgundy = Copper = 1,5 %
def scene_rarity(cv, t):
    if not (E.RARITY - 0.1 <= t < E.TEASE + 0.3):
        return
    out = appear(t, E.TEASE - 0.3, 0.3)
    m = lot('Whip Cupcake', 'black_floor')
    for j, bd in enumerate(('Black', 'Burgundy', 'Copper')):
        tj = E.RARITY + 0.3 + 0.3 * j
        a = appear(t, tj, 0.3) * (1 - out)
        if a <= 0:
            continue
        x = 190 + 350 * j
        s = 0.8 * (0.6 + 0.4 * pop_in(t, tj))
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, 500 + 10, s, a)
        put(cv, gift_tile('Whip Cupcake', m['model'], bd, TILE, t - tj), x, 500, s, a)
        put(cv, text('Whip Cupcake', 26, 'Heavy'), x, 500 - 150 * s / 0.8 * 0.8 - 30, 1.0, a)
        put(cv, text(bd, 30, 'Heavy'), x, 650, 1.0, a)
        hl = appear(t, E.RARITY_SAME, 0.3)
        put(cv, utext('1,5%', 40, 'ExtraBold', WINE if hl > 0.5 else MUTED), x, 705, 1.0 + 0.1 * hl * beat_pulse(t, 8), a)
    if t >= E.RARITY_SAME + 0.5:
        put(cv, utext('= = =', 34, 'ExtraBold', MUTED), 540, 770, 1.0, appear(t, E.RARITY_SAME + 0.5, 0.3) * (1 - out))


# ---- 7. тизер: «Так почему?»
@functools.lru_cache(None)
def qmark_tile():
    im = fx.rounded(TILE, TILE, 46, (20, 16, 30, 255), (120, 40, 70, 255), 4).copy()
    q = text('?', 160, 'Heavy', (220, 200, 230))
    im.alpha_composite(q, ((TILE - q.width) // 2, (TILE - q.height) // 2))
    return im


def scene_tease(cv, t):
    if not (E.TEASE - 0.1 <= t < AD_STOP + 0.6):
        return
    a = appear(t, E.TEASE + 0.1, 0.3) * (1 - appear(t, AD_STOP + 0.2, 0.3))
    put(cv, qmark_tile(), 540, 520, 1.1 * (1 + 0.04 * math.sin(t * 6)), a, math.sin(t * 3) * 0.05)


# ---- 8. спрос: карта, машина, смокинг
def icon_card(d, cx, cy, s):
    d.rounded_rectangle([cx - 130 * s, cy - 82 * s, cx + 130 * s, cy + 82 * s], int(18 * s), fill=(20, 18, 28, 255))
    d.rounded_rectangle([cx - 100 * s, cy - 35 * s, cx - 55 * s, cy + 0 * s], int(6 * s), fill=GOLD + (255,))
    for i in range(4):
        d.rounded_rectangle([cx - 100 * s + i * 52 * s, cy + 35 * s, cx - 62 * s + i * 52 * s, cy + 47 * s], int(3 * s), fill=(150, 150, 160, 255))


def icon_car(d, cx, cy, s):
    body = [(-150, 30), (-140, -5), (-80, -20), (-45, -60), (55, -60), (95, -20), (150, -8), (155, 30)]
    d.polygon([(cx + x * s, cy + y * s) for x, y in body], fill=(20, 18, 28, 255))
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(-35, -50), (5, -50), (5, -22), (-65, -22)]], fill=(90, 90, 110, 255))
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(15, -50), (48, -50), (78, -22), (15, -22)]], fill=(90, 90, 110, 255))
    for wx in (-85, 90):
        d.ellipse([cx + (wx - 30) * s, cy + 2 * s, cx + (wx + 30) * s, cy + 62 * s], fill=(40, 38, 48, 255), outline=(150, 150, 160, 255), width=int(6 * s))


def icon_tux(d, cx, cy, s):
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(-110, 110), (-90, -70), (-35, -100), (0, -40), (35, -100), (90, -70), (110, 110)]], fill=(20, 18, 28, 255))
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(-35, -100), (0, -40), (35, -100), (22, 110), (-22, 110)]], fill=(245, 245, 248, 255))
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(-34, -70), (0, -55), (-34, -40)]], fill=WINE + (255,))
    d.polygon([(cx + x * s, cy + y * s) for x, y in [(34, -70), (0, -55), (34, -40)]], fill=WINE + (255,))


def scene_demand(cv, t):
    if not (AD_STOP <= t < E.GLOW + 0.3):
        return
    out = appear(t, E.GLOW - 0.3, 0.3)
    a0 = appear(t, E.DEMAND + 0.1, 0.3) * (1 - out)
    put(cv, utext('спрос', 60, 'ExtraBold', WINE), 540, 300, 0.8 + 0.2 * pop_in(t, E.DEMAND + 0.1), a0)
    for j, (name, lab) in enumerate((('card', 'карты'), ('car', 'машины'), ('tux', 'смокинги'))):
        tj = E.ICONS[j]
        a = appear(t, tj, 0.25) * (1 - out)
        if a <= 0:
            continue
        x = 190 + 350 * j
        s = pop_in(t, tj) * (1 + 0.015 * beat_pulse(t, 8))
        put(cv, prop_img(name), x, 560, s, a)
        put(cv, text(lab, 32, 'Heavy'), x, 730, 1.0, a)


@functools.lru_cache(None)
def prop_img(name):
    """Фото-предметы для «спроса» (ChatGPT, хромакей: input/props/luxury_sheet.png → card/car/tux.png)."""
    im = Image.open(HERE / 'input' / 'props' / f'{name}.png').convert('RGBA')
    bw, bh = {'card': (270, 230), 'car': (345, 260), 'tux': (250, 280)}[name]
    k = min(bw / im.width, bh / im.height)
    return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)


# ---- 9. светится в тёмной теме
@functools.lru_cache(None)
def phone_frame():
    im = Image.new('RGBA', (440, 560), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 439, 559], 54, fill=(14, 14, 22, 255), outline=(60, 60, 75, 255), width=6)
    d.rounded_rectangle([170, 18, 270, 34], 8, fill=(40, 40, 52, 255))
    return im


def scene_glow(cv, t):
    if not (E.GLOW - 0.1 <= t < E.PLAIN + 0.3):
        return
    out = appear(t, E.PLAIN - 0.3, 0.3)
    c = lot('Neko Helmet', 'black_floor')
    a = appear(t, E.GLOW + 0.1, 0.3) * (1 - out)
    ph = appear(t, E.GLOW_PHONE, 0.4)
    s = (1.15 - 0.42 * ph) * (1 + 0.02 * beat_pulse(t, 8))
    if ph > 0:
        put(cv, phone_frame(), 540, 500, 0.72 + 0.08 * ph, a * ph)
    glow = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(t * 4))
    put(cv, tinted_glow((255, 210, 120)), 540, 510, 1.6 * s, a * glow)
    put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - E.GLOW), 540, 510, s, a)
    put(cv, text(c['gift'], 30, 'Heavy', WHITE if ph > 0.5 else INK), 540, 510 - 150 * s - 28, 1.0, a)


# ---- 10. обычный фон тускнеет
def scene_plain(cv, t):
    if not (E.PLAIN - 0.1 <= t < E.PRICE + 0.3):
        return
    out = appear(t, E.PRICE - 0.3, 0.3)
    c = lot('Neko Helmet', 'floor')
    a = appear(t, E.PLAIN + 0.1, 0.3) * (1 - out)
    dim = appear(t, E.PLAIN + 1.0, 0.8)
    tile = gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - E.PLAIN)
    if dim > 0:
        g = ImageOps.grayscale(tile.convert('RGB')).convert('RGBA')
        g.putalpha(tile.getchannel('A'))
        tile = Image.blend(tile, g, dim * 0.85)
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), 540, 550, 1.0, a * (1 - 0.6 * dim))
    put(cv, tile, 540, 540, 1.0 - 0.08 * dim, a * (1 - 0.35 * dim))
    put(cv, text(c['gift'], 30, 'Heavy'), 540, 540 - 150 - 30, 1.0, a * (1 - 0.35 * dim))
    put(cv, text('просто фон…', 40, 'Heavy', MUTED), 540, 760, 1.0, a * dim)


# ---- 11. цена растёт
def scene_price(cv, t):
    if not (E.PRICE - 0.1 <= t < E.OUTRO + 0.3):
        return
    out = appear(t, E.OUTRO - 0.3, 0.3)
    a = appear(t, E.PRICE + 0.1, 0.3) * (1 - out)
    k = ease((t - E.PRICE - 0.3) / 3.2)
    def draw(d, mp, S):
        x0, y0 = mp(200, 760)
        x1, y1 = mp(880, 330)
        d.line([x0, y0, x1, y0], fill=(200, 194, 215, 255), width=int(4 * S))
        d.line([x0, y0, x0, y1], fill=(200, 194, 215, 255), width=int(4 * S))
        pts = [(0, 0.05), (0.15, 0.12), (0.3, 0.1), (0.45, 0.3), (0.6, 0.38), (0.75, 0.62), (0.9, 0.8), (1.0, 0.95)]
        P = [mp(200 + 680 * u, 760 - 430 * v) for u, v in pts if u <= k]
        if len(P) > 1:
            d.line(P, fill=WINE + (255,), width=int(10 * S), joint='curve')
            X, Y = P[-1]
            r = 14 * S
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=WINE + (255,))
    fx.over(cv, fx.draw_rgba((150, 290, 930, 800), draw), a)
    if t >= E.PRICE_UP:
        put(cv, utext('цена ↑', 46, 'ExtraBold', WINE), 760, 380, 0.7 + 0.3 * pop_in(t, E.PRICE_UP), a)


# ---- 12. люкс или минимум
def scene_outro(cv, t):
    """«роскошный люкс» — дорогой подарок на чёрном (Electric Skull, 26 тыс. ₽);
    «базовый минимум» — дешёвый на самом невзрачном зелёном (Snow Globe, Ranger Green, 701 ₽)."""
    if t < E.OUTRO - 0.1:
        return
    L, R = lot('Electric Skull', 'black_floor'), lot('Snow Globe', 'floor')
    for j, (c, lab, tj) in enumerate(((L, 'роскошный люкс', E.OUTRO_LUX), (R, 'базовый минимум', E.OUTRO_MIN))):
        a = appear(t, tj, 0.3)
        if a <= 0:
            continue
        x = 540 + (j - 0.5) * 520
        s = 0.95 * (0.6 + 0.4 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
        if j == 0:                                  # люкс слегка сияет
            put(cv, tinted_glow((255, 210, 120)), x, 500, 1.3 * s, a * (0.3 + 0.15 * math.sin(t * 4)))
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), x, 500 + 14, s, a)
        put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - tj), x, 500, s, a)
        put(cv, text(c['gift'], 28, 'Heavy'), x, 500 - 150 * s - 28, 1.0, a)
        put(cv, upill(lab, WINE if j == 0 else (226, 220, 238), 24, WHITE if j == 0 else INK), x, 690, 1.0, a)
        put(cv, text(rub(c['rub']), 36, 'Heavy', WINE if j == 0 else MUTED), x, 745, 1.0, a)
    k = appear(t, E.OUTRO_PILL, 0.3)
    put(cv, fx.solid_pill('Пиши в комментариях', ACCENT, 34), 540, 232, 0.8 + 0.2 * k, k)


# ------------------------------------------------------------------ субтитры
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
SUB_Y = 1596


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
    goth = t >= E.SPIN + SPIN_DUR * 0.6
    acc = WINE if goth else ACCENT
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = acc if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (INK if on else (150, 144, 170))
        parts.append(((' ' if j else '') + _disp(w[0]).upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    pop = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    border = (232, 210, 218) if goth else (236, 228, 248)
    put(cv, fx.rounded(pw, 84, 30, (255, 255, 255, 230), border + (255,), 3), 540, SUB_Y, 0.85 + 0.15 * pop, 1.0)
    put(cv, im, 540, SUB_Y, sc * (0.85 + 0.15 * pop), 1.0)


# ------------------------------------------------------------------ боковые панели (заполняют кадр)
def side_panels(cv, t):
    def txt_panel(x, t0, t1, top, big, bot, big_col=WINE):
        a = window_a(t, t0, t1, 0.3)
        if a <= 0:
            return
        s = put_panel(cv, x, SIDE_Y, a, t0, t)
        put(cv, utext(top, 20, 'SemiBold', MUTED), x, SIDE_Y - 105, s, a)
        im = utext(big, 46, 'ExtraBold', big_col)
        put(cv, im, x, SIDE_Y - 10, s * min(1.0, 230 / im.width), a)
        put(cv, utext(bot, 20, 'SemiBold', MUTED), x, SIDE_Y + 85, s, a)
    n = len(BLK['gifts'])
    txt_panel(LX, E.X7 + 0.6, E.PLAYER, 'коллекций', '121', 'с чёрным фоном')
    txt_panel(RX, E.X7 + 1.0, E.PLAYER, 'чёрный дороже', '×7', 'в среднем')
    txt_panel(LX, E.LOCKET + 0.6, E.RARITY, 'самый дешёвый', '149 тыс', 'Heart Locket')
    txt_panel(RX, E.LOCKET_HIT + 0.9, E.RARITY, 'на чёрном', '17,5 млн', 'цена продавца')
    txt_panel(LX, E.RARITY + 0.6, E.TEASE, 'шанс Black', '1,5%', 'как у других')
    txt_panel(RX, E.RARITY_SAME, E.TEASE, 'а цена', '×5,6', 'Whip Cupcake')
    # хук: обычный против чёрного
    txt_panel(LX, 0.9, E.SPIN - 0.3, 'обычный фон', '438 ₽', 'Whip Cupcake', MUTED)
    txt_panel(RX, E.HOOK_PRICE + 0.4, E.SPIN - 0.3, 'чёрный фон', '×5,6', 'дороже')
    # дороже проигрывателя
    txt_panel(LX, E.PLAYER + 0.5, E.LOCKET, 'самый дешёвый', 'на Black', 'из 121 коллекции')
    txt_panel(RX, E.PLAYER_HIT, E.LOCKET, 'дороже', '×1,9', 'проигрывателя')
    # тизер — загадка
    txt_panel(LX, E.TEASE + 0.3, AD_STOP + 0.2, 'не редкость', '?', 'тогда что')
    txt_panel(RX, E.TEASE + 0.6, AD_STOP + 0.2, 'платят', '×7', 'за что?')
    # спрос
    txt_panel(LX, E.DEMAND + 0.5, E.GLOW, 'чёрный', 'люкс', 'цвет статуса')
    txt_panel(RX, E.ICONS[1], E.GLOW, 'хотят', 'все', 'спрос ↑')
    # светится
    txt_panel(LX, E.GLOW + 0.4, E.PLAIN, 'на чёрном', 'ярче', 'контраст')
    txt_panel(RX, E.GLOW_PHONE, E.PLAIN, 'тёмная тема', 'телеграм', 'фон сливается')
    # обычный фон: тот же Neko Helmet
    txt_panel(LX, E.PLAIN + 0.4, E.PRICE, 'обычный фон', '3 940 ₽', 'Neko Helmet', MUTED)
    txt_panel(RX, E.PLAIN + 1.0, E.PRICE, 'на чёрном', '×10', '38 528 ₽')
    # финал
    txt_panel(LX, E.OUTRO_MIN + 0.3, DUR + 1, 'разница', '×37', 'люкс / минимум')
    txt_panel(RX, E.OUTRO_PILL, DUR + 1, 'а ты?', 'люкс', 'или минимум')
    txt_panel(LX, E.PRICE + 0.4, E.OUTRO, 'хотят все', 'спрос ↑', '')
    txt_panel(RX, E.PRICE_UP, E.OUTRO, 'продавцы', 'цена ↑', 'не снижают')


# ------------------------------------------------------------------ реклама: мини-игра «Угадай цену»
QUIZ = lot('Neko Helmet', 'black_floor')
QUIZ_OPTS = ['≈ 3 900 ₽', '≈ 12 000 ₽', rub(QUIZ['rub'])]


@functools.lru_cache(None)
def ad_panel():
    im = Image.new('RGBA', (W, 662), (0, 0, 0, 0))
    m = Image.new('L', (W, 662), 0)
    ImageDraw.Draw(m).rounded_rectangle([30, 30, W - 30, 650], 48, fill=240)
    im.paste((252, 250, 255, 255), (0, 0), m)
    return im


def ad_overlay(c, t):
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    fx.over(cv, (ad_panel(), 0, 8), a)
    put(cv, text('Угадай цену', 52, 'Heavy'), 540, 120, 1.0, a)
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), 300, 380 + 10, 0.85, a)
    put(cv, gift_tile(QUIZ['gift'], QUIZ['model'], QUIZ['backdrop'], TILE, t), 300, 380, 0.85 * (1 + 0.03 * math.sin(t * 4)), a)
    put(cv, text(QUIZ['gift'], 28, 'Heavy'), 300, 230, 1.0, a)
    for j, o in enumerate(QUIZ_OPTS):
        put(cv, upill(f'{"ABC"[j]}  {o}', (236, 230, 246), 32, INK), 740, 280 + j * 105, 1.0 + 0.03 * math.sin(t * 5 + j), a)
    left = max(0, math.ceil(BR.B - max(0.0, bt)))
    put(cv, fx.solid_pill(f'ответ через {left}' if left > 0 else 'ответ!', WINE, 30), 540, 600, 1.0, a)
    return cv[..., :3]


def quiz_answer(cv, t):
    """Сразу после рекламы — правильный вариант подсвечивается (над сценой, 2,2 с)."""
    k = t - (AD_STOP + 0.05)
    if not 0 <= k < 2.4:
        return
    a = min(1.0, k * 5) * (1 - fx.clamp01((k - 2.0) / 0.4))
    put(cv, fx.solid_pill(f'Ответ: C  {rub(QUIZ["rub"])}', WINE, 32), 540, 730, 0.8 + 0.2 * pop_in(t, AD_STOP + 0.05), a)


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    headline(cv, t)
    scene_hook(cv, t)
    scene_x7(cv, t)
    scene_player(cv, t)
    scene_locket(cv, t)
    scene_rarity(cv, t)
    scene_tease(cv, t)
    scene_demand(cv, t)
    scene_glow(cv, t)
    scene_plain(cv, t)
    scene_price(cv, t)
    scene_outro(cv, t)
    side_panels(cv, t)
    wind(cv, t, False)
    draw_mita(cv, t)
    wind(cv, t, True)
    quiz_answer(cv, t)
    subtitles(cv, t)
    return np.clip(cv[..., :3], 0, 255).astype(np.uint8)


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
    frames.cli(out_frame, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
