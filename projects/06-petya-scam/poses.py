"""Full-body characters in different poses (author, 2026-11-05: «сделай им позы разные… оживи картину»).

A simple flat puppet: torso + two-segment arms and legs (thick round strokes) in each character's clothes,
the existing heads from chars.py on top. Poses are joint angles, so walking, dancing and bouncing are cycles.

    body, neck = figure_body('katya', 'sit_cross', phase=0.0, phone=True, glow=0.6)
    place_figure(canvas, 'katya', 'sit_cross', x, y_neck, scale, t, head_expr=dict(smile=0.6), phase=...)

Angles: degrees from straight down; positive turns the limb towards +x (screen right).
Local units: the neck at (0, 0), head half-width ≈ 100 (same as the bust heads).
"""
import functools
import math

from PIL import Image

import chars as C
from art import Layer, mixc, shade

BOX = (1000, 1300)
NECK = (500, 300)
SH_Y, HIP_Y = 52, 330
UPPER, FORE, THIGH, SHIN = 150, 140, 185, 180

CLOTH = {
    'petya': dict(top=C.PETYA['cloth'], top_sh=C.PETYA['cloth_sh'], sleeve=C.PETYA['cloth'], pants=(52, 64, 96),
                  shoe=(245, 245, 245), shoe2=(255, 138, 52), skin=C.PETYA['skin'], sh=C.PETYA['sh']),
    'katya': dict(top=C.KATYA['cloth'], top_sh=C.KATYA['cloth_sh'], sleeve=C.KATYA['cloth'],
                  pants=(236, 224, 206), shoe=(40, 34, 40), shoe2=(200, 160, 90), skin=C.KATYA['skin'],
                  sh=C.KATYA['sh']),
    'dima': dict(top=C.DIMA['cloth'], top_sh=C.DIMA['cloth_sh'], sleeve=C.DIMA['shirt'], pants=(96, 100, 112),
                 shoe=(30, 30, 36), shoe2=(60, 60, 70), skin=C.DIMA['skin'], sh=C.DIMA['sh']),
    'sery': dict(top=C.SERY['cloth'], top_sh=C.SERY['cloth_sh'], sleeve=C.SERY['cloth'], pants=(60, 70, 100),
                 shoe=(250, 250, 250), shoe2=(214, 58, 58), skin=C.SERY['skin'], sh=C.SERY['sh']),
    'vanya': dict(top=C.VANYA['cloth'], top_sh=C.VANYA['cloth_sh'], sleeve=None, pants=(70, 90, 140),
                  shoe=(40, 40, 50), shoe2=(250, 196, 64), skin=C.VANYA['skin'], sh=C.VANYA['sh']),
}


def _pt(p, ang, ln):
    a = math.radians(ang)
    return p[0] + ln * math.sin(a), p[1] + ln * math.cos(a)


def _limb(L, p0, a1, l1, a2, l2, w1, w2, col, col2=None, shade_col=None):
    p1 = _pt(p0, a1, l1)
    p2 = _pt(p1, a2, l2)
    L.stroke([p0, p1], w1, col, smooth=False)
    L.stroke([p1, p2], w2, col2 or col, smooth=False)
    L.ell(p1[0], p1[1], w1 / 2, w1 / 2, col)
    if shade_col:
        L.stroke([p0, p1], w1 * 0.3, shade_col, alpha=0.35, smooth=False)
    return p1, p2


