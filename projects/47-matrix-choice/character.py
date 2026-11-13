"""Морфеус: только голова и две ладони (автор). Спрайты — assets/sprites/ (cut_sheets.py + фото автора).

Голова: выражения HEADS (calm — фото автора; остальные — лист Fish Audio). Ладони: позы POSES, правая — зеркало левой.
Движение кодом, без новых картинок:
- idle: медленное «дыхание» головы (вверх-вниз 4 px, лёгкий наклон), ладони парят в противофазе;
- nod / tilt / shake: короткие жесты головы (пружина);
- glint: блик, пробегающий по очкам слева направо;
- смена выражения и позы — кроссфейд 0,12 с с маленьким «пружинным» масштабом (живое, а не склейка).
Всё — функция времени: draw(c, t, state), где state — словарь (выражение, позы, жесты с их временем).
"""
import functools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import fx

HERE = Path(__file__).resolve().parent
SP = HERE / 'assets' / 'sprites'
HEADS = ['calm', 'smirk', 'brow', 'over_glasses', 'surprise']   # 'wince' есть в assets, но не используется:
# автор (2026-11-13) — персонаж серьёзный, прилёты предметов в голову оскорбительны; гэги референса не копировать
POSES = ['open', 'fist', 'half', 'cup', 'hold', 'down', 'point']

HEAD_W = 430.0                  # on-screen head width, px
HAND_W = 400.0                  # on-screen width of the open palm, px
HEAD_POS = (540.0, 600.0)
HAND_POS = ((268.0, 1262.0), (812.0, 1262.0))      # screen-left = NFT (blue), screen-right = real thing (red)


SHEET2 = {'blow', 'look_left', 'look_right', 'look_up', 'talk_a', 'talk_o'}


@functools.lru_cache(None)
def head(name):
    """One scale per Fish sheet (heads inside a sheet share their size): sheet 1 by its calm head, sheet 2 by its
    frontal talking head, so turned heads keep their real (narrower) width."""
    im = Image.open(SP / f'head_{name}.png').convert('RGBA')
    ref = 434.0 if name in SHEET2 else 454.0
    return im, HEAD_W / ref


@functools.lru_cache(None)
def agent(name):
    im = Image.open(SP / f'agent_{name}.png').convert('RGBA')
    return im


@functools.lru_cache(None)
def hand(side, pose):
    s = 'L' if side == 0 else 'R'
    im = Image.open(SP / (f'hand_{s}.png' if pose == 'open' else f'hand_{s}_{pose}.png')).convert('RGBA')
    ref = 559.0 if pose == 'open' else 522.0           # sheet hands: their «half» pose = the author's open palm
    return im, HAND_W / ref


@functools.lru_cache(None)
def glint_mask(name):
    """Lens area of the head sprite (dark, low-saturation pixels in the glasses band) for the moving highlight."""
    im, _ = head(name)
    a = np.asarray(im).astype(np.float32)
    h = a.shape[0]
    band = np.zeros(a.shape[:2], bool)
    band[int(h * 0.36):int(h * 0.56)] = True
    dark = (a[..., :3].max(-1) < 70) & (a[..., 3] > 200) & band
    from scipy import ndimage
    dark = ndimage.binary_opening(dark, iterations=2)
    return dark


def _cross(c, items, cx, cy, sc, rot, a):
    """items: [(image, weight)] drawn on top of each other (crossfade)."""
    for im, w in items:
        if w > 0.004:
            fx.over(c, fx.warp(im, cx, cy, sc, sc, rot), a * w)


def _mix(seq, t, dur=0.12):
    """seq: [(t_start, name)] sorted. -> [(name, weight)] crossfading over dur."""
    cur, prev, t_sw = seq[0][1], None, -9.0
    for ts, n in seq:
        if t >= ts and n != cur:
            prev, cur, t_sw = cur, n, ts
        elif t >= ts:
            cur = n
    k = fx.smooth((t - t_sw) / dur) if prev else 1.0
    # the old pose stays opaque underneath while the new one fades in (no see-through ghost), then goes
    return ([(prev, 1 - fx.smooth((k - 0.75) / 0.25))] if prev and k < 1 else []) + [(cur, k if prev else 1.0)], t_sw


