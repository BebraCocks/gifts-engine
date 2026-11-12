"""44-rose-or-diamond: the white marble head (the gambler from 43) and the pink statue over the RubUp screen recording.
Hands change shape by action (open / pointing / clenched around a held item), gifts pass from hand to hand.
Frame = f(video time). No RubUp ad break: the RubUp logo stays on screen (author, as in 43)."""
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
from timeline import DUR, HITS, DROP, RESUME, src_at

W, H, FPS = 1080, 1920, 60
fx.set_frame(W, H)
BUILD = paths.build(HERE)
SRC = BUILD / 'src'
A = HERE / 'assets'


def rgba(name):
    return Image.open(A / f'{name}.png').convert('RGBA')


# ---------------------------------------------------------------- characters
CH = {
    'W': dict(head=np.asarray(rgba('head'), np.float32), anchor=(378.0, 800.0), base=0.70,
              lip=(625.0, 405.0, 66.0, 175.0), jaw=15.0, eyes=np.array([(307.0, 410.0), (515.0, 417.0)]),
              hand_off=330.0, hand_y=1760.0, hand_s=0.60),
    'P': dict(head=np.asarray(rgba('pink_head'), np.float32), anchor=(350.0, 734.0), base=0.62,
              lip=(582.0, 375.0, 62.0, 165.0), jaw=12.0, eyes=np.array([(259.0, 369.0), (459.0, 369.0)]),
              hand_off=285.0, hand_y=1770.0, hand_s=0.55),
}
HANDS = {
    ('W', 'open', 'L'): rgba('hand_l'), ('W', 'open', 'R'): rgba('hand_r'), ('W', 'point', 'R'): rgba('hand_point'),
    ('W', 'fist', 'L'): rgba('fist_l'), ('W', 'fist', 'R'): rgba('fist_r'),
    ('P', 'open', 'L'): rgba('pink_hand_l'), ('P', 'open', 'R'): rgba('pink_hand_r'),
    ('P', 'fist', 'L'): rgba('pink_fist_l'), ('P', 'fist', 'R'): rgba('pink_fist_r'),
}
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
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-ss', '31', '-i', str(HERE / 'input' / 'rubup_screen.mp4'),
                        '-frames:v', '1', '-vf', 'crop=150:96:12:200,scale=225:144:flags=lanczos', str(f)], check=True)
    reg = np.asarray(Image.open(f).convert('RGB'), np.float32)
    bg = np.median(np.concatenate([reg[:4].reshape(-1, 3), reg[-4:].reshape(-1, 3)]), 0)
    a = np.clip(np.abs(reg - bg).max(2) / 110.0, 0, 1)
    rgb = bg + (reg - bg) / np.maximum(a[..., None], 1e-3)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA'), 14, 6


LOGO = _logo()


# ---------------------------------------------------------------- voice envelopes (mouths)
def _env(who):
    f = BUILD / f'voice_env_{who}.npy'
    if f.exists():
        return np.load(f)
    import voice_review as V
    sr = V.SR
    keep = [c for c in script.VOICE_CUES if script.LINES[c[0]][0] == who]
    saved = script.VOICE_CUES
    script.VOICE_CUES = keep
    v = V.voice_track(int(DUR * sr) + sr)
    script.VOICE_CUES = saved
    hop = sr // FPS
    e = np.array([np.sqrt((v[k:k + hop] ** 2).mean()) for k in range(0, len(v) - hop, hop)])
    e = e / (np.percentile(e[e > 1e-4], 95) + 1e-9)
    out, prev = np.zeros_like(e), 0.0
    for k, x in enumerate(np.clip(e, 0, 1.2)):
        prev = prev + (x - prev) * (0.55 if x > prev else 0.22)
        out[k] = prev
    np.save(f, out)
    return out


ENV = {'W': _env('W'), 'P': _env('P')}


def talk(who, t):
    k = int(t * FPS)
    e = ENV[who]
    return float(e[k]) if 0 <= k < len(e) else 0.0


