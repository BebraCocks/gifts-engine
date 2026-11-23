"""Звук «Насрать на вентилятор»: голос + SFX Botanica (sfxkit) + кодом: гул мотора, удары лопасти, шлепки брызг,
шипение распыления. Пишет build/mix.wav и build/review/{sfx_only,mix,voice_only}.mp3 + sfx_cues.txt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import subprocess
import wave
import numpy as np
from scipy.signal import butter, sosfilt
import banner
import sound
import sfxkit
from timeline import DUR, ON, END, S, E, TAKES, KEYS
from events import AD_STOPS

SR = 48000
BR = banner.Breaks(AD_STOPS, cy=960)
N = int(round(DUR * SR))


def filt(x, f, kind='low', order=2):
    return sosfilt(butter(order, f, kind, fs=SR, output='sos'), x)


def st(x):
    return np.stack([x, x], 1)


def fan_hum(dur, speed=1.0, seed=0):
    """Гул вентилятора: мотор 100 Гц + шум воздуха с модуляцией частотой прохода лопастей (65 Гц при полной скорости)."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    sp = np.full(n, speed) if np.isscalar(speed) else speed
    ph = np.cumsum(65 * sp) / SR
    air = filt(r.standard_normal(n), 1800) * (0.55 + 0.45 * np.sin(2 * np.pi * ph)) * sp
    motor = 0.25 * np.sin(2 * np.pi * 100 * t) * np.minimum(1, sp * 2)
    x = air * 0.6 + motor
    return st(x / (np.abs(x).max() + 1e-9))


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


