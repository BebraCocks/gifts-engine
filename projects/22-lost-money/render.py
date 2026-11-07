"""22-lost-money «На каких подарках вы бы потеряли деньги»: minimal 2D on a navy, almost black background. Thin lines,
one coral accent for loss and a cool blue for the peak price. Content time t -> RGB frame; RubUp via banner.Breaks."""
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
COOL = config.COOL
NAMES = (config.PEPE, config.LOCKET, config.PEACH, config.PAPAKHA, config.CAP)
LOT = {n: str(gifts_api.original_file(n, 'json')) for n in NAMES}
MINI = [str(gifts_api.original_png(n, 128)) for n in NAMES]
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




# ------------------------------------------------------------------ captions (not for the hook and the intro title)
ACC_WORDS = {'$8000.', 'Минус', 'минус', 'половина.', '$1900.', '$330.', '76', 'процентов!', '$32.', '$500', '82',
             'процента!', 'погорели?'}
COOL_WORDS = {'$16', '000,', '$4500,', '$1350…', '$150,', '$2800'}


def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC_WORDS, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(len(LINES)) if WORDS[k]], width=900, top=1350, size=52,
                        weight='Semibold', max_lines=2, color=WHITE, accent_color=ACC, shadow=False, fade_out=0.2,
                        rise=10)


def money(v):
    return '$' + counter(v)


def stamp(c, t, t0, s, cx, cy, a, size=130):
    """A loss stamp: lands from 1.5× with a spring, framed, slightly rotated."""
    k = pop(t0, t, 2.2, 0.45)
    if k <= 0:
        return
    sc = lerp(1.5, 1.0, min(1.0, k)) * (1 + 0.04 * fx.bump(t - t0 - 0.25, 3, 7))
    im = label(s, size, 'Heavy', ACC)
    w, h = im.width * sc, im.height * sc
    al = a * cl(k * 2.5)
    pts = rot_pts(rrect_pts(cx - w / 2 - 26, cy - h / 2 - 18, cx + w / 2 + 26, cy + h / 2 + 18, 18, 6), cx, cy, -0.06)
    stroke(c, pts, ACC, 5, 1, al)
    put(c, im, cx, cy, sc, al, -0.06)


def shake(t, t0, amp=10):
    d = t - t0
    if d < 0 or d > 0.45:
        return 0.0, 0.0
    e = amp * (1 - d / 0.45) ** 2
    return e * math.sin(d * 70), e * math.cos(d * 55)


def wiggle(x0, y0, x1, y1, n, seed, amp):
    """A market-like path from (x0, y0) to (x1, y1): a smooth trend plus a deterministic wobble (zero at the ends)."""
    pts = []
    for j in range(n + 1):
        u = j / n
        w = math.sin(u * math.pi) * amp * (0.6 * math.sin(u * 17 + seed) + 0.4 * math.sin(u * 41 + 2 * seed))
        pts.append((lerp(x0, x1, u), lerp(y0, y1, fx.smooth(u)) + w))
    return pts


# ------------------------------------------------------------------ hero: the cap crashes (hook)
def hook(c, t):
    a, _, ko = win(t, -1, E['i_five'] - 0.25, dout=0.3)
    if a <= 0.004:
        return
    dy = -80 * ko
    k0 = pop(-0.5, t, 1.6)
    text(c, 'КЕПКА ДУРОВА', 84, 'Heavy', WHITE, 540, 290 + dy, a * cl(k0 * 2), 1 + 0.05 * fx.bump(t - E['h_cap'], 3, 7))
    text(c, "Durov's Cap", 38, 'Semibold', GREY, 540, 370 + dy, a * cl(k0 * 2))
    fall = sm(E['h_today'] + 0.1, E['h_500'] + 0.2, t)
    sx, sy = shake(t, E['h_500'] + 0.1, 12)
    gift(c, LOT[config.CAP], t, 540 + sx, 660 + dy + 40 * fall + 40 * (1 - k0) + sy, 460,
         lerp(0.6, 1.0, k0) * lerp(1.0, 0.92, fall), a * cl(k0 * 2), rot=-0.12 * fall)
    kp = sm(E['h_3k'] - 0.15, E['h_3k'] + 0.15, t)
    v = lerp(2829, 512, fx.smooth(fall))
    col = mix(COOL, ACC, fall)
    text(c, money(v), 150, 'Heavy', col, 540 + sx, 1010 + dy, a * kp, 1 + 0.05 * fx.bump(t - E['h_3k'], 3, 7))
    text(c, 'сентябрь 2025', 36, 'Semibold', GREY, 540, 1110 + dy, a * kp * (1 - fall))
    text(c, 'сегодня', 36, 'Semibold', ACC, 540, 1110 + dy, a * fall)
    # the old price, struck through, stays small above once the number has fallen
    ko2 = sm(E['h_500'], E['h_500'] + 0.3, t)
    text(c, '$2 829', 48, 'Heavy', GREY, 540, 905 + dy, a * ko2)
    stroke(c, [(470, 908 + dy), (610, 902 + dy)], ACC, 4, ko2, a)
    stamp(c, t, E['h_500'] + 0.1, '−82%', 540, 1250 + dy, a)


