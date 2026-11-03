"""Общая карта событий: слова, переходы, удары. Одни времена для картинки и звука."""
from script import DUR, AD_STOP, BLOCKS, SEGMENTS

WORDS = []          # (слово, начало, конец, стиль)
for a, b, text, style in SEGMENTS:
    words, carry = [], ''
    for w in text.split():                      # короткие предлоги/союзы — вместе со следующим словом
        if len(w.strip('.,:—«»…?')) <= 2 and w not in ('87',) and not w.endswith(('.', ',', '?')):
            carry += w + ' '
        else:
            words.append(carry + w); carry = ''
    if carry:
        words[-1] += ' ' + carry.strip()
    weights = [len(w.strip('.,:—«»…?')) + 4 for w in words]
    total = sum(weights)
    t = a
    for w, k in zip(words, weights):
        dt = (b - a) * k / total
        WORDS.append((w, t, t + dt, style))
        t += dt
for k in range(len(WORDS) - 1):                     # слово держится до следующего, без наложения
    w, t0, t1, s = WORDS[k]
    if WORDS[k + 1][1] - t1 < 0.15:
        WORDS[k] = (w, t0, WORDS[k + 1][1] - 0.01, s)

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
