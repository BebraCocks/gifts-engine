"""Предпросмотр и прогрев кеша v2: рендерит по кадру из каждой сцены (или заданные сцены) в build/review_v2.
    python -B projects/63-nizshii-1/bake.py [сцена ...] [--at 0.3]"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import paths  # noqa: E402
HERE = paths.enter(__file__)
import render as r  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith('--')]
at = float(sys.argv[sys.argv.index('--at') + 1]) if '--at' in sys.argv else 0.5
out = HERE / 'build' / 'review_v2'
out.mkdir(parents=True, exist_ok=True)
done = set()
for i, (name, t0, t1, _) in enumerate(r.SCENES):
    if args and name not in args:
        continue
    t = t0 + (t1 - t0) * at
    s = time.time()
    try:
        im = r.render_at(t)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('FAIL', name, e)
        continue
    im.save(out / f'{i:02d}_{name}_{t:.1f}.png')
    print(f'{name:14s} t={t:7.2f} {time.time() - s:6.1f}s', flush=True)
