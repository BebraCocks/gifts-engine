"""Track grid and the source-time map of the screen recording (track time -> recording time).
Everything is measured on the author's files (2026-11-10): track input/aura_track.mp4, recording input/rubup_screen.mp4."""
DUR = 58.0667                      # = track length
BEAT = 0.5108                      # one beat; a bass hit every 2 beats
HIT = 2 * BEAT
DROP1, BREAK, DROP2 = 8.09, 37.5, 41.71
HITS = [DROP1 + k * HIT for k in range(40) if DROP1 + k * HIT < BREAK - 0.05] + \
       [DROP2 + k * HIT for k in range(40) if DROP2 + k * HIT < DUR]

# (track t0, track t1, src s0, src s1): linear inside, a cut between segments.
# Recording events (20 fps scan): case presses 13.10 / 36.00 / 46.95, popups 20.60 / 42.95 / 55.80;
# upgrade (cookie -> Spy Agaric 49.4 %) press 97.05, «Не повезло» 102.25;
# final (2 gifts -> Neko Helmet 19.9 %) press 146.55, «Улучшено» 151.70, popup ~152.4.
SEG = [
    (0.00, 3.20, 148.20, 151.35),     # hook: final spin, the result is never shown
    (3.20, 4.50, 151.35, 151.35),     # hook: frozen + hidden under blur
    (4.50, 8.09, 9.40, 13.10),        # intro: «Любой NFT», 5 005★
    (8.09, 10.13, 13.10, 20.60),      # case 1 spin (fast)
    (10.13, 12.18, 20.60, 22.65),     # popup: Ginger Cookie 915
    (12.18, 13.20, 35.25, 36.00),     # case page again
    (13.20, 15.24, 36.00, 42.95),     # case 2 spin
    (15.24, 19.33, 42.95, 46.95),     # popup: Snow Globe 780, back to the page
    (19.33, 21.37, 46.95, 55.80),     # case 3 spin
    (21.37, 24.43, 55.80, 58.55),     # popup: Eternal Candle 566
    (24.43, 29.54, 93.30, 97.05),     # upgrade page: cookie -> Spy Agaric 49.4 %
    (29.54, 33.62, 97.05, 102.25),    # upgrade spin
    (33.62, 37.50, 102.25, 102.90),   # «Не повезло»
    (37.50, 37.95, 141.00, 141.45),   # final page: 2 gifts -> Neko Helmet 19.9 %
    (37.95, 41.71, 146.55, 151.70),   # final spin (break)
    (41.71, 48.00, 151.70, 158.00),   # «Улучшено», popup
    (48.00, 58.07, 158.00, 159.90),   # popup holds
]


def src_at(t):
    t0, t1, s0, s1 = SEG[seg_index(t)]
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return s0 + (s1 - s0) * u


def seg_index(t):
    for k, (t0, t1, _, _) in enumerate(SEG):
        if t < t1:
            return k
    return len(SEG) - 1
