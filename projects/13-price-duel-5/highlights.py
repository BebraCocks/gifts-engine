"""Highlights for the author at OUTPUT time (with the RubUp break): build/review/hl_NN.png + highlights.png."""
from PIL import Image
import render as R
import sfxkit
from timeline import ROUND_IN, TIMER0, REVEAL, OUTRO
from events import E

CONTENT = [0.05, TIMER0[0] + 2.4, REVEAL[0] + 1.0, REVEAL[1] + 1.0, REVEAL[2] + 1.0, None,
           TIMER0[3] + 3.3, REVEAL[3] + 1.0, TIMER0[4] + 4.5, REVEAL[4] + 1.2, E['comments'] + 0.8, E['end'] - 0.1]
ims = []
for k, ct in enumerate(CONTENT):
    ot = R.AD_STOP + 3.0 if ct is None else sfxkit.out_time(R.BR, ct)
    im = Image.fromarray(R.BR.render(R.render_at, ot))
    im.save(f'build/review/hl_{k + 1:02d}.png')
    ims.append(im.resize((360, 640), Image.LANCZOS))
    print(k + 1, round(ot, 2))
cols = 6
sheet = Image.new('RGB', (cols * 360, 2 * 640))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 360, (k // cols) * 640))
sheet.save('build/review/highlights.png')
