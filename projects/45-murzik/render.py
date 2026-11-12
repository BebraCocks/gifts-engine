"""45-murzik: the white marble head (the gambler from 43/44) and his NFT cat Мурзик (Scared Cat · Purrlion) over the
RubUp screen recording. The cat sits on the palms, bolts, comes back out of the upgrade window. Everything on the beat.
Frame = f(video time). No RubUp ad break: the RubUp logo stays on screen (author, as in 43/44)."""
import math
import subprocess
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
import script
import timeline as TL
from timeline import DUR, HITS, BEAT, src_at, src_speed

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BUILD = paths.build(HERE)
SRC = BUILD / 'src'
A = HERE / 'assets'


def rgba(name):
    return Image.open(A / f'{name}.png').convert('RGBA')


# ---------------------------------------------------------------- character
CH = {
    'W': dict(head=np.asarray(rgba('head'), np.float32), anchor=(378.0, 800.0), base=0.70,
              lip=(625.0, 405.0, 66.0, 175.0), jaw=15.0, eyes=np.array([(307.0, 410.0), (515.0, 417.0)]),
              hand_off=330.0, hand_y=1760.0, hand_s=0.60),
}
HANDS = {('open', 'L'): rgba('hand_l'), ('open', 'R'): rgba('hand_r'), ('point', 'R'): rgba('hand_point'),
         ('fist', 'L'): rgba('fist_l'), ('fist', 'R'): rgba('fist_r')}
PT_TIP = (15.0, 23.0)                     # index fingertip in hand_point.png
PT_ROT = -0.45                            # pointing hand drawn tilted so the finger goes up-left


def src_frame(s):
    k = int(round(s * 60))
    for d in (0, 1, -1, 2, -2, 3, -3, 4, -4):
        p = SRC / f'{k + d:06d}.jpg'
        if p.exists():
            return Image.open(p).convert('RGB')
    raise FileNotFoundError(f'no source frame near {s:.2f} s')


def _logo():
    """Crisp RubUp logo cut from a full recording frame (the crop starts below it), alpha from the header colour."""
    f = BUILD / 'logo.png'
    if not f.exists():
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', '6', '-i', str(HERE / 'input' / 'rubup_screen.mp4'),
                        '-frames:v', '1', '-vf', 'crop=150:96:12:200,scale=225:144:flags=lanczos', str(f)], check=True)
    reg = np.asarray(Image.open(f).convert('RGB'), np.float32)
    bg = np.median(np.concatenate([reg[:4].reshape(-1, 3), reg[-4:].reshape(-1, 3)]), 0)
    a = np.clip(np.abs(reg - bg).max(2) / 110.0, 0, 1)
    rgb = bg + (reg - bg) / np.maximum(a[..., None], 1e-3)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA'), 14, 6


LOGO = _logo()


# ---------------------------------------------------------------- voice envelope (mouth)
def _env():
    f = BUILD / 'voice_env.npy'
    if f.exists():
        return np.load(f)
    import voice_review as V
    sr = V.SR
    v = V.voice_track(int(DUR * sr) + sr, quiet=True)
    hop = sr // FPS
    e = np.array([np.sqrt((v[k:k + hop] ** 2).mean()) for k in range(0, len(v) - hop, hop)])
    e = e / (np.percentile(e[e > 1e-4], 95) + 1e-9)
    out, prev = np.zeros_like(e), 0.0
    for k, x in enumerate(np.clip(e, 0, 1.2)):
        prev = prev + (x - prev) * (0.55 if x > prev else 0.22)
        out[k] = prev
    np.save(f, out)
    return out


ENV = _env()


def talk(t):
    k = int(t * FPS)
    return float(ENV[k]) if 0 <= k < len(ENV) else 0.0


# ---------------------------------------------------------------- eye fire (white head only)
FIRE = {   # core, mid, outer, height, width, intensity, turbulence, size
    'calm':    ((215, 235, 255), (60, 120, 255), (20, 30, 160), 120, 34, 0.90, 0.6, 16),
    'tense':   ((255, 225, 255), (175, 60, 255), (70, 0, 150), 165, 38, 1.05, 0.9, 17),
    'annoyed': ((255, 240, 200), (255, 140, 30), (170, 45, 0), 160, 38, 1.05, 1.0, 17),
    'angry':   ((255, 220, 180), (255, 70, 20), (150, 10, 0), 215, 44, 1.20, 1.4, 19),
    'rage':    ((255, 240, 220), (255, 30, 10), (130, 0, 0), 300, 52, 1.45, 1.9, 23),
    'cocky':   ((220, 255, 255), (40, 200, 255), (0, 60, 170), 165, 36, 1.00, 0.8, 17),
    'love':    ((255, 230, 245), (255, 90, 190), (170, 20, 110), 175, 40, 1.10, 0.9, 18),
    'evil':    ((255, 190, 160), (190, 0, 30), (50, 0, 30), 250, 46, 1.30, 1.5, 20),
    'joy':     ((255, 255, 230), (255, 200, 40), (255, 90, 0), 340, 58, 1.55, 1.3, 25),
    # pink statue: smaller fire, her own colours (author 2026-11-12)
    'p_pout':    ((255, 235, 250), (255, 80, 190), (160, 0, 110), 105, 24, 0.95, 0.7, 11),
    'p_puzzled': ((225, 255, 250), (60, 235, 205), (0, 110, 120), 95, 22, 0.90, 0.5, 10),
    'p_angry':   ((255, 240, 210), (255, 45, 140), (130, 0, 70), 165, 30, 1.20, 1.5, 13),
}


def fire_params(t, emo=None):
    emo = emo or E.EMO
    prev, cur, t_cur = None, emo[0][1], emo[0][0]
    for tk, st in emo:
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


def emotion_at(t):
    return fire_params(t)[1]


def emo_start(t):
    return max((tk for tk, _ in E.EMO if tk <= t), default=0.0)


def hit_pulse(t):
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


