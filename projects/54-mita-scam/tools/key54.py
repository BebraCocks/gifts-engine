"""Хромакей 53: клипы Gemini и картинки ChatGPT на зелёном → RGBA.
Ключ по «зелёности» g−max(r,b) (а не по расстоянию до цвета): полупрозрачные свечения, искры и снег на зелёном
становятся белыми полупрозрачными, а не серой дымкой; цвет переднего плана восстанавливается вычитанием фона.
  python3 tools/key53.py clips [имя…]   → build/clips/<имя>/f%04d.png + build/clips/geom.json
  python3 tools/key53.py images        → build/keyed/<имя>.png"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parents[1]
VID = HERE / 'input' / 'mita' / 'video'
OUT = HERE / 'build' / 'clips'
KEYED = HERE / 'build' / 'keyed'
CLIPS = {'hook': VID / 'hook_gemini.mp4', 'talk': VID / 'talk_gemini.mp4', 'lens': VID / 'lens_gemini.mp4',
         'stamp': VID / 'stamp_gemini.mp4', 'case': VID / 'case_gemini.mp4', 'choice': VID / 'choice_gemini.mp4',
         'fox': HERE / 'input' / 'decor' / 'fox_gemini.mp4', 'nono': VID / 'nono_gemini.mp4', 'shock': VID / 'shock_gemini.mp4',
         'phone': VID / 'phone_gemini.mp4', 'point': VID / 'point_gemini.mp4',
         'listen': VID / 'listen.mp4', 'step': VID / 'step.mp4',
         **{f's{k}_{p}': VID / f's{k}_{p}.mp4' for k in range(1, 6) for p in ('walkin', 'talk', 'run')},
         **{n: VID / f'{n}.mp4' for n in ('tp1_smoke', 'tp2_glitch', 'tp3_papers', 'tp4_lens', 'tp5_hat')}}
IMAGES = {'detective': 'input/mita/sheets/detective_ref.png', 'creep_1': 'input/mita/sheets/creep_1.png',
          'creep_2': 'input/mita/sheets/creep_2.png', 'creep_3': 'input/mita/sheets/creep_3.png',
          'creep_4': 'input/mita/sheets/creep_4.png', 'creep_5': 'input/mita/sheets/creep_5.png',
          'lens': 'input/decor/lens.png', 'sheet_psf': 'input/decor/phone_stamp_fox.png', 'counter': 'input/decor/counter.png',
          'notes': 'input/decor/notes_folders.png', 'fox_full': 'input/decor/fox_full.png', 'ui': 'input/decor/ui.png',
          'emotes': 'input/decor/emotes.png', 'fx': 'input/decor/fx.png'}


def bg_of(f):
    c = np.concatenate([f[:24, :24].reshape(-1, 3), f[:24, -24:].reshape(-1, 3), f[-24:, :24].reshape(-1, 3),
                        f[-24:, -24:].reshape(-1, 3)])
    return np.median(c, 0).astype(np.float32)


def key(f, bg, soft=0.75, mode='normal'):
    x = f.astype(np.float32)
    gr = x[..., 1] - np.maximum(x[..., 0], x[..., 2])
    g0 = float(bg[1] - max(bg[0], bg[2]))
    a = np.clip((g0 * 0.92 - gr) / (g0 * soft), 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.6)
    a[a < 0.04] = 0
    aa = np.maximum(a, 1e-3)[..., None]
    fg = (x - (1 - a[..., None]) * bg) / aa
    fg = np.where(a[..., None] > 0.02, fg, 0)
    if mode == 'tree':            # ёлка тёмно-зелёная: зелёный гасим только на полупрозрачных краях
        lim = np.maximum(fg[..., 0], fg[..., 2]) * 1.04 + 4
        fg[..., 1] = np.where(a < 0.97, np.minimum(fg[..., 1], lim), fg[..., 1])
    elif mode == 'box':           # вихрь: искры и «призрак» Миты на зелёном → золотые/тёплые, без зелени
        r_, b_ = fg[..., 0], fg[..., 2]
        fg[..., 1] = np.minimum(fg[..., 1], 0.5 * (r_ + b_) + 0.25 * np.abs(r_ - b_))
    else:
        fg[..., 1] = np.minimum(fg[..., 1], np.maximum(fg[..., 0], fg[..., 2]) * 1.04 + 4)
    return np.dstack([fg.clip(0, 255), a * 255]).astype(np.uint8)


def frames(path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield cv2.cvtColor(f, cv2.COLOR_BGR2RGB)


def run_clip(name, geo):
    fs = list(frames(CLIPS[name]))
    bg = bg_of(fs[0])
    od = OUT / name
    od.mkdir(parents=True, exist_ok=True)
    tp = name.startswith('tp')                    # телепорты: полупрозрачная Мита/дым — мягче ключ + сильнее убрать зелень
    for i, f in enumerate(fs, 1):
        Image.fromarray(key(f, bg_of(f), 1.0 if tp else 0.75, 'box' if tp else 'normal')).save(od / f'f{i:04d}.png',
                                                                                             compress_level=1)
    # геометрия по первому кадру: верх, низ (подошвы), центр стоп
    a = key(fs[0], bg)[..., 3] > 128
    ys, xs = np.nonzero(a)
    top, bot = int(ys.min()), int(ys.max())
    low = ys > bot - 40
    geo[name] = dict(n=len(fs), top=top, bot=bot, hx=float((xs[low].min() + xs[low].max()) / 2), w=fs[0].shape[1],
                     h=fs[0].shape[0])
    print(name, len(fs), 'кадров, фон', bg.astype(int).tolist(), geo[name])


def run_images():
    KEYED.mkdir(parents=True, exist_ok=True)
    for name, rel in IMAGES.items():
        f = np.array(Image.open(HERE / rel).convert('RGB'))
        k = key(f, bg_of(f), 0.75, 'box' if name == 'fx' else 'normal')
        Image.fromarray(k).save(KEYED / f'{name}.png')
        print(name, f.shape, round((k[..., 3] > 128).mean(), 3))


if __name__ == '__main__':
    if sys.argv[1] == 'images':
        run_images()
    else:
        gp = OUT / 'geom.json'
        OUT.mkdir(parents=True, exist_ok=True)
        geo = json.loads(gp.read_text()) if gp.exists() else {}
        for n in (sys.argv[2:] or list(CLIPS)):
            run_clip(n, geo)
        gp.write_text(json.dumps(geo, indent=1))
