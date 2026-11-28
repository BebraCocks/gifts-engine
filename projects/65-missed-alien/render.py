"""Рендер серии 1 «Будильник» (всё кодом). Кадр — чистая функция времени.

    python -B render.py --frames 2.8,5,20,30,38,47,56     # build/review/frame_*.jpg
    python -B render.py --build missed_alarm_v1.mp4         # build/<имя> со звуком build/mix.wav
"""
import functools
import hashlib
import json
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import art  # noqa: E402
from timeline import T, V, D, DUR  # noqa: E402

W, H, FPS = 1080, 1920, 60
FD = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
SPR = HERE / 'build' / 'sprites'
rng0 = np.random.default_rng(65)
WORDS = {w: (a, b) for w, a, b in []}
_ws = json.load(open(HERE / 'data' / 'words_asr.json', encoding='utf-8'))['segments']


def word_t(word, after=0.0):
    for w, a, b in _ws:
        if a >= after and w.lower().strip('?!,.…—') == word.lower():
            return a
    raise KeyError(word)


ROLE_T = [word_t('Первый'), word_t('второй'), word_t('третий'), word_t('уснул', 15) + 0.35, word_t('По')]
CROSS_T = word_t('первые')


@functools.lru_cache(64)
def font(w, s):
    return ImageFont.truetype(str(FD / f'SF-Pro-Text-{w}.otf'), s)


def cl(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def eo(x):
    x = cl(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def spring(x, f=2.2, z=0.45):
    if x <= 0:
        return 0.0
    w = 2 * math.pi * f
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


def lerp(a, b, k):
    return a + (b - a) * k


# ------------------------------------------------------------------ голос → рот
def _env():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(HERE / 'build' / 'review' / 'voice_only.mp3'),
                          '-f', 'f32le', '-ac', '1', '-ar', '6000', '-'], capture_output=True, check=True).stdout
    a = np.abs(np.frombuffer(raw, np.float32))
    hop = 6000 // FPS
    n = len(a) // hop
    e = a[:n * hop].reshape(n, hop).mean(1)
    return e / (e.max() + 1e-9)


ENV = _env()


def speaking(who, t):
    for k, t0 in V.items():
        if (k[0] in 'MI') == (who == 'M') and t0 <= t < t0 + D[k]:
            return k
    return None


def mouth_open(who, t):
    if not speaking(who, t):
        return 0
    i = int(t * FPS)
    v = ENV[i] if i < len(ENV) else 0
    return 2 if v > 0.22 else 1 if v > 0.08 else 0


# ------------------------------------------------------------------ спрайты с кэшем на диске
def _key(kind, p):
    return kind + '_' + hashlib.md5(json.dumps(p, sort_keys=True).encode()).hexdigest()[:12]


@functools.lru_cache(256)
def _sprite(kind, pj):
    p = json.loads(pj)
    path = SPR / (_key(kind, p) + '.png')
    if path.exists():
        return Image.open(path).convert('RGBA')
    SPR.mkdir(parents=True, exist_ok=True)
    im = art.missed(p) if kind == 'missed' else art.dimon(p) if kind == 'dimon' else art.dimon_legs(**p)
    tmp = path.with_suffix(f'.{id(im)}.png')
    im.save(tmp)
    tmp.replace(path)
    return im


def sprite(kind, **p):
    return _sprite(kind, json.dumps(p, sort_keys=True))


@functools.lru_cache(512)
def _scaled(kind, pj, scale, light, rot=0, flip=False):
    im = _sprite(kind, pj)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    return relight(im, light)


def scaled(kind, scale, light='day', rot=0, flip=False, **p):
    return _scaled(kind, json.dumps(p, sort_keys=True), round(scale, 3), light, rot, flip)


def relight(im, light):
    if light == 'day':
        return im
    a = np.asarray(im, np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    if light == 'dark':                                   # почти не видно в тёмном углу
        rgb = rgb * np.array([0.10, 0.10, 0.18])
    elif light == 'night':
        rgb = rgb * np.array([0.78, 0.80, 0.95])
        m = Image.fromarray(a[..., 3].astype(np.uint8))
        inner = np.asarray(m.filter(ImageFilter.MinFilter(9)), np.float32) / 255
        rim = np.clip(a[..., 3] / 255 - inner, 0, 1) * np.clip(np.linspace(1.4, -0.6, a.shape[1]), 0, 1)[None, :]
        rgb = rgb + rim[..., None] * np.array([60, 70, 100])
    elif light == 'beam':
        rgb = rgb * np.array([0.92, 0.96, 1.0]) + np.array([10, 18, 30])
        fade = np.clip((np.linspace(1, 0, a.shape[0]) - 0.0) / 0.35, 0, 1)[:, None, None]
        al = al * fade
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), 'RGBA')


def put(im, spr, cx, bottom):
    im.alpha_composite(spr, (int(cx - spr.width / 2), int(bottom - spr.height)))


# ------------------------------------------------------------------ фоны
def vgrad(w, h, top, bot):
    k = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float) * (1 - k) + np.array(bot, float) * k
    return Image.fromarray(np.repeat(a, w, 1).astype(np.uint8), 'RGB').convert('RGBA')


WIN = (70, 230, 470, 780)
BED = (20, 1240, 640, 1600)          # матрас: x0, верх, x1, низ
CHAIR_X = 860


