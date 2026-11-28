"""Рендер «Ещё одно видео» (всё кодом). Спальня и кресло — из серии 1 (65), сканер/плашки/улица — из «Холодильника» (66).

    python -B render.py --frames 2.8,6,10,14,20,24,26,28,33,37,40,44,48,53
    python -B render.py --prewarm
    python -B render.py --build missed_one_more_v1.mp4
"""
import importlib.util
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(ROOT / 'engine'))
sys.path.append(str(ROOT / 'projects' / '65-missed-alien'))       # art.py
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402
import events as E  # noqa: E402
from timeline import T, V, D, DUR  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R65 = _load('r65', ROOT / 'projects' / '65-missed-alien' / 'render.py')     # комната, кресло, кровать, телефон
R66 = _load('r66', ROOT / 'projects' / '66-missed-fridge' / 'render.py')    # текст, плашки, спрайты, улица, НЛО
cl, eo, eio, spring, lerp = R66.cl, R66.eo, R66.eio, R66.spring, R66.lerp
font, text_c, chip, wrap, flash, scaled, put = R66.font, R66.text_c, R66.chip, R66.wrap, R66.flash, R66.scaled, R66.put

W, H, FPS = 1080, 1920, 60
ARTEM = dict(hood=[150, 90, 220], hair=[45, 32, 30])
GIFT = G.original_file('Hanging Star', 'tgs')
CHAIR_X = R65.CHAIR_X


def _env():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(HERE / 'build' / 'review' / 'voice_only.mp3'),
                          '-f', 'f32le', '-ac', '1', '-ar', '6000', '-'], capture_output=True, check=True).stdout
    a = np.abs(np.frombuffer(raw, np.float32))
    hop = 6000 // FPS
    n = len(a) // hop
    e = a[:n * hop].reshape(n, hop).mean(1)
    return e / (e.max() + 1e-9)


ENV = _env()


def mouth_open(who, t):
    for k, t0 in V.items():
        if (k[0] in 'MIO') == (who == 'M') and t0 <= t < t0 + D[k]:
            i = int(t * FPS)
            v = ENV[i] if i < len(ENV) else 0
            return 2 if v > 0.22 else 1 if v > 0.08 else 0
    return 0


SUBS = {
    'M1': 'Объект: Артём. Шестнадцать лет. Говорит, что ложится спать.', 'A1': 'Всё, ещё одно видео — и сплю.',
    'M2': 'Это было сорок минут назад.', 'A2': 'Ну это не считается, оно короткое было.', 'M3': 'Они все короткие.',
    'A3': 'Вот именно! Значит, можно ещё одно.', 'M4': 'Записываю: короткое видео длится вечно.',
    'A4': 'Ай! …Ладно, последнее.', 'M5': 'Ты говоришь «последнее» сорок седьмой раз.',
    'A5': 'А вдруг там что-то важное?', 'M6': 'Например?', 'A6': '…Кот, который боится огурца.', 'M7': '…Важно.',
    'M8': 'Держи. Звёздочка — чтобы помнил, что сейчас ночь.', 'A7': 'Спасибо! Сейчас только сторис про неё выложу…',
    'O1': 'С этим землянином всё ясно. Дальше — Макс.'}


def subtitles(im, t):
    for k, t0 in V.items():
        if k not in SUBS or not (t0 - 0.05 <= t < t0 + D[k] + 0.25):
            continue
        size = 64
        lines = wrap(SUBS[k], font('Heavy', size), 800)
        col = (255, 196, 222, 255) if k[0] in 'MO' else (255, 255, 255, 255)
        a = cl((t - t0 + 0.05) / 0.12)
        y0 = 1120 if k == 'O1' else 1385 - len(lines) * (size + 10)
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        for i, ln in enumerate(lines):
            text_c(lay, ln, W / 2, y0 + i * (size + 10) + (1 - eo(a)) * 18, size, fill=col)
        if a < 1:
            lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)


# ------------------------------------------------------------------ персонажи
def missed_pose(t, arm='mug'):
    m = mouth_open('M', t)
    p = dict(mouth='o' if m == 2 else 'flat' if m == 1 else 'smile', blink=1 if (t % 3.9) < 0.12 else 0, ear_l=0.0, ear_r=0.0)
    if arm:
        p['arm'] = arm
    return p


