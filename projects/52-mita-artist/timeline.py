"""Таймлайн содержания (до вставки рекламы), общий для audio.py и render.py.
ON/END — начало и конец реплик (1-based), AD_STOP — где ролик встаёт на RubUp, DUR — длительность содержания."""
import json
from pathlib import Path
import script

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / 'voice' / 'lines.json').read_text(encoding='utf-8'))
TAKES = {m['line']: HERE / 'voice' / f"L{m['line']:02d}.wav" for m in META if script.LINES[m['line'] - 1][0]}
HAS_NARRATION = True
LEAD = 0.3
AD_GAP = 0.3


def build():
    on, end, stop = {}, {}, None
    t = LEAD
    for m in META:
        i = m['line']
        dur = m['dur'] if script.LINES[i - 1][0] else 0.0     # пустая реплика — пропущена
        on[i], end[i] = t, t + dur
        pause = script.LINES[i - 1][2]
        t += dur + pause
        if i == script.AD_AFTER:
            stop = end[i] + pause * 0.6
            t = stop + AD_GAP
    return on, end, stop, t + 0.3


ON, END, AD_STOP, DUR = build()
SCENE = {i: script.LINES[i - 1][1] for i in ON}
