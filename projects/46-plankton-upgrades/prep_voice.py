"""Нарезка дублей в voice/Lxx_ID.wav: обрезка, скорость (atempo, без смены тона), громкость −16 LUFS, мягкие края."""
import subprocess, json, re
from pathlib import Path
from script import SEQ
HERE = Path(__file__).resolve().parent
OUT = HERE / 'voice'; OUT.mkdir(exist_ok=True)
def lufs(p):
    r = subprocess.run(['ffmpeg', '-i', str(p), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
k = 0
for cid, src, a, b, pause, text, speed in SEQ:
    if not src:
        continue
    k += 1
    p = HERE / (src + '.mp3')
    g = -16 - lufs(p)
    d = (b - a) / speed
    af = (f'atrim={a}:{b},asetpts=N/SR/TB,aformat=sample_rates=48000:channel_layouts=stereo,'
          + (f'atempo={speed},' if speed != 1 else '')
          + f'volume={g:.1f}dB,afade=t=in:d=0.02,afade=t=out:st={max(d - (0.25 if speed == 1 else 0.04), 0):.3f}:d={0.25 if speed == 1 else 0.04}')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(p), '-af', af, str(OUT / f'L{k:02d}_{cid}.wav')], check=True)
print(k, 'дублей в', OUT)
