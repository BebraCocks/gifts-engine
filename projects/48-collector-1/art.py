"""«Коллекционер», часть 1 — 2D-графика кодом: Кирилл (крупный план и в полный рост), Коллекционер, фоны
(панельный дом, комната, прихожая с дверью), телефон от первого лица и экраны (лента, чат, подарок).
Плоский 2D с тёмной обводкой; объём — параллаксом, наклоном телефона и «рыбьим глазом» глазка.
Всё — чистые функции параметров (кэш по ключу), кадр детерминирован."""
import functools
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths

W, H = 1080, 1920
S = 2                                       # суперсэмплинг спрайтов

# ------------------------------------------------------------------ палитра
INK = (18, 16, 30)
NIGHT = (12, 14, 32)
SKY_TOP, SKY_BOT = (10, 12, 34), (40, 36, 78)
WALL, WALL_D = (52, 50, 84), (40, 38, 66)
FLOOR, FLOOR_D = (70, 52, 58), (54, 40, 46)
DOOR, DOOR_D, DOOR_L = (110, 58, 44), (82, 42, 32), (138, 78, 58)
SKIN, SKIN_D = (242, 204, 176), (214, 168, 140)
HAIR, HAIR_D = (60, 40, 32), (40, 26, 22)
HOOD, HOOD_D = (104, 124, 142), (78, 94, 112)
PANTS = (46, 50, 66)
GLOW = (150, 205, 255)
RED = (232, 62, 74)
GOLD = (246, 196, 72)
WHITE = (245, 245, 250)
TG_BG, TG_BAR, TG_IN, TG_OUT = (14, 22, 33), (23, 33, 43), (24, 37, 51), (43, 82, 120)
TG_ACC = (100, 170, 235)
FONT_DIR = paths.ROOT / 'input' / 'fonts' / 'SF-Pro-Text'


@functools.lru_cache(None)
def font(weight, size):
    return ImageFont.truetype(str(FONT_DIR / f'SF-Pro-Text-{weight}.otf'), int(size))


def rgba(c, a=255):
    return tuple(c[:3]) + (int(a),)


def mix(a, b, u):
    return tuple(int(a[k] + (b[k] - a[k]) * u) for k in range(3))


def canvas(w, h, c=(0, 0, 0, 0)):
    return Image.new('RGBA', (int(w), int(h)), c)


