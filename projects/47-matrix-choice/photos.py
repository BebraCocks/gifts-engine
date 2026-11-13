"""Real product photos for the «in life» side (red halo). Sources = the shop pages the prices come from
(data/prices_2026-11-13_v2.json); files in .cache/photos47/ (not in Git: third-party images).
White studio backgrounds are cut out (flood fill from the border); the cactus is cut from a table photo by saturation.
sprite(kind) -> RGBA cut-out, longest side ≈ BOX px, with a soft contact shadow."""
import functools
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
import paths

CACHE = paths.CACHE / 'photos47'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120'
SRC = {   # kind: (file, url, page, crop box or None, mode)
    'chess': ('chess_2.jpg', 'https://holod.ru/pics/clean/big/59/1186559_2.jpg',
              'https://www.holodilnik.ru/kids/educational_games/zolotaya_skazka/664671/', None, 'white'),
    'drill': ('drill_3122705.jpg', 'https://holod.ru/pics/clean/big/69/1282769_3122705.jpg',
              'https://www.holodilnik.ru/construction_repair/drills_and_screwdrivers/anycons/ac-id65l2_0833804/', None, 'white'),
    'cactus': ('cactus_0.jpg', 'https://spb.bazacvetov24.ru/products/8523/ekhinokaktus-gruzoni-v-gorshke-10-005_9375_lg.jpg',
               'https://spb.bazacvetov24.ru/flowers/ekhinokaktus-gruzoni-v-gorshke-10-005/', (500, 655, 685, 898), 'sat'),
    'telescope': ('telescope_0.jpg', 'https://holod.ru/pics/clean/big/55/896755_0.jpg',
                  'https://www.holodilnik.ru/cottage_repair/telescopes/praktica/antares_70_700az_chernyy_91170700/', None, 'white'),
    'chainsaw': ('chainsaw_1.jpg', 'https://holod.ru/pics/clean/big/20/539320_1.jpg',
                 'https://www.holodilnik.ru/cottage_repair/petrol_powered_saws/champion/254_18_0_325_1_5_72/', None, 'white'),
}
BOX = {'chess': 330, 'drill': 330, 'cactus': 250, 'telescope': 380, 'chainsaw': 360}


def fetch(kind):
    f = CACHE / SRC[kind][0]
    if not f.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(['curl', '-sSfL', '--retry', '5', '-m', '60', '-A', UA, '-o', str(f), SRC[kind][1]], check=True)
    return f


def cutout(kind):
    _, _, _, crop, mode = SRC[kind]
    im = Image.open(fetch(kind)).convert('RGB')
    if crop:
        im = im.crop(crop)
    a = np.asarray(im).astype(np.float32)
    if mode == 'sat':                    # cactus on a white table: background = light and grey, flood from the border
        sat = a.max(-1) - a.min(-1)
        near = (a.min(-1) > 95) & (sat < 30)
        lab, _ = ndimage.label(near)
        edge = np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))
        m = ndimage.binary_fill_holes(~np.isin(lab, edge[edge > 0]))
        m = ndimage.binary_opening(m, iterations=2)
    else:
        near = (a.min(-1) > 236) & (a.max(-1) - a.min(-1) < 14)
        lab, _ = ndimage.label(near)
        edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        m = ndimage.binary_fill_holes(~np.isin(lab, edge[edge > 0]))
        m = ndimage.binary_opening(m, iterations=1)
    lab, n = ndimage.label(m)
    if n > 1:
        size = ndimage.sum(m, lab, range(1, n + 1))
        m = np.isin(lab, 1 + np.nonzero(size > size.max() * 0.05)[0])
    rgba = im.convert('RGBA')
    rgba.putalpha(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9)))
    return rgba.crop(rgba.getbbox())


@functools.lru_cache(None)
def sprite(kind):
    obj = cutout(kind)
    s = BOX[kind] / max(obj.size)
    obj = obj.resize((round(obj.width * s), round(obj.height * s)), Image.LANCZOS)
    return obj


if __name__ == '__main__':
    sheet = Image.new('RGBA', (len(SRC) * 400, 420), (255, 255, 255, 255))
    for k, kind in enumerate(SRC):
        im = sprite(kind)
        sheet.alpha_composite(im, (k * 400 + (400 - im.width) // 2, (420 - im.height) // 2))
    out = Path(__file__).resolve().parent / 'build' / 'review' / 'photos.png'
    sheet.convert('RGB').save(out)
    print(out)
