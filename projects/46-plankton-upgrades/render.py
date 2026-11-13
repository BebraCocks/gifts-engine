"""46 · «Из чего это улучшили?» — минималистичный 2D в «Помойном ведре».
Кадр — чистая функция времени содержания t. Планктон и Карен нарисованы кодом (куклы с мимикой и мелкой анимацией),
NFT — живые Lottie из gifts engine, переходы — пузыри, RubUp — banner.Breaks (содержание на паузе)."""
import sys
import math
import functools
import wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import banner
import frames
import fx
import gifts_api as G
import lottie
import config
from timeline import DUR, AT, END_OF, TAKES, IDS, ON
from events import AD_STOP, SLIDE, TRANSITIONS, ROUNDS, PLANKTON_PICK, FAIL, KAREN
from script import TIMER, SEQ

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)

CREAM, TEAL, GREEN, RED = (245, 238, 214), (120, 214, 196), (96, 224, 128), (236, 84, 76)
INK = (22, 30, 32)
MODEL_C, MODEL_S = (540, 660), 500
FLOOR_Y = 960
CARD_Y, CARD_W, CARD_H = 1175, 310, 340
CARD_X = (200, 540, 880)
PL_FEET = (200, 1745)

DATA = [
    dict(gift='Instant Ramen', model='Red Lobster', title='КРАСНЫЙ ЛОБСТЕР', ans=1, pick=0, rar='ВЫПАДАЕТ 2 РАЗА ИЗ 100',
         cards=[('Pool Float', 'круг'), ('Instant Ramen', 'лапша'), ('Money Pot', 'горшок')]),
    dict(gift='Big Year', model='Pavel Durov', title='ПАВЕЛ ДУРОВ', ans=2, pick=0, rar='ВЫПАДАЕТ 23 РАЗА ИЗ 1000',
         cards=[("Durov's Cap", 'кепка'), ("Durov's Glasses", 'очки'), ('Big Year', 'календарь')]),
    dict(gift='Money Pot', model='Skibidi Toilet', title='СКИБИДИ-ТУАЛЕТ', ans=1, pick=0, rar='ВЫПАДАЕТ 1 РАЗ ИЗ 1000',
         cards=[('Happy Brownie', 'какашка'), ('Money Pot', 'горшок'), ('Restless Jar', 'банка')]),
]
for d in DATA:
    d['mfile'] = str(G.model_file(d['gift'], d['model'], 'json'))
    d['ofile'] = str(G.original_file(d['gift'], 'json'))
    d['cfiles'] = [str(G.original_file(g, 'json')) for g, _ in d['cards']]
CAP_FILE = str(G.original_file("Durov's Cap", 'json'))
SEG = [0.0] + list(TRANSITIONS) + [DUR + 1]          # хук, раунды 1–3
LINES = {s[0]: s[5] for s in SEQ}
P_LINES = [(AT[c], END_OF[c], c) for c in IDS if c.startswith('P')]


# ------------------------------------------------------------------ голос Планктона -> рот
def _envelopes():
    env = {}
    for take, cid, on in zip(TAKES, IDS, ON):
        if not cid.startswith('P') or not take.is_file():
            continue
        with wave.open(str(take)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32).reshape(-1, w.getnchannels()).mean(1)
            sr = w.getframerate()
        hop = sr // 60
        e = np.sqrt(np.array([np.mean(x[i:i + hop] ** 2) for i in range(0, len(x) - hop, hop)]) + 1e-9)
        e = np.convolve(e / (np.percentile(e, 95) + 1e-9), np.ones(3) / 3, 'same')
        env[cid] = (on, np.clip(e, 0, 1))
    return env


ENV = _envelopes()


def mouth_open(t):
    for cid, (on, e) in ENV.items():
        k = int((t - on) * 60)
        if 0 <= k < len(e):
            return float(e[k])
    return 0.0


def speaking(t):
    for a, b, c in P_LINES:
        if a - 0.05 <= t <= b + 0.1:
            return c
    return None


# ------------------------------------------------------------------ helpers
def put(c, im, cx, cy, s=1.0, rot=0.0, alpha=1.0, anchor=None, add=False):
    if im is None or alpha <= 0.003 or s <= 0.003:
        return
    fx.over(c, fx.warp(im, cx, cy, s, rot_=rot, anchor=anchor), alpha, add=add)


def txt(c, s, size, col, cx, cy, weight='Heavy', alpha=1.0, scale=1.0):
    put(c, fx.text_img(((s, col),), size, weight), cx, cy, scale, alpha=alpha)


