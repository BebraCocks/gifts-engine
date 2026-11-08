"""Shared content-time events (picture, SFX and music)."""
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, AD_HOLD
from words import wt

AD_STOP = END[KEY['a3']] + AD_HOLD          # RubUp right after the third answer; the teaser pill is on the freeze

E = {
    'hook_out': ON[KEY['rules']] - 0.1,          # hook text gives way to the rules
    'blue': wt('rules', 'синих'),               # rules: the blue row lights up
    'red': wt('rules', 'красных'),              # rules: the red row lights up
    'pick': wt('rules', 'выбери'),              # rules: «1 + 1» hint
    'more': wt('rules', 'дороже'),              # rules: 100 / 300 / 500 chips
    'sum': ON[KEY['sum']],
    'comments': wt('outro', 'пиши'),
    'end': DUR,
}