def down(im):
    return im.resize((im.width // S, im.height // S), Image.LANCZOS)


def vgrad(w, h, top, bot):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float)[None, None, :3]
    b = np.array(bot, float)[None, None, :3]
    g = (a + (b - a) * t) * np.ones((1, w, 1))
    return Image.fromarray(g.astype(np.uint8), 'RGB').convert('RGBA')


def paste(base, im, x, y, alpha=1.0):
    """Наложить RGBA im верхним левым углом в (x, y) с общей прозрачностью."""
    if im is None or alpha <= 0.003:
        return
    if alpha < 0.999:
        im = im.copy()
        a = im.getchannel('A').point(lambda v: int(v * alpha))
        im.putalpha(a)
    base.alpha_composite(im, (int(round(x)), int(round(y)))) if 0 <= x and 0 <= y and x + im.width <= base.width \
        and y + im.height <= base.height else _paste_clip(base, im, int(round(x)), int(round(y)))


def _paste_clip(base, im, x, y):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(base.width, x + im.width), min(base.height, y + im.height)
    if x1 <= x0 or y1 <= y0:
        return
    base.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def place_c(base, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    """Наложить im центром в (cx, cy) с масштабом и поворотом (градусы)."""
    if im is None:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    paste(base, im, cx - im.width / 2, cy - im.height / 2, alpha)


# ------------------------------------------------------------------ текст
def text_size(s, size, weight='Bold'):
    f = font(weight, size)
    b = f.getbbox(s)
    return b[2] - b[0], b[3] - b[1]


def wrap(s, size, weight, maxw):
    f = font(weight, size)
    out, cur = [], ''
    for w in s.split():
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


@functools.lru_cache(maxsize=512)
def label(s, size, color=WHITE, weight='Heavy', stroke=0, stroke_c=INK, shadow=True):
    f = font(weight, size * S)
    b = f.getbbox(s, stroke_width=stroke * S)
    pad = 14 * S
    im = canvas(b[2] - b[0] + 2 * pad, b[3] - b[1] + 2 * pad)
    d = ImageDraw.Draw(im)
    if shadow:
        d.text((pad - b[0], pad - b[1] + 5 * S), s, font=f, fill=(0, 0, 0, 120), stroke_width=stroke * S, stroke_fill=(0, 0, 0, 120))
    d.text((pad - b[0], pad - b[1]), s, font=f, fill=rgba(color), stroke_width=stroke * S, stroke_fill=rgba(stroke_c))
    return down(im)


# ------------------------------------------------------------------ эмодзи 😇 (в шрифте его нет)
@functools.lru_cache(None)
def emoji_angel(size):
    s = size * S
    im = canvas(s, s)
    d = ImageDraw.Draw(im)
    r = s * 0.40
    cx, cy = s / 2, s * 0.56
    d.ellipse([s * 0.18, s * 0.02, s * 0.82, s * 0.20], outline=rgba((120, 200, 255)), width=int(s * 0.06))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba((255, 204, 77)))
    for sx in (-1, 1):
        d.arc([cx + sx * r * 0.42 - r * 0.2, cy - r * 0.25, cx + sx * r * 0.42 + r * 0.2, cy + r * 0.05], 200, 340,
              fill=rgba((90, 60, 20)), width=int(s * 0.05))
    d.arc([cx - r * 0.5, cy - r * 0.1, cx + r * 0.5, cy + r * 0.6], 20, 160, fill=rgba((90, 60, 20)), width=int(s * 0.055))
    return down(im)


# ======================================================================================== КИРИЛЛ — крупный план
EXPR = ('neutral', 'happy', 'scared', 'sus', 'sad', 'hope', 'greed', 'shock', 'think')


@functools.lru_cache(maxsize=256)
def kirill_bust(expr='neutral', mouth=0, blink=0, look=0, lit=0, sweat=0, tear=0):
    """Кирилл по пояс анфас, 760x900 (центр головы ~ (380, 330)). mouth 0..3, blink 0/1, look -1..1 (зрачки),
    lit 0/1 — подсветка снизу экраном телефона, sweat/tear 0/1."""
    w, h = 760, 900
    im = canvas(w * S, h * S)
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    R = lambda x0, y0, x1, y1: [x0 * S, y0 * S, x1 * S, y1 * S]
    O = 6 * S
    # плечи / худи
    d.rounded_rectangle(R(110, 560, 650, 1000), 160 * S, fill=rgba(HOOD), outline=rgba(INK), width=O)
    d.polygon([P(250, 560), P(380, 700), P(510, 560)], fill=rgba(HOOD_D))                 # ворот
    d.line([P(330, 640), P(320, 760)], fill=rgba(INK), width=4 * S)                          # шнурки
    d.line([P(430, 640), P(440, 760)], fill=rgba(INK), width=4 * S)
    d.ellipse(R(312, 752, 328, 768), fill=rgba(WHITE))
    d.ellipse(R(432, 752, 448, 768), fill=rgba(WHITE))
    # капюшон за головой
    d.ellipse(R(160, 470, 600, 660), fill=rgba(HOOD_D), outline=rgba(INK), width=O)
    # шея
    d.rectangle(R(335, 480, 425, 590), fill=rgba(SKIN_D), outline=rgba(INK), width=O)
    # уши
    for sx in (-1, 1):
        d.ellipse(R(380 + sx * 185 - 32, 300, 380 + sx * 185 + 32, 390), fill=rgba(SKIN), outline=rgba(INK), width=O)
    # голова
    d.rounded_rectangle(R(200, 150, 560, 520), 150 * S, fill=rgba(SKIN), outline=rgba(INK), width=O)
    # волосы (взъерошенные)
    hair = [P(190, 290), P(200, 190), P(250, 130), P(300, 150), P(330, 100), P(390, 140), P(430, 95), P(470, 150),
            P(530, 140), P(560, 210), P(572, 300), P(540, 240), P(500, 205), P(450, 230), P(400, 200), P(340, 235),
            P(290, 210), P(240, 250)]
    d.polygon(hair, fill=rgba(HAIR), outline=rgba(INK))
    d.line(hair + [hair[0]], fill=rgba(INK), width=O, joint='curve')
    # круги под глазами
    for sx in (-1, 1):
        d.arc(R(380 + sx * 80 - 46, 330, 380 + sx * 80 + 46, 392), 20, 160, fill=rgba(SKIN_D), width=5 * S)
    # глаза
    ey = 320
    for sx in (-1, 1):
        ex = 380 + sx * 80
        if blink:
            d.arc(R(ex - 38, ey - 18, ex + 38, ey + 22), 200, 340, fill=rgba(INK), width=6 * S)
            continue
        ry = 34 if expr in ('scared', 'shock') else 28
        if expr == 'sus':
            ry = 14
        if expr == 'happy':
            d.arc(R(ex - 38, ey - 10, ex + 38, ey + 40), 200, 340, fill=rgba(INK), width=7 * S)
            continue
        d.ellipse(R(ex - 36, ey - ry, ex + 36, ey + ry), fill=rgba(WHITE), outline=rgba(INK), width=5 * S)
        pr = 13 if expr in ('scared', 'shock') else 17
        px = ex + look * 14
        if expr == 'greed':
            f = font('Heavy', 46 * S)
            d.text(P(px, ey + 2), '$', font=f, fill=rgba((40, 170, 80)), anchor='mm')
        else:
            d.ellipse(R(px - pr, ey - pr + 2, px + pr, ey + pr + 2), fill=rgba(INK))
            d.ellipse(R(px - 6, ey - 8, px + 2, ey), fill=rgba(WHITE))
        if expr == 'sus':                                                    # прищур — верхнее веко
            d.rectangle(R(ex - 40, ey - 40, ex + 40, ey - 8), fill=rgba(SKIN))
            d.line([P(ex - 40, ey - 8), P(ex + 40, ey - 8)], fill=rgba(INK), width=6 * S)
    # брови
    bro = {'neutral': (0, 0), 'happy': (-10, 0), 'scared': (-22, 14), 'sus': (8, -16), 'sad': (-6, 18), 'hope': (-16, 10),
           'greed': (-14, -6), 'shock': (-30, 0), 'think': (-4, -10)}[expr]
    for sx in (-1, 1):
        ex = 380 + sx * 80
        y_in, y_out = ey - 52 + bro[0] + (bro[1] if True else 0), ey - 52 + bro[0]
        if expr in ('sad', 'hope', 'scared'):
            y_in, y_out = ey - 60 + bro[0], ey - 44 + bro[0] + bro[1] // 2
        if expr in ('sus', 'greed', 'think'):
            y_in, y_out = ey - 44 + bro[0] - bro[1] // 2, ey - 56 + bro[0]
        d.line([P(ex - sx * 4, y_in), P(ex + sx * 44, y_out)], fill=rgba(HAIR_D), width=11 * S)
    # нос
    d.arc(R(362, 360, 398, 420), 290, 70, fill=rgba(SKIN_D), width=5 * S)
    # рот
    my = 450
    if expr in ('happy', 'greed') and mouth == 0:
        d.chord(R(320, my - 30, 440, my + 30), 0, 180, fill=rgba((120, 40, 50)), outline=rgba(INK), width=5 * S)
        d.rectangle(R(332, my, 428, my + 8), fill=rgba(WHITE))
    elif expr in ('sad', 'scared') and mouth == 0:
        d.arc(R(340, my, 420, my + 40), 200, 340, fill=rgba(INK), width=6 * S)
    elif expr == 'sus' and mouth == 0:
        d.line([P(345, my + 4), P(415, my - 4)], fill=rgba(INK), width=6 * S)
    elif mouth == 0:
        d.line([P(350, my), P(410, my)], fill=rgba(INK), width=6 * S)
    else:
        oh = [0, 14, 26, 38][mouth]
        ow = 34 + 6 * mouth if expr not in ('happy', 'greed') else 52
        d.ellipse(R(380 - ow, my - oh / 2, 380 + ow, my + oh / 2 + 10), fill=rgba((110, 36, 46)), outline=rgba(INK), width=5 * S)
        if mouth >= 2:
            d.ellipse(R(380 - ow * 0.55, my + oh / 2 - 6, 380 + ow * 0.55, my + oh / 2 + 8), fill=rgba((214, 96, 110)))
    if sweat:
        d.polygon([P(555, 250), P(540, 290), P(570, 290)], fill=rgba((160, 210, 255)))
        d.ellipse(R(538, 278, 572, 312), fill=rgba((160, 210, 255)), outline=rgba(INK), width=3 * S)
    if tear:
        for sx in (-1, 1):
            d.line([P(380 + sx * 96, 350), P(380 + sx * 100, 430)], fill=rgba((140, 200, 255)), width=10 * S)
    if expr in ('scared', 'shock'):
        d.ellipse(R(232, 380, 282, 410), fill=rgba((255, 190, 190, 0)))
    out = down(im)
    if lit:                                                                  # холодный свет экрана снизу
        a = np.asarray(out).astype(np.float32)
        yy = np.linspace(0, 1, h)[:, None]
        k = np.clip((yy - 0.25) * 1.3, 0, 1) * 0.35
        tint = np.array(GLOW, np.float32)
        a[..., :3] = a[..., :3] * (1 - k[..., None] * 0.5) + tint * k[..., None] * 0.5
        a[..., :3] *= 0.82
        out = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    return out


# ======================================================================================== КИРИЛЛ — в полный рост, профиль вправо
@functools.lru_cache(maxsize=512)
def kirill_side(pose='stand', ph=0, expr='neutral', mouth=0, arm=0.0):
    """Кирилл в полный рост, профиль вправо. Холст 520x980, ступни на y=950, центр x=260.
    pose: stand | walk | back | push | kneel | brace | mop; ph — фаза шага (0..15); arm — подъём рук (0..1)."""
    w, h = 520, 980
    im = canvas(w * S, h * S)
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    R = lambda x0, y0, x1, y1: [x0 * S, y0 * S, x1 * S, y1 * S]
    O = 6 * S
    a = ph / 16 * 2 * math.pi
    lean = {'push': 18, 'brace': -10, 'back': -6, 'kneel': 0}.get(pose, 0)
    hip = (250, 560) if pose != 'kneel' else (250, 700)
    bob = abs(math.sin(a)) * 10 if pose in ('walk', 'back') else 0
    hx, hy = hip[0], hip[1] - bob
    # ноги
    def leg(phase, far):
        col = mix(PANTS, INK, 0.25) if far else PANTS
        if pose in ('walk', 'back'):
            sw = math.sin(phase) * (0.45 if pose == 'walk' else 0.3)
            kx, ky = hx + math.sin(sw) * 190, hy + math.cos(sw) * 190
            bend = max(0, -math.sin(phase + 0.6)) * 0.6
            fx_, fy = kx + math.sin(sw - bend) * 190, ky + math.cos(sw - bend) * 190
        elif pose == 'kneel':
            kx, ky = (hx + 120, hy + 40) if far else (hx + 30, hy + 210)
            fx_, fy = (hx + 130, hy + 245) if far else (hx - 140, hy + 245)
        elif pose == 'push':
            kx, ky = (hx - 60, hy + 185) if far else (hx + 30, hy + 190)
            fx_, fy = (hx - 140, hy + 385) if far else (hx + 20, hy + 385)
        else:
            kx, ky = hx + (12 if far else -6), hy + 190
            fx_, fy = hx + (18 if far else -4), hy + 385
        d.line([P(hx, hy), P(kx, ky), P(fx_, fy)], fill=rgba(INK), width=46 * S, joint='curve')
        d.line([P(hx, hy), P(kx, ky), P(fx_, fy)], fill=rgba(col), width=34 * S, joint='curve')
        d.rounded_rectangle(R(fx_ - 24, fy - 22, fx_ + 50, fy + 6), 12 * S, fill=rgba((230, 230, 236) if not far else (190, 190, 200)),
                            outline=rgba(INK), width=5 * S)
    leg(a + math.pi, True)
    # туловище
    sx_, sy_ = hx + lean * 1.4, hy - 250
    body = [P(hx - 60, hy + 10), P(hx + 60, hy + 10), P(sx_ + 62, sy_ + 20), P(sx_ - 58, sy_ + 10)]
    # дальняя рука
    def arm_(far):
        col = mix(HOOD_D, INK, 0.2) if far else HOOD
        shx, shy = sx_ + (8 if far else -4), sy_ + 40
        if pose == 'push' or pose == 'brace':
            ex, ey_ = shx + 90, shy + 40 + (10 if far else 0)
            wx, wy = shx + 175, shy + 20 + (14 if far else 0)
        elif pose == 'mop':
            ex, ey_ = shx + 70, shy + 120
            wx, wy = shx + 140, shy + 170 + math.sin(a * 2) * 20 * (1 if far else -1)
        elif pose in ('walk', 'back'):
            sw = -math.sin(a + (math.pi if far else 0)) * 0.5
            ex, ey_ = shx + math.sin(sw) * 130, shy + math.cos(sw) * 130
            wx, wy = ex + math.sin(sw + 0.4) * 120, ey_ + math.cos(sw + 0.4) * 120
        elif pose == 'kneel':
            ex, ey_ = shx + 60, shy + 120
            wx, wy = shx + 80, shy + 200
        else:
            up = arm
            ex, ey_ = shx + 30 + up * 60, shy + 130 - up * 120
            wx, wy = ex + 20 + up * 50, ey_ + 120 - up * 150
        d.line([P(shx, shy), P(ex, ey_), P(wx, wy)], fill=rgba(INK), width=44 * S, joint='curve')
        d.line([P(shx, shy), P(ex, ey_), P(wx, wy)], fill=rgba(col), width=32 * S, joint='curve')
        d.ellipse(R(wx - 22, wy - 22, wx + 22, wy + 22), fill=rgba(SKIN if not far else SKIN_D), outline=rgba(INK), width=5 * S)
        return wx, wy
    arm_(True)
    d.polygon(body, fill=rgba(HOOD), outline=rgba(INK))
    d.line(body + [body[0]], fill=rgba(INK), width=O)
    d.polygon([P(sx_ - 58, sy_ + 10), P(sx_ - 74, sy_ + 70), P(sx_ - 20, sy_ + 40)], fill=rgba(HOOD_D), outline=rgba(INK))  # капюшон
    leg(a, False)
    # голова (профиль)
    cx, cy = sx_ + 18, sy_ - 92
    d.rectangle(R(cx - 26, cy + 60, cx + 20, cy + 112), fill=rgba(SKIN_D), outline=rgba(INK), width=O)
    d.ellipse(R(cx - 96, cy - 110, cx + 96, cy + 96), fill=rgba(SKIN), outline=rgba(INK), width=O)
    d.polygon([P(cx + 88, cy - 6), P(cx + 116, cy + 26), P(cx + 86, cy + 36)], fill=rgba(SKIN), outline=rgba(INK))   # нос
    d.line([P(cx + 88, cy - 6), P(cx + 116, cy + 26), P(cx + 86, cy + 36)], fill=rgba(INK), width=5 * S)
    hair = [P(cx - 104, cy + 10), P(cx - 100, cy - 70), P(cx - 50, cy - 124), P(cx + 10, cy - 112), P(cx + 40, cy - 140),
            P(cx + 70, cy - 100), P(cx + 96, cy - 70), P(cx + 60, cy - 60), P(cx + 20, cy - 74), P(cx - 20, cy - 50),
            P(cx - 50, cy - 20), P(cx - 70, cy + 20)]
    d.polygon(hair, fill=rgba(HAIR))
    d.line(hair, fill=rgba(INK), width=O, joint='curve')
    d.ellipse(R(cx - 40, cy - 6, cx - 4, cy + 40), fill=rgba(SKIN), outline=rgba(INK), width=5 * S)              # ухо
    ey = cy - 18
    if expr == 'happy':
        d.arc(R(cx + 34, ey - 10, cx + 74, ey + 22), 200, 340, fill=rgba(INK), width=6 * S)
    else:
        r_ = 20 if expr in ('scared', 'shock') else 15
        d.ellipse(R(cx + 38, ey - r_, cx + 72, ey + r_), fill=rgba(WHITE), outline=rgba(INK), width=4 * S)
        d.ellipse(R(cx + 54, ey - 8, cx + 70, ey + 8), fill=rgba(INK))
    bro = -14 if expr in ('scared', 'shock', 'sad') else 0
    d.line([P(cx + 30, ey - 34 + bro * 0.4), P(cx + 78, ey - 30 + bro)], fill=rgba(HAIR_D), width=9 * S)
    my = cy + 54
    if mouth:
        d.ellipse(R(cx + 52, my - 6 * mouth, cx + 84, my + 8 * mouth), fill=rgba((110, 36, 46)), outline=rgba(INK), width=4 * S)
    elif expr in ('sad', 'scared'):
        d.arc(R(cx + 52, my, cx + 86, my + 20), 200, 330, fill=rgba(INK), width=5 * S)
    elif expr == 'happy':
        d.arc(R(cx + 50, my - 18, cx + 86, my + 10), 20, 140, fill=rgba(INK), width=5 * S)
    else:
        d.line([P(cx + 56, my), P(cx + 84, my - 2)], fill=rgba(INK), width=5 * S)
    arm_(False)
    if pose == 'mop':                                                              # швабра
        d.line([P(sx_ + 120, sy_ + 120), P(sx_ + 260, hy + 380)], fill=rgba((150, 110, 70)), width=12 * S)
        d.rounded_rectangle(R(sx_ + 210, hy + 368, sx_ + 320, hy + 392), 8 * S, fill=rgba((90, 150, 200)), outline=rgba(INK), width=4 * S)
    return down(im)


@functools.lru_cache(maxsize=64)
def kirill_bed(scroll=0, blink=0, expr='neutral'):
    """Кирилл лежит на кровати на боку лицом к зрителю, держит телефон — экран светит ему в лицо. 980x560."""
    w, h = 980, 560
    im = canvas(w * S, h * S)
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    R = lambda x0, y0, x1, y1: [x0 * S, y0 * S, x1 * S, y1 * S]
    O = 6 * S
    # подушка
    d.rounded_rectangle(R(60, 250, 360, 380), 60 * S, fill=rgba((200, 206, 226)), outline=rgba(INK), width=O)
    # одеяло (тело под ним)
    d.rounded_rectangle(R(250, 300, 960, 520), 110 * S, fill=rgba((92, 72, 140)), outline=rgba(INK), width=O)
    for k in range(5):
        d.arc(R(320 + k * 120, 330, 420 + k * 120, 460), 200, 320, fill=rgba((70, 54, 112)), width=5 * S)
    # голова
    cx, cy = 230, 250
    d.ellipse(R(cx - 110, cy - 110, cx + 110, cy + 110), fill=rgba(SKIN), outline=rgba(INK), width=O)
    hair = [P(cx - 120, cy + 10), P(cx - 110, cy - 70), P(cx - 50, cy - 130), P(cx + 20, cy - 112), P(cx + 70, cy - 130),
            P(cx + 120, cy - 60), P(cx + 80, cy - 50), P(cx + 30, cy - 70), P(cx - 30, cy - 50), P(cx - 80, cy - 20)]
    d.polygon(hair, fill=rgba(HAIR))
    d.line(hair, fill=rgba(INK), width=O, joint='curve')
    for sx in (-1, 1):
        ex = cx + 40 + sx * 44
        if blink:
            d.arc(R(ex - 22, cy - 14, ex + 22, cy + 14), 200, 340, fill=rgba(INK), width=5 * S)
        else:
            d.ellipse(R(ex - 20, cy - 18, ex + 20, cy + 18), fill=rgba(WHITE), outline=rgba(INK), width=4 * S)
            d.ellipse(R(ex - 4, cy - 2 + 6, ex + 12, cy + 14 + 2), fill=rgba(INK))
    if expr == 'happy':
        d.arc(R(cx + 30, cy + 40, cx + 100, cy + 80), 20, 160, fill=rgba(INK), width=5 * S)
    else:
        d.line([P(cx + 46, cy + 64), P(cx + 86, cy + 64)], fill=rgba(INK), width=5 * S)
    # рука с телефоном
    d.line([P(420, 420), P(470, 330)], fill=rgba(INK), width=44 * S)
    d.line([P(420, 420), P(470, 330)], fill=rgba(HOOD), width=32 * S)
    d.rounded_rectangle(R(440, 200, 520, 350), 14 * S, fill=rgba((30, 30, 40)), outline=rgba(INK), width=5 * S)
    d.rounded_rectangle(R(450, 212, 510, 338), 8 * S, fill=rgba(mix(GLOW, WHITE, 0.3)))
    d.ellipse(R(450, 300, 494, 344), fill=rgba(SKIN), outline=rgba(INK), width=4 * S)
    out = down(im)
    # свет экрана на лице
    glow = Image.new('L', out.size, 0)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([180, 80, 560, 420], fill=120)
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    col = Image.new('RGBA', out.size, rgba(GLOW))
    col.putalpha(Image.fromarray((np.asarray(glow).astype(np.float32) * (np.asarray(out.getchannel('A')) / 255.0)).astype(np.uint8)))
    out = Image.alpha_composite(out, Image.blend(Image.new('RGBA', out.size, (0, 0, 0, 0)), col, 0.6))
    return out


# ======================================================================================== КОЛЛЕКЦИОНЕР
@functools.lru_cache(maxsize=32)
def collector(eye=1.0, tilt=0, lid=0.3):
    """Коллекционер анфас: длинное пальто, внутри висят подарки; вместо головы — коробка с бантом, из щели
    под крышкой светят глаза. Холст 700x1500, центр по x=350, низ пальто y=1490."""
    w, h = 700, 1500
    im = canvas(w * S, h * S)
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * S, y * S)
    R = lambda x0, y0, x1, y1: [x0 * S, y0 * S, x1 * S, y1 * S]
    O = 7 * S
    coat, coat_d, lining = (34, 30, 44), (22, 20, 30), (96, 24, 36)
    # пальто
    d.polygon([P(200, 420), P(500, 420), P(640, 1490), P(60, 1490)], fill=rgba(coat), outline=rgba(INK))
    d.polygon([P(290, 430), P(410, 430), P(470, 1490), P(230, 1490)], fill=rgba(lining))     # распахнуто — подкладка
    # подарки внутри пальто
    rng = np.random.default_rng(7)
    cols = [(232, 62, 74), (246, 196, 72), (90, 190, 120), (110, 150, 240), (200, 110, 230), (240, 140, 60)]
    for k in range(14):
        gx = 250 + (k % 3) * 70 + rng.uniform(-10, 10)
        gy = 520 + (k // 3) * 170 + rng.uniform(-10, 10)
        c = cols[k % len(cols)]
        d.line([P(gx + 20, gy - 40), P(gx + 20, gy)], fill=rgba((180, 170, 150)), width=3 * S)
        d.rounded_rectangle(R(gx, gy, gx + 42, gy + 42), 6 * S, fill=rgba(c), outline=rgba(INK), width=4 * S)
        d.line([P(gx + 21, gy), P(gx + 21, gy + 42)], fill=rgba(WHITE), width=5 * S)
        d.line([P(gx, gy + 21), P(gx + 42, gy + 21)], fill=rgba(WHITE), width=5 * S)
    d.line([P(200, 420), P(60, 1490)], fill=rgba(INK), width=O)
    d.line([P(500, 420), P(640, 1490)], fill=rgba(INK), width=O)
    d.line([P(290, 430), P(230, 1490)], fill=rgba(coat_d), width=12 * S)
    d.line([P(410, 430), P(470, 1490)], fill=rgba(coat_d), width=12 * S)
    # плечи и руки — длинные, пальцы когтями
    d.polygon([P(200, 420), P(110, 470), P(80, 1000), P(150, 1000), P(220, 520)], fill=rgba(coat), outline=rgba(INK))
    d.polygon([P(500, 420), P(590, 470), P(620, 1000), P(550, 1000), P(480, 520)], fill=rgba(coat), outline=rgba(INK))
    for hx, sx in ((115, -1), (585, 1)):
        for f in range(4):
            d.line([P(hx - 24 + f * 16, 1000), P(hx - 30 + f * 18 + sx * 6, 1080 + (f % 2) * 14)], fill=rgba((150, 150, 165)), width=8 * S)
    # голова-коробка
    bx, by, bw, bh = 350, 270, 230, 200
    d.rectangle(R(bx - bw / 2, by - bh / 2 + 30, bx + bw / 2, by + bh / 2 + 30), fill=rgba((168, 120, 70)), outline=rgba(INK), width=O)
    gap = 16 + lid * 40
    d.rectangle(R(bx - bw / 2 + 6, by - bh / 2 + 34, bx + bw / 2 - 6, by - bh / 2 + 34 + gap), fill=rgba((6, 4, 10)))
    for sx in (-1, 1):                                                            # глаза в щели
        ex, ey = bx + sx * 48, by - bh / 2 + 34 + gap / 2
        c = mix((60, 0, 0), (255, 40, 50), eye)
        d.ellipse(R(ex - 16, ey - 7, ex + 16, ey + 7), fill=rgba(c))
    # крышка (поднята)
    ly = by - bh / 2 + 34 - 46
    d.rectangle(R(bx - bw / 2 - 16, ly, bx + bw / 2 + 16, ly + 46), fill=rgba((186, 136, 82)), outline=rgba(INK), width=O)
    d.rectangle(R(bx - 18, ly - 4, bx + 18, by + bh / 2 + 30), fill=rgba(RED), outline=rgba(INK), width=5 * S)   # лента
    d.ellipse(R(bx - 90, ly - 70, bx - 4, ly + 6), fill=rgba(RED), outline=rgba(INK), width=5 * S)              # бант
    d.ellipse(R(bx + 4, ly - 70, bx + 90, ly + 6), fill=rgba(RED), outline=rgba(INK), width=5 * S)
    d.ellipse(R(bx - 22, ly - 34, bx + 22, ly + 8), fill=rgba((200, 40, 52)), outline=rgba(INK), width=5 * S)
    out = down(im)
    if tilt:
        out = out.rotate(tilt, Image.BICUBIC, center=(350, 900))
    return out


def eyes_glow(base, x, y, s=1.0, a=1.0):
    g = canvas(260, 120)
    d = ImageDraw.Draw(g)
    for sx in (-1, 1):
        d.ellipse([130 + sx * 48 - 26, 60 - 14, 130 + sx * 48 + 26, 60 + 14], fill=(255, 40, 50, int(170 * a)))
    g = g.filter(ImageFilter.GaussianBlur(10))
    place_c(base, g, x, y, s)


# ======================================================================================== ФОНЫ
@functools.lru_cache(maxsize=4)
def stars(seed=1):
    im = canvas(W, H)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for _ in range(170):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H * 0.6), rng.choice([1, 1, 1.5, 2, 2.5])
        a = int(rng.uniform(90, 230))
        d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 235, 255, a))
    return im


