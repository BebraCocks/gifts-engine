"""«Низший», книга 1, часть 1 «Пробуждение» — v2 на 15,5 минут (автор 2026-11-27: 12–16 мин, всё по книге,
от лица Оди; детализация кодом в нуарном стиле v1, наполненные локации; из текста — только неброские субтитры).
Сцены идут по CLIPS (script.py); внутри длинных сцен — 2–4 плана со сменой на репликах.
Люди — people.py/figure.py, места — places.py/places2.py, кадр — stage.py.

    python -B projects/63-nizshii-1/render.py --frames 600,3000,9000
    python -B engine/tools/build.py projects/63-nizshii-1 --approved --name nizshii_part1_v2
"""
import functools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import banner  # noqa: E402
import frames  # noqa: E402
import kit  # noqa: E402
import people as pp  # noqa: E402
import figure as fg  # noqa: E402
import places  # noqa: E402
import places2 as p2  # noqa: E402
from stage import (W, H, CW, CH, GREEN, cl, ramp, eo, eio, bump, mid, mouth, blink, plate, sprite, to_pil, actor,  # noqa
                   put, layer, cam, kb, shake, grade, mix, subtitles, hud_text, hud_box, dust, q)
from timeline import S, E, DUR, SCENES, KEYS  # noqa: E402

FPS = 60


def HY(hp, head_y):
    """где поставить стопы, чтобы голова фигуры ростом hp оказалась на высоте head_y холста"""
    return head_y + 0.93 * hp
BR = banner.Breaks([], cy=H / 2)
X = 0.3                                     # длительность мягкой смены сцен
D = {k: E[k] - S[k] for k in KEYS}
ODI_DRY = dict(pp.ODI, dry=1.0)
RED = (255, 90, 80)


# ── плиты ──────────────────────────────────────────────────────────────────
def corr_P(eye=1.65):
    return places.Persp(CW, CH, f=CW * 0.52, vy=CH * 0.45, eye=eye)


def corridor_plate(seed=1, **kw):
    key = f'corr{seed}_' + '_'.join(f'{k}{v}' for k, v in sorted(kw.items()))
    return plate(key, lambda: places.corridor(CW, CH, seed=seed, **kw)[0])


def canvas(pl):
    return pl.convert('RGBA')


def blurred(pl, r=8, dark=0.75):
    key = ('blur', id(pl), r, dark)
    return plate(f'blur_{hash(pl.tobytes()[:4096]) % 10**8}_{r}_{dark}',
                 lambda: Image.eval(pl.filter(ImageFilter.GaussianBlur(r)), lambda v: int(v * dark)))


def darken(img, a, col=(0, 0, 0)):
    if a > 0:
        img.alpha_composite(Image.new('RGBA', img.size, col + (int(255 * cl(a)),)))


def glow(img, x, y, r, col, a):
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse((x - r, y - r, x + r, y + r), fill=col + (int(255 * cl(a)),))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(r * 0.5)))


def flash(img, a, col=(255, 255, 255)):
    darken(img, a, col)


# ── толпа в коридоре ───────────────────────────────────────────────────────
CROWD = [(k, (-1 if k % 2 == 0 else 1), 3.0 + k * 1.05 + (k * 37 % 5) * 0.15) for k in range(16)]


def crowd(img, P, t, mode='lean', seed=0, zmin=2.6, n=16, smile=0.0, exclude=(), walkers=0):
    """жители вдоль стен. mode: lean — привалились к стене, straight — выпрямились «руки в бока», walk — идут"""
    items = []
    for k, side, z in CROWD[:n]:
        if k in exclude or z < zmin:
            continue
        x = side * (2.75 + (k * 13 % 7) * 0.05)
        items.append((z, x, k))
    for w in range(walkers):
        z = 3.0 + ((w * 5.3 + t * (0.9 + 0.2 * (w % 3))) % 26)
        x = (-1.2 + (w % 4) * 0.8)
        items.append((z, x, 100 + w))
    items.sort(key=lambda i: -i[0])
    for z, x, k in items:
        lk = pp.crowd_look(200 + k + seed)
        hpx = 1.72 * P.s(z)
        fx, fy = P.p(x, 0, z)
        fog = 1 - math.exp(-z * 0.05)
        light = dict(key=0.92, fog=round(fog, 2))
        if k >= 100:
            actor(img, f'cw{k}_{seed}', lk, 'walk', fx, fy, hpx, dict(yaw=0.0), t, phase=t * 0.7 + k * 0.3, light=light)
        elif mode == 'straight':
            actor(img, f'cs{k}_{seed}', lk, 'hips', fx, fy, hpx, dict(smile=smile, mouth=0.18 * smile, eye=1.1, yaw=-x * 0.06),
                  t, light=light)
        else:
            actor(img, f'cl{k}_{seed}', lk, 'wall', fx, fy, hpx, dict(yaw=-x * 0.05, eye=0.7), t, light=light,
                  kw=dict(lean=-0.04 * (1 if x > 0 else -1), head_tilt=0.08 * (1 if x > 0 else -1)))


# ── сцены ──────────────────────────────────────────────────────────────────
def sc_dark(t):
    """веки закрыты: тёмно-красная плоть, пульс; зелёные строки «Перечня последних событий»"""
    img = Image.new('RGBA', (CW, CH), (6, 2, 3, 255))
    beat = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 1.1) ** 8
    glow(img, CW / 2, CH * 0.5, 700, (70, 8, 10), 0.35 + 0.25 * beat)
    lines = ['ПЕРЕЧЕНЬ ПОСЛЕДНИХ СОБЫТИЙ:', 'ГИДРАЦИЯ — УСПЕШНО.', 'КОМПЛЕКТАЦИЯ — УСПЕШНО.', 'РЕАНИМАЦИЯ — УСПЕШНО.']
    times = [S['A01'] - 0.3, S['A01'] + 0.2, S['A01'] + 2.5, S['A01'] + 4.9]
    for k, (s, t0) in enumerate(zip(lines, times)):
        a = eo(ramp(t, t0, t0 + 0.35))
        if a > 0:
            jitter = (random.Random(int(t * 30) + k).random() - 0.5) * 4 * (1 - ramp(t, t0, t0 + 0.6))
            hud_text(img, 150 + jitter, CH * 0.36 + k * 110, s, 52 if k else 42, GREEN, a * (0.75 + 0.25 * beat))
    # A02: попытка открыть глаза — полоска света сквозь ресницы
    u = ramp(t, S['A02'] + D['A02'] * 0.55, E['A02'])
    if u > 0:
        h = 40 * eio(u) * (0.6 + 0.4 * math.sin(t * 7))
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle((0, CH * 0.5 - h, CW, CH * 0.5 + h), fill=(220, 240, 235, int(200 * u)))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(30)))
    return kb(img, t, 0, E['A02'], 1.0, 1.08, (CW / 2, CH / 2), (CW / 2, CH * 0.49))


@functools.lru_cache(None)
def floor_plate(seed=4):
    return plate(f'floor{seed}', lambda: p2._finish(kit.from_premul(places.floor_top(CW, CH, seed=seed))))


def odi_lying(img, t, x, y, scale, rot, fc, name='lie', lk=ODI_DRY, arms=None):
    """Оди на спине (вид сверху): кукла в позе стоя, повёрнутая"""
    kw = dict(arms=arms or {'L': (1.75, 1.3), 'R': (1.45, 2.0)}, legs={'L': (1.5, 1.56), 'R': (1.66, 1.62)})
    return actor(img, name, lk, 'stand', x, y, scale, fc, t, kw=kw, rot=rot, shadow=0, light=dict(key=0.95, grad=0.1))


def lamp_pool(img, x, y, rx, ry, k=0.55, base=0.4):
    """нуарное пятно света: всё вне пятна темнеет"""
    m = Image.new('L', (img.width // 4, img.height // 4), int(255 * base))
    ImageDraw.Draw(m).ellipse(((x - rx) / 4, (y - ry) / 4, (x + rx) / 4, (y + ry) / 4), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(rx / 8)).resize(img.size, Image.BILINEAR)
    dark = Image.new('RGBA', img.size, (2, 6, 8, 255))
    dark.putalpha(m.point(lambda v: int((255 - v) * k)))
    img.alpha_composite(dark)


def sc_body(t):
    img = canvas(floor_plate())
    jolt = bump(t, S['A03'] + 0.6, 0.05, 0.5) + bump(t, S['A03'] + D['A03'] * 0.45, 0.05, 0.5)
    pain = 0.7 + 0.3 * math.sin(t * 6)
    head = odi_lying(img, t, CW * 1.1, CH * 0.68, 1550, 60, dict(eye=0.0, pain=pain, mouth=0.1 + 0.15 * jolt, blink=False))
    # пульсирующий локоть
    beat = bump((t * 1.25) % 1.0, 0.0, 0.08, 0.5)
    lamp_pool(img, CW * 0.5, CH * 0.45, CW * 0.55, CH * 0.42)
    dust(img, t, 40, 3, (0, 0, CW, CH), 0.35)
    dx, dy = shake(t, 6 * jolt)
    return kb(img, t, S['A03'] - X, E['A03'] + X, 1.05, 1.22, (CW * 0.5 + dx, CH * 0.45 + dy),
              (CW * 0.5 + dx, CH * 0.34 + dy), (-2, 1))


def sc_yorka_voice(t):
    """крик в правое ухо: лицо Оди крупно (лёжа), смуглая рука трясёт за плечо, тень девушки"""
    img = canvas(floor_plate(5))
    keys = ['A04', 'A06']
    k = 'A04' if t < S['A05'] else 'A06'
    shout = mouth(t, keys)
    jolt = shout * 0.9
    odi_lying(img, t, CW * 0.4 + 3800 * 0.87, CH * 0.36 + 3800 * 0.5, 3800, 60, dict(eye=0.0 if k == 'A04' else 0.12 * blink(t, 0.6), pain=0.9,
                                                          mouth=0.05, blink=False), name='lie_big')
    # её тень и рука
    sh = layer(lambda c: (kit.ellipse(c, CW * 1.02, CH * 0.35, 520, 900, 0.25), kit.fill(c, (0, 0, 0), 0.6)))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(70)))
    hx, hy = CW * 0.86 + 20 * math.sin(t * 22) * jolt, CH * 0.62 + 14 * math.sin(t * 19) * jolt

    def arm(c):
        pts = fg.chain_outline([(CW + 200, hy - 420), (hx + 160, hy - 120), (hx, hy)], [230, 170, 120])
        kit.smooth_path(c, pts)
        kit.fill(c, (255, 255, 255))
    m = np.asarray(layer(arm).getchannel('A'), np.float32) / 255
    img.alpha_composite(to_pil(fg.shade_mask(m, pp.SKIN_DARK, rim=0.9)))
    lamp_pool(img, CW * 0.45, CH * 0.35, CW * 0.6, CH * 0.4, 0.6)
    dx, dy = shake(t, 10 * jolt, 14)
    return kb(img, t, S[k] - X, E[k] + X, 1.0, 1.1, (CW * 0.5 + dx, CH * 0.5 + dy), (CW * 0.52 + dx, CH * 0.46 + dy))


def sc_memory(t):
    """океан памяти пуст: тёмная толща воды, лучи сверху, мелкая сеть утаскивает последнюю рыбёшку во тьму"""
    s, e = S['A05'] - X, E['A05'] + X
    u = ramp(t, s, e)
    img = Image.new('RGBA', (CW, CH), (0, 0, 0, 255))
    g = layer(lambda c: (c.rectangle(0, 0, CW, CH), c.set_source(kit.lin(0, 0, 0, CH, [(0, (30, 70, 80), 1),
                                                                                      (0.5, (8, 24, 32), 1),
                                                                                      (1, (2, 4, 8), 1)])), c.fill()))
    img.alpha_composite(g)
    rays = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(rays)
    for k in range(7):
        x = CW * (0.1 + k * 0.14) + 60 * math.sin(t * 0.3 + k)
        d.polygon([(x - 30, 0), (x + 30, 0), (x + 220, CH), (x - 60, CH)], fill=(160, 220, 220, 22))
    img.alpha_composite(rays.filter(ImageFilter.GaussianBlur(30)))

    def net(c):
        yoff = -CH * 0.9 * eio(ramp(t, s + 2.5, e))
        for k in range(28):
            x = k * CW / 27
            pts = [(x + 30 * math.sin(yy / 200 + t + k), yy + yoff) for yy in np.linspace(CH * 0.25, CH * 0.85, 12)]
            kit.smooth_path(c, pts, closed=False)
            kit.stroke(c, (150, 190, 190), 2.2, 0.35)
        for k in range(14):
            yy = CH * 0.25 + k * CH * 0.6 / 13 + yoff
            pts = [(x, yy + 26 * math.sin(x / 150 + t * 0.8 + k)) for x in np.linspace(0, CW, 14)]
            kit.smooth_path(c, pts, closed=False)
            kit.stroke(c, (150, 190, 190), 2.2, 0.35)
        # рыбёшка в сети
        fx, fy = CW * 0.55 + 40 * math.sin(t * 2), CH * 0.55 + yoff
        kit.ellipse(c, fx, fy, 60, 22, 0.2)
        kit.fill(c, (200, 210, 200), 0.6)
        kit.poly(c, [(fx - 55, fy - 5), (fx - 95, fy - 30), (fx - 95, fy + 25)])
        kit.fill(c, (200, 210, 200), 0.6)
    img.alpha_composite(layer(net))
    dust(img, t, 90, 8, (0, 0, CW, CH), 0.3, 2.5)
    return kb(img, t, s, e, 1.0, 1.15, (CW / 2, CH * 0.45), (CW / 2, CH * 0.6))


