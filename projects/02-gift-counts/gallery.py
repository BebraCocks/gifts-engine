"""«Ночная галерея графа»: a ray-cast castle corridor + perspective portrait planes.

World: x right, y up, z toward the viewer (metres). The corridor is a box x∈[-HALF, HALF],
y∈[0, CEIL], z∈[Z_END, Z_START]. Environment is ray-cast per pixel at half resolution
(deterministic, a function of camera + time only); portraits are textured quads drawn
with an exact homography on top (they lie on the walls, so a convex room never occludes them).
"""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
FOV = 60.0                                   # vertical
F = (H / 2) / math.tan(math.radians(FOV) / 2)
SCALE = 2                                    # environment is ray-cast at W/SCALE x H/SCALE
HALF, CEIL = 3.0, 5.2
Z_START, Z_END = 6.0, -92.0
EYE = 2.05

FOG = np.array([5, 3, 7], np.float32)
FLAME = np.array([1.0, 0.66, 0.36], np.float32)


# ------------------------------------------------------------------ camera
def rot(yaw, pitch=0.0):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    return Ry @ Rx                             # camera -> world; forward = R @ (0, 0, -1)


class Cam:
    def __init__(self, pos, yaw, pitch=0.0, roll_px=(0.0, 0.0)):
        self.p = np.asarray(pos, float)
        self.R = rot(yaw, pitch)
        self.shift = roll_px                   # screen-space shake (px)

    def project(self, pts):
        """pts (n,3) world -> (n,2) screen px, (n,) depth."""
        q = (np.asarray(pts, float) - self.p) @ self.R        # world -> camera (R orthonormal)
        z = -q[:, 2]
        zs = np.where(z > 1e-4, z, 1e-4)
        x = W / 2 + F * q[:, 0] / zs + self.shift[0]
        y = H / 2 - F * q[:, 1] / zs + self.shift[1]
        return np.stack([x, y], 1), z


# ------------------------------------------------------------------ procedural textures (built once)
def _noise(n, seed, octaves=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        k = 4 * 2 ** o
        g = rng.random((k, k)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)
        g = np.asarray(im, np.float32) / 255
        # make it tile: blend with rolled copy
        out += amp * g
        tot += amp
        amp *= 0.5
    out /= tot
    return (out - out.min()) / (out.max() - out.min() + 1e-6)


@functools.lru_cache(None)
def damask(n=256):
    """Seamless damask tile (n x n = 1 m x 1 m): plum ground, lighter ornament."""
    S = 2
    im = Image.new('L', (n * S, n * S), 0)
    d = ImageDraw.Draw(im)
    c = n * S
    for ox, oy in ((0, 0), (c, 0), (0, c), (c, c), (c / 2, c / 2)):
        # medallion: stacked ellipses + leaves
        for k, (rx, ry) in enumerate(((0.16, 0.30), (0.10, 0.20), (0.05, 0.10))):
            box = [ox - rx * c, oy - ry * c, ox + rx * c, oy + ry * c]
            d.ellipse(box, fill=255 if k % 2 == 0 else 0)
        for sgn in (-1, 1):
            d.ellipse([ox + sgn * 0.12 * c - 0.08 * c, oy - 0.05 * c, ox + sgn * 0.12 * c + 0.08 * c, oy + 0.05 * c],
                      fill=200)
    for x in (c / 2, 0, c):                           # thin diamond lattice
        for y in (0, c / 2, c):
            d.line([(x - c / 2, y), (x, y - c / 2)], fill=120, width=3 * S)
    im = im.resize((n, n), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    a = np.asarray(im, np.float32) / 255
    base = np.array([40, 19, 34], np.float32)
    orn = np.array([58, 29, 47], np.float32)
    nz = _noise(n, 7)[..., None]
    return base * (0.9 + 0.2 * nz) * (1 - a[..., None]) + orn * (0.9 + 0.2 * nz) * a[..., None]


@functools.lru_cache(None)
def marble(n=256):
    nz = _noise(n, 3, 5)
    veins = np.abs(np.sin((nz * 9 + np.linspace(0, 6, n)[None, :]) * math.pi))
    v = 1 - np.clip(veins * 4, 0, 1)
    return (0.85 + 0.15 * nz + 0.35 * v).astype(np.float32)


def _sample(tex, u, v):
    """Nearest sample of a tiling texture; u, v in texels."""
    n = tex.shape[0]
    return tex[(v.astype(np.int64) % n), (u.astype(np.int64) % n)]


# ------------------------------------------------------------------ lights
def sconces():
    """Candle sconces on both walls every 5 m, skipping portrait positions. -> list of (x, y, z)."""
    import config
    taken = [(h['wall'], h['z']) for h in config.HEROES if h['wall'] != 'E'] + \
            [('L' if k % 2 == 0 else 'R', -8.0 - 5 * k) for k in range(7)]
    out = []
    for j in range(20):
        z = 2.5 - 5.0 * j
        if z < Z_END + 1.5:
            break
        for wall, x in (('L', -HALF + 0.18), ('R', HALF - 0.18)):
            if any(w == wall and abs(z - zp) < 1.3 for w, zp in taken):
                z2 = z - 2.5
            else:
                z2 = z
            out.append((x, 3.15, z2))
    out.append((-1.9, 3.2, Z_END + 0.18))
    out.append((1.9, 3.2, Z_END + 0.18))
    return out


SCONCES = sconces()


def flicker(k, t):
    return 1.0 + 0.07 * math.sin(t * 11.3 + k * 1.7) + 0.05 * math.sin(t * 23.1 + k * 4.1) \
        + 0.04 * math.sin(t * 5.3 + k * 0.6)


# ------------------------------------------------------------------ environment ray cast
@functools.lru_cache(None)
def _rays():
    w, h = W // SCALE, H // SCALE
    f = F / SCALE
    xs = (np.arange(w) + 0.5 - w / 2) / f
    ys = -(np.arange(h) + 0.5 - h / 2) / f
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, Y, -np.ones_like(X)], -1)
    return (d / np.linalg.norm(d, axis=-1, keepdims=True)).astype(np.float32)


