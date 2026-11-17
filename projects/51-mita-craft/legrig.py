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
TOE_OFF = 30.0         # угол отрыва пятки (носок на полу), °
HEEL_STRIKE = 20.0     # носок вверх при постановке на пятку, °


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
    if u < 0.12:
        b = HEEL_STRIKE * (1 - u / 0.12)
        return _foot_at(L, 'heel', (hx, GROUND), b), b
    if u < 0.65:
        return _foot_at(L, 'heel', (hx, GROUND), 0.0), 0.0
    b = -TOE_OFF * (u - 0.65) / 0.35
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


def _render_leg(L, H, phi):
    A, beta = _leg_state(L, phi)
    K, A = _ik(H, A, L['L1'], L['L2'])
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


def leg_frame(phase):
    R = rig()
    bob = -BOB * math.cos(4 * math.pi * (phase - STANCE / 4))   # таз выше всего на середине опоры
    out = np.zeros_like(R['upper'])
    for k, off in ((1, 0.5), (2, 0.0)):                 # сначала дальняя нога, потом ближняя
        L = R['legs'][k]
        H = L['H'] + np.array([0.0, bob])
        img = _render_leg(L, H, phase + off)
        a = img[..., 3:4] / 255
        out = img + out * (1 - a)                       # премультипликация
    # верх поверх, обрезан у подола, со сдвигом таза
    U = anim._translate(R['upper'].astype(np.uint8), np.array([0, bob], np.float32)).astype(np.float32)
    yy = np.arange(U.shape[0], dtype=np.float32)[:, None]
    mu = np.clip((R['hem'] + bob + 4 - yy) / 6 + 0.5, 0, 1)
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
