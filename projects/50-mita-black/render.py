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
import anim
import cv2
import mita_v4 as M3
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
PANEL_W, PANEL_H = 240, 300
SIDE_Y = 1150
LX, RX = 152, 928


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
POSES = [  # (с какого времени, поза, вспышка) — только для кружения (старые кадры 49/50)
    (0.0, 'normal_sly', False),
    (E.SPIN + SPIN_DUR, 'goth_explain', False),
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


def _draw_mita_old(cv, t):
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


def old_draw(cv, t, alpha=1.0):
    if alpha >= 0.999:
        _draw_mita_old(cv, t)
        return
    if alpha <= 0.002:
        return
    base = cv.copy()
    _draw_mita_old(cv, t)
    cv[:] = base + (cv - base) * alpha


def draw_mita(cv, t):
    M3.draw_mita(cv, t, old_draw)


@functools.lru_cache(None)
def prop_cap(name):
    return Image.open(HERE / 'input' / 'props' / f'{name}.png').convert('RGBA')


def breathe(t):
    return anim.breathe(t)


# ------------------------------------------------------------------ 3D-комнаты (ChatGPT) с параллаксом
ROOM_FLOOR = {'showroom': 1170, 'bedroom': 1540}       # линия «стена/пол» на экране (для двух слоёв параллакса)


@functools.lru_cache(None)
def room_img(name):
    im = Image.open(HERE / 'input' / 'rooms' / f'{name}.png').convert('RGB')
    k = 1.36 * H / im.height                              # с запасом под движение камеры и параллакс
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    return np.asarray(im, np.float32)


def room_bg(name, t, pan, t0):
    """Комната: стена и пол сдвигаются с разной скоростью (глубина), лёгкий наезд, пылинки в свете."""
    src = room_img(name)
    sh, sw = src.shape[:2]
    z = 1.0 + 0.05 * ease((t - t0) / 6.0)
    out = np.empty((H, W, 3), np.float32)
    fl = ROOM_FLOOR[name]
    for layer, k in (('wall', 0.45), ('floor', 1.0)):
        s_ = (H / sh) * 1.12 * z
        ox = (sw * s_ - W) / 2 + pan * k
        oy = (sh * s_ - H) / 2 - 20 * k
        M = np.float32([[s_, 0, -ox], [0, s_, -oy]])
        img = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        if layer == 'wall':
            out[:] = img
        else:
            yy = np.clip((np.arange(H) - (fl - 60)) / 120, 0, 1)[:, None, None]
            out[:] = out * (1 - yy) + img * yy
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = out * 0.92
    cv[..., 3] = 255
    def motes(d, mp, S):
        rng = np.random.default_rng(5 if name == 'showroom' else 9)
        for j in range(46):
            x0, y0, sp = rng.uniform(0, W), rng.uniform(150, 1300), rng.uniform(6, 22)
            x = x0 + math.sin(t * 0.5 + j) * 20 + pan * 0.7
            y = (y0 - t * sp) % 1300 + 150
            tw = 0.5 + 0.5 * math.sin(t * 2.0 + j)
            col = (255, 220, 170) if name == 'showroom' else (255, 190, 230)
            X, Y = mp(x, y)
            r = (1.6 + 2.2 * tw) * S
            d.ellipse([X - r, Y - r, X + r, Y + r], fill=col + (int(70 + 110 * tw),))
    fx.over(cv, fx.draw_rgba((0, 0, W, H), motes), 1.0, add=True)
    return cv


def creepy_bg(t):
    cv = np.empty((H, W, 4), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.45) / H) ** 2)
    k = np.clip(1 - r * 1.6, 0, 1)[..., None]
    fl = 0.85 + 0.15 * (math.sin(t * 37) > 0.6)
    cv[..., :3] = (np.array([10, 4, 10], np.float32) * (1 - k) + np.array([70, 10, 24], np.float32) * k) * fl
    cv[..., 3] = 255
    return cv


# ------------------------------------------------------------------ детали фона по сценам (v4, умеренно)
@functools.lru_cache(None)
def bokeh_tile(gift, bd):
    c = [v for k, v in LOTS.items() if k.startswith(gift + '|')][0]
    im = gift_tile(gift, c['model'], bd, 160, 0.0)
    return im.filter(ImageFilter.GaussianBlur(7))


@functools.lru_cache(None)
def spot_glow():
    return fx.radial(256, (255, 214, 150), 1.4, 1.0).resize((360, 110))


@functools.lru_cache(None)
def soft_glow(c, w, h):
    return fx.radial(256, c, 1.5, 1.0).resize((w, h))


def window(t, t0, t1, d=0.4):
    return appear(t, t0, d) * (1 - appear(t, t1 - d, d))


FLOAT_GIFTS = ['Electric Skull', 'Neko Helmet', 'Top Hat', 'Heart Locket', 'Snow Globe', 'Big Year', 'Whip Cupcake',
               'Bonded Ring', 'Mad Pumpkin']


@functools.lru_cache(None)
def float_lot(g):
    k = f'{g}|black_floor'
    if k in LOTS:
        c = LOTS[k]
        return c['gift'], c['model'], c['backdrop']
    if g == 'Mad Pumpkin':
        return 'Mad Pumpkin', 'Red Demon', 'Black'
    return None


def side_floaters(cv, t, sc):
    """Парящие NFT на чёрном по краям (над боковыми панелями) — заполняют пустые бока, медленно плывут и покачиваются."""
    if sc in ('creepy', 'show', 'spin'):
        return
    idx = [n for n, _ in M3.SCENES].index(sc) if sc in [n for n, _ in M3.SCENES] else 0
    t0 = dict(M3.SCENES)[sc]
    for side, x in ((0, LX), (1, RX)):
        if (sc == 'hook' and side == 1 and t < 2.7) or (sc == 'hang' and side == 0):
            continue
        g = FLOAT_GIFTS[(idx * 2 + side) % len(FLOAT_GIFTS)]
        c = float_lot(g)
        if not c:
            continue
        a = appear(t, t0 + 0.2 + 0.25 * side, 0.45)
        y = (560 if sc == 'pumpkin' else 885) + 18 * math.sin(t * 1.1 + side * 2) - (40 if side else 0)
        s_ = 0.52 * (0.85 + 0.15 * pop_in(t, t0 + 0.2 + 0.25 * side))
        rot = 0.08 * math.sin(t * 0.8 + side)
        put(cv, tinted_glow((255, 215, 150)), x, y, 0.7, 0.28 * a)
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.4), x, y + 10, s_, 0.7 * a)
        put(cv, gift_tile(c[0], c[1], c[2], TILE, t), x, y, s_, a, rot)


def deco(cv, t, sc):
    goth = appear(t, M3.SPIN_END - 0.3, 0.6)
    # подиум: мягкий круг света под Митой
    if sc in ('card', 'jump', 'rare', 'show', 'phone', 'kick', 'two', 'hook'):
        put(cv, soft_glow((200, 170, 230) if goth < 0.5 else (230, 170, 190), 620, 120), 540, 1548, 1.0, 0.45)
    # готика: лепестки роз и тонкие узоры в углах
    if goth > 0:
        def petals(d, mp, S):
            rng = np.random.default_rng(31)
            for j in range(12):
                x0, sp = rng.uniform(0, W), rng.uniform(40, 80)
                y = (rng.uniform(0, H) + t * sp) % (H + 60) - 30
                x = x0 + math.sin(t * 0.8 + j) * 40
                X, Y = mp(x, y)
                r = rng.uniform(7, 12) * S
                a2 = t * 1.5 + j
                pts = [(X + math.cos(a2) * r * 1.5, Y + math.sin(a2) * r * 1.5), (X + math.cos(a2 + 1.6) * r * 0.6, Y + math.sin(a2 + 1.6) * r * 0.6),
                       (X - math.cos(a2) * r * 1.5, Y - math.sin(a2) * r * 1.5), (X - math.cos(a2 + 1.6) * r * 0.6, Y - math.sin(a2 + 1.6) * r * 0.6)]
                d.polygon(pts, fill=WINE + (int(70 * goth),))
            for sx_ in (1, -1):                                   # узоры в верхних углах
                cx0 = 0 if sx_ > 0 else W
                for k in range(3):
                    r_ = (140 + 60 * k) * S
                    X, Y = mp(cx0, 0)
                    d.arc([X - r_, Y - r_, X + r_, Y + r_], 0 if sx_ > 0 else 90, 90 if sx_ > 0 else 180,
                          fill=WINE + (int(45 * goth),), width=max(1, int(2 * S)))
        fx.over(cv, fx.draw_rgba((0, 0, W, H), petals))
    # тыква: луна и летучие мыши
    a = window(t, E.PUMPKIN - 0.1, E.LOCKET + 0.1)
    if a > 0:
        put(cv, soft_glow((255, 236, 170), 420, 420), 830, 660, 1.0, 0.35 * a)
        def bats(d, mp, S):
            for j in range(5):
                u = ((t - E.PUMPKIN) * 0.12 + j * 0.21) % 1.0
                x = -80 + u * (W + 160)
                y = 420 + 160 * math.sin(j * 2.1) + 30 * math.sin(t * 2 + j)
                X, Y = mp(x, y)
                f = math.sin(t * 14 + j * 2)
                r = (18 + 4 * j) * S
                d.polygon([(X, Y), (X - r, Y - r * 0.5 * f - 4 * S), (X - r * 0.5, Y), (X - r * 1.1, Y + r * 0.2),
                           (X, Y + r * 0.25), (X + r * 1.1, Y + r * 0.2), (X + r * 0.5, Y), (X + r, Y - r * 0.5 * f - 4 * S)],
                          fill=(50, 26, 46, int(150 * a)))
        fx.over(cv, fx.draw_rgba((0, 0, W, H), bats))
    # медальон: всплывающие сердечки
    a = window(t, E.LOCKET, E.CREEPY)
    if a > 0:
        def hearts(d, mp, S):
            rng = np.random.default_rng(7)
            for j in range(10):
                x, sp = rng.uniform(80, W - 80), rng.uniform(50, 110)
                y = H - ((t - E.LOCKET) * sp + rng.uniform(0, H)) % H
                X, Y = mp(x + 20 * math.sin(t + j), y)
                r = rng.uniform(8, 14) * S
                c = ((236, 72, 120) if j % 2 else WINE) + (int(80 * a),)
                d.ellipse([X - r, Y - r, X, Y], fill=c)
                d.ellipse([X, Y - r, X + r, Y], fill=c)
                d.polygon([(X - r, Y - r * 0.5), (X + r, Y - r * 0.5), (X, Y + r * 0.9)], fill=c)
        fx.over(cv, fx.draw_rgba((0, 0, W, H), hearts))
    # карусель: свет под кольцом
    a = window(t, E.CREEPY_END, E.TEASE)
    if a > 0:
        put(cv, soft_glow((255, 200, 220), 900, 240), 540, 560, 1.0, 0.5 * a)
    # «Так почему?»: бледные знаки вопроса
    a = window(t, E.TEASE, AD_STOP + 0.1, 0.3)
    if a > 0:
        for j in range(5):
            x = 120 + j * 210 + 30 * math.sin(t + j)
            y = 900 + 300 * math.sin(j * 1.7) - ((t - E.TEASE) * 40) % 200
            put(cv, text('?', 70 + 15 * (j % 3), 'Heavy', (190, 170, 210)), x, y, 1.0, 0.35 * a, 0.2 * math.sin(t + j))
    # спрос: золотые искры и тонкие линии
    a = window(t, AD_STOP + 0.1, E.GLOW)
    if a > 0:
        def gold(d, mp, S):
            for j in range(14):
                u = (t * 0.07 + j * 0.071) % 1.0
                X, Y = mp(60 + (j * 151) % 960, H * (1 - u))
                tw = 0.5 + 0.5 * math.sin(t * 3 + j)
                fx.sparkle(d, X, Y, (6 + 8 * tw) * S, GOLD + (int(120 * a * tw),))
            for k in range(2):
                X0, Y0 = mp(-100, 300 + 700 * k)
                X1, Y1 = mp(W + 100, 700 + 700 * k)
                d.line([X0, Y0, X1, Y1], fill=(220, 180, 90, int(50 * a)), width=max(1, int(2 * S)))
        fx.over(cv, fx.draw_rgba((0, 0, W, H), gold))
    # телефон: фон чуть темнеет, вокруг фиолетовые искры
    a = window(t, E.GLOW, E.PLAIN)
    if a > 0:
        cv[..., :3] *= 1 - 0.22 * a
        put(cv, soft_glow((190, 120, 255), 700, 700), 540, 520, 1.0, 0.35 * a)
    # обычный фон: всё ненадолго блекнет
    a = window(t, E.PLAIN + 0.3, E.PRICE, 0.5)
    if a > 0:
        g = cv[..., :3].mean(-1, keepdims=True)
        cv[..., :3] = cv[..., :3] * (1 - 0.6 * a) + g * 0.6 * a
    # график: бледная клетка и стрелки вверх
    a = window(t, E.PRICE, E.OUTRO)
    if a > 0:
        def grid(d, mp, S):
            for k in range(0, W, 90):
                X, _ = mp(k, 0)
                d.line([X, mp(0, 280)[1], X, mp(0, 1480)[1]], fill=(170, 160, 200, int(40 * a)), width=1)
            for k in range(280, 1480, 90):
                _, Y = mp(0, k)
                d.line([mp(60, 0)[0], Y, mp(1020, 0)[0], Y], fill=(170, 160, 200, int(40 * a)), width=1)
        fx.over(cv, fx.draw_rgba((0, 0, W, H), grid))
        for j in range(4):
            y = 1400 - ((t - E.PRICE) * 120 + j * 300) % 1100
            put(cv, text('↑', 60, 'Heavy', (200, 120, 150)), 900 + 40 * (j % 2), y, 1.0, 0.3 * a)
    # финал: слева тёплое золото (люкс), справа блёклая зелень (минимум)
    a = appear(t, E.OUTRO, 0.5)
    if a > 0:
        put(cv, soft_glow((255, 200, 110), 700, 900), 260, 700, 1.0, 0.35 * a)
        put(cv, soft_glow((150, 190, 140), 700, 900), 820, 700, 1.0, 0.3 * a)