def seg_alpha(t, k):
    """Видимость сегмента k (0 — хук, 1..3 — раунды): смена прячется в пузырях, перекрёстно за 0,24 с."""
    a = fx.smooth((t - SEG[k]) / 0.24 + 0.5) if k else 1.0
    return a * (1 - fx.smooth((t - SEG[k + 1]) / 0.24 + 0.5))


def slide(t):
    """0..1: Планктон с моделью уезжает вниз перед RubUp и возвращается после (время содержания стоит на AD_STOP)."""
    if t < AD_STOP:
        return fx.ease_in(fx.clamp01((t - (AD_STOP - SLIDE)) / SLIDE))
    return 1 - fx.ease_out(fx.clamp01((t - AD_STOP) / SLIDE))


# ------------------------------------------------------------------ фон: «Помойное ведро»
@functools.lru_cache(None)
def background():
    S = 2
    im = Image.new('RGB', (W * S, H * S))
    d = ImageDraw.Draw(im)
    for y in range(0, H * S, 4):                                   # стена: холодный серо-зелёный металл
        k = y / (H * S)
        d.rectangle([0, y, W * S, y + 4], fill=(int(30 - 8 * k), int(42 - 10 * k), int(44 - 10 * k)))
    for x in range(108, W, 216):                                   # швы листов и заклёпки
        d.line([x * S, 0, x * S, FLOOR_Y * S], fill=(40, 55, 57), width=3 * S)
        for y in range(120, FLOOR_Y - 40, 190):
            d.ellipse([(x - 20) * S, (y - 5) * S, (x - 10) * S, (y + 5) * S], fill=(48, 66, 68))
            d.ellipse([(x + 10) * S, (y - 5) * S, (x + 20) * S, (y + 5) * S], fill=(48, 66, 68))
    d.rectangle([0, FLOOR_Y * S, W * S, H * S], fill=(17, 24, 26))  # пол
    d.rectangle([0, FLOOR_Y * S, W * S, (FLOOR_Y + 5) * S], fill=(52, 72, 74))
    for k in range(1, 7):                                          # плитка пола, уходящая в глубину
        y = FLOOR_Y + 5 + (H - FLOOR_Y) * (k / 6) ** 1.8
        d.line([0, y * S, W * S, y * S], fill=(22, 31, 33), width=2 * S)
    for k in range(-6, 7):
        d.line([(540 + k * 70) * S, FLOOR_Y * S, (540 + k * 330) * S, H * S], fill=(22, 31, 33), width=2 * S)
    # лампа на проводе
    d.line([540 * S, 0, 540 * S, 70 * S], fill=(12, 16, 17), width=5 * S)
    d.polygon([(500 * S, 70 * S), (580 * S, 70 * S), (615 * S, 118 * S), (465 * S, 118 * S)], fill=(60, 84, 80))
    d.ellipse([515 * S, 104 * S, 565 * S, 138 * S], fill=(255, 244, 190))
    return np.asarray(im.resize((W, H), Image.LANCZOS), np.float32)