def draw_fire(canvas, eyes_xy, scale, t, emo=None, seed=0):
    p, state = fire_params(t, emo)
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
    if x1 <= x0 or y1 <= y0:
        return
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

    for k, (ex, ey) in enumerate(eyes_xy):
        splat(ex, ey, 26 * scale, mid, 0.45 * inten)
        splat(ex, ey, 9 * scale, core, 0.9 * inten)
        i0, i1 = int((t - 1.0) * RATE), int(t * RATE)
        idx = np.arange(i0, i1 + 1)
        k = k + seed
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
            if r4 > 0.93:
                splat(px + (r2 - 0.5) * w * a, py - h * 0.5 * a, 3 * scale + 1, core, 0.9 * inten * (1 - a))
                continue
            splat(px, py, rad * (0.55 + 0.45 * a), col, 0.5 * inten * (1 - a) ** 0.9)
    light = 1 - np.exp(-acc * 2.2)
    al = np.clip(light.max(2, keepdims=True) * 1.15, 0, 1)
    col = light / np.maximum(al, 1e-3)
    reg = canvas[y0:y1, x0:x1, :3]
    reg[:] = reg * (1 - al) + col * 255 * al
    reg[:] = np.minimum(255, reg + light * 60)


# ---------------------------------------------------------------- heads with a jaw
_JAW = {}


def head_image(who, open_px):
    c = CH[who]
    HEAD = c['head']
    LIP_Y, MOUTH_X, MOUTH_HW, JAW_HW = c['lip']
    q = round(open_px * 2) / 2
    if q < 0.25:
        return Image.fromarray(HEAD.astype(np.uint8), 'RGBA')
    key = (who, q)
    if key in _JAW:
        return _JAW[key]
    hh, ww = HEAD.shape[:2]
    ry0, ry1, rx0, rx1 = int(LIP_Y - 40), hh, int(MOUTH_X - JAW_HW - 5), int(MOUTH_X + JAW_HW + 5)
    yy, xx = np.mgrid[ry0:ry1, rx0:rx1].astype(np.float32)
    dx = np.abs(xx - MOUTH_X)
    gx = np.where(dx < 70, 1.0, np.clip(np.cos(np.clip((dx - 70) / (JAW_HW - 70), 0, 1) * math.pi / 2), 0, 1) ** 1.5)
    inner = np.clip((MOUTH_HW * 1.05 - dx) / (MOUTH_HW * 0.35), 0, 1)
    hard = (yy >= LIP_Y).astype(np.float32)
    soft = np.clip((yy - (LIP_Y - 30)) / 70, 0, 1)
    soft = soft * soft * (3 - 2 * soft)
    tail = np.clip((hh - yy) / 60, 0.35, 1)
    D = q * gx * (inner * hard + (1 - inner) * soft) * tail
    sy = yy - D
    out = HEAD.copy()
    reg = np.stack([nd.map_coordinates(HEAD[..., k], [sy, xx], order=1, mode='nearest') for k in range(4)], -1)
    open_col = q * gx * inner
    cav = inner * np.clip((LIP_Y - sy) / 1.5, 0, 1) * hard
    depth = np.clip((yy - LIP_Y) / np.maximum(open_col, 1), 0, 1)
    cav_rgb = np.stack([28 + 30 * (1 - depth), 14 + 12 * (1 - depth), 18 + 12 * (1 - depth)], -1)
    reg[..., :3] = reg[..., :3] * (1 - cav[..., None]) + cav_rgb * cav[..., None]
    reg[..., 3] = np.maximum(reg[..., 3], 255 * cav)
    out[ry0:ry1, rx0:rx1] = reg
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA')
    if len(_JAW) > 96:
        _JAW.clear()
    _JAW[key] = im
    return im


FIRE.update({
    'sad':   ((200, 215, 235), (110, 140, 190), (40, 60, 110), 80, 26, 0.70, 0.4, 13),
    'shock': ((255, 255, 255), (170, 220, 255), (60, 120, 255), 300, 50, 1.40, 1.8, 22),
})


# ---------------------------------------------------------------- head
def head_move(t):
    K = E.W_KEYS
    if t <= K[0][0]:
        return K[0][1:]
    for (t0, *a), (t1, *b) in zip(K, K[1:]):
        if t0 <= t < t1:
            u = fx.smooth((t - t0) / (t1 - t0))
            return tuple(p + (q - p) * u for p, q in zip(a, b))
    return K[-1][1:]


def spinning(t):
    """A case reel or the upgrade wheel is running (fists, tension)."""
    return any(a + 0.3 < t < b for a, b in TL.SPINS) or TL.WHEEL[0] + 0.3 < t < TL.WHEEL[1]


def head_pose(t):
    """-> (anchor x, anchor y, scale, rotation rad)"""
    c = CH['W']
    tk = talk(t)
    pulse = hit_pulse(t)
    hx, mdy, mds = head_move(t)
    vx = (head_move(t + 0.04)[0] - head_move(t - 0.04)[0]) / 0.08
    s = c['base'] * mds * (1 + 0.02 * pulse + 0.01 * tk) * (1 + 0.00003 * abs(vx))
    x, y = hx, 1915.0 + mdy - 0.03 * abs(vx)
    rot = 0.03 * math.sin(t * 1.3) + 0.02 * tk * math.sin(t * 7.0) - 0.00018 * vx
    y += 4 * math.sin(t * 2.1) - 8 * pulse
    st = emotion_at(t)
    if st in ('rage', 'angry'):
        amp = 1.0 if st == 'rage' else 0.45
        x += amp * 7 * math.sin(t * 61) + amp * 4 * math.sin(t * 37)
        rot += amp * 0.035 * math.sin(t * 47)
    if st == 'love':                                   # looks at the cat on the palms (to the right)
        k = fx.smooth((t - emo_start(t)) / 0.4) if t > 1 else 1.0
        rot += k * (0.07 + 0.03 * math.sin(t * 2.4))
    if st == 'sad':                                    # droops
        k = fx.smooth((t - emo_start(t)) / 0.5)
        rot += -0.10 * k
        y += 26 * k
    if st == 'shock':                                  # jolts back, then stares after the cat
        u = t - TL.SCARE
        k = math.exp(-u * 5) * math.cos(u * 16)
        rot += -0.12 * k + 0.06 * fx.smooth(u / 0.5)
        y -= 30 * abs(k)
        x += 4 * math.sin(t * 55) * math.exp(-u * 2)
    if st == 'tense':
        x += 2.5 * math.sin(t * 53)
    if st == 'joy':                                    # bounces on the beat
        b = (t - TL.BEAT0) / BEAT
        k = fx.smooth((t - emo_start(t)) / 0.25)
        y -= k * 26 * abs(math.sin(math.pi * b))
        rot += k * 0.06 * math.sin(math.pi * b)
    return x, y, s, rot


