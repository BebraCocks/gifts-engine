"""Flat 2D cartoon characters drawn in code: Алексей (very thin, hungry) and Михаил (round, carefree).

Units: a character stands with feet at (0, 0), y grows downward, ~1000 units tall. `Pen` maps units to
supersampled pixels: px = (origin + unit * scale) * SS. Every shape gets a dark outline drawn underneath.
A pose is a plain dict (see ALEX / MISHA defaults); `mix(p, q, a)` interpolates poses for animation.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

INK = (29, 27, 46)
SS = 2


def lerp(a, b, t):
    return a + (b - a) * t


def mix(p, q, a):
    """Interpolate two poses (numbers and tuples); non-numeric keys switch at a = 0.5."""
    out = dict(p)
    for k, v in q.items():
        if k not in p:
            out[k] = v
        elif isinstance(v, (int, float)) and isinstance(p[k], (int, float)) and not isinstance(v, bool):
            out[k] = lerp(p[k], v, a)
        elif isinstance(v, tuple) and isinstance(p[k], tuple) and len(v) == len(p[k]):
            out[k] = tuple(lerp(x, y, a) for x, y in zip(p[k], v))
        else:
            out[k] = v if a >= 0.5 else p[k]
    return out


def tint(rgb, to, a):
    return tuple(int(lerp(c, d, a)) for c, d in zip(rgb, to))


def shade(rgb, k=0.78):
    return tuple(int(c * k) for c in rgb)


class Pen:
    def __init__(self, draw, ox, oy, scale, ol=6.0):
        self.d = draw
        self.ox, self.oy, self.s = ox, oy, scale
        self.ol = ol * SS                    # outline width in supersampled px

    def P(self, x, y):
        return ((self.ox + x * self.s) * SS, (self.oy + y * self.s) * SS)

    def L(self, v):
        return v * self.s * SS

    def ellipse(self, cx, cy, rx, ry, fill, outline=True, rot=0.0):
        if rot:
            pts = [(cx + rx * math.cos(a) * math.cos(rot) - ry * math.sin(a) * math.sin(rot),
                    cy + rx * math.cos(a) * math.sin(rot) + ry * math.sin(a) * math.cos(rot))
                   for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
            return self.poly(pts, fill, outline)
        x, y = self.P(cx, cy)
        a, b = self.L(rx), self.L(ry)
        if outline:
            o = self.ol
            self.d.ellipse([x - a - o, y - b - o, x + a + o, y + b + o], fill=INK)
        self.d.ellipse([x - a, y - b, x + a, y + b], fill=fill)

    def poly(self, pts, fill, outline=True):
        q = [self.P(x, y) for x, y in pts]
        if outline:
            self.d.line(q + [q[0]], fill=INK, width=int(self.ol * 2), joint='curve')
            for p in q:
                r = self.ol
                self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=INK)
        self.d.polygon(q, fill=fill)

    def limb(self, pts, w, fill, outline=True):
        q = [self.P(x, y) for x, y in pts]
        W = self.L(w)
        for col, ww in ((INK, W + 2 * self.ol), (fill, W)) if outline else ((fill, W),):
            self.d.line(q, fill=col, width=max(1, int(ww)), joint='curve')
            for p in (q[0], q[-1]):
                r = ww / 2
                self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    def line(self, pts, w, col=INK):
        q = [self.P(x, y) for x, y in pts]
        W = max(1, int(self.L(w)))
        self.d.line(q, fill=col, width=W, joint='curve')
        for p in (q[0], q[-1]):
            r = W / 2
            self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)

    def dot(self, cx, cy, r, col):
        x, y = self.P(cx, cy)
        R = self.L(r)
        self.d.ellipse([x - R, y - R, x + R, y + R], fill=col)


def sub(pen, cx, cy, k):
    """Same drawing surface, geometry scaled by k around unit point (cx, cy)."""
    q = Pen(pen.d, pen.ox + cx * pen.s * (1 - k), pen.oy + cy * pen.s * (1 - k), pen.s * k, 1.0)
    q.ol = pen.ol
    return q


HEAD = 1.32


def curve(x0, y0, x1, y1, bend, n=12):
    """Quadratic arc from (x0,y0) to (x1,y1); bend lifts the middle (negative = up)."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + bend
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1,
             (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1) for t in np.linspace(0, 1, n)]