@functools.lru_cache(None)
def wall_plate(seed=3, **kw):
    key = f'wall{seed}_' + '_'.join(f'{k}{v}' for k, v in sorted(kw.items()))
    return plate(key, lambda: p2.wall_close(seed=seed, **kw))


def sc_getup(t):
    img = canvas(wall_plate(3))
    if t < S['A08'] - 0.1:                       # A07: на четвереньках, ладонь в мокрый пол
        u = ramp(t, S['A07'], E['A07'])
        y = CH * 1.02
        kw = dict(arms={'R': (math.pi / 2 + 0.35, math.pi / 2 + 0.1), 'L': (math.pi / 2 - 0.5, math.pi / 2 - 1.0)},
                  head_dy=0.25 - 0.2 * u)
        actor(img, 'kneel', ODI_DRY, 'kneel', CW * 0.5, y, 2500, dict(eye=0.25 + 0.4 * u, pain=1.0, gaze=(0, 0.8), yaw=0.1),
              t, kw=kw, light=dict(key=0.95))
        # рука Йорки на плече
        lamp_pool(img, CW * 0.6, CH * 0.35, CW * 0.6, CH * 0.5, 0.55)
        return kb(img, t, S['A07'] - X, E['A07'], 1.15, 1.3, (CW * 0.5, CH * 0.62), (CW * 0.5, CH * 0.55))
    u = ramp(t, S['A08'], S['A08'] + 2.0)
    actor(img, 'yk_side', pp.YORKA, 'stand', CW * 0.9, CH * 1.05, 2300, dict(yaw=-0.45, gaze=(-0.6, 0.2), brow=-0.3), t,
          light=dict(key=0.8, side=-0.5))
    actor(img, 'lean_wall', ODI_DRY, 'wall', CW * 0.42, CH * 1.04, 2600,
          dict(eye=0.7, pain=0.8, gaze=(0, 1.0), yaw=0.05), t, kw=dict(head_tilt=0.12, head_dy=0.1, lean=-0.03),
          light=dict(key=1.0))
    lamp_pool(img, CW * 0.5, CH * 0.3, CW * 0.6, CH * 0.5, 0.5)
    return kb(img, t, S['A08'] - 0.2, E['A08'] + X, 1.2, 1.35, (CW * 0.5, CH * 0.42), (CW * 0.48, CH * 0.5))


def sc_self(t):
    """взгляд вниз по своему телу: торс → шорты → ноги-спички → руки и раздутый локоть"""
    img = canvas(blurred(wall_plate(3), 10, 0.6))
    hp = 6200
    x = CW * 0.5
    clip = (0, 0, CW, CH)
    if t < S['A10']:
        # A09: взгляд скользит от груди к ступням
        u = eio(ramp(t, S['A09'], E['A09']))
        yy = (CH * 0.4 + 0.75 * hp) * (1 - u) + (CH * 0.75) * u
        _big_odi(img, x, yy, hp, t)
        return cam(img, 1.0, CW / 2, CH / 2)
    y = CH + hp * 0.62
    # A10: руки — плечо с кольцевым шрамом, тонкая рука, раздутый синий локоть
    u = eio(ramp(t, S['A10'], E['A10']))
    yy = y - hp * 0.18 + 0 * u
    _big_odi(img, x - hp * 0.13 * (1 - u) - hp * 0.02, yy - hp * 0.1 * u, hp, t)
    beat = bump((t * 1.2) % 1.0, 0, 0.08, 0.5)
    return kb(img, t, S['A10'] - X, E['A10'] + X, 1.0, 1.08, (CW / 2, CH / 2), (CW / 2, CH * 0.52))


def _big_odi(img, x, y, hp, t):
    """огромный Оди: одна запечённая плита (рендерится один раз), сдвигается камерой"""
    spr = sprite('odi_huge', lambda: _render_huge())
    s = hp / HUGE
    sp = spr if s == 1 else spr.resize((int(spr.width * s), int(spr.height * s)), Image.BICUBIC)
    put(img, sp, x, y - sp.height / 2 + hp * 0.02)


HUGE = 4600


def _render_huge():
    j = pp.pose(0, 0, HUGE, 'stand', arms={'L': (math.pi / 2 - 0.22, math.pi / 2 - 0.05),
                                           'R': (math.pi / 2 + 0.22, math.pi / 2 + 0.05)})
    a, (x0, y0) = fg.render(j, ODI_DRY, dict(eye=0.8, gaze=(0, 1), pain=0.5))
    return to_pil(a)


def yorka_mid(img, t, x, y, hp, keys, fc=None, name='yk_mid', kind='stand', light=None, kw=None):
    fc = {**dict(yaw=-0.2, brow=-0.4, gaze=(-0.2, 0.15)), **(fc or {})}
    return actor(img, name, pp.YORKA, kind, x, y, hp, fc, t, talk=keys, light=light or dict(key=1.0, side=0.3), kw=kw)


def sc_yorka_close(t):
    img = canvas(blurred(corridor_plate(5), 9, 0.7))
    if t < S['A12'] - 0.1:                 # A11: она говорит про комплект (пояс вверх)
        yorka_mid(img, t, CW * 0.52, HY(4200, CH * 0.34), 4200, ['A11'], dict(gaze=(-0.1, 0.4)))
        lamp_pool(img, CW * 0.5, CH * 0.3, CW * 0.7, CH * 0.55, 0.45)
        return kb(img, t, S['A11'] - X, E['A11'], 1.0, 1.06, (CW / 2, CH * 0.5), (CW / 2, CH * 0.47))
    # A12: целиком — однорукая, смуглая, антрацитово-чёрные ноги
    u = eio(ramp(t, S['A12'], E['A12']))
    img = canvas(corridor_plate(5))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=3, zmin=5)
    fx, fy = P.p(0.3, 0, 2.0)
    yorka_mid(img, t, fx, fy, 1.72 * P.s(2.0), [], dict(gaze=(-0.2, 0.6), yaw=-0.25), name='yk_full', light=dict(key=1.0))
    return kb(img, t, S['A12'] - 0.2, E['A12'] + X, 1.55, 1.3, (fx, fy - 1.3 * P.s(2.0)), (fx, fy - 0.6 * P.s(2.0)))


def sc_yorka_face(t):
    img = canvas(blurred(corridor_plate(5), 12, 0.6))
    yorka_mid(img, t, CW * 0.5, HY(6800, CH * 0.4), 6800, ['A14'], dict(yaw=-0.15, gaze=(-0.15, 0.3), brow=-0.5), name='yk_face',
              light=dict(key=1.0, side=0.5))
    lamp_pool(img, CW * 0.45, CH * 0.32, CW * 0.55, CH * 0.4, 0.5)
    if t < S['A14']:
        u = ramp(t, S['A13'], E['A13'])          # медленно по шрамам: щека → лоб → глаз → губы
        return kb(img, t, S['A13'] - X, E['A13'], 1.25, 1.4, (CW * 0.47, CH * 0.36), (CW * 0.53, CH * 0.32))
    return kb(img, t, S['A14'] - 0.2, E['A14'] + X, 1.15, 1.05, (CW / 2, CH * 0.4), (CW / 2, CH * 0.45))


def corridor_scene(t, mode='lean', smile=0.0, odi=True, yorka=True, walkers=3, seed=1, odi_fc=None, yk_talk=None,
                   sphere_z=None, lasers=None, odi_x=-0.55, odi_z=1.25):
    img = canvas(corridor_plate(seed))
    P = corr_P()
    crowd(img, P, t, mode, seed=seed, smile=smile, walkers=walkers)
    sp = None
    if sphere_z is not None:
        sx, sy = P.p(0, 5.0 - 0.15, sphere_z)
        r = P.s(sphere_z) * 0.85
        lay = layer(lambda c: places.sphere(c, sx, sy + r * 0.55, r, t))
        img.alpha_composite(lay)
        sp = (sx, sy + r * 0.6, r)
    heads = {}
    if yorka:
        fx, fy = P.p(1.0, 0, 1.6)
        heads['y'] = actor(img, f'yk_c{seed}', pp.YORKA, 'stand', fx, fy, 1.72 * P.s(1.6),
                           dict(yaw=-0.3, gaze=(-0.6, 0), brow=-0.4), t, talk=yk_talk, light=dict(key=1.0))
    if odi:
        fx, fy = P.p(odi_x, 0, odi_z)
        heads['o'] = actor(img, f'odi_c{seed}{mode}', ODI_DRY if t < S['A28'] else pp.ODI,
                           'wall' if mode == 'lean' else 'stand', fx, fy, 1.72 * P.s(odi_z),
                           {**dict(yaw=0.2, eye=0.8, pain=0.7), **(odi_fc or {})}, t, light=dict(key=1.0))
        heads['o_floor'] = (fx, fy)
        heads['o_h'] = 1.72 * P.s(odi_z)
    if lasers and sp:
        lay = layer(lambda c: places.lasers(c, [(sp[0] + dx, sp[1] + 10) for dx in (-30, 0, 30)][:len(lasers)], lasers, 0.85))
        img.alpha_composite(lay)
    dust(img, t, 50, seed, (0, 0, CW, CH), 0.3)
    return img, P, heads


def sc_corridor(t):
    straight = t >= S['A16'] + D['A16'] * 0.42
    img, P, hd = corridor_scene(t, 'straight' if straight else 'lean', smile=1.0 if straight else 0.0,
                                yk_talk=['A17'], walkers=0 if straight else 4, seed=1)
    if S['A16'] + D['A16'] * 0.42 <= t < S['A16'] + D['A16'] * 0.42 + 0.6:
        flash(img, 0.12 * (1 - ramp(t, S['A16'] + D['A16'] * 0.42, S['A16'] + D['A16'] * 0.42 + 0.6)))
    if t < S['A16']:
        return kb(img, t, S['A15'] - X, E['A15'], 1.0, 1.12, (CW / 2, CH * 0.5), (CW / 2, CH * 0.47))
    if t < S['A17']:
        return kb(img, t, S['A16'] - 0.1, E['A16'], 1.12, 1.18, (CW / 2, CH * 0.47), (CW / 2, CH * 0.46))
    return kb(img, t, S['A17'] - 0.1, E['A17'] + X, 1.5, 1.7, (CW * 0.68, CH * 0.38), (CW * 0.66, CH * 0.36))


def sc_smiles(t):
    """медленная панорама по натянутым улыбкам смертельно больных людей"""
    img = canvas(blurred(corridor_plate(2), 6, 0.7))
    u = ramp(t, S['A18'] - X, E['A18'] + X)
    for k, x in enumerate((0.18, 0.5, 0.82)):
        lk = pp.crowd_look(300 + k)
        actor(img, f'sm{k}', lk, 'hips', CW * x, HY(3600, CH * 0.3), 3600,
              dict(smile=1.0, mouth=0.25, eye=1.15, brow=0.6, pain=0.5, yaw=(0.5 - x) * 0.4), t, light=dict(key=0.9))
    lamp_pool(img, CW * 0.5, CH * 0.3, CW * 0.7, CH * 0.5, 0.5)
    return kb(img, t, S['A18'] - X, E['A18'] + X, 1.35, 1.35, (CW * 0.28, CH * 0.33), (CW * 0.72, CH * 0.33))


def sc_number(t):
    """две жирные чёрные единицы на левой грудной мышце; потом — гул над головой, взгляд вверх"""
    img = canvas(blurred(corridor_plate(1), 10, 0.6))
    u = eio(ramp(t, S['A19'], E['A19']))
    hp = 6200
    _big_odi(img, CW * 0.36, 960 + 0.75 * hp + u * 1100, hp, t)
    flick = 0.5 + 0.5 * math.sin(t * 40) if u > 0.75 else 0
    return kb(img, t, S['A19'] - X, E['A19'] + X, 1.25, 1.1, (CW * 0.6, CH * 0.5), (CW * 0.5, CH * 0.35))


def sc_sphere(t):
    """полусфера с двадцатью объективами ползёт по рельсу; лазеры по лицу, по цифрам — и на правом плече штрихкод"""
    z = 9.0 - 5.0 * eio(ramp(t, S['A20'] - X, S['A20'] + 5))
    img = canvas(corridor_plate(1))
    P = corr_P()
    crowd(img, P, t, 'straight', seed=1, smile=1.0, walkers=0)
    sx, sy = P.p(0, 4.85, z)
    r = P.s(z) * 0.85
    img.alpha_composite(layer(lambda c: places.sphere(c, sx, sy + r * 0.55, r, t)))
    fx, fy = P.p(-0.35, 0, 1.3)
    hp = 1.72 * P.s(1.3)
    hd = actor(img, 'odi_scan', ODI_DRY, 'stand', fx, fy, hp, dict(yaw=0.1, eye=1.0, gaze=(0.1, -1), pain=0.6), t,
               light=dict(key=1.0))
    u = ramp(t, S['A20'] + 3.0, E['A20'] - 0.5)
    tx = [(hd[0] + 30 * math.sin(t * 3), hd[1]), (fx + hp * 0.07, fy - hp * 0.72 + u * 0), (fx - hp * 0.13, fy - hp * 0.74)]
    seq = [0, 1, 2]
    k = min(2, int(u * 3))
    if t > S['A20'] + 3.0:
        targets = [tx[k], (tx[k][0] + 18 * math.sin(t * 11), tx[k][1] + 12 * math.cos(t * 9))]
        img.alpha_composite(layer(lambda c: places.lasers(c, [(sx - 30, sy + r * 0.9), (sx + 30, sy + r * 0.9)], targets)))
    if t >= S['A21']:                             # щелчок — и второй в голове
        f = bump(t, S['A21'] + D['A21'] * 0.55, 0.03, 0.4)
        flash(img, 0.5 * f, (200, 255, 220))
    if t < S['A21']:
        return kb(img, t, S['A20'] - X, E['A20'], 1.0, 1.2, (CW / 2, CH * 0.38), (CW * 0.45, CH * 0.45))
    return kb(img, t, S['A21'] - 0.2, E['A21'] + X, 1.2, 1.45, (CW * 0.45, CH * 0.45), (CW * 0.42, CH * 0.42))


