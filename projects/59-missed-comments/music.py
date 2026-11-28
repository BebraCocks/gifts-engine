"""Музыка кодом: бодрый праздничный бит 128 BPM (бочка, хлопок, хэты, бас, яркие аккорды, колокольчики),
удар на старте, подъём перед карточками, «дождь» из звонов на раздаче. build/music.wav"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import V, T, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
BPM = 128
B = 60 / BPM
rng = np.random.default_rng(59)
N = int((DUR + 1) * SR)
mix = np.zeros(N, np.float32)


def put(y, t, g=1.0):
    i = int(t * SR)
    if 0 <= i < N:
        j = min(N, i + len(y)); mix[i:j] += y[:j - i] * g


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def kick(a=0.55):
    n = int(0.32 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 32)
    return (np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * a).astype(np.float32)


def clap(a=0.22):
    n = int(0.2 * SR); t = np.arange(n) / SR
    y = np.diff(rng.standard_normal(n), prepend=0) * (np.exp(-t * 22) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035))
    return (y * a).astype(np.float32)


def hat(a=0.06, open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    y = np.diff(np.diff(rng.standard_normal(n), prepend=0), prepend=0) * np.exp(-np.arange(n) / SR * (14 if open_ else 70))
    return (y * a).astype(np.float32)


def saw(f, dur, a=0.05):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sum(((t * f * (1 + d)) % 1 * 2 - 1) for d in (-0.006, 0, 0.007)) / 3
    k = 8; y = np.convolve(y, np.ones(k) / k, 'same')          # чуть мягче
    e = np.minimum(1, t / 0.01) * np.exp(-t * 3.5)
    return (y * e * a).astype(np.float32)


def bell(f, dur=1.0, a=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * math.pi * f * t + 2 * np.sin(2 * math.pi * f * 3.5 * t) * np.exp(-t * 5)) * np.exp(-t * 3) * a).astype(np.float32)


def bass(f, dur, a=0.2):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.tanh(2 * np.sin(2 * math.pi * f * t)) * np.exp(-t * 2.5) * a).astype(np.float32)


CH = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 67]]   # Cmaj7 Am7 Fmaj7 G
MEL = [79, 76, 79, 81, 79, 76, 74, 76]


def groove(t0, t1, full=True, gain=1.0):
    bar, k = 4 * B, 0
    t = t0
    while t < t1 - 0.02:
        ch = CH[k % 4]
        for b in range(4):
            tb = t + b * B
            if tb >= t1:
                break
            put(kick(), tb, gain)
            if b % 2 == 1:
                put(clap(), tb, gain)
            for h in (0.5,):
                put(hat(), tb + h * B, gain)
            if full:
                put(hat(0.03), tb + 0.25 * B, gain); put(hat(0.03), tb + 0.75 * B, gain)
            put(bass(hz(ch[0] - 24), B * 0.9), tb, gain)
            for m in ch:
                put(saw(hz(m), B * 0.45), tb + 0.5 * B, gain * (0.9 if full else 0.6))
        if full:
            for j in range(8):
                put(bell(hz(MEL[(k * 8 + j) % 8]), 0.6, 0.035), t + j * B / 2, gain)
        t += bar; k += 1


# старт: удар + сразу грув
put(kick(0.8), V['L1']); put(clap(0.3), V['L1'])
groove(V['L1'], V['L3'] - 2 * B, full=False)
# подъём перед карточками
n = int(2 * B * SR); tt = np.arange(n) / SR
riser = np.diff(rng.standard_normal(n), prepend=0) * (tt / tt[-1]) ** 2 * 0.12
put(riser.astype(np.float32), V['L3'] - 2 * B)
groove(V['L3'], DUR + 0.5, full=True)
for j in range(16):                                  # дождь колокольчиков на раздаче
    put(bell(hz(84 + (j * 5) % 12), 0.8, 0.05), T['rain'] + j * 0.09)
for m in (72, 76, 79, 84):                           # фанфара топ-комментатора
    put(bell(hz(m), 1.4, 0.07), T['top'] + (m - 72) * 0.03)

fade = int(0.8 * SR); e = int(DUR * SR)
mix[e - fade:e] *= np.linspace(1, 0, fade); mix[e:] = 0
mix = np.tanh(mix * 1.4) / 1.4
st = np.stack([mix, np.roll(mix, 300) * 0.95], 1).astype(np.float32)
out = HERE / 'build' / 'music.wav'; out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=st.tobytes(), check=True)
print('OK', out)
