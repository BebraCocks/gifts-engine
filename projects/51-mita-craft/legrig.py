"""2D-риг ног для ходьбы Миты (как в cut-out анимации): ноги берутся из ОДНОЙ позы и сгибаются программно.

Почему: позы ног с разных листов ChatGPT нарисованы каждый раз заново (стопа, чулок, тени) → при любом
выборе/морфе ноги «дёргаются». Здесь рисунок ног один и тот же во всех кадрах, меняются только углы.

• источник SRC (обе стопы на полу, ноги раздельно), выровненный кадр из frames_aligned;
• каждая нога: бедро (вращение в тазобедренном), голень (колено), стопа (голеностоп) — мягкие веса на стыках,
  деформация «обратным LBS»: каждая кость сдвигает всю ногу, результаты смешиваются по весам;
• походка: опора 60 % (стопа скользит назад с постоянной скоростью — в сцене спрайт едет вперёд с той же скоростью,
  и стопа стоит на месте), перекат пятка → вся стопа → носок, мах 40 % по дуге; колено — 2-звенная IK;
• верх (голова, руки, плащ, юбка) — та же поза SRC, только покачивается вместе с тазом; шов под подолом.

leg_frame(phase) → RGBA 768×1024; phase — доля полного цикла (два шага)."""
import functools
import math

import cv2
import numpy as np

import anim

SRC = 'walk_bc'
GROUND = 990.0
STANCE = 0.6
LIFT = 55.0            # высота подъёма стопы в махе (px холста 768×1024)
BOB = 5.0              # покачивание таза
TOE_OFF = 40.0         # угол отрыва пятки (носок на полу), °
HEEL_STRIKE = 20.0     # носок вверх при постановке на пятку, °
HEEL_OFF = 0.62        # с какой доли опоры начинает подниматься пятка


def _ang(v):
    return math.atan2(-v[1], v[0])                 # против часовой на экране (y вниз)


def _R(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, s], [-s, c]], np.float64)   # поворот против часовой на экране


def _runs(row):
    xs = np.nonzero(row)[0]
    if len(xs) == 0:
        return []
    return [r for r in np.split(xs, np.nonzero(np.diff(xs) > 2)[0] + 1)]


