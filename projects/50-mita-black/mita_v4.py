"""v4 (2026-11-17): белая студия, без локаций; Мита — позы ChatGPT с досчётом кадров, переходы 0,35–0,5 с,
в паузах постоянное микродвижение. Сцены: хук (ходьба, 9 поз) → кружение → кекс в камеру → тыква (сидит на Red Demon)
→ прыжок → жуть → карусель редкости → «хм» → [реклама: попкорн] → спутники (карта/машина/смокинг) → телефон → пинок
→ график (плавный отрыв) → два NFT. Помощники размещения — из mita_v3 (put_mita, grade, cards_painter…)."""
import functools
import math

import numpy as np
from PIL import Image

import anim
import fx
import events as E
import mita_v3 as V3
from mita_v3 import put_mita, grade, cards_painter, lot3, biggest, tile_np, shadow_sprite, phone_painter
from timeline import AD_STOP, DUR, ON

R = None
S0, BASE, HOOK_BASE, FOOT = V3.S0, V3.BASE, V3.HOOK_BASE, V3.FOOT
SPIN_END = E.SPIN + 1.05


def bind(r):
    global R
    R = r
    V3.bind(r)


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.3):
    return ease((t - t0) / d)


class Drift(anim.Track):
    """Дорожка с «живым» удержанием: пока поза держится, она слегка перетекает к соседней (6–10 %) — без застываний."""

    def __init__(self, keys, dur=0.42, drift=None, amt=0.09):
        super().__init__(keys, dur)
        self.drift = drift or {}
        self.amt = amt

    def frame(self, t):
        a, b, k = self.at(t)
        if a != b:
            return anim.morph(a, b, k)
        alt = self.drift.get(a)
        if alt:
            w = self.amt * (0.5 + 0.5 * math.sin(t * 1.7))
            return anim.morph(a, alt, w)
        return anim.pose(a)


# ------------------------------------------------------------------ дорожки
HOOK_T = Drift([(0.0, 'hook_peek'), (1.15, 'hook_in_a'), (1.38, 'hook_w1'), (1.6, 'hook_in_b'), (1.82, 'hook_w2'),
                (2.04, 'hook_step'), (2.26, 'hook_w3'), (2.5, 'hook_in_c'), (2.85, 'hook_wave'), (3.2, 'hook_in_c'),
                (3.55, 'hook_wave'), (4.0, 'hook_in_c')], dur=0.22,
               drift={'hook_in_c': 'hook_wave', 'hook_peek': 'hook_in_a'}, amt=0.08)


def hook_x(t):
    return 962 + (540 - 962) * ease((t - 1.0) / 1.55)


CARD_T = Drift([(SPIN_END, 'jump_calm'), (E.CARD_GRAB, 'card_in_a'), (E.CARD_GRAB + 0.45, 'card_1'),
                (E.CARD_GRAB + 0.9, 'card_in_b'), (E.CARD_GRAB + 1.35, 'card_2'), (E.CARD_SHOW, 'card_in_c'),
                (E.CARD_SHOW + 0.45, 'card_3')], dur=0.42,
               drift={'jump_calm': 'jump_notice', 'card_2': 'card_in_b', 'card_3': 'card_in_c'}, amt=0.12)
PUMP_SWING = ['pump_1', 'pump_in_a', 'pump_2', 'pump_in_b', 'pump_3']
LH = E.LOCKET_HIT
JUMP_T = anim.Track([(E.LOCKET - 0.25, 'jump_notice'), (LH - 0.5, 'jump_prep'), (LH - 0.24, 'jump_crouch'), (LH, 'jump_takeoff'),
                     (LH + 0.17, 'jump_peak'), (LH + 0.36, 'jump_fall'), (LH + 0.52, 'jump_land'), (LH + 0.82, 'jump_recover'),
                     (LH + 1.5, 'jump_calm')], dur=0.2)
CREEPY_T = V3.CREEPY_T
G0, G1, G2 = E.GACHA
RARE_T = Drift([(E.CREEPY_END, 'jump_calm'), (G0 - 0.25, 'show_in_a'), (G0 + 0.2, 'show_up'), (G2 + 0.35, 'show_end'),
                (E.TEASE - 0.1, 'think_1'), (E.TEASE + 0.45, 'think_2'), (E.TEASE + 1.2, 'think_3')], dur=0.45,
               drift={'show_up': 'show_in_a', 'show_end': 'jump_calm', 'think_2': 'think_1', 'think_3': 'think_2',
                      'jump_calm': 'jump_notice'}, amt=0.1)
