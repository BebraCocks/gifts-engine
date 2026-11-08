"""Content timeline from the selected takes voice/L01..L11.wav (text estimate as fallback, no narration).
Hook (L01-L02) -> 4 signs, each: the mug lands (SIGN_IN), intro line s*, forecast line h* -> outro (L11).
RubUp right after the second forecast (h2)."""
from pathlib import Path
import wave
import config
from script import LINES

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / f'L{k:02d}.wav' for k in range(1, len(LINES) + 1)]
HAS_NARRATION = not config.WITHOUT_NARRATION and all(p.is_file() for p in TAKES)


def _len(k):
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            return w.getnframes() / w.getframerate()
    return max(1.4, len(LINES[k][0].split()) / 2.6)


START = 0.08
GAP = 0.2            # between the intro and the forecast of one sign
SWAP = 0.3           # previous mug leaves -> next mug lands
LAND = 0.2           # the mug lands before the intro line starts
AD_HOLD = 0.4        # the forecast settles before RubUp
ON, END = [0.0] * len(LINES), [0.0] * len(LINES)
SIGN_IN, FORECAST = [], []
ON[0] = START
END[0] = ON[0] + _len(0)
ON[1] = END[0] + 0.2
END[1] = ON[1] + _len(1)
cur = END[1] + 0.2
AD_STOP = None
for s in range(4):
    a, b = 2 + 2 * s, 3 + 2 * s
    SIGN_IN.append(cur)
    ON[a] = cur + LAND
    END[a] = ON[a] + _len(a)
    ON[b] = END[a] + GAP
    FORECAST.append(ON[b] - 0.1)
    END[b] = ON[b] + _len(b)
    cur = END[b] + SWAP
    if s == 1:
        AD_STOP = END[b] + AD_HOLD
        cur = AD_STOP + 0.6       # Leo + teaser stay on the RubUp freeze frame, then swap
OUTRO = END[9] + 0.3
ON[10] = OUTRO + 0.3
END[10] = ON[10] + _len(10)
DUR = END[10] + 0.8
KEY = {LINES[k][1]: k for k in range(len(LINES))}
