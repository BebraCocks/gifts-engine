"""Copy the chosen takes to voice/L01..wav, trimming only leading/trailing silence (speech is not sped up)."""
import sys
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
CHOICE = {1: '12', 2: '08', 3: '08', 4: '09', 5: '09', 6: '08', 7: '08', 8: '09'}   # drama-3 takes
KEEP_LEAD, KEEP_TAIL = 0.03, 0.08


def trim(src, dst):
    with wave.open(str(src)) as w:
        p = w.getparams()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2')
    sr = p.framerate
    xm = x.reshape(-1, p.nchannels).astype(float).mean(1) if p.nchannels > 1 else x.astype(float)
    hop = sr // 100
    e = np.array([np.sqrt((xm[k:k + hop] ** 2).mean()) for k in range(0, len(xm) - hop, hop)])
    db = 20 * np.log10(e / 32768 + 1e-6)
    on = np.nonzero(db > db.max() - 38)[0]
    a = max(0, int((on[0] / 100 - KEEP_LEAD) * sr))
    b = min(len(xm), int(((on[-1] + 1) / 100 + KEEP_TAIL) * sr))
    y = x.reshape(-1, p.nchannels)[a:b].copy()
    f = int(0.01 * sr)
    y[-f:] = (y[-f:] * np.linspace(1, 0, f)[:, None]).astype('<i2')
    with wave.open(str(dst), 'wb') as w:
        w.setparams(p)
        w.writeframes(y.tobytes())
    return len(y) / sr


if __name__ == '__main__':
    total = 0
    for k, take in CHOICE.items():
        d = trim(HERE / 'voice' / f'L{k:02d}_take{take}.wav', HERE / 'voice' / f'L{k:02d}.wav')
        total += d
        print(f'L{k:02d} <- take{take}: {d:.2f} s')
    print(f'total {total:.2f} s')
