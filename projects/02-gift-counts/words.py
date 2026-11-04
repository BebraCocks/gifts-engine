"""No narration: word anchors are not used; events.py holds authored times."""
WORDS = []


def wt(line, word, occurrence=0):
    raise RuntimeError('Text-only clip: use events.py times')
