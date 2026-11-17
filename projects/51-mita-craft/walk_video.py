"""Ходьба Миты из видео Gemini (input/mita/video/walk_gemini.mp4, 720×1280, 24 к/с, зелёный фон).

1) выравнивание: голова (шаблон первого кадра, поиск ±40 px) — по горизонтали всегда на одном месте
   (иначе Миту «шатает»); по вертикали — пол (самая нижняя точка стоп), слегка сглаженный — естественное
   покачивание шага остаётся, дрожание камеры уходит;
2) 24 → 60 к/с — досчёт кадров оптическим потоком (ffmpeg minterpolate) на зелёном фоне;
3) хромакей с подавлением зелёной каймы → build/walk_video/f%04d.png (RGBA) + превью build/walk_video.mp4.
python3 walk_video.py"""
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
SRC = HERE / 'input' / 'mita' / 'video' / 'walk_gemini.mp4'
OUT = HERE / 'build' / 'walk_video'
GREEN = np.array([15, 245, 19], np.float32)


def frames(path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield cv2.cvtColor(f, cv2.COLOR_BGR2RGB)


def mask(a):
    d = np.sqrt(((a.astype(np.float32) - GREEN) ** 2).sum(-1))
    return np.clip((d - 60) / 60, 0, 1)


def stabilize():
    fs = list(frames(SRC))
    m0 = mask(fs[0]) > 0.5
    ys, xs = np.nonzero(m0)
    top = ys.min()
    hx = int(xs[ys < top + 120].mean())
    box = (top, top + 220, hx - 110, hx + 110)
    tpl = cv2.cvtColor(fs[0], cv2.COLOR_RGB2GRAY)[box[0]:box[1], box[2]:box[3]]
    dx, floor = [], []
    for f in fs:
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY)
        R = 40
        sub = g[max(0, box[0] - R):box[1] + R, box[2] - R:box[3] + R]
        r = cv2.matchTemplate(sub, tpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, (mx, my) = cv2.minMaxLoc(r)
        dx.append(R - mx)
        m = mask(f) > 0.5
        floor.append(np.nonzero(m.any(1))[0].max())
    dx = np.array(dx, np.float32)
    floor = np.array(floor, np.float32)
    # пол: верхняя огибающая (опорная стопа) по окну ±6 кадров, сглаженная — дрожание камеры уходит
    env = np.array([floor[max(0, i - 6):i + 7].max() for i in range(len(floor))])
    env = np.convolve(np.pad(env, 4, mode='edge'), np.ones(9) / 9, mode='valid')
    dy = env.max() - env
    out = []
    for f, x, y in zip(fs, dx, dy):
        M = np.float32([[1, 0, x], [0, 1, y]])
        out.append(cv2.warpAffine(f, M, (f.shape[1], f.shape[0]), borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=tuple(int(c) for c in GREEN)))
    print('сдвиг по x:', round(float(dx.min()), 1), '…', round(float(dx.max()), 1), ' по y:', round(float(dy.max()), 1))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / 'stab60.mp4'
    if not tmp.exists():
        _stab60(tmp)
    h, w = next(frames(tmp)).shape[:2]
    n = 0
    prev = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '540x960', '-r', '60', '-i', '-',
                             '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(HERE / 'build' / 'walk_video.mp4')],
                            stdin=subprocess.PIPE)
    _key(tmp, prev, w, h)


def _stab60(tmp):
    st = stabilize()
    h, w = st[0].shape[:2]
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', '24', '-i', '-',
                          '-vf', 'minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
                          '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv444p', str(tmp)], stdin=subprocess.PIPE)
    for f in st:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()


def _key(tmp, prev, w, h):
    n = 0
    for f in frames(tmp):
        a = mask(f)
        rgb = f.astype(np.float32)
        # подавление зелёного во ВСЕХ пикселях (в костюме зелёного нет; досчёт кадров подмешивает фон между ногами)
        rgb[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]) * 1.02)
        rgba = np.concatenate([rgb, a[..., None] * 255], -1).clip(0, 255).astype(np.uint8)
        n += 1
        Image.fromarray(rgba).save(OUT / f'f{n:04d}.png')
        bg = Image.new('RGBA', (w, h), (250, 248, 255, 255))
        bg.alpha_composite(Image.fromarray(rgba))
        prev.stdin.write(np.array(bg.convert('RGB').resize((540, 960), Image.LANCZOS)).tobytes())
    prev.stdin.close()
    prev.wait()
    print(n, 'кадров →', OUT)


if __name__ == '__main__':
    main()
