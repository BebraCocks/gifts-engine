"""Two characters drawn in code, flat «storybook» style without outlines (cel shadow + soft blush):

Лёва — 23, slim, light skin, tousled dark-brown hair, teal hoodie. Front bust (`leva`) and a back view for
over-the-shoulder shots (`leva_back`).
Часовщик — kind old watchmaker: white hair and short beard, round gold glasses, cream shirt, burgundy
waistcoat with a gold watch chain (`watchmaker`).

Units: head centre at (0, 0), head half-width ≈ 100. A pose is a dict; every sprite is cached by its pose,
quantised, so a still character costs nothing per frame. Heads and bodies are separate sprites, so the
renderer can tilt/bob the head around the neck pivot.
"""
import functools
import math

from PIL import Image

from art import Layer, ellipse_pts, mixc, shade

SKIN = (247, 214, 192)
SKIN_SH = (228, 182, 162)
BLUSH = (240, 150, 150)
LIP = (196, 106, 106)
HAIR = (66, 46, 40)
HAIR_HI = (98, 72, 62)
HOOD = (52, 108, 116)
HOOD_SH = (38, 82, 94)
STRING = (234, 228, 216)
EYE = (44, 34, 38)

OLD_SKIN = (240, 202, 178)
OLD_SH = (214, 166, 146)
WHITE_HAIR = (236, 234, 230)
WHITE_SH = (196, 196, 204)
SHIRT = (240, 230, 210)
SHIRT_SH = (206, 192, 172)
VEST = (124, 40, 52)
VEST_SH = (94, 28, 42)
BOW = (36, 86, 70)
GOLD = (232, 182, 86)
GOLD_SH = (176, 124, 52)

HEAD_BOX = (560, 640)        # head sprite size (px at k=1), head centre at (280, 330)
HC = (280, 330)


def _q(v, step):
    return round(v / step) * step


# ------------------------------------------------------------------ faces
def _eyes(L, look, blink, brow, sad, glint=True, spacing=40, y=0, r=(10.5, 13.5), col=EYE, brow_col=HAIR,
          brow_w=8.5, lid=SKIN):
    lx, ly = look
    for s in (-1, 1):
        cx, cy = s * spacing + lx * 5, y + ly * 4
        ry = r[1] * max(0.08, 1 - blink)
        L.ell(cx, cy, r[0], ry, col)
        if glint and blink < 0.5:
            L.ell(cx + 3.5, cy - 5 * (1 - blink), 3.6, 3.6 * (1 - blink), (255, 255, 255))
        if blink > 0.6:                                     # closed lid line
            L.stroke([(cx - 11, cy), (cx, cy + 3), (cx + 11, cy)], 3.4, col)
        # brow: inner end lifts with sadness, whole brow lifts with surprise
        inner = (s * 18, y - 30 - brow * 7 - sad * 7)
        mid = (s * 38, y - 36 - brow * 7 + sad * 2)
        outer = (s * 56, y - 30 - brow * 5 + sad * 6)
        L.stroke([inner, mid, outer], brow_w, brow_col)


def _mouth(L, smile, open_, y=62, w=22, col=LIP):
    if open_ > 0.08:
        h = 4 + 15 * open_
        top = y - 2 - smile * 3
        pts = [(-w * 0.8, top), (0, top - 2 + smile * 2), (w * 0.8, top), (w * 0.55, top + h * 0.8),
               (0, top + h + smile * 3), (-w * 0.55, top + h * 0.8)]
        m = L.shape(pts, (120, 52, 60))
        L.ell(0, top + h * 0.85, w * 0.42, h * 0.38, (214, 110, 116), clip=m)
    else:
        c = smile * 9
        L.stroke([(-w, y - c * 0.6), (-w * 0.45, y + c * 0.35), (0, y + c * 0.55), (w * 0.45, y + c * 0.35),
                  (w, y - c * 0.6)], 4.6, col)


