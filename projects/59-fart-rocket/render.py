"""«Реактивный пук»: всё нарисовано кодом (2D). Кадр — чистая функция времени содержания.

    python -B projects/59-fart-rocket/render.py --frames 0,600,1200     # пробные кадры (номера кадров вывода)
    python -B projects/59-fart-rocket/render.py --video out.mp4         # полный видеоряд (вызывает build.py)
"""
import functools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
import banner  # noqa: E402
import captions as CAP  # noqa: E402
import frames  # noqa: E402
from script import LINES  # noqa: E402
from timeline import DUR, ON, END, S, E, TAKES  # noqa: E402
from events import AD_STOP  # noqa: E402

W, H, FPS = 1080, 1920, 60
SS = 2                                   # суперсэмплинг спрайтов
BR = banner.Breaks([AD_STOP], cy=H / 2)

INK = (34, 28, 52)
GAS = (128, 214, 74)
GAS_D = (74, 150, 52)
GAS_L = (190, 240, 140)
SKIN = (246, 204, 166)
HOOD = (38, 168, 160)
HOOD_D = (24, 120, 116)
PANTS = (54, 70, 124)
WOOD = (184, 118, 66)
WOOD_D = (138, 84, 44)
YEL = (255, 214, 64)
RED = (240, 74, 74)
WHITE = (255, 255, 255)


# ------------------------------------------------------------------ утилиты
def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def sm(x):
    x = cl(x); return x * x * (3 - 2 * x)


def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back(x, s=1.7):
    x = cl(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def spring(x, f=2.2, z=0.38):
    if x <= 0:
        return 0.0
    w = 2 * math.pi * f; wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))


def noise(t, seed=0):
    return (math.sin(t * 13.1 + seed) * 0.5 + math.sin(t * 29.7 + seed * 2.3) * 0.3 + math.sin(t * 51.3 + seed * 4.1) * 0.2)


@functools.lru_cache(64)
def font(size, w='Heavy'):
    return ImageFont.truetype(paths.font(f'SF-Pro-Text-{w}.otf'), size)


@functools.lru_cache(512)
def text_spr(text, size, color=WHITE, w='Heavy', stroke=0, scol=INK):
    f = font(size, w)
    l, t_, r, b = f.getbbox(text, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 8, b - t_ + 8), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4 - l, 4 - t_), text, font=f, fill=color + (255,), stroke_width=stroke,
                            stroke_fill=scol + (255,))
    return im


def put(im, spr, cx, cy, scale=1.0, rot=0.0, alpha=1.0, anchor=(0.5, 0.5)):
    """Вставить спрайт: точка anchor спрайта (доли) попадает в (cx, cy)."""
    if spr is None or alpha <= 0.003 or scale <= 0.01:
        return
    w, h = spr.size
    ax, ay = anchor[0] * w, anchor[1] * h
    if abs(scale - 1) > 0.004:
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        spr = spr.resize((nw, nh), Image.BILINEAR)
        ax, ay = ax * nw / w, ay * nh / h
        w, h = nw, nh
    if abs(rot) > 0.05:
        r = math.radians(rot)
        dx, dy = ax - w / 2, ay - h / 2
        spr = spr.rotate(rot, Image.BICUBIC, expand=True)
        nx = dx * math.cos(r) + dy * math.sin(r)
        ny = -dx * math.sin(r) + dy * math.cos(r)
        ax, ay = spr.size[0] / 2 + nx, spr.size[1] / 2 + ny
    if alpha < 0.997:
        spr = spr.copy()
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * alpha)))
    x, y = int(round(cx - ax)), int(round(cy - ay))
    # обрезка по кадру
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(im.size[0], x + spr.size[0]), min(im.size[1], y + spr.size[1])
    if x1 <= x0 or y1 <= y0:
        return
    if (x0, y0, x1, y1) != (x, y, x + spr.size[0], y + spr.size[1]):
        spr = spr.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    im.alpha_composite(spr, (x0, y0))


def canvas(w, h):
    im = Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def done(im):
    return im.resize((im.size[0] // SS, im.size[1] // SS), Image.LANCZOS)


def P(*v):
    return [x * SS for x in v]


def oval(d, cx, cy, rx, ry, fill, ol=INK, w=6):
    d.ellipse(P(cx - rx, cy - ry, cx + rx, cy + ry), fill=fill, outline=ol, width=w * SS if ol else 0)


def rrect(d, box, r, fill, ol=INK, w=6):
    d.rounded_rectangle(P(*box), r * SS, fill=fill, outline=ol, width=w * SS if ol else 0)


def thick(d, pts, width, col, ol=INK, w=6):
    pts = [tuple(P(*p)) for p in pts]
    if ol:
        d.line(pts, fill=ol, width=(width + 2 * w) * SS, joint='curve')
        for p in (pts[0], pts[-1]):
            r = (width / 2 + w) * SS
            d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=ol)
    d.line(pts, fill=col, width=width * SS, joint='curve')
    for p in (pts[0], pts[-1]):
        r = width / 2 * SS
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=col)


@functools.lru_cache(16)
def vgrad(top, bot, h=H, w=W):
    a = np.linspace(0, 1, h)[:, None, None]
    g = np.array(top, np.float32) * (1 - a) + np.array(bot, np.float32) * a
    return Image.fromarray(np.repeat(g, w, 1).astype(np.uint8), 'RGB').convert('RGBA')


def grad_t(top, bot):
    return vgrad(tuple(top), tuple(bot)).copy()


# ------------------------------------------------------------------ герой
@functools.lru_cache(8)
def chair_parts():
    """Детали стула: (спрайт, центр по x, центр по y) в системе героя (сиденье в (0,0))."""
    parts = []
    im, d = canvas(270, 300)
    rrect(d, (8, 8, 262, 292), 26, WOOD_D)
    for k in range(3):
        rrect(d, (40, 40 + k * 80, 230, 80 + k * 80), 10, WOOD, None)
    parts.append((done(im), 0, -140))                    # спинка
    for x in (-128, 128):
        im, d = canvas(34, 250)
        rrect(d, (4, 4, 30, 246), 8, WOOD_D)
        parts.append((done(im), x, 150))                 # ножки
    im, d = canvas(330, 54)
    rrect(d, (4, 4, 326, 50), 14, WOOD)
    d.line(P(30, 20, 300, 20), fill=(214, 150, 92), width=6 * SS)
    parts.append((done(im), 0, 20))                      # сиденье
    return parts


@functools.lru_cache(8)
def body_spr(pose='sit'):
    """Тело сидя, вид спереди. Точка сиденья — (260, 470) на холсте 520x760."""
    im, d = canvas(520, 760)
    cx, sy = 260, 470
    # ноги
    for s in (-1, 1):
        x0 = cx + s * 62
        thick(d, [(x0, sy - 10), (x0 + s * 6, sy + 40), (x0 + s * 4, sy + 215)], 84, PANTS)
        oval(d, x0 + s * 14, sy + 238, 62, 30, (236, 236, 240))
        d.rectangle(P(x0 + s * 14 - 58, sy + 236, x0 + s * 14 + 58, sy + 246), fill=RED)
        oval(d, x0 + s * 4, sy + 22, 50, 36, PANTS)          # колени
    # туловище (худи)
    d.polygon([tuple(P(cx - 150, sy - 210)), tuple(P(cx + 150, sy - 210)), tuple(P(cx + 128, sy + 10)),
               tuple(P(cx - 128, sy + 10))], fill=INK)
    d.polygon([tuple(P(cx - 143, sy - 205)), tuple(P(cx + 143, sy - 205)), tuple(P(cx + 122, sy + 4)),
               tuple(P(cx - 122, sy + 4))], fill=HOOD)
    oval(d, cx - 112, sy - 180, 50, 50, HOOD)
    oval(d, cx + 112, sy - 180, 50, 50, HOOD)
    d.polygon([tuple(P(cx - 140, sy - 205)), tuple(P(cx + 140, sy - 205)), tuple(P(cx + 120, sy)),
               tuple(P(cx - 120, sy))], fill=HOOD)
    rrect(d, (cx - 80, sy - 80, cx + 80, sy - 10), 22, HOOD_D, INK, 4)      # карман
    oval(d, cx, sy - 212, 70, 26, HOOD_D, INK, 5)                         # капюшон у шеи
    d.line(P(cx - 22, sy - 190, cx - 26, sy - 120), fill=WHITE, width=5 * SS)
    d.line(P(cx + 22, sy - 190, cx + 26, sy - 120), fill=WHITE, width=5 * SS)
    # руки на коленях
    for s in (-1, 1):
        thick(d, [(cx + s * 140, sy - 175), (cx + s * 160, sy - 70), (cx + s * 92, sy + 8)], 56, HOOD)
        oval(d, cx + s * 86, sy + 14, 30, 27, SKIN)
    return done(im)


