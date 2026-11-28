"""Тайминг второго ролика-призыва: от длительностей озвучки и меток слов (распознавание Fish pro с таймкодами)."""
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
DUR = t + 0.8
O = -0.06                                     # сдвиг: в wav обрезана тишина в начале
T['stop'] = V['L1']                           # «Стоп!»
T['give'] = V['L1'] + 0.62                    # «Мисед раздаёт NFT — и я заберу их для вас!»
T['forU'] = V['L1'] + 2.2                     # «…для вас»
T['rule'] = V['L2'] + 1.02 + O                # «кто первым наберёт больше всех комментариев»
T['win'] = V['L2'] + 4.24 + O                 # «тот и получает подарок»
T['tier'] = [V['L3'] + 1.68 + O, V['L3'] + 3.6 + O, V['L3'] + 6.32 + O]   # названия подарков
T['self0'] = V['L4'] + 0.08 + O               # «Себе я ничего не оставлю»
T['sell'] = V['L4'] + 1.92 + O                # «выигрыш продам»
T['buy'] = V['L4'] + 2.96 + O                 # «накуплю на все деньги NFT»
T['give2'] = V['L4'] + 4.56 + O               # «и раздам их вам в комментариях»
T['top'] = V['L4'] + 6.56 + O                 # «а самый активный получит особый подарок»
T['type'] = V['L5'] + 0.96 + O                # «напиши, какой подарок хочешь именно ты»
T['any'] = V['L5'] + 4.4 + O                  # «Засчитывается абсолютно любой комментарий»
T['dot'] = V['L5'] + 7.12 + O                 # «даже точка»
T['more'] = V['L5'] + 8.48 + O                # «Чем больше комментариев — тем больше раздача»
SCENES = ['L1', 'L2', 'L3', 'L4', 'L5']


def scene_at(x):
    cur = 'L1'
    for k in SCENES:
        if x >= V[k]:
            cur = k
    return cur


if __name__ == '__main__':
    print({k: round(v, 2) for k, v in V.items()}, 'DUR', round(DUR, 2))
