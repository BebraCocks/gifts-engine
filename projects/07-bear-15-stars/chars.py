"""Characters of «Мишка за 15 звёзд», drawn in code: flat 2D without outlines (cel shadow + blush).

Герой «Вы» — 20, ginger cowlick, big eyes, green hoodie. Variants: tired (eye bags), beanie (old clothes),
beard (months on the sofa). Друзья: Кепка (red cap) and Очкарик (round glasses).
Мишка — the plain brown teddy (Telegram gift for 15 ⭐), own drawing: the gift is not in api.changes.tg.

Units: head centre at (0, 0), head half-width ≈ 100. Heads and bodies are separate cached sprites,
so the renderer can tilt/bob the head around the neck pivot (bust()).
"""
import functools
import math

from PIL import Image

from art import Layer, mixc, shade

EYE = (40, 32, 38)
WHITE = (255, 255, 255)
BLUSH = (240, 140, 140)

HEAD_BOX = (560, 680)
HC = (280, 330)
BODY_BOX = (760, 760)
BC = (380, 120)


def _q(v, step):
    return round(v / step) * step


HERO = dict(skin=(250, 220, 198), sh=(232, 184, 162), hair=(198, 98, 46), hi=(236, 140, 74), lip=(192, 104, 98),
            cloth=(64, 160, 110), cloth_sh=(44, 124, 84), accent=(255, 214, 92),
            old=(132, 128, 126), old_sh=(102, 98, 98), patch1=(170, 120, 80), patch2=(90, 110, 150),
            beanie=(70, 74, 92), beanie_sh=(52, 54, 70))
CAP = dict(skin=(246, 212, 188), sh=(226, 178, 154), hair=(54, 40, 34), hi=(90, 70, 60), lip=(184, 100, 96),
           cloth=(52, 92, 170), cloth_sh=(38, 68, 132), cap=(226, 60, 56), cap_sh=(180, 40, 42))
GLASS = dict(skin=(252, 228, 212), sh=(236, 192, 172), hair=(232, 196, 120), hi=(250, 222, 160),
             lip=(196, 106, 104), cloth=(246, 180, 52), cloth_sh=(214, 146, 32), frame=(50, 48, 60))


# ================================================================== face parts
def _eyes(L, look, blink, brow, sad, anger, shock, *, spacing=40, y=0, r=(11.5, 15.0), brow_col, brow_w=8.5):
    lx, ly = look
    for s in (-1, 1):
        cx, cy = s * spacing + lx * 5, y + ly * 4
        ry = r[1] * max(0.08, 1 - blink)
        if shock > 0.05 and blink < 0.5:
            L.ell(cx - lx * 3, cy, r[0] * (1 + 0.55 * shock), ry * (1 + 0.45 * shock), WHITE)
            L.ell(cx, cy, r[0] * (1 - 0.45 * shock), ry * (1 - 0.45 * shock), EYE)
        else:
            L.ell(cx, cy, r[0], ry, EYE)
            if blink < 0.5:
                L.ell(cx + 4, cy - 5.5 * (1 - blink), 4.0, 4.0 * (1 - blink), WHITE)
        if blink > 0.6:
            L.stroke([(cx - 12, cy), (cx, cy + 3), (cx + 12, cy)], 3.6, EYE)
        lift = brow * 7 + shock * 9
        inner = (s * 18, y - 32 - lift - sad * 7 + anger * 9)
        mid = (s * 40, y - 38 - lift + sad * 2 - anger * 1)
        outer = (s * 58, y - 32 - lift * 0.8 + sad * 6 - anger * 3)
        L.stroke([inner, mid, outer], brow_w, brow_col)


