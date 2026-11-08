"""Highlights for the author at OUTPUT time (with the RubUp break): build/review/hl_NN.png + highlights.png."""
from PIL import Image
import render as R
import sfxkit
from timeline import ROUND_IN, TIMER0, REVEAL, OUTRO
from events import E

CONTENT = [0.05, E['more'] + 0.8, TIMER0[0] + 2.5, REVEAL[0] + 1.6, REVEAL[1] + 1.6, REVEAL[2] + 2.0, None,
           ROUND_IN[3] + 0.05, TIMER0[4] + 4.4, REVEAL[4] + 1.8, E['sum'] + 2.0, E['end'] - 0.05]
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
