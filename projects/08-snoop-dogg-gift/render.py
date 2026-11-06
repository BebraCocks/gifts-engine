"""08-snoop-dogg-gift: minimal picture. One object at a time, graphite, thin white lines, one accent (the lime
of Barks Lightyear's visor). Content time t -> RGB frame; RubUp via banner.Breaks (same in audio.py).
Heroes are only gifts: Snoop Dogg · Barks Lightyear (Lottie) and the 15 ⭐ bear (Lottie). No people, no nicknames."""
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

BG, WHITE, GREY, DIM, ACC = config.BACKGROUND, config.WHITE, config.GREY, config.DIM, config.ACCENT
GIFT = str(gifts_api.model_file(config.GIFT_NAME, config.MODEL_NAME, 'json'))
BEAR = str(gifts_api.original_file(config.BEAR_ID, 'json'))
GS = 640                                    # gift sprite size; scale with warp
ROW_Y, ROW_X, R0 = 1050, (270, 540, 810), 88  # the three conditions


# ------------------------------------------------------------------ helpers
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


# ------------------------------------------------------------------ captions (subtitles), not for the hook line
def _phr(k):
    acc = {config.MODEL_NAME.replace(' ', '\u00a0') + '.', 'лайк', 'Лайк', 'репост', 'комментарий',
           'десять', 'мишке', 'миллион', 'Снуп', 'полчаса'}
    ws = [(w, a) for w, a, b in WORDS[k]]
    first, second = config.MODEL_NAME.split()
    for j in range(len(ws) - 1):                    # keep «Barks Lightyear» on one line (no-break space)
        if ws[j][0] == first and ws[j + 1][0].startswith(second):
            ws[j:j + 2] = [(first + '\u00a0' + ws[j + 1][0], ws[j][1])]
            break
    return captions.phrase(ws, accent=acc, end=END[k] + 0.15)


CAP = captions.Captions([_phr(k) for k in range(1, len(LINES))], width=860, top=1330, size=52, weight='Semibold',
                        max_lines=2, color=WHITE, accent_color=ACC, shadow=False, fade_out=0.2, rise=10)


# ------------------------------------------------------------------ scene pieces
def gift_pose(t):
    """(cx, cy, scale, alpha) of the Snoop Dogg gift."""
    k = spr(-0.06, t, 1.6, 0.5)                                         # pops into the centre, clear of the title
    cx, cy, s, a = 540.0, 760 - 140 * (1 - k), lerp(0.55, 1.0, k), 1.0
    k = sm(E['real'] - 0.15, E['real'] + 0.45, t)                       # into the card
    cy, s = lerp(cy, 680, k), lerp(s, 0.80, k)
    k = sm(E['profile'] - 0.1, E['profile'] + 0.6, t)                    # into the profile cell
    cx, cy, s = lerp(cx, 300, k), lerp(cy, 900, k), lerp(s, 0.31, k)
    s *= 1 + 0.10 * fx.bump(t - E['profile'] - 0.6, 3.0, 7.0)
    k = sm(E['sold'], E['sold'] + 0.35, t)                               # out with the profile
    cy, a = cy - 120 * k, a * (1 - k)
    # back for the conditions
    k = spr(E['want'], t, 1.6, 0.55)
    if t > E['want']:
        cx, cy, s, a = 540.0, lerp(-300, 560, k), 0.66, 1.0
    k = sm(E['what'] - 0.1, E['what'] + 0.35, t)                         # makes room for the comment field
    cy, s = lerp(cy, 455, k), lerp(s, 0.48, k)
    k = sm(E['bears_in'], E['bears_in'] + 0.25, t)
    cy, a = cy - 90 * k, a * (1 - k)
    if t > E['f_snoop'] - 0.1:                                            # the finale: back to the opening pose
        k = spr(E['f_snoop'] - 0.1, t, 1.5, 0.55)
        cx, cy, s, a = 540.0, lerp(-300, 560, k), 0.66, 1.0
        k2 = sm(E['f_snoop'] + 1.5, E['f_snoop'] + 2.4, t)
        cy, s = lerp(cy, 760, k2), lerp(s, 1.0, k2)
    return cx, cy, s, a


