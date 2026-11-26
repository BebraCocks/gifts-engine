"""Voice timeline of episode 1: line order and the pause before each line (s). Build: python -B voice_timeline.py"""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = [("A1", 0.30), ("A2", 0.40), ("A3", 0.50), ("M1", 0.35), ("A4", 0.35), ("M2", 0.35), ("A5", 0.35),
         ("M3", 0.35), ("A6", 0.35), ("M4", 1.00), ("A7", 1.00), ("M5", 0.50), ("A8", 0.60), ("M6", 0.80),
         ("A9", 1.00), ("A10", 0.60), ("M7", 0.60)]
TAIL = 1.80
TARGET_DB = -15.0  # одна громкость для Айзена и Миседа (автор: Айзен тише) — RMS активной речи
LIMIT = 58.9


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def level_db(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    import numpy as np
    x = np.frombuffer(raw, np.float32)
    fr = np.array([np.sqrt(np.mean(x[i:i + 320] ** 2)) for i in range(0, len(x) - 320, 320)])
    act = fr[fr > fr.max() * 0.1]
    return 20 * np.log10(np.sqrt(np.mean(act ** 2)))


def build():
    t, cues, inputs, parts = 0.0, [], [], []
    for i, (k, gap) in enumerate(ORDER):
        t += gap
        f = HERE / "build" / "voice" / "trim" / f"{k}.wav"
        d = dur(f)
        cues.append({"id": k, "start": round(t, 3), "end": round(t + d, 3)})
        inputs += ["-i", str(f)]
        gain = TARGET_DB - level_db(f)
        parts.append(f"[{i}]volume={gain:.2f}dB,adelay={int(t * 1000)}:all=1[a{i}]")
        t += d
    total = t + TAIL
    assert total <= LIMIT, f"too long: {total:.2f} s"
    mix = "".join(f"[a{i}]" for i in range(len(ORDER)))
    flt = ";".join(parts) + f";{mix}amix=inputs={len(ORDER)}:normalize=0,alimiter=limit=0.95,apad,atrim=0:{total:.3f}"
    out = HERE / "build" / "review" / "voice_only.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", flt, "-b:a", "192k", str(out)], check=True)
    (HERE / "voice_cues.json").write_text(json.dumps({"total": round(total, 3), "cues": cues}, ensure_ascii=False, indent=1))
    print(f"{out}  {total:.2f} s")


if __name__ == "__main__":
    build()
