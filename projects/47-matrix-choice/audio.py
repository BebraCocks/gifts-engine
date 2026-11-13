"""Voice (Fish drama-3, Morpheus) + the author's track (music.py) + SFX (Botanica V4 via sfxkit, no repeats; drill and
chainsaw from one Fish sound-effect generation, input/ext/) + the complete RubUp sound.
Writes build/mix.wav and, for the author, build/review/{sfx_only,mix,music_only,voice_only}.mp3 + sfx_cues.txt.

One cue = one action on screen (events.py). Tricks run one after another during the real 5 s countdown:
first the NFT, then the thing. No own SFX during RubUp (docs/ADVERTISING.md)."""
import subprocess
import sys
import wave
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import banner
import sound
import sfxkit
from timeline import DUR, ON, END, HAS_NARRATION, TAKES, ROUND_IN, TIMER0, REVEAL, OUTRO
from events import AD_STOP, E, WIN, TRICK_NFT, TRICK_THING, LOSE_T, WIN_GONE, FISTS
import music

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
MUSIC_DB = -9.0            # under the voice; ducks a further 8 dB while Morpheus speaks
CONTENT_GAIN_DB = 5.5      # → ≈ −14 LUFS with the soft limiter below
EXT = HERE / 'input' / 'ext'
SIDE_PAN = (-0.4, 0.4)     # gift on the left (blue), thing on the right (red)


def ext(buf, name, t, seg=None, gain_db=-12.0, pan=0.0, label='', cues=None):
    """A clip from input/ext/ (seg = (start, end) seconds inside the file)."""
    f = EXT / name
    if not f.exists():
        print('нет файла', f, '— звук пропущен:', label)
        return
    x = sound.load_stereo(f, SR)
    if seg:
        x = x[int(seg[0] * SR):int(seg[1] * SR)].copy()
        k = min(len(x) // 4, int(0.03 * SR))
        x[:k] *= np.linspace(0, 1, k)[:, None]
        x[-k:] *= np.linspace(1, 0, k)[:, None]
    i0 = int(t * SR)
    n = min(len(x), len(buf) - i0)
    if n <= 0:
        return
    pl, pr = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2), np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
    g = 10 ** (gain_db / 20)
    buf[i0:i0 + n, 0] += x[:n, 0] * g * min(1.0, pl)
    buf[i0:i0 + n, 1] += x[:n, 1] * g * min(1.0, pr)
    if cues is not None:
        cues.append(dict(t=round(t, 3), at=round(t, 3), align='start', gain_db=gain_db, pan=pan, label=label,
                         role='ext', id=f'input/ext/{name}', file=f'input/ext/{name}', peak=0.0))


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    add = kit.add
    # ---- intro: Morpheus assembled from falling green code (≈ 2 s, fists)
    add(fx, 'scan', 0.0, gain_db=-15, fit=1.9, fade_out=0.4, label='intro: green code pours down')
    add(fx, 'glitch-text', 0.12, gain_db=-19, pan=-0.3, label='intro: data chatter L')
    add(fx, 'glitch-text', 0.50, gain_db=-20, pan=0.3, label='intro: data chatter R')
    add(fx, 'power-up', 0.22, gain_db=-17, fit=1.7, fade_out=0.3, label='intro: the figure charges up')
    add(fx, 'glitch', 1.15, gain_db=-18, label='intro: code → photo')
    add(fx, 'impact', E['formed'], gain_db=-14, align='peak', label='intro: Morpheus formed, fists')
    for r in range(5):
        L, R = SIDE_PAN
        # palms open, the new pair assembles from code; halos light up
        add(fx, 'whoosh-short', ROUND_IN[r], gain_db=-21, label=f'R{r + 1}: fists open')
        add(fx, 'glitch-text', ROUND_IN[r] + 0.05, gain_db=-21, pan=L, label=f'R{r + 1}: NFT assembles (blue)')
        add(fx, 'glitch-text', ROUND_IN[r] + 0.15, gain_db=-21, pan=R, label=f'R{r + 1}: thing assembles (red)')
        add(fx, 'power-up', ROUND_IN[r] + 0.25, gain_db=-24, fit=0.9, fade_out=0.3, label=f'R{r + 1}: halos on')
        # the real 5 s countdown: one tick motif for the whole video, the last second higher
        for s in range(5):
            add(fx, 'click', TIMER0[r] + s, gain_db=-20 + 2 * (s == 4), key='tick', vary=False, semitones=3 * (s == 4),
                label=f'R{r + 1}: timer {5 - s}')
        # reveal
        add(fx, 'impact', REVEAL[r], gain_db=-15, pan=SIDE_PAN[WIN[r]], align='peak', label=f'R{r + 1}: reveal → winner side')
        add(fx, 'coin', REVEAL[r] + 0.10, gain_db=-21, pan=SIDE_PAN[WIN[r]], label=f'R{r + 1}: prices up')
        add(fx, 'select-soft', REVEAL[r] + 0.30, gain_db=-21, label=f'R{r + 1}: score +1')
        # winner dissolves into code, palms close into fists
        add(fx, 'glitch-text', WIN_GONE[r], gain_db=-19, pan=SIDE_PAN[WIN[r]], label=f'R{r + 1}: winner dissolves into code')
        add(fx, 'whoosh-short', FISTS[r], gain_db=-23, label=f'R{r + 1}: palms close into fists')
    # ---- tricks (NFT first, then the thing — once each, during the countdown)
    (a, _), (b, _) = TRICK_NFT[0], TRICK_THING[0]
    add(fx, '*', a, gain_db=-15, pan=-0.4, file='coin-flip-spin-rotation-01', vary=False, label='R1 NFT: signet ring flipped like a coin')
    add(fx, '*', b + 0.55, gain_db=-14, pan=0.4, file='foley/drop.flac', vary=False, label='R1 thing: chess knight lands')
    add(fx, '*', b + 0.95, gain_db=-17, pan=0.4, file='foley/drop.flac', vary=True, semitones=2, label='R1 thing: knight hops again')
    (a, _), (b, _) = TRICK_NFT[1], TRICK_THING[1]
    add(fx, 'whoosh-organic', a + 0.1, gain_db=-21, pan=-0.4, label='R2 NFT: watch swings like a pendulum')
    add(fx, 'whoosh-short', b, gain_db=-19, pan=0.4, label='R2 thing: drill tossed, spins')
    (a, _), (b, _) = TRICK_NFT[2], TRICK_THING[2]
    add(fx, 'spinback', a, gain_db=-19, pan=-0.4, label='R3 NFT: ring spins like a top')
    add(fx, 'sparkle-whoosh', b + 0.3, gain_db=-18, pan=0.4, label='R3 thing: cactus blooms')
    (a, _), (b, _) = TRICK_NFT[3], TRICK_THING[3]
    add(fx, 'sparkle', a + 0.2, gain_db=-17, pan=-0.4, label='R4 NFT: glint across the lenses')
    add(fx, 'stretch', b, gain_db=-17, pan=0.4, label='R4 thing: telescope tube extends')
    add(fx, 'sparkle', b + 1.2, gain_db=-22, pan=0.2, label='R4 thing: a star twinkles above')
    (a, _), (b, _) = TRICK_NFT[4], TRICK_THING[4]
    add(fx, 'whoosh', a, gain_db=-19, pan=-0.4, fit=1.4, fade_out=0.3, label='R5 NFT: cap spins on a finger')
    return fx