def _mouth(L, smile, open_, smirk=0.0, teeth=0.0, *, y=62, w=24, col):
    dx = smirk * 5
    if open_ > 0.08:
        h = 6 + 28 * open_
        top = y - 2 - smile * 3
        pts = [(-w * 0.8 + dx, top + smirk * 4), (dx, top - 2 + smile * 2), (w * 0.8 + dx, top - smirk * 6),
               (w * 0.55 + dx, top + h * 0.8), (dx, top + h + smile * 3), (-w * 0.55 + dx, top + h * 0.8)]
        m = L.shape(pts, (118, 48, 58))
        if teeth > 0:
            L.poly([(-w + dx, top - 10), (w + dx, top - 10), (w + dx, top + h * 0.34 * teeth + 1),
                    (-w + dx, top + h * 0.34 * teeth + 1)], WHITE, clip=m)
        L.ell(dx, top + h * 0.88, w * 0.42, h * 0.36, (212, 108, 116), clip=m)
    else:
        c = smile * 10
        pts = [(-w + dx, y - c * 0.6 + smirk * 3), (-w * 0.45 + dx, y + c * 0.35 + smirk * 1),
               (dx, y + c * 0.55), (w * 0.45 + dx, y + c * 0.35 - smirk * 4),
               (w + dx + smirk * 3, y - c * 0.6 - smirk * 11)]
        L.stroke(pts, 5.6, col)


def _sweat(L, sweat, x=96, y=-56):
    if sweat > 0.05:
        a = min(1.0, sweat)
        L.shape([(x, y - 22), (x + 11, y), (x + 9, y + 12), (x, y + 16), (x - 9, y + 12), (x - 11, y)],
                (170, 220, 255), alpha=a)
        L.ell(x - 3, y + 4, 3, 5, WHITE, alpha=a * 0.8)


def _ears(L, P, y=8, rx=17, ry=27, x=96):
    for s in (-1, 1):
        L.ell(s * x, y, rx, ry, P['skin'])
        L.ell(s * (x + 1), y + 2, rx * 0.47, ry * 0.55, P['sh'])


FACE = [(0, -126), (64, -118), (94, -76), (97, -20), (90, 34), (68, 82), (34, 112), (0, 120),
        (-34, 112), (-68, 82), (-90, 34), (-97, -20), (-94, -76), (-64, -118)]


def _face(L, P, pts=FACE, blush=0.34):
    fm = L.shape(pts, P['skin'])
    L.shape([(58, -130), (110, -90), (108, 10), (90, 70), (50, 116), (20, 130), (60, 80), (80, 20), (82, -50)],
            P['sh'], clip=fm, alpha=0.72)
    for s in (-1, 1):
        L.ell(s * 60, 44, 20, 12, BLUSH, alpha=blush, blur=6)
    return fm


def _nose(L, P, y=20):
    L.stroke([(-2, y), (5, y + 16), (-5, y + 21)], 4.2, P['sh'])


