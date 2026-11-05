"""05-time-pawnshop «Ломбард времени» — picture. A frame is a pure function of content time t.

Shots (content seconds, events.py): hook (3D counter, Pepe drops, the Saturday page burns) → room at night
(grandma's gift, the bot) → zoom through the phone into the 3D pawnshop → cheap deals → the rule → rich deals
(the world loses colour) → the safe → RubUp → the lot (orbit around Pepe) → «в другой раз», signature →
grandma's kitchen (silence) → he brings everything back → refusal + profile «от: Ломбард времени» → the
watchmaker offers Pepe to the viewer → vote cards.
"""
import functools
import math
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
import chars as C
import sets as S
import stage
import ui
from stage import Cam, billboard, quad
from timeline import DUR, ON, END, KEY, TAKES, HAS_NARRATION
from words import WORDS
from events import AD_STOP, S as SH, E

W, H, FPS = 1080, 1920, 60
BR = banner.Breaks([AD_STOP], cy=H / 2, speed=1.1)
COUNTER_Y = -0.75


# ------------------------------------------------------------------ small helpers
def sm(x):
    return fx.smooth(x)


def ramp(t, a, b):
    return fx.clamp01((t - a) / (b - a)) if b > a else float(t >= a)


def pop(t, t0, d=0.4):
    return fx.ease_out_back(ramp(t, t0, t0 + d)) if t >= t0 else 0.0


def lerp(a, b, k):
    return a + (b - a) * k


def lerp3(a, b, k):
    return [lerp(x, y, k) for x, y in zip(a, b)]


def blink(t, seed=0.0, every=3.3):
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
    """Mouth opening 0..1 from the loudness of the line(s) being spoken."""
    if not HAS_NARRATION:
        return 0.0
    for key in keys:
        k = KEY[key]
        if ON[k] <= t < END[k]:
            e = _env(k)
            i = int((t - ON[k]) * 100)
            return float(np.clip(e[min(i, len(e) - 1)] * 0.9, 0, 1))
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


def glow(canvas, x, y, r, rgb, a):
    if a <= 0.01:
        return
    g = _glow_spr(int(r), rgb)
    put(canvas, g, x, y, a)


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


def add_light(canvas, x, y, r, rgb, k):
    """Additive light (screen-like) — for lamps, the safe, fireflies."""
    if k <= 0.01:
        return
    base = np.asarray(canvas, np.float32)
    g = np.asarray(_glow_spr(int(r), rgb), np.float32)
    x0, y0 = int(x - r), int(y - r)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + 2 * r), min(H, y0 + 2 * r)
    if xb <= xa or yb <= ya:
        return canvas
    piece = g[ya - y0:yb - y0, xa - x0:xb - x0]
    reg = base[ya:yb, xa:xb, :3]
    reg += piece[..., :3] * (piece[..., 3:4] / 255) * k
    base[ya:yb, xa:xb, :3] = np.clip(reg, 0, 255)
    return Image.fromarray(base.astype(np.uint8), 'RGBA')


def desat(im, k):
    if k <= 0.01:
        return im
    out = ImageEnhance.Color(im).enhance(1 - k)
    return ImageEnhance.Brightness(out).enhance(1 - 0.18 * k)


@functools.lru_cache(maxsize=128)
def text_spr(text, size, rgb=(255, 255, 255), weight='Heavy', stroke=8, srgb=(20, 14, 18), shadow=True):
    f = fx.font(weight, size)
    lines = text.split('\n')
    lh = int(size * 1.12)
    w = int(max(f.getlength(s) for s in lines)) + 2 * stroke + 40
    h = lh * len(lines) + 2 * stroke + 40
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, s in enumerate(lines):
        d.text((w / 2, 20 + stroke + lh * k + lh / 2), s, font=f, fill=tuple(rgb) + (255,), anchor='mm',
               stroke_width=stroke, stroke_fill=tuple(srgb) + (255,))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.6)))
        out = Image.new('RGBA', im.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 0))
        out.alpha_composite(im)
        return out
    return im


@functools.lru_cache(maxsize=8)
def emoji(ch, size):
    from PIL import ImageFont
    f = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf', 109)
    im = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((70, 70), ch, font=f, embedded_color=True, anchor='mm')
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------ characters as sprites
def old_sprite(t, look=(0, 0), smile=0.45, open_=0.0, tilt=0.0, brow=0.0, sad=0.0, glint=None, bob=0.0):
    im = Image.new('RGBA', (900, 1150), (0, 0, 0, 0))
    g = (t * 0.35) % 1.0 if glint is None else glint
    head = C.old_head(look=look, blink=blink(t, 0.4), brow=brow, sad=sad, smile=smile, open_=open_, glint=g)
    C.place(im, C.bust(head, C.old_body(), 450, 470, tilt=tilt, bob=bob))
    return im


def leva_sprite(t, look=(0, 0.4), smile=0.3, open_=0.0, tilt=0.0, brow=0.0, sad=0.0, glow_=0.0, arms='phone',
                bob=0.0):
    im = Image.new('RGBA', (900, 1150), (0, 0, 0, 0))
    head = C.leva_head(look=look, blink=blink(t, 1.3, 2.9), brow=brow, sad=sad, smile=smile, open_=open_,
                       glow=glow_)
    C.place(im, C.bust(head, C.leva_body(arms, glow_), 450, 470, tilt=tilt, bob=bob))
    return im


# ------------------------------------------------------------------ the pawnshop (3D)
@functools.lru_cache(None)
def wall_tex(blur=0):
    im = S.shop_wall()
    return im.filter(ImageFilter.GaussianBlur(blur)) if blur else im


WALL_Z = 5.6
WALL_W_M, WALL_H_M = S.WALL_W / 400, S.WALL_H / 400
WALL_CY = 0.45
SAFE = (-1.15, 0.85, WALL_Z - 0.02)
SAFE_R = 0.42
CLOCKS = [(1.25, 1.55, 0.26, 0.0), (0.55, 1.95, 0.18, 0.3), (-0.35, 1.75, 0.22, 0.6), (1.45, 0.55, 0.16, 0.15)]


def gift_live(name, model, t, size=300, offset=0.0):
    return ui.gift(name, model, t, size, offset)


