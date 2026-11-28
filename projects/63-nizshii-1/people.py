"""Люди «Низшего» кодом (часть 1 v2): скелетная кукла с позами и детальной отрисовкой.
Внешность — строго по книге (BOOK1-NOTES.md, главы 1–3): у каждого чужие конечности своего возраста и цвета,
кольцевые шрамы на стыках, номер на груди. Рисуется pycairo, вид спереди/3/4; лёжа — та же кукла, повёрнутая.

Кукла: pose — словарь суставов (пиксели), look — внешность. draw(ctx, pose, look, face) рисует фигуру."""
import math
import random
import kit
from kit import limb, blob, smooth_path, fill, stroke, soft_line, ellipse, rad, lin, shade, mixc

# ── палитра ────────────────────────────────────────────────────────────────
SKIN_TAN = (196, 146, 112)
SKIN_OLD = (190, 160, 140)      # старческие пришитые конечности Оди: бледные, сероватые
SKIN_DARK = (112, 74, 54)       # Йорка
SKIN_COAL = (44, 42, 48)        # антрацитово-чёрные ноги Йорки, чёрная рука №444
SKIN_PALE = (214, 186, 166)
SKIN_OLIVE = (170, 128, 96)
SKIN_YELLOW = (200, 172, 120)
SCAR = (176, 70, 66)
INK = (24, 20, 22)


def P(x, y):
    return (x, y)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def add(a, d):
    return (a[0] + d[0], a[1] + d[1])


def polar(p, L, ang):
    return (p[0] + L * math.cos(ang), p[1] + L * math.sin(ang))


# ── позы ───────────────────────────────────────────────────────────────────
def pose(x, y, h, kind='stand', t=0.0, **kw):
    """x,y — точка между стоп (пол), h — рост в пикселях. Возвращает словарь суставов.
    kind: stand, hips (руки в бока), crossed (руки скрещены), wall (сутулый у стены), sit_floor, sit_bench,
    kneel, walk (t — фаза), carry (ведро в правой), reach (тянется правой вперёд-вверх), slap (замах)."""
    u = h / 7.6                                     # «голова»
    sw = kw.get('sw', 1.0)                          # ширина плеч
    hw = kw.get('hw', 1.0)
    lean = kw.get('lean', 0.0)                      # наклон корпуса (рад)
    breath = math.sin(t * 2 * math.pi / 4.2) * 0.012 * u * 8
    hipy = y - u * 3.75
    sh_y = y - u * 6.05 + breath * 0.3
    cx = x
    j = {}
    j['hipL'], j['hipR'] = (cx + u * 0.62 * hw, hipy), (cx - u * 0.62 * hw, hipy)
    tilt = kw.get('tilt', 0.0)
    j['neck'] = (cx + math.sin(lean) * u * 2.3, sh_y - u * 0.25)
    # руки крепятся под дельтой (пришитые конечности растут из мускулистого плеча)
    att = kw.get('att', 1.08)
    j['shL'] = (cx + u * att * sw + math.sin(lean) * u * 2.2, sh_y + u * 0.3 + tilt * u * 0.3)
    j['shR'] = (cx - u * att * sw + math.sin(lean) * u * 2.2, sh_y + u * 0.3 - tilt * u * 0.3)
    j['sw'] = sw
    j['head'] = (j['neck'][0] + kw.get('head_dx', 0) * u, j['neck'][1] - u * 0.78 + kw.get('head_dy', 0) * u)
    j['head_tilt'] = kw.get('head_tilt', 0.0)
    ua, fa = u * 1.3, u * 1.24                      # плечо (от дельты), предплечье
    th, sh = u * 1.86, u * 1.8                      # бедро, голень

    def arm(side, a1, a2):
        s = j['sh' + side]
        e = polar(s, ua, a1)
        w = polar(e, fa, a2)
        j['el' + side], j['wr' + side] = e, w

    def leg(side, a1, a2):
        hp = j['hip' + side]
        k = polar(hp, th, a1)
        a = polar(k, sh, a2)
        j['kn' + side], j['an' + side] = k, a

    D = math.pi / 2
    if kind in ('stand', 'wall'):
        sway = math.sin(t * 2 * math.pi / 5.0) * 0.02
        arm('L', D - 0.16 + sway, D - 0.08)
        arm('R', D + 0.16 - sway, D + 0.08)
        leg('L', D - 0.06, D - 0.02)
        leg('R', D + 0.06, D + 0.02)
    elif kind == 'hips':
        arm('L', D - 0.95, D + 1.35)
        arm('R', D + 0.95, D - 1.35)
        leg('L', D - 0.1, D - 0.03)
        leg('R', D + 0.1, D + 0.03)
    elif kind == 'crossed':
        arm('L', D - 0.08, math.pi - 0.32)
        arm('R', D + 0.08, 0.32)
        leg('L', D - 0.12, D - 0.04)
        leg('R', D + 0.12, D + 0.04)
    elif kind == 'reach':
        arm('L', D - 0.12, D - 0.05)
        arm('R', -D + 1.15, -D + 0.95)
        leg('L', D - 0.06, D)
        leg('R', D + 0.1, D + 0.05)
    elif kind == 'slap':
        u2 = kw.get('swing', 0.0)
        arm('L', D - 0.15, D - 0.05)
        arm('R', D + 1.9 - u2 * 1.6, D + 2.3 - u2 * 2.2)
        leg('L', D - 0.08, D)
        leg('R', D + 0.1, D + 0.04)
    elif kind == 'walk':
        ph = t * 2 * math.pi
        s = math.sin(ph)
        arm('L', D + 0.28 * s, D + 0.12 * s - 0.15)
        arm('R', D - 0.28 * s, D - 0.12 * s - 0.15)
        leg('L', D - 0.3 * s, D - 0.3 * s + max(0, math.sin(ph + 0.9)) * 0.5)
        leg('R', D + 0.3 * s, D + 0.3 * s + max(0, math.sin(ph + math.pi + 0.9)) * 0.5)
        bob = abs(math.cos(ph)) * u * 0.08
        for k_ in list(j):
            if isinstance(j[k_], tuple):
                j[k_] = (j[k_][0], j[k_][1] - bob)
    elif kind == 'carry':
        arm('L', D - 0.35, D - 0.75)                # больной локоть прижат
        arm('R', D + 0.02, D + 0.0)
        leg('L', D - 0.12, D - 0.02)
        leg('R', D + 0.14, D + 0.04)
    elif kind == 'sit_floor':
        for k_ in ('hipL', 'hipR'):
            j[k_] = (j[k_][0], y - u * 0.5)
        dy = (y - u * 0.5) - hipy
        for k_ in ('neck', 'shL', 'shR', 'head'):
            j[k_] = (j[k_][0], j[k_][1] + dy)
        arm('L', D - 0.25, D - 0.55)
        arm('R', D + 0.4, D + 1.2)
        leg('L', -0.9, D + 0.55)
        leg('R', math.pi + 0.9, D - 0.55)
    elif kind == 'sit_bench':
        for k_ in ('hipL', 'hipR'):
            j[k_] = (j[k_][0], y - u * 2.0)
        dy = (y - u * 2.0) - hipy
        for k_ in ('neck', 'shL', 'shR', 'head'):
            j[k_] = (j[k_][0], j[k_][1] + dy)
        arm('L', D - 0.2, D + 0.35)
        arm('R', D + 0.2, D - 0.35)
        leg('L', D - 0.55, D - 0.05)
        leg('R', D + 0.55, D + 0.05)
    elif kind == 'kneel':
        for k_ in ('hipL', 'hipR'):
            j[k_] = (j[k_][0], y - u * 1.9)
        dy = (y - u * 1.9) - hipy
        for k_ in ('neck', 'shL', 'shR', 'head'):
            j[k_] = (j[k_][0], j[k_][1] + dy)
        arm('L', D - 0.4, D + 0.2)
        arm('R', D + 0.3, D - 0.1)
        leg('L', D - 0.2, D + 1.5)
        leg('R', D + 0.25, D + 1.45)
    # ручные правки углов: kw['arms'] = {'L': (a1, a2)} …
    for side, (a1, a2) in kw.get('arms', {}).items():
        arm(side, a1, a2)
    for side, (a1, a2) in kw.get('legs', {}).items():
        leg(side, a1, a2)
    j['u'] = u
    j['kind'] = kind
    return j


