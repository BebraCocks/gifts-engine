"""Звук «Холодильника»: голос + музыка (music.py) с приглушением + звуки кодом (synth66.py) + SFX Botanica (sfxkit).

    python -B music.py && python -B audio.py
Результат: build/mix.wav, build/review/{voice_only,music_only,sfx_only,mix}.mp3, sfx_cues.txt.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import sfxkit  # noqa: E402
import synth66 as S  # noqa: E402
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
# заставка и концовка
place(code, S.ufo(1.3), T['ufo_in'], 0.9, 'НЛО прилетает')
place(code, S.beam(1.2), T['beam'], 0.8, 'луч')
place(code, S.beam(1.6, up=True), T['s6'] + 0.05, 0.8, 'луч забирает Миседа')
place(code, S.scan_beep(), T['card'], 0.8, 'сканер: следующий объект')
place(code, S.scan_sweep(1.2), T['card'] + 0.3, 0.7)
place(code, S.ufo(0.9, rise=True), T['ufo_out'] - 0.1, 0.9, 'НЛО улетает')
# холодильник
for a, b in E.DOOR:
    place(code, S.fridge_open(), a, 0.9, 'дверца: открыть')
    place(code, S.fridge_hum(b - a + 0.2), a + 0.05, 0.9)
    place(code, S.fridge_close(), b, 0.8, 'дверца: закрыть')
place(code, S.fridge_open(), E.FREEZER[0], 0.9, 'морозилка')
place(code, S.freezer_hiss(1.8), E.FREEZER[0] + 0.05, 0.9, 'пар морозилки')
place(code, S.fridge_close(), E.FREEZER[1], 0.8)
for i, t in enumerate(E.STEPS):
    place(code, S.step(1 + 0.08 * (i % 2)), t, 0.8, 'шаг' if i in (0, 3) else None)
place(code, S.scan_beep(), E.SCAN, 0.8, 'сканер на Стасе')
place(code, S.scan_sweep(1.0), E.SCAN + 0.1, 0.6)
place(code, S.scribble(E.NOTE[1] - E.NOTE[0]), E.NOTE[0], 0.9, 'ручка по блокноту')
place(code, S.crickets(1.4), E.CRICKETS, 0.9, 'сверчки')
place(code, S.tap(), E.TAP, 1.0, 'тап по телефону')
place(code, S.tap(), E.TAP + 0.18, 0.8)
place(code, S.scratch(), E.STOP, 0.8, 'скрэтч')
tb = S.sad_trombone()
tb = tb[:int((T['s6'] + 0.4 - E.TROMBONE) * SR)]
tb[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]
place(code, tb, E.TROMBONE, 0.9, 'грустный тромбон')

# музыка с приглушением
duck = np.ones(N, np.float32)
for k, t in V.items():
    span(duck, t - 0.12, t + D[k] + 0.2, 0.33)
span(duck, E.CRICKETS - 0.1, V['S4'] + D['S4'] + 0.1, 0.0)      # тишина под сверчков
span(duck, E.STOP, T['s5'] - 0.05, 0.0)                         # стоп после скрэтча
span(duck, E.TROMBONE - 0.05, T['s6'] - 0.05, 0.0)              # тромбон без музыки
k = int(0.08 * SR)
duck = np.convolve(duck, np.ones(k) / k, 'same')
music = load(HERE / 'build' / 'music.wav')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0))) * duck[:, None] * 0.5

fx = np.zeros((N, 2), np.float32)
kit = sfxkit.Kit(HERE)
kit.add(fx, 'sparkle', T['land'], gain_db=-14)
kit.add(fx, 'whoosh-short', T['logo'], align='peak', gain_db=-13)
kit.add(fx, 'sparkle-whoosh', T['intro_end'] - 0.15, gain_db=-13)
kit.add(fx, 'pop', E.SCAN + 0.15, gain_db=-12)                       # плашка объекта
kit.add(fx, 'sparkle', V['M2'], gain_db=-12)                         # «Холодильник полный»
kit.add(fx, 'whoosh-short', V['M2'] - 0.05, align='peak', gain_db=-15)
kit.add(fx, 'paper', E.NOTE[0], gain_db=-13)                         # страница блокнота
kit.add(fx, 'confirm', E.NOTE[0] + 2.0, gain_db=-16)                 # подчёркнуто
kit.add(fx, 'cartoon-move', E.AWAY[0], gain_db=-13)                  # уходит
kit.add(fx, 'cartoon-move', E.BACK[0], gain_db=-13)                  # возвращается
for t0, _ in E.COUNT:
    kit.add(fx, 'counter', t0 + 0.05, gain_db=-15)
for t0 in T['opens']:
    kit.add(fx, 'whoosh-short', t0, align='peak', gain_db=-12)       # склейки монтажа
kit.add(fx, 'sparkle-whoosh', V['S5'] - 0.1, gain_db=-11)            # пельмени!
kit.add(fx, 'select', E.TAP + 0.4, gain_db=-14)                      # приложение доставки
kit.add(fx, 'pop', E.CMP + 0.02, gain_db=-12)
kit.add(fx, 'pop', E.CMP + 0.27, gain_db=-12)
kit.add(fx, 'impact', E.STAMP, align='peak', gain_db=-9)             # штамп
kit.add(fx, 'whoosh', T['gift'] - 0.25, align='peak', gain_db=-12)
kit.add(fx, 'coin', T['gift'] + 0.05, gain_db=-11)
kit.add(fx, 'confirm', T['gift'] + 0.15, gain_db=-13)
kit.add(fx, 'sparkle', T['gift'] + 0.2, gain_db=-14)
kit.add(fx, 'whoosh-deep', T['s6'] - 0.05, gain_db=-12)              # переход на улицу
kit.add(fx, 'sparkle', T['s6'] + 1.4, gain_db=-15)
kit.save()

sfx = fx + code * 0.5                     # звуки кодом громче пака — общий уровень ниже
mix = voice + music + sfx
peak = float(np.abs(mix).max())
over = np.abs(mix) > 0.9                  # мягкий лимитер только на пиках
mix[over] = np.sign(mix[over]) * (0.9 + 0.08 * np.tanh((np.abs(mix[over]) - 0.9) / 0.08))
write(HERE / 'build' / 'mix.wav', mix)
for name, a in (('voice_only.mp3', voice), ('music_only.mp3', music), ('sfx_only.mp3', sfx), ('mix.mp3', mix)):
    write(REV / name, a)
lines = [f'{c["at"]:6.2f} с  {c["role"]:<15} {c["id"].split("/")[-1].split("#")[0]}' for c in kit.cues]
lines += [f'{t:6.2f} с  кодом           {n}' for t, n in cues]
(REV / 'sfx_cues.txt').write_text('\n'.join(sorted(lines)) + '\n', encoding='utf-8')
print('OK', round(DUR, 2), 's, peak', round(peak, 2))
