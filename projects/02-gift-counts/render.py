"""02-gift-counts: «Ночная галерея графа». 3D corridor, live Lottie portraits, verdict stamps, RubUp pause."""
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
from events import (DUR, HOOK_MOVE, TRANSITS, PULLBACK, AD_STOP, HOOK_T, HEROES_T, TEASER_T, FINAL_T,
                    LIGHT_ON)
from script import HOOK, FACTS, TEASER, FINAL

FPS = 60
BR = banner.Breaks([AD_STOP], cy=H / 2)
P = config.PARCHMENT
GOLD = config.GOLD
BLOOD = config.BLOOD

# ------------------------------------------------------------------ portraits (world placement)
D_HERO, D_END = 4.0, 4.4
HERO_Y, END_Y = 2.32, 2.34
PX_PER_M = 500                       # texture density of a close portrait


class Portrait:
    def __init__(self, gift, model, wall, z, w, h, yc, backdrop, hero=None, stamp=None, stamp_rgb=None):
        self.gift, self.model, self.wall, self.z = gift, model, wall, z
        self.w, self.h, self.yc = w, h, yc
        self.c0, self.c1 = backdrop
        self.hero = hero
        self.stamp, self.stamp_rgb = stamp, stamp_rgb
        self.path = str(G.model_file(gift, model, 'json'))
        self.phase = (hash_str(gift) % 997) / 997 * 3.0
        self.border = 0.13
        self.margin = 0.12

    def corners(self):
        m = self.margin
        return GL.wall_quad(self.wall, 0.0 if self.wall == 'E' else self.z, self.yc,
                            self.w + 2 * m, self.h + 2 * m)

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

    def texture(self, t, ppm):
        w, h = int(self.w * ppm), int(self.h * ppm)
        b, m = int(self.border * ppm), int(self.margin * ppm)
        cw, ch = w - 2 * b, h - 2 * b
        can = GL.backdrop(cw, ch, self.c0, self.c1).copy()
        size = int(min(cw, ch) * 0.86)
        lot = np.asarray(lottie.frame(self.path, t + self.phase, size=size), np.float32)
        x0, y0 = (cw - size) // 2, int((ch - size) * 0.42)
        al = lot[..., 3:4] / 255
        reg = can[y0:y0 + size, x0:x0 + size]
        reg[:] = reg * (1 - al) + lot[..., :3] * al
        if self.hero is not None and self.stamp:
            ts = HEROES_T[self.hero]['stamp']
            u = t - ts
            if u > 0:
                st = GL.stamp_img(self.stamp, self.stamp_rgb, max(8, int(0.2 * ppm)))
                k = 1.0 + 0.9 * (1 - ease_out(u / 0.13))
                a = min(1.0, u / 0.08)
                sw, sh = int(st.width * k), int(st.height * k)
                if sw > 2 and sh > 2:
                    s2 = np.asarray(st.resize((sw, sh), Image.BILINEAR), np.float32)
                    cx, cy = int(cw * 0.56), int(ch * 0.80)
                    xa, ya = cx - sw // 2, cy - sh // 2
                    xb, yb = max(xa, 0), max(ya, 0)
                    xe, ye = min(xa + sw, cw), min(ya + sh, ch)
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
        lum = min(1.25, GL.light_at(self.centre() + (0, 0, 0), t, lamps))
        art[..., :3] *= lum
        tex = Image.fromarray(np.clip(art, 0, 255).astype(np.uint8), 'RGBA')
        return GL.draw_quad(canvas, cam, corners, tex)


def hash_str(s):
    return sum((i + 1) * ord(c) for i, c in enumerate(s))


HEROES = []
for k, hd in enumerate(config.HEROES):
    big = hd['wall'] == 'E'
    HEROES.append(Portrait(hd['gift'], hd['model'], hd['wall'], hd['z'], 1.9 if big else 1.7, 2.24 if big else 2.0,
                           END_Y if big else HERO_Y, hd['backdrop'], hero=k, stamp=hd['stamp'],
                           stamp_rgb=hd['stamp_rgb']))
