"""Синтез мерзких и мультяшных звуков кодом (перенесено из 60-fan и дополнено для 61)."""
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def filt(x, f, kind='low', order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def st(x):
    return np.stack([x, x], 1)


def whack(seed=0, low=90):
    """Удар лопасти по «посылке»: глухой шлепок + короткий щелчок."""
    r = np.random.default_rng(seed)
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * low * t * (1 - 0.4 * t / 0.35)) * np.exp(-t * 22)
    wet = filt(r.standard_normal(n), 2500) * np.exp(-t * 30)
    x = thump + 0.7 * wet
    return st(x / np.abs(x).max())


def splat(seed=0):
    """Шлепок брызги о стену: влажный шумовой всплеск."""
    r = np.random.default_rng(seed)
    n = int(0.18 * SR)
    t = np.arange(n) / SR
    x = filt(filt(r.standard_normal(n), 300, 'high'), 3500 + 1500 * r.random()) * np.exp(-t * (35 + 20 * r.random()))
    x += 0.4 * np.sin(2 * np.pi * (140 + 60 * r.random()) * t) * np.exp(-t * 40)
    return st(x / np.abs(x).max())


def spray(dur, seed=0):
    """Шипение распыления."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = filt(filt(r.standard_normal(n), 1500, 'high'), 7000) * np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.3)
    return st(x / np.abs(x).max())


def meow():
    """Обиженное «мяу»: тон 500→750→420 Гц с гармониками и вибрато."""
    n = int(0.75 * SR)
    t = np.arange(n) / SR
    f = np.interp(t, [0, 0.25, 0.75], [500, 760, 420]) * (1 + 0.02 * np.sin(2 * np.pi * 7 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * h) / h for h in range(1, 6))
    x = filt(x, 2500) * np.minimum(1, t / 0.06) * np.minimum(1, (0.75 - t) / 0.2)
    return st(x / np.abs(x).max())


def tv_static(dur, seed=7):
    r = np.random.default_rng(seed)
    x = filt(r.standard_normal(int(dur * SR)), 6000) * 0.8
    return st(x / np.abs(x).max())


def sniff(seed=0):
    r = np.random.default_rng(seed + 50)
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    x = filt(filt(r.standard_normal(n), 1200, 'high'), 5000) * np.sin(np.pi * t / 0.22) ** 2
    return st(x / np.abs(x).max())


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)


def fart(dur=0.6, f0=95, wet=0.4, seed=0, fall=0.3, squeak=False):
    """Пук: пила с «трепетом» сфинктера и шумом. squeak — короткий писклявый."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 - fall * t / dur) * (1 + 0.12 * np.sin(2 * np.pi * (5 + 4 * r.random()) * t))
    if squeak:
        f = f * (1 + 1.5 * np.sin(np.pi * t / dur))
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    flut = filt(np.sign(np.sin(2 * np.pi * (16 + 10 * r.random()) * t)) * 0.4 + 0.6, 50)
    x = saw * flut + wet * filt(r.standard_normal(n), 900) * (1 + np.sin(2 * np.pi * 23 * t))
    x = filt(x, 1400 if squeak else 800, order=4)
    x *= np.minimum(1, t / 0.015) * np.minimum(1, (dur - t) / 0.1)
    return st(x / (np.abs(x).max() + 1e-9))


def sad_trombone_fart():
    """Четыре нисходящих «ноты»-пука: ва-ва-ва-ваааа."""
    parts = [fart(0.28, f, 0.2, seed=k, fall=0.05) for k, f in enumerate((150, 140, 132))]
    parts.append(fart(1.0, 124, 0.3, seed=9, fall=0.25))
    gap = np.zeros((int(0.05 * SR), 2))
    return np.concatenate(sum([[p, gap] for p in parts], []))


def plop():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 18) + 200) / SR) * np.exp(-t * 14)
    return st(x / np.abs(x).max())


