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
import config
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
    add(fx, 'whoosh-short', 0.02, gain_db=-18, label='mystery silhouette in (hook)')
    add(fx, 'riser', E['h_x'] - 0.05, gain_db=-18, fit=1.2, label='×1 → ×880 counter')
    add(fx, 'error', E['h_pepe'], gain_db=-19, label='«не Пепе» cross')
    add(fx, 'impact', E['h_end'] - 0.05, gain_db=-17, label='stamp «покажу последним»')
    add(fx, 'whoosh', E['intro'] + 0.1, align='peak', gain_db=-20, label='intro title')
    for i in range(5):
        add(fx, 'select-soft', E['intro'] + 0.2 + 0.1 * i, gain_db=-20, label=f'card {i + 1}')
    gain = {1: True, 2: False, 3: False, 4: True, 5: True}
    for n_ in range(1, 6):
        key, p = f'p{n_}', f'q{n_}'
        add(fx, 'whoosh-short', E[key], gain_db=-19, label=f'gift {n_} in')
        add(fx, 'counter', E[p + '_then'] - 0.05, gain_db=-19, label=f'gift {n_}: store price')
        add(fx, 'power-up' if gain[n_] else 'power-down', E[p + '_now'], gain_db=-20, fit=0.8,
            label=f'gift {n_}: price counts {"up" if gain[n_] else "down"}')
        add(fx, 'impact', E[p + '_pct'] + 0.05, gain_db=-17, label=f'gift {n_}: verdict stamp')
        add(fx, 'confirm', E[p + '_thing'], gain_db=-18, label=f'gift {n_}: real thing card')
    add(fx, 'whoosh-deep', E['tease'], gain_db=-19, label='teaser: Pepe silhouette')
    add(fx, 'power-up', E['ts_x'] - 0.05, gain_db=-19, fit=0.9, label='teaser: ×266 counter')
    add(fx, 'cartoon-hit', E['ts_stop'] - 0.15, gain_db=-17, label='stamp «не листай!»')
    add(fx, 'sparkle', E['q5_name'] - 0.2, gain_db=-18, label='cat revealed')
    add(fx, 'whoosh', E['total'], align='peak', gain_db=-19, label='total in')
    add(fx, 'coin', E['t_sum'] - 0.05, gain_db=-16, label='18 025 ★')
    add(fx, 'riser', E['t_today'], gain_db=-19, fit=0.9, label='$ counts up')
    add(fx, 'impact', E['t_car'] - 0.3, gain_db=-16, label='Lada card')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='outro cards in')
    add(fx, 'typing', E['o_write'] + 0.4, gain_db=-22, fit=0.9, label='comment typed')
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