SLOTS = {  # counter positions (x, z) and heights for gifts
    'jar': (0.48, 3.0, 0.44), 'cal': (-0.48, 2.95, 0.4), 'cookie': (-0.18, 2.5, 0.27),
    'globe': (0.12, 2.45, 0.31), 'player': (-0.62, 2.42, 0.32), 'cap': (0.5, 2.45, 0.28),
}
GIFTS = {
    'jar': ('Restless Jar', 'Fireflies'), 'cookie': ('Ginger Cookie', 'Coffee Break'),
    'globe': ('Snow Globe', 'Winter'), 'player': ('Record Player', 'Sunset Beach'),
    'cap': ("Durov's Cap", 'Seabreeze'), 'pepe': ('Plush Pepe', 'Midas Pepe'),
    'sat': ('Desk Calendar', 'Saturday'), 'sun': ('Desk Calendar', 'Sunday'), 'cal': ('Desk Calendar', None),
}
APPEAR = {'cookie': E['cookie'], 'globe': E['globe'], 'player': E['player'], 'cap': E['cap']}
TAKE_AWAY = SH['safe'] - 0.45            # Лёва takes the gifts at the end of «rich»
BRING_BACK = E['pour']


def counter_gifts(t):
    """[(key, x, z, height, scale_mul, y_lift)] standing on the counter at time t."""
    out = []
    for key in ('cookie', 'globe', 'player', 'cap'):
        t0 = APPEAR[key]
        x, z, h = SLOTS[key]
        if t < t0:
            continue
        if TAKE_AWAY <= t < BRING_BACK:
            u = ramp(t, TAKE_AWAY + 0.06 * list(APPEAR).index(key), TAKE_AWAY + 0.4)
            if u >= 1:
                continue
            out.append((key, x * (1 - u), z - 1.8 * fx.ease_in(u), h, 1.0, 0.25 * math.sin(math.pi * u)))
            continue
        if t >= BRING_BACK:                                  # thrown back onto the counter
            k = list(APPEAR).index(key)
            t1 = BRING_BACK + 0.12 + 0.14 * k
            if t < t1:
                continue
            u = t - t1
            y = max(0.0, 0.9 * (1 - u / 0.32)) if u < 0.32 else abs(math.sin(u * 9)) * 0.06 * math.exp(-5 * u)
            out.append((key, x, z, h, 1.0, y))
            continue
        s = pop(t, t0, 0.45)
        out.append((key, x, z, h, s, 0.0))
    return out


def shop(t, cam, who=True, hands=True, items=True, wall_blur=1, light=1.0, old_pose=None, extra=None,
         gray=0.0, cal_model=None, pepe=None, leva_back=None, safe_open=0.0, lamp_k=1.0, dark=0.0, slots=None, gifts_on=True):
    im = Image.new('RGBA', (W, H), (20, 14, 12, 255))
    # back wall (with optional colour drain)
    wl = wall_tex(wall_blur)
    if gray:
        wl = desat(wl, gray)
    hw, hh = WALL_W_M / 2, WALL_H_M / 2
    quad(im, wl, [(-hw, WALL_CY + hh, WALL_Z), (hw, WALL_CY + hh, WALL_Z), (hw, WALL_CY - hh, WALL_Z),
                  (-hw, WALL_CY - hh, WALL_Z)], cam)
    # clocks on the wall
    for cx, cy, r, ph in CLOCKS:
        ck = S.clock(t, r=int(r * 400), speed=1.0, phase=ph)
        quad(im, ck, [(cx - r, cy + r, WALL_Z - 0.01), (cx + r, cy + r, WALL_Z - 0.01),
                      (cx + r, cy - r, WALL_Z - 0.01), (cx - r, cy - r, WALL_Z - 0.01)], cam)
    # safe: body in the wall, door swings on its left hinge (3D quad)
    sx, sy, sz = SAFE
    r = SAFE_R
    quad(im, S.safe_body(), [(sx - r * 1.12, sy + r * 1.12, sz), (sx + r * 1.12, sy + r * 1.12, sz),
                             (sx + r * 1.12, sy - r * 1.12, sz), (sx - r * 1.12, sy - r * 1.12, sz)], cam)
    if safe_open > 0:
        p = cam.project((sx, sy, sz))
        if p:
            k = cam.k / p[2]
            im = add_light(im, p[0], p[1], int(r * k * 0.95), (255, 200, 110), 1.2 * safe_open)
    a = math.radians(105) * fx.ease_out(safe_open)
    hx = sx - r
    ex, ez = hx + 2 * r * math.cos(a), sz - 2 * r * math.sin(a)
    quad(im, S.safe_door(), [(hx, sy + r, sz - 0.005), (ex, sy + r, ez - 0.005), (ex, sy - r, ez - 0.005),
                             (hx, sy - r, sz - 0.005)], cam)
    if gray:
        im = desat(im, gray * 0.6)
    # lamp
    lp = billboard(im, S.lamp(), (0.15, 1.05, 3.2), 1.9, cam, anchor=(0.5, 0.85))
    # watchmaker
    if who:
        pose = dict(old_pose or {})
        sp = old_sprite(t, **pose)
        if gray:
            sp = desat(sp, gray * 0.7)
        billboard(im, sp, (0.0, -0.86, 3.72), 1.15, cam)
    if lp and lamp_k:
        im = add_light(im, lp[0], lp[1] + 40, 520, (255, 196, 120), 0.32 * lamp_k * light)
    # counter: top and front
    quad(im, S.counter_top(), [(-1.9, COUNTER_Y, 3.45), (1.9, COUNTER_Y, 3.45), (1.9, COUNTER_Y, 2.15),
                               (-1.9, COUNTER_Y, 2.15)], cam)
    quad(im, S.counter_front(), [(-1.9, COUNTER_Y, 2.15), (1.9, COUNTER_Y, 2.15), (1.9, COUNTER_Y - 1.9, 2.15),
                                 (-1.9, COUNTER_Y - 1.9, 2.15)], cam)
    if who and hands:
        hs = C.old_hands()
        billboard(im, desat(hs, gray * 0.7) if gray else hs, (0.0, COUNTER_Y - 0.07, 3.36), 0.32, cam)
    labels = []
    if items:
        objs = []
        sl = dict(SLOTS, **(slots or {}))
        x, z, h = sl['jar']
        objs.append((z, 'jar', x, h, 1.0, 0.0))
        x, z, h = sl['cal']
        objs.append((z, cal_model or 'cal', x, h, 1.0, 0.0))
        for key, gx, gz, gh, s, yl in (counter_gifts(t) if gifts_on else []):
            objs.append((gz, key, gx, gh, s, yl))
        if pepe:
            objs.append(pepe)
        for z, key, x, h, s, yl in sorted(objs, key=lambda o: -o[0]):
            if s <= 0.02:
                continue
            name, model = GIFTS[key]
            spr = gift_live(name, model, t, 320, offset=hash(key) % 7 * 0.31)
            # contact shadow
            sh = _shadow_spr()
            billboard(im, sh, (x, COUNTER_Y + 0.005, z + 0.02), h * 0.22 * s, cam, anchor=(0.5, 0.55),
                      alpha=0.55 * (1 - min(1, yl * 2)))
            pr = billboard(im, spr, (x, COUNTER_Y + yl - 0.02, z), h * s, cam)
            if pr:
                labels.append((key, pr[0], pr[1] - h * s * cam.k / cam.depth((x, COUNTER_Y, z))))
    if extra:
        extra(im, cam)
    if leva_back is not None:
        billboard(im, C.leva_back(), leva_back, 1.25, cam, anchor=(0.5, 1.0))
    if dark:
        im = Image.blend(im, Image.new('RGBA', (W, H), (8, 6, 8, 255)), dark)
    return im, labels


