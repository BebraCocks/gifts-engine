"""Третий ролик-призыв: поп-арт комикс (жёлтый фон, растровые точки, толстые контуры, наклейки, вспышки «БАМ!»).
Всё кодом; Мисед — только оригинальная ава в круге-наклейке.

    python -B projects/61-missed-comments-3/render.py --frames 1.0,6.0
    python -B projects/61-missed-comments-3/render.py --build name.mp4
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
INK = (18, 14, 20)
YEL, RED, BLUE, GRN, PINK, WHITE = (255, 214, 50), (240, 50, 60), (40, 110, 240), (60, 200, 110), (255, 110, 180), (255, 255, 255)


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


@functools.lru_cache(6)
def halftone(base, dot, step=34):
    """Фон с растровыми точками, как в комиксе."""
    im = Image.new('RGBA', (W, H), base + (255,))
    d = ImageDraw.Draw(im)
    for yi, y in enumerate(range(0, H + step, step)):
        for x in range(-step, W + step, step):
            xx = x + (step // 2 if yi % 2 else 0)
            r = 4 + 5 * (y / H)
            d.ellipse((xx - r, y - r, xx + r, y + r), fill=dot + (255,))
    return im


def bg(t, base=YEL, dot=(255, 190, 30)):
    im = halftone(base, dot).copy()
    # «скоростные» лучи из центра, медленно крутятся
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(14):
        a0 = t * 0.15 + i * 2 * math.pi / 14
        d.polygon((W / 2, H / 2, W / 2 + 1800 * math.cos(a0), H / 2 + 1800 * math.sin(a0),
                   W / 2 + 1800 * math.cos(a0 + 0.16), H / 2 + 1800 * math.sin(a0 + 0.16)), fill=(255, 255, 255, 46))
    im.alpha_composite(lay)
    return im


def ctext(im, s, x, y, size, col=WHITE, scale=1.0, a=1.0, rot=0, stroke=14, shadow=True):
    """Комиксный текст: заливка + толстый чёрный контур + смещённая тень."""
    f = font('Heavy', max(8, int(size * scale)))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    if shadow:
        d.text((x + 10, y + 12), s, font=f, anchor='mm', fill=INK + (int(255 * a),), stroke_width=stroke, stroke_fill=INK + (int(255 * a),))
    d.text((x, y), s, font=f, anchor='mm', fill=col + (int(255 * a),), stroke_width=stroke, stroke_fill=INK + (int(255 * a),))
    if rot:
        lay = lay.rotate(rot, center=(x, y), resample=Image.BICUBIC)
    im.alpha_composite(lay)


def burst(im, cx, cy, r, col=RED, n=14, rot=0.0, txt=None, tsize=90, tcol=WHITE, scale=1.0):
    """Звезда-вспышка «БАМ!»."""
    r *= scale
    if r < 4:
        return
    pts = []
    for i in range(2 * n):
        a = rot + i * math.pi / n
        rr = r if i % 2 == 0 else r * 0.68
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d = ImageDraw.Draw(im)
    d.polygon([(x + 12, y + 14) for x, y in pts], fill=INK)
    d.polygon(pts, fill=col, outline=INK)
    d.line(pts + [pts[0]], fill=INK, width=10, joint='curve')
    if txt:
        ctext(im, txt, cx, cy, tsize, tcol, scale=scale, stroke=10, shadow=False)


def sticker(src, border=16):
    """Белая кайма + чёрный контур вокруг непрозрачной части — вид наклейки."""
    a = src.getchannel('A')
    pad = border + 10
    big = Image.new('L', (src.width + 2 * pad, src.height + 2 * pad), 0)
    big.paste(a, (pad, pad))
    wb = big.filter(ImageFilter.MaxFilter(2 * border + 1))
    ob = wb.filter(ImageFilter.MaxFilter(9))
    out = Image.new('RGBA', big.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', big.size, INK + (255,)), (0, 0), ob)
    out.paste(Image.new('RGBA', big.size, WHITE + (255,)), (0, 0), wb)
    out.alpha_composite(src, (pad, pad))
    return out


@functools.lru_cache(8)
def avatar(size):
    im = Image.open(HERE / 'refs' / 'missed_original.jpg').convert('RGB')
    im = im.crop((60, 0, 600, 540)).resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4, size * 4), fill=255)
    m = m.resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size)); out.paste(im, (0, 0), m)
    return sticker(out, 18)


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
def gift_sticker(name, size):
    m = G.models(name)[-1]['name']
    return sticker(Image.open(G.model_png(name, m, 512)).convert('RGBA').resize((size, size), Image.LANCZOS), 12)


def gift_anim(name, model, t, size):
    return lottie.frame(G.model_file(name, model, 'tgs'), t, size=size)


@functools.lru_cache(16)
def bubble(txt, w=760, h=300, size=120):
    """Комиксное облачко-реплика с хвостиком."""
    im = Image.new('RGBA', (w + 40, h + 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 26, w + 26, h + 26), 120, fill=INK)
    d.polygon(((140 + 14, h - 10 + 14), (110 + 14, h + 100 + 14), (260 + 14, h - 10 + 14)), fill=INK)
    d.rounded_rectangle((10, 10, w + 10, h + 10), 120, fill=WHITE, outline=INK, width=12)
    d.polygon(((140, h - 6), (110, h + 100), (260, h - 6)), fill=WHITE, outline=INK)
    d.line(((140, h + 4), (110, h + 100), (260, h + 4)), fill=INK, width=12)
    d.rectangle((150, h - 14, 250, h + 6), fill=WHITE)
    d.text((10 + w // 2, 10 + h // 2), txt, font=font('Heavy', size), anchor='mm', fill=INK)
    return im


def comment_icon(size, fill=WHITE):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    d.ellipse((s * .06, s * .08, s * .94, s * .78), fill=fill, outline=INK, width=max(4, s // 25))
    d.polygon(((s * .25, s * .66), (s * .16, s * .94), (s * .5, s * .74)), fill=fill, outline=INK)
    for k in range(3):
        cx = s * (0.32 + 0.18 * k)
        d.ellipse((cx - s * .05, s * .38, cx + s * .05, s * .48), fill=INK)
    return im


def flash(im, t, t0, dur=0.1, col=WHITE):
    u = t - t0
    if 0 <= u < dur:
        im.alpha_composite(Image.new('RGBA', (W, H), col + (int(220 * (1 - u / dur)),)))


def shake(t, hits, amp=22, dur=0.3):
    for h in hits:
        u = t - h
        if 0 <= u < dur:
            k = 1 - u / dur
            return int(amp * k * math.sin(u * 95)), int(amp * k * math.cos(u * 81))
    return 0, 0


# ------------------------------------------------------------------ сцены
def s1(t):
    """Хук: огромное облачко с одной точкой → наезд → «БАМ!» → NFT."""
    im = bg(t)
    u = t - V['L1']
    if t < T['boom']:
        z = 1 + 0.5 * eo(u / (T['boom'] - V['L1']))
        put(im, bubble('', 760, 420), W // 2, 900, z * spring(u * 2, 2.4, 0.5))
        r = 34 * z * (1 + 0.15 * abs(math.sin(t * 14)))
        ImageDraw.Draw(im).ellipse((W / 2 - r, 900 - 50 * z - r, W / 2 + r, 900 - 50 * z + r), fill=INK)
        ctext(im, 'ОДНА ТОЧКА', W // 2, 300, 120, RED, scale=spring(u * 1.8, 2.4, 0.45), rot=-4)
        ctext(im, 'в комментариях…', W // 2, 1500, 80, WHITE, a=eo((u - 0.3) / 0.3))
    else:
        v = t - T['boom']
        dx, dy = shake(t, [T['boom']], 30, 0.4)
        burst(im, W // 2 + dx, 900 + dy, 560, RED, 16, t * 0.4, scale=spring(v * 2, 2.4, 0.5))
        burst(im, W // 2 + dx, 900 + dy, 420, YEL, 12, -t * 0.6, scale=spring((v - 0.05) * 2, 2.4, 0.5))
        put(im, sticker(gift_anim('Heart Locket', 'Royal Flush', v, 420), 14), W // 2 + dx, 900 + dy,
            spring((v - 0.1) * 1.6, 2.2, 0.45), rot=6 * math.sin(t * 3))
        ctext(im, '= NFT', W // 2, 300, 160, WHITE, scale=spring(v * 1.8, 2.4, 0.45), rot=-5)
        ctext(im, 'МОЖЕТ СТАТЬ ТВОИМ!', W // 2, 1520, 84, BLUE, scale=spring((v - 0.3) * 1.8, 2.4, 0.45), rot=3)
        flash(im, t, T['boom'], 0.12)
    return im


def s2(t):
    u = t - V['L2']
    im = bg(t, (255, 120, 160), (240, 80, 130))
    dx, dy = shake(t, cues.SLAMS, 18, 0.25)
    if t < T['self0']:
        put(im, avatar(380), 300, 520, spring(u * 1.6, 2.2, 0.45), rot=-6)
        put(im, bubble('Дарю NFT', 620, 240, 92), 680, 300, spring((u - 0.2) * 1.8, 2.4, 0.5))
        ctext(im, 'ЗА КОММЕНТЫ', W // 2, 1050, 110, YEL, scale=spring((u - 0.6) * 1.8, 2.4, 0.45), rot=-3)
        for i in range(5):
            put(im, comment_icon(150), 140 + i * 200, 1400 + 20 * math.sin(t * 4 + i), spring((u - 0.8 - i * 0.1) * 2, 2.4, 0.5))
        return im
    if t < T['sell']:
        v = t - T['self0']
        ctext(im, 'СЕБЕ', W // 2 + dx, 420 + dy, 170, WHITE, scale=spring(v * 2, 2.4, 0.45), rot=-4)
        burst(im, W // 2 + dx, 960 + dy, 380, BLUE, 12, t * 0.3, txt='0', tsize=330, scale=spring((v - 0.1) * 2, 2.4, 0.45))
        ctext(im, 'НИЧЕГО!', W // 2, 1480, 140, YEL, scale=spring((v - 0.3) * 2, 2.4, 0.45), rot=4)
        flash(im, t, T['self0'], 0.08)
        return im
    if t < T['give']:
        v = t - T['sell']
        put(im, sticker(gift_anim('Mighty Arm', 'T800', v, 420), 14), W // 2 + dx, 800 + dy, spring(v * 2, 2.4, 0.5), rot=-8)
        ctext(im, 'ПРОДАМ!', W // 2, 300, 170, WHITE, scale=spring(v * 2, 2.4, 0.45), rot=-5)
        for i in range(10):
            rr = random.Random(i)
            x = W / 2 + rr.uniform(-450, 450)
            y = 1150 + (v * rr.uniform(400, 900)) % 650
            d = ImageDraw.Draw(im)
            d.ellipse((x - 40, y - 40, x + 40, y + 40), fill=YEL, outline=INK, width=8)
            d.text((x, y), '$', font=font('Heavy', 50), anchor='mm', fill=INK)
        flash(im, t, T['sell'], 0.08)
        return im
    v = t - T['give']
    ctext(im, 'РАЗДАМ ВАМ!', W // 2, 300, 128, YEL, scale=spring(v * 2, 2.4, 0.45), rot=-4)
    for i in range(5):
        put(im, comment_icon(170), 130 + i * 205, 1450)
    for i in range(10):
        rr = random.Random(i + 30)
        k = cl((v - i * 0.12) / 0.7)
        if k <= 0:
            continue
        tx = 130 + (i % 5) * 205
        x = rr.uniform(100, W - 100) * (1 - k) + tx * k
        y = 500 * (1 - k) + 1300 * k - 220 * math.sin(math.pi * k)
        put(im, gift_sticker(cues.CHEAP[i], 160), x, y, 1 - 0.25 * k, rot=30 * (1 - k))
    flash(im, t, T['give'], 0.08)
    return im


def s3(t):
    im = bg(t, (120, 210, 255), (70, 170, 240))
    dx, dy = shake(t, T['tier'], 18, 0.25)
    ctext(im, 'НАГРАДЫ', W // 2, 150, 120, YEL, rot=-3)
    for i, ((cnt, name, model), t0) in enumerate(zip(cues.TIERS, T['tier'])):
        v = t - t0
        if v < 0:
            continue
        y = 470 + i * 480
        x = W // 2 + (1 if i % 2 else -1) * 1200 * (1 - eo(v / 0.25))
        rot = [-4, 3, -2][i]
        card = Image.new('RGBA', (980, 420), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        cd.rounded_rectangle((16, 20, 976, 416), 50, fill=INK)
        col = [RED, GRN, PINK][i]
        cd.rounded_rectangle((0, 0, 960, 396), 50, fill=col, outline=INK, width=12)
        cd.text((420, 120), cnt, font=font('Heavy', 96), anchor='lm', fill=WHITE, stroke_width=8, stroke_fill=INK)
        cd.text((420, 215), 'комментов', font=font('Heavy', 52), anchor='lm', fill=INK)
        cd.text((420, 305), name, font=font('Heavy', 58), anchor='lm', fill=WHITE, stroke_width=6, stroke_fill=INK)
        g = sticker(gift_anim(name, model, v, 320), 10)
        card.alpha_composite(g, (200 - g.width // 2, 198 - g.height // 2))
        put(im, card, x + dx, y + dy, 1.0, rot=rot)
        if v < 0.6:
            burst(im, x + 440, y - 190, 90, YEL, 10, t, txt='БАМ!', tsize=38, tcol=INK, scale=spring(v * 2.5, 2.4, 0.5))
        flash(im, t, t0, 0.08)
    return im


def s4(t):
    im = bg(t, (140, 230, 140), (100, 200, 110))
    u = t - V['L4']
    if t < T['top']:
        ctext(im, 'ПИШИ ЧТО УГОДНО!', W // 2, 200, 84, WHITE, scale=spring(u * 1.8, 2.4, 0.45), rot=-3)
        items = [('огонь', T['word'], 300, 560), (':)', T['smile'], 780, 820), ('.', T['dot'], 360, 1130)]
        for txt, t0, x, y in items:
            v = t - t0
            if v < 0:
                continue
            put(im, bubble(txt, 460, 230, 110 if txt != '.' else 160), x, y, spring(v * 2, 2.4, 0.5), rot=-5 if x < 540 else 5)
        if t >= T['dot']:
            v = t - T['dot']
            burst(im, 800, 1180, 170, RED, 12, t, txt='ДАЖЕ!', tsize=62, scale=spring(v * 2.4, 2.4, 0.5))
        if t >= T['ok']:
            v = t - T['ok']
            sc = 1 + 1.2 * (1 - eo(v / 0.15))
            ctext(im, 'ЗАСЧИТАНО!', W // 2, 1560, 130, GRN, scale=sc, rot=-8)
            flash(im, t, T['ok'], 0.08)
    else:
        v = t - T['top']
        ctext(im, 'КТО БОЛЬШЕ ВСЕХ —', W // 2, 220, 84, WHITE, scale=spring(v * 1.8, 2.4, 0.45))
        ctext(im, 'ТОМУ ПОДАРОК!', W // 2, 340, 110, YEL, scale=spring((v - 0.15) * 1.8, 2.4, 0.45), rot=-3)
        # пьедестал
        d = ImageDraw.Draw(im)
        for i, (x, h_, col, lab) in enumerate(((270, 320, BLUE, '2'), (540, 480, RED, '1'), (810, 220, PINK, '3'))):
            k = eo((v - 0.1 * i) / 0.4)
            top = 1700 - h_ * k
            if top + 14 < 1700:                                  # столбик ещё не вырос — тень не рисуем
                d.rectangle((x - 140 + 12, top + 14, x + 140 + 12, 1700), fill=INK)
            if top < 1690:
                d.rectangle((x - 140, top, x + 140, 1700), fill=col, outline=INK, width=10)
            d.text((x, top + 70), lab, font=font('Heavy', 110), anchor='mm', fill=WHITE, stroke_width=8, stroke_fill=INK)
            put(im, comment_icon(150), x, top - 90 + 8 * math.sin(t * 4 + i), k)
        # подарок над первым местом
        bx = Image.new('RGBA', (380, 380), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bx)
        bd.rounded_rectangle((30, 130, 350, 370), 26, fill=BLUE, outline=INK, width=12)
        bd.rectangle((160, 130, 220, 370), fill=YEL, outline=INK, width=6)
        bd.rounded_rectangle((10, 80, 370, 160), 22, fill=(70, 140, 255), outline=INK, width=12)
        bd.rectangle((160, 80, 220, 160), fill=YEL, outline=INK, width=6)
        bd.text((190, 260), '?', font=font('Heavy', 170), anchor='mm', fill=WHITE, stroke_width=8, stroke_fill=INK)
        put(im, bx, 540, 810 + 14 * math.sin(t * 3), spring((v - 0.5) * 1.6, 2.2, 0.45), rot=6 * math.sin(t * 2))
        burst(im, 820, 640, 150, YEL, 10, t, txt='КРУТОЙ!', tsize=52, tcol=INK, scale=spring((v - 0.9) * 2, 2.4, 0.5))
    return im


def s5(t):
    im = bg(t, (255, 160, 60), (240, 120, 40))
    u = t - V['L5']
    ctext(im, 'ЖМИ!', W // 2, 230, 200, RED, scale=spring(u * 2, 2.4, 0.45), rot=-5)
    press = max((1 - eo((t - p) / 0.25)) if 0 <= t - p < 0.25 else 0 for p in cues.PRESS)
    put(im, comment_icon(460), W // 2, 820, 1 - 0.12 * press + 0.05 * math.sin(t * 5))
    # рука-указатель жмёт на иконку
    hx, hy = W // 2 + 170, 1010 - 60 * press
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((hx - 50 + 10, hy + 10, hx + 50 + 10, hy + 230 + 10), 46, fill=INK)
    d.rounded_rectangle((hx - 50, hy, hx + 50, hy + 230), 46, fill=WHITE, outline=INK, width=10)
    d.rounded_rectangle((hx - 50, hy + 120, hx + 150, hy + 330), 60, fill=WHITE, outline=INK, width=10)
    if t >= T['write']:
        v = t - T['write']
        ctext(im, 'ПИШИ СЕЙЧАС!', W // 2 - 40, 1440, 104, WHITE, scale=spring(v * 2, 2.4, 0.45), rot=3)
    if t >= T['fast']:
        v = t - T['fast']
        frac = eo(v / 1.6)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((100 + 12, 1590 + 14, W - 100 + 12, 1700 + 14), 55, fill=INK)
        d.rounded_rectangle((100, 1590, W - 100, 1700), 55, fill=WHITE, outline=INK, width=10)
        d.rounded_rectangle((112, 1602, 112 + (W - 224) * frac, 1688), 45, fill=GRN)
        ctext(im, 'РАЗДАЧА БЛИЖЕ!', W // 2, 1645, 60, WHITE, stroke=8, shadow=False)
        ax, ay = W - 100 + 20 * math.sin(t * 8), 1210
        d.polygon(((ax - 100 + 10, ay - 30 + 12), (ax - 20 + 10, ay - 30 + 12), (ax - 20 + 10, ay - 72 + 12), (ax + 60 + 10, ay + 12),
                   (ax - 20 + 10, ay + 72 + 12), (ax - 20 + 10, ay + 30 + 12), (ax - 100 + 10, ay + 30 + 12)), fill=INK)
        d.polygon(((ax - 100, ay - 30), (ax - 20, ay - 30), (ax - 20, ay - 72), (ax + 60, ay),
                   (ax - 20, ay + 72), (ax - 20, ay + 30), (ax - 100, ay + 30)), fill=RED, outline=INK, width=8)
    end = DUR - t
    if end < 0.5:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.5)))))
    return im


def render_at(t):
    s = scene_at(t)
    im = {'L1': s1, 'L2': s2, 'L3': s3, 'L4': s4, 'L5': s5}[s](t)
    if s != 'L1':
        flash(im, t, V[s], 0.1)
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
