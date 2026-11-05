"""Stills at content times for checking shots: python -B review.py 0.5,3.8,... [--sheet name]"""
import sys
import time
from PIL import Image
import render as R

ts = [float(x) for x in sys.argv[1].split(',')]
name = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '--sheet' else 'sheet'
out = R.paths.build(R.HERE) / 'review'
out.mkdir(parents=True, exist_ok=True)
ims = []
for t in ts:
    t0 = time.time()
    im = Image.fromarray(R.render_at(t))
    print(f'{t:6.2f}  {time.time() - t0:5.2f} s', flush=True)
    im.save(out / f'c{t:05.2f}.png')
    ims.append(im.resize((360, 640), Image.LANCZOS))
cols = min(6, len(ims))
sheet = Image.new('RGB', (cols * 360, ((len(ims) + cols - 1) // cols) * 640))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 360, (k // cols) * 640))
sheet.save(out / f'{name}.png')
print(out / f'{name}.png')