def sc_scan(t):
    img = canvas(blurred(corridor_plate(1), 4, 0.8))
    a = eo(ramp(t, S['A22'] - 0.1, S['A22'] + 0.4))
    g = (random.Random(int(t * 25)).random() - 0.5) * 14 * (1 - ramp(t, S['A22'], S['A22'] + 1))
    hud_text(img, 150 + g, CH * 0.44, 'АКТИВАЦИЯ ИНТЕРФЕЙСА —', 44, GREEN, a)
    hud_text(img, 150 - g, CH * 0.44 + 70, 'УСПЕШНО.', 52, GREEN, a)
    hud_text(img, CW - 260, CH * 0.82, 'МЕНЮ', 40, GREEN, a * (0.5 + 0.5 * math.sin(t * 6)))
    return kb(img, t, S['A22'] - X, E['A22'] + X, 1.0, 1.04, (CW / 2, CH / 2), (CW / 2, CH / 2))


def sc_slump(t):
    img = canvas(corridor_plate(2))
    P = corr_P(eye=1.0)
    P = places.Persp(CW, CH, f=CW * 0.52, vy=CH * 0.45, eye=1.65)
    crowd(img, P, t, 'lean', seed=2, walkers=6)
    fx, fy = P.p(-1.9, 0, 2.2)
    if t < S['A25'] - 0.1:
        actor(img, 'slump', ODI_DRY, 'sit_floor', fx, fy, 1.72 * P.s(2.2), dict(eye=0.5, pain=1.0, gaze=(0.3, 0.5)), t,
              light=dict(key=0.9))
    else:
        actor(img, 'slump_up', ODI_DRY, 'wall', fx, fy, 1.72 * P.s(2.2), dict(eye=0.9, brow=-0.3, yaw=0.4, gaze=(0.8, 0)),
              t, light=dict(key=1.0), kw=dict(lean=0.05))
    # ноги прохожих на переднем плане
    for k in range(2):
        ph = (t * 0.35 + k * 0.5) % 1.0
        x = CW * (1.3 - ph * 1.6)
        actor(img, f'pass{k}', pp.crowd_look(400 + k), 'walk', x, CH * 1.45, 2600, dict(), t, phase=t * 0.9 + k,
              light=dict(key=0.7), shadow=0.3)
    if t < S['A24']:
        return kb(img, t, S['A23'] - X, E['A23'], 1.1, 1.25, (CW * 0.4, CH * 0.5), (CW * 0.36, CH * 0.55))
    if t < S['A25']:
        return kb(img, t, S['A24'] - 0.1, E['A24'], 1.25, 1.3, (CW * 0.36, CH * 0.55), (CW * 0.4, CH * 0.53))
    return kb(img, t, S['A25'] - 0.1, E['A25'] + X, 1.2, 1.05, (CW * 0.38, CH * 0.5), (CW * 0.55, CH * 0.45))


@functools.lru_cache(None)
def niche_door_plate():
    def make():
        cv = kit.from_premul(p2.wall_close(seed=12))
        c = cv.ctx
        x0, y0, x1, y1 = CW * 0.32, CH * 0.24, CW * 0.68, CH * 0.775
        c.rectangle(x0, y0, x1 - x0, y1 - y0)
        kit.fill(c, (34, 38, 40))
        c.rectangle(x0, y0, x1 - x0, y1 - y0)
        kit.stroke(c, (60, 235, 120), 16, 0.95)
        c.rectangle(CW / 2 - 50, CH * 0.62, 100, 100)
        kit.fill(c, (6, 8, 10))
        return cv.premul()
    return plate('niche_door', make)


def sc_niche_door(t):
    img = canvas(niche_door_plate())
    u = eio(ramp(t, S['A27'] + 0.6, E['A27'] + 0.5))
    if u > 0:                                    # дверца бесшумно уходит вверх, за ней — свет
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        y0, y1 = CH * 0.24, CH * 0.775
        ImageDraw.Draw(lay).rectangle((CW * 0.32 + 8, y1 - (y1 - y0) * u, CW * 0.68 - 8, y1), fill=(190, 225, 210, 255))
        img.alpha_composite(lay)
        glow(img, CW / 2, CH * 0.6, 400, (180, 255, 220), 0.35 * u)
    actor(img, 'door_odi', ODI_DRY, 'stand', CW * 0.5, CH * 1.55, 3400, dict(back=True), t, light=dict(key=0.6, tint=(0.9, 1.0, 0.95)),
          ) if False else None
    back = dict(ODI_DRY, back=True)
    actor(img, 'door_odi_back', back, 'stand', CW * 0.5, CH * 1.3, 2700, dict(), t, light=dict(key=0.55, grad=0.3))
    if t >= S['A27']:
        hud_text(img, 160, CH * 0.18, 'ОДИННАДЦАТЫЙ. (ОРН).', 42, GREEN, eo(ramp(t, S['A27'], S['A27'] + 0.3)))
    return kb(img, t, S['A26'] - X, E['A27'] + X, 1.0, 1.12, (CW / 2, CH * 0.5), (CW / 2, CH * 0.44))


@functools.lru_cache(None)
def niche_plate():
    return plate('niche_in', lambda: p2.niche_inside())


def sc_niche(t):
    img = canvas(niche_plate())
    # Оди в кресле
    actor(img, 'niche_sit', ODI_DRY if t < S['A29'] else pp.ODI, 'sit_bench', CW * 0.5, CH * 0.95, 1900,
          dict(eye=0.9 if t < S['A29'] else 0.2 + 0.8 * blink(t), pain=0.6, gaze=(0, 0.3)), t,
          kw=dict(arms={'L': (math.pi / 2 - 0.5, 0.2), 'R': (math.pi / 2 + 0.5, math.pi - 0.2)}),
          light=dict(key=1.05, tint=(0.92, 1.0, 0.96)))
    ax, ay = CW * 0.17, CH * 0.6 - 130
    if t < S['A29']:
        u = ramp(t, S['A28'] + 0.8, S['A28'] + 2.0)
        lvl = 1.0 - ramp(t, S['A28'] + 2.8, S['A28'] + 4.4) + ramp(t, S['A28'] + 5.0, S['A28'] + 6.0)
        def cup(c):
            x, y = CW * 0.17 + 0, ay - 120 * u
            c.rectangle(x - 60, y - 190, 120, 190)
            kit.fill(c, (200, 230, 235), 0.35)
            c.rectangle(x - 56, y - 186 * cl(lvl), 112, 186 * cl(lvl))
            kit.fill(c, (120, 190, 210), 0.45)
            c.rectangle(x - 60, y - 190, 120, 190)
            kit.stroke(c, (230, 245, 250), 4, 0.7)
        img.alpha_composite(layer(cup))
        return kb(img, t, S['A28'] - X, E['A28'], 1.6, 1.4, (CW * 0.28, CH * 0.5), (CW * 0.4, CH * 0.45))
    # A29: три огненных тычка в челюсть + отсчёт, кубик из подлокотника
    jabs = [S['A29'] + D['A29'] * f for f in (0.08, 0.2, 0.32)]
    j = sum(bump(t, tj, 0.03, 0.3) for tj in jabs)
    for k, tj in enumerate(jabs):
        if tj - 0.5 < t < tj + 0.8:
            hud_text(img, CW * 0.46, CH * 0.16, str(3 - k), 120, GREEN, 1 - ramp(t, tj + 0.3, tj + 0.8))
    flash(img, 0.35 * j, (255, 140, 60))
    cu = eo(ramp(t, S['A29'] + D['A29'] * 0.6, S['A29'] + D['A29'] * 0.66))
    if cu > 0:
        img.alpha_composite(layer(lambda c: (c.rectangle(CW * 0.83 - 34, ay - 40 - 60 * cu, 68, 68),
                                             kit.fill(c, (190, 176, 130)))))
    dx, dy = shake(t, 10 * j, 16)
    return kb(img, t, S['A29'] - 0.2, E['A29'] + X, 1.25, 1.15, (CW / 2 + dx, CH * 0.42 + dy), (CW / 2 + dx, CH * 0.45 + dy))


def sc_cube(t):
    img = canvas(corridor_plate(2))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=4, walkers=4, zmin=4)
    fx, fy = P.p(-1.6, 0, 2.0)
    actor(img, 'cube_odi', pp.ODI, 'sit_floor', fx, fy, 1.72 * P.s(2.0), dict(eye=1.0, yaw=0.3, gaze=(0.6, -0.4), smile=0.3),
          t, light=dict(key=1.0))
    gx, gy = P.p(-0.4, 0, 1.6)
    yorka_mid(img, t, gx, gy, 1.72 * P.s(1.6), ['A31'], dict(yaw=0.35, gaze=(0.6, 0.5)), name='yk_cube', kind='kneel')
    if t < S['A31']:
        return kb(img, t, S['A30'] - X, E['A30'], 1.2, 1.35, (CW * 0.42, CH * 0.5), (CW * 0.45, CH * 0.52))
    return kb(img, t, S['A31'] - 0.2, E['A31'] + X, 1.5, 1.6, (CW * 0.55, CH * 0.45), (CW * 0.56, CH * 0.44))


def two_shot(t, keys_y, odi_keys=(), seed=4, yk_fc=None, odi_fc=None, cut=None):
    """Оди сидит у стены, Йорка присела рядом и говорит"""
    img = canvas(corridor_plate(seed))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=seed, walkers=3, zmin=5)
    fx, fy = P.p(-1.7, 0, 2.0)
    od = actor(img, f'ts_odi{seed}', pp.ODI, 'sit_floor', fx, fy, 1.72 * P.s(2.0),
               {**dict(eye=1.0, yaw=0.35, gaze=(0.7, -0.3)), **(odi_fc or {})}, t, talk=list(odi_keys), light=dict(key=1.0))
    gx, gy = P.p(-0.55, 0, 1.75)
    yk = yorka_mid(img, t, gx, gy, 1.72 * P.s(1.75), keys_y, {**dict(yaw=0.35, gaze=(0.7, 0.4)), **(yk_fc or {})},
                   name=f'yk_ts{seed}', kind='kneel')
    return img, od, yk


def sc_yorka_talk(t):
    keys = ['A32', 'A33', 'A34', 'A35', 'A41']
    img, od, yk = two_shot(t, ['A32', 'A34', 'A41'], ['A35'], seed=4,
                           odi_fc=dict(pain=0.8) if S['A35'] <= t < E['A35'] + 0.5 else None)
    cur = next((k for k in keys if S[k] - 0.3 <= t < E[k] + 0.45), keys[-1])
    if cur in ('A32', 'A34', 'A41'):
        return kb(img, t, S[cur] - 0.3, E[cur] + 0.4, 1.9, 2.05, (yk[0], yk[1] + 240), (yk[0], yk[1] + 220))
    if cur == 'A33':                         # её культя: «сол за пустоту»
        return kb(img, t, S[cur] - 0.3, E[cur] + 0.4, 1.6, 1.8, (yk[0] - 60, yk[1] + 380), (yk[0] - 40, yk[1] + 360))
    return kb(img, t, S[cur] - 0.3, E[cur] + 0.4, 1.9, 2.0, (od[0], od[1] + 260), (od[0], od[1] + 240))


def sc_slap(t):
    img, od, yk = two_shot(t, ['A36'], [], seed=6, yk_fc=dict(brow=-1.0, pain=0.0))
    hits = [S['A36'] + D['A36'] * 0.92, S['A37'] + D['A37'] * 0.42]
    hit = sum(bump(t, h, 0.02, 0.35) for h in hits)
    if hit > 0:
        flash(img, 0.25 * hit, (255, 230, 220))
        glow(img, od[0] - 50, od[1] + 30, 90, (220, 40, 40), 0.35 * hit)
    dx, dy = shake(t, 22 * hit, 18)
    if t < S['A37']:
        return kb(img, t, S['A36'] - X, E['A36'] + 0.3, 1.7, 1.9, (yk[0] + dx, yk[1] + 240 + dy), (od[0] + 200 + dx, od[1] + 250 + dy))
    return kb(img, t, S['A37'] - 0.1, E['A37'] + X, 2.0, 2.2, (od[0] + dx, od[1] + 240 + dy), (od[0] + dx, od[1] + 220 + dy))


