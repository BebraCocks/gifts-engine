"""Общие события картинки и звука (время содержания). Опорные слова — data/words_asr.json."""
import json
from pathlib import Path
from timeline import ON, END, AD_STOP, DUR
W = json.loads((Path(__file__).resolve().parent / 'data' / 'words_asr.json').read_text(encoding='utf-8'))['words']


def at(word, n=0, after=0.0):
    """Начало n-го вхождения слова (после времени after)."""
    hits = [s for w, s, e in W if w.lower().strip('.,!?') == word.lower() and s >= after]
    return hits[n]


HOOK = ON[1]
HOOK_PRICE = at('больше') - 0.1                  # «готовы платить больше» — цена чёрного растёт
SPIN = at('переоденусь') + 0.15                  # кружение-переход в готику
X7 = ON[3] - 0.05
X7_BADGE = at('семь', 0, ON[3]) - 0.05           # «в семь раз»
PLAYER = ON[4] - 0.05
PLAYER_HIT = at('проигрыватель') - 0.05
LOCKET = ON[5] - 0.05
LOCKET_HIT = at('семнадцать') - 0.1
RARITY = ON[6] - 0.05
RARITY_SAME = at('бордовый') - 0.1
TEASE = ON[7] - 0.05
DEMAND = ON[8] - 0.05
ICONS = [at('карты') - 0.2, at('машины') - 0.2, at('смокинги') - 0.2]
GLOW = ON[9] - 0.05
GLOW_PHONE = at('темной', 0, ON[9]) - 0.1
PLAIN = ON[10] - 0.05
PRICE = ON[11] - 0.05
PRICE_UP = at('растет') - 0.6
OUTRO = ON[12] - 0.05
OUTRO_MIN = at('базовый') - 0.1
OUTRO_PILL = at('Пиши') - 0.05
