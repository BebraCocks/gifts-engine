"""Four voices (Fish Audio drama-3) + SFX from Botanica V4 via sfxkit + the complete RubUp sound (two breaks).
Writes build/mix.wav and build/review/{sfx_only,mix}.mp3 + sfx_cues.txt.

Synthesised (not in the pack): the party music behind the scene (a plain 120 bpm kick/hat/bass loop) — the pack
has no music loop; it is muffled the moment the last message arrives. The voice of the last message gets
a short echo.
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
from script import LINES
from timeline import DUR, ON, END, KEY, HAS_NARRATION, TAKES
from events import AD1, AD2, T
import render as R

SR = 48000
BR = banner.Breaks([AD1, AD2], cy=960, speed=1.1)


def party_beat(t0, t1, muffle_at, gain_db=-17.0):
    n = int((t1 - t0) * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(3)
    beat = 0.5
    k = 0
    while k * beat / 2 < (t1 - t0):
        i = int(k * beat / 2 * SR)
        if k % 2 == 0:                                   # kick
            m = int(0.22 * SR)
            tt = np.arange(m) / SR
            f = 50 + 90 * np.exp(-tt * 30)
            y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 14)
            j = min(n, i + m)
            out[i:j] += y[:j - i]
        else:                                            # hat
            m = int(0.05 * SR)
            y = rng.normal(0, 0.25, m) * np.exp(-np.linspace(0, 8, m))
            y = sosfilt(butter(2, 7000, 'highpass', fs=SR, output='sos'), y)
            j = min(n, i + m)
            out[i:j] += y[:j - i]
        if k % 4 == 1:                                   # off-beat bass
            m = int(0.2 * SR)
            tt = np.arange(m) / SR
            y = 0.35 * np.sign(np.sin(2 * np.pi * (55 if (k // 8) % 2 else 73) * tt)) * np.exp(-tt * 9)
            y = sosfilt(butter(2, 400, 'lowpass', fs=SR, output='sos'), y)
            j = min(n, i + m)
            out[i:j] += y[:j - i]
        k += 1
    out /= np.abs(out).max() + 1e-9
    m0 = int((muffle_at - t0) * SR)
    if 0 < m0 < n:                                       # the last message: party goes «behind a wall»
        low = sosfilt(butter(2, 220, 'lowpass', fs=SR, output='sos'), out)
        x = np.linspace(0, 1, n - m0)
        out[m0:] = low[m0:] * 1.4 * np.clip(1 - x * 1.4, 0, 1)
    out[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    st = np.stack([out, out], 1) * 10 ** (gain_db / 20)
    return st


def chat_sfx(fx, kit, chat, t_from, t_to, name):
    A = kit.add
    for e in chat['events']:
        if not (t_from <= e['t'] < t_to):
            continue
        if e['k'] == 'msg':
            if e['side'] == 'in':
                A(fx, 'select-soft', e['t'], gain_db=-15, pan=-0.2, label=f'{name}: incoming message')
            else:
                A(fx, 'click', e['t'] - 0.02, gain_db=-16, pan=0.2, label=f'{name}: message sent')
        elif e['k'] == 'draft':
            A(fx, 'typing', e['t'], gain_db=-21, fit=max(0.4, e['t1'] - e['t']), label=f'{name}: typing')
        elif e['k'] == 'gift':
            A(fx, 'sparkle-whoosh', e['t'], align='peak', gain_db=-14, label=f'{name}: gift {e["name"]} arrives')
            A(fx, 'coin', e['t'] + 0.1, gain_db=-19, label=f'{name}: gift {e["name"]} lands')
        elif e['k'] == 'blocked':
            A(fx, 'error', e['t'], gain_db=-14, label=f'{name}: user blocked')


def sfx_layer(n, kit):
    fx = np.zeros((n, 2))
    A = kit.add
    # ---- hook
    A(fx, 'glitch', 0.0, gain_db=-16, label='open on the phone')
    A(fx, 'popup', T['hook_msg'], gain_db=-12, label='hook: the last message arrives')
    A(fx, 'bed', 0.0, gain_db=-24, fit=T['room'], fade_out=0.6, tags=('dark',), label='hook: dark bed')
    A(fx, 'sub-drop', T['shock'], gain_db=-10, label='cut to Petya in shock')
    A(fx, 'voice', T['shock'] + 0.15, gain_db=-14, file='scared.flac', label='Petya gasps')
    A(fx, 'spinback', T['rewind'], gain_db=-12, label='rewind «несколько месяцев назад»')
    A(fx, 'whoosh', T['room'], align='peak', gain_db=-15, label='flash into the room')
    # ---- room → boss chat
    A(fx, 'pop', T['room'] + 0.25, gain_db=-21, label='chip «Петя, 16»')
    A(fx, 'voice', T['room'] + 0.4, gain_db=-18, file='tired.flac', label='Petya sighs')
    A(fx, 'popup', T['buzz'], gain_db=-13, label='notification from «Друг»')
    A(fx, 'whoosh-deep', T['fly1'], align='end', gain_db=-14, fit=1.1, label='camera flies into the phone')
    chat_sfx(fx, kit, R.CHAT_BOSS, T['fly1'], T['dima'], 'boss')
    # ---- Dima
    A(fx, 'sparkle-whoosh', T['dima'] + 0.25, align='peak', gain_db=-14, label='Dima + the NFT calendar')
    A(fx, 'pop', T['dima'] + 0.15, gain_db=-21, label='chip «Дима, 13»')
    A(fx, 'whoosh-short', T['to_dima_chat'], align='peak', gain_db=-14, label='whip to the chat')
    chat_sfx(fx, kit, R.CHAT_DIMA, T['to_dima_chat'], T['dima_cry'], 'dima')
    A(fx, 'cartoon-hit', T['dima_cry'], gain_db=-14, label='«ЗАБЛОКИРОВАН»')
    A(fx, 'voice', T['dima_cry'] + 0.05, gain_db=-16, file='upset.flac', label='Dima is upset')
    A(fx, 'whoosh-short', T['simple'], align='peak', gain_db=-18, label='back to Petya')
    # ---- sleep → RubUp 1
    A(fx, 'whoosh-organic', T['sleep'], align='peak', gain_db=-18, label='to the bedroom')
    A(fx, 'ambience', T['sleep'], gain_db=-28, fit=AD1 - T['sleep'] + 0.3, fade_out=0.5,
      file='ambience-nature-night', label='night outside')
    A(fx, 'whoosh-deep', AD1, align='peak', gain_db=-16, label='slow-down to RubUp 1')
    # ---- months: loot tunnel
    A(fx, 'sparkle-whoosh', T['tunnel'] + 0.1, gain_db=-14, label='into the loot tunnel')
    A(fx, 'counter', T['tunnel'] + 0.3, gain_db=-21, fit=1.1, label='loot counter')
    A(fx, 'riser', T['katya'], align='end', gain_db=-16, fit=1.4, label='tunnel builds to Katya')
    A(fx, 'impact', T['katya'], align='peak', gain_db=-14, label='flash: Katya')
    A(fx, 'pop', T['katya'] + 0.2, gain_db=-21, label='chip «Катя, 23»')
    A(fx, 'boing', END[KEY['katya']] - 1.8, gain_db=-18, label='«NFT?»')
    # ---- search → found → profile
    A(fx, 'whoosh-short', T['search'], align='peak', gain_db=-16, label='cut to the night search')
    A(fx, 'bed', T['search'], gain_db=-26, fit=T['found'] - T['search'], fade_out=0.3, tags=('dark',),
      label='search: tension bed')
    A(fx, 'list', T['search'] + 0.2, gain_db=-22, fit=2.4, label='tabs flying past')
    A(fx, 'riser-hit', T['found'], align='peak', gain_db=-12, label='«Вот оно!»')
    A(fx, 'whoosh-deep', T['profile'], align='end', gain_db=-15, fit=1.1, label='fly into the dating profile')
    for k in range(4):
        A(fx, 'scan', T['profile'] + 1.2 + 0.55 * k, gain_db=-21, fit=0.4, label=f'marker over wish {k + 1}')
    # ---- AI builds Alexander
    A(fx, 'glitch-text', T['ai'], gain_db=-14, label='AI: generation starts')
    A(fx, 'power-up', T['ai'] + 0.3, gain_db=-17, label='hologram powers up')
    A(fx, 'scan', T['ai'] + 0.5, gain_db=-20, fit=1.6, label='scan line reveals the face')
    A(fx, 'riser-hit', T['alex_name'], align='peak', gain_db=-12, label='«АЛЕКСАНДР, 28»')
    for k, th in enumerate((0.2, 0.4, 0.6, 0.8)):
        A(fx, 'confirm', T['ai'] + (th + 0.12) * (T['chat_k'] - T['ai']), gain_db=-22,
          label=f'panel {k + 1} ready')
    A(fx, 'whoosh-deep', T['chat_k'], align='end', gain_db=-15, fit=1.1, label='fly into the chat with Katya')
    # ---- Katya chat (whole conversation)
    chat_sfx(fx, kit, R.CHAT_K, T['chat_k'], T['party'], 'katya')
    A(fx, 'sparkle', T['katya_love'] + 0.1, gain_db=-22, fit=1.4, label='Katya in love: hearts')
    A(fx, 'whoosh-short', T['cancel'], align='peak', gain_db=-17, label='cut to Petya, fake sad')
    A(fx, 'whoosh-deep', T['fly_cancel'], align='end', gain_db=-16, fit=1.1, label='fly into the phone')
    A(fx, 'whoosh-short', T['katya_worried'], align='peak', gain_db=-16, label='whip to worried Katya')
    A(fx, 'whoosh-short', T['lie'], align='peak', gain_db=-16, label='whip back to the chat')
    A(fx, 'cartoon-move', T['genius'] + 0.1, gain_db=-17, label='sly grin «какой же я гений»')
    A(fx, 'whoosh-short', T['help'], align='peak', gain_db=-17, label='back to the chat')
    for k, g in enumerate(T['gifts']):
        A(fx, 'impact', g + 0.05, gain_db=-17 - k, label=f'gift {k + 1} bursts out of the phone')
    A(fx, 'whoosh-short', T['katya_sad'], align='peak', gain_db=-18, label='cut to Katya')
    A(fx, 'riser', AD2, align='end', gain_db=-17, fit=2.5, label='his smile spreads')
    A(fx, 'whoosh-deep', AD2, align='peak', gain_db=-16, label='slow-down to RubUp 2')
    # ---- after RubUp 2: transfer, mockery, waiting
    A(fx, 'popup', T['transfer'] + 0.05, gain_db=-16, label='sheet «Передать подарки»')
    A(fx, 'select', T['transfer_done'] - 0.35, gain_db=-15, label='press «Передать»')
    A(fx, 'confirm', T['transfer_done'], gain_db=-14, label='«Подарки переданы»')
    A(fx, 'bed', T['mock_sent'], gain_db=-24, fit=T['party'] - T['mock_sent'], fade_out=0.4, tags=('dark',),
      label='waiting: tension bed')
    A(fx, 'pop', T['five'], gain_db=-17, label='«+5 минут»')
    A(fx, 'pop', T['ten'], gain_db=-16, label='«+10 минут»')
    A(fx, 'whoosh-short', T['uneasy'], align='peak', gain_db=-18, label='cut to uneasy Petya')
    # ---- party
    A(fx, 'whoosh', T['party'], align='peak', gain_db=-14, label='cut to the party')
    A(fx, 'granular-combo', T['party'] + 0.1, gain_db=-18, label='confetti')
    A(fx, 'voice', T['party'] + 0.6, gain_db=-16, file='public.flac', label='friends cheer')
    A(fx, 'popup', T['buzz2'], gain_db=-12, label='one message on the main account')
    A(fx, 'whoosh-deep', T['fly_final'], align='end', gain_db=-14, fit=1.1, label='fly into the phone')
    beat = party_beat(T['party'], T['shock2'], T['final_msg'])
    i0 = int(T['party'] * SR)
    fx[i0:i0 + len(beat)] += beat[:max(0, min(len(beat), n - i0))]
    kit.cues.append(dict(t=round(T['party'], 3), at=round(T['party'], 3), align='start', gain_db=-17, pan=0,
                         label='party music (synthesised), muffled at the last message', id='synth:party',
                         role='synth', dur=len(beat) / SR))
    # ---- the last message
    A(fx, 'sub-drop', T['final_msg'], gain_db=-8, label='«Зря ты это сделал, Петя.»')
    A(fx, 'downlifter', T['final_msg'] + 0.2, gain_db=-15, label='lights die')
    A(fx, 'bed', T['final_msg'], gain_db=-21, fit=DUR - T['final_msg'], fade_out=1.0, tags=('dark',),
      label='ending: dark bed')
    for k in range(3):
        A(fx, 'impact', T['shock2'] + 0.55 * k, gain_db=-16 - 2 * k, label=f'heartbeat {k + 1}')
    A(fx, 'glitch', T['endcard'], gain_db=-15, label='end card')
    A(fx, 'riser-hit', T['endcard'] + 0.3, align='peak', gain_db=-13, label='«МОГЛИ ВЫЧИСЛИТЬ?»')
    A(fx, 'pop', T['endcard'] + 1.0, gain_db=-17, label='«ЧАСТЬ 2 — СКОРО»')
    return fx


def echo(x, delay=0.17, g=0.32, n=3):
    out = x.copy()
    for k in range(1, n + 1):
        d = int(delay * k * SR)
        out[d:] += x[:-d] * g ** k
    return out


def make_mix(kit):
    n = int(round(DUR * SR))
    voice = np.zeros((n, 2), np.float64)
    if HAS_NARRATION:
        for k, take in enumerate(TAKES):
            data = sound.load_stereo(take, SR)
            e = np.sqrt(np.convolve(data[:, 0] ** 2, np.ones(2400) / 2400, 'same'))
            rms = 20 * np.log10(np.sqrt((data[e > e.max() * 0.1, 0] ** 2).mean()) + 1e-9)
            who, key = LINES[k][0], LINES[k][2]
            target = -16.0 if key in ('genius',) else -13.0 if key == 'threat' else -14.0
            data = data * 10 ** (np.clip(target - rms, -6, 12) / 20)
            if who == 'X':
                data = np.concatenate([data, np.zeros((int(0.8 * SR), 2))])
                data = echo(data)
            start = round(ON[k] * SR)
            count = min(len(data), n - start)
            voice[start:start + count] += data[:count]
    else:
        print('Озвучки нет: только SFX и звук баннера.')
    fx = sfx_layer(n, kit)
    if HAS_NARRATION:
        env = np.abs(voice).max(1)
        env = np.convolve(env, np.ones(2400) / 2400, 'same')
        fx *= (1 - 0.5 * np.clip(env / (np.percentile(env, 95) * 0.5 + 1e-9), 0, 1))[:, None]
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
