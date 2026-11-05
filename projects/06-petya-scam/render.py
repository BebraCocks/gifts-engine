"""06-petya-scam «Петя и NFT», часть 1 — picture. A frame is a pure function of content time t.

Every Telegram conversation is shown inside the phone (tg.py): first the character in his/her place, then the
camera flies into the phone — only the hands and the screen are seen (author's brief, 2026-11-05).
3D moments: the loot tunnel after RubUp 1, the AI «assembling» Alexander as a hologram, the last message
on a phone floating in the dark.
"""
import functools
import math
import random
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import banner
import config
import frames
import fx
import gifts_api as G
import lottie
import chars as C
import sets as S
import screens as SC
import stage
import tg
from art import Layer, shade
from tg import blocked, draft, gift, msg, note, typing
from timeline import DUR, ON, END, KEY, TAKES, HAS_NARRATION
from words import WORDS
from events import AD1, AD2, T
from script import LINES

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([AD1, AD2], cy=H / 2, speed=1.1)


# ------------------------------------------------------------------ helpers
def ramp(t, a, b):
    return fx.clamp01((t - a) / (b - a)) if b > a else float(t >= a)


def sm(x):
    return fx.smooth(x)


def eo(x):
    return fx.ease_out(fx.clamp01(x))


def pop(t, t0, d=0.4):
    return fx.ease_out_back(ramp(t, t0, t0 + d)) if t >= t0 else 0.0


def lerp(a, b, k):
    return a + (b - a) * k


def blink(t, seed=0.0, every=3.1):
    p = (t + seed * 1.7) % every
    return max(0.0, 1 - abs(p - 0.08) / 0.08) if p < 0.16 else 0.0


@functools.lru_cache(None)
def _env(k):
    with wave.open(str(TAKES[k])) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        sr = w.getframerate()
    hop = sr // 100
    e = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    return e / (np.percentile(e, 95) + 1e-6)


def talk(t, keys):
    if not HAS_NARRATION:
        return 0.0
    for key in keys:
        k = KEY[key]
        if ON[k] <= t < END[k]:
            e = _env(k)
            i = int((t - ON[k]) * 100)
            return float(np.clip(e[min(i, len(e) - 1)] * 0.85, 0, 1))
    return 0.0


def put(canvas, im, x, y, a=1.0, scale=1.0, rot=0.0):
    if a <= 0.01 or scale <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if a < 1.0:
        im = im.copy()
        im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    stage._paste_clip(canvas, im, x - im.width / 2, y - im.height / 2)


@functools.lru_cache(maxsize=64)
def _glow_spr(r, rgb):
    n = 2 * r
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2
    im = np.zeros((n, n, 4), np.uint8)
    im[..., :3] = rgb
    im[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(im, 'RGBA')


def glow(canvas, x, y, r, rgb, a):
    if a > 0.01:
        put(canvas, _glow_spr(int(r), tuple(rgb)), x, y, a)


def zoom_view(im, fx_, fy, k, rot=0.0):
    """Camera: look at (fx_, fy) with zoom k (1 = whole frame)."""
    if abs(k - 1) < 1e-3 and not rot and abs(fx_ - W / 2) < 0.5 and abs(fy - H / 2) < 0.5:
        return im
    w, h = W / k, H / k
    x0 = min(max(fx_ - w / 2, 0), W - w) if k >= 1 else fx_ - w / 2
    y0 = min(max(fy - h / 2, 0), H - h) if k >= 1 else fy - h / 2
    out = im.transform((W, H), Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BILINEAR)
    if rot:
        out = out.rotate(rot, resample=Image.BILINEAR, fillcolor=(0, 0, 0, 255))
    return out


def radial_blur(im, cx, cy, k):
    if k < 0.02:
        return im
    out = im
    for j, s in enumerate((1.02, 1.045, 1.07)):
        s = 1 + (s - 1) * k * 3
        z = zoom_view(im, cx, cy, s)
        out = Image.blend(out, z, 0.5 / (j + 1))
    return out


def text_spr(text, size, rgb=(255, 255, 255), weight='Heavy', stroke=9, srgb=(16, 12, 22)):
    return _text_spr(text, size, tuple(rgb), weight, stroke, tuple(srgb))


@functools.lru_cache(maxsize=128)
def _text_spr(text, size, rgb, weight, stroke, srgb):
    f = fx.font(weight, size)
    w = int(f.getlength(text)) + 2 * stroke + 40
    h = int(size * 1.5) + 2 * stroke
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((w / 2, h / 2), text, font=f, fill=rgb + (255,), anchor='mm', stroke_width=stroke,
                            stroke_fill=srgb + (255,))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
    out = Image.new('RGBA', (w, h + 10), (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 8))
    out.alpha_composite(im)
    return out


@functools.lru_cache(maxsize=32)
def chip(text, rgb=(255, 255, 255), bg=(20, 18, 30)):
    f = fx.font('Heavy', 44)
    w = int(tg.text_width(text, f)) + 64
    im = Image.new('RGBA', (w, 84), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 83], 42, fill=bg + (225,))
    tg.draw_text(im, (32, 14), text, f, rgb)
    return im


def gift_live(name, model, t, size=300, offset=0.0):
    return lottie.frame(str(G.model_file(name, model, 'json')), max(0.0, t) + offset, size=size)


# ------------------------------------------------------------------ characters
def person(canvas, who, x, y, scale, t, arms='down', glow_=0.0, talk_keys=(), tilt=0.0, bob=0.0, seed=0.0,
           **expr):
    o = talk(t, talk_keys) if talk_keys else 0.0
    if o > 0:
        expr['open_'] = max(expr.get('open_', 0.0), 0.15 + 0.6 * o)
    expr.setdefault('blink', blink(t, seed))
    hd = C.head(who, glow=glow_, **expr)
    bd = C.BODIES[who](arms=arms, glow=round(glow_ * 4) / 4)
    C.place(canvas, C.bust(hd, bd, x, y, scale=scale, tilt=tilt, bob=bob))


def phone_point(x, y, scale):
    """Screen position of the phone in a bust with arms='phone' (neck pivot at x, y)."""
    return x, y + 385 * scale


# ------------------------------------------------------------------ the phone in hands (POV)
PH_S = 0.6
PH_C = (540, 900)
PW, PHH = int(980 * PH_S), int(1880 * PH_S)
X0, Y0, X1, Y1 = PH_C[0] - PW // 2, PH_C[1] - PHH // 2, PH_C[0] + PW // 2, PH_C[1] + PHH // 2


