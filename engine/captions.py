"""Word-level captions, estimated timing and anchor corrections. Validate timing against actual narration."""
import functools
import math
import re
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import paths

WHITE = (255, 255, 255)
ACCENT = (255, 255, 255)  # choose an accent from the new visual brief
VOWELS = set("аеёиоуыэюяaeiouy")


# ------------------------------------------------------------------ timing
def _syllables(word):
    if not re.sub(r"[\W_]", "", word):
        return 0                                         # dashes, ellipses: silent
    v = sum(1 for c in word.lower() if c in VOWELS)
    if v == 0:
        v = max(1, len(re.sub(r"\W", "", word)) // 3)    # numbers, abbreviations
    return v


def _voice_env(wav_path):
    with wave.open(str(wav_path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    hop = sr // 100
    env = np.array([np.sqrt((x[k:k + hop] ** 2).mean()) for k in range(0, len(x) - hop, hop)])
    return 20 * np.log10(env + 1e-6)


def _segments(db, start=None, end=None, min_gap=0.12):
    thr = db.max() - 30
    on = db > thr
    i0 = int((start or 0) * 100)
    i1 = int(end * 100) if end else len(db)
    segs, s = [], None
    for k in range(i0, i1):
        if on[k] and s is None:
            s = k
        elif not on[k] and s is not None:
            segs.append([s, k])
            s = None
    if s is not None:
        segs.append([s, i1])
    merged = []
    for a, b in segs:
        if merged and (a - merged[-1][1]) < min_gap * 100:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a / 100, b / 100) for a, b in merged if b - a >= 4]


def estimate_word_times(wav_path, text, offset=0.0, speech_start=None, speech_end=None):
    """Estimate when each word of `text` starts in a voice take.

    Speech is split into voiced chunks at pauses; text is split into clauses at punctuation.
    If both counts match, each clause gets its chunk; otherwise words are spread by syllable
    count over voiced time only (silences are skipped). Returns [(word, absolute_start), ...]
    with absolute = offset + time inside the file. Check the result on review frames.
    """
    words = text.split()
    db = _voice_env(wav_path)
    segs = _segments(db, speech_start, speech_end)
    if not segs or not words:
        return [(w, offset) for w in words]
    clauses, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[,.!?;:—–…]$", w) or w in ("—", "–"):
            clauses.append(cur)
            cur = []
    if cur:
        clauses.append(cur)

    def spread(ws, t0, t1):
        syl = np.array([_syllables(w) for w in ws], float)
        if syl.sum() == 0:
            syl[:] = 1
        starts = t0 + (t1 - t0) * np.concatenate([[0], np.cumsum(syl)[:-1]]) / syl.sum()
        return list(zip(ws, starts))

    out = []
    if len(clauses) == len(segs):
        for ws, (a, b) in zip(clauses, segs):
            out += spread(ws, a, b)
    else:
        voiced = np.array([b - a for a, b in segs])
        cum = np.concatenate([[0], np.cumsum(voiced)])
        syl = np.array([_syllables(w) for w in words], float)
        frac = np.concatenate([[0], np.cumsum(syl)[:-1]]) / syl.sum()
        for w, f in zip(words, frac):
            tv = f * cum[-1]
            k = min(int(np.searchsorted(cum, tv, side="right") - 1), len(segs) - 1)
            out.append((w, segs[k][0] + (tv - cum[k])))
    return [(w, offset + float(t)) for w, t in out]


NUMBER_WORDS = set("""ноль один одна два две три четыре пять шесть семь восемь девять десять одиннадцать двенадцать
тринадцать четырнадцать пятнадцать шестнадцать семнадцать восемнадцать девятнадцать двадцать тридцать сорок пятьдесят
шестьдесят семьдесят восемьдесят девяносто сто двести триста четыреста пятьсот шестьсот семьсот восемьсот девятьсот
сто ста тысяча тысячи тысячу тысяч целых целая десятых десятая сотых процента процент процентов
первый второй третий четвёртый четвертый пятый шестой седьмой восьмой девятый десятый двадцатый тридцатый
сороковой пятидесятый шестидесятый семидесятый восьмидесятый девяностый сотый тысячный
первого второго третьего четвёртого четвертого пятого шестого седьмого восьмого девятого десятого одиннадцатого
двенадцатого тринадцатого четырнадцатого пятнадцатого шестнадцатого семнадцатого восемнадцатого девятнадцатого
двадцатого двухтысячного""".split())


def align(spoken_times, caption_text):
    """Map timings of the spoken text (numbers in words, names in Cyrillic) onto the caption text
    (digits, Latin names). A caption token with a digit takes all following spoken number words;
    other tokens take one spoken word each. Use a no-break space inside numbers ("1 900")."""
    cap = [w for w in re.split(r"[ \t\n]+", caption_text) if w]   # keeps no-break spaces inside tokens
    out, j = [], 0
    for tok in cap:
        if j >= len(spoken_times):
            out.append((tok, spoken_times[-1][1]))
            continue
        t = spoken_times[j][1]
        if re.search(r"\d", tok):
            j += 1
            while j < len(spoken_times) and re.sub(r"[^\w]", "", spoken_times[j][0].lower()) in NUMBER_WORDS:
                j += 1
        else:
            j += 1
        out.append((tok.replace(" ", " "), t))
    return out


def phrase(word_times, accent=(), end=None, hold=0.35):
    """Build a phrase from [(word, start)]; `accent` = set of words (exact text) to colour."""
    ws = [(w, t, w in accent or w.strip(",.!?:;«»\"") in accent) for w, t in word_times]
    last = ws[-1][1] if ws else 0
    return {"words": ws, "end": end if end is not None else last + 0.45 + hold}


# ------------------------------------------------------------------ rendering
@functools.lru_cache(maxsize=4096)
def _word_sprite(text, size, weight, color, shadow, stroke=0):
    f = ImageFont.truetype(paths.font(f"SF-Pro-Text-{weight}.otf"), size)
    l, t_, r, b = f.getbbox(text)
    pad = 10
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (r - l + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if shadow:
        d.text((pad - l, pad + 3), text, font=f, fill=(0, 0, 0, 120))
    if stroke:
        d.text((pad - l, pad), text, font=f, fill=(0, 0, 0, 0), stroke_width=stroke, stroke_fill=(10, 10, 14, 200))
    d.text((pad - l, pad), text, font=f, fill=color + (255,))
    return im, pad, f.getlength(text), f.getlength(" ")


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Captions:
    def __init__(self, phrases, width=960, top=170, size=58, weight="Bold", max_lines=2, line_gap=1.18,
                 align="center", color=WHITE, accent_color=ACCENT, shadow=True, frame_w=1080,
                 appear=0.12, rise=14, fade_out=0.25, lead=0.10, stroke=0):
        self.phrases = sorted(phrases, key=lambda p: p["words"][0][1] if p["words"] else 0)
        self.width, self.top, self.size, self.weight = width, top, size, weight
        self.max_lines, self.line_h = max_lines, int(size * line_gap)
        self.align, self.color, self.accent_color, self.shadow = align, color, accent_color, shadow
        self.frame_w, self.appear, self.rise, self.fade_out = frame_w, appear, rise, fade_out
        self.lead = lead            # words start appearing slightly before their sound
        self.stroke = stroke        # dark outline (px) for busy / bright backgrounds
        self._pages = [self._paginate(p) for p in self.phrases]

    def _paginate(self, ph):
        """Lay words into lines; a word that would open line max_lines+1 starts a new page."""
        pages, lines, line, x = [], [], [], 0.0
        for w, t, acc in ph["words"]:
            _, _, wlen, space = _word_sprite(w, self.size, self.weight, self.color, self.shadow)
            need = wlen if not line else x + space + wlen
            if line and need > self.width:
                lines.append(line)
                line, x = [], 0.0
                if len(lines) == self.max_lines:
                    pages.append(lines)
                    lines = []
            line.append((w, t, acc, 0.0 if not line else x + space))
            x = (0.0 if len(line) == 1 else x + space) + wlen
        if line:
            lines.append(line)
        if lines:
            pages.append(lines)
        out = []
        for k, pg in enumerate(pages):
            start = pg[0][0][1]
            nxt = pages[k + 1][0][0][1] if k + 1 < len(pages) else ph["end"]
            out.append((start, nxt, pg, k + 1 == len(pages)))
        return out

    def layer(self, t):
        """RGBA layer for time t, or None. Returns (image, x0, y0) in frame pixels.

        The newest page that has started wins: a page change is a clean reset (no overlap),
        only the last page of a phrase fades out."""
        best = None
        for pages in self._pages:
            for start, end, pg, last in pages:
                t_off = end + (self.fade_out if last else 0.0)
                if start - self.lead <= t < t_off and (best is None or start > best[0]):
                    best = (start, end, pg, last)
        if best is None:
            return None
        start, end, pg, last = best
        fade = 1.0 - _smooth((t - end) / self.fade_out) if (last and t > end) else 1.0
        h = self.line_h * len(pg) + 40
        im = Image.new("RGBA", (self.frame_w, h), (0, 0, 0, 0))
        for li, line in enumerate(pg):
            lw = line[-1][3] + _word_sprite(line[-1][0], self.size, self.weight, self.color, self.shadow)[2]
            x0 = (self.frame_w - lw) / 2 if self.align == "center" else (self.frame_w - self.width) / 2
            for w, ts, acc, xo in line:
                k = (t - ts + self.lead) / self.appear
                if k <= 0:
                    continue
                a = _smooth(k) * fade
                col = self.accent_color if acc else self.color
                spr, pad, _, _ = _word_sprite(w, self.size, self.weight, col, self.shadow, self.stroke)
                if a < 0.999:
                    spr = spr.copy()
                    spr.putalpha(spr.getchannel("A").point(lambda v, a=a: int(v * a)))
                dy = self.rise * (1 - _smooth(k))
                im.alpha_composite(spr, (int(round(x0 + xo - pad)), int(round(li * self.line_h + dy))))
        return im, 0, self.top


def retime(word_times, anchors):
    """Correct estimated word times with known anchors {word_index: true_start}. Words between anchors
    are moved piecewise-linearly (keeps their order and relative spacing); outside, they shift."""
    if not anchors:
        return word_times
    idx = sorted(anchors)
    src = [word_times[i][1] for i in idx]
    dst = [anchors[i] for i in idx]
    out = []
    for i, (w, t) in enumerate(word_times):
        if t <= src[0]:
            nt = t + (dst[0] - src[0])
        elif t >= src[-1]:
            nt = t + (dst[-1] - src[-1])
        else:
            nt = float(np.interp(t, src, dst))
        out.append((w, nt))
    return out