I0, I1, I2 = E.ICONS
SHOW_T = Drift([(E.DEMAND, 'show_end'), (I0 - 0.05, 'show_left'), (I1 - 0.3, 'show_in_a'), (I1 + 0.12, 'show_up'),
                (I2 - 0.3, 'show_in_b'), (I2 + 0.12, 'show_right'), (E.GLOW - 0.45, 'show_end')], dur=0.45,
               drift={'show_left': 'show_in_a', 'show_up': 'show_in_a', 'show_right': 'show_in_b', 'show_end': 'jump_calm'},
               amt=0.1)
PHONE_T = Drift([(E.GLOW, 'phst_1'), (E.GLOW_PHONE - 0.25, 'phst_in_a'), (E.GLOW_PHONE + 0.25, 'phst_2'),
                 (E.GLOW_SHOW - 0.4, 'phst_in_b'), (E.GLOW_SHOW + 0.1, 'phst_3'), (E.PLAIN - 0.5, 'phst_hug')], dur=0.45,
                drift={'phst_1': 'phst_in_a', 'phst_2': 'phst_in_b', 'phst_3': 'phst_in_b'}, amt=0.08)
K = E.KICK
KICK_T = Drift([(E.PLAIN, 'kick_1'), (K - 0.4, 'kick_in_a'), (K - 0.15, 'kick_2'), (K + 0.04, 'kick_in_b'),
                (K + 0.18, 'kick_3'), (K + 0.7, 'kick_dust')], dur=0.22, drift={'kick_1': 'kick_in_a'}, amt=0.08)
P = E.PRICE
HANG_T = anim.Track([(P, 'hang_grab'), (P + 0.55, 'hang_tiptoe'), (P + 1.0, 'hang_lift'), (P + 1.45, 'hang_settle'),
                     (P + 1.9, 'hang_in_a')], dur=0.45)
HANG_SWING = ['hang_in_a', 'hang_1', 'hang_in_b', 'hang_3', 'hang_in_b', 'hang_1', 'hang_in_a', 'hang_2']
TWO_T = Drift([(E.OUTRO, 'two_1'), (E.OUTRO_LUX + 0.5, 'two_in_a'), (E.OUTRO_MIN + 0.1, 'two_2'),
               (E.OUTRO_MIN + 0.75, 'two_in_b'), (E.OUTRO_PILL - 0.55, 'two_3'), (E.OUTRO_PILL + 0.25, 'two_point')], dur=0.45,
              drift={'two_1': 'two_in_a', 'two_2': 'two_in_b', 'two_point': 'two_3'}, amt=0.07)
POP = ['pop_1', 'pop_in_a', 'pop_2', 'pop_in_b', 'pop_3', 'pop_in_b', 'pop_2', 'pop_in_a']

SCENES = [
    ('hook', 0.0), ('spin', E.SPIN - 0.12), ('card', SPIN_END), ('pumpkin', E.PUMPKIN - 0.15), ('jump', E.LOCKET - 0.25),
    ('creepy', E.CREEPY), ('rare', E.CREEPY_END), ('show', AD_STOP + 0.02), ('phone', E.GLOW - 0.2), ('kick', E.PLAIN),
    ('hang', E.PRICE), ('two', E.OUTRO),
]
CUT = {'creepy', 'rare'}


def scene_of(t):
    cur = SCENES[0]
    for sc in SCENES:
        if t >= sc[1]:
            cur = sc
    return cur


# ------------------------------------------------------------------ тыква
PUMP_C = (540, 1275)          # центр модели Red Demon на экране
PUMP_SIZE = 700


@functools.lru_cache(None)
def _unused_pumpkin_top():
    """Верх «купола» тыквы (без рожек) в долях кадра модели — для посадки Миты."""
    im = np.array(R.lottie.frame(R.model_path('Mad Pumpkin', 'Red Demon'), 0.0, size=480))
    col = im[:, 200:280, 3].max(1)
    ys = np.nonzero(col > 120)[0]
    return ys.min() / 480


