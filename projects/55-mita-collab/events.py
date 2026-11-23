"""События 55 (время содержания). Опорные слова — data/words_asr.json."""
import json
from pathlib import Path
from timeline import ON, END, DUR

W = json.loads((Path(__file__).resolve().parent / 'data' / 'words_asr.json').read_text(encoding='utf-8'))['words']


def at(word, n=0, after=0.0):
    w0 = word.lower().replace('ё', 'е')
    return [s for w, s, e in W if w.lower().replace('ё', 'е') == w0 and s >= after - 1e-6][n]


# переходы между нарядами/локациями: (начало, длительность)
T1 = (END[1] + 0.05, 0.6)          # «загрузка матча»: комната → арена
T2 = (END[4] + 0.05, 0.85)         # «распаковка»: арена → магазин
T3 = (END[7] + 0.1, 0.55)          # «затвор камеры»: магазин → студия
T4 = (END[11] + 0.15, 0.55)        # «свайп ленты»: студия → комната
# 1 хук
HOOK_Q = at('стандоффе') - 0.05
# 2–4 игры
SO2 = at('стандофф') - 0.1
CHARM = at('брелки') - 0.05
GRAF = at('граффити') - 0.05
SKIN = at('скины') - 0.05
AGENT = at('агенты') - 0.05
TOURN = at('турниров') - 0.1
NFT3 = at('nft', 0, ON[3] + 5) - 0.05
PROMO = at('телеграм', 0, ON[4]) - 0.1
TYPE0 = at('промики') - 0.35
APPLY = at('голду') - 0.15
GOLD = at('голду') + 0.05
CASE = at('кейсы') - 0.05
STICK = at('стикеры') - 0.15
# 5–7 мерч
SCREEN = at('экрана') - 0.1
HOLD = at('подержать') - 0.4
MERCH = at('мерч', 0, ON[5]) - 0.05
PLUSH = at('плюшевые') - 0.05
HOODIE = at('худи') - 0.05
FIGURE = at('фигурки') - 0.05
QR = at('кью-ар') - 0.1
SCAN = at('сканируешь') - 0.05
RARE = at('телегу') - 0.05
CREEPY = ON[7] - 0.1
CREEPY_END = END[7] + 0.15
# 8–11 блогеры
IDEA3 = ON[8]
VIEWS = at('ролик') - 0.1
VIEWS_HIT = at('просмотров') + 0.1
AWARD = at('телеграм', 0, ON[9]) - 0.1
TGCARD = at('nft', 0, ON[9]) - 0.1
LIMIT = at('тысяча') - 0.1
GRID = at('блогеры', 0, ON[10]) - 0.1
MILLION = at('миллионы') - 0.1
WINK = at('кстати') - 0.05
# 12–13 итог
SUM = [at('игры', 0, ON[12]) - 0.05, at('мерч', 0, ON[12]) - 0.05, at('блогеры', 0, ON[12]) - 0.05]
MERGE = at('одному') - 0.2
CARDS = [at('первая', 0, ON[13]) - 0.1, at('вторая', 0, ON[13]) - 0.1, at('третья', 0, ON[13]) - 0.1]
WRITE = at('пиши') - 0.1
