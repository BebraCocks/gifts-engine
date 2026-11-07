"""21-early-gifts «Сколько бы вы заработали?»: minimal 2D picture. Midnight-ink background, thin light lines, one mint
accent for profit and a warm tone for everyday things (crumbs, pizza, tickets). Content time t -> RGB frame; RubUp via
banner.Breaks (same in audio.py)."""
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
WARM = config.WARM
WATCHG = str(gifts_api.original_file(config.WATCH, 'json'))
CAPG = str(gifts_api.original_file(config.CAP, 'json'))
PEPEG = str(gifts_api.original_file(config.PEPE, 'json'))
MINI = [str(gifts_api.original_png(n, 128)) for n in (config.WATCH, config.CAP, config.PEPE)]
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


# ------------------------------------------------------------------ drawn everyday things and phones
def crumbs(c, cx, cy, s, a=1.0, crossed=0.0):
    """A crumbs pack: a bag with a zigzag top, a label band and a few crumbs. s = height in px."""
    if a <= 0.004:
        return
    w, h = s * 0.70, s
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    top = [(x0 + w * k / 8, y0 + (0 if k % 2 == 0 else s * 0.05)) for k in range(9)]
    body = top + [(x1 - w * 0.04, y1), (x0 + w * 0.04, y1)]
    fill(c, body, (46, 40, 34), a)
    stroke(c, body + [body[0]], WARM, max(2.0, s * 0.018), 1, a)
    rrect(c, x0 + w * 0.10, cy - s * 0.12, x1 - w * 0.10, cy + s * 0.12, s * 0.06, WARM, a)
    if s >= 120:
        text(c, 'СУХАРИКИ', int(s * 0.10), 'Heavy', (46, 40, 34), cx, cy, a)
    for dx, dy in ((-0.18, 0.30), (0.05, 0.34), (0.20, 0.28)):
        rrect(c, cx + dx * s - s * 0.035, cy + dy * s - s * 0.035, cx + dx * s + s * 0.035, cy + dy * s + s * 0.035,
              s * 0.01, WARM, a * 0.8)
    if crossed > 0.004:
        stroke(c, [(x0 - s * 0.08, y1 + s * 0.05), (x1 + s * 0.08, y0 - s * 0.05)], (255, 110, 110),
               max(3.0, s * 0.035), crossed, a)


def pizza(c, cx, cy, r, a=1.0, crossed=0.0):
    if a <= 0.004:
        return
    disc(c, cx, cy, r, (196, 128, 60), a)                      # crust
    disc(c, cx, cy, r * 0.86, WARM, a)                         # cheese
    for k in range(3):                                         # slice cuts
        ang = math.radians(30 + 60 * k)
        stroke(c, [(cx - r * 0.86 * math.cos(ang), cy - r * 0.86 * math.sin(ang)),
                   (cx + r * 0.86 * math.cos(ang), cy + r * 0.86 * math.sin(ang))], (196, 128, 60), max(2, r * 0.03), 1, a)
    for dx, dy in ((-0.4, -0.25), (0.35, -0.38), (0.1, 0.42), (-0.3, 0.35), (0.45, 0.15), (0.0, -0.05)):
        disc(c, cx + dx * r, cy + dy * r, r * 0.11, (214, 70, 60), a)
    if crossed > 0.004:
        stroke(c, [(cx - r * 1.1, cy + r * 1.1), (cx + r * 1.1, cy - r * 1.1)], (255, 110, 110), max(3, r * 0.06), crossed, a)


def ticket(c, cx, cy, s, a=1.0, rot=0.0):
    if a <= 0.004:
        return
    w, h = s, s * 0.5
    pts = rot_pts(rrect_pts(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, s * 0.06, 6), cx, cy, rot)
    fill(c, pts, (46, 40, 34), a)
    stroke(c, pts, WARM, 3, 1, a)
    for sx in (-1, 1):
        x, y = rot_pts([(cx + sx * w / 2, cy)], cx, cy, rot)[0]
        disc(c, x, y, s * 0.07, BG, a)
    put(c, label('КИНО', int(s * 0.18), 'Heavy', WARM), cx, cy, 1.0, a, rot)


