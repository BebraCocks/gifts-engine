"""Compositor: 3D plate (Blender, 540x960 -> 1080x1920) + 2D layers (drawing, hand, gifts, captions),
grade, transitions and the RubUp breaks. Frame = function of output time only.

    python -B projects/02-resistance-dog/render.py --frames 0,600,1800
"""
import functools
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import banner
import frames
import gifts_api
import lottie
import art
from events import AD_STOPS, SHOTS, E, shot_at
from timeline import DUR
from words import WORDS

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks(AD_STOPS, cy=H / 2)
import os
PLATES = Path(os.environ.get('RD_PLATES', HERE / 'build' / 'plates'))
GIFT = 'Resistance Dog'
FONT_DIR = paths.ROOT / 'input' / 'fonts' / 'SF-Pro-Text' if hasattr(paths, 'ROOT') else \
    Path(__file__).resolve().parents[2] / 'input' / 'fonts' / 'SF-Pro-Text'


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def spring(x, f=1.8, z=0.45):
    if x <= 0:
        return 0.0
    return 1 - math.exp(-z * 10 * x) * math.cos(f * 2 * math.pi * x)


# ------------------------------------------------------------------ plates
def _existing(n):
    for d in (0, -1, 1, -2, 2):
        if (PLATES / f'f{n + d:05d}.png').exists():
            return n + d
    return None


@functools.lru_cache(maxsize=8)
def plate(n):
    p = PLATES / f'f{n:05d}.png'
    if not p.exists():
        return None
    im = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=2.0, percent=60, threshold=2))
    return np.asarray(im, np.float32)


@functools.lru_cache(maxsize=8)
def anchors(n):
    p = PLATES / 'anchors' / f'f{n:05d}.json'
    return json.loads(p.read_text()) if p.exists() else {}


def plate_index(t, shot):
    """Nearest rendered content frame inside the current shot."""
    name, a, b = shot
    n = int(round(t * FPS))
    lo, hi = math.ceil(a * FPS), math.ceil(b * FPS) - 1
    return min(hi, max(lo, n))


# ------------------------------------------------------------------ gifts (Lottie, full forward loop)
MODELS = {'gift_main': None, 'gift_drop': None, 'statue': None, 'gift_vpn': 'VPN', 'm_vpn': 'VPN',
          'm_anon': 'Anonymous', 'm_che': 'Che Guevara', 'm_sparta': 'Spartacus', 'm_satoshi': 'Satoshi',
          'm_imposter': 'Imposter', 'fin0': 'VPN', 'fin1': 'Anonymous', 'fin2': 'Che Guevara', 'fin3': 'Spartacus',
          'fin4': 'Satoshi'}
APPEAR = {'gift_main': E['gift1'] - 0.15, 'gift_vpn': E['models5'] - 0.1, 'm_vpn': AD_STOPS[0] - 1.0, 'statue': -10.0,
          'gift_drop': E['sold'] - 0.05, 'm_anon': E['anon'] - 0.2, 'm_che': E['che'] - 0.2, 'm_sparta': E['sparta'] - 0.2,
          'm_satoshi': E['satoshi'] - 0.2, 'm_imposter': E['imposter'] - 0.2,
          'fin0': E['drawing'] + 0.2, 'fin1': E['survived'] + 0.1, 'fin2': E['survived'] + 0.7,
          'fin3': E['legend2'] - 0.2, 'fin4': E['legend2'] + 0.4}
LABEL = {'gift_vpn': 'VPN', 'm_vpn': 'VPN', 'm_anon': 'Anonymous', 'm_che': 'Che Guevara', 'm_sparta': 'Spartacus',
         'm_satoshi': 'Satoshi · крафт', 'm_imposter': 'Imposter · 0,1%', 'gift_main': 'Resistance Dog',
         'gift_drop': 'Resistance Dog'}


@functools.lru_cache(maxsize=None)
def lottie_path(model):
    if model is None:
        return str(gifts_api.original_file(GIFT, 'json'))
    return str(gifts_api.model_file(GIFT, model, 'json'))


def gift_sprite(key, t, px):
    path = lottie_path(MODELS[key])
    size = int(max(64, min(1024, px)))
    size -= size % 2
    return lottie.frame(path, t - APPEAR[key], size=size)


