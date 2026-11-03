"""Полный цикл Lottie каждой маски → PNG-кадры для 3D-прохода (build/masks/<slug>/NNN.png)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths
HERE = paths.enter(__file__)
import numpy as np
import gifts_api
import lottie

GIFT = 'Myth Mask'
MASKS = {'ghostface': 'Ghostface', 'anonymous': 'Anonymous', 'bella-ciao': 'Bella Ciao',
         'arthur-fool': 'Arthur Fool', 'dark-knight': 'Dark Knight'}
SIZE = 640


def main(names):
    for slug in names:
        path = str(gifts_api.model_file(GIFT, MASKS[slug], 'json'))
        meta = lottie.info(path)
        out = paths.build(HERE) / 'masks' / slug
        out.mkdir(parents=True, exist_ok=True)
        alphas = []
        for f in range(meta['frames']):
            im = lottie.frame(path, f / meta['fps'], size=SIZE)
            alphas.append(np.asarray(im)[..., 3].mean())
            im.save(out / f'{f:03d}.png')
        if min(alphas) < 1:
            raise SystemExit(f'{slug}: пустая альфа — аварийная подмена Lottie')
        print(f"{slug}: {meta['frames']} кадров, {meta['fps']} fps, альфа {min(alphas):.0f}–{max(alphas):.0f}")


if __name__ == '__main__':
    main(sys.argv[1:] or list(MASKS))
