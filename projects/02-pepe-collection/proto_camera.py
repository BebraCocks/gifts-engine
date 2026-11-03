"""Camera test (4 s, no narration): Happy Pepe -> the star flies off -> camera follows it -> Pepe Dream.

World: a night swamp of our own (water plane with moon reflection, lily pads, reeds, fireflies, stars).
2.5D: gifts are live Lottie billboards placed in 3D; water/sky are shaded per pixel through a perspective camera.
Frame is a pure function of time. Motion blur = averaged sub-frames, count depends on screen motion.

    python -B proto_camera.py --frames 0,75,110,140,170,200,239
    python -B proto_camera.py --video build/proto_camera.mp4
"""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import frames
import fx
import gifts_api
import lottie

W, H, FPS = 1080, 1920, 60
DUR = 4.0
HW, HH = W // 2, H // 2                       # background is shaded at half resolution
SHUTTER = 0.5 / FPS                            # 180-degree shutter

HP_ANIM = str(gifts_api.model_file('Kissed Frog', 'Happy Pepe', 'json'))
PD_ANIM = str(gifts_api.model_file("Durov's Glasses", 'Pepe Dream', 'json'))

# ---------------------------------------------------------------- palette (night swamp)
ZENITH = np.array([3, 7, 14], np.float32)
HORIZON = np.array([20, 50, 50], np.float32)
FOG = np.array([22, 52, 50], np.float32)
WATER = np.array([3, 13, 13], np.float32)
TREES = np.array([5, 15, 15], np.float32)
PAD = np.array([38, 92, 44], np.float32)
PAD_DARK = np.array([18, 50, 26], np.float32)
MOONLIGHT = np.array([225, 240, 215], np.float32)
FIREFLY = np.array([200, 255, 120], np.float32)
STAR = np.array([255, 222, 90], np.float32)
MINT = (170, 228, 190)
PEPE = (120, 205, 85)

MOON = np.array([0.155, 0.255, 1.0]); MOON /= np.linalg.norm(MOON)

# ---------------------------------------------------------------- world layout
HP_POS = np.array([0.0, 0.0, 0.0])            # Happy Pepe sits on a pad
PD_POS = np.array([7.5, 0.0, 9.0])            # Pepe Dream floats above a pad
GIFT_SIZE = 2.0
PD_HOVER = 0.55

rng = np.random.default_rng(20261103)
PADS = [(0.0, 0.05, 1.25, 0.6), (7.5, 9.0, 1.15, 2.4)]          # x, z, radius, notch angle
for _ in range(60):
    x, z = rng.uniform(-9, 16), rng.uniform(-3, 26)
    if all((x - a) ** 2 + (z - b) ** 2 > (r + 0.9) ** 2 for a, b, r, _ in PADS):
        PADS.append((x, z, rng.uniform(0.35, 0.9), rng.uniform(0, 2 * math.pi)))
PADS = np.array(PADS, np.float32)

STARS = rng.normal(size=(700, 3)); STARS[:, 1] = np.abs(STARS[:, 1]) + 0.02
STARS /= np.linalg.norm(STARS, axis=1, keepdims=True)
STAR_MAG = rng.uniform(0.25, 1.0, 700) ** 2.5
STAR_PHASE = rng.uniform(0, 6.28, 700)

FIREFLIES = np.column_stack([rng.uniform(-6, 13, 110), rng.uniform(0.25, 3.2, 110), rng.uniform(-4, 17, 110)])
FF_PHASE = rng.uniform(0, 6.28, (110, 4))


def reed_cluster(cx, cz, n, hmin, hmax, seed):
    r = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        bx, bz = cx + r.uniform(-0.45, 0.45), cz + r.uniform(-0.3, 0.3)
        h = r.uniform(hmin, hmax)
        lean = r.uniform(-0.25, 0.25)
        out.append((bx, bz, h, lean, r.uniform(0, 6.28), r.random() < 0.55))
    return out


BACK_REEDS = sum((reed_cluster(x, z, 9, 1.0, 2.4, i) for i, (x, z) in enumerate(
    [(-4.5, 6), (3.5, 14), (12, 15), (-1.5, 15), (10.5, 5), (-7, 2), (14, 22), (5, 20)])), [])
FRONT_REEDS = sum((reed_cluster(x, z, 7, 1.6, 3.2, 50 + i) for i, (x, z) in enumerate(
    [(-2.9, -3.6), (2.6, -2.2), (5.2, 1.8), (2.4, 4.4), (10.6, 7.6)])), [])