@functools.lru_cache(maxsize=64)
def label_img(text, size=40):
    f = ImageFont.truetype(str(FONT_DIR / 'SF-Pro-Text-Heavy.otf'), size)
    tw = int(f.getlength(text)) + 40
    im = Image.new('RGBA', (tw, size + 26), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, tw - 1, size + 25), radius=(size + 25) // 2, fill=(14, 16, 24, 205))
    d.text((tw / 2, (size + 26) / 2), text, font=f, fill=(255, 255, 255, 255), anchor='mm')
    return im


def paste(canvas, im, cx, cy, alpha=1.0):
    """Alpha-composite RGBA PIL image centred at (cx, cy) onto float canvas (H,W,3)."""
    if alpha <= 0.003:
        return
    a = np.asarray(im, np.float32)
    h, w = a.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    sub = a[ya - y0:yb - y0, xa - x0:xb - x0]
    al = sub[..., 3:4] / 255 * alpha
    reg = canvas[ya:yb, xa:xb]
    reg[:] = reg * (1 - al) + sub[..., :3] * al


def add_glow(canvas, cx, cy, r, color, k):
    if k <= 0.01 or r < 4:
        return
    x0, x1 = int(max(0, cx - r)), int(min(W, cx + r))
    y0, y1 = int(max(0, cy - r)), int(min(H, cy + r))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    g = np.clip(1 - d, 0, 1) ** 2.2 * k
    canvas[y0:y1, x0:x1] += g[..., None] * np.array(color, np.float32)


GOLD = np.array([[40, 22, 8], [150, 92, 30], [235, 170, 70], [255, 236, 170]], np.float32)


def gold(im):
    """Recolour a sprite as polished gold (luminance -> bronze/gold/highlight ramp), keep alpha."""
    a = np.asarray(im, np.float32)
    lum = (a[..., 0] * 0.3 + a[..., 1] * 0.55 + a[..., 2] * 0.15) / 255
    lum = np.clip(lum * 1.15 + 0.08, 0, 1) * 3
    i = np.clip(lum.astype(int), 0, 2)
    f = (lum - i)[..., None]
    rgb = GOLD[i] * (1 - f) + GOLD[i + 1] * f
    return Image.fromarray(np.dstack([rgb, a[..., 3]]).astype(np.uint8), 'RGBA')


PENDING_LABELS = []


def draw_gifts(c, t, an):
    for key in MODELS:
        if key not in an:
            continue
        x, y, r, depth = an[key]
        if depth <= 0:
            continue
        u = t - APPEAR[key]
        if u < -0.05:
            continue
        k = spring(seg(u, 0, 0.75), 1.7, 0.42)
        if k <= 0.01:
            continue
        px = 2.35 * r * k
        if px < 8:
            continue
        add_glow(c, x, y, 1.9 * r, (255, 236, 190), 45 * math.exp(-6 * max(0, u)) * (u >= 0))
        spr = gift_sprite(key, t, px)
        if key == 'statue':
            spr = gold(spr)
        paste(c, spr, x, y - 0.12 * px)
        lab = LABEL.get(key)
        if lab and not key.startswith('fin'):
            la = smooth(seg(u, 0.25, 0.55))
            if la > 0:
                PENDING_LABELS.append((label_img(lab, 38 if r > 120 else 30), x, y - 1.5 * r * k - 34 + 14 * (1 - la), la))


# ------------------------------------------------------------------ hook drawing (projected onto the paper)
def homography(src, dst):
    A_, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A_.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A_.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    h = np.linalg.solve(np.array(A_, float), np.array(b, float))
    return np.append(h, 1).reshape(3, 3)


DRAW_T0, DRAW_T1 = 0.15, 3.05


@functools.lru_cache(maxsize=4)
def drawing_img(q):
    return art.line_art(q / 400, size=1000, width=14)


def draw_paper(c, t, an, final=False):
    if 'paper0' not in an:
        return
    quad = [an[f'paper{i}'][:2] for i in range(4)]
    if min(an[f'paper{i}'][3] for i in range(4)) <= 0:
        return
    prog = 1.0 if final else seg(t, DRAW_T0, DRAW_T1)
    if prog <= 0:
        return
    src = [(0, 0), (1000, 0), (1000, 1000), (0, 1000)]
    Hm = homography(quad, src)                       # screen -> drawing (PIL wants output->input)
    img = drawing_img(int(round(prog * 400)))
    warped = img.transform((W, H), Image.PERSPECTIVE, tuple((Hm / Hm[2, 2]).flatten()[:8]), Image.BILINEAR)
    a = np.asarray(warped, np.float32)
    al = a[..., 3:4] / 255 * 0.95
    c[:] = c * (1 - al) + a[..., :3] * al
    if not final:
        Hf = homography(src, quad)
        px, py = art.pen_at(prog)
        v = Hf @ np.array([px, py, 1.0])
        sx, sy = v[0] / v[2], v[1] / v[2]
        side = math.dist(quad[0], quad[1])
        leave = smooth(seg(t, DRAW_T1 + 0.05, DRAW_T1 + 0.6))
        enter = 1 - smooth(seg(t, 0.0, DRAW_T0 + 0.25))
        sx += (leave + enter) * 700
        sy -= (leave + enter) * 500
        hs = int(side * 0.62)
        hand = hand_img(hs)
        paste(c, hand, sx + hs * (0.5 - 0.06), sy + hs * (0.5 - 0.94), 1.0)


