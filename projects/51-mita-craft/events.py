"""Общие события картинки и звука (время содержания). Опорные слова — words.WORDS."""
from timeline import ON, END, AD_STOP, DUR
from words import WORDS


def at(word, n=0, after=0.0):
    """Начало n-го вхождения слова (после времени after); ё = е, без знаков препинания."""
    w0 = word.lower().replace('ё', 'е')
    hits = [s for w, s, e, _ in WORDS if w.lower().strip('.,!?…:;«»').replace('ё', 'е') == w0 and s >= after - 1e-6]
    return hits[n]


def end_of(word, n=0, after=0.0):
    w0 = word.lower().replace('ё', 'е')
    hits = [e for w, s, e, _ in WORDS if w.lower().strip('.,!?…:;«»').replace('ё', 'е') == w0 and s >= after - 1e-6]
    return hits[n]


# хук (обычный наряд)
HOOK_NFT = at('странные') - 0.15                 # три крафтовые модели появляются
HOOK_NO = at('улучшением') - 0.1                 # «нельзя получить улучшением»
HOOK_CRAFT = at('сделать') - 0.1                 # 4 подарка слетаются в один
KNOCK = at('смотри') - 1.7                       # фишка: стук по экрану (клип knock, удары ≈ 1,75 и 2,05 с)
KNOCK_HITS = [KNOCK + 1.75, KNOCK + 2.05]
# щелчок и смена наряда
SNAP = END[1] + 0.05
SNAP_DUR = 3.08
CRAFT_IN = SNAP + 2.0                            # слоты крафта появляются уже при приземлении
# крафт: 1–4 подарка
WALK1 = max(ON[2] - 0.05, SNAP + SNAP_DUR)       # Мита отходит влево (сразу после щелчка)
SLOTS = [at('одного', 0, ON[2]) - 0.05, at('четырех', 0, ON[2]) - 0.1, at('четырех', 0, ON[2]) + 0.12,
         at('четырех', 0, ON[2]) + 0.34]
CHANCE = at('больше', 0, ON[2]) - 0.1            # «Чем больше — тем выше шанс»
NEVER = at('ста', 0, ON[2]) - 0.1                # «но ста процентов не бывает никогда»
BURN = at('сгорят', 0, ON[3]) - 0.15             # подарки вспыхивают
# жуть
CREEPY = ON[4] - 0.12
CREEPY_CLOSE = at('остаются', 0, ON[4]) - 0.55   # наезд → крупный план
CREEPY_MID = at('здесь', 0, ON[4]) - 0.1
CREEPY_FULL = at('со', 0, ON[4]) - 0.15
CREEPY_END = ON[5] - 0.12                        # снова мило
# редкости
TIER_ONLY = at('модели', 0, ON[5]) - 0.1
TIERS = [at('четыре', 0, ON[5]) - 0.05 + 0.18 * k for k in range(4)]
TEASE = ON[6] - 0.08
# эпические (после рекламы)
EPIC = ON[7] - 0.05
EPIC_BASE = at('эпические', 0, ON[7]) - 0.1
EPIC_CHEAP = at('одна', 0, ON[7]) - 0.05
EPIC_RICH = at('другая', 0, ON[7]) - 0.05
SHUFFLE = ON[8] - 0.05
SHUF_SHOW = at('необычный', 0, ON[8]) - 0.1
SHUF_LEG = at('легендарки', 0, ON[8]) - 0.2
SHUF_X2 = at('два', 0, ON[8]) - 0.1
CHEAP = ON[9] - 0.05
SWEEP = at('больше', 0, ON[9]) - 0.05            # взмах — россыпь дешёвых крафтовых
FOUR = at('четыре', 0, ON[9]) - 0.1              # «чем четыре подарка»
WHY = ON[10] - 0.05
WALK2 = ON[10] - 0.05
LOVE = at('нравится', 0, ON[10]) - 0.15
OUTRO = ON[11] - 0.05
OUTRO_PILL = at('пиши', 0, ON[11]) - 0.05
CHOICE = at('выбирай', 0, ON[11]) - 0.1          # фишка: выбор как в игре
SAVE = SNAP + 2.2                                # фишка: «сохранение…» после переодевания
LOADING = CREEPY_END + 0.05                      # фишка: «загрузка» на выходе из жути
PUNCH = [BURN + 0.05, ON[7] - 0.02, SHUF_X2, SWEEP + 0.1]   # лёгкие наезды камеры
