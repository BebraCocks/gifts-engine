"""Чиптюн кодом (четвёртый ролик): 150 BPM, квадратные волны, треугольный бас, шумовые барабаны,
джинглы «level up» на наградах и «монетка» на продаже. build/music.wav"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import V, T, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
B = 60 / 150
rng = np.random.default_rng(62)
N = int((DUR + 1) * SR)
mix = np.zeros(N, np.float32)


def put(y, t, g=1.0):
    i = int(t * SR)
    if 0 <= i < N:
        j = min(N, i + len(y)); mix[i:j] += y[:j - i] * g


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def pulse(f, dur, a=0.05, duty=0.25):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.where((t * f) % 1 < duty, 1.0, -1.0)
    return (y * np.minimum(1, (dur - t) / 0.01) * a).astype(np.float32)


def tri(f, dur, a=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    y = 2 * np.abs(2 * ((t * f) % 1) - 1) - 1
    return (y * np.minimum(1, (dur - t) / 0.01) * a).astype(np.float32)


def noise(dur, a=0.08, dec=30):
    n = int(dur * SR)
    y = np.sign(rng.standard_normal(n)) * np.exp(-np.arange(n) / SR * dec)
    return (y * a).astype(np.float32)


PROG = [45, 41, 43, 40]                      # A F G E (корни)
LEAD = [69, 72, 76, 72, 74, 72, 69, 67, 69, 72, 76, 79, 77, 76, 74, 72]


def song(t0, t1, lead=True):
    t, k = t0, 0
    while t < t1 - 0.02:
        r = PROG[k % 4]
        for s in range(8):
            ts = t + s * B / 2
            if ts >= t1:
                break
            put(tri(hz(r - 12 + (12 if s % 2 else 0)), B / 2 * 0.9), ts)
            if s % 4 == 0:
                put(noise(0.12, 0.1, 25), ts)
            if s % 4 == 2:
                put(noise(0.08, 0.06, 60), ts)
            if lead:
                put(pulse(hz(LEAD[(k * 8 + s) % 16]), B / 2 * 0.8, 0.045, 0.125 if k % 2 else 0.25), ts)
            for j, iv in enumerate((0, 4, 7)):                     # быстрое арпеджио
                put(pulse(hz(r + 24 + iv), B / 6 * 0.9, 0.02, 0.5), ts + j * B / 6)
        t += 4 * B; k += 1


def jingle(t0, notes, step=0.07, a=0.06):
    for j, m in enumerate(notes):
        put(pulse(hz(m), step * 1.6, a, 0.5), t0 + j * step)


jingle(V['L1'], [72, 76, 79, 84], 0.06)
song(V['L1'] + 0.3, V['L3'], lead=False)
song(V['L3'], DUR + 0.5, lead=True)
for x in T['tier']:
    jingle(x, [72, 76, 79, 84, 88], 0.05, 0.07)                 # level up
for j in range(6):
    jingle(T['sell'] + 0.2 + j * 0.12, [88, 95], 0.04, 0.04)     # монетки
jingle(T['zero'], [60, 55, 48], 0.1, 0.06)
jingle(T['top'], [79, 84, 88, 91, 96], 0.06, 0.07)
fade = int(0.8 * SR); e = int(DUR * SR)
mix[e - fade:e] *= np.linspace(1, 0, fade); mix[e:] = 0
mix = np.tanh(mix * 1.4) / 1.4
st = np.stack([mix, np.roll(mix, 200) * 0.95], 1).astype(np.float32)
out = HERE / 'build' / 'music.wav'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=st.tobytes(), check=True)
print('OK', out)