def draw_missed(im, t):
    lean = eio((t - E.LEAN[0]) / 0.45) * (1 - eio((t - E.LEAN[1]) / 0.4))
    arm = 'reach' if T['s5'] <= t < T['s6'] else 'mug'
    p = missed_pose(t, arm)
    if lean > 0.5:
        p.update(mouth='o' if mouth_open('M', t) else 'smile', ear_l=1.0, ear_r=1.0)
    sc = 0.44 + 0.06 * lean
    spr = scaled('missed', sc, 'night', flip=arm == 'reach', **p)
    x = CHAIR_X - 230 * lean
    put(im, spr, x, 1500 + math.sin(t * 2.2) * 3 - 60 * lean)
    if arm == 'mug' and lean < 0.3:
        writing = E.NOTE[0] <= t < E.NOTE[1]
        R66.notebook(im, x + 72 * sc + 12, 1500 - (1500 - 1240) * sc + 10, t, writing)


def artem_pose(t):
    talk = mouth_open('A', t)
    mouth = {2: 'open', 1: 'o'}.get(talk, 'smile')
    p = dict(arms='phone', eyes='open', mouth=mouth, look=0.0, **ARTEM)
    y_off, lying = 0.0, False
    if V['A2'] <= t < V['A3'] + D['A3']:
        p['look'] = 0.6
    c0, c1, c2 = T['cuts']
    if c0 <= t < c1:                                    # 00:30 — смеётся
        p.update(eyes='closed', mouth='open')
    elif c1 <= t < c2:                                  # 01:15 — глаза слипаются
        p.update(eyes='half', mouth='flat', brows='plead')
    elif c2 <= t < E.DROP + 0.05:                       # 02:40 — засыпает с телефоном над лицом
        p.update(eyes='half', mouth='sleep')
        lying = True
    elif E.DROP + 0.05 <= t < V['M5'] + D['M5']:
        p.update(eyes='wide', mouth=mouth if talk else 'o', brows='shout')
        lying = True
    if T['s4'] <= t < T['s5']:
        p.update(look=0.5, brows='plead' if t >= V['A6'] - 0.4 else '')
    if t >= T['gift']:
        p.update(arms='up', eyes='wide', mouth=mouth if talk else 'open', look=0.0)
    if t >= V['A7'] - 0.1:
        p.update(arms='phone', eyes='open', look=0.0, mouth=mouth if talk else 'smile')
    return p, lying


def draw_artem(im, t):
    p, lying = artem_pose(t)
    R65.pillow(im, 'night', 150, 1150)
    if lying:
        spr = scaled('human', 0.40, 'night', **p).rotate(80, expand=True, resample=Image.BICUBIC)
        im.alpha_composite(spr, (60, int(1215 - spr.height / 2)))
        # телефон над лицом → падает
        k = eio((t - E.DROP + 0.35) / 0.35)
        px, py = 315, lerp(1030, 1175, k)                 # лицо лежащего Артёма ≈ (315, 1200)
        if t >= E.DROP:
            py = 1175 + math.sin(min(1, (t - E.DROP) / 0.3) * math.pi) * -20
        R65.phone_small(im, px, py, rot=90, glow=True)
        if 0 <= t - E.DROP < 0.6:                       # звёздочки от удара
            u = (t - E.DROP) / 0.6
            d = ImageDraw.Draw(im)
            for j in range(5):
                a = j / 5 * 2 * math.pi + u * 4
                x, y = 315 + math.cos(a) * 90, 1110 + math.sin(a) * 30 - u * 30
                d.regular_polygon((x, y, 14 * (1 - u) + 4), 5, rotation=u * 200, fill=(255, 230, 90, int(255 * (1 - u))))
    else:
        spr = scaled('human', 0.40, 'night', **p)
        put(im, spr, 260, 1350 + math.sin(t * 2.0) * 2)
        if p['arms'] == 'phone':
            R65.phone_small(im, 260, 1205, glow=True)
    R65.blanket(im, 'night', 1330)


# ------------------------------------------------------------------ интерфейс
FEED = [((255, 120, 150), 'танец'), ((90, 200, 255), 'кот'), ((255, 200, 70), 'пранк'), ((140, 230, 140), 'лайфхак'),
        ((200, 140, 255), 'мем'), ((255, 150, 90), 'рецепт')]


