"""«Матрица» на белом: бледный фон из бегущих столбцов 0/1 и сборка персонажа из зелёных строк кода (~2 с).

Всё — чистые функции времени (детерминированно, без состояния между кадрами).

- rain_bg(t): почти невидимые серые столбцы 0/1 бегут вниз по белому фону (фон всего ролика).
- assemble(t, sprite, cx, cy, t0, ...): персонаж «проявляется» из кода:
    1) по силуэту спрайта падают зелёные струи (яркая голова + затухающий хвост);
    2) когда голова струи проходит клетку внутри силуэта, клетка «застывает» символом цвета картинки (зелёный тон);
    3) символы растворяются в настоящую фотографию по случайному порогу клетки, с зелёной кромкой;
  Возвращает RGBA-слой во весь кадр.
Глифы 0/1 рисуются моноширинным шрифтом и кешируются в assets/glyphs_<size>.png (не зависит от шрифтов системы).
"""
import functools
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1080, 1920
GREEN = np.array((20, 225, 90), np.float32)        # highlights of the picture
GREEN_DARK = np.array((0, 70, 30), np.float32)     # shadows (glasses) — dark, so the figure reads on white
MONO = ['/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf']
CHARS = '01'


@functools.lru_cache(None)
def glyphs(cell):
    """(len(CHARS), cell, cell) float masks 0..1."""
    f = HERE / 'assets' / f'glyphs_{cell}.png'
    if not f.exists():
        font = next((ImageFont.truetype(p, int(cell * 1.0)) for p in MONO if Path(p).exists()), None)
        sheet = Image.new('L', (cell * len(CHARS), cell), 0)
        d = ImageDraw.Draw(sheet)
        for k, ch in enumerate(CHARS):
            d.text((k * cell + cell / 2, cell / 2), ch, font=font, fill=255, anchor='mm')
        f.parent.mkdir(exist_ok=True)
        sheet.save(f)
    a = np.asarray(Image.open(f), np.float32) / 255
    return np.stack([a[:, k * cell:(k + 1) * cell] for k in range(len(CHARS))])


def tile(idx, cell):
    """Per-cell glyph index (gh, gw) -> mask (gh*cell, gw*cell)."""
    g = glyphs(cell)[idx]                                   # gh, gw, c, c
    gh, gw = idx.shape
    return g.transpose(0, 2, 1, 3).reshape(gh * cell, gw * cell)


def _hash(*a):
    """Deterministic pseudo-random in [0,1) for integer arrays."""
    x = np.uint32(2166136261)
    for v in a:
        x = (x ^ np.asarray(v, np.uint32)) * np.uint32(16777619)
    x ^= x >> np.uint32(13)
    x *= np.uint32(0x5bd1e995)
    x ^= x >> np.uint32(15)
    return (x & np.uint32(0xFFFFFF)).astype(np.float32) / float(0x1000000)


# ------------------------------------------------------------------ background rain
BG_CELL = 26


def rain_bg(t, strength=1.0, cell=BG_CELL, speed_px=(90, 160), seed=0, period=22.0, gaps=0.18):
    """0/1 columns falling down: returns (H, W) glyph intensity 0..1. Background: gray on white (multiply in);
    the intro uses the same function with green, faster and denser."""
    BG_CELL = cell
    gw, gh = W // BG_CELL + 1, H // BG_CELL + 2
    cols = np.arange(gw) + 1000 * seed
    speed = speed_px[0] + speed_px[1] * _hash(cols, 7)      # px/s, each column its own pace
    off = (t * speed + 2000 * _hash(cols, 3)) / BG_CELL     # cells scrolled
    rows = np.arange(gh)[:, None]
    src = rows - np.floor(off)[None, :]                     # glyph identity moves with the column
    flip = np.floor(t * 3 + _hash(cols, 9)[None, :] * 3)    # digits change slowly
    idx = (_hash(src.astype(np.int64) & 0xFFFF, cols[None, :], flip.astype(np.int64)) > 0.5).astype(np.int64)
    # brightness: long soft streaks along the column (a «tail» every ~22 cells)
    phase = (rows - off[None, :] * 1.0) / period + _hash(cols, 11)[None, :]
    streak = (phase - np.floor(phase))                      # 0..1 saw
    lum = np.clip(streak ** 2.2, 0, 1) * (0.35 + 0.65 * _hash(cols, 5))[None, :]
    lum *= (_hash(src.astype(np.int64) & 0xFFFF, cols[None, :] + 999) > gaps)   # gaps
    frac = (off - np.floor(off)) * BG_CELL                  # sub-cell scroll
    m = tile(idx, BG_CELL) * np.repeat(np.repeat(lum, BG_CELL, 0), BG_CELL, 1)
    out = np.zeros((H, W), np.float32)
    # shift each column by its sub-cell offset (columns are BG_CELL wide)
    for c in range(gw):
        x0, x1 = c * BG_CELL, min(W, (c + 1) * BG_CELL)
        if x0 >= W:
            break
        s = int(frac[c])
        out[:, x0:x1] = m[BG_CELL - s:BG_CELL - s + H, x0:x1]
    return out * strength


