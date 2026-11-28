"""Звук второго ролика: голос + музыка (приглушена под речь) + SFX Botanica через sfxkit."""
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import sfxkit  # noqa: E402
from timeline import V, T, D, DUR  # noqa: E402
import cues  # noqa: E402

SR = 48000
N = int(DUR * SR)


def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def place(buf, a, t, g=1.0):
    i = int(t * SR); a = a[:max(0, len(buf) - i)]; buf[i:i + len(a)] += a * g


def write(p, a):
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(p)],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)


voice = np.zeros((N, 2), np.float32)
for k, t in V.items():
    place(voice, load(HERE / 'voice' / f'{k}.wav'), t, 1.1)
duck = np.ones(N, np.float32)
for k, t in V.items():
    duck[int(t * SR):int((t + D[k] - 0.25) * SR)] = 0.32
w = int(0.1 * SR); duck = np.convolve(duck, np.ones(w) / w, 'same')
music = load(HERE / 'build' / 'music.wav')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0))) * duck[:, None] * 0.5

fx = np.zeros((N, 2), np.float32)
kit = sfxkit.Kit(HERE)
kit.add(fx, 'glitch', T['stop'], gain_db=-7)
kit.add(fx, 'impact', T['stop'], align='peak', gain_db=-7)
kit.add(fx, 'sparkle-whoosh', T['give'], gain_db=-10)
kit.add(fx, 'whoosh-short', T['forU'], align='peak', gain_db=-12)
for t in cues.CUTS:
    kit.add(fx, 'whoosh-deep', t, align='peak', gain_db=-13)
for t in cues.FLIP:
    kit.add(fx, 'flip' if int(t * 10) % 3 else 'counter', t, gain_db=-19)
kit.add(fx, 'confirm', T['win'], gain_db=-11)
for t in cues.CHESTS:
    kit.add(fx, 'riser', t, align='end', gain_db=-16)
    kit.add(fx, 'impact', t, align='peak', gain_db=-10)
    kit.add(fx, 'sparkle', t + 0.1, gain_db=-15)
kit.add(fx, 'error', T['self0'] + 0.3, gain_db=-13)
for t in cues.COINS:
    kit.add(fx, 'coin', t, gain_db=-17)
for t in cues.CART:
    kit.add(fx, ['pop', 'select-soft'], t, gain_db=-17)
for t in cues.DELIVER:
    kit.add(fx, 'cartoon-move', t, gain_db=-18)
kit.add(fx, 'power-up', T['top'], gain_db=-11)
for t in cues.TYPE_KEYS:
    kit.add(fx, 'typing', t, gain_db=-20)
for t in cues.COMMENTS:
    kit.add(fx, 'popup', t, gain_db=-15)
kit.add(fx, 'impact', T['dot'], align='peak', gain_db=-8)
kit.add(fx, 'riser', T['more'] + 1.4, align='end', gain_db=-13)
kit.add(fx, 'sparkle-whoosh', T['more'] + 1.4, gain_db=-11)
kit.save()

mix = voice + music + fx
pk = np.abs(mix).max()
if pk > 0.98:
    mix *= 0.98 / pk
write(HERE / 'build' / 'mix.wav', mix)
for n, a in (('voice_only.mp3', voice), ('sfx_only.mp3', fx), ('mix.mp3', mix)):
    write(HERE / 'build' / 'review' / n, a)
(HERE / 'build' / 'review' / 'sfx_cues.txt').write_text('\n'.join(map(str, kit.cues)), encoding='utf-8')
print('OK', round(DUR, 2), 'peak', round(float(pk), 2))
