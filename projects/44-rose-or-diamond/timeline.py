"""Video time (s) -> screen-recording time and the track layout. Measured on the author's files (2026-11-12):
recording input/rubup_screen.mp4 (58,5 s, 720x1600, VFR) and track input/track.m4a (30,8 s, ~96 BPM, beat 0,627 s,
drop at 10,04 s; chopped intro with stop gaps 0,35 / 1,78 / 2,89 / 4,30 / 5,41 / 6,54 s)."""
DUR = 33.05
BEAT = 0.627
TRACK_DROP = 10.04
# Music (author): plays under the intro, fades out before the drop, silence for the dialogue, comes back right after
# «Ах ты мразь!» and continues so that the drop lands on the diamond hit.
FADE0, FADE1 = 3.30, 4.30            # intro fade (video time = track time)
RESUME = 22.55                       # video time when the track continues ...
RESUME_SRC = 2.99                    # ... from this track time (just after the stop gap 2,89): the drop comes
                                     # 7 s later, so the diamond flies ~1,3 s (author 2026-11-12)
DROP = RESUME + (TRACK_DROP - RESUME_SRC)    # 29.60: diamond hits, «А-ай!», the dance starts

HITS = [k * BEAT * 2 for k in range(4)] + \
       [RESUME + (k * BEAT * 2 - (RESUME_SRC % (2 * BEAT))) for k in range(1, 5)] + \
       [DROP + k * BEAT for k in range(8)]
HITS = sorted(h for h in HITS if 0 <= h < DUR and not (FADE1 <= h < RESUME))

# (t0, t1, src s0, src s1): linear inside, a cut between segments.
# Recording: list scroll 0–18; 50/50 shelf 24.0–26.9; case «Роза или алмаз» 30.0–33.6, press 33.6;
# rose popup 39.95–44.2 (press «Крутить ещё» ~44.1); diamond popup from 52.75.
SEG = [
    (0.00, 2.40, 0.50, 8.00),        # flicking through the cases
    (2.40, 9.55, 24.30, 26.85),      # 50/50 shelf (slow), pink enters and complains
    (9.55, 13.65, 30.00, 33.60),     # case «Роза или алмаз», press
    (13.65, 14.60, 33.60, 37.60),    # spin 1 (fast)
    (14.60, 15.60, 37.60, 39.95),    # spin 1 slows down
    (15.60, 22.55, 39.95, 44.05),    # popup: Роза 40★
    (22.55, 23.55, 44.05, 50.20),    # «Крутить ещё», spin 2 (fast)
    (23.55, 24.55, 50.20, 52.75),    # spin 2 slows down
    (24.55, DUR, 52.75, 58.45),      # popup: Алмаз 160★
]


def seg_index(t):
    for k, (t0, t1, _, _) in enumerate(SEG):
        if t < t1:
            return k
    return len(SEG) - 1


def src_at(t):
    t0, t1, s0, s1 = SEG[seg_index(t)]
    u = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    return s0 + (s1 - s0) * u
