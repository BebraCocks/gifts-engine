"""Content timeline from the selected takes voice/L01..L06.wav (text estimate as fallback, no narration).
Hook (L01) -> 4 signs, one take each (character -> mug -> «Прогноз: …»), the mug lands at SIGN_IN -> outro (L06).
RubUp right after the third sign (Virgo): the middle of the video (thumbnails) stays content (author, 2026-11-09)."""
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
SWAP = 0.3           # previous mug leaves -> next mug lands
LAND = 0.2           # the mug lands before its line starts
AD_HOLD = 0.4        # the last words settle before RubUp
ON, END = [0.0] * len(LINES), [0.0] * len(LINES)
SIGN_IN = []
ON[0] = START
END[0] = ON[0] + _len(0)
cur = END[0] + 0.15
AD_STOP = None
for s in range(4):
    k = 1 + s
    SIGN_IN.append(cur)
    ON[k] = cur + LAND
    END[k] = ON[k] + _len(k)
    cur = END[k] + SWAP
    if s == 2:
        AD_STOP = END[k] + AD_HOLD
        cur = AD_STOP + 0.6       # Virgo + teaser stay on the RubUp freeze frame, then swap
OUTRO = END[4] + 0.3
ON[5] = OUTRO + 0.3
END[5] = ON[5] + _len(5)
DUR = END[5] + 0.7
KEY = {LINES[k][1]: k for k in range(len(LINES))}
