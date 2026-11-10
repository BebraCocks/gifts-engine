"""43-aura-ludoman: marble gambler head + hands over the RubUp screen recording, eye fire by emotion, beat-cut.
Frame = f(track time). No RubUp ad break (author, 2026-11-10)."""
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as nd
import frames
import fx
import gifts_api
import lottie
import config
import events as E
from timeline import DUR, HITS, DROP1, DROP2, BREAK, src_at, seg_index, SEG

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BUILD = paths.build(HERE)
SRC = BUILD / 'src'

# ---------------------------------------------------------------- assets
HEAD = np.asarray(Image.open(HERE / 'assets' / 'head.png'), np.float32)          # 831 x 757 RGBA
HAND_R = Image.open(HERE / 'assets' / 'hand_r.png').convert('RGBA')
HAND_L = Image.open(HERE / 'assets' / 'hand_l.png').convert('RGBA')
HAND_PT = Image.open(HERE / 'assets' / 'hand_point.png').convert('RGBA')   # generated (Fish nano-banana, 2026-11-10)
PT_TIP = (15.0, 23.0)                                                      # index fingertip in hand_point.png
EYES = np.array([(307.0, 410.0), (515.0, 417.0)])                                 # in head.png
HEAD_ANCHOR = (378.0, 800.0)                                                      # neck, bottom centre
LIP_Y, MOUTH_X, MOUTH_HW, JAW_HW = 625.0, 405.0, 66.0, 175.0
HAND_TIP_R = (70.0, 300.0)                                                        # fingertips in hand_r.png



def src_frame(s):
    k = int(round(s * 60))
    for d in (0, 1, -1, 2, -2, 3, -3):
        p = SRC / f'{k + d:06d}.jpg'
        if p.exists():
            return Image.open(p).convert('RGB')
    raise FileNotFoundError(f'no source frame near {s:.2f} s')


def _logo():
    """Crisp RubUp logo (top-left of the recording) with alpha, kept on top so a dimmed popup never hides it."""
    im = np.asarray(src_frame(9.4), np.float32)
    x0, y0, x1, y1 = (int(v * E.CARD_S) for v in (12, 22, 160, 100))             # crop coords (orig y-190)
    reg = im[y0:y1, x0:x1]
    bg = np.median(np.concatenate([reg[:4].reshape(-1, 3), reg[-4:].reshape(-1, 3)]), 0)
    a = np.clip(np.abs(reg - bg).max(2) / 110.0, 0, 1)
    rgb = bg + (reg - bg) / np.maximum(a[..., None], 1e-3)
    rgba = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    return Image.fromarray(rgba, 'RGBA'), E.CARD_X + x0, E.CARD_Y + y0


LOGO = _logo()

# ---------------------------------------------------------------- voice envelope (mouth)
def _voice_env():
    f = BUILD / 'voice_env.npy'
    if f.exists():
        return np.load(f)
    import voice_review
    sr = voice_review.SR
    v = voice_review.voice_track(int(DUR * sr) + sr)
    hop = sr // FPS
    e = np.array([np.sqrt((v[k:k + hop] ** 2).mean()) for k in range(0, len(v) - hop, hop)])
    e = e / (np.percentile(e[e > 1e-4], 95) + 1e-9)
    out, prev = np.zeros_like(e), 0.0
    for k, x in enumerate(np.clip(e, 0, 1.2)):                                     # fast attack, slower release
        prev = prev + (x - prev) * (0.55 if x > prev else 0.22)
        out[k] = prev
    np.save(f, out)
    return out


ENV = _voice_env()


def talk(t):
    k = int(t * FPS)
    return float(ENV[k]) if 0 <= k < len(ENV) else 0.0


# ---------------------------------------------------------------- emotion -> eye fire
FIRE = {   # core, mid, outer, height, width, intensity, turbulence, size
    'calm':    ((215, 235, 255), (60, 120, 255), (20, 30, 160), 120, 34, 0.90, 0.6, 16),
    'tense':   ((255, 225, 255), (175, 60, 255), (70, 0, 150), 165, 38, 1.05, 0.9, 17),
    'annoyed': ((255, 240, 200), (255, 140, 30), (170, 45, 0), 160, 38, 1.05, 1.0, 17),
    'angry':   ((255, 220, 180), (255, 70, 20), (150, 10, 0), 215, 44, 1.20, 1.4, 19),
    'rage':    ((255, 240, 220), (255, 30, 10), (130, 0, 0), 300, 52, 1.45, 1.9, 23),
    'cocky':   ((220, 255, 255), (40, 200, 255), (0, 60, 170), 165, 36, 1.00, 0.8, 17),
    'sad':     ((200, 210, 235), (90, 110, 160), (40, 50, 85), 55, 22, 0.55, 0.3, 11),
    'joy':     ((255, 255, 230), (255, 200, 40), (255, 90, 0), 340, 58, 1.55, 1.3, 25),
    'greedy':  ((240, 255, 220), (110, 255, 80), (210, 170, 0), 210, 42, 1.20, 1.0, 19),
}


