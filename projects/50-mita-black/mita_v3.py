"""v3 (2026-11-17): Мита из ключевых поз ChatGPT с досчётом кадров (anim.py), сцены по новому сценарию.
Подключается из render.py: from mita_v3 import *  (использует помощники render через модуль R)."""
import functools
import math

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

import anim
import fx
import events as E
from timeline import AD_STOP, DUR, ON

R = None                     # render (подставляется в bind)
S0 = 0.92                    # масштаб новых поз (v5: крупнее — меньше пустоты): холст 768×1024 → экран
BASE = 988                   # линия пола на холсте (листы стоя)
HOOK_BASE = 965
FOOT = 1540
SPIN_END = E.SPIN + 1.05


def bind(r):
    global R
    R = r


def ease(x):
    return fx.smooth(fx.clamp01(x))


def appear(t, t0, d=0.3):
    return ease((t - t0) / d)


# ------------------------------------------------------------------ общие помощники
@functools.lru_cache(None)
def shadow_sprite():
    return fx.radial(256, (0, 0, 0), 1.6, 0.55).resize((420, 70))


def grade(a, tint=None, k=0.0, rim=None, rim_k=0.0, bright=1.0):
    if tint is None and rim is None and bright == 1.0:
        return a
    f = a.astype(np.float32)
    rgb = f[..., :3]
    if tint is not None and k > 0:
        rgb = rgb * (1 - k) + rgb * (np.array(tint, np.float32) / 255) * k * 1.5
    if bright != 1.0:
        rgb = rgb * bright
    if rim is not None and rim_k > 0:
        al = f[..., 3]
        bl = cv2.GaussianBlur(al, (0, 0), 5)
        e = np.clip((al - bl) / 255 * 2.4, 0, 1)[..., None]
        rgb = rgb + e * np.array(rim, np.float32) * rim_k
    f[..., :3] = np.clip(rgb, 0, 255)
    return f.astype(np.uint8)


def put_mita(cv, a, cx, foot, s=S0, base=BASE, alpha=1.0, rot=0.0, sx=1.0, sy=1.0, shadow=True, reflect=0.0, flip=False,
             anchor_x=None):
    if alpha <= 0.003:
        return
    im = Image.fromarray(a)
    ax = anim.CW / 2 if anchor_x is None else anchor_x
    if flip:
        im = ImageOps.mirror(im)
        ax = anim.CW - ax
    if shadow:
        R.put(cv, shadow_sprite(), cx, foot - 4, s / 0.8 * (0.9 + 0.1 * sx), 0.75 * alpha)
    if reflect > 0:
        ref = ImageOps.flip(im)
        fx.over(cv, fx.warp(ref, cx, foot, s * sx, s * sy, 0.0, (ax, anim.CH - base)), reflect * alpha)
    fx.over(cv, fx.warp(im, cx, foot, s * sx, s * sy, rot, (ax, base)), alpha)


@functools.lru_cache(None)
def tile_np(gift, model, backdrop, size, q):
    """NFT-плитка как RGBA-массив (q — номер кадра Lottie ×1/12 с; для карточек в руках анимация неважна)."""
    return np.array(R.gift_tile(gift, model, backdrop, size, q / 12.0))


def cards_painter(tiles):
    """Магентовые карточки → NFT по порядку слева направо (tiles: список (gift, model, backdrop))."""
    def paint(comps, shape):
        out = np.zeros(shape, np.float32)
        cs = sorted([c for c in comps if c['area'] > 600], key=lambda c: c['c'][0])
        for c, tl in zip(cs, tiles):
            q = anim.quad_of(c)
            tile = tile_np(tl[0], tl[1], tl[2], 256, 0)
            w = anim.fill_quad(out, None, q, tile, inset=-0.06)
            a = w[..., 3:4] / 255
            out = out * (1 - a) + w * a
        return out
    return paint


def lot3(g, k):
    c = R.lot(g, k)
    return (c['gift'], c['model'], c['backdrop'])


CUP_BLACK = None


