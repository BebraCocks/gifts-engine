"""64 · «Уроки Айзена», способ 1 «Лестница „да“». Кадр — чистая функция времени.

    python -B render.py --frames 0,600,1500        # пробные кадры (номера кадров, 60 fps) -> build/review/
    python -B render.py --video build/video_only.mp4  # только после «собирай»

Мисед — главный (решение автора): цветной, крупный; Айзен и окружение — чёрно-белая манга.
"""
import functools
import json
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps  # noqa: E402
import frames  # noqa: E402
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import chat_gpt  # noqa: E402

W, H, FPS = 1080, 1920, 60
REFS = HERE / 'refs'
FONTS = HERE.parents[1] / 'input' / 'fonts' / 'SF-Pro-Text'
CUES = json.loads((HERE / 'voice_cues.json').read_text())
DUR = CUES['total']
C = {c['id']: (c['start'], c['end']) for c in CUES['cues']}
GIFT = ('Crystal Ball', 'Femme Fatale')
SWORD_CLIP = HERE / 'refs' / 'sword.mp4'   # видео Gemini (если есть) заменяет меч кодом

CHAT_X, CHAT_Y, CHAT_W = 140, 170, 770
CHAT_IDS = ['A3', 'M1', 'A4', 'M2', 'A5', 'M3', 'A6', 'M4']
SUBS = {
    'A2': 'Тот, кто трижды сказал «да»,\nуже не сможет сказать «нет».',
    'A7': 'Вот как. Ты знал этот приём.',
    'M5': 'Я знаю их все.\nТы пытался меня обмануть?',
    'A8': 'Да. Отрицать очевидное —\nудел слабых.',
    'M6': 'Честный ответ.\nЗа него и дарю.',
    'A9': 'Значит, ключ к тебе —\nчестность. Любопытно.',
    'A10': 'Всё идёт по моему плану.',
    'M7': 'Нет. Это был мой план —\nчтобы ты сказал правду.',
}
PINK = (255, 150, 170)
# Безопасная зона TikTok (автор: надписи не у краёв): текст только в x 140..940, y 240..1400
SAFE_W = 760
SUB_Y = 1290

# ---- сцены (границы по озвучке)
S = [
    ('hook', 0.0), ('ladder', C['A2'][0] - 0.2), ('chat', C['A3'][0] - 0.25), ('collapse', C['M4'][1] + 0.3),
    ('glasses', C['A7'][0] + 0.55), ('calm', C['A7'][0] + 2.05), ('missed5', C['M5'][0] - 0.15),
    ('sword', C['A8'][0] - 0.15), ('missed6', C['M6'][0] - 0.2), ('palm', C['A9'][0] - 0.2),
    ('window', C['A10'][0] - 0.25), ('final', C['M7'][0] - 0.2),
]
START = dict(S)


def scene_at(t):
    name = S[0][0]
    for n, t0 in S:
        if t >= t0:
            name = n
    return name


# ---- помощники
def cl(x):
    return max(0.0, min(1.0, x))


def eo(x):
    x = cl(x)
    return 1 - (1 - x) ** 3


def spring(x, f=2.2, z=0.45):
    x = max(0.0, x)
    return 1 - math.exp(-z * 10 * x) * math.cos(f * 2 * math.pi * x)


@functools.lru_cache(None)
def font(w, s):
    return ImageFont.truetype(str(FONTS / f'SF-Pro-Text-{w}.otf'), s)


@functools.lru_cache(None)
def img(name):
    return Image.open(REFS / name).convert('RGBA')


@functools.lru_cache(None)
def scaled(name, w=None, h=None):
    im = img(name)
    if w:
        h = round(im.height * w / im.width)
    else:
        w = round(im.width * h / im.height)
    return im.resize((w, h), Image.LANCZOS)


@functools.lru_cache(None)
def bg(name, dark=0, blur=0):
    im = img(name).resize((W, H), Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if dark:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, dark)))
    return im