@functools.lru_cache(maxsize=256)
def _leva_head(look, blink, brow, sad, smile, open_, glow):
    L = Layer(*HEAD_BOX).at(*HC)
    # ears
    for s in (-1, 1):
        L.ell(s * 98, 8, 17, 27, SKIN)
        L.ell(s * 99, 10, 8, 15, SKIN_SH)
    face = [(0, -128), (66, -120), (98, -78), (101, -20), (94, 34), (72, 82), (36, 114), (0, 124),
            (-36, 114), (-72, 82), (-94, 34), (-101, -20), (-98, -78), (-66, -120)]
    fm = L.shape(face, SKIN)
    # cel shadow on the right side and under the hair line
    L.shape([(58, -130), (110, -90), (108, 10), (90, 70), (50, 116), (20, 130), (60, 80), (80, 20), (82, -50)],
            SKIN_SH, clip=fm, alpha=0.75)
    L.shape([(-120, -70), (0, -92), (120, -70), (120, -50), (0, -66), (-120, -48)], SKIN_SH, clip=fm, alpha=0.6,
            blur=6)
    # phone glow from below (night scene)
    if glow > 0:
        L.ell(0, 120, 150, 90, (150, 210, 255), clip=fm, alpha=0.35 * glow, blur=30)
    for s in (-1, 1):
        L.ell(s * 60, 42, 20, 12, BLUSH, alpha=0.32, blur=6)
    _eyes(L, look, blink, brow, sad)
    L.stroke([(-2, 20), (5, 36), (-5, 41)], 4.2, SKIN_SH)        # nose
    _mouth(L, smile, open_)
    # hair: back volume, then the swept fringe
    L.shape([(-104, -10), (-118, -80), (-90, -140), (-30, -170), (40, -168), (96, -138), (120, -80),
             (108, -6), (98, -58), (60, -98), (-60, -98), (-98, -58)], HAIR)
    fr = L.shape([(-102, -40), (-96, -96), (-56, -136), (10, -150), (74, -132), (108, -92), (104, -40),
                  (88, -72), (52, -90), (36, -70), (4, -92), (-36, -72), (-70, -86), (-92, -56)], HAIR)
    L.stroke([(-50, -128), (0, -140), (52, -126)], 9, HAIR_HI, clip=fr, alpha=0.6)
    L.stroke([(20, -150), (40, -172), (34, -186)], 12, HAIR)    # cowlick
    for s_ in (-1, 1):
        L.shape([(s_ * 104, -40), (s_ * 100, 4), (s_ * 92, 10), (s_ * 90, -36)], HAIR)          # sideburns
    L.stroke([(-86, -100), (-60, -122)], 7, HAIR_HI, clip=fr, alpha=0.45)
    return L.image()


def leva_head(look=(0, 0), blink=0.0, brow=0.0, sad=0.0, smile=0.3, open_=0.0, glow=0.0):
    return _leva_head((_q(look[0], 0.1), _q(look[1], 0.1)), _q(blink, 0.125), _q(brow, 0.1), _q(sad, 0.1),
                      _q(smile, 0.1), _q(open_, 0.1), _q(glow, 0.25))


BODY_BOX = (760, 760)        # body sprite, neck pivot at (380, 120)
BC = (380, 120)