@functools.lru_cache(256)
def head_spr(expr='calm', mouth=0, squash=0):
    """Голова 300x300, центр (150, 160). mouth 0/1 — рот закрыт/открыт; squash 0..3 — перегрузка."""
    im, d = canvas(300, 300)
    cx, cy = 150, 160
    rx, ry = 100, 104
    if squash:
        rx, ry = 100 + squash * 10, 104 - squash * 10
    oval(d, cx - rx + 4, cy + 8, 18, 24, SKIN)
    oval(d, cx + rx - 4, cy + 8, 18, 24, SKIN)
    oval(d, cx, cy, rx, ry, SKIN)
    if squash:                                           # щёки «плывут»
        for s in (-1, 1):
            oval(d, cx + s * (rx - 20), cy + 40 + squash * 6, 30 + squash * 4, 26, SKIN, INK, 4)
    # волосы
    hy = cy - ry
    d.chord(P(cx - rx - 4, hy - 6, cx + rx + 4, cy + 30), 180, 360, fill=INK)
    d.chord(P(cx - rx + 10, hy + 22, cx + rx - 10, cy + 40), 180, 360, fill=SKIN)
    d.polygon([tuple(P(cx - 30, hy + 4)), tuple(P(cx + 10, hy - 34)), tuple(P(cx + 4, hy + 6)),
               tuple(P(cx + 44, hy - 22)), tuple(P(cx + 34, hy + 16))], fill=INK)
    ey = cy - 8
    if expr in ('calm', 'smug', 'talk'):
        for s in (-1, 1):
            oval(d, cx + s * 38, ey, 21, 25, WHITE, INK, 5)
            oval(d, cx + s * 38 + 3, ey + 4, 10, 11, INK, None)
            d.line(P(cx + s * 38 - 22, ey - 40 + (6 if expr == 'smug' and s < 0 else 0), cx + s * 38 + 22, ey - 44),
                   fill=INK, width=7 * SS)
        if expr == 'smug':
            for s in (-1, 1):
                d.chord(P(cx + s * 38 - 23, ey - 27, cx + s * 38 + 23, ey + 4), 180, 360, fill=SKIN)
                d.line(P(cx + s * 38 - 22, ey - 6, cx + s * 38 + 22, ey - 6), fill=INK, width=5 * SS)
    elif expr in ('shock', 'scared'):
        for s in (-1, 1):
            oval(d, cx + s * 40, ey - 4, 27, 32, WHITE, INK, 5)
            oval(d, cx + s * 40, ey - 2, 7, 8, INK, None)
            d.arc(P(cx + s * 40 - 26, ey - 66, cx + s * 40 + 26, ey - 30), 200, 340, fill=INK, width=7 * SS)
    elif expr == 'happy':
        for s in (-1, 1):
            d.arc(P(cx + s * 38 - 22, ey - 18, cx + s * 38 + 22, ey + 18), 200, 340, fill=INK, width=8 * SS)
    elif expr == 'strain':
        for s in (-1, 1):
            x0 = cx + s * 40
            d.line(P(x0 - 20, ey - 14, x0 + 20, ey), fill=INK, width=8 * SS) if s < 0 else \
                d.line(P(x0 + 20, ey - 14, x0 - 20, ey), fill=INK, width=8 * SS)
            d.line(P(x0 - 20, ey + 14, x0 + 20, ey), fill=INK, width=8 * SS) if s < 0 else \
                d.line(P(x0 + 20, ey + 14, x0 - 20, ey), fill=INK, width=8 * SS)
    # нос
    d.arc(P(cx - 12, cy + 4, cx + 12, cy + 30), 300, 120, fill=(200, 140, 110), width=5 * SS)
    my = cy + 56 - squash * 4
    if expr == 'strain':
        rrect(d, (cx - 52, my - 18, cx + 52, my + 18), 10, WHITE, INK, 5)
        for k in (-26, 0, 26):
            d.line(P(cx + k, my - 16, cx + k, my + 16), fill=INK, width=3 * SS)
        d.line(P(cx - 50, my, cx + 50, my), fill=INK, width=3 * SS)
    elif expr in ('shock',):
        oval(d, cx, my + 4, 24, 30 if mouth else 22, (120, 40, 50))
    elif expr == 'scared':
        pts = [(cx - 40 + k * 10, my + (6 if k % 2 else -6)) for k in range(9)]
        d.line([tuple(P(*p)) for p in pts], fill=INK, width=6 * SS, joint='curve')
    elif expr == 'happy' or mouth:
        d.chord(P(cx - 44, my - 26, cx + 44, my + 30 if mouth else my + 20), 0, 180, fill=(120, 40, 50),
                outline=INK, width=5 * SS)
        d.chord(P(cx - 22, my + 4, cx + 22, my + 26), 180, 360, fill=(236, 110, 120))
    elif expr == 'smug':
        d.arc(P(cx - 40, my - 30, cx + 44, my + 10), 20, 150, fill=INK, width=7 * SS)
    else:
        d.arc(P(cx - 38, my - 30, cx + 38, my + 12), 25, 155, fill=INK, width=7 * SS)
    # румянец
    for s in (-1, 1):
        d.ellipse(P(cx + s * 66 - 16, cy + 26, cx + s * 66 + 16, cy + 40), fill=(240, 150, 140, 140))
    return done(im)


def talk_open(t, key):
    if key not in S:
        return 0
    u = t - S[key]
    return 1 if 0 <= u < E[key] - S[key] - 0.08 and int(u * 8.5) % 2 == 0 else 0


def hero(im, x, y, scale=1.0, expr='calm', mouth=0, chair=True, rot=0.0, squash=0, bob=0.0, soot=0.0,
         head_dy=0.0, chair_alpha=1.0):
    """(x, y) — точка сиденья в кадре."""
    if chair:
        for spr, px, py in chair_parts():
            put(im, spr, x + px * scale, y + py * scale + bob * 0.3, scale, alpha=chair_alpha)
    b = body_spr()
    h = head_spr(expr, mouth, squash)
    if soot > 0:
        b, h = sooty(b, soot), sooty(h, soot)
    put(im, b, x, y + bob, scale, rot, anchor=(0.5, 470 / 760))
    hx = x + math.sin(math.radians(rot)) * -330 * scale
    hy = y + bob - 320 * scale + head_dy * scale + squash * 8 * scale
    put(im, h, hx, hy, scale, rot, anchor=(0.5, 0.62))


def sooty(spr, k):
    a = np.asarray(spr).astype(np.float32)
    a[..., :3] *= 1 - 0.7 * k
    a[..., :3] += np.array([30, 20, 10]) * k
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


# ------------------------------------------------------------------ газ
@functools.lru_cache(32)
def puff_spr(r=60, seed=0, face=True, col=GAS):
    rnd = random.Random(seed)
    im, d = canvas(int(r * 3.2), int(r * 2.6))
    cx, cy = r * 1.6, r * 1.4
    blobs = [(cx, cy, r)] + [(cx + math.cos(a) * r * 0.75, cy + math.sin(a) * r * 0.5, r * rnd.uniform(0.5, 0.7))
                             for a in [k * math.pi / 3 + rnd.uniform(-0.3, 0.3) for k in range(6)]]
    for bx, by, br in blobs:
        oval(d, bx, by, br + 6, br + 6, INK, None)
    dark = mix(col, (40, 90, 30), 0.35)
    for bx, by, br in blobs:
        oval(d, bx, by, br, br, dark, None)
    for bx, by, br in blobs:
        oval(d, bx - br * 0.12, by - br * 0.14, br * 0.86, br * 0.86, col, None)
    oval(d, cx - r * 0.45, cy - r * 0.5, r * 0.22, r * 0.14, mix(col, WHITE, 0.6), None)
    if face:
        for s in (-1, 1):
            oval(d, cx + s * r * 0.28, cy - r * 0.05, r * 0.11, r * 0.14, INK, None)
            oval(d, cx + s * r * 0.28 + r * 0.03, cy - r * 0.1, r * 0.04, r * 0.05, WHITE, None)
        d.arc(P(cx - r * 0.22, cy + r * 0.02, cx + r * 0.22, cy + r * 0.32), 20, 160, fill=INK, width=int(r * 0.07) * SS)
    return done(im)


