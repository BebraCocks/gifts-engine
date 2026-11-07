"""Highlights for the author at OUTPUT time (with the RubUp break): build/review/hl_NN.png + highlights.png."""
from PIL import Image
import render as R
import sfxkit
from events import E

CONTENT = [E['h_end'] + 0.6, E['i_b'] + 0.6, E['q1_thing'] + 1.0, E['q2_thing'] + 1.0, None, E['q3_thing'] + 1.2,
           E['q4_thing'] + 1.0, E['q5_thing'] + 1.0, E['t_today'] + 1.0, E['t_car'] + 0.8, E['o_write'] + 1.5, E['end'] - 0.1]
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