@functools.lru_cache(maxsize=32)
def leva_body(arms='phone', glow=0.0):
    L = Layer(*BODY_BOX).at(*BC)
    # neck
    nm = L.poly([(-34, -40), (34, -40), (40, 70), (-40, 70)], SKIN)
    L.ell(0, -30, 60, 34, SKIN_SH, clip=nm, alpha=0.9, blur=4)
    # torso (hoodie)
    tm = L.shape([(-60, 40), (-170, 70), (-250, 140), (-280, 300), (-290, 700), (290, 700), (280, 300),
                  (250, 140), (170, 70), (60, 40)], HOOD)
    L.shape([(120, 60), (280, 160), (300, 700), (180, 700), (190, 300)], HOOD_SH, clip=tm, alpha=0.8)
    # hood collar around the neck
    hm = L.shape([(-96, 20), (-120, 70), (-70, 118), (0, 132), (70, 118), (120, 70), (96, 20), (60, 52),
                  (0, 66), (-60, 52)], shade(HOOD, 0.9))
    L.shape([(40, 40), (120, 60), (110, 110), (40, 126)], HOOD_SH, clip=hm, alpha=0.7)
    for s in (-1, 1):
        L.stroke([(s * 24, 110), (s * 28, 180), (s * 24, 236)], 7, STRING)
        L.ell(s * 24, 240, 7, 9, STRING)
    # pocket seam
    L.stroke([(-150, 520), (-110, 440), (110, 440), (150, 520)], 6, HOOD_SH, alpha=0.8)
    if arms == 'phone':
        # forearms come up from below, hands hold the phone at chest height
        for s in (-1, 1):
            L.shape([(s * 250, 700), (s * 260, 520), (s * 170, 420), (s * 110, 400), (s * 90, 470),
                     (s * 160, 560), (s * 170, 700)], shade(HOOD, 0.93))
        ph = L.poly([(-78, 300), (78, 300), (84, 470), (-84, 470)], (28, 30, 40))
        L.poly([(-70, 308), (70, 308), (75, 462), (-75, 462)], mixc((40, 70, 110), (150, 210, 255), glow))
        for s in (-1, 1):
            L.shape([(s * 120, 470), (s * 132, 400), (s * 96, 370), (s * 70, 384), (s * 66, 420),
                     (s * 76, 470)], SKIN)
            L.stroke([(s * 72, 392), (s * 64, 410)], 5, SKIN_SH)
    elif arms == 'down':
        pass
    return L.image()


@functools.lru_cache(maxsize=8)
def leva_back(rim=(255, 200, 120)):
    """Back of head and shoulders, dark, with a warm rim light from the shop lamp."""
    L = Layer(900, 900).at(450, 330)
    dark = (30, 26, 34)
    tm = L.shape([(-80, 160), (-250, 220), (-380, 330), (-430, 600), (-440, 900), (440, 900), (430, 600),
                  (380, 330), (250, 220), (80, 160)], (34, 50, 58))
    L.shape([(-120, 120), (-170, 230), (0, 280), (170, 230), (120, 120)], (40, 60, 68))
    hm = L.shape([(-105, 60), (-120, -40), (-90, -130), (0, -165), (90, -130), (120, -40), (105, 60), (60, 150),
                  (0, 165), (-60, 150)], dark)
    L.stroke([(60, -140), (112, -60), (108, 40)], 10, rim, clip=hm, alpha=0.8, blur=2)
    L.stroke([(250, 225), (380, 335), (420, 520)], 10, rim, clip=tm, alpha=0.55, blur=3)
    for s in (-1, 1):
        L.ell(s * 112, 10, 16, 26, (52, 40, 44))
    return L.image()


