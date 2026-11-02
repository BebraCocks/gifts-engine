"""PCM16 WAV speech bounds and fades; no account or voice identity is configured."""
import wave
import numpy as np

def onset_end(path, floor_db=30):
    with wave.open(str(path)) as w:
        if w.getsampwidth() != 2:
            raise ValueError("Expected PCM16 WAV")
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if not len(x) or np.max(np.abs(x)) < 1e-6:
        return 0.0, 0.0
    hop = max(1, sr // 100)
    env = np.array([np.sqrt(np.mean(x[k:k+hop] ** 2)) for k in range(0, len(x), hop)])
    active = np.flatnonzero(env > env.max() * 10 ** (-floor_db / 20))
    if not len(active):
        return 0.0, 0.0
    return max(0, (active[0] - 2) * hop / sr), min(len(x) / sr, (active[-1] + 1) * hop / sr)

def trim(x, sr, start, end, fade=0.03, tail=0.12):
    mask = np.ones(len(x))
    b = max(0, int(round(start * sr)))
    a = max(0, b - int(round(fade * sr)))
    mask[:a] = 0
    if b > a:
        mask[a:b] = np.linspace(0, 1, b-a, endpoint=False)
    mask[int(round((end + tail) * sr)):] = 0
    return x * (mask[:, None] if x.ndim == 2 else mask)