def head_point(pose, px, py):
    """head-image pixel -> frame point for a head pose"""
    x, y, s, rot = pose
    ax, ay = CH['W']['anchor']
    c, sn = math.cos(rot), math.sin(rot)
    return x + s * (c * (px - ax) - sn * (py - ay)), y + s * (sn * (px - ax) + c * (py - ay))


def place_head(canvas, t):
    pose = head_pose(t)
    x, y, s, rot = pose
    opening = CH['W']['jaw'] * min(1.0, talk(t) ** 0.8)
    fx.over(canvas, fx.warp(head_image('W', opening), x, y, s, rot_=rot, anchor=CH['W']['anchor']))
    return [head_point(pose, ex, ey) for ex, ey in CH['W']['eyes']], pose


# ---------------------------------------------------------------- hands: shape by action
def rest(side, t):
    c = CH['W']
    hx, hdy, hsc = head_move(t)
    ph = 0.0 if side == 'L' else 1.3
    x = hx + (-1 if side == 'L' else 1) * c['hand_off'] * hsc + 5 * math.sin(t * 1.1 + ph)
    y = c['hand_y'] + hdy + 9 * math.sin(t * 1.9 + ph) - 10 * hit_pulse(t)
    return x, y, 0.0, c['hand_s'] * hsc


def lift(side, t):
    x, y, r, s = rest(side, t)
    hsc = head_move(t)[2]
    return x + (60 if side == 'L' else -60) * hsc, y - 150 * hsc, (0.08 if side == 'L' else -0.08), s * 1.02


def cheer(side, t):
    x, y, r, s = rest(side, t)
    b = (t - TL.BEAT0) / BEAT + (0.0 if side == 'L' else 1.0)
    up = math.sin(math.pi * b)
    return (x + (-40 if side == 'L' else 40), y - 230 - 70 * up, (0.3 if side == 'L' else -0.3) * (1 + 0.5 * up), s)


def hold_xy(t):
    """Where the two palms meet: the cat's seat. Breathes; dips when the cat lands."""
    x, y = E.HOLD
    y += 6 * math.sin(t * 2.0) - 6 * hit_pulse(t)
    u = t - TL.LAND
    if 0 <= u < 0.8:
        y += 34 * math.exp(-u * 7) * math.cos(u * 15)
    u = t - TL.SCARE
    if 0 <= u < 0.6:                                   # the hop kicks the palms down
        y += 22 * math.exp(-u * 8) * math.cos(u * 18)
    return x, y


def hold(side, t):
    x, y = hold_xy(t)
    return x + (-112 if side == 'L' else 112), y + 30, (0.10 if side == 'L' else -0.10), CH['W']['hand_s'] * 0.92


def C(x, y, r=0.0, sm=1.0):
    return ('c', x, y, r, sm)


def T(x, y, r=0.0, sm=1.0):
    return ('tip', x, y, r, sm)


LIFT, CHEER, HOLD = ('lift',), ('cheer',), ('hold',)


def _press(tp, pt, back):
    """Pointing finger: comes in, taps pt exactly at tp, pulls back."""
    return [(tp - 0.32, 'open', None), (tp - 0.16, 'point', T(pt[0] + 90, pt[1] + 150)), (tp, 'point', T(*pt)),
            (tp + 0.20, 'point', T(*back))]


def _spin(tp, t1):
    return [(tp + 0.38, 'fist', LIFT), (t1 - 0.12, 'fist', LIFT), (t1 + 0.12, 'open', None)]


# (time, pose, target): the hand glides between targets (ease-in-out); the pose changes at the waypoint time.
# None = rest beside the head; C(...) = hand centre; T(...) = fingertip of the pointing hand (follows the screen zoom).
PATHS = {
    'R': [
        (0.00, 'open', HOLD), (TL.SCARE + 0.45, 'open', HOLD), (2.70, 'open', C(985, 1330, -0.35)),   # reaches after him
        (3.75, 'open', C(990, 1350, -0.30)),
        (4.10, 'point', T(520, 900)), (TL.TAP_TILE, 'point', T(*E.TILE)), (TL.TAP_TILE + 0.22, 'point', T(640, 1330)),
        *_press(TL.PRESS[0], E.OPEN_BTN, (610, 1290))[1:], *_spin(TL.PRESS[0], TL.POP[0] - 0.1),
        *_press(TL.PRESS[1], E.OPEN_BTN, (610, 1290)), *_spin(TL.PRESS[1], TL.POP[1] - 0.1),
        *_press(TL.PRESS[2], E.OPEN_BTN, (610, 1290)), *_spin(TL.PRESS[2], TL.POP[2] - 0.1),
        *_press(TL.TAP_WANT, E.WANT, (930, 1330)),
        (TL.TYPE[0] - 0.05, 'point', T(600, 560)), (TL.TYPE[-1] + 0.1, 'point', T(620, 560)),          # follows the typing
        (TL.RESULTS + 0.25, 'point', T(940, 1250)), (TL.TAP_CAT - 0.18, 'point', T(930, 1080)),
        (TL.TAP_CAT, 'point', T(*E.CAT_CARD)), (TL.TAP_CAT + 0.22, 'point', T(930, 1560)),
        *_press(TL.PRESS_UP, E.UP_BTN, (900, 1640))[1:], *_spin(TL.PRESS_UP, TL.WIN - 0.05),
        (TL.WIN + 0.2, 'open', CHEER), (TL.JUMP - 0.10, 'open', CHEER), (TL.JUMP + 0.34, 'open', HOLD),
    ],
    'L': [
        (0.00, 'open', HOLD), (TL.SCARE + 0.45, 'open', HOLD), (2.70, 'open', None),
        *_spin(TL.PRESS[0], TL.POP[0] - 0.1), *_spin(TL.PRESS[1], TL.POP[1] - 0.1), *_spin(TL.PRESS[2], TL.POP[2] - 0.1),
        *_spin(TL.PRESS_UP, TL.WIN - 0.05),
        (TL.WIN + 0.2, 'open', CHEER), (TL.JUMP - 0.10, 'open', CHEER), (TL.JUMP + 0.34, 'open', HOLD),
    ],
}


