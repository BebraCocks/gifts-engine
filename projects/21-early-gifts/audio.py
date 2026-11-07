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
    add(fx, 'pop', 0.02, gain_db=-14, label='crumbs pack in (hook)')
    add(fx, 'whoosh-short', E['h_gift'] - 0.1, gain_db=-19, label='pack slides left, crossed')
    add(fx, 'sparkle', E['h_gift'] + 0.05, gain_db=-18, label='Swiss Watch pops in')
    add(fx, 'impact', E['h_phone'], gain_db=-17, label='phone appears «как айфон»')
    add(fx, 'whoosh', E['count'], align='peak', gain_db=-19, label='«Сколько бы вы заработали?»')
    add(fx, 'scan', E['c_how'], gain_db=-23, fit=1.6, label='timeline dot 2024 -> 2026')
    add(fx, 'whoosh-short', E['watch'], gain_db=-19, label='watch in')
    add(fx, 'coin', E['w15'], gain_db=-16, label='$1,5')
    add(fx, 'pop', E['w_crumbs'] - 0.15, gain_db=-18, label='two crumbs packs')
    add(fx, 'whoosh-short', E['wnow'], gain_db=-19, label='«ноябрь 2026»')
    add(fx, 'counter', E['w75'] - 0.1, gain_db=-21, fit=0.8, label='counter to 75 TON')
    add(fx, 'riser-hit', E['w50'] + 0.3, align='peak', gain_db=-17, label='bars, ×50')
    add(fx, 'list', E['w20'] - 0.3, gain_db=-21, fit=0.9, label='20 packs appear')
    add(fx, 'sparkle-whoosh', E['w10'], gain_db=-19, label='packs turn into 10 watches')
    add(fx, 'confirm', E['w_phone'] - 0.2, gain_db=-16, label='iPhone 16e')
    add(fx, 'whoosh', E['cap'] + 0.1, gain_db=-20, label='cap in (after RubUp)')
    add(fx, 'coin', E['c15'], gain_db=-16, label='$15')
    add(fx, 'pop', E['c_pizza'] - 0.3, gain_db=-17, label='pizza')
    add(fx, 'click', E['c2'] + 0.3, gain_db=-16, label='pizzas crossed')
    add(fx, 'sparkle', E['c_caps'] - 0.1, gain_db=-18, label='two caps')
    add(fx, 'impact', E['c_phone'] - 0.2, gain_db=-16, label='iPhone 17e')
    add(fx, 'whoosh-short', E['pepe'], gain_db=-19, label='Pepe in')
    add(fx, 'coin', E['p30'], gain_db=-16, label='$30')
    add(fx, 'select-soft', E['p_kino'] - 0.2, gain_db=-18, label='cinema tickets')
    add(fx, 'whoosh', E['pnow'], align='peak', gain_db=-19, label='«ноябрь 2026»')
    add(fx, 'counter', E['p649'] - 0.3, gain_db=-20, fit=1.2, label='counter to 649 000 ₽')
    for j in range(3):
        add(fx, 'select', E['p3'] - 0.1 + 0.18 * j, gain_db=-18, label=f'phone {j + 1} of 3')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='three cards in')
    add(fx, 'typing', E['o_sorry'] + 0.0, gain_db=-22, fit=0.8, label='«Я не купил…» typed')
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
