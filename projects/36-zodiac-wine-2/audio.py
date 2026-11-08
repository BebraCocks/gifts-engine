"""Voice + SFX + background bed — every non-voice sound from the pack input/sfx/ (Botanica V4) via sfxkit
(author, 2026-11-08: «звуки используй из папки»; the code-synthesized music of v1 removed) + the complete RubUp sound.
Writes build/mix.wav and, for the author, build/review/{sfx_only,mix,bed_only,voice_only}.mp3 + sfx_cues.txt."""
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
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES, SIGN_IN, OUTRO, SWAP, AD_STOP
from events import E, FORECAST

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
CONTENT_GAIN_DB = 3.0
BED_DB = -8.0              # pack bed under the voice; ducks a further 7 dB while someone speaks


def sfx_layer(n, kit):
    """One cue = one action on screen (STORYBOARD.md, «Звук»). No own SFX during RubUp (docs/ADVERTISING.md)."""
    fx = np.zeros((n, 2))
    add = kit.add
    add(fx, 'sparkle-whoosh', 0.0, gain_db=-17, label='hook: the zodiac wheel of 12 mugs')
    add(fx, 'sparkle', E['twelve'], gain_db=-19, label='«у каждого»: ripple around the wheel, «12»')
    add(fx, 'select', E['four'], gain_db=-18, label='«первая»: 4 mugs glow, the rest dim')
    add(fx, 'pop', E['four'] + 0.3, gain_db=-19, label='«первая часть»: «ЧАСТЬ 1», badge bump')
    add(fx, 'whoosh', SIGN_IN[0] - 0.55, gain_db=-19, label='sign 1 leaves the wheel for the centre')
    for s in range(4):
        if s:
            add(fx, 'whoosh-short', SIGN_IN[s] - SWAP - 0.2, gain_db=-20, label=f'sign {s}: mug flies off left')
            add(fx, 'whoosh-organic', SIGN_IN[s] - 0.38, gain_db=-21, label=f'sign {s + 1}: mug drops in')
        add(fx, 'impact', SIGN_IN[s] - 0.08, gain_db=-23, dur=(0, 0.8), file='hit-impact', label=f'sign {s + 1}: mug lands, header')
        add(fx, 'granular-move', SIGN_IN[s] + 0.15, gain_db=-23, label=f'sign {s + 1}: constellation draws')
        add(fx, 'sparkle', FORECAST[s] + 0.05, gain_db=-21, label=f'sign {s + 1}: forecast sentence — sparkles fly out')
    add(fx, 'popup', END[KEY['s2']] + 0.1, gain_db=-18, label='teaser «НЕ ЛИСТАЙ» before RubUp')
    add(fx, 'sparkle-whoosh', OUTRO - 0.1, gain_db=-18, label='outro: the wheel returns')
    add(fx, 'confirm', OUTRO + 0.15, gain_db=-20, label='«А КТО ТЫ ПО ЗНАКУ ЗОДИАКА?»')
    add(fx, 'pop', E['comments'], gain_db=-16, label='«ПИШИ В КОММЕНТАРИЯХ» pill')
    return fx


def bed_layer(n, kit):
    """Night-sky bed from the pack (dark, tonal, wide, unused by other videos) + musical swells on the big turns."""
    b = np.zeros((n, 2))
    kit.add(b, ['bed', 'ambience', 'music-transition', '*'], 0.0, gain_db=0.0, vary=False, fit=DUR, fade_out=0.8,
            file='atmo-bg-static-musical-24', label='bed: night sky under the whole video')
    kit.add(b, ['music-transition', '*'], SIGN_IN[0] - 0.05, gain_db=-4.0, vary=False, align='peak',
            file='long-b-music-transition-01', label='swell: hook -> sign 1')
    kit.add(b, ['music-transition', '*'], OUTRO + 0.1, gain_db=-4.0, vary=False, align='peak',
            file='longer-b-music-transition-02', label='swell: the wheel returns (outro)')
    f = np.minimum(1, np.arange(n) / SR / 0.3)
    return b * f[:, None]


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
    mus = bed_layer(n, kit) * 10 ** (BED_DB / 20)
    if HAS_NARRATION:
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        k = np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1)
        k = np.convolve(k, np.ones(4800) / 4800, 'same')
        fx *= (1 - 0.45 * k)[:, None]
        mus *= (1 - (1 - 10 ** (-7 / 20)) * k)[:, None]
    g = 10 ** (CONTENT_GAIN_DB / 20)
    return (voice + fx + mus) * g, fx * g, mus * g, voice * g


def mp3(x, path):
    raw = (np.clip(x, -0.98, 0.98) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-b:a', '192k', str(path)], input=raw, check=True)


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE)
    content, fx, mus, voice = make_mix(kit)
    data = BR.audio(content, SR)
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    mp3(mus, rev / 'bed_only.mp3')
    mp3(voice / (np.abs(voice).max() + 1e-9) * 0.9, rev / 'voice_only.mp3')    # narration alone, content time
    print('build/mix.wav готов; для прослушивания:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt',
          rev / 'bed_only.mp3', rev / 'voice_only.mp3')
