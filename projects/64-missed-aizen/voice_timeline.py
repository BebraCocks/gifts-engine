"""Voice timeline of episode 1: line order and the pause before each line (s). Build: python -B voice_timeline.py"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [("A1", 0.30), ("A2", 0.40), ("A3", 0.50), ("M1", 0.35), ("A4", 0.35), ("M2", 0.35), ("A5", 0.35),
         ("M3", 0.35), ("A6", 0.35), ("M4", 1.00), ("A7", 1.00), ("M5", 0.50), ("A8", 0.60), ("M6", 0.80),
         ("A9", 1.00), ("A10", 0.60), ("M7", 0.60)]
TAIL = 1.80
LIMIT = 58.9


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def build():
    t, cues, inputs, parts = 0.0, [], [], []
    for i, (k, gap) in enumerate(ORDER):
        t += gap
        f = HERE / "build" / "voice" / "trim" / f"{k}.wav"
        d = dur(f)
        cues.append({"id": k, "start": round(t, 3), "end": round(t + d, 3)})
        inputs += ["-i", str(f)]
        parts.append(f"[{i}]adelay={int(t * 1000)}:all=1[a{i}]")
        t += d
    total = t + TAIL
    assert total <= LIMIT, f"too long: {total:.2f} s"
    mix = "".join(f"[a{i}]" for i in range(len(ORDER)))
    flt = ";".join(parts) + f";{mix}amix=inputs={len(ORDER)}:normalize=0,apad,atrim=0:{total:.3f}"
    out = HERE / "build" / "review" / "voice_only.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", flt, "-b:a", "192k", str(out)], check=True)
    (HERE / "voice_cues.json").write_text(json.dumps({"total": round(total, 3), "cues": cues}, ensure_ascii=False, indent=1))
    print(f"{out}  {total:.2f} s")


if __name__ == "__main__":
    build()
