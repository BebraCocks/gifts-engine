"""Shared content-time events (seconds) for picture and sound. Text-only clip: times are authored,
not derived from speech. Total = DUR + one RubUp break (~6.1 s) ≈ 58.5 s."""
DUR = 52.4

# Camera transits: (start, end). 0 = hook rush to hero 1; k = hero k -> hero k+1; last = pull-back.
HOOK_MOVE = (0.0, 5.2)
TRANSITS = [(12.6, 13.9), (20.8, 22.1), (29.5, 30.8), (38.4, 39.8)]
PULLBACK = (47.6, DUR)

AD_STOP = 29.45                       # after the teaser, before the turn to Count Dracula

HOOK_T = [(0.15, 4.75), (2.45, 4.75)]  # (in, out) of the two hook beats


def hero_times(k):
    """Text and stamp schedule of hero k (0..4)."""
    arrive = HOOK_MOVE[1] if k == 0 else TRANSITS[k - 1][1]
    leave = TRANSITS[k][0] if k < len(TRANSITS) else PULLBACK[0]
    title = arrive - 0.45
    d = dict(arrive=arrive, leave=leave, title=title, f1=title + 0.5, f2=title + 2.9,
             stamp=title + 5.2, out=leave - 0.1)
    if k == 2:                                   # Nosferatu: earlier stamp, then the teaser before RubUp
        d.update(stamp=title + 4.7, out=27.9)
    if k == 0:
        d.update(title=4.6, f1=5.2, f2=7.7, stamp=10.0)
    return d


HEROES_T = [hero_times(k) for k in range(5)]
TEASER_T = (28.0, 29.95)                 # stays on screen through the ad pause, leaves on the turn
FINAL_T = dict(line1=47.9, grid=48.3, line2=49.5, cta=50.4, fade=52.1)
LIGHT_ON = [h['arrive'] - 0.35 for h in HEROES_T]       # picture lamp of each hero clicks on
