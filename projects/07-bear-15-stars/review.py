"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.5, 1.4, 3.4, 5.6, 8.6, 11.8, 16.5, 18.9, 21.0, 23.6, 27.9, 30.5, 32.8, 35.6, 38.4, 40.9, 42.9, 47.6,
    50.5, 55.0, 57.5, 60.0, 63.0, 67.5]
ims = []
for t in TS:
    im = Image.fromarray(R.render_at(t))
    im.save(f'build/review/f_{t:05.1f}.png')
    ims.append(im.resize((270, 480)))
cols = 6
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 270, rows * 480), (0, 0, 0))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
sheet.save('build/review/sheet.png')
print('ok', len(ims))
