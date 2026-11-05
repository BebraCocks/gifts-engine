"""Characters of «Петя и NFT» drawn in code: flat minimal 2D without outlines (cel shadow + soft blush).

Петя — 16, schoolboy-scammer: messy chestnut hair, light freckles, graphite hoodie with orange strings.
Катя — 23, rich and kind: long wavy honey hair, pearl earrings, camel coat, gold necklace.
Александр — the AI-made «dream guy» Petya hides behind: neat dark hair, stubble, navy blazer.
Дима — 13, first victim: bowl cut, big round glasses, school vest and tie.
Серый, Ваня — Petya's friends at the party.

Units: head centre at (0, 0), head half-width ≈ 100. Heads and bodies are separate cached sprites
(quantised pose), so the renderer can tilt/bob the head around the neck pivot.
Expression parameters (all heads): look (x, y), blink, brow (surprise lift), sad (inner brows up),
anger (inner brows down), smile, open_ (mouth), smirk (one corner up), teeth, shock (white eyes, tiny pupils),
sweat (drop on the temple).
"""
import functools
import math

from PIL import Image

from art import Layer, ellipse_pts, mixc, shade

EYE = (40, 32, 38)
WHITE = (255, 255, 255)
BLUSH = (240, 140, 140)

HEAD_BOX = (560, 680)        # head sprite size, head centre at HC
HC = (280, 330)
BODY_BOX = (760, 760)        # body sprite, neck pivot at BC
BC = (380, 120)


def _q(v, step):
    return round(v / step) * step


# ================================================================== palettes
PETYA = dict(skin=(250, 220, 200), sh=(232, 186, 166), hair=(112, 70, 46), hi=(150, 100, 66),
             lip=(190, 104, 100), cloth=(62, 66, 80), cloth_sh=(46, 48, 62), accent=(255, 138, 52))
KATYA = dict(skin=(252, 228, 214), sh=(236, 194, 178), hair=(226, 184, 122), hi=(246, 214, 160),
             hair_sh=(190, 140, 88), lip=(214, 104, 124), cloth=(198, 154, 108), cloth_sh=(164, 120, 80),
             top=(250, 244, 236), gold=(236, 190, 96))
ALEX = dict(skin=(242, 208, 184), sh=(222, 176, 152), hair=(46, 36, 34), hi=(84, 66, 60), lip=(178, 102, 96),
            cloth=(40, 54, 90), cloth_sh=(28, 38, 66), shirt=(246, 246, 250), shirt_sh=(204, 210, 224))
DIMA = dict(skin=(252, 224, 206), sh=(236, 190, 170), hair=(176, 136, 92), hi=(206, 170, 122),
            lip=(196, 108, 108), cloth=(46, 70, 130), cloth_sh=(34, 52, 100), shirt=(248, 248, 250),
            shirt_sh=(208, 212, 224), tie=(200, 50, 60), frame=(58, 56, 66))
SERY = dict(skin=(248, 216, 194), sh=(228, 182, 160), hair=(52, 40, 36), hi=(86, 66, 58), lip=(186, 102, 98),
            cloth=(70, 118, 84), cloth_sh=(52, 90, 64), cap=(214, 58, 58), cap_sh=(170, 40, 44))
VANYA = dict(skin=(252, 226, 210), sh=(236, 192, 172), hair=(214, 112, 58), hi=(240, 150, 90),
             lip=(196, 106, 104), cloth=(250, 196, 64), cloth_sh=(222, 160, 40))


