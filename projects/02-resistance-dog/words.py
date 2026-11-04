"""Word timing from Fish Audio ASR of the selected takes (voice/LNN.asr.json), in content seconds.
Caption spelling is corrected where ASR differs from the script (names, brands, numbers)."""
import json
from timeline import FILE_ON, TAKES, HAS_NARRATION, ON, END
from script import LINES, plain

FIX = {'споти': 'Спотти', 'спойте': 'Спотти', 'адуров': 'А Дуров', 'анонимус': 'Anonymous', 'чегивара': 'Че Гевара', 'вошь': 'вождь', 'черный': 'чёрный', 'блокировки': 'блокировке', 'telegram': 'Телеграм', 'чагивара': 'Че Гевара', 'чагевара': 'Че Гевара', 'рембо': 'Рэмбо',
       'импостер': 'Imposter', 'прокси-сервер': 'Proxy Server', 'анонимус': 'Anonymous',
       'токиннатон': 'токен на TON', 'пес': 'пёс', 'ушел': 'ушёл', 'черном': 'чёрном',
       'самолетики': 'самолётики', 'четвертом': 'четвёртом', 'живет': 'живёт'}

WORDS = []          # per line: [(caption word, start, end)]
for k, (spoken, chapter, pause) in enumerate(LINES):
    out = []
    if HAS_NARRATION:
        segs = json.loads(TAKES[k].with_suffix('.asr.json').read_text(encoding='utf-8'))['segments']
        j = 0
        while j < len(segs):
            s = segs[j]
            w = s['text'].strip()
            key = w.lower().strip('.,!?:;')
            nxt = segs[j + 1]['text'].lower().strip('.,!?:;') if j + 1 < len(segs) else ''
            if key == 'прокси' and nxt == 'сервер':
                out.append(('Proxy Server', FILE_ON[k] + s['start'], FILE_ON[k] + segs[j + 1]['end']))
                j += 2
                continue
            if w.isdigit() and nxt == 'года':           # '2018 года' -> one caption '2018'
                out.append((w, FILE_ON[k] + s['start'], FILE_ON[k] + segs[j + 1]['end']))
                j += 2
                continue
            if key == 'токин' and j + 1 < len(segs) and segs[j + 1]['text'].lower().startswith('натон'):
                out.append(('токен на TON', FILE_ON[k] + s['start'], FILE_ON[k] + segs[j + 1]['end']))
                j += 2
                continue
            if key in FIX:
                w = FIX[key]
            out.append((w, FILE_ON[k] + s['start'], FILE_ON[k] + s['end']))
            j += 1
    else:
        split = plain(spoken).split()
        step = (END[k] - ON[k]) / max(1, len(split))
        out = [(w, ON[k] + i * step, ON[k] + (i + 1) * step) for i, w in enumerate(split)]
    WORDS.append(out)


def wt(line, word, occurrence=0, edge='start'):
    """Content time of a word in line `line` (1-based, like L01). Matches case-insensitively by prefix."""
    hits = [(a, b) for w, a, b in WORDS[line - 1] if w.lower().strip('.,!?:;').startswith(word.lower())]
    a, b = hits[occurrence]
    return a if edge == 'start' else b


if __name__ == '__main__':
    for k, ws in enumerate(WORDS, 1):
        print(k, ' '.join(f'{w}@{a:.2f}' for w, a, b in ws))
