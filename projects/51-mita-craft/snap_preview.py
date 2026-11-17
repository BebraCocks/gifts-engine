"""Превью сцены «щелчок → крафтовый круг → наряд звездочёта» (30 ключевых кадров ChatGPT + досчёт).
python3 snap_preview.py → build/snap_preview.mp4 (540×960, 60 к/с)."""
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import anim

# выравнивание поз (ChatGPT ставит фигуру на листе чуть по-разному → Миту «шатало»):
# центр ног (нижние 25 % силуэта) → x = 384, подошвы → y = 990. Высоту полёта задаём сами (FLOAT).
AL = Path(__file__).resolve().parent / 'input' / 'mita' / 'frames_aligned'


def _run_mid(row, x0):
    xs = np.nonzero(row)[0]
    if len(xs) == 0:
        return None
    runs = np.split(xs, np.nonzero(np.diff(xs) > 3)[0] + 1)
    r = min(runs, key=lambda r: 0 if r[0] <= x0 <= r[-1] else min(abs(r[0] - x0), abs(r[-1] - x0)))
    return (r[0] + r[-1]) / 2


def body_x(a):
    """Центр тела: голова (5–15 % высоты, отрезок у центра — без разлетающихся волос), талия (38–46 %), обе ноги (низ 12 %)."""
    al = a[..., 3] > 60
    ys = np.nonzero(al.any(1))[0]
    y0, y1 = ys.min(), ys.max()
    h = y1 - y0
    def band(f0, f1, x0):
        v = [_run_mid(al[y], x0) for y in range(int(y0 + f0 * h), int(y0 + f1 * h))]
        v = [x for x in v if x is not None]
        return float(np.median(v))
    cx = float(np.median(np.nonzero(al)[1]))
    head = band(0.05, 0.15, cx)
    waist = band(0.38, 0.46, head)
    lx = np.nonzero(al[int(y1 - 0.12 * h):y1 + 1].any(0))[0]
    legs = (lx.min() + lx.max()) / 2
    return 0.5 * head + 0.5 * legs


AIRBORNE = {'jump_5', 'jump_3', 'jump_4', 'jump_6', 'jump_7', 'jump_45', 'jump_55'}   # позы в воздухе


def align_all(names):
    AL.mkdir(exist_ok=True)
    order = list(names)
    xs = {n: body_x(anim.pose(n)) for n in order}
    for i, n in enumerate(order):
        x = xs[n] if n != 'astro_sc3' else xs['astro_sc2']   # в последнем кадре она наклоняется к зрителю — наклон оставляем
        a = anim.pose(n)
        ys = np.nonzero(a[..., 3] > 60)[0]
        dy = 0.0 if n in AIRBORNE else 990 - ys.max()      # в прыжке — высота как на листе (пол листа ≈ 990)
        Image.fromarray(anim._translate(a, np.array([384 - x, dy], np.float32))).save(AL / f'{n}.png')


HERE = Path(__file__).resolve().parent
W, H, FPS = 540, 960, 60
SEQ = ['snap_idle', 'snap_up1', 'snap_up2', 'snap_up3', 'snap_pre', 'snap_click', 'snap_post', 'snap_dn1', 'snap_dn2',
       'snap_dn3', 'snap_wind75', 'snap_wind', 'snap_rise1', 'snap_rise2', 'snap_peak',
       'astro_peak', 'astro_fall1', 'astro_fall2', 'astro_fall3', 'astro_land', 'astro_look1', 'astro_look2', 'astro_look3',
       'astro_cape', 'astro_rel1', 'astro_rel2', 'astro_rel3', 'astro_sc1', 'astro_sc2', 'astro_sc3']
# длительность перехода В кадр i (с): щелчок быстрый, полёт и приземление медленнее, на ключевых — задержка
DUR = [0.0, 0.08, 0.07, 0.07, 0.07, 0.05, 0.06, 0.08, 0.08, 0.09, 0.09, 0.1, 0.1, 0.1, 0.11,
       0.0, 0.11, 0.11, 0.11, 0.11, 0.09, 0.08, 0.08, 0.09, 0.1, 0.08, 0.08, 0.08, 0.08, 0.14]
HOLD = {'snap_idle': 0.12, 'astro_cape': 0.12, 'astro_sc3': 0.35}
T, t = [], 0.0
for n, d in zip(SEQ, DUR):
    t += d
    T.append(t)
    t += HOLD.get(n, 0.0)
TOTAL = t
FLASH = T[SEQ.index('astro_peak')]
CLICK = T[SEQ.index('snap_click')]


