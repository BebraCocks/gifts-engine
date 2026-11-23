"""Общие события картинки и звука (одни и те же времена в render.py и audio.py)."""
from timeline import T, V, SCENES

YEARS = [T['s2'] + 0.05, T['s2'] + 1.95, T['s2'] + 3.85]          # «2023», «2024», «2025»
MSG_POP = [T[k] for k in ('dm1', 'dmm1', 'dm2', 'dmm2', 'om1', 'omm1', 'om2', 'omm2', 'om3', 'omm3')]
TYPING = [(T['dty1'], T['dmm1']), (T['dty2'], T['dmm2']), (T['oty1'], T['omm1']),
          (T['oty2'], T['omm2']), (T['oty3'], T['omm3'])]
CUTS = [T[s] for s in SCENES[1:]]
VANISH = [T['s8'] + 0.45 + i * 0.3 for i in range(6)]

SENT = [T[k] for k in ('dm1', 'dm2', 'om1', 'om2', 'om3')]               # свои сообщения: отправка
INCOMING = [T[k] for k in ('dmm1', 'dmm2', 'omm1', 'omm2', 'omm3')]     # сообщения Миседа: уведомление
SWIPE = V['D1'] - 0.1                                                    # лента: свайп к ролику Миседа
JUMPS = [V['D4'] - 0.4 + 0.29 + k * 0.571 for k in range(4)]            # приземления прыжков Димона
