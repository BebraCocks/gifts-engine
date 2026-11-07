"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['ring']] + 0.25     # RubUp after place 4 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_cat': wt('hook', 'кота'), 'h_ton': wt('hook', 'семь'), 'h_usd': wt('hook', 'тридцать'),
    'h_q': wt('hook', 'что'), 'h_qcat': wt('hook', 'котом'), 'h_end': wt('hook', 'ответ'),
    'intro': on('intro', -0.2), 'i_ton': wt('intro', 'тоны'), 'i_twice': wt('intro', 'дважды'),
    'ring': on('ring', -0.15), 'ri_name': wt('ring', 'кольцо'), 'ri_then': wt('ring', 'сорок'),
    'ri_now': wt('ring', 'сегодня'), 'ri_gift': wt('ring', 'стоит'),
    'rose': on('rose', -0.15), 'ro_name': wt('rose', 'роза'), 'ro_then': wt('rose', 'тридцать'),
    'ro_now': wt('rose', 'сейчас'), 'ro_gift': wt('rose', 'роза', 1),
    'potion': on('potion', -0.2), 'po_name': wt('potion', 'зелье'), 'po_then': wt('potion', 'тридцать'),
    'po_now': wt('potion', 'теперь'), 'po_gift': wt('potion', 'подорожало'),
    'cat': on('cat', -0.15), 'ca_name': wt('cat', 'кот'), 'ca_then': wt('cat', 'семь'),
    'ca_now': wt('cat', 'сегодня'), 'ca_gift': wt('cat', 'сам'),
    'outro': on('outro', -0.2), 'o_sell': wt('outro', 'продали'), 'o_hold': wt('outro', 'держали'),
    'o_write': wt('outro', 'пишите'),
    'end': DUR,
}
for p in ('ri', 'ro', 'po', 'ca'):                  # the loss stamp lands after today's value of the TON
    E[p + '_pct'] = E[p + '_now'] + 0.6
