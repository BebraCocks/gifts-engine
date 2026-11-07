"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from events import E

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.05, E['crazy'] + 0.4, E['copy'] + 0.2, E['goal'] + 0.3, E['price1'] + 0.6, E['h11'] + 0.4, E['h10'] + 0.6,
    E['p_took'] + 0.4, E['p_gift'] + 0.8, E['b7000'] + 1.0, E['b34'] + 0.6, E['c15'] + 0.3, E['c3000'] + 0.5,
    E['q2'] + 0.3, E['q100'] + 0.5, E['t761'] + 1.0, E['t35'] + 0.5, E['o_cap'] + 0.2, E['end'] - 0.1]
ims = []
for t in TS:
    im = Image.fromarray(R.render_at(t))
    im.save(f'build/review/f_{t:05.2f}.png')
    ims.append(im.resize((270, 480), Image.LANCZOS))
cols = 7
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 270, rows * 480), (0, 0, 0))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
sheet.save('build/review/sheet.png')
print('ok', [round(t, 2) for t in TS])
