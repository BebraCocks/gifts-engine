"""Звук «Реактивного пука»: голос + SFX Botanica (sfxkit) + синтезированные кодом пуки и гул струи + RubUp.
Пишет build/mix.wav и build/review/{sfx_only,mix,voice_only}.mp3 + sfx_cues.txt."""
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
rng = np.random.default_rng(59)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, 'low', fs=SR, output='sos'), x)


def fart(dur=0.6, f0=95, wet=1.0, seed=0, fall=0.35):
    """Мультяшный пук: пила 70–120 Гц с дрожанием амплитуды и шумом."""
    r = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 0.15 * np.sin(2 * np.pi * 7 * t) + 0.05 * r.standard_normal(n).cumsum() / np.sqrt(n)) * (1 - fall * t / dur)
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    flutter = 0.6 + 0.4 * np.sign(np.sin(2 * np.pi * (18 + 6 * r.random()) * t))
    flutter = lp(flutter, 60)
    x = saw * flutter + 0.35 * wet * r.standard_normal(n)
    x = lp(x, 900, 4)
    env = np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.12)
    x *= env
    x /= np.abs(x).max() + 1e-9
    return np.stack([x, x], 1)


def rumble(n, f=180, seed=1):
    r = np.random.default_rng(seed)
    x = lp(r.standard_normal(n), f, 4)
    x /= np.abs(x).max() + 1e-9
    return np.stack([x, np.roll(x, 300)], 1)


