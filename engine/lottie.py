"""Lottie / TGS playback for renders (rlottie via the `rlottie-python` package).

    import lottie
    im = lottie.frame(path_json_or_tgs, t, size=512)          # PIL RGBA, straight alpha, loops
    im = lottie.frame(path, t, size=512, speed=1.0, offset=0.4)   # desync several copies

Deterministic: the frame depends only on `t` (seconds), never on how many frames were rendered.
If rlottie is missing or the file cannot be rendered, a PNG next to it (same stem, `_512.png`
or `.png`) is returned instead, so a render never crashes on one bad animation.
"""
import functools
import gzip
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from rlottie_python import LottieAnimation
except ImportError:  # pragma: no cover
    LottieAnimation = None

_FRAMES = OrderedDict()
_MAX_CACHED = 96           # bounded memory per renderer process


@functools.lru_cache(maxsize=64)
def _anim(path):
    p = Path(path)
    if LottieAnimation is None:
        return None
    try:
        if p.suffix == ".tgs":                   # gzipped Lottie JSON
            raw = gzip.decompress(p.read_bytes()).decode('utf-8')
            a = LottieAnimation.from_data(raw, resource_path=str(p.parent))
        else:
            a = LottieAnimation.from_file(str(p))
        if a.lottie_animation_get_totalframe() <= 0 or a.lottie_animation_get_framerate() <= 0:
            return None                          # broken / empty animation -> PNG fallback
        return a
    except Exception:
        return None


@functools.lru_cache(maxsize=64)
def info(path):
    """{'frames', 'fps', 'duration', 'w', 'h'} of an animation."""
    # The document's out-point is exclusive. Some rlottie builds report a last
    # frame index as totalframe; the source document preserves the complete cycle.
    try:
        p = Path(path)
        raw = gzip.decompress(p.read_bytes()) if p.suffix.lower() == '.tgs' else p.read_bytes()
        j = json.loads(raw)
        n, fps = int(j['op'] - j['ip']), float(j['fr'])
        if n > 0 and fps > 0:
            return dict(frames=n, fps=fps, duration=n/fps, w=j['w'], h=j['h'])
    except (OSError, ValueError, KeyError):
        pass
    a = _anim(str(path))
    if a is None:
        try:
            j = json.loads(Path(path).read_text(encoding="utf-8"))
            n = int(j["op"] - j["ip"])
            return dict(frames=n, fps=float(j["fr"]), duration=n / float(j["fr"]), w=j["w"], h=j["h"])
        except Exception:
            return dict(frames=1, fps=60.0, duration=0.0, w=0, h=0)
    n = a.lottie_animation_get_totalframe()
    fps = a.lottie_animation_get_framerate()
    w, h = a.lottie_animation_get_size()
    return dict(frames=n, fps=fps, duration=n / fps, w=w, h=h)


def _fallback(path, size):
    p = Path(path)
    for cand in (p.with_name(f"{p.stem}_{size}.png"), p.with_name(f"{p.stem}_512.png"), p.with_suffix(".png")):
        if cand.exists():
            im = Image.open(cand).convert("RGBA")
            return im if im.size == (size, size) else im.resize((size, size), Image.LANCZOS)
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def _unpremultiply(im):
    a = np.asarray(im, np.float32)
    al = a[..., 3:4]
    rgb = np.where(al > 0, a[..., :3] * 255.0 / np.maximum(al, 1), 0)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), al]).astype(np.uint8), "RGBA")


def frame(path, t, size=512, speed=1.0, offset=0.0, loop=True):
    """RGBA frame of the animation at time t (seconds)."""
    path = str(path)
    a = _anim(path)
    if a is None:
        return _fallback(path, size)
    meta = info(path)
    n = meta["frames"]
    f = (t * speed + offset) * meta["fps"]
    f = int(f) % n if loop else min(max(int(f), 0), n - 1)
    key = (path, f, size)
    im = _FRAMES.get(key)
    if im is None:
        try:
            im = _unpremultiply(a.render_pillow_frame(frame_num=f, width=size, height=size))
        except Exception:
            im = _fallback(path, size)
        _FRAMES[key] = im
        if len(_FRAMES) > _MAX_CACHED:
            _FRAMES.popitem(last=False)
    else:
        _FRAMES.move_to_end(key)
    return im
