"""События ролика 54 v4 (время содержания, до вставки рекламы). Опорные слова — words.WORDS.
Схема k: IN — детектив представляет (мошенница заходит), SAY — мошенница говорит, OUT — разоблачение и защита."""
from timeline import ON, END, AD_STOP, DUR
from words import WORDS


def at(word, n=0, after=0.0):
    w0 = word.lower().replace('ё', 'е')
    hits = [s for w, s, e, _ in WORDS if w.lower().strip('.,!?…:;«»—').replace('ё', 'е') == w0 and s >= after - 1e-6]
    return hits[n]


def end_of(word, n=0, after=0.0):
    w0 = word.lower().replace('ё', 'е')
    hits = [e for w, s, e, _ in WORDS if w.lower().strip('.,!?…:;«»—').replace('ё', 'е') == w0 and s >= after - 1e-6]
    return hits[n]


# 1 хук: обычная Мита → лупа → детектив
HOOK_MSG = at('интересен') - 0.2
LENS0 = at('как') - 0.15
LENS1 = LENS0 + 1.5
COUNTER_IN = LENS1 + 0.1
# 2–4 фейковый оффер (мошенница справа)
OFFER = ON[2]
OFFER_SAY, OFFER_SAY_END = ON[3], END[3]
OFFER_CARD = at('пятьсот') - 0.1
OFFER_OUT = ON[4]
LANG = at('смени') - 0.15
REAL = at('настоящее') - 0.1
FAKE = at('фейк', 0, ON[4]) - 0.35
STAMP1 = at('фейк', 0, ON[4]) + 0.05          # штамп на «фейк» — мошенница убегает раньше
# 5–7 клон (мошенница слева)
CLONE = ON[5]
CLONE_SAY, CLONE_SAY_END = ON[6], END[6]
ASK = at('спроси') - 0.1
FOX_FLIP = at('клон') - 0.1
STAMP2 = at('спроси') + 0.35        # «спроси то, что знает только друг» — клон теряется и убегает (до жути)
# 8 жуть «это я»
CREEPY = ON[8] - 0.2
CREEPY_END = END[8] + 0.2
# 9 крючок → реклама
TEASE = ON[9]
# 10–12 ссылка-двойник (справа)
LINK = ON[10]
LINK_SAY, LINK_SAY_END = ON[11], END[11]
LINK_MSG = at('ссылочку') - 0.2
LINK_LENS = at('переходи') - 0.2
STAMP3 = at('сайт-двойник') + 0.3     # «сайт-двойник» — штамп, мошенница убегает пораньше
# 13–15 обмен «ты первый» (слева)
SWAP = ON[13]
SWAP_SAY, SWAP_SAY_END = ON[14], END[14]
SWAP_FINGERS = at('первый', 0, ON[14]) - 0.2
STAMP4 = at('честный') + 0.05      # «Честный человек не попросит…» — пустая коробка под эти слова
# 16–18 гарант (справа)
GUAR = ON[16]
GUAR_SAY, GUAR_SAY_END = ON[17], END[17]
GUAR_FOX = at('мошенник', 0, ON[18]) - 0.3
STAMP5 = at('мошенник', 0, ON[18]) - 0.1
GUAR_SAFE = at('сделки', 0, ON[18]) - 0.1
# 19 памятка
MEMO = ON[19]
NOTE1 = at('первым', 0, ON[19]) - 0.3
NOTE2 = at('слово', 0, ON[19]) - 0.3
NOTE3 = at('ссылкам', 0, ON[19]) - 0.3
# 20 финал: папки «БЫЛО / НЕ БЫЛО»
MOVE2 = ON[20] - 0.45
CHOICE = at('пиши', 0, ON[20]) - 0.1
STAMPS = [STAMP1, STAMP2, STAMP3, STAMP4, STAMP5]
SCHEME_T = [OFFER, CLONE, LINK, SWAP, GUAR]
SAY = [(OFFER_SAY, OFFER_SAY_END), (CLONE_SAY, CLONE_SAY_END), (LINK_SAY, LINK_SAY_END), (SWAP_SAY, SWAP_SAY_END),
       (GUAR_SAY, GUAR_SAY_END)]
