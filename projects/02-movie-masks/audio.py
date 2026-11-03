"""Звук: без диктора (ключа Fish Audio нет). Синтезированный саунд-дизайн по общей карте событий
+ полный звук баннера RubUp в паузе. Внешних аудиофайлов нет."""
import json
import sys
import wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from scipy import signal
import banner
import config
from events import DUR, AD_STOP, TRANSITIONS, MASK_LAND, FLIPS, CURTAIN, TITLES
from timeline import HAS_VOICE, VOICE_AT
import sound

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
rng = np.random.default_rng(20261103)
N = int(round(DUR * SR))
L = np.zeros(N); Rr = np.zeros(N)


def put(x, t, gl, gr=None):
    s = int(round(t * SR))
    if s < 0:
        x = x[-s:]; s = 0
    m = min(len(x), N - s)
    if m <= 0:
        return
    L[s:s + m] += x[:m] * gl
    Rr[s:s + m] += x[:m] * (gl if gr is None else gr)


def env(n, a, d):
    e = np.ones(n); ka, kd = int(a * SR), int(d * SR)
    if ka: e[:ka] = np.linspace(0, 1, ka)
    if kd: e[-kd:] *= np.linspace(1, 0, kd)
    return e


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x)


def lp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc / (SR / 2), output='sos'), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc / (SR / 2), 'high', output='sos'), x)


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


def noise(d):
    return rng.standard_normal(int(d * SR))


def sweep(d, f0, f1, q=1.2):
    n = int(d * SR); x = rng.standard_normal(n + 2400); out = np.zeros(n); blk = 960
    for s in range(0, n, blk):
        fc = f0 * (f1 / f0) ** (s / n)
        lo, hi = fc / (1 + 1 / q), min(SR / 2 * 0.98, fc * (1 + 1 / q))
        y = signal.sosfilt(signal.butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x[s:s + blk + 2400])
        out[s:s + blk] = y[2400:2400 + len(out[s:s + blk])]
    return norm(out)


def whoosh(t_peak, d=0.9, f0=300, f1=2600, g=0.4, pan=(1, 1)):
    x = sweep(d, f0, f1) * np.sin(np.linspace(0, np.pi, int(d * SR))) ** 1.8
    put(x, t_peak - d * 0.6, g * pan[0], g * pan[1])


def riser(t_end, d, f0, f1, g):
    x = sweep(d, f0, f1) * np.linspace(0, 1, int(d * SR)) ** 2.4
    put(x, t_end - d, g)


def impact(t, g=0.8, f_hi=85, f_lo=42, tail=0.9):
    tt = np.arange(int(1.6 * SR)) / SR
    thump = np.sin(2 * np.pi * np.cumsum(f_lo + (f_hi - f_lo) * np.exp(-tt * 9)) / SR) * np.exp(-tt * 3.0)
    click = lp(rng.standard_normal(len(tt)), 2600) * np.exp(-tt * 40)
    ir = rng.standard_normal(int(tail * SR)) * np.exp(-np.arange(int(tail * SR)) / SR * 5)
    rev = signal.fftconvolve(click, ir)[:len(tt)]
    put(thump * 0.85 + click * 0.45 + norm(rev) * 0.12, t, g)


def bell(t, f=164.8, g=0.35, d=4.0):
    tt = np.arange(int(d * SR)) / SR
    parts = [(0.5, 1.0, 1.2), (1.0, 0.8, 1.6), (1.19, 0.5, 2.2), (1.5, 0.45, 2.6), (2.0, 0.35, 3.0), (2.74, 0.2, 3.8), (3.0, 0.15, 4.5)]
    x = sum(a * np.sin(2 * np.pi * f * r * tt + rng.uniform(0, 6)) * np.exp(-tt * dk) for r, a, dk in parts)
    put(norm(x) * env(len(tt), 0.004, 0.3), t, g)


def bed(t0, t1, x_fn, g, pan=(1, 1), fade=0.5):
    d = t1 - t0; x = x_fn(d)
    put(norm(x) * env(len(x), fade, fade), t0, g * pan[0], g * pan[1])


