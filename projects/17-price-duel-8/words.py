"""Word times in content seconds, estimated from the voice envelope (captions.estimate_word_times): the author
stopped the Fish ASR check (2026-11-06), so there is no recognition. Captions map the spoken words onto
script.CAPTIONS (Latin names, digits) with captions.align."""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import captions
from script import LINES, CAPTIONS
from timeline import ON, END, HAS_NARRATION, TAKES, KEY


def _norm(w):
    return re.sub(r'[^0-9a-zа-яё]', '', w.casefold().replace('ё', 'е'))


SPOKEN, WORDS = [], []      # per line: [(word, start)] spoken / caption tokens
for k, (spoken, key, pause) in enumerate(LINES):
    if HAS_NARRATION:
        sp = captions.estimate_word_times(str(TAKES[k]), spoken, offset=ON[k])
    else:
        split = spoken.split()
        sp = [(w, ON[k] + j * (END[k] - ON[k]) / len(split)) for j, w in enumerate(split)]
    SPOKEN.append(sp)
    WORDS.append(captions.align(sp, CAPTIONS[k]) if CAPTIONS[k] else [])


def wt(line, word, occurrence=0):
    """Start of a spoken word (content seconds); line = index or screen key."""
    k = KEY[line] if isinstance(line, str) else line
    m = [t for w, t in SPOKEN[k] if _norm(w) == _norm(word)]
    if not m:
        raise KeyError(f'{word!r} not in line {k + 1}: {[w for w, _ in SPOKEN[k]]}')
    return m[occurrence]