def jet(im, x, y, length, width, t, col_in=(230, 255, 200), col_out=GAS, fire=0.0, down=True):
    """Струя газа из-под сиденья вниз (или вверх, если down=False)."""
    if length < 4:
        return
    L = int(length); Wd = int(width)
    lay = Image.new('RGBA', (Wd * 3 + 40, L + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = lay.size[0] / 2
    outer = mix(col_out, (255, 120, 30), fire)
    inner = mix(col_in, (255, 240, 160), fire)
    for k, (wf, colr) in enumerate(((1.0, outer), (0.55, inner))):
        pts = []
        for i in range(21):
            v = i / 20
            ww = Wd * wf * (0.5 + 0.9 * v ** 0.6) * (1 + 0.12 * noise(t * 3 + v * 4, k + i))
            pts.append((c - ww / 2, 20 + v * L))
        for i in range(20, -1, -1):
            v = i / 20
            ww = Wd * wf * (0.5 + 0.9 * v ** 0.6) * (1 + 0.12 * noise(t * 3 + v * 4 + 7, k + i))
            pts.append((c + ww / 2, 20 + v * L))
        d.polygon(pts, fill=colr + (235 if k == 0 else 255,))
    # кольца-«ромбы» реактивной струи
    for i in range(1, 5):
        yy = 20 + L * i / 5 - (t * 900) % (L / 5)
        r = Wd * 0.25
        d.ellipse((c - r, yy - r * 0.5, c + r, yy + r * 0.5), fill=WHITE + (150,))
    lay = lay.filter(ImageFilter.GaussianBlur(5))
    if not down:
        lay = lay.transpose(Image.FLIP_TOP_BOTTOM)
        im.alpha_composite(lay, (int(x - c), int(y - L - 40)))
    else:
        put(im, lay, x, y - 20, 1.0, anchor=(0.5, 0.0))


# ------------------------------------------------------------------ фоны и детали
def blueprint(t, top=(26, 34, 74), bot=(44, 28, 84)):
    im = grad_t(top, bot)
    d = ImageDraw.Draw(im)
    off = (t * 30) % 90
    for x in range(-90, W + 90, 90):
        d.line((x + off, 0, x + off, H), fill=(255, 255, 255, 18), width=2)
    for y in range(-90, H + 90, 90):
        d.line((0, y + off, W, y + off), fill=(255, 255, 255, 18), width=2)
    return im


BUBBLES = [(random.Random(i).uniform(0, W), random.Random(i + 50).uniform(0, H), random.Random(i + 9).uniform(30, 90),
            random.Random(i + 3).uniform(6, 18), random.Random(i + 4).uniform(0, 6.28)) for i in range(26)]


def bubbles(im, t, alpha=90, col=GAS):
    d = ImageDraw.Draw(im)
    for x0, y0, sp, r, ph in BUBBLES:
        y = (y0 - sp * t) % (H + 60) - 30
        x = x0 + 16 * math.sin(t * 1.1 + ph)
        d.ellipse((x - r, y - r, x + r, y + r), outline=col + (alpha,), width=3)


def panel(im, box, fill=(255, 255, 255, 235), r=34, ol=INK, w=6):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 + 8, y0 + 12, x1 + 8, y1 + 12), r, fill=(0, 0, 0, 70))
    d.rounded_rectangle(box, r, fill=fill, outline=ol, width=w)


def label(im, text, cx, cy, size=64, col=WHITE, stroke=6, scale=1.0, rot=0.0, alpha=1.0, w='Heavy'):
    put(im, text_spr(text, size, col, w, stroke), cx, cy, scale, rot, alpha)


def counter_text(v, suffix=''):
    s = f'{int(round(v)):,}'.replace(',', ' ')
    return s + suffix


def pop(u, d=0.35):
    """Масштаб появления с пружиной."""
    return spring(u / d * 0.5, 2.0, 0.42) if u > 0 else 0.0


@functools.lru_cache(4)
def coin_spr(r=70):
    im, d = canvas(r * 2 + 20, r * 2 + 20)
    c = r + 10
    oval(d, c, c, r, r, (236, 190, 70))
    oval(d, c, c, r - 14, r - 14, (250, 214, 100), (190, 140, 40), 4)
    f = font(int(r * 1.1) * SS, 'Heavy')
    d.text((c * SS, c * SS), '₽', font=f, fill=(190, 130, 30), anchor='mm')
    return done(im)


@functools.lru_cache(4)
def bullet_spr():
    im, d = canvas(220, 70)
    d.polygon([tuple(P(60, 8)), tuple(P(160, 8)), tuple(P(212, 35)), tuple(P(160, 62)), tuple(P(60, 62))], fill=INK)
    d.polygon([tuple(P(66, 14)), tuple(P(158, 14)), tuple(P(202, 35)), tuple(P(158, 56)), tuple(P(66, 56))],
              fill=(210, 160, 80))
    rrect(d, (8, 8, 72, 62), 6, (190, 190, 200))
    return done(im)


@functools.lru_cache(4)
def fighter_spr():
    """Силуэт истребителя сверху, носом вправо."""
    im, d = canvas(420, 260)
    body = [(20, 120), (60, 100), (300, 108), (400, 130), (300, 152), (60, 160), (20, 140)]
    wing = [(140, 112), (230, 20), (262, 20), (240, 112), (240, 148), (262, 240), (230, 240), (140, 148)]
    tail = [(30, 112), (60, 50), (82, 50), (90, 112), (90, 148), (82, 210), (60, 210), (30, 148)]
    for poly, col in ((wing, (150, 160, 175)), (tail, (150, 160, 175)), (body, (184, 192, 206))):
        d.polygon([tuple(P(*p)) for p in poly], fill=col, outline=INK, width=6 * SS)
    oval(d, 320, 130, 40, 13, (90, 190, 240))
    return done(im)


@functools.lru_cache(4)
def pilot_spr():
    """Пилот в шлеме, без сознания."""
    im, d = canvas(260, 300)
    rrect(d, (40, 190, 220, 296), 40, (90, 110, 70))
    oval(d, 130, 130, 100, 104, (200, 205, 215))
    rrect(d, (52, 100, 208, 190), 40, SKIN)
    for s in (-1, 1):
        x0 = 130 + s * 36
        d.line(P(x0 - 14, 124, x0 + 14, 148), fill=INK, width=7 * SS)
        d.line(P(x0 + 14, 124, x0 - 14, 148), fill=INK, width=7 * SS)
    oval(d, 130, 172, 18, 10, (120, 40, 50))
    oval(d, 130, 64, 70, 26, (60, 70, 90), INK, 5)
    return done(im)


@functools.lru_cache(4)
def elevator_spr():
    im, d = canvas(330, 600)
    rrect(d, (6, 6, 324, 594), 18, (160, 168, 184))
    rrect(d, (36, 70, 294, 570), 10, (70, 76, 96))
    rrect(d, (120, 20, 210, 56), 8, (30, 30, 40))
    d.text(P(165, 38), '▲', font=font(28 * SS), fill=(255, 90, 90), anchor='mm')
    return done(im)


@functools.lru_cache(4)
def house_spr(hole=False):
    im, d = canvas(620, 640)
    rrect(d, (70, 260, 550, 630), 8, (232, 206, 176))
    for yy in range(290, 620, 34):
        d.line(P(76, yy, 544, yy), fill=(214, 186, 156), width=4 * SS)
    d.polygon([tuple(P(30, 280)), tuple(P(310, 40)), tuple(P(590, 280))], fill=(200, 72, 62), outline=INK,
              width=6 * SS)
    for k in range(5):
        d.line(P(70 + k * 20, 260 - k * 40 + 20, 550 - k * 20, 260 - k * 40 + 20), fill=(170, 52, 48), width=4 * SS)
    rrect(d, (250, 470, 370, 630), 10, (120, 80, 50))
    oval(d, 350, 555, 8, 8, YEL, None)
    for x in (120, 420):
        rrect(d, (x, 330, x + 90, 420), 8, (255, 232, 140))
        d.line(P(x + 45, 330, x + 45, 420), fill=INK, width=5 * SS)
        d.line(P(x, 375, x + 90, 375), fill=INK, width=5 * SS)
    if hole:
        pts = [(270, 150), (290, 122), (318, 130), (344, 118), (356, 150), (340, 178), (306, 172), (280, 182)]
        d.polygon([tuple(P(*p)) for p in pts], fill=(20, 16, 24), outline=INK, width=4 * SS)
        for (a, b) in ((pts[1], (296, 92)), (pts[3], (352, 96)), (pts[4], (380, 150))):
            d.line([tuple(P(*a)), tuple(P(*b))], fill=INK, width=5 * SS)
    return done(im)


