"""Character sheets for the author's review: build/review/chars_*.png (one sheet per hero + lineup)."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chars as C  # noqa: E402

ROOT = HERE.parents[1]
OUT = HERE / 'build' / 'review'
FONT = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'


def font(size, w='Heavy'):
    return ImageFont.truetype(str(FONT / f'SF-Pro-Text-{w}.otf'), size)


def bg(w, h, top, bot):
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)) + (255,))
    return im


SHEETS = {
    'petya': ('Петя, 16', 'главный герой: школьник-скамер', (238, 232, 250), (204, 196, 232), [
        ('обычный', dict(smile=0.3), 'down'),
        ('сомневается', dict(sad=0.4, smile=-0.2, look=(-0.8, 0.2), brow=0.2), 'phone'),
        ('ухмылка манипулятора', dict(smirk=1.0, smile=0.4, look=(0.6, 0.3), glow=0.8), 'phone'),
        ('«Неужели всё так просто?»', dict(brow=0.8, open_=0.4, smile=0.4, look=(0, -0.4)), 'down'),
        ('торжество, смеётся', dict(smile=1.0, open_=0.9, teeth=1.0, blink=1.0), 'down'),
        ('насторожился', dict(sad=0.3, smile=-0.3, look=(-0.6, 0.0), sweat=1.0), 'phone'),
        ('«Зря ты это сделал…»', dict(shock=1.0, open_=0.6, smile=-0.6, sweat=1.0, glow=1.0), 'phone'),
        ('в капюшоне (за работой)', dict(smirk=0.7, smile=0.2, look=(0.4, 0.4), glow=1.0, hood=True), 'phone'),
    ]),
    'katya': ('Катя, 23', 'богатая девушка, не разбирается в NFT', (252, 236, 232), (240, 206, 200), [
        ('нежная улыбка', dict(smile=0.6), 'down'),
        ('влюблена в «Александра»', dict(smile=0.9, blink=0.875, glow=0.6), 'phone'),
        ('«Что-то случилось?»', dict(sad=0.8, brow=0.3, open_=0.3, smile=-0.3), 'phone'),
        ('молчит. Холодный взгляд', dict(anger=0.5, smile=-0.1, look=(0.3, 0.2), glow=0.7), 'phone'),
    ]),
    'alex': ('«Александр»', 'парень мечты из нейросети (маска Пети)', (230, 240, 252), (196, 214, 238), [
        ('фото профиля', dict(smile=0.7, open_=0.35, teeth=1.0), 'down'),
        ('уверенный', dict(smirk=0.6, smile=0.5, look=(0.4, 0)), 'down'),
    ]),
    'dima': ('Дима, 13', 'первая жертва: владелец NFT-календаря', (234, 246, 236), (198, 226, 204), [
        ('доверчивый', dict(smile=0.7), 'down'),
        ('«На 5 минут? Ладно…»', dict(sad=0.4, smile=0.2, look=(-0.5, 0.3), glow=0.6), 'phone'),
        ('«Ты лошара» + ЧС', dict(shock=1.0, sad=0.8, open_=0.7, smile=-0.7), 'phone'),
        ('плачет', dict(sad=1.0, blink=1.0, open_=0.5, smile=-0.8, sweat=1.0), 'down'),
    ]),
    'friends': ('Друзья Пети', 'на вечеринке «Всё за мой счёт!»', (250, 242, 222), (236, 214, 176), [
        ('Серый', dict(smile=0.9, open_=0.6, teeth=1.0), 'sery'),
        ('Ваня', dict(smile=1.0, open_=0.8, teeth=1.0, blink=1.0), 'vanya'),
    ]),
}


def cell(who, params, arms, label, w, h, S=0.62):
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    hd = C.head(who, **params)
    bd = C.BODIES[who](arms=arms, glow=params.get('glow', 0.0))
    C.place(im, C.bust(hd, bd, w / 2, h * 0.47, scale=S))
    d = ImageDraw.Draw(im)
    f = font(30, 'Semibold')
    tw = d.textlength(label, font=f)
    d.rounded_rectangle([w / 2 - tw / 2 - 18, h - 70, w / 2 + tw / 2 + 18, h - 22], 22, fill=(255, 255, 255, 230))
    d.text((w / 2 - tw / 2, h - 66), label, font=f, fill=(40, 36, 50))
    return im


def sheet(key):
    title, sub, top, bot, poses = SHEETS[key]
    cols = 4 if len(poses) > 4 else 2
    rows = (len(poses) + cols - 1) // cols
    cw, ch = (540, 640) if cols == 2 else (480, 600)
    W, H = cw * cols, 200 + ch * rows
    im = bg(W, H, top, bot)
    d = ImageDraw.Draw(im)
    d.text((48, 40), title, font=font(72), fill=(36, 30, 48))
    d.text((52, 128), sub, font=font(36, 'Medium'), fill=(80, 72, 96))
    for i, (label, params, arms) in enumerate(poses):
        who = key if key != 'friends' else arms
        a = 'down' if key == 'friends' else arms
        c = cell(who, params, a, label, cw, ch, S=0.62 if cols == 2 else 0.56)
        im.alpha_composite(c, ((i % cols) * cw, 200 + (i // cols) * ch))
    if key == 'friends':   # Telegram-only characters: avatars
        pass
    return im


def lineup():
    W, H = 2160, 1100
    im = bg(W, H, (246, 244, 250), (214, 210, 230))
    d = ImageDraw.Draw(im)
    d.text((48, 36), 'Петя и NFT · персонажи', font=font(68), fill=(36, 30, 48))
    who = [('dima', 'Дима', dict(smile=0.6), 0.5), ('petya', 'Петя', dict(smirk=0.8, smile=0.4), 0.56),
           ('alex', '«Александр»', dict(smile=0.7, open_=0.35, teeth=1.0), 0.6),
           ('katya', 'Катя', dict(smile=0.6), 0.56), ('sery', 'Серый', dict(smile=0.7), 0.54),
           ('vanya', 'Ваня', dict(smile=0.7), 0.54)]
    step = (W - 340) / (len(who) - 1)
    for i, (k, name, p, s) in enumerate(who):
        x = 170 + i * step
        C.place(im, C.bust(C.head(k, **p), C.BODIES[k](), x, 560 + (0.6 - s) * 300, scale=s))
        f = font(38)
        tw = d.textlength(name, font=f)
        d.text((x - tw / 2, 1010), name, font=f, fill=(36, 30, 48))
    # avatars
    for j, (k, name) in enumerate((('boss', 'Интернет-друг «Шеф»'), ('unknown', 'Последнее сообщение'))):
        av = C.avatar(k, 180)
        x0 = W - 860 + j * 420
        im.alpha_composite(av, (x0, 30))
        d.text((x0 + 190, 70), 'Шеф' if j == 0 else '???', font=font(30), fill=(36, 30, 48))
        d.text((x0 + 190, 112), 'интернет-друг' if j == 0 else 'финальное СМС', font=font(24, 'Medium'),
               fill=(90, 84, 104))
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    keys = sys.argv[1:] or list(SHEETS) + ['lineup']
    for k in keys:
        im = lineup() if k == 'lineup' else sheet(k)
        p = OUT / f'chars_{k}.png'
        im.convert('RGB').save(p, optimize=True)
        print(p.relative_to(ROOT), im.size)


if __name__ == '__main__':
    main()
