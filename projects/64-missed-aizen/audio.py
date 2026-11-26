"""Звук выпуска 1: голос (voice_timeline.py) + музыка автора (music.py) + SFX Botanica V4 через sfxkit.

    python -B audio.py
-> build/mix.wav, build/review/{voice_only,sfx_only,mix}.mp3, build/review/sfx_cues.txt
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import sfxkit  # noqa: E402

SR = 48000
WITH_MUSIC = False  # автор, 2026-11-26: TikTok не даёт выложить с треком «Блича» — музыку убрали полностью
CUES = json.loads((HERE / 'voice_cues.json').read_text())
DUR = CUES['total']
C = {c['id']: (c['start'], c['end']) for c in CUES['cues']}
N = int(round(DUR * SR))
REV = HERE / 'build' / 'review'


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2)[:N]
    return np.pad(a, ((0, N - len(a)), (0, 0)))


def write(path, a):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(path)],
                   input=np.clip(a, -1, 1).astype(np.float32).tobytes(), check=True)


def main():
    subprocess.run([sys.executable, '-B', 'voice_timeline.py'], cwd=HERE, check=True)
    subprocess.run([sys.executable, '-B', 'music.py'], cwd=HERE, check=True)
    import render  # те же времена сцен, что и в кадре
    S = render.START
    voice = load(REV / 'voice_only.mp3')
    music = load(REV / 'music_only.wav') * (1.0 if WITH_MUSIC else 0.0)
    fx = np.zeros((N, 2), np.float32)
    kit = sfxkit.Kit(HERE)
    a = lambda *x, **k: kit.add(fx, *x, **k)  # noqa: E731

    # 1. хук
    a('impact', 0.12, gain_db=-12, align='peak', label='хук: титр')
    a('pop', 0.15, gain_db=-14, label='фото Миседа на доске')
    a('paper', 3.4, gain_db=-18, fit=1.0, label='мел: способ 1')
    # 2. лестница мелом
    a('paper', S['ladder'], gain_db=-18, fit=0.9, label='мел: заголовок')
    a('paper', S['ladder'] + 0.6, gain_db=-20, fit=0.6, label='мел: перила')
    for i, d in enumerate((0.9, 1.4, 1.9)):
        a('select-soft', C['A2'][0] + d, gain_db=-14, label=f'ступенька {i + 1}')
    a('pop', C['A2'][0] + 3.2, gain_db=-16, label='вопрос на доске')
    # 3. чат
    a('whoosh-short', S['chat'], gain_db=-12, align='peak', label='переход в чат')
    for cid in render.CHAT_IDS[:-1]:
        if cid.startswith('A'):
            a('select', C[cid][0], gain_db=-16, label=f'{cid}: отправка')
        else:
            a('popup', C[cid][0], gain_db=-12, key='missed_msg', label=f'{cid}: Мисед')
    a('popup', C['M4'][0], gain_db=-11, key='missed_msg', label='«Нет»')
    a('impact', C['M4'][0] + 0.02, gain_db=-9, align='peak', label='«Нет»: удар')
    a('sub-drop', C['M4'][0] + 0.02, gain_db=-14, label='«Нет»: саб')
    # 4. обвал лестницы, очки
    a('foley', S['collapse'], gain_db=-13, file='demolition', label='лестница рушится')
    a('cartoon-move', S['collapse'] + 0.1, gain_db=-20, label='обломки падают')
    a('sparkle', S['glasses'] + 0.2, gain_db=-14, fit=1.2, label='блик очков')
    a('whoosh-short', S['calm'], gain_db=-18, align='peak', label='переход')
    # 5. Мисед
    a('whoosh-short', S['missed5'], gain_db=-13, align='peak', label='наезд на Миседа')
    # 6. меч
    hit = C['A8'][0] + 0.75
    a('riser', hit, gain_db=-18, align='end', label='меч: нарастание')
    a('whoosh-deep', hit, gain_db=-10, align='peak', label='меч: взмах')
    a('impact', hit, gain_db=-10, align='peak', label='меч: давление')
    a('click', C['A8'][1] + 0.15, gain_db=-12, label='меч в ножнах')
    # 7. подарок
    a('whoosh-short', S['missed6'], gain_db=-14, align='peak', label='Мисед')
    g = C['M6'][1] - 1.1
    a('sparkle-whoosh', g, gain_db=-12, align='peak', label='подарок появляется')
    a('coin', g + 0.1, gain_db=-14, label='подарок')
    a('popup', S['palm'] + 0.3, gain_db=-12, key='missed_msg', label='уведомление о подарке')
    a('sparkle', S['palm'] + 0.2, gain_db=-16, fit=1.5, label='шар опускается')
    # 8. окно и финал
    a('whoosh-organic', S['window'], gain_db=-16, align='peak', fit=2.0, label='окно')
    a('whoosh-short', S['final'], gain_db=-13, align='peak', label='наезд на Миседа')
    end = C['M7'][1] + 0.05
    a('riser', end, gain_db=-18, align='end', label='к титру')
    a('impact', end, gain_db=-10, align='peak', label='финальный титр')
    kit.save()

    mix = voice + music + fx
    peak = np.abs(mix).max()
    if peak > 0.97:
        mix *= 0.97 / peak
    write(HERE / 'build' / 'mix.wav', mix)
    write(REV / 'sfx_only.mp3', fx)
    write(REV / 'mix.mp3', mix)
    lines = [f"{c['at']:7.2f}  {c['role']:<16} {c.get('label') or ''}  ({c['id']})" for c in kit.cues]
    (REV / 'sfx_cues.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('audio OK', HERE / 'build' / 'mix.wav', f'{DUR:.2f} s, peak {peak:.2f}')


if __name__ == '__main__':
    main()
