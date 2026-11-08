"""39-lucky-cells: real product photos (15 things, data/prices_2026-11-08.json).
Real product photos for the «настоящий» side (as in 09-price-duel v2: «используй настоящие предметы, их реальные фото»).
Photos come from the same shop pages the prices come from (data/prices_2026-11-08.json), downloaded into
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
SRC = {   # kind: (url, page, crop box in source px or None, background) — data/prices_2026-11-08.json
    'crackers': ('https://img.vkusvill.ru/pim/images/site_for_feed/8d61f739-6af7-4b29-b1e4-e83fc7b9aec3.jpg',
        'https://vkusvill.ru/goods/sukhariki-rzhanye-s-chesnokom-i-solyu-43322.html', (300, 40, 780, 690), 'light'),
    'book': ('https://content.img-gorod.ru/pim/products/images/62/a8/018f5cb0-84aa-78c9-a36c-9d49401462a8.jpg',
        'https://www.chitai-gorod.ru/product/garri-potter-i-filosofskiy-kamen-2405917', None, 'white'),
    'airpods': ('https://cdn.iport.ru/iblock/a9b/a9b7638df32d35d6e3571e1e9bce6839/3b0279de3c6742d03d6b44137a70ac77.jpg',
        'https://www.iport.ru/products/productID149174/', None, 'white'),
    'icecream': ('https://img.vkusvill.ru/pim/images/site_for_feed/2b97071f-9340-48c1-b748-a617b78e6fc3.jpg',
        'https://vkusvill.ru/goods/plombir-v-rozhke-klubnika-27166/', (230, 40, 870, 690), 'light'),
    'bear': ('https://content.img-gorod.ru/pim/products/images/10/5b/019e8375-92c6-7162-b48b-5435b6c0105b.jpg',
        'https://www.chitai-gorod.ru/product/magkaa-igruska-medved-33sm-12-191025-i13-3132979', (150, 420, 1500, 2000), 'corner'),
    'watch': ('https://cdn.iport.ru/iblock/bcd/bcdbb5a219cd79072ff58c94c73bba00/ec02c8fd5cac7a77153f5e565f9485e8.jpg',
        'https://www.iport.ru/products/productID149302/', None, 'white'),
    'chips': ('https://img.vkusvill.ru/pim/images/site/site_for_feed/5f3b7192-9464-43f8-9407-37417cceaa2d.png',
        'https://vkusvill.ru/goods/chipsy-kartofelnye-lay-s-so-vkusom-kraba-140-g-114240.html', None, 'white'),
    'lego': ('https://content.img-gorod.ru/pim/products/images/0e/40/019957af-b8ba-782d-b028-beea28c70e40.jpg',
        'https://www.chitai-gorod.ru/product/76303-konstruktor-detskij-lego-dc-tumbler-betmena-protiv-dvulikogo-i-dzokera-429-detalej-vozrast-8-3126514', None, 'white'),
    'iphone': ('https://cdn.iport.ru/iblock/515/515a5ff5f18a935bf05bcd3e483779f3/df37e6f0f3652eba8aef1d503a6fc820.png',
        'https://www.iport.ru/products/productID156657/', None, 'corner'),
    'ramen': ('https://img.vkusvill.ru/pim/images/site/site_for_feed/ac43af53-5815-4fed-a57c-afeb94d8ec1e.jpg',
        'https://vkusvill.ru/goods/lapsha-ottogi-syrnyy-ramen-62-g-93229.html', None, 'white'),
    'pen': ('https://content.img-gorod.ru/pim/products/images/df/5d/018ed324-0bc4-7667-9ec1-939102d8df5d.jpg',
        'https://www.chitai-gorod.ru/product/ruchka-sharikovaya-parker-jotter-stainless-steel-gt-podarochnaya-sinyaya-242818', None, 'white'),
    'dyson': ('https://cdn.iport.ru/iblock/d1f/d1fe0e831db24a53b6ec01f3fc94f030/888dbd2ec523c7931de31fcc1543f408.jpg',
        'https://www.iport.ru/products/productID143566/', None, 'white'),
    'cookie': ('https://img.vkusvill.ru/pim/images/site/site_for_feed/bbd8cad5-cad5-4682-aa7b-32def877f05c.jpg',
        'https://vkusvill.ru/goods/pechene-zatyazhnoe-imbirnoe-63631/', (180, 60, 900, 660), 'light'),
    'airpodsmax': ('https://cdn.iport.ru/iblock/ac8/ac8a78719106991954c58fe5912a08ae/af6accea4d375c28bacd0351625f8c0f.jpg',
        'https://www.iport.ru/products/productID126901/', None, 'white'),
    'macbook': ('https://cdn.iport.ru/iblock/51f/51f0a87413258c6bad5917c28cb8655d/a01f2462158fc6dbb1489c1a4468fe52.jpg',
        'https://www.iport.ru/products/productID150214/', None, 'white'),
}
BOX = {k: (250, 250) for k in SRC}       # fits a 300 px card
GLASS = {}
SAT = {}        # (saturation threshold, closing): white stripes between red ones
RING = {}   # wreath on a door: outer ellipse (inner unused), source px
RIM = 10          # white sticker rim, px at the final size
INK_W = 4


def fetch(kind):
    url = SRC[kind][0]
    f = CACHE / f'{kind}_39{Path(url.split("?")[0]).suffix}'
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
        mask = ndimage.binary_fill_holes(ndimage.binary_closing(sat > SAT.get(kind, (46, 3))[0], iterations=SAT.get(kind, (46, 3))[1]))
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
    elif bg == 'green':                                                  # green tree on a warm grey-brown backdrop
        rgb = a[..., :3]
        mask = (rgb[..., 1] - rgb[..., 0] > 6) & (rgb[..., 1] > rgb[..., 2] + 4)
        mask = ndimage.binary_opening(ndimage.binary_closing(mask, iterations=2), iterations=1)
        lab, n = ndimage.label(mask)
        if n > 1:
            size = ndimage.sum(mask, lab, range(1, n + 1))
            mask = np.isin(lab, 1 + np.nonzero(size > size.max() * 0.02)[0])
    elif bg == 'ring':                                                   # round wreath on a busy photo: two ellipses
        (o0, o1, o2, o3), (i0, i1, i2, i3) = RING[kind]
        yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
        ell = lambda x0, y0, x1, y1: ((xx - (x0 + x1) / 2) / ((x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) ** 2 <= 1
        mask = ell(o0, o1, o2, o3)          # the door shows through the middle (a hole would become a white disc on the sticker)
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
    return st


if __name__ == '__main__':
    sheet = Image.new('RGBA', (5 * 300, 3 * 300), config.BACKGROUND + (255,))
    for k, kind in enumerate(SRC):
        im = sprite(kind)
        sheet.alpha_composite(im, ((k % 5) * 300 + (300 - im.width) // 2, (k // 5) * 300 + (300 - im.height) // 2))
    Path('build/review').mkdir(parents=True, exist_ok=True)
    sheet.save('build/review/photos.png')
    print('build/review/photos.png')
