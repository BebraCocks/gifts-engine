"""Остальные места части 1 v2 — по книге (главы 1–3). Каждая функция возвращает premultiplied RGBA float
(или PIL) для stage.plate(). Размеры — холст плана stage.CW×CH."""
import math
import random
import numpy as np
from scipy import ndimage
import kit
from kit import fill, stroke, ellipse, rad, lin, shade, smooth_path, poly
from places import Persp, quad, rivets, streaks, text, haze, STEEL, GRIME, RUST
import places

CW, CH = 1350, 2400


def _finish(cv, tex=0.14, seed=1, light=None):
    arr = cv.premul()
    if light is not None:
        arr[..., :3] *= light[..., None]
    np.clip(arr, 0, 1, out=arr)
    kit.texture(arr, tex, 7, seed=seed, fine=0.06)
    return arr


def light_map(w, h, spots, base=0.25):
    """spots: (x, y, rx, ry, k) — эллиптические пятна света"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    L = np.full((h, w), base, np.float32)
    for x, y, rx, ry, k in spots:
        L += np.exp(-(((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2)) * k
    return np.clip(L, 0, 1.6)


def wall_panels(c, x0, y0, x1, y1, pw=300, ph=420, seed=1, col=STEEL, rust=0.3):
    r = random.Random(seed)
    for yy in range(int(y0), int(y1), ph):
        for xx in range(int(x0), int(x1), pw):
            cc = shade(col, 0.72 + r.random() * 0.22)
            c.rectangle(xx + 2, yy + 2, pw - 4, ph - 4)
            fill(c, cc)
            c.rectangle(xx + 2, yy + 2, pw - 4, ph - 4)
            stroke(c, (14, 16, 18), 5, 0.9)
            c.move_to(xx + 6, yy + 6)
            c.line_to(xx + pw - 6, yy + 6)
            stroke(c, shade(cc, 1.35), 2, 0.5)
            rivets(c, [(xx + 16, yy + 16), (xx + pw - 16, yy + 16), (xx + 16, yy + ph - 16), (xx + pw - 16, yy + ph - 16),
                       (xx + pw / 2, yy + 16), (xx + pw / 2, yy + ph - 16)], 5.5, shade(cc, 1.1))
            streaks(c, xx + 8, yy + 20, xx + pw - 8, yy + ph - 8, 4, seed * 100 + xx + yy)
            if r.random() < rust:
                g = rad(xx + r.random() * pw, yy + r.random() * ph, 0, 80, [(0, RUST, 0.4), (1, RUST, 0)])
                c.rectangle(xx, yy, pw, ph)
                c.set_source(g)
                c.fill()


def pipe(c, x0, y0, x1, y1, w, col=(66, 70, 72)):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    g = lin(x0 + nx * w / 2, y0 + ny * w / 2, x0 - nx * w / 2, y0 - ny * w / 2,
            [(0, shade(col, 0.4), 1), (0.3, shade(col, 1.45), 1), (0.55, col, 1), (1, shade(col, 0.35), 1)])
    c.move_to(x0, y0)
    c.line_to(x1, y1)
    c.set_source(g)
    c.set_line_width(w)
    c.stroke()


def drops(c, x0, y0, x1, y1, n, seed):
    r = random.Random(seed)
    for _ in range(n):
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        s = r.uniform(2, 6)
        ellipse(c, x, y, s * 0.7, s)
        fill(c, (20, 28, 32), 0.5)
        ellipse(c, x - s * 0.2, y - s * 0.3, s * 0.25, s * 0.3)
        fill(c, (200, 220, 225), 0.6)


# ── стена крупно (закуток, лавка, медблок) ─────────────────────────────────
def wall_close(seed=3, lamp=(0.72, 0.12), redcross=False, bench=False, w=CW, h=CH):
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (30, 34, 38))
    wall_panels(c, -40, -60, w + 40, h * 0.78, 320, 440, seed)
    # пол
    c.rectangle(0, h * 0.78, w, h * 0.22)
    c.set_source(lin(0, h * 0.78, 0, h, [(0, (34, 38, 40), 1), (1, (20, 22, 24), 1)]))
    c.fill()
    for k in range(8):
        y = h * 0.78 + (k ** 1.6) * 12
        c.move_to(0, y)
        c.line_to(w, y)
        stroke(c, (14, 16, 18), 2 + k * 0.6, 0.6)
    for k in range(-6, 7):
        c.move_to(w / 2 + k * 60, h * 0.78)
        c.line_to(w / 2 + k * 420, h)
        stroke(c, (14, 16, 18), 3, 0.6)
    c.rectangle(0, h * 0.775, w, 14)
    fill(c, (12, 14, 16))
    # трубы
    pipe(c, -20, h * 0.06, w + 20, h * 0.06, 46)
    pipe(c, -20, h * 0.11, w + 20, h * 0.11, 26, (84, 54, 40))
    pipe(c, w * 0.08, -20, w * 0.08, h * 0.78, 34)
    for k in range(5):
        x = w * (0.1 + k * 0.22)
        c.rectangle(x - 10, h * 0.06 - 30, 20, 60)
        fill(c, (24, 26, 28))
    drops(c, 0, 0, w, h * 0.75, 70, seed)
    if bench:
        c.rectangle(0, h * 0.66, w, h * 0.12)
        fill(c, (28, 30, 34))
        c.rectangle(0, h * 0.655, w, 34)
        c.set_source(lin(0, h * 0.655, 0, h * 0.655 + 34, [(0, (110, 100, 88), 1), (1, (60, 54, 48), 1)]))
        c.fill()
    if redcross:
        x0, y0 = w * 0.3, h * 0.28
        c.rectangle(x0, y0, w * 0.4, h * 0.5)
        fill(c, (46, 50, 54))
        c.rectangle(x0, y0, w * 0.4, h * 0.5)
        stroke(c, (14, 16, 18), 8, 1)
        cx, cy = x0 + w * 0.2, y0 + h * 0.12
        for rw, rh in ((60, 200), (200, 60)):
            c.rectangle(cx - rw / 2, cy - rh / 2, rw, rh)
            fill(c, (200, 40, 40))
        c.rectangle(x0 + w * 0.17, y0 + h * 0.3, 70, 70)
        fill(c, (6, 8, 10))
    # лампа в решётке
    lx, ly = w * lamp[0], h * lamp[1]
    ellipse(c, lx, ly, 70, 44)
    c.set_source(rad(lx, ly, 0, 70, [(0, (255, 246, 210), 1), (0.6, (230, 200, 140), 1), (1, (120, 100, 70), 1)]))
    c.fill()
    for k in range(-3, 4):
        c.move_to(lx + k * 20, ly - 46)
        c.line_to(lx + k * 20, ly + 46)
        stroke(c, (30, 30, 30), 4, 0.9)
    L = light_map(w, h, [(lx, ly + h * 0.25, w * 0.6, h * 0.45, 1.0), (lx, ly, 160, 120, 0.8)], 0.22)
    return _finish(cv, 0.15, seed, L)


# ── ниша-раздатчик изнутри ─────────────────────────────────────────────────
def niche_inside(w=CW, h=CH, door_open=False):
    """глубокая освещённая ниша: изогнутое дырчатое кресло на одной ножке, широкие подлокотники"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    c.set_source(rad(w / 2, h * 0.3, 50, h * 0.9, [(0, (150, 176, 168), 1), (0.5, (70, 90, 86), 1), (1, (22, 30, 30), 1)]))
    c.fill()
    # стенки ниши в перспективе
    for sx in (-1, 1):
        poly(c, [(w / 2 + sx * w * 0.5, 0), (w / 2 + sx * w * 0.36, h * 0.12), (w / 2 + sx * w * 0.36, h * 0.86),
                 (w / 2 + sx * w * 0.5, h)])
        c.set_source(lin(w / 2 + sx * w * 0.5, 0, w / 2 + sx * w * 0.36, 0, [(0, (30, 40, 40), 1), (1, (80, 100, 96), 1)]))
        c.fill()
    c.rectangle(w * 0.14, h * 0.12, w * 0.72, h * 0.74)
    fill(c, (96, 116, 110), 0.5)
    for k in range(9):                    # вентиляционные прорези
        c.rectangle(w * 0.34, h * 0.15 + k * 26, w * 0.32, 10)
        fill(c, (30, 40, 40), 0.8)
    # плафон сверху
    ellipse(c, w / 2, h * 0.035, w * 0.3, 40)
    fill(c, (235, 255, 245))
    # кресло: спинка с отверстиями
    bx0, bx1, by0, by1 = w * 0.26, w * 0.74, h * 0.2, h * 0.6
    c.move_to(bx0, by1)
    c.curve_to(bx0 - 40, by0 + 300, bx0 + 60, by0, w / 2, by0 - 20)
    c.curve_to(bx1 - 60, by0, bx1 + 40, by0 + 300, bx1, by1)
    c.close_path()
    c.set_source(lin(bx0, 0, bx1, 0, [(0, (70, 78, 80), 1), (0.35, (170, 180, 180), 1), (0.7, (110, 120, 122), 1),
                                      (1, (50, 56, 58), 1)]))
    c.fill()
    for row in range(14):
        for col in range(9):
            x = bx0 + 50 + col * (bx1 - bx0 - 100) / 8
            y = by0 + 40 + row * (by1 - by0 - 80) / 13
            ellipse(c, x, y, 9, 9)
            fill(c, (20, 26, 28), 0.9)
    # сиденье
    poly(c, [(bx0 - 30, by1), (bx1 + 30, by1), (bx1 + 70, by1 + 120), (bx0 - 70, by1 + 120)])
    c.set_source(lin(0, by1, 0, by1 + 120, [(0, (160, 170, 170), 1), (1, (70, 78, 80), 1)]))
    c.fill()
    # подлокотники (очень широкие)
    for sx in (-1, 1):
        ax = w / 2 + sx * w * 0.33
        poly(c, [(ax - 110, by1 - 150), (ax + 110, by1 - 150), (ax + 130, by1 - 90), (ax - 130, by1 - 90)])
        c.set_source(lin(0, by1 - 150, 0, by1 - 90, [(0, (190, 198, 198), 1), (1, (90, 98, 100), 1)]))
        c.fill()
        c.rectangle(ax - 130, by1 - 90, 260, 260)
        c.set_source(lin(ax - 130, 0, ax + 130, 0, [(0, (60, 66, 68), 1), (0.5, (110, 118, 120), 1), (1, (50, 54, 56), 1)]))
        c.fill()
        ellipse(c, ax, by1 - 120, 44, 14)                   # гнездо для стакана / выдача кубика
        fill(c, (14, 18, 20))
    # одна круглая ножка
    c.rectangle(w / 2 - 50, by1 + 120, 100, h * 0.9 - by1 - 120)
    c.set_source(lin(w / 2 - 50, 0, w / 2 + 50, 0, [(0, (40, 44, 46), 1), (0.4, (150, 156, 158), 1), (1, (30, 32, 34), 1)]))
    c.fill()
    ellipse(c, w / 2, h * 0.9, 220, 40)
    fill(c, (40, 44, 46))
    c.rectangle(0, h * 0.86, w, h * 0.14)
    fill(c, (30, 36, 36))
    L = light_map(w, h, [(w / 2, h * 0.2, w * 0.6, h * 0.5, 1.0)], 0.4)
    return _finish(cv, 0.1, 9, L)