def sc_elbow(t):
    """локоть-помидор сгибается — боль сквозь обезболивающее; её холодное «рука работает»"""
    if t < S['A40'] - 0.1:
        img = canvas(blurred(corridor_plate(4), 12, 0.55))
        bend = eio(ramp(t, S['A39'], S['A39'] + 1.8)) * (1 - ramp(t, E['A39'], E['A39'] + 0.6))
        kw = dict(arms={'L': (math.pi / 2 - 0.25, math.pi / 2 - 0.25 - 1.1 * bend)})
        actor(img, f'elbow_{int(bend * 6)}', pp.ODI, 'stand', CW * 0.32, CH * 2.9, 6000, dict(eye=1.0 - 0.7 * bend,
              pain=0.4 + 0.6 * bend, mouth=0.25 * bend, blink=False), t, kw=kw, light=dict(key=1.0, side=0.3))
        if bend > 0.2:
            darken(img, 0.25 * bend, (120, 0, 10))
        dx, dy = shake(t, 6 * bend, 13)
        return kb(img, t, S['A38'] - X, E['A39'] + 0.3, 1.05, 1.12, (CW * 0.62 + dx, CH * 0.45 + dy), (CW * 0.62 + dx, CH * 0.48 + dy))
    img = canvas(blurred(corridor_plate(5), 12, 0.6))
    yorka_mid(img, t, CW * 0.5, HY(6800, CH * 0.4), 6800, ['A40'], dict(yaw=-0.05, brow=-0.8, gaze=(0, 0.5)), name='yk_cold',
              light=dict(key=0.9, side=0.6))
    lamp_pool(img, CW * 0.5, CH * 0.3, CW * 0.5, CH * 0.4, 0.55)
    return kb(img, t, S['A40'] - 0.2, E['A40'] + X, 1.15, 1.25, (CW / 2, CH * 0.42), (CW / 2, CH * 0.38))


def sc_party(t):
    img = canvas(corridor_plate(7))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=7, walkers=3, zmin=5)
    fx, fy = P.p(-1.4, 0, 2.0)
    od = actor(img, 'pt_odi', pp.ODI, 'sit_floor', fx, fy, 1.72 * P.s(2.0), dict(eye=1.0, yaw=0.4, gaze=(0.7, -0.9), smile=0.4),
               t, talk=['A42', 'A44'], light=dict(key=1.0))
    gx, gy = P.p(-0.2, 0, 1.9)
    yk = yorka_mid(img, t, gx, gy, 1.72 * P.s(1.9), ['A43'], dict(yaw=0.4, gaze=(0.7, 0.7), smile=0.5 if t > S['A43'] else 0),
                   name='yk_pt', kind='stand')
    cur = 'A42' if t < S['A43'] else ('A43' if t < S['A44'] else 'A44')
    tgt = yk if cur == 'A43' else od
    return kb(img, t, S[cur] - 0.3, E[cur] + 0.4, 1.6, 1.75, (tgt[0], tgt[1] + 300), (tgt[0], tgt[1] + 280))


def sc_leave(t):
    img = canvas(corridor_plate(7))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=7, walkers=4, zmin=4)
    u = ramp(t, S['A45'] - X, E['A45'] + X)
    z = 2.0 + 9 * u
    fx, fy = P.p(0.2 + 0.4 * u, 0, z)
    actor(img, 'yk_back', dict(pp.YORKA, back=True), 'walk', fx, fy, 1.72 * P.s(z), dict(), t, phase=t * 0.9,
          light=dict(key=0.9, fog=round(1 - math.exp(-z * 0.05), 1)))
    return kb(img, t, S['A45'] - X, E['A45'] + X, 1.2, 1.35, (CW / 2, CH * 0.48), (CW / 2, CH * 0.45))


def sc_menu(t):
    """зелёное «МЕНЮ» на краю зрения: статус, физ. состояние, финансы, задания"""
    img = canvas(blurred(corridor_plate(4), 10, 0.55))
    s = S['A46']
    rows = [(S['A46'] + 0.0, 'МЕНЮ', GREEN, 46), (S['A46'] + 1.2, 'СТАТУС: ОДИННАДЦАТЫЙ', GREEN, 34),
            (S['A46'] + 2.4, 'РАНГ: НИЗШИЙ (ДОБРОВОЛЬНЫЙ)', GREEN, 34),
            (S['A46'] + D['A46'] * 0.62, 'ЛВК: НЕДОСТУПНО ДЛЯ РАНГА «НИЗШИЙ»', RED, 30),
            (S['A47'] + 0.2, 'БАЛАНС: 0', GREEN, 34), (S['A47'] + 1.2, 'ДОЛГ: 8 СОЛОВ', RED, 40),
            (S['A48'] + 0.2, 'ЗАДАНИЕ: СБОР СЕРОЙ СЛИЗИ', GREEN, 34), (S['A48'] + 1.6, '40 ЁМКОСТЕЙ · ЗОНА 3, БЛОК 6', GREEN, 32),
            (S['A48'] + 3.0, 'НАГРАДА: 15 СОЛОВ', GREEN, 34)]
    a0 = eo(ramp(t, s - 0.2, s + 0.4)) * (0.88 + 0.12 * math.sin(t * 13))
    hud_box(img, 110, int(CH * 0.2), CW - 110, int(CH * 0.2 + 120 + 92 * 8), a0)
    for k, (t0, txt, col, size) in enumerate(rows):
        a = eo(ramp(t, t0, t0 + 0.3))
        if a > 0:
            hud_text(img, 160, CH * 0.2 + 60 + k * 92, txt, size, col, a * a0)
    return kb(img, t, s - X, E['A48'] + X, 1.0, 1.05, (CW / 2, CH * 0.5), (CW / 2, CH * 0.47))


def sc_odin(t):
    img = canvas(blurred(corridor_plate(4), 9, 0.6))
    rise = eio(ramp(t, S['A49'], E['A49']))
    actor(img, 'odin', pp.ODI, 'stand', CW * 0.5, HY(6400, CH * 0.4), 6400, dict(eye=1.0, brow=-0.6, gaze=(0, -0.1), smile=0.25 * rise),
          t, light=dict(key=0.9 + 0.3 * rise, side=0.3), kw=dict(head_tilt=-0.03))
    glow(img, CW / 2, CH * (0.75 - 0.25 * rise), 600, (255, 200, 140), 0.18 * rise)
    return kb(img, t, S['A49'] - X, E['A49'] + 0.6, 1.0, 1.25, (CW / 2, CH * 0.48), (CW / 2, CH * 0.36))


@functools.lru_cache(None)
def screen_plate():
    def make():
        arr, box = p2.screen_wall()
        return arr
    return plate('screen_wall', make)


SCR = (CW * 0.12, CH * 0.2, CW * 0.88, CH * 0.52)


def screen_content(img, t, mode):
    x0, y0, x1, y1 = SCR
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle((x0, y0, x1, y1), fill=(196, 180, 120, 255))
    for k in range(int(y0), int(y1), 5):
        d.line((x0, k, x1, k), fill=(150, 136, 90, 60))
    img.alpha_composite(lay)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if mode == 'call':
        left = max(0, 59 - int(t - S['A50']))
        hud_text(img, cx, cy - 120, '11', 240, (40, 34, 24), 1, 'mm', False)
        hud_text(img, cx, cy + 110, 'ИГРОВОЙ ВЫЗОВ!', 64, (60, 40, 24), 1, 'mm', False)
        hud_text(img, cx, cy + 210, f'00:{left:02d}', 56, (120, 30, 20), 1, 'mm', False)
    elif mode == 'game':
        u = ramp(t, S['A54'] + 1.0, E['A54'] - 0.5)
        g = (x1 - x0) * 0.6
        gx, gy = cx - g / 2, cy - g / 2
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for k in (1, 2):
            d.line((gx + g * k / 3, gy, gx + g * k / 3, gy + g), fill=(40, 34, 24, 255), width=8)
            d.line((gx, gy + g * k / 3, gx + g, gy + g * k / 3), fill=(40, 34, 24, 255), width=8)
        moves = [(1, 1, 'X'), (0, 1, 'O'), (2, 0, 'X'), (0, 2, 'O'), (0, 0, 'X'), (2, 2, 'O'), (1, 0, 'X')]
        rnd = int(u * 3) % 3
        n = int((u * 3 % 1) * 8)
        for k, (i, jj, m) in enumerate(moves[:n]):
            px, py = gx + g * (i + 0.5) / 3, gy + g * (jj + 0.5) / 3
            r = g / 9
            if m == 'X':
                d.line((px - r, py - r, px + r, py + r), fill=(200, 30, 30, 255), width=12)
                d.line((px - r, py + r, px + r, py - r), fill=(200, 30, 30, 255), width=12)
            else:
                d.ellipse((px - r, py - r, px + r, py + r), outline=(40, 34, 24, 255), width=10)
        img.alpha_composite(lay)
        hud_text(img, cx, y0 + 60, f'РАУНД {rnd + 1} / 3', 44, (60, 40, 24), 1, 'mm', False)
    elif mode == 'win':
        hud_text(img, cx, cy - 60, 'ПОБЕДА!', 110, (150, 110, 20), 1, 'mm', False)
        hud_text(img, cx, cy + 110, '11', 160, (200, 150, 30), 1, 'mm', False)


def sc_screen(t):
    img = canvas(screen_plate())
    on = eo(ramp(t, S['A50'] - 0.1, S['A50'] + 0.15))
    if on > 0:
        screen_content(img, t, 'call')
        glow(img, CW / 2, CH * 0.36, 650, (220, 200, 120), 0.18 * on)
    P = corr_P()
    for k, x in enumerate((-0.9, 0.2, 1.1, -0.2, 0.8)):          # затылки толпы перед экраном
        z = 1.6 + (k % 3) * 0.5
        fx, fy = P.p(x, 0, z)
        actor(img, f'scr_back{k}', dict(pp.crowd_look(500 + k), back=True), 'stand', fx, fy + 60, 1.72 * P.s(z), dict(), t,
              light=dict(key=0.6, grad=0.3))
    if t < S['A51']:
        return kb(img, t, S['A50'] - X, E['A50'], 1.05, 1.1, (CW / 2, CH * 0.42), (CW / 2, CH * 0.4))
    return kb(img, t, S['A51'] - 0.2, E['A51'] + X, 1.1, 1.25, (CW / 2, CH * 0.4), (CW / 2, CH * 0.38))


def sc_push(t):
    img = canvas(screen_plate())
    screen_content(img, t, 'call')
    P = corr_P()
    push = bump(t, S['A52'] + D['A52'] * 0.22, 0.08, 0.7)
    tx, ty = P.p(-0.2 + 0.5 * push, 0, 1.5)
    od = actor(img, 'push_odi', pp.ODI, 'reach' if t > S['A52'] + D['A52'] * 0.6 else 'stand', tx, ty, 1.72 * P.s(1.5),
               dict(yaw=0.4, gaze=(0.9, 0), brow=-0.6, pain=0.2 + 0.6 * push), t, light=dict(key=1.0))
    bx, by = P.p(1.25 - 0.4 * push + 0.6 * ramp(t, S['A53'] + 1.5, E['A53']), 0, 1.7 + 2 * ramp(t, S['A53'] + 1.5, E['A53']))
    look_up = S['A53'] <= t < S['A53'] + 1.6
    actor(img, 'b58', pp.B58, 'stand', bx, by, 1.8 * P.s(1.7), dict(yaw=-0.4, gaze=(-0.8, -1 if look_up else 0),
                                                                     brow=-0.8, pain=0.3 if look_up else 0), t,
          light=dict(key=0.9, side=-0.4))
    dx, dy = shake(t, 18 * push, 15)
    if t < S['A53']:
        return kb(img, t, S['A52'] - X, E['A52'], 1.35, 1.45, (CW * 0.55 + dx, CH * 0.5 + dy), (CW * 0.5 + dx, CH * 0.48 + dy))
    return kb(img, t, S['A53'] - 0.2, E['A53'] + X, 1.5, 1.3, (CW * 0.62, CH * 0.42), (CW * 0.55, CH * 0.45))


def sc_game(t):
    img = canvas(screen_plate())
    win = t > S['A54'] + D['A54'] * 0.88
    screen_content(img, t, 'win' if win or t >= S['A55'] else 'game')
    glow(img, CW / 2, CH * 0.36, 650, (220, 200, 120), 0.18)
    if t >= S['A55']:
        a = eo(ramp(t, S['A55'] + 0.4, S['A55'] + 0.8))
        hud_text(img, 170, CH * 0.62, '+3 СОЛА', 54, GREEN, a)
        b = eo(ramp(t, S['A55'] + 1.8, S['A55'] + 2.2))
        hud_text(img, 170, CH * 0.62 + 80, '→ В СЧЁТ ДОЛГА. ДОЛГ: 5', 40, RED, b)
    return kb(img, t, S['A54'] - X, E['A55'] + X, 1.15, 1.25, (CW / 2, CH * 0.4), (CW / 2, CH * 0.43))


def sc_lame(t):
    img = canvas(corridor_plate(9))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=9, walkers=3, zmin=5)
    u = ramp(t, S['A56'] - X, E['A57'] + X)
    fx, fy = P.p(0.6 - 0.2 * u, 0, 2.6 - 0.6 * u)
    wm = actor(img, 'lame', pp.LAME, 'walk', fx, fy, 1.68 * P.s(2.6 - 0.6 * u), dict(yaw=-0.3, eye=0.7, gaze=(-0.4, 0.3)),
               t, talk=['A56', 'A57'], phase=t * 0.6, light=dict(key=0.95), kw=dict(legs={'L': (math.pi / 2 - 0.05, math.pi / 2)}))
    ox, oy = P.p(-0.6, 0, 2.2 - 0.4 * u)
    actor(img, 'lame_odi', pp.ODI, 'walk', ox, oy, 1.72 * P.s(2.2 - 0.4 * u), dict(yaw=0.3, gaze=(0.7, 0)), t, phase=t * 0.5,
          light=dict(key=1.0))
    return kb(img, t, S['A56'] - X, E['A57'] + X, 1.45, 1.6, (wm[0] - 100, wm[1] + 300), (wm[0] - 120, wm[1] + 320))


