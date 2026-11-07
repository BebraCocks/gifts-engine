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
    add(fx, 'whoosh-short', 0.02, gain_db=-18, label='Snoop Dogg gift in (hook)')
    add(fx, 'counter', E['h_mln'] - 0.1, gain_db=-20, fit=1.0, label='counter to 996 000')
    add(fx, 'click', E['h_half'] - 0.05, gain_db=-17, label='«за 30 минут»')
    add(fx, 'error', E['h_minus'] + 0.05, gain_db=-17, label='stamp «часть — в минусе»')
    add(fx, 'whoosh', E['i_five'] - 0.2, align='peak', gain_db=-20, label='title «цена в магазине…»')
    for i in range(5):
        add(fx, 'select-soft', E['i_five'] + 0.12 * i, gain_db=-20, label=f'gift card {i + 1} of 5')
    add(fx, 'sparkle', E['i_shop'], gain_db=-21, label='star price tags')
    gains = {'snoop': 'confirm', 'cigar': 'confirm', 'westside': 'select', 'lowrider': 'boing', 'swag': 'impact'}
    for n_, (key, p) in enumerate([('snoop', 'sn'), ('cigar', 'ci'), ('westside', 'we'), ('lowrider', 'lo'),
                                   ('swag', 'sw')], 1):
        add(fx, 'whoosh-short', E[key] + (0.1 if key == 'westside' else 0.0), gain_db=-19, label=f'gift {n_} in')
        add(fx, 'pop', E[key] + 0.15, gain_db=-19, label=f'ring «{n_}»')
        add(fx, 'coin', E[p + '_then'] - 0.1, gain_db=-20, label=f'gift {n_}: store price')
        add(fx, 'power-down' if key == 'swag' else 'power-up', E[p + '_now'] - 0.05, gain_db=-20, fit=0.7,
            label=f'gift {n_}: line to today')
        add(fx, gains[key], E[p + '_pct'] + 0.05, gain_db=-17, label=f'gift {n_}: stamp')
    add(fx, 'sub-drop', E['sw_pct'] + 0.05, gain_db=-18, label='Swag Bag: red flush')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='outro cards in')
    for i in range(5):
        add(fx, 'select', E['o_took'] + 0.12 * i, gain_db=-21, label=f'card {i + 1} highlight')
    add(fx, 'typing', E['o_write'] + 0.4, gain_db=-22, fit=0.9, label='«Я брал Swag Bag и» typed')
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
