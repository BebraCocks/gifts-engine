"""Two fully 3D cutaway scenes, ray-traced analytically per pixel (numpy, deterministic). Only the chosen
Telegram NFT models appear (live Lottie, placed as camera-facing cards in the 3D space) — no realistic objects:

A · «По Млечному Пути»: the Dung Beetle model stands on night sand under the Milky Way; the camera orbits it.
B · «По цене золота»: the Art Supplies model stands on a dark pedestal with gold trim over a lacquer floor
    (reflections), gold glints falling.

    frame_a(t, u) / frame_b(t, u) -> float32 (1920, 1080, 3); t = content time (Lottie phase), u = scene time.
"""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx
import gifts_api as G
import lottie

W, H = 1080, 1920


def _norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def project(eye, target, fov, p, cy=0.40):
    """World point -> (x, y) px, depth; same camera as _look."""
    eye, target, p = (np.asarray(v, np.float32) for v in (eye, target, p))
    f = _norm(target - eye)
    r = _norm(np.cross(f, [0, 1, 0]))
    up = np.cross(r, f)
    q = p - eye
    z = float(np.dot(q, f))
    t = math.tan(math.radians(fov) / 2)
    x = W / 2 + float(np.dot(q, r)) / z / t * (H / 2)
    y = H * cy - float(np.dot(q, up)) / z / t * (H / 2)
    return x, y, z


def sprite(canvas, eye, target, fov, base, height, img, alpha=1.0, flip=False, mask=None):
    """Draw an RGBA model card standing at world point `base`, `height` metres tall, facing the camera."""
    x0, y0, z = project(eye, target, fov, base)
    x1, y1, _ = project(eye, target, fov, np.asarray(base) + (0, height, 0))
    if z <= 0.1:
        return
    hp = abs(y0 - y1) / 0.9                                 # the model fills ~90 % of its Lottie frame
    im = img.resize((max(2, int(hp)), max(2, int(hp))), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    a = np.asarray(im, np.float32)
    s = a.shape[0]
    X = int(x0 - s / 2)
    Y = int(y0 - s * 0.95) if not flip else int(y0 - s * 0.05)
    xa, ya, xb, yb = max(X, 0), max(Y, 0), min(X + s, W), min(Y + s, H)
    if xb <= xa or yb <= ya:
        return
    piece = a[ya - Y:yb - Y, xa - X:xb - X]
    al = piece[..., 3:4] / 255 * alpha
    if mask is not None:
        al = al * mask[ya:yb, xa:xb, None]
    reg = canvas[ya:yb, xa:xb]
    reg[:] = reg * (1 - al) + piece[..., :3] * al


def _look(eye, target, fov, cy=0.40):
    eye, target = np.asarray(eye, np.float32), np.asarray(target, np.float32)
    f = _norm(target - eye)
    r = _norm(np.cross(f, [0, 1, 0]))
    up = np.cross(r, f)
    t = math.tan(math.radians(fov) / 2)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    px = (xs + 0.5 - W / 2) / (H / 2) * t
    py = -(ys + 0.5 - H * cy) / (H / 2) * t
    d = f[None, None] + px[..., None] * r[None, None] + py[..., None] * up[None, None]
    return eye, _norm(d).astype(np.float32)


def _noise2(n, seed, octaves=5):
    """Seamlessly tiling fractal noise (random-phase spectrum, ~1/f), 0..1. `octaves` sets the finest detail."""
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None] * n
    fx_ = np.fft.rfftfreq(n)[None, :] * n
    f = np.sqrt(fx_ ** 2 + fy ** 2)
    amp = np.where(f > 0, 1.0 / np.maximum(f, 1) ** 1.6, 0) * (f < 4 * 2 ** octaves)
    spec = amp * np.exp(2j * np.pi * rng.random(amp.shape))
    out = np.fft.irfft2(spec, s=(n, n)).astype(np.float32)
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


