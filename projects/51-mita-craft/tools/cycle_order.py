"""Порядок поз в цикле (ходьба): каждая новая поза вставляется туда, где она ближе всего к соседям (по силуэту ног и рук).
python3 tools/cycle_order.py база1,база2,... новая1,новая2,...  → печатает порядок и сохраняет data/walk_cycle.json"""
import sys, json
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import anim
import snap_preview as SP

base = sys.argv[1].split(',')
new = sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] else []
SP.align_all(base + new)
def feat(n):
    a = np.array(Image.open(SP.AL / f'{n}.png').convert('RGBA')).astype(np.float32)
    al = a[..., 3:4] / 255
    g = (a[..., :3].mean(-1, keepdims=True) * al + 255 * (1 - al))[..., 0]
    g = np.array(Image.fromarray(g.astype(np.uint8)).resize((96, 128), Image.BILINEAR), np.float32)
    w = np.ones_like(g); w[64:] = 3.0          # ноги важнее
    return g, w
F = {n: feat(n) for n in base + new}
def d(a, b):
    (ga, w), (gb, _) = F[a], F[b]
    return float((np.abs(ga - gb) * w).mean())
cyc = list(base)
for n in new:
    best = None
    for i in range(len(cyc)):
        a, b = cyc[i], cyc[(i + 1) % len(cyc)]
        cost = d(a, n) + d(n, b) - d(a, b)
        if best is None or cost < best[0]:
            best = (cost, i + 1)
    cyc.insert(best[1], n)
print(' '.join(cyc))
print('шаги:', [round(d(cyc[i], cyc[(i + 1) % len(cyc)]), 1) for i in range(len(cyc))])
Path('data/walk_cycle.json').write_text(json.dumps(cyc))
