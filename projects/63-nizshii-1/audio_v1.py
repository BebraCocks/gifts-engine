"""Звук части 1: голоса (voice/clips, выровнены по громкости prep_voice.py), музыка кодом (music.py),
SFX Botanica через sfxkit; удар сердца синтезирован (в паке нет). Без рекламы.
Пишет build/mix.wav и build/review/{sfx_only,mix,voice_only,music_only}.mp3 + sfx_cues.txt."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import wave
import numpy as np
import banner
import sound
import sfxkit
from music import music
from timeline import DUR, ON, TAKES, S, E, SCENES, KEYS

SR = 48000
BR = banner.Breaks([], cy=960)
N = int(round(DUR * SR))
D = {k: E[k] - S[k] for k in KEYS}
OK = [S['A01'] + 1.15, S['A01'] + 3.55, S['A01'] + 6.0]
BEATS = [OK[2] + i * 0.55 for i in range(3)]


def place(buf, y, t, db):
    i = int(round(t * SR))
    c = min(len(y), len(buf) - i)
    if c > 0:
        buf[i:i + c] += (y[:c, None] if y.ndim == 1 else y[:c]) * 10 ** (db / 20)


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


def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    A(fx, 'power-up', 0.1, gain_db=-20, label='система включается')
    for k, ok in enumerate(OK):
        A(fx, 'confirm', ok, gain_db=-20, label=f'успешно {k + 1}')
    for j in range(4):
        A(fx, 'click', OK[0] + 0.55 + j * 0.3, gain_db=-18, file='metalic', label='конечность на месте')
    for b in BEATS:
        place(fx, heartbeat(), b - 0.02, -8)
    for tt in (S['A02'] + 3.2, S['A02'] + 3.9):
        place(fx, heartbeat(), tt, -12)                                       # боль пульсирует
    for name, t0, t1, _ in SCENES[1:]:                                       # мягкий переход между сценами
        A(fx, 'whoosh-short', t0, align='peak', gain_db=-24, label=f'→ {name}')
    A(fx, 'impact', S['A04'] + 0.06, align='peak', gain_db=-15, label='Эй!')
    A(fx, 'scan', S['A07'] + D['A07'] * 0.3, gain_db=-20, label='полусфера едет')
    A(fx, 'scan', S['A08'], gain_db=-17, label='сканер')
    A(fx, 'glitch-text', S['A08'] + 0.7, gain_db=-17, label='интерфейс')
    A(fx, 'confirm', S['A08'] + D['A08'] * 0.8, gain_db=-17, label='активация')
    for k in range(3):
        A(fx, 'click', S['A09'] + D['A09'] * (0.38 + k * 0.055), gain_db=-15, label='укол')
    A(fx, 'pop', S['A09'] + D['A09'] * 0.55, gain_db=-17, label='кубик')
    A(fx, 'impact', S['A13'] + D['A13'] * 0.35, align='peak', gain_db=-12, label='пощёчина')
    for k in range(5):
        A(fx, 'select-soft', S['A15'] + 0.4 + k * D['A15'] * 0.16, gain_db=-20, label='строка меню')
    A(fx, 'power-up', S['A17'] - 0.1, gain_db=-17, label='экран загорелся')
    A(fx, 'impact', S['A18'] + 0.3, align='peak', gain_db=-16, label='толчок 58-го')
    for k in range(7):
        A(fx, 'select', S['A18'] + D['A18'] * (0.3 + k * 0.035), gain_db=-19, label='ход')
    A(fx, 'confirm', S['A18'] + D['A18'] * 0.6, gain_db=-15, label='победа')
    A(fx, 'error', S['A18'] + D['A18'] * 0.8, gain_db=-17, label='в счёт долга')
    A(fx, 'impact', S['A20'] + D['A20'] * 0.28, align='peak', gain_db=-13, label='пинок ведра')
    A(fx, 'error', S['A20'] + D['A20'] * 0.7, gain_db=-18, label='душ в долг')
    A(fx, 'impact', S['A22'] + D['A22'] * 0.45, align='peak', gain_db=-18, label='отрежут руку')
    for k, f in enumerate((0.12, 0.22, 0.32, 0.42, 0.52)):
        A(fx, 'select-soft', S['A23'] + D['A23'] * f, gain_db=-19, label=f'раса {k + 1}')
    A(fx, 'sparkle', S['A23'] + D['A23'] * 0.62, gain_db=-17, label='эльфы')
    A(fx, 'error', S['A25'] + 0.3, gain_db=-16, label='медблок закрыт')
    A(fx, 'power-down', S['A28'] - 0.1, gain_db=-15, label='понижение до УРН')
    A(fx, 'glitch-text', S['A28'], gain_db=-16, label='УРН')
    A(fx, 'pop', S['B29'] + D['B29'] * 0.55, gain_db=-17, label='жвачка')
    A(fx, 'power-down', E['A30'] - 0.2, gain_db=-18, label='свет гаснет')
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
    env = np.abs(voice).max(1)
    env = np.convolve(env, np.ones(win) / win, 'same')
    g = 1 - depth * np.clip(env / (np.percentile(env, 95) * 0.4 + 1e-9), 0, 1)
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
    content = np.frombuffer(r.stdout, '<f4').reshape(-1, 2).astype(np.float64)[:N]   # пики срезает лимитер
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
