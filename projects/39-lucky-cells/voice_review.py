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
if '--bomb' in sys.argv:                     # the gold-box explosion, small and quiet (author, v4), for this test only
    from events import E
    b = sound.load_stereo(paths.ROOT / 'input' / 'sfx' / 'botanica-v4' / 'impact-hit' / 'hit-impact-with-fx-04.flac', SR)[:int(1.3 * SR)]
    b[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))[:, None]
    b *= 0.22 / (np.abs(b).max() + 1e-9)
    s = round(E['gold_open'] * SR)
    v[s:s + len(b)] += b[:n - s]
out = banner.Breaks([AD_STOP], cy=960).audio(v * 1.4, SR, banner=False)
rev = paths.build(HERE) / 'review'
NAME = 'voice_bomb_test.mp3' if '--bomb' in sys.argv else 'voice_only.mp3'
rev.mkdir(parents=True, exist_ok=True)
raw = (np.clip(out, -0.98, 0.98) * 32767).astype('<i2').tobytes()
subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-',
                '-b:a', '192k', str(rev / NAME)], input=raw, check=True)
print(rev / NAME, round(len(out) / SR, 2), 's')
