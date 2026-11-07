"""Real product photos for the «настоящий» side (as in 09-price-duel v2: «используй настоящие предметы, их реальные фото»).
Photos come from the same shop pages the prices come from (data/prices_2026-11-06.json), downloaded into
.cache/photos/ (not in Git: third-party images). White studio backgrounds are cut out (flood fill from the
border + hole filling), then every photo becomes a die-cut sticker: white rim + thin ink outline, so it sits
on the paper next to the animated gifts. sprite(kind) -> RGBA ≈ 330 px."""
import functools
import subprocess
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
import paths
import config

CACHE = paths.CACHE / 'photos'
SRC = {   # kind: (url, page, crop box in source px or None, background)
    'lollipop': ('https://img.vkusvill.ru/pim/images/site_BigWebP/20417e66-5a16-46e3-962c-6de8f3270cf5.webp',
        'https://vkusvill.ru/goods/karamel-ledentsovaya-figurnaya-16155/', (150, 68, 366, 228), 'sat'),
    'tamagotchi': ('https://catalog-cdn.detmir.st/media/5cH9dimFDm537r1GqZx3snx6b0zhB4NxtgxL3Fy3xOA=.jpeg',
        'https://www.detmir.ru/product/index/id/7147031/', None, 'white'),
    'pumpkin': ('https://img.vkusvill.ru/pim/images/site/site_BigWebP/ea9c5d7e-7ecd-4392-a695-54c6f333ace8.webp',
        'https://vkusvill.ru/goods/tykva-1212/', None, 'light'),
    'lego_sakura': ('https://catalog-cdn.detmir.st/media/OU-vq_8A-DomX5yMRJb6EyFXPUFf2opiCzT8RqRzNek=.jpeg', 'https://www.detmir.ru/product/index/id/7223896/', None, 'white'),
    'globe': ('https://catalog-cdn.detmir.st/media/1QbXn55xBM1wCWARFsVL-8XuQVBHqJwTG_q3vfrCYEo=.jpeg',
        'https://www.detmir.ru/product/index/id/6384825/', None, 'blue'),
}
BOX = {k: (340, 340) for k in SRC}
GLASS = {'globe': (502, 138, 1532, 1110)}      # ellipse of the glass sphere, source px
RIM = 10          # white sticker rim, px at the final size
INK_W = 4


def fetch(kind):
    url = SRC[kind][0]
    f = CACHE / f'{kind}_30{Path(url.split("?")[0]).suffix}'
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(['curl', '-sSfL', '--retry', '5', '--retry-all-errors', '--retry-delay', '2', '-m', '60',
                        '-A', 'Mozilla/5.0', '-o', str(f), url], check=True)     # the proxy drops some TLS tunnels
    png = f.with_suffix('.png')
    if f.read_bytes()[4:12] in (b'ftypavif', b'ftypavis'):          # the book cover comes as AVIF
        if not png.exists():
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(f), str(png)], check=True)
        return png
    return f


