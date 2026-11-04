"""Locations S08-S13 (see shots.py for conventions)."""
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

from lib import (glow_mat, box, cyl, sphere, torus, plane, card, text, empty, blob, sun, point, spot, area, camera, look, path,
                 smooth, ease_out, ease_in, spring, lerp, vlerp, shake, mat, emissive, world_gradient, scatter)
from events import E

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parents[1]
A = PROJECT / 'build' / 'assets'
PI = math.pi
UP = (PI / 2, 0, 0)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def _paper_plane(loc, size, m):
    s = size
    verts = [(0, s, 0), (-s * 0.62, -s * 0.55, s * 0.06), (0, -s * 0.42, -s * 0.02), (s * 0.62, -s * 0.55, s * 0.06),
             (0, -s * 0.5, -s * 0.22)]
    me = bpy.data.meshes.new('pp')
    me.from_pydata(verts, [], [(0, 1, 2), (0, 2, 3), (0, 4, 2)])
    ob = bpy.data.objects.new('pp', me)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.data.materials.append(m)
    return ob


def cloud(loc, s, m, seed):
    r = random.Random(seed)
    root = empty('cloud', loc)
    for i in range(9):
        a = i / 9 * 2 * PI
        sphere(s * r.uniform(0.45, 0.75), (math.cos(a) * s * 0.9, math.sin(a) * s * 0.45, r.uniform(-0.1, 0.35) * s),
               m, scale=(1, 1, 0.8), parent=root, seg=20)
    sphere(s * 0.9, (0, 0, s * 0.25), m, scale=(1.2, 0.9, 0.75), parent=root, seg=24)
    return root


# ====================================================================== S08 sky of paper planes
def S08_planes(sh, t0, t1):
    world_gradient((0.1, 0.2, 0.6), (1.0, 0.45, 0.28), 0.55)
    cm = mat((1.0, 0.95, 0.92), rough=0.9, emit=(1.0, 0.75, 0.65), emit_strength=0.05)
    clouds = [((-0.85, 15.5, 0.2), 1.5), ((1.45, 18.5, 1.2), 1.6), ((-6, 32, 3), 3.0), ((7, 36, -2), 3.2),
              ((0, 46, 2), 4.0), ((-9, 20, -4), 2.5), ((8, 12, -3), 2.0), ((-2, 6, -5), 1.6)]
    for i, (p, s) in enumerate(clouds):
        cloud(p, s, cm, i)
    # models stand on two clouds
    sh.anchor('m_proxy', (-0.85, 15.5, 1.1 + 0.62), 0.62)
    sh.anchor('m_anon', (1.45, 18.5, 2.1 + 0.62), 0.62)
    blob((-0.85, 15.5, 1.07), 0.55, 0.35)
    blob((1.45, 18.5, 2.07), 0.55, 0.35)
    # city far below
    tm = mat((0.35, 0.3, 0.45), rough=0.8)
    r = random.Random(3)
    for i in range(80):
        x, y = r.uniform(-40, 40), r.uniform(0, 90)
        h = r.uniform(2, 12)
        box((r.uniform(2, 5), r.uniform(2, 5), h), (x, y, -30 + h / 2), m=tm, bevel=0)
    box((200, 200, 1), (0, 40, -30.5), m=mat((0.3, 0.28, 0.4), rough=0.9), bevel=0)
    pm = mat((0.98, 0.98, 1.0), rough=0.6, emit=(1, 0.95, 0.9), emit_strength=0.1)
    planes = []
    pts = [p for p in scatter(31, 90, (-12, 12), (-2, 50), (-4, 7)) if not (abs(p[0] - 0.8) < 2.6 and abs(p[2] - 2.6) < 2.2)][:46]
    for i, p in enumerate(pts):
        ob = _paper_plane(p, 0.35 + 0.25 * ((i * 13) % 7) / 7, pm)
        planes.append((ob, Vector(p), i))
        sh.track(ob, 'location', 'rotation_euler')
    sun((1.25, 0.0, 2.4), 2.6, (1.0, 0.75, 0.55))
    cam = camera(24, dof=9.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    pl, pr, an = E['planes'], E['proxyserver'], E['anon']

    def update(t):
        for ob, p0, i in planes:
            sp = 2.2 + (i % 5) * 0.35
            y = p0.y + (t - t0) * sp
            ob.location = (p0.x + 0.8 * math.sin(t * 0.8 + i), y, p0.z + 0.5 * math.sin(t * 1.1 + i * 0.7))
            ob.rotation_euler = (0.15 * math.sin(t * 1.3 + i), 0.4 * math.sin(t * 0.9 + i), 0.12 * math.cos(t * 0.8 + i))
        keys = [(t0, (0.6, -7.0, 1.4)), (pl + 0.6, (0.3, 1.5, 2.2)), (pr - 0.3, (0.0, 8.5, 2.6)),
                (an + 0.2, (0.1, 10.4, 2.75)), (t1, (0.15, 11.9, 2.85))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 10, 1.6)), (pl + 0.6, (0, 16, 2.0)), (pr + 0.1, (-1.2, 16, 1.9)),
                       (an + 0.3, (0.2, 17.5, 2.2)), (t1, (0.1, 17.5, 2.1))])
        look(cam, p, tgt, 0.1 * math.sin(t * 0.9))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S09 the legend: barrier lifts, golden statue
