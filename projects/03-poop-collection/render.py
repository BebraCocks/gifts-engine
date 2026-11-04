"""03-poop-collection: «Музей кал-лекции». Tiled 3D corridor, live Lottie portraits, stamps, RubUp pause."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
sys.path.insert(0, str(HERE))
import functools
import math

import numpy as np
from PIL import Image, ImageDraw

import banner
import frames
import fx
from fx import smooth, ease_out, bump, spring
import gifts_api as G
import layout
import lottie
import config
import gallery as GL
from gallery import Cam, HALF, Z_END, EYE, W, H
from timeline import DUR
from events import HOOK_MOVE, TRANSITS, PULLBACK, AD_STOP, HOOK, HEROES_T, FINAL, LIGHT_ON

FPS = 60
BR = banner.Breaks([AD_STOP], cy=H / 2)
P = config.PAPER
GOLD = config.GOLD

D_HERO, D_END = 4.0, 4.4
HERO_Y, END_Y = 2.32, 2.34
PX_PER_M = 500


def anim(gift, model):
    return str(G.original_file(gift, 'json') if model is None else G.model_file(gift, model, 'json'))


class Portrait:
    def __init__(self, gift, model, wall, z, w, h, yc, backdrop, hero=None, stamp=None, stamp_rgb=None, swap=None):
        self.gift, self.model, self.wall, self.z = gift, model, wall, z
        self.w, self.h, self.yc = w, h, yc
        self.c0, self.c1 = backdrop
        self.hero, self.stamp, self.stamp_rgb = hero, stamp, stamp_rgb
        self.path = anim(gift, model)
        self.swap = anim(gift, swap) if swap else None
        self.phase = (sum((i + 1) * ord(c) for i, c in enumerate(gift + (model or ''))) % 997) / 997 * 3.0
        self.border, self.margin = 0.13, 0.12

    def corners(self):
        m = self.margin
        return GL.wall_quad(self.wall, 0.0 if self.wall == 'E' else self.z, self.yc, self.w + 2 * m, self.h + 2 * m)

    def centre(self):
        if self.wall == 'L':
            return np.array([-HALF, self.yc, self.z])
        if self.wall == 'R':
            return np.array([HALF, self.yc, self.z])
        return np.array([0.0, self.yc, Z_END])

    def lamp_pos(self):
        c = self.centre()
        top = self.yc + self.h / 2 + 0.25
        if self.wall == 'L':
            return (c[0] + 0.5, top, c[2])
        if self.wall == 'R':
            return (c[0] - 0.5, top, c[2])
        return (0.0, top, Z_END + 0.5)

    def _paste(self, can, path, t, size, alpha=1.0, scale=1.0):
        ch, cw = can.shape[:2]
        s = max(4, int(size * scale))
        lot = np.asarray(lottie.frame(path, t + self.phase, size=s), np.float32)
        x0, y0 = (cw - s) // 2, int((ch - s) * 0.42) + (size - s) // 2
        xa, ya = max(x0, 0), max(y0, 0)
        xb, yb = min(x0 + s, cw), min(y0 + s, ch)
        piece = lot[ya - y0:yb - y0, xa - x0:xb - x0]
        al = piece[..., 3:4] / 255 * alpha
        reg = can[ya:yb, xa:xb]
        reg[:] = reg * (1 - al) + piece[..., :3] * al

    def texture(self, t, ppm):
        w, h = int(self.w * ppm), int(self.h * ppm)
        b, m = int(self.border * ppm), int(self.margin * ppm)
        cw, ch = w - 2 * b, h - 2 * b
        can = GL.backdrop(cw, ch, self.c0, self.c1).copy()
        size = int(min(cw, ch) * 0.86)
        if self.swap is not None:
            ts = HEROES_T[self.hero]['swap']
            k = smooth((t - ts) / 0.3)
            pop = 1.0 + 0.12 * bump(t - ts - 0.15, f=3.0, decay=5.0)
            if k < 1:
                self._paste(can, self.path, t, size, 1 - k, 1 - 0.3 * k)
            if k > 0:
                self._paste(can, self.swap, t - ts, size, k, (0.7 + 0.3 * k) * pop)
        else:
            self._paste(can, self.path, t, size)
        if self.hero is not None and self.stamp:
            u = t - HEROES_T[self.hero]['stamp']
            if u > 0:
                fs = min(0.17 * ppm, 0.62 * cw / max(4, len(self.stamp)))
                st = GL.stamp_img(self.stamp, self.stamp_rgb, max(8, int(fs)))
                k = 1.0 + 0.9 * (1 - ease_out(u / 0.13))
                a = min(1.0, u / 0.08)
                sw, sh = int(st.width * k), int(st.height * k)
                s2 = np.asarray(st.resize((max(2, sw), max(2, sh)), Image.BILINEAR), np.float32)
                cx, cy = int(cw * 0.55), int(ch * 0.83)
                xa, ya = cx - sw // 2, cy - sh // 2
                xb, yb, xe, ye = max(xa, 0), max(ya, 0), min(xa + sw, cw), min(ya + sh, ch)
                if xe > xb and ye > yb:
                    piece = s2[yb - ya:ye - ya, xb - xa:xe - xa]
                    a2 = piece[..., 3:4] / 255 * a
                    reg2 = can[yb:ye, xb:xe]
                    reg2[:] = reg2 * (1 - a2) + piece[..., :3] * a2
        art = GL.frame_art(w, h, b, m).copy()
        hole = art[m + b:m + b + ch, m + b:m + b + cw]
        hole[..., :3] = can
        hole[..., 3] = 255
        return art

    def draw(self, canvas, cam, t, lamps):
        corners = self.corners()
        pts, z = cam.project(corners)
        if (z < 0.25).any():
            return None
        if pts[:, 0].max() < 0 or pts[:, 0].min() > W or pts[:, 1].max() < 0 or pts[:, 1].min() > H:
            return None
        hpx = float(np.linalg.norm(pts[0] - pts[3]))
        ppm = PX_PER_M if hpx > 520 else (220 if hpx > 200 else 90)
        art = self.texture(t, ppm)
        art[..., :3] *= min(1.2, GL.light_at(self.centre(), t, lamps))
        tex = Image.fromarray(np.clip(art, 0, 255).astype(np.uint8), 'RGBA')
        return GL.draw_quad(canvas, cam, corners, tex)


HEROES = []
for k, hd in enumerate(config.HEROES):
    big = hd['wall'] == 'E'
    HEROES.append(Portrait(hd['gift'], hd['model'], hd['wall'], hd['z'], 1.9 if big else 1.7, 2.24 if big else 2.0,
                           END_Y if big else HERO_Y, hd['backdrop'], hero=k, stamp=hd['stamp'],
                           stamp_rgb=hd['stamp_rgb'], swap=hd.get('swap')))
_BACK = [('#d08656', '#602901'), ('#e7a75a', '#ad0e00'), ('#97b07c', '#28471b'), ('#b17da5', '#652852')]
CORR = [Portrait('Happy Brownie', m, 'L' if k % 2 == 0 else 'R', -8.0 - 5 * k, 1.5, 1.8, 2.35, _BACK[k % 4])
        for k, m in enumerate(config.CORRIDOR)]
ALL = CORR + HEROES


# ------------------------------------------------------------------ camera
def focus(k, d):
    p = HEROES[k]
    if p.wall == 'L':
        return np.array([-HALF + d, EYE, p.z]), math.pi / 2
    if p.wall == 'R':
        return np.array([HALF - d, EYE, p.z]), -math.pi / 2
    return np.array([0.0, EYE, Z_END + d]), 0.0


def hold_pose(k, t):
    h = HEROES_T[k]
    u = smooth((t - h['arrive']) / max(0.1, h['leave'] - h['arrive']))
    d0 = D_END if HEROES[k].wall == 'E' else D_HERO
    pos, yaw = focus(k, d0 - 0.25 * u)
    return pos, yaw + 0.012 * math.sin(t * 0.9 + k)


def camera(t):
    b = HOOK_MOVE[1]
    if t < b:
        u = max(0.0, t) / b
        p1, y1 = hold_pose(0, b)
        z0 = 4.0
        zz = z0 + (p1[2] - z0) * (1 - (1 - u) ** 2.3)
        turn = smooth((u - 0.66) / 0.34)
        return np.array([p1[0] * turn, EYE, zz]), y1 * turn, 0.04 * (1 - smooth(u / 0.8))
    for k, (ta, tb) in enumerate(TRANSITS):
        if t < ta:
            pos, yaw = hold_pose(k, t)
            return pos, yaw, 0.0
        if t < tb:
            s = smooth((t - ta) / (tb - ta))
            pa, ya = hold_pose(k, ta)
            pb, yb = hold_pose(k + 1, tb)
            pos = pa + (pb - pa) * s
            pos[1] = EYE + 0.15 * math.sin(math.pi * s)
            return pos, ya + (yb - ya) * s, 0.0
    if t < PULLBACK[0]:
        pos, yaw = hold_pose(4, t)
        return pos, yaw, 0.0
    u = t - PULLBACK[0]
    s = 0.85 * smooth(u / 3.2) + 0.15 * min(1.0, u / (PULLBACK[1] - PULLBACK[0]))
    pa, ya = hold_pose(4, PULLBACK[0])
    return pa + np.array([0.0, 0.25 * s, 7.5 * s]), ya, -0.02 * s


def shake(t):
    s = sum(14 * bump(t - h['stamp'], f=7.0, decay=9.0) for h in HEROES_T)
    return (0.4 * s, s)


def lamps(t):
    out = []
    for k, p in enumerate(HEROES):
        on = smooth((t - LIGHT_ON[k]) / 0.12)
        if on > 0:
            out.append((p.lamp_pos(), 2.0 * on * (1.2 if k == 4 else 1.0), (1.0, 0.9, 0.72)))
    return out


# ------------------------------------------------------------------ text
def wrap(s, size, weight, maxw):
    f = fx.font(weight, size)
    lines, cur = [], ''
    for w_ in s.split():
        nxt = (cur + ' ' + w_).strip()
        if f.getlength(nxt) <= maxw or not cur:
            cur = nxt
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return tuple(lines)


@functools.lru_cache(None)
def card(text, size, weight, rgb, panel=True, edge=None, maxw=860, lh=1.28, pad=(40, 30), fill=(18, 24, 24, 215)):
    lines = wrap(text, size, weight, maxw)
    widths = [layout.ink(s, size, weight) for s in lines]
    inner_w = max(r - l for l, t_, r, b in widths)
    step = size * lh
    cap = -layout.cap_top(size, weight)
    band_h = cap + step * (len(lines) - 1)
    Wc = int(inner_w + 2 * pad[0])
    Hc = int(band_h + 2 * pad[1] + size * 0.28)
    S = 2
    im = Image.new('RGBA', (Wc * S, Hc * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if panel:
        d.rounded_rectangle([0, 0, Wc * S - 1, Hc * S - 1], 26 * S, fill=fill,
                            outline=(edge or GOLD) + (160,), width=2 * S)
    top = (Hc - band_h) / 2
    inks = []
    fS = fx.font(weight, size * S)
    for j, s in enumerate(lines):
        base = top + cap + j * step
        x, _ = layout.centered(s, size, weight, cx=Wc / 2, cy=0)
        d.text((x * S, base * S), s, font=fS, fill=rgb + (255,), anchor='ls')
        inks.append(layout.box_of(s, size, weight, x, base))
    return im.resize((Wc, Hc), Image.LANCZOS), tuple(inks), (top, top + band_h)


def put(c, spr, cx, cy, alpha, name=None, dy=0.0, scale=1.0):
    im, inks, band = spr
    if alpha <= 0.01:
        return
    fx.over(c, fx.warp(im, cx, cy + dy, scale), alpha)
    if name and scale == 1.0 and abs(dy) < 0.5:
        x0, y0 = cx - im.width / 2, cy - im.height / 2
        layout.record(name, (x0, y0, x0 + im.width, y0 + im.height),
                      [(a + x0, b + y0, r + x0, q + y0) for a, b, r, q in inks],
                      band=(band[0] + y0, band[1] + y0), alpha=alpha)


def env_in_out(t, t_in, t_out, din=0.3, dout=0.3):
    if t < t_in or t > t_out + dout:
        return 0.0, 0.0
    a = smooth((t - t_in) / din) * (1 - smooth((t - t_out) / dout))
    dy = 34 * (1 - ease_out((t - t_in) / 0.45)) - 26 * smooth((t - t_out) / dout)
    return a, dy


def title_spr(s, size=84, rgb=None):
    return card(s, size, 'Heavy', rgb or P, panel=False, maxw=1000, pad=(20, 10))


# ------------------------------------------------------------------ overlays
@functools.lru_cache(None)
def _grad(h0, h1, a0, a1):
    y = np.arange(H, dtype=np.float32)
    return (a0 + (a1 - a0) * np.clip((y - h0) / (h1 - h0), 0, 1))[:, None, None]


@functools.lru_cache(None)
def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.45 * np.clip(r - 0.55, 0, 1) ** 1.4)[..., None]


def grade(c):
    c *= (1 - _grad(120, 640, 0.84, 0.0)) * (1 - _grad(1180, 1920, 0.0, 0.74))
    c *= _vignette()


def glow(c, cx, cy, size, rgb, alpha):
    fx.over(c, fx.warp(fx.radial(256, rgb, power=2.2), cx, cy, size / 256), alpha, add=True)


def picture_lamps(c, cam, t):
    for k, p in enumerate(HEROES):
        on = smooth((t - LIGHT_ON[k]) / 0.12)
        if on <= 0:
            continue
        pts, z = cam.project(np.array([p.lamp_pos()]))
        if z[0] < 0.4:
            continue
        glow(c, pts[0, 0], pts[0, 1], 1.1 * GL.F / z[0], (255, 226, 180), 0.28 * on * math.exp(-z[0] / 30))


@functools.lru_cache(None)
def fly_sprite(n):
    im = Image.new('RGBA', (n * 4, n * 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n * 2
    d.ellipse([c - n * 0.9, c - n * 1.3, c + n * 0.1, c - n * 0.1], fill=(200, 230, 255, 120))
    d.ellipse([c - n * 0.1, c - n * 1.3, c + n * 0.9, c - n * 0.1], fill=(200, 230, 255, 120))
    d.ellipse([c - n * 0.55, c - n * 0.45, c + n * 0.55, c + n * 0.55], fill=(22, 26, 22, 255))
    return im.resize((n, n), Image.LANCZOS)


def flies(c, cam, t):
    """A few buzzing flies around the camera's focus point (Lissajous paths, seeded)."""
    rng = np.random.default_rng(42)
    fwd = cam.R @ np.array([0, 0, -1.0])
    centre = cam.p + fwd * 2.2
    for k in range(7):
        a, b, ph = rng.uniform(1.3, 2.6), rng.uniform(1.1, 2.4), rng.uniform(0, 6.28)
        off = np.array([math.sin(t * a + ph) * 0.9, 0.5 + math.sin(t * b * 1.3 + ph) * 0.5 + k * 0.08,
                        math.cos(t * a * 0.7 + ph) * 0.9]) * [1.0, 1.0, 1.0]
        side = cam.R @ np.array([1.0, 0, 0]) * (rng.uniform(-1.2, 1.2))
        p = centre + side + cam.R @ off
        pts, z = cam.project(p[None])
        if z[0] < 0.4:
            continue
        x, y = pts[0]
        x += 3 * math.sin(t * 90 + k)
        size = int(np.clip(70 / z[0], 6, 40))
        fx.over(c, fx.warp(fly_sprite(size), x, y, 1.0), 0.9)


