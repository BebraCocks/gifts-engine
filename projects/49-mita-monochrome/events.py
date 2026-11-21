"""Общие события картинки и звука: границы сцен, удары музыки (бит), рекламная пауза."""
import numpy as np
from timeline import ON, END, AD_STOP, DUR
import music
from words import WORDS


def at(word, n=0, after=0.0):
    """Начало слова (время содержания) по меткам ASR: n-е вхождение после after."""
    w0 = word.lower().replace('ё', 'е')
    hits = [s for w, s, e, _ in WORDS if w.lower().strip('.,!?…:;«»—').replace('ё', 'е') == w0 and s >= after - 1e-6]
    return hits[n]

BEATS = music.beats_in_content()          # времена сильных долей музыки во времени содержания


def snap(t, win=0.22):
    """Ближайшая доля музыки в пределах win, иначе t."""
    if not len(BEATS):
        return t
    b = BEATS[np.argmin(np.abs(BEATS - t))]
    return float(b) if abs(b - t) <= win else t


# Сцены (время содержания); v3 — «монохром видно сразу», затем «Это…» → RubUp (~62 %), без нарастающей подводки
HOOK = ON[1]
LOOK = 0.0                              # v6: «Смотри» — первое слово ролика; подарки крупно в центре с первого кадра
PRICE_X10 = at('десять') + 0.1          # «дороже в десять раз»
INTRO = snap(ON[3] - 0.05)
COUNTER = at('трёх') - 0.05              # «трёх видов»
SPIN = at('переодеваться') - 0.1         # «буду переодеваться»
TYPE1 = snap(ON[5] - 0.1)
TYPE1_ZOOM = at('точно') - 0.05          # «так точно»
TYPE2 = snap(ON[6] - 0.1)
TYPE2_NAMES = at('тоже') - 0.1           # «Киберпанк … тоже Киберпанк»
TYPE2_COLOR = at('цвета') - 0.1          # «а цвета иногда спорят»
SEEN = snap(ON[8] - 0.05)                # «Монохром видно сразу»
TEASE = snap(ON[9] - 0.1)                # «А третий вид — самый крутой. Это…» → RubUp
TYPE3 = ON[10] - 0.05                    # сразу после рекламы — ответ «Чёрно-белый монохром!»
TYPE3_ZOOM = at('настоящая') - 0.05      # «настоящая удача»
WHY = snap(ON[12] - 0.1)
ORDER = at('порядок') - 0.1              # «мозг обожает порядок»
OUTRO = snap(ON[13] - 0.1)
CREEPY = 1e9                             # v5: жуткой концовки нет (эффекты финала отключены)

def beats_after(t, n=3, min_gap=0.22, max_gap=0.75):
    """n последовательных долей после t (для появления карточек «под бит»); если долей мало — равный шаг 0,29 с."""
    out, cur = [], t
    for _ in range(n):
        nxt = BEATS[BEATS > cur + min_gap]
        if len(nxt) and nxt[0] - cur <= max_gap:
            cur = float(nxt[0])
        else:
            cur = cur + 0.29
        out.append(cur)
    return out


HOOK_POPS = beats_after(0.05, 2)
CARD_POPS = {
    'type1': beats_after(TYPE1 + 0.05),
    'type2': beats_after(TYPE2 + 0.05),
    'tease': beats_after(TEASE + 0.05),
    'type3': beats_after(TYPE3 + 0.1),
    'outro': beats_after(OUTRO),
}
