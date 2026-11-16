"""Хромакей листа + разрезка на N фигур по самым узким местам. python3 splitn.py лист.jpg tag N имя1,имя2,..."""
import sys, subprocess, numpy as np
from PIL import Image
src, tag, n, names = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split(',')
subprocess.run([sys.executable, str(__import__('pathlib').Path(__file__).with_name('chroma_key.py')), src, tag], check=True)
D = str(__import__('pathlib').Path(__file__).resolve().parents[1] / 'input' / 'mita') + '/'
arr = np.array(Image.open(f'{tag}_key.png')); A = arr[..., 3]; col = (A > 40).sum(0); W = A.shape[1]
cuts = [0]
for k in range(1, n):
    c = int(W * k / n); lo, hi = c - int(W / n / 2.5), c + int(W / n / 2.5)
    cuts.append(lo + int(np.argmin(col[lo:hi])))
cuts.append(W)
for i, nm in enumerate(names):
    sub = arr[:, cuts[i]:cuts[i + 1]].copy(); a = sub[..., 3]; sub[a < 8] = 0
    xs = np.nonzero((a > 40).sum(0))[0]; ys = np.nonzero((a > 40).sum(1))[0]
    Image.fromarray(sub[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]).save(D + nm + '.png'); print(nm, cuts[i], cuts[i + 1])