# ── внешность ──────────────────────────────────────────────────────────────
def look(**kw):
    d = dict(torso=SKIN_TAN, head=None, build='muscle', female=False,
             arms={'L': ('old', SKIN_OLD), 'R': ('old', SKIN_OLD)},
             legs={'L': ('old', SKIN_OLD), 'R': ('old', SKIN_OLD)},
             shorts=(46, 48, 54), top=None, number=None, num_pos='pec', hair=('buzz', (30, 26, 24)),
             beard=None, eyes=(70, 56, 44), scars=[], swollen_elbow=None, barcode=False, ring_scars=True,
             pouch=False, belt=None, nails_black=False, dry=0.0, finger_miss=False, spine=0.0, bottle=False)
    d.update(kw)
    if d['head'] is None:
        d['head'] = d['torso']
    return d


ODI = look(number='11', barcode=True, swollen_elbow='L', nails_black=True, finger_miss=True,
           hair=('buzz', (34, 28, 26)), beard=('stubble', (40, 32, 30)), eyes=(84, 92, 96))
YORKA = look(torso=SKIN_DARK, build='slim', female=True,
             arms={'L': ('female', SKIN_DARK), 'R': None},
             legs={'L': ('athletic', SKIN_COAL), 'R': ('athletic', SKIN_COAL)},
             shorts=(52, 50, 48), top=('tank', (96, 98, 96)), number='91', num_pos='collar',
             hair=('ragged', (18, 16, 18)), eyes=(44, 30, 24),
             scars=['cheekR', 'forehead', 'eyeL', 'lips'], pouch=True)


# ── части тела ─────────────────────────────────────────────────────────────
ARM_W = {'old': (0.30, 0.24, 0.22), 'muscle': (0.50, 0.40, 0.26), 'strong': (0.46, 0.38, 0.25),
         'female': (0.30, 0.25, 0.19), 'normal': (0.36, 0.30, 0.22), 'thin': (0.27, 0.22, 0.19)}
LEG_W = {'old': (0.46, 0.30, 0.24), 'muscle': (0.74, 0.50, 0.30), 'athletic': (0.66, 0.46, 0.27),
         'normal': (0.60, 0.40, 0.27), 'thin': (0.44, 0.30, 0.22), 'strong': (0.70, 0.48, 0.29)}


def ring_scar(ctx, p, d, w, u):
    """кольцевой шрам поперёк конечности в точке p, направление оси d"""
    L = math.hypot(*d) or 1
    nx, ny = -d[1] / L, d[0] / L
    a = (p[0] + nx * w * 0.56, p[1] + ny * w * 0.56)
    b = (p[0] - nx * w * 0.56, p[1] - ny * w * 0.56)
    mid = (p[0] + d[0] / L * u * 0.05, p[1] + d[1] / L * u * 0.05)
    ctx.move_to(*a)
    ctx.curve_to(mid[0] + nx * w * 0.2, mid[1] + ny * w * 0.2, mid[0] - nx * w * 0.2, mid[1] - ny * w * 0.2, *b)
    stroke(ctx, SCAR, u * 0.09, 0.85)
    ctx.move_to(*a)
    ctx.curve_to(mid[0] + nx * w * 0.2, mid[1] + ny * w * 0.2, mid[0] - nx * w * 0.2, mid[1] - ny * w * 0.2, *b)
    stroke(ctx, (230, 140, 130), u * 0.025, 0.7)
    for k in range(6):                               # стежки
        t = (k + 0.5) / 6
        q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        ctx.move_to(q[0] - d[0] / L * u * 0.07, q[1] - d[1] / L * u * 0.07)
        ctx.line_to(q[0] + d[0] / L * u * 0.07, q[1] + d[1] / L * u * 0.07)
        stroke(ctx, (90, 30, 30), u * 0.018, 0.8)


def wrinkles(ctx, p, d, w, u, n=4, col=None, a=0.35):
    L = math.hypot(*d) or 1
    ux, uy = d[0] / L, d[1] / L
    nx, ny = -uy, ux
    for k in range(n):
        o = (k - n / 2) * u * 0.055
        c = (p[0] + ux * o, p[1] + uy * o)
        ww = w * (0.32 - abs(k - n / 2) * 0.03)
        pts = [(c[0] + nx * ww, c[1] + ny * ww), (c[0] + ux * u * 0.02, c[1] + uy * u * 0.02),
               (c[0] - nx * ww, c[1] - ny * ww)]
        soft_line(ctx, pts, col or (60, 40, 36), u * 0.012, a)


def veins(ctx, p0, p1, w, u, seed=1, col=(96, 110, 150)):
    import random
    r = random.Random(seed)
    for k in range(2):
        pts = []
        off = (r.random() - 0.5) * w * 0.5
        for i in range(6):
            t = 0.15 + i / 7
            q = lerp(p0, p1, t)
            L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
            nx, ny = -(p1[1] - p0[1]) / L, (p1[0] - p0[0]) / L
            o = off + math.sin(i * 1.7 + seed + k) * w * 0.12
            pts.append((q[0] + nx * o, q[1] + ny * o))
        soft_line(ctx, pts, col, u * 0.016, 0.35)


def spots(ctx, p0, p1, w, u, seed=3, n=6):
    import random
    r = random.Random(seed)
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1
    nx, ny = -(p1[1] - p0[1]) / L, (p1[0] - p0[0]) / L
    for _ in range(n):
        t = r.random()
        o = (r.random() - 0.5) * w * 0.7
        q = lerp(p0, p1, t)
        ellipse(ctx, q[0] + nx * o, q[1] + ny * o, u * (0.02 + r.random() * 0.025), u * (0.016 + r.random() * 0.02))
        fill(ctx, (120, 84, 60), 0.4)


def hand(ctx, wr, d, u, color, kind='relaxed', side='L', old=False, finger_miss=False, scale=1.0):
    """кисть: d — направление предплечья (от локтя к запястью)"""
    L = math.hypot(*d) or 1
    ux, uy = d[0] / L, d[1] / L
    nx, ny = -uy, ux
    s = u * scale
    if side == 'R':
        nx, ny = -nx, -ny
    palm_len = s * 0.42
    pw = s * (0.26 if old else 0.3)
    c0 = (wr[0] + ux * s * 0.04, wr[1] + uy * s * 0.04)
    if kind == 'fist':
        blob(ctx, c0[0] + ux * s * 0.2, c0[1] + uy * s * 0.2, s * 0.2, s * 0.17, color, math.atan2(uy, ux))
        for k in range(4):
            o = (k - 1.5) * s * 0.085
            q = (c0[0] + ux * s * 0.33 + nx * o, c0[1] + uy * s * 0.33 + ny * o)
            blob(ctx, q[0], q[1], s * 0.05, s * 0.045, shade(color, 0.92), outline=True)
        return
    # ладонь
    pts = [(c0[0] + nx * pw * 0.5, c0[1] + ny * pw * 0.5),
           (c0[0] + ux * palm_len + nx * pw * 0.55, c0[1] + uy * palm_len + ny * pw * 0.55),
           (c0[0] + ux * palm_len - nx * pw * 0.5, c0[1] + uy * palm_len - ny * pw * 0.5),
           (c0[0] - nx * pw * 0.48, c0[1] - ny * pw * 0.48)]
    kit.volume_fill(ctx, pts, c0, (c0[0] + ux * palm_len, c0[1] + uy * palm_len), pw, color)
    smooth_path(ctx, pts)
    stroke(ctx, shade(color, 0.3), 1.2, 0.5)
    spread = {'relaxed': 0.06, 'open': 0.22, 'grip': 0.0, 'point': 0.05, 'middle': 0.0}[kind]
    curl = {'relaxed': 0.35, 'open': 0.0, 'grip': 1.3, 'point': 0.0, 'middle': 1.4}[kind]
    lens = [0.36, 0.42, 0.4, 0.32]
    base_ang = math.atan2(uy, ux)
    for k in range(4):
        o = (k - 1.5) / 1.5
        b = (c0[0] + ux * palm_len + nx * o * pw * 0.42, c0[1] + uy * palm_len + ny * o * pw * 0.42)
        ang = base_ang + o * spread * (1 if side == 'L' else -1)
        c = curl
        if kind == 'middle' and k == 1:
            c = -0.1
        if kind == 'point' and k == 3:
            c = 0.0
        ln = s * lens[k] * (0.96 if old else 1)
        if finger_miss and k == 0 and side == 'L':
            ln *= 0.62
        m = polar(b, ln * 0.52, ang + c * 0.6 * (1 if side == 'L' else -1))
        e = polar(m, ln * 0.48, ang + c * 1.2 * (1 if side == 'L' else -1))
        fw = s * (0.085 if old else 0.095)
        limb(ctx, b, m, fw, fw * 0.9, color, outline=True)
        limb(ctx, m, e, fw * 0.9, fw * 0.75, color, outline=True)
        if old:
            blob(ctx, b[0], b[1], fw * 0.55, fw * 0.5, shade(color, 1.05), outline=False)
        # ноготь
        ellipse(ctx, e[0] - ux * fw * 0.2, e[1] - uy * fw * 0.2, fw * 0.28, fw * 0.22, ang)
        fill(ctx, shade(color, 1.18), 0.6)
    # большой палец
    tb = (c0[0] + ux * palm_len * 0.35 + nx * pw * 0.52, c0[1] + uy * palm_len * 0.35 + ny * pw * 0.52)
    tang = base_ang + 0.7 * (1 if side == 'L' else -1)
    tm = polar(tb, s * 0.2, tang)
    te = polar(tm, s * 0.16, tang - 0.3 * (1 if side == 'L' else -1) + (0.8 if kind == 'grip' else 0))
    limb(ctx, tb, tm, s * 0.11, s * 0.1, color)
    limb(ctx, tm, te, s * 0.1, s * 0.08, color)
    if old:  # сухожилия на тыльной стороне
        for k in range(3):
            o = (k - 1) * pw * 0.28
            soft_line(ctx, [(c0[0] + nx * o * 0.6, c0[1] + ny * o * 0.6),
                            (c0[0] + ux * palm_len * 0.9 + nx * o, c0[1] + uy * palm_len * 0.9 + ny * o)],
                      shade(color, 0.7), s * 0.012, 0.4, smooth=False)


