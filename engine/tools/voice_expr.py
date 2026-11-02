"""Measure how expressive a voice take is (to compare TTS style settings without listening).

    python engine/tools/voice_expr.py take1.wav take2.wav ...
Prints: pitch range in semitones (p10..p90 of voiced frames), pitch std, loudness std (dB), speaking rate proxy.
Higher pitch range / std = livelier intonation. A flat reading is ~2-3 st; an expressive one 5+ st.
"""
import sys
import wave

import numpy as np


def load(p):
    with wave.open(p) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    return (x.reshape(-1, ch).mean(1) if ch > 1 else x), sr


def f0_track(x, sr, fmin=70, fmax=260, hop=0.01, win=0.045):
    """Autocorrelation pitch with octave-error cleanup (good enough to compare takes, not a tuner)."""
    n, h = int(win * sr), int(hop * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    f0, rms = [], []
    for i in range(0, len(x) - n, h):
        fr = x[i:i + n] * np.hanning(n)
        e = np.sqrt((fr ** 2).mean())
        rms.append(e)
        if e < 0.015:
            f0.append(np.nan)
            continue
        ac = np.correlate(fr, fr, "full")[n - 1:]
        ac /= ac[0] + 1e-9
        k = lo + int(np.argmax(ac[lo:hi]))
        f0.append(sr / k if ac[k] > 0.6 else np.nan)
    f0 = np.array(f0)
    v = ~np.isnan(f0)
    if v.sum() > 5:
        med = np.median(f0[v])
        for j in np.nonzero(v)[0]:                      # fold octave jumps back toward the median
            while f0[j] > med * 1.6:
                f0[j] /= 2
            while f0[j] < med / 1.6:
                f0[j] *= 2
        from scipy.ndimage import median_filter
        tmp = np.where(v, f0, med)
        f0 = np.where(v, median_filter(tmp, 5), np.nan)
    return f0, np.array(rms)


def measure(path, skip=0.5):
    x, sr = load(path)
    x = x[int(skip * sr):]                       # skip the TTS start blip
    f0, rms = f0_track(x, sr)
    v = f0[~np.isnan(f0)]
    if len(v) < 10:
        return None
    st = 12 * np.log2(v / np.median(v))
    db = 20 * np.log10(rms[rms > 0.01] + 1e-6)
    return dict(range_st=float(np.percentile(st, 90) - np.percentile(st, 10)), std_st=float(st.std()),
                loud_std=float(db.std()), median_hz=float(np.median(v)), voiced=float(len(v) / max(1, len(f0))))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        m = measure(p)
        print(p, {k: round(v, 2) for k, v in m.items()} if m else "too short")