# ------------------------------------------------------------------ watchmaker
@functools.lru_cache(maxsize=256)
def _old_head(look, blink, brow, sad, smile, open_, glint):
    L = Layer(*HEAD_BOX).at(*HC)
    for s in (-1, 1):
        L.ell(s * 100, 14, 18, 28, OLD_SKIN)
        L.ell(s * 101, 16, 8, 15, OLD_SH)
    face = [(0, -126), (70, -118), (102, -74), (104, -16), (98, 40), (78, 88), (40, 118), (0, 126),
            (-40, 118), (-78, 88), (-98, 40), (-104, -16), (-102, -74), (-70, -118)]
    fm = L.shape(face, OLD_SKIN)
    L.shape([(60, -130), (112, -86), (110, 14), (92, 76), (50, 120), (20, 132), (62, 82), (82, 20), (84, -50)],
            OLD_SH, clip=fm, alpha=0.7)
    for s in (-1, 1):
        L.ell(s * 62, 40, 20, 12, BLUSH, alpha=0.3, blur=6)
        L.stroke([(s * 70, 6), (s * 80, 12)], 3, OLD_SH)           # smile lines at the eyes
    # forehead lines
    for k, yy in enumerate((-78, -64)):
        L.stroke([(-34 + 6 * k, yy), (0, yy - 4), (34 - 6 * k, yy)], 3.2, OLD_SH, alpha=0.7)
    _eyes(L, look, blink, brow, sad, r=(9, 11.5), brow_col=WHITE_HAIR, brow_w=11, y=4)
    # glasses (round, gold rims) with a glint that slides across the lenses
    for s_ in (-1, 1):
        L.ell(s_ * 40, 6, 27, 25, (220, 235, 255), alpha=0.14)
        ring = ellipse_pts(s_ * 40, 6, 28, 26, n=72)
        L.stroke(ring + ring[:2], 4.2, GOLD, smooth=False)
        g = glint % 1.0
        L.stroke([(s_ * 40 - 16 + 26 * g, -8), (s_ * 40 - 6 + 26 * g, 2)], 4, (255, 255, 255),
                 alpha=0.6 * math.sin(math.pi * g))
    L.stroke([(-10, 2), (0, -2), (10, 2)], 4.5, GOLD)                # bridge
    for s in (-1, 1):
        L.stroke([(s * 70, 2), (s * 98, -4)], 4, GOLD)
    L.stroke([(-2, 22), (6, 40), (-6, 46)], 4.4, OLD_SH)            # nose
    # beard + moustache (white), mouth shows between them
    L.shape([(-92, 40), (-80, 96), (-40, 132), (0, 142), (40, 132), (80, 96), (92, 40), (70, 70), (40, 86),
             (0, 90), (-40, 86), (-70, 70)], WHITE_HAIR)
    L.shape([(30, 96), (84, 64), (78, 100), (40, 128)], WHITE_SH, alpha=0.35, blur=8)
    _mouth(L, smile, open_, y=72, w=18, col=(150, 80, 80))
    L.shape([(-46, 62), (-30, 52), (0, 56), (30, 52), (46, 62), (30, 66), (0, 62), (-30, 66)], WHITE_HAIR)
    # hair: white sides, thin combed top
    for s in (-1, 1):
        L.shape([(s * 92, -30), (s * 112, -90), (s * 80, -128), (s * 50, -118), (s * 84, -80), (s * 96, 0)],
                WHITE_HAIR)
    L.shape([(-70, -112), (-30, -134), (30, -136), (74, -116), (40, -122), (0, -124), (-40, -120)], WHITE_HAIR)
    return L.image()


def old_head(look=(0, 0), blink=0.0, brow=0.0, sad=0.0, smile=0.45, open_=0.0, glint=0.0):
    return _old_head((_q(look[0], 0.1), _q(look[1], 0.1)), _q(blink, 0.125), _q(brow, 0.1), _q(sad, 0.1),
                     _q(smile, 0.1), _q(open_, 0.1), _q(glint, 0.05))


@functools.lru_cache(maxsize=16)
def old_body(hands='rest'):
    L = Layer(*BODY_BOX).at(*BC)
    nm = L.poly([(-36, -40), (36, -40), (42, 70), (-42, 70)], OLD_SKIN)
    L.ell(0, -30, 60, 34, OLD_SH, clip=nm, alpha=0.9, blur=4)
    # shirt
    sm = L.shape([(-60, 40), (-180, 74), (-262, 150), (-292, 320), (-300, 700), (300, 700), (292, 320),
                  (262, 150), (180, 74), (60, 40)], SHIRT)
    L.shape([(140, 70), (290, 170), (300, 700), (200, 700), (210, 300)], SHIRT_SH, clip=sm, alpha=0.8)
    # collar
    for s in (-1, 1):
        L.poly([(s * 6, 66), (s * 56, 36), (s * 74, 70), (s * 30, 104)], SHIRT)
        L.stroke([(s * 56, 36), (s * 74, 70), (s * 30, 104)], 3, SHIRT_SH)
    # waistcoat
    vm = L.poly([(-180, 120), (-60, 100), (0, 300), (60, 100), (180, 120), (196, 700), (-196, 700)], VEST)
    L.poly([(60, 100), (180, 120), (196, 700), (110, 700), (120, 300)], VEST_SH, clip=vm, alpha=0.8)
    for k in range(4):
        L.ell(0, 340 + k * 70, 9, 9, GOLD)
        L.ell(2, 338 + k * 70, 4, 4, (255, 230, 160))
    # pocket + watch chain
    L.stroke([(-150, 430), (-90, 430)], 6, VEST_SH)
    L.stroke([(0, 410), (-50, 440), (-110, 432)], 5, GOLD)
    # bow tie
    for s in (-1, 1):
        L.shape([(0, 80), (s * 44, 60), (s * 50, 100), (s * 40, 112)], BOW)
    L.ell(0, 88, 12, 13, shade(BOW, 0.85))
    # sleeves: the arm seam and a soft fold; forearms on the counter come from old_hands()
    for s_ in (-1, 1):
        L.stroke([(s_ * 230, 150), (s_ * 250, 330), (s_ * 246, 700)], 5, SHIRT_SH, alpha=0.7)
    return L.image()


