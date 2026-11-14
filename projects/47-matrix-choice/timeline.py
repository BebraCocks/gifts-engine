"""Content timeline from the selected takes voice/L01..L17.wav (Fish drama-3, ×1.15 tempo in select_takes.py).
Round r: fists open (ROUND_IN) → question q starts the 5 s timer (TIMER0) → Morpheus' short line t during the tricks →
REVEAL → answer a. After the answer the empty palms close into fists and open again for the next pair.
Content length is fixed: the whole video = the author's track (58.37 s) = content + RubUp (banner.Breaks adds ≈ 6.115 s)."""
from pathlib import Path
import wave
from script import LINES, TIMER

HERE = Path(__file__).resolve().parent
TAKES = [HERE / 'voice' / f'L{k:02d}.wav' for k in range(1, len(LINES) + 1)]
HAS_NARRATION = all(p.is_file() for p in TAKES)
MAX_TOTAL = 70.0           # author 2026-11-13: up to 70 s with RubUp; the track is extended to the content length
AD_EXTRA = 6.1155          # banner.Breaks([..]).out_dur(d) - d


def _len(k):
    if HAS_NARRATION:
        with wave.open(str(TAKES[k])) as w:
            return w.getnframes() / w.getframerate()
    return max(1.0, len(LINES[k][0].split()) / 2.4)


KEY = {LINES[k][1]: k for k in range(len(LINES))}
ON, END = [0.0] * len(LINES), [0.0] * len(LINES)
HOOK_ON = 0.05             # the code rain is already falling at frame 0; the voice comes in right after
ON[0] = HOOK_ON
END[0] = ON[0] + _len(0)
OPEN = 0.26                # fists → open palms, the pair assembles
CLOSE = 0.12               # after the answer: palms empty, close into fists (then OPEN again)
AD_HOLD = 0.04
ROUND_IN, TIMER0, REVEAL = [], [], []
cur = END[0] + 0.0
for r in range(5):
    q, t, a = 1 + 3 * r, 2 + 3 * r, 3 + 3 * r
    ROUND_IN.append(cur)
    ON[q] = cur + (0.0 if r == 0 else 0.04)                       # the pair assembles while the question is asked
    END[q] = ON[q] + _len(q)
    TIMER0.append(END[q] + 0.0)             # author: a real 5 s countdown AFTER the question (5…1, a tick a second)
    REVEAL.append(TIMER0[-1] + TIMER)
    ON[t] = TIMER0[-1] + 0.35                # Morpheus' short line right after «5», the tricks follow it
    END[t] = ON[t] + _len(t)
    ON[a] = REVEAL[-1] + (0.50 if r == 0 else 0.0)    # R1: he blows the chess away first, THEN speaks
    END[a] = ON[a] + _len(a)
    cur = END[a] + CLOSE + (AD_HOLD if LINES[a][1] == 'a3' else 0.0)
OUTRO = cur - CLOSE + 0.0
ON[16] = OUTRO
END[16] = ON[16] + _len(16)
DUR = END[16] + 0.20         # Morpheus dissolves into code after the last word
SLACK = MAX_TOTAL - AD_EXTRA - DUR
assert SLACK >= 0, f'content too long by {-SLACK:.2f} s'
for k in range(len(LINES) - 1):
    assert END[k] <= ON[k + 1] + 1e-6, f'line {k + 1} overlaps line {k + 2}'

if __name__ == '__main__':
    for k, (s, key) in enumerate(LINES):
        print(f'{key:6s} {ON[k]:6.2f}–{END[k]:6.2f}  {s}')
    print('reveals', [round(x, 2) for x in REVEAL], 'DUR', round(DUR, 2), 'slack', round(SLACK, 2))
