"""Telegram gifts from the free API https://api.changes.tg (thanks to @GiftChanges).

Everything is cached under .cache/gifts/<gift-slug>/, so a render
never depends on the network once the files are there.

    import gifts_api as G
    info  = G.gift("Plush Pepe")                 # name, id, models with rarity %
    mods  = G.models("Plush Pepe", sorted_=True) # [{"name", "rarity" (in %), ...}] rarest first
    bds   = G.backdrops("Plush Pepe")            # [{"name", "hex": {centerColor, edgeColor, patternColor, textColor}, "rarity"}]
    png   = G.model_png("Plush Pepe", "Cozy Galaxy", size=512)   # -> Path to PNG with alpha
    tgs   = G.model_file("Plush Pepe", "Cozy Galaxy", "json")    # -> Path to Lottie JSON (animation)
    orig  = G.original_png("Plush Pepe", 512)    # the gift before upgrade

CLI (prefetch for a video):
    python engine/gifts_api.py "Plush Pepe" --models 6 --size 512
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

BASE = "https://api.changes.tg"
CACHE = paths.CACHE / "gifts"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _get(path, dest=None):
    url = BASE + "/".join(urllib.parse.quote(p, safe="?=&.") for p in path.split("/"))
    if dest is not None and dest.exists():
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": "telegram-video-starter/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if dest is None:
        return data
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def _json(path, cache_name):
    f = CACHE / cache_name
    if not f.exists():
        _get(path, f)
    return json.loads(f.read_text(encoding="utf-8"))


def gift(name):
    return _json(f"/gift/{name}", f"{slug(name)}/gift.json")


def models(name, sorted_=True):
    return _json(f"/models/{name}" + ("?sorted" if sorted_ else ""), f"{slug(name)}/models_{int(sorted_)}.json")


def backdrops(name, sorted_=True):
    return _json(f"/backdrops/{name}" + ("?sorted" if sorted_ else ""), f"{slug(name)}/backdrops_{int(sorted_)}.json")


def symbols(name, sorted_=True):
    return _json(f"/symbols/{name}" + ("?sorted" if sorted_ else ""), f"{slug(name)}/symbols_{int(sorted_)}.json")


def all_gifts():
    return _json("/gifts", "_all_gifts.json")


def model_png(name, model, size=512):
    return _get(f"/model/{name}/{model}.png?size={size}", CACHE / slug(name) / "models" / f"{slug(model)}_{size}.png")


def model_file(name, model, ext="tgs"):
    """ext: tgs (gzipped Lottie), json (Lottie), svg (first frame)."""
    return _get(f"/model/{name}/{model}.{ext}", CACHE / slug(name) / "models" / f"{slug(model)}.{ext}")


def symbol_png(name, symbol, size=256):
    return _get(f"/symbol/{name}/{symbol}.png?size={size}", CACHE / slug(name) / "symbols" / f"{slug(symbol)}_{size}.png")


def original_png(name, size=512):
    return _get(f"/original/{name}.png?size={size}", CACHE / slug(name) / f"original_{size}.png")


def original_file(name, ext="tgs"):
    return _get(f"/original/{name}.{ext}", CACHE / slug(name) / f"original.{ext}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("gift")
    ap.add_argument("--models", type=int, default=6, help="how many rarest models to fetch")
    ap.add_argument("--size", type=int, default=512, choices=[64, 128, 256, 512, 1024])
    ap.add_argument("--anim", action="store_true", help="also fetch Lottie JSON animations")
    a = ap.parse_args()
    g = gift(a.gift)["gift"]
    print(f"{g['name']}  id={g['id']}")
    print("original:", original_png(a.gift, a.size))
    for m in models(a.gift)[:a.models]:
        p = model_png(a.gift, m["name"], a.size)
        extra = f"  anim: {model_file(a.gift, m['name'], 'json').name}" if a.anim else ""
        print(f"  {m['name']:<22} {m['rarity']}%  -> {p.name}{extra}")