def sc_walk(t):
    img = canvas(corridor_plate(10))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=10, walkers=5, zmin=3)
    fx, fy = P.p(-1.0, 0, 2.0)
    actor(img, 'walk_odi', pp.ODI, 'walk', fx, fy, 1.72 * P.s(2.0), dict(yaw=0.3, eye=0.8, gaze=(0.3, 0.6), mouth=0.0), t,
          talk=None, phase=t * 0.45, light=dict(key=1.0), kw=dict(arms={'R': (math.pi / 2 + 0.9, math.pi / 2 + 1.2)}))
    return kb(img, t, S['A58'] - X, E['A58'] + X, 1.25, 1.4, (CW * 0.35, CH * 0.47), (CW * 0.4, CH * 0.5))


@functools.lru_cache(None)
def ring_plate():
    return plate('ring', lambda: p2.ring()[0])


def ring_P():
    return places.Persp(CW, CH, f=CW * 0.55, vy=CH * 0.44, eye=1.6)


@functools.lru_cache(64)
def bucket_spr(level=1.0, slime=True, s=1.0):
    return layer(lambda c: p2.bucket(c, 200, 330, 300 * s, level, slime), (400, 400))


def workers(img, P, t, n=7, seed=0, bend=0.012):
    for w in range(n):
        z = 2.5 + ((w * 4.1 + t * (0.6 + 0.15 * (w % 3)) * (1 if w % 2 else -1)) % 22)
        x = (-1.6 + (w * 0.9) % 3.2) + bend * z * z
        lk = [pp.STRONGW, pp.GREYMAN][w % 2] if w < 2 else pp.crowd_look(600 + w + seed)
        fx, fy = P.p(x, 0, z)
        hp = 1.72 * P.s(z)
        actor(img, f'wk{w}{seed}', lk, 'carry', fx, fy, hp, dict(pain=0.6, eye=0.6), t, phase=t * 0.8 + w,
              light=dict(key=0.85, fog=round(1 - math.exp(-z * 0.06), 1)))
        put(img, bucket_spr(1.0), fx - hp * 0.16, fy - hp * 0.2, scale=hp / 1400)


def sc_ring(t):
    img = canvas(ring_plate())
    P = ring_P()
    workers(img, P, t, 8, 1)
    for k in range(2):                            # две маленькие полусферы наматывают круги
        z = (6 + t * 1.2 + k * 11) % 26 + 3
        sx, sy = P.p(-0.6 + k * 1.5 + 0.012 * z * z, 3.45, z)
        r = P.s(z) * 0.35
        img.alpha_composite(layer(lambda c: places.sphere(c, sx, sy + r * 0.5, r, t)))
    fall = bump(t, S['A59'] + D['A59'] * 0.6, 0.1, 1.2)
    return kb(img, t, S['A59'] - X, E['A59'] + X, 1.0, 1.15, (CW / 2, CH * 0.48), (CW * 0.55, CH * 0.5))


@functools.lru_cache(None)
def tooth_plate():
    return plate('tooth', lambda: p2.tooth_room()[0])


def sc_tooth(t):
    img = canvas(tooth_plate())
    img.alpha_composite(layer(lambda c: p2.slime_tongues(c, CW, CH * 0.6, t, 3, 11, 0, length=0.7)))
    P = places.Persp(CW, CH, f=CW * 0.6, vy=CH * 0.42, eye=1.6)
    for k, (x, z) in enumerate(((-1.4, 3.6), (1.2, 3.0), (0.2, 4.4))):
        fx, fy = P.p(x, 0, z)
        hp = 1.72 * P.s(z)
        actor(img, f'scoop{k}', pp.crowd_look(700 + k), 'kneel', fx, fy, hp, dict(eye=0.6, gaze=(0, 1)), t,
              kw=dict(arms={'L': (math.pi / 2 - 0.2, math.pi / 2 + 0.3), 'R': (math.pi / 2 + 0.2, math.pi / 2 - 0.3)}),
              light=dict(key=0.9))
        put(img, bucket_spr(0.6), fx + hp * 0.2, fy - hp * 0.05, scale=hp / 1300)
    dust(img, t, 30, 5, (0, 0, CW, CH), 0.2)
    return kb(img, t, S['A60'] - X, E['A60'] + X, 1.0, 1.15, (CW / 2, CH * 0.4), (CW / 2, CH * 0.5))


@functools.lru_cache(None)
def recv_plate():
    return plate('recv', lambda: p2.receiver())


def sc_conveyor(t):
    img = canvas(recv_plate())
    # лента едет: вёдра уезжают влево
    for k in range(5):
        x = (CW * 0.78 - ((t * 140 + k * 260) % (CW * 0.9)))
        put(img, bucket_spr(1.0), x, CH * 0.6 - 150, scale=0.9)
    # чистые вёдра в окошке
    for k in range(3):
        put(img, bucket_spr(0.0, False), CW * 0.86 + k * 70, CH * 0.6 - 130, scale=0.6)
    P = places.Persp(CW, CH, f=CW * 0.6, vy=CH * 0.42, eye=1.6)
    ph = (t * 0.25) % 1.0
    fx, fy = CW * (0.95 - ph * 0.8), CH * 1.05
    actor(img, 'conv_w', pp.STRONGW, 'carry', fx, fy, 2100, dict(eye=0.7), t, phase=t * 0.8, light=dict(key=0.9))
    put(img, bucket_spr(1.0), fx - 330, fy - 420, scale=1.5)
    lamp_pool(img, CW * 0.45, CH * 0.5, CW * 0.7, CH * 0.4, 0.45)
    return kb(img, t, S['A61'] - X, E['A61'] + X, 1.0, 1.1, (CW / 2, CH * 0.5), (CW * 0.55, CH * 0.48))


def sc_laugh(t):
    img = canvas(blurred(ring_plate(), 6, 0.6))
    lg = 0.5 + 0.5 * math.sin(t * 14)
    actor(img, 'laugh', pp.ODI, 'sit_floor', CW * 0.5, CH * 1.15, 3200,
          dict(eye=0.2, smile=1.0, mouth=q(0.35 + 0.35 * lg, 4), brow=0.5, blink=False), t,
          kw=dict(arms={'R': (math.pi / 2 + 1.9, -0.6)}, head_tilt=0.12 * math.sin(t * 7)), light=dict(key=1.0))
    return kb(img, t, S['A62'] - X, E['A62'] + X, 1.3, 1.45, (CW / 2, CH * 0.45), (CW / 2, CH * 0.42))


def sc_bucket(t):
    img = canvas(tooth_plate())
    img.alpha_composite(layer(lambda c: p2.slime_tongues(c, CW, CH * 0.55, t, 4, 9, 0, length=0.75)))
    u = ramp(t, S['A63'] + D['A63'] * 0.35, S['A63'] + D['A63'] * 0.6)
    fx, fy = CW * 0.5, CH * 1.1
    kind = 'kneel' if u < 0.5 else 'carry'
    actor(img, f'bk_{kind}', pp.ODI, kind, fx, fy, 2600, dict(pain=0.5 + 0.5 * u, eye=0.6, mouth=0.2 * u, gaze=(0, 0.6)), t,
          light=dict(key=1.0))
    lvl = q(ramp(t, S['A63'] + 0.4, S['A63'] + D['A63'] * 0.3), 8)
    put(img, bucket_spr(lvl), fx + (-260 if kind == 'carry' else 300), fy - (560 if kind == 'carry' else 160), scale=1.6)
    shm = bump(t, S['A63'] + 0.4, 0.03, 0.3) + bump(t, S['A63'] + 1.0, 0.03, 0.3)
    dx, dy = shake(t, 8 * shm)
    return kb(img, t, S['A63'] - X, E['A63'] + X, 1.15, 1.25, (CW / 2 + dx, CH * 0.55 + dy), (CW / 2, CH * 0.5))


def bars_and_buksa(img, P, t, x=0.5, z=2.2, talk_b=(), talk_k=(), b_fc=None, k_fc=None, finger=False):
    fx, fy = P.p(x, 0, z)
    bh = actor(img, 'bars', pp.BARS, 'stand', fx, fy, 1.76 * P.s(z), {**dict(yaw=-0.3, gaze=(-0.6, 0), brow=-0.6), **(b_fc or {})},
               t, talk=list(talk_b), light=dict(key=1.0, side=-0.3))
    gx, gy = P.p(x + 0.75, 0, z + 0.3)
    kw = dict(arms={'R': (math.pi / 2 + 2.3, -1.6)}) if finger else {}
    lk = dict(pp.BUKSA, hand_R='middle') if finger else pp.BUKSA
    kh = actor(img, 'buksa' + ('_f' if finger else ''), lk, 'stand', gx, gy, 1.62 * P.s(z + 0.3),
               {**dict(yaw=-0.4, gaze=(-0.6, 0), smile=0.6), **(k_fc or {})}, t, talk=list(talk_k),
               light=dict(key=1.0), kw=kw)
    return bh, kh


def sc_kick(t):
    img = canvas(ring_plate())
    P = ring_P()
    workers(img, P, t, 4, 2)
    kick = S['A64'] + 0.15
    k = ramp(t, kick, kick + 0.5)
    bx, by = P.p(-0.4, 0, 2.4)
    if k < 0.01:
        put(img, bucket_spr(1.0), bx, by - 120, scale=1.0)
    else:
        put(img, bucket_spr(0.2), bx - 200 * k, by - 90, scale=1.0, rot=80 * eo(k))
        img.alpha_composite(layer(lambda c: [(kit.ellipse(c, bx - 120 - 260 * k + j * 40, by - 20 + (j % 3) * 18,
                                                          90 * k + 20, 22 * k + 6), kit.fill(c, (140, 142, 134), 0.85))
                                             for j in range(6)]))
    bars_and_buksa(img, P, t, x=0.2, z=2.6, k_fc=dict(mouth=0.5 * bump(t, kick + 0.2, 0.05, 1.5), smile=1.0))
    dx, dy = shake(t, 14 * bump(t, kick, 0.03, 0.4))
    return kb(img, t, S['A64'] - X, E['A64'] + X, 1.25, 1.35, (CW * 0.5 + dx, CH * 0.5 + dy), (CW * 0.52, CH * 0.48))


def sc_bars(t):
    img = canvas(ring_plate())
    P = ring_P()
    workers(img, P, t, 4, 3)
    look_up = S['A65'] + D['A65'] * 0.7 <= t < E['A65']
    finger = t >= S['A68']
    bh, kh = bars_and_buksa(img, P, t, x=0.1, z=2.3, talk_b=['A67'], b_fc=dict(gaze=(-0.5, -1 if look_up else 0)),
                            k_fc=dict(mouth=0.5 if finger else 0.0), finger=finger)
    if t < S['A66']:
        return kb(img, t, S['A65'] - X, E['A65'], 1.7, 1.6, (bh[0], bh[1] + 420), (bh[0], bh[1] + 260))
    if t < S['A67']:
        ox, oy = P.p(-1.0, 0, 1.6)
        od = actor(img, 'bars_odi', pp.ODI, 'stand', ox, oy, 1.72 * P.s(1.6), dict(yaw=0.45, smile=0.5, gaze=(0.8, 0)), t,
                   talk=['A66'], light=dict(key=1.0))
        return kb(img, t, S['A66'] - 0.2, E['A66'] + 0.2, 1.7, 1.75, (od[0] + 100, od[1] + 300), (od[0] + 100, od[1] + 290))
    if t < S['A68']:
        return kb(img, t, S['A67'] - 0.2, E['A67'] + 0.3, 1.9, 2.0, (bh[0], bh[1] + 260), (bh[0], bh[1] + 250))
    return kb(img, t, S['A68'] - 0.2, E['A68'] + X, 1.4, 1.3, (kh[0] - 100, kh[1] + 420), (kh[0] - 160, kh[1] + 400))


def sc_colossus(t):
    """колосс на глиняных ногах: свет на мощном торсе, затем вниз — на ноги-спички"""
    img = canvas(blurred(ring_plate(), 8, 0.45))
    u = eio(ramp(t, S['A69'], E['A69']))
    _big_odi(img, CW * 0.5, CH * 1.45 - u * 2500, 6200, t)
    glow(img, CW * 0.5, CH * (0.45 - 0.0 * u), 700, (255, 210, 160), 0.15 * (1 - u))
    return cam(img, 1.0, CW / 2, CH / 2)


