"""«Как не попасться на скам с NFT-подарками» — 1080×1920, 60 fps. Кадр — чистая функция времени.
Детективное бюро (фон в аниме-стиле): пробковая доска с уликами-полароидами и красной нитью, счётчик схем 1–5
(горит текущая, разобранная гаснет + красная галочка), телефон с перепиской мошенника, штамп «СКАМ!».
Хук — лупа-разоблачение (обычная Мита → детектив). Жуть — 5 картинок «это я» + сообщения сами печатаются.
Реклама — Мита изучает дело над баннером, под баннером крадётся лиса-мошенник. Финал — папки «БЫЛО / НЕ БЫЛО».
Петля — круглый штамп «ДЕЛО ЗАКРЫТО» в конце и в начале."""
import functools
import math
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import banner
import frames
import fx
import events as E
import mita54 as M
import stage as S
import script
from timeline import DUR, ON, END, AD_STOP
from words import WORDS

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
KEYED = HERE / 'build' / 'keyed'
DECOR = HERE / 'input' / 'decor'
UFONT = HERE.parent / '51-mita-craft' / 'input' / 'fonts'
INK = (34, 30, 44)
WHITE = (255, 255, 255)
RED = (214, 40, 40)
BLUE = (40, 120, 230)
GOLD = (240, 190, 60)
MUSTARD = (226, 170, 40)
SUB_Y = 1640
TON_RUB = 86
PHONE_X, PHONE_Y, PHONE_H = 800, 1080, 860
PX = PHONE_X                      # текущий x телефона (меняется по ходу ролика)


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.35):
    return ease((t - t0) / d)


def pop(t, t0, d=0.45):
    return fx.ease_out_back(fx.clamp01((t - t0) / d)) if t < t0 + d else 1.0


def put(canvas, im, cx, cy, s=1.0, a=1.0, rot=0.0, anchor=None):
    if im is None or a <= 0.003 or s <= 0.003:
        return
    fx.over(canvas, fx.warp(im, cx, cy, s, s, rot, anchor), a)


@functools.lru_cache(None)
def ufont(weight, size):
    return ImageFont.truetype(str(UFONT / f'Unbounded-{weight}.ttf'), size)


@functools.lru_cache(None)
def utext(s_, size, weight='ExtraBold', color=WHITE, stroke=0, scol=INK):
    f = ufont(weight, size)
    l, t_, r, b_ = f.getbbox(s_, stroke_width=stroke)
    im = Image.new('RGBA', (r - l + 24, b_ - t_ + 24), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((12 - l, 12 - t_), s_, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=scol + (255,))
    return im


@functools.lru_cache(None)
def multi(parts, size, weight='Heavy'):
    return fx.text_img(parts, size, weight, False)


SYM_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


@functools.lru_cache(None)
def pill(s_, fill, size=30, tcol=WHITE):
    sym = s_[-1] if s_[-1] in '✓✗' else ''                # у основного шрифта нет ✓/✗ — рисуем их DejaVu
    body = s_[:-1].rstrip() if sym else s_
    S = 2
    fb, fs = ufont('ExtraBold', size * S), ImageFont.truetype(SYM_FONT, int(size * 1.15 * S))
    bw = fb.getlength(body) / S
    sw = (fs.getlength(sym) / S + size * 0.35) if sym else 0
    tw = int(bw + sw)
    w_, h_ = tw + 2 * size, int(size * 2.0)
    im = Image.new('RGBA', ((w_ + 12) * S, (h_ + 12) * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6 * S, 6 * S, (6 + w_) * S, (6 + h_) * S), h_ * S // 2, fill=fill + (255,), outline=(255, 255, 255, 235),
                        width=3 * S)
    x0, cy = 6 + size, (6 + h_ / 2 + 1) * S
    d.text((x0 * S, cy), body, font=fb, fill=tcol + (255,), anchor='lm')
    if sym:
        d.text(((x0 + tw) * S, cy), sym, font=fs, fill=tcol + (255,), anchor='rm')
    return im.resize((w_ + 12, h_ + 12), Image.LANCZOS)


@functools.lru_cache(None)
def keyed(name, w=None, h=None):
    im = Image.open(KEYED / f'{name}.png').convert('RGBA')
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
    if w:
        im = im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)
    elif h:
        im = im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)
    return im


def rub(ton):
    v = int(round(ton * TON_RUB / 100.0) * 100)
    return '~' + f'{v:,}'.replace(',', ' ') + ' ₽'


@functools.lru_cache(maxsize=32)
def radial(size, rgb, power=2.0):
    return fx.radial(size, rgb, power, 1.0)


# ------------------------------------------------------------------ фон: бюро (картинка автора)
@functools.lru_cache(None)
def office():
    im = Image.open(DECOR / 'office.png').convert('RGB')
    s = H / im.height
    im = im.resize((round(im.width * s), H), Image.LANCZOS)
    x0 = (im.width - W) // 2
    a = np.array(im.crop((x0, 0, x0 + W, H))).astype(np.float32)
    lum = a.mean(-1, keepdims=True)
    return a * 0.85 + lum * 0.15                 # чуть приглушить — фон не перетягивает внимание


BOARD = (50, 194, 1030, 819)                     # пробковая доска на экране
SLOTS = [(175, 470), (375, 430), (575, 470), (775, 430), (965, 470)]   # места полароидов (улик)
COUNTER_Y = 278


