"""2D-персонажи «Подарка по заслугам», нарисованные кодом: плоский стикерный стиль, толстый контур, мягкие тени.

    import chars
    im = chars.missed(pose)   # RGBA 700x1100, якорь — середина низа
Поза — словарь: mouth ('smile','grin','open','o','flat','smirk','shock'), eyes ('open','half','closed','wide','narrow'),
blink 0..1, look -1..1 (поворот головы), arms ('down','up','phone','hips').
"""
import math
from PIL import Image, ImageDraw, ImageFilter, ImageChops

SS = 2
OUT = (26, 22, 40)
LW = 8

def _c(w=700, h=1100):
    return Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))

def _done(im):
    return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)

def S(v):
    if isinstance(v, (list, tuple)):
        o = []
        for x in v:
            o.extend((x[0] * SS, x[1] * SS) if isinstance(x, (list, tuple)) else (x * SS,))
        return o
    return v * SS

def dark(c, k=0.78):
    return tuple(int(x * k) for x in c[:3])

def shape(im, draw_fn, fill, shade_k=0.8, light=True, dx=-0.16, dy=-0.2, outline=True):
    """Заливка фигуры с мягкой тенью снизу-справа и бликом; draw_fn(draw, fill) рисует фигуру."""
    m = Image.new('L', im.size, 0); draw_fn(ImageDraw.Draw(m), 255)
    bb = m.getbbox()
    if not bb:
        return
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    im.paste(Image.new('RGBA', im.size, fill), (0, 0), m)
    sh = ImageChops.offset(m, int(w * dx), int(h * dy))
    shm = ImageChops.subtract(m, sh).filter(ImageFilter.GaussianBlur(9 * SS))
    shm = ImageChops.multiply(shm, m)
    im.paste(Image.new('RGBA', im.size, dark(fill, shade_k) + (255,)), (0, 0), shm)
    if light:
        hl = Image.new('L', im.size, 0)
        ImageDraw.Draw(hl).ellipse((bb[0] + w * 0.2, bb[1] + h * 0.08, bb[0] + w * 0.4, bb[1] + h * 0.2), fill=110)
        im.paste(Image.new('RGBA', im.size, (255, 255, 255, 255)), (0, 0),
                 ImageChops.multiply(hl.filter(ImageFilter.GaussianBlur(7 * SS)), m))
    if outline:
        edge = m.filter(ImageFilter.MaxFilter(LW * SS // 2 * 2 + 1))
        ring = ImageChops.subtract(edge, m)
        im.paste(Image.new('RGBA', im.size, OUT + (255,)), (0, 0), ring)

def mouth(d, cx, cy, kind, w=70):
    L = LW * SS
    if kind == 'smile':
        d.arc(S((cx - w / 2, cy - w / 2.4, cx + w / 2, cy + w / 2.6)), 25, 155, fill=OUT, width=L)
    elif kind == 'smirk':
        d.arc(S((cx - w / 2.2, cy - w / 2.6, cx + w / 1.8, cy + w / 3)), 15, 95, fill=OUT, width=L)
    elif kind == 'flat':
        d.line(S((cx - w / 3, cy + 4, cx + w / 3, cy + 4)), fill=OUT, width=L)
    elif kind == 'grin':
        d.chord(S((cx - w / 1.6, cy - w / 3, cx + w / 1.6, cy + w / 1.5)), 0, 180, fill=(90, 24, 40), outline=OUT, width=L)
        d.rectangle(S((cx - w / 2.1, cy - w / 3 + 10, cx + w / 2.1, cy - w / 3 + 30)), fill=(255, 255, 255))
        d.ellipse(S((cx - w / 4, cy + w / 6, cx + w / 4, cy + w / 2.2)), fill=(236, 100, 110))
    elif kind in ('open', 'o', 'shock'):
        ww, hh = {'open': (w * 0.8, w * 0.6), 'o': (w * 0.4, w * 0.45), 'shock': (w * 0.6, w * 0.9)}[kind]
        d.ellipse(S((cx - ww / 2, cy - hh / 2, cx + ww / 2, cy + hh / 2)), fill=(90, 24, 40), outline=OUT, width=L)
        if kind != 'o':
            d.ellipse(S((cx - ww / 3.2, cy + hh / 8, cx + ww / 3.2, cy + hh / 2 - 6)), fill=(236, 100, 110))

def arms(im, cx, top, col, skin, kind='down', sleeve_w=72):
    d = ImageDraw.Draw(im)
    for sgn in (-1, 1):
        sx = cx + sgn * 175
        if kind == 'up':
            pts, hand = (sx, top + 60, sx + sgn * 110, top - 160), (sx + sgn * 110, top - 160)
        elif kind == 'phone' and sgn == 1:
            pts, hand = (sx, top + 60, cx + 60, top + 150), (cx + 60, top + 150)
        elif kind == 'phone':
            pts, hand = (sx, top + 60, cx - 30, top + 170), (cx - 30, top + 170)
        elif kind == 'hips':
            pts, hand = (sx, top + 60, sx + sgn * 70, top + 200), (sx + sgn * 20, top + 290)
        else:
            pts, hand = (sx, top + 60, sx + sgn * 25, top + 300), (sx + sgn * 25, top + 300)
        def f(dd, fill, pts=pts):
            dd.line(S(pts), fill=fill, width=sleeve_w * SS)
            dd.ellipse(S((pts[0] - sleeve_w / 2, pts[1] - sleeve_w / 2, pts[0] + sleeve_w / 2, pts[1] + sleeve_w / 2)), fill=fill)
        shape(im, f, col, light=False)
        hx, hy = hand
        shape(im, lambda dd, fill: dd.ellipse(S((hx - 34, hy - 30, hx + 34, hy + 34)), fill=fill), skin, light=False)

def torso(im, cx, top, col, w=200):
    def f(d, fill):
        d.rounded_rectangle(S((cx - w, top, cx + w, top + 520)), 120 * SS, fill=fill)
    shape(im, f, col, light=False)

def phone(im, cx, cy, glow=True):
    d = ImageDraw.Draw(im)
    if glow:
        g = Image.new('L', im.size, 0)
        ImageDraw.Draw(g).ellipse(S((cx - 120, cy - 150, cx + 120, cy + 150)), fill=120)
        im.paste(Image.new('RGBA', im.size, (120, 200, 255, 255)), (0, 0), g.filter(ImageFilter.GaussianBlur(30 * SS)))
    d.rounded_rectangle(S((cx - 55, cy - 95, cx + 55, cy + 95)), 18 * SS, fill=(30, 34, 48), outline=OUT, width=LW * SS)
    d.rounded_rectangle(S((cx - 44, cy - 82, cx + 44, cy + 82)), 12 * SS, fill=(130, 200, 255) if glow else (20, 24, 34))

# ---------------------------------------------------------------- Мисед
SKIN_M = (246, 204, 188)

def missed(p=None):
    p = p or {}
    im = _c(); cx = 350
    look = p.get('look', 0) * 22
    torso(im, cx, 600, (34, 34, 44), 170)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(S((cx - 120, 590, cx + 120, 680)), 50 * SS, fill=(48, 48, 60), outline=OUT, width=LW * SS)
    for sgn in (-1, 1):
        d.line(S((cx + sgn * 32, 680, cx + sgn * 36, 790)), fill=(210, 210, 222), width=6 * SS)
    d.rounded_rectangle(S((cx - 105, 860, cx + 105, 960)), 30 * SS, outline=(60, 60, 76), width=6 * SS)
    shape(im, lambda dd, fill: dd.rounded_rectangle(S((cx - 26, 500, cx + 26, 640)), 26 * SS, fill=fill), SKIN_M, light=False)
    hx = cx + look
    for sgn in (-1, 1):                               # уши строго в стороны
        ex = hx + sgn * 150
        shape(im, lambda dd, fill, ex=ex, sgn=sgn: dd.polygon(S([(ex, 300), (ex + sgn * 250, 330), (ex, 400)]), fill=fill),
              SKIN_M, light=False)
        ImageDraw.Draw(im).polygon(S([(ex + sgn * 8, 322), (ex + sgn * 190, 336), (ex + sgn * 8, 380)]), fill=(232, 168, 160))
    # голова: яйцо, шире сверху
    def head(dd, fill):
        pts = []
        for k in range(120):
            a = 2 * math.pi * k / 120
            r = 1 + 0.12 * math.sin(a - math.pi / 2) * -1      # шире сверху
            pts.append((hx + 175 * math.cos(a) * (1.06 if math.sin(a) < 0 else 0.9), 300 + 255 * math.sin(a) * (r if math.sin(a) < 0 else 1)))
        dd.polygon(S(pts), fill=fill)
    shape(im, head, SKIN_M)
    d = ImageDraw.Draw(im)
    e = p.get('eyes', 'open'); blink = p.get('blink', 0)
    k = {'open': 1, 'half': 0.55, 'closed': 0.06, 'wide': 1.2, 'narrow': 0.42}[e] * (1 - 0.94 * blink)
    for sgn in (-1, 1):                               # огромные миндалевидные глаза, внешний угол выше
        ex, ey = hx + sgn * 82, 368
        pts = []
        for j in range(60):
            a = 2 * math.pi * j / 60
            x = ex + 78 * math.cos(a)
            y = ey + 48 * k * math.sin(a) * (1.15 if math.sin(a) > 0 else 0.85)
            y -= sgn * (x - ex) * 0.32 * (-1)          # наклон: внешний угол вверх
            pts.append((x, y))
        d.polygon(S(pts), fill=(10, 10, 18), outline=OUT)
        if k > 0.3:
            d.ellipse(S((ex - 40, ey - 30 * k, ex - 12, ey - 30 * k + 28)), fill=(255, 255, 255))
            d.ellipse(S((ex + 20, ey + 8 * k, ex + 32, ey + 8 * k + 12)), fill=(170, 185, 240))
    for sgn in (-1, 1):
        d.ellipse(S((hx + sgn * 8 - 4, 448, hx + sgn * 8 + 4, 456)), fill=(170, 110, 105))
    mouth(d, hx, 492, p.get('mouth', 'smile'), 62)
    if p.get('arms'):
        arms(im, cx, 640, (34, 34, 44), SKIN_M, p['arms'], 64)
    return _done(im)

# ---------------------------------------------------------------- люди
def human(p, skin, top_col, hair_fn, brow_col, extra_top=None, extra_face=None):
    im = _c(); cx = 350
    look = p.get('look', 0) * 18
    torso(im, cx, 640, top_col, 205)
    if extra_top:
        extra_top(im, cx)
    shape(im, lambda dd, fill: dd.rounded_rectangle(S((cx - 42, 560, cx + 42, 680)), 30 * SS, fill=fill), skin, light=False)
    hx = cx + look
    for sgn in (-1, 1):
        shape(im, lambda dd, fill, sgn=sgn: dd.ellipse(S((hx + sgn * 196 - 36, 345, hx + sgn * 196 + 36, 440)), fill=fill), skin, light=False)
    shape(im, lambda dd, fill: dd.ellipse(S((hx - 200, 120, hx + 200, 610)), fill=fill), skin)
    hair_fn(im, hx)
    d = ImageDraw.Draw(im)
    e = p.get('eyes', 'open'); blink = p.get('blink', 0)
    k = {'open': 1, 'half': 0.55, 'closed': 0.08, 'wide': 1.35, 'narrow': 0.4}[e] * (1 - 0.92 * blink)
    for sgn in (-1, 1):
        ex, ey = hx + sgn * 76, 390
        d.ellipse(S((ex - 34, ey - 40 * k, ex + 34, ey + 40 * k)), fill=(255, 255, 255), outline=OUT, width=LW * SS)
        if k > 0.25:
            pr = min(22, 34 * k)
            px = ex + look * 0.6
            d.ellipse(S((px - pr, ey - pr + 4, px + pr, ey + pr + 4)), fill=(50, 40, 60))
            d.ellipse(S((px - pr * 0.55, ey - pr * 0.6, px - pr * 0.05, ey - pr * 0.1)), fill=(255, 255, 255))
    up = {'wide': -22, 'open': -6, 'half': 4, 'narrow': 10}.get(e, 0)
    for sgn in (-1, 1):
        if p.get('angry_brows'):
            d.line(S((hx + sgn * 40, 336 + up, hx + sgn * 112, 304 + up)), fill=brow_col, width=13 * SS)
        else:
            d.line(S((hx + sgn * 42, 318 + up, hx + sgn * 112, 310 + up)), fill=brow_col, width=13 * SS)
    for sgn in (-1, 1):                               # румянец
        g = Image.new('L', im.size, 0)
        ImageDraw.Draw(g).ellipse(S((hx + sgn * 120 - 34, 460, hx + sgn * 120 + 34, 500)), fill=90)
        im.paste(Image.new('RGBA', im.size, (240, 120, 120, 255)), (0, 0), g.filter(ImageFilter.GaussianBlur(8 * SS)))
    d = ImageDraw.Draw(im)
    d.arc(S((hx - 18, 420, hx + 18, 478)), 290, 70, fill=dark(skin, 0.7), width=6 * SS)
    mouth(d, hx, 520, p.get('mouth', 'smile'), 80)
    if extra_face:
        extra_face(im, hx)
    if p.get('arms'):
        arms(im, cx, 680, top_col, skin, p['arms'], 78)
        if p['arms'] == 'phone':
            phone(im, cx + 20, 830, p.get('glow', True))
    return _done(im)

def dimon(p=None):
    p = p or {}
    skin = (252, 216, 190)
    def hair(im, hx):
        def f(d, fill):
            pts = [(hx - 210, 330), (hx - 205, 200), (hx - 140, 120), (hx - 40, 88), (hx + 70, 92), (hx + 160, 128),
                   (hx + 212, 210), (hx + 212, 330), (hx + 170, 245), (hx + 110, 270), (hx + 70, 215), (hx + 10, 262),
                   (hx - 50, 212), (hx - 110, 268), (hx - 160, 236)]
            d.polygon(S(pts), fill=fill)
        shape(im, f, (128, 78, 46))
    def top(im, cx):
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(S((cx - 135, 620, cx + 135, 720)), 50 * SS, fill=(92, 148, 240), outline=OUT, width=LW * SS)
        for sgn in (-1, 1):
            d.line(S((cx + sgn * 36, 720, cx + sgn * 40, 830)), fill=(255, 255, 255), width=7 * SS)
        d.rounded_rectangle(S((cx - 115, 900, cx + 115, 1000)), 30 * SS, outline=(52, 100, 196), width=6 * SS)
    return human(p, skin, (70, 124, 226), hair, (100, 60, 34), top)

def oleg(p=None):
    p = p or {}
    skin = (236, 196, 166)
    p = dict(p); p.setdefault('angry_brows', True)
    def hair(im, hx):
        def f(d, fill):
            pts = [(hx - 205, 320), (hx - 200, 190), (hx - 120, 112), (hx + 10, 92), (hx + 140, 110), (hx + 210, 180),
                   (hx + 210, 320), (hx + 185, 220), (hx + 80, 185), (hx - 40, 180), (hx - 160, 215)]
            d.polygon(S(pts), fill=fill)
        shape(im, f, (40, 36, 46))
        d = ImageDraw.Draw(im)
        for k in range(4):
            d.arc(S((hx - 160 + k * 70, 105, hx + 20 + k * 70, 215)), 205, 300, fill=(96, 90, 108), width=5 * SS)
    def top(im, cx):
        d = ImageDraw.Draw(im)
        d.polygon(S([(cx - 75, 650), (cx, 840), (cx + 75, 650)]), fill=(236, 236, 242), outline=OUT)
        for sgn in (-1, 1):
            shape(im, lambda dd, fill, sgn=sgn: dd.polygon(S([(cx + sgn * 75, 650), (cx + sgn * 12, 860), (cx + sgn * 165, 720)]), fill=fill),
                  (66, 60, 72), light=False)
        d = ImageDraw.Draw(im)
        for k in range(16):
            a = math.pi * (0.12 + 0.76 * k / 15)
            x, y = cx + 92 * math.cos(a), 655 + 130 * math.sin(a)
            d.ellipse(S((x - 10, y - 10, x + 10, y + 10)), fill=(246, 200, 64), outline=(150, 110, 20), width=2 * SS)
    return human(p, skin, (46, 42, 52), hair, (30, 26, 36), top)
