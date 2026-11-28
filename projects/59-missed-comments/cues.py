"""События, общие для картинки и звука."""
from timeline import V, T, SCENES

CUTS = [V[k] for k in SCENES[1:] if k != 'L3']          # на L3 свои удары карточек
BURST = [V['L1'] + 0.08 + i * 0.05 for i in range(6)]   # подарки разлетаются от аватарки
COUNTER = [V['L2'] + 0.6 + i * 0.32 for i in range(12)]
BUBBLES2 = [V['L2'] + 1.0 + i * 0.7 for i in range(6)]
RAIN_POPS = [T['rain'] + 0.25 + i * 0.11 for i in range(14)]
BUBBLES5 = [V['L5'] + 0.3 + i * 0.42 for i in range(6)]
ARROW = [T['each'] + 0.6 + i * 0.5 for i in range(3)]
CHEAP = ['Lol Pop', 'Desk Calendar', 'B-Day Candle', 'Hypno Lollipop', 'Jester Hat', 'Ginger Cookie', 'Snow Mittens',
         'Star Notepad', 'Hanging Star', 'Party Sparkler', 'Santa Hat', 'Spiced Wine', 'Witch Hat', 'Big Year',
         'Holiday Drink', 'Snake Box', 'Pet Snake', 'Candy Cane', 'Winter Wreath', 'Jack-in-the-Box', 'Xmas Stocking',
         'Whip Cupcake', 'Instant Ramen', 'Ice Cream', 'Fresh Socks', 'Clover Pin', 'Lush Bouquet', 'Happy Brownie',
         'Mood Pack', 'Cookie Heart', 'Jingle Bells', 'Snow Globe']
TIERS = [('10 000', 'Mighty Arm', 'T800'), ('100 000', 'Resistance Dog', 'Ultras'), ('1 000 000', 'Heart Locket', 'Royal Flush')]
