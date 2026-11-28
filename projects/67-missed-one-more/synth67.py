"""Звуки «Ещё одно видео» кодом: свайп ленты, быстрые тики часов (тайм-лапс), «бум» телефона по лицу."""
import math

import numpy as np

SR = 48000
rng = np.random.default_rng(67)


def _st(y):
    return np.stack([y, y], 1).astype(np.float32)


def swipe():
    t = np.arange(int(0.16 * SR)) / SR
    n = rng.standard_normal(len(t))
    hi = n - np.convolve(n, np.ones(6) / 6, 'same')
    return _st(hi * np.sin(np.pi * t / t[-1]) ** 2 * 0.18)


def ticks(d, rate=14):
    t = np.arange(int(d * SR)) / SR
    y = np.zeros_like(t)
    k = 0
    while k / rate < d:
        i = int(k / rate * SR)
        tt = t[:int(0.02 * SR)]
        y[i:i + len(tt)] += np.sin(2 * math.pi * (2600 if k % 2 else 2100) * tt) * np.exp(-tt * 300) * 0.25
        k += 1
    return _st(y[:len(t)])


def bonk():
    """Телефон падает на лицо: глухой удар + мультяшный «бом»."""
    t = np.arange(int(0.6 * SR)) / SR
    thud = np.sin(2 * math.pi * (60 + 120 * np.exp(-t * 40)) * t) * np.exp(-t * 16) * 0.8
    bom = np.sin(2 * math.pi * (420 - 200 * t) * t) * np.exp(-t * 7) * 0.25
    return _st(thud + bom)
