"""Content-time stills and a contact sheet: python -B review.py t1,t2,... [name]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
from PIL import Image, ImageDraw
import fx
import render as R

ts = [float(x) for x in sys.argv[1].split(',')]
name = sys.argv[2] if len(sys.argv) > 2 else 'sheet'
out = HERE / 'build' / 'review'
out.mkdir(parents=True, exist_ok=True)
cols = min(6, len(ts))
rows = (len(ts) + cols - 1) // cols
sw, sh = 270, 480
sheet = Image.new('RGB', (cols * sw, rows * (sh + 30)), (20, 20, 24))
d = ImageDraw.Draw(sheet)
for i, t in enumerate(ts):
    im = Image.fromarray(R.render_at(t))
    im.save(out / f'c{t:07.2f}.png')
    sheet.paste(im.resize((sw, sh)), ((i % cols) * sw, (i // cols) * (sh + 30)))
    d.text(((i % cols) * sw + 8, (i // cols) * (sh + 30) + sh + 4), f'{t:.2f}', font=fx.font('Semibold', 20), fill=(255, 255, 255))
sheet.save(out / f'{name}.png')
print(out / f'{name}.png')
