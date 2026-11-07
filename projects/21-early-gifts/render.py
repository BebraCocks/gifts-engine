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
PEPE1 = str(gifts_api.model_file(*config.PEPE1, 'json'))
PEPE834 = str(gifts_api.model_file(*config.PEPE834, 'json'))
HELMET = str(gifts_api.original_file(config.HELMET, 'json'))
BRICK = str(gifts_api.original_file(config.BRICK, 'json'))
CAPG = str(gifts_api.original_file(config.CAP, 'json'))
MINI = [str(gifts_api.original_png(n, 128)) for n in ('Plush Pepe', "Durov's Cap")]
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
ACC_WORDS = {'ссылку', 'рекомендации.', 'Пепе', '2025', '$47 000.', '$11 000', '10', 'раз', 'подарил', '7000',
             'кирпичей', '34', 'минуты.', '$15,', '$3000.', '$100 000.', '761', '35', 'млн', 'шлем', 'кепку?',
             'комментарии.', 'Пепе,', 'дизайнеру'}


def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC_WORDS, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=900, top=1350, size=52, weight='Semibold',
                        max_lines=2, color=WHITE, accent_color=ACC, shadow=False, fade_out=0.2, rise=10)


# ------------------------------------------------------------------ hook: Plush Pepe #1 lives in Durov's profile
def pepe1_pose(t):
    k = spr(-0.05, t, 1.5, 0.55)
    cx, cy, s, a = 540.0, 900.0, lerp(1.0, 1.25, k), 1.0                 # 440 px sprite
    k = sm(E['link'] - 0.05, E['link'] + 0.35, t)
    cy, a = cy - 140 * k, a * (1 - k)
    return cx, cy, s * (1 + 0.07 * fx.bump(t - E['first'], 3, 7)), a


def hook(c, t):
    a, _, ko = win(t, -1, E['link'] - 0.1, dout=0.3)
    if a <= 0.004:
        return
    dy = -50 * ko
    text(c, 'В ПРОФИЛЕ ПАВЛА ДУРОВА', 44, 'Semibold', GREY, 540, 230 + dy, a)
    text(c, 'САМЫЙ ПЕРВЫЙ', 104, 'Heavy', WHITE, 540, 350 + dy, a, 1 + 0.05 * fx.bump(t - E['first'], 3, 7))
    text(c, 'PLUSH PEPE #1', 104, 'Heavy', ACC, 540, 470 + dy, a)
    cx, cy, s, ga = pepe1_pose(t)
    gift(c, PEPE1, t, cx, cy, 440, s, ga)
    k = sm(E['crazy'] - 0.1, E['crazy'] + 0.2, t)                        # «…и это не самая безумная покупка»
    text(c, 'и это не самое безумное', 40, 'Semibold', GREY, 540, 1250 + dy, a * k)


# ------------------------------------------------------------------ the three purchases
def pepe1_card(c, t):
    a, ki, ko = win(t, E['pepe1'] + 0.05, E['helmet'], dout=0.3)
    if a <= 0.004:
        return
    y = 40 * (1 - ki) - 90 * ko
    tg_card(c, t, PEPE1, E['pepe1'], 'Plush Pepe #1', (('Владелец', 'Pavel Durov'), ('Модель', 'Pumpkin · 3%')),
            y, a, (60, 64, 68), w_title=E['pepe1'] + 0.5)
    kq = spr(E['price1'] - 0.1, t, 1.8, 0.55) if t > E['price1'] - 0.1 else 0
    if kq > 0:
        text(c, '$47 000', 84, 'Heavy', ACC, 540, 1180 + y + 20 * (1 - kq), a * cl(kq * 2), lerp(0.85, 1, kq))
        text(c, '14 850 TON · подарок, апрель 2025', 26, 'Medium', GREY, 540, 1250 + y, a * cl(kq * 2))
    text(c, 'ПОДАРИЛИ ДУРОВУ', 44, 'Heavy', WHITE, 540, 250 + y, a * sm(E['gave'] - 0.1, E['gave'] + 0.2, t))
    text(c, 't.me/nft/PlushPepe-1 · ForkLog 27.04.2025', 24, 'Medium', SRC, 540, 300 + y, a)