# ── экран игрового вызова на стене ─────────────────────────────────────────
def screen_wall(w=CW, h=CH):
    arr, P = places.corridor(w, h, seed=8, half=3.3)
    cv = kit.from_premul(arr)
    c = cv.ctx
    # большой экран в раме на левой стене крупным планом
    x0, y0, x1, y1 = w * 0.12, h * 0.2, w * 0.88, h * 0.52
    c.rectangle(x0 - 30, y0 - 30, x1 - x0 + 60, y1 - y0 + 60)
    fill(c, (18, 18, 20))
    c.rectangle(x0, y0, x1 - x0, y1 - y0)
    fill(c, (40, 38, 30))
    rivets(c, [(x0 - 15, y0 - 15), (x1 + 15, y0 - 15), (x0 - 15, y1 + 15), (x1 + 15, y1 + 15)], 8)
    # чёрный квадратик внизу экрана
    c.rectangle(w / 2 - 50, y1 + 60, 100, 100)
    fill(c, (6, 6, 8))
    c.rectangle(w / 2 - 50, y1 + 60, 100, 100)
    stroke(c, (80, 80, 70), 3, 0.8)
    return cv.premul(), (x0, y0, x1, y1)


# ── кольцевой блок слизи (зона 3, блок 6) ──────────────────────────────────
def ring(w=CW, h=CH, seed=6):
    """овальный закольцованный коридор-«шестерёнка»: внешняя стена с прямоугольными зубцами-комнатами,
    стены в серых брызгах, лужи слизи, по потолку на рельсах две маленькие полусферы"""
    P = Persp(w, h, f=w * 0.55, vy=h * 0.44, eye=1.6)
    cv = kit.Canvas(w, h)
    c = cv.ctx
    r = random.Random(seed)
    c.rectangle(0, 0, w, h)
    fill(c, (12, 16, 18))
    half, height = 2.6, 3.6
    bend = 0.012                                      # коридор плавно уходит вправо

    def bx(z):
        return bend * z * z

    zs = np.arange(0.5, 46, 1.2)
    for i in range(len(zs) - 1):
        z0, z1 = zs[i], zs[i + 1]
        # потолок
        quad(c, P, [(-half + bx(z0), height, z0), (half + bx(z0), height, z0), (half + bx(z1), height, z1),
                    (-half + bx(z1), height, z1)])
        fill(c, shade((44, 48, 50), 0.8 + 0.1 * (i % 2)))
        # пол
        quad(c, P, [(-half + bx(z0), 0, z0), (half + bx(z0), 0, z0), (half + bx(z1), 0, z1), (-half + bx(z1), 0, z1)])
        fill(c, shade((56, 58, 56), 0.7 + 0.15 * r.random()))
        # внутренняя стена (справа)
        quad(c, P, [(half + bx(z0), 0, z0), (half + bx(z0), height, z0), (half + bx(z1), height, z1), (half + bx(z1), 0, z1)])
        fill(c, shade((70, 74, 74), 0.75 + 0.15 * r.random()))
        # внешняя стена (слева) — с «зубцами» каждые 4 сегмента
        tooth = (i % 5 == 2)
        if tooth:
            quad(c, P, [(-half + bx(z0), 0, z0), (-half + bx(z0), height * 0.85, z0), (-half + bx(z1), height * 0.85, z1),
                        (-half + bx(z1), 0, z1)])
            fill(c, (14, 16, 16))
            # в глубине зубца — сползающая слизь, свет
            pa = P.p(-half - 2.5 + bx(z0), height * 0.5, z0 + 0.6)
            g = rad(pa[0], pa[1], 0, P.s(z0) * 1.6, [(0, (120, 124, 116), 0.8), (1, (30, 32, 30), 0)])
            ellipse(c, pa[0], pa[1], P.s(z0) * 0.9, P.s(z0) * 1.4)
            c.set_source(g)
            c.fill()
        else:
            quad(c, P, [(-half + bx(z0), 0, z0), (-half + bx(z0), height, z0), (-half + bx(z1), height, z1),
                        (-half + bx(z1), 0, z1)])
            fill(c, shade((66, 70, 70), 0.7 + 0.15 * r.random()))
        # серые брызги на стенах
        for _ in range(5):
            side = r.choice((-1, 1))
            if side < 0 and tooth:
                continue
            yy = r.uniform(0.1, height * 0.8)
            a = P.p(side * half + bx(z0 + 0.6), yy, z0 + 0.6)
            s_ = P.s(z0) * r.uniform(0.05, 0.25)
            ellipse(c, a[0], a[1], s_ * 0.6, s_)
            fill(c, (150, 150, 140), 0.6)
            c.move_to(a[0], a[1])
            c.line_to(a[0], a[1] + s_ * r.uniform(1, 5))
            stroke(c, (150, 150, 140), max(1, s_ * 0.3), 0.5)
    # лужи слизи на полу
    for _ in range(40):
        zz = r.uniform(1.0, 30)
        xx = r.uniform(-half * 0.9, half * 0.9) + bx(zz)
        a = P.p(xx, 0, zz)
        rx = P.s(zz) * r.uniform(0.2, 0.9)
        ellipse(c, a[0], a[1], rx, rx * 1.6 / zz)
        c.set_source(rad(a[0], a[1], 0, rx, [(0, (140, 142, 134), 0.85), (0.8, (110, 112, 104), 0.7), (1, (90, 92, 86), 0)]))
        c.fill()
        ellipse(c, a[0] - rx * 0.3, a[1] - rx * 0.3 / zz, rx * 0.3, rx * 0.4 / zz)
        fill(c, (230, 235, 225), 0.35)
    # рельсы с полусферами
    for dx in (-0.6, 0.9):
        pts = [P.p(dx + bx(z), height - 0.1, z) for z in np.arange(0.6, 40, 0.8)]
        smooth_path(c, pts, closed=False)
        stroke(c, (100, 104, 106), 6, 0.9)
    arr = cv.premul()
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dy = np.abs(yy - P.vy) + 1
    depthm = np.where(yy > P.vy, 1.6 * P.f / dy, 2.0 * P.f / dy)
    L = light_map(w, h, [(w * 0.5, h * 0.62, w * 0.7, h * 0.3, 0.8), (w * 0.62, h * 0.4, w * 0.25, h * 0.2, 0.4)], 0.35)
    arr[..., :3] *= L[..., None]
    kit.texture(arr, 0.15, 8, seed=seed, fine=0.06)
    haze(arr, depthm, color=(30, 36, 34), k=0.06)
    return arr, P