def squelch(seed=0):
    """Мокрый «шмяк»."""
    r = np.random.default_rng(seed + 70)
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    x = bp(r.standard_normal(n), 250, 2200) * np.exp(-t * 11) * (1 + 0.8 * np.sin(2 * np.pi * 31 * t))
    x += 0.8 * np.sin(2 * np.pi * (180 - 120 * t) * t) * np.exp(-t * 16)
    return st(x / np.abs(x).max())


def glottal(n, f0, jitter, seed):
    r = np.random.default_rng(seed)
    t = np.arange(n) / SR
    f = f0 * (1 + jitter * filt(r.standard_normal(n), 30) * 8)
    ph = np.cumsum(f) / SR
    return (2 * (ph % 1) - 1) ** 3, t


def retch(seed=0, f0=120, long=True):
    """Позыв к рвоте: два «хык» + «бэээ» (форманты Э/А с хрипом) + плеск."""
    r = np.random.default_rng(seed + 90)
    out = []
    for k in range(2):                                   # «хык», «хык»
        n = int(0.22 * SR)
        g, t = glottal(n, f0 * 1.3, 0.02, seed + k)
        x = bp(g + 0.6 * r.standard_normal(n), 400, 1300) * np.sin(np.pi * t / 0.22) ** 0.6
        out += [x / np.abs(x).max(), np.zeros(int(0.12 * SR))]
    if long:
        n = int(0.9 * SR)
        g, t = glottal(n, f0, 0.04, seed + 5)
        g = g * (1 - 0.25 * t / 0.9)
        rasp = r.standard_normal(n) * (1 + np.sin(2 * np.pi * 37 * t))
        v = bp(g, 450, 900) + 0.7 * bp(g, 1100, 1800) + 0.9 * bp(rasp, 300, 2500)
        v *= np.minimum(1, t / 0.05) * np.minimum(1, (0.9 - t) / 0.25)
        out.append(v / np.abs(v).max())
        n = int(0.5 * SR)
        t = np.arange(n) / SR
        sp = filt(r.standard_normal(n), 1600) * np.exp(-t * 7) * (1 + np.sin(2 * np.pi * 19 * t))
        out.append(0.8 * sp / np.abs(sp).max())
    return st(np.concatenate(out))


def hiss(seed=3):
    r = np.random.default_rng(seed)
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = filt(r.standard_normal(n), 3000, 'high') * np.minimum(1, t / 0.05) * np.exp(-t * 3)
    return st(x / np.abs(x).max())


def place(buf, a, t, gain_db=0.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    a = a[:len(buf) - i]
    buf[i:i + len(a)] += a * 10 ** (gain_db / 20)


def gurgle(dur=1.2, seed=0):
    """Урчание живота: низкий шум с «пузырями» — свип частоты резонанса."""
    r = np.random.default_rng(seed + 300)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(int(dur * 7)):
        t0 = r.uniform(0, dur - 0.2)
        i0 = int(t0 * SR)
        m = int(r.uniform(0.08, 0.25) * SR)
        tt = np.arange(m) / SR
        f = r.uniform(120, 260) * (1 + 1.5 * tt / tt[-1])
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / tt[-1]) ** 2
        x[i0:i0 + m] += b[:n - i0]
    x += 0.4 * filt(r.standard_normal(n), 200) * (1 + np.sin(2 * np.pi * 3 * t))
    x *= np.minimum(1, t / 0.1) * np.minimum(1, (dur - t) / 0.2)
    return st(x / np.abs(x).max())


