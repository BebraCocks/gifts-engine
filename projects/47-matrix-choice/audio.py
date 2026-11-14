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
from events import AD_STOP, E, WIN, TRICK, LOSE_T, WIN_GONE, FISTS, CRUSH, HOOK_OPEN, REEL_T, REEL_LAND, EGGS, EGG_HOLD, GLITCH_MODE
from words import wt
HOOK_SLAM_T = wt(0, 'Угадай') - 0.04
import music

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
MUSIC_DB = -16.0           # author: the music was too loud; ducks a further 8 dB under the voice
CONTENT_GAIN_DB = 8.0      # → ≈ −14 LUFS with the soft limiter below
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


def synth(buf, cues, x, t, gain_db, pan, label):
    i0 = int(t * SR)
    m = min(len(x), len(buf) - i0)
    if m <= 0:
        return
    g = 10 ** (gain_db / 20)
    pl, pr = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2), np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
    buf[i0:i0 + m, 0] += x[:m, 0] * g * min(1.0, pl)
    buf[i0:i0 + m, 1] += x[:m, 1] * g * min(1.0, pr)
    cues.append(dict(t=round(t, 3), at=round(t, 3), align='start', gain_db=gain_db, pan=pan, label=label,
                     role='synth', id='toolsynth.py', file='toolsynth.py', peak=0.0))


