"""Procedural sound effects (no third-party samples), placed on the shared events.
Every generator returns a stereo float array at 48 kHz; `cue_list()` says what plays when."""
import math

import numpy as np
from scipy.signal import butter, sosfilt

from events import E, SHOTS, AD_STOPS
import art

SR = 48000
RNG = np.random.default_rng(42)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'), x)


def _lp(x, f, order=2):
    return sosfilt(butter(order, f, 'lowpass', fs=SR, output='sos'), x)


def _hp(x, f, order=2):
    return sosfilt(butter(order, f, 'highpass', fs=SR, output='sos'), x)


def _st(x, pan=0.0, width=0.0):
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    y = np.stack([x * l, x * r], 1) * 1.4142
    if width:
        d = int(0.012 * SR)
        y[d:, 1] = y[d:, 1] * (1 - width) + y[:-d, 1] * width
    return y


def _norm(x, peak):
    m = np.abs(x).max() + 1e-9
    return x / m * peak


def whoosh(d=0.6, lo=300, hi=3000, peak=0.35, pan=0.0):
    t = _t(d)
    n = RNG.standard_normal(len(t))
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    # sweep a band through the noise in a few slices
    out = np.zeros_like(n)
    k = 12
    for i in range(k):
        a, b = i * len(t) // k, (i + 1) * len(t) // k
        f = lo + (hi - lo) * math.sin(math.pi * (i + 0.5) / k)
        out[a:b] = _bp(n, f * 0.6, min(f * 1.6, 20000))[a:b]
    return _st(_norm(out * env, peak), pan, 0.4)


def impact(d=1.4, f0=90, peak=0.75, noise=0.4):
    t = _t(d)
    f = f0 * (1 + 1.5 * np.exp(-t * 18))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 3.2)
    crack = _lp(RNG.standard_normal(len(t)), 2500) * np.exp(-t * 28) * noise
    return _st(_norm(np.tanh(1.6 * (body + crack)), peak))


def pop(f=520, d=0.22, peak=0.32, pan=0.0):
    t = _t(d)
    fr = f * (1.6 - 0.6 * np.minimum(1, t / 0.05))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 22)
    return _st(_norm(x, peak), pan)


def ding(f=1320, d=1.6, peak=0.18, pan=0.0):
    t = _t(d)
    x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * dk) for m, a, dk in
            ((1, 1, 2.5), (2.76, 0.45, 4), (5.4, 0.25, 7), (8.9, 0.12, 10)))
    x *= np.minimum(1, t / 0.004)
    return _st(_norm(x, peak), pan, 0.3)


def sparkle(d=1.2, peak=0.12):
    out = np.zeros((int(d * SR), 2))
    r = np.random.default_rng(7)
    for i in range(9):
        s = ding(r.uniform(1800, 4200), 0.6, peak * r.uniform(0.4, 1), r.uniform(-0.7, 0.7))
        a = int(r.uniform(0, d - 0.6) * SR)
        out[a:a + len(s)] += s
    return out


def click(peak=0.4, f=3000):
    t = _t(0.05)
    x = _bp(RNG.standard_normal(len(t)), f * 0.5, f * 1.5) * np.exp(-t * 160)
    return _st(_norm(x, peak))


def hum(d, f=50, peak=0.12, buzz=0.5):
    t = _t(d)
    x = np.sin(2 * np.pi * f * t) + buzz * np.sign(np.sin(2 * np.pi * 2 * f * t)) * 0.3
    x = _lp(x, 900)
    env = np.minimum(1, t / 0.08) * np.minimum(1, (d - t) / 0.2)
    return _st(_norm(x * env, peak))


def scribble(d, peak=0.22):
    """Marker on paper: band-passed noise with stroke rhythm."""
    t = _t(d)
    n = _bp(RNG.standard_normal(len(t)), 1800, 7000)
    rhythm = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 3.1 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.9 * t))
    env = np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.1)
    return _st(_norm(n * rhythm * env, peak), -0.15)


def spray(d=1.1, peak=0.28):
    t = _t(d)
    n = _hp(RNG.standard_normal(len(t)), 3500)
    env = np.minimum(1, t / 0.03) * np.minimum(1, (d - t) / 0.15) * (0.85 + 0.15 * np.sin(t * 40))
    return _st(_norm(n * env, peak), 0.1, 0.5)