def treeline(az):
    return (0.03 + 0.016 * np.sin(az * 7 + 1) + 0.01 * np.sin(az * 23 + 2)
            + 0.006 * np.sin(az * 61) + 0.004 * np.abs(np.sin(az * 140)))


# ---------------------------------------------------------------- camera
def ease(x):
    x = fx.clamp01(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def bez(p0, p1, p2, u):
    return (1 - u) ** 2 * p0 + 2 * (1 - u) * u * p1 + u * u * p2


STAR_T0, STAR_T1 = 1.30, 2.42                  # star flight; impact on Pepe Dream at STAR_T1
EMERGE = 1.22


def hp_center():
    return HP_POS + np.array([0, GIFT_SIZE * 0.38, 0])


def pd_center(t):
    bob = 0.06 * math.sin(t * 2.4)
    sq = squash(t)
    return PD_POS + np.array([0, PD_HOVER + GIFT_SIZE * 0.5 + bob - 0.1 * sq, 0])


def squash(t):
    return fx.bump(fx.clamp01((t - STAR_T1) / 0.6), 3.0, 5.0) if t >= STAR_T1 else 0.0


S0 = hp_center() + np.array([GIFT_SIZE * 0.20, GIFT_SIZE * 0.03, -0.15])
S_CTRL = np.array([2.4, 3.6, 2.2])


def star_pos(t):
    u = ease((t - STAR_T0) / (STAR_T1 - STAR_T0)) if t > STAR_T0 else 0.0
    return bez(S0, S_CTRL, pd_center(STAR_T1) + np.array([0, 0.05, -0.2]), u)


CAM_A0 = np.array([-0.35, 1.25, -6.3])
CAM_A1 = np.array([-0.15, 1.15, -5.3])
CAM_MID = np.array([2.8, 2.7, -1.0])
CAM_B1 = PD_POS + np.array([-2.0, 1.3, -6.6])
CAM_B2 = PD_POS + np.array([-1.7, 1.2, -5.9])
LOOK_HP = HP_POS + np.array([0, 0.95, 0])
LOOK_PD = PD_POS + np.array([0, 1.3, 0])


def camera(t):
    """-> position, target, roll (rad), vertical fov (deg)."""
    if t < STAR_T0:
        u = ease(t / STAR_T0) * 0.85 + 0.15 * t / STAR_T0
        C = CAM_A0 + (CAM_A1 - CAM_A0) * u
    elif t < 2.75:
        u = (t - STAR_T0) / (2.75 - STAR_T0)
        u = ease(u) * 0.92 + 0.08 * u
        C = bez(CAM_A1, CAM_MID, CAM_B1, u)
    else:
        u = ease((t - 2.75) / (DUR - 2.75)) * 0.7 + 0.3 * (t - 2.75) / (DUR - 2.75)
        C = CAM_B1 + (CAM_B2 - CAM_B1) * u
    # target: Happy Pepe -> chase the star -> settle on Pepe Dream (no hard switches)
    w_star = ease((t - 1.18) / 0.32) * (1 - ease((t - 2.25) / 0.45))
    w_pd = ease((t - 2.05) / 0.75)
    base = LOOK_HP + (LOOK_PD - LOOK_HP) * w_pd
    lead = star_pos(min(t + 0.06, STAR_T1))
    T = base + (lead - base) * w_star * 0.85
    # handheld drift + bank into the turn
    drift = np.array([0.03 * math.sin(t * 1.3), 0.025 * math.sin(t * 1.7 + 1), 0])
    roll = math.radians(0.8 * math.sin(t * 0.9) - 17.0 * math.sin(math.pi * fx.clamp01((t - 1.25) / 1.45)) ** 2)
    fov = 50 + 9 * math.sin(math.pi * fx.clamp01((t - 1.3) / 1.3)) ** 2
    return C + drift, T + drift * 0.5, roll, fov


def basis(C, T, roll):
    f = T - C; f = f / np.linalg.norm(f)
    r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r)
    u = np.cross(f, r)
    cr, sr = math.cos(roll), math.sin(roll)
    return f, cr * r + sr * u, -sr * r + cr * u


