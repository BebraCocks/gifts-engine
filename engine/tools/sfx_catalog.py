"""Analyse the SFX library in input/sfx/ and write catalog.json + CATALOG.md.

    python -B engine/tools/sfx_catalog.py                  # (re)build the catalog
    python -B engine/tools/sfx_catalog.py --show click     # table of one role (or a file name part)
    python -B engine/tools/sfx_catalog.py --sheet whoosh   # waveform + spectrogram sheet -> .cache/sfx/
    python -B engine/tools/sfx_catalog.py --audition click # all variants of a role in one WAV/MP3 to listen

What is measured per file (and per hit inside a file, see «segments»):
  dur / active        full length and length above -40 dB of the file's own peak, seconds
  peak_db, rms_db     sample peak and RMS of the active part, dBFS
  attack_ms           from the first audible sample to 90 % of the loudest 5 ms window
  peak_t, tail_s      where the loudest moment is and how long it rings after it
  segments            separate hits (gap >= 0.12 s of near silence) -> one file can hold several clicks
  onsets              transient count (spectral flux) -> «one tap» vs «a burst of taps»
  centroid_hz         spectral centre of mass: < 1.5 kHz dark, > 4 kHz bright
  bands               energy share: low < 250 Hz, mid 250-2k, high 2-8k, air > 8 kHz
  flatness            0 tonal (pitched, musical) ... 1 noise (air, paper, static)
  level_slope         dB/s of the loudness trend: > 0 grows (riser), < 0 dies away
  pitch_slope         octaves/s of the brightness trend: > 0 rises, < 0 falls (power down)
  width               side/mid energy: 0 mono ... ~1 very wide
Roles come from the pack folder/name (see ROLE_RULES), tags from the numbers above.
Numbers find candidates and defects; whether a sound fits is decided by listening.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import find_peaks, stft

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paths  # noqa: E402

SR = 48000
LIB = paths.INPUT / 'sfx'
CATALOG = LIB / 'catalog.json'
REPORT = LIB / 'CATALOG.md'
EXT = {'.flac', '.wav', '.mp3', '.ogg', '.m4a', '.aif', '.aiff'}
VERSION = 1

# (regex on the path inside the library, role). First match wins. Roles are generic so that other
# packs can reuse them; a pack without rules gets the role from its folder name.
ROLE_RULES = [
    (r'/button/(mouse|mechanical|metalic)', 'click'),
    (r'/button/(button-cursor-select|magnetic)', 'select'),
    (r'/button/granular-button-select', 'select-soft'),
    (r'/button/correct', 'confirm'),
    (r'/button/error', 'error'),
    (r'/button/pop-up', 'popup'),
    (r'/button/sparkle', 'sparkle'),
    (r'/cartoon/cartoon-(pop|blink|wink)', 'pop'),
    (r'/cartoon/cartoon-(boing|spring)', 'boing'),
    (r'/cartoon/cartoon-(bonk|smash|fly-crash|expressions-impact)', 'cartoon-hit'),
    (r'/cartoon/cartoon-(whoosh|slide-up|flute|falling|run|transition|spin|slip|stretch)', 'cartoon-move'),
    (r'/cartoon/cartoon-coin', 'coin'),
    (r'/cartoon/', 'cartoon'),
    (r'/countdown-list/(count|number)', 'counter'),
    (r'/countdown-list/', 'list'),
    (r'/foley/camera-shutter', 'shutter'),
    (r'/foley/coin', 'coin'),
    (r'/foley/(paper|trash|lamination)', 'paper'),
    (r'/foley/', 'foley'),
    (r'/glitch-flicker/scan', 'scan'),
    (r'/glitch-flicker/glitch-flicker-text', 'glitch-text'),
    (r'/glitch-flicker/', 'glitch'),
    (r'/granular-combo/', 'granular-combo'),
    (r'/granular/number-code', 'scan'),
    (r'/granular/granular-glitch', 'glitch-texture'),
    (r'/granular/', 'granular-move'),
    (r'/human/', 'voice'),
    (r'/impact-hit/(impact-sub|impact-wobbler)', 'sub-drop'),
    (r'/impact-hit/riser-bang', 'riser-hit'),
    (r'/impact-hit/impact-engine', 'power-down'),
    (r'/impact-hit/', 'impact'),
    (r'/music-transition/', 'music-transition'),
    (r'/power-down-up/.*(down|slow)', 'power-down'),
    (r'/power-down-up/', 'power-up'),
    (r'/transform/(flip|spin)', 'flip'),
    (r'/transform/risers', 'riser'),
    (r'/transform/shimmer', 'sparkle'),
    (r'/transform/stretch', 'stretch'),
    (r'/transform/', 'transform'),
    (r'/transition/botanical/', 'whoosh-organic'),
    (r'/transition/dj-spinner/', 'spinback'),
    (r'/transition/musical/musical-downlifter', 'downlifter'),
    (r'/transition/(musical|risers)/', 'riser'),
    (r'/transition/sparkle/sparkle-whoosh', 'sparkle-whoosh'),
    (r'/transition/sparkle/', 'sparkle'),
    (r'/transition/whoosh/deep-mini', 'whoosh-short'),
    (r'/transition/whoosh/deeper', 'whoosh-deep'),
    (r'/transition/whoosh/', 'whoosh'),
    (r'/transition/', 'transition'),
    (r'/typing/v\d-enter', 'key-enter'),
    (r'/typing/v\d-backspace', 'key-backspace'),
    (r'/typing/v\d-space$', 'key-space'),
    (r'/typing/', 'typing'),
    (r'/ambience/', 'ambience'),
    (r'/bg-atmosphere/', 'bed'),
]

# Roles that are meant to be heard as one long piece: never split into hits, never pitched.
WHOLE = {'bed', 'ambience', 'music-transition', 'riser', 'downlifter', 'power-up', 'power-down',
         'typing', 'voice', 'list', 'counter', 'granular-combo', 'spinback', 'riser-hit'}


def decode(path, ch=None):
    if ch is None:
        out = subprocess.run([paths.ffprobe(), '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                              'stream=channels', '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
        ch = min(2, int(out.stdout.strip() or 1))
    raw = subprocess.run([paths.ffmpeg(), '-v', 'error', '-i', str(path), '-f', 'f32le', '-ac', str(ch),
                          '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<f4').astype(np.float64).reshape(-1, ch)


def role_of(rel):
    key = '/' + rel.rsplit('.', 1)[0]
    for rx, role in ROLE_RULES:
        if re.search(rx, key):
            return role
    parts = rel.split('/')
    return parts[-2] if len(parts) > 1 else 'misc'


def envelope(mono, hop=240):
    n = len(mono) // hop
    if n == 0:
        return np.array([1e-9])
    e = np.sqrt(np.mean(mono[:n * hop].reshape(n, hop) ** 2, 1))
    return np.maximum(e, 1e-9)


def find_segments(env_db, hop_s, long_file):
    """Hits separated by >= 0.12 s below -45 dB (relative to the loudest window)."""
    act = env_db > -45
    if long_file or not act.any():
        idx = np.flatnonzero(act)
        return [(int(idx[0]), int(idx[-1]) + 1)] if len(idx) else [(0, len(env_db))]
    gap = int(round(0.12 / hop_s))
    segs, start, quiet = [], None, 0
    for i, a in enumerate(act):
        if a:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet >= gap:
                segs.append((start, i - quiet + 1))
                start, quiet = None, 0
    if start is not None:
        segs.append((start, len(act) - quiet))
    return [s for s in segs if (s[1] - s[0]) * hop_s >= 0.02] or [(0, len(env_db))]


def spectral(mono):
    if len(mono) < 2048:
        mono = np.pad(mono, (0, 2048 - len(mono)))
    f, t, Z = stft(mono, SR, nperseg=2048, noverlap=1536)
    P = np.abs(Z) ** 2 + 1e-18
    frame_e = P.sum(0)
    live = frame_e > frame_e.max() * 1e-4
    Pm = P[:, live].mean(1)
    band = (f >= 40) & (f <= 18000)
    cen = float((f[band] * Pm[band]).sum() / Pm[band].sum())
    flat = float(np.exp(np.mean(np.log(Pm[band]))) / np.mean(Pm[band]))
    tot = Pm[band].sum()
    bands = {k: round(float(Pm[(f >= a) & (f < b)].sum() / tot), 3)
             for k, (a, b) in dict(low=(40, 250), mid=(250, 2000), high=(2000, 8000), air=(8000, 18000)).items()}
    # brightness trend over time (octaves per second) on the audible frames
    c_t = (f[:, None] * P).sum(0) / P.sum(0)
    tt, cc = t[live], np.log2(np.maximum(c_t[live], 20))
    pslope = float(np.polyfit(tt, cc, 1)[0]) if len(tt) > 3 and tt[-1] - tt[0] > 0.15 else 0.0
    # onsets: positive spectral flux peaks
    logP = np.log10(P)
    flux = np.maximum(np.diff(logP, axis=1), 0).sum(0)
    flux = flux / (flux.max() + 1e-12)
    pk, _ = find_peaks(flux, height=max(0.25, np.median(flux) + 4 * np.median(np.abs(flux - np.median(flux)))),
                       distance=max(1, int(0.06 * SR / 512)))
    return cen, flat, bands, pslope, len(pk)


def analyse(path, rel):
    x = decode(path)
    mono = x.mean(1)
    dur = len(mono) / SR
    peak = float(np.abs(x).max()) if len(x) else 0.0
    role = role_of(rel)
    hop = 240
    hop_s = hop / SR
    env = envelope(mono, hop)
    env_db = 20 * np.log10(env / env.max())
    segs = find_segments(env_db, hop_s, dur > 8 or role in WHOLE)
    act = env_db > -40
    a_idx = np.flatnonzero(act)
    a0, a1 = (a_idx[0], a_idx[-1] + 1) if len(a_idx) else (0, len(env))
    active = (a1 - a0) * hop_s
    loud = mono[a0 * hop:a1 * hop]
    rms = float(np.sqrt(np.mean(loud ** 2))) if len(loud) else 0.0
    pk_i = int(np.argmax(env))
    reach = np.flatnonzero(env[a0:pk_i + 1] >= 0.9 * env[pk_i])
    attack = ((reach[0] if len(reach) else 0)) * hop_s
    after = np.flatnonzero(env_db[pk_i:] > -40)
    tail = (after[-1] if len(after) else 0) * hop_s
    seg_part = env_db[a0:a1]
    lslope = float(np.polyfit(np.arange(len(seg_part)) * hop_s, seg_part, 1)[0]) if len(seg_part) > 20 else 0.0
    cen, flat, bands, pslope, onsets = spectral(mono[: SR * 30])
    width = 0.0
    if x.shape[1] == 2:
        mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
        width = float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mid ** 2)) + 1e-12))
    seg_list = []
    for s0, s1 in segs:
        b0 = max(0, s0 * hop - int(0.005 * SR))
        b1 = min(len(mono), s1 * hop + int(0.03 * SR))
        part = mono[b0:b1]
        p_i = int(np.argmax(envelope(part, hop))) * hop_s if len(part) else 0.0
        seg_list.append([round(b0 / SR, 3), round(b1 / SR, 3), round(p_i, 3)])
    item = dict(
        file=rel, role=role, dur=round(dur, 3), active=round(active, 3), channels=int(x.shape[1]),
        peak_db=round(20 * np.log10(peak + 1e-12), 1), rms_db=round(20 * np.log10(rms + 1e-12), 1),
        attack_ms=round(attack * 1000), peak_t=round(pk_i * hop_s, 3), tail_s=round(tail, 3),
        onsets=onsets, segments=seg_list, centroid_hz=round(cen), flatness=round(flat, 3), bands=bands,
        level_slope=round(lslope, 1), pitch_slope=round(pslope, 2), width=round(width, 2))
    item['tags'] = tags(item)
    return item


def tags(it):
    t = []
    a = it['active']
    t.append('micro' if a < 0.15 else 'short' if a < 0.6 else 'medium' if a < 2 else 'long' if a < 8 else 'bed')
    c = it['centroid_hz']
    t.append('dark' if c < 1500 else 'bright' if c > 4000 else 'neutral')
    t.append('noisy' if it['flatness'] > 0.25 else 'tonal' if it['flatness'] < 0.05 else 'mixed')
    if it['attack_ms'] <= 15:
        t.append('sharp')
    elif it['attack_ms'] >= 300:
        t.append('swell')
    if it['bands']['low'] > 0.45:
        t.append('bassy')
    if a > 0.6 and it['level_slope'] > 6:
        t.append('rising')
    if a > 0.6 and it['level_slope'] < -12:
        t.append('decaying')
    if it['pitch_slope'] > 0.4:
        t.append('pitch-up')
    elif it['pitch_slope'] < -0.4:
        t.append('pitch-down')
    if len(it['segments']) > 1:
        t.append('multi')
    elif it['onsets'] >= 4 and a < 3:
        t.append('burst')
    if it['width'] > 0.5:
        t.append('wide')
    elif it['width'] < 0.05:
        t.append('mono')
    return t


def files():
    return sorted(p for p in LIB.rglob('*') if p.is_file() and p.suffix.lower() in EXT)


def build(force=False):
    old = {}
    if CATALOG.is_file() and not force:
        data = json.loads(CATALOG.read_text(encoding='utf-8'))
        if data.get('version') == VERSION:
            old = {s['file']: s for s in data['sounds']}
    out = []
    fs = files()
    for k, p in enumerate(fs):
        rel = p.relative_to(LIB).as_posix()
        st = p.stat()
        sig = [st.st_size]
        if rel in old and old[rel].get('sig') == sig:
            it = old[rel]                       # measurements cached; roles and tags follow the current rules
            it['role'] = role_of(rel)
            it['tags'] = tags(it)
            out.append(it)
            continue
        it = analyse(p, rel)
        it['sig'] = sig
        out.append(it)
        print(f'[{k + 1}/{len(fs)}] {rel}  {it["role"]}  {" ".join(it["tags"])}', flush=True)
    CATALOG.write_text(json.dumps(dict(version=VERSION, sr=SR, sounds=out), ensure_ascii=False, indent=0),
                       encoding='utf-8')
    write_report(out)
    print(f'{len(out)} sounds -> {CATALOG.relative_to(paths.ROOT)}, {REPORT.relative_to(paths.ROOT)}')


def write_report(items):
    by = {}
    for it in items:
        by.setdefault(it['role'], []).append(it)
    hits = sum(len(it['segments']) for it in items)
    lines = ['# Каталог SFX', '',
             'Создан `engine/tools/sfx_catalog.py` — не редактировать вручную.',
             f'Файлов: {len(items)}, отдельных ударов/вариантов: {hits}, ролей: {len(by)}.', '',
             'Колонки: длительность / звучащая часть (с), атака (мс), хвост после пика (с), '
             'центр спектра (Гц), число ударов в файле, теги. Смысл чисел — в docstring скрипта.', '',
             '| Роль | Файлов | Ударов | Звучит, с | Пример |', '|---|---|---|---|---|']
    for role in sorted(by):
        g = by[role]
        act = sorted(it['active'] for it in g)
        lines.append(f'| `{role}` | {len(g)} | {sum(len(i["segments"]) for i in g)} | '
                     f'{act[0]:.2f}–{act[-1]:.2f} | `{g[0]["file"]}` |')
    for role in sorted(by):
        lines += ['', f'## {role}', '', '| Файл | Длит. / звучит | Атака | Хвост | Центр | Удары | Теги |',
                  '|---|---|---|---|---|---|---|']
        for it in sorted(by[role], key=lambda i: i['file']):
            lines.append(f'| `{it["file"].split("/", 1)[-1]}` | {it["dur"]:.2f} / {it["active"]:.2f} | '
                         f'{it["attack_ms"]} | {it["tail_s"]:.2f} | {it["centroid_hz"]} | '
                         f'{len(it["segments"])} | {" ".join(it["tags"])} |')
    REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def select(items, query):
    return [it for it in items if it['role'] == query or query in it['file']]


def load_items():
    if not CATALOG.is_file():
        build()
    return json.loads(CATALOG.read_text(encoding='utf-8'))['sounds']


def sheet(query):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    items = select(load_items(), query)[:40]
    if not items:
        raise SystemExit('nothing matches ' + query)
    fig, ax = plt.subplots(len(items), 2, figsize=(16, 1.3 * len(items)), squeeze=False,
                           gridspec_kw=dict(width_ratios=[1, 1]))
    for r, it in enumerate(items):
        m = decode(LIB / it['file']).mean(1)[: SR * 12]
        t = np.arange(len(m)) / SR
        ax[r, 0].plot(t, m, lw=0.4)
        for s in it['segments']:
            ax[r, 0].axvspan(s[0], s[1], alpha=0.12, color='g')
        ax[r, 0].set_title(f'{it["file"]}  ·  {" ".join(it["tags"])}', loc='left', fontsize=7)
        ax[r, 1].specgram(m + 1e-9, NFFT=1024, Fs=SR, noverlap=768, vmin=-130, vmax=-30)
        ax[r, 1].set_ylim(0, 16000)
        for a in ax[r]:
            a.tick_params(labelsize=6)
    out = paths.CACHE / 'sfx' / f'sheet_{re.sub(r"[^a-z0-9]+", "-", query.lower())}.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out, dpi=60)
    print(out)


def audition(query):
    """Every hit of the matching sounds in a row, 0.5 s apart, with a spoken-free index in the cue list."""
    items = select(load_items(), query)
    if not items:
        raise SystemExit('nothing matches ' + query)
    parts, cues, t = [], [], 0.0
    for it in items:
        x = decode(LIB / it['file'], 2)
        for k, (s0, s1, _) in enumerate(it['segments']):
            y = x[int(s0 * SR):int(s1 * SR)][: SR * 8]
            pk = np.abs(y).max() + 1e-9
            parts += [y * (0.7 / pk), np.zeros((int(0.5 * SR), 2))]
            cues.append(f'{t:7.2f}  {it["file"]}#{k}')
            t += len(y) / SR + 0.5
    out = paths.CACHE / 'sfx' / f'audition_{re.sub(r"[^a-z0-9]+", "-", query.lower())}'
    out.parent.mkdir(parents=True, exist_ok=True)
    y = np.concatenate(parts)
    subprocess.run([paths.ffmpeg(), '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-',
                    '-c:a', 'libmp3lame', '-b:a', '192k', str(out) + '.mp3'],
                   input=y.astype('<f4').tobytes(), check=True)
    Path(str(out) + '.txt').write_text('\n'.join(cues) + '\n', encoding='utf-8')
    print(str(out) + '.mp3')
    print(str(out) + '.txt')


def show(query):
    for it in select(load_items(), query):
        print(f'{it["file"]:70s} {it["active"]:6.2f}s att {it["attack_ms"]:4d}ms cen {it["centroid_hz"]:5d} '
              f'seg {len(it["segments"]):2d}  {" ".join(it["tags"])}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--force', action='store_true', help='re-analyse every file')
    ap.add_argument('--show', metavar='ROLE_OR_TEXT')
    ap.add_argument('--sheet', metavar='ROLE_OR_TEXT')
    ap.add_argument('--audition', metavar='ROLE_OR_TEXT')
    a = ap.parse_args()
    if a.show:
        show(a.show)
    elif a.sheet:
        sheet(a.sheet)
    elif a.audition:
        audition(a.audition)
    else:
        build(a.force)


if __name__ == '__main__':
    main()
