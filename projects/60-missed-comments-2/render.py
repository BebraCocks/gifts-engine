"""Второй ролик-призыв (другой канал): неоновая аркада. Всё кодом, Мисед — только оригинальная ава в круге.

    python -B projects/60-missed-comments-2/render.py --frames 1.0,6.0
    python -B projects/60-missed-comments-2/render.py --build name.mp4
"""
import functools
import math
import random
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import cues  # noqa: E402
from timeline import V, T, DUR, scene_at  # noqa: E402

W, H, FPS = 1080, 1920, 60
FD = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
CYAN, MAG, YEL, RED = (0, 236, 255), (255, 46, 196), (255, 226, 70), (255, 50, 70)
INK = (6, 6, 22)


@functools.lru_cache(64)
def font(w, s):
    return ImageFont.truetype(str(FD / f'SF-Pro-Text-{w}.otf'), s)


def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3


def spring(x, f=2.0, z=0.4):
    if x <= 0:
        return 0.0
    w = 2 * math.pi * f; wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


def bump(x, f=6, dec=7):
    return 0.0 if x <= 0 else math.exp(-dec * x) * math.sin(2 * math.pi * f * x)


@functools.lru_cache(4)
def base_bg(top, bot):
    a = np.linspace(0, 1, H)[:, None, None]
    g = np.array(top, np.float32) * (1 - a) + np.array(bot, np.float32) * a
    return Image.fromarray(np.repeat(g, W, 1).astype(np.uint8), 'RGB').convert('RGBA')


def neon_bg(t, horizon=1250, top=(8, 6, 30), bot=(30, 4, 46)):
    """Синтвейв: тёмное небо, неоновая сетка-пол, уходящая в горизонт."""
    im = base_bg(top, bot).copy()
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(1, 16):                                   # горизонтали, бегут на зрителя
        z = (i + (t * 1.6) % 1) / 15
        y = horizon + (H - horizon) * z ** 2
        d.line((0, y, W, y), fill=MAG + (int(60 + 150 * z),), width=3)
    for i in range(-12, 13):
        d.line((W / 2 + i * 40, horizon, W / 2 + i * 260, H), fill=MAG + (110,), width=3)
    d.line((0, horizon, W, horizon), fill=CYAN + (200,), width=4)
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))
    im.alpha_composite(lay)
    return im


def scan(im, a=26):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for y in range(0, H, 6):
        d.line((0, y, W, y), fill=(0, 0, 0, a))
    im.alpha_composite(lay)


def ntext(im, s, x, y, size, col=CYAN, scale=1.0, a=1.0, weight='Heavy', glow=True, rgb=0.0, rot=0):
    """Неоновый текст: свечение цветом + белая сердцевина; rgb>0 — глитч-расслоение."""
    f = font(weight, max(8, int(size * scale)))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if rgb:
        d.text((x - rgb, y), s, font=f, anchor='mm', fill=(255, 0, 60, int(200 * a)))
        d.text((x + rgb, y), s, font=f, anchor='mm', fill=(0, 220, 255, int(200 * a)))
    if glow:
        g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((x, y), s, font=f, anchor='mm', fill=col + (int(255 * a),), stroke_width=10, stroke_fill=col + (int(255 * a),))
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(lay)
    d.text((x, y), s, font=f, anchor='mm', fill=(255, 255, 255, int(255 * a)), stroke_width=4, stroke_fill=col + (int(255 * a),))
    if rot:
        lay = lay.rotate(rot, center=(x, y), resample=Image.BICUBIC)
    im.alpha_composite(lay)


@functools.lru_cache(8)
def avatar(size):
    im = Image.open(HERE / 'refs' / 'missed_original.jpg').convert('RGB')
    im = im.crop((60, 0, 600, 540)).resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4, size * 4), fill=255)
    m = m.resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size)); out.paste(im, (0, 0), m)
    return out


def neon_ring(im, cx, cy, r, t, col=CYAN, col2=MAG):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col + (255,), width=12)
    for k in range(24):                                          # вращающийся пунктир
        a0 = t * 1.2 + k * 2 * math.pi / 24
        d.arc((cx - r - 34, cy - r - 34, cx + r + 34, cy + r + 34), math.degrees(a0), math.degrees(a0) + 7, fill=col2 + (255,), width=10)
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
    im.alpha_composite(lay)