@functools.lru_cache(None)
def light_cone():
    im = Image.new('L', (W // 2, H // 2), 0)
    ImageDraw.Draw(im).polygon([(245, 60), (295, 60), (520, 440), (20, 440)], fill=255)
    im = im.filter(ImageFilter.GaussianBlur(22)).resize((W, H), Image.BILINEAR)
    a = np.asarray(im, np.float32) / 255
    a *= np.clip(1 - (np.arange(H)[:, None] - 100) / 900, 0, 1) ** 1.3
    return a[..., None] * np.array([150, 255, 190], np.float32)


# ------------------------------------------------------------------ Планктон (кукла)
BODY, BODY_D = (64, 142, 88), (30, 84, 54)


def plankton_img(t, emo, talk, look, point, blink):
    """Логический холст 380x470, ноги в (190, 455). emo: smug | angry | shock | idle."""
    S = 2
    im = Image.new('RGBA', (380 * S, 470 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    sway = math.sin(t * 2.1) * 0.10 + (math.sin(t * 31) * 0.05 if emo == 'angry' else 0) + talk * math.sin(t * 17) * 0.04
    for side in (-1, 1):                                           # усики: три сегмента, покачиваются
        x, y, ang = 190 + side * 26, 172, -math.pi / 2 + side * 0.34 + sway
        pts = [P(x, y)]
        for k in range(4):
            ang += side * 0.20 + sway * 0.6
            x, y = x + math.cos(ang) * 38, y + math.sin(ang) * 38
            pts.append(P(x, y))
        d.line(pts, fill=BODY_D + (255,), width=9 * S, joint='curve')
        d.ellipse([pts[-1][0] - 7 * S, pts[-1][1] - 7 * S, pts[-1][0] + 7 * S, pts[-1][1] + 7 * S], fill=BODY_D + (255,))
    for side in (-1, 1):                                           # ноги
        d.line([P(190 + side * 22, 395), P(190 + side * 26, 440)], fill=BODY_D + (255,), width=9 * S)
        d.ellipse([*P(190 + side * 26 - 20 + side * 8, 432), *P(190 + side * 26 + 20 + side * 8, 452)], fill=BODY_D + (255,))
    # руки
    wig = math.sin(t * 3.0) * 0.08
    arms = {-1: math.pi / 2 + 0.55 + wig, 1: math.pi / 2 - 0.55 - wig}
    if emo == 'angry':
        arms = {-1: -math.pi / 2 - 0.55 + math.sin(t * 26) * 0.22, 1: -math.pi / 2 + 0.55 + math.sin(t * 26 + 1) * 0.22}
    elif emo == 'shock':
        arms = {-1: math.pi + 0.5, 1: -0.5}
    elif emo == 'smug':
        arms[-1] = math.pi / 2 + 0.9 + wig                         # рука в бок
    if point > 0.01:
        arms[1] = (math.pi / 2 - 0.55) * (1 - point) + (-0.62 + math.sin(t * 9) * 0.06) * point
    for side in (-1, 1):
        x0, y0 = 190 + side * 62, 300
        L = 78 if not (side == 1 and point > 0.01) else 78 + 22 * point
        x1, y1 = x0 + math.cos(arms[side]) * L, y0 + math.sin(arms[side]) * L
        d.line([P(x0, y0), P(x1, y1)], fill=BODY_D + (255,), width=10 * S)
        d.ellipse([*P(x1 - 12, y1 - 12), *P(x1 + 12, y1 + 12)], fill=BODY + (255,), outline=BODY_D + (255,), width=3 * S)
    # тело-капсула
    d.rounded_rectangle([*P(118, 150), *P(262, 405)], 72 * S, fill=BODY + (255,), outline=BODY_D + (255,), width=5 * S)
    d.rounded_rectangle([*P(134, 168), *P(160, 300)], 13 * S, fill=(88, 170, 110, 255))          # блик
    # глаз
    ex, ey, er = 190, 240, 50
    ry = er * (1 - 0.92 * blink) * (1.12 if emo == 'shock' else 1.0)
    if emo == 'angry':
        ry *= 0.82
    d.ellipse([*P(ex - er, ey - ry), *P(ex + er, ey + ry)], fill=(252, 240, 150, 255), outline=BODY_D + (255,), width=4 * S)
    if blink < 0.6:
        ir = 24 if emo != 'shock' else 15
        px, py = ex + look[0] * 18, ey + look[1] * min(14, ry * 0.4)
        d.ellipse([*P(px - ir, py - ir), *P(px + ir, py + ir)], fill=(196, 44, 40, 255))
        d.ellipse([*P(px - ir * .45, py - ir * .45), *P(px + ir * .45, py + ir * .45)], fill=(14, 10, 10, 255))
        d.ellipse([*P(px - ir * .6, py - ir * .65), *P(px - ir * .25, py - ir * .3)], fill=(255, 255, 255, 230))
    # бровь
    tilt = {'smug': -0.22, 'angry': 0.30, 'shock': 0.0, 'idle': -0.05}[emo]
    by = ey - er - {'smug': 12, 'angry': -6, 'shock': 30, 'idle': 14}[emo]
    d.line([P(ex - 58, by - math.sin(tilt) * 58), P(ex + 58, by + math.sin(tilt) * 58)], fill=(14, 20, 16, 255), width=14 * S)
    # рот
    mx, my = 190, 338
    if talk > 0.08 or emo in ('angry', 'shock'):
        o = max(talk, 0.55 if emo == 'shock' else 0.25 if emo == 'angry' else 0)
        mw, mh = (40 if emo == 'shock' else 56), 8 + o * 34
        d.ellipse([*P(mx - mw, my - mh), *P(mx + mw, my + mh)], fill=(74, 14, 20, 255), outline=BODY_D + (255,), width=3 * S)
        if emo == 'angry':
            d.rectangle([*P(mx - mw * .7, my - mh + 2), *P(mx + mw * .7, my - mh + 9)], fill=(250, 250, 240, 255))
        elif mh > 18:
            d.ellipse([*P(mx - 22, my + mh - 20), *P(mx + 22, my + mh + 4)], fill=(226, 92, 100, 255))
    else:
        d.arc([*P(mx - 46, my - 34), *P(mx + 46, my + 14)], 20 if emo == 'smug' else 30, 150, fill=(14, 20, 16, 255), width=6 * S)
        if emo == 'smug':
            d.line([P(mx + 40, my - 4), P(mx + 52, my - 16)], fill=(14, 20, 16, 255), width=6 * S)
    return im.resize((380, 470), Image.LANCZOS)


def blink_at(t, period=3.1, phase=0.0):
    u = (t + phase) % period
    return max(0.0, 1 - abs(u - 0.09) / 0.09) if u < 0.18 else 0.0


def plankton_state(t):
    """-> (emo, talk, point 0..1, look, dx, dy, alpha-ish visible)"""
    line = speaking(t)
    emo = 'idle'
    if line in ('P1', 'P2', 'P4', 'P6'):
        emo = 'smug'
    if line in ('P3', 'P5', 'P7'):
        emo = 'angry'
    for (q, timer, ans), fail in zip(ROUNDS, FAIL):
        if ans + 0.3 <= t < fail:
            emo = 'shock'
    point = 0.0
    for pk, (q, timer, ans) in zip(PLANKTON_PICK, ROUNDS):
        point = max(point, fx.smooth((t - pk) / 0.25) * (1 - fx.smooth((t - ans + 0.2) / 0.25)))
    look = (0.75, -0.85) if emo in ('idle', 'shock') else (0.6, 0.25) if point > 0.3 else (0.35, 0.1)
    return emo, mouth_open(t), point, look


def draw_plankton(c, t):
    t_in = AT['P1'] - 0.3
    if t < t_in:
        return
    emo, talk, point, look = plankton_state(t)
    x, y = PL_FEET
    y += (1 - fx.ease_out_back(fx.clamp01((t - t_in) / 0.45))) * 520          # выпрыгивает снизу
    y += slide(t) * 1100
    for f in FAIL:                                                             # подпрыгивает от злости
        u = t - f
        if 0 <= u < 0.9:
            y -= abs(math.sin(u * 11)) * 34 * (1 - u / 0.9)
    for pk in PLANKTON_PICK:                                                   # уверенный кивок на выборе
        y -= fx.bump((t - pk) / 0.5) * 16 if 0 <= t - pk < 1 else 0
    t_out = END_OF['P7'] + 0.05                                                # убегает за левый край
    run = fx.ease_in(fx.clamp01((t - t_out) / 0.55))
    x -= run * 520
    if emo == 'angry':
        x += math.sin(t * 43) * 5
    breathe = 1 + math.sin(t * 2.6) * 0.022
    rot = math.sin(t * 1.7) * 0.025 - run * 0.35 + (0.06 if point > 0.3 else 0)
    im = plankton_img(t, emo, talk, look, point, blink_at(t, 2.7, 0.4))
    sh = fx.radial(220, (0, 0, 0), 1.6, 0.55)
    fx.over(c, fx.warp(sh, x, PL_FEET[1] + 4 + slide(t) * 1100, 1.0, 0.22), 0.8 * (1 - run))
    fx.over(c, fx.warp(im, x, y, 0.98, 0.98 * breathe, rot_=rot, anchor=(190, 455)))
    # реплика в пузыре
    line = speaking(t)
    if line and slide(t) < 0.05:
        a, b = AT[line], END_OF[line]
        k = fx.ease_out_back(fx.clamp01((t - a) / 0.22)) * (1 - fx.smooth((t - b - 0.02) / 0.1))
        put(c, speech_bubble(LINES[line]), 372, 1500, k, anchor=(0, 110), alpha=min(1, k * 1.5))


@functools.lru_cache(None)
def speech_bubble(text):
    f = fx.font('Bold', 46)
    words, rows, cur = text.split(), [], ''
    for w_ in words:
        if f.getlength((cur + ' ' + w_).strip()) > 560 and cur:
            rows.append(cur)
            cur = w_
        else:
            cur = (cur + ' ' + w_).strip()
    rows.append(cur)
    bw = int(max(f.getlength(r) for r in rows)) + 70
    bh = 58 * len(rows) + 52
    S = 2
    im = Image.new('RGBA', ((bw + 40) * S, (bh + 20) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 110 * S), (46 * S, 70 * S), (46 * S, 120 * S)], fill=CREAM + (255,))
    d.rounded_rectangle([36 * S, 6 * S, (36 + bw) * S, (6 + bh) * S], 34 * S, fill=CREAM + (255,))
    f2 = fx.font('Bold', 46 * S)
    for k, r in enumerate(rows):
        d.text(((36 + bw / 2) * S, (6 + 26 + 29 + 58 * k) * S), r, font=f2, fill=INK + (255,), anchor='mm')
    return im.resize((bw + 40, bh + 20), Image.LANCZOS)


# ------------------------------------------------------------------ Карен
def karen_img(t):
    """Логический холст 300x360, колёса в (150, 350). Экран с «голосовой» волной, кепка Дурова — живой Lottie."""
    S = 2
    im = Image.new('RGBA', (300 * S, 360 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    d.line([P(150, 250), P(150, 322)], fill=(92, 104, 110, 255), width=14 * S)                 # стойка
    d.rounded_rectangle([*P(82, 318), *P(218, 338)], 9 * S, fill=(70, 80, 86, 255))
    for wx in (100, 200):                                                                     # колёса крутятся
        d.ellipse([*P(wx - 15, 328), *P(wx + 15, 358)], fill=(24, 28, 30, 255))
        a = t * 14
        d.line([P(wx - math.cos(a) * 11, 343 - math.sin(a) * 11), P(wx + math.cos(a) * 11, 343 + math.sin(a) * 11)],
               fill=(130, 140, 146, 255), width=3 * S)
    d.rounded_rectangle([*P(48, 118), *P(252, 256)], 18 * S, fill=(150, 162, 170, 255), outline=(84, 96, 102, 255), width=4 * S)
    d.rounded_rectangle([*P(64, 134), *P(236, 240)], 10 * S, fill=(18, 40, 38, 255))
    pts = []                                                                                  # волна на экране
    for k in range(41):
        x = 74 + k * 3.8
        env = math.exp(-((k - 20) / 11) ** 2)
        y = 187 + math.sin(k * 0.9 + t * 13) * 26 * env * (0.55 + 0.45 * math.sin(t * 5.3))
        pts.append(P(x, y))
    d.line(pts, fill=(110, 255, 150, 255), width=4 * S, joint='curve')
    d.ellipse([*P(222, 244), *P(232, 254)], fill=(255, 90, 80, 255) if math.sin(t * 9) > 0 else (120, 40, 36, 255))
    im = im.resize((300, 360), Image.LANCZOS)
    cap = lottie.frame(CAP_FILE, t, size=190)
    cap = cap.rotate(-7, Image.BICUBIC)
    im.alpha_composite(cap, (55, -18 + int(round(math.sin(t * 12) * 2))))
    return im


def draw_karen(c, t):
    a, b = KAREN
    if not a <= t <= b:
        return
    u = (t - a) / (b - a)
    x = -170 + u * (W + 340)
    y = FLOOR_Y + 22 + math.sin(t * 12) * 2.5
    fx.over(c, fx.warp(fx.radial(320, (0, 0, 0), 1.6, 0.5), x, FLOOR_Y + 24, 1.0, 0.16), 0.8)
    put(c, karen_img(t), x, y, 1.0, rot=0.045 + math.sin(t * 6) * 0.012, anchor=(150, 356), alpha=0.93)


# ------------------------------------------------------------------ карточки и модель
@functools.lru_cache(None)
def card_plate(state):
    col = {'base': (36, 49, 52, 255), 'ok': (30, 66, 46, 255), 'q': (36, 49, 52, 255)}[state]
    out = {'base': (70, 94, 96, 255), 'ok': GREEN + (255,), 'q': (70, 94, 96, 255)}[state]
    return fx.rounded(CARD_W, CARD_H, 36, col, out, 5 if state != 'ok' else 8)


@functools.lru_cache(None)
def mark_badge(failed):
    S = 2
    im = Image.new('RGBA', (92 * S, 92 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([4 * S, 4 * S, 88 * S, 88 * S], fill=BODY + (255,), outline=CREAM + (255,), width=4 * S)
    d.ellipse([24 * S, 22 * S, 68 * S, 66 * S], fill=(252, 240, 150, 255))
    d.ellipse([36 * S, 34 * S, 56 * S, 54 * S], fill=(196, 44, 40, 255))
    d.line([20 * S, 20 * S, 72 * S, 16 * S], fill=(14, 20, 16, 255), width=7 * S)
    if failed:
        d.ellipse([4 * S, 4 * S, 88 * S, 88 * S], fill=(236, 84, 76, 235), outline=CREAM + (255,), width=4 * S)
        d.line([28 * S, 28 * S, 64 * S, 64 * S], fill=(255, 255, 255, 255), width=9 * S)
        d.line([64 * S, 28 * S, 28 * S, 64 * S], fill=(255, 255, 255, 255), width=9 * S)
    return im.resize((92, 92), Image.LANCZOS)


def draw_cards(c, t, k, alpha):
    """k = 0 — хук (карточки «?»), 1..3 — раунды."""
    if alpha <= 0.003:
        return
    if k == 0:
        for j, x in enumerate(CARD_X):
            a = fx.ease_out_back(fx.clamp01((t - 0.45 - 0.25 * j) / 0.35))
            pulse = 1 + 0.06 * max(0, math.sin((t - j * 0.33) * 6.0)) ** 3
            put(c, card_plate('q'), x, CARD_Y + (1 - a) * 60, a * pulse, alpha=alpha * min(1, a * 1.4))
            txt(c, '?', 170, TEAL, x, CARD_Y + (1 - a) * 60 - 6, alpha=alpha * min(1, a * 1.4), scale=a * pulse)
        return
    d = DATA[k - 1]
    q, timer, ans = ROUNDS[k - 1]
    pk, fail = PLANKTON_PICK[k - 1], FAIL[k - 1]
    for j, x in enumerate(CARD_X):
        a = fx.ease_out_back(fx.clamp01((t - q - 0.4 - 0.18 * j) / 0.35))
        if a <= 0.003:
            continue
        rev = fx.smooth((t - ans - 0.35) / 0.3)
        ok = j == d['ans']
        s = a * (1 + 0.07 * rev + 0.05 * fx.bump((t - ans - 0.35) / 0.6)) if ok else a * (1 - 0.05 * rev)
        al = alpha * min(1, a * 1.4) * (1 if ok else 1 - 0.55 * rev)
        y = CARD_Y + (1 - a) * 60 - (14 * rev if ok else 0)
        if ok and rev > 0:
            put(c, fx.radial(560, GREEN, 1.8, 0.55), x, y, 1.0, alpha=al * rev * (0.8 + 0.2 * math.sin(t * 5)), add=True)
        put(c, card_plate('base'), x, y, s, alpha=al)
        if ok and rev > 0:
            put(c, card_plate('ok'), x, y, s, alpha=al * rev)
        put(c, lottie.frame(d['cfiles'][j], t + j * 0.7, size=225), x, y - 40, s, alpha=al)
        txt(c, d['cards'][j][1], 48, CREAM, x, y + 120, 'Bold', alpha=al, scale=s)
        if j == d['pick']:
            m = fx.ease_out_back(fx.clamp01((t - pk - 0.15) / 0.3))
            failed = t >= ans + 0.75
            wob = math.sin((t - ans - 0.75) * 30) * 0.2 * max(0, 1 - (t - ans - 0.75) / 0.5) if failed else 0
            put(c, mark_badge(failed), x - CARD_W / 2 + 22, y - CARD_H / 2 + 22, m * (1 + 0.25 * fx.bump((t - ans - 0.75) / 0.5)),
                rot=wob, alpha=alpha * min(1, m * 1.5))


def burst(c, t0, t, cx, cy, col):
    u = t - t0
    if not 0 <= u < 0.7:
        return
    for k in range(18):
        ang = k * 2.399 + 0.4
        r = 60 + fx.ease_out(u / 0.7) * (230 + 90 * math.sin(k * 7.1))
        s = (0.5 + 0.5 * math.sin(k * 3.3) ** 2) * (1 - u / 0.7)
        put(c, fx.radial(64, col if k % 3 else CREAM, 1.2, 1.0), cx + math.cos(ang) * r, cy + math.sin(ang) * r, s * 1.3,
            alpha=1 - u / 0.7, add=True)


def draw_model(c, t, k, alpha):
    if alpha <= 0.003:
        return
    cx, cy = MODEL_C
    cy += math.sin(t * 1.9) * 9
    glow = 0.42 + 0.08 * math.sin(t * 2.3)
    if k == 0:
        d = DATA[2]
        s = 0.9 + 0.1 * fx.spring(fx.clamp01(t / 0.9)) + 0.03 * math.sin(t * 3.1)
        put(c, fx.radial(880, (90, 255, 170), 2.2, glow), cx, cy, 1.0, alpha=alpha, add=True)
        put(c, lottie.frame(d['mfile'], t + 0.5, size=MODEL_S), cx, cy, s, rot=math.sin(t * 1.3) * 0.05, alpha=alpha)
        return
    d = DATA[k - 1]
    q, timer, ans = ROUNDS[k - 1]
    off = slide(t) * 1750 if k == 3 else 0
    cy += off
    ent = fx.clamp01((t - q + 0.1) / 0.55)
    if ent <= 0:
        return
    y_in = (1 - fx.spring(ent, 2.0, 0.5)) * -620
    put(c, fx.radial(880, (90, 255, 170), 2.2, glow), cx, cy + y_in, 1.0, alpha=alpha * min(1, ent * 2), add=True)
    if timer is not None and timer <= t < ans:                                   # кольцо таймера
        left = max(0.0, 1 - (t - timer) / TIMER)
        ring = fx.draw_rgba((cx - 330, cy - 330, cx + 330, cy + 330), lambda dr, m, S: (
            dr.ellipse([*m(cx - 310, cy - 310), *m(cx + 310, cy + 310)], outline=(60, 82, 84, 255), width=10 * S),
            dr.arc([*m(cx - 310, cy - 310), *m(cx + 310, cy + 310)], -90, -90 + 360 * left,
                   fill=(RED if left < 0.3 else TEAL) + (255,), width=12 * S)))
        fx.over(c, ring, alpha * fx.smooth((t - timer) / 0.2) * (1 - fx.smooth((t - ans + 0.2) / 0.2)))
    out = fx.clamp01((t - ans) / 0.28)                                           # модель «распадается»…
    if out < 1:
        put(c, lottie.frame(d['mfile'], t, size=MODEL_S), cx, cy + y_in, 1 - fx.ease_in(out), rot=out * 1.4 + math.sin(t * 1.3) * 0.04,
            alpha=alpha * (1 - out))
    burst(c, ans + 0.12, t, cx, cy, GREEN)
    back = fx.clamp01((t - ans - 0.18) / 0.5)                                    # …и собирается в исходный подарок
    if back > 0:
        put(c, lottie.frame(d['ofile'], t, size=MODEL_S), cx, cy, 0.94 * fx.spring(back, 2.2, 0.45), alpha=alpha * min(1, back * 3))
    r = fx.ease_out_back(fx.clamp01((t - ans - 0.85) / 0.3))                     # редкость
    if r > 0 and k < 3 or (k == 3 and r > 0 and t < AT['N8'] - 0.2):
        put(c, fx.solid_pill(d['rar'], (30, 66, 46), 44, CREAM), cx, 945, r, alpha=alpha * min(1, r * 1.5))


# ------------------------------------------------------------------ шапка
@functools.lru_cache(None)
def score_slot(state):
    S = 2
    im = Image.new('RGBA', (56 * S, 56 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if state:
        d.ellipse([2 * S, 2 * S, 54 * S, 54 * S], fill=RED + (255,))
        d.line([17 * S, 17 * S, 39 * S, 39 * S], fill=(255, 255, 255, 255), width=6 * S)
        d.line([39 * S, 17 * S, 17 * S, 39 * S], fill=(255, 255, 255, 255), width=6 * S)
    else:
        d.ellipse([4 * S, 4 * S, 52 * S, 52 * S], outline=(96, 124, 124, 255), width=4 * S)
    return im.resize((56, 56), Image.LANCZOS)


def draw_header(c, t):
    k = max(i for i in range(4) if t >= SEG[i] or i == 0)
    final = fx.smooth((t - AT['N8'] + 0.15) / 0.3)
    for seg in range(4):
        a = seg_alpha(t, seg)
        if seg == 3:
            a *= 1 - final
        if a <= 0.003:
            continue
        if seg == 0:
            pop = fx.ease_out_back(fx.clamp01(t / 0.4 + 0.55))
            txt(c, 'ИЗ ЧЕГО УЛУЧШИЛИ', 84, CREAM, 540, 235, alpha=a, scale=pop)
            txt(c, 'СКИБИДИ-ТУАЛЕТ?', 84, GREEN, 540, 330, alpha=a, scale=pop * (1 + 0.03 * math.sin(t * 5)))
            b = fx.smooth((t - 1.2) / 0.3)
            put(c, fx.solid_pill('ответ — в конце ролика', (36, 49, 52), 40, TEAL, 'Semibold'), 540, 945, 1.0, alpha=a * b)
        else:
            d = DATA[seg - 1]
            q = ROUNDS[seg - 1][0]
            e = fx.ease_out_back(fx.clamp01((t - q + 0.25) / 0.35))
            put(c, fx.solid_pill(f'РАУНД {seg} ИЗ 3', (36, 49, 52), 38, TEAL), 200, 185, 1.0, alpha=a)
            txt(c, d['title'], 86, CREAM, 540, 282, alpha=a * min(1, e * 1.5), scale=e)
            txt(c, 'из какого подарка?', 50, TEAL, 540, 364, 'Semibold', alpha=a * fx.smooth((t - q - 0.2) / 0.3))
    if t >= SEG[1] - 0.12:                                                       # счёт Планктона: три попытки
        a = fx.smooth((t - SEG[1]) / 0.24 + 0.5) * (1 - final)
        txt(c, 'ПЛАНКТОН', 36, TEAL, 740, 185, 'Bold', alpha=a)
        for j in range(3):
            hit = t >= ROUNDS[j][2] + 0.75
            s = 1 + 0.5 * fx.bump((t - ROUNDS[j][2] - 0.75) / 0.5) if hit else 1
            put(c, score_slot(hit), 880 + j * 62, 185, s, alpha=a)
    if final > 0:                                                                # финал
        e = fx.ease_out_back(fx.clamp01((t - AT['N8'] + 0.1) / 0.4))
        txt(c, 'А ТЫ СКОЛЬКО', 90, CREAM, 540, 235, alpha=final, scale=e)
        txt(c, 'УГАДАЛ?', 90, GREEN, 540, 335, alpha=final, scale=e * (1 + 0.03 * math.sin(t * 5)))
        b = fx.ease_out_back(fx.clamp01((t - AT['N8'] - 0.9) / 0.35))
        put(c, fx.solid_pill('ПЛАНКТОН: 0 ИЗ 3', (120, 36, 34), 58, CREAM), 540, 1500, b, alpha=min(1, b * 1.5))
        b2 = fx.ease_out_back(fx.clamp01((t - AT['N8'] - 1.3) / 0.35))
        put(c, fx.solid_pill('пиши в комментариях', CREAM, 52, INK), 540, 1625, b2 * (1 + 0.03 * math.sin(t * 6)), alpha=min(1, b2 * 1.5))


# ------------------------------------------------------------------ пузыри-переход
@functools.lru_cache(None)
def bubble(r, blur):
    S = 2
    n = (r * 2 + 24) * S
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = 12 * S
    d.ellipse([o, o, n - o, n - o], fill=(96, 200, 214, 150), outline=(226, 250, 255, 240), width=max(3, r // 12) * S)
    d.ellipse([o + r * S * 0.18, o + r * S * 0.18, n - o - r * S * 0.1, n - o - r * S * 0.1], fill=(70, 170, 196, 120))
    d.arc([o + r * S * 0.22, o + r * S * 0.22, n - o - r * S * 0.22, n - o - r * S * 0.22], 200, 262,
          fill=(255, 255, 255, 235), width=max(4, r // 7) * S)
    d.ellipse([n * 0.62, n * 0.66, n * 0.62 + r * S * 0.16, n * 0.66 + r * S * 0.16], fill=(255, 255, 255, 150))
    im = im.resize((r * 2 + 24, r * 2 + 24), Image.LANCZOS)
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


_RNG = np.random.RandomState(46)
BUBBLES = [(_RNG.uniform(-60, W + 60), _RNG.uniform(-200, H + 500), int(_RNG.choice([40, 60, 80, 110, 140, 180])),
            _RNG.uniform(0.82, 1.22), _RNG.uniform(0, 6.28)) for _ in range(95)]
BUBBLES.sort(key=lambda b: b[2])


def draw_bubbles(c, t):
    for T in TRANSITIONS:
        u = t - T
        if not -0.75 <= u <= 0.75:
            continue
        for x, y0, r, v, ph in BUBBLES:
            y = y0 - u * (H + 900) / 0.7 * v
            if y < -r - 30 or y > H + r + 30:
                continue
            put(c, bubble(r, 3 if r >= 180 else 0), x + math.sin(u * 7 + ph) * 22, y, 1 + 0.05 * math.sin(u * 15 + ph))


def draw_ambient_bubbles(c, t):
    """Редкие мелкие пузырьки на фоне — зал не выглядит застывшим."""
    for k in range(7):
        per = 5.0 + k * 0.7
        u = ((t + k * 1.9) % per) / per
        x = 90 + (k * 157) % 900 + math.sin(t * 1.3 + k) * 16
        put(c, bubble(40, 0), x, FLOOR_Y + 60 - u * 900, 0.22 + 0.05 * (k % 3), alpha=0.35 * math.sin(u * math.pi))


# ------------------------------------------------------------------ кадр
def render_at(t):
    c = background().copy()
    flick = 0.20 + 0.03 * math.sin(t * 3.1) + (0.05 if math.sin(t * 0.9) > 0.985 else 0)
    c += light_cone() * flick
    draw_ambient_bubbles(c, t)
    draw_karen(c, t)
    for k in range(4):
        a = seg_alpha(t, k)
        draw_model(c, t, k, a)
        draw_cards(c, t, k, a)
    draw_header(c, t)
    draw_plankton(c, t)
    draw_bubbles(c, t)
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
