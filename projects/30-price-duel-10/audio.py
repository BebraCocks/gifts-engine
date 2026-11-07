"""Voice + SFX (Botanica V4 via sfxkit, no repeats) + music (music.py, code) + the complete RubUp sound.
No author's sound here (author, 2026-11-06: «без звука … удаляем»).
Writes build/mix.wav and, for the author, build/review/{sfx_only,mix}.mp3 + sfx_cues.txt (+ music_only.mp3)."""
import subprocess
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
from timeline import DUR, ON, END, HAS_NARRATION, TAKES, ROUND_IN, TIMER0, REVEAL, OUTRO, SWAP
from events import AD_STOP, E, WIN
import music

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
CONTENT_GAIN_DB = 3.0      # voice + SFX + music up to ≈ −14 LUFS (the RubUp sound is not touched)
MUSIC_DB = -12.0           # under the voice; ducks a further 7 dB while someone speaks


def sfx_layer(n, kit):
    """One cue = one action on screen (STORYBOARD.md, «Звук»). No own SFX during RubUp (docs/ADVERTISING.md)."""
    fx = np.zeros((n, 2))
    add = kit.add
    add(fx, 'sparkle-whoosh', 0.0, gain_db=-18, label='hook: the bet appears')
    add(fx, 'pop', 0.55, gain_db=-17, label='«ПРОТИВ» bumps')
    add(fx, 'select', E['hook_q'], gain_db=-19, label='title «ЧТО ДОРОЖЕ?» + score')
    for r in range(5):
        if r:
            add(fx, 'whoosh-short', ROUND_IN[r] - SWAP + 0.05, gain_db=-19, label=f'round {r}: items fly out')
        add(fx, 'whoosh-organic', ROUND_IN[r] - (SWAP - 0.1 if r else 0.0), gain_db=-22, label=f'round {r + 1}: items drop')
        add(fx, 'pop', ROUND_IN[r] + 0.2, gain_db=-20, label=f'round {r + 1}: items land on the pans')
        for s in range(5):                      # one tick sound for the whole video: a timer is a motif
            add(fx, 'click', TIMER0[r] + s, gain_db=-23 + 1.5 * (s >= 3), key='tick', vary=False, file='mechanical-click-04',
                label=f'round {r + 1}: timer {5 - s}')
        add(fx, 'impact', REVEAL[r], gain_db=-18, pan=-0.35 if WIN[r] == 0 else 0.35,
            label=f'round {r + 1}: the scale falls to the dearer side')
        add(fx, 'boing', REVEAL[r] + 0.14, gain_db=-19, key='stamp', vary=False, pan=-0.35 if WIN[r] == 0 else 0.35,
            label=f'round {r + 1}: «ДОРОЖЕ» stamp')
        add(fx, 'coin', REVEAL[r] + 0.08, gain_db=-22, label=f'round {r + 1}: price tags')
        add(fx, 'select-soft', REVEAL[r] + 0.2, gain_db=-21, label=f'round {r + 1}: score +1')
    add(fx, 'whoosh-short', OUTRO, gain_db=-20, label='outro: prices go, «ГДЕ ОШИБСЯ?»')
    add(fx, 'popup', E['comments'], gain_db=-16, label='«ПИШИ В КОММЕНТЫ» pill on «жду»')
    add(fx, 'flip', E['which'] - 0.1, gain_db=-19, label='«ГДЕ ОШИБСЯ?»')
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
    kit = sfxkit.Kit(HERE)
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
