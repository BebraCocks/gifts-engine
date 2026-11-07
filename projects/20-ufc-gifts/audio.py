"""Narration is optional; the complete advertisement sound is always present.
SFX come from the default library input/sfx/ through engine/sfxkit.py (different variants every time).
Writes build/mix.wav and, for the author to listen to, build/review/{sfx_only,mix}.mp3 + sfx_cues.txt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
import banner
import sound
import sfxkit
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES
from events import AD_STOP, E

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
SFX_GAIN_DB = 0.0          # whole SFX layer; individual cues set their own gain_db
CONTENT_GAIN_DB = 3.0      # voice + SFX up to ≈ −14 LUFS like the previous videos (the RubUp sound is not touched)


def sfx_layer(n, kit):
    """One cue = one action on screen (STORYBOARD.md, «Звук»). No own SFX during RubUp (docs/ADVERTISING.md)."""
    fx = np.zeros((n, 2))
    add = kit.add
    for j in range(0, 10, 2):
        add(fx, 'pop', 0.02 + 0.1 * j, gain_db=-19, pan=((j % 5) - 2) * 0.2, label=f'fighters {j + 1}–{j + 2} (hook)')
    add(fx, 'impact', E['four_h'] - 0.05, gain_db=-15, label='«РАСКУПИЛИ ЗА 4 ЧАСА»')
    add(fx, 'whoosh-short', E['link'], gain_db=-19, label='hook out, share sheet in')
    add(fx, 'click', E['copy'] + 0.25, gain_db=-13, label='«Копировать ссылку» tapped')
    add(fx, 'confirm', E['copy'] + 0.55, gain_db=-17, label='toast «Ссылка скопирована»')
    add(fx, 'whoosh-short', E['khabib'], gain_db=-18, label='papakha in')
    add(fx, 'counter', E['k29'] - 0.05, gain_db=-21, fit=1.0, label='counter to 29 000')
    add(fx, 'coin', E['k_usd'], gain_db=-15, label='≈ $4 500 000')
    add(fx, 'cartoon-hit', E['scam'] - 0.05, gain_db=-15, label='«это обман»')
    for key in ('c_jones', 'c_ades', 'c_oliv'):
        add(fx, 'pop', E[key] - 0.1, gain_db=-17, label=f'{key} figurine')
    add(fx, 'whoosh', E['strike'], align='peak', gain_db=-18, label='UFC Strike box in (after RubUp)')
    for i, key in enumerate(('s0', 's1', 's2', 's3', 's4')):
        add(fx, 'pop', E[key] - 0.1, gain_db=-18, pan=(i - 2) * 0.25, label=f'{key} figurine')
    add(fx, 'select', E['s5'], gain_db=-17, label='«+ ЕЩЁ 5»')
    add(fx, 'whoosh-short', E['sold'], gain_db=-19, label='strip of ten in')
    add(fx, 'counter', E['n60'] - 0.05, gain_db=-21, fit=1.1, label='counter to 60 000')
    add(fx, 'scan', E['auction'], gain_db=-24, fit=1.4, label='hours track fills')
    add(fx, 'confirm', E['hours'] + 0.2, gain_db=-15, label='«ВСЁ РАСКУПЛЕНО»')
    add(fx, 'glitch', E['neon'], gain_db=-21, label='stream window, LIVE')
    add(fx, 'riser-hit', E['streamer'], align='peak', gain_db=-18, label='N3ON')
    add(fx, 'select-soft', E['n323'], gain_db=-18, label='UFC 323')
    add(fx, 'sparkle-whoosh', E['octagon'], gain_db=-19, label='octagon in, lights')
    add(fx, 'whoosh-short', E['fighters_out'] - 0.2, gain_db=-19, label='two fighters walk in')
    add(fx, 'sparkle', E['golden'], gain_db=-16, label='gold figurines')
    add(fx, 'impact', E['half'], gain_db=-15, label='0,5%')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='grid of ten in')
    add(fx, 'granular-move', E['o_profile'], gain_db=-22, fit=0.8, label='wave over the ten')
    add(fx, 'typing', E['o_write'] + 0.4, gain_db=-22, fit=0.8, label='«Мой боец —» typed')
    return fx * 10 ** (SFX_GAIN_DB / 20)


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            start = round(ON[k] * SR)
            count = min(len(data), n - start)
            voice[start:start+count] += data[:count] * 0.85
    else:
        print('Дикторской озвучки нет. Добавите новый ключ Fish Audio и свой голос? Пока текст + звук баннера.')
    fx = sfx_layer(n, kit)
    if HAS_NARRATION:                       # SFX step back under speech
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        fx *= (1 - 0.5 * np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1))[:, None]
    g = 10 ** (CONTENT_GAIN_DB / 20)
    return (voice + fx) * g, fx * g


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE)
    content, fx = make_mix(kit)
    data = BR.audio(content, SR)
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98)*32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    print('build/mix.wav готов; для прослушивания:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')
