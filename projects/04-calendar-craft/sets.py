"""2D sets in the same flat outlined style: school hallway and canteen. Drawn once at 2x into build/cache/,
then cropped by a 2D camera. Stage units: x -260..1340 (1600 wide), y 0..1920; the frame shows 1080 x 1920
at zoom 1 centred on (540, 960)."""
import functools
from pathlib import Path
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import paths
import fx
from chars import INK

HERE = Path(__file__).resolve().parent
X0, SW, SH = -260, 1600, 1920
K = 2                                           # cache resolution factor
FLOOR = 1500


class D:
    def __init__(self, im):
        self.d = ImageDraw.Draw(im)

    def P(self, x, y):
        return ((x - X0) * K, y * K)

    def rect(self, x0, y0, x1, y1, fill, ol=6, r=0):
        a, b = self.P(x0, y0)
        c, e = self.P(x1, y1)
        if ol:
            self.d.rounded_rectangle([a - ol, b - ol, c + ol, e + ol], r * K + ol, fill=INK)
        self.d.rounded_rectangle([a, b, c, e], r * K, fill=fill)

    def poly(self, pts, fill, ol=6):
        q = [self.P(*p) for p in pts]
        if ol:
            self.d.line(q + [q[0]], fill=INK, width=ol * 2, joint='curve')
        self.d.polygon(q, fill=fill)

    def line(self, pts, w, col=INK):
        self.d.line([self.P(*p) for p in pts], fill=col, width=int(w * K), joint='curve')

    def ellipse(self, cx, cy, rx, ry, fill, ol=6):
        a, b = self.P(cx - rx, cy - ry)
        c, e = self.P(cx + rx, cy + ry)
        if ol:
            self.d.ellipse([a - ol, b - ol, c + ol, e + ol], fill=INK)
        self.d.ellipse([a, b, c, e], fill=fill)

    def text(self, x, y, s, size, col=INK, weight='Heavy', anchor='mm'):
        self.d.text(self.P(x, y), s, font=fx.font(weight, size * K), fill=col, anchor=anchor)


def _floor(dr, y0, c1, c2):
    """Checker floor in one-point perspective (vanishing point at stage centre, y=700)."""
    vx, vy = 540, 700
    rows = []
    z = 1.0
    ys = []
    for k in range(14):
        y = vy + (y0 - vy) * (1.0 + k * 0.22) ** 1.6
        ys.append(min(y, SH + 400))
    for r in range(len(ys) - 1):
        ya, yb = ys[r], ys[r + 1]
        for c in range(-16, 17):
            def X(y, cc):
                return vx + (cc * 140) * (y - vy) / (y0 - vy)
            pts = [(X(ya, c), ya), (X(ya, c + 1), ya), (X(yb, c + 1), yb), (X(yb, c), yb)]
            dr.poly(pts, c1 if (r + c) % 2 == 0 else c2, ol=0)
    dr.line([(X0, y0), (X0 + SW, y0)], 6)


