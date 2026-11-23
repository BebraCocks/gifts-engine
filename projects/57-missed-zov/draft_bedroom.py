"""Черновик сцены в спальне (3D-версия): видео Gemini + музыка Lunar Abyss + три сообщения с голосами.

    python -B projects/57-missed-zov/draft_bedroom.py [имя.mp4]
Входы в build/ (в Git не хранятся): veo_01_bedroom.mp4, lunar_abyss.mp3, voice/v1.wav, v2.wav, v4.wav.
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import sfxkit  # noqa: E402

BLD = HERE / 'build'
W, H, FPS, SR = 1080, 1920, 30, 48000
BEAT0, B = 0.1625, 0.44118                    # сетка ударов Lunar Abyss
beat = lambda k: BEAT0 + k * B
DUR = 12.0
OUT = BLD / (sys.argv[1] if len(sys.argv) > 1 else 'zov3d_bedroom_v1.mp4')
FONT = ROOT / 'input' / 'fonts' / 'SF-Pro-Text' / 'SF-Pro-Text-Heavy.otf'

# сообщение, голос, начало (на удар), сторона
MSGS = [('Мисед, меня заскамил\nтвой двойник!', 'v1.wav', beat(7), 'L'),
        ('Мисед, фейк забрал\nмой подарок!', 'v2.wav', beat(14), 'R'),
        ('Он сказал, что улучшит\nмой подарок...', 'v4.wav', beat(20), 'L')]
SHOW = 1.8

def bubble(text):
    fnt = ImageFont.truetype(str(FONT), 54)
    d0 = ImageDraw.Draw(Image.new('L', (1, 1)))
    l, t, r, b = d0.multiline_textbbox((0, 0), text, font=fnt, spacing=10, align='center')
    pw, ph = int(r - l + 80), int(b - t + 60)
    im = Image.new('RGBA', (pw + 40, ph + 70), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20 + pw, 26 + ph), 40, fill=(0, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 16, 20 + pw, 16 + ph), 40, fill=(255, 255, 255, 245))
    d.polygon([(20 + pw // 2 - 26, 16 + ph - 2), (20 + pw // 2 + 26, 16 + ph - 2), (20 + pw // 2, 16 + ph + 40)],
              fill=(255, 255, 255, 245))
    d.multiline_text((20 + pw // 2, 16 + ph // 2), text, font=fnt, fill=(20, 22, 30), anchor='mm',
                     spacing=10, align='center')
    return im

def png_bubble(i, width=900):              # плашки нарисованы в ChatGPT (refs/ui)
    im = Image.open(HERE / 'refs' / 'ui' / f'bubble_{i}.png').convert('RGBA')
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)

BUB = [png_bubble(i + 1) for i in range(len(MSGS))]
ease_out_back = lambda x: 1 + 2.7 * (x - 1) ** 3 + 1.7 * (x - 1) ** 2

def overlay(frame, t):
    for (txt, _, t0, side), bim in zip(MSGS, BUB):
        u = t - t0
        if not 0 <= u < SHOW:
            continue
        s = ease_out_back(min(u / 0.22, 1)) if u < 0.22 else 1
        a = 1 if u < SHOW - 0.25 else (SHOW - u) / 0.25
        if u > SHOW - 0.25:
            s *= 1 + 0.15 * (u - (SHOW - 0.25)) / 0.25
        w, h = max(1, int(bim.width * s)), max(1, int(bim.height * s))
        im = bim.resize((w, h), Image.BICUBIC)
        if a < 1:
            im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
        bw = bim.width                         # держим пузырь целиком в кадре
        cx = 20 + bw / 2 if side == 'L' else W - 20 - bw / 2
        cy = 300 + (90 if side == 'R' else 0)
        frame.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))
    return frame

def audio():
    def dec(path, extra=()):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), *extra, '-t', f'{DUR}', '-f', 's16le',
                              '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
        a = np.frombuffer(raw, np.int16).reshape(-1, 2).astype(np.float32) / 32768
        n = int(DUR * SR)
        return np.pad(a, ((0, max(0, n - len(a))), (0, 0)))[:n]
    mus = dec(BLD / 'lunar_abyss.mp3')
    room = dec(BLD / 'veo_01_bedroom.mp4')            # тишина комнаты и вибрация из Gemini
    mix = mus * 0.85 + room * 0.6
    for txt, v, t0, _ in MSGS:
        va = dec(BLD / 'voice' / v, ('-af', 'atempo=1.15'))
        i = int((t0 + 0.05) * SR)
        va = va[:len(mix) - i]
        mix[i:i + len(va)] += va * 1.0
    fx = np.zeros_like(mix)
    kit = sfxkit.Kit(HERE)
    for _, _, t0, _ in MSGS:
        kit.add(fx, 'popup', t0, gain_db=-10)
    kit.save()
    fade = int(0.4 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return np.clip(mix + fx, -1, 1)

def main():
    wav = OUT.with_suffix('.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', str(wav)],
                   input=audio().astype(np.float32).tobytes(), check=True)
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(BLD / 'veo_01_bedroom.mp4'), '-t', f'{DUR}',
                            '-vf', f'fps={FPS},scale={W}:{H}:flags=lanczos', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}',
                            '-r', str(FPS), '-i', '-', '-i', str(wav), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                            '-crf', '18', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(OUT)], stdin=subprocess.PIPE)
    n, last = 0, None
    while n < int(DUR * FPS):
        buf = dec.stdout.read(W * H * 4)
        if len(buf) == W * H * 4:
            fr = last = Image.frombuffer('RGBA', (W, H), buf, 'raw', 'RGBA', 0, 1).copy()
            t_end = n / FPS
        else:                                  # видео кончилось: держим последний кадр с наездом
            z = 1 + 0.04 * (n / FPS - t_end)
            cw, ch = W / z, H / z
            fr = last.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        enc.stdin.write(overlay(fr, n / FPS).convert('RGB').convert('RGBA').tobytes())
        n += 1
    enc.stdin.close(); enc.wait(); wav.unlink()
    print('OK', OUT, n, 'frames')

if __name__ == '__main__':
    main()
