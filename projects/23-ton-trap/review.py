"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from events import E

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    E['h_228'] + 0.5, E['h_119'] + 1.0, E['i_ton'] + 0.6, E['i_melt'] + 0.8, E['ca_then'] + 0.5, E['ca_pct'] + 0.6,
    E['du_pct'] + 0.6, E['se_pct'] + 0.6, E['re_then'] + 0.5, E['re_pct'] + 0.6, E['o_out'] + 0.4, E['end'] - 0.1]
ims = []
for t in TS:
    im = Image.fromarray(R.render_at(t))
    im.save(f'build/review/f_{t:05.2f}.png')
    ims.append(im.resize((270, 480), Image.LANCZOS))
cols = 6
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 270, rows * 480), (0, 0, 0))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
sheet.save('build/review/sheet.png')
print('ok', [round(t, 2) for t in TS])
