"""Download chosen Fish Audio takes (takes.json), trim silence, shorten long gaps -> voice/LNN.wav (+ .map.json).
leading/trailing silence trimmed, long internal silences shortened to MAX_GAP (the delivery itself is not
sped up beyond TEMPO). drama-3 reads this voice slowly (57 s of speech for a 59 s video with RubUp), so every
take is time-stretched by TEMPO with ffmpeg atempo — pitch unchanged. The paid takes stay in voice/raw/<task id>.wav."""
import json
import subprocess
import urllib.request
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / 'voice' / 'raw'
URL = 'https://platform.r2.fish.audio/tasks/2026-11-06/{}.mp3'
SR = 48000
SEGMAP = []
KEEP_LEAD, KEEP_TAIL = 0.03, 0.10
MAX_GAP = {}
DEFAULT_GAP = 0.16
TEMPO = 1.0


def fetch(task):
    wav = RAW / f'{task}.wav'
    if not wav.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        mp3 = RAW / f'{task}.mp3'
        if not mp3.exists():
            urllib.request.urlretrieve(URL.format(task), mp3)
        subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', str(mp3), '-ar', str(SR),
                        '-ac', '1', str(wav)], check=True)
    with wave.open(str(wav)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64)


def stretch(y):
    if TEMPO == 1.0:
        return y
    a, b = RAW / '_in.wav', RAW / '_out.wav'
    with wave.open(str(a), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.clip(y, -32767, 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', str(a), '-af', f'atempo={TEMPO}',
                    str(b)], check=True)
    with wave.open(str(b)) as w:
        out = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64)
    a.unlink()
    b.unlink()
    return out


def tighten(x, max_gap):
    hop = SR // 100
    e = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(e / 32768 + 1e-6)
    loud = db > db.max() - 36
    on = np.nonzero(loud)[0]
    a, b = on[0], on[-1] + 1
    keep = np.zeros(len(e), bool)
    keep[max(0, a - int(KEEP_LEAD * 100)):min(len(e), b + int(KEEP_TAIL * 100))] = True
    k = a
    while k < b:                                   # internal silences longer than max_gap -> max_gap
        if not loud[k]:
            j = k
            while j < b and not loud[j]:
                j += 1
            gap = j - k
            lim = int(max_gap * 100)
            if gap > lim:
                cut0 = k + lim // 2
                keep[cut0:cut0 + gap - lim] = False
            k = j
        else:
            k += 1
    segs, out = [], []
    global SEGMAP
    SEGMAP = []                                    # (raw start s, out start s, length s) for ASR word times
    k = 0
    pos = 0
    f = int(0.005 * SR)
    while k < len(e):                              # join kept frames with 5 ms crossfades
        if keep[k]:
            j = k
            while j < len(e) and keep[j]:
                j += 1
            segs.append(x[k * hop:j * hop].copy())
            SEGMAP.append((k * hop / SR, pos / SR, (j - k) * hop / SR))
            pos += (j - k) * hop - (f if len(segs) > 1 else 0)
            k = j
        else:
            k += 1
    f = int(0.005 * SR)
    for s in segs:
        if out and len(s) > 2 * f and len(out[-1]) > 2 * f:
            ramp = np.linspace(0, 1, f)
            out[-1][-f:] = out[-1][-f:] * (1 - ramp) + s[:f] * ramp
            s = s[f:]
        out.append(s)
    y = np.concatenate(out)
    n = int(0.01 * SR)
    y[-n:] *= np.linspace(1, 0, n)
    return y


if __name__ == '__main__':
    takes = {k: v for k, v in json.loads((HERE / 'takes.json').read_text()).items() if k.startswith('L')}
    total = 0
    for line, ids in sorted(takes.items()):
        y = stretch(tighten(fetch(ids[0]), MAX_GAP.get(line, DEFAULT_GAP)))
        with wave.open(str(HERE / 'voice' / f'{line}.wav'), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(np.clip(y, -32767, 32767).astype('<i2').tobytes())
        (HERE / 'voice' / f'{line}.map.json').write_text(json.dumps({'tempo': TEMPO, 'segments': SEGMAP}))
        total += len(y) / SR
        print(f'{line} <- {ids[0][:8]}: {len(y) / SR:.2f} s')
    print(f'speech total {total:.2f} s')
