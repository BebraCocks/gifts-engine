"""Content timeline from the selected takes voice/L01..L12.wav. A question q* opens a round; its answer a* starts
right after the 5 s timer (TIMER), whatever the question length. Text estimate as fallback (no narration)."""
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
SWAP = 0.34          # items fly out / in between rounds
LAND = 0.25          # new items land before the question starts
HOLD = 0.36          # verdict stays after the answer
AD_HOLD = 0.45       # the answer settles before RubUp
ON, END = [0.0] * len(LINES), [0.0] * len(LINES)
ROUND_IN, TIMER0, REVEAL = [], [], []      # per round: items start dropping, timer starts, verdict
ON[0] = START
END[0] = START + _len(0)
cur = END[0] - 0.35          # round 1 drops in while the hook line ends
for r in range(5):
    q, a = 1 + 2 * r, 2 + 2 * r
    ROUND_IN.append(cur)
    ON[q] = cur + LAND
    END[q] = ON[q] + _len(q)
    TIMER0.append(ON[q])
    REVEAL.append(ON[q] + TIMER)
    ON[a] = REVEAL[-1] + 0.08
    END[a] = ON[a] + _len(a)
    cur = END[a] + (AD_HOLD if a == 6 else HOLD) + (0.0 if r == 4 else SWAP)
    if a == 6:
        cur += 0.2        # after RubUp the next round starts with a little air
OUTRO = END[10] + HOLD
ON[11] = OUTRO + 0.35
END[11] = ON[11] + _len(11)
DUR = END[11] + 0.35
KEY = {LINES[k][1]: k for k in range(len(LINES))}
