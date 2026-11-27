"""«Низший», книга 1, часть 1 «Пробуждение» — полная версия (~5:18). Анимация кодом в нуарном стиле A
(автор 2026-11-24/27: анимация, не комикс; из текста — только неброские субтитры в безопасной зоне).
Сцены идут по CLIPS (script.py): у каждой своё действие и движение камеры, смены — мягким размытием.
Персонажи: anim.py (Оди, Йорка, их лица и руки), anim2.py (силуэты, №444, места действия).

    python -B projects/63-nizshii-1/render.py --frames 300,1200,2400
    python -B engine/tools/build.py projects/63-nizshii-1 --approved --name nizshii_part1_v1
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
import anim2  # noqa: E402
from timeline import S, E, DUR, SCENES, SUBS, KEYS  # noqa: E402

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([], cy=H / 2)
ROOT = Path(__file__).resolve().parents[2]
F = HERE / 'fonts'
GREEN = (110, 255, 160)

# ключевые моменты внутри клипов (доли длины клипа — по слуху/паузам)
D = {k: E[k] - S[k] for k in KEYS}
OK = [S['A01'] + 1.15, S['A01'] + 3.55, S['A01'] + 6.0]          # три «успешно»
BEATS = [OK[2] + i * 0.55 for i in range(3)]


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
    if a <= 0.003 or spr is None:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05:
        spr = spr.rotate(rot, Image.BILINEAR, expand=True)
    if a < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * cl(a))))
    base.alpha_composite(spr, (int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))))


def cam(src, z, cx, cy, rot=0.0):
    a = math.radians(rot)
    c, s = math.cos(a) / z, math.sin(a) / z
    return src.transform((W, H), Image.AFFINE, (c, s, cx - c * W / 2 - s * H / 2, -s, c, cy + s * W / 2 - c * H / 2),
                         resample=Image.BILINEAR)


def kb(src, t, t0, t1, z0, z1, c0, c1, rot=(0, 0)):
    """плавный наезд/панорама между t0 и t1"""
    u = eio(ramp(t, t0, t1))
    return cam(src, z0 + (z1 - z0) * u, c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u,
               rot[0] + (rot[1] - rot[0]) * u)


def overlay(im, rgba):
    im.alpha_composite(Image.new('RGBA', im.size, rgba))


# ------------------------------------------------------------------ голос -> рот
@functools.lru_cache(None)
def envelope(key):
    with wave.open(str(HERE / 'voice' / 'clips' / f'{key}.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32).reshape(-1, 2).mean(1)
        sr = w.getframerate()
    hop = sr // 60
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    rms = np.convolve(rms, np.ones(3) / 3, 'same')
    return np.clip(rms / (np.percentile(rms, 90) + 1e-6), 0, 1.2)


def mouth(t, keys):
    for k in keys:
        if S[k] <= t < E[k]:
            env = envelope(k)
            i = int((t - S[k]) * 60)
            return float(env[i]) if 0 <= i < len(env) else 0.0
    return 0.0


def blink(t, times, d=0.09):
    for b in times:
        v = abs(t - b)
        if v < d:
            return v / d
    return 1.0


def auto_blinks(t0, t1, every=3.1):
    return [t0 + 1.2 + k * every + 0.4 * math.sin(k * 7) for k in range(int((t1 - t0) / every) + 1)]


# ------------------------------------------------------------------ Оди: тело на полу (сцена body)
CROP = (200, 500, 900, 1860)
ROT, BSC, BPOS = -58, 0.82, (760, 1180)


@functools.lru_cache(None)
def body_layers():
    P = anim.hero_parts()
    torso = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    for k in ('shorts', 'neck', 'torso', 'head'):
        torso.alpha_composite(P[k])
    torso.alpha_composite(anim.hero_details())
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
    u = eio(ramp(t, t0, t1))
    if u <= 0:
        return None
    if u >= 1:
        return img
    ys = y0 + (y1 - y0) * u
    out = img.copy()
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, img.width, ys), fill=255)
    out.putalpha(ImageChops.multiply(img.getchannel('A'), m))
    a = img.getchannel('A').crop((0, int(ys) - 10, img.width, int(ys) + 10))
    line = Image.new('RGBA', a.size, (120, 255, 170, 255))
    line.putalpha(a)
    out.alpha_composite(line, (0, int(ys) - 10))
    return out


def body_at(t):
    torso, gray, limbs = body_layers()
    hyd = eio(ramp(t, S['A01'] + 0.2, OK[0] + 0.5))
    canvas = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    s2 = OK[0] + 0.5
    windows = {'arm_l': (0.05, 0.8, 840, 1390), 'arm_r': (0.35, 1.1, 840, 1390),
               'leg_l': (0.7, 1.5, 1290, 1850), 'leg_r': (0.95, 1.75, 1290, 1850)}
    for k, (a, b, y0, y1) in windows.items():
        im = scan_reveal(limbs[k], s2 + a, s2 + b, t, y0, y1)
        if im:
            canvas.alpha_composite(im)
    breath = 0.0 if t < BEATS[0] else 0.012 * (0.5 - 0.5 * math.cos(2 * math.pi * (t - BEATS[0]) / 2.4))
    tor = Image.blend(gray, torso, hyd) if hyd < 1 else torso
    if breath > 0:
        w2 = int(1080 * (1 + breath))
        tor = tor.resize((w2, 1920), Image.BILINEAR).crop(((w2 - 1080) // 2, 0, (w2 - 1080) // 2 + 1080, 1920))
    canvas.alpha_composite(tor)
    fx = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
    dfx = ImageDraw.Draw(fx)
    on = False
    w_u = ramp(t, S['A01'] + 0.1, OK[0] + 0.7)
    if 0 < w_u < 1:
        y = 560 + 1300 * eio(w_u)
        for k in range(14):
            dfx.rectangle((0, y - k * 9, 1080, y - k * 9 + 9), fill=(120, 190, 255, int(150 * (1 - k / 14))))
        on = True
    pulse = sum(bump(t, b, 0.05, 0.25) for b in BEATS)
    if pulse > 0.01:
        dfx.ellipse((470, 830, 650, 1010), fill=(255, 40, 40, int(170 * min(1, pulse))))
        on = True
    throb = 0.5 + 0.5 * math.sin(t * 6) if t > S['A02'] + 3.0 else 0.0                       # горящий локоть
    if throb > 0:
        dfx.ellipse((720, 1030, 820, 1130), fill=(255, 60, 40, int(200 * throb)))
        on = True
    if on:
        fx = fx.filter(ImageFilter.GaussianBlur(10))
        fx.putalpha(ImageChops.multiply(fx.getchannel('A'), canvas.getchannel('A')))
        canvas.alpha_composite(fx)
    return canvas.crop(CROP)


def body_point(x, y, jolt=0.0):
    """точка позы стоя -> координаты мира пола"""
    cx, cy = (CROP[2] - CROP[0]) / 2, (CROP[3] - CROP[1]) / 2
    px, py = x - CROP[0] - cx, y - CROP[1] - cy
    a = math.radians(ROT + 2.5 * jolt)
    rx, ry = px * math.cos(a) + py * math.sin(a), -px * math.sin(a) + py * math.cos(a)
    sc = BSC * (1 + 0.03 * jolt)
    return BPOS[0] + rx * sc, BPOS[1] + ry * sc - 10 * jolt


def sc_body(t):
    world = anim.floor_noir().copy()
    body = body_at(t)
    jolt = sum(bump(t, b, 0.04, 0.18) for b in BEATS)
    body = body.rotate(ROT + 2.5 * jolt, Image.BILINEAR, expand=True)
    sc = BSC * (1 + 0.03 * jolt)
    body = body.resize((int(body.width * sc), int(body.height * sc)), Image.BILINEAR)
    sh = Image.new('RGBA', body.size, (0, 0, 0, 0))
    sh.putalpha(body.getchannel('A').point(lambda v: int(v * 0.55)))
    world.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)), (BPOS[0] - body.width // 2 + 18, BPOS[1] - body.height // 2 + 22))
    world.alpha_composite(body, (BPOS[0] - body.width // 2, BPOS[1] - body.height // 2 - int(10 * jolt)))
    rip = Image.new('RGBA', world.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(rip)
    for k in range(4):
        v = (t - S['A01'] - k * 0.45) / 1.8
        if 0 < v < 1:
            r = 120 + 700 * eo(v)
            dr.ellipse((760 - r, 1180 - r * 0.62, 760 + r, 1180 + r * 0.62), outline=(150, 200, 255, int(120 * (1 - v))), width=4)
    world.alpha_composite(rip)
    head = body_point(540, 660)
    elbow = body_point(770, 1080)
    # камера: общий план -> голова («очнулся») -> локоть («горел огнём») -> снова голова
    keys = [(0, 0.9, BPOS), (S['A02'], 1.2, BPOS), (S['A02'] + 2.0, 1.9, head), (S['A02'] + 4.0, 2.0, elbow),
            (S['A02'] + 6.6, 2.4, head), (S['A03'], 2.6, head)]
    z, c = keys[0][1], keys[0][2]
    for (t0, z0, c0), (t1, z1, c1) in zip(keys, keys[1:]):
        if t0 <= t < t1:
            u = eio((t - t0) / (t1 - t0))
            z, c = z0 + (z1 - z0) * u, (c0[0] + (c1[0] - c0[0]) * u, c0[1] + (c1[1] - c0[1]) * u)
        elif t >= t1:
            z, c = z1, c1
    im = cam(world, z, c[0], c[1], rot=-6 + 10 * eio(ramp(t, 0, S['A03'])))
    for k, tt in enumerate((S['A02'] + 3.2, S['A02'] + 3.9)):                     # вспышки боли
        b = bump(t, tt, 0.04, 0.3)
        if b > 0.01:
            overlay(im, (255, 255, 255, int(80 * b)))
    return im


# ------------------------------------------------------------------ лицо Оди (крупно)
@functools.lru_cache(None)
def face_bg(blur=6):
    f = anim.floor_noir().crop((200, 500, 1300, 2456)).resize((W, H), Image.BILINEAR)
    return f.filter(ImageFilter.GaussianBlur(blur))


def odi_face(t, open_, gaze, furrow, mo=0.0, y=850, scale=1.02, rot=-8, bg=None, extra=None):
    img = (bg or face_bg()).copy()
    head = anim.hero_head_base().copy()
    anim.draw_hero_face(head, open_=open_, gaze=gaze, furrow=furrow, mouth=mo)
    if extra:
        extra(head)
    br = 1 + 0.012 * math.sin(2 * math.pi * t / 3.2)
    put(img, head, 540, y, 1.0, scale * br, rot=rot + 2 * math.sin(t * 0.4))
    return img


def gaze_path(t, keys):
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t < t1:
            return v0 + (v1 - v0) * eio((t - t0) / (t1 - t0) * 1.6)
    return keys[-1][1]


def sc_face(t):
    s = S['A03']
    o = 0.25 * eio(ramp(t, s - 0.4, s - 0.2)) - 0.25 * eio(ramp(t, s - 0.2, s)) + 0.7 * eio(ramp(t, s + 0.1, s + 0.9))
    o += 0.3 * eio(ramp(t, s + D['A03'] * 0.75, s + D['A03'] * 0.85))
    o *= blink(t, [s + 2.3, s + 4.4])
    gx = gaze_path(t, [(s - 1, 0), (s + 1.2, -0.7), (s + 2.0, 0.6), (s + 2.9, -0.3), (s + 3.6, 0.5), (s + 4.6, 0)])
    fr = 0.25 + 0.5 * eio(ramp(t, s + D['A03'] * 0.5, s + D['A03'] * 0.6))
    img = odi_face(t, cl(o), (gx, 0), fr)
    return kb(img, t, s - 0.3, E['A03'] + 0.4, 1.0, 1.12, (540, 960), (540, 900))


# ------------------------------------------------------------------ Йорка
@functools.lru_cache(None)
def halo():
    im = Image.new('RGBA', (900, 900), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((150, 150, 750, 750), fill=(170, 200, 255, 120))
    return im.filter(ImageFilter.GaussianBlur(120))


def yorka_sprite(t, mo, keys_blink):
    yo = anim.yorka_base().copy()
    anim.draw_yorka_face(yo, mouth=mo, blink=blink(t, keys_blink))
    return yo


def sc_yorka_up(t):
    img = anim.ceiling_noir().copy()
    s = S['A04']
    u = eo(ramp(t, s - 0.35, s + 0.2))
    talking = s <= t < E['A04']
    shake = math.sin(t * 2 * math.pi * 3.4) * (7 if talking else 0) + 10 * bump(t, s + 0.06, 0.04, 0.3)
    yo = yorka_sprite(t, mouth(t, ['A04']), [s + 2.6])
    put(img, halo(), 560, 600, 0.9 * u)
    rot = -14 + 3 * math.sin(t * 2 * math.pi * 1.7) * (1 if talking else 0.2)
    put(img, yo, 520 + 300 * (1 - u), 860 - 500 * (1 - u) + shake, u, 1.08, rot=rot)
    reach = 12 * math.sin(t * 2 * math.pi * 3.4) if talking else 0
    put(img, anim.yorka_arm(), 716 + 260 * (1 - u) + shake * 2 + reach, 1284 + 300 * (1 - u) + shake + reach * 0.6, u, 0.8, rot=4)
    im = cam(img, 1.02 + 0.06 * eio(ramp(t, s, E['A04'])), 540 + shake * 0.6, 960 + shake * 0.4)
    if s + 0.06 <= t < s + 0.3:
        overlay(im, (255, 240, 230, int(70 * (1 - (t - s - 0.06) / 0.24))))
    return im


def sc_yorka_look(t):
    """Оди рассматривает её: камера скользит с лица на синяк, шрам, номер 91 и культю"""
    img = anim.ceiling_noir().copy()
    s = S['A05']
    yo = yorka_sprite(t, 0.0, auto_blinks(s, E['A05']))
    put(img, halo(), 560, 600, 0.9)
    put(img, yo, 520, 860 + 6 * math.sin(t * 1.4), 1.0, 1.08, rot=-14 + 2 * math.sin(t * 0.6))
    put(img, anim.yorka_arm(), 716, 1284, 1.0, 0.8, rot=4)
    return kb(img, t, s - 0.3, E['A05'] + 0.3, 1.5, 1.35, (470, 660), (480, 1180), rot=(4, -3))


def yorka_talk(t, keys, cut_odi=None):
    """Йорка говорит: губы по громкости, лёгкие кивки; фон — стена коридора в расфокусе"""
    img = corridor_soft().copy()
    bl = auto_blinks(S[keys[0]], E[keys[-1]], 2.7) if keys else auto_blinks(t - 5, t + 5, 2.7)
    yo = yorka_sprite(t, mouth(t, keys), bl)
    nod = 6 * math.sin(t * 2 * math.pi * 1.3) * (1 if mouth(t, keys) > 0.2 else 0.3)
    put(img, yo, 540, 900 + nod, 1.0, 1.0, rot=-4 + 2 * math.sin(t * 0.5))
    return img


@functools.lru_cache(None)
def corridor_soft():
    return anim2.corridor().filter(ImageFilter.GaussianBlur(9))


# ------------------------------------------------------------------ Оди смотрит на себя
@functools.lru_cache(None)
def chest():
    P = anim.hero_parts()
    full = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    for k in ('shorts', 'neck', 'torso'):
        full.alpha_composite(P[k])
    full.alpha_composite(anim.hero_details())
    c = full.crop((330, 800, 750, 1260)).resize((1260, 1380), Image.LANCZOS)
    bg = anim.floor_noir().crop((300, 700, 1200, 2300)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10))
    bg.alpha_composite(c, (-90, 260))
    return bg


@functools.lru_cache(None)
def hand(left=True, swollen=False):
    def draw(d, s):
        def cap(a, b, ra, rb):
            ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
            pts = [(a[0] + ra * math.cos(ang), a[1] + ra * math.sin(ang)), (b[0] + rb * math.cos(ang), b[1] + rb * math.sin(ang)),
                   (b[0] - rb * math.cos(ang), b[1] - rb * math.sin(ang)), (a[0] - ra * math.cos(ang), a[1] - ra * math.sin(ang))]
            d.polygon([(x * s, y * s) for x, y in pts], fill=255)
            for (x, y), r in ((a, ra), (b, rb)):
                d.ellipse(((x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s), fill=255)
        cap((210, 1200), (210, 520), 54, 46)
        d.ellipse((130 * s, 300 * s, 300 * s, 540 * s), fill=255)
        for k, (x, top) in enumerate(((150, 120), (195, 80), (240, 95), (280, 150))):
            cap((x, 360), (x - 6 + k * 3, top), 22, 18)
        cap((140, 450), (70, 330), 24, 19)
        if swollen:
            d.ellipse((120 * s, 1040 * s, 300 * s, 1220 * s), fill=255)
    m = anim.big_mask((420, 1260), draw)
    im = anim.shade_rgba(m, (196, 176, 152))
    d = ImageDraw.Draw(im)
    for y in (180, 250, 300):
        d.line((140, y, 290, y - 6), fill=(130, 100, 80, 255), width=2)
    if swollen:
        g = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((120, 1040, 300, 1220), fill=(150, 60, 110, 200))
        g.putalpha(ImageChops.multiply(g.getchannel('A'), im.getchannel('A')))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(6)))
    return im if left else im.transpose(Image.FLIP_LEFT_RIGHT)


def sc_self(t):
    s = S['A06']
    img = chest().copy()
    u1 = eio(ramp(t, s + D['A06'] * 0.35, s + D['A06'] * 0.5))       # «чужие руки» — руки поднимаются
    tremble = math.sin(t * 37) * 4
    put(img, hand(True), 300 + tremble, 2350 - 900 * u1, 1.0, 1.0, rot=12)
    put(img, hand(False, True), 800 - tremble, 2400 - 950 * u1, 1.0, 1.0, rot=-12)
    rise = 1 - eio(ramp(t, s - 0.3, s + 1.5))                            # она поднимает его — камера встаёт
    zf = 1.0 + 0.05 * eio(ramp(t, s, s + D['A06'] * 0.6))
    cy = 960 + 500 * rise
    if t > s + D['A06'] * 0.8:                                           # «локоть раздут» — наезд на локоть
        u = eio(ramp(t, s + D['A06'] * 0.8, s + D['A06'] * 0.9))
        return cam(img, zf + 0.9 * u, 540 + 230 * u, cy + 380 * u)
    return cam(img, zf, 540, cy)


# ------------------------------------------------------------------ коридор, толпа, полусфера
CROWD = [(-1, 0.96, 'c1', (True, False)), (1, 0.96, 'c2', (False, True)), (-1, 0.72, 'c3', (True, True)),
         (1, 0.70, 'c4', (True, True)), (-1, 0.52, 'c5', (False, True)), (1, 0.50, 'c6', (True, False)),
         (-1, 0.36, 'c7', (True, True)), (1, 0.35, 'c8', (True, True))]


@functools.lru_cache(None)
def crowd_spr(name, arms):
    return anim2.silhouette(name, arms=arms, body=(26 + hash(name) % 12, 30, 36), rim=1.4 + (hash(name) % 5) / 10)


def corridor_scene(t, sphere_u=None, straighten=0.0, extra=None):
    img = anim2.corridor().copy()
    for side, f, name, arms in sorted(CROWD, key=lambda c: c[1]):
        spr = crowd_spr(name, arms)
        sc = f * 0.72 * (1 + 0.04 * straighten)
        x = 540 + side * (130 + 330 * f ** 1.4)
        y = 860 + 640 * f ** 1.6
        sway = math.sin(t * 1.1 + f * 9) * 3 * (1 - straighten)
        put(img, spr, x + sway, y - spr.height * sc / 2, 1.0, sc, rot=side * 3 * (1 - straighten))
    if sphere_u is not None:
        u = sphere_u
        sc = 0.25 + 1.1 * u
        put(img, anim2.sphere(), 540, 300 + 260 * (1 - u) * 0 + 60 * u, 1.0, sc)
        if 0.2 < u < 1:                                                        # лазеры сканера
            lz = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lz)
            for k in range(5):
                x = 540 + math.sin(t * 3 + k * 1.3) * 420
                d.line((540, 360 + 60 * u, x, 1500), fill=(255, 60, 50, 90), width=3)
            img.alpha_composite(lz)
    if extra:
        extra(img)
    return img


def sc_corridor(t):
    s = S['A07']
    su = eio(ramp(t, s + D['A07'] * 0.25, s + D['A07'] * 0.75))
    st = eio(ramp(t, s + D['A07'] * 0.62, s + D['A07'] * 0.7))
    img = corridor_scene(t, su, st)
    return kb(img, t, s - 0.25, E['A07'] + 0.2, 1.0, 1.15, (540, 980), (540, 900))


@functools.lru_cache(None)
def glyphs():
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(str(F / 'JetBrainsMono-Bold.ttf'), 30)
    r = np.random.default_rng(2)
    for k in range(26):
        x, y = r.uniform(160, 880), r.uniform(300, 1300)
        d.text((x, y), ''.join(r.choice(list('01ОРНСОЛ#-:/')) for _ in range(int(r.uniform(4, 12)))), font=f,
               fill=GREEN + (150,))
    return im


def sc_scan(t):
    s = S['A08']
    img = corridor_soft().copy()
    put(img, anim2.sphere(), 540, 380, 1.0, 1.7 + 0.1 * math.sin(t))
    lz = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lz)
    for k in range(6):
        y = 700 + ((t - s) * 600 + k * 180) % 900
        d.line((140, y, 940, y), fill=(255, 70, 60, 120), width=4)
    img.alpha_composite(lz)
    a = eio(ramp(t, s + 0.6, s + 1.4))
    if a > 0:
        g = glyphs().copy()
        g.putalpha(g.getchannel('A').point(lambda v: int(v * a * (0.7 + 0.3 * math.sin(t * 20)))))
        img.alpha_composite(g)
    im = kb(img, t, s - 0.25, E['A08'] + 0.5, 1.0, 1.08, (540, 900), (540, 960))
    b = bump(t, s + D['A08'] * 0.8, 0.05, 0.4)
    if b > 0.01:
        overlay(im, (120, 255, 170, int(70 * b)))
    return im


# ------------------------------------------------------------------ ниша-кресло
def sc_niche(t):
    s = S['A09']
    if t >= S['B09'] - 0.3:                                              # Йорка объясняет про кубик
        img = yorka_talk(t, ['B09'])
        put(img, anim2.cube(), 300, 1180 + 8 * math.sin(t * 2), 1.0, 1.2, rot=20)
        return kb(img, t, S['B09'] - 0.3, E['B09'] + 0.3, 1.25, 1.35, (540, 820), (540, 860))
    img = anim2.niche().copy()
    d_ = D['A09']
    cups = [(s + 0.6, s + d_ * 0.18), (s + d_ * 0.18 + 0.4, s + d_ * 0.32)]
    for a, b in cups:
        if a - 0.3 < t < b + 0.3:
            u_in = eo(ramp(t, a - 0.3, a + 0.2))
            lvl = 1 - eio(ramp(t, a + 0.5, b - 0.2))
            put(img, anim2.cup(lvl), 310, 960 - 80 * u_in, u_in * (1 - ramp(t, b, b + 0.3)))
    for k in range(3):                                                    # три укола
        tt = s + d_ * (0.38 + k * 0.055)
        b = bump(t, tt, 0.03, 0.2)
        if b > 0.02:
            ng = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ng).line((540, 1300, 540 - 40 * k + 40, 1080), fill=(230, 240, 255, int(255 * b)), width=6)
            img.alpha_composite(ng)
    cu = eo(ramp(t, s + d_ * 0.55, s + d_ * 0.62))
    if cu > 0:
        put(img, anim2.cube(), 770, 980 - 70 * cu, cu, 1.0)
    jolt = sum(bump(t, s + d_ * (0.38 + k * 0.055), 0.03, 0.15) for k in range(3))
    im = kb(img, t, s - 0.25, E['A09'] + 0.4, 1.0, 1.18, (540, 960), (540, 1020))
    if jolt > 0.02:
        overlay(im, (255, 255, 255, int(60 * min(1, jolt))))
    return im


# ------------------------------------------------------------------ разговор с Йоркой
def sc_yorka_talk(t):
    if S['A11'] + D['A11'] * 0.35 <= t < S['A11'] + D['A11'] * 0.65:      # Оди слушает
        img = odi_face(t, 0.85 * blink(t, [S['A11'] + D['A11'] * 0.5]), (0.3, 0), 0.5, bg=corridor_soft(), y=900, rot=0)
        return kb(img, t, S['A11'] + D['A11'] * 0.35, S['A11'] + D['A11'] * 0.65, 1.15, 1.25, (540, 860), (540, 880))
    img = yorka_talk(t, ['A10', 'A11', 'A12'])
    z0 = 1.0 if t < S['A11'] else (1.2 if t < S['A12'] else 1.3)
    im = kb(img, t, S['A10'] - 0.25, E['A12'] + 0.5, z0, z0 + 0.12, (540, 900), (540, 860))
    dim = ramp(t, S['A12'] + D['A12'] * 0.6, E['A12'])                    # «Смерть» — свет гаснет
    if dim > 0:
        overlay(im, (0, 0, 0, int(140 * dim)))
    return im


def sc_slap(t):
    s = S['A13']
    hit = s + D['A13'] * 0.35
    if t < hit + 0.08:
        img = yorka_talk(t, [])
        sw = eio(ramp(t, hit - 0.35, hit))
        put(img, anim.yorka_arm(), 900 - 900 * sw, 1250 - 200 * sw, 1.0, 1.1, rot=30 - 50 * sw)
        return kb(img, t, s - 0.25, hit, 1.15, 1.25, (540, 860), (520, 880))
    red = (lambda h: h.alpha_composite(_cheek()))
    img = odi_face(t, 0.9 * blink(t, [hit + 2.0]), (0.0, 0), 0.95, bg=corridor_soft(), y=880, rot=4 + 10 * bump(t, hit, 0.03, 0.25),
                   extra=red)
    im = kb(img, t, hit, E['A13'] + 0.3, 1.25, 1.1, (560, 860), (540, 900))
    b = bump(t, hit, 0.02, 0.25)
    if b > 0.02:
        overlay(im, (255, 255, 255, int(160 * b)))
    return im


@functools.lru_cache(None)
def _cheek():
    g = Image.new('RGBA', (anim.FACE_W, anim.FACE_H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((640, 700, 820, 880), fill=(255, 40, 40, 110))
    g = g.filter(ImageFilter.GaussianBlur(30))
    g.putalpha(ImageChops.multiply(g.getchannel('A'), anim.hero_head_base().getchannel('A')))
    return g


def sc_leave(t):
    s = S['A14']
    img = anim2.corridor().copy()
    u = eio(ramp(t, s + D['A14'] * 0.5, E['A14'] + 0.6))
    spr = anim2.silhouette('yorka_walk', arms=(False, True), hair='spiky', body=(40, 36, 34), rim=1.8)
    bob = abs(math.sin(t * 5)) * 14 * (1 if u > 0 else 0)
    sc = 0.9 * (1 - 0.7 * u)
    put(img, spr, 540 + 40 * math.sin(t * 2.5) * u, 1500 - 600 * u - bob - spr.height * sc / 2 + 300, 1.0, sc,
        rot=3 * math.sin(t * 5) * (1 if u > 0 else 0))
    return kb(img, t, s - 0.25, E['A14'] + 0.5, 1.05, 1.15, (540, 980), (540, 900))


# ------------------------------------------------------------------ интерфейс в глазах
def hud_panel(lines, shown, w=760):
    f = ImageFont.truetype(str(F / 'JetBrainsMono-Bold.ttf'), 34)
    im = Image.new('RGBA', (w, 90 + 70 * len(lines)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, im.height - 1), fill=(4, 18, 10, 150), outline=GREEN + (200,), width=3)
    for k, (txt, col) in enumerate(lines):
        if k < shown:
            d.text((30, 40 + 70 * k), txt, font=f, fill=col + (235,))
    return im


def sc_menu(t):
    s = S['A15']
    img = corridor_soft().copy()
    overlay(img, (0, 0, 0, 90))
    lines = [('СТАТУС: НИЗШИЙ · ОРН', GREEN), ('БАЛАНС: 0', GREEN), ('ДОЛГ: 8 СОЛОВ', (255, 110, 90)),
             ('ЗАДАНИЕ: СЕРАЯ СЛИЗЬ', GREEN), ('40 ВЁДЕР → 15 СОЛОВ', GREEN)]
    shown = 1 + int(ramp(t, s + 0.4, s + D['A15'] * 0.8) * 4.99)
    a = eo(ramp(t, s - 0.2, s + 0.4)) * (0.85 + 0.15 * math.sin(t * 13))
    put(img, hud_panel(lines, shown), 540, 820, a)
    return kb(img, t, s - 0.25, E['A15'] + 0.3, 1.0, 1.05, (540, 960), (540, 940))


def sc_odin(t):
    s = S['A16']
    rise = eio(ramp(t, s, E['A16']))
    img = odi_face(t, 1.0 * blink(t, [s + 1.0]), (0, 0), 0.85, bg=corridor_soft(), y=880, rot=0)
    lt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lt).ellipse((140, 1100 - 500 * rise, 940, 1900 - 500 * rise), fill=(255, 200, 140, int(70 * rise)))
    img.alpha_composite(lt.filter(ImageFilter.GaussianBlur(90)))
    im = kb(img, t, s - 0.25, E['A16'] + 0.5, 1.1, 1.45, (540, 900), (540, 760))
    b = bump(t, s + D['A16'] * 0.38, 0.05, 0.4)
    if b > 0.02:
        overlay(im, (255, 255, 255, int(60 * b)))
    return im


# ------------------------------------------------------------------ игровой вызов
def screen_scene(t, scr, bully=0.0, woman=None):
    img = anim2.corridor().copy()
    put(img, scr, 540, 760, 1.0, 1.05)
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse((140, 380, 940, 1140), fill=(255, 200, 120, 40))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(80)))
    for k, (x, name) in enumerate(((240, 'c3'), (860, 'c4'))):
        spr = crowd_spr(name, (True, True))
        put(img, spr, x, 1500 - spr.height * 0.45 + 300, 1.0, 0.95)
    if bully > 0:
        spr = anim2.silhouette('bully58', wide=1.3, body=(22, 22, 26), rim=2.0)
        put(img, spr, 980 - 260 * bully, 1250, 1.0, 1.25, rot=10 * bully)
    if woman is not None:
        spr = anim2.silhouette('woman', hair='long', body=(34, 30, 34), rim=1.6)
        bob = abs(math.sin(t * 3.2)) * 18
        put(img, spr, -100 + 1300 * woman, 1380 - bob, 1.0, 0.9, rot=4 * math.sin(t * 3.2))
    return img


def sc_screen(t):
    s = S['A17']
    on = eio(ramp(t, s - 0.2, s + 0.3))
    timer = max(0, 59 - int((t - s) * 1.0))
    scr = anim2.wall_screen(on, text=[('11', 190), (f'ИГРОВОЙ ВЫЗОВ · 0:{timer:02d}', 48)])
    img = screen_scene(t, scr)
    return kb(img, t, s - 0.25, E['A17'] + 0.3, 1.0, 1.15, (540, 960), (540, 820))


def sc_game(t):
    s = S['A18']
    d_ = D['A18']
    push = ramp(t, s, s + 0.4) * (1 - ramp(t, s + 1.6, s + 2.4))
    moves = [4, 1, 6, 0, 2, 3, 8]
    seq = [(c, 'X' if k % 2 == 0 else 'O') for k, c in enumerate(moves)]
    n = int(ramp(t, s + d_ * 0.3, s + d_ * 0.55) * len(seq))
    if t < s + d_ * 0.6:
        scr = anim2.wall_screen(1.0, grid=seq[:n])
    elif t < s + d_ * 0.8:
        scr = anim2.wall_screen(1.0, text=[('ПОБЕДА', 140), ('+3 СОЛА', 80)], col=(120, 255, 160))
    else:
        scr = anim2.wall_screen(1.0, text=[('ДОЛГ', 140), ('−3 СОЛА', 80)], col=(255, 110, 90))
    woman = ramp(t, S['B18'] - 0.5, E['B18'] + 0.8) if t > S['B18'] - 0.5 else None
    img = screen_scene(t, scr, bully=eio(push), woman=woman)
    sh = 18 * bump(t, s + 0.3, 0.05, 0.3)
    im = kb(img, t, s - 0.25, E['B18'] + 0.4, 1.12, 1.0, (540 + sh, 820), (540, 960))
    return im


# ------------------------------------------------------------------ слизь
@functools.lru_cache(None)
def drips():
    im = Image.new('RGBA', (W, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(12)
    for k in range(40):
        x = r.uniform(0, W)
        y = r.uniform(0, 2 * H)
        d.ellipse((x - 9, y - 22, x + 9, y + 22), fill=(150, 154, 150, 170))
    return im


def slime_scene(t, workers=True, bucket_lvl=None):
    img = anim2.slime_room().copy()
    off = int((t * 60) % H)
    dr = drips().crop((0, H - off, W, 2 * H - off))
    img.alpha_composite(dr)
    if workers:
        for k in range(3):
            u = ((t * 0.07 + k * 0.37) % 1)
            spr = crowd_spr(f'c{5 + k}', (True, True))
            x = -200 + 1480 * u if k % 2 == 0 else 1280 - 1480 * u
            bob = abs(math.sin(t * 4 + k)) * 12
            put(img, spr, x, 1100 + k * 120 - bob, 1.0, 0.7 + 0.12 * k)
            put(img, anim2.bucket(), x + 90, 1350 + k * 140 - bob, 1.0, 0.45 + 0.08 * k)
    if bucket_lvl is not None:
        b = anim2.bucket().copy()
        dd = ImageDraw.Draw(b)
        dd.ellipse((30, 50, 210, 86), fill=(120, 124, 118, 255))
        put(img, b, 540, 1300, 1.0, 1.6)
        hh = int(140 * bucket_lvl)
        g = Image.new('RGBA', (300, 300), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((80, 220 - hh, 220, 230), 30, fill=(140, 144, 138, 255))
        put(img, g, 540, 1010, 1.0, 1.0)
    return img


def sc_slime(t):
    s = S['A19']
    if t >= S['B19'] - 0.3:
        img = slime_scene(t, workers=False, bucket_lvl=ramp(t, S['B19'], E['B19']))
        return kb(img, t, S['B19'] - 0.3, E['B19'] + 0.4, 1.0, 1.2, (540, 1100), (540, 1150))
    img = slime_scene(t)
    im = kb(img, t, s - 0.25, E['A19'] + 0.3, 1.0, 1.12, (540, 900), (600, 960))
    return im


def sc_kick(t):
    s = S['A20']
    d_ = D['A20']
    if t < s + d_ * 0.55:
        img = slime_scene(t, workers=False)
        u = eio(ramp(t, s - 0.2, s + d_ * 0.3))
        bars = anim2.silhouette('bars', wide=1.3, body=(30, 28, 30), rim=1.8)
        buksa = anim2.silhouette('buksa', hair='spiky', body=(46, 34, 40), rim=1.8)
        put(img, bars, 1300 - 700 * u, 1150, 1.0, 1.05)
        put(img, buksa, 1500 - 700 * u, 1220, 1.0, 0.85)
        kick = s + d_ * 0.28
        v = t - kick
        if v < 0:
            put(img, anim2.bucket(), 420, 1480, 1.0, 1.0)
        else:
            put(img, anim2.bucket(), 420 - 500 * v, 1480 - 600 * v + 900 * v * v, 1.0, 1.0, rot=360 * v)
            sp = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            dd = ImageDraw.Draw(sp)
            r = np.random.default_rng(5)
            for k in range(26):
                ang = r.uniform(math.pi, 2 * math.pi)
                sp_ = r.uniform(300, 900)
                x = 420 + math.cos(ang) * sp_ * v
                y = 1480 + math.sin(ang) * sp_ * v + 800 * v * v
                rr = r.uniform(8, 22)
                dd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(150, 154, 148, int(230 * max(0, 1 - v))))
            img.alpha_composite(sp)
        return kb(img, t, s - 0.25, s + d_ * 0.55, 1.0, 1.1, (540, 1000), (500, 1100))
    # душ
    img = corridor_soft().copy()
    spr = anim2.silhouette('odi_back', body=(40, 38, 40), rim=1.5)
    put(img, spr, 540, 1150, 1.0, 0.85)
    wr = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(wr)
    r = np.random.default_rng(int(t * 30))
    for k in range(90):
        x = r.uniform(240, 840)
        y = r.uniform(0, H)
        d.line((x, y, x - 6, y + 60), fill=(170, 200, 230, 120), width=3)
    img.alpha_composite(wr)
    return kb(img, t, s + d_ * 0.55, E['A20'] + 0.4, 1.0, 1.1, (540, 960), (540, 1000))


# ------------------------------------------------------------------ №444
def p444_face(t, keys, red=0.0):
    img = corridor_soft().copy()
    head = anim2.head444().copy()
    mo = mouth(t, keys)
    anim.draw_hero_face(head, open_=0.75 * blink(t, auto_blinks(S[keys[0]], E[keys[-1]], 2.5)),
                        gaze=(0.5 * math.sin(t * 1.3), 0), furrow=0.7, mouth=0.0)
    b, dy = anim2.beard(mo)
    head.alpha_composite(b, (0, dy))
    put(img, head, 540, 880, 1.0, 0.95, rot=3 * math.sin(t * 2.1))
    bottle = Image.new('RGBA', (260, 420), (0, 0, 0, 0))
    ImageDraw.Draw(bottle).rounded_rectangle((40, 80, 220, 410), 60, fill=(150, 190, 220, 150), outline=(210, 230, 245, 200), width=5)
    ImageDraw.Draw(bottle).rectangle((95, 0, 165, 90), fill=(150, 190, 220, 150), outline=(210, 230, 245, 200), width=5)
    put(img, bottle, 760, 1470, 1.0, 1.0, rot=-8)
    if red > 0:
        overlay(img, (180, 20, 20, int(70 * red)))
    return img


def sc_bench(t):
    s = S['A21']
    if t >= S['B21'] - 0.3:
        img = p444_face(t, ['B21'])
        return kb(img, t, S['B21'] - 0.3, E['B21'] + 0.3, 1.1, 1.2, (540, 900), (540, 880))
    img = corridor_soft().copy()
    a = anim2.silhouette('p444', hair='long', body=(36, 30, 28), rim=1.6)
    o = anim2.silhouette('odi_sit', body=(46, 40, 38), rim=1.4)
    put(img, o, 360, 1230, 1.0, 0.8)
    put(img, a, 740, 1230, 1.0, 0.75, rot=-3)
    d = ImageDraw.Draw(img)
    d.rectangle((60, 1430, 1020, 1480), fill=(40, 44, 50))
    drink = ramp(t, s + D['A21'] * 0.45, s + D['A21'] * 0.65)
    bx = 700 - 300 * eio(drink) * (1 - ramp(t, s + D['A21'] * 0.7, s + D['A21'] * 0.8))
    bottle = Image.new('RGBA', (120, 200), (0, 0, 0, 0))
    ImageDraw.Draw(bottle).rounded_rectangle((15, 40, 105, 195), 30, fill=(150, 190, 220, 150), outline=(210, 230, 245, 200), width=4)
    put(img, bottle, bx, 1180 - 120 * math.sin(math.pi * drink), 1.0, 1.0, rot=-60 * math.sin(math.pi * drink))
    return kb(img, t, s - 0.25, S['B21'], 1.0, 1.1, (540, 1000), (540, 1050))


def sc_talk444(t):
    keys = ['A22'] if t < S['A23'] else ['A24']
    k = keys[0]
    red = bump(t, S['A22'] + D['A22'] * 0.45, 0.1, 1.5) if k == 'A22' else 0.0
    img = p444_face(t, keys, red)
    return kb(img, t, S[k] - 0.25, E[k] + 0.4, 1.05, 1.25, (540, 900), (540, 860))


# ------------------------------------------------------------------ расы
RACES = [('worm', dict(arms=(False, False), legs=(False, False), lying=True), 0.12),
         ('zombie', dict(arms=(True, False), legs=(False, True)), 0.22),
         ('goblin', dict(arms=(False, True)), 0.32),
         ('orc', dict(), 0.42),
         ('halfling', dict(wide=1.15), 0.52)]


def sc_races(t):
    s = S['A23']
    d_ = D['A23']
    img = Image.new('RGBA', (W, H), (10, 12, 16, 255))
    fl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(fl).ellipse((-200, 1200, 1280, 1700), fill=(60, 80, 110, 120))
    img.alpha_composite(fl.filter(ImageFilter.GaussianBlur(60)))
    for k, (name, kw, frac) in enumerate(RACES):
        a = eo(ramp(t, s + d_ * frac, s + d_ * frac + 0.4))
        if a <= 0:
            continue
        spr = anim2.silhouette('race_' + name, body=(30 + k * 6, 32, 38), rim=1.6, **kw)
        x = 150 + k * 195
        sc = 0.42 + 0.04 * k
        y = 1440 - spr.height * sc / 2
        put(img, spr, x, y + 30 * (1 - a), a, sc)
    e = eio(ramp(t, s + d_ * 0.6, s + d_ * 0.72))
    if e > 0:
        lt = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lt).ellipse((240, 150, 840, 900), fill=(200, 220, 255, int(120 * e)))
        img.alpha_composite(lt.filter(ImageFilter.GaussianBlur(100)))
        elf = anim2.silhouette('elf', ears=True, body=(210, 225, 255), rim=0.4)
        put(img, elf, 540, 560 + 60 * (1 - e) + 8 * math.sin(t), e * 0.9, 0.42)
    return kb(img, t, s - 0.25, E['A23'] + 0.4, 1.1, 1.0, (540, 1150), (540, 960))


# ------------------------------------------------------------------ медблок, клукс, понижение
def sc_medblock(t):
    s = S['A25']
    img = anim2.medblock().copy()
    pul = 0.5 + 0.5 * math.sin(t * 5)
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((340, 560, 740, 900), fill=(255, 40, 30, int(60 * pul)))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(50)))
    spr = anim2.silhouette('odi_back', body=(40, 38, 40), rim=1.5)
    put(img, spr, 540, 1450, 1.0, 0.75)
    return kb(img, t, s - 0.25, E['A25'] + 0.3, 1.0, 1.1, (540, 1000), (540, 900))


def sc_klux(t):
    s = S['A26']
    w = s + D['A26'] * 0.78
    if t >= w:
        img = anim2.vending().copy()
        return kb(img, t, w, E['A26'] + 0.4, 1.05, 1.3, (540, 900), (540, 780))
    img = anim2.klux().copy()
    return kb(img, t, s - 0.25, w, 1.0, 1.35, (540, 1100), (800, 760))


def sc_demote(t):
    s = S['A27']
    img = odi_face(t, 0.6 * blink(t, [s + 1.5]), (0.0, 0.2), 0.3, bg=corridor_soft(), y=880, rot=-2)
    dn = S['A28'] - 0.1
    if t < dn:
        lines = [('СТАТУС: ОРН', GREEN)]
    else:
        glitch = bump(t, dn, 0.02, 0.4)
        lines = [('СТАТУС: УРН', (255, 90, 70))]
        if glitch > 0.1:
            lines = [('СТАТУС: ' + ('ОРН' if int(t * 40) % 2 else 'УРН'), (255, 90, 70))]
    put(img, hud_panel(lines, 1, 520), 540, 420, eo(ramp(t, s, s + 0.5)) * (0.85 + 0.15 * math.sin(t * 11)))
    return kb(img, t, s - 0.25, E['A28'] + 0.5, 1.05, 1.2, (540, 900), (540, 880))


# ------------------------------------------------------------------ охранник и капсула
def sc_guard(t):
    """охранник иглы бригады: «Отвали» -> бросает жвачку; затем стена капсул, крышка свободной открывается"""
    if t < E['B29'] + 0.3:
        img = corridor_soft().copy()
        g = anim2.silhouette('guard', wide=1.25, body=(14, 14, 16), rim=2.0)
        put(img, g, 540, 1080 + 4 * math.sin(t * 1.3), 1.0, 1.05)
        v = t - (S['B29'] + D['B29'] * 0.55)
        if v > 0:
            gum = Image.new('RGBA', (120, 60), (0, 0, 0, 0))
            ImageDraw.Draw(gum).rounded_rectangle((0, 0, 120, 60), 10, fill=(230, 230, 220, 255))
            ImageDraw.Draw(gum).rectangle((40, 0, 80, 60), fill=(200, 60, 60, 255))
            vv = min(v, 1.0)
            put(img, gum, 600 - 60 * vv, 900 + 500 * vv - 300 * vv * (1 - vv), 1.0, 0.8 + 2.2 * vv, rot=200 * v)
        return kb(img, t, S['B29'] - 0.3, E['B29'] + 0.3, 1.0, 1.1, (540, 960), (540, 900))
    img = anim2.capsule_wall().copy()
    op = eio(ramp(t, S['A29'] + D['A29'] * 0.55, S['A29'] + D['A29'] * 0.75))
    if op > 0:
        ImageDraw.Draw(img).rounded_rectangle((70, 310, 510, 850), 26, fill=(230, 200, 140))
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle((60, 300 - 500 * op, 520, 860 - 500 * op), 30, fill=(70, 78, 88, 255),
                                            outline=(110, 120, 130, 255), width=8)
        img.alpha_composite(g)
    return kb(img, t, S['A29'], E['A29'] + 0.4, 1.0, 1.5, (540, 960), (290, 600))


def sc_capsule(t):
    s = S['A30']
    img = Image.new('RGBA', (W, H), (8, 9, 12, 255))
    lamp = 1 - ramp(t, E['A30'] - 0.3, E['A30'] + 0.6)
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((140, 0, 940, 900), fill=(255, 220, 150, int(110 * lamp)))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(90)))
    o = 0.7 * (1 - eio(ramp(t, s + 1.2, E['A30'] - 0.2)))
    head = anim.hero_head_base().copy()
    anim.draw_hero_face(head, open_=o, gaze=(0, -0.2), furrow=0.2)
    head = ImageEnhance.Brightness(head).enhance(0.45 + 0.55 * lamp)
    put(img, head, 540, 1000, 1.0, 0.95, rot=90)
    im = kb(img, t, s - 0.25, DUR, 1.0, 1.15, (540, 960), (540, 960))
    return im


SCENE_FN = {'body': sc_body, 'face': sc_face, 'yorka_up': sc_yorka_up, 'yorka_look': sc_yorka_look, 'self': sc_self,
            'corridor': sc_corridor, 'scan': sc_scan, 'niche': sc_niche, 'yorka_talk': sc_yorka_talk, 'slap': sc_slap,
            'leave': sc_leave, 'menu': sc_menu, 'odin': sc_odin, 'screen': sc_screen, 'game': sc_game,
            'slime': sc_slime, 'kick': sc_kick, 'bench': sc_bench, 'talk444': sc_talk444, 'races': sc_races,
            'medblock': sc_medblock, 'klux': sc_klux, 'demote': sc_demote, 'guard': sc_guard, 'capsule': sc_capsule}


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


def grade(im, t):
    a = np.asarray(im.convert('RGB'), np.float32)
    lum = a.mean(-1, keepdims=True) / 255
    a = a + (1 - lum) * np.array([-8, 4, 14], np.float32)
    a = a * vignette() + grain(int(t * 24) % 8)
    return np.clip(a, 0, 255).astype(np.uint8)


@functools.lru_cache(None)
def sub_spr(text):
    f = ImageFont.truetype(str(ROOT / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Semibold.otf'), 40)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 40, bb[3] - bb[1] + 30
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((20 - bb[0], 17 - bb[1]), text, font=f, fill=(0, 0, 0, 210))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(im).text((20 - bb[0], 15 - bb[1]), text, font=f, fill=(236, 236, 232, 225))
    if im.width > 800:
        k = 800 / im.width
        im = im.resize((800, int(im.height * k)), Image.LANCZOS)
    return im


def subtitles(im, t):
    for t0, t1, text in SUBS:
        if t0 <= t < t1:
            a = ramp(t, t0, t0 + 0.1) * (1 - ramp(t, t1 - 0.1, t1))
            put(im, sub_spr(text), W / 2, 1360, a)


def mix(a, b, u):
    r = 10 * math.sin(math.pi * u)
    if r > 0.5:
        small = (W // 4, H // 4)
        a = a.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((W, H), Image.BILINEAR)
        b = b.resize(small, Image.BILINEAR).filter(ImageFilter.GaussianBlur(r / 4)).resize((W, H), Image.BILINEAR)
    return Image.blend(a, b, eio(u))


X = 0.25


def scene_at(t):
    for k, (name, t0, t1, _) in enumerate(SCENES):
        if t0 <= t < t1:
            return k
    return len(SCENES) - 1


def render_at(t):
    k = scene_at(t)
    name, t0, t1, _ = SCENES[k]
    im = None
    if k + 1 < len(SCENES) and t >= t1 - X:
        nxt = SCENES[k + 1][0]
        im = mix(SCENE_FN[name](t).convert('RGB'), SCENE_FN[nxt](t).convert('RGB'), (t - (t1 - X)) / (2 * X))
    elif k > 0 and t < t0 + X:
        prv = SCENES[k - 1][0]
        im = mix(SCENE_FN[prv](t).convert('RGB'), SCENE_FN[name](t).convert('RGB'), (t - (t0 - X)) / (2 * X))
    else:
        im = SCENE_FN[name](t)
    out = Image.fromarray(grade(im, t)).convert('RGBA')
    subtitles(out, t)
    kf = ramp(t, 0, 0.6) * (1 - ramp(t, DUR - 1.5, DUR))
    if kf < 1:
        overlay(out, (0, 0, 0, int(255 * (1 - kf))))
    return np.asarray(out.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