PUMP_DUR, PUMP_FPS, PS = 3.0, 60, 240         # длительность Lottie тыквы, кадры, размер для анализа
SEAT_U = (0.25, 0.43)                          # окно поверхности под Митой (доли ширины модели, левее рожки по центру)


def _surface(a, x):
    """Верх «толстой» части тела в столбце x (рожки тонкие — пропускаются)."""
    c = a[:, x] > 120
    y = 0
    while y < PS:
        if c[y]:
            run = 0
            while y + run < PS and c[y + run]:
                run += 1
            if run >= PS // 8:
                return y
            y += run
        y += 1
    return None


@functools.lru_cache(None)
def pump_profile():
    """По каждому кадру анимации тыквы: высота поверхности под Митой, наклон, сдвиг тела по x, высота тела.
    Сглажено по времени (окно 5 кадров, по кругу), чтобы Мита не дрожала."""
    path = R.model_path('Mad Pumpkin', 'Red Demon')
    n = int(PUMP_DUR * PUMP_FPS)
    ys, sl, cx, hh = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    x0, x1 = int(PS * SEAT_U[0]), int(PS * SEAT_U[1])
    xm = (x0 + x1) / 2
    for i in range(n):
        a = np.array(R.lottie.frame(path, i / PUMP_FPS, size=PS))[..., 3]
        pts = [(x, _surface(a, x)) for x in range(x0, x1 + 1, 3)]
        Y = np.array([y for x, y in pts if y is not None], float)
        ys[i] = np.median(Y)
        # общий наклон тыквы: разница высот поверхности слева и справа от центра (без рожек)
        def mean_top(u0, u1):
            v = [_surface(a, x) for x in range(int(PS * u0), int(PS * u1), 2)]
            v = [y for y in v if y is not None]
            return float(np.median(v)) if v else ys[i]
        sl[i] = (mean_top(0.58, 0.66) - mean_top(0.34, 0.42)) / (0.24 * PS)
        cols = np.nonzero(a.max(0) > 120)[0]
        cx[i] = (cols.min() + cols.max()) / 2 - PS / 2
        rows = np.nonzero(a.max(1) > 120)[0]
        hh[i] = rows.max() - ys[i]
    sl -= np.median(sl)
    ker = np.hanning(9)[1:-1]
    ker /= ker.sum()
    sm = lambda v: np.convolve(np.concatenate([v[-3:], v, v[:3]]), ker, 'valid')
    return sm(ys), sm(sl), sm(cx), sm(hh), xm


def pump_state(t):
    ys, sl, cx, hh, xm = pump_profile()
    n = len(ys)
    f = (t % PUMP_DUR) * PUMP_FPS
    i = int(f) % n
    j = (i + 1) % n
    w = f - int(f)
    lerp = lambda v: v[i] * (1 - w) + v[j] * w
    return lerp(ys), lerp(sl), lerp(cx), lerp(hh), xm, float(np.median(hh))


CALM0, CALM_LEN, CALM_SPEED = 2.58, 0.72, 0.6     # спокойный кусок анимации (2,58 → 3,0 → 0,30 с, по кругу)


def pumpkin_time(t):
    """Время Lottie тыквы: только спокойный кусок, туда-обратно с плавными разворотами (без резких рывков)."""
    u = max(0.0, t - E.PUMPKIN + 0.2) * CALM_SPEED
    ph = (u / CALM_LEN) % 2.0
    x = CALM_LEN * (0.5 - 0.5 * math.cos(math.pi * ph))
    return (CALM0 + x) % PUMP_DUR


def pump_scale(t):
    return 0.92 + 0.08 * ease((t - E.PUMPKIN + 0.15) / 0.45)


def draw_pumpkin(cv, t, a):
    im = R.lottie.frame(R.model_path('Mad Pumpkin', 'Red Demon'), pumpkin_time(t), size=PUMP_SIZE)
    s = pump_scale(t)
    R.put(cv, shadow_sprite(), PUMP_C[0], PUMP_C[1] + PUMP_SIZE * 0.42, 1.6, 0.8 * a)
    R.put(cv, im, PUMP_C[0], PUMP_C[1], s, a)


