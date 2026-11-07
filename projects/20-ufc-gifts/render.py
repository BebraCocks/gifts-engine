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
SURF, GOLD = config.SURFACE, config.GOLD
FIG = [str(gifts_api.model_file(config.STRIKE, m, 'json')) for m in config.FIGHTERS]
GOLDS = [str(gifts_api.model_file(config.STRIKE, m, 'json')) for m in config.GOLDS]
OCT = str(gifts_api.model_file(config.STRIKE, config.OCTAGON, 'json'))
BOX = str(gifts_api.original_file(config.STRIKE, 'json'))
PAPAKHA = str(gifts_api.original_file(config.KHABIB, 'json'))
NAMES = ['Jones', 'Pereira', 'Chimaev', 'Topuria', 'Volkanovski', 'Adesanya', 'Oliveira', 'O’Malley', 'Dvalishvili',
         'Pantoja']
MINI = []
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




def rot_pts(pts, cx, cy, ang):
    cs, sn = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * cs - (y - cy) * sn, cy + (x - cx) * sn + (y - cy) * cs) for x, y in pts]


def link_icon(c, cx, cy, s, color, a=1.0, width=4):
    """Two chain links (rounded capsules at 45°)."""
    for dx in (-0.22, 0.22):
        x, y = cx + dx * s, cy - dx * s
        pts = rrect_pts(x - 0.32 * s, y - 0.16 * s, x + 0.32 * s, y + 0.16 * s, 0.16 * s, 6)
        stroke(c, rot_pts(pts, x, y, -math.pi / 4), color, width, 1, a)