def sc_trip(t):
    img = canvas(ring_plate())
    P = ring_P()
    workers(img, P, t, 5, 4)
    trip = S['A70'] + D['A70'] * 0.6
    fall = eo(ramp(t, trip, trip + 0.5))
    ox, oy = P.p(-0.3, 0, 2.0)
    if fall < 0.5:
        actor(img, 'trip_odi', pp.ODI, 'carry', ox, oy, 1.72 * P.s(2.2), dict(pain=0.6), t, phase=t * 0.4, light=dict(key=1.0))
    else:
        actor(img, 'trip_fall', pp.ODI, 'sit_floor', ox, oy, 1.72 * P.s(2.2), dict(pain=1.0, eye=0.3, mouth=0.3), t,
              light=dict(key=1.0), rot=-8)
    bh, kh = bars_and_buksa(img, P, t, x=0.6, z=2.8, talk_k=['A71'], k_fc=dict(smile=1.0))
    if t >= S['A71']:
        return kb(img, t, S['A71'] - 0.2, E['A71'] + X, 1.7, 1.8, (kh[0], kh[1] + 300), (kh[0], kh[1] + 280))
    dx, dy = shake(t, 16 * bump(t, trip + 0.4, 0.03, 0.4))
    return kb(img, t, S['A70'] - X, E['A70'], 1.2, 1.3, (CW * 0.45 + dx, CH * 0.5 + dy), (CW * 0.48, CH * 0.52))


def sc_count(t):
    img = canvas(recv_plate())
    if t < S['A73']:                                 # счёт: ведро — двадцать минут; три в час; сорок не успеть
        darken(img, 0.35)
        u = ramp(t, S['A72'], E['A72'])
        n = min(40, int(u * 46))
        for k in range(40):
            x = 140 + (k % 8) * 130
            y = CH * 0.3 + (k // 8) * 170
            spr = bucket_spr(1.0 if k < n else 0.0, k < n, 0.45)
            put(img, spr, x, y, a=1.0 if k < n else 0.25, scale=1.0)
        hud_text(img, CW / 2, CH * 0.2, f'{min(n, 3) if u < 0.5 else min(n, 30)} / 40', 64, RED if u > 0.6 else GREEN, 1, 'mm')
        return kb(img, t, S['A72'] - X, E['A72'], 1.0, 1.05, (CW / 2, CH * 0.47), (CW / 2, CH * 0.45))
    for k in range(3):
        put(img, bucket_spr(0.0, False), CW * 0.86 + k * 70, CH * 0.6 - 130, scale=0.6)
    u = ramp(t, S['A73'], E['A73'])
    put(img, bucket_spr(0.3), CW * (0.6 - 0.5 * u), CH * 0.6 - 150, scale=0.9)
    actor(img, 'count_odi', pp.ODI, 'wall', CW * 0.72, CH * 1.12, 2500, dict(eye=0.4, pain=1.0, mouth=0.15), t,
          light=dict(key=0.9), kw=dict(head_tilt=0.15, head_dy=0.15, lean=-0.05))
    lamp_pool(img, CW * 0.5, CH * 0.5, CW * 0.6, CH * 0.4, 0.5)
    return kb(img, t, S['A73'] - 0.2, E['A73'] + X, 1.15, 1.25, (CW * 0.6, CH * 0.5), (CW * 0.62, CH * 0.48))


@functools.lru_cache(None)
def shower_plate():
    return plate('shower', lambda: p2.shower())


def sc_shower(t):
    if t < S['A75']:                              # красный огонёк, писк, открывается узкая дверь
        img = canvas(wall_plate(14))
        blink_r = 0.5 + 0.5 * math.sin(t * 9)
        glow(img, CW * 0.5, CH * 0.2, 80, (255, 30, 30), 0.6 * blink_r)
        u = eio(ramp(t, S['A74'] + 0.5, E['A74']))
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle((CW * 0.36, CH * 0.28, CW * 0.36 + CW * 0.28 * u, CH * 0.775), fill=(150, 170, 172, 255))
        img.alpha_composite(lay)
        hud_text(img, 150, CH * 0.12, 'ТРЕБУЕТСЯ НЕЗАМЕДЛИТЕЛЬНОЕ', 36, RED, eo(ramp(t, S['A74'], S['A74'] + 0.3)))
        hud_text(img, 150, CH * 0.12 + 56, 'ПРИНЯТИЕ ДУША.', 36, RED, eo(ramp(t, S['A74'], S['A74'] + 0.3)))
        return kb(img, t, S['A74'] - X, E['A74'] + 0.2, 1.0, 1.1, (CW / 2, CH * 0.5), (CW / 2, CH * 0.45))
    img = canvas(shower_plate())
    d = S['A75']
    water = ramp(t, d, d + 0.3) * (1 - ramp(t, d + 2.0, d + 2.3)) + ramp(t, d + 3.6, d + 3.9) * (1 - ramp(t, d + 5.6, d + 6.0))
    soap = ramp(t, d + 2.0, d + 2.4) * (1 - ramp(t, d + 4.0, d + 5.0))
    actor(img, 'shower_odi', pp.ODI, 'reach' if water > 0.5 else 'stand', CW * 0.5, CH * 1.0, 2400,
          dict(eye=0.2 if water > 0.3 else 0.9, mouth=0.1, yaw=0.1), t, light=dict(key=1.05))
    if water > 0:
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        r = random.Random(int(t * 30))
        for _ in range(220):
            x = r.uniform(CW * 0.15, CW * 0.85)
            y = (r.random() * CH + t * 2600) % CH
            dd.line((x, y, x + 2, y + 60), fill=(200, 230, 240, int(120 * water)), width=3)
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1)))
    if soap > 0:
        img.alpha_composite(layer(lambda c: [(kit.ellipse(c, CW * 0.5 + math.sin(k * 2.1) * 200, CH * 0.2 + k * 25,
                                                          30 + (k % 4) * 10, 24), kit.fill(c, (240, 245, 220), 0.5 * soap))
                                             for k in range(30)]))
    if t > E['A75'] - 2.6:
        hud_text(img, 140, CH * 0.12, 'ОПЛАТА ДУШЕВОЙ ПРОЦЕДУРЫ: 1 СОЛ', 34, RED, eo(ramp(t, E['A75'] - 2.6, E['A75'] - 2.2)))
    return kb(img, t, S['A75'] - 0.2, E['A75'] + X, 1.05, 1.12, (CW / 2, CH * 0.5), (CW / 2, CH * 0.46))


def sc_lunch(t):
    s = S['A76']
    if t < s + D['A76'] * 0.55:                   # в кресле: сладкая вода, кубик-бульон
        img = canvas(niche_plate())
        actor(img, 'lunch_sit', pp.ODI, 'sit_bench', CW * 0.5, CH * 0.95, 1900, dict(eye=0.8, smile=0.3), t,
              kw=dict(arms={'L': (math.pi / 2 - 0.5, 0.2), 'R': (math.pi / 2 + 1.2, -2.3)}), light=dict(key=1.05))
        return kb(img, t, s - X, s + D['A76'] * 0.55, 1.3, 1.4, (CW / 2, CH * 0.42), (CW / 2, CH * 0.4))
    img = canvas(wall_plate(15, bench=True))
    actor(img, 'sleep_bench', pp.ODI, 'stand', CW * 0.5, CH * 0.62, 1500, dict(eye=0.0, blink=False, mouth=0.05), t,
          rot=90, shadow=0, light=dict(key=0.85, grad=0.1))
    lamp_pool(img, CW * 0.5, CH * 0.55, CW * 0.6, CH * 0.3, 0.6)
    u = ramp(t, s + D['A76'] * 0.55, E['A76'] + X)
    darken(img, 0.6 * u)
    return kb(img, t, s + D['A76'] * 0.55, E['A76'] + X, 1.2, 1.35, (CW / 2, CH * 0.58), (CW / 2, CH * 0.6))


def bench_444(img, t, talk=(), fc=None, x=0.62, y=1.02, hp=2700, name='p444', odi=True, odi_fc=None, odi_talk=()):
    bottle_hold = dict(arms={'L': (math.pi / 2 - 0.15, math.pi / 2 + 0.75), 'R': (math.pi / 2 + 0.15, math.pi / 2 - 0.75)})
    if odi:
        actor(img, f'{name}_odi', pp.ODI, 'sit_bench', CW * (x - 0.42), CH * y, hp * 1.02,
              {**dict(yaw=0.45, gaze=(0.8, 0), eye=0.9), **(odi_fc or {})}, t, talk=list(odi_talk), light=dict(key=1.0))
    hd = actor(img, name, pp.P444, 'sit_bench', CW * x, CH * y, hp, {**dict(yaw=-0.35, gaze=(-0.6, 0.2), brow=0.4), **(fc or {})},
               t, talk=list(talk), kw=dict(bottle_hold, lean=0.06, head_dy=0.12), light=dict(key=0.95, side=-0.3))
    # пузатая бутылка между ляжек, тряпичная лямка вокруг горлышка
    bx, by = CW * x, CH * y - hp * 0.36

    def bottle(c):
        c.move_to(bx - 70, by + 120)
        c.curve_to(bx - 110, by + 20, bx - 90, by - 70, bx - 45, by - 100)
        c.line_to(bx - 40, by - 170)
        c.line_to(bx + 40, by - 170)
        c.line_to(bx + 45, by - 100)
        c.curve_to(bx + 90, by - 70, bx + 110, by + 20, bx + 70, by + 120)
        c.close_path()
        c.set_source(kit.lin(bx - 100, 0, bx + 100, 0, [(0, (90, 140, 160), 0.7), (0.3, (200, 230, 240), 0.8),
                                                        (1, (60, 100, 120), 0.7)]))
        c.fill()
        c.rectangle(bx - 44, by - 170, 88, 30)
        kit.fill(c, (60, 90, 120))
        kit.soft_line(c, [(bx - 44, by - 120), (bx, by - 108), (bx + 44, by - 122), (bx + 80, by - 40)], (150, 120, 90), 10, 0.9)
    img.alpha_composite(layer(bottle))
    return hd


def sc_wake444(t):
    img = canvas(wall_plate(15, bench=True))
    bench_444(img, t, odi_fc=dict(eye=0.2 + 0.8 * ramp(t, S['A77'], S['A77'] + 1.5), pain=0.5))
    u = ramp(t, S['A77'], E['A77'])
    return kb(img, t, S['A77'] - X, E['A77'] + X, 1.35, 1.35, (CW * 0.3, CH * 0.6), (CW * 0.62, CH * 0.6))


def sc_bottle(t):
    img = canvas(wall_plate(15, bench=True))
    hd = bench_444(img, t, talk=['A79'], fc=dict(pain=0.8 if t < S['A79'] + 1.5 else 0.2, brow=0.6))
    if t < S['A79']:
        return kb(img, t, S['A78'] - X, E['A78'], 1.6, 1.5, (CW * 0.62, CH * 0.75), (CW * 0.62, CH * 0.62))
    if t < S['A80']:
        return kb(img, t, S['A79'] - 0.2, E['A79'], 1.7, 1.8, (hd[0], hd[1] + 220), (hd[0], hd[1] + 200))
    return kb(img, t, S['A80'] - 0.2, E['A80'] + X, 1.3, 1.4, (CW * 0.42, CH * 0.6), (CW * 0.4, CH * 0.58))


def amputation(img, t, t0, t1):
    """«пятьдесят солов долга — отрежут руку, потом ногу…»: силуэт в красном свете теряет конечности"""
    u = ramp(t, t0, t1)
    n = int(u * 4.99)
    arms = {'L': ('normal', (80, 30, 30)), 'R': ('normal', (80, 30, 30))}
    legs = {'L': ('normal', (80, 30, 30)), 'R': ('normal', (80, 30, 30))}
    order = [('arms', 'L'), ('legs', 'R'), ('legs', 'L'), ('arms', 'R')]
    for grp, side in order[:n]:
        (arms if grp == 'arms' else legs)[side] = None
    lk = pp.look(torso=(80, 30, 30), build='normal', arms=arms, legs=legs, shorts=(30, 12, 12), hair=('shaved', None),
                 ring_scars=False, number=None)
    if legs['L'] is None and legs['R'] is None:
        actor(img, f'amp{n}', lk, 'stand', CW / 2, CH * 0.78, 1500, dict(eye=0.4, pain=1.0), t, light=dict(key=0.8),
              rot=80, kw=dict(legs={'L': (math.pi / 2, math.pi / 2), 'R': (math.pi / 2, math.pi / 2)}))
    else:
        actor(img, f'amp{n}', lk, 'stand', CW / 2, CH * 0.8, 1500, dict(eye=0.6, pain=1.0), t, light=dict(key=0.8))


def sc_talk444(t):
    img = canvas(wall_plate(15, bench=True))
    keys = ['A81', 'A82', 'A83', 'A84', 'A88', 'A89']
    cur = next((k for k in keys if S[k] - 0.35 <= t < E[k] + 0.4), keys[-1])
    if cur == 'A82':                                # отрежут руку, ногу… червь
        img = Image.new('RGBA', (CW, CH), (10, 2, 2, 255))
        glow(img, CW / 2, CH * 0.45, 700, (160, 20, 20), 0.5)
        amputation(img, t, S['A82'] + D['A82'] * 0.3, E['A82'] - 0.5)
        return kb(img, t, S['A82'] - 0.35, E['A82'] + 0.4, 1.0, 1.08, (CW / 2, CH * 0.5), (CW / 2, CH * 0.48))
    if cur == 'A84':                                # за должником приходит пати полуросликов
        img = canvas(corridor_plate(11))
        P = corr_P()
        u = ramp(t, S['A84'], E['A84'])
        for k in range(3):
            fx, fy = P.p(-0.8 + k * 0.6, 0, 4.0 - u * 1.2 + k * 0.2)
            lk = dict(pp.crowd_look(800 + k), top=('tee', (60, 70, 90)), shoes=(40, 40, 44))
            actor(img, f'halfl{k}', lk, 'walk', fx, fy, 1.72 * P.s(4.0 - u * 1.2), dict(brow=-0.8, yaw=0), t, phase=t * 0.8 + k,
                  light=dict(key=0.9))
        darken(img, 0.25, (40, 0, 0))
        return kb(img, t, S['A84'] - 0.35, E['A84'] + 0.4, 1.1, 1.3, (CW / 2, CH * 0.5), (CW / 2, CH * 0.48))
    hd = bench_444(img, t, talk=['A81', 'A89'], odi_talk=['A83', 'A88'], fc=dict(brow=0.3, gaze=(-0.7, 0)))
    if cur in ('A83', 'A88'):
        return kb(img, t, S[cur] - 0.35, E[cur] + 0.4, 1.7, 1.75, (CW * 0.25, CH * 0.62), (CW * 0.25, CH * 0.6))
    if cur == 'A89':
        return kb(img, t, S[cur] - 0.35, E[cur] + 0.4, 1.9, 2.1, (hd[0], hd[1] + 200), (hd[0], hd[1] + 180))
    return kb(img, t, S[cur] - 0.35, E[cur] + 0.4, 1.55, 1.65, (hd[0] - 100, hd[1] + 300), (hd[0] - 80, hd[1] + 280))


