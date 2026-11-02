"""Plot audio metrics: python engine/tools/audio_report.py projects/01-topic. Metrics do not replace listening."""
import sys
import wave
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.signal import spectrogram  # noqa: E402


def load(p):
    with wave.open(str(p)) as f:
        ch, sr = f.getnchannels(), f.getframerate()
        x = np.frombuffer(f.readframes(f.getnframes()), "<i2").astype(np.float32) / 32768
    return (x.reshape(-1, ch).mean(1) if ch > 1 else x), sr


proj = Path(sys.argv[1])
build = proj / "build"
mix, sr = load(build / "mix.wav")
stems = sorted((build / "stems").glob("*.wav")) if (build / "stems").exists() else []
fig, ax = plt.subplots(2 + len(stems), 1, figsize=(20, 3 + 1.6 * (2 + len(stems))), sharex=True)
f, t, S = spectrogram(mix, sr, nperseg=1024, noverlap=768)
ax[0].pcolormesh(t, f, 10 * np.log10(S + 1e-12), vmin=-110, vmax=-30, shading="auto")
ax[0].set_ylim(0, 10000)
ax[0].set_title("mix spectrogram", loc="left")
for k, p in enumerate(stems):
    x, _ = load(p)
    e = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, "same"))
    ax[k + 1].plot(np.arange(len(e)) / sr, e, lw=0.5)
    ax[k + 1].set_title(p.stem, loc="left")
e = np.sqrt(np.convolve(mix ** 2, np.ones(480) / 480, "same"))
ax[-1].plot(np.arange(len(e)) / sr, 20 * np.log10(e + 1e-6), lw=0.5)
ax[-1].set_ylim(-60, 0)
ax[-1].set_title("mix level, dBFS", loc="left")
ax[-1].set_xticks(np.arange(0, len(mix) / sr + 0.5, 0.5))
for a in ax:
    a.grid(alpha=0.25)
(build / "review").mkdir(parents=True, exist_ok=True)
plt.tight_layout()
plt.savefig(build / "review" / "audio.png", dpi=55)
print(build / "review" / "audio.png")