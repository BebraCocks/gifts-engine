"""Cut the fist-closing strip (assets/gen/fist_strip_v1.png, 3×2, white) into hand_L_close_0..5.png (+ mirrored R).
All six frames are cut with ONE common box relative to their grid cell, so the wrist stays in place when they play
in sequence (the generation kept the wrist fixed inside each cell)."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
import cut_sheets

HERE = Path(__file__).resolve().parent
import sys
SHEET, PREFIX = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ('fist_strip_v1.png', 'close')
sheet = Image.open(HERE / 'assets' / 'gen' / SHEET).convert('RGB')
cw, ch = sheet.width / 3, sheet.height / 2
cells = [sheet.crop((round(c * cw), round(r * ch), round((c + 1) * cw), round((r + 1) * ch))) for r in range(2) for c in range(3)]
cuts = []
for cell in cells:
    a = np.asarray(cell).astype(np.float32)
    im = cut_sheets.cut(cell) if False else None
    cuts.append(cell)
# masks per cell with the same method as cut_sheets.cut but WITHOUT cropping
from scipy import ndimage
from PIL import ImageFilter
rgba_cells, boxes = [], []
for cell in cells:
    a = np.asarray(cell).astype(np.float32)
    mx, mn = a.max(-1), a.min(-1)
    bgm = (mn > 232) & (mx - mn < 16)
    lab, _ = ndimage.label(bgm)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    m = ndimage.binary_fill_holes(ndimage.binary_opening(~np.isin(lab, edge[edge > 0]), iterations=2))
    lab, n = ndimage.label(m)
    if n > 1:
        s = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == 1 + int(np.argmax(s))
    m = ndimage.binary_erosion(m, iterations=1)
    arr = np.asarray(cell.convert('RGBA')).copy()
    al = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))).astype(np.float32) / 255
    rgb = arr[..., :3].astype(np.float32)
    edge_px = (al > 0) & (al < 0.98)
    fixed = np.clip((rgb - 255 * (1 - al[..., None])) / np.maximum(al[..., None], 0.05), 0, 255)
    arr[..., :3] = np.where(edge_px[..., None], fixed, rgb).astype(np.uint8)
    arr[..., 3] = (al * 255).astype(np.uint8)
    im = Image.fromarray(arr)
    rgba_cells.append(im)
    boxes.append(im.getbbox())
box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
out = HERE / 'assets' / 'sprites'
for k, im in enumerate(rgba_cells):
    c = im.crop(box)
    c.save(out / f'hand_L_{PREFIX}_{k}.png')
    ImageOps.mirror(c).save(out / f'hand_R_{PREFIX}_{k}.png')
print('box', box, 'size', (box[2] - box[0], box[3] - box[1]))