def sfx_layer(n, kit):
    """One cue = one action on screen (events.py, render.py)."""
    import toolsynth
    fx = np.zeros((n, 2))
    add = kit.add
    L, R = SIDE_PAN
    # ---- intro: Morpheus assembled from falling green code (≈ 2 s, fists)
    add(fx, 'scan', 0.0, gain_db=-15, fit=1.3, fade_out=0.4, label='intro: green code pours down')
    add(fx, 'glitch-text', 0.12, gain_db=-19, pan=-0.3, label='intro: data chatter L')
    add(fx, 'glitch-text', 0.40, gain_db=-20, pan=0.3, label='intro: data chatter R')
    add(fx, 'power-up', 0.15, gain_db=-17, fit=1.15, fade_out=0.3, label='intro: the figure charges up')
    add(fx, 'glitch', 0.80, gain_db=-18, label='intro: code → photo')
    add(fx, 'impact', E['formed'], gain_db=-14, align='peak', label='intro: Morpheus formed, fists')
    # hook: fists open, the reels spin (a reel tick per switch, slowing down), a ding when they land on round 1
    add(fx, '*', HOOK_OPEN, gain_db=-19, file='friction-movement-transform-01', vary=False, label='hook: fists open')
    for i, ts in enumerate(REEL_T[:-1]):
        add(fx, 'click', ts, gain_db=-19 + 0.25 * i, key='reel', vary=False, semitones=-2 + 0.25 * i,
            pan=-0.35 if i % 2 else 0.35, label=f'hook: reel switch {i + 1}')
    add(fx, 'confirm', REEL_LAND, gain_db=-14, label='hook: the reels land on the lamp and the chess')
    add(fx, 'impact', HOOK_SLAM_T, gain_db=-13, align='peak', label='hook: «УГАДАЙ, ЧТО ДОРОЖЕ» slams in')
    for r in range(5):
        # fists open (skin/cloth friction), the pair assembles from code, auras flash on (round 1: palms already open)
        if r:
            add(fx, '*', ROUND_IN[r], gain_db=-20, file='friction-movement-transform-02', vary=False, label=f'R{r + 1}: fists open')
        if r:
            add(fx, 'glitch-text', ROUND_IN[r] + 0.08, gain_db=-21, pan=L, label=f'R{r + 1}: NFT assembles (blue)')
            add(fx, 'glitch-text', ROUND_IN[r] + 0.18, gain_db=-21, pan=R, label=f'R{r + 1}: thing assembles (red)')
            add(fx, 'power-up', ROUND_IN[r] + 0.30, gain_db=-22, fit=0.9, fade_out=0.3, label=f'R{r + 1}: auras flash on')
        for s_ in range(5):                         # the real 5 s countdown, one tick motif, last second higher
            add(fx, 'click', TIMER0[r] + s_, gain_db=-20 + 2 * (s_ == 4), key='tick', vary=False, semitones=3 * (s_ == 4),
                label=f'R{r + 1}: timer {5 - s_}')
        add(fx, 'impact', REVEAL[r], gain_db=-15, pan=SIDE_PAN[WIN[r]], align='peak', label=f'R{r + 1}: reveal → winner side')
        add(fx, 'coin', REVEAL[r] + 0.10, gain_db=-21, pan=SIDE_PAN[WIN[r]], label=f'R{r + 1}: prices up')
        add(fx, 'select-soft', REVEAL[r] + 0.30, gain_db=-21, label=f'R{r + 1}: score +1')
        add(fx, 'glitch-text', WIN_GONE[r], gain_db=-19, pan=SIDE_PAN[WIN[r]], label=f'R{r + 1}: winner dissolves into code')
        add(fx, '*', FISTS[r], gain_db=-21, file='friction-movement-transform-03', vary=False, label=f'R{r + 1}: palms close into fists')
    # ---- one trick per round, alternating NFT / thing (events.TRICK)
    def at(r, u):
        w0, w1 = TRICK[r]
        return w0 + u * (w1 - w0)
    add(fx, '*', at(0, 0.0), gain_db=-17, pan=L, file='friction.flac', vary=False, label='R1: the genie lamp is rubbed, sways')
    add(fx, 'sparkle-whoosh', at(0, 0.33), gain_db=-17, pan=L, label='R1: magic stirs in the lamp')
    add(fx, 'transform', at(0, 0.40), gain_db=-18, pan=-0.2, label='R1: green code smoke curls up from the spout')
    add(fx, 'whoosh-short', at(1, 0.0), gain_db=-17, pan=R, label='R2: drill tossed, one tumble')
    add(fx, 'cartoon-hit', at(1, 0.34), gain_db=-19, pan=R, label='R2: drill caught')
    synth(fx, kit.cues, toolsynth.drill(0.15 * (TRICK[1][1] - TRICK[1][0]), 1), at(1, 0.40), -14, R, 'R2: drill burst 1 (synth)')
    synth(fx, kit.cues, toolsynth.drill(0.14 * (TRICK[1][1] - TRICK[1][0]), 3), at(1, 0.66), -14, R, 'R2: drill burst 2 (synth)')
    add(fx, 'riser', at(2, 0.0), gain_db=-19, pan=L, fit=2.6, fade_out=0.6, label='R3: black hole ring levitates, code spirals in')
    add(fx, 'whoosh-deep', at(2, 0.75), gain_db=-19, pan=L, label='R3: ring settles')
    add(fx, 'stretch', at(3, 0.08), gain_db=-19, pan=R, label='R4: telescope adjusts toward the star')
    add(fx, 'sparkle-whoosh', TRICK[3][0] + 1.2, gain_db=-17, pan=-0.2, label='R4: shooting star crosses')
    add(fx, 'whoosh-short', at(4, 0.0), gain_db=-17, pan=L, label='R5: cap tossed, tumbling')
    add(fx, 'pop', at(4, 0.42), gain_db=-17, pan=L, label='R5: cap lands on the fingertip')
    add(fx, 'spinback', at(4, 0.5), gain_db=-21, pan=L, label='R5: cap balances, spinning')
    add(fx, 'whoosh-short', at(4, 0.86), gain_db=-19, pan=L, label='R5: cap flicked back to the palm')
    # more sound design: a riser into every reveal, a sub hit on it, glitches on round changes, keys on the score
    for r in range(5):
        add(fx, 'riser', REVEAL[r] - 1.25, gain_db=-23, fit=1.25, fade_out=0.05, label=f'R{r + 1}: tension rises into the reveal')
        add(fx, 'sub-drop', REVEAL[r] + 0.02, gain_db=-19, label=f'R{r + 1}: sub hit on the reveal (screen punch)')
        add(fx, 'key-enter', REVEAL[r] + 0.32, gain_db=-22, label=f'R{r + 1}: the score line updates')
        for side in (0, 1) if r else ():
            add(fx, 'sparkle', ROUND_IN[r] + 0.32 + 0.1 * side, gain_db=-25, pan=SIDE_PAN[side], label=f'R{r + 1}: code sparks burst ({"NFT" if side == 0 else "thing"})')
    for g0 in [f + 0.12 for f in FISTS[:4]] + [OUTRO - 0.05]:
        add(fx, 'glitch', g0, gain_db=-21, label='RGB glitch between rounds')
    # background interference with an easter egg decoding out of the rain
    for (t0, phrase, side), mode in zip(EGGS, GLITCH_MODE):
        add(fx, 'glitch', t0, gain_db=-18, pan=-0.5 if side == 0 else 0.5, label=f'interference on the code («{phrase.replace("|", " ")}»)')
        if mode == 'stutter':
            add(fx, 'glitch-texture', t0, gain_db=-20, fit=0.45, fade_out=0.08, label='the code stutters')
        elif mode == 'reverse':
            add(fx, 'spinback', t0, gain_db=-18, label='the code runs backwards for a moment')
        elif mode == 'failure':
            add(fx, 'error', t0 + 0.02, gain_db=-17, label='«СБОЙ МАТРИЦЫ» flickers')
        elif mode == 'deja':
            add(fx, 'voice', t0 + 0.35, gain_db=-22, file='cute-vocal', vary=False, label='déjà vu: a black cat walks by')
            add(fx, 'glitch', t0 + 1.15, gain_db=-17, label='déjà vu: the glitch')
            add(fx, 'voice', t0 + 1.55, gain_db=-22, file='cute-vocal', vary=False, label='déjà vu: the same cat again')
        add(fx, 'glitch-text', t0 + 0.08, gain_db=-21, pan=-0.6 if side == 0 else 0.6, label='the easter egg decodes')
        add(fx, 'glitch-text', t0 + EGG_HOLD, gain_db=-24, pan=-0.6 if side == 0 else 0.6, label='it falls back into digits')
    # bullet time in the final countdown
    add(fx, 'downlifter', TIMER0[4] - 0.2, gain_db=-19, label='R5: bullet time — the code slows down')
    add(fx, 'riser', REVEAL[4] - 0.9, gain_db=-20, fit=0.9, fade_out=0.1, label='R5: time resumes on the answer')
    return fx