# ================================================================== heads
@functools.lru_cache(maxsize=512)
def _hero_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, tired, beanie, beard,
               web):
    P = HERO
    L = Layer(*HEAD_BOX).at(*HC)
    # back hair volume (ginger), tufts behind the ears
    L.shape([(-104, -6), (-118, -86), (-88, -146), (-20, -172), (50, -166), (104, -132), (120, -80),
             (106, -4), (96, -60), (54, -96), (-56, -96), (-96, -60)], P['hair'])
    _ears(L, P)
    fm = _face(L, P)
    if tired > 0:
        for s in (-1, 1):
            L.ell(s * 40 + look[0] * 5, 22, 20, 8, (186, 150, 170), alpha=0.75 * tired, clip=fm)
    _eyes(L, look, max(blink, 0.35 * tired), brow, sad + 0.3 * tired, anger, shock, spacing=40,
          brow_col=shade(P['hair'], 0.8), brow_w=9)
    _nose(L, P)
    if beard > 0:
        bm = L.shape([(-96, -4), (-92, 60), (-64, 126), (-20, 160 + 60 * beard), (20, 160 + 60 * beard),
                      (64, 126), (92, 60), (96, -4), (70, 40), (36, 52), (0, 44), (-36, 52), (-70, 40)],
                     mixc(P['skin'], P['hair'], 0.35 + 0.65 * min(1.0, beard * 2)))
        L.stroke([(-40, 100), (-20, 140), (0, 150)], 4, shade(P['hair'], 0.8), clip=bm, alpha=0.5)
        L.stroke([(40, 100), (20, 140)], 4, shade(P['hair'], 0.8), clip=bm, alpha=0.5)
        L.stroke([(-26, 64), (0, 70), (26, 64)], 5.6, (150, 70, 70))
    else:
        _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=66, w=26)
    if beanie:
        bm = L.shape([(-112, -40), (-110, -110), (-70, -164), (0, -182), (70, -164), (110, -110), (112, -40),
                      (60, -56), (0, -60), (-60, -56)], P['beanie'])
        L.shape([(40, -160), (110, -110), (112, -40), (64, -54)], P['beanie_sh'], clip=bm, alpha=0.8)
        L.shape([(-118, -54), (-116, -82), (0, -96), (116, -82), (118, -54), (0, -66)], shade(P['beanie'], 0.85))
        for k in range(-3, 4):
            L.stroke([(k * 30, -150), (k * 32, -92)], 4, P['beanie_sh'], alpha=0.6)
        L.ell(0, -186, 26, 22, (196, 196, 204))
        L.ell(36, -100, 10, 6, (220, 120, 100))       # a darned hole
    else:
        fr = L.shape([(-102, -30), (-100, -100), (-60, -142), (6, -158), (74, -140), (110, -98), (104, -36),
                      (88, -60), (70, -44), (58, -82), (30, -58), (16, -86), (-10, -58), (-28, -86), (-52, -60),
                      (-66, -88), (-86, -52)], P['hair'])
        L.stroke([(-50, -128), (0, -144), (52, -130)], 9, P['hi'], clip=fr, alpha=0.6)
        # the cowlick
        L.shape([(-6, -150), (-30, -206), (10, -232), (40, -214), (18, -200), (16, -156)], P['hair'])
        L.stroke([(-14, -196), (8, -220)], 6, P['hi'], alpha=0.6)
    if web > 0:
        cx, cy = -70, -150
        for a in range(5):
            ang = math.radians(150 + a * 25)
            L.stroke([(cx, cy), (cx + 150 * math.cos(ang) * -1, cy + 150 * math.sin(ang) * -1)], 2.2, WHITE,
                     alpha=0.75 * web)
        for r in (40, 80, 120):
            pts = [(cx - r * math.cos(math.radians(150 + a * 25)), cy - r * math.sin(math.radians(150 + a * 25)))
                   for a in range(5)]
            L.stroke(pts, 2.0, WHITE, alpha=0.65 * web, smooth=False)
    _sweat(L, sweat)
    return L.image()


@functools.lru_cache(maxsize=256)
def _cap_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, *_):
    P = CAP
    L = Layer(*HEAD_BOX).at(*HC)
    _ears(L, P)
    _face(L, P)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=38, brow_col=P['hair'], brow_w=10)
    _nose(L, P)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=64, w=26)
    L.shape([(-98, -30), (-96, -70), (96, -70), (98, -30), (60, -54), (0, -60), (-60, -54)], P['hair'])
    cm = L.shape([(-104, -56), (-100, -120), (-56, -160), (0, -170), (56, -160), (100, -120), (104, -56)], P['cap'])
    L.shape([(30, -162), (100, -120), (104, -56), (60, -60)], P['cap_sh'], clip=cm, alpha=0.8)
    L.shape([(-110, -62), (-60, -66), (60, -66), (150, -62), (156, -44), (60, -44), (-110, -46)], P['cap_sh'])
    L.ell(0, -168, 10, 6, P['cap_sh'])
    return L.image()


@functools.lru_cache(maxsize=256)
def _glass_head(look, blink, brow, sad, anger, smile, open_, smirk, teeth, shock, sweat, *_):
    P = GLASS
    L = Layer(*HEAD_BOX).at(*HC)
    L.shape([(-108, 40), (-120, -80), (-80, -150), (0, -170), (80, -150), (120, -80), (108, 40), (90, -50),
             (-90, -50)], P['hair'])
    _ears(L, P)
    _face(L, P)
    _eyes(L, look, blink, brow, sad, anger, shock, spacing=40, brow_col=shade(P['hair'], 0.7), brow_w=8)
    for s in (-1, 1):
        L.stroke([(s * 40 + 30 * math.cos(a), 30 * math.sin(a)) for a in [k * math.pi / 10 for k in range(21)]],
                 5, P['frame'], smooth=False)
    L.stroke([(-10, -4), (10, -4)], 5, P['frame'])
    _nose(L, P)
    _mouth(L, smile, open_, smirk, teeth, col=P['lip'], y=66, w=24)
    fr = L.shape([(-104, -40), (-100, -110), (-50, -150), (20, -156), (90, -130), (108, -60), (60, -96),
                  (0, -92), (-50, -80)], P['hair'])
    L.stroke([(-40, -130), (20, -142)], 8, P['hi'], clip=fr, alpha=0.6)
    return L.image()