# ------------------------------------------------------------------ background (белый, микродетали)
TINTS = [  # (время, свечение 1, свечение 2) — фон меняет цвет по ходу ролика (как в 49); Мита всё время в чёрном
    (0.0, (120, 70, 200), (220, 90, 160)),
    (E.SPIN + 0.6, (170, 40, 90), (110, 60, 170)),
    (E.PUMPKIN, (240, 110, 60), (190, 40, 70)),
    (E.LOCKET, (236, 72, 140), (170, 60, 200)),
    (E.CREEPY_END, (190, 120, 230), (240, 140, 190)),
    (AD_STOP, (220, 170, 80), (160, 40, 80)),
    (E.GLOW, (150, 90, 255), (90, 60, 200)),
    (E.PLAIN, (170, 170, 180), (130, 160, 140)),
    (E.PRICE, (200, 40, 80), (240, 110, 150)),
    (E.OUTRO, (255, 190, 90), (140, 190, 140)),
]


def tint_at(t):
    c1, c2 = TINTS[0][1], TINTS[0][2]
    for k in range(1, len(TINTS)):
        if t >= TINTS[k][0]:
            m = ease((t - TINTS[k][0]) / 0.6)
            p, q = TINTS[k - 1], TINTS[k]
            c1 = tuple(a * (1 - m) + b * m for a, b in zip(p[1], q[1]))
            c2 = tuple(a * (1 - m) + b * m for a, b in zip(p[2], q[2]))
    return c1, c2


# огромная цифра части истории за Митой (как «1/2/3» в 49) и чипы прогресса под заголовком
STEPS = [('дорого', E.X7, E.CREEPY), ('не редкий', E.CREEPY_END, AD_STOP + 0.1), ('спрос', AD_STOP + 0.1, E.PRICE),
         ('цена', E.PRICE, E.OUTRO)]


def step_at(t):
    for j, (_, t0, t1) in enumerate(STEPS):
        if t0 <= t < t1:
            return j
    return -1


@functools.lru_cache(None)
def big_digit(d):
    return text(d, 760, 'Heavy', (236, 228, 242))


def big_number(cv, t):
    for j, (_, t0, t1) in enumerate(STEPS):
        a = window(t, t0, t1, 0.4)
        if a > 0:
            put(cv, big_digit(str(j + 1)), 540, 1100 + 30 * (1 - a), 1.0 + 0.015 * beat_pulse(t, 6), a)


def progress(cv, t):
    a = window(t, E.X7 - 0.2, E.OUTRO + 0.4, 0.4) * (0 if M3.scene_of(t)[0] == 'creepy' else 1)
    if a <= 0:
        return
    cur = step_at(t)
    xs = (-1.5, -0.5, 0.5, 1.5)
    for j, (lab, _, _) in enumerate(STEPS):
        on = j == cur
        done = cur > j or t >= E.OUTRO
        fill = WINE if on else ((30, 24, 48) if done else (226, 220, 238))
        tc = WHITE if (on or done) else MUTED
        put(cv, fx.solid_pill(lab, fill, 20, tc), 540 + xs[j] * 200, 214, 1.0 + (0.06 * beat_pulse(t, 8) if on else 0), a)


# плывущие подарки по краям (живые модели текущей сцены), как в 49
DRIFT = {   # только NFT на чёрном фоне
    'hook': [('Whip Cupcake', 'black_floor'), ('Top Hat', 'black_floor')], 'spin': [],
    'card': [('Top Hat', 'black_floor'), ('Big Year', 'black_floor')],
    'pumpkin': [('Mad Pumpkin', None), ('Mad Pumpkin', None)], 'jump': [('Heart Locket', 'black_floor'), ('Electric Skull', 'black_floor')],
    'creepy': [], 'rare': [('Whip Cupcake', 'black_floor'), ('Snow Globe', 'black_floor')],
    'show': [('Electric Skull', 'black_floor'), ('Bonded Ring', 'black_floor')],
    'phone': [('Neko Helmet', 'black_floor'), ('Snow Globe', 'black_floor')], 'kick': [('Neko Helmet', 'black_floor'), ('Top Hat', 'black_floor')],
    'hang': [('Top Hat', 'black_floor'), ('Electric Skull', 'black_floor')], 'two': [('Electric Skull', 'black_floor'), ('Bonded Ring', 'black_floor')],
}


@functools.lru_cache(None)
def drift_model(g, k):
    if g == 'Mad Pumpkin':
        return model_path('Mad Pumpkin', 'Red Demon')
    return model_path(g, lot(g, k)['model'])


def drifting_gifts(cv, t, sc):
    for side, (g, k) in enumerate(DRIFT.get(sc, [])):
        for m in range(2):
            ph = (t * 0.045 + m * 0.5 + side * 0.25) % 1.0
            y = 1900 - ph * 1900
            x = (58, 1022)[side] + math.sin(t * 0.9 + m * 2 + side) * 16
            a = 0.42 * min(1.0, ph * 6, (1 - ph) * 6)
            mdl = 'Red Demon' if g == 'Mad Pumpkin' else lot(g, k)['model']
            im = gift_tile(g, mdl, 'Black', 120, t + m)
            put(cv, im, x, y, 1.0, a * 1.4, math.sin(t * 0.7 + m) * 0.15)


# реакции над головой Миты (как в 49)
VIOLET = (120, 90, 230)
REACT = [(E.HOOK_PRICE + 0.5, '!'), (E.PUMP_BLACK + 0.1, '!'), (E.LOCKET_HIT + 0.6, '!'), (E.GACHA[1], '?'),
         (E.TEASE + 0.5, '?'), (E.ICONS[1] + 0.2, 'heart'), (E.GLOW_SHOW + 0.2, 'heart'), (E.KICK + 0.3, 'dots'),
         (E.PRICE_UP + 0.2, '!'), (E.OUTRO_LUX + 0.3, 'heart')]


def reactions(cv, t):
    sc = M3.scene_of(t)[0]
    if sc in ('creepy', 'hang', 'pumpkin'):
        return
    for t0, kind in REACT:
        k = t - t0
        if not 0 <= k < 1.3:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 0.9) / 0.4))
        pop = fx.ease_out_back(fx.clamp01(k / 0.35))
        x, y = 770, 860 - 40 * ease(k / 1.3)
        if kind in ('!', '?'):
            put(cv, fx.solid_pill(kind, ACCENT if kind == '!' else VIOLET, 44), x, y, 0.6 + 0.4 * pop, a, -0.15)
        else:
            def icon(d, mp, S, kind=kind, a=a, pop=pop, x=x, y=y):
                X, Y = mp(x, y)
                r = 26 * S * (0.6 + 0.4 * pop)
                if kind == 'heart':
                    col = (236, 72, 120, int(255 * a))
                    d.ellipse([X - r, Y - r, X, Y], fill=col)
                    d.ellipse([X, Y - r, X + r, Y], fill=col)
                    d.polygon([(X - r, Y - r * 0.45), (X + r, Y - r * 0.45), (X, Y + r * 0.95)], fill=col)
                else:
                    for j in range(3):
                        rr = r * 0.28
                        cxx = X - r + j * r
                        d.ellipse([cxx - rr, Y - rr, cxx + rr, Y + rr], fill=(30, 24, 48, int(200 * a)))
            fx.over(cv, fx.draw_rgba((x - 60, y - 70, x + 60, y + 60), icon))


def lighten(c, k=0.55):
    return tuple(v + (255 - v) * k for v in c)


# мелкая детализация фона: у каждой части свой узор из маленьких значков, едва заметный, медленно плывёт
PATTERNS = [  # (с какого времени, вид)
    (0.0, 'dots'), (E.SPIN + 0.6, 'diamond'), (E.PUMPKIN, 'leaf'), (E.LOCKET, 'heart'), (E.CREEPY_END, 'circle'),
    (E.TEASE, 'qmark'), (AD_STOP, 'crown'), (E.GLOW, 'star'), (E.PLAIN, 'dash'), (E.PRICE, 'arrow'), (E.OUTRO, 'sparkle'),
]


