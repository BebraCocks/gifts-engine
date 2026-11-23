"""Таймлайн 55 (рекламы-баннера нет: логотип RubUp на одежде Миты). ON/END — начало и конец реплик (1-based)."""
import json
from pathlib import Path
import script

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / 'voice' / 'lines.json').read_text(encoding='utf-8'))
TAKES = {m['line']: HERE / 'voice' / f"L{m['line']:02d}.wav" for m in META}
LEAD = 0.05
EXTRA = {4: 0.55, 7: 0.25, 11: 0.35}      # паузы под переходы между нарядами (после 4, 7, 11)


def build():
    on, end, t = {}, {}, LEAD
    for m in META:
        i = m['line']
        on[i], end[i] = t, t + m['dur']
        t += m['dur'] + script.LINES[i - 1][2] + EXTRA.get(i, 0.0)
    return on, end, t + 0.4


ON, END, DUR = build()