def tractor(dur=2.0, seed=1):
    """«Трактор на морозе»: пульсирующий низкий мотор, неровный."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    rate = 9 + 2 * np.sin(2 * np.pi * 0.7 * t)
    pulse = (np.sin(2 * np.pi * np.cumsum(rate) / SR) > 0.3).astype(float)
    pulse = filt(pulse, 80)
    x = filt(r.standard_normal(n), 300) * pulse + 0.5 * np.sin(2 * np.pi * 55 * t) * pulse
    x *= np.minimum(1, t / 0.1) * np.minimum(1, (dur - t) / 0.3)
    return st(x / np.abs(x).max())


def glass(seed=2):
    """Звон разбитого экрана."""
    r = np.random.default_rng(seed)
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    x = filt(r.standard_normal(n), 3000, 'high') * np.exp(-t * 6)
    for k in range(8):
        f = r.uniform(2500, 6500)
        t0 = r.uniform(0, 0.3)
        x += 0.4 * np.sin(2 * np.pi * f * t) * np.exp(-np.clip(t - t0, 0, None) * 18) * (t > t0)
    return st(x / np.abs(x).max())


def pop_snap(seed=4):
    """Хлопок пуговицы."""
    r = np.random.default_rng(seed)
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    x = filt(r.standard_normal(n), 1500, 'high') * np.exp(-t * 60) + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 50)
    return st(x / np.abs(x).max())


def rip(seed=5):
    """Рывок «эпиляции»: резкий шумовой свип вверх."""
    r = np.random.default_rng(seed)
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    x = r.standard_normal(n)
    out = np.zeros(n)
    for k, f in enumerate(np.linspace(500, 5000, 8)):
        seg = slice(int(k * n / 8), int((k + 1) * n / 8))
        out[seg] = bp(x, f * 0.7, min(f * 1.4, 20000))[seg]
    out *= np.exp(-t * 4)
    return st(out / np.abs(out).max())


def squeeze_tube(seed=6):
    """Выдавливание тюбика: тонкий писк + мокрый шорох."""
    r = np.random.default_rng(seed)
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = 0.5 * np.sin(2 * np.pi * np.cumsum(1400 + 600 * np.sin(np.pi * t / 0.6)) / SR) * np.sin(np.pi * t / 0.6)
    x += bp(r.standard_normal(n), 800, 3000) * 0.6 * np.sin(np.pi * t / 0.6)
    return st(x / np.abs(x).max())


def balloon_fart(dur=3.0, seed=8):
    """Сдувающийся шарик-пук: высота скачет, затухает к концу."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 160 + 90 * np.sin(2 * np.pi * 2.3 * t) * np.sin(2 * np.pi * 0.9 * t + 1) - 60 * t / dur
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    flut = filt(np.sign(np.sin(2 * np.pi * 21 * t)) * 0.35 + 0.65, 60)
    x = saw * flut + 0.5 * filt(r.standard_normal(n), 1200)
    x = filt(x, 1500, order=4) * np.minimum(1, t / 0.03) * (1 - t / dur) ** 0.5
    return st(x / np.abs(x).max())


