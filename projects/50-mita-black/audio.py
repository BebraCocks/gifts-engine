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
    a(fx, 'whoosh*', E.SPIN + SPIN_DUR * 0.3, align='peak', gain_db=-13, label='кружение')
    a(fx, 'sparkle', E.SPIN + 0.45, gain_db=-13, label='вспышка: смена наряда → готика')
    for j, tj in enumerate((E.X7 + 0.1, 8.25, E.CARD_GRAB)):
        a(fx, 'popup', tj, gain_db=-18, label=f'пара в нишах {j + 1}')
    a(fx, 'coin', E.CARD_SHOW, gain_db=-17, label='цена кекса на чёрном')
    a(fx, 'cartoon-move', E.PUMPKIN - 0.15, gain_db=-19, label='тыква: Мита рисует руками круг')
    a(fx, 'select-soft', E.PUMP_CHEAP, gain_db=-17, label='обычная ≈ 1 300 ₽')
    a(fx, 'flip', E.PUMP_BLACK - 0.2, gain_db=-16, label='плитка переворачивается')
    a(fx, 'coin', E.PUMP_BLACK + 0.1, gain_db=-15, label='на чёрном ≈ 43 700 ₽')
    a(fx, 'whoosh-short', E.LOCKET + 0.1, align='peak', gain_db=-18, label='медальон')
    a(fx, 'boing', E.LOCKET_HIT, gain_db=-17, label='прыжок от шока')
    a(fx, 'impact', E.LOCKET_HIT + 0.52, gain_db=-15, label='приземление, 17 млн')
    a(fx, 'glitch', E.CREEPY, gain_db=-14, label='ЖУТЬ: глитч, музыка обрывается')
    a(fx, 'sub-drop', E.CREEPY + 0.05, gain_db=-15, label='жуть: низкий гул')
    a(fx, 'glitch-text', E.CREEPY + 1.3, gain_db=-19, label='глаза отражения светятся')
    a(fx, 'glitch', E.CREEPY_END - 0.04, gain_db=-15, label='щелчок — снова мило')
    for j, g in enumerate(E.GACHA):
        a(fx, 'select', g - 0.05, gain_db=-17, label=f'ниша: фон {j + 1}')
    a(fx, 'whoosh-short', AD_STOP, align='peak', gain_db=-19, label='торможение на RubUp')
    for j, ti in enumerate(E.ICONS):
        a(fx, 'pop', ti, gain_db=-16, label=f'предмет {j + 1}')
    a(fx, 'sparkle-whoosh', E.GLOW_SHOW, gain_db=-17, label='подарок светится на экране')
    a(fx, 'whoosh-short', E.KICK - 0.1, align='peak', gain_db=-20, label='«хмф» — отворачивается, ниша гаснет')
    a(fx, 'sparkle', E.PRICE - 0.1, gain_db=-18, label='вспышка: Мита на графике')
    a(fx, 'sparkle', E.OUTRO - 0.1, gain_db=-19, label='вспышка: финал')
    a(fx, 'riser', E.PRICE_UP + 0.4, align='end', gain_db=-21, label='цена растёт (Мита на графике)')
    a(fx, 'sparkle', E.OUTRO_LUX, gain_db=-16, label='люкс')
    a(fx, 'pop', E.OUTRO_MIN, gain_db=-18, label='минимум')
    a(fx, 'select-soft', E.OUTRO_PILL, gain_db=-16, label='пиши в комментариях')
    return fx * 10 ** (-1 / 20)


def creepy_cut(m):
    """Музыка обрывается на жути и возвращается после «щелчка»."""
    t = np.arange(len(m)) / SR
    g = np.ones(len(m))
    g -= np.clip((t - E.CREEPY + 0.05) / 0.08, 0, 1)
    g += np.clip((t - E.CREEPY_END) / 0.25, 0, 1)
    return m * np.clip(g, 0, 1)[:, None]


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
    m = creepy_cut(music.music(n, env, slow_from=None))
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
