"""30-second demo of the "Nizshii" score, synthesized in code.
Dark industrial ambient, D minor, 70 BPM: sub drone + vent hiss -> heavy metal pulse -> cold pad Dm-Bb-Gm-A -> sparse bells.
Usage: python3 nizshii_music_demo.py OUT.wav"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
DUR = 30.0
N = int(SR * DUR)
BPM = 70.0
BEAT = 60.0 / BPM
rng = np.random.default_rng(11)
t = np.arange(N) / SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def filt(x, kind, f, order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def env_ad(n, a, d):
    """attack a sec linear, exponential decay with time constant d sec"""
    tt = np.arange(n) / SR
    e = np.exp(-tt / d)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def fade(x, t0, t1, up=True):
    g = np.clip((t - t0) / (t1 - t0), 0, 1)
    return x * (g if up else 1 - g)


L = np.zeros(N)
R = np.zeros(N)


def add(start, y, gain=1.0, pan=0.0):
    a = int(start * SR)
    b = min(N, a + len(y))
    if b <= a:
        return
    y = y[:b - a] * gain
    L[a:b] += y * np.sqrt((1 - pan) / 2)
    R[a:b] += y * np.sqrt((1 + pan) / 2)


# 1. Sub drone: D1, A1, D2 with slow breathing + low rumble
lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
drone = (np.sin(2 * np.pi * hz(26) * t) + 0.6 * np.sin(2 * np.pi * hz(33) * t + 1.0)
         + 0.35 * np.sin(2 * np.pi * hz(38.03) * t)) * lfo
rumble = filt(rng.standard_normal(N), 'lowpass', 60, 4) * 3.0  # only deep sub, no audible hiss
bed = fade(drone * 0.26 + rumble * 0.10, 0, 5)
add(0, bed, 1.0, 0.0)

# 2. Ventilation hiss: band-passed noise, two slightly different channels
for pan, seed in ((-0.7, 1), (0.7, 2)):
    nz = np.random.default_rng(seed).standard_normal(N)
    hiss = filt(nz, 'bandpass', [700, 3200], 2)
    hiss *= 0.6 + 0.4 * np.sin(2 * np.pi * (0.11 + seed * 0.03) * t + seed)
    pass  # hiss layer removed (author: audible noise)

# 3. Heavy pulse from 6 s: thud on every beat, metal clank on beats 2 and 4
def thud():
    n = int(0.6 * SR)
    tt = np.arange(n) / SR
    f = 35 + 30 * np.exp(-tt / 0.06)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env_ad(n, 0.003, 0.18)


def clank(seed):
    n = int(1.4 * SR)
    r = np.random.default_rng(seed)
    burst = r.standard_normal(n) * env_ad(n, 0.001, 0.02)
    y = np.zeros(n)
    for f, d, g in ((410, 0.5, 1.0), (1127, 0.35, 0.7), (2268, 0.25, 0.45), (3190, 0.18, 0.3)):
        f2 = f * (1 + r.uniform(-0.03, 0.03))
        y += filt(burst, 'bandpass', [f2 * 0.98, f2 * 1.02], 2) * env_ad(n, 0.001, d) * g * 40
    return y


start, end = 6.0, 27.5
k = 0
tb = start
while tb < end:
    g = min(1.0, (tb - start) / 4 + 0.3)
    add(tb, thud(), 0.55 * g)
    if k % 2 == 1:
        add(tb + 0.02, clank(100 + k), 0.12 * g, -0.4 if k % 4 == 1 else 0.4)
    k += 1
    tb += BEAT

# 4. Cold pad from 12 s: Dm - Bb - Gm - A, detuned saws, low-passed
def saw(f, n, det):
    ph = np.cumsum(np.full(n, f * det)) / SR
    return 2 * (ph % 1.0) - 1


chords = [(50, 53, 57), (46, 50, 53), (43, 46, 50), (45, 49, 52)]   # Dm Bb Gm A
clen = 4.5
for i, ch in enumerate(chords):
    t0 = 12.0 + i * clen
    n = int((clen + 2.0) * SR)
    y = np.zeros(n)
    for m in ch:
        for det in (0.996, 1.0, 1.005):
            y += saw(hz(m), n, det)
    y = filt(y, 'lowpass', 700, 2)
    e = np.ones(n)
    na, nr = int(1.8 * SR), int(2.0 * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    add(t0, y * e, 0.035, -0.3 if i % 2 else 0.3)

# 5. Sparse cold bells (FM), into the reverb
def bell(m, dur=3.5):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = hz(m)
    mod = np.sin(2 * np.pi * f * 1.41 * tt) * 2.2 * np.exp(-tt / 0.6)
    return np.sin(2 * np.pi * f * tt + mod) * env_ad(n, 0.002, 1.1)


for tb, m, pan in ((14.0, 69, -0.5), (17.5, 77, 0.5), (21.0, 74, -0.3), (24.5, 76, 0.4), (27.0, 74, 0.0)):
    add(tb, bell(m), 0.10, pan)

# Reverb: synthetic exponentially decaying stereo IR (dark metal hall)
irn = int(2.8 * SR)
irt = np.arange(irn) / SR
irL = filt(rng.standard_normal(irn), 'lowpass', 2500) * np.exp(-irt / 0.7)
irR = filt(rng.standard_normal(irn), 'lowpass', 2500) * np.exp(-irt / 0.7)
irL /= np.sqrt(np.sum(irL ** 2))
irR /= np.sqrt(np.sum(irR ** 2))
wetL = fftconvolve(filt(L, 'highpass', 150), irL)[:N]
wetR = fftconvolve(filt(R, 'highpass', 150), irR)[:N]
outL = L + wetL * 0.45
outR = R + wetR * 0.45

# Master: fade out, soft clip, normalise peak
out = np.stack([outL, outR], 1)
out = out * np.clip((DUR - t) / 3.0, 0, 1)[:, None]
out = np.tanh(out * 1.5) / 1.5
out /= np.max(np.abs(out)) / 0.89

import wave
pcm = (out * 32767).astype('<i2')
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('ok', DUR)
