"""Озвучка серии «Холодильник»: обрезка тишины, громкость. Мисед — мягко: без понижения тона, лёгкая «комната»
(решение автора, 2026-11-27: голос Миседа менее грубый). Стас — +1 полутон и +5 % темпа, чтобы отличался от Миседа.

    python -B prep_voice.py      (voice/raw_*.mp3 -> voice/*.wav)
"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = HERE / 'voice'
TRIM = ('silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,'
        'areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse')
MISSED = 'aecho=0.85:0.4:35|70:0.10|0.05,highshelf=f=6000:g=-2'
STAS = 'asetrate=48000*1.0595,aresample=48000,atempo=0.9911'     # +1 полутон, итоговый темп ≈ +5 %

for k in json.load(open(HERE / 'takes.json')):
    role = MISSED if k[0] in 'MI' else STAS
    af = f'aresample=48000,{TRIM},{role},loudnorm=I=-16:TP=-1.5:LRA=7'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(V / f'raw_{k}.mp3'), '-af', af,
                    '-ar', '48000', '-ac', '2', str(V / f'{k}.wav')], check=True)
print('OK')
