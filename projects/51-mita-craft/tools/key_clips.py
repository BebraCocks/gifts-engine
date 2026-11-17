"""Клипы Gemini (input/mita/video/*.mp4, 720×1280, 24 к/с, зелёный фон) → RGBA-кадры build/clips/<имя>/f%04d.png.
• цвет фона берётся из угла каждого клипа (у Gemini он разный: 15,245,19 / 19,208,36 …);
• мягкая маска по расстоянию до фона, подавление зелёного во всех пикселях (в нарядах зелёного нет);
• мелкие отдельные пятна (искорки, которые Gemini дорисовал вопреки промпту) удаляются — остаётся фигура;
• ходьба (walk_*) выравнивается по голове (как walk_video.py), остальные — как есть (камера у Gemini неподвижна).
24 к/с оставляем (аниме-темп, без ореолов досчёта кадров). python3 tools/key_clips.py [имя …]"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / 'input' / 'mita' / 'video'
OUT = HERE / 'build' / 'clips'
FPS60 = {'walk_left'}
CLIPS = ['hook_normal', 'talk', 'cast_down', 'sweep', 'nope', 'palm', 'think', 'walk_left', 'creep_gemini_try1']


def frames(path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield cv2.cvtColor(f, cv2.COLOR_BGR2RGB)


def key(f, bg):
    d = np.sqrt(((f.astype(np.float32) - bg) ** 2).sum(-1))
    a = np.clip((d - 60) / 60, 0, 1)
    # только связное с фигурой: самая большая компонента + всё, что к ней близко (волосы, пальцы)
    m = (a > 0.5).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((9, 9), np.uint8)))
    if n > 1:
        big = 1 + int(np.argmax(st[1:, 4]))
        a *= (lab == big)
    rgb = f.astype(np.float32)
    rgb[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]) * 1.02)
    return np.concatenate([rgb, a[..., None] * 255], -1).clip(0, 255).astype(np.uint8)


def head_dx(fs, bg):
    """Сдвиг по x, чтобы голова стояла на месте (для ходьбы)."""
    m0 = np.sqrt(((fs[0].astype(np.float32) - bg) ** 2).sum(-1)) > 60
    ys, xs = np.nonzero(m0)
    top = ys.min()
    hx = int(xs[ys < top + 120].mean())
    box = (top, top + 220, hx - 110, hx + 110)
    tpl = cv2.cvtColor(fs[0], cv2.COLOR_RGB2GRAY)[box[0]:box[1], box[2]:box[3]]
    out = []
    for f in fs:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        R = 60
        sub = g[max(0, box[0] - R):box[1] + R, max(0, box[2] - R):box[3] + R]
        r = cv2.matchTemplate(sub, tpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, (mx, my) = cv2.minMaxLoc(r)
        out.append(min(R, box[2]) - mx)
    return out


def interp60(path):
    """24 → 60 к/с досчётом по движению (как walk_video.py): ходьба плавная, без рывков 24-кадровых шагов."""
    out = OUT / f'_{path.stem}_60.mp4'
    if not out.exists():
        import subprocess
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(path), '-an', '-vf',
                        'minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
                        '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv444p', str(out)], check=True)
    return out


def run(name):
    path = SRC / f'{name}_gemini.mp4' if (SRC / f'{name}_gemini.mp4').exists() else SRC / f'{name}.mp4'
    if name in FPS60:
        path = interp60(path)
    fs = list(frames(path))
    bg = np.median(np.stack([fs[0][:20, :20].reshape(-1, 3), fs[0][:20, -20:].reshape(-1, 3)]).reshape(-1, 3), 0).astype(np.float32)
    if name.startswith('walk'):
        # голова на месте, но без покадровых ±1–2 px: сдвиг сглажен (убирается только медленный уход Gemini)
        d = np.array(head_dx(fs, bg), np.float32)
        k = 15
        d = np.convolve(np.pad(d, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), 'valid')
        dx = list(d)
    else:
        dx = [0] * len(fs)
    od = OUT / name
    od.mkdir(parents=True, exist_ok=True)
    for i, (f, x) in enumerate(zip(fs, dx), 1):
        if abs(x) > 0.01:
            f = cv2.warpAffine(f, np.float32([[1, 0, x], [0, 1, 0]]), (f.shape[1], f.shape[0]), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=tuple(int(c) for c in bg))
        Image.fromarray(key(f, bg)).save(od / f'f{i:04d}.png', compress_level=1)
    print(name, len(fs), 'кадров, фон', bg.astype(int).tolist())


if __name__ == '__main__':
    for n in (sys.argv[1:] or CLIPS):
        run(n)