def mita_at(t):
    for i in range(1, len(SEQ)):
        if t < T[i]:
            a, b = SEQ[i - 1], SEQ[i]
            if a.split('_')[0] != b.split('_')[0]:          # смена наряда — в белой вспышке, без морфа
                return anim.pose(b if t > T[i] - 0.02 else a)
            k = (t - (T[i] - DUR[i])) / DUR[i] if DUR[i] else 1.0
            return anim.morph(a, b, max(0.0, k)) if k > 0 else anim.pose(a)
    return anim.pose(SEQ[-1])


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


ZOD = '♈♉♊♋♌♍♎♏♐♑♒♓'


def circle(t):
    """Золотой крафтовый круг на полу (перспектива), зажигается после щелчка, ярчайший у вспышки, затем гаснет."""
    on = ease((t - CLICK) / 0.5) * (1 - ease((t - FLASH - 0.5) / 0.9))
    if on <= 0:
        return None
    S = 2
    R = 210
    im = Image.new('RGBA', (2 * R * S + 40, 2 * R * S + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = im.width // 2
    rot = (t - CLICK) * 0.9
    gold = (255, 205, 90)
    for r, w in ((R, 6), (R * 0.82, 3), (R * 0.5, 4)):
        d.ellipse([c - r * S, c - r * S, c + r * S, c + r * S], outline=gold + (int(255 * on),), width=w * S)
    for k in range(12):
        a = rot + k * math.pi / 6
        x, y = c + math.cos(a) * R * 0.91 * S, c + math.sin(a) * R * 0.91 * S
        d.ellipse([x - 9 * S, y - 9 * S, x + 9 * S, y + 9 * S], fill=gold + (int(230 * on),))
        x2, y2 = c + math.cos(a + 0.26) * R * 0.66 * S, c + math.sin(a + 0.26) * R * 0.66 * S
        d.line([c + math.cos(a) * R * 0.5 * S, c + math.sin(a) * R * 0.5 * S, x2, y2], fill=gold + (int(160 * on),), width=2 * S)
    for k in range(8):
        a = -rot * 1.6 + k * math.pi / 4
        d.line([c, c, c + math.cos(a) * R * 0.5 * S, c + math.sin(a) * R * 0.5 * S], fill=gold + (int(200 * on),), width=3 * S)
    d.ellipse([c - 26 * S, c - 26 * S, c + 26 * S, c + 26 * S], fill=(255, 220, 110, int(255 * on)))
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    glow = im.filter(ImageFilter.GaussianBlur(10))
    out = Image.alpha_composite(glow, im)
    return out.resize((out.width, int(out.height * 0.32)), Image.LANCZOS), on


def frame(t):
    bg = Image.new('RGBA', (W, H), (250, 248, 255, 255))
    foot = 830
    c = circle(t)
    if c:
        im, on = c
        bg.alpha_composite(im, (W // 2 - im.width // 2, foot - im.height // 2))
        # столб света от круга
        col = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(col)
        k = on * (0.5 + 0.5 * ease((t - (FLASH - 0.6)) / 0.6))
        dd.polygon([(W / 2 - 170, foot), (W / 2 + 170, foot), (W / 2 + 120, 120), (W / 2 - 120, 120)], fill=(255, 220, 140, int(70 * k)))
        bg.alpha_composite(col.filter(ImageFilter.GaussianBlur(30)))
    a = mita_at(t)
    m = Image.fromarray(a)
    rise = ease((t - T[SEQ.index('snap_wind75')]) / (FLASH - T[SEQ.index('snap_wind75')])) * (1 - ease((t - FLASH) / (T[SEQ.index('astro_land')] - FLASH)))
    lift = int(70 * rise)                                  # плавный подъём и приземление
    s = 0.72
    m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
    bg.alpha_composite(m, (W // 2 - m.width // 2, foot - int(990 * s) - lift))
    # искры, поднимающиеся вверх
    if c:
        d = ImageDraw.Draw(bg)
        rng = np.random.default_rng(3)
        for j in range(26):
            u = ((t - CLICK) * rng.uniform(0.3, 0.6) + rng.uniform(0, 1)) % 1.0
            x = W / 2 + rng.uniform(-190, 190) * (1 - 0.3 * u)
            y = foot - u * 700
            r = rng.uniform(2, 5)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 215, 120, int(220 * c[1] * (1 - u))))
    # вспышка
    f = math.exp(-((t - FLASH) / 0.09) ** 2)
    if f > 0.01:
        wh = Image.new('RGBA', (W, H), (255, 252, 235, int(255 * min(1.0, f * 1.1))))
        bg.alpha_composite(wh)
    return np.array(bg.convert('RGB'))


if __name__ == '__main__':
    align_all(SEQ)
    anim.FR = AL
    anim.pose.cache_clear()
    out = HERE / 'build' / 'snap_preview.mp4'
    out.parent.mkdir(exist_ok=True)
    n = int((TOTAL + 0.3) * FPS)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)], stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    print(out, round(TOTAL, 2), 's', n, 'кадров')
