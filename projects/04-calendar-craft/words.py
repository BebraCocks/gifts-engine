"""Word times in content seconds from Fish Audio ASR of the selected takes (voice/LNN.asr.json,
engine/tools/fish_asr.py); estimated timing as a fallback."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import captions
from script import LINES
from timeline import ON, END, HAS_NARRATION, TAKES, KEY


def _norm(w):
    return re.sub(r'[^0-9a-zа-яё]', '', w.casefold().replace('ё', 'е'))


WORDS = []
for k, (who, spoken, key, pause) in enumerate(LINES):
    asr = Path(str(TAKES[k])[:-4] + '.asr.json')
    if HAS_NARRATION and asr.exists():
        segs = json.loads(asr.read_text(encoding='utf-8'))['segments']
        words = [(s['text'], ON[k] + s['start'], ON[k] + s['end']) for s in segs]
    elif HAS_NARRATION:
        words = [(w, t, t + 0.3) for w, t in captions.estimate_word_times(str(TAKES[k]), spoken, offset=ON[k])]
    else:
        split = spoken.split()
        step = (END[k] - ON[k]) / max(1, len(split))
        words = [(w, ON[k] + j * step, ON[k] + (j + 1) * step) for j, w in enumerate(split)]
    WORDS.append(words)


def wt(line, word, occurrence=0, end=False):
    """line: index or screen key; returns the start (or end) of the word in content seconds."""
    k = KEY[line] if isinstance(line, str) else line
    m = [(a, b) for w, a, b in WORDS[k] if _norm(w) == _norm(word)]
    if not m:
        raise KeyError(f'{word!r} not in line {k + 1}: {[w for w, _, _ in WORDS[k]]}')
    return m[occurrence][1 if end else 0]