def slime_tongues(c, w, h, t, seed=1, n=9, top=0, col=(98, 100, 94), length=0.55):
    """толстые глянцевые языки серой слизи, медленно сползающие со стены/потолка"""
    r = random.Random(seed)
    for k in range(n):
        x = w * (0.05 + 0.9 * (k + r.random() * 0.6) / n)
        wd = w * r.uniform(0.04, 0.1)
        ln = h * length * r.uniform(0.5, 1.0) * (1 + 0.04 * math.sin(t * 0.7 + k))
        tip = top + ln + 20 * math.sin(t * 0.9 + k * 1.3)
        c.move_to(x - wd, top)
        c.curve_to(x - wd * 0.9, top + ln * 0.5, x - wd * 0.6, tip - wd, x, tip)
        c.curve_to(x + wd * 0.6, tip - wd, x + wd * 0.9, top + ln * 0.5, x + wd, top)
        c.close_path()
        c.set_source(lin(x - wd, 0, x + wd, 0, [(0, shade(col, 0.55), 0.97), (0.3, shade(col, 1.2), 0.97),
                                                (0.55, col, 0.97), (1, shade(col, 0.5), 0.97)]))
        c.fill()
        ellipse(c, x - wd * 0.35, top + ln * 0.45, wd * 0.12, ln * 0.3)
        fill(c, (200, 204, 196), 0.25)
        # капля на кончике
        dy = (t * 120 + k * 97) % 400
        if dy < 300:
            ellipse(c, x, tip + dy, wd * 0.14, wd * 0.2)
            fill(c, shade(col, 1.1), 0.9)


