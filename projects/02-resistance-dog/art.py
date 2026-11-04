"""Own vector drawing of the dog (not a copy of any logo): marker strokes for the hook,
a paper cutout (no hood) and a hooded version, a faceless silhouette and a cartoon hand.
Coordinates are in a 1000x1000 drawing space. Everything is deterministic."""
import functools
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ASSETS = HERE / 'build' / 'assets'
INK = (24, 22, 28)
SS = 2  # supersampling


def bez(p0, p1, p2, p3, n=28):
    out = []
    for i in range(n + 1):
        u = i / n
        a = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u * u, u ** 3
        out.append((a[0] * p0[0] + a[1] * p1[0] + a[2] * p2[0] + a[3] * p3[0],
                    a[0] * p0[1] + a[1] * p1[1] + a[2] * p2[1] + a[3] * p3[1]))
    return out


def chain(*segs):
    pts = []
    for s in segs:
        b = bez(*s)
        pts += b if not pts else b[1:]
    return pts


def ellipse(cx, cy, rx, ry, a0=0.0, a1=2 * math.pi, n=64, tilt=0.0):
    pts = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        c, s = math.cos(tilt), math.sin(tilt)
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


# ------------------------------------------------------------------ the dog (sitting, facing us)
HEAD = chain(((500, 175), (650, 172), (742, 270), (738, 400)),
             ((738, 400), (735, 520), (640, 590), (500, 592)),
             ((500, 592), (360, 590), (265, 520), (262, 400)),
             ((262, 400), (258, 270), (350, 172), (500, 175)))
EAR_L = chain(((300, 255), (215, 250), (165, 360), (190, 470)),
              ((190, 470), (205, 530), (262, 525), (282, 470)))
EAR_R = [(1000 - x, y) for x, y in EAR_L]
MUZZLE = ellipse(500, 468, 128, 92)
NOSE = ellipse(500, 432, 50, 34)
MOUTH = chain(((500, 466), (500, 500), (470, 520), (445, 505))) + chain(((500, 500), (500, 500), (530, 520), (555, 505)))[1:]
EYE_L = ellipse(415, 352, 20, 26)
EYE_R = ellipse(585, 352, 20, 26)
BODY = chain(((372, 575), (300, 660), (285, 800), (330, 880)),
             ((330, 880), (420, 905), (580, 905), (670, 880)),
             ((670, 880), (715, 800), (700, 660), (628, 575)))
PAW_L = ellipse(425, 888, 62, 40)
PAW_R = ellipse(575, 888, 62, 40)
LEG = chain(((500, 700), (498, 780), (500, 840), (500, 870)))
TAIL = chain(((700, 820), (770, 830), (800, 770), (780, 720)))
SPOT = ellipse(592, 345, 58, 52, tilt=0.3)

# drawing order for the hook (start, end as fraction of the drawing time is computed by length)
STROKES = [HEAD, EAR_L, EAR_R, EYE_L, EYE_R, MUZZLE, NOSE, MOUTH, BODY, LEG, PAW_L, PAW_R, TAIL]
FILLED = {id(EYE_L), id(EYE_R), id(NOSE)}


