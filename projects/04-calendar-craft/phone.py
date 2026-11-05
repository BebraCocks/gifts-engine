"""Close-up phone with our own craft screen (not a copy of the Telegram UI): slots with live Lottie models,
chance counter, «Крафт» button, vortex, fire burn, ash and a result card.

screen(state) -> RGBA 1080 x 1920 phone image (transparent outside the phone body)."""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx
import gifts_api as G
import lottie
from chars import INK

W, H = 1080, 1920
PX0, PY0, PX1, PY1 = 70, 120, 1010, 1800          # phone body
SX0, SY0, SX1, SY1 = 104, 160, 976, 1760          # screen
BG = (22, 30, 48)
CARD = (34, 46, 72)
BLUE = (42, 171, 238)
GIFT = 'Desk Calendar'

# Telegram backdrop colours used on the slot cards (centre, edge) — picked for composition.
CARD_BACKS = {
    'Deadline': ('#e98b5a', '#9a3d18'), 'Burning Time': ('#f3a44c', '#a3501a'),
    'Heartbreak': ('#e77c9c', '#8f2d4e'), 'Blank Page': ('#8fb4d8', '#3e5f86'),
    'Monday': ('#9fd26f', '#4a7d2a'),
}
SLOT_POS = [(320, 640), (760, 640), (320, 1060), (760, 1060)]
SLOT = 380


def lottie_im(name, t, size):
    return lottie.frame(str(G.model_file(GIFT, name, 'json')), t, size=size)


