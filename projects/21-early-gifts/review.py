"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from events import E

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.05, E['h_gift'] + 0.5, E['h_phone'] + 0.3, E['c_early'] + 0.3, E['w15'] + 0.5, E['w_crumbs'] + 0.5,
    E['w7k'] + 0.9, E['w50'] + 0.8, E['w20'] + 0.5, E['w10'] + 0.6, E['w_phone'] + 0.6, E['c15'] + 0.4,
    E['c_pizza'] + 0.3, E['c_caps'] + 0.4, E['c_phone'] + 0.6, E['p30'] + 0.4, E['p_kino'] + 0.5, E['p649'] + 1.0,
    E['p3'] + 0.9, E['o_which'] + 0.6, E['end'] - 0.1]
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