def feed_card(im, t, a, cat=False):
    """Крупный экран телефона с лентой коротких видео; свайпы по E.SWIPES."""
    if a <= 0:
        return
    x0, y0, x1, y1 = 330, 360, 750, 1060
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0 - 14, y0 - 14, x1 + 14, y1 + 14), 56, fill=(20, 20, 28, 255))
    n = sum(t >= s for s in E.SWIPES)
    last = max([s for s in E.SWIPES if s <= t], default=-9)
    k = eo((t - last) / 0.2)
    scr = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 255))
    sd = ImageDraw.Draw(scr)
    hgt = y1 - y0
    for j, off in ((n - 1, -hgt * k), (n, hgt * (1 - k))):
        if j < 0:
            continue
        col, label = FEED[j % len(FEED)]
        top = int(off)
        sd.rectangle((0, top, x1 - x0, top + hgt), fill=col + (255,))
        if cat:
            continue
        sd.ellipse((110, top + 200, 310, top + 400), fill=(255, 255, 255, 120))
        sd.polygon([(185, top + 255), (185, top + 345), (255, top + 300)], fill=(255, 255, 255, 230))
        sd.text((30, top + hgt - 120), '@' + label, font=font('Heavy', 36), fill=(255, 255, 255, 255))
    if cat:                                             # кот боится огурца
        sd.rectangle((0, 0, x1 - x0, hgt), fill=(240, 225, 200, 255))
        jump = abs(math.sin(t * 6)) * 60
        cx, cy = 150, 420 - jump
        sd.ellipse((cx - 80, cy - 50, cx + 80, cy + 60), fill=(240, 150, 60, 255))
        sd.ellipse((cx + 40, cy - 110, cx + 140, cy - 10), fill=(240, 150, 60, 255))
        sd.polygon([(cx + 50, cy - 95), (cx + 65, cy - 145), (cx + 85, cy - 100)], fill=(240, 150, 60, 255))
        sd.polygon([(cx + 100, cy - 100), (cx + 120, cy - 150), (cx + 132, cy - 95)], fill=(240, 150, 60, 255))
        for ex in (cx + 75, cx + 108):
            sd.ellipse((ex - 9, cy - 75, ex + 9, cy - 55), fill=(30, 30, 30, 255))
        sd.text((cx + 20, cy - 190), '!!', font=font('Heavy', 60), fill=(230, 50, 60, 255))
        sd.rounded_rectangle((250, 520, 400, 565), 22, fill=(70, 170, 70, 255))
        for j in range(5):
            sd.ellipse((262 + j * 26, 532, 270 + j * 26, 540), fill=(140, 220, 140, 255))
        sd.text((30, hgt - 120), '@кот_vs_огурец', font=font('Heavy', 34), fill=(60, 40, 30, 255))
    # правая панель: лайки
    for j, yy in enumerate((380, 470, 560)):
        sd.ellipse((x1 - x0 - 80, yy, x1 - x0 - 30, yy + 50), fill=(255, 255, 255, 200))
    mask = Image.new('L', scr.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, scr.width - 1, scr.height - 1), 44, fill=255)
    lay.paste(scr, (x0, y0), mask)
    if a < 1:
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(lay)


def clock_chip(im, t):
    txt, t0 = None, 0
    for s, tt in E.CLOCKS:
        if t >= tt:
            txt, t0 = s, tt
    if E.SPIN[0] <= t < E.SPIN[1]:                       # тайм-лапс 23:00 → 23:47
        mm = int(47 * eio((t - E.SPIN[0]) / (E.SPIN[1] - E.SPIN[0])))
        txt, t0 = f'23:{mm:02d}', t
    if txt is None or t >= T['s4'] or t < V['A1']:
        return
    late = txt[0] == '0'
    chip(im, txt, W / 2 - 170, 280, bg=(230, 60, 70, 240) if late else (40, 30, 70, 235), size=56,
         pop=spring(t - t0, 3, 0.4) if t - t0 < 1 and t0 != t else 1)


def counter(im, t):
    n, last = 0, 0
    for t0, c in E.COUNT:
        if t >= t0:
            n, last = c, t0
    if n and V['A1'] <= t < T['s4']:
        chip(im, f'ВИДЕО: {n}', W / 2 + 170, 280, bg=(255, 90, 160, 240), size=50,
             pop=spring(t - last, 3, 0.4) if t - last < 1 else 1)


