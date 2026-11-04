"""Two fully 3D cutaway scenes, ray-traced analytically per pixel (numpy, deterministic):

A · «По Млечному Пути»: a dung ball rolls over night sand, leaving a track, under a starry sky with the Milky Way.
B · «По цене золота»: Manzoni's tin (label: author, weight, year, number — no rude word) turns on a dark
    reflective floor under warm gold light, gold glints falling.

    frame_a(u) / frame_b(u) -> float32 (1920, 1080, 3), u = seconds since the scene started.
"""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx

W, H = 1080, 1920


def _norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


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


@functools.lru_cache(None)
def dung_tex():
    a = _noise2(256, 21)
    b = _noise2(256, 23, 3)
    c = np.array([92, 58, 30], np.float32) * (0.65 + 0.6 * a)[..., None]
    c += np.clip((b - 0.6) * 3, 0, 1)[..., None] * np.array([30, 22, 8], np.float32)
    return c


R_BALL = 0.42


def ball_x(u):
    return -0.75 + 0.62 * u


def frame_a(u):
    with np.errstate(all='ignore'):
        return _frame_a(u)


def _frame_a(u):
    bx = ball_x(u)
    eye, d = _look((bx * 0.6 + 0.35, 0.34, 2.6 - 0.15 * u), (bx * 0.85, 1.0, -1.0), 62)
    C = np.array([bx, R_BALL, 0.0], np.float32)
    L = _norm(np.array([-0.5, 0.65, 0.45], np.float32))           # moonlight
    out = np.zeros(d.shape, np.float32)
    # --- sky
    lat = np.arcsin(np.clip(d[..., 1], -1, 1))
    lon = np.arctan2(d[..., 2], d[..., 0])
    sky = _tex(sky_tex(), (lon / (2 * np.pi)) % 1, 0.5 - lat / np.pi)
    out[:] = sky
    # --- ground (gentle dunes: height only shades, plane stays flat)
    hit_g = d[..., 1] < -1e-4
    tg = np.where(hit_g, -eye[1] / np.minimum(d[..., 1], -1e-4), np.inf)
    P = eye + d * tg[..., None]
    gx, gz = P[..., 0], P[..., 2]
    sand = _tex(sand_tex(), gx * 1.6, gz * 1.6) * (0.85 + 0.15 * _tex(sand_tex(), gx * 0.2 + 0.3, gz * 0.2))
    near = np.exp(-tg / 3.0)
    ripple = 0.5 + 0.5 * np.sin(gx * 14 + 2.0 * np.sin(gz * 2.3)) * near
    lam = np.full(gx.shape, float(L[1]), np.float32)
    # ball shadow on the ground (soft): distance of the ray to the ball along L
    q = P - C
    tq = np.sum(q * L, -1)
    dist = np.linalg.norm(q - tq[..., None] * L, axis=-1)
    shadow = np.where(tq < 0, np.clip((dist - R_BALL * 0.55) / (R_BALL * 0.9), 0, 1), 1.0)
    # rolled track behind the ball
    track = np.exp(-(gz / 0.16) ** 2) * (gx < bx) * np.clip((gx + 2.0) / 1.0, 0, 1)
    sand_rgb = np.array([150, 128, 104], np.float32) * sand[..., None] * (0.25 + 0.75 * lam * shadow)[..., None]
    sand_rgb *= (1 - 0.35 * track)[..., None]
    sand_rgb *= (0.9 + 0.1 * ripple)[..., None]
    fog = np.exp(-np.maximum(tg - 2.0, 0) / 9.0)[..., None]
    horizon = np.array([22, 24, 48], np.float32)
    ground = sand_rgb * fog + horizon * (1 - fog)
    out = np.where(hit_g[..., None], ground, out)
    # --- ball
    oc = eye - C
    b = np.sum(d * oc, -1)
    c = float(np.dot(oc, oc)) - R_BALL ** 2
    disc = b * b - c
    hit_b = disc > 0
    tb = np.where(hit_b, -b - np.sqrt(np.maximum(disc, 0)), np.inf)
    hit_b &= (tb > 0) & (tb < tg)
    Pb = eye + d * tb[..., None]
    Nb = (Pb - C) / R_BALL
    ang = -(bx + 0.75) / R_BALL                                     # rolling about z
    ca, sa = math.cos(ang), math.sin(ang)
    lx = Nb[..., 0] * ca - Nb[..., 1] * sa
    ly = Nb[..., 0] * sa + Nb[..., 1] * ca
    lz = Nb[..., 2]
    uu = (np.arctan2(lz, lx) / (2 * np.pi)) % 1
    vv = np.arccos(np.clip(ly, -1, 1)) / np.pi
    alb = _tex(dung_tex(), uu * 3, vv * 2)
    bump = (_tex(_noise2(256, 31)[..., None], uu * 5, vv * 3)[..., 0] - 0.5) * 0.5
    lamb = np.clip(np.sum(Nb * L, -1) + bump, 0, 1)
    rim = np.clip(1 - np.abs(np.sum(Nb * d, -1)), 0, 1) ** 3
    col = alb * (0.3 + 1.35 * lamb)[..., None] + rim[..., None] * np.array([70, 80, 140], np.float32)
    out = np.where(hit_b[..., None], col, out)
    return out


