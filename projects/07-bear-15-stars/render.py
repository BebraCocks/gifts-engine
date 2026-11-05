"""07-bear-15-stars «Как получить мишку за 15 звёзд» — picture. A frame is a pure function of content time t.

Shots (events.py): hook (bear drops, «15 ⭐», three closed cards) → card «1 МЕСТО» → chats list «дайте мишку»
→ room, days fly, «10 ч/день» → the bear arrives → BAN stamps in every chat → card «2 МЕСТО» (chart up)
→ street: old clothes + sign «НА ЛЕКАРСТВА» → passers-by, a coin → RubUp → friends spot him → they crumble
to dust, tumbleweed → card «3 МЕСТО» (crown, 100%) → sofa → DM «Павел Дуров»: «дай мишку» → one grey tick,
months pass, beard and cobweb → like button + waving bear.
"""
import functools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import banner
import config
import frames
import fx
import gifts_api
import lottie
import chars as C
import sets as S_
import tg
from timeline import DUR, ON, END, KEY
from words import WORDS
from events import AD_STOP, S, E

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
GOLD = (255, 200, 70)


# ------------------------------------------------------------------ helpers
def ramp(t, a, b):
    return fx.clamp01((t - a) / (b - a)) if b > a else float(t >= a)


def sm(x):
    return fx.smooth(x)


def pop(t, t0, d=0.4):
    return fx.ease_out_back(ramp(t, t0, t0 + d)) if t >= t0 else 0.0


def lerp(a, b, k):
    return a + (b - a) * k


def blink(t, seed=0.0, every=3.1):
    p = (t + seed * 1.7) % every
    return max(0.0, 1 - abs(p - 0.08) / 0.08) if p < 0.16 else 0.0


def paste_clip(canvas, im, x, y):
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.width, x + im.width), min(canvas.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    piece = im.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    canvas.alpha_composite(piece, (x0, y0))


def put(canvas, im, x, y, a=1.0, scale=1.0, rot=0.0, sx=None):
    """Centre im at (x, y). sx: separate horizontal scale (card flips)."""
    if a <= 0.01 or scale <= 0.01:
        return
    kx = scale * (sx if sx is not None else 1.0)
    if abs(kx) < 0.01:
        return
    if kx != 1.0 or scale != 1.0:
        im = im.resize((max(1, int(im.width * abs(kx))), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 1.0:
        im = im.copy()
        im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    paste_clip(canvas, im, x - im.width / 2, y - im.height / 2)


@functools.lru_cache(maxsize=64)
def _glow_spr(r, rgb):
    n = 2 * r
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = rgb
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im, 'RGBA')


def glow(canvas, x, y, r, rgb, a):
    if a > 0.01:
        put(canvas, _glow_spr(int(r), tuple(rgb)), x, y, a)


@functools.lru_cache(maxsize=128)
def text_spr(text, size, rgb=(255, 255, 255), weight='Heavy', stroke=9, srgb=(28, 16, 50), shadow=True):
    f = fx.font(weight, size)
    lines = text.split('\n')
    lh = int(size * 1.1)
    w = int(max(f.getlength(s) for s in lines)) + 2 * stroke + 40
    h = lh * len(lines) + 2 * stroke + 40
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, s in enumerate(lines):
        d.text((w / 2, 20 + stroke + lh * k + lh / 2), s, font=f, fill=tuple(rgb) + (255,), anchor='mm',
               stroke_width=stroke, stroke_fill=tuple(srgb) + (255,))
    if not shadow:
        return im
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 8))
    out.alpha_composite(im)
    return out