@functools.lru_cache(maxsize=64)
def _hands(tl, tr, sleeve, back=False):
    """Petya's hands holding the phone (frame coordinates). back=True: sleeves + palms behind the phone;
    back=False: palm heels over the lower corners and the thumbs over the screen."""
    P = C.PETYA
    L = Layer(W, H, ss=2)
    sk, sh = P['skin'], P['sh']
    cuff = shade(sleeve, 0.85)
    for s, (tx, ty) in ((-1, tl), (1, tr)):
        f = (lambda x: x) if s < 0 else (lambda x: 2 * 540 - x)  # mirror left-hand geometry for the right hand
        if back:
            # forearm in the sleeve, diagonally from the bottom corner to the wrist
            L.shape([(f(-120), H + 80), (f(-60), 1800), (f(60), 1690), (f(200), 1660), (f(300), 1740),
                     (f(330), H + 80)], sleeve)
            L.stroke([(f(10), 1760), (f(250), 1700)], 30, cuff)
            # palm along the lower half of the phone side (most of it is hidden behind the phone)
            pm = L.shape([(f(120), 1730), (f(140), 1560), (f(178), 1400), (f(210), 1270), (f(236), 1175),
                          (f(262), 1160), (f(330), 1420), (f(320), 1720)], sk)
            L.shape([(f(120), 1730), (f(140), 1560), (f(178), 1400), (f(205), 1300), (f(205), 1560),
                     (f(180), 1740)], sh, clip=pm, alpha=0.5)
            L.ell(f(238), 1168, 20, 26, sk)                      # index knuckle at the phone edge
            continue
        # base of the thumb over the lower corner of the phone
        hm = L.shape([(f(190), 1600), (f(205), 1470), (f(250), 1405), (f(318), 1395), (f(366), 1440),
                      (f(352), 1530), (f(290), 1600)], sk)
        L.shape([(f(190), 1600), (f(205), 1470), (f(235), 1430), (f(250), 1600)], sh, clip=hm, alpha=0.45)
        # the thumb: tapering, slightly bent towards the tip
        bx, by = f(318), 1425
        dx, dy = tx - bx, ty - by
        ln = max(1.0, math.hypot(dx, dy))
        nx, ny = -dy / ln, dx / ln
        mx_, my_ = bx + dx * 0.55 + nx * 10 * s, by + dy * 0.55 + ny * 10 * s
        pts = [(bx + nx * 27, by + ny * 27), (mx_ + nx * 23, my_ + ny * 23), (tx + nx * 19, ty + ny * 19),
               (tx + dx / ln * 18, ty + dy / ln * 18),
               (tx - nx * 19, ty - ny * 19), (mx_ - nx * 23, my_ - ny * 23), (bx - nx * 27, by - ny * 27)]
        tm = L.shape(pts, sk)
        L.shape([(bx - nx * 27, by - ny * 27), (mx_ - nx * 23, my_ - ny * 23), (mx_ - nx * 8, my_ - ny * 8),
                 (bx - nx * 6, by - ny * 6)], sh, clip=tm, alpha=0.45)
        L.shape([(tx + nx * 12 - dx / ln * 2, ty + ny * 12 - dy / ln * 2), (tx + dx / ln * 12, ty + dy / ln * 12),
                 (tx - nx * 12 - dx / ln * 2, ty - ny * 12 - dy / ln * 2), (tx - dx / ln * 14, ty - dy / ln * 14)],
                (252, 236, 228), alpha=0.9)
        L.stroke([(mx_ - dx / ln * 20 + nx * 14, my_ - dy / ln * 20 + ny * 14),
                  (mx_ - dx / ln * 20 - nx * 6, my_ - dy / ln * 20 - ny * 6)], 3, sh, alpha=0.6)   # knuckle crease
    return L.image()


def _ky(row):
    return Y0 + (20 + tg.SCREEN[1] - tg.KB_H + 18 + row * 118 + 48) * PH_S


TAPS_L = [(320, 0), (400, 1), (350, 2), (450, 0), (300, 1)]
TAPS_R = [(760, 0), (680, 1), (720, 2), (620, 0), (780, 1)]


def thumbs(t, typing_on, kb):
    if typing_on:
        k = int(t * 11)
        if k % 2 == 0:
            x, r = TAPS_L[(k * 3) % 5]
            return (x, _ky(r)), (740, 1330)
        x, r = TAPS_R[(k * 7 + 1) % 5]
        return (340, 1330), (x, _ky(r))
    y = 1360 - 60 * kb
    return (360, y), (720, y)


@functools.lru_cache(maxsize=8)
def environment(mode):
    """Petya's surroundings behind the phone: his room + desk, slightly out of focus."""
    im = S.room(mode).copy()
    im.alpha_composite(S.desk(mode))
    im = im.filter(ImageFilter.GaussianBlur(5))
    a = np.asarray(im, np.float32)
    a[..., :3] *= 0.82
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


@functools.lru_cache(maxsize=1)
def _phone_shadow():
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([X0 + 20, Y0 + 40, X1 + 30, Y1 + 50], 80, fill=(0, 0, 0, 120))
    return sh.filter(ImageFilter.GaussianBlur(30))


def pov(t, chat=None, screen=None, bg=None, zoom=1.0, focus=None, sleeve=None, shake=0.0, dark=0.0):
    sleeve = sleeve or C.PETYA['cloth']
    base = bg if bg is not None else environment('night')
    bobx = 5 * math.sin(t * 1.3) + shake * math.sin(t * 61)
    boby = 7 * math.sin(t * 0.9 + 1) + shake * math.cos(t * 53)
    im = base.copy()
    if screen is None:
        screen = tg.chat_screen(t, chat)
    typing_on, kb = False, 0.0
    if chat is not None:
        typing_on = any(e['k'] == 'draft' and e['t'] <= t < e['t1'] for e in chat['events'])
        kb = tg.kb_open(t, chat['events'])
    dev = tg.phone(screen).resize((PW, PHH), Image.BILINEAR)
    rig = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rig.alpha_composite(_phone_shadow())
    rig.alpha_composite(_hands((0, 0), (0, 0), sleeve, back=True))
    glow(rig, PH_C[0], PH_C[1], 560, (140, 180, 255), 0.12)
    rig.alpha_composite(dev, (X0, Y0))
    lt, rt = thumbs(t, typing_on, kb)
    q = lambda p: (round(p[0] / 10) * 10, round(p[1] / 10) * 10)
    rig.alpha_composite(_hands(q(lt), q(rt), sleeve))
    stage._paste_clip(im, rig, bobx, boby)
    if dark > 0:
        im = Image.blend(im, Image.new('RGBA', (W, H), (0, 0, 0, 255)), dark)
    if zoom != 1.0 or focus:
        fxp, fyp = focus or PH_C
        im = zoom_view(im, fxp, fyp, zoom)
    return im


def screen_y(sy):
    """Screen-space y (0..1840) → frame y in POV."""
    return Y0 + (20 + sy) * PH_S


# ------------------------------------------------------------------ avatars & chats
AV_DIMA = tg.head_avatar(C.head('dima', smile=0.6), bg=(150, 200, 160))
AV_KATYA = tg.head_avatar(C.head('katya', smile=0.6), bg=(240, 190, 190))
AV_PETYA = tg.head_avatar(C.head('petya', smile=0.5), bg=(120, 170, 230))
AV_BOSS = tg.circle(C.avatar('boss', 240), 240)
AV_UNKNOWN = tg.circle(C.avatar('unknown', 240), 240)

CHAT_BOSS = dict(theme='day', name='Друг', status='в сети', avatar=AV_BOSS, clock='18:40', events=[
    msg(T['buzz'], 'in', 'Есть тема 💸', '18:40'),
    msg(T['fly1'] + 0.25, 'in', 'Пишешь людям, втираешься в доверие и уговариваешь отдать NFT-подарки', '18:40'),
    msg(T['fly1'] + 1.0, 'in', 'Всё просто 😎', '18:41'),
    draft(ON[KEY['try']] + 0.05, ON[KEY['try']] + 1.5, 'Звучит как развод 🤨'),
    msg(ON[KEY['try']] + 1.55, 'out', 'Звучит как развод 🤨', '18:41'),
    typing(ON[KEY['try']] + 1.7, ON[KEY['try']] + 2.3),
    msg(ON[KEY['try']] + 2.3, 'in', 'Кто не рискует — тот без подарков 🎁', '18:42'),
    draft(ON[KEY['try']] + 2.5, END[KEY['try']] - 0.05, 'Ладно, попробую'),
    msg(END[KEY['try']], 'out', 'Ладно, попробую', '18:42'),
])

