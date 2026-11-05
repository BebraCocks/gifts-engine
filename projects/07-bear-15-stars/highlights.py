"""Highlights for the author at OUTPUT time (with the RubUp break): build/review/hl_NN.png + highlights.png."""
from PIL import Image
import render as R
import sfxkit

CONTENT = [1.6, 5.6, 8.6, 12.5, 17.5, 20.6, 23.4, 27.9, 32.0, 36.0, None, 40.6, 42.9, 47.6, 50.5, 56.5, 60.5, 66.5]
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
