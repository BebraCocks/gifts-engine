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
    (42.41, 'Neko Helmet', 'Glitch', WIN_GIFT, 99.0),          # the win: hero until HELMET_FLY, then onto the head
]

HELMET_FLY, HELMET_ON = 51.20, 51.93   # «…Шлем мой!»: the helmet flies from the popup onto the head (on a bass hit)
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
