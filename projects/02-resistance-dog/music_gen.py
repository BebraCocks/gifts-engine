"""Fallback score synthesized in code (used only while the author's tracks are missing).
Four cues in OUTPUT time: playful (hook/Spotty), tension (2018), rise (legend/TON/gifts), drive (models/final).
Writes build/music_fallback.wav (48 kHz stereo)."""
import math
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import banner
from events import AD_STOPS, SHOTS
from timeline import DUR

SR = 48000
BR = banner.Breaks(AD_STOPS, cy=960)
OUT_DUR = BR.out_dur(DUR)
RNG = np.random.default_rng(3)


def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.2, length=None):
    L = n
    t = np.arange(L) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    if length is not None:
        rel = t > length
        e[rel] *= np.exp(-(t[rel] - length) / r)
    return e


def osc(f, n, kind='saw', detune=0.0):
    t = np.arange(n) / SR
    out = 0
    for dt in ((-detune, 0, detune) if detune else (0,)):
        ph = 2 * np.pi * f * (1 + dt) * t
        if kind == 'sine':
            out = out + np.sin(ph)
        elif kind == 'tri':
            out = out + 2 / np.pi * np.arcsin(np.sin(ph))
        elif kind == 'square':
            out = out + np.tanh(3 * np.sin(ph))
        else:
            out = out + 2 * ((f * (1 + dt) * t) % 1) - 1
    return out / (3 if detune else 1)


def lp(x, f):
    return sosfilt(butter(2, min(f, SR / 2 - 100), 'lowpass', fs=SR, output='sos'), x)


def hp(x, f):
    return sosfilt(butter(2, f, 'highpass', fs=SR, output='sos'), x)


class Track:
    def __init__(self, dur):
        self.x = np.zeros((int(dur * SR) + SR, 2))

    def add(self, t, y, gain=1.0, pan=0.0):
        a = int(t * SR)
        if y.ndim == 1:
            l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            y = np.stack([y * l, y * r], 1) * 1.41
        m = min(len(y), len(self.x) - a)
        if m > 0 and a >= 0:
            self.x[a:a + m] += y[:m] * gain


def pluck(f, d=0.5):
    n = int(d * SR)
    y = osc(f, n, 'tri') * np.exp(-np.arange(n) / SR * 9) + 0.3 * osc(2 * f, n, 'sine') * np.exp(-np.arange(n) / SR * 14)
    return y * np.minimum(1, np.arange(n) / (0.002 * SR))


def bell(f, d=1.2):
    n = int(d * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 6)) * np.exp(-t * 3.5)


def pad(fs, d, cutoff=1400, att=0.6):
    n = int(d * SR)
    y = sum(osc(f, n, 'saw', 0.004) for f in fs) / len(fs)
    y = lp(y, cutoff)
    t = np.arange(n) / SR
    e = np.minimum(1, t / att) * np.minimum(1, (d - t) / 0.8)
    return y * e


def kick(d=0.45):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8)


def snare(d=0.25):
    n = int(d * SR)
    t = np.arange(n) / SR
    return hp(RNG.standard_normal(n), 1500) * np.exp(-t * 18) * 0.6 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.4


def hat(d=0.06):
    n = int(d * SR)
    return hp(RNG.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR * 70)


def tom(f=90, d=0.6):
    n = int(d * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-t * 20))) / SR) * np.exp(-t * 6)


def bass(f, d):
    n = int(d * SR)
    return lp(osc(f, n, 'saw'), 500) * env_adsr(n, 0.005, 0.15, 0.5, 0.08, d * 0.8)


def reverb(x, decay=1.6, mix=0.22):
    n = int(decay * SR)
    ir = RNG.standard_normal((n, 2)) * np.exp(-np.arange(n) / SR * 5 / decay)[:, None]
    ir[:, 0] = lp(ir[:, 0], 6000)
    ir[:, 1] = lp(ir[:, 1], 6000)
    wet = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    wet *= np.abs(x).max() / (np.abs(wet).max() + 1e-9)
    return x * (1 - mix) + wet * mix


def out_time(content_t):
    """Content time -> output time (after RubUp breaks)."""
    return content_t + BR.extra * sum(1 for s in AD_STOPS if content_t > s)


