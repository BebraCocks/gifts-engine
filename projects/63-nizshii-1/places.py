"""Места части 1 v2 — наполненные и проработанные (автор 2026-11-27), по книге (BOOK1-NOTES.md, главы 1–3).
Перспектива одной точкой: мир в метрах (x — вбок, y — вверх, z — вглубь), камера на высоте глаз.
Плиты рендерятся с запасом (SS) под движение камеры и кешируются в build/v2_cache."""
import math
import random
from pathlib import Path
import numpy as np
from PIL import Image
import kit
from kit import fill, stroke, ellipse, rad, lin, shade, smooth_path, poly

CACHE = Path(__file__).resolve().parent / 'build' / 'v2_cache'
STEEL = (70, 78, 84)
STEEL_D = (40, 46, 52)
GRIME = (52, 46, 36)
RUST = (120, 70, 40)


def cached(name, fn):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{name}.npy'
    if p.is_file():
        return np.load(p)
    a = fn().astype(np.float16)
    np.save(p, a)
    return a


class Persp:
    def __init__(self, w, h, f=820, vx=None, vy=None, eye=1.6):
        self.w, self.h, self.f, self.eye = w, h, f, eye
        self.vx = w / 2 if vx is None else vx
        self.vy = h * 0.43 if vy is None else vy

    def p(self, x, y, z):
        z = max(z, 0.05)
        return (self.vx + x * self.f / z, self.vy - (y - self.eye) * self.f / z)

    def s(self, z):           # пикселей на метр на глубине z
        return self.f / max(z, 0.05)


def quad(ctx, P, pts):
    poly(ctx, [P.p(*q) for q in pts])


def haze(arr, depth, color=(16, 28, 36), k=0.045, maxa=0.85):
    """туман по карте глубины (м)"""
    a = np.clip(1 - np.exp(-depth * k), 0, maxa)[..., None]
    c = np.asarray(color, np.float32) / 255
    arr[..., :3] = arr[..., :3] * (1 - a) + c * a * arr[..., 3:4]
    return arr


def rivets(ctx, pts, r, col=STEEL):
    for x, y in pts:
        g = rad(x, y, 0, r, [(0, shade(col, 1.5), 1), (0.6, col, 1), (1, shade(col, 0.4), 1)], x - r * 0.3, y - r * 0.4)
        ellipse(ctx, x, y, r, r)
        ctx.set_source(g)
        ctx.fill()


def streaks(ctx, x0, y0, x1, y1, n, seed, col=GRIME, a=0.25):
    """потёки грязи вниз по стене (в экранной рамке прямоугольника)"""
    r = random.Random(seed)
    for _ in range(n):
        x = x0 + r.random() * (x1 - x0)
        y = y0 + r.random() * (y1 - y0) * 0.4
        ln = (y1 - y) * (0.3 + r.random() * 0.7)
        w = (x1 - x0) * (0.01 + r.random() * 0.04)
        g = lin(x, y, x, y + ln, [(0, col, a * (0.5 + r.random())), (1, col, 0)])
        ctx.rectangle(x - w / 2, y, w, ln)
        ctx.set_source(g)
        ctx.fill()


def text(ctx, x, y, s, size, col, a=1.0, bold=True, anchor='c', font='DejaVu Sans'):
    ctx.save()
    ctx.select_font_face(font, 0, 1 if bold else 0)
    ctx.set_font_size(size)
    e = ctx.text_extents(s)
    dx = {'c': -e.width / 2, 'l': 0, 'r': -e.width}[anchor] - e.x_bearing
    ctx.move_to(x + dx, y + e.height / 2)
    ctx.set_source_rgba(*kit.rgb(col, a))
    ctx.show_text(s)
    ctx.restore()


# ── главный коридор-улица ──────────────────────────────────────────────────
STRIPES = [((70, 200, 110), 'ЗОНА 3', 1), ((220, 190, 70), 'ЗОНА 5', -1), ((90, 150, 230), 'КЛУКС-17', 1),
           ((210, 80, 70), 'МЕДБЛОК', -1)]


