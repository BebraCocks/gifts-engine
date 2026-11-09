"""Deterministic frame CLI, parallel workers, configurable H.264 encoding and progress.
Use --frames 0,60 for still previews; --video only after explicit build approval."""
import ctypes
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

from PIL import Image

import paths


def nvenc_ok():
    """True if ffmpeg can encode H.264 on an NVIDIA GPU here (tiny test encode)."""
    if os.environ.get("VIZ_ENCODER", "x264").lower() == "x264":
        return False
    r = subprocess.run([paths.ffmpeg(), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.1",
                        "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


# Delivery for TikTok / Shorts / Reels (2026-11-08): RGB -> BT.709 limited range with matching colour tags (without them
# players guess BT.601 and colours shift), a keyframe every 2 s at 60 fps, square pixels tagged (SAR 1:1, 2026-11-08).
DELIVERY = ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1", "-colorspace", "bt709",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-g", "120", "-keyint_min", "60"]


CRF_STEP = {"slow": 0, "medium": 1, "fast": 1, "faster": 2}   # CRF lowered so a faster preset keeps slow's quality


def encoder_args(crf, tune=None):
    """Select output quality through VIZ_CQ."""
    cq = int(os.environ.get("VIZ_CQ", "26"))
    hevc = os.environ.get("VIZ_CODEC", "").lower() in ("hevc", "h265")
    if nvenc_ok():
        args = ["-c:v", "hevc_nvenc" if hevc else "h264_nvenc", "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", str(cq),
                "-b:v", "0", "-maxrate", "30M", "-bufsize", "60M", "-spatial-aq", "1", "-temporal-aq", "1", "-bf", "3",
                "-pix_fmt", "yuv420p"]
        args += ["-tag:v", "hvc1"] if hevc else ["-profile:v", "high", "-b_ref_mode", "middle"]
        return args + DELIVERY, f"{'hevc' if hevc else 'h264'}_nvenc cq {cq} (GPU)"
    # x264 preset (2026-11-09, 41 test): VIZ_PRESET=medium lowers CRF one step and keeps slow's quality (SSIM 0.99885 vs
    # 0.99875, PSNR 53.3 vs 52.8 dB at VIZ_CQ=24) for 24 % less encoder CPU, but the whole 61 s video built only 3 % faster
    # (frames, not the encoder, are the bottleneck) and the file grew 11.5 % (Drive upload limit ~40 MB). Default stays slow.
    preset = "slow" if hevc else os.environ.get("VIZ_PRESET", "slow")
    crf = cq - 10 - CRF_STEP.get(preset, 0)
    args = ["-c:v", "libx265" if hevc else "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if not hevc:                                   # social upload profile (2026-11-08): High@4.2, capped CRF
        args += ["-profile:v", "high", "-level", "4.2", "-maxrate", "16M", "-bufsize", "32M"]
    if tune:
        args += ["-tune", tune]
    return args + DELIVERY, f"{'libx265' if hevc else 'libx264'} {preset} crf {crf} (CPU)"


def low_priority():
    """BELOW_NORMAL priority for this process (Pool initializer): the frame workers yield resources to other processes."""
    try:
        if os.name == "nt":
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
        else:
            os.nice(10)
    except Exception:
        pass


def mem_mb():
    """(total, available) physical memory in MB, or (0, 0) if unknown."""
    try:
        if os.name == "nt":
            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                    (k, ctypes.c_ulonglong) for k in ("total", "avail", "tpf", "apf", "tv", "av", "aev")]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.total >> 20, m.avail >> 20
        info = dict(line.split(":", 1) for line in open("/proc/meminfo"))
        return int(info["MemTotal"].split()[0]) >> 10, int(info["MemAvailable"].split()[0]) >> 10
    except Exception:
        return 0, 0


WORKER_MB = int(os.environ.get("VIZ_WORKER_MB", "600"))    # RAM per frame worker (41, 2026-11-09: ~240 MB PSS + Lottie cache)


def cpu_workers():
    """Frame workers (2026-11-09): all logical cores by default (VIZ_CPU = fraction of cores, default 1.0; VIZ_WORKERS =
    exact number). The workers and ffmpeg run at low priority, so the PC stays responsive while the CPU is fully used.
    Capped by RAM: workers x VIZ_WORKER_MB must fit into 90 % of total memory minus what is already in use."""
    n = os.cpu_count() or 2
    if os.environ.get("VIZ_WORKERS"):
        return max(1, int(os.environ["VIZ_WORKERS"]))
    want = max(1, int(round(n * float(os.environ.get("VIZ_CPU", "1.0")))))
    total, avail = mem_mb()
    if total:
        budget = avail - 0.10 * total - 400                      # keep 10 % free + ~400 MB for ffmpeg and the main process
        want = min(want, max(1, int(budget // WORKER_MB)))
    return want


def _mmss(sec):
    sec = int(max(0, sec))
    return f"{sec // 60}:{sec % 60:02d}"


class Progress:
    """Prints a progress bar every ~3 s and keeps build/progress.json (tiny, for watch_progress.py)."""

    def __init__(self, total, build, stage="frames"):
        self.total, self.stage, self.t0, self.last = total, stage, time.time(), 0.0
        self.path = Path(build) / "progress.json"
        self.tty = sys.stdout.isatty()

    def update(self, done, force=False):
        now = time.time()
        gap = 3.0 if self.tty else 5.0
        if not force and now - self.last < gap:
            return
        self.last = now
        el = now - self.t0
        pct = 100.0 * done / max(1, self.total)
        eta = el / done * (self.total - done) if done else 0.0
        bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
        line = f"[{bar}] {pct:3.0f}%  {self.stage} {done}/{self.total}  elapsed {_mmss(el)}  left ~{_mmss(eta)}"
        print(("\r" + line + "   ") if self.tty else line, end="" if self.tty else "\n", flush=True)
        try:
            self.path.write_text(json.dumps({"stage": self.stage, "done": done, "total": self.total, "pct": round(pct, 1),
                                             "elapsed_s": round(el), "eta_s": round(eta), "updated": round(now)}), encoding="utf-8")
        except OSError:
            pass
        if force and self.tty:
            print()


# ------------------------------------------------------------------ frame transport (2026-11-09)
# Workers put finished frames into shared-memory slots instead of pickling ~6 MB per frame through a pipe (that cost the
# main process ~4 s of CPU per 600 frames). Frame i always uses slot i % n and waits until frame i - n has been written to
# ffmpeg; the main process writes frames strictly in order, so the frame it waits for can always proceed (no deadlock).
_SHM = {}


def _shm_init(name, n_slots, slot_size, written, frame_bytes):
    from multiprocessing import shared_memory
    low_priority()
    try:
        shm = shared_memory.SharedMemory(name=name, track=False)     # Python 3.13+: the main process owns the block
    except TypeError:
        shm = shared_memory.SharedMemory(name=name)
    _SHM.update(shm=shm, n=n_slots, size=slot_size, written=written, fb=frame_bytes)


def _shm_task(i):
    b = _SHM["fb"](i)
    if len(b) != _SHM["size"]:
        return b                                           # unexpected size: send it the old way
    n, w = _SHM["n"], _SHM["written"]
    while w.value <= i - n:                                # the slot still holds frame i - n
        time.sleep(0.002)
    off = (i % n) * _SHM["size"]
    _SHM["shm"].buf[off:off + len(b)] = b
    return None


def _encode_frames(proc, frame_bytes, n_frames, frame_size, workers, prog):
    import multiprocessing as mp
    from multiprocessing import shared_memory
    n_slots = max(8, 4 * workers)
    shm = shared_memory.SharedMemory(create=True, size=n_slots * frame_size)
    written = mp.Value("q", 0, lock=False)
    try:
        with Pool(workers, initializer=_shm_init,
                  initargs=(shm.name, n_slots, frame_size, written, frame_bytes)) as pool:
            for k, b in enumerate(pool.imap(_shm_task, range(n_frames), chunksize=1)):
                if b is None:
                    off = (k % n_slots) * frame_size
                    proc.stdin.write(shm.buf[off:off + frame_size])
                else:
                    proc.stdin.write(b)
                written.value = k + 1
                prog.update(k + 1)
    finally:
        shm.close()
        shm.unlink()


def cli(render_at, frame_bytes, W, H, fps, n_frames, crf=14, tune=None):
    args = sys.argv[1:]
    build = paths.build()
    if args[:1] == ["--frames"] and len(args) > 1:
        out = build / "review"
        out.mkdir(exist_ok=True)
        for s in args[1].split(","):
            i = int(s)
            Image.fromarray(render_at(i / fps)).save(out / f"f{i:04d}.png", compress_level=1)   # lossless, ~1.6x faster
            print("frame", i, "->", out / f"f{i:04d}.png", flush=True)
    elif args[:1] == ["--video"]:
        out = Path(args[1]) if len(args) > 1 else build / "video_only.mp4"
        enc, enc_name = encoder_args(crf, tune)
        cmd = [paths.ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(fps), "-i", "-"] + enc
        low_priority()                                              # the main process and ffmpeg too
        proc = subprocess.Popen(cmd + [str(out)], stdin=subprocess.PIPE,
                                creationflags=0x4000 if os.name == "nt" else 0)      # BELOW_NORMAL_PRIORITY_CLASS
        workers = cpu_workers()
        for k_ in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            os.environ.setdefault(k_, "1")                          # children inherit: no thread storms inside the workers
        total, avail = mem_mb()
        print(f"{n_frames} frames, {workers} CPU workers (of {os.cpu_count()} cores; RAM free {avail} of {total} MB), "
              f"encoder {enc_name}", flush=True)
        t0 = time.time()
        prog = Progress(n_frames, build)
        if os.environ.get("VIZ_SHM", "1") == "1":
            _encode_frames(proc, frame_bytes, n_frames, W * H * 3, workers, prog)
        else:                                                       # VIZ_SHM=0: the previous pipe transport
            with Pool(workers, initializer=low_priority) as pool:
                for k, b in enumerate(pool.imap(frame_bytes, range(n_frames), chunksize=2)):
                    proc.stdin.write(b)
                    prog.update(k + 1)
        prog.update(n_frames, force=True)
        proc.stdin.close()
        proc.wait()
        print(f"done {proc.returncode} in {time.time() - t0:.0f} s -> {out}")
        if proc.returncode:
            sys.exit(proc.returncode)
    else:
        print(__doc__)