DRACS = []
_DRAC_BACK = [('#a35e66', '#340307'), ('#5c6985', '#030a18'), ('#b17da5', '#652852'), ('#363738', '#0e0f0f')]
for k, (gift, rarity) in enumerate(config.DRACULAS):
    DRACS.append(Portrait(gift, 'Dracula', 'L' if k % 2 == 0 else 'R', -8.0 - 5 * k, 1.5, 1.8, 2.35,
                          _DRAC_BACK[k % len(_DRAC_BACK)]))
ALL = DRACS + HEROES


# ------------------------------------------------------------------ camera path
def focus(k, d=None):
    p = HEROES[k]
    if p.wall == 'L':
        return np.array([-HALF + (d or D_HERO), EYE, p.z]), math.pi / 2
    if p.wall == 'R':
        return np.array([HALF - (d or D_HERO), EYE, p.z]), -math.pi / 2
    return np.array([0.0, EYE, Z_END + (d or D_END)]), 0.0


def hold_pose(k, t):
    """Slow push-in + tiny sway while hero k is on screen."""
    h = HEROES_T[k]
    leave = h['leave']
    u = smooth((t - h['arrive']) / max(0.1, leave - h['arrive']))
    d0 = D_END if HEROES[k].wall == 'E' else D_HERO
    pos, yaw = focus(k, d0 - 0.25 * u)
    yaw += 0.012 * math.sin(t * 0.9 + k)
    return pos, yaw


def camera(t):
    a, b = HOOK_MOVE
    if t < b:
        u = max(0.0, t) / b
        p1, y1 = hold_pose(0, b)
        p0 = np.array([0.0, EYE, 4.0])
        zz = p0[2] + (p1[2] - p0[2]) * (1 - (1 - u) ** 2.3)
        turn = smooth((u - 0.66) / 0.34)
        pos = np.array([p0[0] + (p1[0] - p0[0]) * turn, EYE, zz])
        yaw = y1 * turn
        pitch = 0.04 * (1 - smooth(u / 0.8))
        return pos, yaw, pitch
    for k, (ta, tb) in enumerate(TRANSITS):
        if t < ta:
            pos, yaw = hold_pose(k, t)
            return pos, yaw, 0.0
        if t < tb:
            s = smooth((t - ta) / (tb - ta))
            pa, ya = hold_pose(k, ta)
            pb, yb = hold_pose(k + 1, tb)
            pos = pa + (pb - pa) * s
            pos[1] = EYE + 0.15 * math.sin(math.pi * s)         # slight lift through the turn
            return pos, ya + (yb - ya) * s, 0.0
    if t < PULLBACK[0]:
        pos, yaw = hold_pose(4, t)
        return pos, yaw, 0.0
    s = smooth((t - PULLBACK[0]) / (PULLBACK[1] - PULLBACK[0]))
    pa, ya = hold_pose(4, PULLBACK[0])
    pos = pa + np.array([0.0, 0.25 * s, 8.5 * s])
    return pos, ya, -0.02 * s


def shake(t):
    s = 0.0
    for h in HEROES_T:
        s += 16 * bump(t - h['stamp'], f=7.0, decay=9.0)
    return (0.4 * s, s)


def lamps(t):
    out = []
    for k, p in enumerate(HEROES):
        on = smooth((t - LIGHT_ON[k]) / 0.12)
        if on > 0:
            out.append((p.lamp_pos(), 2.2 * on * (1.15 if k == 4 else 1.0), (1.0, 0.86, 0.66)))
    return out


# ------------------------------------------------------------------ text sprites
def wrap(s, size, weight, maxw):
    f = fx.font(weight, size)
    words, lines, cur = s.split(), [], ''
    for w_ in words:
        nxt = (cur + ' ' + w_).strip()
        if f.getlength(nxt) <= maxw or not cur:
            cur = nxt
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return tuple(lines)