def place(buf, a, t, gain_db=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(a) <= 0:
        return
    if i < 0:
        a, i = a[-i:], 0
    a = a[:len(buf) - i]
    buf[i:i + len(a)] += a * 10 ** (gain_db / 20)


def env_seg(n, t0, t1, fade=0.3):
    t = np.arange(n) / SR
    return np.clip(np.minimum((t - t0) / fade, (t1 - t) / fade), 0, 1)


def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    starts = [S[k] - 0.12 for k in KEYS[1:]]
    wipes = {S[k] - 0.12 for k in ('L05', 'L09', 'L15', 'L16', 'L17')}
    for t in starts:
        if t in wipes:
            A(fx, 'whoosh-organic', t, align='peak', gain_db=-13, label='переход облаком газа')
        else:
            A(fx, 'whoosh-short', t, align='peak', gain_db=-17, label='смена сцены')
    # 1. хук
    for k, t in enumerate((0.15, 1.6, 3.1)):
        place(fx, fart(0.28 + 0.08 * k, 120 - 12 * k, seed=k), t, -20)
    for i in range(3):
        A(fx, 'select', S['L01'] + 4.6 + i * 0.18, gain_db=-16, label='формула')
    # 2. 14 облачков
    for i in range(14):
        A(fx, ['pop', 'select-soft'], S['L02'] + 0.3 + i * 2.5 / 14, gain_db=-17, label=f'пук {i + 1}')
    # 3. годы и счётчик
    d3 = E['L03'] - S['L03']
    A(fx, 'counter', S['L03'] + 0.4, gain_db=-14, label='счётчик пуков')
    A(fx, 'impact', S['L03'] + d3 * 0.82, align='peak', gain_db=-12, label='штамп 128 000')
    # 4. лифты
    d4 = E['L04'] - S['L04']
    A(fx, 'counter', S['L04'], gain_db=-15, label='литры')
    A(fx, 'granular-move', S['L04'] + 1.6, gain_db=-14, label='газ заполняет лифты')
    A(fx, 'confirm', S['L04'] + d4 - 0.1, gain_db=-15, label='до потолка')
    # 5. садится
    A(fx, 'cartoon-hit', S['L05'] + 0.55, gain_db=-11, label='приземление на стул')
    A(fx, 'click', S['L05'] + 2.2, gain_db=-13, label='секундомер')
    A(fx, 'coin', S['L05'] + 4.0, gain_db=-14, label='монета')
    place(fx, rumble(int(2.4 * SR), 120, 3) * env_seg(int(2.4 * SR), 0.2, 2.4, 0.8)[:, None], S['L05'] + 4.3, -16)
    # 6. скорость
    A(fx, 'riser', S['L06'] + 1.4, align='end', gain_db=-15, label='стрелка до 20 км/с')
    A(fx, 'whoosh-short', S['L06'] + 3.2, align='peak', gain_db=-15, label='пуля')
    A(fx, 'whoosh', S['L06'] + 3.9, align='peak', gain_db=-14, label='струя')
    A(fx, 'impact', S['L06'] + 5.0, align='peak', gain_db=-12, label='×22')
    # 7. стул ломается + первая струя
    A(fx, 'foley', S['L07'] + 0.35, gain_db=-9, file='demolition', label='стул в щепки')
    A(fx, 'cartoon-hit', S['L07'] + 0.38, gain_db=-12, label='удар')
    place(fx, fart(1.0, 85, seed=7, fall=0.2), S['L07'] + 0.3, -12)
    A(fx, 'impact', S['L07'] + 0.65, align='peak', gain_db=-14, label='штамп СТУЛ: ВСЁ')
    # 8. тяга и вес
    A(fx, 'whoosh-deep', S['L08'] + 0.2, gain_db=-15, label='истребитель')
    A(fx, 'select', S['L08'] + 0.8, gain_db=-15, label='шкала истребителя')
    A(fx, 'select', S['L08'] + 2.0, gain_db=-14, label='шкала струи')
    A(fx, 'boing', S['L08'] + 4.6, gain_db=-14, label='весы 70 кг')
    # 9. отсчёт и взлёт
    go = E['L09'] - 0.7
    d9 = go - S['L09']
    for k in range(3):
        A(fx, 'click', S['L09'] + k * max(0.3, d9 / 3), gain_db=-12, label=f'отсчёт {3 - k}')
    A(fx, 'riser-hit', go, align='peak', gain_db=-10, label='ПУСК')
    place(fx, fart(1.6, 70, seed=9, fall=0.3), go - 0.05, -8)
    # 10. перегрузка
    A(fx, 'counter', S['L10'] + 0.1, gain_db=-15, label='G-метр')
    A(fx, 'cartoon-move', S['L10'] + 4.8, gain_db=-14, label='пилот отключился')
    # 11–14 полёт
    A(fx, 'whoosh', S['L11'], align='peak', gain_db=-12, label='8 махов')
    A(fx, 'confirm', S['L11'] + 5.0, gain_db=-14, label='поза: сидя')
    A(fx, 'spinback', S['L12'] - 0.1, gain_db=-16, label='звук отстаёт')
    f12 = fart(1.8, 90, seed=12, fall=0.5)
    f12 *= np.linspace(1, 0.15, len(f12))[:, None]                 # удаляющийся «ПУУУК»
    place(fx, f12, S['L12'] + 0.3, -11)
    A(fx, 'sparkle', S['L13'] + 0.3, gain_db=-17, label='МКС')
    A(fx, 'pop', S['L13'] + (E['L13'] - S['L13']) * 0.8, gain_db=-15, label='почти!')
    A(fx, 'power-up', S['L14'] + 1.2, align='end', gain_db=-13, label='нагрев')
    A(fx, 'impact', S['L14'] + 2.0, align='peak', gain_db=-9, label='вспышка')
    # гул струи: от взлёта до вспышки + огонь, под паузой RubUp — уходит вместе с содержанием
    t0, t1 = S['L07'] + 0.35, E['L14'] + 0.3
    n = int((t1 - t0) * SR)
    r = rumble(n, 160, 5) * env_seg(n, 0, t1 - t0, 0.6)[:, None]
    place(fx, r, t0, -17)
    # 15. падающая звезда
    A(fx, 'sparkle-whoosh', S['L15'] + 0.1, gain_db=-12, label='падающая звезда')
    A(fx, 'sparkle', S['L15'] + (E['L15'] - S['L15']) * 0.55, gain_db=-14, label='желание')
    # 16. дом
    A(fx, 'ambience', S['L16'] - 0.1, gain_db=-24, file='night', dur=(3, 200), label='ночь')
    A(fx, 'pop', S['L16'] + 2.2, gain_db=-15, label='…и запах')
    # 17. заключение
    A(fx, 'paper', S['L17'] + 0.3, gain_db=-12, label='бланк')
    A(fx, 'impact', S['L17'] + 2.0, align='peak', gain_db=-10, label='штамп ЕСТЕСТВЕННЫЕ')
    A(fx, 'cartoon-hit', S['L17'] + 2.12, gain_db=-14, label='штамп ПРИЧИНЫ')
    A(fx, 'sparkle', E['L17'] - 2.0, gain_db=-15, label='нимб')
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
