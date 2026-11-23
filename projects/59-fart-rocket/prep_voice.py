"""Дубли Fish Audio (voice/Lxx.mp3) -> voice/fast/Lxx.wav: края обрезаны, паузы внутри >0,32 с ужаты до 0,28 с,
темп 1,15x без смены тона (atempo)."""
import subprocess
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SR = 48000
TEMPO = 1.15
OUT = HERE / 'voice' / 'fast'
OUT.mkdir(parents=True, exist_ok=True)


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def squeeze(a, thr_db=-42, max_gap=0.32, keep=0.28):
    env = np.abs(a).max(1)
    win = int(0.02 * SR)
    env = np.convolve(env, np.ones(win) / win, 'same')
    loud = env > 10 ** (thr_db / 20)
    idx = np.flatnonzero(loud)
    a = a[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.08 * SR)]
    loud = loud[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.08 * SR)]
    out, i, n = [], 0, len(a)
    while i < n:
        if loud[i]:
            j = i
            while j < n and loud[j]:
                j += 1
            out.append(a[i:j]); i = j
        else:
            j = i
            while j < n and not loud[j]:
                j += 1
            seg = a[i:j]
            if (j - i) / SR > max_gap:
                h = int(keep * SR / 2)
                seg = np.concatenate([seg[:h], seg[-h:]])
            out.append(seg); i = j
    return np.concatenate(out)


for p in sorted((HERE / 'voice').glob('L*.mp3')):
    a = squeeze(load(p))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-af', f'atempo={TEMPO}', str(OUT / (p.stem + '.wav'))], input=a.tobytes(), check=True)
    print(p.stem, round(len(a) / SR / TEMPO, 2))
