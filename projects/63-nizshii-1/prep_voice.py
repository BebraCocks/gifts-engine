"""Чистит дубли (фильтр шума, утверждённый автором 2026-11-24) и режет клипы voice/clips/<KEY>.wav.
    python -B projects/63-nizshii-1/prep_voice.py"""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
from script import CLIPS

CLEAN = ('highpass=f=60,afftdn=nr=18:nf=-50:tn=1,'
         'agate=threshold=0.006:ratio=4:range=0.06:attack=5:release=180:knee=3')
V = HERE / 'voice'
(V / 'clean').mkdir(exist_ok=True)
(V / 'clips').mkdir(exist_ok=True)
for take in sorted({c[1] for c in CLIPS}):
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-i', str(V / 'raw' / f'{take}.mp3'), '-af', CLEAN,
                    '-ar', '48000', '-ac', '2', str(V / 'clean' / f'{take}.wav')], check=True)
for key, take, t0, t1, _, _ in CLIPS:
    d = t1 - t0
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-t', f'{d:.3f}',
                    '-i', str(V / 'clean' / f'{take}.wav'),
                    '-af', f'afade=t=in:d=0.015,afade=t=out:st={d - 0.04:.3f}:d=0.04,volume=1.0',
                    '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(V / 'clips' / f'{key}.wav')], check=True)
    print(key, round(d, 2))
