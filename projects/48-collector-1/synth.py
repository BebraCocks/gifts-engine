"""Звуки, которых нет в паке Botanica V4 и в бесплатной библиотеке Fish: стук в деревянную дверь, удары
по двери, сирена за окном, сердцебиение, низкий гул, тишина комнаты. Всё стерео (n, 2), 48 кГц, детерминированно."""
import numpy as np

SR = 48000


def _rng(seed):
    return np.random.default_rng(seed)


def fftconv(x, h):
    n = len(x) + len(h) - 1
    m = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(h, m), m)[:n]


def reverb(x, dur=1.2, wet=0.3, seed=0, damp=4000):
    """Простой ревербератор: свёртка с затухающим шумом, отдельно для каждого канала."""
    r = _rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = []
    for ch in range(2):
        ir = r.standard_normal(n) * np.exp(-6.9 * t / dur)
        ir = lowpass(ir, damp)
        ir /= np.sqrt((ir ** 2).sum()) + 1e-9
        out.append(fftconv(x[:, ch] if x.ndim == 2 else x, ir))
    y = np.stack(out, 1)
    dry = x if x.ndim == 2 else np.stack([x, x], 1)
    y[:len(dry)] = y[:len(dry)] * wet + dry * (1 - wet)
    y[len(dry):] *= wet
    return y


def lowpass(x, fc):
    """Однополюсный ФНЧ дважды (мягкий спад 12 дБ/окт)."""
    a = np.exp(-2 * np.pi * fc / SR)
    for _ in range(2):
        x = _iir1(x, a)
    return x


def _iir1(x, a):
    """y[n] = (1-a) x[n] + a y[n-1], блоками через свёртку с a^k."""
    y = np.empty_like(x, dtype=np.float64)
    b = 1 - a
    prev = 0.0
    blk = 4096
    k = np.arange(blk)
    pw = a ** (k + 1)
    for s in range(0, len(x), blk):
        seg = x[s:s + blk] * b
        m = len(seg)
        # y[i] = sum_{j<=i} a^(i-j) seg[j] + a^(i+1) prev
        c = fftconv(seg, a ** np.arange(m))[:m]
        y[s:s + m] = c + pw[:m] * prev
        prev = y[s + m - 1]
    return y


def highpass(x, fc):
    return x - lowpass(x, fc)


def _st(x, pan=0.0):
    l, r = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2), np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
    return np.stack([x * min(1, l), x * min(1, r)], 1)


def knock_one(strength=1.0, seed=0):
    """Один удар костяшками по деревянной двери: резонансы полотна + щелчок."""
    r = _rng(seed)
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, d, a in ((118, 0.05, 1.0), (196, 0.04, 0.8), (262, 0.03, 0.55), (410, 0.02, 0.35), (640, 0.012, 0.2)):
        f *= r.uniform(0.97, 1.03)
        y += a * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28)) * np.exp(-t / d)
    click = highpass(r.standard_normal(n), 1500) * np.exp(-t / 0.004) * 0.5
    y = (y + click) * strength
    return y / (np.abs(y).max() + 1e-9)


def knocks(times, strength=1.0, seed=0, room=0.25):
    """Серия стуков; times — моменты ударов (с) от начала. Звук «из прихожей»."""
    n = int((max(times) + 0.6) * SR)
    y = np.zeros(n)
    for k, t0 in enumerate(times):
        s = knock_one(strength * (0.85 + 0.15 * ((k * 7) % 3) / 2), seed + k)
        i = int(t0 * SR)
        y[i:i + len(s)] += s[:n - i]
    return reverb(_st(y), dur=0.5, wet=room, seed=seed, damp=3000)


def bash_one(seed=0, strength=1.0):
    """Тяжёлый удар в дверь плечом: низкий удар, дребезг рамы и петель."""
    r = _rng(seed)
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, d, a in ((52, 0.18, 1.0), (78, 0.14, 0.8), (121, 0.09, 0.6), (187, 0.06, 0.45), (300, 0.04, 0.3)):
        f *= r.uniform(0.95, 1.05)
        y += a * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28)) * np.exp(-t / d)
    thud = lowpass(r.standard_normal(n), 900) * np.exp(-t / 0.05) * 2.0
    rattle = highpass(r.standard_normal(n), 2500) * (np.abs(np.sin(2 * np.pi * 31 * t)) ** 6) * np.exp(-t / 0.18) * 0.25
    y = (y + thud + rattle) * strength
    y = np.tanh(1.5 * y / (np.abs(y).max() + 1e-9))
    return y / (np.abs(y).max() + 1e-9)


