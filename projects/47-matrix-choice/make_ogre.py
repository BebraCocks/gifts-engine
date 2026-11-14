"""Glitch gag (author 2026-11-14): Morpheus turns into a green ogre for an instant. The Fish generation was refused by
moderation, so it is made locally: Morpheus' own head (same face, expression, glasses) and open palms are recoloured to
the ogre's green skin, and the ogre's trumpet ears are cut from the author's picture (assets/src/author_ogre_ref.jpg).
-> assets/sprites/head_ogre.png, hand_L_ogre.png, hand_R_ogre.png"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from scipy import ndimage

HERE = Path(__file__).resolve().parent
SP = HERE / 'assets' / 'sprites'
REF = Image.open(HERE / 'assets' / 'src' / 'author_ogre_ref.jpg').convert('RGB')


def ogre_tone():
    a = np.asarray(REF.crop((70, 30, 110, 70))).reshape(-1, 3).astype(np.float32)     # cheek area of the face
    hsv = np.asarray(REF.crop((70, 30, 110, 70)).convert('HSV')).reshape(-1, 3).astype(np.float32)
    return np.median(hsv[:, 0]), np.median(hsv[:, 1])


def recolor(im, hue, sat):
    """Skin → ogre green; dark low-saturation pixels (glasses, pupils, nostrils) are kept as they are."""
    rgba = np.asarray(im).copy()
    rgb = Image.fromarray(rgba[..., :3])
    hsv = np.asarray(rgb.convert('HSV')).astype(np.float32)
    v = hsv[..., 2]
    s = hsv[..., 1]
    skin = (v > 45) & ((s > 40) | (v > 150))                     # highlights too (they were pink)
    k = np.clip((v - 45) / 30, 0, 1) * np.maximum(np.clip((s - 40) / 30, 0, 1), np.clip((v - 150) / 40, 0, 1))
    k = ndimage.gaussian_filter(k * skin, 1.0)
    new = hsv.copy()
    new[..., 0] = 52                                              # yellow-green of the ogre (PIL hue 0..255 ≈ 73°)
    new[..., 1] = np.clip(np.maximum(0.55 * sat + 0.35 * s, 90), 0, 255)
    new[..., 2] = np.clip(v * 1.04 + 6, 0, 235)
    out = np.asarray(Image.fromarray(new.astype(np.uint8), 'HSV').convert('RGB')).astype(np.float32)
    mix = rgba[..., :3] * (1 - k[..., None]) + out * k[..., None]
    rgba[..., :3] = np.clip(mix, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba)


def drawn_ear(h, flip=False):
    """A crisp trumpet ear in the same green (the picture's ears are only ~20 px): stalk + flared cup + shading."""
    S = 4
    w, hh = 150, 120
    im = Image.new('RGBA', (w * S, hh * S), (0, 0, 0, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    base = (150, 168, 52)
    dark = (96, 112, 30)
    d.polygon([(150 * S, 74 * S), (150 * S, 104 * S), (88 * S, 74 * S), (80 * S, 50 * S)], fill=base + (255,))   # short thick stalk
    d.ellipse([34 * S, 12 * S, 104 * S, 72 * S], fill=base + (255,))                                         # flared cup
    d.ellipse([46 * S, 22 * S, 92 * S, 62 * S], fill=dark + (255,))
    d.ellipse([56 * S, 30 * S, 82 * S, 54 * S], fill=(70, 84, 22, 255))
    im = im.resize((w, hh), Image.LANCZOS)
    k = h / 531 * 1.15
    im = im.resize((int(w * k), int(hh * k)), Image.LANCZOS)
    im = im.rotate(-32, expand=True, resample=Image.BICUBIC)                  # cup up and out
    return ImageOps.mirror(im) if flip else im


def ear(box):
    """Cut one trumpet ear from the author's picture by colour (green on white)."""
    im = REF.crop(box)
    a = np.asarray(im).astype(np.float32)
    g = (a[..., 1] > a[..., 2] + 30) & (a.min(-1) < 235)
    g = ndimage.binary_fill_holes(ndimage.binary_opening(g, iterations=1))
    lab, n = ndimage.label(g)
    if n > 1:
        sz = ndimage.sum(g, lab, range(1, n + 1))
        g = lab == 1 + int(np.argmax(sz))
    rgba = im.convert('RGBA')
    rgba.putalpha(Image.fromarray((g * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5)))
    rgba = rgba.crop(rgba.getbbox())
    return rgba.resize((rgba.width * 6, rgba.height * 6), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.2))


if __name__ == '__main__':
    hue, sat = ogre_tone()
    print('ogre hue/sat', hue, sat)
    head = recolor(Image.open(SP / 'head_calm3.png').convert('RGBA'), hue, sat)
    W, H = head.size
    eL, eR = drawn_ear(H), drawn_ear(H, flip=True)
    canvas = Image.new('RGBA', (W + 2 * eL.width, H + 40), (0, 0, 0, 0))
    ox, oy = eL.width, 20
    ey = oy + int(H * 0.36)                                  # at the real ears' height, covering them
    canvas.alpha_composite(eL, (ox + 92 - eL.width, ey - eL.height // 2 - 6))
    canvas.alpha_composite(eR, (ox + W - 92, ey - eR.height // 2 - 6))
    canvas.alpha_composite(head, (ox, oy))
    canvas = canvas.crop(canvas.getbbox())
    canvas.save(SP / 'head_ogre.png')
    print('head', canvas.size, '(base head', head.size, ')')
    for side in ('L', 'R'):
        hand = recolor(Image.open(SP / f'hand_{side}_close_0.png').convert('RGBA'), hue, sat)
        hand.crop(hand.getbbox()).save(SP / f'hand_{side}_ogre.png')
    prev = Image.new('RGB', (canvas.width + 700, max(canvas.height, 520)), (255, 255, 255))
    prev.paste(canvas, (0, 0), canvas)
    h = Image.open(SP / 'hand_L_ogre.png')
    prev.paste(h, (canvas.width + 40, 40), h)
    prev.save(HERE / 'build' / 'review' / 'ogre_preview.png')
