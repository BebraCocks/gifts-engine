"""Chosen Fish Audio takes (takes.json) -> voice/LNN.wav: lead/tail silence trimmed, internal gaps > MAX_GAP shortened,
optional per-line atempo (pitch unchanged). Paid takes stay in voice/raw/<task id>.mp3."""
import json
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / 'voice' / 'raw'
URL = 'https://platform.r2.fish.audio/tasks/2026-11-12/{}.mp3'
SR = 48000
MAX_GAP = 0.22
GAP = {'W0': 0.30, 'W8': 0.30, 'W9': 0.30}
TEMPO = {}                                   # line -> atempo
PICK = {}                                    # line -> take index (default 0)


def load(task):
    mp3 = RAW / f'{task}.mp3'
    if not mp3.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        subprocess.run(['curl', '-sSfL', '--retry', '5', '-o', str(mp3), URL.format(task)], check=True)
    raw = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', str(mp3), '-ar', str(SR), '-ac', '1',
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<i2').astype(np.float64)


def tighten(x, max_gap):
    hop = SR // 100
    e = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(e / 32768 + 1e-6)
    loud = db > db.max() - 38
    on = np.nonzero(loud)[0]
    a, b = on[0], on[-1] + 1
    keep = np.zeros(len(e), bool)
    keep[max(0, a - 3):min(len(e), b + 10)] = True
    k, lim = a, int(max_gap * 100)
    while k < b:
        if loud[k]:
            k += 1
            continue
        j = k
        while j < b and not loud[j]:
            j += 1
        if j - k > lim:
            keep[k + lim // 2:j - lim // 2] = False
        k = j
    m = np.repeat(keep, hop)
    m = np.concatenate([m, np.zeros(len(x) - len(m), bool)])
    return x[m]


def stretch(y, tempo):
    if tempo == 1.0:
        return y
    p = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-af', f'atempo={tempo}', '-f', 's16le', '-'],
                       input=np.clip(y, -32767, 32767).astype('<i2').tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, '<i2').astype(np.float64)


def main():
    takes = json.loads((HERE / 'takes.json').read_text(encoding='utf-8'))
    out = {}
    for line, ids in takes.items():
        if line.startswith('_'):
            continue
        y = stretch(tighten(load(ids[PICK.get(line, 0)]), GAP.get(line, MAX_GAP)), TEMPO.get(line, 1.0))
        f = 6 * SR // 1000
        y[:f] *= np.linspace(0, 1, f)
        y[-f:] *= np.linspace(1, 0, f)
        with wave.open(str(HERE / 'voice' / f'{line}.wav'), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(np.clip(y, -32767, 32767).astype('<i2').tobytes())
        out[line] = round(len(y) / SR, 3)
    (HERE / 'voice' / 'durations.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in out.items():
        print(k, v)


if __name__ == '__main__':
    main()