def fire_params(t):
    prev, cur, t_cur = None, E.EMO[0][1], E.EMO[0][0]
    for tk, st in E.EMO:
        if t >= tk:
            prev, cur, t_cur = cur, st, tk
    a = FIRE[cur]
    if prev is None or prev == cur:
        p = [np.array(v, float) if isinstance(v, tuple) else float(v) for v in a]
    else:
        u = fx.smooth(min(1.0, (t - t_cur) / 0.35))
        b = FIRE[prev]
        p = [np.array(bv, float) * (1 - u) + np.array(av, float) * u for av, bv in zip(a, b)]
    return p, cur


def hit_pulse(t):
    """0..1 kick on each bass hit (after the drops)."""
    best = 0.0
    for h in HITS:
        if 0 <= t - h < 0.5:
            best = max(best, math.exp(-(t - h) * 9))
    return best


def _hash(i, k):
    return np.modf(np.sin(i * 12.9898 + k * 78.233) * 43758.5453)[0] % 1.0


_SPRITES = {}


def sprite(r):
    r = max(2, int(r))
    s = _SPRITES.get(r)
    if s is None:
        yy, xx = np.mgrid[-2 * r:2 * r + 1, -2 * r:2 * r + 1]
        s = np.exp(-(xx ** 2 / (2 * (r * 0.5) ** 2) + yy ** 2 / (2 * (r * 0.85) ** 2))).astype(np.float32)
        _SPRITES[r] = s
    return s


RATE = 170.0


def draw_fire(canvas, eyes_xy, scale, t):
    p, state = fire_params(t)
    core, mid, outer, h, w, inten, turb, size = p
    pulse = hit_pulse(t)
    h = h * scale * (1 + 0.18 * pulse)
    w, size = w * scale, size * scale
    inten = inten * (1 + 0.25 * pulse)
    pad = int(h + 4 * size + 60)
    x0 = int(min(e[0] for e in eyes_xy) - w - 4 * size - 40)
    x1 = int(max(e[0] for e in eyes_xy) + w + 4 * size + 40)
    y0 = int(min(e[1] for e in eyes_xy) - pad)
    y1 = int(max(e[1] for e in eyes_xy) + 4 * size + 40)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    acc = np.zeros((y1 - y0, x1 - x0, 3), np.float32)

    def splat(cx, cy, r, col, e):
        s = sprite(r)
        n = s.shape[0] // 2
        ix, iy = int(cx) - x0, int(cy) - y0
        ax0, ay0, ax1, ay1 = max(0, ix - n), max(0, iy - n), min(acc.shape[1], ix + n + 1), min(acc.shape[0], iy + n + 1)
        if ax1 <= ax0 or ay1 <= ay0:
            return
        ss = s[ay0 - (iy - n):ay1 - (iy - n), ax0 - (ix - n):ax1 - (ix - n)]
        acc[ay0:ay1, ax0:ax1] += ss[..., None] * (col * e / 255.0)

    for ex, ey in eyes_xy:                                                        # burnt sockets
        r = int(34 * scale)
        sx0, sy0 = int(ex) - x0 - 2 * r, int(ey) - y0 - 2 * r
        sh = sprite(r)[: acc.shape[0] - sy0, : acc.shape[1] - sx0]
        if sx0 >= 0 and sy0 >= 0:
            reg = canvas[y0 + sy0:y0 + sy0 + sh.shape[0], x0 + sx0:x0 + sx0 + sh.shape[1], :3]
            reg *= (1 - 0.55 * sh[..., None])
    for k, (ex, ey) in enumerate(eyes_xy):
        # iris glow (eye burns from inside) and a soft halo
        splat(ex, ey, 26 * scale, mid, 0.45 * inten)
        splat(ex, ey, 9 * scale, core, 0.9 * inten)
        i0, i1 = int((t - 1.0) * RATE), int(t * RATE)
        idx = np.arange(i0, i1 + 1)
        life = 0.55 + 0.35 * _hash(idx, 1 + k * 7)
        age = (t - idx / RATE) / life
        keep = (age >= 0) & (age < 1) & (_hash(idx, 3 + k * 7) < 0.55 + 0.45 * min(1.0, inten / 1.2))
        for i, a in zip(idx[keep], age[keep]):
            r2, r3, r4 = _hash(i, 5 + k * 7), _hash(i, 9 + k * 7), _hash(i, 11 + k * 7)
            px = ex + (r3 - 0.5) * w * (1 - 0.5 * a) + turb * 13 * scale * math.sin(8.2 * t + i * 1.7) * a \
                + turb * 7 * scale * math.sin(15 * t + i * 0.9) * a * a
            py = ey - 8 * scale - h * (a ** 0.85) * (0.7 + 0.6 * r2)
            rad = size * (0.6 + 0.8 * r4) * (1 - a) ** 0.55 + 2
            col = core + (mid - core) * (a / 0.18) if a < 0.18 else mid + (outer - mid) * ((a - 0.18) / 0.82)
            if r4 > 0.93:                                                          # a spark: tiny, flies higher
                splat(px + (r2 - 0.5) * w * a, py - h * 0.5 * a, 3 * scale + 1, core, 0.9 * inten * (1 - a))
                continue
            splat(px, py, rad * (0.55 + 0.45 * a), col, 0.5 * inten * (1 - a) ** 0.9)
    light = 1 - np.exp(-acc * 2.2)
    al = np.clip(light.max(2, keepdims=True) * 1.15, 0, 1)
    col = light / np.maximum(al, 1e-3)
    reg = canvas[y0:y1, x0:x1, :3]
    reg[:] = reg * (1 - al) + col * 255 * al                                      # opaque flame (reads on white marble)
    reg[:] = np.minimum(255, reg + light * 60)                                    # plus a little light
    return mid


