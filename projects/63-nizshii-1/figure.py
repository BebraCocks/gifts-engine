"""Отрисовка людей части 1 v2: цельные силуэты (конечность — одним контуром через сустав), объём по форме
(нормали из поля расстояний, как в v1, но по каждой части отдельно), анатомия — мягкими размытыми слоями теней
и бликов, лицо и мелочи — чётко поверх. Позы — people.pose(), внешность — people.look().

    arr = figure.render(j, look, face, box=(x0, y0, w, h))   # premultiplied RGBA float32 размера (h, w)"""
import math
import random
import numpy as np
from scipy import ndimage
import kit
import people as pp
from kit import smooth_path, fill, stroke, ellipse, rad, lin, shade

LIGHT = np.array([-0.5, -0.62, 0.6], np.float32)
LIGHT /= np.linalg.norm(LIGHT)
RIM = np.array([92, 150, 210], np.float32) / 255
AMB = np.array([0.10, 0.15, 0.20], np.float32)


# ── формы ──────────────────────────────────────────────────────────────────
def chain_outline(pts, widths, bulges=(), samples=40):
    """контур вдоль ломаной pts (суставы) с шириной widths[i] в каждом суставе.
    bulges: (t, amp, side, sigma) — t в долях всей длины, side +1 латерально (налево от направления), -1 медиально."""
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(seg) or 1
    cum = np.cumsum([0] + seg) / total
    left, right = [], []
    for k in range(samples + 1):
        t = k / samples
        i = min(len(seg) - 1, int(np.searchsorted(cum, t, 'right') - 1))
        lt = (t - cum[i]) / max(1e-6, cum[i + 1] - cum[i])
        p = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * lt, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * lt)
        w = widths[i] + (widths[i + 1] - widths[i]) * (lt * lt * (3 - 2 * lt))
        # направление: сглаженное около суставов
        d0 = np.subtract(pts[i + 1], pts[i])
        d0 = d0 / (np.linalg.norm(d0) + 1e-6)
        d = d0
        if lt < 0.25 and i > 0:
            dp = np.subtract(pts[i], pts[i - 1])
            dp = dp / (np.linalg.norm(dp) + 1e-6)
            m = 0.5 + lt * 2
            d = dp * (1 - m) + d0 * m
        elif lt > 0.75 and i < len(seg) - 1:
            dn = np.subtract(pts[i + 2], pts[i + 1])
            dn = dn / (np.linalg.norm(dn) + 1e-6)
            m = 0.5 + (1 - lt) * 2
            d = d0 * m + dn * (1 - m)
        d = d / (np.linalg.norm(d) + 1e-6)
        nx, ny = -d[1], d[0]
        wl = wr = w / 2
        for bt, amp, side, sg in bulges:
            b = amp * w * math.exp(-((t - bt) / sg) ** 2)
            if side >= 0:
                wl += b * (1 if side > 0 else 0.5)
            if side <= 0:
                wr += b * (1 if side < 0 else 0.5)
        left.append((p[0] + nx * wl, p[1] + ny * wl))
        right.append((p[0] - nx * wr, p[1] - ny * wr))
    return left + right[::-1]


ARM = {   # ширины в «головах» u: плечо, локоть, запястье; мышечные профили
    'old': ((0.30, 0.25, 0.2), [(0.18, 0.12, -1, 0.12), (0.36, 0.08, -1, 0.1), (0.5, 0.14, 0, 0.05),
                                (0.62, 0.12, 1, 0.1)]),
    'strong': ((0.46, 0.36, 0.25), [(0.25, 0.28, 1, 0.13), (0.22, 0.18, -1, 0.12), (0.62, 0.3, 1, 0.1),
                                    (0.6, 0.12, -1, 0.1)]),
    'muscle': ((0.5, 0.38, 0.26), [(0.25, 0.32, 1, 0.13), (0.22, 0.22, -1, 0.12), (0.62, 0.32, 1, 0.1),
                                   (0.6, 0.15, -1, 0.1)]),
    'normal': ((0.36, 0.29, 0.22), [(0.25, 0.14, 1, 0.13), (0.62, 0.16, 1, 0.1)]),
    'female': ((0.31, 0.25, 0.19), [(0.25, 0.1, 1, 0.13), (0.6, 0.12, 1, 0.1)]),
    'thin': ((0.27, 0.22, 0.18), [(0.5, 0.1, 0, 0.05)]),
}
LEG = {
    'old': ((0.5, 0.3, 0.22), [(0.2, 0.1, 1, 0.15), (0.5, 0.16, 0, 0.04), (0.64, 0.1, -1, 0.08)]),
    'muscle': ((0.76, 0.44, 0.27), [(0.22, 0.18, 1, 0.16), (0.36, 0.14, -1, 0.1), (0.64, 0.3, -1, 0.09),
                                    (0.62, 0.2, 1, 0.08)]),
    'athletic': ((0.68, 0.4, 0.25), [(0.22, 0.14, 1, 0.16), (0.36, 0.1, -1, 0.1), (0.64, 0.28, -1, 0.09),
                                     (0.62, 0.18, 1, 0.08)]),
    'strong': ((0.72, 0.42, 0.27), [(0.22, 0.16, 1, 0.16), (0.64, 0.26, -1, 0.09), (0.62, 0.16, 1, 0.08)]),
    'normal': ((0.62, 0.38, 0.25), [(0.22, 0.1, 1, 0.16), (0.64, 0.18, -1, 0.09)]),
    'thin': ((0.46, 0.3, 0.21), [(0.5, 0.12, 0, 0.04), (0.64, 0.08, -1, 0.08)]),
}


