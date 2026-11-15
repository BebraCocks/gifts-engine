"""Общие события картинки и звука: границы сцен, удары музыки (бит), рекламная пауза."""
import numpy as np
from timeline import ON, END, AD_STOP, DUR
import music

BEATS = music.beats_in_content()          # времена сильных долей музыки во времени содержания


def snap(t, win=0.22):
    """Ближайшая доля музыки в пределах win, иначе t."""
    if not len(BEATS):
        return t
    b = BEATS[np.argmin(np.abs(BEATS - t))]
    return float(b) if abs(b - t) <= win else t


# Сцены (время содержания); v3 — «монохром видно сразу», затем «Это…» → RubUp (~62 %), без нарастающей подводки
HOOK = ON[1]
LOOK = snap(ON[2] - 0.05)               # «Смотри» — наезд: подарки в центр крупно (правка друга автора)
PRICE_X10 = snap(ON[2] + 2.6)            # «дороже в десять раз»
INTRO = snap(ON[3] - 0.05)
COUNTER = snap(ON[3] + 2.4)              # «трёх видов»
SPIN = snap(ON[4] + 1.0)                 # «менять наряды»
TYPE1 = snap(ON[5] - 0.1)
TYPE1_ZOOM = snap(ON[5] + 4.0)           # «почти идеально»
TYPE2 = snap(ON[6] - 0.1)
TYPE2_NAMES = snap(ON[6] + 2.6)          # «Киберпанк … тоже Киберпанк»
TYPE2_COLOR = snap(ON[7] + 1.3)          # «а по цвету»
SEEN = snap(ON[8] - 0.05)                # «Монохром видно сразу»
TEASE = snap(ON[9] - 0.1)                # «А третий вид — самый крутой. Это…» → RubUp
TYPE3 = ON[10] - 0.05                    # сразу после рекламы — ответ «Чёрно-белый монохром!»
TYPE3_ZOOM = snap(ON[11] + 2.6)          # «огромная удача»
WHY = snap(ON[12] - 0.1)
ORDER = snap(ON[12] + 2.6)               # «мозг любит порядок»
OUTRO = snap(ON[13] - 0.1)
CREEPY = ON[14] - 0.05

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