# ------------------------------------------------------------------ Durov's post on the phone screen (illustration)
def _font(w, size):
    return ImageFont.truetype(str(FONT_DIR / f'SF-Pro-Text-{w}.otf'), size)


@functools.lru_cache(maxsize=4)
def _gift_icon(name, size):
    p = gifts_api.original_png(name, 256)
    return Image.open(p).convert('RGBA').resize((size, size), Image.LANCZOS)


def post_screen(t):
    """Phone screen 600x1300: a channel post (paraphrase, not a verbatim quote) + countdown."""
    Wd, Hd = 600, 1300
    im = Image.new('RGBA', (Wd, Hd), (18, 25, 34, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, Wd, 150), fill=(26, 36, 48, 255))
    d.ellipse((30, 45, 110, 125), fill=(64, 120, 190, 255))
    d.text((70, 85), 'Д', font=_font('Heavy', 44), fill=(255, 255, 255, 255), anchor='mm')
    d.text((130, 62), 'Канал Дурова', font=_font('Bold', 34), fill=(240, 244, 248, 255))
    d.text((130, 104), '14 августа 2025', font=_font('Regular', 24), fill=(140, 160, 180, 255))
    wr, hr, am = E['wrote'], E['hour'], E['among']
    u = smooth(seg(t, wr - 0.1, wr + 0.45))
    if u > 0:
        y0 = int(330 + 260 * (1 - u))
        bub = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((30, y0, 570, y0 + 760), radius=34, fill=(33, 46, 62, 255))
        bd.text((60, y0 + 30), 'иллюстрация поста', font=_font('Regular', 20), fill=(120, 140, 160, 255))
        bd.text((60, y0 + 70), 'Через час —', font=_font('Heavy', 46), fill=(255, 255, 255, 255))
        bd.text((60, y0 + 128), 'новые подарки', font=_font('Heavy', 46), fill=(255, 255, 255, 255))
        cd = max(0.0, 3600 - max(0.0, t - hr) * 1.0) if t > hr - 0.2 else 3600
        if t > hr - 0.2:
            mm, ss = int(cd // 60) % 60, int(cd % 60)
            bd.rounded_rectangle((60, y0 + 205, 330, y0 + 265), radius=30, fill=(64, 140, 230, 255))
            bd.text((195, y0 + 235), f'00:{mm:02d}:{ss:02d}', font=_font('Bold', 32), fill=(255, 255, 255, 255), anchor='mm')
        g = smooth(seg(t, am - 0.2, am + 0.3))
        for k, name in enumerate(('Resistance Dog', "Durov's Glasses")):
            x = 70 + k * 250
            box = (x, y0 + 300, x + 210, y0 + 510)
            bd.rounded_rectangle(box, radius=26, fill=(44, 60, 80, 255))
            if k == 0 and g > 0:
                bd.rounded_rectangle((box[0] - 6, box[1] - 6, box[2] + 6, box[3] + 6), radius=30,
                                     outline=(255, 200, 80, int(255 * g)), width=6)
            ic = _gift_icon(name, 180)
            bub.alpha_composite(ic, (x + 15, y0 + 315))
            bd.text((x + 105, y0 + 540), name, font=_font('Semibold', 22), fill=(200, 210, 222, 255), anchor='mm')
        bd.text((60, y0 + 600), '+ ещё подарки', font=_font('Regular', 28), fill=(150, 170, 190, 255))
        a = np.asarray(bub, np.float32)
        a[..., 3] *= u
        im.alpha_composite(Image.fromarray(a.astype(np.uint8), 'RGBA'))
    return im


def draw_phone(c, t, an):
    if 'screen0' not in an or min(an[f'screen{i}'][3] for i in range(4)) <= 0:
        return
    quad = [an[f'screen{i}'][:2] for i in range(4)]
    src = [(0, 0), (600, 0), (600, 1300), (0, 1300)]
    Hm = homography(quad, src)
    img = post_screen(t)
    warped = img.transform((W, H), Image.PERSPECTIVE, tuple((Hm / Hm[2, 2]).flatten()[:8]), Image.BILINEAR)
    a = np.asarray(warped, np.float32)
    al = a[..., 3:4] / 255
    c[:] = c * (1 - al) + a[..., :3] * 1.08 * al


@functools.lru_cache(maxsize=2)
def stamp_img():
    f = _font('Heavy', 120)
    txt = 'РАСКУПЛЕНО'
    tw = int(f.getlength(txt)) + 80
    im = Image.new('RGBA', (tw, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, tw - 8, 222), radius=26, outline=(235, 40, 50, 255), width=14)
    d.text((tw / 2, 115), txt, font=f, fill=(235, 40, 50, 255), anchor='mm')
    return im.rotate(-12, resample=Image.BICUBIC, expand=True)


def draw_stamp(c, t):
    u = t - E['seconds'] + 0.1
    if u < 0:
        return
    k = 1 + 1.6 * math.exp(-11 * u)
    im = stamp_img()
    im = im.resize((int(im.width * k * 0.85), int(im.height * k * 0.85)), Image.BILINEAR)
    paste(c, im, W / 2, 760, smooth(seg(u, 0, 0.08)))


@functools.lru_cache(maxsize=8)
def hand_img(size):
    size = int(size // 8 * 8)
    base = Image.open(HERE / 'build' / 'assets' / 'hand.png').convert('RGBA')
    return base.resize((max(8, size), max(8, size)), Image.LANCZOS)


# ------------------------------------------------------------------ captions: spray-paint stencil words
ACCENT = {'S01_desk': (255, 72, 72), 'S02_office': (90, 170, 255), 'S03_past': (255, 196, 110), 'S04_vault': (110, 220, 255),
          'S05_court': (255, 80, 70), 'S06_roof': (120, 200, 255), 'S07_ipcity': (255, 80, 80), 'S08_planes': (255, 190, 90),
          'S09_legend': (255, 200, 90), 'S10_ton': (110, 200, 255), 'S11_giftrain': (255, 210, 100),
          'S12_gallery': (255, 200, 100), 'S13_laser': (255, 70, 70), 'S14_final': (255, 210, 120),
          'S15_phone': (110, 190, 255), 'S16_hacker': (80, 255, 140), 'S17_havana': (255, 120, 90),
          'S18_arena': (255, 90, 70), 'S19_crypto': (255, 200, 80)}
KEY = {'войны', 'спотти', 'вконтакте', 'дуров', 'телеграм', 'телеге', 'телега', 'resistance', 'dog', 'vpn', 'совпадение',
       '2018', 'фсб', 'блокирует', 'капюшоне', 'сопротивление', 'роскомнадзор', 'ip', 'прокси', 'proxy server',
       'anonymous', 'самолётики', 'легендой', 'токен на ton', 'франции', 'аватарки', 'подарки', 'он', 'интересное',
       'улучшать', 'че гевара', 'спартак', 'рэмбо', 'сатоши', 'imposter', 'тысячу', 'коллекционным', 'продолжается',
       'рисунок', 'символом', 'шифрования', 'подарком', 'миллионы', 'десятки', 'редкая', 'дурова', 'вождь',
       'гладиатор', 'хакер', 'маске', 'революционер', 'биткоином', 'золотом', 'крафтовая', 'реже', 'написал', 'час',
       'секунды', 'впервые', 'токен', 'моделей', 'модели', 'восстания', 'легенда', 'кубинским', 'чёрный', 'заблокировали',
       'капюшон', 'восемнадцатом', 'четырнадцатого', 'история', 'легендой', 'телеги'}
CAP_Y = 1330


@functools.lru_cache(maxsize=256)
def caption_img(word, accent):
    txt = word.upper().strip('.,!?:;…')
    size = 118 if len(txt) <= 9 else (96 if len(txt) <= 13 else 80)
    f = ImageFont.truetype(str(FONT_DIR / 'SF-Pro-Text-Heavy.otf'), size)
    tw = int(f.getlength(txt)) + 120
    th = size + 110
    mask = Image.new('L', (tw, th), 0)
    ImageDraw.Draw(mask).text((tw / 2, th / 2), txt, font=f, fill=255, anchor='mm')
    m = np.asarray(mask, np.float32) / 255
    # stencil bridges: two thin slanted gaps through the letters
    yy, xx = np.mgrid[0:th, 0:tw]
    for frac, slope in ((0.43, 0.035), (0.6, -0.03)):
        yc = th * frac + (xx - tw / 2) * slope
        gap = np.abs(yy - yc) < max(2.0, size * 0.025)
        m = np.where(gap, 0, m)
    is_key = word.lower().strip('.,!?:;…') in KEY
    fill = np.array(accent if is_key else (255, 255, 255), np.float32)
    rng = np.random.default_rng(abs(hash(txt)) % (2 ** 32))
    # overspray: soft halo + sprinkled dots in the accent/dark colour
    halo = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(size * 0.11)), np.float32) / 255
    dots = (rng.random((th, tw)) < 0.035).astype(np.float32) * np.clip(halo * 2.2, 0, 1)
    outline = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)), np.float32) / 255
    rgb = np.zeros((th, tw, 3), np.float32)
    a = np.zeros((th, tw), np.float32)
    dark = np.array((14, 14, 22), np.float32)
    a = np.maximum(a, halo * 0.55)
    rgb += dark * (halo * 0.55)[..., None]
    a = np.maximum(a, outline)
    rgb = np.where(outline[..., None] > 0, dark, rgb)
    tex = 0.9 + 0.1 * rng.random((th, tw))
    rgb = np.where(m[..., None] > 0.02, fill * tex[..., None], rgb)
    a = np.maximum(a, m)
    spray = np.array(accent if is_key else (210, 220, 235), np.float32)
    rgb = np.where((dots > 0)[..., None] & (m[..., None] < 0.02), spray, rgb)
    a = np.maximum(a, dots * 0.8)
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(a * 255, 0, 255)]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


