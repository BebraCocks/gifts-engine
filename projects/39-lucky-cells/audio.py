"""Voice + SFX (Botanica V4 via sfxkit, no repeats) + music (music.py, code) + the complete RubUp sound.
No author's sound here (author, 2026-11-06: «без звука … удаляем»).
Writes build/mix.wav and, for the author, build/review/{sfx_only,mix}.mp3 + sfx_cues.txt (+ music_only.mp3)."""
import subprocess
import zlib
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
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES, ROUND_IN, TIMER0, REVEAL, OUTRO, SWAP
from events import AD_STOP, E
from script import ROUNDS
import render as R
import music

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
CONTENT_GAIN_DB = 3.0      # voice + SFX + music up to ≈ −14 LUFS (the RubUp sound is not touched)
MUSIC_DB = -12.0           # under the voice; ducks a further 7 dB while someone speaks


def sfx_layer(n, kit):
    """One cue = one action on screen (STORYBOARD.md, «Звук»). No own SFX during RubUp (docs/ADVERTISING.md).
    A series of the same action sounds different: the box-opening cascade climbs in pitch, ticks are one motif."""
    fx = np.zeros((n, 2))
    add = kit.add
    add(fx, 'sparkle-whoosh', 0.0, gain_db=-18, label='hook: six closed boxes + «БОЛЬШЕ 5000?»')
    add(fx, 'pop', 1.4, gain_db=-19, label='hook: «БОЛЬШЕ 5000?» pulses')
    add(fx, 'select', E['blue'], gain_db=-19, pan=-0.1, label='rules: blue row bounces, tag')
    add(fx, 'select', E['red'], gain_db=-19, pan=0.1, label='rules: red row bounces, tag')
    add(fx, 'paper', E['pick'] - 0.1, gain_db=-21, label='rules: title «ВЫБЕРИ 1 СИНЮЮ И 1 КРАСНУЮ»')
    for k in range(3):
        add(fx, 'counter', E['more'] + 0.12 * k, gain_db=-22, key='chip', vary=False, semitones=3 * k,
            label=f'rules: chip {(100, 1000, 5000)[k]}')
    for r in range(5):
        nb = len(ROUNDS[r]['blue'])
        if r:
            add(fx, 'whoosh-short', ROUND_IN[r] - SWAP, gain_db=-20, label=f'round {r}: open cards fall away')
            add(fx, 'pop', ROUND_IN[r] - SWAP + 0.2, gain_db=-21, label=f'round {r + 1}: new boxes pop in')
        for s in range(5):
            add(fx, 'click', TIMER0[r] + s, gain_db=-24 + 1.5 * (s >= 3), key='tick', vary=False, dur=(0, 0.3),
                label=f'round {r + 1}: timer {5 - s}')
        add(fx, 'riser', REVEAL[r], gain_db=-28, align='end', fit=1.2, label=f'round {r + 1}: last second')
        for row in (0, 1):
            pts = (ROUNDS[r]['blue_pts'], ROUNDS[r]['red_pts'])[row]
            for k in range(nb):
                j = nb * row + k
                tf = R.flip_t(r, row, k)
                pan = (k - (nb - 1) / 2) * (0.8 / max(1, nb - 1))
                add(fx, 'flip', tf, gain_db=-22 - (2 if nb == 5 else 0), key='flip', vary=False,
                    semitones=(0.8 if nb == 3 else 0.5) * j - 2, pan=pan,
                    label=f'round {r + 1}: box opens ({"blue" if row == 0 else "red"} {k + 1})')
                if pts[k] == max(pts):
                    add(fx, 'coin', tf + 0.3, gain_db=-20, pan=pan,
                        label=f'round {r + 1}: best of the row {pts[k]} ({"blue" if row == 0 else "red"} {k + 1})')
                if pts[k] >= 5000:
                    add(fx, 'impact', tf + 0.32, gain_db=-20, label=f'round {r + 1}: ★ 5000 jackpot')
    add(fx, 'sparkle', END[KEY['a3']] - 0.15, gain_db=-19, label='teaser pill «НЕ ЛИСТАЙ» before RubUp')
    add(fx, 'sparkle', ROUND_IN[4] - SWAP + 0.5, gain_db=-21, label='final: the gold box appears')
    # the gold box: a small, quiet explosion (author: «небольшого и не особо громкого»)
    add(fx, 'impact', E['gold_open'], gain_db=-21, file='impact-hit/hit-impact-with-fx-04.flac', vary=False, fit=1.3,
        fade_out=0.4, label='gold box: bomb — small explosion')
    add(fx, 'error', E['gold_open'] + 0.4, gain_db=-23, label='gold box: «−1000»')
    add(fx, 'whoosh', OUTRO, gain_db=-20, label='outro: cards leave')
    for i in range(5):
        add(fx, 'list', E['sum'] + 0.05 + 0.16 * i, gain_db=-21, key='lvl', vary=False, semitones=2 * i,
            label=f'levels: row {i + 1}')
    add(fx, 'confirm', E['sum'] + 0.05 + 0.16 * 4 + 0.1, gain_db=-19, label='levels: «ВАНГА ИЗ ТЕЛЕГИ» (gold)')
    add(fx, 'popup', E['comments'], gain_db=-16, label='«ПИШИ СВОЙ РЕЗУЛЬТАТ» pill')
    return fx


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            start = round(ON[k] * SR)
            count = min(len(data), n - start)
            voice[start:start + count] += data[:count] * 0.85
    else:
        print('Дикторской озвучки нет: текст + звук баннера.')
    fx = sfx_layer(n, kit)
    mus = music.music(n, SR) * 10 ** (MUSIC_DB / 20)
    if HAS_NARRATION:                       # SFX and music step back under speech
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        k = np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1)
        k = np.convolve(k, np.ones(4800) / 4800, 'same')          # smooth duck, no pumping
        fx *= (1 - 0.45 * k)[:, None]
        mus *= (1 - (1 - 10 ** (-7 / 20)) * k)[:, None]
    g = 10 ** (CONTENT_GAIN_DB / 20)
    return (voice + fx + mus) * g, fx * g, mus * g


def mp3(x, path):
    raw = (np.clip(x, -0.98, 0.98) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-b:a', '192k', str(path)], input=raw, check=True)


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE, seed=zlib.crc32(b'39-lucky-cells'))
    content, fx, mus = make_mix(kit)
    data = BR.audio(content, SR)
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    mp3(mus, rev / 'music_only.mp3')
    print('build/mix.wav готов; для прослушивания:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt',
          rev / 'music_only.mp3')
