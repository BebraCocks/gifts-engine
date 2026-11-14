"""Shared content-time events (picture, SFX, music) — one source of truth for render.py and audio.py.

Author's notes 2026-11-13 (v3):
- ONE trick per round, alternating: R1 the NFT, R2 the thing, R3 the NFT, R4 the thing, R5 the NFT;
- every spin is a real tumble in the picture plane (no flat «2D flip» squash);
- the loser's defeat is physical: blown away (head turned to it), crushed in the fist (fist shakes, opens, palm tilts,
  crumbs fall), pulled into the ring's black hole, lenses crack and fall, chainsaw glitches into a cube;
- palms close into fists realistically (6-frame strip) after every round and open for the next pair."""
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, AD_HOLD, CLOSE
from script import ROUNDS, TON_RUB, TIMER

AD_STOP = END[KEY['a3']] + AD_HOLD          # RubUp right after the third answer (middle of the video)
WIN = [0 if r[2] * TON_RUB > r[5] else 1 for r in ROUNDS]     # 0 = gift (left, blue), 1 = thing (right, red)
assert WIN == [0, 1, 0, 1, 0], WIN

TRICK_SIDE = [0, 1, 0, 1, 0]
TRICK = [(t0 + 1.0, t0 + 4.35) for t0 in TIMER0]          # one trick window per round, after Morpheus' short line
TRICK_KIND = ['ring_toss', 'drill_toss_burst', 'black_hole_levitate', 'telescope_star', 'cap_toss_balance']
DEFEAT = ['blow_away', 'crush', 'black_hole', 'lens_crack', 'glitch_cube']

LOSE_T = [rv + (0.10 if r == 0 else 0.5) for r, rv in enumerate(REVEAL)]   # R1: the blow comes before the answer line
# R2 crush: watch into the palm → fist closes → shakes → opens → palm tilts → crumbs fall → palm level again
CRUSH = dict(close=(0.0, 0.26), shake=(0.26, 0.70), turn=(0.70, 1.00), open=(1.00, 1.30), drop=(1.10, 2.10))
# v6 (author): after the crush the fist turns over (back of the hand up) and opens palm-down — the dust pours out by itself
WIN_GONE = [END[3 + 3 * r] - 0.40 for r in range(5)]    # the winner dissolves into code under the answer's last word
FISTS = [END[3 + 3 * r] - 0.02 for r in range(5)]       # empty palms close into fists (strip, 0.28 s)
OPEN_DUR = 0.26                                          # fist → open palm at ROUND_IN

HOOK_OPEN = 1.32          # hook: fists open and the reels start (random NFTs / things flash in the hands)


def _reel_times():
    """Reel switches: fast at first, slowing like a slot machine; the last one lands on round 1's pair."""
    end = ROUND_IN[0] - 0.30
    ts, d, t = [], 0.40, end
    while t > HOOK_OPEN + 0.08:
        ts.append(t)
        t -= d
        d = max(0.065, d / 1.22)
    return sorted(ts)


REEL_T = _reel_times()
REEL_LAND = REEL_T[-1]

# background interference + an easter-egg phrase decoding out of the rain (author 2026-11-14), away from key moments
EGGS = [(TIMER0[0] + 2.6, 'ПРОСНИСЬ,|НЕО', 1), (ROUND_IN[1] + 0.9, 'ТУК-ТУК,|НЕО', 0), (TIMER0[2] + 2.8, 'ЛОЖКИ|НЕТ', 1),
        (TIMER0[3] + 1.4, 'СЛЕДУЙ ЗА|КРОЛИКОМ', 0), (ROUND_IN[4] + 0.6, 'ЭТО|ДЕЖАВЮ', 1), (OUTRO + 1.6, 'ТЕЛЕГА|ЗНАЕТ', 0)]
EGG_HOLD = 1.9

E = {
    'formed': 1.28,                # Morpheus assembled from code (intro)
    'outro': OUTRO,
    'dissolve': DUR - 1.15,        # Morpheus drains into code under the last words
    'end': DUR,
}
