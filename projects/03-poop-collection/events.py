"""Shared content-time events for picture and sound, anchored to the narration (words.wt)."""
from timeline import DUR, ON, END
from words import wt

# hero k speaks line HERO_LINE[k]; hero 2 (Skibidi) also holds the teaser line 4
HERO_LINE = [1, 2, 3, 5, 6]
HOOK_MOVE = (0.0, ON[1] - 0.05)
AD_STOP = END[4] + 0.22                   # after «А дальше — два настоящих шедевра», before «Модерн Арт»
TRANSITS = [(END[1] - 0.25, ON[2] + 0.75), (END[2] - 0.25, ON[3] + 0.75),
            (AD_STOP + 0.07, ON[5] + 0.95), (END[5] - 0.15, ON[6] + 0.75)]
PULLBACK = (ON[7] - 0.1, DUR)

HOOK = dict(title=0.12, real=wt(0, 'банка'))

HEROES_T = []
for k in range(5):
    arrive = HOOK_MOVE[1] if k == 0 else TRANSITS[k - 1][1]
    leave = TRANSITS[k][0] if k < 4 else PULLBACK[0]
    HEROES_T.append(dict(arrive=arrive, leave=leave, title=arrive - 0.45, out=leave - 0.1))

H = HEROES_T
H[0].update(f1=wt(1, 'первое'), f2=wt(1, 'находит'), stamp=wt(1, 'Млечному'))
H[1].update(f1=wt(2, 'Копи'), f2=wt(2, 'прошедший'), stamp=wt(2, 'тысячи'))
H[2].update(f1=wt(3, 'редкость'), f2=wt(3, 'мем'), stamp=wt(3, 'десятая'), facts_out=ON[4] - 0.2,
            teaser=ON[4])
H[2]['out'] = AD_STOP + 0.35                       # title/teaser stay through the ad pause
H[3].update(f1=max(wt(5, 'банан'), TRANSITS[2][1] - 0.2), f2=wt(5, 'купили'), stamp=wt(5, 'съели'))
H[4].update(f1=wt(6, 'банка'), f2=wt(6, 'тридцать'), stamp=wt(6, 'двести'))

FINAL = dict(line=ON[7] + 0.1, art=wt(7, 'искусство'), cta=wt(7, 'Перешли'), fade=DUR - 0.3)
LIGHT_ON = [h['arrive'] - 0.35 for h in HEROES_T]

for h in HEROES_T:                                  # a fact never appears before its hero's title
    h['f1'] = max(h['f1'], h['title'] + 0.35)
    h['f2'] = max(h['f2'], h['f1'] + 0.6)
