"""Нарезка дублей (паузы внутри реплики длиннее 0,32 с сжимаются) в voice/Lxx_ID.wav: обрезка, скорость (atempo, без смены тона), громкость −16 LUFS, мягкие края."""
import subprocess, json, re
from pathlib import Path
from script import SEQ
HERE = Path(__file__).resolve().parent
OUT = HERE / 'voice'; OUT.mkdir(exist_ok=True)
def lufs(p):
    r = subprocess.run(['ffmpeg', '-i', str(p), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
k = 0
for cid, src, a, b, pause, text, speed, *extra in SEQ:
    if not src:
        continue
    k += 1
    p = HERE / (src + '.mp3')
    g = -16 - lufs(p) + (extra[0] if extra else 0.0)   # смех тише речи (автор, 2026-11-13)
    d = (b - a) / speed
    speech = speed != 1                 # смех и чужие звуки не ускоряем и не сжимаем
    af = (f'atrim={a}:{b},asetpts=N/SR/TB,aformat=sample_rates=48000:channel_layouts=stereo,'
          + ('silenceremove=stop_periods=-1:stop_duration=0.32:stop_threshold=-40dB:detection=rms,' if speech else '')
          + (f'atempo={speed},' if speech else '')
          + f'volume={g:.1f}dB,afade=t=in:d=0.02'
          + ('' if speech else f',afade=t=out:st={max(d - 0.25, 0):.3f}:d=0.25'))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(p), '-af', af, str(OUT / f'L{k:02d}_{cid}.wav')], check=True)
print(k, 'дублей в', OUT)
