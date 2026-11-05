"""Highlights for the author at OUTPUT time (with the RubUp break): build/review/hl_NN.png + highlights.png."""
from PIL import Image
import render as R
import sfxkit

from events import S, E
CONTENT = [E['price'] + 0.2, E['best'] + 0.5, E['stamp1'] + 0.4, E['rich'] + 0.3, E['luck'] + 0.3, E['gift_in'] + 0.8,
           E['ban'] + 1.9, E['effect'] + 0.5, E['sign_up'] + 0.5, E['coin'] + 0.3, None, E['spotted'] + 0.5,
           E['dust'] + 0.5, E['full'] + 0.3, E['couch'], E['send'] - 0.3, E['ask'] + 0.3, E['bear_wave']]
ims = []
for k, ct in enumerate(CONTENT):
    ot = R.AD_STOP + 3.2 if ct is None else sfxkit.out_time(R.BR, ct)
    im = Image.fromarray(R.BR.render(R.render_at, ot))
    im.save(f'build/review/hl_{k + 1:02d}.png')
    ims.append(im.resize((360, 640), Image.LANCZOS))
    print(k + 1, round(ot, 2))
cols = 6
sheet = Image.new('RGB', (cols * 360, 3 * 640))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 360, (k // cols) * 640))
sheet.save('build/review/highlights.png')
