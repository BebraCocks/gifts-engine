"""Музыка кодом (третий ролик): весёлый «комиксный» фанк 112 BPM — щипковый бас, свистящая мелодия,
хлопки, тарелочки, удары-«стопы» на награды. build/music.wav"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import V, T, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
B = 60 / 112
rng = np.random.default_rng(61)
N = int((DUR + 1) * SR)
mix = np.zeros(N, np.float32)


def put(y, t, g=1.0):
    i = int(t * SR)
    if 0 <= i < N:
        j = min(N, i + len(y)); mix[i:j] += y[:j - i] * g


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def pluck(f, dur, a=0.14):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.tanh(3 * np.sin(2 * math.pi * f * t)) * np.exp(-t * 7)
    return (y * a).astype(np.float32)


def whistle(f, dur, a=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.01 * np.sin(2 * math.pi * 6 * t)
    y = np.sin(2 * math.pi * np.cumsum(f * vib) / SR) * np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.05)
    return (y * a).astype(np.float32)


def kick(a=0.55):
    n = int(0.28 * SR); t = np.arange(n) / SR
    f = 50 + 100 * np.exp(-t * 30)
    return (np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 10) * a).astype(np.float32)


def clap(a=0.2):
    n = int(0.18 * SR); t = np.arange(n) / SR
    return (np.diff(rng.standard_normal(n), prepend=0) * np.exp(-t * 25) * a).astype(np.float32)


def tick(a=0.05):
    n = int(0.03 * SR)
    return (np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / SR * 120) * a).astype(np.float32)


BASS = [43, 43, 46, 48, 43, 43, 50, 48]          # G-фанк
MEL = [79, 77, 79, 82, 79, 77, 74, 77, 79, 82, 84, 82, 79, 77, 79, 0]


def groove(t0, t1, mel=True):
    t, k = t0, 0
    while t < t1 - 0.02:
        for s in range(8):
            ts = t + s * B / 2
            if ts >= t1:
                break
            put(pluck(hz(BASS[s]), B / 2 * 0.9), ts)
            if s % 2 == 0:
                put(kick(), ts) if s in (0, 4) else None
                put(tick(), ts + B / 4)
            if s in (2, 6):
                put(clap(), ts)
            if mel:
                m = MEL[(k * 8 + s) % 16]
                if m:
                    put(whistle(hz(m), B / 2 * 0.85), ts)
        t += 4 * B; k += 1


put(kick(0.4), V['L1'])
for j in range(3):                                   # «тик-тик-тик» до взрыва точки
    put(tick(0.12), V['L1'] + 0.3 + j * 0.35)
put(kick(0.9), T['boom']); put(clap(0.35), T['boom'])
groove(T['boom'], V['L3'], mel=False)
groove(V['L3'], DUR + 0.5, mel=True)
for x in T['tier']:
    put(kick(0.8), x); put(clap(0.3), x)
for x in (T['self0'], T['sell'], T['give']):
    put(clap(0.3), x)
fade = int(0.8 * SR); e = int(DUR * SR)
mix[e - fade:e] *= np.linspace(1, 0, fade); mix[e:] = 0
mix = np.tanh(mix * 1.5) / 1.5
st = np.stack([mix, np.roll(mix, 280) * 0.95], 1).astype(np.float32)
out = HERE / 'build' / 'music.wav'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=st.tobytes(), check=True)
print('OK', out)
