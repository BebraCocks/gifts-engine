"""Звук серии 1: голос по таймлайну + музыка (music.py) с приглушением + звуки кодом (synth.py) + SFX через sfxkit.

    python -B music.py && python -B audio.py
Результат: build/mix.wav и build/review/{voice_only,music_only,sfx_only,mix}.mp3, sfx_cues.txt.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import sfxkit  # noqa: E402
import synth  # noqa: E402
from timeline import T, V, D, DUR, CUTS  # noqa: E402

SR = 48000
N = int(DUR * SR)
REV = HERE / 'build' / 'review'


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def place(buf, a, t, gain=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    a = a[:len(buf) - i]
    buf[i:i + len(a)] += a * gain


def write(path, a):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(path)],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)


def span(arr, t0, t1, val):
    arr[max(0, int(t0 * SR)):min(N, int(t1 * SR))] = np.minimum(arr[max(0, int(t0 * SR)):min(N, int(t1 * SR))], val)


voice = np.zeros((N, 2), np.float32)
for k, t in V.items():
    place(voice, load(HERE / 'voice' / f'{k}.wav'), t)

# --- звуки кодом
code = np.zeros((N, 2), np.float32)
place(code, synth.ufo(1.3), T['ufo_in'], 0.9)
place(code, synth.beam(1.2), T['beam'], 0.8)
for i, t in enumerate(T['alarm_set'] if 'alarm_set' in T else T['alarms_set']):
    place(code, synth.tick(1600 + 150 * i), t, 0.7)
RING_LEN = [0.75, 0.6, 0.5, 0.8, 0.6]          # пока Димон не выключит
for n, (t, d) in enumerate(zip(T['ring'], RING_LEN)):
    place(code, synth.alarm(n, d), t, 0.55 + 0.1 * n)
place(code, synth.snore(1.6), T['snore1'], 0.9)
for i in range(6):                               # шесть будильников снова
    place(code, synth.tick(1600 + 120 * i), T['alarm6'] - 0.5 + i * 0.3, 0.6)
place(code, synth.snore(1.4), T['snore2'], 0.8)

# --- музыка с приглушением
duck = np.ones(N, np.float32)
for k, t in V.items():
    span(duck, t - 0.12, t + D[k] + 0.2, 0.32)
for t, d in zip(T['ring'], RING_LEN):
    span(duck, t - 0.05, t + d + 0.1, 0.12)
span(duck, T['wake'], T['s6'] - 0.1, 0.0)        # обрыв на «ПОЧЕМУ…»
k = int(0.1 * SR)
duck = np.convolve(duck, np.ones(k) / k, 'same')
music = load(HERE / 'build' / 'music.wav')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0))) * duck[:, None] * 0.5

# --- SFX пака Botanica
fx = np.zeros((N, 2), np.float32)
kit = sfxkit.Kit(HERE)
kit.add(fx, 'sparkle', T['land'], gain_db=-14)                     # Мисед касается земли
kit.add(fx, 'whoosh-short', T['logo'], align='peak', gain_db=-13)  # логотип
kit.add(fx, 'sparkle-whoosh', T['intro_end'] - 0.15, gain_db=-13)  # вспышка луча — переход в серию
kit.add(fx, 'select-soft', T['eyes'], gain_db=-16)                 # блик глаз в темноте
kit.add(fx, 'cartoon-hit', T['jump'], gain_db=-12)                 # Димон подпрыгивает
kit.add(fx, 'boing', T['jump'] + 0.05, gain_db=-16)
kit.add(fx, 'click', T['blink'], gain_db=-15)                      # моргание вместо ответа
for t in T['roles']:                                               # плашки системы
    kit.add(fx, 'pop', t, gain_db=-15)
kit.add(fx, 'whoosh-deep', T['pause'] + 0.05, gain_db=-16)         # наезд на Миседа
kit.add(fx, 'cartoon-move', T['pillow'], gain_db=-12)              # подушка
kit.add(fx, 'cartoon-hit', T['pillow'] + 0.3, gain_db=-13)
kit.add(fx, 'click', T['off'], gain_db=-12)                        # выключил пятый
kit.add(fx, 'spinback', T['clock'], gain_db=-12)                   # часы прокручиваются
kit.add(fx, 'impact', T['wake'], align='peak', gain_db=-9)         # 9:40!
for i in range(5):                                                 # беготня
    kit.add(fx, 'cartoon-move', T['s6'] + 0.3 + i * 1.6, gain_db=-17)
kit.add(fx, 'downlifter', T['ears'], gain_db=-15)                  # уши опускаются
kit.add(fx, 'whoosh', T['gift'] - 0.25, align='peak', gain_db=-12) # подарок влетает
kit.add(fx, 'coin', T['gift'] + 0.05, gain_db=-11)
kit.add(fx, 'confirm', T['gift'] + 0.15, gain_db=-13)
kit.add(fx, 'sparkle', T['title'], gain_db=-14)
for t in CUTS:
    if t not in (T['s1'], T['s5']):
        kit.add(fx, 'whoosh-short', t, align='peak', gain_db=-17)
kit.save()

sfx = fx + code
mix = voice + music + sfx
peak = float(np.abs(mix).max())
if peak > 0.98:
    mix *= 0.98 / peak
write(HERE / 'build' / 'mix.wav', mix)
for name, a in (('voice_only.mp3', voice), ('music_only.mp3', music), ('sfx_only.mp3', sfx), ('mix.mp3', mix)):
    write(REV / name, a)
(REV / 'sfx_cues.txt').write_text('\n'.join(str(c) for c in kit.cues), encoding='utf-8')
print('OK', round(DUR, 2), 's, peak', round(peak, 2))