@functools.lru_cache(4)
def room(light):
    night = light == 'night'
    im = vgrad(W, H, (22, 28, 58), (12, 14, 32)) if night else vgrad(W, H, (250, 232, 208), (238, 206, 176))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(3)
    # обои: мелкий ромб
    pat = (30, 36, 70, 255) if night else (240, 216, 188, 255)
    for y in range(120, 1560, 90):
        for x in range((y // 90) % 2 * 45, W, 90):
            d.regular_polygon((x, y, 7), 4, fill=pat)
    wx0, wy0, wx1, wy1 = WIN
    sky = vgrad(wx1 - wx0, wy1 - wy0, (34, 52, 110), (60, 80, 140)) if night else vgrad(wx1 - wx0, wy1 - wy0, (120, 190, 250), (200, 230, 255))
    sd = ImageDraw.Draw(sky)
    if night:
        for _ in range(40):
            x, y = rng.integers(0, wx1 - wx0), rng.integers(0, wy1 - wy0)
            s = int(rng.choice([1, 1, 2]))
            sd.ellipse((x, y, x + s, y + s), fill=(230, 235, 255))
        halo = Image.new('RGBA', sky.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse((170, 30, 370, 230), fill=(230, 235, 255, 90))
        sky.alpha_composite(halo.filter(ImageFilter.GaussianBlur(30)))
        ImageDraw.Draw(sky).ellipse((210, 70, 330, 190), fill=(250, 245, 220, 255))
    else:
        halo = Image.new('RGBA', sky.size, (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse((200, 40, 400, 240), fill=(255, 250, 200, 160))
        sky.alpha_composite(halo.filter(ImageFilter.GaussianBlur(30)))
        sd = ImageDraw.Draw(sky)
        sd.ellipse((250, 90, 350, 190), fill=(255, 236, 140, 255))
        for cx, cy in ((90, 330), (260, 420)):
            for dx, r in ((-50, 40), (0, 55), (50, 40)):
                sd.ellipse((cx + dx - r, cy - r, cx + dx + r, cy + r), fill=(255, 255, 255, 255))
        # крыши за окном
        for x0, hh in ((0, 120), (110, 80), (220, 140), (330, 90)):
            sd.rectangle((x0, wy1 - wy0 - hh, x0 + 100, wy1 - wy0), fill=(170, 190, 220, 255))
    im.alpha_composite(sky, (wx0, wy0))
    fc = (40, 36, 52, 255) if night else (255, 255, 255, 255)
    d.rectangle((wx0 - 18, wy0 - 18, wx1 + 18, wy1 + 18), outline=fc, width=22)
    d.line((wx0 + (wx1 - wx0) // 2, wy0, wx0 + (wx1 - wx0) // 2, wy1), fill=fc, width=14)
    d.line((wx0, wy0 + 260, wx1, wy0 + 260), fill=fc, width=14)
    cur, cur2 = ((46, 40, 78, 255), (36, 30, 64, 255)) if night else ((240, 120, 110, 255), (220, 100, 92, 255))
    for x0, x1 in ((20, 120), (420, 520)):
        d.rectangle((x0, 180, x1, 900), fill=cur)
        for k in range(x0 + 18, x1, 26):
            d.line((k, 180, k, 900), fill=cur2, width=6)
    # постер (планета) справа
    pc = ((36, 44, 86, 255), (60, 72, 128, 255), (52, 64, 116, 255)) if night else ((70, 80, 150, 255), (250, 200, 90, 255), (240, 140, 90, 255))
    d.rounded_rectangle((720, 330, 960, 640), 12, fill=pc[0], outline=(255, 255, 255, 60), width=6)
    d.ellipse((790, 400, 890, 500), fill=pc[1])
    d.ellipse((770, 440, 910, 460), outline=pc[2], width=6)
    for x, y in ((750, 360), (930, 600), (760, 600), (920, 380)):
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255, 200))
    # пол
    fl, fl2 = ((18, 18, 36, 255), (24, 24, 46, 255)) if night else ((200, 150, 110, 255), (186, 136, 98, 255))
    d.rectangle((0, 1560, W, H), fill=fl)
    for y in range(1580, H, 46):
        d.line((0, y, W, y), fill=fl2, width=3)
    if night:
        beam = Image.new('L', (W, H), 0)
        ImageDraw.Draw(beam).polygon([(wx0, wy0), (wx1, wy0), (1080, 1500), (430, 1700)], fill=50)
        im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), v) for v in (170, 190, 255)] + [beam.filter(ImageFilter.GaussianBlur(40))]))
    else:
        beam = Image.new('L', (W, H), 0)
        ImageDraw.Draw(beam).polygon([(wx0, wy0), (wx1, wy0), (1080, 1560), (430, 1700)], fill=60)
        im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), v) for v in (255, 240, 190)] + [beam.filter(ImageFilter.GaussianBlur(40))]))
    # кровать: изголовье и матрас (одеяло рисуется поверх Димона)
    hb = (70, 58, 110, 255) if night else (150, 100, 70, 255)
    d.rounded_rectangle((BED[0], 1000, BED[0] + 60, 1620), 20, fill=hb)
    d.rounded_rectangle((BED[0], BED[1] + 40, BED[2], BED[3]), 30, fill=(60, 60, 100, 255) if night else (235, 235, 245, 255))
    d.rectangle((BED[0] + 20, BED[3] - 10, BED[2] - 20, 1660), fill=hb)
    return im


def blanket(im, light, y0=1300):
    night = light == 'night'
    c, c2 = ((50, 70, 140, 255), (40, 58, 120, 255)) if night else ((120, 170, 240, 255), (100, 150, 225, 255))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((BED[0] + 70, y0, BED[2] + 10, BED[3] + 10), 50, fill=c)
    for x in range(BED[0] + 130, BED[2], 90):
        d.line((x, y0 + 30, x, BED[3]), fill=c2, width=5)
    d.rounded_rectangle((BED[0] + 70, y0, BED[2] + 10, y0 + 50), 25, fill=(235, 240, 255, 255) if not night else (90, 100, 160, 255))


