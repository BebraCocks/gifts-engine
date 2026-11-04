"""Blender helpers for the stylized diorama look. Runs inside the bpy module (Blender 5.2).
Everything is a function of content time t, so any frame can be rendered alone."""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector, Matrix, Euler
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[3]
FONT = ROOT / 'input' / 'fonts' / 'SF-Pro-Text'
FPS = 60


# ------------------------------------------------------------------ scene
def reset(scale=50, samples=6, world=(0.05, 0.06, 0.09), strength=1.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
    sc.render.resolution_percentage = scale
    sc.render.fps = FPS
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.image_settings.compression = 15
    sc.eevee.taa_render_samples = samples
    try:
        sc.eevee.use_shadows = True
        sc.eevee.shadow_ray_count = 1
        sc.eevee.shadow_step_count = 4
        sc.eevee.use_raytracing = False
        sc.eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
    except AttributeError:
        pass
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Punchy'
    except TypeError:
        pass
    sc.render.use_motion_blur = __import__('os').environ.get('RD_MB', '1') == '1'
    sc.render.motion_blur_shutter = 0.5
    w = bpy.data.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*world, 1)
    bg.inputs[1].default_value = strength
    return sc


def world_gradient(top, bottom, strength=1.0, horizon=0.5):
    """Sky gradient by view direction (z): bottom colour below the horizon, top above."""
    w = bpy.context.scene.world
    nt = w.node_tree
    nodes, links = nt.nodes, nt.links
    tc = nodes.new('ShaderNodeTexCoord')
    sep = nodes.new('ShaderNodeSeparateXYZ')
    ramp = nodes.new('ShaderNodeValToRGB')
    links.new(tc.outputs['Generated'], sep.inputs[0])
    mr = nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -0.2
    mr.inputs['From Max'].default_value = 1.0
    links.new(sep.outputs['Z'], mr.inputs['Value'])
    links.new(mr.outputs['Result'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[0].position = horizon * 0.6
    ramp.color_ramp.elements[1].color = (*top, 1)
    bg = nodes['Background']
    links.new(ramp.outputs['Color'], bg.inputs[0])
    bg.inputs[1].default_value = strength


# ------------------------------------------------------------------ materials
_MATS = {}


def mat(color, rough=0.55, metal=0.0, emit=None, emit_strength=0.0, name=None, spec=0.4, alpha=1.0,
        coat=0.0):
    key = (tuple(round(c, 3) for c in color), rough, metal, emit and tuple(emit), emit_strength, spec, alpha, coat, name)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name or 'm%d' % len(_MATS))
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color[:3], 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Specular IOR Level'].default_value = spec
    if coat:
        p.inputs['Coat Weight'].default_value = coat
    if emit is not None:
        p.inputs['Emission Color'].default_value = (*emit[:3], 1)
        p.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        p.inputs['Alpha'].default_value = alpha
    _MATS[key] = m
    return m


def glow_mat(color, strength=2.0, alpha=0.35):
    """Additive-looking transparent emission (light beams)."""
    m = bpy.data.materials.new('beam')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*color[:3], 1)
    e.inputs[1].default_value = strength
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    ad = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(e.outputs[0], ad.inputs[0])
    nt.links.new(tr.outputs[0], ad.inputs[1])
    nt.links.new(ad.outputs[0], nt.nodes['Material Output'].inputs[0])
    try:
        m.surface_render_method = 'BLENDED'
    except AttributeError:
        pass
    return m


def emissive(color, strength=3.0):
    m = bpy.data.materials.new('emit')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*color[:3], 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes['Material Output'].inputs[0])
    return m