def _cup():
    global CUP_BLACK
    if CUP_BLACK is None:
        CUP_BLACK = lot3('Whip Cupcake', 'black_floor')
    return CUP_BLACK


# ------------------------------------------------------------------ дорожки поз
HOOK_T = anim.Track([(0.0, 'hook_peek'), (1.15, 'hook_in_a'), (1.42, 'hook_in_b'), (1.72, 'hook_step'), (2.02, 'hook_in_c'),
                     (2.30, 'hook_wave'), (2.58, 'hook_in_c'), (2.86, 'hook_wave'), (3.3, 'hook_in_c')], dur=0.27)


def hook_x(t):
    return 962 + (540 - 962) * ease((t - 0.95) / 1.35)


CARD_T = anim.Track([(SPIN_END, 'jump_calm'), (E.CARD_GRAB, 'card_in_a'), (E.CARD_GRAB + 0.35, 'card_1'),
                     (E.CARD_GRAB + 0.7, 'card_in_b'), (E.CARD_GRAB + 1.05, 'card_2'), (E.CARD_SHOW, 'card_in_c'),
                     (E.CARD_SHOW + 0.32, 'card_3')], dur=0.3)
LH = E.LOCKET_HIT
JUMP_T = anim.Track([(E.LOCKET - 0.2, 'jump_notice'), (LH - 0.45, 'jump_prep'), (LH - 0.22, 'jump_crouch'), (LH, 'jump_takeoff'),
                     (LH + 0.17, 'jump_peak'), (LH + 0.36, 'jump_fall'), (LH + 0.52, 'jump_land'), (LH + 0.78, 'jump_recover'),
                     (LH + 1.4, 'jump_calm')], dur=0.18)
CR = E.CREEPY
CREEPY_T = anim.Track([(CR, 'creepy_1'), (CR + 0.38, 'creepy_in_a'), (CR + 0.7, 'creepy_2'), (CR + 1.0, 'creepy_in_b'),
                       (CR + 1.28, 'creepy_3'), (CR + 1.6, 'creepy_in_c')], dur=0.3)


def _knob_keys():
    ks = [(E.CREEPY_END, 'knob_1')]
    for g in E.GACHA:
        t0 = g - 0.62
        ks += [(t0, 'knob_1'), (t0 + 0.14, 'knob_in_a'), (t0 + 0.28, 'knob_2'), (t0 + 0.42, 'knob_in_b'), (t0 + 0.56, 'knob_3')]
    ks += [(E.GACHA[-1] + 0.3, 'knob_watch'), (E.TEASE + 0.2, 'jump_notice')]
    out, last = [], -1
    for t, n in sorted(ks):
        if t > last + 0.05:
            out.append((t, n))
            last = t
    return out


KNOB_T = anim.Track(_knob_keys(), dur=0.14)
GL = E.GLOW
PHONE_T = anim.Track([(GL, 'phone_1'), (E.GLOW_PHONE - 0.1, 'phone_in_a'), (E.GLOW_PHONE + 0.2, 'phone_2'),
                      (E.GLOW_SHOW - 0.25, 'phone_in_b'), (E.GLOW_SHOW + 0.05, 'phone_3'), (E.PLAIN - 0.3, 'phone_hug')], dur=0.28)
K = E.KICK
KICK_T = anim.Track([(E.PLAIN, 'kick_1'), (K - 0.32, 'kick_in_a'), (K - 0.12, 'kick_2'), (K + 0.04, 'kick_in_b'),
                     (K + 0.16, 'kick_3'), (K + 0.62, 'kick_dust')], dur=0.16)
TWO_T = anim.Track([(E.OUTRO, 'two_1'), (E.OUTRO_LUX + 0.5, 'two_in_a'), (E.OUTRO_MIN + 0.1, 'two_2'),
                    (E.OUTRO_MIN + 0.75, 'two_in_b'), (E.OUTRO_PILL - 0.5, 'two_3'), (E.OUTRO_PILL + 0.25, 'two_point')], dur=0.3)