def card(c, t):
    """L02: the Telegram gift card drawn around the model, rows, then the profile strip."""
    out = sm(E['profile'] - 0.1, E['profile'] + 0.3, t)
    if t < E['real'] - 0.1 or out >= 1 and t > E['sold'] + 0.4:
        pass
    p = sm(E['real'] - 0.1, E['real'] + 0.7, t)
    stroke(c, rrect_pts(170, 320, 910, 1240, 56), WHITE, 3, p, 1 - out)
    rows = [('Snoop Dogg', 60, 'Heavy', WHITE, 1010), (config.MODEL_NAME, 44, 'Semibold', ACC, 1085),
            ('модель · 2,5%', 32, 'Medium', GREY, 1145)]
    for j, (s, size, wgt, col, y) in enumerate(rows):
        k = sm(E['model'] - 0.1 + 0.12 * j, E['model'] + 0.25 + 0.12 * j, t)
        text(c, s, size, wgt, col, 540, y + 16 * (1 - k), k * (1 - out))
    # profile strip: an empty avatar, two bars, three gift cells (no faces, no names)
    k = sm(E['profile'] - 0.05, E['profile'] + 0.45, t) * (1 - sm(E['sold'], E['sold'] + 0.35, t))
    if k > 0.004:
        dy = -120 * sm(E['sold'], E['sold'] + 0.35, t) + 30 * (1 - k)
        disc(c, 540, 480 + dy, 96, DIM, k)
        rrect(c, 400, 616 + dy, 680, 642 + dy, 13, DIM, k)
        rrect(c, 450, 664 + dy, 630, 682 + dy, 9, (40, 40, 45), k)
        for j, x in enumerate(ROW_X[:0] or (300, 540, 780)):
            col = ACC if j == 0 and t > E['profile'] + 0.55 else DIM
            rrect(c, x - 110, 790 + dy, x + 110, 1010 + dy, 36, None, k, outline=col, width=3)
        text(c, 'ПОДАРКИ В ПРОФИЛЕ', 30, 'Semibold', GREY, 540, 1070 + dy, k)


def sold(c, t):
    k_in = sm(E['sold'] + 0.3, E['sold'] + 0.6, t)          # after the profile has left (no overlap)
    k_out = sm(E['want'] - 0.1, E['want'] + 0.25, t)
    a = k_in * (1 - k_out)
    if a <= 0.004:
        return
    dy = 40 * (1 - k_in) - 80 * k_out
    text(c, 'ПОЧТИ', 40, 'Semibold', GREY, 540, 600 + dy, a)
    v = 1_000_000 * fx.ease_out(cl((t - E['million'] + 0.1) / 1.25))
    n = int(round(v / 1000) * 1000) if v < 999_500 else 1_000_000
    s = f'{n:,}'.replace(',', ' ')
    pop = 1 + 0.06 * fx.bump(t - E['million'] - 1.15, 3, 7)
    text(c, s, 124, 'Heavy', WHITE if n < 1_000_000 else ACC, 540, 730 + dy, a, pop)
    text(c, 'РАСКУПИЛИ', 52, 'Heavy', WHITE, 540, 880 + dy, a * sm(E['bought'] - 0.05, E['bought'] + 0.2, t),
         1 + 0.05 * fx.bump(t - E['bought'], 3, 8))
    # half-hour track: fills while «раскупили … полчаса», stops short of the end («меньше чем за полчаса»)
    x0, x1, y = 200, 880, 1030 + dy
    rrect(c, x0, y - 4, x1, y + 4, 4, DIM, a)
    f = 0.88 * fx.ease_out(cl((t - E['bought']) / (E['half'] + 0.5 - E['bought'])))
    if f > 0.01:
        rrect(c, x0, y - 4, x0 + (x1 - x0) * f, y + 4, 4, ACC, a)
        disc(c, x0 + (x1 - x0) * f, y, 11, ACC, a)
    text(c, '0 мин', 30, 'Medium', GREY, x0, y + 50, a, left=True)
    hi = sm(E['half'], E['half'] + 0.25, t)
    col = tuple(int(lerp(g, w, hi)) for g, w in zip(GREY, WHITE))
    text(c, '30 мин', 30, 'Semibold', col, x1 - 88, y + 50, a, left=True)
    text(c, 'Decrypt · 10.07.2025', 26, 'Medium', (96, 96, 104), 540, 1190 + dy, a)


def icon_fill(i, t):
    """0..1 accent fill of condition icon i (0 like, 1 repost, 2 comment)."""
    first = (E['done'] + 0.05, E['friend'], END[KEY['comment']] - 0.15)[i]
    again = (E['f_like'], E['f_repost'], E['f_comment'])[i]
    reset = ON[KEY['final']] - 0.45
    if t < reset:
        return sm(first, first + 0.22, t)
    return 1 - sm(reset, reset + 0.25, t) + sm(again, again + 0.2, t) if t < again + 0.2 else 1.0