def pillow(im, light, x=170, y=1200, rot=0):
    night = light == 'night'
    p = Image.new('RGBA', (260, 140), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle((0, 0, 259, 139), 60, fill=(120, 125, 170, 255) if night else (255, 255, 255, 255))
    ImageDraw.Draw(p).rounded_rectangle((10, 10, 249, 129), 55, outline=(100, 105, 150, 255) if night else (225, 225, 235, 255), width=4)
    if rot:
        p = p.rotate(rot, expand=True, resample=Image.BICUBIC)
    im.alpha_composite(p, (int(x - p.width / 2), int(y - p.height / 2)))


def armchair_back(im, light):
    d = ImageDraw.Draw(im)
    c, dk = ((54, 46, 92, 255), (40, 34, 72, 255))
    d.rounded_rectangle((CHAIR_X - 200, 930, CHAIR_X + 200, 1560), 90, fill=c)
    d.rounded_rectangle((CHAIR_X - 165, 965, CHAIR_X + 165, 1500), 70, fill=dk)


def armchair_front(im, light):
    d = ImageDraw.Draw(im)
    for k in (-1, 1):
        x0 = CHAIR_X + k * 175
        d.rounded_rectangle((x0 - 55, 1300, x0 + 55, 1600), 45, fill=(62, 54, 104, 255))
        d.rounded_rectangle((x0 - 55, 1300, x0 + 55, 1345), 22, fill=(74, 66, 120, 255))
    d.rounded_rectangle((CHAIR_X - 190, 1420, CHAIR_X + 190, 1600), 40, fill=(58, 50, 98, 255))


def table_front(im):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((670, 1330, 1075, 1370), 14, fill=(170, 110, 70, 255))
    d.rectangle((690, 1370, 1055, 1390), fill=(140, 88, 54, 255))
    for x in (700, 1030):
        d.rectangle((x, 1390, x + 24, 1600), fill=(140, 88, 54, 255))


def table_back(im):
    d = ImageDraw.Draw(im)       # спинка стула за Миседом
    d.rounded_rectangle((CHAIR_X - 150, 1060, CHAIR_X + 150, 1340), 30, fill=(200, 130, 90, 255))
    d.rounded_rectangle((CHAIR_X - 125, 1085, CHAIR_X + 125, 1320), 24, fill=(220, 150, 108, 255))


def mug(im, x, y, t):
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x - 34, y - 40, x + 34, y + 36), 12, fill=(250, 110, 120, 255))
    d.arc((x + 18, y - 24, x + 56, y + 16), 270, 90, fill=(250, 110, 120, 255), width=10)
    d.ellipse((x - 30, y - 48, x + 30, y - 32), fill=(140, 80, 50, 255))
    for k in range(3):                       # пар
        ph = (t * 0.6 + k / 3) % 1
        sx = x - 14 + k * 14 + math.sin(ph * 6 + k) * 8
        sy = y - 50 - ph * 90
        a = int(140 * math.sin(math.pi * ph))
        st = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
        ImageDraw.Draw(st).ellipse((8, 8, 32, 32), fill=(255, 255, 255, a))
        im.alpha_composite(st.filter(ImageFilter.GaussianBlur(4)), (int(sx - 20), int(sy - 20)))


def wall_clock(im, hh, mm, light):
    cx, cy, r = 600, 330, 64
    d = ImageDraw.Draw(im)
    d.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=(60, 60, 90, 255) if light == 'night' else (120, 80, 60, 255))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(240, 240, 250, 255))
    for k in range(12):
        a = k / 12 * 2 * math.pi
        d.line((cx + math.sin(a) * (r - 12), cy - math.cos(a) * (r - 12), cx + math.sin(a) * (r - 4), cy - math.cos(a) * (r - 4)), fill=(60, 60, 70, 255), width=4)
    ah = (hh % 12 + mm / 60) / 12 * 2 * math.pi
    am = mm / 60 * 2 * math.pi
    d.line((cx, cy, cx + math.sin(ah) * 34, cy - math.cos(ah) * 34), fill=(30, 30, 40, 255), width=8)
    d.line((cx, cy, cx + math.sin(am) * 50, cy - math.cos(am) * 50), fill=(30, 30, 40, 255), width=5)
    d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=(230, 60, 70, 255))


def phone_small(im, x, y, rot=0, glow=False, shake=0.0, t=0.0):
    p = Image.new('RGBA', (90, 160), (0, 0, 0, 0))
    d = ImageDraw.Draw(p)
    d.rounded_rectangle((0, 0, 89, 159), 16, fill=(30, 30, 40, 255))
    d.rounded_rectangle((6, 8, 83, 151), 12, fill=(120, 190, 255, 255) if glow else (50, 60, 80, 255))
    if shake:
        rot += math.sin(t * 90) * 10 * shake
        x += math.sin(t * 70) * 6 * shake
    if rot:
        p = p.rotate(rot, expand=True, resample=Image.BICUBIC)
    if glow:
        g = Image.new('RGBA', (360, 360), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((60, 60, 300, 300), fill=(120, 180, 255, 90))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)), (int(x - 180), int(y - 180)))
    im.alpha_composite(p, (int(x - p.width / 2), int(y - p.height / 2)))
    if shake:                                   # волны звонка
        d = ImageDraw.Draw(im)
        for k in range(3):
            ph = (t * 3 + k / 3) % 1
            r = 60 + ph * 90
            a = int(255 * (1 - ph) * shake)
            for sgn in (-1, 1):
                d.arc((x - r, y - r, x + r, y + r), 300 if sgn > 0 else 120, 60 if sgn > 0 else 240, fill=(255, 220, 80, a), width=6)


# ------------------------------------------------------------------ UI
def text_c(im, text, cx, y, size, fill=(255, 255, 255, 255), weight='Heavy', stroke=7, stroke_fill=(20, 16, 40, 255), maxw=800, shadow=True):
    f = font(weight, size)
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=f)
    while w > maxw and size > 20:
        size -= 2
        f = font(weight, size)
        w = d.textlength(text, font=f)
    x = cx - w / 2
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x, y + 6), text, font=f, fill=(0, 0, 0, 150))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    d.text((x, y), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return w


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ''
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


SUBS = {
    'I1': 'Я Мисед. Изучаю землян.', 'D1': 'Всё. Завтра встаю ровно в семь.', 'M1': 'Ты поставил пять будильников.',
    'D2': 'А-а! Ты почему не спишь?!', 'D3': 'Это система. Первый будит, второй напоминает, третий — чтоб не уснул…',
    'M3': 'А пятый?', 'D4': 'По пятому я встаю.', 'M4': 'Тогда зачем первые четыре?', 'D5': '…Ты не поймёшь. Это земное.',
    'D6': 'Ещё пять минут…', 'D7': 'Я уже встал…', 'M5': 'Он говорит, что встал. Он лежит.',
    'D9': 'ПОЧЕМУ МЕНЯ НИКТО НЕ РАЗБУДИЛ?!', 'M6': 'Тебя будили пять раз. Ты их все выключил.',
    'M7': 'На моей планете будильник один.', 'D10': 'И вы сразу встаёте?', 'M8': 'Он звенит, пока не встанешь.',
    'D11': 'Это жестоко!', 'M9': 'Это утро.', 'D12': 'Шесть — это новая система.',
    'M10': 'Держи. Будешь знать, сколько проспал.'}


def subtitles(im, t):
    for k, t0 in V.items():
        if k == 'I1' or not (t0 - 0.05 <= t < t0 + D[k] + 0.25):
            continue
        size = 66
        f = font('Heavy', size)
        lines = wrap(SUBS[k], f, 800)
        col = (255, 196, 222, 255) if k[0] == 'M' else (255, 255, 255, 255)
        a = cl((t - t0 + 0.05) / 0.12)
        y0 = 1385 - len(lines) * (size + 10)
        if T['s6'] <= t < T['s7']:                       # в беготне Димон внизу — субтитры наверх
            y0 = 420
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        dy = (1 - eo(a)) * 18
        for i, ln in enumerate(lines):
            text_c(lay, ln, W / 2, y0 + i * (size + 10) + dy, size, fill=col)
        if a < 1:
            lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)


