"""Движок кадра части 1 v2: кеш плит и спрайтов (на диске — общий для процессов-рабочих), актёры с липсинком,
камера, нуарная цветокоррекция, субтитры, зелёный интерфейс системы. Сцены — render.py."""
import functools
import hashlib
import math
import os
import pickle
import wave
from collections import OrderedDict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage
import kit
import people as pp
import figure as fg
from timeline import S, E, SUBS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
W, H = 1080, 1920
SC = 1.25
CW, CH = int(W * SC), int(H * SC)                 # холст плана (запас под камеру)
CACHE = HERE / 'build' / 'v2_cache'
GREEN = (110, 255, 160)
FONT_HUD = str(HERE / 'fonts' / 'JetBrainsMono-Bold.ttf')
FONT_SUB = str(ROOT / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Semibold.otf')


# ── время ──────────────────────────────────────────────────────────────────
def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ramp(t, a, b):
    return cl((t - a) / (b - a)) if b != a else float(t >= a)


def eo(x):
    return 1 - (1 - x) ** 3


def eio(x):
    return x * x * (3 - 2 * x)


def bump(t, t0, rise=0.06, fall=0.35):
    if t < t0:
        return 0.0
    if t < t0 + rise:
        return (t - t0) / rise
    return max(0.0, 1 - (t - t0 - rise) / fall)


def mid(k):
    return (S[k] + E[k]) / 2


# ── голос → рот, моргание ─────────────────────────────────────────────────
@functools.lru_cache(None)
def envelope(key):
    with wave.open(str(HERE / 'voice' / 'clips' / f'{key}.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32).reshape(-1, 2).mean(1)
        sr = w.getframerate()
    hop = sr // 60
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    rms = np.convolve(rms, np.ones(4) / 4, 'same')
    return np.clip(rms / (np.percentile(rms, 90) + 1e-6), 0, 1.2)


def mouth(t, keys):
    for k in keys:
        if S[k] <= t < E[k]:
            env = envelope(k)
            i = int((t - S[k]) * 60)
            return float(env[i]) if 0 <= i < len(env) else 0.0
    return 0.0


def blink(t, period=3.3, seed=0):
    """1 — глаза открыты; короткие моргания с неровным шагом"""
    k = math.floor((t + seed * 0.7) / period)
    tb = k * period + 0.6 * math.sin(k * 7.3 + seed) + period * 0.5 - seed * 0.7
    v = abs(t - tb)
    return 1.0 if v > 0.09 else v / 0.09


def q(x, n):
    return round(x * n) / n


# ── кеш ───────────────────────────────────────────────────────────────────
class LRU(OrderedDict):
    def __init__(self, n):
        super().__init__()
        self.n = n

    def get_or(self, key, fn):
        if key in self:
            self.move_to_end(key)
            return self[key]
        v = fn()
        self[key] = v
        while len(self) > self.n:
            self.popitem(last=False)
        return v


_MEM = LRU(160)


def _disk(name, fn, mode):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{name}.png'
    if p.is_file():
        try:
            return Image.open(p).convert(mode)
        except Exception:
            pass
    im = fn().convert(mode)
    tmp = p.with_suffix(f'.{os.getpid()}.tmp.png')
    im.save(tmp, compress_level=1)
    os.replace(tmp, p)
    return im


def plate(name, fn):
    """фон плана: fn() -> PIL RGB (или premul float) — один раз на диск"""
    def make():
        r = fn()
        return r if isinstance(r, Image.Image) else to_pil(r).convert('RGB')
    return _MEM.get_or(('plate', name), lambda: _disk('plate_' + name, make, 'RGB'))


def sprite(name, fn):
    def make():
        r = fn()
        return r if isinstance(r, Image.Image) else to_pil(r)
    return _MEM.get_or(('spr', name), lambda: _disk('spr_' + name, make, 'RGBA'))


def to_pil(premul):
    a = np.clip(premul[..., 3:4], 0, 1)
    rgb = np.where(a > 1e-4, premul[..., :3] / np.maximum(a, 1e-4), 0)
    return Image.fromarray((np.clip(np.concatenate([rgb, a], -1), 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA')


def hkey(*parts):
    return hashlib.md5(pickle.dumps(parts)).hexdigest()[:12]


# ── актёры ─────────────────────────────────────────────────────────────────
def lit(arr, top_y, hpx, key=1.0, fog=0.0, tint=(1, 1, 1), grad=0.62, fogc=(16, 28, 36), side=0.0):
    """свет сцены на спрайте: сверху светлее (лампы под потолком), к ногам темнее; боковой ключ; туман"""
    h, w = arr.shape[:2]
    yy = (np.arange(h, dtype=np.float32)[:, None] - top_y) / max(1.0, hpx)
    L = np.clip(1.12 - grad * yy, 0.35, 1.12) * key
    if side:
        xx = np.linspace(-1, 1, w, dtype=np.float32)[None]
        L = L * np.clip(1 + side * xx * 0.35, 0.5, 1.3)
    arr[..., :3] *= L[..., None] * np.asarray(tint, np.float32)
    if fog > 0:
        arr[..., :3] = arr[..., :3] * (1 - fog) + np.asarray(fogc, np.float32) / 255 * fog * arr[..., 3:4]
    np.clip(arr, 0, 1, out=arr)
    return arr


def actor(img, name, lk, kind, x, yfloor, hpx, fc=None, t=0.0, talk=None, light=None, phase=None, kw=None,
          shadow=0.5, rot=0.0, flip=False, head_only=False, body=True):
    """рисует актёра на PIL-холсте img. talk — ключи реплик (рот по огибающей); phase — фаза позы (0..1, квантуется).
    Тело кешируется один раз, голова — по квантованному состоянию лица."""
    fc = dict(fc or {})
    kw = dict(kw or {})
    if lk['female'] and 'sw' not in kw:
        kw.update(sw=0.86, att=0.9)
    light = dict(light or {})
    if talk:
        m = mouth(t, talk)
        fc['mouth'] = q(min(0.85, m * 0.7), 6) if m > 0.08 else (fc.get('mouth') or 0.0)
    if fc.get('mouth') is None:
        fc['mouth'] = 0.0
    if 'eye' not in fc or fc.get('blink', True):
        fc['eye'] = q(fc.get('eye', 1.0) * blink(t, 3.1 + (hash(name) % 7) * 0.2, hash(name) % 5), 3)
    fc.pop('blink', None)
    ph = q(phase % 1.0, 12) if phase is not None else 0.0
    # локальные координаты: фигура в своём холсте
    j = pp.pose(0, 0, hpx, kind, t=ph * 4.2 if phase is not None else 0.0, **kw)
    u = j['u']
    box = None
    if not rot:                                  # крупные планы: рисуем только то, что попадает в холст
        xs = [v[0] for v in j.values() if isinstance(v, tuple)]
        ys = [v[1] for v in j.values() if isinstance(v, tuple)]
        bx0, by0 = min(xs) - u * 1.2, min(ys) - u * 1.4
        bx1, by1 = max(xs) + u * 1.2, max(ys) + u * 0.8
        cx0, cy0, cx1, cy1 = -x - 40, -yfloor - 40, img.width - x + 40, img.height - yfloor + 40
        if bx0 < cx0 or by0 < cy0 or bx1 > cx1 or by1 > cy1:
            box = (int(max(bx0, cx0)), int(max(by0, cy0)), int(min(bx1, cx1) - max(bx0, cx0)),
                   int(min(by1, cy1) - max(by0, cy0)))
            if box[2] <= 0 or box[3] <= 0:
                return (x + j['head'][0], yfloor + j['head'][1])
    base = (name, hkey(lk), kind, round(hpx), ph, tuple(sorted(kw.items())), tuple(sorted(light.items())), rot, flip, box)

    def body_spr():
        a, (x0, y0) = fg.render(j, lk, fc, box=box, parts='body' if not head_only else 'all')
        lit(a, -hpx - y0, hpx, **light)
        return a, (x0, y0)

    def head_spr():
        a, (x0, y0) = fg.render(j, lk, fc, parts='head')
        lit(a, -hpx - y0, hpx, **light)
        return a, (x0, y0)
    bkey = 'b' + hkey(base)
    meta = CACHE / f'meta_{bkey}.pkl'
    if body and not head_only:
        if meta.is_file():
            ox, oy = pickle.loads(meta.read_bytes())
            spr = sprite(bkey, lambda: Image.new('RGBA', (1, 1)))
        else:
            a, (ox, oy) = body_spr()
            spr = sprite(bkey, lambda: to_pil(a))
            CACHE.mkdir(parents=True, exist_ok=True)
            meta.write_bytes(pickle.dumps((ox, oy)))
        _place(img, spr, x, yfloor, ox, oy, rot, flip, shadow, hpx)
    fkey = 'h' + hkey(base, tuple(sorted((k, (v if not isinstance(v, float) else round(v, 3))) for k, v in fc.items())))
    hmeta = CACHE / f'meta_{fkey}.pkl'
    if hmeta.is_file():
        ox, oy = pickle.loads(hmeta.read_bytes())
        spr = sprite(fkey, lambda: Image.new('RGBA', (1, 1)))
    else:
        a, (ox, oy) = head_spr()
        spr = sprite(fkey, lambda: to_pil(a))
        CACHE.mkdir(parents=True, exist_ok=True)
        hmeta.write_bytes(pickle.dumps((ox, oy)))
    _place(img, spr, x, yfloor, ox, oy, rot, flip, 0, hpx)
    hx, hy = j['head']
    return (x + hx, yfloor + hy)


def _place(img, spr, x, yfloor, ox, oy, rot, flip, shadow, hpx):
    if flip:
        spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
        ox = -(ox + spr.width)
    if shadow:
        sh = Image.new('RGBA', (int(hpx * 0.6), int(hpx * 0.1)), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(0, 0, 0, int(255 * shadow)))
        sh = sh.filter(ImageFilter.GaussianBlur(hpx * 0.02))
        img.alpha_composite(sh, (int(x - sh.width / 2), int(yfloor - sh.height / 2)))
    if rot:
        w0, h0 = spr.size
        ax, ay = -ox - w0 / 2, -oy - h0 / 2
        r = math.radians(rot)
        vx, vy = ax * math.cos(r) + ay * math.sin(r), -ax * math.sin(r) + ay * math.cos(r)
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
        _paste_clip(img, spr, int(x - (spr.width / 2 + vx)), int(yfloor - (spr.height / 2 + vy)))
        return
    _paste_clip(img, spr, int(x + ox), int(yfloor + oy))


def _inside(img, spr, x, y):
    return x >= 0 and y >= 0 and x + spr.width <= img.width and y + spr.height <= img.height


def _paste_clip(img, spr, x, y):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img.width, x + spr.width), min(img.height, y + spr.height)
    if x1 <= x0 or y1 <= y0:
        return
    img.alpha_composite(spr.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def put(img, spr, cx, cy, a=1.0, scale=1.0, rot=0.0):
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BICUBIC)
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 1.0:
        spr = spr.copy()
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * a)))
    _paste_clip(img, spr, int(cx - spr.width / 2), int(cy - spr.height / 2))


def layer(fn, size=(CW, CH)):
    """рисование cairo на прозрачном слое: fn(ctx) -> PIL RGBA (распремультипликация в C)"""
    cv = kit.Canvas(*size)
    fn(cv.ctx)
    cv.surf.flush()
    return Image.frombuffer('RGBA', size, bytes(cv.surf.get_data()), 'raw', 'BGRa', 0, 1)


# ── камера ─────────────────────────────────────────────────────────────────
def cam(src, z=1.0, cx=None, cy=None, rot=0.0):
    """вырез W×H из холста плана: z — увеличение относительно «весь холст по ширине W»"""
    cx = src.width / 2 if cx is None else cx
    cy = src.height / 2 if cy is None else cy
    k = src.width / W / z
    a = math.radians(rot)
    c, s = math.cos(a) * k, math.sin(a) * k
    return src.transform((W, H), Image.AFFINE, (c, s, cx - c * W / 2 - s * H / 2, -s, c, cy + s * W / 2 - c * H / 2),
                         resample=Image.BILINEAR)


def kb(src, t, t0, t1, z0, z1, c0, c1, rot=(0, 0), ease=eio):
    u = ease(ramp(t, t0, t1))
    return cam(src, z0 + (z1 - z0) * u, c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u,
               rot[0] + (rot[1] - rot[0]) * u)


def shake(t, amp, freq=11):
    return (amp * math.sin(t * freq * 2.1) * math.sin(t * 3.3), amp * math.sin(t * freq * 1.7 + 1))


# ── нуарная цветокоррекция ─────────────────────────────────────────────────
@functools.lru_cache(None)
def _vign():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = ((xx - W / 2) / (W * 0.78)) ** 2 + ((yy - H * 0.47) / (H * 0.64)) ** 2
    return np.clip(1.06 - 0.78 * r, 0.22, 1.0)[..., None]


@functools.lru_cache(None)
def _grain(k):
    g = np.random.default_rng(100 + k).normal(0, 6.0, (H // 2, W // 2)).astype(np.float32)
    return np.kron(g, np.ones((2, 2), np.float32))[..., None]


def grade(im, t, bloom=0.7, warm=0.0):
    im = im.convert('RGB')
    a = np.asarray(im, np.float32)
    if bloom:
        sm = np.asarray(im.resize((W // 4, H // 4), Image.BILINEAR), np.float32)
        br = np.clip(sm.max(-1, keepdims=True) - 150, 0, 255) / 105 * sm
        bi = Image.fromarray(np.clip(br, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
        a += np.asarray(bi.resize((W, H), Image.BILINEAR), np.float32) * bloom
    lum = a.mean(-1, keepdims=True) * (1.8 / 255)
    a += (1 - np.minimum(lum, 1)) * np.array([-6, 3, 11], np.float32)
    if warm:
        a *= np.array([1 + 0.06 * warm, 1 + 0.01 * warm, 1 - 0.06 * warm], np.float32)
    a *= _vign()
    a += _grain(int(t * 24) % 8)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def mix(a, b, u):
    r = 10 * math.sin(math.pi * u)
    if r > 0.5:
        small = (W // 4, H // 4)
        a = a.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((W, H), Image.BILINEAR)
        b = b.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((W, H), Image.BILINEAR)
    return Image.blend(a, b, eio(u))


# ── субтитры и интерфейс ───────────────────────────────────────────────────
@functools.lru_cache(512)
def sub_spr(text):
    f = ImageFont.truetype(FONT_SUB, 40)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 30
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - bb[0], 17 - bb[1]), text, font=f, fill=(0, 0, 0, 210))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(im).text((20 - bb[0], 15 - bb[1]), text, font=f, fill=(236, 236, 232, 225))
    if im.width > 800:
        k = 800 / im.width
        im = im.resize((800, int(im.height * k)), Image.LANCZOS)
    return im


def subtitles(im, t):
    for t0, t1, text in SUBS:
        if t0 <= t < t1:
            a = ramp(t, t0, t0 + 0.1) * (1 - ramp(t, t1 - 0.1, t1))
            put(im, sub_spr(text), W / 2, 1360, a)


@functools.lru_cache(64)
def hud_font(size):
    return ImageFont.truetype(FONT_HUD, size)


def hud_text(img, x, y, s, size=34, col=GREEN, a=1.0, anchor='la', glow=True):
    """зелёные строки интерфейса «перед глазами» — со свечением"""
    f = hud_font(size)
    bb = f.getbbox(s, anchor=anchor)
    pad = 24
    lay = Image.new('RGBA', (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((pad - bb[0], pad - bb[1]), s, font=f, fill=col + (int(240 * a),), anchor=anchor)
    if glow:
        g = lay.filter(ImageFilter.GaussianBlur(8))
        img.alpha_composite(g, (int(x + bb[0] - pad), int(y + bb[1] - pad)))
    img.alpha_composite(lay, (int(x + bb[0] - pad), int(y + bb[1] - pad)))


def hud_box(img, x0, y0, x1, y1, a=1.0):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle((x0, y0, x1, y1), fill=(4, 22, 12, int(140 * a)), outline=GREEN + (int(200 * a),), width=3)
    for k in range(y0 + 6, y1, 6):                 # строки развёртки
        d.line((x0 + 3, k, x1 - 3, k), fill=(110, 255, 160, int(10 * a)))
    img.alpha_composite(lay)


def dust(img, t, n=60, seed=1, area=None, a=0.5, size=3.0, beam=None):
    """пылинки в луче света (медленный дрейф)"""
    import random
    r = random.Random(seed)
    x0, y0, x1, y1 = area or (0, 0, img.width, img.height)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(n):
        px = x0 + ((r.random() * (x1 - x0) + t * (6 + r.random() * 14) * (1 if k % 2 else -0.6)) % (x1 - x0))
        py = y0 + ((r.random() * (y1 - y0) - t * (10 + r.random() * 22)) % (y1 - y0))
        s = size * (0.4 + r.random())
        al = a * (0.4 + 0.6 * math.sin(t * (0.6 + r.random()) + k) ** 2)
        d.ellipse((px - s, py - s, px + s, py + s), fill=(230, 235, 220, int(255 * al)))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))
