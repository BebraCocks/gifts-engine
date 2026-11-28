"""События, общие для картинки и звука (второй канал)."""
from timeline import V, T

CUTS = [V[k] for k in ('L2', 'L4', 'L5')]
FLIP = [T['rule'] + i * 0.12 for i in range(20)]            # табло-счётчик листается
CHESTS = T['tier']
COINS = [T['sell'] + 0.1 + i * 0.07 for i in range(10)]
CART = [T['buy'] + 0.15 + i * 0.12 for i in range(10)]
DELIVER = [T['give2'] + 0.2 + i * 0.16 for i in range(9)]
TYPE_KEYS = [T['type'] + i * 0.11 for i in range(22)]
COMMENTS = [T['any'] + 0.2 + i * 0.25 for i in range(9)]
CHEAP = ['Lol Pop', 'Desk Calendar', 'B-Day Candle', 'Hypno Lollipop', 'Jester Hat', 'Ginger Cookie', 'Snow Mittens',
         'Star Notepad', 'Hanging Star', 'Party Sparkler', 'Santa Hat', 'Spiced Wine', 'Witch Hat', 'Big Year',
         'Holiday Drink', 'Snake Box', 'Pet Snake', 'Candy Cane', 'Winter Wreath', 'Jack-in-the-Box', 'Xmas Stocking',
         'Whip Cupcake', 'Instant Ramen', 'Ice Cream', 'Fresh Socks', 'Clover Pin', 'Lush Bouquet', 'Happy Brownie',
         'Mood Pack', 'Cookie Heart', 'Jingle Bells', 'Snow Globe']
TIERS = [('10К', 'Mighty Arm', 'T800'), ('100К', 'Resistance Dog', 'Ultras'), ('1 МЛН', 'Heart Locket', 'Royal Flush')]