@functools.lru_cache(None)
def pattern_tile(kind, col):
    S = 2
    T = 120
    im = Image.new('RGBA', (T * S, T * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = col + (255,)
    for (cx, cy, r) in ((30, 30, 7), (90, 90, 7)):
        X, Y, R_ = cx * S, cy * S, r * S
        if kind == 'dots':
            d.ellipse([X - 3 * S, Y - 3 * S, X + 3 * S, Y + 3 * S], fill=c)
        elif kind == 'diamond':
            d.polygon([(X, Y - R_), (X + R_ * 0.7, Y), (X, Y + R_), (X - R_ * 0.7, Y)], fill=c)
        elif kind == 'leaf':
            d.ellipse([X - R_, Y - R_ * 0.5, X + R_, Y + R_ * 0.5], fill=c)
        elif kind == 'heart':
            d.ellipse([X - R_, Y - R_, X, Y], fill=c)
            d.ellipse([X, Y - R_, X + R_, Y], fill=c)
            d.polygon([(X - R_, Y - R_ * 0.45), (X + R_, Y - R_ * 0.45), (X, Y + R_ * 0.95)], fill=c)
        elif kind == 'circle':
            d.ellipse([X - R_, Y - R_, X + R_, Y + R_], outline=c, width=2 * S)
        elif kind == 'qmark':
            d.text((X, Y), '?', fill=c, font=ufont('ExtraBold', 18 * S), anchor='mm')
        elif kind == 'crown':
            d.polygon([(X - R_, Y + R_ * 0.6), (X - R_, Y - R_ * 0.4), (X - R_ * 0.5, Y), (X, Y - R_ * 0.8),
                       (X + R_ * 0.5, Y), (X + R_, Y - R_ * 0.4), (X + R_, Y + R_ * 0.6)], fill=c)
        elif kind == 'star':
            fx.sparkle(d, X, Y, R_ * 1.3, c)
        elif kind == 'dash':
            d.line([X - R_, Y, X + R_, Y], fill=c, width=2 * S)
        elif kind == 'arrow':
            d.polygon([(X, Y - R_), (X + R_ * 0.8, Y), (X + R_ * 0.3, Y), (X + R_ * 0.3, Y + R_), (X - R_ * 0.3, Y + R_),
                       (X - R_ * 0.3, Y), (X - R_ * 0.8, Y)], fill=c)
        else:
            fx.sparkle(d, X, Y, R_ * 1.1, c)
    return im.resize((T, T), Image.LANCZOS)


@functools.lru_cache(maxsize=24)
def pattern_layer(kind, col):
    tile = pattern_tile(kind, col)
    big = Image.new('RGBA', (W + 120, H + 120), (0, 0, 0, 0))
    for y in range(0, H + 120, 120):
        for x in range(0, W + 120, 120):
            big.alpha_composite(tile, (x, y))
    return big


def micro_pattern(cv, t):
    c1, _ = tint_at(t)
    col = tuple(int(v * 0.8) for v in c1)
    col = tuple(int(round(v / 24) * 24) for v in col)          # квантуем цвет, чтобы слой кэшировался
    for k, (t0, kind) in enumerate(PATTERNS):
        t1 = PATTERNS[k + 1][0] if k + 1 < len(PATTERNS) else DUR + 5
        a = appear(t, t0, 0.5) * (1 - appear(t, t1, 0.5))
        if a <= 0.01:
            continue
        lay = pattern_layer(kind, col)
        ox = int((t * 6) % 120)
        oy = int((t * 10) % 120)
        fx.over(cv, (lay, -ox, -oy), 0.13 * a)


def background(t):
    sc = M3.scene_of(t)[0]
    if sc == 'creepy':
        return creepy_bg(t)
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = base_bg()
    cv[..., 3] = 255
    c1, c2 = tint_at(t)
    p = beat_pulse(t, 5)
    q = lambda c: tuple(int(v) for v in c)
    # фон преимущественно белый: лёгкий оттенок части истории + мягкие пятна
    cv[..., :3] = cv[..., :3] * 0.94 + np.array(lighten(c1), np.float32) * 0.06
    put(cv, tinted_glow(q(c1)), 230 + 80 * math.sin(t * 0.31), 560 + 60 * math.cos(t * 0.27), 2.8, 0.10 + 0.04 * p)
    put(cv, tinted_glow(q(c2)), 860 + 70 * math.cos(t * 0.23), 1300 + 90 * math.sin(t * 0.29), 3.0, 0.08 + 0.04 * p)
    micro_pattern(cv, t)
    fx.over(cv, fx.draw_rgba((0, 0, W, H), lambda d, mp, S: confetti(d, mp, S, t)))
    big_number(cv, t)
    drifting_gifts(cv, t, sc)
    deco(cv, t, sc)
    return cv


# ------------------------------------------------------------------ заголовок
HEADS = [
    (0.0, E.X7, 'Почему чёрный фон дороже?', None),
    (E.X7, E.PUMPKIN, 'Чёрный — самый дорогой', None),
    (E.PUMPKIN, E.LOCKET, 'Mad Pumpkin на чёрном', None),
    (E.LOCKET, E.CREEPY, '17 миллионов ₽?!', None),
    (E.CREEPY_END, E.TEASE, 'Но он не редкий', None),
    (E.TEASE, AD_STOP + 0.1, 'Так почему?', None),
    (AD_STOP + 0.1, E.GLOW, 'Всё дело в спросе', None),
    (E.GLOW, E.PLAIN, 'Чёрный выделяет', None),
    (E.PLAIN, E.PRICE, 'А обычный фон…', None),
    (E.PRICE, E.OUTRO, 'Спрос — и цена растёт', None),
    (E.OUTRO, DUR + 1, 'Люкс или минимум?', None),
]


def headline(cv, t):
    dark = False
    for t0, t1, s, sub in HEADS:
        a = (1.0 if t0 <= 0 else appear(t, t0, 0.3)) * (1 - appear(t, t1 - 0.25, 0.25))   # v5: заголовок хука с 1-го кадра
        if a <= 0:
            continue
        y = 150 + 10 * (1 - a)
        im = text(s, 52, 'Heavy', WHITE if dark else INK, dark)
        put(cv, im, 540, y, min(1.0, 1000 / im.width), a)
        if sub:
            put(cv, fx.solid_pill(sub, WINE, 24), 540, y + 56, 1.0, a)


# ------------------------------------------------------------------ карточки
TILE = 300


@functools.lru_cache(None)
def qmark():
    """Стилизованный «?» для скрытой карточки: белый, толстая винная обводка, мягкая тень."""
    f = ImageFont.truetype(str(UFONT / 'Unbounded-ExtraBold.ttf'), 190)
    im = Image.new('RGBA', (260, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((130, 158), '?', font=f, anchor='mm', fill=(255, 255, 255, 255), stroke_width=12, stroke_fill=WINE + (255,))
    sh = Image.new('RGBA', im.size, (40, 10, 30, 0))
    sh.putalpha(im.getchannel('A').point(lambda v: int(v * 0.45)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (0, 0))
    out.alpha_composite(im)
    return out


def card(cv, c, cx, cy, s, a, t_anim, price_txt=None, price_col=None, label=True, dim=0.0, blur=0.0):
    if a <= 0:
        return
    a *= 1 - 0.7 * dim
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), cx, cy + 14 * s, s, a)
    tile = gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t_anim)
    if blur > 0.01:                                     # v5: «мыльная» карточка на хуке, раскрывается по реплике
        tile = tile.filter(ImageFilter.GaussianBlur(22 * blur))
    put(cv, tile, cx, cy, s, a)
    if blur > 0.01:
        wob = math.sin(t_anim * 3.1 + cx) * 0.06
        put(cv, qmark(), cx, cy + 6 * math.sin(t_anim * 2.4), s * (0.75 + 0.25 * blur) * (1 + 0.04 * math.sin(t_anim * 5)), a * blur, wob)
    if label:
        put(cv, text(c['gift'], 30, 'Heavy'), cx, cy - (TILE / 2 + 30) * s, s, a)
        bcol = INK if c['backdrop'] == 'Black' else MUTED
        put(cv, multi((('Фон ', MUTED), (c['backdrop'], bcol)), 26, 'Semibold'), cx, cy + (TILE / 2 + 30) * s, s, a)
    pt = price_txt if price_txt is not None else rub(c['rub'])
    put(cv, text(pt, 42, 'Heavy', price_col or (WINE if c['backdrop'] == 'Black' else MUTED)), cx, cy + (TILE / 2 + 76) * s, s, a)


def pop_in(t, t0, d=0.45):
    return fx.ease_out_back(fx.clamp01((t - t0) / d)) if t < t0 + d else 1.0


def pair(cv, t, left, right, t_in, t_out, cy=500, s0=1.0, lp=None, rp=None, gap=520, rcol=None, reveal=None):
    out = appear(t, t_out - 0.3, 0.3) if t_out else 0.0
    for j, c in enumerate((left, right)):
        tj = t_in + 0.25 * j
        a = appear(t, tj, 0.3) * (1 - out)
        s = s0 * (0.6 + 0.4 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
        b = 0.0
        if reveal:                                      # v5: до своего слова карточка размыта и под «?»
            b = 1 - ease((t - reveal[j]) / 0.35)
            if t >= reveal[j]:
                s *= 1 + 0.08 * math.sin(math.pi * min(1.0, (t - reveal[j]) / 0.4))   # лёгкий «пульс» при раскрытии
        card(cv, c, 540 + (j - 0.5) * gap, cy, s, a, t - tj, (lp, rp)[j], rcol if j else None, blur=b)


# ---- 1. хук: кекс обычный vs чёрный
def scene_hook(cv, t):
    if t >= E.X7 + 0.3:
        return
    L, R = lot('Whip Cupcake', 'floor'), lot('Whip Cupcake', 'black_floor')
    k = fx.clamp01((t - E.HOOK_PRICE) / 0.6)
    rp = None if k >= 1 else (rub(int(round((L['rub'] + (R['rub'] - L['rub']) * ease(k)) / 10) * 10)) if k > 0 else '≈ ? ₽')
    pair(cv, t, L, R, -0.8, E.SPIN - 0.1, cy=520, s0=1.05, rp=rp, reveal=(E.REVEAL_L, E.REVEAL_R))   # v5: с 1-го кадра, «мыльные» под «?»
    qa = 1 - appear(t, E.HOOK_PRICE + 0.3, 0.3)
    if qa > 0:                                                            # v5: вопрос-крючок под заголовком
        put(cv, fx.solid_pill('ЗА ЧТО ПЕРЕПЛАТА?', WINE, 34), 540, 238 + 4 * math.sin(t * 3), 1.0 + 0.03 * math.sin(t * 5), qa)


# ---- 3. чёрный — самый дорогой: три пары (без множителей), потом Мита берёт кекс
X7G = ['Top Hat', 'Big Year', 'Snow Globe']


def scene_x7(cv, t):
    if not (E.X7 - 0.1 <= t < E.UFC + 0.3):
        return
    out = appear(t, E.CARD_GRAB - 0.1, 0.35)
    for j, g in enumerate(X7G):
        L, R = lot(g, 'floor'), lot(g, 'black_floor')
        tj = E.X7 + 0.3 + 0.35 * j
        a = appear(t, tj, 0.3) * (1 - out)
        if a <= 0:
            continue
        y = 355 + j * 205
        s = 0.5 * (0.6 + 0.4 * pop_in(t, tj))
        for side, c in enumerate((L, R)):
            x = 170 + side * 470
            put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, y + 8, s, a)
            put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - tj), x, y, s, a)
            put(cv, text(c['gift'], 20, 'Heavy'), x, y - 92, 1.0, a)
            put(cv, text(rub(c['rub']), 34, 'Heavy', WINE if side else MUTED), x + 190, y, 1.0, a)
    # три самых дешёвых NFT на чёрном (Fragment, 16.11): в центре кекс, который Мита держит
    a2 = appear(t, E.CARD_GRAB + 0.15, 0.35) * (1 - appear(t, E.PUMPKIN - 0.35, 0.3))
    if a2 > 0:
        cup = lot('Whip Cupcake', 'black_floor')
        trio = [('Homemade Cake', 'Frosted Mint', 'Black', 2452), (cup['gift'], cup['model'], cup['backdrop'], cup['rub']),
                ('Xmas Stocking', 'Pink Faerie', 'Black', 2452)]
        put(cv, upill('самые дешёвые на чёрном', WINE, 24, WHITE), 540, 292, 0.8 + 0.2 * pop_in(t, E.CARD_GRAB + 0.15), a2)
        for j, (g, m, bd, price) in enumerate(trio):
            tj = E.CARD_GRAB + 0.15 + (0.0 if j == 1 else 0.25)
            aj = a2 * appear(t, tj, 0.3)
            if aj <= 0:
                continue
            x = (200, 540, 880)[j]
            s2 = (0.7 if j == 1 else 0.58) * (0.7 + 0.3 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
            if j == 1:
                put(cv, tinted_glow((255, 210, 140)), x, 480, 1.25 * s2, aj * (0.25 + 0.1 * math.sin(t * 3)))
            put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), x, 480 + 14 * s2, s2, aj)
            put(cv, gift_tile(g, m, bd, TILE, t - tj), x, 480, s2, aj)
            put(cv, text(g, 22, 'Heavy'), x, 480 - 150 * s2 - 22, 1.0, aj)
            put(cv, text(rub(price), 32, 'Heavy', WINE), x, 480 + 150 * s2 + 28, 1.0, aj)


# ---- 4. тыква: Мита сидит на огромной Red Demon; сверху плитка переворачивается (обычная → на чёрном)
PUMP_LO = dict(gift='Mad Pumpkin', model='Pump King', backdrop=None, rub=1313)
PUMP_HI = dict(gift='Mad Pumpkin', model='Red Demon', backdrop='Black', rub=43694)


@functools.lru_cache(None)
def pump_lo_backdrop():
    bds = [b['name'] for b in gifts_api.backdrops('Mad Pumpkin')]
    for name in ('Pumpkin', 'Orange', 'Tangerine', 'Carrot Juice', 'Copper'):
        if name in bds:
            return name
    return bds[0]


def flip_tile(cv, t, x, y, s, a, t_flip, lo, hi):
    """3D-переворот плитки вокруг вертикальной оси: до t_flip — lo, после — hi; на ребре — блик."""
    u = (t - t_flip) / 0.5
    if u <= 0:
        c, sq = lo, 1.0
    elif u >= 1:
        c, sq = hi, 1.0
    else:
        ang = math.pi * ease(u)
        sq = abs(math.cos(ang))
        c = lo if ang < math.pi / 2 else hi
    tile = gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t)
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, y + 14 * s, s * max(0.2, sq), a)
    fx.over(cv, fx.warp(tile, x, y, s * max(0.02, sq), s * (1 + 0.06 * (1 - sq)), 0.0), a)
    if 0 < u < 1:
        put(cv, tinted_glow((255, 240, 200)), x, y, s * 0.9, a * (1 - sq) * 0.6)


def scene_pumpkin(cv, t):
    if not (E.PUMPKIN - 0.15 <= t < E.LOCKET + 0.2):
        return
    a = appear(t, E.PUMPKIN, 0.35) * (1 - appear(t, E.LOCKET - 0.3, 0.3))
    lo = dict(PUMP_LO, backdrop=pump_lo_backdrop())
    s = 0.72 * (0.7 + 0.3 * pop_in(t, E.PUMPKIN))
    flip_tile(cv, t, 540, 470, s, a, E.PUMP_BLACK - 0.2, lo, PUMP_HI)
    put(cv, text('Mad Pumpkin', 26, 'Heavy'), 540, 470 - 150 * s - 26, 1.0, a)
    k = fx.clamp01((t - (E.PUMP_BLACK - 0.2)) / 0.7)
    price = lo['rub'] + (PUMP_HI['rub'] - lo['rub']) * ease(k)
    col = WINE if k > 0.5 else MUTED
    if t >= E.PUMP_CHEAP - 0.1:
        put(cv, text(rub(int(round(price / 10) * 10)), 40, 'Heavy', col), 540, 470 + 150 * s + 34, 1.0, a * appear(t, E.PUMP_CHEAP - 0.1, 0.25))
    lab = 'на чёрном фоне' if k > 0.5 else 'обычная'
    put(cv, upill(lab, WINE if k > 0.5 else (226, 220, 238), 24, WHITE if k > 0.5 else INK), 540, 470 + 150 * s + 86, 1.0,
        a * appear(t, E.PUMP_CHEAP - 0.1, 0.25))