def tooth_room(w=CW, h=CH, seed=7):
    """комната-зубец: слизь сползает с потолка и стен, на полу серая жижа и вёдра (статичная часть)"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (40, 44, 44))
    P = Persp(w, h, f=w * 0.6, vy=h * 0.42, eye=1.6)
    d, half, height = 6.0, 3.0, 3.6
    quad(c, P, [(-half, 0, d), (half, 0, d), (half, height, d), (-half, height, d)])
    fill(c, (64, 68, 66))
    for sx in (-1, 1):
        quad(c, P, [(sx * half, 0, 0.5), (sx * half, height, 0.5), (sx * half, height, d), (sx * half, 0, d)])
        fill(c, (54, 58, 56))
    quad(c, P, [(-half, height, 0.5), (half, height, 0.5), (half, height, d), (-half, height, d)])
    fill(c, (48, 50, 50))
    quad(c, P, [(-half, 0, 0.5), (half, 0, 0.5), (half, 0, d), (-half, 0, d)])
    fill(c, (70, 72, 68))
    # жижа на полу
    r = random.Random(seed)
    for _ in range(26):
        zz = r.uniform(1.0, d)
        a = P.p(r.uniform(-half, half), 0, zz)
        rx = P.s(zz) * r.uniform(0.3, 1.2)
        ellipse(c, a[0], a[1], rx, rx * 1.6 / zz)
        c.set_source(rad(a[0], a[1], 0, rx, [(0, (146, 148, 140), 0.95), (1, (120, 122, 116), 0)]))
        c.fill()
    # серая масса, облепившая заднюю стену и потолок
    a, b = P.p(-half, height, d), P.p(half, 0, d)
    for k in range(30):
        x = a[0] + r.random() * (b[0] - a[0])
        y = a[1] + r.random() * (b[1] - a[1]) * 0.7
        ellipse(c, x, y, r.uniform(30, 90), r.uniform(40, 140))
        fill(c, (92, 94, 88), 0.5)
    arr = cv.premul()
    L = light_map(w, h, [(w / 2, h * 0.35, w * 0.6, h * 0.45, 0.9)], 0.3)
    arr[..., :3] *= L[..., None]
    kit.texture(arr, 0.18, 6, seed=seed, fine=0.07)
    return arr, P


def receiver(w=CW, h=CH, seed=11):
    """приёмник: длинная щель в стене (от колена до пояса, метра четыре), стена над ней утоплена на полметра,
    внутри непрерывная лента; рядом окошко с чистыми блестящими вёдрами на выступе"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (36, 40, 42))
    wall_panels(c, -40, -40, w + 40, h * 0.8, 300, 400, seed, rust=0.2)
    y0, y1 = h * 0.5, h * 0.62
    c.rectangle(-10, h * 0.3, w * 0.78, h * 0.2)                 # утопленная стена над щелью
    c.set_source(lin(0, h * 0.3, 0, h * 0.5, [(0, (20, 22, 24), 1), (1, (44, 48, 50), 1)]))
    c.fill()
    c.rectangle(-10, y0, w * 0.78, y1 - y0)
    fill(c, (6, 8, 8))
    c.rectangle(-10, y1 - 34, w * 0.78, 34)                       # лента
    fill(c, (34, 34, 32))
    # окошко с чистыми вёдрами
    wx = w * 0.82
    c.rectangle(wx - 10, h * 0.4, w * 0.2, h * 0.22)
    fill(c, (10, 12, 12))
    c.rectangle(wx - 30, h * 0.6, w * 0.24, 30)
    fill(c, (90, 94, 96))
    c.rectangle(0, h * 0.8, w, h * 0.2)
    c.set_source(lin(0, h * 0.8, 0, h, [(0, (60, 62, 58), 1), (1, (30, 32, 30), 1)]))
    c.fill()
    r = random.Random(seed)
    for _ in range(18):
        x, y = r.uniform(0, w), r.uniform(h * 0.82, h)
        ellipse(c, x, y, r.uniform(40, 160), r.uniform(10, 30))
        fill(c, (130, 132, 124), 0.7)
    L = light_map(w, h, [(w * 0.4, h * 0.45, w * 0.7, h * 0.35, 0.8)], 0.3)
    return _finish(cv, 0.14, seed, L)


def bucket(c, x, y, s, fill_lvl=0.0, slime=False, shine=1.0):
    """стальное блестящее ведро ~20 л: бачок, книзу не сужается, тонкая железная дужка"""
    w, hh = s * 0.62, s * 0.72
    c.rectangle(x - w / 2, y - hh, w, hh)
    c.set_source(lin(x - w / 2, 0, x + w / 2, 0, [(0, (60, 64, 68), 1), (0.25, (200, 208, 214), 1), (0.45, (130, 136, 140), 1),
                                                  (0.8, (70, 74, 78), 1), (1, (40, 42, 46), 1)]))
    c.fill()
    for k in (0.12, 0.88):
        c.rectangle(x - w / 2, y - hh * k - 3, w, 6)
        fill(c, (40, 42, 44), 0.6)
    ellipse(c, x, y - hh, w / 2, s * 0.08)
    fill(c, (26, 28, 30))
    if fill_lvl > 0:
        ellipse(c, x, y - hh + s * 0.02, w / 2 * 0.92, s * 0.065)
        fill(c, (140, 142, 134))
    if slime:
        for k in range(3):
            c.rectangle(x - w / 2 + w * (0.2 + k * 0.3), y - hh, w * 0.06, hh * (0.2 + 0.2 * k))
            fill(c, (130, 132, 124), 0.8)
    c.move_to(x - w / 2, y - hh)
    c.curve_to(x - w / 2, y - hh - s * 0.5, x + w / 2, y - hh - s * 0.5, x + w / 2, y - hh)
    stroke(c, (150, 156, 160), max(1.5, s * 0.02), 0.95)