@functools.lru_cache(None)
def rig():
    a = anim.pose(SRC).astype(np.float32)
    al = a[..., 3] > 60
    import walk
    hem = walk._hem(a.astype(np.uint8))
    Y0 = hem - 12
    # только ширина бёдер под подолом (кисть руки и край юбки — не ноги)
    xs_t = np.nonzero(al[hem + 15])[0]
    al = al.copy()
    al[:hem + 15, :max(0, xs_t.min() - 4)] = False
    al[:hem + 15, xs_t.max() + 5:] = False
    # промежность: первая строка, начиная с которой 20 строк подряд две большие «полосы»
    yc = None
    for y in range(Y0, 900):
        if all(len([r for r in _runs(al[yy]) if len(r) > 15]) >= 2 for yy in range(y, y + 20)):
            yc = y
            break
    gx, gy = [], []
    for y in range(yc, yc + 60):
        rs = sorted([r for r in _runs(al[y]) if len(r) > 15], key=len)[-2:]
        rs = sorted(rs, key=lambda r: r[0])
        gx.append((rs[0][-1] + rs[1][0]) / 2)
        gy.append(y)
    m, q = np.polyfit(gy, gx, 1)
    lab = np.zeros(al.shape, np.int32)                 # 1 — дальняя (левая), 2 — ближняя (правая)
    n, cc, st, _ = cv2.connectedComponentsWithStats(al[yc:].astype(np.uint8))
    big = sorted(range(1, n), key=lambda i: -st[i, 4])[:2]
    big = sorted(big, key=lambda i: st[i, 0])
    sub = lab[yc:]
    sub[cc == big[0]] = 1
    sub[cc == big[1]] = 2
    # мелкие обрывки (кусочки носка) — к ближайшей ноге по x
    rest = (cc > 0) & (sub == 0)
    if rest.any():
        ys, xs = np.nonzero(rest)
        for y, x in zip(ys, xs):
            sub[y, x] = 1 if x < m * (y + yc) + q else 2
    for y in range(Y0, yc):
        xs = np.nonzero(al[y])[0]
        split = m * y + q
        lab[y, xs[xs < split]] = 1
        lab[y, xs[xs >= split]] = 2
    legs = {}
    for k in (1, 2):
        img = a.copy()
        img[..., 3] *= (lab == k)
        img[:Y0] = 0
        msk = lab == k
        # скелет: средняя линия ноги
        def mid(y):
            xs = np.nonzero(msk[y])[0]
            return (xs.min() + xs.max()) / 2
        ys = np.nonzero(msk.any(1))[0]
        ybot = ys.max()
        ya = ybot - 75                                  # голеностоп — над туфлей
        yk = Y0 + 0.47 * (ya - Y0)
        top = [(mid(y), y) for y in range(yc + 5, yc + 45)]   # ось бедра — ниже промежности (там нога целиком)
        mm, qq = np.polyfit([t[1] for t in top], [t[0] for t in top], 1)
        H = np.array([mid(hem + 15), hem - 45.0])        # тазобедренный — над серединой бедра у подола
        # под юбкой продлеваем бедро вверх по его наклону (чтобы при повороте у подола не открылась щель)
        row = img[Y0].copy()
        for d in range(1, 111):
            img[Y0 - d] = anim._translate(row[None], np.array([-mm * d, 0], np.float32))[0]
        msk = img[..., 3] > 60
        K = np.array([mid(int(yk)), yk])
        A = np.array([mid(int(ya)), float(ya)])
        # стопа: пятка — нижняя точка левого края туфли, носок — нижняя точка правого края
        sh = msk.copy()
        sh[:int(ya) + 15] = False
        cols = np.nonzero(sh.any(0))[0]
        def bottom(x):
            return float(np.nonzero(sh[:, x])[0].max())
        heel = np.array([float(cols.min() + 3), bottom(cols.min() + 3)])
        toe = np.array([float(cols.max() - 3), bottom(cols.max() - 3)])
        beta = math.degrees(_ang(toe - heel))           # угол стопы в исходной позе (+ носок вверх)
        # веса костей по высоте (бедро → голень у колена ±28 px, голень → стопа у голеностопа ±10 px)
        Y = np.arange(a.shape[0], dtype=np.float32)[:, None] * np.ones((1, a.shape[1]), np.float32)
        def sm(x):
            x = np.clip(x, 0, 1)
            return x * x * (3 - 2 * x)
        w_sh = sm((Y - (yk - 40)) / 80)
        X = np.arange(a.shape[1], dtype=np.float32)[None, :] * np.ones((a.shape[0], 1), np.float32)
        # стопа: всё ниже голеностопа + носок туфли, выступающий вперёд (он выше линии голеностопа)
        w_ft = np.maximum(sm((Y - (ya - 10)) / 20), sm((X - (A[0] + 25)) / 20) * (Y > ya - 45))
        W = [1 - w_sh, w_sh * (1 - w_ft), w_ft]
        pre = img.copy()
        pre[..., :3] *= pre[..., 3:4] / 255
        mesh = _mesh(img[..., 3], W)
        legs[k] = dict(img=pre, W=W, mesh=mesh, H=H, K=K, A=A, heel=heel, toe=toe, beta=beta,
                       L1=float(np.linalg.norm(K - H)), L2=float(np.linalg.norm(A - K)))
    # шаг: ближняя нога в исходной позе — на касании пяткой (u=0), дальняя — на отрыве носка (u=1)
    near, far = legs[2], legs[1]
    flat_n = float(np.linalg.norm(near['toe'] - near['heel']))
    flat_f = float(np.linalg.norm(far['toe'] - far['heel']))
    xf_near = near['heel'][0] - near['H'][0]                      # пятка спереди относительно таза
    S = xf_near + flat_f - (far['toe'][0] - far['H'][0])           # длина шага
    for L, fl in ((near, flat_n), (far, flat_f)):
        L['xf'] = xf_near
        L['S'] = S
        L['flat'] = fl
    upper = a.copy()
    return dict(legs=legs, hem=hem, upper=upper)


