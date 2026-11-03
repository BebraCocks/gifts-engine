"""Несколько дублей drama-3 на естественной скорости 1,0 для каждой реплики; выбирается дубль,
который влезает в окно и звучит чище (меньше шумовой «плоскости» спектра в звонких кадрах).
Ключ — только FISH_API_KEY процесса. Старые дубли не удаляются."""
import hashlib
import os
import shutil
import sys
import wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine' / 'tools'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import fish_tts
import voice
from script import VOICE, VOICE_WIN

VARIANTS = 3


def flatness(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32768
        sr = w.getframerate()
    n = 2048; hop = 512; vals = []
    for s in range(0, len(x) - n, hop):
        f = x[s:s + n] * np.hanning(n)
        if np.sqrt(np.mean(f ** 2)) < 0.02:
            continue
        S = np.abs(np.fft.rfft(f))[5:int(8000 / sr * n)] + 1e-9
        vals.append(np.exp(np.mean(np.log(S))) / np.mean(S))
    return float(np.median(vals)) if vals else 1.0


def main():
    vid = os.environ['FISH_VOICE']; model = os.environ.get('FISH_TTS_MODEL', 'drama-3')
    folder = HERE / 'voice'
    for k, (text, (a, b)) in enumerate(zip(VOICE, VOICE_WIN), 1):
        if not text:
            continue
        tag = model.replace('.', '') + '_' + hashlib.sha1((model + vid + text).encode()).hexdigest()[:6]
        cands = [folder / f'V{k:02d}_{tag}_s100.wav'] + [folder / f'V{k:02d}_{tag}_s100_v{n}.wav' for n in range(2, VARIANTS + 1)]
        rows = []
        for c in cands:
            if not c.exists():
                fish_tts.tts(text, c, vid, speed=1.0)
            on, end = voice.onset_end(c)
            rows.append((end - on <= b - a, -flatness(c), c, end - on))
        rows.sort(key=lambda r: (not r[0], -r[1]))
        fits, negf, best, d = rows[0]
        shutil.copyfile(best, folder / f'V{k:02d}.wav')
        print(f'V{k:02d}: ' + ', '.join(f'{r[3]:.2f}с/{-r[1]:.3f}' for r in rows) + f' → {best.name} ({"влезает" if fits else "НЕ ВЛЕЗАЕТ"})', flush=True)


if __name__ == '__main__':
    main()
