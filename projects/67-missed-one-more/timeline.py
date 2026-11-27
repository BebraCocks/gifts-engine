"""Тайминг «Ещё одно видео» от реальных длительностей озвучки (voice/*.wav). Лимит автора — 59 с."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = list(json.load(open(HERE / 'takes.json')))


def _dur(k):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                          str(HERE / 'voice' / f'{k}.wav')], capture_output=True, text=True).stdout
    return float(out)


D = {k: _dur(k) for k in KEYS}
V, T = {}, {}
G = 0.17


def say(k, t):
    V[k] = t
    return t + D[k]


# Заставка 3,5 с
T['ufo_in'], T['beam'], T['land'], T['logo'], T['intro_end'] = 0.0, 1.2, 2.3, 2.6, 3.5
say('I1', 0.85)
# 1. Спальня, 23:00
T['s1'] = 3.5
e = say('M1', T['s1'] + 0.1)              # сканер «ОБЪЕКТ: АРТЁМ, 16»
e = say('A1', e + G)
# 2. Часы 23:00 → 23:47, свайпы
T['s2'] = e + 0.2
T['spin1'] = (T['s2'], T['s2'] + 0.9)
e = say('M2', T['s2'] + 0.95)
e = say('A2', e + G)
e = say('M3', e + G)
e = say('A3', e + G)
T['note'] = e + 0.05
e = say('M4', e + G)                      # «Записываю: короткое видео длится вечно»
# 3. Монтаж: 00:30 смеётся, 01:15 глаза слипаются, 02:40 телефон падает на лицо
T['s3'] = e + 0.25
T['cuts'] = [T['s3'], T['s3'] + 0.75, T['s3'] + 1.5]
T['drop'] = T['cuts'][2] + 0.45           # бум — телефон на лицо
e = say('A4', T['drop'] + 0.1)
e = say('M5', e + G)
# 4. «А вдруг там что-то важное?»
T['s4'] = e + 0.2
e = say('A5', T['s4'])
e = say('M6', e + G)
e = say('A6', e + 0.35)
T['lean'] = e + 0.1                       # Мисед наклоняется к экрану
e = say('M7', e + 0.45)
# 5. Подарок
T['s5'] = e + 0.35
e = say('M8', T['s5'] + 0.05)
T['gift'] = V['M8'] + 0.5
e = say('A7', e + G)
# 6. Концовка-тизер с закольцовкой
T['s6'] = e + 0.2
T['lift'] = T['s6'] + 0.1
e = say('O1', T['s6'] + 0.35)
T['card'] = V['O1'] + 1.4
T['ufo_out'] = e + 0.1
DUR = T['ufo_out'] + 0.75

if __name__ == '__main__':
    for k, t in sorted(V.items(), key=lambda x: x[1]):
        print(f'{t:6.2f}–{t + D[k]:6.2f}  {k}')
    print('DUR', round(DUR, 2))
