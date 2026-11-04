"""Locations v3: Durov's post (phone), hacker den (Anonymous), Havana (Che Guevara),
arena (Spartacus), crypto vault (Satoshi). Conventions as in shots.py."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

from lib import (glow_mat, box, cyl, sphere, torus, plane, card, text, empty, blob, sun, point, spot, area, camera,
                 look, path, smooth, ease_out, ease_in, spring, lerp, vlerp, shake, mat, emissive, world_gradient,
                 scatter)
from events import E

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
A = PROJECT / 'build' / 'assets'
PI = math.pi
UP = (PI / 2, 0, 0)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def _img(name, w, h, draw):
    p = A / f'{name}.png'
    if not p.exists():
        from PIL import Image, ImageDraw
        im = Image.new('RGB', (w, h), (0, 0, 0))
        draw(im, ImageDraw.Draw(im))
        im.save(p)
    return p


def tex_emit(path, strength=2.0, name='screen'):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = bpy.data.images.load(str(path), check_existing=True)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[1].default_value = strength
    nt.links.new(tx.outputs['Color'], e.inputs[0])
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs[0])
    return m


def code_texture(seed, green=True):
    def draw(im, d):
        r = random.Random(seed)
        y = 8
        while y < im.height - 10:
            x = 10 + r.randint(0, 4) * 18
            for _ in range(r.randint(2, 6)):
                w = r.randint(20, 90)
                c = (40, 230, 120) if green and r.random() < 0.7 else (120, 200, 255) if r.random() < 0.6 else (230, 230, 240)
                d.rectangle((x, y, x + w, y + 7), fill=c)
                x += w + 10
                if x > im.width - 40:
                    break
            y += 16
    return _img(f'code_{seed}', 320, 200, draw)


def towers(seed, n, rr, h, tm, center=(0, 0), zoff=0.0, keep_clear=None):
    r = random.Random(seed)
    for _ in range(n):
        ang = r.uniform(0, 2 * PI)
        dist = r.uniform(*rr)
        x, y = center[0] + math.cos(ang) * dist, center[1] + math.sin(ang) * dist
        if keep_clear and keep_clear(x, y):
            r.uniform(2.5, 6), r.uniform(*h), r.uniform(0.7, 1.3)
            continue
        w, hh = r.uniform(2.5, 6), r.uniform(*h)
        box((w, w * r.uniform(0.7, 1.3), hh), (x, y, hh / 2 + zoff), m=tm, bevel=0)


# ====================================================================== S15 Durov's post: a giant phone over the night city
def S15_phone(sh, t0, t1):
    from shots import window_texture, tower_mat
    world_gradient((0.03, 0.03, 0.1), (0.2, 0.1, 0.3), 1.0)
    tm = tower_mat('city', window_texture('win_night', 3, warm=True), strength=2.4, density=0.8)
    towers(41, 170, (6, 60), (3, 24), tm, (0, 12), -14, keep_clear=lambda x, y: abs(x) < 16 and y < 22)
    box((200, 200, 1), (0, 12, -14.5), m=mat((0.05, 0.05, 0.09), rough=0.6), bevel=0)
    sphere(2.0, (18, 70, 22), emissive((1.0, 0.95, 0.85), 3.0))
    # the phone (screen content is composited at the four corner anchors)
    ph = empty('phone', (0, 6, 3.0))
    body = mat((0.06, 0.06, 0.08), rough=0.25, metal=0.6, coat=0.8)
    box((3.1, 0.32, 6.3), (0, 0, 0), m=body, bevel=0.42, seg=6, parent=ph)
    box((2.86, 0.05, 6.06), (0, -0.16, 0), m=mat((0.01, 0.01, 0.015), rough=0.1), bevel=0.3, seg=6, parent=ph)
    for i, (sx, sz) in enumerate(((-1, 1), (1, 1), (1, -1), (-1, -1))):
        e = empty(f'scr{i}', (sx * 1.33, -0.2, sz * 2.88), ph)
        sh.anchor(f'screen{i}', e, 0.0)
    glow = point((0, 3.8, 3.2), 0.0, (0.45, 0.65, 1.0), r=1.5)
    sh.track(glow.data, 'energy')
    sh.track(ph, 'location', 'rotation_euler')
    # light rays / notification rings
    ring_m = glow_mat((0.4, 0.7, 1.0), 0.0, 0.4)
    rs = ring_m.node_tree.nodes['Emission'].inputs[1]
    sh.track(rs, 'default_value')
    rings = []
    for k in range(3):
        rg = torus(2.2, 0.03, (0, 6.2, 3.0), (PI / 2, 0, 0), m=ring_m)
        rings.append((rg, k))
        sh.track(rg, 'scale')
    stars = emissive((1, 1, 1), 3.0)
    for p in scatter(5, 120, (-60, 60), (40, 90), (8, 50)):
        sphere(0.08, p, stars, seg=6)
    area((0, -4, 8), (0, 6, 3), 400, 6, (0.6, 0.7, 1.0))
    cam = camera(28, dof=6.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    wr, hr, am = E['wrote'], E['hour'], E['among']

    def update(t):
        ph.location = (0, 6, 3.0 + 0.12 * math.sin(t * 1.3))
        ph.rotation_euler = (0.05 * math.sin(t * 0.9), 0.04 * math.sin(t * 0.7), 0.1 * (1 - smooth(seg(t, t0, wr))))
        glow.data.energy = 600 + 1800 * smooth(seg(t, wr - 0.2, wr + 0.4))
        rs.default_value = 3.0 * (smooth(seg(t, wr - 0.1, wr + 0.2)))
        for rg, k in rings:
            u = ((t - wr) * 0.8 + k / 3) % 1.0 if t > wr else 0.0
            s = 1 + 1.6 * u
            rg.scale = (s * (t > wr) + 1e-3, s * (t > wr) + 1e-3, 1)
        keys = [(t0, (-6.0, -18.0, 9.0)), (wr - 0.3, (-1.0, -5.5, 4.0)), (am, (0.3, -2.2, 3.2)),
                (t1 - 0.6, (0.1, -0.6, 3.05)), (t1, (0.0, 3.2, 3.0))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 6, 2.0)), (wr, (0, 6, 3.0)), (t1, (0, 6, 3.0))])
        look(cam, p, tgt, 0.12 * (1 - smooth(seg(t, t0, wr))))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S16 hacker den (Anonymous)
def S16_hacker(sh, t0, t1):
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.005, 0.006, 0.01, 1)
    box((14, 14, 0.2), (0, 2, -0.1), m=mat((0.05, 0.05, 0.07), rough=0.4), bevel=0)
    wall = mat((0.07, 0.07, 0.1), rough=0.8)
    box((14, 0.2, 5), (0, 3.2, 2.5), m=wall, bevel=0)
    box((0.2, 14, 5), (-4, 2, 2.5), m=wall, bevel=0)
    neon = emissive((0.7, 0.2, 1.0), 6.0)
    box((7, 0.05, 0.05), (0, 3.08, 4.2), m=neon, bevel=0)
    box((0.05, 7, 0.05), (-3.88, 0, 4.2), m=emissive((0.1, 0.9, 0.7), 5.0), bevel=0)
    desk = mat((0.12, 0.12, 0.14), rough=0.35)
    box((3.6, 1.3, 0.08), (0, 1.5, 0.95), m=desk, bevel=0.02)
    for x in (-1.7, 1.7):
        box((0.08, 1.2, 0.95), (x, 1.5, 0.47), m=desk, bevel=0.01)
    scr_ms = []
    for k, (x, rz, z) in enumerate(((-1.15, 0.35, 1.6), (0.0, 0.0, 1.65), (1.15, -0.35, 1.6), (0.0, 0.0, 2.45))):
        mon = empty('mon', (x, 2.0, z))
        mon.rotation_euler = (0, 0, rz)
        box((1.1, 0.06, 0.68), (0, 0.03, 0), m=mat((0.02, 0.02, 0.03)), bevel=0.02, parent=mon)
        sm = tex_emit(code_texture(10 + k, green=(k != 3)), 2.2)
        plane((1.02, 0.6), (0, -0.005, 0), UP, m=sm, parent=mon)
        scr_ms.append(sm)
    box((1.4, 0.45, 0.04), (0, 1.15, 1.0), m=mat((0.06, 0.06, 0.08)), bevel=0.01)
    box((1.42, 0.47, 0.01), (0, 1.15, 0.98), m=emissive((0.9, 0.2, 0.9), 2.0), bevel=0)
    for x in (1.35, 1.5):
        cyl(0.05, 0.16, (x, 1.0, 1.07), m=mat((0.2, 0.9, 0.3), metal=0.8, rough=0.2))
    # server rack with blinking LEDs
    rack = box((0.9, 0.8, 2.6), (-2.9, 1.8, 1.3), m=mat((0.05, 0.05, 0.06), metal=0.5, rough=0.4), bevel=0.02)
    leds = []
    r = random.Random(3)
    for i in range(36):
        lm = emissive((0.2, 1.0, 0.4) if r.random() < 0.7 else (1.0, 0.4, 0.1), 0.0)
        sphere(0.025, (-2.6 + r.uniform(-0.25, 0.2), 1.39, 0.3 + (i % 18) * 0.12), lm, seg=6)
        leds.append((lm.node_tree.nodes['Emission'].inputs[1], r.uniform(2, 9), r.uniform(0, 6)))
        sh.track(leds[-1][0], 'default_value')
    for i in range(6):
        cyl(0.025, 2.0, (-2.4 + i * 0.12, 1.4, 0.4), (0.4, 1.3, 0), m=mat((0.1 + 0.1 * (i % 3), 0.1, 0.12)), verts=8, bevel=0)
    # chair
    cm = mat((0.1, 0.1, 0.12), rough=0.5)
    box((0.7, 0.65, 0.12), (0.6, 0.4, 0.55), m=cm, bevel=0.04)
    box((0.7, 0.12, 0.8), (0.6, 0.05, 1.0), m=cm, bevel=0.04)
    cyl(0.05, 0.45, (0.6, 0.4, 0.27), m=cm)
    for i in range(3):
        box((0.5, 0.7, 0.02), (2.8, 3.08, 1.6 + i * 0.05), m=mat((0.8, 0.8, 0.85), rough=0.9), bevel=0)
    blob((0.05, 1.45, 0.99), 0.5, 0.5)
    sh.anchor('m_anon', (0.05, 1.45, 0.99 + 0.6), 0.6)
    key = area((1.5, -1.5, 3.5), (0, 1.5, 1.2), 120, 3, (0.5, 0.9, 1.0))
    point((0, 1.4, 2.0), 80, (0.3, 1.0, 0.5), r=0.5)
    cam = camera(26, dof=2.8)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    an, mk = E['anon'], E['mask']

    def update(t):
        for sock, f, ph in leds:
            sock.default_value = 6.0 * (math.sin(t * f + ph) > 0.2)
        keys = [(t0, (-2.0, -2.2, 1.8)), (an + 0.5, (-0.7, -0.9, 1.6)), (mk + 0.5, (0.3, -0.35, 1.55)),
                (t1, (0.5, 0.15, 1.45))]
        p = path(t, keys)
        tgt = path(t, [(t0, (-1.0, 1.8, 1.4)), (an, (0.0, 1.5, 1.55)), (t1, (0.05, 1.5, 1.55))])
        look(cam, p, tgt, 0.06 * math.sin(t * 0.8))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S17 Havana street (Che Guevara)
def _cuba_flag():
    def draw(im, d):
        W, H = im.size
        for i in range(5):
            d.rectangle((0, i * H / 5, W, (i + 1) * H / 5), fill=(0, 42, 143) if i % 2 == 0 else (255, 255, 255))
        d.polygon([(0, 0), (W * 0.43, H / 2), (0, H)], fill=(207, 20, 43))
        cx, cy, R = W * 0.15, H / 2, H * 0.14
        pts = []
        for k in range(10):
            a = -PI / 2 + k * PI / 5
            rr = R if k % 2 == 0 else R * 0.4
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=(255, 255, 255))
    return _img('cuba_flag', 600, 300, draw)


def S17_havana(sh, t0, t1):
    world_gradient((0.15, 0.3, 0.75), (1.0, 0.6, 0.35), 0.45)
    box((40, 60, 0.2), (0, 10, -0.1), m=mat((0.35, 0.32, 0.3), rough=0.7), bevel=0)
    box((2.2, 60, 0.18), (-4.6, 10, 0.09), m=mat((0.75, 0.7, 0.62), rough=0.8), bevel=0.02)
    box((2.2, 60, 0.18), (4.6, 10, 0.09), m=mat((0.75, 0.7, 0.62), rough=0.8), bevel=0.02)
    pastel = [(0.95, 0.55, 0.6), (0.4, 0.8, 0.75), (0.98, 0.85, 0.45), (0.55, 0.7, 0.95), (0.98, 0.65, 0.35),
              (0.75, 0.55, 0.85)]
    white = mat((0.97, 0.95, 0.9), rough=0.6)
    r = random.Random(9)
    for side in (-1, 1):
        y = -6
        k = 0
        while y < 40:
            w = r.uniform(3.2, 4.6)
            h = r.uniform(5.5, 9)
            c = pastel[(k + (side > 0) * 3) % 6]
            x = side * 7.6
            box((4.4, w - 0.1, h), (x, y + w / 2, h / 2), m=mat(c, rough=0.75), bevel=0.05)
            box((4.6, w + 0.05, 0.3), (x, y + w / 2, h + 0.15), m=white, bevel=0.03)
            for fl in range(1, int(h // 2.6) + 1):
                z = fl * 2.6 - 0.7
                for j in range(2):
                    wy = y + w * (0.3 + 0.4 * j)
                    box((0.1, 0.85, 1.4), (x - side * 2.21, wy, z), m=mat((0.15, 0.35, 0.45), rough=0.4), bevel=0.02)
                    box((0.14, 1.05, 0.12), (x - side * 2.23, wy, z + 0.78), m=white, bevel=0.02)
                if fl > 0 and r.random() < 0.6:
                    box((0.7, w * 0.7, 0.08), (x - side * 2.55, y + w / 2, z - 0.75), m=white, bevel=0.02)
                    for q in range(6):
                        cyl(0.02, 0.6, (x - side * 2.85, y + w * 0.17 + q * w * 0.12, z - 0.45), m=mat((0.1, 0.1, 0.1)), verts=6, bevel=0)
            y += w
            k += 1
    # vintage car (Che stands on the bonnet)
    car = empty('car', (0.8, 9.0, 0))
    cm = mat((0.25, 0.8, 0.78), rough=0.25, coat=0.9)
    chrome = mat((0.9, 0.9, 0.92), metal=1.0, rough=0.15)
    box((2.0, 4.6, 0.75), (0, 0, 0.75), m=cm, bevel=0.3, seg=5, parent=car)
    box((1.8, 2.2, 0.7), (0, 0.4, 1.4), m=cm, bevel=0.3, seg=5, parent=car)
    box((1.7, 2.0, 0.5), (0, 0.4, 1.42), m=mat((0.2, 0.3, 0.35), rough=0.05), bevel=0.2, parent=car)
    box((2.1, 0.2, 0.25), (0, -2.35, 0.55), m=chrome, bevel=0.08, parent=car)
    box((2.1, 0.2, 0.25), (0, 2.35, 0.55), m=chrome, bevel=0.08, parent=car)
    for x in (-0.95, 0.95):
        for y in (-1.5, 1.5):
            cyl(0.42, 0.3, (x, y, 0.42), (0, PI / 2, 0), m=mat((0.05, 0.05, 0.05), rough=0.8), parent=car)
            cyl(0.22, 0.32, (x, y, 0.42), (0, PI / 2, 0), m=chrome, parent=car)
    for x in (-0.65, 0.65):
        sphere(0.15, (x, -2.33, 0.95), emissive((1.0, 0.95, 0.8), 2.0), parent=car)
    blob((0.8, 7.2, 1.13), 0.45, 0.45)
    sh.anchor('m_che', (0.8, 7.2, 1.13 + 0.62), 0.62)
    # palms + flag
    for x, y in ((-3.8, 2), (3.9, 15), (-3.9, 22)):
        for i in range(8):
            cyl(0.14 - i * 0.008, 0.6, (x + 0.05 * i, y, 0.3 + i * 0.58), (0.0, 0.05 * i, 0), m=mat((0.5, 0.38, 0.25)), bevel=0)
        for a in range(7):
            ang = a * 2 * PI / 7
            box((2.0, 0.35, 0.05), (x + 0.4 + math.cos(ang) * 0.9, y + math.sin(ang) * 0.9, 4.9 - 0.25), (0.0, 0.35, ang),
                m=mat((0.2, 0.55, 0.25), rough=0.6), bevel=0.02)
    cyl(0.05, 4.2, (-2.6, 11.5, 2.1), m=chrome)
    flag = card(_cuba_flag(), 1.0, (-2.55, 11.5, 3.2), (PI / 2, 0, -PI / 2), aspect=2.0)
    sh.track(flag, 'rotation_euler', 'scale')
    sun((1.25, 0.0, -2.3), 2.6, (1.0, 0.7, 0.42))
    area((0, 0, 9), (0, 9, 0), 250, 10, (0.6, 0.75, 1.0))
    cam = camera(26, dof=5.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    ch, fl, cg = E['che'], E['flag'], E['cigar']

    def update(t):
        flag.rotation_euler = (PI / 2 + 0.05 * math.sin(t * 6), 0, -PI / 2 + 0.25 * math.sin(t * 2.2))
        flag.scale = (2.0 * (0.92 + 0.08 * math.sin(t * 5)), 1.0, 1)
        keys = [(t0, (2.6, -6.0, 0.7)), (ch + 0.6, (1.7, 3.0, 1.35)), (fl + 0.3, (0.2, 4.2, 1.6)),
                (t1, (-0.2, 4.8, 1.7))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0.5, 10, 1.6)), (ch + 0.4, (0.8, 7.2, 1.75)), (fl, (-0.3, 8.5, 2.1)), (cg, (0.8, 7.2, 1.8)),
                       (t1, (0.8, 7.2, 1.8))])
        look(cam, p, tgt, 0.05 * math.sin(t))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S18 arena (Spartacus) + "there are rarer ones"
def S18_arena(sh, t0, t1):
    arena_banner()
    world_gradient((0.25, 0.35, 0.65), (0.95, 0.65, 0.45), 0.7)
    W = bpy.context.scene.world.node_tree.nodes['Background'].inputs[1]
    sh.track(W, 'default_value')
    cyl(16, 0.2, (0, 0, -0.1), m=mat((0.82, 0.68, 0.48), rough=0.95), bevel=0, verts=64)
    stone = mat((0.78, 0.68, 0.55), rough=0.8)
    stone2 = mat((0.62, 0.52, 0.42), rough=0.85)
    R = 15
    n = 36
    for k in range(n):
        a = k / n * 2 * PI
        x, y = math.cos(a) * R, math.sin(a) * R
        for lvl in range(3):
            z0 = lvl * 3.4
            box((0.9, 0.9, 2.6), (x, y, z0 + 1.3), (0, 0, a), m=stone, bevel=0.06)
            box((2.8, 1.1, 0.8), (math.cos(a + PI / n) * R, math.sin(a + PI / n) * R, z0 + 3.0), (0, 0, a + PI / n + PI / 2),
                m=stone2, bevel=0.06)
        if k % 6 == 0:
            ban = card(A / 'arena_banner.png' if (A / 'arena_banner.png').exists() else A / 'poster_text.png', 3.0,
                       (math.cos(a) * (R - 0.6), math.sin(a) * (R - 0.6), 3.6), (PI / 2, 0, a + PI / 2), emit=0.2, aspect=0.4)
    # stands with a hint of crowd
    r = random.Random(5)
    crowd = [mat(c, rough=0.8) for c in ((0.8, 0.3, 0.25), (0.9, 0.85, 0.75), (0.4, 0.45, 0.7), (0.85, 0.65, 0.3))]
    for k in range(260):
        a = r.uniform(0, 2 * PI)
        rr = r.uniform(R + 1.2, R + 7)
        z = 1.0 + (rr - R) * 1.4
        sphere(0.22, (math.cos(a) * rr, math.sin(a) * rr, z), crowd[k % 4], seg=8)
    for k in range(6):
        cyl(R + 1 + k * 1.2, 0.6, (0, 0, 0.6 + k * 1.7), m=stone2, bevel=0, verts=64, open_ends=True)
    # centre: stone block + braziers
    box((1.6, 1.6, 1.0), (0, 0, 0.5), m=stone, bevel=0.08)
    blob((0, 0, 1.0), 0.6, 0.5)
    sh.anchor('m_sparta', (0, 0, 1.0 + 0.62), 0.62)
    fires = []
    for x, y in ((-2.2, 1.2), (2.2, 1.2), (-2.6, -2.0), (2.6, -2.0)):
        cyl(0.1, 1.4, (x, y, 0.7), m=mat((0.2, 0.15, 0.1), metal=0.7))
        cyl(0.35, 0.3, (x, y, 1.45), m=mat((0.25, 0.18, 0.1), metal=0.8), r2=0.2)
        fm = glow_mat((1.0, 0.5, 0.15), 6.0, 0.2)
        fl = sphere(0.28, (x, y, 1.75), fm, scale=(1, 1, 1.6), seg=12)
        L = point((x, y, 2.0), 300, (1.0, 0.55, 0.2), r=0.3)
        fires.append((fl, L, fm.node_tree.nodes['Emission'].inputs[1], x + y))
        sh.track(fl, 'scale')
        sh.track(L.data, 'energy')
    sunL = sun((1.1, 0.0, 2.0), 3.0, (1.0, 0.75, 0.5))
    sh.track(sunL.data, 'energy')
    cam = camera(26, dof=5.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    sp, gl, ld, rb, rr_ = E['sparta'], E['glad'], E['leader'], E['rebellion'], E['rarer']
    dim0 = rr_ - 1.6

    def update(t):
        dim = 1 - 0.8 * smooth(seg(t, dim0, rr_ + 0.4))
        W.default_value = 0.7 * dim + 0.03
        sunL.data.energy = 3.0 * dim
        for fl, L, sock, ph in fires:
            f = 0.85 + 0.15 * math.sin(t * 13 + ph) * math.sin(t * 7.3 + ph * 2)
            fl.scale = (f, f, 1.6 * f)
            L.data.energy = 300 * f * (0.6 + 0.4 * dim)
        keys = [(t0, (-9.0, -9.0, 5.5)), (sp + 0.5, (-3.2, -4.5, 1.6)), (gl + 0.6, (-0.9, -2.9, 0.9)),
                (ld + 0.2, (0.6, -2.2, 0.55)), (rb + 0.4, (1.2, -2.5, 0.8)), (t1, (0.3, -6.5, 2.4))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 0, 1.5)), (sp + 0.5, (0, 0, 1.6)), (ld, (0, 0, 1.8)), (rb + 0.4, (0, 0, 1.7)),
                       (t1, (0, 0, 1.5))])
        look(cam, p, tgt, -0.05 * math.sin(t * 0.7))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


def arena_banner():
    def draw(im, d):
        W, H = im.size
        d.rectangle((0, 0, W, H), fill=(150, 20, 22))
        d.rectangle((10, 10, W - 10, H - 10), outline=(230, 180, 70), width=8)
        d.polygon([(W / 2, H * 0.3), (W * 0.75, H * 0.55), (W / 2, H * 0.8), (W * 0.25, H * 0.55)], fill=(230, 180, 70))
    return _img('arena_banner', 160, 400, draw)


# ====================================================================== S19 crypto vault (Satoshi)
def S19_crypto(sh, t0, t1):
    world_gradient((0.5, 0.32, 0.12), (0.25, 0.15, 0.06), 0.8)
    box((30, 30, 0.2), (0, 4, -0.1), m=mat((0.12, 0.09, 0.06), metal=0.6, rough=0.25), bevel=0)
    wall = mat((0.18, 0.13, 0.08), metal=0.7, rough=0.35)
    box((30, 0.3, 8), (0, 7, 4), m=wall, bevel=0)
    for i in range(-5, 6):
        box((0.3, 0.2, 8), (i * 2.5, 6.8, 4), m=mat((0.5, 0.36, 0.15), metal=1.0, rough=0.3), bevel=0.05)
    gold = mat((1.0, 0.72, 0.28), metal=0.75, rough=0.32, emit=(1.0, 0.6, 0.15), emit_strength=0.12)
    gold2 = mat((0.95, 0.62, 0.2), metal=0.75, rough=0.38, emit=(1.0, 0.55, 0.12), emit_strength=0.1)
    r = random.Random(11)
    # coin pile (cone of coins)
    for k in range(420):
        rr = r.random() ** 0.6 * 2.2
        a = r.uniform(0, 2 * PI)
        z = max(0.03, (1 - rr / 2.2) * 1.4 + r.uniform(-0.05, 0.05))
        cyl(0.17, 0.04, (math.cos(a) * rr, 2.0 + math.sin(a) * rr, z), (r.uniform(-0.4, 0.4), r.uniform(-0.4, 0.4), 0),
            m=gold if k % 3 else gold2, bevel=0.01, verts=16)
    blob((0, 2.0, 1.42), 0.55, 0.4)
    sh.anchor('m_satoshi', (0, 2.0, 1.42 + 0.62), 0.62)
    # mining rigs with LEDs
    leds = []
    for side in (-1, 1):
        for j in range(4):
            x = side * (4.2 + j * 1.6)
            box((1.2, 1.0, 2.4), (x, 4.5, 1.2), m=mat((0.08, 0.08, 0.09), metal=0.5, rough=0.4), bevel=0.04)
            for q in range(6):
                lm = emissive((0.3, 1.0, 0.4) if q % 2 else (1.0, 0.6, 0.1), 0.0)
                sphere(0.04, (x - 0.4 + q * 0.16, 3.98, 2.0), lm, seg=6)
                leds.append((lm.node_tree.nodes['Emission'].inputs[1], r.uniform(3, 9), r.uniform(0, 6)))
                sh.track(leds[-1][0], 'default_value')
            for q in range(4):
                cyl(0.2, 0.05, (x - 0.3 + (q % 2) * 0.6, 3.97, 0.6 + (q // 2) * 0.7), (PI / 2, 0, 0), m=mat((0.2, 0.2, 0.22)))
    sym = text('₿', 2.6, (0, 6.7, 4.9), UP, m=emissive((1.0, 0.7, 0.2), 2.2), extrude=0.15)
    sh.track(sym, 'rotation_euler')
    rays = glow_mat((1.0, 0.8, 0.4), 0.8, 0.3)
    for k in range(5):
        cyl(0.4 + k * 0.15, 7, (-1.5 + k * 0.75, 3.5, 4.0), (0.35, 0.25 - k * 0.12, 0), m=rays, bevel=0, open_ends=True, r2=0.05)
    spot((0, 0.5, 6.0), (0, 2.0, 1.4), 3000, (1.0, 0.82, 0.5), 35, 0.5)
    point((0, 1.0, 3.5), 200, (1.0, 0.75, 0.4), r=0.6)
    cam = camera(26, dof=4.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    sa, cr, gw = E['satoshi'], E['craft'], E['goldw']

    def update(t):
        for sock, f, ph in leds:
            sock.default_value = 5.0 * (math.sin(t * f + ph) > 0.1)
        sym.rotation_euler = (PI / 2, 0, 0.25 * math.sin(t * 0.8))
        keys = [(t0, (0.4, -3.8, 4.4)), (sa + 0.6, (0.2, -2.2, 2.6)), (cr + 0.5, (-0.9, -1.0, 1.95)),
                (gw, (-0.3, -0.4, 1.85)), (t1, (0.3, -0.1, 1.9))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 2.0, 2.0)), (sa + 0.5, (0, 2.0, 2.0)), (t1, (0, 2.0, 2.0))])
        look(cam, p, tgt, 0.04 * math.sin(t))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update
