"""Голос Миты + «Okay, Everyone! (Yuri)» + SFX (Botanica V4 через sfxkit) + полный звук RubUp.
build/mix.wav и build/review/{voice_only,sfx_only,mix}.mp3 + sfx_cues.txt."""
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
from timeline import DUR, ON, TAKES, AD_STOP

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)
SPIN_DUR = 1.05


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
    a(fx, 'pop', 0.1, gain_db=-16, label='хук: кекс 1')
    a(fx, 'pop', 0.35, gain_db=-16, label='хук: кекс 2')
    a(fx, 'counter', E.HOOK_PRICE, gain_db=-18, label='цена чёрного растёт')
    a(fx, 'coin', E.HOOK_PRICE + 0.6, gain_db=-15, label='×5,6')
    a(fx, 'whoosh*', E.SPIN + SPIN_DUR * 0.3, align='peak', gain_db=-13, label='кружение')
    a(fx, 'sparkle', E.SPIN + SPIN_DUR * 0.62, gain_db=-13, label='смена наряда → готика')
    for j in range(3):
        a(fx, 'popup', E.X7 + 0.3 + 0.35 * j, gain_db=-18, label=f'×7: пара {j + 1}')
    a(fx, 'confirm', E.X7_BADGE, gain_db=-17, label='«в семь раз»')
    a(fx, 'whoosh-short', E.PLAYER + 0.1, align='peak', gain_db=-18, label='кекс vs проигрыватель')
    a(fx, 'select', E.PLAYER_HIT, gain_db=-16, label='«>»')
    a(fx, 'whoosh-short', E.LOCKET + 0.1, align='peak', gain_db=-18, label='медальон')
    a(fx, 'impact', E.LOCKET_HIT + 0.9, gain_db=-14, label='17,5 млн ₽')
    for j in range(3):
        a(fx, 'popup', E.RARITY + 0.3 + 0.3 * j, gain_db=-18, label=f'фон {j + 1} (1,5%)')
    a(fx, 'select-soft', E.RARITY_SAME, gain_db=-16, label='«так же часто»')
    a(fx, 'whoosh-short', AD_STOP, align='peak', gain_db=-19, label='торможение на RubUp')
    a(fx, 'confirm', AD_STOP + 0.05, gain_db=-15, label='ответ мини-игры')
    for j, ti in enumerate(E.ICONS):
        a(fx, 'pop', ti, gain_db=-16, label=f'иконка {j + 1}')
    a(fx, 'sparkle-whoosh', E.GLOW + 0.1, gain_db=-16, label='подарок светится')
    a(fx, 'power-down', E.PLAIN + 1.0, gain_db=-19, label='обычный фон тускнеет')
    a(fx, 'riser', E.PRICE_UP + 0.4, align='end', gain_db=-21, label='цена растёт')
    a(fx, 'popup', E.OUTRO + 0.1, gain_db=-17, label='люкс')
    a(fx, 'popup', E.OUTRO_MIN, gain_db=-17, label='минимум')
    a(fx, 'select-soft', E.OUTRO_PILL, gain_db=-16, label='пиши в комментариях')
    return fx * 10 ** (-1 / 20)


def save_wav(path, x):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -0.98, 0.98) * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    n = int(round(DUR * SR))
    kit = sfxkit.Kit(HERE)
    v = voice_track(n)
    env = envelope(v)
    m = music.music(n, env, slow_from=None)
    fx = sfx_layer(n, kit)
    fx *= (1 - 0.45 * env)[:, None]
    data = BR.audio(v + m + fx, SR)
    build = paths.build(HERE)
    save_wav(build / 'mix.wav', data)
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    save_wav(build / 'voice_only.wav', BR.audio(v, SR, banner=False))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(build / 'voice_only.wav'), '-b:a', '192k', str(rev / 'voice_only.mp3')], check=True)
    print('content', round(DUR, 2), 's; out', round(BR.out_dur(DUR), 2), 's')