CHAT_DIMA = dict(theme='day', name='Дима', status='в сети', avatar=AV_DIMA, clock='16:05', events=[
    msg(-9, 'out', 'Привет! Видел у тебя календарь в профиле 🔥', '16:02'),
    msg(-8, 'in', 'Привет) да, мама подарила 😊', '16:03'),
    draft(ON[KEY['ask']] + 0.05, T['ask_sent'] - 0.05, 'Слушай, скинь на 5 минут? Скрин для канала сделаю и сразу верну 🙏'),
    msg(T['ask_sent'], 'out', 'Слушай, скинь на 5 минут? Скрин для канала сделаю и сразу верну 🙏', '16:03'),
    typing(T['ask_sent'] + 0.1, T['dima_reply']),
    msg(T['dima_reply'], 'in', 'Ну ладно… только правда верни 🥺', '16:04'),
    gift(T['calendar'], 'in', 'Desk Calendar', 'Sunshine', 'Sky Blue', 'Дима отправил вам подарок'),
    draft(ON[KEY['loser']] - 0.1, T['loser_sent'] - 0.05, 'Спасибо, лошара 😂'),
    msg(T['loser_sent'], 'out', 'Спасибо, лошара 😂', '16:05'),
    blocked(T['block1']), note(T['block1'], 'Вы заблокировали пользователя'),
])

GIFTS_K = [('Plush Pepe', 'Tropical', 'Pure Gold'), ('Resistance Dog', 'Caesar', 'Emerald'),
           ('Heart Locket', 'Royal Flush', 'Raspberry')]
MOCK = ('Какая же ты наивная, ха-ха 😂 Всё это время никакого Александра не существовало. Это был обман. '
        'Ну а теперь прощай! А я пойду пробовать вкус роскошной жизни 😎')


def _transfer_overlay(im, t):
    SC.transfer_sheet(im, t, T['transfer'], T['transfer_done'], [(g[0], g[1]) for g in GIFTS_K], AV_PETYA)


CHAT_K = dict(theme='night', name='Катя', status='в сети', avatar=AV_KATYA, back='Чаты',
              clock=[(-99, '21:03'), (T['date_msg'] - 0.5, '23:12'), (T['cancel'], '23:40'), (T['lie'], '23:44'),
                     (T['help'], '23:45'), (T['all_msg'], '23:47'), (AD2, '23:50'), (T['five'], '23:55'),
                     (T['ten'], '00:00')],
              overlays=[_transfer_overlay], events=[
    msg(T['chat_k'], 'out', 'Привет! Кажется, мы любим одни и те же места 🙂', '21:03'),
    msg(T['chat_k'] + 0.22, 'in', 'Ого, правда? 😊', '21:05'),
    msg(T['chat_k'] + 0.44, 'out', 'Правда) Может, встретимся в субботу?', '22:58'),
    typing(T['chat_k'] + 0.6, T['date_msg']),
    msg(T['date_msg'], 'in', 'С радостью! Жду не дождусь субботы 🥰', '23:12'),
    draft(T['fly_cancel'] + 0.05, T['cancel_sent'] - 0.05,
          'Кать, прости пожалуйста, но я не смогу приехать на свидание 😔'),
    msg(T['cancel_sent'], 'out', 'Кать, прости пожалуйста, но я не смогу приехать на свидание 😔', '23:40'),
    typing(T['cancel_sent'] + 0.1, T['why_msg']),
    msg(T['why_msg'], 'in', 'Почему? Что-то случилось? Мы ведь уже договорились!', '23:41'),
    draft(T['lie'] + 0.05, T['lie_sent'] - 0.05, 'Начальник подставил меня. Теперь я скрываюсь от полиции 🚔 '
          'Все накопления уже потратил… Придётся жить на улице 😢'),
    msg(T['lie_sent'], 'out', 'Начальник подставил меня. Теперь я скрываюсь от полиции 🚔 Все накопления уже '
        'потратил… Придётся жить на улице 😢', '23:44'),
    typing(T['lie_sent'] + 0.2, T['help_msg']),
    msg(T['help_msg'], 'in', 'Блин, чего же ты раньше молчал?! Сейчас помогу, чем смогу!', '23:45'),
] + [gift(tt, 'in', n, m, b, 'Катя отправила вам подарок') for tt, (n, m, b) in zip(T['gifts'], GIFTS_K)] + [
    msg(T['all_msg'], 'in', 'Вот, держи. Это всё, что у меня было ❤️ Надеюсь, тебе поможет', '23:47'),
    draft(T['mock_draft'], T['mock_sent'] - 0.05, MOCK),
    msg(T['mock_sent'], 'out', MOCK, '23:50'),
    tg.status(T['mock_sent'] + 0.6, 'была только что'),
    blocked(T['block2']), note(T['block2'], 'Вы заблокировали пользователя'),
])

CHAT_X = dict(theme='night', name='Неизвестный', status='был(а) недавно', avatar=AV_UNKNOWN, clock='02:13',
              events=[msg(0.0, 'in', 'Зря ты это сделал, Петя.', '02:13')])


def chat_x(t0):
    c = dict(CHAT_X)
    c['events'] = [msg(t0, 'in', 'Зря ты это сделал, Петя.', '02:13')]
    return c


# ------------------------------------------------------------------ scene pieces
def room_scene(t, mode, who_kw, scale=1.25, neck=(540, 1010), cam=None, desk_=True, extra=None):
    im = S.room(mode).copy()
    person(im, 'petya', neck[0], neck[1], scale, t, **who_kw)
    if extra:
        extra(im)
    if desk_:
        im.alpha_composite(S.desk(mode))
    if cam:
        im = zoom_view(im, *cam)
    return im


def fly_out(im, t, tc, px, py, d=0.42):
    """Camera rushes into the phone at (px, py) before the cut at tc."""
    k = ramp(t, tc - d, tc)
    if k <= 0:
        return im
    e = k * k
    c = min(1.0, math.sqrt(e) * 1.4)
    out = zoom_view(im, lerp(W / 2, px, c), lerp(H / 2, py, c), 1 + 3.2 * e)
    out = radial_blur(out, W / 2, H / 2, e)
    return Image.blend(out, Image.new('RGBA', (W, H), (235, 245, 255, 255)), 0.55 * max(0, k - 0.6) / 0.4)


def fly_in(t, tc, d=0.38):
    """(zoom, blur, flash) for the first moments of a POV shot after a fly."""
    k = ramp(t, tc, tc + d)
    if k >= 1:
        return 1.0, 0.0, 0.0
    e = eo(k)
    return 1 + 0.55 * (1 - e), 1 - e, 0.5 * (1 - k)


def pov_shot(t, chat, t0, bg, fly=True, **kw):
    z, b, fl = fly_in(t, t0) if fly else (1.0, 0.0, 0.0)
    im = pov(t, chat, bg=bg, zoom=kw.pop('zoom', 1.0) * z, **kw)
    if b:
        im = radial_blur(im, W / 2, H / 2, b)
    if fl:
        im = Image.blend(im, Image.new('RGBA', (W, H), (235, 245, 255, 255)), fl)
    return im


def whip(im, k):
    if k <= 0.01:
        return im
    a = np.asarray(im.convert('RGB'), np.float32)
    n = int(2 + 16 * k)
    out = np.zeros_like(a)
    for j in range(n):
        out += np.roll(a, int((j - n / 2) * 10 * k), axis=1)
    return Image.fromarray((out / n).astype(np.uint8), 'RGB').convert('RGBA')


def confetti(im, t, t0, n=70, seed=3):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(im)
    for _ in range(n):
        x0 = rnd.uniform(0, W)
        sp = rnd.uniform(160, 340)
        ph = rnd.uniform(0, 30)
        y = (rnd.uniform(-H, 0) + (t - t0 + ph) * sp) % (H + 200) - 100
        x = x0 + 40 * math.sin((t + ph) * 2.2)
        c = rnd.choice([(255, 80, 120), (80, 200, 255), (255, 210, 70), (140, 255, 140), (190, 120, 255)])
        a = (t + ph) * 5
        w_, h_ = 14 * abs(math.cos(a)) + 3, 22
        d.polygon([(x - w_, y - h_ / 2), (x + w_, y - h_ / 2), (x + w_, y + h_ / 2), (x - w_, y + h_ / 2)], fill=c)


