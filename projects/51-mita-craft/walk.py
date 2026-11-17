"""Ходьба Миты без «мерцания» верха.

Позы ходьбы с разных листов ChatGPT отличаются руками, плащом, хвостами и оттенком ткани → на 60 к/с верх «дёргается».
Поэтому кадр собирается из двух слоёв:
  • ноги — из плотного цикла (data/walk_cycle.json, морф соседних поз);
  • верх (голова, руки, плащ, юбка) — плавный морф двух согласованных поз UPPER (контакт → проход → контакт за шаг),
    сдвинутый по вертикали вместе с покачиванием ног.
Шов прячется под подолом юбки. Позы берутся из frames_aligned (snap_preview.align_all — голова+ремень, рост).
walk_frame(phase) → RGBA 768×1024, phase — доля ШАГА (0..1, цикл из одного шага повторяется)."""
import functools
import json
from pathlib import Path

import cv2
import numpy as np

import anim
import snap_preview as SP

HERE = Path(__file__).resolve().parent
MORPH_LEGS = True
UPPER = ('walk_a', 'walk_a')          # верх из одной позы: морф рук между разными позами двоит кисть


def KEYS():
    """Ключевые позы ног (tools/walk_keys.py): самые согласованные позы цикла, между ними — морф."""
    return json.loads((HERE / 'data' / 'walk_keys.json').read_text())['keys']


def SEGS():
    return json.loads((HERE / 'data' / 'walk_keys.json').read_text())['segs']


def cycle():
    return json.loads((HERE / 'data' / 'walk_cycle.json').read_text())


@functools.lru_cache(None)
def _bob(n):
    """Вертикальное смещение головы позы n относительно walk_a (после выравнивания)."""
    return float(SP._walk_shift(anim.pose('walk_a'), anim.pose(n))[1])


def _hem(a):
    """Строка подола юбки: первая строка ниже 560, где силуэт уже 60 % ширины юбки."""
    al = a[..., 3] > 60
    def width(y):
        xs = np.nonzero(al[y])[0]
        return (xs.max() - xs.min()) if len(xs) else 0
    w0 = max(width(y) for y in range(530, 560))
    for y in range(560, 700):
        if width(y) < 0.6 * w0:
            return y
    return 610


@functools.lru_cache(maxsize=64)
def _morph_sharp_q(n1, n2, qk):
    """Как anim.morph, но смена позы в середине перехода короче (0.44–0.56): полупрозрачная «вторая нога» не видна."""
    Q = anim.Q
    k = qk / Q
    if qk <= 0:
        return anim.pose(n1)
    if qk >= Q:
        return anim.pose(n2)
    d = anim._shift(n1, n2)
    A = anim._premul(anim.pose(n1))
    B = anim._premul(anim._translate(anim.pose(n2), -d))
    wa = anim._translate(anim._warp(A, anim._flow(n1, n2), k), d * k)
    wb = anim._translate(anim._warp(B, anim._flow_rev(n1, n2), 1 - k), d * k)
    u = max(0.0, min(1.0, (k - 0.44) / 0.12))
    sm = u * u * (3 - 2 * u)
    m = wa * (1 - sm) + wb * sm
    al = np.clip(m[..., 3:4], 1e-3, 255)
    rgb = np.clip(m[..., :3] * 255 / al, 0, 255)
    return np.concatenate([rgb, np.clip(m[..., 3:4], 0, 255)], -1).astype(np.uint8)


def _morph_sharp(n1, n2, k):
    return _morph_sharp_q(n1, n2, int(round(max(0.0, min(1.0, k)) * anim.Q)))


def _shift_y(a, dy):
    return anim._translate(a, np.array([0, dy], np.float32)) if abs(dy) > 0.05 else a


