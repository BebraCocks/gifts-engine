"""Голос Миты + «Ohayou Sayori!» (обрывается на жути) + SFX (Botanica V4 через sfxkit) + звук RubUp. → build/mix.wav"""
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
    for j, t in enumerate((E.G_KULICH, E.G_ICE, E.G_STAR)):
        a(fx, 'sparkle', t + 0.35, gain_db=-19, label=f'подарок {j + 1} нарисован')
    a(fx, 'power-down', E.NO_SKIN + 0.1, gain_db=-21, label='скинов нет — серые')
    a(fx, 'popup', E.MANY + 0.1, gain_db=-19, label='подарки высыпают')
    a(fx, 'whoosh-short', E.SPLASH - 0.15, align='peak', gain_db=-16, label='ведро падает')
    a(fx, 'impact', E.SPLASH, gain_db=-15, label='ведро опрокинулось')
    a(fx, 'cartoon-hit', E.SPLASH + 0.12, gain_db=-16, label='всплеск краски')
    a(fx, 'sparkle', E.OUT_START + 0.6, gain_db=-18, label='художница')
    a(fx, 'paper', E.CARD + 0.1, gain_db=-18, label='карточка')
    a(fx, 'counter', E.CARD + 1.2, gain_db=-21, label='≈ 296 / 850')
    a(fx, 'select', E.FIN_PLANE, gain_db=-19, label='самолётик')
    a(fx, 'select', E.FIN_ICE, gain_db=-19, label='мороженое')
    a(fx, 'error', E.FIN_NONE + 0.1, gain_db=-22, label='почти ничего')
    a(fx, 'paper', E.ERASE1 + 0.1, gain_db=-17, label='ластик стирает')
    a(fx, 'typing', E.ERASE1 + 0.55, gain_db=-20, fit=0.45, label='карандаш дорисовывает')
    a(fx, 'click', E.POKE_HIT - 0.02, gain_db=-14, label='тык кисточкой')
    a(fx, 'boing', E.POKE_HIT + 0.02, gain_db=-16, label='подарок выезжает')
    a(fx, 'foley', E.POKE_HIT + 0.1, gain_db=-17, label='цепи звенят')
    a(fx, 'glitch', E.CREEPY, gain_db=-15, label='ЖУТЬ: музыка обрывается')
    a(fx, 'sub-drop', E.CREEPY + 0.05, gain_db=-16, label='гул')
    a(fx, 'glitch-texture', E.CREEP_C + 0.1, gain_db=-20, label='полунабросок')
    a(fx, 'sparkle-whoosh', E.CREEPY_END - 0.1, gain_db=-15, label='вихрь краски')
    a(fx, 'sparkle', E.HEART + 1.2, gain_db=-18, label='сердечко на стекле')
    a(fx, 'paper', E.NO_NEW, gain_db=-19, label='зачёркнуто')
    a(fx, 'paper', E.YEAR_END + 0.05, gain_db=-19, label='обведено маркером')
    a(fx, 'granular-move', E.WHY + 0.1, gain_db=-21, fit=1.4, label='песочные часы')
    a(fx, 'whoosh-short', AD_STOP, align='peak', gain_db=-19, label='торможение на RubUp')
    a(fx, 'list', E.FAN50, gain_db=-19, label='веер 50')
    a(fx, 'list', E.FAN100, gain_db=-19, label='веер 100')
    a(fx, 'pop', E.CONTEST + 0.6, gain_db=-17, label='медаль')
    for j in range(4):
        a(fx, 'pop', E.CONTEST_ART + 0.18 * j, gain_db=-20, label=f'конкурсная работа {j + 1}')
    a(fx, 'sparkle-whoosh', E.REPAINT + 0.2, gain_db=-17, label='кулич раскрашивается')
    a(fx, 'confirm', E.UPGRADE + 0.05, gain_db=-18, label='улучшить')
    a(fx, 'paper', E.ERASE2 + 0.1, gain_db=-18, label='ластик (финал)')
    t = E.ERASE2 + 0.2
    j = 0
    while t < DUR - 0.3:                       # змейка: короткие «клики» шагов, тихо
        if j % 2 == 0:
            a(fx, 'key-space' if j % 4 == 0 else 'click', t, gain_db=-28, label='змейка')
        t += 0.44
        j += 1
    a(fx, 'select-soft', E.CHOICE, gain_db=-16, label='выбор')
    return fx * 10 ** (-1 / 20)


def creepy_cut(m):
    t = np.arange(len(m)) / SR
    g = 1 - np.clip((t - E.CREEPY + 0.05) / 0.08, 0, 1) + np.clip((t - E.CREEPY_END) / 0.9, 0, 1)
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
    sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    print('content', round(DUR, 2), 's; out', round(BR.out_dur(DUR), 2), 's')
