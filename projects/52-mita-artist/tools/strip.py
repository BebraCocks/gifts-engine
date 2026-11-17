"""Лента поз с номерами — референс для ChatGPT «нарисуй позу между №N и №N+1».
python3 tools/strip.py выход.png поза1 поза2 ... (кадры из input/mita/frames, выровнены по голове+ногам)"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anim
import snap_preview as SP
out, names = sys.argv[1], sys.argv[2:]
SP.align_all(names)
cw, ch = 300, 512
cols = min(len(names), 6)
rows = (len(names) + cols - 1) // cols
im = Image.new('RGB', (cols * cw, rows * (ch + 40)), (0, 255, 0))
d = ImageDraw.Draw(im)
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
for i, n in enumerate(names):
    a = Image.open(SP.AL / f'{n}.png')
    a = a.crop((134, 0, 634, 1024)).resize((250, 512))
    x, y = (i % cols) * cw, (i // cols) * (ch + 40)
    im.paste(a, (x + 25, y + 40), a)
    d.rectangle([x + 8, y + 2, x + 70, y + 40], fill=(255, 255, 255))
    d.text((x + 14, y + 2), str(i + 1), fill=(0, 0, 0), font=f)
im.save(out)
print(out, im.size)