def row_pose(t):
    """(y, scale, label alpha, alpha) of the condition row."""
    y, s, la, a = ROW_Y, 1.0, 1.0, 1.0
    k = sm(E['bears_in'] + 0.25, E['bears_in'] + 0.6, t)    # after the gift and the field have left
    y, s, la = lerp(y, 300, k), lerp(s, 0.6, k), 1 - sm(E['bears_in'], E['bears_in'] + 0.25, t)
    k = sm(E['week'] - 0.1, E['week'] + 0.3, t)
    a *= 1 - k
    k = spr(ON[KEY['final']] - 0.45, t, 1.6, 0.6) if t > ON[KEY['final']] - 0.45 else 0
    if k:
        y, s, la, a = lerp(1500, ROW_Y, k), 1.0, 1.0, cl(k * 1.5)
    k = sm(E['f_snoop'] + 1.4, E['f_snoop'] + 2.2, t)
    y, a = y + 220 * k, a * (1 - k)
    return y, s, la, a


def conditions(c, t):
    if t < E['three'] - 0.35:
        return
    y, s, la, a = row_pose(t)
    if a <= 0.004:
        return
    names = ('ЛАЙК', 'РЕПОСТ', 'КОММЕНТАРИЙ')
    starts = (E['like'], E['repost'], E['comment'])
    for i, x0 in enumerate(ROW_X):
        x = 540 + (x0 - 540) * s
        r = R0 * s
        p = sm(E['three'] - 0.3 + 0.12 * i, E['three'] + 0.25 + 0.12 * i, t)
        st = starts[i]
        on_ = sm(st - 0.05, st + 0.45, t)
        fl = icon_fill(i, t)
        relit = (E['f_like'], E['f_repost'], E['f_comment'])[i]
        bump = 1 + 0.12 * fx.bump(t - ((E['done'], E['friend'], END[KEY['comment']] - 0.15)[i]), 3, 6) \
            + 0.12 * fx.bump(t - relit, 3, 6)
        if i == 0 and E['press'] < t < AD_STOP:                                    # «жми» — heart beats
            bump *= 1 + 0.07 * abs(math.sin((t - E['press']) * math.pi * 2.2))
        ring_col = tuple(int(lerp(w, a_, fl)) for w, a_ in zip(WHITE, ACC))
        stroke(c, circle_pts(x, y, r * bump), ring_col, 3, p, a)
        text(c, str(i + 1), round(54 * s), 'Medium', GREY, x, y, a * p * (1 - on_))
        sz = r * 0.9 * bump
        shape = (heart_pts(x, y, sz * 0.62), share_pts(x, y, sz * 1.05), bubble_pts(x, y + 4 * s, sz * 1.15))[i]
        if fl > 0.01:
            fill(c, shape, ACC, a * fl)
        stroke(c, shape, WHITE if fl < 0.5 else ACC, 3, on_, a)
        text(c, names[i], round(32 * s), 'Semibold', WHITE if fl < 0.5 else ACC, x, y + r + 48, a * la * on_)
        if fl > 0.05:                                                              # small ✓ badge
            bx, by = x + r * 0.72, y - r * 0.72
            disc(c, bx, by, 24 * s * min(1, fl * 1.2), ACC, a)
            stroke(c, check_pts(bx, by, 30 * s), BG, 4 * s, cl(fl * 1.4 - 0.3), a)
    # repost: a dot flies from the share icon to the right edge
    k = cl((t - E['friend']) / 0.5)
    if 0 < k < 1 and t < E['bears_in']:
        x = lerp(ROW_X[1], 1120, fx.ease_in(k))
        stroke(c, [(lerp(ROW_X[1], x, 0.35), y - 4), (x, y - 4)], ACC, 4, 1, (1 - k) * a)
        disc(c, x, y - 4, 12, ACC, a)


TYPED = 'поставлю его в профиль'


def comment_field(c, t):
    k_in = sm(E['what'] - 0.05, E['what'] + 0.35, t)
    k_out = sm(E['bears_in'], E['bears_in'] + 0.25, t)
    a = k_in * (1 - k_out)
    if a <= 0.004:
        return
    y = 790 + 30 * (1 - k_in) - 60 * k_out
    rrect(c, 120, y - 52, 900, y + 52, 52, (30, 30, 34), a, outline=(70, 70, 78), width=2)
    n = int(len(TYPED) * cl((t - E['what'] - 0.45) / 2.1))
    s = TYPED[:n]
    f = fx.font('Medium', 36)
    if n == 0:
        text(c, 'Добавить комментарий…', 36, 'Medium', GREY, 170, y, a, left=True)
        cx = 168
    else:
        text(c, s, 36, 'Medium', WHITE, 170, y, a, left=True)
        cx = 172 + f.getlength(s)
    if (t * 2.2) % 1 < 0.6 or 0 < n < len(TYPED):
        rrect(c, cx, y - 24, cx + 4, y + 24, 2, ACC, a)


