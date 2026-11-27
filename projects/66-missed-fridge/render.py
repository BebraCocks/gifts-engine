"""Рендер серии «Холодильник» (всё кодом). Кадр — чистая функция времени.

    python -B render.py --frames 2.8,6,10,15,22,28.5,30.5,40,45,49,56,58.5
    python -B render.py --prewarm
    python -B render.py --build missed_fridge_v1.mp4
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
sys.path.append(str(ROOT / 'projects' / '65-missed-alien'))    # art.py — общие персонажи сериала
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import art  # noqa: E402
import events as E  # noqa: E402
from timeline import T, V, D, DUR  # noqa: E402

W, H, FPS = 1080, 1920, 60
FD = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
SPR = HERE / 'build' / 'sprites'
STAS = dict(hood=[240, 150, 60], hair=[200, 160, 90], glasses=True)
GIFT = G.original_file('Homemade Cake', 'tgs')
FRIDGE = (60, 560, 420, 1580)          # x0, y0, x1, y1
FREEZER_Y = 860                        # граница морозилки
TABLE_X = 840


# ------------------------------------------------------------------ утилиты
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


def vgrad(w, h, top, bot):
    k = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float) * (1 - k) + np.array(bot, float) * k
    return Image.fromarray(np.repeat(a, w, 1).astype(np.uint8), 'RGB').convert('RGBA')


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
        if (k[0] in 'MIO') == (who == 'M') and t0 <= t < t0 + D[k]:
            return k
    return None


def mouth_open(who, t):
    if not speaking(who, t):
        return 0
    i = int(t * FPS)
    v = ENV[i] if i < len(ENV) else 0
    return 2 if v > 0.22 else 1 if v > 0.08 else 0


# ------------------------------------------------------------------ спрайты (кэш на диске)
@functools.lru_cache(256)
def _sprite(kind, pj):
    p = json.loads(pj)
    path = SPR / (kind + '_' + hashlib.md5(pj.encode()).hexdigest()[:12] + '.png')
    if path.exists():
        return Image.open(path).convert('RGBA')
    SPR.mkdir(parents=True, exist_ok=True)
    im = art.missed(p) if kind == 'missed' else art.dimon(p) if kind == 'human' else art.dimon_legs(**p)
    tmp = path.with_suffix(f'.{id(im)}.png')
    im.save(tmp)
    tmp.replace(path)
    return im


def relight(im, light):
    if light == 'day':
        return im
    a = np.asarray(im, np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    m = Image.fromarray(a[..., 3].astype(np.uint8))
    inner = np.asarray(m.filter(ImageFilter.MinFilter(9)), np.float32) / 255
    edge = np.clip(a[..., 3] / 255 - inner, 0, 1)
    if light == 'night':
        rgb = rgb * np.array([0.62, 0.66, 0.86])
        rim = edge * np.clip(np.linspace(-0.6, 1.4, a.shape[1]), 0, 1)[None, :]   # свет справа (окно)
        rgb = rgb + rim[..., None] * np.array([50, 60, 90])
    elif light == 'fridge':                                # яркий холодный свет из холодильника слева
        grad = np.clip(np.linspace(1.15, 0.7, a.shape[1]), 0, 2)[None, :, None]
        rgb = rgb * np.array([0.95, 0.97, 1.0]) * grad
        rim = edge * np.clip(np.linspace(1.6, -0.4, a.shape[1]), 0, 1)[None, :]
        rgb = rgb + rim[..., None] * np.array([120, 130, 140])
    elif light == 'beam':
        rgb = rgb * np.array([0.92, 0.96, 1.0]) + np.array([10, 18, 30])
        al = al * np.clip(np.linspace(1, 0, a.shape[0]) / 0.35, 0, 1)[:, None, None]
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), 'RGBA')


@functools.lru_cache(512)
def _scaled(kind, pj, scale, light, flip):
    im = _sprite(kind, pj)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    return relight(im, light)


def scaled(kind, scale, light='night', flip=False, **p):
    return _scaled(kind, json.dumps(p, sort_keys=True), round(scale, 3), light, flip)


def put(im, spr, cx, bottom):
    im.alpha_composite(spr, (int(cx - spr.width / 2), int(bottom - spr.height)))


# ------------------------------------------------------------------ текст / UI
def text_c(im, text, cx, y, size, fill=(255, 255, 255, 255), weight='Heavy', stroke=7, stroke_fill=(20, 16, 40, 255),
           maxw=800, shadow=True):
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


def wrap(text, f, maxw):
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    lines, cur = [], ''
    for w in text.split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def chip(im, text, cx, y, bg=(40, 30, 70, 235), fg=(255, 255, 255, 255), size=44, pop=1.0, outline=None):
    f = font('Heavy', size)
    w = ImageDraw.Draw(im).textlength(text, font=f)
    lay = Image.new('RGBA', (int(w + 70), size + 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((0, 0, lay.width - 1, lay.height - 1), lay.height // 2, fill=bg, outline=outline,
                        width=4 if outline else 0)
    d.text((35, 16), text, font=f, fill=fg)
    s = max(0.01, pop)
    if s != 1:
        lay = lay.resize((max(1, int(lay.width * s)), max(1, int(lay.height * s))), Image.BICUBIC)
    im.alpha_composite(lay, (int(cx - lay.width / 2), int(y - lay.height / 2)))


SUBS = {
    'M1': 'Объект: Стас. Двадцать три года. Голодный.', 'S1': 'Есть нечего.', 'M2': 'Холодильник полный.',
    'S2': 'Ну полный. Но есть-то нечего.', 'M3': 'Записываю: полный — значит пустой.',
    'M4': 'Ты открывал его минуту назад.', 'S3': 'Ну мало ли. Вдруг что-то появилось.',
    'M5': 'А кто должен был положить?', 'S4': '…Никто.', 'S5': 'О! Пельмени!', 'M6': 'Они лежали там все шесть раз.',
    'S6': 'Не, варить долго. Закажу доставку.', 'M7': 'Сколько ждать?', 'S7': 'Час.',
    'M8': 'Пельмени варятся десять минут.', 'S8': '…Зато у плиты стоять не надо.',
    'M9': 'Ты простоял у холодильника двадцать.', 'M10': 'Держи. Этот тортик готовить не нужно.',
    'S9': 'О, тортик! …А его можно съесть?', 'M11': 'Нет.', 'O1': 'Стас изучен. Следующий объект — Артём.'}


def subtitles(im, t):
    for k, t0 in V.items():
        if k not in SUBS or not (t0 - 0.05 <= t < t0 + D[k] + 0.25):
            continue
        size = 66
        lines = wrap(SUBS[k], font('Heavy', size), 800)
        col = (255, 196, 222, 255) if k[0] in 'MO' else (255, 255, 255, 255)
        a = cl((t - t0 + 0.05) / 0.12)
        y0 = 1385 - len(lines) * (size + 10)
        if k == 'O1':
            y0 = 1120
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        for i, ln in enumerate(lines):
            text_c(lay, ln, W / 2, y0 + i * (size + 10) + (1 - eo(a)) * 18, size, fill=col)
        if a < 1:
            lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)


def flash(im, t, t0, dur=0.12, col=(255, 255, 255), k=0.9):
    u = (t - t0) / dur
    if -1 <= u <= 1:
        im.alpha_composite(Image.new('RGBA', im.size, col + (int(255 * (1 - abs(u)) * k),)))


# ------------------------------------------------------------------ кухня
@functools.lru_cache(2)
def kitchen():
    im = vgrad(W, H, (24, 28, 56), (14, 16, 34))
    d = ImageDraw.Draw(im)
    for y in range(140, 1100, 64):                       # кафельный фартук
        for x in range(440, W, 64):
            d.rectangle((x + 2, y + 2, x + 60, y + 60), outline=(34, 40, 74, 255), width=2)
    # окно справа с луной
    d.rectangle((640, 250, 1000, 640), fill=(30, 44, 96, 255), outline=(44, 40, 60, 255), width=18)
    d.line((820, 250, 820, 640), fill=(44, 40, 60, 255), width=12)
    d.ellipse((880, 300, 960, 380), fill=(250, 245, 220, 255))
    rng = np.random.default_rng(4)
    for _ in range(18):
        x, y = rng.integers(650, 990), rng.integers(260, 630)
        d.ellipse((x, y, x + 2, y + 2), fill=(230, 235, 255, 255))
    # полка с банками и часы
    d.rectangle((450, 700, 620, 716), fill=(70, 56, 90, 255))
    for i, c in enumerate([(120, 70, 90), (70, 100, 120), (110, 100, 60)]):
        d.rounded_rectangle((462 + i * 52, 630, 500 + i * 52, 700), 8, fill=c + (255,))
    # столешница и шкафчики (между холодильником и столом)
    d.rectangle((440, 1180, 660, 1560), fill=(40, 40, 70, 255))
    d.rectangle((430, 1160, 670, 1190), fill=(60, 58, 96, 255))
    d.rectangle((455, 1220, 645, 1530), outline=(52, 52, 86, 255), width=4)
    d.ellipse((470, 1100, 560, 1170), fill=(90, 90, 120, 255))      # чайник
    d.rectangle((550, 1120, 590, 1135), fill=(90, 90, 120, 255))
    # пол
    d.rectangle((0, 1560, W, H), fill=(26, 24, 44, 255))
    for x in range(-200, W + 200, 120):
        d.line((x, 1560, x - 160, H), fill=(34, 32, 56, 255), width=3)
    # лунный свет из окна
    beam = Image.new('L', (W, H), 0)
    ImageDraw.Draw(beam).polygon([(640, 250), (1000, 250), (1080, 1300), (520, 1700)], fill=45)
    im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), v) for v in (170, 190, 255)] + [beam.filter(ImageFilter.GaussianBlur(40))]))
    return im


def fridge_body(im):
    x0, y0, x1, y1 = FRIDGE
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((x0 - 8, y0 - 8, x1 + 8, y1), 34, fill=(150, 160, 190, 255))


@functools.lru_cache(2)
def fridge_inside(freezer=False):
    """Внутренность: полки с продуктами (и морозилка с пельменями)."""
    x0, y0, x1, y1 = FRIDGE
    w, h = x1 - x0, y1 - y0
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if freezer:
        fh = FREEZER_Y - y0
        d.rounded_rectangle((8, 8, w - 8, fh - 4), 20, fill=(200, 230, 255, 255))
        for k in range(5):                                   # иней
            d.line((20, 20 + k * 50, w - 20, 30 + k * 50), fill=(230, 245, 255, 255), width=3)
        # пачка пельменей
        d.rounded_rectangle((40, 90, 320, 260), 18, fill=(250, 250, 255, 255), outline=(60, 110, 220, 255), width=6)
        d.text((62, 132), 'ПЕЛЬМЕНИ', font=font('Heavy', 40), fill=(40, 80, 200, 255))
        for k in range(4):
            d.ellipse((95 + k * 46, 190, 135 + k * 46, 230), fill=(245, 230, 200, 255), outline=(200, 170, 120, 255), width=3)
        return im
    top = FREEZER_Y - y0 + 10
    d.rounded_rectangle((8, top, w - 8, h - 8), 20, fill=(248, 248, 236, 255))
    shelves = [top + 230, top + 440, top + 640]
    for y in shelves:
        d.rectangle((14, y, w - 14, y + 10), fill=(200, 215, 230, 255))
    # продукты
    sy = shelves[0]
    d.rectangle((40, sy - 150, 100, sy), fill=(255, 255, 255, 255), outline=(80, 140, 220, 255), width=4)   # молоко
    d.polygon([(40, sy - 150), (70, sy - 185), (100, sy - 150)], fill=(80, 140, 220, 255))
    d.polygon([(130, sy), (230, sy), (230, sy - 70)], fill=(250, 210, 70, 255))                           # сыр
    for k in range(3):
        d.ellipse((150 + k * 22, sy - 40, 162 + k * 22, sy - 28), fill=(230, 180, 40, 255))
    d.rounded_rectangle((250, sy - 120, 320, sy), 12, fill=(200, 60, 60, 255))                            # кетчуп
    sy = shelves[1]
    for k in range(6):                                                                                      # яйца
        d.ellipse((30 + k * 32, sy - 50, 60 + k * 32, sy - 6), fill=(255, 246, 230, 255), outline=(220, 200, 170, 255), width=2)
    d.rounded_rectangle((235, sy - 90, 330, sy), 16, fill=(240, 130, 140, 255))                            # колбаса
    d.ellipse((235, sy - 90, 275, sy), fill=(250, 180, 180, 255))
    sy = shelves[2]
    for k, c in enumerate([(230, 60, 50), (240, 80, 60), (90, 190, 80)]):                                  # помидоры, огурец
        d.ellipse((30 + k * 60, sy - 60, 85 + k * 60, sy - 5), fill=c + (255,))
    d.rounded_rectangle((210, sy - 160, 260, sy), 10, fill=(120, 200, 120, 255))                           # бутылка
    d.rounded_rectangle((270, sy - 110, 330, sy), 10, fill=(255, 220, 120, 255))                           # банка
    d.rounded_rectangle((30, shelves[2] + 30, w - 30, h - 30), 20, fill=(220, 240, 220, 255))             # ящик для овощей
    return im


def fridge(im, t, light_k=0.0):
    """Дверцы: основная (по событиям DOOR) и морозилка (FREEZER). Возвращает степень открытия основной."""
    x0, y0, x1, y1 = FRIDGE
    open_k = 0.0
    for a, b in E.DOOR:
        if a - 0.01 <= t < b + 0.3:
            open_k = eo((t - a) / 0.3) * (1 - eio((t - b) / 0.25))
    fz_k = 0.0
    a, b = E.FREEZER
    if a - 0.01 <= t < b + 0.3:
        fz_k = eo((t - a) / 0.3) * (1 - eio((t - b) / 0.25))
    fridge_body(im)
    d = ImageDraw.Draw(im)
    if open_k > 0:
        im.alpha_composite(fridge_inside(False).crop((0, FREEZER_Y - y0, x1 - x0, y1 - y0)), (x0, FREEZER_Y))
    if fz_k > 0:
        im.alpha_composite(fridge_inside(True).crop((0, 0, x1 - x0, FREEZER_Y - y0)), (x0, y0))
    # дверцы: петли слева, открытая дверца — узкая полоска, развёрнутая к камере
    for (ya, yb, k) in ((y0, FREEZER_Y - 6, fz_k), (FREEZER_Y + 6, y1, open_k)):
        wdoor = (x1 - x0) * (1 - k) + 70 * k
        xl = x0 - k * 60
        d.rounded_rectangle((xl, ya, xl + wdoor, yb), 26, fill=(214, 222, 240, 255) if k < 0.5 else (190, 200, 222, 255),
                            outline=(120, 130, 160, 255), width=4)
        if k < 0.5:
            hx = xl + wdoor - 40
            d.rounded_rectangle((hx, ya + 60, hx + 16, ya + 60 + min(240, (yb - ya) * 0.5)), 8, fill=(150, 160, 180, 255))
    # магниты на закрытой дверце
    if open_k < 0.3:
        for (mx, my, c) in ((140, 1000, (240, 90, 90)), (260, 1080, (90, 180, 240)), (180, 1180, (250, 210, 70))):
            d.ellipse((mx - 18, my - 18, mx + 18, my + 18), fill=c + (255,))
        d.rectangle((210, 960, 330, 1050), fill=(255, 255, 240, 255))
        d.text((222, 985), 'ЕДА?', font=font('Heavy', 30), fill=(200, 60, 60, 255))
    return open_k, fz_k


def fridge_light(im, k, freezer=False):
    """Конус света из открытого холодильника + пылинки."""
    if k <= 0:
        return
    x0, y0, x1, y1 = FRIDGE
    beam = Image.new('L', (W, H), 0)
    ya = y0 if freezer else FREEZER_Y
    ImageDraw.Draw(beam).polygon([(x1, ya), (x1, y1), (900, 1920), (1000, ya + 300)], fill=int(110 * k))
    beam = beam.filter(ImageFilter.GaussianBlur(50))
    col = (200, 230, 255) if freezer else (255, 250, 225)
    im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), v) for v in col] + [beam]))


def fog(im, t, t0):
    """Холодный пар из морозилки."""
    u = t - t0
    if u < 0:
        return
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(10):
        ph = (u * 0.5 + k / 10) % 1
        x = FRIDGE[2] - 20 + ph * 260 + math.sin(k * 3 + u * 2) * 30
        y = 640 + k * 22 + ph * 220
        r = 40 + ph * 60
        d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=(220, 240, 255, int(110 * (1 - ph))))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(16)))


def table(im, front=True):
    d = ImageDraw.Draw(im)
    if not front:
        d.rounded_rectangle((TABLE_X - 140, 1080, TABLE_X + 140, 1340), 30, fill=(70, 50, 80, 255))
        return
    d.rounded_rectangle((660, 1330, 1075, 1372), 14, fill=(96, 70, 100, 255))
    d.rectangle((680, 1372, 1055, 1392), fill=(78, 56, 84, 255))
    for x in (690, 1030):
        d.rectangle((x, 1392, x + 24, 1600), fill=(78, 56, 84, 255))


def notebook(im, x, y, t, writing):
    nb = Image.new('RGBA', (120, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(nb)
    d.rounded_rectangle((0, 0, 119, 149), 10, fill=(240, 232, 210, 255), outline=(120, 90, 70, 255), width=4)
    for k in range(5):
        d.line((14, 30 + k * 22, 105, 30 + k * 22), fill=(170, 190, 220, 255), width=2)
    nb = nb.rotate(12, expand=True, resample=Image.BICUBIC)
    im.alpha_composite(nb, (int(x - nb.width / 2), int(y - nb.height / 2)))
    if writing:                                     # ручка ходит туда-сюда
        px = x - 20 + math.sin(t * 14) * 25
        py = y - 10 + math.sin(t * 3) * 15
        ImageDraw.Draw(im).line((px, py, px + 30, py - 60), fill=(40, 40, 60, 255), width=8)


# ------------------------------------------------------------------ персонажи
def missed_pose(t, ears=(0.0, 0.0), arm='mug'):
    m = mouth_open('M', t)
    blink = 1 if (t % 3.9) < 0.12 else 0
    q = lambda v: round(v * 2) / 2
    p = dict(mouth='o' if m == 2 else 'flat' if m == 1 else 'smile', blink=blink, ear_l=q(ears[0]), ear_r=q(ears[1]))
    if arm:
        p['arm'] = arm
    return p


def draw_missed(im, t):
    """Мисед сидит за столом справа с блокнотом. Ухо дёргается, когда открывают холодильник."""
    twitch = any(a <= t < a + 0.22 for a, _ in E.DOOR) or E.FREEZER[0] <= t < E.FREEZER[0] + 0.22
    arm = 'reach' if T['s5'] <= t < T['s6'] else 'mug'
    p = missed_pose(t, (1.0 if twitch else 0.0, 0.0), arm)
    spr = scaled('missed', 0.44, 'night', flip=arm == 'reach', **p)
    put(im, spr, TABLE_X, 1500 + math.sin(t * 2.2) * 3)
    if arm == 'mug':
        writing = E.NOTE[0] <= t < E.NOTE[1]
        notebook(im, TABLE_X + 72 * 0.44 + 12, 1500 - (1500 - 1240) * 0.44 + 10, t, writing)


def stas_pose(t):
    """Поза и место Стаса по времени: (x, bottom, params, legs_phase, legs_amp, flip)."""
    x, flip, legs = 560, False, (0.0, 0.0)
    talk = mouth_open('S', t)
    mouth = {2: 'open', 1: 'o'}.get(talk, 'flat')
    p = dict(arms='down', eyes='open', mouth=mouth, look=-0.8, **STAS)
    if t < T['open1']:
        p.update(look=-0.8, mouth='smile' if not talk else mouth)
    if V['S2'] <= t < V['S2'] + D['S2'] + 0.2 or V['S3'] <= t < V['S3'] + D['S3']:
        p['look'] = 0.8                                          # поворачивается к Миседу
    if V['S1'] - 0.2 <= t < V['S1'] + D['S1'] + 0.3:
        p.update(eyes='half', brows='plead')
    # уходит и возвращается
    a0, a1 = E.AWAY
    b0, b1 = E.BACK
    if a0 <= t < b1:
        if t < a1:
            k = eio((t - a0) / (a1 - a0))
            x = lerp(560, 1300, k)
        elif t < b0:
            x = 1300
        else:
            k = eio((t - b0) / (b1 - b0))
            x = lerp(1300, 560, k)
        legs = ((t * 3) % 1, 1.0)
        flip = t < a1
    if V['S4'] - 0.6 <= t < V['S4'] + D['S4'] + 0.3:
        p.update(eyes='half', mouth=mouth if talk else 'flat', brows='plead', look=0.3)
    # монтаж открытий
    for i, t0 in enumerate(T['opens']):
        if t >= t0:
            p.update([({'arms': 'phone', 'mouth': 'o'}), ({'eyes': 'half', 'mouth': 'sleep'}),
                      ({'arms': 'plead', 'brows': 'plead', 'eyes': 'open'}), ({'arms': 'up', 'eyes': 'wide', 'mouth': mouth if talk else 'open'})][i].items())
    if t >= T['s4']:
        p.update(arms='phone', eyes='half', brows='', look=0.6, mouth=mouth if talk else 'flat')
        p.pop('sock', None)
    if t >= V['S8'] - 0.1:
        p.update(eyes='open', brows='plead')
    if V['M9'] + 0.6 <= t < T['s5']:
        p.update(eyes='wide', mouth='flat', arms='down')
    if t >= T['s5']:
        p.update(arms='down', eyes='open', look=0.6, brows='', mouth=mouth if talk else 'smile')
    if t >= T['gift']:
        p.update(arms='up', eyes='wide', mouth=mouth if talk else 'open')
    if t >= V['S9'] + 1.0:
        p.update(arms='down', eyes='open', mouth=mouth if talk else 'smile')
    if t >= V['M11'] + 0.15:
        p.update(eyes='half', mouth='flat', brows='plead', arms='down')
    return x, p, legs, flip


def draw_stas(im, t, light):
    x, p, (ph, amp), flip = stas_pose(t)
    bob = abs(math.sin(ph * 2 * math.pi)) * 14 if amp else math.sin(t * 2.0) * 2
    legs = scaled('legs', 0.40, light, flip=flip, phase=round(ph * 8) / 8, amp=amp)
    up = scaled('human', 0.40, light, flip=flip, **p)
    put(im, legs, x, 1830 - bob * 0.2)
    put(im, up, x, 1830 - legs.height + 34 - bob)
    if p.get('arms') == 'phone' and t >= T['s4']:
        d = ImageDraw.Draw(im)
        px, py = x, 1830 - legs.height + 34 - bob - up.height * 0.21
        d.rounded_rectangle((px - 20, py - 34, px + 20, py + 34), 8, fill=(30, 30, 40, 255))
        d.rounded_rectangle((px - 15, py - 28, px + 15, py + 28), 6, fill=(120, 190, 255, 255))
    if t >= T['opens'][0] and t < T['opens'][1] and p.get('arms') == 'phone':     # пачка чипсов вместо телефона
        d = ImageDraw.Draw(im)
        px, py = x, 1830 - legs.height + 34 - up.height * 0.21
        d.polygon([(px - 50, py - 60), (px + 50, py - 60), (px + 40, py + 60), (px - 40, py + 60)], fill=(250, 200, 40, 255))
        d.text((px - 38, py - 20), 'ЧИПСЫ', font=font('Heavy', 22), fill=(200, 40, 40, 255))


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


UFO = ufo_sprite()


@functools.lru_cache(1)
def street():
    im = vgrad(W, H, (8, 10, 36), (52, 40, 100))
    d = ImageDraw.Draw(im)
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
    return im


def stars(im, t):
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(11)
    for _ in range(140):
        x, y = rng.integers(0, W), rng.integers(0, 1400)
        tw = 0.5 + 0.5 * math.sin(t * rng.uniform(2, 6) + rng.uniform(0, 6))
        s = int(rng.choice([2, 2, 3, 4]))
        d.ellipse((x, y, x + s, y + s), fill=(255, 255, 255, int(120 + 135 * tw)))


def ufo_lights(im, ux, uy, t):
    d = ImageDraw.Draw(im)
    for k in range(7):
        a = k / 7 * 2 * math.pi + t * 4
        lx, ly = ux + math.cos(a) * 220, uy + 20 + math.sin(a) * 30
        if math.sin(a) > -0.2:
            on = int(t * 8 + k) % 2
            d.ellipse((lx - 9, ly - 9, lx + 9, ly + 9), fill=(255, 230, 90, 255) if on else (255, 120, 120, 255))


def beam_draw(im, ux, uy, a):
    if a <= 0:
        return
    beam = Image.new('L', (W, H), 0)
    ImageDraw.Draw(beam).polygon([(ux - 90, uy + 90), (ux + 90, uy + 90), (ux + 300, 1580), (ux - 300, 1580)], fill=int(150 * a))
    im.alpha_composite(Image.merge('RGBA', [Image.new('L', (W, H), v) for v in (170, 240, 255)] + [beam.filter(ImageFilter.GaussianBlur(14))]))


def scene_intro(t):
    im = street().copy()
    stars(im, t)
    k_in = eo(t / 1.2)
    k_out = eio((t - 2.8) / 0.6)
    ux = lerp(1350, 540, k_in) + math.sin(t * 3) * 6
    uy = lerp(-200, 560, k_in) + math.sin(t * 4) * 8 - k_out * 1000
    beam_draw(im, ux, uy, cl((t - 1.2) / 0.15) * (1 - cl((t - 2.75) / 0.2)))
    if t >= 1.25:
        k = eo((t - 1.25) / 1.05)
        p = dict(mouth='o' if mouth_open('M', t) == 2 else 'smile', blink=0, ear_l=0.0, ear_r=0.0)
        if 2.3 <= t < 2.65:
            p['tilt'] = 6
        put(im, scaled('missed', 0.5, 'beam', **p), 540, lerp(1000, 1640, k))
    im.alpha_composite(UFO, (int(ux - 260), int(uy - 130)))
    ufo_lights(im, ux, uy, t)
    if t >= T['logo']:
        s = spring(t - T['logo'])
        lay = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
        text_c(lay, 'МИСЕД НА ЗЕМЛЕ', W / 2, 30, 96, stroke=9, stroke_fill=(90, 40, 160, 255))
        chip(lay, 'ХОЛОДИЛЬНИК', W / 2, 220, bg=(255, 210, 70, 255), fg=(40, 20, 60, 255), size=50, pop=spring(t - T['logo'] - 0.15))
        lay = lay.resize((max(1, int(W * s)), max(1, int(420 * s))), Image.BICUBIC)
        im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(540 - lay.height / 2)))
    flash(im, t, T['intro_end'] - 0.07)
    return im


def scene_outro(t):
    """Луч забирает Миседа, тизер следующего объекта, НЛО улетает — последний кадр = первый кадр заставки."""
    im = street().copy()
    stars(im, t - T['s6'] + DUR)                  # звёзды продолжают мерцание к началу петли
    u = t - T['s6']
    k_out = eio((t - T['ufo_out']) / 0.6)
    ux = 540 + math.sin(t * 3) * 6 + k_out * 900
    uy = 560 + math.sin(t * 4) * 8 - k_out * 820
    beam_draw(im, ux, uy, cl(u / 0.15) * (1 - cl((t - T['ufo_out'] + 0.3) / 0.2)))
    lift = eio((u - 0.1) / 1.6)
    if lift < 1:
        p = dict(mouth='o' if mouth_open('M', t) == 2 else 'smile', blink=0, ear_l=0.0, ear_r=0.0)
        spr = scaled('missed', lerp(0.5, 0.25, lift), 'beam', **p)
        put(im, spr, 540, lerp(1640, uy + 150, lift))
    im.alpha_composite(UFO, (int(ux - 260), int(uy - 130)))
    ufo_lights(im, ux, uy, t)
    # карточка сканера: «СЛЕДУЮЩИЙ ОБЪЕКТ»
    if T['card'] <= t < T['ufo_out'] + 0.4:
        k = spring(t - T['card'], 2.5, 0.5) * (1 - eio((t - T['ufo_out']) / 0.35))
        card = Image.new('RGBA', (660, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, 659, 519), 40, fill=(10, 20, 30, 235), outline=(90, 255, 200, 255), width=5)
        d.text((40, 30), 'СЛЕДУЮЩИЙ ОБЪЕКТ', font=font('Heavy', 44), fill=(90, 255, 200, 255))
        sil = scaled('human', 0.2, 'day', arms='phone', eyes='open', mouth='flat')
        a = np.asarray(sil).copy()
        a[..., :3] = (20, 60, 60)
        sil = Image.fromarray(a)
        card.alpha_composite(sil, (40, 110))
        d.text((250, 140), 'АРТЁМ, 16', font=font('Heavy', 56), fill=(255, 255, 255, 255))
        d.text((250, 225), '«ещё одно видео —', font=font('Bold', 36), fill=(200, 220, 230, 255))
        d.text((250, 270), 'и сплю»', font=font('Bold', 36), fill=(200, 220, 230, 255))
        yy = 110 + ((t * 300) % 300)                     # бегущая линия сканера
        d.line((30, yy, 630, yy), fill=(90, 255, 200, 140), width=4)
        d.text((40, 440), 'СКАНИРОВАНИЕ…', font=font('Bold', 32), fill=(90, 255, 200, int(140 + 115 * math.sin(t * 10))))
        card = card.resize((max(1, int(660 * k)), max(1, int(520 * k))), Image.BICUBIC)
        im.alpha_composite(card, (int(W / 2 - card.width / 2), int(560 - card.height / 2)))
    flash(im, t, T['s6'], 0.14)
    return im


def scene_kitchen(t):
    im = kitchen().copy()
    table(im, front=False)
    draw_missed(im, t)
    table(im, front=True)
    open_k, fz_k = fridge(im, t)
    lit = max(open_k, fz_k)
    draw_stas(im, t, 'fridge' if lit > 0.5 else 'night')
    fridge_light(im, open_k)
    fridge_light(im, fz_k, freezer=True)
    if fz_k > 0:
        fog(im, t, E.FREEZER[0])
    # блеск продуктов на «Холодильник полный» и «Пельмени»
    for t0, (cx, cy) in ((V['M2'], (240, 1150)), (V['S5'], (240, 730))):
        u = t - t0
        if 0 <= u < 1.2:
            d = ImageDraw.Draw(im)
            for k in range(6):
                a = k / 6 * 2 * math.pi + u * 2
                r = 80 + 60 * u
                x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 1.4
                s = 14 * (1 - u / 1.2)
                d.polygon([(x, y - s * 2), (x + s * 0.5, y), (x, y + s * 2), (x - s * 0.5, y)], fill=(255, 255, 220, 255))
                d.polygon([(x - s * 2, y), (x, y - s * 0.5), (x + s * 2, y), (x, y + s * 0.5)], fill=(255, 255, 220, 255))
    # виньетка
    return im


VIGNETTE = None


def vignette(im):
    global VIGNETTE
    if VIGNETTE is None:
        v = Image.new('L', (W, H), 0)
        ImageDraw.Draw(v).ellipse((-300, -200, W + 300, H + 200), fill=255)
        v = v.filter(ImageFilter.GaussianBlur(160))
        VIGNETTE = Image.new('RGBA', (W, H), (4, 4, 14, 255))
        VIGNETTE.putalpha(Image.eval(v, lambda p: int((255 - p) * 0.55)))
    im.alpha_composite(VIGNETTE)


def camera(im, t):
    """Наезды, панорамы, удары камеры на склейках, тряска."""
    zoom, fx, fy = 1.0, W / 2, H / 2

    def push(t0, t1, z, x, y, a=0.35, b=0.35):
        nonlocal zoom, fx, fy
        k = eio((t - t0) / a) * (1 - eio((t - t1) / b))
        if k > 0:
            zoom, fx, fy = lerp(zoom, z, k), lerp(fx, x, k), lerp(fy, y, k)

    push(V['S1'] - 0.1, V['S1'] + D['S1'], 1.25, 520, 1250)                    # лицо Стаса «Есть нечего»
    push(V['M2'], V['M2'] + D['M2'] + 0.1, 1.7, 260, 1150)                     # полный холодильник
    push(T['note1'], V['M3'] + D['M3'], 1.55, TABLE_X, 1260)                   # Мисед пишет
    push(E.CRICKETS, V['S4'] + D['S4'] + 0.1, 1.45, 560, 1220, a=0.9)          # медленный наезд перед «…Никто»
    push(V['S5'] - 0.1, V['S5'] + D['S5'], 1.5, 300, 900)                      # пельмени!
    push(V['M9'], V['M9'] + D['M9'] + 0.6, 1.4, 700, 1250)                     # «Ты простоял…»
    push(V['M11'] - 0.05, T['s6'], 1.45, 560, 1250, a=0.15)                    # «Нет.» — грустное лицо
    # удар камеры на склейках монтажа
    for t0 in T['opens']:
        if 0 <= t - t0 < 0.3:
            zoom *= 1 + 0.12 * (1 - (t - t0) / 0.3)
    sx = sy = 0.0
    for t0, amp in [(a, 10) for a, _ in E.DOOR] + [(b, 14) for _, b in E.DOOR] + [(E.STAMP, 16)]:
        if 0 <= t - t0 < 0.3:
            k = (1 - (t - t0) / 0.3) * amp
            sx, sy = sx + math.sin(t * 90) * k, sy + math.cos(t * 77) * k
    if zoom == 1 and not sx and not sy:
        return im
    cw, ch = W / zoom, H / zoom
    x0 = min(max(0, fx - cw / 2), W - cw) + sx
    y0 = min(max(0, fy - ch / 2), H - ch) + sy
    return im.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)


def scanner(im, t):
    """Рамка-сканер на Стасе и плашка «ОБЪЕКТ: СТАС, 23»."""
    u = t - E.SCAN
    if not (0 <= u < V['M1'] + D['M1'] - E.SCAN + 0.4):
        return
    a = cl(u / 0.2) * (1 - cl((t - V['M1'] - D['M1']) / 0.4))
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = 360, 780, 760, 1860
    c = (90, 255, 200, 255)
    L = 60
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line((x, y, x + dx * L, y), fill=c, width=8)
        d.line((x, y, x, y + dy * L), fill=c, width=8)
    yy = y0 + ((u * 700) % (y1 - y0))
    d.line((x0 + 10, yy, x1 - 10, yy), fill=(90, 255, 200, 150), width=5)
    lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(lay)
    chip(im, 'ОБЪЕКТ: СТАС, 23', W / 2, 300, bg=(10, 30, 30, 235), fg=(90, 255, 200, 255), size=48,
         pop=spring(u - 0.15, 3, 0.5) * a, outline=(90, 255, 200, 255))


def overlay_ui(im, t):
    # хук
    if T['s1'] <= t < T['s1'] + 3.3 and t < E.SCAN + 0.6:
        pass
    if T['s1'] <= t < T['open1'] + 1.2:
        a = cl((t - T['s1']) / 0.2) * (1 - cl((t - T['open1'] - 0.8) / 0.4))
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        text_c(lay, 'ПРИШЕЛЕЦ ВПЕРВЫЕ ВИДИТ,', W / 2, 400, 58, fill=(255, 220, 90, 255))
        text_c(lay, 'КАК ЗЕМЛЯНЕ ИЩУТ ЕДУ', W / 2, 472, 58, fill=(255, 220, 90, 255))
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)
    scanner(im, t)
    # страница блокнота «полный = пустой»
    n0, n1 = E.NOTE
    if n0 <= t < n1 + 0.5:
        k = spring(t - n0, 2.5, 0.55) * (1 - eio((t - n1) / 0.4))
        page = Image.new('RGBA', (560, 300), (0, 0, 0, 0))
        d = ImageDraw.Draw(page)
        d.rounded_rectangle((0, 0, 559, 299), 24, fill=(245, 238, 215, 250), outline=(140, 110, 80, 255), width=5)
        for j in range(5):
            d.line((30, 70 + j * 46, 530, 70 + j * 46), fill=(170, 190, 220, 255), width=2)
        d.line((80, 10, 80, 290), fill=(230, 120, 120, 255), width=3)
        d.text((100, 24), 'НАБЛЮДЕНИЕ №1', font=font('Bold', 30), fill=(120, 90, 70, 255))
        txt = 'полный = пустой'
        nch = int(len(txt) * cl((t - n0 - 0.3) / 1.6))
        d.text((100, 110), txt[:nch], font=font('Heavy', 64), fill=(40, 50, 120, 255))
        if nch == len(txt):
            d.line((100, 210, 100 + 380 * eo((t - n0 - 1.9) / 0.4), 210), fill=(230, 60, 70, 255), width=8)
        page = page.rotate(-4, expand=True, resample=Image.BICUBIC)
        page = page.resize((max(1, int(page.width * k)), max(1, int(page.height * k))), Image.BICUBIC)
        im.alpha_composite(page, (int(W / 2 - page.width / 2), int(560 - page.height / 2)))
    # счётчик открытий
    n, last = 0, 0
    for t0, c in E.COUNT:
        if t >= t0:
            n, last = c, t0
    if n and t < T['s4'] + 0.3:
        a = 1 - cl((t - T['s4']) / 0.3)
        pop = spring(t - last, 3, 0.4) if t - last < 1 else 1
        chip(im, f'ОТКРЫТИЙ: {n}', W / 2, 300, bg=(230, 60, 70, int(240 * a)), fg=(255, 255, 255, int(255 * a)), size=50, pop=pop)
    # доставка: приложение на телефоне
    if T['phone'] <= t < V['M8']:
        k = spring(t - T['phone'], 2.5, 0.5)
        chip(im, 'ДОСТАВКА · ~60 МИН', W / 2, 330, bg=(255, 90, 60, 240), size=48, pop=k)
    # сравнение
    if E.CMP <= t < T['s5']:
        chip(im, 'ПЕЛЬМЕНИ: 10 МИН', W / 2, 300, bg=(70, 200, 110, 240), size=48, pop=spring(t - E.CMP, 3, 0.45))
        chip(im, 'ДОСТАВКА: 60 МИН', W / 2, 400, bg=(255, 90, 60, 240), size=48, pop=spring(t - E.CMP - 0.25, 3, 0.45))
        if t >= E.STAMP:
            k = spring(t - E.STAMP, 3.5, 0.35)
            f = font('Heavy', 46)
            tw = int(ImageDraw.Draw(im).textlength('У ХОЛОДИЛЬНИКА: 20 МИН', font=f))
            st = Image.new('RGBA', (tw + 70, 130), (0, 0, 0, 0))
            d = ImageDraw.Draw(st)
            d.rounded_rectangle((0, 0, tw + 69, 129), 20, outline=(230, 40, 50, 255), width=10)
            d.text((35, 30), 'У ХОЛОДИЛЬНИКА: 20 МИН', font=f, fill=(230, 40, 50, 255))
            st = st.rotate(-6, expand=True, resample=Image.BICUBIC)
            s = lerp(2.2, 1.0, cl(k))
            st = st.resize((max(1, int(st.width * s)), max(1, int(st.height * s))), Image.BICUBIC)
            im.alpha_composite(st, (int(W / 2 - st.width / 2), int(540 - st.height / 2)))
    # подарок
    gt = T['gift']
    if gt - 0.5 <= t < gt + 0.1:
        k = eio((t - gt + 0.5) / 0.6)
        x, y = lerp(TABLE_X - 160, 560, k), lerp(1100, 1150, k) - math.sin(k * math.pi) * 380
        size = int(lerp(140, 240, math.sin(k * math.pi)))
        g = lottie.frame(GIFT, t - gt + 0.5, size=size)
        im.alpha_composite(g, (int(x - size / 2), int(y - size / 2)))
    if gt <= t < T['s6']:
        k = spring(t - gt, 2.5, 0.5)
        lay = Image.new('RGBA', (740, 200), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        dd.rounded_rectangle((0, 0, 739, 199), 50, fill=(25, 25, 40, 240), outline=(255, 210, 90, 255), width=4)
        lay.alpha_composite(lottie.frame(GIFT, t - gt, size=170), (15, 15))
        dd.text((200, 40), 'Мисед подарил', font=font('Bold', 40), fill=(220, 220, 240, 255))
        dd.text((200, 100), 'Homemade Cake', font=font('Heavy', 52), fill=(255, 215, 90, 255))
        lay = lay.resize((max(1, int(740 * k)), max(1, int(200 * k))), Image.BICUBIC)
        im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(380 - lay.height / 2)))
        u = t - gt
        for j in range(30):
            if u > 2.5:
                break
            rr = np.random.default_rng(j)
            ang = rr.uniform(0, 2 * math.pi)
            sp = rr.uniform(300, 700)
            cx = W / 2 + math.cos(ang) * sp * u
            cy = 380 + math.sin(ang) * sp * u + 500 * u * u
            c = [(255, 210, 70), (120, 220, 255), (255, 120, 160), (140, 240, 140)][j % 4]
            ImageDraw.Draw(im).rectangle((cx - 8, cy - 5, cx + 8, cy + 5), fill=c + (int(255 * cl(1 - u / 2.5)),))


def render_at(t):
    if t < T['intro_end']:
        return scene_intro(t).convert('RGB')
    if t >= T['s6']:
        im = scene_outro(t)
        subtitles(im, t)
        return im.convert('RGB')
    im = scene_kitchen(t)
    im = camera(im, t)
    vignette(im)
    overlay_ui(im, t)
    subtitles(im, t)
    for c in [T['s1']] + list(T['opens']):              # вспышки на склейках
        flash(im, t, c, 0.1, k=0.7)
    if T['s4'] <= t < T['s4'] + 0.12:
        flash(im, t, T['s4'], 0.12, k=0.5)
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