@functools.lru_cache(4)
def kid_spr():
    im, d = canvas(220, 340)
    thick(d, [(90, 250), (84, 326)], 30, (60, 80, 140))
    thick(d, [(130, 250), (136, 326)], 30, (60, 80, 140))
    rrect(d, (60, 150, 160, 262), 30, (240, 120, 60))
    thick(d, [(150, 170), (196, 70)], 26, (240, 120, 60))         # рука показывает вверх
    oval(d, 198, 62, 16, 16, SKIN)
    oval(d, 110, 98, 62, 62, SKIN)
    d.chord(P(46, 30, 174, 120), 180, 360, fill=(120, 70, 40))
    oval(d, 128, 92, 8, 10, INK, None)
    oval(d, 92, 92, 8, 10, INK, None)
    d.arc(P(90, 104, 132, 134), 20, 160, fill=INK, width=5 * SS)
    return done(im)


@functools.lru_cache(4)
def expert_spr(wink=False):
    im, d = canvas(460, 760)
    rrect(d, (70, 300, 390, 760), 60, (246, 246, 250))           # халат
    d.polygon([tuple(P(230, 300)), tuple(P(190, 420)), tuple(P(230, 470)), tuple(P(270, 420))], fill=(90, 110, 160))
    d.line(P(230, 470, 230, 760), fill=(200, 200, 210), width=5 * SS)
    oval(d, 230, 190, 120, 130, SKIN)
    d.chord(P(104, 56, 356, 210), 180, 360, fill=(140, 140, 150))
    for s in (-1, 1):
        oval(d, 230 + s * 48, 190, 36, 30, (220, 236, 255), INK, 6)
        if wink and s > 0:
            d.arc(P(230 + s * 48 - 18, 176, 230 + s * 48 + 18, 204), 200, 340, fill=INK, width=7 * SS)
        else:
            oval(d, 230 + s * 48, 192, 9, 10, INK, None)
    d.line(P(194, 190, 266, 190), fill=INK, width=5 * SS)
    oval(d, 230, 272, 50, 16, (150, 150, 160), None)               # усы
    d.arc(P(196, 268, 264, 300), 20, 160, fill=INK, width=6 * SS)
    return done(im)


@functools.lru_cache(4)
def iss_spr():
    im, d = canvas(360, 200)
    for x in (20, 250):
        for k in range(2):
            rrect(d, (x, 20 + k * 100, x + 90, 80 + k * 100), 4, (60, 90, 180))
            for g in range(1, 4):
                d.line(P(x + g * 22, 20 + k * 100, x + g * 22, 80 + k * 100), fill=(150, 180, 240), width=2 * SS)
    d.line(P(110, 100, 250, 100), fill=(200, 200, 210), width=10 * SS)
    rrect(d, (140, 74, 220, 126), 12, (230, 230, 236))
    return done(im)


def sky(t, alt):
    """Небо по высоте alt 0..1 (0 — земля, 1 — космос)."""
    top = mix((86, 170, 250), (6, 8, 30), cl(alt * 1.2))
    bot = mix((190, 230, 255), (30, 40, 110), cl(alt * 1.2))
    return grad_t(top, bot)


CLOUDS = [(random.Random(i).uniform(-100, W + 100), random.Random(i + 7).uniform(0, H),
           random.Random(i + 3).uniform(0.5, 1.3)) for i in range(10)]


@functools.lru_cache(8)
def cloud_spr(seed):
    return puff_spr(90, 100 + seed, False, (248, 250, 255))


def clouds(im, t, speed=900, alpha=1.0):
    for k, (x, y0, s) in enumerate(CLOUDS):
        y = (y0 + speed * s * t) % (H + 400) - 200
        put(im, cloud_spr(k % 4), x, y, s * 1.4, alpha=alpha * 0.92)


def speedlines(im, t, n=24, alpha=120, vertical=True, col=WHITE):
    d = ImageDraw.Draw(im)
    for k in range(n):
        rnd = random.Random(k)
        x = rnd.uniform(0, W)
        L = rnd.uniform(160, 420)
        y = (rnd.uniform(0, H) + t * rnd.uniform(2400, 3800)) % (H + L) - L
        if vertical:
            d.line((x, y, x, y + L), fill=col + (alpha,), width=rnd.choice((3, 4, 6)))
        else:
            d.line((y * W / H, x * H / W, y * W / H + L, x * H / W), fill=col + (alpha,), width=4)


STARS = [(random.Random(i).uniform(0, W), random.Random(i + 77).uniform(0, H), random.Random(i + 5).uniform(1.5, 4),
          random.Random(i + 6).uniform(0, 6.28)) for i in range(140)]


def stars(im, t, alpha=1.0):
    d = ImageDraw.Draw(im)
    for x, y, r, ph in STARS:
        a = int(255 * alpha * (0.55 + 0.45 * math.sin(t * 2 + ph)))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))


def gauge(im, cx, cy, r, val, vmax, title, unit, t, red_from=None):
    d = ImageDraw.Draw(im)
    d.ellipse((cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14), fill=INK)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(250, 250, 255))
    a0, a1 = 150, 390
    if red_from is not None:
        d.arc((cx - r + 18, cy - r + 18, cx + r - 18, cy + r - 18), a0 + (a1 - a0) * red_from / vmax, a1,
              fill=RED, width=22)
    for k in range(11):
        a = math.radians(a0 + (a1 - a0) * k / 10)
        d.line((cx + math.cos(a) * (r - 20), cy + math.sin(a) * (r - 20), cx + math.cos(a) * (r - 52),
                cy + math.sin(a) * (r - 52)), fill=INK, width=6)
    shake = 1.5 * noise(t * 2, 3) if val > vmax * 0.95 else 0
    a = math.radians(a0 + (a1 - a0) * min(1.02, val / vmax) + shake)
    d.line((cx, cy, cx + math.cos(a) * (r - 40), cy + math.sin(a) * (r - 40)), fill=RED, width=12)
    d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=INK)
    label(im, title, cx, cy + r * 0.42, int(r * 0.17), INK, 0)
    label(im, counter_text(val) + unit, cx, cy + r * 0.72, int(r * 0.26), INK, 0)