def hook_text(c, t):
    k = spring(t - HOOK['title'], f=1.5, z=0.5)
    al, _ = env_in_out(t, HOOK['title'], HOOK_MOVE[1] - 0.65, din=0.15)
    if al > 0:
        put(c, title_spr('Кал-лекция', 150), W / 2, 540, al, scale=0.85 + 0.15 * k)
        a2, dy2 = env_in_out(t, HOOK['title'] + 0.3, HOOK_MOVE[1] - 0.65)
        put(c, card('в подарках Telegram', 58, 'Semibold', GOLD, panel=False, maxw=1000, pad=(20, 10)),
            W / 2, 660, a2, 'hook-sub', dy=dy2)
    a3, dy3 = env_in_out(t, HOOK['real'], HOOK_MOVE[1] - 0.35)
    put(c, card('Какашку можно подарить. Официально', 50, 'Semibold', P), W / 2, 1440, a3, 'hook-real', dy=dy3)


SCREEN = [
    dict(f1='Вышла в ночь на 1 апреля 2025', f2='Все 50 моделей — какашки',
         f3='Редчайшая — Kinky Stinky · 0,1%'),
    dict(f1='Та же редкость — 0,1%', f2='Мем из YouTube-сериала 2023 года'),
    dict(f1='Popsicle + poop = Poopsicle', f2='Такая же — у Pet Snake, 1,5%',
         teaser='Дальше — какашка, за которой нужно убирать'),
    dict(f1='Тамагочи — Bandai, 1996', f2='Питомец какал. Не убрал — заболел'),
    dict(f1='Если дарить — то золотую', f2='В золоте и самоцветах — 0,5%'),
]


