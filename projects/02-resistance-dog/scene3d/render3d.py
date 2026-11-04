"""Render 3D plates for one shot (Blender 5.2 bpy module, EEVEE).

    /root/venv-bpy/bin/python scene3d/render3d.py S04_vault [--frames 1200,1300] [--step 1] [--samples 6]

Writes build/plates/fNNNNN.png (content frame index at 60 fps, 540x960) and
build/plates/anchors/fNNNNN.json (screen positions of 2D-layer anchors, full-res pixels).
Existing frames are skipped, so an interrupted render continues where it stopped."""
import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJECT))

import bpy  # noqa: E402
import lib  # noqa: E402
from events import SHOTS  # noqa: E402

OUT = PROJECT / 'build' / 'plates'


class Shot:
    """Collects animated properties so they can be keyframed (EEVEE motion blur needs real animation)."""

    def __init__(self):
        self.tracks = []
        self.anchors = {}
        self.update = None

    def track(self, db, *paths):
        for p in paths:
            self.tracks.append((db, p))

    def anchor(self, name, ob_or_pos, radius):
        self.anchors[name] = (ob_or_pos, radius)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shot')
    ap.add_argument('--frames', default=None, help='comma list of content frames, or a:b range')
    ap.add_argument('--step', type=int, default=1)
    ap.add_argument('--samples', type=int, default=2)
    ap.add_argument('--scale', type=int, default=50)
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    name = args.shot
    start, end = [(a, b) for n, a, b in SHOTS if n == name][0]
    f0, f1 = math.ceil(start * 60), math.ceil(end * 60) - 1
    import shots
    lib.reset(scale=args.scale, samples=args.samples)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    sh = Shot()
    getattr(shots, name)(sh, start, end)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = f0, f1
    t0 = time.time()
    for f in range(f0 - 1, f1 + 2):
        sh.update(f / 60)
        for db, p in sh.tracks:
            db.keyframe_insert(p, frame=f)
    print(f'{name}: keyed {len(sh.tracks)} channels over {f1 - f0 + 1} frames in {time.time() - t0:.1f}s', flush=True)
    if args.frames:
        if ':' in args.frames:
            a, b = map(int, args.frames.split(':'))
            frames = list(range(max(f0, a), min(f1, b) + 1, args.step))
        else:
            frames = [int(x) for x in args.frames.split(',')]
    else:
        frames = list(range(f0, f1 + 1, args.step))
    out = Path(args.out)
    (out / 'anchors').mkdir(parents=True, exist_ok=True)
    cam = sc.camera
    for f in frames:
        png = out / f'f{f:05d}.png'
        if png.exists():
            continue
        sc.frame_set(f)
        an = {k: lib.project(cam, o, r) for k, (o, r) in sh.anchors.items()}
        an['_shot'] = name
        (out / 'anchors' / f'f{f:05d}.json').write_text(json.dumps(an))
        sc.render.filepath = str(png)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f'{name} f{f} {time.time() - t:.2f}s', flush=True)


if __name__ == '__main__':
    main()
