"""Голос Миты + «Daijoubu!» (обрывается на жути) + SFX (через sfxkit) + звук RubUp. → build/mix.wav"""
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
import stage as S
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
    a(fx, 'scan', E.LENS0, gain_db=-17, fit=1.4, label='лупа проходит по Мите')
    a(fx, 'transform', E.LENS1 - 0.1, gain_db=-16, label='детектив!')
    for j in range(5):
        a(fx, 'select-soft', E.COUNTER_IN + 0.08 * j, gain_db=-24, label=f'счётчик {j + 1}')
    a(fx, 'popup', E.OFFER_SAY + 0.25, gain_db=-18, label='фейковый оффер')
    for k, segs in enumerate(S.SCAM, 1):                   # мошенницы: заход, испуг, побег
        wk, tk, rn = segs
        a(fx, 'cartoon-move', wk['t0'] + 0.2, gain_db=-22, label=f'мошенница {k} заходит')
        a(fx, 'boing', E.STAMPS[k - 1] + 0.05, gain_db=-19, label=f'мошенница {k} вздрогнула')
        a(fx, 'whoosh-short', rn['pieces'][1][0], gain_db=-18, label=f'мошенница {k} убегает')
    a(fx, 'flip', E.LANG, gain_db=-19, label='смена языка')
    a(fx, 'confirm', E.REAL, gain_db=-20, label='настоящее перевелось')
    a(fx, 'error', E.FAKE, gain_db=-19, label='фейк — нет')
    a(fx, 'typing', E.ASK + 0.2, gain_db=-22, fit=0.8, label='вопрос другу')
    a(fx, 'sub-drop', E.CREEPY + 0.05, gain_db=-15, label='ЖУТЬ: музыка обрывается')
    a(fx, 'typing', E.CREEPY + 0.3, gain_db=-20, fit=4.2, label='«это я» печатается само')
    a(fx, 'glitch-texture', E.CREEPY_END - 1.0, gain_db=-21, label='улыбка')
    a(fx, 'riser', E.TEASE + 0.2, gain_db=-21, fit=2.5, label='самая хитрая…')
    a(fx, 'whoosh-short', AD_STOP, align='peak', gain_db=-19, label='торможение на RubUp')
    a(fx, 'popup', E.LINK_MSG, gain_db=-19, label='ссылка')
    a(fx, 'scan', E.LINK_LENS, gain_db=-19, label='лупа: rn ≠ m')
    a(fx, 'error', E.LINK_LENS + 0.7, gain_db=-19, label='не переходи')
    a(fx, 'confirm', E.GUAR_SAFE, gain_db=-18, label='маркет Telegram')
    for k, ts in enumerate(E.STAMPS):
        a(fx, 'impact', ts, gain_db=-14, label=f'ШТАМП {k + 1}')
        a(fx, 'paper', ts + 0.05, gain_db=-20, label=f'улика {k + 1} на доску')
    for k, tn in enumerate((E.NOTE1, E.NOTE2, E.NOTE3)):
        a(fx, 'pop', tn, gain_db=-18, label=f'памятка {k + 1}')
    a(fx, 'sparkle-whoosh', E.MOVE2, gain_db=-19, label='в центр')
    a(fx, 'select-soft', E.MOVE2 + 0.6, gain_db=-17, label='«БЫЛО»')
    a(fx, 'select-soft', E.MOVE2 + 1.8, gain_db=-17, label='«НЕ БЫЛО»')
    a(fx, 'impact', DUR - 0.55, gain_db=-15, label='ДЕЛО ЗАКРЫТО')
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