def arm_pts(sx, sy, a1, a2, l1, l2):
    """Shoulder -> elbow -> hand. Angles in degrees from straight down, positive = towards +x."""
    r1, r2 = math.radians(a1), math.radians(a1 + a2)
    ex, ey = sx + l1 * math.sin(r1), sy + l1 * math.cos(r1)
    hx, hy = ex + l2 * math.sin(r2), ey + l2 * math.cos(r2)
    return (sx, sy), (ex, ey), (hx, hy)


# ------------------------------------------------------------------ face (shared)
def mouth(pen, cx, cy, w, smile, open_, teeth=True, tongue=True, lip=None):
    """smile: -1 (sad) .. 1 (grin); open_: 0..1."""
    xs = np.linspace(-w, w, 15)
    k = (xs / w) ** 2
    up = cy - smile * 16 * (1 - k) * 0 + smile * 14 * k * -1
    up = cy + smile * 14 * (k - 0.35)
    up = cy - smile * 12 * k + smile * 4
    if open_ < 0.06:
        pen.line(list(zip(xs, up)), 6, INK)
        return
    dn = up + open_ * 70 * (1 - k ** 1.4) * (0.6 + 0.4 * max(0, smile) + 0.3 * max(0, -smile))
    pts = list(zip(xs, up)) + list(zip(xs[::-1], dn[::-1]))
    pen.poly(pts, (110, 30, 46))
    if teeth and open_ > 0.15:
        tw = w * 0.78
        tx = np.linspace(-tw, tw, 11)
        tk = (tx / w) ** 2
        tu = cy - smile * 12 * tk + smile * 4 + 2
        th = min(16, open_ * 26)
        pen.poly(list(zip(tx, tu)) + list(zip(tx[::-1], (tu + th)[::-1])), (250, 248, 240), outline=False)
    if tongue and open_ > 0.35:
        bot = float(dn[7])
        pen.ellipse(cx, bot - open_ * 14, w * 0.42, open_ * 15, (226, 96, 110), outline=False)


def eye(pen, cx, cy, r, open_, look, brow, side, angry=0.0, sad=0.0, pupil=0.42, white=(255, 255, 255),
        bags=0.0, twitch=0.0):
    """side: -1 left eye, +1 right eye (screen). brow: (dy, tilt)."""
    ry = r * 1.18 * max(0.06, open_)
    if bags > 0:
        pen.line(curve(cx - r * 0.9, cy + r * 1.15, cx + r * 0.9, cy + r * 1.15, r * 0.55), 4 + bags * 3,
                 tint((205, 180, 215), (180, 150, 200), bags))
    if open_ < 0.12:
        pen.line(curve(cx - r, cy, cx + r, cy, r * 0.35), 7)
    else:
        pen.ellipse(cx, cy, r, ry, white)
        px = cx + look[0] * r * 0.45
        py = cy + look[1] * ry * 0.4
        pr = r * pupil
        pen.ellipse(px, py, pr, min(pr, ry * 0.85), INK, outline=False)
        pen.dot(px - pr * 0.35, py - pr * 0.4, pr * 0.32, (255, 255, 255))
        if open_ < 0.98:                                  # upper lid
            lid = cy - ry
            pen.line([(cx - r, lid + 2), (cx + r, lid + 2)], 5)
    # brow: inner end is towards the nose (x = 0)
    dy, tilt = brow
    tilt = tilt - angry * 26 + sad * 22
    inner = cx - side * r * 0.9
    outer = cx + side * r * 1.0
    by = cy - r * 1.55 + dy
    pen.line([(outer, by - tilt * 0.25), (inner, by + tilt * 0.75)], 11 + angry * 3)
    if twitch > 0:
        for k in range(3):
            a = math.radians(-60 + 60 * k) * side
            pen.line([(cx + side * (r * 1.35) * math.cos(a), cy - r * 1.3 + r * math.sin(a) * 0.6),
                      (cx + side * (r * 1.75) * math.cos(a), cy - r * 1.55 + r * math.sin(a) * 0.8)], 5)