RUN = ['run_1', 'run_2', 'run_3', 'run_4', 'run_5', 'run_6']
HANG = ['hang_3', 'hang_in_b', 'hang_1', 'hang_in_a', 'hang_2']
SWING = ['ad_sit_1', 'ad_sit_in_a', 'ad_sit_2', 'ad_sit_in_b', 'ad_sit_3']
UFC_SIT = ['ufc_sit_1', 'ufc_sit_2', 'ufc_sit_3']

# сцены (время содержания) — у каждой своя отрисовка Миты
SCENES = [
    ('hook', 0.0), ('spin', E.SPIN - 0.12), ('card', SPIN_END), ('ufc', E.UFC - 0.2), ('jump', E.LOCKET - 0.2),
    ('creepy', E.CREEPY), ('gacha', E.CREEPY_END), ('demand', AD_STOP + 0.12), ('phone', E.GLOW), ('kick', E.PLAIN),
    ('hang', E.PRICE), ('two', E.OUTRO),
]
CUT = {'creepy', 'gacha', 'demand', 'phone', 'kick'}      # жёсткая смена под глитч (без перетекания)


def scene_of(t):
    cur = SCENES[0]
    for sc in SCENES:
        if t >= sc[1]:
            cur = sc
    return cur


# ------------------------------------------------------------------ геометрия сцен
@functools.lru_cache(None)
def comps_of(name):
    return anim.magenta(anim.pose(name))[1]


def biggest(comps):
    return max(comps, key=lambda c: c['area']) if comps else None


# автомат с капсулами: ручка автомата совпадает с магентовой ручкой в руке Миты
GACHA_CX = 640
_gk = biggest(comps_of('knob_1'))
KNOB_SX = GACHA_CX + (_gk['c'][0] - anim.CW / 2) * S0
KNOB_SY = FOOT - (BASE - _gk['c'][1]) * S0
MACH_H = 610
MACH_IMG = None


def machine():
    global MACH_IMG
    if MACH_IMG is None:
        im = Image.open(R.HERE / 'input' / 'props' / 'gacha.png').convert('RGBA')
        k = MACH_H / im.height
        MACH_IMG = (im.resize((round(im.width * k), MACH_H), Image.LANCZOS), k)
    return MACH_IMG


def machine_geom():
    im, k = machine()
    left = KNOB_SX - 300 * k
    top = KNOB_SY - 587 * k
    return im, k, left, top


# ------------------------------------------------------------------ Мита по сценам
def mita_frame(name, t):
    """(массив RGBA холста, параметры размещения) для сцены name в момент t."""
    P = dict(cx=540.0, foot=FOOT, s=S0, base=BASE, rot=0.0, sx=1.0, sy=1.0, flip=False, shadow=True, reflect=0.0,
             tint=None, k=0.0, rim=None, rim_k=0.0, bright=1.0, anchor_x=None)
    by, bx = anim.breathe(t)
    tk = R.talk(t)
    P['sy'] = by * (1 + 0.01 * tk)
    if name == 'hook':
        a = HOOK_T.frame(t)
        P.update(cx=hook_x(t), base=HOOK_BASE)
        if t < 1.0:                                       # выглядывает из-за края — без тени
            P['shadow'] = False
        return a, P
    if name == 'card':
        a = CARD_T.frame(t)
        if t >= E.CARD_GRAB - 0.3:
            a = anim.replace_magenta(a, cards_painter([_cup()]))
        return a, P
    if name == 'ufc':
        return ufc_group(t), dict(P, s=0.84, foot=1580, base=1000, shadow=False)
    if name == 'jump':
        a = JUMP_T.frame(t)
        u = (t - LH) / 0.52
        if 0 < u < 1:
            P['foot'] = FOOT - 70 * math.sin(math.pi * u)
        P['sy'] = 1.0
        return a, P
    if name == 'creepy':
        a = CREEPY_T.frame(t)
        z = 1.0 + 0.08 * ease((t - CR) / 1.7)
        return a, dict(P, s=2.0 * z, foot=1960, base=1024, shadow=False, sy=1.0, tint=(255, 60, 70), k=0.25, bright=0.9,
                       rim=(255, 40, 60), rim_k=0.8)
    if name == 'gacha':
        a = KNOB_T.frame(t)
        a = anim.replace_magenta(a, None)                 # ручка автомата видна сквозь пальцы
        return a, dict(P, cx=GACHA_CX)
    if name == 'demand':
        return demand_mita(t, P)
    if name == 'phone':
        a = PHONE_T.frame(t)
        a = anim.replace_magenta(a, phone_painter(t))
        return a, dict(P, s=0.9, foot=1662, base=1005, tint=(255, 120, 170), k=0.22, rim=(255, 130, 210), rim_k=0.9,
                       shadow=False)
    if name == 'kick':
        return KICK_T.frame(t), dict(P, cx=470)
    if name == 'hang':
        return hang_mita(t, P)
    if name == 'two':
        a = TWO_T.frame(t)
        a = anim.replace_magenta(a, cards_painter([lot3('Electric Skull', 'black_floor'), lot3('Snow Globe', 'floor')]))
        return a, P
    return None, P


