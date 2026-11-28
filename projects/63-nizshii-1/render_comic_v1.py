"""«Низший» 1/1 — первые ~19 с части 1 в стиле графического романа (выбор агента 2026-11-24 по просьбе автора).
Панели комикса на тёмной странице: чёрная рамка, растр, плашки системы (зелёный моноширинный), плашки мыслей Оди
(кремовые), облачко речи Йорки, звуковые надписи «ТУК». Камера плавно едет внутри панели; панели сменяются наездом.
Предыдущая версия (неоновая инфографика) — render_infographic_v1.py. Кадр — чистая функция времени.

    python -B projects/63-nizshii-1/render.py --frames 60,300,520,700,860,1080
    python -B engine/tools/build.py projects/63-nizshii-1 --approved --name nizshii_1_comic_v1
"""
import functools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
import banner  # noqa: E402
import frames  # noqa: E402
import comic  # noqa: E402
from timeline_test import S, E, DUR, CAPS, SC2, SC3, STAMP  # noqa: E402
from events_test import AD_STOPS, OK, BEATS, MEMORY_DRAIN, NAME_GLITCH, FACE_GLITCH, HEY  # noqa: E402

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks(AD_STOPS, cy=H / 2)
F = HERE / 'fonts'
INK = (0, 0, 0)
PAGE = (20, 20, 24)
GREEN = (96, 255, 150)
CREAM = (246, 236, 204)
RED = (214, 40, 36)
YELLOW = (255, 214, 64)
M = 34                                         # поле страницы


def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(x):
    x = cl(x)
    return 1 - (1 - x) ** 3


def eio(x):
    x = cl(x)
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return cl((t - a) / (b - a)) if b > a else float(t >= a)


def back(x, s=1.7):
    x = cl(x) - 1
    return 1 + x * x * ((s + 1) * x + s)


@functools.lru_cache(None)
def font(name, size):
    return ImageFont.truetype(str(F / name), size)


def osw(size):
    return font('Oswald-700.ttf', size)


def mono(size):
    return font('JetBrainsMono-Bold.ttf', size)


def put(base, spr, cx, cy, a=1.0, scale=1.0, rot=0.0):
    if a <= 0.003:
        return
    if abs(scale - 1) > 1e-3:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.05:
        spr = spr.rotate(rot, Image.BICUBIC, expand=True)
    if a < 0.999:
        spr = spr.copy()
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * cl(a))))
    base.alpha_composite(spr, (int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))))


# ------------------------------------------------------------------ спрайты (один раз на процесс)
@functools.lru_cache(None)
def lying(eyes):
    """Оди лежит на полу по диагонали — вид сверху"""
    im = comic.hero(eyes).crop((240, 520, 860, 1840))
    im = im.resize((int(im.width * 0.72), int(im.height * 0.72)), Image.LANCZOS)
    return im.rotate(-58, Image.BICUBIC, expand=True)


@functools.lru_cache(None)
def face_crop():
    return comic.hero('half').crop((330, 520, 750, 1000)).resize((1008, 1152), Image.LANCZOS)


@functools.lru_cache(None)
def chest_crop():
    return comic.hero('half').crop((370, 790, 770, 1130)).resize((1000, 850), Image.LANCZOS)


@functools.lru_cache(None)
def yorka_crop():
    return comic.yorka().crop((360, 470, 780, 1260)).resize((714, 1343), Image.LANCZOS)


@functools.lru_cache(None)
def box(text, size, fg, bg, border=INK, pad=(26, 16), mono_font=False, bw=6, acc=None):
    f = mono(size) if mono_font else osw(size)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + pad[0] * 2, bb[3] - bb[1] + pad[1] * 2
    im = Image.new('RGBA', (w + 14, h + 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w + 10, h + 10), fill=(0, 0, 0, 160))                   # сдвинутая тень, как в комиксе
    d.rectangle((0, 0, w, h), fill=bg, outline=border, width=bw)
    x = pad[0] - bb[0]
    if acc and acc in text:
        pre, post = text.split(acc, 1)
        d.text((x, pad[1] - bb[1]), pre, font=f, fill=fg)
        x += f.getlength(pre)
        d.text((x, pad[1] - bb[1]), acc, font=f, fill=RED)
        x += f.getlength(acc)
        d.text((x, pad[1] - bb[1]), post, font=f, fill=fg)
    else:
        d.text((x, pad[1] - bb[1]), text, font=f, fill=fg)
    return im


