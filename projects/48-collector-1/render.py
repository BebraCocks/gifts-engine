"""«Коллекционер», часть 1 — видео 1080x1920, 60 fps. 2D-графика кодом (art.py), местами объём: параллакс,
наклон телефона, «рыбий глаз» глазка. Сцены идут по таймлайну озвучки (timeline.py), события звука и картинки
общие (времена стуков/ударов совпадают с audio.py). Две вставки RubUp — banner.Breaks.

    python -B render.py --frames 0,600,1200        # пробные кадры (номер кадра в итоговом времени)
    python -B render.py --video build/video_only.mp4"""
import functools
import math
import re
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
sys.path.insert(0, str(HERE))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import banner
import captions as CAP
import frames
import gifts_api
import lottie
import art as A
import script
from timeline import ON, END, STOPS, DUR, WHO

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks(STOPS, cy=H / 2, speed=1.1)
GIFT = ('Loot Bag', 'Money Bag', '0,5 %')                    # данные gifts engine (api.changes.tg), 2026-11-14
GIFT_JSON = str(gifts_api.model_file(GIFT[0], GIFT[1], 'json'))
ICE = ('Ice Cream', 'Utya Pop')
ICE_JSON = str(gifts_api.model_file(*ICE, 'json'))
BD = gifts_api.backdrops('Loot Bag')
_bd = next((b for b in BD if b['name'] == 'Cyberpunk'), BD[0])['hex']
BACKDROP = (tuple(int(_bd['centerColor'][k:k + 2], 16) for k in (1, 3, 5)), tuple(int(_bd['edgeColor'][k:k + 2], 16) for k in (1, 3, 5)))
SIDE_GIFTS = [str(gifts_api.model_png(g, m, 256)) for g, m in (('Plush Pepe', 'Cozy Galaxy'), ("Durov's Cap", None), ('Swiss Watch', 'DeLorean'),
                                                                 ('Hypno Lollipop', 'The Maze'), ('Spy Agaric', 'Teleshroom')) if m]


def sm(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lin(t, a, b):
    return min(1.0, max(0.0, (t - a) / (b - a))) if b > a else float(t >= a)


def out_back(x, s=1.6):
    x = min(1.0, max(0.0, x)) - 1
    return 1 + x * x * ((s + 1) * x + s)


# ================================================================== события звука (те же времена, что в audio.py)
KNOCKS = ([ON[10] + 1.35 + d for d in (0, 0.32, 0.6)] + [ON[11] - 0.55 + d for d in (0, 0.28)]
          + [END[20] + 0.05 + d for d in (0, 0.9)] + [END[27] + 0.15 + d for d in (0, 0.25, 0.5, 0.75)])
_t0 = END[21] + 0.15
BASH = [_t0 + h for h in [0, 0.95, 1.7, 2.3, 3.4, 4.0, 4.6, 5.6, 6.2, 6.7, 7.6, 8.2, 8.7, 9.3, 9.8, 10.3] if _t0 + h < END[23] + 0.1]
BIG = END[23] + 0.3                                          # последний, самый сильный удар
JAR_HIT = END[24] + 0.2                                      # банка разбивается


def impulse(t, times, decay=7.0, dur=0.6):
    v = 0.0
    for x in times:
        if 0 <= t - x < dur:
            v += math.exp(-(t - x) * decay)
    return v


def shake(t, amp, times, decay=9.0):
    k = impulse(t, times, decay)
    return (math.sin(t * 91) * amp * k, math.cos(t * 77) * amp * k * 0.7)


# ================================================================== голос: тексты, слова, рот
def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>|\[[^\]]*\]|#.*$', '', s)).strip()


TEXT = {i: clean(t) for i, (w, t) in enumerate(script.LINES, 1)}
TEXT[18] = 'Удачи 😇'


@functools.lru_cache(None)
def words(i):
    return CAP.estimate_word_times(str(HERE / 'voice' / f'L{i:02d}.wav'), clean(script.LINES[i - 1][1]), offset=ON[i])


def word_t(i, k):
    w = words(i)
    return w[min(k, len(w) - 1)][1]


@functools.lru_cache(None)
def env(i):
    with wave.open(str(HERE / 'voice' / f'L{i:02d}.wav')) as f:
        x = np.frombuffer(f.readframes(f.getnframes()), '<i2').astype(np.float32) / 32768
    hop = 480
    e = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    return e / (np.percentile(e, 95) + 1e-9)


def mouth(t, lines=None):
    """Уровень рта 0..3 по громкости реплики, которая звучит в момент t (только реплики Кирилла вслух)."""
    for i in (lines or [k for k, w in WHO.items() if w == 'K']):
        if ON[i] <= t < END[i]:
            e = env(i)
            k = int((t - ON[i]) * 100)
            v = e[min(k, len(e) - 1)]
            return 0 if v < 0.15 else 1 if v < 0.45 else 2 if v < 0.8 else 3
    return 0


def blink(t, seed=0):
    p = (t + seed * 1.7) % 3.7
    return 1 if p < 0.12 else 0


# ================================================================== субтитры
CAP_COL = {'N': (245, 245, 250), 'K': (255, 214, 90), 'T': (180, 220, 255), 'U': (150, 235, 170), 'X': (255, 90, 90),
           'M': (255, 170, 200), 'P': (140, 190, 255)}
NO_CAP = {2, 18, 11, 15, 28, 29}                                  # видны текстом на экране телефона или в «пузыре» у двери
CAP_Y = 1610


@functools.lru_cache(None)
def chunks(i):
    """Реплика → куски по 1–2 строки: [(текст, начало)]."""
    ws = words(i)
    out, cur, t0 = [], [], None
    for w, t in ws:
        if not cur:
            t0 = t
        cur.append(w)
        txt = ' '.join(cur)
        if len(txt) > 40 or (re.search(r'[.!?…]$', w) and len(txt) > 14):
            out.append((txt, t0))
            cur = []
    if cur:
        out.append((' '.join(cur), t0))
    return out


@functools.lru_cache(maxsize=256)
def cap_img(text, who):
    col = CAP_COL[who]
    lines = A.wrap(text, 56, 'Heavy', 900)
    lh = 70
    w = max(A.font('Heavy', 56).getlength(x) for x in lines) + 70
    h = lh * len(lines) + 40
    im = A.canvas(w, h)
    d = ImageDraw.Draw(im)
    if who == 'T':                                                        # мысли — облачко
        d.rounded_rectangle([0, 0, w - 1, h - 1], 46, fill=(30, 40, 70, 215), outline=(180, 220, 255, 230), width=4)
        for k, (x, y, r) in enumerate(((60, h + 14, 14), (34, h + 40, 9))):
            d.ellipse([x - r, y - r, x + r, y + r], fill=(30, 40, 70, 215), outline=(180, 220, 255, 230), width=3)
    else:
        d.rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=(8, 8, 16, 190))
    for k, ln in enumerate(lines):
        d.text((w / 2, 20 + lh * k + lh / 2), ln, font=A.font('Heavy', 56), fill=A.rgba(col), anchor='mm',
               stroke_width=3, stroke_fill=(0, 0, 0, 255))
    if text.endswith('😇'):
        pass
    return im


def draw_caption(base, t, skip=()):
    for i in TEXT:
        if i in NO_CAP or i in skip:
            continue
        if ON[i] - 0.05 <= t < END[i] + 0.35:
            ch = chunks(i)
            k = max(j for j, (_, t0) in enumerate(ch) if t >= t0 - 0.05) if t >= ch[0][1] - 0.05 else 0
            txt, t0 = ch[k]
            a = sm((t - (ON[i] - 0.05)) / 0.12) * (1 - sm((t - END[i] - 0.15) / 0.2))
            im = cap_img(txt, WHO[i])
            y = CAP_Y - im.height / 2 + (1 - sm((t - t0 + 0.05) / 0.12)) * 18
            A.paste(base, im, (W - im.width) / 2, y, a)
            return