FLAT = [(w, a, b, k) for k, line in enumerate(WORDS) for (w, a, b) in line]


def current_word(t):
    for i, (w, a, b, k) in enumerate(FLAT):
        nxt = FLAT[i + 1][1] if i + 1 < len(FLAT) else 1e9
        same_line = i + 1 < len(FLAT) and FLAT[i + 1][3] == k
        end = nxt if same_line and nxt - b < 0.5 else b + 0.28
        if a - 0.04 <= t < end:
            return w, a, i
    return None


def draw_caption(c, t, shot):
    cw = current_word(t)
    if cw is None:
        return
    w, a, i = cw
    img = caption_img(w, ACCENT.get(shot, (255, 210, 100)))
    u = t - a + 0.04
    k = 1.0 + 0.18 * math.exp(-14 * max(0, u)) * math.cos(u * 30)
    rot = ((i * 37) % 7 - 3) * 0.9
    al = smooth(seg(u, 0, 0.06))
    im = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if abs(k - 1) > 0.01:
        im = im.resize((int(im.width * k), int(im.height * k)), Image.BILINEAR)
    paste(c, im, W / 2, CAP_Y, al)


# ------------------------------------------------------------------ grade, glow, transitions
GRADE = {  # (lift rgb, gain rgb, saturation)
    'S01_desk': ((6, 6, 12), (1.05, 0.98, 0.92), 1.08), 'S02_office': ((4, 6, 10), (1.0, 1.0, 1.04), 1.12),
    'S03_past': ((10, 7, 4), (1.06, 0.98, 0.86), 0.9), 'S04_vault': ((2, 4, 10), (0.98, 1.0, 1.06), 1.25),
    'S05_court': ((6, 3, 2), (1.08, 0.96, 0.88), 1.1), 'S06_roof': ((4, 3, 10), (1.0, 0.98, 1.08), 1.15),
    'S07_ipcity': ((2, 3, 8), (1.0, 1.0, 1.05), 1.2), 'S08_planes': ((8, 6, 8), (1.05, 1.0, 0.98), 1.15),
    'S09_legend': ((8, 5, 3), (1.08, 1.0, 0.9), 1.15), 'S10_ton': ((2, 4, 10), (0.96, 1.0, 1.08), 1.2),
    'S11_giftrain': ((3, 5, 10), (1.0, 1.0, 1.04), 1.2), 'S12_gallery': ((6, 4, 3), (1.05, 1.0, 0.95), 1.1),
    'S13_laser': ((6, 2, 2), (1.05, 0.95, 0.95), 1.1), 'S14_final': ((6, 5, 8), (1.05, 0.98, 0.92), 1.05),
    'S15_phone': ((3, 3, 10), (1.0, 1.0, 1.06), 1.15), 'S16_hacker': ((2, 4, 4), (0.98, 1.04, 1.0), 1.15),
    'S17_havana': ((8, 6, 4), (1.06, 1.0, 0.94), 1.2), 'S18_arena': ((8, 5, 3), (1.07, 0.98, 0.9), 1.12),
    'S19_crypto': ((6, 4, 1), (1.08, 1.0, 0.85), 1.15)}

