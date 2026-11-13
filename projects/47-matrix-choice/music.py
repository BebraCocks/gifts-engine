"""The author's track (Rob Dougan «Clubbed To Death», from the video the author sent; input/track_full.wav, 58.37 s)
fitted to the content length DUR in content time (RubUp pauses it like the voice).

Self-similarity (spectral frames, 2026-11-13): bars repeat almost exactly at a lag of 4.71 s around 25.9 s
(similarity 0.88, the best place in the middle of the track). The content is longer than the track, so those two
bars are played twice (…25.9 → 30.61 → back to 25.9 → 30.61…), joined with an 80 ms crossfade at the same phase.
The small remainder is absorbed by a pitch-preserving time stretch (atempo ≈ 0.99, inaudible). The track's own
fade-out ends the video."""
import subprocess
import wave
from pathlib import Path
import numpy as np
from timeline import DUR

HERE = Path(__file__).resolve().parent
SRC = HERE / 'input' / 'track_full.wav'
LOOP_A, LOOP_B = 25.90, 30.61
XF = 0.08


def _read(p):
    with wave.open(str(p)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').reshape(-1, w.getnchannels()).astype(np.float64) / 32768
    return x, sr


def fitted(sr_out=48000):
    x, sr = _read(SRC)
    a, b, f = int(LOOP_A * sr), int(LOOP_B * sr), int(XF * sr)
    head = x[:b]
    tail = x[a:]                                   # from the loop start again
    ramp = np.linspace(0, 1, f)[:, None]
    joined = np.concatenate([head[:-f], head[-f:] * (1 - ramp) + tail[:f] * ramp, tail[f:]])
    tempo = (len(joined) / sr) / DUR
    tmp_in, tmp_out = HERE / 'build' / '_mus_in.wav', HERE / 'build' / '_mus_out.wav'
    tmp_in.parent.mkdir(exist_ok=True)
    with wave.open(str(tmp_in), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(joined, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(tmp_in), '-af', f'atempo={tempo:.6f}',
                    '-ar', str(sr_out), str(tmp_out)], check=True)
    y, _ = _read(tmp_out)
    tmp_in.unlink()
    tmp_out.unlink()
    return y, tempo


def music(n, sr):
    y, _ = fitted(sr)
    out = np.zeros((n, 2))
    m = min(n, len(y))
    out[:m] = y[:m]
    k = int(0.4 * sr)                              # never a click at the very end
    out[n - k:] *= np.linspace(1, 0, k)[:, None]
    return out


if __name__ == '__main__':
    y, tempo = fitted()
    print(f'track {len(y) / 48000:.2f} s for content {DUR:.2f} s, atempo {tempo:.4f}')
