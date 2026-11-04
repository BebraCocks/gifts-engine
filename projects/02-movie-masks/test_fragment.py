"""Проба 10 с: 3D-проход (build/scene) + подписи по одному слову + синтезированные SFX.
Не полная сборка: без рекламы, без диктора. Итог: renders/02-movie-masks/test_fragment_vN.mp4."""
import functools
import subprocess
import sys
import wave
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import signal
import fx
import layout

W, H, FPS, DUR = 1080, 1920, 60, 10.0
SR = 48000
YELLOW, CYAN, GREEN, WHITE, RED = (255, 225, 77), (92, 225, 255), (124, 255, 107), (255, 255, 255), (255, 52, 52)
PALETTE = [WHITE, YELLOW, CYAN, WHITE, GREEN]

# (слово, начало) — оценочное время чтения, диктора нет
HOOK = [('ЧТОБЫ', 0.30), ('СТАТЬ', 0.62), ('КЕМ-ТО', 0.94), ('ДРУГИМ,', 1.30), ('ХВАТИТ', 1.80), ('ОДНОЙ', 2.18), ('МАСКИ', 2.56)]
GHOST = [('ЭТУ', 6.00), ('МАСКУ', 6.32), ('НЕ', 6.66), ('РИСОВАЛИ', 6.92), ('ДЛЯ', 7.40), ('ФИЛЬМА.', 7.68),
         ('ЕЁ', 8.24), ('НАШЛИ', 8.52), ('В', 8.88), ('ЧУЖОМ', 9.04), ('ДОМЕ', 9.42)]
WORDS = []
for seq, end in ((HOOK, 3.12), (GHOST, 10.2)):
    for k, (w, t0) in enumerate(seq):
        t1 = seq[k + 1][1] - 0.02 if k + 1 < len(seq) else end
        WORDS.append((w, t0, t1, PALETTE[(k + (seq is GHOST)) % len(PALETTE)], 96))
WORDS.append(('МАНЬЯК', 3.22, 4.36, RED, 168))