def scanner(im, t):
    u = t - E.SCAN
    if not (0 <= u < V['M1'] + D['M1'] - E.SCAN + 0.4):
        return
    a = cl(u / 0.2) * (1 - cl((t - V['M1'] - D['M1']) / 0.4))
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = 60, 880, 470, 1420
    for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line((x, y, x + dx * 60, y), fill=(90, 255, 200, 255), width=8)
        d.line((x, y, x, y + dy * 60), fill=(90, 255, 200, 255), width=8)
    yy = y0 + ((u * 600) % (y1 - y0))
    d.line((x0 + 10, yy, x1 - 10, yy), fill=(90, 255, 200, 150), width=5)
    lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(lay)
    chip(im, 'ОБЪЕКТ: АРТЁМ, 16', W / 2, 300, bg=(10, 30, 30, 235), fg=(90, 255, 200, 255), size=48,
         pop=spring(u - 0.15, 3, 0.5) * a, outline=(90, 255, 200, 255))


def note_page(im, t):
    n0, n1 = E.NOTE
    if not (n0 <= t < n1 + 0.5):
        return
    k = spring(t - n0, 2.5, 0.55) * (1 - eio((t - n1) / 0.4))
    page = Image.new('RGBA', (600, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(page)
    d.rounded_rectangle((0, 0, 599, 329), 24, fill=(245, 238, 215, 250), outline=(140, 110, 80, 255), width=5)
    for j in range(5):
        d.line((30, 70 + j * 50, 570, 70 + j * 50), fill=(170, 190, 220, 255), width=2)
    d.line((80, 10, 80, 320), fill=(230, 120, 120, 255), width=3)
    d.text((100, 24), 'НАБЛЮДЕНИЕ №2', font=font('Bold', 30), fill=(120, 90, 70, 255))
    for row, txt, start in ((0, 'короткое видео', 0.3), (1, '= вечно', 1.2)):
        nch = int(len(txt) * cl((t - n0 - start) / 0.9))
        d.text((100, 95 + row * 95), txt[:nch], font=font('Heavy', 60), fill=(40, 50, 120, 255))
    if t >= n0 + 2.2:
        d.line((100, 290, 100 + 300 * eo((t - n0 - 2.2) / 0.4), 290), fill=(230, 60, 70, 255), width=8)
    page = page.rotate(-4, expand=True, resample=Image.BICUBIC)
    page = page.resize((max(1, int(page.width * k)), max(1, int(page.height * k))), Image.BICUBIC)
    im.alpha_composite(page, (int(W / 2 - page.width / 2), int(600 - page.height / 2)))


def gift_ui(im, t):
    gt = T['gift']
    if gt - 0.5 <= t < gt + 0.1:
        k = eio((t - gt + 0.5) / 0.6)
        x, y = lerp(CHAIR_X - 160, 280, k), lerp(1100, 1080, k) - math.sin(k * math.pi) * 380
        size = int(lerp(140, 240, math.sin(k * math.pi)))
        im.alpha_composite(lottie.frame(GIFT, t - gt + 0.5, size=size), (int(x - size / 2), int(y - size / 2)))
    if gt <= t < T['s6']:
        k = spring(t - gt, 2.5, 0.5)
        lay = Image.new('RGBA', (740, 200), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        dd.rounded_rectangle((0, 0, 739, 199), 50, fill=(25, 25, 40, 240), outline=(255, 210, 90, 255), width=4)
        lay.alpha_composite(lottie.frame(GIFT, t - gt, size=170), (15, 15))
        dd.text((200, 40), 'Мисед подарил', font=font('Bold', 40), fill=(220, 220, 240, 255))
        dd.text((200, 100), 'Hanging Star', font=font('Heavy', 52), fill=(255, 215, 90, 255))
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


# ------------------------------------------------------------------ сцены
def scene_intro(t):
    im = R66.street().copy()
    R66.stars(im, t)
    k_in = eo(t / 1.2)
    k_out = eio((t - 2.8) / 0.6)
    ux = lerp(1350, 540, k_in) + math.sin(t * 3) * 6
    uy = lerp(-200, 560, k_in) + math.sin(t * 4) * 8 - k_out * 1000
    R66.beam_draw(im, ux, uy, cl((t - 1.2) / 0.15) * (1 - cl((t - 2.75) / 0.2)))
    if t >= 1.25:
        k = eo((t - 1.25) / 1.05)
        p = dict(mouth='o' if mouth_open('M', t) == 2 else 'smile', blink=0, ear_l=0.0, ear_r=0.0)
        if 2.3 <= t < 2.65:
            p['tilt'] = 6
        put(im, scaled('missed', 0.5, 'beam', **p), 540, lerp(1000, 1640, k))
    im.alpha_composite(R66.UFO, (int(ux - 260), int(uy - 130)))
    R66.ufo_lights(im, ux, uy, t)
    if t >= T['logo']:
        s = spring(t - T['logo'])
        lay = Image.new('RGBA', (W, 420), (0, 0, 0, 0))
        text_c(lay, 'МИСЕД НА ЗЕМЛЕ', W / 2, 30, 96, stroke=9, stroke_fill=(90, 40, 160, 255))
        chip(lay, 'ЕЩЁ ОДНО ВИДЕО', W / 2, 220, bg=(255, 210, 70, 255), fg=(40, 20, 60, 255), size=50, pop=spring(t - T['logo'] - 0.15))
        lay = lay.resize((max(1, int(W * s)), max(1, int(420 * s))), Image.BICUBIC)
        im.alpha_composite(lay, (int(W / 2 - lay.width / 2), int(540 - lay.height / 2)))
    flash(im, t, T['intro_end'] - 0.07)
    return im


def scene_outro(t):
    im = R66.street().copy()
    R66.stars(im, t - T['s6'] + DUR)
    u = t - T['s6']
    k_out = eio((t - T['ufo_out']) / 0.6)
    ux = 540 + math.sin(t * 3) * 6 + k_out * 900
    uy = 560 + math.sin(t * 4) * 8 - k_out * 820
    R66.beam_draw(im, ux, uy, cl(u / 0.15) * (1 - cl((t - T['ufo_out'] + 0.3) / 0.2)))
    lift = eio((u - 0.1) / 1.6)
    if lift < 1:
        p = dict(mouth='o' if mouth_open('M', t) == 2 else 'smile', blink=0, ear_l=0.0, ear_r=0.0)
        put(im, scaled('missed', lerp(0.5, 0.25, lift), 'beam', **p), 540, lerp(1640, uy + 150, lift))
    im.alpha_composite(R66.UFO, (int(ux - 260), int(uy - 130)))
    R66.ufo_lights(im, ux, uy, t)
    if T['card'] <= t < T['ufo_out'] + 0.4:
        k = spring(t - T['card'], 2.5, 0.5) * (1 - eio((t - T['ufo_out']) / 0.35))
        card = Image.new('RGBA', (660, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(card)
        d.rounded_rectangle((0, 0, 659, 519), 40, fill=(10, 20, 30, 235), outline=(255, 190, 90, 255), width=5)
        d.text((40, 30), 'НА ОЧЕРЕДИ', font=font('Heavy', 48), fill=(255, 190, 90, 255))
        sil = scaled('human', 0.2, 'day', arms='phone', eyes='open', mouth='open')
        a = np.asarray(sil).copy()
        a[..., :3] = (60, 45, 20)
        card.alpha_composite(Image.fromarray(a), (40, 110))
        d.text((250, 140), 'МАКС, 19', font=font('Heavy', 56), fill=(255, 255, 255, 255))
        d.text((250, 225), 'голосовые', font=font('Bold', 38), fill=(230, 220, 200, 255))
        d.text((250, 272), 'по 4 минуты', font=font('Bold', 38), fill=(230, 220, 200, 255))
        bars = [abs(math.sin(t * 9 + j * 0.7)) for j in range(14)]          # волна голосового
        for j, b in enumerate(bars):
            h = 8 + b * 40
            d.rounded_rectangle((250 + j * 24, 380 - h / 2, 262 + j * 24, 380 + h / 2), 5, fill=(255, 190, 90, 255))
        d.text((40, 440), 'ЗАГРУЗКА ОБЪЕКТА…', font=font('Bold', 32), fill=(255, 190, 90, int(140 + 115 * math.sin(t * 10))))
        card = card.resize((max(1, int(660 * k)), max(1, int(520 * k))), Image.BICUBIC)
        im.alpha_composite(card, (int(W / 2 - card.width / 2), int(560 - card.height / 2)))
    flash(im, t, T['s6'], 0.14)
    return im


def scene_bedroom(t):
    im = R65.room('night').copy()
    R65.armchair_back(im, 'night')
    draw_missed(im, t)
    R65.armchair_front(im, 'night')
    draw_artem(im, t)
    return im


VIG = None


def vignette(im):
    global VIG
    if VIG is None:
        v = Image.new('L', (W, H), 0)
        ImageDraw.Draw(v).ellipse((-300, -200, W + 300, H + 200), fill=255)
        v = v.filter(ImageFilter.GaussianBlur(160))
        VIG = Image.new('RGBA', (W, H), (4, 4, 14, 255))
        VIG.putalpha(Image.eval(v, lambda p: int((255 - p) * 0.55)))
    im.alpha_composite(VIG)


def camera(im, t):
    zoom, fx, fy = 1.0, W / 2, H / 2

    def push(t0, t1, z, x, y, a=0.35, b=0.35):
        nonlocal zoom, fx, fy
        k = eio((t - t0) / a) * (1 - eio((t - t1) / b))
        if k > 0:
            zoom, fx, fy = lerp(zoom, z, k), lerp(fx, x, k), lerp(fy, y, k)

    push(V['M2'], V['M2'] + D['M2'], 1.35, 300, 1150)                       # «сорок минут назад» — на Артёма
    push(E.DROP - 0.4, V['M5'] - 0.2, 1.6, 320, 1150, a=0.4)                 # падение телефона
    push(V['A6'] - 0.3, V['A6'] + D['A6'], 1.3, 300, 1150, a=0.6)             # «…Кот, который боится огурца»
    push(E.LEAN[0], E.LEAN[1], 1.25, 520, 1150, a=0.5)                       # Мисед заглядывает
    for c in T['cuts']:
        if 0 <= t - c < 0.3:
            zoom *= 1 + 0.12 * (1 - (t - c) / 0.3)
    sx = sy = 0.0
    if 0 <= t - E.DROP < 0.35:
        k = (1 - (t - E.DROP) / 0.35) * 18
        sx, sy = math.sin(t * 90) * k, math.cos(t * 77) * k
    if zoom == 1 and not sx and not sy:
        return im
    cw, ch = W / zoom, H / zoom
    x0 = min(max(0, fx - cw / 2), W - cw) + sx
    y0 = min(max(0, fy - ch / 2), H - ch) + sy
    return im.transform((W, H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BILINEAR)


def overlay(im, t):
    if T['s1'] <= t < V['A1'] + D['A1'] + 0.3:                          # хук
        a = cl((t - T['s1']) / 0.2) * (1 - cl((t - V['A1'] - D['A1']) / 0.3))
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
        text_c(lay, 'ПРИШЕЛЕЦ ВПЕРВЫЕ ВИДИТ,', W / 2, 400, 58, fill=(255, 220, 90, 255))
        text_c(lay, 'КАК ЗЕМЛЯНЕ ЛОЖАТСЯ СПАТЬ', W / 2, 472, 58, fill=(255, 220, 90, 255))
        lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
        im.alpha_composite(lay)
    scanner(im, t)
    # лента на телефоне: после хука и до «бума»; кот — в разговоре про «важное»
    a = cl((t - V['A1'] - D['A1'] - 0.1) / 0.25) * (1 - cl((t - T['note'] + 0.1) / 0.25))
    a2 = cl((t - T['s3']) / 0.15) * (1 - cl((t - T['cuts'][2] - 0.2) / 0.2))
    feed_card(im, t, max(a, a2))
    ac = cl((t - V['A6']) / 0.25) * (1 - cl((t - T['s5'] + 0.2) / 0.25))
    feed_card(im, t, ac, cat=True)
    clock_chip(im, t)
    counter(im, t)
    note_page(im, t)
    if V['M5'] <= t < T['s4']:                                           # «сорок седьмой раз»
        k = spring(t - V['M5'] - 1.2, 3, 0.45)
        if t >= V['M5'] + 1.2:
            chip(im, '«ПОСЛЕДНЕЕ» ×47', W / 2, 560, bg=(255, 90, 160, 240), size=60, pop=k)
    gift_ui(im, t)


def render_at(t):
    if t < T['intro_end']:
        return scene_intro(t).convert('RGB')
    if t >= T['s6']:
        im = scene_outro(t)
        subtitles(im, t)
        return im.convert('RGB')
    im = scene_bedroom(t)
    im = camera(im, t)
    vignette(im)
    overlay(im, t)
    subtitles(im, t)
    for c in [T['s1']] + list(T['cuts']):
        flash(im, t, c, 0.1, k=0.7)
    if E.SPIN[0] <= t < E.SPIN[1]:                                       # тайм-лапс: лёгкое мерцание
        im.alpha_composite(Image.new('RGBA', im.size, (120, 140, 255, int(30 + 25 * math.sin(t * 40)))))
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
    with Pool(4) as pool:
        for _ in pool.imap_unordered(_frame, range(0, int(DUR * FPS), step), chunksize=4):
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