# ---------------------------------------------------------------- head with a jaw
_JAW = {}


def head_image(open_px):
    """Head RGBA (PIL) with the lower jaw dropped by open_px (head.png pixels)."""
    q = round(open_px * 2) / 2
    if q < 0.25:
        return Image.fromarray(HEAD.astype(np.uint8), 'RGBA')
    if q in _JAW:
        return _JAW[q]
    hh, ww = HEAD.shape[:2]
    ry0, ry1, rx0, rx1 = int(LIP_Y - 40), hh, int(MOUTH_X - JAW_HW - 5), int(MOUTH_X + JAW_HW + 5)
    yy, xx = np.mgrid[ry0:ry1, rx0:rx1].astype(np.float32)
    dx = np.abs(xx - MOUTH_X)
    gx = np.where(dx < 70, 1.0, np.clip(np.cos(np.clip((dx - 70) / (JAW_HW - 70), 0, 1) * math.pi / 2), 0, 1) ** 1.5)
    inner = np.clip((MOUTH_HW * 1.05 - dx) / (MOUTH_HW * 0.35), 0, 1)                # 1 inside the mouth width
    hard = (yy >= LIP_Y).astype(np.float32)
    soft = np.clip((yy - (LIP_Y - 30)) / 70, 0, 1)
    soft = soft * soft * (3 - 2 * soft)
    tail = np.clip((hh - yy) / 60, 0.35, 1)                                          # neck edge moves a bit less
    D = q * gx * (inner * hard + (1 - inner) * soft) * tail
    sy = yy - D
    out = HEAD.copy()
    reg = np.stack([nd.map_coordinates(HEAD[..., c], [sy, xx], order=1, mode='nearest') for c in range(4)], -1)
    # mouth cavity where the sample crossed the lip line
    open_col = q * gx * inner
    cav = inner * np.clip((LIP_Y - sy) / 1.5, 0, 1) * hard
    depth = np.clip((yy - LIP_Y) / np.maximum(open_col, 1), 0, 1)
    cav_rgb = np.stack([28 + 30 * (1 - depth), 14 + 12 * (1 - depth), 18 + 12 * (1 - depth)], -1)
    reg[..., :3] = reg[..., :3] * (1 - cav[..., None]) + cav_rgb * cav[..., None]
    reg[..., 3] = np.maximum(reg[..., 3], 255 * cav)
    out[ry0:ry1, rx0:rx1] = reg
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')
    if len(_JAW) > 64:
        _JAW.clear()
    _JAW[q] = im
    return im


# ---------------------------------------------------------------- character motion
def emotion_at(t):
    return fire_params(t)[1]


def head_move(t):
    """Story moves of the head (dx, dy, dscale), smooth between keys."""
    K = E.HEAD_KEYS
    if t <= K[0][0]:
        return K[0][1:]
    for (t0, *a), (t1, *b) in zip(K, K[1:]):
        if t0 <= t < t1:
            u = fx.smooth((t - t0) / (t1 - t0))
            return tuple(p + (q - p) * u for p, q in zip(a, b))
    return K[-1][1:]


def head_pose(t):
    """-> (anchor x, anchor y, scale, rotation rad)"""
    st = emotion_at(t)
    pulse = hit_pulse(t)
    tk = talk(t)
    base_s = 0.70
    big = 0.0                                          # joy moments: the head grows into the frame
    if E.HOOK_HIDE <= t < E.HOOK_END:
        big = fx.ease_out_back(min(1.0, (t - E.HOOK_HIDE) / 0.35)) * (1 - fx.smooth((t - (E.HOOK_END - 0.25)) / 0.25))
    if t >= DROP2:
        big = fx.ease_out_back(min(1.0, (t - DROP2) / 0.4)) * 0.75
    hxp, mdy, mds = head_move(t)
    s = base_s * (1 + 0.32 * big) * (1 + 0.025 * pulse + 0.01 * tk) * mds
    x, y = hxp, 1915.0 - 40 * big + mdy
    rot = 0.03 * math.sin(t * 1.3) + 0.02 * tk * math.sin(t * 7.0)
    y += 4 * math.sin(t * 2.1) - 10 * pulse
    if st in ('rage', 'angry'):
        amp = 1.0 if st == 'rage' else 0.45
        x += amp * 7 * math.sin(t * 61) + amp * 4 * math.sin(t * 37)
        rot += amp * 0.035 * math.sin(t * 47)
    if st == 'sad':
        rot -= 0.07
        y += 26
    if st == 'tense':
        s *= 1.03
    if st == 'joy':
        y -= 28 * abs(math.sin(t * math.pi / 0.5108))
        rot += 0.05 * math.sin(t * math.pi / 1.0216)
    if st == 'greedy':
        rot += 0.06 * math.sin(t * 2.4)
    return x, y, s, rot


