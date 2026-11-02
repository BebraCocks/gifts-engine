"""Inspect a full animation cycle. Arguments: output.png "Gift/Model" --n 12."""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gifts_api as G  # noqa: E402
import lottie  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("models", nargs="+", help='"Gift/Model"')
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--size", type=int, default=160)
    a = ap.parse_args()
    s = a.size
    im = Image.new("RGB", (s * a.n, (s + 30) * len(a.models)), (235, 235, 235))
    d = ImageDraw.Draw(im)
    for r, spec in enumerate(a.models):
        gift, model = spec.split("/", 1)
        path = G.model_file(gift, model, "json")
        info = lottie.info(str(path))
        print(f"{spec}: {info['frames']} frames, {info['fps']} fps, {info['duration']:.2f} s")
        for j in range(a.n):
            t = j * info["duration"] / a.n
            fr = lottie.frame(str(path), t, s)
            im.paste(fr, (s * j, (s + 30) * r), fr)
            d.text((s * j + 4, (s + 30) * r + s + 8), f"{model} {t:.2f}s", fill=(0, 0, 0))
    im.save(a.out)
    print("->", a.out)


if __name__ == "__main__":
    main()