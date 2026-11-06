"""Music for 15-price-duel-7 (09-price-duel code, ля мажор A – F♯m – D – E), synthesized in code
A light quiz-show groove, 120 BPM (the timer needs 2 beats a second), G – Em – C – D (09: Am – F – C – G, 10: D – Bm – G – A, 11: Em – C – G – D). Content time, so RubUp pauses it like the voice.

Sections follow the events:
- hook (0 … first round): kick, clap, bass, marimba arpeggio — the bet;
- timer (TIMER0 … REVEAL, 5 s = 10 beats): the grid restarts exactly at TIMER0, so every second of the timer
  is a beat: kick + ticking hat, a muted bass pulse and one marimba note climbing every second (tension);
- reveal: a chord stab and a noise splash, then the full groove under the answer;
- swap between rounds: the groove thins out; outro: full groove, a last chord at the end.
Writes nothing by itself: audio.py calls music(n, sr)."""
import math
import numpy as np
from scipy.signal import butter, sosfilt
from timeline import DUR, ROUND_IN, TIMER0, REVEAL, OUTRO
from events import E

BPM = 120.0
BEAT = 60.0 / BPM
RNG = np.random.default_rng(9)
PROG = [(57, (57, 61, 64)), (54, (54, 57, 61)), (62, (62, 66, 69)), (64, (64, 68, 71))]   # ля мажор A – F♯m – D – E (root, chord)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, sr):
    return sosfilt(butter(2, f, 'lowpass', fs=sr, output='sos'), x)


def hp(x, f, sr):
    return sosfilt(butter(2, f, 'highpass', fs=sr, output='sos'), x)


class Buf:
    def __init__(self, n, sr):
        self.sr, self.x = sr, np.zeros((n, 2))

    def add(self, t, y, gain=1.0, pan=0.0):
        a = int(round(t * self.sr))
        if a >= len(self.x) or a + len(y) <= 0:
            return
        if a < 0:
            y, a = y[-a:], 0
        y = y[:len(self.x) - a]
        self.x[a:a + len(y), 0] += y * gain * math.cos((pan + 1) * math.pi / 4) * 1.414
        self.x[a:a + len(y), 1] += y * gain * math.sin((pan + 1) * math.pi / 4) * 1.414


def kick(sr):
    t = np.arange(int(0.32 * sr)) / sr
    f = 45 + 95 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 9) * (1 - np.exp(-t * 900))


def clap(sr):
    n = int(0.22 * sr)
    t = np.arange(n) / sr
    env = sum(np.exp(-np.clip(t - d, 0, None) * 60) * (t >= d) for d in (0, 0.011, 0.022)) / 2 + np.exp(-t * 18) * 0.5
    return lp(hp(RNG.standard_normal(n), 900, sr), 5200, sr) * env


def hat(sr, open_=False):
    n = int((0.18 if open_ else 0.05) * sr)
    t = np.arange(n) / sr
    return hp(RNG.standard_normal(n), 7000, sr) * np.exp(-t * (16 if open_ else 70))


def marimba(m, sr, dur=0.45):
    t = np.arange(int(dur * sr)) / sr
    f = hz(m)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 7) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 30)
    return y * (1 - np.exp(-t * 2000))


def bass(m, sr, dur):
    t = np.arange(int(dur * sr)) / sr
    f = hz(m - 24)
    y = np.tanh(2.2 * np.sin(2 * np.pi * f * t)) + 0.3 * np.sin(4 * np.pi * f * t)
    return lp(y, 520, sr) * np.exp(-t * 4.5) * (1 - np.exp(-t * 600))


def stab(chord, sr):
    t = np.arange(int(0.9 * sr)) / sr
    y = sum(np.sign(np.sin(2 * np.pi * hz(m + 12) * t)) * 0.25 + np.sin(2 * np.pi * hz(m) * t) for m in chord)
    return lp(y / len(chord), 2600, sr) * np.exp(-t * 4.0) * (1 - np.exp(-t * 900))


