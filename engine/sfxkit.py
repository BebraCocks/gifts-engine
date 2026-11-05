"""Default SFX from the library in input/sfx/ (Botanica V4), with variety inside and across videos.

    import sfxkit
    kit = sfxkit.Kit(HERE)                        # project folder -> its own seed and usage record
    fx = np.zeros((n, 2))
    for t in CLICKS:
        kit.add(fx, 'click', t, gain_db=-14)      # a different click every time, no machine-gun effect
    kit.add(fx, 'whoosh*', CUT, align='peak')     # the loudest moment of the whoosh lands on the cut
    kit.add(fx, 'riser', DROP, align='end')       # the riser finishes exactly at DROP
    kit.add(fx, 'sub-drop', DROP, key='drop')     # same key -> the same sound each time (a motif)
    kit.save()                                    # build/sfx_cues.json + docs/SFX-USAGE.json

Roles are listed in input/sfx/CATALOG.md. A role may be a glob ('whoosh*') or a list. Filters:
dur=(min, max) seconds of audible length, tags=('bright',), exclude_tags=('bassy',), file='substring'.

Variety rules (so that videos do not sound the same):
- inside one video every role is a shuffled bag: a variant is not repeated until the bag is empty, and
  never twice in a row; files holding several hits are split, so each hit is its own variant;
- across videos the picks are weighted away from sounds used by other projects in docs/SFX-USAGE.json
  (recent projects weigh more), so a new video gets mostly sounds the previous ones did not use;
- every instance gets a small random gain (±1 dB) and pitch (±0.3 semitone) offset; if the bag has to
  repeat a variant within 4 s, the repeat is shifted further (1-2 semitones) so a series never sounds
  identical. Use vary=False for voices, beds and anything that must stay exact.
The picks are deterministic for a project (seeded by its folder name), so re-renders sound the same.
"""
import fnmatch
import json
import random
import zlib
from datetime import date
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

import paths
import sound

LIB = paths.INPUT / 'sfx'
CATALOG = LIB / 'catalog.json'
USAGE = paths.ROOT / 'docs' / 'SFX-USAGE.json'
NO_PITCH = {'bed', 'ambience', 'voice', 'music-transition', 'typing', 'key-enter', 'key-backspace', 'key-space'}
TARGET_RMS_DB = -20.0           # every variant is levelled to this before gain_db, peak kept <= -1 dBFS


def catalog():
    if not CATALOG.is_file():
        raise FileNotFoundError('Run: python -B engine/tools/sfx_catalog.py  (input/sfx/catalog.json missing)')
    return json.loads(CATALOG.read_text(encoding='utf-8'))['sounds']


def roles():
    out = {}
    for it in catalog():
        out[it['role']] = out.get(it['role'], 0) + len(it['segments'])
    return dict(sorted(out.items()))


def _usage():
    if USAGE.is_file():
        return json.loads(USAGE.read_text(encoding='utf-8'))
    return {}


