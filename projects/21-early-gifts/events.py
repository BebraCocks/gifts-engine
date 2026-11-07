"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['pepe834']] + 0.25        # RubUp after the three purchases (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'first': wt('hook', 'первый'),
    'crazy': wt('hook', 'безумная'),
    'link': on('link', -0.2), 'copy': wt('link', 'скопируй'), 'goal': wt('link', 'рекомендации'),
    'pepe1': on('pepe1', -0.15), 'gave': wt('pepe1', 'подарили'), 'price1': wt('pepe1', 'сорок'),
    'helmet': on('helmet', -0.15), 'h_buy': wt('helmet', 'купил'), 'h11': wt('helmet', 'одиннадцать'),
    'h10': wt('helmet', 'десять'),
    'p834': on('pepe834', -0.15), 'p_took': wt('pepe834', 'взял'), 'p_gift': wt('pepe834', 'подарил'),
    'brick': on('brick', -0.2), 'b7000': wt('brick', 'семь'), 'b_sold': wt('brick', 'раскупили'),
    'b34': wt('brick', 'тридцать'),
    'cap': on('cap', -0.15), 'c15': wt('cap', 'пятнадцать'), 'c_year': wt('cap', 'через'), 'c3000': wt('cap', 'три'),
    'quote': on('quote', -0.15), 'q2': wt('quote', 'пару'), 'q100': wt('quote', 'ста'),
    'total': on('total', -0.15), 't761': wt('total', 'семьсот'), 't35': wt('total', 'почти'),
    'outro': on('outro', -0.2), 'o_pepe': wt('outro', 'пепе'), 'o_helmet': wt('outro', 'шлем'),
    'o_cap': wt('outro', 'кепку'), 'o_write': wt('outro', 'пиши'),
    'end': DUR,
}
