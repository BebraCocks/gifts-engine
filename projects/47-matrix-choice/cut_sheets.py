"""Cut the Fish Audio sprite sheets (white background, 3x2 grid) into RGBA sprites -> assets/sprites/.
Heads: head_<name>.png; hands: left hand hand_L_<pose>.png + mirrored right hand hand_R_<pose>.png.
The author's own photo gives head.png / hand_L.png / hand_R.png (calm head, open palms)."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from scipy import ndimage

HERE = Path(__file__).resolve().parent
OUT = HERE / 'assets' / 'sprites'
SHEETS = {
    'head_sheet_v1.png': ('head', ['calm', 'smirk', 'brow', 'over_glasses', 'wince', 'surprise']),
    'hand_sheet_v1.png': ('hand', ['fist', 'half', 'cup', 'hold', 'down', 'point']),
    'hand_sheet_v2.png': ('hand', ['point_up', 'flick', 'pinch', 'grip', 'squeeze', 'catch']),
    'head_sheet_v2.png': ('head', ['blow', 'look_left', 'look_right', 'look_up', 'talk_a', 'talk_o']),
    'agent_sheet_v1.png': ('agent', ['front', 'left', 'right', 'down', 'down_left', 'down_right']),
}


def cut(cell):
    a = np.asarray(cell).astype(np.float32)
    mx, mn = a.max(-1), a.min(-1)
    bgm = (mn > 232) & (mx - mn < 16)
    lab, _ = ndimage.label(bgm)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    m = ~np.isin(lab, edge[edge > 0])
    m = ndimage.binary_fill_holes(ndimage.binary_opening(m, iterations=2))
    lab, n = ndimage.label(m)
    if n > 1:
        s = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == 1 + int(np.argmax(s))
    m = ndimage.binary_erosion(m, iterations=1)
    im = cell.convert('RGBA')
    im.putalpha(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1)))
    # de-fringe: pull edge colours away from the white backdrop
    arr = np.asarray(im).astype(np.float32)
    al = arr[..., 3:4] / 255
    edge_px = (al > 0) & (al < 0.98)
    rgb = arr[..., :3]
    fixed = np.clip((rgb - 255 * (1 - al)) / np.maximum(al, 0.05), 0, 255)
    arr[..., :3] = np.where(edge_px, fixed, rgb)
    im = Image.fromarray(arr.astype(np.uint8))
    return im.crop(im.getbbox())


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    for f, (kind, names) in SHEETS.items():
        if not (HERE / 'assets' / 'gen' / f).exists():
            continue
        sheet = Image.open(HERE / 'assets' / 'gen' / f).convert('RGB')
        cw, ch = sheet.width / 3, sheet.height / 2
        for k, name in enumerate(names):
            c, r = k % 3, k // 3
            sp = cut(sheet.crop((round(c * cw), round(r * ch), round((c + 1) * cw), round((r + 1) * ch))))
            if kind in ('head', 'agent'):
                sp.save(OUT / f'{kind}_{name}.png')
            else:
                sp.save(OUT / f'hand_L_{name}.png')
                ImageOps.mirror(sp).save(OUT / f'hand_R_{name}.png')
            print(kind, name, sp.size)