class Cam:
    def __init__(self, t):
        self.C, T, self.roll, fov = camera(t)
        self.f, self.r, self.u = basis(self.C, T, self.roll)
        self.F = (H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, P):
        d = np.asarray(P, float) - self.C
        z = d @ self.f
        return W / 2 + self.F * (d @ self.r) / np.maximum(z, 1e-3), H / 2 - self.F * (d @ self.u) / np.maximum(z, 1e-3), z


# ---------------------------------------------------------------- background (per pixel, half res)
_gx, _gy = np.meshgrid((np.arange(HW) + 0.5) * 2 - W / 2, (np.arange(HH) + 0.5) * 2 - H / 2)


def sky(dx, dy, dz):
    n = np.sqrt(dx * dx + dy * dy + dz * dz)
    e = dy / n
    k = np.clip(e / 0.55, 0, 1); k = (k * k * (3 - 2 * k))[..., None]
    col = HORIZON + (ZENITH - HORIZON) * k
    m = np.clip((dx * MOON[0] + dy * MOON[1] + dz * MOON[2]) / n, 0, 1)
    col = col + MOONLIGHT[None, None] * (0.10 * m ** 40 + 0.05 * m ** 6)[..., None]
    az = np.arctan2(dx, dz)
    tree = e < treeline(az)
    col = np.where(tree[..., None], TREES + (FOG - TREES) * 0.25, col)
    return col


def background(cam, t):
    a, b = _gx / cam.F, _gy / cam.F
    dx = cam.f[0] + a * cam.r[0] - b * cam.u[0]
    dy = cam.f[1] + a * cam.r[1] - b * cam.u[1]
    dz = cam.f[2] + a * cam.r[2] - b * cam.u[2]
    out = sky(dx, dy, dz)
    water = dy < -1e-4
    if water.any():
        wx, wy, wz = dx[water], dy[water], dz[water]
        tt = -cam.C[1] / wy
        x, z = cam.C[0] + tt * wx, cam.C[2] + tt * wz
        n = np.sqrt(wx * wx + wy * wy + wz * wz)
        dist = tt * n
        # ripples perturb the reflected ray
        px = 0.045 * (np.sin(1.3 * x + 2.1 * t) + 0.6 * np.sin(2.9 * z - 1.4 * t + 0.7 * x))
        pz = 0.07 * (np.sin(1.7 * z + 1.6 * t) + 0.5 * np.sin(3.7 * x + 2.3 * t))
        att = np.clip(4.0 / (dist + 4.0), 0.15, 1)
        rx, ry, rz = wx / n + px * att, -wy / n, wz / n + pz * att
        refl = sky(rx[None], ry[None], rz[None])[0]
        m = np.clip((rx * MOON[0] + ry * MOON[1] + rz * MOON[2]) / np.sqrt(rx * rx + ry * ry + rz * rz), 0, 1)
        glint = (0.75 * m ** 2500 + 0.09 * m ** 200)[:, None] * MOONLIGHT
        fres = (0.35 + 0.55 * (1 - np.abs(wy / n)) ** 4)[:, None]
        col = WATER + refl * fres + glint
        # lily pads (analytic, perspective-correct)
        aa = 0.012 * dist + 0.01
        for cx, cz, rad, notch in PADS:
            ddx, ddz = x - cx, z - cz
            d = np.sqrt(ddx * ddx + ddz * ddz)
            near = d < rad + aa
            if not near.any():
                continue
            ang = np.arctan2(ddz[near], ddx[near]) - notch
            cut = np.clip((np.cos(ang) - 0.965) / 0.02, 0, 1) * np.clip(d[near] / (rad * 0.25), 0, 1)
            cover = np.clip((rad - d[near]) / aa[near], 0, 1) * (1 - cut)
            vein = 0.5 + 0.5 * np.cos(ang * 9)
            rim = np.clip((d[near] / rad - 0.82) / 0.18, 0, 1)
            pc = PAD_DARK + (PAD - PAD_DARK) * (0.55 + 0.25 * vein[:, None] + 0.35 * rim[:, None])
            spec = MOONLIGHT * (0.12 * np.clip(1 - d[near] / rad, 0, 1))[:, None]
            c = col[near]
            col[near] = c + (pc + spec - c) * cover[:, None]
        fog = (1 - np.exp(-dist / 22.0))[:, None] * 0.85
        out[water] = col + (FOG - col) * fog
    return out


# ---------------------------------------------------------------- sprites
_cache = {}


