"""Общие события картинки и звука (время содержания). Опорные слова — data/words_asr.json. v3 (2026-11-17)."""
import json
from pathlib import Path
from timeline import ON, END, AD_STOP, DUR
W = json.loads((Path(__file__).resolve().parent / 'data' / 'words_asr.json').read_text(encoding='utf-8'))['words']


def at(word, n=0, after=0.0):
    """Начало n-го вхождения слова (после времени after); ё = е."""
    w0 = word.lower().replace('ё', 'е')
    hits = [s for w, s, e in W if w.lower().strip('.,!?…').replace('ё', 'е') == w0 and s >= after]
    return hits[n]


def end_of(word, n=0, after=0.0):
    w0 = word.lower().replace('ё', 'е')
    hits = [e for w, s, e in W if w.lower().strip('.,!?…').replace('ё', 'е') == w0 and s >= after]
    return hits[n]


HOOK = ON[1]
REVEAL_L = at('подарками') - 0.05              # v5: левая карточка раскрывается на «с подарками»
REVEAL_R = at('телеге') - 0.05                 # v5: правая (на чёрном) — на «в телеге»
HOOK_PRICE = at('точно') - 0.05                # «точно так же» — цена чёрного растёт                  # «готовы платить больше» — цена чёрного растёт
SPIN = END[1] + 0.12                             # v4: кружение сразу после «Сейчас объясню!»
X7 = ON[3] - 0.05                                # «Чёрный фон — самый дорогой…»
CARD_GRAB = at('тот', 0, ON[3]) - 0.35           # «Тот же самый подарок…» — Мита берёт кекс
CARD_SHOW = at('намного', 0, ON[3]) - 0.25       # подносит к камере
PUMPKIN = ON[4] - 0.05
PUMP_CHEAP = at('обычная', 0, ON[4]) - 0.05
PUMP_BLACK = at('сорока', 0, ON[4]) - 0.1
UFC, UFC_CHEAP, UFC_BLACK = PUMPKIN, PUMP_CHEAP, PUMP_BLACK      # совместимость со сценами v3
LOCKET = ON[5] - 0.05
LOCKET_HIT = at('семнадцать') - 0.1
CREEPY = ON[6] - 0.05                            # «Но вот что странно…» — жуть
CREEPY_END = at('черный', 0, ON[6]) - 0.12       # щелчок — снова мило
GACHA = [at('выпадает', 0, ON[6]) - 0.05, at('бордовый', 0, ON[6]) - 0.1, at('медный', 0, ON[6]) - 0.1]
RARITY = CREEPY
RARITY_SAME = GACHA[1]
TEASE = ON[7] - 0.05
DEMAND = ON[8] - 0.05
ICONS = [at('карты') - 0.2, at('машины') - 0.2, at('смокинги') - 0.2]
GLOW = ON[9] - 0.05
GLOW_PHONE = at('темной', 0, ON[9]) - 0.1
GLOW_SHOW = at('светится', 0, ON[9]) - 0.2
PLAIN = ON[10] - 0.05
KICK = at('просто', 0, ON[10]) - 0.1
PRICE = ON[11] - 0.05
PRICE_UP = at('растет') - 0.6
OUTRO = ON[12] - 0.05
OUTRO_LUX = at('роскошный') - 0.1
OUTRO_MIN = at('базовый') - 0.1
OUTRO_PILL = at('пиши') - 0.05