def _hex(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@functools.lru_cache(None)
def card_bg(name, size):
    c, e = CARD_BACKS.get(name, ('#5a6a90', '#27304a'))
    c, e = np.array(_hex(c), np.float32), np.array(_hex(e), np.float32)
    yy, xx = np.mgrid[0:size, 0:size] / size - 0.5
    r = np.clip(np.sqrt(xx ** 2 + yy ** 2) * 1.6, 0, 1)[..., None]
    rgb = c * (1 - r) + e * r
    a = np.zeros((size, size), np.uint8)
    m = Image.new('L', (size * 2, size * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size * 2 - 1, size * 2 - 1], 64, fill=255)
    a = np.asarray(m.resize((size, size), Image.LANCZOS))
    return Image.fromarray(np.dstack([rgb.astype(np.uint8), a]), 'RGBA')


@functools.lru_cache(None)
def body():
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([PX0 - 8, PY0 - 8, PX1 + 8, PY1 + 8], 118, fill=INK)
    d.rounded_rectangle([PX0, PY0, PX1, PY1], 110, fill=(54, 58, 74))
    d.rounded_rectangle([SX0, SY0, SX1, SY1], 84, fill=BG)
    d.rounded_rectangle([470, 182, 610, 214], 16, fill=(10, 12, 18))          # camera notch
    return im


@functools.lru_cache(None)
def mask():
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([SX0, SY0, SX1, SY1], 84, fill=255)
    return m


@functools.lru_cache(None)
def _noise(n=256, seed=3):
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    fx_, fy_ = np.meshgrid(f, f)
    amp = 1 / np.maximum(np.sqrt(fx_ ** 2 + fy_ ** 2), 1 / n) ** 1.4
    z = np.real(np.fft.ifft2(amp * np.exp(2j * np.pi * rng.random((n, n)))))
    return ((z - z.min()) / (z.max() - z.min())).astype(np.float32)


def fire(w, h, t, strength):
    """Procedural flames (RGBA, w x h): scrolling tiled noise shaped by a rising envelope."""
    n = _noise()
    s = 2
    hw, hh = w // s, h // s
    ys, xs = np.mgrid[0:hh, 0:hw].astype(np.float32)
    u = (xs / hw * 1.6 + 0.07 * np.sin(ys / 13 + t * 3)) % 1
    v = (ys / hh * 1.3 + t * 1.25) % 1
    a = n[(v * 255).astype(int), (u * 255).astype(int)]
    b = n[((v * 2.1 + 0.3) % 1 * 255).astype(int), ((u * 2.3) % 1 * 255).astype(int)]
    q = 0.65 * a + 0.35 * b
    height = np.clip(strength, 0, 1.2)
    env = np.clip((ys / hh - (1 - height)) / max(height, 1e-3), 0, 1) ** 0.8
    edge = np.clip(1 - np.abs(xs / hw - 0.5) * 2, 0, 1) ** 0.35
    f = np.clip((q * 1.5 - 0.55 + env * 0.9) * env * edge * 1.6, 0, 1)
    rgb = np.stack([np.clip(f * 3.2, 0, 1) * 255, np.clip(f * 2.0 - 0.35, 0, 1) * 235,
                    np.clip(f * 2.4 - 1.5, 0, 1) * 200], -1)
    al = np.clip(f * 2.2, 0, 1) * 255
    im = Image.fromarray(np.dstack([rgb, al]).astype(np.uint8), 'RGBA')
    return im.resize((w, h), Image.BILINEAR)


def _text(d, xy, s, size, col, weight='Heavy', anchor='mm'):
    d.text(xy, s, font=fx.font(weight, size), fill=col, anchor=anchor)


def screen(st):
    """st keys: t, models (list of up to 4 names), filled (list 0..1 per slot), chance (float %),
    show_chance 0..1, press 0..1, vortex 0..1, burn 0..1, ash 0..1, fail 0..1, flash 0..1, title, owner."""
    t = st.get('t', 0.0)
    im = body().copy()
    scr = Image.new('RGBA', (W, H), BG + (255,))
    d = ImageDraw.Draw(scr)
    _text(d, (540, 270), 'Крафт подарка', 50, (240, 244, 255))
    _text(d, (170, 270), '‹', 70, BLUE, 'Bold')
    _text(d, (540, 340), st.get('subtitle', 'Добавьте до 4 подарков'), 32, (140, 156, 190), 'Medium')
    models = st.get('models', [])
    filled = st.get('filled', [0] * 4)
    vortex = st.get('vortex', 0.0)
    burn = st.get('burn', 0.0)
    ash = st.get('ash', 0.0)
    nslots = st.get('nslots', 4)
    # empty slot frames
    for k in range(nslots):
        cx, cy = SLOT_POS[k]
        d.rounded_rectangle([cx - SLOT / 2, cy - SLOT / 2, cx + SLOT / 2, cy + SLOT / 2], 40, fill=CARD,
                            outline=(64, 82, 120), width=4)
        if k >= len(models) or filled[k] < 0.5:
            _text(d, (cx, cy - 10), '+', 110, (90, 110, 150), 'Medium')
    # chance meter
    sc = st.get('show_chance', 0.0)
    if sc > 0:
        ch = st.get('chance', 0.0)
        col = (90, 220, 120) if ch >= 50 else (255, 196, 70)
        _text(d, (540, 1330), 'Шанс успеха', 40, (160, 176, 210), 'Semibold')
        _text(d, (540, 1430), f'{ch:.0f}%', int(130 + 20 * sc), col)
        d.rounded_rectangle([200, 1510, 880, 1536], 13, fill=(44, 56, 86))
        d.rounded_rectangle([200, 1510, 200 + 680 * ch / 100, 1536], 13, fill=col)
    # button
    pr = st.get('press', 0.0)
    bw = 1 - 0.06 * math.sin(min(pr, 1) * math.pi)
    bx0, bx1 = 540 - 340 * bw, 540 + 340 * bw
    by0, by1 = 1600 - 62 * bw, 1600 + 62 * bw
    d.rounded_rectangle([bx0, by0, bx1, by1], 62, fill=BLUE if pr < 0.5 or vortex == 0 else (30, 120, 180))
    _text(d, (540, 1600), 'Крафтить', 52, (255, 255, 255))
    # models in slots (or swirling to the centre)
    for k, name in enumerate(models[:nslots]):
        f = filled[k] if k < len(filled) else 0
        if f <= 0:
            continue
        cx, cy = SLOT_POS[k]
        if vortex > 0:
            a = fx.ease_in(vortex)
            ang = math.atan2(cy - 850, cx - 540) + a * 5.5
            rad = math.hypot(cx - 540, cy - 850) * (1 - a * 0.85)
            cx, cy = 540 + rad * math.cos(ang), 850 + rad * math.sin(ang)
        drop = (1 - fx.ease_out_back(min(1, f))) * -260
        size = int(SLOT * 0.92 * (1 - 0.45 * fx.ease_in(vortex)) * (0.6 + 0.4 * min(1, f)))
        if size < 8:
            continue
        bg = card_bg(name, size)
        g = lottie_im(name, t + k * 0.37, size)
        card = bg.copy()
        card.alpha_composite(g.resize((int(size * 0.86),) * 2, Image.LANCZOS), (int(size * 0.07),) * 2)
        if burn > 0:                                  # char the card
            c = np.asarray(card, np.float32)
            k_ = np.clip(burn * 1.6 - 0.1, 0, 1)
            c[..., :3] = c[..., :3] * (1 - 0.85 * k_) + np.array([30, 18, 14]) * 0.85 * k_
            c[..., 3] *= 1 - np.clip(ash * 1.4 - 0.1, 0, 1)
            card = Image.fromarray(c.astype(np.uint8), 'RGBA')
        if vortex > 0:
            card = card.rotate(vortex * 400 + k * 30, Image.BICUBIC, expand=True)
        scr.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2 + drop)))
        if burn == 0 and vortex == 0 and f >= 1:
            _text(d, (SLOT_POS[k][0], SLOT_POS[k][1] + SLOT / 2 - 26), name, 30, (255, 255, 255), 'Bold')
    if vortex > 0 and burn == 0:                     # glow building in the centre
        gsz = int(200 + 700 * vortex)
        glow = fx.radial(gsz, (140, 200, 255), power=2.2, peak=min(1, vortex * 1.4))
        scr.alpha_composite(glow, (540 - gsz // 2, 850 - gsz // 2))
    if burn > 0:
        fh = int(1100 * min(1, burn * 1.3))
        if fh > 20:
            fl = fire(872, 1420, t, burn * 1.1 * (1 - ash * 0.75))
            scr.alpha_composite(fl, (104, 1760 - 1420))
        for k in range(int(80 * ash)):                # ash flakes falling
            rng = np.random.default_rng(k)
            x = 160 + rng.random() * 760
            y = 500 + rng.random() * 300 + ash * 900 * (0.5 + rng.random())
            r = 4 + rng.random() * 7
            d2 = ImageDraw.Draw(scr)
            d2.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(70, 66, 64, 220))
    fail = st.get('fail', 0.0)
    if fail > 0:                                      # result card
        a = fx.ease_out_back(min(1, fail))
        cw, chh = int(760 * a), int(330 * a)
        if cw > 20:
            card = Image.new('RGBA', (760, 330), (0, 0, 0, 0))
            dd = ImageDraw.Draw(card)
            dd.rounded_rectangle([0, 0, 759, 329], 50, fill=(60, 22, 30), outline=(255, 90, 80), width=6)
            _text(dd, (380, 105), 'Крафт не удался', 56, (255, 120, 110))
            _text(dd, (380, 200), 'Подарки сгорели', 46, (255, 220, 210), 'Bold')
            _text(dd, (380, 270), st.get('fail_note', '4 из 4'), 34, (220, 170, 170), 'Medium')
            card = card.resize((cw, chh), Image.LANCZOS)
            scr.alpha_composite(card, (540 - cw // 2, 860 - chh // 2))
    fl = st.get('flash', 0.0)
    if fl > 0:
        scr.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * min(1, fl)))))
    im.paste(scr, (0, 0), mask())
    # glass glint
    gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(gl).polygon([(SX0, SY0 + 200), (SX0 + 380, SY0), (SX0 + 520, SY0), (SX0, SY0 + 420)],
                               fill=(255, 255, 255, 14))
    im.alpha_composite(gl)
    return im


def thumb(im, x, y, press, skin=(226, 214, 176)):
    """A cartoon thumb coming from the bottom edge to (x, y); press 0..1 squashes it."""
    d = ImageDraw.Draw(im)
    w = 120
    yy = y + 40 * press
    pts = [(x - w / 2, H + 40), (x - w / 2 - 10, yy + 60), (x - w / 2 + 6, yy), (x + w / 2 - 6, yy),
           (x + w / 2 + 10, yy + 60), (x + w / 2, H + 40)]
    d.line(pts + [pts[0]], fill=INK, width=14, joint='curve')
    d.polygon(pts, fill=skin)
    d.ellipse([x - w / 2 + 2, yy - 50, x + w / 2 - 2, yy + 70], fill=INK)
    d.ellipse([x - w / 2 + 9, yy - 43, x + w / 2 - 9, yy + 63], fill=skin)
    d.rounded_rectangle([x - 36, yy - 34, x + 36, yy + 10], 20, fill=(246, 236, 220))
    return im
