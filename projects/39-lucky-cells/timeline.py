"""Content timeline from the selected takes voice/L01..L15.wav. A round question q* starts the 5 s timer; the cells flip
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
SWAP = 0.38          # open cards fly out, new closed cells drop in
LAND = 0.16          # new cells land before the question
ANS = 0.30           # the cells flip, then the answer starts
HOLD = 0.26          # the answer settles before the swap
AD_HOLD = 0.35       # the answer settles before RubUp
TABLE_READ = 0.7     # pause to read the levels table before the last line
ON, END = [0.0] * len(LINES), [0.0] * len(LINES)
ROUND_IN, TIMER0, REVEAL = [], [], []
ON[0] = START
END[0] = START + _len(0)
ON[1] = END[0] + 0.14
END[1] = ON[1] + _len(1)
KEY = {LINES[k][1]: k for k in range(len(LINES))}
cur = END[1] + 0.12
for r in range(5):
    q, a = KEY[f'q{r + 1}'], KEY[f'a{r + 1}']
    ROUND_IN.append(cur)
    ON[q] = cur + LAND
    END[q] = ON[q] + _len(q)
    TIMER0.append(ON[q])                        # v6 (author): the round line is spoken while the 5 s timer runs
    REVEAL.append(max(TIMER0[-1] + TIMER, END[q] + 0.15))
    ON[a] = REVEAL[-1] + ANS
    END[a] = ON[a] + _len(a)
    cur = END[a] + (AD_HOLD if r == 2 else HOLD) + (0.0 if r == 4 else SWAP)
    if r == 2:
        cur += 0.1
G, S, O = KEY['gold'], KEY['sum'], KEY['outro']
GOLD_OPEN = END[KEY['a5']] + 0.2            # final: after the best cells are named, the gold box opens
ON[G] = GOLD_OPEN + 0.4
END[G] = ON[G] + _len(G)
OUTRO = END[G] + HOLD + 0.1                 # cards go, the levels table comes in
ON[S] = OUTRO + 0.45
END[S] = ON[S] + _len(S)
ON[O] = END[S] + TABLE_READ
END[O] = ON[O] + _len(O)
DUR = END[O] + 0.55
KEY = {LINES[k][1]: k for k in range(len(LINES))}