@functools.lru_cache(None)
def word_sprite(text, size, color, stroke):
    """Готовый спрайт слова: обводка + мягкая тень; размер шрифта не меняется во времени."""
    f = fx.font('Heavy', size)
    l, t, r, b = layout.ink(text, size, 'Heavy')
    pad = stroke + 24
    w, h = int(r - l) + 2 * pad, int(b - t) + 2 * pad
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    org = (pad - l, pad - t)
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((org[0], org[1] + 6), text, font=f, anchor='ls', fill=(0, 0, 0, 150), stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(im).text(org, text, font=f, anchor='ls', fill=color + (255,), stroke_width=stroke, stroke_fill=(8, 8, 12, 255))
    return im


def place(canvas, spr, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0.002:
        return
    if abs(scale - 1) > 0.002:
        spr = spr.resize((max(1, round(spr.width * scale)), max(1, round(spr.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        spr = spr.copy(); spr.putalpha(spr.getchannel('A').point(lambda v: int(v * alpha)))
    canvas.alpha_composite(spr, (int(round(cx - spr.width / 2)), int(round(cy - spr.height / 2))))


def vignette():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.42 * np.clip(d - 0.45, 0, 1) ** 1.6)[..., None].astype(np.float32)


VIG = vignette()


def render_at(t):
    i = min(int(round(t * FPS)), int(DUR * FPS) - 1)
    base = np.asarray(Image.open(HERE / 'build' / 'scene' / f'f{i:05d}.png').convert('RGB'), np.float32) * VIG
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
    for w, t0, t1, col, size in WORDS:
        if t0 - 0.02 <= t < t1:
            k = (t - t0) / 0.14
            s = 0.72 + 0.28 * fx.ease_out_back(fx.clamp01(k), 2.2) if k < 1 else 1.0
            a = fx.clamp01((t - t0 + 0.02) / 0.06) * (1 - fx.clamp01((t - t1 + 0.06) / 0.06))
            cy = 1300 if size < 120 else 1330
            place(im, word_sprite(w, size, col, 9 if size < 120 else 12), 540, cy, s, a)
    # титр блока
    k = fx.clamp01((t - 5.85) / 0.45)
    if k > 0:
        e = fx.ease_out(k)
        place(im, word_sprite('МАСКА 1 ИЗ 5', 42, YELLOW, 6), 540, 236 - 20 * (1 - e), 1, e)
        place(im, word_sprite('КРИК · 1996', 104, WHITE, 10), 540, 330 - 34 * (1 - e), 1, e)
    k = fx.clamp01((t - 6.5) / 0.35)
    if k > 0:
        pill = fx.solid_pill('Myth Mask · Ghostface · 1,1%', (18, 18, 24), 34)
        place(im, pill, 540, 1560 + 24 * (1 - fx.ease_out(k)), 1, fx.ease_out(k) * 0.92)
    return np.asarray(im.convert('RGB'))


# ---------------- звук: синтез, без внешних файлов ----------------
def env(n, a, d):
    e = np.ones(n); ka = int(a * SR); kd = int(d * SR)
    if ka: e[:ka] = np.linspace(0, 1, ka)
    if kd: e[-kd:] *= np.linspace(1, 0, kd)
    return e


def sweep_noise(rng, dur, f0, f1, q=1.2):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); blk = 960
    for s in range(0, n, blk):
        u = s / n; fc = f0 * (f1 / f0) ** u if f1 > 0 else f0
        sos = signal.butter(2, [fc / (1 + 1 / q) / (SR / 2), min(0.99, fc * (1 + 1 / q) / (SR / 2))], 'band', output='sos')
        out[s:s + blk] = signal.sosfilt(sos, x[max(0, s - 2000):s + blk])[-len(x[s:s + blk]):]
    return out / (np.abs(out).max() + 1e-9)


def make_audio():
    rng = np.random.default_rng(1103)
    n = int(DUR * SR); L = np.zeros(n); Rr = np.zeros(n)

    def put(x, t, gl, gr=None):
        s = int(t * SR); m = min(len(x), n - s)
        L[s:s + m] += x[:m] * gl; Rr[s:s + m] += x[:m] * (gl if gr is None else gr)
    # тон гримёрки
    room = signal.sosfilt(signal.butter(2, 180 / (SR / 2), output='sos'), rng.standard_normal(int(5.2 * SR)))
    put(room / np.abs(room).max() * env(len(room), 0.4, 0.6), 0.0, 0.05)
    # нарастание к посадке маски
    rise = sweep_noise(rng, 1.25, 250, 3200) * np.linspace(0, 1, int(1.25 * SR)) ** 2.4
    put(rise, 1.97, 0.22)
    # удар
    tt = np.arange(int(1.4 * SR)) / SR
    thump = np.sin(2 * np.pi * np.cumsum(45 + 45 * np.exp(-tt * 9)) / SR) * np.exp(-tt * 3.2)
    click = signal.sosfilt(signal.butter(2, 2500 / (SR / 2), output='sos'), rng.standard_normal(len(tt))) * np.exp(-tt * 40)
    tail = np.convolve(click, rng.standard_normal(int(0.9 * SR)) * np.exp(-np.arange(int(0.9 * SR)) / SR * 5), 'full')[:len(tt)]
    put(thump * 0.8 + click * 0.5 + tail / (np.abs(tail).max() + 1e-9) * 0.12, 3.2, 0.75)
    # пролёт сквозь зеркало: свист со сменой панорамы
    wd = 1.45; wh = sweep_noise(rng, wd, 380, 2600) * np.sin(np.linspace(0, np.pi, int(wd * SR))) ** 1.6
    pan = np.linspace(0, 1, len(wh))
    put(wh * (1 - 0.6 * pan), 4.3, 0.42, 0)
    put(wh * (0.4 + 0.6 * pan), 4.3, 0, 0.42)
    # звон стекла
    tg = np.arange(int(1.2 * SR)) / SR
    glass = sum(np.sin(2 * np.pi * f * tg + rng.uniform(0, 6)) * np.exp(-tg * d) for f, d in ((2140, 4), (3310, 5), (4720, 6), (6180, 7)))
    put(glass / 4 * env(len(tg), 0.003, 0.05), 5.03, 0.18)
    # ночь: сверчки + ветер
    tn = np.arange(int(5.4 * SR)) / SR
    for f, ph, gl, gr in ((4650, 0.0, 0.05, 0.015), (4320, 0.43, 0.015, 0.045)):
        chirp = ((tn + ph) % 0.95 < 0.12) * (np.sin(2 * np.pi * 32 * tn) > 0)
        put(np.sin(2 * np.pi * f * tn) * signal.sosfilt(signal.butter(1, 120 / (SR / 2), output='sos'), chirp.astype(float)) * env(len(tn), 0.8, 0.3), 4.6, gl, gr)
    wind = signal.sosfilt(signal.butter(2, [200 / (SR / 2), 700 / (SR / 2)], 'band', output='sos'), rng.standard_normal(len(tn)))
    put(wind / np.abs(wind).max() * env(len(tn), 1.0, 0.4) * (0.7 + 0.3 * np.sin(tn * 0.8)), 4.6, 0.07)
    mix = np.stack([L, Rr], 1)
    mix *= 0.7 / (np.abs(mix).max() + 1e-9)
    fade = int(0.25 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return mix


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else 'v1'
    out_dir = paths.RENDERS / '02-movie-masks'; out_dir.mkdir(parents=True, exist_ok=True)
    build = paths.build(HERE)
    if '--frames' in sys.argv:
        for s in sys.argv[sys.argv.index('--frames') + 1].split(','):
            Image.fromarray(render_at(int(s) / FPS)).save(build / f'test_{int(s):04d}.png')
        return
    wav = build / 'test_audio.wav'
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(make_audio(), -0.98, 0.98) * 32767).astype('<i2').tobytes())
    out = out_dir / f'test_fragment_{version}.mp4'
    cmd = [paths.ffmpeg(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', str(wav), '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
           '-movflags', '+faststart', '-shortest', str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        proc.stdin.write(render_at(i / FPS).tobytes())
    proc.stdin.close(); proc.wait()
    print('->', out)


if __name__ == '__main__':
    main()