@functools.lru_cache(None)
def _shadow_spr():
    im = Image.new('RGBA', (400, 120), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([40, 20, 360, 100], fill=(20, 10, 6, 200))
    return im.filter(ImageFilter.GaussianBlur(16))


def fireflies(im, cam, t, t0, start, dur=0.9, n=1):
    """Pages turn into fireflies that fly into the jar (start = 3D point)."""
    jx, jz, jh = SLOTS['jar']
    end = (jx, COUNTER_Y + jh * 0.55, jz)
    out = im
    for k in range(n):
        u = ramp(t, t0 + 0.05 * k, t0 + dur + 0.05 * k)
        if u <= 0 or u >= 1:
            continue
        uu = fx.smooth(u)
        mid = ((start[0] + end[0]) / 2, max(start[1], end[1]) + 0.5, (start[2] + end[2]) / 2)
        p = [(1 - uu) ** 2 * a + 2 * uu * (1 - uu) * b + uu ** 2 * c for a, b, c in zip(start, mid, end)]
        pr = cam.project(p)
        if pr:
            s = cam.k / pr[2]
            out = add_light(out, pr[0], pr[1], int(max(12, 0.09 * s)), (255, 230, 130), 1.2)
            glow(out, pr[0], pr[1], int(max(6, 0.03 * s)), (255, 250, 220), 1.0)
    return out


def jar_flash(im, cam, t, t0):
    k = math.exp(-4 * (t - t0)) if t >= t0 else 0.0
    if k < 0.02:
        return im
    jx, jz, jh = SLOTS['jar']
    pr = cam.project((jx, COUNTER_Y + jh * 0.5, jz))
    if not pr:
        return im
    return add_light(im, pr[0], pr[1], int(0.5 * cam.k / pr[2]), (255, 220, 120), 0.9 * k)


def flying_page(im, cam, t, t0, text, sub, start, dur=0.75):
    """A calendar page tears off, flips up and dissolves into a firefly (fireflies() continues the flight)."""
    u = ramp(t, t0, t0 + dur)
    if u <= 0 or u >= 1:
        return im
    pg = ui.page_sprite(text, sub)
    p = (start[0] + 0.12 * u, start[1] + 0.55 * fx.ease_out(u), start[2] - 0.2 * u)
    pr = cam.project(p)
    if not pr:
        return im
    s = 0.34 * cam.k / pr[2] / pg.width * (1 - 0.6 * u)
    put(im, pg, pr[0], pr[1], a=1 - fx.ease_in(u), scale=s, rot=25 * math.sin(u * 4))
    return im


def label_at(im, labels, key, t, t0, name, model, dy=-40):
    a = ramp(t, t0, t0 + 0.25) * (1 - ramp(t, t0 + 2.2, t0 + 2.6))
    for k, x, y in labels:
        if k == key and a > 0:
            lb = ui.gift_label(name, model)
            put(im, lb, min(max(x, lb.width / 2 + 30), W - lb.width / 2 - 30), y + dy - 40 * (1 - a), a=a,
                scale=0.9 + 0.1 * pop(t, t0, 0.3))


# ------------------------------------------------------------------ shots
HOOK_SLOTS = {'jar': (0.36, 3.05, 0.4), 'cal': (-0.3, 2.95, 0.36)}


def shot_hook(t):
    u = t / SH['room']
    cam = Cam((-0.28 + 0.26 * u, -0.32, 0.45 + 0.4 * sm(u)), (0.04, -0.56, 2.7), fov=38)
    t_land = E['pepe_land']
    drop = 1 - fx.ease_in(ramp(t, 0.0, t_land))
    sq = fx.bump(t - t_land, f=3.2, decay=7) if t > t_land else 0.0

    def extra(im, cam):
        # the price tag swings in next to Pepe
        a = pop(t, t_land + 0.25, 0.5)
        pr = cam.project((0.2, COUNTER_Y + 0.36, 2.6))
        if pr and a > 0:
            tag = ui.price_tag(('Цена:', 'вечер', 'с бабушкой'))
            put(im, tag, pr[0] + 60, pr[1] + 40, a=min(1, a), scale=0.7 * a,
                rot=6 * math.sin((t - t_land) * 3) * math.exp(-1.2 * (t - t_land)))

    pepe = (2.62, 'pepe', 0.06, 0.42 * (1 + 0.1 * sq), 1.0, 0.42 * drop)
    im, labels = shop(t, cam, who=False, items=True, pepe=pepe, wall_blur=6, light=1.3, slots=HOOK_SLOTS)
    extra(im, cam)
    # Saturday page burning: rises from the calendar, embers
    pb = E['page_burn']
    if t >= pb - 0.35:
        u2 = ramp(t, pb - 0.35, pb + 0.8)
        pr = cam.project((-0.2, COUNTER_Y + 0.38 + 0.12 * u2, 2.85))
        if pr:
            pg = ui.page_sprite('СУББОТА', 'бабушка, пирог')
            s = 0.3 * cam.k / pr[2] / pg.width
            burn = _burn(pg, ramp(t, pb, pb + 0.75))
            put(im, burn, pr[0], pr[1], scale=s, rot=-8)
            im = add_light(im, pr[0], pr[1] + 30, 220, (255, 130, 50), 0.8 * math.sin(math.pi * ramp(t, pb, pb + 0.9)))
            _embers(im, pr[0], pr[1], t - pb, s * pg.width)
    im = add_light(im, W * 0.55, H * 0.42, 700, (255, 190, 110), 0.18)
    return im


def _burn(pg, k):
    """Burn the page from the bottom: an irregular edge eats it, the edge glows."""
    if k <= 0:
        return pg
    a = np.asarray(pg).astype(np.float32)
    h, w = a.shape[:2]
    xs = np.arange(w)
    edge = h * (1 - k * 1.15) + 18 * np.sin(xs / 17.0) + 10 * np.sin(xs / 7.3 + 2)
    yy = np.arange(h)[:, None]
    d = yy - edge[None, :]
    alpha = np.clip(1 - d / 4, 0, 1)
    char = np.clip(1 - np.abs(d + 10) / 16, 0, 1)
    a[..., :3] = a[..., :3] * (1 - char[..., None] * 0.8) + np.array([255, 120, 40]) * char[..., None] * 0.8
    a[..., 3] *= alpha
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def _embers(im, x, y, u, size):
    if u < 0:
        return
    rng = np.random.default_rng(11)
    d = ImageDraw.Draw(im)
    for k in range(26):
        t0 = rng.uniform(0, 0.6)
        v = u - t0
        if v < 0 or v > 1.2:
            continue
        ex = x + rng.uniform(-0.5, 0.5) * size + 40 * math.sin(v * 5 + k)
        ey = y + size * 0.3 - v * rng.uniform(180, 380)
        r = 3 + 3 * (1 - v)
        col = (255, int(150 + 80 * (1 - v)), 60, int(255 * (1 - v / 1.2)))
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=col)


