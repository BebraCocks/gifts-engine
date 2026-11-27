"""Мисед кодом по оригинальному референсу автора (projects/58-missed-new-year/refs/missed_original.jpg):
мягкий «пластилин»: светлая персиково-бежевая кожа, высокая голова-яйцо, маленькие тёмные глаза с бликом
и розоватыми веками, длинные острые уши в стороны (левое чуть ниже), бугорок носа, лёгкая улыбка,
очень тонкая длинная шея, худое тело без одежды.

    import art
    im = art.missed(dict(look=0.0, blink=0.0, mouth='smile', ear_l=0.0, ear_r=0.0))   # RGBA, якорь — низ по центру
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt

SS = 2
W, H = 1000, 1500                      # холст спрайта до уменьшения (×SS внутри)
SKIN = np.array([238, 212, 194], float)
SKIN_SH = np.array([190, 150, 158], float)     # тени — в розово-сиреневый, как на референсе
LID = (214, 160, 160)


def _mask(fn):
    m = Image.new('L', (W * SS, H * SS), 0)
    fn(ImageDraw.Draw(m))
    return m


def _P(pts):
    return [(x * SS, y * SS) for x, y in pts]


def _shade(mask, light=(-0.45, -0.6), round_r=0.32, spec=0.35, base=SKIN, shadow=SKIN_SH):
    """Объёмная заливка маски: края темнее (скругление), свет сверху-слева, мягкий блик."""
    a = np.asarray(mask, np.float32) / 255
    bb = mask.getbbox()
    if not bb:
        return None
    x0, y0, x1, y1 = bb
    w, h = x1 - x0, y1 - y0
    d = distance_transform_edt(a > 0.5)
    r = max(1.0, round_r * min(w, h))
    s = np.sqrt(np.clip(d / r, 0, 1))                         # 0 у края → 1 внутри
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    u = (xx - (x0 + x1) / 2) / (w / 2 + 1e-6)
    v = (yy - (y0 + y1) / 2) / (h / 2 + 1e-6)
    lit = np.clip(0.62 - 0.32 * (u * light[0] + v * light[1]) * -1, 0, 1)   # сторона к свету светлее
    k = np.clip(0.35 + 0.65 * s * (0.55 + 0.45 * lit), 0, 1)[..., None]
    col = shadow + (base - shadow) * k
    sp = np.exp(-(((u - light[0] * 0.45) ** 2) / 0.05 + ((v - light[1] * 0.45) ** 2) / 0.07)) * spec
    col = col + (255 - col) * sp[..., None]
    rgba = np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA')


def _rim(mask, col=(150, 105, 115), w=2.2, alpha=150):
    """Мягкий тёмный контур по краю (не чёрная обводка)."""
    edge = mask.filter(ImageFilter.MaxFilter(int(w * SS) * 2 + 1))
    ring = Image.fromarray(np.clip(np.asarray(edge, np.int16) - np.asarray(mask, np.int16), 0, 255).astype(np.uint8))
    ring = ring.filter(ImageFilter.GaussianBlur(1.2 * SS)).point(lambda p: p * alpha // 255)
    lay = Image.new('RGBA', mask.size, col + (0,))
    lay.putalpha(ring)
    return lay


def _layer(im, mask, rim=(150, 105, 115), **kw):
    """Заливка маски объёмом; считается только в рамке маски (быстро)."""
    bb = mask.getbbox()
    if not bb:
        return
    pad = 12 * SS
    box = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(mask.width, bb[2] + pad), min(mask.height, bb[3] + pad))
    m = mask.crop(box)
    sh = _shade(m, **kw)
    if sh is not None:
        im.alpha_composite(sh, box[:2])
        im.alpha_composite(_rim(m, col=rim), box[:2])


def _overlay(im, mask, col, alpha=255):
    lay = Image.new('RGBA', im.size, tuple(col[:3]) + (0,))
    lay.putalpha(mask.point(lambda v: v * alpha // 255))
    im.alpha_composite(lay)


def _capsule(d, pts, w):
    """Ломаная толстой «колбасой» со скруглёнными концами."""
    pts = _P(pts)
    d.line(pts, fill=255, width=int(w * SS), joint='curve')
    r = w * SS / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)


def missed(p=None):
    p = p or {}
    look = p.get('look', 0.0)            # -1..1 поворот головы
    blink = p.get('blink', 0.0)
    ear_l, ear_r = p.get('ear_l', 0.0), p.get('ear_r', 0.0)    # -1 опущено … 1 поднято
    tilt = p.get('tilt', 0.0)            # наклон головы, градусы
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    cx = W / 2
    hx = cx + look * 30                  # центр головы
    top, chin = 130, 770                 # макушка и подбородок
    # --- тело и шея одной маской: узкие покатые плечи, очень тонкая шея плавно расширяется
    def torso(d):
        d.polygon(_P([(hx - 34, chin - 70), (hx + 34, chin - 70), (cx + 44, 900), (cx + 105, 950), (cx + 170, 990),
                      (cx + 200, 1060), (cx + 205, 1500), (cx - 205, 1500), (cx - 200, 1060), (cx - 170, 990),
                      (cx - 105, 950), (cx - 44, 900)]), fill=255)
    body = _mask(torso).filter(ImageFilter.GaussianBlur(16 * SS)).point(lambda v: 255 if v > 128 else 0)
    _layer(im, body, round_r=0.5, spec=0.12)
    neck = body
    dr = ImageDraw.Draw(im)
    for sgn in (-1, 1):                  # ключицы и ямка между ними
        dr.arc(_P([(cx + (10 if sgn > 0 else -150), 975), (cx + (150 if sgn > 0 else -10), 1025)]),
               200 if sgn > 0 else 270, 270 if sgn > 0 else 340, fill=(218, 178, 176, 255), width=3 * SS)
    dr.line(_P([(cx, 1040), (cx, 1170)]), fill=(224, 190, 184, 255), width=2 * SS)
    arm = p.get('arm')
    if arm:                              # тонкие руки: «mug» — кружка у груди, «reach» — протягивает вправо
        if arm == 'mug':
            path = [(cx + 178, 1040), (cx + 235, 1260), (cx + 95, 1250)]
            hand = (cx + 72, 1240)
        else:
            path = [(cx + 178, 1040), (cx + 300, 990), (cx + 405, 935)]
            hand = (cx + 435, 920)
        am = _mask(lambda d: _capsule(d, path, 48))
        _layer(im, am, base=SKIN * 0.97, rim=(140, 95, 105), round_r=0.5, spec=0.12)
        hm2 = _mask(lambda d: d.ellipse(_P([(hand[0] - 38, hand[1] - 32), (hand[0] + 38, hand[1] + 32)]), fill=255))
        _layer(im, hm2, rim=(140, 95, 105), round_r=0.5, spec=0.15)
    # тень головы на шее
    sh = Image.new('L', im.size, 0)
    ImageDraw.Draw(sh).ellipse(_P([(hx - 70, chin - 50), (hx + 70, chin + 40)]), fill=140)
    sh = sh.filter(ImageFilter.GaussianBlur(18 * SS))
    neck_a = np.asarray(neck, np.float32) / 255
    sha = (np.asarray(sh, np.float32) * neck_a).astype(np.uint8)
    lay = Image.new('RGBA', im.size, (170, 120, 135, 0)); lay.putalpha(Image.fromarray(sha))
    im.alpha_composite(lay)

    # --- уши: длинные острые, в стороны, чуть вверх; кончик светлее
    def ear(sgn, lift):
        bx, by = hx + sgn * 185, 560
        drop = 40 if sgn < 0 else -80          # левое чуть вниз, правое вверх — как на референсе
        tip = (hx + sgn * 455, by + drop - lift * 70)
        return [(bx - sgn * 20, by - 80), (tip[0] - sgn * 110, tip[1] - 22), (tip[0] - sgn * 8, tip[1] - 12), tip,
                (tip[0] - sgn * 10, tip[1] + 16), (tip[0] - sgn * 130, tip[1] + 44), (bx - sgn * 10, by + 70)]
    for sgn, lift in ((-1, ear_l), (1, ear_r)):
        pts = ear(sgn, lift)
        m = _mask(lambda d, pts=pts: d.polygon(_P(pts), fill=255)).filter(ImageFilter.GaussianBlur(6 * SS))
        m = m.point(lambda v: 255 if v > 110 else 0)
        _layer(im, m, round_r=0.5, spec=0.2, light=(-0.2, -0.8))
        # внутренняя розовая часть уха
        inner = [(pts[0][0] + sgn * 30, pts[0][1] + 55), (pts[3][0] - sgn * 60, pts[3][1] + 4), (pts[6][0] + sgn * 30, pts[6][1] - 45)]
        mi = _mask(lambda d, inner=inner: d.polygon(_P(inner), fill=255)).filter(ImageFilter.GaussianBlur(9 * SS))
        lay = Image.new('RGBA', im.size, (215, 150, 155, 0)); lay.putalpha(mi.point(lambda v: v * 150 // 255))
        im.alpha_composite(lay)

    # --- голова: высокое яйцо, купол шире, к подбородку сужается
    def head(d):
        pts = []
        cy = 430
        for k in range(200):
            a = 2 * math.pi * k / 200
            sx, sy = math.cos(a), math.sin(a)
            if sy < 0:                       # верх — купол
                x, y = 225 * sx, (cy - top) * sy
            else:                            # низ — сужается к узкому подбородку
                narrow = 1 - 0.30 * sy ** 3.0
                x, y = 225 * sx * narrow, (chin - cy) * sy
            pts.append((hx + x, cy + y))
        d.polygon(_P(pts), fill=255)
    hm = _mask(head)
    _layer(im, hm, round_r=0.42, spec=0.45, light=(-0.35, -0.75))

    d = ImageDraw.Draw(im)
    # --- глаза: маленькие тёмные, розоватые веки вокруг
    ey = 548
    for sgn in (-1, 1):
        ex = hx + sgn * 84 + look * 14
        lid = Image.new('L', im.size, 0)
        ImageDraw.Draw(lid).ellipse(_P([(ex - 62, ey - 46), (ex + 62, ey + 50)]), fill=255)
        lid = lid.filter(ImageFilter.GaussianBlur(12 * SS))
        lay = Image.new('RGBA', im.size, LID + (0,)); lay.putalpha(lid.point(lambda v: v * 210 // 255))
        im.alpha_composite(lay)
        k = max(0.06, 1 - blink)
        ry = 36 * k
        d = ImageDraw.Draw(im)
        d.ellipse(_P([(ex - 37, ey - ry), (ex + 37, ey + ry)]), fill=(22, 14, 20, 255))
        if k > 0.35:
            d.ellipse(_P([(ex - 4, ey - ry * 0.75), (ex + 10, ey - ry * 0.75 + 14)]), fill=(255, 255, 255, 255))
            d.ellipse(_P([(ex - 16, ey + ry * 0.35), (ex - 9, ey + ry * 0.35 + 7)]), fill=(120, 110, 140, 255))
        # верхнее веко — мягкая складка
        d.arc(_P([(ex - 46, ey - ry - 12), (ex + 46, ey + ry + 4)]), 200, 340, fill=(205, 150, 152, 255), width=3 * SS)
    # --- нос: маленький бугорок с тенью снизу
    nx, ny = hx + look * 22, 622
    nb = Image.new('L', im.size, 0)
    ImageDraw.Draw(nb).ellipse(_P([(nx - 34, ny - 30), (nx + 34, ny + 24)]), fill=255)
    nb = nb.filter(ImageFilter.GaussianBlur(5 * SS))
    lay = Image.new('RGBA', im.size, (248, 222, 210, 0)); lay.putalpha(nb.point(lambda v: v * 200 // 255))
    im.alpha_composite(lay)
    d = ImageDraw.Draw(im)
    d.arc(_P([(nx - 28, ny - 6), (nx + 28, ny + 26)]), 20, 160, fill=(200, 145, 145, 255), width=3 * SS)
    # --- рот
    mx, my = hx + look * 18, 688
    mo = p.get('mouth', 'smile')
    if mo == 'smile':
        d.arc(_P([(mx - 34, my - 18), (mx + 34, my + 14)]), 25, 150, fill=(165, 100, 110, 255), width=4 * SS)
    elif mo == 'flat':
        d.line(_P([(mx - 22, my), (mx + 22, my)]), fill=(165, 100, 110, 255), width=4 * SS)
    elif mo == 'o':
        d.ellipse(_P([(mx - 11, my - 10), (mx + 11, my + 12)]), fill=(120, 60, 75, 255))
    # лёгкий румянец
    for sgn in (-1, 1):
        bl = Image.new('L', im.size, 0)
        ImageDraw.Draw(bl).ellipse(_P([(hx + sgn * 120 - 40, 620), (hx + sgn * 120 + 40, 665)]), fill=255)
        lay = Image.new('RGBA', im.size, (235, 160, 160, 0)); lay.putalpha(bl.filter(ImageFilter.GaussianBlur(14 * SS)).point(lambda v: v * 90 // 255))
        im.alpha_composite(lay)
    if tilt:
        im = im.rotate(tilt, resample=Image.BICUBIC, center=(cx * SS, 1000 * SS))
    return im.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- Димон
DSKIN = np.array([250, 214, 188], float)
DSKIN_SH = np.array([205, 150, 140], float)
HOOD = np.array([74, 122, 222], float)
HOOD_SH = np.array([40, 66, 150], float)
HAIR = np.array([120, 76, 44], float)
HAIR_SH = np.array([70, 40, 24], float)


def dimon(p=None):
    """Димон (сосед): круглая голова, тёмно-русые лохматые волосы, синее худи. Верх тела, низ холста — пояс.
    eyes: open/closed/wide/half; mouth: smile/open/o/flat/shout/sleep/brush; arms: down/phone/count/plead/up;
    props: sock (носок на руке)."""
    p = p or {}
    im = Image.new('RGBA', (W * SS, H * SS), (0, 0, 0, 0))
    cx, hx, hy = W / 2, W / 2 + p.get('look', 0) * 25, 560
    arms = p.get('arms', 'down')
    HOOD = np.array(p.get('hood', [74, 122, 222]), float)
    HOOD_SH = HOOD * 0.55
    HAIR = np.array(p.get('hair', [120, 76, 44]), float)
    HAIR_SH = HAIR * 0.58
    # худи
    hood = _mask(lambda d: d.rounded_rectangle(_P([(cx - 250, 860), (cx + 250, 1560)]), 170 * SS, fill=255))
    _layer(im, hood, base=HOOD, shadow=HOOD_SH, rim=(30, 40, 90), round_r=0.35, spec=0.12)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(_P([(cx - 130, 1230), (cx + 130, 1380)]), 40 * SS, outline=tuple(int(c) for c in HOOD * 0.8) + (255,), width=5 * SS)
    for sgn in (-1, 1):
        d.line(_P([(cx + sgn * 40, 900), (cx + sgn * 46, 1060)]), fill=(235, 240, 255, 255), width=6 * SS)
    # капюшон-воротник
    col = _mask(lambda d: d.rounded_rectangle(_P([(cx - 170, 820), (cx + 170, 930)]), 50 * SS, fill=255))
    _layer(im, col, base=HOOD * 1.06, shadow=HOOD_SH, rim=(30, 40, 90), round_r=0.5, spec=0.1)
    neck = _mask(lambda d: d.rounded_rectangle(_P([(hx - 50, 740), (hx + 50, 880)]), 40 * SS, fill=255))
    _layer(im, neck, base=DSKIN * 0.95, shadow=DSKIN_SH, round_r=0.5, spec=0.05)
    # уши
    for sgn in (-1, 1):
        em = _mask(lambda d, sgn=sgn: d.ellipse(_P([(hx + sgn * 215 - 36, hy - 10), (hx + sgn * 215 + 36, hy + 80)]), fill=255))
        _layer(im, em, base=DSKIN, shadow=DSKIN_SH, round_r=0.5, spec=0.05)
    # голова
    head = _mask(lambda d: d.ellipse(_P([(hx - 225, hy - 250), (hx + 225, hy + 250)]), fill=255))
    _layer(im, head, base=DSKIN, shadow=DSKIN_SH, rim=(150, 100, 90), round_r=0.42, spec=0.3)

    # волосы: шапка с прядями-зубцами
    def hair(d):
        pts = []
        for k in range(6, 175, 6):
            a = math.radians(180 + k)
            r = 250 + (22 if (k // 6) % 2 else 0)
            pts.append((hx + r * math.cos(a), hy - 30 + r * 1.02 * math.sin(a)))
        pts += [(hx + 238, hy - 10), (hx + 200, hy - 120)]
        for k in range(7):                     # чёлка зубцами
            x = hx + 200 - k * 66
            pts += [(x - 33, hy - 70 if k % 2 else hy - 40), (x - 66, hy - 140)]
        pts += [(hx - 215, hy - 110)]
        d.polygon(_P(pts), fill=255)
    hm = _mask(hair)
    _layer(im, hm, base=HAIR, shadow=HAIR_SH, rim=(50, 28, 16), round_r=0.3, spec=0.25)
    d = ImageDraw.Draw(im)
    # брови
    e = p.get('eyes', 'open')
    by = hy - 40 if e != 'wide' else hy - 62
    for sgn in (-1, 1):
        tilt_b = {'plead': 18, 'shout': -14}.get(p.get('brows', ''), 0) * sgn
        d.line(_P([(hx + sgn * 120, by - tilt_b), (hx + sgn * 40, by + tilt_b)]), fill=(90, 54, 30, 255), width=11 * SS)
    # глаза
    for sgn in (-1, 1):
        ex, ey = hx + sgn * 82 + p.get('look', 0) * 10, hy + 30
        if e == 'closed':
            d.arc(_P([(ex - 30, ey - 22), (ex + 30, ey + 16)]), 20, 160, fill=(50, 30, 30, 255), width=6 * SS)
        else:
            rw, rh = {'open': (24, 30), 'half': (24, 12), 'wide': (34, 42)}[e]
            if e == 'wide':
                d.ellipse(_P([(ex - rw - 14, ey - rh - 14), (ex + rw + 14, ey + rh + 14)]), fill=(255, 255, 255, 255),
                          outline=(60, 40, 40, 255), width=3 * SS)
            d.ellipse(_P([(ex - rw, ey - rh), (ex + rw, ey + rh)]), fill=(40, 28, 30, 255))
            d.ellipse(_P([(ex - 8, ey - rh * 0.6), (ex + 6, ey - rh * 0.6 + 13)]), fill=(255, 255, 255, 255))
            if e == 'half':
                d.line(_P([(ex - rw - 6, ey - rh), (ex + rw + 6, ey - rh)]), fill=(70, 45, 40, 255), width=6 * SS)
    # нос, румянец
    d.arc(_P([(hx - 16, hy + 70), (hx + 16, hy + 110)]), 300, 90, fill=(205, 150, 135, 255), width=5 * SS)
    for sgn in (-1, 1):
        bl = Image.new('L', im.size, 0)
        ImageDraw.Draw(bl).ellipse(_P([(hx + sgn * 135 - 45, hy + 100), (hx + sgn * 135 + 45, hy + 150)]), fill=255)
        _overlay(im, bl.filter(ImageFilter.GaussianBlur(14 * SS)), (240, 150, 140), 110)
    d = ImageDraw.Draw(im)
    mo, mx, my = p.get('mouth', 'smile'), hx, hy + 165
    LIP = (120, 50, 55, 255)
    if mo == 'smile':
        d.arc(_P([(mx - 50, my - 34), (mx + 50, my + 22)]), 25, 155, fill=LIP, width=7 * SS)
    elif mo == 'flat':
        d.line(_P([(mx - 34, my), (mx + 34, my)]), fill=LIP, width=7 * SS)
    elif mo == 'sleep':
        d.ellipse(_P([(mx - 10, my - 6), (mx + 10, my + 10)]), fill=LIP)
    elif mo in ('open', 'o', 'shout', 'brush'):
        rw, rh = {'open': (38, 26), 'o': (20, 24), 'shout': (62, 58), 'brush': (30, 18)}[mo]
        d.ellipse(_P([(mx - rw, my - rh), (mx + rw, my + rh)]), fill=(110, 30, 40, 255), outline=LIP, width=4 * SS)
        if mo in ('open', 'shout'):
            d.ellipse(_P([(mx - rw * 0.6, my + rh * 0.2), (mx + rw * 0.6, my + rh * 0.95)]), fill=(230, 110, 120, 255))
        if mo == 'brush':                      # зубная щётка торчит изо рта
            d.rounded_rectangle(_P([(mx + 5, my - 9), (mx + 190, my + 9)]), 8 * SS, fill=(90, 210, 200, 255))
            d.rounded_rectangle(_P([(mx - 30, my - 14), (mx + 20, my + 14)]), 6 * SS, fill=(245, 245, 255, 255))
    if p.get('glasses'):
        d = ImageDraw.Draw(im)
        for sgn in (-1, 1):
            ex, ey = hx + sgn * 82 + p.get('look', 0) * 10, hy + 30
            d.rounded_rectangle(_P([(ex - 58, ey - 46), (ex + 58, ey + 46)]), 22 * SS, outline=(30, 30, 40, 255), width=8 * SS)
        d.line(_P([(hx - 24, hy + 22), (hx + 24, hy + 22)]), fill=(30, 30, 40, 255), width=8 * SS)
    # руки
    def hand_at(x, y, sock=False):
        hm3 = _mask(lambda d: d.ellipse(_P([(x - 42, y - 40), (x + 42, y + 40)]), fill=255))
        if sock:
            _layer(im, hm3, base=np.array([240, 240, 240.]), shadow=np.array([170, 170, 190.]), rim=(90, 90, 110), round_r=0.5)
            ImageDraw.Draw(im).line(_P([(x - 40, y + 5), (x + 40, y + 5)]), fill=(230, 80, 80, 255), width=8 * SS)
        else:
            _layer(im, hm3, base=DSKIN, shadow=DSKIN_SH, round_r=0.5, spec=0.1)
    paths = {'down': [[(cx - 230, 950), (cx - 270, 1250), (cx - 250, 1420)], [(cx + 230, 950), (cx + 270, 1250), (cx + 250, 1420)]],
             'phone': [[(cx - 230, 950), (cx - 230, 1220), (cx - 70, 1180)], [(cx + 230, 950), (cx + 230, 1220), (cx + 70, 1180)]],
             'count': [[(cx - 230, 950), (cx - 270, 1250), (cx - 250, 1420)], [(cx + 230, 950), (cx + 340, 820), (cx + 330, 640)]],
             'plead': [[(cx - 230, 950), (cx - 160, 800), (cx - 40, 700)], [(cx + 230, 950), (cx + 160, 800), (cx + 40, 700)]],
             'up': [[(cx - 230, 950), (cx - 380, 760), (cx - 420, 560)], [(cx + 230, 950), (cx + 380, 760), (cx + 420, 560)]]}[arms]
    for i, path in enumerate(paths):
        am = _mask(lambda d, path=path: _capsule(d, path, 92))
        _layer(im, am, base=HOOD * 1.03, shadow=HOOD_SH, rim=(30, 40, 90), round_r=0.5, spec=0.1)
        hand_at(*path[-1], sock=(p.get('sock') and i == 0))
    if arms == 'count':                        # пальцы
        n = p.get('fingers', 3)
        x, y = paths[1][-1]
        for k in range(n):
            fm = _mask(lambda d, k=k: _capsule(d, [(x - 30 + k * 20, y - 20), (x - 40 + k * 26, y - 90)], 22))
            _layer(im, fm, base=DSKIN, shadow=DSKIN_SH, round_r=0.5, spec=0.05)
    return im.resize((W, H), Image.LANCZOS)


def dimon_legs(phase=0.0, amp=1.0):
    """Ноги для бега: серые штаны, белые носки. Холст 1000×800, верх — пояс (стык с низом dimon())."""
    im = Image.new('RGBA', (W * SS, 800 * SS), (0, 0, 0, 0))
    cx = W / 2
    for sgn, ph in ((-1, phase), (1, phase + 0.5)):
        a = math.sin(2 * math.pi * ph) * 0.6 * amp
        knee = (cx + sgn * 90 + math.sin(a) * 210, 60 + math.cos(a) * 280)
        b = a - (0.5 + 0.4 * max(0, math.sin(2 * math.pi * ph))) * amp
        foot = (knee[0] + math.sin(b) * 250, knee[1] + math.cos(b) * 250)
        path = [(cx + sgn * 90, 20), knee, foot]

        def leg(d, path=path):
            d.rectangle((0, 0, 1, 1), fill=0)
            pts = _P(path)
            d.line(pts, fill=255, width=120 * SS, joint='curve')
            r = 60 * SS
            for x, y in pts:
                d.ellipse((x - r, y - r, x + r, y + r), fill=255)
        m = Image.new('L', im.size, 0)
        leg(ImageDraw.Draw(m))
        _layer(im, m, base=np.array([120, 124, 140.]), shadow=np.array([70, 72, 90.]), rim=(40, 40, 55), round_r=0.4, spec=0.08)
        fm = Image.new('L', im.size, 0)
        fx, fy = foot
        ImageDraw.Draw(fm).ellipse(_P([(fx - 80, fy - 40), (fx + 80, fy + 45)]), fill=255)
        _layer(im, fm, base=np.array([245, 245, 250.]), shadow=np.array([180, 180, 200.]), rim=(90, 90, 110), round_r=0.5)
    return im.resize((W, 800), Image.LANCZOS)
