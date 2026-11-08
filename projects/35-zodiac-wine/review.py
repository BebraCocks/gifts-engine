"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from timeline import SIGN_IN, OUTRO, END, KEY
from events import E, FORECAST

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.0, 1.0, E['twelve'] + 0.4, E['four'] + 0.8, SIGN_IN[0] - 0.3, SIGN_IN[0] + 0.5,
    SIGN_IN[0] + 2.5, FORECAST[0] + 0.4, SIGN_IN[1] - 0.6, SIGN_IN[1] + 2.0, FORECAST[1] + 2.0, END[KEY['s2']] + 0.4,
    SIGN_IN[2] + 2.0, FORECAST[2] + 1.5, SIGN_IN[3] + 2.0, FORECAST[3] + 1.5, OUTRO + 0.8, E['end'] - 0.1]
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
