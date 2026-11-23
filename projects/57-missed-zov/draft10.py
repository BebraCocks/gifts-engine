"""Черновик первых 10 секунд «Зова»: кадры 1–3 + экран с сообщениями, склейки под бит.

    python -B projects/57-missed-zov/draft10.py
Музыка: build/zov_music_cut_v1.mp3 (нарезка трека автора, в Git не хранится).
Результат: build/zov_first10_vN.mp4
"""
import math, random, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import sfxkit  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
B = 0.5573                      # один удар музыки, 108 BPM
DUR = 18 * B
OUT = HERE / 'build' / (sys.argv[1] if len(sys.argv) > 1 else 'zov_first10_v1.mp4')
FONT = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
f = lambda w, s: ImageFont.truetype(str(FONT / f'SF-Pro-Text-{w}.otf'), s)

def cover(path):
    im = Image.open(path).convert('RGB')
    k = max(W / im.width, H / im.height) * 1.25
    return im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)

F1, F2, F3 = (cover(HERE / 'refs' / 'frames' / n) for n in
              ('frame_01_phone.jpg', 'frame_02_reading.jpg', 'frame_03_stare.jpg'))

def view(im, zoom, dx=0, dy=0, cy=0.5):
    """zoom 1.0 = кадр целиком по ширине экрана."""
    base = im.width / 1.25
    cw, ch = base / zoom, base / zoom * H / W
    cx, cyy = im.width / 2 + dx, im.height * cy + dy
    box = (cx - cw / 2, cyy - ch / 2, cx + cw / 2, cyy + ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=box)

ease = lambda x: 1 - (1 - min(max(x, 0), 1)) ** 3

MSG = [('Аня', 'Мисед, меня заскамил твой двойник', (232, 93, 117)),
       ('Dima_TON', 'Мисед, фейк забрал мой подарок', (90, 160, 250)),
       ('Кирилл', 'кто-то с твоим ником просил 100 звёзд', (250, 170, 60)),
       ('nft_vika', 'он сказал, что улучшит мой подарок...', (170, 110, 240)),
       ('Саша', 'Мисед, это правда ты мне писал?', (70, 200, 160)),
       ('Max', 'у меня украли NFT, помоги', (240, 120, 70)),
       ('Лиза', 'твой двойник просит сидку', (230, 90, 180)),
       ('Егор', 'Мисед, их тут десятки', (110, 190, 90)),
       ('Тимур', 'МИСЕД!!!', (240, 80, 80))]

def card(name, text, col, w=1000, banner=False):
    h = 170
    c = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 34, fill=(28, 31, 38, 235 if banner else 255))
    d.ellipse((28, 30, 138, 140), fill=col)
    d.text((83, 85), name[0].upper(), font=f('Bold', 52), fill='white', anchor='mm')
    d.text((165, 38), name, font=f('Semibold', 38), fill='white')
    d.text((165, 92), text, font=f('Regular', 34), fill=(200, 205, 215))
    d.text((w - 30, 42), '23:47', font=f('Regular', 28), fill=(140, 145, 155), anchor='ra')
    if not banner:
        d.ellipse((w - 80, 92, w - 32, 140), fill=(64, 140, 255))
        d.text((w - 56, 116), str(random.Random(name).randint(2, 9)), font=f('Bold', 28), fill='white', anchor='mm')
    return c

CARDS = [card(*m) for m in MSG]
BANNERS = [card(*m, banner=True) for m in MSG[:2]]

