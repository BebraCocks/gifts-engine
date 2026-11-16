"""Добивка зелёной каймы в тёмном кружеве после хромакея: g ≤ max(r,b); тёмные бирюзовые пиксели → нейтральнее.
python3 despill_dark.py файл.png [...] (перезаписывает)."""
import sys
import numpy as np
from PIL import Image
for f in sys.argv[1:]:
    x = np.array(Image.open(f).convert('RGBA')).astype(np.float32)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    g2 = np.minimum(g, np.maximum(r, b))
    teal = (np.minimum(g2, b) > r + 6) & (np.maximum(g2, b) < 110) & (b < r + 60) & (g2 > b - 25)
    m = (r + (g2 + b) / 2) / 2
    x[..., 1] = np.where(teal, m, g2)
    x[..., 2] = np.where(teal, np.minimum(b, m + 6), b)
    Image.fromarray(x.clip(0, 255).astype(np.uint8), 'RGBA').save(f)
    print(f, int(teal.sum()))
