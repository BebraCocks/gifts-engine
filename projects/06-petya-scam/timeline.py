"""Content timeline from the selected takes voice/L01..L14.wav (select_takes.py); text estimate as fallback."""
from pathlib import Path
import wave
import config
from script import LINES

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / f'L{k:02d}.wav' for k in range(1, len(LINES) + 1)]
HAS_NARRATION = not config.WITHOUT_NARRATION and all(p.is_file() for p in TAKES)
START, TAIL = 0.15, 0.2
ON, END, SPEAKER = [], [], []
cursor = START
for k, (who, spoken, key, pause) in enumerate(LINES):
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            duration = w.getnframes() / w.getframerate()
    else:
        duration = max(1.2, len(spoken.split()) / 2.6)
    ON.append(cursor)
    END.append(cursor + duration)
    SPEAKER.append(who)
    cursor += duration + pause
DUR = END[-1] + TAIL
KEY = {LINES[k][2]: k for k in range(len(LINES))}
