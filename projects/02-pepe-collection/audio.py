"""Voice + synthesized SFX and ambience on the same content-time events as render.py; RubUp sound kept whole.

All effects are generated here (no third-party sound files). Final mix is loudness-normalised (-14 LUFS)."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
from scipy.signal import butter, sosfilt
import banner
import sound
from timeline import DUR, ON, HAS_NARRATION, TAKES
from events import AD_STOP

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
RNG = np.random.default_rng(7)


def n_(sec):
    return int(round(sec * SR))


def env(n, a=0.005, r=0.2, curve=4.0):
    """Attack-release envelope over n samples."""
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    rel = np.exp(-curve * np.clip(t - a, 0, None) / max(r, 1e-4))
    return att * rel


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)


def noise(sec):
    return RNG.standard_normal(n_(sec))


def norm(x, peak=1.0):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def sweep_noise(sec, f0, f1, width=0.6, blocks=48):
    """Noise through a band-pass whose centre glides f0 -> f1 (a whoosh)."""
    x = noise(sec)
    out = np.zeros_like(x)
    edges = np.linspace(0, len(x), blocks + 1).astype(int)
    for k in range(blocks):
        fc = f0 * (f1 / f0) ** (k / max(1, blocks - 1))
        lo, hi = max(40, fc * (1 - width)), min(SR / 2 - 100, fc * (1 + width))
        seg = slice(max(0, edges[k] - 2048), edges[k + 1])
        y = bp(x[seg], lo, hi)
        out[edges[k]:edges[k + 1]] = y[-(edges[k + 1] - edges[k]):]
    return out


def whoosh(sec=0.6, f0=300, f1=2500):
    x = sweep_noise(sec, f0, f1)
    t = np.linspace(0, 1, len(x))
    return norm(x * np.sin(np.pi * t) ** 1.5)


def thud(f=70, sec=0.5):
    t = np.arange(n_(sec)) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-t * 30))) / SR
    x = np.sin(ph) * np.exp(-t * 9) + 0.4 * lp(noise(sec), 400) * np.exp(-t * 25)
    return norm(x)


def pop(f=900, sec=0.15):
    t = np.arange(n_(sec)) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 1.2 * np.exp(-t * 60))) / SR
    return norm(np.sin(ph) * np.exp(-t * 35) + 0.3 * hp(noise(sec), 2000) * np.exp(-t * 80))


def ding(freqs=(1568, 2093), sec=0.9):
    t = np.arange(n_(sec)) / SR
    x = sum(np.sin(2 * np.pi * f * t + i) * np.exp(-t * (4 + i)) for i, f in enumerate(freqs))
    x += 0.3 * np.sin(2 * np.pi * freqs[0] * 2.76 * t) * np.exp(-t * 9)
    return norm(x * np.clip(t / 0.003, 0, 1))


def coins(sec=0.8):
    out = np.zeros(n_(sec))
    for k in range(7):
        s = ding((2093 * (1 + 0.06 * RNG.standard_normal()), 2637), 0.35)
        i = n_(k * 0.06 + 0.01 * RNG.random())
        out[i:i + len(s)] += s[:len(out) - i] * (0.9 - 0.08 * k)
    return norm(out)


def boing(sec=0.35, f0=220, f1=520):
    t = np.arange(n_(sec)) / SR
    f = f0 + (f1 - f0) * (1 - np.exp(-t * 18)) + 25 * np.sin(2 * np.pi * 14 * t)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7))


def whistle_fall(sec=0.5, f0=1800, f1=500):
    t = np.arange(n_(sec)) / SR
    f = f0 * (f1 / f0) ** (t / sec)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.clip(t / 0.05, 0, 1) * (0.6 + 0.4 * t / sec))


def engine(sec, f0=45, f1=90, rough=0.5):
    t = np.arange(n_(sec)) / SR
    f = f0 + (f1 - f0) * np.clip(t / sec, 0, 1) ** 1.5
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * h) / h for h in range(1, 8))
    x *= 1 + rough * np.sin(ph * 0.5)
    return norm(lp(x, 900) * np.clip(t / 0.08, 0, 1))


def whir(sec, f0=520, f1=880):
    t = np.arange(n_(sec)) / SR
    f = f0 + (f1 - f0) * np.clip(t / sec, 0, 1)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.25 * bp(noise(sec), 800, 2500)
    return norm(x * np.clip(t / 0.1, 0, 1))


def splash(sec=0.9):
    t = np.arange(n_(sec)) / SR
    x = bp(noise(sec), 400, 3500) * np.exp(-t * 6)
    for k in range(10):
        b = bubble(0.08 + 0.05 * RNG.random(), 300 + 500 * RNG.random())
        i = n_(0.05 + 0.6 * RNG.random())
        x[i:i + len(b)] += 0.4 * b[:len(x) - i]
    return norm(x)


def bubble(sec=0.1, f=500):
    t = np.arange(n_(sec)) / SR
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 2 * t / sec)) / SR) * np.sin(np.pi * t / sec)


def bubbles(sec, rate=18):
    x = np.zeros(n_(sec))
    for k in range(int(sec * rate)):
        b = bubble(0.05 + 0.08 * RNG.random(), 250 + 700 * RNG.random())
        i = n_(sec * RNG.random())
        x[i:i + len(b)] += b[:len(x) - i] * (0.4 + 0.6 * RNG.random())
    return norm(x)


def roar(sec, lo=60, hi=900, crescendo=True):
    t = np.linspace(0, 1, n_(sec))
    x = bp(noise(sec), lo, hi) * ((0.2 + 0.8 * t) if crescendo else 1.0)
    crackle = (RNG.random(len(x)) > 0.9985) * RNG.standard_normal(len(x)) * 3
    return norm(x + hp(crackle, 1500) * 0.4)


def hiss(sec):
    t = np.linspace(0, 1, n_(sec))
    return norm(hp(noise(sec), 3000) * np.sin(np.pi * t) ** 0.5)


def horn(sec=0.22, f=(415, 523)):
    t = np.arange(n_(sec)) / SR
    x = sum(np.sign(np.sin(2 * np.pi * fr * t)) for fr in f)
    return norm(lp(x, 2500) * np.clip(t / 0.01, 0, 1) * np.clip((sec - t) / 0.03, 0, 1))


def scribble(sec):
    x = hp(noise(sec), 2500)
    t = np.arange(len(x)) / SR
    return norm(x * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t) ** 2))


def rustle(sec=0.6):
    t = np.linspace(0, 1, n_(sec))
    return norm(bp(noise(sec), 1500, 7000) * (np.abs(np.sin(np.pi * t * 5)) ** 3) * np.sin(np.pi * t))


def scare(sec=0.45):
    t = np.arange(n_(sec)) / SR
    f = 900 + 600 * np.sin(2 * np.pi * 9 * t)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4) + 0.6 * hp(noise(sec), 2500) * np.exp(-t * 8))


# ---------------------------------------------------------------- ambience beds
def amb_swamp(sec):
    t = np.arange(n_(sec)) / SR
    crick = np.sin(2 * np.pi * 4600 * t) * (np.sin(2 * np.pi * 28 * t) > 0.6) * (np.sin(2 * np.pi * 0.7 * t) > 0)
    crick2 = np.sin(2 * np.pi * 5200 * t) * (np.sin(2 * np.pi * 33 * t + 1) > 0.7) * (np.sin(2 * np.pi * 0.45 * t + 2) > 0.2)
    air = lp(noise(sec), 500)
    x = 0.25 * crick + 0.18 * crick2 + 0.5 * norm(air)
    for k in range(int(sec / 2.2)):                       # distant frog croaks
        c = norm(np.sin(2 * np.pi * np.cumsum(np.full(n_(0.18), 140.0)) / SR) * np.sin(2 * np.pi * 25 * np.arange(n_(0.18)) / SR))
        i = n_(k * 2.2 + 0.9 * RNG.random())
        x[i:i + len(c)] += 0.35 * c[:len(x) - i] * np.hanning(len(c))[:len(x) - i]
    return norm(x)


def amb_city(sec):
    x = lp(noise(sec), 300) * 1.0 + 0.2 * bp(noise(sec), 300, 1200)
    t = np.arange(len(x)) / SR
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.13 * t)
    return norm(x)


def amb_sewer(sec):
    x = 0.6 * norm(lp(noise(sec), 150))
    for k in range(int(sec * 1.6)):                       # drips with a short echo
        f = 900 + 900 * RNG.random()
        d = np.sin(2 * np.pi * np.cumsum(f * (1 + 2.5 * np.linspace(0, 1, n_(0.06)))) / SR) * np.exp(-np.arange(n_(0.06)) / SR * 50)
        i = n_(sec * RNG.random())
        for e, g in ((0, 0.5), (0.11, 0.25), (0.23, 0.12)):
            j = i + n_(e)
            if j < len(x):
                x[j:j + len(d)] += g * d[:len(x) - j]
    return norm(x)


def amb_space(sec):
    t = np.arange(n_(sec)) / SR
    x = sum(np.sin(2 * np.pi * f * t + p) * (0.6 + 0.4 * np.sin(2 * np.pi * l * t)) for f, p, l in
            ((55, 0, 0.07), (82.4, 1, 0.11), (110, 2, 0.05), (164.8, 3, 0.09)))
    x += 0.15 * lp(noise(sec), 2000) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.2 * t))
    return norm(x)


def amb_kitchen(sec):
    return norm(0.6 * bubbles(sec, rate=22) + 0.4 * norm(lp(noise(sec), 400)) + 0.15 * norm(hp(noise(sec), 4000)))


# ---------------------------------------------------------------- event map (content seconds), gains in dB
def db(g):
    return 10 ** (g / 20)


S = [20.30, 29.19, 37.30, 45.70]
EVENTS = [
    # hook
    (0.00, rustle(0.7), -26), (0.35, thud(60, 0.5), -16), (1.40, scribble(1.2), -30), (3.27, pop(700), -18),
    (5.10, thud(60, 0.5), -16), *[(6.75 + 0.055 * k, pop(1100 + 40 * k, 0.08), -30) for k in range(18)],
    (8.30, whoosh(1.2, 250, 1800), -16),
    # swamp
    (11.45, boing(0.4, 300, 420), -24), (12.60, ding((1318, 1760), 0.6), -28),
    (17.90, whistle_fall(0.45), -24), (18.35, thud(55, 0.7), -12), (18.35, splash(0.8), -20),
    (18.05, coins(), -20), (19.20, boing(), -20), (19.65, engine(0.7, 40, 85), -16), (19.95, whoosh(0.6, 400, 3000), -14),
    # street
    (20.30, engine(0.7, 85, 45), -18), (20.85, hiss(0.25), -28), (21.45, ding((1318, 1760), 0.6), -28),
    (23.95, scare(), -18), (24.30, pop(800), -18), (24.45, coins(), -20), (25.20, boing(), -20),
    (26.00, whir(1.55), -20), (27.55, whistle_fall(0.9, 1500, 300), -20), (28.20, thud(45, 0.6), -22),
    # sewer
    (29.62, splash(1.0), -12), (30.50, whoosh(0.4, 600, 3000), -20), (30.55, pop(500, 0.2), -18),
    (31.55, ding((1318, 1760), 0.6), -28), (33.75, ding((880, 1175), 0.9), -22),
    (35.30, bubbles(1.0), -18), (36.25, roar(1.2, 60, 1200), -12), (36.40, whoosh(0.9, 300, 4000), -14),
    # space
    (37.30, whoosh(0.6, 3000, 600), -18), (39.85, ding((1568, 2093, 2637), 1.2), -26),
    (42.65, pop(800), -18), (42.65, coins(), -20), (44.20, boing(), -20), (44.55, roar(1.3, 80, 2000, False), -12),
    (44.60, whoosh(1.1, 200, 1500), -16),
    # kitchen
    (45.70, hiss(0.8), -18), (46.05, thud(80, 0.5), -16), (46.35, ding((1318, 1760), 0.6), -28),
    (48.55, pop(900), -18), (48.55, coins(), -20), (48.90, horn(), -20), (49.20, horn(), -20), (49.30, boing(), -20),
    (50.95, engine(0.8, 50, 110), -18), (51.06, pop(700), -16), (51.30, ding((1046, 1318, 1568), 1.4), -22),
]
BEDS = [(8.8, S[0], amb_swamp, -30), (S[0], S[1], amb_city, -30), (S[1], S[2], amb_sewer, -28),
        (S[2], S[3], amb_space, -26), (S[3], DUR, amb_kitchen, -32)]


def place_mono(mix, x, t0, gain_db, pan=0.0):
    i = n_(t0)
    if i >= len(mix):
        return
    x = x[:len(mix) - i] * db(gain_db)
    mix[i:i + len(x), 0] += x * (1 - max(0, pan))
    mix[i:i + len(x), 1] += x * (1 + min(0, pan))


def make_mix():
    mix = np.zeros((n_(DUR), 2), np.float64)
    for t0, t1, fn, g in BEDS:
        x = fn(t1 - t0 + 0.6)
        fade = np.ones(len(x))
        k = n_(0.3)
        fade[:k] = np.linspace(0, 1, k); fade[-k:] = np.linspace(1, 0, k)
        place_mono(mix, x * fade, max(0.0, t0 - 0.3), g)
    for t0, x, g in EVENTS:
        place_mono(mix, x, t0, g)
    voice = np.zeros_like(mix)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            start = n_(ON[k])
            count = min(len(data), len(mix) - start)
            voice[start:start + count] += data[:count] * 0.85
    # gentle ducking of effects/ambience under the voice
    env_v = np.abs(voice[:, 0])
    env_v = lp(env_v, 8, 1)
    duck = 1 - 0.45 * np.clip(env_v / 0.05, 0, 1)
    mix = mix * duck[:, None] + voice
    return BR.audio(mix, SR)


if __name__ == '__main__':
    data = make_mix()
    raw = paths.build(HERE) / 'mix_raw.wav'
    with wave.open(str(raw), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data / max(1.0, np.abs(data).max() / 0.98), -0.98, 0.98) * 32767).astype('<i2').tobytes())
    out = paths.build(HERE) / 'mix.wav'
    subprocess.run([paths.ffmpeg(), '-y', '-v', 'error', '-i', str(raw), '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                    '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', str(out)], check=True)
    print('build/mix.wav готов (голос, эффекты, фон, RubUp; −14 LUFS)')