def sc_twins(t):
    img = canvas(corridor_plate(12))
    P = corr_P()
    lk = pp.crowd_look(901)
    for k, x in enumerate((-0.5, 0.5)):
        fx, fy = P.p(x, 0, 2.4)
        actor(img, f'twin{k}', lk, 'stand', fx, fy, 1.72 * P.s(2.4), dict(yaw=0.3 * (1 if k == 0 else -1), smile=0.5), t,
              light=dict(key=1.0))
    glow(img, CW / 2, CH * 0.45, 500, (255, 220, 170), 0.15)
    return kb(img, t, S['A85'] - X, E['A85'] + X, 1.4, 1.55, (CW / 2, CH * 0.45), (CW / 2, CH * 0.43))


def sc_races(t):
    """черви, зомби, гоблины, орки, полурослики — а над всеми эльфы (их никто не видел)"""
    if t < S['A87']:
        img = canvas(wall_plate(15, bench=True))
        hd = bench_444(img, t, talk=['A86'], fc=dict(brow=0.3, smile=0.4))
        return kb(img, t, S['A86'] - X, E['A86'] + 0.3, 1.7, 1.8, (hd[0], hd[1] + 240), (hd[0], hd[1] + 220))
    img = Image.new('RGBA', (CW, CH), (6, 8, 10, 255))
    s = S['A87']
    fl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(fl).rectangle((0, CH * 0.72, CW, CH), fill=(24, 26, 28, 255))
    img.alpha_composite(fl)
    races = [
        ('worm', pp.look(torso=(170, 130, 100), build='thin', arms={'L': None, 'R': None}, legs={'L': None, 'R': None},
                         hair=('ragged', (60, 50, 40)), number='29'), 0.1),
        ('zombie', pp.look(torso=(160, 140, 120), build='thin', arms={'L': ('old', pp.SKIN_OLD), 'R': None},
                           legs={'L': ('thin', pp.SKIN_PALE), 'R': None}, number='3'), 0.2),
        ('goblin', pp.look(torso=(180, 140, 110), build='thin', arms={'L': ('old', pp.SKIN_OLD), 'R': None}, number='11'), 0.32),
        ('orc', pp.crowd_look(950), 0.44),
        ('halfling', dict(pp.crowd_look(951), top=('tee', (80, 96, 120)), shoes=(40, 40, 44)), 0.56),
    ]
    for k, (name, lk, f) in enumerate(races):
        a = eo(ramp(t, s + D['A87'] * f, s + D['A87'] * f + 0.5))
        if a <= 0:
            continue
        x = CW * (0.12 + k * 0.19)
        glow(img, x, CH * 0.72, 140, (220, 210, 180), 0.12 * a)
        if name == 'worm':
            actor(img, 'race_worm', lk, 'stand', x, CH * 0.76, 900, dict(eye=0.6, pain=0.8), t, rot=85, shadow=0.4,
                  light=dict(key=0.9 * a))
        elif name == 'zombie':
            actor(img, 'race_zombie', lk, 'stand', x + 20 * math.sin(t * 6), CH * 0.73 - 30 * abs(math.sin(t * 6)), 900,
                  dict(eye=0.8, pain=0.4), t, light=dict(key=0.9 * a))
        else:
            actor(img, f'race_{name}', lk, 'stand', x, CH * 0.73, 900 + k * 30, dict(eye=1.0), t, light=dict(key=0.95 * a))
    # эльфы: столб света сверху и высокий силуэт в нём
    e = eo(ramp(t, s + D['A87'] * 0.62, s + D['A87'] * 0.72))
    if e > 0:
        beam = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(beam).polygon([(CW * 0.42, 0), (CW * 0.58, 0), (CW * 0.68, CH * 0.5), (CW * 0.32, CH * 0.5)],
                                     fill=(220, 235, 255, int(70 * e)))
        img.alpha_composite(beam.filter(ImageFilter.GaussianBlur(40)))
        sil = layer(lambda c: (kit.ellipse(c, CW / 2, CH * 0.12, 40, 55), kit.fill(c, (240, 245, 255), 0.9 * e),
                               kit.poly(c, [(CW / 2 - 70, CH * 0.17), (CW / 2 + 70, CH * 0.17), (CW / 2 + 40, CH * 0.42),
                                            (CW / 2 - 40, CH * 0.42)]), kit.fill(c, (240, 245, 255), 0.9 * e),
                               kit.poly(c, [(CW / 2 - 36, CH * 0.07), (CW / 2 - 70, CH * 0.03), (CW / 2 - 30, CH * 0.1)]),
                               kit.fill(c, (240, 245, 255), 0.9 * e),
                               kit.poly(c, [(CW / 2 + 36, CH * 0.07), (CW / 2 + 70, CH * 0.03), (CW / 2 + 30, CH * 0.1)]),
                               kit.fill(c, (240, 245, 255), 0.9 * e)))
        img.alpha_composite(sil.filter(ImageFilter.GaussianBlur(6)))
    return kb(img, t, s - 0.2, E['A87'] + X, 1.05, 1.0, (CW / 2, CH * 0.55), (CW / 2, CH * 0.42))


def sc_promise(t):
    img = canvas(wall_plate(15, bench=True))
    if t < S['A91']:
        hd = bench_444(img, t, fc=dict(smile=0.7, brow=0.5), odi_talk=['A90'], odi_fc=dict(smile=0.4))
        return kb(img, t, S['A90'] - X, E['A90'], 1.35, 1.4, (CW * 0.45, CH * 0.62), (CW * 0.45, CH * 0.6))
    u = ramp(t, S['A91'], E['A91'] + X)
    actor(img, 'pr_odi', pp.ODI, 'sit_bench', CW * 0.2, CH * 1.02, 2750, dict(yaw=0.5, gaze=(0.9, -0.2), smile=0.5), t,
          light=dict(key=1.0))
    actor(img, 'p444_run', pp.P444, 'walk', CW * (0.68 + 0.5 * u), CH * 1.08, 2700, dict(yaw=-0.5, smile=0.8, gaze=(-0.9, 0)),
          t, talk=['A91'], phase=t * 0.9, light=dict(key=0.95), kw=dict(arms={'R': (-1.2, -1.6)}))
    return kb(img, t, S['A91'] - 0.2, E['A91'] + X, 1.25, 1.3, (CW * 0.55, CH * 0.58), (CW * 0.62, CH * 0.58))


def sc_medblock(t):
    img = canvas(wall_plate(16, redcross=True))
    back = dict(pp.ODI, back=True)
    actor(img, 'med_back', back, 'stand', CW * 0.5, CH * 1.45, 3200, dict(), t, light=dict(key=0.6, grad=0.3))
    if t >= S['A93']:
        a = eo(ramp(t, S['A93'], S['A93'] + 0.3))
        hud_text(img, 130, CH * 0.12, 'НЕ В СОСТОЯНИИ ОПЛАТИТЬ', 40, RED, a)
        hud_text(img, 130, CH * 0.12 + 62, 'УСЛУГИ МЕДБЛОКА.', 40, RED, a)
        hud_text(img, 130, CH * 0.12 + 140, 'ДИАГНОСТИКА — 2 СОЛА', 34, RED, a * 0.8)
    return kb(img, t, S['A92'] - X, E['A93'] + X, 1.0, 1.15, (CW / 2, CH * 0.5), (CW / 2, CH * 0.44))


def sc_receiver(t):
    img = canvas(recv_plate())
    for k in range(4):
        x = (CW * 0.78 - ((t * 140 + k * 300) % (CW * 0.9)))
        put(img, bucket_spr(1.0), x, CH * 0.6 - 150, scale=0.9)
    P = places.Persp(CW, CH, f=CW * 0.6, vy=CH * 0.42, eye=1.6)
    scare = bump((t * 0.5) % 1.0, 0.1, 0.1, 0.4)
    bars_and_buksa(img, P, t, x=-0.3, z=2.6, talk_k=['A95'], b_fc=dict(smile=0.6 * scare, brow=-0.6), k_fc=dict(smile=0.9),
                   finger=t >= S['A95'])
    ph = (t * 0.3) % 1.0
    wx, wy = P.p(1.4 - ph * 0.6, 0, 3.4)
    actor(img, 'recv_w', pp.GREYMAN, 'carry', wx, wy, 1.7 * P.s(3.4), dict(pain=0.9, eye=0.5 + 0.5 * scare), t, phase=t * 0.8,
          light=dict(key=0.9))
    return kb(img, t, S['A94'] - X, E['A95'] + X, 1.2, 1.3, (CW * 0.45, CH * 0.5), (CW * 0.42, CH * 0.48))


def sc_rumors(t):
    img = canvas(corridor_plate(13))
    P = corr_P()
    crowd(img, P, t, 'lean', seed=13, walkers=4, zmin=4)
    ox, oy = P.p(-2.2, 0, 3.0)
    actor(img, 'rum_odi', pp.ODI, 'walk', ox, oy, 1.72 * P.s(3.0), dict(yaw=0.4, gaze=(0.7, 0)), t, phase=t * 0.45,
          light=dict(key=0.9))
    for k, (x, lk) in enumerate(((0.4, pp.crowd_look(1001)), (1.1, pp.crowd_look(1002, female=True)))):
        fx, fy = P.p(x, 0, 1.5)
        actor(img, f'rum{k}', lk, 'stand', fx, fy, 1.72 * P.s(1.5), dict(yaw=0.5 * (1 if k == 0 else -1), gaze=(0.7 * (1 if k == 0 else -1), 0),
              brow=-0.4), t, talk=['A97'], light=dict(key=0.85, side=0.4))
    return kb(img, t, S['A96'] - X, E['A97'] + X, 1.3, 1.45, (CW * 0.55, CH * 0.45), (CW * 0.5, CH * 0.44))


@functools.lru_cache(None)
def kmap_plate():
    return plate('kmap', lambda: p2.klux_map())


def sc_klux_map(t):
    img = canvas(kmap_plate())
    return kb(img, t, S['A98'] - X, E['A98'] + X, 1.3, 1.1, (CW / 2, CH * 0.38), (CW / 2, CH * 0.42))


@functools.lru_cache(None)
def klux_plate():
    return plate('klux', lambda: p2.klux()[0])


def sc_klux(t):
    img = canvas(klux_plate())
    P = places.Persp(CW, CH, f=CW * 0.8, vy=CH * 0.4, eye=1.8)
    r = random.Random(3)
    for k in range(26):                           # люди за столиками и в проходах
        z = 4 + (k * 1.9) % 22
        x = -9 + (k * 3.7) % 18
        fx, fy = P.p(x, 0, z)
        if -100 < fx < CW + 100:
            actor(img, f'kl{k}', pp.crowd_look(1100 + k), 'sit_bench' if k % 3 else 'stand', fx, fy, 1.72 * P.s(z),
                  dict(yaw=r.uniform(-0.4, 0.4)), t, light=dict(key=1.0, tint=(1.05, 1.0, 0.9)))
    dust(img, t, 50, 17, (0, 0, CW, CH), 0.25)
    if t < S['B99']:
        return kb(img, t, S['A99'] - X, E['A99'], 1.0, 1.2, (CW / 2, CH * 0.55), (CW / 2, CH * 0.48))
    return kb(img, t, S['B99'] - 0.2, E['B99'] + X, 1.3, 1.7, (CW / 2, CH * 0.42), (CW / 2, CH * 0.32))


@functools.lru_cache(None)
def vend_row(kinds):
    def make():
        img = Image.new('RGB', (CW, CH), (30, 28, 26))
        d = ImageDraw.Draw(img)
        d.rectangle((0, int(CH * 0.8), CW, CH), fill=(44, 40, 36))
        w = int(CW / len(kinds))
        for k, kind in enumerate(kinds):
            spr = to_pil(p2.vending(kind, w - 20, int(CH * 0.62), seed=k + 1)).convert('RGB')
            img.paste(spr, (k * w + 10, int(CH * 0.18)))
        return img
    return plate('vend_' + '_'.join(kinds), make)


def sc_vending(t):
    img = canvas(vend_row(('clothes', 'home', 'food')))
    glow(img, CW / 2, CH * 0.45, 700, (220, 240, 230), 0.12)
    return kb(img, t, S['C01'] - X, E['C01'] + X, 1.25, 1.25, (CW * 0.3, CH * 0.48), (CW * 0.7, CH * 0.48))


