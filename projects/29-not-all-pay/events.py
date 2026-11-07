"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['tease']] + 0.2   # RubUp right after the teaser «не листай» (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_one': wt('hook', 'один'), 'h_x': wt('hook', 'восемьсот'), 'h_pepe': wt('hook', 'пепе'),
    'h_end': wt('hook', 'последним'),
    'intro': on('intro', -0.15), 'i_a': wt('intro', 'окупаются'), 'i_b': wt('intro', 'погнали'),
    'p1': on('p1', -0.15), 'q1_name': wt('p1', 'медальон-сердце'), 'q1_then': wt('p1', 'десять'),
    'q1_now': wt('p1', 'сейчас'), 'q1_thing': wt('p1', 'это'),
    'p2': on('p2', -0.15), 'q2_name': wt('p2', 'парные'), 'q2_then': wt('p2', 'пять'),
    'q2_now': wt('p2', 'сейчас'), 'q2_thing': wt('p2', 'хватит'),
    'tease': on('tease', -0.1), 'ts_x': wt('tease', 'двести'), 'ts_stop': wt('tease', 'листай'),
    'p3': on('p3', -0.15), 'q3_name': wt('p3', 'цилиндр'), 'q3_then': wt('p3', 'тысяча'),
    'q3_now': wt('p3', 'сейчас'), 'q3_thing': wt('p3', 'даже'),
    'p4': on('p4', -0.15), 'q4_name': wt('p4', 'плюшевый'), 'q4_then': wt('p4', 'две'),
    'q4_now': wt('p4', 'сейчас'), 'q4_thing': wt('p4', 'это'),
    'p5': on('p5', -0.15), 'q5_name': wt('p5', 'самый'), 'q5_then': wt('p5', 'двадцать'),
    'q5_now': wt('p5', 'сейчас'), 'q5_thing': wt('p5', 'это'),
    'total': on('total', -0.2), 't_sum': wt('total', 'восемнадцать'), 't_today': wt('total', 'сегодня'),
    't_car': wt('total', 'ладу'),
    'outro': on('outro', -0.2), 'o_a': wt('outro', 'какой'), 'o_b': wt('outro', 'купили'),
    'o_write': wt('outro', 'пишите'),
    'end': DUR,
}
for n in range(1, 6):                 # verdict stamp shortly after the «now» value lands
    E[f'q{n}_pct'] = E[f'q{n}_now'] + 0.75
