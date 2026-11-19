"""Скорость «беговой дорожки» в клипах ходьбы/бега Gemini (камера ведёт персонажа, он в центре кадра).
Опорная стопа в кадре едет назад со скоростью шага; по экрану персонажа двигаем кодом с той же скоростью —
тогда стопы не скользят. Пишет build/clips/gait.json: {клип: {v: px/с в пикселях клипа, ground: y пола}}.
  python3 tools/gait.py s1_walkin:0.6:4.2 ..."""
import json
import sys
from pathlib import Path
import cv2
import numpy as np

HERE = Path(__file__).resolve().parents[1]
VID = HERE / 'input' / 'mita' / 'video'


def masks(path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        b, g, r = [f[..., k].astype(int) for k in range(3)]
        yield (g - np.maximum(r, b)) < 60


def blobs(row_mask):
    xs = np.nonzero(row_mask)[0]
    if len(xs) == 0:
        return []
    parts = np.split(xs, np.nonzero(np.diff(xs) > 4)[0] + 1)
    return [(p.min() + p.max()) / 2 for p in parts if len(p) > 6]


def measure(name, t0, t1, fps=24):
    ms = list(masks(VID / f'{name}.mp4'))
    bots = [np.nonzero(m.any(1))[0].max() for m in ms]
    ground = int(np.median(bots[:6]))
    i0, i1 = int(t0 * fps), min(len(ms) - 1, int(t1 * fps))
    d = []
    for i in range(i0, i1):
        a = blobs(ms[i][ground - 10:ground + 3].any(0))       # что касается пола
        b = blobs(ms[i + 1][ground - 10:ground + 3].any(0))
        for x in a:
            if b:
                j = min(b, key=lambda y: abs(y - x))
                if abs(j - x) < 40:
                    d.append(j - x)
    d = np.array(d)
    v = float(np.median(d[np.abs(d) > 2])) * fps if (np.abs(d) > 2).any() else 0.0
    return dict(v=round(v, 1), ground=ground, n=len(ms))


if __name__ == '__main__':
    out = HERE / 'build' / 'clips' / 'gait.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    res = json.loads(out.read_text()) if out.exists() else {}
    for arg in sys.argv[1:]:
        name, a, b = arg.split(':')
        res[name] = measure(name, float(a), float(b))
        print(name, res[name])
    out.write_text(json.dumps(res, indent=1))