def shower(w=CW, h=CH):
    """душевая: металлические стены «под кафель», решётка в полу и в потолке"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (60, 66, 68))
    for y in range(0, h, 90):
        for x in range(-(y // 90 % 2) * 45, w, 90):
            c.rectangle(x + 2, y + 2, 86, 86)
            fill(c, shade((92, 100, 102), 0.8 + 0.2 * ((x * 7 + y * 3) % 5) / 5))
    c.rectangle(w * 0.2, 0, w * 0.6, h * 0.08)
    fill(c, (20, 22, 24))
    for k in range(16):
        c.rectangle(w * 0.2 + k * w * 0.6 / 16, 0, 10, h * 0.08)
        fill(c, (80, 86, 88))
    c.rectangle(w * 0.15, h * 0.9, w * 0.7, h * 0.1)
    fill(c, (18, 20, 22))
    for k in range(18):
        c.rectangle(w * 0.15 + k * w * 0.7 / 18, h * 0.9, 12, h * 0.1)
        fill(c, (76, 80, 82))
    L = light_map(w, h, [(w / 2, h * 0.1, w * 0.5, h * 0.6, 0.9)], 0.35)
    return _finish(cv, 0.1, 21, L)


# ── клукс-17 ───────────────────────────────────────────────────────────────
def klux_map(w=CW, h=CH):
    """схема на стене: на сером фоне чёрная колючая клякса — дохлый раздувшийся ёж"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (40, 44, 46))
    wall_panels(c, -40, -40, w + 40, h + 40, 340, 460, 31, rust=0.15)
    x0, y0, x1, y1 = w * 0.1, h * 0.18, w * 0.9, h * 0.66
    c.rectangle(x0 - 16, y0 - 16, x1 - x0 + 32, y1 - y0 + 32)
    fill(c, (16, 16, 18))
    c.rectangle(x0, y0, x1 - x0, y1 - y0)
    fill(c, (150, 150, 146))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - 40
    r = random.Random(4)
    pts = []
    n = 26
    for k in range(n):
        a = k / n * math.tau
        rr = 190 * (1 + 0.12 * math.sin(a * 3))
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.75))
    smooth_path(c, pts)
    fill(c, (14, 14, 16))
    for k in range(n):                           # иглы
        a = (k + 0.5) / n * math.tau
        rr = 190 * (1 + 0.12 * math.sin(a * 3))
        bx, by = cx + math.cos(a) * rr * 0.95, cy + math.sin(a) * rr * 0.75 * 0.95
        L = r.uniform(140, 260)
        poly(c, [(bx + math.cos(a + 1.57) * 18, by + math.sin(a + 1.57) * 14),
                 (bx + math.cos(a) * L, by + math.sin(a) * L * 0.8),
                 (bx - math.cos(a + 1.57) * 18, by - math.sin(a + 1.57) * 14)])
        fill(c, (14, 14, 16))
    for k in range(4):                           # лапки кверху
        a = math.pi * (0.25 + k * 0.17)
        poly(c, [(cx + math.cos(a) * 120 - 14, cy + 120), (cx + math.cos(a) * 140, cy + 230), (cx + math.cos(a) * 120 + 14, cy + 120)])
        fill(c, (14, 14, 16))
    text(c, cx, y1 - 70, 'КЛУКС-17', 64, (20, 20, 22))
    for k in range(5):
        c.rectangle(x0 + 60, y1 + 70 + k * 46, (x1 - x0 - 120) * (0.6 + 0.4 * ((k * 37) % 5) / 5), 14)
        fill(c, (120, 120, 116), 0.8)
    L = light_map(w, h, [(w / 2, h * 0.4, w * 0.7, h * 0.4, 0.9)], 0.3)
    return _finish(cv, 0.12, 33, L)