def power_tools(fx, cues):
    """Drill (R2) and chainsaw (R5): the Fish sound-effect generation (input/ext/power_tools.mp3) when present,
    otherwise synthesised in code (toolsynth.py)."""
    (b2, _), (b5, _) = TRICK_THING[1], TRICK_THING[4]
    if not (EXT / 'power_tools.mp3').exists():
        import toolsynth
        for t, x, g, lab in ((b2 + 0.75, toolsynth.drill(0.45, 1), -15, 'R2 thing: drill burst 1 (synth)'),
                             (b2 + 1.30, toolsynth.drill(0.40, 3), -15, 'R2 thing: drill burst 2 (synth)'),
                             (b5 + 0.10, toolsynth.chainsaw(), -16, 'R5 thing: chainsaw pull-start, short rev (synth)')):
            i0 = int(t * SR)
            m = min(len(x), len(fx) - i0)
            g_ = 10 ** (g / 20)
            fx[i0:i0 + m, 0] += x[:m, 0] * g_ * 0.85
            fx[i0:i0 + m, 1] += x[:m, 1] * g_ * 1.0
            cues.append(dict(t=round(t, 3), at=round(t, 3), align='start', gain_db=g, pan=0.4, label=lab,
                             role='synth', id='toolsynth.py', file='toolsynth.py', peak=0.0))
        return
    ext(fx, 'power_tools.mp3', b2 + 0.75, POWER['drill1'], -13, 0.4, 'R2 thing: drill burst 1', cues)
    ext(fx, 'power_tools.mp3', b2 + 1.30, POWER['drill2'], -13, 0.4, 'R2 thing: drill burst 2', cues)
    ext(fx, 'power_tools.mp3', b5 + 0.10, POWER['saw'], -14, 0.4, 'R5 thing: chainsaw pull-start, short rev', cues)