def foot(ctx, an, u, color, side='L', black_nails=False, angle=None):
    s = u
    dirx = 1 if side == 'L' else -1
    x, y = an
    # стопа спереди-сверху: пятка скрыта, видна тыльная сторона и пальцы
    pts = [(x - s * 0.16, y - s * 0.05), (x + s * 0.16, y - s * 0.05),
           (x + s * 0.22 + dirx * s * 0.05, y + s * 0.3), (x - s * 0.2 + dirx * s * 0.05, y + s * 0.32)]
    kit.volume_fill(ctx, pts, (x, y), (x + dirx * s * 0.04, y + s * 0.32), s * 0.4, color)
    smooth_path(ctx, pts)
    stroke(ctx, shade(color, 0.3), 1.2, 0.5)
    for k in range(5):
        o = (k - 2) / 2 * dirx
        tx = x + dirx * s * 0.04 + o * s * 0.16
        ty = y + s * 0.33 + (abs(o) * s * 0.03)
        r = s * (0.065 if k in ((0, 4)[side == 'R'],) else 0.045)
        blob(ctx, tx, ty, r, r * 0.9, color, outline=True)
        ellipse(ctx, tx, ty + r * 0.25, r * 0.6, r * 0.45)
        fill(ctx, (30, 26, 28) if black_nails else shade(color, 1.15), 0.85 if black_nails else 0.5)
    # сухожилия
    for k in range(3):
        o = (k - 1) * s * 0.07
        soft_line(ctx, [(x + o * 0.5, y), (x + dirx * s * 0.03 + o * 1.4, y + s * 0.27)], shade(color, 0.72),
                  s * 0.012, 0.35, smooth=False)


def draw_limb_set(ctx, j, side, kind, lk, which):
    u = j['u']
    if which == 'arm':
        spec = lk['arms'].get(side)
        a, b, c = j['sh' + side], j['el' + side], j['wr' + side]
        W = ARM_W
    else:
        spec = lk['legs'].get(side)
        a, b, c = j['hip' + side], j['kn' + side], j['an' + side]
        W = LEG_W
    if spec is None:                                 # культя
        if which == 'arm':
            d = (b[0] - a[0], b[1] - a[1])
            e = lerp(a, b, 0.18)
            limb(ctx, a, e, u * 0.42, u * 0.36, lk['torso'], rim=0.4)
            blob(ctx, e[0], e[1], u * 0.19, u * 0.16, shade(lk['torso'], 0.95), outline=True)
            soft_line(ctx, [(e[0] - u * 0.13, e[1]), (e[0], e[1] + u * 0.05), (e[0] + u * 0.13, e[1])],
                      shade(lk['torso'], 0.6), u * 0.02, 0.6)
        return
    typ, col = spec
    w1, w2, w3 = [v * u for v in W[typ]]
    old = typ == 'old'
    muscled = typ in ('muscle', 'strong', 'athletic')
    if which == 'arm':
        limb(ctx, a, b, w1, w2, col, bulge=0.22 if muscled else 0.04, bpos=0.4, rim=0.7)
        sw = lk.get('swollen_elbow') == side
        limb(ctx, b, c, w2 * (1.05 if muscled else 1), w3, col, bulge=0.25 if muscled else 0.06, bpos=0.25,
             rim=0.7)
        if old:
            blob(ctx, b[0], b[1], w2 * 0.62, w2 * 0.55, shade(col, 1.02), outline=False)
            wrinkles(ctx, b, (c[0] - a[0], c[1] - a[1]), w2, u, 5)
            veins(ctx, b, c, w2, u, seed=hash(side) % 7)
            spots(ctx, a, c, w2, u, seed=len(side) + 3)
        if sw:
            sw_c = lerp(b, c, 0.06)
            g = rad(sw_c[0], sw_c[1], 0, u * 0.48, [(0, (160, 70, 110), 0.95), (0.55, (92, 60, 130), 0.9),
                                                    (0.85, (120, 90, 120), 0.6), (1, (150, 110, 110), 0)])
            ellipse(ctx, sw_c[0], sw_c[1], u * 0.46, u * 0.4)
            ctx.set_source(g)
            ctx.fill()
            blob(ctx, sw_c[0], sw_c[1], u * 0.3, u * 0.27, (98, 70, 150), outline=True)
            ellipse(ctx, sw_c[0] - u * 0.09, sw_c[1] - u * 0.1, u * 0.08, u * 0.05, -0.5)
            fill(ctx, (230, 210, 255), 0.45)
        d = (c[0] - b[0], c[1] - b[1])
        hk = lk.get('hand_' + side, 'relaxed')
        hand(ctx, c, d, u, col, hk, side, old, lk.get('finger_miss') and side == 'L')
    else:
        limb(ctx, a, b, w1, w2, col, bulge=0.18 if muscled else 0.02, bpos=0.35, rim=0.6)
        limb(ctx, b, c, w2, w3, col, bulge=0.3 if muscled else 0.08, bpos=0.28, bside=0.3, rim=0.6)
        blob(ctx, b[0], b[1], w2 * (0.62 if old else 0.5), w2 * (0.6 if old else 0.48), shade(col, 1.03),
             outline=old)
        if old:
            wrinkles(ctx, b, (c[0] - a[0], c[1] - a[1]), w2, u, 4)
            spots(ctx, b, c, w3 * 1.4, u, seed=7 + len(side), n=5)
            veins(ctx, b, c, w3 * 1.2, u, seed=4)
        else:
            # коленная чашечка, мышцы бедра
            soft_line(ctx, [lerp(a, b, 0.35), lerp(a, b, 0.75), b], shade(col, 0.72), u * 0.02, 0.35)
        foot(ctx, c, u, col, side, lk.get('nails_black') and old)
    if lk.get('ring_scars', True):
        d = (b[0] - a[0], b[1] - a[1])
        ring_scar(ctx, lerp(a, b, 0.07), d, w1, u)


