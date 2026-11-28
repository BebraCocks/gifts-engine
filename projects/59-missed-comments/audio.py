"""Звук: голос + музыка (приглушена под речь) + SFX из пака Botanica через sfxkit. build/mix.wav, build/review/*."""
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
    i = int(t * SR)
    a = a[:max(0, len(buf) - i)]
    buf[i:i + len(a)] += a * g


def write(p, a):
    p.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(p)],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)


voice = np.zeros((N, 2), np.float32)
for k, t in V.items():
    place(voice, load(HERE / 'voice' / f'{k}.wav'), t, 1.1)
duck = np.full(N, 1.0, np.float32)
for k, t in V.items():
    duck[int(t * SR):int((t + D[k] - 0.3) * SR)] = 0.33
w = int(0.1 * SR); duck = np.convolve(duck, np.ones(w) / w, 'same')
music = load(HERE / 'build' / 'music.wav')[:N]
music = np.pad(music, ((0, N - len(music)), (0, 0))) * duck[:, None] * 0.5

fx = np.zeros((N, 2), np.float32)
kit = sfxkit.Kit(HERE)
kit.add(fx, 'impact', V['L1'], align='peak', gain_db=-6)
kit.add(fx, 'sparkle-whoosh', V['L1'] + 0.05, gain_db=-10)
for t in cues.BURST:
    kit.add(fx, 'cartoon-move', t, gain_db=-16)
kit.add(fx, 'whoosh-short', T['help'], align='peak', gain_db=-12)
for t in cues.CUTS:
    kit.add(fx, 'whoosh', t, align='peak', gain_db=-12)
for t in cues.COUNTER:
    kit.add(fx, 'counter', t, gain_db=-17)
for t in cues.BUBBLES2:
    kit.add(fx, 'popup', t, gain_db=-15)
for t in T['tier']:
    kit.add(fx, 'whoosh-short', t, align='peak', gain_db=-10)
    kit.add(fx, 'impact', t + 0.18, align='peak', gain_db=-12)
kit.add(fx, 'impact', T['sold'], align='peak', gain_db=-8)
kit.add(fx, 'coin', T['sold'] + 0.1, gain_db=-9)
for t in cues.RAIN_POPS:
    kit.add(fx, ['pop', 'select-soft'], t, gain_db=-18)
kit.add(fx, 'power-up', T['top'] - 0.1, gain_db=-11)
kit.add(fx, 'sparkle', T['top'] + 0.4, gain_db=-11)
for t in cues.BUBBLES5:
    kit.add(fx, 'popup', t, gain_db=-14)
kit.add(fx, 'impact', T['each'], align='peak', gain_db=-8)
for t in cues.ARROW:
    kit.add(fx, 'boing', t, gain_db=-16)
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