TORSO = {   # ориентиры от основания шеи N: (x, y) в «головах», x масштабируется шириной плеч
    'muscle': [(0.36, -0.2), (0.7, 0.04), (1.0, 0.16), (1.18, 0.3), (1.3, 0.52), (1.31, 0.8), (1.17, 1.02),
               (1.0, 1.12), (0.98, 1.42), (0.9, 1.78), (0.78, 2.08), (0.8, 2.36), (0.84, 2.75)],
    'normal': [(0.32, -0.2), (0.64, 0.06), (0.92, 0.18), (1.08, 0.32), (1.16, 0.55), (1.14, 0.82), (1.02, 1.0),
               (0.9, 1.1), (0.88, 1.45), (0.82, 1.8), (0.74, 2.08), (0.78, 2.38), (0.82, 2.75)],
    'thin': [(0.28, -0.2), (0.58, 0.08), (0.86, 0.22), (1.0, 0.36), (1.04, 0.58), (1.0, 0.84), (0.9, 1.0),
             (0.8, 1.1), (0.76, 1.45), (0.72, 1.8), (0.66, 2.08), (0.72, 2.38), (0.76, 2.75)],
    'slim': [(0.26, -0.2), (0.54, 0.08), (0.8, 0.22), (0.93, 0.36), (0.98, 0.56), (0.94, 0.8), (0.84, 0.98),
             (0.76, 1.08), (0.78, 1.36), (0.7, 1.72), (0.6, 1.98), (0.74, 2.32), (0.82, 2.75)],
    'heavy': [(0.42, -0.2), (0.78, 0.04), (1.08, 0.18), (1.26, 0.34), (1.36, 0.6), (1.34, 0.86), (1.2, 1.06),
              (1.06, 1.16), (1.08, 1.5), (1.1, 1.86), (1.04, 2.1), (0.98, 2.38), (0.94, 2.75)],
}


def torso_outline(j, lk):
    u = j['u']
    nk = j['neck']
    b = lk['build'] if lk['build'] in TORSO else ('slim' if lk['female'] else 'normal')
    tab = TORSO[b]
    sw = j.get('sw', 1.0)
    shL, shR = j['shL'], j['shR']
    tilt = (shL[1] - shR[1]) / 2
    left = [(nk[0] + x * u * sw, nk[1] + y * u + tilt * min(1, y)) for x, y in tab]
    right = [(nk[0] - x * u * sw, nk[1] + y * u - tilt * min(1, y)) for x, y in tab]
    # низ торса — к тазу позы (сидя таз выше)
    hm = pp.lerp(j['hipL'], j['hipR'], 0.5)
    dy = hm[1] - (nk[1] + 2.55 * u)
    for arr in (left, right):
        for i in range(8, len(arr)):
            k = (i - 7) / (len(arr) - 7)
            arr[i] = (arr[i][0], arr[i][1] + dy * k)
    return left + right[::-1]


def hand_outline(wr, d, u, kind, side, old):
    """кисть «варежкой» + линии пальцев (детали отдельно)"""
    L = math.hypot(*d) or 1
    ux, uy = d[0] / L, d[1] / L
    nx, ny = -uy, ux
    sgn = 1 if side == 'L' else -1
    nx, ny = nx * sgn, ny * sgn
    s = u
    pw = s * (0.27 if old else 0.31)
    pl = s * 0.44
    fl = s * (0.42 if kind in ('relaxed', 'open', 'point') else 0.2)
    c0 = (wr[0] + ux * s * 0.02, wr[1] + uy * s * 0.02)

    def at(a, b):   # a — вдоль, b — поперёк (доли)
        return (c0[0] + ux * a + nx * b, c0[1] + uy * a + ny * b)
    if kind == 'fist':
        pts = [at(0, pw * 0.46), at(pl * 0.5, pw * 0.58), at(pl * 0.95, pw * 0.52), at(pl * 1.08, pw * 0.1),
               at(pl * 1.02, -pw * 0.45), at(pl * 0.5, -pw * 0.52), at(0, -pw * 0.42)]
        thumb = [at(pl * 0.3, pw * 0.5), at(pl * 0.7, pw * 0.62), at(pl * 0.92, pw * 0.2)]
        return pts, thumb, []
    spread = 0.35 if kind == 'open' else 0.0
    pts = [at(0, pw * 0.44), at(pl * 0.55, pw * 0.56), at(pl, pw * 0.56 + spread * pw),
           at(pl + fl * 0.92, pw * 0.4 + spread * pw * 1.4), at(pl + fl, pw * 0.1 + spread * pw * 0.5),
           at(pl + fl * 1.02, -pw * 0.15), at(pl + fl * 0.9, -pw * 0.45 - spread * pw),
           at(pl * 0.98, -pw * 0.52), at(pl * 0.5, -pw * 0.5), at(0, -pw * 0.42)]
    thumb = [at(pl * 0.2, -pw * 0.5), at(pl * 0.5, -pw * 0.78 - spread * pw), at(pl * 0.85, -pw * 0.82 - spread * pw * 1.5)]
    lines = []
    for k in range(3):
        b = pw * (0.3 - k * 0.27)
        lines.append([at(pl * 0.98, b), at(pl + fl * 0.95, b * (1 + spread * 1.4))])
    return pts, thumb, lines


# ── объём ──────────────────────────────────────────────────────────────────
def bbox(a, pad=0, thr=0.004):
    ys = np.flatnonzero(a.max(1) > thr)
    xs = np.flatnonzero(a.max(0) > thr)
    if not len(ys):
        return None
    h, w = a.shape
    return (max(0, ys[0] - pad), min(h, ys[-1] + pad + 1), max(0, xs[0] - pad), min(w, xs[-1] + pad + 1))


