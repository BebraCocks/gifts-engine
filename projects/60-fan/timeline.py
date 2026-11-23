"""Тайминг от реальных длительностей дублей voice/fast/*.wav (prep_voice.py)."""
from pathlib import Path
import wave
from script import LINES

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / 'fast' / f'{k}.wav' for k, *_ in LINES]
HAS_NARRATION = all(p.is_file() for p in TAKES)
KEYS = [k for k, *_ in LINES]
ON, END = [], []
cursor = 0.35
for k, (key, spoken, screen, pause) in enumerate(LINES):
    with wave.open(str(TAKES[k])) as w:
        duration = w.getnframes() / w.getframerate()
    ON.append(cursor)
    END.append(cursor + duration)
    cursor += duration + pause
DUR = cursor + 1.6
S = dict(zip(KEYS, ON))      # начало реплики
E = dict(zip(KEYS, END))     # конец реплики

if __name__ == '__main__':
    for k in KEYS:
        print(k, round(S[k], 2), round(E[k], 2))
    print('DUR', round(DUR, 2))
