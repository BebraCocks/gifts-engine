"""Широкий баннер 3800×1000 (≈3,8:1): картинка Fish (Мита слева) + «Мита о Гифтах» справа (Unbounded)
+ бледные настоящие NFT-модели (gifts_api) сверху и снизу надписи как декор. python3 make_banner_wide.py вход.jpg выход.png"""
import math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G
F = Path(__file__).resolve().parents[1] / 'input' / 'fonts'
W, H = 3800, 1000
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert('RGBA')
s = H / im.height
im = im.resize((int(im.width * s), H), Image.LANCZOS)
if im.width < W:                                    # дотянуть фон вправо крайним столбцом
    ext = Image.new('RGBA', (W, H)); ext.paste(im, (0, 0))
    edge = im.crop((im.width - 2, 0, im.width, H)).resize((W - im.width, H))
    ext.paste(edge, (im.width, 0)); im = ext
im = im.crop((0, 0, W, H))
INK, PINK = (30, 24, 48), (226, 54, 120)
font = lambda w, z: ImageFont.truetype(str(F / f'Unbounded-{w}.ttf'), z)
f1 = font('ExtraBold', 190)
d0 = ImageDraw.Draw(im)
t1, t2 = 'Мита ', 'о Гифтах'
tw = d0.textlength(t1, font=f1) + d0.textlength(t2, font=f1)
x = int(W * 0.30); cx = int(x + tw / 2); y = int(H / 2 - 120)
box = (x - 60, y - 40, x + tw + 60, y + 250)
# декор: бледные NFT-модели сверху и снизу надписи
gifts = [('Ginger Cookie', 'Sweetheart'), ('Love Potion', 'Milkshake'), ('Big Year', 'Cyberpunk'), ('Santa Hat', 'Inky White'),
         ('Whip Cupcake', 'Sweetheart'), ('Jester Hat', 'Neon White'), ('Clover Pin', 'Lollipop'), ('Gem Signet', 'Moonstone'),
         ('Snoop Dogg', 'Sapphire'), ('Precious Peach', 'Malachite'), ('Eternal Rose', 'Moonstone'), ('Spiced Wine', 'Persimmon')]
rnd = random.Random(7)
deco = Image.new('RGBA', (W, H), (0, 0, 0, 0))
xs = [int(W * 0.30 + i * (W * 0.66) / 6) for i in range(7)]
spots = [(xx + rnd.randint(-40, 40), rnd.randint(60, 150)) for xx in xs] + [(xx + 120 + rnd.randint(-40, 40), rnd.randint(H - 170, H - 70)) for xx in xs[:6]]
for k, (px, py) in enumerate(spots):
    g, m = gifts[k % len(gifts)]
    p = Image.open(G.model_png(g, m, size=256)).convert('RGBA')
    sz = rnd.randint(120, 170)
    p = p.resize((sz, sz), Image.LANCZOS).rotate(rnd.uniform(-18, 18), expand=True, resample=Image.BICUBIC)
    p = ImageEnhance.Color(p).enhance(0.75)
    a = p.getchannel('A').point(lambda v: int(v * 0.24)); p.putalpha(a)
    deco.alpha_composite(p, (px - p.width // 2, py - p.height // 2))
im.alpha_composite(deco)
lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
d.text((x, y), t1, font=f1, fill=PINK + (255,))
d.text((x + d.textlength(t1, font=f1), y), t2, font=f1, fill=INK + (255,))
sh = Image.new('RGBA', (W, H), (255, 255, 255, 0)); sh.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.35)))
im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18))); im.alpha_composite(lay)
im.convert('RGB').save(dst, quality=95)
print(dst, im.size)
