"""Тайминг третьего ролика-призыва: от длительностей озвучки и пауз в ней (silencedetect −32 dB)."""
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
T['boom'] = V['L1'] + 1.41          # «— и NFT может стать твоим!»: точка взрывается
T['self0'] = V['L2'] + 3.32         # «А я себе ничего не оставлю»
T['sell'] = V['L2'] + 5.23          # «всё, что выиграю, продам»
T['give'] = V['L2'] + 6.73          # «и разыграю среди вас!»
T['tier'] = [V['L3'] + 1.7, V['L3'] + 3.95, V['L3'] + 6.4]   # названия подарков
T['word'] = V['L4'] + 1.0           # «слово»
T['smile'] = V['L4'] + 1.5          # «смайлик»
T['dot'] = V['L4'] + 2.1            # «даже одну точку»
T['ok'] = V['L4'] + 3.0             # «засчитывается всё!»
T['top'] = V['L4'] + 4.1            # «А кто накидает больше всех…»
T['write'] = V['L5'] + 2.35         # «и пиши прямо сейчас»
T['fast'] = V['L5'] + 3.51          # «чем быстрее наберём — тем быстрее раздача»
SCENES = ['L1', 'L2', 'L3', 'L4', 'L5']


def scene_at(x):
    cur = 'L1'
    for k in SCENES:
        if x >= V[k]:
            cur = k
    return cur


if __name__ == '__main__':
    print({k: round(v, 2) for k, v in V.items()}, 'DUR', round(DUR, 2))
