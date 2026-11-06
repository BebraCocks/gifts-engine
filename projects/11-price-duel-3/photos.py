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
SRC = {   # kind: (url, page, crop box in source px or None, background: 'white' | 'light' | 'alpha' | 'rect')
    'brownie': ('https://img.vkusvill.ru/pim/images/site_for_feed/4d824d0a-0610-42c5-969f-7cc8b648a292.jpg',
                'https://vkusvill.ru/goods/brauni-shokoladnyy-bez-pshenichnoy-muki-75588/', (230, 150, 850, 610), 'rect'),
    'pen': ('https://content.img-gorod.ru/pim/products/images/df/5d/018ed324-0bc4-7667-9ec1-939102d8df5d.jpg'
            '?width=608&height=876',
            'https://www.chitai-gorod.ru/product/ruchka-sharikovaya-parker-jotter-stainless-steel-gt-podarochnaya-sinyaya-242818',
            None, 'white'),
    'notepad': ('https://content.img-gorod.ru/pim/products/images/7e/65/019c0b79-52c5-7e67-8b14-0029a1947e65.jpg'
                '?width=608&height=876',
                'https://www.chitai-gorod.ru/product/bloknot-a6-80l-kl-pastel-assorti-plast-obl-spiral-yoi-3096621',
                None, 'white'),
    'dyson': ('https://cdn.iport.ru/iblock/d1f/d1fe0e831db24a53b6ec01f3fc94f030/888dbd2ec523c7931de31fcc1543f408.jpg',
              'https://www.iport.ru/products/productID143566/', None, 'white'),
    'ipad': ('https://cdn.iport.ru/iblock/3ab/3ab066f810104d856c29a555025df161/c767b3360d880b22208f065da6cbdaca.jpg',
             'https://www.iport.ru/products/productID144927/', None, 'white'),
}
BOX = {'brownie': (340, 300), 'pen': (300, 360), 'notepad': (290, 350), 'dyson': (360, 340), 'ipad': (330, 340)}
RIM = 10          # white sticker rim, px at the final size
INK_W = 4


def fetch(kind):
    url = SRC[kind][0]
    f = CACHE / f'{kind}_11{Path(url.split("?")[0]).suffix}'
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            f.write_bytes(r.read())
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
    elif bg == 'rect':                                                   # a flat cover: the whole picture
        mask = np.ones(a.shape[:2], bool)
    else:
        rgb = a[..., :3]
        lo, sat = (238, 10) if bg == 'white' else (196, 16)              # 'light': grey gradient backdrop
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
