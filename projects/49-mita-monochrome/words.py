"""Слова для субтитров: текст script.py (орфография, «ё») + времена Fish ASR pro (data/words_asr.json).
WORDS = [(слово для экрана, начало, конец, номер реплики)], время содержания. Дефисные слова — одно слово на экране."""
import difflib
import json
import re
from pathlib import Path
import script

HERE = Path(__file__).resolve().parent
ASR = json.loads((HERE / 'data' / 'words_asr.json').read_text(encoding='utf-8'))['words']
NUM = {'10': 'десять'}


def norm(w):
    w = NUM.get(w, w).lower().replace('ё', 'е')
    return re.sub(r'[^a-zа-я0-9]', '', w)


def clean(text):
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    return [w for w in text.replace('—', ' ').split() if re.search(r'\w', w)]


def build():
    disp, parts = [], []                    # disp: (слово, реплика); parts: (норм. часть, индекс disp)
    for li, (txt, _, _) in enumerate(script.LINES, 1):
        for w in clean(txt):
            disp.append((w, li))
            for p in w.split('-'):
                if norm(p):
                    parts.append((norm(p), len(disp) - 1))
    a = [p for p, _ in parts]
    b = [norm(w) for w, _, _ in ASR]
    times = [None] * len(parts)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ('equal', 'replace') and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                times[i1 + k] = (ASR[j1 + k][1], ASR[j1 + k][2])
    out = []
    for di, (w, li) in enumerate(disp):
        ts = [times[k] for k, (_, d) in enumerate(parts) if d == di and times[k]]
        if not ts:
            continue
        out.append((w, ts[0][0], ts[-1][1], li))
    return out


WORDS = build()

if __name__ == '__main__':
    n = sum(len(clean(t)) for t, _, _ in script.LINES)
    print(len(WORDS), 'из', n)
    print(WORDS[:12])
