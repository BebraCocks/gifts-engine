"""Real-life things drawn in code, flat with an ink outline (no logos): chips with crab, Apple Watch SE,
AirPods Pro, iPhone 18 Pro (back), Lada Granta (side). sprite(kind) -> RGBA ≈ 300 px, drawn at 2x."""
import functools
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
from PIL import Image, ImageDraw
import fx
import config

INK = config.INK + (255,)
S = 2
OUT = 6 * S          # outline width


def _c(rgb):
    return tuple(rgb) + (255,)


def _canvas(w=320, h=320):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _fin(im):
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


def P(*xy):
    return [(x * S, y * S) for x, y in zip(xy[::2], xy[1::2])]


def chips():
    im, d = _canvas(300, 320)
    # bag with crimped top and bottom
    top, bot, x0, x1 = 34, 296, 46, 254
    pts = [(x0 + 10, top)]
    n = 9
    for k in range(n + 1):
        x = x0 + 10 + (x1 - x0 - 20) * k / n
        pts.append((x, top - (7 if k % 2 else 0)))
    pts += [(x1, top + 18), (x1 + 8, 160), (x1, bot - 18)]
    for k in range(n + 1):
        x = x1 - 10 - (x1 - x0 - 20) * k / n
        pts.append((x, bot + (7 if k % 2 else 0)))
    pts += [(x0, bot - 18), (x0 - 8, 160), (x0, top + 18)]
    d.polygon([(x * S, y * S) for x, y in pts], fill=_c((252, 202, 48)), outline=INK, width=OUT)
    d.line(P(x0 + 4, 64, x1 - 4, 64), fill=INK, width=4 * S)
    d.line(P(x0 + 4, 268, x1 - 4, 268), fill=INK, width=4 * S)
    # red sun badge
    cx, cy, r = 150, 150, 74
    d.ellipse(P(cx - r, cy - r, cx + r, cy + r), fill=_c((236, 60, 44)), outline=INK, width=5 * S)
    # crab
    d.ellipse(P(cx - 40, cy - 14, cx + 40, cy + 34), fill=_c((255, 132, 72)), outline=INK, width=4 * S)
    for sx in (-1, 1):
        for k in range(3):
            y = cy + 6 + k * 10
            d.line(P(cx + sx * 36, y, cx + sx * 56, y + 8), fill=INK, width=4 * S)
        d.line(P(cx + sx * 26, cy - 8, cx + sx * 40, cy - 34), fill=INK, width=4 * S)
        d.pieslice(P(cx + sx * 40 - 15, cy - 56, cx + sx * 40 + 15, cy - 26), 200 if sx < 0 else -20,
                   160 if sx < 0 else 340, fill=_c((255, 132, 72)), outline=INK, width=3 * S)
        d.line(P(cx + sx * 10, cy - 12, cx + sx * 12, cy - 26), fill=INK, width=3 * S)
        d.ellipse(P(cx + sx * 12 - 6, cy - 34, cx + sx * 12 + 6, cy - 22), fill=_c((255, 255, 255)),
                  outline=INK, width=2 * S)
    d.text((150 * S, 247 * S), 'КРАБ', font=fx.font('Heavy', 30 * S), fill=INK, anchor='mm')
    return _fin(im)


def watch():
    im, d = _canvas(300, 320)
    band = _c((214, 204, 190))
    d.rounded_rectangle(P(98, 6, 202, 92), 26 * S, fill=band, outline=INK, width=OUT)
    d.rounded_rectangle(P(98, 228, 202, 314), 26 * S, fill=band, outline=INK, width=OUT)
    d.line(P(150, 30, 150, 60), fill=INK, width=4 * S)
    d.ellipse(P(144, 270, 156, 282), fill=INK)
    d.rounded_rectangle(P(62, 66, 238, 254), 48 * S, fill=_c((236, 230, 220)), outline=INK, width=OUT)
    d.rounded_rectangle(P(80, 84, 220, 236), 34 * S, fill=_c((24, 22, 30)))
    d.rounded_rectangle(P(236, 116, 252, 160), 6 * S, fill=_c((236, 230, 220)), outline=INK, width=4 * S)
    d.text((150 * S, 150 * S), '10:09', font=fx.font('Heavy', 46 * S), fill=_c((255, 255, 255)), anchor='mm')
    d.text((150 * S, 204 * S), 'ПТ 6', font=fx.font('Semibold', 20 * S), fill=_c(config.ACCENT), anchor='mm')
    return _fin(im)


