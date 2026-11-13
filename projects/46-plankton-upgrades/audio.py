"""Звук ролика 46: голоса (voice/Lxx_*.wav), музыка и звуки из мультфильма (input/ext/, просьба автора 2026-11-13),
SFX пака Botanica через sfxkit (без повторов), RubUp целиком со звуком на паузе содержания.
Пишет build/mix.wav и для автора build/review/{sfx_only,mix}.mp3 + sfx_cues.txt."""
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
from timeline import DUR, ON, TAKES, HAS_NARRATION, AT, END_OF
from events import AD_STOP, SLIDE, TRANSITIONS, ROUNDS, PLANKTON_PICK
from script import TIMER

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)
EXT = HERE / 'input' / 'ext'
# Интегральная громкость файлов (ffmpeg ebur128, 2026-11-13) — чтобы задавать уровень в LUFS, а не «на глаз».
LUFS = {'tomfoolery-1-spongebob-squarepants': -14.1, 'hawaiian-cocktail-spongebob-squarepants': -11.6,
        'rakehornpipe-spongebob-squarepants': -11.8, 'krusty-krab-theme-song': -15.2, 'dramatic-cue-a': -20.0,
        'spongebob-bubble-transition': -28.7}
MUSIC_LUFS = -29.0
MASTER_DB = 1.5          # итог около −16 LUFS, пик ниже −0,5 dBFS


def ext(buf, name, t, level_lufs, start=0.0, dur=None, fade_in=0.05, fade_out=0.3):
    """Внешний звук из input/ext/ в буфер содержания с уровнем по LUFS и мягкими краями."""
    x = sound.load_stereo(EXT / f'{name}.mp3', SR, start=start, dur=dur) * 10 ** ((level_lufs - LUFS[name]) / 20)
    fi, fo = int(fade_in * SR), min(len(x), int(fade_out * SR))
    x[:fi] *= np.linspace(0, 1, fi)[:, None]
    x[len(x) - fo:] *= np.linspace(1, 0, fo)[:, None]
    i0 = int(round(t * SR))
    n = min(len(x), len(buf) - i0)
    buf[i0:i0 + n] += x[:n]