def bars(c, t, t0, y, labels, vals, a, unit_w=640, colors=None):
    """Horizontal comparison bars growing from the left at t0 (vals relative to max)."""
    mx = max(vals)
    for j, (lab, v) in enumerate(zip(labels, vals)):
        k = fx.ease_out(cl((t - t0 - 0.15 * j) / 0.6))
        yy = y + 110 * j
        text(c, lab, 32, 'Semibold', GREY, 220, yy - 34, a, left=True)
        rrect(c, 220, yy - 10, 220 + unit_w, yy + 10, 10, (30, 32, 56), a)
        if k > 0.01:
            col = (colors or [WHITE] * len(vals))[j]
            rrect(c, 220, yy - 10, 220 + max(20, unit_w * v / mx * k), yy + 10, 10, col, a)


def helmet(c, t):
    a, ki, ko = win(t, E['helmet'] + 0.05, E['p834'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'КУПИЛ САМ', 44, 'Heavy', WHITE, 540, 250 + dy, a * sm(E['h_buy'] - 0.1, E['h_buy'] + 0.2, t))
    k = spr(E['helmet'], t, 1.6, 0.55)
    gift(c, HELMET, t, 540, 560 + dy + 40 * (1 - k), 400, lerp(0.6, 0.95, k), a * cl(k * 2))
    text(c, 'Heroic Helmet #1100', 46, 'Semibold', ACC, 540, 800 + dy, a)
    kq = spr(E['h11'] - 0.1, t, 1.8, 0.55) if t > E['h11'] - 0.1 else 0
    if kq > 0:
        text(c, '$11 000', 110, 'Heavy', WHITE, 540, 920 + dy, a * cl(kq * 2), lerp(0.85, 1, kq))
    kb = sm(E['h10'] - 0.3, E['h10'], t)
    if kb > 0.004:
        bars(c, t, E['h10'] - 0.2, 1080 + dy, ('обычная цена ≈ $1 100', 'заплатил Дуров'), (1, 10), a * kb,
             colors=[GREY, ACC])
        text(c, '×10', 64, 'Heavy', ACC, 900, 1150 + dy, a * sm(E['h10'], E['h10'] + 0.3, t),
             1 + 0.08 * fx.bump(t - E['h10'] - 0.3, 3, 7))
    text(c, 'июль 2025 · Код.ру по данным канала barboskich.ton', 24, 'Medium', SRC, 540, 300 + dy, a)


def pepe834(c, t):
    a, ki, ko = win(t, E['p834'] + 0.05, E['brick'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ИЮНЬ 2026', 44, 'Heavy', WHITE, 540, 250 + dy, a)
    fly = sm(E['p_gift'], E['p_gift'] + 0.7, t)
    k = spr(E['p834'], t, 1.6, 0.55)
    cx, cy = lerp(540, 780, fly), lerp(640, 900, fly)
    gift(c, PEPE834, t, cx, cy + dy + 40 * (1 - k), 400, lerp(0.6, 1.0, k) * lerp(1, 0.55, fly), a * cl(k * 2))
    text(c, 'Plush Pepe #834', 56, 'Heavy', WHITE, 540, 330 + dy + 560 * 0, a * (1 - fly) * 0)
    lab = 1 - fly
    text(c, 'Plush Pepe #834 · Donatello', 42, 'Semibold', ACC, 540, 900 + dy, a * lab)
    text(c, '7 500 GRAM', 72, 'Heavy', WHITE, 540, 1000 + dy, a * sm(E['p_took'], E['p_took'] + 0.3, t) * lab)
    # the designer: an empty avatar (no face), the gift lands in his profile
    kd = sm(E['p_gift'] - 0.2, E['p_gift'] + 0.2, t)
    if kd > 0.004:
        disc(c, 300, 900 + dy, 110, DIM, a * kd)
        disc(c, 300, 870 + dy, 40, (78, 82, 120), a * kd)
        rrect(c, 236, 920 + dy, 364, 980 + dy, 30, (78, 82, 120), a * kd)
        text(c, 'ДИЗАЙНЕР ТЕЛЕГРАМА', 36, 'Heavy', WHITE, 540, 1090 + dy, a * kd)
        p = sm(E['p_gift'], E['p_gift'] + 0.6, t)
        stroke(c, [(440, 900 + dy), (650, 900 + dy)], ACC, 4, p, a * kd * (1 - fly * 0.0))
        stroke(c, [(470, 880 + dy), (440, 900 + dy), (470, 920 + dy)], ACC, 4, cl(p * 2 - 1), a * kd)
    text(c, 'BeInCrypto · 27.06.2026', 24, 'Medium', SRC, 540, 300 + dy, a)


# ------------------------------------------------------------------ after RubUp: bricks, the cap, the quote, the total
def brick(c, t):
    a, ki, ko = win(t, E['brick'] + 0.1, E['cap'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, '1 АПРЕЛЯ 2025', 44, 'Heavy', WHITE, 540, 250 + dy, a)
    k = spr(E['brick'], t, 1.6, 0.55)
    gift(c, BRICK, t, 540, 560 + dy + 40 * (1 - k), 400, lerp(0.6, 0.95, k), a * cl(k * 2))
    text(c, 'Artisan Brick', 44, 'Semibold', ACC, 540, 790 + dy, a)
    v = 7000 * fx.ease_out(cl((t - E['b7000'] + 0.05) / 1.0))
    kk = sm(E['b7000'] - 0.1, E['b7000'] + 0.2, t)
    text(c, counter(v, 10), 120, 'Heavy', ACC if v >= 6999 else WHITE, 540, 910 + dy, a * kk)
    text(c, 'КИРПИЧЕЙ ПО 5 000 ★', 36, 'Semibold', GREY, 540, 1005 + dy, a * kk)
    x0, x1, y = 200, 880, 1100 + dy                                     # 34 minutes track
    rrect(c, x0, y - 4, x1, y + 4, 4, DIM, a * kk)
    f = 34 / 60 * fx.ease_out(cl((t - E['b_sold']) / (E['b34'] + 0.6 - E['b_sold'])))
    if f > 0.01:
        rrect(c, x0, y - 4, x0 + (x1 - x0) * f, y + 4, 4, ACC, a)
        disc(c, x0 + (x1 - x0) * f, y, 11, ACC, a)
        text(c, '34 мин', 30, 'Semibold', WHITE, x0 + (x1 - x0) * f, y - 42, a * sm(E['b34'], E['b34'] + 0.3, t))
    text(c, '0', 30, 'Medium', GREY, x0, y + 46, a * kk, left=True)
    text(c, '1 час', 30, 'Medium', GREY, x1 - 70, y + 46, a * kk, left=True)
    text(c, 'ForkLog · 01.04.2025', 24, 'Medium', SRC, 540, 300 + dy, a)


def cap(c, t):
    a, ki, ko = win(t, E['cap'] + 0.05, E['quote'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    k = spr(E['cap'], t, 1.6, 0.55)
    gift(c, CAPG, t, 540, 500 + dy + 40 * (1 - k), 360, lerp(0.6, 0.95, k), a * cl(k * 2))
    text(c, "Durov's Cap", 44, 'Semibold', ACC, 540, 700 + dy, a)
    # price line: a flat start, then it climbs (two dated points, the line between is a sketch, not a chart of data)
    x0, x1, yb, yt = 200, 880, 1180 + dy, 820 + dy
    stroke(c, [(x0, yb), (x1, yb)], DIM, 2, 1, a)
    p = sm(E['c_year'] - 0.1, E['c3000'] + 0.4, t)
    pts = [(x0 + (x1 - x0) * u, yb - (yb - yt) * u ** 3) for u in [j / 40 for j in range(41)]]
    stroke(c, pts, ACC, 4, p, a)
    k15 = sm(E['c15'] - 0.1, E['c15'] + 0.2, t)
    disc(c, x0, yb, 12, WHITE, a * k15)
    text(c, '$15', 56, 'Heavy', WHITE, x0 + 10, yb - 60, a * k15, left=True)
    text(c, 'ноябрь 2024', 26, 'Medium', GREY, x0, yb + 40, a * k15, left=True)
    k3 = sm(E['c3000'] - 0.1, E['c3000'] + 0.3, t)
    disc(c, x1, yt, 12, ACC, a * k3)
    text(c, '$2 829', 64, 'Heavy', ACC, x1 - 190, yt - 30, a * k3, 1 + 0.06 * fx.bump(t - E['c3000'] - 0.3, 3, 7))
    text(c, 'сентябрь 2025', 26, 'Medium', GREY, x1 - 180, yb + 40, a * k3, left=True)
    text(c, 'Gift Charts через канал Дурова · vc.ru 18.09.2025', 24, 'Medium', SRC, 540, 1250 + dy, a * k3)


def quote(c, t):
    a, ki, ko = win(t, E['quote'] + 0.05, E['total'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ПАВЕЛ ДУРОВ', 44, 'Heavy', GREY, 540, 300 + dy, a)
    text(c, '“', 260, 'Heavy', ACC, 540, 520 + dy, a * 0.9)
    k2 = spr(E['q2'] - 0.1, t, 1.8, 0.55) if t > E['q2'] - 0.1 else 0
    text(c, '$2', 150, 'Heavy', WHITE, 540, 720 + dy + 20 * (1 - k2), a * cl(k2 * 2))
    p = sm(E['q2'] + 0.3, E['q100'] - 0.1, t)
    stroke(c, [(540, 820 + dy), (540, 930 + dy)], GREY, 4, p, a)
    stroke(c, [(505, 895 + dy), (540, 930 + dy), (575, 895 + dy)], GREY, 4, cl(p * 2 - 1), a)
    k1 = spr(E['q100'] - 0.1, t, 1.8, 0.55) if t > E['q100'] - 0.1 else 0
    text(c, '$100 000+', 140, 'Heavy', ACC, 540, 1050 + dy + 20 * (1 - k1), a * cl(k1 * 2), lerp(0.85, 1, k1))
    text(c, 'подарки, юзернеймы и номера · канал Дурова, 22.07.2025', 24, 'Medium', SRC, 540, 1180 + dy, a)


COLS, ROWS, STEP = 28, 28, 26


def total(c, t):
    a, ki, ko = win(t, E['total'] + 0.05, E['outro'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    n = int(761 * fx.ease_out(cl((t - E['t761'] + 0.3) / 1.4)))
    text(c, counter(n), 130, 'Heavy', ACC if n >= 761 else WHITE, 540, 270 + dy, a,
         1 + 0.06 * fx.bump(t - E['t761'] - 1.1, 3, 7))
    text(c, 'ПУБЛИЧНЫХ ПОДАРКОВ', 40, 'Semibold', GREY, 540, 370 + dy, a)
    gx0 = (W - (COLS - 1) * STEP) / 2
    for j in range(COLS * ROWS):                                        # 784 dots, 761 of them light up
        x = gx0 + (j % COLS) * STEP
        y = 450 + (j // COLS) * STEP + dy
        if j < n:
            disc(c, x, y, 9, ACC if j % 7 else WHITE, a)
        else:
            disc(c, x, y, 5, DIM, a * (1 if j < 761 else 0.4))
    kq = spr(E['t35'] - 0.1, t, 1.8, 0.55) if t > E['t35'] - 0.1 else 0
    if kq > 0:
        rrect(c, 170, 1200 + dy, 910, 1310 + dy, 55, SURF, a * cl(kq * 2), outline=ACC, width=3)
        text(c, '≈ 35 000 000 ₽', 70, 'Heavy', WHITE, 540, 1255 + dy, a * cl(kq * 2), lerp(0.85, 1, kq))
    text(c, 'оценка блога cyber.sports.ru · 16.06.2025', 24, 'Medium', SRC, 540, 1180 + dy, a * (1 - cl(kq * 2)))


def outro(c, t):
    a, ki, _ = win(t, E['outro'] + 0.05, None)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki)
    text(c, 'КАКОЙ ПОДАРОК ДУРОВА', 70, 'Heavy', WHITE, 540, 300 + dy, a)
    text(c, 'ЗАБРАЛ БЫ ТЫ?', 96, 'Heavy', ACC, 540, 410 + dy, a)
    choice_cards(c, t, E['outro'], [(PEPE1, 'ПЕПЕ', E['o_pepe']), (HELMET, 'ШЛЕМ', E['o_helmet']),
                                    (CAPG, 'КЕПКА', E['o_cap'])], dy, a)
    comment_field(c, t, E['o_write'], 'Мой выбор — ')


def render_at(t):
    c = _bg().copy()
    hook(c, t)
    link_scene(c, t, E['link'] + 0.1, E['pepe1'] - 0.1, E['copy'], E['goal'], 'видео быстрее попадёт в рекомендации')
    pepe1_card(c, t)
    helmet(c, t)
    pepe834(c, t)
    brick(c, t)
    cap(c, t)
    quote(c, t)
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
