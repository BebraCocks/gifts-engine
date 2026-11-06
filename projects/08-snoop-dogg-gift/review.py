"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from events import E

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.25, 1.6, E['real'] + 0.8, E['model'] + 0.9, E['profile'] + 1.0, E['million'] + 0.6, E['half'] + 0.5,
    E['three'] + 0.6, E['press'] + 0.3, E['nice'], E['friend'] + 0.25, E['what'] + 1.6, E['ten'] + 1.4,
    E['random'] + 0.2, E['pin'] + 0.6, E['f_comment'] + 0.5, E['f_snoop'] + 0.8, E['end'] - 0.1]
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