def chip(im, text, cx, y, bg=(40, 30, 70, 230), fg=(255, 255, 255, 255), size=44, pop=1.0):
    f = font('Heavy', size)
    w = ImageDraw.Draw(im).textlength(text, font=f)
    s = max(0.01, pop)
    lay = Image.new('RGBA', (int(w + 70), size + 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, lay.width - 1, lay.height - 1), lay.height // 2, fill=bg)
    d.text((35, 16), text, font=f, fill=fg)
    if s != 1:
        lay = lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))), Image.BICUBIC)
    im.alpha_composite(lay, (int(cx - lay.width / 2), int(y - lay.height / 2)))


def alarm_card(im, t, n_rows, row_t, new_idx=None, a=1.0, y0=420):
    """Экран будильников телефона (крупно, в безопасной зоне)."""
    if a <= 0:
        return
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    x0, x1 = 250, 830
    rows = n_rows
    h = 110 + rows * 96
    d = ImageDraw.Draw(lay)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 14, x1, y0 + h + 14), 44, fill=(0, 0, 0, 120))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    d.rounded_rectangle((x0, y0, x1, y0 + h), 44, fill=(20, 22, 34, 245), outline=(70, 80, 120, 255), width=4)
    d.text((x0 + 40, y0 + 30), 'Будильник', font=font('Heavy', 46), fill=(255, 255, 255, 255))
    times = ['7:00', '7:05', '7:10', '7:15', '7:20', '7:25']
    for i in range(rows):
        k = eo((t - row_t[i]) / 0.25)
        if k <= 0:
            continue
        y = y0 + 110 + i * 96 + (1 - k) * 30
        ra = int(255 * k)
        d.line((x0 + 30, y - 6, x1 - 30, y - 6), fill=(60, 64, 90, ra), width=2)
        col = (255, 220, 90, ra) if i == new_idx else (255, 255, 255, ra)
        d.text((x0 + 40, y + 4), times[i], font=font('Bold', 64), fill=col)
        tx = x1 - 150
        d.rounded_rectangle((tx, y + 18, tx + 100, y + 72), 27, fill=(70, 210, 110, ra))
        d.ellipse((tx + 50, y + 22, tx + 96, y + 68), fill=(255, 255, 255, ra))
    if a < 1:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(lay)


def flash(im, t, t0, dur=0.14, col=(255, 255, 255)):
    k = (t - t0) / dur
    if -1 <= k <= 1:
        a = int(255 * (1 - abs(k)) * 0.9)
        im.alpha_composite(Image.new('RGBA', im.size, col + (a,)))


def zzz(im, t, x, y, t0):
    if t < t0:
        return
    for k in range(3):
        ph = ((t - t0) * 0.7 + k / 3) % 1
        a = int(255 * math.sin(math.pi * ph))
        text_c(im, 'z', x + ph * 80 + k * 10, y - ph * 160, 40 + int(ph * 30), fill=(255, 255, 255, a), stroke=4, shadow=False)


# ------------------------------------------------------------------ персонажи в сценах
def missed_pose(t, ears=(0, 0), arm=None, mouth_idle='smile'):
    m = mouth_open('M', t)
    mouth = 'o' if m == 2 else 'flat' if m == 1 else mouth_idle
    ph = t % 3.7
    blink = 1 if ph < 0.12 else 0
    q = lambda v: round(v * 2) / 2
    p = dict(mouth=mouth, blink=blink, ear_l=q(ears[0]), ear_r=q(ears[1]))
    if arm:
        p['arm'] = arm
    return p


def dimon_mouth(t, idle='smile', talk_big='open'):
    m = mouth_open('D', t)
    return talk_big if m == 2 else 'o' if m == 1 else idle


def missed_in_chair(im, t, light, ears=(0, 0), arm=None, scale=0.44):
    p = missed_pose(t, ears, arm)
    breath = math.sin(t * 2.2) * 3
    put(im, scaled('missed', scale, light, flip=arm == 'reach', **p), CHAIR_X, 1500 + breath)


def missed_at_table(im, t, ears=(0, 0), scale=0.44, arm='mug'):
    p = missed_pose(t, ears, arm)
    breath = math.sin(t * 2.2) * 3
    spr = scaled('missed', scale, 'day', **p)
    put(im, spr, CHAIR_X, 1500 + breath)
    return spr


def dimon_sitting(im, t, light, scale=0.40, y_off=0.0, **p):
    spr = scaled('dimon', scale, light, **p)
    put(im, spr, 260, 1350 + y_off)


def dimon_lying(im, t, scale=0.40, **p):
    spr = scaled('dimon', scale, 'day', rot=82, **p)
    im.alpha_composite(spr, (int(80), int(1215 - spr.height / 2 + math.sin(t * 2) * 3)))