# ================================================================== face parts
def _eyes(L, look, blink, brow, sad, anger, shock, *, spacing=40, y=0, r=(10.5, 13.5), brow_col, brow_w=8.5,
          lashes=False, brow_lift_r=0.0, glint=True):
    lx, ly = look
    for s in (-1, 1):
        cx, cy = s * spacing + lx * 5, y + ly * 4
        ry = r[1] * max(0.08, 1 - blink)
        if shock > 0.05 and blink < 0.5:
            # eyes go wide: white sclera, tiny pupil
            L.ell(cx - lx * 3, cy, r[0] * (1 + 0.55 * shock), ry * (1 + 0.45 * shock), WHITE)
            L.ell(cx, cy, r[0] * (1 - 0.45 * shock), ry * (1 - 0.45 * shock), EYE)
        else:
            L.ell(cx, cy, r[0], ry, EYE)
            if glint and blink < 0.5:
                L.ell(cx + 3.5, cy - 5 * (1 - blink), 3.6, 3.6 * (1 - blink), WHITE)
        if blink > 0.6:
            L.stroke([(cx - 11, cy), (cx, cy + 3), (cx + 11, cy)], 3.4, EYE)
        if lashes and blink <= 0.6:
            L.stroke([(cx + s * r[0] * 0.6, cy - ry * 0.8), (cx + s * (r[0] + 6), cy - ry - 3)], 3.2, EYE)
            L.stroke([(cx + s * r[0] * 0.95, cy - ry * 0.35), (cx + s * (r[0] + 9), cy - ry * 0.55)], 3.2, EYE)
        # brows: inner end up with sadness, down with anger; all up with surprise / shock
        lift = brow * 7 + shock * 9 + (brow_lift_r * 9 if s == 1 else 0)
        inner = (s * 18, y - 30 - lift - sad * 7 + anger * 9)
        mid = (s * 38, y - 36 - lift + sad * 2 - anger * 1)
        outer = (s * 56, y - 30 - lift * 0.8 + sad * 6 - anger * 3)
        L.stroke([inner, mid, outer], brow_w, brow_col)


def _mouth(L, smile, open_, smirk=0.0, teeth=0.0, *, y=62, w=22, col, lips=False):
    dx = smirk * 5
    if open_ > 0.08:
        h = 6 + 26 * open_
        top = y - 2 - smile * 3
        pts = [(-w * 0.8 + dx, top + smirk * 4), (dx, top - 2 + smile * 2), (w * 0.8 + dx, top - smirk * 6),
               (w * 0.55 + dx, top + h * 0.8), (dx, top + h + smile * 3), (-w * 0.55 + dx, top + h * 0.8)]
        m = L.shape(pts, (118, 48, 58))
        if teeth > 0:
            L.poly([(-w + dx, top - 10), (w + dx, top - 10), (w + dx, top + h * 0.34 * teeth + 1),
                    (-w + dx, top + h * 0.34 * teeth + 1)], WHITE, clip=m)
        L.ell(dx, top + h * 0.88, w * 0.42, h * 0.36, (212, 108, 116), clip=m)
    else:
        c = smile * 9
        pts = [(-w + dx, y - c * 0.6 + smirk * 3), (-w * 0.45 + dx, y + c * 0.35 + smirk * 1),
               (dx, y + c * 0.55), (w * 0.45 + dx, y + c * 0.35 - smirk * 4),
               (w + dx + smirk * 3, y - c * 0.6 - smirk * 11)]
        if lips:
            # soft filled lips: upper line + a fuller lower lip
            L.shape([(-w * 0.9 + dx, y - c * 0.5), (dx, y - 4 + c * 0.2), (w * 0.9 + dx, y - c * 0.5 - smirk * 8),
                     (w * 0.45 + dx, y + 9 + c * 0.2), (dx, y + 11 + c * 0.4), (-w * 0.45 + dx, y + 9 + c * 0.2)],
                    col)
            L.stroke(pts[1:4], 2.6, shade(col, 0.7), alpha=0.8)
            L.ell(dx + 4, y + 6, 5, 2.4, WHITE, alpha=0.35)
        else:
            L.stroke(pts, 5.4, col)


def _sweat(L, sweat, x=96, y=-56):
    if sweat > 0.05:
        a = min(1.0, sweat)
        L.shape([(x, y - 22), (x + 11, y), (x + 9, y + 12), (x, y + 16), (x - 9, y + 12), (x - 11, y)],
                (170, 220, 255), alpha=a)
        L.ell(x - 3, y + 4, 3, 5, WHITE, alpha=a * 0.8)


def _ears(L, P, y=8, rx=17, ry=27, x=98):
    for s in (-1, 1):
        L.ell(s * x, y, rx, ry, P['skin'])
        L.ell(s * (x + 1), y + 2, rx * 0.47, ry * 0.55, P['sh'])


