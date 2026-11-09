"""RubUp advertisement: complete playback with original sound, central placement, content pause.
Speed 1.0..1.1; audio time stretching preserves pitch. No presenter or other assets are required."""
import functools
import math
import os

import numpy as np
from PIL import Image, ImageFilter

import paths
from fx import smooth

SRC = paths.INPUT / "video" / "RubUP Gifts banner.mov"
W_OUT = 1080            # banner width in the frame (full width)
SPEED = 1.1             # maximum playback speed; audio preserves pitch
RAMP = 0.4              # s: the video slows to a stop / speeds up again
PRE, POST = 0.05, 0.12  # s: still frame before / after the banner itself
DIM = 0.20              # background darkened by 20 %
SOFT = 3.0              # px: light blur of the paused background (keeps the eye on the banner)
CY = 960                # centre of a 1080 x 1920 frame


# ------------------------------------------------------------------ the banner itself (decoded once, cached)
def _cache_dir(w):
    return paths.CACHE / "banner" / f"rubup_gifts_{w}"


def _decode(w=W_OUT):
    import av                                            # PyAV (FFmpeg 8+): reads the alpha layer of HEVC
    d = _cache_dir(w)
    d.mkdir(parents=True, exist_ok=True)
    c = av.open(str(SRC))
    vs = c.streams.video[0]
    n = 0
    for f in c.decode(vs):
        im = Image.fromarray(f.to_ndarray(format="rgba"))
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        im.save(d / f"f{n:04d}.png", compress_level=1)
        n += 1
    fps = float(vs.average_rate)
    c.close()
    import sound
    snd = sound.load_stereo(SRC, 48000).astype(np.float32)
    np.save(d / "sound.npy", snd)
    (d / "info.txt").write_text(f"{n} {fps}")
    print(f"banner: decoded {n} frames at {fps} fps -> {d}")


@functools.lru_cache(None)
def info(w=W_OUT):
    d = _cache_dir(w)
    if not (d / "info.txt").exists():
        _decode(w)
    n, fps = (d / "info.txt").read_text().split()
    return int(n), float(fps)


@functools.lru_cache(None)
def _frames_raw(w=W_OUT):
    """All banner frames as one uncompressed uint8 array (n, h, w, 4), memory-mapped from .cache (2026-11-09).
    PNG decoding cost ~15 ms per frame in every worker; the raw file is read from the OS page cache, shared by all workers,
    and holds exactly the same pixels (built once from the lossless PNG cache)."""
    d = _cache_dir(w)
    n, _ = info(w)
    raw = d / "frames_rgba.npy"
    if not raw.exists():
        first = np.asarray(Image.open(d / "f0000.png").convert("RGBA"))
        tmp = d / f"frames_rgba.{os.getpid()}.tmp.npy"
        mm = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.uint8, shape=(n,) + first.shape)
        for k in range(n):
            mm[k] = np.asarray(Image.open(d / f"f{k:04d}.png").convert("RGBA"))
        mm.flush()
        del mm
        os.replace(tmp, raw)                            # atomic: a parallel process never sees a half-written file
    return np.load(raw, mmap_mode="r")


@functools.lru_cache(maxsize=4)
def _frame(k, w=W_OUT):
    a = np.asarray(_frames_raw(w)[k], np.float32)
    return a[..., :3], a[..., 3:4] / 255


def length(w=W_OUT):
    n, fps = info(w)
    return n / fps