def S09_legend(sh, t0, t1):
    world_gradient((0.18, 0.2, 0.5), (1.0, 0.5, 0.25), 0.75)
    box((60, 60, 0.2), (0, 10, -0.1), m=mat((0.75, 0.6, 0.5), rough=0.6), bevel=0)
    tile = mat((0.68, 0.52, 0.42), rough=0.7)
    for i in range(-12, 13):
        box((0.04, 60, 0.005), (i * 1.2, 10, 0.003), m=tile, bevel=0)
        box((60, 0.04, 0.005), (0, i * 1.2 + 10, 0.003), m=tile, bevel=0)
    stone = mat((0.82, 0.76, 0.68), rough=0.5)
    for k, (s, h) in enumerate(((5.0, 0.35), (4.0, 0.35), (3.0, 1.6))):
        box((s, s, h), (0, 8, sum(x[1] for x in ((5.0, 0.35), (4.0, 0.35), (3.0, 1.6))[:k]) + h / 2), m=stone, bevel=0.05)
    gold = mat((1.0, 0.72, 0.3), metal=1.0, rough=0.22)
    blob((0, 8, 2.3), 1.3, 0.5)
    sh.anchor('statue', (0, 8.0, 2.3 + 1.75), 1.75)
    plq = text('RESISTANCE', 0.32, (0, 6.48, 1.3), UP, m=mat((0.95, 0.85, 0.5), metal=1, rough=0.2), extrude=0.02)
    # barrier
    post = mat((0.85, 0.85, 0.88), rough=0.4)
    box((0.4, 0.4, 1.2), (-2.4, 1.5, 0.6), m=post, bevel=0.04)
    piv = empty('bar', (-2.4, 1.5, 1.05))
    redm, whm = mat((0.9, 0.12, 0.1), rough=0.4), mat((0.98, 0.98, 0.98), rough=0.4)
    for k in range(6):
        box((0.8, 0.12, 0.12), (0.4 + k * 0.8, 0, 0), m=redm if k % 2 == 0 else whm, parent=piv, bevel=0.02)
    sh.track(piv, 'rotation_euler')
    cyl(0.06, 2.6, (2.6, 1.5, 1.3), m=mat((0.2, 0.2, 0.22)))
    box((0.35, 0.3, 0.8), (2.6, 1.5, 2.8), m=mat((0.12, 0.12, 0.14)), bevel=0.04)
    lr, lg = emissive((1.0, 0.1, 0.1), 6.0), emissive((0.2, 1.0, 0.4), 0.0)
    sh.track(lr.node_tree.nodes['Emission'].inputs[1], 'default_value')
    sh.track(lg.node_tree.nodes['Emission'].inputs[1], 'default_value')
    sphere(0.11, (2.6, 1.34, 3.0), lr)
    sphere(0.11, (2.6, 1.34, 2.6), lg)
    # trees, lamps
    for x, y in ((-6, 6), (6, 6), (-7, 12), (7, 12), (-5, 16), (5, 16)):
        cyl(0.14, 2.0, (x, y, 1.0), m=mat((0.35, 0.22, 0.14)))
        for i in range(3):
            sphere(0.9 - i * 0.2, (x, y, 2.2 + i * 0.55), mat((0.35, 0.55, 0.25), rough=0.7))
    for x in (-3.5, 3.5):
        for y in (3, 13):
            cyl(0.06, 3.2, (x, y, 1.6), m=mat((0.15, 0.15, 0.18), metal=0.5))
            sphere(0.2, (x, y, 3.3), emissive((1.0, 0.85, 0.6), 4.0))
    for i in range(12):
        box((3.5, 3.5, 6 + (i * 37) % 9), (-22 + i * 4, 30, 3), m=mat((0.6, 0.5, 0.55), rough=0.8), bevel=0.05)
    sun((1.35, 0.0, 2.6), 3.0, (1.0, 0.65, 0.4))
    rim = area((0, 14, 6), (0, 8, 3), 2500, 4, (1.0, 0.75, 0.45))
    sh.track(rim.data, 'energy')
    cam = camera(26, dof=8.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    lift, leg = E['lift'], E['legend']

    def update(t):
        u = smooth(seg(t, lift - 0.1, lift + 0.8))
        piv.rotation_euler = (0, -1.35 * u, 0)
        lr.node_tree.nodes['Emission'].inputs[1].default_value = 6.0 * (1 - u)
        lg.node_tree.nodes['Emission'].inputs[1].default_value = 7.0 * u
        rim.data.energy = 2500 + 2500 * smooth(seg(t, leg - 0.3, leg + 0.4))
        keys = [(t0, (0.2, -4.5, 1.2)), (lift + 0.6, (0.1, -1.0, 1.4)), (leg - 0.6, (1.6, 2.4, 1.3)),
                (t1, (1.1, 3.4, 1.1))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 2, 1.3)), (lift + 0.4, (0, 8, 3.0)), (leg, (0, 8, 4.3)), (t1, (0, 8, 4.5))])
        look(cam, p, tgt, -0.06 * smooth(seg(t, leg - 1, t1)))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