def _face(L, P, pts, sh_pts=None, blush=0.32, freckles=False):
    fm = L.shape(pts, P['skin'])
    sh_pts = sh_pts or [(58, -130), (110, -90), (108, 10), (90, 70), (50, 116), (20, 130), (60, 80), (80, 20),
                        (82, -50)]
    L.shape(sh_pts, P['sh'], clip=fm, alpha=0.72)
    for s in (-1, 1):
        L.ell(s * 60, 42, 20, 12, BLUSH, alpha=blush, blur=6)
    if freckles:
        for s in (-1, 1):
            for fx, fy in ((48, 30), (62, 24), (56, 38), (72, 34)):
                L.ell(s * fx, fy, 2.6, 2.6, P['sh'], alpha=0.9)
    return fm


def _nose(L, P, y=20):
    L.stroke([(-2, y), (5, y + 16), (-5, y + 21)], 4.2, P['sh'])


# ================================================================== heads
@functools.lru_cache(maxsize=512)
def _petya_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, glow, hood):
    P = PETYA
    L = Layer(*HEAD_BOX).at(*HC)
    if hood:   # hood up: dark volume behind the head, down to the shoulders
        L.shape([(-170, 200), (-158, 60), (-150, -60), (-114, -166), (0, -200), (114, -166), (150, -60),
                 (158, 60), (170, 200), (0, 230)], P['cloth'])
    _ears(L, P, x=94)
    face = [(0, -126), (64, -118), (94, -76), (97, -20), (90, 34), (68, 82), (34, 112), (0, 120),
            (-34, 112), (-68, 82), (-90, 34), (-97, -20), (-94, -76), (-64, -118)]
    fm = _face(L, P, face, freckles=True)
    if glow > 0:   # phone light from below
        L.ell(0, 130, 150, 90, (200, 230, 255), clip=fm, alpha=0.2 * glow, blur=30)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=38, brow_col=P['hair'], brow_w=9,
          brow_lift_r=max(0.0, smirk))
    _nose(L, P)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=64, w=26)
    # hair: back volume, then a messy fringe that falls over the forehead
    L.shape([(-100, -10), (-114, -84), (-86, -142), (-24, -170), (44, -166), (98, -134), (116, -78),
             (104, -6), (94, -60), (54, -96), (-56, -96), (-94, -60)], P['hair'])
    fr = L.shape([(-100, -30), (-98, -98), (-58, -140), (6, -156), (72, -138), (108, -96), (102, -36),
                  (86, -62), (74, -48), (60, -80), (34, -60), (20, -84), (-6, -56), (-24, -84), (-50, -60),
                  (-64, -86), (-84, -52)], P['hair'])
    L.stroke([(-48, -126), (0, -142), (50, -128)], 9, P['hi'], clip=fr, alpha=0.55)
    # three spikes on the crown
    for x0, x1, y1 in (() if hood else ((-30, -50, -186), (8, 10, -194), (44, 70, -180))):
        L.shape([(x0 - 22, -150), (x1, y1), (x0 + 22, -152), (x0, -140)], P['hair'])
    for s_ in (-1, 1):
        L.shape([(s_ * 100, -40), (s_ * 98, 2), (s_ * 90, 8), (s_ * 88, -34)], P['hair'])
    if hood:   # front rim of the hood over the hair and the cheeks
        rim = [(-150, 190), (-138, 60), (-134, -70), (-100, -156), (0, -190), (100, -156), (134, -70),
               (138, 60), (150, 190), (110, 150), (108, 60), (112, -60), (84, -130), (0, -152), (-84, -130),
               (-112, -60), (-108, 60), (-110, 150)]
        L.shape(rim, shade(P['cloth'], 0.9))
        L.shape([(100, -156), (134, -70), (138, 60), (150, 190), (110, 150), (108, 60), (112, -60)],
                P['cloth_sh'])
    _sweat(L, sweat)
    return L.image()