def put(im, sprite, cx, cy, scale=1.0, alpha=1.0, rot=0):
    s = sprite
    if scale != 1.0:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BILINEAR)
    if rot:
        s = s.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 1:
        s = s.copy(); s.putalpha(s.getchannel('A').point(lambda v: int(v * alpha)))
    im.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


@functools.lru_cache(64)
def gift_png(name, size):
    m = G.models(name)[-1]['name']
    return Image.open(G.model_png(name, m, 512)).convert('RGBA').resize((size, size), Image.LANCZOS)


def gift_anim(name, model, t, size):
    return lottie.frame(G.model_file(name, model, 'tgs'), t, size=size)


def flash(im, t, t0, dur=0.12, col=(255, 255, 255)):
    u = t - t0
    if 0 <= u < dur:
        im.alpha_composite(Image.new('RGBA', (W, H), col + (int(210 * (1 - u / dur)),)))


def shake(t, hits, amp=20, dur=0.3):
    for h in hits:
        u = t - h
        if 0 <= u < dur:
            k = 1 - u / dur
            return int(amp * k * math.sin(u * 95)), int(amp * k * math.cos(u * 81))
    return 0, 0


def panel(im, box, col=CYAN, fill=(10, 10, 34, 235), r=36, w=6):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle(box, r, outline=col + (255,), width=w)
    g = lay.filter(ImageFilter.GaussianBlur(10))
    ImageDraw.Draw(im).rounded_rectangle(box, r, fill=fill)
    im.alpha_composite(g); im.alpha_composite(lay)


