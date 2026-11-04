"""Content timeline from the selected Drama 3 takes (voice/L01.wav ...).
Total output = content DUR + two RubUp breaks (6.1 s each) = 119.5 s."""
from pathlib import Path
import wave
import numpy as np
import config
from script import LINES

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / f'L{k:02d}.wav' for k in range(1, len(LINES) + 1)]
HAS_NARRATION = not config.WITHOUT_NARRATION and all(p.is_file() for p in TAKES)
TARGET_DUR = 107.7          # content seconds; + 2 x 6.115 s of RubUp = 119.93 s output
LEAD = 0.7                  # the hand starts drawing before the first word
EXTRA = {0: 0.8, 1: 0.3, 2: 0.5, 3: 0.2, 10: 0.2}   # extra breath after these lines (zero-based)


def _speech_span(path):
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        dur = w.getnframes() / sr
    h = sr // 100
    env = np.array([np.sqrt((x[i:i + h] ** 2).mean()) for i in range(0, len(x) - h, h)])
    on = np.nonzero(20 * np.log10(env + 1e-9) > -40)[0]
    return on[0] / 100, on[-1] / 100 + 0.03, dur


ON, END, FILE_ON, SPAN = [], [], [], []
cursor = LEAD
for k, (spoken, chapter, pause) in enumerate(LINES):
    if HAS_NARRATION:
        a, b, _ = _speech_span(TAKES[k])
    else:
        a, b = 0.0, max(2.5, len(spoken.split()) / 2.2)
    FILE_ON.append(cursor - a)          # where the wav file starts in content time
    ON.append(cursor)                   # first sound of speech
    END.append(cursor + (b - a))        # last sound of speech
    SPAN.append((a, b))
    cursor = END[-1] + pause + EXTRA.get(k, 0.0)
TAIL = max(1.1, TARGET_DUR - cursor)
DUR = cursor + TAIL
CHAPTER = [c for _, c, _ in LINES]

if __name__ == '__main__':
    for k in range(len(LINES)):
        print(f'L{k+1:02d} {CHAPTER[k]:9s} {ON[k]:7.2f} -> {END[k]:7.2f}')
    print('DUR', round(DUR, 2), 'tail', round(TAIL, 2))