def _foot_at(L, pivot_name, pivot_pos, beta):
    """Положение голеностопа, если точка стопы pivot (пятка/носок) стоит в pivot_pos, а стопа под углом beta."""
    Rm = _R(math.radians(beta - L['beta']))
    p_r = L[pivot_name] - L['A']
    return np.asarray(pivot_pos, np.float64) - Rm @ p_r


def _stance(L, u):
    hx = L['H'][0] + L['xf'] - L['S'] * u                 # пятка скользит назад равномерно
    if u < 0.14:                                        # перекат с пятки на всю стопу
        x = u / 0.14
        b = HEEL_STRIKE * (1 - x) ** 2
        return _foot_at(L, 'heel', (hx, GROUND), b), b
    if u < HEEL_OFF:
        return _foot_at(L, 'heel', (hx, GROUND), 0.0), 0.0
    x = (u - HEEL_OFF) / (1 - HEEL_OFF)                 # пятка плавно поднимается, носок на полу
    b = -TOE_OFF * x ** 1.6
    return _foot_at(L, 'toe', (hx + L['flat'], GROUND), b), b


def _leg_state(L, phi):
    phi %= 1.0
    if phi < STANCE:
        A, b = _stance(L, phi / STANCE)
    else:
        v = (phi - STANCE) / (1 - STANCE)
        A0, b0 = _stance(L, 1.0)
        A1, b1 = _stance(L, 0.0)
        e = 0.5 - 0.5 * math.cos(math.pi * v)
        A = A0 * (1 - e) + A1 * e + np.array([0.0, -LIFT * math.sin(math.pi * v ** 0.8)])
        b = b0 * (1 - e) + b1 * e
    return A, b


def _ik(H, A, L1, L2):
    d = A - H
    D = min(float(np.linalg.norm(d)), (L1 + L2) * 0.999)
    u = d / max(np.linalg.norm(d), 1e-6)
    cg = (L1 * L1 + D * D - L2 * L2) / (2 * L1 * D)
    g = math.acos(max(-1.0, min(1.0, cg)))
    p = np.array([-u[1], u[0]])
    if p[0] < 0:
        p = -p                                          # колено вперёд (по ходу движения — вправо)
    K = H + L1 * (math.cos(g) * u + math.sin(g) * p)
    A2 = K + L2 * (A - K) / max(np.linalg.norm(A - K), 1e-6)
    return K, A2


def _affine(rot, src_pivot, dst_pivot):
    """Матрица 2×3: x' = R(rot)(x − src) + dst (в координатах экрана)."""
    Rm = _R(rot)
    t = dst_pivot - Rm @ src_pivot
    return np.array([[Rm[0, 0], Rm[0, 1], t[0]], [Rm[1, 0], Rm[1, 1], t[1]]], np.float32)


STEP = 8