# ---- 5. медальон за 17 млн
def scene_locket(cv, t):
    if not (E.LOCKET - 0.1 <= t < E.CREEPY):
        return
    L, R = lot('Heart Locket', 'floor'), lot('Heart Locket', 'black_floor')
    k = fx.clamp01((t - E.LOCKET_HIT) / 0.9)
    rp = '≈ ? ₽' if k <= 0 else ('≈ ' + f"{(L['rub'] + (R['rub'] - L['rub']) * ease(k)) / 1e6:.1f}".replace('.', ',') + ' млн ₽')
    pair(cv, t, L, R, E.LOCKET + 0.1, E.CREEPY + 0.3, cy=520, s0=1.0, rp=rp)


# ---- 7. «Так почему?»
@functools.lru_cache(None)
def qmark_tile():
    im = fx.rounded(TILE, TILE, 46, (20, 16, 30, 255), (120, 40, 70, 255), 4).copy()
    q = text('?', 160, 'Heavy', (220, 200, 230))
    im.alpha_composite(q, ((TILE - q.width) // 2, (TILE - q.height) // 2))
    return im


def scene_tease(cv, t):
    if not (E.TEASE - 0.1 <= t < AD_STOP + 0.12):
        return
    a = appear(t, E.TEASE + 0.1, 0.3)
    for j, (x, sc_, ph) in enumerate(((220, 0.62, 1.0), (540, 1.0, 0.0), (860, 0.62, 2.0))):
        aj = a * appear(t, E.TEASE + 0.1 + (0.2 if j != 1 else 0), 0.3)
        put(cv, qmark_tile(), x, 500 + (40 if j != 1 else 0), sc_ * (1 + 0.04 * math.sin(t * 6 + ph)), aj, math.sin(t * 3 + ph) * 0.06)


# ---- 8. спрос: шоурум, предметы появляются, пока Мита пробегает мимо
@functools.lru_cache(None)
def prop_img(name, sc=1.0):
    """Фото-предметы для «спроса» (ChatGPT, хромакей: input/props/luxury_sheet.png → card/car/tux.png)."""
    im = Image.open(HERE / 'input' / 'props' / f'{name}.png').convert('RGBA')
    bw, bh = {'card': (270, 230), 'car': (345, 260), 'tux': (250, 280)}[name]
    k = min(bw / im.width, bh / im.height) * sc
    return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)


@functools.lru_cache(None)
def spot_pool():
    return fx.radial(256, (255, 214, 160), 1.4, 1.0).resize((420, 120))


def scene_demand(cv, t):
    """Шкала «спрос»: наполняется на «спросе!» и с каждым предметом (карты, машины, смокинги)."""
    if not (E.DEMAND - 0.1 <= t < E.GLOW):
        return
    a = appear(t, E.DEMAND + 0.15, 0.35) * (1 - appear(t, E.GLOW - 0.35, 0.3))
    if a <= 0:
        return
    lv = 0.25 * appear(t, E.DEMAND + 0.3, 0.6)
    for ti in E.ICONS:
        lv += 0.25 * appear(t, ti, 0.5)
    x0, x1, y = 230, 850, 352
    def draw(d, mp, S):
        X0, Y0 = mp(x0, y - 18)
        X1, Y1 = mp(x1, y + 18)
        d.rounded_rectangle([X0, Y0, X1, Y1], int(18 * S), fill=(236, 230, 246, 255))
        Xf = X0 + (X1 - X0) * lv
        if Xf > X0 + 36 * S:
            d.rounded_rectangle([X0, Y0, Xf, Y1], int(18 * S), fill=WINE + (255,))
            g = 0.5 + 0.5 * math.sin(t * 6)
            d.ellipse([Xf - 22 * S, Y0 - 4 * S, Xf + 4 * S, Y1 + 4 * S], fill=(255, 210, 120, int(120 * g)))
    fx.over(cv, fx.draw_rgba((x0 - 30, y - 40, x1 + 30, y + 40), draw), a)
    put(cv, utext('спрос', 30, 'ExtraBold', WINE), x0 - 10, y - 50, 1.0, a, anchor=None)
    put(cv, utext(f'{int(round(lv * 100))}%', 26, 'ExtraBold', INK), x1 - 20, y - 50, 1.0, a)
    if lv > 0.97:
        sparkles(cv, t, E.ICONS[2] + 0.45, x1, y, 120, 10, GOLD)


# ---- 9. светится: телефон-рамка сверху (как в v2), Мита держит свой телефон внизу
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
    a = appear(t, E.GLOW + 0.1, 0.35) * (1 - out)
    ph = appear(t, E.GLOW_PHONE, 0.5)
    s = (1.0 - 0.3 * ph) * (1 + 0.02 * beat_pulse(t, 8))
    if ph > 0:
        put(cv, phone_frame(), 540, 480, 0.68 + 0.08 * ph, a * ph)
    glow = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(t * 4))
    put(cv, tinted_glow((210, 150, 255)), 540, 490, 1.6 * s, a * glow)
    put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - E.GLOW), 540, 490, s, a)
    put(cv, text(c['gift'], 30, 'Heavy', WHITE if ph > 0.5 else INK), 540, 490 - 150 * s - 28, 1.0, a)


# ---- 10. обычный фон: Мита отпинывает серый подарок
def scene_plain(cv, t):
    if not (E.PLAIN - 0.1 <= t < E.PRICE + 0.3):
        return
    hi, c = lot('Neko Helmet', 'black_floor'), lot('Neko Helmet', 'floor')
    a = appear(t, E.PLAIN + 0.05, 0.3)
    at = a * (1 - appear(t, E.PRICE - 0.3, 0.3))
    dim = appear(t, E.KICK - 0.6, 0.6)
    for j, (cc, x) in enumerate(((hi, 300), (c, 780))):
        s_ = 0.72 * (0.7 + 0.3 * pop_in(t, E.PLAIN + 0.05 + 0.15 * j))
        tl = gift_tile(cc['gift'], cc['model'], cc['backdrop'], TILE, t - E.PLAIN)
        if j == 1 and dim > 0:
            gg = ImageOps.grayscale(tl.convert('RGB')).convert('RGBA')
            gg.putalpha(tl.getchannel('A'))
            tl = Image.blend(tl, gg, 0.8 * dim)
        if j == 0:
            put(cv, tinted_glow((255, 210, 140)), x, 470, 1.2 * s_, at * (0.3 + 0.1 * math.sin(t * 4)))
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, 470 + 12 * s_, s_, at * (1 - 0.4 * dim * j))
        put(cv, tl, x, 470, s_ * (1 - 0.06 * dim * j), at * (1 - 0.35 * dim * j))
        put(cv, text(cc['gift'], 24, 'Heavy'), x, 470 - 150 * s_ - 24, 1.0, at)
        put(cv, text(rub(cc['rub']), 36, 'Heavy', WINE if j == 0 else MUTED), x, 470 + 150 * s_ + 30, 1.0, at)
        put(cv, upill('на чёрном' if j == 0 else 'обычный фон', WINE if j == 0 else (226, 220, 238), 22, WHITE if j == 0 else INK),
            x, 470 + 150 * s_ + 78, 1.0, at)
    if dim > 0.5:
        put(cv, text('просто фон…', 30, 'Heavy', MUTED), 780, 300, 1.0, at * appear(t, E.KICK - 0.2, 0.3))
    tile = gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - E.PLAIN)
    g = ImageOps.grayscale(tile.convert('RGB')).convert('RGBA')
    g.putalpha(tile.getchannel('A'))
    tile = Image.blend(tile, g, 0.75)
    u = t - (E.KICK + 0.12)
    x, y, rot, s = 790.0, 1440.0, 0.0, 0.5
    if u > 0:
        x += 1300 * u
        y += -900 * u + 900 * u * u
        rot = -u * 9
    else:
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, y + 12, s, a)
    put(cv, tile, x, y, s, a, rot)
    if u <= 0:
        put(cv, text(c['gift'], 24, 'Heavy', MUTED), x, y - 100, 1.0, a)
    if 0 < u < 0.5:
        sparkles(cv, t, E.KICK + 0.12, 700, 1420, 140, 10, (180, 180, 190))


# ---- 11. спрос → цена растёт: Мита висит на линии графика
def scene_price(cv, t):
    if not (E.PRICE - 0.1 <= t < E.OUTRO + 0.3):
        return
    a = appear(t, E.PRICE + 0.05, 0.3) * (1 - appear(t, E.OUTRO - 0.3, 0.3))
    pts = M3.graph_points(t)
    def draw(d, mp, S):
        x0, y0 = mp(90, 1470)
        d.line([x0, y0, mp(1000, 1470)[0], y0], fill=(200, 194, 215, 255), width=int(4 * S))
        d.line([x0, y0, x0, mp(0, 280)[1]], fill=(200, 194, 215, 255), width=int(4 * S))
        P = [mp(x, y) for x, y in pts]
        d.line(P, fill=WINE + (255,), width=int(12 * S), joint='curve')
    fx.over(cv, fx.draw_rgba((60, 260, 1020, 1500), draw), a)
    if t >= E.PRICE_UP:
        x, y = pts[-1]
        put(cv, utext('цена ↑', 46, 'ExtraBold', WINE), x + 230, y + 40, 0.7 + 0.3 * pop_in(t, E.PRICE_UP), a)