def resolve(target, side, t):
    """target -> hand-centre frame position (x, y, rot, scale)"""
    if target is None:
        return rest(side, t)
    if target == LIFT:
        return lift(side, t)
    if target == CHEER:
        return cheer(side, t)
    if target == HOLD:
        return hold(side, t)
    kind, x, y, r, sm = target
    s = CH['W']['hand_s'] * head_move(t)[2] * sm
    if kind == 'tip':                                  # fingertip -> centre of the pointing hand
        x, y = zmap(x, y, t)
        img = HANDS[('point', 'R')]
        rr = r + PT_ROT
        dx, dy = (img.width / 2 - PT_TIP[0]) * s, (img.height / 2 - PT_TIP[1]) * s
        c, sn = math.cos(rr), math.sin(rr)
        return x + c * dx - sn * dy, y + sn * dx + c * dy, r, s
    return x, y, r, s


def hand_state(side, t):
    """-> pose, previous pose, pose blend 0..1, (x, y, rot, scale) of the hand centre"""
    P = PATHS[side]
    i = 0
    while i + 1 < len(P) and P[i + 1][0] <= t:
        i += 1
    t0, pose, a = P[i]
    prev = P[i - 1][1] if i > 0 else pose
    blend = fx.smooth(min(1.0, (t - t0) / 0.10)) if prev != pose else 1.0
    pa = resolve(a, side, t)
    if i + 1 < len(P) and t >= t0:
        t1, pose1, b = P[i + 1]
        pb = resolve(b, side, t)
        u = fx.smooth((t - t0) / (t1 - t0))
        st = tuple(p + (q - p) * u for p, q in zip(pa, pb))
    else:
        st = pa
    x, y, r, s = st
    em = emotion_at(t)
    ph = 0 if side == 'L' else 1.3
    if em in ('rage', 'angry'):
        y += 10 * math.sin(t * 43 + ph)
        r += 0.06 * math.sin(t * 29 + ph)
    if em == 'sad' and a is None:
        y += 30 * fx.smooth((t - emo_start(t)) / 0.5)
    if em == 'shock' and t > E.RUN + 0.3 and side == 'R':
        y += 8 * math.sin(t * 31)
    if pose == 'fist' and spinning(t):                 # clenched and trembling while it spins
        x += 3 * math.sin(t * 53 + ph)
        y += 4 * math.sin(t * 47)
    return pose, prev, blend, (x, y, r, s)


def draw_hand_img(canvas, pose, side, st, alpha=1.0, squash=1.0):
    x, y, r, s = st
    img = HANDS.get((pose, side), HANDS[('open', side)])
    rr = r + (PT_ROT if pose == 'point' else 0.0)
    fx.over(canvas, fx.warp(img, x, y, s * squash, rot_=rr), alpha=alpha)


def place_hand(canvas, side, t):
    pose, prev, blend, st = hand_state(side, t)
    if blend < 1.0:                                    # quick morph: the old shape shrinks out, the new pops in
        draw_hand_img(canvas, prev, side, st, alpha=1 - blend, squash=1 - 0.12 * blend)
        draw_hand_img(canvas, pose, side, st, alpha=blend, squash=0.9 + 0.1 * blend)
    else:
        draw_hand_img(canvas, pose, side, st)


# ---------------------------------------------------------------- the cat
CAT_SIZE = 420
_CAT = {}