@functools.lru_cache(None)
def card(text, size, weight, rgb, panel=True, edge=None, maxw=860, lh=1.28, pad=(40, 30)):
    """-> (RGBA image, inks relative to image, cap band). Multi-line, centred, measured ink."""
    lines = wrap(text, size, weight, maxw)
    f = fx.font(weight, size)
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
        d.rounded_rectangle([0, 0, Wc * S - 1, Hc * S - 1], 26 * S, fill=(14, 8, 14, 205),
                            outline=(edge or GOLD) + (150,), width=2 * S)
    top = (Hc - band_h) / 2
    inks = []
    fS = fx.font(weight, size * S)
    for j, s in enumerate(lines):
        base = top + cap + j * step
        x, _ = layout.centered(s, size, weight, cx=Wc / 2, cy=0)
        d.text((x * S, base * S), s, font=fS, fill=rgb + (255,), anchor='ls')
        inks.append(layout.box_of(s, size, weight, x, base))
    im = im.resize((Wc, Hc), Image.LANCZOS)
    return im, tuple(inks), (top, top + band_h)


def put(c, spr, cx, cy, alpha, name=None, dy=0.0, scale=1.0, audit=True):
    im, inks, band = spr
    if alpha <= 0.01:
        return
    placed = fx.warp(im, cx, cy + dy, scale)
    fx.over(c, placed, alpha)
    if audit and name and scale == 1.0 and abs(dy) < 0.5:
        x0, y0 = cx - im.width / 2, cy - im.height / 2
        layout.record(name, (x0, y0, x0 + im.width, y0 + im.height),
                      [(a + x0, b + y0, r + x0, q + y0) for a, b, r, q in inks],
                      band=(band[0] + y0, band[1] + y0), alpha=alpha)


def env_in_out(t, t_in, t_out, din=0.35, dout=0.3):
    if t < t_in or t > t_out + dout:
        return 0.0, 0.0
    a = smooth((t - t_in) / din) * (1 - smooth((t - t_out) / dout))
    dy = 34 * (1 - ease_out((t - t_in) / 0.5)) - 26 * smooth((t - t_out) / dout)
    return a, dy


# ------------------------------------------------------------------ overlays
@functools.lru_cache(None)
def _grad(h0, h1, a0, a1):
    y = np.arange(H, dtype=np.float32)
    k = np.clip((y - h0) / (h1 - h0), 0, 1)
    return (a0 + (a1 - a0) * k)[:, None, None]


@functools.lru_cache(None)
def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    return (1 - 0.45 * np.clip(r - 0.55, 0, 1) ** 1.4)[..., None]


def grade(c):
    top = _grad(0, 560, 0.62, 0.0)
    bot = _grad(1180, 1920, 0.0, 0.7)
    c *= (1 - top) * (1 - bot)
    c *= _vignette()


def glow(c, cx, cy, size, rgb, alpha):
    fx.over(c, fx.warp(fx.radial(256, rgb, power=2.2), cx, cy, size / 256), alpha, add=True)


def candles(c, cam, t):
    pts, z = cam.project(np.array(GL.SCONCES))
    for k, ((x, y), d) in enumerate(zip(pts, z)):
        if d < 0.4 or d > 40 or not (-80 < x < W + 80 and -80 < y < H + 80):
            continue
        fl = GL.flicker(k, t)
        s = GL.F / d
        fog = math.exp(-d / 24)
        glow(c, x, y, 2.2 * s, (255, 150, 70), 0.35 * fl * fog)
        glow(c, x, y - 0.04 * s, 0.32 * s, (255, 220, 150), 0.95 * fog)


def picture_lamps(c, cam, t):
    for k, p in enumerate(HEROES):
        on = smooth((t - LIGHT_ON[k]) / 0.12)
        if on <= 0:
            continue
        (x, y), = cam.project(np.array([p.lamp_pos()]))[0]
        d = cam.project(np.array([p.lamp_pos()]))[1][0]
        if d < 0.4:
            continue
        s = GL.F / d
        glow(c, x, y, 1.1 * s, (255, 214, 160), 0.3 * on * math.exp(-d / 24))


