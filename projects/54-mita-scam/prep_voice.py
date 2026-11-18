"""Дубли Fish (voice/raw/LNN_K.mp3, выбор — PICK) → voice/LNN.wav (48 кГц моно) + voice/lines.json.
Тишина по краям обрезается, паузы внутри реплики сокращаются до MAX_GAP. Темп — TEMPO (atempo, без смены тона)."""
import json
import subprocess
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RAW, OUT = HERE / 'voice' / 'raw', HERE / 'voice'
SR = 48000
PICK = {}
TEMPO = 1.15         # 53: быстрее, чтобы уложиться ~70 с
MAX_GAP = 0.13
GAP_LINE = {6: 0.45}    # жуткий шёпот: паузы чуть длиннее остальных, но короче исходных
TRIM_START = {}


def load(path, af):
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-af', af, '-ac', '1', '-ar', str(SR), '-f', 's16le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, '<i2').astype(np.float64) / 32768


def tighten(x, max_gap, thr_db=-40):
    win = int(0.01 * SR)
    n = len(x) // win
    rms = np.sqrt(np.mean(x[:n * win].reshape(n, win) ** 2, 1) + 1e-12)
    loud = 20 * np.log10(rms) > thr_db
    idx = np.nonzero(loud)[0]
    a, b = max(0, idx[0] - 3), min(n, idx[-1] + 6)          # 30 мс до, 60 мс после
    keep, gaps, run = [], [], 0
    for i in range(a, b):
        if loud[i]:
            if run:
                g = run * win / SR
                gaps.append(round(min(g, max_gap), 3))
                keep.extend(range(i - min(run, int(max_gap * 100)), i))
            run = 0
            keep.append(i)
        else:
            run += 1
    keep.extend(range(b - 5, b))
    keep = sorted(set(keep))
    y = np.concatenate([x[i * win:(i + 1) * win] for i in keep])
    f = int(0.008 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y, gaps


def write(path, x):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    from script import LINES
    meta = []
    for k in range(1, len(LINES) + 1):
        name = f'L{k:02d}'
        trim = TRIM_START.get(k, 0.0)
        tempo = 1.06 if k == 6 else TEMPO                    # шёпот чуть медленнее остальных
        x = load(RAW / f'{name}_{PICK.get(name, 0)}.mp3', f'atrim=start={trim},asetpts=PTS-STARTPTS,atempo={tempo},loudnorm=I=-16:TP=-1.5:LRA=11')
        y, gaps = tighten(x, GAP_LINE.get(k, MAX_GAP))
        write(OUT / f'{name}.wav', y)
        meta.append({'line': k, 'dur': round(len(y) / SR, 3), 'gaps': gaps})
        print(name, round(len(y) / SR, 2))
    (OUT / 'lines.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print('сумма', round(sum(m['dur'] for m in meta), 2))