def _tex(tex, u, v):
    """Bilinear sample with wrap; u, v in texture repeats (any real value)."""
    h, w = tex.shape[:2]
    u = np.nan_to_num(u) * w - 0.5
    v = np.nan_to_num(v) * h - 0.5
    x0, y0 = np.floor(u), np.floor(v)
    fx_, fy_ = u - x0, v - y0
    x0, y0 = x0.astype(np.int64) % w, y0.astype(np.int64) % h
    x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    if tex.ndim == 3:
        fx_, fy_ = fx_[..., None], fy_[..., None]
    a = tex[y0, x0] * (1 - fx_) + tex[y0, x1] * fx_
    b = tex[y1, x0] * (1 - fx_) + tex[y1, x1] * fx_
    return a * (1 - fy_) + b * fy_


# ======================================================================= A · Milky Way
@functools.lru_cache(None)
def sky_tex():
    """Equirectangular night sky (2048 x 1024): gradient, Milky Way band with dust lanes, stars."""
    w, h = 2048, 1024
    rng = np.random.default_rng(1897)
    lon = (np.arange(w) + 0.5) / w * 2 * np.pi
    lat = np.pi / 2 - (np.arange(h) + 0.5) / h * np.pi
    LON, LAT = np.meshgrid(lon, lat)
    d = np.stack([np.cos(LAT) * np.cos(LON), np.sin(LAT), np.cos(LAT) * np.sin(LON)], -1)
    n = _norm(np.array([1.0, 0.3, 0.35]))
    band = np.exp(-(d @ n / 0.16) ** 2)
    nz = _noise2(512, 4)[(LAT * 300).astype(int) % 512, (LON * 160).astype(int) % 512]
    dust = _noise2(512, 9)[(LAT * 520).astype(int) % 512, (LON * 260).astype(int) % 512]
    glow = band * (0.45 + 0.8 * nz) * (1 - 0.65 * np.clip((dust - 0.45) * 3, 0, 1) * band)
    base = np.array([6, 9, 26], np.float32) + np.clip(1 - LAT[..., None] * 1.6, 0, 1) * np.array([16, 20, 44], np.float32)
    col = base + glow[..., None] * np.array([70, 72, 100], np.float32) + (band ** 3)[..., None] * np.array([34, 22, 14])
    k = 9000
    sx, sy = rng.integers(0, w, k), rng.integers(0, h // 2 + 80, k)
    near = rng.random(k) < 0.25 + 0.75 * band[sy, sx]
    br = (rng.random(k) ** 4 * 230 + 25)[:, None] * np.array([[1.0, 0.97, 0.9]])
    col[sy[near], sx[near]] = np.maximum(col[sy[near], sx[near]], br[near])
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    return np.asarray(im, np.float32) * 1.1


@functools.lru_cache(None)
def sand_tex():
    a = _noise2(512, 13)
    b = _noise2(512, 17, 3)
    return (0.75 + 0.35 * a + 0.15 * b).astype(np.float32)


BEETLE = None


def _beetle():
    global BEETLE
    if BEETLE is None:
        BEETLE = str(G.model_file('Happy Brownie', 'Dung Beetle', 'json'))
    return BEETLE


def frame_a(t, u):
    with np.errstate(all='ignore'):
        return _frame_a(t, u)


def _frame_a(t, u):
    ang = -0.42 + 0.36 * u                                      # slow orbit around the model
    eye = (3.1 * math.sin(ang), 0.45, 3.1 * math.cos(ang))
    target = (0.0, 0.62, 0.0)
    fov = 58
    eye, d = _look(eye, target, fov)
    L = _norm(np.array([-0.5, 0.65, 0.45], np.float32))
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))
    lon = np.arctan2(d[..., 2], d[..., 0])
    out = _tex(sky_tex(), (lon / (2 * np.pi)) % 1, 0.5 - lat / np.pi)
    hit_g = d[..., 1] < -1e-4
    tg = np.where(hit_g, -eye[1] / np.minimum(d[..., 1], -1e-4), np.inf)
    P = eye + d * tg[..., None]
    gx, gz = P[..., 0], P[..., 2]
    sand = _tex(sand_tex(), gx * 1.6, gz * 1.6) * (0.85 + 0.15 * _tex(sand_tex(), gx * 0.2 + 0.3, gz * 0.2))
    near = np.exp(-tg / 3.0)
    ripple = 0.5 + 0.5 * np.sin(gx * 14 + 2.0 * np.sin(gz * 2.3)) * near
    shadow = 0.45 + 0.55 * np.clip((np.hypot(gx / 0.55, gz / 0.35) - 0.4) / 0.7, 0, 1)   # soft contact shadow
    sand_rgb = np.array([150, 128, 104], np.float32) * sand[..., None] * (0.25 + 0.75 * float(L[1]) * shadow)[..., None]
    sand_rgb *= (0.9 + 0.1 * ripple)[..., None]
    fog = np.exp(-np.maximum(tg - 2.0, 0) / 9.0)[..., None]
    ground = sand_rgb * fog + np.array([22, 24, 48], np.float32) * (1 - fog)
    out = np.where(hit_g[..., None], ground, out).astype(np.float32)
    img = lottie.frame(_beetle(), t, size=900)
    # moon rim: a cool glow behind the model
    x, y, _ = project(eye, target, fov, (0, 0.4, 0))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    out += (np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 330 ** 2)) * 0.35)[..., None] * np.array([120, 130, 200], np.float32)
    sprite(out, eye, target, fov, (0, 0.0, 0), 0.92, img)
    return out