@functools.lru_cache(None)
def envelope():
    """Громкость голоса по кадрам (0..1) — пульс Миседа, когда он говорит."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(HERE / 'build' / 'review' / 'voice_only.mp3'), '-ac', '1',
                          '-ar', '48000', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    n = 48000 // FPS
    e = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n, n)])
    e = np.convolve(e, np.ones(4) / 4, 'same')
    return e / (e.max() + 1e-9)


def env(t):
    e = envelope()
    i = int(t * FPS)
    return float(e[i]) if 0 <= i < len(e) else 0.0


def missed_talking(t):
    for k, (a, b) in C.items():
        if k.startswith('M') and a - 0.05 <= t <= b + 0.05:
            return env(t)
    return 0.0


def camera(im, z=1.0, cx=W / 2, cy=H / 2, sx=0.0, sy=0.0):
    if z == 1.0 and not sx and not sy:
        return im
    w, h = W / z, H / z
    x0 = min(max(cx - w / 2 + sx, 0), W - w)
    y0 = min(max(cy - h / 2 + sy, 0), H - h)
    return im.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BILINEAR)


def shake(t, t0, dur=0.35, amp=18):
    k = (t - t0) / dur
    if not 0 <= k <= 1:
        return 0.0, 0.0
    a = amp * (1 - k) ** 2
    return a * math.sin(t * 91), a * math.cos(t * 77)


def paste(canvas, sprite, x, y, alpha=1.0):
    if alpha <= 0:
        return
    if alpha < 1:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel('A').point(lambda v: int(v * alpha)))
    canvas.alpha_composite(sprite, (int(x), int(y)))


def text_sprite(text, size, weight='Bold', fill=(255, 255, 255), stroke=6, stroke_fill=(0, 0, 0), align='center'):
    f = font(weight, size)
    d = ImageDraw.Draw(Image.new('L', (1, 1)))
    box = d.multiline_textbbox((0, 0), text, font=f, align=align, stroke_width=stroke, spacing=10)
    w, h = int(box[2] - box[0] + 20), int(box[3] - box[1] + 20)
    im = Image.new('RGBA', (w, h))
    ImageDraw.Draw(im).multiline_text((10 - int(box[0]), 10 - int(box[1])), text, font=f, fill=fill, align=align,
                                      stroke_width=stroke, stroke_fill=stroke_fill, spacing=10)
    return im


text_sprite = functools.lru_cache(None)(text_sprite)


@functools.lru_cache(None)
def chalk_noise(w, h):
    rng = np.random.default_rng(7)
    n = rng.random((h, w))
    return Image.fromarray(((n > 0.22) * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.6))


@functools.lru_cache(None)
def chalk(text, size):
    """Белый мел: текст с рваной фактурой."""
    sp = text_sprite(text, size, 'Semibold', (235, 235, 230), 0)
    a = np.asarray(sp.getchannel('A')).astype(np.float32) * (np.asarray(chalk_noise(*sp.size)) / 255.0) * 0.92
    out = sp.copy()
    out.putalpha(Image.fromarray(a.astype('uint8')))
    return out


def fit(sp, maxw=SAFE_W):
    if sp.width <= maxw:
        return sp
    return sp.resize((maxw, round(sp.height * maxw / sp.width)), Image.LANCZOS)



def wipe(sprite, k):
    """Появление слева направо (мелом)."""
    k = cl(k)
    if k >= 1:
        return sprite
    out = sprite.copy()
    m = Image.new('L', sprite.size, 0)
    ImageDraw.Draw(m).rectangle((0, 0, int(sprite.width * k), sprite.height), fill=255)
    a = Image.fromarray(np.minimum(np.asarray(out.getchannel('A')), np.asarray(m)))
    out.putalpha(a)
    return out


def subtitle(im, t, y=SUB_Y):
    for k, txt in SUBS.items():
        a, b = C[k]
        if a - 0.1 <= t <= b + 0.35:
            al = cl((t - a + 0.1) / 0.15) * cl((b + 0.35 - t) / 0.2)
            col = PINK if k.startswith('M') else (255, 255, 255)
            sp = fit(text_sprite(txt, 58, 'Bold', col, 7))
            paste(im, sp, (W - sp.width) / 2, y - sp.height / 2, al)


def flash(im, t, t0, dur=0.12, col=(255, 255, 255)):
    k = (t - t0) / dur
    if 0 <= k <= 1:
        im.alpha_composite(Image.new('RGBA', (W, H), col + (int(200 * (1 - k)),)))


# ---- Мисед
@functools.lru_cache(None)
def missed_card(size, radius=None):
    src = Image.open(REFS / 'missed.jpg').convert('RGB').resize((size, size), Image.LANCZOS)
    m = Image.new('L', (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius or size // 9, fill=255)
    out = Image.new('RGBA', (size, size))
    out.paste(src, (0, 0), m)
    return out


@functools.lru_cache(None)
def glow(size, col=PINK, blur=40, pad=90):
    g = Image.new('RGBA', (size + 2 * pad, size + 2 * pad))
    ImageDraw.Draw(g).rounded_rectangle((pad, pad, pad + size, pad + size), radius=size // 9, fill=col + (255,))
    return g.filter(ImageFilter.GaussianBlur(blur))


def draw_missed(im, t, cx, cy, size, alpha=1.0, ring=True):
    talk = missed_talking(t)
    sc = 1.0 + 0.045 * talk
    s = int(size * sc)
    s -= s % 2
    if ring:
        g = glow(s // 4 * 4)
        ga = 0.45 + 0.45 * talk + 0.1 * math.sin(t * 3)
        paste(im, g, cx - g.width / 2, cy - g.height / 2, alpha * min(1.0, ga))
    card = missed_card(s)
    paste(im, card, cx - s / 2, cy - s / 2, alpha)
    if ring:
        r = Image.new('RGBA', (s + 24, s + 24))
        ImageDraw.Draw(r).rounded_rectangle((4, 4, s + 19, s + 19), radius=s // 9 + 10, outline=PINK + (255,),
                                            width=6)
        paste(im, r, cx - r.width / 2, cy - r.height / 2, alpha * (0.6 + 0.4 * talk))


@functools.lru_cache(None)
def pinned_photo(size):
    """Фото Миседа, приколотое к доске: цветное, белая рамка, скотч."""
    card = Image.open(REFS / 'missed.jpg').convert('RGB').resize((size, size), Image.LANCZOS)
    fr = Image.new('RGBA', (size + 28, size + 28), (250, 250, 248, 255))
    fr.paste(card, (14, 14))
    tape = Image.new('RGBA', (120, 40), (235, 235, 225, 170))
    fr2 = Image.new('RGBA', (fr.width + 40, fr.height + 60))
    fr2.alpha_composite(fr, (20, 30))
    fr2.alpha_composite(tape.rotate(-8, expand=True), (fr2.width // 2 - 64, 6))
    return fr2.rotate(3, expand=True, resample=Image.BICUBIC)


def gift(t, size):
    path = G.model_file(GIFT[0], GIFT[1], 'json')
    return lottie.frame(str(path), t, size=size)


def gift_glow(size):
    return glow(size, (255, 170, 230), blur=50, pad=70)


# ---- лестница мелом
BOARD = (0, 345, 855, 890)
LAD_X = (170, 320)
LAD_Y = (875, 520)
RUNG_Y = [800, 710, 620]


def ladder_parts():
    """Отрезки лестницы: (x0, y0, x1, y1)."""
    parts = [(LAD_X[0], LAD_Y[0], LAD_X[0], LAD_Y[1]), (LAD_X[1], LAD_Y[0], LAD_X[1], LAD_Y[1])]
    parts += [(LAD_X[0], y, LAD_X[1], y) for y in RUNG_Y]
    return parts


def chalk_line(d, p, k=1.0, w=9):
    x0, y0, x1, y1 = p
    d.line((x0, y0, x0 + (x1 - x0) * k, y0 + (y1 - y0) * k), fill=(235, 235, 230, 215), width=w)


def draw_ladder(im, t, rails_t, rung_ts, labels=True):
    lay = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(lay)
    parts = ladder_parts()
    for p in parts[:2]:
        chalk_line(d, p, eo((t - rails_t) / 0.6))
    for i, rt in enumerate(rung_ts):
        if t >= rt:
            chalk_line(d, parts[2 + i], eo((t - rt) / 0.3))
            if labels:
                sp = chalk('ДА', 46)
                paste(lay, sp, LAD_X[1] + 24, RUNG_Y[i] - sp.height / 2, cl((t - rt - 0.15) / 0.2))
    m = np.asarray(chalk_noise(W, H)) / 255.0
    a = np.asarray(lay.getchannel('A')).astype(np.float32) * (0.55 + 0.45 * m)
    lay.putalpha(Image.fromarray(a.astype('uint8')))
    im.alpha_composite(lay)


def board_base(t, photo=True):
    im = bg('bg_classroom.png').copy()
    if photo:
        ph = pinned_photo(300)
        paste(im, ph, 640 - ph.width / 2, 640 - ph.height / 2)
    return im


# ---- сцены
def s_hook(t):
    im = board_base(t, photo=False)
    ph = pinned_photo(290)
    k = spring(t / 0.9)
    paste(im, ph.resize((max(1, int(ph.width * k)), max(1, int(ph.height * k)))),
          480 - ph.width * k / 2, 640 - ph.height * k / 2)
    a1 = scaled('aizen_01_teach.png', h=980)
    paste(im, a1, W - a1.width + 70 + 60 * (1 - eo(t / 0.8)), H - a1.height + 40, cl(t / 0.4))
    tt = fit(text_sprite('Как получить подарок\nот Миседа?', 80, 'Heavy', (255, 255, 255), 9), 720)
    paste(im, tt, (W - tt.width) / 2, 250, cl((t - 0.15) / 0.25))
    sub = fit(chalk('Способ 1: лестница «да»', 54), 700)
    paste(im, wipe(sub, (t - 3.4) / 1.0), 140, 822)
    return camera(im, 1.0 + 0.03 * t / 6.7, W / 2, 800)


def s_ladder(t):
    t0 = START['ladder']
    im = board_base(t)
    title = chalk('Лестница «да»', 62)
    paste(im, wipe(title, (t - t0) / 0.9), 140, 365)
    a2 = C['A2']
    rung_ts = [a2[0] + 0.9, a2[0] + 1.4, a2[0] + 1.9]
    draw_ladder(im, t, t0 + 0.6, rung_ts)
    q = chalk('?', 90)
    paste(im, q, (LAD_X[0] + LAD_X[1]) / 2 - q.width / 2, LAD_Y[1] - 60, cl((t - a2[0] - 3.2) / 0.3))
    a = scaled('aizen_02_chalk.png', w=500)
    paste(im, a, W - a.width + 30, H - a.height, cl((t - t0) / 0.3))
    return camera(im, 1.06 - 0.03 * eo((t - t0) / 6), 500, 760)


def s_chat(t):
    n, pop = 0, None
    for k, cid in enumerate(CHAT_IDS):
        if t >= C[cid][0]:
            n = k + 1
            p = (t - C[cid][0]) / 0.28
            if p < 1:
                pop = (k, p)
    cw = CHAT_W
    fr = chat_gpt.chat_frame(n, pop).resize((cw, round(1672 * cw / 941)), Image.BILINEAR).convert('RGBA')
    im = bg('bg_classroom.png', dark=170, blur=8).copy()
    sh = Image.new('RGBA', (cw + 60, fr.height + 60))
    ImageDraw.Draw(sh).rounded_rectangle((30, 30, cw + 30, fr.height + 30), radius=40, fill=(0, 0, 0, 200))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (CHAT_X - 30, CHAT_Y - 10))
    m = Image.new('L', fr.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, fr.width - 1, fr.height - 1), radius=36, fill=255)
    fr.putalpha(m)
    im.alpha_composite(fr, (CHAT_X, CHAT_Y))
    t0 = START['chat']
    z = 1.0 + 0.015 * cl((t - t0) / 10)
    no = C['M4'][0]
    if t >= no:
        k = eo((t - no) / 0.25)
        z += 0.18 * k
        sx, sy = shake(t, no, 0.4, 16)
        f = CHAT_W / 941
        bx, by = CHAT_X + 157 * f, CHAT_Y + 1362 * f
        return camera(im, z, bx * k + W / 2 * (1 - k), by * k + H / 2 * (1 - k), sx, sy)
    return camera(im, z, W / 2, H / 2)


def s_collapse(t):
    t0 = START['collapse']
    im = board_base(t)
    title = chalk('Лестница «да»', 62)
    paste(im, title, 140, 365)
    lay = Image.new('RGBA', (W, H))
    for i, (x0, y0, x1, y1) in enumerate(ladder_parts()):
        k = max(0.0, t - t0 - 0.05 * i)
        dy = 1400 * k * k
        rot = (i % 2 * 2 - 1) * 70 * k
        L = math.hypot(x1 - x0, y1 - y0)
        seg = Image.new('RGBA', (int(L) + 20, 20))
        ImageDraw.Draw(seg).line((10, 10, 10 + L, 10), fill=(235, 235, 230, 210), width=9)
        ang = -math.degrees(math.atan2(y1 - y0, x1 - x0)) + rot
        seg = seg.rotate(ang, expand=True, resample=Image.BICUBIC)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + dy
        if cy < 960:
            paste(lay, seg, cx - seg.width / 2, cy - seg.height / 2, 1 - cl(k / 0.9))
    im.alpha_composite(lay)
    rng = np.random.default_rng(3)
    d = ImageDraw.Draw(im)
    for _ in range(70):
        x, y, vx, vy = rng.uniform(150, 340), rng.uniform(480, 860), rng.normal(0, 120), rng.uniform(-80, 60)
        k = t - t0
        px, py = x + vx * k, y + vy * k + 300 * k * k
        a = int(160 * cl(1 - k / 1.0))
        if a > 0 and py < 890:
            d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(230, 230, 225, a))
    a = scaled('aizen_04_calm.png', h=1180)
    paste(im, a, W - a.width - 10, H - a.height + 60)
    sx, sy = shake(t, t0, 0.3, 10)
    return camera(im, 1.03, W / 2, 900, sx, sy)


@functools.lru_cache(None)
def speedlines(dark=True, n=140, seed=1):
    rng = np.random.default_rng(seed)
    im = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(im)
    cx, cy = W / 2, H * 0.42
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(420, 620)
        w = rng.uniform(2, 9)
        col = (0, 0, 0, 255) if dark else (255, 255, 255, 220)
        p0 = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
        p1 = (cx + 1600 * math.cos(a), cy + 1600 * math.sin(a))
        p2 = (cx + 1600 * math.cos(a + w / 1600), cy + 1600 * math.sin(a + w / 1600))
        d.polygon([p0, p1, p2], fill=col)
    return im


def s_glasses(t):
    t0 = START['glasses']
    im = Image.new('RGBA', (W, H), (245, 245, 245, 255))
    im.alpha_composite(speedlines(True))
    a = scaled('aizen_03_glasses.png', w=1240)
    paste(im, a, (W - a.width) / 2, H - a.height + 40)
    k = (t - t0 - 0.2) / 0.5
    if 0 <= k <= 1:
        s = 1 - abs(2 * k - 1)
        for lx in (W / 2 - 1240 / 2 + 565 * 1240 / 1312, W / 2 - 1240 / 2 + 795 * 1240 / 1312):
            ly = H - a.height + 40 + 575 * 1240 / 1312
            star(im, lx, ly, 120 * s)
    return camera(im, 1.0 + 0.05 * eo((t - t0) / 1.5), W / 2, 900)


def star(im, x, y, r):
    if r < 2:
        return
    d = ImageDraw.Draw(im)
    w = max(2, r / 9)
    d.polygon([(x - r, y), (x, y - w), (x + r, y), (x, y + w)], fill=(255, 255, 255, 255))
    d.polygon([(x, y - r * 0.7), (x - w, y), (x, y + r * 0.7), (x + w, y)], fill=(255, 255, 255, 255))
    d.ellipse((x - w * 1.6, y - w * 1.6, x + w * 1.6, y + w * 1.6), fill=(255, 255, 255, 255))


def s_calm(t):
    t0 = START['calm']
    im = board_base(t, photo=False)
    ph = pinned_photo(380)
    paste(im, ph, 430 - ph.width / 2, 610 - ph.height / 2)
    a = scaled('aizen_04_calm.png', h=1180)
    paste(im, a, W - a.width - 10, H - a.height + 60)
    return camera(im, 1.0 + 0.05 * eo((t - t0) / 2), 430, 700)


def missed_scene(t, t0, gift_at=None):
    im = bg('bg_classroom.png', dark=150, blur=6).copy()
    k = eo((t - t0) / 0.35)
    size = int(640 * (0.85 + 0.15 * k))
    draw_missed(im, t, W / 2, 770, size, alpha=cl((t - t0) / 0.2))
    name = text_sprite('Мисед', 64, 'Heavy', PINK, 7)
    paste(im, name, (W - name.width) / 2, 770 - size / 2 - 115, cl((t - t0 - 0.1) / 0.25))
    if gift_at is not None and t >= gift_at:
        g = eo((t - gift_at) / 0.45)
        gs = int(320 * spring((t - gift_at) / 0.6))
        if gs > 8:
            gl = gift_glow(gs)
            gx, gy = W / 2 + 230, 770 + 230
            paste(im, gl, gx - gl.width / 2, gy - gl.height / 2, 0.8 * g)
            gf = gift(t - gift_at, gs)
            paste(im, gf, gx - gs / 2, gy - gs / 2)
    return im


def s_missed5(t):
    return missed_scene(t, START['missed5'])


def s_sword(t):
    t0 = START['sword']
    if SWORD_CLIP.is_file():
        return sword_clip(t - t0)
    im = bg('bg_classroom.png', dark=60).copy()
    hit = C['A8'][0] + 0.75   # после «Да.»
    k = (t - hit)
    if k >= 0:
        im.alpha_composite(speedlines(True, 180, 5).copy() if k < 0.9 else Image.new('RGBA', (W, H)))
    a = scaled('aizen_04_calm.png', h=1650)
    ax, ay = (W - a.width) / 2 + 60, H - a.height + 120
    paste(im, a, ax, ay)
    # клинок: блик вдоль рукояти и полосой через кадр
    hx, hy = ax + 505 * a.width / 941, ay + 425 * a.height / 1672
    if 0 <= k <= 1.4:
        s = math.sin(math.pi * cl(k / 1.4))
        streak = Image.new('RGBA', (W, H))
        d = ImageDraw.Draw(streak)
        ang = math.radians(-52)
        L = 1500 * eo(k / 0.25)
        x1, y1 = hx + L * math.cos(ang), hy + L * math.sin(ang)
        x2, y2 = hx - L * math.cos(ang), hy - L * math.sin(ang)
        d.line((x2, y2, x1, y1), fill=(255, 255, 255, int(255 * s)), width=int(10 + 18 * s))
        streak = streak.filter(ImageFilter.GaussianBlur(3))
        d = ImageDraw.Draw(streak)
        d.line((x2, y2, x1, y1), fill=(255, 255, 255, int(255 * s)), width=4)
        im.alpha_composite(streak)
        star(im, hx, hy, 170 * s)
    # давление: тёмные края пульсируют
    if k >= 0:
        p = math.exp(-2.2 * k) * (0.6 + 0.4 * math.sin(k * 14))
        vig = vignette()
        paste(im, vig, 0, 0, cl(p))
    flash(im, t, hit, 0.1)
    sx, sy = shake(t, hit, 0.45, 22)
    return camera(im, 1.0 + 0.06 * eo((t - t0) / 4), W / 2, 820, sx, sy)


@functools.lru_cache(None)
def vignette():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H * 0.45) / (H / 2)) ** 2)
    a = np.clip((r - 0.55) / 0.6, 0, 1) * 255
    im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    im.putalpha(Image.fromarray(a.astype('uint8')))
    return im


@functools.lru_cache(None)
def _sword_frames():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(SWORD_CLIP), '-vf',
                          f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def sword_clip(dt):
    fr = _sword_frames()
    i = min(len(fr) - 1, max(0, int(dt * FPS)))
    return Image.fromarray(fr[i]).convert('RGBA')


def s_missed6(t):
    return missed_scene(t, START['missed6'], gift_at=C['M6'][1] - 1.1)


def s_palm(t):
    t0 = START['palm']
    im = bg('bg_classroom.png', dark=40).copy()
    a = scaled('aizen_05_palm.png', w=980)
    ax, ay = W - a.width + 120, H - a.height
    paste(im, a, ax, ay)
    px, py = ax + 820 * a.width / 1312, ay + 760 * a.height / 1199
    k = eo((t - t0) / 0.6)
    gs = 270
    gx = px + 90
    gy = py - 110 - 600 * (1 - k)
    bob = 12 * math.sin((t - t0) * 2.4)
    gl = gift_glow(gs)
    paste(im, gl, gx - gl.width / 2, gy + bob - gl.height / 2, 0.85)
    paste(im, gift(t, gs), gx - gs / 2, gy + bob - gs / 2)
    # уведомление: подарок от Миседа (цветное, сверху)
    n = notif()
    nk = spring((t - t0 - 0.3) / 0.7)
    paste(im, n, 140, 250 - 360 * (1 - nk), cl((t - t0 - 0.3) / 0.2))
    return camera(im, 1.0 + 0.04 * eo((t - t0) / 5), gx, 1100)


@functools.lru_cache(None)
def notif():
    w, h = 780, 160
    im = Image.new('RGBA', (w, h))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=40, fill=(30, 30, 34, 235),
                                         outline=PINK + (255,), width=4)
    av = missed_card(118, 59)
    im.alpha_composite(av, (26, 26))
    d = ImageDraw.Draw(im)
    d.text((170, 30), 'Мисед', font=font('Bold', 44), fill=PINK)
    d.text((170, 92), 'отправил вам подарок', font=font('Regular', 40), fill=(235, 235, 235))
    return im


def s_window(t):
    t0 = START['window']
    im = bg('bg_window.png').copy()
    a = scaled('aizen_06_back.png', h=1150)
    sway = 6 * math.sin((t - t0) * 2.0)
    paste(im, a, 20 + sway, H - a.height + 20)
    return camera(im, 1.0 + 0.03 * eo((t - t0) / 3), 380, 1100)


def s_final(t):
    t0 = START['final']
    im = bg('bg_window.png', dark=150, blur=6).copy()
    k = eo((t - t0) / 0.5)
    size = int(560 + 260 * k)
    cy = 820
    draw_missed(im, t, W / 2, cy, size)
    gs = 300
    gx, gy = W / 2 + size / 2 - 40, cy + size / 2 - 30 + 10 * math.sin(t * 2.4)
    gl = gift_glow(gs)
    paste(im, gl, gx - gl.width / 2, gy - gl.height / 2, 0.8 * k)
    paste(im, gift(t, gs), gx - gs / 2, gy - gs / 2, k)
    end = C['M7'][1] + 0.05
    if t >= end:
        e = cl((t - end) / 0.3)
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(170 * e))))
        t1 = fit(text_sprite('На Миседа\nманипуляции\nне работают', 92, 'Heavy', (255, 255, 255), 10))
        paste(im, t1, (W - t1.width) / 2, 520 - 60 * (1 - eo((t - end) / 0.35)), e)
        t2 = fit(text_sprite('Способ 2 — «Нога в двери»', 56, 'Bold', PINK, 7))
        paste(im, t2, (W - t2.width) / 2, 1270, cl((t - end - 0.4) / 0.3))
    if DUR - t < 0.35:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * cl(1 - (DUR - t) / 0.35)))))
    return im


SCENES = {'hook': s_hook, 'ladder': s_ladder, 'chat': s_chat, 'collapse': s_collapse, 'glasses': s_glasses,
          'calm': s_calm, 'missed5': s_missed5, 'sword': s_sword, 'missed6': s_missed6, 'palm': s_palm,
          'window': s_window, 'final': s_final}


def render_at(t):
    s = scene_at(t)
    im = SCENES[s](t)
    if s != 'final':
        subtitle(im, t, 540 if s == 'palm' else SUB_Y)
    if s not in ('hook', 'sword'):
        flash(im, t, START[s], 0.1)
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return render_at(i / FPS).tobytes()


if __name__ == '__main__':
    frames.cli(render_at, frame_bytes, W, H, FPS, int(round(DUR * FPS)))