def klux(w=CW, h=CH, seed=17):
    """огромный зал: сотня квадратных столиков ровными рядами, лавки прикручены к полу; в центре толстенное вздутие
    с кучей дверок; по периметру входы в «иглы»; мягкий тёплый свет; большая неподвижная сфера и мелкие"""
    P = Persp(w, h, f=w * 0.8, vy=h * 0.4, eye=1.8)
    cv = kit.Canvas(w, h)
    c = cv.ctx
    r = random.Random(seed)
    c.rectangle(0, 0, w, h)
    c.set_source(lin(0, 0, 0, h, [(0, (26, 26, 28), 1), (0.4, (60, 54, 46), 1), (1, (38, 36, 34), 1)]))
    c.fill()
    D, half, height = 40, 14, 9
    # пол: плитка
    for zz in np.arange(2, D, 2):
        a, b = P.p(-half, 0, zz), P.p(half, 0, zz)
        c.move_to(*a)
        c.line_to(*b)
        stroke(c, (30, 28, 26), max(1, P.s(zz) * 0.02), 0.6)
    for xx in np.arange(-half, half, 2):
        a, b = P.p(xx, 0, 2), P.p(xx, 0, D)
        c.move_to(*a)
        c.line_to(*b)
        stroke(c, (30, 28, 26), 2, 0.5)
    # дальняя стена с входами в иглы
    a, b = P.p(-half, height, D), P.p(half, 0, D)
    c.rectangle(a[0], a[1], b[0] - a[0], b[1] - a[1])
    fill(c, (52, 50, 48))
    for xx in np.arange(-half + 2, half, 4.2):
        p0, p1 = P.p(xx, 2.6, D), P.p(xx + 2.2, 0, D)
        c.rectangle(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1])
        fill(c, (14, 14, 16))
        for k in range(3):                       # в глубине иглы — огоньки капсул
            q0 = P.p(xx + 0.4 + k * 0.6, 1.6, D + 3)
            ellipse(c, q0[0], q0[1], 3, 2)
            fill(c, (60, 230, 120) if (k + int(xx)) % 2 else (230, 60, 50), 0.9)
    # вздутие в центре с дверками
    bx, bz = 0, 16
    top = P.p(0, 7.0, bz)
    bot = P.p(0, 0, bz)
    rw = P.s(bz) * 6.5
    c.move_to(top[0] - rw * 0.55, bot[1])
    c.curve_to(top[0] - rw * 0.75, top[1] + 120, top[0] - rw * 0.4, top[1] - 30, top[0], top[1] - 30)
    c.curve_to(top[0] + rw * 0.4, top[1] - 30, top[0] + rw * 0.75, top[1] + 120, top[0] + rw * 0.55, bot[1])
    c.close_path()
    c.set_source(lin(top[0] - rw * 0.6, 0, top[0] + rw * 0.6, 0, [(0, (50, 52, 54), 1), (0.4, (126, 128, 126), 1),
                                                                  (1, (40, 42, 44), 1)]))
    c.fill()
    for row in range(2):
        for k in range(-3, 4):
            dx = k * rw * 0.13 * (1 - row * 0.15)
            y = bot[1] - (row + 1) * P.s(bz) * 2.1
            c.rectangle(top[0] + dx - P.s(bz) * 0.35, y, P.s(bz) * 0.7, P.s(bz) * 1.8)
            fill(c, (34, 36, 38))
            c.rectangle(top[0] + dx - P.s(bz) * 0.35, y, P.s(bz) * 0.7, P.s(bz) * 1.8)
            stroke(c, (60, 230, 120), 2, 0.8)
    # большая неподвижная сфера над вздутием
    sp = P.p(0, 8.2, bz)
    places.sphere(c, sp[0], sp[1], P.s(bz) * 1.6, 0.0)
    # столики рядами (ближние — крупнее), лавки прикручены
    for zz in np.arange(2.5, 34, 2.6)[::-1]:
        for xx in np.arange(-half + 1.5, half - 1, 2.8):
            if abs(xx) < 4.5 and abs(zz - bz) < 4.5:
                continue
            p = P.p(xx, 0.75, zz)
            s_ = P.s(zz)
            if p[0] < -s_ or p[0] > w + s_:
                continue
            for dz in (-0.75, 0.75):                    # лавки
                q0 = P.p(xx - 0.6, 0.45, zz + dz)
                q1 = P.p(xx + 0.6, 0.45, zz + dz)
                c.rectangle(q0[0], q0[1], q1[0] - q0[0], max(2, s_ * 0.08))
                fill(c, (70, 60, 50))
                c.rectangle(q0[0], q0[1] - s_ * 0.3, q1[0] - q0[0], max(2, s_ * 0.06))
                fill(c, (60, 52, 44))
            t0, t1 = P.p(xx - 0.5, 0.75, zz - 0.5), P.p(xx + 0.5, 0.75, zz + 0.5)
            poly(c, [P.p(xx - 0.5, 0.75, zz - 0.5), P.p(xx + 0.5, 0.75, zz - 0.5), P.p(xx + 0.5, 0.75, zz + 0.5),
                     P.p(xx - 0.5, 0.75, zz + 0.5)])
            fill(c, (120, 112, 100))
            c.rectangle(p[0] - s_ * 0.05, p[1], s_ * 0.1, s_ * 0.75)
            fill(c, (40, 38, 36))
    # мелкие сферы под потолком
    for k in range(10):
        p = P.p(r.uniform(-half, half), height - 0.4, r.uniform(8, 50))
        places.sphere(c, p[0], p[1], P.s(20) * 0.4, k)
    arr = cv.premul()
    L = light_map(w, h, [(w / 2, h * 0.55, w * 0.9, h * 0.4, 0.9), (w * 0.2, h * 0.3, w * 0.3, h * 0.2, 0.3),
                         (w * 0.8, h * 0.3, w * 0.3, h * 0.2, 0.3)], 0.35)
    arr[..., :3] *= L[..., None] * np.array([1.08, 1.0, 0.88], np.float32)
    np.clip(arr, 0, 1, out=arr)
    kit.texture(arr, 0.1, 8, seed=seed, fine=0.05)
    return arr, P


VEND = {
    'clothes': ((70, 76, 92), 'ОДЕЖДА'), 'home': ((80, 84, 78), 'БЫТ'), 'food': ((96, 74, 60), 'ЕДА'),
    'camo': ((74, 82, 52), 'ЭКИПИРОВКА'), 'arms': ((52, 54, 58), 'ОРУЖИЕ'),
}


def vending(kind, w=900, h=1500, seed=1):
    """торговый автомат со светящейся витриной: полочки и товары по книге"""
    col, _ = VEND[kind]
    cv = kit.Canvas(w, h)
    c = cv.ctx
    r = random.Random(seed + len(kind))
    c.rectangle(0, 0, w, h)
    c.set_source(lin(0, 0, w, 0, [(0, shade(col, 0.6), 1), (0.4, col, 1), (1, shade(col, 0.5), 1)]))
    c.fill()
    if kind == 'camo':                          # камуфляжные пятна
        for _ in range(40):
            ellipse(c, r.uniform(0, w), r.uniform(0, h), r.uniform(40, 120), r.uniform(30, 80), r.random())
            fill(c, r.choice([(52, 60, 36), (96, 92, 60), (40, 44, 30)]), 0.8)
    gx0, gy0, gx1, gy1 = w * 0.08, h * 0.06, w * 0.92, h * 0.78
    c.rectangle(gx0, gy0, gx1 - gx0, gy1 - gy0)
    c.set_source(lin(0, gy0, 0, gy1, [(0, (200, 220, 210), 1), (1, (110, 130, 126), 1)]))
    c.fill()
    shelves = 6
    for k in range(shelves):
        y = gy0 + (k + 1) * (gy1 - gy0) / shelves
        c.rectangle(gx0, y - 8, gx1 - gx0, 8)
        fill(c, (60, 64, 66))
        n = 5
        for m in range(n):
            x = gx0 + (m + 0.5) * (gx1 - gx0) / n
            item(c, kind, k, m, x, y - 8, (gx1 - gx0) / n * 0.7, (gy1 - gy0) / shelves * 0.8, r)
    # блик стекла
    poly(c, [(gx0, gy0), (gx0 + (gx1 - gx0) * 0.35, gy0), (gx0 + (gx1 - gx0) * 0.12, gy1), (gx0, gy1)])
    fill(c, (255, 255, 255), 0.08)
    c.rectangle(gx0, gy0, gx1 - gx0, gy1 - gy0)
    stroke(c, (20, 22, 24), 10, 1)
    # окошко выдачи и кнопка
    c.rectangle(w * 0.2, h * 0.84, w * 0.6, h * 0.09)
    fill(c, (10, 12, 12))
    ellipse(c, w * 0.86, h * 0.82, 30, 30)
    fill(c, (14, 14, 16))
    c.rectangle(w * 0.08, h * 0.8, w * 0.1, h * 0.05)
    fill(c, (6, 8, 8))
    return c and kit.texture(cv.premul(), 0.1, 6, seed=seed, fine=0.04)