# ---------------- хук: гримёрка ----------------
bed(0.0, 5.7, lambda d: lp(noise(d), 160), 0.06)                       # тон комнаты
for k in range(16):                                                    # лампы щёлкают, зажигаясь
    tt = np.arange(int(0.03 * SR)) / SR
    put(hp(rng.standard_normal(len(tt)), 2000) * np.exp(-tt * 300), 0.03 * k, 0.10, 0.10)
riser(MASK_LAND, 1.15, 250, 3400, 0.22)
impact(MASK_LAND, 0.85)
for f in FLIPS:                                                        # смена маски: шорох + удар
    whoosh(f, 0.22, 900, 3800, 0.22)
    impact(f, 0.35, 120, 60, 0.4)
whoosh(TRANSITIONS['mirror'], 1.3, 380, 2700, 0.42, (1.0, 0.5))
whoosh(TRANSITIONS['mirror'] + 0.15, 1.2, 420, 2400, 0.32, (0.4, 1.0))
tg = np.arange(int(1.4 * SR)) / SR                                    # звон стекла
put(norm(sum(np.sin(2 * np.pi * f * tg + rng.uniform(0, 6)) * np.exp(-tg * d) for f, d in ((2140, 4), (3310, 5), (4720, 6), (6180, 7)))), TRANSITIONS['mirror'] - 0.05, 0.12)

# ---------------- пригород (Крик) ----------------
def crickets(d):
    tn = np.arange(int(d * SR)) / SR; out = np.zeros(len(tn))
    for f, ph in ((4650, 0.0), (4320, 0.43), (4900, 0.71)):
        chirp = ((tn + ph) % 0.95 < 0.12) * (np.sin(2 * np.pi * 32 * tn) > 0)
        out += np.sin(2 * np.pi * f * tn) * lp(chirp.astype(float), 120, 1)
    return out
bed(5.3, 15.6, crickets, 0.035)
bed(5.3, 15.6, lambda d: bp(noise(d), 200, 700), 0.05)
riser(TRANSITIONS['window'], 0.8, 200, 2200, 0.25)
whoosh(TRANSITIONS['window'] + 0.1, 0.9, 300, 1800, 0.35)

# ---------------- Лондон ----------------
bed(15.3, 24.1, lambda d: lp(noise(d), 400), 0.07)                   # река и город
bell(16.45, 164.8, 0.30)                                               # удар часов
ev = json.loads((HERE / 'build' / 'events_3d.json').read_text())
for k, b in enumerate(ev['bursts']):
    if b > 24.1:
        continue
    pan = (0.6 + 0.4 * (k % 2), 1.0 - 0.4 * (k % 2))
    impact(b, 0.22, 70, 38, 1.2)
    tt = np.arange(int(1.4 * SR)) / SR                                 # треск искр
    crack = hp(rng.standard_normal(len(tt)), 1800) * (rng.random(len(tt)) < 0.004) * np.exp(-tt * 2.2)
    put(lp(crack, 7000) * 3.0, b + 0.08, 0.07 * pan[0], 0.07 * pan[1])
# напряжение перед паузой: два удара сердца
for t in (22.35, 22.75, 23.25, 23.6):
    impact(t, 0.28 if t in (22.35, 23.25) else 0.2, 60, 35, 0.3)

# ---------------- после рекламы: лепестки → Мадрид ----------------
whoosh(TRANSITIONS['petals'], 0.7, 600, 3200, 0.38)
def paper(d):
    n = int(d * SR); x = np.zeros(n)
    for _ in range(int(d * 26)):
        s = int(rng.uniform(0, n - 2000)); g = rng.standard_normal(1600) * np.hanning(1600)
        x[s:s + 1600] += bp(g, 2500, 7000)
    return x
bed(24.2, 32.7, paper, 0.05)
bed(24.2, 32.7, lambda d: bp(noise(d), 120, 500) * (0.7 + 0.3 * np.sin(np.arange(int(d * SR)) / SR * 6)), 0.05)
whoosh(TRANSITIONS['notes'], 0.8, 500, 3600, 0.4)
put(norm(paper(0.9)), TRANSITIONS['notes'] - 0.4, 0.18)