def floating_gift(im, t, name, model, x, y, size, label=None, t0=0.0, a=1.0):
    k = pop(t, t0, 0.5)
    if k <= 0:
        return
    glow(im, x, y, size * 0.7, (255, 230, 150), 0.5 * a)
    g = gift_live(name, model, t - t0, 420)
    put(im, g, x, y + 10 * math.sin(t * 2), a=a, scale=size / 420 * k)
    if label:
        put(im, chip(label, bg=(30, 60, 110)), x, y + size * 0.62, a=a * ramp(t, t0 + 0.2, t0 + 0.5))


# ------------------------------------------------------------------ shots
PARTY_BG = None


def party_bg_blur():
    return environment('party')


def shot_hook(t):
    z = 1.12 + 0.2 * sm(ramp(t, 0.2, T['shock']))
    im = pov(t, chat_x(T['hook_msg']), bg=party_bg_blur(), zoom=z, focus=(520, screen_y(1500)), shake=2)
    im = Image.blend(im, Image.new('RGBA', (W, H), (255, 255, 255, 255)), 0.7 * (1 - ramp(t, 0, 0.25)))
    return im


def _party_lights(im, t, k=1.0):
    for j, (c, ph) in enumerate((((255, 60, 180), 0.0), ((60, 200, 255), 1.7), ((255, 200, 60), 3.1))):
        x = 540 + 420 * math.sin(t * 0.9 + ph)
        y = 600 + 300 * math.cos(t * 0.7 + ph * 1.3)
        glow(im, x, y, 520, c, 0.28 * k)


def shot_shock(t, t_rev=None):
    im = S.room('party').copy()
    _party_lights(im, t)
    shake = 6 * (1 - ramp(t, T['shock'], T['shock'] + 0.6))
    person(im, 'petya', 540 + shake * math.sin(t * 70), 1060, 1.9, t, arms='phone', glow_=1.0,
           shock=1.0, open_=0.5, smile=-0.6, sweat=1.0, look=(0, 0.5))
    k = 1.0 + 0.12 * ramp(t, T['shock'], T['rewind'])
    im = zoom_view(im, 540, 820, k)
    red = 0.25 + 0.1 * math.sin(t * 9)
    im = Image.blend(im, Image.new('RGBA', (W, H), (200, 20, 40, 255)), red * ramp(t, T['shock'], T['shock'] + 0.3))
    return im


def shot_rewind(t):
    # time runs back over the shock shot, VHS lines, then the caption
    k = ramp(t, T['rewind'], T['room'])
    back = T['rewind'] - 2.4 * sm(k)
    im = shot_shock(max(T['shock'], back))
    im = whip(im, 0.4 + 0.3 * math.sin(t * 20) ** 2)
    a = np.asarray(im.convert('RGB'), np.float32)
    g = a.mean(2, keepdims=True)
    a = a * 0.4 + g * 0.6
    rnd = np.random.default_rng(int(t * 60))
    for _ in range(5):
        y, hb = int(rnd.uniform(0, H - 40)), int(rnd.uniform(6, 30))
        a[y:y + hb] = np.roll(a[y:y + hb], int(rnd.uniform(-60, 60)), 1)
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    put(im, text_spr('НЕСКОЛЬКО МЕСЯЦЕВ НАЗАД', 66), 540, 900, a=ramp(t, T['rewind'] + 0.2, T['rewind'] + 0.45))
    put(im, text_spr('◀◀', 110, rgb=(255, 255, 255)), 540, 760, a=0.6 + 0.4 * (int(t * 4) % 2))
    im = Image.blend(im, Image.new('RGBA', (W, H), (255, 255, 255, 255)), 0.8 * ramp(t, T['room'] - 0.15,
                                                                                         T['room']))
    return im


def shot_room(t):
    buzz = ramp(t, T['buzz'], T['buzz'] + 0.1)
    look = (0.0, -0.2) if t < T['buzz'] else (0.0, 0.7)
    sad = 0.35 * (1 - buzz)
    sh = 5 * math.sin(t * 80) * (ramp(t, T['buzz'], T['buzz'] + 0.05) - ramp(t, T['buzz'] + 0.3, T['buzz'] + 0.4))

    def ex(im):
        px, py = phone_point(540, 1010, 1.25)
        glow(im, px, py, 300, (150, 210, 255), 0.6 * buzz)
        if t >= T['buzz']:
            put(im, chip('Друг: Есть тема 💸', bg=(30, 40, 60)), px, py - 230, a=pop(t, T['buzz'], 0.35))
    k = 1.0 + 0.08 * ramp(t, T['room'], T['buzz'])
    im = room_scene(t, 'eve', dict(arms='phone', glow_=buzz, sad=sad, smile=0.0 if t < T['buzz'] else 0.25,
                                   brow=0.6 * buzz, look=look, bob=sh), extra=ex, cam=(540, 1000, k))
    if t < T['room'] + 2.4:
        put(im, chip('Петя, 16'), 540, 300, a=ramp(t, T['room'] + 0.2, T['room'] + 0.5) *
            (1 - ramp(t, T['room'] + 2.0, T['room'] + 2.4)))
    px, py = phone_point(540, 1010, 1.25)
    return fly_out(im, t, T['fly1'], px, (py - 1000) * k + 960)


def shot_boss(t):
    return pov_shot(t, CHAT_BOSS, T['fly1'], environment('eve'))


def shot_dima(t):
    im = S.dima_room().copy()
    person(im, 'dima', 420, 1080, 1.2, t, arms='phone', glow_=0.5, smile=0.75, look=(0.6, -0.3))
    floating_gift(im, t, 'Desk Calendar', 'Sunshine', 830, 620, 330, label='NFT-календарь', t0=T['dima'] + 0.25)
    put(im, chip('Дима, 13'), 420, 300, a=ramp(t, T['dima'] + 0.1, T['dima'] + 0.4))
    im = zoom_view(im, 560, 960, 1.0 + 0.06 * ramp(t, T['dima'], T['to_dima_chat']))
    return whip(im, ramp(t, T['to_dima_chat'] - 0.2, T['to_dima_chat']))


def shot_dima_chat(t):
    im = pov_shot(t, CHAT_DIMA, T['to_dima_chat'], environment('eve'))
    im = whip(im, 1 - ramp(t, T['to_dima_chat'], T['to_dima_chat'] + 0.2))
    if T['calendar'] <= t < T['calendar'] + 0.8:          # the gift arrives: a flash of light
        glow(im, 540, 1150, 500, (255, 230, 150), 0.6 * (1 - ramp(t, T['calendar'], T['calendar'] + 0.8)))
    return im


def shot_dima_cry(t):
    im = S.dima_room().copy()
    person(im, 'dima', 540, 1000, 1.7, t, arms='phone', glow_=0.6, shock=1.0, sad=0.9, open_=0.6, smile=-0.7,
           sweat=1.0 * ramp(t, T['dima_cry'] + 0.2, T['dima_cry'] + 0.4))
    put(im, text_spr('ЗАБЛОКИРОВАН', 70, rgb=(255, 80, 80)), 540, 360, a=pop(t, T['dima_cry'], 0.25))
    return zoom_view(im, 540, 820, 1.05 + 0.1 * ramp(t, T['dima_cry'], T['simple']))


def shot_simple(t):
    k = 1.0 + 0.18 * sm(ramp(t, T['simple'], T['sleep']))
    im = room_scene(t, 'eve', dict(arms='down', talk_keys=('simple',), brow=0.7, smile=0.45, look=(0.2, -0.6),
                                   tilt=-3 * sm(ramp(t, T['simple'], T['simple'] + 1))), cam=(540, 860, k))
    return im