@functools.lru_cache(maxsize=4)
def panel_building(lit_kirill=True, glow=0):
    """Девятиэтажка-панелька 760x1500, окно Кирилла — 5 этаж, 3-е слева."""
    w, h = 760, 1500
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, h], fill=(64, 66, 88), outline=INK, width=6)
    for k in range(1, 9):
        d.line([0, k * h / 9, w, k * h / 9], fill=(52, 54, 74), width=4)
    for k in range(1, 6):
        d.line([k * w / 6, 0, k * w / 6, h], fill=(56, 58, 80), width=2)
    rng = np.random.default_rng(3)
    for fl in range(9):
        for col in range(6):
            x0 = 30 + col * w / 6
            y0 = 40 + fl * h / 9
            on = rng.random() < 0.18
            c = (250, 210, 120) if on else (26, 30, 52)
            if fl == 4 and col == 2 and lit_kirill:
                c = mix(GLOW, WHITE, 0.25)
            d.rectangle([x0, y0, x0 + 70, y0 + 92], fill=c, outline=INK, width=4)
            d.line([x0 + 35, y0, x0 + 35, y0 + 92], fill=INK, width=3)
            d.rectangle([x0 - 6, y0 + 92, x0 + 76, y0 + 102], fill=(84, 86, 108))
    d.rectangle([w / 2 - 60, h - 120, w / 2 + 60, h], fill=(40, 34, 40), outline=INK, width=5)   # подъезд
    d.rectangle([w / 2 - 80, h - 140, w / 2 + 80, h - 120], fill=(90, 92, 110), outline=INK, width=4)
    d.ellipse([w / 2 - 14, h - 170, w / 2 + 14, h - 142], fill=(255, 220, 140))
    return im