@functools.lru_cache(None)
def room_bg_layer():
    return S.room_night()


def room(t, scale=1.0, dx=0.0, glow_=1.0, warm=0.0):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    bg = room_bg_layer()
    k = 0.86 * scale
    w, h = int(bg.width * k), int(bg.height * k)
    put(im, bg.resize((w, h), Image.BILINEAR), W / 2 + dx * 0.5, H / 2 - 60)
    if warm:
        im = add_light(im, W * 0.5, H * 0.45, 900, (255, 170, 90), 0.35 * warm)
    return im


def shot_room(t):
    """invite + bot: Лёва on his bed at night; Telegram cards float in 3D in front of him."""
    u = ramp(t, SH['room'], SH['shop'])
    z = 1 + 0.06 * sm(u)
    warm = ramp(t, E['bot_text'], SH['shop'] - 0.2)
    im = room(t, z, dx=-30 * u, warm=warm)
    bed = S.bed_front()
    # Лёва
    look = (0.1, 0.5) if t < E['cake_msg'] + 0.3 else (0.0, -0.35)
    smile = 0.55 if E['cake_text'] < t < SH['bot'] else (0.2 if t < E['bot_msg'] else 0.0)
    brow = 0.6 * ramp(t, E['bot_msg'], E['bot_msg'] + 0.3)
    sp = leva_sprite(t, look=look, smile=smile, brow=brow, glow_=1.0 - 0.5 * warm,
                     bob=2 * math.sin(t * 1.6), tilt=2 * math.sin(t * 0.7))
    put(im, sp, W / 2 + 10 - 20 * u, 1530 + 10 * u, scale=0.98 * z)
    put(im, bed, W / 2, 1830, scale=1.0)
    # cards (3D tilt): grandma, then the bot on top
    cam = Cam((0, 0, 0), (0, 0, 1), fov=40)
    a1 = ramp(t, E['cake_msg'] - 0.25, E['cake_msg'] + 0.15)
    if a1 > 0:
        c1 = ui.chat_card(t, 'grandma', [('gift', ('Homemade Cake', None), ramp(t, E['cake_msg'], E['cake_msg'] + 0.35),
                                           'для любимого внука'),
                                          ('text', 'Приезжай в субботу, испеку пирог ❤', ramp(t, E['cake_text'] - 0.15,
                                                                                               E['cake_text'] + 0.2))])
        push = ramp(t, E['bot_msg'] - 0.3, E['bot_msg'] + 0.3)
        _card3d(im, cam, c1, (-0.02 - 0.08 * push, 0.5 + 0.18 * push, 3.0 + 1.0 * push), 1.0,
                yaw=lerp(-0.45, 0.12, sm(a1)) - 0.1 * push, pitch=0.08, alpha=sm(a1) * (1 - 0.55 * push))
    a2 = ramp(t, E['bot_msg'] - 0.2, E['bot_msg'] + 0.2)
    if a2 > 0:
        typed = ramp(t, E['bot_text'], E['bot_text'] + 2.6)
        gl = max(0.0, 1 - (t - E['bot_msg']) / 0.5) if t > E['bot_msg'] else 1.0
        c2 = ui.chat_card(t, 'bot', [('text', 'Ломбард времени. Покупаем часы вашей жизни. Платим подарками.', 1.0)],
                          typed=typed, glitch=gl + 0.25 * max(0.0, math.sin(t * 13)) * (1 - typed))
        zoom = ramp(t, SH['shop'] - 0.55, SH['shop'])
        zpos = lerp(3.0, 0.55, fx.ease_in(zoom))
        _card3d(im, cam, c2, (0.03, 0.45 * (1 - zoom), zpos), 1.0, yaw=lerp(0.4, -0.06, sm(a2)) * (1 - zoom),
                pitch=-0.05, alpha=sm(a2))
    return im


def _card3d(im, cam, card, center, width, yaw=0.0, pitch=0.0, alpha=1.0, shadow=True):
    w = width
    h = width * card.height / card.width
    cx, cy, cz = center
    cyw, syw = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def P(x, y):
        # rotate (x, y, 0) by pitch (around x) then yaw (around y)
        yy, zz = y * cp, y * sp
        xx, z2 = x * cyw + zz * syw, -x * syw + zz * cyw
        return (cx + xx, cy + yy, cz + z2)

    if shadow:
        quad(im, _card_shadow(card.width, card.height), [P(-w / 2 - 0.08, h / 2 + 0.02), P(w / 2 + 0.08, h / 2 + 0.02),
                                                     P(w / 2 + 0.08, -h / 2 - 0.14), P(-w / 2 - 0.08, -h / 2 - 0.14)],
             cam, alpha=0.6 * alpha)
    quad(im, card, [P(-w / 2, h / 2), P(w / 2, h / 2), P(w / 2, -h / 2), P(-w / 2, -h / 2)], cam, alpha=alpha)