def creepy_k(t):
    return ease((t - E.CREEPY) / 0.5) * (1 - ease((t - E.CREEPY_END) / 0.5))


def background(t):
    cv = np.zeros((H, W, 4), np.float32)
    cv[..., :3] = office()
    cv[..., 3] = 255
    # лампа мерцает в жуть
    ck = creepy_k(t)
    fl = 1.0 if ck <= 0 else (0.4 + 0.6 * (math.sin(t * 37) > -0.2) * (math.sin(t * 11.3) > -0.6))
    put(cv, radial(256, (255, 220, 150)), 540, 150, 1.4, 0.3 * fl * (1 - 0.5 * ck))
    return cv


# ------------------------------------------------------------------ улики на доске: полароиды + красная нить
def polaroid(kind):
    """Полароид с «уликой» внутри (кэш по виду)."""
    return _polaroid(kind)


@functools.lru_cache(maxsize=8)
def _polaroid(kind):
    base = keyed('polaroid', w=180).copy()
    pw, ph = base.size
    # окно снимка ≈ 8 % отступ, 70 % высоты
    box = (int(pw * 0.08), int(ph * 0.17), int(pw * 0.92), int(ph * 0.78))
    bw, bh = box[2] - box[0], box[3] - box[1]
    if kind == 0:
        inner = keyed('offer_card', w=int(bw * 0.95))
    elif kind in (1, 4):
        inner = keyed('fox_head', h=int(bh * 0.92))
    elif kind == 2:
        inner = keyed('addr_bar', w=int(bw * 0.95))
    else:
        inner = keyed('bubble_out', w=int(bw * 0.9))
    base.alpha_composite(inner, (box[0] + (bw - inner.width) // 2, box[1] + (bh - inner.height) // 2))
    return base


def wanted(cv, t):
    """Пока улик мало — на доске плакат «РАЗЫСКИВАЕТСЯ» с лисой-мошенником (доска не пустая)."""
    a = appear(t, 0.3, 0.4) * (1 - appear(t, E.OFFER_SAY - 0.4, 0.5))
    if a <= 0:
        return
    x, y = 660, 520
    put(cv, keyed('polaroid', w=190), x, y, 1.0, a, 0.05)
    put(cv, keyed('fox_head', w=130), x, y - 22, 1.0, a, 0.05)
    put(cv, pill('РАЗЫСКИВАЕТСЯ', RED, 20), x, y + 112, 1.0, a, 0.05)
    pa = a
    put(cv, pill('МОШЕННИК', (60, 50, 50), 22), x - 250, y - 40, pop(t, E.HOOK_MSG + 0.4), pa, -0.08)
    put(cv, pill('ДЕЛО № 54', (120, 90, 60), 22), x - 250, y + 40, pop(t, E.HOOK_MSG + 0.7), pa, -0.05)


def board(cv, t):
    wanted(cv, t)
    done = [j for j, ts in enumerate(E.STAMPS) if t >= ts]
    pts = []
    for j in done:
        x, y = SLOTS[j]
        k = pop(t, E.STAMPS[j] + 0.1, 0.5)
        rot = (-0.08, 0.06, -0.05, 0.07, -0.06)[j]
        put(cv, polaroid(j), x, y + 6 * math.sin(t * 1.3 + j), k, 1.0, rot)
        put(cv, keyed('check', w=70), x + 55, y + 50, pop(t, E.STAMPS[j] + 0.3, 0.4), 1.0, -0.2)
        pts.append((x, y - 70))
    nxt = len(done)                                      # следующая улика — пустой полароид с «?» (доска не пустует)
    if 0 < nxt < 5 and t < E.MEMO:
        x, y = SLOTS[nxt]
        k = appear(t, E.STAMPS[nxt - 1] + 0.6, 0.4)
        put(cv, keyed('polaroid', w=150), x, y + 6 * math.sin(t * 1.5), 1.0, 0.75 * k, 0.04)
        put(cv, keyed('emo_quest', h=80), x, y - 14 + 6 * math.sin(t * 1.5), 1.0, 0.85 * k, 0.1 * math.sin(t * 2))
    if len(pts) > 1:                                     # красная нить между уликами
        def string(d, mp, S):
            q = [mp(x, y) for x, y in pts]
            d.line(q, fill=(200, 30, 36, 255), width=int(5 * S))
            for X, Y in q:
                d.ellipse((X - 9 * S, Y - 9 * S, X + 9 * S, Y + 9 * S), fill=(220, 40, 40, 255))
        fx.over(cv, fx.draw_rgba((100, 280, 1060, 460), string))
    # счётчик схем 1–5
    if t >= E.COUNTER_IN:
        cur = None
        for j, ts in enumerate(E.SCHEME_T):
            if t >= ts:
                cur = j
        for j in range(5):
            x = 220 + j * 160
            k = pop(t, E.COUNTER_IN + 0.08 * j, 0.45)
            lit = cur == j and t < E.STAMPS[j]
            if lit:
                pulse = 1 + 0.06 * math.sin(t * 6)
                put(cv, radial(128, GOLD), x, COUNTER_Y, 1.2 * pulse, 0.6)
                put(cv, keyed('badge_on', w=104), x, COUNTER_Y, k * pulse)
                put(cv, utext(str(j + 1), 46, 'ExtraBold', (255, 230, 140)), x, COUNTER_Y + 2, k * pulse)
            else:
                put(cv, keyed('badge_off', w=90), x, COUNTER_Y, k, 0.95)
                put(cv, utext(str(j + 1), 38, 'ExtraBold', (170, 170, 180)), x, COUNTER_Y + 2, k, 0.95)
                if t >= E.STAMPS[j]:
                    put(cv, keyed('check', w=72), x + 18, COUNTER_Y - 6, pop(t, E.STAMPS[j], 0.35), 1.0, -0.15)


# ------------------------------------------------------------------ телефон с перепиской
@functools.lru_cache(None)
def phone_img():
    return keyed('phone', h=PHONE_H)


def phone_box():
    im = phone_img()
    s = PHONE_H / 811
    x0 = PX - im.width / 2
    y0 = PHONE_Y - im.height / 2
    return x0 + 18 * s, y0 + 40 * s, x0 + 375 * s, y0 + 790 * s


@functools.lru_cache(maxsize=128)
def bubble(text, side, size=24, tcol=INK):
    """Пузырь чата по ширине текста (3-срез из картинки автора), с переносом строк."""
    f = ufont('SemiBold', size)
    words = text.split()
    lines, cur = [], ''
    for w in words:
        if f.getlength((cur + ' ' + w).strip()) > 280:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    lines.append(cur)
    tw = int(max(f.getlength(l) for l in lines))
    lh = int(size * 1.35)
    bw, bh = tw + 56, lh * len(lines) + 34
    src = keyed('bubble_in' if side == 'in' else 'bubble_out')
    sh = src.height
    sc = bh / sh
    s2 = src.resize((round(src.width * sc), bh), Image.LANCZOS)
    cap = int(bh * 0.6)
    left, right = s2.crop((0, 0, cap, bh)), s2.crop((s2.width - cap, 0, s2.width, bh))
    mid = s2.crop((cap, 0, cap + 4, bh)).resize((max(1, bw - 2 * cap), bh))
    im = Image.new('RGBA', (max(bw, 2 * cap + 1), bh), (0, 0, 0, 0))
    im.alpha_composite(left, (0, 0))
    im.alpha_composite(mid, (cap, 0))
    im.alpha_composite(right, (im.width - cap, 0))
    d = ImageDraw.Draw(im)
    for k, l in enumerate(lines):
        d.text((28 if side == 'in' else 24, 15 + k * lh), l, font=f, fill=tcol + (255,))
    return im


def chat(cv, t, a, title, avatar, msgs, typing=None):
    """msgs: [(t0, 'in'|'out'|'sys', текст)]. avatar: 'fox' | 'friend' | 'mita' | 'tg'."""
    if a <= 0:
        return
    put(cv, fx.soft_shadow(380, 820, 60, 26, 0.35), PX + 10, PHONE_Y + 18, 1.0, a)
    put(cv, phone_img(), PX, PHONE_Y, 1.0, a, 0.02 * (PX - round(PX / 10) * 10))
    x0, y0, x1, y1 = phone_box()
    # шапка чата
    def head(d, mp, S):
        X0, Y0 = mp(x0, y0 + 10)
        X1, Y1 = mp(x1, y0 + 92)
        d.rectangle((X0, Y0, X1, Y1), fill=(246, 248, 252, 255))
        d.line((X0, Y1, X1, Y1), fill=(220, 224, 232, 255), width=int(2 * S))
    fx.over(cv, fx.draw_rgba((x0, y0, x1, y0 + 100), head), a)
    av = {'fox': keyed('fox_head', w=62), 'tg': keyed('offer_card', w=1) if False else None}.get(avatar)
    ax, ay = x0 + 48, y0 + 52
    if avatar == 'fox':
        put(cv, keyed('fox_head', w=62), ax, ay, 1.0, a)
    elif avatar in ('friend', 'mita'):
        col = (90, 150, 230) if avatar == 'friend' else (60, 70, 140)
        def circ(d, mp, S):
            X, Y = mp(ax, ay)
            d.ellipse((X - 28 * S, Y - 28 * S, X + 28 * S, Y + 28 * S), fill=col + (255,))
        fx.over(cv, fx.draw_rgba((ax - 32, ay - 32, ax + 32, ay + 32), circ), a)
        put(cv, utext('Д' if avatar == 'friend' else 'М', 28, 'ExtraBold', WHITE), ax, ay + 1, 1.0, a)
    elif avatar == 'tg':
        def circ(d, mp, S):
            X, Y = mp(ax, ay)
            d.ellipse((X - 28 * S, Y - 28 * S, X + 28 * S, Y + 28 * S), fill=BLUE + (255,))
            d.polygon([(X - 14 * S, Y + 2 * S), (X + 14 * S, Y - 12 * S), (X + 4 * S, Y + 14 * S)], fill=(255, 255, 255, 255))
        fx.over(cv, fx.draw_rgba((ax - 32, ay - 32, ax + 32, ay + 32), circ), a)
    put(cv, utext(title, 24, 'ExtraBold', INK), ax + 40, ay, 1.0, a, anchor=None) if False else None
    tim = utext(title, 26, 'ExtraBold', INK)
    if tim.width > (x1 - ax - 60):
        tim = utext(title, 20, 'ExtraBold', INK)
    put(cv, tim, ax + 44 + tim.width / 2, ay, 1.0, a)
    # сообщения снизу вверх (последнее — внизу)
    shown = [m for m in msgs if t >= m[0]]
    y = y1 - 30
    items = []
    if typing is not None and t >= typing and (not shown or shown[-1][0] < typing):
        items.append(('typing', None, typing))
    for t0, side, text in reversed(shown):
        items.append((side, text, t0))
    for side, text, t0 in items:
        if side == 'typing':
            im = bubble('• • •', 'in', 32, (120, 120, 140))
        elif side == 'sys':
            im = pill(text, (150, 150, 165), 20)
        else:
            im = bubble(text, side, 34, INK if side == 'in' else (20, 40, 90))
        if y - im.height < y0 + 110:
            break
        k = pop(t, t0, 0.35)
        cx = x0 + 14 + im.width / 2 if side in ('in', 'typing') else (x1 - 14 - im.width / 2 if side == 'out' else (x0 + x1) / 2)
        put(cv, im, cx, y - im.height / 2, 0.85 + 0.15 * k, a * min(1.0, (t - t0) * 6 + 0.01))
        y -= im.height + 14


def stamp_scam(cv, t, ts, x, y, word='СКАМ!', sc=1.0):
    """Штамп с ударом: падает и «впечатывается», рамка автора + слово."""
    u = (t - ts) / 0.18
    if u < -1 or t > ts + 1.6:
        return
    a = 1 - ease((t - ts - 1.2) / 0.4)
    s = (1.8 - 0.8 * ease(u) if u < 1 else 1.0) * sc
    if u < 0:
        return
    fr = keyed('stamp_frame', w=330)
    put(cv, fr, x, y, s, a, -0.12)
    put(cv, utext(word, 64, 'ExtraBold', RED), x, y, s, a, -0.12)
    if 0 <= u < 1.5:
        cv[..., :3] *= 1 - 0.05 * math.sin(math.pi * min(1, u))


# ------------------------------------------------------------------ сцены
def scene_hook(cv, t):
    if t >= E.OFFER + 0.3:
        return
    return                                                  # v4: телефона нет


def speech_card(cv, t, t0, a, x, y):
    """Облачко мошенницы №1: карточка оффера «500 TON ≈ 43 000 ₽» (картинка автора + текст кодом)."""
    k = pop(t, t0, 0.5)
    card = keyed('offer_card', w=340)
    yy = y + 6 * math.sin(t * 2.2)
    put(cv, card, x, yy, k, a, 0.03)
    put(cv, utext('Вам предложили', 21, 'ExtraBold', INK), x + 18, yy - 66, k, a, 0.03)
    put(cv, utext('500 TON', 40, 'ExtraBold', BLUE), x, yy - 14, k, a, 0.03)
    put(cv, utext(rub(500), 28, 'ExtraBold', (60, 60, 90)), x, yy + 32, k, a, 0.03)
    put(cv, utext('ПРИНЯТЬ', 23, 'ExtraBold', WHITE), x, yy + 104, k, a, 0.03)


def scene_offer(cv, t):
    if not (E.OFFER_SAY - 0.2 <= t < E.STAMP1 + 1.4):
        return
    tc = E.OFFER_SAY + 0.25
    a = appear(t, tc, 0.25) * (1 - appear(t, E.STAMP1 + 0.4, 0.4))
    if t >= tc:
        speech_card(cv, t, tc, a, S.SR - 10, 520)
    # «смени язык»: настоящее переводится, фейк — нет (над детективом)
    if t >= E.LANG:
        la = appear(t, E.LANG, 0.3) * (1 - appear(t, E.STAMP1 + 0.2, 0.35))
        cx = S.DL + 60
        put(cv, pill('ЯЗЫК → English', (60, 70, 100), 28), cx, 470, pop(t, E.LANG, 0.4), la)
        rk = appear(t, E.REAL, 0.3) * la
        if rk > 0:
            put(cv, pill('НАСТОЯЩЕЕ → EN ✓', (40, 150, 90), 28), cx, 550, pop(t, E.REAL, 0.4), rk)
        fk = appear(t, E.FAKE, 0.3) * la
        if fk > 0:
            put(cv, pill('ФЕЙК → НЕ МЕНЯЕТСЯ ✗', RED, 28), cx + 40, 630, pop(t, E.FAKE, 0.4), fk)
    stamp_scam(cv, t, E.STAMP1, S.SR - 70, 1060, 'ФЕЙК!', 0.82)


def scene_clone(cv, t):
    return                                                  # v4: переделать без телефона
    if not (E.CLONE - 0.1 <= t < E.CREEPY + 0.3):
        return
    a = appear(t, E.CLONE, 0.3) * (1 - appear(t, E.CREEPY - 0.1, 0.3))
    chat(cv, t, a, 'Дима (друг)', 'friend', [(E.FRIEND_MSG, 'in', 'Дай подарок на минутку?')], typing=E.CLONE + 0.3)
    x0, y0, x1, y1 = phone_box()
    cx, cy = (x0 + x1) / 2, y0 + 300
    fl = ease((t - E.FOX_FLIP) / 0.45)
    sx = abs(math.cos(math.pi * fl))
    k = pop(t, E.CLONE + 0.2, 0.5)
    if fl < 0.5:
        fx.over(cv, fx.warp(avatar_disc(), cx, cy, sx * k, k), a)
        fx.over(cv, fx.warp(utext('Д', 130, 'ExtraBold', WHITE), cx, cy + 4, sx * k, k), a)
        put(cv, pill('ДИМА', (60, 90, 160), 26), cx, cy + 160, k, a)
    else:
        fx.over(cv, fx.warp(keyed('fox_head', w=260), cx, cy, sx, 1.0), a)
        put(cv, pill('КЛОН!', RED, 30), cx, cy + 160, pop(t, E.FOX_FLIP + 0.3), a)
    if t >= E.ASK:
        put(cv, keyed('emo_bulb', w=100), cx + 150, cy - 120, pop(t, E.ASK), a)
    if t >= E.STAMP2:                                      # вердикт — красный крест маркером
        u = ease((t - E.STAMP2) / 0.3)
        put(cv, keyed('cross', h=300), cx, cy, 1.3 - 0.3 * u, a * u, -0.05)


def scene_creepy(cv, t):
    ck = creepy_k(t)
    if ck <= 0:
        return
    cv[..., :3] *= (1 - 0.7 * ck)
    cv[..., 2] += 16 * ck
    yy = np.linspace(-1, 1, H)[:, None]
    xx = np.linspace(-1, 1, W)[None, :]
    vig = np.clip(np.sqrt(xx ** 2 * 0.8 + yy ** 2 * 0.6) - 0.4, 0, 1)[..., None]
    cv[..., :3] *= 1 - 0.7 * ck * vig
    # крупный план: лицо Миты медленно приближается (единственный наезд в ролике)
    z = 1.0 + 1.3 * ease((t - E.CREEPY - 0.2) / (E.CREEPY_END - E.CREEPY - 0.6))
    for name, k in M.creep_frames(t):
        im, anc = M.still(name)
        fx_ = anc[0]
        head_y = anc[1] - M.DET_H * 0.86                     # точка у лица
        put(cv, im, 540, 760, z, ck * k, anchor=(fx_, head_y))
    # «ЭТО Я» проступает на весь экран
    rng = np.random.default_rng(3)
    for j in range(7):
        tj = E.CREEPY + 0.5 + j * 0.55
        u = (t - tj)
        if u < 0:
            continue
        aj = ck * min(1, u * 3) * (0.25 + 0.2 * (j % 3))
        x = rng.uniform(170, 910)
        y = rng.uniform(260, 1450)
        sz = int(rng.uniform(70, 130))
        put(cv, utext('ЭТО Я', sz, 'ExtraBold', (230, 60, 60)), x + 3 * math.sin(t * 40 + j), y, 1.0, aj, rng.uniform(-0.25, 0.25))
    put(cv, utext('ТЫ УВЕРЕН?', 92, 'ExtraBold', (255, 235, 235), 5, (120, 20, 20)), 540, 1380,
        pop(t, E.CREEPY_END - 1.6, 0.4), ck * appear(t, E.CREEPY_END - 1.6, 0.2))


def scene_tease(cv, t):
    if not (E.CREEPY_END - 0.1 <= t < AD_STOP + 0.1):
        return
    a = appear(t, E.CREEPY_END, 0.3)
    chat(cv, t, a, 'Покупатель', 'fox', [], typing=E.TEASE + 0.2)
    x0, y0, x1, y1 = phone_box()
    put(cv, keyed('emo_siren', w=130), (x0 + x1) / 2, y0 + 330, pop(t, E.TEASE + 0.5), a, 0.1 * math.sin(t * 8))
    put(cv, pill('САМАЯ ХИТРАЯ…', (60, 70, 100), 26), (x0 + x1) / 2, y0 + 470, pop(t, E.TEASE + 0.9), a)


def scene_link(cv, t):
    return                                                  # v4: переделать без телефона
    if not (E.LINK - 0.1 <= t < E.SWAP + 0.3):
        return
    a = appear(t, E.LINK, 0.3) * (1 - appear(t, E.SWAP - 0.1, 0.3))
    chat(cv, t, a, 'Покупатель', 'fox', [(E.LINK_MSG, 'in', 'Выстави NFT вот тут: fragrnent.com')], typing=E.LINK + 0.2)
    x0, y0, x1, y1 = phone_box()
    if t >= E.LINK_LENS:
        la = appear(t, E.LINK_LENS, 0.3) * a
        cx, cy = (x0 + x1) / 2, y0 + 300
        put(cv, keyed('addr_bar', w=340), cx, cy - 60, pop(t, E.LINK_LENS, 0.4), la)
        put(cv, utext('fragrnent.com', 30, 'ExtraBold', INK), cx + 10, cy - 62, pop(t, E.LINK_LENS, 0.4), la)
        put(cv, keyed('emo_glint', w=150), cx + 40, cy + 70, pop(t, E.LINK_LENS + 0.4, 0.4), la)
        put(cv, pill('rn ≠ m', RED, 30), cx - 70, cy + 70, pop(t, E.LINK_LENS + 0.7), la, -0.06)
        put(cv, pill('НЕ ПЕРЕХОДИ!', RED, 24), cx, cy + 170, pop(t, E.LINK_LENS + 1.2), la)
    stamp_scam(cv, t, E.STAMP3, (x0 + x1) / 2, y0 + 300, 'ФЕЙК!')


def scene_swap(cv, t):
    return                                                  # v4: переделать без телефона
    if not (E.SWAP - 0.1 <= t < E.GUAR + 0.3):
        return
    a = appear(t, E.SWAP, 0.3) * (1 - appear(t, E.GUAR - 0.1, 0.3))
    chat(cv, t, a, 'Покупатель', 'fox', [(E.SWAP_MSG, 'in', 'Меняемся? Только ты первый!')], typing=E.SWAP + 0.2)
    x0, y0, x1, y1 = phone_box()
    cx, cy = (x0 + x1) / 2, y0 + 310
    k = pop(t, E.SWAP + 0.3, 0.5)
    tear = ease((t - E.STAMP4) / 0.5)
    l, r = keyed('torn_l', h=300), keyed('torn_r', h=300)
    put(cv, l, cx - l.width / 2 - 60 * tear, cy + 40 * tear, k, a, -0.25 * tear)
    put(cv, r, cx + r.width / 2 + 60 * tear, cy + 60 * tear, k, a, 0.3 * tear)
    put(cv, utext('ОБМЕН', 40, 'ExtraBold', INK), cx - 60 * tear, cy - 40 + 40 * tear, k, a * (1 - tear))
    put(cv, utext('ТЫ ПЕРВЫЙ', 30, 'ExtraBold', RED), cx, cy + 20, k, a * (1 - tear))
    if E.SWAP_SENT <= t < E.SWAP_SENT + 1.2:              # подарок улетает
        u = (t - E.SWAP_SENT) / 1.2
        put(cv, keyed('emo_poof', w=120), cx + 120 * u, cy - 200 - 300 * u, 0.6 + 0.8 * u, a * (1 - u))
    if t >= E.STAMP4:
        put(cv, pill('СОБЕСЕДНИК ИСЧЕЗ', RED, 26), cx, cy + 230, pop(t, E.STAMP4 + 0.2), a)


def scene_guar(cv, t):
    return                                                  # v4: переделать без телефона
    if not (E.GUAR - 0.1 <= t < E.MEMO + 0.3):
        return
    a = appear(t, E.GUAR, 0.3) * (1 - appear(t, E.MEMO - 0.1, 0.3))
    chat(cv, t, a, '@garant_official', 'friend', [(E.GUAR_MSG, 'in', 'Не бойся, я гарант!')], typing=E.GUAR + 0.1)
    x0, y0, x1, y1 = phone_box()
    cx, cy = (x0 + x1) / 2, y0 + 290
    off = ease((t - E.GUAR_FOX) / 0.5)
    put(cv, keyed('fox_head', w=230), cx, cy, pop(t, E.GUAR + 0.2, 0.5), a * max(0.0, off))
    if off < 1:
        put(cv, pill('ГАРАНТ ✓', (40, 150, 90), 40), cx + 260 * off, cy - 200 * off, 1.0, a * (1 - off), 0.8 * off)
    if t >= E.GUAR_SAFE:
        sa = appear(t, E.GUAR_SAFE, 0.3) * a
        put(cv, pill('ТОЛЬКО МАРКЕТ TELEGRAM ✓', (40, 120, 210), 22), cx, cy + 210, pop(t, E.GUAR_SAFE, 0.45), sa)
    stamp_scam(cv, t, E.STAMP5, cx, cy, 'ФЕЙК!')


@functools.lru_cache(maxsize=4)
def note_col(k):
    im = np.array(keyed('note', w=330)).astype(np.float32)
    tint = [(1.0, 1.0, 1.0), (1.06, 1.06, 1.25), (0.85, 0.97, 1.3)][k]
    im[..., :3] = np.clip(im[..., :3] * np.array(tint), 0, 255)
    return Image.fromarray(im.astype(np.uint8))


MEMO_MASK = np.clip((900 - np.arange(H, dtype=np.float32)) / 120, 0, 1)[:, None, None]   # мягкий нижний край


def memo_wash(cv, t):
    """Доска «уходит» под цвет стены — рисуется ДО Миты, чтобы не бледнить её."""
    if not (E.MEMO - 0.1 <= t < E.MOVE2 + 0.3):
        return
    a = appear(t, E.MEMO, 0.35) * (1 - appear(t, E.MOVE2, 0.3))
    wall = np.array([236, 226, 214], np.float32)
    k = 0.85 * a * MEMO_MASK
    cv[..., :3] = cv[..., :3] * (1 - k) + wall * k


def scene_memo(cv, t):
    if not (E.MEMO - 0.1 <= t < E.MOVE2 + 0.3):
        return
    a = appear(t, E.MEMO, 0.35) * (1 - appear(t, E.MOVE2, 0.3))
    put(cv, pill('ЗАПОМНИ', (60, 50, 50), 40), 540, 150, pop(t, E.MEMO, 0.5), a)
    items = ((E.NOTE1, ('ПОДАРОК', 'ПЕРВЫМ', 'НЕ ОТПРАВЛЯЙ'), 'emo_excl'), (E.NOTE2, ('НА СЛОВО', 'НЕ ВЕРЬ'), 'emo_anger'),
             (E.NOTE3, ('ТОЛЬКО', 'ПРОВЕРЕННЫЕ', 'МАРКЕТЫ'), 'emo_bulb'))
    pos = [(360, 470), (760, 520), (760, 950)]
    for k, (tn, lines, ico) in enumerate(items):
        ka = appear(t, tn, 0.25) * a
        if ka <= 0:
            continue
        x, y = pos[k]
        rot = (-0.06, 0.05, -0.04)[k]
        p = pop(t, tn, 0.45)
        put(cv, note_col(k), x, y, p, ka, rot)
        for li, line in enumerate(lines):
            put(cv, utext(line, 34, 'ExtraBold', INK), x, y - 20 * (len(lines) - 1) + li * 46 + 20, p, ka, rot)
        put(cv, keyed(ico, w=70), x + 130, y - 120, p, ka)


@functools.lru_cache(None)
def folders():
    im = keyed('folders')
    w = im.width
    return im.crop((0, 0, w // 2, im.height)), im.crop((w // 2, 0, w, im.height))


def scene_choice(cv, t):
    if t < E.MOVE2 + 0.2:
        return
    lt = t - E.MOVE2
    l, r = folders()
    for side, (im, word, t_on, x) in enumerate(((l, 'БЫЛО', 0.6, 175), (r, 'НЕ БЫЛО', 1.8, 905))):
        a = appear(lt, t_on - 0.3, 0.4)
        if a <= 0:
            continue
        y = 1080 + 10 * math.sin(t * 2 + side)
        img = im.resize((230, round(im.height * 230 / im.width)), Image.LANCZOS)
        put(cv, radial(256, (255, 220, 140) if side == 0 else (170, 200, 255)), x, y, 1.6, 0.35 * a)
        put(cv, img, x, y, pop(lt, t_on - 0.3, 0.5), a, (-0.06 if side == 0 else 0.06))
        put(cv, utext(word, 28 if side == 0 else 24, 'ExtraBold', INK), x + (-4 if side == 0 else 6), y - 52, pop(lt, t_on - 0.1), a,
            (-0.06 if side == 0 else 0.06))
    put(cv, pill('ПИШИ В КОММЕНТАРИЯХ!', (190, 130, 40), 28), 540, 620, pop(t, E.CHOICE + 0.3), appear(t, E.CHOICE + 0.3, 0.2))


# ------------------------------------------------------------------ лиса-пасхалка выглядывает из-за края
FOX_PEEK = [35.6]                 # v4: справа/слева теперь заходят мошенницы — лиса выглядывает только на крючке


def fox_peek(cv, t):
    for k, t0 in enumerate(FOX_PEEK):
        u = (t - t0) / 3.0
        if not 0 <= u < 1:
            continue
        o = math.sin(math.pi * u) ** 0.6
        im = keyed('fox_head', w=150)
        side = k % 2
        x = (W + 50 - 120 * o) if side == 0 else (-50 + 120 * o)
        put(cv, im, x, 560 + k * 40, 1.0, 1.0, (0.5 if side == 0 else -0.5))


# ------------------------------------------------------------------ эмоции над головой
REACT = [(E.HOOK_MSG + 0.3, 'quest'), (E.LENS1, 'sparkle'), (E.OFFER_SAY_END + 0.1, 'quest'), (E.LANG + 0.2, 'bulb'),
         (E.FAKE + 0.2, 'excl'), (E.CLONE_SAY_END + 0.1, 'sweat'), (E.ASK + 0.1, 'bulb'), (E.TEASE + 0.3, 'excl'),
         (E.LINK_LENS + 0.6, 'glint'), (E.SWAP_SAY_END + 0.1, 'anger'), (E.GUAR_FOX + 0.1, 'anger'), (E.NOTE1, 'bulb'),
         (E.CHOICE, 'sparkle')]


def reactions(cv, t):
    for t0, kind in REACT:
        k = t - t0
        if not 0 <= k < 1.4:
            continue
        a = min(1.0, k * 6) * (1 - fx.clamp01((k - 1.0) / 0.4))
        p = fx.ease_out_back(fx.clamp01(k / 0.35))
        x0 = S.det_x(t)
        head = M.FOOT - M.DET_H
        x, y = x0 + 150, head + 20 - 40 * ease(k / 1.4)
        if kind == 'sweat':
            x, y = x0 + 95, head + 110
        put(cv, keyed(f'emo_{kind}', h=100), x, y, 0.6 + 0.4 * p, a, 0.12 * math.sin(k * 6))


# ------------------------------------------------------------------ перевоплощение: лупа
@functools.lru_cache(None)
def lens_big():
    im = keyed('lens')
    s = 0.62
    im2 = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    full = Image.open(KEYED / 'lens.png')
    bb = full.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox()
    gcx, gcy, gr = (505 - bb[0]) * s, (403 - bb[1]) * s, 286 * s
    return im2, (gcx, gcy, gr, 1.0)


def mita_shadow(cv, x, y):
    def draw(d, mp, S):
        X, Y = mp(x, y + 2)
        d.ellipse([X - 150 * S, Y - 18 * S, X + 150 * S, Y + 18 * S], fill=(40, 30, 30, 70))
    fx.over(cv, fx.draw_rgba((x - 170, y - 30, x + 170, y + 30), draw))


# ------------------------------------------------------------------ субтитры
def _disp(w):
    return re.sub(r'[.,:;…!?]+$', '', w.replace('«', '').replace('»', ''))


def _chunks():
    out, cur = [], []
    for w in WORDS:
        if cur and (len(cur) >= 3 or cur[-1][3] != w[3] or sum(len(x[0]) for x in cur) + len(w[0]) > 20
                    or re.search(r'[.!?…:,—]$', cur[-1][0])):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


CHUNKS = _chunks()


def subtitles(cv, t):
    ch = None
    for k, c in enumerate(CHUNKS):
        t0 = c[0][1] - 0.06
        t1 = CHUNKS[k + 1][0][1] - 0.06 if k + 1 < len(CHUNKS) else c[-1][2] + 0.6
        t1 = min(t1, c[-1][2] + 0.7)
        if t0 <= t < t1:
            ch, start = c, t0
            break
    if ch is None:
        return
    acc = (200, 60, 60) if creepy_k(t) > 0.5 else ((60, 110, 220) if ch[0][3] in script.SCAM else (196, 140, 30))
    parts = []
    for j, w in enumerate(ch):
        on = w[1] - 0.03 <= t
        col = acc if (on and (j == len(ch) - 1 or t < ch[j + 1][1] - 0.03)) else (INK if on else (160, 156, 166))
        parts.append(((' ' if j else '') + _disp(w[0]).upper(), col))
    im = multi(tuple(parts), 54, 'Heavy')
    sc = min(1.0, 980 / im.width)
    p = fx.ease_out_back(fx.clamp01((t - start) / 0.22))
    pw = int(im.width * sc) + 44
    put(cv, fx.rounded(pw, 84, 30, (255, 252, 244, 240), (226, 214, 190, 255), 3), 540, SUB_Y, 0.85 + 0.15 * p, 1.0)
    put(cv, im, 540, SUB_Y, sc * (0.85 + 0.15 * p), 1.0)


# ------------------------------------------------------------------ кадр
def render_at(t):
    cv = background(t)
    board(cv, t)
    fox_peek(cv, t)
    memo_wash(cv, t)
    if t != AD_STOP:
        if E.LENS0 <= t < E.LENS1:
            mita_shadow(cv, M.LENS_X, M.FOOT)
            lim, geom = lens_big()
            M.lens_reveal(cv, t, put, lim, geom)
        else:
            if not (E.CREEPY + 0.3 <= t < E.CREEPY_END - 0.3):
                S.draw(cv, t, put, mita_shadow if creepy_k(t) < 0.5 else None)
            if E.LENS1 <= t < E.LENS1 + 0.6:              # лупа «уменьшается» и прыгает в руку + дымка
                u = (t - E.LENS1) / 0.6
                put(cv, keyed('shimmer', w=420), M.LENS_X, M.FOOT - 380, 0.8 + 0.6 * u, 1 - u)
    scene_creepy(cv, t)
    scene_hook(cv, t)
    scene_offer(cv, t)
    scene_clone(cv, t)
    scene_tease(cv, t)
    scene_link(cv, t)
    scene_swap(cv, t)
    scene_guar(cv, t)
    scene_memo(cv, t)
    scene_choice(cv, t)
    if creepy_k(t) < 0.5:
        reactions(cv, t)
    if not (AD_STOP - 0.02 <= t < AD_STOP + 0.1):
        subtitles(cv, t)
    return np.clip(cv[..., :3], 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ реклама: Мита изучает дело, под баннером крадётся лиса
BAN_TOP = int(H / 2 - 283)
BAN_BOT = int(H / 2 + 284)


@functools.lru_cache(maxsize=300)
def fox_frame(idx, h):
    im = Image.open(HERE / 'build' / 'clips' / 'fox' / f'f{idx + 1:04d}.png')
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 30 else 0).getbbox() or (0, 0, im.width, im.height))
    return im.resize((round(im.width * h / im.height), h), Image.BILINEAR)


def ad_overlay(c, t):
    ph = BR.phase(t)
    if ph is None:
        return c
    a, bt = ph['dim'], ph['bt']
    cv = np.dstack([c.astype(np.float32), np.full(c.shape[:2], 255, np.float32)])
    M.draw_ad(cv, bt, put, a, 540, BAN_TOP - 10, 560)
    put(cv, keyed('emo_quest', h=90), 700, BAN_TOP - 520, pop(bt, 1.2), a, 0.15)
    B = BR.B
    u = fx.clamp01((bt + 0.2) / max(1.0, B + 0.2))
    fh = 400
    x = -200 + (W + 400) * u
    y = BAN_BOT + 40 + fh / 2 + 10 * math.sin(bt * 5)
    idx = int((bt + 1.0) * 24) % 240
    put(cv, fox_frame(idx, fh), x, y, 1.0, a)
    return cv[..., :3]


TOTAL = BR.out_dur(DUR)
LOOP_D = 0.5


def case_closed(img, t):
    """Петля: в конце штамп «ДЕЛО ЗАКРЫТО» падает на экран, в начале — снимается."""
    k_end = (t - (TOTAL - 0.9)) / 0.25
    k_start = 1 - t / LOOP_D
    if k_end < 0 and k_start <= 0:
        return img
    cv = np.dstack([img.astype(np.float32), np.full(img.shape[:2], 255, np.float32)])
    if k_end >= 0:
        s = 2.0 - ease(min(1, k_end))
        a = 1.0
    else:
        s, a = 1.0 + 0.4 * (1 - k_start), k_start
    cv[..., :3] *= 1 - 0.35 * a
    put(cv, keyed('stamp_round', w=620), 540, 900, s, a, -0.12)
    put(cv, utext('ДЕЛО', 64, 'ExtraBold', RED), 540, 860, s, a, -0.12)
    put(cv, utext('ЗАКРЫТО', 64, 'ExtraBold', RED), 540, 950, s, a, -0.12)
    return cv[..., :3]


def out_frame(t, i=None):
    img = ad_overlay(BR.render(render_at, t, i).astype(np.float32), t)
    img = case_closed(img, t)
    return np.clip(img, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return out_frame(i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--content' in sys.argv or '--out' in sys.argv:
        out = paths.build(HERE) / 'review'
        out.mkdir(parents=True, exist_ok=True)
        key = '--content' if '--content' in sys.argv else '--out'
        fn = render_at if key == '--content' else out_frame
        for s in sys.argv[sys.argv.index(key) + 1].split(','):
            Image.fromarray(fn(float(s))).save(out / f'{key[2]}{float(s):06.2f}.png')
            print(key, s)
        raise SystemExit
    frames.cli(out_frame, frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
