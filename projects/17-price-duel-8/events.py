"""Shared content-time events (picture, SFX and music)."""
import json
from pathlib import Path
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, AD_HOLD
from words import wt
from script import ROUNDS, TON_RUB

AD_STOP = END[KEY['a3']] + AD_HOLD          # RubUp right after the third answer, no lead-in

# which side wins each round: 0 = gift (left), 1 = thing (right)
WIN = [0 if r[5] * TON_RUB > r[6] else 1 for r in ROUNDS]

E = {
    'hook_q': END[0] - 0.25,                 # end of the hook line — the title settles
    'comments': wt('outro', 'пиши'),
    'which': wt('outro', 'а'),
    'end': DUR,
}

