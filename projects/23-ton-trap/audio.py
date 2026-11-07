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
    add(fx, 'whoosh-short', 0.02, gain_db=-18, label='record Pepe in (hook)')
    add(fx, 'coin', E['h_228'] - 0.05, gain_db=-16, label='$228 000')
    add(fx, 'popup', E['h_ton'] - 0.1, gain_db=-18, label='TON coin + 107 207 TON')
    add(fx, 'downlifter', E['h_today'] + 0.1, gain_db=-19, fit=1.6, label='dollars roll down to $118 657')
    add(fx, 'impact', E['h_119'] + 0.6, gain_db=-15, label='stamp −$109 343, red flush')
    add(fx, 'whoosh', E['i_ton'] - 0.5, align='peak', gain_db=-20, label='«продали за TON и не вывели?»')
    add(fx, 'select-soft', E['i_ton'] - 0.3, gain_db=-19, label='big TON coin')
    add(fx, 'power-down', E['i_melt'] - 0.1, gain_db=-18, fit=1.0, label='coin melts')
    for n_, (key, p) in zip((4, 3, 2, 1), [('cat', 'ca'), ('durov', 'du'), ('sept', 'se'), ('record', 're')]):
        add(fx, 'whoosh-short', E[key] + (0.1 if key == 'sept' else 0.0), gain_db=-19, label=f'place {n_} in')
        add(fx, 'pop', E[key] + 0.15, gain_db=-19, label=f'ring «{n_}»')
        add(fx, 'coin', E[p + '_ton'] - 0.05, gain_db=-20, label=f'place {n_}: TON amount')
        add(fx, 'select-soft', E[p + '_then'] - 0.05, gain_db=-19, label=f'place {n_}: dollars then')
        add(fx, 'power-down', E[p + '_now'] - 0.05, gain_db=-19, fit=0.8, label=f'place {n_}: line falls, gift sags')
        add(fx, 'impact', E[p + '_pct'] + 0.05, gain_db=-16 if key != 'record' else -14, label=f'place {n_}: stamp')
    add(fx, 'sub-drop', E['re_pct'] + 0.05, gain_db=-17, label='place 1: red flush')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='outro cards in')
    add(fx, 'select', E['o_hold'], gain_db=-19, label='«ДЕРЖУ» highlight')
    add(fx, 'select', E['o_out'], gain_db=-19, label='«ВЫВОЖУ» highlight')
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
