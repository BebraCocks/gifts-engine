"""Shared content-time events (picture, SFX and music)."""
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, AD_HOLD
from words import wt
from script import ROUNDS, TON_RUB

AD_STOP = END[KEY['a3']] + AD_HOLD          # RubUp right after «Кепка! Сорок одна тысяча.», no lead-in

# which side wins each round: 0 = gift (left), 1 = thing (right)
WIN = [0 if ton * TON_RUB > rub else 1 for (_, _, _, _, _, ton, rub) in ROUNDS]

E = {
    'hook_q': wt('hook', 'что'),             # «Что дороже?» — the title settles
    'comments': wt('outro', 'пиши'),
    'which': wt('outro', 'что'),
    'end': DUR,
}
