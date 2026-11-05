"""04-calendar-craft «Первый крафт»: 2D cartoon shots + two 3D cutaways, RubUp in the middle.
Frame = render_at(content time). Shots, poses and overlays follow events.py (word anchors from the voice)."""
import functools
import math
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import banner
import frames
import fx
import config
import chars as C
import sets as S
import phone as P
import scenes3d as S3
import events as E
from script import LINES
from timeline import DUR, ON, END, SPEAKER, TAKES, HAS_NARRATION
from words import WORDS

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([E.AD_STOP], cy=H / 2)
INK = C.INK
GOLD = (255, 196, 70)
RED = (255, 84, 70)
GREEN = (90, 220, 120)
ALEX_X, MISHA_X = 380.0, 770.0          # stage x of the two boys in the hallway


# ------------------------------------------------------------------ timing helpers
def ramp(t, a, b):
    return fx.smooth((t - a) / (b - a)) if b > a else float(t >= a)


def keys(t, pts):
    """Smoothly interpolated scalar keys [(time, value), ...]."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t < t1:
            return v0 + (v1 - v0) * fx.smooth((t - t0) / (t1 - t0))
    return pts[-1][1]


def pkeys(t, pts):
    """Pose keys [(time, pose dict)] -> interpolated pose."""
    if t <= pts[0][0]:
        return dict(pts[0][1])
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t < t1:
            return C.mix(p0, p1, fx.smooth((t - t0) / (t1 - t0)))
    return dict(pts[-1][1])


def blink(t, seed=0.0):
    ph = (t + seed) % 3.7
    return 1.0 if ph > 0.14 else abs(ph - 0.07) / 0.07


@functools.lru_cache(None)
def _env(k):
    if not HAS_NARRATION:
        return np.zeros(1)
    with wave.open(str(TAKES[k])) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32)
        sr = w.getframerate()
    hop = sr // 100
    e = np.array([np.sqrt((x[i:i + hop] ** 2).mean()) for i in range(0, len(x) - hop, hop)])
    e = np.convolve(e, np.ones(4) / 4, 'same')
    return np.clip(e / (np.percentile(e, 90) + 1e-6), 0, 1.2)


def talk(t, who):
    """Mouth opening 0..1 for speaker `who` from the loudness of their current take."""
    for k, sp in enumerate(SPEAKER):
        if sp == who and ON[k] <= t < END[k]:
            e = _env(k)
            i = int((t - ON[k]) * 100)
            return float(np.clip(e[min(i, len(e) - 1)] * 0.85, 0, 1)) if len(e) > 1 else 0.0
    return 0.0


def line_at(t):
    for k in range(len(LINES)):
        if ON[k] - 0.05 <= t < END[k] + 0.15:
            return k
    return None


# ------------------------------------------------------------------ text
@functools.lru_cache(maxsize=256)
def text_sprite(text, size, rgb, weight='Heavy', stroke=0, stroke_rgb=INK):
    f = fx.font(weight, size)
    lines = text.split('\n')
    lw = [f.getlength(s) for s in lines]
    asc, desc = f.getmetrics()
    lh = int(size * 1.12)
    pad = stroke + 12
    im = Image.new('RGBA', (int(max(lw)) + pad * 2, lh * len(lines) + pad * 2 + desc // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for j, s in enumerate(lines):
        d.text((im.width / 2, pad + j * lh + asc * 0.5 + 4), s, font=f, fill=rgb + (255,), anchor='mm',
               stroke_width=stroke, stroke_fill=stroke_rgb + (255,))
    return im


def put(im, spr, x, y, a=1.0, scale=1.0, rot=0.0):
    if a <= 0.01 or scale <= 0.01:
        return
    s = spr
    if abs(scale - 1) > 0.01:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BICUBIC)
    if rot:
        s = s.rotate(rot, Image.BICUBIC, expand=True)
    if a < 0.99:
        s = s.copy()
        s.putalpha(s.getchannel('A').point(lambda v: int(v * a)))
    im.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))


def pop(t, t0, d=0.35):
    """Scale for a pop-in that starts at t0."""
    if t < t0:
        return 0.0
    return fx.ease_out_back(min(1.0, (t - t0) / d), 1.8)


def headline(im, t, t0, text, y, size=96, rgb=(255, 255, 255), t1=None):
    if t < t0 or (t1 is not None and t > t1 + 0.25):
        return
    a = 1.0 if t1 is None else 1 - ramp(t, t1, t1 + 0.25)
    put(im, text_sprite(text, size, rgb, 'Heavy', 10), W / 2, y, a, pop(t, t0))


CENSOR = {'сука': 'с*ка', 'блядь': 'бл*дь', 'охуели': 'оху*ли', 'нахуй': 'нах*й', 'хуйня': 'х*йня',
          'похуй': 'пох*й', 'ебанутый': 'еб*нутый', 'долбаёб': 'долба*б'}


def censor(text):
    for a, b in CENSOR.items():
        text = text.replace(a, b)
    return text


def subtitles(im, t):
    k = line_at(t)
    if k is None or LINES[k][2] in ('hook', 'vault3d', 'moral', 'cta'):
        return
    who = SPEAKER[k]
    name = {'N': None, 'A': ('АЛЕКСЕЙ', (120, 180, 255)), 'M': ('МИХАИЛ', (255, 120, 110))}[who]
    import re
    words = re.findall(r'\S+?-(?=\S)|\S+', censor(LINES[k][1]))
    asr = [a for w, a, b in WORDS[k]]
    n, m = len(words), len(asr)
    times = [asr[min(m - 1, round(j * (m - 1) / max(1, n - 1)))] if n != m else asr[j] for j in range(n)]
    cur = max([j for j, a in enumerate(times) if t >= a - 0.02] or [0])
    f = fx.font('Heavy', 54)
    # wrap into lines of max width
    rows, row = [], []
    for j, w in enumerate(words):
        test = ' '.join(x for x, _ in row + [(w, j)]) + ' ' * len(row)
        if row and f.getlength(test) > 900:
            rows.append(row)
            row = []
        row.append((w, j))
    rows.append(row)
    a = ramp(t, ON[k] - 0.05, ON[k] + 0.08) * (1 - ramp(t, END[k] + 0.02, END[k] + 0.15))
    y0 = 1640 - (len(rows) - 1) * 33
    d = ImageDraw.Draw(im)
    if name:
        spr = fx.solid_pill(name[0], name[1], 26, (255, 255, 255), 'Heavy')
        put(im, spr, W / 2, y0 - 64, a)
    for r, row in enumerate(rows):
        line = ' '.join(w for w, _ in row)
        x = W / 2 - (f.getlength(line) + 6 * (len(row) - 1)) / 2
        for w, j in row:
            col = (255, 214, 64) if j == cur else (255, 255, 255)
            d.text((x, y0 + r * 66), w, font=f, fill=col + (int(255 * a),), anchor='lm', stroke_width=7,
                   stroke_fill=INK + (int(255 * a),))
            x += f.getlength(w) + (0 if w.endswith('-') else f.getlength(' ') + 6)


# ------------------------------------------------------------------ 2D stage
def stage(bg, cx, cy, z, actors, extra=None, blur=0.0, dim=0.0):
    """bg: cached set; actors: [(draw fn, stage x, char scale, pose)] drawn in order."""
    im = S.view(bg, cx, cy, z, blur).convert('RGBA')
    draws = []
    for fn, x, cs, pose in actors:
        draws.append((fn, 540 + (x - cx) * z, 960 + (S.FLOOR + 20 - cy) * z, cs * z, pose))
    if extra:
        draws += extra(lambda x, y: (540 + (x - cx) * z, 960 + (y - cy) * z), z)
    im.alpha_composite(C.render_layer(W, H, draws))
    if dim:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * dim))))
    return im


def shake(t, t0, dur, amp):
    if not t0 <= t < t0 + dur:
        return 0.0, 0.0
    k = 1 - (t - t0) / dur
    return amp * k * math.sin(t * 87), amp * k * math.cos(t * 71)


def piggy(ox, oy, s, fill):
    """Piggy bank drawn with chars.Pen; fill 0..1 swells it a little."""
    def fn(pen, p):
        k = 1 + 0.18 * fill
        pink = (255, 160, 180)
        for dx in (-50, 50):
            pen.limb([(dx * k, 40), (dx * k, 80)], 30, pink)
        pen.ellipse(0, 0, 110 * k, 80 * k, pink)
        pen.ellipse(-60 * k, -70 * k, 22, 30, pink)
        pen.ellipse(110 * k, 0, 26, 30, (255, 130, 160))
        pen.dot(104 * k, -6, 5, INK)
        pen.dot(116 * k, 6, 5, INK)
        pen.dot(50 * k, -30 * k, 8, INK)
        pen.line([(-20, -76 * k), (30, -76 * k)], 8)
    return (fn, ox, oy, s, {})


def coin(ox, oy, s, ang):
    def fn(pen, p):
        pen.ellipse(0, 0, 34 * abs(math.cos(ang)) + 4, 34, (255, 200, 60))
        pen.line([(0, -16), (0, 16)], 5, (220, 150, 30))
    return (fn, ox, oy, s, {})


def tear_calendar(ox, oy, s, label, flip):
    """Wall tear-off calendar: shows `label`; a page flies away while flip goes 0..1."""
    def fn(pen, p):
        pen.poly([(-90, -110), (90, -110), (90, 110), (-90, 110)], (255, 252, 244))
        pen.poly([(-90, -110), (90, -110), (90, -60), (-90, -60)], (220, 70, 60))
        for x in (-50, 50):
            pen.ellipse(x, -112, 10, 16, (200, 200, 210))
    return (fn, ox, oy, s, {})


# ------------------------------------------------------------------ poses
A0 = dict(C.ALEX)
M0 = dict(C.MISHA)
A_PHONE = dict(la=(14.0, -150.0), phone_hand='l', phone_glow=True, look=(0.25, 0.6))
M_PHONE = dict(la=(14.0, -145.0), phone_hand='l', phone_glow=True, look=(0.3, 0.6))


def alex(t, base=None, **kw):
    p = dict(A0, t=t)
    p.update(base or {})
    p['eye_open'] = p['eye_open'] * blink(t, 0.4)
    p['bob'] = math.sin(t * 2.1) * 4
    p.update(kw)
    if 'mouth' not in kw:
        p['mouth'] = talk(t, 'A') * 0.75
    return p


def misha(t, base=None, **kw):
    p = dict(M0, t=t)
    p.update(base or {})
    p['eye_open'] = p['eye_open'] * blink(t, 1.9)
    p['bob'] = math.sin(t * 1.8 + 1) * 5
    p.update(kw)
    if 'mouth' not in kw:
        p['mouth'] = talk(t, 'M') * 0.8
    return p


# ------------------------------------------------------------------ shots
def shot_hook_face(t):
    z = 2.55 + 0.25 * t / E.HOOK_CUT
    p = alex(t, A_PHONE, thin=1.0, pale=1.0, smile=0.1, look=(0.1, 0.75), sweat=0.6, brow=(4, -4))
    im = stage(S.hallway(), ALEX_X, 690, z, [(C.draw_alex, ALEX_X, 1.05, p)])
    glow = fx.radial(900, (140, 190, 255), power=1.8, peak=0.16)
    put(im, glow, W / 2, 1500)
    put(im, text_sprite('3 ГОДА', 150, GOLD, 'Heavy', 12), W / 2, 330, 1, pop(t, 0.05))
    put(im, text_sprite('БЕЗ ОБЕДОВ', 110, (255, 255, 255), 'Heavy', 11), W / 2, 480, 1, pop(t, E.wt('hook', 'обедов') - 0.1))
    return im


def craft_state(t, mode):
    """Phone screen state for Алексей (mode 'a') or Михаил (mode 'm') at content time t."""
    if mode == 'hook':
        return dict(t=t, models=config.BURNED, filled=[1] * 4, show_chance=1, chance=89)
    if mode == 'a':
        filled = [ramp(t, s, s + 0.3) * 1.0 + (t >= s + 0.3) * 0 for s in E.SLOT_T]
        filled = [min(1, max(0, (t - s) / 0.3)) for s in E.SLOT_T]
        ch = 89 * fx.ease_out(min(1, max(0, (t - E.CHANCE0) / (E.CHANCE1 - E.CHANCE0))))
        st = dict(t=t, models=config.BURNED, filled=filled, show_chance=ramp(t, E.SLOT_T[0], E.SLOT_T[0] + 0.3),
                  chance=ch, press=min(1, max(0, (t - E.PRESS + 0.12) / 0.3)),
                  vortex=min(1, max(0, (t - E.VORTEX0) / (E.VORTEX1 - E.VORTEX0))),
                  burn=min(1, max(0, (t - E.BURN0) / 0.9)), ash=min(1, max(0, (t - E.ASH0) / 0.9)),
                  fail=min(1, max(0, (t - E.FAIL) / 0.35)) if t >= E.FAIL else 0.0)
        return st
    filled = [min(1, max(0, (t - E.SLOT2) / 0.3)), 0, 0, 0]
    ch = 22 * fx.ease_out(min(1, max(0, (t - E.CH2_0) / (E.CH2_1 - E.CH2_0 - 0.3))))
    return dict(t=t, models=['Monday'], filled=filled, show_chance=ramp(t, E.SLOT2, E.SLOT2 + 0.3), chance=ch,
                press=min(1, max(0, (t - E.PRESS2 + 0.1) / 0.25)),
                vortex=min(1, max(0, (t - E.PRESS2 - 0.08) / 0.45)),
                flash=min(1, max(0, (t - E.FLASH2 + 0.18) / 0.18)), subtitle='Один подарок — тоже можно')


@functools.lru_cache(maxsize=4)
def blurred(name, z):
    bg = S.hallway() if name == 'hall' else S.canteen()
    im = S.view(bg, 540, 900, z).filter(ImageFilter.GaussianBlur(14))
    return Image.blend(im, Image.new('RGB', im.size, (10, 14, 26)), 0.55)


def phone_frame(t, st, scale=0.8, cy=1000, thumb=None, shake_amp=0.0, bg='hall', fire_light=0.0):
    im = blurred(bg, 1.2).convert('RGBA')
    if fire_light > 0:
        put(im, fx.radial(1600, (255, 120, 40), power=1.4, peak=0.55 * fire_light), W / 2, 1100)
    ph = P.screen(st)
    if thumb is not None:
        P.thumb(ph, *thumb)
    sx, sy = shake_amp * math.sin(t * 83), shake_amp * math.cos(t * 67)
    put(im, ph, W / 2 + sx, cy + sy, 1, scale)
    return im


def shot_hook_phone(t):
    u = t - E.HOOK_CUT
    st = craft_state(t, 'hook')
    tx = 540 + 6 * math.sin(t * 40)                        # trembling thumb above the button
    im = phone_frame(t, st, 0.74, 1080, thumb=(tx, 1700 + 40 * math.sin(t * 3), 0.0,
                                                (246, 232, 220)), shake_amp=1.5)
    put(im, text_sprite('РАДИ ОДНОЙ\nКНОПКИ', 104, (255, 255, 255), 'Heavy', 11), W / 2, 330, 1, pop(t, E.HOOK_CUT + 0.05))
    return im


def shot_canteen(t):
    u = t - E.CANTEEN
    n = sum(t >= c + 0.35 for c in E.COINS)
    thin = keys(t, [(E.CANTEEN, 0.0), (E.COINS[2], 0.45), (E.FULL, 1.0)])
    pale = keys(t, [(E.CANTEEN, 0.0), (E.COINS[3], 1.0)])
    give = max([math.sin(min(1, max(0, (t - c + 0.15) / 0.5)) * math.pi) for c in E.COINS] + [0])
    p = alex(t, thin=thin, pale=pale, smile=0.35 - 0.3 * thin, look=(0.6, 0.1), ra=(30 + 60 * give, -20 - 40 * give),
             sway=0, lean=keys(t, [(E.FULL - 0.2, 0), (E.FULL + 0.3, -40), (E.FULL + 0.7, 0)]))
    m = misha(t, bun=1, chew=1, ra=(10, -130), look=(-0.4, 0), smile=0.6)
    cx = 600 + 25 * u
    z = 1.1
    piggy_fill = n / 4 + ramp(t, E.FULL, E.FULL + 0.3) * 0.2
    def extra(to, z_):
        out = []
        px, py = to(640, 830)
        out.append(piggy(px, py, z_ * 0.95, piggy_fill))
        hx, hy = to(ALEX_X + 120, S.FLOOR - 560)
        for c in E.COINS:
            k = (t - c) / 0.4
            if 0 <= k <= 1:
                x = hx + (px - hx) * k
                y = hy + (py - 70 * z_ - hy) * k - math.sin(k * math.pi) * 180 * z_
                out.append(coin(x, y, z_ * 0.9, t * 12))
        return out
    im = stage(S.canteen(), cx, 1000, z,
               [(C.draw_misha, MISHA_X + 180, 0.88, m), (C.draw_alex, ALEX_X - 30, 1.05, p)], extra)
    # tear-off calendar sticker: years flip with every coin (time passing)
    years = ['2023', '2024', '2025', '2026', '2026']
    cal = text_sprite(years[min(n, 4)], 64, (220, 70, 60), 'Heavy', 0)
    box = Image.new('RGBA', (220, 230), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle([6, 6, 214, 224], 18, fill=(255, 252, 244), outline=INK, width=7)
    d.rounded_rectangle([6, 6, 214, 70], 18, fill=(220, 70, 60), outline=INK, width=7)
    d.text((110, 40), 'ОБЕДЫ', font=fx.font('Heavy', 30), fill=(255, 255, 255), anchor='mm')
    d.text((110, 150), years[min(n, 4)], font=fx.font('Heavy', 66), fill=INK, anchor='mm')
    put(im, box, 920, 250, 1, 1, 4 * math.sin(t * 2))
    for c in E.COINS:                                      # flying page
        k = (t - c) / 0.5
        if 0 <= k <= 1:
            put(im, box, 920 - 260 * k, 250 - 120 * k + 500 * k * k, 1 - k, 1 - 0.3 * k, 60 * k)
    if t >= E.FULL:
        put(im, fx.solid_pill('КОПИЛКА ПОЛНА', (255, 140, 170), 40, (255, 255, 255), 'Heavy'),
            W / 2 + 160, 1180, 1, pop(t, E.FULL))
    return im


def shot_vault(t):
    u = t - E.VAULT
    im = Image.fromarray(S3.vault(u, t)).convert('RGBA')
    put(im, text_sprite('57 КАЛЕНДАРЕЙ', 92, (255, 255, 255), 'Heavy', 10), W / 2, 300, 1, pop(t, E.ON[2] - 0.05))
    put(im, text_sprite('ТОЛЬКО ИЗ КРАФТА', 76, (150, 210, 255), 'Heavy', 9), W / 2, 410, 1, pop(t, E.wt('vault3d', 'только') - 0.05))
    if t >= E.LEGEND_WORD - 0.05:
        put(im, text_sprite('ЛЕГЕНДАРНЫХ — 5', 88, GOLD, 'Heavy', 10), W / 2, 1640, 1, pop(t, E.LEGEND_WORD - 0.05))
    put(im, text_sprite('Desk Calendar · api.changes.tg · 05.11.2026', 26, (200, 200, 220), 'Medium', 3),
        W / 2, 1830, 0.8)
    fl = max(0.0, 1 - u / 0.2)
    if fl > 0:
        im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(255 * fl))))
    return im


def shot_first(t):
    u = t - E.FIRST
    up = ramp(t, E.wt('first', 'наконец') - 0.1, E.wt('first', 'наконец') + 0.35)
    high = ramp(t, E.wt('first', 'крафт') - 0.2, E.wt('first', 'крафт') + 0.2)
    p = alex(t, A_PHONE, thin=1.0, pale=1.0, smile=1.0, tears=0.8, brow=(-14, 4), eye_open=1.0 * blink(t),
             look=(0.1, -0.4 + 0.9 * (1 - high)), wide=0.3)
    p['la'] = (14 + 140 * high, -150 + 140 * high)
    p['mouth'] = max(0.25, talk(t, 'A'))
    p['bob'] = -20 * up + math.sin(t * 9) * 6 * up
    z = 1.45 + 0.25 * u / (E.PHONE1 - E.FIRST)
    im = stage(S.hallway(), ALEX_X + 40, 900, z, [(C.draw_alex, ALEX_X, 1.05, p)])
    if high > 0.5:
        for k in range(8):
            a = k / 8 * 2 * math.pi + t
            fx_ = 540 - (ALEX_X + 40 - ALEX_X) * z
            put(im, fx.radial(120, (255, 230, 120), power=3, peak=0.8), 300 + 240 * math.cos(a), 420 + 160 * math.sin(a))
    return im


def shot_phone1(t):
    st = craft_state(t, 'a')
    thumb = None
    if E.THUMB_IN <= t < E.PRESS + 0.6:
        k_in = fx.ease_out(min(1, (t - E.THUMB_IN) / 0.5))
        k_out = fx.ease_in(min(1, max(0, (t - E.PRESS - 0.15) / 0.4)))
        y = 1900 + (1610 - 1900) * k_in + 500 * k_out
        thumb = (540 + 4 * math.sin(t * 37), y, min(1, max(0, (t - E.PRESS + 0.12) / 0.15)) * (1 - k_out),
                 (246, 232, 220))
    burn = st['burn']
    sh = 10 * burn * (1 - st['ash']) + 3 * st['vortex']
    z = 0.8 + 0.06 * st['vortex']
    return phone_frame(t, st, z * 0.95, 880, thumb, sh, fire_light=burn * (1 - 0.6 * st['ash']))


def shot_face(t):
    u = t - E.FACE
    smile = keys(t, [(E.FACE, 1.0), (E.FACE + 0.8, 1.0), (E.SMILE_GONE, 0.05), (E.REALISE, -0.25), (E.RAGE, -0.45)])
    wide = keys(t, [(E.SMILE_GONE, 0.0), (E.REALISE + 0.2, 0.9)])
    p = alex(t, A_PHONE, thin=1.0, pale=1.0, smile=smile, mouth=max(0, smile) * 0.35,
             eye_open=(0.75 + 0.25 * wide) * blink(t), look=(0.05, 0.8 - 0.6 * wide), wide=wide,
             sweat=ramp(t, E.REALISE, E.REALISE + 0.4), twitch=float(t > E.REALISE + 0.3 and int(t * 9) % 3 == 0),
             brow=(keys(t, [(E.FACE, -12), (E.SMILE_GONE, 0), (E.REALISE, -16)]), 0))
    z = 2.5 + 0.35 * fx.smooth(u / (E.RAGE - E.FACE))
    im = stage(S.hallway(), ALEX_X, 700, z, [(C.draw_alex, ALEX_X, 1.05, p)])
    put(im, fx.radial(1100, (255, 150, 70), power=1.5, peak=0.16 * (1 - ramp(t, E.FACE, E.FACE + 2))), W / 2, 1750)
    for k, (name, rus, tw) in enumerate((('Burning Time', 'Горящее время', E.wt('burned', 'горящее')),
                                         ('Heartbreak', 'Разбитое сердце', E.wt('burned', 'разбитое')))):
        if t >= tw - 0.05:
            a = 1 - ramp(t, E.SMILE_GONE + 0.3, E.SMILE_GONE + 0.8)
            spr = text_sprite(f'{name}\n{rus}', 58, (190, 190, 196), 'Heavy', 7)
            x, y = W / 2 + (-60 if k == 0 else 60), 290 + k * 190 - (t - tw) * 14
            put(im, spr, x, y, a, pop(t, tw - 0.05), -6 if k == 0 else 5)
            d = ImageDraw.Draw(im)
            ww = spr.width * 0.42
            if a > 0.05:
                d.line([(x - ww, y + 10), (x + ww, y - 6)], fill=RED + (int(255 * a),), width=10)
    if t >= E.wt('burned', 'намекали') - 0.05:
        put(im, text_sprite('НАЗВАНИЯ\nНАМЕКАЛИ', 84, (255, 255, 255), 'Heavy', 9), W / 2, 360, 1,
            pop(t, E.wt('burned', 'намекали') - 0.05))
    return im


SHARDS = [(math.cos(a) * r, math.sin(a) * r, s) for a, r, s in
          zip(np.linspace(0, 2 * math.pi, 11, endpoint=False), [1.0, 0.7, 1.2, 0.9, 1.1, 0.8, 1.3, 1.0, 0.75, 1.15, 0.95],
              [1.0, 0.7, 0.9, 1.2, 0.8, 1.1, 0.7, 1.0, 0.9, 0.8, 1.1])]
WALL = (150.0, 930.0)                                # impact point on the locker (stage)
RAGE_X = 610.0                                       # Алексей stands away from the lockers


def rage_frame(t):
    red = ramp(t, E.RAGE, E.RAGE + 1.3) * (1 - 0.4 * ramp(t, E.IMPACT + 0.4, E.IMPACT + 1.5))
    wind = ramp(t, E.SCREAM - 0.35, E.SCREAM + 0.1)
    throw = ramp(t, E.THROW - 0.12, E.THROW + 0.12)
    shake_amt = ramp(t, E.RAGE + 0.5, E.SCREAM) * (1 - throw)
    p = alex(t, thin=1.0, pale=1.0, red=red, angry=red, smile=-0.6, steam=red, shake=shake_amt * 1.4,
             brow=(6, 0), look=(-0.2 * throw, 0.1), eye_open=0.85, la=(18, -10))
    p['mouth'] = max(talk(t, 'A'), 0.25 * red)
    # right arm: phone at the chest -> wind-up overhead -> throw forward (screen left)
    chest = (14.0, -150.0)
    over = (165.0, 35.0)
    fwd = (-60.0, -10.0)
    ra = tuple(C.lerp(C.lerp(a, b, wind), c, throw) for a, b, c in zip(chest, over, fwd))
    p['ra'] = ra
    if t < E.THROW:
        p['phone_hand'] = 'r'
    p['phone_glow'] = False
    p['lean'] = -60 * throw + 40 * wind * (1 - throw)
    pant = ramp(t, E.IMPACT + 0.3, E.IMPACT + 0.8)
    p['mouth'] = max(p['mouth'], 0.4 * pant * (0.5 + 0.5 * math.sin(t * 9)))
    z = 1.42
    cx = 480 - 20 * throw
    sx, sy = shake(t, E.IMPACT, 0.45, 24)
    cx += sx / z
    cyy = 940 + sy / z

    def extra(to, z_):
        out = []
        if E.THROW <= t < E.IMPACT:
            k = (t - E.THROW) / (E.IMPACT - E.THROW)
            hx, hy = RAGE_X + 120, S.FLOOR - 1010
            x = hx + (WALL[0] - hx) * k
            y = hy + (WALL[1] - hy) * k - math.sin(k * math.pi) * 300
            X, Y = to(x, y)
            out.append((lambda pen, q, a=t * 1400: C.phone(pen, 0, 0, a, 1.0, (36, 48, 80)), X, Y, z_ * 1.05, {}))
        if t >= E.IMPACT:
            u = t - E.IMPACT
            for j, (dx, dy, s) in enumerate(SHARDS):
                x = WALL[0] + dx * 260 * (1 - math.exp(-u * 4)) + dx * 30 * u
                y = WALL[1] + dy * 200 * (1 - math.exp(-u * 4)) + 420 * u * u
                y = min(y, S.FLOOR + 20 + j * 6)
                X, Y = to(x, y)
                rot = j * 40 + u * 300 * (1 if j % 2 else -1) * math.exp(-u)
                def shard(pen, q, rot=rot, s=s, j=j):
                    c, sn = math.cos(math.radians(rot)), math.sin(math.radians(rot))
                    pts = [(-22 * s, -14 * s), (20 * s, -20 * s), (12 * s, 18 * s), (-16 * s, 12 * s)]
                    col = (36, 48, 80) if j % 3 else (180, 200, 230)
                    pen.poly([(x_ * c - y_ * sn, x_ * sn + y_ * c) for x_, y_ in pts], col)
                out.append((shard, X, Y, z_, {}))
        return out
    im = stage(S.hallway(), cx, cyy, z, [(C.draw_alex, RAGE_X, 1.05, p)], extra)
    if t >= E.IMPACT:
        u = t - E.IMPACT
        X, Y = 540 + (WALL[0] - cx) * z, 960 + (WALL[1] - cyy) * z
        put(im, fx.radial(500, (255, 255, 230), power=2, peak=max(0, 1 - u / 0.3)), X, Y)
        put(im, text_sprite('БАХ!', 130, (255, 230, 80), 'Heavy', 12), X + 120, Y - 260, 1 - ramp(t, E.IMPACT + 0.9, E.IMPACT + 1.3),
            pop(t, E.IMPACT, 0.25), 10)
        d = ImageDraw.Draw(im)                           # dent / cracks on the locker
        for j in range(7):
            a = j / 7 * 2 * math.pi + 0.3
            d.line([(X, Y), (X + math.cos(a) * 90, Y + math.sin(a) * 90)], fill=INK + (255,), width=6)
    return im


def shot_rage(t):
    return rage_frame(t)


def shot_freeze(t):
    u = t - E.FREEZE
    base = rage_frame(E.FREEZE_AT).convert('RGB')
    z = 1 + 0.05 * fx.smooth(min(1, u / 4))
    if z > 1.001:
        w, h = W / z, H / z
        base = base.transform((W, H), Image.EXTENT, ((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2), Image.BILINEAR)
    g = Image.blend(base.convert('L').convert('RGB'), Image.new('RGB', (W, H), (255, 255, 255)), 0.12)
    im = Image.blend(base, g, min(1, u / 0.15) * 0.3).convert('RGBA')      # light «paused» look, colours kept
    put(im, text_sprite('СТОП-КАДР', 120, (255, 255, 255), 'Heavy', 12), W / 2, 330, 1, pop(t, E.FREEZE), -4)
    fl = max(0.0, 1 - u / 0.12)
    if fl > 0:
        im.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 255, int(220 * fl))))
    return im


def shot_talk(t):
    """After RubUp: Михаил walks in, Алексей tells, Михаил thinks and takes out his phone."""
    walk_k = ramp(t, E.MISHA_IN - 0.4, E.MISHA_IN + 0.9)
    mx = 1450 + (MISHA_X - 1450) * walk_k
    walking = 0 < walk_k < 1
    think = ramp(t, E.THINK, E.THINK + 0.6) * (1 - ramp(t, E.PHONE_OUT - 0.1, E.PHONE_OUT + 0.2))
    phone_out = ramp(t, E.PHONE_OUT - 0.2, E.PHONE_OUT + 0.3)
    m = misha(t, bun=1 - phone_out * 0, chew=1 - ramp(t, E.TRY - 0.3, E.TRY), walk=(t * 1.6) % 1 if walking else 0,
              look=(-0.6, 0.1), think=think, smile=0.45 + 0.4 * phone_out, ra=(10, -130))
    if phone_out > 0.5:
        m.update(M_PHONE)
        m['look'] = (-0.2, 0.5)
    m['la'] = tuple(C.lerp(a, b, phone_out) for a, b in zip((14.0, -8.0), (14.0, -145.0)))
    if phone_out <= 0.5:
        m['la'] = (14.0 + 10 * think, -8.0 - 140 * think)       # hand to the chin while thinking
    sad = 1.0
    a = alex(t, thin=1.0, pale=1.0, sad=sad, smile=-0.55, tears=0.8 if t >= E.TELLS else 0.3,
             look=(0.6, 0.2), la=(14.0, -150.0), phone_hand='l', cracked=True, phone_glow=False, brow=(6, 0))
    # camera: wide on the entrance -> push to Алексей while he speaks -> to Михаил
    z = keys(t, [(E.RESUME, 1.12), (E.TELLS - 0.2, 1.12), (E.TELLS + 0.6, 1.5), (E.TRY - 0.3, 1.5), (E.TRY + 0.5, 1.55)])
    cx = keys(t, [(E.RESUME, 560), (E.TELLS - 0.2, 560), (E.TELLS + 0.6, 450), (E.TRY - 0.3, 450), (E.TRY + 0.5, 700)])
    cy = keys(t, [(E.RESUME, 980), (E.TELLS + 0.6, 920), (E.TRY + 0.5, 930)])
    return stage(S.hallway(), cx, cy, z, [(C.draw_alex, ALEX_X, 1.05, a), (C.draw_misha, mx, 1.0, m)])


def shot_phone2(t):
    st = craft_state(t, 'm')
    thumb = None
    if E.PRESS2 - 0.6 <= t < E.FLASH2:
        k_in = fx.ease_out(min(1, (t - E.PRESS2 + 0.6) / 0.35))
        y = 1900 + (1610 - 1900) * k_in
        thumb = (600, y, min(1, max(0, (t - E.PRESS2 + 0.1) / 0.15)), (255, 222, 200))
    return phone_frame(t, st, 0.76, 880, thumb, 2 * st['vortex'])


def shot_legend(t):
    u = t - E.LEGEND
    im = Image.fromarray(S3.legend(u, t, config.LEGEND)).convert('RGBA')
    put(im, text_sprite('LEGENDARY', 110, GOLD, 'Heavy', 10), W / 2, 225, 1, pop(t, E.LEGEND + 0.35))
    put(im, text_sprite('Celestial Map · фон Black', 52, (235, 235, 240), 'Heavy', 7), W / 2, 1660, 1,
        pop(t, E.LEGEND + 0.8))
    return im


@functools.lru_cache(None)
def offer_card(state):
    card = Image.new('RGBA', (700, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([6, 6, 694, 324], 44, fill=(28, 36, 58), outline=INK, width=8)
    d.text((40, 60), 'Предложение о покупке', font=fx.font('Bold', 34), fill=(150, 170, 210), anchor='lm')
    d.text((40, 125), 'Celestial Map', font=fx.font('Heavy', 50), fill=GOLD, anchor='lm')
    d.text((660, 125), '100 ₽', font=fx.font('Heavy', 56), fill=(255, 255, 255), anchor='rm')
    col = (42, 171, 238) if state == 0 else GREEN
    d.rounded_rectangle([40, 200, 660, 290], 45, fill=col)
    d.text((350, 245), 'Принять' if state == 0 else 'Продано ✓', font=fx.font('Heavy', 44), fill=(255, 255, 255), anchor='mm')
    return card


def shot_ugly(t):
    fu = ramp(t, E.UGLY - 0.05, E.UGLY + 0.2) * (1 - ramp(t, E.OFFER - 0.25, E.OFFER + 0.05))
    m = misha(t, M_PHONE, disgust=fu, smile=0.5 + 0.4 * ramp(t, E.OFFER, E.OFFER + 0.3), look=(0.25, 0.6 - 0.3 * fu))
    acc = ramp(t, E.ACCEPT - 0.25, E.ACCEPT)
    a = alex(t, thin=1.0, pale=1.0, wide=0.6, eye_open=1.0, smile=-0.3, look=(0.8, 0.3), mouth=0.15 + 0.3 * acc,
             jaw=acc * 0.6, la=(14.0, -150.0), phone_hand='l', cracked=True, phone_glow=False)
    z = 1.62
    cx = 720 + 20 * fx.smooth((t - E.UGLY) / 4)
    im = stage(S.hallway(), cx, 860, z, [(C.draw_alex, ALEX_X, 1.05, a), (C.draw_misha, MISHA_X, 1.0, m)])
    if t >= E.OFFER - 0.1:
        put(im, offer_card(int(t >= E.ACCEPT)), W / 2 + 40, 330, 1, pop(t, E.OFFER - 0.1) * (1 + 0.08 * math.exp(-max(0, t - E.HUNDRED) * 6) * (t > E.HUNDRED)))
    if E.ACCEPT - 0.3 <= t < E.ACCEPT + 0.25:
        put(im, fx.radial(180, (255, 255, 255), power=2, peak=0.8), W / 2 + 40, 375)
    return im


def shot_pizza(t):
    leave = ramp(t, E.LEAVE, E.SHOCK + 0.15)
    mx = MISHA_X + (-700 - MISHA_X) * leave
    m = misha(t, smile=1.0, look=(-0.6 * (leave > 0), 0), walk=(t * 1.7) % 1 if 0 < leave < 1 else 0,
              pizza=0, ra=(120 * (1 - leave), 30), la=(14.0, -8.0))
    a = alex(t, thin=1.0, pale=1.0, jaw=0.3, wide=1.0, eye_open=1.0, smile=-0.15, mouth=0.55,
             look=(0.9 - 1.6 * leave, 0.0), twitch=float(int(t * 8) % 3 == 0), la=(14.0, -150.0), phone_hand='l',
             cracked=True, phone_glow=False, brow=(-16, 0))
    z = 1.2
    im = stage(S.hallway(), 560, 960, z, [(C.draw_misha, mx, 1.0, m), (C.draw_alex, ALEX_X, 1.05, a)])
    # pizza thought bubble above Михаил
    if t < E.LEAVE + 0.4:
        X = 540 + (mx - 560) * z + 150
        s = pop(t, E.wt('pizza', 'пиццу') - 0.1)
        if s > 0:
            b = Image.new('RGBA', (300, 260), (0, 0, 0, 0))
            d = ImageDraw.Draw(b)
            d.ellipse([10, 10, 290, 220], fill=(255, 255, 255), outline=INK, width=8)
            d.polygon([(90, 50), (210, 50), (150, 190)], fill=(250, 196, 80), outline=INK)
            d.line([(84, 48), (216, 48)], fill=(210, 130, 60), width=22)
            for px, py in ((125, 80), (170, 85), (150, 125)):
                d.ellipse([px - 13, py - 13, px + 13, py + 13], fill=(200, 50, 50))
            put(im, b, W / 2 + 190, 300, 1 - ramp(t, E.LEAVE, E.LEAVE + 0.4), s)
    if t >= E.wt('pizza', 'продал') - 0.1:
        put(im, fx.solid_pill('+100 ₽', GREEN, 54, (255, 255, 255), 'Heavy'), W / 2 + 200, 560,
            1 - ramp(t, E.SHOCK - 0.3, E.SHOCK), pop(t, E.wt('pizza', 'продал') - 0.1))
    return im


def shot_shock(t):
    u = t - E.SHOCK
    wtf = getattr(E, 'WTF', None)                    # optional «Ты чё…» line (not in the v1 voice-over)
    yell = ramp(t, wtf - 0.1, wtf + 0.25) if wtf is not None else 0.0
    a = alex(t, thin=1.0, pale=1.0, jaw=0.3 - 0.3 * yell, wide=1.0 - 0.5 * yell, eye_open=1.0, smile=-0.15,
             mouth=0.6 if yell < 0.5 else max(0.2, talk(t, 'A')), look=(0, 0),
             twitch=float(int(t * 10) % 2 == 0 and yell < 0.5), brow=(-18 + 26 * yell, 0), angry=yell,
             red=0.7 * yell, steam=yell, shake=0.8 * yell * float(wtf is not None and t < E.END[E.L['wtf']]),
             la=(14.0, -150.0), phone_hand='l', cracked=True, phone_glow=False)
    z = 2.7 + 0.6 * fx.ease_out(min(1, u / 0.25)) - 0.5 * yell
    return stage(S.hallway(), ALEX_X, 700 + 60 * yell, z, [(C.draw_alex, ALEX_X, 1.05, a)])


def shot_moral(t):
    u = t - E.MORAL
    im = blurred('hall', 1.0).convert('RGBA')
    k = pop(t, E.MORAL)
    a = alex(t, thin=1.0, pale=1.0, sad=1, smile=-0.5, la=(14.0, -150.0), phone_hand='l', cracked=True,
             phone_glow=False, look=(0.3, 0.3))
    m = misha(t, pizza=1, ra=(150, 20), smile=1.0, chew=0.6, look=(-0.3, 0))
    lay = C.render_layer(W, H, [(C.draw_alex, 290, 1500, 0.66, a), (C.draw_misha, 800, 1500, 0.64, m)])
    im.alpha_composite(lay)
    put(im, fx.solid_pill('89% → сгорело', RED, 40, (255, 255, 255), 'Heavy'), 290, 1580, 1, pop(t, E.MORAL + 0.2))
    put(im, fx.solid_pill('22% → легендарка', GREEN, 40, (255, 255, 255), 'Heavy'), 800, 1580, 1, pop(t, E.MORAL + 0.45))
    put(im, text_sprite('МОРАЛЬ', 84, GOLD, 'Heavy', 9), W / 2, 260, 1, k)
    put(im, text_sprite('ПРОЦЕНТЫ НЕ ЗНАЮТ,', 70, (255, 255, 255), 'Heavy', 8), W / 2, 380, 1, pop(t, E.wt('moral', 'проценты') - 0.05))
    put(im, text_sprite('СКОЛЬКО ОБЕДОВ', 70, (255, 255, 255), 'Heavy', 8), W / 2, 470, 1, pop(t, E.wt('moral', 'сколько') - 0.05))
    put(im, text_sprite('ТЫ ПРОПУСТИЛ', 70, (255, 255, 255), 'Heavy', 8), W / 2, 560, 1, pop(t, E.wt('moral', 'ты') - 0.05))
    return im


@functools.lru_cache(None)
def like_icon():
    s = 300
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([6, 6, s - 6, s - 6], fill=(255, 64, 90), outline=INK, width=10)
    d.rounded_rectangle([80, 140, 126, 230], 10, fill=(255, 255, 255), outline=INK, width=6)
    d.polygon([(134, 140), (160, 70), (186, 76), (178, 132), (226, 134), (220, 226), (134, 228)],
              fill=(255, 255, 255), outline=INK)
    return im


def shot_cta(t):
    u = t - E.CTA
    a = alex(t, thin=1.0, pale=0.8, red=0.55, angry=0.8, smile=-0.5, brow=(6, 0), look=(0.8, 0), la=(14.0, -10.0))
    m = misha(t, pizza=1, ra=(150 + 20 * math.sin(t * 7), 20), smile=1.0, look=(-0.2, 0), chew=0.5)
    im = stage(S.hallway(), 560, 1000, 1.15, [(C.draw_alex, ALEX_X, 1.05, a), (C.draw_misha, MISHA_X, 1.0, m)])
    put(im, text_sprite('ЛАЙК, ЕСЛИ У ТЕБЯ\nТОЖЕ ЕСТЬ ТАКОЙ ДРУГ', 70, (255, 255, 255), 'Heavy', 9), W / 2, 330, 1,
        pop(t, E.CTA))
    put(im, like_icon(), W / 2, 1560, 1, pop(t, E.LIKE - 0.05, 0.45) * (1 + 0.06 * math.sin(max(0, t - E.LIKE) * 8)))
    bub = fx.solid_pill('А ты продал бы за 100 ₽?', (42, 171, 238), 44, (255, 255, 255), 'Heavy')
    put(im, bub, W / 2, 1790, 1, pop(t, E.wt('cta', 'друг') - 0.2))
    return im


SHOTS = [
    (0.0, shot_hook_face), (E.HOOK_CUT, shot_hook_phone), (E.CANTEEN, shot_canteen), (E.VAULT, shot_vault),
    (E.FIRST, shot_first), (E.PHONE1, shot_phone1), (E.FACE, shot_face), (E.RAGE, shot_rage),
    (E.FREEZE, shot_freeze), (E.RESUME, shot_talk), (E.PHONE2, shot_phone2), (E.LEGEND, shot_legend),
    (E.UGLY, shot_ugly), (E.PIZZA, shot_pizza), (E.SHOCK, shot_shock), (E.MORAL, shot_moral), (E.CTA, shot_cta),
]
CUTS = [s for s, _ in SHOTS[1:]]


def render_at(t):
    t = min(max(t, 0.0), DUR - 1e-3)
    fn = [f for s, f in SHOTS if t >= s][-1]
    im = fn(t)
    # quick zoom punch on every cut (keeps 2D cuts lively)
    for c in CUTS:
        if c <= t < c + 0.18 and fn not in (shot_vault, shot_legend, shot_freeze, shot_ugly):
            k = 1 + 0.04 * (1 - (t - c) / 0.18)
            w, h = W / k, H / k
            im = im.transform((W, H), Image.EXTENT, ((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2), Image.BILINEAR)
            break
    subtitles(im, t)
    out = np.asarray(im.convert('RGB'), np.float32)
    out += np.random.default_rng(int(t * FPS)).normal(0, 2.2, (H // 4, W // 4, 1)).repeat(4, 0).repeat(4, 1)
    fade = ramp(t, DUR - 0.35, DUR)
    out *= 1 - 0.85 * fade
    return np.clip(out, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Сначала хайлайты и слово автора «собирай» (config.STYLE_READY)')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