def drop(pen, x, y, r, col=(130, 200, 255)):
    pen.poly([(x, y - r * 2.1), (x + r * 0.9, y - r * 0.1), (x, y + r), (x - r * 0.9, y - r * 0.1)], col)
    pen.dot(x - r * 0.3, y - r * 0.2, r * 0.25, (230, 245, 255))


def steam(pen, x, y, s, phase):
    for k in range(3):
        u = (phase + k / 3) % 1.0
        r = s * (0.4 + u)
        a = (1 - u)
        col = tint((255, 255, 255), (230, 230, 235), u)
        if a > 0.05:
            pen.ellipse(x + math.sin(u * 6 + k) * s * 0.4, y - u * s * 3.2, r, r * 0.8, col)


def phone(pen, x, y, ang, scale=1.0, screen=(40, 60, 110), glow=False, cracked=False):
    w, h = 46 * scale, 86 * scale
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    def R(px, py):
        return (x + px * c - py * s, y + px * s + py * c)
    pen.poly([R(-w, -h), R(w, -h), R(w, h), R(-w, h)], (34, 36, 48))
    m = 6 * scale
    pen.poly([R(-w + m, -h + m * 2), R(w - m, -h + m * 2), R(w - m, h - m * 2), R(-w + m, h - m * 2)], screen,
             outline=False)
    if cracked:
        for a, b in (((-0.2, -0.6), (0.5, 0.1)), ((0.5, 0.1), (0.1, 0.7)), ((0.5, 0.1), (-0.6, 0.3))):
            pen.line([R(a[0] * w, a[1] * h), R(b[0] * w, b[1] * h)], 3, (230, 230, 240))


# ------------------------------------------------------------------ Алексей
ALEX = dict(
    x=0.0, y=0.0, lean=0.0, bob=0.0, head_tilt=0.0, head_dx=0.0,
    thin=1.0,                               # 0 = normal schoolboy, 1 = starved
    eye_open=0.9, look=(0.0, 0.1), brow=(0.0, 0.0), angry=0.0, sad=0.0,
    smile=0.15, mouth=0.0, red=0.0, pale=0.6, tears=0.0, sweat=0.0, steam=0.0, twitch=0.0,
    # arms: (shoulder angle, elbow bend) degrees; left = screen left
    la=(8.0, -6.0), ra=(8.0, -6.0), phone_hand=None, phone_ang=0.0, phone_glow=False,
    shake=0.0, t=0.0, jaw=0.0, wide=0.0,
)


