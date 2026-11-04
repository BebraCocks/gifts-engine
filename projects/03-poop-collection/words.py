"""Estimated word timing; correct anchors against real speech before delivery."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import captions
from script import LINES
from timeline import ON, END, HAS_NARRATION, TAKES

WORDS = []
for k, (spoken, screen, style, pause) in enumerate(LINES):
    if HAS_NARRATION:
        words = captions.estimate_word_times(str(TAKES[k]), spoken, offset=ON[k])
    else:
        split = spoken.split()
        words = [(word, ON[k] + j * (END[k]-ON[k]) / max(1, len(split))) for j, word in enumerate(split)]
    WORDS.append(words)


def wt(line, word, occurrence=0):
    """line is zero-based; occurrence disambiguates repeated words."""
    matches = [t for text, t in WORDS[line] if text.strip('.,!?—:;«»"').casefold() == word.casefold()]
    return matches[occurrence]
