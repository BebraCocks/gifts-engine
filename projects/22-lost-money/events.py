"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['locket']] + 0.25     # RubUp after place 4 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_cap': wt('hook', 'кепку'), 'h_3k': wt('hook', 'три'), 'h_today': wt('hook', 'сегодня'),
    'h_watch': wt('hook', 'досмотрите'), 'h_wow': wt('hook', 'удивитесь'),
    'intro': on('intro', -0.2), 'i_five': wt('intro', 'пять'), 'i_burn': wt('intro', 'погорели'),
    'pepe': on('pepe', -0.15), 'pe_name': wt('pepe', 'плюш'), 'pe_then': wt('pepe', 'шестнадцать'),
    'pe_now': wt('pepe', 'стало'), 'pe_pct': wt('pepe', 'минус'),
    'locket': on('locket', -0.15), 'lo_name': wt('locket', 'сердце-медальон'), 'lo_then': wt('locket', 'четыре'),
    'lo_now': wt('locket', 'стало'),
    'peach': on('peach', -0.2), 'pc_name': wt('peach', 'драгоценный'), 'pc_then': wt('peach', 'тысяча'),
    'pc_now': wt('peach', 'теперь'), 'pc_pct': wt('peach', 'минус'),
    'papakha': on('papakha', -0.15), 'pa_name': wt('papakha', 'папаха'), 'pa_then': wt('papakha', 'сто'),
    'pa_now': wt('papakha', 'сегодня'),
    'cap': on('cap', -0.15), 'cp_name': wt('cap', 'кепка'), 'cp_then': wt('cap', 'две'), 'cp_now': wt('cap', 'пятьсот'),
    'cp_pct': wt('cap', 'минус'),
    'outro': on('outro', -0.2), 'o_which': wt('outro', 'каком'), 'o_burn': wt('outro', 'погорели'),
    'o_write': wt('outro', 'пишите'), 'o_minus': wt('outro', 'минус'),
    'end': DUR,
}
# places without a spoken percentage show it shortly after the new price
E['lo_pct'] = E['lo_now'] + 1.0
E['pa_pct'] = E['pa_now'] + 1.0