@functools.lru_cache(maxsize=512)
def _katya_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, glow, hood):
    P = KATYA
    L = Layer(*HEAD_BOX).at(*HC)
    L.shape([(-112, -110), (-132, 0), (-140, 140), (-128, 300), (-60, 330), (60, 330), (128, 300), (140, 140),
             (132, 0), (112, -110), (0, -150)], P['hair_sh'])
    nk = L.poly([(-26, 90), (26, 90), (30, 340), (-30, 340)], P['skin'])
    L.ell(0, 120, 50, 40, P['sh'], clip=nk, alpha=0.9, blur=4)
    _ears(L, P, x=92, rx=15, ry=24)
    face = [(0, -128), (62, -120), (92, -78), (95, -20), (86, 34), (62, 82), (28, 114), (0, 122),
            (-28, 114), (-62, 82), (-86, 34), (-95, -20), (-92, -78), (-62, -120)]
    fm = _face(L, P, face, blush=0.4)
    if glow > 0:
        L.ell(0, 130, 150, 90, (200, 230, 255), clip=fm, alpha=0.18 * glow, blur=30)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=38, r=(11.5, 15), brow_col=P['hair_sh'], brow_w=6.5,
          lashes=True)
    _nose(L, P, y=24)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=66, w=19, lips=True)
    # pearl earrings, under the hair line
    for s in (-1, 1):
        L.ell(s * 92, 46, 8, 8, (250, 246, 240))
        L.ell(s * 92 - 2, 43, 3, 3, WHITE)
    # hair: centre part, two soft waves framing the face and falling past the jaw
    for s in (-1, 1):
        side = [(0, -150), (s * 70, -142), (s * 112, -90), (s * 122, -10), (s * 116, 80), (s * 128, 170),
                (s * 112, 250), (s * 86, 290), (s * 92, 210), (s * 82, 130), (s * 94, 40), (s * 92, -40),
                (s * 72, -96), (s * 30, -118), (s * 4, -124)]
        sm = L.shape(side, P['hair'])
        L.stroke([(s * 40, -136), (s * 96, -96), (s * 108, -10)], 10, P['hi'], clip=sm, alpha=0.7)
        L.stroke([(s * 108, 60), (s * 118, 150), (s * 100, 240)], 8, P['hair_sh'], clip=sm, alpha=0.55)
    L.stroke([(0, -150), (0, -122)], 3, P['hair_sh'], alpha=0.8)   # parting
    _sweat(L, sweat, x=-100)
    return L.image()


@functools.lru_cache(maxsize=256)
def _alex_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, glow, hood):
    P = ALEX
    L = Layer(*HEAD_BOX).at(*HC)
    _ears(L, P, x=100)
    face = [(0, -130), (70, -122), (100, -80), (104, -20), (100, 40), (88, 86), (50, 116), (0, 124),
            (-50, 116), (-88, 86), (-100, 40), (-104, -20), (-100, -80), (-70, -122)]
    fm = _face(L, P, face, blush=0.16)
    # stubble along the jaw and upper lip
    L.shape([(-100, 30), (-88, 86), (-50, 116), (0, 126), (50, 116), (88, 86), (100, 30), (72, 60), (40, 80),
             (0, 84), (-40, 80), (-72, 60)], (120, 104, 100), clip=fm, alpha=0.09, blur=2)
    L.shape([(-30, 48), (0, 42), (30, 48), (24, 54), (-24, 54)], (120, 104, 100), clip=fm, alpha=0.2, blur=2)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=40, r=(10, 12.5), brow_col=P['hair'], brow_w=11,
          y=2)
    _nose(L, P, y=22)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=68, w=24)
    # neat hair: short sides, volume swept up and to the right
    L.shape([(-104, -20), (-110, -90), (-80, -140), (-20, -162), (50, -160), (100, -130), (112, -80),
             (106, -20), (96, -70), (60, -104), (-60, -104), (-96, -70)], P['hair'])
    tm = L.shape([(-98, -84), (-80, -150), (-20, -182), (60, -180), (112, -146), (120, -100), (96, -96),
                  (60, -118), (0, -120), (-60, -108)], P['hair'])
    L.stroke([(-50, -160), (20, -172), (90, -150)], 10, P['hi'], clip=tm, alpha=0.6)
    L.stroke([(-30, -110), (-40, -150)], 4, P['hi'], alpha=0.5)       # side parting
    return L.image()