def _stretch(x, speed):
    """Time-stretch a stereo float array (48 kHz) by `speed` WITHOUT changing the pitch (ffmpeg atempo, WSOLA)."""
    import subprocess, tempfile, wave
    with tempfile.TemporaryDirectory() as td:
        a, b = f"{td}/in.wav", f"{td}/out.wav"
        with wave.open(a, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(np.clip(np.round(x * 32767), -32768, 32767).astype("<i2").tobytes())
        subprocess.run([paths.ffmpeg(), "-y", "-loglevel", "error", "-i", a, "-af", f"atempo={speed}", b], check=True)
        with wave.open(b) as w:
            y = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32768
    return y.reshape(-1, 2)


@functools.lru_cache(None)
def sound(sr=48000, speed=1.0):
    """The complete banner sound, time-stretched without pitch shifting."""
    info()
    x = np.load(_cache_dir(W_OUT) / "sound.npy").astype(np.float64)
    if speed != 1.0:
        x = _stretch(x, speed)
    if sr != 48000:
        from scipy.signal import resample_poly
        x = resample_poly(x, sr, 48000, axis=0)
    return x


# ------------------------------------------------------------------ time map: output time -> content time
def _sm(x):
    """smoothstep for numpy arrays"""
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def _ease_int(x):
    """Integral of smoothstep over [0, x] (x in 0..1): content advance while the speed eases."""
    x = np.clip(x, 0, 1)
    return x ** 3 - x ** 4 / 2


class Breaks:
    def __init__(self, stops, cy=CY, speed=None):
        """stops: content times where the video comes to a full stop (one per banner); cy: banner centre y;
        speed: banner playback speed (maximum 1.1x; the sound keeps its pitch)."""
        self.cy = cy
        self.speed = float(SPEED if speed is None else speed)
        if not 1.0 <= self.speed <= 1.1:
            raise ValueError("RubUp playback speed must be between 1.0 and 1.1")
        self.B = length() / self.speed
        _frames_raw()                                   # build the raw frame cache once, before any render workers start
        self.hold = PRE + self.B + POST
        self.extra = RAMP + self.hold                   # output seconds added by one break
        self.stops = sorted(stops)

    @classmethod
    def auto(cls, dur, on, end, tail=0.1, speed=None):
        """One banner per minute (at least one), each in the voice pause nearest the middle of its minute.
        The video stops right after the line ends and starts again just before the next line."""
        n = max(1, math.ceil(dur / 60))
        stops = []
        for m in range(n):
            target = (m + 0.5) * dur / n
            gaps = [(abs((end[k] + on[k + 1]) / 2 - target), k) for k in range(len(on) - 1)]
            k = min(gaps)[1]
            at = min(end[k] + tail + RAMP / 2, on[k + 1] - RAMP / 2 - 0.02)
            stops.append(max(at, end[k]))
        return cls(stops, speed=speed)

    def windows(self):
        """Output-time (start, end) of each break: from the first slow-down to full speed again."""
        return [(at - RAMP / 2 + k * self.extra, at - RAMP / 2 + (k + 1) * self.extra + RAMP)
                for k, at in enumerate(self.stops)]

    def duck(self, n, sr, floor_db=-30.0, fade=0.6):
        """Gain curve (n,) in OUTPUT time for a music bed mixed after audio(): smoothly down to floor_db over
        `fade` s as the video slows, held under the banner, back up as the video restarts."""
        t = np.arange(n) / sr
        g = np.ones(n)
        lo = 10 ** (floor_db / 20)
        for k, (o0, o1) in enumerate(self.windows()):
            b1 = self.stops[k] + RAMP / 2 + PRE + k * self.extra + self.B      # banner ends (output time)
            down = _sm((t - o0) / fade)
            up = _sm((t - (b1 + POST)) / fade)
            gk = 1 - (1 - lo) * down * (1 - up)
            g = np.minimum(g, gk)
        return g

    def out_dur(self, dur):
        return dur + self.extra * len(self.stops)

    def n_frames(self, fps, dur):
        return int(round(self.out_dur(dur) * fps))

    def _local(self, t):
        """(break index, u = seconds since this break began) or (None, content time)."""
        shift = 0.0
        for k, at in enumerate(self.stops):
            o0 = at - RAMP / 2 + shift
            if t < o0:
                return None, t - shift
            if t < o0 + self.extra + RAMP:
                return k, t - o0
            shift += self.extra
        return None, t - shift

    def content_t(self, t):
        k, u = self._local(t)
        if k is None:
            return u
        at = self.stops[k]
        if u < RAMP:
            x = u / RAMP                                    # speed 1 -> 0: advance = RAMP * (x - int S)
            return at - RAMP / 2 + RAMP * (x - float(_ease_int(x)))
        if u < RAMP + self.hold:
            return at
        return at + RAMP * float(_ease_int((u - RAMP - self.hold) / RAMP))

    def content_t_array(self, t):
        """Vectorised content_t for a numpy array of output times."""
        t = np.asarray(t, np.float64)
        ct = np.empty_like(t)
        done = np.zeros(t.shape, bool)
        shift = 0.0
        for k, at in enumerate(self.stops):
            o0 = at - RAMP / 2 + shift
            before = (~done) & (t < o0)
            ct[before] = t[before] - shift
            done |= before
            inb = (~done) & (t < o0 + self.extra + RAMP)
            u = t - o0
            r1 = inb & (u < RAMP)
            x = u[r1] / RAMP
            ct[r1] = at - RAMP / 2 + RAMP * (x - _ease_int(x))
            hold = inb & (u >= RAMP) & (u < RAMP + self.hold)
            ct[hold] = at
            r2 = inb & (u >= RAMP + self.hold)
            ct[r2] = at + RAMP * _ease_int((u[r2] - RAMP - self.hold) / RAMP)
            done |= inb
            shift += self.extra
        rest = ~done
        ct[rest] = t[rest] - shift
        return ct

    def phase(self, t):
        """None outside a break, else dict(dim 0..1, bt = banner time (s, may be <0 or >B), speed 0..1)."""
        k, u = self._local(t)
        if k is None:
            return None
        if u < RAMP:
            x = u / RAMP
            return dict(dim=smooth(x), bt=u - RAMP - PRE, speed=1 - smooth(x))
        if u < RAMP + self.hold:
            return dict(dim=1.0, bt=u - RAMP - PRE, speed=0.0)
        x = (u - RAMP - self.hold) / RAMP
        return dict(dim=1 - smooth(x), bt=u - RAMP - PRE, speed=smooth(x))

    # -------------------------------------------------------------- picture
    def render(self, render_at, t, i=None, fps=60):
        i = round(t * fps) if i is None else i
        ph = self.phase(t)
        if ph is None:
            return render_at(self.content_t(t))
        c = self._paused(render_at, self.content_t(t), ph["dim"]).copy()
        bt = ph["bt"]
        n, bfps = info()
        if 0 <= bt < self.B:
            rgb, al = _frame(min(n - 1, int(bt * bfps * self.speed)))
            y0 = int(self.cy) - rgb.shape[0] // 2
            reg = c[y0:y0 + rgb.shape[0], :rgb.shape[1]]
            reg[:] = reg * (1 - al) + rgb * al
        return np.clip(c, 0, 255).astype(np.uint8)

    def _paused(self, render_at, ct, d):
        """Dimmed, softly blurred content under the banner. While the video stands still (ct and dim unchanged, ~6 s of
        every break) it is computed once and reused: the frame is a pure function of time, so the pixels are identical
        (2026-11-09; before, every paused frame re-rendered and re-blurred the same picture)."""
        key = (render_at, float(ct), float(d))
        if self.__dict__.get("_pkey") == key:
            return self._pval
        frame = render_at(ct)
        c = frame.astype(np.float32)
        if SOFT * d > 0.3:
            im = Image.fromarray(frame).filter(ImageFilter.GaussianBlur(SOFT * d))
            c = np.asarray(im, np.float32)
        c *= 1 - DIM * d
        self._pkey, self._pval = key, c
        return c

    # -------------------------------------------------------------- sound
    def audio(self, mix, sr=48000, banner=True):
        """mix: (N, 2) float in content time -> output-time mix with the pauses and the banner sound.
        banner=False gives the same time map without the banner (an SFX-only stem for review)."""
        import sound as S
        n_out = int(round(self.out_dur(len(mix) / sr) * sr))
        t = np.arange(n_out) / sr
        ct = np.empty(n_out)
        gain = np.ones(n_out)
        ct[:] = self.content_t_array(t)                 # vectorised, identical to content_t per sample
        for k in range(len(self.stops)):                # fade the content out with the speed (soft tape stop)
            o0 = self.stops[k] - RAMP / 2 + k * self.extra
            u = t - o0
            r1 = (u >= 0) & (u < RAMP)
            gain[r1] = (1 - _sm(u[r1] / RAMP)) ** 0.7
            gain[(u >= RAMP) & (u < RAMP + self.hold)] = 0
            r2 = (u >= RAMP + self.hold) & (u < self.extra + RAMP)
            gain[r2] = _sm((u[r2] - RAMP - self.hold) / RAMP) ** 0.7
        pos = np.clip(ct * sr, 0, len(mix) - 1)
        out = np.stack([np.interp(pos, np.arange(len(mix)), mix[:, ch]) for ch in range(2)], 1) * gain[:, None]
        if not banner:
            return np.clip(out, -0.98, 0.98)
        ban = sound(sr, self.speed) * 0.82                           # banner peak ~ -3 dBFS, like our mix
        for k, at in enumerate(self.stops):
            b0 = at + RAMP / 2 + PRE + k * self.extra
            i0 = int(round(b0 * sr))
            nn = min(len(ban), n_out - i0)
            out[i0:i0 + nn] += ban[:nn]
        return np.clip(out, -0.98, 0.98)
