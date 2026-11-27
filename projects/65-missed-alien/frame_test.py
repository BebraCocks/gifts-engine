"""Пробный кадр серии 1: сцена 3, ночь, наезд на Миседа в кресле — «Тогда зачем первые четыре?».

    python -B frame_test.py     # build/review/test_scene3.png
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import art

HERE = Path(__file__).resolve().parent
FONT = HERE.parents[1] / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Heavy.otf'
WF, HF = 1080, 1920
rng = np.random.default_rng(7)


def vgrad(w, h, top, bot):
    k = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float) * (1 - k) + np.array(bot, float) * k
    return Image.fromarray(np.repeat(a, w, 1).astype(np.uint8), 'RGB').convert('RGBA')


def glow(size, col, r):
    m = Image.new('L', size, 0)
    return m, col, r


def room_night():
    im = vgrad(WF, HF, (22, 28, 58), (12, 14, 32))
    d = ImageDraw.Draw(im)
    # окно с луной слева сверху
    wx0, wy0, wx1, wy1 = 70, 230, 470, 780
    sky = vgrad(wx1 - wx0, wy1 - wy0, (34, 52, 110), (60, 80, 140))
    sd = ImageDraw.Draw(sky)
    for _ in range(40):
        x, y = rng.integers(0, wx1 - wx0), rng.integers(0, wy1 - wy0)
        s = rng.choice([1, 1, 2])
        sd.ellipse((x, y, x + s, y + s), fill=(230, 235, 255))
    moon = Image.new('RGBA', sky.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(moon)
    md.ellipse((210, 70, 330, 190), fill=(250, 245, 220, 255))
    halo = Image.new('RGBA', sky.size, (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse((170, 30, 370, 230), fill=(230, 235, 255, 90))
    sky.alpha_composite(halo.filter(ImageFilter.GaussianBlur(30)))
    sky.alpha_composite(moon)
    im.alpha_composite(sky, (wx0, wy0))
    frame_c = (40, 36, 52, 255)
    d.rectangle((wx0 - 18, wy0 - 18, wx1 + 18, wy1 + 18), outline=frame_c, width=22)
    d.line((wx0 + (wx1 - wx0) // 2, wy0, wx0 + (wx1 - wx0) // 2, wy1), fill=frame_c, width=14)
    d.line((wx0, wy0 + 260, wx1, wy0 + 260), fill=frame_c, width=14)
    # шторы
    for x0, x1 in ((20, 120), (420, 520)):
        d.rectangle((x0, 180, x1, 900), fill=(46, 40, 78, 255))
        for k in range(x0 + 18, x1, 26):
            d.line((k, 180, k, 900), fill=(36, 30, 64, 255), width=6)
    # лунный луч по комнате
    beam = Image.new('L', (WF, HF), 0)
    ImageDraw.Draw(beam).polygon([(wx0, wy0), (wx1, wy0), (1080, 1500), (430, 1700)], fill=60)
    im.alpha_composite(Image.merge('RGBA', [Image.new('L', (WF, HF), v) for v in (170, 190, 255)] + [beam.filter(ImageFilter.GaussianBlur(40))]))
    # пол
    d.rectangle((0, 1560, WF, HF), fill=(18, 18, 36, 255))
    for y in range(1580, HF, 46):
        d.line((0, y, WF, y), fill=(24, 24, 46, 255), width=3)
    # постер и полка на стене справа
    d.rounded_rectangle((700, 300, 960, 640), 12, fill=(36, 44, 86, 255), outline=(52, 60, 104, 255), width=6)
    d.ellipse((780, 380, 880, 480), fill=(60, 72, 128, 255))
    d.polygon([(760, 560), (830, 470), (900, 560)], fill=(52, 64, 116, 255))
    return im


def armchair(im, cx, top):
    """Кресло: высокая спинка за головой, подлокотники спереди (рисуется в два слоя)."""
    back = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(back)
    col, dk = (54, 46, 92, 255), (40, 34, 72, 255)
    d.rounded_rectangle((cx - 360, top, cx + 360, top + 1100), 150, fill=col)
    d.rounded_rectangle((cx - 300, top + 60, cx + 300, top + 1000), 120, fill=dk)
    for k in (-1, 1):
        d.line((cx + k * 120, top + 120, cx + k * 120, top + 900), fill=(48, 40, 84, 255), width=10)
    return back


def armrests(im, cx, y):
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in (-1, 1):
        x0 = cx + k * 300
        d.rounded_rectangle((min(x0, x0 + k * 150) - 20, y, max(x0, x0 + k * 150) + 20, y + 520), 80, fill=(62, 54, 104, 255))
        d.rounded_rectangle((min(x0, x0 + k * 150) - 20, y, max(x0, x0 + k * 150) + 20, y + 70), 40, fill=(74, 66, 120, 255))
    d.rounded_rectangle((cx - 330, y + 260, cx + 330, y + 700), 60, fill=(58, 50, 98, 255))
    return lay


def moonlit(sprite):
    """Ночная подсветка: холодный общий тон + светлый край со стороны окна (слева)."""
    a = np.asarray(sprite, np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    tone = np.array([0.80, 0.80, 0.94])
    rgb = rgb * tone
    m = Image.fromarray(a[..., 3].astype(np.uint8))
    inner = np.asarray(m.filter(ImageFilter.MinFilter(15)), np.float32) / 255
    rim = np.clip(a[..., 3] / 255 - inner, 0, 1)
    rim = rim * np.clip(np.linspace(1.4, -0.6, rim.shape[1]), 0, 1)[None, :]
    rgb = rgb + rim[..., None] * np.array([70, 80, 110])
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), 'RGBA')


def subtitle(im, lines, y, size=72, gap=12):
    """Субтитры по центру, строки не шире безопасной зоны x 140…940."""
    f = ImageFont.truetype(str(FONT), size)
    d = ImageDraw.Draw(im)
    for i, text in enumerate(lines):
        w = d.textlength(text, font=f)
        assert w <= 800, (text, w)
        x, yy = (WF - w) / 2, y + i * (size + gap)
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x, yy + 6), text, font=f, fill=(0, 0, 0, 170))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
        d.text((x, yy), text, font=f, fill=(255, 255, 255, 255), stroke_width=7, stroke_fill=(20, 16, 40, 255))
    return im


def main():
    im = room_night()
    cx = 600
    zoom = 1.08                          # наезд на «Тогда зачем…»
    im.alpha_composite(armchair(im, cx, 520))
    m = art.missed(dict(mouth='flat', look=-0.15))
    m = m.resize((int(m.width * zoom), int(m.height * zoom)), Image.LANCZOS)
    m = moonlit(m)
    im.alpha_composite(m, (int(cx - m.width / 2), 380))
    im.alpha_composite(armrests(im, cx, 1330))
    # виньетка
    v = Image.new('L', (WF, HF), 0)
    ImageDraw.Draw(v).ellipse((-300, -200, WF + 300, HF + 200), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new('RGBA', (WF, HF), (4, 4, 14, 255))
    dark.putalpha(Image.eval(v, lambda p: int((255 - p) * 0.75)))
    im.alpha_composite(dark)
    subtitle(im, ['Тогда зачем', 'первые четыре?'], 1230)
    out = HERE / 'build' / 'review' / 'test_scene3.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert('RGB').save(out)
    print(out)


if __name__ == '__main__':
    main()
