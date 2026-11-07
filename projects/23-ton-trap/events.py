"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['durov']] + 0.25     # RubUp after place 3 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_pepe': wt('hook', 'плюш'), 'h_228': wt('hook', 'двести'), 'h_ton': wt('hook', 'тонах'),
    'h_today': wt('hook', 'сегодня'), 'h_119': wt('hook', 'сто'),
    'intro': on('intro', -0.2), 'i_ton': wt('intro', 'тоны'), 'i_melt': wt('intro', 'растаяли'),
    'cat': on('cat', -0.15), 'ca_name': wt('cat', 'испуганный'), 'ca_ton': wt('cat', 'пятьсот'),
    'ca_then': wt('cat', 'девятьсот'), 'ca_now': wt('cat', 'сегодня'),
    'durov': on('durov', -0.15), 'du_name': wt('durov', 'дуров'), 'du_ton': wt('durov', 'семь'),
    'du_then': wt('durov', 'двенадцать'), 'du_now': wt('durov', 'сейчас'),
    'sept': on('sept', -0.2), 'se_name': wt('sept', 'сентябрь'), 'se_ton': wt('sept', 'пять'),
    'se_then': wt('sept', 'шестнадцать'), 'se_now': wt('sept', 'сейчас'),
    'record': on('record', -0.15), 're_name': wt('record', 'рекорд'), 're_ton': wt('record', 'сто'),
    're_then': wt('record', 'двести'), 're_now': wt('record', 'превратились'),
    'outro': on('outro', -0.2), 'o_hold': wt('outro', 'держите'), 'o_out': wt('outro', 'выводите'),
    'o_write': wt('outro', 'пишите'),
    'end': DUR,
}
for p in ('ca', 'du', 'se', 're'):                  # the loss stamp lands shortly after today's value
    E[p + '_pct'] = E[p + '_now'] + (0.55 if p == 'du' else 0.9)