def _len(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


LENGTHS = [_len(s) for s in STROKES]
TOTAL = sum(LENGTHS)


def pen_at(progress):
    """(x, y) of the marker tip in drawing space at progress 0..1 (moves along the strokes)."""
    d = max(0.0, min(1.0, progress)) * TOTAL
    for s, L in zip(STROKES, LENGTHS):
        if d <= L:
            acc = 0.0
            for i in range(len(s) - 1):
                seg = math.dist(s[i], s[i + 1])
                if acc + seg >= d:
                    u = (d - acc) / max(seg, 1e-6)
                    return (s[i][0] + (s[i + 1][0] - s[i][0]) * u, s[i][1] + (s[i + 1][1] - s[i][1]) * u)
                acc += seg
            return s[-1]
        d -= L
    return STROKES[-1][-1]


def _scaled(pts, k, off=(0, 0)):
    return [(off[0] + x * k, off[1] + y * k) for x, y in pts]


def line_art(progress, size=1000, width=13, color=INK):
    """RGBA marker drawing, `progress` 0..1 of total stroke length."""
    S = size * SS
    k = S / 1000
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    left = max(0.0, min(1.0, progress)) * TOTAL
    w = max(1, int(width * k))
    for s, L in zip(STROKES, LENGTHS):
        if left <= 0:
            break
        pts = _scaled(s, k)
        if left >= L:
            part = pts
            if id(s) in FILLED:
                d.polygon(pts, fill=color)
        else:
            part, acc = [pts[0]], 0.0
            for i in range(len(s) - 1):
                seg = math.dist(s[i], s[i + 1])
                if acc + seg >= left:
                    u = (left - acc) / max(seg, 1e-6)
                    part.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u,
                                 pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u))
                    break
                part.append(pts[i + 1])
                acc += seg
        d.line(part, fill=color, width=w, joint='curve')
        for p in (part[0], part[-1]):
            d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=color)
        left -= L
    return im.resize((size, size), Image.LANCZOS)


def _poly(d, pts, k, fill=None, outline=None, width=0):
    p = _scaled(pts, k)
    if fill:
        d.polygon(p, fill=fill)
    if outline:
        d.line(p + [p[0]], fill=outline, width=width, joint='curve')


def colored(hood=False, size=1000, paper_border=True):
    """Colour cutout of the drawing. hood=True adds the black hood of 'digital resistance'."""
    S = size * SS
    k = S / 1000
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w = int(12 * k)
    white, shade, ink = (250, 248, 244, 255), (226, 222, 218, 255), (*INK, 255)
    hood_c, hood_s = (38, 37, 46, 255), (24, 23, 30, 255)
    # silhouette mask for the paper border
    sil = Image.new('L', (S, S), 0)
    ds = ImageDraw.Draw(sil)
    shapes = [HEAD, EAR_L, EAR_R, BODY, PAW_L, PAW_R, TAIL]
    if hood:
        shapes.append(HOOD)
    for sh in shapes:
        ds.polygon(_scaled(sh, k), fill=255)
    for x, y in _scaled(TAIL, k):
        ds.ellipse((x - 22 * k, y - 22 * k, x + 22 * k, y + 22 * k), fill=255)
    if paper_border:
        border = sil.filter(ImageFilter.MaxFilter(int(44 * k) | 1)).filter(ImageFilter.GaussianBlur(2 * k))
        paper = Image.new('RGBA', (S, S), (255, 253, 248, 255))
        im.paste(paper, (0, 0), border.point(lambda v: 255 if v > 110 else 0))
        d = ImageDraw.Draw(im)
    for col, rad in ((ink, 20 * k + w), (white, 20 * k)):
        for x, y in _scaled(TAIL, k):
            d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=col)
    _poly(d, BODY, k, fill=white, outline=ink, width=w)
    _poly(d, ellipse(500, 760, 120, 110), k, fill=shade)
    d.line(_scaled(LEG, k), fill=ink, width=w)
    for paw in (PAW_L, PAW_R):
        _poly(d, paw, k, fill=white, outline=ink, width=w)
    if hood:
        _poly(d, HOOD, k, fill=hood_c, outline=ink, width=w)
        _poly(d, HOOD_IN, k, fill=hood_s)
        _poly(d, MUZZLE, k, fill=white, outline=ink, width=w)
        _poly(d, NOSE, k, fill=ink)
        d.line(_scaled(MOUTH, k), fill=ink, width=w)
        _poly(d, ellipse(486, 422, 16, 9), k, fill=(255, 255, 255, 200))
    else:
        for ear in (EAR_L, EAR_R):
            _poly(d, ear, k, fill=ink)
        _poly(d, HEAD, k, fill=white, outline=ink, width=w)
        _poly(d, SPOT, k, fill=(52, 50, 60, 255))
        _poly(d, MUZZLE, k, fill=shade)
        _poly(d, ellipse(500, 462, 116, 82), k, fill=white)
        for eye in (EYE_L, EYE_R):
            _poly(d, eye, k, fill=ink)
        for ex in (408, 578):
            _poly(d, ellipse(ex, 343, 7, 8), k, fill=(255, 255, 255, 255))
        _poly(d, NOSE, k, fill=ink)
        _poly(d, ellipse(486, 422, 16, 9), k, fill=(255, 255, 255, 200))
        d.line(_scaled(MOUTH, k), fill=ink, width=w)
    return im.resize((size, size), Image.LANCZOS)


