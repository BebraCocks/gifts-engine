"""16-celebrity-gifts «Подарки звёзд»: minimal 2D picture. Deep midnight-ink background, thin light lines, one warm gold
accent, one idea per shot. Heroes are gifts and typography only (no faces of real people). Content time t -> RGB
frame; RubUp via banner.Breaks (same in audio.py)."""
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
SNOOP = [str(gifts_api.original_file(n, 'json')) for n in config.SNOOP]
PAPAKHA = str(gifts_api.original_file(config.KHABIB, 'json'))
CAPG = str(gifts_api.original_file(config.CAP, 'json'))
PEPE = str(gifts_api.model_file(*config.PEPE, 'json'))
MINI = [str(gifts_api.original_png(n, 128)) for n in config.MINI]
SRC = (92, 95, 128)                      # source lines

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
    lift = np.asarray((7, 7, 14), np.float32)
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


# ------------------------------------------------------------------ captions (not for the hook line)
ACC_WORDS = {'Снуп,', 'сумка,', 'сигара,', 'лоурайдер', 'Westside.', 'миллион', '$12', 'млн.', 'вторую', 'серию.',
             'Хабиб', 'папаху', '29 000', 'сутки.', 'Конор', 'Макгрегор', 'Дуров', 'собирает.', 'Plush', 'Pepe',
             '$47 000.', 'Evelone', '119', '40', 'млн', '18', 'Porsche.', 'Снупа,', 'Хабиба', 'Дурова?',
             'комментарии.', 'первый'}


def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC_WORDS, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=900, top=1350, size=52, weight='Semibold',
                        max_lines=2, color=WHITE, accent_color=ACC, shadow=False, fade_out=0.2, rise=10)


# ------------------------------------------------------------------ Snoop Dogg: hook → five collections → sold → series 2
SLOTS = [(200, 640), (540, 640), (880, 640), (370, 990), (710, 990)]
STRIP = [(540 + (i - 2) * 172, 300) for i in range(5)]
NAMES = config.SNOOP
WORD_N = ('n0', 'n1', 'n2', 'n3', 'n4')


def snoop_pose(i, t):
    """(cx, cy, scale, alpha) of Snoop collection i; sprites are 300 px."""
    if i == 0:
        k = spr(-0.05, t, 1.5, 0.55)
        cx, cy, s, a = 540.0, 900.0, lerp(1.6, 1.95, k), 1.0           # the hook: big, from the first frame
        k = sm(E['five'], E['five'] + 0.5, t)
        cx, cy, s = lerp(cx, SLOTS[0][0], k), lerp(cy, SLOTS[0][1], k), lerp(s, 1.0, k)
    else:
        t0 = E[WORD_N[i]] - 0.12
        if t < t0:
            return 0, 0, 0, 0
        k = spr(t0, t, 1.7, 0.5)
        cx, cy, s, a = SLOTS[i][0], SLOTS[i][1] + 60 * (1 - k), lerp(0.4, 1.0, k), cl(k * 2)
    s *= 1 + 0.08 * fx.bump(t - E[WORD_N[i]], 3, 7) * (t > E['five'])
    k = sm(E['sold'], E['sold'] + 0.5 + 0.04 * i, t)                       # into the top strip
    cx, cy, s = lerp(cx, STRIP[i][0], k), lerp(cy, STRIP[i][1], k), lerp(s, 0.48, k)
    k = sm(E['khabib'], E['khabib'] + 0.35, t)                              # out with the Snoop block
    cy, a = cy - 160 * k, a * (1 - k)
    return cx, cy, s, a


