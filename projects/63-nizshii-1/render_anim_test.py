"""«Низший» 1/1 — первые ~19 с части 1. Анимация в нуарном стиле A (автор 2026-11-24: «анимация, а не комикс»,
из текста — только неброские субтитры внизу). Предыдущие версии: render_infographic_v1.py, render_comic_v1.py.

Сцены: (1) вид сверху — Оди лежит на мокром полу; система «гидрирует» тело (цвет возвращается), «комплектует»
(руки и ноги проявляются за зелёной линией сканера), «реанимирует» (тело вздрагивает на каждый удар сердца, начинается
дыхание); (2) крупно лицо: веки дрожат и открываются, взгляд мечется, брови сводятся; (3) взгляд с пола вверх —
Йорка нависает и трясёт его, губы двигаются по громкости её голоса; (4) взгляд вниз на свою грудь с номером 11,
к нему тянется старческая рука. Нуарная обработка: тёмный тил в тенях, виньетка, зерно.

    python -B projects/63-nizshii-1/render.py --frames 60,240,400,560,700,900,1100
    python -B engine/tools/build.py projects/63-nizshii-1 --approved --name nizshii_1_anim_v1
"""
import functools
import math
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops  # noqa: E402
import banner  # noqa: E402
import frames  # noqa: E402
import anim  # noqa: E402
from timeline_test import S, E, ON, END, KEYS, DUR, SC2, SC3, STAMP  # noqa: E402
from events_test import AD_STOPS, OK, BEATS, MEMORY_DRAIN, NAME_GLITCH, FACE_GLITCH, HEY  # noqa: E402

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks(AD_STOPS, cy=H / 2)
SC4 = STAMP - 0.15
SUBS = {'S1': 'Гидрация — успешно.', 'S2': 'Комплектация — успешно.', 'S3': 'Реанимация — успешно.',
        'O2': 'И я не помню ничего.', 'O3': 'Ни имени.', 'O4': 'Ни лица.',
        'Y1': '— Эй! Одиннадцатый! Очнись уже! Подъём!'}


def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(x):
    x = cl(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return cl((t - a) / (b - a)) if b > a else float(t >= a)


def bump(t, t0, rise=0.06, fall=0.35):
    v = t - t0
    if v < 0:
        return 0.0
    return min(1.0, v / rise) * math.exp(-max(0.0, v - rise) / fall)


def put(base, spr, cx, cy, a=1.0, scale=1.0, rot=0.0):
    if a <= 0.003:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05:
        spr = spr.rotate(rot, Image.BILINEAR, expand=True)
    if a < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * cl(a))))
    base.alpha_composite(spr, (int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))))


def cam(src, w, h, z, cx, cy, rot=0.0):
    """вырезать из src кадр w×h с центром (cx, cy), масштабом z и поворотом rot (градусы)"""
    a = math.radians(rot)
    c, s = math.cos(a) / z, math.sin(a) / z
    return src.transform((w, h), Image.AFFINE, (c, s, cx - c * w / 2 - s * h / 2, -s, c, cy + s * w / 2 - c * h / 2),
                         resample=Image.BILINEAR)


