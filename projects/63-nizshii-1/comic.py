"""Персонажи и фоны «Низшего» в стиле графического романа (выбор агента 2026-11-24 по просьбе автора):
чёрный контур, светотень в 2–3 тона по карте нормалей, растр в тенях. Спрайты считаются один раз и кешируются в
build/comic_cache/*.png (их нет в Git: пересоздаются автоматически)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = Path(__file__).resolve().parent
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageChops  # noqa: E402
from scipy import ndimage  # noqa: E402
import style_probes as sp  # noqa: E402
from style_probes import W, H, SS, mask, capsule, smooth_poly, shade, fnt  # noqa: E402

CACHE = paths.build(HERE) / 'comic_cache'
INK = (0, 0, 0)
yy, xx = np.mgrid[0:H, 0:W]
DOTS = ((np.sin(xx * 0.45) * np.sin(yy * 0.45)) > 0.3).astype(np.float32)


def cached(name, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{name}.png'
    if p.is_file():
        return Image.open(p).convert('RGBA')
    im = fn()
    im.save(p)
    return im


def figure(P, order, colors, light=np.array([-0.7, -0.3, 0.65]), extra=None):
    rgb = np.zeros((H, W, 3), np.float32)
    al = np.zeros((H, W), np.float32)
    for k in order:
        m, lam, n = shade(P[k], light)
        base = np.asarray(colors[k], np.float32) * np.array([1.08, 1.0, 0.92])
        lv = np.where(lam > 0.62, 1.0, np.where(lam > 0.42, 0.74, 0.46))
        col = base[None, None] * lv[..., None]
        col = col * (1 - 0.35 * DOTS[..., None] * (lv[..., None] < 0.5))
        rgb = rgb * (1 - m[..., None]) + col * m[..., None]
        al = np.maximum(al, m)
        edge = np.clip(np.asarray(P[k].filter(ImageFilter.MaxFilter(7)), np.float32) / 255 - m, 0, 1)
        rgb *= (1 - edge[..., None])
        al = np.maximum(al, edge)
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al * 255]).astype(np.uint8), 'RGBA')
    if extra:
        extra(ImageDraw.Draw(im))
    return im


# ------------------------------------------------------------------ Оди
def hero_face(d, eyes):
    if eyes == 'half':
        sp.face(d, 'B')
        return
    d.line((496, 654, 522, 650, 532, 656), fill=INK, width=6, joint='curve')
    d.line((548, 656, 558, 650, 584, 654), fill=INK, width=6, joint='curve')
    for cx in (512, 568):
        d.arc((cx - 20, 660, cx + 20, 684), 20, 160, fill=INK, width=5)                  # закрытые веки
    d.line((540, 676, 534, 716, 546, 720), fill=INK, width=4)
    d.line((520, 742, 540, 738, 560, 742), fill=INK, width=5)


def hero(eyes='closed'):
    def make():
        P = sp.parts()
        return figure(P, sp.ORDER, sp.COLOR, extra=lambda d: (sp.details(d, 'B'), hero_face(d, eyes)))
    return cached(f'hero_{eyes}', make)


# ------------------------------------------------------------------ Йорка: смуглая, однорукая, чёрные ноги, синяки
def yorka():
    def make():
        P = {}
        P['torso'] = mask(lambda d: d.polygon([(x * SS, y * SS) for x, y in smooth_poly(
            [(540, 770), (640, 778), (668, 820), (650, 940), (618, 1010), (628, 1120), (540, 1130), (452, 1120),
             (462, 1010), (430, 940), (412, 820), (440, 778)])], fill=255))
        P['neck'] = mask(lambda d: capsule(d, (540, 690), (540, 780), 30, 36))
        P['head'] = mask(lambda d: d.ellipse((472 * SS, 520 * SS, 608 * SS, 708 * SS), fill=255))
        P['stump'] = mask(lambda d: d.ellipse((402 * SS, 784 * SS, 462 * SS, 850 * SS), fill=255))
        arm = [(652, 800), (700, 990), (716, 1170)]
        m1 = mask(lambda d: capsule(d, arm[0], arm[1], 28, 21))
        m2 = mask(lambda d: capsule(d, arm[1], arm[2], 21, 17))
        m3 = mask(lambda d: d.ellipse((694 * SS, 1160 * SS, 740 * SS, 1236 * SS), fill=255))
        P['arm'] = ImageChops.lighter(ImageChops.lighter(m1, m2), m3)
        P['shorts'] = mask(lambda d: d.polygon([(x * SS, y * SS) for x, y in smooth_poly(
            [(456, 1100), (540, 1110), (624, 1100), (636, 1240), (556, 1248), (540, 1210), (524, 1248), (444, 1240)])],
            fill=255))
        legs = []
        for x0 in (498, 582):
            a = mask(lambda d, x0=x0: capsule(d, (x0, 1220), (x0 - 4, 1470), 46, 32))
            b = mask(lambda d, x0=x0: capsule(d, (x0 - 4, 1470), (x0 - 6, 1700), 32, 22))
            c = mask(lambda d, x0=x0: d.ellipse(((x0 - 40) * SS, 1690 * SS, (x0 + 34) * SS, 1736 * SS), fill=255))
            legs.append(ImageChops.lighter(ImageChops.lighter(a, b), c))
        P['leg_l'], P['leg_r'] = legs
        P['hair'] = mask(lambda d: d.polygon([(x * SS, y * SS) for x, y in
                                               [(466, 640), (470, 560), (500, 520), (540, 508), (590, 516), (618, 556),
                                                (616, 640), (600, 600), (586, 618), (566, 584), (540, 600), (520, 574),
                                                (500, 606), (486, 586)]], fill=255))
        order = ['leg_l', 'leg_r', 'shorts', 'arm', 'stump', 'neck', 'torso', 'head', 'hair']
        skin = (178, 124, 92)
        colors = dict(leg_l=(58, 50, 50), leg_r=(58, 50, 50), shorts=(70, 74, 82), arm=(184, 150, 120), stump=skin,
                      neck=skin, torso=(92, 110, 96), head=skin, hair=(46, 32, 26))

        def extra(d):
            d.ellipse((512, 610, 552, 640), fill=(92, 60, 110))                       # подбитый левый глаз
            d.line((500, 602, 530, 598), fill=INK, width=6)                          # брови вниз — злость
            d.line((552, 598, 584, 606), fill=INK, width=6)
            for cx in (528, 570):
                d.ellipse((cx - 11, 618, cx + 11, 634), fill=(255, 255, 255), outline=INK, width=3)
                d.ellipse((cx - 5, 621, cx + 5, 631), fill=INK)
            d.line((546, 630, 540, 660, 552, 664), fill=INK, width=4)                # нос
            d.ellipse((520, 672, 568, 700), fill=(40, 10, 14), outline=INK, width=4)  # рот: кричит
            d.rectangle((526, 674, 562, 680), fill=(240, 236, 226))
            d.line((556, 672, 562, 690), fill=(170, 40, 40), width=3)               # разбитая губа
            d.line((496, 566, 584, 560), fill=(200, 50, 50), width=5)               # свежий рубец на лбу
            d.line((592, 640, 600, 676), fill=(120, 80, 60), width=4)               # старый шрам на щеке
            d.text((572, 772), '91', font=fnt('Oswald-700.ttf', 34), fill=(20, 20, 22))
            d.line((444, 790, 444, 850), fill=INK, width=0)
        return figure(P, order, colors, extra=extra)
    return cached('yorka', make)


# ------------------------------------------------------------------ фоны
def floor_top():
    """стальной пол сверху: плиты, заклёпки, решётка стока, лужи, растр"""
    def make():
        w, h = 1400, 2400
        im = Image.new('RGB', (w, h), (64, 72, 82))
        d = ImageDraw.Draw(im)
        r = np.random.default_rng(5)
        for y in range(0, h, 300):
            for x in range(0, w, 350):
                c = 60 + int(r.integers(0, 16))
                d.rectangle((x + 6, y + 6, x + 344, y + 294), fill=(c, c + 7, c + 16), outline=INK, width=6)
                for px, py in ((x + 24, y + 24), (x + 326, y + 24), (x + 24, y + 276), (x + 326, y + 276)):
                    d.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(110, 118, 128), outline=INK, width=2)
        d.rectangle((520, 1500, 900, 1700), fill=(20, 22, 26), outline=INK, width=8)       # решётка стока
        for k in range(10):
            d.line((540 + k * 38, 1510, 540 + k * 38, 1690), fill=(70, 76, 86), width=8)
        for cx, cy, rx, ry in ((300, 1900, 220, 90), (1050, 700, 180, 70), (820, 2150, 260, 80)):
            d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(84, 96, 110), outline=INK, width=4)   # лужи
            d.arc((cx - rx + 30, cy - ry + 14, cx + rx - 40, cy + ry - 20), 200, 320, fill=(190, 210, 230), width=5)
        a = np.asarray(im, np.float32)
        dots = ((np.sin(np.arange(w)[None] * 0.5) * np.sin(np.arange(h)[:, None] * 0.5)) > 0.45).astype(np.float32)
        a *= (1 - 0.25 * dots[..., None])
        yy2, xx2 = np.mgrid[0:h, 0:w]
        light = np.exp(-(((xx2 - 700) / 600) ** 2 + ((yy2 - 1100) / 800) ** 2))
        a = a * (0.45 + 0.75 * light[..., None]) + light[..., None] * np.array([0, 18, 6])
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('floor', make)


def corridor_bg():
    def make():
        im = Image.new('RGB', (W, H))
        sp.corridor(ImageDraw.Draw(im), ((70, 80, 92), (52, 60, 72), (40, 44, 52), (30, 34, 40), INK, (255, 240, 170)))
        a = np.asarray(im, np.float32) * (1 - 0.3 * DOTS[..., None])
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('corridor', make)


def action_bg(col=(214, 64, 40), col2=(255, 176, 60)):
    """фон крика: радиальный градиент и линии действия, как в комиксе"""
    def make():
        cx, cy = 760, 760
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / 1300
        a = np.array(col2)[None, None] * (1 - r[..., None]) + np.array(col)[None, None] * r[..., None]
        a *= (1 - 0.22 * DOTS[..., None])
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
        d = ImageDraw.Draw(im)
        rr = np.random.default_rng(9)
        for k in range(90):
            ang = rr.uniform(0, 2 * math.pi)
            r0 = rr.uniform(330, 520)
            wdt = rr.uniform(4, 16)
            x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
            x1, y1 = cx + 2400 * math.cos(ang), cy + 2400 * math.sin(ang)
            p = (-math.sin(ang) * wdt, math.cos(ang) * wdt)
            d.polygon([(x0, y0), (x1 + p[0], y1 + p[1]), (x1 - p[0], y1 - p[1])], fill=(20, 8, 6, 220))
        return im
    return cached('action', make)
