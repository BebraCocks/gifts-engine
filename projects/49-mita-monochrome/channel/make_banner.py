"""Баннер канала: картинка Fish (без текста) + надпись Unbounded слева. python3 make_banner.py вход.jpg выход.png"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
F = Path(__file__).resolve().parents[1] / 'input' / 'fonts'
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGBA')
W, H = im.size
INK, PINK, MUTED = (30, 24, 48), (226, 54, 120), (118, 112, 140)
def font(w, s): return ImageFont.truetype(str(F / f'Unbounded-{w}.ttf'), s)
k = W / 2560
lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
x = int(W * 0.08); y = int(H * 0.36)
f1, f2, f3 = font('ExtraBold', int(170 * k)), font('SemiBold', int(70 * k)), font('SemiBold', int(54 * k))
d.text((x, y), 'Мита', font=f1, fill=PINK + (255,))
wm = d.textlength('Мита ', font=f1)
d.text((x + wm, y), '· Гифты', font=f1, fill=INK + (255,))
d.text((x + 6 * k, y + 205 * k), 'подарки в телеге без воды', font=f2, fill=INK + (255,))
d.text((x + 6 * k, y + 300 * k), '@mitagifts', font=f3, fill=MUTED + (255,))
sh = lay.copy(); sh.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.25)))
sh = Image.merge('RGBA', (*[Image.new('L', im.size, 255)] * 3, sh.getchannel('A'))).filter(ImageFilter.GaussianBlur(10 * k))
im.alpha_composite(sh); im.alpha_composite(lay)
im.convert('RGB').save(dst, quality=95)
print(dst, im.size)
