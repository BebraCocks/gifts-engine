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
def background(t):
    sc = M3.scene_of(t)[0]
    if sc == 'creepy':
        return creepy_bg(t)
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
        a = appear(t, t0, 0.3) * (1 - appear(t, t1 - 0.25, 0.25))
        if a <= 0:
            continue
        y = 150 + 10 * (1 - a)
        im = text(s, 52, 'Heavy', WHITE if dark else INK, dark)
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
        y = 340 + j * 205
        s = 0.5 * (0.6 + 0.4 * pop_in(t, tj))
        for side, c in enumerate((L, R)):
            x = 170 + side * 470
            put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.5), x, y + 8, s, a)
            put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - tj), x, y, s, a)
            put(cv, text(c['gift'], 20, 'Heavy'), x, y - 92, 1.0, a)
            put(cv, text(rub(c['rub']), 34, 'Heavy', WINE if side else MUTED), x + 190, y, 1.0, a)
    # кекс, который Мита держит, — крупно сверху (как плитка тыквы)
    a2 = appear(t, E.CARD_GRAB + 0.15, 0.35) * (1 - appear(t, E.PUMPKIN - 0.35, 0.3))
    if a2 > 0:
        c = lot('Whip Cupcake', 'black_floor')
        s2 = 0.78 * (0.7 + 0.3 * pop_in(t, E.CARD_GRAB + 0.15)) * (1 + 0.02 * beat_pulse(t, 8))
        put(cv, tinted_glow((255, 210, 140)), 540, 470, 1.25 * s2, a2 * (0.25 + 0.1 * math.sin(t * 3)))
        put(cv, fx.soft_shadow(TILE, TILE, 46, 26, 0.6), 540, 470 + 14 * s2, s2, a2)
        put(cv, gift_tile(c['gift'], c['model'], c['backdrop'], TILE, t - E.CARD_GRAB), 540, 470, s2, a2)
        put(cv, text(c['gift'], 26, 'Heavy'), 540, 470 - 150 * s2 - 26, 1.0, a2)
        put(cv, text(rub(c['rub']), 40, 'Heavy', WINE), 540, 470 + 150 * s2 + 34, 1.0, a2)
        put(cv, upill('на чёрном фоне', WINE, 24, WHITE), 540, 470 + 150 * s2 + 86, 1.0, a2)


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
    flip_tile(cv, t, 540, 420, s, a, E.PUMP_BLACK - 0.2, lo, PUMP_HI)
    put(cv, text('Mad Pumpkin', 26, 'Heavy'), 540, 420 - 150 * s - 26, 1.0, a)
    k = fx.clamp01((t - (E.PUMP_BLACK - 0.2)) / 0.7)
    price = lo['rub'] + (PUMP_HI['rub'] - lo['rub']) * ease(k)
    col = WINE if k > 0.5 else MUTED
    if t >= E.PUMP_CHEAP - 0.1:
        put(cv, text(rub(int(round(price / 10) * 10)), 40, 'Heavy', col), 540, 420 + 150 * s + 34, 1.0, a * appear(t, E.PUMP_CHEAP - 0.1, 0.25))
    lab = 'на чёрном фоне' if k > 0.5 else 'обычная'
    put(cv, upill(lab, WINE if k > 0.5 else (226, 220, 238), 24, WHITE if k > 0.5 else INK), 540, 420 + 150 * s + 86, 1.0,
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
    put(cv, qmark_tile(), 540, 520, 1.1 * (1 + 0.04 * math.sin(t * 6)), a, math.sin(t * 3) * 0.05)


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
    x0, x1, y = 230, 850, 300
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
    c = lot('Neko Helmet', 'floor')
    a = appear(t, E.PLAIN + 0.05, 0.3)
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
    txt_panel(LX, 0.9, E.SPIN - 0.3, 'обычный фон', '438 ₽', 'Whip Cupcake', MUTED)
    txt_panel(RX, E.HOOK_PRICE + 0.4, E.SPIN - 0.3, 'чёрный фон', '2 452 ₽', 'Whip Cupcake')
    txt_panel(LX, E.X7 + 0.6, E.PUMPKIN, 'коллекций', '121', 'с чёрным фоном')
    txt_panel(RX, E.X7 + 1.0, E.PUMPKIN, 'чёрный фон', 'дороже', 'почти везде')
    txt_panel(LX, E.LOCKET + 0.6, E.CREEPY, 'самый дешёвый', '149 тыс', 'Heart Locket')
    txt_panel(RX, E.LOCKET_HIT + 0.9, E.CREEPY, 'на чёрном', '17,5 млн', 'цена продавца')
    txt_panel(LX, E.GACHA[1], E.TEASE, 'чёрный', 'не редкий', 'как бордовый')
    txt_panel(RX, E.GACHA[2], E.TEASE, 'выпадает', 'так же', 'как медный')
    txt_panel(LX, E.TEASE + 0.3, AD_STOP + 0.12, 'не редкость', '?', 'тогда что')
    txt_panel(RX, E.TEASE + 0.6, AD_STOP + 0.12, 'платят', 'больше', 'за что?')
    txt_panel(LX, E.DEMAND + 0.4, E.GLOW, 'чёрный цвет', 'люкс', 'цвет статуса')
    txt_panel(RX, E.DEMAND + 0.8, E.GLOW, 'чёрное', 'хотят', 'все')
    txt_panel(LX, E.GLOW + 0.4, E.PLAIN, 'на чёрном', 'ярче', 'контраст')
    txt_panel(RX, E.GLOW_PHONE, E.PLAIN, 'тёмная тема', 'телеграм', 'фон сливается')
    txt_panel(LX, E.PLAIN + 0.4, E.PRICE, 'обычный фон', '3 940 ₽', 'Neko Helmet', MUTED)
    txt_panel(RX, E.PLAIN + 0.9, E.PRICE, 'на чёрном', '38 528 ₽', 'Neko Helmet')
    txt_panel(RX, E.PRICE_UP, E.OUTRO, 'продавцы', 'цена ↑', 'не снижают')
    txt_panel(LX, E.OUTRO_MIN + 0.3, DUR + 1, 'выбирай', 'люкс', 'на чёрном')
    txt_panel(RX, E.OUTRO_PILL, DUR + 1, 'или', 'минимум', 'на зелёном', MUTED)


# ------------------------------------------------------------------ реклама: Мита сидит под баннером на огромном кексе
@functools.lru_cache(None)
def big_cup():
    c = lot('Whip Cupcake', 'black_floor')
    return lottie.frame(model_path(c['gift'], c['model']), 0.0, size=560)


def ad_overlay(c, t):
    """Во время рекламы Мита стоит внизу, под баннером, и смотрит его с попкорном (баннер ничем не закрыт)."""
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    u = max(0.0, bt)
    if bt > BR.B - 1.8:
        k = ease((bt - (BR.B - 1.8)) / 0.45)
        fr = anim.morph(anim.pingpong_name(M3.POP, BR.B - 1.8, 3.2), 'pop_wow', k)
    else:
        fr = anim.loop(M3.POP, u, 3.2)
    put(cv, M3.shadow_sprite(), 540, 1898, 0.6, 0.6 * a)
    by, _ = anim.breathe(t)
    M3.put_mita(cv, fr, 540, 1900, 0.46, 988, a, sy=by, shadow=False, rot=0.006 * math.sin(t * 0.9))
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


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    sc = M3.scene_of(t)[0]
    if sc != 'creepy':
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
        wind(cv, t, False)
    if t != AD_STOP:                         # на застывшем кадре рекламы Миты нет — она под баннером
        action_fx(cv, t, False)
        draw_mita(cv, t)
        action_fx(cv, t, True)
    if sc != 'creepy':
        wind(cv, t, True)
    cv = apply_camera(cv, t)
    if sc != 'creepy':
        headline(cv, t)
        if sc not in ('pumpkin',):
            side_panels(cv, t)
    if not (AD_STOP - 0.02 <= t < AD_STOP + 0.1):          # на застывшем кадре рекламы субтитров нет
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
