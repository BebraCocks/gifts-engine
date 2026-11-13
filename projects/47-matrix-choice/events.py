"""Shared content-time events (picture, SFX, music). One source of truth for both render.py and audio.py.

Per round r (STORYBOARD.md §3, author 2026-11-13): tricks one after another during the 5 s timer — first the NFT, then
the thing, once each; on the reveal the loser plays its defeat, the winner dissolves into green code; the empty palms
close into fists and open for the next pair."""
from timeline import DUR, ON, END, KEY, ROUND_IN, TIMER0, REVEAL, OUTRO, AD_HOLD, CLOSE
from script import ROUNDS, TON_RUB, TIMER

AD_STOP = END[KEY['a3']] + AD_HOLD          # RubUp right after the third answer (middle of the video)
WIN = [0 if r[2] * TON_RUB > r[5] else 1 for r in ROUNDS]     # 0 = gift (left, blue), 1 = thing (right, red)
assert WIN == [0, 1, 0, 1, 0], WIN

# trick windows inside the timer: (start, end) for the NFT, then for the thing (sequential, no overlap)
TRICK_NFT = [(t0 + 0.55, t0 + 2.05) for t0 in TIMER0]
TRICK_THING = [(t0 + 2.25, t0 + 4.15) for t0 in TIMER0]

# what each trick / defeat is (render.py and audio.py both read this)
NFT_TRICK = ['ring_flip', 'watch_pendulum', 'ring_spin', 'glasses_glint', 'cap_spin']
THING_TRICK = ['knight_hop', 'drill_toss_burst', 'cactus_bloom', 'telescope_extend', 'chainsaw_pull']
DEFEAT = ['blow_away', 'crush', 'black_hole', 'lens_crack', 'glitch_cube']   # the loser of round r

LOSE_T = [rv + 0.55 for rv in REVEAL]       # the loser's defeat starts after the prices are up
WIN_GONE = [END[3 + 3 * r] - 0.40 for r in range(5)]   # the winner dissolves into code under the answer's last word
FISTS = [END[3 + 3 * r] - 0.02 for r in range(5)]      # palms empty → fists, then the next round opens them (CLOSE)

E = {
    'formed': 1.95,                # Morpheus assembled from code (intro)
    'outro': OUTRO,
    'dissolve': DUR - 1.35,        # Morpheus dissolves into code under the last words
    'end': DUR,
}