def torso(ctx, j, lk):
    u = j['u']
    shL, shR, hL, hR, nk = j['shL'], j['shR'], j['hipL'], j['hipR'], j['neck']
    col = lk['torso']
    fem = lk['female']
    muscle = lk['build'] == 'muscle'
    wid = abs(shL[0] - shR[0])
    mid = lerp(shL, shR, 0.5)
    hmid = lerp(hL, hR, 0.5)
    waist = lerp(mid, hmid, 0.72)
    ww = abs(hL[0] - hR[0]) * (0.92 if muscle else 0.86)
    # шея
    limb(ctx, (nk[0], nk[1] + u * 0.3), (j['head'][0], j['head'][1] + u * 0.3), u * (0.62 if muscle else 0.46),
         u * (0.56 if muscle else 0.42), lk['head'], rim=0.6)
    pts = [shL, (shL[0] - u * 0.06, shL[1] + u * 0.55), (mid[0] + wid * 0.46, mid[1] + u * 1.2),
           (waist[0] + ww * 0.5, waist[1]), (hL[0] + u * 0.1, hL[1] + u * 0.15),
           (hR[0] - u * 0.1, hR[1] + u * 0.15), (waist[0] - ww * 0.5, waist[1]),
           (mid[0] - wid * 0.46, mid[1] + u * 1.2), (shR[0] + u * 0.06, shR[1] + u * 0.55), shR,
           (nk[0] - u * 0.45, nk[1] + u * 0.18), (nk[0] + u * 0.45, nk[1] + u * 0.18)]
    kit.volume_fill(ctx, pts, mid, hmid, wid, col, rim=0.7)
    # общий объём: тень по бокам
    g = lin(mid[0] - wid * 0.55, 0, mid[0] + wid * 0.55, 0, [(0, (10, 18, 26), 0.28), (0.25, (0, 0, 0), 0),
                                                            (0.7, (0, 0, 0), 0), (1, (10, 18, 30), 0.42)])
    smooth_path(ctx, pts)
    ctx.set_source(g)
    ctx.fill()
    dk = shade(col, 0.55)
    if muscle and not fem:
        # дельты
        for s, sh in (('L', shL), ('R', shR)):
            sx = 1 if s == 'L' else -1
            blob(ctx, sh[0] - sx * u * 0.08, sh[1] + u * 0.32, u * 0.4, u * 0.5, col, rot=sx * 0.3, outline=False)
        # грудные
        for sx in (1, -1):
            c = (mid[0] + sx * wid * 0.22, mid[1] + u * 0.78)
            g = rad(c[0], c[1] - u * 0.15, 0, u * 0.9, [(0, shade(col, 1.08), 1), (0.6, col, 0.0), (1, col, 0)])
            ellipse(ctx, c[0], c[1], wid * 0.25, u * 0.55)
            ctx.set_source(g)
            ctx.fill()
            soft_line(ctx, [(mid[0] + sx * u * 0.06, mid[1] + u * 1.3), (c[0], c[1] + u * 0.58),
                            (c[0] + sx * wid * 0.2, c[1] + u * 0.25)], dk, u * 0.035, 0.6)
            ellipse(ctx, c[0] + sx * u * 0.1, c[1] + u * 0.28, u * 0.045, u * 0.04)
            fill(ctx, shade(col, 0.6), 0.7)
        # ключицы
        for sx in (1, -1):
            soft_line(ctx, [(nk[0] + sx * u * 0.12, nk[1] + u * 0.32), (nk[0] + sx * u * 0.6, nk[1] + u * 0.28),
                            (nk[0] + sx * u * 1.0, nk[1] + u * 0.22)], dk, u * 0.022, 0.45)
        # пресс
        top = (mid[0], mid[1] + u * 1.42)
        bot = (hmid[0], hmid[1] - u * 0.15)
        soft_line(ctx, [top, lerp(top, bot, 0.5), bot], dk, u * 0.03, 0.5)
        for k in range(3):
            y0 = top[1] + (bot[1] - top[1]) * (0.12 + k * 0.24)
            for sx in (1, -1):
                soft_line(ctx, [(top[0] + sx * u * 0.06, y0), (top[0] + sx * u * 0.3, y0 + u * 0.04),
                                (top[0] + sx * u * 0.48, y0 - u * 0.02)], dk, u * 0.026, 0.42)
                bx = top[0] + sx * u * 0.25
                g = rad(bx - u * 0.05, y0 + u * 0.18, 0, u * 0.25, [(0, shade(col, 1.07), 0.8), (1, col, 0)])
                ellipse(ctx, bx, y0 + u * 0.2, u * 0.22, u * 0.18)
                ctx.set_source(g)
                ctx.fill()
        # косые и «v»
        for sx in (1, -1):
            soft_line(ctx, [(waist[0] + sx * ww * 0.42, waist[1] - u * 0.4), (hmid[0] + sx * u * 0.35, hmid[1] + u * 0.05)],
                      dk, u * 0.03, 0.45)
            for k in range(3):
                y0 = mid[1] + u * (1.3 + k * 0.28)
                soft_line(ctx, [(mid[0] + sx * wid * 0.36, y0), (mid[0] + sx * wid * 0.44, y0 + u * 0.1)], dk,
                          u * 0.018, 0.35)
        ellipse(ctx, hmid[0], hmid[1] - u * 0.55, u * 0.05, u * 0.07)
        fill(ctx, shade(col, 0.45), 0.8)
    elif fem:
        for sx in (1, -1):
            c = (mid[0] + sx * wid * 0.2, mid[1] + u * 0.95)
            blob(ctx, c[0], c[1], wid * 0.17, u * 0.38, col, outline=False)
        soft_line(ctx, [(nk[0] - u * 0.5, nk[1] + u * 0.3), (nk[0], nk[1] + u * 0.4), (nk[0] + u * 0.5, nk[1] + u * 0.3)],
                  dk, u * 0.02, 0.4)
    else:                                              # худой: рёбра
        for k in range(4):
            for sx in (1, -1):
                y0 = mid[1] + u * (1.0 + k * 0.28)
                soft_line(ctx, [(mid[0] + sx * u * 0.25, y0), (mid[0] + sx * wid * 0.38, y0 + u * 0.12)], dk,
                          u * 0.02, 0.4)
    if lk.get('dry', 0) > 0:                          # обезвоженная дряблая кожа (первые сцены)
        import random
        r = random.Random(5)
        for _ in range(int(40 * lk['dry'])):
            x = mid[0] + (r.random() - 0.5) * wid * 0.8
            y = mid[1] + u * (0.4 + r.random() * 2.6)
            soft_line(ctx, [(x - u * 0.08, y), (x, y + u * 0.015), (x + u * 0.08, y)], shade(col, 0.6), u * 0.008, 0.4)
    return mid, wid


def number(ctx, j, lk, mid, wid):
    if not lk.get('number'):
        return
    u = j['u']
    ctx.save()
    if lk['num_pos'] == 'collar':
        x, y, size = mid[0], mid[1] + u * 0.25, u * 0.34
    else:  # левая грудная мышца (слева для зрителя — правая часть экрана у фигуры, смотрящей на нас)
        x, y, size = mid[0] + wid * 0.22, mid[1] + u * 0.7, u * 0.46
    ctx.select_font_face('DejaVu Sans', 0, 1)
    ctx.set_font_size(size)
    ext = ctx.text_extents(lk['number'])
    ctx.move_to(x - ext.width / 2 - ext.x_bearing, y + ext.height / 2)
    ctx.text_path(lk['number'])
    ctx.set_source_rgba(*kit.rgb((22, 22, 26), 0.82))
    ctx.fill()
    ctx.restore()


def barcode(ctx, j):
    u = j['u']
    sh = j['shR']
    x0, y0 = sh[0] + u * 0.05, sh[1] + u * 0.2
    import random
    r = random.Random(11)
    x = x0 - u * 0.22
    for _ in range(16):
        w = u * (0.012 + r.random() * 0.02)
        ctx.rectangle(x, y0, w, u * 0.34)
        x += w + u * 0.012
    fill(ctx, INK, 0.75)


def shorts(ctx, j, lk):
    u = j['u']
    hL, hR = j['hipL'], j['hipR']
    kL, kR = j['knL'], j['knR']
    col = lk['shorts']
    top = min(hL[1], hR[1]) - u * 0.25
    for side, h, k in (('L', hL, kL), ('R', hR, kR)):
        end = lerp(h, k, 0.38)
        w = u * 0.9
        limb(ctx, (h[0], h[1] - u * 0.05), end, w, w * 0.92, col, rim=0.4)
        soft_line(ctx, [lerp(h, k, 0.1), lerp(h, k, 0.28)], shade(col, 0.6), u * 0.025, 0.5)
    pts = [(hL[0] + u * 0.42, top), (hL[0] + u * 0.46, hL[1] + u * 0.3), ((hL[0] + hR[0]) / 2, hL[1] + u * 0.5),
           (hR[0] - u * 0.46, hR[1] + u * 0.3), (hR[0] - u * 0.42, top)]
    kit.volume_fill(ctx, pts, ((hL[0] + hR[0]) / 2, top), ((hL[0] + hR[0]) / 2, hL[1] + u * 0.5), u * 1.6, col)
    # широкая резинка
    ctx.rectangle(hR[0] - u * 0.44, top, (hL[0] - hR[0]) + u * 0.88, u * 0.2)
    fill(ctx, shade(col, 0.75))
    for k in range(10):
        x = hR[0] - u * 0.4 + k * ((hL[0] - hR[0]) + u * 0.8) / 9
        ctx.move_to(x, top + u * 0.02)
        ctx.line_to(x, top + u * 0.18)
        stroke(ctx, shade(col, 0.55), u * 0.012, 0.6)
    # складки
    for k in range(3):
        x = (hL[0] + hR[0]) / 2 + (k - 1) * u * 0.35
        soft_line(ctx, [(x, top + u * 0.3), (x + u * 0.05, top + u * 0.6), (x - u * 0.02, top + u * 0.9)],
                  shade(col, 0.55), u * 0.02, 0.4)
    if lk.get('pouch'):                               # самодельная поясная сумка Йорки
        px, py = hR[0] - u * 0.1, top + u * 0.25
        ctx.rectangle(px - u * 0.22, py, u * 0.44, u * 0.36)
        fill(ctx, (78, 66, 50))
        ctx.rectangle(px - u * 0.22, py, u * 0.44, u * 0.12)
        fill(ctx, (62, 52, 40))
        for k in range(5):
            ctx.move_to(px - u * 0.2 + k * u * 0.1, py + u * 0.34)
            ctx.line_to(px - u * 0.2 + k * u * 0.1 + u * 0.04, py + u * 0.36)
            stroke(ctx, (40, 34, 26), u * 0.012, 0.8)
    belt = lk.get('belt')
    if belt:
        ctx.rectangle(hR[0] - u * 0.44, top - u * 0.02, (hL[0] - hR[0]) + u * 0.88, u * 0.12)
        fill(ctx, (20, 20, 22))
        if belt == 'baton':
            bx = hL[0] + u * 0.4
            limb(ctx, (bx, top + u * 0.05), (bx + u * 0.15, top + u * 1.4), u * 0.12, u * 0.11, (24, 24, 28), rim=0.9)