# ------------------------------------------------------------------ сцены
def ufo_sprite():
    u = Image.new('RGBA', (520, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(u)
    d.ellipse((150, 20, 370, 170), fill=(140, 230, 255, 230))
    d.ellipse((190, 40, 260, 90), fill=(230, 255, 255, 200))
    d.ellipse((10, 110, 510, 230), fill=(150, 160, 190, 255))
    d.ellipse((30, 105, 490, 190), fill=(200, 210, 235, 255))
    d.ellipse((170, 180, 350, 250), fill=(90, 100, 130, 255))
    return u


UFO = None


def scene_intro(t):
    global UFO
    if UFO is None:
        UFO = ufo_sprite()
    im = vgrad(W, H, (8, 10, 36), (52, 40, 100))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(11)
    for _ in range(140):
        x, y = rng.integers(0, W), rng.integers(0, 1400)
        tw = 0.5 + 0.5 * math.sin(t * rng.uniform(2, 6) + rng.uniform(0, 6))
        s = rng.choice([2, 2, 3, 4])
        d.ellipse((x, y, x + s, y + s), fill=(255, 255, 255, int(120 + 135 * tw)))
    # дома спального района
    rng = np.random.default_rng(5)
    x = -20
    while x < W:
        w = int(rng.integers(160, 260))
        h = int(rng.integers(300, 560))
        d.rectangle((x, 1560 - h, x + w, 1560), fill=(24, 22, 52, 255))
        for wy in range(1560 - h + 30, 1540, 60):
            for wx in range(x + 22, x + w - 30, 50):
                if rng.random() < 0.35:
                    d.rectangle((wx, wy, wx + 24, wy + 30), fill=(255, 210, 110, 255))
        x += w + 10
    d.rectangle((0, 1560, W, H), fill=(30, 34, 50, 255))
    # НЛО
    k_in = eo(t / 1.2)
    k_out = eio((t - 2.8) / 0.6)
    ux = lerp(1350, 540, k_in) + math.sin(t * 3) * 6
    uy = lerp(-200, 560, k_in) + math.sin(t * 4) * 8 - k_out * 1000
    # луч
    ba = cl((t - 1.2) / 0.15) * (1 - cl((t - 2.75) / 0.2))
    if ba > 0:
        beam = Image.new('L', (W, H), 0)
        ImageDraw.Draw(beam).polygon([(ux - 90, uy + 90), (ux + 90, uy + 90), (ux + 300, 1580), (ux - 300, 1580)], fill=int(150 * ba))
        beam = beam.filter(ImageFilter.GaussianBlur(14))
        im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), v) for v in (170, 240, 255)] + [beam]))
        for k in range(6):                      # искры в луче
            ph = (t * 0.8 + k / 6) % 1
            sx = ux + math.sin(k * 2.3 + t * 3) * 120 * ph
            sy = lerp(1560, uy + 120, ph)
            d.ellipse((sx - 4, sy - 4, sx + 4, sy + 4), fill=(255, 255, 255, int(220 * ba)))
    # Мисед опускается в луче
    if t >= 1.25:
        k = eo((t - 1.25) / 1.05)
        bottom = lerp(1000, 1640, k)
        nod = 2.3 <= t < 2.65
        p = dict(mouth='o' if mouth_open('M', t) == 2 else 'smile', blink=0, ear_l=0.0, ear_r=0.0)
        if nod:
            p['tilt'] = 6
        spr = scaled('missed', 0.5, 'beam', **p)
        put(im, spr, 540, bottom)
        if t >= 2.3:                              # пыль при касании
            a = 1 - cl((t - 2.3) / 0.6)
            for s in (-1, 1):
                for j in range(4):
                    px = 540 + s * (90 + j * 40) * eo((t - 2.3) / 0.6)
                    d.ellipse((px - 20, 1540 - j * 8, px + 20, 1572 - j * 8), fill=(200, 210, 240, int(120 * a)))
    im.alpha_composite(UFO, (int(ux - 260), int(uy - 130)))
    d = ImageDraw.Draw(im)
    for k in range(7):                            # огоньки по ободу
        a = k / 7 * 2 * math.pi + t * 4
        lx, ly = ux + math.cos(a) * 220, uy + 20 + math.sin(a) * 30
        if math.sin(a) > -0.2:
            on = int(t * 8 + k) % 2
            d.ellipse((lx - 9, ly - 9, lx + 9, ly + 9), fill=(255, 230, 90, 255) if on else (255, 120, 120, 255))
    # логотип и название серии
    if t >= T['logo']:
        s = spring(t - T['logo'])
        lay = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
        text_c(lay, 'МИСЕД НА ЗЕМЛЕ', W / 2, 30, 96, fill=(255, 255, 255, 255), stroke=9, stroke_fill=(90, 40, 160, 255))
        chip(lay, 'БУДИЛЬНИК', W / 2, 220, bg=(255, 210, 70, 255), fg=(40, 20, 60, 255), size=50,
             pop=spring(t - T['logo'] - 0.15))
        lay = lay.resize((max(1, int(W * s)), max(1, int(420 * s))), Image.BICUBIC)
        im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(330 + 210 - lay.height / 2 - 210 * s + 210 * s - 0)))
    flash(im, t, T['intro_end'] - 0.07, 0.12)
    return im


