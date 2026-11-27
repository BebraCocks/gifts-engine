"""Общие события «Холодильника» для картинки и звука (одни времена)."""
from timeline import T, V, D

# дверца холодильника: (открыть, закрыть)
DOOR = [(T['open1'], T['close1']), (T['open2'], T['s3'] - 0.02)]
DOOR += [(T['opens'][i], T['opens'][i + 1] - 0.02) for i in range(3)]
FREEZER = (T['freezer'], T['s4'] - 0.02)
COUNT = [(T['open2'], 2)] + [(t, 3 + i) for i, t in enumerate(T['opens'])]
SCAN = T['s1'] + 0.25                       # сканер-рамка на «Объект: Стас»
AWAY = (T['away'], T['away'] + 0.45)        # уходит вправо
BACK = (T['open2'] - 0.55, T['open2'] - 0.05)
STEPS = [AWAY[0] + k * 0.15 for k in range(3)] + [BACK[0] + k * 0.15 for k in range(3)]
NOTE = (T['note1'], V['M3'] + D['M3'])      # Мисед пишет в блокнот
CRICKETS = V['S4'] - 0.5                    # пауза перед «…Никто.»
TAP = T['phone']
CMP = V['M8']                               # «Пельмени варятся десять минут» — сравнение
STAMP = V['M9'] + 0.9                       # штамп «20 МИН У ХОЛОДИЛЬНИКА»
STOP = V['M9'] + D['M9'] + 0.05             # скрэтч, стоп музыки
TROMBONE = V['M11'] + D['M11'] + 0.05       # после «Нет.»
