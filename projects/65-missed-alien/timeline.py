"""Тайминг серии 1 «Будильник»: всё от реальных длительностей озвучки (voice/*.wav).
Вырезаны ради лимита 59 с: «Наблюдаю.», «Ну ещё один, последний…», «Ого, часы!..» (их дубли в takes.json остаются)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE = HERE / 'voice'
USED = ('I1', 'D1', 'M1', 'D2', 'D3', 'M3', 'D4', 'M4', 'D5', 'D6', 'D7', 'M5', 'D9', 'M6',
        'M7', 'D10', 'M8', 'D11', 'M9', 'D12', 'M10')


def _dur(k):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                          str(VOICE / f'{k}.wav')], capture_output=True, text=True).stdout
    return float(out)


D = {k: _dur(k) for k in USED}
V, T = {}, {}
G = 0.14                      # обычная пауза между репликами


def say(k, t):
    V[k] = t
    return t + D[k]


# Заставка 3,5 с: НЛО влетает, луч, Мисед опускается, логотип
T['ufo_in'] = 0.0
T['beam'] = 1.2
T['land'] = 2.3
T['logo'] = 2.6
say('I1', 0.7)
T['intro_end'] = 3.5
# 1. Ночь: будильники на телефоне
T['s1'] = T['intro_end']
e = say('D1', T['s1'] + 0.1)
T['alarms_set'] = [T['s1'] + 0.35 + i * 0.42 for i in range(5)]
# 2. Глаза в темноте
T['s2'] = max(e, T['alarms_set'][-1]) + 0.15
T['eyes'] = T['s2']
e = say('M1', T['s2'] + 0.2)
T['jump'] = e + 0.05
e = say('D2', e + G)
T['blink'] = e + 0.15                      # вместо ответа Мисед просто моргает
# 3. Система
T['s3'] = T['blink'] + 0.45
e = say('D3', T['s3'])
T['roles'] = [V['D3'] + x for x in (0.0, 1.2, 2.4, 3.6)]
e = say('M3', e + G)
e = say('D4', e + G)
T['pause'] = e
e = say('M4', e + 0.55)                    # долгий взгляд и наезд
e = say('D5', e + 0.18)
# 4. Утро: пять звонков
T['s4'] = e + 0.3
T['ring'] = [T['s4'] + 0.1]
e = say('D6', T['ring'][0] + 0.55)
T['ring'].append(e + 0.1)                  # 2: подушка
T['pillow'] = T['ring'][1] + 0.55
T['ring'].append(T['ring'][1] + 1.05)      # 3: «Я уже встал…»
e = say('D7', T['ring'][2] + 0.4)
e = say('M5', e + G)
T['ring'].append(e + 0.1)                  # 4: молча торгуется с потолком
T['ring'].append(T['ring'][3] + 0.85)      # 5: выключает и засыпает
T['off'] = T['ring'][4] + 0.55
T['snore1'] = T['off'] + 0.15
# 5. 9:40
T['s5'] = T['off'] + 0.45
T['clock'] = T['s5']                       # часы прокручиваются 0,8 с
T['wake'] = T['s5'] + 0.8
e = say('D9', T['wake'] + 0.05)
e = say('M6', e + 0.2)
# 6. Беготня
T['s6'] = e + 0.2
e = say('M7', T['s6'] + 0.1)
e = say('D10', e + G)
e = say('M8', e + G)
e = say('D11', e + G)
e = say('M9', e + G)
# 7. Шестой будильник
T['s7'] = e + 0.25
e = say('D12', T['s7'] + 0.1)
T['alarm6'] = V['D12'] + 0.1
T['ears'] = e + 0.05
# 8. Подарок
T['s8'] = e + 0.3
e = say('M10', T['s8'] + 0.05)
T['gift'] = V['M10'] + 0.45
T['snore2'] = e + 0.15
T['title'] = e + 0.1
DUR = e + 0.7

CUTS = [T[k] for k in ('s1', 's3', 's4', 's5', 's6', 's7', 's8')]

if __name__ == '__main__':
    for k, t in sorted(V.items(), key=lambda x: x[1]):
        print(f'{t:6.2f}–{t + D[k]:6.2f}  {k}')
    print('DUR', round(DUR, 2))