# ---------------------------------------------------------------- eye fire (white head only)
FIRE = {   # core, mid, outer, height, width, intensity, turbulence, size
    'calm':    ((215, 235, 255), (60, 120, 255), (20, 30, 160), 120, 34, 0.90, 0.6, 16),
    'tense':   ((255, 225, 255), (175, 60, 255), (70, 0, 150), 165, 38, 1.05, 0.9, 17),
    'annoyed': ((255, 240, 200), (255, 140, 30), (170, 45, 0), 160, 38, 1.05, 1.0, 17),
    'angry':   ((255, 220, 180), (255, 70, 20), (150, 10, 0), 215, 44, 1.20, 1.4, 19),
    'rage':    ((255, 240, 220), (255, 30, 10), (130, 0, 0), 300, 52, 1.45, 1.9, 23),
    'cocky':   ((220, 255, 255), (40, 200, 255), (0, 60, 170), 165, 36, 1.00, 0.8, 17),
    'love':    ((255, 230, 245), (255, 90, 190), (170, 20, 110), 175, 40, 1.10, 0.9, 18),
    'evil':    ((255, 200, 200), (210, 0, 60), (70, 0, 90), 250, 46, 1.30, 1.5, 20),
    'joy':     ((255, 255, 230), (255, 200, 40), (255, 90, 0), 340, 58, 1.55, 1.3, 25),
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


def head_move(who, t):
    K = E.W_KEYS if who == 'W' else E.P_KEYS
    if t <= K[0][0]:
        return K[0][1:]
    for (t0, *a), (t1, *b) in zip(K, K[1:]):
        if t0 <= t < t1:
            u = fx.smooth((t - t0) / (t1 - t0))
            if who == 'P' and (t0, t1) == E.PINK_IN:
                u = fx.ease_out_back((t - t0) / (t1 - t0), 1.2)
            return tuple(p + (q - p) * u for p, q in zip(a, b))
    return K[-1][1:]


def pink_state(t):
    if t < 4.5:
        return 'idle'
    if t < E.GIVE:
        return 'pout'
    if t < 18.85:
        return 'puzzled'
    return 'angry'


def head_pose(who, t):
    """-> (anchor x, anchor y, scale, rotation rad)"""
    c = CH[who]
    tk = talk(who, t)
    pulse = hit_pulse(t)
    hx, mdy, mds = head_move(who, t)
    vx = (head_move(who, t + 0.04)[0] - head_move(who, t - 0.04)[0]) / 0.08
    s = c['base'] * mds * (1 + 0.02 * pulse + 0.01 * tk) * (1 + 0.00003 * abs(vx))
    x, y = hx, 1915.0 + mdy - 0.03 * abs(vx)
    rot = 0.03 * math.sin(t * 1.3 + (0 if who == 'W' else 2.0)) + 0.02 * tk * math.sin(t * 7.0) - 0.00018 * vx
    y += 4 * math.sin(t * 2.1 + (0 if who == 'W' else 1.0)) - 8 * pulse
    if who == 'W':
        st = emotion_at(t)
        if t < 9.5:                                        # thinking: slow tilt
            rot += 0.06 * math.sin(t * 0.9)
        if st in ('rage', 'angry', 'evil'):
            amp = {'rage': 1.0, 'angry': 0.45, 'evil': 0.25}[st]
            x += amp * 7 * math.sin(t * 61) + amp * 4 * math.sin(t * 37)
            rot += amp * 0.035 * math.sin(t * 47)
        if st == 'love':
            rot += 0.05 * math.sin(t * 3.0)
        u = t - E.ROSE_HIT                                 # knocked by the rose
        if 0 <= u < 1.0:
            k = math.exp(-u * 5) * math.cos(u * 14)
            rot += 0.22 * k
            x -= 40 * k
            y += 15 * abs(k)
        if st == 'joy':
            y -= 26 * abs(math.sin(t * math.pi / 0.627))
            rot += 0.05 * math.sin(t * math.pi / 1.254)
    else:
        ps = pink_state(t)
        if ps == 'pout':
            rot += -0.05 + 0.04 * math.sin(t * 2.6) * min(1.0, tk * 2)
        elif ps == 'puzzled':
            k = fx.smooth((t - E.STARE[0]) / 0.5)
            rot += 0.16 * k + 0.02 * math.sin(t * 1.7)
        elif ps == 'angry':
            amp = 0.8 * (1 - fx.smooth((t - 20.2) / 0.4))
            x += amp * 8 * math.sin(t * 59)
            rot += -0.08 * fx.smooth((t - 18.85) / 0.2) + amp * 0.04 * math.sin(t * 43)
    return x, y, s, rot


def head_point(pose, who, px, py):
    """head-image pixel -> frame point for a head pose"""
    x, y, s, rot = pose
    ax, ay = CH[who]['anchor']
    c, sn = math.cos(rot), math.sin(rot)
    return x + s * (c * (px - ax) - sn * (py - ay)), y + s * (sn * (px - ax) + c * (py - ay))


def place_head(canvas, who, t):
    pose = head_pose(who, t)
    x, y, s, rot = pose
    opening = CH[who]['jaw'] * min(1.0, talk(who, t) ** 0.8)
    fx.over(canvas, fx.warp(head_image(who, opening), x, y, s, rot_=rot, anchor=CH[who]['anchor']))
    return [head_point(pose, who, ex, ey) for ex, ey in CH[who]['eyes']], pose


# ---------------------------------------------------------------- hands: shape by action
def rest(who, side, t):
    c = CH[who]
    hx, hdy, hsc = head_move(who, t)
    ph = (0.0 if side == 'L' else 1.3) + (0 if who == 'W' else 0.7)
    x = hx + (-1 if side == 'L' else 1) * c['hand_off'] * hsc + 5 * math.sin(t * 1.1 + ph)
    y = c['hand_y'] + hdy + 9 * math.sin(t * 1.9 + ph) - 10 * hit_pulse(t)
    return x, y, 0.0, c['hand_s'] * hsc


def lift(who, side, t):
    x, y, r, s = rest(who, side, t)
    hsc = head_move(who, t)[2]
    return x + (60 if side == 'L' else -60) * hsc, y - 150 * hsc, (0.08 if side == 'L' else -0.08), s * 1.02


def raised(who, side, t):
    x, y, r, s = rest(who, side, t)
    ph = 0.0 if side == 'L' else 1.0
    b = abs(math.sin(t * math.pi / 0.627 + ph))
    return x + (-70 if side == 'L' else 70), y - 340 - 40 * b, (0.35 if side == 'L' else -0.35) + 0.12 * math.sin(t * 10 + ph), s


def popup_xy(t):
    x, y = zmap(*E.POPUP_GIFT, t)
    return x, y + 30


def C(x, y, r=0.0, sm=1.0):
    return ('c', x, y, r, sm)


def T(x, y, r=0.0, sm=1.0):
    return ('tip', x, y, r, sm)


P_ = lambda: 'popup'
POPUP = ('popup',)
LIFT = ('lift',)
RAISED = ('raised',)

# (time, pose, target): the hand glides between targets (ease-in-out); the pose changes at the waypoint time.
# None = rest beside the head; C(...) = hand centre; T(...) = fingertip of the pointing hand.
PATHS = {
    ('W', 'R'): [
        (0.00, 'open', None), (0.15, 'point', T(770, 1420)), (0.30, 'point', T(770, 1380)),
        (0.75, 'point', T(800, 880)), (1.05, 'point', T(770, 1400)), (1.20, 'point', T(770, 1380)),
        (1.65, 'point', T(800, 880)), (2.25, 'open', None),
        (13.20, 'open', None), (13.35, 'point', T(640, 1330)), (E.PRESS1, 'point', T(548, 1172)),
        (13.85, 'point', T(610, 1280)), (14.05, 'fist', LIFT), (15.40, 'fist', LIFT),
        (15.50, 'open', None), (E.GRAB1 - 0.08, 'open', POPUP), (E.GRAB1, 'fist', POPUP),
        (16.40, 'fist', C(430, 1430, 0.1)), (16.60, 'fist', C(430, 1430, 0.1)),
        (E.GIVE - 0.12, 'fist', C(590, 1440, -0.15)), (E.GIVE, 'open', C(590, 1450, -0.1)), (17.75, 'open', None),
        (22.10, 'open', None), (22.30, 'point', T(780, 1800)), (E.PRESS2, 'point', T(712, 1868)),
        (22.75, 'point', T(780, 1780)), (22.95, 'fist', LIFT), (24.35, 'fist', LIFT),
        (24.45, 'open', None), (E.GRAB2 - 0.08, 'open', POPUP), (E.GRAB2, 'fist', POPUP),
        (25.30, 'fist', C(600, 1440, -0.05)), (26.40, 'fist', C(610, 1420, 0.05)), (E.WINDUP, 'fist', C(600, 1440, 0.0)),
        (27.72, 'fist', C(260, 1330, 0.7, 1.05)), (E.THROW2, 'open', C(930, 1120, -0.6, 1.1)),
        (28.15, 'open', C(820, 1300, -0.2)), (28.55, 'open', None), (28.85, 'open', RAISED),
    ],
    ('W', 'L'): [
        (0.00, 'open', None), (13.80, 'open', None), (13.95, 'fist', LIFT), (15.40, 'fist', LIFT), (15.60, 'open', None),
        (22.65, 'open', None), (22.80, 'fist', LIFT), (24.35, 'fist', LIFT), (24.55, 'open', None),
        (DROP + 0.25, 'open', None), (28.75, 'open', RAISED),
    ],
    ('P', 'L'): [
        (0.00, 'open', None), (16.90, 'open', None), (E.GIVE - 0.06, 'open', C(640, 1450, 0.1)),
        (E.GIVE, 'fist', C(640, 1440, 0.05)), (17.65, 'fist', C(700, 1330, 0.12)), (18.80, 'fist', C(705, 1325, 0.1)),
        (19.00, 'fist', C(900, 1240, -0.5)), (E.THROW1, 'open', C(640, 1190, 0.5, 1.05)),
        (19.45, 'open', C(700, 1450, 0.2)), (19.80, 'open', None),
    ],
    ('P', 'R'): [(0.00, 'open', None)],
}


def resolve(target, who, side, t, pose):
    """target -> hand-centre frame position (x, y, rot, scale)"""
    if target is None:
        return rest(who, side, t)
    if target == LIFT:
        return lift(who, side, t)
    if target == RAISED:
        return raised(who, side, t)
    base = CH[who]['hand_s'] * head_move(who, t)[2]
    if target == POPUP:
        x, y = popup_xy(t)
        return x, y, -0.15, base * 1.05
    kind, x, y, r, sm = target
    s = base * sm
    if kind == 'tip':                                  # fingertip -> centre of the pointing hand
        img = HANDS[(who, 'point', side)]
        rr = r + PT_ROT
        dx, dy = (img.width / 2 - PT_TIP[0]) * s, (img.height / 2 - PT_TIP[1]) * s
        c, sn = math.cos(rr), math.sin(rr)
        return x + c * dx - sn * dy, y + sn * dx + c * dy, r, s
    return x, y, r, s


def hand_state(who, side, t):
    """-> pose, previous pose, pose blend 0..1, (x, y, rot, scale) of the hand centre"""
    P = PATHS[(who, side)]
    i = 0
    while i + 1 < len(P) and P[i + 1][0] <= t:
        i += 1
    t0, pose, a = P[i]
    prev = P[i - 1][1] if i > 0 else pose
    blend = fx.smooth(min(1.0, (t - t0) / 0.10)) if prev != pose else 1.0
    pa = resolve(a, who, side, t, pose)
    if i + 1 < len(P) and t >= t0:
        t1, pose1, b = P[i + 1]
        pb = resolve(b, who, side, t, pose1)
        u = fx.smooth((t - t0) / (t1 - t0))
        st = tuple(p + (q - p) * u for p, q in zip(pa, pb))
    else:
        st = pa
    x, y, r, s = st
    if who == 'W':                                     # emotions shake the hands too
        em = emotion_at(t)
        if em in ('rage', 'angry'):
            amp = 1.0 if em == 'rage' else 0.5
            ph = 0 if side == 'L' else 1.3
            y += amp * 10 * math.sin(t * 43 + ph)
            r += amp * 0.06 * math.sin(t * 29 + ph)
        u = t - E.ROSE_HIT
        if 0 <= u < 0.6:
            y -= 60 * math.exp(-u * 6)
        if pose == 'fist' and (13.9 < t < 15.5 or 22.8 < t < 24.45):
            x += 3 * math.sin(t * 53 + (0 if side == 'L' else 1))
            y += 4 * math.sin(t * 47)
    if who == 'P' and pink_state(t) == 'pout' and side == 'R':  # she gestures while complaining
        k = min(1.0, talk('P', t) * 1.5)
        y -= 70 * k
        r -= 0.2 * k
    return pose, prev, blend, (x, y, r, s)


def draw_hand_img(canvas, who, pose, side, st, alpha=1.0, squash=1.0):
    x, y, r, s = st
    img = HANDS[(who, pose, side)] if (who, pose, side) in HANDS else HANDS[(who, 'open', side)]
    rr = r + (PT_ROT if pose == 'point' else 0.0)
    fx.over(canvas, fx.warp(img, x, y, s * squash, rot_=rr), alpha=alpha)


def place_hand(canvas, who, side, t):
    pose, prev, blend, st = hand_state(who, side, t)
    for it in ITEMS:                                   # a held item sits behind the clenched fingers
        h = it.holder(t)
        if h == (who, side):
            it.draw_held(canvas, t, st)
    if blend < 1.0:                                    # quick morph: the old shape shrinks out, the new pops in
        draw_hand_img(canvas, who, prev, side, st, alpha=1 - blend, squash=1 - 0.12 * blend)
        draw_hand_img(canvas, who, pose, side, st, alpha=blend, squash=0.9 + 0.1 * blend)
    else:
        draw_hand_img(canvas, who, pose, side, st)


def fist_top(st, who):
    """Point just above the knuckles of a fist (where a held item comes out)."""
    x, y, r, s = st
    h = HANDS[(who, 'fist', 'R')].height
    c, sn = math.cos(r), math.sin(r)
    off = -0.30 * h * s
    return x - sn * off, y + c * off


# ---------------------------------------------------------------- items: rose and diamond
class Item:
    def __init__(self, gid, popup_t, grab, hand_seq, release, fly, size_held):
        self.path = None
        self.gid = gid
        self.popup_t, self.grab, self.hand_seq, self.release, self.fly, self.size_held = \
            popup_t, grab, hand_seq, release, fly, size_held

    def lottie(self, t, size):
        if self.path is None:
            self.path = str(gifts_api.original_file(self.gid, 'json'))
        return lottie.frame(self.path, max(0.0, t - self.grab), size=int(size) // 2 * 2)

    def holder(self, t):
        if not (self.grab <= t < self.release):
            return None
        h = None
        for ts, who, side in self.hand_seq:
            if t >= ts:
                h = (who, side)
        return h

    def size(self, t):
        u = fx.smooth(min(1.0, (t - self.grab) / 0.45))
        _, _, z = view(t)
        return 470 * z * (1 - u) + self.size_held * u

    def draw_held(self, canvas, t, st):
        who = self.holder(t)[0]
        x, y = fist_top(st, who)
        sz = self.size(t)
        im = self.lottie(t, sz)
        fx.over(canvas, fx.warp(im, x, y - sz * 0.30, 1.0, rot_=st[2] * 0.6))

    def draw_free(self, canvas, t):
        self.fly(self, canvas, t)


def rose_fly(it, canvas, t):
    if not (E.THROW1 <= t < 21.2):
        return
    _, _, _, st = hand_state('P', 'L', E.THROW1)
    x0, y0 = fist_top(st, 'P')
    x0, y0 = x0, y0 - 80
    ex = [head_point(head_pose('W', E.ROSE_HIT), 'W', px, py) for px, py in CH['W']['eyes']]
    x1, y1 = (ex[0][0] + ex[1][0]) / 2, (ex[0][1] + ex[1][1]) / 2 + 10
    if t < E.ROSE_HIT:
        u = (t - E.THROW1) / (E.ROSE_HIT - E.THROW1)
        x = x0 + (x1 - x0) * u
        y = y0 + (y1 - y0) * u - 120 * math.sin(math.pi * u)
        rot = 7.0 * u
        sz = it.size_held * (1 + 0.15 * u)
    else:                                              # bounces off the face and falls out of the frame
        u = t - E.ROSE_HIT
        x = x1 - 260 * u
        y = y1 - 520 * u + 0.5 * 2600 * u * u
        rot = 7.0 + 9 * u
        sz = it.size_held * 1.15
    fx.over(canvas, fx.warp(it.lottie(t, sz), x, y, 1.0, rot_=rot))


def diamond_fly(it, canvas, t):
    if not (E.THROW2 <= t < E.HIT2 + 0.05):
        return
    _, _, _, st = hand_state('W', 'R', E.THROW2)
    x0, y0 = fist_top(st, 'W')
    u = (t - E.THROW2) / (E.HIT2 - E.THROW2)
    x = x0 + (1300 - x0) * u
    y = y0 - 80 + (1060 - y0 + 80) * u - 160 * math.sin(math.pi * u)
    sz = it.size_held * (1 + 0.5 * u)
    for k in range(4):                                 # motion trail
        uu = max(0.0, u - 0.06 * (k + 1))
        xx = x0 + (1300 - x0) * uu
        yy = y0 - 80 + (1060 - y0 + 80) * uu - 160 * math.sin(math.pi * uu)
        fx.over(canvas, fx.warp(fx.radial(128, (140, 210, 255), power=1.6), xx, yy, sz * 0.8 / 128), alpha=0.35 * (1 - k / 4), add=True)
    fx.over(canvas, fx.warp(it.lottie(t, sz), x, y, 1.0, rot_=-9 * u))


ROSE = Item(E.ROSE_ID, E.POP1, E.GRAB1, [(E.GRAB1, 'W', 'R'), (E.GIVE, 'P', 'L')], E.THROW1, rose_fly, 250)
DIAMOND = Item(E.DIAMOND_ID, E.POP2, E.GRAB2, [(E.GRAB2, 'W', 'R')], E.THROW2, diamond_fly, 230)
ITEMS = [ROSE, DIAMOND]


# ---------------------------------------------------------------- screen
HEADER = 105                        # frame rows of the RubUp header kept in the crop (balance painted over)


def card_image(t):
    st = src_at(t)
    a = np.asarray(src_frame(st)).copy()
    a[0:HEADER] = a[0:HEADER, 540:541]                 # the star balance (and the half-cut logo) vanish
    for it, name, s0, s1 in ((ROSE, 'rose', 39.9, 44.06), (DIAMOND, 'diamond', 52.7, 99)):
        if t >= it.grab and s0 <= st < s1:              # taken out of the window: the picture is empty
            x0, y0, x1, y1 = E.GIFT_BOX[name]
            fx0, fy0 = E.card_xy(x0, y0)
            fx1, fy1 = E.card_xy(x1, y1)
            fx0, fy0, fx1, fy1 = int(fx0), int(fy0), int(fx1), int(fy1)
            k = fx.smooth(min(1.0, (t - it.grab) / 0.12))
            left = a[fy0:fy1, fx0 - 4:fx0 - 3].astype(np.float32)
            right = a[fy0:fy1, fx1 + 3:fx1 + 4].astype(np.float32)
            u = np.linspace(0, 1, fx1 - fx0)[None, :, None]
            fill = left + (right - left) * u
            a[fy0:fy1, fx0:fx1] = (a[fy0:fy1, fx0:fx1] * (1 - k) + fill * k).astype(np.uint8)
    return Image.fromarray(a)


def view(t):
    best = (E.CARD_W / 2, E.CARD_H / 2, 1.0)
    for t0, t1, (ox, oy), z0, z1 in E.ZOOMS:
        if t0 - 0.01 <= t < t1:
            u = (t - t0) / (t1 - t0)
            zin = fx.ease_out(min(1.0, (t - t0) / 0.3))
            z = 1 + ((z0 + (z1 - z0) * fx.smooth(u)) - 1) * zin
            return ox * E.CARD_S, (oy - E.CARD_Y0) * E.CARD_S, z
    return best


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
PRESSES = [(E.PRESS1, (548, 1172)), (E.PRESS2, (712, 1868))]
SPINS = [(E.PRESS1, E.POP1), (E.PRESS2, E.POP2)]


def press_fx(canvas, t):
    for tp, (bx, by) in PRESSES:
        u = (t - tp) / 0.45
        if not 0 <= u < 1:
            continue
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
    for t0, t1 in SPINS:
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


def reveal_glow(canvas, t):
    for tp in (E.POP1, E.POP2):
        u = t - tp
        if 0 <= u < 0.9:
            x, y = zmap(*E.POPUP_GIFT, t)
            fx.over(canvas, fx.warp(fx.radial(256, (255, 230, 200), power=1.8), x, y, 900 / 256),
                    alpha=0.5 * (1 - u / 0.9), add=True)
            burst(canvas, x, y, u, 330)


def pink_entry_trail(canvas, t):
    u = (t - E.PINK_IN[0]) / (E.PINK_IN[1] - E.PINK_IN[0])
    if 0 <= u < 1.3:
        x, _, _ = head_move('P', t)
        a = 0.55 * (1 - min(1.0, u)) ** 0.7

        def fn(d, m, S):
            for i in range(9):
                yy = 1430 + i * 50
                d.line([m(x + 120, yy), m(x + 120 + 420 * (1 - min(1.0, u)), yy)],
                       fill=(255, 170, 200, int(200 * a)), width=int(4 * S))
        fx.over(canvas, fx.draw_rgba((0, 1380, W, H), fn), add=True)


QMARK = {}


def question_marks(canvas, t):
    """She stares at the rose: three «?» pop up over her head one after another."""
    if not (E.STARE[0] <= t < E.STARE[1] + 0.25):
        return
    pose = head_pose('P', t)
    hx, hy = head_point(pose, 'P', 350, 30)
    if 'q' not in QMARK:
        QMARK['q'] = fx.text_img((('?', (255, 255, 255)),), 130, 'Heavy')
    q = QMARK['q']
    for k, (dx, dy, ang) in enumerate(((-120, -40, -0.25), (10, -110, 0.05), (130, -50, 0.3))):
        u = t - (E.STARE[0] + 0.15 + 0.4 * k)
        if u < 0:
            continue
        out = fx.smooth((t - E.STARE[1]) / 0.25)
        kk = fx.ease_out_back(min(1.0, u / 0.25), 2.4) * (1 - out)
        y = hy + dy - 10 * math.sin(u * 4 + k)
        fx.over(canvas, fx.warp(q.filter(ImageFilter.GaussianBlur(10)), hx + dx, y, kk), alpha=0.8, add=True)
        fx.over(canvas, fx.warp(q, hx + dx, y, kk, rot_=ang + 0.08 * math.sin(u * 5 + k)))


def anger_mark(canvas, t):
    """Her «Да пошёл ты!»: a red anger mark pulses beside her head."""
    u = t - 18.90
    if not 0 <= u < 1.4:
        return
    pose = head_pose('P', t)
    x, y = head_point(pose, 'P', 600, 120)
    k = fx.ease_out_back(min(1.0, u / 0.2), 2.5) * (1 + 0.12 * math.sin(u * 18)) * (1 - fx.smooth((u - 1.1) / 0.3))
    r = 60 * k

    def fn(d, m, S):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            cx, cy = x + sx * r * 0.62, y + sy * r * 0.62
            box = [*m(cx - r * 0.5, cy - r * 0.5), *m(cx + r * 0.5, cy + r * 0.5)]
            start = {(-1, -1): 0, (1, -1): 90, (1, 1): 180, (-1, 1): 270}[(sx, sy)]
            d.arc(box, start, start + 90, fill=(255, 40, 50, 255), width=int(9 * S))
    fx.over(canvas, fx.draw_rgba((x - 2 * r - 20, y - 2 * r - 20, x + 2 * r + 20, y + 2 * r + 20), fn))


SHADES = None


def shades_img():
    global SHADES
    if SHADES is None:
        lens = ['#WW########', '##WW#######', '.##WW#####.', '..#######..']
        rows = ['#' * 26] + ['.' + r + '..' + r + '.' for r in lens]
        cell = 16
        im = Image.new('RGBA', (26 * cell, len(rows) * cell), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for j, row in enumerate(rows):
            assert len(row) == 26, row
            for i, ch in enumerate(row):
                if ch != '.':
                    d.rectangle([i * cell, j * cell, (i + 1) * cell - 1, (j + 1) * cell - 1],
                                fill=(255, 255, 255, 255) if ch == 'W' else (8, 8, 10, 255))
        SHADES = im
    return SHADES


def place_shades(canvas, pose, t):
    """The flex: pixel shades fall onto the eyes and stay."""
    u = t - E.SHADES
    if u < -0.4:
        return
    x, y, s, rot = pose
    cx, cy = head_point(pose, 'W', 411.0, 413.0 - 20)
    k = fx.ease_out_back(fx.clamp01((u + 0.4) / 0.4), 1.6)
    yy = cy - 700 * (1 - k)
    im = shades_img()
    fx.over(canvas, fx.warp(im, cx, yy, s * 1.05, rot_=rot, anchor=(im.width / 2, 2.5 * 16)))


def flex_glow(canvas, t):
    u = t - E.HIT2
    if u < 0:
        return
    pose = head_pose('W', t)
    x, y = head_point(pose, 'W', 378, 420)
    a = min(1.0, u / 0.3)
    fx.over(canvas, fx.warp(fx.radial(256, (255, 200, 70), power=1.5), x, y, (1100 + 80 * hit_pulse(t)) / 256), alpha=0.45 * a, add=True)
    n, r = 14, 760

    def fn(d, m, S):
        for k in range(n):
            th = u * 0.35 + k * 2 * math.pi / n
            w = 0.09
            d.polygon([m(x, y), m(x + r * math.cos(th - w), y + r * math.sin(th - w)),
                       m(x + r * math.cos(th + w), y + r * math.sin(th + w))], fill=(255, 220, 120, int(30 * a)))
    placed = fx.draw_rgba((x - r, y - r, x + r, y + r), fn)
    fx.over(canvas, (placed[0].filter(ImageFilter.GaussianBlur(6)),) + placed[1:], add=True)


CONF_COLS = [(255, 205, 60), (255, 240, 170), (255, 150, 40), (255, 255, 255), (120, 200, 255)]


def confetti(canvas, t):
    u = t - (E.HIT2 + 0.05)
    if not (0 <= u < 3.0):
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


def hit_fx(canvas, t):
    u = t - E.ROSE_HIT                                  # rose smacks the face
    if 0 <= u < 0.6:
        ex = [head_point(head_pose('W', E.ROSE_HIT), 'W', px, py) for px, py in CH['W']['eyes']]
        burst(canvas, (ex[0][0] + ex[1][0]) / 2, (ex[0][1] + ex[1][1]) / 2, u, 200, col=(255, 120, 140), n=12, dur=0.5)
    u = t - E.HIT2                                      # diamond hits her off-screen right
    if 0 <= u < 0.9:
        x, y = 1060, 1060
        fx.over(canvas, fx.warp(fx.radial(256, (255, 240, 200), power=1.4), x, y, (500 + 900 * fx.ease_out(u / 0.9)) / 256),
                alpha=0.9 * (1 - u / 0.9), add=True)
        burst(canvas, x - 40, y, u, 420, col=(255, 250, 220), n=18, dur=0.8)

        def fn(d, m, S):                                # comic impact star
            k = 1 - u / 0.9
            pts = []
            for i in range(16):
                rr = (260 if i % 2 == 0 else 110) * (0.7 + 0.5 * fx.ease_out(min(1.0, u / 0.15)))
                th = i * 2 * math.pi / 16 + 0.2
                pts.append(m(x + rr * math.cos(th), y + rr * math.sin(th)))
            d.polygon(pts, fill=(255, 255, 255, int(235 * k)), outline=(255, 200, 60, int(255 * k)))
        fx.over(canvas, fx.draw_rgba((x - 380, y - 380, x + 380, y + 380), fn))


def place_aura_text(canvas, t):
    for ta, text, col, (x0, y0) in E.AURA_TEXT:
        u = t - ta
        if not (0 <= u < 1.8):
            continue
        im = fx.text_img(((text, col),), 96, 'Heavy')
        k = fx.ease_out_back(min(1.0, u / 0.25), 2.0)
        a = min(1.0, u / 0.08) * (1 - fx.smooth((u - 1.3) / 0.5))
        x, y = x0, y0 - 110 * fx.ease_out(u / 1.8)
        fx.over(canvas, fx.warp(im.filter(ImageFilter.GaussianBlur(14)), x, y, 1.08 * k, rot_=-0.06), alpha=a, add=True)
        fx.over(canvas, fx.warp(im, x, y, k, rot_=-0.06), alpha=a)


def flashes(canvas, t):
    for tf, col, dur, peak in ((E.PINK_IN[1] - 0.1, (255, 150, 200), 0.3, 0.22), (E.PRESS1, (120, 150, 255), 0.25, 0.2),
                               (E.POP1, (255, 255, 255), 0.18, 0.25), (E.ROSE_HIT, (255, 40, 60), 0.4, 0.3),
                               (E.RAGE, (255, 20, 10), 0.45, 0.3), (E.PRESS2, (255, 60, 40), 0.25, 0.2),
                               (E.POP2, (200, 235, 255), 0.2, 0.3), (E.HIT2, (255, 215, 110), 0.6, 0.8),
                               (9.55, (255, 255, 255), 0.15, 0.2)):
        u = (t - tf) / dur
        if 0 <= u < 1:
            a = peak * (1 - u) ** 2
            canvas[..., :3] = canvas[..., :3] * (1 - a) + np.array(col, np.float32) * a


def shake(t):
    for tf, amp in ((E.ROSE_HIT, 14), (E.RAGE, 12), (E.HIT2, 22), (E.PRESS1, 5), (E.PRESS2, 7), (E.PINK_IN[1] - 0.1, 6)):
        u = t - tf
        if 0 <= u < 0.45:
            k = amp * math.exp(-u * 8)
            return int(k * math.sin(u * 90)), int(k * math.cos(u * 70))
    return 0, 0


_POST = {}
PUNCH = (E.PINK_IN[1] - 0.1, 9.55, E.PRESS1, E.POP1, E.ROSE_HIT, E.RAGE, E.PRESS2, E.POP2, E.HIT2, 2.40, 6.70)


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
        rng = np.random.default_rng(44)
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
    tint = tuple(int(v) for v in fire_params(t)[0][1])
    hx, hdy, hsc = head_move('W', t)
    fx.over(canvas, fx.warp(fx.radial(256, tint, power=1.8), hx, 1640 + hdy, 1000 * hsc / 256),
            alpha=0.20 + 0.12 * hit_pulse(t), add=True)
    if 4.0 <= t < 20.7:
        px, pdy, _ = head_move('P', t)
        fx.over(canvas, fx.warp(fx.radial(256, (255, 140, 190), power=1.8), px, 1660 + pdy, 900 / 256), alpha=0.18, add=True)
    flex_glow(canvas, t)
    press_fx(canvas, t)
    pink_entry_trail(canvas, t)
    # pink (behind the white one: she stands at the right edge)
    if t >= E.PINK_IN[0] - 0.05 and t < E.PINK_OUT[1] + 0.1:
        place_hand(canvas, 'P', 'R', t)
        place_head(canvas, 'P', t)
        place_hand(canvas, 'P', 'L', t)
    place_hand(canvas, 'W', 'L', t)
    eyes, pose = place_head(canvas, 'W', t)
    place_shades(canvas, pose, t)
    draw_fire(canvas, eyes, pose[2] / 0.7, t)
    place_hand(canvas, 'W', 'R', t)
    for it in ITEMS:
        it.draw_free(canvas, t)
    question_marks(canvas, t)
    anger_mark(canvas, t)
    hit_fx(canvas, t)
    confetti(canvas, t)
    place_aura_text(canvas, t)
    fx.over(canvas, LOGO)
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
