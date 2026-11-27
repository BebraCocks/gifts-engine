"""Анимационные персонажи «Низшего» в нуарном стиле A (решение автора 2026-11-24: «анимация, а не комикс»).
Объём — ламберт по псевдонормали из поля расстояний + холодный контровой свет (как style_probes.style_A).
Лица — отдельные крупные риги: веки, зрачки, брови, рот рисуются каждый кадр поверх заранее затенённой головы.
Тяжёлые спрайты кешируются в build/anim_cache/*.png."""
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

CACHE = paths.build(HERE) / 'anim_cache'
LIGHT = np.array([-0.5, -0.6, 0.62])
RIM = np.array([90, 140, 220], np.float32)


def cached(name, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{name}.png'
    if p.is_file():
        return Image.open(p).convert('RGBA')
    im = fn()
    im.save(p)
    return im


def smooth_shade(m, light=LIGHT):
    """как sp.shade, но сглаживание зависит от размера формы — без шва по оси у широких фигур"""
    a = np.asarray(m, np.float32) / 255
    dist = ndimage.distance_transform_edt(a > 0.5)
    r = max(1.0, dist.max())
    h = np.sqrt(np.clip(dist / r, 0, 1))
    h = ndimage.gaussian_filter(h, max(6.0, r * 0.16))
    gy, gx = np.gradient(h)
    k = r * 0.9
    n = np.stack([-gx * k, -gy * k, 0.08 + h * 0.9], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    lam = np.clip((n * light).sum(-1), 0, 1) * 0.75 + 0.25
    return a, lam, n


def shade_rgba(m, color, light=LIGHT, amb=0.16, rim_k=1.0, size=None):
    """L-маска -> RGBA с объёмом и контровым светом"""
    a, lam, n = smooth_shade(m, light)
    rim = np.clip(n[..., 0] * 0.8 - n[..., 1] * 0.4, 0, 1) ** 3 * rim_k
    col = np.asarray(color, np.float32)[None, None] * (amb + 0.95 * lam[..., None]) + rim[..., None] * RIM
    return Image.fromarray(np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8), 'RGBA')


def big_mask(size, fn, ss=2):
    w, h = size
    m = Image.new('L', (w * ss, h * ss), 0)
    fn(ImageDraw.Draw(m), ss)
    return m.resize((w, h), Image.LANCZOS)


def stubble(im, box, n, col=(50, 38, 34, 110), seed=1, inside=None):
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        if inside is None or inside(x, y):
            d.point((x, y), fill=col)
    im.alpha_composite(lay)


# ------------------------------------------------------------------ Оди: тело лёжа, части по отдельности
def hero_parts():
    """отдельные затенённые спрайты частей в позе стоя (1080x1920); поворот и сборка — в render.py"""
    def make(name):
        P = sp.parts()
        return lambda: shade_rgba(P[name], sp.COLOR[name])
    out = {}
    for k in ('torso', 'neck', 'head', 'shorts', 'arm_l', 'arm_r', 'leg_l', 'leg_r', 'elbow'):
        out[k] = cached(f'hero_{k}', make(k))
    return out


def hero_details():
    """шрамы, номер, мышцы — отдельным слоем, чтобы не лежали на конечностях до «комплектации»"""
    def make():
        im = Image.new('RGBA', (sp.W, sp.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ink = (80, 46, 40, 170)
        d.arc((410, 880, 545, 990), 20, 160, fill=ink, width=3)
        d.arc((535, 880, 670, 990), 20, 160, fill=ink, width=3)
        for k in range(3):
            y = 1030 + k * 50
            d.line((500, y, 532, y + 4), fill=ink, width=2)
            d.line((548, y + 4, 580, y), fill=ink, width=2)
        d.text((600, 900), '11', font=sp.fnt('Oswald-700.ttf', 64), fill=(24, 22, 24, 235))
        for (x, y), r in (((352, 872), 32), ((728, 872), 32), ((462, 1340), 42), ((618, 1340), 42)):
            d.arc((x - r, y - r * 0.45, x + r, y + r * 0.45), 0, 180, fill=(150, 50, 50, 230), width=5)
        return im
    return cached('hero_details', make)


# ------------------------------------------------------------------ Оди: крупное лицо
FACE_W, FACE_H = 1080, 1500
HC = (540, 640)                     # центр головы
HRX, HRY = 300, 400


def face_inside(x, y):
    return ((x - HC[0]) / HRX) ** 2 + ((y - HC[1]) / HRY) ** 2 < 0.97


def hero_head_base():
    """затенённая голова с шеей и плечами, глазницами, носом и щетиной — без век, глаз и рта"""
    def make():
        def head(d, s):
            d.ellipse(((HC[0] - HRX) * s, (HC[1] - HRY) * s, (HC[0] + HRX) * s, (HC[1] + HRY) * s), fill=255)
            d.ellipse(((HC[0] - HRX - 40) * s, 560 * s, (HC[0] - HRX + 40) * s, 760 * s), fill=255)    # уши
            d.ellipse(((HC[0] + HRX - 40) * s, 560 * s, (HC[0] + HRX + 40) * s, 760 * s), fill=255)
        def neck(d, s):
            d.polygon([(x * s, y * s) for x, y in [(360, 900), (720, 900), (790, 1180), (1080, 1300), (1080, 1500),
                                                   (0, 1500), (0, 1300), (290, 1180)]], fill=255)
        im = Image.new('RGBA', (FACE_W, FACE_H), (0, 0, 0, 0))
        im.alpha_composite(shade_rgba(big_mask((FACE_W, FACE_H), neck), (190, 140, 112)))
        im.alpha_composite(shade_rgba(big_mask((FACE_W, FACE_H), head), (206, 158, 126)))
        sock = Image.new('RGBA', im.size, (0, 0, 0, 0))
        for cx in (430, 650):
            ImageDraw.Draw(sock).ellipse((cx - 100, 585, cx + 100, 690), fill=(60, 30, 24, 60))
        im.alpha_composite(sock.filter(ImageFilter.GaussianBlur(16)))
        im2 = im.copy()
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        ds.polygon([(540, 600), (500, 800), (470, 860), (520, 880), (560, 880), (610, 860)], fill=(70, 36, 28, 110))  # нос
        ds.ellipse((470, 850, 520, 880), fill=(40, 18, 16, 200))
        ds.ellipse((560, 850, 610, 880), fill=(40, 18, 16, 200))
        ds.line((540, 620, 520, 830), fill=(255, 220, 190, 70), width=14)                                    # спинка носа
        ds.ellipse((420, 960, 660, 1060), fill=(70, 40, 32, 60))                                              # подбородок
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        im2.alpha_composite(sh)
        stubble(im2, (240, 240, 840, 1040), 26000, seed=2,
                inside=lambda x, y: face_inside(x, y) and (y < 450 or y > 880 or x < 330 or x > 750))
        return im2
    return cached('hero_head', make)


SKIN_AT = {}


def draw_hero_face(im, open_=0.0, gaze=(0.0, 0.0), furrow=0.0, mouth=0.0, ox=0, oy=0):
    """веки (open_ 0..1), взгляд (-1..1), сведённые брови (0..1), приоткрытый рот (0..1)"""
    if not SKIN_AT:
        base = hero_head_base()
        for k, cx in enumerate((430, 650)):
            SKIN_AT[k] = tuple(int(v) for v in np.asarray(base.crop((cx - 40, 585, cx + 40, 612)))[..., :3].reshape(-1, 3).mean(0))
    for k, cx in enumerate((430 + ox, 650 + ox)):
        cy = 640 + oy
        ex, ey = 62, 26
        lidc = SKIN_AT.get(k, (170, 120, 94))
        eye = Image.new('L', im.size, 0)
        ImageDraw.Draw(eye).polygon([(cx - ex, cy), (cx - ex * 0.4, cy - ey), (cx + ex * 0.4, cy - ey), (cx + ex, cy),
                                     (cx + ex * 0.4, cy + ey * 0.8), (cx - ex * 0.4, cy + ey * 0.8)], fill=255)
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        if open_ > 0.05:
            dl.rectangle((cx - ex, cy - ey, cx + ex, cy + ey), fill=(218, 206, 196, 255))
            ix, iy = cx + gaze[0] * 28, cy + gaze[1] * 8 + 2
            dl.ellipse((ix - 24, iy - 24, ix + 24, iy + 24), fill=(70, 84, 80, 255))
            dl.ellipse((ix - 11, iy - 11, ix + 11, iy + 11), fill=(10, 10, 12, 255))
            dl.ellipse((ix - 12, iy - 15, ix - 4, iy - 7), fill=(255, 255, 255, 230))
        lid = cy - ey + (2 * ey) * (1 - open_)
        dl.rectangle((cx - ex - 2, cy - ey - 2, cx + ex + 2, lid), fill=lidc + (255,))
        dl.line((cx - ex, cy, cx - ex * 0.4, lid if open_ > 0.05 else cy, cx + ex * 0.4,
                 lid if open_ > 0.05 else cy, cx + ex, cy), fill=(52, 30, 24, 255), width=5, joint='curve')
        im.paste(lay.convert('RGB'), (0, 0), ImageChops.multiply(eye, lay.getchannel('A')))
        ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        d.arc((cx - ex - 10, cy - ey - 24, cx + ex + 10, cy + ey - 6), 200, 340, fill=(80, 46, 36, 120), width=5)
        inner = 548 + oy + 30 * furrow
        outer = 530 + oy - 6 * furrow
        if k == 0:
            pts = [(cx - 95, outer + 10), (cx - 20, outer - 8), (cx + 85, inner)]
        else:
            pts = [(cx - 85, inner), (cx + 20, outer - 8), (cx + 95, outer + 10)]
        d.line(pts, fill=(48, 30, 26), width=22, joint='curve')
        im.alpha_composite(ov)
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # рот
    my = 950 + oy
    if mouth > 0.05:
        h = 40 * mouth
        d.ellipse((470 + ox, my - h / 2, 610 + ox, my + h / 2 + 6), fill=(40, 12, 14))
    d.line((460 + ox, my + 4, 500 + ox, my - 4, 580 + ox, my - 4, 620 + ox, my + 6), fill=(70, 34, 30), width=8,
           joint='curve')
    d.line((480 + ox, my + 26, 600 + ox, my + 26), fill=(120, 70, 56, 120), width=6)
    im.alpha_composite(ov)


# ------------------------------------------------------------------ Йорка: крупно, наклоняется сверху
YW, YH = 1080, 1500
YC = (540, 600)


def yorka_base():
    """голова, стрижка, шея, плечи в майке, культя справа — затенено; лицо рисуется поверх"""
    def make():
        skin = (178, 124, 92)
        def head(d, s):
            d.ellipse(((YC[0] - 230) * s, (YC[1] - 300) * s, (YC[0] + 230) * s, (YC[1] + 300) * s), fill=255)
        def neck(d, s):
            d.polygon([(x * s, y * s) for x, y in [(430, 820), (650, 820), (680, 1000), (560, 1040), (520, 1040),
                                                   (400, 1000)]], fill=255)
        def shirt(d, s):
            d.polygon([(x * s, y * s) for x, y in sp.smooth_poly(
                [(540, 980), (760, 1010), (900, 1100), (960, 1500), (120, 1500), (180, 1100), (320, 1010)])], fill=255)
        def stump(d, s):
            d.ellipse((90 * s, 1040 * s, 260 * s, 1220 * s), fill=255)
        def hair(d, s):
            pts = [(300, 640), (300, 470), (340, 360), (420, 300), (540, 280), (660, 300), (740, 370), (780, 470),
                   (780, 640), (740, 520), (720, 560), (690, 470), (640, 520), (600, 440), (560, 500), (510, 430),
                   (470, 500), (430, 440), (380, 540), (350, 480)]
            d.polygon([(x * s, y * s) for x, y in pts], fill=255)
        im = Image.new('RGBA', (YW, YH), (0, 0, 0, 0))
        im.alpha_composite(shade_rgba(big_mask((YW, YH), stump), skin))
        im.alpha_composite(shade_rgba(big_mask((YW, YH), shirt), (78, 96, 84)))
        im.alpha_composite(shade_rgba(big_mask((YW, YH), neck), (160, 110, 80)))
        im.alpha_composite(shade_rgba(big_mask((YW, YH), head), skin))
        im.alpha_composite(shade_rgba(big_mask((YW, YH), hair), (44, 30, 24), amb=0.3))
        ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        ds.ellipse((380, 580, 500, 690), fill=(80, 40, 100, 170))                     # синяк под левым глазом
        ds.polygon([(540, 600), (515, 740), (500, 780), (580, 780)], fill=(70, 36, 28, 90))
        ds.ellipse((500, 760, 530, 782), fill=(40, 18, 16, 170))
        ds.ellipse((552, 760, 582, 782), fill=(40, 18, 16, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)))
        d.line((660, 680, 690, 760), fill=(110, 70, 54, 200), width=6)                # старый шрам на щеке
        d.line((420, 520, 600, 505), fill=(190, 50, 46, 230), width=8)                # свежий рубец на лбу
        d.text((620, 1080), '91', font=sp.fnt('Oswald-700.ttf', 70), fill=(20, 20, 22, 220))
        im.alpha_composite(ov)
        return im
    return cached('yorka_head', make)


def draw_yorka_face(im, mouth=0.0, blink=1.0, ox=0, oy=0):
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k, cx in enumerate((450 + ox, 630 + ox)):
        cy = 620 + oy
        if blink > 0.1:
            d.ellipse((cx - 44, cy - 22 * blink, cx + 44, cy + 22 * blink), fill=(230, 220, 212))
            d.ellipse((cx - 18, cy - 18 * blink, cx + 18, cy + 18 * blink), fill=(52, 34, 24))
            d.ellipse((cx - 8, cy - 8 * blink, cx + 8, cy + 8 * blink), fill=(6, 6, 8))
        d.line((cx - 50, cy - 22 * blink - 2, cx + 50, cy - 22 * blink - 2), fill=(30, 18, 14), width=7)
        d.line((cx - 60, cy - 70 + (10 if k == 0 else 26), cx + 55, cy - 70 + (26 if k == 0 else 10)),
               fill=(36, 22, 18), width=16)                                         # брови: злость, сведены
    my = 860 + oy
    h = 14 + 90 * mouth
    d.ellipse((480 + ox, my - h / 2, 600 + ox, my + h / 2), fill=(44, 10, 14), outline=(120, 50, 44), width=6)
    if mouth > 0.25:
        d.rectangle((500 + ox, my - h / 2 + 4, 580 + ox, my - h / 2 + 16), fill=(232, 226, 214))
    d.line((566 + ox, my - h / 2 - 2, 574 + ox, my - h / 2 + 14), fill=(180, 30, 30), width=4)   # разбитая губа
    im.alpha_composite(ov)


def yorka_arm():
    """вытянутая рука (её левая), тянется вниз к герою"""
    def make():
        m = Image.new('L', (900 * 2, 700 * 2), 0)
        dd = ImageDraw.Draw(m)
        S = 2
        for (a, b, ra, rb) in (((120, 120), (420, 360), 60, 48), ((420, 360), (720, 560), 48, 40)):
            ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
            pts = [(a[0] + ra * math.cos(ang), a[1] + ra * math.sin(ang)), (b[0] + rb * math.cos(ang), b[1] + rb * math.sin(ang)),
                   (b[0] - rb * math.cos(ang), b[1] - rb * math.sin(ang)), (a[0] - ra * math.cos(ang), a[1] - ra * math.sin(ang))]
            dd.polygon([(x * S, y * S) for x, y in pts], fill=255)
            dd.ellipse(((b[0] - rb) * S, (b[1] - rb) * S, (b[0] + rb) * S, (b[1] + rb) * S), fill=255)
        dd.ellipse((690 * S, 520 * S, 820 * S, 640 * S), fill=255)                   # кисть
        m = m.resize((900, 700), Image.LANCZOS)
        return shade_rgba(m, (150, 108, 84)).transpose(Image.FLIP_LEFT_RIGHT)
    return cached('yorka_arm', make)


# ------------------------------------------------------------------ фоны
def floor_noir():
    """мокрый стальной пол сверху, тёмный, с бликами и пятном света"""
    def make():
        w, h = 1500, 2400
        im = Image.new('RGB', (w, h), (40, 46, 52))
        d = ImageDraw.Draw(im)
        r = np.random.default_rng(5)
        for y in range(0, h, 300):
            for x in range(0, w, 350):
                c = 38 + int(r.integers(0, 12))
                d.rectangle((x + 4, y + 4, x + 346, y + 296), fill=(c, c + 5, c + 11), outline=(16, 18, 22), width=8)
                for px, py in ((x + 24, y + 24), (x + 326, y + 24), (x + 24, y + 276), (x + 326, y + 276)):
                    d.ellipse((px - 8, py - 8, px + 8, py + 8), fill=(70, 76, 84))
        d.rectangle((560, 1600, 940, 1800), fill=(12, 14, 16))
        for k in range(10):
            d.line((580 + k * 38, 1610, 580 + k * 38, 1790), fill=(50, 56, 62), width=8)
        a = np.asarray(im, np.float32)
        a += ndimage.gaussian_filter(r.random((h, w)), 2)[..., None] * 18 - 9
        wet = ndimage.gaussian_filter(r.random((h // 10, w // 10)), 4)
        wet = np.kron(wet, np.ones((10, 10)))[:h, :w]
        wet = np.clip((wet - 0.5) * 8, 0, 1)
        a = a * (1 - 0.3 * wet[..., None]) + wet[..., None] * np.array([40, 60, 80]) * 0.5
        yy, xx = np.mgrid[0:h, 0:w]
        light = np.exp(-(((xx - 750) / 520) ** 2 + ((yy - 1150) / 760) ** 2))
        a = a * (0.35 + 0.9 * light[..., None]) + light[..., None] * np.array([10, 18, 28])
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('floor_noir', make)


def ceiling_noir():
    """вид с пола вверх: потолок, длинные лампы в перспективе, рельс и полусфера"""
    def make():
        w, h = 1080, 1920
        yy, xx = np.mgrid[0:h, 0:w]
        a = np.zeros((h, w, 3), np.float32) + np.array([16, 20, 26])
        vp = (540, 300)
        im = Image.fromarray(a.astype(np.uint8))
        d = ImageDraw.Draw(im)
        for k in range(14):                                  # трубы и швы, сходятся к точке
            x = -400 + k * 140
            d.line((x, h, vp[0] + (x - vp[0]) * 0.08, vp[1]), fill=(34, 40, 48), width=18 if k % 3 == 0 else 6)
        for k in range(1, 9):
            f = (k / 9) ** 1.6
            y = h - (h - vp[1]) * f
            hw = 900 * (1 - f) + 40
            d.rectangle((vp[0] - hw * 0.35, y - 26 * (1 - f) - 3, vp[0] + hw * 0.35, y + 26 * (1 - f) + 3),
                        fill=(230, 240, 255))
        d.line((vp[0], vp[1], vp[0], h), fill=(60, 66, 76), width=24)
        d.chord((380, 1160, 700, 1480), 180, 360, fill=(28, 30, 36), outline=(80, 86, 96), width=6)
        for k in range(6):
            d.ellipse((420 + k * 46, 1300, 444 + k * 46, 1324), fill=(220, 50, 40))
        a = np.asarray(im, np.float32)
        glow = ndimage.gaussian_filter(a, (22, 22, 0))
        a = a + glow * 0.9
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('ceiling_noir', make)