def shot_sleep(t):
    im = S.bedroom().copy()
    hd = C.head('petya', blink=1.0, smile=0.8 + 0.1 * math.sin(t * 2), smirk=0.2)
    hd = hd.rotate(78, resample=Image.BICUBIC, expand=True)
    put(im, hd, 300, 1110, scale=0.95)
    im.alpha_composite(S.blanket())
    # zzz
    for j in range(3):
        ph = (t * 0.6 + j / 3) % 1.0
        put(im, text_spr('z', 60 + 20 * j, rgb=(220, 230, 255), stroke=5), 430 + 60 * ph + 30 * j, 950 - 260 * ph,
            a=math.sin(math.pi * ph) * 0.9)
    k = 1.0 + 0.1 * ramp(t, T['sleep'], AD1)
    return zoom_view(im, 520, 1050, k)


# 3D loot tunnel ------------------------------------------------------------
TUNNEL = [('Plush Pepe', 'Cozy Galaxy'), ('Heart Locket', 'Golden'), ('Resistance Dog', 'Guard Dog'),
          ('Desk Calendar', 'Celestial Map'), ('Plush Pepe', 'Emerald Plush'), ('Heart Locket', 'Neptune'),
          ('Resistance Dog', 'Satoshi'), ('Desk Calendar', 'Lovely'), ('Plush Pepe', 'Magnate'),
          ('Heart Locket', 'Mirror'), ('Resistance Dog', 'Ice Walker'), ('Desk Calendar', 'Pink Day')]


@functools.lru_cache(maxsize=32)
def _gift_png(name, model):
    return Image.open(G.model_png(name, model, 256)).convert('RGBA')


@functools.lru_cache(maxsize=1)
def _tunnel_items():
    rnd = random.Random(5)
    items = []
    for i in range(36):
        a = i * 2.4
        r = rnd.uniform(1.1, 1.6)
        items.append((math.cos(a) * r, math.sin(a) * r * 1.3 + 0.2, 1.2 + i * 0.55, TUNNEL[i % len(TUNNEL)]))
    return items


def shot_tunnel(t):
    k = ramp(t, T['tunnel'], T['katya'])
    im = Image.new('RGBA', (W, H), (14, 10, 34, 255))
    glow(im, 540, 960, 900, (120, 80, 255), 0.35)
    cam = stage.Cam((0.15 * math.sin(t), 0.2, -1.0 + 17 * sm(k)), (0, 0.2, 30), fov=60, roll=0.15 * k)
    items = sorted(_tunnel_items(), key=lambda it: -cam.depth((it[0], it[1], it[2])))
    for x, y, z, (n, m) in items:
        dpt = cam.depth((x, y, z))
        if dpt < 0.3 or dpt > 12:
            continue
        a = min(1.0, (12 - dpt) / 3) * min(1.0, (dpt - 0.3) / 0.6)
        stage.billboard(im, _gift_png(n, m), (x, y - 0.45, z), 0.9, cam, anchor=(0.5, 0.5), alpha=a)
    put(im, text_spr('МЕСЯЦЫ СПУСТЯ', 76), 540, 380, a=ramp(t, T['tunnel'] + 0.1, T['tunnel'] + 0.35))
    n = int(lerp(3, 48, sm(k)))
    put(im, text_spr(f'Улов Пети: {n} подарков', 52, rgb=(255, 214, 90)), 540, 470,
        a=ramp(t, T['tunnel'] + 0.25, T['tunnel'] + 0.5))
    return Image.blend(im, Image.new('RGBA', (W, H), (255, 240, 230, 255)), 0.9 * ramp(t, T['katya'] - 0.12,
                                                                                         T['katya']))


def shot_katya(t):
    im = S.katya_flat().copy()
    puzzled = ramp(t, END[KEY['katya']] - 1.8, END[KEY['katya']] - 1.5)
    person(im, 'katya', 540, 1060, 1.3, t, arms='phone', glow_=0.4, smile=0.6 - 0.6 * puzzled, sad=0.5 * puzzled,
           brow=0.6 * puzzled, look=(0, 0.2 + 0.4 * puzzled), seed=1.3)
    if puzzled > 0:
        put(im, text_spr('NFT?', 64, rgb=(255, 255, 255)), 800, 560, a=pop(t, END[KEY['katya']] - 1.8, 0.35))
    put(im, chip('Катя, 23'), 540, 300, a=ramp(t, T['katya'] + 0.2, T['katya'] + 0.5))
    k = 1.0 + 0.07 * ramp(t, T['katya'], T['search'])
    im = zoom_view(im, 540, 960, k)
    return Image.blend(im, Image.new('RGBA', (W, H), (255, 240, 230, 255)), 0.9 * (1 - ramp(t, T['katya'],
                                                                                        T['katya'] + 0.25)))


def shot_search(t):
    k = ramp(t, T['search'], T['found'])
    day = 1 + int(20 * k)

    def ex(im):
        px, py = phone_point(540, 1010, 1.25)
        glow(im, px, py, 360, (150, 210, 255), 0.55)
        put(im, chip(f'День {day}', bg=(40, 30, 60)), 540, 300)
        for j in range(3):                                         # tabs flying past
            ph = (t * 1.4 + j / 3) % 1
            put(im, chip(['поиск: Катя ...', 'ничего не найдено', 'ещё 1 вкладка'][j], bg=(20, 24, 40)),
                lerp(1300, -250, ph), 520 + j * 110, a=0.8)
    im = room_scene(t, 'night', dict(arms='phone', glow_=1.0, hood=True, sad=0.3, smile=-0.1,
                                     blink=0.5 + 0.4 * (math.sin(t * 3) > 0.6), look=(0, 0.6)), extra=ex,
                    cam=(540, 1000, 1.0 + 0.1 * k))
    return im


def shot_found(t):
    j = pop(t, T['found'], 0.3)
    im = room_scene(t, 'night', dict(arms='phone', glow_=1.0, hood=True, brow=1.0, smile=1.0, open_=0.9,
                                     teeth=1.0, look=(0, 0.4), bob=-40 * math.sin(math.pi * ramp(t, T['found'],
                                                                                                 T['found'] + 0.4))),
                    cam=(540, 900, 1.15 + 0.08 * j))
    put(im, text_spr('ВОТ ОНО!', 110, rgb=(255, 220, 80)), 540, 330, a=j, scale=0.8 + 0.2 * j)
    im = Image.blend(im, Image.new('RGBA', (W, H), (255, 255, 255, 255)), 0.6 * (1 - ramp(t, T['found'],
                                                                                         T['found'] + 0.2)))
    px, py = phone_point(540, 1010, 1.25)
    return fly_out(im, t, T['profile'], px, (py - 900) * 1.23 + 960)


def shot_profile(t):
    t0 = T['profile']
    hl = [t0 + 1.2 + 0.55 * k for k in range(4)]
    scr = SC.dating_screen(t, t0 + 0.3, hl)
    z, b, fl = fly_in(t, t0)
    zz = z * (1 + 0.1 * sm(ramp(t, t0 + 1.0, t0 + 2.2)))
    im = pov(t, screen=scr, bg=environment('night'), zoom=zz, focus=(540, screen_y(1350)))
    if b:
        im = radial_blur(im, W / 2, H / 2, b)
    return Image.blend(im, Image.new('RGBA', (W, H), (235, 245, 255, 255)), fl)


# 3D: the AI assembles Alexander -----------------------------------------------
@functools.lru_cache(maxsize=1)
def _alex_card():
    im = Image.new('RGBA', (600, 760), (0, 0, 0, 0))
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 599, 759], 40, fill=255)
    bg = Image.new('RGBA', im.size, (60, 120, 200, 255))
    d = ImageDraw.Draw(bg)
    for y in range(760):
        k = y / 759
        d.line([(0, y), (600, y)], fill=(int(70 + 60 * k), int(130 + 40 * k), int(210 - 10 * k), 255))
    C.place(bg, C.bust(C.head('alex', smile=0.75, open_=0.35, teeth=1.0), C.alex_body(), 300, 560, scale=0.95))
    im.paste(bg, (0, 0), m)
    return im


