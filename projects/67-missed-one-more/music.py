"""Музыка «Ещё одно видео» кодом. Заставка — джингл сериала. Спальня — сонный лоу-фай-«колыбельная»:
мягкая бочка, щётки, электропиано Fmaj7–Em7–Dm7–Cmaj7, арпеджио-шкатулка. Прокрутка часов — ускорение (тайм-лапс).
Монтаж — сбивки. Телефон на лицо — стоп. «…Важно.» — пауза. Подарок — колокольчики. Концовка — джингл зеркально, в ноль.

    python -B music.py      # build/music.wav
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / '66-missed-fridge'))
from timeline import T, V, D, DUR  # noqa: E402

SR = 48000
N = int(DUR * SR)
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
rng = np.random.default_rng(67)


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440 * 2 ** ((NOTE[n] + 12 * (o - 4) - 9) / 12)


def tone(f, dur, kind, amp):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == 'epiano':
        mod = np.sin(2 * math.pi * f * t) * 1.1 * np.exp(-t * 3)
        y = np.sin(2 * math.pi * f * t + mod) * np.exp(-t * 1.4) * np.minimum(1, t / 0.006) * np.minimum(1, (dur - t) / 0.08)
    elif kind == 'bass':
        y = np.sin(2 * math.pi * f * t) * np.exp(-t * 2.2) * np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.05)
    elif kind == 'box':
        mod = np.sin(2 * math.pi * f * 4 * t) * 1.5 * np.exp(-t * 8)
        y = np.sin(2 * math.pi * f * t + mod) * np.exp(-t * 3.5)
    elif kind == 'pad':
        y = sum(np.sin(2 * math.pi * f * (1 + d) * t) for d in (-0.003, 0, 0.004)) / 3
        y *= np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.5)
    elif kind == 'theremin':
        vib = 1 + 0.012 * np.sin(2 * math.pi * 6 * t) * np.minimum(1, t / 0.15)
        y = np.sin(2 * math.pi * np.cumsum(f * vib) / SR) * np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.08)
    return y * amp


m = np.zeros((N, 2))


def put(t0, y, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0:
        return
    y = y[:N - i]
    m[i:i + len(y), 0] += y * math.sqrt((1 - pan) / 2)
    m[i:i + len(y), 1] += y * math.sqrt((1 + pan) / 2)


def kick(a=0.4):
    t = np.arange(int(0.3 * SR)) / SR
    return np.sin(2 * math.pi * (46 + 70 * np.exp(-t * 26)) * t) * np.exp(-t * 9) * a


def brush(a=0.05, d=0.18):
    t = np.arange(int(d * SR)) / SR
    n = rng.standard_normal(len(t))
    return (n - np.convolve(n, np.ones(5) / 5, 'same')) * np.sin(np.pi * t / t[-1]) * a


# заставка — джингл сериала
for t0, n, d in [(0.15, 'E5', 0.35), (0.5, 'A5', 0.35), (0.85, 'G#5', 0.25), (1.1, 'E6', 0.9), (2.1, 'D6', 0.3), (2.4, 'E6', 0.9)]:
    put(t0, tone(hz(n), d, 'theremin', 0.16))
for i in range(14):
    put(1.15 + i * 0.09, tone(hz(['A5', 'C#6', 'E6', 'A6'][i % 4]), 0.4, 'box', 0.07), pan=0.5 * (-1) ** i)
put(0.0, tone(hz('A2'), 3.5, 'pad', 0.12))
put(0.0, tone(hz('E3'), 3.5, 'pad', 0.08))

CH = [('F2', ['E4', 'A4', 'C5']), ('E2', ['D4', 'G4', 'B4']), ('D2', ['C4', 'F4', 'A4']), ('C2', ['B3', 'E4', 'G4'])]
ARP = [0, 1, 2, 1]


def lullaby(t0, t1, bpm=76, amp=1.0, drums=True):
    B = 60 / bpm
    t, bar = t0, 0
    while t < t1 - 0.05:
        root, ch = CH[bar % 4]
        for k, n in enumerate(ch):
            put(t + k * 0.02, tone(hz(n), B * 3.8, 'epiano', 0.04 * amp), pan=-0.2 + k * 0.2)
        put(t, tone(hz(root), B * 3.8, 'bass', 0.14 * amp))
        for s in range(8):                                    # шкатулка восьмыми
            ts = t + s * B / 2
            if ts < t1:
                put(ts, tone(hz(ch[ARP[s % 4]][:-1] + str(int(ch[ARP[s % 4]][-1]) + 1)), 0.6, 'box', 0.025 * amp), pan=0.4 * math.sin(s))
        if drums:
            for b in range(4):
                tb = t + b * B
                if tb >= t1:
                    break
                if b in (0, 2):
                    put(tb, kick(0.32 * amp))
                put(tb + B / 2, brush(0.045 * amp), pan=0.3)
                if b in (1, 3):
                    put(tb, brush(0.08 * amp, 0.25))
        t += B * 4
        bar += 1


lullaby(T['s1'], T['spin1'][0], drums=False)
# тайм-лапс: быстрые восходящие арпеджио
for i in range(int((T['spin1'][1] - T['spin1'][0]) / 0.06)):
    put(T['spin1'][0] + i * 0.06, tone(hz(['C5', 'E5', 'G5', 'B5', 'D6'][i % 5]), 0.25, 'box', 0.05), pan=0.5 * (-1) ** i)
lullaby(T['spin1'][1], T['s3'])
lullaby(T['s3'], T['drop'] - 0.02, bpm=96, amp=1.05)
for c in T['cuts'][1:]:
    for k in range(3):
        put(c - 0.12 + k * 0.04, brush(0.12, 0.08))
lullaby(V['M5'], T['lean'] - 0.05, amp=0.9)                    # после «бум» — снова тихо
# подарок
for n in ('F3', 'C4', 'A4'):
    put(T['s5'], tone(hz(n), T['s6'] - T['s5'], 'pad', 0.06))
for i in range(12):
    put(T['gift'] + i * 0.08, tone(hz(['C6', 'E6', 'G6', 'C7'][i % 4]), 0.6, 'box', 0.05), pan=0.4 * (-1) ** i)
lullaby(T['gift'] + 0.4, T['s6'] - 0.05, amp=0.55, drums=False)
# концовка
o = T['s6']
for t0, n, d in [(0.1, 'E6', 0.5), (0.65, 'D6', 0.3), (1.0, 'E6', 0.5), (1.6, 'G#5', 0.3), (1.95, 'A5', 0.35), (2.35, 'E5', 0.9)]:
    put(o + t0, tone(hz(n), d, 'theremin', 0.12))
put(o, tone(hz('A2'), DUR - o, 'pad', 0.1))
put(o, tone(hz('E3'), DUR - o, 'pad', 0.07))
for i in range(16):
    put(T['card'] + i * 0.07, tone(hz(['A6', 'E6', 'C#6', 'A5'][i % 4]), 0.4, 'box', 0.05), pan=0.5 * (-1) ** i)

fade = int(0.7 * SR)
m[-fade:] *= np.linspace(1, 0, fade)[:, None]
m /= max(1e-6, np.abs(m).max()) / 0.8
out = HERE / 'build' / 'music.wav'
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=m.astype(np.float32).tobytes(), check=True)
print('music', round(DUR, 2))