def stack(c, t, items, name):
    """items: [(sprite, t_in, t_out)] stacked from y = 1372 downwards."""
    y = 1372
    for k, (spr, a_, b_) in enumerate(items):
        a, dy = env_in_out(t, a_, b_)
        put(c, spr, W / 2, y + spr[0].height / 2, a, f'{name}{k}', dy=dy)
        y += spr[0].height + 20


def hero_text(c, t, k):
    h, hd, sc = HEROES_T[k], config.HEROES[k], SCREEN[k]
    if t < h['title'] - 0.1 or t > h['out'] + 0.5:
        return
    al, dy = env_in_out(t, h['title'], h['out'])
    name = hd['title'] if k != 0 or t < h['swap'] else 'Kinky Stinky'
    if k == 0:
        a_sw = smooth((t - h['swap']) / 0.25)
        put(c, title_spr(hd['title']), W / 2, 214, al * (1 - a_sw), 'title', dy=dy)
        put(c, title_spr('Kinky Stinky'), W / 2, 214, al * a_sw, 'title2', dy=dy)
        sub = card('Happy Brownie · 0,1%' if t >= h['swap'] else 'подарок-какашка · 50 моделей', 40, 'Medium', GOLD,
                   panel=False, maxw=1000, pad=(20, 8))
    else:
        put(c, title_spr(name), W / 2, 214, al, 'title', dy=dy)
        sub = card(hd['rarity'], 40, 'Medium', GOLD, panel=False, maxw=1000, pad=(20, 8))
    put(c, sub, W / 2, 300, al * smooth((t - h['title'] - 0.15) / 0.3), 'subtitle', dy=dy)
    s1, s2 = card(sc['f1'], 46, 'Semibold', P), card(sc['f2'], 46, 'Semibold', P)
    facts_out = h.get('facts_out', h['out'])
    stack(c, t, [(s1, h['f1'], facts_out), (s2, h['f2'], facts_out)], 'fact')
    if 'f3' in sc:
        stack(c, t, [(card(sc['f3'], 50, 'Semibold', P, edge=config.ALERT), h['f3'], h['out'])], 'verdict')
    if 'teaser' in sc:
        stack(c, t, [(card(sc['teaser'], 50, 'Semibold', GOLD, edge=GOLD), h['teaser'], h['out'])], 'teaser')
    fa, _ = env_in_out(t, h['f1'], h['out'])
    put(c, card(f'редкость: {config.DATA_SOURCE} · {config.DATA_DATE}', 26, 'Regular', (150, 160, 150),
                panel=False, pad=(10, 6)), W / 2, 1752, 0.85 * fa, 'source')


