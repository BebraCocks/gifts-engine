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


def _layer(im, mask, **kw):
    sh = _shade(mask, **kw)
    if sh is not None:
        im.alpha_composite(sh)
        im.alpha_composite(_rim(mask))


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
