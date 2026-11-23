"""Лист персонажей для согласования стиля: python -B projects/58-missed-new-year/sheet.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import chars
HERE = Path(__file__).resolve().parent
F = HERE.parents[1] / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Heavy.otf'
W, H = 2160, 1920
bg = Image.new('RGB', (W, H), (22, 30, 58))
d = ImageDraw.Draw(bg)
for y in range(H):
    c = int(22 + 30 * y / H); d.line((0, y, W, y), fill=(c, c + 10, c + 40))
rows = [('Мисед', [chars.missed({}), chars.missed({'eyes': 'narrow', 'mouth': 'flat'}), chars.missed({'eyes': 'half', 'mouth': 'smirk', 'look': 0.6, 'arms': 'down'})]),
        ('Димон', [chars.dimon({'arms': 'down'}), chars.dimon({'eyes': 'wide', 'mouth': 'grin', 'arms': 'up'}), chars.dimon({'eyes': 'half', 'mouth': 'flat', 'look': -0.5, 'arms': 'phone'})]),
        ('Олег', [chars.oleg({'mouth': 'smirk', 'eyes': 'half', 'arms': 'hips'}), chars.oleg({'eyes': 'open', 'mouth': 'flat', 'arms': 'phone'}), chars.oleg({'eyes': 'wide', 'mouth': 'shock', 'angry_brows': False, 'arms': 'up'})])]
f = ImageFont.truetype(str(F), 64)
for r, (name, ims) in enumerate(rows):
    y0 = 40 + r * 630
    d.text((60, y0 + 20), name, font=f, fill='white')
    for c, im in enumerate(ims):
        s = 560 / im.height
        im2 = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        bg.paste(im2, (360 + c * 600, y0 + 30), im2)
out = HERE / 'build' / 'review'; out.mkdir(parents=True, exist_ok=True)
bg.save(out / 'chars_sheet_v2.jpg', quality=92); print(out / 'chars_sheet_v2.jpg')