def bar(im, x, y, w, h, frac, col, text, val_text, t_alpha=1.0):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x, y, x + w, y + h), h // 2, fill=(255, 255, 255, 40), outline=WHITE + (120,), width=3)
    if frac > 0.005:
        d.rounded_rectangle((x, y, x + max(h, w * frac), y + h), h // 2, fill=col + (255,), outline=INK, width=5)
    spr = text_spr(text, 46, WHITE, 'Heavy', 5)
    put(im, spr, x, y - 40, anchor=(0, 0.5), alpha=t_alpha)
    if val_text:
        spr = text_spr(val_text, 52, YEL, 'Heavy', 6)
        put(im, spr, x + max(h, w * frac) + 16, y + h / 2, anchor=(0, 0.5), alpha=t_alpha)


def stamp(im, text, cx, cy, u, col=RED, size=96, rot=-12):
    if u <= 0:
        return
    s = 1 + 1.4 * (1 - eo(u / 0.18))
    a = cl(u / 0.1)
    spr = text_spr(text, size, col, 'Heavy', 0)
    box = Image.new('RGBA', (spr.size[0] + 60, spr.size[1] + 50), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((6, 6, box.size[0] - 6, box.size[1] - 6), 22, outline=col + (255,), width=10)
    box.alpha_composite(spr, (30, 25))
    put(im, box, cx, cy, s, rot, a)


def puff_wipe(im, u, dur=0.5):
    """Переход «облако газа»: облака закрывают кадр к u=0 и расходятся к u=dur. u — от момента смены сцены."""
    k = 1 - abs(u) / (dur / 2)
    if k <= 0:
        return
    k = sm(k)
    for i in range(14):
        rnd = random.Random(i)
        x, y = rnd.uniform(-80, W + 80), rnd.uniform(-80, H + 80)
        put(im, puff_spr(120, 300 + i % 5, False), x, y, 0.2 + 4.2 * k * rnd.uniform(0.7, 1.1), rnd.uniform(-20, 20))


# ------------------------------------------------------------------ субтитры
def _phrases():
    out = []
    for k, (key, spoken, screen, pause) in enumerate(LINES):
        wt = CAP.estimate_word_times(str(TAKES[k]), spoken, offset=ON[k])
        wt = CAP.align(wt, screen)
        acc = {w for w, _ in wt if any(ch.isdigit() for ch in w)}
        out.append(CAP.phrase(wt, accent=acc, end=END[k] + 0.15, hold=0.2))
    return out


CAPS = CAP.Captions(_phrases(), width=960, top=150, size=60, weight='Heavy', max_lines=2, stroke=6,
                    accent_color=YEL)


def draw_caps(im, t):
    lay = CAPS.layer(t)
    if lay:
        spr, x0, y0 = lay
        im.alpha_composite(spr, (x0, y0))


# ------------------------------------------------------------------ сцены
def sc01(t):
    """Хук: герой на стуле, газ рвётся наружу, вопрос «ВСЕ ПУКИ РАЗОМ?»."""
    u = t
    im = blueprint(t)
    bubbles(im, t)
    # большая плашка вопроса
    s = 1 + 0.03 * math.sin(t * 5)
    label(im, 'ВСЕ ПУКИ', 540, 470, 120, YEL, 10, s, -3 + 2 * math.sin(t * 2))
    label(im, 'ЗА ЖИЗНЬ', 540, 600, 120, WHITE, 10, s, 2 * math.sin(t * 2 + 1))
    label(im, '= РАЗОМ?!', 540, 730, 110, GAS, 10, s * (1 + 0.08 * max(0, math.sin(t * 9))), -2)
    # герой
    jitter = 4 * noise(t * 2, 1) if t > 2.0 else 0
    expr = 'shock' if t < 4.6 else 'smug'
    hero(im, 540 + jitter, 1360, 0.95, expr, talk_open(t, 'L01') if expr != 'shock' else 1, bob=3 * math.sin(t * 6))
    # газ пытается вырваться: облачка из-под стула
    for i in range(5):
        ph = (t * 0.9 + i / 5) % 1
        x = 540 + (i - 2) * 120 + 30 * math.sin(i * 3 + t)
        put(im, puff_spr(50, i, True), x, 1700 - ph * 160, 0.5 + 0.7 * ph, 10 * math.sin(t + i), alpha=1 - ph ** 2)
    # «давай посчитаем» — формулы
    v = t - (S['L01'] + 4.6)
    if v > 0:
        for i, f in enumerate(('14 × 365', '× 25 лет', '= ?')):
            uu = v - i * 0.18
            put(im, text_spr(f, 62, WHITE, 'Heavy', 6), 200 + i * 340, 880, pop(uu), -6 + i * 6, cl(uu / 0.15))
    return im


def sc02(t):
    u = t - S['L02']
    im = blueprint(t, (30, 40, 90), (60, 30, 90))
    # листок календаря
    panel(im, (90, 400, 520, 830))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((90, 400, 520, 510), 34, fill=RED, outline=INK, width=6)
    d.rectangle((96, 480, 514, 510), fill=RED)
    label(im, '1 ДЕНЬ', 305, 456, 64, WHITE, 0)
    label(im, '24 ч', 305, 640, 150, INK, 0)
    # счётчик
    n = int(cl((u - 0.3) / 2.5) * 14 + 0.999) if u > 0.3 else 0
    panel(im, (580, 400, 990, 830), (255, 236, 150, 245))
    label(im, f'×{n}', 785, 590, 200 if n < 10 else 180, INK, 0, 1 + 0.08 * bump_from(u, [0.3 + i * 2.5 / 14 for i in range(14)]))
    label(im, 'пуков', 785, 750, 64, INK, 0)
    # 14 облачков-пуков сеткой
    for i in range(14):
        ti = 0.3 + i * 2.5 / 14
        uu = u - ti
        r, c = divmod(i, 7)
        x, y = 135 + c * 135, 1020 + r * 190
        put(im, puff_spr(56, i, True), x, y + 8 * math.sin(t * 3 + i), pop(uu, 0.3) * 0.95, 8 * math.sin(t * 2 + i))
    hero(im, 540, 1620, 0.5, 'smug', talk_open(t, 'L02'), bob=2 * math.sin(t * 5))
    return im


def bump_from(u, times):
    v = 0.0
    for ti in times:
        x = u - ti
        if 0 <= x < 0.4:
            v = max(v, math.sin(x / 0.4 * math.pi) * (1 - x / 0.4))
    return v


def sc03(t):
    u = t - S['L03']
    dur = E['L03'] - S['L03']
    im = blueprint(t, (40, 30, 90), (70, 26, 80))
    # рой облачков растёт
    k = eio(u / (dur * 0.9))
    n = int(8 + 150 * k)
    for i in range(n):
        rnd = random.Random(i + 500)
        x, y = rnd.uniform(40, W - 40), rnd.uniform(380, 1880)
        put(im, puff_spr(40, i % 8, True), x + 12 * math.sin(t * 2 + i), y + 10 * math.cos(t * 2.3 + i),
            0.55 * pop(u - i * dur * 0.9 / 158, 0.25), 15 * math.sin(i))
    # годы
    years = int(cl(u / (dur * 0.6)) * 25 + 0.5)
    panel(im, (120, 420, 960, 640), (255, 255, 255, 240))
    label(im, f'{years} лет', 540, 530, 140, INK, 0)
    # большой счётчик
    v = 128000 * eio((u - 0.4) / (dur * 0.75))
    panel(im, (60, 760, 1020, 1060), (255, 214, 64, 250))
    label(im, counter_text(v), 540, 880, 190, INK, 0, 1 + 0.03 * math.sin(t * 20) * (1 - cl(u / dur)))
    label(im, 'пуков', 540, 1010, 70, INK, 0)
    if u > dur * 0.82:
        stamp(im, '≈ 128 000!', 540, 1250, u - dur * 0.82, RED, 110, -8)
    return im


def sc04(t):
    u = t - S['L04']
    dur = E['L04'] - S['L04']
    im = blueprint(t, (24, 40, 80), (40, 30, 70))
    v = 9000 * eio(u / 1.6)
    panel(im, (120, 390, 960, 620), (255, 255, 255, 240))
    label(im, counter_text(v, ' л'), 540, 480, 150, INK, 0)
    label(im, 'газа', 540, 582, 54, (120, 120, 140), 0, w='Bold')
    # шахта: два лифта
    fill = eio((u - 1.6) / (dur - 1.8))
    for i, x in enumerate((300, 780)):
        el = elevator_spr()
        put(im, el, x, 1220 + 6 * math.sin(t * 2 + i), 1.0)
        # уровень газа внутри кабины
        x0, x1 = x - 129, x + 129
        y1 = 1220 + 270 + 6 * math.sin(t * 2 + i)
        hgt = 500 * fill
        if hgt > 2:
            lay = Image.new('RGBA', (258, 520), (0, 0, 0, 0))
            dl = ImageDraw.Draw(lay)
            top = 520 - hgt
            pts = [(0, 520)] + [(xx, top + 10 * math.sin(xx / 30 + t * 6 + i)) for xx in range(0, 259, 12)] + [(258, 520)]
            dl.polygon(pts, fill=GAS + (235,))
            for b in range(8):
                rnd = random.Random(b + i * 10)
                by = 520 - ((t * rnd.uniform(60, 140) + rnd.uniform(0, 500)) % max(1, hgt))
                bx = rnd.uniform(20, 238)
                dl.ellipse((bx - 9, by - 9, bx + 9, by + 9), outline=GAS_L + (255,), width=3)
            im.alpha_composite(lay, (int(x0), int(y1 - 520)))
            if fill > 0.85:
                put(im, puff_spr(46, 3 + i, True), x, y1 - 470, pop(u - 1.6 - (dur - 1.8) * 0.85), 0)
        label(im, f'ЛИФТ {i + 1}', x, 1560, 50, WHITE, 5)
    hero(im, 540, 1790, 0.34, 'shock' if fill > 0.5 else 'calm', talk_open(t, 'L04'))
    if fill > 0.98:
        stamp(im, 'ДО ПОТОЛКА', 540, 1690, u - 1.6 - (dur - 1.8), RED, 80, 6)
    return im


def room(t, shake=0.0):
    im = grad_t((250, 214, 170), (226, 180, 140))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 120):
        d.rectangle((x, 0, x + 60, 1500), fill=(244, 204, 160, 255))
    d.rectangle((0, 1500, W, H), fill=(150, 98, 64))
    for y in range(1500, H, 70):
        d.line((0, y, W, y), fill=(130, 84, 54), width=4)
    # окно и картинка — чтобы комната не была пустой
    d.rounded_rectangle((90, 380, 400, 720), 20, fill=(150, 210, 255), outline=INK, width=8)
    d.line((245, 380, 245, 720), fill=INK, width=8)
    d.line((90, 550, 400, 550), fill=INK, width=8)
    d.rounded_rectangle((700, 420, 960, 640), 12, fill=(255, 248, 230), outline=INK, width=8)
    label(im, 'HOME', 830, 530, 58, RED, 0)
    # лампа
    d.line((540, 0, 540, 230), fill=INK, width=6)
    d.pieslice((440, 200, 640, 330), 180, 360, fill=(255, 220, 90), outline=INK, width=6)
    return im


def sc05(t):
    u = t - S['L05']
    im = room(t)
    # герой падает на стул на «садишься»
    land = 0.55
    if u < land:
        drop = (1 - eo(u / land)) * -900
    else:
        drop = -40 * math.exp(-8 * (u - land)) * math.sin((u - land) * 30)
    rumble = 0
    if u > 2.2:
        rumble = 6 * cl((u - 2.2) / 2) * noise(t * 3, 2)
    expr = 'calm' if u < 2.0 else ('shock' if u < 4.0 else 'scared')
    hero(im, 540 + rumble, 1300, 1.0, expr, talk_open(t, 'L05') if expr == 'calm' else 1,
         bob=drop if u < land + 1 else 0)
    if u < land + 0.4 and u > land:
        d = ImageDraw.Draw(im)
        for k in range(8):
            a = math.pi * (k / 7)
            r0 = 300 + 500 * (u - land)
            d.line((540 + math.cos(a) * r0, 1550 + math.sin(a) * -60, 540 + math.cos(a) * (r0 + 60),
                    1550 + math.sin(a) * -60), fill=INK, width=6)
    # секундомер «1 с»
    if u > 2.2:
        v = u - 2.2
        cx, cy = 230, 860
        d = ImageDraw.Draw(im)
        sc = pop(v)
        r = 120 * sc
        if r > 30:
            d.ellipse((cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10), fill=INK)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)
            d.rectangle((cx - 20 * sc, cy - r - 8 - 32 * sc, cx + 20 * sc, cy - r - 8), fill=INK)
            a = math.radians(-90 + 360 * cl(v / 1.0))
            d.pieslice((cx - r + 14, cy - r + 14, cx + r - 14, cy + r - 14), -90, -90 + 360 * cl(v / 1.0),
                       fill=GAS + (255,))
            d.line((cx, cy, cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8), fill=INK, width=8)
            label(im, '1 сек', cx, cy + r + 60, 58, WHITE, 6, sc)
    # монета для масштаба
    if u > 4.0:
        v = u - 4.0
        cx, cy = 840, 860
        sc = pop(v)
        d = ImageDraw.Draw(im)
        put(im, coin_spr(), cx, cy, sc)
        label(im, 'Ø ≈ 2,5 см', cx, cy + 140, 54, WHITE, 6, sc)
        # линия-указатель к сиденью
        if sc > 0.5:
            d.line((cx - 60, cy + 100, 640, 1290), fill=WHITE + (200,), width=5)
    return im


