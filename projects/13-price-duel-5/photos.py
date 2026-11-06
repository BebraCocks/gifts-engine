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
    'lego_orchid': ('https://content.img-gorod.ru/pim/products/images/46/1a/01985af8-e057-727d-9211-ba617b09461a.jpg?width=608&height=876',
        'https://www.chitai-gorod.ru/product/konstruktor-lego-mini-orchid-3118441', None, 'white'),
    'stockwell': ('https://cdn.iport.ru/iblock/36e/36e3e7e960924364e2509cd8748efc36/dc36e3273e4f73975a540df49171b032.png',
        'https://www.iport.ru/products/productID105634/', None, 'alpha'),
    'lego_batman': ('https://content.img-gorod.ru/pim/products/images/0e/40/019957af-b8ba-782d-b028-beea28c70e40.jpg?width=608&height=876',
        'https://www.chitai-gorod.ru/product/76303-konstruktor-detskij-lego-dc-tumbler-betmena-protiv-dvulikogo-i-dzokera-429-detalej-vozrast-8-3126514', None, 'white'),
    'airpodsmax': ('https://cdn.iport.ru/iblock/ac8/ac8a78719106991954c58fe5912a08ae/af6accea4d375c28bacd0351625f8c0f.jpg',
        'https://www.iport.ru/products/productID126901/', None, 'white'),
    'macbookpro': ('https://cdn.iport.ru/iblock/51f/51f0a87413258c6bad5917c28cb8655d/a01f2462158fc6dbb1489c1a4468fe52.jpg',
        'https://www.iport.ru/products/productID150214/', None, 'white'),
}
BOX = {'lego_orchid': (340, 340), 'stockwell': (340, 340), 'lego_batman': (340, 340), 'airpodsmax': (340, 340), 'macbookpro': (340, 340)}
RIM = 10          # white sticker rim, px at the final size
INK_W = 4


def fetch(kind):
    url = SRC[kind][0]
    f = CACHE / f'{kind}_13{Path(url.split("?")[0]).suffix}'
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
