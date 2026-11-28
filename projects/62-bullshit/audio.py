"""Звук «Нести х*йню»: голос + мерзкие/мультяшные звуки кодом (synth.py) + SFX Botanica (sfxkit). Без рекламы.
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
from synth import (SR, place, fart, sad_trombone_fart, squelch, retch, rip, babble, steps, waves, gull, applause,
                   jingle, crackle, alarm, glass)
from timeline import DUR, ON, END, S, E, TAKES, KEYS
from events import AD_STOPS

BR = banner.Breaks(AD_STOPS, cy=960)
N = int(round(DUR * SR))



def sfx(kit):
    fx = np.zeros((N, 2))
    A = kit.add
    wipes = {'B04', 'B07', 'B10', 'B13', 'B15'}
    for k in KEYS[1:]:
        t = S[k] - 0.12
        if k in wipes:
            place(fx, babble(0.6, 50 + int(k[1:]), 210), t - 0.3, -16)
            A(fx, 'whoosh-organic', t, align='peak', gain_db=-15, label='переход-пузыри')
        else:
            A(fx, 'whoosh-short', t, align='peak', gain_db=-18, label='смена сцены')
    # 1. хук: герой бормочет чепуху
    place(fx, babble(D('B01') + 0.2, 1, 180), S['B01'], -22)
    A(fx, 'impact', S['B01'] + 0.3, align='peak', gain_db=-14, label='НЕСТИ Х*ЙНЮ')
    # 2. счётчик слов и х*йнеметр
    A(fx, 'counter', S['B02'] + 0.1, gain_db=-14, label='16 000 слов')
    A(fx, 'riser', S['B02'] + D('B02') * 0.55 + 1.2, align='end', gain_db=-15, label='стрелка в красное')
    A(fx, 'error', S['B02'] + D('B02') * 0.55 + 1.2, gain_db=-13, label='100%')
    place(fx, babble(D('B02'), 2, 220), S['B02'], -26)
    # 3. книги
    for k in range(10):
        A(fx, 'cartoon-hit', S['B03'] + 0.6 + k * (D('B03') * 0.5 / 10), gain_db=-18, label='книга')
    A(fx, 'cartoon', S['B03'] + D('B03') * 0.72, gain_db=-17, file='crickets', label='0 читателей')
    A(fx, 'impact', S['B03'] + D('B03') * 0.72, align='peak', gain_db=-13, label='штамп')
    # 4. чат, «ага», беззвучка
    for t0 in (0.2, 0.6, 1.0, 2.4, 2.7):
        A(fx, 'key-enter', S['B04'] + t0, gain_db=-14, label='сообщение')
    A(fx, 'popup', S['B04'] + 1.8, gain_db=-11, label='ага')
    A(fx, 'click', S['B04'] + D('B04') * 0.75, gain_db=-9, label='беззвучка')
    A(fx, 'power-down', S['B04'] + D('B04') * 0.75 + 0.1, gain_db=-15, label='звук выключен')
    # 5. мама
    place(fx, babble(D('B05') * 0.5, 5, 190), S['B05'], -22)
    A(fx, 'voice', S['B05'] + D('B05') * 0.45, gain_db=-10, file='tired', label='вздох мамы')
    A(fx, 'paper', S['B05'] + D('B05') * 0.72, gain_db=-12, label='запись к врачу')
    A(fx, 'confirm', S['B05'] + D('B05') * 0.72 + 0.3, gain_db=-15, label='срочно')
    # 6. гонка рта и мозга
    place(fx, steps(D('B06') + 0.3, 8, 6), S['B06'] - 0.1, -15)
    place(fx, babble(D('B06'), 6, 260), S['B06'], -22)
    A(fx, 'cartoon', S['B06'] + 0.3, gain_db=-17, file='tiptoe', label='мозг семенит')
    # 7. батарейка, отпуск
    A(fx, 'power-up', S['B07'] + 0.1, gain_db=-15, label='20%')
    split = D('B07') * 0.4
    place(fx, waves(D('B07') - split + 0.6), S['B07'] + split - 0.1, -16)
    for k in range(2):
        place(fx, gull(7 + k), S['B07'] + split + 0.5 + k * 1.3, -17)
    place(fx, rip(9), S['B07'] + split + 0.2, -18)          # молния чемодана
    A(fx, 'sparkle', S['B07'] + split + 0.6, gain_db=-16, label='МОЗГ В ОТПУСКЕ')
    # 8. собеседование
    A(fx, 'popup', S['B08'] + 0.2, gain_db=-13, label='Я умею летать')
    A(fx, 'impact', S['B08'] + D('B08') * 0.45, align='peak', gain_db=-10, label='ПРИНЯТ')
    A(fx, 'cartoon', S['B08'] + D('B08') * 0.72, gain_db=-14, file='horn', label='отдел маркетинга')
    A(fx, 'cartoon', E['B08'] + 0.05, gain_db=-19, file='crickets', label='тишина')
    # 9. эксперт во всём
    for f in (0.0, 0.35, 0.65):
        A(fx, 'select', S['B09'] + D('B09') * f + 0.05, gain_db=-12, label='новый слайд')
    A(fx, 'coin', S['B09'] + 0.3, gain_db=-14, label='крипта')
    A(fx, 'glitch', S['B09'] + D('B09') * 0.35 + 0.2, gain_db=-15, label='коллайдер')
    A(fx, 'voice', S['B09'] + D('B09') * 0.65 + 0.2, gain_db=-17, file='cute', label='котики')
    place(fx, applause(2.2, 9), E['B09'] - 1.6, -15)
    # 10. миллион подписчиков, сеть
    A(fx, 'counter', S['B10'] + 0.1, gain_db=-13, label='1 000 000')
    A(fx, 'scan', S['B10'] + D('B10') * 0.55, gain_db=-15, label='сеть загорается')
    place(fx, applause(1.6, 10), S['B10'] + D('B10') * 0.3, -18)
    # 11–12. учёные
    A(fx, 'impact', S['B11'] + D('B11') * 0.25, align='peak', gain_db=-13, label='ЗАКОН БРАНДОЛИНИ')
    A(fx, 'select-soft', S['B11'] + D('B11') * 0.5, gain_db=-14, label='сказать 1')
    A(fx, 'riser', S['B11'] + D('B11') * 0.5 + 1.9, align='end', gain_db=-15, label='опровергнуть ×10')
    A(fx, 'typing', S['B12'] + 0.2, gain_db=-16, label='пишет статью')
    A(fx, 'list', S['B12'] + 0.1, gain_db=-14, label='видео штампуются')
    # 13. гороскоп
    place(fx, jingle(), S['B13'] - 0.05, -10)
    A(fx, 'sparkle', S['B13'] + D('B13') * 0.45, gain_db=-14, label='ГОРОСКОП')
    place(fx, applause(1.5, 13), E['B13'] - 0.6, -18)
    # 14. суп горит
    place(fx, crackle(D('B14') + 0.3), S['B14'] - 0.05, -14)
    place(fx, alarm(1.6), S['B14'] + 0.6, -20)
    for t0 in (0.0, 0.3, 0.6):
        A(fx, 'popup', S['B14'] + D('B14') * 0.45 + t0, gain_db=-13, label='ответ друга')
    place(fx, sad_trombone_fart(), S['B14'] + D('B14') * 0.8, -11)
    A(fx, 'impact', S['B14'] + D('B14') * 0.8, align='peak', gain_db=-14, label='R.I.P. СУП')
    # 15. финал: четвёртая стена и петля
    A(fx, 'sub-drop', S['B15'] + D('B15') * 0.35, gain_db=-13, label='это видео — тоже?')
    A(fx, 'spinback', S['B15'] + D('B15') * 0.65, gain_db=-12, label='посмотри ещё раз')
    # мерзкие акценты
    place(fx, fart(0.3, 230, 0.1, seed=31, squeak=True), S['B03'] + D('B03') * 0.9, -18)     # «никто не будет»
    place(fx, retch(32, 140, long=False), S['B05'] + D('B05') * 0.3, -18)                   # мама еле держится
    place(fx, fart(0.5, 110, 0.3, seed=33), S['B13'] + D('B13') * 0.9, -19)                 # в эфире
    return fx


def D(k):
    return E[k] - S[k]


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
