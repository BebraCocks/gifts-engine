"""События, общие для картинки и звука (третий ролик)."""
from timeline import V, T

CUTS = [V[k] for k in ('L2', 'L3', 'L4', 'L5')]
SLAMS = [T['self0'], T['sell'], T['give']]
COINS = [T['sell'] + 0.15 + i * 0.08 for i in range(8)]
RAIN = [T['give'] + 0.2 + i * 0.12 for i in range(10)]
STICKERS = [T['word'], T['smile'], T['dot']]
PRESS = [V['L5'] + 0.3, V['L5'] + 1.1, V['L5'] + 1.9]
CHEAP = ['Lol Pop', 'Desk Calendar', 'B-Day Candle', 'Hypno Lollipop', 'Jester Hat', 'Ginger Cookie', 'Snow Mittens',
         'Star Notepad', 'Hanging Star', 'Party Sparkler', 'Santa Hat', 'Spiced Wine', 'Witch Hat', 'Big Year',
         'Holiday Drink', 'Snake Box', 'Pet Snake', 'Candy Cane', 'Winter Wreath', 'Jack-in-the-Box']
TIERS = [('10 000', 'Mighty Arm', 'T800'), ('100 000', 'Resistance Dog', 'Ultras'), ('1 000 000', 'Heart Locket', 'Royal Flush')]
