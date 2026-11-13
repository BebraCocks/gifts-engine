"""Проба: появление Морфеуса из зелёных строк (~2 с, с зажатыми кулаками), затем кулаки раскрываются.
python -B test_intro.py -> build/review/intro_sheet.png, intro_test.mp4 (30 к/с, 540×960, без звука), sprites_sheet.png"""
import math
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image
import fx
import matrix
import character as ch

W, H = 1080, 1920
fx.set_frame(W, H)
GREEN = np.array((0, 175, 70), np.float32)
INTRO = 2.0


def page(t):
    bg = matrix.rain_bg(t, cell=26, seed=0)
    c = np.empty((H, W, 3), np.float32)
    c[:] = 255
    c *= (1 - 0.075 * bg)[..., None]                     # «едва видимые» серые 0/1
    return c


def green_rain(c, t):
    """Full-screen green code pouring down while the figure forms; gone by the end of the intro."""
    env = fx.smooth(t / 0.18) * (1 - fx.smooth((t - 1.05) / 0.85))
    if env <= 0.003:
        return
    g = matrix.rain_bg(t, cell=22, seed=3, speed_px=(700, 600), period=14.0, gaps=0.35)
    k = (g * env * 0.85)[..., None]
    c[:] = c * (1 - k) + GREEN * k


def scaled(im, s):
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


HEAD_IM = scaled(*ch.head('calm'))
FIST_IM = [scaled(*ch.hand(side, 'fist')) for side in (0, 1)]
matrix.register('head', HEAD_IM)
matrix.register('fist0', FIST_IM[0])
matrix.register('fist1', FIST_IM[1])


def place_np(c, arr, cx, cy):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    fx.over(c, fx.warp(im, cx, cy, 1.0))


FACES = [(0, 'calm'), (3.35, 'over_glasses'), (4.3, 'calm')]
HEAD_G = [('nod', 2.65)]
POSES = [(0, 'fist'), (2.55, 'half'), (2.68, 'open')]
HAND_G = [('shake', 2.0, 'both'), ('offer', 2.68, 'both')]


def frame(t):
    c = page(t)
    green_rain(c, t)
    specs = [('head', ch.HEAD_POS, 0.12, 1.75), ('fist0', ch.HAND_POS[0], 0.28, 1.6), ('fist1', ch.HAND_POS[1], 0.36, 1.55)]
    for key, (px, py), t0, dur in specs:
        if t < t0 + dur:
            arr, _ = matrix.assemble(t, key, t0, dur, seed={'head': 1, 'fist0': 2, 'fist1': 3}[key])
            if key == 'head':
                dx, dy, rot, sc = ch.head_motion(t, ())
            else:
                dx, dy, rot, sc = ch.hand_motion(t, 0 if key == 'fist0' else 1, ())
            place_np(c, arr, px + dx, py + dy)
        else:
            if key == 'head':
                ch.draw_head(c, t, FACES, HEAD_G, glints=(1.95,))
            else:
                side = 0 if key == 'fist0' else 1
                ch.draw_hand(c, t, side, POSES, HAND_G)
    return np.clip(c, 0, 255).astype(np.uint8)


def sprites_sheet():
    c = page(0.0)
    cols = [(180, 'calm'), (540, 'smirk'), (900, 'brow')]
    for x, n in cols:
        ch.draw_head(c, 0.0, [(0, n)], pos=(x, 330), extra_sc=0.62)
    for x, n in zip((180, 540, 900), ('over_glasses', 'wince', 'surprise')):
        ch.draw_head(c, 0.0, [(0, n)], pos=(x, 760), extra_sc=0.62)
    poses = ch.POSES
    for k, p in enumerate(poses):
        y = 1130 + (k // 4) * 330
        x = 140 + (k % 4) * 267
        ch.draw_hand(c, 0.0, 0, [(0, p)], pos=(x, y), extra_sc=0.55)
    Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save('build/review/sprites_sheet.png')


if __name__ == '__main__':
    rev = paths.build(HERE) / 'review'
    rev.mkdir(parents=True, exist_ok=True)
    sprites_sheet()
    ts = [0.15, 0.45, 0.75, 1.05, 1.35, 1.65, 1.95, 2.6, 3.6]
    ims = [Image.fromarray(frame(t)).resize((270, 480), Image.LANCZOS) for t in ts]
    sheet = Image.new('RGB', (270 * len(ims), 480))
    for k, im in enumerate(ims):
        sheet.paste(im, (k * 270, 0))
    sheet.save(rev / 'intro_sheet.png')
    Image.fromarray(frame(1.05)).save(rev / 'intro_105.png')
    if '--video' in sys.argv:
        fps, dur = 30, 4.6
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960',
                              '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                              str(rev / 'intro_test.mp4')], stdin=subprocess.PIPE)
        for i in range(int(dur * fps)):
            p.stdin.write(np.asarray(Image.fromarray(frame(i / fps)).resize((540, 960), Image.BILINEAR)).tobytes())
        p.stdin.close()
        p.wait()
    print('ok')
