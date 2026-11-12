"""VOICE_CUES -> build/review/voice_only.mp3 and voice_on_track.mp3 (voice over the whole track, as in the mix)."""
import subprocess
from pathlib import Path
import numpy as np
import script
from timeline import DUR

HERE = Path(__file__).resolve().parent
SR = 48000
TRACK = HERE / 'input' / 'track.m4a'
MUSIC_GAIN = 0.55


def read(path, sr=SR, ch=1):
    raw = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', str(path), '-vn', '-ar', str(sr), '-ac', str(ch),
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<i2').astype(np.float64).reshape(-1, ch) / 32768


def tempo(y, t):
    if t == 1.0:
        return y
    p = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-',
                        '-af', f'atempo={t}', '-f', 'f64le', '-'], input=y.astype('<f8').tobytes(), capture_output=True,
                       check=True)
    return np.frombuffer(p.stdout, '<f8')


def fade(y, ms=12):
    f = min(len(y) // 2, SR * ms // 1000)
    y = y.copy()
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def voice_track(n, stereo=False, quiet=False):
    out = np.zeros((n, 2)) if stereo else np.zeros(n)
    for line, parts, start, t, pan in script.VOICE_CUES:
        x = read(HERE / 'voice' / f'{line}.wav')[:, 0]
        x = x / max(1e-9, np.abs(x).max())                    # every line at the same peak
        y = np.concatenate([fade(x[int(a * SR):(int(b * SR) if b else len(x))], 40 if b else 12) for a, b in parts])
        y = tempo(y, t)
        k = int(start * SR)
        m = len(y[:max(0, n - k)])
        if stereo:
            out[k:k + m, 0] += y[:m] * np.sqrt(0.5 * (1 - pan))
            out[k:k + m, 1] += y[:m] * np.sqrt(0.5 * (1 + pan))
        else:
            out[k:k + m] += y[:m]
        if not quiet:
            print(f'{line} {start:6.2f}–{start + len(y) / SR:6.2f}')
    return out


def music_track(n):
    """The author's track once, from its start; a short fade at the very end."""
    tr = read(TRACK, ch=2)
    out = np.zeros((n, 2))
    m = min(n, len(tr))
    out[:m] = tr[:m]
    tail = int(0.6 * SR)
    out[n - tail:] *= np.linspace(1, 0, tail)[:, None]
    return out


def duck_env(v):
    env = np.convolve(np.abs(v).max(1), np.ones(SR // 20) / (SR // 20), 'same')
    duck = 1 - 0.60 * np.clip(env / 0.03, 0, 1)
    return env, np.convolve(duck, np.ones(SR // 8) / (SR // 8), 'same')


def write(path, x):
    x = np.clip(x, -1, 1)
    ch = 1 if x.ndim == 1 else x.shape[1]
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', str(ch), '-i', '-',
                    '-b:a', '192k', str(path)], input=(x * 32767).astype('<i2').tobytes(), check=True)


def main():
    n = int(round(DUR * SR))
    music = music_track(n)
    v = voice_track(n, stereo=True)
    v *= 0.89 / max(1e-9, np.abs(v).max())
    _, duck = duck_env(v)
    mix = music * MUSIC_GAIN * duck[:, None] + v * 0.95
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    out = HERE / 'build' / 'review'
    out.mkdir(parents=True, exist_ok=True)
    write(out / 'voice_only.mp3', v)
    write(out / 'voice_on_track.mp3', mix)
    print('->', out / 'voice_only.mp3', out / 'voice_on_track.mp3')


if __name__ == '__main__':
    main()