FAN_PATHS = [anim('Happy Brownie', m) for m in config.FAN]
SIDE = anim(*config.SIDE_POOPSICLE[:2])
SYM = [Image.open(G.symbol_png('Plush Pepe', s, 256)).convert('RGBA') for s in config.PATTERNS]


def fan(c, t):
    """«Все 50 моделей»: eight more Happy Brownie models pop around the portrait, then leave."""
    h = HEROES_T[0]
    u = t - h['fan']
    if u <= 0 or t > h['swap'] + 0.6:
        return
    out = smooth((t - h['swap'] + 0.1) / 0.4)
    for j, path in enumerate(FAN_PATHS):
        uj = u - 0.07 * j
        if uj <= 0:
            continue
        ang = -math.pi / 2 + (j + 0.5) / len(FAN_PATHS) * 2 * math.pi
        r = 470 + 30 * math.sin(j * 1.7)
        cx, cy = W / 2 + math.cos(ang) * r * 0.95, 840 + math.sin(ang) * r * 1.05
        sp = spring(uj, f=1.9, z=0.5) * (1 - out)
        if sp <= 0.02:
            continue
        im = lottie.frame(path, t + 0.3 * j, size=190)
        fx.over(c, fx.warp(im, cx, cy, sp), min(1.0, uj / 0.15) * (1 - out))


