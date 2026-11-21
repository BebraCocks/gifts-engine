"""Таймлайн содержания (до вставки рекламы), общий для audio.py и render.py.
ON/END — начало и конец реплик (1-based), AD_STOP — где ролик встаёт на RubUp, DUR — длительность содержания."""
import json
from pathlib import Path
import script

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / 'voice' / 'lines.json').read_text(encoding='utf-8'))
TAKES = {m['line']: HERE / 'voice' / f"L{m['line']:02d}.wav" for m in META}
HAS_NARRATION = True
LEAD = 0.05          # v6: голос с первой доли секунды (зрители уходили на 0:01)
AD_GAP = 0.3


def build():
    on, end, stop = {}, {}, None
    t = LEAD
    for m in META:
        i = m['line']
        on[i], end[i] = t, t + m['dur']
        pause = script.LINES[i - 1][2]
        t += m['dur'] + pause
        if i == script.AD_AFTER:
            stop = end[i] + pause * 0.6
            t = stop + AD_GAP
    return on, end, stop, t + 0.3


ON, END, AD_STOP, DUR = build()
SCENE = {i: script.LINES[i - 1][1] for i in ON}
