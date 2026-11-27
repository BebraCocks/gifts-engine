"""Тайминг части 1 по реальной длине клипов voice/clips/*.wav; субтитры — короткими кусками,
время куска — по доле знаков внутри участков речи (паузы клипа не считаются)."""
import re
import wave
from pathlib import Path
import numpy as np
from script import CLIPS, LEAD

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / 'clips' / f'{c[0]}.wav' for c in CLIPS]
HAS_NARRATION = all(p.is_file() for p in TAKES)
KEYS = [c[0] for c in CLIPS]
ON, END = [], []
cursor = LEAD
for k, c in enumerate(CLIPS):
    with wave.open(str(TAKES[k])) as w:
        dur = w.getnframes() / w.getframerate()
    ON.append(cursor)
    END.append(cursor + dur)
    cursor += dur + c[4]
DUR = cursor
S = dict(zip(KEYS, ON))
E = dict(zip(KEYS, END))

# сцены: последовательные отрезки с одинаковой меткой сцены
SCENES = []
for k, c in enumerate(CLIPS):
    t0 = 0.0 if k == 0 else ON[k] - 0.25
    if SCENES and SCENES[-1][0] == c[3]:
        continue
    if SCENES:
        SCENES[-1][2] = t0
    SCENES.append([c[3], t0, None, k])
SCENES[-1][2] = DUR
SCENES = [tuple(s) for s in SCENES]


def _speech_mask(path, hop=0.02):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32).reshape(-1, 2).mean(1) / 32768
    n = int(sr * hop)
    rms = np.array([np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n, n)])
    on = rms > max(0.01, np.percentile(rms, 60) * 0.25)
    on = np.convolve(on.astype(float), np.ones(9), 'same') > 0          # склеить короткие провалы
    return on, hop


def _chunks(text, limit=38):
    parts = re.split(r'(?<=[.!?…:—])\s+', text)
    out = []
    for p in parts:
        while len(p) > limit:
            cut = max(p.rfind(', ', 0, limit), p.rfind(' — ', 0, limit), p.rfind(' ', 0, limit))
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:].strip()
        if p:
            out.append(p)
    return out


SUBS = []          # (начало, конец, текст)
if HAS_NARRATION:
    for k, c in enumerate(CLIPS):
        mask, hop = _speech_mask(TAKES[k])
        speech_t = np.cumsum(mask) * hop
        total = speech_t[-1] if len(speech_t) else 1.0
        chunks = _chunks(c[5])
        n_all = sum(len(x) for x in chunks)
        acc = 0
        starts = []
        for ch in chunks:
            target = total * acc / n_all
            i = int(np.searchsorted(speech_t, target + 1e-6))
            starts.append(ON[k] + i * hop)
            acc += len(ch)
        for j, ch in enumerate(chunks):
            t1 = starts[j + 1] if j + 1 < len(chunks) else END[k] + 0.15
            SUBS.append((starts[j] - 0.05, t1, ch))

if __name__ == '__main__':
    for s in SCENES:
        print(f'{s[0]:12s} {s[1]:7.2f} {s[2]:7.2f}  {s[2] - s[1]:5.1f}s')
    print('DUR', round(DUR, 2), 'subs', len(SUBS))
    for s in SUBS[:12]:
        print(round(s[0], 2), round(s[1], 2), s[2])