def disco(dur=4.0, bpm=124):
    """Короткая «вечеринка бактерий»: бочка, хэт, писклявая мелодия."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    beat = 60 / bpm
    x = np.zeros(n)
    rng = np.random.default_rng(1)
    for b in range(int(dur / beat)):
        i = int(b * beat * SR)
        m = int(0.25 * SR)
        tt = np.arange(m) / SR
        kick = np.sin(2 * np.pi * (50 + 120 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 10)
        x[i:i + m] += kick[:n - i]
        j = int((b + 0.5) * beat * SR)
        h = filt(rng.standard_normal(int(0.05 * SR)), 7000, 'high') * np.exp(-np.arange(int(0.05 * SR)) / SR * 60)
        x[j:j + len(h)] += 0.3 * h[:max(0, n - j)]
    notes = [523, 659, 784, 659, 587, 698, 880, 698]
    for k in range(int(dur / (beat / 2))):
        i = int(k * beat / 2 * SR)
        m = int(beat / 2 * 0.8 * SR)
        tt = np.arange(m) / SR
        tone = np.sign(np.sin(2 * np.pi * notes[k % 8] * tt)) * np.exp(-tt * 6) * 0.15
        x[i:i + m] += tone[:max(0, n - i)]
    x *= np.minimum(1, t / 0.2) * np.minimum(1, (dur - t) / 0.4)
    return st(x / np.abs(x).max())


def coo(seed=9):
    """Голубиное «гуу»."""
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    f = 420 * (1 + 0.08 * np.sin(2 * np.pi * 9 * t)) * (1 - 0.15 * t / 0.5)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.5) ** 1.5
    x = filt(x + 0.1 * np.sin(4 * np.pi * np.cumsum(f) / SR), 1200)
    return st(x / np.abs(x).max())


# ---------------------------------------------------------------- 62-bullshit
def babble(dur=1.5, seed=0, f0=170):
    """Бормотание «бла-бла»: слоги из пилы через форманты гласных."""
    r = np.random.default_rng(seed + 400)
    out = []
    total = 0
    vowels = [(700, 1200), (500, 1800), (300, 2200), (450, 900)]
    while total < dur * SR:
        m = int(r.uniform(0.07, 0.14) * SR)
        tt = np.arange(m) / SR
        f = f0 * r.uniform(0.85, 1.25) * (1 + 0.1 * np.sin(2 * np.pi * 4 * tt))
        ph = np.cumsum(f) / SR
        g = 2 * (ph % 1) - 1
        f1, f2 = vowels[r.integers(len(vowels))]
        v = bp(g, f1 * 0.7, f1 * 1.3) + 0.6 * bp(g, f2 * 0.8, f2 * 1.2)
        v *= np.clip(np.sin(np.pi * tt / tt[-1]), 0, None) ** 0.8
        out += [v, np.zeros(int(r.uniform(0.01, 0.05) * SR))]
        total += m
    x = np.concatenate(out)[:int(dur * SR)]
    return st(x / (np.abs(x).max() + 1e-9))


def steps(dur=2.0, rate=7.0, seed=1):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    x = np.zeros(n)
    k = 0
    while k / rate < dur:
        i = int(k / rate * SR)
        m = int(0.05 * SR)
        tt = np.arange(m) / SR
        s = (np.sin(2 * np.pi * (140 + 60 * (k % 2)) * tt) + 0.5 * filt(r.standard_normal(m), 2000)) * np.exp(-tt * 70)
        x[i:i + m] += s[:max(0, n - i)]
        k += 1
    return st(x / np.abs(x).max())


def waves(dur=4.0, seed=2):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = filt(r.standard_normal(n), 900) * (0.4 + 0.6 * np.sin(np.pi * (t % 2.2) / 2.2) ** 2)
    x *= np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.5)
    return st(x / np.abs(x).max())


def gull(seed=3):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 1400 + 500 * np.sin(np.pi * t / 0.45) - 600 * t
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.45) ** 2
    x = x + 0.3 * np.sign(x) * np.abs(x) ** 0.5
    return st(filt(x, 3500) / np.abs(x).max())


def applause(dur=2.5, seed=4):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(int(dur * 60)):
        i = int(r.uniform(0, dur - 0.03) * SR)
        m = int(0.02 * SR)
        x[i:i + m] += bp(r.standard_normal(m), 800, 4000) * np.exp(-np.arange(m) / SR * 200) * r.uniform(0.3, 1)
    x *= np.minimum(1, t / 0.3) * np.minimum(1, (dur - t) / 0.6)
    return st(x / np.abs(x).max())


def jingle():
    """Телезаставка гороскопа: восходящее арпеджио колокольчиков."""
    notes = [523, 659, 784, 1047, 1319]
    n = int(1.6 * SR)
    x = np.zeros(n)
    for k, f in enumerate(notes):
        i = int(k * 0.12 * SR)
        m = n - i
        tt = np.arange(m) / SR
        x[i:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2.76 * f * tt)) * np.exp(-tt * 3.5)
    return st(x / np.abs(x).max())


def crackle(dur=3.0, seed=5):
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = filt(r.standard_normal(n), 600) * 0.4
    for k in range(int(dur * 25)):
        i = int(r.uniform(0, dur - 0.01) * SR)
        m = int(0.006 * SR)
        x[i:i + m] += filt(r.standard_normal(m), 3000, 'high') * r.uniform(0.5, 1.5)
    x *= np.minimum(1, t / 0.4) * np.minimum(1, (dur - t) / 0.4)
    return st(x / np.abs(x).max())


def alarm(dur=2.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    gate = ((t % 0.5) < 0.25).astype(float)
    x = np.sign(np.sin(2 * np.pi * 3100 * t)) * gate * 0.6
    return st(filt(x, 6000))
