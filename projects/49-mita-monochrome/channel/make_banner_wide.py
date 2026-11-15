"""Широкий баннер 3800×1000 (≈3,8:1): картинка Fish (Мита слева) + «Мита о Гифтах» справа (Unbounded)
+ бледные настоящие NFT-модели (gifts_api) сверху и снизу надписи как декор. python3 make_banner_wide.py вход.jpg выход.png"""
import math, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G
F = Path(__file__).resolve().parents[1] / 'input' / 'fonts'
W, H = 3200, 1200          # пропорции ≈2,67:1 — как в окне обрезки приложения
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
f1 = font('ExtraBold', 140)
# Видимая зона профиля TikTok (по скриншоту автора): по горизонтали ≈0,12–0,87 W; снизу ≈0,62 H закрывает имя;
# справа (x > 0,63 W, y 0,28–0,47 H) — кнопки. Надпись — в две строки вплотную к Мите, в верхней части.
x = int(W * 0.318); y = int(H * 0.12)
lines = [('Мита', PINK), ('про гифты', INK)]
LH = 178
# декор: бледные NFT-модели справа и под надписью, вне зоны текста
gifts = [('Ginger Cookie', 'Sweetheart'), ('Love Potion', 'Milkshake'), ('Big Year', 'Cyberpunk'), ('Santa Hat', 'Inky White'),
         ('Whip Cupcake', 'Sweetheart'), ('Jester Hat', 'Neon White'), ('Clover Pin', 'Lollipop'), ('Gem Signet', 'Moonstone'),
         ('Snoop Dogg', 'Sapphire'), ('Precious Peach', 'Malachite'), ('Eternal Rose', 'Moonstone'), ('Spiced Wine', 'Persimmon')]
rnd = random.Random(7)
deco = Image.new('RGBA', (W, H), (0, 0, 0, 0))
spots = [(0.70, 0.10), (0.79, 0.20), (0.88, 0.09), (0.94, 0.27), (0.72, 0.52), (0.83, 0.60), (0.93, 0.50),
         (0.40, 0.56), (0.50, 0.62), (0.60, 0.55), (0.45, 0.85), (0.62, 0.82), (0.78, 0.86)]
for k, (fx_, fy_) in enumerate(spots):
    px, py = int(W * fx_ + rnd.randint(-30, 30)), int(H * fy_ + rnd.randint(-20, 20))
    g, m = gifts[k % len(gifts)]
    p = Image.open(G.model_png(g, m, size=256)).convert('RGBA')
    sz = rnd.randint(120, 165)
    p = p.resize((sz, sz), Image.LANCZOS).rotate(rnd.uniform(-18, 18), expand=True, resample=Image.BICUBIC)
    p = ImageEnhance.Color(p).enhance(0.75)
    p.putalpha(p.getchannel('A').point(lambda v: int(v * 0.24)))
    deco.alpha_composite(p, (px - p.width // 2, py - p.height // 2))
im.alpha_composite(deco)
lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
for j, (t_, col) in enumerate(lines):
    d.text((x, y + j * LH), t_, font=f1, fill=col + (255,))
sh = Image.new('RGBA', (W, H), (255, 255, 255, 0)); sh.putalpha(lay.getchannel('A').point(lambda v: int(v * 0.35)))
im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18))); im.alpha_composite(lay)
im.convert('RGB').save(dst, quality=95)
print(dst, im.size)
