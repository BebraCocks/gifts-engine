"""Narration (Fish Audio drama-3, author's voice) + SFX from Botanica V4 via sfxkit + the complete RubUp sound.
No music. Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt.

The clock ticking that runs through the pawnshop and stops dead on «Другого раза не случилось» is synthesised:
the pack has no steady clock tick (only a one-shot cartoon clock), and the motif must be exactly regular.
"""
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
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES
from events import AD_STOP, S, E

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)


def ticks(t0, t1, period=0.5, gain_db=-24.0):
    """Clock tick-tock: short band-passed clicks, alternating pitch. Stereo float, from t0 to t1 (content s)."""
    n = int((t1 - t0) * SR)
    out = np.zeros((n, 2))
    rng = np.random.default_rng(5)
    k = 0
    while k * period < (t1 - t0):
        i = int(k * period * SR)
        m = int(0.03 * SR)
        noise = rng.normal(0, 1, m) * np.exp(-np.linspace(0, 9, m))
        f = (2600, 5200) if k % 2 == 0 else (1900, 3800)
        y = sosfilt(butter(2, f, 'bandpass', fs=SR, output='sos'), noise)
        y = y / (np.abs(y).max() + 1e-9)
        j = min(n, i + m)
        out[i:j, 0] += y[:j - i] * (0.9 if k % 2 else 1.0)
        out[i:j, 1] += y[:j - i] * (1.0 if k % 2 else 0.9)
        k += 1
    return out * 10 ** (gain_db / 20)


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    A = kit.add
    # hook: Pepe falls onto the counter, the Saturday page burns
    A(fx, 'whoosh-short', E['pepe_land'], align='end', gain_db=-16, label='Pepe falls')
    A(fx, 'impact', E['pepe_land'], align='peak', gain_db=-11, label='Pepe lands on the counter')
    A(fx, 'paper', E['pepe_land'] + 0.3, gain_db=-20, fit=0.6, label='price tag swings in')
    A(fx, 'granular-move', E['page_burn'], gain_db=-17, label='the Saturday page burns')
    # room at night
    A(fx, 'whoosh', S['room'], align='peak', gain_db=-15, label='whip pan to the room')
    A(fx, 'popup', E['cake_msg'] - 0.05, gain_db=-15, label="grandma's gift arrives")
    A(fx, 'sparkle', E['cake_msg'] + 0.1, gain_db=-23, fit=1.2, label='Homemade Cake gift')
    A(fx, 'select-soft', E['cake_text'] - 0.1, gain_db=-18, label='her message')
    A(fx, 'glitch', E['bot_msg'] - 0.1, gain_db=-15, label='the bot glitches in')
    A(fx, 'typing', E['bot_text'], gain_db=-21, fit=2.4, label='bot types its offer')
    A(fx, 'riser', S['shop'], align='end', gain_db=-16, fit=1.4, label='pulled into the phone')
    A(fx, 'sparkle-whoosh', S['shop'], align='peak', gain_db=-13, label='flash into the pawnshop')
    # deals: page torn -> firefly into the jar -> gift appears
    for k, key in enumerate(('tear1', 'tear2', 'tear3', 'tear4')):
        t0 = E[key]
        A(fx, 'paper', t0, gain_db=-17, fit=0.7, pan=-0.3, label=f'page {k + 1} torn off')
        A(fx, 'whoosh-short', t0 + 0.6, gain_db=-21, pan=0.2, label=f'firefly {k + 1} flies')
        A(fx, 'select-soft', t0 + 1.25, gain_db=-17, pan=0.4, label=f'firefly {k + 1} into the jar')
    for key, lab in (('cookie', 'Ginger Cookie'), ('globe', 'Snow Globe'), ('player', 'Record Player'),
                     ('cap', "Durov's Cap")):
        A(fx, 'pop', E[key], gain_db=-15, label=f'{lab} appears')
        A(fx, 'coin', E[key] + 0.05, gain_db=-22, label=f'{lab}: deal')
    A(fx, 'transform', E['tear2'] - 0.25, gain_db=-20, label='calendar turns into «Sunday»')
    # the rule
    A(fx, 'whoosh-short', E['rule_a'] - 0.1, align='peak', gain_db=-17, label='«ЧЕМ ДОРОЖЕ ЧАС…» plate')
    A(fx, 'confirm', E['rule_b'] - 0.05, gain_db=-17, label='«…ТЕМ ДОРОЖЕ ПОДАРОК»')
    # rich: the world loses colour, friends' messages
    A(fx, 'power-down', E['tear3'] + 0.4, gain_db=-20, label='colour drains')
    for k, t0 in enumerate((E['tear3'] + 0.3, E['tear4'], E['cap'] + 0.3)):
        A(fx, 'select', t0, gain_db=-21, pan=-0.4, label=f'friends message {k + 1} (unanswered)')
    A(fx, 'whoosh-short', S['safe'] - 0.45, gain_db=-17, label='Лёва takes the gifts')
    # the safe
    A(fx, 'foley', E['safe_open'] - 0.05, gain_db=-17, fit=1.0, label='safe dial / lock')
    A(fx, 'riser', E['safe_light'] + 0.9, align='end', gain_db=-14, fit=2.0, label='golden light builds')
    A(fx, 'whoosh-deep', AD_STOP, align='peak', gain_db=-16, label='slow-down to RubUp')
    # the lot
    A(fx, 'riser-hit', S['lot'] + 0.05, align='peak', gain_db=-14, label='Plush Pepe revealed')
    A(fx, 'sparkle', S['lot'] + 0.2, gain_db=-17, fit=2.5, label='golden Pepe shimmer')
    A(fx, 'paper', E['price_tag'], gain_db=-19, fit=0.5, label='price tag')
    A(fx, 'pop', E['saturday'], gain_db=-15, label='«1 суббота» calendar')
    # «в другой раз» + signature
    A(fx, 'cartoon-move', E['shrug'], gain_db=-21, label='careless shrug')
    A(fx, 'whoosh-short', E['signs'] - 0.55, align='peak', gain_db=-18, label='cut to the contract')
    A(fx, 'stretch', E['signs'], gain_db=-21, fit=0.6, label='pen signs')
    A(fx, 'paper', E['signs'] + 0.35, gain_db=-19, fit=0.6, label='the Saturday page lifts off')
    # silence in the kitchen
    A(fx, 'sub-drop', E['stop_tick'], gain_db=-14, label='ticking stops: «Другого раза…»')
    A(fx, 'ambience', S['never'] + 0.1, gain_db=-34, fit=S['return'] - S['never'] - 0.2, fade_out=0.8,
      label="quiet room tone in grandma's kitchen")
    A(fx, 'flip', S['never'] + 1.4, gain_db=-24, label='calendar pages run forward')
    # back to the shop
    A(fx, 'whoosh', S['return'], align='peak', gain_db=-16, label='back to the shop')
    for k in range(5):
        A(fx, 'cartoon-hit', E['pour'] + 0.44 + 0.14 * k, align='peak', gain_db=-19 - k, pan=(-0.3, 0.3)[k % 2],
          label=f'gift {k + 1} thrown on the counter')
    A(fx, 'whoosh-short', E['please'] - 0.15, align='peak', gain_db=-19, label='close-up «Верните субботу»')
    # refusal + profile
    A(fx, 'error', E['no'] + 0.1, gain_db=-20, label='«Обратно не продаю»')
    A(fx, 'whoosh-short', E['profile'] - 0.1, align='peak', gain_db=-17, label='cut to the profile')
    A(fx, 'list', E['profile'] + 0.1, gain_db=-23, fit=0.8, label='gift grid')
    A(fx, 'sparkle', E['grandma_gift'], gain_db=-18, fit=1.4, label="grandma's gift lights up")
    # the offer to the viewer
    A(fx, 'stretch', E['slide'], gain_db=-20, label='Pepe slides towards you')
    A(fx, 'impact', E['waits'] + 0.05, gain_db=-20, label='heartbeat «ждёт»')
    # vote
    A(fx, 'whoosh-short', S['vote'], align='peak', gain_db=-16, label='vote screen')
    A(fx, 'popup', E['card_l'] - 0.25, gain_db=-14, label='card 🐸 БЕРУ')
    A(fx, 'popup', E['card_r'] - 0.25, gain_db=-14, label='card ⏳ ОСТАВЛЮ ВЕЧЕР')
    # the ticking motif: pawnshop scenes, stops on «Другого раза…»
    tk = ticks(S['shop'], E['stop_tick'])
    i0 = int(S['shop'] * SR)
    fx[i0:i0 + len(tk)] += tk[:max(0, min(len(tk), n - i0))]
    kit.cues.append(dict(t=round(S['shop'], 3), at=round(S['shop'], 3), align='start', gain_db=-24, pan=0,
                         label='clock ticking (synthesised) until «Другого раза…»', id='synth:tick', role='synth',
                         dur=len(tk) / SR))
    tk0 = ticks(0.0, S['room'] + 0.2, gain_db=-22)
    fx[:len(tk0)] += tk0[:n]
    kit.cues.append(dict(t=0.0, at=0.0, align='start', gain_db=-22, pan=0, label='hook: clock ticking',
                         id='synth:tick0', role='synth', dur=len(tk0) / SR))
    tk2 = ticks(S['return'], DUR - 0.2, gain_db=-28)
    i0 = int(S['return'] * SR)
    fx[i0:i0 + len(tk2)] += tk2[:max(0, min(len(tk2), n - i0))]
    kit.cues.append(dict(t=round(S['return'], 3), at=round(S['return'], 3), align='start', gain_db=-28, pan=0,
                         label='ticking resumes, quieter', id='synth:tick2', role='synth', dur=len(tk2) / SR))
    return fx


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            e = np.sqrt(np.convolve(data[:, 0] ** 2, np.ones(2400) / 2400, 'same'))
            rms = 20 * np.log10(np.sqrt((data[e > e.max() * 0.1, 0] ** 2).mean()) + 1e-9)
            target = -17.0 if KEY['never'] == k else -14.0           # «Другого раза…» stays quiet
            data = data * 10 ** (np.clip(target - rms, -4, 12) / 20)
            start = round(ON[k] * SR)
            count = min(len(data), n - start)
            voice[start:start + count] += data[:count]
    else:
        print('Дикторской озвучки нет: текст + звук баннера.')
    fx = sfx_layer(n, kit)
    if HAS_NARRATION:                       # SFX step back under speech
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        fx *= (1 - 0.45 * np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1))[:, None]
    mix = voice + fx
    mix = np.tanh(mix * 1.15) / 1.15
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
