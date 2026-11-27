"""Музыка части 1 «Низшего» кодом (в комплекте нет музыкальной библиотеки). Тёмный индустриальный эмбиент ре минор
без шипящих слоёв (требование автора 2026-11-24). Настроение по сценам (MOOD): гул идёт всё время, поверх
плавно (1,5 с) включаются слои: calm — редкие холодные колокола; sad — аккорды Dm–Bb–Gm–A; tension — пульс 70 BPM
с металлическим лязгом; dark — только низкий гул. music(n, sr) -> стерео; audio.py приглушает её под голосом."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from timeline import DUR, SCENES

MOOD = {'body': 'calm', 'face': 'calm', 'yorka_up': 'tension', 'yorka_look': 'calm', 'self': 'sad',
        'corridor': 'tension', 'scan': 'tension', 'niche': 'calm', 'yorka_talk': 'sad', 'slap': 'tension',
        'leave': 'calm', 'menu': 'calm', 'odin': 'sad', 'screen': 'tension', 'game': 'tension', 'slime': 'dark',
        'kick': 'tension', 'bench': 'calm', 'talk444': 'sad', 'races': 'dark', 'medblock': 'dark', 'klux': 'calm',
        'demote': 'sad', 'guard': 'calm', 'capsule': 'sad'}
BEAT = 60 / 70


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def filt(x, kind, f, sr, order=2):
    return sosfilt(butter(order, f, kind, fs=sr, output='sos'), x)


def env_ad(n, a, d, sr):
    tt = np.arange(n) / sr
    e = np.exp(-tt / d)
    na = max(1, int(a * sr))
    e[:na] *= np.linspace(0, 1, na)
    return e


def layer_gain(n, sr, mood):
    """огибающая слоя: 1 там, где сцена этого настроения, с переходами 1,5 с"""
    g = np.zeros(n)
    for name, t0, t1, _ in SCENES:
        if MOOD.get(name) == mood:
            g[int(t0 * sr):int(t1 * sr)] = 1.0
    k = int(1.5 * sr)
    return np.convolve(g, np.ones(k) / k, 'same')


def music(n, sr=48000):
    rng = np.random.default_rng(11)
    t = np.arange(n) / sr
    L, R = np.zeros(n), np.zeros(n)

    def add(start, y, gain=1.0, pan=0.0):
        a = int(start * sr)
        b = min(n, a + len(y))
        if b <= a or a < 0:
            return
        y = y[:b - a] * gain
        L[a:b] += y * np.sqrt((1 - pan) / 2)
        R[a:b] += y * np.sqrt((1 + pan) / 2)

    # гул всё время (синусы + суббас ниже 55 Гц)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    drone = (np.sin(2 * np.pi * hz(26) * t) + 0.6 * np.sin(2 * np.pi * hz(33) * t + 1.0)
             + 0.35 * np.sin(2 * np.pi * hz(38.03) * t)) * lfo
    sub = filt(rng.standard_normal(n), 'lowpass', 55, sr, 4) * 3.0
    dark = layer_gain(n, sr, 'dark')
    base = (drone * (0.22 + 0.1 * dark) + sub * 0.08) * np.clip(t / 2.5, 0, 1)
    L += base
    R += base

    # calm: колокола каждые ~4 с
    def bell(m, dur=3.2):
        k = int(dur * sr)
        tt = np.arange(k) / sr
        f = hz(m)
        mod = np.sin(2 * np.pi * f * 1.41 * tt) * 2.0 * np.exp(-tt / 0.6)
        return np.sin(2 * np.pi * f * tt + mod) * env_ad(k, 0.002, 1.0, sr)

    calm = layer_gain(n, sr, 'calm')
    notes = [69, 74, 77, 72, 76, 74, 69, 81]
    for k, tb in enumerate(np.arange(1.0, n / sr, 4 * BEAT)):
        g = calm[min(n - 1, int(tb * sr))]
        if g > 0.05:
            add(tb, bell(notes[k % len(notes)]), 0.06 * g, (-0.4, 0.4)[k % 2])

    # sad: аккорды Dm–Bb–Gm–A по 4 такта
    def saw(f, k, det):
        ph = np.cumsum(np.full(k, f * det)) / sr
        return 2 * (ph % 1.0) - 1

    sad = layer_gain(n, sr, 'sad')
    chords = [(50, 53, 57), (46, 50, 53), (43, 46, 50), (45, 49, 52)]
    clen = 8 * BEAT
    pad = np.zeros(n)
    for k, t0 in enumerate(np.arange(0, n / sr, clen)):
        kk = int((clen + 1.5) * sr)
        y = sum(saw(hz(m), kk, det) for m in chords[k % 4] for det in (0.996, 1.0, 1.005))
        y = filt(y, 'lowpass', 650, sr)
        e = np.ones(kk)
        na, nr = int(1.2 * sr), int(1.5 * sr)
        e[:na] = np.linspace(0, 1, na)
        e[-nr:] *= np.linspace(1, 0, nr)
        a = int(t0 * sr)
        b = min(n, a + kk)
        pad[a:b] += (y * e)[:b - a]
    L += pad * sad * 0.026
    R += pad * sad * 0.026

    # tension: пульс и лязг
    def thud():
        k = int(0.6 * sr)
        tt = np.arange(k) / sr
        f = 35 + 30 * np.exp(-tt / 0.06)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * env_ad(k, 0.003, 0.18, sr)

    def clank(seed):
        k = int(1.0 * sr)
        r = np.random.default_rng(seed)
        burst = r.standard_normal(k) * env_ad(k, 0.001, 0.015, sr)
        y = np.zeros(k)
        for f, d, g in ((410, 0.45, 1.0), (1127, 0.3, 0.6), (2268, 0.2, 0.35)):
            f2 = f * (1 + r.uniform(-0.03, 0.03))
            y += filt(burst, 'bandpass', [f2 * 0.98, f2 * 1.02], sr) * env_ad(k, 0.001, d, sr) * g * 40
        return y

    ten = layer_gain(n, sr, 'tension')
    th = thud()
    for j, tb in enumerate(np.arange(0, n / sr, BEAT)):
        g = ten[min(n - 1, int(tb * sr))]
        if g > 0.05:
            add(tb, th, 0.45 * g)
            if j % 2:
                add(tb + 0.02, clank(100 + j % 16), 0.07 * g, -0.4 if j % 4 == 1 else 0.4)

    irn = int(2.6 * sr)
    irt = np.arange(irn) / sr
    irs = []
    for _ in range(2):
        ir = filt(rng.standard_normal(irn), 'lowpass', 2500, sr) * np.exp(-irt / 0.7)
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    wl = fftconvolve(filt(L, 'highpass', 150, sr), irs[0])[:n]
    wr = fftconvolve(filt(R, 'highpass', 150, sr), irs[1])[:n]
    out = np.stack([L + wl * 0.45, R + wr * 0.45], 1)
    out *= np.clip((DUR - t) / 2.0, 0, 1)[:, None]
    out = np.tanh(out * 1.5) / 1.5
    out = filt(out.T, 'lowpass', 9000, sr).T
    return out / (np.max(np.abs(out)) + 1e-9) * 0.5
