"""Shared content-time events (picture, SFX and music)."""
import json
from pathlib import Path
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, AD_HOLD
from words import wt
from script import ROUNDS, TON_RUB

AD_STOP = END[KEY['a3']] + AD_HOLD          # RubUp right after «Арбузный! Это почти четыре обычных.», no lead-in

# which side wins each round: 0 = gift (left), 1 = thing (right)
WIN = [0 if r[5] * TON_RUB > r[6] else 1 for r in ROUNDS]

E = {
    'hook_q': END[0] - 0.25,                 # end of the hook line — the title settles
    'comments': wt('outro', 'признавайся'),
    'which': wt('outro', 'на'),
    'end': DUR,
}
# The author's sound (sfx/fart-ripper.mp3) goes into the pause inserted in the hook take (select_takes.py, INSERT):
# «…что дороже?» — sound — «Спорим, на финале ошибёшься?». ≈ 2.4–3.0 s, the «~3rd second» the author asked for.
_ins = Path(__file__).resolve().parent / 'voice' / 'L01.insert.json'
E['fart'] = ON[0] + (json.loads(_ins.read_text())['at'] + 0.15 if _ins.exists() else 2.2)