@functools.lru_cache(maxsize=1)
def _alex_pixel():
    a = _alex_card()
    p = a.resize((24, 30), Image.BILINEAR).resize(a.size, Image.NEAREST)
    arr = np.asarray(p, np.float32)
    arr[..., 0] = arr[..., 0] * 0.3
    arr[..., 1] = arr[..., 1] * 0.8 + 60
    arr[..., 2] = np.minimum(255, arr[..., 2] * 1.0 + 80)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')


@functools.lru_cache(maxsize=1)
def _grid_tex():
    im = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(0, 1025, 64):
        d.line([(k, 0), (k, 1024)], fill=(80, 200, 255, 140), width=3)
        d.line([(0, k), (1024, k)], fill=(80, 200, 255, 140), width=3)
    return im


@functools.lru_cache(maxsize=8)
def _panel(text, ok):
    f = fx.font('Semibold', 40)
    w = int(f.getlength(text)) + 120
    im = Image.new('RGBA', (w, 90), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 89], 24, fill=(20, 60, 100, 200), outline=(90, 210, 255, 255), width=3)
    d.text((30, 45), text, font=f, fill=(220, 245, 255), anchor='lm')
    if ok:
        d.ellipse([w - 72, 22, w - 26, 68], fill=(80, 220, 140))
        d.line([(w - 62, 46), (w - 52, 56), (w - 36, 34)], fill=(255, 255, 255), width=5)
    return im


def shot_ai(t):
    t0 = T['ai']
    k = ramp(t, t0, T['chat_k'])
    im = Image.new('RGBA', (W, H), (6, 12, 30, 255))
    glow(im, 540, 900, 900, (40, 120, 255), 0.35)
    yaw = -0.5 + 0.9 * sm(k)
    eye = (4.8 * math.sin(yaw), 1.6 - 0.3 * k, -4.8 * math.cos(yaw))
    cam = stage.Cam(eye, (0, 1.25, 0), fov=46)
    stage.quad(im, _grid_tex(), [(-6, 0, 6), (6, 0, 6), (6, 0, -6), (-6, 0, -6)], cam, alpha=0.7)
    # the portrait: pixels → scan line reveal
    rev = ramp(t, t0 + 0.4, T['alex_name'])
    card = _alex_pixel().copy()
    if rev > 0:
        real = _alex_card()
        yy = int(real.height * rev)
        card.paste(real.crop((0, 0, real.width, yy)), (0, 0))
        d = ImageDraw.Draw(card)
        if rev < 1:
            d.rectangle([0, yy - 4, real.width, yy + 4], fill=(150, 240, 255, 255))
    stage.quad(im, card, [(-0.75, 2.2, 0), (0.75, 2.2, 0), (0.75, 0.3, 0), (-0.75, 0.3, 0)], cam)
    # holo panels around
    items = [('Фото', 0.2, -1.05, 2.05), ('Биография', 0.4, 0.2, 1.75), ('Соцсети', 0.6, -1.05, 0.95),
             ('Переписка', 0.8, 0.2, 0.6)]
    for s, th, x, y in items:
        pnl = _panel(s, k > th + 0.12)
        a = ramp(k, th - 0.1, th)
        if a > 0:
            w_ = 0.85 * pnl.width / 330
            h_ = w_ * pnl.height / pnl.width
            stage.quad(im, pnl, [(x, y, -0.6), (x + w_, y, -0.6), (x + w_, y - h_, -0.6), (x, y - h_, -0.6)],
                       cam, alpha=a)
    put(im, text_spr('НЕЙРОСЕТЬ: ГЕНЕРАЦИЯ…', 54, rgb=(150, 230, 255)), 540, 260,
        a=ramp(t, t0, t0 + 0.3) * (1 - ramp(t, T['alex_name'] - 0.1, T['alex_name'])))
    if t >= T['alex_name']:
        put(im, text_spr('АЛЕКСАНДР, 28', 84, rgb=(255, 255, 255)), 540, 300, a=1,
            scale=0.8 + 0.2 * pop(t, T['alex_name'], 0.35))
        put(im, chip('предприниматель · путешествия · собаки', bg=(20, 50, 90)), 540, 410,
            a=ramp(t, T['alex_name'] + 0.2, T['alex_name'] + 0.5))
    im = Image.blend(im, Image.new('RGBA', (W, H), (255, 255, 255, 255)), 0.7 * (1 - ramp(t, t0, t0 + 0.2)))
    return fly_out(im, t, T['chat_k'], 540, 900, d=0.35)


def shot_chat_k(t, t0=None, fly=True):
    return pov_shot(t, CHAT_K, t0 if t0 is not None else T['chat_k'], environment('night'), fly=fly)


def shot_katya_love(t):
    im = S.katya_flat().copy()
    person(im, 'katya', 540, 1020, 1.6, t, arms='phone', glow_=0.7, talk_keys=('date',), smile=0.9,
           blink=0.875 if (t % 2.2) < 1.4 else blink(t), look=(0, 0.5), tilt=4 * math.sin(t * 1.5), seed=0.6)
    for j in range(5):                                             # little hearts float up
        ph = (t * 0.5 + j / 5) % 1
        put(im, tg._emoji('❤', 64), 260 + j * 140 + 30 * math.sin(t + j), 1200 - 700 * ph,
            a=math.sin(math.pi * ph) * 0.9)
    return zoom_view(im, 540, 900, 1.05 + 0.06 * ramp(t, T['katya_love'], T['cancel']))


def shot_cancel(t):
    def ex(im):
        px, py = phone_point(540, 1010, 1.3)
        glow(im, px, py, 360, (150, 210, 255), 0.6)
    im = room_scene(t, 'night', dict(arms='phone', glow_=1.0, sad=0.8, smile=-0.2, smirk=0.6 * ramp(
        t, T['cancel'] + 0.5, T['cancel'] + 0.8), talk_keys=('cancel',), look=(0, 0.6)), scale=1.3, extra=ex,
        cam=(540, 950, 1.05))
    px, py = phone_point(540, 1010, 1.3)
    return fly_out(im, t, T['fly_cancel'], px, (py - 950) * 1.05 + 960)


def shot_katya_worried(t):
    im = S.katya_flat().copy()
    person(im, 'katya', 540, 1020, 1.6, t, arms='phone', glow_=0.7, talk_keys=('why',), sad=0.9, brow=0.4,
           smile=-0.3, look=(0, 0.4), seed=2.1)
    im = zoom_view(im, 540, 880, 1.1 + 0.05 * ramp(t, T['katya_worried'], T['lie']))
    return whip(im, 1 - ramp(t, T['katya_worried'], T['katya_worried'] + 0.15))


def shot_lie(t):
    im = pov_shot(t, CHAT_K, T['lie'], environment('night'), fly=False)
    return whip(im, 1 - ramp(t, T['lie'], T['lie'] + 0.15))


def shot_genius(t):
    def ex(im):
        px, py = phone_point(540, 1010, 1.25)
        glow(im, px, py, 380, (150, 210, 255), 0.7)
    im = room_scene(t, 'night', dict(arms='phone', glow_=1.0, hood=True, smirk=1.0, smile=0.6, look=(0.3, 0.5),
                                     talk_keys=('genius',), anger=0.3), extra=ex)
    k = 1.7 + 0.25 * sm(ramp(t, T['genius'], T['help']))
    return zoom_view(im, 540, 640, k)


@functools.lru_cache(maxsize=4)
def _star(r):
    L = Layer(4 * r, 4 * r, ss=2)
    c = 2 * r
    L.poly([(c, c - 2 * r), (c + r * 0.3, c - r * 0.3), (c + 2 * r, c), (c + r * 0.3, c + r * 0.3), (c, c + 2 * r),
            (c - r * 0.3, c + r * 0.3), (c - 2 * r, c), (c - r * 0.3, c - r * 0.3)], (255, 244, 190))
    return L.image()