def corridor(w=1620, h=2880, seed=1, half=3.3, height=5.0, depth=70, eye=1.65, niches=True, screens_on=False,
             bench=True, wet=True, lamps=True):
    """премультиплированный RGBA float + карта глубины. Стены — клёпаные панели, полосы-указатели, ниши-раздатчики,
    экраны, лавки, кабели и трубы, рельс полусферы."""
    P = Persp(w, h, f=w * 0.52, vy=h * 0.45, eye=eye)
    cv = kit.Canvas(w, h)
    c = cv.ctx
    r = random.Random(seed)
    zs = [0.4]
    while zs[-1] < depth:
        zs.append(zs[-1] + 2.4)
    # фон
    c.rectangle(0, 0, w, h)
    fill(c, (10, 14, 18))
    # потолок
    for i in range(len(zs) - 1):
        z0, z1 = zs[i], zs[i + 1]
        quad(c, P, [(-half, height, z0), (half, height, z0), (half, height, z1), (-half, height, z1)])
        fill(c, shade((40, 46, 52), 0.85 + 0.15 * (i % 2)))
        for xk in (-half * 0.5, 0, half * 0.5):       # балки
            quad(c, P, [(xk - 0.08, height, z0), (xk + 0.08, height, z0), (xk + 0.08, height, z1), (xk - 0.08, height, z1)])
            fill(c, (26, 30, 34))
        quad(c, P, [(-half, height - 0.02, z0), (half, height - 0.02, z0), (half, height - 0.25, z0 + 0.05),
                    (-half, height - 0.25, z0 + 0.05)])
        fill(c, (30, 34, 38))
    # стены
    for sx in (-1, 1):
        for i in range(len(zs) - 1):
            z0, z1 = zs[i], zs[i + 1]
            x = sx * half
            base = shade(STEEL, 0.78 + 0.12 * r.random())
            quad(c, P, [(x, 0, z0), (x, height, z0), (x, height, z1), (x, 0, z1)])
            fill(c, base)
            # горизонтальные стыки панелей
            for y in (1.2, 2.6, 3.8):
                a, b = P.p(x, y, z0), P.p(x, y, z1)
                c.move_to(*a)
                c.line_to(*b)
                stroke(c, (18, 20, 24), max(1, P.s(z0) * 0.02), 0.8)
                a2, b2 = P.p(x, y - 0.02, z0), P.p(x, y - 0.02, z1)
                c.move_to(*a2)
                c.line_to(*b2)
                stroke(c, shade(base, 1.3), max(0.6, P.s(z0) * 0.008), 0.5)
            a, b = P.p(x, 0, z0), P.p(x, height, z0)
            c.move_to(*a)
            c.line_to(*b)
            stroke(c, (16, 18, 22), max(1, P.s(z0) * 0.03), 0.9)
            # заклёпки по краю панели
            if z0 < 30:
                pts = [P.p(x, y, z0 + 0.08) for y in np.linspace(0.15, height - 0.2, 12)]
                rivets(c, pts, max(1.2, P.s(z0) * 0.025))
            # потёки
            pa, pb = P.p(x, height, z0), P.p(x, 0, z1)
            streaks(c, min(pa[0], pb[0]), min(pa[1], pb[1]), max(pa[0], pb[0]), max(pa[1], pb[1]), 6, seed + i * 7 + sx)
            # ржавое пятно
            if r.random() < 0.35:
                yy = r.uniform(0.3, 3.5)
                cx_, cy_ = P.p(x, yy, z0 + 1.2)
                g = rad(cx_, cy_, 0, P.s(z0) * 0.6, [(0, RUST, 0.45), (1, RUST, 0)])
                ellipse(c, cx_, cy_, P.s(z0) * 0.3, P.s(z0) * 0.6)
                c.set_source(g)
                c.fill()
        # полосы-указатели
        for k, (col, label, d) in enumerate(STRIPES):
            y0 = 1.35 + k * 0.13
            if (sx < 0) == (k % 2 == 1) or True:
                quad(c, P, [(sx * (half - 0.01), y0, 1), (sx * (half - 0.01), y0 + 0.08, 1),
                            (sx * (half - 0.01), y0 + 0.08, depth), (sx * (half - 0.01), y0, depth)])
                fill(c, shade(col, 0.7), 0.85)
                for zz in np.arange(3 + k * 1.3, depth, 9):
                    a = P.p(sx * (half - 0.02), y0 + 0.04, zz)
                    s_ = P.s(zz)
                    if s_ < 6:
                        continue
                    # стрелка
                    ah = s_ * 0.07
                    dd = d * sx
                    c.move_to(a[0] + dd * s_ * 0.0, a[1] - ah)
                    c.line_to(a[0] - dd * s_ * 0.12, a[1])
                    c.line_to(a[0], a[1] + ah)
                    fill(c, shade(col, 1.3), 0.95)
                    if s_ > 30 and k == 0:
                        text(c, a[0] + dd * s_ * 0.25, a[1] - s_ * 0.1, label, s_ * 0.075, shade(col, 1.2), 0.85)
        # лавка — выступ стены с пластиком
        if bench:
            quad(c, P, [(sx * half, 0.48, 1), (sx * (half - 0.42), 0.48, 1), (sx * (half - 0.42), 0.48, depth),
                        (sx * half, 0.48, depth)])
            fill(c, (64, 58, 52))
            quad(c, P, [(sx * (half - 0.42), 0.48, 1), (sx * (half - 0.42), 0.0, 1), (sx * (half - 0.42), 0.0, depth),
                        (sx * (half - 0.42), 0.48, depth)])
            fill(c, (30, 32, 36))
        # ниши-раздатчики с зелёным контуром и экраны
        for zz in np.arange(4.0 + (sx > 0) * 3.5, depth, 7.0):
            if niches:
                x = sx * (half - 0.005)
                quad(c, P, [(x, 0.0, zz), (x, 2.05, zz), (x, 2.05, zz + 0.95), (x, 0.0, zz + 0.95)])
                fill(c, (34, 38, 40))
                c.set_line_width(max(1.2, P.s(zz) * 0.035))
                quad(c, P, [(x, 0.0, zz), (x, 2.05, zz), (x, 2.05, zz + 0.95), (x, 0.0, zz + 0.95)])
                stroke(c, (60, 230, 120), max(1.2, P.s(zz) * 0.035), 0.85)
                quad(c, P, [(x, 0.55, zz + 0.3), (x, 0.8, zz + 0.3), (x, 0.8, zz + 0.62), (x, 0.55, zz + 0.62)])
                fill(c, (8, 10, 12))
            if r.random() < 0.6:
                x = sx * (half - 0.005)
                z1 = zz + 2.5
                quad(c, P, [(x, 2.25, z1), (x, 3.35, z1), (x, 3.35, z1 + 1.8), (x, 2.25, z1 + 1.8)])
                fill(c, (20, 20, 18))
                quad(c, P, [(x, 2.32, z1 + 0.08), (x, 3.28, z1 + 0.08), (x, 3.28, z1 + 1.72), (x, 2.32, z1 + 1.72)])
                fill(c, (120, 108, 70) if screens_on else (44, 42, 34))
        # трубы и кабели вдоль стыка стены и потолка
        for k, (yy, dx, wd, col) in enumerate([(height - 0.25, 0.25, 0.16, (60, 64, 66)), (height - 0.5, 0.18, 0.1, (54, 46, 40)),
                                               (height - 0.62, 0.1, 0.05, (20, 20, 22)), (height - 0.7, 0.12, 0.04, (110, 40, 34))]):
            x = sx * (half - dx)
            pts = [P.p(x, yy, 1.0), P.p(x, yy, depth)]
            wa = wd * P.s(1.0)
            c.move_to(*pts[0])
            c.line_to(*pts[1])
            g = lin(pts[0][0], pts[0][1] - wa, pts[0][0], pts[0][1] + wa, [(0, shade(col, 1.4), 1), (0.5, col, 1),
                                                                          (1, shade(col, 0.4), 1)])
            c.set_source(g)
            c.set_line_width(wa)
            c.stroke()
            for zz in np.arange(2, depth, 5):                # хомуты
                a = P.p(x, yy, zz)
                ellipse(c, a[0], a[1], P.s(zz) * wd * 0.35, P.s(zz) * wd * 0.6)
                fill(c, (22, 24, 26), 0.9)
    # пол: плиты, швы, решётки стока, лужи
    for i in range(len(zs) - 1):
        z0, z1 = zs[i], zs[i + 1]
        for xk in range(-3, 3):
            x0, x1 = xk * half / 3, (xk + 1) * half / 3
            quad(c, P, [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)])
            fill(c, shade((52, 56, 58), 0.75 + 0.2 * r.random()))
            quad(c, P, [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)])
            stroke(c, (18, 20, 22), max(0.8, P.s(z0) * 0.015), 0.8)
        if i % 3 == 1:
            quad(c, P, [(-0.5, 0, z0 + 0.5), (0.5, 0, z0 + 0.5), (0.5, 0, z0 + 1.1), (-0.5, 0, z0 + 1.1)])
            fill(c, (12, 14, 16))
            for k in range(9):
                xx = -0.45 + k * 0.11
                a, b = P.p(xx, 0, z0 + 0.52), P.p(xx, 0, z0 + 1.08)
                c.move_to(*a)
                c.line_to(*b)
                stroke(c, (60, 64, 66), max(0.8, P.s(z0) * 0.02), 0.8)
    if wet:
        for k in range(46):
            zz = 3.0 + r.random() ** 1.5 * depth * 0.7
            xx = r.uniform(-half * 0.92, half * 0.92)
            a = P.p(xx, 0, zz)
            rx = P.s(zz) * r.uniform(0.35, 1.3)
            ry = rx * eye / zz * 0.9
            g = rad(a[0], a[1], 0, rx, [(0, (14, 20, 24), 0.55), (0.75, (16, 22, 26), 0.45), (1, (16, 22, 26), 0)])
            ellipse(c, a[0], a[1], rx, max(2, ry))
            c.set_source(g)
            c.fill()
            g = rad(a[0], a[1] - ry * 0.2, 0, rx, [(0, (150, 190, 195), 0.0), (0.7, (150, 190, 195), 0.1),
                                                   (0.9, (150, 190, 195), 0.16), (1, (150, 190, 195), 0)])
            ellipse(c, a[0], a[1], rx, max(2, ry))
            c.set_source(g)
            c.fill()
    # рельс полусферы по центру потолка
    for dx in (-0.12, 0.12):
        a, b = P.p(dx, height - 0.12, 1.0), P.p(dx, height - 0.12, depth)
        c.move_to(*a)
        c.line_to(*b)
        stroke(c, (90, 96, 100), P.s(1.0) * 0.05, 1)
    for zz in np.arange(1.5, depth, 3):
        a, b = P.p(0, height, zz), P.p(0, height - 0.12, zz)
        c.move_to(*a)
        c.line_to(*b)
        stroke(c, (40, 44, 48), max(1, P.s(zz) * 0.05), 1)
    # лампы
    lamp_pts = []
    if lamps:
        for zz in np.arange(3, depth, 6):
            for xx in (-half * 0.62, half * 0.62):
                quad(c, P, [(xx - 0.35, height - 0.03, zz), (xx + 0.35, height - 0.03, zz),
                            (xx + 0.35, height - 0.03, zz + 1.2), (xx - 0.35, height - 0.03, zz + 1.2)])
                fill(c, (200, 230, 230))
                lamp_pts.append((xx, zz + 0.6))
    arr = cv.premul()
    # глубина для тумана (приближённо по строке экрана и колонке)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy = np.abs(yy - P.vy) + 1
    dx = np.abs(xx - P.vx) + 1
    z_floor = (eye * P.f) / dy
    z_ceil = ((height - eye) * P.f) / dy
    z_wall = half * P.f / dx
    zf = np.where(yy > P.vy, z_floor, z_ceil)
    depthm = np.minimum(zf, z_wall)
    # свет: пятна от ламп на полу и стенах, тил в глубине
    light = np.zeros((h, w), np.float32)
    for xx_, zz in lamp_pts:
        a = P.p(xx_ * 0.6, 0, zz)
        s_ = P.s(zz)
        light += np.exp(-(((xx - a[0]) / (s_ * 2.4)) ** 2 + ((yy - a[1]) / (s_ * 0.9)) ** 2)) * 0.6
        b = P.p(xx_ * 1.4, 2.8, zz)
        light += np.exp(-(((xx - b[0]) / (s_ * 1.0)) ** 2 + ((yy - b[1]) / (s_ * 2.2)) ** 2)) * 0.35
    arr[..., :3] *= (0.28 + np.clip(light, 0, 1.8)[..., None] * np.array([1.05, 1.04, 1.0], np.float32))
    np.clip(arr, 0, 1, out=arr)
    kit.texture(arr, 0.16, 8, seed=seed + 20, fine=0.06)
    haze(arr, depthm, k=0.045)
    # свечение ламп и световые конусы
    glow = kit.Canvas(w, h)
    gc = glow.ctx
    for xx_, zz in lamp_pts:
        a = P.p(xx_, height - 0.05, zz)
        s_ = P.s(zz)
        g = rad(a[0], a[1], 0, s_ * 1.4, [(0, (220, 245, 240), 0.55), (0.3, (120, 170, 175), 0.18), (1, (0, 0, 0), 0)])
        ellipse(gc, a[0], a[1], s_ * 1.4, s_ * 0.8)
        gc.set_source(g)
        gc.fill()
        f0, f1 = P.p(xx_ * 0.7 - 0.9, 0, zz + 0.2), P.p(xx_ * 0.7 + 0.9, 0, zz + 1.0)
        poly(gc, [(a[0] - s_ * 0.3, a[1]), (a[0] + s_ * 0.3, a[1]), (f1[0], f1[1]), (f0[0], f0[1])])
        gc.set_source(lin(a[0], a[1], a[0], f0[1], [(0, (170, 210, 210), 0.12), (1, (170, 210, 210), 0.0)]))
        gc.fill()
    ga = glow.premul()
    arr[..., :3] = np.clip(arr[..., :3] + ga[..., :3], 0, 1)
    return arr, P