def _mesh(alpha, W):
    """Сетка треугольников по ноге (шаг STEP), веса костей в вершинах. Берём только клетки, где есть нога."""
    ys, xs = np.nonzero(alpha > 10)
    x0, x1 = xs.min() - 12, xs.max() + 12
    y0, y1 = ys.min() - 12, ys.max() + 12
    gx = np.arange(x0, x1 + STEP, STEP, dtype=np.float32)
    gy = np.arange(y0, y1 + STEP, STEP, dtype=np.float32)
    nx, ny = len(gx), len(gy)
    V = np.stack(np.meshgrid(gx, gy), -1).reshape(-1, 2)
    h, w = alpha.shape
    vi = np.clip(V[:, 1].astype(int), 0, h - 1), np.clip(V[:, 0].astype(int), 0, w - 1)
    Wv = np.stack([Wb[vi] for Wb in W], 1)
    Wv /= Wv.sum(1, keepdims=True)
    m = cv2.dilate((alpha > 10).astype(np.uint8), np.ones((7, 7), np.uint8))
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            cx0, cy0 = int(gx[i]), int(gy[j])
            if not m[max(0, cy0):min(h, cy0 + STEP + 1), max(0, cx0):min(w, cx0 + STEP + 1)].any():
                continue
            a, b, c, d = j * nx + i, j * nx + i + 1, (j + 1) * nx + i, (j + 1) * nx + i + 1
            tris += [(a, b, c), (b, d, c)]
    T = np.array(tris, np.int32)
    order = np.argsort(-V[T].mean(1)[:, 1])            # снизу вверх: бедро рисуется последним (поверх сгиба)
    return dict(V=V, Wv=Wv.astype(np.float32), T=T[order])


# Кривые походки человека (доля цикла от касания пяткой → угол, °), по данным биомеханики (Winter):
# бедро — сгибание вперёд (+) / разгибание назад (−); колено — сгибание; стопа — наклон к полу (+ носок вверх).
GAIT_HIP = [(0, 30), (10, 27), (20, 20), (30, 12), (40, 3), (50, -6), (55, -9), (60, -8), (65, -2), (70, 7),
            (75, 15), (80, 22), (85, 27), (90, 30), (95, 31), (100, 30)]
GAIT_KNEE = [(0, 4), (5, 10), (12, 17), (18, 18), (25, 13), (35, 6), (42, 4), (50, 8), (55, 18), (60, 35),
             (65, 50), (70, 60), (73, 62), (78, 58), (85, 40), (90, 22), (95, 8), (100, 4)]
GAIT_FOOT = [(0, 18), (4, 10), (8, 2), (12, 0), (40, 0), (45, -3), (52, -12), (58, -28), (62, -38), (67, -35),
             (72, -22), (78, -10), (85, 0), (92, 10), (97, 16), (100, 18)]
HIP_SCALE = 0.8        # вид три четверти: шаг в кадре короче, чем сбоку
KNEE_SCALE = 1.0
FOOT_SCALE = 0.85


@functools.lru_cache(None)
def _curves():
    from scipy.interpolate import CubicSpline
    out = []
    for pts, sc in ((GAIT_HIP, HIP_SCALE), (GAIT_KNEE, KNEE_SCALE), (GAIT_FOOT, FOOT_SCALE)):
        x = np.array([p[0] for p in pts], float) / 100
        y = np.array([p[1] for p in pts], float) * sc
        out.append(CubicSpline(x, y, bc_type='periodic'))
    return out


def _joints(L, H, phi):
    """Прямая кинематика: таз H, фаза phi → колено, голеностоп, наклон стопы."""
    ch, ck, cf = _curves()
    p = phi % 1.0
    th = math.radians(float(ch(p)))
    ts = th - math.radians(float(ck(p)))
    K = H + L['L1'] * np.array([math.sin(th), math.cos(th)])
    A = K + L['L2'] * np.array([math.sin(ts), math.cos(ts)])
    return K, A, float(cf(p))


def _contacts(L, A, beta):
    """Пятка и носок (нижние точки туфли) при голеностопе A и наклоне beta."""
    Rm = _R(math.radians(beta - L['beta']))
    return [A + Rm @ (L[n] - L['A']) for n in ('heel', 'toe')]