def draw_alex(pen, p):
    t = p['t']
    sx = p['x'] + (math.sin(t * 61) * 6 + math.sin(t * 43) * 4) * p['shake']
    sy = p['y'] + p['bob']
    th = p['thin']
    skin = tint((255, 226, 204), (246, 232, 220), p['pale'])          # fair skin; pale = whiter, not yellow
    skin = tint(skin, (255, 128, 118), min(1.0, p['red']) * 0.8)
    hood = (92, 110, 148)
    jeans = (58, 72, 110)
    lean = p['lean']
    # body proportions
    sh = lerp(112, 80, th)                   # shoulder half-width (the hoodie hangs on bones)
    hip = lerp(88, 76, th)
    top = -560
    neck_w = lerp(28, 13, th)
    pen_x = lambda x, y: (sx + x + lean * (-y) / 1000, sy + y)
    # legs
    for side in (-1, 1):
        lx = side * lerp(40, 30, th)
        pen.limb([pen_x(lx, -300), pen_x(lx * 1.05, -150), pen_x(lx * 1.1, -22)], lerp(62, 34, th), jeans)
        pen.ellipse(*pen_x(lx * 1.1 + side * 14, -12), 46, 20, (235, 235, 240))
        pen.line([pen_x(lx * 1.1 + side * 14 - 40, -4), pen_x(lx * 1.1 + side * 14 + 40, -4)], 6, (200, 70, 70))
    # back arm (screen right) drawn first
    def arm(sxo, ang, side):
        s0 = pen_x(side * (sh - 12), top + 34)
        a1, a2 = ang[0] * side, ang[1] * side
        (x0, y0), (ex, ey), (hx, hy) = arm_pts(s0[0], s0[1], a1, a2, 215, 200)
        pen.limb([(x0, y0), (ex, ey)], lerp(62, 40, th), hood)
        pen.limb([(ex, ey), (hx, hy)], lerp(54, 34, th), hood)
        # wrist + hand
        wx, wy = lerp(ex, hx, 0.93), lerp(ey, hy, 0.93)
        pen.limb([(wx, wy), (hx, hy)], 16, skin)
        pen.ellipse(hx, hy + 10, 26, 28, skin)
        return hx, hy + 10
    hand_r = arm(0, p['ra'], 1)
    # torso: baggy hoodie
    pts = [pen_x(-sh, top + 40), pen_x(-sh + 18, top + 4), pen_x(-30, top - 10), pen_x(30, top - 10),
           pen_x(sh - 18, top + 4), pen_x(sh, top + 40), pen_x(hip + 22, -300), pen_x(hip + 12, -268),
           pen_x(-hip - 12, -268), pen_x(-hip - 22, -300)]
    pen.poly(pts, hood)
    # pocket + drawstrings + wrinkles show the loose fit
    pen.poly([pen_x(-62, -390), pen_x(62, -390), pen_x(80, -300), pen_x(-80, -300)], shade(hood, 0.86))
    for side in (-1, 1):
        pen.line([pen_x(side * 22, top + 4), pen_x(side * 26, top + 90)], 5, (236, 236, 240))
    for k in range(int(2 + 3 * th)):
        yy = top + 130 + k * 42
        pen.line(curve(*pen_x(-sh + 20, yy), *pen_x(-sh + 70, yy + 20), 6), 4, shade(hood, 0.7))
    # hood ring
    pen.poly([pen_x(-62, top - 2), pen_x(-34, top - 30), pen_x(34, top - 30), pen_x(62, top - 2),
              pen_x(30, top + 22), pen_x(-30, top + 22)], shade(hood, 0.88))
    # neck
    hx0, hy0 = pen_x(p['head_dx'], top - 26)
    pen.limb([(hx0, hy0 + 10), (hx0, hy0 - 40)], neck_w * 2, skin)
    draw_alex_head(sub(pen, hx0, hy0 - 120, HEAD), hx0, hy0 - 120 - 40, p, skin)
    # front arm (screen left) on top
    hand_l = arm(0, p['la'], -1)
    if p['phone_hand']:
        hx, hy = hand_l if p['phone_hand'] == 'l' else hand_r
        phone(pen, hx, hy - 30, p['phone_ang'], 1.0, (60, 120, 220) if p['phone_glow'] else (36, 48, 80),
              cracked=p.get('cracked', False))
        hx2 = hx + (14 if p['phone_hand'] == 'l' else -14)
        pen.ellipse(hx2, hy + 4, 24, 22, skin)                 # thumb over the phone
    return hand_l, hand_r


