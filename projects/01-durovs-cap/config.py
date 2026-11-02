"""Test clip: temporary dark style until the author sends references."""
STYLE_READY = False            # set True only after the author says «собирай»
BG_TOP = (14, 19, 32)
BG_BOTTOM = (24, 30, 48)
GIFT_NAME = "Durov's Cap"
# Random sample (seed 20261102) of the 55 models; rarity % from api.changes.tg, fetched 2026-11-02.
MODELS = [
    ('Jade', 2, (40, 190, 130)),
    ('Cartoon', 1.5, (60, 150, 230)),
    ('Chicago Bulls', 2, (230, 50, 70)),
]
WITHOUT_NARRATION = True
