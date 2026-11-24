"""Музыка «Низшего», написана кодом (в комплекте нет музыкальной библиотеки, у Fish Audio нет музыкальной модели).
Тёмный индустриальный эмбиент, ре минор, 70 BPM. Без шипящих шумовых слоёв (требование автора 2026-11-24):
гул — только синусы и глубокий суббас; ревербератор с тёмным хвостом.

Сцены: пробуждение — гул и редкие холодные колокола; профиль без памяти — холодные аккорды Dm–Bb;
крик Йорки — тяжёлый пульс с металлическим лязгом; «11» — удар и затухание.
music(n, sr) возвращает стерео (n, 2); audio.py сам приглушает музыку под голосом."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from timeline import S, E, DUR, SC2, SC3, STAMP

BPM = 70.0
BEAT = 60.0 / BPM


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

    # 1. гул: D1, A1, D2 + глубокий суббас (шум только ниже 55 Гц — не слышен как шипение)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t)
    drone = (np.sin(2 * np.pi * hz(26) * t) + 0.6 * np.sin(2 * np.pi * hz(33) * t + 1.0)
             + 0.35 * np.sin(2 * np.pi * hz(38.03) * t)) * lfo
    sub = filt(rng.standard_normal(n), 'lowpass', 55, sr, 4) * 3.0
    fade_in = np.clip(t / 2.5, 0, 1)
    add(0, (drone * 0.26 + sub * 0.08) * fade_in)

    # 2. колокола пробуждения — на каждое «успешно» почти неслышный холодный звон
    def bell(m, dur=3.2):
        k = int(dur * sr)
        tt = np.arange(k) / sr
        f = hz(m)
        mod = np.sin(2 * np.pi * f * 1.41 * tt) * 2.0 * np.exp(-tt / 0.6)
        return np.sin(2 * np.pi * f * tt + mod) * env_ad(k, 0.002, 1.0, sr)

    for tb, m, pan in ((S['S1'] + 1.1, 69, -0.4), (S['S2'] + 1.25, 74, 0.4), (S['S3'] + 1.3, 77, 0.0)):
        add(tb, bell(m), 0.07, pan)

    # 3. холодные аккорды профиля: Dm -> Bb (детюн-пилы, фильтр 650 Гц)
    def saw(f, k, det):
        ph = np.cumsum(np.full(k, f * det)) / sr
        return 2 * (ph % 1.0) - 1

    half = (SC3 - SC2) / 2
    for i, ch in enumerate([(50, 53, 57), (46, 50, 53)]):
        t0 = SC2 - 0.4 + i * half
        k = int((half + 1.6) * sr)
        y = sum(saw(hz(m), k, det) for m in ch for det in (0.996, 1.0, 1.005))
        y = filt(y, 'lowpass', 650, sr)
        e = np.ones(k)
        na, nr = int(1.2 * sr), int(1.4 * sr)
        e[:na] = np.linspace(0, 1, na)
        e[-nr:] *= np.linspace(1, 0, nr)
        add(t0, y * e, 0.030, -0.25 if i else 0.25)

    # 4. тяжёлый пульс от крика Йорки до удара «11»
    def thud():
        k = int(0.6 * sr)
        tt = np.arange(k) / sr
        f = 35 + 30 * np.exp(-tt / 0.06)
        return np.sin(2 * np.pi * np.cumsum(f) / sr) * env_ad(k, 0.003, 0.18, sr)

    def clank(seed):
        k = int(1.2 * sr)
        r = np.random.default_rng(seed)
        burst = r.standard_normal(k) * env_ad(k, 0.001, 0.015, sr)
        y = np.zeros(k)
        for f, d, g in ((410, 0.45, 1.0), (1127, 0.3, 0.6), (2268, 0.2, 0.35)):
            f2 = f * (1 + r.uniform(-0.03, 0.03))
            y += filt(burst, 'bandpass', [f2 * 0.98, f2 * 1.02], sr) * env_ad(k, 0.001, d, sr) * g * 40
        return y

    tb, j = S['Y1'], 0
    while tb < STAMP - 0.2:
        add(tb, thud(), 0.5)
        if j % 2 == 1:
            add(tb + 0.02, clank(100 + j), 0.09, -0.4 if j % 4 == 1 else 0.4)
        tb += BEAT * 0.5          # ускорение: восьмые — тревога
        j += 1

    # 5. удар «11»: низкий бум + аккорд ре минор, долгий хвост
    k = int(3.0 * sr)
    tt = np.arange(k) / sr
    boom = np.sin(2 * np.pi * np.cumsum(40 + 60 * np.exp(-tt / 0.08)) / sr) * env_ad(k, 0.002, 0.7, sr)
    add(STAMP, boom, 0.9)
    y = sum(np.sin(2 * np.pi * hz(m) * tt) for m in (38, 50, 53, 57, 62)) * env_ad(k, 0.01, 1.2, sr)
    add(STAMP, y, 0.07)

    # реверб: тёмный хвост (IR до 2,5 кГц)
    irn = int(2.6 * sr)
    irt = np.arange(irn) / sr
    irs = []
    for _ in range(2):
        ir = filt(rng.standard_normal(irn), 'lowpass', 2500, sr) * np.exp(-irt / 0.7)
        irs.append(ir / np.sqrt(np.sum(ir ** 2)))
    wl = fftconvolve(filt(L, 'highpass', 150, sr), irs[0])[:n]
    wr = fftconvolve(filt(R, 'highpass', 150, sr), irs[1])[:n]
    out = np.stack([L + wl * 0.45, R + wr * 0.45], 1)
    out *= np.clip((DUR - t) / 1.2, 0, 1)[:, None]
    out = np.tanh(out * 1.5) / 1.5
    out = filt(out.T, 'lowpass', 9000, sr).T          # без верхнего шороха
    return out / (np.max(np.abs(out)) + 1e-9) * 0.5