def top(ctx, j, lk, mid, wid):
    t = lk.get('top')
    if not t:
        return
    kind, col = t
    u = j['u']
    shL, shR, hL, hR = j['shL'], j['shR'], j['hipL'], j['hipR']
    hmid = lerp(hL, hR, 0.5)
    if kind == 'tank':
        pts = [(shL[0] - u * 0.35, shL[1] - u * 0.05), (shL[0] - u * 0.15, shL[1] + u * 0.55),
               (mid[0] + wid * 0.42, mid[1] + u * 1.4), (hL[0] + u * 0.05, hL[1] - u * 0.25),
               (hR[0] - u * 0.05, hR[1] - u * 0.25), (mid[0] - wid * 0.42, mid[1] + u * 1.4),
               (shR[0] + u * 0.15, shR[1] + u * 0.55), (shR[0] + u * 0.35, shR[1] - u * 0.05),
               (mid[0] - u * 0.35, mid[1] + u * 0.5), (mid[0] + u * 0.35, mid[1] + u * 0.5)]
    else:   # футболка
        pts = [(shL[0] + u * 0.3, shL[1] + u * 0.1), (shL[0] + u * 0.25, shL[1] + u * 0.85),
               (shL[0] - u * 0.15, shL[1] + u * 0.85), (mid[0] + wid * 0.44, mid[1] + u * 1.4),
               (hL[0] + u * 0.08, hL[1] - u * 0.15), (hR[0] - u * 0.08, hR[1] - u * 0.15),
               (mid[0] - wid * 0.44, mid[1] + u * 1.4), (shR[0] + u * 0.15, shR[1] + u * 0.85),
               (shR[0] - u * 0.25, shR[1] + u * 0.85), (shR[0] - u * 0.3, shR[1] + u * 0.1),
               (mid[0] - u * 0.35, mid[1] + u * 0.1), (mid[0] + u * 0.35, mid[1] + u * 0.1)]
    kit.volume_fill(ctx, pts, mid, hmid, wid * 1.1, col, rim=0.5)
    smooth_path(ctx, pts)
    stroke(ctx, shade(col, 0.35), 1.4, 0.6)
    for k in range(4):                                 # складки ткани
        x = mid[0] + (k - 1.5) * wid * 0.18
        soft_line(ctx, [(x, mid[1] + u * 1.5), (x + u * 0.08, mid[1] + u * 2.0), (x - u * 0.05, hmid[1] - u * 0.4)],
                  shade(col, 0.62), u * 0.025, 0.45)
    # грязные пятна
    import random
    r = random.Random(4)
    for _ in range(6):
        ellipse(ctx, mid[0] + (r.random() - 0.5) * wid * 0.7, mid[1] + u * (0.8 + r.random() * 2),
                u * (0.06 + r.random() * 0.1), u * (0.04 + r.random() * 0.06))
        fill(ctx, shade(col, 0.6), 0.25)


# ── голова и лицо ──────────────────────────────────────────────────────────
def face_default():
    return dict(yaw=0.0, eye=1.0, brow=0.0, mouth=0.0, smile=0.0, gaze=(0.0, 0.0), pain=0.0)