def place_head(canvas, t):
    x, y, s, rot = head_pose(t)
    opening = 15.0 * min(1.0, talk(t) ** 0.8)
    im = head_image(opening)
    placed = fx.warp(im, x, y, s, rot_=rot, anchor=HEAD_ANCHOR)
    fx.over(canvas, placed)
    c, sn = math.cos(rot), math.sin(rot)
    eyes = [(x + s * (c * (ex - HEAD_ANCHOR[0]) - sn * (ey - HEAD_ANCHOR[1])),
             y + s * (sn * (ex - HEAD_ANCHOR[0]) + c * (ey - HEAD_ANCHOR[1]))) for ex, ey in EYES]
    return eyes, s, (x, y, s, rot)


def hand_pose(t, side):
    """-> (image, anchor, x, y, scale, rot)"""
    st = emotion_at(t)
    pulse = hit_pulse(t)
    hxp, hdy, hsc = head_move(t)                         # hands travel with the head
    rest_x = hxp + (-375.0 if side == 'L' else 375.0) * hsc
    x, y, s, rot = rest_x, 1745.0 + hdy + 900 * max(0.0, 1.0 - hsc) ** 1.2, 0.62 * hsc, 0.0   # aside -> hands sink
    ph = 0.0 if side == 'L' else 1.3
    y += 9 * math.sin(t * 1.9 + ph) - 12 * pulse
    x += 5 * math.sin(t * 1.1 + ph)
    img = HAND_L if side == 'L' else HAND_R
    anchor = (img.width / 2, img.height / 2)
    gesture = 0.0
    if st == 'joy':
        lift = 1.0
        if t >= DROP2:
            lift = fx.smooth((t - DROP2) / 0.35)
        elif E.HOOK_HIDE <= t < E.HOOK_END:
            lift = fx.smooth((t - E.HOOK_HIDE) / 0.25) * (1 - fx.smooth((t - (E.HOOK_END - 0.3)) / 0.3))
        y -= lift * (330 + 40 * abs(math.sin(t * math.pi / 0.5108 + ph)))
        x += lift * (-60 if side == 'L' else 60)
        rot += lift * (0.35 if side == 'L' else -0.35) + lift * 0.15 * math.sin(t * 12 + ph)
    elif st in ('rage', 'angry'):
        amp = 1.0 if st == 'rage' else 0.5
        y += amp * 10 * math.sin(t * 43 + ph)
        rot += amp * 0.08 * math.sin(t * 29 + ph)
    elif st == 'sad':
        y += 40
        rot += 0.12 if side == 'L' else -0.12
    elif st == 'greedy':
        rot += 0.1 * math.sin(t * 5 + ph)
    if side == 'R':
        for tp, (bx, by) in E.PRESSES:                    # right hand presses the buttons
            u = (t - (tp - 0.42)) / 0.42                   # approach
            v = (t - tp) / 0.45                            # return
            if 0 <= u < 1 or 0 <= v < 1:
                anchor = HAND_TIP_R
                tx, ty = bx + 10, by + 6
                rx, ry = x + (HAND_TIP_R[0] - img.width / 2) * s, y + (HAND_TIP_R[1] - img.height / 2) * s
                if u < 1:
                    k = fx.ease_in(u) if u > 0.55 else fx.smooth(u)
                    k = fx.smooth(u)
                else:
                    k = 1 - fx.smooth(v)
                x = rx + (tx - rx) * k
                y = ry + (ty - ry) * k - 60 * math.sin(math.pi * k) * (1 - k)
                rot = 0.45 * k
                touch = math.exp(-((t - tp) / 0.06) ** 2)
                s = s * (1 + 0.15 * k) * (1 - 0.18 * touch)
                gesture = fx.smooth(min(1.0, k * 2.2))         # the palm folds into a pointing finger on the way
                break
    for tt, hand, _ in E.THROWS:                          # CTA: a quick upward fling per throw
        if hand == side and -0.3 <= t - tt < 0.35:
            u = t - tt
            k = math.exp(-((u + 0.02) / 0.12) ** 2)
            y -= 150 * k
            rot += (0.6 if side == 'L' else -0.6) * k
            x += (-40 if side == 'L' else 40) * k
    return img, anchor, x, y, s, rot, gesture


def place_hand(canvas, t, side):
    img, anchor, x, y, s, rot, g = hand_pose(t, side)
    if g < 0.999:
        fx.over(canvas, fx.warp(img, x, y, s * (1 - 0.12 * g), rot_=rot, anchor=anchor), alpha=1 - g)
    if g > 0.001:                                       # pointing hand: fingertip on the same spot
        fx.over(canvas, fx.warp(HAND_PT, x, y, s * (0.88 + 0.12 * g), rot_=rot - 0.45, anchor=PT_TIP), alpha=g)


# ---------------------------------------------------------------- screen card
_CLEAN = {}