# ------------------------------------------------------------------ голос Йорки -> рот
@functools.lru_cache(None)
def envelope():
    with wave.open(str(HERE / 'voice' / 'clips' / 'Y1.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32).reshape(-1, 2).mean(1)
        sr = w.getframerate()
    hop = sr // 60
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    rms = np.convolve(rms, np.ones(3) / 3, 'same')
    return np.clip(rms / (np.percentile(rms, 90) + 1e-6), 0, 1.2)


def yorka_mouth(t):
    env = envelope()
    i = int((t - S['Y1']) * 60)
    return float(env[i]) if 0 <= i < len(env) else 0.0


# ------------------------------------------------------------------ сцена 1: тело на полу
CROP = (200, 500, 900, 1860)                   # область тела в координатах позы стоя


@functools.lru_cache(None)
def body_layers():
    P = anim.hero_parts()
    torso = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    for k in ('shorts', 'neck', 'torso', 'head'):
        torso.alpha_composite(P[k])
    torso.alpha_composite(anim.hero_details())
    # закрытые глаза и рот на маленькой голове
    d = ImageDraw.Draw(torso)
    for cx in (512, 568):
        d.arc((cx - 18, 664, cx + 18, 684), 20, 160, fill=(60, 34, 28), width=4)
    d.line((520, 742, 540, 739, 560, 742), fill=(80, 44, 36), width=4)
    gray = ImageEnhance.Brightness(ImageEnhance.Color(torso).enhance(0.15)).enhance(0.62)
    limbs = {}
    for k in ('arm_l', 'arm_r', 'leg_l', 'leg_r'):
        im = P[k].copy()
        if k == 'arm_r':
            im.alpha_composite(P['elbow'])
        limbs[k] = im
    return torso, gray, limbs


def scan_reveal(img, t0, t1, t, y0, y1):
    """проявление сверху вниз за зелёной линией сканера; возвращает RGBA"""
    u = eio(ramp(t, t0, t1))
    if u <= 0:
        return None
    ys = y0 + (y1 - y0) * u
    out = img.copy()
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, img.width, ys), fill=255)
    out.putalpha(Image.composite(img.getchannel('A'), Image.new('L', img.size, 0), m))
    if u < 1:
        a = img.getchannel('A').crop((0, int(ys) - 10, img.width, int(ys) + 10))
        line = Image.new('RGBA', a.size, (120, 255, 170, 255))
        line.putalpha(a)
        out.alpha_composite(line.filter(ImageFilter.GaussianBlur(3)), (0, int(ys) - 10))
        out.alpha_composite(line, (0, int(ys) - 10))
    return out