class Kit:
    def __init__(self, project_dir, sr=48000, seed=None, history=True):
        self.dir = Path(project_dir).resolve()
        self.name = self.dir.name
        self.sr = sr
        self.rng = random.Random(seed if seed is not None else zlib.crc32(self.name.encode()))
        self.items = catalog()
        self.bags = {}
        self.last = {}                  # variant id -> last content time it was placed at
        self.keys = {}
        self.cues = []
        self._files = {}
        self.penalty = {}
        if history:
            others = [(v.get('date', ''), p, v) for p, v in _usage().items() if p != self.name]
            for rank, (_, _, v) in enumerate(sorted(others, reverse=True)):
                w = 0.85 if rank < 3 else 0.5 if rank < 8 else 0.25        # recent projects push harder
                for vid in v.get('sounds', []):
                    self.penalty[vid] = min(0.95, self.penalty.get(vid, 0) + w)

    # ------------------------------------------------------------------ choice
    def variants(self, role, dur=None, tags=(), exclude_tags=(), file=None):
        pats = [role] if isinstance(role, str) else list(role)
        out = []
        for it in self.items:
            if not any(fnmatch.fnmatchcase(it['role'], p) for p in pats):
                continue
            if file and file not in it['file']:
                continue
            if any(t not in it['tags'] for t in tags) or any(t in it['tags'] for t in exclude_tags):
                continue
            for k, (s0, s1, pk) in enumerate(it['segments']):
                if dur and not (dur[0] <= s1 - s0 <= dur[1]):
                    continue
                out.append((f'{it["file"]}#{k}', it, s0, s1, pk))
        if not out:
            raise LookupError(f'No SFX for role={role!r} dur={dur} tags={tags}. See input/sfx/CATALOG.md')
        return out

    def pick(self, role, key=None, **flt):
        if key is not None and key in self.keys:
            return self.keys[key]
        bag_id = json.dumps([role, sorted(flt.items())], default=str)
        bag = self.bags.get(bag_id)
        if not bag:
            pool = self.variants(role, **flt)
            weights = [(1.0 - self.penalty.get(v[0], 0.0)) * self.rng.uniform(0.6, 1.0) for v in pool]
            # weighted shuffle: fresh sounds first, sounds used by other videos at the end of the bag
            order = sorted(range(len(pool)), key=lambda i: -weights[i] * self.rng.random() ** 0.35)
            bag = [pool[i] for i in order]
            prev = self.bags.get(bag_id + '#last')
            if prev and len(bag) > 1 and bag[0][0] == prev:
                bag.append(bag.pop(0))
            self.bags[bag_id] = bag
        v = bag.pop(0)
        self.bags[bag_id + '#last'] = v[0]
        if key is not None:
            self.keys[key] = v
        return v

    # ------------------------------------------------------------------ audio
    def _audio(self, v):
        vid, it, s0, s1, _ = v
        if it['file'] not in self._files:                 # whole file, then slice: ffmpeg -ss fails on tiny FLACs
            self._files[it['file']] = sound.load_stereo(LIB / it['file'], self.sr)
        full = self._files[it['file']]
        x = full[int(round(s0 * self.sr)):int(round(s1 * self.sr))].copy()
        if not len(x):
            x = full.copy()
        rms = np.sqrt(np.mean(x ** 2)) + 1e-12
        x = x * (10 ** (TARGET_RMS_DB / 20) / rms)
        pk = np.abs(x).max()
        if pk > 0.89:
            x *= 0.89 / pk
        f = min(len(x) // 4, int(0.004 * self.sr))
        if f > 1:
            x[:f] *= np.linspace(0, 1, f)[:, None]
            x[-f:] *= np.linspace(1, 0, f)[:, None]
        return x

    def get(self, role, t=None, vary=True, key=None, semitones=0.0, **flt):
        """(stereo array, info) for one placement; t is only used to detect close repeats."""
        v = self.pick(role, key=key, **flt)
        x = self._audio(v)
        shift = semitones
        g = 0.0
        if vary and key is None and v[1]['role'] not in NO_PITCH:
            shift += self.rng.uniform(-0.3, 0.3)
            g = self.rng.uniform(-1.0, 1.0)
            if t is not None and v[0] in self.last and abs(t - self.last[v[0]]) < 4.0:
                shift += self.rng.choice([-1, 1]) * self.rng.uniform(1.0, 2.0)
        if abs(shift) > 0.01:
            r = Fraction(2 ** (shift / 12)).limit_denominator(200)     # play faster = higher pitch
            x = resample_poly(x, r.denominator, r.numerator, axis=0)
        if t is not None:
            self.last[v[0]] = t
        ratio = 2 ** (-shift / 12)
        return x * 10 ** (g / 20), dict(id=v[0], role=v[1]['role'], peak=v[4] * ratio, dur=len(x) / self.sr,
                                        semitones=round(shift, 2), gain_jitter_db=round(g, 2))

    def add(self, buf, role, t, gain_db=-12.0, pan=0.0, align='start', vary=True, key=None, semitones=0.0,
            fit=None, fade_out=0.05, label=None, **flt):
        """Mix one SFX into buf (N, 2) at content time t. align: 'start' | 'peak' | 'end'.
        fit=seconds trims a long sound (beds, ambience) with a fade_out. Returns the cue dict."""
        x, info = self.get(role, t=t, vary=vary, key=key, semitones=semitones, **flt)
        if fit:
            n = int(fit * self.sr)
            if len(x) > n:
                x = x[:n].copy()
                f = min(n, int(fade_out * self.sr))
                x[-f:] *= np.linspace(1, 0, f)[:, None]
        off = {'start': 0.0, 'peak': info['peak'], 'end': len(x) / self.sr}[align]
        t0 = t - off
        i0 = int(round(t0 * self.sr))
        a = max(0, -i0)
        n = min(len(x) - a, len(buf) - max(0, i0))
        if n > 0:
            pl, pr = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2), np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
            g = 10 ** (gain_db / 20)
            buf[max(0, i0):max(0, i0) + n, 0] += x[a:a + n, 0] * g * min(1.0, pl)
            buf[max(0, i0):max(0, i0) + n, 1] += x[a:a + n, 1] * g * min(1.0, pr)
        cue = dict(t=round(t0, 3), at=round(t, 3), align=align, gain_db=gain_db, pan=pan, label=label, **info)
        self.cues.append(cue)
        return cue

    # ------------------------------------------------------------------ records
    def save(self, breaks=None):
        """build/sfx_cues.json (content and output time) and this project's line in docs/SFX-USAGE.json."""
        out = paths.build(self.dir) / 'sfx_cues.json'
        cues = []
        for c in self.cues:
            c = dict(c)
            c['out_t'] = round(out_time(breaks, c['t']), 3) if breaks else c['t']
            cues.append(c)
        out.write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding='utf-8')
        data = _usage()
        data[self.name] = dict(date=date.today().isoformat(), sounds=sorted({c['id'] for c in self.cues}))
        USAGE.write_text(json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=1) + '\n',
                         encoding='utf-8')
        return out


def out_time(breaks, t):
    """Content time -> output time (approximate inside the slow-down ramps)."""
    return t + breaks.extra * sum(1 for at in breaks.stops if at <= t)


def write_review(project_dir, fx, mix_out, breaks, sr=48000, cues=None):
    """Listening files for the author next to the highlight frames, all in OUTPUT time (match the video):
    build/review/sfx_only.mp3 — SFX alone; build/review/mix.mp3 — the full mix; sfx_cues.txt — time list."""
    import subprocess
    rev = paths.build(project_dir) / 'review'
    rev.mkdir(parents=True, exist_ok=True)
    fx_out = breaks.audio(fx, sr, banner=False) if breaks else fx
    for name, data in (('sfx_only', fx_out), ('mix', mix_out)):
        subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '2', '-i', '-',
                        '-c:a', 'libmp3lame', '-b:a', '192k', str(rev / (name + '.mp3'))],
                       input=np.clip(data, -1, 1).astype('<f4').tobytes(), check=True)
    if cues:
        lines = ['out_t  роль               звук (файл#удар)  [label]']
        for c in sorted(cues, key=lambda c: c['t']):
            t = out_time(breaks, c['t']) if breaks else c['t']
            lines.append(f'{t:6.2f}  {c["role"]:18s} {c["id"]}  {c.get("label") or ""}'.rstrip())
        (rev / 'sfx_cues.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return rev
