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
    add(fx, 'pop', 0.02, gain_db=-14, label='Snoop Dogg pops in (hook)')
    add(fx, 'sparkle', E['five_word'], gain_db=-19, label='«5» bumps')
    add(fx, 'whoosh-short', E['five'], gain_db=-19, label='Snoop moves to slot 1')
    for i, k in enumerate(('n1', 'n2', 'n3', 'n4')):
        add(fx, 'pop', E[k] - 0.1, gain_db=-17, pan=(-0.3, 0.3, -0.15, 0.15)[i], label=f'collection {i + 2} lands')
    add(fx, 'whoosh-short', E['sold'], gain_db=-20, label='five gifts fly into the strip')
    add(fx, 'counter', E['million'] - 0.05, gain_db=-21, fit=1.3, label='counter runs to 996 000')
    add(fx, 'confirm', E['million'] + 1.2, gain_db=-16, label='996 000 reached')
    add(fx, 'impact', E['usd'], gain_db=-15, label='$12 000 000')
    add(fx, 'sparkle-whoosh', E['second'], gain_db=-21, label='dashed card «?» is drawn')
    add(fx, 'riser-hit', E['series'], align='peak', gain_db=-18, label='«СЕРИЯ 2» turns gold')
    add(fx, 'whoosh', E['khabib'], align='peak', gain_db=-18, label='Snoop block out, Khabib in')
    add(fx, 'select-soft', E['papakha'], gain_db=-18, label="Khabib's Papakha label")
    add(fx, 'counter', E['k29'] - 0.05, gain_db=-21, fit=1.1, label='counter to 29 000')
    add(fx, 'scan', E['auction'] - 0.1, gain_db=-24, fit=1.4, label='24 h ring fills')
    add(fx, 'confirm', E['day'] + 0.3, gain_db=-16, label='ring closed')
    add(fx, 'cartoon-hit', E['accused'] - 0.1, gain_db=-15, label='Conor quote bubble + papakha shakes')
    add(fx, 'whoosh-short', E['durov'], gain_db=-18, label='Khabib out, Durov in (after RubUp)')
    add(fx, 'pop', E['durov'] + 0.15, gain_db=-17, label="Durov's Cap lands")
    add(fx, 'select', E['release'], gain_db=-19, label="«Durov's Cap» label")
    add(fx, 'whoosh-short', E['pepe'], gain_db=-18, label='cap steps aside, card is drawn')
    add(fx, 'sparkle', E['first'], gain_db=-17, label='Plush Pepe #1')
    add(fx, 'coin', E['price'], gain_db=-15, label='$47 000')
    add(fx, 'whoosh', E['evelone'], align='peak', gain_db=-19, label='card out, Evelone in')
    add(fx, 'list', E['e119'] - 0.25, gain_db=-21, fit=1.3, label='119 cells fill')
    add(fx, 'confirm', E['e119'] + 1.05, gain_db=-17, label='119 reached')
    add(fx, 'coin', E['e40'], gain_db=-15, label='≈ 40 000 000 ₽')
    add(fx, 'whoosh-short', E['porsche'], gain_db=-18, label='Evelone out, Portals in')
    for j in range(0, 18, 3):
        add(fx, 'pop', E['g18'] - 0.3 + 0.045 * j, gain_db=-22, pan=((j // 3) - 2.5) * 0.15, label=f'gifts {j + 1}–{j + 3} land')
    add(fx, 'whoosh-short', E['car'] - 0.7, gain_db=-21, label='arrow down')
    add(fx, 'riser', E['car'] + 0.7, align='end', gain_db=-21, fit=1.1, label='car outline is drawn')
    add(fx, 'impact', E['car'] + 0.75, gain_db=-14, label='PORSCHE 911 GT3 turns gold')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='three cards in')
    for k in ('o_snoop', 'o_khabib', 'o_durov'):
        add(fx, 'select', E[k], gain_db=-18, label=f'{k} card lights up')
    add(fx, 'typing', E['o_write'] + 0.4, gain_db=-22, fit=0.8, label='«Мой выбор —» typed')
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