def sc_vending_arms(t):
    img = canvas(vend_row(('camo', 'arms')))
    actor(img, 'weirdo', pp.WEIRDO, 'reach', CW * 0.85, CH * 1.08, 2600, dict(yaw=-0.5, gaze=(-0.8, -0.2), eye=1.2), t,
          light=dict(key=0.8, side=-0.6), kw=dict(arms={'R': (-math.pi / 2 - 0.9, math.pi + 0.2)}))
    press = bump((t * 1.6) % 1.0, 0.0, 0.05, 0.3)
    glow(img, CW * 0.75, CH * 0.78, 30, (255, 255, 255), 0.5 * press)
    return kb(img, t, S['C02'] - X, E['C02'] + X, 1.1, 1.3, (CW * 0.35, CH * 0.5), (CW * 0.62, CH * 0.5))


@functools.lru_cache(None)
def bulge_door():
    def make():
        cv = kit.from_premul(p2.wall_close(seed=18))
        c = cv.ctx
        x0, y0, x1, y1 = CW * 0.3, CH * 0.24, CW * 0.7, CH * 0.775
        c.rectangle(x0, y0, x1 - x0, y1 - y0)
        kit.fill(c, (40, 44, 46))
        c.rectangle(x0, y0, x1 - x0, y1 - y0)
        kit.stroke(c, (60, 235, 120), 16, 0.95)
        return cv.premul()
    return plate('bulge_door', make)


def sc_evening(t):
    if t < S['C03'] + D['C03'] * 0.5:
        img = canvas(klux_plate())
        hud_text(img, CW / 2, CH * 0.14, '20:00', 120, GREEN, eo(ramp(t, S['C03'], S['C03'] + 0.3)), 'mm')
        return kb(img, t, S['C03'] - X, S['C03'] + D['C03'] * 0.5, 1.2, 1.3, (CW / 2, CH * 0.4), (CW / 2, CH * 0.4))
    img = canvas(bulge_door())
    actor(img, 'ev_back', dict(pp.ODI, back=True), 'stand', CW * 0.5, CH * 1.3, 2700, dict(), t, light=dict(key=0.6, grad=0.3))
    if t >= S['C04']:
        hud_text(img, 150, CH * 0.14, 'ОДИННАДЦАТЫЙ. (УРН).', 42, GREEN, eo(ramp(t, S['C04'], S['C04'] + 0.3)))
        hud_text(img, 150, CH * 0.14 + 70, 'ЦЕЛЬ?', 42, GREEN, eo(ramp(t, S['C04'] + 1.0, S['C04'] + 1.3)))
    if t >= S['C06']:
        hud_text(img, 150, CH * 0.14 + 160, 'УЙТИ.', 64, RED, eo(ramp(t, S['C06'], S['C06'] + 0.2)))
    return kb(img, t, S['C03'] + D['C03'] * 0.5, E['C06'] + X, 1.0, 1.15, (CW / 2, CH * 0.5), (CW / 2, CH * 0.44))


def sc_demote(t):
    img = canvas(blurred(klux_plate(), 9, 0.55))
    actor(img, 'dem_face', pp.ODI, 'stand', CW * 0.5, HY(6400, CH * 0.4), 6400, dict(eye=0.8, brow=0.4, pain=0.6, gaze=(0, 0.2)), t,
          light=dict(key=0.85, side=0.4))
    sw = ramp(t, S['C07'] + D['C07'] * 0.6, S['C07'] + D['C07'] * 0.6 + 0.3)
    gl = bump(t, S['C07'] + D['C07'] * 0.6, 0.02, 0.6)
    txt = 'ТЕКУЩИЙ СТАТУС: ' + ('УРН' if sw > 0.5 else 'ОРН')
    jx = (random.Random(int(t * 40)).random() - 0.5) * 40 * gl
    hud_text(img, 140 + jx, CH * 0.16, txt, 48, RED if sw > 0.5 else GREEN, eo(ramp(t, S['C07'], S['C07'] + 0.3)))
    if t >= S['C09']:
        hud_text(img, 140, CH * 0.16 + 80, 'ДОЛГ: 10 СОЛОВ', 40, RED, eo(ramp(t, S['C09'], S['C09'] + 0.3)))
    if gl > 0:
        darken(img, 0.3 * gl, (120, 0, 0))
    return kb(img, t, S['C07'] - X, E['C09'] + X, 1.05, 1.18, (CW / 2, CH * 0.42), (CW / 2, CH * 0.38))


@functools.lru_cache(None)
def caps_plate(litter=True):
    return plate(f'caps{int(litter)}', lambda: p2.capsule_wall(litter=litter)[0])


def sc_guard(t):
    img = canvas(caps_plate(False))
    P = places.Persp(CW, CH, f=CW * 0.55, vy=CH * 0.4, eye=1.7)
    chew = 0.15 + 0.15 * abs(math.sin(t * 5))
    gx, gy = P.p(0.1, 0, 1.6)
    talking = any(S[k] <= t < E[k] for k in ('C11', 'C13'))
    gh = actor(img, 'guard', pp.GUARD, 'crossed', gx, gy, 1.8 * P.s(1.6),
               dict(yaw=-0.1, brow=-0.5, eye=0.7, mouth=None if talking else q(chew, 6), gaze=(-0.3, 0.1)), t,
               talk=['C11', 'C13'], light=dict(key=1.0))
    throw = S['C13'] + D['C13'] * 0.72
    if t < S['C10'] + D['C10'] * 0.15:
        pass
    u = ramp(t, throw, throw + 0.7)
    if 0 < u < 1:
        gx2 = gh[0] + (CW * 0.15 - gh[0]) * u
        gy2 = gh[1] + 300 - math.sin(u * math.pi) * 300
        img.alpha_composite(layer(lambda c: (c.rectangle(gx2 - 30, gy2 - 10, 60, 20), kit.fill(c, (220, 214, 190)))))
    cur = next((k for k in ('C10', 'C11', 'C12', 'C13') if S[k] - 0.3 <= t < E[k] + 0.4), 'C13')
    if cur in ('C10', 'C11'):
        return kb(img, t, S['C10'] - X, E['C11'] + 0.4, 1.0, 1.4, (CW / 2, CH * 0.55), (gh[0], gh[1] + 300))
    if cur == 'C12':
        img2 = canvas(blurred(caps_plate(False), 8, 0.6))
        actor(img2, 'guard_odi', pp.ODI, 'stand', CW * 0.5, HY(6400, CH * 0.4), 6400, dict(eye=1.0, brow=0.3, yaw=0.15, gaze=(0.2, -0.3)),
              t, talk=['C12'], light=dict(key=0.9))
        return kb(img2, t, S['C12'] - 0.3, E['C12'] + 0.4, 1.05, 1.1, (CW / 2, CH * 0.42), (CW / 2, CH * 0.4))
    return kb(img, t, S['C13'] - 0.3, E['C13'] + X, 1.6, 1.4, (gh[0], gh[1] + 260), (gh[0] - 100, gh[1] + 320))


def sc_poor_side(t):
    img = canvas(caps_plate(True))
    return kb(img, t, S['C14'] - X, E['C14'] + X, 1.0, 1.2, (CW / 2, CH * 0.5), (CW / 2, CH * 0.38))


def sc_capsule(t):
    img = canvas(caps_plate(True))
    P = places.Persp(CW, CH, f=CW * 0.55, vy=CH * 0.4, eye=1.7)
    u = ramp(t, S['C15'], S['C15'] + D['C15'] * 0.6)
    fx, fy = P.p(-1.45, 1.4 * u, 2.6)
    actor(img, 'climb', dict(pp.ODI, back=True), 'reach', fx, fy, 1.72 * P.s(2.6), dict(), t, light=dict(key=0.85),
          kw=dict(arms={'R': (-math.pi / 2 - 0.3, -math.pi / 2 - 0.2), 'L': (math.pi / 2 - 0.4, math.pi / 2 - 1.2)}))
    lid = eo(ramp(t, S['C15'] + D['C15'] * 0.7, E['C15']))
    if lid > 0:
        a = P.p(-2.0, 4.0, 1.0)
        glow(img, a[0] + 60, a[1] + 120, 160, (255, 220, 140), 0.35 * lid)
    return kb(img, t, S['C15'] - X, E['C15'] + X, 1.2, 1.5, (CW * 0.35, CH * 0.45), (CW * 0.25, CH * 0.32))


@functools.lru_cache(None)
def capin_plate(lamp):
    return plate(f'capin{int(lamp)}', lambda: p2.capsule_in(lamp=lamp))


def sc_capsule_in(t):
    off = t > S['C16'] + D['C16'] * 0.34
    img = canvas(capin_plate(not off))
    actor(img, 'cap_lie', pp.ODI, 'stand', CW * 0.5, CH * 0.98, 2100, dict(eye=0.9 if t < S['C18'] else 0.0, smile=0.3,
          gaze=(0, -1), blink=t < S['C18']), t, shadow=0, rot=0, light=dict(key=0.95 if not off else 0.45, tint=(1.1, 1.0, 0.75)),
          kw=dict(arms={'R': (-math.pi / 2 - 0.2, -math.pi / 2) if S['C16'] + D['C16'] * 0.25 < t < S['C16'] + D['C16'] * 0.36
                        else (math.pi / 2 + 0.25, math.pi / 2 + 0.1)}))
    # жвачка на полочке
    if t > S['C16'] + D['C16'] * 0.45:
        img.alpha_composite(layer(lambda c: (c.rectangle(CW * 0.8, CH * 0.3 - 26, 70, 22), kit.fill(c, (220, 214, 190)))))
    if off:
        darken(img, 0.45)
    if t >= S['C17']:
        hud_text(img, 140, CH * 0.14, 'ДОЛГ: 11 СОЛОВ', 44, RED, eo(ramp(t, S['C17'], S['C17'] + 0.3)) * (1 - ramp(t, S['C18'], S['C18'] + 1)))
    fade = ramp(t, E['C18'] - 0.5, DUR)
    darken(img, fade)
    return kb(img, t, S['C16'] - X, DUR, 1.1, 1.35, (CW / 2, CH * 0.36), (CW / 2, CH * 0.3))


SCENE_FN = {
    'dark': sc_dark, 'body': sc_body, 'yorka_voice': sc_yorka_voice, 'memory': sc_memory, 'getup': sc_getup,
    'self': sc_self, 'yorka_close': sc_yorka_close, 'yorka_face': sc_yorka_face, 'corridor': sc_corridor,
    'smiles': sc_smiles, 'number': sc_number, 'sphere': sc_sphere, 'scan': sc_scan, 'slump': sc_slump,
    'niche_door': sc_niche_door, 'niche': sc_niche, 'cube': sc_cube, 'yorka_talk': sc_yorka_talk, 'slap': sc_slap,
    'elbow': sc_elbow, 'party': sc_party, 'leave': sc_leave, 'menu': sc_menu, 'odin': sc_odin, 'screen': sc_screen,
    'push': sc_push, 'game': sc_game, 'lame': sc_lame, 'walk': sc_walk, 'ring': sc_ring, 'tooth': sc_tooth,
    'conveyor': sc_conveyor, 'laugh': sc_laugh, 'bucket': sc_bucket, 'kick': sc_kick, 'bars': sc_bars,
    'colossus': sc_colossus, 'trip': sc_trip, 'count': sc_count, 'shower': sc_shower, 'lunch': sc_lunch,
    'wake444': sc_wake444, 'bottle': sc_bottle, 'talk444': sc_talk444, 'twins': sc_twins, 'races': sc_races,
    'promise': sc_promise, 'medblock': sc_medblock, 'receiver': sc_receiver, 'rumors': sc_rumors,
    'klux_map': sc_klux_map, 'klux': sc_klux, 'vending': sc_vending, 'vending_arms': sc_vending_arms,
    'evening': sc_evening, 'demote': sc_demote, 'guard': sc_guard, 'poor_side': sc_poor_side, 'capsule': sc_capsule,
    'capsule_in': sc_capsule_in,
}
WARM = {'klux', 'klux_map', 'vending', 'vending_arms', 'evening', 'demote', 'guard', 'capsule_in'}


def scene_at(t):
    for i, (name, t0, t1, _) in enumerate(SCENES):
        if t0 <= t < t1 or i == len(SCENES) - 1:
            return i
    return len(SCENES) - 1


def frame_scene(i, t):
    name = SCENES[i][0]
    im = SCENE_FN[name](t)
    return grade(im, t, warm=1.0 if name in WARM else 0.0)


def render_at(t):
    i = scene_at(t)
    name, t0, t1, _ = SCENES[i]
    im = frame_scene(i, t)
    if i > 0 and t < t0 + X / 2:                      # мягкая смена: смешиваем с предыдущей
        u = 0.5 + (t - t0) / X
        im = mix(frame_scene(i - 1, t), im, u)
    elif i < len(SCENES) - 1 and t > t1 - X / 2:
        u = 0.5 - (t1 - t) / X
        im = mix(im, frame_scene(i + 1, t), u)
    im = im.convert('RGBA')
    subtitles(im, t)
    return im.convert('RGB')


def frame_bytes(i):
    return BR.render(render_at, i / FPS, i).tobytes()


if __name__ == '__main__':
    frames.cli(lambda t: BR.render(render_at, t), frame_bytes, W, H, FPS, BR.n_frames(FPS, DUR))