def dog_statue(loc, s, m, nose=None):
    """Hooded dog: pointed hood flowing over the shoulders, dark face opening, light muzzle, nose."""
    root = empty('statue', loc)
    dark = mat((0.12, 0.08, 0.05), metal=0.6, rough=0.35)
    sphere(0.58 * s, (0, 0.05 * s, 0.55 * s), m, scale=(1, 0.85, 1.0), parent=root)          # body
    for x in (-0.27, 0.27):
        sphere(0.2 * s, (x * s, -0.42 * s, 0.13 * s), nose[0], scale=(1, 1.3, 0.65), parent=root)
    sphere(0.78 * s, (0, 0.02 * s, 1.3 * s), m, scale=(1, 0.9, 1.0), parent=root)            # hood dome
    cyl(0.62 * s, 1.2 * s, (0, 0.1 * s, 2.0 * s), (0.18, 0, 0), m=m, r2=0.02 * s, parent=root, bevel=0)  # hood tip
    sphere(0.5 * s, (0, -0.42 * s, 1.22 * s), dark, scale=(1, 0.5, 0.95), parent=root)       # face opening
    sphere(0.34 * s, (0, -0.62 * s, 1.12 * s), nose[0], scale=(1, 0.6, 0.78), parent=root)   # muzzle
    sphere(0.1 * s, (0, -0.83 * s, 1.18 * s), nose[1], scale=(1.3, 0.8, 0.8), parent=root)   # nose
    return root