def cutout(kind):
    url, page, crop, bg = SRC[kind]
    im = Image.open(fetch(kind)).convert('RGBA')
    if crop:
        im = im.crop(crop)
    a = np.asarray(im).astype(np.float32)
    if bg == 'alpha':
        mask = ndimage.binary_opening(a[..., 3] > 24, iterations=4)     # drops thin parts (aerial)
    elif bg == 'sat':                                                    # coloured candy on a white plate
        rgb = a[..., :3]
        sat = rgb.max(-1) - rgb.min(-1)
        mask = ndimage.binary_fill_holes(ndimage.binary_closing(sat > 46, iterations=3))
        mask = ndimage.binary_opening(mask, iterations=2)
        lab, n = ndimage.label(mask)
        if n > 1:
            size = ndimage.sum(mask, lab, range(1, n + 1))
            mask = lab == 1 + int(np.argmax(size))
    elif bg == 'blue':                                                   # dark-blue studio backdrop
        rgb = a[..., :3]
        near = ((rgb[..., 2] - rgb[..., 0] > 38) & (rgb.max(-1) < 175)) | ((rgb.max(-1) < 70) & (rgb[..., 2] >= rgb[..., 0]))
        near = ndimage.binary_opening(near, iterations=2)
        lab, _ = ndimage.label(near)
        edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        mask = ~np.isin(lab, edge[edge > 0])
        if kind in GLASS:                                                # blue glass = backdrop colour: add the sphere
            x0, y0, x1, y1 = GLASS[kind]
            yy, xx = np.mgrid[:mask.shape[0], :mask.shape[1]]
            mask |= ((xx - (x0 + x1) / 2) / ((x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) ** 2 <= 1
        mask = ndimage.binary_fill_holes(mask)
        mask = ndimage.binary_opening(mask, iterations=3)
        lab, n = ndimage.label(mask)
        if n > 1:
            size = ndimage.sum(mask, lab, range(1, n + 1))
            mask = lab == 1 + int(np.argmax(size))
    elif bg == 'rect':                                                   # a flat cover: the whole picture
        mask = np.ones(a.shape[:2], bool)
    else:
        rgb = a[..., :3]
        if bg == 'corner':                                               # flat coloured card: key out its colour
            key = np.median(np.concatenate([rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3)]), 0)
            near = np.linalg.norm(rgb - key, axis=-1) < 34
        else:
            lo, sat = (238, 10) if bg == 'white' else (196, 16)          # 'light': grey gradient backdrop
            near = (rgb.min(-1) > lo) & (rgb.max(-1) - rgb.min(-1) < sat)
        lab, _ = ndimage.label(near)
        edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        bgm = np.isin(lab, edge[edge > 0])
        mask = ndimage.binary_fill_holes(~bgm)
        mask = ndimage.binary_opening(mask, iterations=2)
        lab, n = ndimage.label(mask)                                          # keep the big parts only
        if n > 1:
            size = ndimage.sum(mask, lab, range(1, n + 1))
            mask = np.isin(lab, 1 + np.nonzero(size > size.max() * 0.04)[0])
    alpha = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    im.putalpha(alpha)
    return im.crop(im.getbbox())


@functools.lru_cache(None)
def sprite(kind):
    obj = cutout(kind)
    bw, bh = BOX[kind]
    pad = RIM + INK_W + 4
    sc = min((bw - 2 * pad) / obj.width, (bh - 2 * pad) / obj.height)
    obj = obj.resize((max(1, round(obj.width * sc)), max(1, round(obj.height * sc))), Image.LANCZOS)
    W, H = obj.width + 2 * pad, obj.height + 2 * pad
    m = np.zeros((H, W), bool)
    m[pad:pad + obj.height, pad:pad + obj.width] = np.asarray(obj)[..., 3] > 110
    rim = ndimage.binary_dilation(m, iterations=RIM)
    rim = ndimage.binary_fill_holes(rim)
    ink = ndimage.binary_dilation(rim, iterations=INK_W) & ~rim
    out = np.zeros((H, W, 4), np.uint8)
    out[ink] = config.INK + (255,)
    out[rim] = (255, 255, 255, 255)
    st = Image.fromarray(out).filter(ImageFilter.GaussianBlur(0.6))
    st.alpha_composite(obj, (pad, pad))
    canvas = Image.new('RGBA', (max(W, 330), max(H, 340)), (0, 0, 0, 0))       # sits on the plate like the gifts
    canvas.alpha_composite(st, ((canvas.width - W) // 2, canvas.height - H - 6))
    return canvas


if __name__ == '__main__':
    sheet = Image.new('RGBA', (5 * 400, 380), config.BACKGROUND + (255,))
    for k, kind in enumerate(SRC):
        im = sprite(kind)
        sheet.alpha_composite(im, (k * 400 + (400 - im.width) // 2, (380 - im.height) // 2))
    Path('build/review').mkdir(parents=True, exist_ok=True)
    sheet.save('build/review/photos.png')
    print('build/review/photos.png')