def phone_screen(t):
    """Экран со списком чатов; новое сообщение на каждый удар."""
    im = Image.new('RGB', (W, H), (14, 16, 21))
    d = ImageDraw.Draw(im)
    d.text((60, 70), '23:47', font=f('Semibold', 40), fill='white')
    d.text((60, 160), 'Сообщения', font=f('Bold', 76), fill='white')
    n_new = int((t - 4 * B) / B) + 1          # 2 сообщения уже пришли баннерами
    shown = min(2 + max(n_new - 1, 0), len(MSG))
    since = (t - 4 * B) - (n_new - 1) * B
    slide = ease(since / 0.18) if shown > 2 else 1
    y0 = 300
    for i in range(shown):
        idx = shown - 1 - i                    # новое сверху
        y = y0 + i * 190 - (190 * (1 - slide) if shown > 2 else 0)
        if i == 0 and shown > 2:
            a = int(255 * slide)
            cimg = CARDS[idx].copy(); cimg.putalpha(cimg.getchannel('A').point(lambda v: min(v, a)))
            im.paste(cimg, (40, int(y0 - 60 * (1 - slide))), cimg)
        else:
            im.paste(CARDS[idx], (40, int(y)), CARDS[idx])
    z = 1 + 0.03 * (t - 4 * B) / (8 * B)
    return im.resize((round(W * z), round(H * z))).crop(((round(W * z) - W) // 2, (round(H * z) - H) // 2,
                                                         (round(W * z) - W) // 2 + W, (round(H * z) - H) // 2 + H))

rng = random.Random(7)
def shake(t, hits, amp=10, dur=0.18):
    for h in hits:
        if 0 <= t - h < dur:
            k = 1 - (t - h) / dur
            return rng.uniform(-amp, amp) * k, rng.uniform(-amp, amp) * k
    return 0, 0

def frame(t):
    if t < 4 * B:                                   # A: телефон вибрирует, приходят баннеры
        dx, dy = shake(t, [0.05, B, 2 * B, 3 * B])
        im = view(F1, 1.0 + 0.05 * t / (4 * B), dx, dy)
        for k, tb in enumerate([0.05, 2 * B]):
            if t >= tb:
                e = ease((t - tb) / 0.22)
                y = int(-200 + (90 + 190 * (1 - k if t >= 2 * B else 0) - (-200)) * e)
                if k == 1: y = int(-200 + (90 - (-200)) * e)
                im.paste(BANNERS[k], (40, y), BANNERS[k])
        return im
    if t < 12 * B:                                  # B: экран с сообщениями
        dx, dy = shake(t, [4 * B + i * B for i in range(8)], amp=5, dur=0.12)
        im = phone_screen(t)
        return im.transform((W, H), Image.AFFINE, (1, 0, -dx, 0, 1, -dy)) if dx else im
    if t < 16 * B:                                  # C: читает
        return view(F2, 1.0 + 0.07 * (t - 12 * B) / (4 * B), cy=0.45)
    u = t - 16 * B                                  # D: взгляд, резкий наезд
    im = view(F3, 1.14 - 0.12 * ease(u / 0.25) + 0.02 * u / (2 * B), cy=0.42)
    if u < 2 / FPS:
        im = Image.blend(im, Image.new('RGB', (W, H), (200, 225, 255)), 0.6)
    return im

def audio():
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(HERE / 'build' / 'zov_music_cut_v1.mp3'), '-t', f'{DUR:.3f}',
                          '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    mus = np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float32) / 32768
    n = int(DUR * SR); mus = np.pad(mus, ((0, max(0, n - len(mus))), (0, 0)))[:n]
    fade = int(0.3 * SR); mus[-fade:] *= np.linspace(1, 0, fade)[:, None]
    fx = np.zeros((n, 2), np.float32)
    for tb in [0.05, B, 2 * B, 3 * B]:              # вибрация телефона (синтез: в паке нет)
        m = np.arange(int(0.22 * SR)) / SR
        buzz = 0.18 * np.sign(np.sin(2 * math.pi * 165 * m)) * (0.5 + 0.5 * np.sin(2 * math.pi * 28 * m)) * np.exp(-m * 6)
        i = int(tb * SR); fx[i:i + len(buzz)] += buzz[:, None] * 0.5
    kit = sfxkit.Kit(HERE)
    for tb in [0.05, 2 * B]:
        kit.add(fx, 'popup', tb + 0.03, gain_db=-12)
    for i in range(1, 8):
        kit.add(fx, ['popup', 'pop'], 4 * B + i * B, gain_db=-13)
    kit.add(fx, 'whoosh-short', 16 * B, align='peak', gain_db=-10)
    kit.save()
    mix = mus * 0.9 + fx
    return np.clip(mix, -1, 1)

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wav = OUT.with_suffix('.wav')
    a = audio()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(wav)],
                   input=a.astype(np.float32).tobytes(), check=True)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                          '-r', str(FPS), '-i', '-', '-i', str(wav), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                          '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(OUT)],
                         stdin=subprocess.PIPE)
    N = int(DUR * FPS)
    for i in range(N):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % (N // 10) == 0:
            print(f'PROGRESS {round(100 * i / N)}%', flush=True)
    p.stdin.close(); p.wait(); wav.unlink()
    print('OK', OUT)

if __name__ == '__main__':
    main()