_HEADS = dict(hero=_hero_head, cap=_cap_head, glass=_glass_head)


def head(who, look=(0, 0), blink=0.0, brow=0.0, sad=0.0, anger=0.0, smile=0.3, open_=0.0, smirk=0.0,
         teeth=0.0, shock=0.0, sweat=0.0, tired=0.0, beanie=False, beard=0.0, web=0.0):
    return _HEADS[who]((_q(look[0], 0.1), _q(look[1], 0.1)), _q(blink, 0.125), _q(brow, 0.1), _q(sad, 0.1),
                       _q(anger, 0.1), _q(smile, 0.1), _q(open_, 0.1), _q(smirk, 0.1), _q(teeth, 0.25),
                       _q(shock, 0.1), _q(sweat, 0.25), _q(tired, 0.25), bool(beanie), _q(beard, 0.125),
                       _q(web, 0.25))


# ================================================================== bodies
def _neck(L, P, w=32):
    nm = L.poly([(-w, -40), (w, -40), (w + 6, 70), (-w - 6, 70)], P['skin'])
    L.ell(0, -30, w * 1.8, 34, P['sh'], clip=nm, alpha=0.9, blur=4)


def _torso(L, col, sh, sx=1.0, top=40):
    tm = L.shape([(-60 * sx, top), (-170 * sx, 70), (-250 * sx, 140), (-280 * sx, 300), (-290 * sx, 700),
                  (290 * sx, 700), (280 * sx, 300), (250 * sx, 140), (170 * sx, 70), (60 * sx, top)], col)
    L.shape([(120 * sx, 60), (280 * sx, 160), (300 * sx, 700), (180 * sx, 700), (190 * sx, 300)], sh, clip=tm,
            alpha=0.8)
    return tm


def _phone_hands(L, P, sleeve, glow, sx=1.0):
    for s in (-1, 1):
        L.shape([(s * 250 * sx, 700), (s * 260 * sx, 540), (s * 150, 455), (s * 96, 436), (s * 72, 486),
                 (s * 140, 572), (s * 170 * sx, 700)], sleeve)
    L.poly([(-46, 318), (46, 318), (50, 452), (-50, 452)], (28, 30, 40))
    L.poly([(-40, 325), (40, 325), (44, 445), (-44, 445)], mixc((40, 70, 110), (150, 210, 255), glow))
    for s in (-1, 1):
        L.shape([(s * 100, 478), (s * 106, 412), (s * 80, 368), (s * 50, 370), (s * 38, 398), (s * 40, 442),
                 (s * 58, 480)], P['skin'])
        L.stroke([(s * 60, 430), (s * 40, 396), (s * 26, 386)], 13, P['skin'])
        L.stroke([(s * 84, 400), (s * 70, 420)], 4, P['sh'], alpha=0.7)


def _hood_collar(L, col, sh):
    hm = L.shape([(-96, 20), (-120, 70), (-70, 118), (0, 130), (70, 118), (120, 70), (96, 20), (58, 50),
                  (0, 62), (-58, 50)], shade(col, 0.9))
    L.shape([(40, 40), (120, 60), (110, 108), (40, 124)], sh, clip=hm, alpha=0.7)


@functools.lru_cache(maxsize=32)
def hero_body(kind='hoodie', arms='down', glow=0.0):
    """kind: hoodie | old.  arms: down | phone | hide (both hands up holding the sign at the face)."""
    P = HERO
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P, w=30)
    col, sh = (P['cloth'], P['cloth_sh']) if kind == 'hoodie' else (P['old'], P['old_sh'])
    tm = _torso(L, col, sh, sx=0.9)
    _hood_collar(L, col, sh)
    if kind == 'hoodie':
        for s in (-1, 1):
            L.stroke([(s * 22, 106), (s * 26, 180), (s * 22, 240)], 7, P['accent'])
            L.ell(s * 22, 244, 7, 9, P['accent'])
        L.shape([(-90, 470), (90, 470), (110, 600), (-110, 600)], sh, alpha=0.7)       # front pocket
    else:
        L.shape([(-200, 300), (-120, 290), (-110, 380), (-196, 392)], P['patch1'], clip=tm)
        L.shape([(120, 420), (210, 410), (220, 500), (126, 510)], P['patch2'], clip=tm)
        for (x0, y0), (x1, y1) in (((-200, 300), (-110, 380)), ((120, 420), (220, 500))):
            for k in range(5):
                xa = x0 + (x1 - x0) * k / 4
                L.stroke([(xa, y0 - 8), (xa + 4, y0 + 8)], 3, (60, 56, 56), alpha=0.8)
        L.shape([(30, 620), (80, 560), (110, 640), (70, 700), (40, 700)], (60, 58, 60), clip=tm)   # a hole
        L.stroke([(-60, 200), (-20, 260), (-50, 320)], 4, sh, alpha=0.6)
    if arms == 'phone':
        _phone_hands(L, P, shade(col, 0.93), glow, sx=0.9)
    return L.image()


