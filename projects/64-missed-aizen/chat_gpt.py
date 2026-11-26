"""Scene-3 chat from the ChatGPT screenshots: empty chat + bubbles cut from the full one.

    frame = chat_frame(n)   # RGB 941x1672, first n bubbles visible (n = 0..8), Missed's original avatar
Bubble k pops in with chat_frame(n, pop=(k, t)) where t in 0..1 is the entry progress.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as nd

HERE = Path(__file__).resolve().parent
REFS = HERE / "refs"

# (side, x, y, w, h) measured on refs/chat_scene3.png, top to bottom
BOXES = [
    ("out", 215, 266, 711, 158), ("in", 17, 460, 255, 102),
    ("out", 382, 590, 542, 99), ("in", 17, 718, 255, 101),
    ("out", 230, 849, 696, 157), ("in", 16, 1043, 257, 103),
    ("out", 147, 1177, 778, 100), ("in", 17, 1311, 282, 102),
]
AVATAR = (200, 125, 60)  # centre x, y and radius on refs/chat_empty.png


@lru_cache(None)
def _sprites():
    full = Image.open(REFS / "chat_scene3.png").convert("RGB")
    x = np.asarray(full).astype(int)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    out_m = (abs(r - g) < 8) & (abs(g - b) < 8) & (r > 185) & (r < 215)
    in_m = (r - g > 40) & (r > 150)
    res = []
    for side, bx, by, bw, bh in BOXES:
        p = 16  # room for the tail
        x0, y0 = max(0, bx - p), max(0, by - p)
        x1, y1 = min(full.width, bx + bw + p), min(full.height, by + bh + p)
        m = (out_m if side == "out" else in_m)[y0:y1, x0:x1]
        m = nd.binary_closing(m, iterations=6)
        m = nd.binary_fill_holes(m)
        lab, n = nd.label(m)
        if n > 1:
            sizes = nd.sum(m, lab, range(1, n + 1))
            m = lab == (np.argmax(sizes) + 1)
        m = nd.binary_dilation(m, iterations=1)
        alpha = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.9))
        spr = full.crop((x0, y0, x1, y1)).convert("RGBA")
        spr.putalpha(alpha)
        res.append((side, x0, y0, spr))
    return res


@lru_cache(None)
def _base():
    base = Image.open(REFS / "chat_empty.png").convert("RGBA")
    cx, cy, rad = AVATAR
    src = Image.open(REFS / "missed.jpg").convert("RGB")
    d = 2 * rad
    face = src.crop((330 - 215, 290 - 215, 330 + 215, 290 + 215)).resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d * 4, d * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    base.paste(face, (cx - rad, cy - rad), mask.resize((d, d), Image.LANCZOS))
    return base


def _shadow(spr):
    a = spr.getchannel("A").filter(ImageFilter.GaussianBlur(8))
    sh = Image.new("RGBA", spr.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: int(v * 0.55)))
    return sh


def chat_frame(n, pop=None):
    img = _base().copy()
    for k, (side, x0, y0, spr) in enumerate(_sprites()[:n]):
        s = spr
        if pop and pop[0] == k:
            t = max(0.0, min(1.0, pop[1]))
            e = 1 - (1 - t) ** 3
            sc = 0.6 + 0.4 * e + 0.06 * np.sin(np.pi * e)  # soft overshoot
            w, h = max(1, int(spr.width * sc)), max(1, int(spr.height * sc))
            s = spr.resize((w, h), Image.LANCZOS)
            s.putalpha(s.getchannel("A").point(lambda v: int(v * e)))
            ax = x0 + (spr.width - w if side == "out" else 0)
            ay = y0 + spr.height - h
            img.alpha_composite(_shadow(s), (ax + 3, ay + 6))
            img.alpha_composite(s, (ax, ay))
            continue
        img.alpha_composite(_shadow(s), (x0 + 3, y0 + 6))
        img.alpha_composite(s, (x0, y0))
    return img.convert("RGB")


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "build" / "chat_gpt_preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    a, b = chat_frame(5), chat_frame(8, pop=(7, 0.55))
    strip = Image.new("RGB", (a.width * 2 + 20, a.height), (255, 255, 255))
    strip.paste(a, (0, 0))
    strip.paste(b, (a.width + 20, 0))
    strip.save(out)
    print(out)