# ================================================================== общие элементы
def finish(im, t, sx=0.0, sy=0.0, vig=0.45, grain=True):
    if abs(sx) > 0.5 or abs(sy) > 0.5:
        im = im.transform(im.size, Image.AFFINE, (1, 0, -sx, 0, 1, -sy), Image.BILINEAR)
    if vig:
        im = A.vignette(im, vig)
    return im


def big_label(base, s, y, t, t0, size=96, color=A.WHITE, dur=None):
    if t < t0:
        return
    a = sm((t - t0) / 0.15)
    if dur is not None:
        a *= 1 - sm((t - t0 - dur) / 0.2)
    im = A.label(s, size, color, 'Heavy', stroke=4)
    sc = 0.6 + 0.4 * out_back((t - t0) / 0.3)
    A.place_c(base, im, W / 2, y, sc, alpha=a)


def room_dim(k=0.55):
    return A.tint(A.room_bg().copy(), (8, 8, 22), k)


@functools.lru_cache(maxsize=2)
def _room_dim_cached(k):
    return room_dim(k)


@functools.lru_cache(maxsize=2)
def _hall_cached(k):
    return A.tint(A.hall_bg().copy(), (8, 8, 22), k)


def clock_img(s, col=(255, 70, 80)):
    return A.label(s, 210, col, 'Heavy', stroke=6, stroke_c=(30, 6, 10))


def exterior(cam, police=0.0, t=0.0, neighbor=0.0):
    """Ночная окраина с наездом камеры (через аффинное преобразование — без лишних пикселей)."""
    base = _sky().copy()
    A.paste(base, A.stars(), 0, -cam * 40)
    d = ImageDraw.Draw(base)
    mx, my = 790 - cam * 40, 260 - cam * 80
    d.ellipse([mx - 70, my - 70, mx + 70, my + 70], fill=(240, 236, 210))
    d.ellipse([mx - 95, my - 80, mx + 35, my + 50], fill=A.SKY_TOP)
    A.paste(base, A.city_far(), -300 - cam * 120, 900 - cam * 100)
    bld = A.panel_building()
    wx, wy = A.kirill_window_xy()
    s = 1.0 + cam * 2.6
    tx = (1 - cam) * (W / 2 - bld.width / 2) + cam * (W / 2 - wx * s)
    ty = (1 - cam) * 520 + cam * (H * 0.45 - wy * s)
    layer = bld.transform((W, H), Image.AFFINE, (1 / s, 0, -tx / s, 0, 1 / s, -ty / s), Image.BICUBIC)
    base.alpha_composite(layer)
    d = ImageDraw.Draw(base)
    gy = ty + bld.height * s
    if gy - 6 < H:
        d.rectangle([0, max(0, gy - 6), W, H], fill=(28, 26, 40))
    if neighbor > 0:                                                    # соседка в окне с телефоном
        nx, ny = tx + (30 + 4 * 760 / 6 + 35) * s, ty + (40 + 3 * 1500 / 9 + 46) * s
        d.rectangle([nx - 35 * s, ny - 46 * s, nx + 35 * s, ny + 46 * s], fill=(255, 220, 140))
        d.ellipse([nx - 14 * s, ny - 30 * s, nx + 14 * s, ny - 2 * s], fill=(30, 20, 30))
        d.rectangle([nx - 20 * s, ny - 2 * s, nx + 20 * s, ny + 46 * s], fill=(30, 20, 30))
        d.rectangle([nx + 6 * s, ny - 26 * s, nx + 16 * s, ny - 8 * s], fill=A.GLOW)
    for x0 in (80, 960):                                                # деревья переднего плана — быстрый параллакс
        x = x0 + (x0 - W / 2) * cam * 1.6
        y = H - 120 + cam * 500
        d.line([x, y, x, y - 520], fill=(14, 12, 22), width=22)
        for br in range(5):
            ang = -math.pi / 2 + (br - 2) * 0.45
            d.line([x, y - 300 - br * 40, x + math.cos(ang) * 180, y - 300 - br * 40 + math.sin(ang) * 180], fill=(14, 12, 22), width=9)
    if police > 0:
        ph = (t * 3.2) % 1
        col = (255, 40, 60) if ph < 0.5 else (60, 110, 255)
        base = A.tint(base, col, 0.22 * police * (0.6 + 0.4 * abs(math.sin(t * 20))))
        car = _police_car()
        ImageDraw.Draw(base).rectangle([0, H - 480, W, H - 380], fill=(30, 28, 38))                # дорога
        A.paste(base, car, W / 2 - car.width / 2 + (1 - police) * -700, H - 620)
        lb = A.canvas(300, 120)
        ImageDraw.Draw(lb).ellipse([0, 0, 300, 120], fill=A.rgba(col, 160))
        A.place_c(base, lb.filter(ImageFilter.GaussianBlur(18)), W / 2 + (1 - police) * -700, H - 610, 1.0)
    return base


@functools.lru_cache(maxsize=1)
def _sky():
    return A.vgrad(W, H, A.SKY_TOP, A.SKY_BOT)


@functools.lru_cache(maxsize=1)
def _police_car():
    im = A.canvas(520, 220)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 80, 510, 180], 40, fill=(235, 235, 240), outline=A.INK, width=7)
    d.polygon([(130, 82), (180, 20), (360, 20), (410, 82)], fill=(235, 235, 240), outline=A.INK)
    d.rectangle([20, 120, 500, 140], fill=(40, 90, 200))
    d.rectangle([220, 4, 260, 22], fill=(255, 40, 60))
    d.rectangle([280, 4, 320, 22], fill=(60, 110, 255))
    for x in (110, 410):
        d.ellipse([x - 44, 140, x + 44, 216], fill=(20, 20, 26), outline=A.INK, width=6)
    return im


# ================================================================== сцены
def sc_exterior(t, t0, t1, cam0=0.0, cam1=0.6, tag=None):
    u = sm(lin(t, t0, t1))
    base = exterior(cam0 + (cam1 - cam0) * u)
    if tag:
        im = A.label(tag, 54, A.WHITE, 'Bold', stroke=3)
        A.place_c(base, im, W / 2, 380, 1.0, alpha=sm((t - t0 - 0.2) / 0.3))
    return finish(base, t, vig=0.5)


@functools.lru_cache(maxsize=1)
def _hook_band():
    g = np.zeros((520, W, 4), np.uint8)
    g[..., 3] = (np.linspace(200, 0, 520) ** 1.0)[:, None].astype(np.uint8)
    return Image.fromarray(g, 'RGBA')


def hook(base, t):
    """Кадр 0 — уже интрига: вопрос ролика сверху (до 2,6 с)."""
    if t > 2.9:
        return
    a = 1 - sm((t - 2.4) / 0.4)
    band = _hook_band()
    A.paste(base, band, 0, 0, a)
    A.place_c(base, A.label('12 NFT ЗА СУТКИ', 92, A.GOLD, 'Heavy', stroke=5), W / 2, 230, 0.9 + 0.1 * out_back(t / 0.4), alpha=a)
    A.place_c(base, A.label('НО ОН НЕ ДОЧИТАЛ УСЛОВИЕ', 64, A.WHITE, 'Heavy', stroke=4), W / 2, 340,
              0.9 + 0.1 * out_back((t - 0.25) / 0.4), alpha=a * sm((t - 0.2) / 0.2))