def item(c, kind, k, m, x, y, w, h, r):
    if kind == 'clothes':
        if k < 2:                                # головные уборы вверху
            ellipse(c, x, y - h * 0.3, w * 0.4, h * 0.3)
            fill(c, r.choice([(40, 50, 90), (130, 40, 40), (40, 40, 40), (180, 160, 60)]))
            c.rectangle(x - w * 0.1, y - h * 0.08, w * 0.6, h * 0.08)
            fill(c, (30, 30, 34))
        elif k < 5:                              # пакеты с майками и шортами
            c.rectangle(x - w * 0.4, y - h * 0.8, w * 0.8, h * 0.8)
            fill(c, r.choice([(170, 60, 60), (60, 120, 170), (220, 220, 210), (70, 140, 80), (40, 40, 44)]))
            c.rectangle(x - w * 0.4, y - h * 0.8, w * 0.8, h * 0.8)
            fill(c, (255, 255, 255), 0.15)
        else:                                    # обувь внизу — шлёпанцы
            ellipse(c, x - w * 0.18, y - h * 0.1, w * 0.16, h * 0.1)
            fill(c, (40, 40, 44))
            ellipse(c, x + w * 0.18, y - h * 0.1, w * 0.16, h * 0.1)
            fill(c, (40, 40, 44))
    elif kind == 'home':
        g = (k + m) % 4
        if g == 0:                               # плоская фляга
            c.rectangle(x - w * 0.22, y - h * 0.85, w * 0.44, h * 0.85)
            c.set_source(lin(x - w * 0.22, 0, x + w * 0.22, 0, [(0, (100, 104, 108), 1), (0.4, (210, 214, 216), 1),
                                                                (1, (80, 84, 88), 1)]))
            c.fill()
        elif g == 1:                             # кружка
            c.rectangle(x - w * 0.25, y - h * 0.5, w * 0.4, h * 0.5)
            fill(c, (200, 196, 186))
            ellipse(c, x + w * 0.2, y - h * 0.25, w * 0.1, h * 0.14)
            stroke(c, (200, 196, 186), 6, 1)
        elif g == 2:                             # полотенце
            c.rectangle(x - w * 0.4, y - h * 0.4, w * 0.8, h * 0.4)
            fill(c, (110, 140, 170))
        else:                                    # бритва
            c.rectangle(x - w * 0.05, y - h * 0.7, w * 0.1, h * 0.7)
            fill(c, (60, 60, 64))
            c.rectangle(x - w * 0.25, y - h * 0.75, w * 0.5, h * 0.1)
            fill(c, (160, 164, 168))
    elif kind == 'food':
        g = (k + m) % 3
        if g == 0:                               # широкогорлая бутылка воды
            c.rectangle(x - w * 0.25, y - h * 0.75, w * 0.5, h * 0.75)
            fill(c, (150, 200, 220), 0.75)
            c.rectangle(x - w * 0.14, y - h * 0.9, w * 0.28, h * 0.15)
            fill(c, (60, 110, 150))
        elif g == 1:                             # бумажный пакетик супа/киселя
            c.rectangle(x - w * 0.3, y - h * 0.7, w * 0.6, h * 0.7)
            fill(c, r.choice([(200, 170, 120), (220, 120, 120), (230, 200, 90)]))
            c.rectangle(x - w * 0.3, y - h * 0.45, w * 0.6, h * 0.1)
            fill(c, (60, 40, 30), 0.7)
        else:                                    # кубики
            for q in range(3):
                c.rectangle(x - w * 0.3 + q * w * 0.22, y - h * 0.2, w * 0.18, h * 0.2)
                fill(c, (190, 176, 130))
    elif kind == 'camo':
        g = (k + m) % 4
        if g == 0:                               # шлем с прозрачным забралом
            ellipse(c, x, y - h * 0.4, w * 0.4, h * 0.4)
            fill(c, (60, 66, 50))
            ellipse(c, x, y - h * 0.3, w * 0.3, h * 0.18)
            fill(c, (180, 220, 230), 0.5)
        elif g == 1:                             # жилет
            poly(c, [(x - w * 0.35, y), (x - w * 0.35, y - h * 0.7), (x - w * 0.1, y - h * 0.85), (x + w * 0.1, y - h * 0.85),
                     (x + w * 0.35, y - h * 0.7), (x + w * 0.35, y)])
            fill(c, (64, 70, 50))
        else:                                    # наколенники
            ellipse(c, x - w * 0.15, y - h * 0.3, w * 0.14, h * 0.3)
            fill(c, (30, 32, 30))
            ellipse(c, x + w * 0.15, y - h * 0.3, w * 0.14, h * 0.3)
            fill(c, (30, 32, 30))
    elif kind == 'arms':
        g = (k + m) % 4
        if g == 0:                               # резиновая дубинка
            c.rectangle(x - w * 0.05, y - h * 0.95, w * 0.1, h * 0.95)
            fill(c, (20, 20, 22))
            c.rectangle(x - w * 0.12, y - h * 0.3, w * 0.24, h * 0.05)
            fill(c, (40, 40, 44))
        elif g == 1:                             # охотничий нож
            poly(c, [(x - w * 0.04, y), (x - w * 0.04, y - h * 0.35), (x - w * 0.06, y - h * 0.9), (x + w * 0.06, y - h * 0.4),
                     (x + w * 0.04, y)])
            c.set_source(lin(x - w * 0.06, 0, x + w * 0.06, 0, [(0, (120, 124, 130), 1), (0.5, (230, 234, 238), 1),
                                                                (1, (100, 104, 110), 1)]))
            c.fill()
            c.rectangle(x - w * 0.06, y - h * 0.3, w * 0.12, h * 0.3)
            fill(c, (60, 40, 30))
        elif g == 2:                             # электрошокер
            c.rectangle(x - w * 0.15, y - h * 0.55, w * 0.3, h * 0.55)
            fill(c, (30, 30, 34))
            c.rectangle(x - w * 0.08, y - h * 0.65, w * 0.04, h * 0.1)
            fill(c, (200, 200, 210))
            c.rectangle(x + w * 0.04, y - h * 0.65, w * 0.04, h * 0.1)
            fill(c, (200, 200, 210))
            ellipse(c, x, y - h * 0.35, w * 0.05, w * 0.05)
            fill(c, (255, 200, 40))
        else:                                    # дымовая шашка
            c.rectangle(x - w * 0.15, y - h * 0.6, w * 0.3, h * 0.6)
            fill(c, (90, 96, 70))
            c.rectangle(x - w * 0.15, y - h * 0.45, w * 0.3, h * 0.08)
            fill(c, (200, 180, 60))


