"""Озвучка «Ещё одно видео»: обрезка тишины, громкость. Мисед — мягко (как в 66). Артём (16) — +2 полутона, +6 % темпа.

    python -B prep_voice.py      (voice/raw_*.mp3 -> voice/*.wav)
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / 'voice'
TRIM = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,'
        'areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse')
GAP = 'silenceremove=stop_periods=-1:stop_duration=0.5:stop_threshold=-45dB:stop_silence=0.5'
MISSED = 'aecho=0.85:0.4:35|70:0.10|0.05,highshelf=f=6000:g=-2'
ARTEM = 'asetrate=48000*1.1225,aresample=48000,atempo=0.9443'     # +2 полутона, итоговый темп ≈ +6 %

for k in json.load(open(HERE / 'takes.json')):
    role = MISSED if k[0] in 'MIO' else ARTEM
    af = f'aresample=48000,{TRIM},{GAP},{role},loudnorm=I=-16:TP=-1.5:LRA=7'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(V / f'raw_{k}.mp3'), '-af', af,
                    '-ar', '48000', '-ac', '2', str(V / f'{k}.wav')], check=True)
print('OK')
