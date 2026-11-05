"""Decode new audio assets, trim silence, normalise and filter. No sound pack is bundled."""
import functools
import subprocess

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

import paths

PACK = paths.INPUT / "sfx"


def _decode(path, sr, ch, start=0.0, dur=None):
    cmd = [paths.ffmpeg(), "-v", "error"]
    if start:                                   # "-ss 0" before -i returns nothing for very short FLACs
        cmd += ["-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", str(path), "-f", "f32le", "-acodec", "pcm_f32le", "-ac", str(ch), "-ar", str(sr), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    x = np.frombuffer(raw, "<f4").astype(np.float64)
    return x.reshape(-1, ch) if ch > 1 else x


@functools.lru_cache(maxsize=256)
def _load(path, sr, trim_db, max_dur):
    x = _decode(path, sr, 1)
    if trim_db is not None and len(x):
        thr = np.abs(x).max() * 10 ** (trim_db / 20)
        k = np.argmax(np.abs(x) > thr)
        x = x[max(0, k - int(0.003 * sr)):]
    if max_dur:
        n = int(max_dur * sr)
        if len(x) > n:
            x = x[:n].copy()
            f = min(len(x), int(0.05 * sr))
            x[-f:] *= np.linspace(1, 0, f)
    pk = np.abs(x).max() if len(x) else 0
    return x / pk if pk > 0 else x


def load(path, sr=48000, trim_db=-40, max_dur=None):
    """Mono, peak-normalised, leading silence below trim_db (relative to peak) removed."""
    return _load(str(path), sr, trim_db, max_dur)


def SFX(name, sr=48000, max_dur=None):
    """A sound from input/sfx/ by file name (extension optional)."""
    hits = [p for p in PACK.rglob("*") if p.is_file() and (p.name == name or p.stem == name)]
    if not hits:
        raise FileNotFoundError(f"{name!r} not in {PACK}")
    return load(hits[0], sr, max_dur=max_dur)


def load_stereo(path, sr=48000, start=0.0, dur=None):
    return _decode(path, sr, 2, start, dur)


def underwater(x, sr, fc=600.0, order=4, body=0.25, mix=1.0):
    """Muffled «under water»: steep low-pass + a little low-mid body, keeps the groove, loses the air.
    mix = effect amount (dry/wet): 1 = fully under water, 1/3 = a third of the effect. Zero-phase filters,
    so blending with the dry signal does not comb."""
    sos = butter(order, fc, "low", fs=sr, output="sos")
    sos2 = butter(2, [120, 380], "band", fs=sr, output="sos")
    filt = sosfilt if mix >= 1.0 else sosfiltfilt
    wet = filt(sos, x, axis=0) + body * filt(sos2, x, axis=0)
    if mix >= 1.0:
        return wet
    dry = x / (np.sqrt(np.mean(x ** 2)) + 1e-12) * np.sqrt(np.mean(wet ** 2))     # dry matched to the wet level
    return mix * wet + (1 - mix) * dry


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.asarray(x) ** 2)) + 1e-12)