# ------------------------------------------------------------------ poses
def pose(name, phase=0.0):
    """Returns dict: arms {'l': (a1, a2), 'r': ...}, legs {'l': (a1, a2, thigh_len_k), ...}, lift (body y)."""
    s = math.sin(2 * math.pi * phase)
    c = math.cos(2 * math.pi * phase)
    if name == 'stand':
        return dict(arms=dict(l=(-10, -4), r=(10, 4)), legs=dict(l=(-4, 0, 1), r=(4, 0, 1)), lift=0)
    if name == 'stand_phone':
        return dict(arms=dict(l=(-14, 100), r=(14, -100)), legs=dict(l=(-4, 0, 1), r=(4, 0, 1)), lift=0,
                    phone=True)
    if name == 'walk_phone':
        return dict(arms=dict(l=(-14, 100), r=(14, -100)),
                    legs=dict(l=(-4 + 14 * s, -4 + 6 * s + 14 * max(0, -s), 1),
                              r=(4 - 14 * s, 4 - 6 * s - 14 * max(0, s), 1)),
                    lift=-10 * abs(c), phone=True)
    if name == 'walk':
        return dict(arms=dict(l=(-8 - 22 * s, -4 - 30 * s), r=(8 + 22 * s, 4 + 30 * s)),
                    legs=dict(l=(-4 + 14 * s, -4 + 6 * s + 14 * max(0, -s), 1),
                              r=(4 - 14 * s, 4 - 6 * s - 14 * max(0, s), 1)), lift=-10 * abs(c))
    if name == 'pace':                                  # walking while laughing at the phone
        return pose('walk_phone', phase)
    if name == 'sit':
        return dict(arms=dict(l=(-14, 100), r=(14, -100)), legs=dict(l=(-14, -4, 0.42), r=(14, 4, 0.42)),
                    lift=0, phone=True, seat=True)
    if name == 'sit_cross':                             # one leg over the other, foot swinging with phase
        return dict(arms=dict(l=(-14, 100), r=(14, -100)),
                    legs=dict(l=(10, -6, 0.42), r=(-30, 40 + 12 * s, 0.55)), lift=0, phone=True, seat=True,
                    front='r')
    if name == 'sit_swing':                             # in love: both feet swinging
        return dict(arms=dict(l=(-14, 100), r=(14, -100)),
                    legs=dict(l=(-12, -10 + 22 * s, 0.42), r=(12, 10 - 22 * s, 0.42)), lift=0, phone=True,
                    seat=True)
    if name == 'sit_knees':                             # on the bed, knees up, phone on the knees
        return dict(arms=dict(l=(-20, 110), r=(20, -110)), legs=dict(l=(-150, 25, 0.75), r=(150, -25, 0.75)),
                    lift=0, phone=True, seat=True, knees=True)
    if name == 'slump':
        return dict(arms=dict(l=(-6, 40), r=(6, -40)), legs=dict(l=(-12, -2, 0.42), r=(12, 2, 0.42)),
                    lift=12, phone=True, seat=True)
    if name == 'jump':
        k = math.sin(math.pi * min(1.0, phase))
        return dict(arms=dict(l=(-150 - 15 * k, -165), r=(150 + 15 * k, 165)),
                    legs=dict(l=(-20 * k - 4, 30 * k, 1), r=(20 * k + 4, -30 * k, 1)), lift=-120 * k)
    if name == 'dance':
        return dict(arms=dict(l=(-140 + 25 * s, -170 + 30 * s), r=(140 + 25 * s, 170 + 30 * s)),
                    legs=dict(l=(-8 - 6 * s, 6 + 10 * abs(s), 1), r=(8 - 6 * s, -6 - 10 * abs(s), 1)),
                    lift=-18 * abs(s))
    if name == 'cheer':
        return dict(arms=dict(l=(-35, -150 + 20 * s), r=(35, 150 - 20 * s)),
                    legs=dict(l=(-6, 0, 1), r=(6, 0, 1)), lift=-10 * abs(s))
    raise KeyError(name)


