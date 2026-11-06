"""Word times in content seconds. L01–L08: Fish Audio ASR of the raw takes (data/asr_v2.json) mapped through
voice/LNN.map.json (silence trimming in select_takes.py). L09–L10 were not recognised (author stopped ASR):
their words are estimated from the voice envelope (captions.estimate_word_times).
CAPTION: what the subtitles show (Latin model name, no dashes); one token per spoken word."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import captions
from script import LINES, MODEL_NAME, MODEL_SAY
from timeline import ON, END, HAS_NARRATION, TAKES, KEY

HERE = Path(__file__).resolve().parent
ASR = json.loads((HERE / 'data' / 'asr_v2.json').read_text(encoding='utf-8'))


def _norm(w):
    return re.sub(r'[^0-9a-zа-яё]', '', w.casefold().replace('ё', 'е'))


def caption_tokens(spoken):
    s = spoken.replace(MODEL_SAY, MODEL_NAME)
    out = []
    for w in s.split():
        if _norm(w):
            out.append(w)
        elif out:                                   # a standalone dash stays with the previous word
            out[-1] += '\u00a0' + w
    return out


def _raw_to_out(k, r):
    m = Path(str(TAKES[k])[:-4] + '.map.json')
    if not m.exists():
        return r
    segs = json.loads(m.read_text())['segments']
    for a, o, n in segs:
        if r < a:
            return o
        if r < a + n:
            return o + (r - a)
    a, o, n = segs[-1]
    return o + n


# L09–L10 without ASR: starts of words read from the 20 ms voice envelope (pauses between words), seconds of the
# trimmed take. A rough estimate, not recognition; check on the move.
ENVELOPE = {8: {0: 0.04, 2: 0.86, 3: 1.30, 4: 1.88, 5: 1.95, 6: 2.40},
            9: {0: 0.02, 1: 0.70, 2: 1.50, 3: 2.48, 4: 2.62, 7: 4.36}}

WORDS = []          # per line: [(caption word, start, end)] in content seconds
for k, (who, spoken, key, pause) in enumerate(LINES):
    toks = caption_tokens(spoken)
    asr = ASR.get(f'L{k + 1:02d}')
    if HAS_NARRATION and asr and len(asr) == len(toks):
        words = [(w, ON[k] + _raw_to_out(k, a), ON[k] + _raw_to_out(k, b)) for w, (_, a, b) in zip(toks, asr)]
    elif HAS_NARRATION and k in ENVELOPE:
        est = captions.estimate_word_times(str(TAKES[k]), ' '.join(toks), offset=ON[k])
        est = captions.retime(est, {i: ON[k] + v for i, v in ENVELOPE[k].items()})
        words = [(w, t, (est[j + 1][1] if j + 1 < len(est) else END[k])) for j, (w, t) in enumerate(est)]
    elif HAS_NARRATION:
        est = captions.estimate_word_times(str(TAKES[k]), ' '.join(toks), offset=ON[k])
        words = [(w, t, (est[j + 1][1] if j + 1 < len(est) else END[k])) for j, (w, t) in enumerate(est)]
    else:
        step = (END[k] - ON[k]) / max(1, len(toks))
        words = [(w, ON[k] + j * step, ON[k] + (j + 1) * step) for j, w in enumerate(toks)]
    WORDS.append(words)


def wt(line, word, occurrence=0, end=False):
    """line: index or screen key; returns the start (or end) of the word in content seconds."""
    k = KEY[line] if isinstance(line, str) else line
    m = [(a, b) for w, a, b in WORDS[k] if _norm(w) == _norm(word)]
    if not m:
        m = [(a, b) for w, a, b in WORDS[k] if len(_norm(word)) >= 5 and _norm(w)[:5] == _norm(word)[:5]]
    if not m:
        raise KeyError(f'{word!r} not in line {k + 1}: {[w for w, _, _ in WORDS[k]]}')
    return m[occurrence][1 if end else 0]
