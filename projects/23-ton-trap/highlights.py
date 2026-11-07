"""Highlights for the author at OUTPUT time (with the RubUp break): build/review/hl_NN.png + highlights.png."""
from PIL import Image
import render as R
import sfxkit
from events import E

CONTENT = [E['h_3k'] + 0.6, E['h_500'] + 0.6, E['i_burn'] + 0.6, E['pe_pct'] + 0.8, E['lo_pct'] + 0.6, None,
           E['pc_pct'] + 0.8, E['pa_pct'] + 0.6, E['cp_then'] + 0.6, E['cp_pct'] + 0.5, E['o_which'] + 0.7,
           E['end'] - 0.1]
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
