"""Звуки кодом: 5 разных будильников (каждый противнее), храп, НЛО, луч, щелчок будильника на телефоне."""
import math

import numpy as np

SR = 48000
rng = np.random.default_rng(65)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _st(y):
    return np.stack([y, y], 1).astype(np.float32)


def _fade(y, a=0.005, r=0.02):
    n = len(y)
    ia, ir = min(n, int(a * SR)), min(n, int(r * SR))
    y[:ia] *= np.linspace(0, 1, ia)
    if ir:
        y[-ir:] *= np.linspace(1, 0, ir)
    return y


def alarm(n, dur):
    """n = 0..4: мягкая маримба → бип → двойной бип → сирена-трель → старый механический звонок."""
    t = _t(dur)
    if n == 0:                                  # мягкая маримба-мелодия
        y = np.zeros_like(t)
        for i, f in enumerate([523, 659, 784, 659, 523, 659, 784, 1047] * 3):
            s = int(i * 0.16 * SR)
            if s >= len(t):
                break
            tt = t[:len(t) - s]
            y[s:] += np.sin(2 * math.pi * f * tt) * np.exp(-tt * 14) * 0.5
        return _st(_fade(y * 0.6))
    if n == 1:                                  # классический бип
        gate = (np.floor(t / 0.25) % 2 == 0)
        y = np.sign(np.sin(2 * math.pi * 2000 * t)) * 0.18 * gate
        return _st(_fade(y))
    if n == 2:                                  # двойной бип быстрее и выше
        ph = t % 0.42
        gate = (ph < 0.08) | ((ph > 0.13) & (ph < 0.21))
        y = (np.sign(np.sin(2 * math.pi * 2600 * t)) * 0.2 + np.sin(2 * math.pi * 3900 * t) * 0.08) * gate
        return _st(_fade(y))
    if n == 3:                                  # сирена-трель
        f = 1500 + 700 * np.sin(2 * math.pi * 3.0 * t)
        y = np.sign(np.sin(2 * math.pi * np.cumsum(f) / SR)) * 0.17
        y *= 0.6 + 0.4 * (np.sin(2 * math.pi * 14 * t) > 0)
        return _st(_fade(y))
    # 4: механический звонок — молоточек по двум чашкам, дребезг
    y = np.zeros_like(t)
    hit = 1 / 24
    for i in range(int(dur / hit)):
        s = int(i * hit * SR)
        tt = t[:len(t) - s]
        f = 2350 if i % 2 else 2810
        y[s:] += (np.sin(2 * math.pi * f * tt) + 0.5 * np.sin(2 * math.pi * f * 2.76 * tt)) * np.exp(-tt * 30) * 0.12
    return _st(_fade(np.tanh(y * 2.2) * 0.42))


def snore(dur=1.6):
    """Вдох-храп (низкий хрип) + выдох-свист."""
    t = _t(dur)
    half = len(t) // 2
    noise = rng.standard_normal(len(t))
    k = int(SR / 400)
    low = np.convolve(noise, np.ones(k) / k, 'same')
    buzz = 0.6 + 0.4 * np.sin(2 * math.pi * 32 * t)
    inh = low * buzz * np.sin(np.linspace(0, math.pi, len(t))) ** 2
    y = np.zeros_like(t)
    y[:half] = inh[:half] * 3.0
    tt = t[half:] - t[half]
    whistle = np.sin(2 * math.pi * (900 - 300 * tt / tt[-1]) * tt) * np.sin(np.linspace(0, math.pi, len(tt))) * 0.08
    y[half:] = whistle + noise[half:] * 0.01
    return _st(_fade(y * 0.5, 0.05, 0.1))


def ufo(dur=1.3):
    """Пролёт НЛО: вибрирующий синус с понижением + шипение, панорама справа налево."""
    t = _t(dur)
    f = 900 * np.exp(-t * 1.1) + 220
    wob = 1 + 0.06 * np.sin(2 * math.pi * 11 * t)
    y = np.sin(2 * math.pi * np.cumsum(f * wob) / SR) * 0.3
    y += np.sin(2 * math.pi * np.cumsum(f * 1.5 * wob) / SR) * 0.1
    env = np.minimum(1, t / 0.25) * np.exp(-np.maximum(0, t - 0.9) * 4)
    y *= env
    pan = np.linspace(0.9, -0.3, len(t))
    l, r = y * np.sqrt((1 - pan) / 2), y * np.sqrt((1 + pan) / 2)
    return np.stack([l, r], 1).astype(np.float32)


def beam(dur=1.2):
    """Луч: восходящий мерцающий аккорд."""
    t = _t(dur)
    y = sum(np.sin(2 * math.pi * f * (1 + 0.5 * t) * t) for f in (440, 554, 659, 880)) / 4
    y *= (0.7 + 0.3 * np.sin(2 * math.pi * 18 * t)) * np.sin(np.linspace(0, math.pi, len(t))) * 0.35
    return _st(y)


def tick(f=1800):
    """Короткий щелчок установки будильника."""
    t = _t(0.06)
    return _st(np.sin(2 * math.pi * f * t) * np.exp(-t * 90) * 0.35)
