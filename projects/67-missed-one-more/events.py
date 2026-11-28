"""Общие события «Ещё одно видео» для картинки и звука."""
from timeline import T, V, D

SCAN = T['s1'] + 0.25
# свайпы ленты: во время A1, в прокрутке часов, в монтаже
SWIPES = [V['A1'] + 0.3, V['A1'] + 1.4] + [T['spin1'][0] + k * 0.18 for k in range(5)] + [c + 0.2 for c in T['cuts'][:2]]
SPIN = T['spin1']                          # 23:00 → 23:47
CLOCKS = [('23:00', T['s1']), ('23:47', T['spin1'][1]), ('00:30', T['cuts'][0]), ('01:15', T['cuts'][1]), ('02:40', T['cuts'][2])]
COUNT = [(T['s1'] + 0.2, 1), (T['spin1'][0] + 0.2, 23), (T['cuts'][0], 58), (T['cuts'][1], 112), (T['cuts'][2], 147)]
NOTE = (T['note'], V['M4'] + D['M4'])
LAUGH = T['cuts'][0] + 0.1
DROP = T['drop']
LEAN = (T['lean'], T['s5'] - 0.1)
