"""Two short 3D cutaways (perspective camera in numpy; deterministic per frame):

A · vault(u)  — fly-through of a dark hall: all 57 crafted Desk Calendar models stand on glowing pedestals,
    grouped by tier (Uncommon → Rare → Epic), the 5 Legendary models wait in a gold arc at the end.
    Glossy floor with per-pixel lighting, mirrored reflections, distance fog.
B · legend(u, t) — the Celestial Map on a Black backdrop card turns in 3D (perspective-mapped planes with
    parallax between backdrop, pattern and model), god rays, floor reflection, floating sparks.

Both return RGB uint8 (1920, 1080, 3). u = seconds since the scene started, t = content time (Lottie phase).
"""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import fx
import gifts_api as G
import lottie

W, H = 1080, 1920
GIFT = 'Desk Calendar'
TIERS = [('uncommon', 'UNCOMMON', (90, 220, 140)), ('rare', 'RARE', (80, 160, 255)),
         ('epic', 'EPIC', (190, 110, 255)), ('legendary', 'LEGENDARY', (255, 196, 70))]


def _norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


class Cam:
    def __init__(self, eye, target, fov, cy=0.5, roll=0.0):
        self.e = np.asarray(eye, np.float32)
        f = _norm(np.asarray(target, np.float32) - self.e)
        r = _norm(np.cross(f, [0, 1, 0]))
        up = np.cross(r, f)
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            r, up = r * c + up * s, up * c - r * s
        self.f, self.r, self.up = f, r, up
        self.k = (H / 2) / math.tan(math.radians(fov) / 2)
        self.cy = cy

    def project(self, p):
        q = np.asarray(p, np.float32) - self.e
        z = float(q @ self.f)
        if z < 0.05:
            return None
        return W / 2 + float(q @ self.r) / z * self.k, H * self.cy - float(q @ self.up) / z * self.k, z

    def rays(self, step=2):
        ys, xs = np.mgrid[0:H:step, 0:W:step].astype(np.float32)
        px = (xs + step / 2 - W / 2) / self.k
        py = -(ys + step / 2 - H * self.cy) / self.k
        d = self.f + px[..., None] * self.r + py[..., None] * self.up
        return _norm(d)


@functools.lru_cache(None)
def crafted():
    ms = [m for m in G.models(GIFT) if m.get('crafted')]
    return {k: [m['name'] for m in ms if m.get('rarityTier') == k] for k, _, _ in TIERS}


def model_im(name, t, size, live=True):
    if live:
        return lottie.frame(str(G.model_file(GIFT, name, 'json')), t, size=size)
    return _png(name, size)


@functools.lru_cache(maxsize=512)
def _png(name, size):
    return Image.open(G.model_png(GIFT, name, 512)).convert('RGBA').resize((size, size), Image.LANCZOS)


def paste(canvas, im, x, y, alpha=1.0, add=False):
    """canvas: float32 HxWx3. Centre of im at (x, y)."""
    a = np.asarray(im, np.float32)
    h, w = a.shape[:2]
    X, Y = int(round(x - w / 2)), int(round(y - h / 2))
    xa, ya, xb, yb = max(X, 0), max(Y, 0), min(X + w, W), min(Y + h, H)
    if xb <= xa or yb <= ya:
        return
    piece = a[ya - Y:yb - Y, xa - X:xb - X]
    al = piece[..., 3:4] / 255 * alpha
    reg = canvas[ya:yb, xa:xb]
    if add:
        reg += piece[..., :3] * al
    else:
        reg[:] = reg * (1 - al) + piece[..., :3] * al


