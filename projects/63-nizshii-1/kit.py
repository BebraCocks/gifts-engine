"""Векторный набор для детальной отрисовки части 1 v2 (pycairo): холст, гладкие контуры, объёмная заливка частей тела,
мягкие тени и фактуры. Стиль — нуар v1 (тил в тенях, тёплый ключевой свет сверху-слева, холодный контровой справа),
но с прорисовкой: анатомия, лица, ткань, грязь, заклёпки (автор 2026-11-27: «детализация везде, локации наполненные»)."""
import math
import functools
import cairo
import numpy as np
from scipy import ndimage

TAU = math.pi * 2
KEY = (-0.55, -0.75)          # направление ключевого света (в экранных координатах, откуда светит)
RIM = (0.36, 0.62, 0.86)      # холодный контровой свет


def rgb(c, a=1.0):
    c = [x / 255 if x > 1 else x for x in c]
    return (c[0], c[1], c[2], a)


def mixc(c1, c2, u):
    return tuple(c1[i] + (c2[i] - c1[i]) * u for i in range(3))


def shade(c, k):
    """k<1 темнее (с уходом в тил), k>1 светлее (в тёплое)"""
    if k < 1:
        t = (1 - k)
        return tuple(max(0, c[i] * k + (np.array([4, 10, 16])[i]) * t) for i in range(3))
    t = k - 1
    return tuple(min(255, c[i] + (255 - c[i]) * t * (0.9, 0.82, 0.7)[i]) for i in range(3))


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        self.ctx = cairo.Context(self.surf)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    def array(self):
        """RGBA float32 0..1, не премультиплицированный"""
        self.surf.flush()
        a = np.ndarray((self.h, self.w, 4), np.uint8, self.surf.get_data()).astype(np.float32) / 255
        out = a[..., [2, 1, 0, 3]].copy()
        al = out[..., 3:4]
        out[..., :3] = np.where(al > 1e-4, out[..., :3] / np.maximum(al, 1e-4), 0)
        return out

    def premul(self):
        self.surf.flush()
        a = np.ndarray((self.h, self.w, 4), np.uint8, self.surf.get_data()).astype(np.float32) / 255
        return a[..., [2, 1, 0, 3]].copy()


def from_premul(arr, canvas=None):
    """premultiplied RGBA float -> новый Canvas с этим содержимым"""
    h, w = arr.shape[:2]
    cv = canvas or Canvas(w, h)
    data = np.ndarray((h, w, 4), np.uint8, cv.surf.get_data())
    data[...] = np.clip(arr[..., [2, 1, 0, 3]] * 255 + 0.5, 0, 255).astype(np.uint8)
    cv.surf.mark_dirty()
    return cv


# ── контуры ────────────────────────────────────────────────────────────────
def smooth_path(ctx, pts, closed=True, tension=0.5):
    """Catmull-Rom через точки -> кубические Безье"""
    n = len(pts)
    if n < 3:
        ctx.move_to(*pts[0])
        for p in pts[1:]:
            ctx.line_to(*p)
        if closed:
            ctx.close_path()
        return
    ctx.move_to(*pts[0])
    if closed:
        segs = [(pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]) for i in range(n)]
    else:
        P = [pts[0]] + list(pts) + [pts[-1]]
        segs = [(P[i - 1], P[i], P[i + 1], P[i + 2]) for i in range(1, n)]
    for p0, p1, p2, p3 in segs:
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        ctx.curve_to(*c1, *c2, *p2)
    if closed:
        ctx.close_path()


def poly(ctx, pts):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


def fill(ctx, color, a=1.0):
    ctx.set_source_rgba(*rgb(color, a))
    ctx.fill()


def stroke(ctx, color, w, a=1.0, keep=False):
    ctx.set_source_rgba(*rgb(color, a))
    ctx.set_line_width(w)
    ctx.stroke_preserve() if keep else ctx.stroke()


