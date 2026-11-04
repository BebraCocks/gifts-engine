"""02-gift-counts: «Ночная галерея графа» — own visual concept (see STORYBOARD.md, section 2)."""
STYLE_READY = False            # set True only after the author says «собирай»
WITHOUT_NARRATION = True       # no Fish Audio key: on-screen text only, banner sound stays

PARCHMENT = (243, 230, 200)
GOLD = (217, 164, 65)
BLOOD = (190, 24, 48)
INK = (12, 8, 12)

DATA_DATE = '04.11.2026'
DATA_SOURCE = 'api.changes.tg'

# Hero portraits. Rarity from api.changes.tg (fetched 2026-11-04); backdrop = Telegram backdrop colours
# picked for composition (not a specific owned gift). wall: L/R side wall at z, E = end wall.
HEROES = [
    dict(gift='Jolly Chimp', model='Count Macaqula', rarity='1%', wall='L', z=-48.0,
         backdrop=('#ae6cae', '#470c47'), stamp='ПАРОДИЯ', stamp_rgb=BLOOD),
    dict(gift='Kissed Frog', model='Count Croakula', rarity='0,5%', wall='R', z=-58.0,
         backdrop=('#a35e66', '#340307'), stamp='ПАРОДИЯ', stamp_rgb=BLOOD),
    dict(gift='Spy Agaric', model='Nosferatu', rarity='0,2%', wall='L', z=-68.0,
         backdrop=('#5c6985', '#030a18'), stamp='ПИРАТ', stamp_rgb=BLOOD),
    dict(gift='Desk Calendar', model='Count Dracula', rarity='только крафт', wall='R', z=-78.0,
         backdrop=('#4d5254', '#0e0f0f'), stamp='ВЫМЫСЕЛ', stamp_rgb=BLOOD),
    dict(gift='Spiced Wine', model='Earl Grey', rarity='1,3%', wall='E', z=-92.0,
         backdrop=('#ccab41', '#5d3b00'), stamp='НАСТОЯЩИЙ', stamp_rgb=GOLD),
]
# The other seven «counts»: models named Dracula (rarity from the same fetch).
DRACULAS = [
    ('Ginger Cookie', '0,3%'), ('Pet Snake', '0,5%'), ('Mini Oscar', '1,5%'), ('Sleigh Bell', '1,5%'),
    ('Snow Globe', '1,5%'), ('Whip Cupcake', '1,5%'), ('Resistance Dog', '1,6%'),
]