def draw_alex_head(pen, cx, cy, p, skin):
    th = p['thin']
    tl = p['head_tilt']
    rx, ry = lerp(112, 100, th), lerp(122, 132, th)
    hair = (52, 40, 44)
    # back hair spikes
    spikes = []
    for k in range(9):
        a = math.radians(-170 + k * 20)
        rr = rx * (1.12 + 0.18 * (k % 2))
        spikes.append((cx + math.cos(a) * rr, cy - 20 + math.sin(a) * ry * 1.05))
    pen.poly([(cx - rx * 1.02, cy + 10)] + spikes + [(cx + rx * 1.02, cy + 10)], hair)
    # ears
    for side in (-1, 1):
        pen.ellipse(cx + side * rx * 0.98, cy + 10, 22, 30, skin)
    # head with a narrow jaw: ellipse + chin polygon
    pen.ellipse(cx, cy, rx, ry * 0.92, skin)
    jaw = lerp(0.82, 0.62, th)
    pen.poly([(cx - rx * 0.93, cy + 8), (cx - rx * jaw, cy + ry * 0.72), (cx - rx * 0.28, cy + ry * 1.04),
              (cx + rx * 0.28, cy + ry * 1.04), (cx + rx * jaw, cy + ry * 0.72), (cx + rx * 0.93, cy + 8)],
             skin, outline=False)
    pen.line(curve(cx - rx * jaw, cy + ry * 0.72, cx - rx * 0.28, cy + ry * 1.04, 6)
             + curve(cx - rx * 0.28, cy + ry * 1.04, cx + rx * 0.28, cy + ry * 1.04, 8)
             + curve(cx + rx * 0.28, cy + ry * 1.04, cx + rx * jaw, cy + ry * 0.72, -6), 6)
    pen.line(curve(cx - rx * 0.93, cy + 8, cx - rx * jaw, cy + ry * 0.72, -2), 6)
    pen.line(curve(cx + rx * 0.93, cy + 8, cx + rx * jaw, cy + ry * 0.72, 2), 6)
    # hollow cheeks
    if th > 0.2:
        for side in (-1, 1):
            pen.line(curve(cx + side * rx * 0.62, cy + 26, cx + side * rx * 0.5, cy + ry * 0.62, side * -10),
                     4, tint(skin, (190, 160, 160), 0.5 * th))
    # fringe
    pen.poly([(cx - rx * 1.02, cy - 18), (cx - rx * 0.7, cy - ry * 0.95), (cx, cy - ry * 1.08),
              (cx + rx * 0.75, cy - ry * 0.95), (cx + rx * 1.02, cy - 12), (cx + rx * 0.62, cy - 52),
              (cx + rx * 0.4, cy - 30), (cx + rx * 0.1, cy - 62), (cx - rx * 0.2, cy - 34),
              (cx - rx * 0.5, cy - 64), (cx - rx * 0.72, cy - 30)], hair)
    if p['red'] > 0.3:                                     # anger vein
        vx, vy = cx + rx * 0.5, cy - ry * 0.55
        a = (p['red'] - 0.3) / 0.7
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            pen.line([(vx + dx * 5, vy + dy * 5), (vx + dx * 18 * a, vy + dy * 18 * a)], 7, (200, 30, 40))
    ey = cy + 6
    er = 27 * (1 + p['wide'] * 0.35)
    look = p['look']
    for side in (-1, 1):
        eye(pen, cx + side * rx * 0.42, ey, er, p['eye_open'], look, p['brow'], side, p['angry'], p['sad'],
            pupil=0.40 - p['wide'] * 0.14, bags=0.5 + 0.5 * th, twitch=p['twitch'] if side > 0 else 0)
    # nose
    pen.line(curve(cx + 4, ey + 20, cx + 10, ey + 58, 0) + curve(cx + 10, ey + 58, cx - 8, ey + 62, 4), 5)
    my = cy + ry * 0.66 + p["jaw"] * 12
    mouth(pen, cx, my, 44 + 10 * p['mouth'], p['smile'], p['mouth'] + p['jaw'] * 0.9)
    if p['tears'] > 0:
        for side in (-1, 1):
            u = (p['t'] * 1.3 + (side + 1) * 0.3) % 1
            drop(pen, cx + side * rx * 0.48, ey + 40 + u * 90 * p['tears'], 11)
    if p['sweat'] > 0:
        drop(pen, cx + rx * 0.95, cy - ry * 0.4 + p['sweat'] * 30, 13)
    if p['steam'] > 0:
        for side in (-1, 1):
            steam(pen, cx + side * rx * 1.05, cy - ry * 0.6, 30 * p['steam'], p['t'] * 1.6 + side * 0.25)


