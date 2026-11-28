"""Пять стилей первого кадра «Низшего», всё кодом (просьба автора 2026-11-24: персонажи ближе к реальным людям).
Одна геометрия героя и коридора, пять способов отрисовки:
  A кино-нуар (объём по карте нормалей, контровой свет, туман)   B графический роман (контур, 2 тона, растр)
  C плоская иллюстрация                                          D пиксель-арт
  E карандаш и акварель
    python -B projects/63-nizshii-1/style_probes.py      -> build/review/style_A..E.png + styles_sheet.jpg"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops  # noqa: E402
from scipy import ndimage  # noqa: E402

W, H = 1080, 1920
SS = 2
F = HERE / 'fonts'
rng = np.random.default_rng(7)


def fnt(name, size):
    return ImageFont.truetype(str(F / name), size)


# ------------------------------------------------------------------ геометрия героя (стоит, прислонился к стене)
def capsule(d, a, b, ra, rb, fill=255):
    (x0, y0), (x1, y1) = a, b
    ang = math.atan2(y1 - y0, x1 - x0) + math.pi / 2
    pts = [(x0 + ra * math.cos(ang), y0 + ra * math.sin(ang)), (x1 + rb * math.cos(ang), y1 + rb * math.sin(ang)),
           (x1 - rb * math.cos(ang), y1 - rb * math.sin(ang)), (x0 - ra * math.cos(ang), y0 - ra * math.sin(ang))]
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
    d.ellipse(((x0 - ra) * SS, (y0 - ra) * SS, (x0 + ra) * SS, (y0 + ra) * SS), fill=fill)
    d.ellipse(((x1 - rb) * SS, (y1 - rb) * SS, (x1 + rb) * SS, (y1 + rb) * SS), fill=fill)


def smooth_poly(pts, n=8):
    """замкнутый Катмулл-Ром по точкам"""
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    return out


def mask(fn):
    m = Image.new('L', (W * SS, H * SS), 0)
    fn(ImageDraw.Draw(m))
    return m.resize((W, H), Image.LANCZOS)


TORSO = smooth_poly([(540, 800), (640, 812), (700, 826), (738, 858), (756, 910), (742, 1000), (700, 1080), (680, 1180), (690, 1230),
                     (540, 1240), (390, 1230), (400, 1180), (380, 1080), (338, 1000), (324, 910), (342, 858), (380, 826), (440, 812)])
SHORTS = smooth_poly([(392, 1200), (540, 1212), (688, 1200), (700, 1300), (708, 1360), (560, 1372), (540, 1330),
                      (520, 1372), (372, 1360), (380, 1300)])
L_ARM = [(352, 872), (318, 1090), (300, 1300)]          # правая рука героя (слева на экране)
R_ARM = [(728, 872), (770, 1080), (800, 1290)]          # левая рука с больным локтем
L_LEG = [(462, 1340), (452, 1580), (448, 1790)]
R_LEG = [(618, 1340), (630, 1580), (636, 1790)]


def parts():
    P = {}
    P['torso'] = mask(lambda d: d.polygon([(x * SS, y * SS) for x, y in TORSO], fill=255))
    P['neck'] = mask(lambda d: capsule(d, (540, 740), (540, 830), 40, 52))
    P['head'] = mask(lambda d: (d.ellipse((462 * SS, 560 * SS, 618 * SS, 772 * SS), fill=255),
                                d.ellipse((450 * SS, 650 * SS, 478 * SS, 708 * SS), fill=255),
                                d.ellipse((602 * SS, 650 * SS, 630 * SS, 708 * SS), fill=255)))
    for name, pts, r in (('arm_l', L_ARM, (30, 22, 19)), ('arm_r', R_ARM, (30, 22, 19))):
        P[name + '_up'] = mask(lambda d, p=pts, r=r: capsule(d, p[0], p[1], r[0], r[1]))
        P[name + '_lo'] = mask(lambda d, p=pts, r=r: capsule(d, p[1], p[2], r[1], r[2]))
        P[name + '_hand'] = mask(lambda d, p=pts: d.ellipse(((p[2][0] - 24) * SS, (p[2][1] - 8) * SS,
                                                             (p[2][0] + 22) * SS, (p[2][1] + 72) * SS), fill=255))
    P['elbow'] = mask(lambda d: d.ellipse((728 * SS, 1040 * SS, 812 * SS, 1122 * SS), fill=255))
    for name, pts in (('leg_l', L_LEG), ('leg_r', R_LEG)):
        P[name + '_up'] = mask(lambda d, p=pts: capsule(d, p[0], p[1], 40, 26))
        P[name + '_lo'] = mask(lambda d, p=pts: capsule(d, p[1], p[2], 26, 18))
        P[name + '_foot'] = mask(lambda d, p=pts: d.ellipse(((p[2][0] - 34) * SS, (p[2][1] - 10) * SS,
                                                             (p[2][0] + 40) * SS, (p[2][1] + 34) * SS), fill=255))
    P['shorts'] = mask(lambda d: d.polygon([(x * SS, y * SS) for x, y in SHORTS], fill=255))
    for side in ('arm_l', 'arm_r', 'leg_l', 'leg_r'):
        keys = [side + x for x in (('_up', '_lo', '_hand') if side.startswith('arm') else ('_up', '_lo', '_foot'))]
        m = P[keys[0]]
        for k in keys[1:]:
            m = ImageChops.lighter(m, P[k])
        P[side] = m.filter(ImageFilter.GaussianBlur(2)).point(lambda v: 255 if v > 110 else int(v * 2.3))
    return P


SKIN_TORSO = np.array([206, 158, 126])
SKIN_OLD = np.array([196, 176, 152])
SHORTS_C = np.array([62, 66, 74])
ELBOW_C = np.array([150, 80, 110])
ORDER = ['leg_l', 'leg_r', 'shorts', 'arm_l', 'arm_r', 'elbow', 'neck', 'torso', 'head']
COLOR = {k: (SKIN_OLD if k.startswith(('arm', 'leg')) else SKIN_TORSO) for k in ORDER}
COLOR['shorts'] = SHORTS_C
COLOR['elbow'] = ELBOW_C
LIGHT = np.array([-0.55, -0.55, 0.63])        # свет сверху-слева-спереди


def shade(m, light=LIGHT):
    """ламберт по псевдонормали из поля расстояний: даёт объём «как у живого тела»"""
    a = np.asarray(m, np.float32) / 255
    dist = ndimage.distance_transform_edt(a > 0.5)
    r = max(1.0, dist.max())
    h = np.sqrt(np.clip(dist / r, 0, 1))
    gy, gx = np.gradient(ndimage.gaussian_filter(h, 11))
    nz = np.full_like(h, 0.08)
    n = np.stack([-gx * r * 0.9, -gy * r * 0.9, nz + h * 0.9], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    lam = np.clip((n * light).sum(-1), 0, 1) * 0.75 + 0.25
    return a, lam, n


# ------------------------------------------------------------------ коридор (одноточечная перспектива)
VP = (540, 860)


def corridor(d, palette, lines=True):
    wall, wall2, floor, ceil, line, lamp = palette
    d.rectangle((0, 0, W, H), fill=ceil)
    d.polygon([(0, 0), (VP[0] - 170, VP[1] - 260), (VP[0] - 170, VP[1] + 200), (0, H)], fill=wall)
    d.polygon([(W, 0), (VP[0] + 170, VP[1] - 260), (VP[0] + 170, VP[1] + 200), (W, H)], fill=wall2)
    d.polygon([(0, H), (VP[0] - 170, VP[1] + 200), (VP[0] + 170, VP[1] + 200), (W, H)], fill=floor)
    d.rectangle((VP[0] - 170, VP[1] - 260, VP[0] + 170, VP[1] + 200), fill=(tuple(int(c * 0.5) for c in ceil) if isinstance(ceil, tuple) else ceil))
    if not lines:
        return
    for k in range(1, 9):                                   # швы панелей
        f = (k / 9) ** 1.7
        xl = 0 + (VP[0] - 170) * f
        d.line((xl, (VP[1] - 260) * f, xl, H - (H - VP[1] - 200) * f), fill=line, width=max(1, int(4 * (1 - f)) + 1))
        xr = W - (W - VP[0] - 170) * f
        d.line((xr, (VP[1] - 260) * f, xr, H - (H - VP[1] - 200) * f), fill=line, width=max(1, int(4 * (1 - f)) + 1))
        y = H - (H - VP[1] - 200) * f
        d.line((xl, y, xr, y), fill=line, width=max(1, int(3 * (1 - f)) + 1))
    for k in range(1, 6):                                   # лампы под потолком
        f = (k / 6) ** 1.5
        x0, x1 = (VP[0] - 170) * f + 120 * (1 - f), W - ((W - VP[0] - 170) * f + 120 * (1 - f))
        y = (VP[1] - 260) * f + 40 * (1 - f)
        d.rectangle(((x0 + x1) / 2 - 90 * (1 - f) - 20, y, (x0 + x1) / 2 + 90 * (1 - f) + 20, y + 14 * (1 - f) + 4),
                    fill=lamp)
    # рельс системы и полусфера
    d.line((VP[0], VP[1] - 260, VP[0], 0), fill=line, width=10)
    d.chord((VP[0] - 70, 150, VP[0] + 70, 290), 0, 180, fill=(30, 32, 38), outline=line, width=4)
    for k in range(5):
        d.ellipse((VP[0] - 50 + k * 22, 236, VP[0] - 38 + k * 22, 248), fill=(220, 60, 50))


def hud(d, col, font_name='JetBrainsMono-Bold.ttf', size=38, x=90, y=360):
    f = fnt(font_name, size)
    for k, (a, b) in enumerate((('ГИДРАЦИЯ', 'УСПЕШНО'), ('КОМПЛЕКТАЦИЯ', 'УСПЕШНО'), ('РЕАНИМАЦИЯ', 'УСПЕШНО'))):
        d.text((x, y + k * 60), f'> {a} ', font=f, fill=col)
        d.text((x + 640, y + k * 60), b, font=f, fill=col)


def face(d, style):
    """лицо: брови, полуприкрытые глаза, нос, гримаса боли, щетина на бритой голове"""
    ink = {'A': (40, 26, 22), 'B': (0, 0, 0), 'C': (70, 44, 36), 'E': (50, 40, 36)}.get(style, (40, 26, 22))
    w = 4 if style == 'B' else 3
    d.line((496, 652, 522, 646, 532, 652), fill=ink, width=w + 2, joint='curve')       # брови сведены от боли
    d.line((548, 652, 558, 646, 584, 652), fill=ink, width=w + 2, joint='curve')
    for cx in (512, 568):
        d.chord((cx - 18, 660, cx + 18, 690), 0, 180, fill=(246, 238, 230) if style != 'B' else (255, 255, 255))
        d.ellipse((cx - 6, 670, cx + 6, 682), fill=(60, 72, 70))
        d.line((cx - 20, 674, cx + 20, 674), fill=ink, width=w + 1)                    # тяжёлые веки
    d.line((540, 676, 534, 716, 546, 720), fill=ink, width=w)                            # нос
    d.line((516, 742, 528, 736, 552, 736, 564, 744), fill=ink, width=w + 1, joint='curve')  # рот: стиснутые зубы
    if style in ('A', 'C', 'E'):
        r = np.random.default_rng(3)
        for _ in range(900):                                                            # щетина на голове и лице
            x, y = r.uniform(466, 614), r.uniform(566, 770)
            if ((x - 540) / 76) ** 2 + ((y - 666) / 104) ** 2 < 1 and not (600 < y < 735 and 470 < x < 610):
                d.point((x, y), fill=(60, 44, 38, 120))


def details(d, style):
    ink = (0, 0, 0) if style == 'B' else (90, 50, 46)
    # шрамы-кольца на плечах и бёдрах
    for (x, y), r in (((352, 872), 32), ((728, 872), 32), ((462, 1340), 42), ((618, 1340), 42)):
        d.arc((x - r, y - r * 0.45, x + r, y + r * 0.45), 0, 180, fill=(170, 60, 60), width=5)
        for k in range(-r + 6, r, 12):
            d.line((x + k, y + r * 0.42 - 6, x + k, y + r * 0.42 + 6), fill=(170, 60, 60), width=2)
    # мышцы: грудь, пресс
    d.arc((410, 880, 545, 990), 20, 160, fill=ink, width=3)
    d.arc((535, 880, 670, 990), 20, 160, fill=ink, width=3)
    for k in range(3):
        y = 1030 + k * 50
        d.line((500, y, 532, y + 4), fill=ink, width=2)
        d.line((548, y + 4, 580, y), fill=ink, width=2)
    d.line((540, 1000, 540, 1180), fill=ink, width=2)
    d.text((600, 900), '11', font=fnt('Oswald-700.ttf', 64), fill=(24, 22, 24))   # номер на груди
    # колени и пигментные пятна на старых конечностях
    for x, y in ((452, 1580), (630, 1580)):
        d.arc((x - 26, y - 18, x + 26, y + 18), 200, 340, fill=ink, width=2)
    for i in range(26):
        lx = [L_ARM, R_ARM, L_LEG, R_LEG][i % 4]
        t = 0.15 + 0.7 * (i * 0.37 % 1)
        x = lx[0][0] + (lx[2][0] - lx[0][0]) * t + (i * 13 % 11 - 5)
        y = lx[0][1] + (lx[2][1] - lx[0][1]) * t
        d.ellipse((x - 3, y - 2, x + 3, y + 2), fill=(150, 120, 96))


def caption(d, text, col=(255, 255, 255), acc=None, y=1640, size=86, font_name='Oswald-700.ttf', stroke=0):
    f = fnt(font_name, size)
    d.text((W / 2, y), text, font=f, fill=col, anchor='mm', stroke_width=stroke, stroke_fill=(0, 0, 0))


# ------------------------------------------------------------------ стиль A: кино-нуар
def style_A(P):
    bg = Image.new('RGB', (W, H))
    corridor(ImageDraw.Draw(bg), ((26, 30, 36), (20, 24, 30), (16, 18, 22), (12, 14, 18), (44, 50, 58), (190, 220, 255)))
    a = np.asarray(bg, np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    glow_ = np.exp(-(((xx - 540) / 380) ** 2 + ((yy - 500) / 520) ** 2))[..., None] * np.array([40, 60, 90])
    a = a * 0.8 + glow_
    for k in ORDER:
        m, lam, n = shade(P[k])
        base = COLOR[k]
        rim = np.clip((n[..., 0] * 0.8 + n[..., 1] * -0.4), 0, 1) ** 3          # холодный контровой свет справа
        col = base[None, None] * (0.18 + 0.95 * lam[..., None]) + rim[..., None] * np.array([90, 140, 220])
        a = a * (1 - m[..., None]) + col * m[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    details(d, 'A')
    face(d, 'A')
    # туман, свет из-за спины, зерно, виньетка
    a = np.asarray(im, np.float32)
    fog = ndimage.gaussian_filter(rng.random((H // 8, W // 8)), 6)
    fog = np.kron(fog, np.ones((8, 8)))[:H, :W]
    a += (fog[..., None] - 0.5) * 50 * np.array([0.6, 0.8, 1.0])
    vig = np.clip(1 - 0.85 * (((xx - 540) / 700) ** 2 + ((yy - 900) / 1100) ** 2), 0.15, 1)
    a = a * vig[..., None] + rng.normal(0, 6, (H, W, 1))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    hud(d, (110, 255, 160, 220))
    caption(d, 'Я НЕ ПОМНЮ НИЧЕГО.', size=90)
    return im


# ------------------------------------------------------------------ стиль B: графический роман
def style_B(P):
    im = Image.new('RGB', (W, H))
    corridor(ImageDraw.Draw(im), ((70, 80, 92), (52, 60, 72), (40, 44, 52), (30, 34, 40), (0, 0, 0), (255, 240, 170)))
    a = np.asarray(im, np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    dots = ((np.sin(xx * 0.45) * np.sin(yy * 0.45)) > 0.3).astype(np.float32)
    for k in ORDER:
        m, lam, n = shade(P[k], np.array([-0.7, -0.3, 0.65]))
        base = COLOR[k] * np.array([1.08, 1.0, 0.92])
        lv = np.where(lam > 0.55, 1.0, np.where(lam > 0.25, 0.72, 0.42))
        col = base[None, None] * lv[..., None]
        col = col * (1 - 0.35 * dots[..., None] * (lv[..., None] < 0.5))
        a = a * (1 - m[..., None]) + col * m[..., None]
        edge = np.asarray(P[k].filter(ImageFilter.MaxFilter(7)), np.float32) / 255 - m
        a = a * (1 - np.clip(edge, 0, 1)[..., None])
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    details(d, 'B')
    face(d, 'B')
    d.rectangle((24, 24, W - 24, H - 24), outline=(0, 0, 0), width=18)       # рамка панели
    d.rectangle((60, 330, 1020, 560), fill=(240, 236, 214), outline=(0, 0, 0), width=6)
    hud(d, (20, 120, 60), size=34, x=90, y=360)
    d.rectangle((140, 1580, 940, 1720), fill=(255, 255, 255), outline=(0, 0, 0), width=6)
    caption(d, 'Я НЕ ПОМНЮ НИЧЕГО...', col=(0, 0, 0), y=1650, size=78)
    return im


# ------------------------------------------------------------------ стиль C: плоская иллюстрация
def style_C(P):
    im = Image.new('RGB', (W, H))
    corridor(ImageDraw.Draw(im), ((48, 64, 82), (40, 54, 72), (34, 44, 58), (26, 34, 46), (60, 78, 98), (255, 214, 140)),
             lines=True)
    a = np.asarray(im, np.float32)
    # длинная мягкая тень героя на полу
    sh = np.asarray(Image.merge('L', [ImageChops.lighter(P['leg_l'], P['leg_r'])]).transform(
        (W, H), Image.AFFINE, (1, 0.9, -820, 0, 1, 0)).filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
    a *= (1 - 0.35 * sh[..., None])
    for k in ORDER:
        m, lam, n = shade(P[k], np.array([-0.8, -0.2, 0.55]))
        base = COLOR[k]
        lv = np.where(lam > 0.4, 1.0, 0.78)
        col = base[None, None] * lv[..., None]
        a = a * (1 - m[..., None]) + col * m[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    details(d, 'C')
    face(d, 'C')
    hud(d, (130, 240, 170), size=36)
    caption(d, 'Я НЕ ПОМНЮ НИЧЕГО.', col=(255, 246, 230), size=88)
    return im


# ------------------------------------------------------------------ стиль D: пиксель-арт
def style_D(P):
    src = style_C(P)
    small = src.resize((W // 6, H // 6), Image.BILINEAR).quantize(32, method=Image.Quantize.MEDIANCUT).convert('RGB')
    im = small.resize((W, H), Image.NEAREST)
    d = ImageDraw.Draw(im)
    d.rectangle((50, 330, 1030, 560), fill=(10, 20, 16))
    hud(d, (90, 255, 130), font_name='JetBrainsMono-Bold.ttf', size=36)
    d.rectangle((120, 1590, 960, 1710), fill=(10, 10, 14), outline=(90, 255, 130), width=6)
    caption(d, 'Я НЕ ПОМНЮ НИЧЕГО.', col=(255, 255, 255), y=1650, size=60, font_name='JetBrainsMono-Bold.ttf')
    return im


# ------------------------------------------------------------------ стиль E: карандаш и акварель
def style_E(P):
    paper = np.full((H, W, 3), [236, 230, 216], np.float32)
    paper += (ndimage.gaussian_filter(rng.random((H, W)), 1.2)[..., None] - 0.5) * 26
    a = paper.copy()

    def wash(m, col, k=0.55):
        mm = np.asarray(m.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
        mm *= 0.7 + 0.3 * ndimage.gaussian_filter(rng.random((H, W)), 18) * 2
        return mm, np.array(col, np.float32), k

    def apply(a, mm, col, k):
        return a * (1 - mm[..., None] * k) + (a * col / 255) * mm[..., None] * k

    walls = mask(lambda d: corridor(d, (255, 255, 255, 255, 0, 0), lines=False))
    a = apply(a, *wash(walls, (90, 110, 130), 0.75))
    for k in ORDER:
        m, lam, n = shade(P[k])
        mm, col, kk = wash(P[k], COLOR[k] * 1.05, 0.85)
        a = apply(a, mm, col, kk)
        a *= (1 - 0.35 * (1 - lam[..., None]) * (np.asarray(P[k], np.float32)[..., None] / 255))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    lay = Image.new('L', (W, H), 0)
    ld = ImageDraw.Draw(lay)
    for k in ORDER:                                        # карандашный контур: несколько дрожащих проходов
        e = np.asarray(P[k].filter(ImageFilter.FIND_EDGES), np.float32)
        ys, xs = np.nonzero(e > 60)
        for _ in range(2):
            j = rng.normal(0, 1.4, (len(xs), 2))
            for x, y, (jx, jy) in zip(xs[::3], ys[::3], j[::3]):
                ld.point((x + jx, y + jy), fill=200)
    pencil = np.asarray(lay.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255
    a = np.asarray(im, np.float32) * (1 - 0.75 * pencil[..., None]) + np.array([50, 44, 40]) * 0.75 * pencil[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    details(d, 'E')
    face(d, 'E')
    hud(d, (40, 140, 80), size=36)
    caption(d, 'Я не помню ничего.', col=(40, 34, 30), size=92, font_name='Oswald-600.ttf')
    return im


if __name__ == '__main__':
    P = parts()
    out = paths.build(HERE) / 'review'
    out.mkdir(parents=True, exist_ok=True)
    ims = []
    for name, fn in (('A', style_A), ('B', style_B), ('C', style_C), ('D', style_D), ('E', style_E)):
        im = fn(P)
        im.save(out / f'style_{name}.png')
        ims.append(im)
        print('style', name)
    sheet = Image.new('RGB', (360 * 5 + 40, 680), (20, 20, 24))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((360, 640)), (i * 368 + 4, 20))
    sheet.save(out / 'styles_sheet.jpg', quality=90)
