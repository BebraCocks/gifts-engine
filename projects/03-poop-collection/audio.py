"""Narration (Fish Audio takes) + synthesised SFX from the shared events + the complete RubUp sound.
No external SFX/music files: every effect is generated here, deterministically (seeded)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
sys.path.insert(0, str(HERE))
import numpy as np
import wave
from scipy.signal import butter, sosfilt
import banner
import sound
import config
from timeline import DUR, ON, END, HAS_NARRATION, TAKES
from events import AD_STOP, HOOK_MOVE, TRANSITS, PULLBACK, HEROES_T, FINAL, LIGHT_ON

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
RNG = np.random.default_rng(2025)


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], 'band', fs=SR, output='sos'), x)


def whoosh(dur, lo=300, hi=2400, rise=0.5):
    """Filtered-noise swish with a pitch sweep (camera turns)."""
    n = int(dur * SR)
    x = RNG.standard_normal(n)
    out = np.zeros(n)
    seg = SR // 50
    for i in range(0, n, seg):
        u = i / n
        f = lo + (hi - lo) * (np.sin(np.pi * u) if rise else u)
        out[i:i + seg] = bp(x[i:i + seg + 400], f * 0.7, f * 1.3)[:len(out[i:i + seg])]
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return out * shape / (np.abs(out).max() + 1e-9)


def flush(dur=1.3):
    """Toilet-flush swirl: low gurgle noise with a fast tremolo, descending."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = bp(RNG.standard_normal(n), 180, 1400)
    trem = 0.6 + 0.4 * np.sin(2 * np.pi * (14 - 6 * t / dur) * t)
    shape = np.minimum(1, t / 0.08) * np.exp(-t / (dur * 0.45))
    return x * trem * shape / (np.abs(x).max() + 1e-9)


def plop():
    """Wet «plop»: a sine that drops in pitch, plus a tiny click (stamps)."""
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 520 * np.exp(-t * 18) + 90
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env(n, 0.003, 0.08)
    thump = np.sin(2 * np.pi * 60 * t) * env(n, 0.002, 0.12)
    click = bp(RNG.standard_normal(n), 2000, 6000) * env(n, 0.0005, 0.006)
    return 0.7 * body + 0.6 * thump + 0.25 * click


def chime():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    out = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
              for f, a, d in ((1318.5, 0.5, 0.9), (1975.5, 0.3, 0.6), (2637, 0.2, 0.4), (659.3, 0.3, 1.2)))
    return out * np.minimum(1, t / 0.004)


def buzz(dur):
    """A fly: buzzing sawtooth ~190 Hz with wandering pitch and amplitude."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 190 + 25 * np.sin(2 * np.pi * 0.7 * t) + 12 * np.sin(2 * np.pi * 3.1 * t)
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    am = 0.55 + 0.45 * np.sin(2 * np.pi * 0.43 * t + 1) ** 2
    x = bp(saw, 150, 3000) * am
    return x * np.minimum(1, np.minimum(t, dur - t) / 0.3)


def click():
    n = int(0.06 * SR)
    return bp(RNG.standard_normal(n), 1500, 7000) * env(n, 0.0005, 0.01) + \
        np.sin(2 * np.pi * 120 * np.arange(n) / SR) * env(n, 0.001, 0.02) * 0.5


def hum(n):
    """Fluorescent hum bed (100 Hz + harmonics), very quiet."""
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 100 * t) + 0.4 * np.sin(2 * np.pi * 200 * t) + 0.15 * np.sin(2 * np.pi * 300 * t)) / 1.6


def add(mix, x, at, gain, pan=0.0):
    i = int(round(at * SR))
    if i >= len(mix) or len(x) == 0:
        return
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(mix) - i)
    l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    mix[i:i + n, 0] += x[:n] * gain * l * 1.414
    mix[i:i + n, 1] += x[:n] * gain * r * 1.414


def make_mix():
    n = int(round(DUR * SR))
    mix = np.zeros((n, 2))
    voice = np.zeros(n)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR).mean(1)
            i = round(ON[k] * SR)
            m = min(len(data), n - i)
            voice[i:i + m] += data[:m] * config.VOICE_GAIN
    else:
        print('Дикторской озвучки нет: текст на экране + звук баннера.')
    # ---- SFX (content time)
    sfx = np.zeros((n, 2))
    add(sfx, whoosh(HOOK_MOVE[1], 200, 1600, rise=0), 0.0, 0.22)            # the rush down the corridor
    add(sfx, buzz(4.6), 0.2, 0.05, pan=-0.3)
    add(sfx, buzz(3.0), 9.0, 0.035, pan=0.4)
    add(sfx, buzz(3.5), 22.5, 0.04, pan=0.3)
    for a, b in TRANSITS:
        add(sfx, flush(min(1.4, b - a + 0.3)), a - 0.05, 0.2)
    for k, h in enumerate(HEROES_T):
        add(sfx, plop(), h['stamp'] - 0.01, 0.55)
        add(sfx, click(), LIGHT_ON[k], 0.3)
    add(sfx, chime(), HEROES_T[0]['swap'], 0.18)
    add(sfx, chime(), HEROES_T[4]['stamp'] + 0.05, 0.3)
    add(sfx, whoosh(2.5, 250, 1200), PULLBACK[0], 0.14)
    for j, key in enumerate(('toilet', 'paper')):
        for q in range(5):
            add(sfx, plop() * 0.6, FINAL[key] + 0.06 * q, 0.22, pan=-0.8 + 0.4 * q)
    add(sfx, chime(), FINAL['cta'], 0.15)
    bed = hum(n) * 0.012
    sfx[:, 0] += bed
    sfx[:, 1] += bed
    # ---- duck SFX under the voice (sidechain from the voice envelope)
    e = np.abs(voice)
    k = SR // 50
    e = np.convolve(e, np.ones(k) / k, mode='same')
    duck = 1 - 0.45 * np.clip(e / 0.05, 0, 1)
    mix += sfx * duck[:, None]
    mix += voice[:, None]
    fade = np.clip((DUR - np.arange(n) / SR) / 0.3, 0, 1)
    mix *= fade[:, None]
    pk = np.abs(mix).max()
    if pk > 0.9:
        mix *= 0.9 / pk
    return BR.audio(mix, SR)


if __name__ == '__main__':
    data = make_mix()
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    print('build/mix.wav готов', round(len(data) / SR, 2), 'с')