def dust(c, cam, t):
    rng = np.random.default_rng(1897)
    n = 260
    base = rng.random((n, 3)) * [2 * HALF - 0.4, 4.6, 14.0] + [-HALF + 0.2, 0.3, 0.0]
    z0 = cam.p[2] - 13.0
    pts = base.copy()
    pts[:, 2] = z0 + ((base[:, 2] + 0.3 * t) % 14.0)
    pts[:, 0] += 0.15 * np.sin(t * 0.5 + base[:, 1] * 3)
    pts[:, 1] += 0.1 * np.sin(t * 0.37 + base[:, 0] * 2)
    scr, z = cam.project(pts)
    ok = (z > 0.6) & (scr[:, 0] > 0) & (scr[:, 0] < W - 1) & (scr[:, 1] > 0) & (scr[:, 1] < H - 1)
    for (x, y), d in zip(scr[ok], z[ok]):
        r = max(1.0, 9.0 / d)
        a = 0.5 * math.exp(-d / 9)
        glow(c, x, y, 6 * r, (255, 210, 160), a)


def hook_text(c, t):
    (a1, b1), (a2, b2) = HOOK_T
    k = spring(t - a1, f=1.5, z=0.5)
    al, dy = env_in_out(t, a1, b1, din=0.2)
    if al > 0:
        sc = 0.85 + 0.15 * k
        put(c, card(HOOK[0][0], 168, 'Heavy', P, panel=False, maxw=1000, pad=(20, 10)), W / 2, 540, al,
            'hook-12', dy=0, scale=sc, audit=False)
        put(c, card(HOOK[0][1], 58, 'Semibold', GOLD, panel=False, maxw=1000, pad=(20, 10)), W / 2, 668,
            al * smooth((t - a1 - 0.25) / 0.3), 'hook-sub', dy=dy)
    al, dy = env_in_out(t, a2, b2)
    if al > 0:
        put(c, card(HOOK[1][0], 64, 'Heavy', P, panel=False, maxw=1040, pad=(20, 10)), W / 2, 1420, al,
            'hook-real', dy=dy)
        al3, dy3 = env_in_out(t, a2 + 0.55, b2)
        put(c, card(HOOK[1][1], 52, 'Medium', GOLD, panel=False, maxw=1000, pad=(20, 10)), W / 2, 1515, al3,
            'hook-guess', dy=dy3)


def hero_text(c, t, k):
    h = HEROES_T[k]
    hd = config.HEROES[k]
    if t < h['title'] - 0.1 or t > h['leave'] + 0.5:
        return
    al, dy = env_in_out(t, h['title'], h['out'])
    if k == 2:
        al, dy = env_in_out(t, h['title'], TEASER_T[1] - 0.25)
    put(c, card(hd['model'], 84, 'Heavy', P, panel=False, maxw=1000, pad=(20, 10)), W / 2, 214, al, 'title', dy=dy)
    sub = f"{hd['gift']} · {hd['rarity']}"
    put(c, card(sub, 40, 'Medium', GOLD, panel=False, maxw=1000, pad=(20, 8)), W / 2, 300,
        al * smooth((t - h['title'] - 0.15) / 0.3), 'subtitle', dy=dy)
    f1, f2, verdict = FACTS[k]
    out_facts = h['stamp'] if verdict else h['out']
    s1 = card(f1, 46, 'Semibold', P)
    s2 = card(f2, 46, 'Semibold', P)
    y1 = 1372 + s1[0].height / 2
    y2 = 1372 + s1[0].height + 20 + s2[0].height / 2
    a, d_ = env_in_out(t, h['f1'], out_facts)
    put(c, s1, W / 2, y1, a, 'fact1', dy=d_)
    a, d_ = env_in_out(t, h['f2'], out_facts)
    put(c, s2, W / 2, y2, a, 'fact2', dy=d_)
    if verdict:
        sv = card(verdict, 48, 'Semibold', P, edge=hd['stamp_rgb'])
        a, d_ = env_in_out(t, h['stamp'] + 0.25, h['out'])
        put(c, sv, W / 2, 1400 + sv[0].height / 2, a, 'verdict', dy=d_)
    fa, _ = env_in_out(t, h['f1'], h['out'] if k != 2 else TEASER_T[1] - 0.25)
    src = card(f'редкость: {config.DATA_SOURCE} · {config.DATA_DATE}', 26, 'Regular', (150, 132, 120),
               panel=False, pad=(10, 6))
    put(c, src, W / 2, 1752, 0.85 * fa, 'source')


