"""Музыка серии «Холодильник» кодом (без сэмплов).
Заставка — фирменный джингл сериала (как в серии 1). Кухня — ночной лоу-фай: мягкая бочка, клэп, шейкер, электропиано
Dm7–G7–Cmaj7–Am7, бас. Монтаж открытий — плотнее, сбивка на каждой склейке. «Пельмени» — мажорный всплеск.
После «Ты простоял…» — стоп. Подарок — тёплые колокольчики. «Нет.» — тишина (тромбон в audio.py).
Концовка — джингл заставки зеркально (улёт), затихает в ноль → петля на начало ролика.

    python -B music.py      # build/music.wav
"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import T, V, D, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
N = int(DUR * SR)
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
rng = np.random.default_rng(66)


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440 * 2 ** ((NOTE[n] + 12 * (o - 4) - 9) / 12)


def tone(f, dur, kind, amp):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == 'epiano':                       # FM-электропиано
        mod = np.sin(2 * math.pi * f * t) * 1.2 * np.exp(-t * 3)
        y = np.sin(2 * math.pi * f * t + mod) * np.exp(-t * 1.6) + 0.15 * np.sin(4 * math.pi * f * t) * np.exp(-t * 5)
        y *= np.minimum(1, t / 0.006) * np.minimum(1, (dur - t) / 0.08)
    elif kind == 'bass':
        y = (np.sin(2 * math.pi * f * t) + 0.25 * np.sin(4 * math.pi * f * t)) * np.exp(-t * 2.5) * np.minimum(1, t / 0.01)
        y *= np.minimum(1, (dur - t) / 0.05)
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


def kick(a=0.5):
    t = np.arange(int(0.3 * SR)) / SR
    return np.sin(2 * math.pi * (48 + 80 * np.exp(-t * 28)) * t) * np.exp(-t * 9) * a


def clap(a=0.18):
    t = np.arange(int(0.25 * SR)) / SR
    n = rng.standard_normal(len(t))
    n = n - np.convolve(n, np.ones(8) / 8, 'same')
    env = sum(np.exp(-np.maximum(0, t - d) * 60) * (t >= d) for d in (0, 0.012, 0.024)) / 3
    return n * env * a


def shaker(a=0.05):
    t = np.arange(int(0.07 * SR)) / SR
    n = rng.standard_normal(len(t))
    return (n - np.convolve(n, np.ones(4) / 4, 'same')) * np.sin(np.pi * t / t[-1]) * a


def vinyl(d, a=0.012):
    n = rng.standard_normal(int(d * SR))
    crackle = (rng.random(int(d * SR)) > 0.9993) * rng.uniform(-1, 1, int(d * SR)) * 6
    return (np.convolve(n, np.ones(30) / 30, 'same') * 0.6 + crackle) * a


# --- Заставка: джингл сериала
JINGLE = [(0.15, 'E5', 0.35), (0.5, 'A5', 0.35), (0.85, 'G#5', 0.25), (1.1, 'E6', 0.9), (2.1, 'D6', 0.3), (2.4, 'E6', 0.9)]
for t0, n, d in JINGLE:
    put(t0, tone(hz(n), d, 'theremin', 0.16))
for i in range(14):
    put(1.15 + i * 0.09, tone(hz(['A5', 'C#6', 'E6', 'A6'][i % 4]), 0.4, 'box', 0.07), pan=0.5 * (-1) ** i)
put(0.0, tone(hz('A2'), 3.5, 'pad', 0.12))
put(0.0, tone(hz('E3'), 3.5, 'pad', 0.08))

# --- Кухонный лоу-фай
BPM = 88
B = 60 / BPM
CH = [('D3', ['F4', 'A4', 'C5', 'E5']), ('G2', ['F4', 'B4', 'D5']), ('C3', ['E4', 'G4', 'B4', 'D5']), ('A2', ['G4', 'C5', 'E5'])]
STOP = V['M9'] + D['M9'] + 0.05            # стоп после «Ты простоял у холодильника двадцать»


def groove(t0, t1, dense=False, amp=1.0):
    bar = 0
    t = t0
    while t < t1 - 0.05:
        root, ch = CH[bar % 4]
        for k, n in enumerate(ch):                       # аккорд с лёгким «страмом»
            put(t + k * 0.018, tone(hz(n), B * 3.6, 'epiano', 0.045 * amp), pan=-0.2 + k * 0.13)
        put(t + B * 2.5, tone(hz(ch[-1]), B * 1.2, 'epiano', 0.03 * amp), pan=0.3)
        for b, nn in enumerate([root, root, root[:-1] + str(int(root[-1]) + 1), root]):
            if t + b * B < t1:
                put(t + b * B, tone(hz(nn), B * 0.9, 'bass', 0.16 * amp))
        for b in range(4):
            tb = t + b * B
            if tb >= t1:
                break
            if b in (0, 2):
                put(tb, kick(0.42 * amp))
            if b in (1, 3):
                put(tb + 0.01, clap(0.16 * amp))
            for s in range(4 if dense else 2):
                put(tb + s * B / (4 if dense else 2) + 0.01, shaker(0.045 * amp), pan=0.35)
        t += B * 4
        bar += 1


groove(T['s1'], T['s3'])
# монтаж: плотнее + сбивки на склейках
groove(T['s3'], T['s4'] - 0.05, dense=True, amp=1.05)
for t0 in T['opens']:
    for k in range(3):
        put(t0 - 0.12 + k * 0.04, clap(0.08))
# «О! Пельмени!» — мажорный всплеск
for k, n in enumerate(['C5', 'E5', 'G5', 'C6']):
    put(V['S5'] + k * 0.06, tone(hz(n), 1.0, 'box', 0.08))
groove(T['s4'], STOP)
# подарок — тёплые колокольчики + пэд, ритм тихо
for n in ('C3', 'G3', 'E4'):
    put(T['s5'], tone(hz(n), V['M11'] - T['s5'], 'pad', 0.06))
for i in range(12):
    put(T['gift'] + i * 0.08, tone(hz(['C6', 'E6', 'G6', 'C7'][i % 4]), 0.6, 'box', 0.05), pan=0.4 * (-1) ** i)
groove(T['gift'] + 0.4, V['M11'] - 0.05, amp=0.55)
# Концовка: джингл зеркально (улёт) и затухание в ноль — петля на начало
o = T['s6']
for t0, n, d in [(0.1, 'E6', 0.5), (0.65, 'D6', 0.3), (1.0, 'E6', 0.5), (1.6, 'G#5', 0.3), (1.95, 'A5', 0.35), (2.35, 'E5', 0.9)]:
    put(o + t0, tone(hz(n), d, 'theremin', 0.12))
put(o, tone(hz('A2'), DUR - o, 'pad', 0.1))
put(o, tone(hz('E3'), DUR - o, 'pad', 0.07))
for i in range(16):
    put(T['card'] + i * 0.07, tone(hz(['A6', 'E6', 'C#6', 'A5'][i % 4]), 0.4, 'box', 0.05), pan=0.5 * (-1) ** i)

m[:, 0] += vinyl(DUR)[:N]
m[:, 1] += vinyl(DUR)[:N]
fade = int(0.7 * SR)
m[-fade:] *= np.linspace(1, 0, fade)[:, None]
m /= max(1e-6, np.abs(m).max()) / 0.8
out = HERE / 'build' / 'music.wav'
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=m.astype(np.float32).tobytes(), check=True)
print('music', round(DUR, 2))