@functools.lru_cache(maxsize=8)
def friend_body(who):
    P = CAP if who == 'cap' else GLASS
    L = Layer(*BODY_BOX).at(*BC)
    _neck(L, P)
    _torso(L, P['cloth'], P['cloth_sh'], sx=0.95)
    if who == 'cap':
        L.shape([(-80, 30), (-90, 80), (0, 96), (90, 80), (80, 30), (0, 60)], (40, 44, 48))
        L.stroke([(0, 90), (0, 700)], 6, (210, 210, 214), alpha=0.8)
    else:
        L.shape([(-46, 44), (0, 84), (46, 44), (40, 60), (0, 96), (-40, 60)], shade(P['cloth'], 0.85))
        L.ell(0, 330, 60, 60, WHITE, alpha=0.9)
        L.ell(0, 330, 30, 30, (230, 80, 80))
    return L.image()


def body(who, **kw):
    return hero_body(**kw) if who == 'hero' else friend_body(who)


# ================================================================== the bear (15 ⭐)
# Matched to the author's reference (input/references/07-bear-15-stars/bear_15_stars_author.jpg, 2026-11-05):
# caramel plush, dashed seams on the head and belly, light belly oval, arms out to the sides, big round feet
# turned to the viewer with dark paw prints.
BEAR = dict(fur=(204, 146, 70), sh=(160, 102, 44), deep=(126, 78, 34), hi=(232, 182, 106), belly=(226, 182, 116),
            snout=(234, 202, 150), sole=(150, 110, 70), paw=(46, 34, 30), nose=(30, 22, 22), inner=(222, 172, 110))


def _seam(L, pts, col, alpha=0.75, dash=0.5, w=3.4):
    """Dashed stitch along a polyline."""
    import numpy as _np
    q = [_np.array(p, float) for p in pts]
    seg = []
    for p0, p1 in zip(q, q[1:]):
        n = max(1, int(_np.linalg.norm(p1 - p0) / 7))
        seg += [p0 + (p1 - p0) * k / n for k in range(n)]
    for k in range(0, len(seg) - 1, 2):
        L.stroke([tuple(seg[k]), tuple(seg[k + 1])], w, col, alpha=alpha, smooth=False)


