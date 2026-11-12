"""Video time (s) -> screen-recording time, and the beat grid. Measured on the author's files (2026-11-12):
track input/track.m4a (29,57 s, ~113,6 BPM: beat 0,528 s, first beat 0,27 s; kick on even beats, snare on odd)
and recording input/rubup_screen.mp4 («rubup 3», 64,7 s, 720x1600). The whole track plays once, every action sits on a beat.
Recording: list 0–1,3 · case «Тыква или лампа» from 4,3 · spins 7,6–12,9 / 16,9–22,2 / 26,1–31,4 · popups 13,7 / 23,0 / 32,2 ·
upgrade screen (3 gifts) 40,8–41,5 · sheet «Хочу получить» 41,5–41,7 (models load 42,1) · search results 47,2 · upgrade with the cat 51,1 ·
press 53,5 · wheel 53,8–58,6 · «Улучшено» 58,6+. Loads, typing with the keyboard and jerks are cut."""
DUR = 29.5
BEAT = 0.528
BEAT0 = 0.27


def B(n):
    return round(BEAT0 + BEAT * n, 3)


SCARE = B(3)        # 1.854  the cat is startled
TAP_TILE = B(8)     # 4.494  tap the «Тыква или лампа» tile -> the case
PRESS = [B(11), B(17), B(23)]     # 6.078 9.246 12.414  «Открыть за 2 399»
POP = [B(14), B(20), B(26)]       # 7.662 10.830 13.998 «Ваш подарок»
CLOSE = [9.02, 12.20]             # popup 1 / 2 slides away
TO_UP = B(31)       # 16.638 cut to the upgrades
TAP_WANT = B(35)    # 18.750 «Хочу получить» -> the sheet
TYPE = [round(B(36) + k * BEAT / 2, 3) for k in range(6)]   # М-у-р-з-и-к on eighth notes
RESULTS = B(39)     # 20.862 search results: the cats
TAP_CAT = B(41)     # 21.918 tap Purrlion -> the upgrade screen with him
PRESS_UP = B(43)    # 22.974 «Улучшить»
WIN = B(47)         # 25.086 «Улучшено»
JUMP = B(48)        # 25.614 the cat jumps out of the window ...
LAND = B(49)        # 26.142 ... onto the palms

HITS = [B(n) for n in range(0, 56) if B(n) < DUR - 0.6]

# (t0, t1, src s0, src s1): linear inside, a cut between segments.
SEG = [
    (0.00, TAP_TILE, 0.50, 0.50),                 # case list (still)
    (TAP_TILE, PRESS[0], 5.70, 7.28),             # the case
    (PRESS[0], 7.50, 7.32, 13.00),                # spin 1 (x4)
    (7.50, 7.70, 13.68, 13.92),                   # popup slides in
    (7.70, CLOSE[0], 13.92, 15.50),               # Mad Pumpkin · Golden Boy
    (CLOSE[0], 9.15, 15.55, 15.75),               # popup away
    (9.15, PRESS[1], 16.30, 16.60),
    (PRESS[1], 10.67, 16.65, 22.30),              # spin 2
    (10.67, 10.87, 22.98, 23.25),
    (10.87, CLOSE[1], 23.25, 24.85),              # Mad Pumpkin · Let It Snow
    (CLOSE[1], 12.33, 24.88, 25.05),
    (12.33, PRESS[2], 25.50, 25.80),
    (PRESS[2], 13.84, 25.85, 31.50),              # spin 3
    (13.84, 14.04, 32.15, 32.42),
    (14.04, TO_UP, 32.42, 33.95),                 # Let It Snow again
    (TO_UP, TAP_WANT, 41.05, 41.45),              # upgrades: his 3 gifts are in
    (TAP_WANT, TAP_WANT + 0.22, 41.50, 41.72),    # the sheet slides up (then render.sheet_image)
    (TAP_WANT + 0.22, TAP_CAT, 42.90, 42.90),
    (TAP_CAT, PRESS_UP, 52.40, 53.45),            # upgrade screen with the cat, 20,4 %
    (PRESS_UP, 25.02, 53.55, 58.60),              # the wheel (x2,4)
    (25.02, 25.32, 58.60, 59.35),                 # «Улучшено» pops
    (25.32, DUR, 59.35, 64.50),
]
SPINS = [(PRESS[0], 7.50), (PRESS[1], 10.67), (PRESS[2], 13.84)]     # case reels (motion blur, ticks)
WHEEL = (PRESS_UP, 25.02)


def seg_index(t):
    for k, (t0, t1, _, _) in enumerate(SEG):
        if t < t1:
            return k
    return len(SEG) - 1


def src_at(t):
    t0, t1, s0, s1 = SEG[seg_index(t)]
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return s0 + (s1 - s0) * u


def src_speed(t):
    t0, t1, s0, s1 = SEG[seg_index(t)]
    return (s1 - s0) / (t1 - t0)