@functools.lru_cache(maxsize=16)
def old_hands(pose='rest'):
    """Forearms on the counter, hands clasped in the middle (sprite 900×320; counter edge at y ≈ 250)."""
    L = Layer(900, 320).at(450, 0)
    for s_ in (-1, 1):
        am = L.shape([(s_ * 300, 0), (s_ * 330, 120), (s_ * 250, 220), (s_ * 120, 250), (s_ * 70, 200),
                      (s_ * 150, 150), (s_ * 230, 40)], SHIRT)
        L.shape([(s_ * 260, 150), (s_ * 330, 120), (s_ * 250, 220), (s_ * 120, 250)], SHIRT_SH, clip=am,
                alpha=0.7)
        L.stroke([(s_ * 228, 120), (s_ * 150, 200)], 16, SHIRT_SH, alpha=0.6)     # rolled cuff
    # left hand underneath, right hand on top with a thumb
    lm = L.shape([(-150, 190), (-100, 160), (-20, 168), (30, 196), (10, 240), (-70, 250), (-130, 236)], OLD_SKIN)
    L.shape([(-150, 190), (-130, 236), (-70, 250), (-110, 220)], OLD_SH, clip=lm, alpha=0.6)
    rm = L.shape([(150, 186), (90, 164), (10, 176), (-40, 204), (-20, 244), (60, 254), (130, 236)], OLD_SKIN)
    L.shape([(150, 186), (130, 236), (60, 254), (110, 214)], OLD_SH, clip=rm, alpha=0.6)
    for k in range(3):
        L.stroke([(-18 + k * 26, 206 + k * 2), (-10 + k * 26, 238 + k * 2)], 3, OLD_SH, alpha=0.8)
    L.stroke([(40, 178), (-6, 170), (-30, 182)], 13, OLD_SKIN)                          # thumb
    L.stroke([(-6, 170), (-30, 182)], 3, OLD_SH, alpha=0.5)
    return L.image()


# ------------------------------------------------------------------ composition helper
def bust(head, body, x, y, scale=1.0, tilt=0.0, bob=0.0):
    """Return [(sprite, x, y)] for placing: neck pivot of the body at (x, y)."""
    out = []
    bw, bh = body.size
    out.append((body, x - BC[0] * scale, y - BC[1] * scale + bob * 0.3, scale, 0.0, None))
    hx, hy = x, y - 8 * scale + bob
    out.append((head, hx - HC[0] * scale, hy - (HC[1] + 120) * scale, scale, tilt, (HC[0], HC[1] + 120)))
    return out


def place(canvas, parts):
    """canvas: PIL RGBA/RGB; parts from bust(). Tilt rotates the head around the neck point."""
    for spr, x, y, s, tilt, pivot in parts:
        im = spr
        if s != 1.0:
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
        if tilt:
            px, py = pivot[0] * s, pivot[1] * s
            im = im.rotate(tilt, resample=Image.BICUBIC, center=(px, py))
        canvas.alpha_composite(im, (int(round(x)), int(round(y)))) if canvas.mode == 'RGBA' else \
            canvas.paste(im, (int(round(x)), int(round(y))), im)