@functools.lru_cache(maxsize=256)
def _dima_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, glow, hood):
    P = DIMA
    L = Layer(*HEAD_BOX).at(*HC)
    _ears(L, P, x=100, rx=19, ry=28)
    face = [(0, -122), (70, -114), (102, -70), (106, -10), (100, 44), (76, 90), (38, 116), (0, 122),
            (-38, 116), (-76, 90), (-100, 44), (-106, -10), (-102, -70), (-70, -114)]
    _face(L, P, face, blush=0.45)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=42, r=(12, 15), brow_col=P['hair'], brow_w=7, y=6)
    # round glasses
    for s in (-1, 1):
        L.ell(s * 42, 6, 31, 29, (220, 236, 255), alpha=0.18)
        ring = ellipse_pts(s * 42, 6, 32, 30, n=72)
        L.stroke(ring + ring[:2], 5, P['frame'], smooth=False)
        L.stroke([(s * 42 - 18, -6), (s * 42 - 8, -14)], 4, WHITE, alpha=0.55)
        L.stroke([(s * 74, 2), (s * 102, -4)], 4.5, P['frame'])
    L.stroke([(-10, 2), (0, -3), (10, 2)], 4.5, P['frame'])
    _nose(L, P, y=28)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=70, w=18)
    # bowl cut with a straight fringe
    hm = L.shape([(-112, 10), (-120, -70), (-90, -132), (-30, -156), (40, -156), (96, -130), (122, -70),
                  (114, 10), (104, -40), (100, -46), (-100, -46), (-104, -40)], P['hair'])
    L.stroke([(-60, -132), (0, -146), (60, -132)], 10, P['hi'], clip=hm, alpha=0.6)
    for k in range(-3, 4):
        L.stroke([(k * 26, -48), (k * 26 + 4, -60)], 3, shade(P['hair'], 0.8), alpha=0.6)
    if sweat > 0.05:   # for Dima `sweat` means tears running down from under the glasses
        for sx_ in (-1, 1):
            L.stroke([(sx_ * 52, 34), (sx_ * 56, 70), (sx_ * 54, 104)], 9, (150, 205, 250), alpha=0.85 * sweat)
            L.ell(sx_ * 54, 108, 7, 9, (150, 205, 250), alpha=0.85 * sweat)
    return L.image()


@functools.lru_cache(maxsize=128)
def _sery_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, glow, hood):
    P = SERY
    L = Layer(*HEAD_BOX).at(*HC)
    _ears(L, P, x=98)
    face = [(0, -124), (66, -116), (98, -74), (100, -16), (94, 38), (72, 86), (36, 114), (0, 122),
            (-36, 114), (-72, 86), (-94, 38), (-100, -16), (-98, -74), (-66, -116)]
    _face(L, P, face, blush=0.3)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=40, brow_col=P['hair'], brow_w=10)
    _nose(L, P)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=64)
    L.shape([(-100, -20), (-104, -70), (-80, -86), (80, -86), (104, -70), (100, -20), (92, -60), (-92, -60)],
            P['hair'])
    # cap turned backwards: dome + strap band + visor sticking out behind on the left
    cm = L.shape([(-112, -60), (-104, -126), (-50, -168), (30, -170), (96, -136), (114, -64), (0, -80)], P['cap'])
    L.shape([(30, -170), (96, -136), (114, -64), (70, -70), (60, -130)], P['cap_sh'], clip=cm, alpha=0.8)
    L.shape([(-104, -96), (-176, -104), (-190, -84), (-110, -66)], P['cap_sh'])
    L.ell(-6, -170, 10, 6, P['cap_sh'])
    return L.image()