def snoop(c, t):
    if t > E['khabib'] + 0.5:
        return
    # hook title: whole promise visible from frame 0
    a, _, ko = win(t, -1, E['five'] - 0.05, dout=0.3)
    if a > 0.004:
        dy = -50 * ko
        b5 = 1 + 0.08 * fx.bump(t - E['five_word'], 3, 7)
        text(c, 'У СНУП ДОГГА В TELEGRAM', 44, 'Semibold', GREY, 540, 230 + dy, a)
        text(c, '5 СВОИХ', 150, 'Heavy', ACC, 540, 370 + dy, a, b5)
        text(c, 'КОЛЛЕКЦИЙ', 100, 'Heavy', WHITE, 540, 500 + dy, a)
    # five collections: heading + names
    a, _, _ = win(t, E['five'], E['sold'] - 0.1, dout=0.3)
    if a > 0.004:
        text(c, 'КОЛЛЕКЦИИ SNOOP DOGG', 40, 'Semibold', GREY, 540, 330, a)
        for i, n in enumerate(NAMES):
            k = sm(E[WORD_N[i]] - 0.05, E[WORD_N[i]] + 0.25, t)
            text(c, n, 36, 'Semibold', WHITE, SLOTS[i][0], SLOTS[i][1] + 185 + 14 * (1 - k), a * k)
    for i in range(5):
        cx, cy, s, a_ = snoop_pose(i, t)
        if a_ > 0.004:
            gift(c, SNOOP[i], t, cx, cy, 300, s, a_, off=0.37 * i)
    sold(c, t)
    series(c, t)