def sc_bed(t, t0):
    base = _room_dim_cached(0.62).copy()
    swipe = impulse(t, [ON[1] + 1.25, ON[1] + 1.85], 10)
    glow = A.canvas(900, 700)
    ImageDraw.Draw(glow).ellipse([100, 100, 800, 600], fill=A.rgba(A.GLOW, int(70 + 50 * swipe)))
    A.place_c(base, glow.filter(ImageFilter.GaussianBlur(60)), 520, 1230)
    z = 1.0 + 0.06 * lin(t, t0, t0 + 1.2)
    A.place_c(base, A.kirill_bed(0, blink(t)), W / 2, 1260, 1.05 * z)
    return finish(base, t, vig=0.6)


def sc_feed(t):
    sw = [ON[1] + 2.45, 99]
    pos = 1 + sum(sm((t - s) / 0.28) for s in sw if t > s)
    scr = A.feed_screen(t, pos, '00:00')
    tn = ON[1] + 3.9
    if t > tn:
        nb = A.notif_banner('Неизвестный', 'Каждые два часа ты будешь получать случайный NFT-подарок…')
        y = -nb.height + (nb.height + 70) * out_back((t - tn) / 0.35, 1.2)
        A.paste(scr, nb, 20, y)
    thumb = None
    tap = ON[2] - 0.3
    if t > tap - 0.6:
        pr = 1 if tap <= t < tap + 0.18 else 0
        thumb = (SCR_W_HALF + 60, 160 + (1 - sm((t - tap + 0.6) / 0.5)) * 600, pr)
    elif t < sw[0] + 0.3:
        thumb = (SCR_W_HALF + 80, 1200 - sm((t - sw[0] + 0.25) / 0.3) * 500, 0)
    im = A.phone_pov(scr, t, bg=_room_dim_cached(0.75), thumb=thumb)
    return finish(im, t, vig=0.55)


SCR_W_HALF = A.SCR_W / 2


def msg_reveal(t, a, b):
    return lin(t, a, b)


def sc_chat_intro(t):
    """Чат: печатает → первое сообщение набирается в такт речи; на «одно условие» — сбой."""
    t2 = ON[2]
    items = []
    status = 'печатает…' if t < t2 + 0.5 else 'в сети'
    if t < t2 + 0.5:
        items.append(A.typing_bubble(t))
    else:
        g = impulse(t, [t2 + 4.5], 6, 0.5)
        items.append(A.bubble(TEXT[2], msg_reveal(t, t2 + 0.4, END[2] - 0.3), hl=('условие',) if t > t2 + 4.5 else (), glitch=g * 0.8))
    scr = A.chat_screen(t, items, '00:01', status)
    return finish(A.phone_pov(scr, t, bg=_room_dim_cached(0.75)), t, vig=0.55)


def sc_kirill_greed(t, t0, t1):
    base = _room_dim_cached(0.5).copy()
    rays = _rays()
    A.place_c(base, rays, W / 2, 820, 1.0, rot=t * 8, alpha=0.5)
    for k, p in enumerate(SIDE_GIFTS + [None]):
        ang = t * 0.9 + k * 2 * math.pi / (len(SIDE_GIFTS) + 1)
        x, y = W / 2 + math.cos(ang) * 400, 760 + math.sin(ang) * 170
        if p is None:
            g = lottie.frame(ICE_JSON, t, size=240)
        else:
            g = _png(p)
        A.place_c(base, g, x, y, 0.95 + 0.1 * math.sin(ang), alpha=sm((t - t0 - k * 0.08) / 0.25))
    bust = A.kirill_bust('greed', 0, blink(t), 0, 0)
    A.place_c(base, bust, W / 2, 1180 + (1 - out_back((t - t0) / 0.4)) * 200, 1.15)
    return finish(base, t, vig=0.5)


@functools.lru_cache(maxsize=16)
def _png(p):
    return Image.open(p).convert('RGBA').resize((220, 220), Image.LANCZOS)


@functools.lru_cache(maxsize=1)
def _rays():
    im = A.canvas(1800, 1800)
    d = ImageDraw.Draw(im)
    for k in range(16):
        a0 = k * 2 * math.pi / 16
        d.polygon([(900, 900), (900 + 1300 * math.cos(a0), 900 + 1300 * math.sin(a0)),
                   (900 + 1300 * math.cos(a0 + 0.17), 900 + 1300 * math.sin(a0 + 0.17))], fill=(255, 210, 90, 60))
    return im


def sc_family(t, t0, t1):
    """Флешбэк: семья выставляет Кирилла за дверь (тёплый сепийный свет), дверь захлопывается."""
    base = Image.new('RGBA', (W, H), (40, 30, 34, 255))
    d = ImageDraw.Draw(base)
    d.rectangle([0, 1380, W, H], fill=(60, 46, 44))
    u = lin(t, t0, t1)
    slam = t0 + (t1 - t0) * 0.62
    dx0, dx1 = 560, 900
    door_open = 1 - sm((t - slam + 0.18) / 0.18)
    d.rectangle([dx0 - 10, 520, dx1 + 10, 1390], fill=(90, 70, 60), outline=A.INK, width=8)
    d.rectangle([dx0, 530, dx1, 1384], fill=(255, 214, 150))
    # силуэты семьи в проёме
    if door_open > 0.05:
        for k, (x, hh) in enumerate(((650, 560), (780, 500), (720, 360))):
            d.ellipse([x - 50, 1384 - hh - 90, x + 50, 1384 - hh + 10], fill=(60, 40, 40))
            d.rounded_rectangle([x - 70, 1384 - hh, x + 70, 1384], 40, fill=(60, 40, 40))
        d.line([650 - 60, 1384 - 480, 450, 1384 - 600], fill=(60, 40, 40), width=34)          # «вон!» — указывает
    dw = (dx1 - dx0) * (1 - door_open * 0.85)
    d.rectangle([dx0, 530, dx0 + dw, 1384], fill=A.DOOR, outline=A.INK, width=8)
    # Кирилл вылетает и пятится влево
    kx = 600 - 380 * sm(lin(t, t0, t0 + 0.8))
    A.place_c(base, A.kirill_side('back', int(t * 16) % 16, 'scared'), kx, 1384 - 465, 0.95)
    if t > slam:
        A.place_c(base, A.label('БАХ!', 110, (255, 230, 120), 'Heavy', stroke=6), 780, 470, 0.8 + 0.3 * out_back((t - slam) / 0.25),
                  alpha=1 - sm((t - slam - 0.6) / 0.3))
    base = A.tint(base, (60, 40, 20), 0.18)
    sx, sy = shake(t, 22, [slam])
    return finish(base, t, sx, sy, vig=0.65)


def sc_accept(t):
    items = [A.bubble(TEXT[2], 1.0), (A.buttons_row(('Принять', 'Отклонить'), press=0 if t > END[3] - 0.08 else -1), 'mid')]
    scr = A.chat_screen(t, items, '00:01', 'в сети')
    tap = END[3] - 0.08
    pr = 1 if tap <= t < tap + 0.2 else 0
    thumb = (190, SCR_H_BTN + (1 - sm((t - tap + 0.7) / 0.6)) * 420, pr)
    return finish(A.phone_pov(scr, t, bg=_room_dim_cached(0.75), thumb=thumb), t, vig=0.55)


SCR_H_BTN = A.SCR_H - 150 - 22 - 48


def sc_wait(t):
    items = [A.bubble(TEXT[2], 1.0), (A.buttons_row(('Принято ✓',), press=0, w=420), 'mid'), A.typing_bubble(t)]
    scr = A.chat_screen(t, items, '00:01', 'печатает…')
    z = 1.0 + 0.05 * lin(t, ON[4], STOPS[0])
    return finish(A.phone_pov(scr, t, bg=_room_dim_cached(0.8), scale=z), t, vig=0.6)


COND = [word_t(5, k) for k in (0, 9, 15, 24, 34)] + [END[5]]   # начала 5 фраз условия и конец


