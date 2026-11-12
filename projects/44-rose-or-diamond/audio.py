"""44-rose-or-diamond sound: the author's track laid out by timeline (intro -> fade -> silent dialogue -> back after
«Ах ты мразь!» -> drop on the diamond hit), the two voices (white left, pink right), SFX from input/sfx/ via sfxkit.
No RubUp banner (author, as in 43). Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import wave
import numpy as np
import sfxkit
import voice_review
import events as E
from timeline import DUR, DROP, RESUME

SR = 48000


def ticks(kit, fx, t0, t1, key, file, gain, first=0.045, last=0.30, label=''):
    t, k = t0, 0
    while t < t1:
        u = (t - t0) / (t1 - t0)
        kit.add(fx, 'list', t, gain_db=gain - 4 * u, key=key, file=file, pan=0.15 * ((-1) ** k),
                label=label if k == 0 else None)
        t += first + (last - first) * u ** 2.2
        k += 1


def reel_ticks(kit, fx, k, gain):
    """One tick per reel card passing the pointer, on the same smooth spin curve as the picture."""
    from timeline import SPINS, CARD_PITCH, spin_ease
    sp = SPINS[k]
    total = np.load(paths.build(HERE) / sp['file'])[1][-1]
    last, prev, n = -1.0, 0, 0
    for t in np.arange(sp['ta'], sp['tb'], 0.001):
        c = int(total * spin_ease((t - sp['ta']) / (sp['tb'] - sp['ta'])) // CARD_PITCH)
        if c > prev and t - last >= 0.035:
            u = (t - sp['ta']) / (sp['tb'] - sp['ta'])
            kit.add(fx, 'list', t, gain_db=gain - 3 * u + (2 if u > 0.7 else 0), key='roulette', file='mini-list-one-shot-2',
                    pan=0.15 * ((-1) ** n), label=f'reel {k + 1}' if n == 0 else None)
            last, n = t, n + 1
        prev = max(prev, c)


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    a = kit.add
    # intro: the white hand flicks the list
    for k, (t0, t1) in enumerate(E.SWIPES):
        a(fx, 'whoosh-short', t1, align='peak', gain_db=-23, pan=0.3, label=f'swipe {k + 1}')
        a(fx, 'select-soft', t0, gain_db=-28, pan=0.3, label=f'finger touch {k + 1}')
    # pink enters
    a(fx, 'whoosh-organic', E.PINK_IN[0], gain_db=-20, pan=0.6, fit=1.0, fade_out=0.3, label='pink slides in')
    a(fx, 'sparkle', E.PINK_IN[1] - 0.1, gain_db=-24, pan=0.5, label='pink lands')
    a(fx, 'whoosh-short', 6.70, align='peak', gain_db=-25, label='zoom to «Роза или алмаз»')
    a(fx, 'pop', 9.55, gain_db=-19, label='«О!» cut to the case')
    # case 1
    a(fx, 'whoosh-short', E.PRESS1, align='peak', gain_db=-24, pan=0.2, label='hand reach 1')
    a(fx, 'click', E.PRESS1, align='peak', gain_db=-11, label='«Открыть за 100»')
    reel_ticks(kit, fx, 0, -15)
    a(fx, 'impact', E.POP1, align='peak', gain_db=-21, label='rose popup')
    a(fx, 'popup', E.POP1 + 0.02, gain_db=-17, label='«Ваш подарок»')
    a(fx, 'sparkle', E.POP1 + E.HALO, gain_db=-19, label='rose pops out glowing (halo, rays)')
    a(fx, 'granular-move', E.GRAB1 - 0.05, gain_db=-22, label='rose taken out of the window')
    a(fx, 'sparkle-whoosh', 16.70, gain_db=-24, fit=1.0, fade_out=0.3, label='«Вот, держи» — he offers it')
    a(fx, 'select', E.GIVE, gain_db=-20, pan=0.3, label='she takes it')
    a(fx, 'glitch-text', E.STARE[0] + 0.15, gain_db=-26, pan=0.4, label='? 1')
    a(fx, 'boing', E.STARE[0] + 0.95, gain_db=-27, pan=0.4, label='? 3')
    # the throw
    a(fx, 'whoosh-short', E.THROW1, align='peak', gain_db=-18, pan=0.2, label='rose thrown')
    a(fx, 'cartoon-hit', E.ROSE_HIT, align='peak', gain_db=-14, pan=-0.3, label='rose smacks the face')
    a(fx, 'glitch-text', E.ROSE_HIT + 0.05, gain_db=-21, label='−1000 AURA')
    a(fx, 'cartoon-move', E.PINK_OUT[0], gain_db=-21, pan=0.7, label='she storms off')
    a(fx, 'impact', E.RAGE, align='peak', gain_db=-17, label='«Ах ты мразь!» rage')
    a(fx, 'glitch', E.RAGE + 0.05, gain_db=-22, label='rage glitch')
    # case 2
    a(fx, 'click', E.PRESS2, align='peak', gain_db=-11, label='«Крутить ещё»')
    reel_ticks(kit, fx, 1, -16)
    a(fx, 'impact', E.POP2, align='peak', gain_db=-20, label='diamond popup')
    a(fx, 'confirm', E.POP2 + 0.05, gain_db=-20, label='diamond chime')
    a(fx, 'sparkle-whoosh', E.POP2 + E.HALO, gain_db=-20, fit=1.2, fade_out=0.3, label='diamond pops out glowing')
    a(fx, 'granular-move', E.GRAB2 - 0.05, gain_db=-22, label='diamond taken')
    a(fx, 'riser', E.THROW2, align='end', gain_db=-22, fit=1.6, label='wind-up builds')
    a(fx, 'whoosh-short', E.THROW2, align='peak', gain_db=-15, pan=0.2, label='diamond thrown')
    a(fx, 'whoosh-deep', E.THROW2 - 0.05, gain_db=-19, pan=0.6, fit=1.0, fade_out=0.4, label='diamond flies off hard')
    a(fx, 'riser', E.HIT2, align='end', gain_db=-21, fit=1.2, label='flight builds to the drop')
    # the drop: hit + flex
    a(fx, 'cartoon-hit', E.HIT2, align='peak', gain_db=-12, pan=0.8, label='diamond hits her (off-screen)')
    a(fx, 'sub-drop', E.HIT2, align='peak', gain_db=-16, label='drop boom')
    a(fx, 'glitch-text', E.HIT2 + 0.1, gain_db=-21, label='+1000 AURA')
    a(fx, 'whoosh-short', E.SHADES, align='end', gain_db=-22, label='shades fall')
    a(fx, 'click', E.SHADES, align='peak', gain_db=-16, label='shades on')
    a(fx, 'sparkle', DROP + 0.2, gain_db=-20, label='confetti')
    a(fx, 'coin', DROP + 1.3, gain_db=-22, label='dance')
    a(fx, 'impact', DROP, align='peak', gain_db=-17, label='drop impact flash')
    # pink: her eye fire lights up, «?» pops, anger
    a(fx, 'power-up', E.PINK_IN[1] - 0.2, gain_db=-27, pan=0.5, fit=0.8, fade_out=0.2, label='her eye fire lights up')
    a(fx, 'pop', E.STARE[0] + 0.55, gain_db=-25, pan=0.5, label='? 2')
    a(fx, 'glitch-text', 18.90, gain_db=-24, pan=0.5, label='anger mark')
    a(fx, 'whoosh-short', 9.60, align='peak', gain_db=-25, label='head steps aside')
    return fx


def main():
    kit = sfxkit.Kit(HERE)
    n = int(round(DUR * SR))
    music = voice_review.music_track(n)
    v = voice_review.voice_track(n, stereo=True)
    v *= 0.89 / max(1e-9, np.abs(v).max())
    env = np.convolve(np.abs(v).max(1), np.ones(SR // 20) / (SR // 20), 'same')
    duck = 1 - 0.62 * np.clip(env / 0.03, 0, 1)                    # music −8 dB under speech (author: lines got lost)
    duck = np.convolve(duck, np.ones(SR // 8) / (SR // 8), 'same')
    fx = sfx_layer(n, kit)
    fx *= (1 - 0.4 * np.clip(env / 0.03, 0, 1))[:, None]
    mix = music * 0.40 * duck[:, None] + v * 0.95 + fx              # music quieter overall (author 2026-11-12)
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    out = paths.build(HERE) / 'mix.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save()
    rev = sfxkit.write_review(HERE, fx, mix, None, SR, kit.cues)
    print('build/mix.wav; review:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')


if __name__ == '__main__':
    main()
