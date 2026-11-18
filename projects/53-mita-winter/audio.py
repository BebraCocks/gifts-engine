"""Голос Миты + «Dreams of Love and Literature» (обрывается на жути) + SFX (через sfxkit) + звук RubUp. → build/mix.wav"""
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


def bells(n, times, gain_db=-24):
    """Тихие бубенчики (синтез): короткие звоны 2–3 обертонами — новогоднее настроение без чужих сэмплов."""
    out = np.zeros((n, 2))
    rng = np.random.default_rng(5)
    for t0 in times:
        for k in range(3):
            s = int((t0 + k * 0.07 + rng.uniform(0, 0.02)) * SR)
            L = int(0.9 * SR)
            if s + L > n:
                continue
            tt = np.arange(L) / SR
            f = rng.choice([2093, 2349, 2637, 3136])
            y = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 9)) * np.exp(-tt * 5)
            pan = rng.uniform(0.3, 0.7)
            out[s:s + L, 0] += y * (1 - pan)
            out[s:s + L, 1] += y * pan
    return out * 10 ** (gain_db / 20)


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    a = kit.add
    a(fx, 'sparkle', 0.5, gain_db=-21, label='подарки-игрушки на гирлянде')
    a(fx, 'popup', E.GLOVES_Q + 0.05, gain_db=-18, label='силуэт перчаток «?»')
    a(fx, 'pop', E.BOX_IN, gain_db=-17, label='коробка появилась')
    a(fx, 'sparkle-whoosh', E.BOX_IN + 0.9, gain_db=-16, label='вихрь лент')
    a(fx, 'transform', E.FLASH - 0.1, gain_db=-15, label='вспышка — новый наряд')
    a(fx, 'impact', E.FLASH + 0.05, gain_db=-22, label='салют за окном')
    a(fx, 'pop', E.BOX_POOF, gain_db=-20, label='коробка исчезла')
    for j, (t0, lab) in enumerate(((E.HAT, 'шапка'), (E.COOKIE, 'пряник'), (E.BELL, 'колокольчик'), (E.STOCK, 'носок'))):
        a(fx, 'select', t0 + 0.05, gain_db=-19, label=f'{lab}: игрушка')
        a(fx, 'counter', t0 + 0.3, gain_db=-22, fit=0.8, label=f'{lab}: градусник')
    a(fx, 'whoosh-short', E.COOKIE + 0.4, gain_db=-22, label='дышит на стекло')
    a(fx, 'paper', E.COOKIE + 2.0, gain_db=-21, label='пишет пальцем')
    a(fx, 'sparkle', E.COOKIE_MAMA + 0.3, gain_db=-19, label='пряник красивый, как свитер')
    a(fx, 'sparkle', E.BELL + 0.2, gain_db=-18, label='колокольчик блестит')
    a(fx, 'power-down', E.STOCK_NOBODY, gain_db=-22, label='носок никнет')
    a(fx, 'sub-drop', E.CREEPY + 0.05, gain_db=-15, label='ЖУТЬ: музыка обрывается, гул')
    a(fx, 'granular-move', E.CREEPY + 0.3, gain_db=-21, fit=2.5, label='шар опускается, иней ползёт')
    a(fx, 'glitch-texture', E.CREEP_B, gain_db=-22, label='лёд')
    a(fx, 'whoosh-deep', E.CREEPY + 0.1, gain_db=-19, label='шар на нитке опускается')
    a(fx, 'impact', E.CREEP_C + 0.05, gain_db=-20, label='трещина по стеклу')
    a(fx, 'impact', E.CREEPY_END, gain_db=-15, label='шар разбивается')
    a(fx, 'sparkle-whoosh', E.CREEPY_END + 0.05, gain_db=-18, label='осколки')
    a(fx, 'pop', E.TEASE, gain_db=-18, label='перчатки')
    a(fx, 'boing', E.TEASE_JUMP + 0.05, gain_db=-17, label='перчатки прыгают')
    a(fx, 'whoosh-short', AD_STOP, align='peak', gain_db=-19, label='торможение на RubUp')
    a(fx, 'sparkle-whoosh', E.MOVE1, gain_db=-19, label='снежная россыпь — влево')
    a(fx, 'popup', E.RUMOR_VIDEO, gain_db=-19, label='видео в тиктоке')
    a(fx, 'flip', E.RUMOR_POST, gain_db=-18, label='пост')
    a(fx, 'error', E.RUMOR_DEL + 0.1, gain_db=-18, label='пост удалён')
    a(fx, 'power-up', E.SPREAD + 0.5, gain_db=-21, label='окна загораются цепочкой')
    for k, dt in enumerate((0.2, 0.6, 1.0, 1.4)):
        a(fx, 'pop', E.SPREAD + dt, gain_db=-21, label=f'бабл {k + 1}')
    a(fx, 'riser', E.PRICE_NOW - 0.2, gain_db=-21, fit=1.4, label='цена растёт')
    a(fx, 'coin', E.PRICE_X2, gain_db=-17, label='×2+')
    a(fx, 'scan', E.TRUTH + 0.1, gain_db=-21, label='вопрос')
    a(fx, 'list', E.TRUTH_MARKET + 0.1, gain_db=-20, label='график растёт')
    a(fx, 'sparkle-whoosh', E.MOVE2, gain_db=-19, label='снежная россыпь — в центр')
    a(fx, 'whoosh', E.MOVE2 + 1.0, gain_db=-19, label='Мита трясёт шар')
    a(fx, 'sparkle', E.MOVE2 + 1.2, gain_db=-18, label='метель в шаре: ВЕРЮ / НЕ ВЕРЮ')
    a(fx, 'whoosh', DUR - 1.4, gain_db=-17, label='снежный шар встряхивают')
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
    jingle = [E.HAT + 0.3, E.COOKIE + 0.3, E.BELL + 0.2, E.BELL + 0.6, E.FLASH, E.MOVE2 + 0.3, E.CHOICE]
    fx += creepy_cut(bells(n, jingle))
    fx *= (1 - 0.45 * env)[:, None]
    data = BR.audio(v + m + fx, SR)
    build = paths.build(HERE)
    save_wav(build / 'mix.wav', data)
    kit.save(BR)
    sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    print('content', round(DUR, 2), 's; out', round(BR.out_dur(DUR), 2), 's')
