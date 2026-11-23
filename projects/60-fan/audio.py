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
from events import AD_STOP

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960)
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


def place(buf, a, t, gain_db=0.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    a = a[:len(buf) - i]
    buf[i:i + len(a)] += a * 10 ** (gain_db / 20)


def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    wipes = {'L05', 'L09', 'L11', 'L14', 'L16'}
    for k in KEYS[1:]:
        t = S[k] - 0.12
        if k in wipes:
            place(fx, splat(int(k[1:])), t - 0.15, -12)
            A(fx, 'whoosh-organic', t, align='peak', gain_db=-14, label='переход-клякса')
        else:
            A(fx, 'whoosh-short', t, align='peak', gain_db=-18, label='смена сцены')
    # гул вентилятора: всё время, где вентилятор крутится (громкость по сценам)
    hum_gain = {'L01': -20, 'L02': -19, 'L03': -21, 'L05': -23, 'L08': -19, 'L11': -22, 'L12': -20, 'L13': -24,
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
    # 6. замедленное падение
    A(fx, 'downlifter', S['L06'], gain_db=-15, label='slow-mo')
    A(fx, 'counter', S['L06'] + 0.2, gain_db=-18, label='таймер')
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
    while u < E['L10'] - S['L10']:
        place(fx, splat(40 + int(u * 10)), S['L10'] + u + 0.14, -14)
        u += cyc
    A(fx, 'error', S['L10'] + 2.0, gain_db=-13, label='НЕ УСПЕЛ')
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
    A(fx, 'transform', S['L12'] + 0.6, gain_db=-14, label='режим поворота')
    place(fx, spray(6.0, 5), S['L12'] + 0.8, -21)
    for k in range(18):
        place(fx, splat(200 + k), S['L12'] + 1.0 + k * 0.32, -16)
    # 13. запах
    A(fx, 'bed', S['L13'], gain_db=-24, dur=(6, 200), tags=('dark',), label='тяжёлый воздух')
    A(fx, 'sub-drop', E['L13'] - 2.2, gain_db=-14, label='запах в коридоре')
    A(fx, 'voice', E['L13'] - 1.4, gain_db=-15, label='сосед')
    # 14. уборка и мусорка
    for k in range(4):
        A(fx, 'foley', S['L14'] + 0.4 + k * 0.7, gain_db=-17, exclude_tags=('bassy',), label='трёт стены')
    A(fx, 'spinback', S['L14'] + 0.2, gain_db=-17, label='часы крутятся')
    d14 = E['L14'] - S['L14']
    A(fx, 'cartoon-move', S['L14'] + d14 * 0.6, gain_db=-14, label='бросок')
    A(fx, 'impact', S['L14'] + d14 * 0.6 + 0.9, align='peak', gain_db=-11, label='в мусорку')
    # 15. идиома
    A(fx, 'scan', S['L15'] + 0.4, gain_db=-16, label='SH*T HITS THE FAN')
    A(fx, 'glitch', S['L15'] + (E['L15'] - S['L15']) * 0.55, gain_db=-14, label='всё к чертям')
    # 16. мама
    A(fx, 'click', S['L16'] + 1.55, gain_db=-10, label='ручка двери')
    A(fx, 'impact', S['L16'] + 1.9, align='peak', gain_db=-10, label='!')
    A(fx, 'sub-drop', S['L16'] + 2.2, gain_db=-12, label='МАМА?!')
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