def capsule_wall(w=CW, h=CH, seed=23, litter=True):
    """игла изнутри: крышки капсул с зелёным контуром в два яруса, лесенки ко второму, огоньки «Занята/Свободна»"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (30, 32, 34))
    r = random.Random(seed)
    P = Persp(w, h, f=w * 0.55, vy=h * 0.4, eye=1.7)
    half, height, D = 2.0, 4.4, 22
    for sx in (-1, 1):
        quad(c, P, [(sx * half, 0, 0.6), (sx * half, height, 0.6), (sx * half, height, D), (sx * half, 0, D)])
        fill(c, (46, 50, 52))
        for zz in np.arange(1.0, D - 1, 2.2):
            for tier, (y0, y1) in enumerate(((0.15, 1.95), (2.2, 4.0))):
                pts = [(sx * half, y0, zz), (sx * half, y1, zz), (sx * half, y1, zz + 1.9), (sx * half, y0, zz + 1.9)]
                quad(c, P, pts)
                fill(c, (58, 62, 64))
                quad(c, P, pts)
                stroke(c, (60, 230, 120), max(1.2, P.s(zz) * 0.03), 0.85)
                free = tier == 1 and r.random() < 0.45
                lp = P.p(sx * half, y1 - 0.25, zz + 0.95)
                ellipse(c, lp[0], lp[1], max(2, P.s(zz) * 0.08), max(1.5, P.s(zz) * 0.05))
                fill(c, (60, 255, 130) if free else (255, 60, 50), 1)
                bp = P.p(sx * half, (y0 + y1) / 2, zz + 1.6)
                c.rectangle(bp[0] - P.s(zz) * 0.05, bp[1] - P.s(zz) * 0.05, P.s(zz) * 0.1, P.s(zz) * 0.1)
                fill(c, (6, 6, 8))
            # лесенка ко второму ярусу
            for k in range(8):
                a, b = P.p(sx * (half - 0.25), 0.3 + k * 0.5, zz + 1.95), P.p(sx * (half - 0.25), 0.3 + k * 0.5, zz + 2.15)
                c.move_to(*a)
                c.line_to(*b)
                stroke(c, (120, 124, 126), max(1, P.s(zz) * 0.03), 1)
            for dz in (1.95, 2.15):
                a, b = P.p(sx * (half - 0.25), 0, zz + dz), P.p(sx * (half - 0.25), 4.1, zz + dz)
                c.move_to(*a)
                c.line_to(*b)
                stroke(c, (100, 104, 106), max(1, P.s(zz) * 0.035), 1)
    quad(c, P, [(-half, 0, 0.6), (half, 0, 0.6), (half, 0, D), (-half, 0, D)])
    fill(c, (40, 42, 42))
    quad(c, P, [(-half, height, 0.6), (half, height, 0.6), (half, height, D), (-half, height, D)])
    fill(c, (22, 24, 26))
    if litter:                                   # мусор у стен — окраина для бедноты
        for _ in range(60):
            zz = r.uniform(1, D * 0.8)
            xx = r.choice((-1, 1)) * r.uniform(half * 0.6, half * 0.98)
            p = P.p(xx, 0, zz)
            s_ = P.s(zz) * r.uniform(0.06, 0.2)
            if r.random() < 0.5:
                poly(c, [(p[0] - s_, p[1]), (p[0] - s_ * 0.3, p[1] - s_ * 0.6), (p[0] + s_, p[1] - s_ * 0.2)])
                fill(c, r.choice([(150, 140, 120), (90, 110, 130), (170, 60, 50)]), 0.9)
            else:
                ellipse(c, p[0], p[1], s_, s_ * 0.4)
                fill(c, r.choice([(150, 200, 220), (200, 190, 170)]), 0.6)
    arr = cv.premul()
    L = light_map(w, h, [(w / 2, h * 0.45, w * 0.7, h * 0.5, 0.8)], 0.3)
    arr[..., :3] *= L[..., None]
    kit.texture(arr, 0.12, 7, seed=seed, fine=0.05)
    return arr, P


def capsule_in(w=CW, h=CH, lamp=True):
    """внутри капсулы (вид сверху на ложе): двухметровая ниша, мягкое эластичное ложе, тусклый жёлтый плафон, полочка"""
    cv = kit.Canvas(w, h)
    c = cv.ctx
    c.rectangle(0, 0, w, h)
    fill(c, (34, 34, 36))
    c.rectangle(w * 0.12, h * 0.06, w * 0.76, h * 0.9)
    c.set_source(lin(w * 0.12, 0, w * 0.88, 0, [(0, (40, 42, 46), 1), (0.5, (74, 76, 82), 1), (1, (40, 42, 46), 1)]))
    c.fill()
    for k in range(14):                          # стёганое ложе
        y = h * 0.08 + k * h * 0.062
        c.move_to(w * 0.14, y)
        c.line_to(w * 0.86, y)
        stroke(c, (28, 30, 32), 4, 0.7)
    c.rectangle(w * 0.78, h * 0.3, w * 0.12, 22)    # полочка
    fill(c, (90, 92, 96))
    L = light_map(w, h, [(w / 2, h * 0.12, w * 0.5, h * 0.4, 0.9 if lamp else 0.0)], 0.2 if lamp else 0.08)
    arr = cv.premul()
    arr[..., :3] *= L[..., None] * (np.array([1.15, 1.0, 0.7], np.float32) if lamp else 1)
    np.clip(arr, 0, 1, out=arr)
    kit.texture(arr, 0.1, 6, seed=5, fine=0.05)
    return arr