def draw_new(cv, name, t, alpha=1.0):
    a, P = mita_frame(name, t)
    if a is None:
        return
    a = grade(a, P['tint'], P['k'], P['rim'], P['rim_k'], P['bright'])
    if name == 'gacha':
        draw_machine(cv, t, alpha)
    put_mita(cv, a, P['cx'], P['foot'], P['s'], P['base'], alpha, P['rot'], P['sx'], P['sy'], P['shadow'], P['reflect'],
             P['flip'], P['anchor_x'])
    if name == 'gacha':
        draw_capsules(cv, t, alpha)


def draw_mita(cv, t, old_draw):
    name, t0 = scene_of(t)
    if name == 'spin':
        if t < E.SPIN:                                    # перетекание из позы хука в первый кадр кружения
            k = ease((t - t0) / 0.12)
            draw_new(cv, 'hook', t, 1 - k)
            old_draw(cv, max(t, E.SPIN), alpha=k)
        else:
            old_draw(cv, t)
        return
    if name == 'card' and t < SPIN_END + 0.18:            # из готики «старой» в новую позу
        k = ease((t - SPIN_END) / 0.18)
        old_draw(cv, SPIN_END - 1e-3, alpha=1 - k)
        draw_new(cv, 'card', t, k)
        R.sparkles(cv, t, SPIN_END, 540, FOOT - 420, 340, 16, R.GOLD)
        return
    if name not in CUT and name != 'hook':
        prev = [s for s in SCENES if s[1] < t0]
        if prev and t < t0 + 0.2 and prev[-1][0] not in ('spin',):
            k = ease((t - t0) / 0.2)
            draw_new(cv, prev[-1][0], t0 - 1e-3, 1 - k)
            draw_new(cv, name, t, k)
            R.sparkles(cv, t, t0, 540, FOOT - 420, 320, 14, R.GOLD)
            return
    draw_new(cv, name, t)


# ------------------------------------------------------------------ сцена: боец UFC
UFC_HEAD = (298.0, 215.0, 108.0)            # центр и «радиус» головы в кадре модели 600 px