def sc_cond_text(t):
    """Фраза 1 условия — длинное сообщение набирается; «Коллекционер» красным; вспышка силуэта."""
    items = [A.bubble(TEXT[2], 1.0), (A.buttons_row(('Принято ✓',), press=0, w=420), 'mid'),
             A.bubble('Следующие 24 часа за тобой будет охотиться Коллекционер.', lin(t, COND[0], COND[1] - 0.6), hl=('Коллекционер',))]
    scr = A.chat_screen(t, items, '00:02', 'в сети')
    im = A.phone_pov(scr, t, bg=_room_dim_cached(0.8), scale=1.0 + 0.04 * lin(t, COND[0], COND[1]))
    flash = impulse(t, [word_t(5, 8)], 4, 0.7)
    if flash > 0.02:
        c = A.collector(eye=1.0)
        A.place_c(im, c, W / 2, H * 0.55, 1.25, alpha=min(1, flash) * 0.55)
        im = A.tint(im, (120, 0, 10), 0.25 * flash)
    return finish(im, t, vig=0.6)


@functools.lru_cache(maxsize=1)
def _map_bg():
    im = Image.new('RGBA', (W, H), (14, 22, 40, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 120):
        d.line([x, 0, x, H], fill=(30, 44, 70), width=10)
    for y in range(0, H, 140):
        d.line([0, y, W, y], fill=(30, 44, 70), width=10)
    rng = np.random.default_rng(4)
    for x in range(0, W, 120):
        for y in range(0, H, 140):
            if rng.random() < 0.8:
                d.rectangle([x + 14, y + 14, x + 106, y + 126], fill=(22, 32, 54))
    d.line([0, 1300, W, 1000], fill=(40, 80, 130), width=40)                    # Волга? — просто река
    return im


def sc_map(t, nft):
    """Фразы 2–3: карта — Коллекционер знает, где ты; с каждым NFT круг поиска сужается."""
    base = _map_bg().copy()
    d = ImageDraw.Draw(base)
    kx, ky = 540, 860
    r_search = 520 - 120 * nft
    pulse = (t * 0.8) % 1
    for k in range(3):
        rr = r_search * (0.4 + 0.6 * ((pulse + k / 3) % 1))
        a = int(160 * (1 - ((pulse + k / 3) % 1)))
        d.ellipse([kx - rr, ky - rr, kx + rr, ky + rr], outline=(255, 60, 70, a), width=8)
    d.ellipse([kx - r_search, ky - r_search, kx + r_search, ky + r_search], outline=(255, 60, 70, 200), width=6)
    A.place_c(base, A.kirill_bust('scared', 0, 0, 0).resize((190, 225)), kx, ky - 30)
    d.ellipse([kx - 22, ky + 70, kx + 22, ky + 114], fill=A.GLOW)
    # Коллекционер — красная точка движется к Кириллу
    ang = 2.3 + 0.2 * math.sin(t)
    dist = 700 - 180 * nft - 30 * (t % 3)
    cx, cy = kx + math.cos(ang) * dist, ky + math.sin(ang) * dist
    d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(255, 40, 50))
    A.place_c(base, A.collector().resize((120, 257)), cx, cy - 150)
    # NFT вокруг Кирилла
    for k in range(int(nft)):
        a0 = -1.2 + k * 1.1
        g = _png(SIDE_GIFTS[k % len(SIDE_GIFTS)])
        A.place_c(base, g, kx + math.cos(a0) * 240, ky + math.sin(a0) * 240, 0.6 * out_back((nft - k) / 0.6))
    return finish(base, t, vig=0.5)


def sc_power(t, t0, t1):
    """Фраза 4: силу подарка можно применить против Коллекционера — но подарок исчезнет навсегда."""
    base = _hall_cached(0.55).copy()
    d = ImageDraw.Draw(base)
    u = lin(t, t0, t1)
    fire = t0 + (t1 - t0) * 0.35
    gone = t0 + (t1 - t0) * 0.62
    A.place_c(base, A.collector(eye=1.0), 820 + 60 * sm((t - fire) / 0.3), 1050, 0.62, rot=-8 * sm((t - fire) / 0.3))
    A.place_c(base, A.kirill_side('push', 0, 'neutral'), 300, 1440 - 470, 1.0)
    gx, gy = 470, 900
    if t < gone + 0.6:
        g = lottie.frame(GIFT_JSON, t, size=220)
        a = 1 - sm((t - gone) / 0.6)
        A.place_c(base, g, gx, gy, 1.0 + 0.1 * math.sin(t * 6), alpha=a)
    if fire <= t < gone + 0.2:
        beam = A.canvas(500, 120)
        ImageDraw.Draw(beam).rounded_rectangle([0, 20, 500, 100], 40, fill=(255, 230, 120, 220))
        A.paste(base, beam.filter(ImageFilter.GaussianBlur(10)), gx + 60, gy - 60, 1 - sm((t - gone) / 0.2))
    if t > gone:                                                                 # подарок рассыпается в искры
        rng = np.random.default_rng(9)
        for k in range(40):
            ang, sp = rng.uniform(0, 6.28), rng.uniform(80, 360)
            dt_ = t - gone
            x, y = gx + math.cos(ang) * sp * dt_, gy + math.sin(ang) * sp * dt_ + 200 * dt_ * dt_
            a = max(0, 1 - dt_ / 1.2)
            d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 220, 100, int(255 * a)))
        big_label(base, 'NFT ИСЧЕЗНЕТ', 360, t, gone, 80, A.RED)
    return finish(base, t, vig=0.55)


def sc_win(t, t0):
    base = _room_dim_cached(0.45).copy()
    A.place_c(base, _rays(), W / 2, 900, 1.0, rot=-t * 10, alpha=0.6)
    for k, p in enumerate(SIDE_GIFTS):
        A.place_c(base, _png(p), 250 + k * 145, 1500 - (k % 2) * 60, 0.9 * out_back((t - t0 - k * 0.07) / 0.3))
    A.place_c(base, A.kirill_bust('greed', 0, blink(t), 0), W / 2, 1060, 1.05)
    big_label(base, '24:00:00', 330, t, t0 + 0.1, 120, A.GOLD)
    return finish(base, t, vig=0.5)


def sc_bust(t, expr, sweat=0, tear=0, bg_k=0.55, z0=1.1, z1=1.18, t0=0.0, t1=1.0, lit=0, look=0.0, think=None):
    base = _room_dim_cached(bg_k).copy() if bg_k < 0.7 else _hall_cached(0.6).copy()
    z = z0 + (z1 - z0) * sm(lin(t, t0, t1))
    m = mouth(t)
    A.place_c(base, A.kirill_bust(expr, m, blink(t, 2), look, lit, sweat, tear), W / 2, 1180, z)
    if think is not None:
        think(base, t)
    return base


def sc_gift(t):
    """Падает Loot Bag: карточка NFT с живой анимацией и подписью модели."""
    tg = ON[6] + 2.25
    items = [A.bubble(TEXT[2], 1.0), (A.buttons_row(('Принято ✓',), press=0, w=420), 'mid')]
    scr = A.chat_screen(t, items, '00:02', 'в сети')
    if t > tg:
        u = out_back((t - tg) / 0.45, 1.4)
        g = lottie.frame(GIFT_JSON, t - tg, size=440)
        card = A.gift_card(g, GIFT[0], GIFT[1], GIFT[2], BACKDROP)
        dim = Image.new('RGBA', scr.size, (0, 0, 0, int(150 * min(1, (t - tg) / 0.3))))
        scr.alpha_composite(dim)
        A.place_c(scr, card, A.SCR_W / 2, A.SCR_H / 2 + 40, 0.3 + 0.7 * u)
        rng = np.random.default_rng(int((t - tg) * 10))
        d = ImageDraw.Draw(scr)
        for k in range(10):
            a0 = rng.uniform(0, 6.28)
            rr = 330 + rng.uniform(0, 60)
            x, y = A.SCR_W / 2 + math.cos(a0) * rr, A.SCR_H / 2 + math.sin(a0) * rr
            A.place_c(scr, _spark(), x, y, rng.uniform(0.4, 1.0), alpha=0.8)
        A.place_c(scr, A.label('НОВЫЙ ПОДАРОК!', 54, A.GOLD, 'Heavy', stroke=3), A.SCR_W / 2, 330, 0.8 + 0.2 * u, alpha=min(1, (t - tg) / 0.2))
    return finish(A.phone_pov(scr, t, bg=_room_dim_cached(0.75)), t, vig=0.5)


