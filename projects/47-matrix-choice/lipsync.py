"""Lip sync from the voice takes (author: «персонаж говорит, но потом не шевелится»).

Per 10 ms of every line: loudness (RMS, smoothed, normalised to the line's own 90th percentile) and spectral
brightness (centroid). They pick a mouth shape (viseme) from the Fish lip sheet of the same head:
closed · slight · «а» · «о/у» · «и/е» · «м/п/б». mouth(t) -> list of (viseme, weight) and the jaw openness 0..1
(used for a tiny head bob). Content time, so RubUp pauses it with everything else."""
import functools
import wave
import numpy as np
from timeline import ON, END, TAKES

VIS = ['closed', 'slight', 'aa', 'oo', 'ee', 'mbp']
HOP = 0.01


@functools.lru_cache(None)
def _line(k):
    with wave.open(str(TAKES[k])) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(1)
    hop, win = int(sr * HOP), int(sr * 0.03)
    n = max(1, (len(x) - win) // hop)
    rms = np.zeros(n)
    cen = np.zeros(n)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    hann = np.hanning(win)
    for i in range(n):
        seg = x[i * hop:i * hop + win] * hann
        rms[i] = np.sqrt((seg ** 2).mean())
        sp = np.abs(np.fft.rfft(seg))
        cen[i] = (sp * freqs).sum() / (sp.sum() + 1e-9)
    rms = np.convolve(rms, np.ones(3) / 3, 'same')
    op = np.clip(rms / (np.percentile(rms, 90) + 1e-9), 0, 1.2)
    voiced = cen[op > 0.38]
    lo, hi = (np.percentile(voiced, 30), np.percentile(voiced, 75)) if len(voiced) > 5 else (1100, 2300)
    return op, (cen, lo, hi)


def _vis_at(op, cen, i):
    o = op[i]
    if o < 0.12:
        nxt = op[min(len(op) - 1, i + 4)]
        return 'mbp' if nxt > 0.35 else 'closed'      # lips press just before a burst («п», «б», «м»)
    if o < 0.38:
        return 'slight'
    c, lo, hi = cen[0][i], cen[1], cen[2]          # brightness relative to this line (a deep voice)
    if c > hi:
        return 'ee'
    if c < lo:
        return 'oo'
    return 'aa'


def mouth(t):
    """(list of (viseme, weight), openness) or (None, 0) when Morpheus is silent."""
    for k in range(len(ON)):
        if ON[k] - 0.02 <= t < END[k] + 0.06:
            op, cen = _line(k)
            f = (t - ON[k]) / HOP
            i = int(np.clip(f, 0, len(op) - 1))
            j = min(len(op) - 1, i + 1)
            a, b = _vis_at(op, cen, i), _vis_at(op, cen, j)
            w = f - int(f)
            openness = float(op[i] * (1 - w) + op[j] * w)
            if a == b:
                return [(a, 1.0)], openness
            return [(a, 1 - w), (b, w)], openness
    return None, 0.0


def speaking(t):
    return any(ON[k] - 0.05 <= t < END[k] + 0.1 for k in range(len(ON)))
