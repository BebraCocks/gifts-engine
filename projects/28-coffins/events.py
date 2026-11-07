"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['p2']] + 0.25     # RubUp after gift 2 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_name': wt('hook', 'гроб'), 'h_then': wt('hook', 'пять'), 'h_q': wt('hook', 'сейчас'),
    'h_end': wt('hook', 'досмотрите'),
    'intro': on('intro', -0.2), 'i_a': wt('intro', 'подарки'), 'i_b': wt('intro', 'окупаются'),
    'p1': on('p1', -0.15), 'q1_name': wt('p1', 'кепка'), 'q1_then': wt('p1', 'тысяча'),
    'q1_now': wt('p1', 'сейчас'),
    'q1_pct': wt('p1', 'вот'),
    'p2': on('p2', -0.15), 'q2_name': wt('p2', 'снуп'), 'q2_then': wt('p2', 'двести'),
    'q2_now': wt('p2', 'сейчас'),
    'q2_pct': wt('p2', 'тоже'),
    'p3': on('p3', -0.15), 'q3_name': wt('p3', 'сваг'), 'q3_then': wt('p3', 'пятьсот'),
    'q3_now': wt('p3', 'сейчас'),
    'q3_pct': wt('p3', 'уже'),
    'p4': on('p4', -0.15), 'q4_name': wt('p4', 'папаха'), 'q4_then': wt('p4', 'десяти'),
    'q4_now': wt('p4', 'сейчас'),
    'coffin': on('p5', -0.15), 'q5_name': wt('p5', 'гроб'), 'q5_then': wt('p5', 'пять'),
    'q5_now': wt('p5', 'улучшений'),
    'q5_pct': wt('p5', 'продать'),
    'outro': on('outro', -0.2), 'o_a': wt('outro', 'какой'), 'o_b': wt('outro', 'окупился'),
    'o_write': wt('outro', 'пишите'),
    'end': DUR,
}
E['q4_pct'] = E['q4_now'] + 1.0