@functools.lru_cache(maxsize=1)
def _spark():
    im = A.canvas(60, 60)
    d = ImageDraw.Draw(im)
    d.polygon([(30, 0), (36, 24), (60, 30), (36, 36), (30, 60), (24, 36), (0, 30), (24, 24)], fill=(255, 240, 160))
    return im


def sc_dream(t):
    base = sc_bust(t, 'happy', bg_k=0.5, t0=ON[7], t1=END[7])
    k = sm((t - ON[7] - 1.0) / 0.4)
    if k > 0:
        cloud = A.canvas(560, 520)
        d = ImageDraw.Draw(cloud)
        for (x, y, r) in ((280, 240, 220), (140, 260, 140), (420, 260, 140), (280, 120, 150)):
            d.ellipse([x - r, y - r, x + r, y + r], fill=(245, 245, 255, 235))
        A.place_c(cloud, A.furniture('phone_new'), 280, 260, 0.62, rot=math.sin(t * 2) * 6)
        A.place_c(base, cloud, 760, 480, 0.6 + 0.4 * k, alpha=k)
        A.place_c(base, A.label('ЗАВТРА', 46, A.INK, 'Heavy', shadow=False), 760, 700, 1.0, alpha=k)
        for (x, y, r) in ((560, 760, 30), (500, 840, 18)):
            dd = ImageDraw.Draw(base)
            dd.ellipse([x - r, y - r, x + r, y + r], fill=(245, 245, 255, int(235 * k)))
    return finish(base, t, vig=0.5)


def sc_sell(t):
    t8 = ON[8]
    items = [A.bubble(TEXT[2], 1.0)]
    scr = A.chat_screen(t, items, '00:03', 'в сети')
    dim = Image.new('RGBA', scr.size, (0, 0, 0, 150))
    scr.alpha_composite(dim)
    g = lottie.frame(GIFT_JSON, t, size=440)
    A.place_c(scr, A.gift_card(g, GIFT[0], GIFT[1], GIFT[2], BACKDROP), A.SCR_W / 2, A.SCR_H / 2 - 40, 1.0)
    A.paste(scr, A.buttons_row(('Продать',), press=0 if t > t8 - 0.1 else -1, w=600), 80, A.SCR_H / 2 + 360)
    if t > t8 + 0.1:
        to = A.toast_img('Продажа недоступна', 'Можно продать через 24 часа')
        A.place_c(scr, to, A.SCR_W / 2, 330, 0.7 + 0.3 * out_back((t - t8 - 0.1) / 0.3), alpha=min(1, (t - t8 - 0.1) / 0.15))
    tap = t8 - 0.1
    thumb = (380, A.SCR_H / 2 + 410 + (1 - sm((t - tap + 0.5) / 0.4)) * 300, 1 if tap <= t < tap + 0.2 else 0)
    sx, sy = shake(t, 14, [t8 + 0.1])
    return finish(A.phone_pov(scr, t, bg=_room_dim_cached(0.75), thumb=thumb), t, sx, sy, vig=0.5)


def sc_clock(t, s, t0):
    base = _room_dim_cached(0.85).copy()
    g = impulse(t, [t0], 5, 0.5)
    im = clock_img(s)
    if g > 0.05:
        im = A.glitch_img(im, min(1, g))
    A.place_c(base, im, W / 2, 820, 0.9 + 0.1 * out_back((t - t0) / 0.3))
    A.place_c(base, A.label('НОЧИ', 60, (255, 160, 160), 'Heavy', stroke=3), W / 2, 980, 1.0, alpha=sm((t - t0 - 0.2) / 0.3))
    return finish(base, t, vig=0.6)


def hall(t, cracks=0, door_dx=0.0, shadow=0.0, warp=0.0, light=1.0, tint_k=0.5, police=0.0, barricade=None, jar=None):
    base = _hall_cached(tint_k).copy()
    dimg = A.door_img(min(3, cracks))
    sh = impulse(t, KNOCKS, 14, 0.25) * 5 + impulse(t, BASH, 8, 0.5) * 26 + impulse(t, [BIG], 6, 0.8) * 50
    dx = math.sin(t * 120) * sh + door_dx
    A.paste(base, dimg, 328 + dx, 418)
    if light > 0:
        A.paste(base, A.under_door_light(shadow, warp), 328, 1384, light)
    if police > 0:
        ph = (t * 3.2) % 1
        col = (255, 40, 60) if ph < 0.5 else (60, 110, 255)
        strip = A.canvas(464, 70)
        ImageDraw.Draw(strip).rectangle([0, 40, 464, 70], fill=A.rgba(col, int(220 * police)))
        A.paste(base, strip.filter(ImageFilter.GaussianBlur(6)), 328, 1380)
        base = A.tint(base, col, 0.12 * police)
    if barricade:
        bed_u, ward_u, jar_u = barricade
        if bed_u > 0:
            A.place_c(base, A.furniture('bed'), 560 - (1 - out_back(bed_u, 1.1)) * 900 + dx * 0.3, 1300, 0.95)
        if ward_u > 0:
            A.place_c(base, A.furniture('wardrobe'), 580 + (1 - out_back(ward_u, 1.1)) * 900 + dx * 0.4, 1080, 0.95)
        if jar is None and jar_u > 0:
            A.place_c(base, A.furniture('jar'), 600 + dx * 0.5, 650 - (1 - sm(jar_u)) * 300, 0.85, alpha=min(1, jar_u * 3))
    if jar is not None:
        x, y, rot = jar
        A.place_c(base, A.furniture('jar'), x, y, 0.85, rot)
    return base


def sc_hall_knock(t):
    base = hall(t, shadow=sm((t - ON[10] - 1.3) / 0.4))
    wk0, wk1 = ON[10] + 2.6, END[10] - 0.6
    x = -200 + 430 * sm(lin(t, wk0, wk1))
    pose = 'walk' if wk0 < t < wk1 else 'stand'
    A.place_c(base, A.kirill_side(pose, int(t * 14) % 16, 'neutral'), x, 1440 - 465, 1.0)
    if t > END[10] - 0.4:
        big_label(base, '?!', 600, t, END[10] - 0.4, 90, A.WHITE, 0.8)
    z = 1.0
    return finish(base, t, vig=0.6)


def sc_mom(t, line, claws=False):
    base = hall(t, shadow=1.0, warp=sm((t - (END[line] - 0.6)) / 0.4) if claws else 0.0)
    A.place_c(base, A.kirill_side('stand', 0, 'scared' if claws else 'neutral'), 230, 1440 - 465, 1.0)
    # речь из-за двери — розовый «пузырь» у двери
    txt = TEXT[line]
    a = sm((t - ON[line]) / 0.2) * (1 - sm((t - END[line] - 0.3) / 0.2))
    reveal = lin(t, ON[line], END[line] - 0.2)
    im = speech_bubble(txt[:max(1, int(len(txt) * reveal))], (255, 170, 200), tail='down')
    A.place_c(base, im, 640, 300, 1.0, alpha=a)
    if claws and t > END[line] - 0.6:
        base = A.tint(base, (120, 0, 10), 0.2 * sm((t - END[line] + 0.6) / 0.3))
        big_label(base, '6 ИЮЛЯ', 760, t, END[line] - 0.5, 110, A.RED, 1.0)
    return finish(base, t, vig=0.6)