def kirill_window_xy():
    return 30 + 2 * 760 / 6 + 35, 40 + 4 * 1500 / 9 + 46       # центр окна Кирилла в координатах здания


@functools.lru_cache(maxsize=2)
def city_far():
    im = canvas(W * 2, 700)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(11)
    x = 0
    while x < W * 2:
        bw, bh = rng.uniform(120, 260), rng.uniform(220, 600)
        d.rectangle([x, 700 - bh, x + bw, 700], fill=(30, 30, 56))
        for k in range(int(bh // 50)):
            for c in range(int(bw // 40)):
                if rng.random() < 0.12:
                    d.rectangle([x + 10 + c * 40, 700 - bh + 16 + k * 50, x + 26 + c * 40, 700 - bh + 34 + k * 50], fill=(200, 170, 110))
        x += bw + rng.uniform(10, 40)
    return im


def exterior(cam):
    """Ночная окраина: cam 0..1 — наезд на окно Кирилла (параллакс слоёв)."""
    base = vgrad(W, H, SKY_TOP, SKY_BOT)
    paste(base, stars(), 0, -cam * 40)
    d = ImageDraw.Draw(base)
    d.ellipse([760 - cam * 30, 210 - cam * 60, 900 - cam * 30, 350 - cam * 60], fill=(240, 236, 210))
    d.ellipse([735 - cam * 30, 200 - cam * 60, 860 - cam * 30, 330 - cam * 60], fill=SKY_TOP + (0,))
    cf = city_far()
    paste(base, cf, -300 - cam * 120, 900 - cam * 100)
    s = 1.0 + cam * 2.4
    bld = panel_building()
    wx, wy = kirill_window_xy()
    bx = W / 2 - (wx - 380) * cam * 1.0
    by = 560 - cam * 20
    bim = bld.resize((int(bld.width * s), int(bld.height * s)), Image.BICUBIC) if s != 1 else bld
    tx = bx - bim.width / 2 + (380 - wx) * (s - 1) * cam * 0.0
    # цель — окно в центре кадра при cam=1
    tx = (1 - cam) * (W / 2 - bim.width / 2) + cam * (W / 2 - wx * s)
    ty = (1 - cam) * by + cam * (H * 0.45 - wy * s)
    paste(base, bim, tx, ty)
    d = ImageDraw.Draw(base)
    gy = ty + bim.height
    if gy - 6 < H:
        d.rectangle([0, max(0, gy - 6), W, H], fill=(28, 26, 40))
    # голые деревья и фонарь на переднем плане (быстрый параллакс)
    for k, x0 in enumerate((80, 960)):
        x = x0 + (x0 - W / 2) * cam * 1.6
        y = H - 120 + cam * 500
        d.line([x, y, x, y - 520], fill=(14, 12, 22), width=22)
        for br in range(5):
            ang = -math.pi / 2 + (br - 2) * 0.45
            d.line([x, y - 300 - br * 40, x + math.cos(ang) * 180, y - 300 - br * 40 + math.sin(ang) * 180], fill=(14, 12, 22), width=9)
    return base


@functools.lru_cache(maxsize=2)
def room_bg():
    """Комната: стена с обоями, окно с ночью, шкаф, постер. Пол y>1380."""
    im = Image.new('RGBA', (W, H), rgba(WALL))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 60):                                           # обои — ромбы
        for y in range(0, 1380, 80):
            d.polygon([(x + 30, y + 10), (x + 50, y + 40), (x + 30, y + 70), (x + 10, y + 40)], fill=WALL_D)
    d.rectangle([0, 1380, W, H], fill=FLOOR)
    for x in range(0, W, 140):
        d.line([x, 1380, x - 60, H], fill=FLOOR_D, width=4)
    d.rectangle([0, 1360, W, 1386], fill=(36, 30, 40))
    # окно
    d.rectangle([600, 300, 960, 760], fill=SKY_BOT, outline=INK, width=8)
    paste(im, vgrad(344, 444, SKY_TOP, SKY_BOT), 608, 308)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(5)
    for _ in range(25):
        x, y = rng.uniform(612, 950), rng.uniform(312, 600)
        d.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(230, 230, 255))
    for k in range(6):
        hx = 612 + k * 58
        d.rectangle([hx, 640 - (k * 37) % 90, hx + 50, 752], fill=(26, 26, 50))
    d.line([780, 300, 780, 760], fill=INK, width=8)
    d.line([600, 520, 960, 520], fill=INK, width=8)
    d.rectangle([580, 760, 980, 786], fill=(200, 200, 210), outline=INK, width=5)       # подоконник
    # шторы
    d.polygon([(560, 270), (630, 270), (610, 820), (540, 820)], fill=(120, 60, 80), outline=INK)
    d.polygon([(930, 270), (1000, 270), (1020, 820), (950, 820)], fill=(120, 60, 80), outline=INK)
    # постер с NFT
    d.rectangle([90, 340, 380, 700], fill=(30, 26, 54), outline=INK, width=6)
    d.ellipse([140, 400, 330, 590], fill=GOLD, outline=INK, width=6)
    d.text((235, 640), 'NFT', font=font('Heavy', 64), fill=GOLD, anchor='mm')
    return im


@functools.lru_cache(maxsize=2)
def hall_bg():
    """Прихожая: стена, пол, проём двери (сама дверь — отдельно door_img). Дверь стоит в (330..790, 420..1440)."""
    im = Image.new('RGBA', (W, H), rgba(WALL))
    d = ImageDraw.Draw(im)
    for y in range(0, 1440, 46):
        d.line([0, y, W, y], fill=WALL_D, width=3)
    d.rectangle([0, 1440, W, H], fill=FLOOR)
    for x in range(-200, W + 200, 120):
        d.line([x, 1440, x - 180, H], fill=FLOOR_D, width=5)
    d.rectangle([0, 1430, W, 1450], fill=(36, 30, 40))
    d.rectangle([300, 390, 820, 1446], fill=(70, 60, 64), outline=INK, width=10)        # наличник
    d.rectangle([328, 418, 792, 1442], fill=(14, 10, 14))
    # вешалка с курткой и выключатель
    d.rectangle([60, 520, 220, 540], fill=(120, 90, 60), outline=INK, width=4)
    d.polygon([(90, 540), (190, 540), (210, 900), (70, 900)], fill=(70, 90, 70), outline=INK)
    d.rounded_rectangle([880, 760, 940, 840], 8, fill=(220, 220, 225), outline=INK, width=4)
    d.rectangle([903, 780, 917, 812], fill=(160, 160, 170))
    # лампочка
    d.line([560, 0, 560, 140], fill=INK, width=5)
    d.ellipse([530, 130, 590, 200], fill=(255, 226, 150), outline=INK, width=4)
    return im


@functools.lru_cache(maxsize=64)
def door_img(cracks=0, light=0):
    """Дверь-«дерматин» с ромбами из гвоздиков, 464x1024. cracks 0..3 — трещины; light — полоска света снизу."""
    w, h = 464, 1024
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], fill=DOOR, outline=INK, width=8)
    for y in range(80, h - 60, 110):
        for x in range(60, w - 40, 110):
            off = 55 if (y // 110) % 2 else 0
            xx = x + off if x + off < w - 40 else x
            d.ellipse([xx - 7, y - 7, xx + 7, y + 7], fill=(200, 170, 110), outline=INK)
    for k in range(0, w, 110):
        d.line([k, 0, k + 220, 440], fill=DOOR_D, width=3)
        d.line([k + 220, 0, k, 440], fill=DOOR_D, width=3)
    d.ellipse([w / 2 - 14, 300, w / 2 + 14, 328], fill=(30, 26, 30), outline=(200, 180, 120), width=4)        # глазок
    d.rounded_rectangle([w - 90, 520, w - 30, 548], 10, fill=(210, 190, 120), outline=INK, width=4)            # ручка
    d.rectangle([w - 70, 580, w - 50, 640], fill=(180, 160, 100), outline=INK, width=3)
    if cracks:
        rng = np.random.default_rng(17)
        for k in range(cracks * 4):
            x, y = w / 2 + rng.uniform(-120, 120), h * 0.45 + rng.uniform(-200, 200)
            pts = [(x, y)]
            for _ in range(5):
                x += rng.uniform(-60, 60)
                y += rng.uniform(-70, 70)
                pts.append((x, y))
            d.line(pts, fill=(30, 14, 10), width=5)
    return im


@functools.lru_cache(maxsize=16)
def under_door_light(shadow=0.0, warp=0.0):
    """Полоска света под дверью со снопом и тенью ног. 464x60."""
    im = canvas(464, 60)
    d = ImageDraw.Draw(im)
    d.rectangle([8, 40, 456, 54], fill=(255, 220, 150, 230))
    if shadow > 0:
        for sx in (-1, 1):
            x = 232 + sx * (60 + warp * 40)
            wd = 50 + warp * 60
            d.rectangle([x - wd / 2, 40, x + wd / 2, 54], fill=(20, 14, 10, int(255 * shadow)))
            if warp > 0.3:                                                     # когти
                for f in range(3):
                    d.polygon([(x - wd / 2 + f * wd / 3, 54), (x - wd / 2 + f * wd / 3 + 10, 54), (x - wd / 2 + f * wd / 3 + 4, 60)],
                              fill=(20, 14, 10, int(255 * shadow)))
    return im


@functools.lru_cache(maxsize=8)
def furniture(kind):
    if kind == 'bed':
        im = canvas(560, 360)
        d = ImageDraw.Draw(im)
        d.rectangle([10, 120, 550, 300], fill=(120, 84, 60), outline=INK, width=7)
        d.rectangle([20, 70, 540, 150], fill=(92, 72, 140), outline=INK, width=6)
        d.rectangle([20, 40, 160, 100], fill=(200, 206, 226), outline=INK, width=6)
        for x in (24, 520):
            d.rectangle([x, 290, x + 18, 350], fill=(90, 60, 44), outline=INK, width=4)
        return im
    if kind == 'wardrobe':
        im = canvas(380, 720)
        d = ImageDraw.Draw(im)
        d.rectangle([6, 6, 374, 714], fill=(150, 104, 66), outline=INK, width=8)
        d.line([190, 6, 190, 714], fill=INK, width=6)
        for x in (166, 214):
            d.rounded_rectangle([x - 6, 300, x + 6, 380], 5, fill=(220, 200, 140), outline=INK, width=3)
        d.rectangle([30, 40, 160, 260], outline=(120, 80, 50), width=5)
        d.rectangle([220, 40, 350, 260], outline=(120, 80, 50), width=5)
        return im
    if kind == 'jar':
        im = canvas(170, 230)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([20, 40, 150, 224], 26, fill=(160, 200, 150, 200), outline=INK, width=6)
        d.rectangle([30, 10, 140, 46], fill=(200, 180, 60), outline=INK, width=6)
        for k in range(6):
            x, y = 44 + (k % 3) * 34, 80 + (k // 3) * 66
            d.rounded_rectangle([x, y, x + 26, y + 60], 13, fill=(70, 130, 60), outline=(30, 60, 30), width=3)
        d.line([40, 60, 40, 200], fill=(255, 255, 255, 120), width=8)
        return im
    if kind == 'phone_new':
        im = canvas(300, 560)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([10, 10, 290, 550], 44, fill=(30, 30, 40), outline=INK, width=8)
        d.rounded_rectangle([26, 26, 274, 534], 32, fill=(120, 90, 220))
        d.ellipse([60, 120, 240, 300], fill=(255, 170, 220))
        d.ellipse([230, 40, 260, 70], fill=(10, 10, 14))
        return im
    raise KeyError(kind)


# ======================================================================================== ТЕЛЕФОН ОТ ПЕРВОГО ЛИЦА
SCR_W, SCR_H = 760, 1520


def phone_pov(screen, t, tilt=0.0, scale=1.0, bg=None, thumb=None):
    """Кадр от первого лица: руки держат телефон, экран — screen (RGBA SCR_W x SCR_H). tilt — наклон (град),
    лёгкая покачка руки по времени; thumb=(x, y, press) — большой палец над экраном (координаты экрана)."""
    base = bg.copy() if bg is not None else Image.new('RGBA', (W, H), rgba((10, 10, 20)))
    sway_x = math.sin(t * 0.9) * 8 + math.sin(t * 2.3) * 3
    sway_y = math.sin(t * 0.7 + 1) * 10
    rot = tilt + math.sin(t * 0.6) * 0.8
    ph = _phone_body()
    ph = ph.copy()
    ph.alpha_composite(_rounded_mask(screen, 46), (40, 60))
    if thumb is not None:
        tx, ty, pr = thumb
        tim = _thumb(pr)
        ph.alpha_composite(tim, (int(40 + tx - 70), int(60 + ty - 30)))
    # перспектива: верх чуть уже — телефон слегка от нас
    ph = _perspective(ph, 0.035)
    sc = 1.02 * scale
    cx, cy = W / 2 + sway_x, H * 0.47 + sway_y
    # руки сзади (ладони)
    hands = _hands()
    place_c(base, hands, cx, cy + 520 * sc, sc, rot * 0.6)
    place_c(base, ph, cx, cy, sc, rot)
    # пальцы спереди по бокам
    place_c(base, _fingers(), cx, cy + 300 * sc, sc, rot)
    return base


@functools.lru_cache(maxsize=1)
def _phone_body():
    w, h = SCR_W + 80, SCR_H + 120
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 80, fill=(22, 22, 28), outline=(70, 70, 82), width=6)
    d.rounded_rectangle([14, 14, w - 15, h - 15], 70, fill=(6, 6, 8))
    return im


def _rounded_mask(im, r):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255)
    out = im.copy()
    a = np.minimum(np.asarray(out.getchannel('A')), np.asarray(m))
    out.putalpha(Image.fromarray(a))
    return out