def _render_leg(L, H, phi, joints=None):
    K, A, beta = joints if joints is not None else _joints(L, H, phi)
    Ms = [_affine(_ang(K - H) - _ang(L['K'] - L['H']), L['H'], H),
          _affine(_ang(A - K) - _ang(L['A'] - L['K']), L['K'], K),
          _affine(math.radians(beta - L['beta']), L['A'], A)]
    me = L['mesh']
    V, Wv, T = me['V'], me['Wv'], me['T']
    Vh = np.concatenate([V, np.ones((len(V), 1), np.float32)], 1)
    Vd = sum(Wv[:, b:b + 1] * (Vh @ Ms[b].T) for b in range(3))      # скиннинг вершин
    h, w = L['img'].shape[:2]
    # растеризация: номер треугольника в каждом пикселе
    lab = np.full((h, w), -1, np.int32)
    SH = 4
    P = np.round(Vd[T] * (1 << SH)).astype(np.int32)
    for t in range(len(T)):
        cv2.fillConvexPoly(lab, P[t], int(t), lineType=cv2.LINE_8, shift=SH)
    # обратные аффинные: экран → исходник, по треугольнику
    S3 = V[T]                                   # (n,3,2) исходные
    D3 = Vd[T]
    Dm = np.concatenate([D3, np.ones((len(T), 3, 1), np.float32)], 2)   # (n,3,3)
    try:
        Inv = np.linalg.solve(Dm, S3)           # (n,3,2): [x y 1] @ Inv = src
    except np.linalg.LinAlgError:
        Inv = np.linalg.lstsq(Dm[0], S3[0], rcond=None)[0][None].repeat(len(T), 0)
    ys, xs = np.nonzero(lab >= 0)
    tl = lab[ys, xs]
    I = Inv[tl]
    mx = np.full((h, w), -10, np.float32)
    my = np.full((h, w), -10, np.float32)
    mx[ys, xs] = xs * I[:, 0, 0] + ys * I[:, 1, 0] + I[:, 2, 0]
    my[ys, xs] = xs * I[:, 0, 1] + ys * I[:, 1, 1] + I[:, 2, 1]
    return cv2.remap(L['img'], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def _render_leg_lbs(L, H, phi):
    A, beta = _leg_state(L, phi)
    K, A = _ik(H, A, L['L1'], L['L2'])
    Ms = [_affine(_ang(K - H) - _ang(L['K'] - L['H']), L['H'], H),
          _affine(_ang(A - K) - _ang(L['A'] - L['K']), L['K'], K),
          _affine(math.radians(beta - L['beta']), L['A'], A)]
    h, w = L['img'].shape[:2]
    acc = np.zeros((h, w, 4), np.float32)
    ws = np.zeros((h, w, 1), np.float32)
    for M, Wb in zip(Ms, L['W']):
        I = cv2.warpAffine(L['img'], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        Ww = cv2.warpAffine(Wb, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)[..., None]
        acc += I * Ww
        ws += Ww
    return acc / np.maximum(ws, 1e-4)


XF = 95.0              # пятка при касании — впереди своего тазобедренного (px)
STRIDE = 320.0         # на сколько опорная стопа уезжает назад за опору (px) — в сцене спрайт едет вперёд так же
SWING_KNEE = 22.0      # добавочный сгиб колена в начале маха, ° (чтобы стопа прошла над полом)


def _knee_rest(u):
    """Желаемый сгиб колена в опоре: амортизация после касания (~15°), дальше почти прямая нога."""
    return 4.0 + 13.0 * math.exp(-((u - 0.2) / 0.09) ** 2)


def _reach(L, kd):
    return math.sqrt(L['L1'] ** 2 + L['L2'] ** 2 + 2 * L['L1'] * L['L2'] * math.cos(math.radians(kd)))


def _stance_state(L, u):
    L = dict(L, xf=XF, S=STRIDE)
    return _stance(L, u)


def _hip_constraints(n=240, legs=((2, 0.0),)):
    """Для каждой фазы — самое высокое положение таза (y), при котором каждая опорная нога достаёт пол с желаемым
    сгибом колена (берём наибольший y среди опорных ног)."""
    R = rig()
    out = np.full(n, -1e9)
    for i in range(n):
        p = i / n
        for k, off in legs:
            L = R['legs'][k]
            ph = (p + off) % 1.0
            if ph < STANCE:
                u = ph / STANCE
                A, _ = _stance_state(L, u)
                dx = A[0] - L['H'][0]
                Lr = _reach(L, _knee_rest(u))
                out[i] = max(out[i], A[1] - math.sqrt(max(Lr * Lr - dx * dx, 1.0)))
    return out


@functools.lru_cache(None)
def _hip_fit(n=480):
    """Таз — гладкая волна (два подъёма за цикл: выше всего в середине опоры, ниже — при переносе веса).
    Амплитуда и фаза подбираются так, чтобы опорные ноги не отрывались от пола, а колени гнулись как можно меньше.
    Дальняя нога на рисунке другой длины → её крепление под юбкой сдвинуто на постоянную величину d."""
    cn = _hip_constraints(n, legs=((2, 0.0),))
    cf = _hip_constraints(n, legs=((1, 0.5),))
    on, of = cn > -1e8, cf > -1e8
    P = np.arange(n) / n
    best = None
    for amp in np.arange(0, 30.5, 0.5):
        for p0 in np.arange(0.0, 0.5, 0.005):
            h = -amp * np.cos(4 * np.pi * (P - p0))
            m = float(np.max((cn - h)[on]))
            d = float(np.max((cf - h)[of])) - m
            cost = float(np.mean((m + h - cn)[on])) + float(np.mean((m + d + h - cf)[of]))
            if best is None or cost < best[0]:
                best = (cost, amp, p0, m, d)
    cost, amp, p0, m, d = best
    print(f'таз: амплитуда {amp:.1f} px, фаза {p0:.3f}, лишний сгиб {cost:.1f} px, сдвиг дальней ноги {d:.1f}')
    return m - amp * np.cos(4 * np.pi * (P - p0)), d


def _hip_curve():
    return _hip_fit()[0]


def _far_offset():
    return _hip_fit()[1]


def _hip_y(p):
    c = _hip_curve()
    n = len(c)
    f = (p % 1.0) * n
    i = int(f)
    return c[i % n] * (1 - (f - i)) + c[(i + 1) % n] * (f - i)


def _angles(H, K, A):
    th = math.atan2(K[0] - H[0], K[1] - H[1])
    ts = math.atan2(A[0] - K[0], A[1] - K[1])
    return th, th - ts                                  # угол бедра от вертикали (+ вперёд), сгиб колена


def _leg_pose(L, phase, off):
    """Колено, голеностоп, наклон стопы для ноги L в момент phase (off — сдвиг фазы ноги)."""
    ph = (phase + off) % 1.0
    dy = _far_offset() if off else 0.0
    hy = lambda t: _hip_y(t) + dy
    H = np.array([L['H'][0], hy(phase)])
    if ph < STANCE:
        A, b = _stance_state(L, ph / STANCE)
        K, A = _ik(H, A, L['L1'], L['L2'])
        return H, K, A, b
    v = (ph - STANCE) / (1 - STANCE)
    # концы маха: отрыв носка (u=1) и касание пяткой (u=0) — из опоры, с высотой таза в те моменты
    t0 = phase - (ph - STANCE)
    t1 = phase + (1 - ph)
    H0 = np.array([L['H'][0], hy(t0)])
    H1 = np.array([L['H'][0], hy(t1)])
    A0, b0 = _stance_state(L, 1.0)
    A1, b1 = _stance_state(L, 0.0)
    K0, A0 = _ik(H0, A0, L['L1'], L['L2'])
    K1, A1 = _ik(H1, A1, L['L1'], L['L2'])
    th0, k0 = _angles(H0, K0, A0)
    th1, k1 = _angles(H1, K1, A1)
    def ss(x):
        x = max(0.0, min(1.0, x))
        return x * x * (3 - 2 * x)
    e = ss(v / 0.85)                                    # бедро выносится вперёд к 85 % маха
    th = th0 + (th1 - th0) * e
    kn = k0 + (k1 - k0) * ss(v) + math.radians(SWING_KNEE) * math.sin(math.pi * v) * (1 - v) / 0.58
    b = b0 + (b1 - b0) * ss(v) + 12.0 * math.sin(math.pi * v)      # в середине маха носок не цепляет пол
    ts = th - kn
    K = H + L['L1'] * np.array([math.sin(th), math.cos(th)])
    A = K + L['L2'] * np.array([math.sin(ts), math.cos(ts)])
    return H, K, A, b


# ── верх: мах рук и вторичное движение (локальная «пластика» картинки, без вырезания) ──
ARM_NEAR = [(446, 292), (484, 290), (500, 330), (504, 420), (556, 428), (610, 434), (650, 448), (650, 505),
            (572, 515), (520, 497), (482, 478), (472, 440), (464, 400), (452, 360)]
ARM_FORE = [(486, 420), (556, 428), (610, 434), (650, 448), (650, 505), (572, 515), (520, 497), (486, 480)]
ARM_FAR = [(204, 484), (285, 480), (285, 530), (262, 610), (212, 612), (200, 560)]
SHOULDER, ELBOW, SHOULDER_FAR = (462.0, 305.0), (488.0, 445.0), (330.0, 300.0)
ARM_SWING = 7.0         # мах передней руки от плеча, °
FORE_SWING = 5.0        # добавочный мах предплечья (с запаздыванием), °
FAR_SWING = 3.5         # задняя кисть (в противофазе), °
HAIR_SWAY = 4.0         # хвосты, px на кончиках
CAPE_SWAY = 3.0         # край плаща, px


@functools.lru_cache(None)
def _upper_masks():
    R = rig()
    h, w = R['upper'].shape[:2]
    def poly(pts, sig):
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
        return cv2.GaussianBlur(m.astype(np.float32), (0, 0), sig)
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    # хвосты и плащ — всё левее корпуса (x < 300), вес растёт сверху вниз
    side = np.clip((300 - X) / 40, 0, 1)
    hair = side * np.clip((Y - 250) / 230, 0, 1) * (Y < 500)
    cape = side * np.clip((Y - 380) / 180, 0, 1) * (Y < 620)
    return dict(near=poly(ARM_NEAR, 5), fore=poly(ARM_FORE, 5), far=poly(ARM_FAR, 6),
                hair=cv2.GaussianBlur(hair.astype(np.float32), (0, 0), 8),
                cape=cv2.GaussianBlur(cape.astype(np.float32), (0, 0), 8), X=X, Y=Y)


def _rot_disp(X, Y, piv, ang, wgt):
    """Смещение точек при повороте вокруг piv на угол ang·wgt (против часовой на экране)."""
    a = ang * wgt
    c, s = np.cos(a), np.sin(a)
    dx, dy = X - piv[0], Y - piv[1]
    return (c * dx + s * dy - dx) * (wgt > 1e-3), (-s * dx + c * dy - dy) * (wgt > 1e-3)


def _upper_motion(U, phase):
    m = _upper_masks()
    X, Y = m['X'], m['Y']
    # передняя рука впереди, когда впереди дальняя нога (её касание пяткой — фаза 0.5); руки чуть запаздывают
    au = math.radians(ARM_SWING) * math.cos(2 * math.pi * (phase - 0.53))
    af = math.radians(FORE_SWING) * math.cos(2 * math.pi * (phase - 0.6))
    ab = -math.radians(FAR_SWING) * math.cos(2 * math.pi * (phase - 0.53))
    dx1, dy1 = _rot_disp(X, Y, SHOULDER, au, m['near'])
    # локоть уже повернулся вместе с плечом
    ex = SHOULDER[0] + math.cos(au) * (ELBOW[0] - SHOULDER[0]) + math.sin(au) * (ELBOW[1] - SHOULDER[1])
    ey = SHOULDER[1] - math.sin(au) * (ELBOW[0] - SHOULDER[0]) + math.cos(au) * (ELBOW[1] - SHOULDER[1])
    dx2, dy2 = _rot_disp(X + dx1, Y + dy1, (ex, ey), af, m['fore'])
    dx3, dy3 = _rot_disp(X, Y, SHOULDER_FAR, ab, m['far'])
    sway = math.sin(4 * math.pi * phase - 1.2)
    DX = dx1 + dx2 + dx3 + HAIR_SWAY * m['hair'] * sway + CAPE_SWAY * m['cape'] * math.sin(4 * math.pi * phase - 1.7)
    DY = dy1 + dy2 + dy3
    # обратное отображение: где взять пиксель для точки p (две итерации — точнее при поворотах)
    mx, my = X - DX, Y - DY
    for _ in range(2):
        DXs = cv2.remap(DX.astype(np.float32), mx, my, cv2.INTER_LINEAR)
        DYs = cv2.remap(DY.astype(np.float32), mx, my, cv2.INTER_LINEAR)
        mx, my = X - DXs, Y - DYs
    return cv2.remap(U, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def leg_frame(phase):
    R = rig()
    legs = [(1, 0.5), (2, 0.0)]                          # сначала дальняя нога, потом ближняя
    hy = _hip_y(phase)
    bob = hy - R['legs'][2]['H'][1]
    out = np.zeros_like(R['upper'])
    for k, off in legs:
        L = R['legs'][k]
        H, K, A, b = _leg_pose(L, phase, off)
        img = _render_leg(L, H, phase + off, (K, A, b))
        a = img[..., 3:4] / 255
        out = img + out * (1 - a)                       # премультипликация
    # верх поверх, обрезан у подола, со сдвигом таза
    U = _upper_motion(R['upper'].astype(np.float32), phase)
    U = anim._translate(np.clip(U, 0, 255).astype(np.uint8), np.array([0, bob], np.float32)).astype(np.float32)
    yy = np.arange(U.shape[0], dtype=np.float32)[:, None]
    xx = np.arange(U.shape[1], dtype=np.float32)[None, :]
    mu = np.clip((R['hem'] + bob + 4 - yy) / 6 + 0.5, 0, 1)
    # задняя кисть свисает ниже подола (левее ног) — её не обрезаем
    mu = np.maximum(mu, (xx < 285) * np.clip((R['hem'] + bob + 45 - yy) / 6 + 0.5, 0, 1))
    U[..., 3] *= mu
    U[..., :3] *= U[..., 3:4] / 255
    ua = U[..., 3:4] / 255
    out = U + out * (1 - ua)
    al = np.clip(out[..., 3:4], 1e-3, 255)
    rgb = np.clip(out[..., :3] * 255 / al, 0, 255)
    return np.concatenate([rgb, np.clip(out[..., 3:4], 0, 255)], -1).astype(np.uint8)


if __name__ == '__main__':
    import subprocess
    import sys
    from PIL import Image
    import snap_preview as SP
    SP.align_all([SRC, 'walk_a'])
    anim.FR = SP.AL
    anim.pose.cache_clear()
    period = float(sys.argv[1]) if len(sys.argv) > 1 else 1.1     # полный цикл (два шага), с
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 3.3
    Wd, Hd, FPS = 540, 960, 60
    out = SP.HERE / 'build' / 'walk_rig.mp4'
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{Wd}x{Hd}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', str(out)], stdin=subprocess.PIPE)
    for fi in range(int(secs * FPS)):
        a = leg_frame(fi / FPS / period)
        bg = Image.new('RGBA', (Wd, Hd), (250, 248, 255, 255))
        m = Image.fromarray(a)
        m = m.resize((int(m.width * 0.72), int(m.height * 0.72)), Image.LANCZOS)
        bg.alpha_composite(m, (Wd // 2 - m.width // 2, 830 - int(990 * 0.72)))
        p.stdin.write(np.array(bg.convert('RGB')).tobytes())
    p.stdin.close()
    p.wait()
    print(out)
