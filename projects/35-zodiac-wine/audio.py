"""Voice + SFX (Botanica V4 via sfxkit, no repeats) + music (music.py, code) + the complete RubUp sound.
Writes build/mix.wav and, for the author, build/review/{sfx_only,mix,music_only}.mp3 + sfx_cues.txt."""
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
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES, SIGN_IN, FORECAST, OUTRO, SWAP, AD_STOP
from events import E
import music

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
CONTENT_GAIN_DB = 3.0
MUSIC_DB = -13.0           # under the voice; ducks a further 7 dB while someone speaks


def sfx_layer(n, kit):
    """One cue = one action on screen (STORYBOARD.md, «Звук»). No own SFX during RubUp (docs/ADVERTISING.md)."""
    fx = np.zeros((n, 2))
    add = kit.add
    add(fx, 'sparkle-whoosh', 0.0, gain_db=-17, label='hook: the zodiac wheel of 12 mugs')
    add(fx, 'sparkle', E['twelve'], gain_db=-19, label='«двенадцать»: ripple around the wheel, «12»')
    add(fx, 'select', E['four'], gain_db=-18, label='«четыре»: 4 mugs glow, the rest dim')
    add(fx, 'pop', E['find'], gain_db=-19, label='«найди свой»: badge bump')
    add(fx, 'whoosh', SIGN_IN[0] - 0.55, gain_db=-19, label='Scorpio leaves the wheel for the centre')
    for s in range(4):
        if s:
            add(fx, 'whoosh-short', SIGN_IN[s] - SWAP - 0.2, gain_db=-20, label=f'sign {s}: mug flies off left')
            add(fx, 'whoosh-organic', SIGN_IN[s] - 0.38, gain_db=-21, label=f'sign {s + 1}: mug drops in')
        add(fx, 'impact', SIGN_IN[s] - 0.08, gain_db=-23, dur=(0, 0.8), file='hit-impact', label=f'sign {s + 1}: mug lands, header')
        add(fx, 'granular-move', SIGN_IN[s] + 0.15, gain_db=-23, label=f'sign {s + 1}: constellation draws')
        add(fx, 'popup', FORECAST[s] - 0.05, gain_db=-20, key='forecast', vary=False,
            label=f'sign {s + 1}: «ПРОГНОЗ» pill (one sound — a motif)')
        add(fx, 'sparkle', FORECAST[s] + 0.05, gain_db=-21, label=f'sign {s + 1}: sparkles fly out')
    add(fx, 'popup', END[KEY['h2']] + 0.1, gain_db=-18, label='teaser «НЕ ЛИСТАЙ» before RubUp')
    add(fx, 'sparkle-whoosh', OUTRO - 0.1, gain_db=-18, label='outro: the wheel returns')
    add(fx, 'confirm', OUTRO + 0.15, gain_db=-20, label='«А ТВОЙ ЗНАК?»')
    add(fx, 'pop', E['comments'], gain_db=-16, label='«ПИШИ В КОММЕНТАРИЯХ» pill')
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
    if HAS_NARRATION:
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        k = np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1)
        k = np.convolve(k, np.ones(4800) / 4800, 'same')
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