# ---- 12. люкс или минимум
def scene_outro(cv, t):
    """«роскошный люкс» — Electric Skull на чёрном (≈26 тыс. ₽); «базовый минимум» — Snow Globe на невзрачном зелёном (≈700 ₽).
    Сверху крупные плитки, у Миты в руках те же NFT."""
    if t < E.OUTRO - 0.1:
        return
    L, R = lot('Electric Skull', 'black_floor'), lot('Snow Globe', 'floor')
    for j, (c, lab, tj) in enumerate(((L, 'роскошный люкс', E.OUTRO_LUX), (R, 'базовый минимум', E.OUTRO_MIN))):
        a = appear(t, tj, 0.3)
        if a <= 0:
            continue
        x = 540 + (j - 0.5) * 520
        s = 0.95 * (0.6 + 0.4 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
        if j == 0:
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


# ------------------------------------------------------------------ боковые панели (заполняют кадр, без процентов и «×»)
def bars(cv, t, t0, t1, lo, hi, lo_lab, hi_lab, top='обычный  ·  чёрный'):
    """Панель-столбики (как в 49): обычный (серый) и чёрный (бордовый), высота — по цене, без множителей."""
    a = window_a(t, t0, t1, 0.3)
    if a <= 0:
        return
    put_panel(cv, LX, SIDE_Y, a, t0, t)
    g = ease((t - t0 - 0.2) / 0.8)
    base, maxh = SIDE_Y + 100, 150
    for j, (v, lab, col) in enumerate(((lo, lo_lab, (190, 184, 210)), (hi, hi_lab, WINE))):
        h = max(8, maxh * (v / hi) ** 0.5 * g)
        x = LX - 52 + 104 * j
        def bar(d, mp, S, h=h, x=x, col=col):
            x0, y0 = mp(x - 32, base - h)
            x1, y1 = mp(x + 32, base)
            d.rounded_rectangle([x0, y0, x1, y1], int(10 * S), fill=col + (int(255 * a),))
        fx.over(cv, fx.draw_rgba((x - 40, base - maxh - 10, x + 40, base + 4), bar))
        put(cv, text(lab, 20, 'Bold', INK if j == 0 else WINE), x, base + 24, 1.0, a)
    put(cv, text(top, 18, 'Semibold', MUTED), LX, SIDE_Y - 125, 1.0, a)


def side_panels(cv, t):
    def txt_panel(x, t0, t1, top, big, bot, big_col=WINE):
        a = window_a(t, t0, t1, 0.3)
        if a <= 0:
            return
        s = put_panel(cv, x, SIDE_Y, a, t0, t)
        put(cv, utext(top, 20, 'SemiBold', MUTED), x, SIDE_Y - 105, s, a)
        im = utext(big, 46, 'ExtraBold', big_col)
        put(cv, im, x, SIDE_Y - 10, s * min(1.0, 200 / im.width), a)
        put(cv, utext(bot, 20, 'SemiBold', MUTED), x, SIDE_Y + 85, s, a)
    txt_panel(LX, -0.5, E.HOOK_PRICE - 0.1, 'один и тот же', 'кекс', 'Whip Cupcake', INK)   # v5: с 1-го кадра, без цены
    bars(cv, t, E.HOOK_PRICE - 0.1, E.SPIN - 0.3, 438, 2452, '438 ₽', '2 452 ₽')          # цены — только после «больше»
    txt_panel(RX, -0.5, E.HOOK_PRICE + 0.4, 'чёрный фон', 'дороже?', 'почему?')
    txt_panel(RX, E.HOOK_PRICE + 0.4, E.SPIN - 0.3, 'чёрный фон', 'дороже', 'Whip Cupcake')
    txt_panel(LX, E.X7 + 0.6, E.PUMPKIN, 'коллекций', '121', 'с чёрным фоном')
    txt_panel(RX, E.X7 + 1.0, E.PUMPKIN, 'чёрный фон', 'дороже', 'почти везде')
    bars(cv, t, E.LOCKET + 0.6, E.CREEPY, 148858, 17512690, '149 тыс', '17,5 млн')
    txt_panel(RX, E.LOCKET_HIT + 0.9, E.CREEPY, 'на чёрном', '17,5 млн', 'цена продавца')
    txt_panel(LX, E.GACHA[1], E.TEASE, 'чёрный', 'не редкий', 'как бордовый')
    txt_panel(RX, E.GACHA[2], E.TEASE, 'выпадает', 'так же', 'как медный')
    txt_panel(LX, E.TEASE + 0.3, AD_STOP + 0.12, 'не редкость', '?', 'тогда что')
    txt_panel(RX, E.TEASE + 0.6, AD_STOP + 0.12, 'платят', 'больше', 'за что?')
    txt_panel(LX, E.DEMAND + 0.4, E.GLOW, 'чёрный цвет', 'люкс', 'цвет статуса')
    txt_panel(RX, E.DEMAND + 0.8, E.GLOW, 'чёрное', 'хотят', 'все')
    txt_panel(LX, E.GLOW + 0.4, E.PLAIN, 'на чёрном', 'ярче', 'контраст')
    txt_panel(RX, E.GLOW_PHONE, E.PLAIN, 'тёмная тема', 'телеграм', 'фон сливается')
    bars(cv, t, E.PLAIN + 0.4, E.PRICE, 3940, 38528, '3 940 ₽', '38 528 ₽')
    txt_panel(RX, E.PLAIN + 0.9, E.PRICE, 'обычный фон', 'просто', 'не цепляет', MUTED)
    txt_panel(RX, E.PRICE_UP, E.OUTRO, 'продавцы', 'цена ↑', 'не снижают')
    txt_panel(LX, E.OUTRO_MIN + 0.3, DUR + 1, 'выбирай', 'люкс', 'на чёрном')
    txt_panel(RX, E.OUTRO_PILL, DUR + 1, 'или', 'минимум', 'на зелёном', MUTED)


# ------------------------------------------------------------------ реклама: Мита сидит под баннером на огромном кексе
@functools.lru_cache(None)
def big_cup():
    c = lot('Whip Cupcake', 'black_floor')
    return lottie.frame(model_path(c['gift'], c['model']), 0.0, size=560)


LIE = ['lie_1', 'lie_2']             # поза лёжа: колено плавно поднимается и опускается (+ промежуточные, если есть)


def lie_frames():
    names = ['lie_1', 'lie_in_a', 'lie_2', 'lie_in_b'] if (anim.FR / 'lie_in_a.png').exists() else ['lie_1', 'lie_2']
    return names


def ad_overlay(c, t):
    """Во время рекламы Мита лежит на боку под баннером в полный рост (баннер ничем не закрыт)."""
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    u = max(0.0, bt)
    names = lie_frames()
    if bt > BR.B - 1.5:
        k = (bt - (BR.B - 1.5)) / 0.6
        fr = anim.morph('lie_1', 'lie_half', ease(k * 2)) if k < 0.5 else anim.morph('lie_half', 'lie_3', ease(k * 2 - 1))
    else:
        fr = anim.pingpong(names, u, 3.4)
    put(cv, soft_glow((200, 170, 230), 1000, 120), 540, 1595, 1.0, 0.6 * a)
    by, _ = anim.breathe(t)
    M3.put_mita(cv, fr, 540, 1600, 1.0, 333, a, sy=1 + 0.5 * (by - 1), shadow=False, anchor_x=768)
    return cv[..., :3]


# ------------------------------------------------------------------ эффекты к движениям Миты (как ветер при кружении, но свои)
def fx_ring(cv, t, t0, x, y, col=(190, 150, 230), w=380, d=0.55):
    u = (t - t0) / d
    if not 0 <= u < 1:
        return
    def draw(dr, mp, S):
        r = (0.25 + 0.75 * ease(u)) * w / 2
        X, Y = mp(x, y)
        for k, a in ((0, 1.0), (0.12, 0.5)):
            rr = r * (1 - k) * S
            dr.ellipse([X - rr, Y - rr * 0.22, X + rr, Y + rr * 0.22], outline=col + (int(200 * a * (1 - u)),),
                       width=max(1, int((7 - 5 * u) * S)))
    fx.over(cv, fx.draw_rgba((x - w / 2 - 20, y - w * 0.15, x + w / 2 + 20, y + w * 0.15), draw))


def fx_dust(cv, t, t0, x, y, d=0.6, n=9, spread=170):
    u = (t - t0) / d
    if not 0 <= u < 1:
        return
    rng = np.random.default_rng(int(t0 * 100))
    def draw(dr, mp, S):
        for j in range(n):
            side = -1 if j % 2 else 1
            dx = side * rng.uniform(0.3, 1.0) * spread * ease(u)
            dy = -rng.uniform(10, 50) * ease(u)
            X, Y = mp(x + dx, y + dy)
            r = (8 + 18 * u) * rng.uniform(0.7, 1.2) * S
            dr.ellipse([X - r, Y - r * 0.8, X + r, Y + r * 0.8], fill=(205, 196, 222, int(150 * (1 - u))))
    fx.over(cv, fx.draw_rgba((x - spread - 60, y - 120, x + spread + 60, y + 40), draw))


def fx_lines(cv, t, t0, x, y, d=0.35, n=12, r0=120, r1=260, col=(150, 24, 52), up=False):
    u = (t - t0) / d
    if not 0 <= u < 1:
        return
    def draw(dr, mp, S):
        for j in range(n):
            ang = (-math.pi / 2 + (j - n / 2) * 0.12) if up else j * 2 * math.pi / n + 0.2
            a = r0 + (r1 - r0) * ease(u)
            b = a + 70 * (1 - u)
            X0, Y0 = mp(x + math.cos(ang) * a, y + math.sin(ang) * a)
            X1, Y1 = mp(x + math.cos(ang) * b, y + math.sin(ang) * b)
            dr.line([X0, Y0, X1, Y1], fill=col + (int(220 * (1 - u)),), width=max(1, int(6 * S * (1 - 0.6 * u))))
    R_ = r1 + 90
    fx.over(cv, fx.draw_rgba((x - R_, y - R_, x + R_, y + R_), draw))


def fx_arc(cv, t, t0, cx, cy, r, a0, a1, d=0.4, col=(200, 190, 215)):
    """След-«свуш» по дуге (пинок, взмах руки)."""
    u = (t - t0) / d
    if not 0 <= u < 1:
        return
    def draw(dr, mp, S):
        head = ease(min(1.0, u * 1.6))
        tail = ease(max(0.0, u * 1.6 - 0.6))
        pts = []
        for q in range(24):
            k = tail + (head - tail) * q / 23
            ang = a0 + (a1 - a0) * k
            pts.append(mp(cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        for q in range(1, len(pts)):
            f = q / len(pts)
            dr.line([pts[q - 1], pts[q]], fill=col + (int(220 * f * (1 - u * 0.6)),), width=max(1, int(14 * f * S)))
    fx.over(cv, fx.draw_rgba((cx - r - 40, cy - r - 40, cx + r + 40, cy + r + 40), draw))


def action_fx(cv, t, front):
    """Эффекты на действиях. back — на полу (за Митой), front — искры/линии (перед ней)."""
    LH, K, P = E.LOCKET_HIT, E.KICK, E.PRICE
    if not front:
        fx_dust(cv, t, 1.25, M3.hook_x(1.25) + 30, 1540)                      # хук: первый шаг
        fx_dust(cv, t, 2.05, M3.hook_x(2.05) + 20, 1540, n=6, spread=120)
        fx_ring(cv, t, E.PUMPKIN + 0.05, 540, 1600, (230, 120, 120), 620)     # тыква появляется
        fx_dust(cv, t, LH - 0.02, 540, 1540)                                  # прыжок: толчок
        fx_ring(cv, t, LH + 0.5, 540, 1545, (190, 150, 230), 520)             # приземление
        fx_dust(cv, t, LH + 0.5, 540, 1540, n=12, spread=230)
        fx_dust(cv, t, K + 0.12, 640, 1520, n=7, spread=140)                  # пинок
        fx_dust(cv, t, P + 0.95, M3.tip(P + 0.95)[0], 1540, n=8, spread=150)  # отрыв от пола на графике
        fx_ring(cv, t, P + 0.95, M3.tip(P + 0.95)[0], 1545, (200, 120, 150), 360)
        return
    sparkles(cv, t, 2.85, 640, 900, 150, 10, (255, 150, 190))                # хук: машет
    sparkles(cv, t, E.CARD_GRAB + 0.45, 430, 1180, 170, 12, GOLD)            # берёт кекс
    fx_lines(cv, t, E.CARD_SHOW + 0.3, 330, 950, n=14, r0=150, r1=300)        # кекс к камере
    sparkles(cv, t, E.PUMPKIN + 0.2, 420, 1000, 260, 14, (255, 150, 90))      # садится на тыкву
    sparkles(cv, t, E.PUMP_BLACK - 0.15, 470, 1050, 220, 16, GOLD)           # «на чёрном!»
    fx_lines(cv, t, LH, 540, 1450, n=9, r0=60, r1=220, col=(150, 140, 180), up=True)   # прыжок вверх
    sparkles(cv, t, LH + 0.15, 540, 1150, 330, 18, (255, 120, 160))          # пик прыжка
    fx_lines(cv, t, LH + 0.5, 540, 1500, n=16, r0=180, r1=380, col=WINE)      # удар приземления
    for g in E.GACHA:                                                          # карусель выдвигает фон
        sparkles(cv, t, g, 540, 570, 200, 12, GOLD)
    sparkles(cv, t, E.TEASE + 0.45, 600, 880, 110, 8, (190, 160, 230))        # «хм»
    for i, ti in enumerate(E.ICONS):                                           # жест к спутнику
        hx = (300, 540, 780)[i]
        fx_arc(cv, t, ti - 0.32, 540, 1130, 230, math.pi * (1.15 if i == 0 else 1.5 if i == 1 else 1.85),
               math.pi * (1.0 if i == 0 else 1.4 if i == 1 else 2.0), 0.4, (255, 215, 150))
    fx_ring(cv, t, E.GLOW_PHONE + 0.2, 540, 1180, (200, 140, 255), 300)       # телефон к зрителю
    fx_lines(cv, t, E.GLOW_SHOW + 0.05, 420, 1080, n=12, r0=110, r1=240, col=(170, 110, 255))
    fx_arc(cv, t, K - 0.12, 470, 1330, 200, math.pi * 0.95, math.pi * 0.05, 0.35)  # пинок: след ноги
    fx_lines(cv, t, K + 0.14, 760, 1420, n=10, r0=40, r1=160, col=(160, 160, 175))
    fx_lines(cv, t, P + 1.0, M3.tip(P + 1.0)[0], 1300, n=9, r0=60, r1=200, col=(150, 140, 180), up=True)
    sparkles(cv, t, E.OUTRO_PILL - 0.5, 600, 880, 160, 12, (255, 120, 170))   # подмигивание
    fx_ring(cv, t, E.OUTRO_PILL + 0.3, 540, 1545, (226, 54, 120), 420)        # «в комментарии»


# ------------------------------------------------------------------ живая камера и глитч-переходы
def camera(t):
    """(zoom, точка, сдвиг x, сдвиг y) для слоя сцены. Интерфейс (заголовок, панели, субтитры) не двигается."""
    z, px, py = 1.0 + 0.012 * math.sin(t * 0.5), 540.0, 1100.0
    dx, dy = 6 * math.sin(t * 0.37), 4 * math.sin(t * 0.29)
    sc = M3.scene_of(t)[0]
    if sc == 'card':
        k = ease((t - E.CARD_SHOW - 0.1) / 0.5) * (1 - ease((t - E.UFC + 0.5) / 0.4))
        z += 0.16 * k
        px, py = 540 * (1 - k) + 330 * k, 1100 * (1 - k) + 900 * k
    elif sc == 'pumpkin':
        u = t - E.PUMPKIN
        z += 0.04 + 0.03 * math.sin(u * 0.7)
        dx += 25 * math.sin(u * 0.5)
    elif sc == 'show':
        z += 0.03 * math.sin((t - E.DEMAND) * 0.6)
    elif sc == 'jump':
        u = t - (E.LOCKET_HIT + 0.52)
        if 0 < u < 0.5:
            dy += 16 * math.sin(u * 60) * (1 - u / 0.5)
            dx += 9 * math.cos(u * 47) * (1 - u / 0.5)
    elif sc == 'phone':
        k = ease((t - E.GLOW_SHOW) / 0.7)
        z += 0.1 * k
        px, py = 540, 1100 * (1 - k) + 1000 * k
    elif sc == 'hang':
        x, y = M3.tip(t)
        py = 1100 + (y - 760) * 0.5
    return z, px, py, dx, dy


def apply_camera(cv, t):
    z, px, py, dx, dy = camera(t)
    if abs(z - 1) < 1e-4 and abs(dx) < 0.01 and abs(dy) < 0.01:
        return cv
    M = np.float32([[z, 0, (1 - z) * px + dx], [0, z, (1 - z) * py + dy]])
    out = cv2.warpAffine(cv, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


GLITCH = [  # (время содержания, длительность, сила, красный)
    (E.SPIN + 0.6, 0.16, 0.6, False),
    (E.CREEPY - 0.04, 0.24, 1.0, True),
    (E.CREEPY + 0.9, 0.08, 0.45, True),
    (E.CREEPY + 1.45, 0.06, 0.55, True),
    (E.CREEPY_END - 0.06, 0.2, 1.0, True),
]


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
    for _ in range(int(6 * k)):
        x0, y0 = int(rng.integers(0, W - 200)), int(rng.integers(0, H - 60))
        w_, h_ = int(rng.integers(60, 360)), int(rng.integers(8, 40))
        out[y0:y0 + h_, x0:x0 + w_] = 255 - out[y0:y0 + h_, x0:x0 + w_] if rng.random() < 0.3 else (
            np.roll(out[y0:y0 + h_, x0:x0 + w_], int(rng.integers(-80, 80)), axis=1))
    f = out.astype(np.float32)
    f[::3] *= 0.8
    if red:
        f[..., 0] = np.minimum(255, f[..., 0] * 1.25 + 30 * k)
        f[..., 1] *= 0.7
        f[..., 2] *= 0.75
    mix = min(1.0, 0.35 + k)
    return np.clip(img * (1 - mix) + f * mix, 0, 255).astype(np.uint8)


def loading_bar(cv, t):
    """Отсылка к MiSide: короткая «загрузка» при входе в новую комнату."""
    for t0 in (AD_STOP + 0.06, E.GLOW - 0.08):
        u = (t - t0) / 0.55
        if not 0 <= u < 1:
            continue
        a = min(1.0, u * 6) * (1 - fx.clamp01((u - 0.75) / 0.25))
        def draw(d, mp, S):
            x0, y0 = mp(340, 1780)
            x1, y1 = mp(740, 1806)
            d.rectangle([x0, y0, x1, y1], outline=(255, 255, 255, 230), width=int(3 * S))
            n = int(10 * min(1, u * 1.4))
            for i in range(n):
                X0 = x0 + (6 + i * 39) * S
                d.rectangle([X0, y0 + 6 * S, X0 + 33 * S, y1 - 6 * S], fill=(255, 255, 255, 230))
        fx.over(cv, fx.draw_rgba((320, 1740, 760, 1830), draw), a)
        put(cv, text('ЗАГРУЗКА…', 26, 'Heavy', WHITE, True), 540, 1755, 1.0, a)


# ================================================================== v5 (2026-11-21): бутик + клипы Gemini
import mita_v5 as M5

BOUT_OY = 250                     # картинка бутика (1024×1536 → ширина 1080) сдвинута вниз; верх — растянутая стена
NY = 690                          # центр подарка в нише
NXL, NXR = 282, 799               # центры ниш
PLATE_Y = 962                     # золотые таблички под нишами
NICHE_IN = [(84, 484, 482, 910), (600, 484, 998, 910)]     # внутренность ниш (бархат)
SIDE_Y = 1235                     # боковые панели — на стене под табличками
GOLD_T = (120, 84, 20)


@functools.lru_cache(None)
def boutique():
    im = Image.open(HERE / 'input' / 'rooms' / 'boutique.png').convert('RGB')
    s = W / im.width
    im = im.resize((W, round(im.height * s)), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    out = np.empty((H, W, 3), np.float32)
    top = a[:int(128 * s)]                                    # спокойная стена над золотой линией
    out[:BOUT_OY + top.shape[0]] = cv2.resize(top, (W, BOUT_OY + top.shape[0]), interpolation=cv2.INTER_LINEAR)
    h_ = min(a.shape[0] - top.shape[0], H - BOUT_OY - top.shape[0])
    out[BOUT_OY + top.shape[0]:BOUT_OY + top.shape[0] + h_] = a[top.shape[0]:top.shape[0] + h_]
    rest = H - (BOUT_OY + top.shape[0] + h_)
    if rest > 0:                                              # низ пола — растянуть последние строки
        out[H - rest:] = cv2.resize(a[-80:], (W, rest), interpolation=cv2.INTER_LINEAR)
    lum = out.mean(-1, keepdims=True)
    return out * 0.9 + lum * 0.06 + 6                         # чуть приглушить: фон не спорит с Митой


@functools.lru_cache(None)
def niche_mask(j):
    x0, y0, x1, y1 = NICHE_IN[j]
    m = Image.new('L', (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], 30, fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(2)), np.float32)[..., None] / 255


def creepy_k(t):
    return ease((t - E.CREEPY + 0.05) / 0.25) * (1 - ease((t - E.CREEPY_END + 0.05) / 0.2))


def spot_flicker(t, j):
    k = creepy_k(t)
    if k <= 0:
        return 1.0
    on = (math.sin(t * 31 + j * 2.3) > -0.3) * (math.sin(t * 9.7 + j) > -0.7)
    return 1 - k * (0.75 if not on else 0.35)


def background(t):
    cv = np.empty((H, W, 4), np.float32)
    cv[..., :3] = boutique()
    cv[..., 3] = 255
    c1, c2 = tint_at(t)
    p = beat_pulse(t, 5)
    q = lambda c: tuple(int(v) for v in c)
    put(cv, tinted_glow(q(c1)), 160 + 60 * math.sin(t * 0.31), 1200 + 50 * math.cos(t * 0.27), 1.9, 0.07 + 0.03 * p)
    put(cv, tinted_glow(q(c2)), 920 + 50 * math.cos(t * 0.23), 1250 + 60 * math.sin(t * 0.29), 1.9, 0.06 + 0.03 * p)
    for j, x in enumerate((NXL, NXR)):                        # тёплый луч светильника над нишей «дышит»
        put(cv, tinted_glow((255, 214, 150)), x, 560, 0.55, (0.10 + 0.04 * math.sin(t * 1.3 + j)) * spot_flicker(t, j), )
    k = creepy_k(t)
    if k > 0:
        cv[..., :3] = cv[..., :3] * (1 - 0.62 * k) + np.array([40, 0, 10], np.float32) * 0.25 * k
    deco(cv, t, M3.scene_of(t)[0])
    return cv


def deco(cv, t, sc):
    goth = appear(t, M5.SW, 0.6)
    if goth > 0 and creepy_k(t) < 0.5:                        # готика: редкие лепестки роз
        def petals(d, mp, S):
            rng = np.random.default_rng(31)
            for j in range(9):
                x0, sp = rng.uniform(0, W), rng.uniform(40, 80)
                y = (rng.uniform(0, H) + t * sp) % (H + 60) - 30
                x = x0 + math.sin(t * 0.8 + j) * 40
                X, Y = mp(x, y)
                r = rng.uniform(7, 12) * S
                a2 = t * 1.5 + j
                pts = [(X + math.cos(a2) * r * 1.5, Y + math.sin(a2) * r * 1.5), (X + math.cos(a2 + 1.6) * r * 0.6, Y + math.sin(a2 + 1.6) * r * 0.6),
                       (X - math.cos(a2) * r * 1.5, Y - math.sin(a2) * r * 1.5), (X - math.cos(a2 + 1.6) * r * 0.6, Y - math.sin(a2 + 1.6) * r * 0.6)]
                d.polygon(pts, fill=WINE + (int(80 * goth),))
        fx.over(cv, fx.draw_rgba((0, 0, W, H), petals))
    a = window(t, E.GLOW, E.PLAIN)                            # телефон: бутик чуть темнеет, фиолетовое свечение
    if a > 0:
        cv[..., :3] *= 1 - 0.18 * a
        put(cv, soft_glow((190, 120, 255), 700, 700), NXR, NY, 1.0, 0.3 * a)
    a = window(t, E.PLAIN + 0.3, E.PRICE, 0.5)                # «просто фон»: всё ненадолго блекнет
    if a > 0:
        g = cv[..., :3].mean(-1, keepdims=True)
        cv[..., :3] = cv[..., :3] * (1 - 0.45 * a) + g * 0.45 * a
    a = appear(t, E.OUTRO, 0.5)                               # финал: левая ниша (люкс) — тёплое золото
    if a > 0:
        put(cv, soft_glow((255, 200, 110), 600, 700), NXL, NY, 1.0, 0.3 * a)


# ---- ниши: подарок на бархате, имя сверху, фон снизу, цена — на золотой табличке
@functools.lru_cache(None)
def plaque(txt, hot):
    t_ = utext(txt, 32, 'ExtraBold', (90, 14, 30) if hot else (70, 52, 20))
    w_, h_ = t_.width + 40, 56
    im = Image.new('RGBA', (w_ * 2, h_ * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(h_ * 2):
        c = 0.55 + 0.45 * math.sin(math.pi * k / (h_ * 2))
        d.line([(0, k), (w_ * 2, k)], fill=(int(205 * c + 40), int(160 * c + 30), int(70 * c + 10), 255))
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w_ * 2 - 1, h_ * 2 - 1], 14, fill=255)
    im.putalpha(m)
    ImageDraw.Draw(im).rounded_rectangle([3, 3, w_ * 2 - 4, h_ * 2 - 4], 12, outline=(255, 236, 170, 255), width=3)
    im = im.resize((w_, h_), Image.LANCZOS)
    im.alpha_composite(t_, ((w_ - t_.width) // 2, (h_ - t_.height) // 2))
    return im


def card(cv, c, cx, cy, s, a, t_anim, price_txt=None, price_col=None, label=True, dim=0.0, blur=0.0):
    if a <= 0:
        return
    a *= 1 - 0.7 * dim
    put(cv, tinted_glow((255, 220, 160)), cx, cy - 20, 0.75 * s, a * 0.22)
    put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.7), cx, cy + 14 * s, s, a)
    tile = gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t_anim)
    if blur > 0.01:
        tile = tile.filter(ImageFilter.GaussianBlur(22 * blur))
    put(cv, tile, cx, cy, s, a)
    if blur > 0.01:
        wob = math.sin(t_anim * 3.1 + cx) * 0.06
        put(cv, qmark(), cx, cy + 6 * math.sin(t_anim * 2.4), s * (0.75 + 0.25 * blur) * (1 + 0.04 * math.sin(t_anim * 5)), a * blur, wob)
    if label:
        put(cv, text(c['gift'], 28, 'Heavy', (246, 236, 220), True), cx, cy - (TILE / 2 + 26) * s, 1.0, a)
        bcol = (255, 205, 120) if c['backdrop'] == 'Black' else (200, 190, 200)
        put(cv, multi((('Фон ', (190, 180, 190)), (c['backdrop'], bcol)), 22, 'Semibold', True), cx, cy + (TILE / 2 + 22) * s, 1.0, a)
    pt = price_txt if price_txt is not None else rub(c['rub'])
    y = PLATE_Y if abs(cy - NY) < 60 else cy + (TILE / 2 + 76) * s
    put(cv, plaque(pt, c['backdrop'] == 'Black' or price_col == WINE), cx, y, 1.0, a)


def pair(cv, t, left, right, t_in, t_out, cy=NY, s0=0.85, lp=None, rp=None, gap=NXR - NXL, rcol=None, reveal=None):
    out = appear(t, t_out - 0.3, 0.3) if t_out else 0.0
    for j, c in enumerate((left, right)):
        tj = t_in + 0.25 * j
        a = appear(t, tj, 0.3) * (1 - out)
        s = s0 * (0.6 + 0.4 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
        b = 0.0
        if reveal:
            b = 1 - ease((t - reveal[j]) / 0.35)
            if t >= reveal[j]:
                s *= 1 + 0.08 * math.sin(math.pi * min(1.0, (t - reveal[j]) / 0.4))
        card(cv, c, (NXL + NXR) / 2 + (j - 0.5) * gap, cy, s, a, t - tj, (lp, rp)[j], rcol if j else None, blur=b)


def scene_hook(cv, t):
    if t >= M5.SW + 0.3:
        return
    L, R = lot('Whip Cupcake', 'floor'), lot('Whip Cupcake', 'black_floor')
    k = fx.clamp01((t - E.HOOK_PRICE) / 0.6)
    rp = None if k >= 1 else (rub(int(round((L['rub'] + (R['rub'] - L['rub']) * ease(k)) / 10) * 10)) if k > 0 else '≈ ? ₽')
    pair(cv, t, L, R, -0.8, M5.SW, rp=rp, reveal=(E.REVEAL_L, E.REVEAL_R))
    qa = 1 - appear(t, E.HOOK_PRICE + 0.3, 0.3)
    if qa > 0:
        put(cv, fx.solid_pill('ЗА ЧТО ПЕРЕПЛАТА?', WINE, 34), 540, 238 + 4 * math.sin(t * 3), 1.0 + 0.03 * math.sin(t * 5), qa)


X7P = [('Top Hat', E.X7 + 0.1, 8.25), ('Big Year', 8.25, E.CARD_GRAB), ('Whip Cupcake', E.CARD_GRAB, E.PUMPKIN - 0.1)]


def scene_x7(cv, t):
    if not (E.X7 - 0.1 <= t < E.PUMPKIN + 0.2):
        return
    for g, t0, t1 in X7P:
        if t0 - 0.05 <= t < t1 + 0.05:
            L, R = lot(g, 'floor'), lot(g, 'black_floor')
            rp = None
            if g == 'Whip Cupcake' and t < E.CARD_SHOW:
                rp = '≈ ? ₽'
            pair(cv, t, L, R, t0, t1, rp=rp)
    a = window(t, E.X7 + 0.3, E.PUMPKIN - 0.1)
    put(cv, upill('тот же подарок на чёрном — дороже', WINE, 24, WHITE), 540, 420, 1.0, a)


def scene_pumpkin(cv, t):
    if not (E.PUMPKIN - 0.15 <= t < E.LOCKET + 0.2):
        return
    out = appear(t, E.LOCKET - 0.3, 0.3)
    lo = dict(PUMP_LO, backdrop=pump_lo_backdrop())
    a0 = appear(t, E.PUMP_CHEAP - 0.1, 0.3) * (1 - out)
    card(cv, lo, NXL, NY, 0.85 * (0.7 + 0.3 * pop_in(t, E.PUMP_CHEAP - 0.1)), a0, t, rub(lo['rub']))
    a1 = appear(t, E.PUMPKIN, 0.3) * (1 - out)
    if a1 > 0:
        s = 0.85 * (0.7 + 0.3 * pop_in(t, E.PUMPKIN))
        u = (t - (E.PUMP_BLACK - 0.2)) / 0.5
        if u < 0.5:
            sq = 1.0 if u <= 0 else abs(math.cos(math.pi * ease(u)))
            fx.over(cv, fx.warp(qmark_tile(), NXR, NY, s * max(0.02, sq), s, 0.0), a1)
        else:
            sq = 1.0 if u >= 1 else abs(math.cos(math.pi * ease(u)))
            tile = gift_tile(PUMP_HI['gift'], PUMP_HI['model'], PUMP_HI['backdrop'], TILE, t)
            fx.over(cv, fx.warp(tile, NXR, NY, s * max(0.02, sq), s * (1 + 0.06 * (1 - sq)), 0.0), a1)
            if u < 1:
                put(cv, tinted_glow((255, 240, 200)), NXR, NY, s * 0.9, a1 * (1 - sq) * 0.6)
            else:
                b = appear(t, E.PUMP_BLACK + 0.3, 0.3)
                put(cv, text('Mad Pumpkin', 28, 'Heavy', (246, 236, 220), True), NXR, NY - (TILE / 2 + 26) * s, 1.0, a1 * b)
                put(cv, multi((('Фон ', (190, 180, 190)), ('Black', (255, 205, 120))), 22, 'Semibold', True), NXR, NY + (TILE / 2 + 22) * s, 1.0, a1 * b)
                put(cv, plaque(rub(PUMP_HI['rub']), True), NXR, PLATE_Y, 1.0, a1 * b)
                sparkles(cv, t, E.PUMP_BLACK + 0.3, NXR, NY, 200, 14, GOLD)


def scene_locket(cv, t):
    if not (E.LOCKET - 0.1 <= t < E.CREEPY):
        return
    L, R = lot('Heart Locket', 'floor'), lot('Heart Locket', 'black_floor')
    k = fx.clamp01((t - E.LOCKET_HIT) / 0.9)
    rp = '≈ ? ₽' if k <= 0 else ('≈ ' + f"{(L['rub'] + (R['rub'] - L['rub']) * ease(k)) / 1e6:.1f}".replace('.', ',') + ' млн ₽')
    pair(cv, t, L, R, E.LOCKET + 0.1, E.CREEPY + 0.1, rp=rp)


def scene_tease(cv, t):
    if not (E.CREEPY_END - 0.1 <= t < AD_STOP + 0.12):
        return
    # «не самый редкий»: в нишах — чёрный и бордовый/медный фоны одного подарка, шанс выпадения одинаковый
    a = appear(t, E.CREEPY_END + 0.1, 0.3) * (1 - appear(t, E.TEASE - 0.2, 0.3))
    if a > 0:
        g = 'Top Hat'
        mdl = lot(g, 'black_floor')['model']
        for j, (bd, t0) in enumerate((('Black', E.CREEPY_END + 0.1), ('Burgundy' if t < E.GACHA[2] else 'Copper', E.GACHA[1]))):
            aj = a * appear(t, t0, 0.3)
            if aj <= 0:
                continue
            x = (NXL, NXR)[j]
            s = 0.8 * (0.7 + 0.3 * pop_in(t, t0))
            try:
                tile = gift_tile(g, mdl, bd, TILE, t)
            except Exception:
                tile = gift_tile(g, mdl, 'Black', TILE, t)
            put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.7), x, NY + 12, s, aj)
            put(cv, tile, x, NY, s, aj)
            put(cv, multi((('Фон ', (190, 180, 190)), (bd, (255, 205, 120))), 24, 'Semibold', True), x, NY - (TILE / 2 + 24) * s, 1.0, aj)
            put(cv, plaque('шанс тот же', False), x, PLATE_Y, 1.0, aj * appear(t, E.GACHA[0], 0.3))
    b = appear(t, E.TEASE + 0.1, 0.3)
    for j, x in enumerate((NXL, NXR)):
        bj = b * appear(t, E.TEASE + 0.1 + 0.2 * j, 0.3)
        put(cv, qmark_tile(), x, NY, 0.8 * (1 + 0.04 * math.sin(t * 6 + j)), bj, math.sin(t * 3 + j) * 0.06)


def scene_demand(cv, t):
    if not (E.DEMAND - 0.3 <= t < E.GLOW):
        return
    a = appear(t, AD_STOP + 0.15, 0.35) * (1 - appear(t, E.GLOW - 0.35, 0.3))
    if a <= 0:
        return
    lv = 0.25 * appear(t, E.DEMAND + 0.3, 0.6)
    for ti in E.ICONS:
        lv += 0.25 * appear(t, ti, 0.5)
    x0, x1, y = 230, 850, 360
    def draw(d, mp, S):
        X0, Y0 = mp(x0, y - 18)
        X1, Y1 = mp(x1, y + 18)
        d.rounded_rectangle([X0, Y0, X1, Y1], int(18 * S), fill=(246, 238, 226, 255), outline=(205, 165, 90, 255), width=int(2 * S))
        Xf = X0 + (X1 - X0) * lv
        if Xf > X0 + 36 * S:
            d.rounded_rectangle([X0, Y0, Xf, Y1], int(18 * S), fill=WINE + (255,))
            g = 0.5 + 0.5 * math.sin(t * 6)
            d.ellipse([Xf - 22 * S, Y0 - 4 * S, Xf + 4 * S, Y1 + 4 * S], fill=(255, 210, 120, int(120 * g)))
    fx.over(cv, fx.draw_rgba((x0 - 30, y - 40, x1 + 30, y + 40), draw), a)
    put(cv, utext('спрос', 30, 'ExtraBold', WINE), x0 + 30, y - 50, 1.0, a)
    put(cv, utext(f'{int(round(lv * 100))}%', 26, 'ExtraBold', INK), x1 - 20, y - 50, 1.0, a)
    if lv > 0.97:
        sparkles(cv, t, E.ICONS[2] + 0.45, x1, y, 120, 10, GOLD)
    # предметы роскоши в нишах: карта → (слева), машина (справа), смокинг сменяет карту
    items = [('card', NXL, E.ICONS[0], E.ICONS[2] - 0.1, 'чёрная карта'), ('car', NXR, E.ICONS[1], E.GLOW, 'чёрная машина'),
             ('tux', NXL, E.ICONS[2], E.GLOW, 'смокинг')]
    for name, x, t0, t1, lab in items:
        b = a * appear(t, t0, 0.3) * (1 - appear(t, t1 - 0.25, 0.25))
        if b <= 0:
            continue
        im = prop_img(name, 1.05)
        put(cv, tinted_glow((255, 220, 160)), x, NY, 0.8, b * 0.3)
        put(cv, im, x, NY + 6 * math.sin(t * 2 + x), 0.7 + 0.3 * pop_in(t, t0), b, 0.04 * math.sin(t * 1.3 + x))
        put(cv, plaque(lab, True), x, PLATE_Y, 1.0, b)
    # до предметов — два подарка на чёрном в нишах (люкс)
    c1 = window(t, AD_STOP + 0.2, E.ICONS[0] + 0.2, 0.3)
    if c1 > 0:
        pair(cv, t, lot('Electric Skull', 'black_floor'), lot('Top Hat', 'black_floor'), AD_STOP + 0.2, E.ICONS[0] + 0.2)


def scene_glow(cv, t):
    if not (E.GLOW - 0.3 <= t < E.PLAIN + 0.3):
        return
    out = appear(t, E.PLAIN - 0.3, 0.3)
    hi, lo = lot('Neko Helmet', 'black_floor'), lot('Neko Helmet', 'floor')
    card(cv, lo, NXL, NY, 0.8 * (0.7 + 0.3 * pop_in(t, E.GLOW)), appear(t, E.GLOW, 0.3) * (1 - out), t - E.GLOW)
    a = appear(t, E.GLOW + 0.25, 0.35) * (1 - out)
    if a <= 0:
        return
    ph = appear(t, E.GLOW_PHONE, 0.5)
    s = 0.8 * (1.0 - 0.18 * ph)
    if ph > 0:
        put(cv, phone_frame(), NXR, NY, 0.66, a * ph)
    glow = 0.35 + 0.25 * (0.5 + 0.5 * math.sin(t * 4)) + 0.4 * appear(t, E.GLOW_SHOW, 0.4)
    put(cv, tinted_glow((210, 150, 255)), NXR, NY, 1.3 * s, a * glow)
    put(cv, gift_tile(hi['gift'], hi['model'], hi['backdrop'], TILE, t - E.GLOW), NXR, NY, s, a)
    put(cv, text(hi['gift'], 28, 'Heavy', (246, 236, 220), True), NXR, NY - (TILE / 2 + 26) * 0.8 - (40 * ph), 1.0, a)
    put(cv, plaque('тёмная тема' if ph > 0.5 else rub(hi['rub']), True), NXR, PLATE_Y, 1.0, a)


def scene_plain(cv, t):
    if not (E.PLAIN - 0.1 <= t < E.PRICE + 0.3):
        return
    hi, c = lot('Neko Helmet', 'black_floor'), lot('Neko Helmet', 'floor')
    at = appear(t, E.PLAIN + 0.05, 0.3) * (1 - appear(t, E.PRICE - 0.3, 0.3))
    dim = appear(t, E.KICK - 0.4, 0.6)
    for j, (cc, x) in enumerate(((hi, NXL), (c, NXR))):
        s_ = 0.8 * (0.7 + 0.3 * pop_in(t, E.PLAIN + 0.05 + 0.15 * j))
        tl = gift_tile(cc['gift'], cc['model'], cc['backdrop'], TILE, t - E.PLAIN)
        if j == 1 and dim > 0:
            gg = ImageOps.grayscale(tl.convert('RGB')).convert('RGBA')
            gg.putalpha(tl.getchannel('A'))
            tl = Image.blend(tl, gg, 0.8 * dim)
        if j == 0:
            put(cv, tinted_glow((255, 210, 140)), x, NY, 1.0 * s_, at * (0.3 + 0.1 * math.sin(t * 4)))
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), x, NY + 12 * s_, s_, at * (1 - 0.4 * dim * j))
        put(cv, tl, x, NY, s_ * (1 - 0.06 * dim * j), at * (1 - 0.35 * dim * j))
        put(cv, plaque(rub(cc['rub']), j == 0), x, PLATE_Y, 1.0, at)
    if dim > 0:                                                 # в правой нише гаснет свет
        x0, y0, x1, y1 = NICHE_IN[1]
        reg = cv[y0:y1, x0:x1, :3]
        reg *= 1 - 0.55 * dim * niche_mask(1)
        put(cv, text('просто фон…', 30, 'Heavy', (210, 200, 210), True), NXR, NY - 165, 1.0, at * dim)