def scene_night(t, part):
    """s1, s2, s3, s7, s8 — ночная комната."""
    im = room('night').copy()
    dark = part == 's1' or (part == 's2' and t < T['eyes'] + 0.6)
    reveal = cl((t - T['eyes'] - 0.6) / 0.5) if part == 's2' else 1.0
    armchair_back(im, 'night')
    ears = (0, 0)
    if part in ('s7', 's8'):
        k = eio((t - T['ears']) / 0.6)
        ears = (-k, -k)
        if part == 's8':
            ears = (lerp(-1, 0, eio((t - T['s8']) / 0.5)),) * 2
    arm = 'reach' if part == 's8' and t >= T['s8'] + 0.1 else None
    if dark:
        missed_in_chair(im, t, 'dark', ears)
        # блики глаз в темноте
        sc = 0.44
        blink = T['eyes'] + 0.25 <= t < T['eyes'] + 0.37
        if not blink:
            d = ImageDraw.Draw(im)
            for sgn in (-1, 1):
                ex = CHAIR_X + sgn * 84 * sc
                ey = 1500 - (1500 - 548) * sc + math.sin(t * 2.2) * 3
                g = Image.new('RGBA', (60, 60), (0, 0, 0, 0))
                ImageDraw.Draw(g).ellipse((15, 15, 45, 45), fill=(200, 220, 255, 120))
                im.alpha_composite(g.filter(ImageFilter.GaussianBlur(6)), (int(ex - 30), int(ey - 30)))
                d.ellipse((ex - 4, ey - 8, ex + 4, ey), fill=(255, 255, 255, 255))
    else:
        if reveal < 1:
            missed_in_chair(im, t, 'dark', ears)
            lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
            missed_in_chair(lay, t, 'night', ears)
            lay.putalpha(lay.getchannel('A').point(lambda v: int(v * reveal)))
            im.alpha_composite(lay)
        else:
            if part == 's2' and T['blink'] <= t < T['blink'] + 0.14:
                p = missed_pose(t, ears)
                p['blink'] = 1
                put(im, scaled('missed', 0.44, 'night', **p), CHAIR_X, 1500 + math.sin(t * 2.2) * 3)
            else:
                missed_in_chair(im, t, 'night', ears, arm)
    armchair_front(im, 'night')
    # Димон в кровати с телефоном
    pillow(im, 'night', 150, 1150)
    y_off = 0.0
    p = dict(arms='phone', eyes='open', mouth=dimon_mouth(t), brows='')
    if part == 's2' and t >= T['jump']:
        k = t - T['jump']
        y_off = -abs(math.sin(min(k, 0.5) * math.pi / 0.5)) * 120 if k < 0.5 else 0
        p.update(eyes='wide', arms='up' if k < 1.2 else 'phone', mouth=dimon_mouth(t, 'o', 'shout'), brows='shout')
    if part == 's3':
        if t < ROLE_T[4] + 0.6:
            p.update(arms='count', fingers=min(4, max(1, sum(t >= x for x in ROLE_T[:4]))), mouth=dimon_mouth(t, 'smile'))
        elif t >= V['D5']:
            p.update(arms='down', mouth=dimon_mouth(t, 'flat'), brows='plead', look=-0.3)
    if part == 's8':
        if t >= T['gift']:
            p.update(eyes='wide', mouth='open', arms='up')
        if t >= T['gift'] + 1.2:
            p.update(eyes='half', mouth='smile', arms='phone')
        if t >= T['snore2'] - 0.4:
            p.update(eyes='closed', mouth='sleep')
    dimon_sitting(im, t, 'night', y_off=y_off, **p)
    if p['arms'] == 'phone':
        phone_small(im, 260, 1205 + y_off, glow=True)
    blanket(im, 'night', 1330)
    if part == 's8':
        zzz(im, t, 330, 980, T['snore2'] - 0.3)
    return im


def scene_morning(t, part):
    """s4, s5, s6 — утро."""
    im = room('day').copy()
    # часы на стене
    if part == 's4':
        hh, mm = 7, min(20, int((t - T['s4']) / (T['off'] - T['s4']) * 20))
    elif part == 's5':
        k = eio((t - T['clock']) / 0.8)
        tot = lerp(7 * 60 + 20, 9 * 60 + 40, k)
        hh, mm = int(tot // 60), tot % 60
    else:
        hh, mm = 9, 41 + int((t - T['s6']) / 6)
    wall_clock(im, hh, mm, 'day')
    table_back(im)
    missed_at_table(im, t, ears=(0, 1 if any(r <= t < r + 0.22 for r in T['ring']) else 0))
    # Мисед держит кружку
    mug(im, CHAIR_X + 72 * 0.44 + 10, 1500 - (1500 - 1240) * 0.44 + math.sin(t * 2.2) * 3, t)
    table_front(im)
    # тумбочка и телефон
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((520, 1360, 660, 1560), 12, fill=(180, 120, 80, 255))
    ring_len = [0.75, 0.6, 0.5, 0.8, 0.6]
    shake = 0.0
    for r, L in zip(T['ring'], ring_len):
        if r <= t < r + L:
            shake = 1.0
    if part == 's4':
        phone_small(im, 590, 1330, rot=90, shake=shake, t=t, glow=shake > 0)
    else:
        phone_small(im, 590, 1330, rot=90)
    if part in ('s4',):
        pi = T['pillow']
        if t < pi - 0.45:
            pillow(im, 'day', 150, 1200)
        elif t < pi + 0.05:                         # подушка летит в телефон
            k = cl((t - pi + 0.45) / 0.5)
            pillow(im, 'day', lerp(150, 590, k), lerp(1200, 1310, k) - math.sin(k * math.pi) * 260, rot=k * 540)
        else:
            pillow(im, 'day', 600, 1400 if t < pi + 0.3 else 1500, rot=20)
        # Димон лежит
        p = dict(arms='down', eyes='closed', mouth=dimon_mouth(t, 'sleep', 'o'))
        if T['ring'][3] - 0.05 <= t < T['off']:
            p.update(arms='plead', eyes='half', brows='plead', mouth='o')
        dimon_lying(im, t, **p)
        blanket(im, 'day', 1310)
        zzz(im, t, 300, 1100, T['snore1'] - 0.2)
        # счётчик звонков
        n = sum(t >= r for r in T['ring'])
        if n:
            last = T['ring'][n - 1]
            chip(im, f'ЗВОНОК {n}/5', W / 2, 300, bg=(230, 60, 70, 240), size=48, pop=spring(t - last, 3, 0.4) if t - last < 1 else 1)
        if T['ring'][3] <= t < T['off'] + 0.1:     # мысль: «ну ещё один…»
            k = spring(t - T['ring'][3], 3, 0.5)
            bub = Image.new('RGBA', (460, 170), (0, 0, 0, 0))
            bd = ImageDraw.Draw(bub)
            bd.rounded_rectangle((0, 0, 459, 130), 60, fill=(255, 255, 255, 240))
            bd.ellipse((60, 130, 95, 160), fill=(255, 255, 255, 240))
            bd.text((40, 32), 'ну ещё один…', font=font('Heavy', 50), fill=(40, 30, 60, 255))
            bub = bub.resize((max(1, int(460 * k)), max(1, int(170 * k))), Image.BICUBIC)
            im.alpha_composite(bub, (180, int(930 - bub.height)))
    elif part == 's5':
        pillow(im, 'day', 600, 1500, rot=20)
        if t < T['wake']:
            dimon_lying(im, t, arms='down', eyes='closed', mouth='sleep')
            blanket(im, 'day', 1310)
            zzz(im, t, 300, 1100, T['snore1'] - 0.2)
        else:
            k = t - T['wake']
            y_off = -abs(math.sin(min(k, 0.4) * math.pi / 0.4)) * 90 if k < 0.4 else 0
            p = dict(arms='up' if k < 2.2 else 'down', eyes='wide', mouth=dimon_mouth(t, 'o', 'shout'), brows='shout')
            dimon_sitting(im, t, 'day', y_off=y_off, **p)
            blanket(im, 'day', 1330)
        # крупные часы
        k = eio((t - T['clock']) / 0.8)
        tot = lerp(7 * 60 + 20, 9 * 60 + 40, k)
        txt = f'{int(tot // 60)}:{int(tot % 60):02d}'
        pop = 1 + 0.12 * math.exp(-6 * max(0, t - T['wake'])) * (t >= T['wake'])
        col = (255, 70, 80, 255) if t >= T['wake'] else (255, 255, 255, 255)
        lay = Image.new('RGBA', (W, 260), (0, 0, 0, 0))
        text_c(lay, txt, W / 2, 20, 190, fill=col, stroke=10, stroke_fill=(30, 20, 50, 255), weight='Heavy')
        if pop != 1:
            lay = lay.resize((int(W * pop), int(260 * pop)), Image.BICUBIC)
        im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(270 - (lay.height - 260) / 2)))
    else:  # s6 — беготня
        pillow(im, 'day', 600, 1500, rot=20)
        blanket(im, 'day', 1330)
        u = t - T['s6']
        period = 2.6
        ph = (u / period) % 1
        x = 140 + 380 * (0.5 - 0.5 * math.cos(2 * math.pi * ph))
        going_right = ph < 0.5
        bob = abs(math.sin(u * 2 * math.pi * 2.2)) * 26
        legs = scaled('legs', 0.36, 'day', flip=not going_right, phase=round((u * 2.2) % 1 * 8) / 8)
        talking = mouth_open('D', t)
        p = dict(arms='down', eyes='wide', mouth=dimon_mouth(t, 'brush', 'open') if talking else 'brush', sock=True, brows='shout')
        up = scaled('dimon', 0.36, 'day', flip=not going_right, **p)
        bx = x + 60
        put(im, legs, bx, 1790 - bob * 0.2)
        put(im, up, bx, 1790 - legs.height + 30 - bob)
        d = ImageDraw.Draw(im)
        for k in range(4):                          # линии скорости
            yy = 1450 + k * 70
            xx = bx - (1 if going_right else -1) * (170 + k * 20)
            d.line((xx, yy, xx - (1 if going_right else -1) * 90, yy), fill=(255, 255, 255, 180), width=6)
    return im