def sc06(t):
    u = t - S['L06']
    dur = E['L06'] - S['L06']
    im = blueprint(t, (20, 26, 60), (50, 30, 80))
    speedlines(im, t, 18, 50, vertical=False)
    v = 20 * eo(u / 1.4)
    gauge(im, 540, 700, 280, v, 22, 'скорость', ' км/с', t, red_from=15)
    # гонка: пуля против струи
    y1, y2 = 1230, 1480
    x_b = 120 + (u * 120) % 1100 if u > 3.2 else 120
    lane = ImageDraw.Draw(im)
    for yy in (y1, y2):
        lane.line((60, yy + 70, 1020, yy + 70), fill=WHITE + (60,), width=3)
    bar(im, 80, y1 + 10, 900, 44, 0.9 / 20 * cl((u - 3.2) / 0.6), (200, 200, 210), 'Винтовочная пуля', '≈ 0,9 км/с',
        cl((u - 3.2) / 0.3))
    bar(im, 80, y2 + 10, 900, 44, eo((u - 3.6) / 1.2), GAS, 'Твоя струя', '20 км/с', cl((u - 3.6) / 0.3))
    if u > 3.2:
        put(im, bullet_spr(), 880 + 20 * math.sin(t * 3), y1 - 34, 0.6)
    if u > 5.0:
        stamp(im, '×22', 830, 1720, u - 5.0, YEL, 130, -10)
    hero(im, 200, 1760, 0.32, 'smug', talk_open(t, 'L06'))
    return im


def sc07(t):
    u = t - S['L07']
    im = room(t)
    brk = 0.35
    x, y = 540, 1300
    # стул разлетается, герой зависает на струе
    if u < brk:
        sh = 10 * noise(t * 4, 5)
        hero(im, x + sh, y, 1.0, 'scared', 1, bob=0)
        return im
    v = u - brk
    rise = -60 * eo(v / 0.6) - 8 * math.sin(v * 4)
    jet(im, x, y + 60 + rise, 260 + 40 * math.sin(t * 9), 120, t)
    hero(im, x, y + rise, 1.0, 'shock', 1, chair=False)
    for k, (spr, px, py) in enumerate(chair_parts()):
        rnd = random.Random(k + 40)
        vx, vy = rnd.uniform(-900, 900), rnd.uniform(-900, -300)
        tx, ty = x + px + vx * v, y + py + vy * v + 1600 * v * v
        put(im, spr, tx, ty, 1.0, rnd.uniform(-400, 400) * v)
    # щепки
    d = ImageDraw.Draw(im)
    for k in range(26):
        rnd = random.Random(k)
        a = rnd.uniform(0, 2 * math.pi)
        sp = rnd.uniform(400, 1200)
        px, py = x + math.cos(a) * sp * v, y + 40 + math.sin(a) * sp * v + 1400 * v * v
        L = rnd.uniform(14, 34)
        d.line((px, py, px + L * math.cos(a + v * 9), py + L * math.sin(a + v * 9)), fill=WOOD_D, width=8)
    stamp(im, 'СТУЛ: ВСЁ', 540, 560, v - 0.3, RED, 110, -8)
    return im


def sc08(t):
    u = t - S['L08']
    dur = E['L08'] - S['L08']
    im = blueprint(t, (20, 34, 70), (34, 40, 90))
    # истребитель + сравнение тяги
    put(im, fighter_spr(), 300 + 20 * math.sin(t * 1.5), 520 + 10 * math.sin(t * 2), 1.0, 0)
    d = ImageDraw.Draw(im)
    for k in range(5):  # пламя форсажа сзади
        xx = 300 - 210 + 20 * math.sin(t * 1.5) - k * 26 - 10 * noise(t * 2, k)
        d.ellipse((xx - 26 + k * 4, 520 - 20 + k * 3, xx + 26 - k * 4, 520 + 20 - k * 3), fill=(255, 160 - k * 15, 60, 220))
    hero(im, 800, 600, 0.42, 'smug', talk_open(t, 'L08'), chair=False)
    jet(im, 800, 625, 120 + 20 * math.sin(t * 9), 50, t)
    bar(im, 80, 900, 880, 54, 0.62 * eo((u - 0.8) / 1.2), (190, 196, 210), 'Тяга истребителя', '', cl((u - 0.8) / 0.3))
    bar(im, 80, 1090, 880, 54, 0.8 * eo((u - 2.0) / 1.2), GAS, 'Тяга твоей струи', 'БОЛЬШЕ', cl((u - 2.0) / 0.3))
    # весы с 70 кг
    v = u - 4.6
    if v > 0:
        sc = pop(v)
        panel(im, (240, 1320, 840, 1760), (255, 255, 255, 240))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((330, 1600, 750, 1690), 20, fill=(200, 205, 215), outline=INK, width=6)
        d.rectangle((340, 1600, 740, 1610), fill=INK)
        put(im, text_spr(counter_text(70 * eo(v / 0.8), ' кг'), 120, INK, 'Heavy', 0), 540, 1430, sc)
        put(im, puff_spr(50, 2, True), 540, 1560, sc * 0.8)
    return im


def sc09(t):
    """Взлёт: дом снаружи, отсчёт на «Итак…», герой пробивает крышу."""
    u = t - S['L09']
    im = sky(t, 0)
    clouds(im, t, 20, 0.8)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1640, W, H), fill=(110, 180, 90))
    d.ellipse((-200, 1600, 600, 1760), fill=(120, 196, 100))
    d.ellipse((500, 1610, 1300, 1780), fill=(100, 170, 84))
    go = E['L09'] - S['L09'] - 0.7        # момент старта — на «взлетаешь!»
    shake = 14 * noise(t * 3, 7) * (cl((u - go + 0.8) / 0.8) if u < go + 1.2 else max(0, 1 - (u - go - 1.2)))
    put(im, house_spr(u > go), 540 + shake, 1350, 1.0)
    if u < go:
        # отсчёт и дрожащий газ из-под крыши
        n = 3 - int(u / max(0.3, go / 3))
        label(im, str(max(1, n)), 540, 760, 260, YEL, 14, 1 + 0.15 * math.sin(u * 20))
        for i in range(3):
            ph = (t * 1.5 + i / 3) % 1
            put(im, puff_spr(40, i, True), 540 + (i - 1) * 90, 1080 - ph * 120, 0.5 + ph * 0.5, alpha=1 - ph)
        return im
    v = u - go
    y = 1100 - 2600 * v * v - 600 * v
    jet(im, 540, y + 50, 1200, 150, t)
    hero(im, 540 + shake * 0.3, y, 0.6, 'shock', 1, chair=False)
    # куски крыши
    for k in range(12):
        rnd = random.Random(k + 80)
        vx, vy = rnd.uniform(-600, 600), rnd.uniform(-1500, -700)
        px, py = 540 + vx * v, 1150 + vy * v + 1800 * v * v
        d.polygon([(px, py), (px + 30, py + 8), (px + 18, py + 30)], fill=(200, 72, 62), outline=INK)
    label(im, 'ПУСК!', 540, 700, 170, YEL, 12, pop(v, 0.3), -6)
    return im


