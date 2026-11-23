"""Картинка «Подарка по заслугам» (2D, всё кодом). Кадр — чистая функция времени.

    python -B projects/58-missed-new-year/render.py --frames 1.0,12.5,30.2   # пробные кадры в build/review
    python -B projects/58-missed-new-year/render.py --build name.mp4          # полный ролик со звуком build/mix.wav
"""
import functools
import math
import random
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import chars  # noqa: E402
import cues  # noqa: E402
from timeline import T, V, D, DUR, scene_at  # noqa: E402

W, H, FPS = 1080, 1920, 60
FD = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'


@functools.lru_cache(64)
def font(w, s):
    return ImageFont.truetype(str(FD / f'SF-Pro-Text-{w}.otf'), s)


def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3


def spring(x, f=2.0, z=0.42):
    if x <= 0:
        return 0.0
    w = 2 * math.pi * f; wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


def bump(x, f=6, dec=7):
    return 0.0 if x <= 0 else math.exp(-dec * x) * math.sin(2 * math.pi * f * x)


def talking(k, t):
    """Губы: открыт/закрыт, пока звучит реплика k."""
    if k not in V:
        return False
    u = t - V[k]
    return 0 <= u < D[k] - 0.05 and int(u * 9) % 2 == 0


# ------------------------------------------------------------------ фоны
@functools.lru_cache(16)
def gradient(top, bot):
    a = np.linspace(0, 1, H)[:, None, None]
    g = np.array(top, np.float32) * (1 - a) + np.array(bot, np.float32) * a
    return Image.fromarray(np.repeat(g, W, 1).astype(np.uint8), 'RGB').convert('RGBA')


FLAKES = [(random.Random(i).uniform(0, W), random.Random(i + 99).uniform(0, H), random.Random(i + 7).uniform(40, 120),
           random.Random(i + 3).uniform(3, 9), random.Random(i + 5).uniform(0, 6.28)) for i in range(90)]


def snow(im, t, k=1.0, alpha=200):
    d = ImageDraw.Draw(im)
    for x0, y0, sp, r, ph in FLAKES[:int(90 * k)]:
        y = (y0 + sp * t) % (H + 40) - 20
        x = x0 + 18 * math.sin(t * 0.8 + ph)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, alpha))


def lights(im, t, y=70, n=11, amp=40):
    d = ImageDraw.Draw(im)
    cols = [(255, 90, 90), (255, 210, 80), (110, 220, 140), (120, 170, 255)]
    pts = [(x, y + amp * math.sin(x / W * math.pi)) for x in np.linspace(-20, W + 20, 60)]
    d.line(pts, fill=(30, 40, 30), width=4)
    for i in range(n):
        x = 50 + i * (W - 100) / (n - 1)
        yy = y + amp * math.sin(x / W * math.pi) + 18
        c = cols[i % 4]
        on = 0.55 + 0.45 * math.sin(t * 3 + i * 1.7)
        g = Image.new('RGBA', (90, 90), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((15, 15, 75, 75), fill=c + (int(110 * on),))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(12)), (int(x - 45), int(yy - 45)))
        d.ellipse((x - 11, yy - 14, x + 11, yy + 14), fill=c + (255,), outline=(30, 30, 40), width=3)


def caption(im, text, y, a=1.0, size=64, col=(255, 255, 255)):
    f = font('Heavy', size)
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        yy = y + i * (size + 14)
        ImageDraw.Draw(im).text((W // 2, yy), ln, font=f, anchor='mm', fill=col + (int(255 * a),),
                                stroke_width=8, stroke_fill=(15, 15, 30, int(255 * a)))


# ------------------------------------------------------------------ персонажи
_CH = {}


def ch(who, **pose):
    key = (who, tuple(sorted(pose.items())))
    if key not in _CH:
        _CH[key] = chars.get(who, **pose)
    return _CH[key]


def put_char(im, sprite, cx, bottom, scale=1.0, dy=0.0, sq=0.0):
    w, h = int(sprite.width * scale * (1 + sq)), int(sprite.height * scale * (1 - sq))
    s = sprite.resize((w, h), Image.BILINEAR)
    im.alpha_composite(s, (int(cx - w / 2), int(bottom - h + dy)))


def dimon_pose(t, base, talk_key=None, **extra):
    p = dict(base); p.update(extra)
    if talk_key and talking(talk_key, t):
        p['mouth'] = 'open' if p.get('mouth') not in ('grin', 'shock') else p['mouth']
    p['blink'] = 1 if (t % 3.7) < 0.09 else 0
    return p


@functools.lru_cache(8)
def missed_avatar(size):
    im = Image.open(HERE / 'refs' / 'missed_original.jpg').convert('RGB')
    im = im.crop((60, 0, 600, 540)).resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size * 4, size * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size * 4, size * 4), fill=255)
    m = m.resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size)); out.paste(im, (0, 0), m)
    return out


