"""События, общие для картинки и звука (четвёртый ролик, 8-бит)."""
from timeline import V, T

CUTS = [V[k] for k in ('L2', 'L3', 'L4', 'L5')]
TYPE1 = [V['L1'] + 0.1 + i * 0.09 for i in range(24)]          # печать заголовка
TYPE2 = [T['quest'] + i * 0.08 for i in range(28)]              # печать диалога квеста
COINS = [T['sell'] + 0.2 + i * 0.1 for i in range(10)]
DROPS = [T['gifts'] + 0.2 + i * 0.14 for i in range(10)]
PLUS = [T['letter'], T['emoji'], T['dot']]
CHEAP = ['Lol Pop', 'Desk Calendar', 'B-Day Candle', 'Hypno Lollipop', 'Jester Hat', 'Ginger Cookie', 'Snow Mittens',
         'Star Notepad', 'Hanging Star', 'Party Sparkler', 'Santa Hat', 'Spiced Wine', 'Witch Hat', 'Big Year']
TIERS = [('10K', 'Mighty Arm', 'T800'), ('100K', 'Resistance Dog', 'Ultras'), ('1M', 'Heart Locket', 'Royal Flush')]