def sc10(t):
    """Перегрузка: крупный план лица, щёки плывут, G-метр до 290."""
    u = t - S['L10']
    dur = E['L10'] - S['L10']
    im = sky(t, 0.15 + 0.1 * cl(u / dur))
    speedlines(im, t, 36, 160)
    sq = 2 if u < 1.2 else 3
    jit = 6 * noise(t * 5, 9)
    jet(im, 330 + jit, 1470, 900, 140, t)
    hero(im, 330 + jit, 1400, 1.05, 'strain', 0, chair=False, squash=sq, head_dy=40 * math.sin(t * 22) * 0.2)
    g = 290 * eo(u / 2.2)
    gauge(im, 790, 760, 220, g, 300, 'перегрузка', ' g', t, red_from=9)
    # пилот, который «отключился» уже на 9
    v = u - 4.8
    if v > 0:
        sc = pop(v)
        panel(im, (600, 1120, 1020, 1640), (255, 255, 255, 240))
        put(im, pilot_spr(), 810, 1330, sc * 1.0, 6 * math.sin(t * 3))
        put(im, text_spr('ПИЛОТ', 52, INK, 'Heavy', 0), 810, 1530, sc)
        put(im, text_spr('отключился на 9 g', 36, RED, 'Heavy', 0), 810, 1590, sc)
        d = ImageDraw.Draw(im)
        for k in range(3):
            a = t * 3 + k * 2.1
            d.text((810 + math.cos(a) * 110, 1190 + math.sin(a) * 30), '★', font=font(40), fill=YEL, anchor='mm')
    return im


def sc11(t):
    """8 Махов, 1,5 км, всё ещё сидя."""
    u = t - S['L11']
    dur = E['L11'] - S['L11']
    alt = 0.25 + 0.15 * cl(u / dur)
    im = sky(t, alt)
    clouds(im, t, 2400, 0.9)
    speedlines(im, t, 28, 130)
    # конус ударной волны
    d = ImageDraw.Draw(im)
    x, y = 540 + 20 * math.sin(t * 1.3), 1000
    for k in range(3):
        off = k * 70 + (t * 300) % 70
        d.line((x, y - 420 + off, x - 520, y + 500 + off), fill=WHITE + (110 - k * 30,), width=8)
        d.line((x, y - 420 + off, x + 520, y + 500 + off), fill=WHITE + (110 - k * 30,), width=8)
    jet(im, x, y + 55, 900, 130, t)
    hero(im, x, y, 0.75, 'smug' if u > 5 else 'shock', talk_open(t, 'L11') if u > 5 else 1, chair=False)
    # приборы
    mach = 8 * eo(u / 1.5)
    panel(im, (50, 1380, 500, 1640), (20, 24, 40, 220), ol=WHITE, w=4)
    label(im, 'СКОРОСТЬ', 275, 1430, 40, (170, 180, 210), 0)
    label(im, f'{mach:.1f} М'.replace('.', ','), 275, 1540, 110, YEL, 0)
    km = 1.5 * eo(u / 2.5)
    panel(im, (580, 1380, 1030, 1640), (20, 24, 40, 220), ol=WHITE, w=4)
    label(im, 'ВЫСОТА', 805, 1430, 40, (170, 180, 210), 0)
    label(im, f'{km:.1f} км'.replace('.', ','), 805, 1540, 110, GAS, 0)
    if u > 5.0:
        stamp(im, 'ПОЗА: СИДЯ', 540, 1770, u - 5.0, YEL, 70, -4)
    return im


def sc12(t):
    """Обогнал звук собственного пердежа: буквы «ПУУУК» отстают."""
    u = t - S['L12']
    im = sky(t, 0.42)
    clouds(im, t, 2400, 0.8)
    speedlines(im, t, 28, 130)
    x, y = 540, 760
    jet(im, x, y + 45, 1300, 120, t)
    hero(im, x, y, 0.6, 'happy', talk_open(t, 'L12'), chair=False)
    # звуковая волна отстаёт
    gap = 260 + 340 * cl(u / 2.4)
    d = ImageDraw.Draw(im)
    for k in range(4):
        r = 120 + k * 60
        yy = y + gap + 140 + k * 40
        d.arc((x - r * 2, yy - r * 0.6, x + r * 2, yy + r * 0.6), 200, 340, fill=YEL + (220 - k * 40,), width=10)
    word = 'ПУ' + 'У' * min(6, 1 + int(u * 3)) + 'К'
    label(im, word, x, y + gap + 360, 120, YEL, 10, 1 + 0.05 * math.sin(t * 15), 4 * math.sin(t * 6))
    label(im, 'звук', 210, y + gap + 200, 46, WHITE, 5, alpha=cl(u / 0.4))
    label(im, 'ты', 820, y - 200, 56, WHITE, 6, alpha=cl(u / 0.4))
    return im


def sc13(t):
    """Траектория к МКС без воздуха."""
    u = t - S['L13']
    dur = E['L13'] - S['L13']
    im = sky(t, 0.9)
    stars(im, t)
    d = ImageDraw.Draw(im)
    # Земля
    d.ellipse((-900, 1450, W + 900, 3600), fill=(60, 130, 220))
    d.ellipse((-900, 1450, W + 900, 3600), outline=(140, 210, 255), width=30)
    d.ellipse((-600, 1520, 500, 1800), fill=(90, 170, 90))
    d.ellipse((560, 1500, 1500, 1760), fill=(90, 170, 90))
    # МКС
    put(im, iss_spr(), 790, 470 + 10 * math.sin(t), 0.9)
    label(im, 'МКС ~400 км', 790, 600, 54, WHITE, 6)
    # траектория
    pts = []
    k = eo(u / (dur * 0.8))
    for i in range(61):
        v = i / 60 * 0.92
        xx = 300 + 470 * v
        yy = 1450 - 920 * (1 - (1 - v) ** 2)
        pts.append((xx, yy))
    nshow = int(len(pts) * k)
    for i in range(0, nshow - 1, 2):
        d.line((pts[i], pts[i + 1]), fill=WHITE + (220,), width=7)
    if nshow > 1:
        hx, hy = pts[nshow - 1]
        put(im, puff_spr(40, 1, True), hx, hy, 0.6)
    if u > dur * 0.8:
        label(im, 'почти!', 640, 720, 70, YEL, 8, pop(u - dur * 0.8), -8)
    label(im, 'без воздуха', 300, 1300, 46, (200, 220, 255), 5, alpha=cl(u / 0.5))
    return im


def sc14(t):
    """Воздух есть — газы вспыхивают."""
    u = t - S['L14']
    dur = E['L14'] - S['L14']
    ign = 2.0
    f = cl((u - ign) / 0.6)
    im = sky(t, 0.45 + 0.1 * f)
    clouds(im, t, 2000, 0.6)
    speedlines(im, t, 30, 130)
    x, y = 540, 900
    jet(im, x, y + 55, 1100, 140, t, fire=f)
    # ореол трения
    if u > 0.4:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        r = 330 + 30 * math.sin(t * 20)
        a = int(140 * cl((u - 0.4) / 1.0))
        dl.ellipse((x - r, y - r - 140, x + r, y + r), fill=(255, 110, 40, a))
        if f > 0:
            for k in range(14):
                rnd = random.Random(k)
                ang = rnd.uniform(0, 2 * math.pi)
                rr = rnd.uniform(160, 320) * (1 + 0.15 * math.sin(t * 13 + k))
                dl.ellipse((x + math.cos(ang) * rr - 70, y - 60 + math.sin(ang) * rr - 70,
                            x + math.cos(ang) * rr + 70, y - 60 + math.sin(ang) * rr + 70),
                           fill=(255, 170 + rnd.randint(0, 60), 40, int(200 * f)))
        lay = lay.filter(ImageFilter.GaussianBlur(30))
        im.alpha_composite(lay)
    hero(im, x + 6 * noise(t * 4, 2) * f, y, 0.7, 'scared' if u > ign else 'shock', 1, chair=False, soot=0.6 * f)
    label(im, 'воздух', 200, 1500, 64, WHITE, 6, alpha=cl(u / 0.4) * (1 - f))
    d = ImageDraw.Draw(im)
    if u < ign:
        for k in range(8):   # струйки воздуха обтекают героя
            yy = (1700 - (t * 1600 + k * 200) % 1200)
            d.arc((x - 420, yy - 60, x + 420, yy + 300), 200, 340, fill=WHITE + (150,), width=6)
    if f > 0:
        stamp(im, 'ВСПЫШКА!', 540, 1640, u - ign, (255, 140, 40), 120, -6)
    return im


