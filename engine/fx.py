"""Shared motion + compositing toolkit for project renderers (vertical 1080x1920 by default).

    import fx
    from fx import smooth, ease_out, bump, keys, catmull, window, spring, warp, over, draw_rgba
    fx.set_frame(1080, 1920)

Everything is a pure function of time / parameters, so frames stay deterministic.
"""
import functools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import paths

W, H = 1080, 1920


def set_frame(w, h):
    global W, H
    W, H = w, h


# ------------------------------------------------------------------ easing / springs
def clamp01(x):
    return min(1.0, max(0.0, x))


def smooth(x):
    x = clamp01(x)
    return x * x * x * (x * (x * 6 - 15) + 10)


def ease_out(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp01(x)
    return x ** 3


def ease_out_back(x, s=1.4):
    x = clamp01(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def spring(x, f=2.2, z=0.45):
    if x <= 0:
        return 0.0
    w = 2 * math.pi * f
    wd = w * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


def bump(x, f=3.0, decay=6.0):
    """Damped wobble that starts at 0 (use for squash, jiggle, shake)."""
    return 0.0 if x <= 0 else math.exp(-decay * x) * math.sin(2 * math.pi * f * x)


def keys(t, v0, ks):
    """Spring keyframes: ks = [(time, value, freq, damping), ...]; values may be tuples."""
    v = np.array(v0, float)
    prev = np.array(v0, float)
    for ti, vi, f, z in ks:
        vi = np.array(vi, float)
        v = v + (vi - prev) * spring(t - ti, f, z)
        prev = vi
    return v


def catmull(t, ts, vals):
    vals = [np.asarray(v, float) for v in vals]
    if t <= ts[0]:
        return vals[0]
    if t >= ts[-1]:
        return vals[-1]
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    t0, t1 = ts[i], ts[i + 1]
    u = (t - t0) / (t1 - t0)
    p0, p1, p2 = vals[max(i - 1, 0)], vals[i], vals[i + 1]
    p3 = vals[min(i + 2, len(vals) - 1)]
    tm0, tm3 = ts[max(i - 1, 0)], ts[min(i + 2, len(ts) - 1)]
    m1 = (p2 - p0) / max(t1 - tm0, 1e-6) * (t1 - t0)
    m2 = (p3 - p1) / max(tm3 - t0, 1e-6) * (t1 - t0)
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2


def window(t, t_in, t_out, dout=0.3, f=2.4, z=0.55):
    """Spring-in at t_in, ease-out after t_out (0..~1.05)."""
    if t < t_in or t > t_out + dout:
        return 0.0
    a = spring(t - t_in, f, z)
    if t > t_out:
        a *= 1 - smooth((t - t_out) / dout)
    return a


def remap(t, pts):
    """Piecewise-linear time remap: pts = [(t_out, t_in), ...] sorted by t_out (slow-mo, freeze, rewind)."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if t <= xs[0]:
        return ys[0] + (t - xs[0])
    if t >= xs[-1]:
        return ys[-1] + (t - xs[-1])
    return float(np.interp(t, xs, ys))


# ------------------------------------------------------------------ compositing
def warp(img, cx, cy, sx, sy=None, rot_=0.0, anchor=None):
    """Affine-place an RGBA image so its anchor (default centre) lands at (cx, cy). -> (img, x0, y0)"""
    sy = sx if sy is None else sy
    iw, ih = img.size
    ax, ay = anchor if anchor else (iw / 2, ih / 2)
    if sx < 1e-3 or sy < 1e-3:
        return None
    c, s = math.cos(rot_), math.sin(rot_)
    A = np.array([[c * sx, -s * sy], [s * sx, c * sy]])
    corners = np.array([[0, 0], [iw, 0], [0, ih], [iw, ih]], float) - [ax, ay]
    pts = corners @ A.T + [cx, cy]
    x0, y0 = np.floor(pts.min(0)).astype(int) - 1
    x1, y1 = np.ceil(pts.max(0)).astype(int) + 1
    if x1 < 0 or y1 < 0 or x0 > W or y0 > H:
        return None
    Ai = np.linalg.inv(A)
    a, b = Ai[0]
    d, e = Ai[1]
    cc = ax - (a * (cx - x0) + b * (cy - y0))
    f = ay - (d * (cx - x0) + e * (cy - y0))
    return img.transform((x1 - x0, y1 - y0), Image.AFFINE, (a, b, cc, d, e, f), Image.BICUBIC), x0, y0


def over(canvas, placed, alpha=1.0, add=False):
    """Composite a placed RGBA onto a float32 canvas (H, W, 3|4). add=True -> additive light."""
    if placed is None or alpha <= 0.002:
        return
    im, x0, y0 = placed
    iw, ih = im.size
    if not add and im.mode == "RGBA":
        # 2026-11-09 speed-up: only the opaque part (alpha > 0) and only what lies on the canvas is converted to float.
        # Pixels with alpha 0 leave the canvas unchanged, so the result is bit-identical to compositing the whole image.
        bb = im.getbbox(alpha_only=True)
        if bb is None:
            return
        cx0, cy0 = max(bb[0], -x0), max(bb[1], -y0)
        cx1, cy1 = min(bb[2], canvas.shape[1] - x0), min(bb[3], canvas.shape[0] - y0)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        if (cx0, cy0, cx1, cy1) != (0, 0, iw, ih):
            im, x0, y0, iw, ih = im.crop((cx0, cy0, cx1, cy1)), x0 + cx0, y0 + cy0, cx1 - cx0, cy1 - cy0
    arr = np.asarray(im, np.float32) / 255
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(canvas.shape[1], x0 + iw), min(canvas.shape[0], y0 + ih)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    a = arr[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0]
    al = a[..., 3:4] * min(alpha, 1.0)
    reg = canvas[dy0:dy1, dx0:dx1]
    if add:
        reg[:, :, :3] = np.minimum(255, reg[:, :, :3] + a[..., :3] * 255 * al)
        return
    reg[:, :, :3] = reg[:, :, :3] * (1 - al) + a[..., :3] * 255 * al
    if canvas.shape[2] == 4:
        reg[:, :, 3:4] = reg[:, :, 3:4] * (1 - al) + al


def draw_rgba(box, fn):
    """Draw vector shapes with PIL at 2x into a frame-space box; fn(draw, map_xy, S). -> placed RGBA"""
    x0, y0, x1, y1 = (int(v) for v in box)
    if x1 <= x0 or y1 <= y0:
        return None
    S = 2
    im = Image.new("RGBA", ((x1 - x0) * S, (y1 - y0) * S), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), lambda x, y: ((x - x0) * S, (y - y0) * S), S)
    return im.resize((x1 - x0, y1 - y0), Image.LANCZOS), x0, y0


def fade(im, a):
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return im


# ------------------------------------------------------------------ text
@functools.lru_cache(None)
def font(weight, size, family="SF-Pro-Text"):
    return ImageFont.truetype(paths.font(f"{family}-{weight}.otf"), size)


@functools.lru_cache(None)
def text_img(parts, size, weight="Bold", shadow=False):
    """parts: tuple of (text, rgb). Single line, RGBA, tight."""
    f = font(weight, size)
    total = sum(f.getlength(s) for s, _ in parts)
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(total) + 16, asc + desc + 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 8
    for s, c in parts:
        if shadow:
            d.text((x, 11), s, font=f, fill=(0, 0, 0, 110))
        d.text((x, 8), s, font=f, fill=c + (255,))
        x += f.getlength(s)
    return im


# ------------------------------------------------------------------ plates


@functools.lru_cache(None)
def solid_pill(text, fill, size, tcol=(255, 255, 255), weight="Bold"):
    f = font(weight, size)
    tw = int(f.getlength(text))
    h_ = int(size * 1.7)
    w_ = tw + h_
    S = 2
    im = Image.new("RGBA", (w_ * S, h_ * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w_ * S - 1, h_ * S - 1], h_ * S // 2, fill=fill + (255,))
    d.text((w_ * S / 2, h_ * S / 2), text, font=font(weight, size * S), fill=tcol + (255,), anchor="mm")
    return im.resize((w_, h_), Image.LANCZOS)


@functools.lru_cache(None)
def soft_shadow(w_, h_, r_, blur=22, alpha=0.55):
    pad = blur * 2
    im = Image.new("L", (w_ + 2 * pad, h_ + 2 * pad), 0)
    ImageDraw.Draw(im).rounded_rectangle([pad, pad, pad + w_, pad + h_], r_, fill=255)
    im = im.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.putalpha(im.point(lambda v: int(v * alpha)))
    return out


@functools.lru_cache(None)
def rounded(w_, h_, r_, fill, outline=None, width=0):
    S = 2
    im = Image.new("RGBA", (w_ * S, h_ * S), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w_ * S - 1, h_ * S - 1], r_ * S, fill=fill,
                                         outline=outline, width=width * S)
    return im.resize((w_, h_), Image.LANCZOS)


@functools.lru_cache(None)
def radial(n, rgb, power=2.0, peak=1.0, ring=None):
    """Soft radial light sprite (n x n). ring=(radius 0..1, width, strength) adds a halo ring."""
    yy, xx = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.sqrt(xx ** 2 + yy ** 2) * 2
    a = np.clip(1 - r, 0, 1) ** power * peak
    if ring:
        a = a + np.exp(-((r - ring[0]) / ring[1]) ** 2) * ring[2]
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = rgb
    im[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(im, "RGBA")


def sparkle(d, cx, cy, r, fill):
    k = r * 0.3
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r), (cx - k, cy + k),
               (cx - r, cy), (cx - k, cy - k)], fill=fill)