# ---------------- Бронкс ----------------
bed(32.4, 40.9, lambda d: lp(noise(d), 260), 0.08)                   # гул улиц
th = np.arange(int(0.5 * SR)) / SR                                    # далёкий гудок
put(lp(np.sign(np.sin(2 * np.pi * 349 * th)) + 0.6 * np.sign(np.sin(2 * np.pi * 440 * th)), 1800) * env(len(th), 0.03, 0.15), 35.2, 0.035)
for k in range(10):                                                    # шаги-щелчки по ступеням, как у танцующего героя
    tt = np.arange(int(0.08 * SR)) / SR
    put(bp(rng.standard_normal(len(tt)), 800, 3000) * np.exp(-tt * 60), 33.0 + k * 0.62, 0.06)
riser(TRANSITIONS['skyward'], 0.7, 300, 4000, 0.28)
whoosh(TRANSITIONS['skyward'] + 0.05, 0.7, 500, 2500, 0.32)

# ---------------- Готэм ----------------
bed(40.5, 49.0, lambda d: hp(noise(d), 1200), 0.06)                   # дождь
bed(40.5, 49.0, lambda d: lp(noise(d), 90), 0.10)                     # низкий гул города
for s in ev['strikes']:
    tt = np.arange(int(3.0 * SR)) / SR
    thunder = lp(rng.standard_normal(len(tt)), 220) * np.exp(-tt * 1.1) * (1 - np.exp(-tt * 18))
    put(norm(thunder), s + 0.12, 0.45)
    impact(s, 0.25, 90, 40, 0.6)
riser(TRANSITIONS['signal'], 0.9, 250, 5200, 0.25)
whoosh(TRANSITIONS['signal'], 0.8, 400, 3000, 0.3)

# ---------------- сцена ----------------
for k in range(5):                                                     # прожекторы включаются
    tt = np.arange(int(0.5 * SR)) / SR
    clunk = np.sin(2 * np.pi * (70 + 30 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14) + 0.3 * lp(rng.standard_normal(len(tt)), 1500) * np.exp(-tt * 50)
    put(clunk, 48.9 + k * 0.12, 0.30 * (0.7 + 0.3 * (k % 2)), 0.30 * (1.0 - 0.3 * (k % 2)))
bed(49.0, DUR, lambda d: lp(noise(d), 300), 0.045)                    # зал
whoosh(CURTAIN + 0.1, 1.2, 200, 900, 0.30)                            # занавес
impact(CURTAIN + 0.6, 0.5, 70, 40, 0.8)

# лёгкий акцент на появлении каждого титра
for t0, *_ in TITLES:
    whoosh(t0 + 0.2, 0.35, 1500, 5000, 0.08)


def make_mix():
    sfx = np.stack([L, Rr], 1)
    sfx *= 0.72 / (np.abs(sfx).max() + 1e-9)
    if HAS_VOICE:
        vox = np.zeros((N, 2))
        for path, offset, _ in VOICE_AT:
            x = sound.load_stereo(path, SR)
            s = int(round(offset * SR)); a = max(0, -s); m = min(len(x) - a, N - max(s, 0))
            vox[max(s, 0):max(s, 0) + m] += x[a:a + m]
        vox *= 0.86 / (np.abs(vox).max() + 1e-9)
        # эффекты уступают голосу: огибающая речи → приглушение до −7 дБ
        env_ = lp(np.abs(vox).mean(1), 6, 1)
        duck = 1 - 0.55 * np.clip(env_ / 0.05, 0, 1)
        mix = sfx * duck[:, None] * 0.8 + vox
        mix *= 0.89 / (np.abs(mix).max() + 1e-9)
        print('Озвучка Fish Audio + саунд-дизайн + звук баннера.')
    else:
        mix = sfx
        print('Дикторской озвучки нет: саунд-дизайн + звук баннера.')
    fade = int(0.35 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return BR.audio(mix, SR)


if __name__ == '__main__':
    data = make_mix()
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    print('build/mix.wav готов', f'{len(data) / SR:.2f} c')
