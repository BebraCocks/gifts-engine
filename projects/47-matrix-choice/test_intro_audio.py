"""Звук пробы появления (Botanica V4 через sfxkit; история использования не пишется — это проба).
-> build/review/intro_sfx.wav и intro_test_sound.mp4 (видео пробы + звук)."""
import subprocess
import sys
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
import sfxkit

SR = 48000
DUR = 4.6
kit = sfxkit.Kit(HERE, seed=zlib.crc32(b'47-matrix-intro'))
buf = np.zeros((int(DUR * SR), 2))
add = kit.add
add(buf, 'scan', 0.0, gain_db=-14, fit=1.9, fade_out=0.4, label='green code pours down')
add(buf, 'glitch-text', 0.15, gain_db=-17, pan=-0.3, label='data chatter L')
add(buf, 'glitch-text', 0.55, gain_db=-18, pan=0.35, label='data chatter R')
add(buf, 'power-up', 0.25, gain_db=-15, align='start', fit=1.7, fade_out=0.3, label='the figure charges up')
add(buf, 'glitch', 1.15, gain_db=-16, label='code -> photo dissolve')
add(buf, 'impact', 1.95, gain_db=-12, align='peak', label='Morpheus formed (fists)')
add(buf, 'click', 2.0, gain_db=-20, label='glasses glint')
add(buf, 'whoosh-short', 2.52, gain_db=-17, label='fists open')
add(buf, 'pop', 2.68, gain_db=-19, label='palms open')
peak = np.abs(buf).max()
buf *= 10 ** (-2.0 / 20) / max(peak, 1e-6)          # preview: peak at -2 dBFS
rev = paths.build(HERE) / 'review'
with wave.open(str(rev / 'intro_sfx.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(buf, -0.98, 0.98) * 32767).astype('<i2').tobytes())
for c in kit.cues:
    print(f"{c['at']:5.2f}  {c['label']:32s} {c.get('file', '')}")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(rev / 'intro_test.mp4'), '-i', str(rev / 'intro_sfx.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(rev / 'intro_test_sound.mp4')], check=True)
print(rev / 'intro_test_sound.mp4')