@functools.lru_cache(maxsize=16)
def _card_shadow(w, h):
    im = Image.new('RGBA', (w + 160, h + 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([80, 80, w + 80, h + 80], 50, fill=(0, 0, 0, 170))
    return im.filter(ImageFilter.GaussianBlur(40))


def cam_cheap(t):
    u = ramp(t, SH['shop'], SH['rule'])
    return Cam((-0.2 + 0.3 * sm(u), 0.3, -0.5 + 0.25 * sm(u)), (0.02, -0.4, 3.6), fov=30)


def deals_fx(im, cam, t):
    for key, t0, text, sub in (('tear1', E['tear1'], '1 ЧАС', 'очередь'), ('tear2', E['tear2'], 'ВОСКРЕСЕНЬЕ', 'проспал'),
                               ('tear3', E['tear3'], 'ЛЕТО', 'с друзьями'), ('tear4', E['tear4'], 'ПОЕЗДКА', 'пропустил')):
        x, z, h = SLOTS['cal']
        start = (x, COUNTER_Y + h * 0.8, z)
        flying_page(im, cam, t, t0, text, sub, start)
        im = fireflies(im, cam, t, t0 + 0.55, (x + 0.1, COUNTER_Y + h + 0.45, z - 0.15), dur=0.7)
        im = jar_flash(im, cam, t, t0 + 1.25)
    return im


def old_pose_at(t):
    p = dict(look=(0, 0.2), smile=0.45)
    for t0 in (E['cookie'], E['globe'], E['player'], E['cap']):
        if t0 <= t < t0 + 0.6:
            p['bob'] = -6 * math.sin(math.pi * (t - t0) / 0.6)            # little nod per deal
    return p


def shot_cheap(t):
    cam = cam_cheap(t)
    cal = 'sun' if E['tear2'] - 0.25 <= t < SH['rule'] + 0.5 else None
    im, labels = shop(t, cam, old_pose=old_pose_at(t), cal_model=cal, leva_back=(-0.5, -1.0, 1.5))
    im = deals_fx(im, cam, t)
    label_at(im, labels, 'cookie', t, E['cookie'], 'Ginger Cookie', 'Coffee Break')
    label_at(im, labels, 'globe', t, E['globe'], 'Snow Globe', 'Winter')
    if E['tear2'] - 0.25 <= t:
        label_at(im, labels, 'sun', t, E['tear2'] - 0.2, 'Desk Calendar', 'Sunday', dy=-30)
    return im


def shot_rule(t):
    u = ramp(t, SH['rule'], SH['rich'])
    cam = Cam((0.1 - 0.15 * sm(u), 0.25, -0.2 + 0.8 * sm(u)), (0.0, -0.05, 3.7), fov=30)
    pose = dict(look=(0, 0), smile=0.5, brow=0.5 * ramp(t, E['rule_a'] - 0.3, E['rule_a']),
                glint=ramp(t, ON[KEY['rule']] + 0.6, ON[KEY['rule']] + 1.3))
    im, _ = shop(t, cam, old_pose=pose, cal_model='sun' if t < SH['rule'] + 0.5 else None)
    # the rule, written in the air in front of the watchmaker (tilted 3D plates)
    c0 = Cam((0, 0, 0), (0, 0, 1), fov=40)
    for t0, txt, y, col in ((E['rule_a'], 'ЧЕМ ДОРОЖЕ ЧАС\nДЛЯ ТЕБЯ —', 0.62, (255, 255, 255)),
                            (E['rule_b'], 'ТЕМ ДОРОЖЕ\nПОДАРОК', 0.18, (255, 206, 96))):
        a = pop(t, t0 - 0.1, 0.45)
        if a > 0:
            spr = text_spr(txt, 92, col, stroke=9)
            _card3d(im, c0, spr, (0.0, y, 3.0), spr.width * 3.0 / c0.k, yaw=0.25 * (1 - min(1, a)) +
                    0.05 * math.sin(t * 1.1), pitch=0.05, alpha=min(1.0, a), shadow=False)
    return im


def shot_rich(t):
    u = ramp(t, SH['rich'], SH['safe'])
    jx, jz, _ = SLOTS['jar']
    ang = lerp(-0.42, 0.3, sm(u))
    c = (0.0, -0.45, 3.0)
    rad = 3.4
    cam = Cam((c[0] + rad * math.sin(ang), 0.3, c[2] - rad * math.cos(ang)), (0.0, -0.4, 3.2), fov=30)
    gray = 0.85 * sm(ramp(t, E['tear3'], SH['safe'] - 0.2))
    im, labels = shop(t, cam, old_pose=dict(look=(0.3 * math.sin(ang), 0.2), smile=0.5), gray=gray,
                      leva_back=None)
    im = deals_fx(im, cam, t)
    label_at(im, labels, 'player', t, E['player'], 'Record Player', 'Sunset Beach')
    label_at(im, labels, 'cap', t, E['cap'], "Durov's Cap", 'Seabreeze')
    # friends' chat: unanswered, greying
    a = ramp(t, E['tear3'] + 0.2, E['tear3'] + 0.6) * (1 - ramp(t, SH['safe'] - 0.5, SH['safe'] - 0.1))
    if a > 0:
        card = _friends_card(t)
        put(im, desat(card, gray), 330, 600, a=a, scale=0.8, rot=4)
    return im


def _friends_card(t):
    msgs = [('text', 'Лёва, ты с нами на море?', 1.0), ('text', 'Лёва??', ramp(t, E['tear4'], E['tear4'] + 0.3)),
            ('text', 'ну ладно…', ramp(t, E['cap'] + 0.3, E['cap'] + 0.6))]
    c = ui.chat_card(t, 'grandma', msgs, w=760)
    # re-title: draw over the header
    d = ImageDraw.Draw(c)
    d.rectangle([150, 20, 740, 120], fill=ui.HEAD + (255,))
    d.text((154, 50), 'Друзья 🏖'.replace('🏖', ''), font=fx.font('Bold', 40), fill=ui.TXT + (255,), anchor='lm')
    d.text((154, 96), '3 непрочитанных', font=fx.font('Regular', 28), fill=ui.DIM + (255,), anchor='lm')
    av = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
    ImageDraw.Draw(av).ellipse([0, 0, 95, 95], fill=(90, 150, 220, 255))
    ImageDraw.Draw(av).text((48, 48), 'Д', font=fx.font('Heavy', 46), fill=(255, 255, 255, 255), anchor='mm')
    c.alpha_composite(av, (34, 22))
    return c


def shot_safe(t):
    u = ramp(t, SH['safe'], AD_STOP)
    sx, sy, sz = SAFE
    tgt = lerp3((0.0, -0.4, 3.6), (sx, sy, sz), sm(u))
    cam = Cam((lerp(0.1, -0.6, sm(u)), lerp(0.3, 0.6, sm(u)), lerp(-0.4, 1.8, sm(u))), tgt, fov=lerp(30, 34, sm(u)))
    op = ramp(t, E['safe_open'], E['safe_open'] + 0.9)
    pose = dict(look=(-0.8, -0.2), smile=0.35, tilt=8 * sm(ramp(t, SH['safe'], SH['safe'] + 0.6)))
    im, _ = shop(t, cam, old_pose=pose, gray=0.85 * (1 - 0.7 * op), safe_open=op)
    # golden rays from the open safe
    p = cam.project(SAFE)
    if p and op > 0:
        im = _rays(im, p[0], p[1], t, op)
    return im


def _rays(im, x, y, t, k):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for j in range(14):
        a = j / 14 * 2 * math.pi + t * 0.25
        w = 0.07 + 0.04 * math.sin(j * 2.3)
        r = 1500
        d.polygon([(x, y), (x + r * math.cos(a - w), y + r * math.sin(a - w)),
                   (x + r * math.cos(a + w), y + r * math.sin(a + w))], fill=(255, 210, 120, int(46 * k)))
    lay = lay.filter(ImageFilter.GaussianBlur(14))
    im.alpha_composite(lay)
    return add_light(im, x, y, 360, (255, 220, 140), 0.9 * k)


def shot_lot(t):
    u = ramp(t, SH['lot'], SH['sign'])
    ang = lerp(-0.55, 0.35, sm(u))
    c = (0.0, -0.5, 2.62)
    rad = 1.7
    cam = Cam((c[0] + rad * math.sin(ang), -0.22, c[2] - rad * math.cos(ang)), (0.0, -0.5, 2.62), fov=34)
    rise = fx.ease_out(ramp(t, SH['lot'] - 0.1, SH['lot'] + 0.5))

    def cushion(im, cam):
        pass

    pepe = (2.62, 'pepe', 0.0, 0.42, 1.0, 0.07 + 0.03 * math.sin(t * 2))
    im, labels = shop(t, cam, old_pose=dict(look=(0, 0.5), smile=0.4), pepe=pepe, items=True, wall_blur=4,
                      safe_open=1.0, gray=0.35)
    # velvet cushion under Pepe is drawn as a billboard below him
    p = cam.project((0.0, COUNTER_Y + 0.07, 2.62))
    if p:
        im = add_light(im, p[0], p[1] - 160, 520, (255, 210, 120), 0.35 * rise)
    label_at(im, labels, 'pepe', t, SH['lot'] + 0.2, 'Plush Pepe', 'Midas Pepe', dy=-20)
    # price tag + Saturday calendar
    a = pop(t, E['price_tag'], 0.45)
    if a > 0:
        tag = ui.price_tag(('Цена:', '1 суббота'))
        put(im, tag, 770, 1180, a=min(1, a), scale=0.85 * a, rot=6 * math.sin((t - E['price_tag']) * 3) *
            math.exp(-(t - E['price_tag'])))
    a2 = pop(t, E['saturday'], 0.45)
    if a2 > 0:
        sat = gift_live('Desk Calendar', 'Saturday', t, 300)
        put(im, sat, 790, 1460, a=min(1, a2), scale=a2)
        lb = ui.gift_label('Desk Calendar', 'Saturday')
        put(im, lb, 790, 1640, a=ramp(t, E['saturday'] + 0.1, E['saturday'] + 0.35), scale=0.8)
    return im


@functools.lru_cache(None)
def bokeh_bg():
    im = Image.new('RGBA', (W, H), (40, 24, 18, 255))
    g = np.linspace(0, 1, H)[:, None]
    a = np.zeros((H, W, 4), np.float32)
    a[..., 0] = 70 - 34 * g
    a[..., 1] = 42 - 22 * g
    a[..., 2] = 32 - 16 * g
    a[..., 3] = 255
    im = Image.fromarray(a.astype(np.uint8), 'RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(3)
    for _ in range(26):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H * 0.75), rng.uniform(30, 110)
        c = (255, int(rng.uniform(150, 210)), int(rng.uniform(80, 130)), int(rng.uniform(40, 110)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
    return im


def leva_close(t, look, smile, brow=0.0, sad=0.0, open_=0.0, scale=1.25, y=1330, tilt=0.0, shake=0.0):
    im = bokeh_bg().copy()
    sp = leva_sprite(t, look=look, smile=smile, brow=brow, sad=sad, open_=open_, glow_=0.0, tilt=tilt)
    put(im, sp, W / 2 + shake, y, scale=scale)
    return add_light(im, W * 0.75, H * 0.3, 700, (255, 180, 100), 0.25)


SIGN_INSERT = E['signs'] - 0.55


def shot_sign(t):
    if t < SIGN_INSERT:
        # careless shrug: eyes roll up, half-smile, head tilt
        sh = ramp(t, E['shrug'] - 0.2, E['shrug'] + 0.3)
        im = leva_close(t, look=(0.6 * sh - 0.2, -0.6 * sh + 0.3), smile=0.2 + 0.4 * sh, brow=0.5 * sh,
                        tilt=-7 * sh, open_=0.0)
        # grandma's message, small, on his phone
        c = ui.chat_card(t, 'grandma', [('text', 'Приезжай в субботу, испеку пирог ❤', 1.0)], w=760)
        put(im, c, 300, 520, a=1 - ramp(t, E['shrug'], E['shrug'] + 0.4), scale=0.6, rot=-5)
        return im
    # insert: a contract on the counter, seen from above; the signature draws itself
    u = ramp(t, SIGN_INSERT, SH['never'])
    cam = Cam((0.05, 0.75, 1.55 + 0.15 * u), (0.0, COUNTER_Y, 2.72), fov=38)

    def no_items(im, cam):
        pass

    im, _ = shop(t, cam, who=False, items=False, wall_blur=6, gray=0.3)
    paper = _contract(ramp(t, E['signs'], E['signs'] + 0.55))
    quad(im, paper, [(-0.36, COUNTER_Y + 0.002, 2.95), (0.36, COUNTER_Y + 0.002, 2.95), (0.36, COUNTER_Y + 0.002, 2.42),
                     (-0.36, COUNTER_Y + 0.002, 2.42)], cam)
    flying_page(im, cam, t, E['signs'] + 0.35, 'СУББОТА', 'бабушка', (0.0, COUNTER_Y + 0.05, 2.7), dur=0.6)
    return im


def _contract(k):
    im = Image.new('RGBA', (720, 530), (248, 242, 226, 255))
    d = ImageDraw.Draw(im)
    d.text((360, 60), 'ДОГОВОР', font=fx.font('Heavy', 52), fill=(70, 50, 44, 255), anchor='mm')
    d.text((60, 140), 'Продавец: Лёва', font=fx.font('Medium', 34), fill=(90, 70, 60, 255))
    d.text((60, 196), 'Продаёт: 1 субботу (бабушка, пирог)', font=fx.font('Medium', 30), fill=(90, 70, 60, 255))
    d.text((60, 246), 'Получает: Plush Pepe', font=fx.font('Medium', 30), fill=(90, 70, 60, 255))
    d.text((60, 296), 'Возврату не подлежит', font=fx.font('Bold', 30), fill=(170, 60, 60, 255))
    d.line([(60, 440), (660, 440)], fill=(160, 140, 120, 255), width=3)
    if k > 0:
        pts = [(100 + 440 * s - 40 * math.sin(2 * math.pi * 4 * s), 400 - 50 * abs(math.sin(2 * math.pi * 2 * s))
                - 30 * math.cos(2 * math.pi * 4 * s) + 20 * s) for s in np.linspace(0, k, max(2, int(200 * k)))]
        d.line(pts, fill=(30, 50, 120, 255), width=7, joint='curve')
    return im


def shot_never(t):
    u = ramp(t, SH['never'], SH['return'])
    bg = S.kitchen()
    z = 0.82 + 0.06 * sm(u)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    put(im, bg.resize((int(bg.width * z), int(bg.height * z)), Image.BILINEAR), W / 2 - 40 * u, H / 2)
    # wall calendar: Saturday, then the pages run forward
    run = ramp(t, SH['never'] + 1.1, SH['return'] - 0.3)
    day = 7 + int(run * 9)
    wd = ['суббота', 'воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница'][(day - 7) % 7]
    cal = S.wall_calendar(day, wd)
    put(im, cal, 860 - 34 * u, 620, scale=z)
    if run > 0:
        ph = (run * 9) % 1.0
        sheet = S.wall_calendar(day + 1 if ph > 0.5 else day, wd)
        put(im, sheet, 860 - 34 * u + 200 * ph, 620 - 260 * ph, a=1 - ph, scale=z * (1 - 0.3 * ph), rot=40 * ph)
    put(im, S.pie_plate(), W / 2 - 60 - 30 * u, 1500, scale=z * 1.1)
    # dusk turns to night, colour drains
    dark = 0.15 + 0.45 * sm(u)
    im = desat(im, 0.3 + 0.6 * sm(u))
    im = Image.blend(im, Image.new('RGBA', (W, H), (20, 24, 44, 255)), dark)
    return im


def shot_return(t):
    if t < E['please'] - 0.15:
        u = ramp(t, SH['return'], E['please'])
        cam = Cam((-0.1 + 0.15 * u, 0.3, -0.3 + 0.2 * u), (0.0, -0.4, 3.6), fov=30)
        shake = fx.bump(t - BRING_BACK - 0.3, f=7, decay=8) * 0.02
        cam = Cam(cam.e + np.array([shake, shake * 0.5, 0]), (0.0, -0.4, 3.6), fov=30)
        pose = dict(look=(0, 0.3), smile=0.0, brow=0.3)
        pepe = None
        if t > BRING_BACK + 0.7:
            v = t - BRING_BACK - 0.7
            y = max(0.0, 0.9 * (1 - v / 0.3)) if v < 0.3 else 0.0
            pepe = (2.7, 'pepe', 0.1, 0.4, 1.0, y)
        im, _ = shop(t, cam, old_pose=pose, pepe=pepe, leva_back=(-0.36, -1.0, 1.5), gray=0.5)
        return im
    k = ramp(t, E['please'] - 0.15, E['please'] + 0.2)
    return leva_close(t, look=(0, -0.1), smile=-0.5, brow=0.2, sad=1.0, open_=talk(t, ['return']) if
                      t > E['please'] else 0.0, scale=1.3 + 0.04 * k, y=1330, shake=3 * math.sin(t * 40) * k)


def shot_refuse(t):
    if t < E['profile'] - 0.1:
        u = ramp(t, SH['refuse'], E['profile'])
        cam = Cam((0.05, 0.25, 0.6 + 0.4 * u), (0.0, 0.0, 3.7), fov=30)
        shake = math.sin((t - E['no']) * 10) * 7 * (1 - ramp(t, E['no'], E['no'] + 1.1)) if t > E['no'] else 0.0
        pose = dict(look=(0, 0), smile=0.25, sad=0.4, tilt=shake, open_=talk(t, ['refuse']))
        im, _ = shop(t, cam, old_pose=pose, gray=0.45)
        return im
    # Лёва's gift profile: every gift «от: Ломбард времени», one «от: Бабушка»
    u = ramp(t, E['profile'] - 0.1, SH['you'])
    im = bokeh_bg().copy()
    im = Image.blend(im, Image.new('RGBA', (W, H), (16, 14, 20, 255)), 0.55)
    card = ui.profile_card(t, focus=ramp(t, E['grandma_gift'] - 0.1, E['grandma_gift'] + 0.5))
    cam = Cam((0, 0, 0), (0, 0, 1), fov=40)
    _card3d(im, cam, card, (0.0, 0.12 + 0.03 * u, 3.2 - 0.35 * sm(u)), 1.12, yaw=lerp(0.35, 0.05, sm(ramp(t, E['profile'],
                                                                                                    E['profile'] + 0.8))),
            pitch=0.12 * (1 - u), alpha=ramp(t, E['profile'] - 0.1, E['profile'] + 0.2))
    return im


def shot_you(t):
    u = ramp(t, SH['you'], SH['vote'])
    cam = Cam((0.0, 0.25, 0.7 + 0.3 * sm(u)), (0.0, -0.4, 3.7), fov=30)
    sl = fx.smooth(ramp(t, E['slide'], E['slide'] + 1.2))
    pz = lerp(3.1, 2.7, sl)
    beat = max(0.0, math.sin((t - E['waits']) * 9)) * math.exp(-2.2 * (t - E['waits'])) if t > E['waits'] else 0
    pepe = (pz, 'pepe', lerp(0.22, 0.0, sl), 0.4 * (1 + 0.06 * beat), 1.0, 0.03 * sl)
    pose = dict(look=(0, 0), smile=0.55, brow=0.25, open_=talk(t, ['you']), glint=ramp(t, E['turn'], E['turn'] + 0.9))
    im, labels = shop(t, cam, old_pose=pose, pepe=pepe, items=True, gray=0.25, wall_blur=4, gifts_on=False)
    return im


@functools.lru_cache(None)
def vote_bg():
    cam = Cam((0.0, 0.25, 0.4), (0.0, -0.3, 3.7), fov=30)
    im, _ = shop(SH['vote'], cam, old_pose=dict(look=(0, 0), smile=0.55), gray=0.3, gifts_on=False)
    im = im.filter(ImageFilter.GaussianBlur(18))
    return Image.blend(im, Image.new('RGBA', (W, H), (14, 10, 12, 255)), 0.45)


def _vote_card(t, side):
    w, h = 470, 700
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (90, 160, 80) if side == 'l' else (230, 150, 70)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 44, fill=(30, 26, 32, 240), outline=col + (255,), width=6)
    if side == 'l':
        g = gift_live('Plush Pepe', 'Midas Pepe', t, 360)
        txt, em = 'БЕРУ\nПЕПЕ', '🐸'
    else:
        g = gift_live('Desk Calendar', 'Saturday', t, 360)
        txt, em = 'ОСТАВЛЮ\nВЕЧЕР', '⏳'
    im.alpha_composite(g, ((w - 360) // 2, 40))
    e = emoji(em, 96)
    im.alpha_composite(e, ((w - 96) // 2, 410))
    tx = text_spr(txt, 54, (255, 255, 255), stroke=0, shadow=False)
    im.alpha_composite(tx, ((w - tx.width) // 2, 500))
    return im


def shot_vote(t):
    im = vote_bg().copy()
    a = pop(t, SH['vote'] - 0.05, 0.4)
    put(im, text_spr('А ТЫ?', 130, (255, 206, 96), stroke=10), W / 2, 300, a=min(1, a), scale=0.8 + 0.2 * a)
    put(im, text_spr('ГОЛОСУЙ В КОММЕНТАРИЯХ', 54, (255, 255, 255), stroke=7), W / 2, 440,
        a=ramp(t, SH['vote'] + 0.2, SH['vote'] + 0.5))
    cam = Cam((0, 0, 0), (0, 0, 1), fov=40)
    for side, t0, x, yaw in (('l', E['card_l'] - 0.25, -0.5, 0.22), ('r', E['card_r'] - 0.25, 0.5, -0.22)):
        k = pop(t, t0, 0.5)
        if k <= 0:
            continue
        card = _vote_card(t, side)
        wob = 0.04 * math.sin(t * 1.7 + (0 if side == 'l' else 1.5))
        _card3d(im, cam, card, (x * 0.62, -0.16 - 0.4 * (1 - min(1, k)), 3.0), 0.56 * min(1.1, k), yaw=yaw + wob,
                pitch=0.06, alpha=min(1, k))
    vs = pop(t, E['card_r'] + 0.1, 0.4)
    put(im, text_spr('ИЛИ', 56, (255, 255, 255), stroke=7), W / 2, 1150, a=min(1, vs))
    return im


SHOTS = [
    (0.0, shot_hook), (SH['room'], shot_room), (SH['shop'], shot_cheap), (SH['rule'], shot_rule),
    (SH['rich'], shot_rich), (SH['safe'], shot_safe), (SH['lot'], shot_lot), (SH['sign'], shot_sign),
    (SH['never'], shot_never), (SH['return'], shot_return), (SH['refuse'], shot_refuse), (SH['you'], shot_you),
    (SH['vote'], shot_vote),
]
CUTS = [s for s, _ in SHOTS[1:]] + [SIGN_INSERT, E['please'] - 0.15, E['profile'] - 0.1]


# ------------------------------------------------------------------ subtitles
@functools.lru_cache(None)
def _timed_script(k):
    """Script words of line k with times interpolated from the ASR words by character position."""
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
    out = []
    for j, w in enumerate(spoken):
        a = float(np.interp(sf[j], af, at))
        b = float(np.interp(sf[j + 1], af, at))
        out.append((w, a, b))
    return out


@functools.lru_cache(None)
def _chunks(k):
    words = _timed_script(k)
    out, cur, n = [], [], 0
    for w in words:
        if cur and (n + len(w[0]) > 20 or cur[-1][0][-1] in '.:?!…'):
            out.append(tuple(cur))
            cur, n = [], 0
        cur.append(w)
        n += len(w[0]) + 1
    if cur:
        out.append(tuple(cur))
    return tuple(out)


from script import LINES  # noqa: E402
LINES_SPOKEN = [s for _, s, _, _ in LINES]


@functools.lru_cache(maxsize=256)
def _sub_spr(words, hi):
    f = fx.font('Heavy', 66)
    space = f.getlength(' ')
    ws = [f.getlength(w) for w in words]
    total = sum(ws) + space * (len(words) - 1)
    im = Image.new('RGBA', (int(total) + 60, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 30
    for k, w in enumerate(words):
        col = (255, 206, 96) if k == hi else (255, 255, 255)
        d.text((x, 60), w, font=f, fill=col + (255,), anchor='lm', stroke_width=8, stroke_fill=(16, 12, 14, 255))
        x += ws[k] + space
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel('A').filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.5)))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 6))
    out.alpha_composite(im)
    return out


SUB_Y = {'vote': 1720, 'you': 1640}


def subtitles(im, t):
    for k in range(len(ON)):
        if ON[k] - 0.05 <= t < END[k] + 0.25:
            for ch in _chunks(k):
                a, b = ch[0][1], ch[-1][2]
                if a - 0.05 <= t < b + 0.25 or (ch is _chunks(k)[-1] and t >= a):
                    hi = max([j for j, w in enumerate(ch) if w[1] <= t] or [0])
                    spr = _sub_spr(tuple(w[0] for w in ch), hi)
                    s = 1 + 0.06 * (1 - ramp(t, a - 0.05, a + 0.1))
                    y = SUB_Y.get(LINES[k][2], 1500)
                    put(im, spr, W / 2, y, a=ramp(t, a - 0.05, a + 0.05), scale=s)
                    return
            return


# ------------------------------------------------------------------ frame
def _whip(im, k):
    """Horizontal motion blur + shift for whip-pan transitions (k 0..1)."""
    if k <= 0.01:
        return im
    a = np.asarray(im.convert('RGB'), np.float32)
    n = int(2 + 18 * k)
    out = np.zeros_like(a)
    for j in range(n):
        out += np.roll(a, int((j - n / 2) * 9 * k), axis=1)
    out /= n
    return Image.fromarray(out.astype(np.uint8), 'RGB').convert('RGBA')


@functools.lru_cache(None)
def _vign():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((x - W / 2) / (W * 0.7)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.35 * np.clip(d - 0.45, 0, 1) ** 1.5)[..., None]


def render_at(t):
    t = min(max(t, 0.0), DUR - 1e-3)
    fn = [f for s, f in SHOTS if t >= s][-1]
    im = fn(t)
    # whip pan out of the hook / zoom flash into the shop
    if SH['room'] - 0.14 <= t < SH['room'] + 0.16:
        im = _whip(im, 1 - abs(t - SH['room']) / 0.16)
    for c in CUTS:
        if c <= t < c + 0.2:
            k = 1 + 0.035 * (1 - (t - c) / 0.2)
            w, h = W / k, H / k
            im = im.transform((W, H), Image.EXTENT, ((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2),
                              Image.BILINEAR)
            break
    if SH['shop'] - 0.12 <= t < SH['shop'] + 0.25:              # warm flash through the phone
        k = 1 - abs(t - SH['shop']) / (0.12 if t < SH['shop'] else 0.25)
        im = Image.blend(im, Image.new('RGBA', (W, H), (255, 226, 170, 255)), 0.8 * max(0, k))
    subtitles(im, t)
    out = np.asarray(im.convert('RGB'), np.float32)
    out *= _vign()
    out += np.random.default_rng(int(t * FPS)).normal(0, 2.4, (H // 3, W // 3, 1)).repeat(3, 0).repeat(3, 1)
    fade = ramp(t, DUR - 0.3, DUR)
    out *= 1 - 0.9 * fade
    return np.clip(out, 0, 255).astype(np.uint8)


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Сначала хайлайты и слово автора «собирай» (config.STYLE_READY)')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
