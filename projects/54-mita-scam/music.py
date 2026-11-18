"""Музыка: «Dreams of Love and Literature» (Dan Salvato, DDLC OST) — выбор автора 2026-11-18. Под речью приглушается.
Трек идёт с начала во времени содержания (OFFSET — смещение в треке). Под речью приглушается; на «Все. До одного»
замедляется и стихает (жутковатый финал). beats_in_content() — сильные доли для монтажа «под бит»."""
import functools
import subprocess
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
TRACK = HERE / 'input' / 'music' / 'dreams_of_love.mp3'
OFFSET = 0.0          # трек с начала
LEVEL_DB = -28.3       # 51: как в 50 по громкости (−24,9 LUFS; Natsuki ярче Yuri на 0,8 дБ)
DUCK_DB = -7.0         # дополнительное приглушение под речью


def _decode(sr, ch=2, start=0.0, dur=None):
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{start:.3f}', '-i', str(TRACK)]
    if dur:
        cmd += ['-t', f'{dur:.3f}']
    cmd += ['-ac', str(ch), '-ar', str(sr), '-f', 's16le', '-']
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, '<i2').astype(np.float64) / 32768
    return x.reshape(-1, ch)


@functools.lru_cache(None)
def track_onsets():
    """Сильные атаки пианино (с) в треке: спектральный поток, локальные максимумы, порог по перцентилю."""
    sr, hop = 22050, 256
    x = _decode(sr, 1)[:, 0]
    n = len(x) // hop - 4
    fr = np.lib.stride_tricks.sliding_window_view(x, 1024)[::hop][:n]
    S = np.log1p(100 * np.abs(np.fft.rfft(fr * np.hanning(1024), axis=1)))
    flux = np.maximum(0, np.diff(S, axis=0)).sum(1)
    flux = (flux - np.convolve(flux, np.ones(43) / 43, 'same')).clip(0)
    fps = sr / hop
    thr = np.percentile(flux, 93)
    peaks, last = [], -1.0
    for i in range(1, len(flux) - 1):
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            t = i / fps
            if t - last >= 0.32:
                peaks.append(t)
                last = t
    return np.array(peaks)


def beats_in_content():
    return track_onsets() - OFFSET


def music(n, voice_env, slow_from=None, sr=48000):
    """Стерео подложка длиной n. voice_env — огибающая речи 0..1 (для приглушения). slow_from — с этого времени
    содержания трек замедляется (до 0,8×) и затихает за ~2,5 с."""
    x = _decode(sr, 2, OFFSET, n / sr + 2)
    rms = np.sqrt(np.mean(x[:sr * 40] ** 2)) + 1e-9
    x = x / rms * 10 ** (LEVEL_DB / 20)
    out = np.zeros((n, 2))
    if slow_from is not None:
        k = int(slow_from * sr)
        head = x[:k]
        tail_src = x[k:k + int(4 * sr)]
        # плавное замедление: позиция в исходнике растёт всё медленнее (скорость 1 → 0,8), тон ниже — жутковато
        m = n - k
        tt = np.arange(m) / sr
        speed = 1 - 0.2 * np.clip(tt / 1.5, 0, 1)
        pos = np.cumsum(speed) - speed[0]
        pos = np.clip(pos, 0, len(tail_src) - 2)
        tail = np.stack([np.interp(pos, np.arange(len(tail_src)), tail_src[:, c]) for c in range(2)], 1)
        tail *= np.clip(1 - tt / 2.6, 0, 1)[:, None] ** 1.3
        y = np.concatenate([head, tail])[:n]
    else:
        y = x[:n]
    out[:len(y)] = y
    fade = int(0.6 * sr)
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    tail = min(n, int(1.4 * sr))                    # мягкое затухание в конце ролика
    out[-tail:] *= np.linspace(1, 0, tail)[:, None] ** 1.5
    duck = 10 ** (DUCK_DB * np.clip(voice_env, 0, 1) / 20)
    return out * duck[:, None]