def _shade_small(a, color, rim, flat):
    inside = a > 0.5
    dist = ndimage.distance_transform_edt(inside).astype(np.float32)
    r = max(2.0, float(np.percentile(dist[inside], 97))) if inside.any() else 2.0
    h = np.sqrt(np.clip(dist / r, 0, 1))
    h = ndimage.gaussian_filter(h, max(1.5, r * 0.22))
    gy, gx = np.gradient(h)
    k = r * 0.85
    n = np.stack([-gx * k, -gy * k, 0.12 + h * 0.85], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6
    lam = np.clip(n @ LIGHT, 0, 1)
    lam = lam * (1 - flat) + 0.6 * flat
    rimv = np.clip(n[..., 0] * 0.85 - n[..., 1] * 0.25, 0, 1) ** 2.5 * rim
    spec = np.clip(n @ np.array([-0.3, -0.5, 0.81], np.float32), 0, 1) ** 24 * 0.18
    c = np.asarray(color, np.float32) / 255
    col = c * (AMB / np.maximum(c, 0.05) * 0.35 + 0.22 + 0.95 * lam[..., None]) + rimv[..., None] * RIM * 0.55 \
        + spec[..., None]
    return np.clip(col, 0, 1)


def shade_mask(a, color, rim=0.8, flat=0.0, scale=1.0):
    """маска 0..1 -> premultiplied RGBA с объёмом (считается в рамке формы, крупные формы — в половинном размере)"""
    out = np.zeros(a.shape + (4,), np.float32)
    bb = bbox(a, 4)
    if bb is None:
        return out
    y0, y1, x0, x1 = bb
    sub = a[y0:y1, x0:x1]
    big = min(sub.shape) > 60
    if big:
        small = sub[::2, ::2]
        col = _shade_small(small, color, rim, flat)
        col = np.repeat(np.repeat(col, 2, 0), 2, 1)[:sub.shape[0], :sub.shape[1]]
        col = ndimage.uniform_filter(col, (2, 2, 1))
    else:
        col = _shade_small(sub, color, rim, flat)
    out[y0:y1, x0:x1, :3] = col * sub[..., None]
    out[y0:y1, x0:x1, 3] = sub
    return out


def blur_fast(arr, s):
    """размытие премультиплированного слоя в рамке содержимого; большие сигмы — через уменьшение"""
    bb = bbox(arr[..., 3], int(s * 3) + 2)
    out = np.zeros_like(arr)
    if bb is None:
        return out
    y0, y1, x0, x1 = bb
    sub = arr[y0:y1, x0:x1]
    if s > 3:
        f = 2
        sm = sub[::f, ::f]
        sm = np.stack([ndimage.gaussian_filter(sm[..., i], s / f) for i in range(4)], -1)
        sm = np.repeat(np.repeat(sm, f, 0), f, 1)[:sub.shape[0], :sub.shape[1]]
        out[y0:y1, x0:x1] = sm
    else:
        out[y0:y1, x0:x1] = np.stack([ndimage.gaussian_filter(sub[..., i], s) for i in range(4)], -1)
    return out


class Layer:
    """холст размера фигуры: маска (cairo) -> numpy"""
    def __init__(self, w, h, ox, oy):
        self.w, self.h, self.ox, self.oy = w, h, ox, oy
        self.cv = kit.Canvas(w, h)
        self.ctx = self.cv.ctx
        self.ctx.translate(-ox, -oy)

    def alpha(self):
        return self.cv.premul()[..., 3]

    def rgba(self):
        return self.cv.premul()


def blurred(layer, s):
    a = layer.rgba()
    return kit.blur_premul(a, s)


# ── фигура ─────────────────────────────────────────────────────────────────
FRONT_ARMS = {'crossed': ('L', 'R'), 'reach': ('R',), 'slap': ('R',), 'hips': ()}
STUMP_FRONT = True


def render(j, lk, fc=None, box=None, back_arms=None, detail=1.0, extras=None):
    u = j['u']
    if back_arms is None:
        front = FRONT_ARMS.get(j.get('kind'), ())
        back_arms = tuple(s for s in ('L', 'R') if s not in front)
    xs = [v[0] for k, v in j.items() if isinstance(v, tuple)]
    ys = [v[1] for k, v in j.items() if isinstance(v, tuple)]
    if box is None:
        x0, y0 = int(min(xs) - u * 1.2), int(min(ys) - u * 1.4)
        w, h = int(max(xs) - x0 + u * 1.2), int(max(ys) - y0 + u * 0.8)
    else:
        x0, y0, w, h = box
    out = np.zeros((h, w, 4), np.float32)
    ink = Layer(w, h, x0, y0)       # тёмные анатомические линии (будут размыты)
    hil = Layer(w, h, x0, y0)       # блики
    sharp = Layer(w, h, x0, y0)     # чёткие мелочи поверх
    order = []
    order += [('leg', 'L'), ('leg', 'R')]
    order += [('arm', s) for s in back_arms]
    order += [('neck',), ('torso',), ('flush',), ('shorts',), ('top',)]
    order += [('arm', s) for s in ('L', 'R') if s not in back_arms]
    order += [('flush',), ('head',)]
    for part in order:
        if part[0] in ('leg', 'arm'):
            limb_part(out, j, lk, part[0], part[1], x0, y0, w, h, ink, hil, sharp)
        elif part[0] == 'torso':
            torso_part(out, j, lk, x0, y0, w, h, ink, hil, sharp)
        elif part[0] == 'neck':
            neck_part(out, j, lk, x0, y0, w, h)
        elif part[0] == 'shorts':
            shorts_part(out, j, lk, x0, y0, w, h)
        elif part[0] == 'top':
            top_part(out, j, lk, x0, y0, w, h)
        elif part[0] == 'flush':
            flush(out, ink, hil, u)
            kit.over(out, sharp.rgba())
            ink, hil, sharp = Layer(w, h, x0, y0), Layer(w, h, x0, y0), Layer(w, h, x0, y0)
        elif part[0] == 'head':
            head_part(out, j, lk, fc, x0, y0, w, h, ink, hil, sharp)
    flush(out, ink, hil, u)
    kit.over(out, sharp.rgba())
    if extras:
        ex = Layer(w, h, x0, y0)
        extras(ex.ctx)
        kit.over(out, ex.rgba())
    kit.texture(out, 0.08, max(3, int(u * 0.04)), seed=5, fine=0.05)
    return out, (x0, y0)


def flush(out, ink, hil, u):
    a = blur_fast(ink.rgba(), max(1.0, u * 0.012))
    al = a[..., 3:4] * (out[..., 3:4] > 0.01)
    out[..., :3] *= 1 - al * 0.9
    out[..., :3] += a[..., :3] * (out[..., 3:4] > 0.01) * 0.9
    b = blur_fast(hil.rgba(), max(1.5, u * 0.02))
    out[..., :3] += b[..., :3] * out[..., 3:4] * 0.5
    np.clip(out[..., :3], 0, out[..., 3:4], out=out[..., :3])


def comp_part(out, mask_layer, color, rim=0.8, flat=0.0):
    a = mask_layer.alpha()
    sh = shade_mask(a, color, rim, flat)
    kit.over(out, sh)
    return a


def neck_part(out, j, lk, x0, y0, w, h):
    u = j['u']
    m = Layer(w, h, x0, y0)
    nk, hd = j['neck'], j['head']
    nw = u * {'muscle': 0.78, 'heavy': 0.82, 'normal': 0.56, 'thin': 0.44, 'slim': 0.42}.get(lk['build'], 0.5)
    pts = chain_outline([(nk[0], nk[1] + u * 0.35), (hd[0], hd[1] + u * 0.3)], [nw * 1.15, nw])
    smooth_path(m.ctx, pts)
    fill(m.ctx, (255, 255, 255))
    comp_part(out, m, shade(lk['head'], 0.92), rim=0.5)
    # тень от подбородка
    s = Layer(w, h, x0, y0)
    ellipse(s.ctx, hd[0], hd[1] + u * 0.62, u * 0.42, u * 0.16)
    fill(s.ctx, (14, 20, 26), 0.55)
    a = blur_fast(s.rgba(), u * 0.06)
    a *= (out[..., 3:4] > 0.01)
    kit.over(out, a)


def limb_part(out, j, lk, which, side, x0, y0, w, h, ink, hil, sharp):
    u = j['u']
    spec = (lk['arms'] if which == 'arm' else lk['legs']).get(side)
    a, b, c = ((j['sh' + side], j['el' + side], j['wr' + side]) if which == 'arm'
               else (j['hip' + side], j['kn' + side], j['an' + side]))
    if spec is None:
        if which == 'arm':          # культя
            m = Layer(w, h, x0, y0)
            a = (a[0], a[1] - u * 0.25)
            e = pp.lerp(a, b, 0.1)
            pts = chain_outline([a, e], [u * 0.36, u * 0.3], [(1.0, 0.1, 0, 0.2)])
            smooth_path(m.ctx, pts)
            fill(m.ctx, (255, 255, 255))
            ellipse(m.ctx, e[0], e[1], u * 0.19, u * 0.13)
            fill(m.ctx, (255, 255, 255))
            comp_part(out, m, lk['torso'])
            pp.soft_line(ink.ctx, [(e[0] - u * 0.14, e[1] + u * 0.04), (e[0], e[1] + u * 0.1), (e[0] + u * 0.14, e[1] + u * 0.03)],
                         (40, 20, 14), u * 0.02, 0.7)
        return
    typ, col = spec
    widths, bul = (ARM if which == 'arm' else LEG)[typ]
    wsc = [v * u for v in widths]
    # нормаль «латеральная» должна смотреть наружу: для левой стороны фигуры (экран вправо) знак свой
    sgn = 1 if side == 'L' else -1
    bulges = [(t, amp, s * sgn * (1 if (b[1] - a[1]) >= 0 else -1), sg) for t, amp, s, sg in bul]
    pts = chain_outline([a, b, c], wsc, bulges)
    m = Layer(w, h, x0, y0)
    smooth_path(m.ctx, pts)
    fill(m.ctx, (255, 255, 255))
    old = typ == 'old'
    # кисть/стопа в ту же маску — единый объём
    d = (c[0] - b[0], c[1] - b[1])
    if which == 'arm':
        hk = lk.get('hand_' + side, 'relaxed')
        hpts, thumb, flines = hand_outline(c, d, u, hk, side, old)
        smooth_path(m.ctx, hpts)
        fill(m.ctx, (255, 255, 255))
        tw = u * 0.11
        pts_t = chain_outline(thumb, [tw * 1.2, tw, tw * 0.8])
        smooth_path(m.ctx, pts_t)
        fill(m.ctx, (255, 255, 255))
    else:
        fpts = foot_outline(c, u, side, j)
        smooth_path(m.ctx, fpts)
        fill(m.ctx, (255, 255, 255))
    comp_part(out, m, col, rim=0.9)
    ic, hc = ink.ctx, hil.ctx
    dk = shade(col, 0.35)
    # сустав: складки, «косточка»
    jd = (c[0] - a[0], c[1] - a[1])
    if old:
        pp.wrinkles(ic, b, jd, wsc[1], u, 6, dk, 0.55)
        pp.veins(sharp.ctx, pp.lerp(b, c, 0.1), c, wsc[1], u, seed=len(side) + (3 if which == 'leg' else 0))
        pp.spots(sharp.ctx, pp.lerp(a, b, 0.45 if which == 'leg' else 0.15), c, wsc[1], u,
                 seed=11 + len(side) + len(which), n=8)
        pp.wrinkles(ic, pp.lerp(a, b, 0.5), jd, wsc[0] * 0.9, u, 3, dk, 0.25)
    else:
        pp.soft_line(ic, [pp.lerp(a, b, 0.55), pp.lerp(a, b, 0.85)], dk, u * 0.03, 0.35)
        pp.soft_line(hc, [pp.lerp(a, b, 0.2), pp.lerp(a, b, 0.6)], (255, 230, 200), u * 0.05, 0.25)
    if which == 'leg':
        ellipse(hc, b[0] - u * 0.03, b[1] - u * 0.02, wsc[1] * 0.26, wsc[1] * 0.3)
        fill(hc, (255, 236, 210), 0.14)
        pp.soft_line(ic, [(b[0] - wsc[1] * 0.35, b[1] + wsc[1] * 0.35), (b[0], b[1] + wsc[1] * 0.5),
                          (b[0] + wsc[1] * 0.35, b[1] + wsc[1] * 0.35)], dk, u * 0.02, 0.5)
        foot_details(sharp.ctx, ic, c, u, side, col, lk.get('nails_black') and old, j)
    else:
        hand_details(sharp.ctx, ic, c, d, u, col, hk, side, old, flines, lk.get('finger_miss') and side == 'L')
        if lk.get('swollen_elbow') == side:
            swollen(sharp.ctx, pp.lerp(b, c, 0.05), u)
    if lk.get('ring_scars', True):
        pp.ring_scar(sharp.ctx, pp.lerp(a, b, 0.05 if which == 'arm' else 0.36), (b[0] - a[0], b[1] - a[1]),
                     wsc[0] * (1.0 if which == 'arm' else 0.82), u)


def swollen(ctx, p, u):
    g = rad(p[0], p[1], 0, u * 0.5, [(0, (150, 60, 110), 0.85), (0.5, (96, 62, 130), 0.75), (0.8, (130, 96, 120), 0.4),
                                     (1, (150, 110, 110), 0)])
    ellipse(ctx, p[0], p[1], u * 0.5, u * 0.42)
    ctx.set_source(g)
    ctx.fill()
    g = rad(p[0], p[1], 0, u * 0.32, [(0, (120, 80, 170), 0.95), (0.7, (86, 58, 128), 0.95), (1, (70, 46, 100), 0.9)],
            p[0] - u * 0.1, p[1] - u * 0.12)
    ellipse(ctx, p[0], p[1], u * 0.3, u * 0.27)
    ctx.set_source(g)
    ctx.fill()
    ellipse(ctx, p[0] - u * 0.1, p[1] - u * 0.1, u * 0.09, u * 0.05, -0.6)
    fill(ctx, (235, 215, 255), 0.4)
    for k in range(4):                     # лопнувшие сосудики
        a = k * 1.6 + 0.4
        ctx.move_to(p[0] + math.cos(a) * u * 0.22, p[1] + math.sin(a) * u * 0.2)
        ctx.line_to(p[0] + math.cos(a) * u * 0.36, p[1] + math.sin(a + 0.2) * u * 0.32)
        stroke(ctx, (130, 30, 50), u * 0.012, 0.6)


def foot_outline(an, u, side, j):
    dirx = 1 if side == 'L' else -1
    x, y = an
    s = u
    lying = j.get('kind') in ('sit_floor',)
    return [(x - s * 0.13, y - s * 0.08), (x + s * 0.13, y - s * 0.08), (x + s * 0.17 + dirx * s * 0.06, y + s * 0.12),
            (x + s * 0.2 + dirx * s * 0.08, y + s * 0.3), (x + dirx * s * 0.06, y + s * 0.36),
            (x - s * 0.18 + dirx * s * 0.06, y + s * 0.31), (x - s * 0.17 + dirx * s * 0.02, y + s * 0.12)]


def foot_details(sc, ic, an, u, side, col, black, j):
    dirx = 1 if side == 'L' else -1
    x, y = an
    for k in range(5):
        o = (k - 2) / 2 * dirx
        tx = x + dirx * s_(u, 0.06) + o * u * 0.15
        ty = y + u * 0.3 - abs(o) * u * 0.035
        if k < 4:
            pp.soft_line(ic, [(tx + dirx * u * 0.038, ty - u * 0.06), (tx + dirx * u * 0.038, ty + u * 0.04)],
                         shade(col, 0.35), u * 0.012, 0.6, smooth=False)
        r = u * (0.045 if k == (0 if dirx < 0 else 4) else 0.032)
        ellipse(sc, tx, ty, r * 0.75, r * 0.55)
        fill(sc, (26, 22, 24) if black else shade(col, 1.2), 0.9 if black else 0.45)
    for k in range(3):
        o = (k - 1) * u * 0.07
        pp.soft_line(ic, [(x + o * 0.6, y - u * 0.02), (x + dirx * u * 0.03 + o * 1.3, y + u * 0.22)],
                     shade(col, 0.45), u * 0.014, 0.35, smooth=False)
    pp.soft_line(ic, [(x - u * 0.12, y - u * 0.06), (x, y - u * 0.02), (x + u * 0.12, y - u * 0.06)], shade(col, 0.4),
                 u * 0.016, 0.4)


def s_(u, k):
    return u * k


def hand_details(sc, ic, c, d, u, col, kind, side, old, flines, finger_miss):
    dk = shade(col, 0.32)
    for ln in flines:
        pp.soft_line(ic, ln, dk, u * 0.014, 0.75, smooth=False)
    L = math.hypot(*d) or 1
    ux, uy = d[0] / L, d[1] / L
    nx, ny = -uy, ux
    if side == 'R':
        nx, ny = -nx, -ny
    pw = u * (0.27 if old else 0.31)
    pl = u * 0.44
    if kind in ('relaxed', 'open', 'point'):
        fl = u * 0.42
        spread = 0.35 if kind == 'open' else 0.0
        for k in range(4):                                   # ногти и костяшки
            b = pw * (0.42 - k * 0.27)
            q = (c[0] + ux * (pl + fl * 0.86) + nx * b * (1 + spread), c[1] + uy * (pl + fl * 0.86) + ny * b * (1 + spread))
            ellipse(sc, q[0], q[1], u * 0.03, u * 0.022, math.atan2(uy, ux))
            fill(sc, shade(col, 1.25), 0.45)
            kq = (c[0] + ux * pl * 1.02 + nx * b, c[1] + uy * pl * 1.02 + ny * b)
            pp.soft_line(ic, [(kq[0] - nx * u * 0.03, kq[1] - ny * u * 0.03), (kq[0] + nx * u * 0.03, kq[1] + ny * u * 0.03)],
                         dk, u * 0.012, 0.4, smooth=False)
            for m in (0.32, 0.6):                         # фаланги
                fq = (c[0] + ux * (pl + fl * m) + nx * b, c[1] + uy * (pl + fl * m) + ny * b)
                pp.soft_line(ic, [(fq[0] - nx * u * 0.025, fq[1] - ny * u * 0.025),
                                  (fq[0] + nx * u * 0.025, fq[1] + ny * u * 0.025)], dk, u * 0.008, 0.35, smooth=False)
        if finger_miss:     # нет крайней фаланги мизинца
            q = (c[0] + ux * (pl + fl * 0.78) - nx * pw * 0.42, c[1] + uy * (pl + fl * 0.78) - ny * pw * 0.42)
            ellipse(sc, q[0], q[1], u * 0.05, u * 0.06)
            fill(sc, (12, 14, 18), 1.0)
    else:
        for k in range(4):
            b = pw * (0.36 - k * 0.24)
            q = (c[0] + ux * pl * 1.0 + nx * b, c[1] + uy * pl * 1.0 + ny * b)
            ellipse(sc, q[0], q[1], u * 0.04, u * 0.035)
            fill(sc, shade(col, 1.15), 0.3)
            pp.soft_line(ic, [(q[0] + ux * u * 0.03, q[1] + uy * u * 0.03), (q[0] + ux * u * 0.12, q[1] + uy * u * 0.12)],
                         dk, u * 0.012, 0.6, smooth=False)
    if old:
        for k in range(3):
            o = (k - 1) * pw * 0.26
            pp.soft_line(ic, [(c[0] + nx * o * 0.5 + ux * u * 0.05, c[1] + ny * o * 0.5 + uy * u * 0.05),
                              (c[0] + ux * pl * 0.92 + nx * o, c[1] + uy * pl * 0.92 + ny * o)], dk, u * 0.012, 0.35,
                         smooth=False)


def torso_part(out, j, lk, x0, y0, w, h, ink, hil, sharp):
    u = j['u']
    col = lk['torso']
    m = Layer(w, h, x0, y0)
    pts = torso_outline(j, lk)
    smooth_path(m.ctx, pts)
    fill(m.ctx, (255, 255, 255))
    comp_part(out, m, col, rim=0.9)
    shL, shR, hL, hR, nk = j['shL'], j['shR'], j['hipL'], j['hipR'], j['neck']
    mid = (nk[0], nk[1] + u * 0.25)
    hm = pp.lerp(hL, hR, 0.5)
    sw = u * 1.02 * j.get('sw', 1.0)
    ic, hc = ink.ctx, hil.ctx
    dk = shade(col, 0.32)
    if lk['build'] == 'muscle':
        for sx in (1, -1):
            # грудные: тень снизу, блик сверху
            c = (mid[0] + sx * sw * 0.42, mid[1] + u * 0.72)
            pp.soft_line(ic, [(mid[0] + sx * u * 0.05, mid[1] + u * 0.35), (mid[0] + sx * u * 0.06, mid[1] + u * 1.15),
                              (c[0], mid[1] + u * 1.28), (c[0] + sx * sw * 0.34, mid[1] + u * 1.0),
                              (c[0] + sx * sw * 0.42, mid[1] + u * 0.6)], dk, u * 0.06, 0.55)
            ellipse(hc, c[0] - u * 0.1, c[1] - u * 0.2, sw * 0.28, u * 0.22)
            fill(hc, (255, 232, 200), 0.16)
            ellipse(sharp.ctx, c[0] + sx * u * 0.08, mid[1] + u * 1.0, u * 0.045, u * 0.04)
            fill(sharp.ctx, shade(col, 0.55), 0.75)
            # дельта: граница с грудной
            pp.soft_line(ic, [(c[0] + sx * sw * 0.42, mid[1] + u * 0.2), (c[0] + sx * sw * 0.48, mid[1] + u * 0.7)], dk,
                         u * 0.04, 0.4)
            # ключица
            pp.soft_line(ic, [(nk[0] + sx * u * 0.16, nk[1] + u * 0.3), (nk[0] + sx * u * 0.6, nk[1] + u * 0.24),
                              (nk[0] + sx * sw * 0.9, nk[1] + u * 0.2)], dk, u * 0.03, 0.4)
            pp.soft_line(hc, [(nk[0] + sx * u * 0.2, nk[1] + u * 0.22), (nk[0] + sx * sw * 0.8, nk[1] + u * 0.14)],
                         (255, 235, 210), u * 0.04, 0.35)
            # зубчатые
            for k in range(3):
                yy = mid[1] + u * (1.25 + k * 0.25)
                pp.soft_line(ic, [(mid[0] + sx * sw * 0.66, yy), (mid[0] + sx * sw * 0.76, yy + u * 0.1)], dk,
                             u * 0.03, 0.4)
        # пресс: кубики светлые, бороздки тёмные
        top_y, bot_y = mid[1] + u * 1.4, hm[1] - u * 0.1
        pp.soft_line(ic, [(mid[0], top_y - u * 0.1), (mid[0] + u * 0.01, bot_y)], dk, u * 0.04, 0.5)
        for k in range(3):
            yy = top_y + (bot_y - top_y) * (0.04 + k * 0.25)
            for sx in (1, -1):
                pp.soft_line(ic, [(mid[0] + sx * u * 0.05, yy), (mid[0] + sx * u * 0.25, yy + u * 0.05),
                                  (mid[0] + sx * u * 0.42, yy - u * 0.02)], dk, u * 0.035, 0.45)
                ellipse(hc, mid[0] + sx * u * 0.2, yy + u * 0.14, u * 0.12, u * 0.08)
                fill(hc, (255, 235, 210), 0.14)
        for sx in (1, -1):     # «косые» и паховая линия
            pp.soft_line(ic, [(mid[0] + sx * sw * 0.62, mid[1] + u * 2.0), (hm[0] + sx * u * 0.5, hm[1] - u * 0.25),
                              (hm[0] + sx * u * 0.22, hm[1] + u * 0.22)], dk, u * 0.04, 0.45)
        ellipse(sharp.ctx, hm[0], hm[1] - u * 0.45, u * 0.04, u * 0.06)
        fill(sharp.ctx, shade(col, 0.4), 0.8)
    elif lk['female']:
        for sx in (1, -1):
            c = (mid[0] + sx * sw * 0.36, mid[1] + u * 0.95)
            pp.soft_line(ic, [(c[0] - sx * u * 0.25, c[1] + u * 0.3), (c[0], c[1] + u * 0.38),
                              (c[0] + sx * u * 0.25, c[1] + u * 0.2)], dk, u * 0.05, 0.45)
            ellipse(hc, c[0] - u * 0.06, c[1] - u * 0.05, u * 0.22, u * 0.2)
            fill(hc, (255, 230, 200), 0.25)
            pp.soft_line(ic, [(nk[0] + sx * u * 0.12, nk[1] + u * 0.3), (nk[0] + sx * sw * 0.8, nk[1] + u * 0.2)], dk,
                         u * 0.025, 0.4)
    else:
        for k in range(5):
            for sx in (1, -1):
                yy = mid[1] + u * (0.9 + k * 0.24)
                pp.soft_line(ic, [(mid[0] + sx * u * 0.25, yy), (mid[0] + sx * sw * 0.55, yy + u * 0.1),
                                  (mid[0] + sx * sw * 0.72, yy + u * 0.06)], dk, u * 0.025, 0.4)
        for sx in (1, -1):
            pp.soft_line(ic, [(nk[0] + sx * u * 0.12, nk[1] + u * 0.3), (nk[0] + sx * sw * 0.85, nk[1] + u * 0.2)], dk,
                         u * 0.03, 0.55)
    if lk.get('dry', 0) > 0:
        r = random.Random(5)
        for _ in range(int(70 * lk['dry'])):
            x = mid[0] + (r.random() - 0.5) * sw * 1.4
            y = mid[1] + u * (0.4 + r.random() * 2.6)
            pp.soft_line(ic, [(x - u * 0.07, y), (x, y + u * 0.012), (x + u * 0.07, y)], dk, u * 0.008, 0.35)
    if lk.get('spine', 0) > 0:      # сутулость/искривление (№444): тень сбоку
        pp.soft_line(ic, [(mid[0] + sw * 0.6, mid[1] + u * 0.2), (mid[0] + sw * 0.75, mid[1] + u * 1.2),
                          (mid[0] + sw * 0.5, mid[1] + u * 2.2)], dk, u * 0.06, 0.4)
    # номер и штрихкод — татуировки, слегка размыты кожей
    if lk.get('number'):
        num_tattoo(sharp.ctx, j, lk, mid, sw)
    if lk.get('barcode'):
        pp.barcode(sharp.ctx, j)


def num_tattoo(ctx, j, lk, mid, sw):
    u = j['u']
    if lk['num_pos'] == 'collar':
        x, y, size = mid[0], mid[1] - u * 0.02, u * 0.2
    else:
        x, y, size = mid[0] + sw * 0.42, mid[1] + u * 0.62, u * 0.46
    ctx.save()
    ctx.select_font_face('DejaVu Sans', 0, 1)
    ctx.set_font_size(size)
    ext = ctx.text_extents(lk['number'])
    ctx.translate(x, y)
    ctx.rotate(-0.04)
    ctx.move_to(-ext.width / 2 - ext.x_bearing, ext.height / 2)
    ctx.text_path(lk['number'])
    ctx.set_source_rgba(0.08, 0.08, 0.1, 0.8)
    ctx.fill()
    ctx.restore()


def shorts_part(out, j, lk, x0, y0, w, h):
    u = j['u']
    col = lk['shorts']
    hL, hR, kL, kR = j['hipL'], j['hipR'], j['knL'], j['knR']
    m = Layer(w, h, x0, y0)
    tor = torso_outline(j, lk)
    n = len(tor) // 2
    wl, wr = tor[10], tor[len(tor) - 1 - 10]
    top = (wl[1] + wr[1]) / 2 + u * 0.06
    for hp, kn, sx in ((hL, kL, 1), (hR, kR, -1)):
        e = pp.lerp(hp, kn, 0.36)
        e = pp.lerp(hp, kn, 0.3)
        pts = chain_outline([(hp[0] + sx * u * 0.02, hp[1] - u * 0.1), e], [u * 0.86, u * 0.8])
        smooth_path(m.ctx, pts)
        fill(m.ctx, (255, 255, 255))
    pts = [(wl[0] + u * 0.04, top), (tor[12][0] + u * 0.08, tor[12][1]), (hL[0] + u * 0.52, hL[1] + u * 0.1),
           ((hL[0] + hR[0]) / 2, hL[1] + u * 0.42), (hR[0] - u * 0.52, hR[1] + u * 0.1),
           (tor[len(tor) - 13][0] - u * 0.08, tor[len(tor) - 13][1]), (wr[0] - u * 0.04, top)]
    smooth_path(m.ctx, pts, tension=0.3)
    fill(m.ctx, (255, 255, 255))
    a = m.alpha()
    sh = shade_mask(a, col, rim=0.5, flat=0.25)
    kit.over(out, sh)
    d = Layer(w, h, x0, y0)
    c = d.ctx
    xl, xr = wl[0] + u * 0.05, wr[0] - u * 0.05
    c.move_to(xr, top)
    c.curve_to(xr + (xl - xr) * 0.3, top + u * 0.05, xr + (xl - xr) * 0.7, top + u * 0.05, xl, top)
    c.line_to(xl + u * 0.01, top + u * 0.2)
    c.curve_to(xr + (xl - xr) * 0.7, top + u * 0.25, xr + (xl - xr) * 0.3, top + u * 0.25, xr - u * 0.01, top + u * 0.2)
    c.close_path()
    fill(c, shade(col, 0.7), 0.95)
    for k in range(12):
        x = xr + u * 0.04 + k * ((xl - xr) - u * 0.08) / 11
        c.move_to(x, top + u * 0.02)
        c.line_to(x, top + u * 0.2)
        stroke(c, shade(col, 0.45), u * 0.012, 0.6)
    for k in range(4):
        x = (hL[0] + hR[0]) / 2 + (k - 1.5) * u * 0.3
        pp.soft_line(c, [(x, top + u * 0.3), (x + u * 0.06, top + u * 0.55), (x - u * 0.03, top + u * 0.85)],
                     shade(col, 0.5), u * 0.025, 0.45)
    for hp, kn, sx in ((hL, kL, 1), (hR, kR, -1)):   # подвёрнутый край штанины
        e = pp.lerp(hp, kn, 0.3)
        pp.soft_line(c, [(e[0] - u * 0.36, e[1] - u * 0.04), (e[0], e[1] + u * 0.02), (e[0] + u * 0.36, e[1] - u * 0.04)],
                     shade(col, 0.4), u * 0.03, 0.6)
    if lk.get('pouch'):
        px, py = hR[0] - u * 0.05, top + u * 0.24
        kit.poly(c, [(px - u * 0.24, py), (px + u * 0.24, py), (px + u * 0.22, py + u * 0.4), (px - u * 0.22, py + u * 0.4)])
        fill(c, (84, 70, 52))
        c.rectangle(px - u * 0.25, py, u * 0.5, u * 0.13)
        fill(c, (60, 50, 38))
        for k in range(6):
            c.move_to(px - u * 0.2 + k * u * 0.08, py + u * 0.39)
            c.line_to(px - u * 0.18 + k * u * 0.08, py + u * 0.42)
            stroke(c, (34, 28, 22), u * 0.012, 0.9)
        pp.soft_line(c, [(px - u * 0.2, py + u * 0.25), (px + u * 0.2, py + u * 0.22)], (40, 32, 26), u * 0.012, 0.6)
    if lk.get('belt'):
        c.rectangle(xr, top - u * 0.03, xl - xr, u * 0.13)
        fill(c, (16, 16, 18))
        c.rectangle((hL[0] + hR[0]) / 2 - u * 0.1, top - u * 0.04, u * 0.2, u * 0.15)
        fill(c, (90, 92, 96))
        if lk['belt'] == 'baton':
            bx = hL[0] + u * 0.42
            pts = chain_outline([(bx, top + u * 0.02), (bx + u * 0.12, top + u * 1.5)], [u * 0.13, u * 0.11])
            smooth_path(c, pts)
            fill(c, (22, 22, 26))
            pp.soft_line(c, [(bx - u * 0.02, top + u * 0.2), (bx + u * 0.08, top + u * 1.3)], (120, 130, 150), u * 0.02, 0.4)
    kit.over(out, d.rgba() * (out[..., 3:4] > 0.01))


def top_part(out, j, lk, x0, y0, w, h):
    t = lk.get('top')
    if not t:
        return
    kind, col = t
    u = j['u']
    shL, shR, hL, hR, nk = j['shL'], j['shR'], j['hipL'], j['hipR'], j['neck']
    mid = (nk[0], nk[1] + u * 0.25)
    hm = pp.lerp(hL, hR, 0.5)
    sw = u * 1.02 * j.get('sw', 1.0)
    m = Layer(w, h, x0, y0)
    c = m.ctx
    if kind == 'tank':
        pts = [(nk[0] + u * 0.3, nk[1] - u * 0.02), (nk[0] + sw * 0.62, nk[1] + u * 0.08),
               (nk[0] + sw * 0.7, nk[1] + u * 0.3), (nk[0] + sw * 0.66, nk[1] + u * 0.85),
               (nk[0] + sw * 0.82, nk[1] + u * 1.2), (hm[0] + sw * 0.74, hm[1] - u * 0.1),
               (hm[0] - sw * 0.74, hm[1] - u * 0.1), (nk[0] - sw * 0.82, nk[1] + u * 1.2),
               (nk[0] - sw * 0.66, nk[1] + u * 0.85), (nk[0] - sw * 0.7, nk[1] + u * 0.3),
               (nk[0] - sw * 0.62, nk[1] + u * 0.08), (nk[0] - u * 0.3, nk[1] - u * 0.02),
               (nk[0] - u * 0.12, nk[1] + u * 0.42), (nk[0] + u * 0.12, nk[1] + u * 0.42)]
    else:
        pts = [(nk[0] + u * 0.34, nk[1]), (shL[0] + u * 0.12, shL[1] - u * 0.04), (shL[0] + u * 0.38, shL[1] + u * 0.85),
               (shL[0] - u * 0.06, shL[1] + u * 0.98), (mid[0] + sw * 0.86, mid[1] + u * 1.4),
               (hm[0] + sw * 0.84, hm[1] - u * 0.05), (hm[0] - sw * 0.84, hm[1] - u * 0.05),
               (mid[0] - sw * 0.86, mid[1] + u * 1.4), (shR[0] + u * 0.06, shR[1] + u * 0.98),
               (shR[0] - u * 0.38, shR[1] + u * 0.85), (shR[0] - u * 0.12, shR[1] - u * 0.04), (nk[0] - u * 0.34, nk[1]),
               (nk[0], nk[1] + u * 0.25)]
    smooth_path(c, pts, tension=0.35)
    fill(c, (255, 255, 255))
    a = m.alpha()
    sh = shade_mask(a, col, rim=0.25, flat=0.35)
    kit.over(out, sh)
    d = Layer(w, h, x0, y0)
    dc = d.ctx
    smooth_path(dc, pts, tension=0.35)
    stroke(dc, shade(col, 0.35), u * 0.02, 0.6)
    for k in range(5):
        x = mid[0] + (k - 2) * sw * 0.32
        pp.soft_line(dc, [(x, mid[1] + u * 1.35), (x + u * 0.1, mid[1] + u * 1.9), (x - u * 0.05, hm[1] - u * 0.3)],
                     shade(col, 0.55), u * 0.035, 0.4)
    r = random.Random(4)
    for _ in range(9):
        ellipse(dc, mid[0] + (r.random() - 0.5) * sw * 1.3, mid[1] + u * (0.7 + r.random() * 2.2),
                u * (0.05 + r.random() * 0.12), u * (0.04 + r.random() * 0.07), r.random())
        fill(dc, shade(col, 0.55), 0.22)
    if lk.get('number') and lk['num_pos'] == 'collar':
        num_tattoo(dc, j, lk, mid, sw)
    if lk.get('top_print'):
        lk['top_print'](dc, mid, u)
    kit.over(out, d.rgba())


def head_part(out, j, lk, fc, x0, y0, w, h, ink, hil, sharp):
    """голова: объём по маске + черты лица (people.head рисует их чётко, тени — мягко)"""
    u = j['u']
    m = Layer(w, h, x0, y0)
    fc2 = {**pp.face_default(), **(fc or {})}
    hw, hh = u * (0.5 if lk['female'] else 0.56), u * 0.68
    cx, cy = j['head']
    yaw = fc2['yaw']
    sh = yaw * hw * 0.18
    jaw = 0.82 if lk['female'] else 0.9
    c = m.ctx
    c.save()
    c.translate(cx, cy)
    c.rotate(j.get('head_tilt', 0.0))
    pts = [(-hw * 0.95 + sh, -hh * 0.35), (-hw * 0.88 + sh, -hh * 0.82), (sh * 0.5, -hh * 1.02),
           (hw * 0.88 + sh, -hh * 0.82), (hw * 0.95 + sh, -hh * 0.35), (hw * 0.9 * jaw + sh * 1.2, hh * 0.25),
           (hw * 0.55 + sh * 1.4, hh * 0.8), (sh * 1.6, hh * 0.98), (-hw * 0.55 + sh * 1.4, hh * 0.8),
           (-hw * 0.9 * jaw + sh * 1.2, hh * 0.25)]
    smooth_path(c, pts)
    fill(c, (255, 255, 255))
    c.restore()
    comp_part(out, m, lk['head'], rim=1.0)
    # черты лица (чёткий слой) — используем people.head без заливки черепа
    f = Layer(w, h, x0, y0)
    pp.head(f.ctx, j, {**lk, '_no_skull': True}, fc2)
    kit.over(out, f.rgba())
