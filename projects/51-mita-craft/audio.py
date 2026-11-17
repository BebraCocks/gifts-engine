"""Голос Миты + «Okay, Everyone! (Natsuki)» + SFX (Botanica V4 через sfxkit) + полный звук RubUp.
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
import snap_preview as SP
from timeline import DUR, ON, TAKES, AD_STOP

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
    for j in range(3):
        a(fx, 'pop', E.HOOK_NFT + 0.14 * j, gain_db=-17, label=f'хук: крафтовая модель {j + 1}')
    a(fx, 'error', E.HOOK_NO + 0.1, gain_db=-22, label='улучшением — нельзя')
    a(fx, 'whoosh-short', E.HOOK_CRAFT + 0.5, align='peak', gain_db=-19, label='4 подарка слетаются')
    a(fx, 'sparkle', E.HOOK_CRAFT + 0.8, gain_db=-17, label='крафт: вспышка')
    a(fx, 'click', E.SNAP + SP.CLICK, gain_db=-12, label='щелчок пальцами')
    a(fx, 'riser', E.SNAP + SP.FLASH, align='end', gain_db=-21, label='круг разгорается')
    a(fx, 'transform', E.SNAP + SP.FLASH, gain_db=-15, label='вспышка: наряд звездочёта')
    a(fx, 'impact', E.SNAP + SP.T[SP.SEQ.index('astro_land')], gain_db=-20, label='приземление')
    a(fx, 'whoosh-organic', E.WALK1 + 0.3, gain_db=-22, label='Мита отходит')
    for j, ts in enumerate(E.SLOTS):
        a(fx, 'select', ts, gain_db=-17, label=f'подарок в слот {j + 1}')
    a(fx, 'power-up', E.CHANCE + 0.1, gain_db=-21, label='шанс растёт')
    a(fx, 'error', E.NEVER + 0.2, gain_db=-20, label='до конца — никогда')
    a(fx, 'whoosh-deep', E.BURN + 0.1, gain_db=-16, label='подарки сгорают')
    a(fx, 'glitch', E.CREEPY, gain_db=-14, label='ЖУТЬ: глитч, музыка обрывается')
    a(fx, 'sub-drop', E.CREEPY + 0.05, gain_db=-15, label='жуть: низкий гул')
    a(fx, 'glitch-texture', E.CREEPY_FULL + 0.1, gain_db=-20, label='ромбы в глазах')
    a(fx, 'glitch', E.CREEPY_END - 0.04, gain_db=-15, label='снова мило')
    a(fx, 'sparkle', E.TIER_ONLY + 0.1, gain_db=-17, label='модель над ладонью')
    for j, ts in enumerate(E.TIERS):
        a(fx, 'popup', ts, gain_db=-18, label=f'редкость {j + 1}')
    a(fx, 'scan', E.TEASE + 0.3, gain_db=-21, label='реже = дороже?')
    a(fx, 'whoosh-short', AD_STOP, align='peak', gain_db=-19, label='торможение на RubUp')
    a(fx, 'cartoon-hit', E.EPIC + 0.1, gain_db=-16, label='А вот и нет!')
    a(fx, 'pop', E.EPIC_BASE, gain_db=-18, label='обычный календарь')
    a(fx, 'coin', E.EPIC_CHEAP, gain_db=-17, label='эпик 1 289 ₽')
    a(fx, 'coin', E.EPIC_RICH, gain_db=-15, label='эпик 17 185 ₽')
    a(fx, 'pop', E.SHUF_SHOW, gain_db=-17, label='Shuffle')
    a(fx, 'pop', E.SHUF_LEG, gain_db=-18, label='легендарка')
    a(fx, 'sparkle-whoosh', E.SHUF_X2, gain_db=-16, label='в два раза')
    a(fx, 'whoosh', E.SWEEP + 0.1, gain_db=-16, label='взмах: россыпь дешёвых')
    a(fx, 'counter', E.FOUR + 0.1, gain_db=-19, label='4 подарка — потратили')
    a(fx, 'whoosh-organic', E.WALK2 + 0.3, gain_db=-22, label='Мита отходит')
    a(fx, 'sparkle', E.LOVE, gain_db=-18, label='нравится людям')
    for j, th in enumerate(E.KNOCK_HITS):
        a(fx, 'click', th, gain_db=-11, key='knock', semitones=-6, vary=False, fit=0.25, label=f'стук по экрану {j + 1}')
    a(fx, 'confirm', E.SAVE + 0.05, gain_db=-20, label='«сохранение…»')
    a(fx, 'scan', E.LOADING + 0.05, gain_db=-21, label='«загрузка»')
    for j, tp in enumerate(E.PUNCH):
        a(fx, 'whoosh-short', tp + 0.05, align='peak', gain_db=-22, label=f'наезд камеры {j + 1}')
    a(fx, 'select-soft', E.CHOICE, gain_db=-16, label='выбор как в игре')
    for k in range(1, 3):
        a(fx, 'click', E.CHOICE + 0.75 * k, gain_db=-22, label=f'курсор выбора {k}')
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