# ------------------------------------------------------------------ L1
def s1(t):
    if t < T['give']:                                        # «СТОП!» — красный глитч
        u = t - T['stop']
        im = Image.new('RGBA', (W, H), (14, 0, 6, 255))
        jit = 26 * math.sin(t * 60)
        ntext(im, 'СТОП!', W // 2 + jit * 0.3, H // 2, 260, RED, scale=1 + 0.5 * (1 - eo(u / 0.12)), rgb=18 + abs(jit) * 0.5)
        scan(im, 60)
        flash(im, t, T['stop'], 0.1, (255, 60, 60))
        return im
    u = t - T['give']
    im = neon_bg(t)
    cy = 760
    k = spring(u * 1.5, 2.0, 0.45)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W // 2 - 330, cy - 330, W // 2 + 330, cy + 330), fill=CYAN + (90,))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))
    put(im, avatar(500), W // 2, cy, 0.3 + 0.7 * k)
    neon_ring(im, W // 2, cy, int(255 * (0.3 + 0.7 * k)), t)
    for j, (line1, y_, sz) in enumerate((('МИСЕД', 200, 130), ('РАЗДАЁТ NFT', 340, 110))):
        n = int(len(line1) * cl((u - j * 0.35) / 0.4))
        if n:
            ntext(im, line1[:n] + ('_' if int(t * 6) % 2 and n < len(line1) else ''), W // 2, y_, sz, CYAN if j == 0 else YEL)
    if t >= T['forU']:
        v = t - T['forU']
        ntext(im, 'А Я ЗАБЕРУ ИХ', W // 2, 1150, 84, YEL, scale=spring(v * 1.8, 2.2, 0.45))
        ntext(im, 'ДЛЯ ВАС!', W // 2, 1290, 150, MAG, scale=spring((v - 0.2) * 1.8, 2.2, 0.45))
        for r in range(3):                                   # кольца «к зрителю»
            ph = (t * 1.4 + r / 3) % 1
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            rr = 120 + 700 * ph
            ImageDraw.Draw(lay).ellipse((W // 2 - rr, 1290 - rr * 0.4, W // 2 + rr, 1290 + rr * 0.4), outline=MAG + (int(160 * (1 - ph)),), width=6)
            im.alpha_composite(lay)
    scan(im)
    flash(im, t, T['give'], 0.14, CYAN)
    return im


# ------------------------------------------------------------------ L2
def flapdigit(ch, size, flip):
    w, h = int(size * 0.72), size
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 16, fill=(20, 20, 40), outline=CYAN + (255,), width=4)
    d.text((w // 2, h // 2), ch, font=font('Heavy', int(size * 0.75)), anchor='mm', fill=(255, 255, 255))
    d.line((6, h // 2, w - 6, h // 2), fill=INK, width=4)
    if flip > 0:
        sq = max(0, int((h / 2 - 8) * (1 - flip)))             # падающая шторка верхней половины
        if sq > 0:
            d.rectangle((4, h // 2 - 2 - sq, w - 4, h // 2 - 2), fill=(40, 40, 70))
    return im


def s2(t):
    u = t - V['L2']
    im = neon_bg(t, horizon=1500, top=(6, 10, 34), bot=(22, 6, 40))
    put(im, avatar(170), W - 140, 170, 1.0)
    neon_ring(im, W - 140, 170, 88, t, MAG, CYAN)
    ntext(im, 'УСЛОВИЕ', 380, 170, 120, YEL, scale=spring(u * 1.6, 2.2, 0.45))
    panel(im, (60, 330, W - 60, 760), MAG)
    lines = ['кто ПЕРВЫМ наберёт', 'больше всех', 'КОММЕНТАРИЕВ']
    for i, ln in enumerate(lines):
        a = eo((t - T['rule'] - i * 0.35) / 0.25)
        ntext(im, ln, W // 2, 420 + i * 120, 80 if i < 2 else 96, CYAN if i < 2 else MAG, a=a, weight='Heavy')
    # табло-счётчик
    if t >= T['rule']:
        v = t - T['rule']
        n = min(99999, int((v * 1.3) ** 3 * 600))
        s = f'{n:05d}'
        for i, ch in enumerate(s):
            fl = (v * 8 + i * 0.37) % 1
            put(im, flapdigit(ch, 190, fl if v < 2.6 else 0), 210 + i * 165, 960)
        ntext(im, 'комментариев', W // 2, 1110, 56, CYAN, weight='Bold')
    if t >= T['win']:
        v = t - T['win']
        ntext(im, '→ ПОДАРОК ТВОЙ!', W // 2, 1310, 100, YEL, scale=spring(v * 1.8, 2.2, 0.45))
        for i in range(24):                                  # конфетти
            rr = random.Random(i)
            x = W / 2 + rr.uniform(-1, 1) * 500 * eo(v / 0.6)
            y = 1310 - rr.uniform(100, 500) * eo(v / 0.6) + 400 * v * v
            c = [CYAN, MAG, YEL][i % 3]
            ImageDraw.Draw(im).rectangle((x - 9, y - 14, x + 9, y + 14), fill=c)
    scan(im)
    return im


# ------------------------------------------------------------------ L3: путь-квест
CP = [(300, 3000), (780, 2050), (420, 1100)]                    # чекпоинты в «мире» (y вверх — дальше)


def s3(t):
    im = base_bg((10, 4, 30), (4, 10, 30)).copy()
    reached = sum(1 for x in T['tier'] if t >= x)
    # камера: плавно ведём к текущему чекпоинту
    targets = [3300] + [CP[i][1] for i in range(3)]
    keys = [V['L3']] + [x - 0.35 for x in T['tier']]
    cam = targets[0]
    for i in range(1, 4):
        if t >= keys[i]:
            cam = targets[i - 1] + (targets[i] - targets[i - 1]) * eo((t - keys[i]) / 0.5)
    oy = H * 0.55 - cam
    dx, dy = shake(t, T['tier'], 16, 0.25)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(540, 3700), (300, 3000), (780, 2050), (420, 1100), (600, 300)]
    path = []
    for a, b in zip(pts, pts[1:]):
        for s in np.linspace(0, 1, 40):
            path.append((a[0] + (b[0] - a[0]) * s + 90 * math.sin(s * math.pi), a[1] + (b[1] - a[1]) * s))
    scr = [(x + dx, y + oy + dy) for x, y in path]
    d.line(scr, fill=CYAN + (255,), width=16, joint='curve')
    g = lay.filter(ImageFilter.GaussianBlur(14))
    im.alpha_composite(g); im.alpha_composite(lay)
    for i, ((lab, name, model), (cx, cy)) in enumerate(zip(cues.TIERS, CP)):
        sx, sy = cx + dx, cy + oy + dy
        if sy < 330 or sy > H + 400:
            continue
        on = i < reached
        col = [YEL, CYAN, MAG][i]
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse((sx - 120, sy - 120, sx + 120, sy + 120), fill=(14, 14, 40, 255),
                                     outline=(col if on else (90, 90, 120)) + (255,), width=10)
        if on:
            gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse((sx - 260, sy - 260, sx + 260, sy + 260), fill=col + (90,))
            im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(60)))
        im.alpha_composite(lay)
        if on:
            v = t - T['tier'][i]
            sc = spring(v * 1.4, 2.0, 0.45)
            put(im, gift_anim(name, model, v, 420), sx, sy - 170 * sc, 0.2 + 0.8 * sc)
            lx = sx + (320 if cx < 540 else -320)
            ntext(im, lab, lx, sy + 20, 120, col, scale=spring((v - 0.1) * 1.8, 2.2, 0.45))
            ntext(im, name, lx, sy + 130, 54, (255, 255, 255), weight='Bold',
                  a=eo((v - 0.3) / 0.3), glow=False)
        else:
            ntext(im, '?', sx, sy, 130, (120, 120, 160), glow=False)
    ntext(im, 'НАГРАДЫ', W // 2, 140, 110, YEL)
    scan(im)
    for x in T['tier']:
        flash(im, t, x, 0.1, (255, 240, 200))
    return im


# ------------------------------------------------------------------ L4
def cart_img(n_items, t):
    im = Image.new('RGBA', (640, 520), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(n_items):                                 # подарки внутри тележки
        rr = random.Random(i)
        g = gift_png(cues.CHEAP[i % len(cues.CHEAP)], 120)
        x = 110 + (i % 4) * 110 + rr.uniform(-15, 15)
        y = 230 - (i // 4) * 70 + rr.uniform(-10, 10)
        im.alpha_composite(g, (int(x - 60), int(y - 60)))
    d.polygon(((60, 200), (600, 200), (540, 400), (120, 400)), fill=(20, 20, 50, 200), outline=CYAN + (255,))
    d.line(((60, 200), (600, 200), (540, 400), (120, 400), (60, 200)), fill=CYAN + (255,), width=10)
    d.line(((600, 200), (630, 120)), fill=CYAN + (255,), width=10)
    for x in (170, 490):
        d.ellipse((x - 34, 420, x + 34, 488), outline=MAG + (255,), width=10)
    return im


USERS = ['@kira', '@den4ik', '@lisa_nft', '@artem', '@mila', '@goshan', '@ksu', '@vovan']


def s4(t):
    im = neon_bg(t, horizon=1650, top=(6, 8, 30), bot=(30, 6, 30))
    dx, dy = shake(t, [T['self0'] + 0.3], 22, 0.3)
    if t < T['buy']:
        v = t - T['self0']
        ntext(im, 'СЕБЕ:', W // 2 - 170 + dx, 300 + dy, 110, CYAN)
        ntext(im, '0', W // 2 + 230 + dx, 300 + dy, 260, MAG, scale=1 + 1.3 * (1 - eo((v - 0.3) / 0.15)) if v > 0.3 else 0.01)
        if t >= T['sell']:
            w = t - T['sell']
            put(im, gift_anim('Mighty Arm', 'T800', w, 480), W // 2, 900 - 600 * eo((w - 0.5) / 0.5))
            ntext(im, 'ПРОДАНО', W // 2, 1180, 150, RED, scale=1 + 1 * (1 - eo(w / 0.15)), rot=-8)
            for i in range(14):                               # монеты
                rr = random.Random(i)
                x = W / 2 + rr.uniform(-420, 420)
                y = 700 + (w * rr.uniform(500, 900)) % 900
                ImageDraw.Draw(im).ellipse((x - 26, y - 26, x + 26, y + 26), fill=YEL, outline=(160, 110, 10), width=5)
                ImageDraw.Draw(im).text((x, y), '$', font=font('Heavy', 30), anchor='mm', fill=(160, 110, 10))
    elif t < T['give2']:
        w = t - T['buy']
        ntext(im, 'НАКУПЛЮ NFT', W // 2, 260, 110, YEL, scale=spring(w * 1.6, 2.2, 0.45))
        ntext(im, 'на все деньги', W // 2, 380, 64, CYAN, weight='Bold')
        n = min(16, int(w / 0.1))
        put(im, cart_img(n, t), W // 2, 1000 + 8 * math.sin(t * 6), 1.3)
        for i in range(6):                                   # подарки летят в тележку
            rr = random.Random(i + 50)
            k = ((w * 1.4) + i / 6) % 1
            x = rr.uniform(100, W - 100) * (1 - k) + W / 2 * k
            y = 520 * (1 - k) + 900 * k - 200 * math.sin(math.pi * k)
            put(im, gift_png(cues.CHEAP[(i * 5) % len(cues.CHEAP)], 120), x, y, 1 - 0.3 * k)
    else:
        w = t - T['give2']
        ntext(im, 'РАЗДАМ ВАМ!', W // 2, 210, 120, MAG, scale=spring(w * 1.6, 2.2, 0.45))
        top = t >= T['top']
        for i, u_ in enumerate(USERS):
            y = 400 + i * 145
            hl = top and i == 3
            panel(im, (70, y, W - 70, y + 120), YEL if hl else CYAN, fill=(40, 30, 10, 240) if hl else (10, 10, 34, 235),
                  r=30, w=8 if hl else 4)
            rr = random.Random(u_)
            d = ImageDraw.Draw(im)
            d.ellipse((95, y + 18, 179, y + 102), fill=(rr.randint(80, 255), rr.randint(80, 220), rr.randint(120, 255)))
            d.text((200, y + 60), u_, font=font('Bold', 44), anchor='lm', fill=(255, 255, 255))
            got = w > 0.2 + i * 0.16
            if got:
                kk = eo((w - 0.2 - i * 0.16) / 0.3)
                put(im, gift_png(cues.CHEAP[(i * 3 + 7) % len(cues.CHEAP)], 100), W - 150, y + 60 - 300 * (1 - kk), 0.5 + 0.5 * kk)
            if hl:
                v = t - T['top']
                ntext(im, '👑 ТОП' .replace('👑 ', ''), 640, y + 60, 50, YEL, a=eo(v / 0.2), weight='Heavy')
        if top:
            v = t - T['top']
            lay = Image.new('RGBA', (440, 440), (0, 0, 0, 0))
            bd = ImageDraw.Draw(lay)
            bd.rounded_rectangle((30, 140, 410, 420), 30, fill=(150, 20, 160), outline=YEL, width=10)
            bd.rectangle((190, 140, 250, 420), fill=YEL)
            bd.rounded_rectangle((10, 90, 430, 180), 26, fill=(190, 40, 200), outline=YEL, width=10)
            bd.text((220, 290), '?', font=font('Heavy', 200), anchor='mm', fill=(255, 255, 255))
            put(im, lay, W // 2, 1620, spring(v * 1.5, 2.2, 0.45) * 0.62, rot=5 * math.sin(t * 3))
            ntext(im, 'ОСОБЫЙ ПОДАРОК', W // 2, 1840, 66, YEL, a=eo((v - 0.3) / 0.3))
    scan(im)
    return im


# ------------------------------------------------------------------ L5
SAMPLES = ['хочу Plush Pepe!', 'имба', '+', 'го-го', 'Мисед топ', ')', 'хочу NFT', 'я тут', 'лол']


def s5(t):
    im = neon_bg(t, horizon=1700, top=(18, 4, 34), bot=(6, 8, 30))
    if t < T['any']:
        v = t - V['L5']
        ntext(im, 'НЕ МОЛЧИ!', W // 2, 260, 140, MAG, scale=spring(v * 1.6, 2.2, 0.45))
        panel(im, (60, 820, W - 60, 980), CYAN, r=60)
        txt = 'хочу Plush Pepe!'
        n = int(len(txt) * cl((t - T['type']) / 2.2))
        shown = txt[:n] if t >= T['type'] else ''
        d = ImageDraw.Draw(im)
        d.text((110, 900), shown if shown else 'Добавьте комментарий…', font=font('Semibold', 56), anchor='lm',
               fill=(255, 255, 255) if shown else (130, 130, 170))
        if int(t * 2.5) % 2:
            x = 110 + d.textlength(shown, font=font('Semibold', 56)) + 6
            d.rectangle((x, 860, x + 6, 940), fill=CYAN)
        d.ellipse((W - 200, 845, W - 90, 955), fill=MAG)
        d.polygon(((W - 165, 875), (W - 165, 925), (W - 115, 900)), fill=(255, 255, 255))
        ntext(im, 'какой подарок хочешь ТЫ?', W // 2, 650, 64, CYAN, weight='Bold')
    else:
        v = t - T['any']
        ntext(im, 'ЗАСЧИТЫВАЕТСЯ', W // 2, 200, 100, CYAN, scale=spring(v * 1.6, 2.2, 0.45))
        ntext(im, 'ЛЮБОЙ КОММЕНТ', W // 2, 320, 100, YEL, scale=spring((v - 0.1) * 1.6, 2.2, 0.45))
        for i, ct in enumerate(cues.COMMENTS):
            w = t - ct
            if w < 0:
                continue
            x = 260 + (i % 3) * 280
            y = 520 + (i // 3) * 150
            b = Image.new('RGBA', (260, 110), (0, 0, 0, 0))
            bd = ImageDraw.Draw(b)
            bd.rounded_rectangle((0, 0, 259, 109), 50, fill=(20, 20, 50, 240), outline=CYAN + (255,), width=4)
            bd.text((130, 55), SAMPLES[i], font=font('Bold', 40 if len(SAMPLES[i]) < 10 else 30), anchor='mm', fill=(255, 255, 255))
            put(im, b, x, y, spring(w * 2, 2.4, 0.5))
        if t >= T['dot']:
            w = t - T['dot']
            panel(im, (W // 2 - 170, 1000, W // 2 + 170, 1220), MAG, r=70, w=8)
            ImageDraw.Draw(im).ellipse((W // 2 - 26, 1084, W // 2 + 26, 1136), fill=(255, 255, 255))
            ntext(im, 'ДАЖЕ ТОЧКА!', W // 2, 1340, 120, MAG, scale=1 + 1.2 * (1 - eo(w / 0.15)), rot=-4)
        if t >= T['more']:
            w = t - T['more']
            frac = eo(w / 2.4)
            panel(im, (90, 1500, W - 90, 1600), YEL, r=50)
            ImageDraw.Draw(im).rounded_rectangle((104, 1514, 104 + (W - 208) * frac, 1586), 40, fill=YEL)
            ntext(im, 'РАЗДАЧА', W // 2, 1550, 64, MAG, glow=False)
            ntext(im, 'БОЛЬШЕ КОММЕНТОВ =', W // 2, 1690, 60, CYAN, a=eo(w / 0.3), weight='Heavy')
            ntext(im, 'БОЛЬШЕ NFT!', W // 2, 1790, 80, YEL, a=eo((w - 0.2) / 0.3), weight='Heavy')
            ax, ay = W - 100 + 20 * math.sin(t * 8), 1110
            ImageDraw.Draw(im).polygon(((ax - 100, ay - 30), (ax - 20, ay - 30), (ax - 20, ay - 72), (ax + 60, ay),
                                        (ax - 20, ay + 72), (ax - 20, ay + 30), (ax - 100, ay + 30)), fill=YEL, outline=INK, width=6)
        flash(im, t, T['dot'], 0.1, MAG)
    end = DUR - t
    if end < 0.5:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.5)))))
    scan(im)
    return im


def render_at(t):
    s = scene_at(t)
    im = {'L1': s1, 'L2': s2, 'L3': s3, 'L4': s4, 'L5': s5}[s](t)
    if s != 'L1':
        flash(im, t, V[s], 0.1, CYAN)
    for x in (T['buy'], T['give2'], T['any']):
        flash(im, t, x, 0.08, (255, 255, 255))
    return im.convert('RGB')


def _frame(i):
    return render_at(i / FPS).tobytes()


def build(name):
    out = HERE / 'build' / name
    n = int(DUR * FPS)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                            '-r', str(FPS), '-i', '-', '-i', str(HERE / 'build' / 'mix.wav'), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
                            '-shortest', '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(_frame, range(n), chunksize=8)):
            enc.stdin.write(b)
            if i % (n // 10) == 0:
                print(f'PROGRESS {round(100 * i / n)}%', flush=True)
    enc.stdin.close(); enc.wait()
    print('OK', out)


if __name__ == '__main__':
    if sys.argv[1] == '--frames':
        rev = HERE / 'build' / 'review'; rev.mkdir(parents=True, exist_ok=True)
        for ts in sys.argv[2].split(','):
            render_at(float(ts)).save(rev / f'frame_{float(ts):06.2f}.jpg', quality=90)
        print('frames OK')
    elif sys.argv[1] == '--build':
        build(sys.argv[2])