def glow(radius, color, core=0.6):
    key = ('g', int(radius), tuple(int(c) for c in color), core)
    if key not in _cache:
        r = max(2, int(radius))
        y, x = np.mgrid[-r:r + 1, -r:r + 1]
        d = np.sqrt(x * x + y * y) / r
        g = np.clip(1 - d, 0, 1) ** 2.2 * (1 - core) + np.exp(-(d / 0.18) ** 2) * core
        _cache[key] = g[..., None] * (np.asarray(color, np.float32) / 255.0)
    return _cache[key]


def star_sprite(size, rot):
    size = max(8, int(size))
    key = ('s', size, int(rot * 20) % 126)
    if key not in _cache:
        s = size * 4
        im = Image.new('L', (s, s), 0)
        d = ImageDraw.Draw(im)
        pts = []
        for k in range(10):
            rr = s * (0.48 if k % 2 == 0 else 0.21)
            a = rot + k * math.pi / 5 - math.pi / 2
            pts.append((s / 2 + rr * math.cos(a), s / 2 + rr * math.sin(a)))
        d.polygon(pts, fill=255)
        im = im.resize((size, size), Image.LANCZOS)
        _cache[key] = np.asarray(im, np.float32)[..., None] / 255.0
    return _cache[key]


def add(canvas, spr, cx, cy, gain=1.0):
    h, w = spr.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    canvas[ya:yb, xa:xb] += spr[ya - y0:yb - y0, xa - x0:xb - x0] * (255.0 * gain)


def blend(canvas, rgba, x0, y0, alpha=1.0):
    h, w = rgba.shape[:2]
    x0, y0 = int(round(x0)), int(round(y0))
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb:
        return
    s = rgba[ya - y0:yb - y0, xa - x0:xb - x0]
    a = s[..., 3:4] * (alpha / 255.0)
    c = canvas[ya:yb, xa:xb]
    c += (s[..., :3] - c) * a


def lottie_sprite(path, t, px, roll):
    q = int(min(1024, max(128, math.ceil(px / 64) * 64)))
    im = lottie.frame(path, t, q)
    px = max(4, int(px))
    im = im.resize((px, px), Image.BILINEAR)
    if abs(roll) > 0.003:
        im = im.rotate(math.degrees(roll), resample=Image.BILINEAR, expand=True)
    return im


def draw_gift(canvas, cam, path, t_anim, center_world, size, reflect_base_y, alpha=1.0, scale=(1.0, 1.0)):
    sx, sy, z = cam.project(center_world)
    if z < 0.3:
        return
    px = cam.F * size / z
    im = lottie_sprite(path, t_anim, px, cam.roll)
    if scale != (1.0, 1.0):
        im = im.resize((max(4, int(im.width * scale[0])), max(4, int(im.height * scale[1]))), Image.BILINEAR)
    arr = np.asarray(im, np.float32)
    # reflection: mirror the billboard in the water plane
    mirror = center_world.copy(); mirror[1] = 2 * reflect_base_y - center_world[1]
    rx, ry, rz = cam.project(mirror)
    ref = arr[::-1].copy()
    hgt = ref.shape[0]
    fade = np.clip(1 - np.linspace(0, 1, hgt) * 1.4, 0, 1) ** 1.5
    ref[..., 3] *= fade[:, None] * 0.38
    ref[..., :3] *= 0.55
    blend(canvas, ref, rx - ref.shape[1] / 2, ry - hgt / 2, alpha)
    blend(canvas, arr, sx - arr.shape[1] / 2, sy - arr.shape[0] / 2, alpha)


def draw_reeds(canvas, cam, reeds, t, color, wind=1.0):
    layer = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(layer)
    for bx, bz, h, lean, ph, head in reeds:
        sway = lean + 0.06 * wind * math.sin(t * 1.6 + ph)
        base = np.array([bx, 0.0, bz]); top = np.array([bx + sway, h, bz])
        x0, y0, z0 = cam.project(base); x1, y1, z1 = cam.project(top)
        if z0 < 0.25 or z1 < 0.25:
            continue
        wpx = max(1.0, cam.F * 0.035 / z0)
        mid = cam.project(base + (top - base) * 0.55 + np.array([sway * 0.3, 0, 0]))
        d.line([(x0, y0), (mid[0], mid[1]), (x1, y1)], fill=255, width=int(wpx))
        if head:
            hc = cam.project(base + (top - base) * 0.82)
            hw = max(2, cam.F * 0.06 / z0); hh = max(4, cam.F * 0.34 / z0)
            d.ellipse([hc[0] - hw, hc[1] - hh / 2, hc[0] + hw, hc[1] + hh / 2], fill=255)
    box = layer.getbbox()
    if not box:
        return
    x0, y0, x1, y1 = box
    a = np.asarray(layer.crop(box), np.float32)[..., None] / 255.0
    c = canvas[y0:y1, x0:x1]
    c += (np.asarray(color, np.float32) - c) * a