@functools.lru_cache(maxsize=128)
def _vanya_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, glow, hood):
    P = VANYA
    L = Layer(*HEAD_BOX).at(*HC)
    _ears(L, P, x=96)
    face = [(0, -122), (66, -114), (96, -72), (98, -16), (92, 38), (70, 86), (34, 114), (0, 122),
            (-34, 114), (-70, 86), (-92, 38), (-98, -16), (-96, -72), (-66, -114)]
    _face(L, P, face, blush=0.4, freckles=True)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=40, brow_col=P['hair'], brow_w=8)
    _nose(L, P)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=64)
    # curly ginger hair: a ring of round curls
    L.shape([(-104, -10), (-112, -80), (-80, -130), (0, -150), (80, -130), (112, -80), (104, -10), (90, -70),
             (-90, -70)], P['hair'])
    for k in range(11):
        a = math.pi * (1.02 + k * 0.096)
        cx, cy = 104 * math.cos(a), -60 + 92 * math.sin(a)
        L.ell(cx, cy, 30, 28, P['hair'])
        L.ell(cx - 6, cy - 8, 10, 8, P['hi'], alpha=0.6)
    return L.image()


_HEADS = dict(petya=_petya_head, katya=_katya_head, alex=_alex_head, dima=_dima_head, sery=_sery_head,
              vanya=_vanya_head)


def head(who, look=(0, 0), blink=0.0, brow=0.0, sad=0.0, anger=0.0, smile=0.3, open_=0.0, smirk=0.0,
         teeth=0.0, shock=0.0, sweat=0.0, glow=0.0, hood=False):
    return _HEADS[who]((_q(look[0], 0.1), _q(look[1], 0.1)), _q(blink, 0.125), _q(brow, 0.1), _q(sad, 0.1),
                       _q(anger, 0.1), _q(smile, 0.1), _q(open_, 0.1), _q(smirk, 0.1), _q(teeth, 0.25),
                       _q(shock, 0.1), _q(sweat, 0.25), _q(glow, 0.25), bool(hood))


# ================================================================== bodies
def _neck(L, P, w=34):
    nm = L.poly([(-w, -40), (w, -40), (w + 6, 70), (-w - 6, 70)], P['skin'])
    L.ell(0, -30, w * 1.8, 34, P['sh'], clip=nm, alpha=0.9, blur=4)


def _torso(L, col, sh, sx=1.0, top=40):
    tm = L.shape([(-60 * sx, top), (-170 * sx, 70), (-250 * sx, 140), (-280 * sx, 300), (-290 * sx, 700),
                  (290 * sx, 700), (280 * sx, 300), (250 * sx, 140), (170 * sx, 70), (60 * sx, top)], col)
    L.shape([(120 * sx, 60), (280 * sx, 160), (300 * sx, 700), (180 * sx, 700), (190 * sx, 300)], sh, clip=tm,
            alpha=0.8)
    return tm


def _phone_hands(L, P, sleeve, glow, sx=1.0):
    """A real-size phone (≈ half a face wide, tilted towards the eyes) held in two hands."""
    for s in (-1, 1):
        L.shape([(s * 250 * sx, 700), (s * 260 * sx, 540), (s * 150, 455), (s * 96, 436), (s * 72, 486),
                 (s * 140, 572), (s * 170 * sx, 700)], sleeve)
    L.poly([(-46, 318), (46, 318), (50, 452), (-50, 452)], (28, 30, 40))
    L.poly([(-40, 325), (40, 325), (44, 445), (-44, 445)], mixc((40, 70, 110), (150, 210, 255), glow))
    for s in (-1, 1):
        L.shape([(s * 100, 478), (s * 106, 412), (s * 80, 368), (s * 50, 370), (s * 38, 398), (s * 40, 442),
                 (s * 58, 480)], P['skin'])
        L.stroke([(s * 60, 430), (s * 40, 396), (s * 26, 386)], 13, P['skin'])          # thumb on the screen
        L.stroke([(s * 84, 400), (s * 70, 420)], 4, P['sh'], alpha=0.7)


@functools.lru_cache(maxsize=32)
def petya_body(arms='down', glow=0.0):
    P = PETYA
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P, w=30)
    _torso(L, P['cloth'], P['cloth_sh'], sx=0.9)
    hm = L.shape([(-92, 20), (-116, 70), (-68, 116), (0, 128), (68, 116), (116, 70), (92, 20), (58, 50),
                  (0, 62), (-58, 50)], shade(P['cloth'], 0.9))
    L.shape([(40, 40), (116, 60), (106, 108), (40, 122)], P['cloth_sh'], clip=hm, alpha=0.7)
    for s in (-1, 1):
        L.stroke([(s * 22, 106), (s * 26, 180), (s * 22, 240)], 7, P['accent'])
        L.ell(s * 22, 244, 7, 9, P['accent'])
    L.ell(-130, 250, 22, 22, P['accent'], alpha=0.95)          # small round patch on the chest
    L.ell(-130, 250, 10, 10, P['cloth'])
    L.stroke([(-140, 520), (-100, 440), (100, 440), (140, 520)], 6, P['cloth_sh'], alpha=0.8)
    if arms == 'phone':
        _phone_hands(L, P, shade(P['cloth'], 0.93), glow, sx=0.9)
    return L.image()


