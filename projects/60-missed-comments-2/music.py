"""Музыка кодом для второго канала: аркадный синтвейв 140 BPM — арпеджио, «качающийся» бас, бочка с хлопком,
ступенька громкости на каждой награде, «касса» на продаже, финальный подъём. build/music.wav"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import V, T, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
B = 60 / 140
rng = np.random.default_rng(60)
N = int((DUR + 1) * SR)
mix = np.zeros(N, np.float32)


def put(y, t, g=1.0):
    i = int(t * SR)
    if 0 <= i < N:
        j = min(N, i + len(y)); mix[i:j] += y[:j - i] * g


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def sq(f, dur, a=0.04, dec=6.0):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sign(np.sin(2 * math.pi * f * t)) * 0.6 + np.sin(2 * math.pi * f * 2 * t) * 0.2
    return (y * np.exp(-t * dec) * np.minimum(1, t / 0.003) * a).astype(np.float32)


def kick(a=0.6):
    n = int(0.3 * SR); t = np.arange(n) / SR
    f = 45 + 120 * np.exp(-t * 35)
    return (np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * a).astype(np.float32)


def snare(a=0.2):
    n = int(0.22 * SR); t = np.arange(n) / SR
    y = rng.standard_normal(n) * np.exp(-t * 18) + 0.5 * np.sin(2 * math.pi * 190 * t) * np.exp(-t * 25)
    return (y * a).astype(np.float32)


def hat(a=0.04):
    n = int(0.04 * SR)
    return (np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / SR * 90) * a).astype(np.float32)


def pad(fs, dur, a=0.035):
    n = int(dur * SR); t = np.arange(n) / SR
    y = sum(((t * f * (1 + d)) % 1 * 2 - 1) for f in fs for d in (-0.005, 0.005)) / (2 * len(fs))
    y = np.convolve(y, np.ones(30) / 30, 'same')
    return (y * np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.2) * a).astype(np.float32)


PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
ARP = [0, 1, 2, 1, 2, 0, 1, 2]


def section(t0, t1, level):
    bar, k, t = 4 * B, 0, t0
    while t < t1 - 0.02:
        ch = PROG[k % 4]
        put(pad([hz(m) for m in ch], min(bar, t1 - t) + 0.1), t, 0.6 + 0.2 * level)
        for s in range(16):
            ts = t + s * B / 4
            if ts >= t1:
                break
            if level >= 1:
                put(sq(hz(ch[ARP[s % 8]] + 12), B / 4, 0.03 + 0.01 * level), ts)
            if s % 4 == 0:
                put(kick(), ts)
                put(sq(hz(ch[0] - 24), B * 0.8, 0.09, 4), ts)       # бас
            if s % 8 == 4 and level >= 1:
                put(snare(), ts)
            if s % 2 == 1 and level >= 2:
                put(hat(), ts)
        t += bar; k += 1


put(kick(0.9), T['stop']); put(snare(0.35), T['stop'])
section(T['give'], V['L3'], 0)
section(V['L3'], V['L4'], 1)
for x in T['tier']:
    put(snare(0.3), x); put(kick(0.7), x)
section(V['L4'], V['L5'], 2)
for j, m in enumerate((84, 88, 91)):                    # «касса»
    put(sq(hz(m), 0.25, 0.05, 10), T['sell'] + j * 0.06)
section(V['L5'], DUR + 0.5, 2)
fade = int(0.8 * SR); e = int(DUR * SR)
mix[e - fade:e] *= np.linspace(1, 0, fade); mix[e:] = 0
mix = np.tanh(mix * 1.5) / 1.5
st = np.stack([mix, np.roll(mix, 260) * 0.95], 1).astype(np.float32)
out = HERE / 'build' / 'music.wav'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=st.tobytes(), check=True)
print('OK', out)