def card_image(t):
    st = src_at(t)
    s = src_frame(st)
    if 144.8 <= st <= 148.5:                              # toast «Цена цели изменилась…» is noise: clean LIVE row
        if 'live' not in _CLEAN:
            y0, y1 = int((318 - 190) * E.CARD_S), int((400 - 190) * E.CARD_S)
            _CLEAN['live'] = (src_frame(141.0).crop((0, y0, E.CARD_W, y1)), y0)
        patch, y0 = _CLEAN['live']
        s.paste(patch, (0, y0))
    if t < E.HOOK_END:                                    # the hook never shows the target or the result
        k = 1.0 if t >= E.HOOK_HIDE else 0.0
        hdr = s.crop((0, 0, E.CARD_W, HEADER))
        s = s.filter(ImageFilter.GaussianBlur(17 + 9 * k))
        s = Image.blend(s, Image.new('RGB', s.size, (8, 8, 20)), 0.2 + 0.15 * k)
        s.paste(hdr, (0, 0))                              # logo + balance stay sharp
    return s


def press_ripple(canvas, t):
    for tp, (bx, by) in E.PRESSES:
        u = (t - tp) / 0.45
        if 0 <= u < 1:
            r = 30 + 150 * fx.ease_out(u)
            a = (1 - u) ** 1.5 * 0.8
            fx.over(canvas, fx.draw_rgba((bx - r - 4, by - r - 4, bx + r + 4, by + r + 4),
                                         lambda d, m, S: d.ellipse([*m(bx - r, by - r), *m(bx + r, by + r)],
                                                                   outline=(255, 255, 255, int(220 * a)), width=int(5 * S))))


HEADER = 160                        # card-local px: logo + balance strip, never zoomed


def view(t):
    """Screen zoom inside the card window: (focus x, focus y in card px, zoom)."""
    best = (E.CARD_W / 2, E.CARD_H / 2, 1.0)
    for t0, t1, (ox, oy), z0, z1 in E.ZOOMS:
        if t0 - 0.01 <= t < t1:
            u = (t - t0) / (t1 - t0)
            zin = fx.ease_out(min(1.0, (t - t0) / 0.3))
            z = 1 + ((z0 + (z1 - z0) * fx.smooth(u)) - 1) * zin    # no zoom-out: it snaps back on a hit/cut
            return ox * E.CARD_S, (oy - 190) * E.CARD_S, z
    return best


def zmap(x, y, t):
    """Frame point of the unzoomed card -> where it is shown now."""
    fxc, fyc, z = view(t)
    qx, qy = x - E.CARD_X, y - E.CARD_Y
    return E.CARD_X + fxc + (qx - fxc) * z, E.CARD_Y + fyc + (qy - fyc) * z