def body_at(t):
    torso, gray, limbs = body_layers()
    hyd = eio(ramp(t, S['S1'] + 0.2, OK['S1'] + 0.5))
    canvas = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    windows = {'arm_l': (0.05, 0.8, 840, 1390), 'arm_r': (0.35, 1.1, 840, 1390),
               'leg_l': (0.7, 1.5, 1290, 1850), 'leg_r': (0.95, 1.75, 1290, 1850)}
    for k, (a, b, y0, y1) in windows.items():
        im = scan_reveal(limbs[k], S['S2'] + a, S['S2'] + b, t, y0, y1)
        if im:
            canvas.alpha_composite(im)
    breath = 0.0 if t < BEATS[0] else 0.012 * (0.5 - 0.5 * math.cos(2 * math.pi * (t - BEATS[0]) / 2.4))
    tor = Image.blend(gray, torso, hyd) if hyd < 1 else torso
    if breath > 0:
        w2 = int(1080 * (1 + breath))
        tor = tor.resize((w2, 1920), Image.BILINEAR).crop(((w2 - 1080) // 2, 0, (w2 - 1080) // 2 + 1080, 1920))
    canvas.alpha_composite(tor)
    a_body = canvas.getchannel('A')
    fx = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    dfx = ImageDraw.Draw(fx)
    w_u = ramp(t, S['S1'] + 0.1, OK['S1'] + 0.7)                  # волна воды от головы к ногам
    if 0 < w_u < 1:
        y = 560 + 1300 * eio(w_u)
        for k in range(14):
            dfx.rectangle((0, y - k * 9, 1080, y - k * 9 + 9), fill=(120, 190, 255, int(150 * (1 - k / 14))))
    pulse = sum(bump(t, b, 0.05, 0.25) for b in BEATS)
    if pulse > 0.01:
        dfx.ellipse((470, 830, 650, 1010), fill=(255, 40, 40, int(170 * min(1, pulse))))
    if w_u > 0 or pulse > 0.01:
        fx = fx.filter(ImageFilter.GaussianBlur(10))
        fx.putalpha(ImageChops.multiply(fx.getchannel('A'), a_body))
        canvas.alpha_composite(fx)
    return canvas.crop(CROP)


@functools.lru_cache(None)
def floor_small():
    return anim.floor_noir()


def scene1(t):
    floor = floor_small()
    world = floor.copy()
    body = body_at(t)
    jolt = sum(bump(t, b, 0.04, 0.18) for b in BEATS)
    body = body.rotate(-58 + 2.5 * jolt, Image.BILINEAR, expand=True)
    sc = 0.82 * (1 + 0.03 * jolt)
    body = body.resize((int(body.width * sc), int(body.height * sc)), Image.BILINEAR)
    # мягкая тень тела на полу
    sh = Image.new('RGBA', body.size, (0, 0, 0, 0))
    sh.putalpha(body.getchannel('A').point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    world.alpha_composite(sh, (760 - body.width // 2 + 18, 1180 - body.height // 2 + 22))
    world.alpha_composite(body, (760 - body.width // 2, 1180 - body.height // 2 - int(10 * jolt)))
    rip = Image.new('RGBA', world.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(rip)
    for k in range(4):                                             # круги по воде вокруг тела
        v = (t - S['S1'] - k * 0.45) / 1.8
        if 0 < v < 1:
            r = 120 + 700 * eo(v)
            dr.ellipse((760 - r, 1180 - r * 0.62, 760 + r, 1180 + r * 0.62), outline=(150, 200, 255, int(120 * (1 - v))),
                       width=4)
    world.alpha_composite(rip.filter(ImageFilter.GaussianBlur(2)))
    u = eio(ramp(t, 0, SC2 + 0.5))
    z = 0.9 + 0.55 * u
    cx = 760 + 180 * u
    cy = 1180 - 300 * u
    return cam(world, W, H, z, cx, cy, rot=-6 + 10 * u)


# ------------------------------------------------------------------ сцена 2: лицо
def face_params(t):
    o = 0.0
    for a, b, lvl in ((7.55, 7.75, 0.25), (7.75, 7.95, -0.25), (8.1, 8.8, 0.65), (MEMORY_DRAIN - 0.4, MEMORY_DRAIN, 0.2),
                      (FACE_GLITCH - 0.2, FACE_GLITCH + 0.15, 0.25)):
        o += lvl * eio(ramp(t, a, b))
    for b in (9.85, 11.0, 12.2):                                   # моргания
        v = abs(t - b)
        if v < 0.09:
            o *= v / 0.09
    keys = [(7.0, 0.0), (8.8, -0.7), (9.5, 0.6), (10.2, -0.3), (10.9, 0.5), (FACE_GLITCH, 0.0), (13, 0.0)]
    gx = 0.0
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t < t1:
            gx = v0 + (v1 - v0) * eio((t - t0) / (t1 - t0) * 1.6)
    furrow = 0.25 + 0.5 * eio(ramp(t, NAME_GLITCH - 0.2, NAME_GLITCH + 0.3)) + 0.2 * eio(ramp(t, FACE_GLITCH, FACE_GLITCH + 0.3))
    mouth = 0.12 * eio(ramp(t, FACE_GLITCH, FACE_GLITCH + 0.3)) * (0.6 + 0.4 * math.sin(t * 23))
    return cl(o), (gx, 0.0), cl(furrow), max(0.0, mouth)


@functools.lru_cache(None)
def face_bg():
    f = anim.floor_noir().crop((200, 500, 1300, 2456)).resize((1080, 1920), Image.BILINEAR)
    return f.filter(ImageFilter.GaussianBlur(6))


def scene2(t):
    img = face_bg().copy()
    head = anim.hero_head_base().copy()
    o, g, fr, mo = face_params(t)
    anim.draw_hero_face(head, open_=o, gaze=g, furrow=fr, mouth=mo)
    br = 1 + 0.012 * math.sin(2 * math.pi * (t - SC2) / 3.2)
    shake = 0.0
    if t >= FACE_GLITCH:
        v = t - FACE_GLITCH
        shake = 4 * math.sin(v * 9) * math.exp(-v * 2)
    put(img, head, 540, 850, 1.0, 1.02 * br, rot=-8 + shake + 3 * math.sin(t * 0.4))
    u = eio(ramp(t, SC2, SC3))
    return cam(img, W, H, 1.0 + 0.12 * u, 540, 960 - 60 * u, rot=0)


# ------------------------------------------------------------------ сцена 3: Йорка сверху
@functools.lru_cache(None)
def halo():
    im = Image.new('RGBA', (900, 900), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((150, 150, 750, 750), fill=(170, 200, 255, 120))
    return im.filter(ImageFilter.GaussianBlur(120))


def scene3(t):
    img = anim.ceiling_noir().copy()
    u = eo(ramp(t, SC3 - 0.1, SC3 + 0.45))
    talking = S['Y1'] <= t < E['Y1']
    shake = math.sin(t * 2 * math.pi * 3.4) * (7 if talking else 0) + 10 * bump(t, HEY, 0.04, 0.3)
    yo = anim.yorka_base().copy()
    blink = 1.0
    for b in (14.6, 16.4):
        v = abs(t - b)
        if v < 0.08:
            blink = v / 0.08
    anim.draw_yorka_face(yo, mouth=yorka_mouth(t), blink=blink)
    put(img, halo(), 560, 600, 0.9 * u)
    rot = -14 + 3 * math.sin(t * 2 * math.pi * 1.7) * (1 if talking else 0.2)
    put(img, yo, 520 + 300 * (1 - u), 860 - 500 * (1 - u) + shake, u, 1.08, rot=rot)
    reach = 12 * math.sin(t * 2 * math.pi * 3.4) if talking else 0
    ax, ay = 716 + 260 * (1 - u), 1284 + 300 * (1 - u)
    put(img, anim.yorka_arm(), ax + shake * 2 + reach, ay + shake + reach * 0.6, u, 0.8, rot=4)
    return cam(img, W, H, 1.02 + 0.06 * eio(ramp(t, SC3, SC4)), 540 + shake * 0.6, 960 + shake * 0.4)


# ------------------------------------------------------------------ сцена 4: взгляд на грудь
@functools.lru_cache(None)
def chest():
    P = anim.hero_parts()
    full = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    for k in ('shorts', 'arm_l', 'arm_r', 'elbow', 'neck', 'torso'):
        full.alpha_composite(P[k])
    full.alpha_composite(anim.hero_details())
    c = full.crop((330, 800, 750, 1260)).resize((1260, 1380), Image.LANCZOS)
    bg = anim.floor_noir().crop((300, 700, 1200, 2300)).resize((1080, 1920), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
    bg.alpha_composite(c, (-90, 260))
    return bg


@functools.lru_cache(None)
def hand():
    """старческая рука: тонкое предплечье, кисть, пальцы тянутся вверх"""
    def draw(d, s):
        def cap(a, b, ra, rb):
            ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
            pts = [(a[0] + ra * math.cos(ang), a[1] + ra * math.sin(ang)), (b[0] + rb * math.cos(ang), b[1] + rb * math.sin(ang)),
                   (b[0] - rb * math.cos(ang), b[1] - rb * math.sin(ang)), (a[0] - ra * math.cos(ang), a[1] - ra * math.sin(ang))]
            d.polygon([(x * s, y * s) for x, y in pts], fill=255)
            for (x, y), r in ((a, ra), (b, rb)):
                d.ellipse(((x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s), fill=255)
        cap((210, 1200), (210, 520), 54, 46)                     # предплечье
        d.ellipse((130 * s, 300 * s, 300 * s, 540 * s), fill=255)  # ладонь
        for k, (x, top) in enumerate(((150, 120), (195, 80), (240, 95), (280, 150))):
            cap((x, 360), (x - 6 + k * 3, top), 22, 18)
        cap((140, 450), (70, 330), 24, 19)                       # большой палец
    m = anim.big_mask((420, 1260), draw)
    im = anim.shade_rgba(m, (196, 176, 152))
    d = ImageDraw.Draw(im)
    for y in (180, 250, 300):                                    # морщины на суставах
        d.line((140, y, 290, y - 6), fill=(130, 100, 80, 255), width=2)
    return im


def scene4(t):
    img = chest().copy()
    v = t - SC4
    u = eio(ramp(v, 0.3, 1.5))
    tremble = math.sin(t * 37) * 4
    put(img, hand(), 760 - 40 * u + tremble, 2300 - 900 * u, 1.0, 1.0, rot=-24 + 8 * u)
    return cam(img, W, H, 1.0 + 0.08 * eio(ramp(v, 0, 2)), 540, 960)


# ------------------------------------------------------------------ обработка, субтитры, монтаж
@functools.lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.46) / (H * 0.62)) ** 2
    return np.clip(1.05 - 0.8 * r, 0.18, 1.0)[..., None].astype(np.float32)


@functools.lru_cache(None)
def grain(k):
    g = np.random.default_rng(100 + k).normal(0, 7, (H // 2, W // 2)).astype(np.float32)
    return np.kron(g, np.ones((2, 2), np.float32))[..., None]


@functools.lru_cache(None)
def shaft():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.abs((xx - 760) * 0.92 + (yy - 0) * 0.38 - 120) / 260                   # наклонный луч сверху справа
    return (np.exp(-d ** 2) * np.clip(1 - yy / H * 0.9, 0, 1))[..., None].astype(np.float32) * np.array(
        [70, 95, 130], np.float32)


DUST = np.random.default_rng(4).random((90, 4))


def grade(im, t):
    a = np.asarray(im.convert('RGB'), np.float32)
    a = a + shaft() * (0.75 + 0.25 * math.sin(t * 1.7))
    for x0, y0, sp, sz in DUST:                                    # пылинки в луче
        x = int((x0 * W + math.sin(t * 0.6 + y0 * 9) * 30) % W)
        y = int((y0 * H - t * (14 + 30 * sp)) % H)
        r = 1 + int(sz * 2.5)
        a[max(0, y - r):y + r, max(0, x - r):x + r] += 40 * (0.4 + sp)
    lum = a.mean(-1, keepdims=True) / 255
    a = a + (1 - lum) * np.array([-8, 4, 14], np.float32)          # тил в тенях
    a = a * vignette() + grain(int(t * 24) % 8)
    return np.clip(a, 0, 255).astype(np.uint8)


@functools.lru_cache(None)
def sub_spr(text):
    f = ImageFont.truetype(str(paths.ROOT / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Semibold.otf'), 40) \
        if hasattr(paths, 'ROOT') else ImageFont.truetype(
            str(Path(__file__).resolve().parents[2] / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Semibold.otf'), 40)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 30
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - bb[0], 17 - bb[1]), text, font=f, fill=(0, 0, 0, 200))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(im).text((20 - bb[0], 15 - bb[1]), text, font=f, fill=(236, 236, 232, 225))
    return im


def subtitles(im, t):
    for k, key in enumerate(KEYS):
        t0, t1 = ON[k] - 0.05, END[k] + 0.2
        if t0 <= t < t1:
            a = ramp(t, t0, t0 + 0.12) * (1 - ramp(t, t1 - 0.15, t1))
            put(im, sub_spr(SUBS[key]), W / 2, 1360, a)


def mix(a, b, u):
    r = 10 * math.sin(math.pi * u)
    if r > 0.5:
        small = (W // 4, H // 4)
        a = a.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((W, H), Image.BILINEAR)
        b = b.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((W, H), Image.BILINEAR)
    return Image.blend(a, b, eio(u))


CUTS = [(SC2, scene1, scene2), (SC3, scene2, scene3), (SC4, scene3, scene4)]
SCENES = [(0, scene1), (SC2, scene2), (SC3, scene3), (SC4, scene4)]
X = 0.25


def render_at(t):
    im = None
    for c, a, b in CUTS:
        if c - X <= t < c + X:
            im = mix(a(t).convert('RGB'), b(t).convert('RGB'), (t - (c - X)) / (2 * X)).convert('RGBA')
    if im is None:
        fn = [f for s, f in SCENES if t >= s][-1]
        im = fn(t)
    out = Image.fromarray(grade(im, t)).convert('RGBA')
    if HEY <= t < HEY + 0.25:
        out.alpha_composite(Image.new('RGBA', (W, H), (255, 240, 230, int(70 * (1 - (t - HEY) / 0.25)))))
    subtitles(out, t)
    k = ramp(t, 0, 0.5) * (1 - ramp(t, DUR - 0.8, DUR))
    if k < 1:
        out.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - k)))))
    return np.asarray(out.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
