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
CRUSH = dict(close=(0.0, 0.26), shake=(0.26, 0.72), open=(0.72, 0.98), tilt=(0.98, 1.22), drop=(1.05, 1.75),
             level=(1.45, 1.70))
WIN_GONE = [END[3 + 3 * r] - 0.40 for r in range(5)]    # the winner dissolves into code under the answer's last word
FISTS = [END[3 + 3 * r] - 0.02 for r in range(5)]       # empty palms close into fists (strip, 0.28 s)
OPEN_DUR = 0.26                                          # fist → open palm at ROUND_IN

E = {
    'formed': 1.95,                # Morpheus assembled from code (intro)
    'outro': OUTRO,
    'dissolve': DUR - 1.15,        # Morpheus drains into code under the last words
    'end': DUR,
}
