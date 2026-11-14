"""Дубли Fish (takes.json) -> voice/LNN.wav (48 кГц моно) + voice/lines.json (длительность и паузы внутри реплики).

Обрезка тишины по краям, длинные паузы внутри реплики сокращаются до MAX_GAP. Темп по персонажу (TEMPO,
rubberband без смены тона) — чтобы ролик уложился в 120–140 с вместе с двумя RubUp.
Обработка: монстр — ниже на ~4 полутона + октавный слой, хрип, реверберация; голоса за дверью (мама,
полиция) — приглушены дверью; во второй реплике «мамы» под голосом проступает низкий слой монстра."""
import json
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import script

SR = 48000
RAW = HERE / 'voice' / 'raw'
OUT = HERE / 'voice'
TEMPO = {'N': 1.26, 'K': 1.12, 'M': 1.0, 'X': 0.96, 'P': 1.0}
MAX_GAP = 0.32
GAP_LINE = {11: 0.75, 15: 0.55, 16: 0.45, 22: 0.45, 24: 0.4}     # драматические паузы внутри реплики


def ff(src, af=None, out=None):
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(src)]
    if af:
        cmd += ['-af', af]
    cmd += ['-ac', '1', '-ar', str(SR), '-f', 's16le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, '<i2').astype(np.float64) / 32768


def proc(x, af):
    a = OUT / '_tmp.wav'
    write(a, x)
    y = ff(a, af)
    a.unlink()
    return y


def write(path, x):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


def tighten(x, max_gap):
    hop = SR // 100
    e = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(e + 1e-9)
    loud = db > db.max() - 34
    on = np.nonzero(loud)[0]
    a, b = on[0], on[-1] + 1
    keep = np.zeros(len(e), bool)
    keep[max(0, a - 3):min(len(e), b + 10)] = True
    k = a
    mg = int(max_gap * 100)
    while k < b:
        if not loud[k]:
            j = k
            while j < b and not loud[j]:
                j += 1
            if j - k > mg:
                keep[k + mg // 2:j - (mg - mg // 2)] = False
            k = j
        else:
            k += 1
    out = np.concatenate([x[i * hop:(i + 1) * hop] for i in np.nonzero(keep)[0]])
    return out


def gaps(x, min_gap=0.18):
    """Середины пауз внутри реплики (с) — места для звуков между фразами."""
    hop = SR // 100
    e = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(e + 1e-9)
    loud = db > db.max() - 34
    on = np.nonzero(loud)[0]
    res, k = [], on[0]
    while k < on[-1]:
        if not loud[k]:
            j = k
            while j < on[-1] and not loud[j]:
                j += 1
            if (j - k) / 100 >= min_gap:
                res.append(round((k + j) / 200, 3))
            k = j
        else:
            k += 1
    return res


def monster(x):
    lo = proc(x, 'rubberband=pitch=0.78:formant=preserved')
    sub = proc(x, 'rubberband=pitch=0.5')
    n = min(len(lo), len(sub))
    y = lo[:n] + 0.35 * sub[:n]
    y = np.tanh(2.2 * y) / np.tanh(2.2)                       # хрип
    y = proc(y, 'aecho=0.8:0.7:60|130|260:0.35|0.25|0.15,lowpass=f=5200,highpass=f=60')
    return y / (np.abs(y).max() + 1e-9) * 0.85


def behind_door(x, fc=2400, room=True):
    af = f'lowpass=f={fc},lowpass=f={fc + 800},highpass=f=120'
    if room:
        af += ',aecho=0.8:0.5:25|55:0.25|0.12'
    return proc(x, af)


def fake_mom(x):
    """«Мама» за дверью, но под голосом проступает монстр — сильнее к концу фразы."""
    door = behind_door(x)
    sub = behind_door(proc(x, 'rubberband=pitch=0.5'), fc=1600, room=False)
    n = min(len(door), len(sub))
    ramp = np.linspace(0.0, 1.0, n) ** 2
    return door[:n] + 0.28 * ramp * sub[:n]


def main():
    takes = json.loads((HERE / 'takes.json').read_text(encoding='utf-8'))
    meta = []
    for i, (who, text, pause) in enumerate(script.LINES, 1):
        task = takes[f'L{i:02d}'][0]
        x = ff(RAW / f'{task}.mp3')
        x = tighten(x, GAP_LINE.get(i, MAX_GAP))
        t = TEMPO[who]
        if t != 1.0:
            x = proc(x, f'rubberband=tempo={t}')
        if who == 'X':
            x = monster(x)
        elif who == 'M':
            x = fake_mom(x) if i == 12 else behind_door(x)
        elif who == 'P':
            x = behind_door(x, fc=3000)
        x = x / (np.sqrt(np.mean(x[np.abs(x) > 0.02] ** 2)) + 1e-9) * 0.16      # выровнять громкость реплик
        x = np.clip(x, -0.95, 0.95)
        write(OUT / f'L{i:02d}.wav', x)
        meta.append(dict(line=i, who=who, dur=round(len(x) / SR, 3), gaps=gaps(x), pause=pause))
        print(f'L{i:02d} {who} {len(x) / SR:6.2f} s  gaps {gaps(x)}')
    (OUT / 'lines.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print('речь всего', round(sum(m['dur'] for m in meta), 1), 'с')


if __name__ == '__main__':
    main()
