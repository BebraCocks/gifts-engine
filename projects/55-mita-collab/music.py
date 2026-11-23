"""Музыка: «Raving Energy» — Kevin MacLeod (incompetech.com), CC BY 4.0 (выбор автора 2026-11-22). Тихо, фоном."""
import subprocess
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
TRACK = HERE / 'input' / 'music' / 'incompetech' / 'Raving_Energy.mp3'
OFFSET = 0.0
LEVEL_DB = -30.0
DUCK_DB = -7.0


def _decode(sr, ch=2, start=0.0, dur=None):
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{start:.3f}', '-i', str(TRACK)]
    if dur:
        cmd += ['-t', f'{dur:.3f}']
    cmd += ['-ac', str(ch), '-ar', str(sr), '-f', 's16le', '-']
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, '<i2').astype(np.float64) / 32768
    return x.reshape(-1, ch)


def music(n, voice_env, sr=48000):
    x = _decode(sr, 2, OFFSET, n / sr + 1)
    rms = np.sqrt(np.mean(x[:sr * 40] ** 2)) + 1e-9
    x = x / rms * 10 ** (LEVEL_DB / 20)
    out = np.zeros((n, 2))
    out[:min(n, len(x))] = x[:n]
    f = int(0.3 * sr)
    out[:f] *= np.linspace(0, 1, f)[:, None]
    tail = min(n, int(1.4 * sr))
    out[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.5
    return out * (10 ** (DUCK_DB * np.clip(voice_env, 0, 1) / 20))[:, None]