def defeats(fx, kit):
    """The loser's own defeat, with its characteristic sounds (author: «по-настоящему, с характерными звуками»)."""
    import toolsynth
    add = kit.add
    L, R = SIDE_PAN
    p = lambda r: SIDE_PAN[1 - WIN[r]]
    # R1: Morpheus turns to the chess and blows: breath + gust, the board scrapes off, pieces clatter
    synth(fx, kit.cues, toolsynth.blow(0.6), LOSE_T[0] - 0.02, -11, 0.2, 'R1: strong blow «ффф» (synth)')
    ext(fx, 'wind_gale.mp3', LOSE_T[0] + 0.02, (6.0, 7.1), -12, 0.5, 'R1: gust of wind (Fish library «Wind 5»)', kit.cues)
    add(fx, '*', LOSE_T[0] + 0.14, gain_db=-15, pan=0.6, file='friction.flac', vary=False, label='R1: board scrapes off the palm')
    for j, dt in enumerate((0.18, 0.24, 0.33, 0.41, 0.52)):
        add(fx, '*', LOSE_T[0] + dt, gain_db=-16 - j, pan=0.5 + 0.08 * j, file='foley/drop.flac', vary=False,
            semitones=4 - 2 * j, label=f'R1: wooden pieces clatter {j + 1}')
    # R2: crushed in the fist: crunch while it shakes, the fist opens, crumbs trickle off the tilted palm
    add(fx, 'cartoon-hit', LOSE_T[1] + CRUSH['close'][1] - 0.04, gain_db=-16, pan=p(1), label='R2: the fist closes on the watch')
    add(fx, '*', LOSE_T[1] + CRUSH['shake'][0], gain_db=-12, pan=p(1), file='paper-texture-crunch-distort-05', vary=False, label='R2: crunch while the fist shakes')
    add(fx, '*', LOSE_T[1] + CRUSH['shake'][0] + 0.15, gain_db=-15, pan=p(1), file='ice-cube', vary=False, label='R2: watch glass cracks inside')
    add(fx, '*', LOSE_T[1] + CRUSH['turn'][0], gain_db=-19, pan=p(1), file='friction-movement-transform-02', vary=True,
        label='R2: the fist turns over, back of the hand up')
    add(fx, 'whoosh-short', LOSE_T[1] + CRUSH['open'][0], gain_db=-22, pan=p(1), label='R2: the hand opens palm-down')
    add(fx, 'granular-move', LOSE_T[1] + CRUSH['drop'][0], gain_db=-17, pan=p(1), fit=1.0, fade_out=0.4,
        label='R2: metal dust pours out of the hand')
    for j in range(4):
        add(fx, '*', LOSE_T[1] + CRUSH['drop'][0] + 0.12 + 0.1 * j, gain_db=-24 - j, pan=p(1), file='foley/drop.flac',
            vary=False, semitones=10 + j, label=f'R2: tiny glass glints fall {j + 1}')
    # R3: the ring's black hole pulls the cactus in
    add(fx, 'downlifter', LOSE_T[2], gain_db=-14, pan=0.0, label='R3: black hole pulls the cactus across')
    add(fx, 'sub-drop', LOSE_T[2] + 1.05, gain_db=-15, pan=L, label='R3: swallowed, the hole closes')
    # R4: lenses crack, the glasses break and fall
    add(fx, '*', LOSE_T[3], gain_db=-14, pan=p(3), file='ice-cube', vary=True, semitones=-2, label='R4: lenses crack')
    add(fx, 'glitch', LOSE_T[3] + 0.36, gain_db=-20, pan=p(3), label='R4: the glasses break into pieces')
    for j in range(4):
        add(fx, '*', LOSE_T[3] + 0.6 + 0.07 * j, gain_db=-22 - j, pan=p(3), file='foley/drop.flac', vary=False, semitones=9 + j,
            label=f'R4: pieces fall {j + 1}')
    # R5: the chainsaw overheats (hiss, sparks) and explodes
    add(fx, 'glitch-texture', LOSE_T[4], gain_db=-19, pan=p(4), fit=0.62, fade_out=0.1, label='R5: chainsaw overheats, sizzles')
    add(fx, 'power-down', LOSE_T[4] + 0.15, gain_db=-20, pan=p(4), label='R5: the engine chokes, smoke')
    add(fx, 'riser', LOSE_T[4] + 0.05, gain_db=-21, fit=0.57, fade_out=0.02, label='R5: pressure builds')
    add(fx, 'impact', LOSE_T[4] + 0.62, gain_db=-8, align='peak', pan=p(4), label='R5: EXPLOSION')
    add(fx, '*', LOSE_T[4] + 0.62, gain_db=-10, pan=p(4), file='demolition', vary=False, label='R5: blast and debris')
    add(fx, 'sub-drop', LOSE_T[4] + 0.64, gain_db=-11, label='R5: the boom in the chest')
    for j in range(4):
        add(fx, '*', LOSE_T[4] + 1.2 + 0.11 * j, gain_db=-20 - j, pan=0.6 - 0.3 * j, file='foley/drop.flac', vary=False,
            semitones=-3 + 2 * j, label=f'R5: debris lands {j + 1}')
    # teaser before RubUp, outro, finale
    add(fx, 'error', AD_STOP - 0.45, gain_db=-17, label='teaser «НЕ ЛИСТАЙ»: glitch before RubUp')
    add(fx, 'confirm', OUTRO + 0.05, gain_db=-18, label='outro: «ТЕЛЕГА ПОБЕДИЛА 3:2»')
    add(fx, '*', OUTRO + 0.35, gain_db=-21, file='friction-movement-transform-01', vary=False, label='outro: palms open')
    add(fx, 'glitch-text', OUTRO + 0.55, gain_db=-20, label='outro: blue and red pills appear')
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