BEAR_X = (220, 380, 540, 700, 860)
BEAR_Y = (720, 890)


def bears(c, t):
    if t < E['ten'] - 0.3 or t > E['week'] + 0.6:
        return
    out = sm(E['week'] - 0.1, E['week'] + 0.35, t)
    landed = 0
    for j in range(10):
        x, y = BEAR_X[j % 5], BEAR_Y[j // 5]
        t0 = E['ten'] - 0.25 + 0.075 * j
        k = spr(t0, t, 1.7, 0.5)
        if k <= 0:
            continue
        landed += t > t0 + 0.28
        hop = 18 * max(0, math.sin(cl((t - E['bear'] - 0.05 * j) / 0.35) * math.pi))
        yy = lerp(ROW_Y * 0 + 300, y, k) - hop + 80 * out
        im = lottie.frame(BEAR, t, size=140, offset=0.29 * j)
        put(c, im, x, yy, 1.0, cl(k * 2) * (1 - out))
    if landed:
        a = sm(E['ten'], E['ten'] + 0.2, t) * (1 - out)
        text(c, f'× {landed}', 120, 'Heavy', ACC, 540, 1130, a, 1 + 0.05 * fx.bump(t - E['ten'] - 0.9, 3, 7))


def result(c, t):
    k_in = sm(E['week'], E['week'] + 0.35, t)
    k_out = sm(ON[KEY['final']] - 0.5, ON[KEY['final']] - 0.15, t)
    a = k_in * (1 - k_out)
    if a <= 0.004:
        return
    dy = 30 * (1 - k_in) - 60 * k_out
    text(c, 'ЧЕРЕЗ', 40, 'Semibold', GREY, 540, 330 + dy, a)
    text(c, '7 ДНЕЙ', 120, 'Heavy', WHITE, 540, 450 + dy, a)
    # the pinned comment: one accent line for the Snoop, three bear lines, «+ ещё 7»
    kc = sm(E['random'] - 0.25, E['random'] + 0.15, t) * a
    if kc <= 0.004:
        return
    y0 = 600 + dy + 30 * (1 - kc)
    rrect(c, 140, y0, 940 - 40, y0 + 520, 40, (26, 26, 30), kc, outline=(58, 58, 64), width=2)
    pk = spr(E['pin'] - 0.1, t, 2.2, 0.5)
    pin(c, 210, y0 + 62 - 40 * (1 - pk), 46, ACC if pk > 0.5 else GREY, kc * cl(pk * 2 + 0.3))
    text(c, 'Закреплено', 30, 'Semibold', GREY, 250, y0 + 62, kc, left=True)
    rnd = np.random.default_rng(int(t * 9) if t < E['pin'] else 7)
    for j in range(4):
        yy = y0 + 150 + j * 92
        im = lottie.frame(GIFT if j == 0 else BEAR, t, size=72, offset=0.5 * j)
        put(c, im, 215, yy, 1.0, kc)
        wbar = 420 if t >= E['pin'] else int(rnd.integers(200, 520))      # names «shuffle» until the pin
        col = ACC if j == 0 else (88, 88, 96)
        rrect(c, 270, yy - 14, 270 + wbar, yy + 14, 14, col, kc)
    text(c, '+ ещё 7', 30, 'Semibold', GREY, 540, y0 + 500 - 22, kc)


def hook_title(c, t):
    a = 1 - sm(E['real'] - 0.3, E['real'] + 0.05, t)
    if a <= 0.004:
        return
    ws = WORDS[0]
    lines = (('ЭТОТ СНУП ДОГГ', 0), ('УЕДЕТ К ОДНОМУ', 3), ('ИЗ ВАС', 6))
    for j, (s, wi) in enumerate(lines):
        k = 1.0 + 0.06 * fx.bump(t - (ws[wi][1] if j else 0.0), 3, 8)   # the whole promise from the first frame
        col = ACC if j == 2 else WHITE
        text(c, s, 78 if j else 54, 'Heavy', GREY if j == 0 else col, 540, (215, 300, 395)[j] + 14 * (1 - min(k, 1)),
             a * min(k, 1), max(1.0, k))


def render_at(t):
    c = _bg().copy()
    card(c, t)
    sold(c, t)
    result(c, t)
    conditions(c, t)
    comment_field(c, t)
    bears(c, t)
    cx, cy, s, a = gift_pose(t)
    if a > 0.004 and cy > -400:
        put(c, lottie.frame(GIFT, t, size=GS), cx, cy, s, a)
    hook_title(c, t)
    fx.over(c, CAP.layer(t))
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
