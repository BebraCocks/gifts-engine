"""Таймлайн содержания (без RubUp): дубли нарезаются в voice/Lxx.wav командой prep_voice.py."""
from pathlib import Path
import wave
from script import SEQ, TIMER

HERE = Path(__file__).resolve().parent
ITEMS = [s for s in SEQ if s[1]]
TAKES = [HERE / 'voice' / f'L{k:02d}_{s[0]}.wav' for k, s in enumerate(ITEMS, 1)]
HAS_NARRATION = all(p.is_file() for p in TAKES)
AT, ON, END, IDS = {}, [], [], []
cursor, k, question_end = 0.3, 0, None
for cid, src, a, b, pause, text, speed, *_ in SEQ:
    if src is None:                     # переход-пузыри: только пауза в речи
        AT[cid] = cursor
        cursor += pause
        continue
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            d = w.getnframes() / w.getframerate()
    else:
        d = (b - a) / speed
    AT[cid] = cursor
    ON.append(cursor); END.append(cursor + d); IDS.append(cid)
    if cid in ('N2', 'N6'):
        question_end = cursor + d
    if pause == 'timer':
        pause = max(0.25, question_end + TIMER - (cursor + d))
    cursor += d + pause
    k += 1
END_OF = dict(zip(IDS, END))
DUR = cursor + 0.6
