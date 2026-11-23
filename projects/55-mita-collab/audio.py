"""Голос Миты + «Raving Energy» (Kevin MacLeod, тихо) + SFX Botanica (sfxkit). Рекламы-баннера нет.
build/mix.wav и build/review/{voice_only,sfx_only,mix}.mp3 + sfx_cues.txt."""
import subprocess
import sys
import wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import sound
import sfxkit
import music
import events as E
from timeline import DUR, ON, TAKES

SR = 48000


def voice_track(n):
    v = np.zeros((n, 2))
    for k, take in TAKES.items():
        d = sound.load_stereo(take, SR)
        s = round(ON[k] * SR)
        c = min(len(d), n - s)
        v[s:s + c] += d[:c] * 0.9
    return v


def envelope(v):
    e = np.convolve(np.abs(v).max(1), np.ones(4800) / 4800, 'same')
    return np.clip(e / (np.percentile(e[e > 1e-4], 60) + 1e-9), 0, 1)


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    a = kit.add
    a(fx, 'pop', 0.08, gain_db=-20, label='первый кадр')
    a(fx, 'sparkle', E.HOOK_Q + 0.1, gain_db=-20, label='брелок на мониторе')
    # переход 1 «загрузка матча»
    t, d = E.T1
    a(fx, 'scan', t, gain_db=-16, label='T1: скан-луч')
    a(fx, 'power-up', t + d * 0.5, gain_db=-19, label='T1: арена включается')
    a(fx, 'impact', t + d, gain_db=-20, label='T1: ROUND 1')
    a(fx, 'popup', E.SO2, gain_db=-19, label='автомат с брелоком на экране')
    for i, tt in enumerate((E.CHARM, E.GRAF, E.SKIN, E.AGENT)):
        a(fx, 'whoosh-short', tt, align='peak', gain_db=-21, label=f'экран арены {i + 1}')
    a(fx, 'riser-hit', E.TOURN + 0.2, align='end', gain_db=-19, label='кубок турнира')
    a(fx, 'sparkle', E.NFT3, gain_db=-19, label='уникальные NFT')
    a(fx, 'popup', E.PROMO, gain_db=-19, label='окно промокода')
    a(fx, 'typing', E.TYPE0, gain_db=-17, label='вводит код')
    a(fx, 'confirm', E.APPLY, gain_db=-17, label='ПРИМЕНИТЬ')
    a(fx, 'coin', E.GOLD, gain_db=-16, label='голда')
    a(fx, 'pop', E.CASE, gain_db=-17, label='кейс')
    a(fx, 'pop', E.STICK, gain_db=-18, label='стикер')
    # переход 2 «распаковка»
    t, d = E.T2
    a(fx, 'whoosh-deep', t, gain_db=-17, label='T2: коробка падает')
    a(fx, 'cartoon-hit', t + 0.3, gain_db=-17, label='T2: коробка приземлилась')
    a(fx, 'paper', t + 0.5, gain_db=-17, label='T2: бант развязывается')
    a(fx, 'sparkle-whoosh', t + 0.65, gain_db=-17, label='T2: коробка раскрылась')
    a(fx, 'sparkle', E.HOLD + 0.1, gain_db=-21, label='NFT в ладонях')
    for tt, lab in ((E.PLUSH, 'плюшевая игрушка'), (E.HOODIE, 'худи'), (E.FIGURE, 'фигурка')):
        a(fx, 'pop', tt, gain_db=-17, label=lab)
    a(fx, 'popup', E.QR, gain_db=-19, label='бирки с QR')
    a(fx, 'scan', E.SCAN, gain_db=-17, label='сканирует QR')
    a(fx, 'confirm', E.SCAN + 0.7, gain_db=-18, label='бип')
    a(fx, 'sparkle-whoosh', E.RARE, gain_db=-17, label='редкая модель прилетела')
    # жуть
    a(fx, 'power-down', E.CREEPY, gain_db=-14, label='ЖУТЬ: свет гаснет, музыка обрывается')
    a(fx, 'sub-drop', E.CREEPY + 0.1, gain_db=-15, label='жуть: низкий гул')
    a(fx, 'glitch-texture', E.CREEPY + 2.4, gain_db=-21, label='глаза загораются')
    # переход 3 «затвор камеры»
    t, d = E.T3
    a(fx, 'glitch', t - 0.05, gain_db=-17, label='жуть кончилась')
    a(fx, 'shutter', t + d * 0.45, gain_db=-14, label='T3: затвор камеры')
    a(fx, 'click', E.IDEA3 + 0.3, gain_db=-18, label='кольцевая лампа включилась')
    a(fx, 'counter', E.VIEWS, gain_db=-19, label='счётчик просмотров')
    a(fx, 'riser-hit', E.AWARD + 0.25, align='end', gain_db=-18, label='награда падает')
    a(fx, 'popup', E.TGCARD, gain_db=-18, label='окно подарка Telegram')
    a(fx, 'select', E.LIMIT + 0.1, gain_db=-18, label='274 / 1 000')
    a(fx, 'list', E.GRID, gain_db=-19, label='ролики множатся')
    a(fx, 'counter', E.MILLION - 0.4, gain_db=-19, label='миллионы зрителей')
    a(fx, 'sparkle', E.WINK + 1.0, gain_db=-20, label='подмигивает')
    # переход 4 «свайп ленты»
    t, d = E.T4
    a(fx, 'whoosh', t + d * 0.4, align='peak', gain_db=-16, label='T4: свайп ленты')
    for i, tt in enumerate(E.SUM):
        a(fx, 'popup', tt, gain_db=-18, label=f'итог: идея {i + 1}')
    a(fx, 'transform', E.MERGE, gain_db=-17, label='три идеи сливаются в подарок')
    for i, tt in enumerate(E.CARDS):
        a(fx, 'select-soft', tt, gain_db=-17, label=f'карточка {i + 1}')
    a(fx, 'confirm', E.WRITE, gain_db=-18, label='пиши номер')
    return fx * 10 ** (-1 / 20)


def creepy_cut(m):
    """Музыка гаснет на жути и возвращается на переходе в студию."""
    n = len(m)
    t = np.arange(n) / SR
    k = np.clip((t - E.CREEPY) / 0.25, 0, 1) * (1 - np.clip((t - (E.T3[0] + E.T3[1] * 0.5)) / 0.3, 0, 1))
    return m * (1 - k)[:, None]


def save_wav(path, x):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    n = int(round(DUR * SR))
    kit = sfxkit.Kit(HERE)
    v = voice_track(n)
    env = envelope(v)
    m = creepy_cut(music.music(n, env))
    fx = sfx_layer(n, kit)
    fx *= (1 - 0.45 * env)[:, None]
    data = v + m + fx
    build = paths.build(HERE)
    save_wav(build / 'mix.wav', data)
    kit.save()
    rev = sfxkit.write_review(HERE, fx, data, None, SR, kit.cues)
    save_wav(build / 'voice_music.wav', v + m)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(build / 'voice_music.wav'), '-b:a', '192k',
                    str(rev / 'voice_music.mp3')], check=True)
    print('content', round(DUR, 2), 's')