# ------------------------------------------------------------------ torso per character
def _torso(L, who, P):
    sk = P['skin']
    if who == 'vanya' or who == 'dima':
        pass
    L.poly([(-28, -40), (28, -40), (32, 30), (-32, 30)], sk)                            # neck
    if who == 'petya':
        tm = L.shape([(-60, 8), (-122, 40), (-132, 180), (-124, 345), (124, 345), (132, 180), (122, 40), (60, 8)],
                     P['top'])
        L.shape([(70, 30), (130, 100), (136, 345), (70, 345), (86, 160)], P['top_sh'], clip=tm, alpha=0.7)
        L.shape([(-80, 0), (-96, 50), (0, 82), (96, 50), (80, 0), (0, 40)], shade(P['top'], 0.88))
        for s in (-1, 1):
            L.stroke([(s * 18, 60), (s * 20, 130)], 6, CLOTH['petya']['shoe2'])
            L.ell(s * 20, 134, 6, 7, CLOTH['petya']['shoe2'])
        L.stroke([(-80, 280), (-56, 220), (56, 220), (80, 280)], 5, P['top_sh'], alpha=0.8)
        L.poly([(-124, 318), (124, 318), (124, 348), (-124, 348)], shade(P['top'], 0.85))
        L.ell(-80, 120, 14, 14, CLOTH['petya']['shoe2'])
        L.ell(-80, 120, 6, 6, P['top'])
    elif who == 'katya':
        L.shape([(-48, 12), (-104, 40), (-112, 200), (-104, 340), (104, 340), (112, 200), (104, 40), (48, 12)],
                (250, 244, 236))
        L.shape([(-34, 14), (0, 70), (34, 14)], sk)
        L.stroke([(-36, 18), (-12, 56), (0, 62), (12, 56), (36, 18)], 3, C.KATYA['gold'])
        for s in (-1, 1):
            cm = L.shape([(s * 46, 12), (s * 120, 40), (s * 132, 200), (s * 128, 400), (s * 40, 400), (s * 56, 200),
                          (s * 70, 100)], P['top'])
            if s == 1:
                L.shape([(90, 50), (132, 200), (128, 400), (96, 400)], P['top_sh'], clip=cm, alpha=0.7)
            L.shape([(s * 46, 12), (s * 84, 22), (s * 96, 110), (s * 70, 160), (s * 62, 100)], shade(P['top'], 0.9))
        L.poly([(-104, 300), (104, 300), (108, 316), (-108, 316)], (180, 140, 100))         # belt
    elif who == 'dima':
        L.shape([(-50, 10), (-108, 36), (-116, 180), (-110, 340), (110, 340), (116, 180), (108, 36), (50, 10)],
                C.DIMA['shirt'])
        vm = L.poly([(-92, 50), (-40, 30), (0, 150), (40, 30), (92, 50), (104, 200), (100, 340), (-100, 340),
                     (-104, 200)], P['top'])
        L.poly([(40, 30), (92, 50), (104, 200), (100, 340), (60, 340), (60, 150)], P['top_sh'], clip=vm, alpha=0.7)
        L.poly([(-8, 22), (8, 22), (6, 36), (-6, 36)], C.DIMA['tie'])
        L.poly([(-6, 36), (6, 36), (14, 120), (0, 136), (-14, 120)], C.DIMA['tie'])
    elif who == 'sery':
        tm = L.shape([(-60, 8), (-124, 40), (-134, 180), (-124, 330), (124, 330), (134, 180), (124, 40), (60, 8)],
                     P['top'])
        L.shape([(70, 30), (130, 100), (136, 330), (70, 330), (86, 160)], P['top_sh'], clip=tm, alpha=0.7)
        L.shape([(-70, 0), (-76, 36), (0, 50), (76, 36), (70, 0), (0, 24)], (40, 44, 48))
        L.stroke([(0, 50), (0, 330)], 5, (210, 210, 210))
        L.poly([(-124, 312), (124, 312), (124, 340), (-124, 340)], (40, 44, 48))
    elif who == 'vanya':
        tm = L.shape([(-56, 8), (-118, 40), (-120, 180), (-112, 340), (112, 340), (120, 180), (118, 40), (56, 8)],
                     P['top'])
        L.shape([(70, 30), (118, 100), (120, 340), (70, 340), (86, 160)], P['top_sh'], clip=tm, alpha=0.7)
        L.ell(0, 170, 44, 44, (255, 255, 255), alpha=0.9)
        L.ell(0, 170, 22, 22, P['top'])