# ====================================================================== S10 TON coin, newspaper, avatars wall
def _newspaper():
    p = A / 'newspaper.png'
    if p.exists():
        return p
    from PIL import Image, ImageDraw, ImageFont
    F = ROOT / 'input/fonts/SF-Pro-Text'
    im = Image.new('RGB', (900, 1200), (236, 230, 216))
    d = ImageDraw.Draw(im)
    fb = ImageFont.truetype(str(F / 'SF-Pro-Text-Heavy.otf'), 92)
    fm = ImageFont.truetype(str(F / 'SF-Pro-Text-Bold.otf'), 40)
    fs = ImageFont.truetype(str(F / 'SF-Pro-Text-Regular.otf'), 26)
    d.text((450, 80), 'ЦИФРОВОЙ ВЕСТНИК', font=fm, fill=(30, 30, 30), anchor='mm')
    d.line((40, 120, 860, 120), fill=(30, 30, 30), width=4)
    d.text((450, 160), 'АВГУСТ 2024 · ФРАНЦИЯ', font=fs, fill=(60, 60, 60), anchor='mm')
    d.text((450, 290), 'ДУРОВ', font=fb, fill=(20, 20, 20), anchor='mm')
    d.text((450, 400), 'ЗАДЕРЖАН', font=fb, fill=(20, 20, 20), anchor='mm')
    d.rectangle((60, 480, 840, 860), fill=(205, 198, 182))
    dog = Image.open(A / 'hooded_plain.png').convert('RGBA').resize((360, 360))
    gray = Image.merge('RGBA', (*[dog.convert('L')] * 3, dog.split()[3]))
    im.paste(gray, (270, 490), gray)
    r = random.Random(2)
    for row in range(8):
        y = 900 + row * 34
        for col in range(2):
            x0 = 60 + col * 400
            d.rectangle((x0, y, x0 + r.randint(250, 370), y + 12), fill=(150, 145, 135))
    p.parent.mkdir(parents=True, exist_ok=True)
    im.save(p)
    return p


