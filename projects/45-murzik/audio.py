"""45-murzik sound: the author's track once from its start (every action is on its beat), the voice, SFX from
input/sfx/ via sfxkit. The pack has no cat: the purr and the startled «мяу» are synthesized here (docs/SFX.md allows
this when the library has no fitting sound). No RubUp banner (author, as in 43/44).
Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import wave
import numpy as np
from scipy.signal import butter, lfilter
import sfxkit
import voice_review
import events as E
import timeline as TL
from timeline import DUR

SR = 48000


def purr(dur, seed=7):
    """A cat's purr: ~25 Hz pulses of low noise, breathing in and out."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    breath = np.sin(2 * np.pi * 0.6 * t)
    ph = np.cumsum(25 + 2.5 * breath) / SR
    pulse = (1 - (ph % 1)) ** 3
    noise = rng.normal(0, 1, n)
    body = lfilter(*butter(2, [70, 420], btype='band', fs=SR), noise)
    air = lfilter(*butter(2, [900, 2400], btype='band', fs=SR), noise) * 0.22
    y = (body + air) * pulse * (0.7 + 0.3 * breath) + 0.25 * np.sin(2 * np.pi * 2 * ph) * pulse
    f = int(0.25 * SR)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y / np.abs(y).max()


def meow(dur=0.46, seed=3):
    """A startled «мяу!»: a rising-falling voiced tone through two moving formants, plus a little hiss."""
    n = int(dur * SR)
    u = np.arange(n) / n
    rng = np.random.default_rng(seed)
    f0 = 620 + 520 * np.sin(np.pi * u ** 0.7) ** 1.5 + 14 * np.sin(2 * np.pi * 11 * u * dur)
    ph = 2 * np.pi * np.cumsum(f0) / SR
    src = sum(np.sin(k * ph) / k ** 0.9 for k in range(1, 9))
    out = np.zeros(n)
    hop = SR // 200
    for i in range(0, n, hop):                         # formants glide: «м-я-у»
        v = i / n
        f1, f2 = 900 + 700 * np.sin(np.pi * v), 2900 - 1500 * v
        seg = src[max(0, i - hop):i + hop]
        y = lfilter(*butter(1, [f1 * 0.8, f1 * 1.25], btype='band', fs=SR), seg) + \
            0.6 * lfilter(*butter(1, [f2 * 0.85, f2 * 1.2], btype='band', fs=SR), seg)
        w = np.hanning(len(seg))
        out[max(0, i - hop):i + hop] += y * w
    hiss = lfilter(*butter(2, [3000, 9000], btype='band', fs=SR), rng.normal(0, 1, n)) * 0.25 * (1 - u) ** 2
    env = np.minimum(1, u / 0.06) * (1 - u) ** 0.7
    y = (out / np.abs(out).max() + hiss) * env
    return y / np.abs(y).max()


def put(fx, y, t, gain_db, pan=0.0):
    k = int(t * SR)
    m = min(len(y), len(fx) - k)
    g = 10 ** (gain_db / 20)
    fx[k:k + m, 0] += y[:m] * g * np.sqrt(0.5 * (1 - pan)) * 1.414
    fx[k:k + m, 1] += y[:m] * g * np.sqrt(0.5 * (1 + pan)) * 1.414


