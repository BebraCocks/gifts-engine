"""Музыка серии кодом (без сэмплов). Фирменный джингл заставки (терменвокс + арпеджио) одинаков во всех сериях.
Ночь — тихая шкатулка; утро — лёгкие щипки, на звонках затихает; обрыв на «ПОЧЕМУ…»; беготня — быстрая погоня
пиццикато; снова ночь; подарок — тёплый аккорд и джингл.

    python -B music.py      # build/music.wav
"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import T, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
N = int(DUR * SR)
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}


def hz(name):
    n, o = name[:-1], int(name[-1])
    return 440 * 2 ** ((NOTE[n] + 12 * (o - 4) - 9) / 12)


def tone(f, dur, kind, amp):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == 'box':                                 # шкатулка
        mod = np.sin(2 * math.pi * f * 4 * t) * 1.5 * np.exp(-t * 8)
        y = np.sin(2 * math.pi * f * t + mod) * np.exp(-t * 3.5)
    elif kind == 'pizz':                              # пиццикато
        y = (np.sin(2 * math.pi * f * t) + 0.35 * np.sin(4 * math.pi * f * t) + 0.15 * np.sin(6 * math.pi * f * t))
        y *= np.exp(-t * 9) * np.minimum(1, t / 0.004)
    elif kind == 'bass':
        y = np.sin(2 * math.pi * f * t) * np.exp(-t * 4) * np.minimum(1, t / 0.01)
    elif kind == 'pad':
        y = sum(np.sin(2 * math.pi * f * (1 + d) * t) for d in (-0.003, 0, 0.004)) / 3
        y *= np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.5)
    elif kind == 'theremin':                          # терменвокс: синус с вибрато
        vib = 1 + 0.012 * np.sin(2 * math.pi * 6 * t) * np.minimum(1, t / 0.15)
        y = np.sin(2 * math.pi * np.cumsum(f * vib) / SR) * np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.08)
    return y * amp


def put(buf, t0, y, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0:
        return
    y = y[:N - i]
    buf[i:i + len(y), 0] += y * math.sqrt((1 - pan) / 2)
    buf[i:i + len(y), 1] += y * math.sqrt((1 + pan) / 2)


def kick(amp=0.5):
    t = np.arange(int(0.25 * SR)) / SR
    return np.sin(2 * math.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 14) * amp


def hat(amp=0.06):
    rng = np.random.default_rng(1)
    t = np.arange(int(0.05 * SR)) / SR
    return np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t * 80) * amp


m = np.zeros((N, 2))

# Заставка: джингл (одинаковый во всех сериях)
for t0, n, d in [(0.15, 'E5', 0.35), (0.5, 'A5', 0.35), (0.85, 'G#5', 0.25), (1.1, 'E6', 0.9), (2.1, 'D6', 0.3), (2.4, 'E6', 0.9)]:
    put(m, t0, tone(hz(n), d, 'theremin', 0.16))
for i in range(14):
    put(m, 1.15 + i * 0.09, tone(hz(['A5', 'C#6', 'E6', 'A6'][i % 4]), 0.4, 'box', 0.07), pan=0.5 * (-1) ** i)
put(m, 0.0, tone(hz('A2'), 3.5, 'pad', 0.12))
put(m, 0.0, tone(hz('E3'), 3.5, 'pad', 0.08))


def music_box(t0, t1, prog, amp=0.08, step=0.5):
    """Тихая шкатулка: арпеджио по аккордам, 120 BPM восьмыми."""
    t, i = t0, 0
    while t < t1:
        ch = prog[int((t - t0) // (step * 8)) % len(prog)]
        put(m, t, tone(hz(ch[i % len(ch)]), 0.9, 'box', amp), pan=0.3 * math.sin(i))
        if i % 8 == 0:
            put(m, t, tone(hz(ch[0][:-1] + '2'), step * 8, 'pad', 0.07))
        t += step / 2
        i += 1


NIGHT = [['A4', 'C5', 'E5', 'C5'], ['F4', 'A4', 'C5', 'A4'], ['C4', 'E4', 'G4', 'E4'], ['G4', 'B4', 'D5', 'B4']]
music_box(T['s1'], T['s4'] - 0.1, NIGHT)

# Утро: бодрые щипки, на каждом звонке затихают (в audio.py — дополнительное приглушение)
MORN = [['C4', 'E4', 'G4', 'C5'], ['A3', 'C4', 'E4', 'A4'], ['F3', 'A3', 'C4', 'F4'], ['G3', 'B3', 'D4', 'G4']]
t, i, beat = T['s4'], 0, 60 / 104
while t < T['off']:
    ch = MORN[int((t - T['s4']) // (beat * 4)) % 4]
    put(m, t, tone(hz(ch[[0, 2, 1, 3][i % 4]]), 0.4, 'pizz', 0.09), pan=-0.2)
    if i % 2 == 0:
        put(m, t, tone(hz(ch[0][:-1] + '2'), beat, 'bass', 0.13))
    t += beat / 2
    i += 1
# храп-пауза: один «сонный» нисходящий звук
for k, n in enumerate(['E5', 'D5', 'C5', 'A4']):
    put(m, T['off'] + 0.05 + k * 0.12, tone(hz(n), 0.3, 'box', 0.06))
# обрыв на 9:40 (тишина до конца «ПОЧЕМУ…»)

# Беготня: быстрая погоня (Am, 150 BPM)
beat = 60 / 150
CHASE = ['A3', 'C4', 'E4', 'A4', 'G#4', 'E4', 'C4', 'B3']
t, i = T['s6'] - 0.05, 0
while t < T['s7'] - 0.15:
    put(m, t, tone(hz(CHASE[i % 8]), 0.25, 'pizz', 0.08), pan=0.25 * (-1) ** i)
    if i % 2 == 0:
        put(m, t, tone(hz(['A2', 'A2', 'F2', 'E2'][(i // 8) % 4]), beat, 'bass', 0.14))
        put(m, t, kick(0.25 if i % 4 == 0 else 0.0))
    put(m, t + beat / 4, hat())
    t += beat / 2
    i += 1

# Снова ночь
music_box(T['s7'], T['s8'], NIGHT[:2], amp=0.07)

# Подарок: тёплый аккорд и джингл
for n in ('C3', 'G3', 'E4', 'C5'):
    put(m, T['s8'], tone(hz(n), DUR - T['s8'], 'pad', 0.07))
for t0, n, d in [(T['title'] - 0.6, 'E5', 0.3), (T['title'] - 0.3, 'A5', 0.3), (T['title'], 'E6', 0.6)]:
    put(m, t0, tone(hz(n), d, 'theremin', 0.12))
for i in range(10):
    put(m, T['gift'] + i * 0.08, tone(hz(['C6', 'E6', 'G6', 'C7'][i % 4]), 0.5, 'box', 0.05), pan=0.4 * (-1) ** i)

fade = int(0.5 * SR)
m[-fade:] *= np.linspace(1, 0, fade)[:, None]
m /= max(1e-6, np.abs(m).max()) / 0.8
out = HERE / 'build' / 'music.wav'
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=m.astype(np.float32).tobytes(), check=True)
print('music', round(DUR, 2))
