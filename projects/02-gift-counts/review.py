"""Review sheet: python -B review.py out.png 0.5,4.6,... (content seconds; 'ad' = middle of the RubUp break)."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import render as R

out, spec = sys.argv[1], sys.argv[2]
ims = []
for s in spec.split(','):
    if s == 'ad':
        to = R.AD_STOP + 2.5
        label = 'RubUp'
    else:
        t = float(s)
        to = t if t < R.AD_STOP - 0.2 else t + R.BR.extra
        label = f'{t:.2f} s'
    im = Image.fromarray(R.BR.render(R.render_at, to))
    full = Path(R.HERE / 'build' / 'review' / f"t{label.replace(' ', '').replace(',', '_')}.png")
    full.parent.mkdir(parents=True, exist_ok=True)
    im.save(full)
    im = im.resize((432, 768))
    ImageDraw.Draw(im).text((10, 10), f'{label} (out {to:.2f})', fill=(255, 255, 0))
    ims.append(im)
cols = min(5, len(ims))
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 442, rows * 778), (255, 255, 255))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 442, (k // cols) * 778))
sheet.save(out)
print('->', out)
