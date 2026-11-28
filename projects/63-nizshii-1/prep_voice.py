"""Чистка шума (фильтр, утверждённый автором), обрезка тишины по краям и выравнивание громкости каждого клипа
к TARGET_LUFS одним усилением. Пишет voice/clips/<KEY>.wav и печатает разброс громкости.
    python -B projects/63-nizshii-1/prep_voice.py"""
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
from script import CLIPS, TARGET_LUFS

CLEAN = ('highpass=f=60,afftdn=nr=18:nf=-50:tn=1,'
         'agate=threshold=0.006:ratio=4:range=0.06:attack=5:release=180:knee=3,'
         'silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.06,areverse,'
         'silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.12,areverse')
V = HERE / 'voice'
(V / 'clips').mkdir(exist_ok=True)


def lufs(path):
    r = subprocess.run([paths.ffmpeg(), '-hide_banner', '-i', str(path), '-af', 'ebur128', '-f', 'null', '-'],
                       capture_output=True, text=True)
    line = [x for x in r.stderr.splitlines() if x.strip().startswith('I:')][-1]
    return float(line.split()[1])


out = {}
for key, take, *_ in CLIPS:
    tmp = V / 'clips' / f'{key}_tmp.wav'
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-i', str(V / 'raw' / f'{take}.mp3'), '-af', CLEAN,
                    '-ar', '48000', '-ac', '2', str(tmp)], check=True)
    gain = TARGET_LUFS - lufs(tmp)
    dst = V / 'clips' / f'{key}.wav'
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-i', str(tmp), '-af',
                    f'volume={gain:.2f}dB,afade=t=in:d=0.02,areverse,afade=t=in:d=0.05,areverse,alimiter=limit=0.95',
                    '-c:a', 'pcm_s16le', str(dst)], check=True)
    tmp.unlink()
    out[key] = round(lufs(dst), 2)
vals = list(out.values())
print(json.dumps(out, ensure_ascii=False))
print('LUFS min', min(vals), 'max', max(vals), 'spread dB', round(max(vals) - min(vals), 2))
