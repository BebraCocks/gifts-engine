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
    add(fx, 'pop', 0.02, gain_db=-14, label='Plush Pepe #1 pops in (hook)')
    add(fx, 'sparkle', E['first'], gain_db=-18, label='«самый первый»')
    add(fx, 'whoosh-short', E['link'], gain_db=-19, label='hook out, share sheet in')
    add(fx, 'click', E['copy'] + 0.25, gain_db=-13, label='«Копировать ссылку» tapped')
    add(fx, 'confirm', E['copy'] + 0.55, gain_db=-17, label='toast «Ссылка скопирована»')
    add(fx, 'sparkle-whoosh', E['pepe1'], gain_db=-20, label='collectible card is drawn')
    add(fx, 'coin', E['price1'], gain_db=-15, label='$47 000')
    add(fx, 'whoosh-short', E['helmet'], gain_db=-18, label='card out, helmet in')
    add(fx, 'impact', E['h11'], gain_db=-16, label='$11 000')
    add(fx, 'riser', E['h10'] + 0.4, align='end', gain_db=-22, fit=0.7, label='bars grow ×10')
    add(fx, 'whoosh-short', E['p834'], gain_db=-19, label='helmet out, Pepe #834 in')
    add(fx, 'whoosh', E['p_gift'] + 0.35, align='peak', gain_db=-18, label='Pepe flies to the designer')
    add(fx, 'whoosh', E['brick'], align='peak', gain_db=-19, label='brick in (after RubUp)')
    add(fx, 'counter', E['b7000'] - 0.05, gain_db=-21, fit=1.0, label='counter to 7 000')
    add(fx, 'scan', E['b_sold'], gain_db=-24, fit=1.4, label='34 min track fills')
    add(fx, 'confirm', E['b34'] + 0.4, gain_db=-17, label='«34 мин»')
    add(fx, 'whoosh-short', E['cap'], gain_db=-18, label='cap in')
    add(fx, 'select-soft', E['c15'], gain_db=-18, label='$15')
    add(fx, 'riser-hit', E['c3000'] + 0.3, align='peak', gain_db=-17, label='line climbs to $2 829')
    add(fx, 'whoosh-short', E['quote'], gain_db=-19, label='quote in')
    add(fx, 'pop', E['q2'] - 0.05, gain_db=-17, label='$2')
    add(fx, 'impact', E['q100'], gain_db=-14, label='$100 000+')
    add(fx, 'whoosh', E['total'], align='peak', gain_db=-19, label='dot grid in')
    add(fx, 'list', E['t761'] - 0.3, gain_db=-21, fit=1.4, label='761 dots light up')
    add(fx, 'coin', E['t35'], gain_db=-15, label='≈ 35 000 000 ₽')
    add(fx, 'whoosh', E['outro'], align='peak', gain_db=-19, label='three cards in')
    for k in ('o_pepe', 'o_helmet', 'o_cap'):
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
