"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['conor']] + 0.25        # RubUp right after the Khabib block (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'five_word': wt('hook', 'пять'),
    'five': on('five', -0.1),
    'n0': wt('five', 'снуп'), 'n1': wt('five', 'сумка'), 'n2': wt('five', 'сигара'),
    'n3': wt('five', 'лоурайдер'), 'n4': wt('five', 'вестсайд'),
    'sold': on('sold', -0.15),
    'million': wt('sold', 'миллион'),
    'half': wt('sold', 'полчаса'),
    'usd': wt('sold', 'двенадцать'),
    'second': on('second', -0.1),
    'series': wt('second', 'вторую'),
    'khabib': on('khabib', -0.2),
    'papakha': wt('khabib', 'папаху'),
    'k29': wt('khabib', 'двадцать'),
    'auction': wt('khabib', 'аукциона'),
    'day': wt('khabib', 'сутки'),
    'conor': on('conor', -0.05),
    'accused': wt('conor', 'обвинил'),
    'durov': on('durov', -0.2),
    'release': wt('durov', 'выпускает'),
    'collect': wt('durov', 'собирает'),
    'pepe': on('pepe1', -0.1),
    'first': wt('pepe1', 'первый'),
    'price': wt('pepe1', 'сорок'),
    'evelone': on('evelone', -0.15),
    'e119': wt('evelone', 'сто'),
    'e40': wt('evelone', 'примерно'),
    'porsche': on('porsche', -0.15),
    'g18': wt('porsche', 'восемнадцать'),
    'car': wt('porsche', 'настоящий'),
    'outro': on('outro', -0.2),
    'o_snoop': wt('outro', 'снупа'),
    'o_khabib': wt('outro', 'хабиба'),
    'o_durov': wt('outro', 'дурова'),
    'o_write': wt('outro', 'пиши'),
    'end': DUR,
}