def _shade(im):
    """Soft vignette and paper grain so flat colour does not look like a placeholder."""
    a = np.asarray(im, np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
    a *= (1 - 0.18 * np.clip(r - 0.5, 0, 1))[..., None]
    rng = np.random.default_rng(4)
    a += rng.normal(0, 3.0, (h, w, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _cache(name, fn):
    p = HERE / 'build' / 'cache' / f'{name}.png'
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        fn().save(p)
    return Image.open(p).convert('RGB')


def _hallway():
    im = Image.new('RGB', (SW * K, SH * K), (159, 216, 197))
    dr = D(im)
    dr.rect(X0, 1080, X0 + SW, FLOOR, (104, 176, 160), ol=0)             # wainscot
    dr.rect(X0, 1062, X0 + SW, 1086, (240, 236, 222), ol=5)             # rail
    for x in range(X0 + 60, X0 + SW, 180):                              # wall panels
        dr.line([(x, 1110), (x, FLOOR - 30)], 3, (90, 160, 146))
    # window with sky and a tree
    dr.rect(330, 260, 750, 860, (240, 236, 222), r=10)
    dr.rect(352, 282, 728, 838, (150, 206, 245), ol=4)
    dr.ellipse(640, 700, 200, 170, (120, 190, 110), ol=4)
    dr.ellipse(470, 760, 150, 120, (100, 176, 98), ol=4)
    dr.ellipse(600, 380, 46, 46, (255, 236, 150), ol=0)
    for cx, cy in ((450, 400), (680, 470)):
        dr.ellipse(cx, cy, 70, 26, (250, 250, 255), ol=0)
    dr.line([(540, 282), (540, 838)], 8, (240, 236, 222))
    dr.line([(352, 560), (728, 560)], 8, (240, 236, 222))
    # lockers left and right
    for x0, n in ((-240, 3), (900, 3)):
        for k in range(n):
            x = x0 + k * 150
            dr.rect(x, 640, x + 140, FLOOR - 10, (238, 140, 70), r=6)
            for j in range(4):
                dr.line([(x + 30, 700 + j * 16), (x + 110, 700 + j * 16)], 5, (196, 102, 46))
            dr.rect(x + 108, 1000, x + 120, 1060, (250, 220, 150), ol=3)
            dr.text(x + 70, 860, str(14 + k + (0 if x0 < 0 else 3)), 34, (196, 102, 46))
    # bulletin board + wall clock
    dr.rect(-200, 220, 240, 560, (196, 150, 100), r=8)
    for (x, y, w, h, c, s) in ((-170, 250, 150, 120, (255, 250, 230), 'КРУЖОК\nРОБОТОВ'),
                               (0, 260, 200, 150, (255, 230, 120), 'ОБЕД\n12:30'),
                               (-150, 400, 170, 130, (190, 230, 255), 'ФИЗРА:\nКРОСС'),
                               (50, 430, 160, 110, (255, 200, 210), 'ТИШИНА!')):
        dr.rect(x, y, x + w, y + h, c, ol=4)
        dr.ellipse(x + w / 2, y + 10, 9, 9, (220, 60, 60), ol=2)
        dr.d.multiline_text(dr.P(x + w / 2, y + h / 2 + 8), s, font=fx.font('Heavy', 26 * K), fill=INK,
                            anchor='mm', align='center', spacing=4)
    dr.ellipse(1080, 330, 90, 90, (250, 250, 245), ol=8)
    for k in range(12):
        a = k / 12 * 2 * math.pi
        dr.line([(1080 + 70 * math.sin(a), 330 - 70 * math.cos(a)), (1080 + 80 * math.sin(a), 330 - 80 * math.cos(a))], 4)
    dr.line([(1080, 330), (1080, 280)], 7)
    dr.line([(1080, 330), (1120, 346)], 7)
    _floor(dr, FLOOR, (236, 226, 204), (200, 186, 160))
    return _shade(im)


def _canteen():
    im = Image.new('RGB', (SW * K, SH * K), (250, 241, 222))
    dr = D(im)
    for y in range(0, 1200, 60):                                        # wall tiles
        dr.line([(X0, y), (X0 + SW, y)], 2, (232, 220, 196))
    for x in range(X0, X0 + SW, 60):
        dr.line([(x, 0), (x, 1200)], 2, (232, 220, 196))
    dr.rect(X0, 1200, X0 + SW, FLOOR, (238, 140, 70), ol=0)
    # menu board (prices are a joke of the story, not data)
    dr.rect(230, 150, 850, 560, (52, 74, 66), r=12)
    dr.text(540, 215, 'МЕНЮ', 64, (250, 246, 230))
    for k, (a, b) in enumerate((('Обед', '120 ₽'), ('Пицца', '100 ₽'), ('Компот', '25 ₽'))):
        dr.text(300, 310 + k * 80, a, 50, (250, 246, 230), 'Bold', 'lm')
        dr.text(780, 310 + k * 80, b, 50, (255, 214, 102), 'Heavy', 'rm')
    # serving counter with trays
    dr.rect(X0 - 10, 900, X0 + SW + 10, 1220, (200, 210, 220), r=0)
    dr.rect(X0 - 10, 880, X0 + SW + 10, 920, (230, 236, 242), r=0)
    for x in range(-200, 1300, 240):
        dr.ellipse(x + 90, 870, 80, 30, (250, 250, 250), ol=5)
        dr.ellipse(x + 90, 858, 60, 22, (240, 190, 90) if x % 480 else (220, 90, 70), ol=4)
    _floor(dr, FLOOR, (246, 240, 228), (214, 204, 186))
    return _shade(im)


@functools.lru_cache(None)
def hallway():
    return _cache('hallway', _hallway)


@functools.lru_cache(None)
def canteen():
    return _cache('canteen', _canteen)


def view(bg, cx=540.0, cy=960.0, zoom=1.0, blur=0.0):
    """Frame (1080 x 1920 RGB) of a cached set seen by a camera centred on stage point (cx, cy)."""
    w, h = 1080 / zoom, 1920 / zoom
    box = ((cx - w / 2 - X0) * K, (cy - h / 2) * K, (cx + w / 2 - X0) * K, (cy + h / 2) * K)
    im = bg.transform((1080, 1920), Image.EXTENT, box, Image.BILINEAR)
    if blur > 0.3:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def cam(cx, cy, zoom):
    """Stage point -> screen px mapping for characters: returns (ox, oy, scale) for chars.Pen."""
    return (540 - cx * zoom, 960 - cy * zoom, zoom)