def environment(cam, t, lamps=()):
    """-> float32 (H, W, 3) 0..255 upscaled environment. lamps: [(pos, intensity)] extra point lights."""
    d = _rays() @ cam.R.T.astype(np.float32)                 # world directions (h, w, 3)
    sx, sy = cam.shift
    o = cam.p.astype(np.float32)
    dx, dy, dz = d[..., 0], d[..., 1], d[..., 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        tx = np.where(dx > 0, (HALF - o[0]) / dx, (-HALF - o[0]) / dx)
        ty = np.where(dy > 0, (CEIL - o[1]) / dy, (0 - o[1]) / dy)
        tz = np.where(dz > 0, (Z_START - o[2]) / dz, (Z_END - o[2]) / dz)
    tx = np.where(np.isfinite(tx) & (tx > 0), tx, np.inf)
    ty = np.where(np.isfinite(ty) & (ty > 0), ty, np.inf)
    tz = np.where(np.isfinite(tz) & (tz > 0), tz, np.inf)
    tt = np.minimum(np.minimum(tx, ty), tz)
    hit = o + d * tt[..., None]
    side = (tx <= ty) & (tx <= tz)
    flat = ~side & (ty <= tz)
    floor = flat & (dy < 0)
    ceil = flat & (dy >= 0)
    endw = ~side & ~flat

    col = np.zeros(d.shape, np.float32)
    nrm = np.zeros(d.shape, np.float32)
    # ---- walls (side + end share the look; u along the wall, v = height)
    wall = side | endw
    u = np.where(side, hit[..., 2], hit[..., 0])
    v = hit[..., 1]
    dam = _sample(damask(), u * 256 / 1.0, (CEIL - v) * 256 / 1.0)
    wains = np.array([24, 13, 17], np.float32) * (0.85 + 0.3 * (np.abs(((u / 1.25) % 1) - 0.5) > 0.47)[..., None])
    wc = np.where((v < 1.1)[..., None], wains, dam)
    rail = ((v > 1.1) & (v < 1.17)) | ((v > 4.5) & (v < 4.6))
    wc = np.where(rail[..., None], np.array([120, 84, 38], np.float32), wc)
    wc = np.where((v >= 4.6)[..., None], np.array([18, 10, 15], np.float32), wc)
    col = np.where(wall[..., None], wc, col)
    nrm[side] = np.stack([-np.sign(dx[side]), np.zeros_like(dx[side]), np.zeros_like(dx[side])], -1)
    nrm[endw] = np.stack([np.zeros_like(dz[endw]), np.zeros_like(dz[endw]), -np.sign(dz[endw])], -1)
    # ---- floor: dark marble checker
    fx_, fz_ = hit[..., 0], hit[..., 2]
    chk = ((np.floor(fx_ / 1.0) + np.floor(fz_ / 1.0)) % 2).astype(np.float32)
    mar = _sample(marble(), fx_ * 128, fz_ * 128)
    fc = (np.array([34, 25, 31], np.float32) * (1 - chk[..., None]) +
          np.array([13, 9, 13], np.float32) * chk[..., None]) * mar[..., None]
    col = np.where(floor[..., None], fc, col)
    nrm[floor] = (0, 1, 0)
    # ---- ceiling: beams every 4 m
    beam = (np.abs(((hit[..., 2] / 4.0) % 1) - 0.5) > 0.42)
    cc = np.where(beam[..., None], np.array([26, 16, 14], np.float32), np.array([13, 8, 12], np.float32))
    col = np.where(ceil[..., None], cc, col)
    nrm[ceil] = (0, -1, 0)

    # ---- lighting: ambient + nearest candles + extra lamps
    light = np.full(tt.shape + (3,), 0.27, np.float32)
    spec = np.zeros(tt.shape + (3,), np.float32)
    near = sorted(range(len(SCONCES)), key=lambda k: abs(SCONCES[k][2] - (cam.p[2] - 6)))[:10]
    srcs = [(np.array(SCONCES[k], np.float32), 3.3 * flicker(k, t), FLAME) for k in near]
    srcs += [(np.asarray(p, np.float32), i, np.array(c, np.float32)) for p, i, c in lamps if i > 0.01]
    r_ = np.stack([dx, np.where(floor, -dy, dy), dz], -1)          # mirror dir on the floor
    for p, inten, rgb in srcs:
        L = p - hit
        dist2 = np.sum(L * L, -1)
        Ln = L / np.sqrt(dist2)[..., None]
        lam = np.clip(np.sum(nrm * Ln, -1), 0, 1)
        att = inten / (1.0 + dist2 / 2.2)
        light += (lam * att)[..., None] * rgb
        al = np.clip(np.sum(r_ * Ln, -1), 0, 1)
        spec += (floor * al ** 90 * inten * 1.6 / (1 + dist2 / 30))[..., None] * rgb
    out = col * light + spec * 255 * 0.55
    fog = np.exp(-tt / 30.0)[..., None]
    out = out * fog + FOG * (1 - fog)
    small = np.clip(out, 0, 255).astype(np.uint8)
    big = np.asarray(Image.fromarray(small).resize((W, H), Image.BILINEAR), np.float32)
    if sx or sy:
        big = np.roll(big, (int(round(sy)), int(round(sx))), (0, 1))
    return big


def light_at(p, t, lamps=()):
    """Scalar brightness at a wall point (for portrait shading)."""
    p = np.asarray(p, float)
    s = 0.62
    for k, q in enumerate(SCONCES):
        d2 = float(np.sum((np.asarray(q) - p) ** 2))
        if d2 < 80:
            s += 0.9 * flicker(k, t) / (1 + d2 / 2.2) * 0.55
    for q, i, _ in lamps:
        d2 = float(np.sum((np.asarray(q) - p) ** 2))
        s += i * 0.55 / (1 + d2 / 2.2)
    return s


# ------------------------------------------------------------------ portrait quads
def homography(src, dst):
    """Coefficients for PIL PERSPECTIVE: maps output (dst) points to input (src) points."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(A, float), np.array(b, float))


def wall_quad(wall, z_or_x, yc, w, h, off=0.03):
    """World corners TL, TR, BR, BL of a w x h plane on a wall, as seen facing it."""
    if wall == 'L':           # faces +x; a camera looking at it (-x) has +z on its left
        x = -HALF + off
        return np.array([[x, yc + h / 2, z_or_x + w / 2], [x, yc + h / 2, z_or_x - w / 2],
                         [x, yc - h / 2, z_or_x - w / 2], [x, yc - h / 2, z_or_x + w / 2]])
    if wall == 'R':           # faces -x; looking at it (+x), right = +z
        x = HALF - off
        return np.array([[x, yc + h / 2, z_or_x - w / 2], [x, yc + h / 2, z_or_x + w / 2],
                         [x, yc - h / 2, z_or_x + w / 2], [x, yc - h / 2, z_or_x - w / 2]])
    z = Z_END + off           # end wall faces +z; viewer looks -z, right = +x
    return np.array([[z_or_x - w / 2, yc + h / 2, z], [z_or_x + w / 2, yc + h / 2, z],
                     [z_or_x + w / 2, yc - h / 2, z], [z_or_x - w / 2, yc - h / 2, z]])


def draw_quad(canvas, cam, corners, tex):
    """Composite RGBA PIL `tex` onto float canvas through the projected quad. Returns screen corners or None."""
    pts, z = cam.project(corners)
    if (z < 0.25).any():
        return None
    x0, y0 = np.floor(pts.min(0)).astype(int)
    x1, y1 = np.ceil(pts.max(0)).astype(int)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if X1 <= X0 or Y1 <= Y0:
        return None
    tw, th = tex.size
    src = [(0, 0), (tw, 0), (tw, th), (0, th)]
    dst = [(px - X0, py - Y0) for px, py in pts]
    coef = homography(src, dst)
    im = tex.transform((X1 - X0, Y1 - Y0), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)
    a = np.asarray(im, np.float32)
    al = a[..., 3:4] / 255
    reg = canvas[Y0:Y1, X0:X1]
    reg[:] = reg * (1 - al) + a[..., :3] * al
    return pts


# ------------------------------------------------------------------ frame artwork
def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


@functools.lru_cache(None)
def frame_art(w, h, border, margin):
    """Gilded frame RGBA (w x h incl. soft wall shadow margin), with a transparent canvas hole."""
    W_, H_ = w + 2 * margin, h + 2 * margin
    sh = Image.new('L', (W_, H_), 0)
    ImageDraw.Draw(sh).rectangle([margin + 6, margin + 18, margin + w + 6, margin + h + 22], fill=200)
    sh = sh.filter(ImageFilter.GaussianBlur(margin * 0.45))
    out = np.zeros((H_, W_, 4), np.float32)
    out[..., 3] = np.asarray(sh, np.float32)
    # gold bevel: brightness by distance to the outer edge
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    k = np.clip(dist / border, 0, 1)
    prof = 0.55 + 0.45 * np.sin(k * math.pi * 2.0) ** 2 * (1 - 0.4 * k) + 0.25 * (k < 0.08)
    light = 1.0 + 0.25 * (yy < xx * h / w)                           # top-left catches the light
    nz = _noise(256, 11)[(yy % 256).astype(int), (xx % 256).astype(int)]
    gold = np.array([196, 146, 58], np.float32)
    rgb = gold[None, None] * (prof * light * (0.85 + 0.25 * nz))[..., None]
    inner = dist >= border
    lip = (dist >= border - 5) & (dist < border)
    rgb[lip] = (40, 26, 12)
    fr = np.zeros((h, w, 4), np.float32)
    fr[..., :3] = np.clip(rgb, 0, 255)
    fr[..., 3] = np.where(inner, 0, 255)
    reg = out[margin:margin + h, margin:margin + w]
    a = fr[..., 3:4] / 255
    reg[..., :3] = reg[..., :3] * (1 - a) + fr[..., :3] * a
    reg[..., 3:4] = np.maximum(reg[..., 3:4] * (1 - a), fr[..., 3:4])
    reg[..., 3] = np.where(inner, 0, reg[..., 3])
    return out


@functools.lru_cache(None)
def backdrop(w, h, c0, c1):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h * 0.46) / (h * 0.62)) ** 2)
    k = np.clip(r, 0, 1)[..., None] ** 1.3
    a, b = np.array(hex_rgb(c0), np.float32), np.array(hex_rgb(c1), np.float32)
    return a * (1 - k) + b * k


@functools.lru_cache(None)
def stamp_img(text, rgb, size):
    import fx
    f = fx.font('Heavy', size)
    tw = int(f.getlength(text))
    pad = int(size * 0.45)
    Wd, Hd = tw + 2 * pad, int(size * 1.25) + 2 * pad
    im = Image.new('L', (Wd, Hd), 0)
    d = ImageDraw.Draw(im)
    lw = max(4, size // 9)
    d.rounded_rectangle([lw, lw, Wd - lw, Hd - lw], radius=size // 5, outline=255, width=lw)
    d.text((Wd / 2, Hd / 2), text, font=f, fill=255, anchor='mm')
    a = np.asarray(im, np.float32) / 255
    rng = np.random.default_rng(len(text) * 31 + size)
    grit = np.asarray(Image.fromarray((rng.random((Hd // 3 + 1, Wd // 3 + 1)) * 255).astype(np.uint8))
                      .resize((Wd, Hd), Image.BILINEAR), np.float32) / 255
    a = a * np.clip(0.55 + 0.7 * grit, 0, 1) * 0.92
    rgba = np.zeros((Hd, Wd, 4), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA').rotate(-11, expand=True, resample=Image.BICUBIC)
