"""Shared events for picture and sound (track time, s)."""
from timeline import DROP1, DROP2, BREAK

# Screen = the whole frame (author 2026-11-10: never shrink it): recording crop x 0..720, y 190..1470
# (status bar and Telegram header removed), scale 1.5 -> 1080 x 1920.
CARD_X, CARD_Y, CARD_S = 0, 0, 1.5
CARD_W, CARD_H = 1080, 1920


def card_xy(ox, oy):
    """Original recording pixel -> frame pixel."""
    return CARD_X + ox * CARD_S, CARD_Y + (oy - 190) * CARD_S


OPEN_BTN = card_xy(360, 1005)      # «Открыть за 999»
UP_BTN = card_xy(360, 1380)        # «Улучшить»
POPUP_GIFT = card_xy(360, 940)     # gift picture in «Ваш подарок»
WIN_GIFT = card_xy(360, 770)       # gift picture in «Улучшено»

# Hand presses: (time of the touch, target)
PRESSES = [(DROP1, OPEN_BTN), (13.20, OPEN_BTN), (19.33, OPEN_BTN), (29.54, UP_BTN), (37.95, UP_BTN)]

# Gift pops out of the popup: (time, gift, model, from xy, hold s)
POPS = [
    (10.13, 'Ginger Cookie', 'Brand New', POPUP_GIFT, 1.75),
    (15.24, 'Snow Globe', 'Choco Waffle', POPUP_GIFT, 1.75),
    (21.37, 'Eternal Candle', 'Candyman', POPUP_GIFT, 2.4),
    (42.41, 'Neko Helmet', 'Glitch', WIN_GIFT, 3.71),          # the win flies out with a glow, back in on the hit 46.82
]

CTA = 53.60                            # «Первым ста в комментах — по мишке!»
BEAR_ID = '5170233102089322756'        # the plain 15 ⭐ bear (Telegram gift id; Lottie via gifts_api.original_file)
# bear throws on bass hits: (time, hand, [(vx, vy, size, spin), ...])
THROWS = [
    (53.97, 'R', [(-420, -2150, 280, -2.2), (60, -2350, 250, 1.6)]),
    (54.99, 'L', [(430, -2100, 290, 2.4), (-40, -2300, 250, -1.4)]),
    (56.01, 'R', [(-650, -1950, 270, -2.8), (-180, -2450, 240, 2.0)]),
    (57.04, 'L', [(640, -1950, 280, 2.6), (190, -2400, 245, -1.8)]),
]
LOSE = 33.62                       # «Не повезло»
HOOK_HIDE = 3.20                   # hook: «ДА!», the result is hidden
HOOK_END = 4.50

# Eye fire: (time, state); states blend over ~0.3 s
EMO = [
    (0.00, 'tense'), (HOOK_HIDE, 'joy'), (HOOK_END, 'calm'),
    (10.20, 'annoyed'), (15.30, 'sad'), (21.40, 'rage'), (26.70, 'cocky'),      # 15.30 «опять неокуп»: расстроился
    (LOSE, 'rage'), (35.20, 'sad'), (BREAK, 'tense'), (DROP2, 'joy'),               # after the loss: расстроился
]

# aura meme counters (modest: two moments)
AURA_TEXT = [(LOSE + 0.1, '−1000 AURA', (255, 70, 60)), (DROP2 + 0.15, '+1000 AURA', (255, 210, 80))]

# Screen zoom inside the card: (t0, t1, focus in ORIGINAL recording px, zoom at t0, zoom at t1); out of presses
ZOOMS = [
    (0.00, 4.50, (360, 560), 1.12, 1.24),            # hook: creeping into the (blurred) wheel; cut at 4.50
    (10.13, 12.18, (360, 1214), 1.16, 1.22),         # «Ваш подарок»: Ginger Cookie; cut at 12.18
    (15.24, 18.30, (360, 1214), 1.16, 1.22),         # Snow Globe; snaps back on the hit 18.30
    (21.37, 24.43, (360, 1214), 1.18, 1.26),         # Eternal Candle; cut at 24.43
    (24.43, 28.52, (360, 640), 1.14, 1.22),          # upgrade 49,4 %; snaps back on the hit 28.52
    (33.62, 37.50, (360, 560), 1.20, 1.32),          # «Не повезло»; cut at 37.50
    (38.10, 41.71, (360, 620), 1.06, 1.38),          # break: slow push into 19,9 %; cut at the drop
    (41.71, 46.82, (360, 800), 1.10, 1.16),          # «Улучшено»; snaps back on the hit 46.82
]

# Head travels with the story (author: smooth, harmonious): (arrival time, x, y offset, scale mult).
# Between keys it glides with ease-in-out; it steps aside so prices / buttons / «Не повезло» stay visible.
HEAD_KEYS = [
    (0.00, 540, -10, 1.02), (3.00, 540, -60, 1.08), (4.50, 540, 0, 1.0),
    (9.20, 540, 0, 1.0), (10.40, 170, 60, 0.84),            # popup 1: glides left, the price is free
    (12.18, 170, 60, 0.84), (13.10, 540, 0, 1.0),           # back to the centre for the next press
    (14.20, 540, 0, 1.0), (15.40, 910, 60, 0.84),           # popup 2: glides right
    (18.30, 910, 60, 0.84), (19.25, 540, 0, 1.0),
    (20.30, 540, 0, 1.0), (21.50, 170, 60, 0.86),           # popup 3 (rage): left
    (24.40, 170, 60, 0.86), (25.60, 225, 35, 0.90),         # upgrade page: stays left, the button is free
    (33.60, 225, 35, 0.90), (34.80, 540, 60, 0.96),         # loss: slumps to the centre
    (35.80, 540, 70, 0.94), (37.20, 265, 90, 0.90),         # sad, drifts aside before the last press
    (38.20, 265, 90, 0.90), (41.55, 540, -80, 1.10),        # break: creeps up to the wheel
    (41.80, 540, 0, 1.0), (58.10, 540, 0, 1.0),
]

# Case results are all «неокуп» (author: no exact numbers, plain words): 915 / 780 / 566 of 999
LOSS_TAGS = [(10.25, 'ПОЧТИ ОКУП', card_xy(430, 1290)), (15.35, 'НЕОКУП', card_xy(290, 1290)),
             (21.45, 'МИНУС ПОЛКЕЙСА', card_xy(440, 1290))]   # between the price and the buttons, away from the head
CONFETTI = 42.45                        # win: gold confetti from the top

# Summary «чек» (author 2026-11-10): the shown chain only — 3 cases × 999 = 2 997★ -> Neko Helmet 6 683★
SUMMARY_T0, SUMMARY_T1 = 47.00, 53.35
SUMMARY_ROWS = [47.83, 48.85, 49.87]    # bass hits: spent, received, profit
SUMMARY_STAMP = 50.90                   # «ОКУП ×2,23» stamp on a hit
SPENT, GOT = 3000, 6700                 # rounded on purpose: «≈», «окуп ×2»
