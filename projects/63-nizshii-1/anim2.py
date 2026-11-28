"""Дополнительные ассеты части 1 (нуар): силуэты людей с контровым светом, коридор, полусфера, ниша-кресло,
настенный экран, зал со слизью, ведро, №444, медблок, клукс, автоматы, капсула. Кеш — build/anim_cache."""
import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
from scipy import ndimage

import anim
import style_probes as sp
from anim import cached, shade_rgba, big_mask

W, H = 1080, 1920
F = sp.F


def font(name, size):
    return ImageFont.truetype(str(F / name), size)


# ------------------------------------------------------------------ силуэт человека
def silhouette(name, arms=(True, True), legs=(True, True), hair=None, wide=1.0, body=(28, 30, 36), rim=1.6,
               lying=False, ears=False):
    """тёмная фигура с холодным контровым светом; конечности можно убрать (черви, зомби, гоблины)"""
    def make():
        P = sp.parts()
        keys = ['torso', 'neck', 'head', 'shorts']
        if arms[0]:
            keys.append('arm_l')
        if arms[1]:
            keys.append('arm_r')
        if legs[0]:
            keys.append('leg_l')
        if legs[1]:
            keys.append('leg_r')
        m = Image.new('L', (W, H), 0)
        for k in keys:
            m = ImageChops.lighter(m, P[k])
        d = ImageDraw.Draw(m)
        if hair == 'long':
            d.polygon([(450, 600), (540, 545), (630, 600), (650, 800), (600, 760), (480, 760), (430, 800)], fill=255)
        elif hair == 'spiky':
            for k in range(7):
                x = 470 + k * 22
                d.polygon([(x, 600), (x + 11, 540 - (k % 2) * 20), (x + 22, 600)], fill=255)
        if ears:
            d.polygon([(462, 660), (420, 590), (472, 640)], fill=255)
            d.polygon([(618, 660), (660, 590), (608, 640)], fill=255)
        for (x, y) in (((352, 872),) if not arms[0] else ()) + (((728, 872),) if not arms[1] else ()):
            d.ellipse((x - 34, y - 34, x + 34, y + 34), fill=255)          # культя
        if wide != 1.0:
            nw = int(W * wide)
            c = Image.new('L', (max(W, nw), H), 0)
            c.paste(m.resize((nw, H), Image.LANCZOS), ((max(W, nw) - nw) // 2, 0))
            m = c
        im = shade_rgba(m, body, amb=0.25, rim_k=rim)
        bbox = im.getchannel('A').getbbox()
        im = im.crop(bbox)
        if lying:
            im = im.rotate(90, Image.BICUBIC, expand=True)
        return im
    return cached(f'sil_{name}', make)


# ------------------------------------------------------------------ коридор
def corridor():
    """коридор в перспективе, металл, лампы, рельс системы под потолком"""
    def make():
        im = Image.new('RGB', (W, H))
        sp.corridor(ImageDraw.Draw(im), ((34, 40, 48), (28, 33, 40), (22, 25, 30), (16, 18, 22), (50, 58, 68), (210, 230, 255)))
        a = np.asarray(im, np.float32)
        yy, xx = np.mgrid[0:H, 0:W]
        a += np.exp(-(((xx - 540) / 300) ** 2 + ((yy - 760) / 520) ** 2))[..., None] * np.array([20, 32, 50])
        a += ndimage.gaussian_filter(np.random.default_rng(3).random((H, W)), 1.5)[..., None] * 14 - 7
        lamps = ndimage.gaussian_filter((a.mean(-1) > 200).astype(np.float32), 18)[..., None] * np.array([90, 120, 160])
        return Image.fromarray(np.clip(a + lamps, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('corridor2', make)


def sphere():
    """полусфера системы с объективами"""
    def make():
        im = Image.new('RGBA', (520, 340), (0, 0, 0, 0))
        m = big_mask((520, 340), lambda d, s: d.chord((20 * s, -240 * s, 500 * s, 330 * s), 0, 180, fill=255))
        im.alpha_composite(shade_rgba(m, (70, 76, 86), amb=0.3))
        d = ImageDraw.Draw(im)
        for k, (x, y) in enumerate([(120, 120), (200, 170), (260, 190), (320, 170), (400, 120), (170, 80), (350, 80),
                                    (260, 110), (90, 60), (430, 60)]):
            r = 22 if k % 3 else 30
            d.ellipse((x - r, y - r, x + r, y + r), fill=(12, 12, 16), outline=(140, 150, 165), width=4)
            d.ellipse((x - r * 0.4, y - r * 0.4, x + r * 0.4, y + r * 0.4), fill=(200, 40, 40) if k % 2 else (60, 140, 220))
        d.rectangle((240, 0, 280, 30), fill=(60, 64, 72))
        return im
    return cached('sphere', make)


# ------------------------------------------------------------------ ниша-кресло
def niche():
    def make():
        im = Image.new('RGB', (W, H), (10, 12, 15))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((140, 260, 940, 1700), 40, fill=(34, 40, 46), outline=(80, 200, 140), width=10)
        d.rounded_rectangle((170, 290, 910, 1670), 30, fill=(46, 54, 62))
        # дырчатое кресло
        d.rounded_rectangle((330, 640, 750, 1380), 60, fill=(70, 78, 88))
        for y in range(690, 1340, 46):
            for x in range(370, 720, 46):
                d.ellipse((x, y, x + 22, y + 22), fill=(26, 30, 36))
        d.rounded_rectangle((250, 1000, 380, 1100), 20, fill=(84, 92, 102))       # подлокотники
        d.rounded_rectangle((700, 1000, 830, 1100), 20, fill=(84, 92, 102))
        d.rectangle((520, 1380, 560, 1640), fill=(60, 66, 74))                       # ножка
        d.rectangle((420, 330, 660, 420), fill=(10, 30, 20))                          # таймер
        d.text((540, 375), '01:59', font=font('JetBrainsMono-Bold.ttf', 56), fill=(110, 255, 160), anchor='mm')
        a = np.asarray(im, np.float32)
        yy, xx = np.mgrid[0:H, 0:W]
        a = a * (0.45 + 0.8 * np.exp(-(((xx - 540) / 420) ** 2 + ((yy - 700) / 700) ** 2)))[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('niche', make)


def cup(level):
    im = Image.new('RGBA', (160, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    top = 200 - 180 * level
    d.rectangle((24, top, 136, 200), fill=(120, 180, 230, 160))
    d.polygon([(14, 10), (146, 10), (136, 210), (24, 210)], outline=(220, 235, 250, 220), width=5)
    d.line((24, top, 136, top), fill=(200, 230, 255, 230), width=4)
    return im


def cube():
    def make():
        m = big_mask((120, 120), lambda d, s: d.rounded_rectangle((10 * s, 10 * s, 110 * s, 110 * s), 14 * s, fill=255))
        return shade_rgba(m, (214, 196, 140), amb=0.35)
    return cached('cube', make)


# ------------------------------------------------------------------ экран
def wall_screen(t_on, grid=None, text=None, col=(255, 214, 120)):
    """настенный экран; grid — список (клетка, 'X'|'O') для крестиков-ноликов"""
    im = Image.new('RGBA', (760, 520), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 760, 520), 24, fill=(18, 18, 22), outline=(70, 76, 86), width=12)
    if t_on <= 0:
        return im
    glow = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((24, 24, 736, 496), 14, fill=(80, 70, 40, int(255 * min(1, t_on))))
    im.alpha_composite(glow)
    if grid is not None:
        x0, y0, c = 230, 70, 130
        for k in range(1, 3):
            d.line((x0 + k * c, y0, x0 + k * c, y0 + 3 * c), fill=(250, 240, 210), width=8)
            d.line((x0, y0 + k * c, x0 + 3 * c, y0 + k * c), fill=(250, 240, 210), width=8)
        for cell, v in grid:
            cx, cy = x0 + (cell % 3) * c + c / 2, y0 + (cell // 3) * c + c / 2
            if v == 'X':
                d.line((cx - 40, cy - 40, cx + 40, cy + 40), fill=(240, 70, 60), width=14)
                d.line((cx - 40, cy + 40, cx + 40, cy - 40), fill=(240, 70, 60), width=14)
            else:
                d.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), outline=(120, 200, 255), width=12)
    if text:
        for k, (txt, size) in enumerate(text):
            d.text((380, 150 + k * 170 if len(text) > 1 else 260), txt, font=font('Oswald-700.ttf', size), fill=col,
                   anchor='mm')
    return im


# ------------------------------------------------------------------ зал со слизью
def slime_room():
    def make():
        im = Image.new('RGB', (W, H), (40, 44, 46))
        d = ImageDraw.Draw(im)
        d.polygon([(0, 0), (W, 0), (W, 1250), (0, 1250)], fill=(52, 56, 58))
        d.polygon([(0, 1250), (W, 1250), (W, H), (0, H)], fill=(36, 40, 42))
        r = np.random.default_rng(8)
        for k in range(26):                                     # потёки слизи
            x = r.uniform(0, W)
            w = r.uniform(30, 120)
            hgt = r.uniform(300, 1200)
            d.rounded_rectangle((x, -20, x + w, hgt), int(w / 2), fill=(118, 122, 118))
        for k in range(8):                                      # лужи
            x, y = r.uniform(0, W), r.uniform(1300, 1850)
            d.ellipse((x - 220, y - 50, x + 220, y + 50), fill=(96, 100, 98))
        a = np.asarray(im, np.float32)
        a += ndimage.gaussian_filter(r.random((H, W)), 3)[..., None] * 30 - 15
        a = ndimage.gaussian_filter(a, (2, 2, 0))
        yy, xx = np.mgrid[0:H, 0:W]
        a *= (0.4 + 0.75 * np.exp(-(((xx - 540) / 600) ** 2 + ((yy - 700) / 900) ** 2)))[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('slime_room', make)


def bucket():
    def make():
        m = big_mask((240, 300), lambda d, s: d.rectangle((20 * s, 60 * s, 220 * s, 290 * s), fill=255))
        im = shade_rgba(m, (170, 176, 182), amb=0.3)
        d = ImageDraw.Draw(im)
        d.ellipse((20, 40, 220, 90), fill=(110, 114, 110), outline=(190, 196, 200), width=5)
        d.arc((30, -60, 210, 120), 200, 340, fill=(160, 166, 172), width=6)
        return im
    return cached('bucket', make)


# ------------------------------------------------------------------ №444: худой, длинные волосы, борода
def head444():
    def make():
        im = anim.hero_head_base().copy()
        hair = big_mask((anim.FACE_W, anim.FACE_H), lambda d, s: (
            d.ellipse((220 * s, 180 * s, 860 * s, 760 * s), fill=255),
            d.rectangle((220 * s, 470 * s, 330 * s, 1150 * s), fill=255),
            d.rectangle((750 * s, 470 * s, 860 * s, 1150 * s), fill=255)))
        cut = big_mask((anim.FACE_W, anim.FACE_H), lambda d, s: d.ellipse((300 * s, 420 * s, 780 * s, 1200 * s), fill=255))
        hair = ImageChops.subtract(hair, cut)
        im.alpha_composite(shade_rgba(hair, (60, 46, 36), amb=0.35))
        return im
    return cached('head444', make)


def beard(jaw=0.0):
    """борода как отдельный слой: «рот» двигается сдвигом бороды вниз"""
    def make():
        m = big_mask((anim.FACE_W, anim.FACE_H), lambda d, s: d.polygon(
            [(x * s, y * s) for x, y in [(290, 760), (360, 900), (460, 1080), (540, 1140), (620, 1080), (720, 900),
                                         (790, 760), (700, 880), (600, 900), (540, 880), (480, 900), (380, 880)]], fill=255))
        return shade_rgba(m, (58, 44, 34), amb=0.35)
    b = cached('beard444', make)
    if jaw <= 0.02:
        return b, 0
    return b, int(24 * jaw)


# ------------------------------------------------------------------ медблок, клукс, автоматы, капсула
def medblock():
    def make():
        im = corridor().copy()
        d = ImageDraw.Draw(im)
        d.rectangle((300, 520, 780, 1500), fill=(30, 32, 36), outline=(110, 40, 40), width=10)
        d.rectangle((500, 600, 580, 820), fill=(200, 40, 40))
        d.rectangle((430, 670, 650, 750), fill=(200, 40, 40))
        g = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((300, 420, 780, 1000), fill=(255, 40, 30, 70))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(80)))
        return im
    return cached('medblock', make)


def klux():
    def make():
        im = Image.new('RGB', (W, H), (14, 16, 20))
        d = ImageDraw.Draw(im)
        vp = (540, 700)
        d.polygon([(0, H), (vp[0] - 500, vp[1] + 80), (vp[0] + 500, vp[1] + 80), (W, H)], fill=(34, 38, 44))
        for row in range(7):                                    # ряды столиков
            f = (row + 1) / 8
            y = vp[1] + 80 + (H - vp[1] - 80) * f ** 1.6
            for col in range(-3, 4):
                x = vp[0] + col * 260 * f ** 1.6 * 2.2
                w = 120 * f ** 1.6 * 2.2
                d.rectangle((x - w, y - w * 0.25, x + w, y), fill=(64, 70, 78))
        for k in range(12):                                     # капсулы-соты слева и справа
            for j in range(2):
                x = 40 + j * 130
                y = 300 + k * 60
                d.rounded_rectangle((x, y, x + 110, y + 50), 10, fill=(40, 46, 52), outline=(90, 200, 140) if (k + j) % 3 else (60, 66, 74), width=3)
        for k in range(4):                                      # автоматы справа
            x = 720 + k * 85
            d.rectangle((x, 320, x + 80, 820), fill=(30, 34, 40), outline=(70, 76, 86), width=3)
            d.rectangle((x + 8, 340, x + 72, 700), fill=(160, 200, 220) if k < 3 else (220, 120, 80))
        a = np.asarray(im, np.float32)
        glow = ndimage.gaussian_filter(a, (30, 30, 0))
        return Image.fromarray(np.clip(a + glow * 0.6, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('klux', make)


def vending():
    """крупно автомат с оружием: дубинки, ножи, шокеры за стеклом"""
    def make():
        im = Image.new('RGB', (W, H), (12, 14, 18))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((160, 200, 920, 1760), 30, fill=(56, 70, 52), outline=(90, 110, 80), width=12)
        d.rectangle((220, 280, 860, 1380), fill=(170, 190, 200))
        for row in range(4):
            y = 330 + row * 260
            d.line((230, y + 200, 850, y + 200), fill=(90, 100, 110), width=8)
            for col in range(3):
                x = 300 + col * 210
                if row == 0:                                    # дубинки
                    d.rounded_rectangle((x - 18, y, x + 18, y + 190), 14, fill=(30, 30, 34))
                elif row == 1:                                  # ножи
                    d.polygon([(x - 10, y + 190), (x + 10, y + 190), (x + 6, y + 70), (x, y), (x - 6, y + 70)], fill=(200, 210, 220))
                    d.rectangle((x - 14, y + 150, x + 14, y + 200), fill=(40, 30, 26))
                elif row == 2:                                  # шокеры
                    d.rounded_rectangle((x - 30, y + 40, x + 30, y + 190), 12, fill=(240, 200, 40))
                    d.line((x - 12, y + 40, x - 12, y + 10), fill=(220, 220, 230), width=6)
                    d.line((x + 12, y + 40, x + 12, y + 10), fill=(220, 220, 230), width=6)
                else:                                           # дымовые шашки
                    d.rounded_rectangle((x - 36, y + 70, x + 36, y + 190), 10, fill=(120, 130, 120))
        d.rectangle((340, 1440, 740, 1560), fill=(20, 20, 24))
        a = np.asarray(im, np.float32)
        yy, xx = np.mgrid[0:H, 0:W]
        a *= (0.4 + 0.8 * np.exp(-(((xx - 540) / 500) ** 2 + ((yy - 800) / 800) ** 2)))[..., None]
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return cached('vending', make)


def capsule_wall():
    def make():
        im = Image.new('RGB', (W, H), (16, 18, 22))
        d = ImageDraw.Draw(im)
        for k in range(2):
            y = 300 + k * 700
            for x in (60, 560):
                d.rounded_rectangle((x, y, x + 460, y + 560), 30, fill=(46, 52, 58), outline=(70, 78, 88), width=8)
                d.ellipse((x + 200, y + 480, x + 260, y + 540), fill=(90, 220, 140) if (k + x) % 3 else (220, 70, 60))
        d.rectangle((80, 960, 1000, 990), fill=(60, 66, 74))
        return im.convert('RGBA')
    return cached('capsule_wall', make)
