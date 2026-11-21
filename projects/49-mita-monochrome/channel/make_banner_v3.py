"""Баннер v3 (2026-11-21): картинка ChatGPT автора с надписью «Мита о гифтах» (banner_v3_raw.png) целиком, вписана по
высоте в 3200×1200 (≈2,67:1) и сдвинута так, чтобы Мита была в видимой зоне профиля (x ≥ 0,12 W), а надпись не
заходила в зону кнопок (x < 0,63 W при y 0,28–0,47 H). Фон по краям дотянут цветом фона (без полос).
python3 make_banner_v3.py banner_v3_raw.png banner_v3.png"""
import sys
import numpy as np
from PIL import Image
W, H = 3200, 1200
X0 = 400
art = Image.open(sys.argv[1]).convert('RGB')
art = art.resize((round(art.width * H / art.height), H), Image.LANCZOS)
a = np.array(art).astype(float)


def bg_column(x):
    col = a[:, x, :].copy()
    ok = (col[:, 2] > 225) & (col[:, 1] > 100) & (col[:, 0] < 140)
    rows = np.arange(H)
    for c in range(3):
        col[:, c] = np.interp(rows, rows[ok], col[ok, c])
    k = np.ones(81) / 81
    return np.stack([np.convolve(np.pad(col[:, c], 40, mode='edge'), k, 'valid') for c in range(3)], 1)


out = np.zeros((H, W, 3))
L, R = bg_column(0), bg_column(art.width - 1)
out[:, :X0] = L[:, None, :] * np.linspace(0.93, 1.0, X0)[None, :, None]
out[:, X0 + art.width:] = R[:, None, :] * np.linspace(1.0, 0.95, W - X0 - art.width)[None, :, None]
out[:, X0:X0 + art.width] = a
# мягкий шов слева: первые 60 px картинки смешиваем с фоном только там, где у края фон (волосы/коробки не трогаем)
for i in range(60):
    w = i / 59
    col = a[:, i]
    isbg = ((col[:, 2] > 225) & (col[:, 1] > 100) & (col[:, 0] < 140))[:, None]
    out[:, X0 + i] = np.where(isbg, L * (1 - w) + col * w, col)
Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(sys.argv[2], quality=95)
s = H / 1024
print(sys.argv[2], 'надпись до x ≈ %.3f W; Мита с x ≈ %.3f W' % ((X0 + 1340 * s) / W, (X0 + 20 * s) / W))
