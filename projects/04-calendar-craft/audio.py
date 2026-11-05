"""Voices (narrator, Алексей, Михаил) + SFX from Botanica V4 via sfxkit + the complete RubUp sound.
Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt. Fire crackle is synthesised:
the pack has no fire sound (recorded in STORYBOARD.md, section 4)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import wave
from scipy.signal import butter, sosfilt
import banner
import sound
import sfxkit
import config
import events as E
from timeline import DUR, ON, END, HAS_NARRATION, TAKES, SPEAKER

SR = 48000
from script import TTS_TEXT
WHISPER = {k for k, x in enumerate(TTS_TEXT) if 'whisper' in x.split(']')[0]}   # whispered lines stay softer
BR = banner.Breaks([E.AD_STOP], cy=960)


def fire_crackle(dur, seed=5):
    """Filtered noise bed with random crackles and a soft attack/decay (stereo)."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.normal(0, 1, (n, 2))
    x = sosfilt(butter(2, [300, 3500], 'band', fs=SR, output='sos'), x, axis=0) * 0.25
    roar = sosfilt(butter(2, 180, 'low', fs=SR, output='sos'), rng.normal(0, 1, (n, 2)), axis=0) * 1.6
    cr = np.zeros((n, 2))
    for _ in range(int(dur * 38)):
        i = rng.integers(0, n - 800)
        k = rng.integers(60, 600)
        cr[i:i + k, rng.integers(0, 2)] += rng.normal(0, 1, k) * np.exp(-np.arange(k) / (k / 5)) * rng.uniform(0.4, 1.6)
    y = x + roar + cr * 0.5
    env = np.minimum(1, np.arange(n) / (0.25 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.8 * SR))
    y *= env[:, None]
    return y / (np.abs(y).max() + 1e-9) * 0.5


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    A = kit.add
    # hook
    A(fx, 'whoosh-short', 0.02, gain_db=-16, label='open on the face')
    A(fx, 'pop', E.wt('hook', 'обедов') - 0.08, gain_db=-16, label='«БЕЗ ОБЕДОВ»')
    A(fx, 'whoosh-short', E.HOOK_CUT, align='peak', gain_db=-15, label='cut to the thumb')
    A(fx, 'select-soft', E.HOOK_CUT + 0.08, gain_db=-17, label='«РАДИ ОДНОЙ КНОПКИ»')
    # canteen: coins into the piggy bank, pages fly
    A(fx, 'whoosh-short', E.CANTEEN, align='peak', gain_db=-15, label='cut to the canteen')
    for k, c in enumerate(E.COINS):
        A(fx, 'coin', c + 0.38, gain_db=-17, pan=0.2, label=f'coin {k + 1} in the piggy bank')
        A(fx, 'paper', c + 0.02, gain_db=-22, pan=0.5, fit=0.5, label=f'calendar page {k + 1}')
    A(fx, 'sparkle', E.FULL, gain_db=-20, fit=1.2, label='piggy bank full')
    # 3D vault
    A(fx, 'sparkle-whoosh', E.VAULT, align='peak', gain_db=-13, label='flash into the 3D vault')
    A(fx, 'whoosh-deep', E.VAULT + 2.0, gain_db=-20, fit=3.0, label='fly-through')
    A(fx, 'riser-hit', E.LEGEND_WORD, align='peak', gain_db=-15, label='«Легендарных — 5»')
    # first craft
    A(fx, 'whoosh-short', E.FIRST, align='peak', gain_db=-16, label='back to the hallway')
    A(fx, 'confirm', E.wt('first', 'крафт'), gain_db=-20, label='phone up')
    for k, s in enumerate(E.SLOT_T):
        A(fx, 'select', s + 0.18, gain_db=-15, pan=(-0.3, 0.3, -0.3, 0.3)[k], label=f'calendar {k + 1} into the slot')
    A(fx, 'counter', E.CHANCE0, gain_db=-19, fit=E.CHANCE1 - E.CHANCE0 + 0.1, label='chance counts up to 89%')
    A(fx, 'click', E.PRESS, gain_db=-11, label='«Крафтить» pressed')
    A(fx, 'riser', E.BURN0, align='end', gain_db=-14, fit=1.2, label='vortex builds')
    A(fx, 'impact', E.BURN0, gain_db=-11, label='craft fails: fire')
    A(fx, 'error', E.FAIL, gain_db=-12, label='«Крафт не удался»')
    A(fx, 'power-down', E.FAIL + 0.2, gain_db=-17, label='hope goes out')
    # realisation, rage, throw, smash
    A(fx, 'cartoon', E.REALISE, gain_db=-20, file='crickets', fit=1.0, label='silence of realisation')
    A(fx, 'stretch', E.RAGE + 0.3, gain_db=-20, label='face turns red')
    A(fx, 'cartoon-move', E.THROW, gain_db=-13, file='whoosh', label='throw')
    A(fx, 'cartoon-hit', E.IMPACT, align='peak', gain_db=-6, file='smash', label='phone smashes into the locker')
    A(fx, 'foley', E.IMPACT + 0.05, gain_db=-14, file='demolition', fit=1.2, label='shards')
    A(fx, 'spinback', E.FREEZE, align='peak', gain_db=-12, label='«Стоп-кадр» record scratch')
    A(fx, 'shutter', E.FREEZE + 0.02, gain_db=-16, label='freeze frame')
    # after RubUp
    A(fx, 'cartoon', E.MISHA_IN - 0.3, gain_db=-20, file='tiptoe', label='Михаил walks in')
    A(fx, 'cartoon', E.MISHA_IN + 0.9, gain_db=-21, file='chomp', label='bun bite')
    A(fx, 'pop', E.THINK + 0.2, gain_db=-19, label='thinking dots')
    A(fx, 'select-soft', E.PHONE_OUT, gain_db=-17, label='phone out')
    A(fx, 'whoosh-short', E.PHONE2, align='peak', gain_db=-15, label='cut to Михаил’s phone')
    A(fx, 'select', E.SLOT2 + 0.18, gain_db=-15, label='one calendar into the slot')
    A(fx, 'counter', E.CH2_0, gain_db=-20, fit=1.0, label='chance 22%')
    A(fx, 'click', E.PRESS2, gain_db=-12, label='careless tap')
    A(fx, 'riser', E.FLASH2, align='end', gain_db=-15, fit=0.6, label='quick build')
    A(fx, 'sub-drop', E.LEGEND, gain_db=-10, label='LEGENDARY drop')
    A(fx, 'sparkle', E.LEGEND + 0.1, gain_db=-14, fit=2.3, label='legendary shimmer')
    A(fx, 'confirm', E.LEGEND + 0.35, gain_db=-15, label='«LEGENDARY» title')
    A(fx, 'cartoon', E.UGLY, gain_db=-20, file='taunt', label='«Фу»')
    A(fx, 'popup', E.OFFER - 0.1, gain_db=-14, label='purchase offer 100 ₽')
    A(fx, 'click', E.ACCEPT - 0.05, gain_db=-13, label='«Принять»')
    A(fx, 'coin', E.ACCEPT + 0.05, gain_db=-16, label='sold')
    A(fx, 'cartoon', E.LEAVE, gain_db=-20, file='tiptoe', label='Михаил leaves')
    A(fx, 'cartoon-hit', E.SHOCK, align='peak', gain_db=-12, file='bonk', label='shock zoom')
    A(fx, 'cartoon', E.SHOCK + 0.05, gain_db=-19, file='eye-whistle', fit=0.35, label='eye twitch')
    if hasattr(E, 'WTF'):
        A(fx, 'stretch', E.WTF - 0.15, gain_db=-19, label='Алексей boils over')
    A(fx, 'whoosh', E.MORAL, align='peak', gain_db=-15, label='moral')
    A(fx, 'pop', E.MORAL + 0.25, gain_db=-17, label='89% plate')
    A(fx, 'pop', E.MORAL + 0.5, gain_db=-17, label='22% plate')
    A(fx, 'whoosh-short', E.CTA, align='peak', gain_db=-15, label='CTA')
    A(fx, 'boing', E.LIKE, gain_db=-14, label='like button')
    A(fx, 'popup', E.wt('cta', 'друг') - 0.2, gain_db=-16, label='comment question')
    # vocal reactions from the Botanica «human» folder (intonations under the action, not words)
    V = dict(role='voice', vary=False)
    A(fx, t=E.COINS[3] + 0.1, gain_db=-17, file='human/tired', label='tired sigh (Алексей худеет)', **V)
    A(fx, t=E.SLOT_T[3] + 0.35, gain_db=-16, file='human/excited', label='«Oh!» all four slots filled', **V)
    A(fx, t=E.THUMB_IN - 0.3, gain_db=-17, file='human/nervous', label='nervous «mm» before the press', **V)
    A(fx, t=E.FAIL + 0.05, gain_db=-14, file='human/oppss', label='«uh-oh» the craft burned', **V)
    A(fx, t=E.SMILE_GONE, gain_db=-17, file='human/upset', label='upset «mm» smile slides off', **V)
    A(fx, t=E.REALISE + 0.1, gain_db=-15, file='human/scared.', label='«ah» realisation', **V)
    A(fx, t=E.THINK + 0.15, gain_db=-14, file='human/interesting', label='Михаил thinks «hmm»', **V)
    A(fx, t=E.LEGEND + 0.25, gain_db=-17, file='human/public', label='crowd «ooh» at LEGENDARY', **V)
    A(fx, t=E.OFFER - 0.35, gain_db=-17, file='human/bored', label='«oh» an offer pops up', **V)
    A(fx, t=E.ACCEPT + 0.02, gain_db=-16, file='human/okay', label='«okay» accept 100 ₽', **V)
    A(fx, t=E.SHOCK + 0.02, gain_db=-15, file='human/scared-2', label='Алексей gasps', **V)
    # synthesised fire under the burn (no fire sound in the pack)
    f = fire_crackle(E.FACE - E.BURN0 + 0.4)
    i0 = int(E.BURN0 * SR)
    fx[i0:i0 + len(f)] += f[:max(0, min(len(f), n - i0))] * 10 ** (-10 / 20)
    kit.cues.append(dict(t=round(E.BURN0, 3), at=round(E.BURN0, 3), align='start', gain_db=-10, pan=0,
                         label='fire crackle (synthesised)', id='synth:fire', role='synth', dur=len(f) / SR))
    return fx


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            e = np.sqrt(np.convolve(data[:, 0] ** 2, np.ones(2400) / 2400, 'same'))
            rms = 20 * np.log10(np.sqrt((data[e > e.max() * 0.1, 0] ** 2).mean()) + 1e-9)
            target = -17.0 if k in WHISPER else -14.0          # equal speech loudness across the 3 voices
            data = data * 10 ** (np.clip(target - rms, -4, 12) / 20)
            start = round(ON[k] * SR)
            count = min(len(data), n - start)
            voice[start:start + count] += data[:count] * config.VOICE_GAIN[SPEAKER[k]]
    else:
        print('Дикторской озвучки нет: текст + звук баннера.')
    fx = sfx_layer(n, kit)
    if HAS_NARRATION:                       # SFX step back under speech
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        fx *= (1 - 0.45 * np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1))[:, None]
    mix = voice + fx
    mix = np.tanh(mix * 1.15) / 1.15                       # soft peak limiter (whispered/shouted takes)
    return mix, fx


if __name__ == '__main__':
    kit = sfxkit.Kit(HERE)
    content, fx = make_mix(kit)
    data = BR.audio(content, SR)
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    kit.save(BR)
    rev = sfxkit.write_review(HERE, fx, data, BR, SR, kit.cues)
    print(f'build/mix.wav {len(data) / SR:.2f} s; review:', rev / 'sfx_only.mp3', rev / 'mix.mp3', rev / 'sfx_cues.txt')