def link_scene(c, t, t0, t1, w_copy, w_goal, title2):
    """After the hook: «скопируй ссылку». A share sheet, the copy button is tapped, a toast confirms it."""
    a, ki, ko = win(t, t0, t1, dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 80 * ko
    b = 1 + 0.06 * fx.bump(t - w_copy, 3, 7)
    text(c, 'СКОПИРУЙ ССЫЛКУ', 88, 'Heavy', WHITE, 540, 330 + dy, a, b)
    g = sm(w_goal - 0.05, w_goal + 0.3, t)
    text(c, title2, 40, 'Semibold', mix(GREY, ACC, g), 540, 430 + dy, a, 1 + 0.05 * fx.bump(t - w_goal, 3, 7))
    y0 = 560 + dy
    rrect(c, 140, y0, 940, y0 + 440, 48, SURF, a, outline=DIM, width=2)
    text(c, 'Поделиться', 34, 'Semibold', GREY, 540, y0 + 70, a)
    for j, x in enumerate((300, 460, 620, 780)):                       # contacts row: empty discs, no faces
        disc(c, x, y0 + 170, 46, DIM, a)
    tap = w_copy + 0.25
    f = sm(tap, tap + 0.15, t)
    bx0, by0, bx1, by1 = 200, y0 + 270, 880, y0 + 380
    rrect(c, bx0, by0, bx1, by1, 55, ACC if f > 0.5 else None, a * (f if f > 0.5 else 1), outline=ACC, width=3)
    col = mix(WHITE, BG, f)
    link_icon(c, 300, (by0 + by1) / 2, 62, col, a, 4)
    text(c, 'Копировать ссылку', 44, 'Semibold', col, 360, (by0 + by1) / 2, a, left=True)
    r = cl((t - tap) / 0.45)                                             # tap ripple
    if 0 < r < 1:
        stroke(c, circle_pts(700, (by0 + by1) / 2, 20 + 70 * fx.ease_out(r)), WHITE, 3, 1, a * (1 - r))
    k = spr(tap + 0.25, t, 1.8, 0.55) if t > tap + 0.25 else 0
    if k > 0:
        yy = y0 + 520 + 30 * (1 - k)
        rrect(c, 260, yy - 44, 820, yy + 44, 44, (32, 35, 60), a * cl(k * 2))
        disc(c, 318, yy, 22, ACC, a * cl(k * 2))
        stroke(c, check_pts(318, yy, 30), BG, 4, cl(k * 1.5), a * cl(k * 2))
        text(c, 'Ссылка скопирована', 36, 'Semibold', WHITE, 360, yy, a * cl(k * 2), left=True)


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


def tg_card(c, t, path, t0, title, rows, y, a, backdrop=(60, 64, 68), w_title=None):
    """Telegram collectible card: backdrop panel with the animated model, a title and label/value rows."""
    p = sm(t0, t0 + 0.8, t)
    rrect(c, 160, 330 + y, 920, 1290 + y, 56, SURF, a * p)
    stroke(c, rrect_pts(160, 330 + y, 920, 1290 + y, 56), DIM, 2.5, p, a)
    rrect(c, 192, 362 + y, 888, 880 + y, 40, backdrop, a * p)
    kp = spr(t0 + 0.2, t, 1.7, 0.5) if t > t0 + 0.2 else 0
    wt_ = w_title if w_title is not None else t0 + 0.4
    gift(c, path, t, 540, 625 + y + 30 * (1 - kp), 440, lerp(0.6, 1.0, kp) * (1 + 0.07 * fx.bump(t - wt_, 3, 7)),
         a * cl(kp * 2))
    k = sm(wt_ - 0.1, wt_ + 0.2, t)
    text(c, title, 66, 'Heavy', WHITE, 540, 950 + y, a * k, 1 + 0.05 * fx.bump(t - wt_, 3, 7))
    f = fx.font('Semibold', 34)
    for j, (l, r) in enumerate(rows):
        kk = sm(wt_ + 0.15 * j, wt_ + 0.3 + 0.15 * j, t)
        yy = 1030 + 58 * j + y
        text(c, l, 34, 'Medium', GREY, 230, yy, a * kk, left=True)
        text(c, r, 34, 'Semibold', WHITE, 850 - f.getlength(r), yy, a * kk, left=True)


def choice_cards(c, t, t0, items, dy, a):
    """Outro: three cards; items = [(lottie path, NAME, word time)]."""
    for i, (path, name, tw) in enumerate(items):
        x = (200, 540, 880)[i]
        ts = t0 + 0.1 + 0.1 * i
        k = spr(ts, t, 1.7, 0.5) if t > ts else 0
        hi = sm(tw - 0.05, tw + 0.2, t)
        b = 1 + 0.12 * fx.bump(t - tw, 3, 6)
        rrect(c, x - 150, 560 + dy, x + 150, 900 + dy, 44, SURF, a * cl(k * 2), outline=mix(DIM, ACC, hi), width=3)
        gift(c, path, t, x, 700 + dy + 30 * (1 - k), 230, lerp(0.5, 1, k) * b, a * cl(k * 2), off=0.5 * i)
        text(c, name, 42, 'Heavy', mix(WHITE, ACC, hi), x, 855 + dy, a * cl(k * 2))


# ------------------------------------------------------------------ captions (not for the hook line)
ACC_WORDS = {'скопируй', 'ссылку', 'просмотры.', 'Хабиб:', '29 000', '$4,5', 'млн.', 'обманом.', 'Джонс,', 'Адесанья',
             'Оливейра', 'UFC', 'Strike:', 'Перейра,', 'Чимаев,', 'Топурия,', 'Волкановски', '60 000', '4', 'часа.',
             'N3on', '323.', 'октагон,', 'золотые', '0,5%', 'профиль?', 'комментарии.'}


def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC_WORDS, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=900, top=1350, size=52, weight='Semibold',
                        max_lines=2, color=WHITE, accent_color=ACC, shadow=False, fade_out=0.2, rise=10)

