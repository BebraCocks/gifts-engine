"""Shared content-time events (picture and sound). Word anchors come from words.py (voice envelope, no ASR)."""
from timeline import DUR, ON, END, KEY
from words import wt

AD_STOP = END[KEY['cigar']] + 0.25     # RubUp after gift 2 (≈ middle of the content)


def on(key, d=0.0):
    return ON[KEY[key]] + d


E = {
    'h_mln': wt('hook', 'миллион'), 'h_half': wt('hook', 'полчаса'), 'h_year': wt('hook', 'прошло'),
    'h_minus': wt('hook', 'минусе'),
    'intro': on('intro', -0.2), 'i_five': wt('intro', 'пять'), 'i_shop': wt('intro', 'магазине'), 'i_now': wt('intro', 'сейчас'),
    'snoop': on('snoop', -0.15), 'sn_name': wt('snoop', 'снуп'), 'sn_then': wt('snoop', 'двести'),
    'sn_now': wt('snoop', 'сейчас'), 'sn_pct': wt('snoop', 'два'),
    'cigar': on('cigar', -0.15), 'ci_name': wt('cigar', 'сигара'), 'ci_then': wt('cigar', 'пятнадцать'),
    'ci_now': wt('cigar', 'сейчас'), 'ci_pct': wt('cigar', 'тоже'),
    'westside': on('westside', -0.2), 'we_name': wt('westside', 'знак'), 'we_then': wt('westside', 'сто'),
    'we_now': wt('westside', 'сейчас'), 'we_pct': wt('westside', 'почти'),
    'lowrider': on('lowrider', -0.15), 'lo_name': wt('lowrider', 'лоурайдер'), 'lo_then': wt('lowrider', 'семьдесят'),
    'lo_now': wt('lowrider', 'семьдесят', 1), 'lo_pct': wt('lowrider', 'год'),
    'swag': on('swag', -0.15), 'sw_name': wt('swag', 'сваг'), 'sw_then': wt('swag', 'семь'),
    'sw_now': wt('swag', 'сейчас'), 'sw_pct': wt('swag', 'минус'),
    'outro': on('outro', -0.2), 'o_took': wt('outro', 'брали'), 'o_write': wt('outro', 'пишите'),
    'o_plus': wt('outro', 'плюсе'), 'o_minus': wt('outro', 'минусе'),
    'end': DUR,
}