def scene_price(cv, t):
    if not (E.PRICE - 0.1 <= t < E.OUTRO + 0.3):
        return
    a = appear(t, E.PRICE + 0.05, 0.3) * (1 - appear(t, E.OUTRO - 0.3, 0.3))
    if a <= 0:
        return
    bl, br, by = M5.bar_screen(t)
    g = ease((t - E.PRICE) / 0.8)
    pts = [(70, 1470), (170, 1400), (240, 1430), (330, 1300), (380, 1250 + 0 * by)]
    pts = [(x, y) for x, y in pts] + [(bl + 8, by)]
    n = max(2, int(len(pts) * g + 0.999))
    P_ = pts[:n]
    tail = [(br - 8, by), (br + 120, by - 70), (980, by - 190)]
    def draw(d, mp, S):
        Q = [mp(x, y) for x, y in P_]
        d.line(Q, fill=WINE + (255,), width=int(12 * S), joint='curve')
        if t >= E.PRICE_UP - 0.3:
            k = ease((t - E.PRICE_UP + 0.3) / 0.6)
            T_ = [mp(x, y) for x, y in tail]
            e = (T_[0][0] + (T_[-1][0] - T_[0][0]) * k, T_[0][1] + (T_[-1][1] - T_[0][1]) * k)
            d.line([T_[0], T_[1] if k > 0.4 else e, e], fill=WINE + (255,), width=int(12 * S), joint='curve')
            ang = math.atan2(T_[-1][1] - T_[1][1], T_[-1][0] - T_[1][0])
            L_ = 34 * S
            d.polygon([e, (e[0] - L_ * math.cos(ang - 0.5), e[1] - L_ * math.sin(ang - 0.5)),
                       (e[0] - L_ * math.cos(ang + 0.5), e[1] - L_ * math.sin(ang + 0.5))], fill=WINE + (255,))
    fx.over(cv, fx.draw_rgba((40, 200, 1040, 1500), draw), a)
    if t >= E.PRICE_UP:
        put(cv, utext('цена ↑', 46, 'ExtraBold', WINE), 900, by - 260, 0.7 + 0.3 * pop_in(t, E.PRICE_UP), a)
    # в нишах — два подарка на чёрном, их цены растут
    for j, (g_, x) in enumerate((('Top Hat', 250), ('Electric Skull', 830))):
        c = lot(g_, 'black_floor')
        k = ease((t - E.PRICE - 0.4) / 4.0)
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), x, NY + 10, 0.62, a)
        put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t), x, NY, 0.62, a)
        v = int(round(c['rub'] * (1 + 0.35 * k) / 10) * 10)
        put(cv, plaque(rub(v), True), (NXL, NXR)[j], PLATE_Y, 1.0, a)


