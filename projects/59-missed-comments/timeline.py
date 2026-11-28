"""Тайминг «Помоги выиграть NFT у Миседа»: от реальных длительностей озвучки (voice/L*.wav, с паузой 0,35 с в конце)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _dur(k):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                 str(HERE / 'voice' / f'{k}.wav')], capture_output=True, text=True).stdout)


D = {k: _dur(k) for k in ('L1', 'L2', 'L3', 'L4', 'L5')}
V, T = {}, {}
t = 0.15
for k in ('L1', 'L2', 'L3', 'L4', 'L5'):
    V[k] = t
    t += D[k]
DUR = t + 0.8
# фразы внутри реплик (по паузам в записи, silencedetect -32 dB)
T['help'] = V['L1'] + 1.44            # «Помоги мне выиграть — и я разыграю всё среди вас!»
T['tier'] = [V['L3'] + 0.0, V['L3'] + 1.95, V['L3'] + 4.12]   # 10К / 100К / 1 млн
T['sold'] = V['L4'] + 1.0             # «продам подарок»
T['rain'] = V['L4'] + 2.1             # «раздам кучу NFT»
T['top'] = V['L4'] + 4.19             # «А кто напишет больше всех…»
T['each'] = V['L5'] + 2.84            # «Каждый комментарий считается!»
SCENES = ['L1', 'L2', 'L3', 'L4', 'L5']


def scene_at(x):
    cur = 'L1'
    for k in SCENES:
        if x >= V[k]:
            cur = k
    return cur


if __name__ == '__main__':
    print({k: round(v, 2) for k, v in V.items()}, 'DUR', round(DUR, 2))
