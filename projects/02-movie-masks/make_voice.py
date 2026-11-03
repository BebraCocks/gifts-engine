"""Реплики Fish Audio под фиксированные окна блоков. Ключ — только из FISH_API_KEY процесса,
голос — FISH_VOICE. Дубли не перезаписываются: voice/V01_s100.wav …; выбранный → voice/V01.wav."""
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine' / 'tools'))
import os
import paths
HERE = paths.enter(__file__)
import fish_tts
import voice
import hashlib
from script import SEGMENTS, VOICE, VOICE_WIN

ROLE_SLACK = 0.06          # слово-роль может чуть заходить за смену маски


def speech_len(path):
    a, b = voice.onset_end(path)
    return b - a


def main():
    vid = os.environ.get('FISH_VOICE')
    if not fish_tts.available() or not vid:
        raise SystemExit('Нужны FISH_API_KEY и FISH_VOICE в окружении процесса')
    folder = HERE / 'voice'; folder.mkdir(exist_ok=True)
    only = {int(x) for x in sys.argv[1:]} if len(sys.argv) > 1 else None
    for k, (text, (a, b)) in enumerate(zip(VOICE, VOICE_WIN), 1):
        if only and k not in only:
            continue
        window = b - a
        model = os.environ.get('FISH_TTS_MODEL', 's2.1-pro')
        tag = model.replace('.', '') + '_' + hashlib.sha1((model + vid + text).encode()).hexdigest()[:6]
        if not text:
            continue
        chosen = None
        for speed in (1.0, 1.05):
            take = folder / f'V{k:02d}_{tag}_s{int(round(speed * 100))}.wav'
            if not take.exists():
                fish_tts.tts(text, take, vid, speed=speed)
            d = speech_len(take)
            print(f'V{k:02d} speed {speed:.2f}: {d:.2f} c (окно {window:.2f})' + ('' if d <= window else '  НЕ ВЛЕЗАЕТ'), flush=True)
            chosen = take
            if d <= window:
                break
        shutil.copyfile(chosen, folder / f'V{k:02d}.wav')


if __name__ == '__main__':
    main()