def floor_top(w, h, seed=2, plate=360, wet=0.6):
    """мокрый липкий стальной пол сверху (сцена пробуждения): плиты, швы, заклёпки, лужи, решётка, грязь"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    r = random.Random(seed)
    c.rectangle(0, 0, w, h)
    fill(c, (44, 50, 54))
    for y in range(0, h, plate):
        for x in range(-(y // plate % 2) * plate // 2, w, plate):
            col = shade((58, 64, 68), 0.75 + r.random() * 0.25)
            c.rectangle(x + 3, y + 3, plate - 6, plate - 6)
            fill(c, col)
            # рифление
            for k in range(0, plate, 28):
                for m in range(0, plate, 28):
                    if (k // 28 + m // 28) % 2:
                        ellipse(c, x + k + 14, y + m + 14, 10, 3.5, 0.78)
                    else:
                        ellipse(c, x + k + 14, y + m + 14, 10, 3.5, -0.78)
                    fill(c, shade(col, 1.15), 0.5)
            c.rectangle(x + 3, y + 3, plate - 6, plate - 6)
            stroke(c, (16, 18, 20), 5, 0.9)
            rivets(c, [(x + 16, y + 16), (x + plate - 16, y + 16), (x + 16, y + plate - 16), (x + plate - 16, y + plate - 16)],
                   6, (70, 74, 78))
    # решётка стока
    gx, gy = int(w * 0.62), int(h * 0.7)
    c.rectangle(gx, gy, 300, 190)
    fill(c, (8, 9, 10))
    for k in range(13):
        c.rectangle(gx + 8 + k * 22, gy + 6, 9, 178)
        fill(c, (56, 60, 62))
    arr = cv.premul()
    # лужи и липкость: мягкие тёмные мокрые пятна, редкие блики
    n = kit.noise(h, w, 160, seed)
    wetm = np.clip((n - (1 - wet)) * 2.5, 0, 1)
    arr[..., :3] *= (1 - wetm[..., None] * 0.35)
    hl = np.clip((n - 0.82) * 8, 0, 1)
    arr[..., :3] += (hl ** 2)[..., None] * np.array([0.08, 0.1, 0.11], np.float32)
    g = kit.noise(h, w, 80, seed + 5)
    arr[..., :3] *= (0.88 + 0.18 * g[..., None]) * np.array([1.0, 0.98, 0.94], np.float32)
    kit.texture(arr, 0.18, 6, seed=seed + 3, fine=0.08)
    np.clip(arr, 0, 1, out=arr)
    return arr


def sphere(ctx, x, y, r, t=0.0, lens_on=1.0):
    """полусфера наблюдения на рельсе: крепление, корпус, ~20 объективов-визоров вниз, огоньки"""
    # крепление к рельсу
    ctx.rectangle(x - r * 0.18, y - r * 0.9, r * 0.36, r * 0.55)
    ctx.set_source(lin(x - r * 0.18, 0, x + r * 0.18, 0, [(0, (40, 44, 48), 1), (0.4, (110, 116, 120), 1), (1, (30, 32, 36), 1)]))
    ctx.fill()
    ctx.rectangle(x - r * 0.45, y - r * 1.0, r * 0.9, r * 0.14)
    fill(ctx, (50, 54, 58))
    # корпус — полусфера (купол вниз)
    ctx.save()
    ctx.translate(x, y - r * 0.32)
    ctx.move_to(-r, 0)
    ctx.arc_negative(0, 0, r, math.pi, 0) if False else None
    ctx.new_path()
    ctx.arc(0, 0, r, 0, math.pi)
    ctx.close_path()
    ctx.set_source(rad(-r * 0.35, r * 0.25, r * 0.05, r * 1.1, [(0, (190, 198, 204), 1), (0.35, (110, 118, 124), 1),
                                                               (0.8, (46, 50, 56), 1), (1, (22, 24, 28), 1)]))
    ctx.fill()
    ctx.rectangle(-r * 1.04, -r * 0.08, r * 2.08, r * 0.12)
    fill(ctx, (34, 36, 40))
    # швы корпуса
    for k in range(1, 6):
        a = math.pi * k / 6
        ctx.move_to(math.cos(a) * r * 0.2, math.sin(a) * r * 0.2)
        ctx.line_to(math.cos(a) * r * 0.99, math.sin(a) * r * 0.99)
        stroke(ctx, (24, 26, 30), r * 0.012, 0.6)
    # объективы: три пояса
    rr = random.Random(5)
    for ring, (rad_k, n, size) in enumerate([(0.86, 9, 0.11), (0.6, 7, 0.1), (0.3, 4, 0.09)]):
        for k in range(n):
            a = math.pi * (k + 0.5) / n
            px, py = math.cos(a) * r * rad_k, math.sin(a) * r * rad_k * 0.92 + r * 0.04
            s_ = r * size
            ctx.set_source(rad(px, py, 0, s_ * 1.3, [(0, (60, 64, 70), 1), (1, (18, 20, 24), 1)]))
            ellipse(ctx, px, py, s_ * 1.25, s_ * 1.25)
            ctx.fill()
            ctx.set_source(rad(px - s_ * 0.3, py - s_ * 0.3, 0, s_, [(0, (70, 120, 140), 1), (0.5, (14, 30, 40), 1),
                                                                     (1, (4, 6, 8), 1)]))
            ellipse(ctx, px, py, s_, s_)
            ctx.fill()
            ellipse(ctx, px - s_ * 0.35, py - s_ * 0.35, s_ * 0.22, s_ * 0.14, -0.6)
            fill(ctx, (220, 240, 255), 0.7)
            if rr.random() < 0.35:
                blink = 0.5 + 0.5 * math.sin(t * 5 + k * 1.7 + ring)
                ellipse(ctx, px + s_ * 1.0, py - s_ * 0.6, s_ * 0.18, s_ * 0.18)
                fill(ctx, (255, 40, 40), 0.4 + 0.6 * blink * lens_on)
    ctx.restore()


def lasers(ctx, src, targets, a=0.7):
    for (x0, y0), (x1, y1) in zip(src, targets):
        for wdt, aa in ((7, 0.12), (2.2, 0.55), (0.9, 1.0)):
            ctx.move_to(x0, y0)
            ctx.line_to(x1, y1)
            stroke(ctx, (255, 50, 40), wdt, a * aa)
        ellipse(ctx, x1, y1, 5, 5)
        fill(ctx, (255, 120, 100), a)
