"""Shared content-time events (picture, SFX and music)."""
from timeline import DUR, ON, END, KEY, SIGN_IN, FORECAST, OUTRO, AD_STOP
from words import wt

E = {
    'twelve': wt('hook', 'двенадцать'),       # the wheel of 12 mugs lights up
    'four': wt('hook2', 'четыре'),            # 4 chosen mugs glow, the rest dim
    'find': wt('hook2', 'найди'),
    'comments': wt('outro', 'пиши'),
    'end': DUR,
}