def airpods():
    im, d = _canvas(300, 320)
    white, shade = _c((250, 249, 246)), _c((226, 220, 210))
    # open lid
    d.rounded_rectangle(P(52, 74, 248, 150), 40 * S, fill=shade, outline=INK, width=OUT)
    # buds standing in the case
    for cx in (110, 190):
        d.rounded_rectangle(P(cx - 14, 96, cx + 14, 196), 14 * S, fill=white, outline=INK, width=5 * S)
        d.ellipse(P(cx - 30, 70, cx + 26, 122), fill=white, outline=INK, width=5 * S)
        d.rounded_rectangle(P(cx - 24, 88, cx - 12, 104), 5 * S, fill=_c((196, 190, 180)))
    # case body
    d.rounded_rectangle(P(48, 140, 252, 300), 56 * S, fill=white, outline=INK, width=OUT)
    d.line(P(60, 172, 240, 172), fill=INK, width=4 * S)
    d.ellipse(P(144, 228, 156, 240), fill=_c((80, 200, 120)))
    return _fin(im)


def iphone():
    im, d = _canvas(300, 330)
    body = _c((176, 204, 226))      # Glacier blue
    w, h = 176, 316
    pad = Image.new('RGBA', (w * S + 40, h * S + 40), (0, 0, 0, 0))
    q = ImageDraw.Draw(pad)
    o = 20
    q.rounded_rectangle([o, o, o + w * S, o + h * S], 34 * S, fill=body, outline=INK, width=OUT)
    q.rounded_rectangle([o + 12 * S, o + 14 * S, o + (w - 12) * S, o + 92 * S], 22 * S, fill=_c((150, 180, 206)),
                        outline=INK, width=4 * S)
    for x, y in ((44, 40), (44, 76), (86, 58)):
        r = 17
        q.ellipse([o + (x - r) * S, o + (y - r) * S, o + (x + r) * S, o + (y + r) * S], fill=_c((40, 40, 52)),
                  outline=INK, width=4 * S)
        q.ellipse([o + (x - 6) * S, o + (y - 9) * S, o + (x + 2) * S, o + (y - 1) * S], fill=_c((120, 140, 170)))
    q.ellipse([o + 132 * S, o + 34 * S, o + 146 * S, o + 48 * S], fill=_c((250, 240, 210)), outline=INK, width=3 * S)
    q.ellipse([o + 76 * S, o + 180 * S, o + 100 * S, o + 204 * S], outline=_c((140, 170, 196)), width=5 * S)
    pad = pad.rotate(-9, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(pad, ((im.width - pad.width) // 2, (im.height - pad.height) // 2))
    return _fin(im)


def granta():
    im, d = _canvas(360, 230)
    body, glass = _c((246, 246, 248)), _c((150, 184, 206))
    # body (sedan, side view, nose to the right)
    pts = [(14, 150), (18, 118), (60, 104), (108, 62), (226, 60), (270, 100), (338, 112), (348, 140), (344, 166),
           (14, 166)]
    d.polygon([(x * S, y * S) for x, y in pts], fill=body, outline=INK, width=OUT)
    d.polygon(P(118, 72, 168, 72, 168, 104, 88, 104), fill=glass, outline=INK, width=4 * S)
    d.polygon(P(178, 72, 222, 72, 254, 104, 178, 104), fill=glass, outline=INK, width=4 * S)
    d.line(P(172, 106, 172, 158), fill=INK, width=4 * S)
    d.line(P(30, 128, 330, 128), fill=_c(config.ACCENT), width=4 * S)
    d.rounded_rectangle(P(320, 116, 344, 128), 4 * S, fill=_c((255, 214, 90)), outline=INK, width=3 * S)
    d.rounded_rectangle(P(16, 120, 30, 134), 3 * S, fill=_c((230, 70, 50)), outline=INK, width=3 * S)
    for cx in (84, 280):
        d.ellipse(P(cx - 34, 132, cx + 34, 200), fill=_c((36, 34, 44)), outline=INK, width=4 * S)
        d.ellipse(P(cx - 15, 151, cx + 15, 181), fill=_c((190, 190, 196)), outline=INK, width=3 * S)
    d.text((200 * S, 146 * S), 'LADA', font=fx.font('Heavy', 14 * S), fill=_c((170, 170, 176)), anchor='mm')
    out = _fin(im)
    canvas = Image.new('RGBA', (360, 300), (0, 0, 0, 0))
    canvas.alpha_composite(out, (0, 90))          # sits low on the plate, like the other things
    return canvas


DRAW = {'chips': chips, 'watch': watch, 'airpods': airpods, 'iphone': iphone, 'granta': granta}


@functools.lru_cache(None)
def sprite(kind):
    return DRAW[kind]()


if __name__ == '__main__':
    sheet = Image.new('RGBA', (5 * 370, 340), config.BACKGROUND + (255,))
    for k, kind in enumerate(DRAW):
        im = sprite(kind)
        sheet.alpha_composite(im, (k * 370 + (370 - im.width) // 2, (340 - im.height) // 2))
    Path('build/review').mkdir(parents=True, exist_ok=True)
    sheet.save('build/review/things.png')
    print('build/review/things.png')