def cat_frame(lt, size, flip=False):
    """Purrlion's Lottie. Only the cat-only part of the cycle is used (0–0.55 s: arched <-> relaxed);
    the rest of the cycle is a ball catching the cat — not for a pet on the palms."""
    if 'p' not in _CAT:
        _CAT['p'] = str(gifts_api.model_file(E.GIFT, E.MODEL, 'json'))
    im = lottie.frame(_CAT['p'], min(0.55, max(0.0, lt)), size=int(size) // 2 * 2)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def cat_seat(t):
    x, y = hold_xy(t)
    return x, y - 40


def win_xy(t):
    return zmap(*E.WIN_GIFT, t)


def draw_cat(canvas, t):
    if t < TL.SCARE:                                   # a living cat on the palms: breathes, looks around
        x, y = cat_seat(t)
        lt = 0.44 + 0.09 * math.sin(t * 2.6)
        br = 1 + 0.025 * math.sin(t * 5.0)
        fx.over(canvas, fx.warp(cat_frame(lt, CAT_SIZE), x + 1.5 * math.sin(t * 150), y, 1.0, br, rot_=0.03 * math.sin(t * 1.7),
                                anchor=(CAT_SIZE / 2, CAT_SIZE * 0.9)), alpha=1.0)
        return
    if t < E.RUN:                                     # startled: arches, hops straight up
        u = (t - TL.SCARE) / (E.RUN - TL.SCARE)
        x, y = cat_seat(t)
        lt = 0.44 * (1 - fx.ease_out(min(1.0, u / 0.35)))
        k = 1 + 0.22 * math.sin(math.pi * min(1.0, u * 1.2))
        fx.over(canvas, fx.warp(cat_frame(lt, CAT_SIZE * 1.25), x + 6 * math.sin(t * 90), y - 210 * math.sin(math.pi * u * 0.62), k,
                                rot_=-0.12 * u, anchor=(CAT_SIZE * 0.625, CAT_SIZE * 1.125)))
        return
    if t < E.RUN + 0.55:                              # bolts to the right, out of the frame
        u = t - E.RUN
        x0, y0 = cat_seat(E.RUN)
        y0 -= 210 * math.sin(math.pi * 0.62)
        x = x0 + 2900 * u * u + 300 * u
        y = y0 + 500 * u * u - 60 * u
        for k in range(5, 0, -1):                      # ghost trail
            uu = max(0.0, u - 0.022 * k)
            fx.over(canvas, fx.warp(cat_frame(0.0, CAT_SIZE, True), x0 + 2900 * uu * uu + 300 * uu, y0 + 500 * uu * uu - 60 * uu,
                                    1.25, 0.9, rot_=0.25), alpha=0.16 * (1 - k / 6))
        fx.over(canvas, fx.warp(cat_frame(0.0, CAT_SIZE, True), x, y, 1.3, 0.88, rot_=0.25 + 0.1 * math.sin(t * 60)))
        return
    if TL.JUMP <= t < TL.LAND:                         # out of the «Улучшено» window, an arc onto the palms
        u = (t - TL.JUMP) / (TL.LAND - TL.JUMP)
        x0, y0 = win_xy(t)
        x1, y1 = cat_seat(TL.LAND)
        y1 -= CAT_SIZE * 0.45
        ue = fx.smooth(u)
        x = x0 + (x1 - x0) * ue
        y = y0 + (y1 - y0) * u * u - 330 * math.sin(math.pi * u) * (1 - 0.3 * u)
        sz = 300 + (CAT_SIZE - 300) * ue
        a = min(1.0, u / 0.12)
        for k in range(4, 0, -1):
            uu = max(0.0, u - 0.03 * k)
            ee = fx.smooth(uu)
            fx.over(canvas, fx.warp(cat_frame(0.3, sz), x0 + (x1 - x0) * ee, y0 + (y1 - y0) * uu * uu - 330 * math.sin(math.pi * uu) * (1 - 0.3 * uu),
                                    1.0, rot_=-6.283 * ee), alpha=0.14 * a * (1 - k / 5))
        fx.over(canvas, fx.warp(cat_frame(0.3, sz), x, y, 1.0, rot_=-6.283 * ue), alpha=a)   # one full flip in the air
        return
    if t >= TL.LAND:                                   # home: squashes on landing, settles, purrs
        u = t - TL.LAND
        x, y = cat_seat(t)
        sq = 0.22 * math.exp(-u * 7) * math.cos(u * 15)
        lt = 0.10 + 0.34 * fx.smooth(u / 0.8) + 0.07 * math.sin(t * 2.6)
        br = 1 + 0.03 * math.sin(t * 5.0)
        fx.over(canvas, fx.warp(cat_frame(lt, CAT_SIZE), x + 2.0 * math.sin(t * 157), y, 1 + sq, (1 - sq) * br,
                                rot_=0.03 * math.sin(t * 1.7), anchor=(CAT_SIZE / 2, CAT_SIZE * 0.9)))


# ---------------------------------------------------------------- pumpkins out of «Ваш подарок»
_PUMP = {}


def draw_pumpkins(canvas, t):
    for k, (gift, model) in enumerate(E.PUMPKINS):
        t0, t1 = TL.POP[k] + 0.10, E.POP_END[k]
        if not (t0 <= t < t1 + 0.1):
            continue
        if k not in _PUMP:
            _PUMP[k] = str(gifts_api.model_file(gift, model, 'json'))
        u = t - t0
        x, y = zmap(*E.POPUP_GIFT, t)
        _, _, z = view(t)
        a = min(1.0, u / 0.08) * (1 - fx.smooth((t - t1) / 0.1))
        col = (255, 150, 60) if k == 0 else (255, 90, 70)
        fx.over(canvas, fx.warp(fx.radial(256, col, power=1.7), x, y, 820 * z / 256), alpha=0.45 * a, add=True)
        draw_rays(canvas, x, y, 500 * z, u, 0.7 * a, col)
        kk = fx.ease_out_back(min(1.0, u / 0.3), 2.2)
        sz = 500 * z * (0.6 + 0.4 * kk)
        fx.over(canvas, fx.warp(lottie.frame(_PUMP[k], u, size=int(sz) // 2 * 2), x, y + 8 * math.sin(u * 3.2), 1.0,
                                rot_=0.05 * math.sin(u * 2.1)), alpha=a)


# ---------------------------------------------------------------- screen
HEADER = 105                        # frame rows of the RubUp header kept in the crop (balance painted over)
_SHEET = {}


def sheet_image(t):
    """«Хочу получить» without the keyboard (author): the sheet at its lower position, the focused search field from the
    results frame, «Мурзик» typed letter by letter instead of «Scared», then the found cats; below them — empty sheet."""
    if not _SHEET:
        a = np.asarray(src_frame(42.9)).copy()
        b = np.asarray(src_frame(48.5))
        dy = E.SHEET_DY
        a[325 + dy:465 + dy] = b[325:465]
        a[352 + dy:434 + dy, 138:345] = b[395, 600]                    # «Scared» out
        r = a.copy()
        r[465 + dy:1066 + dy] = b[465:1066]
        r[1066 + dy:] = b[1066, 540]
        _SHEET['type'], _SHEET['res'] = a, r
        _SHEET['font'] = fx.font('Medium', 50)
    k = sum(1 for tt in TL.TYPE if t >= tt)
    u = fx.clamp01((t - TL.RESULTS) / 0.12)
    base = _SHEET['type'] if u <= 0 else (_SHEET['res'] if u >= 1 else
                                         (_SHEET['type'] * (1 - u) + _SHEET['res'] * u).astype(np.uint8))
    im = Image.fromarray(base)
    d = ImageDraw.Draw(im)
    txt = E.WORD[:k]
    y = 394 + E.SHEET_DY
    d.text((150, y), txt, font=_SHEET['font'], fill=(255, 255, 255), anchor='lm')
    if int(t * 2.2) % 2 == 0 or (k and t - TL.TYPE[k - 1] < 0.3):       # caret
        cx = 152 + _SHEET['font'].getlength(txt)
        d.rectangle([cx, y - 30, cx + 3, y + 30], fill=(255, 255, 255))
    return np.asarray(im).copy()


def card_image(t):
    if E.SHEET0 <= t < TL.TAP_CAT:
        a = sheet_image(t)
    else:
        st = src_at(t)
        a = np.asarray(src_frame(st)).copy()
        sp = src_speed(t)
        if sp > 1.5:                                   # sped-up reel / wheel: blend source frames = motion blur
            n = min(5, int(math.ceil(sp)) + 1)
            y0, y1 = (520, 1050) if t < TL.TO_UP else (300, 860)
            acc = a[y0:y1].astype(np.float32)
            for j in range(1, n):
                acc += np.asarray(src_frame(st - sp / 60 * j / n))[y0:y1]
            a[y0:y1] = (acc / n).astype(np.uint8)
    a[0:HEADER] = a[0:HEADER, 540:541]                 # the star balance (and the half-cut logo) vanish
    return Image.fromarray(a)


def view(t):
    for t0, t1, (fxc, fyc), z0, z1 in E.ZOOMS:
        if t0 - 0.001 <= t < t1:
            u = (t - t0) / (t1 - t0)
            zin = fx.ease_out(min(1.0, (t - t0) / 0.3))
            return fxc, fyc, 1 + ((z0 + (z1 - z0) * fx.smooth(u)) - 1) * zin
    return E.CARD_W / 2, E.CARD_H / 2, 1.0


def zmap(x, y, t):
    fxc, fyc, z = view(t)
    return fxc + (x - fxc) * z, fyc + (y - fyc) * z


def zoomed(im, t):
    fxc, fyc, z = view(t)
    if z <= 1.0005:
        return im
    box = (fxc - fxc / z, fyc - fyc / z, fxc + (E.CARD_W - fxc) / z, fyc + (E.CARD_H - fyc) / z)
    out = im.resize((E.CARD_W, E.CARD_H), Image.BICUBIC, box=box)
    out.paste(im.crop((0, 0, E.CARD_W, HEADER)), (0, 0))
    sh = Image.new('RGBA', (E.CARD_W, 24), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([0, 0, E.CARD_W, 24], fill=(0, 0, 0, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(6)).crop((0, 12, E.CARD_W, 24))
    out = out.convert('RGBA')
    out.alpha_composite(sh, (0, HEADER))
    return out.convert('RGB')


def place_card(canvas, t):
    im = zoomed(card_image(t), t)
    zoom = 1.0 + 0.006 * hit_pulse(t)
    if zoom > 1.0005:
        cw, ch = W / zoom, H / zoom
        im = im.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    canvas[:, :, :3] = np.asarray(im, np.float32)


# ---------------------------------------------------------------- FX
def draw_rays(canvas, x, y, r, u, a, col):
    if a < 0.02:
        return
    n = 16

    def fn(d, m, S):
        for k in range(n):
            th = u * 0.5 + k * 2 * math.pi / n
            w = 0.085
            d.polygon([m(x, y), m(x + r * math.cos(th - w), y + r * math.sin(th - w)),
                       m(x + r * math.cos(th + w), y + r * math.sin(th + w))], fill=col + (int(46 * a),))
    placed = fx.draw_rgba((x - r, y - r, x + r, y + r), fn)
    fx.over(canvas, (placed[0].filter(ImageFilter.GaussianBlur(7)),) + placed[1:], add=True)
def burst(canvas, x, y, u, size, col=(255, 240, 190), n=16, dur=0.7):
    if not 0 <= u < dur:
        return
    k = u / dur

    def fn(d, m, S):
        for i in range(n):
            th = i * 2 * math.pi / n + 0.3
            rr = size * (0.3 + 0.9 * fx.ease_out(k)) * (0.8 + 0.4 * ((i * 7) % 5) / 4)
            fx.sparkle(d, *m(x + rr * math.cos(th), y + rr * math.sin(th)), (16 * (1 - k) + 2) * S, col + (int(255 * (1 - k)),))
    fx.over(canvas, fx.draw_rgba((x - 2 * size, y - 2 * size, x + 2 * size, y + 2 * size), fn), add=True)


PRESSES = [(TL.TAP_TILE, E.TILE), *((p, E.OPEN_BTN) for p in TL.PRESS), (TL.TAP_WANT, E.WANT), (TL.TAP_CAT, E.CAT_CARD),
           (TL.PRESS_UP, E.UP_BTN)]


def press_fx(canvas, t):
    for tp, pt in PRESSES:
        u = (t - tp) / 0.45
        if not 0 <= u < 1:
            continue
        bx, by = zmap(*pt, min(t, tp + 0.001)) if tp == TL.TAP_CAT else pt
        r = 30 + 150 * fx.ease_out(u)
        a = (1 - u) ** 1.5 * 0.8

        def fn(d, m, S, bx=bx, by=by, u=u, tp=tp, r=r, a=a):
            d.ellipse([*m(bx - r, by - r), *m(bx + r, by + r)], outline=(255, 255, 255, int(220 * a)), width=int(5 * S))
            for i in range(12):
                th = i * 2 * math.pi / 12 + tp
                r0, r1 = 20 + 120 * fx.ease_out(u), 40 + 170 * fx.ease_out(u)
                d.line([m(bx + r0 * math.cos(th), by + r0 * math.sin(th)), m(bx + r1 * math.cos(th), by + r1 * math.sin(th))],
                       fill=(255, 240, 200, int(255 * (1 - u))), width=int(5 * S * (1 - u) + S))
        fx.over(canvas, fx.draw_rgba((bx - 240, by - 240, bx + 240, by + 240), fn), add=True)


def roulette_streaks(canvas, t):
    for t0, t1 in TL.SPINS:
        if not (t0 + 0.1 <= t < t1):
            continue
        u = (t - t0) / (t1 - t0)
        a = (1 - u) ** 1.5
        y0, y1 = 560, 1030

        def fn(d, m, S, a=a):
            for i in range(14):
                yy = y0 + (i * 37 % (y1 - y0))
                x = (W + 400) - ((t * 3200 + i * 517) % (W + 800))
                ln = 180 + 120 * ((i * 13) % 5) / 4
                d.line([m(x, yy), m(x + ln, yy)], fill=(220, 230, 255, int(150 * a)), width=int(3 * S))
        fx.over(canvas, fx.draw_rgba((0, y0 - 10, W, y1 + 10), fn), add=True)


def reveal_glow(canvas, t):
    for tp in TL.POP:
        u = t - tp
        if 0 <= u < 0.9:
            x, y = zmap(*E.POPUP_GIFT, t)
            fx.over(canvas, fx.warp(fx.radial(256, (255, 230, 200), power=1.8), x, y, 900 / 256),
                    alpha=0.5 * (1 - u / 0.9), add=True)
            burst(canvas, x, y, u, 330)


def wheel_fx(canvas, t):
    """The upgrade wheel: a glow that tightens with every beat while it spins."""
    t0, t1 = TL.WHEEL
    if not (t0 <= t < t1):
        return
    u = (t - t0) / (t1 - t0)
    x, y = zmap(*E.WHEEL_C, t)
    _, _, z = view(t)
    p = hit_pulse(t)
    fx.over(canvas, fx.warp(fx.radial(256, (200, 110, 255), power=1.6), x, y, (760 + 160 * p) * z / 256), alpha=0.22 + 0.3 * u, add=True)
    ring = fx.radial(256, (255, 215, 120), power=1.0, peak=0.0, ring=(0.8, 0.05, 1.0))
    for k in range(3):
        v = (t * 1.9 + k / 3) % 1.0
        fx.over(canvas, fx.warp(ring, x, y, (900 - 520 * v) * z / 256), alpha=0.5 * v * (0.4 + 0.6 * u), add=True)


def tension(canvas, t):
    """Heartbeat vignette on the wheel: the edges darken, pulsing with the beat."""
    t0, t1 = TL.WHEEL
    if not (t0 + 0.1 <= t < t1):
        return
    if 'vig' not in _POST:
        return
    u = (t - t0) / (t1 - t0)
    k = (0.25 + 0.45 * u) * (0.6 + 0.4 * hit_pulse(t))
    canvas[..., :3] *= 1 - k * (1 - _POST['vig']) * 2.2


def win_fx(canvas, t):
    u = t - TL.WIN
    if u < 0 or t > TL.LAND + 0.5:
        return
    x, y = win_xy(t)
    _, _, z = view(t)
    a = min(1.0, u / 0.12) * (1 - fx.smooth((t - TL.LAND) / 0.5))
    fx.over(canvas, fx.warp(fx.radial(256, (255, 205, 90), power=1.5), x, y, (1000 + 80 * hit_pulse(t)) * z / 256), alpha=0.5 * a, add=True)
    draw_rays(canvas, x, y, 620 * z, u, a, (255, 220, 130))
    burst(canvas, x, y, u, 360, col=(255, 235, 170), n=18, dur=0.8)
    if u < 0.6:
        ring = fx.radial(256, (255, 220, 140), power=1.0, peak=0.0, ring=(0.8, 0.06, 1.0))
        fx.over(canvas, fx.warp(ring, x, y, (300 + 1100 * fx.ease_out(u / 0.6)) * z / 256), alpha=0.9 * (1 - u / 0.6), add=True)


_TXT = {}


def txt(s, size, col):
    key = (s, size, col)
    if key not in _TXT:
        _TXT[key] = fx.text_img(((s, col),), size, 'Heavy')
    return _TXT[key]


def scare_fx(canvas, t):
    """«!» over the cat, a shock ring, dust where he kicked off, speed lines behind him."""
    u = t - TL.SCARE
    if not 0 <= u < 1.1:
        return
    x, y = cat_seat(TL.SCARE)
    if u < 0.5:
        ring = fx.radial(256, (255, 255, 255), power=1.0, peak=0.0, ring=(0.8, 0.07, 1.0))
        fx.over(canvas, fx.warp(ring, x, y - 120, (200 + 900 * fx.ease_out(u / 0.5)) / 256), alpha=0.8 * (1 - u / 0.5), add=True)
    for k, (dx, ang) in enumerate(((-95, -0.3), (0, 0.0), (95, 0.3))):
        uu = u - 0.04 * k
        if 0 <= uu < 0.6:
            kk = fx.ease_out_back(min(1.0, uu / 0.14), 2.6) * (1 - fx.smooth((uu - 0.4) / 0.2))
            im = txt('!', 150, (255, 225, 60))
            fx.over(canvas, fx.warp(im, x + dx * 1.3, y - 420 - 40 * uu, kk, rot_=ang))
    v = t - E.RUN
    if 0 <= v < 0.8:
        x0, y0 = cat_seat(E.RUN)
        for k in range(6):                             # dust puffs
            r = 30 + 90 * fx.ease_out(v / 0.8) + 12 * k
            px = x0 - 40 + 46 * k - 120 * v
            py = y0 + 20 - 30 * (k % 2) - 40 * v
            fx.over(canvas, fx.warp(fx.radial(128, (235, 235, 245), power=1.3), px, py, r / 64), alpha=0.45 * (1 - v / 0.8))
        if v < 0.5:
            def fn(d, m, S):
                for i in range(10):
                    yy = y0 - 380 + i * 34
                    ln = (300 + 110 * ((i * 7) % 4)) * min(1.0, v / 0.08)
                    xx = x0 + 2900 * v * v + 300 * v - 120
                    d.line([m(xx, yy), m(xx - ln, yy)], fill=(255, 255, 255, int(190 * (1 - v / 0.5))), width=int(5 * S))
            fx.over(canvas, fx.draw_rgba((0, y0 - 420, W, y0 + 20), fn), add=True)


def purr_fx(canvas, t):
    """Home again: hearts and «мрр» float up from the purring cat; sparkles on the landing."""
    u = t - TL.LAND
    if u < 0:
        return
    x, y = cat_seat(t)
    burst(canvas, x, y - 100, u, 300, col=(255, 200, 230), n=14, dur=0.6)
    fade = 1 - fx.smooth((t - (DUR - 0.5)) / 0.4)

    def fn(d, m, S):
        for i in range(7):
            v = (u * 0.55 + i * 0.37) % 1.0
            if u < i * 0.2:
                continue
            hx = x + (-150 + 50 * i) + 26 * math.sin(u * 2 + i)
            hy = y - 230 - 300 * v
            r = (20 + 5 * (i % 3)) * min(1.0, v / 0.15)
            a = int(235 * (1 - v) ** 0.8 * fade)
            col = ((255, 105, 150), (255, 150, 190), (255, 210, 110))[i % 3] + (a,)
            d.ellipse([*m(hx - r, hy - r), *m(hx, hy)], fill=col)
            d.ellipse([*m(hx, hy - r), *m(hx + r, hy)], fill=col)
            d.polygon([m(hx - r * 0.96, hy - r * 0.3), m(hx + r * 0.96, hy - r * 0.3), m(hx, hy + r * 0.95)], fill=col)
    fx.over(canvas, fx.draw_rgba((x - 300, y - 620, x + 300, y), fn))
    for i in range(3):
        v = (u * 0.5 + i / 3) % 1.0
        if u < 0.35 + i * 0.3:
            continue
        im = txt('мрр', 54, (255, 235, 245))
        fx.over(canvas, fx.warp(im, x - 210 + 40 * math.sin(u * 3 + i) - 20 * i, y - 60 - 260 * v, 0.8 + 0.3 * v, rot_=-0.15),
                alpha=0.9 * (1 - v) * min(1.0, v / 0.1) * fade)


def qmark_fx(canvas, t):
    """«А может, он убежал в апгрейды?»: an idea bulb of sparkles pops over the head."""
    u = t - 16.60
    if not 0 <= u < 1.2:
        return
    pose = head_pose(t)
    x, y = head_point(pose, 378, -20)
    kk = fx.ease_out_back(min(1.0, u / 0.2), 2.5) * (1 - fx.smooth((u - 0.9) / 0.3))
    fx.over(canvas, fx.warp(fx.radial(128, (255, 230, 120), power=1.5), x, y - 70, 260 * kk / 128), alpha=0.8, add=True)
    fx.over(canvas, fx.warp(txt('!', 150, (255, 230, 90)), x, y - 70, kk, rot_=0.08 * math.sin(u * 9)))


CONF_COLS = [(255, 205, 60), (255, 240, 170), (190, 110, 255), (255, 255, 255), (255, 130, 200)]


def confetti(canvas, t):
    u = t - (TL.WIN + 0.05)
    if not (0 <= u < 3.2):
        return

    def fn(d, m, S):
        for i in range(110):
            r = [((i * 7919 + k * 104729) % 1000) / 1000 for k in range(6)]
            y = -60 - 500 * r[2] + (380 + 520 * r[1]) * u
            x = r[0] * W + 40 * math.sin(u * (2 + 3 * r[3]) + i)
            if y > H + 40:
                continue
            w, h = 10 + 10 * r[4], 5 + 6 * r[5]
            th = u * (3 + 6 * r[3]) + i
            c, sn = math.cos(th), math.sin(th) * (0.4 + 0.6 * abs(math.cos(u * 5 + i)))
            pts = [(x + c * dx - sn * dy, y + sn * dx + c * dy) for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
            d.polygon([m(*p) for p in pts], fill=CONF_COLS[i % 5] + (235,))
    fx.over(canvas, fx.draw_rgba((0, 0, W, H), fn))


def place_aura_text(canvas, t):
    for ta, text, col, (x0, y0) in E.AURA_TEXT:
        u = t - ta
        if not (0 <= u < 1.6):
            continue
        im = txt(text, 92, col)
        k = fx.ease_out_back(min(1.0, u / 0.25), 2.0)
        a = min(1.0, u / 0.08) * (1 - fx.smooth((u - 1.15) / 0.45))
        x, y = x0, y0 - 90 * fx.ease_out(u / 1.6)
        fx.over(canvas, fx.warp(im.filter(ImageFilter.GaussianBlur(14)), x, y, 1.08 * k, rot_=-0.06), alpha=a, add=True)
        fx.over(canvas, fx.warp(im, x, y, k, rot_=-0.06), alpha=a)


FLASH = [(TL.SCARE, (255, 255, 255), 0.30, 0.45), (TL.TAP_TILE, (255, 255, 255), 0.18, 0.25),
         *((p, (120, 150, 255), 0.25, 0.2) for p in TL.PRESS),
         (TL.POP[0], (255, 150, 60), 0.3, 0.28), (TL.POP[1], (255, 60, 50), 0.35, 0.3), (TL.POP[2], (255, 20, 10), 0.45, 0.36),
         (TL.TO_UP, (255, 255, 255), 0.18, 0.28), (TL.TAP_WANT, (150, 170, 255), 0.2, 0.15),
         (TL.RESULTS, (255, 215, 110), 0.3, 0.3), (TL.TAP_CAT, (255, 255, 255), 0.18, 0.28),
         (TL.PRESS_UP, (255, 200, 60), 0.25, 0.25), (TL.WIN, (255, 225, 140), 0.6, 0.85), (TL.LAND, (255, 190, 220), 0.3, 0.25)]


def flashes(canvas, t):
    for tf, col, dur, peak in FLASH:
        u = (t - tf) / dur
        if 0 <= u < 1:
            a = peak * (1 - u) ** 2
            canvas[..., :3] = canvas[..., :3] * (1 - a) + np.array(col, np.float32) * a


SHAKES = [(TL.SCARE, 16), (TL.POP[0], 8), (TL.POP[1], 9), (TL.POP[2], 14), (TL.WIN, 22), (TL.LAND, 9), (TL.TAP_TILE, 5),
          (TL.TO_UP, 6), (TL.RESULTS, 7), (TL.PRESS_UP, 7), *((p, 5) for p in TL.PRESS)]


def shake(t):
    for tf, amp in SHAKES:
        u = t - tf
        if 0 <= u < 0.45:
            k = amp * math.exp(-u * 8)
            return int(k * math.sin(u * 90)), int(k * math.cos(u * 70))
    return 0, 0


_POST = {}
PUNCH = (TL.SCARE, TL.TAP_TILE, *TL.PRESS, *TL.POP, TL.TO_UP, TL.TAP_WANT, TL.RESULTS, TL.TAP_CAT, TL.PRESS_UP, TL.WIN, TL.LAND)


def post(out, t):
    pulse = hit_pulse(t)
    z = 1 + 0.016 * pulse
    big = 0.0
    for tf in PUNCH:
        if 0 <= t - tf < 0.5:
            big = max(big, math.exp(-(t - tf) * 7))
    z += 0.035 * big
    if z > 1.0005:
        cw, ch = W / z, H / z
        x0, y0 = (W - cw) / 2, (H - ch) / 2
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
        rng = np.random.default_rng(45)
        _POST['grain'] = rng.normal(0, 5.5, (4, H // 2, W // 2)).astype(np.float32)
    g = _POST['grain'][int(t * 24) % 4]
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[..., None]
    out = out * _POST['vig'] + g
    return np.clip(out, 0, 255).astype(np.uint8)




def render_at(t):
    canvas = np.zeros((H, W, 3), np.float32)
    place_card(canvas, t)
    roulette_streaks(canvas, t)
    reveal_glow(canvas, t)
    draw_pumpkins(canvas, t)
    wheel_fx(canvas, t)
    tension(canvas, t)
    win_fx(canvas, t)
    tint = tuple(int(v) for v in fire_params(t)[0][1])
    hx, hdy, hsc = head_move(t)
    fx.over(canvas, fx.warp(fx.radial(256, tint, power=1.8), hx, 1640 + hdy, 1000 * hsc / 256),
            alpha=0.20 + 0.12 * hit_pulse(t), add=True)
    if t < E.RUN or t >= TL.LAND - 0.2:               # a warm glow under the cat's seat
        a = 1.0 if t < E.RUN else fx.smooth((t - TL.LAND + 0.2) / 0.3)
        fx.over(canvas, fx.warp(fx.radial(256, (190, 110, 255), power=1.7), E.HOLD[0], E.HOLD[1] - 120, 760 / 256), alpha=0.30 * a, add=True)
    press_fx(canvas, t)
    place_hand(canvas, 'L', t)
    eyes, pose = place_head(canvas, t)
    draw_fire(canvas, eyes, pose[2] / 0.7, t)
    place_hand(canvas, 'R', t)
    draw_cat(canvas, t)
    scare_fx(canvas, t)
    purr_fx(canvas, t)
    qmark_fx(canvas, t)
    confetti(canvas, t)
    place_aura_text(canvas, t)
    fx.over(canvas, LOGO)
    flashes(canvas, t)
    if t > DUR - 0.35:                                 # short fade to black with the track's tail
        canvas *= 1 - fx.smooth((t - (DUR - 0.35)) / 0.35)
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
