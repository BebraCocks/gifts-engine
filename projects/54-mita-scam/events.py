"""События ролика 54 (время содержания, до вставки рекламы). Опорные слова — words.WORDS."""
from timeline import ON, END, AD_STOP, DUR
from words import WORDS


def at(word, n=0, after=0.0):
    w0 = word.lower().replace('ё', 'е')
    hits = [s for w, s, e, _ in WORDS if w.lower().strip('.,!?…:;«»—').replace('ё', 'е') == w0 and s >= after - 1e-6]
    return hits[n]


# 1 хук: обычная Мита, сообщение «покупателя»; лупа-разоблачение → детектив
HOOK_MSG = at('интересен') - 0.2
LENS0 = at('как') - 0.15
LENS1 = LENS0 + 1.5
COUNTER_IN = LENS1 + 0.1
# 2 фейковый оффер
OFFER = ON[2]
OFFER_CARD = at('пишет') - 0.1
LANG = at('смени') - 0.15
REAL = at('настоящее') - 0.1
FAKE = at('фейк', 0, ON[2]) - 0.1
STAMP1 = END[2] - 0.15
# 3 клон друга
CLONE = ON[3]
FRIEND_MSG = at('просит', 0, ON[3]) - 0.1
ASK = at('спроси') - 0.1
FOX_FLIP = at('клон') - 0.1
STAMP2 = at('растеряется') - 0.05
# 4 жуть «это я»
CREEPY = ON[4] - 0.2
CREEPY_END = END[4] + 0.2
# 5 крючок → реклама
TEASE = ON[5]
# 6 ссылка на сайт-двойник
LINK = ON[6]
LINK_MSG = at('покупатель') - 0.1
LINK_LENS = at('переходи') - 0.2
STAMP3 = END[6] - 0.1
# 7 обмен «ты первый»
SWAP = ON[7]
SWAP_MSG = at('давай', 0, ON[7]) - 0.1
SWAP_SENT = at('первый', 0, ON[7]) + 0.2
SWAP_GONE = at('честный') - 0.1
STAMP4 = END[7] - 0.1
# 8 гарант
GUAR = ON[8]
GUAR_MSG = ON[8] + 0.1
GUAR_FOX = at('мошенник', 0, ON[8]) - 0.4
GUAR_SAFE = at('сделки', 0, ON[8]) - 0.1
STAMP5 = END[8] - 0.1
# 9 памятка
MEMO = ON[9]
NOTE1 = at('первым', 0, ON[9]) - 0.3
NOTE2 = at('слово', 0, ON[9]) - 0.3
NOTE3 = at('сделки', 0, ON[9]) - 0.1
# 10 финал: папки «БЫЛО / НЕ БЫЛО»
MOVE2 = ON[10] - 0.45
CHOICE = at('пиши', 0, ON[10]) - 0.1
STAMPS = [STAMP1, STAMP2, STAMP3, STAMP4, STAMP5]
SCHEME_T = [OFFER, CLONE, LINK, SWAP, GUAR]
