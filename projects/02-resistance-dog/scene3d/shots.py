"""The 14 locations. Each function builds one Blender scene and sets sh.update(t) (content seconds).
Animated properties are registered with sh.track so they are keyframed (motion blur, determinism).
2D layers (gifts, drawing, hand, captions) are composited later at the registered anchors."""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

from lib import (box, cyl, sphere, torus, plane, card, text, empty, blob, sun, point, spot, area, aim, camera,
                 look, path, smooth, ease_out, ease_in, spring, lerp, vlerp, shake, mat, emissive, world_gradient,
                 scatter)

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT))
from events import E  # noqa: E402

A = PROJECT / 'build' / 'assets'
PI = math.pi
UP = (PI / 2, 0, 0)          # upright card facing -Y


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def window_texture(name='windows', seed=3, w=128, h=256, cols=6, rows=14, lit=0.55, warm=False):
    """Emission texture of building windows (generated once into build/assets)."""
    p = A / f'{name}.png'
    if not p.exists():
        from PIL import Image, ImageDraw
        r = random.Random(seed)
        im = Image.new('RGB', (w, h), (6, 8, 14))
        d = ImageDraw.Draw(im)
        cw, ch = w / cols, h / rows
        for i in range(cols):
            for j in range(rows):
                if r.random() < lit:
                    c = (255, 214, 150) if (warm and r.random() < 0.7) else (170, 210, 255)
                    k = 0.55 + 0.45 * r.random()
                    c = tuple(int(v * k) for v in c)
                    d.rectangle((i * cw + cw * 0.22, j * ch + ch * 0.25, i * cw + cw * 0.78, j * ch + ch * 0.8), fill=c)
        im.save(p)
    return p