def music_layer(n):
    m = np.zeros((n, 2))
    ext(m, 'tomfoolery-1-spongebob-squarepants', 0.0, MUSIC_LUFS, dur=TRANSITIONS[1] + 0.4, fade_in=0.01, fade_out=0.8)
    ext(m, 'hawaiian-cocktail-spongebob-squarepants', TRANSITIONS[1] - 0.2, MUSIC_LUFS,
        dur=TRANSITIONS[2] - TRANSITIONS[1] + 0.6, fade_in=0.4, fade_out=0.8)
    ext(m, 'rakehornpipe-spongebob-squarepants', TRANSITIONS[2] - 0.2, MUSIC_LUFS,
        dur=AT['P7'] - TRANSITIONS[2] + 0.4, fade_in=0.4, fade_out=0.5)
    ext(m, 'krusty-krab-theme-song', AT['N8'] - 0.2, MUSIC_LUFS - 1, dur=DUR - AT['N8'] + 0.2, fade_in=0.6, fade_out=0.6)
    return m


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    # Хук: модель влетает с кадра 0, три карточки «?» мигают, Планктон выпрыгивает
    kit.add(fx, 'whoosh-short', 0.05, gain_db=-14, label='хук: Скибиди-туалет влетает')
    for k, t in enumerate((0.55, 0.8, 1.05)):
        kit.add(fx, 'pop', t, gain_db=-18, pan=(k - 1) * 0.4, label=f'хук: карточка «?» {k + 1}')
    kit.add(fx, 'boing', AT['P1'] - 0.1, gain_db=-15, label='Планктон выпрыгивает')
    # Переходы-пузыри (звук из мультфильма): гуще всего пузыри — в момент смены раунда
    for k, t in enumerate(TRANSITIONS):
        ext(fx, 'spongebob-bubble-transition', t - 1.1, -21.0, start=0.3, dur=2.7, fade_out=0.4)
    # Раунды
    for r, (q, timer, answer) in enumerate(ROUNDS):
        kit.add(fx, 'whoosh-short', q, align='peak', gain_db=-15, label=f'раунд {r + 1}: модель влетает')
        for k in range(3):
            kit.add(fx, 'select-soft', q + 0.45 + 0.18 * k, gain_db=-20, pan=(k - 1) * 0.4,
                    label=f'раунд {r + 1}: карточка {k + 1}')
        if timer is not None:
            for s in range(int(TIMER)):
                kit.add(fx, 'counter', timer + s, gain_db=-21, label=f'раунд {r + 1}: таймер {int(TIMER) - s}')
        kit.add(fx, 'select', PLANKTON_PICK[r] + 0.15, gain_db=-17, label=f'раунд {r + 1}: метка Планктона на карточке')
        kit.add(fx, 'transform', answer - 0.05, gain_db=-15, label=f'раунд {r + 1}: модель распадается в подарок')
        kit.add(fx, 'confirm', answer + 0.35, gain_db=-16, label=f'раунд {r + 1}: верная карточка загорается')
        kit.add(fx, 'error', answer + 0.75, gain_db=-19, label=f'раунд {r + 1}: метка Планктона гаснет')
    # RubUp без подводки: Планктон с моделью уезжает вниз и возвращается
    kit.add(fx, 'cartoon-move', AD_STOP - SLIDE, gain_db=-17, label='Планктон уезжает вниз (перед RubUp)')
    kit.add(fx, 'cartoon-move', AD_STOP + 0.02, gain_db=-17, label='Планктон возвращается (после RubUp)')
    # Реакции
    kit.add(fx, 'cartoon-hit', AT['P3'], gain_db=-17, label='Планктон трясётся от злости')
    kit.add(fx, 'coin', AT['KR'] + 0.1, gain_db=-17, label='Крабс: денежки')
    ext(fx, 'dramatic-cue-a', AT['P7'] + 0.9, -20.0, start=0.19, dur=4.6, fade_out=0.6)   # «дан-дан-дан» под «Я ещё вернусь»
    kit.add(fx, 'impact', AT['N8'] - 0.05, gain_db=-17, label='итоговый счёт крупно')
    kit.add(fx, 'whoosh-short', DUR - 0.9, gain_db=-17, label='Планктон уходит за край')
    return fx


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2))
    if HAS_NARRATION:
        for take, t in zip(TAKES, ON):
            d = sound.load_stereo(take, SR)
            i0 = round(t * SR)
            c = min(len(d), n - i0)
            voice[i0:i0 + c] += d[:c] * 0.85
    fx = sfx_layer(n, kit)
    music = music_layer(n)
    env = np.convolve(np.abs(voice).max(1), np.ones(2400) / 2400, 'same')
    duck = np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1)
    fx *= (1 - 0.45 * duck)[:, None]
    music *= (1 - 0.5 * duck)[:, None]
    i7 = int((AT['P7'] + 0.9) * SR)                    # под «дан-дан-дан» музыка уходит
    music[i7:int(AT['N8'] * SR) - int(0.2 * SR)] *= 0.15
    return voice + fx + music, fx, voice


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE)
    content, fx, voice = make_mix(kit)
    data = BR.audio(content, SR) * 10 ** (MASTER_DB / 20)
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    import subprocess, tempfile
    vo = BR.audio(voice, SR)                     # голос по таймлайну (с паузой и звуком RubUp) — сразу автору
    with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
        with wave.open(tmp.name, 'wb') as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(vo, -0.98, 0.98) * 32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp.name, '-b:a', '192k', str(rev / 'voice_only.mp3')], check=True)
    print('build/mix.wav:', round(len(data) / SR, 2), 'с;', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')