@functools.lru_cache(maxsize=16)
def katya_body(arms='down', glow=0.0):
    P = KATYA
    L = Layer(*BODY_BOX).at(*BC)
    # long hair behind the shoulders (continues the back hair of the head sprite)
    L.shape([(-128, -60), (-150, 60), (-168, 260), (-120, 380), (0, 400), (120, 380), (168, 260), (150, 60),
             (128, -60), (0, -80)], P['hair_sh'])
    _neck(L, P, w=28)
    # white top with a soft neckline
    _torso(L, P['top'], (226, 218, 210), sx=0.86, top=50)
    L.shape([(-44, 50), (0, 110), (44, 50), (60, 60), (0, 136), (-60, 60)], P['skin'])
    # gold necklace with a small pendant
    L.stroke([(-48, 56), (-20, 96), (0, 104), (20, 96), (48, 56)], 3, P['gold'])
    L.ell(0, 112, 7, 9, P['gold'])
    # camel coat open over the top, with lapels
    for s in (-1, 1):
        cm = L.shape([(s * 70, 60), (s * 160, 70), (s * 236, 140), (s * 262, 300), (s * 270, 700), (s * 70, 700),
                      (s * 90, 300), (s * 110, 190)], P['cloth'])
        if s == 1:
            L.shape([(150, 80), (262, 170), (276, 700), (190, 700), (200, 320)], P['cloth_sh'], clip=cm, alpha=0.8)
        L.shape([(s * 70, 60), (s * 128, 66), (s * 150, 200), (s * 110, 300), (s * 98, 210)],
                shade(P['cloth'], 0.9))
    for k in range(2):
        L.ell(-104, 400 + k * 110, 9, 9, P['cloth_sh'])
    if arms == 'phone':
        _phone_hands(L, P, P['cloth'], glow, sx=0.86)
    return L.image()


@functools.lru_cache(maxsize=16)
def alex_body(arms='down', glow=0.0):
    P = ALEX
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P, w=38)
    _torso(L, P['shirt'], P['shirt_sh'], sx=0.7)
    L.shape([(-34, 50), (0, 120), (34, 50)], P['skin'])            # open collar
    for s in (-1, 1):
        L.poly([(s * 6, 120), (s * 40, 40), (s * 74, 66), (s * 34, 130)], P['shirt'])
        L.stroke([(s * 40, 40), (s * 74, 66), (s * 34, 130)], 3, P['shirt_sh'])
    for s in (-1, 1):
        bm = L.shape([(s * 80, 60), (s * 180, 76), (s * 270, 150), (s * 300, 320), (s * 310, 700),
                      (s * 90, 700), (s * 110, 300), (s * 70, 160)], P['cloth'])
        if s == 1:
            L.shape([(160, 90), (290, 180), (310, 700), (210, 700), (220, 320)], P['cloth_sh'], clip=bm,
                    alpha=0.8)
        L.shape([(s * 80, 60), (s * 140, 74), (s * 170, 210), (s * 118, 330), (s * 104, 220)],
                shade(P['cloth'], 0.85))
    L.stroke([(150, 250), (200, 246)], 4, WHITE, alpha=0.85)      # pocket square
    return L.image()


