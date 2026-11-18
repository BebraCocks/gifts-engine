"""Черновой звук для проверки автором: голос + «Dreams of Love and Literature» (приглушается под речью, обрывается на жути) + реклама RubUp.
Без SFX. → build/review/voice_music_preview.mp3"""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
import banner
import sound
import music
from timeline import DUR, ON, END, TAKES, AD_STOP

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)
n = int(round(DUR * SR))
v = np.zeros((n, 2))
for k, take in TAKES.items():
    d = sound.load_stereo(take, SR)
    s = round(ON[k] * SR)
    c = min(len(d), n - s)
    v[s:s + c] += d[:c] * 0.9
env = np.convolve(np.abs(v).max(1), np.ones(4800) / 4800, 'same')
env = np.clip(env / (np.percentile(env[env > 1e-4], 60) + 1e-9), 0, 1)
m = np.zeros((n, 2))                  # музыка ещё не выбрана — превью только голос + реклама
t = np.arange(n) / SR
c0, c1 = ON[4] - 0.12, END[4] + 0.15                       # жуть: музыка обрывается и плавно возвращается
g = 1 - np.clip((t - c0) / 0.08, 0, 1) + np.clip((t - c1) / 0.9, 0, 1)
m *= np.clip(g, 0, 1)[:, None]
out = BR.audio(v + m, SR)
b = paths.build(HERE) / 'review'
b.mkdir(parents=True, exist_ok=True)
with wave.open(str(b / 'voice_music_preview.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(out, -0.98, 0.98) * 32767).astype('<i2').tobytes())
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(b / 'voice_music_preview.wav'), '-b:a', '192k', str(b / 'voice_music_preview.mp3')], check=True)
print('контент', round(DUR, 2), 'с; с рекламой', round(BR.out_dur(DUR), 2), 'с')