HOOD = chain(((500, 40), (600, 120), (790, 250), (785, 470)),
             ((785, 470), (782, 560), (735, 640), (660, 660)),
             ((660, 660), (560, 600), (440, 600), (340, 660)),
             ((340, 660), (265, 640), (218, 560), (215, 470)),
             ((215, 470), (210, 250), (400, 120), (500, 40)))
HOOD_IN = chain(((500, 300), (610, 300), (660, 380), (650, 470)),
                ((650, 470), (640, 560), (580, 590), (500, 592)),
                ((500, 592), (420, 590), (360, 560), (350, 470)),
                ((350, 470), (340, 380), (390, 300), (500, 300)))


def silhouette(size=(600, 1300), color=(28, 30, 40), question=False):
    """Faceless figure in a hoodie seen from the front, holding a marker (authorship is unproven)."""
    W, H = size[0] * SS, size[1] * SS
    k = W / 600
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (*color, 255)
    head = ellipse(300, 230, 120, 140)
    _poly(d, head, k, fill=c)
    torso = chain(((150, 420), (220, 360), (380, 360), (450, 420)),
                  ((450, 420), (500, 640), (480, 820), (440, 860)),
                  ((440, 860), (380, 870), (220, 870), (160, 860)),
                  ((160, 860), (120, 820), (100, 640), (150, 420)))
    _poly(d, torso, k, fill=c)
    for x0 in (175, 335):
        legs = [(x0, 850), (x0 + 90, 850), (x0 + 85, 1240), (x0 + 5, 1240)]
        _poly(d, legs, k, fill=c)
        _poly(d, ellipse(x0 + 40, 1250, 70, 30), k, fill=c)
    arm = chain(((440, 430), (520, 520), (540, 640), (500, 700)))
    d.line(_scaled(arm, k), fill=c, width=int(70 * k), joint='curve')
    d.line(_scaled([(505, 690), (560, 610)], k), fill=(240, 240, 245, 255), width=int(18 * k))
    rim = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if question:
        qd = ImageDraw.Draw(rim)
        from PIL import ImageFont
        f = ImageFont.truetype(str(HERE.parents[1] / 'input/fonts/SF-Pro-Text/SF-Pro-Text-Heavy.otf'), int(200 * k))
        qd.text((300 * k, 235 * k), '?', font=f, fill=(255, 255, 255, 235), anchor='mm')
        im.alpha_composite(rim)
    return im.resize(size, Image.LANCZOS)


