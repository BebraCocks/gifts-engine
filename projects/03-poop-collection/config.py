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

# Rarity from api.changes.tg, fetched 2026-11-04. Backdrop colours are Telegram backdrops picked for
# composition (not a specific owned gift); 'stars' = a night sky with the Milky Way (drawn in render.py).
HEROES = [
    dict(gift='Happy Brownie', model='Dung Beetle', title='Dung Beetle', rarity='Happy Brownie · 1,5%',
         wall='L', z=-48.0, backdrop='stars', stamp='ПО ЗВЁЗДАМ', stamp_rgb=GOLD),
    dict(gift='Happy Brownie', model='Shitty Coffee', title='Shitty Coffee', rarity='Happy Brownie · 2,5%',
         wall='R', z=-58.0, backdrop=('#b1907e', '#4a3226'), stamp='$1300 / КГ', stamp_rgb=ALERT),
    dict(gift='Money Pot', model='Skibidi Toilet', title='Skibidi Toilet', rarity='Money Pot · 0,1%',
         wall='L', z=-68.0, backdrop=('#5db1cb', '#025074'), stamp='0,1%', stamp_rgb=ALERT),
    dict(gift='Happy Brownie', model='Modern Art', title='Modern Art', rarity='Happy Brownie · 0,2%',
         wall='R', z=-78.0, backdrop=('#e9e7e2', '#88847e'), stamp='$6,2 МЛН', stamp_rgb=ALERT),
    dict(gift='Happy Brownie', model='Art Supplies', title='Art Supplies', rarity='Happy Brownie · 2%',
         wall='E', z=-92.0, backdrop=('#ccab41', '#5d3b00'), stamp='€275 000', stamp_rgb=ALERT),
]
# Hook corridor: other Happy Brownie models (all 50 are poop-shaped).
CORRIDOR = ['Golgothan', 'Holy Shit', 'Poocano', 'Kinky Stinky', 'Gold Nugget', 'Cat Scat', 'Unicorn']
