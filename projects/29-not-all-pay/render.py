"""29-not-all-pay: «не все подарки окупаются» — слева цена в магазине (★, ≈ $), справа сейчас (★, ≈ $) + настоящая вещь на эту сумму."""
import functools
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw
import banner
import captions
import frames
import fx
import gifts_api
import lottie
import config
from script import LINES
from timeline import DUR, ON, END, KEY
from words import WORDS
from events import AD_STOP, E

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2)

BG, WHITE, GREY, DIM, ACC = config.BACKGROUND, config.WHITE, config.GREY, config.LINE, config.ACCENT
SURF = config.SURFACE
STAR = config.STAR
GAIN = config.GAIN
LOT = {k: str(gifts_api.model_file(g, m, 'json')) for k, (g, m) in config.GIFTS.items()}
MINI = [str(gifts_api.model_png(g, m, 256)) for g, m in config.GIFTS.values()]
SRC = (78, 86, 122)                      # source lines

def cl(x):
    return min(1.0, max(0.0, x))


def sm(a, b, t):
    """0→1 smoothly between a and b."""
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def lerp(a, b, k):
    return a + (b - a) * k


def spr(t0, t, f=2.0, z=0.55):
    return fx.spring(t - t0, f, z) if t > t0 else 0.0


@functools.lru_cache(None)
def _bg():
    # Flat graphite: a vignette at this darkness steps by 1 level in 8-bit video and shows rings (v1, 2026-11-06).
    return np.broadcast_to(np.asarray(BG, np.float32), (H, W, 3)).copy()


@functools.lru_cache(4096)
def label(s, size, weight, color):
    """Text sprite whose ink box is centred in the image (so warp centres the letters, not the line box)."""
    f = fx.font(weight, size)
    l, t, r, b = f.getbbox(s, anchor='ls')
    pad = 6
    im = Image.new('RGBA', (int(r - l) + 2 * pad, int(b - t) + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - l, pad - t), s, font=f, fill=color + (255,), anchor='ls')
    return im


def text(c, s, size, weight, color, cx, cy, a=1.0, sc=1.0, left=False):
    if a <= 0.004 or sc <= 0.01:
        return
    im = label(s, size, weight, color)
    if im.width * sc > 1000:                    # never wider than the frame minus gutters
        sc = 1000 / im.width
    if left:
        cx += im.width * sc / 2
    fx.over(c, fx.warp(im, cx, cy, sc), a)


def put(c, im, cx, cy, sc=1.0, a=1.0, rot=0.0):
    if a > 0.004 and sc > 0.01:
        fx.over(c, fx.warp(im, cx, cy, sc, sc, rot), a)


def partial(pts, p):
    if p >= 0.999:
        return pts
    seg = [math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1)]
    goal, out = sum(seg) * cl(p), [pts[0]]
    for k, d in enumerate(seg):
        if goal <= d:
            q = goal / d if d else 0
            out.append((lerp(pts[k][0], pts[k + 1][0], q), lerp(pts[k][1], pts[k + 1][1], q)))
            return out
        goal -= d
        out.append(pts[k + 1])
    return out


def _box(pts, pad):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(0, min(xs) - pad), max(0, min(ys) - pad), min(W, max(xs) + pad), min(H, max(ys) + pad))


