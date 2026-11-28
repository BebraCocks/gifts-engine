"""Звуки серии «Холодильник» кодом: дверца (чмок уплотнителя), гул, хлопок, шипение морозилки, шаги, ручка
по блокноту, писк сканера, сверчки, грустный тромбон, скрэтч, тап по телефону."""
import math

import numpy as np

SR = 48000
rng = np.random.default_rng(66)


def _t(d):
    return np.arange(int(d * SR)) / SR


def _st(y, pan=0.0):
    l, r = y * math.sqrt((1 - pan) / 2) * 1.414, y * math.sqrt((1 + pan) / 2) * 1.414
    return np.stack([l, r], 1).astype(np.float32)


def _lp(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, 'same')


def _fade(y, a=0.004, r=0.03):
    ia, ir = min(len(y), int(a * SR)), min(len(y), int(r * SR))
    y[:ia] *= np.linspace(0, 1, ia)
    if ir:
        y[-ir:] *= np.linspace(1, 0, ir)
    return y


def fridge_open():
    """Чмок уплотнителя + короткий щелчок лампы + начало гула."""
    t = _t(0.6)
    n = rng.standard_normal(len(t))
    suck = _lp(n, 30) * np.exp(-t * 25) * 1.6
    thump = np.sin(2 * math.pi * (90 + 60 * np.exp(-t * 20)) * t) * np.exp(-t * 18) * 0.5
    click = np.zeros_like(t)
    i = int(0.12 * SR)
    click[i:i + 300] = np.sin(2 * math.pi * 3000 * t[:300]) * np.exp(-t[:300] * 300) * 0.3
    return _st(_fade(suck + thump + click))


def fridge_hum(d):
    t = _t(d)
    y = (np.sin(2 * math.pi * 100 * t) * 0.5 + np.sin(2 * math.pi * 200 * t) * 0.2 + np.sin(2 * math.pi * 300 * t) * 0.05)
    y *= 0.9 + 0.1 * np.sin(2 * math.pi * 0.7 * t)
    y += _lp(rng.standard_normal(len(t)), 8) * 0.05
    return _st(_fade(y * 0.12, 0.15, 0.2))


def fridge_close():
    t = _t(0.5)
    y = np.sin(2 * math.pi * (70 + 80 * np.exp(-t * 30)) * t) * np.exp(-t * 14) * 0.8
    y += _lp(rng.standard_normal(len(t)), 6) * np.exp(-t * 40) * 0.4
    rattle = np.sin(2 * math.pi * 1400 * t) * np.exp(-t * 35) * 0.06 * (np.sin(2 * math.pi * 30 * t) > 0)
    return _st(_fade(y + rattle))


def freezer_hiss(d=1.6):
    t = _t(d)
    n = rng.standard_normal(len(t))
    hi = n - _lp(n, 6)
    env = np.minimum(1, t / 0.05) * np.exp(-t * 1.6)
    return _st(_fade(hi * env * 0.25, 0.01, 0.2))


def step(pitch=1.0):
    t = _t(0.18)
    y = np.sin(2 * math.pi * 70 * pitch * t) * np.exp(-t * 35) * 0.6
    y += _lp(rng.standard_normal(len(t)), 10) * np.exp(-t * 50) * 0.3
    return _st(_fade(y))


def scribble(d=1.2):
    """Ручка по бумаге: шуршащие штрихи."""
    t = _t(d)
    n = rng.standard_normal(len(t))
    bp = _lp(n, 3) - _lp(n, 14)
    strokes = (np.sin(2 * math.pi * 5.5 * t + np.sin(2 * math.pi * 1.3 * t) * 2) > -0.2).astype(float)
    strokes = _lp(strokes, 400)
    return _st(_fade(bp * strokes * 0.35, 0.02, 0.05), 0.3)


def scan_beep():
    t = _t(0.42)
    y = np.zeros_like(t)
    for t0, f in ((0.0, 1800), (0.16, 2400)):
        i = int(t0 * SR)
        tt = t[:int(0.1 * SR)]
        y[i:i + len(tt)] += np.sin(2 * math.pi * f * tt) * np.minimum(1, tt / 0.005) * np.exp(-tt * 18) * 0.25
    return _st(y)


def scan_sweep(d=1.0):
    t = _t(d)
    f = 400 + 1600 * t / d
    y = np.sin(2 * math.pi * np.cumsum(f) / SR) * 0.08 * np.sin(np.pi * t / d)
    return _st(y)


def crickets(d=1.4):
    t = _t(d)
    y = np.zeros_like(t)
    for k in range(int(d / 0.45)):
        i = int((0.05 + k * 0.45) * SR)
        tt = t[:int(0.16 * SR)]
        chirp = np.sin(2 * math.pi * 4400 * tt) * (np.sin(2 * math.pi * 55 * tt) > 0) * np.sin(np.pi * tt / tt[-1])
        y[i:i + len(tt)] += chirp[:len(y) - i] * 0.12
    return _st(y, -0.4)


def sad_trombone():
    """Ва-ва-ва-ваааа: четыре нисходящие ноты, последняя с вибрато."""
    notes = [(311, 0.32), (294, 0.32), (277, 0.32), (262, 1.0)]
    out = []
    for i, (f, d) in enumerate(notes):
        t = _t(d)
        vib = 1 + (0.02 * np.sin(2 * math.pi * 6 * t) if i == 3 else np.zeros_like(t))
        ph = 2 * math.pi * np.cumsum(f * vib) / SR
        y = sum(np.sin(ph * h) / h ** 0.8 for h in range(1, 7))
        y *= np.minimum(1, t / 0.04) * np.minimum(1, (d - t) / 0.06)
        wah = 0.6 + 0.4 * np.minimum(1, t / 0.12)
        out.append(y * wah)
    return _st(np.concatenate(out) * 0.12)


def scratch():
    t = _t(0.35)
    f = 300 + 900 * np.abs(np.sin(2 * math.pi * 3 * t))
    n = rng.standard_normal(len(t))
    y = (_lp(n, 4) * np.sin(2 * math.pi * np.cumsum(f) / SR)) * np.exp(-t * 5) * 0.4
    return _st(_fade(y))


def tap():
    t = _t(0.05)
    return _st(np.sin(2 * math.pi * 1200 * t) * np.exp(-t * 120) * 0.3)


def ufo(dur=1.3, rise=False):
    """Пролёт НЛО (как в серии 1); rise=True — уход вверх (тон растёт)."""
    t = _t(dur)
    f = (220 + 700 * (1 - np.exp(-t * 1.6))) if rise else (900 * np.exp(-t * 1.1) + 220)
    wob = 1 + 0.06 * np.sin(2 * math.pi * 11 * t)
    y = np.sin(2 * math.pi * np.cumsum(f * wob) / SR) * 0.3 + np.sin(2 * math.pi * np.cumsum(f * 1.5 * wob) / SR) * 0.1
    env = np.minimum(1, t / 0.2) * np.exp(-np.maximum(0, t - dur + 0.4) * 6)
    return _st(y * env)


def beam(dur=1.2, up=False):
    t = _t(dur)
    s = 1 + (0.8 if up else 0.5) * t
    y = sum(np.sin(2 * math.pi * f * s * t) for f in (440, 554, 659, 880)) / 4
    y *= (0.7 + 0.3 * np.sin(2 * math.pi * 18 * t)) * np.sin(np.linspace(0, math.pi, len(t))) * 0.35
    return _st(y)