def lin(x0, y0, x1, y1, stops):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    for o, c, a in stops:
        g.add_color_stop_rgba(o, *rgb(c, a)[:3], a)
    return g


def rad(x, y, r0, r1, stops, x0=None, y0=None):
    g = cairo.RadialGradient(x if x0 is None else x0, y if y0 is None else y0, r0, x, y, r1)
    for o, c, a in stops:
        g.add_color_stop_rgba(o, *rgb(c, a)[:3], a)
    return g


def ellipse(ctx, x, y, rx, ry, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(max(rx, 0.01), max(ry, 0.01))
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()


def soft_line(ctx, pts, color, w, a, smooth=True):
    """тонкая складка/мышечная линия: широкий прозрачный штрих + узкий потемнее"""
    for k, aa in ((2.6, 0.35), (1.0, 1.0)):
        if smooth and len(pts) > 2:
            smooth_path(ctx, pts, closed=False)
        else:
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
        stroke(ctx, color, w * k, a * aa)


# ── объёмные части тела ─────────────────────────────────────────────────────
def limb_outline(p0, p1, w0, w1, bulge=0.0, bpos=0.4, bside=0.0, wm=None):
    """контур конечности от p0 до p1: ширины w0..w1, мышечное утолщение bulge (доля) около bpos,
    bside сдвигает утолщение на одну сторону (-1..1). Возвращает список точек (левая сторона, затем правая)."""
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    left, right = [], []
    N = 9
    for i in range(N + 1):
        t = i / N
        w = w0 + (w1 - w0) * t
        if wm is not None:
            w = w0 + (wm - w0) * min(1, t / 0.5) if t < 0.5 else wm + (w1 - wm) * (t - 0.5) / 0.5
        b = bulge * math.exp(-((t - bpos) / 0.22) ** 2) * w
        cx, cy = x0 + ux * L * t, y0 + uy * L * t
        wl = w / 2 + b * (1 + bside) * 0.5
        wr = w / 2 + b * (1 - bside) * 0.5
        left.append((cx + nx * wl, cy + ny * wl))
        right.append((cx - nx * wr, cy - ny * wr))
    return left + right[::-1]


def volume_fill(ctx, pts, p0, p1, w, color, light=1.0, rim=0.5, closed=True):
    """заливка формы с цилиндрическим затенением поперёк оси p0->p1 (свет сверху-слева, тил-контр справа)"""
    x0, y0 = p0
    x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0) or 1
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    # сторона, повёрнутая к свету
    if nx * KEY[0] + ny * KEY[1] > 0:
        nx, ny = -nx, -ny
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    r = w * 0.62
    ax, ay = mx - nx * r, my - ny * r          # освещённый край
    bx, by = mx + nx * r, my + ny * r          # теневой край
    c = color
    g = lin(ax, ay, bx, by, [
        (0.0, shade(c, 0.78), 1), (0.16, shade(c, 1.0 + 0.10 * light), 1), (0.34, shade(c, 1.0 + 0.04 * light), 1),
        (0.62, shade(c, 0.74), 1), (0.86, shade(c, 0.46), 1), (1.0, shade(c, 0.5 + 0.3 * rim), 1)])
    smooth_path(ctx, pts, closed=closed)
    ctx.set_source(g)
    ctx.fill_preserve()
    # холодный контровой край
    g2 = lin(ax, ay, bx, by, [(0.78, (0, 0, 0), 0), (1.0, tuple(v * 255 for v in RIM), 0.38 * rim)])
    ctx.set_source(g2)
    ctx.fill_preserve()
    ctx.new_path()


def limb(ctx, p0, p1, w0, w1, color, bulge=0.0, bpos=0.4, bside=0.0, light=1.0, rim=0.6, wm=None, outline=True):
    pts = limb_outline(p0, p1, w0, w1, bulge, bpos, bside, wm)
    volume_fill(ctx, pts, p0, p1, max(w0, w1, wm or 0) * (1 + bulge), color, light, rim)
    if outline:
        smooth_path(ctx, pts)
        stroke(ctx, shade(color, 0.3), 1.6, 0.55)
    return pts


