"""Баннер v2 (2026-11-21): картинка ChatGPT автора (Мита слева на голубом) целиком, без обрезки сверху/снизу,
вписана по высоте в 3200×1200 (≈2,67:1 — окно обрезки приложения) и сдвинута вправо в видимую зону профиля;
фон дотянут крайними столбцами. Надпись «Мита о гифтах» (Unbounded) — справа сверху, вне зоны кнопок и имени.
Видимая зона профиля TikTok (скриншот автора): x ≈0,12–0,87 W; снизу ≈0,62 H — имя; x > 0,63 W, y 0,28–0,47 H — кнопки.
python3 make_banner_v2.py banner_v2_raw.png banner_v2.png"""
import random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G
F = Path(__file__).resolve().parents[1] / 'input' / 'fonts'
W, H = 3200, 1200
src, dst = sys.argv[1], sys.argv[2]
art = Image.open(src).convert('RGBA')
s = H / art.height
art = art.resize((round(art.width * s), H), Image.LANCZOS)
X0 = 330                                             # сдвиг вправо: Мита целиком в видимой зоне (с 0,12 W)
im = Image.new('RGBA', (W, H))
im.paste(art, (X0, 0))
# фон влево: цвет фона по строкам левого края картинки, где волосы — интерполяция между строками фона
import numpy as np
col = np.array(art.crop((0, 0, 1, H)))[:, 0, :3].astype(float)
lum = col.mean(1)
ok = (col[:, 2] > 225) & (col[:, 1] > 100) & (col[:, 0] < 140)        # только голубой фон (без волос, руки, бликов)
rows = np.arange(H)
for c in range(3):
    col[:, c] = np.interp(rows, rows[ok], col[ok, c])
k = np.ones(81) / 81
col = np.stack([np.convolve(np.pad(col[:, c], 40, mode='edge'), k, 'valid') for c in range(3)], 1)
left = np.repeat(col[:, None, :], X0, 1)
left *= np.linspace(0.92, 1.0, X0)[None, :, None]          # к краю чуть темнее (как виньетка справа)
im.paste(Image.fromarray(left.clip(0, 255).astype(np.uint8)).convert('RGBA'), (0, 0))
fade = Image.new('L', (40, H)); fade.putdata([int(255 * (i % 40) / 39) for i in range(40 * H)])
im.paste(art.crop((0, 0, 40, H)), (X0, 0), Image.linear_gradient('L').rotate(90).resize((40, H)))
im.paste(art.crop((art.width - 2, 0, art.width, H)).resize((W - X0 - art.width, H)), (X0 + art.width, 0))   # вправо
font = lambda w, z: ImageFont.truetype(str(F / f'Unbounded-{w}.ttf'), z)
# декор: бледные настоящие NFT-модели справа, вне надписи и вне зоны кнопок
gifts = [('Ginger Cookie', 'Sweetheart'), ('Love Potion', 'Milkshake'), ('Big Year', 'Cyberpunk'), ('Santa Hat', 'Inky White'),
         ('Whip Cupcake', 'Sweetheart'), ('Jester Hat', 'Neon White'), ('Clover Pin', 'Lollipop'), ('Gem Signet', 'Moonstone')]
spots = [(0.80, 0.12), (0.92, 0.20), (0.97, 0.55), (0.88, 0.70), (0.70, 0.62), (0.56, 0.58), (0.76, 0.86), (0.60, 0.85)]
rnd = random.Random(11)
deco = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for k, (fx_, fy_) in enumerate(spots):
    g, m = gifts[k % len(gifts)]
    p = Image.open(G.model_png(g, m, size=256)).convert('RGBA')
    sz = rnd.randint(120, 160)
    p = p.resize((sz, sz), Image.LANCZOS).rotate(rnd.uniform(-16, 16), expand=True, resample=Image.BICUBIC)
    p.putalpha(p.getchannel('A').point(lambda v: int(v * 0.30)))
    deco.alpha_composite(p, (int(W * fx_) - p.width // 2, int(H * fy_) - p.height // 2))
im.alpha_composite(deco)
# надпись: «Мита» — красная (цвет её свитера) с белой обводкой, «о гифтах» — белая с тёмной обводкой
RED, WHITE, NAVY = (226, 40, 52), (255, 255, 255), (22, 30, 80)
f1, f2 = font('ExtraBold', 160), font('ExtraBold', 106)
x, y1 = int(W * 0.40), int(H * 0.07)
lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
d.text((x, y1), 'Мита', font=f1, fill=RED + (255,), stroke_width=10, stroke_fill=WHITE + (255,))
y2 = y1 + 192
d.text((x + 8, y2), 'о гифтах', font=f2, fill=WHITE + (255,), stroke_width=9, stroke_fill=NAVY + (255,))
sh = Image.new('RGBA', (W, H), (10, 20, 70, 0)); sh.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.45)))
im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)), (6, 10)); im.alpha_composite(lay)
im.convert('RGB').save(dst, quality=95)
print(dst, im.size, 'надпись до x = %.3f W; низ %.3f H' % ((x + max(d.textlength('Мита', font=f1), d.textlength('о гифтах', font=f2))) / W, (y2 + 125) / H))