def _perspective(im, k):
    w, h = im.size
    dx = w * k
    coeffs = _find_coeffs([(dx, 0), (w - dx, 0), (w, h), (0, h)], [(0, 0), (w, 0), (w, h), (0, h)])
    return im.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def _find_coeffs(pa, pb):
    A = []
    for p1, p2 in zip(pa, pb):
        A.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0] * p1[0], -p2[0] * p1[1]])
        A.append([0, 0, 0, p1[0], p1[1], 1, -p2[1] * p1[0], -p2[1] * p1[1]])
    A = np.array(A, float)
    B = np.array(pb, float).reshape(8)
    res = np.linalg.solve(A, B)
    return res.tolist()


@functools.lru_cache(maxsize=1)
def _hands():
    im = canvas(1200 * S // 2 * 2, 700)
    im = canvas(1200, 700)
    d = ImageDraw.Draw(im)
    for sx in (-1, 1):
        x = 600 + sx * 330
        d.rounded_rectangle([x - 170, 120, x + 170, 700], 150, fill=rgba(HOOD), outline=rgba(INK), width=8)    # рукава
        d.ellipse([x - 190, -60, x + 190, 320], fill=rgba(SKIN), outline=rgba(INK), width=8)                 # ладонь
    return im


@functools.lru_cache(maxsize=1)
def _fingers():
    """Пальцы, обхватившие телефон: слева большой палец вдоль края, справа три пальца заходят на рамку."""
    im = canvas(1100, 900)
    d = ImageDraw.Draw(im)
    # правая рука: кончики пальцев на рамке
    for f in range(3):
        y = 160 + f * 150
        d.rounded_rectangle([960, y, 1100, y + 104], 52, fill=rgba(SKIN), outline=rgba(INK), width=7)
        d.arc([972, y + 22, 1030, y + 82], 90, 270, fill=rgba(SKIN_D), width=4)
    # левая рука: большой палец вдоль края
    d.rounded_rectangle([0, 300, 120, 640], 60, fill=rgba(SKIN), outline=rgba(INK), width=7)
    d.rounded_rectangle([38, 312, 112, 400], 34, fill=rgba((250, 225, 210)), outline=rgba(SKIN_D), width=4)
    return im


@functools.lru_cache(maxsize=4)
def _thumb(press):
    im = canvas(170, 520)
    d = ImageDraw.Draw(im)
    s = 1 - 0.06 * press
    d.rounded_rectangle([20, 10, 150 * s, 520], 70, fill=rgba(SKIN), outline=rgba(INK), width=7)
    d.rounded_rectangle([44, 24, 126 * s, 110], 36, fill=rgba((250, 225, 210)), outline=rgba(SKIN_D), width=4)
    if press:
        g = canvas(170, 520)
        ImageDraw.Draw(g).ellipse([20, -30, 150, 80], fill=(255, 255, 255, 90))
        im = Image.alpha_composite(g, im)
    return im


# ------------------------------------------------------------------ экраны
def status_bar(im, clock):
    d = ImageDraw.Draw(im)
    d.text((70, 44), clock, font=font('Semibold', 34), fill=WHITE, anchor='lm')
    for k in range(4):
        d.rectangle([SCR_W - 200 + k * 14, 54 - k * 6, SCR_W - 190 + k * 14, 60], fill=WHITE)
    d.rounded_rectangle([SCR_W - 120, 30, SCR_W - 60, 58], 8, outline=WHITE, width=3)
    d.rectangle([SCR_W - 116, 34, SCR_W - 90, 54], fill=WHITE)
    d.ellipse([SCR_W / 2 - 60, 22, SCR_W / 2 + 60, 66], fill=(0, 0, 0))                                       # «чёлка»


def feed_screen(t, pos, clock='00:00'):
    """Лента коротких видео (без логотипов): pos — индекс ролика с дробной частью (свайп вверх)."""
    im = Image.new('RGBA', (SCR_W, SCR_H), (0, 0, 0, 255))
    k0 = int(math.floor(pos))
    frac = pos - k0
    for j, k in enumerate((k0, k0 + 1)):
        y = (j - frac) * SCR_H
        if -SCR_H < y < SCR_H:
            paste(im, _clip(k, t), 0, y)
    d = ImageDraw.Draw(im)
    for k, n in enumerate(('1,2M', '8 413', '21K')):
        y = 820 + k * 160
        cx, cy = SCR_W - 80, y + 40
        if k == 0:                                                    # сердце
            d.ellipse([cx - 34, cy - 26, cx + 2, cy + 10], fill=WHITE)
            d.ellipse([cx - 2, cy - 26, cx + 34, cy + 10], fill=WHITE)
            d.polygon([(cx - 33, cy - 2), (cx + 33, cy - 2), (cx, cy + 34)], fill=WHITE)
        elif k == 1:                                                  # облачко комментария
            d.ellipse([cx - 36, cy - 30, cx + 36, cy + 22], fill=WHITE)
            d.polygon([(cx - 20, cy + 14), (cx - 4, cy + 18), (cx - 26, cy + 36)], fill=WHITE)
        else:                                                         # стрелка «поделиться»
            d.polygon([(cx + 34, cy - 4), (cx + 2, cy - 34), (cx + 2, cy - 16), (cx - 34, cy - 10), (cx - 30, cy + 30),
                       (cx - 10, cy + 8), (cx + 2, cy + 8), (cx + 2, cy + 26)], fill=WHITE)
        d.text((cx, y + 104), n, font=font('Semibold', 28), fill=WHITE, anchor='mm')
    status_bar(im, clock)
    return im


@functools.lru_cache(maxsize=8)
def _clip_bg(k):
    pal = [((255, 120, 80), (120, 40, 160)), ((40, 180, 200), (20, 40, 90)), ((250, 200, 60), (200, 60, 80)),
           ((120, 220, 140), (30, 70, 60)), ((200, 120, 255), (40, 20, 80))]
    a, b = pal[k % len(pal)]
    return vgrad(SCR_W, SCR_H, a, b)


def _clip(k, t):
    im = _clip_bg(k).copy()
    d = ImageDraw.Draw(im)
    cx, cy = SCR_W / 2, SCR_H * 0.5
    kind = k % 3
    if kind == 0:                                                    # котик танцует
        b = math.sin(t * 8) * 20
        d.ellipse([cx - 140, cy - 60 + b, cx + 140, cy + 200 + b], fill=(250, 250, 250), outline=INK, width=8)
        d.ellipse([cx - 110, cy - 220 + b, cx + 110, cy - 20 + b], fill=(250, 250, 250), outline=INK, width=8)
        for sx in (-1, 1):
            d.polygon([(cx + sx * 90, cy - 190 + b), (cx + sx * 110, cy - 290 + b), (cx + sx * 40, cy - 210 + b)], fill=(250, 250, 250), outline=INK)
            d.ellipse([cx + sx * 40 - 14, cy - 140 + b, cx + sx * 40 + 14, cy - 112 + b], fill=INK)
    elif kind == 1:                                                  # бургер
        r = math.sin(t * 3) * 6
        for j, c in enumerate(((220, 150, 70), (90, 50, 30), (250, 210, 60), (120, 200, 90), (220, 150, 70))):
            y = cy - 160 + j * 70
            d.rounded_rectangle([cx - 200 + r, y, cx + 200 - r, y + 70], 30, fill=c, outline=INK, width=6)
    else:                                                            # человечек в прыжке
        jump = abs(math.sin(t * 5)) * 120
        d.ellipse([cx - 50, cy - 260 - jump, cx + 50, cy - 160 - jump], fill=(255, 220, 190), outline=INK, width=7)
        d.line([cx, cy - 160 - jump, cx, cy - jump], fill=INK, width=18)
        d.line([cx - 110, cy - 220 - jump, cx, cy - 120 - jump, cx + 110, cy - 220 - jump], fill=INK, width=14)
        d.line([cx - 80, cy + 80 - jump, cx, cy - jump, cx + 80, cy + 80 - jump], fill=INK, width=14)
    d.text((50, SCR_H - 220), f'@user{k * 37 % 900}', font=font('Bold', 34), fill=WHITE)
    d.text((50, SCR_H - 170), '#рекомендации #ночь', font=font('Regular', 30), fill=(230, 230, 230))
    return im


def notif_banner(title, body):
    w, h = SCR_W - 40, 170
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 40, fill=(38, 40, 50, 240))
    d.ellipse([28, 40, 118, 130], fill=TG_ACC)
    d.text((73, 85), '?', font=font('Heavy', 54), fill=WHITE, anchor='mm')
    d.text((142, 54), title, font=font('Bold', 32), fill=WHITE, anchor='lm')
    d.text((w - 30, 54), 'сейчас', font=font('Regular', 26), fill=(170, 170, 180), anchor='rm')
    lines = wrap(body, 28, 'Regular', w - 170)
    for k, ln in enumerate(lines[:2]):
        d.text((142, 96 + k * 36), ln + ('…' if k == 1 and len(lines) > 2 else ''), font=font('Regular', 28), fill=(225, 225, 232), anchor='lm')
    return im


