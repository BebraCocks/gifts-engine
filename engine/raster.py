"""Minimal numpy triangle rasterizer: z-buffer, perspective-correct attributes, flat lighting."""
import numpy as np


def rot(yaw, pitch, roll=0.0):
    cy, sy = np.cos(yaw), np.sin(yaw)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cr, sr = np.cos(roll), np.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
    return Rz @ Rx @ Ry


SMALL = 8      # triangles whose box fits in SMALL x SMALL px are rasterized all at once (vectorised)


def _small_batch(Vs, iz, F, attrs, W, H, sel, depth, fid, out):
    """All small triangles in one numpy pass: candidate pixels of every box, z-test, nearest wins."""
    tri = np.nonzero(sel)[0]
    if not len(tri):
        return
    P = Vs[F[tri]]                                             # (m, 3, 2)
    x0 = np.maximum(np.floor(P[:, :, 0].min(1)).astype(int), 0)
    y0 = np.maximum(np.floor(P[:, :, 1].min(1)).astype(int), 0)
    oy, ox = np.divmod(np.arange(SMALL * SMALL), SMALL)
    xs = x0[:, None] + ox[None, :]                             # (m, S*S) pixel indices
    ys = y0[:, None] + oy[None, :]
    xx, yy = xs + 0.5, ys + 0.5
    px, py = P[:, :, 0], P[:, :, 1]
    area = (px[:, 1] - px[:, 0]) * (py[:, 2] - py[:, 0]) - (px[:, 2] - px[:, 0]) * (py[:, 1] - py[:, 0])
    w0 = ((px[:, 1:2] - xx) * (py[:, 2:3] - yy) - (px[:, 2:3] - xx) * (py[:, 1:2] - yy)) / area[:, None]
    w1 = ((px[:, 2:3] - xx) * (py[:, 0:1] - yy) - (px[:, 0:1] - xx) * (py[:, 2:3] - yy)) / area[:, None]
    w2 = 1 - w0 - w1
    m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0) & (xs < W) & (ys < H)
    if not m.any():
        return
    ti, kk = np.nonzero(m)
    a, b, c = F[tri[ti], 0], F[tri[ti], 1], F[tri[ti], 2]
    q0, q1, q2 = w0[ti, kk] * iz[a], w1[ti, kk] * iz[b], w2[ti, kk] * iz[c]
    s = q0 + q1 + q2
    z = 1.0 / s
    key = ys[ti, kk] * W + xs[ti, kk]
    order = np.lexsort((tri[ti], z, key))                      # per pixel: nearest first (ties: lower face id)
    key_o = key[order]
    first = np.ones(len(order), bool)
    first[1:] = key_o[1:] != key_o[:-1]
    o = order[first]
    yv, xv = np.divmod(key[o], W)
    depth[yv, xv] = z[o]
    fid[yv, xv] = tri[ti[o]]
    out[yv, xv] = (q0[o, None] * attrs[a[o]] + q1[o, None] * attrs[b[o]] + q2[o, None] * attrs[c[o]]) / s[o, None]


def rasterize(Vs, zc, F, attrs, W, H):
    """Vs: (n,2) screen xy, zc: (n,) camera depth (>0), F: (m,3), attrs: (n,K).

    Returns depth (H,W), face id (H,W), interpolated attrs (H,W,K)."""
    depth = np.full((H, W), np.inf)
    fid = np.full((H, W), -1, int)
    K = attrs.shape[1]
    out = np.zeros((H, W, K))
    iz = 1.0 / zc
    P = Vs[F]
    lo, hi = np.floor(P.min(1)).astype(int), np.ceil(P.max(1)).astype(int)
    lo, hi = np.maximum(lo, 0), np.minimum(hi, [W - 1, H - 1])
    area = ((P[:, 1, 0] - P[:, 0, 0]) * (P[:, 2, 1] - P[:, 0, 1]) - (P[:, 2, 0] - P[:, 0, 0]) * (P[:, 1, 1] - P[:, 0, 1]))
    ok = (hi[:, 0] >= lo[:, 0]) & (hi[:, 1] >= lo[:, 1]) & (np.abs(area) >= 1e-9)
    small = ok & ((hi - lo).max(1) < SMALL)
    _small_batch(Vs, iz, F, attrs, W, H, small, depth, fid, out)
    for t in np.nonzero(ok & ~small)[0]:
        a, b, c = F[t]
        p = Vs[[a, b, c]]
        x0, y0 = np.floor(p.min(0)).astype(int)
        x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        area = (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1]) - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
        if abs(area) < 1e-9:
            continue
        yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1] + 0.5
        w0 = ((p[1, 0] - xx) * (p[2, 1] - yy) - (p[2, 0] - xx) * (p[1, 1] - yy)) / area
        w1 = ((p[2, 0] - xx) * (p[0, 1] - yy) - (p[0, 0] - xx) * (p[2, 1] - yy)) / area
        w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any():
            continue
        q0, q1, q2 = w0[m] * iz[a], w1[m] * iz[b], w2[m] * iz[c]
        s = q0 + q1 + q2
        z = 1.0 / s
        ys_, xs_ = (yy[m] - 0.5).astype(int), (xx[m] - 0.5).astype(int)
        closer = z < depth[ys_, xs_]
        if not closer.any():
            continue
        ys_, xs_ = ys_[closer], xs_[closer]
        q0, q1, q2, s = q0[closer], q1[closer], q2[closer], s[closer]
        depth[ys_, xs_] = z[closer]
        fid[ys_, xs_] = t
        out[ys_, xs_] = (q0[:, None] * attrs[a] + q1[:, None] * attrs[b] + q2[:, None] * attrs[c]) / s[:, None]
    return depth, fid, out


def project(Vw, W, H, dist, fov_deg, center=(0.0, 0.0)):
    """Vw: camera-space-ish points (x right, y up, z toward camera). Camera on +z at `dist`."""
    f = (H / 2) / np.tan(np.radians(fov_deg) / 2)
    zc = dist - Vw[:, 2]
    xs = W / 2 + f * (Vw[:, 0] - center[0]) / zc
    ys = H / 2 - f * (Vw[:, 1] - center[1]) / zc
    return np.stack([xs, ys], 1), zc
