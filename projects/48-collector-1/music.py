"""Музыкальная подложка (Kevin MacLeod, CC BY 4.0 — input/music/SOURCE.md) во времени содержания.
Сегменты: (трек, начало в ролике, конец, смещение в треке, уровень дБ, атака, спад)."""
from pathlib import Path
import numpy as np
import sound
from timeline import ON, END, DUR

HERE = Path(__file__).resolve().parent
M = HERE / 'input' / 'music'


def segments():
    return [
        ('Unseen_Horrors.mp3', 0.0, ON[20] + 0.4, 0.0, -1.0, 1.2, 1.4),       # ночь, чат, «мама»
        ('Anxiety.mp3', ON[20] - 0.2, END[23] + 0.32, 0.0, -6.0, 1.0, 0.05),  # монстр, выбивание; обрыв на последнем ударе
        ('Unseen_Horrors.mp3', ON[25], ON[28] - 0.2, 120.0, -3.0, 2.5, 1.0),  # после сирен — тихо
        ('Dark_Hallway.mp3', ON[28] - 0.4, DUR, 0.0, 0.0, 0.6, 2.0),          # «полиция» и опрос
    ]


def music(n, sr=48000):
    out = np.zeros((n, 2))
    for name, t0, t1, off, db, a, r in segments():
        x = sound.load_stereo(M / name, sr, start=off, dur=t1 - t0 + 0.1)
        x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 10 ** (-24 / 20)      # к общему уровню −24 dBFS RMS
        m = min(len(x), int((t1 - t0) * sr), n - int(t0 * sr))
        x = x[:m] * 10 ** (db / 20)
        env = np.ones(m)
        ka, kr = min(m, int(a * sr)), min(m, int(r * sr))
        env[:ka] = np.linspace(0, 1, ka) ** 1.5
        if kr:
            env[-kr:] *= np.linspace(1, 0, kr)
        i0 = int(t0 * sr)
        out[i0:i0 + m] += x * env[:, None]
    return out
