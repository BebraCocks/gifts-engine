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
    add(fx, 'pop', 0.02, gain_db=-15, label='gift pops into the centre')
    add(fx, 'sparkle-whoosh', E['real'] - 0.1, gain_db=-20, label='card outline is drawn')
    add(fx, 'select-soft', E['model'], gain_db=-19, label='card rows: Snoop Dogg / Barks Lightyear')
    add(fx, 'whoosh-short', E['profile'], gain_db=-19, label='gift flies into the profile')
    add(fx, 'click', E['profile'] + 0.6, gain_db=-14, label='gift lands in the cell')
    add(fx, 'counter', E['million'] - 0.05, gain_db=-21, fit=1.2, label='counter runs to 1 000 000')
    add(fx, 'confirm', E['million'] + 1.15, gain_db=-16, label='1 000 000 reached')
    add(fx, 'select', E['half'], gain_db=-19, label='«30 мин» lights up')
    add(fx, 'whoosh-short', E['want'], gain_db=-18, label='gift comes back')
    for i in range(3):
        add(fx, 'pop', E['three'] - 0.3 + 0.12 * i, gain_db=-20, label=f'circle {i + 1} drawn')
    add(fx, 'transform', E['like'], gain_db=-20, label='1 -> heart')
    add(fx, 'confirm', E['done'] + 0.05, gain_db=-15, label='heart fills (after RubUp)')
    add(fx, 'transform', E['repost'], gain_db=-20, label='2 -> share arrow')
    add(fx, 'whoosh-short', E['friend'], gain_db=-16, label='repost flies to a friend')
    add(fx, 'transform', E['comment'], gain_db=-20, label='3 -> bubble')
    add(fx, 'typing', E['what'] + 0.45, gain_db=-22, fit=2.1, label='comment is typed')
    add(fx, 'confirm', END[KEY['comment']] - 0.15, gain_db=-16, label='bubble fills')
    for j in range(10):
        add(fx, 'pop', E['ten'] - 0.25 + 0.075 * j + 0.28, gain_db=-22, pan=(j % 5 - 2) * 0.25,
            label=f'bear {j + 1} lands')
    add(fx, 'sparkle', E['ten'] + 0.9, gain_db=-19, label='× 10')
    add(fx, 'flip', E['week'], gain_db=-18, label='«7 дней»')
    add(fx, 'scan', E['random'] - 0.25, gain_db=-23, fit=max(0.3, E['pin'] - E['random'] + 0.25),
        label='nickname bars shuffle')
    add(fx, 'click', E['pin'], gain_db=-13, label='pin')
    add(fx, 'whoosh-short', ON[KEY['final']] - 0.45, gain_db=-19, label='conditions come back')
    for k in ('f_like', 'f_repost', 'f_comment'):
        add(fx, 'confirm', E[k], gain_db=-17, label=f'{k} lights up')
    add(fx, 'whoosh', E['f_snoop'] + 0.15, align='peak', gain_db=-18, label='Snoop drops back')
    add(fx, 'sparkle', E['f_snoop'] + 1.5, gain_db=-19, label='final pose')
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