def S10_ton(sh, t0, t1):
    world_gradient((0.02, 0.05, 0.14), (0.05, 0.14, 0.3), 1.0)
    box((80, 80, 0.2), (0, 0, -0.1), m=mat((0.03, 0.06, 0.12), rough=0.15, coat=0.6), bevel=0)
    gl = emissive((0.15, 0.45, 1.0), 1.5)
    for i in range(-20, 21):
        box((0.03, 80, 0.01), (i * 2, 0, 0.005), m=gl, bevel=0)
        box((80, 0.03, 0.01), (0, i * 2, 0.005), m=gl, bevel=0)
    coin = empty('coin', (0, 0, 2.2))
    crys = mat((0.25, 0.6, 1.0), metal=0.6, rough=0.12, emit=(0.2, 0.55, 1.0), emit_strength=0.6, coat=1.0)
    cyl(1.4, 0.28, (0, 0, 0), (PI / 2, 0, 0), m=crys, parent=coin, verts=64, bevel=0.08)
    torus(1.4, 0.07, (0, 0, 0), (PI / 2, 0, 0), m=emissive((0.6, 0.85, 1.0), 5.0), parent=coin)
    for side in (-1, 1):
        c = card(A / 'hooded_plain.png', 1.7, (0, side * 0.15, -0.85), (PI / 2, 0, 0 if side < 0 else PI), emit=0.4, parent=coin)
    sh.track(coin, 'rotation_euler', 'location', 'scale')
    news = card(_newspaper(), 2.4, (0, 0, 0), UP)
    news.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.9
    sh.track(news, 'location', 'rotation_euler')
    # avatars wall: arc of round avatars behind
    av_mats = []
    avs = []
    r = random.Random(8)
    for row in range(9):
        for col in range(-9, 10):
            ang = col * 0.11
            R = 14
            x, y = math.sin(ang) * R, math.cos(ang) * R - 4
            z = 0.6 + row * 1.25 + (0.6 if col % 2 else 0)
            c = card(A / f'avatar_{r.randint(0, 3)}.png', 1.05, (x, y, z), (PI / 2, 0, -ang), emit=0.0)
            m = c.data.materials[0]
            sock = m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
            avs.append((sock, math.hypot(col, row - 4) + r.random() * 0.6))
            sh.track(sock, 'default_value')
    key = area((0, -5, 6), (0, 0, 2), 900, 6, (0.6, 0.8, 1.0))
    point((3, -2, 4), 300, (0.6, 0.8, 1.0))
    cam = camera(28, dof=5.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    tok, arr, fr, ava = E['token'], E['arrest'], E['france'], E['avatars']

    def update(t):
        coin.rotation_euler = (0.15 * math.sin(t), 0, (t - t0) * 2.4 + 6 * ease_out(seg(t, tok - 0.3, tok + 0.6)))
        k = 0.2 + 0.8 * spring(seg(t, t0, t0 + 1.0), 1.5, 0.5)
        coin.scale = (k, k, k)
        coin.location = (0, 0, 2.2 + 0.12 * math.sin(t * 1.6))
        u_in = ease_out(seg(t, arr - 0.7, arr + 0.1))
        u_out = ease_in(seg(t, fr + 0.7, fr + 1.3))
        news.location = (lerp(3.2, 0.25, u_in) - 4.5 * u_out, -2.5, 0.75 + 0.05 * math.sin(t * 2))
        news.rotation_euler = (PI / 2 + 0.06 * math.sin(t * 1.7), 0.08 * (1 - u_in) - 0.3 * u_out, -0.25 * (1 - u_in) + 0.05 * math.sin(t * 1.3))
        wave = (t - ava + 0.6) * 9
        for sock, dist in avs:
            sock.default_value = 1.6 * smooth(clamp(wave - dist))
        keys = [(t0, (0.8, -4.2, 2.6)), (tok + 0.5, (-0.6, -3.3, 2.3)), (arr - 0.3, (0.2, -5.0, 2.0)),
                (fr + 0.6, (0.1, -5.3, 2.1)), (t1, (0.0, -12.5, 4.2))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 0, 2.2)), (tok + 0.5, (0, 0, 2.1)), (arr, (0.2, -2.5, 1.95)), (fr + 0.6, (0.2, -2.5, 2.0)),
                       (ava - 0.2, (0, 2, 3.5)), (t1, (0, 6, 5.0))])
        look(cam, p, tgt, 0.05 * math.sin(t * 0.6))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S11 gift rain, the dog arrives
