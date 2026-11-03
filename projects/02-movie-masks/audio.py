"""Narration is optional; the complete advertisement sound is always present."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
import banner
import sound
from timeline import DUR, ON, HAS_NARRATION, TAKES
from events import AD_STOP

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)


def make_mix():
    mix = np.zeros((int(round(DUR * SR)), 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            start = round(ON[k] * SR)
            count = min(len(data), len(mix)-start)
            mix[start:start+count] += data[:count] * 0.85
    else:
        print('Дикторской озвучки нет. Добавите новый ключ Fish Audio и свой голос? Пока текст + звук баннера.')
    return BR.audio(mix, SR)


if __name__ == '__main__':
    data = make_mix()
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98)*32767).astype('<i2').tobytes())
    print('build/mix.wav готов')
