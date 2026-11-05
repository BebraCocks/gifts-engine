"""Review sheet: python -B review.py out.png 0.5,4.6,... (content seconds; 'ad' = middle of the RubUp break).
Full frames go to build/review/t<sec>.png."""
import sys
from PIL import Image, ImageDraw
import render as R

out, spec = sys.argv[1], sys.argv[2]
ims = []
for s in spec.split(','):
    if s == 'ad':
        to = R.E.AD_STOP + 3.0
        label = 'RubUp'
    else:
        t = float(s)
        to = t if t < R.E.AD_STOP - 0.2 else t + R.BR.extra
        label = f'{t:.2f}s'
    im = Image.fromarray(R.BR.render(R.render_at, to))
    full = R.HERE / 'build' / 'review' / f"t{label}.png"
    full.parent.mkdir(parents=True, exist_ok=True)
    im.save(full)
    im = im.resize((360, 640))
    ImageDraw.Draw(im).text((8, 8), f'{label} (out {to:.2f})', fill=(255, 255, 0))
    ims.append(im)
cols = min(6, len(ims))
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 366, rows * 646), (255, 255, 255))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 366, (k // cols) * 646))
sheet.save(out)
print('->', out)
