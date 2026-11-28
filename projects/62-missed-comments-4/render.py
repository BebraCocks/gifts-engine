"""Четвёртый ролик-призыв: ретро 8-бит игра. Кадр рисуется в 270×480 и увеличивается ×4 без сглаживания.
Всё кодом; Мисед — только оригинальная ава в круге (пикселизованная, как портрет в RPG).

    python -B projects/62-missed-comments-4/render.py --frames 1.0,6.0
    python -B projects/62-missed-comments-4/render.py --build name.mp4
"""
import functools
import math
import random
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import cues  # noqa: E402
from timeline import V, T, DUR, scene_at  # noqa: E402

S = 4
w, h = 270, 480                         # «игровое» разрешение
W, H, FPS = w * S, h * S, 60
FD = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
BG, INK, WHITE = (22, 18, 44), (8, 6, 16), (250, 250, 240)
YEL, RED, GRN, BLUE, PINK, ORG, CYAN = (255, 214, 64), (232, 56, 72), (88, 216, 96), (72, 120, 255), (255, 112, 200), (255, 150, 40), (80, 220, 240)


@functools.lru_cache(64)
def font(sz):
    return ImageFont.truetype(str(FD / 'SF-Pro-Text-Heavy.otf'), sz)


def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def eo(x):
    x = cl(x); return 1 - (1 - x) ** 3


def step(x, n=4):
    """Ступенчатая анимация, как в старых играх."""
    return math.floor(cl(x) * n) / n


@functools.lru_cache(512)
def ptext_img(s, sz, col, outline=INK):
    """Пиксельный текст: рисуем и обрезаем сглаживание порогом, с контуром в 1 пиксель."""
    f = font(sz)
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    l, t_, r, b = d0.textbbox((0, 0), s, font=f)
    tw, th = r - l + 6, b - t_ + 6
    m = Image.new('L', (tw, th), 0)
    ImageDraw.Draw(m).text((3 - l, 3 - t_), s, font=f, fill=255)
    m = m.point(lambda v: 255 if v > 110 else 0)
    o = Image.new('L', (tw, th), 0)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            o.paste(m, (dx, dy), m)
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    im.paste(Image.new('RGBA', (tw, th), outline + (255,)), (0, 0), o)
    im.paste(Image.new('RGBA', (tw, th), col + (255,)), (0, 0), m)
    return im


def ptext(im, s, x, y, sz, col=WHITE, a=True):
    if not a:
        return
    t = ptext_img(s, sz, col)
    im.alpha_composite(t, (int(x - t.width / 2), int(y - t.height / 2)))


def stars(im, t, dense=60):
    d = ImageDraw.Draw(im)
    for i in range(dense):
        rr = random.Random(i)
        x = int(rr.uniform(0, w)); y = int((rr.uniform(0, h) + t * rr.uniform(6, 24)) % h)
        if (int(t * 4) + i) % 5:
            d.point((x, y), fill=WHITE)


def ground(im, t):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 430, w, h), fill=(56, 160, 64))
    for x in range(-16, w + 16, 16):
        xx = x - int(t * 30) % 16
        d.rectangle((xx, 430, xx + 7, 437), fill=(96, 208, 96))
        d.rectangle((xx + 8, 446, xx + 15, 453), fill=(40, 120, 48))


def box(im, x0, y0, x1, y1, col=WHITE, fill=(30, 30, 80)):
    d = ImageDraw.Draw(im)
    d.rectangle((x0, y0, x1, y1), fill=fill, outline=INK)
    d.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), outline=col)


@functools.lru_cache(4)
def avatar(sz):
    im = Image.open(HERE / 'refs' / 'missed_original.jpg').convert('RGB')
    im = im.crop((60, 0, 600, 540)).resize((sz, sz), Image.BILINEAR)
    m = Image.new('L', (sz, sz), 0)
    ImageDraw.Draw(m).ellipse((0, 0, sz - 1, sz - 1), fill=255)
    out = Image.new('RGBA', (sz + 4, sz + 4), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, sz + 3, sz + 3), fill=YEL + (255,))
    a = Image.new('RGBA', (sz, sz)); a.paste(im, (0, 0), m)
    out.alpha_composite(a, (2, 2))
    return out