def S11_giftrain(sh, t0, t1):
    from shots import gift_box
    world_gradient((0.12, 0.35, 0.85), (0.45, 0.72, 1.0), 1.0)
    W = bpy.context.scene.world.node_tree.nodes['Background'].inputs[1]
    sh.track(W, 'default_value')
    box((60, 60, 0.2), (0, 0, -0.1), m=mat((0.32, 0.58, 0.95), rough=0.2, coat=0.5), bevel=0)
    r = random.Random(17)
    cols = [(0.95, 0.35, 0.45), (0.98, 0.75, 0.25), (0.45, 0.8, 0.5), (0.7, 0.45, 0.95), (0.98, 0.98, 1.0),
            (0.35, 0.6, 1.0)]
    boxes = []
    for i in range(34):
        ang, rad = r.uniform(0, 2 * PI), r.uniform(1.8, 8)
        x, y = math.cos(ang) * rad, math.sin(ang) * rad + 2
        s = r.uniform(0.45, 0.95)
        root, lid = gift_box((x, y, 0), s, cols[i % 6], rot=r.uniform(0, 3))
        boxes.append((root, x, y, r.uniform(0, 2.2), r.uniform(-1, 1)))
        sh.track(root, 'location', 'rotation_euler')
    hero, hlid = gift_box((0, 0, 0), 1.3, (0.12, 0.12, 0.16), ribbon=(1.0, 0.78, 0.3))
    sh.track(hero, 'location', 'scale')
    sh.track(hlid, 'location', 'rotation_euler')
    sh.anchor('gift_drop', (0, 0, 1.35 + 0.65), 0.62)
    beam = cyl(0.45, 6, (0, 0, 3.0), m=glow_mat((1.0, 0.9, 0.65), 0.0), r2=0.85, bevel=0, open_ends=True)
    bs = beam.data.materials[0].node_tree.nodes['Emission'].inputs[1]
    sh.track(bs, 'default_value')
    sh.track(beam, 'scale')
    key = area((-3, -5, 7), (0, 0, 0), 1200, 7, (0.95, 0.97, 1.0))
    sh.track(key.data, 'energy')
    sp = spot((0, -1, 6), (0, 0, 1), 0.0, (1.0, 0.95, 0.85), 30, 0.5)
    sh.track(sp.data, 'energy')
    cam = camera(28, dof=5.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    g24, yr, him, nxt = E['gifts24'], E['year'], E['him'], E['next']

    def drop(t, start, h0=9.0):
        """Fall with gravity, then two damped bounces. Returns height above floor."""
        u = t - start
        if u <= 0:
            return h0 + 20
        T = math.sqrt(2 * h0 / 9.81)
        if u < T:
            return h0 - 0.5 * 9.81 * u * u
        u -= T
        v = 9.81 * T * 0.35
        for _ in range(2):
            tb = 2 * v / 9.81
            if u < tb:
                return v * u - 0.5 * 9.81 * u * u
            u -= tb
            v *= 0.35
        return 0.0

    def update(t):
        for root, x, y, d, sp_ in boxes:
            z = drop(t, g24 - 1.6 + d * 0.8)
            root.location = (x, y, z)
            root.rotation_euler = (0, 0, sp_ * max(0, z) * 0.15)
        hz = drop(t, yr - 1.2, 10)
        k = 1.0
        hero.location = (0, 0, hz)
        opn = ease_out(seg(t, him - 0.15, him + 0.5))
        hlid.location = (0.0, 0.0, 1.3 * 0.82 + 2.2 * opn)
        hlid.rotation_euler = (0.9 * opn, 0.4 * opn, 0)
        bs.default_value = 1.6 * opn * (1 - 0.5 * smooth(seg(t, nxt, nxt + 0.6)))
        beam.scale = (1, 1, max(opn, 1e-3))
        dim = 1 - 0.65 * smooth(seg(t, nxt - 0.2, nxt + 0.6))
        W.default_value = dim
        key.data.energy = 1200 * dim
        sp.data.energy = 2500 * opn
        keys = [(t0, (0, -12, 6.5)), (g24, (2.2, -8.5, 3.6)), (yr, (0.8, -5.5, 2.5)), (him + 0.3, (0.2, -4.0, 2.1)),
                (t1, (0.0, -2.9, 2.0))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 2, 1.0)), (yr, (0, 0, 1.2)), (t1, (0, 0, 1.9))])
        look(cam, p, tgt, 0.04 * math.sin(t))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S12 gallery of models
def _backdrops():
    g = json.loads((ROOT / '.cache/gifts/resistance-dog/gift.json').read_text(encoding='utf-8'))
    out = {}
    for b in g['backdrops']:
        out[b['name']] = tuple(int(b['hex']['centerColor'][i:i + 2], 16) / 255 for i in (1, 3, 5)), \
            tuple(int(b['hex']['edgeColor'][i:i + 2], 16) / 255 for i in (1, 3, 5))
    return out