# ------------------------------------------------------------------ Михаил
MISHA = dict(
    x=0.0, y=0.0, lean=0.0, bob=0.0, head_dx=0.0,
    eye_open=0.85, look=(0.0, 0.05), brow=(0.0, 0.0), angry=0.0, sad=0.0, disgust=0.0,
    smile=0.45, mouth=0.0, chew=0.0, t=0.0,
    la=(14.0, -8.0), ra=(14.0, -8.0), phone_hand=None, phone_ang=0.0, phone_glow=False,
    bun=0.0, pizza=0.0, think=0.0, walk=0.0, wide=0.0,
)


def draw_misha(pen, p):
    t = p['t']
    sx, sy = p['x'], p['y'] + p['bob']
    skin = (255, 222, 200)
    suit = (214, 52, 58)
    stripe = (250, 250, 250)
    lean = p['lean']
    W = 1.0
    top = -560
    pen_x = lambda x, y: (sx + x + lean * (-y) / 1000, sy + y)
    # legs with an optional walk cycle
    ph = p['walk']
    for side in (-1, 1):
        sw = math.sin(ph * 2 * math.pi + (0 if side < 0 else math.pi)) * 26 * (1 if ph else 0)
        lift = max(0.0, math.sin(ph * 2 * math.pi + (0 if side < 0 else math.pi))) * 22 * (1 if ph else 0)
        lx = side * 52
        pen.limb([pen_x(lx, -290), pen_x(lx + sw * 0.5, -150 - lift * 0.4), pen_x(lx + sw, -26 - lift)], 74, suit)
        pen.line([pen_x(lx + side * 30, -280), pen_x(lx + sw + side * 30, -44 - lift)], 7, stripe)
        pen.ellipse(*pen_x(lx + sw + side * 16, -14 - lift), 54, 22, (40, 40, 52))
    def arm(ang, side):
        s0 = pen_x(side * 120, top + 64)
        (x0, y0), (ex, ey), (hx, hy) = arm_pts(s0[0], s0[1], ang[0] * side, ang[1] * side, 190, 180)
        pen.limb([(x0, y0), (ex, ey)], 68, suit)
        pen.limb([(ex, ey), (hx, hy)], 62, suit)
        pen.line([(x0 + side * 22, y0 + 10), (ex + side * 22, ey)], 6, stripe)
        pen.ellipse(hx, hy + 12, 32, 32, skin)
        return hx, hy + 12
    hand_r = arm(p['ra'], 1)
    # round torso
    pen.ellipse(*pen_x(0, -410), 160 * W, 170, suit)
    pen.line([pen_x(0, -560), pen_x(0, -250)], 6, shade(suit, 0.7))       # zip
    pen.ellipse(*pen_x(0, -560), 8, 8, (230, 230, 230))
    for side in (-1, 1):
        pen.line(curve(*pen_x(side * 150, -470), *pen_x(side * 120, -290), side * 0), 7, stripe)
    pen.poly([pen_x(-70, -580), pen_x(0, -520), pen_x(70, -580), pen_x(50, -560), pen_x(0, -540),
              pen_x(-50, -560)], (240, 240, 240))
    hx0, hy0 = pen_x(p['head_dx'], top - 20)
    draw_misha_head(sub(pen, hx0, hy0 - 100, HEAD), hx0, hy0 - 100 - 30, p, skin)
    hand_l = arm(p['la'], -1)
    if p['phone_hand']:
        hx, hy = hand_l if p['phone_hand'] == 'l' else hand_r
        phone(pen, hx, hy - 34, p['phone_ang'], 1.05, (60, 120, 220) if p['phone_glow'] else (36, 48, 80))
        pen.ellipse(hx + (16 if p['phone_hand'] == 'l' else -16), hy + 4, 28, 24, skin)
    if p['bun'] > 0:                                     # half-eaten bun in the right hand
        bx, by = hand_r
        pen.ellipse(bx, by - 24, 52 * p['bun'], 36 * p['bun'], (232, 170, 92))
        pen.ellipse(bx + 30 * p['bun'], by - 34, 18 * p['bun'], 16 * p['bun'], (250, 232, 196), outline=False)
        for k in range(3):
            pen.dot(bx - 18 + k * 16, by - 44, 3.5, (250, 240, 220))
    if p['pizza'] > 0:
        bx, by = hand_r
        s = p['pizza']
        pen.poly([(bx - 70 * s, by - 90 * s), (bx + 70 * s, by - 90 * s), (bx, by + 40 * s)], (250, 196, 80))
        pen.limb([(bx - 74 * s, by - 94 * s), (bx + 74 * s, by - 94 * s)], 24 * s, (210, 130, 60))
        for dx, dy in ((-24, -60), (18, -54), (0, -20)):
            pen.ellipse(bx + dx * s, by + dy * s, 13 * s, 13 * s, (200, 50, 50))
    return hand_l, hand_r