_vy, _vx = np.mgrid[0:H, 0:W]
VIGNETTE = (1 - 0.32 * np.clip(((_vx - W / 2) / (W * 0.62)) ** 2 + ((_vy - H / 2) / (H * 0.6)) ** 2, 0, 1.4) ** 1.4)[..., None].astype(np.float32)
del _vy, _vx


def grade(c, shot, t):
    lift, gain, sat = GRADE[shot]
    if shot == 'S03_past':
        s = smooth(seg(t, E['past'] - 0.6, E['past'] + 0.5))
        sat = 0.9 - 0.45 * s
        gain = (1.06 + 0.04 * s, 0.98 - 0.02 * s, 0.86 - 0.12 * s)
    lum = c.mean(axis=2, keepdims=True)
    c[:] = lum + (c - lum) * sat
    c *= np.array(gain, np.float32)
    c += np.array(lift, np.float32)
    # bloom from the brightest parts (computed at quarter size)
    small = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
    s = np.asarray(small, np.float32)
    br = np.clip(s - 185, 0, None) * 1.4
    bl = Image.fromarray(np.clip(br, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))
    c += np.asarray(bl.resize((W, H), Image.BILINEAR), np.float32) * 0.55
    c *= VIGNETTE


def whip(c, amount, horizontal=True):
    """Directional blur + exposure lift for cut transitions."""
    if amount <= 0.02:
        return
    n = 7
    step = int(10 + 70 * amount)
    acc = np.zeros_like(c)
    for k in range(n):
        d = (k - n // 2) * step
        acc += np.roll(c, d, axis=1 if horizontal else 0)
    c[:] = c * (1 - amount) + acc / n * amount
    c += 60 * amount ** 2


def grain(c, t):
    rng = np.random.default_rng(int(t * FPS) + 7)
    g = rng.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32)
    c += np.repeat(np.repeat(g, 2, 0), 2, 1)


