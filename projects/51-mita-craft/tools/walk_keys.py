"""Ключевые позы ног для ходьбы: из плотного цикла (data/walk_cycle.json) выбрать K поз в том же порядке так,
чтобы соседние были как можно ровнее (минимум суммы квадратов расстояний по силуэту/яркости ног).
Выбивающиеся позы (другой рисунок чулка, стопа «скачет») пропускаются. → data/walk_keys.json
python3 tools/walk_keys.py [K]"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import snap_preview as SP

K = int(sys.argv[1]) if len(sys.argv) > 1 else 12
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 5        # между соседними ключами не больше GAP шагов цикла
cyc = json.loads(Path('data/walk_cycle.json').read_text())
SP.align_all(cyc + ['walk_a'])


def feat(n):
    a = np.array(Image.open(SP.AL / f'{n}.png').convert('RGBA')).astype(np.float32)
    a = a[600:1000]                                    # только ноги (ниже подола)
    al = a[..., 3:4] / 255
    g = (a[..., :3].mean(-1, keepdims=True) * al + 255 * (1 - al))[..., 0]
    return np.array(Image.fromarray(g.astype(np.uint8)).resize((96, 50), Image.BILINEAR), np.float32)


F = {n: feat(n) for n in cyc}
N = len(cyc)
D = np.array([[float(np.abs(F[a] - F[b]).mean()) for b in cyc] for a in cyc])

best = None
for s in range(N):                                     # с какой позы начинается цикл ключей
    order = cyc[s:] + cyc[:s]
    idx = [cyc.index(n) for n in order]
    INF = 1e18
    # dp[j][c] — минимальная стоимость, если c-й ключ — поза j (по порядку), первый ключ — order[0]
    dp = np.full((N, K), INF)
    prv = np.zeros((N, K), int)
    dp[0][0] = 0
    for c in range(1, K):
        for j in range(c, N):
            lo = max(c - 1, j - GAP)
            cand = [dp[i][c - 1] + D[idx[i], idx[j]] ** 2 for i in range(lo, j)]
            if not cand:
                continue
            m = int(np.argmin(cand))
            dp[j][c] = cand[m]
            prv[j][c] = m + lo
    for j in range(max(K - 1, N - GAP), N):           # замыкание на первый ключ (тоже не дальше GAP)
        tot = dp[j][K - 1] + D[idx[j], idx[0]] ** 2
        if best is None or tot < best[0]:
            path, c, jj = [], K - 1, j
            while c >= 0:
                path.append(order[jj])
                jj = prv[jj][c]
                c -= 1
            best = (tot, path[::-1])
keys = best[1]
steps = [round(float(D[cyc.index(keys[i]), cyc.index(keys[(i + 1) % K])]), 1) for i in range(K)]
print(' '.join(keys))
print('шаги:', steps)
TH = 12.0                                              # больше — морф «размажет» ногу: там показываем позы цикла как есть
segs = []
for i in range(K):
    a, b = keys[i], keys[(i + 1) % K]
    ia, ib = cyc.index(a), cyc.index(b)
    mid = [cyc[(ia + j) % N] for j in range(1, (ib - ia) % N)]
    segs.append({'cut': bool(D[ia, ib] > TH), 'mid': mid})
print('рез:', [s_['cut'] for s_ in segs])
Path('data/walk_keys.json').write_text(json.dumps({'keys': keys, 'segs': segs}, ensure_ascii=False))
