"""Финальная картинка: 3D-проход (build/scene) + слова по одному + титры + подписи моделей
+ центральная пауза RubUp. Кадр — функция времени; содержание и реклама из events.py."""
import functools
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import banner
import frames
import fx
import layout
import config
from script import ROLE_COLORS, ACCENTS
from events import DUR, AD_STOP, TITLES, LABELS, WORDS

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([AD_STOP], cy=H / 2)
N_SCENE = int(round(DUR * FPS))
SCENE = HERE / 'build' / 'scene'
WHITE, YELLOW = (255, 255, 255), (255, 225, 77)
MAX_W = 980


@functools.lru_cache(None)
def word_sprite(text, size, color, stroke):
    """Готовый спрайт: кегль подбирается один раз под ширину, обводка и мягкая тень."""
    text = text.replace('_', ' ')
    while True:
        l, t, r, b = layout.ink(text, size, 'Heavy')
        if r - l + 2 * stroke <= MAX_W or size <= 40:
            break
        size -= 2
    f = fx.font('Heavy', size)
    pad = stroke + 24
    w, h = int(r - l) + 2 * pad, int(b - t) + 2 * pad
    org = (pad - l, pad - t)
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((org[0], org[1] + 6), text, font=f, anchor='ls', fill=(0, 0, 0, 160), stroke_width=stroke, stroke_fill=(0, 0, 0, 160))
    im = sh.filter(ImageFilter.GaussianBlur(6))
    ImageDraw.Draw(im).text(org, text, font=f, anchor='ls', fill=color + (255,), stroke_width=stroke, stroke_fill=(8, 8, 12, 255))
    return im


def place(canvas, spr, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.003:
        return
    if abs(scale - 1) > 0.003:
        spr = spr.resize((max(1, round(spr.width * scale)), max(1, round(spr.height * scale))), Image.BICUBIC)
    if alpha < 0.997:
        spr = spr.copy()
        spr.putalpha(spr.getchannel('A').point(lambda v: int(v * alpha)))
    canvas.alpha_composite(spr, (int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))))


def _vignette():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.40 * np.clip(d - 0.45, 0, 1) ** 1.6)[..., None].astype(np.float32)


VIG = _vignette()
PALETTE = [WHITE, YELLOW, (92, 225, 255), WHITE, (124, 255, 107)]


def scene_at(c):
    """3D-кадр для времени содержания c; между кадрами сетки (торможение перед рекламой) — смешение."""
    f = min(max(c * FPS, 0), N_SCENE - 1)
    i0 = int(f); a = f - i0
    img = np.asarray(Image.open(SCENE / f'f{i0:05d}.png').convert('RGB'), np.float32)
    if a > 0.02 and i0 + 1 < N_SCENE:
        img = img * (1 - a) + np.asarray(Image.open(SCENE / f'f{i0 + 1:05d}.png').convert('RGB'), np.float32) * a
    return img


def word_color(k, w, style):
    if style == 'role':
        return ROLE_COLORS.get(w, WHITE)
    for key, col in ACCENTS.items():
        if key in w:
            return col
    return PALETTE[k % len(PALETTE)]


def render_at(c):
    base = scene_at(c) * VIG
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
    # титры блоков
    for t0, t1, small, big in TITLES:
        k = fx.clamp01((c - t0) / 0.45) * (1 - fx.clamp01((c - t1) / 0.3))
        if k > 0:
            e = fx.ease_out(fx.clamp01((c - t0) / 0.45))
            place(im, word_sprite(small, 42, YELLOW, 6), 540, 236 - 20 * (1 - e), 1, k)
            place(im, word_sprite(big, 100, WHITE, 10), 540, 330 - 34 * (1 - e), 1, k)
    # подписи моделей
    for t0, t1, text in LABELS:
        k = fx.clamp01((c - t0) / 0.35) * (1 - fx.clamp01((c - t1) / 0.3))
        if k > 0:
            place(im, fx.solid_pill(text, (18, 18, 24), 34), 540, 1560 + 24 * (1 - fx.ease_out(fx.clamp01((c - t0) / 0.35))), 1, k * 0.92)
    # слова по одному
    for k, (w, t0, t1, style) in enumerate(WORDS):
        if t0 - 0.02 <= c < t1:
            u = (c - t0) / 0.14
            s = 0.72 + 0.28 * fx.ease_out_back(fx.clamp01(u), 2.2) if u < 1 else 1.0
            a = fx.clamp01((c - t0 + 0.02) / 0.06) * (1 - fx.clamp01((c - t1 + 0.06) / 0.06))
            role = style == 'role'
            size = 168 if role else (108 if any(key in w for key in ACCENTS) else 92)
            place(im, word_sprite(w, size, word_color(k, w, style), 12 if role else 9), 540, 1330 if role else 1300, s, a)
    return np.asarray(im.convert('RGB'))


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
