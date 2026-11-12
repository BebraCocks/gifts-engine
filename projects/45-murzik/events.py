"""Shared events for picture and sound (video time, s). Beat-locked times live in timeline; voice starts — script.VOICE_CUES.
Screen = the whole frame: recording crop x 0..720, y 230..1510, scale 1.5 -> 1080 x 1920. Points below are FRAME px."""
from timeline import (SCARE, TAP_TILE, PRESS, POP, CLOSE, TO_UP, TAP_WANT, TYPE, RESULTS, TAP_CAT, PRESS_UP, WIN,
                      JUMP, LAND, DUR)

CARD_W, CARD_H = 1080, 1920
TILE = (281, 518)            # «Тыква или лампа» in the case list
OPEN_BTN = (548, 1168)       # «Открыть за 2 399 ★»
POPUP_GIFT = (540, 1060)     # gift picture in «Ваш подарок»
WANT = (812, 1101)           # «Хочу получить» panel on the upgrade screen
SHEET_DY = 72                # the sheet sits 72 px lower without the keyboard
CAT_CARD = (870, 850 + SHEET_DY)   # Purrlion in the search results
UP_BTN = (800, 1741)         # «Улучшить» (right part: clear of the head)
WHEEL_C = (540, 562)         # upgrade wheel centre
WIN_GIFT = (540, 812)        # the cat picture in «Улучшено»
HOLD = (800, 1545)           # the two palms meet here; the cat sits on them
SHEET0 = TAP_WANT + 0.22     # the sheet is up: own composite (no keyboard, «Мурзик» typed)
WORD = 'Мурзик'
GIFT, MODEL = 'Scared Cat', 'Purrlion'                       # the upgrade target on the recording
PUMPKINS = [('Mad Pumpkin', 'Golden Boy'), ('Mad Pumpkin', 'Let It Snow'), ('Mad Pumpkin', 'Let It Snow')]
POP_END = [CLOSE[0], CLOSE[1], TO_UP]
RUN = SCARE + 0.22           # after the hop he bolts to the right

# Eye fire: (time, state)
EMO = [
    (0.00, 'love'), (SCARE, 'shock'), (4.10, 'cocky'), (PRESS[0], 'tense'), (POP[0] + 0.1, 'annoyed'),
    (PRESS[1], 'tense'), (POP[1] + 0.1, 'sad'), (PRESS[2], 'tense'), (POP[2] + 0.1, 'rage'),
    (16.50, 'cocky'), (RESULTS, 'joy'), (PRESS_UP, 'tense'), (WIN, 'joy'), (LAND + 0.25, 'love'),
]

# Head travels: (arrival time, x, y offset, scale mult). Smooth ease-in-out between keys.
W_KEYS = [
    (0.00, 330, 0, 0.86), (SCARE + 0.25, 330, 0, 0.86), (2.75, 430, -10, 0.88),     # leans after the cat
    (3.90, 430, -10, 0.88), (4.45, 540, 0, 0.88),
    (TO_UP - 0.1, 540, 0, 0.88), (17.30, 300, 20, 0.80),                           # steps aside: the «Улучшить» button stays visible
    (JUMP - 0.15, 300, 20, 0.80), (LAND - 0.05, 330, 0, 0.86), (40.0, 330, 0, 0.86),
]

# Screen zoom: (t0, t1, focus in frame px, zoom at t0 -> t1); out of a zoom = a snap on a cut / hit
ZOOMS = [
    (3.20, TAP_TILE, (281, 560), 1.04, 1.30),
    (TAP_TILE, PRESS[0] - 0.05, (540, 800), 1.08, 1.18),
    (POP[0], CLOSE[0], (540, 1040), 1.08, 1.15),
    (POP[1], CLOSE[1], (540, 1040), 1.08, 1.15),
    (POP[2], TO_UP, (540, 1040), 1.08, 1.18),
    (TO_UP, TAP_WANT - 0.05, (560, 700), 1.04, 1.12),
    (RESULTS, TAP_CAT, (700, 760), 1.06, 1.20),
    (TAP_CAT, PRESS_UP - 0.05, (540, 620), 1.08, 1.14),
    (PRESS_UP + 0.05, WIN - 0.07, (540, 600), 1.05, 1.36),
    (WIN, JUMP + 0.25, (540, 860), 1.10, 1.16),
]

AURA_TEXT = [(POP[0] + 0.25, 'НЕ МУРЗИК', (255, 70, 60), (540, 430)),
             (POP[1] + 0.25, 'ОПЯТЬ НЕ МУРЗИК', (255, 70, 60), (540, 430)),
             (POP[2] + 0.25, 'ГДЕ МУРЗИК?!', (255, 40, 30), (540, 430)),
             (WIN + 0.08, 'МУРЗИК!', (255, 210, 80), (600, 235))]