def _gift_burst(im, t):
    for tt, (n, m, b) in zip(T['gifts'], GIFTS_K):
        if tt <= t < tt + 0.9:
            k = ramp(t, tt, tt + 0.9)
            y = lerp(1000, 520, eo(k))
            s = 0.5 + 0.9 * math.sin(math.pi * min(1, k * 1.2)) if k < 0.8 else 1.4 * (1 - (k - 0.8) / 0.2) + 0.01
            a = 1 - ramp(k, 0.75, 1.0)
            glow(im, 540, y, 420 * s, (255, 220, 140), 0.6 * a)
            for r in range(10):                                   # sparkles
                ang = r * 0.63 + tt
                rr = 120 + 360 * eo(k)
                put(im, _star(26), 540 + rr * math.cos(ang), y + rr * math.sin(ang), a=a)
            put(im, gift_live(n, m, t - tt, 420), 540, y, a=a, scale=s)


def shot_help(t):
    im = pov_shot(t, CHAT_K, T['help'], environment('night'), fly=False,
                  shake=8 * sum(1 - ramp(t, g, g + 0.3) for g in T['gifts'] if t >= g))
    _gift_burst(im, t)
    return whip(im, 1 - ramp(t, T['help'], T['help'] + 0.15))


def shot_katya_sad(t):
    im = S.katya_flat().copy()
    person(im, 'katya', 540, 1020, 1.6, t, arms='phone', glow_=0.6, talk_keys=('all',), sad=0.6, smile=0.35,
           look=(0, 0.5), seed=0.2)
    return zoom_view(im, 540, 880, 1.1 + 0.05 * ramp(t, T['katya_sad'], T['smile']))


def shot_smile(t):
    k = ramp(t, T['smile'], AD1 if False else AD2)
    sm_ = sm(ramp(t, T['smile'] + 0.2, T['smile'] + 2.5))

    def ex(im):
        px, py = phone_point(540, 1010, 1.25)
        glow(im, px, py, 400, (255, 220, 150), 0.7)                 # gold light of the gifts on his face
    im = room_scene(t, 'night', dict(arms='phone', glow_=1.0, smile=0.1 + 0.9 * sm_, smirk=0.9 * sm_,
                                     open_=0.25 * sm_, teeth=sm_, look=(0, 0.5), brow=0.2 * sm_), extra=ex)
    im = zoom_view(im, 540, 680, 1.9 + 0.35 * sm(k))
    a = np.asarray(im, np.float32)
    a[..., 0] = np.minimum(255, a[..., 0] * (1 + 0.08 * sm_))
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def shot_mock(t):
    im = pov_shot(t, CHAT_K, AD2, environment('night'), fly=False)
    for key, txt in (('five', '+5 минут'), ('ten', '+10 минут')):
        if T[key] <= t < T[key] + 1.2:
            put(im, text_spr(txt, 86, rgb=(255, 214, 90)), 540, 1600, a=pop(t, T[key], 0.3) *
                (1 - ramp(t, T[key] + 0.9, T[key] + 1.2)))
    if t >= T['mock_sent'] + 0.5:                                   # waiting: slow push on the message
        k = sm(ramp(t, T['mock_sent'] + 0.5, T['uneasy']))
        im = zoom_view(im, 540, 1000, 1 + 0.12 * k)
    return im


def shot_uneasy(t):
    def ex(im):
        px, py = phone_point(540, 1010, 1.25)
        glow(im, px, py, 360, (150, 210, 255), 0.6)
    im = room_scene(t, 'night', dict(arms='phone', glow_=1.0, sad=0.3, smile=-0.1 + 0.4 * ramp(
        t, END[KEY['uneasy']] - 1.2, END[KEY['uneasy']] - 0.9), smirk=0.6 * ramp(t, END[KEY['uneasy']] - 1.2,
                                                                                END[KEY['uneasy']] - 0.9),
        sweat=ramp(t, T['uneasy'] + 0.4, T['uneasy'] + 0.7), look=(-0.6, 0.2)), extra=ex)
    return zoom_view(im, 540, 760, 1.5 + 0.1 * ramp(t, T['uneasy'], T['block2_shot']))


def shot_block2(t):
    return pov_shot(t, CHAT_K, T['block2_shot'], environment('night'), fly=True)


def shot_party(t):
    im = S.room('party').copy()
    _party_lights(im, t)
    lp = ramp(t, T['buzz2'] - 0.1, T['buzz2'])
    person(im, 'sery', 190, 1110, 1.0, t, smile=0.9, open_=0.5 + 0.3 * math.sin(t * 7), teeth=1.0,
           bob=12 * math.sin(t * 8), tilt=4 * math.sin(t * 4), seed=0.5)
    person(im, 'vanya', 890, 1100, 1.0, t, smile=1.0, open_=0.6, teeth=1.0, blink=1.0 if (t % 1.0) < 0.5 else 0,
           bob=12 * math.sin(t * 8 + 2), tilt=-4 * math.sin(t * 4 + 1), seed=1.2)
    person(im, 'petya', 540, 1060, 1.25, t, arms='phone' if lp > 0.5 else 'down', glow_=lp,
           talk_keys=('party',), smile=1.0 - 0.8 * lp, open_=0.6 * (1 - lp), teeth=1.0 - lp, brow=0.3,
           look=(0, 0.6 * lp), bob=10 * math.sin(t * 8) * (1 - lp))
    confetti(im, t, T['party'])
    if lp > 0:
        px, py = phone_point(540, 1060, 1.25)
        glow(im, px, py, 300, (150, 210, 255), 0.7 * lp)
    put(im, text_spr('ВСЁ ЗА МОЙ СЧЁТ!', 80, rgb=(255, 220, 80)), 540, 330,
        a=pop(t, ON[KEY['party']], 0.3) * (1 - ramp(t, END[KEY['party']] + 0.4, END[KEY['party']] + 0.7)))
    k = 1.0 + 0.15 * sm(lp)
    im = zoom_view(im, 540, 1000 + 200 * lp, k)
    px, py = phone_point(540, 1060, 1.25)
    return fly_out(im, t, T['fly_final'], px, (py - (1000 + 200 * lp)) * k + 960)


def shot_final(t):
    t0 = T['fly_final']
    fade = ramp(t, t0, T['final_msg'] + 0.6)
    bg = Image.blend(party_bg_blur(), Image.new('RGBA', (W, H), (8, 6, 12, 255)), 0.85 * fade)
    scr = tg.chat_screen(t, chat_x(T['final_msg']))
    dev = tg.phone(scr)
    im = bg.copy()
    # 3D: the phone is a plane that turns towards us while the camera pushes in
    k = sm(ramp(t, t0, T['shock2']))
    cam = stage.Cam((0, 0, -2.7 + 0.55 * k), (0, 0, 0), fov=50)
    yaw = 0.55 * (1 - eo(ramp(t, t0, t0 + 1.6)))
    hw, hh = 0.52, 1.0
    c, s = math.cos(yaw), math.sin(yaw)
    corners = [(-hw * c, hh, -hw * s), (hw * c, hh, hw * s), (hw * c, -hh, hw * s), (-hw * c, -hh, -hw * s)]
    red = 0.5 + 0.5 * math.sin(t * 6)
    glow(im, 540, 960, 760, (200, 30, 50), (0.25 + 0.15 * red) * ramp(t, T['final_msg'], T['final_msg'] + 0.4))
    stage.quad(im, dev, corners, cam)
    z, b, fl = fly_in(t, t0)
    if b:
        im = radial_blur(im, W / 2, H / 2, b)
    return Image.blend(im, Image.new('RGBA', (W, H), (235, 245, 255, 255)), fl)


