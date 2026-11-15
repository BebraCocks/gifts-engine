"""Голос Миты + музыка «Your Reality» (piano) + SFX (Botanica V4 через sfxkit) + полный звук RubUp.
build/mix.wav и для автора build/review/{voice_only,sfx_only,mix}.mp3 + sfx_cues.txt."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
import banner
import sound
import sfxkit
import music
import events as E
from timeline import DUR, ON, END, TAKES, AD_STOP

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)
SFX_GAIN_DB = -1.0


def voice_track(n):
    v = np.zeros((n, 2))
    for k, take in TAKES.items():
        d = sound.load_stereo(take, SR)
        s = round(ON[k] * SR)
        c = min(len(d), n - s)
        v[s:s + c] += d[:c] * 0.9
    return v


def envelope(v):
    e = np.abs(v).max(1)
    e = np.convolve(e, np.ones(4800) / 4800, 'same')
    return np.clip(e / (np.percentile(e[e > 1e-4], 60) + 1e-9), 0, 1)


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    a = kit.add
    a(fx, 'whoosh-short', 0.05, gain_db=-17, label='хук: подарки въезжают')
    a(fx, 'pop', E.HOOK_POPS[0] - 0.05, gain_db=-16, label='хук: левый подарок')
    a(fx, 'pop', E.HOOK_POPS[1] - 0.05, gain_db=-16, label='хук: правый подарок')
    a(fx, 'counter', E.PRICE_X10 - 0.55, gain_db=-18, label='цена правого растёт')
    a(fx, 'coin', E.PRICE_X10, gain_db=-14, label='×10')
    a(fx, 'select-soft', E.INTRO, gain_db=-17, label='подпись «монохром»')
    for j, dt in enumerate((0.0, 0.29, 0.58)):
        a(fx, 'click', E.COUNTER + dt, gain_db=-17, label=f'счётчик {j + 1}')
    a(fx, 'whoosh*', E.SPIN, align='peak', gain_db=-13, label='Мита кружится')
    a(fx, 'sparkle', E.TYPE1, gain_db=-14, label='наряд → розовый')
    for j, tp in enumerate(E.CARD_POPS['type1']):
        a(fx, 'popup', tp - 0.05, gain_db=-18, label=f'вид 1: карточка {j + 1} (на долю)')
    a(fx, 'whoosh-short', E.TYPE1_ZOOM, align='peak', gain_db=-18, label='зум на карточку')
    a(fx, 'sparkle-whoosh', E.TYPE2, gain_db=-15, label='наряд → пёстрый')
    for j, tp in enumerate(E.CARD_POPS['type2']):
        a(fx, 'popup', tp - 0.05, gain_db=-18, label=f'вид 2: карточка {j + 1} (на долю)')
    a(fx, 'select', E.TYPE2_NAMES, gain_db=-16, label='совпадающие названия подсвечены')
    a(fx, 'error', E.TYPE2_COLOR, gain_db=-19, label='«по цвету — не всегда»')
    a(fx, 'riser', AD_STOP, align='end', gain_db=-19, label='тизер перед рекламой')
    a(fx, 'whoosh-deep', AD_STOP, align='peak', gain_db=-16, label='торможение на RubUp')
    a(fx, 'impact', E.TYPE3, gain_db=-15, label='вспышка: чёрно-белый')
    a(fx, 'sparkle', E.TYPE3 + 0.05, gain_db=-16, label='наряд → чёрно-белый')
    for j, tp in enumerate(E.CARD_POPS['type3']):
        a(fx, 'popup', tp - 0.05, gain_db=-18, label=f'вид 3: карточка {j + 1} (на долю)')
    a(fx, 'whoosh-short', E.TYPE3_ZOOM, align='peak', gain_db=-18, label='зум на самую дорогую')
    a(fx, 'transform', E.ORDER, gain_db=-16, label='хаос → порядок')
    a(fx, 'confirm', E.SEEN + 0.6, gain_db=-17, label='монохром видно сразу')
    for j, tp in enumerate(E.CARD_POPS['tease']):
        a(fx, 'click', tp - 0.05, gain_db=-19, label=f'тизер: «?» {j + 1}')
    for j, tp in enumerate(E.CARD_POPS['outro']):
        a(fx, 'select-soft', tp - 0.05, gain_db=-18, label=f'финал: вид {j + 1}')
    a(fx, 'downlifter', E.CREEPY, gain_db=-18, label='жутковатый финал')
    return fx * 10 ** (SFX_GAIN_DB / 20)


def save_wav(path, x):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -0.98, 0.98) * 32767).astype('<i2').tobytes())


def mp3(src, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-b:a', '192k', str(dst)], check=True)


if __name__ == '__main__':
    n = int(round(DUR * SR))
    kit = sfxkit.Kit(HERE)
    v = voice_track(n)
    env = envelope(v)
    m = music.music(n, env, slow_from=E.CREEPY)
    fx = sfx_layer(n, kit)
    fx *= (1 - 0.45 * env)[:, None]
    content = v + m + fx
    data = BR.audio(content, SR)
    build = paths.build(HERE)
    save_wav(build / 'mix.wav', data)
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    vo = BR.audio(v, SR, banner=False)
    save_wav(build / 'voice_only.wav', vo)
    mp3(build / 'voice_only.wav', rev / 'voice_only.mp3')
    mo = BR.audio(v + m, SR, banner=False)
    save_wav(build / 'voice_music.wav', mo)
    mp3(build / 'voice_music.wav', rev / 'voice_music.mp3')
    print('content', round(DUR, 2), 's; out', round(BR.out_dur(DUR), 2), 's; review:', rev)