@functools.lru_cache(maxsize=32)
def pill(text, size=54, bg=(255, 255, 255), fg=(30, 20, 60), pad=34):
    f = tg.font('Heavy', size)
    tw = tg.text_width(text, f)
    w, h = int(tw + 2 * pad), int(size * 1.6)
    im = Image.new('RGBA', (w + 20, h + 24), (0, 0, 0, 0))
    sh = Image.new('L', im.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([10, 18, 10 + w, 18 + h], h // 2, fill=120)
    im.putalpha(sh.filter(ImageFilter.GaussianBlur(7)))
    im = Image.composite(Image.new('RGBA', im.size, (0, 0, 0, 255)), Image.new('RGBA', im.size, (0, 0, 0, 0)),
                         im.getchannel('A'))
    body = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(body).rounded_rectangle([10, 8, 10 + w, 8 + h], h // 2, fill=tuple(bg) + (255,))
    im.alpha_composite(body)
    tg.draw_text(im, (10 + pad, 8 + (h - size * 1.2) / 2), text, f, tuple(fg))
    return im


@functools.lru_cache(None)
def price_tag():
    """«⭐ 15» like on the gift sheet: dark pill, gold number, sparkles."""
    im = pill('⭐ 15', 70, bg=(52, 42, 34), fg=(255, 196, 80), pad=40)
    d = ImageDraw.Draw(im)
    rnd = np.random.default_rng(15)
    for _ in range(14):
        x, y, r = rnd.uniform(20, im.width - 20), rnd.uniform(14, im.height - 20), rnd.uniform(3, 7)
        fx.sparkle(d, x, y, r, (255, 214, 120, 200))
    return im


def emoji(ch, size):
    return tg._emoji(ch, size)


def hero_at(canvas, x, y, scale, t, kind='hoodie', arms='down', glow_=0.0, tilt=0.0, bob=0.0, **face):
    face.setdefault('blink', blink(t))
    hd = C.head('hero', **face)
    bd = C.body('hero', kind=kind, arms=arms, glow=round(glow_ * 4) / 4)
    C.place(canvas, C.bust(hd, bd, x, y, scale, tilt=tilt, bob=bob))


BEAR_ID = '5170233102089322756'        # the plain 15 ⭐ bear: Telegram gift id, Lottie from api.changes.tg
BEAR = str(gifts_api.original_file(BEAR_ID, 'json'))
BEAR_BOTTOM = 0.91                      # feet line inside the Lottie box (alpha bottom 464/512)


def bear_at(canvas, x, y, size, t, wave=0.0, squash=0.0, rot=0.0, a=1.0, t0=0.0):
    """The real bear animation (full 3 s loop), feet at (x, y). size = Lottie box width in px."""
    n = int(round(size / 8) * 8)
    sp = lottie.frame(BEAR, max(0.0, t - t0), size=min(n, 1024))
    if n > 1024:
        sp = sp.resize((n, n), Image.BICUBIC)
    if squash:
        sp = sp.resize((max(1, int(n * (1 + 0.18 * squash))), max(1, int(n * (1 - 0.22 * squash)))), Image.BICUBIC)
    if rot:
        sp = sp.rotate(rot, resample=Image.BICUBIC, expand=True, center=(sp.width / 2, sp.height * BEAR_BOTTOM))
    if a < 1:
        sp = sp.copy()
        sp.putalpha(sp.getchannel('A').point(lambda v: int(v * a)))
    paste_clip(canvas, sp, x - sp.width / 2, y - sp.height * BEAR_BOTTOM)


def shadow_ell(canvas, x, y, rx, a=0.3):
    lay = Image.new('RGBA', (int(rx * 2 + 60), 120), (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse([30, 40, 30 + rx * 2, 80], fill=(0, 0, 0, int(255 * a)))
    put(canvas, lay.filter(ImageFilter.GaussianBlur(10)), x, y)


def stage_bg(t, ray=1.0):
    im = S_.show().copy()
    if ray > 0:
        r = S_.rays(t)
        add = Image.new('RGBA', (W, H), (255, 236, 190, 255))
        im = Image.composite(add, im, r.point(lambda v: int(v * ray)))
    return im


def confetti(canvas, t, t0, cx, cy, n=60, seed=1, spread=520):
    if t < t0 or t > t0 + 2.4:
        return
    u = t - t0
    rnd = np.random.default_rng(seed)
    cols = [(255, 90, 110), (255, 200, 70), (90, 200, 255), (120, 230, 140), (200, 140, 255)]
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(n):
        a = rnd.uniform(-math.pi, 0)
        v = rnd.uniform(0.5, 1.0) * spread * 2.2
        x = cx + math.cos(a) * v * u * 0.9
        y = cy + math.sin(a) * v * u + 900 * u * u
        s = rnd.uniform(10, 20)
        r = u * rnd.uniform(4, 10)
        c = cols[k % len(cols)]
        al = int(255 * (1 - ramp(u, 1.6, 2.4)))
        pts = [(x + s * math.cos(r + j * math.pi / 2) * (1 if j % 2 else 0.45),
                y + s * math.sin(r + j * math.pi / 2) * (1 if j % 2 else 0.45)) for j in range(4)]
        d.polygon(pts, fill=c + (al,))
    canvas.alpha_composite(lay)


# ------------------------------------------------------------------ 1. hook
def shot_hook(t):
    im = stage_bg(t)
    tl = E['bear_land']
    # bear: falls from above, squash on landing, then settles; shrinks up when the cards arrive
    up = sm(ramp(t, E['cards'] - 0.1, E['cards'] + 0.45))
    if t < tl:
        k = t / tl
        y = lerp(-80, 1180, k * k)
        squash = -0.25 * k
    else:
        u = t - tl
        y = 1180 - 90 * abs(math.sin(min(u, 0.55) / 0.55 * math.pi)) * (1 - min(u, 0.55) / 0.55) * (u < 0.55)
        squash = 0.9 * fx.bump(ramp(u, 0, 0.5), f=3.0, decay=5) if u < 0.6 else 0.0
    y = lerp(y, 860, up)
    size = lerp(760, 470, up)
    sway = 2.5 * math.sin(t * 2.2)
    shadow_ell(im, 540, y - 10, size * 0.36, 0.3)
    glow(im, 540, y - size * 0.5, int(size * 0.75), (255, 220, 150), 0.35)
    bear_at(im, 540, y, size * 1.05, t, squash=squash, rot=sway, t0=tl)
    # price tag
    if t >= E['price']:
        k = pop(t, E['price'], 0.45)
        sw = 8 * math.sin((t - E['price']) * 5) * math.exp(-(t - E['price']) * 1.5)
        px, py = 540 + size * 0.42, y - size * 0.86
        put(im, price_tag(), px, py, a=min(1, k * 2), scale=k, rot=sw - 10)
    # title
    tk = pop(t, 0.05, 0.45)
    put(im, text_spr('КАК ПОЛУЧИТЬ\nМИШКУ?', 104, GOLD), 540, lerp(300, 250, up), a=min(1, tk * 2),
        scale=0.6 + 0.4 * tk)
    # three closed cards
    for j, x in enumerate((200, 540, 880)):
        t0 = E['cards'] + 0.12 * j
        if t < t0:
            continue
        k = pop(t, t0, 0.5)
        best = j == 2
        wob = 0.0
        sc = 0.4 * k
        if best and t >= E['best']:
            u = t - E['best']
            sc *= 1 + 0.14 * sm(ramp(u, 0, 0.3)) + 0.03 * math.sin(u * 8)
            wob = 6 * math.sin(u * 9) * math.exp(-u * 1.2)
            glow(im, x, 1250, 260, (255, 220, 120), 0.6 * sm(ramp(u, 0, 0.3)))
        put(im, S_.card(3 if best else (1 if j == 0 else 2), back=True), x, lerp(2100, 1240, k), scale=sc, rot=wob)
        put(im, text_spr(f'№{j + 1}', 50, (255, 255, 255), stroke=7), x, lerp(2100, 1240, k) + 210, a=k)
    if t >= E['best']:
        k = pop(t, E['best'] + 0.1, 0.4)
        put(im, text_spr('САМАЯ\nЛУЧШАЯ', 44, GOLD, stroke=6), 880, 1000, a=min(1, 2 * k), scale=k, rot=8)
    return im


# ------------------------------------------------------------------ place cards
TITLES = {1: 'ПРОСЬБА О\nБЛАГОСКЛОННОСТИ', 2: 'БОЛЕЕ\nЭФФЕКТИВНЫЙ', 3: 'РАБОТАЕТ\nНА 100%'}


def shot_place(t, rank, t0, flip):
    im = stage_bg(t, 1.0 if rank < 3 else 1.5)
    k = sm(ramp(t, t0, t0 + 0.4))
    # the card flies from the №-position of the hook to the centre, then flips on «место»
    x0 = (200, 540, 880)[rank - 1]
    x = lerp(x0, 540, k)
    y = lerp(1240, 760, k) + 10 * math.sin(t * 2.0)
    sc = lerp(0.4, 1.0, fx.ease_out_back(k, 1.2))
    f = ramp(t, flip - 0.18, flip + 0.18)
    sx = math.cos(math.pi * f)
    back = f < 0.5
    if rank == 3 and not back:
        glow(im, x, y, 520, (255, 210, 110), 0.65 + 0.1 * math.sin(t * 6))
    put(im, S_.card(rank, back=back), x, y, scale=sc, sx=abs(sx))
    if not back:
        u = t - flip
        for j in range(8):                      # a ring of sparkles on the flip
            a = j * math.pi / 4 + u
            r = 300 + 260 * sm(ramp(u, 0, 0.6))
            al = 1 - ramp(u, 0.3, 0.8)
            if al > 0:
                put(im, emoji('✨', 70), x + r * math.cos(a), y + r * math.sin(a) * 1.2, a=al)
    # title stamp
    ts = E[{1: 'stamp1', 2: 'effect', 3: 'meter'}[rank]] - (0.3 if rank > 1 else 0.05)
    if t >= ts:
        kk = ramp(t, ts, ts + 0.16)
        s = 1.6 - 0.6 * fx.ease_out(kk)
        col = {1: (255, 150, 90), 2: (220, 228, 245), 3: GOLD}[rank]
        put(im, text_spr(TITLES[rank], 82 if rank == 1 else 104, col), 540, 1390,
            a=min(1, kk * 2), scale=s, rot=-3 if rank == 1 else 0)
    if rank == 2 and t >= E['effect'] - 0.2:
        chart(im, t, E['effect'] - 0.2)
    if rank == 3:
        meter(im, t)
    return im


def chart(im, t, t0):
    """A tiny chart in the corner: the line shoots up."""
    k = sm(ramp(t, t0, t0 + 0.7))
    lay = Image.new('RGBA', (360, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, 359, 299], 30, fill=(255, 255, 255, 230))
    pts = [(40, 250), (110, 225), (170, 235), (230, 170), (300, 60)]
    n = max(2, int(1 + k * (len(pts) - 1) + 0.999))
    seg = pts[:n]
    d.line(seg, fill=(60, 190, 110), width=14, joint='curve')
    if k > 0.95:
        d.polygon([(300, 30), (330, 80), (276, 76)], fill=(60, 190, 110))
    put(im, lay, 870, 330, a=min(1, k * 3), rot=6, scale=0.5 + 0.5 * fx.ease_out_back(min(1, k * 2)))


def meter(im, t):
    a0, a1 = E['meter'] - 0.1, E['full']
    if t < a0:
        return
    k = sm(ramp(t, a0, a1))
    x0, y0, w, h = 140, 1580, 800, 70
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x0 - 8, y0 - 8, x0 + w + 8, y0 + h + 8], (h + 16) // 2, fill=(20, 12, 50, 230))
    if k > 0.02:
        d.rounded_rectangle([x0, y0, x0 + w * k, y0 + h], h // 2, fill=GOLD + (255,))
    im.alpha_composite(lay)
    pct = int(round(100 * k))
    put(im, text_spr(f'{pct}%', 64, (255, 255, 255), stroke=7), x0 + max(70, w * k) - 10, y0 - 70)
    if t >= a1:
        glow(im, x0 + w, y0 + h / 2, 160, (255, 230, 150), 0.8 * (1 - ramp(t, a1, a1 + 0.6)))


# ------------------------------------------------------------------ 2. chats list (p1)
CHATS = [
    ('Богачи NFT 💎', 'Вы: дайте мишку пж 🥺', (90, 130, 230), '💎'),
    ('Клуб миллионеров', 'Вы: ну одного мишку…', (230, 150, 60), 'К'),
    ('Plush Pepe Holders', 'Вы: мишку бы 🧸', (90, 190, 110), '🐸'),
    ('Звёздный фонд ⭐', 'Вы: 15 звёзд жалко?', (240, 190, 60), '⭐'),
    ('Миллиардеры 24/7', 'Вы: дядь, мишку 🥺', (200, 90, 160), 'М'),
    ('Олигархи чат', 'Вы: мне бы мишку…', (90, 170, 200), 'О'),
    ('Подарки даром 🎁', 'Вы: ПОЖАЛУЙСТА 🙏', (230, 90, 90), '🎁'),
    ('Elite Gifts', 'Вы: ну мишку 🧸🧸', (120, 110, 220), 'E'),
    ('Rich Kids', 'Вы: я хороший 🥺', (60, 160, 150), 'R'),
    ('Сливки общества', 'Вы: мишку плиз', (210, 130, 100), 'С'),
]


def chat_rows(t0, step, ban_t=None):
    rows = []
    for j, (name, last, col, letter) in enumerate(CHATS):
        rows.append(dict(name=name, last=last, clock=f'{9 + j // 3}:{(17 * j) % 60:02d}', col=col, letter=letter,
                         t=t0 + step * j, unread=0, ban=None if ban_t is None else ban_t + 0.17 * j,
                         dim=0 if ban_t is None else 1))
    return rows


def phone_view(screen, cx, cy, scale, rot=0.0, a=1.0):
    dev = tg.phone(screen)
    return dev, cx, cy, scale, rot, a


def show_phone(im, screen, cx=540, cy=980, scale=0.86, rot=0.0, a=1.0):
    dev = tg.phone(screen)
    shadow = Image.new('RGBA', (dev.width + 120, dev.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([60, 80, 60 + dev.width, 80 + dev.height], 120, fill=(0, 0, 0, 110))
    put(im, shadow.filter(ImageFilter.GaussianBlur(30)), cx, cy + 20, scale=scale, rot=rot, a=a)
    put(im, dev, cx, cy, scale=scale, rot=rot, a=a)


def shot_chats(t):
    im = stage_bg(t, 0.6)
    k = sm(ramp(t, S['chats'], S['chats'] + 0.35))
    rows = chat_rows(S['chats'] + 0.25, 0.3)
    scr = tg.chat_list(t, rows, clock='09:41')
    show_phone(im, scr, 540, lerp(2400, 1000, k), 0.92, rot=lerp(-12, -2, k) + 1.0 * math.sin(t))
    if t >= E['rich']:
        kk = pop(t, E['rich'], 0.35)
        put(im, pill('💰 только богатые', 50, bg=GOLD, fg=(60, 30, 10)), 540, 70, a=min(1, 2 * kk), scale=kk)
    return im


# ------------------------------------------------------------------ 3. the grind
def shot_grind(t):
    t0 = S['grind']
    u = t - t0
    days_end = E['luck'] - 0.1
    k_days = ramp(t, t0 + 0.3, days_end)
    speed = 0.25 + 2.6 * k_days                          # cycles per second accelerate
    phase = (0.25 * u + 1.3 * k_days ** 2 * 3) % 1.0
    if t >= days_end:
        phase = 0.0
    im = S_.room(round(phase * 24) / 24 % 1.0).copy()
    tired = min(1.0, k_days * 1.4)
    happy = sm(ramp(t, E['luck'], E['luck'] + 0.25))
    hero_at(im, 540, 1200, 1.05, t, arms='phone', glow_=1, tilt=2 * math.sin(t * 1.7), bob=3 * math.sin(t * 2.3),
            tired=tired * (1 - happy), sad=0.3 * tired * (1 - happy), smile=lerp(0.1, 1.0, happy),
            open_=0.7 * happy, brow=1.2 * happy, look=(0, 0.4 * (1 - happy)), sweat=tired * (1 - happy))
    # counters
    day = 1 + int(213 * k_days ** 2.2)
    put(im, pill(f'📅 День {day}', 56), 290, 150, a=sm(ramp(t, t0, t0 + 0.3)))
    if t >= E['hours'] - 0.1:
        kk = pop(t, E['hours'] - 0.1, 0.4)
        put(im, pill('⏰ 10 ч / день', 56, bg=(255, 110, 100), fg=(255, 255, 255)), 770, 150, a=min(1, kk * 2),
            scale=kk)
    if t >= E['luck'] - 0.25:              # the notification drops in
        kk = sm(ramp(t, E['luck'] - 0.25, E['luck'] + 0.1))
        put(im, notif(), 540, lerp(-120, 330, kk))
        glow(im, 540, 330, 380, (255, 240, 180), 0.4 * kk)
    return im


@functools.lru_cache(None)
def notif():
    w, h = 940, 170
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w - 1, h - 1], 44, fill=(250, 250, 252, 240))
    im.alpha_composite(tg.avatar_letter('🎁', (90, 170, 240), 100), (32, 35))
    tg.draw_text(im, (160, 30), 'Telegram', tg.font('Semibold', 34), (20, 20, 24))
    tg.draw_text(im, (160, 82), 'Вам отправили подарок 🧸', tg.font('Regular', 36), (40, 40, 46))
    return im


# ------------------------------------------------------------------ 4. the bear arrives -> ban
def shot_gift(t):
    if t >= S['banlist']:
        return shot_banlist(t)
    im = stage_bg(t, 0.8)
    chat = dict(theme='day', name='Богатый дядя 💎', status='в сети', avatar=tg.avatar_letter('💎', (90, 130, 230), 84),
                clock='21:14', events=[tg.msg(S['gift'] - 5, 'out', 'дайте мишку пж 🥺', '21:13', read=0.2),
                                       tg.msg(S['gift'] - 4.6, 'in', 'ладно, держи', '21:14'),
                                       tg.bear(E['gift_in'] - 0.15, 'in', 'Богатый дядя отправил подарок')])
    scr = tg.chat_screen(t, chat)
    k = sm(ramp(t, S['gift'], S['gift'] + 0.3))
    show_phone(im, scr, 540, 960, lerp(0.8, 0.9, k), rot=-1.5 + math.sin(t))
    confetti(im, t, E['gift_in'], 540, 1000, n=70, seed=4)
    return im


def shot_banlist(t):
    im = stage_bg(t, 0.3)
    rows = chat_rows(-10, 0, ban_t=E['ban'] - 0.05)
    for r in rows:
        r['dim'] = ramp(t, r['ban'], r['ban'] + 0.2) if r['ban'] is not None else 0
        r['last'] = 'Вы заблокированы' if t >= r['ban'] else r['last']
    scr = tg.chat_list(t, rows, clock='21:15')
    shake = 0.0
    for r in rows:
        if r['ban'] <= t < r['ban'] + 0.2:
            shake = max(shake, 1 - (t - r['ban']) / 0.2)
    dx = 14 * shake * math.sin(t * 90)
    dy = 10 * shake * math.cos(t * 77)
    show_phone(im, scr, 540 + dx, 980 + dy, 0.86, rot=-1.5)
    # the bear sits on top of the phone, happy, unaware
    if t < E['ban'] + 2.2:
        bear_at(im, 840, 320, 320, t, t0=E['ban'] - 0.05)
    return im


# ------------------------------------------------------------------ 5. street
def street_base(t, hero_kind, beanie, sign_y, face, crowd=False, friends=0.0, dust=0.0, cam=1.0):
    im = S_.street().copy()
    # passers-by in the back (small legs) when crowded
    hero_at(im, 540, 1180, 1.02, t, kind=hero_kind, arms='down', beanie=beanie, tilt=1.5 * math.sin(t * 1.3),
            bob=2 * math.sin(t * 2), **face)
    put(im, S_.cup(), 860, 1660)
    if sign_y is not None:
        put(im, S_.sign(), 540, sign_y, rot=2 * math.sin(t * 1.6))
    return im


def legs_layer(im, t, t0, specs):
    """specs: (start offset, speed px/s, colour, shoe, scale, y)."""
    for off, v, col, shoe, sc, y in specs:
        u = t - (t0 + off)
        if u < 0:
            continue
        x = -320 + v * u if v > 0 else W + 320 + v * u
        if -400 < x < W + 400:
            ph = (u * abs(v) / 560) % 1.0
            sp = S_.legs(round(ph * 20) / 20, col, shoe)
            if v < 0:
                sp = sp.transpose(Image.FLIP_LEFT_RIGHT)
            put(im, sp, x, y, scale=sc)


def shot_street(t):
    change = E['change']
    old = t >= change
    face = dict(smile=0.6 if not old else 0.0, sad=0.0 if not old else 0.8, look=(0, 0) if not old else (0, 0.5))
    sy = None
    if t >= E['sign_up'] - 0.2:
        k = fx.ease_out_back(ramp(t, E['sign_up'] - 0.2, E['sign_up'] + 0.25))
        sy = lerp(2200, 1430, k)
    im = street_base(t, 'old' if old else 'hoodie', old, sy, face)
    if change - 0.12 <= t < change + 0.3:            # a puff of smoke when the clothes change
        k = 1 - abs(t - change) / (0.12 if t < change else 0.3)
        for j in range(9):
            a = j * 0.7
            glow(im, 540 + 220 * math.cos(a), 1100 + 260 * math.sin(a), 220, (255, 255, 255), 0.9 * k)
    if old and t < change + 1.2:
        put(im, pill('👕 старая одежда', 50), 540, 200, a=1 - ramp(t, change + 0.9, change + 1.2))
    return im


PASSERS = [(0.0, 900, (70, 96, 160), (40, 40, 44), 0.62, 1610), (0.7, -1000, (60, 60, 70), (240, 240, 240), 0.64, 1620),
           (1.5, 1050, (120, 120, 130), (120, 60, 40), 0.6, 1600), (2.3, -880, (60, 130, 100), (30, 30, 34), 0.62, 1615),
           (2.9, 950, (180, 80, 80), (60, 50, 50), 0.62, 1610)]


def shot_wait(t):
    face = dict(sad=0.6, look=(0.6 * math.sin(t * 1.4), 0.2), smile=0.0)
    if t >= E['coin'] + 0.25:
        face = dict(sad=0.2, smile=0.6, brow=0.8, look=(0.6, 0.6))
    im = street_base(t, 'old', True, 1430, face)
    # the coin
    if t >= E['coin'] - 0.45:
        u = ramp(t, E['coin'] - 0.45, E['coin'])
        x = lerp(1100, 860, u)
        y = lerp(1250, 1600, u) - 260 * math.sin(math.pi * u)
        if u < 1:
            put(im, S_.coin(), x, y, rot=u * 720)
        else:
            k = 1 - ramp(t, E['coin'], E['coin'] + 0.5)
            put(im, emoji('✨', 80), 860, 1580, a=k)
            put(im, pill('+1 ₽', 46, bg=GOLD, fg=(60, 30, 10)), 860, 1480 - 60 * (1 - k), a=k)
    return im


def friend_parts(who, t, x, y, scale, face, alpha=1.0):
    hd = C.head(who, blink=blink(t, 1.3 if who == 'cap' else 2.1), **face)
    return C.bust(hd, C.body(who), x, y, scale)


def shot_friends(t):
    hide = sm(ramp(t, E['spotted'] - 0.15, E['spotted'] + 0.2))
    face = dict(sad=0.4, look=(0, 0.2), shock=sm(ramp(t, E['friend_in'], E['friend_in'] + 0.2)) * (1 - hide),
                sweat=hide)
    im = street_base(t, 'old', True, lerp(1430, 1010, hide), face)
    friends(im, t, 0.0)
    if t >= E['spotted']:
        k = pop(t, E['spotted'], 0.3)
        put(im, text_spr('!', 150, (255, 80, 80)), 170, 560, scale=k)
        put(im, text_spr('!', 150, (255, 80, 80)), 910, 560, scale=k)
    return im


def friends(im, t, dust):
    k = sm(ramp(t, E['friend_in'] - 0.4, E['friend_in'] + 0.2))
    laugh = sm(ramp(t, E['spotted'] + 0.1, E['spotted'] + 0.4))
    fa = dict(smile=0.7 + 0.3 * laugh, open_=0.8 * laugh, teeth=laugh, brow=0.6, look=(0.8, 0.2))
    fb = dict(smile=0.6 + 0.4 * laugh, open_=0.6 * laugh, brow=0.8, look=(-0.8, 0.2))
    bob = 6 * math.sin(t * 14) * laugh
    parts_l = friend_parts('cap', t, lerp(-300, 130, k), 1180 + bob, 0.9, fa)
    parts_r = friend_parts('glass', t, lerp(1380, 950, k), 1200 - bob, 0.9, fb)
    if dust <= 0:
        C.place(im, parts_l)
        C.place(im, parts_r)
        return
    # crumbling: draw into a layer, then erase with a noise threshold moving up, particles fly right
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    C.place(lay, parts_l)
    C.place(lay, parts_r)
    a = np.asarray(lay).copy()
    rng = np.random.default_rng(5)
    noise = rng.random((H // 6, W // 6)).repeat(6, 0).repeat(6, 1)
    yy = np.linspace(0, 1, H)[:, None]
    thr = noise * 0.6 + (1 - yy) * 0.4
    keep = thr > dust * 1.05
    a[..., 3] = np.where(keep, a[..., 3], 0)
    im.alpha_composite(Image.fromarray(a, 'RGBA'))
    d = ImageDraw.Draw(im)
    pr = np.random.default_rng(11)
    for j in range(140):
        side = j % 2
        x0 = (130 if side == 0 else 950) + pr.uniform(-200, 200)
        y0 = pr.uniform(700, 1900)
        s = dust - pr.uniform(0, 0.4)
        if s <= 0:
            continue
        x = x0 + 600 * s * pr.uniform(0.4, 1.2)
        y = y0 - 300 * s * pr.uniform(0.2, 1.0)
        r = pr.uniform(3, 8)
        al = int(220 * max(0.0, 1 - s * 1.2))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(120, 110, 120, al))


def shot_nofriends(t):
    dust = ramp(t, E['dust'] - 0.25, E['dust'] + 0.9)
    lower = sm(ramp(t, E['dust'] + 0.2, E['dust'] + 0.7))
    face = dict(sad=0.9, look=(0.5 * math.sin(t), 0.3), sweat=1 - lower)
    im = street_base(t, 'old', True, lerp(1010, 1430, lower), face)
    friends(im, t, max(0.0001, dust))
    # tumbleweed
    u = t - (E['dust'] + 0.1)
    if u > 0:
        x = -150 + 700 * u
        y = 1700 - 60 * abs(math.sin(u * 4.5))
        put(im, S_.tumbleweed(), x, y, rot=-u * 400)
    im = ImageEnhance.Color(im).enhance(1 - 0.5 * sm(ramp(t, E['dust'], E['dust'] + 0.8)))
    return im


# ------------------------------------------------------------------ 6. sofa + DM
def sofa_scene(t, beard=0.0, web=0.0, dim=0.0, face=None, phone_glow=1.0):
    im = S_.sofa_room().copy()
    im.alpha_composite(S_.sofa_back())
    face = face or {}
    hero_at(im, 560, 900, 0.95, t, arms='phone', glow_=phone_glow, tilt=-8 + 1.5 * math.sin(t * 1.1),
            bob=2 * math.sin(t * 1.5), beard=beard, web=web, **face)
    im.alpha_composite(S_.sofa_front())
    if dim > 0:
        im = ImageEnhance.Brightness(im).enhance(1 - 0.35 * dim)
    return im


def shot_sofa(t):
    face = dict(smile=0.8, look=(0, 0.5))
    im = sofa_scene(t, face=face)
    if t >= E['couch'] - 0.4:
        k = pop(t, E['couch'] - 0.4, 0.4)
        put(im, pill('🛋 0 шагов', 52), 540, 200, a=min(1, 2 * k), scale=k)
    return im


def dm_chat():
    # Easter egg for attentive viewers (author's request, 2026-11-05): an instant rude reply flashes on the
    # screen while the phone shrinks into the hero's hands. Not voiced.
    t_reply = S['auto'] + 0.15
    ev = [tg.draft(E['type0'] - 0.5, E['send'] + 0.05, 'дай мишку'),
          tg.msg(E['send'] + 0.05, 'out', 'дай мишку', '12:00', read=t_reply - 0.1 - (E['send'] + 0.05)),
          tg.status(t_reply - 0.15, 'в сети'),
          tg.msg(t_reply, 'in', 'Иди нахуй, еблан', '12:00'),
          tg.status(t_reply + 1.2, 'был(а) давно')]
    return dict(theme='day', name='Павел Дуров', status='был(а) недавно',
                avatar=tg.avatar_letter('П', (80, 150, 220), 84), clock='12:00', events=ev)


def shot_dm(t):
    im = stage_bg(t, 0.5)
    k = sm(ramp(t, S['dm'], S['dm'] + 0.35))
    scr = tg.chat_screen(t, dm_chat())
    show_phone(im, scr, 540, lerp(2300, 1010, k), 0.9, rot=lerp(10, -1, k))
    if t >= E['type0'] - 0.3:
        kk = pop(t, E['type0'] - 0.3, 0.35)
        put(im, pill('🤫 кодовая фраза', 50, bg=GOLD, fg=(60, 30, 10)), 540, 66, a=min(1, kk * 2), scale=kk)
    return im


def shot_auto(t):
    t0 = S['auto']
    pull = sm(ramp(t, t0 + 0.8, t0 + 1.6))
    time_k = ramp(t, t0 + 1.2, E['ask'] + 0.6)
    months = int(1 + 35 * time_k ** 1.6)
    beard = sm(time_k)
    web = sm(ramp(time_k, 0.4, 1.0))
    face = dict(smile=lerp(0.8, 0.0, time_k), sad=0.8 * time_k, tired=time_k, look=(0, 0.5), blink=blink(t, 0.2, 2.4))
    im = sofa_scene(t, beard=beard, web=web, dim=0.6 * time_k, face=face)
    # big phone: shrinks into the hero's hands
    scr = tg.chat_screen(t, dm_chat())
    if pull < 1:
        show_phone(im, scr, lerp(540, 560, pull), lerp(960, 1300, pull), lerp(0.9, 0.12, pull), a=1 - ramp(pull, 0.8, 1))
    else:
        put(im, bubble_one_tick(), 540, 300, scale=1.0 + 0.02 * math.sin(t * 3))
        put(im, pill(f'⏳ прошло {months_text(months)}', 52, bg=(30, 22, 60), fg=(255, 255, 255)), 540, 470)
    # «автоматически» — a checkmark stamp that turns out to be a single grey tick
    return im


def months_text(n):
    if n < 12:
        return f'{n} мес.'
    y = n // 12
    return f'{y} год' if y == 1 else f'{y} года'


@functools.lru_cache(None)
def bubble_one_tick():
    b = tg.bubble('дай мишку', 'out', '12:00', 'day', True)      # read (✓✓): he did see it
    return b.resize((int(b.width * 1.25), int(b.height * 1.25)), Image.LANCZOS)


# ------------------------------------------------------------------ 7. like
def shot_like(t):
    im = stage_bg(t, 1.3)
    t0 = S['like']
    k = pop(t, t0, 0.5)
    y = lerp(2300, 1020, k)
    glow(im, 540, y - 260, 460, (255, 220, 150), 0.4)
    shadow_ell(im, 540, y - 10, 180, 0.3)
    w = 0.5 + 0.5 * math.sin(t * 7.5)
    bear_at(im, 540, y, 600, t, rot=2 * math.sin(t * 3), t0=t0)
    if t >= E['like_btn'] - 0.15:
        kk = pop(t, E['like_btn'] - 0.15, 0.45)
        beat = 1 + 0.06 * max(0.0, math.sin((t - E['like_btn']) * 6))
        put(im, S_.like_button(), 540, 1320, scale=0.78 * kk * beat)
        confetti(im, t, E['like_btn'], 540, 1300, n=50, seed=9)
    put(im, text_spr('СТАВЬ ЛАЙК!', 110, GOLD), 540, 230, a=min(1, k * 2), scale=0.7 + 0.3 * k)
    return im


# ------------------------------------------------------------------ scene table
SHOTS = [
    (S['hook'], shot_hook),
    (S['p1'], lambda t: shot_place(t, 1, S['p1'], E['flip1'])),
    (S['chats'], shot_chats),
    (S['grind'], shot_grind),
    (S['gift'], shot_gift),
    (S['p2'], lambda t: shot_place(t, 2, S['p2'], E['flip2'])),
    (S['street'], shot_street),
    (S['wait'], shot_wait),
    (S['friends'], shot_friends),
    (S['nofriends'], shot_nofriends),
    (S['p3'], lambda t: shot_place(t, 3, S['p3'], E['flip3'])),
    (S['sofa'], shot_sofa),
    (S['dm'], shot_dm),
    (S['auto'], shot_auto),
    (S['like'], shot_like),
]
CUTS = [S[k] for k in ('p1', 'chats', 'grind', 'gift', 'banlist', 'p2', 'street', 'p3', 'sofa', 'dm', 'like')]
WHIPS = [S['chats'], S['street'], S['sofa']]


# ------------------------------------------------------------------ subtitles
from script import LINES  # noqa: E402
LINES_SPOKEN = [s for _, s, _, _ in LINES]


def _timed_script(k):
    """Script words of line k with times interpolated from the ASR words by character position."""
    asr = WORDS[k]
    spoken = LINES_SPOKEN[k].replace('«', '').replace('»', '').split()
    spoken = [w for w in spoken if w not in ('—', '–')]
    if not asr:
        return []
    ac = np.cumsum([0] + [len(w) + 1 for w, _, _ in asr])
    af = ac / ac[-1]
    at = [a for _, a, _ in asr] + [asr[-1][2]]
    sc = np.cumsum([0] + [len(w) + 1 for w in spoken])
    sf = sc / sc[-1]
    return [(w, float(np.interp(sf[j], af, at)), float(np.interp(sf[j + 1], af, at))) for j, w in enumerate(spoken)]


@functools.lru_cache(None)
def _chunks(k):
    out, cur, n = [], [], 0
    for w in _timed_script(k):
        if cur and (n + len(w[0]) > 20 or cur[-1][0][-1] in '.:?!…,'):
            out.append(tuple(cur))
            cur, n = [], 0
        cur.append(w)
        n += len(w[0]) + 1
    if cur:
        out.append(tuple(cur))
    return tuple(out)


@functools.lru_cache(maxsize=256)
def _sub_spr(words, hi):
    f = fx.font('Heavy', 64)
    space = f.getlength(' ')
    ws = [f.getlength(w) for w in words]
    total = sum(ws) + space * (len(words) - 1)
    im = Image.new('RGBA', (int(total) + 60, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 30
    for k, w in enumerate(words):
        col = GOLD if k == hi else (255, 255, 255)
        d.text((x, 60), w, font=f, fill=col + (255,), anchor='lm', stroke_width=8, stroke_fill=(24, 14, 40, 255))
        x += ws[k] + space
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 6))
    out.alpha_composite(im)
    return out


SUB_Y = {'p3': 1760, 'like': 1700, 'hook': 1640, 'wait': 1820, 'friends': 1820, 'nofriends': 1820,
         'street': 1820, 'chats': 1800, 'ban': 1800, 'dm': 1790, 'auto': 1760}


def subtitles(im, t):
    for k in range(len(ON)):
        if ON[k] - 0.05 <= t < END[k] + 0.25:
            chs = _chunks(k)
            for ch in chs:
                a, b = ch[0][1], ch[-1][2]
                if a - 0.05 <= t < b + 0.25 or (ch is chs[-1] and t >= a):
                    hi = max([j for j, w in enumerate(ch) if w[1] <= t] or [0])
                    spr = _sub_spr(tuple(w[0] for w in ch), hi)
                    s = 1 + 0.06 * (1 - ramp(t, a - 0.05, a + 0.1))
                    put(im, spr, W / 2, SUB_Y.get(LINES[k][2], 1700), a=ramp(t, a - 0.05, a + 0.05), scale=s)
                    return
            return


# ------------------------------------------------------------------ frame
def _whip(im, k):
    if k <= 0.01:
        return im
    a = np.asarray(im.convert('RGB'), np.float32)
    n = int(2 + 16 * k)
    out = np.zeros_like(a)
    for j in range(n):
        out += np.roll(a, int((j - n / 2) * 10 * k), axis=1)
    out /= n
    return Image.fromarray(out.astype(np.uint8), 'RGB').convert('RGBA')


@functools.lru_cache(None)
def _vign():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W * 0.7)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.3 * np.clip(d - 0.45, 0, 1) ** 1.5)[..., None]


def render_at(t):
    t = min(max(t, 0.0), DUR - 1e-3)
    fn = [f for s, f in SHOTS if t >= s][-1]
    im = fn(t)
    for c in WHIPS:
        if c - 0.12 <= t < c + 0.14:
            im = _whip(im, 1 - abs(t - c) / 0.14)
    for c in CUTS:
        if c <= t < c + 0.2 and c not in WHIPS:
            k = 1 + 0.04 * (1 - (t - c) / 0.2)
            w, h = W / k, H / k
            im = im.transform((W, H), Image.EXTENT, ((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2),
                              Image.BILINEAR)
            break
    subtitles(im, t)
    out = np.asarray(im.convert('RGB'), np.float32)
    out *= _vign()
    out += np.random.default_rng(int(t * FPS)).normal(0, 2.0, (H // 3, W // 3, 1)).repeat(3, 0).repeat(3, 1)
    out *= 1 - 0.9 * ramp(t, DUR - 0.3, DUR)
    return np.clip(out, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Сначала хайлайты и слово автора «собирай» (config.STYLE_READY)')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
