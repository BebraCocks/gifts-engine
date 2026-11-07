"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['s4']] + 0.25     # RubUp after place 4 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_name': wt('hook', 'очки'), 'h_then': wt('hook', 'двести'), 'h_q': wt('hook', 'сейчас'),
    'h_end': wt('hook', 'ответ'),
    'intro': on('intro', -0.2), 'i_five': wt('intro', 'пять'), 'i_burn': wt('intro', 'подешевели'),
    's5': on('s5', -0.15), 'a5_name': wt('s5', 'лампа'), 'a5_then': wt('s5', 'пятьдесят'),
    'a5_now': wt('s5', 'стало'),
    's4': on('s4', -0.15), 'a4_name': wt('s4', 'могучая'), 'a4_then': wt('s4', 'двести'),
    'a4_now': wt('s4', 'теперь'),
    's3': on('s3', -0.15), 'a3_name': wt('s3', 'астральный'), 'a3_then': wt('s3', 'двести'),
    'a3_now': wt('s3', 'сейчас'),
    's2': on('s2', -0.15), 'a2_name': wt('s2', 'доска'), 'a2_then': wt('s2', 'двенадцать'),
    'a2_now': wt('s2', 'стало'),
    'a2_pct': wt('s2', 'минус'),
    's1': on('s1', -0.15), 'a1_name': wt('s1', 'очки'), 'a1_then': wt('s1', 'двести'),
    'a1_now': wt('s1', 'сейчас'),
    'a1_pct': wt('s1', 'минус'),
    'outro': on('outro', -0.2), 'o_which': wt('outro', 'продаёте'), 'o_burn': wt('outro', 'отскока'),
    'o_write': wt('outro', 'пишите'),
    'end': DUR,
}
# places without a spoken percentage show it shortly after the new price
E['a5_pct'] = E['a5_now'] + 1.0
E['a4_pct'] = E['a4_now'] + 1.0
E['a3_pct'] = E['a3_now'] + 1.0
