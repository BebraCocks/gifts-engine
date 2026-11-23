"""Звук «Подарка по заслугам»: голос по таймлайну + музыка (music.py) с приглушением под речь + SFX через sfxkit.

    python -B projects/58-missed-new-year/audio.py
Результат: build/mix.wav и build/review/{voice_only,sfx_only,mix}.mp3, sfx_cues.txt.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import sfxkit  # noqa: E402
from timeline import T, V, D, DUR  # noqa: E402
import cues  # noqa: E402

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


voice = np.zeros((N, 2), np.float32)
for k, t in V.items():
    place(voice, load(HERE / 'voice' / f'{k}.wav'), t, 1.0)

# приглушение музыки под речь
duck = np.ones(N, np.float32)
for k, t in V.items():
    i0, i1 = int((t - 0.15) * SR), int((t + D[k] + 0.25) * SR)
    duck[max(0, i0):min(N, i1)] = 0.38
k = int(0.12 * SR)
duck = np.convolve(duck, np.ones(k) / k, 'same')
music = load(HERE / 'build' / 'music.wav')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0))) * duck[:, None] * 0.55

fx = np.zeros((N, 2), np.float32)
kit = sfxkit.Kit(HERE)                      # пак Botanica V4 из input/sfx/
# 1. хук: ноль подарков
kit.add(fx, 'counter', 0.35, gain_db=-12)
kit.add(fx, 'error', 1.6, gain_db=-12)
# 2. годы: удар на цифре, письмо улетает, «пусто»
for t in cues.YEARS:
    kit.add(fx, 'impact', t, align='peak', gain_db=-11)
    kit.add(fx, 'paper', t + 0.12, gain_db=-14)
    kit.add(fx, 'whoosh-short', t + 0.35, align='peak', gain_db=-15)
    kit.add(fx, 'select-soft', t + 0.95, gain_db=-15)
# 3. лента
kit.add(fx, 'whoosh-short', cues.SWIPE, align='peak', gain_db=-10)
kit.add(fx, 'pop', cues.SWIPE + 0.3, gain_db=-12)
# 4, 7. чаты: отправка своих, набор текста, входящие от Миседа
for t in cues.SENT:
    kit.add(fx, 'key-enter', t, gain_db=-12)
    kit.add(fx, 'whoosh-short', t + 0.05, align='peak', gain_db=-18)
for t0, t1 in cues.TYPING:
    tt = t0 + 0.05
    while tt < t1 - 0.2:
        kit.add(fx, 'typing', tt, gain_db=-17); tt += 0.45
for t in cues.INCOMING:
    kit.add(fx, 'popup', t, gain_db=-8)
# 5. подарок
kit.add(fx, 'riser', T['s5'], align='end', gain_db=-11)
kit.add(fx, 'impact', T['s5'], align='peak', gain_db=-8)
kit.add(fx, 'sparkle-whoosh', T['s5'] + 0.05, gain_db=-10)
kit.add(fx, 'coin', T['s5'] + 0.55, gain_db=-10)
kit.add(fx, 'confirm', T['s5'] + 0.6, gain_db=-12)
for t in cues.JUMPS:
    kit.add(fx, 'boing', t, gain_db=-14)
# 6. звонок
kit.add(fx, 'click', T['s6'] + 0.05, gain_db=-10)
kit.add(fx, 'select', T['s6'] + 0.15, gain_db=-12)
# 7. обрыв музыки и приговор
kit.add(fx, 'sub-drop', T['omm2'], gain_db=-9)
kit.add(fx, 'glitch', T['omm3'], gain_db=-9)
kit.add(fx, 'error', T['omm3'] + 0.05, gain_db=-12)
# 8. подарки исчезают
for t in cues.VANISH:
    kit.add(fx, 'glitch-text', t, gain_db=-13)
    kit.add(fx, 'counter', t + 0.2, gain_db=-16)
kit.add(fx, 'power-down', cues.VANISH[-1] + 0.3, gain_db=-11)
# 9. финал
kit.add(fx, 'sparkle-whoosh', T['s9'] + 0.2, gain_db=-12)
kit.add(fx, 'sparkle', V['N3'] + 0.1, gain_db=-14)
kit.add(fx, 'sparkle', V['N3'] + 1.9, gain_db=-14)
# переходы между сценами
for t in cues.CUTS:
    if abs(t - T['s5']) > 0.05:
        kit.add(fx, 'whoosh-short', t, align='peak', gain_db=-15)
kit.save()

mix = voice + music + fx
peak = np.abs(mix).max()
if peak > 0.98:
    mix *= 0.98 / peak
write(HERE / 'build' / 'mix.wav', mix)
for name, a in (('voice_only.mp3', voice), ('sfx_only.mp3', fx), ('mix.mp3', mix)):
    write(REV / name, a)
(REV / 'sfx_cues.txt').write_text('\n'.join(f'{c}' for c in kit.cues), encoding='utf-8')
print('OK', round(DUR, 2), 's, peak', round(float(peak), 2))