def zoomed(im, t):
    fxc, fyc, z = view(t)
    if z <= 1.0005:
        return im
    box = (fxc - fxc / z, fyc - fyc / z, fxc + (E.CARD_W - fxc) / z, fyc + (E.CARD_H - fyc) / z)
    out = im.resize((E.CARD_W, E.CARD_H), Image.BICUBIC, box=box)
    hdr = im.crop((0, 0, E.CARD_W, HEADER))
    out.paste(hdr, (0, 0))
    sh = Image.new('RGBA', (E.CARD_W, 24), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([0, 0, E.CARD_W, 24], fill=(0, 0, 0, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(6)).crop((0, 12, E.CARD_W, 24))
    out = out.convert('RGBA')
    out.alpha_composite(sh, (0, HEADER))
    return out.convert('RGB')


def place_card(canvas, t, tint):
    """The screen recording fills the whole frame; it only ever zooms IN (beat pulse, story zooms)."""
    pulse = hit_pulse(t)
    im = zoomed(card_image(t), t)
    zoom = 1.0 + 0.006 * pulse
    if E.HOOK_END <= t < E.HOOK_END + 0.35:              # the story starts: punch-in that settles
        zoom *= 1 + 0.05 * (1 - fx.ease_out((t - E.HOOK_END) / 0.35))
    if zoom > 1.0005:
        cw, ch = W / zoom, H / zoom
        im = im.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    canvas[:, :, :3] = np.asarray(im, np.float32)
    fx.over(canvas, LOGO)


# ---------------------------------------------------------------- gift pop-outs
HERO = {'Neko Helmet': (0.0, -15.0, 600.0)}               # offset from the popup picture, final size


def place_pops(canvas, t):
    for tp, gift, model, (gx0, gy0), hold in E.POPS:
        u = t - tp
        gx, gy = zmap(gx0, gy0, t)
        total = 0.35 + hold + 0.35
        if not (0 <= u < total):
            continue
        path = gifts_api.model_file(gift, model, 'json')
        hx, hy, size1 = HERO.get(gift, (0.0, -60.0, 600.0))
        size0 = 215.0
        if u < 0.35:
            k = fx.ease_out_back(u / 0.35, 2.6)
            kp = fx.ease_out(u / 0.35)
        elif u < 0.35 + hold:
            k, kp = 1.0, 1.0
        else:
            k = kp = 1 - fx.ease_in((u - 0.35 - hold) / 0.35)
        x = gx + hx * kp
        y = gy + hy * kp + 10 * math.sin(u * 2.4) * kp
        size = size0 + (size1 - size0) * k
        alpha = min(1.0, u / 0.08) * (1.0 if kp > 0.15 else kp / 0.15)
        # light behind
        pulse = hit_pulse(t)
        col = (255, 210, 90) if gift == 'Neko Helmet' else (190, 200, 255)
        lg = fx.radial(256, col, power=1.8)
        fx.over(canvas, fx.warp(lg, x, y, size * (1.9 + 0.2 * pulse) / 256), alpha=0.55 * alpha * kp, add=True)
        if gift == 'Neko Helmet':
            draw_rays(canvas, x, y, size * 1.25, u, alpha * kp)
        burst(canvas, x, y, u, size)
        im = lottie.frame(str(path), u, size=int(size) // 2 * 2)
        rot = 0.06 * math.sin(u * 1.7) * kp
        fx.over(canvas, fx.warp(im, x, y, 1.0, rot_=rot), alpha=alpha)


def draw_rays(canvas, x, y, r, u, a):
    if a < 0.02:
        return
    n = 14
    rot = u * 0.35

    def fn(d, m, S):
        for k in range(n):
            th = rot + k * 2 * math.pi / n
            w = 0.09
            pts = [m(x, y), m(x + r * math.cos(th - w), y + r * math.sin(th - w)),
                   m(x + r * math.cos(th + w), y + r * math.sin(th + w))]
            d.polygon(pts, fill=(255, 220, 120, int(34 * a)))
    placed = fx.draw_rgba((x - r, y - r, x + r, y + r), fn)
    fx.over(canvas, (placed[0].filter(ImageFilter.GaussianBlur(6)),) + placed[1:], add=True)


def burst(canvas, x, y, u, size):
    if u > 0.7:
        return
    k = u / 0.7

    def fn(d, m, S):
        for i in range(16):
            th = i * 2 * math.pi / 16 + 0.3
            rr = size * (0.3 + 0.9 * fx.ease_out(k)) * (0.8 + 0.4 * ((i * 7) % 5) / 4)
            fx.sparkle(d, *m(x + rr * math.cos(th), y + rr * math.sin(th)), (14 * (1 - k) + 2) * S,
                       (255, 240, 190, int(255 * (1 - k))))
    fx.over(canvas, fx.draw_rgba((x - 2 * size, y - 2 * size, x + 2 * size, y + 2 * size), fn), add=True)



# ---------------------------------------------------------------- helmet on the head, bears, aura text
BEAR = None


def place_bears(canvas, t):
    global BEAR
    G = 2600.0
    for tt, hand, bears in E.THROWS:
        u = t - tt
        if u < 0 or u > 2.0:
            continue
        if BEAR is None:
            BEAR = str(gifts_api.original_file(E.BEAR_ID, 'json'))
        _, _, hx, hy, _, _, _ = hand_pose(tt, hand)
        for k, (vx, vy, size, spin) in enumerate(bears):
            x = hx + vx * u
            y = hy - 60 + vy * u + 0.5 * G * u * u
            if y > H + 300 or x < -300 or x > W + 300:
                continue
            sz = size * (0.55 + 0.45 * fx.ease_out(min(1.0, u / 0.18)))
            im = lottie.frame(BEAR, u + k * 0.7, size=int(sz) // 2 * 2)
            fx.over(canvas, fx.warp(im, x, y, 1.0, rot_=spin * u))


def place_aura_text(canvas, t):
    for ta, text, col in E.AURA_TEXT:
        u = t - ta
        if not (0 <= u < 1.7):
            continue
        im = fx.text_img(((text, col),), 96, 'Heavy')
        k = fx.ease_out_back(min(1.0, u / 0.25), 2.0)
        a = min(1.0, u / 0.08) * (1 - fx.smooth((u - 1.2) / 0.5))
        x, y = 540, 1280 - 110 * fx.ease_out(u / 1.7)
        glow = im.filter(ImageFilter.GaussianBlur(14))
        fx.over(canvas, fx.warp(glow, x, y, 1.08 * k, rot_=-0.06), alpha=a, add=True)
        fx.over(canvas, fx.warp(im, x, y, k, rot_=-0.06), alpha=a)



# ---------------------------------------------------------------- outcome FX: minus tags, confetti, summary
def fmt(n):
    return f'{int(round(n)):,}'.replace(',', ' ')


def place_loss_tags(canvas, t):
    for ta, text, pxy in E.LOSS_TAGS:
        u = t - ta
        if not (0 <= u < 1.9):
            continue
        x, y = zmap(*pxy, t)
        k = fx.ease_out_back(min(1.0, u / 0.22), 2.2)
        a = min(1.0, u / 0.06) * (1 - fx.smooth((u - 1.4) / 0.5))
        im = fx.text_img(((text, (255, 70, 60) if text != 'ПОЧТИ ОКУП' else (255, 150, 60)),), 56, 'Heavy')
        glow = im.filter(ImageFilter.GaussianBlur(10))
        y -= 70 * fx.ease_out(u / 1.9)
        x += 4 * math.sin(u * 40) * math.exp(-u * 6)
        fx.over(canvas, fx.warp(glow, x, y, k), alpha=a * 0.9, add=True)
        fx.over(canvas, fx.warp(im, x, y, k, rot_=-0.08), alpha=a)


CONF_COLS = [(255, 205, 60), (255, 240, 170), (255, 150, 40), (255, 255, 255), (120, 200, 255)]


def place_confetti(canvas, t):
    u = t - E.CONFETTI
    if not (0 <= u < 3.6):
        return

    def fn(d, m, S):
        for i in range(110):
            r = [((i * 7919 + k * 104729) % 1000) / 1000 for k in range(6)]
            x0 = r[0] * W
            vy = 380 + 520 * r[1]
            y = -60 - 500 * r[2] + vy * u
            x = x0 + 40 * math.sin(u * (2 + 3 * r[3]) + i)
            if y > H + 40:
                continue
            w, h = 10 + 10 * r[4], 5 + 6 * r[5]
            th = u * (3 + 6 * r[3]) + i
            c, sn = math.cos(th), math.sin(th) * (0.4 + 0.6 * abs(math.cos(u * 5 + i)))
            pts = [(x + c * dx - sn * dy, y + sn * dx + c * dy) for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
            col = CONF_COLS[i % len(CONF_COLS)]
            d.polygon([m(*p) for p in pts], fill=col + (int(235 * min(1.0, (3.6 - u) / 0.6)),))
    fx.over(canvas, fx.draw_rgba((0, 0, W, H), fn))


def counter(t, t0, value, dur=0.65):
    u = fx.clamp01((t - t0) / dur)
    return value * fx.ease_out(u)


def summary_dim(canvas, t):
    """Dim the screen card under the summary (drawn before the head, so the head stays bright)."""
    t0, t1 = E.SUMMARY_T0, E.SUMMARY_T1
    if t0 <= t < t1:
        kout = fx.ease_in(fx.clamp01((t - (t1 - 0.35)) / 0.35))
        canvas[:, :, :3] *= 1 - 0.55 * min(1.0, (t - t0) / 0.3) * (1 - kout)
        fx.over(canvas, LOGO)                             # the RubUp logo stays bright


def place_summary(canvas, t):
    t0, t1 = E.SUMMARY_T0, E.SUMMARY_T1
    if not (t0 <= t < t1):
        return
    kin = fx.ease_out_back(min(1.0, (t - t0) / 0.45), 1.3)
    kout = fx.ease_in(fx.clamp01((t - (t1 - 0.35)) / 0.35))
    pw, ph = 860, 640
    cx = 540
    cy = 700 - (1 - kin) * 900 - kout * 1100
    panel = fx.rounded(pw, ph, 40, (16, 16, 34, 238), outline=(255, 205, 80, 150), width=3)
    fx.over(canvas, fx.warp(fx.radial(256, (255, 190, 60), power=1.6), cx, cy, 1300 / 256), alpha=0.25 * (1 - kout), add=True)
    fx.over(canvas, fx.warp(panel, cx, cy, 1.0))
    top = cy - ph / 2
    title = fx.text_img((('ИТОГ ЛУДОМАНА', (255, 215, 110)),), 54, 'Heavy')
    fx.over(canvas, fx.warp(title, cx, top + 70, 1.0))
    rows = [('Потрачено · 3 кейса', '≈' + fmt(round(counter(t, E.SUMMARY_ROWS[0], E.SPENT), -2)) + ' ★', (255, 90, 80)),
            ('Получено · Neko Helmet', '≈' + fmt(round(counter(t, E.SUMMARY_ROWS[1], E.GOT), -2)) + ' ★', (255, 210, 80)),
            ('Итог', 'В ПЛЮСЕ', (110, 255, 140))]
    for k, ((label, val, col), tr) in enumerate(zip(rows, E.SUMMARY_ROWS)):
        if t < tr:
            continue
        a = min(1.0, (t - tr) / 0.12)
        y = top + 175 + k * 120 + (18 if k == 2 else 0)
        dx = 60 * (1 - fx.ease_out(min(1.0, (t - tr) / 0.25)))
        size = 60 if k == 2 else 50
        lab = fx.text_img(((label, (200, 205, 230)),), 40 if k < 2 else 48, 'Semibold' if k < 2 else 'Heavy')
        fx.over(canvas, (lab, int(cx - pw / 2 + 50 + dx) - 8, int(y - lab.height / 2)), alpha=a)
        v = fx.text_img(((val, col),), size, 'Heavy')
        fx.over(canvas, (v, int(cx + pw / 2 - 50 - v.width + dx) + 8, int(y - v.height / 2)), alpha=a)
        if k == 1:
            line_y = int(y + 62)
            canvas[line_y:line_y + 3, int(cx - pw / 2 + 50):int(cx + pw / 2 - 50), :3] = \
                canvas[line_y:line_y + 3, int(cx - pw / 2 + 50):int(cx + pw / 2 - 50), :3] * (1 - a * 0.6) + 120 * a * 0.6
    ts = E.SUMMARY_STAMP
    if t >= ts:
        u = t - ts
        k = 1 + 1.4 * math.exp(-u * 11) * (1 if u < 0.6 else 0)
        a = min(1.0, u / 0.06)
        roi = 'ОКУП ×2'
        txt = fx.text_img(((roi, (255, 215, 90)),), 74, 'Heavy')
        st = fx.rounded(txt.width + 50, txt.height + 26, 22, None, outline=(255, 215, 90, 255), width=7)
        st.alpha_composite(txt, ((st.width - txt.width) // 2, (st.height - txt.height) // 2))
        fx.over(canvas, fx.warp(st.filter(ImageFilter.GaussianBlur(12)), cx + 150, top + ph - 70, k), alpha=a * 0.8,
                add=True)
        fx.over(canvas, fx.warp(st, cx + 150, top + ph - 70, k, rot_=-0.16), alpha=a)


# ---------------------------------------------------------------- aura post: zoom punch, RGB split, vignette, grain
_POST = {}


def post(out, t):
    pulse = hit_pulse(t)
    z = 1 + 0.016 * pulse
    big = 0.0
    for tf in (E.HOOK_HIDE, DROP1, E.LOSE, DROP2, 21.40, E.SUMMARY_STAMP):
        if 0 <= t - tf < 0.5:
            big = max(big, math.exp(-(t - tf) * 7))
    z += 0.035 * big
    if z > 1.0005:
        cw, ch = W / z, H / z
        x0, y0 = (W - cw) / 2, (H - ch) / 2 + (ch - H) * -0.0
        out = np.asarray(Image.fromarray(out).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)))
    d = int(round(9 * big))
    out = out.astype(np.float32)
    if d:
        out[:, :, 0] = np.roll(out[:, :, 0], d, 1)
        out[:, :, 2] = np.roll(out[:, :, 2], -d, 1)
    if 'vig' not in _POST:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
        _POST['vig'] = (1 - 0.38 * np.clip(r - 0.55, 0, 1) ** 1.4)[..., None].astype(np.float32)
        rng = np.random.default_rng(43)
        _POST['grain'] = rng.normal(0, 5.5, (4, H // 2, W // 2)).astype(np.float32)
    g = _POST['grain'][int(t * 24) % 4]
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    out = out * _POST['vig'] + g
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- background and flashes
_BG = None


def background():
    global _BG
    if _BG is None:
        yy = np.linspace(0, 1, H)[:, None, None]
        top, bot = np.array([10, 11, 28], np.float32), np.array([4, 4, 12], np.float32)
        _BG = np.broadcast_to(top + (bot - top) * yy, (H, W, 3)).astype(np.float32)
    return _BG.copy()


def flashes(canvas, t):
    for tf, col, dur, peak in ((E.HOOK_HIDE, (255, 230, 160), 0.35, 0.75), (E.HOOK_END, (255, 255, 255), 0.18, 0.5),
                               (DROP1, (120, 150, 255), 0.25, 0.25), (E.LOSE, (255, 30, 20), 0.5, 0.35),
                               (10.20, (255, 40, 30), 0.35, 0.18), (15.30, (255, 40, 30), 0.35, 0.2),
                               (21.40, (255, 30, 20), 0.4, 0.26), (E.SUMMARY_STAMP, (255, 220, 120), 0.3, 0.35),
                               (DROP2, (255, 210, 80), 0.6, 0.8)):
        u = (t - tf) / dur
        if 0 <= u < 1:
            a = peak * (1 - u) ** 2
            canvas[..., :3] = canvas[..., :3] * (1 - a) + np.array(col, np.float32) * a


def shake(t):
    for tf, amp in ((DROP1, 10), (E.LOSE, 16), (DROP2, 18), (E.HOOK_HIDE, 12), (21.40, 9), (E.SUMMARY_STAMP, 12)):
        u = t - tf
        if 0 <= u < 0.4:
            k = amp * math.exp(-u * 9)
            return int(k * math.sin(u * 90)), int(k * math.cos(u * 70))
    return 0, 0


def render_at(t):
    canvas = background()
    tint = tuple(int(v) // 16 * 16 for v in fire_params(t)[0][1])
    place_card(canvas, t, tint)
    hxp, hdy, hsc = head_move(t)                          # aura light from the eyes spills onto the screen
    fx.over(canvas, fx.warp(fx.radial(256, tint, power=1.8), hxp, 1640 + hdy, 1100 * hsc / 256),
            alpha=0.22 + 0.14 * hit_pulse(t), add=True)
    summary_dim(canvas, t)
    press_ripple(canvas, t)
    place_hand(canvas, t, 'L')
    eyes, s, pose = place_head(canvas, t)
    draw_fire(canvas, eyes, s / 0.7, t)
    place_hand(canvas, t, 'R')
    place_pops(canvas, t)
    place_loss_tags(canvas, t)
    place_confetti(canvas, t)
    place_summary(canvas, t)
    place_bears(canvas, t)
    place_aura_text(canvas, t)
    flashes(canvas, t)
    dx, dy = shake(t)
    out = post(np.clip(canvas, 0, 255).astype(np.uint8), t)
    if dx or dy:
        out = np.roll(out, (dy, dx), (0, 1))
    return out


def frame_bytes(i):
    return render_at(i / FPS).tobytes()


if __name__ == '__main__':
    if '--video' in sys.argv and not config.STYLE_READY:
        raise SystemExit('Define your own visual concept in STORYBOARD.md/config.py before building')
    frames.cli(render_at, frame_bytes, W, H, FPS, int(round(DUR * FPS)))