def ufc_group(t):
    """Холст 768×1024: боец (сзади) + Мита + голова бойца в магентовом шаре."""
    fr = anim.pingpong(UFC_SIT, t, 1.5)
    comps = anim.magenta(fr)[1]
    sp = biggest(comps)
    if sp is None:
        return fr
    hx, hy = sp['c']
    r = math.sqrt(sp['area'] / math.pi)
    m = r * 1.06 / UFC_HEAD[2]
    model = R.lottie.frame(R.model_path('UFC Strike', 'C. Oliveira'), t, size=600)
    M = np.float32([[m, 0, hx - UFC_HEAD[0] * m], [0, m, hy - UFC_HEAD[1] * m]])
    fighter = cv2.warpAffine(np.array(model), M, (anim.CW, anim.CH), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)).astype(np.float32)
    mita = anim.replace_magenta(fr, lambda comps, shape: fighter)
    mf = mita.astype(np.float32)
    a = mf[..., 3:4] / 255
    out = fighter * (1 - a) + mf * a
    out[..., 3:4] = fighter[..., 3:4] * (1 - a) + mf[..., 3:4]
    return np.clip(out, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ сцена: автомат
def draw_machine(cv, t, alpha=1.0):
    im, k, left, top = machine_geom()
    base = top + MACH_H
    # тумба под автоматом
    def ped(d, mp, S):
        x0, y0 = mp(left + 20, base - 6)
        x1, y1 = mp(left + im.width - 20, FOOT + 6)
        d.rounded_rectangle([x0, y0, x1, y1], int(14 * S), fill=(34, 26, 40, 255))
        d.rounded_rectangle([x0 + 10 * S, y0 + 10 * S, x1 - 10 * S, y0 + 22 * S], int(6 * S), fill=(150, 24, 52, 255))
    R.put(cv, shadow_sprite(), left + im.width / 2, FOOT - 4, 1.1, 0.7 * alpha)
    fx.over(cv, fx.draw_rgba((left - 10, base - 20, left + im.width + 10, FOOT + 20), ped), alpha)
    shake = 0.0
    for g in E.GACHA:
        u = (t - (g - 0.15)) / 0.3
        if 0 < u < 1:
            shake = math.sin(u * math.pi * 6) * 3 * (1 - u)
    fx.over(cv, (im, int(left + shake), int(top)), alpha)


def draw_capsules(cv, t, alpha=1.0):
    alpha *= 1 - appear(t, E.TEASE - 0.15, 0.3)
    if alpha <= 0.003:
        return
    im, k, left, top = machine_geom()
    chx, chy = left + 296 * k, top + 739 * k
    for j, (g, bd, cap) in enumerate(zip(E.GACHA, ('Black', 'Burgundy', 'Copper'), ('cap_black', 'cap_burgundy', 'cap_copper'))):
        u = t - g
        if u < 0:
            continue
        x_slot = 190 + 350 * j
        if u < 0.55:                                       # капсула выкатывается и подпрыгивает
            v = u / 0.55
            x = chx - 60 * v
            y = chy + 40 + (FOOT - 40 - chy - 40) * v - 120 * math.sin(math.pi * v)
            R.put(cv, R.prop_cap(cap), x, y, 0.42, alpha, v * 4)
        elif u < 0.95:                                     # раскрывается — кекс летит в ряд
            v = (u - 0.55) / 0.4
            sx = chx - 60
            R.put(cv, R.prop_cap(cap), sx - 30 * v, FOOT - 40 + 10 * v, 0.42, alpha * (1 - v))
            x = sx + (x_slot - sx) * ease(v)
            y = (FOOT - 60) + (430 - FOOT + 60) * ease(v) - 140 * math.sin(math.pi * v)
            R.put(cv, R.gift_tile('Whip Cupcake', R.lot('Whip Cupcake', 'black_floor')['model'], bd, R.TILE, t), x, y,
                  0.25 + 0.3 * ease(v), alpha)
        else:
            s = 0.55 * (1 + 0.02 * R.beat_pulse(t, 8))
            R.put(cv, R.gift_tile('Whip Cupcake', R.lot('Whip Cupcake', 'black_floor')['model'], bd, R.TILE, t), x_slot, 430, s, alpha)
            a2 = alpha * appear(t, g + 0.95, 0.25)
            R.put(cv, R.text('Whip Cupcake', 22, 'Heavy'), x_slot, 430 - 300 * s / 2 - 22, 1.0, a2)
            R.put(cv, R.text(bd, 30, 'Heavy', R.WINE if j == 0 else R.INK), x_slot, 430 + 300 * s / 2 + 26, 1.0, a2)
        R.sparkles(cv, t, g + 0.55, chx - 60, FOOT - 60, 160, 10, R.GOLD)


# ------------------------------------------------------------------ сцена: спрос (шоурум, бег)
RUN_START = E.ICONS[0] - 0.45
RUN_X = [(RUN_START, 900), (E.ICONS[0] + 0.15, 790), (E.ICONS[1] + 0.1, 520), (E.ICONS[2] + 0.1, 240), (E.GLOW + 0.05, -260)]
ITEMS = [('card', 830, 1180, 0.95), ('car', 530, 1165, 1.3), ('tux', 230, 1150, 1.15)]   # справа налево — по ходу бега


def run_x(t):
    for (t0, x0), (t1, x1) in zip(RUN_X, RUN_X[1:]):
        if t < t1:
            return x0 + (x1 - x0) * ((t - t0) / (t1 - t0))
    return RUN_X[-1][1]


def demand_mita(t, P):
    warm = dict(tint=(255, 190, 140), k=0.16, rim=(255, 210, 160), rim_k=0.8, reflect=0.16)
    if t < RUN_START:
        return anim.pose('jump_calm'), dict(P, cx=900, **warm)
    u = t - RUN_START
    if u < 0.14:                                           # разворот в профиль: сжатие по x
        k = u / 0.14
        if k < 0.5:
            return anim.pose('jump_calm'), dict(P, cx=900, sx=1 - 1.8 * k, **warm)
        return anim.pose('run_1'), dict(P, cx=900, sx=(k - 0.5) * 2, **warm)
    a = anim.loop(RUN, u, 0.62)
    bob = -10 * abs(math.sin(u / 0.62 * 2 * math.pi))
    return a, dict(P, cx=run_x(t), foot=FOOT + bob, sy=1.0, **warm)


# ------------------------------------------------------------------ сцена: телефон (спальня)
def phone_painter(t):
    c = R.lot('Neko Helmet', 'black_floor')
    def paint(comps, shape):
        out = np.zeros(shape, np.float32)
        sp = biggest(comps)
        if sp is None:
            return out
        if sp['area'] < 2500:                              # видно ребро/обратную сторону — просто свечение
            out[...] = (190, 120, 255, 255)
            return out
        q = anim.quad_of(sp)
        tile = tile_np(c['gift'], c['model'], c['backdrop'], 256, int(t * 12) % 48)
        scr = np.zeros((420, 256, 4), np.uint8)
        scr[...] = (12, 10, 20, 255)
        scr[82:82 + 256] = tile
        return anim.fill_quad(out, None, q, scr, inset=-0.04)
    return paint


# ------------------------------------------------------------------ сцена: график (висит)
def tip(t):
    k = ease((t - E.PRICE - 0.5) / (E.PRICE_UP + 0.4 - E.PRICE - 0.5))
    return 600 + 40 * k, 760 + (340 - 760) * k


def hang_mita(t, P):
    x, y = tip(t)
    if t < E.PRICE + 0.55:
        a = anim.pose('hang_grab')
    elif t < E.PRICE + 0.85:
        a = anim.morph('hang_grab', 'hang_1', ease((t - E.PRICE - 0.55) / 0.3))
    else:
        a = anim.pingpong(HANG, t - E.PRICE - 0.85 + 0.72, 1.9)
    bar = biggest(anim.magenta(a)[1])
    a = anim.replace_magenta(a, lambda comps, shape: np.dstack([np.full(shape[:2], c, np.float32) for c in R.WINE + (255,)]))
    bx, by = bar['c'] if bar else (384, 40)
    return a, dict(P, cx=x, foot=y, base=by, anchor_x=bx, sy=1.0, shadow=t < E.PRICE + 0.7)


def graph_points(t):
    """Линия цены: точки поднимаются вместе с концом (за который держится Мита)."""
    x, y = tip(t)
    f = [(0.0, 0.0), (0.18, 0.12), (0.32, 0.07), (0.48, 0.38), (0.64, 0.52), (0.82, 0.86), (1.0, 1.0)]
    return [(110 + (x - 110) * u, 1440 + (y - 1440) * v) for u, v in f]