# ======================================================================= B · the tin
R_CAN, H_CAN = 0.5, 0.74


@functools.lru_cache(None)
def label_tex():
    """Wrap-around paper label: original Italian title, author, weight, numbering (no English swear word)."""
    w, h = 2400, 520
    im = Image.new('RGB', (w, h), (232, 222, 196))
    d = ImageDraw.Draw(im)
    for y in (26, h - 40):
        d.rectangle([0, y, w, y + 12], fill=(60, 52, 40))
    for k in range(2):
        x0 = k * w // 2
        d.text((x0 + w // 4, 150), 'PIERO MANZONI', font=fx.font('Heavy', 118), fill=(40, 34, 26), anchor='mm')
        d.text((x0 + w // 4, 270), 'contenuto netto gr 30 · conservata al naturale', font=fx.font('Medium', 44),
               fill=(70, 60, 46), anchor='mm')
        d.text((x0 + w // 4, 360), 'prodotta e inscatolata nel maggio 1961', font=fx.font('Semibold', 50),
               fill=(40, 34, 26), anchor='mm')
        d.text((x0 + w // 4, 440), 'N. 014', font=fx.font('Bold', 52), fill=(150, 40, 30), anchor='mm')
    a = np.asarray(im, np.float32) * (0.9 + 0.12 * _noise2(512, 41)[:, :, None][
        (np.arange(h)[:, None] * 512 // h) % 512, (np.arange(w)[None, :] * 512 // w) % 512])
    return a


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


def _can_hit(eye, d, ang):
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


def _shade_can(t, n, u, yh, rr, part, d, Lk, Lr):
    lab = _tex(label_tex(), u, 1 - np.clip((yh - 0.08) / (H_CAN - 0.16), 0, 0.999))
    in_label = (yh > 0.08) & (yh < H_CAN - 0.08)
    metal = np.array([200, 186, 150], np.float32)
    hv = _norm(Lk[None, None] - d)
    spec = np.clip(np.sum(n * hv, -1), 0, 1) ** 60
    lam = np.clip(np.sum(n * Lk, -1), 0, 1)
    rim = np.clip(np.sum(n * Lr, -1), 0, 1) ** 2
    # side
    side_alb = np.where(in_label[..., None], lab, metal * (0.7 + 0.3 * np.sin(yh * 220)[..., None] ** 2))
    side = side_alb * (0.22 + 0.85 * lam)[..., None] + (spec * (1 - 0.7 * in_label))[..., None] * 255 \
        + rim[..., None] * np.array([255, 190, 90], np.float32) * 0.6
    # top: concentric pressed rings, very shiny
    rings = 0.75 + 0.25 * np.cos(rr * 70) ** 2
    top = metal * rings[..., None] * (0.35 + 0.7 * lam)[..., None] + spec[..., None] * 255 * 1.3
    return np.where((part == 2)[..., None], top, side)


def frame_b(u):
    with np.errstate(all='ignore'):
        return _frame_b(u)


def _frame_b(u):
    ang = 0.9 * u - 0.4
    eye, d = _look((0.3 * math.sin(u * 0.6), 1.15, 3.6 - 0.25 * u), (0.0, 0.5, 0.0), 38)
    Lk = _norm(np.array([0.6, 0.7, 0.8], np.float32))
    Lr = _norm(np.array([-0.8, 0.3, -0.6], np.float32))
    out = bokeh_bg().copy()
    E = np.broadcast_to(eye, d.shape).astype(np.float32)
    t, n, uu, yh, rr, part = _can_hit(E, d, ang)
    hit = part > 0
    out = np.where(hit[..., None], _shade_can(t, n, uu, yh, rr, part, d, Lk, Lr), out)
    # floor y=0: dark lacquer with reflection of the tin and a soft contact shadow
    tf = np.where(d[..., 1] < -1e-4, -eye[1] / np.minimum(d[..., 1], -1e-4), np.inf)
    floor = (tf < t) & np.isfinite(tf)
    P = E + d * tf[..., None]
    rd = d * np.array([1, -1, 1], np.float32)
    t2, n2, u2, y2, r2, p2 = _can_hit(P, rd, ang)
    refl = _shade_can(t2, n2, u2, y2, r2, p2, rd, Lk, Lr) * 0.32
    dist = np.hypot(P[..., 0], P[..., 2])
    shadow = np.clip((dist - R_CAN * 0.9) / 0.5, 0, 1) * 0.7 + 0.3
    fl = np.array([28, 20, 12], np.float32) * shadow[..., None] + (bokeh_bg() * 0.18) * np.exp(-tf / 4)[..., None]
    fl = np.where((p2 > 0)[..., None], fl * 0.5 + refl, fl)
    out = np.where(floor[..., None], fl, out)
    return out