def teaser(c, t):
    a, dy = env_in_out(t, TEASER_T[0], TEASER_T[1] - 0.25)
    if a > 0:
        put(c, card(TEASER, 50, 'Semibold', GOLD, edge=GOLD), W / 2, 1470, a, 'teaser', dy=dy)


GRID = [(g, 'Dracula') for g, _ in config.DRACULAS[:3]] + [(h['gift'], h['model']) for h in config.HEROES[:4]] + \
       [(g, 'Dracula') for g, _ in config.DRACULAS[3:]] + [(config.HEROES[4]['gift'], config.HEROES[4]['model'])]
GRID_PATHS = [str(G.model_file(g, m, 'json')) for g, m in GRID]


def final(c, t):
    ft = FINAL_T
    a, dy = env_in_out(t, ft['line1'], DUR + 1)
    put(c, card(FINAL[0], 74, 'Heavy', P, panel=False, maxw=900, pad=(20, 10)), W / 2, 250, a, 'final1', dy=dy)
    u = t - ft['grid']
    if u > 0:
        cell = 150
        for j, path in enumerate(GRID_PATHS):
            r, q = divmod(j, 6)
            cx = W / 2 + (q - 2.5) * (cell + 14)
            cy = 1290 + r * (cell + 22)
            uj = u - 0.05 * j
            if uj <= 0:
                continue
            sp = spring(uj, f=1.8, z=0.55)
            real = j == len(GRID_PATHS) - 1
            fade = smooth((u - 0.9) / 0.4)
            alpha = smooth(uj / 0.2) * (1 - 0.6 * fade * (not real))
            if real:
                glow(c, cx, cy, 330 * sp * (0.6 + 0.4 * fade), (255, 196, 90), 0.55 * fade)
            im = lottie.frame(path, t + 0.37 * j, size=cell)
            if not real and fade > 0:
                arr = np.asarray(im, np.float32)
                g = arr[..., :3].mean(-1, keepdims=True)
                arr[..., :3] = arr[..., :3] * (1 - 0.85 * fade) + g * 0.85 * fade
                im = Image.fromarray(arr.astype(np.uint8), 'RGBA')
            fx.over(c, fx.warp(im, cx, cy + 40 * (1 - sp), max(0.05, sp)), alpha)
    a, dy = env_in_out(t, ft['line2'], DUR + 1)
    put(c, card(FINAL[1], 64, 'Heavy', GOLD, panel=False, maxw=1000, pad=(20, 10)), W / 2, 1560, a, 'final2', dy=dy)
    a, dy = env_in_out(t, ft['cta'], DUR + 1)
    put(c, card(FINAL[2], 40, 'Medium', P, panel=False, maxw=1000, pad=(20, 8)), W / 2, 1660, a * 0.9, 'cta', dy=dy)


# ------------------------------------------------------------------ frame
def render_at(t):
    pos, yaw, pitch = camera(t)
    cam = Cam(pos, yaw, pitch, shake(t))
    lm = lamps(t)
    c = GL.environment(cam, t, lm)
    for p in sorted(ALL, key=lambda p: -float(np.linalg.norm(p.centre() - cam.p))):
        p.draw(c, cam, t, lm)
    candles(c, cam, t)
    picture_lamps(c, cam, t)
    if t > 44.0:                                      # gold aura of the one real count
        h = HEROES_T[4]
        k = smooth((t - h['stamp']) / 0.5)
        if k > 0:
            (x, y), = cam.project(np.array([HEROES[4].centre() + (0, 0, 0.05)]))[0]
            d = cam.project(np.array([HEROES[4].centre()]))[1][0]
            glow(c, x, y, 2.9 * GL.F / d, (255, 190, 80), 0.32 * k)
    dust(c, cam, t)
    grade(c)
    hook_text(c, t)
    for k in range(5):
        hero_text(c, t, k)
    teaser(c, t)
    if t > FINAL_T['line1'] - 0.2:
        final(c, t)
    a0 = 1 - smooth(t / 0.12)
    if a0 > 0:
        c *= 1 - a0
    e = smooth((t - FINAL_T['fade']) / (DUR - FINAL_T['fade']))
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