@functools.lru_cache(None)
def sfx_word(text, size, col, rot):
    """звуковая надпись: цветная, с чёрной и белой обводкой"""
    f = osw(size)
    bb = f.getbbox(text)
    w, h = bb[2] - bb[0] + 80, bb[3] - bb[1] + 80
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((40 - bb[0], 40 - bb[1]), text, font=f, fill=(255, 255, 255), stroke_width=22, stroke_fill=(255, 255, 255))
    d.text((40 - bb[0], 40 - bb[1]), text, font=f, fill=col, stroke_width=10, stroke_fill=INK)
    return im.rotate(rot, Image.BICUBIC, expand=True)


# ------------------------------------------------------------------ панель
def panel_frame(im, rect, content_fn, t):
    """content_fn(t, w, h) -> RGBA; вставляется в прямоугольник с чёрной рамкой"""
    x0, y0, x1, y1 = [int(v) for v in rect]
    w, h = x1 - x0, y1 - y0
    if w < 8 or h < 8:
        return
    c = content_fn(t, w, h)
    im.alpha_composite(c, (x0, y0))
    d = ImageDraw.Draw(im)
    d.rectangle((x0, y0, x1, y1), outline=INK, width=14)
    d.rectangle((x0 - 7, y0 - 7, x1 + 7, y1 + 7), outline=(236, 232, 222), width=4)


def ken(src, t, t0, t1, w, h, z0, z1, c0, c1):
    """камера внутри панели: зум z и центр c (в координатах исходника), плавно"""
    u = eio(ramp(t, t0, t1))
    z = z0 + (z1 - z0) * u
    cx = c0[0] + (c1[0] - c0[0]) * u
    cy = c0[1] + (c1[1] - c0[1]) * u
    return src.transform((w, h), Image.AFFINE, (1 / z, 0, cx - w / 2 / z, 0, 1 / z, cy - h / 2 / z),
                         resample=Image.BILINEAR)