def blob(ctx, x, y, rx, ry, color, rot=0.0, light=1.0, rim=0.6, outline=True):
    """эллипс со сферическим затенением"""
    lx, ly = x + KEY[0] * rx * 0.45, y + KEY[1] * ry * 0.45
    g = rad(x, y, 0, max(rx, ry) * 1.15, [(0, shade(color, 1.0 + 0.12 * light), 1), (0.55, color, 1),
                                          (0.85, shade(color, 0.6), 1), (1.0, shade(color, 0.45), 1)], lx, ly)
    ellipse(ctx, x, y, rx, ry, rot)
    ctx.set_source(g)
    ctx.fill_preserve()
    g2 = lin(x - rx, y, x + rx, y, [(0.72, (0, 0, 0), 0), (1.0, tuple(v * 255 for v in RIM), 0.35 * rim)])
    ctx.set_source(g2)
    ctx.fill_preserve()
    if outline:
        stroke(ctx, shade(color, 0.3), 1.4, 0.5)
    ctx.new_path()


# ── пост-обработка в numpy ──────────────────────────────────────────────────
def blur_premul(arr, s):
    return np.stack([ndimage.gaussian_filter(arr[..., i], s) for i in range(4)], -1) if s > 0 else arr


def over(dst, src, x=0, y=0, a=1.0):
    """premultiplied src поверх premultiplied dst (in-place), со сдвигом"""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return dst
    s = src[y0 - y:y1 - y, x0 - x:x1 - x] * a
    d = dst[y0:y1, x0:x1]
    d *= (1 - s[..., 3:4])
    d += s
    return dst


@functools.lru_cache(None)
def noise(h, w, scale, seed=0):
    """гладкий шум 0..1"""
    r = np.random.default_rng(seed).random((max(2, h // scale + 2), max(2, w // scale + 2))).astype(np.float32)
    z = ndimage.zoom(r, (h / (r.shape[0] - 1) + 0.01, w / (r.shape[1] - 1) + 0.01), order=3)[:h, :w]
    z = ndimage.gaussian_filter(z, max(1, scale / 4))
    z = (z - z.min()) / (np.ptp(z) + 1e-6)
    return z


_TEX = {}


def _tex(seed):
    if seed not in _TEX:
        r = np.random.default_rng(seed)
        big = ndimage.gaussian_filter(r.random((512, 512)).astype(np.float32), 2.5, mode='wrap')
        big = (big - big.min()) / (np.ptp(big) + 1e-6) - 0.5
        fine = r.random((512, 512)).astype(np.float32) - 0.5
        _TEX[seed] = (big, fine)
    return _TEX[seed]


def texture(arr, amount=0.12, scale=6, seed=1, fine=0.05):
    """грязь/поры на премультиплированном слое: модуляция яркости внутри альфы (общая плитка шума)"""
    h, w = arr.shape[:2]
    big, fn = _tex(seed)
    ry, rx = -(-h // 512), -(-w // 512)
    n = np.tile(big, (ry, rx))[:h, :w]
    f = np.tile(fn, (ry, rx))[:h, :w]
    k = 1 + n * amount * 2 + f * fine
    arr[..., :3] *= k[..., None]
    np.clip(arr, 0, None, out=arr)
    arr[..., :3] = np.minimum(arr[..., :3], arr[..., 3:4])
    return arr


def drop_shadow(arr, s=12, dx=10, dy=16, a=0.5):
    sh = np.zeros_like(arr)
    sh[..., 3] = arr[..., 3]
    sh = blur_premul(sh, s)
    sh = np.roll(np.roll(sh, dy, 0), dx, 1) * a
    out = sh.copy()
    over(out, arr)
    return out