@functools.lru_cache(64)
def gift_px(name, sz):
    m = G.models(name)[-1]['name']
    im = Image.open(G.model_png(name, m, 512)).convert('RGBA').resize((sz, sz), Image.BILINEAR)
    a = im.getchannel('A').point(lambda v: 255 if v > 100 else 0)
    im.putalpha(a)
    return im


def gift_anim_px(name, model, t, sz):
    im = lottie.frame(G.model_file(name, model, 'tgs'), t, size=256).resize((sz, sz), Image.BILINEAR)
    im.putalpha(im.getchannel('A').point(lambda v: 255 if v > 100 else 0))
    return im


def put(im, s, cx, cy):
    im.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


def coin(d, x, y, r=5):
    d.rectangle((x - r, y - r + 1, x + r, y + r - 1), fill=YEL)
    d.rectangle((x - r + 1, y - r, x + r - 1, y + r), fill=YEL)
    d.line((x, y - r + 2, x, y + r - 2), fill=ORG)


def bubble(im, txt, x, y, col=WHITE):
    t = ptext_img(txt, 26, INK, outline=WHITE)
    bw, bh = t.width + 24, t.height + 14
    d = ImageDraw.Draw(im)
    d.rectangle((x - bw // 2, y - bh // 2, x + bw // 2, y + bh // 2), fill=col, outline=INK)
    d.polygon(((x - 10, y + bh // 2), (x - 14, y + bh // 2 + 7), (x - 2, y + bh // 2)), fill=col, outline=INK)
    im.alpha_composite(t, (x - t.width // 2, y - t.height // 2))


def flash(im, t, t0, dur=0.1):
    if 0 <= t - t0 < dur:
        im.alpha_composite(Image.new('RGBA', im.size, WHITE + (int(200 * (1 - (t - t0) / dur)),)))


# ------------------------------------------------------------------ сцены
def s1(t):
    im = Image.new('RGBA', (w, h), BG + (255,))
    stars(im, t)
    ground(im, t)
    lines = [('Я РАЗДАМ NFT,', YEL, 120), ('КОТОРЫЕ ЕЩЁ', WHITE, 150), ('НЕ ВЫИГРАЛ!', RED, 182)]
    k = 0
    for i, (s, col, y) in enumerate(lines):
        n = int((t - V['L1'] - i * 0.7) / 0.06)
        if n > 0:
            ptext(im, s[:n], w // 2, y, 22 if i < 2 else 26, col)
    put(im, avatar(64), w // 2, 300 + (2 if int(t * 4) % 2 else 0))
    put(im, gift_px('Lol Pop', 40), w // 2 - 70, 300 - (4 if int(t * 3) % 2 else 0))
    put(im, gift_px('Santa Hat', 40), w // 2 + 70, 300 - (0 if int(t * 3) % 2 else 4))
    if t >= T['explain']:
        v = t - T['explain']
        box(im, 30, 360, 240, 410, YEL)
        ptext(im, 'ОБЪЯСНЯЮ ▶' if int(t * 4) % 2 else 'ОБЪЯСНЯЮ', w // 2, 385, 20, YEL)
        flash(im, t, T['explain'], 0.08)
    else:
        if int(t * 2.5) % 2:
            ptext(im, 'PRESS START', w // 2, 385, 16, WHITE)
    return im


def s2(t):
    im = Image.new('RGBA', (w, h), (16, 30, 52, 255))
    stars(im, t, 30)
    ground(im, t)
    if t < T['sell']:
        ptext(im, 'КВЕСТ ОТ МИСЕДА', w // 2, 40, 20, YEL)
        box(im, 12, 300, 258, 420, WHITE, (20, 20, 60))
        put(im, avatar(56), 48, 300)
        txt = ['Собери больше всех', 'комментариев под видео', 'про меня — получи NFT!']
        tot = int((t - T['quest']) / 0.05)
        for i, ln in enumerate(txt):
            n = max(0, min(len(ln), tot - sum(len(x) for x in txt[:i])))
            if n:
                im.alpha_composite(ptext_img(ln[:n], 14, WHITE), (24, 340 + i * 22))
        put(im, gift_px('Heart Locket', 90), w // 2, 180 + (3 if int(t * 3) % 2 else 0))
        return im
    if t < T['gifts']:
        v = t - T['sell']
        ptext(im, 'ПРОДАЮ ВЫИГРЫШ', w // 2, 50, 20, YEL)
        put(im, gift_anim_px('Mighty Arm', 'T800', v, 96), w // 2, 185 + (2 if int(t * 4) % 2 else 0))
        if v > 0.3 and int(v * 6) % 2:
            ptext(im, 'SOLD!', w // 2 + 60, 150, 16, RED)
        d = ImageDraw.Draw(im)
        for i in range(12):
            rr = random.Random(i)
            x = int(rr.uniform(30, w - 30)); y = int(250 + (v * rr.uniform(60, 140)) % 160)
            coin(d, x, y)
        money = int(cl(v / 1.2) * 9999)
        box(im, 50, 92, 220, 118, YEL)
        ptext(im, f'$ {money:04d}', w // 2, 105, 18, YEL)
        return im
    if t < T['zero']:
        v = t - T['gifts']
        ptext(im, 'ДЕНЬГИ → ПОДАРКИ', w // 2, 50, 18, CYAN)
        ptext(im, 'ДЛЯ ВАС!', w // 2, 80, 26, GRN)
        d = ImageDraw.Draw(im)
        for i in range(10):                                         # игроки внизу
            x = 22 + i * 25
            d.rectangle((x - 6, 404, x + 6, 428), fill=[BLUE, PINK, ORG, CYAN, GRN][i % 5], outline=INK)
            d.rectangle((x - 4, 396, x + 4, 404), fill=(250, 210, 170), outline=INK)
        for i in range(10):
            k = step((v - i * 0.14) / 0.6, 8)
            if k <= 0:
                continue
            x = 22 + i * 25
            y = 120 + (370 - 120) * k
            put(im, gift_px(cues.CHEAP[i], 22), x, int(y))
        return im
    v = t - T['zero']
    im2 = Image.new('RGBA', (w, h), (40, 8, 16, 255))
    ptext(im2, 'СЕБЕ:', w // 2, 150, 30, WHITE)
    sz = 90 if int(v * 8) % 2 == 0 or v > 0.5 else 70
    ptext(im2, '0', w // 2, 240, sz, RED)
    ptext(im2, 'НИ КОПЕЙКИ!', w // 2, 330, 24, YEL)
    flash(im2, t, T['zero'], 0.08)
    return im2


def s3(t):
    im = Image.new('RGBA', (w, h), (12, 12, 36, 255))
    stars(im, t, 40)
    ptext(im, 'СТАВКИ', w // 2, 34, 26, YEL)
    for i, ((lab, name, model), t0) in enumerate(zip(cues.TIERS, T['tier'])):
        y = 120 + i * 125
        v = t - t0
        on = v >= 0
        box(im, 14, y - 50, 256, y + 50, [ORG, GRN, PINK][i] if on else (90, 90, 110), (24, 24, 64) if on else (18, 18, 30))
        ptext(im, f'LV{i + 1}', 46, y - 28, 14, [ORG, GRN, PINK][i] if on else (90, 90, 110))
        if on:
            g = gift_anim_px(name, model, v, 80)
            put(im, g, 60, y + 8 - (3 if int(t * 4) % 2 else 0))
            ptext(im, lab, 170, y - 16, 30, WHITE)
            ptext(im, name, 170, y + 22, 14, YEL)
            if v < 0.8 and int(v * 10) % 2:
                ptext(im, 'LEVEL UP!', 190, y - 46, 12, GRN)
            flash(im, t, t0, 0.06)
        else:
            ptext(im, '? ? ?', 150, y, 24, (90, 90, 110))
    return im


def s4(t):
    im = Image.new('RGBA', (w, h), (20, 40, 30, 255))
    stars(im, t, 20)
    if t < T['top']:
        ptext(im, 'ЛЮБОЙ КОММЕНТ', w // 2, 40, 20, YEL)
        ptext(im, '= +1 ОЧКО', w // 2, 66, 20, GRN)
        score = sum(1 for x in cues.PLUS if t >= x)
        box(im, 70, 92, 200, 118, GRN)
        ptext(im, f'СЧЁТ: {score:03d}', w // 2, 105, 16, GRN)
        for (txt, t0, x, y) in (('а', T['letter'], 70, 190), (':)', T['emoji'], 190, 250), ('.', T['dot'], 90, 320)):
            v = t - t0
            if v < 0:
                continue
            bubble(im, txt, x, y)
            if v < 0.7:
                ptext(im, '+1', x + 40, int(y - 20 - v * 40), 16, YEL)
        if t >= T['dot']:
            ptext(im, 'ДАЖЕ ТОЧКА!', w // 2, 390, 24, PINK)
        return im
    v = t - T['top']
    im = Image.new('RGBA', (w, h), (36, 16, 60, 255))
    stars(im, t, 40)
    ptext(im, 'HIGH SCORE', w // 2, 40, 26, YEL)
    rows = [('1', '@ty_lider', 999, YEL), ('2', '@kira', 512, WHITE), ('3', '@den4ik', 377, WHITE), ('4', '@mila', 205, WHITE)]
    for i, (pl, nm, sc, col) in enumerate(rows):
        if v < i * 0.15:
            continue
        y = 100 + i * 34
        ptext(im, pl, 30, y, 18, col)
        im.alpha_composite(ptext_img(nm, 16, col), (48, y - 9))
        ptext(im, f'{sc:03d}', 228, y, 16, col)
    if v > 0.8:
        d = ImageDraw.Draw(im)
        cx, cy = w // 2, 320 + (2 if int(t * 4) % 2 else 0)
        d.rectangle((cx - 40, cy - 20, cx + 40, cy + 30), fill=(150, 80, 30), outline=INK)
        d.rectangle((cx - 44, cy - 34, cx + 44, cy - 16), fill=(190, 110, 40), outline=INK)
        d.rectangle((cx - 5, cy - 34, cx + 5, cy + 30), fill=YEL, outline=INK)
        if int(t * 6) % 2:
            for k in range(6):
                a = k * math.pi / 3 + t
                d.point((int(cx + 56 * math.cos(a)), int(cy + 40 * math.sin(a))), fill=YEL)
        ptext(im, 'БОНУС-ПОДАРОК', w // 2, 390, 18, YEL)
        ptext(im, 'ЗА 1 МЕСТО', w // 2, 414, 16, WHITE)
    return im


def s5(t):
    im = Image.new('RGBA', (w, h), BG + (255,))
    stars(im, t)
    ground(im, t)
    if int(t * 3) % 2:
        ptext(im, 'INSERT COMMENT', w // 2, 120, 20, YEL)
    put(im, avatar(56), w // 2, 210)
    d = ImageDraw.Draw(im)
    # иконка комментария, пиксельная
    cx, cy = w // 2, 300
    d.rectangle((cx - 30, cy - 20, cx + 30, cy + 18), fill=WHITE, outline=INK)
    d.polygon(((cx - 18, cy + 18), (cx - 24, cy + 30), (cx - 6, cy + 18)), fill=WHITE, outline=INK)
    for k in range(3):
        d.rectangle((cx - 16 + k * 14, cy - 3, cx - 10 + k * 14, cy + 3), fill=INK)
    if t >= T['go']:
        v = t - T['go']
        ptext(im, 'ПЕРВЫЙ ПОШЁЛ!', w // 2, 370, 24, GRN)
        ax = w - 30 + (3 if int(t * 6) % 2 else 0)
        d.polygon(((ax - 20, 290), (ax - 6, 290), (ax - 6, 282), (ax + 8, 300), (ax - 6, 318), (ax - 6, 310), (ax - 20, 310)),
                  fill=YEL, outline=INK)
        flash(im, t, T['go'], 0.08)
    else:
        ptext(im, 'КОММЕНТЫ САМИ', w // 2, 370, 18, WHITE)
        ptext(im, 'НЕ НАПИШУТСЯ', w // 2, 394, 18, WHITE)
    end = DUR - t
    if end < 0.5:
        im.alpha_composite(Image.new('RGBA', im.size, (0, 0, 0, int(255 * (1 - end / 0.5)))))
    return im


def render_at(t):
    s = scene_at(t)
    im = {'L1': s1, 'L2': s2, 'L3': s3, 'L4': s4, 'L5': s5}[s](t)
    if s != 'L1':
        flash(im, t, V[s], 0.08)
    return im.convert('RGB').resize((W, H), Image.NEAREST)


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