@functools.lru_cache(maxsize=128)
def speech_bubble(text, col, tail='down'):
    lines = A.wrap(text, 50, 'Bold', 760)
    lh = 64
    w = max(A.font('Bold', 50).getlength(x) for x in lines) + 80
    h = lh * len(lines) + 50
    im = A.canvas(w, h + 50)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 40, fill=A.rgba((252, 246, 250)), outline=A.rgba(col), width=8)
    d.polygon([(w / 2 - 30, h - 4), (w / 2 + 30, h - 4), (w / 2, h + 46)], fill=A.rgba((252, 246, 250)), outline=A.rgba(col))
    for k, ln in enumerate(lines):
        d.text((w / 2, 25 + lh * k + lh / 2), ln, font=A.font('Bold', 50), fill=A.INK, anchor='mm')
    return im


def think_cloud_ice(base, t):
    """Мысль о брате, обменянном на NFT-мороженое: облачко с мороженым."""
    k = sm((t - ON[12] - 0.4) / 0.4)
    if k <= 0:
        return
    cloud = A.canvas(620, 460)
    d = ImageDraw.Draw(cloud)
    for (x, y, r) in ((310, 230, 200), (150, 250, 130), (470, 250, 130), (310, 110, 140)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 240, 255, 230))
    d.ellipse([100, 170, 210, 280], fill=(80, 60, 50))                                   # брат (силуэт)
    d.rounded_rectangle([90, 270, 220, 380], 40, fill=(80, 60, 50))
    for yy, sg in ((240, 1), (300, -1)):                                               # стрелки обмена ⇄
        d.line([(250, yy), (350, yy)], fill=A.INK, width=12)
        hx = 350 if sg > 0 else 250
        d.polygon([(hx, yy - 22), (hx + 30 * sg, yy), (hx, yy + 22)], fill=A.INK)
    g = lottie.frame(ICE_JSON, t, size=230)
    cloud.alpha_composite(g, (360, 130))
    A.place_c(base, cloud, 760, 470, 0.6 + 0.4 * k, rot=math.sin(t * 1.5) * 2, alpha=k)


def sc_think(t, line, expr, cloud=None, pulse=False):
    base = sc_bust(t, expr, bg_k=0.75, z0=1.12, z1=1.2, t0=ON[line], t1=END[line] + 0.3)
    if cloud:
        cloud(base, t)
    if pulse:
        hb = impulse(t, [ON[13] + 0.2 + k * 0.652 for k in range(5)], 6, 0.5)
        base = A.vignette(base, 0.35 * min(1, hb), (90, 0, 10))
    im = finish(base, t, vig=0.6)
    # «эхо» мыслей — лёгкое двоение картинки
    return im


def sc_ask(t):
    base = hall(t, shadow=1.0)
    A.place_c(base, A.kirill_side('stand', 0, 'neutral', mouth(t)), 330, 1440 - 465, 1.0)
    return finish(base, t, vig=0.6)


def sc_back(t):
    t16 = ON[16]
    born = word_t(16, 4)
    if t < born - 0.1:
        base = hall(t, shadow=1.0, warp=1.0)
        x = 330 - 260 * sm(lin(t, t16, t16 + 1.6))
        A.place_c(base, A.kirill_side('back', int(t * 12) % 16, 'scared'), x, 1440 - 465, 1.0)
        return finish(base, t, vig=0.6)
    base = _room_dim_cached(0.6).copy()
    for k, (txt, col, x, rot, ok) in enumerate((('6 ИЮЛЯ', A.RED, 330, -8, False), ('7 АПРЕЛЯ', (90, 200, 120), 750, 6, True))):
        a = sm((t - born - k * 0.35) / 0.25)
        card = calendar_card(txt, col, ok)
        A.place_c(base, card, x, 900, 0.7 + 0.3 * out_back((t - born - k * 0.35) / 0.35), rot, a)
    return finish(base, t, vig=0.55)


@functools.lru_cache(maxsize=4)
def calendar_card(txt, col, ok):
    im = A.canvas(420, 460)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 419, 459], 30, fill=(250, 248, 240), outline=A.INK, width=8)
    d.rounded_rectangle([0, 0, 419, 110], 30, fill=col, outline=A.INK, width=8)
    d.rectangle([4, 80, 415, 110], fill=col)
    for x in (110, 310):
        d.rounded_rectangle([x - 12, -20, x + 12, 40], 10, fill=(80, 80, 90))
    num, mon = txt.split()
    d.text((210, 250), num, font=A.font('Heavy', 180), fill=A.INK, anchor='mm')
    d.text((210, 390), mon, font=A.font('Heavy', 56), fill=A.INK, anchor='mm')
    if not ok:
        d.line([40, 140, 380, 430], fill=A.RED, width=22)
        d.line([380, 140, 40, 430], fill=A.RED, width=22)
    else:
        d.ellipse([300, 120, 400, 220], fill=(255, 210, 90), outline=A.INK, width=5)          # тортик-кружок
        d.text((350, 170), '★', font=A.font('Heavy', 50), fill=A.INK, anchor='mm')
    return im


def sc_luck(t):
    t18 = END[17] - 0.1
    items = [A.bubble(TEXT[2], 1.0), (A.buttons_row(('Принято ✓',), press=0, w=420), 'mid')]
    if t > t18:
        items.append(A.bubble('Удачи', 1.0, emoji=True, time_s='01:38'))
    gone_t = ON[19] + 0.55
    g = impulse(t, [gone_t], 5, 0.4)
    scr = A.chat_screen(t, items, '01:38', 'в сети', gone=sm((t - gone_t) / 0.35))
    if g > 0.05:
        scr = A.glitch_img(scr, min(1, g * 1.2))
    return finish(A.phone_pov(scr, t, bg=_hall_cached(0.8)), t, vig=0.55)


@functools.lru_cache(maxsize=1)
def _stairwell():
    im = Image.new('RGBA', (900, 900), (34, 40, 36, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 620, 900, 900], fill=(60, 56, 50))
    for k in range(6):
        d.rectangle([600 + k * 50, 620 - k * 60, 900, 640 - k * 60], fill=(80, 76, 70), outline=(30, 30, 30), width=3)
    d.rectangle([60, 140, 230, 560], fill=(80, 60, 50), outline=(20, 20, 20), width=6)                      # соседская дверь
    d.ellipse([420, 30, 480, 80], fill=(200, 220, 160))                                                     # тусклая лампа
    return im


def sc_peep(t):
    t20 = ON[20]
    if t < t20 + 0.7:                                             # наезд на глазок
        u = sm(lin(t, t20 - 0.1, t20 + 0.7))
        base = hall(t, shadow=1.0, warp=1.0)
        s = 1 + 5 * u
        cx, cy = 328 + 232, 418 + 314
        base = base.transform((W, H), Image.AFFINE, (1 / s, 0, cx - W / 2 / s, 0, 1 / s, cy - H / 2 / s), Image.BICUBIC)
        return finish(base, t, vig=0.6)
    lean = sm((t - (t20 + 2.95)) / 0.6)
    view = _stairwell().copy()
    sc = 0.36 + 0.22 * lean
    c = A.collector(eye=0.8 + 0.2 * math.sin(t * 6), tilt=int(round(-6 * math.sin(t * 0.7))), lid=0.3 + 0.3 * lean)
    A.place_c(view, c, 450 + 20 * math.sin(t * 0.8), 560 + 60 * lean, sc)
    view = A.tint(view, (0, 20, 10), 0.25)
    fe = A.fisheye(view, 1.0)
    base = Image.new('RGBA', (W, H), (4, 4, 6, 255))
    ring = A.canvas(1000, 1000)
    ImageDraw.Draw(ring).ellipse([0, 0, 999, 999], fill=(0, 0, 0, 0), outline=(40, 36, 30, 255), width=40)
    A.place_c(base, fe.resize((960, 960), Image.BICUBIC), W / 2, H * 0.45)
    A.place_c(base, ring, W / 2, H * 0.45)
    return finish(base, t, *shake(t, 10, [t20 + 2.95]), vig=0.7)


