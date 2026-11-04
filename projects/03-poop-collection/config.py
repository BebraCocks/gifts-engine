"""03-poop-collection: «Музей кал-лекции» — own visual concept (STORYBOARD.md, section 2)."""
STYLE_READY = False            # set True only after the author says «собирай»
WITHOUT_NARRATION = False      # Fish Audio takes voice/L01..L09.wav (take02, speed 1.1)
VOICE_GAIN = 0.85

PAPER = (246, 242, 232)        # toilet-paper white
GOLD = (226, 178, 72)
BROWN = (150, 86, 40)
TEAL = (60, 150, 138)
ALERT = (214, 64, 52)

DATA_DATE = '04.11.2026'
DATA_SOURCE = 'api.changes.tg'

# model=None -> the original (non-upgraded) gift. Rarity from api.changes.tg, fetched 2026-11-04.
# Backdrop colours are Telegram backdrops picked for composition, not a specific owned gift.
HEROES = [
    dict(gift='Happy Brownie', model=None, swap='Kinky Stinky', title='Happy Brownie', rarity='50 моделей',
         wall='L', z=-48.0, backdrop=('#d19a3a', '#7d3600'), stamp='ОФИЦИАЛЬНО', stamp_rgb=ALERT),
    dict(gift='Money Pot', model='Skibidi Toilet', title='Skibidi Toilet', rarity='Money Pot · 0,1%',
         wall='R', z=-58.0, backdrop=('#5db1cb', '#025074'), stamp='МЕМ', stamp_rgb=ALERT),
    dict(gift='Ice Cream', model='Poopsicle', title='Poopsicle', rarity='Ice Cream · 0,2%',
         wall='L', z=-68.0, backdrop=('#e28ab6', '#8e054e'), stamp='НЕ ЛИЗАТЬ', stamp_rgb=ALERT),
    dict(gift='Tama Gadget', model='Poo Byte', title='Poo Byte', rarity='Tama Gadget · 0,3%',
         wall='R', z=-78.0, backdrop=('#95b457', '#046b06'), stamp='УБЕРИ!', stamp_rgb=ALERT),
    dict(gift='Happy Brownie', model='Gold Nugget', title='Gold Nugget', rarity='Happy Brownie · 0,5%',
         wall='E', z=-92.0, backdrop=('#ccab41', '#5d3b00'), stamp='ЗОЛОТО', stamp_rgb=GOLD),
]
# Hook corridor: other Happy Brownie models (all 50 are poop-shaped).
CORRIDOR = ['Golgothan', 'Holy Shit', 'Poocano', 'Unicorn', 'Alien', 'Cat Scat', 'Snowman']
# «50 моделей» fan around the first portrait
FAN = ['Kawaii', 'Raphael', 'Homer', 'Mud King', 'Poopy Dragon', 'Octopoo', 'Hot Shit', 'Sponge Boi']
SIDE_POOPSICLE = ('Pet Snake', 'Poopsicle', '1,5%')
PATTERNS = ['Toilet', 'Toilet Paper']    # symbols: 48 + 48 gifts, 72 distinct of 124 (fetched 2026-11-04)