# ---------------------------------------------------------------- one sharp sub-frame
def scene(t):
    cam = Cam(t)
    bg = background(cam, t)
    canvas = np.asarray(Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32)
    # stars + moon
    sx, sy, sz = cam.project(cam.C + STARS * 100)
    az = np.arctan2(STARS[:, 0], STARS[:, 2])
    vis = (sz > 0) & (STARS[:, 1] > treeline(az) + 0.01) & (sx > -4) & (sx < W + 4) & (sy > -4) & (sy < H + 4)
    for i in np.nonzero(vis)[0]:
        tw = 0.75 + 0.25 * math.sin(t * 3 + STAR_PHASE[i])
        add(canvas, glow(3 + 3 * STAR_MAG[i], (230, 240, 255), 0.85), sx[i], sy[i], STAR_MAG[i] * tw * 0.9)
    mx, my, mz = cam.project(cam.C + MOON * 100)
    if mz > 0:
        add(canvas, glow(cam.F * 0.18, (190, 220, 200), 0.0), mx, my, 0.35)
        add(canvas, glow(cam.F * 0.045, (255, 255, 240), 0.95), mx, my, 1.0)
    draw_reeds(canvas, cam, BACK_REEDS, t, TREES * 1.1)
    # gifts
    hp_t = t                                      # Lottie star bursts at ~1.2 s of the cycle
    hp_c = hp_center()
    pd_t = (t - STAR_T1 + 0.55) % 3.0             # mask opens its eyes right at the impact
    sq = squash(t)
    pdc = pd_center(t)
    items = [(cam.project(hp_c)[2], lambda: draw_gift(canvas, cam, HP_ANIM, hp_t, hp_c, GIFT_SIZE, 0.0)),
             (cam.project(pdc)[2], lambda: draw_gift(canvas, cam, PD_ANIM, pd_t, pdc, GIFT_SIZE, 0.0,
                                                    scale=(1 + 0.16 * sq, 1 - 0.14 * sq)))]
    for _, fn in sorted(items, key=lambda it: -it[0]):
        fn()
    # star: emerge from the Lottie burst, fly, trail, impact
    if t >= EMERGE:
        k = np.arange(0, 140)
        taus = STAR_T0 + k * 0.009
        for tau in taus[(taus <= min(t, STAR_T1)) & (taus > t - 0.55)]:
            age = (t - tau) / 0.55
            j = np.array([math.sin(tau * 91.7), math.sin(tau * 53.3 + 1), math.sin(tau * 71.1 + 2)]) * 0.06 * (1 + 2 * age)
            p = star_pos(tau) + j + np.array([0, -0.25 * age * age, 0])
            x, y, z = cam.project(p)
            if z > 0.3:
                add(canvas, glow(max(2, cam.F * 0.05 / z * (1 - age)), (255, 225, 110), 0.7), x, y, (1 - age) ** 1.5 * 0.55)
        if t < STAR_T1 + 0.05:
            p = star_pos(t)
            x, y, z = cam.project(p)
            grow = ease((t - EMERGE) / 0.12)
            if z > 0.3:
                size = cam.F * 0.42 / z * grow
                add(canvas, glow(size * 1.3, (255, 210, 80), 0.25), x, y, 0.55)
                add(canvas, star_sprite(size, t * 9.0) * STAR / 255.0, x, y, 1.0)
        if t >= STAR_T1:
            age = (t - STAR_T1) / 0.7
            if age < 1:
                cx, cy, cz = cam.project(pd_center(STAR_T1))
                add(canvas, glow(cam.F * (0.9 + 0.8 * age) / cz, (255, 230, 140), 0.1), cx, cy, (1 - age) ** 2 * 0.8)
                for i in range(22):
                    a = i / 22 * 6.283 + 0.4
                    rr = (0.4 + 1.5 * ease(age)) * (0.8 + 0.3 * math.sin(i * 7.1))
                    p = pd_center(STAR_T1) + np.array([math.cos(a) * rr, math.sin(a) * rr * 0.8 - 0.4 * age * age, -0.3])
                    x, y, z = cam.project(p)
                    add(canvas, star_sprite(cam.F * 0.12 / z * (1 - age), a) * STAR / 255.0, x, y, (1 - age))
    # fireflies
    for i, (bx, by, bz) in enumerate(FIREFLIES):
        ph = FF_PHASE[i]
        p = np.array([bx + 0.35 * math.sin(t * 0.7 + ph[0]), by + 0.2 * math.sin(t * 1.1 + ph[1]), bz + 0.35 * math.sin(t * 0.5 + ph[2])])
        x, y, z = cam.project(p)
        if z < 0.5 or not (-60 < x < W + 60 and -60 < y < H + 60):
            continue
        blink = 0.35 + 0.65 * max(0.0, math.sin(t * 2.2 + ph[3])) ** 2
        add(canvas, glow(max(4, cam.F * 0.1 / z), FIREFLY, 0.5), x, y, blink * 1.1)
    draw_reeds(canvas, cam, FRONT_REEDS, t, (2, 6, 6), wind=1.4)
    return canvas


