"""Звук «Шаурма + суперклей»: голос + мерзкие/мультяшные звуки кодом (synth.py) + SFX Botanica (sfxkit). Без рекламы.
Пишет build/mix.wav и build/review/{sfx_only,mix,voice_only}.mp3 + sfx_cues.txt."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import subprocess
import wave
import numpy as np
import banner
import sound
import sfxkit
from synth import (SR, place, fart, sad_trombone_fart, plop, squelch, retch, hiss, splat, gurgle, tractor, glass,
                   pop_snap, rip, squeeze_tube, balloon_fart, disco, coo, sniff)
from timeline import DUR, ON, END, S, E, TAKES, KEYS
from events import AD_STOPS

BR = banner.Breaks(AD_STOPS, cy=960)
N = int(round(DUR * SR))


def D(k):
    return E[k] - S[k]


def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    wipes = {'A04', 'A05', 'A07', 'A13', 'A15', 'A16'}
    for k in KEYS[1:]:
        t = S[k] - 0.12
        if k in wipes:
            A(fx, 'whoosh-organic', t, align='peak', gain_db=-14, label='переход-облако газа')
        else:
            A(fx, 'whoosh-short', t, align='peak', gain_db=-18, label='смена сцены')
    # фон вокзала: гул зала
    A(fx, 'ambience', 0.0, gain_db=-28, dur=(8, 200), label='вокзал')
    # 1. хук
    A(fx, 'pop', S['A01'] + 1.0, gain_db=-14, label='+')
    A(fx, 'select', S['A01'] + 1.6, gain_db=-15, label='= ?')
    A(fx, 'error', S['A01'] + D('A01') * 0.62, gain_db=-12, label='НЕ ПОВТОРЯТЬ')
    # 2. продавец, мухи
    for f in (0.22, 0.45):
        A(fx, 'select-soft', S['A02'] + D('A02') * f, gain_db=-14, label='бирка')
    A(fx, 'cartoon', S['A02'] + D('A02') * 0.7, gain_db=-15, file='comic-expressions', label='продавец пожимает плечами')
    # 3. голуби
    for k in range(3):
        place(fx, coo(9 + k), S['A03'] + 0.4 + k * 1.1, -16)
    A(fx, 'cartoon-move', S['A03'] + D('A03') * 0.62, gain_db=-15, label='голубь с окурком')
    # 4. ест, клеит, таймер 10 с
    eat = D('A04') * 0.35
    for k in range(4):
        A(fx, 'cartoon', S['A04'] + k * eat / 4 + 0.1, gain_db=-12, file='cartoon-eat', label='кусь')
    place(fx, squeeze_tube(), S['A04'] + eat + 0.3, -12)
    A(fx, 'glitch-text', S['A04'] + eat + 0.05, gain_db=-17, label='цензура')
    A(fx, 'counter', S['A04'] + eat + 0.6, gain_db=-14, label='таймер 10 с')
    A(fx, 'impact', S['A04'] + eat + 2.6, align='peak', gain_db=-11, label='СХВАЧЕНО')
    # 5. вечеринка бактерий
    place(fx, disco(D('A05') + 0.3), S['A05'] - 0.1, -17)
    A(fx, 'sparkle', S['A05'] + 0.4, gain_db=-16, label='диско-шар')
    for k in range(5):
        place(fx, gurgle(0.6, k), S['A05'] + D('A05') * 0.55 + k * 0.5, -17)
    A(fx, 'impact', S['A05'] + D('A05') * 0.55, align='peak', gain_db=-12, label='+ГАЗ')
    # 6. выход закрыт
    A(fx, 'stretch', S['A06'] + D('A06') * 0.35, gain_db=-14, label='скотч-клей крест-накрест')
    A(fx, 'error', S['A06'] + D('A06') * 0.6, gain_db=-12, label='выход закрыт')
    A(fx, 'sub-drop', S['A06'] + D('A06') * 0.78, gain_db=-11, label='НАГЛУХО')
    # 7. живот надувается, урчит трактором
    A(fx, 'stretch', S['A07'] + 0.1, gain_db=-12, label='надувается')
    A(fx, 'riser', S['A07'] + D('A07') * 0.6, align='end', gain_db=-17, label='надувание')
    place(fx, tractor(D('A07') * 0.55 + 0.4), S['A07'] + D('A07') * 0.45, -12)
    place(fx, gurgle(1.5, 7), S['A07'] + D('A07') * 0.45, -12)
    # 8. пуговица в телевизор
    pt = S['A08'] + D('A08') * 0.25
    place(fx, pop_snap(), pt, -8)
    A(fx, 'whoosh-short', pt + 0.15, align='peak', gain_db=-12, label='пуговица летит')
    place(fx, glass(), pt + 0.35, -9)
    A(fx, 'impact', pt + 0.35, align='peak', gain_db=-13, label='ДЗЫНЬ')
    A(fx, 'cartoon', S['A08'] + D('A08') * 0.78, gain_db=-14, file='horn', label='ОПЯТЬ')
    # 9. друзья
    A(fx, 'popup', S['A09'] + 0.2, gain_db=-13, label='вопрос друзей')
    A(fx, 'popup', S['A09'] + D('A09') * 0.45, gain_db=-13, label='Шаурма.')
    place(fx, gurgle(1.0, 9), S['A09'] + D('A09') * 0.5, -13)
    A(fx, 'cartoon', S['A09'] + D('A09') * 0.72, gain_db=-17, file='crickets', label='понимающе кивают')
    # 10. не взлетит
    for k in range(3):
        A(fx, 'boing', S['A10'] + 0.2 + k * 1.31, gain_db=-13, label='подпрыгивает')
    A(fx, 'error', S['A10'] + D('A10') * 0.5, gain_db=-12, label='НЕ ВЗЛЕТИТ')
    place(fx, gurgle(1.4, 11), S['A10'] + D('A10') * 0.72, -11)
    A(fx, 'voice', S['A10'] + D('A10') * 0.6, gain_db=-14, file='upset', label='грустный')
    # 11. огнеопасно, торт без тебя
    A(fx, 'scan', S['A11'] + 0.3, gain_db=-15, label='знак огнеопасно')
    A(fx, 'select', S['A11'] + 0.8, gain_db=-14, label='H2')
    A(fx, 'select', S['A11'] + 1.1, gain_db=-14, label='CH4')
    A(fx, 'confirm', S['A11'] + D('A11') * 0.45, gain_db=-14, label='С днём рождения')
    A(fx, 'impact', S['A11'] + D('A11') * 0.45 + 0.4, align='peak', gain_db=-12, label='БЕЗ ТЕБЯ')
    # 12. эпиляция
    for k in range(3):
        place(fx, fart(0.18, 260, 0.1, seed=20 + k, squeak=True), S['A12'] + 0.4 + k * 0.6, -18)   # натуга
    place(fx, rip(), S['A12'] + D('A12') * 0.4, -7)
    A(fx, 'voice', S['A12'] + D('A12') * 0.4 + 0.1, gain_db=-10, file='scared.flac', label='АЙ!!!')
    A(fx, 'confirm', S['A12'] + D('A12') * 0.4 + 0.4, gain_db=-15, label='эпиляция: бесплатно')
    # 13. хирург, ацетон, все разбегаются
    A(fx, 'cartoon', S['A13'] + 0.3, gain_db=-16, file='crickets', label='долгий взгляд')
    A(fx, 'cartoon', S['A13'] + D('A13') * 0.3, gain_db=-14, file='eye-whistle', label='ацетон')
    A(fx, 'popup', S['A13'] + D('A13') * 0.7, gain_db=-12, label='ВСЕМ НА 10 М')
    A(fx, 'cartoon-move', S['A13'] + D('A13') * 0.72, gain_db=-13, label='персонал убегает')
    # 14. выход газа: шарик носится по палате
    go = S['A14'] + D('A14') * 0.35
    for k in range(3):
        A(fx, 'click', S['A14'] + 0.3 + k * 0.5, gain_db=-12, label='3-2-1')
    place(fx, balloon_fart(D('A14') * 0.65 + 0.6), go, -6)
    A(fx, 'whoosh', go + 0.2, align='peak', gain_db=-14, label='носится по палате')
    A(fx, 'cartoon', go + 0.4, gain_db=-15, file='ricochet', label='рикошет')
    # 15. проветривание, увольнение
    A(fx, 'paper', S['A15'] + D('A15') * 0.35, gain_db=-12, label='заявление хирурга')
    A(fx, 'paper', S['A15'] + D('A15') * 0.75, gain_db=-12, label='заявление медсестры')
    place(fx, retch(30, 150, long=False), S['A15'] + 0.6, -13)
    # 16. финал
    A(fx, 'impact', S['A16'] + D('A16') * 0.4, align='peak', gain_db=-12, label='ВКУСНАЯ')
    A(fx, 'sparkle', S['A16'] + D('A16') * 0.7, gain_db=-14, label='ЗАВТРА ЕЩЁ')
    place(fx, gurgle(1.0, 16), E['A16'] + 0.3, -12)                     # живот уже урчит
    # --- пуки, рвота, шмяки (кодом) ---
    place(fx, fart(0.3, 220, 0.1, seed=1, squeak=True), S['A01'] + 3.0, -17)          # от одного вида шаурмы
    place(fx, retch(1, 130, long=False), S['A02'] + D('A02') * 0.25, -15)             # «вчерашнее»
    place(fx, fart(0.5, 120, 0.3, seed=2), S['A03'] + D('A03') * 0.85, -16)           # «А они едят окурки»
    place(fx, squelch(3), S['A04'] + eat + 0.4, -14)                                 # клей — шмяк
    for k in range(4):
        place(fx, fart(0.15, 300 + 40 * k, 0.05, seed=10 + k, squeak=True), S['A06'] + 0.3 + k * 0.35, -19)  # газ стучится
    place(fx, fart(0.4, 90, 0.5, seed=12, fall=0.1), S['A06'] + D('A06') * 0.6, -14)   # и упирается в клей
    place(fx, retch(4, 120, long=False), S['A09'] + D('A09') * 0.3, -15)              # подруга давится
    place(fx, sad_trombone_fart(), S['A10'] + D('A10') * 0.55, -12)                    # «НЕ ВЗЛЕТИТ»
    place(fx, retch(5, 110), S['A14'] + D('A14') * 0.75, -12)                          # кого-то в палате тошнит
    place(fx, retch(6, 135), S['A15'] + D('A15') * 0.2, -15)
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