FLASH = {E['hood']: (1.0, (255, 255, 255)), E['blocks']: (0.6, (255, 90, 70)), E['war']: (0.55, (255, 60, 50)),
         E['lift']: (0.5, (255, 240, 200)), E['imposter']: (0.6, (255, 90, 80))}


# ------------------------------------------------------------------ frame
def render_at(t):
    t = min(max(t, 0.0), DUR - 1e-6)
    shot = shot_at(t)
    name, a, b = shot
    n = plate_index(t, shot)
    m = _existing(n)
    n = m if m is not None and (math.ceil(a * FPS) <= m <= math.ceil(b * FPS) - 1) else n
    base = plate(n)
    if base is None:
        c = np.full((H, W, 3), 30, np.float32)
        an = {}
    else:
        c = base.copy()
        an = anchors(n)
    if name == 'S01_desk':
        draw_paper(c, t, an)
    elif name == 'S14_final':
        draw_paper(c, t, an, final=True)
    if name == 'S15_phone':
        draw_phone(c, t, an)
    draw_gifts(c, t, an)
    if name == 'S11_giftrain':
        draw_stamp(c, t)
    grade(c, name, t)
    for li, lx, ly, la in PENDING_LABELS:
        lx = min(max(lx, li.width / 2 + 24), W - li.width / 2 - 24)
        paste(c, li, lx, ly, la)
    PENDING_LABELS.clear()
    # whip transitions around every cut (not at the ad stops: those cut under the banner)
    for k, (nm, sa, sb) in enumerate(SHOTS[1:], 1):
        if any(abs(sa - s) < 1e-6 for s in AD_STOPS):
            continue
        d = abs(t - sa)
        if d < 0.16:
            whip(c, (1 - d / 0.16) ** 1.5, horizontal=(k % 2 == 0))
    for ft, (amp, col) in FLASH.items():
        u = t - ft
        if 0 <= u < 0.5:
            c += np.array(col, np.float32) * amp * 0.55 * math.exp(-9 * u)
    draw_caption(c, t, name)
    # fade in from black / out to black
    c *= smooth(seg(t, 0, 0.25)) * (1 - smooth(seg(t, DUR - 0.7, DUR - 0.05)))
    grain(c, t)
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