def pumpkin_seat(t):
    """(x, y, наклон в радианах, сжатие) точки, где сидит Мита, — едет вместе с поверхностью тыквы.
    Небольшая инерция: Мита отстаёт от тыквы на ~0,04 с (её «подбрасывает» и она опускается обратно)."""
    k = PUMP_SIZE / PS * pump_scale(t)
    y_now, sl, cx, hh, xm, h0 = pump_state(pumpkin_time(t))
    y_lag = pump_state(pumpkin_time(t - 0.04))[0]
    y = 0.65 * y_now + 0.35 * y_lag
    X = PUMP_C[0] + (xm - PS / 2) * k + cx * k * 0.3
    Y = PUMP_C[1] + (y - PS / 2) * k
    ang = float(np.clip(math.atan(sl) * 0.7, -0.2, 0.2))
    squash = float(np.clip(hh / h0, 0.85, 1.12))
    return X, Y, ang, squash


# ------------------------------------------------------------------ Мита по сценам
def mita_frame(name, t):
    P_ = dict(cx=540.0, foot=FOOT, s=S0, base=BASE, rot=0.0, sx=1.0, sy=1.0, flip=False, shadow=True, reflect=0.0,
              tint=None, k=0.0, rim=None, rim_k=0.0, bright=1.0, anchor_x=None)
    by, bx = anim.breathe(t)
    P_['sy'] = by * (1 + 0.01 * R.talk(t))
    P_['rot'] = 0.007 * math.sin(t * 0.9)                     # лёгкое покачивание
    if name == 'hook':
        a = HOOK_T.frame(t)
        P_.update(cx=hook_x(t), base=HOOK_BASE)
        if t < 1.0:
            P_.update(shadow=False, rot=0.0)
        return a, P_
    if name == 'card':
        a = CARD_T.frame(t)
        if t >= E.CARD_GRAB - 0.3:
            a = anim.replace_magenta(a, cards_painter([V3._cup()]))
        return a, P_
    if name == 'pumpkin':
        u = t - E.PUMPKIN
        if t < E.PUMP_BLACK - 0.45:
            a = anim.pingpong(PUMP_SWING, max(0.0, u), 2.6)
        else:
            k = ease((t - (E.PUMP_BLACK - 0.45)) / 0.5)
            a = anim.morph(anim.pingpong_name(PUMP_SWING, E.PUMP_BLACK - 0.45 - E.PUMPKIN, 2.6), 'pump_point', k)
        sx_, sy_, ang, sq = pumpkin_seat(t)
        # сжатие тыквы → Мита слегка «проседает» (по вертикали сильнее, по ширине чуть шире)
        return a, dict(P_, cx=sx_, foot=sy_ + 34, base=570, shadow=False, sy=1 - 0.35 * (1 - sq), sx=1 + 0.12 * (1 - sq),
                       rot=ang)
    if name == 'jump':
        a = JUMP_T.frame(t)
        u = (t - LH) / 0.52
        if 0 < u < 1:
            P_['foot'] = FOOT - 70 * math.sin(math.pi * u)
        P_.update(sy=1.0, rot=0.0)
        return a, P_
    if name == 'creepy':
        a = CREEPY_T.frame(t)
        z = 1.0 + 0.08 * ease((t - E.CREEPY) / 1.7)
        return a, dict(P_, s=2.0 * z, foot=1960, base=1024, shadow=False, sy=1.0, rot=0.0, tint=(255, 60, 70), k=0.25,
                       bright=0.9, rim=(255, 40, 60), rim_k=0.8)
    if name == 'rare':
        return RARE_T.frame(t), P_
    if name == 'show':
        return SHOW_T.frame(t), P_
    if name == 'phone':
        a = PHONE_T.frame(t)
        if PHONE_T.name(t) != 'phst_1':
            a = anim.replace_magenta(a, phone_painter(t))
        return a, P_
    if name == 'kick':
        return KICK_T.frame(t), dict(P_, cx=470)
    if name == 'hang':
        return hang_mita(t, P_)
    if name == 'two':
        a = TWO_T.frame(t)
        a = anim.replace_magenta(a, cards_painter([lot3('Electric Skull', 'black_floor'), lot3('Snow Globe', 'floor')]))
        return a, P_
    return None, P_


