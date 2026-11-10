"""Shared events for picture and sound (track time, s)."""
from timeline import DROP1, DROP2, BREAK

# Screen card: recording crop x 0..720, y 190..1440 (status bar and Telegram header removed), scale 1.05.
CARD_X, CARD_Y, CARD_S = 162, 40, 1.05
CARD_W, CARD_H = 756, 1313


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
    (10.20, 'annoyed'), (15.30, 'angry'), (21.40, 'rage'), (26.70, 'cocky'),
    (LOSE, 'rage'), (35.90, 'sad'), (BREAK, 'tense'), (DROP2, 'joy'),
]

# aura meme counters (modest: two moments)
AURA_TEXT = [(LOSE + 0.1, '−1000 AURA', (255, 70, 60)), (DROP2 + 0.15, '+1000 AURA', (255, 210, 80))]

# Screen zoom inside the card: (t0, t1, focus in ORIGINAL recording px, zoom at t0, zoom at t1); out of presses
ZOOMS = [
    (0.00, 4.50, (360, 560), 1.18, 1.32),            # hook: creeping into the (blurred) wheel
    (10.13, 12.18, (360, 1010), 1.30, 1.36),         # «Ваш подарок»: Ginger Cookie 915
    (15.24, 18.30, (360, 1010), 1.30, 1.36),         # Snow Globe 780
    (21.37, 24.43, (360, 1010), 1.32, 1.40),         # Eternal Candle 566
    (24.60, 29.25, (360, 640), 1.22, 1.30),          # upgrade 49,4 %
    (33.62, 37.45, (360, 560), 1.30, 1.42),          # «Не повезло»
    (38.10, 41.71, (360, 620), 1.12, 1.50),          # break: slow push into 19,9 %
    (41.71, 47.20, (360, 800), 1.20, 1.26),          # «Улучшено» 6 683
]

# Head moves with the story: (time, dx, dy, dscale)
HEAD_KEYS = [
    (0.00, 0, -30, 0.04), (3.10, 0, -70, 0.08), (3.30, 0, 0, 0.0), (4.50, 0, 0, 0.0),
    (7.70, 0, 0, 0.0), (8.30, 0, -55, 0.05), (10.00, 0, -55, 0.05), (10.40, -45, 10, 0.0), (12.90, -45, 10, 0.0),
    (13.40, 0, -55, 0.05), (15.10, 0, -55, 0.05), (15.50, 45, 15, 0.0), (19.00, 45, 15, 0.0),
    (19.50, 0, -60, 0.06), (21.25, 0, -60, 0.06), (21.55, 0, -25, 0.05), (24.30, 0, 0, 0.0),
    (26.90, 70, 10, -0.02), (29.10, 70, 10, -0.02), (29.70, 0, -60, 0.06), (33.50, 0, -75, 0.08),
    (33.75, 0, 45, -0.03), (35.70, 0, 45, -0.03), (36.40, -30, 95, -0.07), (37.50, -30, 95, -0.07),
    (37.90, 0, -20, 0.0), (41.60, 0, -120, 0.13), (41.80, 0, 0, 0.0), (58.10, 0, 0, 0.0),
]

# Case results are all «неокуп»: red minus next to the price (999 − 915 / 780 / 566)
LOSS_TAGS = [(10.25, '−84 ★'), (15.35, '−219 ★'), (21.45, '−433 ★')]
PRICE_XY = card_xy(545, 1214)
CONFETTI = 42.45                        # win: gold confetti from the top

# Summary «чек» (author 2026-11-10): the shown chain only — 3 cases × 999 = 2 997★ -> Neko Helmet 6 683★
SUMMARY_T0, SUMMARY_T1 = 47.00, 53.35
SUMMARY_ROWS = [47.83, 48.85, 49.87]    # bass hits: spent, received, profit
SUMMARY_STAMP = 50.90                   # «ОКУП ×2,23» stamp on a hit
SPENT, GOT = 2997, 6683