def stroke(c, pts, color, width=3.0, p=1.0, a=1.0):
    if p <= 0.003 or a <= 0.004:
        return
    pts = partial(pts, p)
    if len(pts) < 2:
        return

    def draw(d, m, S):
        q = [m(x, y) for x, y in pts]
        r = width * S / 2
        d.line(q, fill=color + (255,), width=max(1, round(width * S)), joint='curve')
        for x, y in (q[0], q[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=color + (255,))
    fx.over(c, fx.draw_rgba(_box(pts, width * 2 + 4), draw), a)


def fill(c, pts, color, a=1.0):
    if a <= 0.004:
        return
    fx.over(c, fx.draw_rgba(_box(pts, 4), lambda d, m, S: d.polygon([m(x, y) for x, y in pts], fill=color + (255,))), a)


def disc(c, cx, cy, r, color, a=1.0):
    if a > 0.004 and r > 0.5:
        fx.over(c, fx.draw_rgba((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2),
                                lambda d, m, S: d.ellipse([*m(cx - r, cy - r), *m(cx + r, cy + r)],
                                                          fill=color + (255,))), a)


def rrect(c, x0, y0, x1, y1, r, color, a=1.0, outline=None, width=0):
    if a <= 0.004:
        return
    fx.over(c, fx.draw_rgba((x0 - 3, y0 - 3, x1 + 3, y1 + 3), lambda d, m, S: d.rounded_rectangle(
        [*m(x0, y0), *m(x1, y1)], r * S, fill=None if color is None else color + (255,),
        outline=None if outline is None else outline + (255,), width=round(width * S))), a)


# ------------------------------------------------------------------ shapes (point lists in frame space)
def circle_pts(cx, cy, r, n=96, start=-90):
    return [(cx + r * math.cos(math.radians(start + 360 * k / n)), cy + r * math.sin(math.radians(start + 360 * k / n)))
            for k in range(n + 1)]


def rrect_pts(x0, y0, x1, y1, r, n=10):
    """Perimeter from the top centre, clockwise."""
    cx = (x0 + x1) / 2
    pts = [(cx, y0)]
    for (ax, ay, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        pts += [(ax + r * math.cos(math.radians(a0 + 90 * k / n)), ay + r * math.sin(math.radians(a0 + 90 * k / n)))
                for k in range(n + 1)]
    return pts + [(cx, y0)]


def heart_pts(cx, cy, s, n=90):
    pts = []
    for k in range(n + 1):
        u = 2 * math.pi * k / n
        x = 16 * math.sin(u) ** 3
        y = 13 * math.cos(u) - 5 * math.cos(2 * u) - 2 * math.cos(3 * u) - math.cos(4 * u)
        pts.append((cx + x * s / 17, cy - y * s / 17 - s * 0.08))
    return pts


def share_pts(cx, cy, s):
    shape = [(0.05, -0.42), (0.47, -0.06), (0.05, 0.30), (0.05, 0.12), (-0.12, 0.12), (-0.30, 0.20), (-0.46, 0.40),
             (-0.44, 0.14), (-0.32, -0.08), (-0.12, -0.20), (0.05, -0.22), (0.05, -0.42)]
    return [(cx + x * s, cy + y * s) for x, y in shape]


def bubble_pts(cx, cy, s, n=80):
    pts = []
    for k in range(n + 1):
        ang = -90 + 360 * k / n
        if 108 < ang < 128:
            if not any(p == 'tip' for p in pts):
                pts.append('tip')
            continue
        pts.append((cx + 0.46 * s * math.cos(math.radians(ang)), cy - 0.06 * s + 0.36 * s * math.sin(math.radians(ang))))
    i = pts.index('tip')
    pts[i] = (cx - 0.40 * s, cy + 0.44 * s)
    return pts


def check_pts(cx, cy, s):
    return [(cx - 0.26 * s, cy + 0.02 * s), (cx - 0.07 * s, cy + 0.20 * s), (cx + 0.28 * s, cy - 0.18 * s)]


def pin(c, cx, cy, s, color, a=1.0, rot=-0.5):
    """A push pin: head disc, collar and needle, rotated."""
    cs, sn = math.cos(rot), math.sin(rot)

    def P(x, y):
        return (cx + (x * cs - y * sn) * s, cy + (x * sn + y * cs) * s)
    fill(c, [P(-0.30, -0.55), P(0.30, -0.55), P(0.22, -0.20), P(0.40, 0.0), P(-0.40, 0.0), P(-0.22, -0.20)], color, a)
    stroke(c, [P(0, 0), P(0, 0.55)], color, 3.5, a=a)




# ------------------------------------------------------------------ background: midnight ink + a faint glow
@functools.lru_cache(None)
def _bg():
    """Flat ink with a very soft glow behind the hero. Static dither noise (±0.6) keeps 8-bit video free of rings."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - 540) ** 2 + ((y - 760) * 0.8) ** 2) / 820
    g = np.clip(1 - d, 0, 1) ** 2
    lift = np.asarray((5, 7, 18), np.float32)
    img = np.asarray(BG, np.float32) + g[..., None] * lift
    img += np.random.default_rng(16).uniform(-0.6, 0.6, (H, W, 1)).astype(np.float32)
    return img


@functools.lru_cache(64)
def mini(i, size):
    im = Image.open(MINI[i % len(MINI)]).convert('RGBA')
    return im.resize((size, size), Image.LANCZOS)


def gift(c, path, t, cx, cy, size, sc=1.0, a=1.0, rot=0.0, off=0.0):
    if a > 0.004 and sc > 0.01:
        put(c, lottie.frame(path, t, size=size, offset=off), cx, cy, sc, a, rot)


def win(t, t_in, t_out, din=0.35, dout=0.3):
    """(alpha, k_in, k_out) of a shot visible between t_in and t_out."""
    ki = sm(t_in, t_in + din, t)
    ko = sm(t_out, t_out + dout, t) if t_out is not None else 0.0
    return ki * (1 - ko), ki, ko


def mix(c1, c2, k):
    return tuple(int(lerp(a, b, k)) for a, b in zip(c1, c2))




def rot_pts(pts, cx, cy, ang):
    cs, sn = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * cs - (y - cy) * sn, cy + (x - cx) * sn + (y - cy) * cs) for x, y in pts]

def comment_field(c, t, t0, typed, y=1080):
    k = sm(t0 - 0.1, t0 + 0.3, t)
    if k <= 0.004:
        return
    y = y + 30 * (1 - k)
    rrect(c, 120, y - 56, 960, y + 56, 56, SURF, k, outline=mix(DIM, ACC, k), width=3)
    n = int(len(typed) * cl((t - t0 - 0.4) / 0.8))
    f = fx.font('Medium', 38)
    s = typed[:n] if n else 'Добавить комментарий…'
    text(c, s, 38, 'Medium', WHITE if n else GREY, 175, y, k, left=True)
    cx = 178 + (f.getlength(typed[:n]) if n else 0)
    if (t * 2.2) % 1 < 0.6 or 0 < n < len(typed):
        rrect(c, cx, y - 26, cx + 4, y + 26, 2, ACC, k)
    stroke(c, bubble_pts(900, y + 2, 56), ACC, 3, 1, k)


def counter(v, step=1):
    n = int(round(v / step) * step)
    return f'{n:,}'.replace(',', ' ')

def arrow(c, x0, y0, x1, y1, p, a=1.0, color=None, width=4):
    color = color or GREY
    stroke(c, [(x0, y0), (x1, y1)], color, width, p, a)
    if p > 0.6:
        ang = math.atan2(y1 - y0, x1 - x0)
        k = cl((p - 0.6) / 0.4)
        L = 22
        for s in (-1, 1):
            stroke(c, [(x1, y1), (x1 - L * math.cos(ang + s * 0.6), y1 - L * math.sin(ang + s * 0.6))], color, width, k, a)


def pop(t0, t, f=1.8, z=0.55):
    return spr(t0, t, f, z) if t > t0 else 0.0


def price(c, t, t0, s, size, color, cx, cy, a):
    k = pop(t0 - 0.1, t)
    if k > 0:
        text(c, s, size, 'Heavy', color, cx, cy + 20 * (1 - k), a * cl(k * 2), lerp(0.8, 1, k) *
             (1 + 0.06 * fx.bump(t - t0 - 0.2, 3, 7)))




# ------------------------------------------------------------------ captions (gift scenes only)
ACC_WORDS = {'125', 'тысяч!', 'тысячи!', '3600.', 'AirTag.', 'меньше', '900.', 'не', 'хватит.', 'полумиллиона!', 'MacBook.',
             '22', 'AirPods', 'Pro.', 'Switch.'}


def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC_WORDS, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(len(LINES)) if WORDS[k]], width=900, top=1480, size=50,
                        weight='Semibold', max_lines=2, color=WHITE, accent_color=STAR, shadow=False, fade_out=0.2,
                        rise=10)

def shake(t, t0, amp=10):
    d = t - t0
    if d < 0 or d > 0.45:
        return 0.0, 0.0
    e = amp * (1 - d / 0.45) ** 2
    return e * math.sin(d * 70), e * math.cos(d * 55)


USD = 0.015                                   # $ per Star (Fragment: 1 000 ★ = $15, 07.11.2026)
PHOTO_DIR = paths.CACHE / 'photos29'
PHOTOS = {   # kind: (file, crop box or None, source page)
    'switch2': ('switch2.png', None, 'nintendo.com'),
    'airtag': ('airtag.jpg', (120, 120, 680, 680), 'apple.com'),
    'charger': ('charger.jpg', (90, 40, 710, 760), 'apple.com'),
    'mba': ('mba.jpg', (300, 150, 900, 480), 'apple.com'),
    'airpods': ('airpods.jpg', (40, 40, 760, 760), 'apple.com'),
    'lada': ('lada.jpg', (60, 60, 1900, 1240), 'Wikimedia Commons, CC0'),
}


def usd(v):
    if v < 1:
        return ('≈ $%.2f' % v).replace('.', ',')
    if v < 20:
        return ('≈ $%.2f' % v).replace('.', ',').replace(',00', '')
    return '≈ $' + counter(v)


def stars(v):
    return counter(v) + ' ★'


@functools.lru_cache(16)
def photo(kind, w, h, fit='contain'):
    f, crop, _ = PHOTOS[kind]
    im = Image.open(PHOTO_DIR / f).convert('RGBA')
    if crop:
        im = im.crop(crop)
    if fit == 'cover':
        s = max(w / im.width, h / im.height)
    else:
        s = min(w / im.width, h / im.height)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    if fit == 'cover':
        x0, y0 = (im.width - w) // 2, (im.height - h) // 2
        im = im.crop((x0, y0, x0 + w, y0 + h))
    return im


@functools.lru_cache(8)
def rounded(kind, w, h, r):
    im = photo(kind, w, h, 'cover').copy()
    m = Image.new('L', (w * 3, h * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 3 - 1, h * 3 - 1], r * 3, fill=255)
    im.putalpha(m.resize((w, h), Image.LANCZOS))
    return im


# gift scenes: key: (n, title, ru name, store ★, now ★, then $, now $, thing)
SCENES = {
    'p1': (1, 'Heart Locket', 'Медальон-сердце · вышел 14.02.2025', 10000, 125000, 150, 1875,
           ('switch2', 3, 'МОЖНО КУПИТЬ', ['3 × Nintendo', 'Switch 2'], '$549,99 за штуку', False)),
    'p2': (2, 'Bonded Ring', 'Парные кольца · вышли 14.02.2025', 5000, 3600, 75, 54,
           ('airtag', 1, 'ХВАТИТ ЛИШЬ НА', ['AirTag'], '$29', False)),
    'p3': (3, 'Top Hat', 'Цилиндр · вышел 23.02.2025', 1000, 880, 15, 13.24,
           ('charger', 1, 'НЕ ХВАТИТ ДАЖЕ НА', ['Зарядку', 'Apple 20 Вт'], '$19', True)),
    'p4': (4, 'Plush Pepe', 'Плюшевый Пепе · вышел 01.12.2024', 2000, 533000, 30, 7997,
           ('mba', 6, 'МОЖНО КУПИТЬ', ['6 × MacBook', 'Air'], '$1 299 за штуку', False)),
    'p5': (5, 'Scared Cat', 'Испуганный кот · вышел 29.10.2024', 25, 22000, 0.375, 330,
           ('airpods', 1, 'МОЖНО КУПИТЬ', ['AirPods Pro 3'], '$249', False)),
}
ORDER = ['p1', 'p2', 'p3', 'p4', 'p5', 'total']
SRC_LINE = 'магазин: telegifter.ru · сейчас: самый дешёвый на Fragment, 07.11.2026 · 1 ★ ≈ $0,015 · цена вещи: {}'


def verdict(now, then):
    r = now / then
    if r >= 1.5:
        return '×' + (('%.1f' % r).replace('.', ',') if r < 20 else str(round(r))), GAIN
    if r >= 1.0:
        return '+%d%%' % round((r - 1) * 100), GREY
    return '−%d%%' % round((1 - r) * 100), ACC


def ring(c, t, t0, n, dy, a, col):
    kh = pop(t0, t, 1.8)
    stroke(c, circle_pts(140, 245 + dy, 62), col, 4, sm(t0, t0 + 0.5, t), a)
    text(c, str(n), 80, 'Heavy', WHITE, 140, 245 + dy, a * cl(kh * 2), lerp(0.6, 1, kh))


def value_between(then, now, p):
    """Count from the store price to today's price on a log scale (×880 must not look like a jump)."""
    return math.exp(lerp(math.log(then), math.log(now), p))


def columns(c, t, then, now, then_usd, now_usd, t_then, t_now, dy, a, col):
    YL, YV, YU = 770, 850, 915
    kl = pop(t_then - 0.1, t, 1.8)
    text(c, 'В МАГАЗИНЕ', 30, 'Semibold', GREY, 270, YL + dy, a * cl(kl * 2))
    text(c, stars(then), 72 if then < 10000 else 64, 'Heavy', STAR, 270, YV + dy, a * cl(kl * 2), lerp(0.8, 1, kl))
    text(c, usd(then_usd), 36, 'Semibold', GREY, 270, YU + dy, a * cl(kl * 2))
    arrow(c, 505, YV + dy, 565, YV + dy, sm(t_now - 0.35, t_now + 0.05, t), a, GREY, 4)
    kr = sm(t_now - 0.2, t_now + 0.1, t)
    p = fx.smooth(cl((t - t_now) / 0.7))
    v = value_between(then, now, p)
    vu = value_between(then_usd, now_usd, p)
    v = round(v, -1) if v >= 100 else round(v)
    ccol = mix(STAR, col, p)
    text(c, 'СЕЙЧАС', 30, 'Semibold', GREY, 810, YL + dy, a * kr)
    text(c, stars(v), 72 if now < 10000 else 64, 'Heavy', ccol, 810, YV + dy, a * kr, 1 + 0.06 * fx.bump(t - t_now - 0.7, 3, 7))
    text(c, usd(vu if p < 1 else now_usd), 36, 'Semibold', GREY, 810, YU + dy, a * kr)


def thing_card(c, t, t0, thing, dy, a):
    kind, count, head, lines, price_s, short = thing
    k = pop(t0 - 0.1, t, 1.8, 0.6)
    if k <= 0:
        return
    al = a * cl(k * 2)
    y0 = 1105 + dy + 40 * (1 - min(1, k))
    rrect(c, 90, y0, 990, y0 + 300, 36, SURF, al, outline=mix(DIM, ACC if short else STAR, 0.5), width=3)
    rrect(c, 110, y0 + 20, 480, y0 + 280, 26, (250, 250, 252), al)
    if count == 1:
        put(c, photo(kind, 320, 220), 295, y0 + 150, 1.0, al)
    elif count == 3:
        for j, ox in enumerate((-60, 0, 60)):
            kj = pop(t0 + 0.12 * j, t, 2.0)
            put(c, photo(kind, 230, 150), 295 + ox, y0 + 120 + 28 * j, lerp(0.6, 1, min(1, kj)), al * cl(kj * 2))
    else:
        for j in range(count):
            kj = pop(t0 + 0.08 * j, t, 2.0)
            px, py = 175 + (j % 3) * 120, y0 + 95 + (j // 3) * 115
            put(c, photo(kind, 120, 70), px, py, lerp(0.5, 1, min(1, kj)), al * cl(kj * 2))
    text(c, head, 26, 'Semibold', ACC if short else GREY, 515, y0 + 62, al, left=True)
    for j, s in enumerate(lines):
        text(c, s, 52, 'Heavy', WHITE, 515, y0 + 128 + 60 * j, al, left=True)
    text(c, price_s, 36, 'Heavy', ACC if short else STAR, 515, y0 + 128 + 60 * len(lines) + 10, al, left=True)
    if short:                                   # a red cross over the photo: the money is not enough
        kx = sm(t0 + 0.4, t0 + 0.8, t)
        stroke(c, [(150, y0 + 50), (440, y0 + 250)], ACC, 9, kx, al)
        stroke(c, [(440, y0 + 50), (150, y0 + 250)], ACC, 9, sm(t0 + 0.6, t0 + 1.0, t), al)


def stamp_v(c, t, t0, s, cx, cy, a, size, color):
    k = pop(t0, t, 2.2, 0.45)
    if k <= 0:
        return
    sc = lerp(1.5, 1.0, min(1.0, k)) * (1 + 0.04 * fx.bump(t - t0 - 0.25, 3, 7))
    im = label(s, size, 'Heavy', color)
    w, h = im.width * sc, im.height * sc
    al = a * cl(k * 2.5)
    pts = rot_pts(rrect_pts(cx - w / 2 - 22, cy - h / 2 - 14, cx + w / 2 + 22, cy + h / 2 + 14, 16, 6), cx, cy, -0.08)
    fill(c, pts, BG, al)
    stroke(c, pts, color, 5, 1, al)
    put(c, im, cx, cy, sc, al, -0.08)


def scene(c, t, key):
    n, title, sub, then, now, then_usd, now_usd, thing = SCENES[key]
    p = f'q{n}'
    t1 = E[ORDER[ORDER.index(key) + 1]]
    a, ki, ko = win(t, E[key] + 0.05, t1, dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    vtext, vcol = verdict(now, then)
    sx, sy = shake(t, E[p + '_pct'] + 0.05, 9 if vcol == ACC else 0)
    ring(c, t, E[key], n, dy, a, vcol)
    kn = sm(E[p + '_name'] - 0.2, E[p + '_name'] + 0.15, t)
    text(c, title, 62, 'Heavy', WHITE, 235, 222 + dy, a * kn, left=True)
    text(c, sub, 30, 'Semibold', GREY, 235, 282 + dy, a * kn, left=True)
    kg = pop(E[key] + 0.1, t, 1.6)
    react = sm(E[p + '_now'] - 0.1, E[p + '_now'] + 0.6, t)
    up = 1 if now > then else -1
    gift(c, LOT[key], t, 540 + sx, 520 + dy + 40 * (1 - kg) - 20 * up * react + sy, 330,
         lerp(0.6, 1.0, kg) * (1 + 0.05 * up * react), a * cl(kg * 2), rot=(-0.1 if up < 0 else 0) * react)
    columns(c, t, then, now, then_usd, now_usd, E[p + '_then'], E[p + '_now'], dy, a, vcol)
    stamp_v(c, t, E[p + '_pct'], vtext, 800 + sx, 1010 + dy + sy, a, 52, vcol)
    word = 'окупился' if vcol == GAIN else 'не окупился'
    kw = sm(E[p + '_pct'] - 0.1, E[p + '_pct'] + 0.2, t)
    text(c, word, 34, 'Heavy', vcol, 280 + sx, 1010 + dy + sy, a * kw)
    thing_card(c, t, E[p + '_thing'], thing, dy, a)
    text(c, SRC_LINE.format(PHOTOS[thing[0]][2]), 20, 'Medium', SRC, 540, 1760 + dy, a)


# ------------------------------------------------------------------ hook: the cat for 25 ★; today is a question
def hook(c, t):
    a, _, ko = win(t, -1, E['intro'], dout=0.3)
    if a <= 0.004:
        return
    dy = -80 * ko
    k0 = pop(-0.5, t, 1.6)
    text(c, 'ИСПУГАННЫЙ КОТ', 84, 'Heavy', WHITE, 540, 280 + dy, a * cl(k0 * 2), 1 + 0.05 * fx.bump(t - E['h_name'], 3, 7))
    text(c, 'Scared Cat · подарок в телеге, октябрь 2024', 34, 'Semibold', GREY, 540, 360 + dy, a * cl(k0 * 2))
    gift(c, LOT['p5'], t, 540, 640 + dy + 40 * (1 - k0), 440, lerp(0.6, 1.0, k0), a * cl(k0 * 2))
    kp = pop(E['h_then'] - 0.1, t, 1.8)
    text(c, 'В МАГАЗИНЕ', 30, 'Semibold', GREY, 280, 920 + dy, a * cl(kp * 2))
    text(c, '25 ★', 96, 'Heavy', STAR, 280, 1005 + dy, a * cl(kp * 2), lerp(0.8, 1, kp))
    text(c, usd(0.375), 36, 'Semibold', GREY, 280, 1080 + dy, a * cl(kp * 2))
    kq = pop(E['h_q'] - 0.1, t, 1.8)
    arrow(c, 500, 1005 + dy, 580, 1005 + dy, sm(E['h_q'] - 0.3, E['h_q'] + 0.1, t), a, GREY, 4)
    text(c, 'СЕЙЧАС', 30, 'Semibold', GREY, 800, 920 + dy, a * cl(kq * 2))
    pulse = 1 + 0.07 * math.sin(max(0.0, t - E['h_q']) * 7)
    text(c, '? ★', 96, 'Heavy', ACC, 800, 1005 + dy, a * cl(kq * 2), lerp(0.8, 1, kq) * pulse)
    text(c, '≈ $ ???', 36, 'Semibold', GREY, 800, 1080 + dy, a * cl(kq * 2))
    stamp_v(c, t, E['h_end'] + 0.05, 'ОТВЕТ — В КОНЦЕ', 540, 1260 + dy, a, 56, WHITE)


# ------------------------------------------------------------------ intro: «не все подарки окупаются»
def intro(c, t):
    a, ki, ko = win(t, E['intro'] + 0.1, E['p1'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'НЕ ВСЕ ПОДАРКИ', 80, 'Heavy', WHITE, 540, 470 + dy, a)
    text(c, 'ОКУПАЮТСЯ', 124, 'Heavy', ACC, 540, 600 + dy, a, 1 + 0.06 * fx.bump(t - E['i_b'], 3, 7))
    xs = [540 + (i - 2) * 190 for i in range(5)]
    for i, x in enumerate(xs):
        k = pop(E['i_a'] + 0.12 * i, t, 1.8)
        rrect(c, x - 80, 740 + dy, x + 80, 960 + dy, 32, SURF, a * cl(k * 2), outline=DIM, width=2)
        put(c, mini(i, 128), x, 820 + dy + 20 * (1 - k), lerp(0.5, 0.95, k), a * cl(k * 2))
        text(c, '?', 40, 'Heavy', STAR, x, 920 + dy, a * cl(k * 2))
    text(c, 'слева — цена в магазине · справа — сейчас', 34, 'Semibold', GREY, 540, 1050 + dy, a)


# ------------------------------------------------------------------ total: 18 025 ★ then -> what it buys today
TOTAL_STARS = sum(v[3] for v in SCENES.values())
TOTAL_THEN = TOTAL_STARS * USD
TOTAL_NOW = sum(v[6] for v in SCENES.values())


def total(c, t):
    a, ki, ko = win(t, E['total'] + 0.05, E['outro'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ПОТРАТИВ ВСЕГО', 44, 'Heavy', GREY, 540, 200 + dy, a)
    xs = [540 + (i - 2) * 180 for i in range(5)]
    for i, (x, key) in enumerate(zip(xs, ORDER[:5])):
        k = pop(E['total'] + 0.1 + 0.08 * i, t, 1.8)
        put(c, mini(i, 128), x, 310 + dy + 20 * (1 - k), lerp(0.5, 0.85, k), a * cl(k * 2))
        text(c, stars(SCENES[key][3]), 26, 'Heavy', STAR, x, 395 + dy, a * cl(k * 2))
    ks = pop(E['t_sum'] - 0.1, t, 1.8)
    text(c, stars(TOTAL_STARS), 100, 'Heavy', STAR, 540, 500 + dy, a * cl(ks * 2), lerp(0.8, 1, ks))
    text(c, usd(TOTAL_THEN), 38, 'Semibold', GREY, 540, 575 + dy, a * cl(ks * 2))
    kt = sm(E['t_today'] - 0.2, E['t_today'] + 0.1, t)
    arrow(c, 540, 615 + dy, 540, 690 + dy, sm(E['t_today'] - 0.3, E['t_today'] + 0.1, t), a, GREY, 4)
    text(c, 'СЕГОДНЯ ОНИ СТОЯТ', 34, 'Semibold', GREY, 540, 735 + dy, a * kt)
    p = fx.smooth(cl((t - E['t_today']) / 0.9))
    text(c, usd(value_between(TOTAL_THEN, TOTAL_NOW, p)), 92, 'Heavy', mix(STAR, GAIN, p), 540, 815 + dy, a * kt,
         1 + 0.05 * fx.bump(t - E['t_today'] - 0.9, 3, 7))
    kc = pop(E['t_car'] - 0.35, t, 1.6, 0.6)
    if kc > 0:
        al = a * cl(kc * 2)
        y0 = 900 + dy + 50 * (1 - min(1, kc))
        rrect(c, 90, y0, 990, y0 + 560, 40, SURF, al, outline=mix(DIM, GAIN, 0.6), width=3)
        put(c, rounded('lada', 860, 400, 28), 540, y0 + 220, lerp(0.92, 1, min(1, kc)), al)
        text(c, 'Новая Lada Granta', 54, 'Heavy', WHITE, 540, y0 + 470, al)
        text(c, '≈ 771 000 ₽ ≈ $9 400', 36, 'Heavy', GAIN, 540, y0 + 528, al)
    text(c, 'цена Lada: 110km.ru, Standard · фото: Wikimedia Commons, CC0 · подарки: Fragment, 07.11.2026', 20, 'Medium',
         SRC, 540, 1760 + dy, a)


# ------------------------------------------------------------------ bait for comments
def outro(c, t):
    a, ki, _ = win(t, E['outro'] + 0.05, None)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki)
    text(c, 'А КАКОЙ ПОДАРОК', 80, 'Heavy', WHITE, 540, 330 + dy, a, 1 + 0.06 * fx.bump(t - E['o_a'], 3, 7))
    text(c, 'КУПИЛИ БЫ ВЫ?', 104, 'Heavy', STAR, 540, 450 + dy, a, 1 + 0.06 * fx.bump(t - E['o_b'], 3, 7))
    xs = [540 + (i - 2) * 190 for i in range(5)]
    for i, (x, key) in enumerate(zip(xs, ORDER[:5])):
        k = pop(E['outro'] + 0.1 + 0.08 * i, t, 1.8)
        _, _, _, then, now, *_ = SCENES[key]
        s, col = verdict(now, then)
        rrect(c, x - 82, 580 + dy, x + 82, 830 + dy, 32, SURF, a * cl(k * 2), outline=mix(DIM, col, 0.6), width=3)
        put(c, mini(i, 128), x, 670 + dy + 20 * (1 - k), lerp(0.5, 0.95, k), a * cl(k * 2))
        text(c, s, 36 if len(s) < 6 else 30, 'Heavy', col, x, 785 + dy, a * cl(k * 2))
    text(c, 'цена в магазине → самый дешёвый на маркете сейчас', 28, 'Medium', GREY, 540, 890 + dy, a)
    comment_field(c, t, E['o_write'], 'Я бы взял Пепе за 2000 ★', y=1060)


@functools.lru_cache(None)
def _red_glow():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - 540) ** 2 + ((y - 900) * 0.7) ** 2) / 900
    return (np.clip(1 - d, 0, 1) ** 2)[..., None] * np.asarray((40, 4, 8), np.float32)


@functools.lru_cache(None)
def _green_glow():
    return _red_glow() * (np.asarray((4, 30, 16), np.float32) / np.asarray((40, 4, 8), np.float32))


def render_at(t):
    c = _bg().copy()
    for key, glow in (('q2_now', _red_glow), ('q3_now', _red_glow), ('q4_now', _green_glow), ('q5_now', _green_glow),
                      ('t_car', _green_glow)):
        g = math.exp(-((t - E[key] - 0.5) / 0.45) ** 2)
        if g > 0.01:
            c += glow() * g
    hook(c, t)
    intro(c, t)
    for key in ORDER[:-1]:
        scene(c, t, key)
    total(c, t)
    outro(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
