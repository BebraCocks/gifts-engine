"""Content timeline from the selected takes voice/L01..L14.wav. A round question q* starts the 5 s timer; the cells flip
at REVEAL = timer end; the answer a* follows. Text estimate as fallback (no narration)."""
from pathlib import Path
import wave
import config
from script import LINES, TIMER

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / f'L{k:02d}.wav' for k in range(1, len(LINES) + 1)]
HAS_NARRATION = not config.WITHOUT_NARRATION and all(p.is_file() for p in TAKES)


def _len(k):
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            return w.getnframes() / w.getframerate()
    return max(1.4, len(LINES[k][0].split()) / 2.8)


START = 0.08
SWAP = 0.42          # open cards fly out, new closed cells drop in
LAND = 0.22          # new cells land before the question
ANS = 0.38           # the cells flip, then the answer starts
HOLD = 0.32          # the answer settles before the swap
AD_HOLD = 0.35       # the answer settles before RubUp
TABLE_READ = 1.1     # pause to read the levels table before the last line
ON, END = [0.0] * len(LINES), [0.0] * len(LINES)
ROUND_IN, TIMER0, REVEAL = [], [], []
ON[0] = START
END[0] = START + _len(0)
ON[1] = END[0] + 0.22
END[1] = ON[1] + _len(1)
cur = END[1] + 0.12
for r in range(5):
    q, a = 2 + 2 * r, 3 + 2 * r
    ROUND_IN.append(cur)
    ON[q] = cur + LAND
    END[q] = ON[q] + _len(q)
    TIMER0.append(ON[q])
    REVEAL.append(ON[q] + TIMER)
    ON[a] = REVEAL[-1] + ANS
    END[a] = ON[a] + _len(a)
    cur = END[a] + (AD_HOLD if a == 7 else HOLD) + (0.0 if r == 4 else SWAP)
    if a == 7:
        cur += 0.1
OUTRO = END[11] + HOLD + 0.1               # cards go, the levels table comes in
ON[12] = OUTRO + 0.45
END[12] = ON[12] + _len(12)
ON[13] = END[12] + TABLE_READ
END[13] = ON[13] + _len(13)
DUR = END[13] + 0.8
KEY = {LINES[k][1]: k for k in range(len(LINES))}