def tower_mat(name, tex, base=(0.05, 0.06, 0.1), strength=2.5, objcolor=False, density=1.0):
    """Building material: dark body + emissive windows. objcolor=True: Object Color drives
    tint (rgb) and strength (alpha) so many towers share one material but animate separately."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*base, 1)
    p.inputs['Roughness'].default_value = 0.5
    tx = nt.nodes.new('ShaderNodeTexImage')
    tx.image = bpy.data.images.load(str(tex), check_existing=True)
    tx.interpolation = 'Closest'
    tx.projection = 'BOX'
    tx.projection_blend = 0.0
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (0.32 * density, 0.32 * density, 0.14 * density)
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    nt.links.new(mp.outputs[0], tx.inputs['Vector'])
    if objcolor:
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        mul = nt.nodes.new('ShaderNodeMix')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        nt.links.new(tx.outputs['Color'], mul.inputs['A'])
        nt.links.new(oi.outputs['Color'], mul.inputs['B'])
        nt.links.new(mul.outputs['Result'], p.inputs['Emission Color'])
        mt = nt.nodes.new('ShaderNodeMath')
        mt.operation = 'MULTIPLY'
        mt.inputs[1].default_value = strength
        nt.links.new(oi.outputs['Alpha'], mt.inputs[0])
        nt.links.new(mt.outputs[0], p.inputs['Emission Strength'])
    else:
        nt.links.new(tx.outputs['Color'], p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = strength
    return m


def emit_socket(m):
    return m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']


def paper_plane(loc=(0, 0, 0), size=0.5, m=None, name='plane'):
    """Folded paper plane mesh, nose along +Y."""
    s = size
    verts = [(0, s * 1.0, 0), (-s * 0.62, -s * 0.55, s * 0.06), (0, -s * 0.42, -s * 0.02), (s * 0.62, -s * 0.55, s * 0.06),
             (0, -s * 0.5, -s * 0.22)]
    faces = [(0, 1, 2), (0, 2, 3), (0, 4, 2)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.data.materials.append(m or mat((0.96, 0.97, 1.0), rough=0.6))
    return ob


def gift_box(loc, s, color, ribbon=(1.0, 0.85, 0.3), rot=0.0, parent=None):
    root = empty('gift', loc, parent)
    root.rotation_euler = (0, 0, rot)
    mb, mr = mat(color, rough=0.35, coat=0.3), mat(ribbon, rough=0.3, metal=0.3)
    box((s, s, s * 0.82), (0, 0, s * 0.41), m=mb, bevel=s * 0.06, parent=root)
    box((s * 1.02, s * 0.16, s * 0.84), (0, 0, s * 0.41), m=mr, bevel=0.01, parent=root)
    box((s * 0.16, s * 1.02, s * 0.84), (0, 0, s * 0.41), m=mr, bevel=0.01, parent=root)
    lid = empty('lid', (0, 0, s * 0.82), root)
    box((s * 1.08, s * 1.08, s * 0.2), (0, 0, s * 0.1), m=mb, bevel=s * 0.05, parent=lid)
    box((s * 1.1, s * 0.16, s * 0.22), (0, 0, s * 0.1), m=mr, bevel=0.01, parent=lid)
    box((s * 0.16, s * 1.1, s * 0.22), (0, 0, s * 0.1), m=mr, bevel=0.01, parent=lid)
    for a in (0.6, -0.6):
        t = torus(s * 0.16, s * 0.05, (math.sin(a) * s * 0.14, 0, s * 0.3), (PI / 2, a, 0), m=mr)
        t.parent = lid
    return root, lid


def dog_statue(loc, s, m, nose=None, parent=None):
    """Hooded dog made of primitives (for the monument)."""
    root = empty('statue', loc, parent)
    sphere(0.55 * s, (0, 0, 0.62 * s), m, scale=(1, 0.85, 1.05), parent=root)            # body
    for x in (-0.28, 0.28):
        sphere(0.2 * s, (x * s, -0.32 * s, 0.16 * s), m, scale=(1, 1.3, 0.7), parent=root)  # paws
    cyl(0.6 * s, 1.15 * s, (0, 0, 1.55 * s), m=m, r2=0.02 * s, parent=root, bevel=0)       # hood cone
    sphere(0.58 * s, (0, 0, 1.32 * s), m, scale=(1, 0.95, 0.9), parent=root)              # hood dome
    face = mat((0.98, 0.95, 0.85), rough=0.4, metal=0.0) if nose is None else nose[0]
    sphere(0.36 * s, (0, -0.36 * s, 1.24 * s), face, scale=(1, 0.6, 0.85), parent=root)  # face
    sphere(0.11 * s, (0, -0.58 * s, 1.27 * s), nose[1] if nose else mat((0.05, 0.05, 0.06)),
           scale=(1.2, 0.8, 0.8), parent=root)
    return root


# ====================================================================== S01 / S14 desk at night
def _desk(sh, final=False):
    wood, wood_d = mat((0.42, 0.24, 0.13), rough=0.45, coat=0.2), mat((0.3, 0.16, 0.08), rough=0.5)
    box((9, 6, 0.25), (0, 0.6, -0.125), m=wood, bevel=0.04)
    for i in range(9):
        box((9, 0.012, 0.01), (0, -2.3 + i * 0.66, 0.0), m=wood_d, bevel=0)
    paper = empty('paper', (0, 0.05, 0.004))
    paper.rotation_euler = (0, 0, 0.06)
    plane((1.75, 2.0), (0, 0.02, 0.002), m=mat((0.97, 0.95, 0.9), rough=0.8), parent=paper)
    plane((1.75, 2.0), (0.035, -0.03, 0.0005), m=mat((0.86, 0.82, 0.76), rough=0.9), parent=paper)
    for i, (sx, sy) in enumerate(((-1, 1), (1, 1), (1, -1), (-1, -1))):
        e = empty(f'c{i}', (sx * 0.7, sy * 0.7 + 0.07, 0.003), paper)
        sh.anchor(f'paper{i}', e, 0.0)
    # lamp
    lm, lm2 = mat((0.12, 0.35, 0.5), rough=0.3, metal=0.4), mat((0.85, 0.82, 0.75), rough=0.3, metal=0.6)
    cyl(0.32, 0.08, (1.45, 1.05, 0.04), m=lm, bevel=0.03)
    arm1 = cyl(0.04, 1.3, (1.35, 0.95, 0.65), (0.0, -0.32, 0.4), m=lm2)
    cyl(0.05, 0.12, (1.25, 0.85, 1.25), (PI / 2, 0, 0.6), m=lm2)
    head = cyl(0.3, 0.45, (0.9, 0.6, 1.22), (0.0, 0.95, 0.75), m=lm, r2=0.12)
    bulb_m = emissive((1.0, 0.85, 0.6), 6.0)
    sphere(0.12, (0.79, 0.52, 1.07), bulb_m)
    lamp = point((0.72, 0.45, 1.0), 260, (1.0, 0.78, 0.5), r=0.15)
    sh.track(lamp.data, 'energy')
    sh.track(bulb_m.node_tree.nodes['Emission'].inputs[1], 'default_value')
    sh.anchor('lamp', (0.79, 0.52, 1.07), 0.12)
    # props
    mug = mat((0.85, 0.28, 0.22), rough=0.25, coat=0.5)
    cyl(0.2, 0.42, (-1.35, 0.9, 0.21), m=mug, bevel=0.03)
    cyl(0.17, 0.02, (-1.35, 0.9, 0.42), m=mat((0.2, 0.1, 0.05), rough=0.1))
    torus(0.11, 0.035, (-1.13, 0.9, 0.22), (PI / 2, 0, 0), m=mug)
    for i, c in enumerate(((0.2, 0.45, 0.7), (0.9, 0.7, 0.2), (0.3, 0.6, 0.35))):
        box((0.95, 0.65, 0.12), (-1.55, -0.75, 0.06 + i * 0.125), (0, 0, 0.2 * (i - 1)), m=mat(c, rough=0.5), bevel=0.02)
    for i, c in enumerate(((0.95, 0.75, 0.2), (0.2, 0.5, 0.9), (0.9, 0.3, 0.3))):
        cyl(0.03, 0.85, (1.15 + i * 0.09, -0.65 - i * 0.05, 0.03), (0, PI / 2, 0.5 + i * 0.1), m=mat(c), verts=6, bevel=0.005)
    for i in range(3):
        box((0.32, 0.32, 0.006), (-1.0 - i * 0.05, 0.05 + i * 0.03, 0.003 + i * 0.002), (0, 0, 0.3 * i - 0.2),
            m=mat((1.0, 0.9, 0.35) if i != 1 else (0.5, 0.85, 1.0), rough=0.8), bevel=0)
    cyl(0.25, 0.4, (1.7, 1.75, 0.2), m=mat((0.75, 0.4, 0.25), rough=0.6), r2=0.2)
    for i, (x, y, z) in enumerate(((1.7, 1.75, 0.6), (1.55, 1.7, 0.75), (1.85, 1.8, 0.78), (1.7, 1.85, 0.95))):
        sphere(0.2, (x, y, z), mat((0.2, 0.55, 0.3), rough=0.6), scale=(1, 1, 1.2))
    # room + night window
    box((14, 0.3, 8), (0, 4.6, 3), m=mat((0.1, 0.11, 0.16), rough=0.9), bevel=0)
    win = plane((4.2, 2.6), (0.4, 4.43, 2.6), (PI / 2, 0, 0), m=emissive((0.04, 0.07, 0.18), 1.0))
    r = random.Random(7)
    city = emissive((1.0, 0.8, 0.45), 2.2)
    for i in range(70):
        x, z = r.uniform(-1.6, 2.4), r.uniform(1.4, 2.6)
        plane((0.05, 0.07), (x, 4.42, z), (PI / 2, 0, 0), m=city)
    mull = mat((0.06, 0.06, 0.08), rough=0.8)
    for x in (-1.7, 0.4, 2.5):
        box((0.08, 0.1, 2.7), (x, 4.4, 2.6), m=mull, bevel=0)
    box((4.3, 0.1, 0.08), (0.4, 4.4, 2.6), m=mull, bevel=0)
    alarm = area((-3.5, -1.5, 2.2), (0, 0.3, 0), 0.0, 3.0, (1.0, 0.12, 0.1))
    sh.track(alarm.data, 'energy')
    fill = area((2.5, -3.5, 3.0), (0, 0, 0), 60, 4.0, (0.45, 0.55, 1.0))
    sh.track(fill.data, 'energy')
    return dict(lamp=lamp, bulb=bulb_m, alarm=alarm, fill=fill, paper=paper)


def S01_desk(sh, t0, t1):
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.01, 0.012, 0.03, 1)
    d = _desk(sh)
    cam = camera(30)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data, 'lens')
    war = E['war']

    def update(t):
        flick = 1.0
        if war <= t < war + 0.55:
            flick = 0.25 + 0.75 * (0.5 + 0.5 * math.sin((t - war) * 70)) * (1 - seg(t, war, war + 0.55)) + 0.15
        dim = 1 - 0.6 * seg(t, war + 0.3, war + 1.0)
        d['lamp'].data.energy = 260 * flick * dim
        d['bulb'].node_tree.nodes['Emission'].inputs[1].default_value = 6 * flick * dim
        pulse = 0.55 + 0.45 * math.sin((t - war) * 7.5)
        d['alarm'].data.energy = 1400 * seg(t, war + 0.2, war + 0.7) * pulse
        d['fill'].data.energy = 60 * (1 - 0.7 * seg(t, war, war + 0.8))
        keys = [(0.0, (0.05, -0.75, 3.35)), (war, (-0.06, -0.8, 3.0)), (war + 1.6, (1.05, -1.75, 1.45)),
                (t1 - 0.9, (0.55, -1.05, 0.82)), (t1, (0.12, -0.42, 0.42))]
        p = path(t, keys)
        tgt = vlerp((0.0, 0.05, 0.0), (0.0, 0.12, 0.05), seg(t, war, t1))
        roll = 0.28 * smooth(seg(t, war + 0.5, t1)) - 0.06 * smooth(seg(t, 0, war))
        p += shake(t, 0.012 * seg(t, war, war + 0.4) * (1 - seg(t, war + 1.2, war + 2.0)), 23)
        look(cam, p, tgt, roll, lens=30 + 4 * seg(t, war, t1))
    sh.update = update


def S14_final(sh, t0, t1):
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.01, 0.012, 0.03, 1)
    d = _desk(sh, final=True)
    # the gifts stand around the paper (2D layers): positions on the desk
    spots = [(-1.18, -0.95), (1.2, -1.15), (-1.25, 0.15), (1.25, 0.25), (0.0, -1.5)]
    for i, (x, y) in enumerate(spots):
        blob((x, y, 0.0), 0.36, 0.55)
        sh.anchor(f'fin{i}', (x, y, 0.36), 0.36)
    cam = camera(30)
    sh.track(cam, 'location', 'rotation_euler')
    cont = E['cont']

    def update(t):
        off = seg(t, cont + 0.45, cont + 0.6)
        d['lamp'].data.energy = 260 * (1 - off) + 8
        d['bulb'].node_tree.nodes['Emission'].inputs[1].default_value = 6 * (1 - off) + 0.05
        d['alarm'].data.energy = 0.0
        d['fill'].data.energy = 60 * (1 - 0.6 * off)
        keys = [(t0, (0.1, -0.35, 0.5)), (t0 + 1.4, (0.35, -1.6, 1.3)), (t0 + 4.5, (0.4, -3.2, 2.6)),
                (t1, (0.2, -4.6, 3.5))]
        p = path(t, keys, ease=lambda x: 1 - (1 - x) ** 2)
        tgt = vlerp((0, 0.1, 0.05), (0, -0.2, 0.2), seg(t, t0, t1))
        look(cam, p, tgt, 0.22 * (1 - smooth(seg(t, t0, t0 + 2.0))))
    sh.update = update


# ====================================================================== S02 blue office (VK era)
def S02_office(sh, t0, t1):
    world_gradient((0.55, 0.72, 0.95), (0.85, 0.9, 1.0), 0.9)
    floor = mat((0.78, 0.82, 0.88), rough=0.3)
    box((40, 40, 0.2), (0, 0, -0.1), m=floor, bevel=0)
    blue = mat((0.27, 0.45, 0.68), rough=0.6)
    box((40, 0.4, 7), (0, 9, 3.5), m=blue, bevel=0)
    box((0.4, 40, 7), (-7.5, 0, 3.5), m=blue, bevel=0)
    sky = emissive((0.75, 0.88, 1.0), 2.5)
    for x in (-4.5, -1.5, 1.5, 4.5):
        plane((2.4, 3.6), (x, 8.78, 3.0), UP, m=sky)
        box((2.6, 0.12, 0.12), (x, 8.75, 1.15), m=mat((0.95, 0.95, 0.97)), bevel=0.02)
    white, legm = mat((0.96, 0.96, 0.97), rough=0.35), mat((0.2, 0.36, 0.6), rough=0.4, metal=0.3)
    scr = emissive((0.55, 0.75, 1.0), 2.2)
    dark = mat((0.08, 0.09, 0.12), rough=0.3)
    chair = mat((0.15, 0.2, 0.3), rough=0.6)
    r = random.Random(4)
    for y in (-9, -6, -3, 0, 3, 6):
        for x in (-2.0, 2.0):
            if (x, y) == (-2.0, 0):
                continue
            box((2.2, 1.0, 0.07), (x, y, 0.78), m=white, bevel=0.02)
            for dx in (-1.0, 1.0):
                box((0.06, 0.9, 0.75), (x + dx, y, 0.38), m=legm, bevel=0.01)
            for k, dx in enumerate((-0.55, 0.55)):
                box((0.75, 0.05, 0.45), (x + dx, y + 0.3, 1.12), m=dark, bevel=0.015)
                plane((0.68, 0.38), (x + dx, y + 0.27, 1.12), UP, m=scr)
                box((0.06, 0.06, 0.3), (x + dx, y + 0.34, 0.95), m=dark, bevel=0)
                box((0.45, 0.16, 0.025), (x + dx, y - 0.15, 0.83), m=mat((0.85, 0.87, 0.9)), bevel=0.005)
                cyl(0.03, 0.4, (x + dx, y - 0.75, 0.25), m=dark)
                box((0.5, 0.5, 0.08), (x + dx, y - 0.75, 0.48), m=chair, bevel=0.03)
                box((0.5, 0.08, 0.55), (x + dx, y - 1.0, 0.8), m=chair, bevel=0.03)
    # the hero desk
    box((2.2, 1.0, 0.07), (-2.0, 0, 0.78), m=white, bevel=0.02)
    for dx in (-1.0, 1.0):
        box((0.06, 0.9, 0.75), (-2.0 + dx, 0, 0.38), m=legm, bevel=0.01)
    box((0.75, 0.05, 0.45), (-2.6, 0.3, 1.12), m=dark, bevel=0.015)
    plane((0.68, 0.38), (-2.6, 0.27, 1.12), UP, m=scr)
    cyl(0.12, 0.2, (-1.3, 0.25, 0.92), m=mat((0.9, 0.6, 0.2), rough=0.3))
    dog = card(A / 'spotty_cutout.png', 1.15, (-1.85, -0.05, 0.815), (PI / 2, 0, 0.12), emit=0.9)
    sh.track(dog, 'scale', 'location')
    fig = card(A / 'figure_q.png', 1.85, (0.6, 1.6, 0.0), (PI / 2, 0, -0.2), emit=0.3)
    # posters, pendant lamps, rug: colour and depth
    for i, (x, c) in enumerate(((-5.5, (0.98, 0.75, 0.3)), (-2.5, (0.95, 0.4, 0.45)), (3.0, (0.4, 0.8, 0.6)), (6.0, (0.98, 0.98, 1.0)))):
        box((1.4, 0.06, 1.9), (x, 8.75, 5.6 if i % 2 else 5.3), m=mat(c, rough=0.7), bevel=0.02)
    pend = emissive((1.0, 0.88, 0.7), 5.0)
    for y in (-6, -3, 0, 3, 6):
        for x in (-2.0, 2.0):
            cyl(0.01, 2.0, (x, y, 5.9), m=mat((0.1, 0.1, 0.1)), verts=6, bevel=0)
            cyl(0.32, 0.3, (x, y, 4.75), m=mat((0.15, 0.25, 0.4), rough=0.4), r2=0.08, bevel=0.01)
            sphere(0.1, (x, y, 4.6), pend, seg=12)
    cyl(1.6, 0.02, (0.2, -1.2, 0.01), m=mat((0.95, 0.6, 0.3), rough=0.9), bevel=0)
    sh.track(fig, 'scale')
    blob((0.6, 1.55, 0), 0.45, 0.4)
    for x, y in ((-5.5, 5.5), (5.5, 2), (-5.5, -4), (5.0, -7)):
        cyl(0.3, 0.5, (x, y, 0.25), m=mat((0.95, 0.95, 0.95)), r2=0.24)
        for i in range(4):
            sphere(0.32, (x + 0.15 * math.cos(i * 1.6), y + 0.15 * math.sin(i * 1.6), 0.75 + 0.18 * i), mat((0.25, 0.6, 0.35)))
    for x, y, c in ((5.4, 6.5, (0.95, 0.55, 0.25)), (4.6, 7.4, (0.3, 0.75, 0.95))):
        sphere(0.65, (x, y, 0.35), mat(c, rough=0.7), scale=(1, 1, 0.55))
    sun((0.95, 0.15, 2.7), 2.8, (1.0, 0.96, 0.9))
    area((0, 0, 6), (0, 0, 0), 900, 10, (0.9, 0.95, 1.0))
    cam = camera(26, dof=2.8)
    cam.data.dof.focus_object = dog
    sh.track(cam, 'location', 'rotation_euler')
    sp, said = E['spotty'], E['said']
    dog_scale = dog.scale.copy()
    fig_scale = fig.scale.copy()

    def update(t):
        k = 0.2 + 0.8 * spring(seg(t, sp - 0.5, sp + 0.7), 1.8, 0.45)
        dog.scale = (dog_scale[0] * k, dog_scale[1] * k, 1)
        kf = spring(seg(t, said - 0.1, said + 0.9), 1.6, 0.45)
        fig.scale = (fig_scale[0] * max(kf, 1e-3), fig_scale[1] * max(kf, 1e-3), 1)
        keys = [(t0, (0.1, -7.5, 1.5)), (sp + 0.3, (-0.7, -1.9, 1.3)), (said + 0.4, (0.0, -1.9, 1.4)),
                (t1 - 0.3, (1.3, -2.6, 1.55)), (t1, (2.0, -2.5, 1.6))]
        p = path(t, keys)
        tgt = path(t, [(t0, (-1.2, 1.0, 1.2)), (sp, (-1.85, 0.0, 1.35)), (said + 0.6, (-0.6, 0.6, 1.15)),
                       (t1 - 0.3, (-0.2, 1.0, 1.2)), (t1, (3.5, 1.0, 1.2))])
        look(cam, p, tgt, 0.05 * math.sin(t * 0.8))
    sh.update = update


# ====================================================================== S03 corridor: he leaves, the dog stays
def S03_past(sh, t0, t1):
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.04, 0.035, 1)
    plank = mat((0.5, 0.33, 0.2), rough=0.45, coat=0.15)
    box((3.4, 18, 0.2), (0, 6, -0.1), m=plank, bevel=0)
    for i in range(7):
        box((0.01, 18, 0.005), (-1.5 + i * 0.5, 6, 0.001), m=mat((0.35, 0.22, 0.13)), bevel=0)
    wall = mat((0.86, 0.8, 0.7), rough=0.8)
    for x in (-1.75, 1.75):
        box((0.2, 18, 3.2), (x, 6, 1.6), m=wall, bevel=0)
        box((0.24, 18, 0.9), (x, 6, 0.45), m=mat((0.55, 0.38, 0.25), rough=0.5), bevel=0)
    box((3.6, 18, 0.2), (0, 6, 3.3), m=mat((0.9, 0.88, 0.84)), bevel=0)
    lamp_m = mat((1, 0.9, 0.7), emit=(1.0, 0.82, 0.55), emit_strength=5.0)
    sh.track(emit_socket(lamp_m), 'default_value')
    lights = []
    for y in (0.5, 4, 7.5, 11):
        box((0.7, 0.25, 0.05), (0, y, 3.18), m=lamp_m, bevel=0.01)
        L = point((0, y, 2.85), 120, (1.0, 0.82, 0.55), r=0.3)
        lights.append(L)
        sh.track(L.data, 'energy')
    for y in (2.5, 9.0):
        box((0.06, 1.0, 0.7), (-1.62, y, 1.7), m=mat((0.3, 0.45, 0.6)), bevel=0.01)
        plane((0.8, 0.55), (-1.58, y, 1.7), (PI / 2, 0, -PI / 2), m=mat((0.6, 0.7, 0.75), rough=0.3))
    # door to the bright blue (new messenger)
    box((3.4, 0.2, 3.2), (0, 14.6, 1.6), m=wall, bevel=0)
    glow = emissive((0.45, 0.72, 1.0), 0.0)
    gl_in = glow.node_tree.nodes['Emission'].inputs[1]
    sh.track(gl_in, 'default_value')
    plane((1.3, 2.3), (0, 14.75, 1.15), UP, m=glow)
    hinge = empty('hinge', (-0.65, 14.5, 0))
    box((1.3, 0.08, 2.3), (0.65, 0, 1.15), m=mat((0.3, 0.2, 0.14), rough=0.4), parent=hinge, bevel=0.02)
    sphere(0.05, (1.15, -0.07, 1.1), mat((0.9, 0.75, 0.3), metal=1, rough=0.2), parent=hinge)
    sh.track(hinge, 'rotation_euler')
    door_light = spot((0, 15.6, 1.4), (0, 6, 0.6), 0.0, (0.5, 0.75, 1.0), 70, 0.6)
    sh.track(door_light.data, 'energy')
    pp = paper_plane((0, 14.4, 1.6), 0.28, emissive((0.85, 0.93, 1.0), 2.0))
    sh.track(pp, 'location', 'rotation_euler', 'scale')
    fig = card(A / 'figure.png', 1.75, (0.15, 2.0, 0), (PI / 2, 0, 0))
    sh.track(fig, 'location')
    # the cardboard box with the cutout, "left in the past"
    cb = mat((0.66, 0.5, 0.32), rough=0.85)
    bx = empty('box', (-0.95, -0.2, 0))
    box((0.9, 0.7, 0.05), (0, 0, 0.03), m=cb, parent=bx, bevel=0.01)
    for (sx, sy, x, y) in ((0.9, 0.05, 0, -0.33), (0.9, 0.05, 0, 0.33), (0.05, 0.7, -0.43, 0), (0.05, 0.7, 0.43, 0)):
        box((sx, sy, 0.55), (x, y, 0.3), m=cb, parent=bx, bevel=0.005)
    flap = box((0.9, 0.35, 0.03), (0, -0.52, 0.6), (-0.9, 0, 0), m=cb, parent=bx, bevel=0.005)
    box((0.03, 0.4, 0.3), (0.62, 0.0, 0.52), (0, 0.9, 0), m=cb, parent=bx, bevel=0.005)
    card(A / 'spotty_cutout.png', 0.8, (-0.95, -0.12, 0.2), (PI / 2 - 0.12, 0, 0.1))
    dust_m = emissive((1.0, 0.9, 0.7), 1.5)
    dust = []
    for i, p in enumerate(scatter(11, 40, (-2.0, 0.2), (-1.4, 1.2), (0.2, 2.4))):
        s = sphere(0.008 + 0.006 * (i % 3), p, dust_m, seg=8)
        dust.append((s, Vector(p), i))
        sh.track(s, 'location')
    cam = camera(26, dof=3.5)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data, 'lens')
    left, tg, past = E['left'], E['telegram1'], E['past']

    def update(t):
        w = seg(t, t0, tg + 0.6)
        fig.location = (0.15 + 0.05 * math.sin(t * 9), lerp(2.0, 13.6, w), 0.04 * abs(math.sin(t * 9)))
        op = smooth(seg(t, tg - 0.3, tg + 0.5)) * (1 - smooth(seg(t, past - 1.0, past + 0.2)))
        hinge.rotation_euler = (0, 0, -1.6 * op)
        gl_in.default_value = 6.0 * op
        door_light.data.energy = 3500 * op
        u = seg(t, tg, tg + 1.6)
        pp.location = (0.4 * math.sin(u * 5), lerp(14.6, 7.0, u), 1.7 + 0.5 * math.sin(u * 3))
        pp.rotation_euler = (0.2 * math.sin(u * 6), 0.6 * math.sin(u * 4), PI)
        pp.scale = (1, 1, 1) if 0 < u < 1 else (0.001, 0.001, 0.001)
        dim = 1 - 0.75 * smooth(seg(t, past - 0.6, past + 0.5))
        for L in lights:
            L.data.energy = 120 * dim
        emit_socket(lamp_m).default_value = 5.0 * dim
        for s, p0, i in dust:
            s.location = (p0.x + 0.05 * math.sin(t * 0.7 + i), p0.y, p0.z + 0.08 * math.sin(t * 0.5 + i * 1.3))
        keys = [(t0, (0.35, -1.2, 1.55)), (tg - 0.2, (0.25, 0.6, 1.5)), (tg + 0.8, (0.2, 0.2, 1.45)),
                (past - 0.6, (0.7, -1.9, 1.25)), (t1, (0.35, -1.75, 0.95))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 10, 1.3)), (tg + 0.6, (0, 13, 1.3)), (tg + 1.5, (-0.6, 2.0, 0.8)),
                       (past - 0.6, (-0.95, -0.15, 0.55)), (t1, (-0.95, -0.15, 0.55))])
        look(cam, p, tgt, 0.0, lens=lerp(26, 34, smooth(seg(t, tg + 0.6, past))))
    sh.update = update


# ====================================================================== S04 gift showroom, VPN tease
def S04_vault(sh, t0, t1):
    world_gradient((0.03, 0.12, 0.42), (0.1, 0.35, 0.85), 0.55)
    W = bpy.context.scene.world.node_tree.nodes['Background'].inputs[1]
    sh.track(W, 'default_value')
    cyl(22, 0.2, (0, 0, -0.1), m=mat((0.06, 0.22, 0.62), rough=0.12, coat=0.8), bevel=0)
    for R in (3, 6, 9, 12):
        torus(R, 0.02, (0, 0, 0.005), m=emissive((0.7, 0.9, 1.0), 1.5))
    ped_m, ring_m = mat((0.97, 0.98, 1.0), rough=0.2, coat=0.6), emissive((0.45, 0.85, 1.0), 4.0)
    peds = {'gift_main': (0.0, 0.0), 'gift_vpn': (3.4, 2.4)}
    for name, (x, y) in peds.items():
        cyl(0.8, 0.9, (x, y, 0.45), m=ped_m, bevel=0.06)
        cyl(0.95, 0.12, (x, y, 0.06), m=ped_m, bevel=0.04)
        torus(0.8, 0.035, (x, y, 0.88), m=ring_m)
        blob((x, y, 0.9), 0.55, 0.55)
        sh.anchor(name, (x, y, 0.9 + 0.55), 0.55)
    r = random.Random(5)
    cols = [(0.95, 0.35, 0.45), (0.98, 0.75, 0.25), (0.45, 0.8, 0.5), (0.7, 0.45, 0.95), (0.98, 0.98, 1.0)]
    for i, (x, y) in enumerate(((-3.2, 3.5), (-4.6, 0.8), (6.2, 5.8), (-1.6, 6.5), (1.5, 7.5), (7.0, 1.2), (-6.0, 5.5))):
        gift_box((x, y, 0), r.uniform(0.6, 1.2), cols[i % 5], rot=r.uniform(0, 3))
    bub_m = emissive((0.55, 0.85, 1.0), 3.0)
    bubbles = []
    for i, p in enumerate(scatter(9, 30, (-7, 9), (3, 12), (1.5, 6.5))):
        s = sphere(0.03 + 0.05 * ((i * 7) % 5) / 5, p, bub_m, seg=12)
        bubbles.append((s, Vector(p), i))
        sh.track(s, 'location')
    spA = spot((0, -0.5, 5.0), (0, 0, 0.9), 0.0, (1.0, 0.95, 0.9), 32, 0.5)
    spB = spot((3.3, 1.9, 5.0), (3.4, 2.4, 0.9), 0.0, (0.85, 0.93, 1.0), 32, 0.5)
    key = area((-3, -4, 5), (0, 0, 0), 450, 6, (0.8, 0.9, 1.0))
    sh.track(spA.data, 'energy')
    sh.track(spB.data, 'energy')
    sh.track(key.data, 'energy')
    cam = camera(28, dof=4.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    g1, vpn, co, nt = E['gift1'], E['models5'], E['story'] - 0.3, E['story']

    def update(t):
        dim = 1 - 0.7 * smooth(seg(t, nt - 0.2, nt + 0.6))
        W.default_value = 0.55 * dim + 0.04
        key.data.energy = 450 * dim
        spA.data.energy = 1800 * smooth(seg(t, g1 - 0.3, g1 + 0.2)) * (1 - 0.6 * smooth(seg(t, nt - 0.2, nt + 0.5)))
        spB.data.energy = 2200 * smooth(seg(t, vpn - 0.3, vpn + 0.2))
        for s, p0, i in bubbles:
            s.location = (p0.x + 0.2 * math.sin(t * 0.4 + i), p0.y, p0.z + 0.35 * math.sin(t * 0.6 + i * 0.9))
        keys = [(t0, (-3.5, -10.5, 7.5)), (t0 + 0.9, (-0.9, -4.6, 2.2)), (g1 + 0.7, (0.5, -3.9, 1.75)),
                (vpn - 0.4, (2.3, -1.4, 1.75)), (co, (2.7, -0.4, 1.6)), (t1, (3.05, 0.75, 1.5))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0, 0, 0.6)), (g1 + 0.9, (0.1, 0, 1.3)), (vpn - 0.2, (3.4, 2.4, 1.35)),
                       (t1, (3.4, 2.4, 1.4))])
        look(cam, p, tgt, -0.04 * math.sin(t * 0.7))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S05 courtroom, April 2018
def S05_court(sh, t0, t1):
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.02, 0.015, 0.012, 1)
    wd, wd2, wd3 = mat((0.3, 0.16, 0.08), rough=0.4, coat=0.3), mat((0.42, 0.24, 0.12), rough=0.45), mat((0.2, 0.1, 0.05), rough=0.5)
    box((20, 20, 0.2), (0, 2, -0.1), m=mat((0.16, 0.08, 0.05), rough=0.35, coat=0.4), bevel=0)
    for i in range(10):
        box((20, 0.02, 0.005), (0, -7 + i * 1.8, 0.002), m=wd3, bevel=0)
    box((20, 0.3, 9), (0, 6.4, 4.5), m=wd, bevel=0)
    for x in range(-8, 9, 2):
        box((1.6, 0.1, 2.4), (x, 6.22, 1.3), m=wd2, bevel=0.04)
        box((1.6, 0.1, 2.2), (x, 6.22, 4.0), m=wd2, bevel=0.04)
    for x in (-4.2, 4.2):
        cyl(0.35, 7, (x, 5.6, 3.5), m=mat((0.85, 0.8, 0.7), rough=0.5), verts=24, bevel=0.02)
        cyl(0.5, 0.3, (x, 5.6, 0.15), m=mat((0.85, 0.8, 0.7)), bevel=0.03)
    curt = mat((0.45, 0.05, 0.07), rough=0.7)
    for x in (-6.5, -5.3, 5.3, 6.5):
        for k in range(5):
            cyl(0.16, 7.5, (x + k * 0.22 - 0.44, 6.0, 3.75), m=curt, verts=12, bevel=0)
    for row in range(4):
        for x in (-2.6, 2.6):
            y = -1.5 - row * 1.6
            box((3.4, 0.45, 0.12), (x, y, 0.55), m=wd2, bevel=0.03)
            box((3.4, 0.1, 0.7), (x, y + 0.25, 0.85), m=wd, bevel=0.03)
            for dx in (-1.5, 1.5):
                box((0.1, 0.5, 0.55), (x + dx, y, 0.27), m=wd3, bevel=0.01)
    torus(1.2, 0.05, (0, 1.0, 6.0), m=mat((0.8, 0.65, 0.3), metal=1, rough=0.3))
    for a in range(8):
        sphere(0.12, (math.cos(a * PI / 4) * 1.2, 1.0 + math.sin(a * PI / 4) * 1.2, 5.9), emissive((1.0, 0.85, 0.6), 6.0), seg=12)
    box((5.4, 1.6, 1.8), (0, 4.2, 0.9), m=wd, bevel=0.06)
    box((5.6, 1.8, 0.12), (0, 4.2, 1.86), m=wd2, bevel=0.03)
    for x in (-1.8, 0, 1.8):
        box((1.5, 0.08, 1.2), (x, 3.38, 0.9), m=wd2, bevel=0.03)
    cyl(0.32, 0.12, (0.6, 3.95, 1.98), m=wd3, bevel=0.02)                         # sound block
    piv = empty('gavel', (1.55, 3.95, 2.05))
    cyl(0.045, 1.0, (-0.5, 0, 0.0), (0, PI / 2, 0), m=wd2, parent=piv)
    cyl(0.17, 0.5, (-0.95, 0, 0.0), (0, 0, 0), m=wd3, parent=piv, bevel=0.03)
    sh.track(piv, 'rotation_euler')
    # calendar
    cal = empty('cal', (-2.6, 6.0, 3.1))
    box((1.9, 0.08, 2.3), (0, 0, 0), m=mat((0.96, 0.94, 0.9), rough=0.8), parent=cal, bevel=0.02)
    box((1.9, 0.1, 0.55), (0, -0.01, 0.9), m=mat((0.8, 0.12, 0.12), rough=0.5), parent=cal, bevel=0.02)
    for x in (-0.5, 0.5):
        torus(0.07, 0.02, (x, -0.06, 1.18), (0, PI / 2, 0), m=mat((0.7, 0.7, 0.75), metal=1, rough=0.2)).parent = cal
    text('АПРЕЛЬ', 0.32, (0, -0.07, 0.9), UP, m=mat((1, 1, 1)), extrude=0.01, parent=cal)
    text('2018', 0.85, (0, -0.07, -0.1), UP, m=mat((0.12, 0.1, 0.1)), extrude=0.02, parent=cal)
    text('13', 0.3, (-0.55, -0.07, -0.85), UP, m=mat((0.8, 0.12, 0.12)), extrude=0.01, parent=cal, weight='Bold')
    text('16', 0.3, (0.55, -0.07, -0.85), UP, m=mat((0.8, 0.12, 0.12)), extrude=0.01, parent=cal, weight='Bold')
    # the encryption key
    key_m = mat((0.85, 0.7, 0.3), metal=1.0, rough=0.22, emit=(0.4, 0.85, 1.0), emit_strength=0.0)
    sh.track(emit_socket(key_m), 'default_value')
    kr = empty('key', (2.4, 1.2, 1.75))
    torus(0.32, 0.08, (-0.75, 0, 0), (PI / 2, 0, 0), m=key_m).parent = kr
    cyl(0.07, 1.25, (0.05, 0, 0), (0, PI / 2, 0), m=key_m, parent=kr)
    for dx, h in ((0.45, 0.26), (0.6, 0.18), (0.25, 0.2)):
        box((0.08, 0.06, h), (dx, 0, -h / 2), m=key_m, parent=kr, bevel=0.01)
    sh.track(kr, 'rotation_euler', 'location')
    cyl(0.45, 1.0, (2.4, 1.2, 0.5), m=mat((0.25, 0.14, 0.08), rough=0.4), bevel=0.04)
    kspot = spot((2.4, 0.4, 4.2), (2.4, 1.2, 1.5), 1200, (0.6, 0.85, 1.0), 30, 0.4)
    sh.track(kspot.data, 'energy')
    warm = area((-4, -3, 6), (0, 3, 1), 700, 3, (1.0, 0.75, 0.5))
    sh.track(warm.data, 'energy')
    red = area((3.5, -2, 5), (0, 3.5, 1.5), 0.0, 6, (1.0, 0.08, 0.06))
    sh.track(red.data, 'energy')
    point((-2.6, 4.6, 4.3), 220, (1.0, 0.85, 0.65))
    cam = camera(30, dof=4.5)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data, 'lens')
    sh.track(cam.data.dof, 'focus_distance')
    ap, keys_t, court, blk = E['april'], E['keys'], E['court'], E['blocks']

    def update(t):
        a = smooth(seg(t, blk - 1.1, blk - 0.35))
        fall = ease_in(seg(t, blk - 0.32, blk))
        ang = -1.2 * a * (1 - fall) + 0.08 * math.sin(clamp(t - blk, 0, 1) * 18) * math.exp(-6 * max(0, t - blk)) * (t > blk)
        piv.rotation_euler = (0, ang, 0)
        kr.rotation_euler = (0.3 * math.sin(t * 0.8), 0, t * 0.9)
        kr.location = (2.4, 1.2, 1.75 + 0.06 * math.sin(t * 1.7))
        emit_socket(key_m).default_value = 4.0 * smooth(seg(t, keys_t - 0.2, keys_t + 0.3)) * (1 - smooth(seg(t, blk, blk + 0.3)))
        hit = smooth(seg(t, blk, blk + 0.08))
        red.data.energy = 1500 * hit * (0.6 + 0.4 * math.sin((t - blk) * 9))
        warm.data.energy = 700 * (1 - 0.65 * hit)
        kspot.data.energy = 1200 * (1 - 0.8 * hit)
        keys = [(t0, (-2.75, 3.6, 3.3)), (ap + 0.9, (-2.5, 3.2, 3.15)), (ap + 2.2, (-0.6, -2.8, 2.4)),
                (keys_t, (1.4, -0.4, 1.95)), (blk - 0.5, (1.3, 1.6, 1.5)), (t1, (1.15, 1.95, 1.25))]
        p = path(t, keys)
        tgt = path(t, [(t0, (-2.6, 6.0, 3.15)), (ap + 1.0, (-2.6, 6.0, 3.0)), (ap + 2.2, (1.5, 2.5, 1.7)),
                       (keys_t, (2.4, 1.2, 1.75)), (blk - 0.6, (0.8, 4.0, 2.0)), (t1, (0.7, 4.0, 2.0))])
        p += shake(t, 0.06 * math.exp(-5 * max(0, t - blk)) * (t >= blk), 31)
        look(cam, p, tgt, 0.0, lens=lerp(30, 22, smooth(seg(t, blk - 1.0, blk - 0.3))))
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S06 rooftop poster: the hood
def S06_roof(sh, t0, t1):
    world_gradient((0.02, 0.025, 0.07), (0.16, 0.1, 0.24), 1.0)
    box((22, 22, 0.3), (0, 2, -0.15), m=mat((0.22, 0.24, 0.3), rough=0.85), bevel=0)
    par = mat((0.3, 0.32, 0.38), rough=0.8)
    for (s, l) in (((22, 0.4, 0.7), (0, -9, 0.35)), ((0.4, 22, 0.7), (-11, 2, 0.35)), ((0.4, 22, 0.7), (11, 2, 0.35))):
        box(s, l, m=par, bevel=0.02)
    tex = window_texture('win_night', 3, warm=True)
    tm = tower_mat('towers', tex, strength=2.2, density=0.8)
    r = random.Random(12)
    for i in range(70):
        ang = r.uniform(-1.2, 1.2) + PI / 2
        dist = r.uniform(16, 48)
        x, y = math.cos(ang) * dist, math.sin(ang) * dist
        w, h = r.uniform(2.5, 6), r.uniform(4, 26)
        box((w, w * r.uniform(0.7, 1.3), h), (x, y, h / 2 - 8), m=tm, bevel=0)
    sphere(2.2, (-24, 60, 26), emissive((1.0, 0.95, 0.85), 3.0))
    # billboard
    frame_m, panel_m = mat((0.1, 0.1, 0.12), rough=0.4, metal=0.5), mat((0.12, 0.13, 0.2), rough=0.7)
    for x in (-1.8, 1.8):
        box((0.18, 0.18, 2.0), (x, 6.0, 1.0), m=frame_m, bevel=0.02)
    box((4.8, 0.3, 3.6), (0, 6.1, 3.6), m=frame_m, bevel=0.05)
    pn = plane((4.4, 3.2), (0, 5.94, 3.6), UP, m=panel_m)
    glow_m = emissive((0.25, 0.6, 1.0), 0.0)
    gin = glow_m.node_tree.nodes['Emission'].inputs[1]
    sh.track(gin, 'default_value')
    for (s, l) in (((4.8, 0.06, 0.06), (0, 5.93, 5.42)), ((4.8, 0.06, 0.06), (0, 5.93, 1.78)),
                   ((0.06, 0.06, 3.6), (-2.42, 5.93, 3.6)), ((0.06, 0.06, 3.6), (2.42, 5.93, 3.6))):
        box(s, l, m=glow_m, bevel=0)
    dog = card(A / 'spotty_cutout.png', 2.3, (0, 5.9, 2.65), UP, emit=0.9)
    hood = card(A / 'hooded_cutout.png', 2.3, (0, 5.88, 2.65), UP, emit=0.9)
    sh.track(dog, 'scale')
    sh.track(hood, 'scale', 'location')
    strip = empty('strip', (-2.05, 5.86, 2.2))
    words = card(A / 'poster_text.png', 0.48, (2.05, 0, 0), UP, emit=2.0, parent=strip)
    words.location = (2.05, 0, -0.24)
    sh.track(strip, 'scale')
    lamps = []
    for x in (-1.4, 1.4):
        cyl(0.08, 0.5, (x, 5.4, 5.6), (1.2, 0, 0), m=frame_m)
        L = spot((x, 5.3, 5.6), (x * 0.4, 5.9, 3.4), 0.0, (0.9, 0.95, 1.0), 55, 0.5)
        lamps.append(L)
        sh.track(L.data, 'energy')
    # roof props
    pm = mat((0.55, 0.58, 0.62), rough=0.5, metal=0.4)
    for x, y in ((-5, 1), (-6.5, 3.5), (5.5, -1)):
        box((1.6, 1.2, 1.0), (x, y, 0.5), m=pm, bevel=0.05)
        cyl(0.42, 0.06, (x, y - 0.61, 0.55), (PI / 2, 0, 0), m=mat((0.2, 0.2, 0.22)))
    cyl(1.2, 2.2, (6.5, 4.5, 2.2), m=mat((0.45, 0.35, 0.3), rough=0.7), bevel=0.05)
    for x, y in ((5.8, 3.8), (7.2, 3.8), (5.8, 5.2), (7.2, 5.2)):
        cyl(0.07, 1.2, (x, y, 0.6), m=frame_m)
    cyl(0.04, 4.0, (-7.5, 6, 2.0), m=frame_m)
    blink = emissive((1.0, 0.1, 0.1), 0.0)
    bin_ = blink.node_tree.nodes['Emission'].inputs[1]
    sh.track(bin_, 'default_value')
    sphere(0.1, (-7.5, 6, 4.05), blink)
    bulbs = emissive((1.0, 0.8, 0.45), 4.0)
    for i in range(18):
        u = i / 17
        sphere(0.05, (lerp(-7.5, -2.2, u), lerp(6, 6.0, u), 3.9 - 1.3 * math.sin(u * PI)), bulbs, seg=8)
    moon = sun((0.9, 0.2, -2.6), 0.6, (0.6, 0.7, 1.0))
    area((0, -4, 6), (0, 3, 0), 300, 8, (0.45, 0.4, 0.9))
    cam = camera(26, dof=5.0)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data.dof, 'focus_distance')
    pub, hd, sign, res = E['pub'], E['hood'], E['sign'], E['resist']
    ds = dog.scale.copy()

    def update(t):
        on = smooth(seg(t, pub - 0.2, pub + 0.4))
        flick = 1.0 if t < res else (0.4 + 0.6 * (math.sin((t - res) * 50) > -0.3) if t < res + 0.5 else 1.0)
        gin.default_value = 6.0 * on * flick
        for L in lamps:
            L.data.energy = 1600 * on
        bin_.default_value = 8.0 * (math.sin(t * 5) > 0.3)
        d = ease_in(seg(t, hd - 0.45, hd))
        hood.location = (0, 5.88, 2.65 + 3.2 * (1 - d))
        k = 1.0 + 0.06 * math.sin(clamp(t - hd, 0, 1) * 25) * math.exp(-5 * max(0, t - hd)) * (t >= hd)
        hood.scale = (ds[0] * k * (d > 0.001), ds[1] * k * (d > 0.001) + 1e-4, 1)
        dog.scale = (ds[0], ds[1], 1) if t < hd else (1e-4, 1e-4, 1)
        sx = smooth(seg(t, sign - 0.05, sign + 1.1))
        strip.scale = (max(sx, 1e-4), 1, 1)
        keys = [(t0, (2.0, -7.5, 0.55)), (pub, (1.1, -4.6, 1.2)), (hd - 0.3, (0.35, -1.8, 2.8)),
                (sign + 0.2, (-0.6, -2.4, 3.2)), (t1, (-2.6, -4.8, 5.6))]
        p = path(t, keys)
        tgt = path(t, [(t0, (0.5, 6, 2.0)), (hd - 0.2, (0, 5.9, 3.6)), (sign + 0.4, (0, 5.9, 2.9)),
                       (t1, (0, 5.9, 3.2))])
        p += shake(t, 0.03 * math.exp(-6 * max(0, t - hd)) * (t >= hd), 19)
        look(cam, p, tgt, 0.0)
        cam.data.dof.focus_distance = (Vector(tgt) - p).length
    sh.update = update


# ====================================================================== S07 IP city blackout + proxy tunnel
def S07_ipcity(sh, t0, t1):
    world_gradient((0.01, 0.02, 0.05), (0.04, 0.06, 0.14), 1.0)
    gm = mat((0.03, 0.04, 0.07), rough=0.25, coat=0.4)
    box((120, 120, 0.2), (0, 20, -0.1), m=gm, bevel=0)
    grid = emissive((0.15, 0.35, 0.8), 1.2)
    for i in range(-14, 15):
        box((0.04, 120, 0.01), (i * 3.2 + 1.6, 20, 0.005), m=grid, bevel=0)
        box((120, 0.04, 0.01), (0, i * 3.2 + 1.6 + 20, 0.005), m=grid, bevel=0)
    tex = window_texture('win_server', 5, cols=4, rows=16, lit=0.7)
    tm = tower_mat('servers', tex, base=(0.04, 0.05, 0.08), strength=3.0, objcolor=True)
    r = random.Random(21)
    towers = []
    for i in range(-5, 6):
        for j in range(-4, 9):
            if i == 0:
                continue
            x, y = i * 3.2, j * 3.2
            h = r.uniform(2.5, 9.0) if abs(i) > 1 else r.uniform(2.0, 5.0)
            ob = box((1.7, 1.7, h), (x, y, h / 2), m=tm, bevel=0.04)
            ob.color = (0.45, 0.75, 1.0, 1.0)
            fall = r.random() < 0.38
            towers.append((ob, x, y, h, fall, r.uniform(0, 1.2)))
            sh.track(ob, 'color', 'location')
    lab_m = emissive((0.6, 0.85, 1.0), 3.0)
    for k, (ob, x, y, h, fall, d) in enumerate(towers[::9]):
        ip = f'{r.randint(31, 217)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}'
        tx = text(ip, 0.32, (x, y - 0.9, min(h, 4.0) - 0.4), UP, m=lab_m, extrude=0.0, bevel=0, weight='Semibold')
        tx.parent = ob
        tx.location = (0, -0.9, min(h, 4.0) - 0.4 - h / 2)
    scan = box((40, 0.15, 12), (0, -20, 6), m=emissive((1.0, 0.1, 0.12), 4.0), bevel=0)
    sh.track(scan, 'location')
    # paper plane + tunnel
    plane_m = emissive((0.9, 0.96, 1.0), 2.5)
    pp = paper_plane((0, -6, 1.2), 0.45, plane_m, 'proxy_plane')
    sh.track(pp, 'location', 'rotation_euler')
    tun_m = mat((0.06, 0.08, 0.14), rough=0.3, metal=0.5)
    tube = cyl(2.0, 22, (0, 40, 1.9), (PI / 2, 0, 0), m=tun_m, verts=48, bevel=0, open_ends=True)
    ring_m = emissive((0.3, 0.75, 1.0), 6.0)
    for k in range(12):
        torus(1.9, 0.05, (0, 30 + k * 1.8, 1.9), (PI / 2, 0, 0), m=ring_m)
    torus(2.15, 0.25, (0, 29.0, 1.9), (PI / 2, 0, 0), m=mat((0.2, 0.25, 0.35), metal=0.6, rough=0.3))
    end_glow = plane((5, 5), (0, 50.9, 1.9), UP, m=emissive((0.8, 0.92, 1.0), 8.0))
    cyl(1.0, 0.25, (0, 28.6, 4.55), m=mat((0.15, 0.2, 0.3), metal=0.7, rough=0.3), bevel=0.05)
    torus(1.0, 0.04, (0, 28.6, 4.68), m=emissive((0.3, 0.75, 1.0), 6.0))
    blob((0, 28.6, 4.69), 0.7, 0.5)
    sh.anchor('m_vpn', (0, 28.6, 4.69 + 0.75), 0.75)
    sun((0.9, 0.0, 0.6), 0.5, (0.5, 0.6, 1.0))
    red = area((0, 10, 14), (0, 10, 0), 0.0, 30, (1.0, 0.1, 0.1))
    sh.track(red.data, 'energy')
    cam = camera(26)
    sh.track(cam, 'location', 'rotation_euler')
    sh.track(cam.data, 'lens')
    rkn, mil, fall_t, tg, px = t0 + 0.2, E['hello'], E['fall'], E['tg'], E['proxy']

    def plane_pos(t):
        u = seg(t, tg - 0.9, t1 + 0.4)
        y = lerp(-8, 48, u ** 1.6)
        return Vector((0.35 * math.sin(u * 7), y, 1.4 + 0.35 * math.sin(u * 5) + 0.5 * smooth(seg(y, 20, 30))))

    def update(t):
        sy = lerp(-16, 30, seg(t, rkn, mil + 0.6))
        scan.location = (0, sy, 6 if rkn <= t <= mil + 0.6 else -30)
        red.data.energy = 9000 * smooth(seg(t, mil - 0.2, mil + 0.6)) * (1 - 0.5 * smooth(seg(t, tg - 0.6, tg + 0.4)))
        for ob, x, y, h, fall, d in towers:
            turned = smooth(seg(sy - y, 0, 2.5)) if t < mil + 0.6 else 1.0
            off = 1.0 - 0.85 * smooth(seg(t, fall_t + d * 0.6 - 0.2, fall_t + d * 0.6 + 0.4)) if fall else 1.0
            ob.color = (lerp(0.45, 1.0, turned), lerp(0.75, 0.12, turned), lerp(1.0, 0.1, turned), off)
            sink = ease_in(seg(t, fall_t + d * 0.7, fall_t + d * 0.7 + 1.0)) if fall else 0.0
            ob.location = (x + 0.06 * math.sin(t * 40 + d * 10) * (0 < sink < 1), y, h / 2 - (h + 0.2) * sink)
        pp.location = plane_pos(t)
        u = seg(t, tg - 0.9, t1)
        pp.rotation_euler = (0.1 * math.sin(u * 9), 0.35 * math.sin(u * 7 + 0.5), -0.2 * math.cos(u * 7))
        chase = smooth(seg(t, tg - 0.5, tg + 0.3))
        keys = [(t0, (2.2, 23.6, 5.4)), (E['vpn'] + 0.6, (1.4, 24.6, 5.2)), (mil + 0.5, (-4.0, 12.0, 8.0)),
                (fall_t + 0.6, (-9.0, -6.0, 9.0)), (tg - 0.5, (-2.5, -9.5, 3.0))]
        p1 = path(min(t, tg - 0.5), keys)
        tg1 = path(min(t, tg - 0.5), [(t0, (0, 28.6, 5.4)), (mil, (0, 28.6, 5.0)), (fall_t + 0.4, (0, 12, 1.5)),
                                       (tg - 0.5, (0, -3, 1.3))])
        pp_ = plane_pos(t)
        p2 = pp_ + Vector((0.12, -1.15, 0.32))
        tg2 = pp_ + Vector((0, 4.0, -0.25))
        p = p1.lerp(p2, chase)
        tgt = Vector(tg1).lerp(tg2, chase)
        look(cam, p, tgt, 0.12 * math.sin(t * 2.0) * chase, lens=lerp(26, 22, chase))
    sh.update = update


from shots_b import S08_planes, S09_legend, S10_ton, S11_giftrain, S12_gallery, S13_laser  # noqa: E402,F401


from shots_c import S15_phone, S16_hacker, S17_havana, S18_arena, S19_crypto  # noqa: E402,F401
