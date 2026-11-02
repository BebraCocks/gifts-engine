"""01-durovs-cap: title with the original cap, RubUp pause, then three random models side by side."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import banner
import frames
import fx
from fx import smooth, ease_out, spring, warp, over
import gifts_api
import lottie
import config
from timeline import DUR, ON, END
from events import AD_STOP

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([AD_STOP], cy=H/2)
GIFT = config.GIFT_NAME
HERO = str(gifts_api.original_file(GIFT, 'json'))
MODELS = [(name, rarity, str(gifts_api.model_file(GIFT, name, 'json')), glow)
          for name, rarity, glow in config.MODELS]

# background: vertical gradient, computed once
_y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
BG = (np.array(config.BG_TOP, np.float32) * (1 - _y) + np.array(config.BG_BOTTOM, np.float32) * _y)
BG = np.repeat(BG, W, axis=1)

SWAP = ON[1] - 0.15            # scene B begins right after the ad pause


def text(canvas, s, size, weight, color, cx, cy, alpha=1.0, scale=1.0, dy=0.0):
    im = fx.text_img(((s, color),), size, weight)
    over(canvas, warp(im, cx, cy + dy, scale), alpha)


def glow(canvas, cx, cy, size, rgb, alpha):
    over(canvas, warp(fx.radial(256, rgb, power=2.2), cx, cy, size / 256), alpha, add=True)


def scene_a(c, t):
    k_in = spring(t - 0.3, f=1.6, z=0.55)
    k_out = smooth((t - (SWAP - 0.1)) / 0.35)
    a = (1 - k_out)
    if a <= 0.01:
        return
    text(c, "Durov's Cap", 104, 'Heavy', (255, 255, 255), W/2, 360, a * smooth((t - 0.3) / 0.3), dy=40 * (1 - k_in))
    text(c, 'коллекционный подарок Telegram', 44, 'Medium', (170, 182, 205), W/2, 470,
         a * smooth((t - 0.5) / 0.3), dy=30 * (1 - spring(t - 0.5, f=1.6, z=0.55)))
    s = 0.6 + 0.4 * k_in - 0.35 * k_out
    glow(c, W/2, 1000, 1100 * s, (90, 140, 255), 0.35 * a)
    cap = lottie.frame(HERO, t, size=720)
    over(c, warp(cap, W/2, 1000 + 120 * (1 - k_in) - 80 * k_out, s), a * smooth((t - 0.25) / 0.25))


def scene_b(c, t):
    u = t - SWAP
    if u <= 0:
        return
    text(c, 'Три модели', 104, 'Heavy', (255, 255, 255), W/2, 360, smooth(u / 0.3),
         dy=40 * (1 - spring(u, f=1.6, z=0.55)))
    for k, (name, rarity, path, rgb) in enumerate(MODELS):
        uk = u - 0.15 - 0.15 * k
        if uk <= 0:
            continue
        cx, cy = 190 + 350 * k, 1000
        sp = spring(uk, f=1.8, z=0.5)
        glow(c, cx, cy, 560 * sp, rgb, 0.45)
        cap = lottie.frame(path, uk + 0.4 * k, size=340)        # full forward cycle, staggered phase
        over(c, warp(cap, cx, cy + 90 * (1 - sp), max(0.01, sp)), smooth(uk / 0.2))
        text(c, name, 40, 'Semibold', (255, 255, 255), cx, 1225, smooth((uk - 0.1) / 0.25),
             dy=20 * (1 - ease_out((uk - 0.1) / 0.4)))
        pill = fx.solid_pill(f'{rarity}%'.replace('.', ','), tuple(int(v * 0.55) for v in rgb), 34)
        over(c, warp(pill, cx, 1300, 1.0), smooth((uk - 0.2) / 0.25))
    text(c, 'редкость моделей · api.changes.tg · 02.11.2026', 28, 'Regular', (120, 130, 150), W/2, 1720,
         0.9 * smooth((u - 0.6) / 0.4))


def render_at(t):
    c = BG.copy()
    scene_a(c, t)
    scene_b(c, t)
    end_fade = smooth((t - (DUR - 0.25)) / 0.25)
    if end_fade > 0:
        c *= 1 - end_fade
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i/FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