def side_poopsicle(c, t):
    """Pet Snake's Poopsicle pops in beside the second fact card (same name, other gift)."""
    h = HEROES_T[2]
    u = t - h['side']
    if u <= 0 or t > h['facts_out'] + 0.4:
        return
    s1 = card(SCREEN[2]['f1'], 46, 'Semibold', P)
    s2 = card(SCREEN[2]['f2'], 46, 'Semibold', P)
    cy = 1372 + s1[0].height + 20 + s2[0].height / 2
    cx = W / 2 + s2[0].width / 2 + 78
    a = 1 - smooth((t - h['facts_out']) / 0.3)
    sp = spring(u, f=1.8, z=0.5)
    glow(c, cx, cy, 300 * sp, (255, 170, 210), 0.3 * a)
    fx.over(c, fx.warp(lottie.frame(SIDE, t, size=150), cx, cy + 30 * (1 - sp), max(0.02, sp)), a)


def final(c, t):
    f = FINAL
    a, dy = env_in_out(t, f['big'], DUR + 1)
    put(c, title_spr('72 из 124', 120, GOLD), W / 2, 250, a, 'final-big', dy=dy)
    a2, dy2 = env_in_out(t, f['big'] + 0.35, DUR + 1)
    put(c, card('подарков прячут в узоре унитаз или рулон бумаги', 44, 'Semibold', P, panel=False, maxw=640,
                pad=(20, 10)), W / 2, 395, a2, 'final-sub', dy=dy2)
    # the two pattern symbols: tile rain at the bottom
    for j, (key, im) in enumerate(zip(('toilet', 'paper'), SYM)):
        u = t - f[key]
        if u <= 0:
            continue
        for q in range(5):
            uq = u - 0.06 * q
            if uq <= 0:
                continue
            cx = 150 + q * 195 + (j * 97)
            cy = 1300 + j * 175 + 14 * math.sin(t * 2 + q)
            sp = spring(uq, f=1.8, z=0.55)
            tint = np.asarray(im, np.float32).copy()
            tint[..., :3] = np.array(P, np.float32)
            fx.over(c, fx.warp(Image.fromarray(tint.astype(np.uint8), 'RGBA'), cx, cy, 0.55 * sp), 0.85)
    a3, dy3 = env_in_out(t, f['cta'], DUR + 1)
    put(c, card('Перешли тому, кому давно пора подарить какашку', 44, 'Semibold', P, edge=GOLD), W / 2, 1660,
        a3, 'cta', dy=dy3)