def cue_playful(T, t0, t1):
    bpm = 104
    b = 60 / bpm
    prog = [(60, 64, 67), (57, 60, 64), (53, 57, 60), (55, 59, 62)]          # C Am F G
    mel = [72, 74, 76, 79, 76, 74, 72, 67]
    t, k = t0, 0
    while t < t1 - 0.2:
        ch = prog[(k // 8) % 4]
        if k % 8 == 0:
            T.add(t, pad([note(m) for m in ch], 8 * b, 1800, 0.3), 0.07)
            T.add(t, bass(note(ch[0] - 24), 2 * b), 0.22)
        if k % 8 == 4:
            T.add(t, bass(note(ch[0] - 24), 2 * b), 0.2)
        T.add(t, pluck(note(ch[k % 3] + 12)), 0.12, -0.3 + 0.2 * (k % 4))
        if k % 2 == 1:
            T.add(t, bell(note(mel[(k // 2) % 8]), 0.9), 0.05, 0.4)
        if k % 4 == 2:
            T.add(t, hat(), 0.08, 0.2)
        t += b / 2 if False else b
        k += 1


def cue_tension(T, t0, t1):
    bpm = 120
    b = 60 / bpm
    prog = [45, 45, 41, 43]                                                    # A A F G (minor feel)
    t, k = t0, 0
    while t < t1 - 0.1:
        root = prog[(k // 16) % 4]
        if k % 16 == 0:
            T.add(t, pad([note(root + 12), note(root + 15), note(root + 19)], 16 * b / 2, 900, 1.0), 0.08)
        T.add(t, bass(note(root - 12), b / 2 * 0.9), 0.24)
        if k % 2 == 0:
            T.add(t, hat(0.04), 0.07, 0.3)
        if k % 8 == 0:
            T.add(t, kick(), 0.32)
        if k % 8 == 4:
            T.add(t, tom(70), 0.18)
        if k % 4 == 3:
            T.add(t, pluck(note(root + 24 + (3 if k % 8 == 7 else 0)), 0.3), 0.06, 0.5)
        t += b / 2
        k += 1


def cue_rise(T, t0, t1):
    bpm = 96
    b = 60 / bpm
    prog = [(57, 60, 64), (53, 57, 60), (60, 64, 67), (55, 59, 62)]          # Am F C G
    t, k = t0, 0
    while t < t1 - 0.1:
        ch = prog[(k // 4) % 4]
        x = (t - t0) / (t1 - t0)
        if k % 4 == 0:
            T.add(t, pad([note(m) for m in ch] + [note(ch[0] + 12)], 4 * b, 1200 + 2000 * x, 0.4), 0.08 + 0.04 * x)
            T.add(t, bass(note(ch[0] - 24), 3.5 * b), 0.22)
        T.add(t, tom(80 + 10 * (k % 2)), 0.12 + 0.18 * x)
        if x > 0.4:
            T.add(t + b / 2, tom(110), 0.1 * x)
        if k % 2 == 1:
            T.add(t, snare(), 0.06 + 0.1 * x)
        t += b
        k += 1


def cue_drive(T, t0, t1):
    bpm = 118
    b = 60 / bpm
    prog = [(62, 65, 69), (58, 62, 65), (60, 64, 67), (57, 61, 64)]          # Dm Bb C A
    arp = [0, 1, 2, 1, 2, 0, 2, 1]
    t, k = t0, 0
    while t < t1 - 1.6:
        ch = prog[(k // 8) % 4]
        if k % 8 == 0:
            T.add(t, pad([note(m) for m in ch], 8 * b / 2 * 2, 2200, 0.2), 0.07)
        if k % 2 == 0:
            T.add(t, kick(), 0.3)
            T.add(t, bass(note(ch[0] - 24), b * 0.45), 0.2)
        else:
            T.add(t, hat(), 0.09, 0.25)
        if k % 4 == 2:
            T.add(t, snare(), 0.13)
        T.add(t, pluck(note(ch[arp[k % 8]] + 12), 0.25), 0.07, 0.4 * math.sin(k))
        t += b / 2
        k += 1
    T.add(t1 - 1.6, pad([note(62), note(65), note(69), note(74)], 3.0, 2500, 0.05), 0.12)


def build():
    T = Track(OUT_DUR + 2)
    names = {n: (a, b) for n, a, b in SHOTS}
    cue_playful(T, 0.0, out_time(AD_STOPS[0]) - 0.05)
    cue_tension(T, out_time(AD_STOPS[0] + 0.01) - 0.2, out_time(names['S09_legend'][0]))
    cue_rise(T, out_time(names['S09_legend'][0]), out_time(AD_STOPS[1]))
    cue_drive(T, out_time(AD_STOPS[1] + 0.01) - 0.2, OUT_DUR)
    x = reverb(T.x[:int(OUT_DUR * SR)], 1.8, 0.25)
    x /= np.abs(x).max() + 1e-9
    return x * 0.7


if __name__ == '__main__':
    import wave
    x = build()
    p = Path(__file__).resolve().parent / 'build' / 'music_fallback.wav'
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    print('->', p, round(len(x) / SR, 2), 's')
