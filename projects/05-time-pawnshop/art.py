"""Vector-style drawing helpers on supersampled RGBA layers (PIL), used by characters and sets.

Layer(w, h, ss): coordinates are in output pixels; everything is drawn at ss× and `.image()` downsamples
with LANCZOS, so edges are smooth. Shapes can be clipped to an earlier shape mask (`clip=`), which gives
clean cel shading: draw the base, then a darker shape clipped to it.
"""
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


def bez(p0, p1, p2, p3, n=18):
    out = []
    for k in range(n + 1):
        t = k / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def smooth_closed(pts, n=10, tension=0.5):
    """Closed Catmull-Rom spline through pts -> dense polygon."""
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        out.extend(bez(p1, c1, c2, p2, n)[:-1])
    return out


def smooth_open(pts, n=10, tension=0.5):
    out = []
    m = len(pts)
    for i in range(m - 1):
        p0, p1, p2 = pts[max(0, i - 1)], pts[i], pts[i + 1]
        p3 = pts[min(m - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) * tension / 3, p1[1] + (p2[1] - p0[1]) * tension / 3)
        c2 = (p2[0] - (p3[0] - p1[0]) * tension / 3, p2[1] - (p3[1] - p1[1]) * tension / 3)
        out.extend(bez(p1, c1, c2, p2, n)[:-1])
    out.append(pts[-1])
    return out


def ellipse_pts(cx, cy, rx, ry, rot=0.0, n=64):
    c, s = math.cos(rot), math.sin(rot)
    return [(cx + rx * math.cos(a) * c - ry * math.sin(a) * s, cy + rx * math.cos(a) * s + ry * math.sin(a) * c)
            for a in np.linspace(0, 2 * math.pi, n, endpoint=False)]


class Layer:
    def __init__(self, w, h, ss=3, bg=None):
        self.w, self.h, self.ss = w, h, ss
        self.im = Image.new('RGBA', (w * ss, h * ss), (0, 0, 0, 0) if bg is None else tuple(bg) + (255,))
        self.ox = self.oy = 0.0
        self.k = 1.0

    # transform: output = origin + k * local
    def at(self, ox, oy, k=1.0):
        self.ox, self.oy, self.k = ox, oy, k
        return self

    def P(self, p):
        return ((self.ox + p[0] * self.k) * self.ss, (self.oy + p[1] * self.k) * self.ss)

    def mask(self, pts):
        m = Image.new('L', self.im.size, 0)
        ImageDraw.Draw(m).polygon([self.P(p) for p in pts], fill=255)
        return m

    def fill(self, m, rgb, alpha=1.0, clip=None, blur=0.0):
        if clip is not None:
            m = ImageChops.multiply(m, clip)
        if blur:
            m = m.filter(ImageFilter.GaussianBlur(blur * self.ss * self.k))
        if alpha < 1.0:
            m = m.point(lambda v: int(v * alpha))
        col = Image.new('RGBA', self.im.size, tuple(int(c) for c in rgb) + (255,))
        if clip is None and alpha >= 1.0:
            self.im.paste(col, (0, 0), m)
        else:
            self.im = Image.composite(col, self.im, m) if self._opaque_under(m) else self._over(col, m)
        return m

    def _opaque_under(self, m):
        return False

    def _over(self, col, m):
        col.putalpha(m)
        out = self.im.copy()
        out.alpha_composite(col)
        return out

    def poly(self, pts, rgb, alpha=1.0, clip=None, blur=0.0):
        return self.fill(self.mask(pts), rgb, alpha, clip, blur)

    def shape(self, pts, rgb, **kw):
        """Smooth closed shape through control points."""
        return self.poly(smooth_closed(pts), rgb, **kw)

    def ell(self, cx, cy, rx, ry, rgb, rot=0.0, **kw):
        return self.poly(ellipse_pts(cx, cy, rx, ry, rot), rgb, **kw)

    def stroke(self, pts, width, rgb, alpha=1.0, clip=None, smooth=True, blur=0.0):
        """Round-capped polyline (smoothed through the points)."""
        q = smooth_open(pts) if smooth and len(pts) > 2 else pts
        m = Image.new('L', self.im.size, 0)
        d = ImageDraw.Draw(m)
        w = max(1, int(width * self.k * self.ss))
        qq = [self.P(p) for p in q]
        d.line(qq, fill=255, width=w, joint='curve')
        r = w / 2
        for p in (qq[0], qq[-1]):
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)
        return self.fill(m, rgb, alpha, clip, blur)

    def image(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def lerp(a, b, t):
    return a + (b - a) * t


def mixc(c1, c2, t):
    return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))


def shade(c, k=0.82, hue=(40, 20, 70)):
    """Darker, slightly cooler version of a colour (cel shadow)."""
    return tuple(int(min(255, max(0, v * k + h * (1 - k) * 0.35))) for v, h in zip(c, hue))
