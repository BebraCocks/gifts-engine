"""Music for 35-zodiac-wine «Гороскоп из телеги», synthesized in code: a soft «night sky» bed, 76 BPM,
ля минор Am(add9) – Fmaj7 – C – G(sus4) (new for the series: the price duels used quiz-show grooves).
- pad: detuned saw voices through a low-pass, slow swell per chord (2 bars each);
- celesta: bell arpeggio in eighths (sine partials 1, 2.76, 5.4 with fast decay), thinned out under the hook;
- each sign landing (SIGN_IN): a low sub swell; each forecast (FORECAST): a short rising bell run;
- outro: the groove continues, last chord rings out to the end.
Content time, so RubUp pauses it like the voice. audio.py calls music(n, sr)."""
import math
import numpy as np
from scipy.signal import butter, sosfilt
from timeline import DUR, SIGN_IN, FORECAST, OUTRO

BPM = 76.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
PROG = [(45, (57, 60, 64, 71)), (41, (57, 60, 64, 65)), (48, (55, 60, 64, 67)), (43, (55, 60, 62, 67))]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, sr):
    return sosfilt(butter(2, f, 'lowpass', fs=sr, output='sos'), x)


def pad(n, sr):
    out = np.zeros((n, 2))
    span = int(2 * BAR * sr)
    t = np.arange(span) / sr
    env = np.minimum(1, t / 1.2) * np.minimum(1, (span / sr - t) / 0.9)
    for k in range(int(n / span) + 1):
        root, ch = PROG[k % 4]
        y = np.zeros((span, 2))
        for i, m in enumerate(ch):
            for d, pan in ((-0.07, 0.2), (0.07, 0.8)):
                f = hz(m + d)
                ph = (t * f + 0.13 * i) % 1.0
                v = (2 * ph - 1) * 0.12
                y[:, 0] += v * (1 - pan)
                y[:, 1] += v * pan
        y[:, 0] += np.sin(2 * np.pi * hz(root) * t) * 0.25
        y[:, 1] += np.sin(2 * np.pi * hz(root) * t) * 0.25
        y = np.stack([lp(y[:, c], 900, sr) for c in (0, 1)], 1) * env[:, None]
        a = k * span
        m_ = min(span, n - a)
        if m_ <= 0:
            break
        out[a:a + m_] += y[:m_]
    return out


def bell(f, sr, dur=1.4):
    t = np.arange(int(dur * sr)) / sr
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t * 3.0) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 7)
         + 0.12 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 12))
    return y * (1 - np.exp(-t * 600))


def add(buf, t, y, gain, pan, sr):
    a = int(round(t * sr))
    if a >= len(buf) or a < 0:
        return
    y = y[:len(buf) - a]
    buf[a:a + len(y), 0] += y * gain * math.cos((pan + 1) * math.pi / 4) * 1.414
    buf[a:a + len(y), 1] += y * gain * math.sin((pan + 1) * math.pi / 4) * 1.414


def music(n, sr):
    out = pad(n, sr) * 0.55
    rng = np.random.default_rng(35)
    step = BEAT / 2
    k = 0
    while k * step < DUR:
        t = k * step
        root, ch = PROG[int(t / (2 * BAR)) % 4]
        notes = [m + 12 for m in ch] + [ch[1] + 24]
        m = notes[[0, 2, 1, 3, 4, 3, 2, 1][k % 8]]
        thin = t < SIGN_IN[0] and k % 2           # the hook stays airy under the long sentence
        if not thin:
            add(out, t, bell(hz(m), sr), 0.075 * (0.85 + 0.3 * rng.random()), 0.5 * math.sin(k * 0.9), sr)
        k += 1
    for t0 in SIGN_IN:                                 # sub swell under each landing
        tt = np.arange(int(1.6 * sr)) / sr
        y = np.sin(2 * np.pi * 55 * tt) * np.minimum(1, tt / 0.08) * np.exp(-tt * 2.2)
        add(out, t0 - 0.05, y, 0.35, 0.0, sr)
    for t0 in FORECAST:                                # rising bell run on each forecast
        for i, m in enumerate((76, 79, 83, 88)):
            add(out, t0 + 0.07 * i, bell(hz(m), sr, 1.0), 0.06, -0.4 + 0.27 * i, sr)
    fade_in = np.minimum(1, np.arange(n) / sr / 0.4)
    fade_out = np.clip((DUR - np.arange(n) / sr) / 0.6, 0, 1)
    out *= (fade_in * fade_out)[:, None]
    return out / (np.abs(out).max() + 1e-9) * 0.7
