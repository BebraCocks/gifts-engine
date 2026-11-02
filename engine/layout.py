"""Measure text bounds and audit padding independently of a visual theme."""
import functools
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402


@functools.lru_cache(maxsize=1024)
def ink(s, size, weight="Bold", tracking=0.0):
    """Ink box of `s` relative to the drawing point of ImageDraw.text(anchor="ls"): (l, t, r, b), t < 0 above the baseline."""
    f = fx.font(weight, size)
    if not s:
        return (0.0, 0.0, 0.0, 0.0)
    if not tracking:
        return tuple(float(v) for v in f.getbbox(s, anchor="ls"))
    x, boxes = 0.0, []
    for char in s:
        l, t, r, b = f.getbbox(char, anchor="ls")
        boxes.append((x + l, t, x + r, b))
        x += f.getlength(char) + tracking
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))



@functools.lru_cache(maxsize=256)
def cap_top(size, weight="Bold"):
    """Top of capitals / digits relative to the baseline (negative)."""
    return ink("НЕ80", size, weight)[1]


def centered(s, size, weight="Bold", cx=540.0, cy=0.0, tracking=0.0):
    """Drawing point (x, baseline) for ImageDraw.text(anchor="ls") so the ink is centred on cx and the cap band on cy."""
    l, t, r, b = ink(s, size, weight, tracking)
    x = cx - (l + r) / 2
    base = cy - cap_top(size, weight) / 2
    return x, base


def box_of(s, size, weight, x, base, tracking=0.0):
    """Absolute ink box of text drawn with ImageDraw.text(s, x, base, anchor="ls")."""
    l, t, r, b = ink(s, size, weight, tracking)
    return (x + l, base + t, x + r, base + b)


def band_of(size, weight, base):
    """The cap band (top of capitals .. baseline) of a line drawn at `base`: what vertical centring looks at."""
    return (base + cap_top(size, weight), base)


# ------------------------------------------------------------------ audit
_REC = []


def record(name, box, inks, sym_x=True, sym_y=True, band=None, pad_min=8.0, alpha=1.0):
    """Remember one framed text: box = frame (x0, y0, x1, y1), inks = ink boxes inside it,
    band = (top, bottom) used for vertical centring (default: the inks' extent). Only visible ones (alpha > 0.5)."""
    if alpha < 0.5 or not inks:
        return
    _REC.append(dict(name=name, box=[float(v) for v in box], inks=[[float(v) for v in k] for k in inks],
                     sym_x=sym_x, sym_y=sym_y, band=None if band is None else [float(band[0]), float(band[1])],
                     pad_min=pad_min))


def take():
    out = list(_REC)
    _REC.clear()
    return out


def flush(i, folder="build/audit"):
    """Append this frame's records to build/audit/<pid>.jsonl (called once per frame by the project)."""
    recs = take()
    if not recs or not os.environ.get("VIZ_AUDIT", "1") == "1":
        return
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f"{os.getpid()}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"i": i, "recs": recs}, ensure_ascii=False) + "\n")


def problems(rec, tol_x=4.0, tol_y=5.0):
    """List of human-readable problems of one record."""
    x0, y0, x1, y1 = rec["box"]
    ks = np.array(rec["inks"])
    l, t, r, b = ks[:, 0].min(), ks[:, 1].min(), ks[:, 2].max(), ks[:, 3].max()
    out = []
    pm = rec["pad_min"]
    if l < x0 + pm or r > x1 - pm or t < y0 + pm * 0.5 or b > y1 - pm * 0.5:
        out.append(f"text outside the frame: ink {l:.0f},{t:.0f}-{r:.0f},{b:.0f} box {x0:.0f},{y0:.0f}-{x1:.0f},{y1:.0f}")
    if rec["sym_x"] and abs((l - x0) - (x1 - r)) > tol_x:
        out.append(f"lopsided horizontally: left {l - x0:.0f} px, right {x1 - r:.0f} px")
    if rec["sym_y"]:
        bt, bb = rec["band"] if rec["band"] else (t, b)
        if abs((bt - y0) - (y1 - bb)) > tol_y:
            out.append(f"lopsided vertically: top {bt - y0:.0f} px, bottom {y1 - bb:.0f} px")
    return out


def report(folder):
    """Read build/audit/*.jsonl -> (frames checked, records, {name: [(frame, problem), ...]})."""
    frames, n, bad = set(), 0, {}
    for p in sorted(Path(folder).glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            frames.add(d["i"])
            for rec in d["recs"]:
                n += 1
                for msg in problems(rec):
                    bad.setdefault(rec["name"], []).append((d["i"], msg))
    return len(frames), n, bad


if __name__ == "__main__":
    proj = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    nf, nr, bad = report(proj / "build" / "audit")
    print(f"layout audit: {nf} frames, {nr} framed texts checked")
    if not bad:
        print("OK: every text stays inside its frame, padding even")
    for name, items in bad.items():
        fr = sorted({i for i, _ in items})
        print(f"  {name}: {len(items)} problems in frames {fr[0]}..{fr[-1]} — e.g. frame {items[0][0]}: {items[0][1]}")
    sys.exit(1 if bad else 0)