@functools.lru_cache(maxsize=16)
def dima_body(arms='down', glow=0.0):
    P = DIMA
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P, w=30)
    _torso(L, P['shirt'], P['shirt_sh'], sx=0.84)
    # V-neck vest
    vm = L.poly([(-130, 80), (-56, 70), (0, 250), (56, 70), (130, 80), (196, 190), (214, 700), (-214, 700),
                 (-196, 190)], P['cloth'])
    L.poly([(56, 70), (130, 80), (196, 190), (214, 700), (140, 700), (130, 300)], P['cloth_sh'], clip=vm,
           alpha=0.8)
    for s in (-1, 1):
        L.poly([(s * 4, 76), (s * 50, 46), (s * 66, 76), (s * 24, 104)], P['shirt'])
    L.poly([(-14, 84), (14, 84), (10, 104), (-10, 104)], P['tie'])
    L.poly([(-10, 104), (10, 104), (22, 220), (0, 246), (-22, 220)], P['tie'])
    if arms == 'phone':
        _phone_hands(L, P, P['shirt'], glow, sx=0.84)
    return L.image()


@functools.lru_cache(maxsize=8)
def sery_body(arms='down', glow=0.0):
    P = SERY
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P)
    _torso(L, P['cloth'], P['cloth_sh'])
    L.shape([(-80, 30), (-90, 80), (0, 96), (90, 80), (80, 30), (0, 60)], (40, 44, 48))     # ribbed collar
    L.stroke([(0, 90), (0, 700)], 6, (200, 200, 200), alpha=0.8)                          # zipper
    L.ell(-170, 220, 24, 10, (230, 160, 60))                                               # sleeve patch
    return L.image()


@functools.lru_cache(maxsize=8)
def vanya_body(arms='down', glow=0.0):
    P = VANYA
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P)
    _torso(L, P['cloth'], P['cloth_sh'], sx=0.95)
    L.shape([(-46, 44), (0, 84), (46, 44), (40, 60), (0, 96), (-40, 60)], shade(P['cloth'], 0.85))
    L.ell(0, 330, 60, 60, WHITE, alpha=0.9)                                                # tee print
    L.ell(0, 330, 32, 32, P['cloth'])
    return L.image()


BODIES = dict(petya=petya_body, katya=katya_body, alex=alex_body, dima=dima_body, sery=sery_body,
              vanya=vanya_body)


# ================================================================== avatars (only seen in Telegram)
@functools.lru_cache(maxsize=8)
def avatar(kind, size=240):
    """'boss' — the internet friend (hooded figure, white grin); 'unknown' — the sender of the last message."""
    L = Layer(size, size).at(size / 2, size / 2, size / 240)
    if kind == 'boss':        # «Друг»: a dark silhouette with a question mark
        cm = L.ell(0, 0, 120, 120, (58, 62, 78))
        L.ell(0, -30, 44, 48, (22, 22, 30), clip=cm)
        L.ell(0, 104, 90, 74, (22, 22, 30), clip=cm)
        L.stroke([(-16, -48), (-12, -62), (0, -68), (13, -62), (15, -48), (2, -36), (0, -24)], 9, WHITE)
        L.ell(0, -8, 6, 6, WHITE)
    elif kind == 'unknown':
        cm = L.ell(0, 0, 120, 120, (16, 16, 20))
        L.ell(0, -28, 40, 44, (60, 60, 70), clip=cm)
        L.ell(0, 100, 84, 70, (60, 60, 70), clip=cm)
    return L.image()


# ================================================================== composition helpers
def bust(head_img, body_img, x, y, scale=1.0, tilt=0.0, bob=0.0):
    """Return parts for place(): neck pivot of the body at (x, y)."""
    out = [(body_img, x - BC[0] * scale, y - BC[1] * scale + bob * 0.3, scale, 0.0, None)]
    hx, hy = x, y - 8 * scale + bob
    out.append((head_img, hx - HC[0] * scale, hy - (HC[1] + 120) * scale, scale, tilt, (HC[0], HC[1] + 120)))
    return out


def place(canvas, parts):
    for spr, x, y, s, tilt, pivot in parts:
        im = spr
        if s != 1.0:
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
        if tilt:
            im = im.rotate(tilt, resample=Image.BICUBIC, center=(pivot[0] * s, pivot[1] * s))
        if canvas.mode == 'RGBA':
            canvas.alpha_composite(im, (int(round(x)), int(round(y))))
        else:
            canvas.paste(im, (int(round(x)), int(round(y))), im)
