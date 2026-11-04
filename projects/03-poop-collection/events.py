"""Shared content-time events for picture and sound, anchored to the narration (words.wt)."""
from timeline import DUR, ON, END
from words import wt

# hero k speaks in line HERO_LINE[k]; hero 3 (Poopsicle) also holds the teaser line 4
HERO_LINE = [1, 2, 3, 5, 6]
HOOK_MOVE = (0.0, ON[1] - 0.05)
TRANSITS = [(END[1] - 0.2, ON[2] + 0.8), (END[2] - 0.15, ON[3] + 0.75),
            None, (END[5] + 0.3, ON[6] + 0.75)]
AD_STOP = END[4] + 0.25                   # after the teaser «…за которой нужно убирать», before «Пу Байт»
TRANSITS[2] = (AD_STOP + 0.07, ON[5] + 1.0)
PULLBACK = (ON[7] - 0.1, DUR)

HOOK = dict(title=0.12, real=wt(0, 'официально'))

HEROES_T = []
for k in range(5):
    arrive = HOOK_MOVE[1] if k == 0 else TRANSITS[k - 1][1]
    leave = TRANSITS[k][0] if k < 4 else PULLBACK[0]
    HEROES_T.append(dict(arrive=arrive, leave=leave, title=arrive - 0.45, out=leave - 0.1))

H = HEROES_T
H[0].update(f1=wt(1, 'вышла'), f2=wt(1, 'пятьдесят'), stamp=wt(1, 'какашки'), swap=wt(1, 'Редчайшая'),
            facts_out=wt(1, 'Редчайшая') - 0.15, f3=wt(1, 'Редчайшая'), fan=wt(1, 'пятьдесят'))
H[1].update(f1=wt(2, 'Столько'), f2=wt(2, 'Мем'), stamp=wt(2, 'Мем'))
H[2].update(f1=wt(3, 'эскимо'), f2=wt(3, 'Такая'), stamp=wt(3, 'Лизать'), side=wt(3, 'Такая'),
            facts_out=ON[4] - 0.2, teaser=ON[4])
H[3].update(f1=wt(5, 'тамагочи'), f2=wt(5, 'настоящем'), stamp=wt(5, 'убрать'))
H[4].update(f1=wt(6, 'дарить'), f2=wt(6, 'Голд'), stamp=wt(6, 'золотую'))
H[2]['out'] = AD_STOP + 0.35                       # title/teaser stay through the ad pause

FINAL = dict(big=wt(7, 'подарки') - 0.1, toilet=wt(7, 'унитаз'), paper=wt(7, 'рулон'), cta=ON[8], fade=DUR - 0.3)
LIGHT_ON = [h['arrive'] - 0.35 for h in HEROES_T]