def head(ctx, j, lk, fc=None):
    fc = {**face_default(), **(fc or {})}
    u = j['u']
    cx, cy = j['head']
    yaw = fc['yaw']
    hw, hh = u * (0.5 if lk['female'] else 0.56), u * 0.68
    col = lk['head']
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(j.get('head_tilt', 0.0))
    dk = shade(col, 0.5)
    # уши
    for sx in (1, -1):
        vis = 1 - max(0, -sx * yaw) * 1.4
        if vis > 0.1:
            ex = sx * hw * (0.98 - 0.25 * abs(yaw)) + yaw * hw * 0.25
            blob(ctx, ex, u * 0.02, u * 0.12 * vis, u * 0.2, shade(col, 0.92), outline=True)
            soft_line(ctx, [(ex - sx * u * 0.02, -u * 0.08), (ex + sx * u * 0.04, u * 0.02), (ex, u * 0.12)],
                      shade(col, 0.55), u * 0.015, 0.6)
    # череп и челюсть
    jaw = 0.82 if lk['female'] else 0.9
    sh = yaw * hw * 0.18
    pts = [(-hw * 0.95 + sh, -hh * 0.35), (-hw * 0.88 + sh, -hh * 0.82), (sh * 0.5, -hh * 1.02),
           (hw * 0.88 + sh, -hh * 0.82), (hw * 0.95 + sh, -hh * 0.35), (hw * 0.9 * jaw + sh * 1.2, hh * 0.25),
           (hw * 0.55 + sh * 1.4, hh * 0.78), (sh * 1.6, hh * 0.96), (-hw * 0.55 + sh * 1.4, hh * 0.78),
           (-hw * 0.9 * jaw + sh * 1.2, hh * 0.25)]
    g = rad(-hw * 0.3 + sh, -hh * 0.4, 0, hh * 1.5, [(0, shade(col, 1.12), 1), (0.45, col, 1),
                                                    (0.8, shade(col, 0.72), 1), (1, shade(col, 0.5), 1)])
    smooth_path(ctx, pts)
    if lk.get('_no_skull'):
        g = lin(-hw, 0, hw, 0, [(0, (0, 0, 0), 0), (1, (0, 0, 0), 0)])
    ctx.set_source(g)
    ctx.fill_preserve()
    side = lin(-hw, 0, hw, 0, [(0, (10, 20, 30), 0.15 + max(0, yaw) * 0.3), (0.4, (0, 0, 0), 0),
                               (0.72, (0, 0, 0), 0), (1, (8, 18, 30), 0.38 + max(0, -yaw) * 0.2)])
    ctx.set_source(side)
    ctx.fill_preserve()
    rimg = lin(-hw, 0, hw, 0, [(0.85, (0, 0, 0), 0), (1, tuple(v * 255 for v in kit.RIM), 0.3)])
    ctx.set_source(rimg)
    ctx.fill_preserve()
    stroke(ctx, shade(col, 0.28), 1.6, 0.35 if lk.get('_no_skull') else 0.6)
    # скулы, глазницы
    fx = lambda x: x * hw * (1 - abs(yaw) * 0.3) + yaw * hw * 0.32   # noqa: E731
    for sx in (1, -1):
        g = rad(fx(sx * 0.38), -hh * 0.12, 0, u * 0.22, [(0, shade(col, 0.6), 0.55), (1, col, 0)])
        ellipse(ctx, fx(sx * 0.38), -hh * 0.12, u * 0.2, u * 0.13)
        ctx.set_source(g)
        ctx.fill()
        soft_line(ctx, [(fx(sx * 0.62), hh * 0.12), (fx(sx * 0.42), hh * 0.32)], shade(col, 0.7), u * 0.02, 0.3)
    # щетина / борода
    beard = lk.get('beard')
    if beard and beard[0] == 'stubble':
        import random
        r = random.Random(9)
        for _ in range(260):
            a = r.random() * math.pi
            rr = 0.55 + r.random() * 0.45
            x = math.cos(a) * hw * 0.85 * rr + sh * 1.3
            y = math.sin(a) * hh * 0.95 * rr
            if y > hh * 0.08:
                ellipse(ctx, x, y, u * 0.008, u * 0.008)
                fill(ctx, beard[1], 0.45)
        g = rad(sh * 1.4, hh * 0.6, 0, hh * 0.6, [(0, beard[1], 0.22), (1, beard[1], 0.0)])
        ellipse(ctx, sh * 1.4, hh * 0.55, hw * 0.85, hh * 0.45)
        ctx.set_source(g)
        ctx.fill()
    # глаза
    ey = -hh * 0.1
    for sx in (1, -1):
        ex = fx(sx * 0.37)
        far = (sx * yaw) < 0
        ew = u * 0.112 * (1 - (abs(yaw) * 0.45 if far else 0))
        g = rad(ex, ey - u * 0.04, 0, u * 0.2, [(0, shade(col, 0.5), 0.55), (0.6, shade(col, 0.7), 0.3), (1, col, 0)])
        ellipse(ctx, ex, ey - u * 0.03, u * 0.2, u * 0.12)
        ctx.set_source(g)
        ctx.fill()
        swollen = 'eyeL' in lk['scars'] and sx == 1
        op = fc['eye'] * (0.12 if swollen else 1.0)
        eh = u * 0.046 * max(0.04, op)
        if op < 0.12 and not swollen:            # закрытый глаз: одно веко дугой и ресницы
            ctx.move_to(ex - ew, ey - u * 0.005)
            ctx.curve_to(ex - ew * 0.4, ey + u * 0.035, ex + ew * 0.4, ey + u * 0.035, ex + ew, ey - u * 0.005)
            stroke(ctx, (30, 18, 18), u * 0.022, 0.9)
            for k in range(5):
                lx = ex - ew * 0.6 + k * ew * 0.3
                ctx.move_to(lx, ey + u * 0.025)
                ctx.line_to(lx - u * 0.008, ey + u * 0.045)
                stroke(ctx, (30, 18, 18), u * 0.008, 0.7)
            ctx.move_to(ex - ew * 0.9, ey - u * 0.04)
            ctx.curve_to(ex - ew * 0.3, ey - u * 0.07, ex + ew * 0.4, ey - u * 0.07, ex + ew * 0.95, ey - u * 0.035)
            stroke(ctx, shade(col, 0.6), u * 0.014, 0.45)
            continue_eye = False
        else:
            continue_eye = True
        # белок
        ellipse(ctx, ex, ey, ew, max(eh, 0.5)) if continue_eye else None
        if continue_eye:
            fill(ctx, (196, 186, 176))
        if op > 0.15:
            ix = ex + fc['gaze'][0] * ew * 0.4 + yaw * ew * 0.2
            iy = ey + fc['gaze'][1] * eh * 0.4
            ctx.save()
            ellipse(ctx, ex, ey, ew, max(eh, 0.5))
            ctx.clip()
            blob(ctx, ix, iy, u * 0.048, u * 0.048, lk['eyes'], outline=False)
            ellipse(ctx, ix, iy, u * 0.022, u * 0.022)
            fill(ctx, (8, 8, 10))
            ellipse(ctx, ix - u * 0.018, iy - u * 0.02, u * 0.012, u * 0.012)
            fill(ctx, (255, 255, 255), 0.85)
            g = lin(0, ey - eh, 0, ey + eh * 0.3, [(0, (30, 22, 22), 0.75), (1, (0, 0, 0), 0)])
            ctx.rectangle(ex - ew, ey - eh, ew * 2, eh)
            ctx.set_source(g)
            ctx.fill()
            ctx.restore()
        # веко
        if continue_eye:
            ctx.move_to(ex - ew * 1.05, ey + u * 0.005)
            ctx.curve_to(ex - ew * 0.5, ey - eh * 1.4, ex + ew * 0.5, ey - eh * 1.4, ex + ew * 1.05, ey)
            stroke(ctx, (22, 14, 14), u * 0.034, 0.95)
            ctx.move_to(ex - ew * 0.8, ey + eh * 0.9)
            ctx.curve_to(ex - ew * 0.3, ey + eh * 1.3, ex + ew * 0.3, ey + eh * 1.3, ex + ew * 0.8, ey + eh * 0.8)
            stroke(ctx, shade(col, 0.55), u * 0.012, 0.6)
            ctx.move_to(ex - ew * 0.9, ey - eh * 1.3 - u * 0.03)                  # складка века
            ctx.curve_to(ex - ew * 0.3, ey - eh * 2 - u * 0.04, ex + ew * 0.4, ey - eh * 2 - u * 0.04,
                         ex + ew * 0.95, ey - eh * 1.1 - u * 0.03)
            stroke(ctx, shade(col, 0.6), u * 0.014, 0.55)
        if swollen:
            blob(ctx, ex, ey - u * 0.01, ew * 1.35, u * 0.13, (110, 70, 96), outline=False)
            soft_line(ctx, [(ex - ew, ey + u * 0.01), (ex, ey + u * 0.03), (ex + ew, ey)], (30, 18, 22), u * 0.02, 0.8)
        # бровь
        bw = ew * 1.25
        by = ey - u * 0.135 - fc['brow'] * u * 0.03
        inner = by + fc['pain'] * u * 0.05 * (1) - fc['brow'] * u * 0.0
        outer = by - fc['pain'] * u * 0.04
        hair_col = (lk['hair'][1] if lk.get('hair') and lk['hair'][1] else (52, 40, 34))
        ctx.move_to(ex - sx * bw * 0.95, inner + (u * 0.03 if fc['brow'] < 0 else 0))
        ctx.curve_to(ex - sx * bw * 0.2, by - u * 0.04, ex + sx * bw * 0.4, by - u * 0.035, ex + sx * bw * 1.05,
                     outer + u * 0.02)
        stroke(ctx, hair_col, u * (0.045 if not lk['female'] else 0.032), 0.95)
    # нос
    nx = fx(0) + yaw * u * 0.1
    soft_line(ctx, [(nx - u * 0.02, -hh * 0.02), (nx - u * 0.05 + yaw * u * 0.05, hh * 0.22),
                    (nx + yaw * u * 0.08, hh * 0.3)], shade(col, 0.6), u * 0.025, 0.55)
    blob(ctx, nx + yaw * u * 0.05, hh * 0.3, u * 0.09, u * 0.07, shade(col, 1.02), outline=False)
    for sx in (1, -1):
        ellipse(ctx, nx + sx * u * 0.06 + yaw * u * 0.03, hh * 0.36, u * 0.032, u * 0.018, sx * 0.4)
        fill(ctx, (40, 22, 20), 0.85)
    g = rad(nx, hh * 0.46, 0, u * 0.18, [(0, shade(col, 0.6), 0.45), (1, col, 0)])
    ellipse(ctx, nx, hh * 0.45, u * 0.18, u * 0.07)
    ctx.set_source(g)
    ctx.fill()
    for sx in (1, -1):
        soft_line(ctx, [(fx(sx * 0.2), hh * 0.32), (fx(sx * 0.3), hh * 0.5), (fx(sx * 0.3), hh * 0.62)],
                  shade(col, 0.6), u * 0.018, 0.35)
    g = rad(fx(0), hh * 0.82, 0, u * 0.2, [(0, shade(col, 0.6), 0.4), (1, col, 0)])
    ellipse(ctx, fx(0), hh * 0.8, u * 0.2, u * 0.08)
    ctx.set_source(g)
    ctx.fill()
    # рот
    mx, my = fx(0) + yaw * u * 0.06, hh * 0.58
    mw = u * (0.2 if lk['female'] else 0.22)
    mo = fc['mouth']
    sm = fc['smile']
    lipc = shade(col, 0.8) if not lk['female'] else (122, 66, 62)
    if mo > 0.05:
        ctx.move_to(mx - mw, my - sm * u * 0.03)
        ctx.curve_to(mx - mw * 0.4, my - u * 0.03, mx + mw * 0.4, my - u * 0.03, mx + mw, my - sm * u * 0.03)
        ctx.curve_to(mx + mw * 0.5, my + mo * u * 0.2, mx - mw * 0.5, my + mo * u * 0.2, mx - mw, my - sm * u * 0.03)
        fill(ctx, (34, 14, 16))
        ctx.save()
        ctx.rectangle(mx - mw, my - u * 0.04, mw * 2, u * 0.05)
        ctx.clip()
        ellipse(ctx, mx, my, mw * 0.7, u * 0.05)
        fill(ctx, (214, 204, 186), 0.9)
        ctx.restore()
    ctx.move_to(mx - mw, my - sm * u * 0.03)
    ctx.curve_to(mx - mw * 0.4, my - u * 0.035, mx + mw * 0.4, my - u * 0.035, mx + mw, my - sm * u * 0.03)
    stroke(ctx, (52, 24, 24), u * 0.022, 0.9)
    # нижняя губа
    ly = my + mo * u * 0.17 + u * 0.03
    ctx.move_to(mx - mw * 0.75, ly - u * 0.01)
    ctx.curve_to(mx - mw * 0.3, ly + u * 0.05, mx + mw * 0.3, ly + u * 0.05, mx + mw * 0.75, ly - u * 0.01)
    stroke(ctx, lipc, u * 0.045, 0.7)
    ellipse(ctx, mx - mw * 0.1, ly + u * 0.005, mw * 0.25, u * 0.012)
    fill(ctx, (255, 230, 220), 0.25)
    soft_line(ctx, [(mx - mw * 0.4, ly + u * 0.09), (mx + mw * 0.4, ly + u * 0.09)], shade(col, 0.6), u * 0.02, 0.35,
              smooth=False)
    # шрамы (Йорка: старый на правой щеке, свежий рубец через лоб, разбитые губы)
    if 'cheekR' in lk['scars']:
        soft_line(ctx, [(fx(-0.6), -hh * 0.02), (fx(-0.5), hh * 0.18), (fx(-0.42), hh * 0.34)], (168, 120, 104),
                  u * 0.028, 0.8)
    if 'forehead' in lk['scars']:
        soft_line(ctx, [(fx(-0.7), -hh * 0.62), (fx(-0.1), -hh * 0.5), (fx(0.6), -hh * 0.44)], (176, 40, 42),
                  u * 0.04, 0.9)
        for k in range(5):
            x = fx(-0.55 + k * 0.27)
            ctx.move_to(x, -hh * 0.6 + k * hh * 0.035)
            ctx.line_to(x + u * 0.02, -hh * 0.46 + k * hh * 0.035)
            stroke(ctx, (110, 24, 26), u * 0.012, 0.7)
    if 'lips' in lk['scars']:
        for dx, dy in ((-0.45, 0.0), (0.35, 1.0)):
            yy = my + dy * (ly - my)
            ellipse(ctx, mx + mw * dx, yy, u * 0.025, u * 0.014)
            fill(ctx, (120, 24, 30), 0.85)
        g = rad(mx + mw * 0.35, ly, 0, u * 0.09, [(0, (110, 40, 60), 0.45), (1, (110, 40, 60), 0)])
        ellipse(ctx, mx + mw * 0.35, ly, u * 0.09, u * 0.05)
        ctx.set_source(g)
        ctx.fill()
    # волосы
    hair(ctx, lk, hw, hh, sh, u)
    ctx.restore()