# ------------------------------------------------------------------ assembling a sprite from code
CELL = 15


@functools.lru_cache(16)
def _prep(sprite_id, sprite_key):
    sp = SPRITES[sprite_key]
    a = np.asarray(sp, np.float32) / 255
    gw, gh = math.ceil(sp.width / CELL), math.ceil(sp.height / CELL)
    pad = np.zeros((gh * CELL, gw * CELL, 4), np.float32)
    pad[:sp.height, :sp.width] = a
    cells = pad.reshape(gh, CELL, gw, CELL, 4).mean((1, 3))      # per-cell mean colour + coverage
    lum = (cells[..., :3] * (0.3, 0.59, 0.11)).sum(-1)
    return pad, cells[..., 3], lum, gw, gh


SPRITES = {}


def register(key, im):
    SPRITES[key] = im.convert('RGBA')


def assemble(t, key, t0, dur=2.0, seed=1):
    """Sprite `key` built from falling green code between t0 and t0+dur.
    Returns (rgba float32 (h, w, 4) in sprite pixels, done 0..1). Place it with fx.warp/over."""
    pad, cov, lum, gw, gh = _prep(id(SPRITES[key]), key)
    u = (t - t0) / dur
    if u >= 1:
        return pad, 1.0
    cols = np.arange(gw)
    rows = np.arange(gh)[:, None].astype(np.float32)
    inside = cov > 0.08
    # a stream per column: its head enters above the sprite and sweeps down; start/pace vary per column
    start = 0.02 + 0.30 * _hash(cols, seed)                 # in units of dur
    pace = (gh + 10) / (0.42 + 0.18 * _hash(cols, seed + 1))   # cells per dur unit
    head = (u - start[None, :]) * pace[None, :] - 6         # head row of the stream
    dist = head - rows                                      # >0: the head has passed this cell
    tail = np.clip(1 - dist / 9.0, 0, 1) * (dist >= 0)      # bright tail just behind the head
    lock = dist >= 0                                        # passed -> the cell keeps its glyph
    # glyphs flicker while in the stream, freeze once locked (a few still flicker)
    tick = np.floor(t * 18 + _hash(cols, seed + 2)[None, :] * 7)
    frz = np.floor((t0 + start[None, :] * dur) * 18)
    ri = rows.astype(np.int64)
    flick = _hash(ri, cols[None, :], np.where(lock & (_hash(ri, cols[None, :], 4) > 0.12), frz, tick).astype(np.int64))
    idx = (flick > 0.5).astype(np.int64)
    # dissolve code -> photo: per cell threshold after the code has locked
    th = 0.58 + 0.30 * _hash(ri, cols[None, :], seed + 5) + 0.06 * (rows / gh)
    photo = np.clip((u - th) / 0.10, 0, 1)                  # 0 code, 1 photo
    edge = np.clip(1 - np.abs(u - th - 0.05) / 0.06, 0, 1) * (photo < 1)   # green rim at the dissolve front
    # code layer colour: dark green -> bright green by picture luminance; stream head near white
    shade = 0.05 + 0.95 * np.clip(lum / max(1e-3, lum[inside].max() if inside.any() else 1), 0, 1)
    code_a = np.where(inside, np.maximum(lock * 0.95, tail), tail * 0.55 * (_hash(ri, cols[None, :], 8) > 0.6))
    code_a *= (1 - photo)
    hot = np.clip(1 - dist / 1.5, 0, 1) * (dist >= 0)       # the head glyph glows
    col = GREEN_DARK[None, None] + (GREEN - GREEN_DARK)[None, None] * shade[..., None]
    col = col * (1 - hot[..., None]) + np.array((60, 255, 120), np.float32) * hot[..., None]
    col = col * (1 - edge[..., None]) + np.array((40, 240, 110), np.float32) * edge[..., None]
    m = tile(idx, CELL)
    up = lambda x: np.repeat(np.repeat(x, CELL, 0), CELL, 1)
    code = np.zeros_like(pad)
    code[..., :3] = up(col) / 255
    code[..., 3] = m * up(np.maximum(code_a, edge * inside))
    ph = up(photo * inside)[..., None]
    out = pad * ph + code * (1 - ph)
    out[..., 3] = pad[..., 3] * ph[..., 0] + code[..., 3] * (1 - ph[..., 0])
    return out, float(np.clip(u, 0, 1))
