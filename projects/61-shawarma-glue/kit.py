"""Общие приёмы рисования ролика 60 (перенесены из 59-fart-rocket и доработаны): утилиты, герой, фоны, шкалы, субтитры."""
import functools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
import captions as CAP  # noqa: E402
from script import LINES  # noqa: E402
from timeline import DUR, ON, END, S, E, TAKES  # noqa: E402

W, H, FPS = 1080, 1920, 60
SS = 2

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
POO = (128, 82, 46)
POO_D = (92, 56, 30)
POO_L = (166, 112, 66)


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


