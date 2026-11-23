"""Тайминг «Подарка по заслугам»: всё считается от реальных длительностей озвучки (voice/*.wav)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE = HERE / 'voice'


def _dur(k):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                          str(VOICE / f'{k}.wav')], capture_output=True, text=True).stdout
    return float(out)


D = {k: _dur(k) for k in ('N1', 'N2', 'N4', 'D1', 'D2', 'D3', 'D4', 'D5', 'O1', 'O2', 'O3', 'O4', 'O5', 'N3', 'M1', 'M2', 'M3', 'M4', 'M5')}
V = {}        # реплика -> время начала
T = {}        # именованные моменты


def say(k, t):
    V[k] = t
    return t + D[k]


# 1. Хук: пустой профиль
T['s1'] = 0.0
e = say('N1', 0.3)
# 2. Годы без подарков
T['s2'] = e + 0.25
e = say('N2', T['s2'] + 0.15)
# 3. Лента
T['s3'] = e + 0.25
e = say('D1', T['s3'] + 0.3)
# 4. Чат Димона
T['s4'] = e + 0.3
T['dm1'] = T['s4'] + 0.15
e = say('D2', T['dm1'])
T['dty1'] = e + 0.15
T['dmm1'] = T['dty1'] + 0.7
e = say('M1', T['dmm1'] + 0.1)          # сообщения Миседа тоже озвучены (автор, 2026-11-23)
T['dm2'] = e + 0.25
e = say('D3', T['dm2'])
T['dty2'] = e + 0.1
T['dmm2'] = T['dty2'] + 0.7
e = say('M2', T['dmm2'] + 0.1)
# 5. Подарок
T['s5'] = e + 0.45
e = say('D4', T['s5'] + 1.4)
# 6. Звонок
T['s6'] = e + 0.6
e = say('D5', T['s6'] + 0.2)
e = say('O1', e + 0.2)
# 6b. Олег — скамер (добавлено по просьбе автора, 2026-11-23)
T['s6b'] = e + 0.35
T['sc_msg'] = T['s6b'] + 0.2        # Олег: «Скинь подарок — я его улучшу»
T['sc_reply'] = T['s6b'] + 1.0      # жертва: «Отправила!»
T['sc_fly'] = T['s6b'] + 1.5        # подарок улетает к Олегу
T['sc_stamp'] = T['s6b'] + 2.4      # штамп «СКАМЕР»
e = say('N4', T['s6b'] + 0.35)
# 7. Чат Олега
T['s7'] = max(e, T['sc_stamp'] + 1.0) + 0.35
T['om1'] = T['s7'] + 0.15
e = say('O2', T['om1'])
T['oty1'] = e + 0.15
T['omm1'] = T['oty1'] + 0.7
e = say('M3', T['omm1'] + 0.1)
T['om2'] = e + 0.25
e = say('O3', T['om2'])
T['oty2'] = e + 0.15
T['omm2'] = T['oty2'] + 1.0          # «Ты уверен?» — музыка обрывается
e = say('M4', T['omm2'] + 0.1)
T['om3'] = e + 0.6
e = say('O4', T['om3'])
T['oty3'] = e + 0.15
T['omm3'] = T['oty3'] + 1.2          # «ненавижу скамеров…»
e = say('M5', T['omm3'] + 0.1)
# 8. Подарки Олега исчезают
T['s8'] = e + 0.7
e = say('O5', T['s8'] + 1.9)
# 9. Финал
T['s9'] = e + 0.35
e = say('N3', T['s9'] + 0.35)
DUR = e + 0.9

SCENES = ['s1', 's2', 's3', 's4', 's5', 's6', 's6b', 's7', 's8', 's9']


def scene_at(t):
    cur = 's1'
    for s in SCENES:
        if t >= T[s]:
            cur = s
    return cur


if __name__ == '__main__':
    for k, v in sorted({**T, **{'V:' + a: b for a, b in V.items()}}.items(), key=lambda kv: kv[1]):
        print(f'{v:6.2f}  {k}')
    print('DUR', round(DUR, 2))