def _chat_header(im, status='был(а) недавно'):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, SCR_W, 190], fill=TG_BAR)
    d.text((44, 136), '‹', font=font('Regular', 70), fill=TG_ACC, anchor='mm')
    d.ellipse([SCR_W - 130, 96, SCR_W - 44, 182], fill=(90, 96, 110))
    d.text((SCR_W - 87, 139), '?', font=font('Heavy', 50), fill=WHITE, anchor='mm')
    d.text((SCR_W / 2, 124), 'Неизвестный', font=font('Bold', 36), fill=WHITE, anchor='mm')
    d.text((SCR_W / 2, 164), status, font=font('Regular', 26), fill=(130, 150, 170) if 'печатает' not in status else TG_ACC, anchor='mm')


@functools.lru_cache(maxsize=1)
def _chat_wall():
    im = Image.new('RGBA', (SCR_W, SCR_H), rgba(TG_BG))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(2)
    for _ in range(60):
        x, y = rng.uniform(0, SCR_W), rng.uniform(0, SCR_H)
        r = rng.uniform(8, 22)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(26, 36, 50), width=3)
    return im


def bubble(text, reveal=1.0, w_max=690, time_s='00:00', size=44, hl=(), glitch=0.0, emoji=False):
    """Входящее сообщение. reveal — доля показанных символов. hl — слова, выделенные красным."""
    lines = wrap(text, size, 'Regular', w_max - 60)
    n_chars = sum(len(x) + 1 for x in lines)
    show = int(round(n_chars * reveal))
    lh = int(size * 1.32)
    w = min(w_max, max(int(font('Regular', size).getlength(x)) for x in lines) + 70) if lines else 200
    if emoji:
        w = max(w, 200)
    h = len(lines) * lh + 76
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 30, fill=TG_IN)
    y = 24
    cnt = 0
    for ln in lines:
        x = 30
        for word in ln.split(' '):
            for ch in word + ' ':
                if cnt >= show:
                    break
                bare = word.strip(',.!?—«»…')
                col = RED if bare in hl else WHITE
                d.text((x, y), ch, font=font('Regular' if bare not in hl else 'Bold', size), fill=col)
                x += font('Regular' if bare not in hl else 'Bold', size).getlength(ch)
                cnt += 1
        y += lh
    if emoji and reveal >= 1:
        e = emoji_angel(46)
        im.alpha_composite(e, (int(30 + font('Regular', size).getlength(text) + 8), 18))
    d.text((w - 24, h - 20), time_s, font=font('Regular', 22), fill=(120, 140, 160), anchor='rm')
    if glitch > 0:
        im = glitch_img(im, glitch)
    return im


