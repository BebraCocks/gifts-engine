"""Подготовка озвучки: обрезка тишины, громкость, Мисед −2 полутона + лёгкое эхо, Димон +6 %.

    python -B prep_voice.py      (voice/raw_*.mp3 -> voice/*.wav)
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / 'voice'
TRIM = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,'
        'areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse')
MISSED = 'asetrate=48000*0.8909,aresample=48000,atempo=1.0,aecho=0.8:0.5:60|120:0.18|0.09'   # −2 полутона
DIMON = 'atempo=1.06'

for k in json.load(open(HERE / 'takes.json')):
    role = MISSED if k[0] in 'MI' else DIMON
    if k[0] in 'MI':
        role = role.replace('atempo=1.0', 'atempo=1.1225')     # вернуть темп после понижения тона
    af = f'aresample=48000,{TRIM},{role},loudnorm=I=-16:TP=-1.5:LRA=7'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(V / f'raw_{k}.mp3'), '-af', af,
                    '-ar', '48000', '-ac', '2', str(V / f'{k}.wav')], check=True)
print('OK')