# ------------------------------------------------------------------ frame
def render_at(t):
    pos, yaw, pitch = camera(t)
    cam = Cam(pos, yaw, pitch, shake(t))
    lm = lamps(t)
    c = GL.environment(cam, t, lm)
    for p in sorted(ALL, key=lambda p: -float(np.linalg.norm(p.centre() - cam.p))):
        p.draw(c, cam, t, lm)
    picture_lamps(c, cam, t)
    k = smooth((t - HEROES_T[4]['stamp']) / 0.5)
    if k > 0:
        pts, z = cam.project(np.array([HEROES[4].centre() + (0, 0, 0.05)]))
        if z[0] > 0.4:
            glow(c, pts[0, 0], pts[0, 1], 2.9 * GL.F / z[0], (255, 200, 90), 0.3 * k)
    flies(c, cam, t)
    grade(c)
    hook_text(c, t)
    fan(c, t)
    for j in range(5):
        hero_text(c, t, j)
    side_poopsicle(c, t)
    a, dy = env_in_out(t, PULLBACK[0] + 0.1, FINAL['big'] - 0.3, dout=0.25)
    put(c, title_spr('Проверь свои подарки', 76), W / 2, 250, a, 'check', dy=dy)
    if t > FINAL['big'] - 0.2:
        final(c, t)
    e = smooth((t - FINAL['fade']) / (DUR - FINAL['fade']))
    if e > 0:
        c *= 1 - e
    return np.clip(c, 0, 255).astype(np.uint8)


def frame_bytes(i):
    out = BR.render(render_at, i / FPS, i).tobytes()
    layout.flush(i)
    return out


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Wait for «собирай», then set STYLE_READY = True in config.py')
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
