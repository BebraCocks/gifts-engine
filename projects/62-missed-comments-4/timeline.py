"""Тайминг четвёртого ролика-призыва: от длительностей озвучки и пауз в ней (silencedetect −32 dB)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _dur(k):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                 str(HERE / 'voice' / f'{k}.wav')], capture_output=True, text=True).stdout)


D = {k: _dur(k) for k in ('L1', 'L2', 'L3', 'L4', 'L5')}
V, T = {}, {}
t = 0.1
for k in ('L1', 'L2', 'L3', 'L4', 'L5'):
    V[k] = t
    t += D[k]
DUR = t + 0.9
T['explain'] = V['L1'] + 3.22       # «Объясняю!»
T['quest'] = V['L2'] + 1.23         # «кто соберёт больше всех комментариев…»
T['sell'] = V['L2'] + 4.74          # «Всё, что выиграю, продаю»
T['gifts'] = V['L2'] + 6.16         # «а деньги превращаю в подарки для вас»
T['zero'] = V['L2'] + 8.67          # «Себе — ни копейки!»
T['tier'] = [V['L3'] + 1.9, V['L3'] + 3.75, V['L3'] + 5.6]   # названия подарков
T['letter'] = V['L4'] + 1.6         # «буква»
T['emoji'] = V['L4'] + 2.2          # «эмодзи»
T['dot'] = V['L4'] + 2.9            # «даже точка»
T['top'] = V['L4'] + 3.8            # «А тот, кто напишет больше всех…»
T['go'] = V['L5'] + 1.9             # «давай, первый пошёл!»
SCENES = ['L1', 'L2', 'L3', 'L4', 'L5']


def scene_at(x):
    cur = 'L1'
    for k in SCENES:
        if x >= V[k]:
            cur = k
    return cur


if __name__ == '__main__':
    print({k: round(v, 2) for k, v in V.items()}, 'DUR', round(DUR, 2))