def walk_frame(phase):
    cyc = cycle()
    N = len(cyc)
    keys = sorted(KEYS(), key=cyc.index)
    # ключи стоят на своих местах в цикле (фаза = индекс/N); между ключами — линейный морф (без ease — иначе шаг «спотыкается»)
    pos = [cyc.index(n) / N for n in keys]
    p = phase % 1.0
    K = len(keys)
    for j in range(K):
        a, b = pos[j], pos[(j + 1) % K] + (1.0 if j == K - 1 else 0.0)
        pp = p if p >= pos[0] else p + 1.0
        if a <= pp < b:
            break
    k = (pp - a) / (b - a)
    n0, n1 = keys[j], keys[(j + 1) % K]
    seg = SEGS()[KEYS().index(n0)]
    if seg['cut']:
        # быстрый мах ногой: настоящие позы цикла по очереди, без морфа
        chain = [n0] + seg['mid'] + [n1]
        f = k * (len(chain) - 1)
        i0 = int(f)
        n0, n1, k = chain[i0], chain[min(i0 + 1, len(chain) - 1)], f - i0
        L = anim.pose(n0 if k < 0.5 else n1).astype(np.float32)
    else:
        L = (_morph_sharp(n0, n1, k) if MORPH_LEGS else anim.pose(n0 if k < 0.5 else n1)).astype(np.float32)
    bob = _bob(n0) * (1 - k) + _bob(n1) * k                 # покачивание шага (голова ног-позы)
    # верх: контакт (0) → проход (0.5) → контакт (1), плавно
    u = 0.5 - 0.5 * np.cos(2 * np.pi * (phase % 1.0))
    U = anim.morph(UPPER[0], UPPER[1], u)
    ub = _bob(UPPER[0]) * (1 - u) + _bob(UPPER[1]) * u
    U = _shift_y(U, -(bob - ub)).astype(np.float32)
    h = _hem(U.astype(np.uint8))
    H, W = U.shape[:2]
    yy = np.arange(H, dtype=np.float32)[:, None]
    # верх — до подола (мягкий край 6 px)
    mu = np.clip((h + 4 - yy) / 6 + 0.5, 0, 1)
    # ноги — от 30 px над подолом; в полосе у подола только в ширину бёдер (чтобы не вылезла кисть/плащ ног-позы)
    al = L[..., 3] > 60
    xs = np.nonzero(al[min(H - 1, h + 12)])[0]
    x0, x1 = (xs.min() - 15, xs.max() + 15) if len(xs) else (0, W)
    xx = np.arange(W, dtype=np.float32)[None, :]
    band = ((xx >= x0) & (xx <= x1)).astype(np.float32)
    ml = np.clip((yy - (h - 30)) / 8, 0, 1) * np.maximum(band, np.clip((yy - (h + 40)) / 8, 0, 1))
    Lm = L.copy()
    Lm[..., 3] *= ml[..., 0] if ml.ndim == 3 else ml
    Um = U.copy()
    Um[..., 3] *= mu if mu.ndim == 2 and mu.shape[1] == W else np.broadcast_to(mu, (H, W))
    # U поверх L (премультипликация)
    ua = Um[..., 3:4] / 255
    la = Lm[..., 3:4] / 255
    oa = ua + la * (1 - ua)
    rgb = (Um[..., :3] * ua + Lm[..., :3] * la * (1 - ua)) / np.maximum(oa, 1e-4)
    return np.clip(np.concatenate([rgb, oa * 255], -1), 0, 255).astype(np.uint8)


if __name__ == '__main__':
    import subprocess
    import sys
    from PIL import Image
    SP.align_all(list(dict.fromkeys(cycle() + list(UPPER))))
    anim.FR = SP.AL
    anim.pose.cache_clear()
    step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5     # длительность шага, с
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    W, H, FPS = 540, 960, 60
    out = HERE / 'build' / 'walk_layered.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)], stdin=subprocess.PIPE)
    for fi in range(int(secs * FPS)):
        a = walk_frame(fi / FPS / step)
        bg = Image.new('RGBA', (W, H), (250, 248, 255, 255))
        m = Image.fromarray(a)
        m = m.resize((int(m.width * 0.72), int(m.height * 0.72)), Image.LANCZOS)
        bg.alpha_composite(m, (W // 2 - m.width // 2, 830 - int(990 * 0.72)))
        p.stdin.write(np.array(bg.convert('RGB')).tobytes())
    p.stdin.close()
    p.wait()
    print(out)
