"""Contact sheet of content-time stills: python -B review.py [t1,t2,...] -> build/review/sheet.png + stills."""
import sys
from PIL import Image
import render as R
from events import E

TS = [float(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else [
    0.05, 2.5, E['n2'] + 0.5, E['n4'] + 0.6, E['million'] + 0.6, E['usd'] + 0.6, E['series'] + 0.4,
    E['papakha'] + 0.4, E['k29'] + 1.3, E['day'] + 0.3, E['accused'] + 0.8, E['release'] + 0.4,
    E['first'] + 0.6, E['price'] + 0.6, E['e119'] + 1.0, E['e40'] + 0.6, E['g18'] + 1.0, E['car'] + 1.2,
    E['o_snoop'] + 0.2, E['o_durov'] + 0.3, E['end'] - 0.1]
ims = []
for t in TS:
    im = Image.fromarray(R.render_at(t))
    im.save(f'build/review/f_{t:05.2f}.png')
    ims.append(im.resize((270, 480), Image.LANCZOS))
cols = 7
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 270, rows * 480), (0, 0, 0))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
sheet.save('build/review/sheet.png')
print('ok', [round(t, 2) for t in TS])
