"""Shared events for picture and sound (video time, s). Voice starts — script.VOICE_CUES."""
from timeline import DROP, RESUME

# Screen = the whole frame: recording crop x 0..720, y 230..1510, scale 1.5 -> 1080 x 1920.
CARD_S, CARD_Y0 = 1.5, 230
CARD_W, CARD_H = 1080, 1920


def card_xy(ox, oy):
    """Original recording pixel -> frame pixel."""
    return ox * CARD_S, (oy - CARD_Y0) * CARD_S


OPEN_BTN = card_xy(360, 1006)      # «Открыть за 100 ★»
AGAIN_BTN = card_xy(470, 1478)     # «Крутить ещё за 100 ★» (right part: clear of the white head)
POPUP_GIFT = card_xy(360, 885)     # gift picture in «Ваш подарок»
GIFT_BOX = {'rose': (175, 715, 550, 1095), 'diamond': (190, 760, 530, 1080)}   # orig px to erase once taken
ROSE_ID = '5168103777563050263'    # Telegram gift 🌹 (Lottie via gifts_api.original_file)
DIAMOND_ID = '5170521118301225164'  # Telegram gift 💎

# --- story beats
SWIPES = [(0.10, 0.35), (0.65, 0.90), (1.20, 1.45)]   # finger contact: the list moves with the finger, then glides
SCROLL_END = 2638.0                             # list offset (orig px) where it stops: the 50/50 shelf (static src 7.6–8.2)
GLIDE = 1.02                                    # inertia after each flick, s
PINK_IN = (4.00, 4.75)                          # pink slides in from the right
PRESS1 = 13.65                                  # «Открыть за 100»
POP1 = 15.20                                    # «Ваш подарок»: Роза
HALO = 0.33                                     # after the popup slides in, the gift pops out glowing
GRAB1 = 16.00                                   # the white hand closes on the rose
GIVE = 17.25                                    # the pink hand takes it
STARE = (17.45, 18.85)                          # she stares at it, puzzled
THROW1 = 19.08                                  # «Да пошёл ты!» — the rose is released
ROSE_HIT = 19.40                                # ... and hits the white head
PINK_OUT = (19.90, 20.60)                       # she leaves to the right
RAGE = 20.70                                    # «Ах ты мразь!»
PRESS2 = RESUME                                 # «Крутить ещё за 100» = the track comes back
POP2 = 24.20                                    # «Ваш подарок»: Алмаз
GRAB2 = 25.00
WINDUP = 27.95
THROW2 = 28.30                                  # a hard straight throw to the right; it hits her ~1,3 s later
HIT2 = DROP                                     # off-screen hit + «А-ай!» on the drop (29.60)
SHADES = DROP + 0.40                            # pixel shades drop onto the eyes (the dance)
EMO_P = [(0.00, 'p_pout'), (17.45, 'p_puzzled'), (18.85, 'p_angry')]   # her smaller eye fire

# Eye fire of the white head: (time, state)
EMO = [
    (0.00, 'calm'), (4.10, 'calm'), (9.60, 'cocky'), (PRESS1 + 0.05, 'tense'), (GRAB1, 'love'),
    (17.45, 'cocky'), (ROSE_HIT, 'annoyed'), (RAGE - 0.05, 'rage'), (PRESS2 + 0.1, 'angry'),
    (GRAB2, 'evil'), (HIT2, 'joy'),
]

# Head travels: (arrival time, x, y offset, scale mult). Smooth ease-in-out between keys.
W_KEYS = [
    (0.00, 540, 0, 1.0), (3.90, 540, 0, 1.0), (4.65, 300, 20, 0.80),
    (9.40, 300, 20, 0.80), (9.90, 270, 10, 0.82),
    (15.10, 270, 10, 0.82), (15.90, 300, 25, 0.80),
    (16.40, 300, 25, 0.80), (16.90, 360, 10, 0.80),             # leans towards her with the rose
    (17.40, 360, 10, 0.80), (17.90, 300, 20, 0.80),
    (ROSE_HIT, 300, 20, 0.80), (20.40, 330, 10, 0.86),
    (24.10, 330, 10, 0.86), (25.20, 330, 0, 0.88),
    (THROW2 - 0.15, 290, 10, 0.88), (THROW2 + 0.1, 400, -5, 0.90),   # the throw: body swings
    (DROP - 0.1, 430, -20, 0.90),                            # looks after it
    (DROP + 0.55, 540, -10, 1.05), (40.0, 540, -10, 1.05),
]
P_KEYS = [
    (0.00, 1500, 0, 1.0), (PINK_IN[0], 1500, 0, 1.0), (PINK_IN[1], 800, 0, 1.0),
    (16.80, 800, 0, 1.0), (17.30, 760, -10, 1.0), (17.70, 800, 0, 1.02),
    (PINK_OUT[0], 800, 0, 1.0), (PINK_OUT[1], 1560, 30, 1.0), (40.0, 1560, 30, 1.0),
]

# Screen zoom (focus in ORIGINAL recording px, zoom at t0 -> t1); out of a zoom = a snap on a cut/hit
ZOOMS = [
    (2.40, 6.70, (360, 900), 1.04, 1.10),            # 50/50 shelf
    (6.70, 9.55, (525, 1100), 1.30, 1.42),            # «…маленького цветочка» -> the «Роза или алмаз» tile
    (9.55, PRESS1 - 0.05, (380, 720), 1.10, 1.22),   # the case: title + reel
    (POP1, GRAB1 + 0.6, (360, 880), 1.10, 1.18),     # rose popup
    (17.45, 18.85, (360, 900), 1.05, 1.12),          # stare: slow push
    (POP2, WINDUP, (360, 880), 1.10, 1.20),          # diamond popup
    (THROW2 + 0.05, DROP, (700, 900), 1.03, 1.12),   # waiting for the hit: slow push to the right
]

AURA_TEXT = [(ROSE_HIT + 0.05, '−1000 AURA', (255, 70, 60), (330, 1080)),
             (HIT2 + 0.10, '+1000 AURA', (255, 210, 80), (540, 1120))]