def shot_shock2(t):
    im = Image.new('RGBA', (W, H), (14, 8, 14, 255))
    glow(im, 540, 900, 900, (200, 30, 50), 0.35 + 0.1 * math.sin(t * 6))
    sh = 4 * math.sin(t * 50)
    person(im, 'petya', 540 + sh, 1060, 1.25, t, arms='phone', glow_=1.0, shock=1.0, open_=0.5, smile=-0.6,
           sweat=1.0, look=(0, 0.4))
    k = 1.6 + 0.4 * sm(ramp(t, T['shock2'], T['endcard']))
    return zoom_view(im, 540, 700, k)


def shot_end(t):
    im = Image.new('RGBA', (W, H), (10, 8, 14, 255))
    glow(im, 540, 900, 800, (200, 30, 50), 0.3)
    put(im, tg.circle(C.avatar('unknown', 240), 260), 540, 640, a=pop(t, T['endcard'], 0.4))
    put(im, text_spr('КАК ПЕТЮ', 110), 540, 900, a=pop(t, T['endcard'] + 0.1, 0.35))
    put(im, text_spr('МОГЛИ ВЫЧИСЛИТЬ?', 92, rgb=(255, 80, 90)), 540, 1030, a=pop(t, T['endcard'] + 0.3, 0.35))
    put(im, chip('ЧАСТЬ 2 — СКОРО', bg=(200, 30, 50)), 540, 1220, a=ramp(t, T['endcard'] + 1.0,
                                                                         T['endcard'] + 1.3))
    if int(t * 12) % 9 == 0:
        im = whip(im, 0.4)
    return im


SHOTS = [
    (0.0, shot_hook, 'pov'),
    (T['shock'], shot_shock, 'scene'),
    (T['rewind'], shot_rewind, 'scene'),
    (T['room'], shot_room, 'scene'),
    (T['fly1'], shot_boss, 'pov'),
    (T['dima'], shot_dima, 'scene'),
    (T['to_dima_chat'], shot_dima_chat, 'pov'),
    (T['dima_cry'], shot_dima_cry, 'scene'),
    (T['simple'], shot_simple, 'scene'),
    (T['sleep'], shot_sleep, 'scene'),
    (T['tunnel'], shot_tunnel, 'scene'),
    (T['katya'], shot_katya, 'scene'),
    (T['search'], shot_search, 'scene'),
    (T['found'], shot_found, 'scene'),
    (T['profile'], shot_profile, 'pov'),
    (T['ai'], shot_ai, 'scene'),
    (T['chat_k'], shot_chat_k, 'pov'),
    (T['katya_love'], shot_katya_love, 'scene'),
    (T['cancel'], shot_cancel, 'scene'),
    (T['fly_cancel'], lambda t: shot_chat_k(t, T['fly_cancel']), 'pov'),
    (T['katya_worried'], shot_katya_worried, 'scene'),
    (T['lie'], shot_lie, 'pov'),
    (T['genius'], shot_genius, 'scene'),
    (T['help'], shot_help, 'pov'),
    (T['katya_sad'], shot_katya_sad, 'scene'),
    (T['smile'], shot_smile, 'scene'),
    (AD2, shot_mock, 'pov'),
    (T['uneasy'], shot_uneasy, 'scene'),
    (T['block2_shot'], shot_block2, 'pov'),
    (T['party'], shot_party, 'scene'),
    (T['fly_final'], shot_final, 'pov'),
    (T['shock2'], shot_shock2, 'scene'),
    (T['endcard'], shot_end, 'scene'),
]
CUTS = [s for s, _, _ in SHOTS[1:]]


# ------------------------------------------------------------------ subtitles
LINES_SPOKEN = [s for _, s, _, _ in LINES]


@functools.lru_cache(None)
def _timed_script(k):
    asr = WORDS[k]
    spoken = LINES_SPOKEN[k].replace('«', '').replace('»', '').split()
    spoken = [w for w in spoken if w not in ('—', '–')]
    if not asr:
        return []
    ac = np.cumsum([0] + [len(w) + 1 for w, _, _ in asr])
    af = ac / ac[-1]
    at = [a for _, a, _ in asr] + [asr[-1][2]]
    sc = np.cumsum([0] + [len(w) + 1 for w in spoken])
    sf = sc / sc[-1]
    return [(w, float(np.interp(sf[j], af, at)), float(np.interp(sf[j + 1], af, at))) for j, w in enumerate(spoken)]


@functools.lru_cache(None)
def _chunks(k):
    out, cur, n = [], [], 0
    for w in _timed_script(k):
        if cur and (n + len(w[0]) > 20 or cur[-1][0][-1] in '.:?!…'):
            out.append(tuple(cur))
            cur, n = [], 0
        cur.append(w)
        n += len(w[0]) + 1
    if cur:
        out.append(tuple(cur))
    return tuple(out)


@functools.lru_cache(maxsize=256)
def _sub_spr(words, hi, accent):
    f = fx.font('Heavy', 64)
    space = f.getlength(' ')
    ws = [f.getlength(w) for w in words]
    total = sum(ws) + space * (len(words) - 1)
    im = Image.new('RGBA', (int(total) + 60, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 30
    for k, w in enumerate(words):
        col = accent if k == hi else (255, 255, 255)
        d.text((x, 60), w, font=f, fill=col + (255,), anchor='lm', stroke_width=8, stroke_fill=(14, 10, 20, 255))
        x += ws[k] + space
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 6))
    out.alpha_composite(im)
    return out


ACCENT = {'N': (255, 214, 90), 'P': (120, 200, 255), 'K': (255, 140, 180), 'X': (255, 80, 90)}


def subtitles(im, t, kind):
    for k in range(len(ON)):
        if ON[k] - 0.05 <= t < END[k] + 0.25:
            who = LINES[k][0]
            if kind == 'pov' and who in 'PKX':
                return                                            # the chat already shows these words
            y = 196 if kind == 'pov' else 1600
            if LINES[k][2] in ('outro',) and t >= T['endcard']:
                y = 1500
            chs = _chunks(k)
            for ch in chs:
                a, b = ch[0][1], ch[-1][2]
                if a - 0.05 <= t < b + 0.25 or (ch is chs[-1] and t >= a):
                    hi = max([j for j, w in enumerate(ch) if w[1] <= t] or [0])
                    spr = _sub_spr(tuple(w[0] for w in ch), hi, ACCENT[who])
                    s = 1 + 0.06 * (1 - ramp(t, a - 0.05, a + 0.1))
                    put(im, spr, W / 2, y, a=ramp(t, a - 0.05, a + 0.05), scale=s)
                    return
            return


# ------------------------------------------------------------------ frame
@functools.lru_cache(None)
def _vign():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W * 0.7)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.3 * np.clip(d - 0.45, 0, 1) ** 1.5)[..., None]


def render_at(t):
    t = min(max(t, 0.0), DUR - 1e-3)
    i = max(j for j, (s, _, _) in enumerate(SHOTS) if t >= s)
    _, fn, kind = SHOTS[i]
    im = fn(t)
    if im.size != (W, H):
        im = im.resize((W, H))
    for c in CUTS:                                                # a small punch-in on every cut
        if c <= t < c + 0.16:
            k = 1 + 0.03 * (1 - (t - c) / 0.16)
            im = zoom_view(im, W / 2, H / 2, k)
            break
    subtitles(im, t, kind)
    out = np.asarray(im.convert('RGB'), np.float32)
    out *= _vign()
    out += np.random.default_rng(int(t * FPS)).normal(0, 2.2, (H // 3, W // 3, 1)).repeat(3, 0).repeat(3, 1)
    out *= 1 - 0.9 * ramp(t, DUR - 0.3, DUR)
    return np.clip(out, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Сначала хайлайты и слово автора «собирай» (config.STYLE_READY)')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