def typing_bubble(t):
    im = canvas(150, 80)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 149, 79], 30, fill=TG_IN)
    for k in range(3):
        a = 0.4 + 0.6 * max(0, math.sin(t * 7 - k * 0.9))
        d.ellipse([34 + k * 30 - 9, 31, 34 + k * 30 + 9, 49], fill=(int(160 * a + 60),) * 3)
    return im


def chat_screen(t, items, clock='00:00', status='был(а) недавно', scroll=0.0, toast=None, gone=0.0):
    """items: список картинок сообщений (снизу вверх идут от последнего); scroll — сдвиг вверх (px)."""
    im = _chat_wall().copy()
    y = SCR_H - 150 + scroll
    for it in reversed(items):
        if it is None:
            continue
        img, side = it if isinstance(it, tuple) else (it, 'in')
        y -= img.height + 22
        x = 26 if side == 'in' else (SCR_W - img.width) / 2
        paste(im, img, x, y)
    d = ImageDraw.Draw(im)
    d.rectangle([0, SCR_H - 130, SCR_W, SCR_H], fill=TG_BAR)
    d.rounded_rectangle([40, SCR_H - 108, SCR_W - 130, SCR_H - 30], 38, fill=(30, 42, 56))
    d.text((80, SCR_H - 69), 'Сообщение', font=font('Regular', 30), fill=(110, 125, 140), anchor='lm')
    d.ellipse([SCR_W - 108, SCR_H - 108, SCR_W - 30, SCR_H - 30], fill=TG_ACC)
    _chat_header(im, status)
    if toast is not None:
        paste(im, toast, (SCR_W - toast.width) / 2, SCR_H * 0.42)
    if gone > 0:
        g = Image.new('RGBA', im.size, rgba(TG_BG))
        dd = ImageDraw.Draw(g)
        _chat_header(g, 'чат удалён')
        dd.text((SCR_W / 2, SCR_H / 2), 'Чат не найден', font=font('Bold', 40), fill=(130, 150, 170), anchor='mm')
        im = Image.blend(im, g, min(1, gone))
    status_bar(im, clock)
    return im