def bash(seed=0, strength=1.0):
    return reverb(_st(bash_one(seed, strength)), dur=0.7, wet=0.22, seed=seed + 50, damp=2500)


def siren(dur=9.0, seed=0):
    """Сирена полиции за окном (вой), подъезжает: нарастает и глушится стеклом."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 750 + 450 * (0.5 - 0.5 * np.cos(2 * np.pi * t / 2.6))          # вой вверх-вниз
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(np.sin(k * ph) / k ** 1.3 for k in range(1, 7))
    env = np.clip(t / (dur * 0.55), 0, 1) ** 1.5 * np.clip((dur - t) / 1.5, 0, 1)
    y = lowpass(y * env, 2200)
    y = reverb(_st(y, -0.35), dur=1.6, wet=0.45, seed=seed, damp=2000)
    return y / (np.abs(y).max() + 1e-9)


def heartbeat(n_beats=4, bpm=92, seed=0):
    period = 60 / bpm
    n = int((n_beats * period + 0.6) * SR)
    y = np.zeros(n)
    t = np.arange(int(0.25 * SR)) / SR
    def thump(f, a):
        return a * np.sin(2 * np.pi * f * t * (1 - 0.3 * t / 0.25)) * np.exp(-t / 0.05)
    for k in range(n_beats):
        for off, f, a in ((0.0, 55, 1.0), (0.24, 48, 0.7)):
            i = int((k * period + off) * SR)
            s = thump(f, a)
            y[i:i + len(s)] += s[:n - i]
    return _st(y / (np.abs(y).max() + 1e-9))


def drone(dur, seed=0, base=41.2):
    """Низкий зловещий гул: расстроенные синусы + шум с медленной модуляцией."""
    r = _rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros((n, 2))
    for k, (m, a) in enumerate(((1, 1.0), (1.5, 0.5), (2, 0.45), (2.997, 0.25), (4.01, 0.12))):
        for ch in range(2):
            det = 1 + (0.003 if ch else -0.003) * (k + 1)
            y[:, ch] += a * np.sin(2 * np.pi * base * m * det * t + r.uniform(0, 6.28))
    noise = lowpass(r.standard_normal(n), 400) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 5.3))
    y += _st(noise * 1.2)
    y *= (0.75 + 0.25 * np.sin(2 * np.pi * t / 7.1))[:, None]
    f = min(n // 3, int(1.5 * SR))
    y[:f] *= np.linspace(0, 1, f)[:, None]
    y[-f:] *= np.linspace(1, 0, f)[:, None]
    return y / (np.abs(y).max() + 1e-9)


def roomtone(dur, seed=0):
    """Тишина ночной однушки: низкий шум и едва слышный гул холодильника."""
    r = _rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    b = lowpass(np.cumsum(r.standard_normal(n)) * 0.02, 250)
    b -= lowpass(b, 20)
    hum = 0.15 * np.sin(2 * np.pi * 50 * t) + 0.08 * np.sin(2 * np.pi * 100 * t) + 0.04 * np.sin(2 * np.pi * 150 * t)
    y = np.stack([b + hum, np.roll(b, 3000) + hum], 1)
    return y / (np.abs(y).max() + 1e-9)


def scrape(dur=1.2, seed=0):
    """Мебель тащат по полу: шум с неровным трением."""
    r = _rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    grit = np.abs(lowpass(r.standard_normal(n), 30)) * 6
    y = lowpass(r.standard_normal(n), 1200) * (0.4 + grit) - lowpass(r.standard_normal(n), 120) * 0.3
    env = np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.15, 0, 1)
    y = y * env
    return reverb(_st(y / (np.abs(y).max() + 1e-9)), dur=0.4, wet=0.2, seed=seed)