def phone(c, cx, cy, h, a=1.0, name=None, glow=0.0):
    """A modern phone in thin lines: body, screen, dynamic island; name inside the screen."""
    if a <= 0.004:
        return
    w = h * 0.49
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    if glow > 0.004:
        disc(c, cx, cy, h * 0.56, mix(BG, ACC, 0.05), a * glow)
    rrect(c, x0, y0, x1, y1, w * 0.18, (18, 20, 36), a, outline=mix(WHITE, ACC, glow), width=max(3, h * 0.012))
    rrect(c, x0 + w * 0.06, y0 + w * 0.06, x1 - w * 0.06, y1 - w * 0.06, w * 0.13, (28, 31, 56), a)
    rrect(c, cx - w * 0.17, y0 + w * 0.11, cx + w * 0.17, y0 + w * 0.20, w * 0.05, (8, 9, 18), a)
    stroke(c, [(x0 + w * 0.22, y0 + h * 0.25), (x0 + w * 0.40, y0 + h * 0.15)], (60, 64, 100), max(2, h * 0.008), 1, a)
    if name:
        lines = name.split('\n')
        for j, s in enumerate(lines):
            size = int(h * (0.095 if j == 0 else 0.13))
            text(c, s, size, 'Heavy', WHITE if j == 0 else ACC, cx, cy + (j - (len(lines) - 1) / 2) * h * 0.14,
                 a, min(1.0, (w * 0.82) / max(1, label(s, size, 'Heavy', WHITE).width)))


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


# ------------------------------------------------------------------ captions (not for the hook line)
ACC_WORDS = {'заработали,', 'раньше.', '$1,5.', 'сухариков.', '75', 'TON.', '50', 'раз', 'дороже!', '20', '10', 'часов.',
             'iPhone', '16e.', '$15', 'пиццу.', '2', '17e.', '$30.', '649', '000', '649 000', '3', '18', 'Pro', 'Max!',
             'жалеете?', 'подарок'}


def _phr(k):
    return captions.phrase(WORDS[k], accent=ACC_WORDS, end=END[k] + 0.2)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=900, top=1350, size=52, weight='Semibold',
                        max_lines=2, color=WHITE, accent_color=ACC, shadow=False, fade_out=0.2, rise=10)


# ------------------------------------------------------------------ 1 hook: crumbs -> gift -> phone
def hook(c, t):
    a, _, ko = win(t, -1, E['count'] - 0.05, dout=0.3)
    if a <= 0.004:
        return
    dy = -60 * ko
    text(c, 'ВМЕСТО ПАЧКИ СУХАРИКОВ —', 50, 'Heavy', WHITE, 540, 300 + dy, a,
         1 + 0.05 * fx.bump(t - E['h_crumbs'], 3, 7))
    kt = sm(E['h_gift'] - 0.1, E['h_gift'] + 0.25, t)
    text(c, 'ПОДАРОК', 110, 'Heavy', ACC, 540, 420 + dy, a * kt, 1 + 0.05 * fx.bump(t - E['h_gift'], 3, 7))
    kp = sm(E['h_phone'] - 0.1, E['h_phone'] + 0.25, t)
    text(c, 'ЦЕНОЙ КАК АЙФОН', 72, 'Heavy', WHITE, 540, 530 + dy, a * kp, 1 + 0.05 * fx.bump(t - E['h_phone'], 3, 7))
    k0 = pop(-0.6, t, 1.6)
    move = sm(E['h_gift'] - 0.2, E['h_gift'] + 0.4, t)
    x = lerp(540, 190, move)
    s = lerp(lerp(200, 330, k0), 210, move)
    crumbs(c, x, 880 + dy, s, a * cl(k0 * 2), crossed=sm(E['h_gift'] + 0.2, E['h_gift'] + 0.6, t))
    kg = pop(E['h_gift'], t, 1.7)
    arrow(c, 300, 880 + dy, 380, 880 + dy, sm(E['h_gift'], E['h_gift'] + 0.35, t), a)
    gift(c, WATCHG, t, 540, 880 + dy, 300, lerp(0.5, 1.0, kg), a * cl(kg * 2))
    arrow(c, 705, 880 + dy, 795, 880 + dy, sm(E['h_phone'] - 0.15, E['h_phone'] + 0.2, t), a)
    kh = pop(E['h_phone'] - 0.1, t, 1.7)
    phone(c, 890, 880 + dy, lerp(200, 320, kh), a * cl(kh * 2), 'iPhone', glow=kh)
    text(c, '$1,5', 44, 'Heavy', WARM, 540, 1080 + dy, a * kg)
    text(c, '→ сейчас ×50', 40, 'Semibold', ACC, 540, 1140 + dy, a * kp)