fc_mouth_dummy = 0


def hair(ctx, lk, hw, hh, sh, u):
    kind, hc = lk.get('hair') or (None, None)
    import random
    r = random.Random(17)
    if kind == 'buzz':                            # короткий ёжик: тёмная тень волос на скальпе + мелкие точки
        pts = [(-hw * 0.99 + sh, -hh * 0.28), (-hw * 0.94 + sh, -hh * 0.84), (sh * 0.5, -hh * 1.05),
               (hw * 0.94 + sh, -hh * 0.84), (hw * 0.99 + sh, -hh * 0.28), (hw * 0.86 + sh, -hh * 0.36),
               (hw * 0.62 + sh, -hh * 0.58), (hw * 0.2 + sh, -hh * 0.64), (-hw * 0.2 + sh, -hh * 0.64),
               (-hw * 0.62 + sh, -hh * 0.58), (-hw * 0.86 + sh, -hh * 0.36)]
        smooth_path(ctx, pts)
        ctx.set_source(rad(-hw * 0.35 + sh, -hh * 0.95, 0, hh * 1.25, [(0, mixc(hc, (120, 110, 104), 0.35), 0.9),
                                                                       (0.55, hc, 0.88), (1, hc, 0.75)]))
        ctx.fill()
        for _ in range(900):
            a = math.pi + r.random() * math.pi
            rr = 0.55 + r.random() * 0.45
            x = math.cos(a) * hw * 0.97 * rr + sh
            y = math.sin(a) * hh * 1.02 * rr - hh * 0.02
            if y < -hh * 0.62 + abs(x - sh) / hw * hh * 0.3:
                ellipse(ctx, x, y, u * 0.006, u * 0.012, a + 1.57)
                fill(ctx, (0, 0, 0) if r.random() < 0.6 else (90, 80, 76), 0.35)
    elif kind == 'ragged':                        # коротко и плохо стриженная: неровная тёмная шапка + пряди
        pts = [(-hw * 1.0 + sh, -hh * 0.18), (-hw * 1.02 + sh, -hh * 0.7), (-hw * 0.7 + sh, -hh * 1.06),
               (sh * 0.5, -hh * 1.14), (hw * 0.72 + sh, -hh * 1.04), (hw * 1.04 + sh, -hh * 0.68),
               (hw * 1.0 + sh, -hh * 0.12), (hw * 0.86 + sh, -hh * 0.3), (hw * 0.78 + sh, -hh * 0.5),
               (hw * 0.5 + sh, -hh * 0.46), (hw * 0.32 + sh, -hh * 0.58), (hw * 0.05 + sh, -hh * 0.44),
               (-hw * 0.25 + sh, -hh * 0.56), (-hw * 0.5 + sh, -hh * 0.42), (-hw * 0.78 + sh, -hh * 0.5),
               (-hw * 0.88 + sh, -hh * 0.26)]
        smooth_path(ctx, pts, tension=0.7)
        ctx.set_source(rad(-hw * 0.3 + sh, -hh * 0.95, 0, hh * 1.2, [(0, (54, 52, 60), 1), (0.6, hc, 1), (1, hc, 1)]))
        ctx.fill()
        for k in range(40):
            a = math.pi * (0.92 + r.random() * 1.16)
            rr = 0.9 + r.random() * 0.12
            if math.pi * 1.25 < a < math.pi * 1.75 and r.random() < 0.7:
                continue
            x0 = math.cos(a) * hw * rr + sh
            y0 = math.sin(a) * hh * rr - hh * 0.12
            ang = math.pi / 2 + (math.cos(a)) * 0.6 + (r.random() - 0.5) * 0.6
            ln = u * (0.04 + r.random() * 0.09)
            ctx.move_to(x0, y0)
            ctx.line_to(x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln)
            stroke(ctx, (34, 34, 40) if r.random() < 0.2 else (8, 8, 10), u * (0.014 + r.random() * 0.012), 0.7)
    elif kind == 'long':                          # длинные волосы (№444)
        for k in range(60):
            sx = (k / 59 - 0.5) * 2
            x0 = sx * hw * 0.85 + sh
            y0 = -hh * (0.95 - abs(sx) * 0.4)
            pts = [(x0, y0), (x0 + sx * hw * 0.3, y0 + hh * 0.5), (x0 + sx * hw * 0.42 + (r.random() - 0.5) * u * 0.1,
                                                                   hh * (0.8 + r.random() * 0.8))]
            if abs(sx) < 0.5:
                continue
            smooth_path(ctx, pts, closed=False)
            stroke(ctx, shade(hc, 0.7 + r.random() * 0.8), u * 0.035, 0.85)
        pts = [(-hw * 0.98 + sh, -hh * 0.4), (-hw * 0.9 + sh, -hh * 0.88), (sh * 0.5, -hh * 1.08),
               (hw * 0.9 + sh, -hh * 0.88), (hw * 0.98 + sh, -hh * 0.4), (sh, -hh * 0.7)]
        smooth_path(ctx, pts)
        fill(ctx, hc, 0.95)
    elif kind == 'spiky':                         # светлые волосы дыбом (Букса)
        for k in range(40):
            a = math.pi * (1.0 + k / 40)
            x0 = math.cos(a) * hw * 0.8 + sh
            y0 = math.sin(a) * hh * 0.9 - hh * 0.1
            ang = -math.pi / 2 + (math.cos(a)) * 0.9 + (r.random() - 0.5) * 0.5
            ln = u * (0.35 + r.random() * 0.35)
            ctx.move_to(x0 - u * 0.06, y0 + u * 0.05)
            ctx.line_to(x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln)
            ctx.line_to(x0 + u * 0.06, y0 + u * 0.05)
            ctx.close_path()
            fill(ctx, shade(hc, 0.8 + r.random() * 0.4), 0.95)
    elif kind == 'shaved':
        ctx.set_source(rad(-hw * 0.3, -hh * 0.8, 0, hh * 0.5, [(0, (255, 240, 220), 0.25), (1, (0, 0, 0), 0)]))
        ellipse(ctx, -hw * 0.3 + sh, -hh * 0.75, hw * 0.4, hh * 0.22)
        ctx.fill()
    beard = lk.get('beard')
    if beard and beard[0] == 'full':
        bc = beard[1]
        pts = [(-hw * 0.92 + sh, hh * 0.0), (-hw * 0.8 + sh, hh * 0.6), (-hw * 0.4 + sh, hh * 1.25), (sh, hh * 1.45),
               (hw * 0.4 + sh, hh * 1.25), (hw * 0.8 + sh, hh * 0.6), (hw * 0.92 + sh, hh * 0.0), (hw * 0.6 + sh, hh * 0.22),
               (hw * 0.3 + sh, hh * 0.42), (sh, hh * 0.4), (-hw * 0.3 + sh, hh * 0.42), (-hw * 0.6 + sh, hh * 0.22)]
        smooth_path(ctx, pts, tension=0.6)
        ctx.set_source(rad(sh - hw * 0.2, hh * 0.5, 0, hh * 1.2, [(0, mixc(bc, (150, 140, 130), 0.3), 0.97), (1, bc, 0.97)]))
        ctx.fill()
        for k in range(120):
            sx = (r.random() - 0.5) * 1.8
            x0 = sx * hw * 0.9 + sh
            y0 = hh * (0.1 + abs(sx) * 0.05 + r.random() * 0.5)
            ln = hh * (0.25 + r.random() * 0.4)
            pts = [(x0, y0), (x0 + sx * u * 0.03, y0 + ln * 0.5), (x0 * 0.92 + (r.random() - 0.5) * u * 0.06, y0 + ln)]
            smooth_path(ctx, pts, closed=False)
            stroke(ctx, shade(bc, 0.6 + r.random() * 0.9), u * 0.018, 0.7)
        # рот в бороде — тёмная щель
        ellipse(ctx, sh * 1.4, hh * 0.6, hw * 0.22, hh * 0.05 + fc_mouth_dummy * 0)
        fill(ctx, (30, 20, 18), 0.8)


