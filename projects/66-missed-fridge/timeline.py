"""Тайминг серии «Холодильник» от реальных длительностей озвучки (voice/*.wav). Лимит автора — 59 с."""
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


# Заставка 3,5 с (общая для сериала)
T['ufo_in'], T['beam'], T['land'], T['logo'], T['intro_end'] = 0.0, 1.2, 2.3, 2.6, 3.5
say('I1', 0.85)
# 1. Кухня, первое открытие
T['s1'] = 3.5
e = say('M1', T['s1'] + 0.1)              # «Объект: Стас…» — плашка объекта
T['open1'] = T['s1'] + 1.6                # дверца открывается, свет на лице
e = say('S1', max(e, T['open1'] + 0.6) + G)
e = say('M2', e + G)
e = say('S2', e + G)
T['note1'] = e + 0.1                      # Мисед пишет в блокнот
e = say('M3', e + G)
T['close1'] = e + 0.05
# 2. Второе открытие
T['s2'] = e + 0.25
T['away'] = T['s2']                       # уходит
T['open2'] = T['s2'] + 1.0                # возвращается и открывает
e = say('M4', T['open2'] + 0.35)
e = say('S3', e + G)
e = say('M5', e + G)
e = say('S4', e + 0.45)                   # пауза перед «…Никто.»
# 3. Монтаж открытий 3–6, на шестом — морозилка
T['s3'] = e + 0.3
T['opens'] = [T['s3'] + 0.1 + i * 0.6 for i in range(4)]   # 3, 4, 5, 6
T['freezer'] = T['opens'][-1]
e = say('S5', T['freezer'] + 0.4)
e = say('M6', e + G)
# 4. Доставка
T['s4'] = e + 0.25
e = say('S6', T['s4'] + 0.05)
T['phone'] = V['S6'] + 1.2
e = say('M7', e + G)
e = say('S7', e + G)
e = say('M8', e + G)
e = say('S8', e + 0.35)
e = say('M9', e + G)
# 5. Подарок
T['s5'] = e + 0.3
e = say('M10', T['s5'] + 0.05)
T['gift'] = V['M10'] + 0.5
e = say('S9', e + G)
e = say('M11', e + 0.2)
# 6. Концовка (своя у каждой серии): Мисед сам открывает холодильник — «ОТКРЫТИЙ: 7» — «…Есть нечего.»
T['s6'] = e + 0.15
T['open7'] = T['s6'] + 0.7
e = say('M12', T['open7'] + 0.35)
T['close7'] = e + 0.15
DUR = T['close7'] + 0.5

CUTS = [T[k] for k in ('s1', 's2', 's3', 's4', 's5', 's6')]

if __name__ == '__main__':
    for k, t in sorted(V.items(), key=lambda x: x[1]):
        print(f'{t:6.2f}–{t + D[k]:6.2f}  {k}')
    print('DUR', round(DUR, 2))