def camera(im, t):
    """Наезды и тряска в мировых координатах."""
    zoom, fx, fy = 1.0, W / 2, H / 2
    sx = sy = 0.0
    # s3: наезд на Миседа на «Тогда зачем первые четыре?»
    if T['s3'] <= t < T['s4']:
        k = eio((t - T['pause']) / 0.45) * (1 - eio((t - V['D5'] + 0.1) / 0.35))
        zoom, fx, fy = lerp(1, 2.0, k), lerp(W / 2, CHAIR_X - 20, k), lerp(H / 2, 1180, k)
    # s4: лёгкий наезд на Миседа на «Он говорит, что встал. Он лежит.»
    if T['s4'] <= t < T['s5']:
        k = eio((t - V['M5']) / 0.4) * (1 - eio((t - V['M5'] - D['M5']) / 0.35))
        zoom, fx, fy = lerp(1, 1.5, k), lerp(W / 2, CHAIR_X - 60, k), lerp(H / 2, 1150, k)
    # s5: тряска на пробуждение
    if T['wake'] <= t < T['wake'] + 0.5:
        a = (1 - (t - T['wake']) / 0.5) * 22
        sx, sy = math.sin(t * 90) * a, math.cos(t * 77) * a
    if zoom == 1 and not sx and not sy:
        return im
    cw, ch = W / zoom, H / zoom
    x0 = min(max(0, fx - cw / 2), W - cw) + sx
    y0 = min(max(0, fy - ch / 2), H - ch) + sy
    return im.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)