def draw_misha_head(pen, cx, cy, p, skin):
    rx, ry = 128, 118
    pen.ellipse(cx - rx * 0.98, cy + 14, 24, 30, skin)
    pen.ellipse(cx + rx * 0.98, cy + 14, 24, 30, skin)
    pen.ellipse(cx, cy, rx, ry, skin)
    # backwards cap
    cap = (40, 110, 200)
    pen.poly(curve(cx - rx * 0.98, cy - 26, cx + rx * 0.98, cy - 26, -ry * 1.7, 18), cap)
    pen.poly([(cx - rx * 1.25, cy - 6), (cx - rx * 0.92, cy - 36), (cx - rx * 0.8, cy - 10),
              (cx - rx * 1.1, cy + 20)], shade(cap, 0.8))
    pen.line(curve(cx - rx * 0.95, cy - 24, cx + rx * 0.95, cy - 24, 10), 8, shade(cap, 0.7))
    # hair tuft under the cap
    pen.poly([(cx + rx * 0.6, cy - 30), (cx + rx * 0.95, cy - 10), (cx + rx * 0.98, cy + 18),
              (cx + rx * 0.75, cy - 6)], (170, 110, 60))
    # cheeks
    for side in (-1, 1):
        pen.ellipse(cx + side * rx * 0.6, cy + 44, 26, 16, (252, 170, 160), outline=False)
    ey = cy + 4
    look = p['look']
    eo = p['eye_open'] * (1 - 0.55 * p['disgust'])
    for side in (-1, 1):
        eye(pen, cx + side * rx * 0.36, ey, 21 * (1 + 0.3 * p['wide']), eo, look,
            (p['brow'][0] - 8 * p['disgust'], p['brow'][1] + side * 0), side, p['angry'],
            p['sad'] + 0.5 * p['disgust'], pupil=0.5)
    pen.ellipse(cx + 2, ey + 40, 20, 16, tint(skin, (230, 150, 120), 0.4))
    chew = (math.sin(p['t'] * 13) * 0.5 + 0.5) * p['chew']
    my = cy + 78
    if p['disgust'] > 0.4:
        xs = np.linspace(-34, 34, 9)
        pen.line([(cx + x, my + 6 + (8 if k % 2 else -4)) for k, x in enumerate(xs)], 6)
        pen.line([(cx + 20, my + 4), (cx + 34, my + 30)], 6)
        pen.ellipse(cx + 34, my + 34, 9, 9, (226, 96, 110))         # tongue out «фу»
    else:
        mouth(pen, cx, my, 40 + 6 * p['mouth'], p['smile'] - chew * 0.2, p['mouth'] + chew * 0.15)
    if p['think'] > 0:                                     # hand-free «hmm» dots
        for k in range(3):
            a = min(1, max(0, p['think'] * 3 - k))
            if a > 0:
                pen.ellipse(cx + rx * 1.2 + k * 34, cy - ry * 0.9 - k * 34, 10 + k * 5, 10 + k * 5,
                            (255, 255, 255))


def render_layer(w, h, draws):
    """draws: list of (fn, ox, oy, scale, pose). Returns an RGBA image of size (w, h)."""
    im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for fn, ox, oy, scale, pose in draws:
        pen = Pen(d, ox, oy, scale, ol=max(2.2, 6.5 * scale))
        fn(pen, pose)
    return im.resize((w, h), Image.LANCZOS)
