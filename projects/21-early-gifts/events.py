"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['watch_phone']] + 0.25     # RubUp after the first example (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_crumbs': wt('hook', 'сухариков'), 'h_gift': wt('hook', 'подарок'), 'h_phone': wt('hook', 'айфон'),
    'count': on('count', -0.2), 'c_how': wt('count', 'сколько'), 'c_early': wt('count', 'раньше'),
    'watch': on('watch', -0.15), 'w15': wt('watch', 'полтора'), 'w_crumbs': wt('watch', 'сухариков'),
    'wnow': on('watch_now', -0.15), 'w7k': wt('watch_now', 'семь'), 'w50': wt('watch_now', 'пятьдесят'),
    'wph': on('watch_phone', -0.15), 'w20': wt('watch_phone', 'двадцать'), 'w10': wt('watch_phone', 'десять'),
    'w_today': wt('watch_phone', 'сегодня'), 'w_phone': wt('watch_phone', 'айфон'),
    'cap': on('cap', -0.2), 'c15': wt('cap', 'пятнадцать'), 'c_pizza': wt('cap', 'пиццу'),
    'cph': on('cap_phone', -0.15), 'c2': wt('cap_phone', 'две'), 'c_caps': wt('cap_phone', 'кепки'),
    'c_phone': wt('cap_phone', 'айфон'),
    'pepe': on('pepe', -0.15), 'p30': wt('pepe', 'тридцать'), 'p_kino': wt('pepe', 'кино'),
    'pnow': on('pepe_now', -0.15), 'p649': wt('pepe_now', 'шестьсот'), 'p3': wt('pepe_now', 'три'),
    'outro': on('outro', -0.2), 'o_which': wt('outro', 'какой'), 'o_sorry': wt('outro', 'жалеете'),
    'end': DUR,
}
