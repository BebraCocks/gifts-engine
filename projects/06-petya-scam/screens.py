"""Other phone screens: the dating-site profile, the «transfer gifts» sheet, a toast. All own drawing."""
import functools

from PIL import Image, ImageDraw, ImageFilter

import tg
from tg import SCREEN, font, draw_text, text_width


def _ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


WANTS = ['высокий брюнет, 27–30 лет', 'лёгкая щетина, стильный', 'своё дело, уверенный', 'любит путешествия и собак']


@functools.lru_cache(maxsize=2)
def _dating_base(photo_key):
    import chars as C
    w, h = SCREEN
    im = Image.new('RGBA', (w, h), (255, 246, 248, 255))
    d = ImageDraw.Draw(im)
    tg._status_bar(im, tg.THEMES['day'], '02:47')
    d.text((w / 2, 170), 'Знакомства', font=font('Heavy', 44), fill=(236, 64, 110), anchor='mm')
    draw_text(im, (w / 2 + font('Heavy', 44).getlength('Знакомства') / 2 + 8, 146), '💘', font('Heavy', 44),
              (0, 0, 0))
    # photo card
    card = Image.new('RGBA', (820, 760), (0, 0, 0, 0))
    m = Image.new('L', card.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 819, 759], 40, fill=255)
    bg = Image.new('RGBA', card.size, (250, 196, 190, 255))
    gd = ImageDraw.Draw(bg)
    for y in range(760):
        k = y / 759
        gd.line([(0, y), (820, y)], fill=(int(252 - 40 * k), int(206 - 70 * k), int(196 - 30 * k), 255))
    head = C.head('katya', smile=0.65)
    body = C.katya_body()
    tmp = Image.new('RGBA', (820, 1100), (0, 0, 0, 0))
    C.place(tmp, C.bust(head, body, 410, 560, scale=1.05))
    bg.alpha_composite(tmp.crop((0, 0, 820, 760)))
    card.paste(bg, (0, 0), m)
    sh = Image.new('RGBA', (880, 820), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([30, 40, 850, 800], 40, fill=(160, 60, 90, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    im.alpha_composite(sh, (30, 220))
    im.alpha_composite(card, (60, 240))
    shade_ = Image.new('RGBA', (820, 220), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade_)
    for y in range(220):
        sd.line([(0, y), (820, y)], fill=(60, 20, 40, int(150 * y / 219)))
    m2 = m.crop((0, 540, 820, 760))
    im.paste(Image.alpha_composite(im.crop((60, 780, 880, 1000)), shade_), (60, 780), m2)
    d.text((100, 878), 'Катя, 23', font=font('Heavy', 58), fill=(255, 255, 255))
    d.text((102, 948), 'Москва · 2 км', font=font('Semibold', 32), fill=(255, 255, 255))
    d.text((70, 1050), 'Обо мне: люблю море, кофе и честных людей', font=font('Regular', 32), fill=(110, 96, 110))
    d.text((60, 1160), 'Ищу:', font=font('Heavy', 46), fill=(40, 30, 40))
    return im


def dating_screen(t, t0, hl_times):
    """Profile screen; WANTS lines appear from t0, a marker sweeps over line k at hl_times[k]."""
    im = _dating_base('katya').copy()
    d = ImageDraw.Draw(im, 'RGBA')
    f = font('Semibold', 40)
    for k, s in enumerate(WANTS):
        a = _ease((t - (t0 + 0.15 * k)) / 0.3)
        if a <= 0:
            continue
        y = 1290 + k * 92
        if k < len(hl_times):
            hk = _ease((t - hl_times[k]) / 0.35)
            if hk > 0:
                wv = f.getlength(s) + 60
                d.rounded_rectangle([64, y - 6, 64 + wv * hk, y + 62], 14, fill=(255, 226, 90, 200))
        dot = (236, 64, 110, int(255 * a))
        d.ellipse([70, y + 18, 90, y + 38], fill=dot)
        d.text((110 + (1 - a) * 30, y), s, font=f, fill=(40, 30, 40, int(255 * a)))
    return im


def transfer_sheet(im, t, t0, t1, gifts, to_avatar):
    """Bottom sheet «Передать подарки» (t0..t1), the button is pressed at t1 - 0.35, then a toast."""
    w, h = SCREEN
    if t0 <= t < t1 + 0.25:
        k = _ease((t - t0) / 0.3) * (1 - _ease((t - t1) / 0.25))
        dim = Image.new('RGBA', (w, h), (0, 0, 0, int(110 * k)))
        im.alpha_composite(dim)
        sh_h = 860
        y0 = int(h - sh_h * k)
        sheet = Image.new('RGBA', (w, sh_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(sheet)
        d.rounded_rectangle([0, 0, w, sh_h + 60], 44, fill=(28, 32, 42, 255))
        d.rounded_rectangle([w / 2 - 40, 16, w / 2 + 40, 24], 4, fill=(90, 96, 110))
        d.text((w / 2, 82), 'Передать подарки', font=font('Heavy', 44), fill=(244, 246, 250), anchor='mm')
        for i, (name, model) in enumerate(gifts):
            g = tg.lottie.frame(str(tg.G.model_file(name, model, 'json')), t - t0 + i * 0.3, size=200)
            cx = w / 2 + (i - (len(gifts) - 1) / 2) * 250
            d.rounded_rectangle([cx - 110, 140, cx + 110, 360], 30, fill=(44, 50, 64))
            sheet.alpha_composite(g, (int(cx - 100), 150))
            # check mark
            d.ellipse([cx + 66, 146, cx + 104, 184], fill=(60, 170, 250))
            d.line([(cx + 75, 165), (cx + 83, 174), (cx + 97, 156)], fill=(255, 255, 255), width=5)
        d.text((60, 420), 'Кому:', font=font('Semibold', 34), fill=(150, 158, 176))
        a = to_avatar.resize((110, 110), Image.LANCZOS)
        sheet.alpha_composite(a, (60, 476))
        d.text((196, 492), 'Петя', font=font('Semibold', 42), fill=(244, 246, 250))
        d.text((196, 546), 'основной аккаунт', font=font('Regular', 30), fill=(150, 158, 176))
        pr = _ease((t - (t1 - 0.4)) / 0.12) * (1 - _ease((t - (t1 - 0.22)) / 0.12))
        bx0, bx1 = 60 + 10 * pr, w - 60 - 10 * pr
        d.rounded_rectangle([bx0, 660 + 6 * pr, bx1, 780 - 6 * pr], 34, fill=(64, 160, 240))
        d.text((w / 2, 720), 'Передать', font=font('Heavy', 42), fill=(255, 255, 255), anchor='mm')
        im.alpha_composite(sheet, (0, y0))
    if t1 <= t < t1 + 1.0:
        k = _ease((t - t1) / 0.2) * (1 - _ease((t - t1 - 0.75) / 0.25))
        toast(im, 'Подарки переданы ✓', k)


def toast(im, text, k, y=300):
    if k <= 0.01:
        return
    w = SCREEN[0]
    f = font('Semibold', 34)
    tw = f.getlength(text) + 70
    t_ = Image.new('RGBA', (int(tw), 84), (0, 0, 0, 0))
    ImageDraw.Draw(t_).rounded_rectangle([0, 0, tw - 1, 83], 30, fill=(20, 22, 28, int(230 * k)))
    ImageDraw.Draw(t_).text((35, 22), text, font=f, fill=(255, 255, 255, int(255 * k)))
    im.alpha_composite(t_, (int((w - tw) / 2), int(y - 20 * (1 - k))))