def shutdown(d=0.5, f0=420, peak=0.22, pan=0.0):
    t = _t(d)
    f = f0 * np.exp(-t * 4)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 6)
    return _st(_norm(_lp(x, 3000), peak), pan)


def wind(d, peak=0.16):
    t = _t(d)
    n = RNG.standard_normal(len(t))
    x = _lp(n, 500) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.23 * t)) + 0.3 * _bp(n, 900, 2400) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.37 * t))
    env = np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6)
    return _st(_norm(x * env, peak), 0, 0.6)


def thud(peak=0.35, f0=70):
    t = _t(0.35)
    x = np.sin(2 * np.pi * f0 * t * (1 + np.exp(-t * 30))) * np.exp(-t * 14) + 0.2 * _lp(RNG.standard_normal(len(t)), 900) * np.exp(-t * 40)
    return _st(_norm(x, peak), RNG.uniform(-0.6, 0.6))


def chord(freqs, d=2.5, peak=0.25, attack=0.02):
    t = _t(d)
    x = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) for f in freqs)
    env = np.minimum(1, t / attack) * np.exp(-t * 1.4)
    return _st(_norm(x * env, peak), 0, 0.5)


def riser(d=1.0, peak=0.2):
    t = _t(d)
    f = 200 * (1 + 6 * (t / d) ** 2)
    n = RNG.standard_normal(len(t))
    out = np.zeros_like(n)
    for i in range(10):
        a, b = i * len(t) // 10, (i + 1) * len(t) // 10
        fc = f[(a + b) // 2]
        out[a:b] = _bp(n, fc * 0.7, fc * 1.4)[a:b]
    return _st(_norm(out * (t / d) ** 2, peak), 0, 0.5)


def footsteps(d, rate=1.7, peak=0.16):
    out = np.zeros((int(d * SR), 2))
    k = 0
    while k / rate < d - 0.2:
        s = thud(peak, 110 + 15 * (k % 2))
        a = int(k / rate * SR)
        out[a:a + len(s)] += s[:len(out) - a]
        k += 1
    return out


def cue_list():
    """(content time, sound array, gain). Whooshes sit on the non-ad cuts."""
    c = []
    cuts = [a for n, a, b in SHOTS[1:] if all(abs(a - s) > 1e-6 for s in AD_STOPS)]
    for i, a in enumerate(cuts):
        c.append((a - 0.32, whoosh(0.62, 250 + 60 * (i % 3), 2600 + 300 * (i % 4), 0.33, (-1) ** i * 0.4), 1.0))
    c.append((0.15, scribble(2.9), 1.0))
    c.append((E['war'] - 0.02, click(0.35), 1.0))
    c.append((E['war'], hum(1.2, 55, 0.12), 1.0))
    c.append((E['war'] + 0.05, impact(1.6, 55, 0.45, 0.2), 1.0))
    c.append((E['spotty'] - 0.4, pop(660, peak=0.25), 1.0))
    c.append((E['said'] - 0.05, pop(380, peak=0.22), 1.0))
    c.append((E['left'] - 0.2, footsteps(2.2), 1.0))
    c.append((E['telegram1'] - 0.3, chord((523, 659, 784), 1.8, 0.12, 0.25), 1.0))
    c.append((E['past'] - 0.4, chord((196, 233, 294), 2.2, 0.1, 0.4), 1.0))
    for k in ('gift1', 'vpn'):
        c.append((E[k] - 0.15, pop(520 if k == 'gift1' else 700, peak=0.3), 1.0))
        c.append((E[k] - 0.1, sparkle(1.2, 0.12), 1.0))
    c.append((E['notat'] - 0.1, impact(1.2, 48, 0.35, 0.1), 1.0))
    c.append((E['y2018'] - 0.1, impact(1.0, 70, 0.3, 0.3), 1.0))
    c.append((E['keys'] - 0.1, ding(2100, 1.2, 0.12), 1.0))
    c.append((E['blocks'], impact(1.8, 62, 0.8, 0.6), 1.0))
    c.append((E['blocks'] + 0.02, click(0.5, 1800), 1.0))
    c.append((E['pub'] - 0.1, click(0.3, 2500), 1.0))
    c.append((E['pub'], hum(2.5, 60, 0.06, 0.8), 1.0))
    c.append((E['hood'] - 0.45, whoosh(0.45, 400, 2000, 0.25), 1.0))
    c.append((E['hood'], impact(1.0, 80, 0.45, 0.4), 1.0))
    c.append((E['sign'] - 0.05, spray(1.15), 1.0))
    c.append((E['rkn'], riser(1.3, 0.16), 1.0))
    for k in range(10):
        c.append((E['millions'] + k * 0.13, shutdown(0.4, 380 + 40 * (k % 4), 0.12, (k % 5 - 2) * 0.3), 1.0))
    for k in range(6):
        c.append((E['fall'] + k * 0.22, impact(0.9, 45 + 5 * k, 0.28, 0.5), 1.0))
    c.append((E['tg'] - 0.8, whoosh(2.2, 500, 5000, 0.22), 1.0))
    c.append((E['proxy'] - 0.3, whoosh(1.0, 800, 6000, 0.3), 1.0))
    c.append((SHOTS[7][1], wind(SHOTS[7][2] - SHOTS[7][1], 0.13), 1.0))
    for k in ('proxyserver', 'anon'):
        c.append((E[k] - 0.15, pop(600, peak=0.28), 1.0))
        c.append((E[k] - 0.1, sparkle(1.0, 0.1), 1.0))
    c.append((E['lift'], ding(880, 1.6, 0.14), 1.0))
    c.append((E['legend'] - 0.05, chord((262, 330, 392, 523), 2.8, 0.22, 0.03), 1.0))
    c.append((E['legend'] - 0.05, impact(1.4, 60, 0.35, 0.2), 1.0))
    c.append((E['token'] - 0.1, ding(1560, 1.8, 0.16), 1.0))
    c.append((E['token'] - 0.05, ding(2340, 1.4, 0.08, 0.3), 1.0))
    c.append((E['arrest'] - 0.5, whoosh(0.9, 300, 3000, 0.22, 0.5), 1.0))
    for k in range(14):
        c.append((E['avatars'] - 0.3 + k * 0.07, click(0.08, 2600 + 120 * k), 1.0))
    # gift rain: thuds when boxes land (approximate the drop times of shots_b.S11)
    r = np.random.default_rng(17)
    for k in range(18):
        c.append((E['gifts24'] - 0.25 + r.uniform(0, 1.9), thud(0.2), 1.0))
    c.append((E['year'] - 0.2, thud(0.35, 55), 1.0))
    c.append((E['him'] - 0.1, pop(440, peak=0.3), 1.0))
    c.append((E['him'], chord((523, 659, 784, 1047), 2.0, 0.16, 0.02), 1.0))
    c.append((E['him'], sparkle(1.4, 0.12), 1.0))
    c.append((E['next'] - 0.2, impact(1.4, 45, 0.3, 0.1), 1.0))
    c.append((E['upgrade'] - 0.1, riser(1.0, 0.14), 1.0))
    for i, k in enumerate(('che', 'sparta', 'rambo', 'satoshi')):
        c.append((E[k] - 0.15, pop(500 + 90 * i, peak=0.3, pan=0.2 * (i - 1.5)), 1.0))
    c.append((E['satoshi'] - 0.1, sparkle(1.3, 0.14), 1.0))
    c.append((SHOTS[12][1], hum(SHOTS[12][2] - SHOTS[12][1], 98, 0.06, 0.6), 1.0))
    c.append((E['imposter'] - 0.2, whoosh(0.5, 600, 4000, 0.22), 1.0))
    c.append((E['imposter'], impact(1.2, 70, 0.4, 0.3), 1.0))
    c.append((E['thousand'] - 0.1, ding(990, 1.4, 0.16), 1.0))
    for i, k in enumerate(('drawing', 'survived', 'survived', 'collect', 'collect')):
        c.append((E[k] + (0.2, 0.1, 0.8, -0.4, 0.3)[i] - 0.1, pop(480 + 60 * i, peak=0.22, pan=0.3 * (i - 2)), 1.0))
    c.append((E['resist2'] - 0.1, chord((262, 330, 392), 3.5, 0.14, 0.4), 1.0))
    c.append((E['cont'] + 0.45, click(0.4, 2200), 1.0))
    return c
