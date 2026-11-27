"""Звук «Ещё одно видео»: голос + музыка (music.py) с приглушением + звуки кодом (synth66, synth67) + SFX Botanica.

    python -B music.py && python -B audio.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
sys.path.append(str(HERE.parent / '66-missed-fridge'))
import sfxkit  # noqa: E402
import synth66 as S  # noqa: E402
import synth67 as S7  # noqa: E402
import events as E  # noqa: E402
from timeline import T, V, D, DUR  # noqa: E402

SR = 48000
N = int(DUR * SR)
REV = HERE / 'build' / 'review'
cues = []


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def place(buf, a, t, gain=1.0, name=None):
    i = int(t * SR)
    if i >= len(buf) or i < 0:
        return
    a = a[:len(buf) - i]
    buf[i:i + len(a)] += a * gain
    if name:
        cues.append((t, name))


def write(path, a):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(path)],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)


def span(arr, t0, t1, val):
    i0, i1 = max(0, int(t0 * SR)), min(N, int(t1 * SR))
    arr[i0:i1] = np.minimum(arr[i0:i1], val)


voice = np.zeros((N, 2), np.float32)
for k, t in V.items():
    place(voice, load(HERE / 'voice' / f'{k}.wav'), t)

code = np.zeros((N, 2), np.float32)
place(code, S.ufo(1.3), T['ufo_in'], 0.9, 'НЛО прилетает')
place(code, S.beam(1.2), T['beam'], 0.8, 'луч')
place(code, S.beam(1.6, up=True), T['s6'] + 0.05, 0.8, 'луч забирает Миседа')
place(code, S.scan_beep(), T['card'], 0.8, 'сканер: на очереди')
place(code, S.scan_sweep(1.2), T['card'] + 0.3, 0.7)
place(code, S.ufo(0.9, rise=True), T['ufo_out'] - 0.1, 0.9, 'НЛО улетает')
place(code, S.scan_beep(), E.SCAN, 0.8, 'сканер на Артёме')
place(code, S.scan_sweep(1.0), E.SCAN + 0.1, 0.6)
for i, t in enumerate(E.SWIPES):
    place(code, S7.swipe(), t, 1.0, 'свайп' if i in (0, 2) else None)
place(code, S7.ticks(E.SPIN[1] - E.SPIN[0]), E.SPIN[0], 0.9, 'часы: тайм-лапс')
place(code, S.scribble(E.NOTE[1] - E.NOTE[0]), E.NOTE[0], 0.9, 'ручка по блокноту')
place(code, S7.bonk(), E.DROP, 1.0, 'телефон по лицу')
place(code, S.crickets(1.0), V['A6'] - 0.6, 0.7, 'сверчки')

duck = np.ones(N, np.float32)
for k, t in V.items():
    span(duck, t - 0.12, t + D[k] + 0.2, 0.33)
span(duck, E.DROP, V['M5'] - 0.05, 0.0)                 # бум — тишина
span(duck, V['A6'] - 0.6, T['s5'] - 0.05, 0.0)          # «Кот… огурца» — «…Важно.» без музыки
k = int(0.08 * SR)
duck = np.convolve(duck, np.ones(k) / k, 'same')
music = load(HERE / 'build' / 'music.wav')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0))) * duck[:, None] * 0.5

fx = np.zeros((N, 2), np.float32)
kit = sfxkit.Kit(HERE)
kit.add(fx, 'sparkle', T['land'], gain_db=-14)
kit.add(fx, 'whoosh-short', T['logo'], align='peak', gain_db=-13)
kit.add(fx, 'sparkle-whoosh', T['intro_end'] - 0.15, gain_db=-13)
kit.add(fx, 'pop', E.SCAN + 0.15, gain_db=-12)
kit.add(fx, 'whoosh', E.SPIN[0], gain_db=-13)                       # тайм-лапс
kit.add(fx, 'paper', E.NOTE[0], gain_db=-13)
kit.add(fx, 'confirm', E.NOTE[0] + 2.0, gain_db=-16)
for t0, _ in E.COUNT[1:]:
    kit.add(fx, 'counter', t0 + 0.05, gain_db=-15)
for c in T['cuts']:
    kit.add(fx, 'whoosh-short', c, align='peak', gain_db=-12)
kit.add(fx, 'cartoon-hit', E.DROP + 0.02, gain_db=-11)
kit.add(fx, 'cartoon-move', E.LEAN[0], gain_db=-13)                 # Мисед наклоняется
kit.add(fx, 'whoosh', T['gift'] - 0.25, align='peak', gain_db=-12)
kit.add(fx, 'coin', T['gift'] + 0.05, gain_db=-11)
kit.add(fx, 'confirm', T['gift'] + 0.15, gain_db=-13)
kit.add(fx, 'sparkle', T['gift'] + 0.2, gain_db=-14)
kit.add(fx, 'whoosh-deep', T['s6'] - 0.05, gain_db=-12)
kit.add(fx, 'sparkle', T['s6'] + 1.4, gain_db=-15)
kit.save()

sfx = fx + code * 0.5
mix = voice + music + sfx
over = np.abs(mix) > 0.9
mix[over] = np.sign(mix[over]) * (0.9 + 0.08 * np.tanh((np.abs(mix[over]) - 0.9) / 0.08))
write(HERE / 'build' / 'mix.wav', mix)
for name, a in (('voice_only.mp3', voice), ('music_only.mp3', music), ('sfx_only.mp3', sfx), ('mix.mp3', mix)):
    write(REV / name, a)
lines = [f'{c["at"]:6.2f} с  {c["role"]:<15} {c["id"].split("/")[-1].split("#")[0]}' for c in kit.cues]
lines += [f'{t:6.2f} с  кодом           {n}' for t, n in cues]
(REV / 'sfx_cues.txt').write_text('\n'.join(sorted(lines)) + '\n', encoding='utf-8')
print('OK', round(DUR, 2))