def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    wipes = {'L05', 'L09', 'L11', 'K14', 'L16'}
    for k in KEYS[1:]:
        t = S[k] - 0.12
        if k in wipes:
            place(fx, splat(int(k[1:])), t - 0.15, -12)
            A(fx, 'whoosh-organic', t, align='peak', gain_db=-14, label='переход-клякса')
        else:
            A(fx, 'whoosh-short', t, align='peak', gain_db=-18, label='смена сцены')
    # гул вентилятора: всё время, где вентилятор крутится (громкость по сценам)
    hum_gain = {'L01': -20, 'L02': -19, 'L03': -21, 'L05': -23, 'L08': -19, 'L11': -22, 'K12': -20, 'L13': -24,
                'L15': -25}
    for k, g in hum_gain.items():
        d = E[k] - S[k] + 0.5
        sp = None
        if k == 'L02':                       # разгон до 1300 об/мин
            tt = np.arange(int(d * SR)) / SR
            sp = 1 - (1 - np.clip(tt / 4.0, 0, 1)) ** 3
        h = fan_hum(d, 1.0 if sp is None else sp, seed=len(k) + int(k[1:]))
        n = len(h)
        env = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (0.15 * SR))
        place(fx, h * env[:, None], S[k] - 0.12, g)
    # 1. хук
    A(fx, 'error', S['L01'] + 2.6, gain_db=-12, label='НЕ ПОВТОРЯТЬ')
    for i in range(3):
        A(fx, 'select', S['L01'] + 3.8 + i * 0.15, gain_db=-16, label='формула')
    # 2. размеры
    A(fx, 'power-up', S['L02'] + 0.1, gain_db=-16, label='разгон вентилятора')
    A(fx, 'stretch', S['L02'] + 1.0, gain_db=-16, label='40 см')
    A(fx, 'counter', S['L02'] + 0.3, gain_db=-17, label='обороты')
    # 3. скорость кончика
    A(fx, 'riser', S['L03'] + 2.0, align='end', gain_db=-16, label='стрелка 100 км/ч')
    A(fx, 'whoosh', S['L03'] + 1.8 + 0.5, align='peak', gain_db=-15, label='машина')
    # 4. три лопасти, 65 ударов
    for k in range(3):
        A(fx, 'pop', S['L04'] + 0.2 + k * 0.25, gain_db=-14, label=f'лопасть {k + 1}')
    A(fx, 'counter', S['L04'] + 1.2, gain_db=-14, label='65 ударов')
    # 5. весы, присаживается
    A(fx, 'cartoon-hit', S['L05'] + 0.45, gain_db=-12, label='на весы')
    A(fx, 'confirm', S['L05'] + 1.3, gain_db=-15, label='130 г')
    A(fx, 'cartoon-move', S['L05'] + 3.2, gain_db=-15, label='присаживается')
    A(fx, 'glitch-text', S['L05'] + 3.6, gain_db=-17, label='цензура')
    A(fx, 'cartoon-move', E['L05'] - 0.4, gain_db=-14, file='falling', label='отпускает')
    # 7. удар
    place(fx, whack(1), S['L07'] + 0.25, -6)
    A(fx, 'impact', S['L07'] + 0.25, align='peak', gain_db=-10, label='БАМ')
    place(fx, spray(1.2, 2), S['L07'] + 0.3, -20)
    for k in range(3):
        A(fx, 'cartoon-hit', S['L07'] + 1.6 + 0.5 + k * 1.2, gain_db=-17, label='подача теннисиста')
    # 8. шесть ударов и облако
    for k in range(6):
        place(fx, whack(10 + k, 80 + 12 * k), S['L08'] + 0.3 + k * 0.32, -10)
    place(fx, spray(2.4, 3), S['L08'] + 1.2, -16)
    A(fx, 'granular-move', S['L08'] + 1.3, gain_db=-15, label='облако брызг')
    # 9. веер до стены
    place(fx, spray(1.2, 4), S['L09'] + 0.8, -16)
    for k in range(10):
        place(fx, splat(20 + k), S['L09'] + 1.75 + k * 0.03, -15)
    A(fx, 'pop', E['L09'] - 2.6, gain_db=-15, label='1/7 с')
    # 10. моргание
    cyc = 1.6
    u = 0.0
    while u < E['K10'] - S['K10']:
        place(fx, splat(40 + int(u * 10)), S['K10'] + u + 0.14, -14)
        u += cyc
    A(fx, 'error', S['K10'] + 2.0, gain_db=-13, label='НЕ УСПЕЛ')
    # 11. стены, шторы, ТВ — и в лицо
    for i in range(46):
        if i % 3 == 0:
            place(fx, splat(60 + i), S['L11'] + 0.2 + (i / 46) * 2.6, -13)
    d11 = E['L11'] - S['L11']
    A(fx, 'whoosh-short', S['L11'] + d11 - 3.4, align='peak', gain_db=-13, label='крупный план')
    for k in range(4):
        place(fx, splat(120 + k), S['L11'] + d11 - 3.4 + 1.2 + k * 0.05, -9)
    A(fx, 'voice', S['L11'] + d11 - 1.6, gain_db=-16, label='реакция')
    # 12. режим поворота
    A(fx, 'transform', S['K12'] + 0.6, gain_db=-14, label='режим поворота')
    place(fx, spray(6.0, 5), S['K12'] + 0.8, -21)
    for k in range(18):
        place(fx, splat(200 + k), S['K12'] + 1.0 + k * 0.32, -16)
    # F1. друзья — «веснушки»
    place(fx, spray(0.7, 11), S['F1'] + 0.6, -15)
    for k in range(8):
        place(fx, splat(300 + k), S['F1'] + 1.0 + k * 0.12, -14)
    A(fx, 'sparkle', S['F1'] + 1.6, gain_db=-14, label='фильтр Веснушки')
    for j, f in enumerate((0.5, 0.66, 0.82)):
        A(fx, 'select-soft', S['F1'] + (E['F1'] - S['F1']) * f, gain_db=-13, label='галочка')
    # C1. кот-леопард
    for k in range(6):
        place(fx, splat(400 + k), S['C1'] + 0.4 + k * 0.17, -16)
    A(fx, 'transform', S['C1'] + 1.4, gain_db=-14, label='КОТ -> ЛЕОПАРД')
    place(fx, meow(), S['C1'] + (E['C1'] - S['C1']) * 0.55, -9)
    A(fx, 'impact', S['C1'] + (E['C1'] - S['C1']) * 0.55 + 0.3, align='peak', gain_db=-13, label='ОБИДЕЛСЯ')
    # T1. телевизор: щелчки пульта, коричневый шум
    place(fx, tv_static(E['T1'] - S['T1'] + 0.3), S['T1'] - 0.1, -24)
    u = 0.2
    while u < E['T1'] - S['T1']:
        A(fx, 'click', S['T1'] + u, gain_db=-15, label='пульт')
        u += 0.35 * 2
    A(fx, 'cartoon-hit', S['T1'] + (E['T1'] - S['T1']) * 0.62, gain_db=-11, label='КОРИЧНЕВЫЙ')
    # 13. запах
    A(fx, 'bed', S['L13'], gain_db=-24, dur=(6, 200), tags=('dark',), label='тяжёлый воздух')
    A(fx, 'sub-drop', E['L13'] - 2.2, gain_db=-14, label='запах в коридоре')
    A(fx, 'voice', E['L13'] - 1.4, gain_db=-15, label='сосед')
    # 14. уборка: шкалы, «НИКОГДА», мусорка
    for k in range(3):
        A(fx, 'foley', S['K14'] + 0.3 + k * 0.6, gain_db=-17, exclude_tags=('bassy',), label='трёт стены')
    A(fx, 'confirm', S['K14'] + 1.4, gain_db=-15, label='стены 100%')
    A(fx, 'confirm', S['K14'] + 2.0, gain_db=-15, label='потолок 100%')
    A(fx, 'error', S['K14'] + 2.3, gain_db=-12, label='репутация 0%')
    A(fx, 'impact', S['K14'] + 3.0, align='peak', gain_db=-11, label='НИКОГДА')
    d14 = E['K14'] - S['K14']
    A(fx, 'cartoon-move', S['K14'] + d14 * 0.72, gain_db=-14, label='бросок')
    A(fx, 'cartoon-hit', S['K14'] + d14 * 0.72 + 0.9, gain_db=-11, label='в мусорку')
    # 15. идиома
    A(fx, 'scan', S['L15'] + 0.4, gain_db=-16, label='SH*T HITS THE FAN')
    A(fx, 'glitch', S['L15'] + (E['L15'] - S['L15']) * 0.55, gain_db=-14, label='всё к чертям')
    # P1. сантехник
    A(fx, 'cartoon-move', S['P1'], gain_db=-15, label='сантехник входит')
    place(fx, sniff(), S['P1'] + 1.4, -11)
    place(fx, sniff(1), S['P1'] + 1.75, -11)
    A(fx, 'glitch-text', S['P1'] + 1.6, gain_db=-17, label='зеленеет')
    for k in range(4):
        A(fx, 'select', S['P1'] + 2.4 + k * 0.12, gain_db=-17, label='набирает номер')
    A(fx, 'popup', S['P1'] + 2.4 + 0.6, gain_db=-12, label='Алло, экзорцист?')
    # 16. мама
    A(fx, 'click', S['L16'] + 1.55, gain_db=-10, label='ручка двери')
    A(fx, 'impact', S['L16'] + 1.9, align='peak', gain_db=-10, label='!')
    A(fx, 'sub-drop', S['L16'] + 2.2, gain_db=-12, label='МАМА?!')
    # --- пуки, рвота и прочие мерзкие звуки (кодом) ---
    place(fx, fart(0.25, 230, 0.1, seed=1, squeak=True), S['L01'] + 1.3, -17)          # колбаска нервничает
    place(fx, fart(0.9, 85, 0.6, seed=2, fall=0.35), E['L05'] - 0.75, -8)               # «…и отпускаешь»
    place(fx, plop(), E['L05'] - 0.05, -14)
    A(fx, 'voice', S['L05'] + 3.4, gain_db=-14, file='oppss', label='присел')
    place(fx, squelch(1), S['L07'] + 0.25, -7)                                          # первый удар — шмяк
    for k in range(6):
        place(fx, squelch(10 + k), S['L08'] + 0.32 + k * 0.32, -15)
    d11 = E['L11'] - S['L11']
    place(fx, squelch(20), S['L11'] + d11 - 3.4 + 1.2, -8)                              # в лицо
    place(fx, retch(1, 125), S['L11'] + d11 - 3.4 + 1.7, -8)                            # герой блюёт
    dF = E['F1'] - S['F1']
    A(fx, 'voice', S['F1'] + 1.05, gain_db=-12, file='scared-2', label='друзья в шоке')
    place(fx, retch(2, 135, long=False), S['F1'] + dF * 0.62, -9)                     # друг давится
    place(fx, fart(0.5, 110, 0.4, seed=3), S['F1'] + dF * 0.84, -13)                    # «…и с ароматом»
    place(fx, hiss(), S['C1'] + (E['C1'] - S['C1']) * 0.55 + 0.75, -12)                 # кот шипит
    place(fx, fart(0.3, 200, 0.1, seed=4, squeak=True), S['T1'] + (E['T1'] - S['T1']) * 0.62 + 0.15, -15)
    place(fx, fart(1.4, 70, 0.7, seed=5, fall=0.2), S['L13'] + 0.3, -18)               # «хуже всего — запах»
    place(fx, retch(3, 115), S['L13'] + (E['L13'] - S['L13']) * 0.8, -11)               # сосед в коридоре
    place(fx, retch(4, 105), S['P1'] + 1.9, -8)                                         # сантехник
    A(fx, 'cartoon', S['P1'] + 3.3, gain_db=-19, file='dizzy-birds', label='сантехник поплыл')
    place(fx, retch(5, 128, long=False), S['K14'] + 0.9, -14)                          # уборка
    A(fx, 'cartoon', S['K14'] + 3.3, gain_db=-17, file='crickets', label='неловкая тишина')
    place(fx, sad_trombone_fart(), S['L15'] + (E['L15'] - S['L15']) * 0.55 + 0.1, -9)   # «всё пошло к чертям»
    place(fx, fart(1.1, 90, 0.5, seed=6, fall=0.4), S['L16'] + 2.15, -7)                 # испуг перед мамой
    A(fx, 'voice', S['L16'] + 2.0, gain_db=-12, file='scared.flac', label='МАМА?!')
    return fx


def make_mix(kit):
    voice = np.zeros((N, 2))
    for k, take in enumerate(TAKES):
        data = sound.load_stereo(take, SR)
        i = round(ON[k] * SR)
        c = min(len(data), N - i)
        voice[i:i + c] += data[:c] * 0.9
    fx = sfx(kit)
    env = np.abs(voice).max(1)
    env = np.convolve(env, np.ones(2400) / 2400, 'same')
    fx *= (1 - 0.45 * np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1))[:, None]
    return voice, fx


def write_mp3(path, a):
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-c:a', 'libmp3lame', '-b:a', '192k', str(path)], input=np.clip(a, -1, 1).astype('<f4').tobytes(),
                   check=True)


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE)
    voice, fx = make_mix(kit)
    content = voice + fx
    pk = np.abs(content).max()
    if pk > 0.95:
        content *= 0.95 / pk
        fx *= 0.95 / pk
    data = BR.audio(content, SR)
    out = paths.build(HERE) / 'mix.wav'
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    write_mp3(rev / 'voice_only.mp3', BR.audio(voice, SR, banner=False))
    print('OK mix', round(len(data) / SR, 2), 's; peak', round(float(pk), 2))