def ticks(kit, fx, t0, t1, gain, label, first=0.04, last=0.24, key='roulette', semitones=0.0):
    """Reel / wheel ticks that slow down to the stop."""
    t, k = t0, 0
    while t < t1 - 0.02:
        u = (t - t0) / (t1 - t0)
        kit.add(fx, 'list', t, gain_db=gain - 3 * u + (2 if u > 0.75 else 0), key=key, file='mini-list-one-shot-2', semitones=semitones,
                pan=0.15 * ((-1) ** k),
                label=label if k == 0 else None)
        t += first + (last - first) * u ** 2.0
        k += 1


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    a = kit.add
    cues = []
    # the cat on the palms
    put(fx, purr(TL.SCARE - 0.05), 0.05, -17, 0.3)
    cues.append((0.05, 'synth: purr (cat on the palms)'))
    a(fx, 'impact', TL.SCARE, align='peak', gain_db=-15, label='the cat is startled')
    put(fx, meow(), TL.SCARE + 0.02, -15, 0.3)
    cues.append((TL.SCARE + 0.02, 'synth: startled «мяу!»'))
    a(fx, 'boing', TL.SCARE, gain_db=-22, pan=0.3, file='cartoon-boing.', label='hop')
    a(fx, 'cartoon-move', E.RUN - 0.03, gain_db=-13, pan=0.5, file='run-away.', label='the cat bolts (cartoon run-away)')
    a(fx, 'whoosh-short', E.RUN + 0.2, align='peak', gain_db=-18, pan=0.7, label='out of the frame')
    a(fx, 'whoosh-organic', 2.45, gain_db=-24, pan=0.4, fit=0.8, fade_out=0.3, label='hand reaches after him')
    a(fx, 'whoosh-short', 3.25, align='peak', gain_db=-26, label='zoom to the case tile')
    # cases
    a(fx, 'click', TL.TAP_TILE, align='peak', gain_db=-12, label='tap «Тыква или лампа»')
    a(fx, 'whoosh-short', TL.TAP_TILE + 0.02, align='peak', gain_db=-22, label='cut to the case')
    for k in range(3):
        p, s1, pop = TL.PRESS[k], TL.SPINS[k][1], TL.POP[k]
        a(fx, 'click', p, align='peak', gain_db=-11, key='open', label=f'«Открыть» {k + 1}')
        a(fx, 'whoosh-short', p + 0.05, align='peak', gain_db=-25, label=f'reel starts {k + 1}')
        ticks(kit, fx, p + 0.06, s1, -15, f'reel {k + 1}')
        a(fx, 'impact', pop, align='peak', gain_db=-19 + k, label=f'popup {k + 1}')
        a(fx, 'popup', pop + 0.02, gain_db=-19, label=f'«Ваш подарок» {k + 1}')
        a(fx, 'error', pop + 0.22, gain_db=-17 + k, label=f'not Мурзик {k + 1}')
        a(fx, 'glitch-text', pop + 0.27, gain_db=-23, label=f'stamp «не Мурзик» {k + 1}')
    a(fx, 'power-down', TL.POP[1] + 0.35, gain_db=-23, fit=1.0, fade_out=0.3, label='he droops (sad)')
    a(fx, 'glitch', TL.POP[2] + 0.1, gain_db=-21, label='rage glitch')
    for k, c in enumerate(TL.CLOSE):
        a(fx, 'whoosh-short', c + 0.05, align='peak', gain_db=-26, label=f'popup away {k + 1}')
    # upgrades
    a(fx, 'pop', 16.60, gain_db=-19, label='idea «!»')
    a(fx, 'whoosh-deep', TL.TO_UP - 0.12, gain_db=-20, fit=0.9, fade_out=0.3, label='cut to the upgrades')
    a(fx, 'whoosh-short', 17.0, align='peak', gain_db=-25, pan=-0.4, label='head steps aside')
    a(fx, 'click', TL.TAP_WANT, align='peak', gain_db=-12, label='tap «Хочу получить»')
    a(fx, 'popup', TL.TAP_WANT + 0.03, gain_db=-20, label='sheet slides up')
    for k, t in enumerate(TL.TYPE):
        a(fx, 'typing', t, gain_db=-14, dur=(0.03, 0.2), pan=-0.2 + 0.08 * k, label=f'key «{E.WORD[k]}»')
    a(fx, 'confirm', TL.RESULTS, gain_db=-17, label='found: the cats')
    a(fx, 'sparkle', TL.RESULTS + 0.05, gain_db=-21, label='results sparkle')
    a(fx, 'click', TL.TAP_CAT, align='peak', gain_db=-12, label='tap Purrlion')
    a(fx, 'whoosh-short', TL.TAP_CAT + 0.02, align='peak', gain_db=-22, label='back to the wheel')
    a(fx, 'click', TL.PRESS_UP, align='peak', gain_db=-10, key='open', label='«Улучшить»')
    a(fx, 'riser', TL.WIN, align='end', gain_db=-19, fit=2.0, label='the wheel builds')
    ticks(kit, fx, TL.PRESS_UP + 0.08, TL.WHEEL[1], -16, 'wheel', first=0.05, last=0.30, key='wheel', semitones=-5.0)
    # win: he is back
    a(fx, 'sub-drop', TL.WIN, align='peak', gain_db=-15, label='«Улучшено» boom')
    a(fx, 'impact', TL.WIN, align='peak', gain_db=-16, label='win flash')
    a(fx, 'sparkle', TL.WIN + 0.05, gain_db=-17, label='confetti')
    a(fx, 'glitch-text', TL.WIN + 0.1, gain_db=-22, label='«МУРЗИК!»')
    a(fx, 'sparkle-whoosh', TL.JUMP - 0.05, gain_db=-17, fit=0.7, fade_out=0.2, label='the cat jumps out of the window')
    a(fx, 'boing', TL.JUMP, gain_db=-23, pan=0.2, label='jump')
    a(fx, 'pop', TL.LAND, gain_db=-17, pan=0.3, label='lands on the palms')
    a(fx, 'sparkle', TL.LAND + 0.05, gain_db=-22, pan=0.3, label='landing sparkles')
    put(fx, purr(TL.BOO - TL.LAND - 0.10, seed=9), TL.LAND + 0.12, -14, 0.3)
    # hook tags, the pumpkin «БУ!» at the start and again at the end
    a(fx, 'pop', TL.B(0), gain_db=-20, pan=0.3, label='hook tag «NFT-КОТ»')
    a(fx, 'coin', TL.B(1), gain_db=-21, pan=0.3, label='hook tag «22 975 ★»')
    a(fx, 'cartoon-hit', TL.SCARE - 0.02, align='peak', gain_db=-17, pan=-0.4, label='pumpkin «БУ!»')
    a(fx, 'glitch-text', E.RUN + 0.12, gain_db=-22, label='stamp «СБЕЖАЛ!»')
    a(fx, 'cartoon-hit', TL.BOO, align='peak', gain_db=-14, pan=-0.5, label='pumpkin «БУ!» again')
    a(fx, 'impact', TL.BOO, align='peak', gain_db=-17, label='final scare')
    put(fx, meow(0.5, seed=5), TL.BOO + 0.03, -14, 0.3)
    cues.append((TL.BOO + 0.03, 'synth: startled «мяу!» (final gag)'))
    cues.append((TL.LAND + 0.12, 'synth: purr (home again)'))
    return fx, cues


def main():
    kit = sfxkit.Kit(HERE)
    n = int(round(DUR * SR))
    music = voice_review.music_track(n)
    v = voice_review.voice_track(n, stereo=True)
    v *= 0.89 / max(1e-9, np.abs(v).max())
    env, duck = voice_review.duck_env(v)
    fx, synth = sfx_layer(n, kit)
    fx *= (1 - 0.35 * np.clip(env / 0.03, 0, 1))[:, None]
    mix = music * voice_review.MUSIC_GAIN * duck[:, None] + v * 0.95 + fx
    mix /= max(1.0, np.abs(mix).max() / 0.97)
    out = paths.build(HERE) / 'mix.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save()
    rev = sfxkit.write_review(HERE, fx, mix, None, SR, kit.cues)
    with open(rev / 'sfx_cues.txt', 'a', encoding='utf-8') as f:
        for t, label in synth:
            f.write(f'{t:7.2f}  {label}\n')
    print('build/mix.wav; review:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')


if __name__ == '__main__':
    main()
