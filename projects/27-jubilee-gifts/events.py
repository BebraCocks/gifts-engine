"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['p2']] + 0.25     # RubUp after gift 2 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_name': wt('hook', 'очки'), 'h_then': wt('hook', 'тридцать'), 'h_q': wt('hook', 'сейчас'),
    'h_end': wt('hook', 'досмотрите'),
    'intro': on('intro', -0.2), 'i_a': wt('intro', 'юбилейные'), 'i_b': wt('intro', 'окупились'),
    'p1': on('p1', -0.15), 'q1_name': wt('p1', 'розовый'), 'q1_then': wt('p1', 'триста'),
    'q1_now': wt('p1', 'сейчас'),
    'q1_pct': wt('p1', 'окупился'),
    'p2': on('p2', -0.15), 'q2_name': wt('p2', 'собака'), 'q2_then': wt('p2', 'пять'),
    'q2_now': wt('p2', 'сейчас'),
    'q2_pct': wt('p2', 'восемь'),
    'p3': on('p3', -0.15), 'q3_name': wt('p3', 'доска'), 'q3_then': wt('p3', 'две'),
    'q3_now': wt('p3', 'сейчас'),
    'q3_pct': wt('p3', 'минус'),
    'p4': on('p4', -0.15), 'q4_name': wt('p4', 'очки'), 'q4_then': wt('p4', 'тридцать'),
    'q4_now': wt('p4', 'сейчас'),
    'q4_pct': wt('p4', 'минус'),
    'outro': on('outro', -0.2), 'o_a': wt('outro', 'окупаются'), 'o_b': wt('outro', 'прогорели'),
    'o_write': wt('outro', 'пишите'),
    'end': DUR,
}
