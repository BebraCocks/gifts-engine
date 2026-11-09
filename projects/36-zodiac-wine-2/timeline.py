"""Content timeline from the selected takes voice/L01..L06.wav (text estimate as fallback, no narration).
Hook (L01) -> 4 signs, one take each (character -> mug -> «Прогноз: …»), the mug lands at SIGN_IN -> outro (L06).
v2 (author, 2026-11-09): RubUp inside Gemini (sign 3) so the middle frame of the video (thumbnails) is content."""
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
# RubUp in the silence inserted after «…две личности.» (select_takes.INSERT), as in 42-zodiac-wine-1b: the middle
# frame is Gemini without the banner, the banner starts ~2 s later.
_ins = HERE / 'voice' / 'L04.insert.json'
AD_PAD = 0.95                    # into the inserted 1.4 s: the ramp (0.4 s) is centred on AD_STOP, 0.25 s left after
if _ins.is_file():
    import json
    AD_STOP = ON[3] + json.loads(_ins.read_text())['at'] + AD_PAD
else:
    AD_STOP = ON[3] + 0.5 * (END[3] - ON[3])
TEASER_ON = AD_STOP - AD_PAD + 0.05
OUTRO = END[4] + 0.3
ON[5] = OUTRO + 0.3
END[5] = ON[5] + _len(5)
DUR = END[5] + 0.7
KEY = {LINES[k][1]: k for k in range(len(LINES))}
