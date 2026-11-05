"""Narration (Fish Audio drama-3, author's voice) + SFX from Botanica V4 via sfxkit + the complete RubUp sound.
No music. Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt.
Ten BAN stamps in a row: roles alternate (cartoon-hit / impact / pop) and sfxkit never repeats a variant
back to back, so the series does not sound like a machine gun."""
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
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES
from events import AD_STOP, S, E
import render as R

SR = 48000
BR = banner.Breaks([AD_STOP], cy=960, speed=1.1)


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    A = kit.add
    # hook
    A(fx, 'whoosh-short', E['bear_land'], align='end', gain_db=-16, label='the bear falls')
    A(fx, 'cartoon-hit', E['bear_land'], align='peak', gain_db=-12, label='the bear lands (squash)')
    A(fx, 'boing', E['bear_land'] + 0.05, gain_db=-19, label='bounce')
    A(fx, 'sparkle', E['price'], gain_db=-20, fit=1.0, label='price tag ⭐ 15')
    for j in range(3):
        A(fx, 'popup' if j < 2 else 'pop', E['cards'] + 0.12 * j, gain_db=-17, pan=(-0.4, 0, 0.4)[j],
          label=f'closed card №{j + 1}')
    A(fx, 'sparkle-whoosh', E['best'], gain_db=-17, label='card №3 glows: «самая лучшая»')
    # place cards
    for rank, (t0, flip) in {1: (S['p1'], E['flip1']), 2: (S['p2'], E['flip2']), 3: (S['p3'], E['flip3'])}.items():
        A(fx, 'whoosh', t0 + 0.2, align='peak', gain_db=-15, label=f'card {rank} flies to the centre')
        A(fx, 'flip', flip - 0.05, gain_db=-14, label=f'card {rank} flips')
        A(fx, 'riser-hit' if rank == 3 else 'impact', flip + 0.15, align='peak', gain_db=-14,
          label=f'«{rank} МЕСТО» revealed')
    A(fx, 'shutter', E['stamp1'] - 0.05, gain_db=-14, label='stamp «ПРОСЬБА О БЛАГОСКЛОННОСТИ»')
    A(fx, 'power-up', E['effect'] - 0.25, gain_db=-17, fit=0.8, label='chart goes up')
    A(fx, 'counter', E['meter'] - 0.1, gain_db=-19, fit=E['full'] - E['meter'], label='meter 0 → 100%')
    A(fx, 'confirm', E['full'], gain_db=-14, label='100%')
    # chats list
    A(fx, 'whoosh-short', S['chats'], align='peak', gain_db=-15, label='whip to the phone')
    rows = R.chat_rows(S['chats'] + 0.25, 0.3)
    for j, r in enumerate(rows[:7]):
        A(fx, 'select-soft' if j % 2 == 0 else 'select', r['t'], gain_db=-21, pan=0.15 * (j % 3 - 1),
          label=f'chat row: {r["name"]}')
    A(fx, 'coin', E['rich'], gain_db=-17, label='«только богатые»')
    # grind
    A(fx, 'counter', S['grind'] + 0.3, gain_db=-21, fit=E['luck'] - S['grind'] - 0.4, label='days fly by')
    A(fx, 'spinback', E['hours'] - 0.1, gain_db=-20, label='«10 ч / день»')
    A(fx, 'popup', E['luck'] - 0.2, gain_db=-13, label='notification: a gift!')
    # the bear arrives -> bans
    A(fx, 'sparkle', E['gift_in'] - 0.1, gain_db=-16, fit=1.4, label='the bear gift card')
    A(fx, 'granular-combo', E['gift_in'], gain_db=-19, label='confetti')
    A(fx, 'whoosh-short', S['banlist'], align='peak', gain_db=-16, label='back to the chats list')
    roles = ['cartoon-hit', 'impact', 'pop']
    for j in range(len(R.CHATS)):
        t = E['ban'] - 0.05 + 0.17 * j
        A(fx, roles[j % 3], t, gain_db=-13 - 0.4 * j, pan=0.3 * ((j % 2) * 2 - 1) * 0.5, label=f'BAN stamp {j + 1}')
    A(fx, 'error', E['ban'] + 1.8, gain_db=-16, label='«Вы заблокированы» everywhere')
    # street
    A(fx, 'whoosh', S['street'], align='peak', gain_db=-15, label='whip to the street')
    A(fx, 'ambience', S['street'] + 0.1, gain_db=-30, fit=S['p3'] - S['street'] - 0.4, label='street ambience')
    A(fx, 'transform', E['change'] - 0.1, gain_db=-15, label='puff: old clothes')
    A(fx, 'paper', E['sign_up'] - 0.15, gain_db=-15, label='cardboard sign')
    A(fx, 'coin', E['coin'], gain_db=-13, label='a coin in the cup')
    A(fx, 'whoosh-deep', AD_STOP - 0.2, align='peak', gain_db=-16, label='slow-down into RubUp (waiting)')
    A(fx, 'cartoon', E['friend_in'] - 0.3, gain_db=-17, label='friends slide in')
    A(fx, 'error', E['spotted'], gain_db=-14, label='«!» — spotted')
    A(fx, 'voice', E['spotted'] + 0.15, gain_db=-20, label='friends laugh')
    A(fx, 'granular-move', E['dust'] - 0.25, gain_db=-14, fit=1.1, label='friends crumble to dust')
    A(fx, 'whoosh-organic', E['dust'] + 0.2, gain_db=-20, label='tumbleweed / wind')
    # sofa + DM
    A(fx, 'whoosh', S['sofa'], align='peak', gain_db=-16, label='whip to the sofa')
    A(fx, 'cartoon-move', E['couch'] - 0.4, gain_db=-19, label='«0 шагов»')
    A(fx, 'whoosh-short', S['dm'] + 0.2, align='peak', gain_db=-16, label='phone flies in')
    A(fx, 'typing', E['type0'] - 0.5, gain_db=-17, fit=E['send'] - E['type0'] + 0.4, label='typing «дай мишеу»')
    A(fx, 'key-enter', E['send'] + 0.02, gain_db=-15, label='send')
    A(fx, 'select-soft', E['send'] + 0.08, gain_db=-17, label='message sent (one tick)')
    A(fx, 'downlifter', S['auto'] + 0.8, gain_db=-17, label='pull back to the sofa')
    A(fx, 'scan', S['auto'] + 1.3, gain_db=-21, fit=E['ask'] - S['auto'] - 1.0, label='time flies: months, beard, cobweb')
    A(fx, 'power-down', E['ask'] + 0.4, gain_db=-16, label='nothing arrives')
    # like
    A(fx, 'riser', S['like'], align='end', gain_db=-17, fit=0.6, label='into the finale')
    A(fx, 'boing', S['like'] + 0.25, gain_db=-17, label='the bear pops up')
    A(fx, 'confirm', E['like_btn'] - 0.15, gain_db=-12, label='like button')
    A(fx, 'granular-combo', E['like_btn'], gain_db=-19, label='confetti')
    A(fx, 'sparkle-whoosh', E['bear_wave'] - 0.2, gain_db=-18, label='the bear waves goodbye')
    return fx


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            e = np.sqrt(np.convolve(data[:, 0] ** 2, np.ones(2400) / 2400, 'same'))
            rms = 20 * np.log10(np.sqrt((data[e > e.max() * 0.1, 0] ** 2).mean()) + 1e-9)
            target = -16.5 if KEY['nofriends'] == k else -14.0       # «Если они у вас есть» stays dry and quiet
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