def draw_new(cv, name, t, alpha=1.0):
    a, P_ = mita_frame(name, t)
    if a is None:
        return
    if name == 'pumpkin':
        draw_pumpkin(cv, t, alpha)
    if name == 'show':
        draw_orbit(cv, t, alpha, front=False)
    if name == 'rare':
        draw_carousel(cv, t, alpha, front=False)
    a = grade(a, P_['tint'], P_['k'], P_['rim'], P_['rim_k'], P_['bright'])
    put_mita(cv, a, P_['cx'], P_['foot'], P_['s'], P_['base'], alpha, P_['rot'], P_['sx'], P_['sy'], P_['shadow'],
             P_['reflect'], P_['flip'], P_['anchor_x'])
    if name == 'show':
        draw_orbit(cv, t, alpha, front=True)
    if name == 'rare':
        draw_carousel(cv, t, alpha, front=True)


def draw_mita(cv, t, old_draw):
    name, t0 = scene_of(t)
    if name == 'spin':
        if t < E.SPIN:
            k = ease((t - t0) / 0.12)
            draw_new(cv, 'hook', t, 1 - k)
            old_draw(cv, max(t, E.SPIN), alpha=k)
        else:
            old_draw(cv, t)
        return
    if name == 'card' and t < SPIN_END + 0.25:
        k = ease((t - SPIN_END) / 0.25)
        old_draw(cv, SPIN_END - 1e-3, alpha=1 - k)
        draw_new(cv, 'card', t, k)
        R.sparkles(cv, t, SPIN_END, 540, FOOT - 420, 340, 16, R.GOLD)
        return
    if name not in CUT and name != 'hook':
        prev = [s for s in SCENES if s[1] < t0]
        if prev and t < t0 + 0.35 and prev[-1][0] not in ('spin', 'creepy'):
            k = ease((t - t0) / 0.35)
            draw_new(cv, prev[-1][0], t0 - 1e-3, 1 - k)
            draw_new(cv, name, t, k)
            R.sparkles(cv, t, t0, 540, FOOT - 420, 320, 14, R.GOLD)
            return
    draw_new(cv, name, t)


# ------------------------------------------------------------------ карусель редкости (за Митой и перед ней)
CAROUSEL = ['Black', 'Sapphire', 'Burgundy', 'Celtic Blue', 'Copper', 'Ivory White']
STOPS = {0: G0, 2: G1, 4: G2}                   # индекс плитки → момент, когда она выезжает вперёд


def carousel_angle(t):
    """Угол кольца: крутится, на «чёрный/бордовый/медный» плавно останавливается так, чтобы плитка была спереди."""
    base = -math.pi / 2                          # «спереди» = угол π/2 (низ эллипса)
    spin = 1.1 * (t - E.CREEPY_END)
    for i, ts in sorted(STOPS.items(), key=lambda x: x[1]):
        target = math.pi / 2 - i * 2 * math.pi / len(CAROUSEL)
        k = ease((t - (ts - 0.45)) / 0.45) * (1 - ease((t - (ts + 0.55)) / 0.35))
        cur = base + spin
        tgt = target + 2 * math.pi * round((cur - target) / (2 * math.pi))
        if k > 0:
            return cur * (1 - k) + tgt * k
    return base + spin


def draw_carousel(cv, t, alpha, front):
    a = alpha * appear(t, E.CREEPY_END + 0.1, 0.4) * (1 - appear(t, E.TEASE - 0.2, 0.35))
    if a <= 0:
        return
    m = R.lot('Whip Cupcake', 'black_floor')['model']
    ang0 = carousel_angle(t)
    cx, cy, rx, ry = 540, 470, 360, 95
    items = []
    for i, bd in enumerate(CAROUSEL):
        th = ang0 + i * 2 * math.pi / len(CAROUSEL)
        depth = math.sin(th)                      # 1 = спереди
        if (depth > 0.15) != front:
            continue
        x, y = cx + rx * math.cos(th), cy + ry * depth
        s = 0.42 + 0.2 * (depth + 1) / 2
        hot = 0.0
        for j, ts in STOPS.items():
            if j == i:
                hot = max(hot, appear(t, ts - 0.1, 0.3) * (1 - appear(t, E.TEASE - 0.3, 0.3)))
        s *= 1 + 0.25 * hot * max(0.0, depth)
        items.append((depth, i, bd, x, y, s, hot))
    for depth, i, bd, x, y, s, hot in sorted(items):
        dim = 0.55 + 0.45 * (depth + 1) / 2
        sq = 0.75 + 0.25 * abs(math.cos(math.atan2(depth, 1)))      # лёгкий поворот плитки на краях кольца
        tile = R.gift_tile('Whip Cupcake', m, bd, R.TILE, t)
        R.put(cv, fx.soft_shadow(R.TILE, R.TILE, 46, 26, 0.4), x, y + 14 * s, s, a * dim * 0.8)
        fx.over(cv, fx.warp(tile, x, y, s * sq, s, 0.0), a * dim)
        if hot > 0.05 and depth > 0.3:
            R.put(cv, R.text(bd, 30, 'Heavy', R.WINE if bd == 'Black' else R.INK), x, y + 300 * s / 2 + 28, 1.0, a * hot)