def buttons_row(labels, press=-1, w=700):
    h = 96
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    bw = (w - 16 * (len(labels) - 1)) / len(labels)
    for k, lb in enumerate(labels):
        x0 = k * (bw + 16)
        col = (60, 80, 104) if k != press else TG_ACC
        d.rounded_rectangle([x0, 0, x0 + bw, h - 1], 24, fill=col)
        d.text((x0 + bw / 2, h / 2), lb, font=font('Bold', 34), fill=WHITE, anchor='mm')
    return im


def gift_card(gift_img, title, model, rarity, backdrop, glow=0.0):
    """Карточка выпавшего NFT: фон-«бэкдроп», живая модель, подпись модели и редкости."""
    w, h = 600, 700
    im = canvas(w, h)
    c0, c1 = backdrop
    bg = Image.new('RGBA', (w, h - 170), rgba(c1))
    yy, xx = np.mgrid[0:h - 170, 0:w]
    r = np.sqrt((xx - w / 2) ** 2 + (yy - (h - 170) / 2) ** 2) / (w * 0.6)
    k = np.clip(r, 0, 1)[..., None]
    arr = np.array(c0, float) * (1 - k) + np.array(c1, float) * k
    bg = Image.fromarray(np.dstack([arr, np.full((h - 170, w), 255)]).astype(np.uint8), 'RGBA')
    im.alpha_composite(_rounded_mask(bg, 34), (0, 0))
    if gift_img is not None:
        g = gift_img.resize((440, 440), Image.LANCZOS)
        im.alpha_composite(g, (80, 40))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, h - 190, w - 1, h - 1], 34, fill=TG_IN)
    d.rectangle([0, h - 190, w, h - 160], fill=TG_IN)
    d.text((40, h - 140), title, font=font('Heavy', 44), fill=WHITE, anchor='lm')
    d.text((40, h - 82), 'Модель', font=font('Regular', 30), fill=(140, 160, 180), anchor='lm')
    d.text((w - 40, h - 82), f'{model} · {rarity}', font=font('Bold', 32), fill=GOLD, anchor='rm')
    d.text((40, h - 36), 'Подарок · NFT', font=font('Regular', 26), fill=(120, 140, 160), anchor='lm')
    return im


def toast_img(text, sub):
    w, h = 640, 170
    im = canvas(w, h)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 34, fill=(60, 20, 26, 245), outline=RED, width=4)
    d.text((110, 62), text, font=font('Bold', 36), fill=WHITE, anchor='lm')
    d.text((110, 112), sub, font=font('Regular', 28), fill=(255, 190, 190), anchor='lm')
    d.rounded_rectangle([34, 52, 82, 112], 8, fill=RED)                                       # замок
    d.arc([40, 22, 76, 70], 180, 360, fill=RED, width=8)
    return im


# ------------------------------------------------------------------ эффекты
def glitch_img(im, k, seed=0):
    a = np.asarray(im).copy()
    rng = np.random.default_rng(int(k * 1000) + seed)
    h = a.shape[0]
    for _ in range(int(4 + 10 * k)):
        y0 = int(rng.uniform(0, h - 10))
        hh = int(rng.uniform(4, 30))
        sh = int(rng.uniform(-40, 40) * k)
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], sh, axis=1)
    out = a.copy()
    out[..., 0] = np.roll(a[..., 0], int(6 * k), axis=1)
    out[..., 2] = np.roll(a[..., 2], -int(6 * k), axis=1)
    return Image.fromarray(out, 'RGBA')


def vignette(im, strength=0.55, color=(0, 0, 0)):
    m = _vig_mask()
    v = Image.new('RGBA', im.size, rgba(color))
    v.putalpha(m.point(lambda x: int(x * strength)))
    return Image.alpha_composite(im, v)


@functools.lru_cache(maxsize=1)
def _vig_mask():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    m = np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * 255
    return Image.fromarray(m.astype(np.uint8), 'L')


def tint(im, color, a):
    if a <= 0:
        return im
    t = Image.new('RGBA', im.size, rgba(color, int(255 * min(1, a))))
    return Image.alpha_composite(im, t)


@functools.lru_cache(maxsize=4)
def _fisheye_map(n, k):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u, v = (xx - n / 2) / (n / 2), (yy - n / 2) / (n / 2)
    r = np.sqrt(u * u + v * v)
    f = 1 + k * r * r
    su, sv = u / f, v / f
    mx = (su * (n / 2) + n / 2).clip(0, n - 1).astype(np.int32)
    my = (sv * (n / 2) + n / 2).clip(0, n - 1).astype(np.int32)
    return mx, my, r <= 1.0


def fisheye(im, k=0.9):
    """Вид в дверной глазок: круг с бочкообразным искажением (im квадратный)."""
    n = im.width
    mx, my, inside = _fisheye_map(n, k)
    a = np.asarray(im)
    out = a[my, mx].copy()
    out[~inside] = 0
    return Image.fromarray(out, 'RGBA')
