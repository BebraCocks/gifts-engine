"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from timeline import ROUND_IN, TIMER0, REVEAL, OUTRO
from events import E

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.3, 1.2, E['hook_q'] + 0.5, ROUND_IN[0] + 0.7, TIMER0[0] + 3.2, REVEAL[0] + 0.9,
    ROUND_IN[1] + 0.25, TIMER0[1] + 4.3, REVEAL[1] + 1.0, REVEAL[2] + 1.0, TIMER0[3] + 2.0, REVEAL[3] + 1.0,
    TIMER0[4] + 4.6, REVEAL[4] + 0.4, REVEAL[4] + 1.5, OUTRO + 0.8, E['comments'] + 0.8, E['end'] - 0.1]
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