def sold(c, t):
    a, ki, ko = win(t, E['sold'] + 0.3, E['second'] - 0.1, dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 80 * ko
    v = 996_000 * fx.ease_out(cl((t - E['million'] + 0.1) / 1.3))
    n = int(round(v / 1000) * 1000)
    done = n >= 996_000
    pop = 1 + 0.06 * fx.bump(t - E['million'] - 1.2, 3, 7)
    text(c, f'{n:,}'.replace(',', ' '), 130, 'Heavy', ACC if done else WHITE, 540, 620 + dy, a, pop)
    text(c, 'ШТУК РАСКУПИЛИ', 44, 'Semibold', GREY, 540, 740 + dy, a)
    x0, x1, y = 200, 880, 850 + dy                            # half-hour track
    rrect(c, x0, y - 4, x1, y + 4, 4, DIM, a)
    f = fx.ease_out(cl((t - E['million']) / (E['half'] + 0.45 - E['million'])))
    if f > 0.01:
        rrect(c, x0, y - 4, x0 + (x1 - x0) * f, y + 4, 4, ACC, a)
        disc(c, x0 + (x1 - x0) * f, y, 11, ACC, a)
    text(c, '0 мин', 30, 'Medium', GREY, x0, y + 50, a, left=True)
    hi = sm(E['half'], E['half'] + 0.25, t)
    text(c, '30 мин', 30, 'Semibold', mix(GREY, WHITE, hi), x1 - 88, y + 50, a, left=True)
    k = spr(E['usd'] - 0.05, t, 1.8, 0.55)
    if k > 0:
        text(c, '$12 000 000', 110, 'Heavy', ACC, 540, 1040 + dy + 30 * (1 - k), a * cl(k * 2), lerp(0.8, 1.0, k))
    text(c, 'Дуров · The Block, Decrypt · 10.07.2025', 26, 'Medium', SRC, 540, 1170 + dy, a)


def series(c, t):
    a, ki, ko = win(t, E['second'], E['khabib'] - 0.05, dout=0.3)
    if a <= 0.004:
        return
    dy = 30 * (1 - ki) - 70 * ko
    gold = sm(E['series'] - 0.05, E['series'] + 0.3, t)
    p = sm(E['second'], E['second'] + 0.8, t)
    col = mix(WHITE, ACC, gold)
    pts = rrect_pts(370, 520 + dy, 710, 860 + dy, 48)
    n = len(pts) - 1                                             # dashed outline: every other piece
    for j in range(0, n, 2):
        if j / n < p:
            stroke(c, pts[j:j + 2], col, 3, 1, a)
    b = 1 + 0.12 * fx.bump(t - E['series'], 3, 6)
    text(c, '?', 190, 'Heavy', mix(GREY, ACC, gold), 540, 690 + dy, a * p, b)
    text(c, 'СЕРИЯ 2', 84, 'Heavy', WHITE, 540, 980 + dy, a * sm(E['second'] + 0.3, E['second'] + 0.6, t))
    text(c, 'анонс в канале Снупа · 13.10.2026', 28, 'Medium', GREY, 540, 1060 + dy,
         a * sm(E['series'], E['series'] + 0.3, t))


# ------------------------------------------------------------------ Khabib: papakha, 29 000 in a day, Conor
def khabib(c, t):
    a, ki, ko = win(t, E['khabib'] + 0.1, E['durov'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ХАБИБ', 130, 'Heavy', WHITE, 540, 250 + dy, a)
    text(c, 'НУРМАГОМЕДОВ', 40, 'Semibold', GREY, 540, 345 + dy, a)
    conor = sm(E['accused'] - 0.5, E['accused'] - 0.15, t)        # the counter block is gone before the quote card
    cx, cy = 540, lerp(680, 620, conor)
    ring_p = sm(E['auction'] - 0.1, E['day'] + 0.35, t)
    if ring_p > 0.003:
        stroke(c, circle_pts(cx, cy + dy, 232), DIM, 3, 1, a * (1 - conor))
        stroke(c, circle_pts(cx, cy + dy, 232), ACC, 4, ring_p, a * (1 - conor))
        text(c, '24 ч', 30, 'Semibold', mix(GREY, ACC, sm(E['day'], E['day'] + 0.3, t)), cx, cy - 262 + dy,
             a * sm(E['auction'] - 0.1, E['auction'] + 0.2, t) * (1 - conor) ** 4)
    k = spr(E['khabib'], t, 1.6, 0.55)
    shake = 0.10 * math.sin((t - E['accused']) * 26) * math.exp(-(t - E['accused']) * 3.5) if t > E['accused'] else 0
    gift(c, PAPAKHA, t, cx, cy + dy + 40 * (1 - k), 420, lerp(0.6, 1.0, k) * (1 - 0.18 * conor), a * cl(k * 2), shake)
    k1 = sm(E['papakha'] - 0.05, E['papakha'] + 0.25, t) * (1 - conor)
    text(c, "Khabib's Papakha", 42, 'Semibold', ACC, 540, 945 + dy + 14 * (1 - k1), a * k1)
    v = 29_000 * fx.ease_out(cl((t - E['k29'] + 0.05) / 1.1))
    k2 = sm(E['k29'] - 0.1, E['k29'] + 0.2, t) * (1 - conor)
    if k2 > 0.004:
        n = int(round(v / 100) * 100)
        text(c, f'{n:,}'.replace(',', ' '), 120, 'Heavy', ACC if n >= 29_000 else WHITE, 540, 1060 + dy, a * k2,
             1 + 0.06 * fx.bump(t - E['k29'] - 1.1, 3, 7))
        text(c, 'ПАПАХ · АУКЦИОН · ЗА СУТКИ', 32, 'Semibold', GREY, 540, 1160 + dy, a * k2)
        text(c, 'ноябрь 2025 · ≈ $4,4 млн', 26, 'Medium', SRC, 540, 1220 + dy, a * k2)
    # Conor McGregor: a quote bubble (his words as reported, no likeness)
    kb = spr(E['accused'] - 0.15, t, 2.0, 0.5) if t > E['accused'] - 0.15 else 0
    if kb > 0.004:
        y0 = 900 + dy + 40 * (1 - kb)
        x0, x1, y1 = 150, 930, y0 + 230
        rrect(c, x0, y0, x1, y1, 44, SURF, a * cl(kb * 2), outline=DIM, width=2)
        text(c, 'КОНОР МАКГРЕГОР', 30, 'Semibold', GREY, 540, y0 + 60, a * cl(kb * 2))
        text(c, '«обман фанатов»', 64, 'Heavy', WHITE, 540, y0 + 140, a * cl(kb * 2), lerp(0.85, 1.0, kb))
        text(c, 'ноябрь 2025', 26, 'Medium', SRC, 540, y1 + 45, a * cl(kb * 2))


# ------------------------------------------------------------------ Durov: his cap, Plush Pepe #1
def durov(c, t):
    a, ki, ko = win(t, E['durov'] + 0.1, E['evelone'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ПАВЕЛ ДУРОВ', 96, 'Heavy', WHITE, 540, 230 + dy, a)
    card_k = sm(E['pepe'], E['pepe'] + 0.45, t)
    # the cap: his own collection, then it steps aside for the card
    k = spr(E['durov'], t, 1.6, 0.55)
    cx, cy, s = lerp(540, 900, card_k), lerp(700, 300, card_k), lerp(1.0, 0.0, card_k)
    gift(c, CAPG, t, cx, cy + dy + 40 * (1 - k), 420, lerp(0.6, 1.0, k) * s, a * cl(k * 2) * (1 - card_k))
    k1 = sm(E['release'] - 0.1, E['release'] + 0.2, t) * (1 - card_k)
    text(c, "Durov's Cap", 44, 'Semibold', ACC, 540, 960 + dy + 14 * (1 - k1), a * k1)
    text(c, 'ЕГО СОБСТВЕННАЯ КОЛЛЕКЦИЯ', 30, 'Semibold', GREY, 540, 1020 + dy, a * k1)
    if card_k <= 0.004:
        return
    # the Telegram collectible card of Plush Pepe #1
    ca = a * card_k
    y = dy + 40 * (1 - card_k)
    p = sm(E['pepe'], E['pepe'] + 0.8, t)
    rrect(c, 160, 330 + y, 920, 1290 + y, 56, SURF, ca * p)
    stroke(c, rrect_pts(160, 330 + y, 920, 1290 + y, 56), DIM, 2.5, p, ca)
    rrect(c, 192, 362 + y, 888, 880 + y, 40, (60, 64, 68), ca * p)          # Onyx Black backdrop (#4d5254 / #313638)
    kp = spr(E['pepe'] + 0.2, t, 1.7, 0.5) if t > E['pepe'] + 0.2 else 0
    gift(c, PEPE, t, 540, 625 + y + 30 * (1 - kp), 440, lerp(0.6, 1.0, kp) * (1 + 0.07 * fx.bump(t - E['first'], 3, 7)),
         ca * cl(kp * 2))
    k = sm(E['first'] - 0.1, E['first'] + 0.2, t)
    text(c, 'Plush Pepe #1', 66, 'Heavy', WHITE, 540, 950 + y, ca * k, 1 + 0.05 * fx.bump(t - E['first'], 3, 7))
    rows = (('Владелец', 'Pavel Durov', 1030), ('Модель', 'Pumpkin · 3%', 1088))
    for j, (l, r, yy) in enumerate(rows):
        kk = sm(E['first'] + 0.15 * j, E['first'] + 0.3 + 0.15 * j, t)
        text(c, l, 34, 'Medium', GREY, 230, yy + y, ca * kk, left=True)
        f = fx.font('Semibold', 34)
        text(c, r, 34, 'Semibold', WHITE, 850 - f.getlength(r), yy + y, ca * kk, left=True)
    kq = spr(E['price'] - 0.1, t, 1.8, 0.55) if t > E['price'] - 0.1 else 0
    if kq > 0:
        text(c, '$47 000', 84, 'Heavy', ACC, 540, 1178 + y + 20 * (1 - kq), ca * cl(kq * 2), lerp(0.85, 1, kq))
        text(c, '14 850 TON · подарили в апреле 2025', 26, 'Medium', GREY, 540, 1250 + y, ca * cl(kq * 2))
    text(c, 't.me/nft/PlushPepe-1 · 06.11.2026', 24, 'Medium', SRC, 540, 300 + y, ca * k)


# ------------------------------------------------------------------ Evelone: 119 gifts
COLS, ROWS, STEP, CELL = 14, 9, 66, 58
GX0, GY0 = (W - (COLS * STEP - (STEP - CELL))) / 2, 470


def evelone(c, t):
    a, ki, ko = win(t, E['evelone'] + 0.1, E['porsche'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'EVELONE', 120, 'Heavy', WHITE, 540, 250 + dy, a)
    text(c, 'СТРИМЕР · публичный профиль', 34, 'Semibold', GREY, 540, 350 + dy, a)
    n = int(119 * fx.ease_out(cl((t - E['e119'] + 0.25) / 1.3)))
    for j in range(COLS * ROWS):
        x = GX0 + (j % COLS) * STEP
        yy = GY0 + (j // COLS) * STEP + dy
        if j < n:
            put(c, mini(j * 7, 52), x + CELL / 2, yy + CELL / 2, 1.0, a)
        else:
            rrect(c, x, yy, x + CELL, yy + CELL, 14, None, a * (0.55 if j < 119 else 0.25), outline=DIM, width=2)
    text(c, f'{n} ПОДАРКОВ', 64, 'Heavy', ACC if n >= 119 else WHITE, 540, 1130 + dy,
         a * sm(E['e119'] - 0.3, E['e119'], t), 1 + 0.06 * fx.bump(t - E['e119'] - 1.05, 3, 7))
    k = spr(E['e40'] - 0.1, t, 1.8, 0.55) if t > E['e40'] - 0.1 else 0
    if k > 0:
        text(c, '≈ 40 000 000 ₽', 76, 'Heavy', ACC, 540, 1225 + dy + 20 * (1 - k), a * cl(k * 2), lerp(0.85, 1, k))
    text(c, 'оценка: блог cyber.sports.ru · 16.06.2025', 24, 'Medium', SRC, 540, 410 + dy, a)


# ------------------------------------------------------------------ Portals co-founder: 18 gifts = a Porsche
CAR_Y = 0.72          # flatten the profile: a 911 is low


def car_pts(x0, y0, w):
    """Profile of a 911 (fastback left, nose right): body line from the rear bottom over the roof, then the sills
    and both wheel arches back to the start."""
    body = [(0.02, 0.0), (0.0, -0.10), (0.02, -0.17), (0.08, -0.24), (0.18, -0.32), (0.30, -0.38), (0.42, -0.405),
            (0.52, -0.40), (0.60, -0.36), (0.67, -0.28), (0.72, -0.245), (0.86, -0.215), (0.95, -0.185),
            (1.0, -0.12), (0.995, -0.04), (0.97, 0.0), (0.885, 0.0)]
    arc_f = [(0.78 + 0.105 * math.cos(math.radians(a)), -0.105 / CAR_Y * math.sin(math.radians(a)) * 0.95)
             for a in range(0, 181, 10)]
    arc_r = [(0.22 + 0.105 * math.cos(math.radians(a)), -0.105 / CAR_Y * math.sin(math.radians(a)) * 0.95)
             for a in range(0, 181, 10)]
    pts = body + arc_f + [(0.675, 0.0), (0.325, 0.0)] + arc_r + [(0.115, 0.0), (0.02, 0.0)]
    return [(x0 + x * w, y0 + y * w * CAR_Y) for x, y in pts]


def car_line(cx0, cy0, cw, pts):
    return [(cx0 + x * cw, cy0 + y * cw * CAR_Y) for x, y in pts]


def porsche(c, t):
    a, ki, ko = win(t, E['porsche'] + 0.1, E['outro'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'СООСНОВАТЕЛЬ', 40, 'Semibold', GREY, 540, 220 + dy, a)
    text(c, 'МАРКЕТА PORTALS', 70, 'Heavy', WHITE, 540, 300 + dy, a)
    landed = 0
    for j in range(18):
        x, yy = 265 + (j % 6) * 110, 430 + (j // 6) * 110 + dy
        t0 = E['g18'] - 0.3 + 0.045 * j
        k = spr(t0, t, 1.8, 0.5) if t > t0 else 0
        landed += t > t0 + 0.2
        if k > 0:
            put(c, mini(j * 5 + 3, 88), x, yy - 30 * (1 - k), lerp(0.5, 1, k), a * cl(k * 2))
    if landed:
        text(c, f'{landed} ПОДАРКОВ', 40, 'Heavy', ACC if landed == 18 else WHITE, 540, 790 + dy, a)
    p = sm(E['car'] - 0.75, E['car'] - 0.2, t)
    stroke(c, [(540, 830 + dy), (540, 905 + dy)], GREY, 3, p, a)
    stroke(c, [(512, 878 + dy), (540, 906 + dy), (568, 878 + dy)], GREY, 3, sm(E['car'] - 0.3, E['car'] - 0.15, t), a)
    pc = sm(E['car'] - 0.2, E['car'] + 0.8, t)
    done = sm(E['car'] + 0.7, E['car'] + 1.0, t)
    col = mix(WHITE, ACC, done)
    cw, cx0, cy0 = 800, 140, 1140 + dy
    stroke(c, car_pts(cx0, cy0, cw), col, 4, pc, a)
    for wx in (0.22, 0.78):
        stroke(c, circle_pts(cx0 + wx * cw, cy0, 0.075 * cw), col, 4, cl(pc * 1.6 - 0.6), a)
        disc(c, cx0 + wx * cw, cy0, 0.022 * cw, col, a * cl(pc * 1.6 - 0.6))
    q = cl(pc * 1.4 - 0.4)
    side = [(0.27, -0.29), (0.36, -0.355), (0.46, -0.375), (0.55, -0.355), (0.62, -0.285), (0.27, -0.285)]
    stroke(c, car_line(cx0, cy0, cw, side + [side[0]]), col, 3, q, a)                 # side window
    stroke(c, car_line(cx0, cy0, cw, [(0.45, -0.37), (0.45, -0.285)]), col, 3, q, a)   # B-pillar
    stroke(c, car_line(cx0, cy0, cw, [(0.03, -0.37), (0.17, -0.37)]), col, 4, q, a)    # the GT3 wing
    stroke(c, car_line(cx0, cy0, cw, [(0.11, -0.37), (0.13, -0.29)]), col, 3, q, a)
    stroke(c, car_line(cx0, cy0, cw, [(0.04, -0.12), (0.96, -0.12)]), col, 2, q, a * 0.6)  # body crease
    text(c, 'PORSCHE 911 GT3', 52, 'Heavy', col, 540, 1250 + dy, a * done)
    text(c, 'ForkLog · 25.08.2025', 24, 'Medium', SRC, 540, 1300 + dy, a * done)


# ------------------------------------------------------------------ outro: whose gift would you take?
OUT = [(SNOOP[0], 'СНУП', 'o_snoop', 200), (PAPAKHA, 'ХАБИБ', 'o_khabib', 540), (PEPE, 'ДУРОВ', 'o_durov', 880)]
TYPED = 'Мой выбор — '


def outro(c, t):
    a, ki, _ = win(t, E['outro'] + 0.05, None)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki)
    text(c, 'ЧЕЙ ПОДАРОК', 96, 'Heavy', WHITE, 540, 300 + dy, a)
    text(c, 'ЗАБРАЛ БЫ ТЫ?', 96, 'Heavy', ACC, 540, 410 + dy, a)
    for i, (path, name, key, x) in enumerate(OUT):
        t0 = E['outro'] + 0.1 + 0.1 * i
        k = spr(t0, t, 1.7, 0.5) if t > t0 else 0
        hi = sm(E[key] - 0.05, E[key] + 0.2, t)
        b = 1 + 0.12 * fx.bump(t - E[key], 3, 6)
        rrect(c, x - 150, 560 + dy, x + 150, 900 + dy, 44, SURF, a * cl(k * 2), outline=mix(DIM, ACC, hi), width=3)
        gift(c, path, t, x, 700 + dy + 30 * (1 - k), 230, lerp(0.5, 1, k) * b, a * cl(k * 2), off=0.5 * i)
        text(c, name, 42, 'Heavy', mix(WHITE, ACC, hi), x, 855 + dy, a * cl(k * 2))
    # comment field with a blinking cursor: «Пиши в комментарии»
    k = sm(E['o_write'] - 0.1, E['o_write'] + 0.3, t)
    if k > 0.004:
        y = 1060 + 30 * (1 - k)
        rrect(c, 120, y - 56, 960, y + 56, 56, SURF, a * k, outline=mix(DIM, ACC, k), width=3)
        n = int(len(TYPED) * cl((t - E['o_write'] - 0.4) / 0.8))
        f = fx.font('Medium', 38)
        s = TYPED[:n] if n else 'Добавить комментарий…'
        text(c, s, 38, 'Medium', WHITE if n else GREY, 175, y, a * k, left=True)
        cx = 178 + (f.getlength(TYPED[:n]) if n else 0)
        if (t * 2.2) % 1 < 0.6 or 0 < n < len(TYPED):
            rrect(c, cx, y - 26, cx + 4, y + 26, 2, ACC, a * k)
        bx, by = 900, y                                                     # comment icon
        stroke(c, bubble_pts(bx, by + 2, 56), ACC, 3, 1, a * k)


def render_at(t):
    c = _bg().copy()
    snoop(c, t)
    khabib(c, t)
    durov(c, t)
    evelone(c, t)
    porsche(c, t)
    outro(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