# ------------------------------------------------------------------ спутники: карта, машина, смокинг
ORBIT = [('card', 230, 600, 0.95), ('car', 540, 450, 1.25), ('tux', 850, 600, 1.1)]


def draw_orbit(cv, t, alpha, front):
    a0 = alpha * appear(t, E.DEMAND + 0.05, 0.4) * (1 - appear(t, E.GLOW - 0.35, 0.3))
    if a0 <= 0:
        return
    cx, cy, rx, ry = 540, 1060, 420, 120
    om = 1.25
    for i, (name, sx, sy, sc) in enumerate(ORBIT):
        rel = E.ICONS[i] - 0.25
        th0 = -math.pi / 2 + i * 2 * math.pi / 3
        def orbit_pos(tt):
            th = th0 + om * (tt - E.DEMAND)
            return cx + rx * math.cos(th), cy + ry * math.sin(th), math.sin(th)
        if t < rel:
            x, y, depth = orbit_pos(t)
            s = sc * (0.45 + 0.25 * (depth + 1) / 2)
            is_front = depth > 0
            dim = 0.6 + 0.4 * (depth + 1) / 2
        else:
            x0, y0, d0 = orbit_pos(rel)
            k = ease((t - rel) / 0.6)
            x = x0 + (sx - x0) * k
            y = y0 + (sy - y0) * k - 90 * math.sin(math.pi * k) + 8 * math.sin(t * 2 + i) * k
            s0 = sc * (0.45 + 0.25 * (d0 + 1) / 2)
            s = s0 + (sc * 0.85 - s0) * k
            is_front = True
            dim = 1.0
        if is_front != front:
            continue
        im = R.prop_img(name)
        R.put(cv, R.spot_glow(), x, y + 10, s * 1.2, a0 * 0.35)
        R.put(cv, im, x, y, s, a0 * dim, 0.06 * math.sin(t * 1.3 + i) * (1 if t >= rel else 0))
        if t >= rel:
            R.put(cv, R.text(['карты', 'машины', 'смокинги'][i], 30, 'Heavy'), x, y + im.height * s / 2 + 30, 1.0,
                  a0 * appear(t, rel + 0.35, 0.3))
            R.sparkles(cv, t, rel + 0.5, sx, sy, 150, 10, R.GOLD)


# ------------------------------------------------------------------ график: плавный отрыв и качание
def tip(t):
    k = ease((t - E.PRICE - 0.95) / (E.PRICE_UP + 0.6 - E.PRICE - 0.95))
    return 600 + 40 * k, 770 + (360 - 770) * k


def hang_mita(t, P_):
    x, y = tip(t)
    if t < E.PRICE + 1.9:
        a = HANG_T.frame(t)
    else:
        a = anim.loop(HANG_SWING, t - E.PRICE - 1.9, 3.6)
    bar = biggest(anim.magenta(a)[1])
    a = anim.replace_magenta(a, lambda comps, shape: np.dstack([np.full(shape[:2], c, np.float32) for c in R.WINE + (255,)]))
    bx, by = bar['c'] if bar else (384, 40)
    return a, dict(P_, cx=x, foot=y, base=by, anchor_x=bx, sy=1.0, rot=0.0, shadow=t < E.PRICE + 0.9)


def graph_points(t):
    x, y = tip(t)
    f = [(0.0, 0.0), (0.18, 0.12), (0.32, 0.07), (0.48, 0.38), (0.64, 0.52), (0.82, 0.86), (1.0, 1.0)]
    return [(110 + (x - 110) * u, 1440 + (y - 1440) * v) for u, v in f]