def image_mat(path, emit=0.0, rough=0.7, name=None, shadow=True):
    """Image with alpha on a card (paper cutouts, posters)."""
    m = bpy.data.materials.new(name or Path(path).stem)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tex.interpolation = 'Cubic'
    nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
    nt.links.new(tex.outputs['Alpha'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = rough
    if emit:
        nt.links.new(tex.outputs['Color'], p.inputs['Emission Color'])
        p.inputs['Emission Strength'].default_value = emit
    try:
        m.surface_render_method = 'DITHERED'
    except AttributeError:
        pass
    return m


def blob_mat(strength=0.75):
    """Soft round contact shadow (dark, transparent edge) for 2D gifts standing in 3D."""
    m = bpy.data.materials.new('blob')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    gr = nt.nodes.new('ShaderNodeTexGradient')
    gr.gradient_type = 'SPHERICAL'
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Location'].default_value = (-1, -1, 0)
    mp.inputs['Scale'].default_value = (2, 2, 2)
    nt.links.new(tc.outputs['UV'], mp.inputs[0])
    nt.links.new(mp.outputs[0], gr.inputs[0])
    pw = nt.nodes.new('ShaderNodeMath')
    pw.operation = 'POWER'
    pw.inputs[1].default_value = 1.6
    nt.links.new(gr.outputs['Fac'], pw.inputs[0])
    ml = nt.nodes.new('ShaderNodeMath')
    ml.operation = 'MULTIPLY'
    ml.inputs[1].default_value = strength
    nt.links.new(pw.outputs[0], ml.inputs[0])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    bk = nt.nodes.new('ShaderNodeEmission')
    bk.inputs[0].default_value = (0, 0, 0, 1)
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(ml.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(bk.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs[0])
    try:
        m.surface_render_method = 'BLENDED'
    except AttributeError:
        pass
    return m


# ------------------------------------------------------------------ geometry
def _finish(ob, material, bevel=0.0, seg=3, smooth=True, parent=None):
    if material is not None:
        ob.data.materials.append(material)
    if bevel:
        md = ob.modifiers.new('bevel', 'BEVEL')
        md.width = bevel
        md.segments = seg
        md.limit_method = 'ANGLE'
    if smooth and hasattr(ob.data, 'polygons'):
        for p in ob.data.polygons:
            p.use_smooth = True
        try:
            ob.data.shade_smooth()
        except AttributeError:
            pass
    if parent is not None:
        ob.parent = parent
    return ob


def box(size, loc=(0, 0, 0), rot=(0, 0, 0), m=None, bevel=0.05, seg=3, parent=None, name=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = size
    bpy.ops.object.transform_apply(scale=True)
    if name:
        ob.name = name
    return _finish(ob, m, bevel, seg, parent=parent)


def cyl(r, h, loc=(0, 0, 0), rot=(0, 0, 0), m=None, bevel=0.03, verts=40, parent=None, name=None, r2=None, open_ends=False):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc, rotation=rot,
                                            end_fill_type='NOTHING' if open_ends else 'NGON')
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=h, vertices=verts, location=loc, rotation=rot,
                                        end_fill_type='NOTHING' if open_ends else 'NGON')
    ob = bpy.context.object
    if name:
        ob.name = name
    return _finish(ob, m, bevel, parent=parent)


def sphere(r, loc=(0, 0, 0), m=None, scale=(1, 1, 1), seg=32, parent=None, name=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=seg // 2, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = scale
    if name:
        ob.name = name
    return _finish(ob, m, parent=parent)


def torus(R, r, loc=(0, 0, 0), rot=(0, 0, 0), m=None, parent=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, location=loc, rotation=rot,
                                     major_segments=48, minor_segments=16)
    return _finish(bpy.context.object, m, parent=parent)


def plane(size, loc=(0, 0, 0), rot=(0, 0, 0), m=None, parent=None, name=None):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.scale = (size[0], size[1], 1) if isinstance(size, (tuple, list)) else (size, size, 1)
    if name:
        ob.name = name
    return _finish(ob, m, smooth=False, parent=parent)


def card(path, height, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), emit=0.0, parent=None, name=None, aspect=None):
    """Upright image card, bottom-centre at loc, facing -Y by default."""
    img = bpy.data.images.load(str(path), check_existing=True)
    a = aspect or img.size[0] / max(1, img.size[1])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    ob = bpy.context.object
    for v in ob.data.vertices:            # pivot at bottom centre
        v.co.y += 0.5
    ob.scale = (height * a, height, 1)
    ob.rotation_euler = rot
    ob.location = loc
    if name:
        ob.name = name
    return _finish(ob, image_mat(path, emit=emit), smooth=False, parent=parent)


_FONTS = {}


def text(body, size=1.0, loc=(0, 0, 0), rot=(math.pi / 2, 0, 0), m=None, extrude=0.05, weight='Heavy',
         align='CENTER', bevel=0.01, parent=None, name=None, spacing=1.0):
    f = _FONTS.get(weight)
    if f is None:
        f = _FONTS[weight] = bpy.data.fonts.load(str(FONT / f'SF-Pro-Text-{weight}.otf'))
    cu = bpy.data.curves.new(name or 'txt', 'FONT')
    cu.body = body
    cu.font = f
    cu.size = size
    cu.extrude = extrude
    cu.bevel_depth = bevel
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.space_character = spacing
    ob = bpy.data.objects.new(name or 'txt', cu)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    if m is not None:
        cu.materials.append(m)
    if parent is not None:
        ob.parent = parent
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    if parent is not None:
        ob.parent = parent
    return ob


def blob(loc, r, strength=0.7, parent=None):
    return plane((r * 2, r * 2), (loc[0], loc[1], loc[2] + 0.004), m=blob_mat(strength), parent=parent)


# ------------------------------------------------------------------ lights
def sun(rot, energy=3.0, color=(1, 0.95, 0.88), angle=8):
    bpy.ops.object.light_add(type='SUN', rotation=rot)
    L = bpy.context.object
    L.data.energy = energy
    L.data.color = color
    L.data.angle = math.radians(angle)
    return L


def point(loc, energy=200, color=(1, 0.9, 0.8), r=0.2):
    bpy.ops.object.light_add(type='POINT', location=loc)
    L = bpy.context.object
    L.data.energy = energy
    L.data.color = color
    L.data.shadow_soft_size = r
    return L


def spot(loc, target, energy=800, color=(1, 1, 1), angle=40, blend=0.4, r=0.15):
    bpy.ops.object.light_add(type='SPOT', location=loc)
    L = bpy.context.object
    L.data.energy = energy
    L.data.color = color
    L.data.spot_size = math.radians(angle)
    L.data.spot_blend = blend
    L.data.shadow_soft_size = r
    aim(L, target)
    return L


def area(loc, target, energy=300, size=2.0, color=(1, 1, 1)):
    bpy.ops.object.light_add(type='AREA', location=loc)
    L = bpy.context.object
    L.data.energy = energy
    L.data.size = size
    L.data.color = color
    aim(L, target)
    return L


def aim(ob, target, roll=0.0):
    d = Vector(target) - ob.location
    q = d.to_track_quat('-Z', 'Y')
    ob.rotation_mode = 'XYZ'
    ob.rotation_euler = (q @ Matrix.Rotation(roll, 4, 'Z').to_quaternion()).to_euler() if roll else q.to_euler()


# ------------------------------------------------------------------ camera & motion
def camera(lens=26, dof=None):
    data = bpy.data.cameras.new('cam')
    data.lens = lens
    data.sensor_fit = 'VERTICAL'
    data.sensor_height = 36
    data.clip_start = 0.02
    data.clip_end = 400
    ob = bpy.data.objects.new('cam', data)
    bpy.context.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    if dof:
        data.dof.use_dof = True
        data.dof.aperture_fstop = dof
    return ob


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = min(1.0, max(0.0, x))
    return x ** 3


def spring(x, f=2.2, z=0.42):
    if x <= 0:
        return 0.0
    return 1 - math.exp(-z * 10 * x) * math.cos(f * 2 * math.pi * x)


def lerp(a, b, x):
    return a + (b - a) * x


def vlerp(a, b, x):
    return Vector(a).lerp(Vector(b), x)


def _cm(p0, p1, p2, p3, u):
    u2, u3 = u * u, u * u * u
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)


def path(t, keys, ease=None):
    """Catmull-Rom through [(time, value-tuple), ...] (C1 continuous camera motion).
    `ease` optionally remaps global progress for a soft start and stop."""
    ts = [k[0] for k in keys]
    if ease is not None and len(keys) > 1:
        x = (t - ts[0]) / (ts[-1] - ts[0])
        t = ts[0] + ease(min(1, max(0, x))) * (ts[-1] - ts[0])
    if t <= ts[0]:
        return Vector(keys[0][1])
    if t >= ts[-1]:
        return Vector(keys[-1][1])
    i = max(k for k in range(len(ts) - 1) if ts[k] <= t)
    u = (t - ts[i]) / (ts[i + 1] - ts[i])
    P = [Vector(keys[max(0, min(len(keys) - 1, j))][1]) for j in (i - 1, i, i + 1, i + 2)]
    return Vector(_cm(*P, u))


def shake(t, amp, freq=7.0, seed=1):
    r = random.Random(seed)
    ph = [r.random() * 6.28 for _ in range(6)]
    return Vector((amp * (math.sin(t * freq + ph[0]) + 0.5 * math.sin(t * freq * 2.3 + ph[1])),
                   amp * (math.sin(t * freq * 1.1 + ph[2]) + 0.5 * math.sin(t * freq * 2.7 + ph[3])),
                   amp * 0.6 * (math.sin(t * freq * 0.9 + ph[4]) + 0.5 * math.sin(t * freq * 2.1 + ph[5]))))


def look(cam, pos, target, roll=0.0, lens=None):
    cam.location = Vector(pos)
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat('-Z', 'Y')
    e = q.to_euler()
    if roll:
        e = (q @ Euler((0, 0, roll)).to_quaternion()).to_euler()
    cam.rotation_euler = e
    if lens:
        cam.data.lens = lens


def project(cam, ob_or_pos, radius=0.0):
    """Screen position in full-res pixels (1080x1920), pixel size of a world radius, depth."""
    sc = bpy.context.scene
    p = ob_or_pos.matrix_world.translation if hasattr(ob_or_pos, 'matrix_world') else Vector(ob_or_pos)
    v = world_to_camera_view(sc, cam, p)
    x, y = v.x * 1080, (1 - v.y) * 1920
    size = 0.0
    if radius:
        up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
        v2 = world_to_camera_view(sc, cam, p + up * radius)
        size = abs(v2.y - v.y) * 1920
    return [round(x, 2), round(y, 2), round(size, 2), round(v.z, 3)]


def scatter(seed, n, xr, yr, zr=(0, 0)):
    r = random.Random(seed)
    return [(r.uniform(*xr), r.uniform(*yr), r.uniform(*zr)) for _ in range(n)]