# ---------------------------------------------------------------- cards (screen space, crisp)
def card(title, sub, stats):
    tf, sf, nf = fx.font('Bold', 92), fx.font('Semibold', 44), fx.font('Semibold', 46)
    im = Image.new('RGBA', (W, 300), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    for layer, off, col in ((sh, 4, (0, 0, 0, 170)), (im, 0, None)):
        d = ImageDraw.Draw(layer)
        d.text((W / 2, 60 + off), title, font=tf, fill=col or (255, 255, 255, 255), anchor='mm')
        d.text((W / 2, 145 + off), sub, font=sf, fill=col or MINT + (255,), anchor='mm')
        d.text((W / 2, 220 + off), stats, font=nf, fill=col or PEPE + (255,), anchor='mm')
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    return np.asarray(Image.alpha_composite(sh, im), np.float32)


CARD_HP = card('Happy Pepe', 'в подарке Kissed Frog', '80 шт. · 0,5% · от 912,9 TON')
CARD_PD = card('Pepe Dream', "в подарке Durov's Glasses", '43 шт. · 1% · ≈ 500 TON')
CARD_Y = 1500


def cards(canvas, t):
    a_in = ease((t - 0.2) / 0.45)
    out = ease((t - 1.22) / 0.3)
    if a_in > 0 and out < 1:
        blend(canvas, CARD_HP, -out * 520, CARD_Y + 40 * (1 - a_in), a_in * (1 - out))
    b = ease((t - 2.6) / 0.45)
    if b > 0:
        blend(canvas, CARD_PD, (1 - b) * 420, CARD_Y, b)


# ---------------------------------------------------------------- frame with motion blur
PROBES = [hp_center(), PD_POS + np.array([0, 1.4, 0]), np.array([3.0, 0.0, 6.0])]


def subframes(t):
    a, b = Cam(t - SHUTTER / 2), Cam(t + SHUTTER / 2)
    move = 0.0
    for P in PROBES:
        x0, y0, z0 = a.project(P); x1, y1, z1 = b.project(P)
        if z0 > 0.3 and z1 > 0.3:
            move = max(move, math.hypot(x1 - x0, y1 - y0))
    return int(min(7, max(1, math.ceil(move / 7))))


def render_at(t):
    n = subframes(t)
    if n == 1:
        acc = scene(t)
    else:
        acc = sum(scene(t + (k + 0.5) / n * SHUTTER - SHUTTER / 2) for k in range(n)) / n
    cards(acc, t)
    # vignette + fine grain (dither for the night gradients)
    acc *= VIGNETTE
    acc += np.random.default_rng(int(t * FPS)).normal(0, 1.6, (H, W, 1))
    return np.clip(acc, 0, 255).astype(np.uint8)


_vy, _vx = np.mgrid[0:H, 0:W]
VIGNETTE = (1 - 0.38 * (((_vx - W / 2) / (W * 0.75)) ** 2 + ((_vy - H / 2) / (H * 0.7)) ** 2))[..., None].astype(np.float32)


def frame_bytes(i):
    return render_at(i / FPS).tobytes()


if __name__ == '__main__':
    frames.cli(render_at, frame_bytes, W, H, FPS, int(DUR * FPS))
