"""Звук пробного фрагмента «Низшего»: голоса (клипы voice/clips), музыка кодом (music.py), SFX Botanica (sfxkit),
сердцебиение синтезировано (в паке нет удара сердца). Без рекламы.
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
from timeline import DUR, ON, TAKES, S, E, SC2, SC3, STAMP
from events import AD_STOPS, OK, BEATS, MEMORY_DRAIN, NAME_GLITCH, FACE_GLITCH, HEY

SR = 48000
BR = banner.Breaks(AD_STOPS, cy=960)
N = int(round(DUR * SR))


def place(buf, y, t, db):
    i = int(round(t * SR))
    c = min(len(y), len(buf) - i)
    if c > 0:
        buf[i:i + c] += (y[:c, None] if y.ndim == 1 else y[:c]) * 10 ** (db / 20)


def heartbeat():
    """глухой двойной удар «лаб-даб»: синусы с падением высоты"""
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
    A(fx, 'power-up', 0.05, gain_db=-20, label='система включается')
    for key in ('S1', 'S2', 'S3'):
        A(fx, 'typing', S[key] - 0.02, gain_db=-22, fit=0.5, label=f'печать строки {key}')
        A(fx, 'confirm', OK[key], gain_db=-19, label=f'УСПЕШНО {key}')
    for j in range(4):
        A(fx, 'click', S['S2'] + 0.35 + j * 0.16, gain_db=-17, file='metalic', label='конечность встаёт на место')
    for b in BEATS:
        place(fx, heartbeat(), b - 0.02, -9)
    A(fx, 'whoosh*', SC2, align='peak', gain_db=-17, dur=(0.6, 1.6), label='переход к профилю')
    A(fx, 'power-down', MEMORY_DRAIN, gain_db=-18, label='память 0%')
    A(fx, 'glitch-text', NAME_GLITCH, gain_db=-17, label='ИМЯ: НЕ НАЙДЕНО')
    A(fx, 'glitch-text', FACE_GLITCH, gain_db=-17, label='ЛИЦО: НЕ НАЙДЕНО')
    A(fx, 'whoosh-short', HEY, align='peak', gain_db=-16, label='Йорка врывается')
    A(fx, 'impact', HEY, align='peak', gain_db=-15, label='ЭЙ!')
    A(fx, 'impact', STAMP, align='peak', gain_db=-11, label='штамп 11')
    A(fx, 'scan', STAMP + 0.35, gain_db=-21, label='штрихкод номера')
    return fx


def load_voice():
    voice = np.zeros((N, 2))
    for k, take in enumerate(TAKES):
        data = sound.load_stereo(take, SR)
        i = round(ON[k] * SR)
        c = min(len(data), N - i)
        voice[i:i + c] += data[:c] * 0.9
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
    mus = duck(music(N, SR), voice, 0.55) * 10 ** (-6 / 20)
    fx = duck(sfx(kit), voice, 0.4)
    content = voice + mus + fx
    pk = np.abs(content).max()
    if pk > 0.95:
        k = 0.95 / pk
        content, voice, mus, fx = content * k, voice * k, mus * k, fx * k
    lufs = loudness(content)
    k = 10 ** ((-16.0 - lufs) / 20)                      # громкость под соцсети: −16 LUFS
    if np.abs(content).max() * k > 0.95:
        k = 0.95 / np.abs(content).max()
    content, voice, mus, fx = content * k, voice * k, mus * k, fx * k
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
    print('OK mix', round(len(data) / SR, 2), 's; peak', round(float(pk), 2))