def hand(size=420):
    """Cartoon hand holding a marker; the marker tip is at (0.06, 0.94) of the sprite."""
    S = size * SS
    k = S / 1000
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ink = (*INK, 255)
    w = int(16 * k)
    skin, skin_s = (250, 214, 182, 255), (232, 186, 150, 255)
    sleeve, sleeve_s = (52, 92, 170, 255), (36, 66, 128, 255)
    # marker body (diagonal) from tip (60, 940) to back (430, 560)
    mk = [(40, 930), (95, 980), (470, 600), (415, 545)]
    _poly(d, mk, k, fill=(238, 238, 242, 255), outline=ink, width=w)
    _poly(d, [(40, 930), (95, 980), (130, 945), (75, 895)], k, fill=(30, 30, 36, 255))
    _poly(d, [(60, 960), (40, 990), (20, 975), (45, 940)], k, fill=(20, 20, 24, 255))
    # palm + fingers
    palm = chain(((300, 560), (380, 470), (560, 470), (640, 560)),
                 ((640, 560), (700, 660), (640, 780), (520, 790)),
                 ((520, 790), (420, 800), (330, 760), (300, 690)),
                 ((300, 690), (285, 640), (285, 600), (300, 560)))
    _poly(d, palm, k, fill=skin, outline=ink, width=w)
    for i, (x, y) in enumerate(((300, 640), (330, 700), (380, 750))):
        _poly(d, ellipse(x, y, 62, 40, tilt=-0.7), k, fill=skin, outline=ink, width=w)
    _poly(d, ellipse(360, 545, 80, 46, tilt=-0.6), k, fill=skin, outline=ink, width=w)   # thumb
    _poly(d, ellipse(560, 700, 90, 60, tilt=0.4), k, fill=skin_s)
    # sleeve
    sl = [(540, 470), (690, 730), (1000, 520), (1000, 220), (830, 200)]
    _poly(d, sl, k, fill=sleeve, outline=ink, width=w)
    _poly(d, [(560, 500), (680, 700), (720, 675), (600, 470)], k, fill=sleeve_s)
    return im.resize((size, size), Image.LANCZOS)


def poster_text(size=(1400, 360)):
    """DIGITAL RESISTANCE stencil lettering for the rooftop poster (white on transparent)."""
    from PIL import ImageFont
    W, H = size
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(HERE.parents[1] / 'input/fonts/SF-Pro-Text/SF-Pro-Text-Heavy.otf'), 150)
    d.text((W / 2, H / 2), 'DIGITAL RESISTANCE', font=f, fill=(250, 250, 250, 255), anchor='mm')
    a = np.asarray(im).copy()
    # stencil bridges: thin vertical gaps
    for x in range(40, W, 74):
        a[:, x:x + 7, 3] = 0
    return Image.fromarray(a)


def avatar(size=256, ring=(64, 168, 240)):
    """Round avatar with the hooded dog (for the avatars wall)."""
    S = size * 2
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, S - 1, S - 1), fill=(*ring, 255))
    d.ellipse((S * 0.06, S * 0.06, S * 0.94, S * 0.94), fill=(232, 238, 246, 255))
    dog = colored(hood=True, size=S, paper_border=False).resize((int(S * 0.95), int(S * 0.95)), Image.LANCZOS)
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).ellipse((S * 0.06, S * 0.06, S * 0.94, S * 0.94), fill=255)
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    layer.paste(dog, (int(S * 0.025), int(S * 0.12)), dog)
    im.paste(layer, (0, 0), Image.composite(layer, Image.new('RGBA', (S, S)), mask))
    return im.resize((size, size), Image.LANCZOS)


def build_assets():
    ASSETS.mkdir(parents=True, exist_ok=True)
    colored(False).save(ASSETS / 'spotty_cutout.png')
    colored(True).save(ASSETS / 'hooded_cutout.png')
    colored(True, paper_border=False).save(ASSETS / 'hooded_plain.png')
    line_art(1.0).save(ASSETS / 'line_art.png')
    silhouette().save(ASSETS / 'figure.png')
    silhouette(question=True).save(ASSETS / 'figure_q.png')
    hand().save(ASSETS / 'hand.png')
    poster_text().save(ASSETS / 'poster_text.png')
    for i, c in enumerate([(64, 168, 240), (120, 200, 255), (40, 120, 220), (90, 150, 250)]):
        avatar(ring=c).save(ASSETS / f'avatar_{i}.png')
    print('assets ->', ASSETS)


if __name__ == '__main__':
    build_assets()