def overlay_ui(im, t):
    """Экранные слои (после камеры): хук, будильники, плашки системы, подарок, титр."""
    if T['s1'] <= t < T['s2'] + 2.0:                    # хук
        a = cl((t - T['s1']) / 0.2) * (1 - cl((t - T['s2'] - 1.6) / 0.4))
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        text_c(lay, 'ПРИШЕЛЕЦ ВПЕРВЫЕ ВИДИТ,', W / 2, 250, 58, fill=(255, 220, 90, 255))
        text_c(lay, 'КАК ЗЕМЛЯНЕ ПРОСЫПАЮТСЯ', W / 2, 322, 58, fill=(255, 220, 90, 255))
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)
    if T['s1'] <= t < T['s2'] + 0.3:                    # будильники ставятся
        a = cl((t - T['s1'] - 0.05) / 0.2) * (1 - cl((t - T['s2']) / 0.3))
        alarm_card(im, t, 5, T['alarms_set'], a=a, y0=430)
    if T['s7'] <= t < T['s8'] + 0.3:
        a = cl((t - T['s7']) / 0.2) * (1 - cl((t - T['s8']) / 0.3))
        rows_t = [T['s7'] - 1] * 5 + [T['alarm6']]
        alarm_card(im, t, 6, rows_t, new_idx=5, a=a, y0=330)
    if T['s3'] <= t < T['s4']:                         # плашки «системы»
        labels = ['1 · БУДИТ', '2 · НАПОМИНАЕТ', '3 · ЧТОБ НЕ УСНУЛ', '4 · НА ВСЯКИЙ СЛУЧАЙ', '5 · ПО НЕМУ ВСТАЮ']
        fade = 1 - cl((t - V['D5'] - D['D5'] + 0.2) / 0.3)
        zk = eio((t - T['pause']) / 0.45) * (1 - eio((t - V['D5'] + 0.1) / 0.35))
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        for i, (lab, t0) in enumerate(zip(labels, ROLE_T)):
            if t < t0:
                continue
            pop = spring(t - t0, 3, 0.45)
            y = 280 + i * 96
            gone = i < 4 and t >= CROSS_T + i * 0.12
            bg = (90, 90, 110, 230) if gone else ((70, 200, 110, 240) if i == 4 else (40, 30, 70, 235))
            chip(lay, lab, W / 2, y, bg=bg, size=42, pop=pop)
            if gone:
                k = eo((t - CROSS_T - i * 0.12) / 0.2)
                ImageDraw.Draw(lay).line((W / 2 - 230, y, W / 2 - 230 + 460 * k, y), fill=(240, 60, 70, 255), width=10)
        a = fade * (1 - 0.0 * zk)
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)
    if T['s8'] <= t:                                  # подарок
        gt = T['gift']
        if gt - 0.5 <= t < gt + 0.1:
            k = eio((t - gt + 0.5) / 0.6)
            x, y = lerp(CHAIR_X - 200, 300, k), lerp(1100, 1130, k) - math.sin(k * math.pi) * 380
            size = int(lerp(140, 230, math.sin(k * math.pi)))
            g = lottie.frame(GIFT, t - gt + 0.5, size=size)
            im.alpha_composite(g, (int(x - size / 2), int(y - size / 2)))
        if t >= gt:                                    # тост на экране
            k = spring(t - gt, 2.5, 0.5)
            lay = Image.new('RGBA', (700, 200), (0, 0, 0, 0))
            dd = ImageDraw.Draw(lay)
            dd.rounded_rectangle((0, 0, 699, 199), 50, fill=(25, 25, 40, 240), outline=(255, 210, 90, 255), width=4)
            g = lottie.frame(GIFT, t - gt, size=170)
            lay.alpha_composite(g, (15, 15))
            dd.text((200, 40), 'Мисед подарил', font=font('Bold', 40), fill=(220, 220, 240, 255))
            dd.text((200, 100), 'Swiss Watch', font=font('Heavy', 54), fill=(255, 215, 90, 255))
            lay = lay.resize((max(1, int(700 * k)), max(1, int(200 * k))), Image.BICUBIC)
            im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(420 - lay.height / 2)))
            for j in range(26):                       # конфетти
                u = t - gt
                if u > 2.5:
                    break
                rr = np.random.default_rng(j)
                ang = rr.uniform(0, 2 * math.pi)
                sp = rr.uniform(300, 700)
                cx = W / 2 + math.cos(ang) * sp * u
                cy = 420 + math.sin(ang) * sp * u + 500 * u * u
                c = [(255, 210, 70), (120, 220, 255), (255, 120, 160), (140, 240, 140)][j % 4]
                ImageDraw.Draw(im).rectangle((cx - 8, cy - 5, cx + 8, cy + 5), fill=c + (int(255 * cl(1 - u / 2.5)),))
        if t >= V['M10'] + D['M10'] - 0.2:            # титр
            s = spring(t - V['M10'] - D['M10'] + 0.2, 2.2, 0.5)
            lay = Image.new('RGBA', (W, 160), (0, 0, 0, 0))
            text_c(lay, 'МИСЕД НА ЗЕМЛЕ', W / 2, 20, 92, fill=(255, 255, 255, 255), stroke=9, stroke_fill=(90, 40, 160, 255))
            lay = lay.resize((max(1, int(W * s)), max(1, int(160 * s))), Image.BICUBIC)
            im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(700 - lay.height / 2)))


GIFT = G.original_file('Swiss Watch', 'tgs')


def scene_of(t):
    order = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8']
    s = None
    for k in order:
        if t >= T[k]:
            s = k
    return s


def render_at(t):
    if t < T['intro_end']:
        return scene_intro(t).convert('RGB')
    s = scene_of(t)
    if s in ('s4', 's5', 's6'):
        im = scene_morning(t, s)
    else:
        im = scene_night(t, s)
    im = camera(im, t)
    overlay_ui(im, t)
    subtitles(im, t)
    if s in ('s3', 's4', 's5', 's6', 's7', 's8') and abs(t - T[s]) < 0.15:
        flash(im, t, T[s], 0.12)
    if s == 's1':
        flash(im, t, T['s1'] - 0.0, 0.14)
    return im.convert('RGB')


def _frame(i):
    return render_at(i / FPS).tobytes()


def build(name):
    out = HERE / 'build' / name
    n = int(DUR * FPS)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                            '-r', str(FPS), '-i', '-', '-i', str(HERE / 'build' / 'mix.wav'), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k',
                            '-shortest', '-movflags', '+faststart', str(out)], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for i, b in enumerate(pool.imap(_frame, range(n), chunksize=6)):
            enc.stdin.write(b)
            if i % (n // 10) == 0:
                print(f'PROGRESS {round(100 * i / n)}%', flush=True)
    enc.stdin.close()
    enc.wait()
    print('OK', out)


def prewarm(step=4):
    """Рисуем все позы по кадрам с шагом (позы — в кэш на диск), параллельно."""
    n = int(DUR * FPS)
    with Pool(4) as pool:
        for _ in pool.imap_unordered(_frame, range(0, n, step), chunksize=4):
            pass


if __name__ == '__main__':
    if sys.argv[1] == '--frames':
        rev = HERE / 'build' / 'review'
        rev.mkdir(parents=True, exist_ok=True)
        for ts in sys.argv[2].split(','):
            render_at(float(ts)).save(rev / f'frame_{float(ts):05.2f}.jpg', quality=90)
        print('frames OK')
    elif sys.argv[1] == '--prewarm':
        prewarm()
        print('prewarm OK')
    elif sys.argv[1] == '--build':
        build(sys.argv[2])
