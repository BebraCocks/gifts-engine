"""Voice only on the output timeline (RubUp = its own sound, kept so the timing is real) -> build/review/voice_only.mp3.
The author gets this right after the takes are cut (AGENTS.md, 2026-11-08)."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import banner
import sound
from timeline import DUR, ON, TAKES
from events import AD_STOP

SR = 48000
n = int(round(DUR * SR))
v = np.zeros((n, 2))
for k, take in enumerate(TAKES):
    d = sound.load_stereo(take, SR)
    s = round(ON[k] * SR)
    c = min(len(d), n - s)
    v[s:s + c] += d[:c] * 0.85
out = banner.Breaks([AD_STOP], cy=960).audio(v * 1.4, SR, banner=False)
rev = paths.build(HERE) / 'review'
rev.mkdir(parents=True, exist_ok=True)
raw = (np.clip(out, -0.98, 0.98) * 32767).astype('<i2').tobytes()
subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-',
                '-b:a', '192k', str(rev / 'voice_only.mp3')], input=raw, check=True)
print(rev / 'voice_only.mp3', round(len(out) / SR, 2), 's')