def splash(sr):
    n = int(1.1 * sr)
    t = np.arange(n) / sr
    return hp(RNG.standard_normal(n), 3000, sr) * np.exp(-t * 4.2) * 0.6


def groove(b, t0, t1, sr, level=1.0, arp=True, start_bar=0):
    """Full groove from t0 to t1 on a grid anchored at t0."""
    k = kick(sr)
    cp = clap(sr)
    nb = int((t1 - t0) / BEAT) + 1
    for i in range(nb):
        t = t0 + i * BEAT
        if t >= t1:
            break
        bar = (start_bar + i // 4) % 4
        root, chord = PROG[bar]
        b.add(t, k, 0.9 * level)
        if i % 2 == 1:
            b.add(t, cp, 0.32 * level, 0.1)
        for h in (0, 0.5):
            b.add(t + h * BEAT, hat(sr, open_=(h == 0.5 and i % 4 == 3)), 0.12 * level, 0.35)
        b.add(t, bass(root, sr, BEAT * 0.9), 0.55 * level)
        b.add(t + 0.5 * BEAT, bass(root + (12 if i % 2 else 0), sr, BEAT * 0.45), 0.35 * level)
        if arp:
            for s in range(4):
                note = chord[(i * 4 + s) % 3] + 12 * ((i * 4 + s) // 3 % 2)
                b.add(t + s * BEAT / 4, marimba(note, sr), 0.16 * level, -0.3 + 0.2 * s)


def timer_section(b, t0, sr, r):
    """10 beats: one second = two beats. The marimba note climbs every second; hat ticks; last second louder."""
    k = kick(sr)
    for i in range(10):
        t = t0 + i * BEAT
        sec = i // 2
        lvl = 0.55 + 0.12 * sec
        if i % 2 == 0:
            b.add(t, k, 0.75 * lvl)
            b.add(t, marimba(81 + [0, 2, 4, 5, 7][sec], sr, 0.35), 0.22 * lvl, 0.15)
        b.add(t, bass(57, sr, BEAT * 0.5), 0.35 * lvl)
        for q in range(2 if sec < 4 else 4):
            b.add(t + q * BEAT / (2 if sec < 4 else 4), hat(sr), 0.10 * lvl, -0.3)


def music(n, sr=48000):
    b = Buf(n, sr)
    # hook: the groove from the first frame
    groove(b, 0.0, ROUND_IN[0] + 0.3, sr, 1.0)
    for r in range(5):
        timer_section(b, TIMER0[r], sr, r)
        root, chord = PROG[r % 4]
        b.add(REVEAL[r], stab(chord, sr), 0.55)
        b.add(REVEAL[r], kick(sr), 1.0)
        b.add(REVEAL[r], splash(sr), 0.5)
        end = ROUND_IN[r + 1] + 0.3 if r < 4 else OUTRO
        groove(b, REVEAL[r] + BEAT, end, sr, 0.75, arp=True, start_bar=r)
    groove(b, OUTRO, DUR - 1.2, sr, 0.9, start_bar=1)
    b.add(DUR - 1.2, stab(PROG[0][1], sr), 0.6)
    b.add(DUR - 1.2, kick(sr), 0.9)
    b.add(DUR - 1.2, splash(sr), 0.4)
    x = b.x
    x /= max(1e-9, np.abs(x).max())
    fade = np.ones(n)
    m = int(0.6 * sr)
    fade[-m:] = np.linspace(1, 0, m)
    return x * fade[:, None]


if __name__ == '__main__':
    import wave
    from pathlib import Path
    sr = 48000
    y = music(int(DUR * sr), sr)
    Path('build').mkdir(exist_ok=True)
    with wave.open('build/music.wav', 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(y * 0.8, -1, 1) * 32767).astype('<i2').tobytes())
    print('build/music.wav')
