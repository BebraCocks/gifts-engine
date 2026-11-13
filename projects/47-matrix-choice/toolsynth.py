"""Synthesised power-tool sounds (fallback while/if the Fish sound effect is missing): drill burst, chainsaw pull-start.
Deterministic (fixed seeds). drill(dur) / chainsaw() -> (N, 2) float, peak ≈ 0.8."""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def _bp(x, lo, hi):
    return sosfilt(butter(2, (lo, hi), 'bandpass', fs=SR, output='sos'), x)


def drill(dur=0.5, seed=1):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    spin = np.clip(t / 0.08, 0, 1) ** 0.6 * np.clip((dur - t) / 0.07, 0, 1)     # spin-up, spin-down
    f = 180 + 520 * spin                                   # motor fundamental rises with speed
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = sum(np.sin(k * ph) / k ** 0.9 for k in range(1, 9))          # buzzy brushed motor
    gear = np.sign(np.sin(ph * 6.0)) * 0.25                               # gear whine
    noise = _bp(rng.standard_normal(n), 1500, 7000) * 0.35
    y = (tone * 0.5 + gear + noise) * spin * (1 + 0.15 * np.sin(2 * np.pi * 37 * t))
    y = _bp(y, 120, 9000)
    y /= np.abs(y).max() + 1e-9
    return np.stack([y, y * 0.96], 1) * 0.8


def chainsaw(seed=2):
    rng = np.random.default_rng(seed)
    pull = int(0.32 * SR)
    t = np.arange(pull) / SR
    cord = _bp(rng.standard_normal(pull), 800, 5000) * np.sin(np.pi * t / t[-1]) ** 2 * 0.5   # cord rasp
    n = int(1.5 * SR)
    t2 = np.arange(n) / SR
    rpm = np.interp(t2, [0, 0.15, 0.55, 1.05, 1.5], [35, 60, 150, 150, 40])        # firing rate, Hz
    ph = 2 * np.pi * np.cumsum(rpm) / SR
    pulses = np.maximum(0, np.sin(ph)) ** 6                                          # two-stroke pops
    body = sosfilt(butter(2, 1800, 'lowpass', fs=SR, output='sos'), pulses * 2 + rng.standard_normal(n) * 0.25 * pulses)
    chain = _bp(rng.standard_normal(n), 2500, 8000) * (rpm / 150) ** 2 * 0.35
    env = np.clip(t2 / 0.03, 0, 1) * np.clip((1.5 - t2) / 0.25, 0, 1)
    eng = (body + chain) * env
    y = np.concatenate([cord, np.zeros(int(0.05 * SR)), eng])
    y = _bp(y, 60, 10000)
    y /= np.abs(y).max() + 1e-9
    return np.stack([y, y * 0.95], 1) * 0.8


def blow(dur=0.55, seed=4):
    """A strong human blow «ффф»: breathy band-passed noise, fast attack, lips-shaped resonance."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.clip(t / 0.035, 0, 1) * np.clip((dur - t) / 0.28, 0, 1) ** 1.5
    x = rng.standard_normal(n)
    y = _bp(x, 350, 2600) * 0.8 + _bp(x, 2600, 6500) * 0.35
    y *= env * (1 + 0.15 * np.sin(2 * np.pi * 9 * t))
    y /= np.abs(y).max() + 1e-9
    return np.stack([y, y * 0.92], 1) * 0.8