def sc_breathe(t):
    base = hall(t, shadow=0.6)
    hit = BASH[0]
    jump = sm((t - hit) / 0.15)
    x = 360 - 140 * jump
    A.place_c(base, A.kirill_side('stand', 0, 'scared' if t > hit else 'neutral'), x, 1440 - 465 - 40 * math.sin(min(1, max(0, (t - hit) / 0.3)) * math.pi), 1.0)
    if t > hit:
        big_label(base, 'БАМ!', 300, t, hit, 140, (255, 220, 120), 0.7)
    return finish(base, t, *shake(t, 26, BASH), vig=0.6)


def sc_barricade(t):
    t22 = ON[22]
    bar = (lin(t, t22 + 0.0, t22 + 0.45), lin(t, t22 + 0.95, t22 + 1.4), lin(t, t22 + 2.1, t22 + 2.5))
    base = hall(t, barricade=bar, shadow=0.0, light=0.6)
    A.place_c(base, A.kirill_side('push', 0, 'scared'), 150, 1440 - 470, 1.0)
    for k, (s, tt) in enumerate((('КРОВАТЬ!', t22), ('ШКАФ!', t22 + 0.95), ('…ОГУРЦЫ', t22 + 2.1))):
        big_label(base, s, 260 + k * 0, t, tt, 100, (255, 214, 90), 0.75 if k < 2 else 1.2)
    return finish(base, t, *shake(t, 18, BASH), vig=0.6)


def sc_forgot(t):
    base = _room_dim_cached(0.7).copy()
    d = ImageDraw.Draw(base)
    A.place_c(base, A.furniture('bed'), W / 2, 1420, 1.5)
    ph = A.canvas(300, 520)
    dd = ImageDraw.Draw(ph)
    dd.rounded_rectangle([0, 0, 299, 519], 40, fill=(20, 20, 26), outline=A.INK, width=8)
    dd.rounded_rectangle([16, 16, 283, 503], 30, fill=A.BACKDROP_DARK if hasattr(A, 'BACKDROP_DARK') else (40, 30, 70))
    g = lottie.frame(GIFT_JSON, t, size=240)
    ph.alpha_composite(g, (30, 120))
    glow = A.canvas(600, 600)
    ImageDraw.Draw(glow).ellipse([60, 60, 540, 540], fill=(255, 210, 90, int(90 + 60 * math.sin(t * 6))))
    A.place_c(base, glow.filter(ImageFilter.GaussianBlur(50)), W / 2, 1180)
    A.place_c(base, ph, W / 2, 1180, 1.0, rot=-12)
    big_label(base, 'А ПОДАРОК?', 560, t, ON[23] + 0.2, 100, A.GOLD)
    return finish(base, t, *shake(t, 10, BASH), vig=0.6)


def sc_crack(t):
    t23 = ON[23]
    cr = 1 + int(t > t23 + 3.0) + int(t > t23 + 3.6)
    base = hall(t, cracks=cr, barricade=(1, 1, 1), light=0.4, tint_k=0.5)
    A.place_c(base, A.kirill_side('brace', 0, 'scared'), 140, 1440 - 470, 1.0)
    base = A.tint(base, (130, 0, 10), 0.12 * (0.5 + 0.5 * math.sin(t * 9)))
    if t > BIG - 0.02:
        base = A.tint(base, (255, 255, 255), 0.8 * (1 - sm((t - BIG) / 0.25)))
    return finish(base, t, *shake(t, 24, BASH + [BIG]), vig=0.65)


def sc_sirens(t):
    t24 = ON[24]
    neigh = word_t(24, 6)
    quiet = word_t(24, 9)
    if t < neigh - 0.1:
        return finish(exterior(0.15, police=sm((t - BIG) / 1.2), t=t), t, vig=0.5)
    if t < quiet - 0.1:
        return finish(exterior(0.35, police=1.0, t=t, neighbor=1.0), t, vig=0.5)
    base = hall(t, cracks=3, barricade=(1, 1, 1), light=0.4, police=1.0)
    A.place_c(base, A.kirill_side('stand', 0, 'scared'), 150, 1440 - 470, 1.0)
    return finish(base, t, vig=0.6)


def sc_jar(t):
    """Банка падает со шкафа и разбивается (удар — JAR_HIT, как в звуке)."""
    fall0 = JAR_HIT - 0.5
    if t < JAR_HIT:
        u = lin(t, fall0, JAR_HIT)
        x = 600 + 90 * u
        y = 650 + 760 * u * u
        rot = -200 * u
        base = hall(t, cracks=3, barricade=(1, 1, 1), light=0.4, police=0.6, jar=(x, y, rot))
    else:
        base = hall(t, cracks=3, barricade=(1, 1, 0), light=0.4, police=0.4)
        d = ImageDraw.Draw(base)
        dt_ = t - JAR_HIT
        d.ellipse([480, 1440, 920, 1480 + 20 * min(1, dt_ * 2)], fill=(150, 190, 120, 200))
        rng = np.random.default_rng(3)
        for k in range(18):
            ang, sp = rng.uniform(math.pi, 2 * math.pi), rng.uniform(150, 600)
            tt = min(dt_, 0.35)
            x = 700 + math.cos(ang) * sp * tt * 1.4
            y = 1450 + math.sin(ang) * sp * tt + 1800 * tt * tt
            y = min(y, 1470)
            d.polygon([(x, y), (x + 18, y + 8), (x + 6, y + 22)], fill=(200, 230, 210), outline=A.INK)
        for k in range(6):
            x = 560 + k * 60 + rng.uniform(-20, 20)
            d.rounded_rectangle([x, 1440, x + 60, 1470], 14, fill=(70, 130, 60), outline=(30, 60, 30), width=3)
    if t > JAR_HIT and t < JAR_HIT + 1.2:
        big_label(base, 'ДЗЫНЬ!', 380, t, JAR_HIT, 110, (200, 240, 220), 0.8)
    return finish(base, t, *shake(t, 12, [JAR_HIT]), vig=0.6)


def sc_sad(t):
    base = hall(t, cracks=3, light=0.4, police=0.3, barricade=(1, 1, 0))
    d = ImageDraw.Draw(base)
    d.ellipse([480, 1440, 920, 1500], fill=(150, 190, 120, 200))
    for k in range(6):
        x = 560 + k * 60
        d.rounded_rectangle([x, 1440, x + 60, 1470], 14, fill=(70, 130, 60), outline=(30, 60, 30), width=3)
    A.place_c(base, A.kirill_side('kneel', 0, 'sad', mouth(t)), 420, 1440 - 465, 1.0)
    tear = A.canvas(30, 50)
    ImageDraw.Draw(tear).ellipse([0, 10, 30, 50], fill=(140, 200, 255))
    A.paste(base, tear, 470, 1440 - 465 - 150 + ((t * 300) % 140))
    return finish(base, t, vig=0.65)


def sc_clean(t):
    t27 = ON[27]
    base = hall(t, cracks=3, light=1.0)
    A.place_c(base, A.kirill_side('mop', int(t * 10) % 16, 'neutral'), 330 + 40 * math.sin(t * 2), 1440 - 465, 1.0)
    clk = word_t(27, 2)
    if t > clk - 0.1:
        A.place_c(base, clock_img('01:59').resize((440, 140)), W / 2, 260, 0.8 + 0.2 * out_back((t - clk) / 0.3))
    if t > END[27]:
        big_label(base, 'ТУК-ТУК', 600, t, END[27] + 0.1, 100, A.WHITE, 1.0)
    return finish(base, t, *shake(t, 6, KNOCKS), vig=0.6)