def head_motion(t, gestures):
    """(dx, dy, rot rad, scale) from idle breathing + gestures [(kind, t0)]."""
    dy = 4.0 * math.sin(t * 2 * math.pi / 3.2)
    rot = 0.012 * math.sin(t * 2 * math.pi / 4.7 + 1.0)
    dx, sc = 0.0, 1.0
    for kind, t0 in gestures:
        u = t - t0
        if u <= 0 or u > 2.0:
            continue
        if kind == 'nod':                      # down-up, serious
            dy += 22 * fx.bump(u, 1.6, 4.0)
        elif kind == 'tilt':                   # questioning tilt, holds then returns
            rot += 0.09 * (fx.spring(u, 1.4, 0.5) - fx.spring(u - 1.1, 1.4, 0.6))
        elif kind == 'shake':                  # «нет»
            dx += 16 * fx.bump(u, 3.2, 3.5)
            rot += 0.02 * fx.bump(u, 3.2, 3.5)
        elif kind == 'lean':                   # leans in to look closer
            sc *= 1 + 0.06 * (fx.spring(u, 1.2, 0.6) - fx.spring(u - 1.2, 1.2, 0.6))
            dy += 18 * (fx.spring(u, 1.2, 0.6) - fx.spring(u - 1.2, 1.2, 0.6))
    return dx, dy, rot, sc


def draw_head(c, t, faces, gestures=(), glints=(), a=1.0, pos=HEAD_POS, extra_sc=1.0):
    dx, dy, rot, sc = head_motion(t, gestures)
    items, t_sw = _mix(faces, t)
    pop = 1 + 0.025 * fx.bump(t - t_sw, 2.6, 6.0)
    for name, w in items:
        im, s = head(name)
        fx.over(c, fx.warp(im, pos[0] + dx, pos[1] + dy, s * sc * pop * extra_sc, None, rot), a * w)
    for g0 in glints:                          # a highlight sweeps over the lenses
        u = (t - g0) / 0.45
        if 0 < u < 1:
            name = items[-1][0]
            im, s = head(name)
            m = glint_mask(name)
            hh, ww = m.shape
            yy, xx = np.mgrid[:hh, :ww]
            x = -0.2 * ww + u * 1.4 * ww
            band = np.clip(1 - np.abs((xx - x) + 0.5 * (yy - hh * 0.45)) / 22.0, 0, 1) * m
            gl = np.zeros((hh, ww, 4), np.uint8)
            gl[..., :3] = 255
            gl[..., 3] = (band * 200 * math.sin(math.pi * u)).astype(np.uint8)
            gim = Image.fromarray(gl).filter(ImageFilter.GaussianBlur(2))
            fx.over(c, fx.warp(gim, pos[0] + dx, pos[1] + dy, s * sc * pop * extra_sc, None, rot), a, add=True)


def hand_motion(t, side, gestures):
    ph = 0.0 if side == 0 else math.pi
    dy = 5.0 * math.sin(t * 2 * math.pi / 3.2 + ph + 1.6)
    rot = 0.015 * math.sin(t * 2 * math.pi / 3.9 + ph)
    dx, sc = 0.0, 1.0
    for kind, t0, s in gestures:
        if s not in (side, 'both'):
            continue
        u = t - t0
        if u <= 0 or u > 2.0:
            continue
        if kind == 'offer':                    # pushes the item towards the viewer
            sc *= 1 + 0.08 * fx.bump(u, 1.8, 3.5)
            dy -= 20 * fx.bump(u, 1.8, 3.5)
        elif kind == 'weigh':                  # weighing: small bounce
            dy += 14 * fx.bump(u, 2.4, 3.0)
        elif kind == 'drop':                   # the loser's hand sinks (a heavy feeling is lost)
            dy += 40 * fx.smooth(u / 0.4) * (1 - fx.smooth((u - 1.2) / 0.5))
        elif kind == 'shake':                  # fists trembling
            dx += 4 * math.sin(u * 2 * math.pi * 11) * math.exp(-u * 1.2)
    return dx, dy, rot, sc


def draw_hand(c, t, side, poses, gestures=(), a=1.0, pos=None, extra_sc=1.0):
    px, py = pos or HAND_POS[side]
    dx, dy, rot, sc = hand_motion(t, side, gestures)
    items, t_sw = _mix(poses, t, 0.10)
    pop = 1 + 0.05 * fx.bump(t - t_sw, 2.8, 6.0)        # a pose change «springs»
    for name, w in items:
        im, s = hand(side, name)
        fx.over(c, fx.warp(im, px + dx, py + dy, s * sc * pop * extra_sc, None, rot if side == 0 else -rot), a * w)