def S12_gallery(sh, t0, t1):
    world_gradient((0.04, 0.035, 0.05), (0.1, 0.08, 0.1), 0.4)
    box((80, 14, 0.2), (20, 0, -0.1), m=mat((0.06, 0.05, 0.05), rough=0.1, coat=0.9), bevel=0)
    wall = mat((0.28, 0.22, 0.24), rough=0.8)
    box((80, 0.3, 7), (20, 3.4, 3.5), m=wall, bevel=0)
    box((80, 14, 0.3), (20, 0, 6.5), m=mat((0.95, 0.93, 0.9)), bevel=0)
    for x in range(-6, 46, 4):
        box((0.5, 0.5, 6.5), (x + 2, 3.0, 3.25), m=mat((0.85, 0.8, 0.72), rough=0.5), bevel=0.05)
    bd = _backdrops()
    names = list(bd.keys())
    picks = {'m_che': names[0], 'm_sparta': names[3], 'm_rambo': names[min(10, len(names) - 1)],
             'm_satoshi': names[min(20, len(names) - 1)]}
    xs = {'m_che': 4.0, 'm_sparta': 8.0, 'm_rambo': 12.0, 'm_satoshi': 16.0}
    ped = mat((0.96, 0.95, 0.93), rough=0.3, coat=0.4)
    goldm = mat((1.0, 0.75, 0.3), metal=1.0, rough=0.25)
    for name, x in xs.items():
        c, e = bd[picks[name]]
        panel = box((2.8, 0.1, 3.4), (x, 3.18, 2.6), m=mat(c, rough=0.6, emit=c, emit_strength=1.2), bevel=0.05)
        box((3.0, 0.08, 3.6), (x, 3.22, 2.6), m=goldm if name == 'm_satoshi' else mat((0.15, 0.12, 0.1)), bevel=0.03)
        cyl(0.7, 1.0, (x, 1.6, 0.5), m=goldm if name == 'm_satoshi' else ped, bevel=0.05)
        blob((x, 1.6, 1.0), 0.55, 0.5)
        sh.anchor(name, (x, 1.6, 1.0 + 0.62), 0.62)
        spot((x, 0.2, 5.8), (x, 1.6, 1.4), 1400 if name != 'm_satoshi' else 2600,
             (1.0, 0.95, 0.85) if name != 'm_satoshi' else (1.0, 0.8, 0.45), 35, 0.4)
        box((0.9, 0.04, 0.3), (x + 0.9, 1.0, 0.25), m=mat((0.2, 0.18, 0.16)), bevel=0.01)
    for x in range(-4, 44, 6):
        sphere(0.35, (x, 0, 6.2), emissive((1.0, 0.9, 0.75), 3.0), scale=(1, 1, 0.3))
    area((8, -3, 5), (8, 2, 1), 250, 10, (1.0, 0.92, 0.82))
    cam = camera(26, dof=4.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    up, dz, che, sp_, ra, sa = E['upgrade'], E['dozens'], E['che'], E['sparta'], E['rambo'], E['satoshi']

    def update(t):
        keys = [(t0, (-3.5, -5.5, 2.6)), (dz, (0.2, -3.6, 1.9)), (che, (3.0, -2.6, 1.55)), (sp_, (7.0, -2.5, 1.5)),
                (ra, (11.0, -2.5, 1.5)), (sa, (15.2, -2.7, 1.6)), (t1, (16.2, -2.0, 1.7))]
        p = path(t, keys)
        tgt = path(t, [(t0, (4, 2, 1.8)), (dz, (3.5, 1.6, 1.6)), (che, (4.0, 1.6, 1.6)), (sp_, (8.0, 1.6, 1.6)),
                       (ra, (12.0, 1.6, 1.6)), (sa, (16.0, 1.6, 1.6)), (t1, (16.0, 1.6, 1.65))])
        look(cam, p, tgt, -0.05 * math.sin((t - t0) * 1.5))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S13 laser vault, Imposter
def S13_laser(sh, t0, t1):
    world_gradient((0.02, 0.02, 0.03), (0.05, 0.04, 0.05), 1.0)
    metal = mat((0.18, 0.19, 0.22), metal=0.8, rough=0.35)
    box((30, 30, 0.2), (0, 4, -0.1), m=mat((0.08, 0.08, 0.1), metal=0.6, rough=0.25), bevel=0)
    for i in range(-3, 4):
        box((2.6, 0.2, 6), (i * 2.7, 8, 3), m=metal, bevel=0.06)
        for z in (1, 3, 5):
            for dx in (-1.0, 1.0):
                sphere(0.06, (i * 2.7 + dx, 7.88, z), mat((0.5, 0.5, 0.55), metal=1, rough=0.2), seg=12)
    for x in (-6, 6):
        box((0.2, 16, 6), (x, 2, 3), m=metal, bevel=0)
    torus(2.4, 0.25, (0, 7.85, 3.0), (PI / 2, 0, 0), m=mat((0.3, 0.3, 0.33), metal=1, rough=0.25))
    for a in range(8):
        box((0.2, 0.1, 1.8), (math.cos(a * PI / 4) * 1.2, 7.8, 3 + math.sin(a * PI / 4) * 1.2), (0, a * PI / 4, 0),
            m=mat((0.35, 0.35, 0.38), metal=1, rough=0.3), bevel=0.02)
    lz = emissive((1.0, 0.05, 0.05), 8.0)
    lasers = []
    r = random.Random(4)
    for i in range(14):
        y = 0.5 + i * 0.5
        z = r.uniform(0.4, 2.6)
        ob = cyl(0.012, 14, (0, y, z), (0, PI / 2, r.uniform(-0.25, 0.25)), m=lz, verts=8, bevel=0)
        lasers.append((ob, z, i))
        sh.track(ob, 'location')
    cyl(0.75, 1.2, (0, 4.5, 0.6), m=mat((0.12, 0.12, 0.14), metal=0.8, rough=0.3), bevel=0.05)
    torus(0.75, 0.04, (0, 4.5, 1.2), m=emissive((1.0, 0.15, 0.1), 5.0))
    dome = sphere(0.85, (0, 4.5, 1.2), glow_mat((0.7, 0.85, 1.0), 0.25), seg=32)
    sh.track(dome, 'location')
    blob((0, 4.5, 1.2), 0.55, 0.6)
    sh.anchor('m_imposter', (0, 4.5, 1.2 + 0.62), 0.62)
    num = text('1 / 1000', 0.9, (0, 7.6, 4.6), UP, m=emissive((1.0, 0.2, 0.15), 0.0), extrude=0.03)
    ns = num.data.materials[0].node_tree.nodes['Emission'].inputs[1]
    sh.track(ns, 'default_value')
    sh.track(num, 'scale')
    red = area((0, 1, 5.5), (0, 4.5, 1), 1500, 5, (1.0, 0.2, 0.15))
    sp = spot((0, 3.0, 5.5), (0, 4.5, 1.4), 0.0, (1.0, 0.95, 0.9), 28, 0.4)
    sh.track(sp.data, 'energy')
    cam = camera(26, dof=3.5)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    im, th = E['imposter'], E['thousand']

    def update(t):
        for ob, z, i in lasers:
            ob.location = (0, 0.5 + i * 0.5, z + 0.25 * math.sin(t * 1.3 + i))
        up_ = ease_out(seg(t, im - 0.5, im + 0.3))
        dome.location = (0, 4.5, 1.2 + 9.0 * up_)
        sp.data.energy = 2600 * smooth(seg(t, im - 0.3, im + 0.2))
        ns.default_value = 7.0 * smooth(seg(t, th - 0.9, th - 0.4))
        k = spring(seg(t, th - 0.9, th + 0.1), 1.6, 0.5)
        num.scale = (max(k, 1e-3),) * 3
        keys = [(t0, (0.4, -4.0, 1.4)), (im - 0.2, (0.15, -0.8, 1.7)), (th - 0.8, (-0.4, 0.6, 2.2)),
                (t1, (-0.2, 1.4, 2.0))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 4.5, 1.6)), (im, (0, 4.5, 1.7)), (th - 0.6, (0, 5.5, 3.0)), (t1, (0, 4.5, 2.2))])
        look(cam, p, tgt, 0.0)
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update