POWER = {'drill1': (0.0, 0.5), 'drill2': (1.0, 1.5), 'saw': (2.5, 4.3)}   # set from the file (see STORYBOARD.md)


def defeats(fx, kit):
    add = kit.add
    lose = [1 - w for w in WIN]
    p = lambda r: SIDE_PAN[lose[r]]
    add(fx, 'whoosh-organic', LOSE_T[0], gain_db=-15, pan=p(0), label='R1 defeat: Morpheus blows the chess away')
    add(fx, 'paper', LOSE_T[0] + 0.15, gain_db=-20, pan=p(0), label='R1 defeat: pieces scatter')
    add(fx, '*', LOSE_T[1], gain_db=-14, pan=p(1), file='paper-texture-crunch-distort-05', vary=False, label='R2 defeat: watch crushed in the fist')
    add(fx, 'cartoon-hit', LOSE_T[1] + 0.32, gain_db=-20, pan=p(1), label='R2 defeat: crunch end')
    add(fx, 'downlifter', LOSE_T[2], gain_db=-15, pan=p(2), label='R3 defeat: black hole pulls the cactus in')
    add(fx, 'sub-drop', LOSE_T[2] + 0.75, gain_db=-16, label='R3 defeat: black hole closes')
    add(fx, '*', LOSE_T[3], gain_db=-15, pan=p(3), file='ice-cube', vary=False, label='R4 defeat: lenses crack')
    add(fx, 'glitch', LOSE_T[3] + 0.25, gain_db=-19, pan=p(3), label='R4 defeat: lenses crumble into pixels')
    add(fx, 'glitch-texture', LOSE_T[4], gain_db=-17, pan=p(4), fit=0.8, fade_out=0.2, label='R5 defeat: chainsaw glitches')
    add(fx, 'power-down', LOSE_T[4] + 0.6, gain_db=-17, pan=p(4), label='R5 defeat: squeezed into a pixel cube')
    # teaser before RubUp, outro
    add(fx, 'error', AD_STOP - 0.45, gain_db=-17, label='teaser «НЕ ЛИСТАЙ»: glitch before RubUp')
    add(fx, 'confirm', OUTRO + 0.05, gain_db=-18, label='outro: «ТЕЛЕГА ПОБЕДИЛА 3:2»')
    add(fx, 'scan', E['dissolve'], gain_db=-15, fit=1.3, fade_out=0.4, label='end: Morpheus dissolves into code')
    add(fx, 'power-down', E['dissolve'] + 0.35, gain_db=-16, label='end: the figure powers down')


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2))
    for k, take in enumerate(TAKES):
        d = sound.load_stereo(take, SR)
        s = round(ON[k] * SR)
        c = min(len(d), n - s)
        voice[s:s + c] += d[:c] * 0.9
    fx = sfx_layer(n, kit)
    power_tools(fx, kit.cues)
    defeats(fx, kit)
    mus = music.music(n, SR) * 10 ** (MUSIC_DB / 20)
    env = np.convolve(np.abs(voice).max(1), np.ones(2400) / 2400, 'same')
    k = np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1)
    k = np.convolve(k, np.ones(4800) / 4800, 'same')
    fx *= (1 - 0.4 * k)[:, None]
    mus *= (1 - (1 - 10 ** (-8 / 20)) * k)[:, None]
    g = 10 ** (CONTENT_GAIN_DB / 20)
    return limit((voice + fx + mus) * g), fx * g, mus * g, voice * g


def limit(x, knee=0.70, ceil=0.89):
    """Soft limiter: transparent below the knee, smooth tanh curve up to the ceiling (≈ −1 dBFS)."""
    a = np.abs(x)
    over = a > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (ceil - knee) * np.tanh((a[over] - knee) / (ceil - knee)))
    return y


def mp3(x, path):
    raw = (np.clip(x, -0.98, 0.98) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2',
                    '-i', '-', '-b:a', '192k', str(path)], input=raw, check=True)


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE, seed=zlib.crc32(b'47-matrix-choice'))
    content, fx, mus, voice = make_mix(kit)
    data = BR.audio(content, SR)
    out = paths.build(HERE) / 'mix.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    if '--save' in sys.argv:
        kit.save(BR)                    # records SFX usage (no repeats in later videos) — only for the final mix
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    mp3(BR.audio(mus, SR, banner=False), rev / 'music_only.mp3')
    print('build/mix.wav', round(len(data) / SR, 2), 's;', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')