# ── сборка ────────────────────────────────────────────────────────────────
def draw(ctx, j, lk, fc=None, back_arms=()):
    """рисует фигуру. back_arms — какие руки рисовать ДО торса (за телом)"""
    for side in ('L', 'R'):
        draw_limb_set(ctx, j, side, None, lk, 'leg')
    shorts(ctx, j, lk)
    for side in back_arms:
        draw_limb_set(ctx, j, side, None, lk, 'arm')
    mid, wid = torso(ctx, j, lk)
    number(ctx, j, lk, mid, wid)
    if lk.get('barcode'):
        barcode(ctx, j)
    top(ctx, j, lk, mid, wid)
    if lk.get('top') and lk.get('number') and lk['num_pos'] == 'collar':
        number(ctx, j, lk, mid, wid)
    if lk.get('belt'):
        shorts_belt = dict(lk)
        shorts(ctx, j, shorts_belt) if False else None
    for side in ('L', 'R'):
        if side not in back_arms:
            draw_limb_set(ctx, j, side, None, lk, 'arm')
    head(ctx, j, lk, fc)


def render(w, h, j, lk, fc=None, back_arms=(), shadow=True):
    """фигура на отдельном холсте w×h -> premultiplied RGBA + мягкая контактная тень"""
    cv = kit.Canvas(w, h)
    draw(cv.ctx, j, lk, fc, back_arms)
    arr = cv.premul()
    kit.texture(arr, 0.1, 5, seed=3, fine=0.04)
    return arr


def crowd_look(seed, female=None):
    """случайный житель коридоров: у каждого пришиты чужие руки и ноги разного возраста и цвета"""
    r = random.Random(seed)
    fem = r.random() < 0.35 if female is None else female
    tones = [SKIN_TAN, SKIN_OLD, SKIN_DARK, SKIN_COAL, SKIN_PALE, SKIN_OLIVE, SKIN_YELLOW, (150, 100, 76)]
    torso = r.choice([SKIN_TAN, SKIN_PALE, SKIN_OLIVE, SKIN_DARK, (178, 132, 100)])
    def lim(kinds):
        if r.random() < 0.06:
            return None
        return (r.choice(kinds), r.choice(tones))
    arms = {'L': lim(['old', 'thin', 'normal', 'strong', 'female']), 'R': lim(['old', 'thin', 'normal', 'strong'])}
    if arms['L'] is None and arms['R'] is None:
        arms['L'] = ('normal', r.choice(tones))
    legs = {'L': (r.choice(['old', 'thin', 'normal', 'athletic']), r.choice(tones)),
            'R': (r.choice(['old', 'thin', 'normal', 'strong']), r.choice(tones))}
    hairs = [('buzz', (30, 26, 24)), ('shaved', None), ('buzz', (90, 70, 50)), ('ragged', (40, 30, 26)),
             ('long', (60, 46, 36)), ('buzz', (150, 140, 130))]
    hair = r.choice(hairs[:4] if not fem else [('ragged', (30, 24, 22)), ('long', (70, 50, 34)), ('ragged', (120, 90, 60))])
    beard = None if fem else r.choice([None, None, ('stubble', (40, 34, 30)), ('full', (50, 40, 34))])
    return look(torso=torso, build=r.choice(['thin', 'thin', 'normal']) if not fem else 'slim', female=fem,
                arms=arms, legs=legs, shorts=shade(r.choice([(46, 48, 54), (60, 52, 44), (40, 44, 40), (70, 66, 60)]), 1.0),
                top=('tank', r.choice([(90, 92, 88), (110, 100, 86), (70, 76, 84)])) if fem else None,
                number=str(r.randint(12, 989)), hair=hair, beard=beard, eyes=r.choice([(60, 44, 34), (70, 80, 90)]),
                nails_black=r.random() < 0.5, finger_miss=r.random() < 0.2, scars=[])


# ── второстепенные по книге ───────────────────────────────────────────────
B58 = look(torso=(186, 140, 108), build='heavy', number='58', hair=('shaved', None), beard=('stubble', (40, 32, 28)),
           arms={'L': ('strong', SKIN_OLD), 'R': ('strong', (196, 166, 146))},     # накачанные стариковские руки
           legs={'L': ('normal', (170, 130, 100)), 'R': ('normal', (176, 136, 104))}, eyes=(50, 40, 34))
LAME = look(torso=(170, 136, 112), build='slim', female=True, number='240', num_pos='collar',
            arms={'L': ('thin', (150, 110, 86)), 'R': ('female', (176, 140, 114))},
            legs={'L': ('thin', (190, 160, 130)), 'R': ('old', SKIN_OLD)}, top=('tank', (98, 90, 82)),
            hair=('ragged', (90, 80, 72)), eyes=(70, 60, 50))
BARS = look(torso=(184, 138, 104), build='muscle', number='107', hair=('buzz', (40, 32, 26)),
            beard=('stubble', (46, 36, 30)), arms={'L': ('strong', (176, 132, 100)), 'R': ('strong', (172, 128, 96))},
            legs={'L': ('muscle', (140, 98, 70)), 'R': ('muscle', (136, 94, 66))}, eyes=(60, 46, 34))
BUKSA = look(torso=(222, 190, 170), build='slim', female=True, hair=('spiky', (236, 224, 170)),
             arms={'L': ('female', (210, 176, 150)), 'R': ('female', (196, 160, 132))},
             legs={'L': ('normal', (226, 196, 176)), 'R': ('thin', (200, 170, 150))}, top=('tank', (150, 90, 110)),
             number='63', num_pos='collar', eyes=(70, 110, 130))
P444 = look(torso=(196, 170, 120), build='thin', number='444', hair=('long', (58, 46, 36)),
            beard=('full', (60, 48, 38)), spine=1.0, eyes=(70, 60, 46),
            arms={'L': ('strong', SKIN_PALE), 'R': ('thin', SKIN_COAL)},             # белая и чёрная
            legs={'L': ('thin', SKIN_YELLOW), 'R': ('thin', SKIN_YELLOW)})
GUARD = look(torso=(190, 146, 112), build='muscle', hair=('shaved', None), beard=None, top=('tee', (24, 24, 26)),
             shorts=(22, 22, 24), belt='baton', shoes=(26, 26, 28), eyes=(56, 44, 36),
             arms={'L': ('strong', (186, 142, 108)), 'R': ('strong', (180, 136, 102))},
             legs={'L': ('athletic', (180, 136, 102)), 'R': ('athletic', (180, 136, 102))})
STRONGW = look(torso=(170, 126, 96), build='slim', female=True, top=('tank', (80, 84, 78)), number='305', num_pos='collar',
               arms={'L': ('strong', (150, 110, 80)), 'R': ('strong', (160, 118, 88))},
               legs={'L': ('athletic', (150, 110, 80)), 'R': ('strong', (140, 100, 74))}, hair=('ragged', (40, 30, 24)))
GREYMAN = look(torso=(200, 170, 150), build='thin', number='512', hair=('buzz', (200, 196, 190)),
               beard=('stubble', (200, 196, 190)), arms={'L': ('old', SKIN_OLD), 'R': ('thin', (190, 150, 120))},
               legs={'L': ('old', SKIN_OLD), 'R': ('old', SKIN_OLD)})
WEIRDO = look(torso=(176, 150, 130), build='thin', number='777', hair=('ragged', (80, 70, 60)), beard=('stubble', (60, 50, 40)),
              arms={'L': ('thin', SKIN_OLIVE), 'R': ('old', SKIN_OLD)}, legs={'L': ('thin', SKIN_PALE), 'R': ('thin', SKIN_DARK)})