@functools.lru_cache(maxsize=512)
def figure_body(who, name, phase=0.0, glow=0.0):
    """RGBA body sprite (without the head); neck at NECK in the sprite."""
    P = CLOTH[who]
    pz = pose(name, phase)
    L = Layer(*BOX, ss=2).at(NECK[0], NECK[1] + pz['lift'])
    sk, sh = P['skin'], P['sh']
    pants = P['pants']
    seat = pz.get('seat')
    knees = pz.get('knees')
    front = pz.get('front')

    def leg(side):
        a1, a2, k = pz['legs'][side]
        sx = -1 if side == 'l' else 1
        hip = (sx * 56, HIP_Y)
        if knees:                                       # knees up towards the viewer: short, wide thighs
            p1 = (sx * 70, HIP_Y - 130)
            L.stroke([hip, p1], 92, pants, smooth=False)
            L.ell(p1[0], p1[1], 48, 48, pants)
            p2 = _pt(p1, a2 * 0.2, 160)
            L.stroke([p1, (p1[0] + sx * 10, p1[1] + 150)], 74, shade(pants, 0.85), smooth=False)
            L.ell(p1[0] + sx * 10, p1[1] + 170, 46, 22, P['shoe'])
            return
        tl = THIGH * k
        p1, p2 = _limb(L, hip, a1, tl, a2, SHIN, 84 if seat else 74, 66, pants, shade_col=shade(pants, 0.7))
        if seat:
            L.ell(p1[0], p1[1], 44, 40, mixc(pants, (255, 255, 255), 0.08))        # knee towards the viewer
        # shoe
        L.ell(p2[0] + sx * 6, p2[1] + 14, 46, 24, P['shoe'])
        L.stroke([(p2[0] - 30 + sx * 6, p2[1] + 26), (p2[0] + 36 + sx * 6, p2[1] + 26)], 6, P['shoe2'])

    def arm(side, in_front=True):
        a1, a2 = pz['arms'][side]
        sx = -1 if side == 'l' else 1
        shp = (sx * 112, SH_Y)
        sleeve = P['sleeve']
        if sleeve is None:                              # short sleeves (Vanya)
            p1 = _pt(shp, a1, UPPER * 0.45)
            L.stroke([shp, p1], 64, P['top'], smooth=False)
            p1b, p2 = _limb(L, p1, a1, UPPER * 0.55, a2, FORE, 50, 46, sk)
        else:
            p1, p2 = _limb(L, shp, a1, UPPER, a2, FORE, 60, 52, sleeve, shade_col=shade(sleeve, 0.7))
        L.ell(p2[0], p2[1], 28, 28, sk)
        return p2

    # back leg first when one leg crosses the other
    order = ['l', 'r'] if front != 'l' else ['r', 'l']
    if not knees:
        for side in order:
            leg(side)
    if seat and not knees:
        L.shape([(-128, HIP_Y - 20), (128, HIP_Y - 20), (132, HIP_Y + 50), (-132, HIP_Y + 50)], pants)
    _torso(L, who, P)
    if knees:
        for side in ('l', 'r'):
            leg(side)
    hands = [arm('l'), arm('r')]
    if pz.get('phone'):
        cx = (hands[0][0] + hands[1][0]) / 2
        cy = (hands[0][1] + hands[1][1]) / 2 - 20
        L.poly([(cx - 36, cy - 58), (cx + 36, cy - 58), (cx + 38, cy + 58), (cx - 38, cy + 58)], (28, 30, 40))
        L.poly([(cx - 30, cy - 52), (cx + 30, cy - 52), (cx + 32, cy + 52), (cx - 32, cy + 52)],
               mixc((40, 70, 110), (150, 210, 255), glow))
        for h in hands:                                 # hands over the phone edges
            L.ell(h[0], h[1], 28, 28, sk)
    return L.image()


def place_figure(canvas, who, name, x, y, scale, head_img, phase=0.0, glow=0.0, tilt=0.0, bob=0.0):
    """Body + head; (x, y) is the neck position on the canvas."""
    body = figure_body(who, name, round(phase * 16) / 16 % 1 if name not in ('jump',) else round(phase * 16) / 16,
                       round(glow * 4) / 4)
    lift = pose(name, phase)['lift']
    parts = [(body, x - NECK[0] * scale, y - NECK[1] * scale + bob, scale, 0.0, None)]
    hx, hy = x, y + (lift - 8) * scale + bob
    parts.append((head_img, hx - C.HC[0] * scale, hy - (C.HC[1] + 120) * scale, scale, tilt,
                  (C.HC[0], C.HC[1] + 120)))
    C.place(canvas, parts)