# ------------------------------------------------------------------ intro: five suspects
def intro(c, t):
    a, ki, ko = win(t, E['i_five'] - 0.15, E['pepe'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'НА КАКИХ ПОДАРКАХ', 76, 'Heavy', WHITE, 540, 380 + dy, a)
    text(c, 'ВЫ БЫ ПОТЕРЯЛИ', 76, 'Heavy', WHITE, 540, 475 + dy, a)
    text(c, 'ДЕНЬГИ?', 150, 'Heavy', ACC, 540, 620 + dy, a, 1 + 0.06 * fx.bump(t - E['i_burn'], 3, 7))
    xs = (150, 345, 540, 735, 930)
    for i, x in enumerate(xs):
        k = pop(E['i_five'] + 0.12 * i, t, 1.8)
        rrect(c, x - 82, 790 + dy, x + 82, 990 + dy, 32, SURF, a * cl(k * 2), outline=DIM, width=2)
        put(c, mini(i, 128), x, 870 + dy + 20 * (1 - k), lerp(0.5, 0.95, k), a * cl(k * 2))
        kd = sm(E['i_burn'] + 0.08 * i, E['i_burn'] + 0.25 + 0.08 * i, t)
        arrow(c, x, 935 + dy, x, 975 + dy, kd, a, ACC, 4)
    text(c, 'цена в сентябре 2025  →  цена сегодня', 34, 'Semibold', GREY, 540, 1080 + dy, a)


# ------------------------------------------------------------------ places 5..1: the same card, a different crash
PLACES = {
    # key: (place, gift, ru name, peak $, now $, pct, peak label, word keys, source)
    'pepe': (5, config.PEPE, 'Плюш Пепе', 16300, 8024, '−51%', 'сен 2025', ('pe_name', 'pe_then', 'pe_now', 'pe_pct'),
             'пик: Gift Charts, 18.09.2025 · сейчас: Fragment, 07.11.2026'),
    'locket': (4, config.LOCKET, 'Сердце-медальон', 4473, 1882, '−58%', 'сен 2025',
               ('lo_name', 'lo_then', 'lo_now', 'lo_pct'), 'пик: Gift Charts, 18.09.2025 · сейчас: Fragment, 07.11.2026'),
    'peach': (3, config.PEACH, 'Драгоценный персик', 1351, 327, '−76%', 'сен 2025',
              ('pc_name', 'pc_then', 'pc_now', 'pc_pct'), 'пик: Gift Charts, 18.09.2025 · сейчас: Fragment, 07.11.2026'),
    'papakha': (2, config.PAPAKHA, 'Папаха Хабиба', 152, 32, '−79%', 'аукцион, ноя 2025',
                ('pa_name', 'pa_then', 'pa_now', 'pa_pct'), 'аукцион: ≈ $4,4 млн / 29 000 шт. · сейчас: Fragment, 07.11.2026'),
    'cap': (1, config.CAP, 'Кепка Дурова', 2829, 512, '−82%', 'сен 2025', ('cp_name', 'cp_then', 'cp_now', 'cp_pct'),
            'пик: Gift Charts, 18.09.2025 · сейчас: Fragment, 07.11.2026'),
}
ORDER = ['pepe', 'locket', 'peach', 'papakha', 'cap', 'outro']


def place(c, t, key):
    n, name, ru, then, now, pct, then_lab, (w_name, w_then, w_now, w_pct), src = PLACES[key]
    t1 = E[ORDER[ORDER.index(key) + 1]]
    a, ki, ko = win(t, E[key] + 0.05, t1, dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    sx, sy = shake(t, E[w_pct] + 0.05, 9)
    # header: place in a ring, the gift's name
    kh = pop(E[key], t, 1.8)
    stroke(c, circle_pts(150, 250 + dy, 64), ACC, 4, sm(E[key], E[key] + 0.5, t), a)
    text(c, str(n), 84, 'Heavy', WHITE, 150, 250 + dy, a * cl(kh * 2), lerp(0.6, 1, kh))
    text(c, 'МЕСТО', 24, 'Semibold', GREY, 150, 345 + dy, a * cl(kh * 2))
    kn = sm(E[w_name] - 0.15, E[w_name] + 0.15, t)
    text(c, name, 62, 'Heavy', WHITE, 245, 228 + dy, a * kn, left=True)
    text(c, ru, 36, 'Semibold', GREY, 245, 292 + dy, a * kn, left=True)
    # the gift sags when the price falls
    kg = pop(E[key] + 0.1, t, 1.6)
    sag = sm(E[w_now] - 0.1, E[w_now] + 0.6, t)
    gift(c, LOT[name], t, 540 + sx, 560 + dy + 40 * (1 - kg) + 30 * sag + sy, 380, lerp(0.6, 1.0, kg) * lerp(1, 0.94, sag),
         a * cl(kg * 2), rot=-0.09 * sag)
    # price chart: hype up to the peak, then the fall to today's floor (proportional heights)
    x0, x1, y0, y1 = 140, 940, 770, 1240
    rrect(c, x0, y0, x1, y1, 36, SURF, a)
    stroke(c, [(190, 1170 + dy), (890, 1170 + dy)], DIM, 2, 1, a)
    ytop, ybot = 880, 1160
    A = (360, ytop + dy)
    B = (860, ytop + (ybot - ytop) * (1 - now / then) + dy)
    S = (200, 1150 + dy)
    up = wiggle(S[0], S[1], A[0], A[1], 16, n * 1.7, 14)
    down = wiggle(A[0], A[1], B[0], B[1], 30, n * 2.3, 18)
    pu = sm(E[w_then] - 0.35, E[w_then] + 0.25, t)
    pd = fx.ease_in(cl((t - E[w_now] + 0.05) / 0.7))
    stroke(c, up, COOL, 5, pu, a)
    if pu > 0.97:
        disc(c, A[0], A[1], 11, COOL, a)
    stroke(c, down, ACC, 5, pd, a)
    if pd > 0.98:
        disc(c, B[0], B[1], 11, ACC, a)
    kt = pop(E[w_then] - 0.05, t, 1.8)
    text(c, money(then), 56, 'Heavy', COOL, A[0], A[1] - 52, a * cl(kt * 2), lerp(0.8, 1, kt))
    text(c, then_lab, 28, 'Semibold', GREY, A[0], 1205 + dy, a * pu)
    kn2 = pop(E[w_now] + 0.5, t, 1.8)
    text(c, money(now), 56, 'Heavy', ACC, B[0] - 20, B[1] - 52, a * cl(kn2 * 2), lerp(0.8, 1, kn2))
    text(c, 'ноя 2026', 28, 'Semibold', GREY, B[0] - 20, 1205 + dy, a * cl(kn2 * 2))
    stamp(c, t, E[w_pct] + 0.05, pct, 700 + sx, 860 + dy + sy, a, 96)
    text(c, src, 22, 'Medium', SRC, 540, 1275 + dy, a)


# ------------------------------------------------------------------ bait for comments
def outro(c, t):
    a, ki, _ = win(t, E['outro'] + 0.05, None)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki)
    text(c, 'А ВЫ НА КАКОМ', 84, 'Heavy', WHITE, 540, 300 + dy, a)
    text(c, 'ПОГОРЕЛИ?', 140, 'Heavy', ACC, 540, 430 + dy, a, 1 + 0.06 * fx.bump(t - E['o_burn'], 3, 7))
    xs = (150, 345, 540, 735, 930)
    for i, (x, key) in enumerate(zip(xs, ORDER[:5])):
        k = pop(E['outro'] + 0.1 + 0.08 * i, t, 1.8)
        hi = sm(E['o_which'] + 0.12 * i, E['o_which'] + 0.12 * i + 0.2, t) * (1 - sm(E['o_which'] + 0.12 * i + 0.4,
                                                                                    E['o_which'] + 0.12 * i + 0.8, t))
        rrect(c, x - 85, 580 + dy, x + 85, 830 + dy, 32, SURF, a * cl(k * 2), outline=mix(DIM, ACC, hi), width=3)
        put(c, mini(i, 128), x, 670 + dy + 20 * (1 - k), lerp(0.5, 0.95, k) * (1 + 0.1 * hi), a * cl(k * 2))
        text(c, PLACES[key][5], 40, 'Heavy', ACC, x, 785 + dy, a * cl(k * 2))
    text(c, 'сентябрь 2025 → ноябрь 2026, в долларах', 28, 'Medium', GREY, 540, 885 + dy, a)
    comment_field(c, t, E['o_write'], 'Мой минус: −', y=1060)


@functools.lru_cache(None)
def _red_glow():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - 540) ** 2 + ((y - 900) * 0.7) ** 2) / 900
    return (np.clip(1 - d, 0, 1) ** 2)[..., None] * np.asarray((40, 4, 8), np.float32)


def render_at(t):
    c = _bg().copy()
    for t0 in (E['h_500'] + 0.1, E['cp_pct'] + 0.05):            # the two biggest crashes flush the room red
        g = math.exp(-((t - t0 - 0.25) / 0.45) ** 2)
        if g > 0.01:
            c += _red_glow() * g
    hook(c, t)
    intro(c, t)
    for key in ORDER[:5]:
        place(c, t, key)
    outro(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