def scene_outro(cv, t):
    if t < E.OUTRO - 0.1:
        return
    L, R = lot('Electric Skull', 'black_floor'), lot('Snow Globe', 'floor')
    for j, (c, lab, tj) in enumerate(((L, 'роскошный люкс', E.OUTRO_LUX), (R, 'базовый минимум', E.OUTRO_MIN))):
        a = appear(t, tj, 0.3)
        if a <= 0:
            continue
        x = (NXL, NXR)[j]
        s = 0.85 * (0.6 + 0.4 * pop_in(t, tj)) * (1 + 0.02 * beat_pulse(t, 8))
        card(cv, c, x, NY, s, a, t - tj)
        put(cv, upill(lab, WINE if j == 0 else (226, 220, 238), 24, WHITE if j == 0 else INK), x, 1022, 0.8 + 0.2 * pop_in(t, tj), a)
    k = appear(t, E.OUTRO_PILL, 0.3)
    put(cv, fx.solid_pill('Пиши в комментариях', ACCENT, 34), 540, 300, 0.8 + 0.2 * k, k)


# ---- жуть: левая ниша становится тёмным зеркалом, отражение поворачивается к зрителю
@functools.lru_cache(None)
def glass_np(j):
    x0, y0, x1, y1 = NICHE_IN[j]
    w_, h_ = x1 - x0, y1 - y0
    yy, xx = np.mgrid[0:h_, 0:w_] / np.array([h_, w_], np.float32)[:, None, None]
    base = np.array([16, 18, 26], np.float32) * (1 - yy[..., None] * 0.4) + np.array([30, 10, 18], np.float32) * yy[..., None] * 0.5
    streak = np.exp(-((xx - yy * 0.6 - 0.15) / 0.05) ** 2) * 50 + np.exp(-((xx - yy * 0.6 - 0.32) / 0.02) ** 2) * 30
    return base + streak[..., None]


