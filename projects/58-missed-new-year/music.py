"""Музыка «Подарка по заслугам», синтезированная кодом (без сэмплов): новогодняя шкатулка → надежда →
праздник на подарке → весёлый грув → мрачнее → обрыв на «Ты уверен?» → гул → тёплый финал.

    python -B projects/58-missed-new-year/music.py      # build/music.wav
"""
import math
import subprocess
from pathlib import Path

import numpy as np

from timeline import T, DUR

HERE = Path(__file__).resolve().parent
SR = 48000
BPM = 100
BEAT = 60 / BPM
rng = np.random.default_rng(58)


def env(n, a=0.005, d=0.3, s=0.0, r=0.05):
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / d))
    tail = int(r * SR)
    if tail and n > tail:
        e[-tail:] *= np.linspace(1, 0, tail)
    return e


def note(f, dur, kind='bell', amp=0.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    if kind == 'bell':                       # FM-колокольчик / шкатулка
        mod = np.sin(2 * math.pi * f * 3.5 * t) * 2.2 * np.exp(-t * 6)
        y = np.sin(2 * math.pi * f * t + mod) * env(n, 0.002, 0.9)
    elif kind == 'pluck':
        y = (np.sin(2 * math.pi * f * t) + 0.4 * np.sin(4 * math.pi * f * t)) * env(n, 0.003, 0.25)
    elif kind == 'pad':                      # мягкий аккордовый пэд из расстроенных треугольников
        y = sum(2 / math.pi * np.arcsin(np.sin(2 * math.pi * f * (1 + dt) * t)) for dt in (-0.004, 0, 0.005)) / 3
        y *= env(n, 0.35, 10, 1.0, 0.4)
    elif kind == 'bass':
        y = np.sin(2 * math.pi * f * t) * env(n, 0.005, 0.35, 0.3, 0.05)
    return (y * amp).astype(np.float32)


def kick(amp=0.5):
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return (np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * amp).astype(np.float32)


def shaker(amp=0.08):
    n = int(0.08 * SR)
    y = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 60)
    y = np.diff(y, prepend=0)                # высокие частоты, как бубенцы саней
    return (y * amp).astype(np.float32)


def cymbal(amp=0.25, dur=2.5):
    n = int(dur * SR)
    y = np.diff(rng.standard_normal(n), prepend=0) * np.exp(-np.arange(n) / SR * 2.2)
    return (y * amp).astype(np.float32)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


N = int((DUR + 1) * SR)
mus = np.zeros(N, np.float32)


def put(y, t, gain=1.0):
    i = int(t * SR)
    if i >= N:
        return
    j = min(N, i + len(y))
    mus[i:j] += y[:j - i] * gain


# аккорды (MIDI): грустный ля-минор и надежда в до-мажоре
SAD = [[57, 60, 64], [53, 57, 60], [55, 59, 62], [52, 55, 59]]          # Am F G Em
HOPE = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]         # C G Am F
DARK = [[57, 60, 63], [56, 60, 63], [55, 58, 62], [56, 59, 63]]         # тревожнее
MEL_SAD = [76, 74, 72, 71, 72, 69, 71, 72]
MEL_HOPE = [72, 76, 79, 76, 74, 77, 76, 72]


def section(t0, t1, chords, mel=None, drums=0, bass=True, bells=True, gain=1.0):
    bar = 4 * BEAT
    t, k = t0, 0
    while t < t1 - 0.05:
        ch = chords[k % len(chords)]
        dur = min(bar, t1 - t)
        for m in ch:
            put(note(hz(m), dur + 0.3, 'pad', 0.05), t, gain)
        if bass:
            for b in range(4):
                if t + b * BEAT < t1:
                    put(note(hz(ch[0] - 12), BEAT * 0.9, 'bass', 0.16), t + b * BEAT, gain)
        if mel and bells:
            for b in range(8):
                tb = t + b * BEAT / 2
                if tb < t1 and (b % 2 == 0 or drums):
                    put(note(hz(mel[(k * 8 + b) % len(mel)]), 1.2, 'bell', 0.07), tb, gain)
        if drums:
            for b in range(4):
                tb = t + b * BEAT
                if tb >= t1:
                    break
                if b in (0, 2) or drums > 1:
                    put(kick(0.35 if drums == 1 else 0.45), tb, gain)
                for h in (0, 0.5):
                    put(shaker(0.05 if drums == 1 else 0.08), tb + h * BEAT, gain)
        t += bar; k += 1


# 1–2: шкатулка, грустно
section(0, T['s3'], SAD, MEL_SAD, drums=0, bass=False)
# 3–4: надежда, лёгкий пульс
section(T['s3'], T['s5'], HOPE, MEL_HOPE, drums=1)
# 5: подарок — тарелка, удар, полный праздник
put(cymbal(0.22), T['s5']); put(kick(0.7), T['s5'])
for m in (72, 76, 79, 84):
    put(note(hz(m), 2.0, 'bell', 0.09), T['s5'] + (m - 72) * 0.03)
section(T['s5'], T['s6'], HOPE, MEL_HOPE, drums=2)
# 6: звонок — весёлый грув
section(T['s6'], T['s7'], HOPE, MEL_HOPE, drums=1)
# 7: чат Олега — мрачнее до «Ты уверен?»
section(T['s7'], T['omm2'], DARK, None, drums=1, gain=0.8)
# обрыв, затем гул и «сердцебиение» до исчезновения подарков
drone_t0 = T['omm2'] + 0.25
n = int((T['s9'] - drone_t0) * SR); tt = np.arange(n) / SR
drone = (np.sin(2 * math.pi * 55 * tt) + 0.5 * np.sin(2 * math.pi * 82.4 * tt)) * 0.07 * np.minimum(1, tt / 1.5)
put(drone.astype(np.float32), drone_t0)
hb = drone_t0 + 0.6
while hb < T['s8'] + 3.5:
    put(kick(0.3), hb); put(kick(0.22), hb + 0.28); hb += 1.1
# 9: тёплый финал
section(T['s9'], DUR + 0.5, HOPE, MEL_HOPE, drums=0, gain=0.9)
put(note(hz(84), 3.0, 'bell', 0.08), T['s9'])

# мягкий лимит и затухание в конце
fade = int(1.2 * SR)
mus[int(DUR * SR) - fade:int(DUR * SR)] *= np.linspace(1, 0, fade)
mus[int(DUR * SR):] = 0
mus = np.tanh(mus * 1.6) / 1.6
st = np.stack([mus, np.roll(mus, 240) * 0.96], 1)          # немного ширины
out = HERE / 'build' / 'music.wav'
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(out)],
               input=st.astype(np.float32).tobytes(), check=True)
print('OK', out, round(len(mus) / SR, 1), 's')
