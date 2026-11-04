"""Timeline from the selected narration takes (voice/L01..L09.wav); text-only estimate as a fallback."""
from pathlib import Path
import wave
import config
from script import LINES

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / f'L{k:02d}.wav' for k in range(1, len(LINES) + 1)]
HAS_NARRATION = not config.WITHOUT_NARRATION and all(p.is_file() for p in TAKES)
START, TAIL = 0.2, 0.4
ON, END = [], []
cursor = START
for k, (spoken, screen, style, pause) in enumerate(LINES):
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            duration = w.getnframes() / w.getframerate()
    else:
        duration = max(2.5, len(spoken.split()) / 2.7)
    ON.append(cursor)
    END.append(cursor + duration)
    cursor += duration + pause
DUR = END[-1] + TAIL
