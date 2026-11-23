"""56-oleg-frog: assemble the Fish Audio drama-3 takes into voice/L01..wav and build/review/voice_only*.mp3.

Voice (author, 2026-11-23): «Кубик в кубе» 2b932e13e5564601a6f5c705cecf36fe for Олег and Димон.
Мама: variant A — the same voice; variant B — «Мама» b39416cb4eae4b5aa4d2acf7782eab71 (author picks).
Each take: silence trimmed at the edges, then TEMPO via atempo (pitch unchanged).
Pauses between lines (GAP_AFTER) include the silent beats: kettle, RubUp slot, phone beeps, the turn.
"""
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / 'voice' / 'raw'
OUT = HERE / 'voice'
REVIEW = HERE / 'build' / 'review'
SR = 48000
TEMPO = 1.08
AD = 6.1   # RubUp at 1.1× (placeholder silence in voice_only)

# key, speaker, take (task id), pause after, s
LINES = [
    ('hook', 'O', '4d57c6e0f8284ae39cf8fa5b44b92998', 0.25),
    ('howlong', 'D', '2269288660d54e52afaba5e4471f12ec', 0.15),
    ('twohours', 'O', '5316753886bc4db387d1043dd19ece6c', 0.35),
    ('pzdc1', 'D', '8262fa3b26b24204b96432cb9b87bac4', 1.6),    # kettle: redden, steam, whistle
    ('pepe', 'D', 'fee87eb846a04d338ef0f0ff39ad9e57', 0.2),
    ('dm', 'D', '0a0bd33421de4ae1b195ac06b6eb214d', 0.2),
    ('wait', 'D', '6df329e5734242f2b483897ceac245ef', 0.4 + AD + 0.3),   # teaser → RubUp
    ('rule', 'D', '784ca7e3685d403587e785f78e5ae544', 0.2),
    ('ok', 'O', '941bbf95c1db4a0488c07092f4c6c9e6', 0.2),
    ('hunt', 'D', '54043a8dd92042c78795030a8a452114', 0.4),
    ('where', 'D', '0b63c5f7b17041d49822d4b980da4f6b', 0.15),
    ('phone', 'O', 'cf60526fd45d4c6e9b47c4ea9cd64a2a', 0.2),
    ('call', 'D', '3aa859d098b24a1eb244aa75b89d6b00', 2.2),     # beeps
    ('mom', 'M', '080aae6142984d43bc75dd7ef3051364', 1.4),      # the turn
    ('pzdc2', 'D', '9bdc0809f08a4c7c8b291aa666311152', 0.6),
]
MOM_B = 'f931d9e147594384bc8c7f4a4134b50a'


def load(task):
    wav = RAW / f'{task}.t.wav'
    if not wav.exists():
        subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', str(RAW / f'{task}.mp3'),
                        '-af', f'atempo={TEMPO}', '-ar', str(SR), '-ac', '1', str(wav)], check=True)
    with wave.open(str(wav)) as w:
        y = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64)
    env = np.abs(y) > 600
    idx = np.flatnonzero(env)
    a = max(0, idx[0] - int(0.03 * SR))
    b = min(len(y), idx[-1] + int(0.10 * SR))
    return y[a:b]


def write_wav(path, y):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.clip(y, -32768, 32767).astype('<i2').tobytes())


def build(mom_take, name):
    parts, t, rows = [], 0.0, []
    for i, (key, spk, take, gap) in enumerate(LINES, 1):
        y = load(mom_take if key == 'mom' else take)
        write_wav(OUT / f'L{i:02d}.wav', y) if name == 'voice_only' or key == 'mom' else None
        rows.append(f'L{i:02d} {key:9s} {spk} start {t:6.2f}  dur {len(y) / SR:5.2f}')
        parts += [y, np.zeros(int(gap * SR))]
        t += len(y) / SR + gap
    mix = np.concatenate(parts)
    REVIEW.mkdir(parents=True, exist_ok=True)
    tmp = REVIEW / f'{name}.wav'
    write_wav(tmp, mix)
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', str(tmp), '-b:a', '192k',
                    str(REVIEW / f'{name}.mp3')], check=True)
    tmp.unlink()
    print(f'{name}: {t:.2f} s total (RubUp slot {AD} s included)')
    print('\n'.join(rows))


if __name__ == '__main__':
    build(LINES[13][2], 'voice_only')
    build(MOM_B, 'voice_only_mom_b')
    sys.exit(0)