# ======================================================================= B · the tin
@functools.lru_cache(None)
def bokeh_bg():
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg = np.array([14, 10, 6], np.float32) + np.clip(1 - np.hypot((xx - W / 2) / W, (yy - 700) / H) * 1.6, 0, 1)[..., None] \
        * np.array([70, 48, 16], np.float32)
    for _ in range(26):
        cx, cy, r = rng.uniform(0, W), rng.uniform(150, 1100), rng.uniform(30, 110)
        a = rng.uniform(0.08, 0.25)
        m = np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1) ** 0.6
        bg += m[..., None] * a * np.array([255, 190, 90], np.float32)
    return bg


def _can_hit(eye, d, ang, R_CAN=0.55, H_CAN=0.5):
    """Ray vs vertical tin (axis y, base on y=0), rotated by ang about y. -> t, normal, u (label), part (1 side, 2 top)."""
    ca, sa = math.cos(ang), math.sin(ang)
    ox, oz = eye[..., 0] * ca + eye[..., 2] * sa, -eye[..., 0] * sa + eye[..., 2] * ca
    dx, dz = d[..., 0] * ca + d[..., 2] * sa, -d[..., 0] * sa + d[..., 2] * ca
    oy, dy = eye[..., 1], d[..., 1]
    A = dx * dx + dz * dz
    B = ox * dx + oz * dz
    Cc = ox * ox + oz * oz - R_CAN ** 2
    disc = B * B - A * Cc
    ok = (disc > 0) & (A > 1e-8)
    t1 = np.where(ok, (-B - np.sqrt(np.maximum(disc, 0))) / np.maximum(A, 1e-8), np.inf)
    y1 = oy + dy * t1
    side = ok & (t1 > 0) & (y1 > 0) & (y1 < H_CAN)
    t_side = np.where(side, t1, np.inf)
    tt = np.where(np.abs(dy) > 1e-6, (H_CAN - oy) / np.where(np.abs(dy) > 1e-6, dy, 1), np.inf)
    xt, zt = ox + dx * tt, oz + dz * tt
    top = (tt > 0) & (xt * xt + zt * zt < R_CAN ** 2)
    t_top = np.where(top, tt, np.inf)
    t = np.minimum(t_side, t_top)
    part = np.where(t_side <= t_top, 1, 2) * np.isfinite(t)
    hx, hz = ox + dx * t, oz + dz * t
    u = (-np.arctan2(hz, hx) / (2 * np.pi)) % 1
    nl = np.stack([hx, np.zeros_like(hx), hz], -1) / R_CAN
    nw = np.stack([nl[..., 0] * ca - nl[..., 2] * sa, np.zeros_like(hx), nl[..., 0] * sa + nl[..., 2] * ca], -1)
    n = np.where((part == 2)[..., None], np.array([0, 1, 0], np.float32), nw)
    yh = oy + dy * t
    rr = np.sqrt(hx * hx + hz * hz)
    return t, n, u, yh, rr, part


