"""VOICE_CUES -> build/review/voice_only.mp3 (голос по таймлайну трека) и voice_on_track.mp3 (голос + трек, трек
приглушён под речью). Длина = длине трека."""
import subprocess
import wave
from pathlib import Path
import numpy as np
import script

HERE = Path(__file__).resolve().parent
SR = 48000
TRACK = HERE / 'input' / 'aura_track.mp4'


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


def voice_track(n):
    out = np.zeros(n)
    for line, parts, start, t in script.VOICE_CUES:
        x = read(HERE / 'voice' / f'{line}.wav')[:, 0]
        y = np.concatenate([fade(x[int(a * SR):(int(b * SR) if b else len(x))], 40 if b else 12) for a, b in parts])
        y = tempo(y, t)
        k = int(start * SR)
        out[k:k + len(y)] += y[:max(0, n - k)]
        print(f'{line} {start:6.2f}–{start + len(y) / SR:6.2f}')
    return out


def write(path, x):
    x = np.clip(x, -1, 1)
    ch = 1 if x.ndim == 1 else x.shape[1]
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', str(ch), '-i', '-',
                    '-b:a', '192k', str(path)], input=(x * 32767).astype('<i2').tobytes(), check=True)


def main():
    music = read(TRACK, ch=2)
    v = voice_track(len(music))
    v *= 0.89 / max(1e-9, np.abs(v).max())                         # пик голоса −1 dBFS
    env = np.convolve(np.abs(v), np.ones(SR // 20) / (SR // 20), 'same')
    duck = 1 - 0.45 * np.clip(env / 0.03, 0, 1)                   # трек −5 dB под речью
    duck = np.convolve(duck, np.ones(SR // 8) / (SR // 8), 'same')
    mix = music * 0.55 * duck[:, None] + v[:, None] * 0.95
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    out = HERE / 'build' / 'review'
    out.mkdir(parents=True, exist_ok=True)
    write(out / 'voice_only.mp3', v)
    write(out / 'voice_on_track.mp3', mix)
    print('->', out / 'voice_only.mp3', out / 'voice_on_track.mp3')


if __name__ == '__main__':
    main()
