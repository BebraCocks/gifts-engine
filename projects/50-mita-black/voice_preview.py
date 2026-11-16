"""Голос по таймлайну + музыка (без SFX и баннера) для проверки автором: build/review/voice_only.mp3, voice_music.mp3."""
import subprocess, sys, wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import numpy as np, sound, banner, music
from timeline import ON, TAKES, DUR, AD_STOP
SR = 48000; HERE = Path(__file__).resolve().parent
n = int(DUR * SR); v = np.zeros((n, 2))
for k, p in TAKES.items():
    d = sound.load_stereo(p, SR); s = round(ON[k] * SR); c = min(len(d), n - s); v[s:s + c] += d[:c] * 0.9
e = np.convolve(np.abs(v).max(1), np.ones(4800) / 4800, 'same'); e = np.clip(e / (np.percentile(e[e > 1e-4], 60) + 1e-9), 0, 1)
m = music.music(n, e, slow_from=None)
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)
rev = HERE / 'build' / 'review'; rev.mkdir(parents=True, exist_ok=True)
for name, x, ban in (('voice_only', v, False), ('voice_music', v + m, True)):
    y = BR.audio(x, SR, banner=ban)
    with wave.open(str(rev / f'{name}.wav'), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -.98, .98) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(rev / f'{name}.wav'), '-b:a', '192k', str(rev / f'{name}.mp3')], check=True)
print('content', round(DUR, 2), 'out', round(BR.out_dur(DUR), 2), 'ad at', round(AD_STOP, 2), round(AD_STOP / DUR, 2))