# ------------------------------------------------------------------ панель 1: тело на полу, система собирает
@functools.lru_cache(None)
def p1_world(eyes):
    world = comic.floor_top().copy()
    hero = lying(eyes)
    world.alpha_composite(hero, (700 - hero.width // 2, 1180 - hero.height // 2))
    return world


def p1(t, w, h):
    eyes = 'half' if t >= BEATS[-1] + 0.1 else 'closed'
    src = p1_world(eyes)
    img = ken(src, t, 0, SC2, w, h, 0.92, 1.25, (700, 1200), (820, 1000))
    d = ImageDraw.Draw(img, 'RGBA')
    # Гидрация: блики воды пробегают по полу; Комплектация: зелёные кольца на стыках; Реанимация: сердце
    g = ramp(t, S['S1'], OK['S1'] + 0.4)
    if 0 < g < 1:
        for k in range(5):
            r = 80 + 900 * ((g + k * 0.2) % 1)
            d.ellipse((w / 2 - r, h * 0.55 - r * 0.5, w / 2 + r, h * 0.55 + r * 0.5), outline=(140, 200, 255, int(120 * (1 - g))),
                      width=5)
    s = ramp(t, OK['S2'] - 0.4, OK['S2'] + 0.6)
    if 0 < s < 1:
        img.alpha_composite(Image.new('RGBA', (w, h), (40, 255, 120, int(45 * math.sin(math.pi * s)))))
    return img


def p1_overlay(im, t):
    """плашки поверх панели 1 (в координатах экрана)"""
    if t < S['S3'] + 0.2:
        a = eo(ramp(t, 0.25, 0.6)) * (1 - ramp(t, S['S3'] - 0.2, S['S3'] + 0.2))
        put(im, box('НИЗШИЙ · ЧАСТЬ 1', 52, INK, YELLOW, bw=7), 290, 150, a, 0.9 + 0.1 * back(ramp(t, 0.25, 0.6)))
    rows = [('S1', 'ГИДРАЦИЯ'), ('S2', 'КОМПЛЕКТАЦИЯ'), ('S3', 'РЕАНИМАЦИЯ')]
    for k, (key, word) in enumerate(rows):
        t0 = S[key] - 0.05
        if t < t0:
            continue
        n = int(len(word) * ramp(t, t0, t0 + 0.4))
        txt = word[:n] + (' — УСПЕШНО' if t >= OK[key] else '')
        spr = box(f'> {txt:<25}', 36, GREEN, (6, 14, 10), border=GREEN, mono_font=True, bw=4)
        y = 250 + k * 100
        put(im, spr, 70 + spr.width / 2, y, eo(ramp(t, t0, t0 + 0.15)))
    for k, b in enumerate(BEATS):                              # ТУК!
        v = t - b
        if 0 <= v < 0.75:
            spr = sfx_word('ТУК!' if k < 2 else 'ТУК-ТУК!', 120 + 20 * k, RED, (-12, 9, -5)[k])
            put(im, spr, (330, 760, 560)[k], (1250, 1120, 1450)[k], 1 - ramp(v, 0.5, 0.75), 0.6 + 0.4 * back(v / 0.18))


# ------------------------------------------------------------------ панель 2: лицо крупно, мысли
def p2(t, w, h):
    img = comic.corridor_bg().resize((w, int(w * 1920 / 1080)), Image.BILINEAR).crop((0, 300, w, 300 + h))
    img = ken(img, t, SC2, SC3, w, h, 1.0, 1.08, (w / 2, h / 2), (w / 2, h / 2 - 30))
    fc = face_crop()
    z = 1.0 + 0.06 * eio(ramp(t, SC2, SC3))
    put(img, fc, w / 2 + 10, h / 2 + 130, 1.0, z)
    d = ImageDraw.Draw(img, 'RGBA')
    if t >= FACE_GLITCH:                                       # «ни лица» — лицо зачёркивается штриховкой
        u = eio(ramp(t, FACE_GLITCH, FACE_GLITCH + 0.7))
        cx, cy = w / 2 + 10, h / 2 + 30
        for k in range(int(26 * u)):
            y = cy - 230 + k * 18
            d.line((cx - 230, y, cx + 230, y - 60), fill=(0, 0, 0, 230), width=7)
    if t >= MEMORY_DRAIN:                                      # знаки вопроса всплывают
        for k in range(6):
            v = (t - MEMORY_DRAIN - k * 0.35)
            if v > 0:
                x = 140 + (k * 157) % (w - 280)
                y = 420 - 120 * v + 30 * math.sin(v * 3 + k)
                f = osw(90 + 20 * (k % 3))
                d.text((x, y), '?', font=f, fill=(255, 255, 255, int(200 * cl(1 - v / 3))), stroke_width=5,
                       stroke_fill=INK)
    return img


def p2_overlay(im, t):
    caps = [c for c in CAPS if c[0] < S['Y1'] - 0.1]
    ys = [1330, 1480, 1630]
    lines = []
    for t0, t1, text, acc in caps:
        if t0 - 0.02 <= t:
            if lines and lines[-1][1] == 'И Я НЕ ПОМНЮ':
                lines[-1] = (lines[-1][0], 'И Я НЕ ПОМНЮ НИЧЕГО.', 'НИЧЕГО.')
            elif text != 'НИЧЕГО.':
                lines.append((t0, text, acc))
            else:
                lines.append((t0, 'И Я НЕ ПОМНЮ ' + text, acc))
    for k, (t0, text, acc) in enumerate(lines[:3]):
        u = ramp(t, t0, t0 + 0.18)
        spr = box(text, 74, INK, CREAM, acc=acc or None, bw=6)
        x = 80 + spr.width / 2 + (k * 90 if k < 2 else 40)
        put(im, spr, x, ys[k], eo(u), 0.85 + 0.15 * back(u))


# ------------------------------------------------------------------ панель 3: Йорка кричит
def p3(t, w, h):
    img = comic.action_bg().crop((0, 0, w, h))
    img = ken(img, t, SC3, STAMP, w, h, 1.0, 1.1, (w / 2 + 100, h / 2), (w / 2 + 150, h / 2 - 40))
    y = yorka_crop()
    u = eo(ramp(t, SC3, SC3 + 0.35))
    bob = math.sin(t * 11) * 6
    put(img, y, w - 300 + 260 * (1 - u), h - 560 + bob, u, 1.0 + 0.04 * math.sin(t * 7))
    return img


def p3_overlay(im, t, rect):
    caps = [c for c in CAPS if c[0] >= S['Y1'] - 0.1]
    shown = [c for c in caps if t >= c[0] - 0.02]
    if not shown:
        return
    f = osw(92)
    lines = [c[2] for c in shown]
    tw = max(f.getlength(s) for s in lines)
    lh = 112
    bw, bh = tw + 230, lh * len(lines) + 130
    x0, y0 = rect[0] + 60, rect[1] + 180
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    tip = (rect[2] - 420, rect[1] + 640)
    d.polygon([(x0 + bw * 0.55, y0 + bh - 20), (x0 + bw * 0.78, y0 + bh - 30), tip], fill=(255, 255, 255), outline=INK)
    d.line([(x0 + bw * 0.55, y0 + bh - 10), tip, (x0 + bw * 0.78, y0 + bh - 20)], fill=INK, width=8)
    d.ellipse((x0, y0, x0 + bw, y0 + bh), fill=(255, 255, 255), outline=INK, width=9)
    for k, c in enumerate(shown):
        v = t - c[0]
        col = RED if c[3] else INK
        sz = 1 + 0.18 * (1 - eo(v / 0.15))
        spr = Image.new('RGBA', (int(tw) + 40, lh + 20), (0, 0, 0, 0))
        ImageDraw.Draw(spr).text((spr.width / 2, spr.height / 2), c[2], font=f, fill=col, anchor='mm')
        put(lay, spr, x0 + bw / 2, y0 + 65 + lh * k + lh / 2, eo(v / 0.1), sz)
    k = back(ramp(t, shown[0][0], shown[0][0] + 0.2))
    put(im, lay, W / 2 + (1 - k) * 40, H / 2, cl(k * 1.5), 0.9 + 0.1 * k)


# ------------------------------------------------------------------ панель 4: номер 11 на груди
def p4(t, w, h):
    img = Image.new('RGBA', (w, h), (30, 34, 40, 255))
    c = chest_crop()
    v = t - STAMP
    put(img, c, w / 2, h / 2 + 60, 1.0, 1.0 + 0.08 * eio(ramp(t, STAMP, DUR)))
    if v < 0.25:
        img.alpha_composite(Image.new('RGBA', (w, h), (255, 255, 255, int(160 * (1 - v / 0.25)))))
    return img


def p4_overlay(im, t):
    v = t - STAMP
    put(im, sfx_word('11', 300, (240, 240, 236), 0), W / 2 + 160, 860, eo(v / 0.08), 1 + 0.6 * (1 - eo(v / 0.2)))
    spr = box('НОМЕР: 11 · СТАТУС: НИЗШИЙ', 40, GREEN, (6, 14, 10), border=GREEN, mono_font=True, bw=4)
    put(im, spr, W / 2, 1560, eo(ramp(v, 0.35, 0.6)))


# ------------------------------------------------------------------ монтаж
FULL = (M, M + 40, W - M, H - M - 40)


def shake(t):
    a = 0.0
    for t0, amp in ((HEY, 26), (STAMP, 34), (BEATS[0], 8), (BEATS[1], 8), (BEATS[2], 10)):
        v = t - t0
        if 0 <= v < 0.45:
            a += amp * math.exp(-v * 10)
    return math.sin(t * 93) * a, math.cos(t * 71) * a


def slide_rect(u, frm):
    """панель въезжает: снизу ('up') или справа ('left') с перелётом"""
    k = back(u, 1.2)
    dx, dy = {'up': (0, H), 'left': (W, 0), 'zoom': (0, 0)}[frm]
    x0, y0, x1, y1 = FULL
    return (x0 + dx * (1 - k), y0 + dy * (1 - k), x1 + dx * (1 - k), y1 + dy * (1 - k))


def render_at(t):
    im = Image.new('RGBA', (W, H), PAGE + (255,))
    sx, sy = shake(t)
    if t < SC2 + 0.6:
        r = FULL
        if t >= SC2:                                           # старая панель отъезжает и темнеет
            u = eio(ramp(t, SC2, SC2 + 0.6))
            r = (FULL[0], FULL[1] - 300 * u, FULL[2], FULL[3] - 300 * u)
        panel_frame(im, (r[0] + sx, r[1] + sy, r[2] + sx, r[3] + sy), p1, t)
        p1_overlay(im, t)
        if t >= SC2:
            im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(150 * ramp(t, SC2, SC2 + 0.6)))))
    if SC2 <= t < SC3 + 0.45:
        r = slide_rect(ramp(t, SC2, SC2 + 0.55), 'up')
        panel_frame(im, r, p2, t)
        if t < SC3:
            p2_overlay(im, t)
    if SC3 <= t < STAMP + 0.5:
        r = slide_rect(ramp(t, SC3, SC3 + 0.4), 'left')
        r = (r[0] + sx, r[1] + sy, r[2] + sx, r[3] + sy)
        panel_frame(im, r, p3, t)
        if t < STAMP:
            p3_overlay(im, t, r)
        if HEY <= t < HEY + 0.3:
            im.alpha_composite(Image.new('RGBA', (W, H), RED + (int(90 * (1 - (t - HEY) / 0.3)),)))
    if t >= STAMP:
        u = ramp(t, STAMP, STAMP + 0.18)
        x0, y0, x1, y1 = FULL
        k = back(u, 2.0)
        cx, cy = W / 2 + sx, H / 2 + sy
        hw, hh = (x1 - x0) / 2 * (0.4 + 0.6 * k), (y1 - y0) / 2 * (0.4 + 0.6 * k)
        panel_frame(im, (cx - hw, cy - hh, cx + hw, cy + hh), p4, t)
        p4_overlay(im, t)
    a_in, a_out = ramp(t, 0, 0.3), ramp(t, DUR - 0.6, DUR)
    k = a_in * (1 - a_out)
    if k < 1:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * (1 - k)))))
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
