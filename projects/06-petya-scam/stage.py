"""A small 3D stage: perspective camera + textured planes and billboards (PIL), so camera moves give real
parallax and perspective (the counter top, the swinging safe door, gifts standing on the counter).

World: metres, y up, the camera looks roughly along +z. Everything is a pure function of the camera, so a
frame depends only on time.
"""
import math

import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1920


def _norm(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


class Cam:
    def __init__(self, eye, target, fov=38.0, roll=0.0):
        self.e = np.asarray(eye, np.float64)
        f = _norm(np.asarray(target, np.float64) - self.e)
        r = _norm(np.cross([0, 1, 0], f))
        up = np.cross(f, r)
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            r, up = r * c + up * s, up * c - r * s
        self.f, self.r, self.up = f, r, up
        self.k = (H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, p):
        q = np.asarray(p, np.float64) - self.e
        z = float(q @ self.f)
        if z < 0.05:
            return None
        return W / 2 + float(q @ self.r) / z * self.k, H / 2 - float(q @ self.up) / z * self.k, z

    def depth(self, p):
        return float((np.asarray(p, np.float64) - self.e) @ self.f)


def _coeffs(dst, src):
    """PIL PERSPECTIVE coefficients mapping output (dst) points to input (src) points."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b += [u, v]
    return np.linalg.solve(np.asarray(A, np.float64), np.asarray(b, np.float64)).tolist()


def quad(canvas, tex, corners, cam, alpha=1.0, blur=0.0):
    """Draw RGBA texture onto the 3D quad corners = [top-left, top-right, bottom-right, bottom-left]."""
    pr = [cam.project(c) for c in corners]
    if any(p is None for p in pr):
        return
    pts = [(p[0], p[1]) for p in pr]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, y0 = max(0, int(math.floor(min(xs))) - 2), max(0, int(math.floor(min(ys))) - 2)
    x1, y1 = min(W, int(math.ceil(max(xs))) + 2), min(H, int(math.ceil(max(ys))) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    tw, th = tex.size
    local = [(x - x0, y - y0) for x, y in pts]
    try:
        c = _coeffs(local, [(0, 0), (tw, 0), (tw, th), (0, th)])
    except np.linalg.LinAlgError:
        return
    im = tex.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, c, Image.BICUBIC)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1.0:
        a = im.getchannel('A').point(lambda v: int(v * alpha))
        im.putalpha(a)
    canvas.alpha_composite(im, (x0, y0))


def billboard(canvas, im, pos, height, cam, anchor=(0.5, 1.0), alpha=1.0, blur=0.0, rot=0.0, min_px=4):
    """Upright sprite of world `height` standing at pos (anchor = point of the sprite at pos).
    Returns (x, y, scale) on screen or None."""
    p = cam.project(pos)
    if p is None:
        return None
    x, y, z = p
    hpx = height * cam.k / z
    s = hpx / im.height
    w, h = max(1, int(round(im.width * s))), max(1, int(round(im.height * s)))
    if w < min_px or h < min_px:
        return None
    if x + w < -50 or x - w > W + 50 or y + h < -50 or y - h > H + 50:
        return x, y, s
    spr = im.resize((w, h), Image.BICUBIC if s > 1 else Image.LANCZOS)
    if rot:
        spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
        w, h = spr.size
    if blur > 0.3:
        spr = spr.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1.0:
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * alpha)))
    canvas.alpha_composite(spr, (int(round(x - anchor[0] * w)), int(round(y - anchor[1] * h)))) \
        if _inside(x - anchor[0] * w, y - anchor[1] * h, w, h) else _paste_clip(canvas, spr, x - anchor[0] * w,
                                                                                y - anchor[1] * h)
    return x, y, s


def _inside(x, y, w, h):
    return x >= 0 and y >= 0 and x + w <= W and y + h <= H


def _paste_clip(canvas, spr, x, y):
    x, y = int(round(x)), int(round(y))
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(spr.width, W - x), min(spr.height, H - y)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    canvas.alpha_composite(spr.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))
