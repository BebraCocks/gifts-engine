"""Общая карта событий: слова, переходы, удары. Одни времена для картинки и звука.
С озвучкой (voice/V01.wav…V14.wav и WITHOUT_NARRATION = False) слова берут время из речи;
без неё — оценочное время чтения по окну отрезка."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine'))
import config
from script import DUR, AD_STOP, BLOCKS, SEGMENTS, VOICE, VOICE_WIN

HERE = Path(__file__).resolve().parent
VOICE_FILES = [HERE / 'voice' / f'V{k:02d}.wav' if VOICE[k - 1] else None for k in range(1, len(SEGMENTS) + 1)]
HAS_VOICE = not config.WITHOUT_NARRATION and all(p.is_file() for p in VOICE_FILES if p)
STRIP = '.,:—«»…?!'


def merge_short(pairs):
    """[(слово, t)] → короткие предлоги/союзы склеиваются со следующим словом (время первого)."""
    out, carry, t_carry = [], '', None
    for w, t in pairs:
        if len(w.strip(STRIP)) <= 2 and w != '87' and not w.endswith(('.', ',', '?')):
            carry += w + ' '
            t_carry = t if t_carry is None else t_carry
        else:
            out.append((carry + w, t if t_carry is None else t_carry)); carry, t_carry = '', None
    if carry:
        w, t = out[-1]; out[-1] = (w + ' ' + carry.strip(), t)
    return out


WORDS = []          # (слово, начало, конец, стиль)
VOICE_AT = []       # (файл, сдвиг клипа в содержании, конец речи)
if HAS_VOICE:
    import captions
    import voice
    captions.NUMBER_WORDS.update({'восьмом', 'второго', 'девятого', 'восемьдесят', 'семь', 'одна', 'десятая'})
for k, (a, b, text, style) in enumerate(SEGMENTS):
    nxt = SEGMENTS[k + 1][0] if k + 1 < len(SEGMENTS) else DUR
    if HAS_VOICE and VOICE_FILES[k]:
        path = VOICE_FILES[k]
        on, end = voice.onset_end(path)
        va = VOICE_WIN[k][0]
        nva = VOICE_WIN[k + 1][0] if k + 1 < len(VOICE_WIN) else DUR
        offset = va - on                              # начало речи = начало окна речи
        VOICE_AT.append((path, offset, va + end - on))
        spoken = captions.estimate_word_times(str(path), VOICE[k], offset=offset, speech_start=on, speech_end=end)
        tokens = merge_short(captions.align(spoken, ' '.join(text.split())))
        last_end = min(va + end - on + 0.35, nva - 0.02)
    else:
        raw = merge_short([(w, 0.0) for w in text.split()])
        weights = [len(w.strip(STRIP)) + 4 for w, _ in raw]
        t, tokens = a, []
        for (w, _), q in zip(raw, weights):
            tokens.append((w, t)); t += (b - a) * q / sum(weights)
        last_end = b
    for j, (w, t0) in enumerate(tokens):
        t1 = tokens[j + 1][1] - 0.01 if j + 1 < len(tokens) else last_end
        WORDS.append((w, t0, max(t1, t0 + 0.12), style))

# Переходы между локациями (середина скрещивания) — для картинки и звука
TRANSITIONS = {
    'mirror': 5.55,          # гримёрка → пригород (пролёт сквозь зеркало)
    'window': 15.42,         # пригород → Лондон
    'petals': 24.45,         # Лондон → Мадрид (после рекламы)
    'notes': 32.55,          # Мадрид → Бронкс
    'skyward': 40.65,        # Бронкс → Готэм
    'signal': 48.85,         # Готэм → сцена
}
MASK_LAND = 2.45             # маска садится на лицо
FLIPS = [2.93, 3.41, 3.89, 4.37, 4.85]   # смены масок в хуке (последняя — назад к Ghostface)
CURTAIN = 51.7               # занавес закрывается