def _shade_pedestal(t, n, yh, rr, part, d, Lk, Lr, H_P=0.5):
    """Black marble pedestal with a gold band at the top."""
    hv = _norm(Lk[None, None] - d)
    spec = np.clip(np.sum(n * hv, -1), 0, 1) ** 50
    lam = np.clip(np.sum(n * Lk, -1), 0, 1)
    rim = np.clip(np.sum(n * Lr, -1), 0, 1) ** 2
    band = (yh > H_P - 0.07) & (part == 1)
    base = np.where(band[..., None], np.array([200, 150, 60], np.float32), np.array([26, 22, 24], np.float32))
    col = base * (0.35 + 0.9 * lam)[..., None] + spec[..., None] * np.where(band, 255, 120)[..., None] \
        + rim[..., None] * np.array([255, 190, 90], np.float32) * 0.5
    top = np.array([34, 28, 30], np.float32) * (0.5 + 0.6 * lam)[..., None] + spec[..., None] * 160
    return np.where((part == 2)[..., None], top, col)


ART = None


def _art():
    global ART
    if ART is None:
        ART = str(G.model_file('Happy Brownie', 'Art Supplies', 'json'))
    return ART


def frame_b(t, u):
    with np.errstate(all='ignore'):
        return _frame_b(t, u)


def _frame_b(t, u):
    ang = 0.0
    eye = (0.35 * math.sin(u * 0.7 - 0.6), 1.1, 3.9 - 0.2 * u)
    target = (0.0, 0.8, 0.0)
    fov = 40
    eye, d = _look(eye, target, fov)
    Lk = _norm(np.array([0.6, 0.7, 0.8], np.float32))
    Lr = _norm(np.array([-0.8, 0.3, -0.6], np.float32))
    out = bokeh_bg().copy()
    E = np.broadcast_to(eye, d.shape).astype(np.float32)
    t1, n, uu, yh, rr, part = _can_hit(E, d, ang)
    ped = part > 0
    out = np.where(ped[..., None], _shade_pedestal(t1, n, yh, rr, part, d, Lk, Lr), out)
    tf = np.where(d[..., 1] < -1e-4, -eye[1] / np.minimum(d[..., 1], -1e-4), np.inf)
    floor = (tf < t1) & np.isfinite(tf)
    P = E + d * tf[..., None]
    rd = d * np.array([1, -1, 1], np.float32)
    t2, n2, u2, y2, r2, p2 = _can_hit(P, rd, ang)
    refl = _shade_pedestal(t2, n2, y2, r2, p2, rd, Lk, Lr) * 0.35
    dist = np.hypot(P[..., 0], P[..., 2])
    shadow = np.clip((dist - 0.5) / 0.5, 0, 1) * 0.7 + 0.3
    fl = np.array([28, 20, 12], np.float32) * shadow[..., None] + (bokeh_bg() * 0.18) * np.exp(-tf / 4)[..., None]
    fl = np.where((p2 > 0)[..., None], fl * 0.5 + refl, fl)
    out = np.where(floor[..., None], fl, out).astype(np.float32)
    img = lottie.frame(_art(), t, size=900)
    free_floor = (floor & ~(p2 > 0)).astype(np.float32)
    sprite(out, eye, target, fov, (0, 0.5, 0), 0.62, img)
    sprite(out, eye, target, fov, (0, -0.5, 0), 0.62, img, alpha=0.22, flip=True, mask=free_floor)
    return out
