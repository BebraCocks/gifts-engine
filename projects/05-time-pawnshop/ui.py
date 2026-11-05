"""Telegram-like UI cards (own drawing, dark theme), labels and subtitles.

chat_card(...)   — a chat window: header (avatar, name, status) + message bubbles / a gift bubble.
profile_card(...) — Лёва's profile «Подарки»: 3×3 grid of live gifts with «от: …» captions.
gift_label(name, model) — pill with the gift name, shown when a gift appears.
Lottie gifts inside cards are live frames (full forward cycle, lottie.frame(t)).
"""
import functools
import math

from PIL import Image, ImageDraw, ImageFilter

import fx
import gifts_api as G
import lottie
from art import Layer

CARD = (24, 28, 38)
HEAD = (32, 37, 50)
BUBBLE = (44, 50, 66)
BLUE = (64, 160, 240)
TXT = (240, 242, 248)
DIM = (150, 158, 176)
GOLD = (255, 206, 96)


def gift(name, model, t, size, offset=0.0):
    """Live Lottie frame of a gift model (model=None -> the original gift)."""
    p = G.model_file(name, model, 'json') if model else G.original_file(name, 'json')
    return lottie.frame(str(p), t + offset, size=size)


def _round_mask(w, h, r):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m


def _wrap(text, f, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        tryl = (cur + ' ' + w).strip()
        if f.getlength(tryl) <= width:
            cur = tryl
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


@functools.lru_cache(None)
def avatar_grandma(size):
    L = Layer(size, size)
    r = size / 2
    L.ell(r, r, r, r, (236, 150, 140))
    L.ell(r, r * 1.06, r * 0.42, r * 0.46, (248, 220, 200))
    L.ell(r, r * 0.66, r * 0.46, r * 0.3, (240, 240, 240))
    L.ell(r, r * 0.42, r * 0.2, r * 0.17, (240, 240, 240))
    L.shape([(r * 0.3, r * 2), (r * 0.5, r * 1.5), (r * 1.5, r * 1.5), (r * 1.7, r * 2)], (150, 110, 160))
    for s in (-1, 1):
        L.ell(r + s * r * 0.16, r * 1.0, r * 0.05, r * 0.06, (60, 50, 60))
    L.stroke([(r - r * 0.14, r * 1.22), (r, r * 1.28), (r + r * 0.14, r * 1.22)], r * 0.05, (190, 100, 100))
    im = L.image()
    im.putalpha(Image.composite(im.getchannel('A'), Image.new('L', im.size, 0), _circle(size)))
    return im


@functools.lru_cache(None)
def _circle(size):
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    return m


def avatar_gift(name, model, t, size, bg=(40, 44, 60)):
    im = Image.new('RGBA', (size, size), bg + (255,))
    g = gift(name, model, t, int(size * 0.9))
    im.alpha_composite(g, ((size - g.width) // 2, (size - g.height) // 2 + 2))
    im.putalpha(_circle(size))
    return im


def heart(size, col=(240, 80, 100)):
    L = Layer(size, size)
    s = size
    L.shape([(s * 0.5, s * 0.92), (s * 0.08, s * 0.48), (s * 0.12, s * 0.16), (s * 0.34, s * 0.08),
             (s * 0.5, s * 0.26), (s * 0.66, s * 0.08), (s * 0.88, s * 0.16), (s * 0.92, s * 0.48)], col)
    return L.image()


def chat_card(t, who, msgs, w=880, typed=1.0, glitch=0.0):
    """who: 'grandma' | 'bot'. msgs: list of ('text', str, appear 0..1) or ('gift', (name, model), appear, caption).
    Returns RGBA card."""
    f_name, f_stat, f_msg = fx.font('Bold', 40), fx.font('Regular', 28), fx.font('Medium', 38)
    pad, head_h = 34, 140
    # layout
    blocks = []
    for m in msgs:
        if m[0] == 'text':
            lines = _wrap(m[1], f_msg, w - 2 * pad - 70)
            blocks.append(('text', lines, m[2], 30 + 50 * len(lines) + 26))
        else:
            blocks.append(('gift', m[1], m[2], 420, m[3] if len(m) > 3 else ''))
    h = head_h + 30 + sum(b[3] + 18 for b in blocks) + 20
    card = Image.new('RGBA', (w, h), CARD + (255,))
    d = ImageDraw.Draw(card)
    d.rectangle([0, 0, w, head_h], fill=HEAD + (255,))
    av = avatar_grandma(96) if who == 'grandma' else avatar_gift('Swiss Watch', 'Timeless', t, 96)
    card.alpha_composite(av, (pad, (head_h - 96) // 2))
    name = 'Бабушка' if who == 'grandma' else 'Ломбард времени'
    stat = 'была недавно' if who == 'grandma' else 'бот'
    d.text((pad + 120, head_h / 2 - 20), name, font=f_name, fill=TXT + (255,), anchor='lm')
    d.text((pad + 120, head_h / 2 + 26), stat, font=f_stat, fill=DIM + (255,), anchor='lm')
    if who == 'bot':
        d.rounded_rectangle([w - pad - 118, head_h / 2 - 22, w - pad, head_h / 2 + 22], 22, fill=(70, 60, 40, 255))
        d.text((w - pad - 59, head_h / 2), 'BOT', font=fx.font('Heavy', 26), fill=GOLD + (255,), anchor='mm')
    y = head_h + 30
    for b in blocks:
        a = b[2]
        if a <= 0:
            continue
        bh = b[3]
        layer = Image.new('RGBA', (w, bh + 18), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        if b[0] == 'text':
            lines = b[1]
            n_chars = sum(len(s) for s in lines)
            shown = int(round(n_chars * typed)) if who == 'bot' else n_chars
            bw = int(max(f_msg.getlength(s) for s in lines)) + 2 * 30
            ld.rounded_rectangle([pad, 0, pad + bw, bh], 30, fill=BUBBLE + (255,))
            yy = 30
            for s in lines:
                part = s[:max(0, shown)]
                shown -= len(s)
                ld.text((pad + 30, yy), part, font=f_msg, fill=TXT + (255,))
                yy += 50
        else:
            name, model = b[1]
            gw = 420
            gb = Image.new('RGBA', (gw, bh), (0, 0, 0, 0))
            gd = ImageDraw.Draw(gb)
            gd.rounded_rectangle([0, 0, gw - 1, bh - 1], 34, fill=(118, 64, 92, 255) if who == 'grandma' else
                                 (80, 62, 40, 255))
            glow = Image.new('RGBA', (gw, bh), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse([60, 20, gw - 60, 300], fill=(255, 170, 190, 120))
            gb.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40)))
            g = gift(name, model, t, 270)
            gb.alpha_composite(g, ((gw - g.width) // 2, 20))
            gd.text((gw / 2, 318), 'Подарок', font=fx.font('Bold', 34), fill=TXT + (255,), anchor='mm')
            gd.text((gw / 2, 362), b[4], font=fx.font('Regular', 26), fill=(240, 210, 220, 255), anchor='mm')
            gb.putalpha(Image.composite(gb.getchannel('A'), Image.new('L', gb.size, 0), _round_mask(gw, bh, 34)))
            layer.alpha_composite(gb, (pad, 0))
        if a < 1:
            s = 0.85 + 0.15 * fx.ease_out_back(a)
            layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.BILINEAR)
            layer.putalpha(layer.getchannel('A').point(lambda v: int(v * min(1, a * 1.6))))
        card.alpha_composite(layer, (int(pad * (1 - (layer.width / w))) if a < 1 else 0, y))
        y += bh + 18
    if glitch > 0:
        card = _glitch(card, glitch, t)
    card.putalpha(Image.composite(card.getchannel('A'), Image.new('L', card.size, 0), _round_mask(w, h, 44)))
    return card


def _glitch(im, k, t):
    import numpy as np
    a = np.asarray(im).copy()
    rng = np.random.default_rng(int(t * 60))
    h = a.shape[0]
    for _ in range(int(3 + 6 * k)):
        y0 = rng.integers(0, h - 20)
        y1 = y0 + rng.integers(6, 40)
        a[y0:y1] = np.roll(a[y0:y1], int(rng.integers(-40, 40) * k), axis=1)
    a[..., 0] = np.roll(a[..., 0], int(6 * k), axis=1)
    return Image.fromarray(a, 'RGBA')


PROFILE_GIFTS = [
    (('Ginger Cookie', 'Coffee Break'), 'Ломбард времени'), (('Snow Globe', 'Winter'), 'Ломбард времени'),
    (('Record Player', 'Sunset Beach'), 'Ломбард времени'), (("Durov's Cap", 'Seabreeze'), 'Ломбард времени'),
    (('Plush Pepe', 'Midas Pepe'), 'Ломбард времени'), (('Swiss Watch', 'Memory Flash'), 'Ломбард времени'),
    (('Desk Calendar', 'Sunday'), 'Ломбард времени'), (('Homemade Cake', None), 'Бабушка'),
    (('Restless Jar', 'Fireflies'), 'Ломбард времени'),
]


def profile_card(t, focus=0.0, w=900):
    """Лёва's gift profile. focus 0..1: everything dims except grandma's Homemade Cake."""
    cell, gap, pad = 262, 22, 30
    h = 250 + 3 * cell + 2 * gap + 2 * pad + 40
    card = Image.new('RGBA', (w, h), CARD + (255,))
    d = ImageDraw.Draw(card)
    av = Layer(130, 130)
    av.ell(65, 65, 65, 65, (52, 108, 116))
    av.ell(65, 74, 30, 34, (247, 214, 192))
    av.shape([(30, 60), (40, 26), (90, 22), (102, 58), (80, 44), (50, 46)], (66, 46, 40))
    card.alpha_composite(av.image(), (pad, 40))
    d.text((pad + 160, 82), 'Лёва', font=fx.font('Heavy', 48), fill=TXT + (255,), anchor='lm')
    d.text((pad + 160, 134), 'был давно', font=fx.font('Regular', 30), fill=DIM + (255,), anchor='lm')
    d.text((pad, 226), 'ПОДАРКИ  ·  9', font=fx.font('Bold', 32), fill=BLUE + (255,), anchor='lm')
    for k, ((name, model), frm) in enumerate(PROFILE_GIFTS):
        cx = pad + (k % 3) * (cell + gap)
        cy = 260 + (k // 3) * (cell + gap)
        is_g = frm == 'Бабушка'
        dim = focus * (0.0 if is_g else 0.72)
        tile = Image.new('RGBA', (cell, cell), (36, 42, 58, 255))
        if is_g and focus > 0:
            gl = Image.new('RGBA', (cell, cell), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse([20, 10, cell - 20, cell - 50], fill=(255, 150, 170, int(140 * focus)))
            tile.alpha_composite(gl.filter(ImageFilter.GaussianBlur(26)))
        g = gift(name, model, t, 186, offset=k * 0.37)
        tile.alpha_composite(g, ((cell - 186) // 2, 10))
        td = ImageDraw.Draw(tile)
        td.text((cell / 2, cell - 40), 'от: ' + frm, font=fx.font('Medium', 24),
                fill=((255, 190, 200) if is_g else DIM) + (255,), anchor='mm')
        if dim:
            ov = Image.new('RGBA', (cell, cell), (14, 16, 22, int(255 * dim)))
            tile.alpha_composite(ov)
        tile.putalpha(Image.composite(tile.getchannel('A'), Image.new('L', tile.size, 0), _round_mask(cell, cell, 28)))
        card.alpha_composite(tile, (cx, cy))
        if is_g and focus > 0:
            r = Image.new('RGBA', (cell + 12, cell + 12), (0, 0, 0, 0))
            ImageDraw.Draw(r).rounded_rectangle([2, 2, cell + 9, cell + 9], 32, outline=(255, 170, 190, int(255 * focus)),
                                                width=5)
            card.alpha_composite(r, (cx - 6, cy - 6))
    card.putalpha(Image.composite(card.getchannel('A'), Image.new('L', card.size, 0), _round_mask(w, h, 48)))
    return card


@functools.lru_cache(maxsize=64)
def gift_label(name, model=None, accent=GOLD):
    f1, f2 = fx.font('Heavy', 40), fx.font('Medium', 28)
    w1 = f1.getlength(name)
    w2 = f2.getlength(model) if model else 0
    w = int(max(w1, w2)) + 64
    h = 108 if model else 76
    im = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([15, 19, w + 15, h + 19], 26, fill=(0, 0, 0, 120))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([15, 15, w + 15, h + 15], 26, fill=(28, 22, 20, 236), outline=accent + (255,), width=3)
    d.text((15 + w / 2, 15 + (40 if model else h / 2)), name, font=f1, fill=accent + (255,), anchor='mm')
    if model:
        d.text((15 + w / 2, 15 + 80), model, font=f2, fill=(236, 226, 210, 255), anchor='mm')
    return im


@functools.lru_cache(maxsize=64)
def page_sprite(text, sub=None, w=300, h=200):
    """A torn-off calendar page with what was sold written on it."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 16, fill=(250, 246, 236, 255))
    d.rectangle([0, 0, w, 46], fill=(222, 92, 84, 255))
    for x in range(20, w, 40):
        d.ellipse([x - 6, 14, x + 6, 26], fill=(250, 246, 236, 255))
    f = fx.font('Heavy', 46 if len(text) < 9 else 34)
    d.text((w / 2, 112 if sub else 122), text, font=f, fill=(60, 52, 64, 255), anchor='mm')
    if sub:
        d.text((w / 2, 162), sub, font=fx.font('Medium', 26), fill=(150, 120, 110, 255), anchor='mm')
    return im


@functools.lru_cache(maxsize=16)
def price_tag(lines):
    """Paper price tag on a string. lines: tuple of strings."""
    f1, f2 = fx.font('Medium', 34), fx.font('Heavy', 50)
    w = int(max(f1.getlength(lines[0]), *(f2.getlength(s) for s in lines[1:]))) + 120
    h = 70 + 64 * (len(lines) - 1) + 30
    L = Layer(w + 40, h + 120)
    L.poly([(40, 120), (w - 10, 120), (w + 30, 120 + h / 2), (w - 10, 120 + h), (40, 120 + h)], (246, 234, 204))
    L.ell(w - 10, 120 + h / 2, 9, 9, (110, 70, 50))
    L.stroke([(w - 10, 120 + h / 2), (w + 30, 10)], 3, (210, 180, 120))
    im = L.image()
    d = ImageDraw.Draw(im)
    d.text((70, 150), lines[0], font=f1, fill=(130, 90, 70, 255), anchor='lt')
    for k, s in enumerate(lines[1:]):
        d.text((70, 196 + k * 64), s, font=f2, fill=(150, 40, 46, 255), anchor='lt')
    return im
