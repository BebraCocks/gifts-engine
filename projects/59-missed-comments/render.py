"""Картинка «Помоги выиграть NFT у Миседа»: всё кодом, Мисед — только оригинальная ава в круге.

    python -B projects/59-missed-comments/render.py --frames 1.0,6.0
    python -B projects/59-missed-comments/render.py --build name.mp4
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
from timeline import V, T, D, DUR, scene_at  # noqa: E402

W, H, FPS = 1080, 1920, 60
FD = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
GOLD = (255, 206, 70)


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


@functools.lru_cache(8)
def gradient(top, bot):
    a = np.linspace(0, 1, H)[:, None, None]
    g = np.array(top, np.float32) * (1 - a) + np.array(bot, np.float32) * a
    return Image.fromarray(np.repeat(g, W, 1).astype(np.uint8), 'RGB').convert('RGBA')


def bg(t, top=(34, 10, 70), bot=(8, 6, 30)):
    im = gradient(top, bot).copy()
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(26):                                   # плавающие огоньки-боке
        rr = random.Random(i)
        x = (rr.uniform(0, W) + 20 * math.sin(t * 0.6 + i)) % W
        y = (rr.uniform(0, H) - t * rr.uniform(20, 60)) % H
        r = rr.uniform(20, 70)
        c = [(255, 90, 200), (90, 160, 255), (255, 200, 80)][i % 3]
        d.ellipse((x - r, y - r, x + r, y + r), fill=c + (40,))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
    return im


def rays(im, cx, cy, t, col=(255, 210, 90), a=55, n=18):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        a0 = t * 0.35 + i * 2 * math.pi / n
        d.polygon((cx, cy, cx + 1700 * math.cos(a0), cy + 1700 * math.sin(a0),
                   cx + 1700 * math.cos(a0 + 0.11), cy + 1700 * math.sin(a0 + 0.11)), fill=col + (a,))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5)))


def glow(im, cx, cy, r, col, a=140, blur=60):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (a,))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur)))


def text(im, s, x, y, size, col=(255, 255, 255), a=1.0, scale=1.0, stroke=10, weight='Heavy', anchor='mm', rot=0):
    f = font(weight, max(8, int(size * scale)))
    if rot:
        tmp = Image.new('RGBA', (W, 600), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((W // 2, 300), s, font=f, anchor='mm', fill=col + (int(255 * a),),
                                 stroke_width=stroke, stroke_fill=(20, 8, 40, int(255 * a)))
        tmp = tmp.rotate(rot, resample=Image.BICUBIC)
        im.alpha_composite(tmp, (int(x - W // 2), int(y - 300)))
        return
    ImageDraw.Draw(im).text((x, y), s, font=f, anchor=anchor, fill=col + (int(255 * a),),
                            stroke_width=stroke, stroke_fill=(20, 8, 40, int(255 * a)))


@functools.lru_cache(8)
def avatar(size):
    """Оригинальная ава Миседа в круге с золотой каймой."""
    im = Image.open(HERE / 'refs' / 'missed_original.jpg').convert('RGB')
    im = im.crop((60, 0, 600, 540)).resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4, size * 4), fill=255)
    m = m.resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size + 28, size + 28), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, size + 27, size + 27), fill=GOLD + (255,))
    av = Image.new('RGBA', (size, size)); av.paste(im, (0, 0), m)
    out.alpha_composite(av, (14, 14))
    return out


def put_center(im, sprite, cx, cy, scale=1.0, alpha=1.0, rot=0):
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


def comment_icon(size, col=(255, 255, 255)):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    d.ellipse((s * 0.06, s * 0.08, s * 0.94, s * 0.78), fill=col + (255,))
    d.polygon(((s * 0.25, s * 0.66), (s * 0.18, s * 0.94), (s * 0.48, s * 0.74)), fill=col + (255,))
    for k in range(3):
        cx = s * (0.32 + 0.18 * k)
        d.ellipse((cx - s * 0.05, s * 0.38, cx + s * 0.05, s * 0.48), fill=(40, 20, 70, 255))
    return im


def comment_bubble(txt, w=None):
    f = font('Bold', 40)
    tw = ImageDraw.Draw(Image.new('L', (1, 1))).textlength(txt, font=f)
    bw = int(w or tw + 150); bh = 96
    im = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, bw - 1, bh - 1), 48, fill=(255, 255, 255, 240))
    rr = random.Random(txt)
    d.ellipse((14, 14, 82, 82), fill=(rr.randint(80, 255), rr.randint(80, 200), rr.randint(120, 255)))
    d.text((100, bh // 2), txt, font=f, anchor='lm', fill=(30, 20, 50))
    return im


def flash(im, t, t0, dur=0.14, col=(255, 255, 255)):
    u = t - t0
    if 0 <= u < dur:
        im.alpha_composite(Image.new('RGBA', (W, H), col + (int(220 * (1 - u / dur)),)))


def shake(t, hits, amp=18, dur=0.3):
    for h in hits:
        u = t - h
        if 0 <= u < dur:
            k = 1 - u / dur
            return int(amp * k * math.sin(u * 90)), int(amp * k * math.cos(u * 77))
    return 0, 0


# ------------------------------------------------------------------ сцены
def s1(t):
    u = t - V['L1']
    im = bg(t)
    rays(im, W // 2, 820, t, a=50)
    glow(im, W // 2, 820, 360, (255, 200, 80), 120, 80)
    # подарки разлетаются от аватарки
    for i, name in enumerate(cues.CHEAP[:10]):
        a0 = i * 2 * math.pi / 10 + 0.3
        k = eo(u / 0.9)
        r = 120 + 400 * k
        x, y = W // 2 + r * math.cos(a0), 820 + r * math.sin(a0) * 1.1
        fade_ = 1 - 0.75 * eo((t - T['help']) / 0.4)            # после «Помоги…» подарки уходят на задний план
        put_center(im, gift_png(name, 150), x, y + 10 * math.sin(t * 3 + i), 0.6 + 0.4 * k, alpha=fade_, rot=15 * math.sin(t * 2 + i))
    big = cl((T['help'] - t) / 0.25) if t < T['help'] + 0.3 else 0
    small = eo((t - T['help']) / 0.35)
    sc = (1 + 0.6 * (1 - spring(u * 1.6, 2.2, 0.45))) * (1 - 0.32 * small)
    cy = 820 - 180 * small
    put_center(im, avatar(500), W // 2, cy, sc)
    # заголовок
    k1 = spring(u * 1.8, 2.4, 0.45)
    text(im, 'МИСЕД', W // 2, 250 - 30 * small, 150, GOLD, scale=0.5 + 0.5 * k1 if u < 1.5 else 1)
    text(im, 'РАЗДАЁТ NFT!', W // 2, 400 - 30 * small, 112, (255, 255, 255), scale=0.5 + 0.5 * spring((u - 0.15) * 1.8, 2.4, 0.45))
    if t >= T['help']:
        v = t - T['help']
        text(im, 'ПОМОГИ ВЫИГРАТЬ —', W // 2, 1230, 78, (255, 255, 255), a=eo(v / 0.2), scale=0.8 + 0.2 * eo(v / 0.25))
        text(im, 'И ВСЁ РАЗДАМ ВАМ!', W // 2, 1340, 92, (140, 255, 170), a=eo((v - 0.9) / 0.2),
             scale=0.7 + 0.3 * spring((v - 0.9) * 1.6, 2.4, 0.45))
        # стрелочки «к вам»
        if v > 1.2:
            for k in range(3):
                ph = (t * 2 + k / 3) % 1
                text(im, '▼', W // 2 + (k - 1) * 160, 1480 + 60 * ph, 70, GOLD, a=1 - ph, stroke=4)
    flash(im, t, V['L1'], 0.2)
    return im


def bar(im, x0, y0, x1, frac, label):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0, y0, x1, y0 + 90), 45, fill=(30, 16, 60), outline=(255, 255, 255), width=6)
    fw = max(90, int((x1 - x0) * frac))
    d.rounded_rectangle((x0 + 8, y0 + 8, x0 + fw - 8, y0 + 82), 38, fill=(120, 255, 160))
    text(im, label, (x0 + x1) // 2, y0 + 45, 52, (255, 255, 255), stroke=7)


def s2(t):
    u = t - V['L2']
    im = bg(t, (16, 14, 70), (6, 4, 26))
    put_center(im, avatar(220), W // 2, 230, 1 + 0.05 * math.sin(t * 4))
    # корона над авой
    d = ImageDraw.Draw(im)
    cx = W // 2
    d.polygon(((cx - 90, 120), (cx - 110, 40), (cx - 50, 85), (cx, 20), (cx + 50, 85), (cx + 110, 40), (cx + 90, 120)),
              fill=GOLD, outline=(120, 80, 10))
    k = spring(u * 1.6, 2.2, 0.45)
    text(im, 'КОНКУРС', W // 2, 470, 150, GOLD, scale=0.4 + 0.6 * k, rot=-4)
    text(im, 'кто первым соберёт', W // 2, 620, 60, (255, 255, 255), a=eo((u - 0.4) / 0.3), weight='Bold', stroke=7)
    text(im, 'больше всех комментариев', W // 2, 700, 60, (255, 255, 255), a=eo((u - 0.4) / 0.3), weight='Bold', stroke=7)
    n = int(min(10000, max(0, (u - 0.6) * 380)) // 7 * 7)
    jit = int(4 * math.sin(t * 40)) if u > 0.6 else 0
    put_center(im, comment_icon(200), W // 2, 900 + jit, 1 + 0.08 * abs(math.sin(t * 5)))
    bar(im, 110, 1030, W - 110, n / 10000, f'{n:,}'.replace(',', ' ') + ' / 10 000')
    for i, t0 in enumerate(cues.BUBBLES2):                # всплывающие комментарии
        v = t - t0
        if v < 0:
            continue
        txt = ['го-го-го!', 'я в деле', 'хочу NFT', 'Мисед топ', 'пишу!', '+1'][i]
        b = comment_bubble(txt)
        x = 260 if i % 2 == 0 else W - 260
        y = 1300 + (i // 2) * 130 - 60 * eo(v / 3)
        put_center(im, b, x, y, spring(v * 1.8, 2.4, 0.5), max(0.01, 1 - cl((v - 3.5) / 0.4)))
    return im


def s3(t):
    im = bg(t, (40, 14, 60), (8, 6, 26))
    dx, dy = shake(t, [x + 0.18 for x in T['tier']], 14, 0.25)
    for i, ((cnt, name, model), t0) in enumerate(zip(cues.TIERS, T['tier'])):
        v = t - t0
        if v < 0:
            continue
        y = 330 + i * 500
        x = W // 2 + 1200 * (1 - eo(v / 0.3))
        active = i == max(j for j, tt in enumerate(T['tier']) if t >= tt)
        card = Image.new('RGBA', (980, 440), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        col = [(255, 170, 60), (90, 200, 255), (255, 90, 160)][i]
        cd.rounded_rectangle((0, 0, 979, 439), 60, fill=(28, 16, 54, 245), outline=col + (255,), width=10 if active else 5)
        cd.text((440, 120), cnt, font=font('Heavy', 96), anchor='lm', fill=col + (255,))
        cd.text((440, 220), 'комментариев', font=font('Bold', 48), anchor='lm', fill=(255, 255, 255, 255))
        cd.text((440, 320), name, font=font('Heavy', 58), anchor='lm', fill=(255, 255, 255, 255))
        if active:
            gc = Image.new('RGBA', card.size, (0, 0, 0, 0))
            ImageDraw.Draw(gc).ellipse((20, 20, 420, 420), fill=col + (110,))
            card.alpha_composite(gc.filter(ImageFilter.GaussianBlur(40)))
        g = gift_anim(name, model, v, 380)
        bs = 1 + (0.12 * bump(v - 0.3, 3, 4) if active else 0)
        gg = g.resize((int(380 * bs), int(380 * bs)))
        card.alpha_composite(gg, (220 - gg.width // 2, 220 - gg.height // 2))
        sc = 1.0 if active else 0.92
        a = 1.0 if active else 0.75
        put_center(im, card, x + dx, y + dy, sc, a)
    for t0 in T['tier']:
        flash(im, t, t0 + 0.18, 0.1, (255, 230, 160))
    return im


def trophy(size):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    d.chord((s * 0.2, s * 0.05, s * 0.8, s * 0.65), 0, 180, fill=GOLD, outline=(140, 90, 10), width=8)
    d.rectangle((s * 0.2, s * 0.05, s * 0.8, s * 0.35), fill=GOLD, outline=(140, 90, 10), width=8)
    for sg in (-1, 1):
        cx = s * 0.5 + sg * s * 0.32
        d.arc((cx - s * 0.13, s * 0.1, cx + s * 0.13, s * 0.4), 90 if sg < 0 else 270, 270 if sg < 0 else 90,
              fill=GOLD, width=int(s * 0.05))
    d.rectangle((s * 0.45, s * 0.6, s * 0.55, s * 0.78), fill=GOLD, outline=(140, 90, 10), width=6)
    d.rounded_rectangle((s * 0.28, s * 0.78, s * 0.72, s * 0.92), 12, fill=(120, 70, 30), outline=(60, 30, 10), width=6)
    d.text((s * 0.5, s * 0.3), '1', font=font('Heavy', int(s * 0.25)), anchor='mm', fill=(140, 90, 10))
    return im


def s4(t):
    u = t - V['L4']
    im = bg(t, (20, 40, 30), (6, 12, 20)) if t < T['top'] else bg(t, (60, 40, 10), (14, 8, 4))
    dx, dy = shake(t, [T['sold']], 22, 0.35)
    if t < T['top']:
        # выигранный Mighty Arm уходит на продажу
        k_out = eo((t - T['rain']) / 0.4)
        cy = 600 - 900 * k_out
        if cy > -300:
            rays(im, W // 2, int(cy), t, (255, 220, 120), 40)
            put_center(im, gift_anim('Mighty Arm', 'T800', u, 560), W // 2 + dx, cy + dy)
            if t >= T['sold']:
                v = t - T['sold']
                text(im, 'ПРОДАНО', W // 2 + dx, cy + 260 + dy, 150, (255, 80, 90), scale=1 + 1.2 * (1 - eo(v / 0.15)), rot=-12,
                     stroke=12)
        # ряды комментариев внизу
        names = ['@lera', '@max', '@dima', '@sonya', '@egor', '@vika', '@timur', '@nastya']
        for i, nm in enumerate(names):
            x = 160 + (i % 4) * 253
            y = 1380 + (i // 4) * 260
            put_center(im, comment_icon(150, (230, 230, 255)), x, y + 6 * math.sin(t * 3 + i))
            text(im, nm, x, y + 110, 34, (255, 255, 255), weight='Bold', stroke=5)
        # дождь из дешёвых NFT
        if t >= T['rain']:
            v = t - T['rain']
            for i, name in enumerate(cues.CHEAP):
                rr = random.Random(i)
                tx = 160 + (i % 4) * 253 + rr.uniform(-40, 40)
                ty = 1300 + ((i // 4) % 2) * 260
                start = rr.uniform(0, 1.2)
                k = cl((v - start) / 0.9)
                if k <= 0:
                    continue
                x = rr.uniform(0, W) * (1 - k) + tx * k
                y = -150 * (1 - k) + ty * k - 200 * math.sin(math.pi * k)
                put_center(im, gift_png(name, 150), x, y, 0.7 + 0.3 * (1 - k), rot=40 * (1 - k) * (1 if i % 2 else -1))
            sc_ = spring(v * 1.6, 2.2, 0.45)
            ImageDraw.Draw(im).rounded_rectangle((W // 2 - 430 * sc_, 250 - 80 * sc_, W // 2 + 430 * sc_, 250 + 80 * sc_), 50,
                                                 fill=(20, 8, 40, 220))
            text(im, 'КУЧА NFT — ВАМ!', W // 2, 250, 100, (140, 255, 170), scale=sc_)
    else:
        v = t - T['top']
        rays(im, W // 2, 760, t, GOLD, 60)
        glow(im, W // 2, 760, 380, (255, 200, 80), 150, 90)
        put_center(im, trophy(560), W // 2, 760 + 30 * math.sin(t * 2), spring(v * 1.4, 2, 0.45))
        text(im, 'ТОП-КОММЕНТАТОР', W // 2, 260, 96, GOLD, scale=spring((v - 0.1) * 1.6, 2.2, 0.45))
        # загадочный крутой NFT
        if v > 1.3:
            w = v - 1.3
            box = Image.new('RGBA', (420, 420), (0, 0, 0, 0))
            bd = ImageDraw.Draw(box)
            bd.rounded_rectangle((20, 120, 400, 400), 30, fill=(150, 40, 220), outline=(255, 255, 255), width=8)
            bd.rectangle((180, 120, 240, 400), fill=GOLD)
            bd.rounded_rectangle((0, 70, 420, 160), 24, fill=(180, 60, 240), outline=(255, 255, 255), width=8)
            bd.rectangle((180, 70, 240, 160), fill=GOLD)
            bd.text((210, 280), '?', font=font('Heavy', 200), anchor='mm', fill=(255, 255, 255))
            glow(im, W // 2, 1420, 260, (200, 90, 255), 140, 60)
            put_center(im, box, W // 2, 1420 + 12 * bump(w, 3, 2), spring(w * 1.6, 2.2, 0.45), rot=6 * math.sin(t * 3))
            text(im, 'КРУТОЙ NFT', W // 2, 1720, 90, (255, 255, 255), a=eo(w / 0.3))
        flash(im, t, T['top'], 0.2, (255, 230, 150))
    flash(im, t, T['sold'], 0.12, (255, 120, 120))
    return im


def s5(t):
    u = t - V['L5']
    im = bg(t, (60, 10, 50), (10, 4, 26))
    text(im, 'ПИШИ СВОЙ ЛЮБИМЫЙ', W // 2, 200, 74, (255, 255, 255), scale=spring(u * 1.6, 2.2, 0.45))
    text(im, 'NFT-ПОДАРОК!', W // 2, 300, 110, GOLD, scale=spring((u - 0.15) * 1.6, 2.2, 0.45))
    pulse = 1 + 0.12 * abs(math.sin(t * 5))
    glow(im, W // 2, 780, 260, (255, 120, 200), 120, 70)
    put_center(im, comment_icon(380), W // 2, 780, pulse)
    for i, t0 in enumerate(cues.BUBBLES5):
        v = t - t0
        if v < 0:
            continue
        txt = ['Plush Pepe!', "Durov's Cap", 'Heart Locket', 'Snoop Dogg', 'Lol Pop', 'Mighty Arm'][i]
        x = 270 if i % 2 == 0 else W - 270
        y = 1010 + (i // 2) * 122
        put_center(im, comment_bubble(txt), x, y, spring(v * 1.8, 2.4, 0.5))
    if t >= T['each']:
        v = t - T['each']
        text(im, 'КАЖДЫЙ КОММЕНТАРИЙ', W // 2, 1530, 72, (140, 255, 170), scale=1 + 0.8 * (1 - eo(v / 0.15)), rot=-3)
        text(im, 'СЧИТАЕТСЯ!', W // 2, 1630, 100, (140, 255, 170), scale=1 + 0.8 * (1 - eo((v - 0.08) / 0.15)), rot=-3)
        # стрелка к кнопке комментариев справа
        ph = math.sin(t * 8)
        ax, ay = W - 120 + 20 * ph, 1420
        ImageDraw.Draw(im).polygon(((ax - 110, ay - 34), (ax - 20, ay - 34), (ax - 20, ay - 80), (ax + 70, ay),
                                    (ax - 20, ay + 80), (ax - 20, ay + 34), (ax - 110, ay + 34)),
                                   fill=GOLD, outline=(20, 8, 40), width=8)
        flash(im, t, T['each'], 0.12)
    end = DUR - t
    if end < 0.5:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.5)))))
    return im


def render_at(t):
    s = scene_at(t)
    im = {'L1': s1, 'L2': s2, 'L3': s3, 'L4': s4, 'L5': s5}[s](t)
    if s not in ('L1', 'L3'):
        flash(im, t, V[s], 0.12)
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