@functools.lru_cache(None)
def _label(text, rgb, size):
    f = fx.font('Heavy', size)
    w = int(f.getlength(text)) + 40
    im = Image.new('RGBA', (w, size + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((w / 2, size / 2 + 20), text, font=f, fill=rgb + (255,), anchor='mm')
    glow = im.filter(ImageFilter.GaussianBlur(10))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out


# ------------------------------------------------------------------ A · vault
def _vault_layout():
    """[(name, tier index, x, z)] — two rows per tier along the hall; legendaries in an arc at the end."""
    out = []
    z = -4.0
    for ti, (key, _, _) in enumerate(TIERS[:3]):
        names = crafted()[key]
        for k, n in enumerate(names):
            side = -1 if k % 2 == 0 else 1
            out.append((n, ti, side * (1.25 + 0.35 * ((k // 2) % 2)), z - (k // 2) * 1.25))
        z -= (len(names) + 1) // 2 * 1.25 + 1.8
    leg = crafted()['legendary']
    zc = z - 4.0
    for k, n in enumerate(leg):
        a = math.radians(-40 + k * 20)
        out.append((n, 3, math.sin(a) * 1.7, zc + 1.2 - math.cos(a) * 1.7))
    return out, zc


VAULT_DUR = 5.6


def vault_cam(u):
    lay, zc = _vault_layout()
    x = fx.smooth(u / VAULT_DUR)
    s = fx.remap(x, [(0, 0), (0.62, 0.9), (1, 1)])
    z = 4.0 + (zc + 5.8 - 4.0) * s
    eye = (0.35 * math.sin(u * 0.9), 0.95 + 0.2 * s, z)
    tgt = (0.2 * math.sin(u * 0.7 + 1), 1.05 + 0.15 * s, z - 6)
    return Cam(eye, tgt, 64, roll=0.03 * math.sin(u * 1.1)), lay, zc


def vault(u, t):
    cam, lay, zc = vault_cam(u)
    step = 2
    d = cam.rays(step)
    e = cam.e
    hit = d[..., 1] < -1e-3
    tt = np.where(hit, -e[1] / np.where(hit, d[..., 1], -1), 1e9)
    px, pz = e[0] + d[..., 0] * tt, e[2] + d[..., 2] * tt
    # sky: deep blue-violet gradient with a warm glow at the far end
    sky = np.zeros(d.shape, np.float32)
    up = np.clip(d[..., 1], -1, 1)
    sky[:] = np.array([10, 10, 24], np.float32) + np.array([30, 18, 60]) * np.clip(1 - up * 2, 0, 1)[..., None]
    fwd = np.clip((d @ np.float32([0, 0.1, -1])), 0, 1) ** 12
    sky *= 0.6
    hz = np.where(up > 1e-3, (3.2 - e[1]) / np.maximum(up, 1e-3), 1e9)       # ceiling plane y = 3.2
    cz = e[2] + d[..., 2] * hz
    beam = np.clip(1 - np.abs(((cz + 0.6) % 2.4) - 1.2) / 0.08, 0, 1) * np.exp(-hz / 14)
    sky += np.array([120, 90, 200]) * (beam * (up > 0))[..., None] * 0.5
    sky += np.array([255, 180, 80]) * fwd[..., None] * 0.35
    # floor: glossy dark tiles, pools of tier light under each pedestal
    col = np.zeros(d.shape, np.float32) + np.array([16, 16, 28], np.float32)
    gx = np.abs(((px + 0.8) % 1.6) - 0.8)
    gz = np.abs(((pz + 0.8) % 1.6) - 0.8)
    line = np.clip(1 - np.minimum(gx, gz) / 0.03, 0, 1)
    col += line[..., None] * 22
    for n, ti, x, z in lay:
        rgb = np.array(TIERS[ti][2], np.float32)
        r2 = (px - x) ** 2 + (pz - z) ** 2
        col += rgb * (np.exp(-r2 / (0.55 if ti < 3 else 1.1)) * (0.55 if ti < 3 else 0.9))[..., None]
    col += np.array([255, 190, 90]) * (np.exp(-((px) ** 2 + (pz - zc) ** 2) / 9) * 0.35)[..., None]
    fog = np.exp(-tt / 26)[..., None]
    col = col * fog + sky * (1 - fog)
    img = np.where(hit[..., None], col, sky)
    img = np.asarray(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR),
                     np.float32)
    # sprites, far to near: reflection first, then pedestal glow, then model
    items = []
    for n, ti, x, z in lay:
        base = cam.project((x, 0.0, z))
        top = cam.project((x, 0.95 if ti < 3 else 1.35, z))
        if base is None or top is None:
            continue
        items.append((base[2], n, ti, x, z, base, top))
    for dist, n, ti, x, z, base, top in sorted(items, reverse=True):
        hp = (base[1] - top[1]) / 0.9
        size = int(hp)
        if size < 6 or size > 2600:
            continue
        live = dist < 9 and size > 90
        im = model_im(n, t + (hash(n) % 97) / 31, min(512, max(16, size)) if live else min(512, size), live)
        if im.size[0] != size:
            im = im.resize((size, size), Image.BILINEAR)
        f = math.exp(-dist / 24)
        cx = base[0]
        cy = base[1] - size * 0.5
        glow = fx.radial(max(8, int(size * 1.4)), TIERS[ti][2], power=2.4, peak=0.55 * f)
        paste(img, glow, cx, base[1] - size * 0.35, 1.0, add=True)
        refl = im.transpose(Image.FLIP_TOP_BOTTOM)
        paste(img, refl, cx, base[1] + size * 0.45, 0.22 * f)
        if f < 0.98:                                       # distance fog on the sprite colour
            arr = np.asarray(im, np.float32).copy()
            arr[..., :3] = arr[..., :3] * f + np.array([20, 16, 40]) * (1 - f)
            im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
        paste(img, im, cx, cy, 1.0)
    # tier labels floating above each group
    groups = {}
    for n, ti, x, z in lay:
        groups.setdefault(ti, []).append(z)
    for ti, zs in groups.items():
        zz = max(zs) + 0.4 if ti < 3 else zc - 0.6
        p = cam.project((0, 1.75 if ti < 3 else 2.25, zz))
        if p is None or p[2] < 1.0:
            continue
        s = int(min(110, 240 / p[2] * 1.6))
        if s < 14:
            continue
        lab = _label(TIERS[ti][1] + (f' · {len(zs)}' if True else ''), TIERS[ti][2], max(14, s))
        a = min(1.0, (p[2] - 1.0) / 2.0) * math.exp(-p[2] / 30)
        paste(img, lab, p[0], p[1], a)
    # vignette + grain
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1 - 0.35 * np.clip(r - 0.55, 0, 1))[..., None]
    img += np.random.default_rng(int(u * 60)).normal(0, 4, (H, W, 1))
    return np.clip(img, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ B · legend
@functools.lru_cache(None)
def _backdrop_tex(n=900):
    """Black backdrop (centre #363738 → edge #0e0f0f) with a faint Star pattern ring, as Telegram shows it."""
    c, e = np.array([0x36, 0x37, 0x38], np.float32), np.array([0x0e, 0x0f, 0x0f], np.float32)
    hgt = int(n * 1.3)
    yy, xx = np.mgrid[0:hgt, 0:n].astype(np.float32)
    r = np.clip(np.sqrt(((xx - n / 2) / (n / 2)) ** 2 + ((yy - hgt * 0.42) / (n / 2)) ** 2) / 1.25, 0, 1)
    rgb = c * (1 - r[..., None]) + e * r[..., None]
    im = Image.fromarray(rgb.astype(np.uint8)).convert('RGBA')
    try:
        sym = Image.open(G.symbol_png(GIFT, 'Star', 256)).convert('RGBA')
        a = np.asarray(sym, np.float32)
        tintc = np.zeros_like(a)
        tintc[..., :3] = (0x6c, 0x68, 0x68)
        tintc[..., 3] = a[..., 3] * 0.55
        sym = Image.fromarray(tintc.astype(np.uint8), 'RGBA')
        for ring, cnt, s in ((0.33, 8, 70), (0.47, 12, 54)):
            for k in range(cnt):
                ang = 2 * math.pi * (k + 0.5 * (ring > 0.4)) / cnt
                sx, sy = n / 2 + math.cos(ang) * n * ring, hgt * 0.42 + math.sin(ang) * n * ring
                im.alpha_composite(sym.resize((s, s), Image.LANCZOS), (int(sx - s / 2), int(sy - s / 2)))
    except Exception:
        pass
    m = Image.new('L', (n * 2, hgt * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, n * 2 - 1, hgt * 2 - 1], 90, fill=255)
    im.putalpha(m.resize((n, hgt), Image.LANCZOS))
    border = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle([3, 3, n - 4, hgt - 4], 46, outline=(255, 210, 110, 200), width=6)
    im.alpha_composite(border)
    return im


def _persp_coeffs(src, dst):
    """Coefficients for PIL PERSPECTIVE mapping output points dst -> input points src."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    return np.linalg.solve(np.array(A, np.float64), np.array(b, np.float64))


def quad(canvas, tex, cam, corners, alpha=1.0):
    """Draw texture `tex` (RGBA) on the world quad corners [tl, tr, br, bl] (perspective-correct)."""
    pts = [cam.project(c) for c in corners]
    if any(p is None for p in pts):
        return
    dst = [(p[0], p[1]) for p in pts]
    w, h = tex.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    x0, y0 = max(0, int(min(p[0] for p in dst)) - 2), max(0, int(min(p[1] for p in dst)) - 2)
    x1, y1 = min(W, int(max(p[0] for p in dst)) + 2), min(H, int(max(p[1] for p in dst)) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    loc = [(x - x0, y - y0) for x, y in dst]
    try:
        co = _persp_coeffs(src, loc)
    except np.linalg.LinAlgError:
        return
    im = tex.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(co), Image.BICUBIC)
    a = np.asarray(im, np.float32)
    al = a[..., 3:4] / 255 * alpha
    reg = canvas[y0:y1, x0:x1]
    reg[:] = reg * (1 - al) + a[..., :3] * al


LEGEND_DUR = 2.5


def legend(u, t, name='Celestial Map'):
    x = min(1.0, u / LEGEND_DUR)
    ang = math.radians(78 * (1 - fx.ease_out(min(1, x * 1.35))) - 8 * fx.smooth(x))
    dist = 6.2 - 1.3 * fx.ease_out(x)
    cam = Cam((math.sin(u * 0.6) * 0.3, 1.5, dist), (0, 1.55, 0), 52, cy=0.47)
    img = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # background: black velvet with a gold halo and rotating god rays
    r = np.sqrt((xx - W / 2) ** 2 + (yy - H * 0.42) ** 2)
    img += np.array([255, 190, 80]) * (np.exp(-r / 380) * 0.55 * fx.smooth(x * 2))[..., None]
    th = np.arctan2(yy - H * 0.42, xx - W / 2)
    rays = (0.5 + 0.5 * np.cos(th * 14 + u * 0.8)) ** 6 * np.exp(-r / 900)
    img += np.array([255, 210, 120]) * (rays * 0.32 * fx.smooth(x * 1.6))[..., None]
    img += np.array([8, 8, 14])
    # glossy floor plane y = 0 from the horizon down
    hor = cam.project((0, 0, -60))
    hy = hor[1] if hor else H * 0.6
    fl = np.clip((yy - hy) / (H - hy), 0, 1)
    img = img * (1 - 0.6 * fl[..., None]) + np.array([10, 10, 16]) * 0.6 * fl[..., None]
    # card (backdrop) and the model in front of it, rotating together about the vertical axis
    tex = _backdrop_tex()
    cw, chh = 2.2, 2.2 * tex.size[1] / tex.size[0]
    ca, sa = math.cos(ang), math.sin(ang)
    def rot(px, py, pz):
        return (px * ca + pz * sa, py, -px * sa + pz * ca)
    yb = 0.25
    corners = [rot(-cw / 2, yb + chh, 0), rot(cw / 2, yb + chh, 0), rot(cw / 2, yb, 0), rot(-cw / 2, yb, 0)]
    refl = [(c[0], -c[1], c[2]) for c in corners]
    quad(img, tex, cam, refl, 0.16)
    quad(img, tex, cam, corners, 1.0)
    m = lottie.frame(str(G.model_file(GIFT, name, 'json')), t, size=512)
    ms = 1.75
    mz = 0.32                                            # model floats in front of the card (parallax)
    my = yb + chh * 0.58
    mc = [rot(-ms / 2, my + ms / 2, mz), rot(ms / 2, my + ms / 2, mz), rot(ms / 2, my - ms / 2, mz),
          rot(-ms / 2, my - ms / 2, mz)]
    quad(img, m, cam, [(c[0], -c[1], c[2]) for c in mc], 0.12)
    quad(img, m, cam, mc, 1.0)
    # sparks drifting in 3D around the card
    rng = np.random.default_rng(7)
    for k in range(70):
        p0 = rng.uniform([-2.4, 0.2, -1.6], [2.4, 3.6, 1.6])
        p = (p0[0] + 0.15 * math.sin(u * 1.3 + k), p0[1] + (u * 0.25 + k * 0.07) % 1.2, p0[2])
        q = cam.project(p)
        if q is None:
            continue
        s = int(max(4, 60 / q[2]))
        tw = 0.5 + 0.5 * math.sin(u * 6 + k * 1.7)
        paste(img, fx.radial(s * 2, (255, 220, 140), power=3, peak=0.9 * tw), q[0], q[1], 1.0, add=True)
    flash = max(0.0, 1 - u / 0.35)
    img = img * (1 - flash) + 255 * flash
    img += np.random.default_rng(int(u * 60) + 99).normal(0, 3.5, (H, W, 1))
    return np.clip(img, 0, 255).astype(np.uint8)
