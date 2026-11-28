"""Звук части 1 v2 (15,5 мин): голоса (voice/clips, выровнены prep_voice.py), музыка кодом по настроению сцен (music.py),
SFX Botanica через sfxkit + синтезированные звуки места (в паке их нет): сердцебиение, гудок, шлепки слизи, ведро,
вода душа, лента приёмника. Без рекламы. Пишет build/mix.wav и build/review/*.mp3."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import wave
import numpy as np
from scipy.signal import butter, sosfilt
import banner
import sound
import sfxkit
from music import music
from timeline import DUR, ON, TAKES, S, E, SCENES, KEYS

SR = 48000
BR = banner.Breaks([], cy=960)
N = int(round(DUR * SR))
D = {k: E[k] - S[k] for k in KEYS}
RNG = np.random.default_rng(7)


def place(buf, y, t, db, pan=0.0):
    i = int(round(t * SR))
    if i < 0:
        y, i = y[-i:], 0
    c = min(len(y), len(buf) - i)
    if c > 0:
        g = 10 ** (db / 20)
        if y.ndim == 1:
            buf[i:i + c, 0] += y[:c] * g * np.sqrt((1 - pan) / 2) * 1.414
            buf[i:i + c, 1] += y[:c] * g * np.sqrt((1 + pan) / 2) * 1.414
        else:
            buf[i:i + c] += y[:c] * g


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, (lo, hi), 'band', fs=SR, output='sos'), x)


def env(n, a, d):
    tt = np.arange(n) / SR
    e = np.exp(-tt / d)
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def heartbeat():
    k = int(0.5 * SR)
    tt = np.arange(k) / SR
    out = np.zeros(k)
    for dt, f0, g in ((0.0, 70, 1.0), (0.17, 60, 0.7)):
        i = int(dt * SR)
        u = tt[:k - i]
        f = f0 * (0.6 + 0.4 * np.exp(-u / 0.04))
        out[i:] += g * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-u / 0.07)
    return out


def horn(dur=2.2, f=110):
    """протяжный гудок коридоров (низкий, без шума)"""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * m * tt + m) / m for m in (1, 2, 3, 5)) * 0.4
    e = np.minimum(1, tt / 0.15) * np.minimum(1, (dur - tt) / 0.4)
    return lp(y * e, 1400)


def squelch(dur=0.35):
    """шлепок вязкой слизи: низкий удар + мягкий влажный хвост (низкие частоты, без шипения)"""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    thud = np.sin(2 * np.pi * (90 * np.exp(-tt / 0.08) + 40) * tt) * np.exp(-tt / 0.07)
    wet = lp(RNG.normal(0, 1, n), 600, 3) * np.exp(-tt / 0.12) * 0.5
    return thud * 0.9 + wet


def clank(f=520, dur=0.9):
    """звон стального ведра / дужки"""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * m * tt) * np.exp(-tt / (0.25 / m)) / m for m in (1, 2.76, 5.4, 8.9))
    return y * 0.5


def splash(dur=0.8):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    return lp(RNG.normal(0, 1, n), 900, 3) * np.exp(-tt / 0.18) * 0.8


def water(dur):
    """струя душа — приглушённая, низкочастотная (без шипения)"""
    n = int(dur * SR)
    y = lp(RNG.normal(0, 1, n), 1200, 4) * 0.35
    e = np.minimum(1, np.arange(n) / (0.1 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.2 * SR))
    return y * e


def belt(dur):
    """гул и постукивание конвейерной ленты"""
    n = int(dur * SR)
    tt = np.arange(n) / SR
    y = 0.3 * np.sin(2 * np.pi * 48 * tt) + 0.15 * np.sin(2 * np.pi * 96 * tt)
    for k in np.arange(0, dur, 0.42):
        i = int(k * SR)
        m = min(n - i, int(0.06 * SR))
        y[i:i + m] += np.sin(2 * np.pi * 180 * tt[:m]) * np.exp(-tt[:m] / 0.015) * 0.6
    return y


def steps(dur, rate=1.6, f=70):
    """шаги толпы босиком по металлу — мягкие низкие удары"""
    n = int(dur * SR)
    y = np.zeros(n)
    for k in np.arange(0, dur, 1 / rate):
        t0 = k + RNG.uniform(0, 0.25)
        i = int(t0 * SR)
        m = min(n - i, int(0.12 * SR))
        if m > 0:
            tt = np.arange(m) / SR
            y[i:i + m] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.03) * RNG.uniform(0.4, 1)
    return y


def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    sc = {name: (t0, t1) for name, t0, t1, _ in SCENES}
    # пробуждение: строки перечня и сердце
    A(fx, 'power-up', 0.1, gain_db=-22, label='система включается')
    for k, tt in enumerate((S['A01'] + 0.2, S['A01'] + 2.5, S['A01'] + 4.9)):
        A(fx, 'confirm', tt, gain_db=-21, label=f'успешно {k + 1}')
    for k in range(10):
        place(fx, heartbeat(), 0.5 + k * 0.9, -12 - k * 0.6)
    for k in range(6):
        place(fx, heartbeat(), S['A03'] + k * 0.8, -11)
    for name, t0, t1, _ in SCENES[1:]:
        A(fx, 'whoosh-short', t0, align='peak', gain_db=-27, label=f'→ {name}')
    A(fx, 'impact', S['A04'] + 0.05, align='peak', gain_db=-17, label='Эй!')
    # коридор: гул шагов, гудок, полусфера, сканер
    for name in ('corridor', 'slump', 'cube', 'yorka_talk', 'walk', 'rumors', 'lame', 'party', 'leave'):
        if name in sc:
            t0, t1 = sc[name]
            place(fx, steps(t1 - t0, 1.3), t0, -24, pan=0.3)
    place(fx, horn(2.4, 98), S['A16'] + D['A16'] * 0.36, -16)
    A(fx, 'scan', S['A20'] + 1.0, gain_db=-19, label='полусфера ползёт')
    A(fx, 'scan', S['A20'] + D['A20'] * 0.6, gain_db=-17, label='лазеры')
    A(fx, 'click', S['A21'] + D['A21'] * 0.25, gain_db=-14, label='щелчок под потолком')
    A(fx, 'click', S['A21'] + D['A21'] * 0.55, gain_db=-12, label='щелчок в голове')
    A(fx, 'glitch-text', S['A22'], gain_db=-17, label='интерфейс')
    A(fx, 'confirm', S['A22'] + D['A22'] * 0.7, gain_db=-17, label='активация')
    # ниша: дверца, вода, уколы, кубик
    A(fx, 'confirm', S['A27'], gain_db=-19, label='опознание')
    A(fx, 'whoosh-deep', S['A27'] + 0.6, gain_db=-20, label='дверца вверх')
    place(fx, water(1.2), S['A28'] + 3.0, -22)
    place(fx, water(1.0), S['A28'] + 5.0, -24)
    for k, f in enumerate((0.08, 0.2, 0.32)):
        A(fx, 'impact', S['A29'] + D['A29'] * f, align='peak', gain_db=-16, label=f'укол {3 - k}')
    A(fx, 'pop', S['A29'] + D['A29'] * 0.62, gain_db=-16, label='кубик')
    # пощёчины, локоть
    A(fx, 'impact', S['A36'] + D['A36'] * 0.92, align='peak', gain_db=-11, label='пощёчина 1')
    A(fx, 'impact', S['A37'] + D['A37'] * 0.42, align='peak', gain_db=-10, label='пощёчина 2')
    for k in range(4):
        place(fx, heartbeat(), S['A39'] + k * 0.6, -9)
    # меню
    for k in range(9):
        A(fx, 'select-soft', S['A46'] + k * 1.2 if k < 4 else S['A47'] + (k - 4) * 1.1, gain_db=-22, label='строка меню')
    A(fx, 'error', S['A46'] + D['A46'] * 0.62, gain_db=-20, label='недоступно')
    # игровой вызов
    A(fx, 'power-up', S['A50'] - 0.1, gain_db=-16, label='экран')
    A(fx, 'impact', S['A52'] + D['A52'] * 0.22, align='peak', gain_db=-14, label='толчок 58-го')
    A(fx, 'confirm', S['A52'] + D['A52'] * 0.75, gain_db=-17, label='успел')
    for k in range(12):
        A(fx, 'select', S['A54'] + 1.0 + k * 0.45, gain_db=-21, label='ход')
    A(fx, 'confirm', S['A54'] + D['A54'] * 0.9, gain_db=-14, label='ПОБЕДА')
    A(fx, 'error', S['A55'] + 1.8, gain_db=-17, label='в счёт долга')
    # блок слизи
    for name in ('ring', 'tooth', 'conveyor', 'bucket', 'kick', 'bars', 'trip', 'receiver'):
        if name in sc:
            t0, t1 = sc[name]
            for k in np.arange(t0 + 0.5, t1, 1.7):
                place(fx, squelch(), k + RNG.uniform(0, 0.6), -26, pan=RNG.uniform(-0.6, 0.6))
            for k in np.arange(t0 + 1.0, t1, 3.1):
                place(fx, clank(RNG.uniform(420, 640)), k, -30, pan=RNG.uniform(-0.6, 0.6))
    for name in ('conveyor', 'receiver', 'count'):
        if name in sc:
            t0, t1 = sc[name]
            place(fx, belt(t1 - t0), t0, -26)
    place(fx, squelch(), S['A63'] + 0.4, -14)
    place(fx, squelch(), S['A63'] + 1.0, -14)
    place(fx, clank(560), S['A63'] + D['A63'] * 0.45, -18)
    place(fx, clank(480, 1.2), S['A64'] + 0.15, -12)
    place(fx, splash(), S['A64'] + 0.3, -14)
    A(fx, 'impact', S['A70'] + D['A70'] * 0.6 + 0.4, align='peak', gain_db=-13, label='подножка')
    # душ
    A(fx, 'error', S['A74'], gain_db=-17, label='писк — душ')
    d = S['A75']
    place(fx, water(2.0), d, -18)
    place(fx, water(2.2), d + 3.6, -18)
    A(fx, 'error', E['A75'] - 2.6, gain_db=-19, label='сол за душ')
    # обед, сон
    place(fx, horn(1.0, 110), S['A76'] - 0.3, -20)
    # медблок, понижение, клукс
    A(fx, 'error', S['A93'], gain_db=-15, label='медблок закрыт')
    place(fx, horn(2.6, 92), S['C03'] + 0.3, -15)
    A(fx, 'error', S['C06'], gain_db=-15, label='уйти')
    A(fx, 'power-down', S['C07'] + D['C07'] * 0.55, gain_db=-14, label='понижение')
    A(fx, 'glitch-text', S['C07'] + D['C07'] * 0.6, gain_db=-15, label='УРН')
    A(fx, 'error', S['C09'], gain_db=-18, label='долг 10')
    A(fx, 'whoosh-short', S['C13'] + D['C13'] * 0.72, gain_db=-16, label='жвачка летит')
    A(fx, 'pop', S['C13'] + D['C13'] * 0.72 + 0.7, gain_db=-16, label='поймал')
    A(fx, 'confirm', S['C15'] + D['C15'] * 0.65, gain_db=-17, label='палец к квадратику')
    A(fx, 'whoosh-deep', S['C15'] + D['C15'] * 0.7, gain_db=-20, label='крышка вверх')
    A(fx, 'click', S['C16'] + D['C16'] * 0.33, gain_db=-12, label='шлепок по плафону')
    A(fx, 'power-down', S['C16'] + D['C16'] * 0.34, gain_db=-20, label='свет гаснет')
    A(fx, 'error', S['C17'], gain_db=-19, label='долг 11')
    return fx


def load_voice():
    voice = np.zeros((N, 2))
    for k, take in enumerate(TAKES):
        data = sound.load_stereo(take, SR)
        i = round(ON[k] * SR)
        c = min(len(data), N - i)
        voice[i:i + c] += data[:c]
    return voice


def duck(x, voice, depth, win=4800):
    e = np.abs(voice).max(1)
    e = np.convolve(e, np.ones(win) / win, 'same')
    g = 1 - depth * np.clip(e / (np.percentile(e, 95) * 0.4 + 1e-9), 0, 1)
    return x * g[:, None]


def loudness(a):
    r = subprocess.run([paths.ffmpeg(), '-hide_banner', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                        '-af', 'ebur128', '-f', 'null', '-'], input=a.astype('<f4').tobytes(), capture_output=True)
    line = [x for x in r.stderr.decode().splitlines() if x.strip().startswith('I:')][-1]
    return float(line.split()[1])


def write_mp3(path, a):
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-c:a', 'libmp3lame', '-b:a', '192k', str(path)],
                   input=np.clip(a, -1, 1).astype('<f4').tobytes(), check=True)


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE)
    voice = load_voice()
    mus = duck(music(N, SR), voice, 0.55) * 10 ** (-5 / 20)
    fx = duck(sfx(kit), voice, 0.4)
    content = voice + mus + fx
    k = 10 ** ((-16.0 - loudness(content)) / 20)
    content, voice, mus, fx = content * k, voice * k, mus * k, fx * k
    r = subprocess.run([paths.ffmpeg(), '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                        '-af', 'alimiter=limit=0.89:attack=3:release=60:level=disabled', '-f', 'f32le', '-'],
                       input=content.astype('<f4').tobytes(), capture_output=True, check=True)
    content = np.frombuffer(r.stdout, '<f4').reshape(-1, 2).astype(np.float64)[:N]
    data = BR.audio(content, SR)
    out = paths.build(HERE) / 'mix.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    write_mp3(rev / 'voice_only.mp3', voice)
    write_mp3(rev / 'music_only.mp3', mus)
    print('OK mix', round(len(data) / SR, 2), 's')