GRID = [(140 + 200 * (j % 5), 690 + 290 * (j // 5)) for j in range(10)]      # 2 × 5 figurines


def fighters_grid(c, t, t0, dy, a, size=220, names=True, wave=None, hi=None):
    for j in range(10):
        x, y = GRID[j]
        ts = t0 + 0.05 * j
        k = spr(ts, t, 1.8, 0.5) if t > ts else 0
        if k <= 0:
            continue
        hop = 0
        if wave is not None:
            hop = 22 * max(0, math.sin(cl((t - wave - 0.06 * j) / 0.35) * math.pi))
        gift(c, FIG[j], t, x, y + dy + 30 * (1 - k) - hop, size, lerp(0.5, 1, k), a * cl(k * 2), off=0.3 * j)
        if names:
            text(c, NAMES[j], 28, 'Semibold', mix(GREY, WHITE, hi or 0), x, y + dy + size * 0.55, a * cl(k * 2))


# ------------------------------------------------------------------ hook: ten champions became gifts
def hook(c, t):
    a, _, ko = win(t, -1, E['link'] - 0.1, dout=0.3)
    if a <= 0.004:
        return
    dy = -50 * ko
    text(c, '10 ЧЕМПИОНОВ UFC', 88, 'Heavy', WHITE, 540, 250 + dy, a)
    text(c, 'СТАЛИ ПОДАРКАМИ', 88, 'Heavy', ACC, 540, 360 + dy, a)
    fighters_grid(c, t, -0.6, dy, a)                                  # all ten from the first frame
    k = spr(E['four_h'] - 0.1, t, 2.0, 0.5) if t > E['four_h'] - 0.1 else 0
    if k > 0:
        rrect(c, 300, 1180 + dy, 780, 1290 + dy, 55, ACC, a * cl(k * 2))
        text(c, 'РАСКУПИЛИ ЗА 4 ЧАСА', 44, 'Heavy', WHITE, 540, 1235 + dy, a * cl(k * 2), lerp(0.8, 1, k))


# ------------------------------------------------------------------ Khabib, then McGregor
def khabib(c, t):
    a, ki, ko = win(t, E['khabib'] + 0.05, E['conor'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ПЕРВЫМ БЫЛ ХАБИБ', 70, 'Heavy', WHITE, 540, 260 + dy, a)
    text(c, '22.11.2025', 30, 'Semibold', GREY, 540, 340 + dy, a)
    k = spr(E['khabib'], t, 1.6, 0.55)
    gift(c, PAPAKHA, t, 540, 620 + dy + 40 * (1 - k), 400, lerp(0.6, 1.0, k), a * cl(k * 2))
    text(c, "Khabib's Papakha", 42, 'Semibold', ACC, 540, 860 + dy, a)
    v = 29_000 * fx.ease_out(cl((t - E['k29'] + 0.05) / 1.0))
    kk = sm(E['k29'] - 0.1, E['k29'] + 0.2, t)
    text(c, counter(v, 100), 120, 'Heavy', WHITE, 540, 980 + dy, a * kk)
    text(c, 'ПАПАХ ЗА СУТКИ', 36, 'Semibold', mix(GREY, WHITE, sm(E['k_day'], E['k_day'] + 0.3, t)), 540, 1075 + dy,
         a * kk)
    kq = spr(E['k_usd'] - 0.1, t, 1.8, 0.55) if t > E['k_usd'] - 0.1 else 0
    if kq > 0:
        text(c, '≈ $4 500 000', 84, 'Heavy', ACC, 540, 1200 + dy + 20 * (1 - kq), a * cl(kq * 2), lerp(0.85, 1, kq))
    text(c, 'TMZ, EssentiallySports · ноябрь–декабрь 2025', 24, 'Medium', SRC, 540, 1275 + dy, a * cl(kq * 2))


TRIO = [(0, 'c_jones'), (5, 'c_ades'), (6, 'c_oliv')]


def conor(c, t):
    a, ki, ko = win(t, E['conor'], E['strike'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    up = sm(E['remind'] - 0.2, E['remind'] + 0.2, t)                     # the quote moves up for the reply
    kb = spr(E['conor'], t, 2.0, 0.5)
    y0 = lerp(620, 300, up) + dy + 40 * (1 - kb)
    rrect(c, 150, y0, 930, y0 + 230, 44, SURF, a * cl(kb * 2), outline=DIM, width=2)
    text(c, 'КОНОР МАКГРЕГОР', 30, 'Semibold', GREY, 540, y0 + 60, a * cl(kb * 2))
    ks = sm(E['scam'] - 0.1, E['scam'] + 0.2, t)
    text(c, '«это обман»', 72, 'Heavy', WHITE, 540, y0 + 145, a * cl(kb * 2) * ks, 1 + 0.06 * fx.bump(t - E['scam'], 3, 7))
    kr = sm(E['remind'] - 0.1, E['remind'] + 0.2, t)
    text(c, 'А ЕМУ НАПОМНИЛИ:', 44, 'Heavy', ACC, 540, 640 + dy, a * kr)
    for i, (j, key) in enumerate(TRIO):
        x = (240, 540, 840)[i]
        k = spr(E[key] - 0.12, t, 1.8, 0.5) if t > E[key] - 0.12 else 0
        if k > 0:
            gift(c, FIG[j], t, x, 860 + dy + 30 * (1 - k), 250, lerp(0.5, 1, k), a * cl(k * 2), off=0.4 * i)
            text(c, NAMES[j], 32, 'Semibold', WHITE, x, 1010 + dy, a * cl(k * 2))
    k = sm(E['c_ads'] - 0.1, E['c_ads'] + 0.25, t)
    text(c, 'ТОЖЕ РЕКЛАМИРОВАЛИ ПОДАРКИ', 40, 'Heavy', WHITE, 540, 1110 + dy, a * k)
    text(c, 'пост главы Gameplan · EssentiallySports 05.12.2025', 24, 'Medium', SRC, 540, 1170 + dy, a * k)


# ------------------------------------------------------------------ after RubUp: UFC Strike
STRIKE5 = ['s0', 's1', 's2', 's3', 's4']


def strike(c, t):
    a, ki, ko = win(t, E['strike'] + 0.1, E['sold'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'UFC STRIKE', 110, 'Heavy', WHITE, 540, 260 + dy, a, 1 + 0.05 * fx.bump(t - E['name_strike'], 3, 7))
    text(c, '7 декабря 2025 · аукцион', 32, 'Semibold', GREY, 540, 355 + dy, a)
    k = spr(E['strike'], t, 1.6, 0.55)
    gift(c, BOX, t, 540, 560 + dy + 40 * (1 - k), 300, lerp(0.6, 1.0, k), a * cl(k * 2))
    for i, key in enumerate(STRIKE5):
        x = 140 + 200 * i
        kk = spr(E[key] - 0.1, t, 1.8, 0.5) if t > E[key] - 0.1 else 0
        if kk > 0:
            gift(c, FIG[i], t, x, 880 + dy + 30 * (1 - kk), 200, lerp(0.5, 1, kk), a * cl(kk * 2), off=0.3 * i)
            text(c, NAMES[i], 28, 'Semibold', WHITE, x, 1000 + dy, a * cl(kk * 2))
    k5 = spr(E['s5'] - 0.15, t, 1.8, 0.5) if t > E['s5'] - 0.15 else 0
    if k5 > 0:
        rrect(c, 400, 1070 + dy, 680, 1160 + dy, 45, None, a * cl(k5 * 2), outline=ACC, width=3)
        text(c, '+ ЕЩЁ 5', 44, 'Heavy', ACC, 540, 1115 + dy, a * cl(k5 * 2), lerp(0.8, 1, k5))


def sold(c, t):
    a, ki, ko = win(t, E['sold'] + 0.05, E['neon'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    fighters = sm(E['sold'], E['sold'] + 0.4, t)
    for j in range(10):                                                   # a strip of all ten
        gift(c, FIG[j], t, 100 + 98 * j, 300 + dy, 110, 1.0, a * fighters, off=0.3 * j)
    v = 60_000 * fx.ease_out(cl((t - E['n60'] + 0.05) / 1.1))
    text(c, counter(v, 100), 150, 'Heavy', ACC if v >= 59_999 else WHITE, 540, 600 + dy, a,
         1 + 0.06 * fx.bump(t - E['n60'] - 1.1, 3, 7))
    text(c, 'ПОДАРКОВ', 44, 'Semibold', GREY, 540, 720 + dy, a)
    # a 6-hour track: the auction stops just past 4 h
    x0, x1, y = 160, 920, 880 + dy
    rrect(c, x0, y - 5, x1, y + 5, 5, DIM, a * sm(E['auction'] - 0.2, E['auction'], t))
    f = (4.15 / 6) * fx.ease_out(cl((t - E['auction']) / (E['hours'] + 0.6 - E['auction'])))
    if f > 0.01:
        rrect(c, x0, y - 5, x0 + (x1 - x0) * f, y + 5, 5, ACC, a)
        disc(c, x0 + (x1 - x0) * f, y, 12, ACC, a)
    for h in range(7):
        xx = x0 + (x1 - x0) * h / 6
        text(c, f'{h} ч', 28, 'Medium', WHITE if h == 4 and t > E['hours'] else GREY, xx, y + 46,
             a * sm(E['auction'] - 0.2, E['auction'], t))
    k = spr(E['hours'] + 0.2, t, 1.8, 0.55) if t > E['hours'] + 0.2 else 0
    if k > 0:
        text(c, 'ВСЁ РАСКУПЛЕНО', 64, 'Heavy', WHITE, 540, 1040 + dy, a * cl(k * 2), lerp(0.85, 1, k))
    text(c, 'Complex · 12.12.2025 · ставки в Telegram Stars', 24, 'Medium', SRC, 540, 1120 + dy, a)


def neon(c, t):
    a, ki, ko = win(t, E['neon'] + 0.05, E['octagon'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    # a stream window: rounded frame, LIVE pill, a play triangle
    rrect(c, 140, 380 + dy, 940, 830 + dy, 40, SURF, a, outline=DIM, width=2)
    blink = 0.55 + 0.45 * (math.sin(t * 6) > 0)
    rrect(c, 180, 420 + dy, 330, 476 + dy, 28, ACC, a)
    disc(c, 208, 448 + dy, 9, WHITE, a * blink)
    text(c, 'LIVE', 30, 'Heavy', WHITE, 280, 448 + dy, a)
    fill(c, [(500, 540 + dy), (500, 680 + dy), (620, 610 + dy)], WHITE, a * 0.9)
    k = spr(E['streamer'] - 0.1, t, 1.8, 0.55) if t > E['streamer'] - 0.1 else 0
    text(c, 'СТРИМЕР', 40, 'Semibold', GREY, 540, 920 + dy, a * cl(k * 2))
    text(c, 'N3ON', 150, 'Heavy', WHITE, 540, 1050 + dy, a * cl(k * 2), lerp(0.85, 1, k))
    k2 = sm(E['n323'] - 0.1, E['n323'] + 0.25, t)
    rrect(c, 330, 1150 + dy, 750, 1240 + dy, 45, None, a * k2, outline=ACC, width=3)
    text(c, 'UFC 323', 48, 'Heavy', ACC, 540, 1195 + dy, a * k2)
    text(c, 'ведущий аукциона UFC Strike', 30, 'Semibold', GREY, 540, 300 + dy, a)


def octagon(c, t):
    a, ki, ko = win(t, E['octagon'] + 0.05, E['gold'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'У ВХОДА В ОКТАГОН', 76, 'Heavy', WHITE, 540, 270 + dy, a, 1 + 0.05 * fx.bump(t - E['entry'], 3, 7))
    k = spr(E['octagon'], t, 1.6, 0.55)
    gift(c, OCT, t, 540, 700 + dy + 40 * (1 - k), 560, lerp(0.6, 1.0, k), a * cl(k * 2))
    kf = sm(E['fighters_out'] - 0.3, E['fighters_out'] + 0.1, t)
    for i, j in enumerate((0, 2)):                                        # two fighters walk in from the sides
        side = -1 if i == 0 else 1
        x = 540 + side * lerp(620, 330, fx.ease_out(kf))
        gift(c, FIG[j], t, x, 1060 + dy, 220, 1.0, a * kf, off=0.5 * i)
    text(c, 'подарки показывали на выходе бойцов · The Blast 21.12.2025', 24, 'Medium', SRC, 540, 1240 + dy, a)


def gold(c, t):
    a, ki, ko = win(t, E['gold'] + 0.05, E['outro'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'САМЫЕ РЕДКИЕ', 96, 'Heavy', GOLD, 540, 270 + dy, a)
    for i, p in enumerate(GOLDS):
        x = (240, 540, 840)[i]
        ts = E['golden'] - 0.1 + 0.12 * i
        k = spr(ts, t, 1.8, 0.5) if t > ts else 0
        if k > 0:
            gift(c, p, t, x, 640 + dy + 30 * (1 - k), 300, lerp(0.5, 1, k), a * cl(k * 2), off=0.5 * i)
            text(c, config.GOLDS[i], 32, 'Semibold', GOLD, x, 830 + dy, a * cl(k * 2))
    kq = spr(E['half'] - 0.1, t, 1.8, 0.55) if t > E['half'] - 0.1 else 0
    if kq > 0:
        text(c, '0,5%', 170, 'Heavy', WHITE, 540, 1020 + dy + 20 * (1 - kq), a * cl(kq * 2), lerp(0.85, 1, kq))
        text(c, 'редкость каждой золотой модели', 32, 'Semibold', GREY, 540, 1140 + dy, a * cl(kq * 2))
    text(c, 'api.changes.tg · 07.11.2026', 24, 'Medium', SRC, 540, 1200 + dy, a * cl(kq * 2))


def outro(c, t):
    a, ki, _ = win(t, E['outro'] + 0.05, None)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki)
    text(c, 'КАКОГО БОЙЦА', 96, 'Heavy', WHITE, 540, 250 + dy, a)
    text(c, 'ПОСТАВИШЬ В ПРОФИЛЬ?', 76, 'Heavy', ACC, 540, 360 + dy, a, 1 + 0.05 * fx.bump(t - E['o_profile'], 3, 7))
    fighters_grid(c, t, E['outro'], dy - 120, a, size=200, wave=E['o_profile'])
    comment_field(c, t, E['o_write'], 'Мой боец — ', y=1180)


def render_at(t):
    c = _bg().copy()
    hook(c, t)
    link_scene(c, t, E['link'] + 0.1, E['khabib'] - 0.1, E['copy'], E['goal'], 'так ролик наберёт больше просмотров')
    khabib(c, t)
    conor(c, t)
    strike(c, t)
    sold(c, t)
    neon(c, t)
    octagon(c, t)
    gold(c, t)
    outro(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