@functools.lru_cache(maxsize=256)
def bear(wave=0.0, blink=0.0, smile=0.6, size=600):
    """Sitting teddy, 600×600 box, feet at the bottom (y≈585). wave: right paw raised 0..1."""
    P = BEAR
    k = size / 600
    L = Layer(size, size).at(300 * k, 316 * k, k)
    # left arm (viewer's left) out and down
    L.shape([(-96, 10), (-170, 60), (-222, 128), (-226, 172), (-186, 186), (-136, 134), (-96, 92)], P['fur'])
    L.ell(-200, 160, 26, 22, P['sh'], alpha=0.45, blur=4)
    # body
    bm = L.shape([(-120, 0), (-150, 90), (-144, 190), (-90, 240), (0, 252), (90, 240), (144, 190), (150, 90),
                  (120, 0), (0, -20)], P['fur'])
    L.ell(110, 150, 90, 130, P['sh'], clip=bm, alpha=0.45, blur=14)
    L.ell(-50, 40, 50, 70, P['hi'], clip=bm, alpha=0.35, blur=8)
    L.ell(0, 128, 74, 92, P['belly'])
    L.ell(-14, 100, 40, 50, (240, 206, 146), alpha=0.5, blur=8)
    _seam(L, [(0, 40), (2, 110), (0, 218)], P['deep'])
    # right arm: resting out to the side -> waving above the shoulder
    th = 0.6 + 2.2 * wave
    sx, sy = 110, 30
    ex, ey = sx + 130 * math.sin(th), sy + 130 * math.cos(th)
    L.stroke([(sx, sy), ((sx + ex) / 2 + 8 * (1 - wave), (sy + ey) / 2), (ex, ey)], 76, P['fur'])
    L.ell(ex, ey, 38, 36, P['fur'])
    L.ell(ex + 6, ey + 4, 22, 20, P['sh'], alpha=0.5)
    # legs + feet facing the viewer (soles with paw prints)
    for s in (-1, 1):
        L.ell(s * 128, 206, 76, 58, P['fur'], rot=s * 0.45)
        fx_, fy_ = s * 186, 196
        L.ell(fx_, fy_, 62, 68, P['fur'], rot=s * 0.3)
        L.ell(fx_ + s * 4, fy_ + 4, 50, 56, P['sole'], rot=s * 0.3)
        L.ell(fx_ + s * 4, fy_ + 18, 22, 18, P['paw'])
        for dx, dy in ((-28, -6), (-11, -20), (11, -20), (28, -6)):
            L.ell(fx_ + s * 4 + dx, fy_ + dy, 8.5, 10, P['paw'])
    # head (drawn at 0.85 scale around the neck, as on the reference the head is wide but not huge)
    L.at(300 * k, 316 * k - 20 * k * 0.15, 0.85 * k)
    for s in (-1, 1):
        L.ell(s * 110, -196, 46, 44, P['fur'])
        L.ell(s * 110, -192, 26, 24, P['inner'])
    hm = L.shape([(-150, -110), (-140, -180), (-90, -226), (0, -240), (90, -226), (140, -180), (150, -110),
                  (130, -40), (70, -6), (0, 4), (-70, -6), (-130, -40)], P['fur'])
    L.ell(110, -90, 80, 130, P['sh'], clip=hm, alpha=0.4, blur=16)
    L.ell(-50, -190, 64, 26, P['hi'], clip=hm, alpha=0.55, blur=5)
    _seam(L, [(-12, -238), (-4, -200), (0, -150), (0, -104)], P['deep'], alpha=0.65)
    _seam(L, [(-120, -150), (-80, -168), (-40, -172)], P['deep'], alpha=0.5)
    L.ell(0, -62, 62, 44, P['snout'])
    L.ell(0, -86, 26, 18, P['nose'])
    L.ell(-8, -92, 9, 5, WHITE, alpha=0.7)
    L.stroke([(0, -70), (0, -50)], 4.2, P['nose'])
    c = smile * 10
    L.stroke([(-26, -46 - c * 0.3), (-12, -36 + c * 0.2), (0, -44), (12, -36 + c * 0.2), (26, -46 - c * 0.3)],
             4.2, P['nose'])
    for s in (-1, 1):
        cx, cy = s * 54, -116
        ry = 13 * max(0.08, 1 - blink)
        L.ell(cx, cy, 11.5, ry, P['nose'])
        if blink < 0.5:
            L.ell(cx + 3.5, cy - 5, 4, 4, WHITE)
    return L.image()


def bear_q(wave=0.0, blink=0.0, smile=0.6, size=600):
    return bear(_q(wave, 0.05), _q(blink, 0.125), _q(smile, 0.1), int(size))


# ================================================================== composition helpers
def bust(head_img, body_img, x, y, scale=1.0, tilt=0.0, bob=0.0):
    out = [(body_img, x - BC[0] * scale, y - BC[1] * scale + bob * 0.3, scale, 0.0, None)]
    hx, hy = x, y - 8 * scale + bob
    out.append((head_img, hx - HC[0] * scale, hy - (HC[1] + 120) * scale, scale, tilt, (HC[0], HC[1] + 120)))
    return out


def place(canvas, parts, alpha=1.0):
    for spr, x, y, s, tilt, pivot in parts:
        im = spr
        if s != 1.0:
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
        if tilt:
            im = im.rotate(tilt, resample=Image.BICUBIC, center=(pivot[0] * s, pivot[1] * s))
        if alpha < 1.0:
            im = im.copy()
            im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
        canvas.alpha_composite(im, (int(round(x)), int(round(y))))