@functools.lru_cache(4)
def missed_cover(w, h):
    im = Image.open(HERE / 'refs' / 'missed_original.jpg').convert('RGB')
    k = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
    return im.crop(((im.width - w) // 2, 0, (im.width - w) // 2 + w, h)).convert('RGBA')


# ------------------------------------------------------------------ подарки
SNOOP = None


def snoop(t, size):
    global SNOOP
    if SNOOP is None:
        SNOOP = G.model_file('Snoop Dogg', 'Goldizzle', 'tgs')
    return lottie.frame(SNOOP, t, size=size)


OLEG_GIFTS = ['Plush Pepe', "Durov's Cap", 'Precious Peach', 'Heart Locket', 'Swiss Watch', 'Eternal Rose']


@functools.lru_cache(16)
def gift_png(name, size):
    model = G.models(name)[-1]['name']
    return Image.open(G.model_png(name, model, 512)).convert('RGBA').resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ телефон / чат
def rrect(im, box, r, fill, outline=None, width=0, shadow=True):
    if shadow:
        x0, y0, x1, y1 = box
        sh = Image.new('RGBA', (int(x1 - x0) + 80, int(y1 - y0) + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((40, 50, x1 - x0 + 40, y1 - y0 + 50), r, fill=(0, 0, 0, 110))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (int(x0 - 40), int(y0 - 40)))
    ImageDraw.Draw(im).rounded_rectangle(box, r, fill=fill, outline=outline, width=width)


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ''
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    for w_ in words:
        test = (cur + ' ' + w_).strip()
        if d.textlength(test, font=f) <= maxw:
            cur = test
        else:
            lines.append(cur); cur = w_
    lines.append(cur)
    return lines


def chat(im, t, msgs, typing, box, me_col=(70, 130, 240)):
    """msgs: [(t_появления, 'me'|'missed', текст)], typing: [(t0, t1)]. Сообщения растут снизу вверх."""
    x0, y0, x1, y1 = box
    rrect(im, box, 46, (18, 22, 36, 255), outline=(60, 70, 100, 255), width=4)
    d = ImageDraw.Draw(im)
    av = missed_avatar(96)
    speak = any(0 <= t - V[k] < D[k] for k in ('M1', 'M2', 'M3', 'M4', 'M5'))
    if speak:                                           # Мисед «говорит»: пульсирующее кольцо вокруг аватарки
        r = 58 + 6 * abs(math.sin(t * 9))
        g = Image.new('RGBA', (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((100 - r, 100 - r, 100 + r, 100 + r), outline=(110, 180, 255, 230), width=8)
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(2)), (x0 + 36 + 48 - 100, y0 + 30 + 48 - 100))
    im.alpha_composite(av, (x0 + 36, y0 + 30))
    d.text((x0 + 150, y0 + 44), 'Мисед', font=font('Bold', 44), fill=(255, 255, 255))
    cx_ = x0 + 150 + d.textlength('Мисед', font=font('Bold', 44)) + 26
    d.ellipse((cx_ - 17, y0 + 50, cx_ + 17, y0 + 84), fill=(60, 150, 255))
    d.line((cx_ - 8, y0 + 67, cx_ - 2, y0 + 74, cx_ + 9, y0 + 59), fill=(255, 255, 255), width=5)
    online = any(a <= t < b for a, b in typing)
    d.text((x0 + 150, y0 + 98), 'печатает…' if online else 'в сети', font=font('Medium', 32),
           fill=(120, 180, 255) if online else (140, 150, 170))
    d.line((x0 + 20, y0 + 156, x1 - 20, y0 + 156), fill=(50, 58, 84), width=3)
    f = font('Semibold', 42)
    items = [m for m in msgs if t >= m[0]]
    for a, b in typing:
        if a <= t < b:
            items.append((a, 'typing', ''))
    y = y1 - 40
    for (ta, who, text) in reversed(items):
        u = t - ta
        s = spring(u * 1.4, 2.2, 0.5) if u < 1.2 else 1.0
        if who == 'typing':
            bw, bh, lines = 150, 86, []
        else:
            lines = wrap(text, f, (x1 - x0) * 0.64)
            bw = max(ImageDraw.Draw(im).textlength(ln, font=f) for ln in lines) + 64
            bh = len(lines) * 54 + 44
        y -= bh + 22
        if y < y0 + 170:
            break
        me = who == 'me'
        bx = x1 - 36 - bw if me else x0 + 36
        col = me_col if me else (44, 50, 72)
        if who == 'missed' and text.startswith('!'):
            col = (150, 30, 50)
        bub = Image.new('RGBA', (int(bw) + 2, int(bh) + 2), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((0, 0, bw, bh), 34, fill=col + (255,))
        if who == 'typing':
            for i in range(3):
                ph = math.sin(t * 9 - i * 0.9)
                bd.ellipse((34 + i * 32, 36 - 6 * ph, 54 + i * 32, 56 - 6 * ph), fill=(200, 210, 230))
        else:
            for i, ln in enumerate(lines):
                bd.text((32, 22 + i * 54), ln.lstrip('!'), font=f, fill=(255, 255, 255))
        if s < 0.999:
            ww, hh = max(1, int(bub.width * s)), max(1, int(bub.height * s))
            bub = bub.resize((ww, hh), Image.BILINEAR)
            ox = bx + (bw - ww if me else 0)
            im.alpha_composite(bub, (int(ox), int(y + bh - hh)))
        else:
            im.alpha_composite(bub, (int(bx), int(y)))


# ------------------------------------------------------------------ сцены
def flash(im, t, t0, dur=0.14):
    u = t - t0
    if 0 <= u < dur:
        im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(200 * (1 - u / dur)))))


def profile_card(im, t, name, avatar, count, gifts=None, vanish=None, scale=1.0, y0=360, count_col=(255, 80, 90)):
    cw, chh = 900, 1130
    card = Image.new('RGBA', (cw + 80, chh + 80), (0, 0, 0, 0))
    rrect(card, (40, 40, cw + 40, chh + 40), 60, (24, 30, 52, 255), outline=(70, 84, 130, 255), width=4)
    d = ImageDraw.Draw(card)
    card.alpha_composite(avatar, (40 + cw // 2 - avatar.width // 2, 90))
    d.text((40 + cw // 2, 90 + avatar.height + 50), name, font=font('Heavy', 64), anchor='mm', fill=(255, 255, 255))
    d.text((90, 520), 'Подарки', font=font('Bold', 40), fill=(150, 165, 200))
    for i in range(6):
        gx, gy = 90 + (i % 3) * 270, 580 + (i // 3) * 220
        d.rounded_rectangle((gx, gy, gx + 240, gy + 200), 30, outline=(70, 84, 130), width=4)
        if gifts and i < len(gifts):
            g = gift_png(gifts[i], 180)
            if vanish:
                u = t - vanish[i]
                if u > 0:
                    k = 1 - eo(u / 0.35)
                    if k <= 0.01:
                        g = None
                    else:
                        g = g.resize((max(1, int(180 * k)), max(1, int(180 * k))))
                        g.putalpha(g.getchannel('A').point(lambda v: int(v * k)))
                    for j in range(14):                            # снежинки-осколки
                        rr = random.Random(i * 31 + j)
                        px = gx + 120 + rr.uniform(-90, 90) + rr.uniform(-60, 60) * u
                        py = gy + 100 - rr.uniform(80, 260) * u
                        a = int(255 * cl(1 - u / 1.1))
                        if a > 0:
                            rs = rr.uniform(4, 10)
                            d.ellipse((px - rs, py - rs, px + rs, py + rs), fill=(220, 235, 255, a))
            if g is not None:
                card.alpha_composite(g, (gx + 120 - g.width // 2, gy + 100 - g.height // 2))
    d.text((40 + cw // 2, 1110), f'{count} {plural(count)}', font=font('Heavy', 72), anchor='mm', fill=count_col)
    if scale != 1.0:
        card = card.resize((int(card.width * scale), int(card.height * scale)), Image.BILINEAR)
    im.alpha_composite(card, (W // 2 - card.width // 2, int(y0 - 40 * scale)))


def plural(n):
    return 'подарок' if n % 10 == 1 and n % 100 != 11 else 'подарка' if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 'подарков'


@functools.lru_cache(4)
def head_avatar(who, size):
    sp = chars.get(who, **({'mouth': 'flat', 'eyes': 'half'} if who == 'dimon' else {'mouth': 'smirk', 'eyes': 'half'}))
    hd = sp.crop((110, 60, 590, 560)).resize((size, size), Image.LANCZOS)
    bg = Image.new('RGBA', (size, size), (70, 110, 200, 255) if who == 'dimon' else (110, 50, 60, 255))
    bg.alpha_composite(hd)
    m = Image.new('L', (size, size), 0); ImageDraw.Draw(m).ellipse((0, 0, size, size), fill=255)
    out = Image.new('RGBA', (size, size)); out.paste(bg, (0, 0), m)
    return out


def scene1(t):
    im = gradient((14, 20, 46), (40, 30, 70)).copy()
    snow(im, t, 0.6, 140)
    lights(im, t)
    u = t - T['s1']
    sc = 1.0 + 0.05 * eo(u / 4)
    profile_card(im, t, 'Димон', head_avatar('dimon', 260), 0, scale=sc, y0=330 + 8 * bump(u - 1.6))
    caption(im, 'У Димона — ни одного NFT', 1660, eo((t - V['N1']) / 0.3), 62)
    return im


@functools.lru_cache(2)
def room_bg():
    im = gradient((40, 36, 84), (22, 20, 48)).copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1420, W, H), fill=(60, 42, 50))
    d.line((0, 1420, W, 1420), fill=(30, 22, 30), width=8)
    d.rounded_rectangle((70, 260, 430, 760), 24, fill=(18, 30, 70), outline=(110, 90, 80), width=14)  # окно
    d.line((250, 260, 250, 760), fill=(110, 90, 80), width=10); d.line((70, 510, 430, 510), fill=(110, 90, 80), width=10)
    d.ellipse((300, 300, 380, 380), fill=(240, 240, 220))
    return im


def tree(im, t, cx=780, base=1450):
    d = ImageDraw.Draw(im)
    d.rectangle((cx - 30, base - 60, cx + 30, base), fill=(110, 70, 40), outline=(30, 20, 20), width=5)
    for i, (w_, y) in enumerate(((300, base - 60), (240, base - 300), (170, base - 520))):
        d.polygon(((cx - w_, y), (cx + w_, y), (cx, y - 330)), fill=(40 + i * 10, 130 + i * 12, 80), outline=(20, 40, 30))
    d.regular_polygon((cx, base - 870, 50), 5, rotation=-90, fill=(255, 210, 60), outline=(120, 80, 10))
    cols = [(255, 90, 90), (255, 210, 80), (120, 180, 255), (255, 255, 255)]
    for i in range(22):
        rr = random.Random(i)
        y = rr.uniform(base - 820, base - 80)
        frac = (y - (base - 870)) / 800
        x = cx + rr.uniform(-1, 1) * 280 * frac
        on = 0.5 + 0.5 * math.sin(t * 4 + i)
        c = cols[i % 4]
        d.ellipse((x - 12, y - 12, x + 12, y + 12), fill=tuple(int(v * (0.5 + 0.5 * on)) for v in c))


def scene2(t):
    im = room_bg().copy()
    snow_l = Image.new('RGBA', (W, H)); snow(snow_l, t, 0.35, 220)
    win = Image.new('L', (W, H), 0); ImageDraw.Draw(win).rectangle((84, 274, 416, 746), fill=255)
    im.paste(snow_l, (0, 0), ImageChops.multiply(snow_l.getchannel('A'), win))
    tree(im, t)
    y_i = max(i for i, yt in enumerate(cues.YEARS) if t >= yt) if t >= cues.YEARS[0] else 0
    u = t - cues.YEARS[y_i]
    poses = [dict(eyes='open', mouth='smile'), dict(eyes='half', mouth='flat'), dict(eyes='half', mouth='sad')]
    sprite = ch('dimon', **poses[y_i])
    put_char(im, sprite, 330, 1640, 0.95, dy=-10 * abs(math.sin(t * 2)))
    # письмо улетает к Деду Морозу
    if u < 1.2:
        ex, ey = 330 + 300 * eo(u / 1.2), 1000 - 900 * eo(u / 1.2)
        env_ = Image.new('RGBA', (170, 120), (0, 0, 0, 0))
        ed = ImageDraw.Draw(env_)
        ed.rectangle((5, 5, 165, 115), fill=(250, 245, 230), outline=(40, 30, 30), width=5)
        ed.line((5, 5, 85, 65, 165, 5), fill=(40, 30, 30), width=5)
        ed.ellipse((70, 50, 100, 80), fill=(210, 40, 50))
        env_ = env_.rotate(20 * math.sin(u * 6), expand=True)
        im.alpha_composite(env_, (int(ex - 85), int(ey - 60)))
    # пустое место под ёлкой
    if u > 0.9:
        a = cl((u - 0.9) / 0.3)
        d = ImageDraw.Draw(im)
        d.ellipse((620, 1440, 940, 1500), outline=(255, 255, 255, int(120 * a)), width=4)
        d.text((780, 1560), 'пусто', font=font('Heavy', 56), anchor='mm', fill=(255, 255, 255, int(220 * a)),
               stroke_width=6, stroke_fill=(20, 20, 40, int(220 * a)))
    yr = ['2023', '2024', '2025'][y_i]
    s = 1 + 0.6 * (1 - spring(u * 1.6, 2.4, 0.5))
    f = font('Heavy', int(170 * s))
    ImageDraw.Draw(im).text((W // 2, 170), yr, font=f, anchor='mm', fill=(255, 220, 120), stroke_width=12, stroke_fill=(30, 20, 40))
    caption(im, 'Каждый год он писал\nДеду Морозу', 1790 - 40, cl((t - V['N2']) / 0.3), 54)
    flash(im, t, cues.YEARS[y_i], 0.1)
    return im


def scene3(t):
    im = gradient((8, 10, 26), (24, 22, 54)).copy()
    snow(im, t, 0.25, 90)
    # телефон с лентой
    px0, py0, px1, py1 = 230, 90, 850, 1180
    sw = V['D1'] - 0.1
    u = cl((t - sw) / 0.35)
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((px0 - 40, py0 - 40, px1 + 40, py1 + 40), 90, fill=(110, 170, 255, 90))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
    rrect(im, (px0 - 18, py0 - 18, px1 + 18, py1 + 18), 78, (10, 10, 14, 255), outline=(70, 70, 90, 255), width=6)
    scr = Image.new('RGBA', (px1 - px0, py1 - py0), (20, 20, 28, 255))
    sh = py1 - py0
    other = gradient((60, 20, 80), (200, 90, 60)).resize((px1 - px0, sh))
    od = ImageDraw.Draw(other)
    od.text((40, sh - 220), '@random_user', font=font('Bold', 38), fill=(255, 255, 255))
    od.text((40, sh - 170), 'обычный ролик…', font=font('Medium', 34), fill=(230, 230, 240))
    scr.alpha_composite(other, (0, int(-sh * eo(u))))
    mv = missed_cover(px1 - px0, sh).copy()
    md = ImageDraw.Draw(mv)
    shade = Image.new('RGBA', mv.size, (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle((0, sh - 420, mv.width, sh), fill=(0, 0, 0, 150))
    mv.alpha_composite(shade.filter(ImageFilter.GaussianBlur(40)))
    md = ImageDraw.Draw(mv)
    md.text((40, sh - 250), '@missed', font=font('Heavy', 44), fill=(255, 255, 255))
    md.text((40, sh - 190), 'Раздаю NFT-подарки', font=font('Bold', 38), fill=(255, 255, 255))
    md.text((40, sh - 140), 'подписчикам', font=font('Bold', 38), fill=(255, 255, 255))
    for i, c in enumerate(((255, 70, 100), (255, 255, 255), (255, 210, 80))):
        cy_ = sh - 620 + i * 140
        md.ellipse((mv.width - 120, cy_, mv.width - 40, cy_ + 80), fill=(0, 0, 0, 120), outline=c, width=6)
    scr.alpha_composite(mv, (0, int(sh * (1 - eo(u)))))
    m = Image.new('L', scr.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, scr.width, scr.height), 60, fill=255)
    im.paste(scr, (px0, py0), m)
    # реакции Димона по ходу реплики D1
    du = t - V['D1']
    if du < 0:
        base = dict(eyes='half', mouth='flat', arms='phone')
    elif du < 1.8:
        base = dict(eyes='wide', mouth='o', arms='phone')
    elif du < 4.4:
        base = dict(eyes='half', mouth='smirk', arms='phone')
    else:
        base = dict(eyes='open', mouth='smile', arms='phone')
    p = dimon_pose(t, base, 'D1')
    put_char(im, ch('dimon', **p), W // 2, H + 330, 0.88, dy=-6 * math.sin(t * 2.2))
    return im


def chat_scene(t, who):
    im = gradient((14, 18, 40), (36, 26, 64) if who == 'dimon' else (46, 18, 30)).copy()
    snow(im, t, 0.2, 70)
    if who == 'dimon':
        msgs = [(T['dm1'], 'me', 'Привет! Можно подарок?'),
                (T['dmm1'], 'missed', 'Ты хорошо вёл себя в этом году?'),
                (T['dm2'], 'me', 'Да! Маме помогал, сессию закрыл, никого не обманывал!'),
                (T['dmm2'], 'missed', 'За честный ответ — держи подарок 🎁'.replace(' 🎁', ''))]
        typing = cues.TYPING[:2]
    else:
        msgs = [(T['om1'], 'me', 'Привет, можно NFT?'),
                (T['omm1'], 'missed', 'А ты хорошо вёл себя в этом году?'),
                (T['om2'], 'me', 'Само собой'),
                (T['omm2'], 'missed', 'Ты уверен?'),
                (T['om3'], 'me', 'Да… что-то не так?'),
                (T['omm3'], 'missed', '!Больше всего я ненавижу скамеров и пиздаболов')]
        typing = cues.TYPING[2:]
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    chat(layer, t, msgs, typing, (40, 70, W - 40, 1180), (70, 130, 240) if who == 'dimon' else (90, 90, 110))
    zoom = 1.0
    if who == 'oleg' and t > T['omm2']:
        zoom = 1 + 0.06 * eo((t - T['omm2']) / 5)
    if zoom > 1.0:
        cw, chh = W / zoom, H / zoom
        layer = layer.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - chh) * 0.3, (W + cw) / 2, (H - chh) * 0.3 + chh))
    gx = 0
    if who == 'oleg' and 0 <= t - T['omm3'] < 0.5:
        gx = int(22 * bump(t - T['omm3'], 9, 6))
    im.alpha_composite(layer, (gx, 0))
    if who == 'dimon':
        if t < T['dmm1']:
            base = dict(eyes='open', mouth='smile')
        elif t < T['dm2']:
            base = dict(eyes='wide', mouth='o')
        elif t < T['dmm2']:
            base = dict(eyes='wide', mouth='grin')
        else:
            base = dict(eyes='wide', mouth='shock')
        p = dimon_pose(t, base, 'D2' if t < T['dm2'] else 'D3', arms='phone')
        put_char(im, ch('dimon', **p), W // 2, H + 330, 0.95, dy=-6 * math.sin(t * 2.4))
    else:
        if t < T['omm2']:
            base = dict(eyes='half', mouth='smirk')
        elif t < T['omm3']:
            base = dict(eyes='wide', mouth='flat', sweat=True, angry_brows=False)
        else:
            base = dict(eyes='wide', mouth='shock', sweat=True, angry_brows=False)
        p = dimon_pose(t, base, 'O2' if t < T['om2'] else 'O3' if t < T['om3'] else 'O4', arms='phone')
        put_char(im, ch('oleg', **p), W // 2, H + 330, 0.95, dy=-4 * math.sin(t * 2.0))
        if t > T['omm2']:                                    # виньетка напряжения
            a = int(170 * eo((t - T['omm2']) / 3))
            v = Image.new('L', (W, H), 0)
            ImageDraw.Draw(v).ellipse((-300, -200, W + 300, H + 200), fill=255)
            vig = Image.new('RGBA', (W, H), (0, 0, 0, a))
            vig.putalpha(ImageChops.multiply(Image.eval(v.filter(ImageFilter.GaussianBlur(120)), lambda x: 255 - x),
                                             Image.new('L', (W, H), a)))
            im.alpha_composite(vig)
    return im


def scene5(t):
    u = t - T['s5']
    im = gradient((40, 20, 60), (10, 8, 24)).copy()
    rays = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    cx, cy = W // 2, 600
    for i in range(16):
        a0 = u * 0.4 + i * math.pi / 8
        rd.polygon((cx, cy, cx + 1600 * math.cos(a0), cy + 1600 * math.sin(a0),
                    cx + 1600 * math.cos(a0 + 0.12), cy + 1600 * math.sin(a0 + 0.12)), fill=(255, 210, 90, 60))
    im.alpha_composite(rays.filter(ImageFilter.GaussianBlur(6)))
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((cx - 380, cy - 380, cx + 380, cy + 380), fill=(255, 200, 80, 120))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(90)))
    s = spring(u * 1.2, 1.8, 0.45)
    size = max(8, int(700 * s))
    gift = snoop(u, 512).resize((size, size), Image.BILINEAR)
    im.alpha_composite(gift, (cx - size // 2, int(cy - size // 2 - 30 * math.sin(u * 2))))
    d = ImageDraw.Draw(im)
    for i in range(70):                                    # конфетти
        rr = random.Random(i)
        x = rr.uniform(0, W) + 40 * math.sin(u * 2 + i)
        y = -60 + (rr.uniform(0, 1.0) * 400 + u * rr.uniform(300, 600)) % (H + 100)
        c = [(255, 90, 90), (255, 210, 80), (110, 220, 140), (120, 170, 255), (255, 255, 255)][i % 5]
        a = rr.uniform(0, 6.28) + u * 5
        w_, h_ = 16 * abs(math.cos(a)) + 3, 26
        d.rectangle((x - w_, y - h_ / 2, x + w_, y + h_ / 2), fill=c)
    if u > 0.5:
        a = eo((u - 0.5) / 0.4)
        pill = 'Snoop Dogg · Goldizzle'
        f = font('Heavy', 58)
        tw = d.textlength(pill, font=f)
        rrect(im, (cx - tw / 2 - 40, 990, cx + tw / 2 + 40, 1090), 50, (255, 200, 70, int(255 * a)), shadow=False)
        ImageDraw.Draw(im).text((cx, 1040), pill, font=f, anchor='mm', fill=(40, 24, 10, int(255 * a)))
        caption(im, '0 → 1 подарок', 170, a, 72, (140, 255, 160))
    if t >= V['D4'] - 0.4:
        uu = t - (V['D4'] - 0.4)
        jump = abs(math.sin(uu * 5.5)) * 90
        sq = 0.06 * math.cos(uu * 11)
        p = dimon_pose(t, dict(eyes='wide', mouth='grin', arms='up'), 'D4')
        put_char(im, ch('dimon', **p), W // 2, H + 480 - 300 * eo(uu / 0.3), 0.95, dy=-jump, sq=sq)
    flash(im, t, T['s5'], 0.25)
    return im


@functools.lru_cache(2)
def scam_room():
    im = gradient((60, 16, 26), (20, 8, 16)).copy()
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((620, 1300, 1050, 1630), 20, fill=(12, 12, 18), outline=(80, 80, 96), width=8)
    for i, txt in enumerate(('улучшу ваш подарок', 'переведи 100 звёзд', 'скинь сидку, проверю')):
        d.rounded_rectangle((645, 1330 + i * 95, 1025, 1405 + i * 95), 24, fill=(44, 50, 72))
        d.text((662, 1367 + i * 95), txt, font=font('Semibold', 30), fill=(255, 255, 255), anchor='lm')
    for i, n in enumerate(OLEG_GIFTS[:4]):
        g = gift_png(n, 110)
        im.alpha_composite(g, (600 + (i % 2) * 230, 1080 + (i // 2) * 0) if False else (560 + i * 118, 1150))
    return im


def scene6(t):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    top = gradient((40, 70, 150), (20, 30, 80)).crop((0, 0, W, H // 2))
    im.alpha_composite(top)
    snow(im, t, 0.2, 80)
    bot = scam_room().crop((0, H // 2, W, H))
    im.alpha_composite(bot, (0, H // 2))
    pd = dimon_pose(t, dict(eyes='wide', mouth='grin', arms='phone'), 'D5')
    po = dimon_pose(t, dict(eyes='half', mouth='smirk', arms='phone'), 'O1')
    upper = Image.new('RGBA', (W, H // 2), (0, 0, 0, 0))
    put_char(upper, ch('dimon', **pd), W // 2 - 140, H // 2 + 380, 0.95, dy=-12 * abs(math.sin(t * 4)))
    im.alpha_composite(upper)
    lower = Image.new('RGBA', (W, H // 2), (0, 0, 0, 0))
    put_char(lower, ch('oleg', **po), 300, H // 2 + 380, 0.95, dy=-4 * math.sin(t * 1.6))
    im.alpha_composite(lower, (0, H // 2))
    d = ImageDraw.Draw(im)
    d.rectangle((0, H // 2 - 8, W, H // 2 + 8), fill=(255, 255, 255))
    secs = int(max(0, t - T['s6']))
    rrect(im, (W // 2 - 150, H // 2 - 50, W // 2 + 150, H // 2 + 50), 50, (40, 200, 110, 255), shadow=False)
    ImageDraw.Draw(im).text((W // 2, H // 2), f'00:{secs:02d}', font=font('Heavy', 52), anchor='mm', fill=(255, 255, 255))
    ImageDraw.Draw(im).text((W - 60, 90), 'Димон', font=font('Heavy', 60), anchor='rm', fill=(255, 255, 255), stroke_width=8, stroke_fill=(15, 15, 30))
    ImageDraw.Draw(im).text((W - 60, H // 2 + 100), 'Олег', font=font('Heavy', 60), anchor='rm', fill=(255, 170, 170), stroke_width=8, stroke_fill=(15, 15, 30))
    return im


def scene8(t):
    im = gradient((40, 14, 24), (12, 6, 14)).copy()
    snow(im, t, 0.5, 160)
    gone = sum(1 for v in cues.VANISH if t >= v)
    profile_card(im, t, 'Олег', head_avatar('oleg', 220), 6 - gone, gifts=OLEG_GIFTS, vanish=cues.VANISH, scale=0.92,
                 y0=110, count_col=(255, 80, 90) if gone else (140, 255, 160))
    p = dimon_pose(t, dict(eyes='wide', mouth='shock', sweat=True, angry_brows=False, arms='up' if t > V['O5'] else 'phone'), 'O5')
    put_char(im, ch('oleg', **p), W // 2, H + 380, 0.95, dy=int(10 * bump(t - V['O5'], 8, 4)))
    return im


def scene9(t):
    u = t - T['s9']
    im = gradient((8, 12, 34), (30, 36, 80)).copy()
    snow(im, t, 1.0, 220)
    cx, cy = W // 2, 640
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((cx - 330, cy - 330, cx + 330, cy + 330), fill=(180, 210, 255, 150))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(70)))
    a = eo(u / 1.0)
    av = missed_avatar(520)
    av2 = av.copy(); av2.putalpha(av.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(av2, (cx - 260, cy - 260 + int(12 * math.sin(u * 1.4))))
    ImageDraw.Draw(im).ellipse((cx - 266, cy - 266, cx + 266, cy + 266), outline=(220, 235, 255, int(255 * a)), width=8)
    gs = snoop(u, 260)
    im.alpha_composite(gs, (cx + 170, cy + 150 + int(14 * math.sin(u * 2 + 1))))
    t1 = V['N3']; t2 = V['N3'] + 1.9
    caption(im, 'Мисед дарит подарки', 1230, eo((t - t1) / 0.4), 70)
    caption(im, 'но только тем,\nкто их заслужил', 1380, eo((t - t2) / 0.4), 70, (255, 220, 120))
    end = DUR - t
    if end < 0.7:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - end / 0.7)))))
    return im


def render_at(t):
    s = scene_at(t)
    if s == 's1':
        im = scene1(t)
    elif s == 's2':
        im = scene2(t)
    elif s == 's3':
        im = scene3(t)
    elif s == 's4':
        im = chat_scene(t, 'dimon')
    elif s == 's5':
        im = scene5(t)
    elif s == 's6':
        im = scene6(t)
    elif s == 's7':
        im = chat_scene(t, 'oleg')
    elif s == 's8':
        im = scene8(t)
    else:
        im = scene9(t)
    if s != 's1':
        flash(im, t, T[s], 0.12)
    return im.convert('RGB')


def _frame(i):
    return render_at(i / FPS).tobytes()


def prewarm():
    """Рисуем все позы заранее (каждая ~10 с), чтобы воркеры брали их из кэша."""
    for i in range(0, int(DUR * FPS), 6):
        render_at(i / FPS)


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
    elif sys.argv[1] == '--prewarm':
        prewarm(); print('prewarm OK')
    elif sys.argv[1] == '--build':
        build(sys.argv[2])
