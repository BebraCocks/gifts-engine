"""Таймлайн содержания (до вставок рекламы): общий для audio.py и render.py.
ON/END — начало и конец реплик (с), STOPS — где ролик встаёт на RubUp, DUR — длительность содержания."""
import json
from pathlib import Path
import script

HERE = Path(__file__).resolve().parent
META = json.loads((HERE / 'voice' / 'lines.json').read_text(encoding='utf-8'))
LEAD = 0.15
# пауза после реплики (с): место для звуков действия; RubUp — после реплик script.AD_AFTER
PAUSE = {1: 0.2, 2: 0.2, 3: 0.2, 4: 0.6, 5: 0.25, 6: 0.1, 7: 0.05, 8: 0.1, 9: 0.3, 10: 0.2, 11: 0.25,
         12: 0.2, 13: 0.2, 14: 0.6, 15: 0.15, 16: 0.15, 17: 0.1, 18: 0.1, 19: 0.2, 20: 0.3, 21: 0.5, 22: 0.1,
         23: 1.3, 24: 0.55, 25: 0.1, 26: 0.25, 27: 0.6, 28: 0.3, 29: 0.5}
AD_GAP = 0.25          # после остановки на рекламу речь продолжается через столько секунд


def timeline():
    on, stops = {}, []
    t = LEAD
    for m in META:
        i = m['line']
        on[i] = t
        t += m['dur'] + PAUSE[i]
        if i in script.AD_AFTER:
            stop = t - PAUSE[i] / 2
            stops.append(round(stop, 3))
            t = stop + AD_GAP + 0.05
    return on, stops, t


ON, STOPS, DUR = timeline()
END = {m['line']: ON[m['line']] + m['dur'] for m in META}
GAPS = {m['line']: m['gaps'] for m in META}
WHO = {m['line']: m['who'] for m in META}
