"""Лист контрольных кадров: python -B sheet.py t1,t2,... (время содержания) -> build/review/sheet.jpg"""
import sys, time
from PIL import Image
import render as R
ts = [float(x) for x in sys.argv[1].split(',')]
ims = []
t0 = time.time()
for t in ts:
    ims.append(Image.fromarray(R.render_at(t)).resize((270, 480)))
print('s/frame', round((time.time() - t0) / len(ts), 3))
cols = 8
rows = (len(ims) + cols - 1) // cols
sh = Image.new('RGB', (270 * cols, 480 * rows), 'black')
for k, im in enumerate(ims):
    sh.paste(im, ((k % cols) * 270, (k // cols) * 480))
sh.save(R.HERE / 'build' / 'review' / (sys.argv[2] if len(sys.argv) > 2 else 'sheet.jpg'), quality=85)
