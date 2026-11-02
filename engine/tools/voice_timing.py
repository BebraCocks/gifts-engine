"""Report speech start and end for WAV files: python engine/tools/voice_timing.py projects/01-topic/voice/*.wav"""
import sys
import wave

import numpy as np


def analyze(path):
    with wave.open(path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(1)
    hop = sr // 100
    env = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(env + 1e-6)
    if not len(db) or not len(x) or np.max(np.abs(x)) < 1e-6:
        return dict(duration=round(len(x) / sr, 3), speech_start=0.0, speech_end=0.0, pauses=[])
    thr = db.max() - 32
    on = np.nonzero(db > thr)[0]
    pauses, run = [], 0
    for k in range(on[0], on[-1]):
        run = run + 1 if db[k] < thr else 0
        if run == 12:
            pauses.append(round((k - 11) / 100, 2))
    return dict(duration=round(len(x) / sr, 3), speech_start=on[0] / 100, speech_end=(on[-1] + 1) / 100, pauses=pauses)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, analyze(p))
