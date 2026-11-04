"""Mix: Drama 3 narration + procedural SFX (content time) -> RubUp breaks -> music beds (output time,
ducked under the voice and under the banner) -> limiter. Writes build/mix.wav.

Music: put the author's tracks into input/music/ and list them in MUSIC below
(file name, output start s, output end s, gain dB, offset into the file s)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import wave

import numpy as np
from scipy.signal import butter, sosfilt

import banner
import sound
import sfx
from events import AD_STOPS
from timeline import DUR, FILE_ON, HAS_NARRATION, TAKES

SR = 48000
BR = banner.Breaks(AD_STOPS, cy=960)
MUSIC_DIR = paths.INPUT / 'music'
# (file, out_start, out_end, gain_db, file_offset) — filled in when the author's tracks arrive
MUSIC = []
VOICE_DB = -17.0          # target RMS of speech
SFX_GAIN = 0.6


def _rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def voice_layer(n):
    v = np.zeros((n, 2))
    if not HAS_NARRATION:
        print('Дикторской озвучки нет: текст + звук баннера.')
        return v
    for k, take in enumerate(TAKES):
        x = sound.load_stereo(take, SR)
        speech = x[np.abs(x).max(1) > 0.01]
        x = x * 10 ** ((VOICE_DB - _rms_db(speech)) / 20)
        a = int(round(FILE_ON[k] * SR))
        m = min(len(x), n - a)
        v[a:a + m] += x[:m]
    # gentle presence + de-mud
    sos = butter(2, 120, 'highpass', fs=SR, output='sos')
    return sosfilt(sos, v, axis=0)


def sfx_layer(n):
    s = np.zeros((n, 2))
    for at, x, g in sfx.cue_list():
        a = int(round(at * SR))
        if a < 0:
            x, a = x[-a:], 0
        m = min(len(x), n - a)
        if m > 0:
            s[a:a + m] += x[:m] * g
    return s * SFX_GAIN


def envelope(x, win=0.25):
    e = np.abs(x).max(1)
    k = int(win * SR)
    c = np.convolve(e, np.ones(k) / k, mode='same')
    return c


def music_layer(n, voice_out):
    mus = np.zeros((n, 2))
    fallback = HERE / 'build' / 'music_fallback.wav'
    if not MUSIC:
        if not fallback.exists():
            print('Музыка не подключена: ждём треки автора в input/music/.')
            return mus
        print('Музыка: временная синтезированная партитура (music_gen.py), пока нет треков автора.')
        x = sound.load_stereo(fallback, SR)
        m = min(n, len(x))
        mus[:m] = x[:m] * 10 ** (-17 / 20)
    for name, a, b, gdb, off in MUSIC:
        x = sound.load_stereo(MUSIC_DIR / name, SR, start=off, dur=b - a + 2.0)
        i0, i1 = int(a * SR), min(n, int(b * SR))
        seg = x[:i1 - i0]
        fade_in, fade_out = int(0.4 * SR), int(1.2 * SR)
        env = np.ones(len(seg))
        env[:fade_in] = np.linspace(0, 1, min(fade_in, len(seg)))[:len(env[:fade_in])]
        env[-fade_out:] = np.linspace(1, 0, min(fade_out, len(seg)))
        mus[i0:i0 + len(seg)] += seg * env[:, None] * 10 ** (gdb / 20)
    # duck under speech (-7 dB) and under the banner (BR.duck)
    ve = envelope(voice_out)
    duck = 1 - 0.55 * np.clip(ve / (ve.max() * 0.25 + 1e-9), 0, 1)
    mus *= duck[:, None]
    mus *= BR.duck(n, SR, floor_db=-30)[:, None]
    return mus


def make_mix():
    n = int(round(DUR * SR))
    voice = voice_layer(n)
    fx = sfx_layer(n)
    ve = envelope(voice, 0.15)
    fx *= (1 - 0.6 * np.clip(ve / (np.percentile(ve, 95) * 0.5 + 1e-9), 0, 1))[:, None]   # SFX step back under speech
    content = voice + fx
    out = BR.audio(content, SR)                       # content pauses + full banner sound
    vo = BR.audio(voice, SR)
    out = out + music_layer(len(out), vo)
    peak = np.abs(out).max()
    if peak > 0.95:
        out = np.tanh(out / peak * 1.1) * 0.95 / np.tanh(1.1)
    return out


if __name__ == '__main__':
    data = make_mix()
    output = paths.build(HERE) / 'mix.wav'
    with wave.open(str(output), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -0.98, 0.98) * 32767).astype('<i2').tobytes())
    print('build/mix.wav готов', round(len(data) / SR, 2), 's')
