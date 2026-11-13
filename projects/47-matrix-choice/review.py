"""Contact sheet of OUTPUT-time stills (with the RubUp break): python -B review.py [ct1,ct2,...|ad:u1,u2] ->
build/review/sheet.png + full frames build/review/s_NN.png. Content times are mapped through the break."""
import sys
from PIL import Image
import render as R
import sfxkit
from timeline import ROUND_IN, TIMER0, REVEAL, OUTRO, DUR
from events import E, TRICK_NFT, TRICK_THING, LOSE_T, WIN_GONE, FISTS, AD_STOP

def out(ct):
    return sfxkit.out_time(R.BR, ct)

if len(sys.argv) > 1 and sys.argv[1].startswith('ad:'):
    o0 = AD_STOP - 0.2
    TS = [o0 + float(x) for x in sys.argv[1][3:].split(',')]
elif len(sys.argv) > 1:
    TS = [out(float(x)) for x in sys.argv[1].split(',')]
else:
    TS = [out(x) for x in (0.05, 0.6, 1.2, 1.9, 3.0, ROUND_IN[0] + 0.3, TRICK_NFT[0][0] + 0.5, TRICK_THING[0][0] + 0.9,
                           REVEAL[0] + 0.5, LOSE_T[0] + 0.4, TRICK_THING[1][0] + 0.4, LOSE_T[1] + 0.5)]
ims = []
for k, t in enumerate(TS):
    im = Image.fromarray(R.BR.render(R.render_at, t))
    im.save(f'build/review/s_{k:02d}.png')
    ims.append(im.resize((270, 480), Image.LANCZOS))
cols = 6
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * 270, rows * 480))
for k, im in enumerate(ims):
    sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
sheet.save('build/review/sheet.png')
print('ok', [round(t, 2) for t in TS])