def sc_police(t):
    base = hall(t, cracks=3, light=1.0, police=1.0)
    A.place_c(base, A.kirill_side('stand', 0, 'scared'), 230, 1440 - 465, 1.0)
    a = sm((t - ON[28]) / 0.15)
    A.place_c(base, speech_bubble(TEXT[28], (140, 190, 255)), 640, 300, 0.8 + 0.2 * out_back((t - ON[28]) / 0.3), alpha=a)
    return finish(base, t, vig=0.6)


def sc_poll(t):
    t29 = ON[29]
    base = A.tint(hall(t, cracks=3, light=1.0, police=0.6).filter(ImageFilter.GaussianBlur(8)), (6, 6, 14), 0.55)
    left = max(0, 60 - int(t - t29) - 1)
    A.place_c(base, A.label('ДО НОВОГО NFT', 54, A.GOLD, 'Heavy', stroke=3), W / 2, 210, 1.0, alpha=sm((t - t29) / 0.2))
    A.place_c(base, A.label(f'00:{left:02d}', 130, A.WHITE, 'Heavy', stroke=5), W / 2, 330, 1.0, alpha=sm((t - t29) / 0.2))
    q = word_t(29, 6)
    big_label(base, 'ЧТО ДЕЛАТЬ КИРИЛЛУ?', 520, t, q, 72, A.WHITE)
    opts = (('А', 'Открыть дверь'), ('Б', 'Притвориться, что никого нет дома'), ('В', 'Подождать минуту до нового NFT'))
    for k, (ltr, txt) in enumerate(opts):
        t0 = t29 + (3.45, 4.75, 7.1)[k]
        if t < t0:
            continue
        card = option_card(ltr, txt, k)
        x = W / 2 + (1 - out_back((t - t0) / 0.4, 1.2)) * 900
        A.place_c(base, card, x, 760 + k * 240, 1.0)
    cm = t29 + 10.5
    if t > cm:
        big_label(base, 'ПИШИ В КОММЕНТАРИЯХ ↓', 1560, t, cm, 66, (255, 214, 90))
    return finish(base, t, vig=0.5)


@functools.lru_cache(maxsize=4)
def option_card(ltr, txt, k):
    w, h = 940, 200
    im = A.canvas(w, h)
    d = ImageDraw.Draw(im)
    col = [(232, 62, 74), (100, 170, 235), (246, 196, 72)][k]
    d.rounded_rectangle([0, 0, w - 1, h - 1], 40, fill=(24, 26, 44, 240), outline=A.rgba(col), width=8)
    d.ellipse([30, 30, 170, 170], fill=A.rgba(col))
    d.text((100, 100), ltr, font=A.font('Heavy', 90), fill=A.WHITE, anchor='mm')
    lines = A.wrap(txt, 50, 'Bold', w - 240)
    for j, ln in enumerate(lines):
        d.text((210, h / 2 + (j - (len(lines) - 1) / 2) * 60), ln, font=A.font('Bold', 50), fill=A.WHITE, anchor='lm')
    return im


# ================================================================== расписание сцен (время содержания)
def W3(i, k):
    return word_t(i, k)


SCENES = [
    (0.0, ON[1] + 1.1, lambda t: sc_exterior(t, 0.0, ON[1] + 1.1, 0.0, 0.7)),
    (ON[1] + 1.1, ON[1] + 2.2, lambda t: sc_bed(t, ON[1] + 1.1)),
    (ON[1] + 2.2, ON[2], sc_feed),
    (ON[2], END[2] + 0.2, sc_chat_intro),
    (END[2] + 0.2, W3(3, 7) - 0.1, lambda t: sc_kirill_greed(t, END[2] + 0.2, W3(3, 7))),
    (W3(3, 7) - 0.1, W3(3, 13) - 0.1, lambda t: sc_family(t, W3(3, 7) - 0.1, W3(3, 13) - 0.1)),
    (W3(3, 13) - 0.1, W3(3, 23) - 0.15, lambda t: sc_exterior(t, W3(3, 13) - 0.1, W3(3, 23), 0.1, 0.95, 'окраина Саратова')),
    (W3(3, 23) - 0.15, END[3] + 0.1, sc_accept),
    (END[3] + 0.1, COND[0] - 0.05, sc_wait),
    (COND[0] - 0.05, COND[1] - 0.1, sc_cond_text),
    (COND[1] - 0.1, COND[2] - 0.1, lambda t: sc_map(t, 0)),
    (COND[2] - 0.1, COND[3] - 0.1, lambda t: sc_map(t, min(3.0, 3 * lin(t, COND[2], COND[3] - 0.6)))),
    (COND[3] - 0.1, COND[4] - 0.1, lambda t: sc_power(t, COND[3] - 0.1, COND[4] - 0.1)),
    (COND[4] - 0.1, ON[6], lambda t: sc_win(t, COND[4] - 0.1)),
    (ON[6], W3(6, 4) - 0.1, lambda t: finish(sc_bust(t, 'scared', sweat=1, bg_k=0.6, t0=ON[6], t1=W3(6, 4)), t, vig=0.6)),
    (W3(6, 4) - 0.1, W3(6, 11) - 0.05, sc_gift),
    (W3(6, 11) - 0.05, ON[7], lambda t: finish(sc_bust(t, 'greed', bg_k=0.5, t0=W3(6, 11), t1=ON[7]), t, vig=0.5)),
    (ON[7], ON[8] - 0.05, sc_dream),
    (ON[8] - 0.05, ON[9], sc_sell),
    (ON[9], END[9] + 0.15, lambda t: finish(sc_bust(t, 'sad', bg_k=0.6, t0=ON[9], t1=END[9]), t, vig=0.6)),
    (END[9] + 0.15, W3(10, 3) - 0.1, lambda t: sc_clock(t, '01:37', END[9] + 0.15)),
    (W3(10, 3) - 0.1, ON[11] - 0.1, sc_hall_knock),
    (ON[11] - 0.1, ON[12], lambda t: sc_mom(t, 11)),
    (ON[12], ON[13], lambda t: sc_think(t, 12, 'hope', think_cloud_ice)),
    (ON[13], ON[14], lambda t: sc_think(t, 13, 'sus', None, pulse=True)),
    (ON[14], ON[15], sc_ask),
    (ON[15], ON[16], lambda t: sc_mom(t, 15, claws=True)),
    (ON[16], ON[17], sc_back),
    (ON[17], ON[20] - 0.1, sc_luck),
    (ON[20] - 0.1, ON[21], sc_peep),
    (ON[21], ON[22] - 0.05, sc_breathe),
    (ON[22] - 0.05, ON[23], sc_barricade),
    (ON[23], W3(23, 6) - 0.1, sc_forgot),
    (W3(23, 6) - 0.1, BIG + 0.35, sc_crack),
    (BIG + 0.35, JAR_HIT - 0.55, sc_sirens),
    (JAR_HIT - 0.55, ON[26], sc_jar),
    (ON[26], ON[27], sc_sad),
    (ON[27], ON[28] - 0.05, sc_clean),
    (ON[28] - 0.05, ON[29], sc_police),
    (ON[29], DUR + 1, sc_poll),
]
XFADE = 0.14


def render_scene(t):
    for k, (a, b, f) in enumerate(SCENES):
        if a <= t < b:
            return k, f(t)
    return len(SCENES) - 1, SCENES[-1][2](t)


def render_at(t):
    k, im = render_scene(t)
    a = SCENES[k][0]
    if k > 0 and t - a < XFADE:                                   # мягкий стык сцен
        prev = SCENES[k - 1][2](t)
        im = Image.blend(prev, im, sm((t - a) / XFADE))
    hook(im, t)
    draw_caption(im, t)
    return np.asarray(im.convert('RGB')).copy()


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