# ------------------------------------------------------------------ 2 «считаем»
def count(c, t):
    a, ki, ko = win(t, E['count'], E['watch'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'СКОЛЬКО БЫ ВЫ', 84, 'Heavy', WHITE, 540, 420 + dy, a)
    text(c, 'ЗАРАБОТАЛИ?', 118, 'Heavy', ACC, 540, 540 + dy, a, 1 + 0.05 * fx.bump(t - E['c_how'], 3, 7))
    x0, x1, y = 190, 890, 1000 + dy
    stroke(c, [(x0, y), (x1, y)], DIM, 3, 1, a)
    p = fx.ease_out(cl((t - E['c_how']) / max(0.5, E['c_early'] - E['c_how'] + 0.3)))
    stroke(c, [(x0, y), (lerp(x0, x1, p), y)], ACC, 5, 1, a)
    disc(c, x0, y, 12, WHITE, a)
    disc(c, lerp(x0, x1, p), y, 14, ACC, a)
    text(c, 'декабрь 2024', 32, 'Semibold', GREY, x0 + 20, y + 50, a, left=True)
    text(c, 'ноябрь 2026', 32, 'Semibold', ACC if p > 0.98 else GREY, x1 - 180, y + 50, a, left=True)
    for i, x in enumerate((340, 540, 740)):
        k = pop(E['count'] + 0.3 + 0.15 * i, t)
        put(c, mini(i, 128), x, 820 + dy + 20 * (1 - k), lerp(0.5, 1, k), a * cl(k * 2))


# ------------------------------------------------------------------ 3–5 Swiss Watch
def watch(c, t):
    a, ki, ko = win(t, E['watch'] + 0.05, E['wnow'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ДЕКАБРЬ 2024', 44, 'Heavy', GREY, 540, 250 + dy, a)
    k = pop(E['watch'], t, 1.6)
    gift(c, WATCHG, t, 540, 560 + dy + 40 * (1 - k), 400, lerp(0.6, 1.0, k), a * cl(k * 2))
    text(c, 'Swiss Watch', 48, 'Semibold', ACC, 540, 800 + dy, a)
    price(c, t, E['w15'], '$1,5', 130, WHITE, 540, 930 + dy, a)
    kc = sm(E['w_crumbs'] - 0.2, E['w_crumbs'] + 0.2, t)
    if kc > 0.004:
        text(c, '=', 80, 'Heavy', GREY, 330, 1105 + dy, a * kc)
        for j, x in enumerate((500, 710)):
            kk = pop(E['w_crumbs'] - 0.15 + 0.12 * j, t)
            crumbs(c, x, 1110 + dy + 20 * (1 - kk), 170, a * cl(kk * 2))
    text(c, 'стартовая цена · ForkLog 25.08.2025', 24, 'Medium', SRC, 540, 300 + dy, a)


def bars(c, t, t0, y, labels, vals, a, unit_w=640, colors=None):
    """Horizontal comparison bars growing from the left at t0 (vals relative to max)."""
    mx = max(vals)
    for j, (lab, v) in enumerate(zip(labels, vals)):
        k = fx.ease_out(cl((t - t0 - 0.2 * j) / 0.7))
        yy = y + 110 * j
        text(c, lab, 32, 'Semibold', GREY, 220, yy - 34, a, left=True)
        rrect(c, 220, yy - 10, 220 + unit_w, yy + 10, 10, (30, 32, 56), a)
        if k > 0.01:
            col = (colors or [WHITE] * len(vals))[j]
            rrect(c, 220, yy - 10, 220 + max(20, unit_w * v / mx * k), yy + 10, 10, col, a)


def watch_now(c, t):
    a, ki, ko = win(t, E['wnow'] + 0.05, E['wph'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'НОЯБРЬ 2026', 44, 'Heavy', ACC, 540, 250 + dy, a)
    k = pop(E['wnow'], t, 1.6)
    gift(c, WATCHG, t, 540, 500 + dy + 30 * (1 - k), 300, lerp(0.6, 1.0, k), a * cl(k * 2))
    v = 75 * fx.ease_out(cl((t - E['w75'] + 0.1) / 0.8))
    kk = sm(E['w75'] - 0.2, E['w75'] + 0.1, t)
    text(c, f'{int(round(v))} TON', 130, 'Heavy', ACC if v >= 74.5 else WHITE, 540, 760 + dy, a * kk)
    text(c, '≈ 6 700 ₽ · самый дешёвый на Fragment', 32, 'Semibold', GREY, 540, 850 + dy, a * kk)
    kb = sm(E['w50'] - 0.3, E['w50'], t)
    if kb > 0.004:
        bars(c, t, E['w50'] - 0.25, 990 + dy, ('декабрь 2024 · $1,5', 'сейчас · ≈ $82'), (1.5, 82), a * kb,
             colors=[WARM, ACC])
        text(c, '×50', 76, 'Heavy', ACC, 880, 920 + dy, a * sm(E['w50'], E['w50'] + 0.3, t),
             1 + 0.08 * fx.bump(t - E['w50'] - 0.3, 3, 7))
    text(c, 'Fragment · 07.11.2026 · 1 TON ≈ 89,5 ₽', 24, 'Medium', SRC, 540, 300 + dy, a)


def watch_phone(c, t):
    a, ki, ko = win(t, E['wph'] + 0.05, E['cap'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    swap = sm(E['w10'] - 0.1, E['w10'] + 0.4, t)
    # 20 packs (5 × 4) -> 10 watches (5 × 2)
    for j in range(20):
        x, y = 220 + (j % 5) * 160, 330 + (j // 5) * 120 + dy
        k = pop(E['w20'] - 0.3 + 0.03 * j, t, 2.2)
        crumbs(c, x, y, 95 * lerp(0.5, 1, k), a * cl(k * 2) * (1 - swap))
    for j in range(10):
        x, y = 220 + (j % 5) * 160, 390 + (j // 5) * 160 + dy
        k = pop(E['w10'] - 0.05 + 0.05 * j, t, 2.0)
        put(c, mini(0, 128), x, y, lerp(0.4, 1.0, k), a * cl(k * 2) * swap)
    k1 = sm(E['w10'] + 0.2, E['w10'] + 0.5, t)
    text(c, '10 × Swiss Watch ≈ 78 000 ₽', 46, 'Heavy', WHITE, 540, 740 + dy, a * k1)
    arrow(c, 540, 790 + dy, 540, 850 + dy, sm(E['w_today'], E['w_today'] + 0.4, t), a)
    kp = pop(E['w_phone'] - 0.3, t, 1.6)
    phone(c, 540, 1065 + dy, lerp(260, 400, kp), a * cl(kp * 2), 'iPhone\n16e', glow=kp)
    text(c, '66 590 ₽ · iPort, 07.11.2026', 30, 'Semibold', ACC, 540, 1300 + dy, a * cl(kp * 2))
    text(c, 'Fragment: 10 самых дешёвых лотов = 871 TON', 24, 'Medium', SRC, 540, 250 + dy, a * k1)


# ------------------------------------------------------------------ 6–7 Durov's Cap (after RubUp)
def cap(c, t):
    a, ki, ko = win(t, E['cap'] + 0.1, E['cph'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'НОЯБРЬ 2024', 44, 'Heavy', GREY, 540, 250 + dy, a)
    k = pop(E['cap'] + 0.1, t, 1.6)
    gift(c, CAPG, t, 540, 560 + dy + 40 * (1 - k), 400, lerp(0.6, 1.0, k), a * cl(k * 2))
    text(c, "Durov's Cap", 48, 'Semibold', ACC, 540, 800 + dy, a)
    price(c, t, E['c15'], '$15', 130, WHITE, 540, 930 + dy, a)
    kz = pop(E['c_pizza'] - 0.35, t, 1.7)
    if kz > 0:
        text(c, '=', 80, 'Heavy', GREY, 380, 1105 + dy, a * cl(kz * 2))
        pizza(c, 570, 1120 + dy, lerp(60, 120, kz), a * cl(kz * 2))
    text(c, 'стартовая цена · ForkLog 25.08.2025', 24, 'Medium', SRC, 540, 300 + dy, a)


def cap_phone(c, t):
    a, ki, ko = win(t, E['cph'] + 0.05, E['pepe'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    swap = sm(E['c_caps'] - 0.15, E['c_caps'] + 0.35, t)
    for j, x in enumerate((360, 720)):
        k = pop(E['c2'] - 0.3 + 0.12 * j, t, 1.8)
        pizza(c, x, 470 + dy, 110 * lerp(0.5, 1, k), a * cl(k * 2) * (1 - swap),
              crossed=sm(E['c2'] + 0.3, E['c2'] + 0.7, t))
        kc = pop(E['c_caps'] - 0.1 + 0.1 * j, t, 1.8)
        gift(c, CAPG, t, x, 470 + dy, 280, lerp(0.5, 1, kc), a * cl(kc * 2) * swap, off=0.4 * j)
    k1 = sm(E['c_caps'] + 0.1, E['c_caps'] + 0.4, t)
    text(c, "2 × Durov's Cap ≈ 86 000 ₽", 46, 'Heavy', WHITE, 540, 690 + dy, a * k1)
    arrow(c, 540, 740 + dy, 540, 810 + dy, sm(E['c_phone'] - 0.5, E['c_phone'] - 0.1, t), a)
    kp = pop(E['c_phone'] - 0.25, t, 1.6)
    phone(c, 540, 1050 + dy, lerp(260, 400, kp), a * cl(kp * 2), 'iPhone\n17e', glow=kp)
    text(c, '82 390 ₽ · iPort, 07.11.2026', 30, 'Semibold', ACC, 540, 1290 + dy, a * cl(kp * 2))
    text(c, 'Fragment: два самых дешёвых лота = 963 TON', 24, 'Medium', SRC, 540, 250 + dy, a * k1)


# ------------------------------------------------------------------ 8–9 Plush Pepe
def pepe(c, t):
    a, ki, ko = win(t, E['pepe'] + 0.05, E['pnow'], dout=0.3)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'ДЕКАБРЬ 2024', 44, 'Heavy', GREY, 540, 250 + dy, a)
    k = pop(E['pepe'], t, 1.6)
    gift(c, PEPEG, t, 540, 560 + dy + 40 * (1 - k), 400, lerp(0.6, 1.0, k), a * cl(k * 2))
    text(c, 'Plush Pepe', 48, 'Semibold', ACC, 540, 800 + dy, a)
    price(c, t, E['p30'], '$30', 130, WHITE, 540, 930 + dy, a)
    for j, (x, rot) in enumerate(((440, -0.18), (640, 0.14))):
        kk = pop(E['p_kino'] - 0.3 + 0.12 * j, t, 1.8)
        if kk > 0:
            ticket(c, x, 1110 + dy + 20 * (1 - kk), 200 * lerp(0.6, 1, kk), a * cl(kk * 2), rot)
    text(c, 'стартовая цена · ForkLog 25.08.2025', 24, 'Medium', SRC, 540, 300 + dy, a)


def pepe_now(c, t):
    a, ki, ko = win(t, E['pnow'] + 0.05, E['outro'], dout=0.35)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki) - 90 * ko
    text(c, 'НОЯБРЬ 2026', 44, 'Heavy', ACC, 540, 250 + dy, a)
    k = pop(E['pnow'], t, 1.6)
    gift(c, PEPEG, t, 540, 470 + dy + 30 * (1 - k), 300, lerp(0.6, 1.0, k), a * cl(k * 2))
    v = 649000 * fx.ease_out(cl((t - E['p649'] + 0.3) / 1.2))
    kk = sm(E['p649'] - 0.5, E['p649'] - 0.2, t)
    text(c, counter(v, 1000) + ' ₽', 120, 'Heavy', ACC if v >= 648500 else WHITE, 540, 700 + dy, a * kk,
         1 + 0.05 * fx.bump(t - E['p649'] - 0.9, 3, 7))
    text(c, '7 250 TON · самый дешёвый на Fragment', 32, 'Semibold', GREY, 540, 790 + dy, a * kk)
    for j, x in enumerate((290, 540, 790)):
        kp = pop(E['p3'] - 0.1 + 0.18 * j, t, 1.7)
        phone(c, x, 1020 + dy, lerp(200, 320, kp), a * cl(kp * 2), 'iPhone\n18 Pro Max', glow=kp * 0.5)
    k3 = sm(E['p3'] + 0.5, E['p3'] + 0.8, t)
    text(c, '3 × 179 990 ₽ = 539 970 ₽ · iPort', 30, 'Semibold', ACC, 540, 1240 + dy, a * k3)
    text(c, 'Fragment · 07.11.2026 · 1 TON ≈ 89,5 ₽', 24, 'Medium', SRC, 540, 300 + dy, a)


# ------------------------------------------------------------------ 10 bait for comments
def outro(c, t):
    a, ki, _ = win(t, E['outro'] + 0.05, None)
    if a <= 0.004:
        return
    dy = 40 * (1 - ki)
    text(c, 'КАКОЙ ПОДАРОК', 80, 'Heavy', WHITE, 540, 300 + dy, a)
    text(c, 'ВЫ УПУСТИЛИ?', 104, 'Heavy', ACC, 540, 415 + dy, a, 1 + 0.05 * fx.bump(t - E['o_which'], 3, 7))
    tw = [E['o_which'] + 0.1 * i for i in range(3)]
    choice_cards(c, t, E['outro'], [(WATCHG, '×50', tw[0]), (CAPG, '×34', tw[1]), (PEPEG, '×265', tw[2])], dy, a)
    text(c, 'рост в долларах от стартовой цены', 28, 'Medium', GREY, 540, 960 + dy, a)
    comment_field(c, t, E['o_sorry'] - 0.4, 'Я не купил… ', y=1110)


def render_at(t):
    c = _bg().copy()
    hook(c, t)
    count(c, t)
    watch(c, t)
    watch_now(c, t)
    watch_phone(c, t)
    cap(c, t)
    cap_phone(c, t)
    pepe(c, t)
    pepe_now(c, t)
    outro(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
