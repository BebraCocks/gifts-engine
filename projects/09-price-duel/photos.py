"""Real product photos for the «жизнь» side (author, 2026-11-06: «используй настоящие предметы, их реальные фото»).
Photos come from the same shop pages the prices come from (data/prices_2026-11-06.json), downloaded into
.cache/photos/ (not in Git: third-party images). White studio backgrounds are cut out (flood fill from the
border + hole filling), then every photo becomes a die-cut sticker: white rim + thin ink outline, so it sits
on the paper next to the animated gifts. sprite(kind) -> RGBA ≈ 330 px."""
import functools
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
SRC = {   # kind: (url, page, crop box in source px or None, background: 'white' | 'alpha')
    'chips': ('https://img.vkusvill.ru/pim/images/site/site_for_feed/5f3b7192-9464-43f8-9407-37417cceaa2d.png',
              'https://vkusvill.ru/goods/chipsy-kartofelnye-lay-s-so-vkusom-kraba-140-g-114240.html', None, 'white'),
    'watch': ('https://cdn.iport.ru/iblock/d24/d248b58d39d175ebe5cb2ea3d774d2a7/2fe3ae832da2e3c2d8d9aefe0dd01162.jpg',
              'https://www.iport.ru/products/productID149302/', None, 'white'),
    'airpods': ('https://cdn.iport.ru/iblock/b7e/b7e817e5be49fd77cc608544380808bb/c4d63fb44aed37dca89ec28df88c2f4c.jpg',
                'https://www.iport.ru/products/productID149174/', None, 'white'),
    'iphone': ('https://cdn.iport.ru/iblock/96b/96b1ab72e5ce5ddac86cd4e6a8a18233/075a4dbf96eb4c32d255b694bb877a58.png',
               'https://www.iport.ru/products/productID156657/', (0, 0, 700, 1000), 'alpha'),
    'granta': ('https://www.avtogermes.ru/images/marks/lada/granta/i-restajling/colors/493/'
               'lada-granta-sedan-i-restajling-sinij-metallik.af4944b3bfe9c37e28b6e05fe56b70df.png',
               'https://www.avtogermes.ru/sale/new/lada/granta/', None, 'alpha'),
}
BOX = {'chips': (330, 360), 'watch': (310, 360), 'airpods': (350, 330), 'iphone': (290, 370), 'granta': (372, 290)}
RIM = 10          # white sticker rim, px at the final size
INK_W = 4


def fetch(kind):
    url = SRC[kind][0]
    f = CACHE / f'{kind}{Path(url).suffix}'
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            f.write_bytes(r.read())
    return f


def cutout(kind):
    url, page, crop, bg = SRC[kind]
    im = Image.open(fetch(kind)).convert('RGBA')
    if crop:
        im = im.crop(crop)
    a = np.asarray(im).astype(np.float32)
    if bg == 'alpha':
        mask = ndimage.binary_opening(a[..., 3] > 24, iterations=4)     # drops thin parts (aerial)
    else:
        rgb = a[..., :3]
        near = (rgb.min(-1) > 238) & (rgb.max(-1) - rgb.min(-1) < 10)        # studio white
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