def creepy_mirror(cv, t):
    k = creepy_k(t)
    if k <= 0:
        return
    x0, y0, x1, y1 = NICHE_IN[0]
    w_, h_ = x1 - x0, y1 - y0
    m = niche_mask(0) * k
    reg = cv[y0:y1, x0:x1, :3]
    reg[:] = reg * (1 - m) + glass_np(0) * m
    im, s = M5.mirror_frame(t, int(w_ * 1.08))
    a = np.asarray(im, np.float32)
    ox = (w_ - a.shape[1]) // 2
    oy = -int(40 * s / 0.6)
    lay = np.zeros((h_, w_, 4), np.float32)
    sx0, sy0 = max(0, -ox), max(0, -oy)
    dx0, dy0 = max(0, ox), max(0, oy)
    ww = min(a.shape[1] - sx0, w_ - dx0)
    hh = min(a.shape[0] - sy0, h_ - dy0)
    lay[dy0:dy0 + hh, dx0:dx0 + ww] = a[sy0:sy0 + hh, sx0:sx0 + ww]
    rgb = lay[..., :3]
    g = rgb.mean(-1, keepdims=True)
    rgb = rgb * 0.55 + g * 0.25 + np.array([18, 4, 14], np.float32)      # холодное, чуть красноватое отражение
    al = lay[..., 3:4] / 255 * 0.85 * ease((t - M5.MIRROR_T0 + 0.1) / 0.35) * m
    reg[:] = reg * (1 - al) + rgb * al
    # светящиеся глаза отражения (после поворота головы)
    e = ease((t - M5.MIRROR_T0 - 1.2) / 0.5) * k
    if e > 0:
        for ex in (0.40, 0.60):
            put(cv, tinted_glow((210, 60, 120)), x0 + w_ * ex, y0 + h_ * 0.36, 0.16, 0.8 * e * (0.8 + 0.2 * math.sin(t * 9)))
    put(cv, tinted_glow((180, 190, 230)), x0 + w_ * 0.25, y0 + h_ * 0.2, 0.5, 0.12 * k)      # блик стекла


# ---- наклейки ChatGPT: эмоции над Митой и плавающие предметы роскоши
@functools.lru_cache(None)
def sticker(sheet, i, size):
    im = np.array(Image.open(HERE / 'input' / 'decor' / f'{sheet}.png').convert('RGB'))
    cw, ch = im.shape[1] / 3, im.shape[0] / 3
    r, c = divmod(i, 3)
    cell = im[int(r * ch):int((r + 1) * ch), int(c * cw):int((c + 1) * cw)]
    k = Image.fromarray(M5.key(cell))
    k = k.crop(k.getbbox())
    s = size / max(k.size)
    return k.resize((round(k.width * s), round(k.height * s)), Image.LANCZOS)


EMO = {'?': 0, '!': 1, 'heart': 2, 'bulb': 3, 'sweat': 4, 'puff': 5, 'spiral': 6, 'sparkle': 7, 'dots': 8}
REACT = [(0.35, '?'), (E.HOOK_PRICE + 0.4, '!'), (M5.SW + 0.5, 'sparkle'), (E.CARD_SHOW + 0.2, '!'),
         (E.PUMP_BLACK + 0.25, 'heart'), (E.LOCKET_HIT + 0.15, '!'), (E.LOCKET_HIT + 1.5, 'spiral'), (E.CREEPY + 0.15, 'dots'),
         (E.GACHA[0], 'sweat'), (E.TEASE + 0.2, '?'), (E.DEMAND + 0.4, 'bulb'), (E.ICONS[1] + 0.1, 'sparkle'),
         (E.GLOW_SHOW + 0.1, 'heart'), (E.KICK - 0.1, 'puff'), (E.PRICE_UP + 0.1, '!'), (E.OUTRO_LUX + 0.4, 'heart'),
         (E.OUTRO_PILL + 0.1, '?')]


def reactions(cv, t):
    for t0, kind in REACT:
        k = t - t0
        if not 0 <= k < 1.4:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 1.0) / 0.4))
        pop = fx.ease_out_back(fx.clamp01(k / 0.35))
        x = 618 + 5 * math.sin(t * 3)
        y = M5.FOOT - M5.MH + 10 - 30 * ease(k / 1.4) + (M5.hang_dy(t) if M3.scene_of(t)[0] == 'hang' else 0)
        rot = (-0.12 if kind not in ('spiral',) else -t * 3.0) + 0.06 * math.sin(t * 5)
        put(cv, sticker('emotes', EMO[kind], 112), x, y, 0.6 + 0.4 * pop, a, rot)


OBJ = {'diamond': 0, 'crown': 1, 'cash': 2, 'tag': 3, 'arrow': 4, 'coins': 5, 'dice': 6, 'ringbox': 7, 'flame': 8}
FLOAT_OBJ = {'hook': ('diamond', 'cash'), 'spin': ('crown', 'diamond'), 'card': ('diamond', 'crown'), 'pumpkin': ('tag', 'coins'),
             'jump': ('ringbox', 'cash'), 'rare': ('dice', 'dice'), 'show': ('crown', 'flame'), 'phone': ('diamond', 'crown'),
             'kick': ('tag', 'coins'), 'hang': ('arrow', 'coins'), 'two': ('crown', 'diamond')}


def float_objects(cv, t, sc):
    if creepy_k(t) > 0.3 or sc == 'creepy':
        return
    t0 = dict(M3.SCENES)[sc]
    t1 = ([s for n, s in M3.SCENES if s > t0] + [DUR + 5])[0]
    for side, name in enumerate(FLOAT_OBJ.get(sc, ())):
        a = appear(t, t0 + 0.15 + 0.2 * side, 0.4) * (1 - appear(t, t1 - 0.3, 0.3))
        if a <= 0:
            continue
        x = (100, 980)[side] + 10 * math.sin(t * 0.9 + side * 2)
        y = 372 + 16 * math.sin(t * 1.3 + side * 1.7)
        rot = 0.12 * math.sin(t * 0.8 + side) + (0.5 * math.sin(t * 2.2) if name == 'dice' else 0)
        put(cv, tinted_glow((255, 215, 150)), x, y, 0.42, 0.25 * a)
        put(cv, sticker('objects', OBJ[name], 128), x, y, 0.6 + 0.4 * pop_in(t, t0 + 0.15 + 0.2 * side), a, rot)


def camera(t):
    """v5: камера почти неподвижна (без наездов и тряски) — Мита не дёргается; лёгкий «вдох» кадра."""
    return 1.0 + 0.006 * math.sin(t * 0.5), 540.0, 1100.0, 3 * math.sin(t * 0.37), 2 * math.sin(t * 0.29)


GLITCH = [  # (время содержания, длительность, сила, красный)
    (E.CREEPY - 0.04, 0.24, 1.0, True),
    (E.CREEPY + 0.95, 0.07, 0.4, True),
    (E.CREEPY_END - 0.06, 0.2, 1.0, True),
]


def spin_flash(cv, t):
    u = (t - M5.SW + 0.06) / 0.5
    if 0 <= u < 1:
        a = (1 - u) ** 1.6 * min(1.0, u * 12 + 0.3)
        put(cv, tinted_glow((255, 236, 200)), 540, M5.FOOT - M5.MH * 0.5, 2.0, 0.9 * a)
        put(cv, tinted_glow((255, 255, 255)), 540, M5.FOOT - M5.MH * 0.55, 1.1, a)
    sparkles(cv, t, M5.SW - 0.05, 540, M5.FOOT - M5.MH * 0.55, 380, 18, GOLD)


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    sc = M3.scene_of(t)[0]
    cre = creepy_k(t)
    if cre < 0.99:
        scene_hook(cv, t)
        scene_x7(cv, t)
        scene_pumpkin(cv, t)
        scene_locket(cv, t)
        scene_tease(cv, t)
        scene_glow(cv, t)
        scene_demand(cv, t)
        scene_plain(cv, t)
        scene_price(cv, t)
        scene_outro(cv, t)
    creepy_mirror(cv, t)
    float_objects(cv, t, sc)
    if t != AD_STOP:
        if cre > 0:
            base = cv.copy()
            M5.draw(cv, t)
            cv[:] = base + (cv - base) * (1 - 0.45 * cre)          # в жуть настоящая Мита в полутьме
        else:
            M5.draw(cv, t)
    spin_flash(cv, t)
    cv = apply_camera(cv, t)
    if cre < 0.5:
        reactions(cv, t)
        headline(cv, t)
        progress(cv, t)
        if sc not in ('pumpkin',):
            side_panels(cv, t)
    else:
        if t < E.CREEPY + 1.4:
            reactions(cv, t)
    if not (AD_STOP - 0.02 <= t < AD_STOP + 0.1):
        subtitles(cv, t)
    img = np.clip(cv[..., :3], 0, 255).astype(np.uint8)
    g = glitch_at(t)
    if g:
        img = glitch(img, g[0], g[1], int(t * 60))
    return img


def out_frame(t, i=None):
    return np.clip(ad_overlay(BR.render(render_at, t, i).astype(np.float32), t), 0, 255).astype(np.uint8)


def frame_bytes(i):
    return out_frame(i / FPS, i).tobytes()


M3.bind(sys.modules[__name__])


if __name__ == '__main__':
    if '--out' in sys.argv:
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[sys.argv.index('--out') + 1].split(','):
            Image.fromarray(out_frame(float(s))).save(out / f'o{float(s):06.2f}.png')
            print('o', s)
        raise SystemExit
    frames.cli(out_frame, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