def sc15(t):
    """Падающая звезда и желание ребёнка."""
    u = t - S['L15']
    dur = E['L15'] - S['L15']
    im = grad_t((10, 14, 46), (60, 40, 110))
    stars(im, t)
    d = ImageDraw.Draw(im)
    # луна
    d.ellipse((800, 330, 960, 490), fill=(255, 244, 200))
    d.ellipse((770, 310, 920, 460), fill=(14, 18, 54))
    # звезда-герой летит по диагонали
    k = (u / dur)
    sx, sy = lerp(1150, -100, k), lerp(380, 1000, k)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for i in range(30):
        tt = i / 30
        dl.ellipse((sx + 520 * tt - 30 * (1 - tt), sy - 260 * tt - 30 * (1 - tt), sx + 520 * tt + 30 * (1 - tt),
                    sy - 260 * tt + 30 * (1 - tt)), fill=(255, 220, 120, int(200 * (1 - tt))))
    lay = lay.filter(ImageFilter.GaussianBlur(10))
    im.alpha_composite(lay)
    d.ellipse((sx - 26, sy - 26, sx + 26, sy + 26), fill=(255, 255, 230))
    hero(im, sx, sy + 6, 0.12, 'happy', 0, chair=False, soot=0.5)
    # холм, ребёнок
    d.ellipse((-300, 1450, 900, 2300), fill=(30, 50, 60))
    d.ellipse((500, 1550, 1500, 2300), fill=(24, 40, 52))
    put(im, kid_spr(), 330, 1340, 1.2)
    v = u - dur * 0.55
    if v > 0:
        sc = pop(v)
        panel(im, (470, 1020, 1010, 1260), (255, 255, 255, 240))
        put(im, text_spr('Хочу…', 70, INK, 'Heavy', 0), 740, 1090, sc)
        put(im, text_spr('чтобы я никогда', 44, (90, 90, 110), 'Bold', 0), 740, 1160, sc)
        put(im, text_spr('не пукал!', 44, (90, 90, 110), 'Bold', 0), 740, 1210, sc)
        for k in range(6):
            a = t * 2 + k
            d.text((330 + math.cos(a) * 120, 1170 + math.sin(a) * 50), '★', font=font(40), fill=YEL, anchor='mm')
    return im


def sc16(t):
    """Дом с дырой в крыше и запахом."""
    u = t - S['L16']
    im = grad_t((24, 28, 60), (60, 50, 90))
    stars(im, t, 0.6)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1640, W, H), fill=(40, 70, 50))
    put(im, house_spr(True), 540, 1330, 1.25)
    # зелёный «запах» из дыры
    for k in range(4):
        ph = (t * 0.4 + k / 4) % 1
        put(im, puff_spr(60, k, False, (150, 200, 90)), 540 + 60 * math.sin(t + k), 900 - ph * 500, 0.5 + ph,
            alpha=0.8 * (1 - ph))
    for k in range(3):   # волнистые линии запаха
        pts = [(400 + k * 140 + 20 * math.sin(yy / 30 + t * 4), yy) for yy in range(700, 1000, 10)]
        d.line(pts, fill=(170, 220, 100, 255), width=8)
    # мигалка
    c = (255, 60, 60) if int(t * 4) % 2 else (60, 120, 255)
    lay = Image.new('RGBA', (W, H), c + (40,))
    im.alpha_composite(lay)
    # лента
    d = ImageDraw.Draw(im)
    for k in range(2):
        y0 = 1600 + k * 120
        d.polygon([(0, y0), (W, y0 - 60), (W, y0 + 10), (0, y0 + 70)], fill=YEL, outline=INK)
        for xx in range(30, W, 360):
            label(im, 'НЕ ПЕРЕСЕКАТЬ', xx + 150, y0 + 5 - xx * 60 / W, 40, INK, 0, rot=3)
    # мухи
    for k in range(5):
        a = t * (3 + k) + k
        fx_, fy = 540 + math.cos(a) * (200 + k * 20), 900 + math.sin(a * 1.3) * 80
        d.ellipse((fx_ - 7, fy - 7, fx_ + 7, fy + 7), fill=INK)
        d.ellipse((fx_ - 14, fy - 14, fx_ - 2, fy - 4), fill=(255, 255, 255, 200))
    if u > 2.2:
        label(im, '…и запах', 760, 560, 80, GAS, 8, pop(u - 2.2), 6)
    return im


def sc17(t):
    """Судмедэксперт и заключение."""
    u = t - S['L17']
    dur = E['L17'] - S['L17']
    im = grad_t((220, 230, 240), (180, 196, 214))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 140):
        d.rectangle((x, 0, x + 4, 1400), fill=(200, 212, 226))
    d.rectangle((0, 1400, W, H), fill=(120, 130, 150))
    wink = u > dur - 1.6
    put(im, expert_spr(wink), 760, 1150 + 4 * math.sin(t * 2), 1.0)
    # бланк заключения
    sc = pop(u - 0.3)
    paper = Image.new('RGBA', (600, 760), (0, 0, 0, 0))
    dp = ImageDraw.Draw(paper)
    dp.rounded_rectangle((10, 10, 590, 750), 20, fill=(255, 255, 250), outline=INK, width=6)
    dp.text((300, 80), 'ЗАКЛЮЧЕНИЕ', font=font(52), fill=INK, anchor='mm')
    for k in range(7):
        dp.line((60, 160 + k * 40, 540 - (k % 3) * 60, 160 + k * 40), fill=(190, 190, 200), width=6)
    dp.text((60, 480), 'Причина смерти:', font=font(40, 'Bold'), fill=(90, 90, 110))
    put(im, paper, 330, 1050, sc, -4)
    reveal = S['L17'] + 2.0 - S['L17']
    stamp(im, 'ЕСТЕСТВЕННЫЕ', 330, 1250, u - reveal, RED, 62, -10)
    stamp(im, 'ПРИЧИНЫ', 330, 1340, u - reveal - 0.12, RED, 62, -10)
    # призрак героя улетает вверх с нимбом
    v = u - (dur - 2.0)
    if v > 0:
        gy = 900 - 260 * eo(v / 2.0)
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        hero(lay, 230, gy, 0.45, 'happy', 0, chair=False)
        a = np.asarray(lay).copy()
        a[..., 3] = (a[..., 3] * 0.6 * cl(v / 0.5)).astype(np.uint8)
        im.alpha_composite(Image.fromarray(a, 'RGBA'))
        d = ImageDraw.Draw(im)
        d.ellipse((230 - 60, gy - 250, 230 + 60, gy - 220), outline=YEL + (255,), width=8)
        label(im, 'технически — да', 540, 1640, 70, INK, 0, pop(v - 0.4), -3)
    return im


SCENES = [('L01', sc01), ('L02', sc02), ('L03', sc03), ('L04', sc04), ('L05', sc05), ('L06', sc06), ('L07', sc07),
          ('L08', sc08), ('L09', sc09), ('L10', sc10), ('L11', sc11), ('L12', sc12), ('L13', sc13), ('L14', sc14),
          ('L15', sc15), ('L16', sc16), ('L17', sc17)]
STARTS = [0.0] + [S[k] - 0.12 for k, _ in SCENES[1:]]
WIPES = {'L05', 'L09', 'L15', 'L16', 'L17'}          # смена места — переход облаком газа
CUTS = STARTS[1:]


def scene_index(t):
    i = 0
    for k, s in enumerate(STARTS):
        if t >= s:
            i = k
    return i


def render_at(t):
    i = scene_index(t)
    key, fn = SCENES[i]
    im = fn(t)
    u = t - STARTS[i]
    if i > 0 and key not in WIPES and u < 0.22:      # «удар» камеры на смене сцены
        s = 1 + 0.07 * (1 - eo(u / 0.22))
        w2, h2 = int(W / s), int(H / s)
        im = im.crop(((W - w2) // 2, (H - h2) // 2, (W - w2) // 2 + w2, (H - h2) // 2 + h2)).resize((W, H), Image.BILINEAR)
        if u < 0.06:
            im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(120 * (1 - u / 0.06)))))
    # переход облаком: закрываем конец прошлой сцены и открываем новую
    for k, s in enumerate(STARTS[1:], 1):
        if SCENES[k][0] in WIPES and abs(t - s) < 0.3:
            puff_wipe(im, t - s, 0.6)
    draw_caps(im, t)
    end = DUR - t
    if end < 0.8:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.8)))))
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
